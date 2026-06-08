---
chapter: 71
title: SPI IMUs (LSM6DSO / ICM-42688 / ADXL345)
part: VII — Device cookbook
estimated_pages: 22
status: draft
---

# Chapter 71 — SPI IMUs

> **What:** three SPI inertial sensors at increasing complexity: **Analog Devices ADXL345** (3-axis accel only, the textbook case), **STMicro LSM6DSO** (6-axis with internal FIFO and finite-state-machine), **InvenSense ICM-42688** (6-axis, low-noise, large FIFO). For each: SPI command framing (R/W bit + register address), FIFO+watermark IRQ patterns, and a from-scratch ADXL345 SPI driver with FIFO support.
> MCU bridge: Think of an IRQ like an EXTI/NVIC interrupt path, except Linux splits the hard interrupt from deferred work and must share lines across drivers.
> **IRQ** - interrupt request, the signal path that tells the CPU or interrupt controller that hardware needs service.
>
> **Why:** beyond ~400 Hz per axis, you run out of I²C bandwidth: 400 kHz divided by ~10 bits per byte does not leave room for many channels. SPI runs at 10+ MHz, so an ICM-42688 streaming all 6 axes at 8 kHz fits comfortably. SPI also gives **per-CS configuration** (different IMUs on the same bus with different speeds and CPOL/CPHA), which makes multi-IMU systems straightforward to wire.
>
> **Focus:** **the FIFO + watermark IRQ pattern**. Instead of taking one IRQ per sample (8000/s, far too many), configure the chip's internal FIFO with a watermark threshold. The chip raises its IRQ only when N samples have accumulated. The driver then drains them in a single SPI burst. The CPU wakes 100×/sec instead of 8000×/sec, while still capturing every sample.


## 71.1  Chip comparison

| | ADXL345 | LSM6DSO | ICM-42688 |
|---|---|---|---|
| Axes | 3 (accel) | 6 (accel+gyro) | 6 (accel+gyro) |
| Max ODR | 3.2 kHz | 6.66 kHz | 8 kHz / 32 kHz (oversampled) |
| FIFO | 32 samples | 9 KB | 2 KB |
| Noise floor (accel) | ~290 µg/√Hz | 70 µg/√Hz | 60 µg/√Hz |
| Max SPI clock | 5 MHz | 10 MHz | 24 MHz |
| Special features | tap, double-tap, activity | FSM (finite-state machines), MLC (machine-learning core) | UI + AUX (two SPI ports), anti-aliasing |
| Volume price | $4–7 | $4–7 | $5–9 |
| Mainline driver | `adxl345_core.c` + `adxl345_spi.c` | `st_lsm6dsx_*` | `inv_icm42600_*` |

**Pick guide:**
- **ADXL345**: cheap accel-only. tap detection. legacy.
- **LSM6DSO**: machine-learning core (FSM + MLC) — useful for "detect a specific motion" without CPU involvement.
- **ICM-42688**: when noise floor matters (industrial vibration, audio-rate sampling).

For most new designs: **ICM-42688 if 6-axis SPI**, ADXL345 if 3-axis accel is enough.

## 71.2  Why SPI

| | I²C @ 400 kHz | SPI @ 10 MHz |
|---|---|---|
| Bits per byte (overhead) | 9 (start, 8 data, ACK) | 8 |
| Max effective throughput | ~40 kB/s | ~1.2 MB/s |
| 6 axes × 2 bytes × N Hz | sustainable up to ~3 kHz | sustainable up to ~100 kHz |
| Per-CS config | shared bus settings | per-device mode/speed |
| Multi-drop | yes (addressed) | star (one CS per chip) |

I²C breaks at high rates because the protocol overhead dominates. SPI doesn't address (CS is implicit), doesn't ACK each byte, and runs much faster. For a 1 kHz IMU, either bus works. For 8 kHz, SPI is mandatory.

## 71.3  ADXL345 SPI protocol

ADXL345 has a 64-byte register map. SPI command framing:

```
   Host: /CS↓ | R/W | MB | addr[5:0] | data... | /CS↑
              ↑     ↑
              0=W   1 = multi-byte (auto-increment)
              1=R
```

A *read* of register 0x32 (DATAX0) for 6 bytes (X/Y/Z, 2 bytes each):

```
   /CS↓
   send: 0b11_110010   (R=1, MB=1, addr=0x32)
   read: 6 bytes
   /CS↑
```

A *write* of value 0x08 to register 0x2D (POWER_CTL):

```
   /CS↓
   send: 0b00_101101   (R=0, MB=0, addr=0x2D)
   send: 0x08
   /CS↑
```

The "MB" (multi-byte) flag tells the chip to auto-increment the register pointer between bytes — efficient way to dump consecutive registers.

Key registers:

| Reg | Name | Purpose |
|-----|------|---------|
| 0x00 | DEVID | Always 0xE5 |
| 0x2C | BW_RATE | Output data rate + low-power mode |
| 0x2D | POWER_CTL | Sleep / standby / measure mode |
| 0x2E | INT_ENABLE | Interrupt sources |
| 0x2F | INT_MAP | Route interrupts to INT1 or INT2 pin |
| 0x30 | INT_SOURCE | Interrupt status |
| 0x31 | DATA_FORMAT | Range, full-resolution, justification |
| 0x32..0x37 | DATAX0/X1/Y0/Y1/Z0/Z1 | 16-bit signed axis data |
| 0x38 | FIFO_CTL | FIFO mode + watermark |
| 0x39 | FIFO_STATUS | FIFO level |

Bring-up:

1. Read DEVID (0x00). verify 0xE5.
2. Write DATA_FORMAT (0x31) = 0x08 (full-res ±2g. +0x01 for ±4g, etc.).
3. Write BW_RATE (0x2C) = 0x0A (100 Hz default. see datasheet table for other rates).
4. Write FIFO_CTL (0x38) = (mode << 6) | (trigger << 5) | watermark.
   - Mode 1 = FIFO mode, 2 = Stream mode, 3 = Trigger mode.
   - Watermark = number of samples (0..31).
5. Write INT_ENABLE (0x2E) = 0x02 (watermark interrupt).
6. Write POWER_CTL (0x2D) = 0x08 (measure mode).

The chip now samples at 100 Hz. The FIFO accumulates samples. when level reaches watermark, INT1 asserts. Host drains, level resets, repeat.

## 71.4  How the mainline `adxl345` driver works

Source: `drivers/iio/accel/adxl345_core.c` (~600 lines) + `adxl345_spi.c` (~80 lines).
**IIO** - Industrial I/O, Linux's subsystem for sensors, ADCs, DACs, and buffered sampled data.

```c
/* drivers/iio/accel/adxl345_spi.c — simplified */
static int adxl345_spi_probe(struct spi_device *spi)
{
    struct regmap *regmap = devm_regmap_init_spi(spi, &adxl345_spi_regmap_config);
    if (IS_ERR(regmap))
        return PTR_ERR(regmap);
    return adxl345_core_probe(&spi->dev, regmap, /* fifo_delay_ns */ 0, /* name */);
}

/* The regmap config encodes the R/W + MB bit-stuffing automatically */
static const struct regmap_config adxl345_spi_regmap_config = {
    .reg_bits = 8,
    .val_bits = 8,
    .read_flag_mask  = 0x80 | 0x40,   /* R=1, MB=1 → OR'd into the address */
    .write_flag_mask = 0x00,
    .max_register    = 0x39,
};
```

The regmap layer takes care of OR'ing 0xC0 into addresses for reads. The core code just calls `regmap_read(regmap, reg, &val)` — same code that worked for I²C now works for SPI, courtesy of regmap.
MCU bridge: Think of regmap like a typed wrapper around your read_reg() and write_reg() helpers, with caching, locking, and bus differences handled centrally.
**regmap** - a kernel helper that wraps register reads and writes over I2C, SPI, or MMIO.

