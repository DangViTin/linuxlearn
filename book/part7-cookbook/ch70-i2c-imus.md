---
chapter: 70
title: I²C IMUs (MPU6050 / MPU9250 / ICM-20948)
part: VII — Device cookbook
estimated_pages: 28
status: draft
---

# Chapter 70 — I²C IMUs

> **What:** three I²C inertial measurement units, dissected: **InvenSense MPU6050** (6-axis, the classic), **MPU9250** (9-axis with an AK8963 magnetometer hiding inside via I²C-master mode), **ICM-20948** (modern 9-axis, replaced MPU9250). For each: register map, the sampling-rate trade-offs, the IIO **trigger + buffer** mechanism for high-rate capture, and a from-scratch MPU6050 driver including IIO buffer support.
> **Why:** IMUs are everywhere — drones, e-scooters, VR headsets, fitness wearables, industrial vibration monitors. They're also the canonical IIO example of *high-rate buffered capture*: a 1 kHz IMU produces 6–9 measurements per sample, and one sysfs read per sample isn't going to work. The IIO trigger/buffer framework is the answer, and once you understand it you can use it for any high-rate sensor.
> **Focus:** **trigger + buffer is the path to thousands of samples per second**. A `trigger` (timer or IRQ) tells the driver "now"; the driver atomically samples *all enabled channels*; pushes the coordinated sample into a kfifo; user-space drains the kfifo from `/dev/iio:deviceN`. The whole pipeline is asynchronous and survives microsecond jitter.

## 70.1  Chip comparison

| | MPU6050 | MPU9250 | ICM-20948 |
|---|---|---|---|
| Accel | 3-axis, 16-bit, ±2/4/8/16 g | 3-axis, 16-bit, ±2/4/8/16 g | 3-axis, 16-bit, ±2/4/8/16 g |
| Gyro | 3-axis, 16-bit, ±250/500/1k/2k °/s | 3-axis, 16-bit, ±250/500/1k/2k °/s | 3-axis, 16-bit, ±250/500/1k/2k °/s |
| Magnetometer | none | AK8963 internal (3-axis, ±4900 µT) | AK09916 internal (3-axis, ±4900 µT) |
| Max ODR | 8 kHz (gyro), 1 kHz (accel) | 8 kHz / 4 kHz | 9 kHz / 4.5 kHz |
| FIFO | 1 kB | 1 kB | 4 kB |
| I²C address | 0x68 / 0x69 | 0x68 / 0x69 | 0x68 / 0x69 |
| Max bus clock | 400 kHz | 400 kHz | 400 kHz (Fast mode), 1 MHz (Fast+) |
| Onboard DMP | yes (closed-source firmware blob) | yes | yes (newer firmware) |
| Idle current | 0.4 mA | 3.5 mA (mag on) | 1.2 mA |
| Lifecycle | EOL but ubiquitous on hobbyist boards | EOL since 2018 | active |
| Volume price | $1.50–2.50 | $3–6 | $4–8 |
| Mainline driver | `inv_mpu6050_*.c` family | same | same |

**Pick guide:**
- **MPU6050**: cheap hobby projects, learning, where 6-axis is enough.
- **MPU9250**: legacy product maintenance — don't design in new.
- **ICM-20948**: new designs needing magnetometer. Same I²C/SPI register model as MPU family (InvenSense legacy compatibility).

## 70.2  Why "9-axis" and what the magnetometer adds

A 6-axis IMU (accel + gyro) can compute **orientation drift-free in roll and pitch** by sensing gravity. But it has *no absolute reference for yaw* — rotate around the vertical axis and the gyro integration drifts seconds-of-arc per second.

Adding a magnetometer gives an Earth-field reference: the chip measures the geomagnetic vector (~50 µT, pointing roughly north + downward). Combined with the accel's gravity vector, the fusion algorithm can pin all three rotational axes. The result: **drift-free orientation in all three axes**.

For drones, AR/VR, robotic-arm control: 9-axis is mandatory. For tap-detection, fall-detection, vibration logging: 6-axis is enough.

## 70.3  Protocol — MPU6050 register map

Register layout (most-used subset):

