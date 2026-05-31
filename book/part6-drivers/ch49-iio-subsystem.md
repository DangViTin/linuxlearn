---
chapter: 49
title: IIO subsystem (ADC, sensors)
part: VI — Driver development
estimated_pages: 18
status: draft
---

# Chapter 49 — IIO subsystem (ADCs, sensors)

> **What:** **Industrial I/O** (IIO) — the kernel framework that everything sensor-related lives in. ADCs, DACs, temperature/humidity/pressure/light/proximity sensors, IMUs (accel + gyro + mag), color sensors, particulate-matter sensors, current sensors — all expose themselves through one consistent API: `/sys/bus/iio/devices/iio:deviceN/in_<type>_<index>_raw` for one-shot reads, `/dev/iio:deviceN` for streamed buffers.
> **Why:** before IIO (~2011), every sensor driver invented its own sysfs layout. Reading an ADXL345 was completely different from reading an LIS3DH despite both being 3-axis accelerometers. IIO standardised the interface: every accelerometer reports `in_accel_x_raw` in the same units after `_scale` is applied. User-space tools (`iio-utils`, libiio, gnuplot wrappers) work generically. **Every chip in Part VII's sensor cookbook is an IIO driver.**
> **Focus:** **channels, scale, and triggers**. A *channel* is one measurable thing (accel-x, temp, ADC-in-3). A *scale* converts raw value to engineering units. A *trigger* is what causes a coordinated sample to be taken (a timer, an IRQ, a sysfs poke). Get these three concepts right and IIO clicks.

## 49.1  Architecture

```
   user-space (iio-utils, libiio, your app, Grafana)
        │ /sys/bus/iio/devices/ ↔ /dev/iio:deviceN
        ▼
   ┌──────────────────────────────────────────────────┐
   │                IIO core                           │
   │   - registers iio_dev with channels + ops         │
   │   - exposes sysfs attributes for each channel     │
   │   - manages chrdev /dev/iio:deviceN for buffers   │
   │   - triggers + buffers (high-rate streaming)      │
   └──────────────────────────────────────────────────┘
        │ iio_info ops (read_raw, write_raw, ...)
        ▼
   ┌──────────────────────────────────────────────────┐
   │                Sensor driver                       │
   │   adxl345, bme280, mcp320x, ti-ads1115, ...        │
   └──────────────────────────────────────────────────┘
        │ I²C / SPI / MMIO
        ▼
   hardware
```

Drivers declare a list of `iio_chan_spec` (channel specifications) and provide `read_raw` / `write_raw` callbacks. The core handles user-space exposure.

## 49.2  The channel — IIO's atom

An IIO channel describes *one measurable quantity*. Examples:

| Channel type | Direction | Modifier | Common index | Sysfs file |
|--------------|-----------|----------|--------------|------------|
| `IIO_VOLTAGE` | input | (none) | 0..7 | `in_voltage0_raw` |
| `IIO_ACCEL` | input | `X/Y/Z` | — | `in_accel_x_raw` |
| `IIO_TEMP` | input | (none) | — | `in_temp_raw` |
| `IIO_HUMIDITYRELATIVE` | input | (none) | — | `in_humidityrelative_raw` |
| `IIO_PRESSURE` | input | (none) | — | `in_pressure_raw` |
| `IIO_LIGHT` | input | (none) | — | `in_illuminance_raw` |
| `IIO_PROXIMITY` | input | (none) | — | `in_proximity_raw` |
| `IIO_INTENSITY` | input | `IR / BOTH / RED / GREEN / BLUE` | — | `in_intensity_ir_raw` |
| `IIO_ANGL_VEL` | input | `X/Y/Z` | — | `in_anglvel_x_raw` |
| `IIO_MAGN` | input | `X/Y/Z` | — | `in_magn_x_raw` |
| `IIO_VOLTAGE` | output | (none) | 0..N | `out_voltage0_raw` (DAC) |

A channel reports a *raw* integer plus a *scale* and (optionally) an *offset*:

```
real_value_in_SI_units = (raw + offset) × scale
```

