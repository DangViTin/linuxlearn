---
chapter: 72
title: Distance & proximity (VL53L0X / HC-SR04 / GP2Y0A)
part: VII — Device cookbook
estimated_pages: 22
status: draft
---

# Chapter 72 — Distance & proximity sensors

> **What:** three radically different "how far away is that object" sensors: **STMicro VL53L0X** (I²C, laser time-of-flight, mm precision, requires firmware-blob upload at probe), **HC-SR04** (GPIO, ultrasonic, famously hard to time accurately under Linux), **Sharp GP2Y0A** (analog IR, ADC-fed). For each: physics, protocol, the mainline driver, and a from-scratch driver for VL53L0X (the most interesting case) plus a clear-eyed look at why HC-SR04 is hard on Linux.
> **Why:** distance sensing is in every robot, every parking assist, every smart-lighting fixture. The three classes cover the practical price/accuracy spectrum: $0.50 IR analog → $3 ultrasonic → $8 ToF laser. Knowing the trade-offs lets you pick correctly and not promise users a ranging accuracy you cannot actually deliver.
> **Focus:** Time-of-flight measures with electronics. Ultrasonic measures with sound. IR measures with reflected brightness. Three different physics. ToF measures photon round-trip directly (mm-accurate, fast, expensive). Ultrasonic measures sound round-trip (cm-accurate, slow, cheap). IR measures reflected intensity then maps to a non-linear curve (poor accuracy, very cheap). Each driver's complexity tracks the physics.

## 72.1  Sensor comparison

| | STMicro VL53L0X | HC-SR04 | Sharp GP2Y0A21YK |
|---|---|---|---|
| Physics | 940 nm laser ToF | 40 kHz ultrasonic | 850 nm IR triangulation |
| Range | 30 mm – 2000 mm | 20 mm – 4000 mm | 100 mm – 800 mm |
| Accuracy | ±3% (≤ 1.2 m), ±7% (1.2 – 2 m) | ±3 mm | ±5% non-linear |
| Update rate | 50 Hz (default) | ~20 Hz | ~25 Hz |
| Interface | I²C (0x29) | GPIO (TRIG + ECHO) | Analog 0 – 3 V |
| Beam cone | ~25° | ~30° | ~5° |
| Sunlight tolerance | poor (IR ambient washout) | excellent | poor |
| Volume price | $5–8 | $1–2 | $3–5 |
| Mainline driver | `vl53l0x-i2c.c` | none (GPIO + user-space or sleeping-bitbang) | none (analog → IIO ADC) |

**Pick guide:**
- **VL53L0X**: indoor robotics, gesture detection, gauging — where mm precision matters.
- **HC-SR04**: low-cost cm-precision; outdoor (it tolerates sun); cheap robots, parking sensors.
- **GP2Y0A**: rough proximity ("is there a wall in front?"), trip-wire, line-following robots.

## 72.2  The three physics

### VL53L0X — Time-of-Flight

A pulsed 940 nm VCSEL (vertical-cavity surface-emitting laser) emits ~10 ns pulses; a Single-Photon Avalanche Diode (SPAD) array detects returning photons. The chip times the round-trip with picosecond resolution → distance = c × t / 2.

Range is 2 m in indoor light. In direct sunlight it drops to ~0.6 m because 940 nm ambient noise dominates. The chip is accurate and fast, but more complex than the alternatives.

### HC-SR04 — Ultrasonic

A transducer emits 8 pulses of 40 kHz ultrasound on the TRIG pin's rising edge. A receiver listens for the echo and pulses the ECHO line for as long as the round-trip takes. Distance = (echo_pulse_us / 58) cm, or in metric: `t_us × 0.000343 / 2` m.

Robust to light, fails on soft / angled / tiny targets (poor acoustic reflection). Slow: at 4 m max range, one measurement takes ~24 ms (longer if no echo — you need a timeout).

### GP2Y0A — IR triangulation

An IR LED emits a 5 ms pulse. A linear PSD (position-sensitive detector) measures *where* the reflected spot lands on the sensor (not how bright). The angle of return → distance via triangulation.