| Reg | Name | Purpose |
|-----|------|---------|
| 0x6B | PWR_MGMT_1 | Reset, sleep, clock source select |
| 0x6C | PWR_MGMT_2 | Per-axis disable |
| 0x19 | SMPLRT_DIV | Sample rate = gyro_output / (1 + DIV) |
| 0x1A | CONFIG | DLPF (digital low-pass filter) config |
| 0x1B | GYRO_CONFIG | Full-scale range select |
| 0x1C | ACCEL_CONFIG | Full-scale range select |
| 0x38 | INT_ENABLE | Interrupt mask |
| 0x3A | INT_STATUS | Interrupt status (data-ready bit) |
| 0x3B..0x40 | ACCEL_OUT (X/Y/Z, 2 bytes each) | 16-bit signed accel |
| 0x41..0x42 | TEMP_OUT | Die temperature |
| 0x43..0x48 | GYRO_OUT (X/Y/Z, 2 bytes each) | 16-bit signed gyro |
| 0x75 | WHO_AM_I | Always 0x68 |
| 0x37 | INT_PIN_CFG | Bypass enable (for MPU9250 magnetometer access) |

To read a single 6-axis sample:

```
   Host: START | 0xD0 | 0x3B | START | 0xD1 | (14 bytes) | STOP
                              ↑
   (write reg pointer = 0x3B, repeated-start, read 14 bytes:
    AX_h AX_l AY_h AY_l AZ_h AZ_l TMP_h TMP_l GX_h GX_l GY_h GY_l GZ_h GZ_l)
```

Each value is 16-bit signed, big-endian. To convert raw to physical units:

```c
/* Accel: ±2g full scale ⇒ 16384 LSB/g */
accel_g_x = (s16)((raw[0] << 8) | raw[1]) / 16384.0;

/* Gyro: ±250 °/s ⇒ 131 LSB / (°/s) */
gyro_dps_x = (s16)((raw[8] << 8) | raw[9]) / 131.0;

/* Temperature: see datasheet eq. */
temp_c = (s16)((raw[6] << 8) | raw[7]) / 340.0 + 36.53;
```

Bring-up sequence:

1. Read WHO_AM_I (0x75); verify it returns 0x68 (or 0x71 for MPU9250, 0xEA for ICM-20948).
2. Write 0x80 to PWR_MGMT_1: soft reset.
3. Wait ~100 ms.
4. Write 0x00 to PWR_MGMT_1: wake from sleep, internal 8 MHz clock.
5. Write 0x01 to PWR_MGMT_1: wake, PLL with X-gyro reference (lower noise).
6. Configure DLPF, sample rate, ranges as needed.
7. Read at the configured cadence — or set up an IRQ on data-ready (bit 0 of INT_STATUS).

## 70.4  IIO trigger + buffer — the high-rate model

For a 1 kHz IMU, a one-sample-per-sysfs-read loop hits the syscall path 1000 times per second per axis. That's ~30 µs per sysfs read × 6 axes × 1000 Hz = 18 % of one CPU just on the syscall overhead. Untenable.

The IIO solution: **triggers** + **buffers**.

```
                 (timer fires every 1 ms, or data-ready GPIO IRQ)
                              │
                              ▼
                  ┌─────────────────────┐
                  │       Trigger       │
                  │   ("now is the      │
                  │    moment to sample")│
                  └──────────┬──────────┘
                             │
                  ┌──────────▼──────────┐
                  │  Driver's trigger    │
                  │  handler (atomic):    │
                  │   - read all enabled │
                  │     channels in one  │
                  │     I²C burst         │
                  │   - push tuple into  │
                  │     kfifo buffer     │
                  └──────────┬──────────┘
                             │
                  ┌──────────▼──────────┐
                  │   kfifo (in driver)  │
                  │   ring buffer        │
                  └──────────┬──────────┘
                             │
                  ┌──────────▼──────────┐
                  │  /dev/iio:deviceN    │
                  │  chardev — user-      │
                  │  space drains via    │
                  │  read(2) / poll(2)    │
                  └─────────────────────┘
```

A user-space app does:

```sh
# Enable channels to be captured
echo 1 > /sys/bus/iio/devices/iio:device0/scan_elements/in_accel_x_en
echo 1 > .../in_accel_y_en
echo 1 > .../in_accel_z_en
echo 1 > .../in_anglvel_x_en
echo 1 > .../in_anglvel_y_en
echo 1 > .../in_anglvel_z_en

# Configure buffer
echo 512 > /sys/bus/iio/devices/iio:device0/buffer/length

# Bind a trigger
echo "hrtimer-0" > .../trigger/current_trigger
echo 1000 > /sys/bus/iio/devices/trigger0/sampling_frequency

# Start streaming
echo 1 > .../buffer/enable

# Drain (each sample = 6 × 2 bytes = 12 bytes; 12000 B/s)
dd if=/dev/iio:device0 of=samples.bin bs=12 count=10000
```

