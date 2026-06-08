---
chapter: 73
title: Magnetometer / compass (HMC5883L / QMC5883L / MMC5983MA)
part: VII — Device cookbook
estimated_pages: 20
status: draft
---

# Chapter 73 — Magnetometer / compass

> **What:** three I²C magnetometers: **Honeywell HMC5883L** (legacy classic, EOL but ubiquitous on hobbyist boards), **QST QMC5883L** (cheap clone with quirky register-set differences), **Memsic MMC5983MA** (modern low-noise). Most of this chapter is not driver code. It is calibration: **hard-iron and soft-iron calibration** — the universal "my compass points 23° wrong" problem and how to fix it.
>
> **Why:** any product that needs to know which way it's facing — drone, robot vacuum, AR headset, GPS-assisted navigation — needs a magnetometer. The math is simple. The *calibration* is what separates a useful compass from a useless one. Many products ship without calibration. their compass is off by 10–30°, and the IMU often gets blamed.
>
> **Focus:** Calibration runs in user-space. The driver's job is to deliver raw X/Y/Z in stable, scaled units. The driver reports raw `µT × scale`. user-space collects samples, fits an ellipsoid model, computes hard-iron (offset) and soft-iron (skew matrix). After applying the correction, raw 3-axis readings become Earth-magnetic-field vectors with < 1° error. Without calibration: 10–30° error is typical, depending on what's mounted near the sensor.


## 73.1  Chip comparison

| | Honeywell HMC5883L | QST QMC5883L | Memsic MMC5983MA |
|---|---|---|---|
| Range | ±0.88 / 1.3 / 1.9 / 2.5 / 4 / 4.7 / 5.6 / 8.1 Gauss | ±2 / 8 Gauss | ±8 Gauss |
| Resolution | 12-bit (in ±0.88 G) — ~0.7 mG/LSB | 16-bit — ~30 µG/LSB | 18-bit — ~0.06 mG/LSB |
| Noise floor | 2 mG RMS | 2 mG RMS | 0.4 mG RMS |
| Update rate | 0.75 – 75 Hz | 10/50/100/200 Hz | up to 1 kHz |
| I²C address | 0x1E | 0x0D | 0x30 |
| Reg map | "real" HMC layout | shifted (different from HMC) | new |
| Compatible? | yes mainline (`hmc5843_i2c.c`) | yes mainline (`qmc5883.c`) | yes (`mmc56x3.c`, recent kernels) |
| Lifecycle | EOL since 2018 | active (cheap China supply) | active |
| Volume price | $4–6 (eBay clones $1) | $0.50–1.50 | $4–6 |

Watch for this: every $1 eBay "HMC5883L" breakout is actually a *QMC5883L*. The pinout is similar. The protocol is different. If your "HMC5883L" doesn't probe at 0x1E, try QMC5883L at 0x0D.

**Pick guide:**
- **HMC5883L** for legacy maintenance only.
- **QMC5883L** for cheap projects. understand the register-set quirk.
- **MMC5983MA** for serious products needing low-noise + high-rate.

## 73.2  The physics — why magnetometers care so much about the environment

A magnetometer measures the **local magnetic field vector** in three orthogonal axes. The Earth produces ~50 µT (0.5 Gauss). local sources can be much stronger:

- **Hard iron** (permanent magnets, magnetised steel): adds a fixed DC offset to each axis.
- **Soft iron** (any ferromagnetic material): bends the field unevenly — different axes see different scale factors, axes may not be exactly orthogonal anymore.

If you take the chip out of the box and read raw, the data lies on a *3D ellipsoid* (not a sphere centered on origin) with the ellipsoid's center *offset* from origin. The ellipse-fitting calibration recovers two corrections:

- **Offset vector b**: subtract from each raw reading to center on origin (hard-iron).
- **3×3 transformation matrix A**: multiply the centered reading to make the ellipsoid a sphere (soft-iron).

Calibrated reading = A × (raw − b). The radius of the resulting sphere equals the magnitude of Earth's field (~50 µT) at your location. Heading angle from the X/Y components is then accurate to ~1°.

Without calibration: heading error of 10–30°, wrong enough to be useless for navigation.

