---
chapter: 80
title: External ADCs (ADS1115 / ADS1256 / MCP3008 / AD7606)
part: VII — Device cookbook
estimated_pages: 24
status: draft
---

# Chapter 80 — External ADCs

> **What:** four external analog-to-digital converters spanning the price/precision spectrum: **TI ADS1115** (16-bit, I²C, programmable-gain, 4-channel), **TI ADS1256** (24-bit, SPI, ultra-low-noise, 8-channel), **Microchip MCP3008** (10-bit, SPI, cheap, 8-channel), **Analog Devices AD7606** (16-bit, 8-channel *simultaneous-sampling*). For each: protocol, the IIO ADC channel model, and a from-scratch ADS1115 IIO driver. Plus ratiometric measurement (load cells, RTDs) — the trick that cancels reference-voltage error.
> **Why:** the i.MX6ULL's internal ADC is 12-bit, ~1 MS/s, 2 channels, ±a few LSB noisy, and shares the SoC's noisy power rails. For precision measurement — a load-cell scale, a 4-20 mA industrial loop, a thermocouple, simultaneous 3-phase power sampling — you need an external ADC with a clean reference, more bits, or simultaneous channels. Knowing which external ADC fits saves you from chasing noise in a design that was doomed at the silicon level.
> **Focus:** **bits, speed, channels, and simultaneity are independent axes**. ADS1115 = high-bit, slow, multiplexed. MCP3008 = low-bit, medium-speed, cheap. ADS1256 = very-high-bit, low-noise, slow. AD7606 = high-bit, fast, *simultaneous* (all channels sampled at the same instant — critical for phase measurement). Pick by which axis your application stresses.

## 80.1  Chip comparison

| | TI ADS1115 | TI ADS1256 | Microchip MCP3008 | ADI AD7606 |
|---|---|---|---|---|
| Resolution | 16-bit | 24-bit | 10-bit | 16-bit |
| Channels | 4 single / 2 diff | 8 single / 4 diff | 8 single | 8 simultaneous |
| Max sample rate | 860 SPS | 30 kSPS | 200 kSPS | 200 kSPS/ch (all at once) |
| Interface | I²C | SPI | SPI | parallel or SPI |
| Built-in PGA | yes (2/3× – 16×) | yes (1× – 64×) | none | none (±10 V / ±5 V range pins) |
| Reference | internal | external | VDD (ratiometric) | internal 2.5 V |
| ENOB (effective bits) | ~15.5 | ~22 | ~9.5 | ~15.5 |
| Simultaneous? | no (mux) | no (mux) | no (mux) | **yes** |
| Volume price | $3–5 | $10–15 | $2–3 | $20–30 |
| Mainline driver | `ti-ads1015.c` | `ti-ads1256` (recent) | `mcp320x.c` | `ad7606.c` |

**Pick guide:**
- **MCP3008**: cheapest 8-channel; 10-bit is fine for "read a potentiometer / light sensor / battery divider."
- **ADS1115**: 16-bit, PGA, I²C — the everyday precision choice. Load cells, 4-20 mA loops.
- **ADS1256**: 24-bit, lowest noise — strain gauges, lab instruments, weigh scales needing sub-gram resolution.
- **AD7606**: when channels must sample *at the same instant* — 3-phase power analysis, vibration with multiple accelerometers, phase-sensitive detection.

## 80.2  Why not use the SoC's internal ADC?

The i.MX6ULL has 2× 12-bit SAR ADCs. They're fine for "read a battery voltage divider" but limited:

- **12-bit / ~10 ENOB**: ~3 mV resolution on a 3.3 V range. A load cell's signal might be 1 mV full-scale — invisible.
- **Shared noisy rails**: the ADC reference is the SoC's analog supply, polluted by digital switching. The bottom 2 bits are noise.
- **2 channels**: not enough for a multi-sensor product.
- **No PGA**: can't amplify a small signal before conversion.
- **No simultaneity**: SAR ADCs mux; channels sampled at different instants.

An external ADC with a clean reference, a PGA, and more bits transforms what's measurable. The cost is a chip + an I²C/SPI transaction per sample.

## 80.3  Protocol — ADS1115

ADS1115 has just 4 registers, addressed by a 1-byte pointer:

| Pointer | Register | Purpose |
|---------|----------|---------|
| 0x00 | Conversion | 16-bit last result (read-only) |
| 0x01 | Config | mux, PGA, mode, data rate, comparator |
| 0x02 | Lo_thresh | comparator low threshold |
| 0x03 | Hi_thresh | comparator high threshold |

To take a single-shot conversion of channel 0 (AIN0 vs GND):

```
1. Write Config (0x01) = a 16-bit word:
   bit 15:    OS = 1 (start single conversion)
   bits 14:12: MUX = 100 (AIN0 vs GND)
   bits 11:9:  PGA = 010 (±2.048 V full scale)
   bit 8:     MODE = 1 (single-shot)
   bits 7:5:  DR = 100 (128 SPS)
   bits 4:0:  comparator config (disabled = 00011)
   = 0xC383 typical
2. Poll bit 15 of Config (OS bit): 1 = busy, 0 = done.
   (Or wait the conversion time: 1/DR seconds.)
3. Read Conversion register (0x00): 16-bit signed result.
4. Convert: voltage = raw × (full_scale / 32768).
   For PGA ±2.048 V: voltage = raw × 2.048 / 32768 = raw × 62.5 µV.
```

Each register is 16-bit, **big-endian** on the wire. The MUX field selects which input pair; you re-write Config to switch channels (one conversion at a time — it's multiplexed).

The PGA is the killer feature: ±0.256 V full-scale range gives 7.8 µV/LSB — read a thermocouple directly.

## 80.4  How the mainline `ti-ads1015` driver works

Source: `drivers/iio/adc/ti-ads1015.c` (~1000 lines). Covers ADS1015 (12-bit) and ADS1115 (16-bit), and the 4-channel variants.

The driver registers an IIO device with one channel per input configuration (4 single-ended + 4 differential = 8 logical channels). Each channel has a `scale_available` listing the PGA ranges, and a `sampling_frequency_available` listing the data rates.

```c
/* Simplified */
static int ads1015_read_raw(struct iio_dev *indio_dev,
                            struct iio_chan_spec const *chan,
                            int *val, int *val2, long mask)
{
    struct ads1015_data *data = iio_priv(indio_dev);

    switch (mask) {
    case IIO_CHAN_INFO_RAW:
        mutex_lock(&data->lock);
        /* Set the mux to this channel, set PGA, trigger conversion */
        ads1015_set_conv_mode(data, ADS1015_SINGLESHOT);
        regmap_update_bits(data->regmap, ADS1015_CFG_REG,
                           ADS1015_CFG_MUX_MASK,
                           chan->address << ADS1015_CFG_MUX_SHIFT);
        /* Wait for conversion */
        ads1015_get_adc_result(data, chan->address, val);
        mutex_unlock(&data->lock);
        return IIO_VAL_INT;

    case IIO_CHAN_INFO_SCALE:
        /* Return the volts-per-LSB for the current PGA setting */
        *val = ads1015_fullscale_range[data->channel_data[chan->address].pga];
        *val2 = chan->scan_type.realbits - 1;   /* 2^15 */
        return IIO_VAL_FRACTIONAL_LOG2;

    case IIO_CHAN_INFO_SAMP_FREQ:
        *val = ads1015_data_rate[data->channel_data[chan->address].data_rate];
        return IIO_VAL_INT;
    }
    return -EINVAL;
}
```

The driver also supports **buffered/continuous mode** with a data-ready IRQ (the ALERT/RDY pin), and a software-comparator that can fire an IIO event when the input crosses a threshold.

User-space sees:

```
in_voltage0_raw            (AIN0 vs GND, single-ended)
in_voltage0-voltage1_raw   (AIN0 vs AIN1, differential)
in_voltage_scale
in_voltage_scale_available  (the PGA ranges)
sampling_frequency
sampling_frequency_available
```

## 80.5  Writing an ADS1115 IIO driver from scratch

`myads1115.c`:

```c
#include <linux/init.h>
#include <linux/module.h>
#include <linux/i2c.h>
#include <linux/delay.h>
#include <linux/iio/iio.h>

#define REG_CONVERSION  0x00
#define REG_CONFIG      0x01

/* Config field positions */
#define CFG_OS_SINGLE   (1 << 15)
#define CFG_MUX_SHIFT   12
#define CFG_PGA_2_048   (0x2 << 9)   /* ±2.048 V */
#define CFG_MODE_SINGLE (1 << 8)
#define CFG_DR_128SPS   (0x4 << 5)
#define CFG_COMP_DIS    0x0003

struct myads {
    struct i2c_client *client;
    struct mutex lock;
};

static int ma_read16(struct myads *m, u8 reg, u16 *val)
{
    int r = i2c_smbus_read_word_swapped(m->client, reg);   /* big-endian */
    if (r < 0) return r;
    *val = r;
    return 0;
}

static int ma_write16(struct myads *m, u8 reg, u16 val)
{
    return i2c_smbus_write_word_swapped(m->client, reg, val);
}

/* mux 4..7 = AIN0..AIN3 vs GND (single-ended) */
static int ma_read_channel(struct myads *m, int chan, s16 *out)
{
    u16 config, status;
    int err, retries = 50;

    config = CFG_OS_SINGLE
           | ((4 + chan) << CFG_MUX_SHIFT)
           | CFG_PGA_2_048
           | CFG_MODE_SINGLE
           | CFG_DR_128SPS
           | CFG_COMP_DIS;

    err = ma_write16(m, REG_CONFIG, config);
    if (err) return err;

    /* Poll OS bit (bit 15) — 1 = busy, 0 = done */
    do {
        usleep_range(1000, 2000);
        err = ma_read16(m, REG_CONFIG, &status);
        if (err) return err;
    } while (!(status & CFG_OS_SINGLE) && retries--);
    /* note: OS reads 1 when conversion is DONE in single-shot; check datasheet */

    err = ma_read16(m, REG_CONVERSION, (u16 *)out);
    return err;
}

static int ma_read_raw(struct iio_dev *idev,
                       struct iio_chan_spec const *chan,
                       int *val, int *val2, long mask)
{
    struct myads *m = iio_priv(idev);
    s16 raw;
    int err;

    switch (mask) {
    case IIO_CHAN_INFO_RAW:
        mutex_lock(&m->lock);
        err = ma_read_channel(m, chan->channel, &raw);
        mutex_unlock(&m->lock);
        if (err) return err;
        *val = raw;
        return IIO_VAL_INT;
    case IIO_CHAN_INFO_SCALE:
        /* ±2.048 V over 2^15 = 62.5 µV/LSB */
        *val = 0; *val2 = 62500;     /* nano-volts per LSB → IIO_VAL_INT_PLUS_NANO */
        return IIO_VAL_INT_PLUS_NANO;
    }
    return -EINVAL;
}

#define ADS_CHAN(idx) {                                              \
    .type = IIO_VOLTAGE, .indexed = 1, .channel = (idx),             \
    .info_mask_separate = BIT(IIO_CHAN_INFO_RAW),                    \
    .info_mask_shared_by_type = BIT(IIO_CHAN_INFO_SCALE),            \
    .scan_index = (idx),                                             \
    .scan_type = { .sign='s', .realbits=16, .storagebits=16 },       \
}

static const struct iio_chan_spec ma_channels[] = {
    ADS_CHAN(0), ADS_CHAN(1), ADS_CHAN(2), ADS_CHAN(3),
};

static const struct iio_info ma_iio_info = {
    .read_raw = ma_read_raw,
};

static int ma_probe(struct i2c_client *client, const struct i2c_device_id *id)
{
    struct iio_dev *idev;
    struct myads *m;
    s16 test;
    int err;

    idev = devm_iio_device_alloc(&client->dev, sizeof(*m));
    if (!idev) return -ENOMEM;
    m = iio_priv(idev);
    m->client = client;
    mutex_init(&m->lock);

    /* Sanity: a read should succeed */
    err = ma_read_channel(m, 0, &test);
    if (err) return dev_err_probe(&client->dev, err, "test read failed\n");

    idev->name = "myads1115";
    idev->info = &ma_iio_info;
    idev->modes = INDIO_DIRECT_MODE;
    idev->channels = ma_channels;
    idev->num_channels = ARRAY_SIZE(ma_channels);

    return devm_iio_device_register(&client->dev, idev);
}

static const struct of_device_id ma_of_match[] = {
    { .compatible = "linuxlearn,myads1115" },
    { }
};
MODULE_DEVICE_TABLE(of, ma_of_match);

static const struct i2c_device_id ma_id[] = { { "myads1115", 0 }, { } };
MODULE_DEVICE_TABLE(i2c, ma_id);

static struct i2c_driver ma_driver = {
    .driver = {
        .name = "myads1115",
        .of_match_table = ma_of_match,
    },
    .probe = ma_probe,
    .id_table = ma_id,
};
module_i2c_driver(ma_driver);

MODULE_LICENSE("GPL");
```

DT:

```dts
&i2c1 {
    ads1115@48 {
        compatible = "linuxlearn,myads1115";
        reg = <0x48>;
    };
};
```

Test:

```
[root@pa-mini:~]# insmod myads1115.ko
[root@pa-mini:~]# cat /sys/bus/iio/devices/iio:device0/in_voltage0_raw
16384
[root@pa-mini:~]# cat /sys/bus/iio/devices/iio:device0/in_voltage_scale
0.000062
[root@pa-mini:~]# # → 16384 × 62.5 µV = 1.024 V on AIN0
```

Driver is ~180 lines, gives 16-bit single-ended reads on 4 channels via IIO. The full mainline driver adds differential channels, runtime PGA selection, continuous mode, comparator events.

## 80.6  MCP3008 — SPI, cheap, 10-bit

MCP3008 we already met in Ch 47 (SPI drivers). Its protocol: a 3-byte SPI transaction encodes the channel and returns a 10-bit result. The mainline driver `drivers/iio/adc/mcp320x.c` covers the MCP320x/MCP330x family.

```c
/* The 3-byte command from Ch 47 */
u8 tx[3] = { 0x01, (u8)(0x80 | (channel << 4)), 0x00 };
u8 rx[3];
/* result = ((rx[1] & 0x03) << 8) | rx[2]; */
```

DT:

```dts
&ecspi3 {
    adc@0 {
        compatible = "microchip,mcp3008";
        reg = <0>;
        spi-max-frequency = <1000000>;
        vref-supply = <&reg_3v3>;       /* ratiometric: scale = vref / 1024 */
    };
};
```

`vref-supply` is important: MCP3008 is *ratiometric* — its full-scale equals VREF (typically VDD). The driver reads the regulator's voltage and computes the scale. So `in_voltage_scale` = VREF / 1024.

## 80.7  ADS1256 — 24-bit, low-noise

ADS1256 is the precision SPI ADC: 24-bit, programmable gain to 64×, 30 kSPS max, but with a beautiful noise floor (~22 ENOB at low data rates). For a load cell measuring a few-mV signal, this is the chip.

Protocol: SPI commands (RDATA, WREG, RREG, SYNC), a register set for gain/rate/mux, and a DRDY pin that goes low when a conversion is ready. The mainline driver is `drivers/iio/adc/ti-ads1256.c` (recent kernels) or out-of-tree variants.

The complexity: ADS1256 has a strict timing relationship between DRDY, the command, and the data read. You must wait for DRDY, issue RDATA, wait t6 (~6.5 × master clock period), then clock out 3 bytes. Get the timing wrong and you read stale or corrupt data.

## 80.8  AD7606 — simultaneous sampling

AD7606 is unique here: **all 8 channels sample at the same instant**. A single CONVST (convert-start) pulse triggers all 8 sample-and-hold circuits simultaneously; then you read the 8 results sequentially (parallel bus or SPI).

Why this matters: for 3-phase power measurement, you need voltage and current of all three phases captured at the *same* moment to compute true power and phase angle. A multiplexed ADC samples them microseconds apart — at 50/60 Hz that's a fraction of a degree of phase error, but for harmonics and transients it matters.

```
   CONVST↓ ──► all 8 S/H freeze simultaneously
   BUSY goes high during conversion (~4 µs)
   BUSY↓ ──► read 8 × 16-bit results over parallel bus or SPI
```

The mainline driver `drivers/iio/adc/ad7606.c` uses a GPIO for CONVST, a GPIO IRQ for BUSY, and either parallel-bus or SPI read. The DT specifies range pins, oversampling pins, etc. This is a more involved driver because of the parallel-bus option and the strict CONVST/BUSY handshake.

## 80.9  Ratiometric measurement — the noise-cancellation trick

For sensors that are *resistive dividers excited by the ADC's reference* — load cells, RTDs, potentiometers — there's a beautiful trick: make the measurement *ratiometric*.

A load cell is a Wheatstone bridge. Excite it with voltage Vexc; the output is `Vout = Vexc × (sensitivity × load)`. If you also use Vexc as the ADC's reference, then:

```
ADC_reading = Vout / Vref = Vout / Vexc = sensitivity × load
```

The Vexc *cancels*. Any noise or drift in the excitation voltage cancels too — the reading depends only on the load, not on the absolute excitation. This is why precision scales use ratiometric ADCs (ADS1256, HX711): the reference and the bridge excitation are the same rail.

To do this: wire the ADC's REF+ / REF− to the same rail that excites the bridge. In DT, the `vref-supply` points at the excitation regulator. The ADC's `scale` becomes meaningless in absolute volts but the *ratio* is rock-stable.

## 80.10  Lab

1. **ADS1115 bring-up.** Wire to I²C1; address 0x48 (ADDR→GND). Feed AIN0 from a potentiometer between 3.3 V and GND.
2. **Build and load `myads1115.ko`.** Turn the pot; verify `in_voltage0_raw` sweeps 0 → 32767.
3. **PGA experiment.** Modify the driver to use ±0.256 V range (PGA = 0x5). Feed a small signal (~100 mV); verify the higher resolution.
4. **MCP3008 comparison.** Wire an MCP3008 too. Read the same pot via both. Compare 10-bit vs 16-bit resolution side by side.
5. **Ratiometric load cell.** If you have a load cell + HX711 or ADS1256: wire the ADC reference to the bridge excitation. Verify that varying the supply voltage by ±5 % doesn't change the reading (ratiometric cancellation).
6. **Switch to mainline.** Use `compatible = "ti,ads1115"`. Verify `in_voltage_scale_available` shows the PGA ranges; write one to change range.
7. **AD7606 simultaneity** (if available). Sample two phase-shifted sine waves; verify the captured samples preserve the phase relationship (multiplexed ADC would smear it).

Commit code to `code/ch80-external-adc/`.

## 80.11  Pitfalls

- **ADS1115 OS-bit polarity confusion.** In single-shot: writing OS=1 *starts* a conversion; reading OS=1 means *idle/done*, OS=0 means *converting*. Easy to get backwards. Check the datasheet's "Operational Status" description carefully (it's counterintuitive).
- **PGA range vs input voltage.** If your signal exceeds the PGA range, the reading clips at ±32767. ADS1115's ±0.256 V range clips anything above 256 mV. Pick the range to fit your signal with margin.
- **Input above VDD.** ADS1115 inputs must be within GND−0.3 V to VDD+0.3 V. A 5 V signal into a 3.3 V-powered ADS1115 damages it. Use a divider.
- **Ratiometric misunderstanding.** Ratiometric works only when the sensor is excited *by the same reference*. A 4-20 mA loop is *not* ratiometric (it's a current source); use absolute reference there.
- **MCP3008 vref vs vdd.** MCP3008 has separate VDD and VREF pins. If VREF < VDD, the usable input range is limited to VREF. Tie them together for full-range.
- **SPI clock too fast for MCP3008.** Max 3.6 MHz at 5 V, 1.35 MHz at 2.7 V. Exceeding it gives noise. Stay at 1 MHz to be safe.
- **ADS1256 DRDY timing.** Must wait for DRDY low before reading; must respect t6 delay after RDATA command. Race conditions give corrupt data.
- **AD7606 oversampling pins.** OS[2:0] pins set hardware oversampling. If left floating, behavior is undefined. Strap or GPIO them.
- **Grounding.** External ADCs need a clean analog ground separate from digital ground, joined at one point (star ground). A noisy ground negates the precision you paid for.

## 80.12  Going deeper

- **`drivers/iio/adc/ti-ads1015.c`** — production ADS1015/1115 driver.
- **`drivers/iio/adc/mcp320x.c`** — MCP3008 family.
- **`drivers/iio/adc/ad7606.c`** — simultaneous-sampling ADC with parallel + SPI variants.
- **ADS1115 datasheet (TI SBAS444)** — config register bit-fields; OS-bit semantics.
- **ADS1256 datasheet (TI SBAS288)** — timing diagrams for the DRDY/RDATA handshake.
- **AD7606 datasheet (ADI)** — CONVST/BUSY handshake.
- **TI app note SLYT423** — "How delta-sigma ADCs work" (for understanding ADS1256's 24-bit precision).
- **`Documentation/devicetree/bindings/iio/adc/`** — DT bindings for each.

> Next chapter: **Chapter 81 — External DACs + clock generators.** Analog *output* (MCP4725, AD5663) and programmable clock generation (Si5351) — the inverse of this chapter, plus the clk-framework integration.