### Probe flow

```c
static int adxl345_core_probe(struct device *dev, struct regmap *regmap,
                               u32 fifo_delay_ns, const char *name)
{
    struct adxl345_data *data;
    struct iio_dev *indio_dev;
    unsigned int devid;

    indio_dev = devm_iio_device_alloc(dev, sizeof(*data));
    data = iio_priv(indio_dev);
    data->regmap = regmap;

    /* Verify DEVID */
    err = regmap_read(regmap, ADXL345_REG_DEVID, &devid);
    if (devid != ADXL345_DEVID) return -ENODEV;

    /* Configure: ±2g full-res, 100 Hz, FIFO stream mode */
    regmap_write(regmap, ADXL345_REG_DATA_FORMAT, ADXL345_FULL_RES | ADXL345_RANGE_2G);
    regmap_write(regmap, ADXL345_REG_BW_RATE, ADXL345_BW_100);
    regmap_write(regmap, ADXL345_REG_FIFO_CTL, ADXL345_FIFO_STREAM | 25);

    /* Enter measurement mode */
    regmap_update_bits(regmap, ADXL345_REG_POWER_CTL,
                       ADXL345_POWER_CTL_MEASURE, ADXL345_POWER_CTL_MEASURE);

    /* Register triggered buffer */
    err = devm_iio_triggered_buffer_setup(dev, indio_dev,
                                           iio_pollfunc_store_time,
                                           adxl345_trigger_handler,
                                           NULL);

    /* If there's an IRQ on the watermark line, set it up */
    if (irq > 0)
        err = devm_request_threaded_irq(dev, irq, NULL, adxl345_irq_handler,
                                         IRQF_TRIGGER_HIGH | IRQF_ONESHOT,
                                         name, indio_dev);

    return devm_iio_device_register(dev, indio_dev);
}
```

### The IRQ + drain pattern

```c
static irqreturn_t adxl345_irq_handler(int irq, void *p)
{
    struct iio_dev *indio_dev = p;
    struct adxl345_data *data = iio_priv(indio_dev);
    unsigned int int_source;
    unsigned int entries;
    int err;

    err = regmap_read(data->regmap, ADXL345_REG_INT_SOURCE, &int_source);
    if (err) return IRQ_NONE;

    if (int_source & ADXL345_INT_WATERMARK) {
        /* Read FIFO_STATUS for the count */
        regmap_read(data->regmap, ADXL345_REG_FIFO_STATUS, &entries);
        entries &= 0x3F;

        /* Drain N samples — each is 6 bytes */
        u8 buf[6 * 32];
        regmap_noinc_read(data->regmap, ADXL345_REG_DATAX0, buf, entries * 6);

        for (int i = 0; i < entries; i++)
            iio_push_to_buffers_with_timestamp(indio_dev, &buf[i * 6],
                                                iio_get_time_ns(indio_dev));
    }
    return IRQ_HANDLED;
}
```

Compare to the per-sample-IRQ alternative: at 800 Hz with watermark = 16, the IRQ fires 50× per second instead of 800× per second. CPU load drops 16-fold, and the captured data is the same.

## 71.5  Writing an ADXL345 SPI driver from scratch (with FIFO + watermark IRQ)

`myadxl345.c`:

```c
#include <linux/init.h>
#include <linux/module.h>
#include <linux/spi/spi.h>
#include <linux/delay.h>
#include <linux/iio/iio.h>
#include <linux/iio/buffer.h>
#include <linux/iio/triggered_buffer.h>
#include <linux/iio/trigger_consumer.h>
#include <linux/iio/trigger.h>
#include <linux/interrupt.h>
#include <linux/gpio/consumer.h>

#define REG_DEVID        0x00
#define REG_BW_RATE      0x2C
#define REG_POWER_CTL    0x2D
#define REG_INT_ENABLE   0x2E
#define REG_INT_MAP      0x2F
#define REG_INT_SOURCE   0x30
#define REG_DATA_FORMAT  0x31
#define REG_DATAX0       0x32
#define REG_FIFO_CTL     0x38
#define REG_FIFO_STATUS  0x39

#define DEVID_VAL        0xE5

#define WATERMARK        16

struct myadxl {
    struct spi_device *spi;
    struct mutex lock;
    int irq;
    struct iio_trigger *trig;
};

/* === Low-level SPI read/write with R/W and MB bits === */

static int ma_read(struct myadxl *m, u8 reg, u8 *buf, int n)
{
    u8 cmd = reg | 0x80 | (n > 1 ? 0x40 : 0);  /* R=1, MB if multi-byte */
    struct spi_transfer xfers[2] = {
        { .tx_buf = &cmd, .len = 1 },
        { .rx_buf = buf,  .len = n },
    };
    struct spi_message msg;
    spi_message_init(&msg);
    spi_message_add_tail(&xfers[0], &msg);
    spi_message_add_tail(&xfers[1], &msg);
    return spi_sync(m->spi, &msg);
}

static int ma_write(struct myadxl *m, u8 reg, u8 val)
{
    u8 buf[2] = { reg, val };    /* R=0, MB=0 implicit */
    return spi_write(m->spi, buf, 2);
}

/* === Per-sample reads (sysfs INFO_RAW) === */

static int ma_read_axis(struct myadxl *m, int axis, s16 *out)
{
    u8 buf[2];
    int err = ma_read(m, REG_DATAX0 + axis*2, buf, 2);
    if (err) return err;
    *out = (s16)(buf[0] | (buf[1] << 8));   /* little-endian on the wire */
    return 0;
}

/* === Bring-up === */

static int ma_init(struct myadxl *m)
{
    u8 devid;
    int err;

    err = ma_read(m, REG_DEVID, &devid, 1);
    if (err) return err;
    if (devid != DEVID_VAL) return -ENODEV;

    /* Standby first */
    ma_write(m, REG_POWER_CTL, 0x00);

    /* ±2g, full-resolution */
    ma_write(m, REG_DATA_FORMAT, 0x08);

    /* 100 Hz ODR */
    ma_write(m, REG_BW_RATE, 0x0A);

    /* FIFO: stream mode (mode 2), watermark 16 */
    ma_write(m, REG_FIFO_CTL, (2 << 6) | WATERMARK);

    /* Map watermark IRQ to INT1, enable */
    ma_write(m, REG_INT_MAP, 0x00);    /* all to INT1 */
    ma_write(m, REG_INT_ENABLE, 0x02); /* watermark only */

    /* Measure mode */
    ma_write(m, REG_POWER_CTL, 0x08);
    return 0;
}

/* === IIO read_raw === */

static int ma_read_raw(struct iio_dev *idev,
                       struct iio_chan_spec const *chan,
                       int *val, int *val2, long mask)
{
    struct myadxl *m = iio_priv(idev);
    s16 raw;
    int err;

    switch (mask) {
    case IIO_CHAN_INFO_RAW:
        mutex_lock(&m->lock);
        err = ma_read_axis(m, chan->scan_index, &raw);
        mutex_unlock(&m->lock);
        if (err) return err;
        *val = raw;
        return IIO_VAL_INT;
    case IIO_CHAN_INFO_SCALE:
        /* Full-res: 4 mg/LSB = 4×9.80665/1000 ≈ 0.0392 m/s²/LSB */
        *val = 0; *val2 = 39226;
        return IIO_VAL_INT_PLUS_MICRO;
    }
    return -EINVAL;
}

#define ACCEL_CH(axis, idx) {                                       \
    .type = IIO_ACCEL, .modified = 1, .channel2 = (axis),            \
    .info_mask_separate = BIT(IIO_CHAN_INFO_RAW),                    \
    .info_mask_shared_by_type = BIT(IIO_CHAN_INFO_SCALE),            \
    .scan_index = (idx),                                             \
    .scan_type = { .sign='s', .realbits=16, .storagebits=16,         \
                   .endianness=IIO_LE },                              \
}

static const struct iio_chan_spec ma_channels[] = {
    ACCEL_CH(IIO_MOD_X, 0),
    ACCEL_CH(IIO_MOD_Y, 1),
    ACCEL_CH(IIO_MOD_Z, 2),
    IIO_CHAN_SOFT_TIMESTAMP(3),
};

static const struct iio_info ma_iio_info = {
    .read_raw = ma_read_raw,
};

/* === Watermark IRQ handler — runs in kernel thread === */

static irqreturn_t ma_irq_thread(int irq, void *p)
{
    struct iio_dev *idev = p;
    struct myadxl *m = iio_priv(idev);
    u8 int_src, fifo_status;
    int err;

    mutex_lock(&m->lock);

    err = ma_read(m, REG_INT_SOURCE, &int_src, 1);
    if (err) goto out;

    if (int_src & 0x02) {     /* watermark */
        ma_read(m, REG_FIFO_STATUS, &fifo_status, 1);
        int entries = fifo_status & 0x3F;

        for (int i = 0; i < entries; i++) {
            u8 sample[6];
            ma_read(m, REG_DATAX0, sample, 6);
            iio_push_to_buffers_with_timestamp(idev, sample,
                                                iio_get_time_ns(idev));
        }
    }
out:
    mutex_unlock(&m->lock);
    return IRQ_HANDLED;
}

/* === Probe / Remove === */

static int ma_probe(struct spi_device *spi)
{
    struct iio_dev *idev;
    struct myadxl *m;
    int err;

    idev = devm_iio_device_alloc(&spi->dev, sizeof(*m));
    if (!idev) return -ENOMEM;
    m = iio_priv(idev);
    m->spi = spi;
    mutex_init(&m->lock);

    spi->mode = SPI_MODE_3;
    spi->bits_per_word = 8;
    err = spi_setup(spi);
    if (err) return dev_err_probe(&spi->dev, err, "spi_setup failed\n");

    err = ma_init(m);
    if (err) return dev_err_probe(&spi->dev, err, "init failed\n");

    idev->name     = "myadxl345";
    idev->info     = &ma_iio_info;
    idev->modes    = INDIO_DIRECT_MODE | INDIO_BUFFER_TRIGGERED;
    idev->channels = ma_channels;
    idev->num_channels = ARRAY_SIZE(ma_channels);

    err = devm_iio_triggered_buffer_setup(&spi->dev, idev,
                                           NULL, NULL, NULL);
    if (err) return err;

    if (spi->irq > 0) {
        err = devm_request_threaded_irq(&spi->dev, spi->irq, NULL, ma_irq_thread,
                                         IRQF_TRIGGER_HIGH | IRQF_ONESHOT,
                                         "myadxl345", idev);
        if (err) return err;
    }

    return devm_iio_device_register(&spi->dev, idev);
}

static const struct of_device_id ma_of_match[] = {
    { .compatible = "linuxlearn,myadxl345" },
    { }
};
MODULE_DEVICE_TABLE(of, ma_of_match);

static const struct spi_device_id ma_id[] = {
    { "myadxl345", 0 },
    { }
};
MODULE_DEVICE_TABLE(spi, ma_id);

static struct spi_driver ma_driver = {
    .driver = {
        .name = "myadxl345",
        .of_match_table = ma_of_match,
    },
    .probe    = ma_probe,
    .id_table = ma_id,
};
module_spi_driver(ma_driver);

MODULE_LICENSE("GPL");
```

