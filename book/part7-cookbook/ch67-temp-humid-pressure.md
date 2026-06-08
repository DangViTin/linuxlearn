---
chapter: 67
title: Temperature / humidity / pressure (BME280 / SHT3x / AHT20)
part: VII — Device cookbook
estimated_pages: 26
status: draft
---

# Chapter 67 — Temperature / humidity / pressure
**IRQ** - interrupt request, the signal path that tells the CPU or interrupt controller that hardware needs service.
> **MCU bridge:** Think of an IRQ like an EXTI/NVIC interrupt path, except Linux splits the hard interrupt from deferred work and must share lines across drivers.

> **What:** three I²C environmental sensors, dissected: **Bosch BME280** (T+H+P, the workhorse), **Sensirion SHT3x** (T+H, lab-grade accuracy), **ASAir AHT20** (T+H, cheap-and-good). For each: register map, the bytes on the wire, how the mainline IIO driver works, and — for BME280, the most complex — a from-scratch IIO driver implemented from the datasheet.
> **IIO** - Industrial I/O, Linux's subsystem for sensors, ADCs, DACs, and buffered sampled data.
>
> **Why:** environmental sensors are the most common I²C peripherals in IoT and HMI products. They're also the canonical sensors for understanding the IIO subsystem: a small driver, a clear data path, real compensation math that exposes why "raw" and "scale" are separate IIO attributes. Writing one from scratch teaches you both the chip and IIO at the same time.
>
> **Focus:** **calibration math turns raw ADC bins into engineering units**. The BME280 ships per-chip calibration coefficients in non-volatile memory. The driver reads them at probe and applies a published polynomial to each raw measurement. Understanding this — that the compensation formula lives in the *driver*, not the *chip* — is the key insight.


## 67.1  Sensor comparison

| | Bosch BME280 | Sensirion SHT3x-DIS | ASAir AHT20 |
|---|---|---|---|
| Measures | T, H, P | T, H | T, H |
| Interface | I²C or SPI | I²C | I²C |
| I²C address | 0x76 / 0x77 | 0x44 / 0x45 | 0x38 |
| Resolution (T) | 0.01 °C | 0.015 °C | 0.01 °C |
| Accuracy (T) | ±1.0 °C | ±0.2 °C | ±0.3 °C |
| Resolution (H) | 0.008 %RH | 0.01 %RH | 0.024 %RH |
| Accuracy (H) | ±3 %RH | ±1.5 %RH | ±2 %RH |
| Resolution (P) | 0.18 Pa | — | — |
| Calibration data | per-chip NVM (read at startup) | factory-trimmed in firmware (no NVM read needed) | factory-trimmed in firmware |
| CRC on data | no | yes (8-bit polynomial) | no |
| Datasheet length | 60 pp | 30 pp | 20 pp |
| Volume price | $2–4 | $4–7 | $0.40–0.80 |
| Mainline driver | `bmp280-i2c.c` + `bmp280-core.c` | `sht3x.c` (hwmon) + `humidity/shtc1.c`-style IIO not yet for SHT3x in IIO; `sht3x` is hwmon | `aht20.c` (recent kernels) |

**Pick guide:**
- **BME280**: when you want pressure (altitude approximation), or when you're already in the BMP/BME ecosystem.
- **SHT3x**: when you need humidity accuracy (HVAC, agriculture, calibration-reference work).
- **AHT20**: when cost matters and ±2 % RH is fine. The default cheap humidity sensor on hobbyist boards.

## 67.2  Schematic

All three are 4–6 pin packages:

```
 i.MX6ULL                Sensor (3.3 V supply, I²C)
 ─────────              ─────────────────────────
 SDA   ──╳──┐──────────► SDA      (4.7 kΩ pull-up to 3.3 V — shared on the bus)
 SCL   ──╳──┘──────────► SCL
 VCC ─────────────────► VDD (3.3 V)
 GND ─────────────────► VSS

 BME280 also has: CSB → tie HIGH for I²C mode (LOW selects SPI mode)
                  SDO → tie HIGH (addr 0x77) or LOW (addr 0x76)

 SHT3x: ADDR → tie HIGH (0x45) or LOW (0x44)
        ALERT → optional output (threshold IRQ); leave NC if unused

 AHT20: no straps; fixed address 0x38
```

The classic mistake: forgetting CSB strap on the BME280 — left floating, the chip oscillates between I²C and SPI modes. Always tie CSB high explicitly.