10 000 atomic samples land in `samples.bin`. The data layout matches the order of `scan_elements/*_en` toggled on. Each sample's bytes are packed; user-space parses with the driver-declared `scan_type` (bits per sample, byte order).

### Triggers

A *trigger* is its own IIO object. Two common kinds:

- **hrtimer**: kernel high-resolution timer firing at a programmable rate. Drift-free, suitable for steady sampling. Backed by `drivers/iio/trigger/iio-trig-hrtimer.c`.
- **interrupt**: an IRQ on a GPIO connected to the chip's INT pin (the chip asserts when it has data ready). Synchronized exactly to the chip's sample clock.

Drivers may also publish their *own* trigger ("data-ready trigger") that consumer code can bind. The MPU6050 driver does this — its INT pin's IRQ becomes an IIO trigger named `mpu6050-dev0`, and you can bind it to its own buffer or to *another* device's buffer (sync sampling across chips).

## 70.5  How the mainline `inv_mpu6050` driver is structured

Source: `drivers/iio/imu/inv_mpu6050/` — 5 files, ~3000 lines total. Covers MPU6050, MPU6500, MPU9150, MPU9250, ICM20608, ICM20602, ICM20690 (the entire InvenSense MPU family).

```
drivers/iio/imu/inv_mpu6050/
├── inv_mpu_core.c     ← chip-agnostic IIO logic
├── inv_mpu_ring.c     ← buffer/trigger callbacks
├── inv_mpu_trigger.c  ← data-ready trigger
├── inv_mpu_i2c.c      ← I²C bus glue (creates regmap)
├── inv_mpu_spi.c      ← SPI bus glue (creates regmap)
```

### Probe walk

```c
/* Simplified */
static int inv_mpu_i2c_probe(struct i2c_client *client)
{
    struct regmap *regmap = devm_regmap_init_i2c(client, &inv_mpu_regmap_config);
    return inv_mpu_core_probe(regmap, client->irq, name,
                              inv_mpu_i2c_aux_bus_setup, /* aux bus for mag */
                              chip_type);
}

/* inv_mpu_core_probe (~simplified): */
static int inv_mpu_core_probe(struct regmap *regmap, int irq, const char *name,
                              int (*setup_aux)(...), int chip_type)
{
    struct iio_dev *indio_dev;
    struct inv_mpu6050_state *st;

    indio_dev = devm_iio_device_alloc(...);
    st = iio_priv(indio_dev);
    st->map = regmap;

    /* Identify */
    err = regmap_read(regmap, INV_MPU6050_REG_WHO_AM_I, &whoami);
    if (whoami != expected) return -ENODEV;

    /* Initial chip config: reset, set clock source, defaults */
    err = inv_mpu6050_init_config(indio_dev);

    /* Optional: bring up auxiliary I²C bus to talk to a magnetometer */
    if (setup_aux) setup_aux(st);

    /* Set up trigger + buffer infrastructure */
    err = devm_iio_triggered_buffer_setup(...,
              iio_pollfunc_store_time,        /* pre-handler */
              inv_mpu6050_read_fifo,           /* main handler */
              &inv_mpu6050_buffer_setup_ops);

    /* Set up the data-ready trigger */
    err = inv_mpu6050_probe_trigger(indio_dev);

    /* Register */
    indio_dev->channels = inv_mpu_channels;
    indio_dev->num_channels = ARRAY_SIZE(inv_mpu_channels);
    indio_dev->info = &mpu_info;
    return devm_iio_device_register(...);
}
```

### Channel definitions

```c
#define INV_MPU6050_CHAN(_type, _channel2, _index) {  \
    .type = (_type),                                   \
    .modified = 1,                                     \
    .channel2 = (_channel2),                           \
    .info_mask_separate = BIT(IIO_CHAN_INFO_RAW),       \
    .info_mask_shared_by_type = BIT(IIO_CHAN_INFO_SCALE), \
    .scan_index = (_index),                             \
    .scan_type = {                                     \
        .sign = 's', .realbits = 16, .storagebits = 16,\
        .shift = 0, .endianness = IIO_BE,              \
    },                                                 \
}

static const struct iio_chan_spec inv_mpu_channels[] = {
    IIO_CHAN_SOFT_TIMESTAMP(0),
    {  /* gyro temp */
        .type = IIO_TEMP, .info_mask_separate = BIT(IIO_CHAN_INFO_RAW) | ...,
        .scan_index = -1,
    },
    INV_MPU6050_CHAN(IIO_ANGL_VEL, IIO_MOD_X, 1),
    INV_MPU6050_CHAN(IIO_ANGL_VEL, IIO_MOD_Y, 2),
    INV_MPU6050_CHAN(IIO_ANGL_VEL, IIO_MOD_Z, 3),
    INV_MPU6050_CHAN(IIO_ACCEL,    IIO_MOD_X, 4),
    INV_MPU6050_CHAN(IIO_ACCEL,    IIO_MOD_Y, 5),
    INV_MPU6050_CHAN(IIO_ACCEL,    IIO_MOD_Z, 6),
};
```

