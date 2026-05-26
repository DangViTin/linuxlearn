---
chapter: 74
title: Hall-effect & rotary position (AS5048A / A1324 / TLE5012)
part: VII — Device cookbook
estimated_pages: 18
status: draft
---

# Chapter 74 — Hall-effect & rotary position sensors

> **What:** three Hall-effect-based position sensors at different abstraction levels: **AMS AS5048A** (SPI, 14-bit absolute rotary, "magnet-on-axis" encoder), **Allegro A1324** (analog linear Hall sensor), **Infineon TLE5012B** (SPI, high-rate, dual-die for safety-critical motor control). For each: physics, protocol, mainline driver, plus a from-scratch SPI driver for AS5048A.
> **Why:** measuring rotary position without mechanical contact is the foundation of brushless motor control, robotic joints, throttle position sensors, steering angle, knob inputs on appliances. Hall-on-magnet replaces optical encoders for lower cost, infinite life (no slip-rings or photo-emitter aging), and tolerance to oil/dust.
> **Focus:** **the magnet matters as much as the chip**. AS5048 needs a *diametrically magnetised* 2-pole magnet, axially mounted, 0.5–3 mm above the chip die. Wrong magnet, wrong distance, wrong polarisation = the chip reports nonsense or a low-resolution mess. Most "AS5048 doesn't work" reports trace to magnet selection.

## 74.1  Sensor comparison

| | AMS AS5048A | Allegro A1324 | Infineon TLE5012B |
|---|---|---|---|
| Output | 14-bit absolute angle | analog 0–3 V | 15-bit absolute angle |
| Interface | SPI (also I²C version: AS5048B) | analog | SPI (SSC mode) |
| Update rate | 11.25 kHz | continuous (analog) | 42 µs latency (24 kHz) |
| Magnet | diametric, on-axis | linear flux | diametric, on-axis |
| Magnet distance | 0.5 – 3 mm | physical contact / very close | 0.5 – 3 mm |
| Programmable zero | yes | no | yes |
| ABI/UVW output | yes | no | yes |
| Safety features | none | none | dual-die for ASIL-B |
| Volume price | $3–6 | $0.50–1.50 | $7–12 |

**Pick guide:**
- **AS5048A**: general motor control, joystick/knob, robotics. Default choice.
- **A1324**: simple "is metal nearby?" or linear-distance from a magnet. ADC-based.
- **TLE5012B**: automotive / safety-rated motor control. Has redundancy.

## 74.2  The physics — Hall and magnetoresistive

A Hall sensor outputs a voltage proportional to the magnetic-field component perpendicular to its die. Rotate a 2-pole magnet near the chip: the field above the chip's center rotates with the magnet. Two perpendicular Hall sensors on the same die (at 0° and 90°) give sin(θ) and cos(θ) — perfect for `atan2()` to extract angle.

AS5048 and TLE5012 actually use **giant magnetoresistance** (GMR) elements arranged in Wheatstone bridges, slightly different from raw Hall but the same principle: cos/sin → angle.

The **magnet** must be:
- **Diametrically magnetised**: poles on opposite sides of the cylinder, not top/bottom. This makes the field rotate with the magnet.
- **On-axis**: the chip's center aligned with the magnet's rotational axis (within ±0.5 mm).
- **At the right distance**: 0.5–3 mm gap. Too close = chip saturates. Too far = noise dominates.

Common Chinese eBay "AS5048A modules" ship without a magnet or with the wrong (axial) magnet. Buy a small (6 mm × 2.5 mm) **diametrically-magnetised** disc-magnet separately.

## 74.3  Protocol — AS5048A SPI

AS5048A uses SPI with a peculiar **command-then-result** sequence. Each SPI frame is 16 bits:

```
   bit 15:    parity (even parity over remaining 15 bits)
   bit 14:    R/W (1 = read, 0 = write)
   bits 13:0: register address (or data)
```

You send a *command frame* this transaction; the *response* comes in the *next* transaction.

To read the angle register (0x3FFF):

```
   Transaction 1:
       Host → chip: 0xFFFF  (parity=1, R=1, addr=0x3FFF)
       Chip → host: (irrelevant — whatever's in the chip's response buffer)

   Transaction 2:
       Host → chip: 0x0000  (NOP — or queue next command)
       Chip → host: 0x_AAAA where AAAA = angle data
```

The response's bit layout:

```
   bit 15:    parity
   bit 14:    error flag (1 = error, read 0x4001 to clear)
   bits 13:0: 14-bit angle (0..16383)
```

Convert to degrees: `angle_deg = (raw / 16384.0) * 360.0`.

### Parity check

Even parity over bits 14:0. The chip rejects frames with bad parity. Implementation:

```c
static u16 as5048_parity(u16 v)
{
    v ^= v >> 8;
    v ^= v >> 4;
    v ^= v >> 2;
    v ^= v >> 1;
    return v & 1;
}

u16 frame_for_read(u16 addr)
{
    u16 cmd = (1 << 14) | addr;   /* R=1 */
    if (as5048_parity(cmd)) cmd |= (1 << 15);   /* set parity to make even */
    return cmd;
}
```

### Key registers

| Reg | Name | Purpose |
|-----|------|---------|
| 0x0000 | NOP | dummy frame |
| 0x0001 | Clear error flag | reading returns error code, clears flag |
| 0x0003 | Programming control | for OTP burn (one-time-programmable) |
| 0x0016 | OTP zero position high | 8 bits |
| 0x0017 | OTP zero position low | 6 bits |
| 0x3FFD | Diagnostics + AGC | magnet too weak / too strong / etc. |
| 0x3FFE | Magnitude | strength of field (sanity check) |
| 0x3FFF | Angle | the answer |

## 74.4  Writing an AS5048A driver from scratch

`myas5048.c`:

```c
#include <linux/init.h>
#include <linux/module.h>
#include <linux/spi/spi.h>
#include <linux/iio/iio.h>

#define REG_ANGLE       0x3FFF
#define REG_DIAG        0x3FFD
#define REG_MAGNITUDE   0x3FFE
#define REG_CLEAR_ERR   0x0001

struct myas {
    struct spi_device *spi;
    struct mutex lock;
};

static u16 parity_even(u16 v)
{
    v ^= v >> 8; v ^= v >> 4; v ^= v >> 2; v ^= v >> 1;
    return v & 1;
}

static u16 build_read_cmd(u16 addr)
{
    u16 cmd = (1 << 14) | (addr & 0x3FFF);
    if (parity_even(cmd)) cmd |= 1 << 15;
    return cmd;
}

/* Two-frame transaction: send cmd this frame, get result in next */
static int ma_read_reg(struct myas *m, u16 addr, u16 *out)
{
    u16 cmd = build_read_cmd(addr);
    u16 nop = build_read_cmd(0x0000);
    u8 tx[4], rx[4];
    struct spi_transfer xfer = {
        .tx_buf = tx,
        .rx_buf = rx,
        .len = 4,
    };
    int err;

    /* Big-endian on the wire */
    tx[0] = cmd >> 8; tx[1] = cmd & 0xFF;
    tx[2] = nop >> 8; tx[3] = nop & 0xFF;

    err = spi_sync_transfer(m->spi, &xfer, 1);
    if (err) return err;

    /* Result is in the second 16 bits */
    u16 result = (rx[2] << 8) | rx[3];

    /* Check parity (we don't enforce, just log) */
    if (parity_even(result))
        pr_debug("myas5048: bad parity on read\n");

    /* Check error flag */
    if (result & (1 << 14)) {
        pr_warn("myas5048: error flag set\n");
        /* Issue a clear-error transaction */
    }

    *out = result & 0x3FFF;
    return 0;
}

static int ma_read_raw(struct iio_dev *idev,
                       struct iio_chan_spec const *chan,
                       int *val, int *val2, long mask)
{
    struct myas *m = iio_priv(idev);
    u16 raw;
    int err;

    if (chan->type != IIO_ANGL) return -EINVAL;

    switch (mask) {
    case IIO_CHAN_INFO_RAW:
        mutex_lock(&m->lock);
        err = ma_read_reg(m, REG_ANGLE, &raw);
        mutex_unlock(&m->lock);
        if (err) return err;
        *val = raw;
        return IIO_VAL_INT;
    case IIO_CHAN_INFO_SCALE:
        /* 14-bit = 16384 LSB per full turn = 2π rad
         * 1 LSB = 2π / 16384 ≈ 383.5 µrad */
        *val = 0; *val2 = 383495;     /* nano-radians per LSB */
        return IIO_VAL_INT_PLUS_NANO;
    }
    return -EINVAL;
}

static const struct iio_chan_spec ma_channels[] = {
    {
        .type = IIO_ANGL,
        .info_mask_separate = BIT(IIO_CHAN_INFO_RAW),
        .info_mask_shared_by_type = BIT(IIO_CHAN_INFO_SCALE),
    },
};

static const struct iio_info ma_iio_info = {
    .read_raw = ma_read_raw,
};

static int ma_probe(struct spi_device *spi)
{
    struct iio_dev *idev;
    struct myas *m;
    u16 magnitude;
    int err;

    idev = devm_iio_device_alloc(&spi->dev, sizeof(*m));
    if (!idev) return -ENOMEM;
    m = iio_priv(idev);
    m->spi = spi;
    mutex_init(&m->lock);

    spi->mode = SPI_MODE_1;     /* CPOL=0, CPHA=1 per AS5048 datasheet */
    spi->bits_per_word = 8;
    err = spi_setup(spi);
    if (err) return dev_err_probe(&spi->dev, err, "spi_setup failed\n");

    /* Sanity-check magnet by reading magnitude */
    err = ma_read_reg(m, REG_MAGNITUDE, &magnitude);
    if (err) return err;
    /* Read again to get the actual answer (first frame is throwaway) */
    err = ma_read_reg(m, REG_MAGNITUDE, &magnitude);
    if (err) return err;
    dev_info(&spi->dev, "AS5048 magnitude: %u (typical 5000-6000 with good magnet)\n",
             magnitude);
    if (magnitude < 1000)
        dev_warn(&spi->dev, "weak magnet — check distance/orientation\n");

    idev->name = "myas5048a";
    idev->info = &ma_iio_info;
    idev->modes = INDIO_DIRECT_MODE;
    idev->channels = ma_channels;
    idev->num_channels = ARRAY_SIZE(ma_channels);

    return devm_iio_device_register(&spi->dev, idev);
}

static const struct of_device_id ma_of_match[] = {
    { .compatible = "linuxlearn,myas5048a" },
    { }
};
MODULE_DEVICE_TABLE(of, ma_of_match);

static const struct spi_device_id ma_id[] = { { "myas5048a", 0 }, { } };
MODULE_DEVICE_TABLE(spi, ma_id);

static struct spi_driver ma_driver = {
    .driver = {
        .name = "myas5048a",
        .of_match_table = ma_of_match,
    },
    .probe = ma_probe,
    .id_table = ma_id,
};
module_spi_driver(ma_driver);

MODULE_LICENSE("GPL");
```