## 67.3  Protocol — BME280 on the wire

BME280 has a register-bank model just like the EEPROMs in Ch 65:

| Reg | Name | Purpose |
|-----|------|---------|
| 0xD0 | id | Chip ID (always 0x60 for BME280, 0x58 for BMP280) |
| 0xE0 | reset | Write 0xB6 to soft-reset |
| 0xF2 | ctrl_hum | Humidity oversampling |
| 0xF4 | ctrl_meas | Temp/pressure oversampling + power mode |
| 0xF5 | config | Filter, standby duration |
| 0xF7..0xF9 | press_msb/lsb/xlsb | Raw pressure (20-bit) |
| 0xFA..0xFC | temp_msb/lsb/xlsb | Raw temperature (20-bit) |
| 0xFD..0xFE | hum_msb/lsb | Raw humidity (16-bit) |
| 0x88..0xA1 | dig_T*, dig_P*, dig_H1 | Calibration coefficients (factory NVM) |
| 0xE1..0xE7 | dig_H2..dig_H6 | More calibration |

To take a measurement:

1. Write to `ctrl_hum` (0xF2): humidity oversampling (1× / 2× / 4× / 8× / 16×).
2. Write to `ctrl_meas` (0xF4): temp + pressure oversampling, power mode.
   - Mode 0b01 = forced (take one measurement, return to sleep).
   - Mode 0b11 = normal (continuous).
3. Wait for measurement to complete (typically 8 ms with default oversampling).
4. Read 8 bytes from 0xF7 — the entire measurement block in one transaction.
5. Apply compensation formulas using the calibration coefficients read at probe.

The compensation formulas (~30 lines of fixed-point arithmetic per axis) are *published in the datasheet* and identical for every BME280. They convert the raw 20-bit ADC values to °C × 100, Pa × 256, and %RH × 1024.

### A worked read

To read once with default oversampling:

```
   START | 0xEC | 0xF4 | 0x25 | STOP        (write 0x25 to ctrl_meas: 1×T, 1×P, forced mode)
   ... wait ~8 ms ...
   START | 0xEC | 0xF7 | START | 0xED |     (write reg address 0xF7, repeated start, read)
       D[0..7] (msb,lsb,xlsb of P; msb,lsb,xlsb of T; msb,lsb of H)
   STOP
```

`0xEC` = (0x76 << 1) | 0 (write). `0xED` = (0x76 << 1) | 1 (read).

The output bytes pack as:

```
press_raw = (D[0] << 12) | (D[1] << 4) | (D[2] >> 4);   // 20-bit
temp_raw  = (D[3] << 12) | (D[4] << 4) | (D[5] >> 4);   // 20-bit
hum_raw   = (D[6] << 8) | D[7];                          // 16-bit
```

These three integers go into the compensation functions (datasheet §4.2.3 / 8.1 / 8.2).

## 67.4  How the mainline driver works

Source: `drivers/iio/pressure/bmp280-core.c` (~1500 lines) + `bmp280-i2c.c` (~150 lines) + `bmp280-spi.c`.

The driver covers BMP180 / BMP280 / BME280 / BMP380 / BMP580 — five chips of similar lineage. The *bus* (I²C vs SPI) is decoupled via regmap. The *chip* is identified at probe via the `0xD0` ID register, and the right `chip_info` table is selected.
> **MCU bridge:** Think of regmap like a typed wrapper around your read_reg() and write_reg() helpers, with caching, locking, and bus differences handled centrally.
**regmap** - a kernel helper that wraps register reads and writes over I2C, SPI, or MMIO.

### Architecture

```c
/* drivers/iio/pressure/bmp280.h — simplified */
struct bmp280_chip_info {
    unsigned int   id_reg;          /* 0xD0 */
    const unsigned int *chip_id;
    const struct iio_chan_spec *channels;
    int num_channels;

    int (*read_calib)(struct bmp280_data *);
    int (*chip_config)(struct bmp280_data *);
    int (*read_press)(struct bmp280_data *, u32 *);
    int (*read_temp)(struct bmp280_data *, s32 *);
    int (*read_humid)(struct bmp280_data *, u32 *);
    ...
};
```

The `chip_info` is a vtable: for each chip in the family, the driver assigns the right callbacks. BME280 gets `bme280_read_humid` (with humidity). BMP280 (no humidity sensor) gets a stub.

### Probe

