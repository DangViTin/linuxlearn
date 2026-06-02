---
chapter: 68
title: Light & color sensors (BH1750 / TSL2561 / VEML7700 / TCS34725)
part: VII — Device cookbook
estimated_pages: 22
status: draft
---

# Chapter 68 — Light & color sensors

> **What:** four I²C ambient-light sensors, dissected: **Rohm BH1750** (the simplest), **AMS TSL2561** (dual-channel for IR rejection), **Vishay VEML7700** (low-power, modern). Plus the bonus **AMS TCS34725** (RGB+clear color sensor). For each: protocol on the wire, the mainline IIO driver internals, and a from-scratch IIO driver for BH1750.
>
> **Why:** measuring light is harder than it looks. A photodiode's current is roughly proportional to incident photon flux, but the human eye's "lux" response is wavelength-weighted (CIE photopic curve). Different sensors solve this differently. BH1750 uses an analog filter. TSL2561 measures a broadband channel and an IR channel and subtracts. VEML7700 uses an integrated correction. After this chapter you can pick a sensor by its trade-offs, and write a driver for any of them.
>
> **Focus:** **integration time controls both noise floor and saturation point**. Light sensors are integrators — current × time → digital count. Long integration: low-light accuracy. Short integration: high-light range. Pick integration time for the range you care about. The IIO `integration_time` attribute exposes this directly.

## 68.1  Sensor comparison

| | Rohm BH1750 | AMS TSL2561 | Vishay VEML7700 | AMS TCS34725 |
|---|---|---|---|---|
| Channels | 1 (lux) | 2 (broad + IR) | 1 (corrected lux) | 4 (R, G, B, clear) |
| Resolution | 1 lx (low res) / 0.5 lx (high res) | 16-bit ADC × 2 | 16-bit | 16-bit × 4 |
| Range | 1–65535 lx | 0.1–40000 lx (auto-gain) | 0.05–120 klx | 0.04–1000 klx (gain-dep) |
| I²C address | 0x23 / 0x5C | 0x29 / 0x39 / 0x49 | 0x10 | 0x29 |
| Max bus clock | 400 kHz | 400 kHz | 400 kHz | 400 kHz |
| Integration time | 120 ms (high-res) / 16 ms (low-res) — fixed | 13.7 / 101 / 402 ms | 25 / 50 / 100 / 200 / 400 / 800 ms | 2.4 ms × 1..256 |
| Has IR rejection | analog filter (built-in) | computed (broad − IR) | analog filter | analog filter |
| Idle current | 1 µA | 0.6 µA | 0.5 µA | 0.5 µA |
| Volume price | $0.80–1.50 | $1.50–2.50 | $1.50–2.50 | $2.50–4.00 |
| Mainline driver | `bh1750.c` | `tsl2561.c` (in `staging`) | `veml7700.c` | `tcs3472.c` |

**Pick guide**:
- **BH1750**: simplest protocol, fine accuracy. Default for "I just need lux."
- **TSL2561**: when ambient has significant IR component (incandescent lighting, sunlight through glass).
- **VEML7700**: low-power product, or when you need wide dynamic range (klx + dark room).
- **TCS34725**: RGB color sensing (color matching, white-balance, paper-color detection).

## 68.2  Why lux is hard — the photometric response

Light meters claim "lux" — but a photodiode just produces current proportional to total photon flux. To convert photon flux to lux, you must weight by the eye's wavelength sensitivity (peaks at 555 nm green, drops to near-zero at 400 nm violet and 700 nm red, dead-zero in IR/UV).

Three sensor strategies:

1. **Optical filter** (BH1750, VEML7700, TCS34725 clear channel): a colored glass cover on the die that approximates the photopic curve. Cheap, fixed.
2. **Multi-channel + math** (TSL2561): one broadband channel (visible + IR) + one IR-only channel. Compute lux = `(broad − IR) × calibrated_curve`. More accurate, more software.
3. **R+G+B sensors** (TCS34725): measure each band; can compute lux *and* report color.

The mainline driver does whichever math the chip needs, and presents user-space with `in_illuminance_input` in lux. The user never sees the wavelength weighting; the driver does it. Just `cat in_illuminance_input` gives lux.

## 68.3  Protocol — BH1750 on the wire

BH1750 is unusual: it has no register map. You send single-byte **opcodes**, and the chip either acts or starts returning data.