`scan_index` is the in-buffer position. `scan_type` tells user-space "16-bit signed, big-endian." `IIO_CHAN_SOFT_TIMESTAMP(0)` adds a 64-bit timestamp per sample — invaluable for time-aligned analysis.

### The trigger handler

```c
static irqreturn_t inv_mpu6050_read_fifo(int irq, void *p)
{
    struct iio_poll_func *pf = p;
    struct iio_dev *indio_dev = pf->indio_dev;
    struct inv_mpu6050_state *st = iio_priv(indio_dev);
    size_t bytes_per_datum, fifo_count;

    mutex_lock(&st->lock);

    /* Read the FIFO count register to see how many samples are queued */
    regmap_bulk_read(st->map, INV_MPU6050_REG_FIFO_COUNT_H, &fifo_count, 2);
    fifo_count = be16_to_cpu(fifo_count);
    bytes_per_datum = compute_packet_size(st);

    while (fifo_count >= bytes_per_datum) {
        u8 sample_buf[INV_MPU6050_OUTPUT_DATA_SIZE];
        regmap_noinc_read(st->map, INV_MPU6050_REG_FIFO_R_W, sample_buf, bytes_per_datum);

        iio_push_to_buffers_with_timestamp(indio_dev, sample_buf,
                                            iio_get_time_ns(indio_dev));
        fifo_count -= bytes_per_datum;
    }

    mutex_unlock(&st->lock);
    iio_trigger_notify_done(indio_dev->trig);
    return IRQ_HANDLED;
}
```

Each trigger event: read FIFO count, drain N samples from FIFO via a single bulk I²C read, push each into the IIO buffer with a kernel timestamp. The driver doesn't care whether the trigger came from a timer or from the chip's own data-ready IRQ — same handler either way.

### Two-stage IRQ path for hardware trigger

When the data-ready trigger is bound:

1. Chip's INT pin goes high → GPIO IRQ on i.MX6ULL.
2. Kernel calls the IIO trigger's primary handler (the chip driver's "I have data" callback).
3. Primary handler returns `IRQ_WAKE_THREAD`; the trigger framework schedules the trigger handler (above) as a kernel thread.
4. Thread runs at SCHED_FIFO priority, drains FIFO, pushes to buffer.

So even at 1 kHz, the CPU only wakes once per sample — and only briefly. Compare to `read()` polling: 30 µs per syscall × 6 channels = 180 µs of CPU per sample (18 %). With trigger+buffer: maybe 5 µs per sample (0.5 %).

## 70.6  Writing an MPU6050 driver from scratch (with buffer support)

Goal: a working IIO driver that supports both sysfs reads (`in_accel_x_raw`) AND triggered buffered capture (via `/dev/iio:device0`). ~350 lines.

`mympu6050.c`:

```c
#include <linux/init.h>
#include <linux/module.h>
#include <linux/i2c.h>
#include <linux/delay.h>
#include <linux/iio/iio.h>
#include <linux/iio/buffer.h>
#include <linux/iio/triggered_buffer.h>
#include <linux/iio/trigger_consumer.h>

#define REG_SMPLRT_DIV   0x19
#define REG_CONFIG       0x1A
#define REG_GYRO_CONFIG  0x1B
#define REG_ACCEL_CONFIG 0x1C
#define REG_INT_ENABLE   0x38
#define REG_INT_STATUS   0x3A
#define REG_ACCEL_XOUT_H 0x3B
#define REG_GYRO_XOUT_H  0x43
#define REG_PWR_MGMT_1   0x6B
#define REG_WHO_AM_I     0x75

#define WHO_AM_I_VAL     0x68

struct mympu {
    struct i2c_client *client;
    struct mutex lock;
};

/* === Low-level I²C ops === */

static int mp_read_block(struct mympu *m, u8 reg, u8 *buf, int n)
{
    int r = i2c_smbus_read_i2c_block_data(m->client, reg, n, buf);
    return r == n ? 0 : (r < 0 ? r : -EIO);
}

static int mp_write_byte(struct mympu *m, u8 reg, u8 val)
{
    return i2c_smbus_write_byte_data(m->client, reg, val);
}

/* === Bring-up === */

static int mp_init(struct mympu *m)
{
    int err;

    /* Reset */
    err = mp_write_byte(m, REG_PWR_MGMT_1, 0x80); if (err) return err;
    msleep(100);
    /* Wake, PLL with X-gyro ref */
    err = mp_write_byte(m, REG_PWR_MGMT_1, 0x01); if (err) return err;
    /* Sample rate = 1 kHz / (1+99) = 10 Hz initially (we'll override) */
    err = mp_write_byte(m, REG_SMPLRT_DIV, 99);   if (err) return err;
    /* DLPF: 44 Hz BW (CONFIG bits 2:0 = 3) */
    err = mp_write_byte(m, REG_CONFIG, 0x03);      if (err) return err;
    /* Gyro ±250 °/s */
    err = mp_write_byte(m, REG_GYRO_CONFIG, 0x00); if (err) return err;
    /* Accel ±2g */
    err = mp_write_byte(m, REG_ACCEL_CONFIG, 0x00); if (err) return err;

    return 0;
}

/* === Single-sample reads (for sysfs INFO_RAW) === */

static int mp_read_accel_axis(struct mympu *m, int axis, s16 *val)
{
    u8 buf[2];
    int err = mp_read_block(m, REG_ACCEL_XOUT_H + axis*2, buf, 2);
    if (err) return err;
    *val = (s16)((buf[0] << 8) | buf[1]);
    return 0;
}

static int mp_read_gyro_axis(struct mympu *m, int axis, s16 *val)
{
    u8 buf[2];
    int err = mp_read_block(m, REG_GYRO_XOUT_H + axis*2, buf, 2);
    if (err) return err;
    *val = (s16)((buf[0] << 8) | buf[1]);
    return 0;
}

/* === IIO read_raw === */

static int mp_read_raw(struct iio_dev *idev,
                       struct iio_chan_spec const *chan,
                       int *val, int *val2, long mask)
{
    struct mympu *m = iio_priv(idev);
    s16 raw;
    int err;

    switch (mask) {
    case IIO_CHAN_INFO_RAW:
        mutex_lock(&m->lock);
        if (chan->type == IIO_ACCEL)
            err = mp_read_accel_axis(m, chan->scan_index - 1, &raw);
        else if (chan->type == IIO_ANGL_VEL)
            err = mp_read_gyro_axis(m, chan->scan_index - 4, &raw);
        else err = -EINVAL;
        mutex_unlock(&m->lock);
        if (err) return err;
        *val = raw;
        return IIO_VAL_INT;
    case IIO_CHAN_INFO_SCALE:
        /* Accel: 1/16384 g/LSB = 9.80665 / 16384 m/s² per LSB */
        /* Gyro: 1/131 °/s/LSB = (π/180) / 131 rad/s per LSB */
        if (chan->type == IIO_ACCEL) {
            *val = 0; *val2 = 598;     /* 9.80665/16384 ≈ 0.000598 m/s²/LSB */
            return IIO_VAL_INT_PLUS_MICRO;
        } else {
            *val = 0; *val2 = 133;     /* π/180/131 ≈ 0.000133 rad/s/LSB */
            return IIO_VAL_INT_PLUS_MICRO;
        }
    }
    return -EINVAL;
}

/* === Channel table === */

#define ACCEL_CH(axis, idx) {                                       \
    .type = IIO_ACCEL, .modified = 1, .channel2 = (axis),            \
    .info_mask_separate = BIT(IIO_CHAN_INFO_RAW),                    \
    .info_mask_shared_by_type = BIT(IIO_CHAN_INFO_SCALE),            \
    .scan_index = (idx),                                             \
    .scan_type = { .sign='s', .realbits=16, .storagebits=16,         \
                   .endianness=IIO_BE },                              \
}
#define GYRO_CH(axis, idx) {                                        \
    .type = IIO_ANGL_VEL, .modified = 1, .channel2 = (axis),         \
    .info_mask_separate = BIT(IIO_CHAN_INFO_RAW),                    \
    .info_mask_shared_by_type = BIT(IIO_CHAN_INFO_SCALE),            \
    .scan_index = (idx),                                             \
    .scan_type = { .sign='s', .realbits=16, .storagebits=16,         \
                   .endianness=IIO_BE },                              \
}

static const struct iio_chan_spec mp_channels[] = {
    ACCEL_CH(IIO_MOD_X, 1),
    ACCEL_CH(IIO_MOD_Y, 2),
    ACCEL_CH(IIO_MOD_Z, 3),
    GYRO_CH (IIO_MOD_X, 4),
    GYRO_CH (IIO_MOD_Y, 5),
    GYRO_CH (IIO_MOD_Z, 6),
    IIO_CHAN_SOFT_TIMESTAMP(7),
};

/* === Buffered capture: trigger handler reads 14 bytes (accel+temp+gyro), pushes 12 bytes (no temp) === */

static irqreturn_t mp_trigger_handler(int irq, void *p)
{
    struct iio_poll_func *pf = p;
    struct iio_dev *idev = pf->indio_dev;
    struct mympu *m = iio_priv(idev);
    u8 raw[14];
    u8 sample[12 + 8];    /* 6 channels × 2 bytes + 64-bit timestamp */
    int err;

    mutex_lock(&m->lock);
    err = mp_read_block(m, REG_ACCEL_XOUT_H, raw, 14);
    mutex_unlock(&m->lock);

    if (err == 0) {
        /* Repack: accel 6 bytes, then gyro 6 bytes (skip temp at raw[6..7]) */
        memcpy(sample,     raw,        6);     /* accel X/Y/Z */
        memcpy(sample + 6, raw + 8,    6);     /* gyro X/Y/Z */
        iio_push_to_buffers_with_timestamp(idev, sample,
                                            iio_get_time_ns(idev));
    }

    iio_trigger_notify_done(idev->trig);
    return IRQ_HANDLED;
}

static const struct iio_info mp_iio_info = {
    .read_raw = mp_read_raw,
};

/* === Probe / Remove === */

static int mp_probe(struct i2c_client *client, const struct i2c_device_id *id)
{
    struct iio_dev *idev;
    struct mympu *m;
    int who, err;

    idev = devm_iio_device_alloc(&client->dev, sizeof(*m));
    if (!idev) return -ENOMEM;
    m = iio_priv(idev);
    m->client = client;
    mutex_init(&m->lock);

    who = i2c_smbus_read_byte_data(client, REG_WHO_AM_I);
    if (who < 0) return who;
    if (who != WHO_AM_I_VAL)
        return dev_err_probe(&client->dev, -ENODEV,
                             "unexpected WHO_AM_I 0x%02x\n", who);

    err = mp_init(m);
    if (err) return err;

    idev->name     = "mympu6050";
    idev->info     = &mp_iio_info;
    idev->modes    = INDIO_DIRECT_MODE | INDIO_BUFFER_TRIGGERED;
    idev->channels = mp_channels;
    idev->num_channels = ARRAY_SIZE(mp_channels);

    err = devm_iio_triggered_buffer_setup(&client->dev, idev,
                                           iio_pollfunc_store_time,
                                           mp_trigger_handler,
                                           NULL);
    if (err) return err;

    return devm_iio_device_register(&client->dev, idev);
}

static const struct of_device_id mp_of_match[] = {
    { .compatible = "linuxlearn,mympu6050" },
    { }
};
MODULE_DEVICE_TABLE(of, mp_of_match);

static const struct i2c_device_id mp_id[] = {
    { "mympu6050", 0 },
    { }
};
MODULE_DEVICE_TABLE(i2c, mp_id);

static struct i2c_driver mp_driver = {
    .driver = {
        .name = "mympu6050",
        .of_match_table = mp_of_match,
    },
    .probe    = mp_probe,
    .id_table = mp_id,
};
module_i2c_driver(mp_driver);

MODULE_LICENSE("GPL");
```