```c
static int bmp280_common_probe(struct device *dev, struct regmap *regmap,
                                const struct bmp280_chip_info *chip_info,
                                const char *name, int irq)
{
    struct bmp280_data *data;
    struct iio_dev *indio_dev;
    unsigned int chip_id;
    int err;

    indio_dev = devm_iio_device_alloc(dev, sizeof(*data));
    data = iio_priv(indio_dev);
    data->regmap = regmap;
    data->chip_info = chip_info;

    /* 1. Identify the chip */
    err = regmap_read(regmap, chip_info->id_reg, &chip_id);
    if (chip_id != chip_info->chip_id[0]) return -EINVAL;

    /* 2. Read the per-chip calibration coefficients into data->calib */
    err = chip_info->read_calib(data);

    /* 3. Configure default operating mode */
    err = chip_info->chip_config(data);

    /* 4. Register with IIO */
    indio_dev->name = name;
    indio_dev->info = &bmp280_info;
    indio_dev->modes = INDIO_DIRECT_MODE;
    indio_dev->channels = chip_info->channels;
    indio_dev->num_channels = chip_info->num_channels;
    return devm_iio_device_register(dev, indio_dev);
}
```

The I²C glue is tiny — just creates a regmap and calls the common probe:

```c
/* drivers/iio/pressure/bmp280-i2c.c — simplified */
static int bmp280_i2c_probe(struct i2c_client *client)
{
    struct regmap *regmap = devm_regmap_init_i2c(client, &bmp280_regmap_config);
    const struct bmp280_chip_info *chip_info = ...;  /* from id_table */
    return bmp280_common_probe(&client->dev, regmap, chip_info, ...);
}
```

### read_raw — the IIO callback

```c
static int bmp280_read_raw(struct iio_dev *indio_dev,
                           struct iio_chan_spec const *chan,
                           int *val, int *val2, long mask)
{
    struct bmp280_data *data = iio_priv(indio_dev);
    int ret;

    mutex_lock(&data->lock);
    switch (mask) {
    case IIO_CHAN_INFO_PROCESSED:
        switch (chan->type) {
        case IIO_TEMP:
            ret = data->chip_info->read_temp(data, val);     /* returns mC */
            break;
        case IIO_PRESSURE:
            ret = data->chip_info->read_press(data, (u32 *)val);  /* Pa */
            break;
        case IIO_HUMIDITYRELATIVE:
            ret = data->chip_info->read_humid(data, (u32 *)val);   /* milli-percent */
            break;
        }
        if (ret == 0) ret = IIO_VAL_INT;
        break;
    }
    mutex_unlock(&data->lock);
    return ret;
}
```

When user-space reads `/sys/bus/iio/devices/iio:device0/in_temp_input`, the driver issues a "forced measurement," waits about 8 ms, reads the 8 raw bytes, applies the compensation formula, and returns `23420` (millidegrees Celsius).

### The compensation formula (where the magic happens)

For temperature, from the BME280 datasheet §8.1:

```c
static s32 bme280_compensate_temp(struct bmp280_data *data, s32 adc_T)
{
    s32 var1, var2;

    var1 = (((adc_T >> 3) - ((s32)data->t_fine_calib.dig_T1 << 1)) *
            (s32)data->t_fine_calib.dig_T2) >> 11;

    var2 = (((((adc_T >> 4) - (s32)data->t_fine_calib.dig_T1) *
              ((adc_T >> 4) - (s32)data->t_fine_calib.dig_T1)) >> 12) *
              (s32)data->t_fine_calib.dig_T3) >> 14;

    data->t_fine = var1 + var2;       /* saved for use in pressure compensation */
    return (data->t_fine * 5 + 128) >> 8;  /* temp in mC */
}
```

These formulas are not approximations. They are lifted byte-for-byte from page 25 of the BME280 datasheet. The driver carries it as-published — same code in every BME280 driver across all OSes.

`dig_T1`, `dig_T2`, `dig_T3` are the calibration coefficients read from chip NVM at probe. Each chip has slightly different ones (silicon process variation).

The pressure formula is longer (~30 lines) and uses 64-bit arithmetic to avoid overflow. humidity formula uses the saved `t_fine` to compensate for temperature.

## 67.5  Writing a BME280 IIO driver from scratch

Goal: a working IIO driver that exposes temp + humidity + pressure as `in_temp_input` / `in_pressure_input` / `in_humidityrelative_input`. No regmap, no chip-family abstraction — just BME280, raw `i2c_smbus_*`, and the Bosch math.