Non-linear output curve (output voltage *not* monotonic with distance — has a peak around 80 mm). Datasheet provides a piecewise table. Cheap and good enough for "object near" detection; bad for precise ranging.

## 72.3  Protocol — VL53L0X

VL53L0X is unusual: it needs a long initial register-write sequence — effectively a firmware blob — uploaded at every probe. Unlike most I²C devices that have a fixed register-set behavior, VL53L0X needs to be initialized by uploading **160 separate register writes** at probe — calibration constants, internal-state-machine setup, and tuning parameters. STMicro's API ships these as a long list in their reference code; the kernel driver embeds them too.

Register map (just the headlines):

| Reg | Name | Purpose |
|-----|------|---------|
| 0xC0 | IDENTIFICATION_MODEL_ID | Always 0xEE (or 0xEEAA depending on rev) |
| 0xC1 | IDENTIFICATION_REV_ID | Silicon revision |
| 0x88 | POWER_MANAGEMENT_GO1 | Power mode |
| 0x80 | (multi-purpose) | Various commands |
| 0x00 | SYSRANGE_START | Write 0x01 → start a measurement |
| 0x13 | RESULT_INTERRUPT_STATUS | Bit 0 set when new measurement ready |
| 0x14 | RESULT_RANGE_STATUS + RANGE_MM_HI/LO | Status + 16-bit distance |
| 0x0A | SYSTEM_INTERRUPT_CONFIG_GPIO | What triggers INT1 |
| 0x60..0xA0 | various magic registers | Tuning, calibration, undocumented |

### The init sequence

```
1. Read 0xC0 (verify chip-id = 0xEE).
2. Write to ~30 "magic" registers to enable internal voltage references.
3. Read SPAD info from a private register sequence.
4. Apply the SPAD calibration map (10+ writes).
5. Load default tuning settings (~80 register writes — basically opaque to user).
6. Configure interrupt: INT on new-sample-ready, active-low.
7. Perform reference calibration (VHV and phase).
8. Start measurement mode.
```

Step 5 is the "tuning settings load" — the famous register-pair dump:

```c
static const u8 vl53l0x_default_tuning[] = {
    0xFF, 0x01,    0x00, 0x00,
    0xFF, 0x00,    0x09, 0x00,
    0x10, 0x00,    0x11, 0x00,
    0x24, 0x01,    0x25, 0xFF,
    ... (about 80 pairs) ...
    0xFF, 0x00,    0x80, 0x00,
};
```

Each pair is `(register, value)`. The driver writes them sequentially. The values are STMicro's IP — they're a calibrated "factory good" state-machine config for the SPAD array. Don't try to derive them from datasheet; they aren't documented.

### A measurement cycle

```
Host: write 0x00 = 0x01    (SYSRANGE_START — single-shot)
... wait for interrupt or poll bit 0 of 0x13 ...
Host: read 2 bytes from 0x1E    (RANGE_MM_HI/LO)
Host: write 0x0B = 0x01    (clear interrupt)
```

Distance = `(buf[0] << 8) | buf[1]` mm. Range status (0x14) tells you about errors: signal too weak (target too far), sigma too high (noisy ambient).

## 72.4  How the mainline `vl53l0x` driver works

Source: `drivers/iio/proximity/vl53l0x-i2c.c` (~600 lines).

Surprisingly compact for a chip with a firmware-blob-equivalent. The driver embeds STMicro's tuning data as a const u8 array and writes it at probe. The init code uses `regmap_multi_reg_write` for the tuning dump.