For example, a temperature sensor might report `in_temp_raw = 25420`, `in_temp_scale = 0.001`, `in_temp_offset = -2048`. The cooked value is `(25420 + (-2048)) × 0.001 = 23.372` °C.

User-space reads either:
- The raw value and computes itself: `cat in_temp_raw → 25420; cat in_temp_scale → 0.001; ...`.
- A processed value if available: `cat in_temp_input → 23372` (in milli-units).

## 49.3  Defining channels in a driver

```c
#include <linux/iio/iio.h>

static const struct iio_chan_spec my_channels[] = {
    {
        .type = IIO_TEMP,
        .info_mask_separate = BIT(IIO_CHAN_INFO_RAW) |
                              BIT(IIO_CHAN_INFO_SCALE) |
                              BIT(IIO_CHAN_INFO_OFFSET),
    },
    {
        .type = IIO_PRESSURE,
        .info_mask_separate = BIT(IIO_CHAN_INFO_RAW) | BIT(IIO_CHAN_INFO_SCALE),
    },
    {
        .type = IIO_HUMIDITYRELATIVE,
        .info_mask_separate = BIT(IIO_CHAN_INFO_RAW) | BIT(IIO_CHAN_INFO_SCALE),
    },
};
```

Three channels: temp, pressure, humidity. `info_mask_separate` declares which per-channel attributes exist (raw, scale, offset). The core auto-creates `in_temp_raw`, `in_temp_scale`, `in_temp_offset`, etc.

The driver's `read_raw` callback dispatches by channel and `info`:

```c
static int my_read_raw(struct iio_dev *idev,
                       struct iio_chan_spec const *chan,
                       int *val, int *val2, long info)
{
    struct my_priv *p = iio_priv(idev);

    switch (info) {
    case IIO_CHAN_INFO_RAW:
        switch (chan->type) {
        case IIO_TEMP:
            *val = read_temp_raw(p);  /* a raw integer from the chip */
            return IIO_VAL_INT;
        case IIO_PRESSURE:
            *val = read_pressure_raw(p);
            return IIO_VAL_INT;
        case IIO_HUMIDITYRELATIVE:
            *val = read_hum_raw(p);
            return IIO_VAL_INT;
        default:
            return -EINVAL;
        }

    case IIO_CHAN_INFO_SCALE:
        switch (chan->type) {
        case IIO_TEMP:
            *val = 0; *val2 = 10000;     /* 0.01 °C per raw */
            return IIO_VAL_INT_PLUS_MICRO;
        /* ... pressure, hum ... */
        }

    case IIO_CHAN_INFO_OFFSET:
        if (chan->type == IIO_TEMP) {
            *val = -2048;
            return IIO_VAL_INT;
        }
        return -EINVAL;
    }

    return -EINVAL;
}

static const struct iio_info my_iio_info = {
    .read_raw = my_read_raw,
};
```

Return values:
- `IIO_VAL_INT` — `*val` holds an integer.
- `IIO_VAL_INT_PLUS_MICRO` — value is `*val + *val2/1000000`. Used for fractional scales.
- `IIO_VAL_INT_PLUS_NANO` — `*val + *val2/1e9`. For very precise scales (e.g., picoteslas).
- `IIO_VAL_FRACTIONAL_LOG2` — `*val / 2^*val2`. Common for ADC scales like 1/4096.

## 49.4  Probing and registering

```c
static int my_probe(struct i2c_client *client,
                    const struct i2c_device_id *id)
{
    struct iio_dev *idev;
    struct my_priv *p;
    int err;

    idev = devm_iio_device_alloc(&client->dev, sizeof(*p));
    if (!idev)
        return -ENOMEM;

    p = iio_priv(idev);
    p->client = client;
    i2c_set_clientdata(client, idev);

    idev->name = "mysensor";
    idev->info = &my_iio_info;
    idev->modes = INDIO_DIRECT_MODE;
    idev->channels = my_channels;
    idev->num_channels = ARRAY_SIZE(my_channels);

    err = devm_iio_device_register(&client->dev, idev);
    if (err)
        return dev_err_probe(&client->dev, err, "iio register failed\n");

    dev_info(&client->dev, "mysensor ready\n");
    return 0;
}
```