`mybme280.c`:

```c
#include <linux/init.h>
#include <linux/module.h>
#include <linux/i2c.h>
#include <linux/delay.h>
#include <linux/iio/iio.h>
#include <linux/of.h>

#define BME280_CHIP_ID         0x60
#define REG_ID                 0xD0
#define REG_RESET              0xE0
#define REG_CTRL_HUM           0xF2
#define REG_CTRL_MEAS          0xF4
#define REG_CONFIG             0xF5
#define REG_DATA_START         0xF7   /* 8 bytes: P, T, H */

/* Calibration registers */
#define REG_CALIB_TP           0x88   /* 24 bytes: T1..T3, P1..P9 */
#define REG_CALIB_H1           0xA1   /* 1 byte */
#define REG_CALIB_H2           0xE1   /* 7 bytes: H2..H6 */

struct mybme {
    struct i2c_client *client;
    struct mutex lock;

    /* Calibration coefficients (read once at probe) */
    u16 T1; s16 T2, T3;
    u16 P1; s16 P2, P3, P4, P5, P6, P7, P8, P9;
    u8  H1, H3;
    s16 H2, H4, H5;
    s8  H6;

    s32 t_fine;   /* set by compensate_temp, used by compensate_press/humid */
};

/* Read N bytes from a register */
static int mb_read_block(struct mybme *m, u8 reg, u8 *out, int n)
{
    int r = i2c_smbus_read_i2c_block_data(m->client, reg, n, out);
    if (r < 0) return r;
    if (r != n) return -EIO;
    return 0;
}

static int mb_read_calib(struct mybme *m)
{
    u8 buf[26];
    int err;

    /* Read T1..T3, P1..P9 (24 bytes) starting at 0x88 */
    err = mb_read_block(m, REG_CALIB_TP, buf, 24);
    if (err) return err;
    m->T1 = buf[0] | (buf[1] << 8);
    m->T2 = (s16)(buf[2] | (buf[3] << 8));
    m->T3 = (s16)(buf[4] | (buf[5] << 8));
    m->P1 = buf[6] | (buf[7] << 8);
    m->P2 = (s16)(buf[8] | (buf[9] << 8));
    m->P3 = (s16)(buf[10] | (buf[11] << 8));
    m->P4 = (s16)(buf[12] | (buf[13] << 8));
    m->P5 = (s16)(buf[14] | (buf[15] << 8));
    m->P6 = (s16)(buf[16] | (buf[17] << 8));
    m->P7 = (s16)(buf[18] | (buf[19] << 8));
    m->P8 = (s16)(buf[20] | (buf[21] << 8));
    m->P9 = (s16)(buf[22] | (buf[23] << 8));

    /* H1 at 0xA1 (1 byte) */
    err = i2c_smbus_read_byte_data(m->client, REG_CALIB_H1);
    if (err < 0) return err;
    m->H1 = err;

    /* H2..H6 at 0xE1 (7 bytes) — encoding is *weird* per datasheet */
    err = mb_read_block(m, REG_CALIB_H2, buf, 7);
    if (err) return err;
    m->H2 = (s16)(buf[0] | (buf[1] << 8));
    m->H3 = buf[2];
    m->H4 = (s16)(((s8)buf[3] << 4) | (buf[4] & 0x0F));
    m->H5 = (s16)(((s8)buf[5] << 4) | (buf[4] >> 4));
    m->H6 = (s8)buf[6];
    return 0;
}

/* ------ Compensation formulas (copy-pasted from Bosch BME280 datasheet §8.1–8.2) ------ */

static s32 compensate_T(struct mybme *m, s32 adc_T)
{
    s32 var1, var2;
    var1 = ((((adc_T >> 3) - ((s32)m->T1 << 1))) * (s32)m->T2) >> 11;
    var2 = (((((adc_T >> 4) - (s32)m->T1) *
               ((adc_T >> 4) - (s32)m->T1)) >> 12) * (s32)m->T3) >> 14;
    m->t_fine = var1 + var2;
    return (m->t_fine * 5 + 128) >> 8;   /* mC */
}

static u32 compensate_P(struct mybme *m, s32 adc_P)
{
    s64 var1, var2, p;
    var1 = (s64)m->t_fine - 128000;
    var2 = var1 * var1 * (s64)m->P6;
    var2 = var2 + ((var1 * (s64)m->P5) << 17);
    var2 = var2 + (((s64)m->P4) << 35);
    var1 = ((var1 * var1 * (s64)m->P3) >> 8) + ((var1 * (s64)m->P2) << 12);
    var1 = (((((s64)1) << 47) + var1)) * ((s64)m->P1) >> 33;
    if (var1 == 0) return 0;
    p = 1048576 - adc_P;
    p = (((p << 31) - var2) * 3125) / var1;
    var1 = (((s64)m->P9) * (p >> 13) * (p >> 13)) >> 25;
    var2 = (((s64)m->P8) * p) >> 19;
    p = ((p + var1 + var2) >> 8) + (((s64)m->P7) << 4);
    return (u32)p;        /* Pa × 256 (driver convention) */
}

static u32 compensate_H(struct mybme *m, s32 adc_H)
{
    s32 v;
    v = m->t_fine - 76800;
    v = ((((adc_H << 14) - (((s32)m->H4) << 20) - (((s32)m->H5) * v)) + 16384) >> 15)
        * (((((((v * ((s32)m->H6)) >> 10) *
               (((v * ((s32)m->H3)) >> 11) + 32768)) >> 10) + 2097152) *
            ((s32)m->H2) + 8192) >> 14);
    v = v - (((((v >> 15) * (v >> 15)) >> 7) * ((s32)m->H1)) >> 4);
    if (v < 0) v = 0;
    if (v > 419430400) v = 419430400;
    return (u32)(v >> 12);   /* %RH × 1024 */
}

/* ------ Do a forced measurement, read all 8 bytes, compensate ------ */

static int mb_measure(struct mybme *m, s32 *t_mC, u32 *p_Pa_x256, u32 *h_xRH_x1024)
{
    u8 raw[8];
    s32 adc_T, adc_P, adc_H;
    int err;

    /* humidity oversampling = 1× */
    err = i2c_smbus_write_byte_data(m->client, REG_CTRL_HUM, 0x01);
    if (err) return err;

    /* temp + press oversampling = 1×; mode = forced (0b01) */
    err = i2c_smbus_write_byte_data(m->client, REG_CTRL_MEAS,
                                    (0x01 << 5) | (0x01 << 2) | 0x01);
    if (err) return err;

    msleep(10);   /* worst-case ~8 ms with 1× oversampling */

    err = mb_read_block(m, REG_DATA_START, raw, 8);
    if (err) return err;

    adc_P = (raw[0] << 12) | (raw[1] << 4) | (raw[2] >> 4);
    adc_T = (raw[3] << 12) | (raw[4] << 4) | (raw[5] >> 4);
    adc_H = (raw[6] << 8) | raw[7];

    *t_mC      = compensate_T(m, adc_T);   /* call first — sets t_fine */
    *p_Pa_x256 = compensate_P(m, adc_P);
    *h_xRH_x1024 = compensate_H(m, adc_H);
    return 0;
}

/* ------ IIO callback ------ */

static int mb_read_raw(struct iio_dev *idev, struct iio_chan_spec const *chan,
                       int *val, int *val2, long info)
{
    struct mybme *m = iio_priv(idev);
    s32 t_mC; u32 p_x256, h_x1024;
    int err;

    if (info != IIO_CHAN_INFO_PROCESSED) return -EINVAL;

    mutex_lock(&m->lock);
    err = mb_measure(m, &t_mC, &p_x256, &h_x1024);
    mutex_unlock(&m->lock);
    if (err) return err;

    switch (chan->type) {
    case IIO_TEMP:
        *val = t_mC;                         /* mC */
        return IIO_VAL_INT;
    case IIO_PRESSURE:
        *val = p_x256 / 256;                  /* Pa */
        return IIO_VAL_INT;
    case IIO_HUMIDITYRELATIVE:
        *val = h_x1024 * 1000 / 1024;         /* milli-percent */
        return IIO_VAL_INT;
    default:
        return -EINVAL;
    }
}

static const struct iio_chan_spec mb_channels[] = {
    { .type = IIO_TEMP,             .info_mask_separate = BIT(IIO_CHAN_INFO_PROCESSED) },
    { .type = IIO_PRESSURE,         .info_mask_separate = BIT(IIO_CHAN_INFO_PROCESSED) },
    { .type = IIO_HUMIDITYRELATIVE, .info_mask_separate = BIT(IIO_CHAN_INFO_PROCESSED) },
};

static const struct iio_info mb_iio_info = {
    .read_raw = mb_read_raw,
};

/* ------ Probe / Remove ------ */

static int mb_probe(struct i2c_client *client)
{
    struct iio_dev *idev;
    struct mybme *m;
    int chip_id, err;

    idev = devm_iio_device_alloc(&client->dev, sizeof(*m));
    if (!idev) return -ENOMEM;
    m = iio_priv(idev);
    m->client = client;
    mutex_init(&m->lock);

    /* Identify */
    chip_id = i2c_smbus_read_byte_data(client, REG_ID);
    if (chip_id < 0) return chip_id;
    if (chip_id != BME280_CHIP_ID)
        return dev_err_probe(&client->dev, -ENODEV,
                             "unexpected chip-id 0x%02x (want 0x60)\n", chip_id);

    /* Soft reset, wait for the chip to come back */
    i2c_smbus_write_byte_data(client, REG_RESET, 0xB6);
    msleep(5);

    err = mb_read_calib(m);
    if (err) return dev_err_probe(&client->dev, err, "read-calib failed\n");

    idev->name = "mybme280";
    idev->info = &mb_iio_info;
    idev->modes = INDIO_DIRECT_MODE;
    idev->channels = mb_channels;
    idev->num_channels = ARRAY_SIZE(mb_channels);

    return devm_iio_device_register(&client->dev, idev);
}

static const struct of_device_id mb_of_match[] = {
    { .compatible = "linuxlearn,mybme280" },
    { }
};
MODULE_DEVICE_TABLE(of, mb_of_match);

static const struct i2c_device_id mb_id[] = {
    { "mybme280", 0 },
    { }
};
MODULE_DEVICE_TABLE(i2c, mb_id);

static struct i2c_driver mb_driver = {
    .driver = {
        .name = "mybme280",
        .of_match_table = mb_of_match,
    },
    .probe    = mb_probe,
    .id_table = mb_id,
};
module_i2c_driver(mb_driver);

MODULE_LICENSE("GPL");
```