```c
/* Simplified probe */
static int vl53l0x_probe(struct i2c_client *client)
{
    struct vl53l0x_data *data;
    struct iio_dev *indio_dev;
    u8 chip_id;
    int err;

    indio_dev = devm_iio_device_alloc(&client->dev, sizeof(*data));
    data = iio_priv(indio_dev);
    data->client = client;
    mutex_init(&data->lock);

    /* Optionally toggle XSHUT to force reset */
    if (data->xshut_gpio)
        gpiod_set_value_cansleep(data->xshut_gpio, 0);

    /* Verify chip-id */
    err = i2c_smbus_read_byte_data(client, VL53L0X_REG_IDENTIFICATION_MODEL_ID);
    if (err != 0xEE) return -ENODEV;

    /* Big init: ~160 register writes from a tuning blob */
    err = vl53l0x_init(data);
    if (err) return err;

    /* IIO setup */
    indio_dev->name = "vl53l0x";
    indio_dev->info = &vl53l0x_iio_info;
    indio_dev->modes = INDIO_DIRECT_MODE;
    indio_dev->channels = vl53l0x_channels;
    indio_dev->num_channels = ARRAY_SIZE(vl53l0x_channels);

    return devm_iio_device_register(&client->dev, indio_dev);
}

static int vl53l0x_init(struct vl53l0x_data *data)
{
    int err;
    /* Data init */
    err = i2c_smbus_write_byte_data(data->client, 0x88, 0x00); ...
    /* Static init */
    err = vl53l0x_load_tuning(data);   /* writes the 80-pair blob */
    /* Reference calibration */
    err = vl53l0x_perform_ref_calibration(data);
    /* Set measurement timing budget */
    err = vl53l0x_set_measurement_timing_budget(data, 33000);   /* µs */
    return 0;
}

static int vl53l0x_read_proximity(struct vl53l0x_data *data, int *val)
{
    int err;
    u8 buf[2];
    int retries = 100;

    /* Start single-shot */
    err = i2c_smbus_write_byte_data(data->client, 0x00, 0x01);
    if (err) return err;

    /* Wait for completion */
    while (retries--) {
        int status = i2c_smbus_read_byte_data(data->client, 0x13);
        if (status & 0x07) break;     /* new sample ready */
        msleep(1);
    }
    if (retries < 0) return -ETIMEDOUT;

    /* Read range */
    err = i2c_smbus_read_i2c_block_data(data->client, 0x1E, 2, buf);
    if (err < 0) return err;
    *val = (buf[0] << 8) | buf[1];

    /* Clear interrupt */
    i2c_smbus_write_byte_data(data->client, 0x0B, 0x01);
    return 0;
}
```

What looks complex in the driver is mostly the tuning-blob loop. The actual measurement is a single-shot trigger, busy-poll, read 2 bytes.

## 72.5  Writing a VL53L0X driver from scratch

Goal: working driver exposing `in_distance_input` in mm. We'll include a minimal-but-functional init sequence (enough to get readings, omitting the deepest calibration tweaks).

`myvl53l0x.c`:

```c
#include <linux/init.h>
#include <linux/module.h>
#include <linux/i2c.h>
#include <linux/delay.h>
#include <linux/iio/iio.h>

#define REG_MODEL_ID         0xC0
#define REG_SYSRANGE_START   0x00
#define REG_RESULT_INT_STATUS 0x13
#define REG_RESULT_RANGE     0x1E
#define REG_INT_CLEAR        0x0B

#define EXPECTED_MODEL_ID    0xEE

/* Minimal tuning blob — first 20-ish writes that get us a working chip.
 * Full STMicro blob is ~80 pairs; this is enough for default range. */
static const u8 vl_min_tuning[][2] = {
    {0x88, 0x00},
    {0x80, 0x01},
    {0xFF, 0x01},
    {0x00, 0x00},
    {0x91, 0x00},   /* stop variable */
    {0x00, 0x01},
    {0xFF, 0x00},
    {0x80, 0x00},
    /* enable signal-rate-msrc-limit defaults */
    {0x44, 0xFF},
    {0x46, 0x06},
    {0x60, 0x00},
    {0x46, 0xFF},
    /* set measurement-timing-budget for ~33 ms */
    {0x70, 0x04},
    {0x71, 0x08},
    /* misc */
    {0x4E, 0x12},
    {0x4F, 0x00},
    {0x01, 0xFF},
};

struct myvl {
    struct i2c_client *client;
    struct mutex lock;
};

static int mv_write(struct myvl *m, u8 reg, u8 val)
{
    return i2c_smbus_write_byte_data(m->client, reg, val);
}

static int mv_read(struct myvl *m, u8 reg)
{
    return i2c_smbus_read_byte_data(m->client, reg);
}

static int mv_init(struct myvl *m)
{
    int err, i;

    /* Verify chip */
    err = mv_read(m, REG_MODEL_ID);
    if (err < 0) return err;
    if (err != EXPECTED_MODEL_ID)
        return -ENODEV;

    /* Apply minimal tuning */
    for (i = 0; i < ARRAY_SIZE(vl_min_tuning); i++) {
        err = mv_write(m, vl_min_tuning[i][0], vl_min_tuning[i][1]);
        if (err) return err;
    }

    return 0;
}

static int mv_measure(struct myvl *m, int *out_mm)
{
    int retries = 100, status;
    u8 buf[2];
    int err;

    err = mv_write(m, REG_SYSRANGE_START, 0x01);
    if (err) return err;

    while (retries-- > 0) {
        status = mv_read(m, REG_RESULT_INT_STATUS);
        if (status < 0) return status;
        if (status & 0x07) break;
        usleep_range(500, 1500);
    }
    if (retries <= 0) return -ETIMEDOUT;

    err = i2c_smbus_read_i2c_block_data(m->client, REG_RESULT_RANGE, 2, buf);
    if (err < 0) return err;
    *out_mm = (buf[0] << 8) | buf[1];

    /* Clear interrupt */
    mv_write(m, REG_INT_CLEAR, 0x01);
    return 0;
}

static int mv_read_raw(struct iio_dev *idev,
                       struct iio_chan_spec const *chan,
                       int *val, int *val2, long mask)
{
    struct myvl *m = iio_priv(idev);
    int mm, err;

    if (mask != IIO_CHAN_INFO_PROCESSED) return -EINVAL;
    if (chan->type != IIO_DISTANCE) return -EINVAL;

    mutex_lock(&m->lock);
    err = mv_measure(m, &mm);
    mutex_unlock(&m->lock);
    if (err) return err;
    *val = mm;
    return IIO_VAL_INT;
}

static const struct iio_chan_spec mv_channels[] = {
    { .type = IIO_DISTANCE,
      .info_mask_separate = BIT(IIO_CHAN_INFO_PROCESSED) },
};

static const struct iio_info mv_iio_info = {
    .read_raw = mv_read_raw,
};

static int mv_probe(struct i2c_client *client)
{
    struct iio_dev *idev;
    struct myvl *m;
    int err;

    idev = devm_iio_device_alloc(&client->dev, sizeof(*m));
    if (!idev) return -ENOMEM;
    m = iio_priv(idev);
    m->client = client;
    mutex_init(&m->lock);

    err = mv_init(m);
    if (err) return dev_err_probe(&client->dev, err, "init failed\n");

    idev->name = "myvl53l0x";
    idev->info = &mv_iio_info;
    idev->modes = INDIO_DIRECT_MODE;
    idev->channels = mv_channels;
    idev->num_channels = ARRAY_SIZE(mv_channels);

    return devm_iio_device_register(&client->dev, idev);
}

static const struct of_device_id mv_of_match[] = {
    { .compatible = "linuxlearn,myvl53l0x" },
    { }
};
MODULE_DEVICE_TABLE(of, mv_of_match);

static const struct i2c_device_id mv_id[] = { { "myvl53l0x", 0 }, { } };
MODULE_DEVICE_TABLE(i2c, mv_id);

static struct i2c_driver mv_driver = {
    .driver = {
        .name = "myvl53l0x",
        .of_match_table = mv_of_match,
    },
    .probe = mv_probe,
    .id_table = mv_id,
};
module_i2c_driver(mv_driver);

MODULE_LICENSE("GPL");
```

DT:

```dts
&i2c1 {
    vl53l0x@29 {
        compatible = "linuxlearn,myvl53l0x";
        reg = <0x29>;
    };
};
```

Test:

```
[root@pa-mini:~]# insmod myvl53l0x.ko
[root@pa-mini:~]# cat /sys/bus/iio/devices/iio:device0/in_distance_input
312       ← 312 mm to nearest reflective surface
```

Wave a hand in front: number drops. Hold further: rises. ~50 Hz update rate.

The minimal-tuning blob gives "good enough" readings (~5 % accuracy in indoor light). For production with mm precision and reliable behavior in edge cases (cover dust, glass, polarisation), use the full mainline driver, which has the complete STMicro blob plus the reference-calibration routines.