DT:

```dts
&ecspi3 {
    adxl345@0 {
        compatible = "linuxlearn,myadxl345";
        reg = <0>;
        spi-max-frequency = <5000000>;
        spi-cpha;
        spi-cpol;                                /* mode 3 */
        interrupt-parent = <&gpio4>;
        interrupts = <14 IRQ_TYPE_LEVEL_HIGH>;     /* watermark IRQ */
    };
};
```

Test:

```
[root@pa-mini:~]# insmod myadxl345.ko
[root@pa-mini:~]# cat /sys/bus/iio/devices/iio:device0/in_accel_z_raw
253        ← ~1 g (1000 mg / 4 mg/LSB = 250), close to 253 LSB
[root@pa-mini:~]# cat /sys/bus/iio/devices/iio:device0/in_accel_x_scale
0.039226
```

Then enable buffered capture — same workflow as Ch 70 (`scan_elements/*_en`, `buffer/enable`). At 100 Hz with watermark 16, IRQs fire ~6×/sec, draining 16 samples each. CPU overhead negligible.

What we got, ~280 lines:
- SPI command framing with R/W + MB bits.
- IIO INFO_RAW sysfs.
**sysfs** - a kernel-generated filesystem under /sys that exposes devices, drivers, and attributes.
- Triggered buffered capture *driven by the chip's own watermark IRQ*.