DT:

```dts
&i2c1 {
    bme280@76 {
        compatible = "linuxlearn,mybme280";
        reg = <0x76>;
    };
};
```

Build, load, exercise:

```
[root@pa-mini:~]# insmod mybme280.ko
[root@pa-mini:~]# ls /sys/bus/iio/devices/iio:device0/
in_humidityrelative_input  in_pressure_input  in_temp_input  name  ...

[root@pa-mini:~]# cat /sys/bus/iio/devices/iio:device0/name
mybme280

[root@pa-mini:~]# cat /sys/bus/iio/devices/iio:device0/in_temp_input
23420
[root@pa-mini:~]# cat /sys/bus/iio/devices/iio:device0/in_pressure_input
100327
[root@pa-mini:~]# cat /sys/bus/iio/devices/iio:device0/in_humidityrelative_input
56000
```

Values: 23.42 °C (temp = 23420 mC), 100.3 kPa (= 100327 Pa = 1003.27 mbar = local barometric pressure at sea level), 56.0 % RH.

Driver is ~300 lines and reports calibrated values via IIO. The compensation math is the longest part — and that's *just the Bosch published formulas* copy-pasted from the datasheet.

What we *skipped* compared to mainline:
- Filter and standby-time configuration (we use minimums).
- Buffered/triggered capture (we only do `INDIO_DIRECT_MODE` sysfs reads).
**sysfs** - a kernel-generated filesystem under /sys that exposes devices, drivers, and attributes.
- Power management (`runtime_suspend` to drop to chip sleep mode).
- Multi-chip support (we only handle BME280. mainline handles BMP180/280/380/580 too).