## 72.6  HC-SR04 — why it's hard on Linux

The HC-SR04 protocol is dead simple in concept:

```
TRIG → drive HIGH for ≥ 10 µs, then LOW.
ECHO ← pulse stays high for (round-trip time) µs.
distance_cm = pulse_us / 58
```

But measuring a pulse of variable duration (60 µs to ~23 ms) with µs accuracy from Linux GPIO is *hard*:

- Standard kernel preemption: any other ISR or higher-priority thread can delay your edge measurement by 100+ µs → 17 mm error.
- The GPIO IRQ → user-space wakeup latency is typically 50–200 µs, even more under load.
- `gpiomon` from libgpiod has the same problem.

The honest options:

1. **PREEMPT_RT + threaded IRQ + ktime_get_ns** in driver: latency ~20 µs typical, ~150 µs worst case. → 5 mm worst-case error. Usable.
2. **Capture-input timer hardware** (a TIM block on the SoC configured to capture-compare on the ECHO edge). i.MX6ULL's GPT has this; very accurate (~10 ns), but requires writing a driver for the GPT capture mode — substantial work.
3. **Dedicated MCU helper** (an ESP32 or STM32 doing the timing, talking back to i.MX6ULL via I²C). The right answer for production systems.
4. **PRU/Cortex-M co-processor** on SoCs that have one (TI Sitara, NXP i.MX7/8). i.MX6ULL has Cortex-M4 in some variants; not in i.MX6ULL.

A from-scratch HC-SR04 driver for Linux that gives reasonable but unspectacular results:

```c
static int sr04_measure(struct sr04 *s, int *out_cm)
{
    ktime_t t_start, t_end;
    int err;

    /* TRIG high for 12 µs */
    gpiod_set_value(s->trig, 1);
    udelay(12);
    gpiod_set_value(s->trig, 0);

    /* Wait for ECHO high (busy-wait with timeout) */
    t_start = ktime_get();
    while (!gpiod_get_value(s->echo)) {
        if (ktime_to_us(ktime_sub(ktime_get(), t_start)) > 5000)
            return -ETIMEDOUT;
        cpu_relax();
    }
    t_start = ktime_get();    /* echo went high; reset clock */

    /* Wait for ECHO low */
    while (gpiod_get_value(s->echo)) {
        if (ktime_to_us(ktime_sub(ktime_get(), t_start)) > 30000)
            return -ETIMEDOUT;
        cpu_relax();
    }
    t_end = ktime_get();

    *out_cm = ktime_to_us(ktime_sub(t_end, t_start)) / 58;
    return 0;
}
```

The kernel busy-waits in two loops here. That keeps one CPU pinned for the full ~25 ms measurement. With PREEMPT_RT and a SCHED_FIFO priority, accuracy improves; without, it's still ±2 cm in the typical case.

In short: do not ship products with HC-SR04 wired directly to Linux GPIO. Either use a co-processor or pick a different sensor.

## 72.7  GP2Y0A — analog needs an ADC

GP2Y0A21YK outputs 0–3 V proportional to distance via a non-linear curve. You read with an ADC; in Linux that means an external I²C/SPI ADC (Ch 80) or the SoC's internal ADC.

i.MX6ULL has ADC1/ADC2 — 12-bit, ~1 MS/s, mainline driver `drivers/iio/adc/vf610_adc.c`. Wire GP2Y0A's output to an ADC channel; in IIO:

```sh
[root@pa-mini:~]# cat /sys/bus/iio/devices/iio:device0/in_voltage0_raw
1834
[root@pa-mini:~]# cat /sys/bus/iio/devices/iio:device0/in_voltage_scale
0.732421875
# → V = 1834 × 0.732 / 1000 = 1.343 V
```

User-space converts voltage to mm via the datasheet's piecewise table or polynomial. The non-linearity peaks ~80 mm; below that distance, voltage *decreases* again — a single voltage maps to two distances. **Always combine with a hard minimum bracket** (mechanically prevent the target from being closer than 100 mm).

This is the only case where the "driver" is just the IIO ADC driver; the sensor-specific math lives in user-space.

## 72.8  Now: the mainline driver