`devm_iio_device_alloc(&client->dev, sizeof(*p))` allocates both the `iio_dev` and your private struct in one block. `iio_priv(idev)` recovers the priv pointer.

`INDIO_DIRECT_MODE` is the simple mode — user-space `cat in_temp_raw` directly invokes your `read_raw`. The advanced mode (`INDIO_BUFFER_HARDWARE` etc.) enables high-rate buffered capture with triggers.

## 49.5  User-space sees this

```
[root@pa-mini:~]# ls /sys/bus/iio/devices/iio:device0/
in_humidityrelative_raw   in_pressure_raw     in_temp_offset
in_humidityrelative_scale in_pressure_scale   in_temp_raw
                                              in_temp_scale
name                      ...

[root@pa-mini:~]# cat /sys/bus/iio/devices/iio:device0/name
mysensor

[root@pa-mini:~]# cat /sys/bus/iio/devices/iio:device0/in_temp_raw
25420

[root@pa-mini:~]# cat /sys/bus/iio/devices/iio:device0/in_temp_scale
0.010000
```

To convert: `awk 'BEGIN{print (25420 + (-2048)) * 0.01}'` → `23.372` °C. Or use a tool that knows IIO conventions:

```
[root@pa-mini:~]# iio_attr -d iio:device0 in_temp_raw
in_temp_raw: 25420
[root@pa-mini:~]# iio_readdev -t mysensor in_temp
23.372 °C
```

## 49.6  Triggers and buffered capture

For high-rate sensors (IMU at 1 kHz, ADC at 100 kHz), per-sample sysfs reads are too slow. IIO's *buffer* infrastructure lets the driver push samples into a kfifo, and user-space reads them as a stream from `/dev/iio:deviceN`.

The orchestration:

1. Driver registers a **buffer** (`devm_iio_kfifo_buffer_setup`).
2. User-space writes to `scan_elements/in_*_en` to enable channels.
3. User-space writes `buffer/length` to set the kfifo depth.
4. User-space binds a **trigger** via `trigger/current_trigger` — typically `hrtimer-N` (a kernel high-resolution timer firing at a set rate).
5. User-space writes `buffer/enable = 1`.
6. The trigger fires; the driver's trigger handler reads a coordinated set of samples and pushes them.
7. User-space `read(/dev/iio:deviceN, ...)` returns the bytes.

```
[root@pa-mini:~]# echo 1 > /sys/bus/iio/devices/iio:device0/scan_elements/in_accel_x_en
[root@pa-mini:~]# echo 1 > /sys/bus/iio/devices/iio:device0/scan_elements/in_accel_y_en
[root@pa-mini:~]# echo 1 > /sys/bus/iio/devices/iio:device0/scan_elements/in_accel_z_en
[root@pa-mini:~]# echo 1024 > /sys/bus/iio/devices/iio:device0/buffer/length
[root@pa-mini:~]# echo "hrtimer-0" > /sys/bus/iio/devices/iio:device0/trigger/current_trigger
[root@pa-mini:~]# echo 1 > /sys/bus/iio/devices/iio:device0/buffer/enable
[root@pa-mini:~]# dd if=/dev/iio:device0 of=samples.bin bs=$((6*100)) count=10
```

Six bytes per sample (3 axes × 2 bytes), 100 samples per read, 10 reads. The trigger drives the cadence; the driver pushes; user-space drains.

We'll meet triggers and buffers again in Ch 70/71 (IMUs) where they really earn their keep.

## 49.7  ADC drivers — a special case

ADCs work the same as sensors but with `IIO_VOLTAGE` channels and an `_indexed` flag so multiple channels can be numbered 0..7:

```c
#define ADC_CHANNEL(idx) {                              \
    .type = IIO_VOLTAGE,                                 \
    .indexed = 1,                                        \
    .channel = (idx),                                    \
    .info_mask_separate = BIT(IIO_CHAN_INFO_RAW),        \
    .info_mask_shared_by_type = BIT(IIO_CHAN_INFO_SCALE),\
    .scan_index = (idx),                                 \
    .scan_type = {                                       \
        .sign = 'u', .realbits = 10, .storagebits = 16,  \
    },                                                   \
}

static const struct iio_chan_spec mcp3008_channels[] = {
    ADC_CHANNEL(0), ADC_CHANNEL(1), ADC_CHANNEL(2), ADC_CHANNEL(3),
    ADC_CHANNEL(4), ADC_CHANNEL(5), ADC_CHANNEL(6), ADC_CHANNEL(7),
};
```