Those are framework features, not chip-understanding features. The chip is what we set out to teach.

## 67.6  SHT3x — a different design philosophy

SHT3x doesn't have a register map. Instead it uses **2-byte commands** sent on I²C, optionally followed by a data block with **CRC**. Sensirion's design choice: keep state in the host, not the chip.

### Commands

| 16-bit command | What |
|-----|-----|
| `0x2C 06` | One-shot measurement, high repeatability, with clock-stretching |
| `0x24 00` | One-shot measurement, high repeatability, no clock-stretching |
| `0x21 30` | Periodic mode, 1 mps, high repeatability |
| `0xE0 00` | Read measurement (after periodic mode) |
| `0x30 41` | Reset |
| `0xF3 2D` | Read status register |

A one-shot read of T+H:

```
   START | 0x88 | 0x2C | 0x06 | STOP       (write command, addr 0x44 << 1 = 0x88)
   ... wait ~15 ms ...
   START | 0x89 | T_msb | T_lsb | T_crc | H_msb | H_lsb | H_crc | STOP
```

The CRC bytes use Sensirion's polynomial `0x31` (CRC-8) over each 2-byte word. The driver validates them. If either CRC is bad, retry.

### Conversion math (much simpler than BME280)

```c
T_mC  = -45000 + ((175000 * temp_raw) >> 16);
RH_milli_pct = (100000 * hum_raw) >> 16;
```