DT:

```dts
&i2c1 {
    mpu6050@68 {
        compatible = "linuxlearn,mympu6050";
        reg = <0x68>;
    };
};
```

Test — sysfs first:

```
[root@pa-mini:~]# insmod mympu6050.ko
[root@pa-mini:~]# cat /sys/bus/iio/devices/iio:device0/in_accel_z_raw
16384         ← chip flat on the table, +1 g on Z
[root@pa-mini:~]# cat /sys/bus/iio/devices/iio:device0/in_accel_x_scale
0.000598
[root@pa-mini:~]# # 16384 × 0.000598 = 9.80 m/s², exactly 1 g. Good.
```

Then triggered buffered capture at 1 kHz using an hrtimer:

```sh
# Find a stock hrtimer trigger (some boards have one; if not, configfs-create one)
echo "hrtimer-0" > /sys/bus/iio/devices/iio:device0/trigger/current_trigger
echo 1000 > /sys/bus/iio/devices/trigger0/sampling_frequency

# Enable channels
for ax in x y z; do
    echo 1 > /sys/bus/iio/devices/iio:device0/scan_elements/in_accel_${ax}_en
    echo 1 > /sys/bus/iio/devices/iio:device0/scan_elements/in_anglvel_${ax}_en
done
echo 1 > /sys/bus/iio/devices/iio:device0/scan_elements/in_timestamp_en

# Buffer + start
echo 1024 > /sys/bus/iio/devices/iio:device0/buffer/length
echo 1 > /sys/bus/iio/devices/iio:device0/buffer/enable

# Drain 5000 samples (each = 6*2 + 8 = 20 bytes)
dd if=/dev/iio:device0 of=imu.bin bs=20 count=5000
```