DT:

```dts
&ecspi3 {
    as5048a@0 {
        compatible = "linuxlearn,myas5048a";
        reg = <0>;
        spi-max-frequency = <10000000>;
        spi-cpha;                       /* mode 1 */
    };
};
```

Test:

```
[root@pa-mini:~]# insmod myas5048a.ko
[root@pa-mini:~]# dmesg | tail -2
myas5048a spi3.0: AS5048 magnitude: 5482 (typical 5000-6000 with good magnet)

[root@pa-mini:~]# cat /sys/bus/iio/devices/iio:device0/in_angl_raw
8192       ← 180° (8192 / 16384 × 360°)

[root@pa-mini:~]# # Rotate the magnet 90°:
[root@pa-mini:~]# cat /sys/bus/iio/devices/iio:device0/in_angl_raw
12288     ← 270°

[root@pa-mini:~]# # In radians:
[root@pa-mini:~]# awk "BEGIN { print 12288 * 0.000383495 }"
4.71239    ← 270° = 3π/2 rad ≈ 4.71
```

Driver is ~150 lines. The 14-bit absolute angle is now in IIO, ready for any consumer.

## 74.5  A1324 — analog linear Hall

Allegro A1324 is a 3-pin part: VCC, GND, OUT. Output voltage:

```
V_OUT = V_OUT_Q + sensitivity × B
       (V_OUT_Q ≈ VCC/2 at zero field; sensitivity ≈ 5 mV/Gauss)
```