| Opcode | Meaning |
|--------|---------|
| 0x00 | Power down |
| 0x01 | Power on |
| 0x07 | Reset (clears data register) |
| 0x10 | Continuous, high-res mode (1 lx, 120 ms) |
| 0x11 | Continuous, high-res mode 2 (0.5 lx, 120 ms) |
| 0x13 | Continuous, low-res mode (4 lx, 16 ms) |
| 0x20 | One-shot, high-res mode |
| 0x21 | One-shot, high-res mode 2 |
| 0x23 | One-shot, low-res mode |
| 0x4N | Change sensitivity (N = MTREG / 8; trim integration time) |

A typical sequence:

```
   START | 0x46 | 0x10 | STOP     (write opcode 0x10 — high-res continuous)
   ... wait 120 ms (per datasheet) ...
   START | 0x47 | D[hi] | D[lo] | STOP  (read 2 bytes — 16-bit count)
```

(`0x46` = 0x23<<1, write; `0x47` = 0x23<<1 | 1, read.)

To convert the 16-bit count to lux:

```
lux = count / 1.2   (datasheet typo-prone; check §"How to Calculate lx")
```

For the high-resolution mode 2 (0x11): `lux = count / (1.2 * 2)`.

Two bytes on the wire and one division — that is the whole protocol. It fits on a page.

## 68.4  How the mainline `bh1750` driver works

Source: `drivers/iio/light/bh1750.c` (~250 lines).

```c
/* Simplified */
struct bh1750_data {
    struct i2c_client *client;
    struct mutex lock;
    int mtreg;             /* sensitivity trim, default 69 */
    const struct bh1750_chip_info *chip_info;
};

struct bh1750_chip_info {
    u16 mtreg_min, mtreg_max, mtreg_default;
    int inc_per_us_lo, inc_per_us_hi;   /* timing constants */
};

static int bh1750_change_mtreg(struct bh1750_data *data, int mtreg)
{
    int err;
    /* MTREG is split across two registers (3 high bits + 5 low bits) */
    err = i2c_smbus_write_byte(data->client, BH1750_MTREG_HI | (mtreg >> 5));
    if (err) return err;
    return i2c_smbus_write_byte(data->client, BH1750_MTREG_LO | (mtreg & 0x1F));
}

static int bh1750_read(struct bh1750_data *data, int *val)
{
    u8 buf[2];
    int err, delay;

    err = i2c_smbus_write_byte(data->client, BH1750_ONE_SHOT_H);
    if (err) return err;

    /* Wait for measurement: typical 120ms, scales with mtreg */
    delay = data->chip_info->inc_per_us_hi * data->mtreg;
    usleep_range(delay, delay + 5000);

    err = i2c_master_recv(data->client, buf, 2);
    if (err < 0) return err;

    *val = (buf[0] << 8) | buf[1];
    return 0;
}

static int bh1750_read_raw(struct iio_dev *idev,
                           struct iio_chan_spec const *chan,
                           int *val, int *val2, long mask)
{
    struct bh1750_data *data = iio_priv(idev);
    int err;

    mutex_lock(&data->lock);
    switch (mask) {
    case IIO_CHAN_INFO_RAW:
        err = bh1750_read(data, val);
        if (err) goto out;
        err = IIO_VAL_INT;
        break;
    case IIO_CHAN_INFO_SCALE:
        /* Scale = mtreg-normalised count per lux */
        *val = 0;
        *val2 = data->chip_info->inc_per_us_hi * 1000 / data->mtreg;
        err = IIO_VAL_INT_PLUS_MICRO;
        break;
    }
out:
    mutex_unlock(&data->lock);
    return err;
}
```

User-space reads `in_illuminance_raw` (the raw 16-bit count) and `in_illuminance_scale` (the conversion factor). The actual lux = `raw * scale`.

Some mainline drivers add a third attribute `_processed` that returns the result already converted to lux × 1000 — saving user-space the math. BH1750's driver opts for the raw+scale pattern (more flexible).

## 68.5  Writing a BH1750 driver from scratch

`mybh1750.c`:

```c
#include <linux/init.h>
#include <linux/module.h>
#include <linux/i2c.h>
#include <linux/delay.h>
#include <linux/iio/iio.h>

#define OP_POWER_ON       0x01
#define OP_RESET          0x07
#define OP_ONESHOT_HIRES  0x20
#define OP_POWER_DOWN     0x00

struct mybh {
    struct i2c_client *client;
    struct mutex lock;
};

static int mb_measure(struct mybh *m, u16 *out_count)
{
    u8 buf[2];
    int err;

    err = i2c_smbus_write_byte(m->client, OP_ONESHOT_HIRES);
    if (err < 0) return err;

    msleep(180);   /* per datasheet: high-res = 120ms typ., 180 ms max */

    err = i2c_master_recv(m->client, buf, 2);
    if (err < 0) return err;
    if (err != 2) return -EIO;

    *out_count = (buf[0] << 8) | buf[1];
    return 0;
}

static int mb_read_raw(struct iio_dev *idev,
                       struct iio_chan_spec const *chan,
                       int *val, int *val2, long mask)
{
    struct mybh *m = iio_priv(idev);
    u16 count;
    int err;

    if (chan->type != IIO_LIGHT) return -EINVAL;

    switch (mask) {
    case IIO_CHAN_INFO_PROCESSED:
        mutex_lock(&m->lock);
        err = mb_measure(m, &count);
        mutex_unlock(&m->lock);
        if (err) return err;
        /* lux = count / 1.2 — report lux × 1000 */
        *val = ((u32)count * 1000) / 12 * 10;     /* count/1.2 × 1000 */
        return IIO_VAL_INT;
    case IIO_CHAN_INFO_SCALE:
        /* Raw is in 0.833 lx units; scale = 1/1.2 */
        *val = 0; *val2 = 833333;
        return IIO_VAL_INT_PLUS_MICRO;
    case IIO_CHAN_INFO_RAW:
        mutex_lock(&m->lock);
        err = mb_measure(m, &count);
        mutex_unlock(&m->lock);
        if (err) return err;
        *val = count;
        return IIO_VAL_INT;
    }
    return -EINVAL;
}

static const struct iio_chan_spec mb_channels[] = {
    {
        .type = IIO_LIGHT,
        .info_mask_separate = BIT(IIO_CHAN_INFO_PROCESSED)
                            | BIT(IIO_CHAN_INFO_RAW)
                            | BIT(IIO_CHAN_INFO_SCALE),
    },
};

static const struct iio_info mb_iio_info = {
    .read_raw = mb_read_raw,
};

static int mb_probe(struct i2c_client *client)
{
    struct iio_dev *idev;
    struct mybh *m;
    int err;

    idev = devm_iio_device_alloc(&client->dev, sizeof(*m));
    if (!idev) return -ENOMEM;
    m = iio_priv(idev);
    m->client = client;
    mutex_init(&m->lock);

    /* Power on, then sanity reset */
    err = i2c_smbus_write_byte(client, OP_POWER_ON);
    if (err < 0) return dev_err_probe(&client->dev, err, "power-on failed\n");
    err = i2c_smbus_write_byte(client, OP_RESET);
    if (err < 0) return dev_err_probe(&client->dev, err, "reset failed\n");
    msleep(10);

    idev->name = "mybh1750";
    idev->info = &mb_iio_info;
    idev->modes = INDIO_DIRECT_MODE;
    idev->channels = mb_channels;
    idev->num_channels = ARRAY_SIZE(mb_channels);

    return devm_iio_device_register(&client->dev, idev);
}

static void mb_remove(struct i2c_client *client)
{
    i2c_smbus_write_byte(client, OP_POWER_DOWN);
}

static const struct of_device_id mb_of_match[] = {
    { .compatible = "linuxlearn,mybh1750" },
    { }
};
MODULE_DEVICE_TABLE(of, mb_of_match);

static const struct i2c_device_id mb_id[] = {
    { "mybh1750", 0 },
    { }
};
MODULE_DEVICE_TABLE(i2c, mb_id);

static struct i2c_driver mb_driver = {
    .driver = {
        .name = "mybh1750",
        .of_match_table = mb_of_match,
    },
    .probe    = mb_probe,
    .remove   = mb_remove,
    .id_table = mb_id,
};
module_i2c_driver(mb_driver);

MODULE_LICENSE("GPL");
```

DT:

```dts
&i2c1 {
    bh1750@23 {
        compatible = "linuxlearn,mybh1750";
        reg = <0x23>;
    };
};
```

Build, load, test:

```
[root@pa-mini:~]# insmod mybh1750.ko
[root@pa-mini:~]# cat /sys/bus/iio/devices/iio:device0/in_illuminance_processed
410000        ← 410 lx (room with overhead lights)

# Cover the sensor:
[root@pa-mini:~]# cat /sys/bus/iio/devices/iio:device0/in_illuminance_processed
80           ← 0.08 lx (effectively dark)
```

Driver is ~120 lines. Bottom-up: opcode write, sleep, read 2 bytes, divide. The whole protocol fit in a paragraph in the datasheet.

## 68.6  TSL2561 — two channels, software fusion

TSL2561 has two photodiodes:
- **Channel 0**: broadband (visible + IR).
- **Channel 1**: IR-only.

The chip's claim to fame: subtract Ch1 from Ch0 to get the visible-only response. The math:

```
ratio = Ch1 / Ch0;

if (ratio < 0.5):   lux = 0.0304 * Ch0 - 0.062 * Ch0 * ratio^1.4
elif ratio < 0.61:  lux = 0.0224 * Ch0 - 0.031 * Ch1
elif ratio < 0.80:  lux = 0.0128 * Ch0 - 0.0153 * Ch1
elif ratio < 1.30:  lux = 0.00146 * Ch0 - 0.00112 * Ch1
else:               lux = 0
```

Piecewise polynomial. The coefficients come from chip characterisation across a range of light sources (incandescent, fluorescent, daylight) — the chip vendor has done the empirical work.

Mainline driver: `drivers/staging/iio/light/tsl2x7x.c` covers TSL2561, TSL2563, TSL2x7x family. Reads both channels, applies the formula, exposes `in_illuminance_input`.

## 68.7  VEML7700 — auto-ranging done right

VEML7700 has one channel with **6 integration times** (25 / 50 / 100 / 200 / 400 / 800 ms) and **4 gains** (1x, 2x, 1/4x, 1/8x). The driver can auto-range: start at low gain + short integration; if count saturates, reduce gain; if count is too low, increase integration time.

```c
/* drivers/iio/light/veml7700.c — simplified auto-range */
static int veml7700_read_lux(struct veml7700_data *data, int *lux)
{
    u16 raw;
    int err = veml7700_read_als(data, &raw);

    while (raw < 100 && data->it_idx < ITERATIONS_MAX) {
        data->it_idx++;
        veml7700_set_integration_time(data);
        err = veml7700_read_als(data, &raw);
    }
    while (raw > 50000 && data->it_idx > 0) {
        data->it_idx--;
        veml7700_set_integration_time(data);
        err = veml7700_read_als(data, &raw);
    }
    *lux = raw * veml7700_lux_per_count(data);
    return 0;
}
```

Why this matters: with auto-ranging, the chip covers 0.05 lx (dark hallway) to 120 klx (direct sunlight) — six decades — without saturating. Without auto-ranging, you'd have to pick a tradeoff at design time.

## 68.8  TCS34725 — RGB + clear

The bonus chip: color sensing. Four channels — R, G, B, and clear (broadband, similar to TSL2561 Ch0). Each is a 16-bit count over a programmable integration time.

```c
/* IIO channels for TCS34725 */
static const struct iio_chan_spec tcs3472_channels[] = {
    { .type = IIO_INTENSITY, .modified = 1, .channel2 = IIO_MOD_LIGHT_CLEAR,
      .info_mask_separate = BIT(IIO_CHAN_INFO_RAW) },
    { .type = IIO_INTENSITY, .modified = 1, .channel2 = IIO_MOD_LIGHT_RED,
      .info_mask_separate = BIT(IIO_CHAN_INFO_RAW) },
    { .type = IIO_INTENSITY, .modified = 1, .channel2 = IIO_MOD_LIGHT_GREEN,
      .info_mask_separate = BIT(IIO_CHAN_INFO_RAW) },
    { .type = IIO_INTENSITY, .modified = 1, .channel2 = IIO_MOD_LIGHT_BLUE,
      .info_mask_separate = BIT(IIO_CHAN_INFO_RAW) },
};
```

User-space sees `in_intensity_clear_raw`, `in_intensity_red_raw`, `_green_raw`, `_blue_raw`. To compute lux: use the clear channel + R/G/B-weighted formula in the datasheet. To compute color temperature (Kelvin): from R/G/B + clear, the McCamy approximation or the chromaticity-coords method.

Mainline driver: `drivers/iio/light/tcs3472.c`.

## 68.9  Now: enable the mainline drivers

DT for BH1750:

```dts
&i2c1 {
    bh1750@23 {
        compatible = "rohm,bh1750";
        reg = <0x23>;
    };
};
```

Kernel config: `CONFIG_BH1750=y`. Boot:

```
[root@pa-mini:~]# cat /sys/bus/iio/devices/iio:device0/name
bh1750
[root@pa-mini:~]# cat /sys/bus/iio/devices/iio:device0/in_illuminance_raw
493
[root@pa-mini:~]# cat /sys/bus/iio/devices/iio:device0/in_illuminance_scale
0.833333
# → lux = 493 × 0.833 = 410 lx
```

For TSL2561 / VEML7700 / TCS34725: substitute the appropriate compatible:

```dts
tsl2561@39 { compatible = "amstaos,tsl2561"; reg = <0x39>; };
veml7700@10 { compatible = "vishay,veml7700"; reg = <0x10>; };
tcs34725@29 { compatible = "amstaos,tcs34725"; reg = <0x29>; };
```

## 68.10  Lab

1. **Detect.** `i2cdetect -y 1`. BH1750 at 0x23 if ADDR low.
2. **From scratch.** Build `mybh1750.ko`. Read in different lighting conditions: room, sunlight through window, covered with hand.
3. **Compare against a phone app.** Most smartphone light-meter apps are accurate to ±20 %. Cross-check.
4. **Add gain control.** Modify `mybh1750.c` to expose `_integration_time` as a writable IIO attribute. Verify writing 1 / 0.5 / 2 changes the effective integration time.
5. **Switch to mainline.** Unload yours, use `rohm,bh1750`. Verify same scale + raw.
6. **TSL2561 (if available).** Configure the chip; read both channels; implement the piecewise formula in user-space; cross-check against BH1750 under fluorescent light (where TSL2561's IR rejection should give a tighter lux number).
7. **TCS34725 color match.** With the bonus chip, hold a red object, a green object, a blue object in front; verify the R/G/B counts respond correspondingly.

## 68.11  Pitfalls

- **BH1750 reading times wrong.** Datasheet says 120 ms typical, 180 ms max for high-res. Use 180 ms to be safe; or check the busy-flag (chip will NACK reads during measurement).
- **TSL2561 saturated**. If Ch0 or Ch1 is 0xFFFF, the chip is saturated. Either drop the gain (HIGH → LOW) or reduce integration time. Auto-range or the user will report "lux = 0" in bright sun.
- **Sensor cover material.** Glass with strong IR-cut coating distorts readings. Use clear glass or a known-spec optical window.
- **Tinted enclosures.** Dark-tinted plastic over the sensor cuts visible light unevenly. Calibrate against a known reference *with the enclosure in place*.
- **Direct light vs reflected.** A sensor pointed at the sky reads sky brightness, not ambient. For "what's the light on my desk?" point at the desk, or use a diffuser cover.
- **VEML7700 auto-range hysteresis.** Switching back and forth between integration times causes flicker in the reported lux. The mainline driver hysteresis suppresses this; rolling your own, leave deadbands.
- **TCS34725 IR contamination.** Even with IR-rejection filter, sunlight's high R-channel reading isn't pure red — there's IR leak. For color-match work, use indoor LED light.
- **Integration time ≠ sampling rate.** If you read every 100 ms but integration is 800 ms, you get the same value four times in a row. Match the cadence.

## 68.12  Going deeper

- **`drivers/iio/light/bh1750.c`** — the production driver.
- **`drivers/staging/iio/light/tsl2x7x.c`** — TSL2561/2563/2x7x family.
- **`drivers/iio/light/veml7700.c`** — auto-ranging.
- **`drivers/iio/light/tcs3472.c`** — RGB + clear.
- **BH1750 datasheet (Rohm)** — opcode table on p.5.
- **TSL2561 datasheet (AMS)** — lux formula on p.16.
- **VEML7700 datasheet (Vishay)** — page on gain/integration trade-offs.
- **TCS34725 datasheet (AMS)** — color-temperature derivation formula in app note AN1078.
- **CIE photopic luminosity function** — the eye-response curve all these sensors approximate.

> Next chapter: **Chapter 69 — Air quality, gas, particulate matter.** Three classes of "what's in the air" sensor: NDIR CO₂ (SCD30), metal-oxide eCO₂/TVOC (CCS811), and laser-scattering PM (PMS5003). Different bus, different protocol, different physics, different accuracy stories.