DT for VL53L0X:

```dts
&i2c1 {
    vl53l0x@29 {
        compatible = "st,vl53l0x";
        reg = <0x29>;
        interrupt-parent = <&gpio4>;
        interrupts = <10 IRQ_TYPE_EDGE_FALLING>;
        xshut-gpios = <&gpio4 11 GPIO_ACTIVE_LOW>;
    };
};
```

`xshut-gpios` is the chip's external-shutdown pin — letting the driver reset the chip if it gets stuck. The `interrupts` line is GPIO1 (the chip's data-ready IRQ) which lets the driver wake on sample-ready instead of polling.

Kernel config: `CONFIG_VL53L0X_I2C=y`.

For multi-chip setups (3 VL53L0X looking forward/left/right), the chips share I²C address 0x29 by default. Use XSHUT to hold all-but-one off at boot; each one is brought up sequentially and reassigned to a unique address before the next is woken. This sequencing happens in the driver via `xshut-gpios`.

## 72.9  Lab

1. **VL53L0X bring-up.** Wire it on I²C1 at 0x29. Verify probe in dmesg.
2. **Build and load `myvl53l0x.ko`.** Wave a hand at 100–500 mm; verify reasonable readings. Compare to ruler.
3. **Test extreme range.** At < 30 mm (below min range): observe garbage or zero. At > 2 m: similarly garbage. Add a sanity check in user-space.
4. **HC-SR04 attempt.** Wire one up. Write a user-space `gpiomon`-based reader. Compare its accuracy to a tape measure. Note variance under CPU load (`stress-ng &`).
5. **HC-SR04 with PREEMPT_RT.** Boot RT kernel. Retest. Variance should drop.
6. **GP2Y0A on ADC.** Wire to i.MX6ULL ADC1 channel; verify IIO ADC reading; write a polynomial-fit converter in user-space.
7. **Multi-VL53L0X.** Wire three on the same bus with separate XSHUT GPIOs. Use mainline driver; configure in DT; verify three `iio:device0/1/2` appear with separate addresses.

## 72.10  Pitfalls

- **VL53L0X under sunlight.** Range collapses to ~60 cm. If outdoor use is required, pick ultrasonic.
- **VL53L0X behind glass.** The chip's emitter reflects off the inner surface of the glass, and you read 0 mm forever. Use a recessed window or tilt the cover slightly.
- **VL53L0X minimum range.** Below 30 mm, readings are nonsense. Don't trust them.
- **HC-SR04 narrow targets.** Sound wave is ~25° cone; a thin pole reflects little — readings drop out. Hold a flat board for testing.
- **HC-SR04 echo from the floor.** In open setups, the floor reflects ultrasound; you read floor distance, not target. Angle the sensor slightly upward.
- **GP2Y0A double-valued zone.** Voltage isn't monotonic with distance below ~80 mm. Constrain mechanically.
- **GP2Y0A ambient light.** Strong IR (sunlight, incandescent bulb) saturates the receiver. Indoor use only.
- **VL53L0X I²C address conflict.** Default 0x29; if your board has another chip there, sequence with XSHUT.
- **Pulsing TRIG too fast on HC-SR04.** Min 60 ms between measurements. Faster = sensor is still listening for previous echo; readings get confused.

## 72.11  Going deeper

- **`drivers/iio/proximity/vl53l0x-i2c.c`** — production VL53L0X driver. Read the tuning blob comments.
- **STMicro VL53L0X API source** at <https://www.st.com/en/embedded-software/stsw-img005.html>. The full reference C implementation; ~10000 lines. Useful for understanding what the kernel driver's minimal init omits.
- **VL53L0X datasheet (STMicro DS33054)** — register summary, calibration overview.
- **HC-SR04 module documentation** (multiple vendors, all roughly the same) — timing diagram.
- **GP2Y0A21YK datasheet (Sharp)** — non-linear curve table (page 5).
- **`Documentation/iio/iio_devbuf.rst`** — for buffered ranging-over-time applications.

> Next chapter: **Chapter 73 — Magnetometer / compass.** From "how far" to "which way" — the magnetic vector of the Earth, the hard-iron and soft-iron calibration that nobody tells you about.