`indexed = 1` causes the sysfs files to be named `in_voltage0_raw`, `in_voltage1_raw`, etc. `info_mask_shared_by_type` means the scale is shared (one `in_voltage_scale` for all channels) — common for ADCs where every channel has the same reference voltage.

## 49.8  Lab

1. **Write a fake sensor driver.** Pick three made-up channels (temp / hum / pressure). Have `read_raw` return random values. Verify sysfs files appear and read sensibly.
2. **Add the scale and offset attributes.** Make `in_temp_scale = 0.1`, verify user-space sees `0.100000`.
3. **Try a real chip.** Wire a BME280 (or any I²C sensor with mainline IIO driver). Enable the driver in kconfig. Verify `/sys/bus/iio/devices/iio:device0/` populates correctly.
4. **Buffered capture.** Use an IMU (MPU6050 or LSM6DSO) with mainline IIO driver. Configure scan elements, hrtimer-trigger, capture 1024 samples to a file. Plot with gnuplot.
5. **Inspect with iio-utils.** Install `libiio-utils`. `iio_info -a` shows every IIO device on the system; `iio_readdev` streams samples.
6. **Compare cooked vs raw.** Some drivers provide `in_temp_input` (pre-cooked) alongside `in_temp_raw`. Diff the two on the same physical reading.

## 49.9  Pitfalls

- **Wrong `realbits` / `storagebits` in `scan_type`.** Buffered reads return junk; user-space can't decode. For a 10-bit signed value stored in 16 bits, `sign='s', realbits=10, storagebits=16, shift=0`.
- **Forgetting `INDIO_DIRECT_MODE`.** A driver with no `modes` set behaves as "buffer-only"; sysfs `_raw` reads return -EBUSY when no trigger is active. For sensors you want polled, always set `INDIO_DIRECT_MODE`.
- **`indexed=1` vs `indexed=0`.** Without `indexed=1`, the sysfs file is `in_voltage_raw` (singular). With it and `.channel = 3`, it's `in_voltage3_raw`. Use indexed for multi-channel ADCs.
- **Returning the wrong `IIO_VAL_*` from `read_raw`.** User-space sees a non-numeric "0.000000" or garbled value. Cross-check the value type with what you store in `*val`/`*val2`.
- **Trigger / channel ordering mismatch.** With buffered capture, the bytes in `/dev/iio:deviceN` are packed in the order of `scan_index`. Make sure your driver pushes in that order.
- **Forgetting `iio_priv()`.** Recovering your private struct via `idev->dev.parent_data` or whatever doesn't work; use `iio_priv(idev)`. The alignment of priv data is also handled correctly only via the `_alloc(sizeof(priv))` form.
- **Two drivers competing for the same DT node.** Sometimes both `hwmon` and IIO drivers exist for the same chip. IIO is the modern choice. Pick one and disable the other in kconfig.

## 49.10  Going deeper

- **`Documentation/iio/`** — the IIO subsystem documentation.
- **`drivers/iio/`** — hundreds of drivers, mostly straightforward. Best ones to read: `pressure/bmp280-i2c.c` + `bmp280-core.c` (BME280 family), `imu/mpu6050/`, `adc/mcp320x.c`.
- **`Documentation/ABI/testing/sysfs-bus-iio*`** — official sysfs ABI for each channel/info combo.
- **`libiio`** at <https://github.com/analogdevicesinc/libiio> — high-level user-space library; bindings for Python, C++, etc.
- **`Documentation/iio/iio_configfs.rst`** — how to add a software-only IIO device (useful for trigger configuration).

> Next chapter: **Chapter 50 — regmap.** Almost every chip with registers is now talked to via the regmap abstraction. Once you know regmap, writing the I²C / SPI / MMIO half of a driver becomes mechanical — you declare a register layout and the framework handles the rest.