5000 atomic samples — accel + gyro + 64-bit timestamp — captured in 5 seconds. User-space can FFT for vibration analysis, or feed to a Madgwick filter for real-time orientation.

What we got, ~350 lines:
- Sysfs INFO_RAW per-axis reads.
- INFO_SCALE per axis-type for cooked-units conversion.
- Triggered buffered capture with timestamps.
- Drift-free protocol for 1 kHz capture.

What we *skipped* compared to mainline:
- Multiple range/ODR runtime configuration (we hardcoded ±2g / ±250 °/s / ~1 kHz).
- DMP firmware upload (closed-source, complex).
- Magnetometer aux-bus (MPU9250-only).
- Self-test, interrupt-on-motion, FIFO overflow detection.
- Runtime PM (chip sleep when idle).

## 70.7  MPU9250 — the magnetometer-via-aux-bus quirk

MPU9250 contains an InvenSense MPU6500 (6-axis) **plus** an AsahiKASEI AK8963 magnetometer in the same package. The AK8963 isn't directly on the host I²C bus — it's accessible via the MPU6500's internal "auxiliary I²C master."

Two modes:

1. **Bypass mode**: bit 1 of INT_PIN_CFG (0x37) = 1. The MPU6500 ties its aux I²C lines directly to the host's I²C lines. Host then sees AK8963 at address 0x0C and talks to it directly.
2. **Aux-bus master mode**: the MPU6500 itself reads AK8963 registers periodically and stores results into its EXT_SENS_DATA registers (0x49..0x60). Host reads those.

Bypass is simpler; aux-master mode is needed when the chip's internal sample-aligned-with-mag synchronisation matters.

The mainline driver supports both via the `inv_mpu_aux` helper, presenting `/sys/bus/iio/devices/iio:device0/in_magn_*_raw` even though physically the magnetometer is on a hidden bus.

## 70.8  ICM-20948 — the modern replacement

ICM-20948 reorganised the register space into **banks** — 4 banks of 256 registers each, switched via a `REG_BANK_SEL` register. The bring-up sequence is 10 % longer (need bank-select before each access), but the chip itself has lower noise, lower idle current, and an updated DMP.

Mainline support: same `inv_mpu6050` driver, with `inv_icm20948_*` callbacks for bank handling.

## 70.9  Now: the mainline driver

DT for MPU6050:

```dts
&i2c1 {
    mpu6050@68 {
        compatible = "invensense,mpu6050";
        reg = <0x68>;
        interrupt-parent = <&gpio1>;
        interrupts = <14 IRQ_TYPE_EDGE_RISING>;   /* INT pin */
    };
};
```

Kernel config: `CONFIG_INV_MPU6050_IIO=y`, `CONFIG_INV_MPU6050_I2C=y`.

For MPU9250: `compatible = "invensense,mpu9250";`. For ICM-20948: `compatible = "invensense,icm20948";`.

The mainline driver gives you the same `/sys/bus/iio/...` interface plus extra knobs:

- `in_accel_sampling_frequency_available` — list of supported ODRs.
- `in_anglvel_scale_available` — list of supported ranges.
- `in_anglvel_calibbias_*` — write a bias offset.
- Data-ready trigger publishes as `mpu6050-dev0` — bindable as the sampling trigger (instead of hrtimer).

## 70.10  Sensor fusion in user-space

The IMU gives raw measurements; orientation comes from a fusion algorithm. Most common: **Madgwick filter** (a complementary filter with quaternion gradient descent). User-space implementation in ~200 lines of C:

```c
void madgwick_update(quat *q, vec3 gyro, vec3 accel, float dt, float beta)
{
    /* Normalize accel */
    accel = normalize(accel);

    /* Gradient descent step from accel: find quaternion that makes
       the predicted accel match the measured */
    vec4 grad = compute_gradient(q, accel);
    grad = normalize(grad);

    /* Quaternion derivative from gyro */
    quat qdot = quat_mul(*q, (quat){0, gyro.x, gyro.y, gyro.z}) * 0.5;

    /* Combine: gyro integration corrected by accel gradient, scaled by beta */
    qdot -= beta * grad;

    /* Integrate */
    *q = quat_add(*q, quat_scale(qdot, dt));
    *q = normalize(*q);
}
```

Run once per IMU sample (1 kHz). `beta` tunes the trust-gyro-vs-trust-accel balance (~0.1 is typical). Output: a quaternion describing the chip's orientation in world frame. Drift-free in roll/pitch.

For yaw, add magnetometer; the algorithm extends to "Madgwick AHRS."

This is *user-space* math, not driver math. The driver's job is to deliver clean samples; the application owns the fusion.

## 70.11  Lab

1. **WHO_AM_I poke.** With i2c-tools: `i2cget -y 1 0x68 0x75`. Should return 0x68 (or 0x71 for MPU9250).
2. **Build and load `mympu6050.ko`.** Read accel and gyro via sysfs. Hold the chip flat → +1 g on Z. Tilt 90° → +1 g on Y or X.
3. **Triggered buffered capture.** Configure hrtimer trigger; capture 5000 samples; parse offline. Plot accel-Z while you tap the table — you'll see vibration peaks.
4. **Madgwick filter.** Compile a user-space Madgwick implementation; feed it samples from `/dev/iio:device0`. Plot the resulting roll/pitch in real-time.
5. **Mainline driver.** Switch to `compatible = "invensense,mpu6050"`. Verify same channels appear.
6. **Self-test.** Write 0xE0 to GYRO_CONFIG (enable self-test); verify gyro outputs increase by datasheet's expected amount; check pass criteria.
7. **MPU9250 mag bypass.** If you have an MPU9250, enable bypass mode; access AK8963 directly at 0x0C via i2c-tools.

## 70.12  Pitfalls

- **Wrong I²C address.** AD0 strap pin: low = 0x68, high = 0x69. Check schematic.
- **Forgetting the wake from sleep.** Default after reset is sleep mode (bit 6 of PWR_MGMT_1). Without writing PWR_MGMT_1 = 0, all reads return 0 or stale data.
- **Wrong byte order.** All IMU output is *big-endian* on the wire. If you misread as little-endian, accel-X and accel-Y appear swapped or scaled wrong.
- **Scale factor wrong.** Each range setting has a different LSB/g or LSB/(°/s). ±2g = 16384 LSB/g; ±4g = 8192; ±8g = 4096; ±16g = 2048. Off-by-2 = factor-of-2 wrong.
- **DLPF too high BW.** Default 256 Hz BW with ODR 1 kHz means you alias high-frequency noise into your signal. Set DLPF to 1/4 of ODR or lower.
- **Gyro bias drift not calibrated.** Gyros drift with temperature. Calibrate at startup (chip stationary for 5 seconds; average ⇒ bias). Subtract bias from every sample.
- **Self-heating.** Continuous-mode chip rises 1-2 °C above ambient. If your application uses chip temperature as a thermometer (don't), this is an offset.
- **Magnetometer interference.** A buck regulator within 5 cm of MPU9250's mag corrupts readings. Schematic-stage planning matters.
- **Buffer overrun.** If user-space drains slower than the trigger rate, the IIO buffer overflows (older samples dropped). Check `/sys/bus/iio/devices/iio:device0/buffer/length` is big enough; check `dmesg` for buffer-overrun warnings.

## 70.13  Going deeper

- **`drivers/iio/imu/inv_mpu6050/inv_mpu_core.c`** — the production driver. Compare to your from-scratch version.
- **`drivers/iio/imu/inv_mpu6050/inv_mpu_ring.c`** — buffer + trigger glue.
- **MPU6050 register map (InvenSense PS-MPU6000A-00 rev 3.4)** — the canonical reference.
- **MPU9250 product specification** — magnetometer-aux-bus details on page 50+.
- **ICM-20948 datasheet** — bank-selection model.
- **Sebastian Madgwick's thesis (2010)** — derivation of the AHRS algorithm. Math-heavy but illuminating.
- **`Documentation/iio/iio_configfs.rst`** — how to create a configfs hrtimer trigger if none exist by default.

> Next chapter: **Chapter 71 — SPI IMUs.** When 1 kHz I²C isn't enough — LSM6DSO, ICM-42688, ADXL345. Bus contention, FIFO-watermark IRQs, and a from-scratch ADXL345 SPI driver.