That's it. Two linear formulas. No per-chip calibration to read — Sensirion factory-trims each chip's coefficients into firmware before shipping, so every chip reports the same scale.

### Mainline driver

`drivers/iio/humidity/sht3x.c` (~700 lines, but most is alert/threshold handling). The probe sends a reset command, sets up periodic mode, and registers an IIO device. The `read_raw` callback sends `0xE0 00`, parses 6 bytes (T,T,CRC,H,H,CRC), validates, returns the linear-mapped result.

To convert the from-scratch BME280 driver to SHT3x:
- Drop the calibration reads and compensation math.
- Replace register-pointer writes with 2-byte command writes.
- Add CRC-8 validation.
- Replace `mb_measure` with a "send command, sleep, read 6 bytes, CRC-check, linear-convert" function.

We won't re-implement it. The structure is now clear.

## 67.7  AHT20 — even simpler

AHT20 is the cheap-and-cheerful option: ASAir's clone of the DHT-family with proper I²C.

### Commands

| Command | What |
|---------|------|
| `0xBE 08 00` | Initialise (write once after power-up) |
| `0xAC 33 00` | Start measurement (trigger) |
| (no command) | Read 7 bytes — status, H[3], T[3] |
| `0xBA` | Soft reset |

A one-shot read:

```
   START | 0x70 | 0xAC | 0x33 | 0x00 | STOP    (start measurement)
   ... wait ~80 ms ...
   START | 0x71 | S | H0 | H1 | H2/T0 | T1 | T2 | CRC | STOP
                    ↑
                    bit 7 of byte S is "busy" (1 = still measuring)
```

The H and T raw values are 20 bits each. They share a middle byte: the top 4 bits go to H, the bottom 4 bits to T.

Conversion:

```c
RH_milli_pct = (h_raw * 100000) >> 20;
T_mC = ((t_raw * 200000) >> 20) - 50000;
```

Mainline driver: `drivers/iio/humidity/aht20.c` (in newer kernels). ~250 lines.

To convert the from-scratch driver: same structure as BME280, drop compensation, use AHT20's command sequence. After the BME280 driver, converting to AHT20 is mostly mechanical command-table substitution.

## 67.8  Now: the mainline driver

DT for the mainline BME280:

```dts
&i2c1 {
    bme280@76 {
        compatible = "bosch,bme280";
        reg = <0x76>;
        /* No other properties needed; the driver defaults are sensible */
    };
};
```

Enable `CONFIG_BMP280=y` and `CONFIG_BMP280_I2C=y` in kernel config. Boot:

```
[root@pa-mini:~]# ls /sys/bus/iio/devices/iio:device0/
in_humidityrelative_input
in_humidityrelative_oversampling_ratio
in_humidityrelative_oversampling_ratio_available
in_pressure_input
in_pressure_oversampling_ratio
in_temp_input
in_temp_oversampling_ratio
name
sampling_frequency
sampling_frequency_available

[root@pa-mini:~]# cat name
bme280
```

Notice extra knobs the mainline driver provides (oversampling ratio, sampling frequency) — these tune the chip's internal averaging.

```
[root@pa-mini:~]# echo 16 > in_temp_oversampling_ratio
[root@pa-mini:~]# echo 16 > in_humidityrelative_oversampling_ratio
```

Sets 16× oversampling: chip averages 16 samples internally, giving ~4× better noise at the cost of ~16× more measurement time (~130 ms instead of ~8 ms). Same data path, just longer averaging.

## 67.9  User-space access

For a logging app:

```python
#!/usr/bin/env python3
import time
def read_iio(path):
    with open(path) as f: return int(f.read().strip())
while True:
    t = read_iio("/sys/bus/iio/devices/iio:device0/in_temp_input") / 1000.0
    h = read_iio("/sys/bus/iio/devices/iio:device0/in_humidityrelative_input") / 1000.0
    p = read_iio("/sys/bus/iio/devices/iio:device0/in_pressure_input")
    print(f"T={t:.2f}°C H={h:.1f}%RH P={p}Pa")
    time.sleep(10)
```