What we skipped:
- Multi-rate ODR support (we hardcoded 100 Hz).
- Tap / double-tap / activity / inactivity detection (ADXL345's interesting features).
- Self-test.

## 71.6  LSM6DSO — the FSM and MLC

LSM6DSO contains a **finite-state-machine engine** (FSM) and a **machine-learning core** (MLC) — runtime-programmable accelerators that detect specific motion patterns *without CPU involvement*:

- **FSM**: a small bytecode language (~256 instructions, configurable). You write a state machine ("if x_accel > 0.5 g for 100 ms then z_accel > -0.5 g for 200 ms then trigger"). The chip runs it at the IMU sample rate and emits an IRQ on match. Detect "doorbell pressed" or "drone has crashed" with zero CPU.
- **MLC**: a decision-tree classifier (8 trees, depth 8). Compiled from a Python tool with sample-labeled training data. Detect "walking vs running vs cycling" with ~90 % accuracy at < 1 % CPU.

These are special. when you need FSM or MLC, no other current-production part offers the same. Mainline support: `drivers/iio/imu/st_lsm6dsx/` includes FSM and MLC firmware-loading via the IIO config interface.

For ordinary use (just sample at 1 kHz), LSM6DSO is a normal SPI IMU — same model as ADXL345 with more channels and a bigger FIFO.

## 71.7  ICM-42688 — the noise winner

ICM-42688 has the lowest accel noise floor in this category (60 µg/√Hz) — meaningful for vibration analysis where you want to see micro-g signals. Its 2 KB FIFO supports streaming at 8 kHz with sane IRQ rates.

Register-set is bank-organised (like ICM-20948). Mainline driver: `drivers/iio/imu/inv_icm42600/`.

Its distinguishing feature is two SPI ports — UI (Userspace Interface) for normal samples, AUX for an external magnetometer pass-through. The MPU9250's aux-bus idea but cleaner.

## 71.8  Now: the mainline drivers

DT for ADXL345:

```dts
&ecspi3 {
    adxl345@0 {
        compatible = "adi,adxl345";
        reg = <0>;
        spi-max-frequency = <5000000>;
        spi-cpha; spi-cpol;
        interrupt-parent = <&gpio4>;
        interrupts = <14 IRQ_TYPE_LEVEL_HIGH>;
    };
};
```

For LSM6DSO: `compatible = "st,lsm6dso";`. For ICM-42688: `compatible = "invensense,icm42688";`.

Mainline drivers expose richer attributes than our from-scratch:

- `in_accel_sampling_frequency_available` — full ODR list.
- `in_accel_scale_available` — full range list.
- `events/in_accel_thresh_rising_value` — tap/threshold events.
- FIFO-watermark configurable via `buffer/watermark`.

## 71.9  Lab

1. **DEVID poke.** Use `spi_test` or any user-space SPI tool to read register 0x00. verify 0xE5.
2. **Build and load `myadxl345.ko`.** Read accel via sysfs. verify ~+1 g on Z when flat.
3. **Configure watermark IRQ.** Set up triggered buffer. capture 1000 samples at 100 Hz. Watch `cat /proc/interrupts` — IRQ should fire ~6 times per second, not 100.
4. **Compare against per-sample-IRQ.** Modify the driver to assert IRQ on every sample (mode 0). Measure CPU usage: `top` while streaming. Watermark mode should be much lower.
5. **Increase ODR.** Change `BW_RATE` to 0x0D (800 Hz). Verify samples land at 800 Hz with timestamps. The watermark IRQ now fires 50×/sec.
6. **Switch to mainline.** Substitute `compatible = "adi,adxl345"`. verify same data, plus extra runtime configurability.
7. **Tap detection.** Configure ADXL345's tap interrupt (different from watermark). verify a tap on the table triggers an event in user-space.
8. **LSM6DSO MLC** (if available). Use ST's online tool to compile a "walking detector" from sample data. flash to chip. verify the chip emits walking-detected events with zero CPU.

## 71.10  Pitfalls

- **SPI mode wrong.** ADXL345 is mode 3 (CPOL=1, CPHA=1). LSM6DSO is mode 0 or 3. ICM-42688 is mode 0. Each datasheet's "SPI timing" diagram tells you. Wrong mode → garbage reads.
- **CS asserted across the wrong byte count.** Reading 6 bytes but the SPI controller deasserts CS after byte 1 → chip resets pointer and you re-read register 0x32 six times. Use a single `spi_message` with all transfers chained.
- **R/W bit position.** Bit 7. MB bit at 6. Different per chip — ICM-42688 uses different bits. Read the datasheet's "SPI protocol" section.
- **Endianness mismatch.** ADXL345 puts data out little-endian. MPU6050 puts it out big-endian. Easy to swap by accident.
- **FIFO overrun.** If user-space drains too slowly, the FIFO overflows and you lose samples silently. Detect via the OVERRUN bit in INT_SOURCE (FIFO_STATUS for some chips).
- **Self-test forgotten.** Each chip has a self-test mode (forces internal mechanical stimulation). Run on power-up to verify the chip is functional. ship products with this in startup self-check.
- **Pull-ups on /CS during reset.** Some boards leave /CS floating during SoC reset. chip enters undefined state. Tie /CS HIGH at idle (10 kΩ to VCC or controller-default).
- **Multi-chip SPI with shared GPIO IRQ.** Multiple IMUs sharing a watermark-IRQ GPIO. Decode in handler by reading each chip's INT_SOURCE. only the one with bit set wants service.
MCU bridge: Think of Linux GPIO like the same pin set/reset block you used on STM32, but accessed through a kernel subsystem that owns numbering, direction, interrupts, and user-space exposure.
**GPIO** - General-Purpose Input/Output, a pin controlled as a digital input, output, or interrupt source.

## 71.11  Going deeper

- **`drivers/iio/accel/adxl345_core.c`** + `adxl345_spi.c` — production ADXL345.
- **`drivers/iio/imu/st_lsm6dsx/`** — LSM6DSO + family. FSM/MLC firmware loading.
- **`drivers/iio/imu/inv_icm42600/`** — ICM-42688.
- **ADXL345 datasheet (Analog Devices Rev G)** — register map + FIFO modes.
- **LSM6DSO datasheet (STMicro DS12140)** — FSM/MLC sections.
- **ICM-42688-P datasheet (InvenSense DS-000347)** — anti-aliasing filter design.
- **`Documentation/iio/iio_devbuf.rst`** — buffered IIO model.

---

> **End of Group C — Motion sensors (Ch 70–71).** I²C IMUs cover up to ~1 kHz, SPI IMUs the rest of the way to ~10 kHz. both use IIO triggered buffers, both support watermark-IRQ patterns when ODR is high.

> Next chapter: **Chapter 72 — Distance & proximity sensors (VL53L0X / HC-SR04 / GP2Y0A).** Three approaches to "how far away is that object?" Each with different physics and very different drivers.