To read: wire to ADC (Ch 80 or i.MX6ULL internal ADC). The "driver" is just the ADC driver. User-space converts voltage to Gauss (or position, given a known magnet's field-vs-distance curve).

For "is there a magnet nearby?" (lid open/closed, latch position): A1324 + ADC + a threshold is enough.

## 74.6  TLE5012B — the safety variant

TLE5012B is functionally similar to AS5048 but with two independent dies on the same package. Each gets its own SPI access; you cross-check the two readings; any divergence indicates fault. ASIL-B (SIL-2) capable.

Mainline driver: `drivers/iio/position/iqs62x.c` covers some Iqs sensors; TLE5012 has out-of-tree drivers from Infineon. The protocol is more elaborate (16-bit SPI with a "SSC" auto-mode option for continuous streaming).

For non-safety-critical use, AS5048 is the cheaper, equally-accurate choice.

## 74.7  Mainline driver enablement

`drivers/iio/position/as5048.c` is the mainline AS5048 driver (covers AS5048A SPI and AS5048B I²C variants).

DT:

```dts
&ecspi3 {
    as5048a@0 {
        compatible = "ams,as5048a";
        reg = <0>;
        spi-max-frequency = <10000000>;
        spi-cpha;
    };
};
```

After load: `/sys/bus/iio/devices/iio:device0/in_angl_raw` plus `_scale` for converting to radians.

## 74.8  Lab

1. **Magnet check.** Use a real diametric magnet (e.g., 6×2.5 mm disc). Verify orientation: the magnet's N-S axis should be in the *plane* of the chip's surface.
2. **Build and load `myas5048a.ko`.** Verify magnitude > 4000 (good magnet); read angle while rotating.
3. **360° sweep.** Rotate slowly; log raw values; verify monotonic 0 → 16383 → 0 wraparound.
4. **Resolution test.** With chip stationary, read 100 samples; standard deviation should be < 5 LSB (0.1°).
5. **Distance sweep.** Move the magnet from 0.5 mm to 5 mm. Magnitude rises then falls; angle stays valid throughout the recommended range.
6. **Mainline switch.** Use `compatible = "ams,as5048a"`. Same data, plus rich diagnostic attributes.
7. **A1324 with ADC.** Wire A1324 output to i.MX6ULL ADC1 channel; verify IIO ADC reading changes when bringing a magnet near.
8. **Servo controller demo.** Hook the AS5048's angle to a PID loop driving a motor; verify the system closes to a setpoint within 1°.

Commit code to `code/ch74-hall-rotary/`.

## 74.9  Pitfalls

- **Wrong magnet.** Axial magnetisation = chip sees constant field, no rotation signal. Diametric is mandatory.
- **Magnet off-axis.** Even 0.5 mm off-axis adds significant non-linearity (>1° error). Mechanical fixturing matters.
- **Magnet too close.** Chip saturates; angle clamps or wraps. Datasheet specifies 1–3 mm typical.
- **Magnet too far / weak.** Magnitude register low; angle is noisy. Use a stronger magnet or move closer.
- **SPI mode wrong.** AS5048A is mode 1 (CPOL=0, CPHA=1). Mode 0 returns 0xFFFF every read.
- **Forgetting the two-frame protocol.** A read result is in the *next* frame. First read returns junk; second returns the answer.
- **Parity ignored on critical applications.** The chip can return bad data due to bus noise; parity is your sanity check. Always validate in safety-critical code.
- **Magnetic interference from motor.** If the AS5048 is on the motor's shaft, motor magnets/coils may bleed through. Use shielding or magnetic isolation.
- **Hot-plug/start-up race**. The chip needs ~10 ms to start up after VCC. Reading earlier returns junk. Mainline driver handles this; from-scratch must too.

## 74.10  Going deeper

- **`drivers/iio/position/as5048.c`** — production AS5048 driver.
- **AS5048A datasheet (AMS)** — SPI protocol, magnet selection appendix, programming OTP.
- **A1324 datasheet (Allegro)** — output transfer function.
- **TLE5012B datasheet (Infineon)** — SSC protocol, safety features.
- **AMS app note AN53048-A1** — magnet selection and mechanical mounting recommendations.
- **`Documentation/ABI/testing/sysfs-bus-iio` (channel type IIO_ANGL)** — angle channel ABI.

---

> **End of Group D — Position & distance (Ch 72–74).** From "how far" (ToF, ultrasonic, IR) to "which way" (magnetometer) to "what angle" (Hall rotary). Three different physics, three different driver shapes.

> Next chapter: **Chapter 75 — Current and power monitoring (INA219 / INA226 / INA3221).** Low-side and high-side current measurement, the calibration register that nobody understands at first, and the `hwmon` framework that sometimes coexists with IIO for the same chip.