Pipe to MQTT, Grafana, SQLite — whatever the product needs.

## 67.10  Lab

1. **Inspect with i2c-tools.** `i2cdetect -y 1` to find the BME280 (0x76 or 0x77). `i2cdump -y 1 0x76` to see the register map. verify the byte at 0xD0 is 0x60.
2. **Build and load `mybme280.ko`.** Read all three IIO inputs. Verify physically — touch the sensor. temp should rise.
3. **Compare against a reference.** Use a known-good thermometer or another working sensor. Expected accuracy: ±1 °C at room temp.
4. **Implement an SHT3x version.** Strip the calibration code and compensation math. substitute the SHT3x command set + linear formulas + CRC validation. ~200 lines.
5. **Switch to the mainline `bme280`.** Unload yours, change DT to `compatible = "bosch,bme280"`, reboot. Verify same readings (within sensor noise). Note the extra `oversampling_ratio` files appearing.
6. **Mainline `read_raw` source dive.** Read `bme280_compensate_temp` in `drivers/iio/pressure/bmp280-core.c`. Verify it's the same formula you copied from the datasheet.
7. **Power consumption.** With mainline driver, measure idle current. Compare against periodic-mode + sleep with `oversampling_ratio = 0` (chip skips a measurement type entirely).

## 67.11  Pitfalls

- **CSB strap floating on BME280**. Chip oscillates between I²C and SPI modes. Tie CSB high explicitly (10 kΩ to VCC).
- **Wrong I²C address.** BME280: 0x76 if SDO low, 0x77 if SDO high. Check schematic.
- **Forgetting to set humidity oversampling** (`ctrl_hum` write). Default at power-on is 0x00 = humidity disabled. You read 0x8000 forever and wonder why.
- **`ctrl_hum` write order**. The chip only acts on `ctrl_hum` *after* the next `ctrl_meas` write. So always write `ctrl_hum` before `ctrl_meas`.
- **Self-heating.** Continuous-mode at 16× oversampling makes the chip's own current dissipation warm the sensor by ~0.5 °C. Use forced-mode + sleep, or accept the offset.
- **Calibration coefficient endianness.** They're little-endian on the wire. If you mis-cast `(s16)((buf[1] << 8) | buf[0])` vs the reverse, math is garbage. Cross-check against datasheet table.
- **CRC ignored on SHT3x**. CRC byte != 0 doesn't *break* but indicates data corruption — chip retried internally but the read got noisy. Log and retry. If persistent, bus signal-integrity issue.
- **AHT20's "busy" bit**. If status bit 7 is set, the chip is still measuring. You got the bytes too early. Re-trigger or wait longer.
- **Reading without the `t_fine` set first** (BME280). `compensate_P` and `compensate_H` use `t_fine` set by `compensate_T`. Call temp compensation first. otherwise pressure & humidity are wrong.
- **All-`0x80 0x00` reads**. Forgot to write `ctrl_meas` with the forced-mode bit. Chip is asleep.

## 67.12  Going deeper

- **`drivers/iio/pressure/bmp280-core.c`** — the mainline driver in full. Compare every block to the from-scratch version.
- **`drivers/iio/pressure/bmp280-i2c.c`** — the tiny I²C glue.
- **`drivers/iio/humidity/sht3x.c`** — SHT3x.
- **`drivers/iio/humidity/aht20.c`** — AHT20 (newer kernels).
- **BME280 datasheet (Bosch BST-BME280-DS001)** — §4 register map. §8 compensation formulas. Read once, refer back forever.
- **SHT3x datasheet** — command list with CRC polynomial.
- **AHT20 datasheet** — short, English version sometimes hard to find. Chinese version on aosong.com has the bit-packing diagrams.
- **`Documentation/ABI/testing/sysfs-bus-iio*`** — IIO sysfs ABI. tells you what `_processed` vs `_raw` + `_scale` mean.
**ABI** - Application Binary Interface: the calling convention, register use, binary format, and library contract that let separately built code run together.

> Next chapter: **Chapter 68 — Light & color sensors.** Photodiodes meet I²C. BH1750 / TSL2561 / VEML7700 — three approaches to "convert photons to lux."