## 73.3  Protocol — HMC5883L

Register map (the "real" HMC):

| Reg | Name | Purpose |
|-----|------|---------|
| 0x00 | CONFIG_A | Output rate, oversampling, measurement mode |
| 0x01 | CONFIG_B | Gain/range select |
| 0x02 | MODE | Continuous / single / idle |
| 0x03..0x08 | X_MSB, X_LSB, Z_MSB, Z_LSB, Y_MSB, Y_LSB | 16-bit signed values (note: Z then Y!) |
| 0x09 | STATUS | DATA_READY bit |
| 0x0A..0x0C | ID_A/B/C | "H43" identification |

Bring-up:

1. Read identification bytes (0x0A..0x0C) — should be 'H', '4', '3'.
2. Write CONFIG_A (0x00) = 0x70: 8-sample averaging, 15 Hz output rate.
3. Write CONFIG_B (0x01) = 0x20: gain ±1.3 Gauss, 1090 LSB/G.
4. Write MODE (0x02) = 0x00: continuous measurement.
5. After ~7 ms (per datasheet), data is ready. Read 6 bytes from 0x03.
6. Apply scale: `field_uT = raw / 1090 * 100` (to get µT from 1090 LSB/Gauss).

Each measurement read is 6 bytes back-to-back. note the **X/Z/Y order** (HMC's idiosyncrasy — most other chips do X/Y/Z).

## 73.4  Protocol — QMC5883L (different!)

QMC5883L uses a *different* register layout despite the similar-looking name and pinout. The differences that matter:

| Reg | QMC | HMC |
|-----|-----|-----|
| Data start | 0x00 | 0x03 |
| Status | 0x06 | 0x09 |
| Temperature | 0x07–0x08 | none |
| Control 1 | 0x09 | (different bits) |
| Control 2 | 0x0A | (different) |
| Period (refresh) | 0x0B | none |
| I²C address | 0x0D | 0x1E |

Mode bits in QMC's control register are also different. HMC5883L code does not work on a QMC5883L — the chip will simply not respond. This is the #1 reason "my $1 HMC5883L doesn't work" — it's not an HMC5883L.

QMC bring-up:

1. Write 0x0B = 0x01: set the "period" register (mandatory. chip won't work without it).
2. Write 0x09 = 0x1D: 200 Hz output rate, ±8 G range, 512 oversampling, continuous mode.
3. Read 6 bytes from 0x00 — X / Y / Z order, *little-endian* per axis (vs HMC's big-endian).

## 73.5  How the mainline drivers work

`drivers/iio/magnetometer/hmc5843_i2c.c` + `hmc5843_core.c` covers HMC5843 + HMC5883 + HMC5883L. Standard regmap-based pattern: read ID, configure, register IIO channels for `IIO_MAGN` with X/Y/Z modifiers.
> **MCU bridge:** Think of regmap like a typed wrapper around your read_reg() and write_reg() helpers, with caching, locking, and bus differences handled centrally.
**IIO** - Industrial I/O, Linux's subsystem for sensors, ADCs, DACs, and buffered sampled data.
**regmap** - a kernel helper that wraps register reads and writes over I2C, SPI, or MMIO.

`drivers/iio/magnetometer/qmc5883.c` is its own driver. can't share with HMC due to the register-set incompatibility.

`drivers/iio/magnetometer/mmc56x3.c` covers MMC5983MA and MMC56x3 family.

All three expose:

```
in_magn_x_raw
in_magn_y_raw
in_magn_z_raw
in_magn_scale            ← LSB to Gauss (or µT) conversion
sampling_frequency
sampling_frequency_available
```

User-space reads `raw × scale` to get the field in physical units. The driver doesn't do calibration — that's user-space's job.

## 73.6  Writing a QMC5883L driver from scratch

We'll target QMC5883L since it's what most people actually have. ~180 lines.

`myqmc5883.c`:

```c
#include <linux/init.h>
#include <linux/module.h>
#include <linux/i2c.h>
#include <linux/delay.h>
#include <linux/iio/iio.h>

#define REG_DATA      0x00
#define REG_STATUS    0x06
#define REG_CONTROL1  0x09
#define REG_CONTROL2  0x0A
#define REG_PERIOD    0x0B

struct myqmc {
    struct i2c_client *client;
    struct mutex lock;
};

static int mq_write(struct myqmc *m, u8 reg, u8 val)
{
    return i2c_smbus_write_byte_data(m->client, reg, val);
}

static int mq_read_block(struct myqmc *m, u8 reg, u8 *buf, int n)
{
    int r = i2c_smbus_read_i2c_block_data(m->client, reg, n, buf);
    return r == n ? 0 : (r < 0 ? r : -EIO);
}

static int mq_init(struct myqmc *m)
{
    int err;
    /* Soft reset */
    err = mq_write(m, REG_CONTROL2, 0x80);
    if (err) return err;
    msleep(20);
    /* Period register — mandatory magic value */
    err = mq_write(m, REG_PERIOD, 0x01);
    if (err) return err;
    /* CONTROL1: OSR=512(00), RNG=±8G(10), ODR=200Hz(11), MODE=continuous(01)
       binary: 0001_1101 = 0x1D */
    err = mq_write(m, REG_CONTROL1, 0x1D);
    if (err) return err;
    return 0;
}

static int mq_read_axes(struct myqmc *m, s16 axes[3])
{
    u8 buf[6];
    int err;

    err = mq_read_block(m, REG_DATA, buf, 6);
    if (err) return err;
    /* QMC: little-endian per axis */
    axes[0] = (s16)(buf[0] | (buf[1] << 8));   /* X */
    axes[1] = (s16)(buf[2] | (buf[3] << 8));   /* Y */
    axes[2] = (s16)(buf[4] | (buf[5] << 8));   /* Z */
    return 0;
}

static int mq_read_raw(struct iio_dev *idev,
                       struct iio_chan_spec const *chan,
                       int *val, int *val2, long mask)
{
    struct myqmc *m = iio_priv(idev);
    s16 axes[3];
    int err;

    switch (mask) {
    case IIO_CHAN_INFO_RAW:
        mutex_lock(&m->lock);
        err = mq_read_axes(m, axes);
        mutex_unlock(&m->lock);
        if (err) return err;
        switch (chan->channel2) {
        case IIO_MOD_X: *val = axes[0]; return IIO_VAL_INT;
        case IIO_MOD_Y: *val = axes[1]; return IIO_VAL_INT;
        case IIO_MOD_Z: *val = axes[2]; return IIO_VAL_INT;
        }
        return -EINVAL;
    case IIO_CHAN_INFO_SCALE:
        /* ±8 G range, 16-bit signed ⇒ 32768 LSB / 8 G = 4096 LSB/G
         * Convert to Tesla: 1 G = 100 µT, so 1 LSB = 100/4096 µT */
        *val = 0; *val2 = 24414;     /* ~24.4 nT/LSB */
        return IIO_VAL_INT_PLUS_NANO;
    }
    return -EINVAL;
}

#define MAGN_CH(axis) {                                             \
    .type = IIO_MAGN, .modified = 1, .channel2 = (axis),             \
    .info_mask_separate = BIT(IIO_CHAN_INFO_RAW),                    \
    .info_mask_shared_by_type = BIT(IIO_CHAN_INFO_SCALE),            \
    .scan_index = 0,                                                 \
    .scan_type = { .sign='s', .realbits=16, .storagebits=16,         \
                   .endianness=IIO_LE },                              \
}

static const struct iio_chan_spec mq_channels[] = {
    MAGN_CH(IIO_MOD_X),
    MAGN_CH(IIO_MOD_Y),
    MAGN_CH(IIO_MOD_Z),
};

static const struct iio_info mq_iio_info = {
    .read_raw = mq_read_raw,
};

static int mq_probe(struct i2c_client *client)
{
    struct iio_dev *idev;
    struct myqmc *m;
    int err;

    idev = devm_iio_device_alloc(&client->dev, sizeof(*m));
    if (!idev) return -ENOMEM;
    m = iio_priv(idev);
    m->client = client;
    mutex_init(&m->lock);

    err = mq_init(m);
    if (err) return dev_err_probe(&client->dev, err, "init failed\n");

    idev->name = "myqmc5883";
    idev->info = &mq_iio_info;
    idev->modes = INDIO_DIRECT_MODE;
    idev->channels = mq_channels;
    idev->num_channels = ARRAY_SIZE(mq_channels);

    return devm_iio_device_register(&client->dev, idev);
}

static const struct of_device_id mq_of_match[] = {
    { .compatible = "linuxlearn,myqmc5883" },
    { }
};
MODULE_DEVICE_TABLE(of, mq_of_match);

static const struct i2c_device_id mq_id[] = { { "myqmc5883", 0 }, { } };
MODULE_DEVICE_TABLE(i2c, mq_id);

static struct i2c_driver mq_driver = {
    .driver = {
        .name = "myqmc5883",
        .of_match_table = mq_of_match,
    },
    .probe = mq_probe,
    .id_table = mq_id,
};
module_i2c_driver(mq_driver);

MODULE_LICENSE("GPL");
```

DT:

```dts
&i2c1 {
    qmc5883@d {
        compatible = "linuxlearn,myqmc5883";
        reg = <0x0d>;
    };
};
```

Test:

```
[root@pa-mini:~]# insmod myqmc5883.ko
[root@pa-mini:~]# cat /sys/bus/iio/devices/iio:device0/in_magn_x_raw
1042
[root@pa-mini:~]# cat /sys/bus/iio/devices/iio:device0/in_magn_y_raw
-832
[root@pa-mini:~]# cat /sys/bus/iio/devices/iio:device0/in_magn_z_raw
-1620

# Calibrated heading (raw, no soft/hard-iron correction!):
[root@pa-mini:~]# awk "BEGIN { print atan2(-832, 1042) * 180 / 3.14159 }"
-38.6      ← "compass says 38.6° west of north"... but it's wrong because no calibration
```

## 73.7  Calibration — the part most products skip

A user-space calibration script collects samples while you slowly rotate the sensor in all 3D orientations (cover an imaginary sphere). The samples fall on an ellipsoid. From the ellipsoid you compute two things:

1. The **offset** (center of the ellipsoid) — hard-iron correction.
2. The **3x3 matrix** to rotate-and-scale the ellipsoid into a sphere — soft-iron correction.

A simple Python sketch:

```python
#!/usr/bin/env python3
import numpy as np, time, sys

def read_axis(axis):
    return int(open(f"/sys/bus/iio/devices/iio:device0/in_magn_{axis}_raw").read())

# Phase 1: collect ~1000 samples while the user rotates the sensor
samples = []
print("Rotate the sensor in all directions for 30 seconds...")
t0 = time.time()
while time.time() - t0 < 30:
    samples.append([read_axis(a) for a in "xyz"])
    time.sleep(0.03)
samples = np.array(samples, dtype=float)

# Phase 2: fit ellipsoid → extract center (hard-iron) and matrix (soft-iron)
# Simplified: just center + scale-axis-by-axis (ignores rotation)
center = (samples.max(axis=0) + samples.min(axis=0)) / 2
ranges = (samples.max(axis=0) - samples.min(axis=0)) / 2
avg_range = ranges.mean()
scale = avg_range / ranges    # per-axis scale

# Phase 3: save calibration
np.savez("magcal.npz", center=center, scale=scale)
print(f"Hard-iron offset: {center}")
print(f"Soft-iron scale:  {scale}")
```

Apply at runtime:

```python
cal = np.load("magcal.npz")
def read_calibrated():
    raw = np.array([read_axis(a) for a in "xyz"])
    return cal["scale"] * (raw - cal["center"])

import math
m = read_calibrated()
heading_deg = math.atan2(m[1], m[0]) * 180 / math.pi
if heading_deg < 0: heading_deg += 360
print(f"Heading: {heading_deg:.1f}°")
```

This is the *simplified* calibration. The proper version fits a full ellipsoid model (10 parameters: center 3 + axes 3 + rotation 3 + radius 1) using least-squares. see `Calibration of triaxial magnetometers` literature for the math. Libraries like **MotionCal** (Adafruit's GUI tool) do this. The resulting offset + 3x3 matrix is portable.

After proper calibration: heading error < 1°, indoor or out.

## 73.8  Mainline driver enablement

DT for QMC5883L:

```dts
&i2c1 {
    qmc5883@d {
        compatible = "qst,qmc5883l";
        reg = <0x0d>;
    };
};
```

For HMC5883L: `compatible = "honeywell,hmc5883l". reg = <0x1e>;`.

For MMC5983MA: `compatible = "memsic,mmc5983ma". reg = <0x30>;`.

The mainline drivers expose richer sysfs:
**sysfs** - a kernel-generated filesystem under /sys that exposes devices, drivers, and attributes.

```
[root@pa-mini:~]# ls /sys/bus/iio/devices/iio:device0/
in_magn_scale
in_magn_scale_available
in_magn_x_raw
in_magn_y_raw
in_magn_z_raw
sampling_frequency
sampling_frequency_available
```

Plus buffered capture via trigger (Ch 70) for high-rate logging.

## 73.9  Lab

1. **Probe.** `i2cdetect -y 1`. Check 0x0D and 0x1E. Whichever responds tells you what chip you have.
2. **Build and load `myqmc5883.ko`.** Read X/Y/Z while moving the sensor. verify values change.
3. **Compute uncalibrated heading.** Use atan2(Y, X) in radians, convert to degrees. Compare to a real compass. note the error.
4. **Run the calibration script.** Rotate the sensor for 30 seconds in all directions. Save offset + scale.
5. **Apply calibration.** Compute heading again. Compare to real compass. should now be within 5°.
6. **Move near a steel object.** Watch the heading change abruptly. Calibration done on the bench doesn't help if the in-product environment has different ferromagnetics — recalibrate in-place.
7. **Switch to mainline driver.** Verify same data flows. verify sampling_frequency_available works.

## 73.10  Pitfalls

- **Mistaking QMC5883L for HMC5883L.** #1 hobbyist trap. If it doesn't respond at 0x1E, try 0x0D.
- **No calibration.** Heading off by 10–30°. Calibrate, every time, in-place.
- **Calibration baked into firmware but environment changed.** A magnetometer on a robot calibrated on workbench, then mounted near a motor: recalibrate on the robot.
- **XY-only heading assumes the sensor is held level.** If the device can tilt, combine the magnetometer with the accelerometer and project the magnetic vector onto the horizontal plane. This is "tilt compensation" and it is mandatory for any device a user holds in their hand.
- **Buck converters within 5 cm.** Switching power supplies emit strong RF magnetic noise. Magnetometer reads garbage. Layout: keep mag far from switchers, or filter heavily.
- **Iron rich PCB substrate.** Cheap PCBs sometimes have ferromagnetic impurities. Affects calibration repeatability across boards.
- **Phone case magnets.** A 30-cm gap to a magnet still measures 100s of µT. Test your product in its real-world envelope.
- **Sensor saturation.** A strong nearby field (relay coil during switch) can saturate the magnetometer. readings stick at ±MAX for a while afterward. Verify range is wide enough.
- **Slow rotation during calibration.** Need to rotate slowly enough that samples cover the sphere uniformly. Too fast = patches uncovered = poor ellipsoid fit.

## 73.11  Going deeper

- **`drivers/iio/magnetometer/hmc5843_core.c`** + `hmc5843_i2c.c` — HMC family.
- **`drivers/iio/magnetometer/qmc5883.c`** — QMC.
- **`drivers/iio/magnetometer/mmc56x3.c`** — MMC.
- **HMC5883L datasheet (Honeywell)** — register layout.
- **QMC5883L datasheet (QST)** — for comparison with HMC. note the differences.
- **MMC5983MA datasheet (Memsic)** — set-reset cycle (a calibration improvement specific to MMC).
- **"Markovsky-Van Huffel ellipsoid fitting"** — the math behind proper soft-iron calibration.
- **MotionCal tool** by Adafruit — interactive calibration capture + analysis.
- **NOAA WMM (World Magnetic Model)** — for converting magnetic-north to true-north (declination varies by location and year).

> Next chapter: **Chapter 74 — Hall-effect & rotary position sensors.** Magnetic sensing applied to mechanical position — AS5048 (absolute rotary), A1324 (linear Hall), TLE5012 (high-rate angular).
