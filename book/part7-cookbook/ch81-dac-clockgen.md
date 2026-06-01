---
chapter: 81
title: External DACs + clock generators (MCP4725 / AD5663 / Si5351)
part: VII — Device cookbook
estimated_pages: 20
status: draft
---

# Chapter 81 — External DACs + clock generators

> **What:** analog *output* and clock *generation* — the inverse of Chapter 80. **Microchip MCP4725** (12-bit I²C DAC with EEPROM), **Analog Devices AD5663** (16-bit dual SPI DAC), and **SiLabs Si5351** (programmable 3-output clock generator). For each: protocol, the IIO `out_voltage` model (DACs) or the `clk` framework (Si5351), and a from-scratch MCP4725 IIO DAC driver.
> **Why:** embedded systems sometimes need to *produce* an analog voltage (control a VCO, set a programmable power-supply setpoint, generate a waveform) or *produce a precise clock* (drive an SDR mixer, clock an external ADC, generate a reference frequency). The SoC has neither a DAC nor flexible clock outputs in most cases. These three chips cover the common cases, and they introduce two new frameworks: IIO's output channels and the kernel's `clk` provider model.
> **Focus:** A DAC is an IIO channel that flows out instead of in. A clock generator is a `clk` provider. DAC: `out_voltage0_raw` is *writable*; writing it sets the output voltage. Clock gen: the chip registers as a `clk` in the kernel clock tree, and other devices (or user-space via `/sys/.../clk`) consume its output. These are two different frameworks; both are useful.

## 81.1  Chip comparison

| | Microchip MCP4725 | ADI AD5663 | SiLabs Si5351A |
|---|---|---|---|
| Function | 12-bit DAC | dual 16-bit DAC | 3-output clock generator |
| Interface | I²C | SPI | I²C |
| Channels | 1 | 2 | 3 (clock outputs) |
| Output range | 0 – VDD | 0 – VREF | 2.5 kHz – 200 MHz |
| Settling time | 6 µs | 5 µs | n/a |
| EEPROM (power-on default) | yes | no | optional (Si5351B) |
| I²C / SPI address | 0x60–0x67 | (SPI CS) | 0x60 / 0x61 |
| Volume price | $1–2 | $5–8 | $1.50–3 |
| Mainline driver | `mcp4725.c` | `ad5446.c` family | `clk-si5351.c` |

**Pick guide:**
- **MCP4725**: cheap single-channel analog output. Set a control voltage, generate slow waveforms.
- **AD5663**: dual-channel, 16-bit, faster — stereo control, precision setpoints.
- **Si5351**: programmable clocks for RF, SDR, clocking external chips. Up to 200 MHz, arbitrary frequencies.

## 81.2  MCP4725 — the simplest DAC

MCP4725 takes a 12-bit value and outputs `V = (value / 4096) × VDD`. Two write modes:

- **Fast write**: 2 bytes — just the 12-bit value. Updates output immediately.
- **Write + EEPROM**: 3 bytes — value + store to EEPROM (so the chip powers up at this value next time).

Fast-write protocol:

```
   START | 0xC0 | (D11..D8 in low nibble) | (D7..D0) | STOP
   Actually: byte0 = (mode << 4) | (D11..D8); byte1 = D7..D0
   Fast mode: byte0 = 0x0_ where high nibble bits select mode (00 = normal)
```

Specifically, fast write:

```c
u8 buf[2];
buf[0] = (value >> 8) & 0x0F;     /* upper 4 bits, mode = normal (00) */
buf[1] = value & 0xFF;            /* lower 8 bits */
i2c_master_send(client, buf, 2);
```

Write with EEPROM (3 bytes):

```c
u8 buf[3];
buf[0] = 0x60;                    /* command: write DAC + EEPROM */
buf[1] = (value >> 4) & 0xFF;     /* D11..D4 */
buf[2] = (value << 4) & 0xF0;     /* D3..D0 in upper nibble */
i2c_master_send(client, buf, 3);
```

(The two formats pack the 12 bits differently — fast write splits 4+8, EEPROM write splits 8+4. Datasheet figures 6-1 and 6-2.)

## 81.3  IIO output channels

DACs use IIO too, but with `output = 1` channels. The key difference: the channel exposes a *writable* `out_voltageN_raw`.

```c
static const struct iio_chan_spec dac_channels[] = {
    {
        .type = IIO_VOLTAGE,
        .indexed = 1,
        .channel = 0,
        .output = 1,                 /* ← this makes it an output */
        .info_mask_separate = BIT(IIO_CHAN_INFO_RAW)
                            | BIT(IIO_CHAN_INFO_SCALE),
    },
};
```

And the driver implements `write_raw` (in addition to or instead of `read_raw`):

```c
static int dac_write_raw(struct iio_dev *idev,
                         struct iio_chan_spec const *chan,
                         int val, int val2, long mask)
{
    /* val is the new raw DAC code; program it into the chip */
}
```

User-space:

```
[root@pa-mini:~]# echo 2048 > /sys/bus/iio/devices/iio:device0/out_voltage0_raw
[root@pa-mini:~]# # → output = 2048/4096 × VDD = VDD/2 = 1.65 V
```

## 81.4  Writing an MCP4725 IIO DAC driver from scratch

`mymcp4725.c`:

```c
#include <linux/init.h>
#include <linux/module.h>
#include <linux/i2c.h>
#include <linux/iio/iio.h>

struct mymcp {
    struct i2c_client *client;
    struct mutex lock;
    u16 last_value;          /* cache for read-back */
    u32 vref_mV;             /* reference (= VDD) in mV */
};

/* Fast write: 2 bytes, mode = normal */
static int mc_set(struct mymcp *m, u16 value)
{
    u8 buf[2];
    int err;

    value &= 0x0FFF;
    buf[0] = (value >> 8) & 0x0F;
    buf[1] = value & 0xFF;

    err = i2c_master_send(m->client, buf, 2);
    if (err != 2) return err < 0 ? err : -EIO;
    m->last_value = value;
    return 0;
}

static int mc_read_raw(struct iio_dev *idev,
                       struct iio_chan_spec const *chan,
                       int *val, int *val2, long mask)
{
    struct mymcp *m = iio_priv(idev);

    switch (mask) {
    case IIO_CHAN_INFO_RAW:
        *val = m->last_value;     /* return the cached DAC code */
        return IIO_VAL_INT;
    case IIO_CHAN_INFO_SCALE:
        /* scale = VDD / 4096, expressed as mV-per-LSB */
        *val = m->vref_mV;
        *val2 = 12;               /* 2^12 */
        return IIO_VAL_FRACTIONAL_LOG2;
    }
    return -EINVAL;
}

static int mc_write_raw(struct iio_dev *idev,
                        struct iio_chan_spec const *chan,
                        int val, int val2, long mask)
{
    struct mymcp *m = iio_priv(idev);
    int err;

    if (mask != IIO_CHAN_INFO_RAW) return -EINVAL;
    if (val < 0 || val > 4095) return -EINVAL;

    mutex_lock(&m->lock);
    err = mc_set(m, val);
    mutex_unlock(&m->lock);
    return err;
}

static const struct iio_chan_spec mc_channels[] = {
    {
        .type = IIO_VOLTAGE,
        .indexed = 1,
        .channel = 0,
        .output = 1,
        .info_mask_separate = BIT(IIO_CHAN_INFO_RAW) | BIT(IIO_CHAN_INFO_SCALE),
    },
};

static const struct iio_info mc_iio_info = {
    .read_raw  = mc_read_raw,
    .write_raw = mc_write_raw,
};

static int mc_probe(struct i2c_client *client)
{
    struct iio_dev *idev;
    struct mymcp *m;
    int err;

    idev = devm_iio_device_alloc(&client->dev, sizeof(*m));
    if (!idev) return -ENOMEM;
    m = iio_priv(idev);
    m->client = client;
    m->vref_mV = 3300;        /* assume VDD = 3.3 V; could read a regulator */
    mutex_init(&m->lock);

    of_property_read_u32(client->dev.of_node, "vref-millivolt", &m->vref_mV);

    /* Set output to mid-scale at startup */
    err = mc_set(m, 2048);
    if (err) return dev_err_probe(&client->dev, err, "initial set failed\n");

    idev->name = "mymcp4725";
    idev->info = &mc_iio_info;
    idev->modes = INDIO_DIRECT_MODE;
    idev->channels = mc_channels;
    idev->num_channels = ARRAY_SIZE(mc_channels);

    return devm_iio_device_register(&client->dev, idev);
}

static const struct of_device_id mc_of_match[] = {
    { .compatible = "linuxlearn,mymcp4725" },
    { }
};
MODULE_DEVICE_TABLE(of, mc_of_match);

static const struct i2c_device_id mc_id[] = { { "mymcp4725", 0 }, { } };
MODULE_DEVICE_TABLE(i2c, mc_id);

static struct i2c_driver mc_driver = {
    .driver = {
        .name = "mymcp4725",
        .of_match_table = mc_of_match,
    },
    .probe = mc_probe,
    .id_table = mc_id,
};
module_i2c_driver(mc_driver);

MODULE_LICENSE("GPL");
```

DT:

```dts
&i2c1 {
    dac@60 {
        compatible = "linuxlearn,mymcp4725";
        reg = <0x60>;
        vref-millivolt = <3300>;
    };
};
```

Test:

```
[root@pa-mini:~]# insmod mymcp4725.ko
[root@pa-mini:~]# echo 0 > /sys/bus/iio/devices/iio:device0/out_voltage0_raw
[root@pa-mini:~]# # measure output: 0 V
[root@pa-mini:~]# echo 4095 > /sys/bus/iio/devices/iio:device0/out_voltage0_raw
[root@pa-mini:~]# # measure output: ~3.3 V
[root@pa-mini:~]# echo 2048 > /sys/bus/iio/devices/iio:device0/out_voltage0_raw
[root@pa-mini:~]# # measure output: ~1.65 V
```

Generate a slow sine wave from user-space:

```sh
#!/bin/sh
while true; do
  for i in $(seq 0 36); do
    # 12-bit sine: 2048 + 2047*sin(i*10°)
    v=$(awk "BEGIN{print int(2048 + 2047*sin($i*0.1745))}")
    echo $v > /sys/bus/iio/devices/iio:device0/out_voltage0_raw
    usleep 5000
  done
done
```

~5 Hz sine on a scope. For faster/cleaner waveforms, write a kernel-side waveform generator or use the AD5663 (faster SPI).

Driver is ~120 lines; gives writable IIO output. Mainline `mcp4725.c` adds EEPROM persistence, power-down modes, and read-back of the actual chip register.

## 81.5  AD5663 — dual 16-bit SPI DAC

AD5663 is two 16-bit DACs in one package, SPI-controlled. Each write is a 24-bit SPI frame: 8 command/address bits + 16 data bits.

```
   bits 23:22: reserved
   bits 21:19: command (e.g., 011 = write + update DAC)
   bits 18:17: address (which DAC: 00=A, 01=B, 11=both)
   bits 16:0:  16-bit data
```

The mainline `drivers/iio/dac/ad5446.c` covers the AD5446/AD5663 family. Two `out_voltage` channels (`out_voltage0_raw`, `out_voltage1_raw`).

Use AD5663 over MCP4725 when you need: 16-bit precision, two synchronized channels, faster update (SPI at 10+ MHz vs I²C at 400 kHz), or external precision reference.

## 81.6  Si5351 — programmable clock generator, and the clk framework

Si5351 is different from the DACs: it produces *clocks*, not voltages. It has a 25 MHz crystal, two internal PLLs, and three output dividers — letting it synthesize almost any frequency from 2.5 kHz to 200 MHz on each of three outputs.

This integrates with the kernel's **clk framework** — the same framework that manages the SoC's internal clock tree (Ch 13, Ch 25). The Si5351 registers as a **clock provider**; its outputs become entries in the kernel clock tree that other devices can consume.

### How clocks flow

```
   25 MHz XTAL ──► Si5351 PLL_A ──► Output divider 0 ──► CLK0 (e.g., 100 MHz)
                          PLL_A ──► Output divider 1 ──► CLK1 (e.g., 13.56 MHz)
                          PLL_B ──► Output divider 2 ──► CLK2 (e.g., 27 MHz)
```

The frequency synthesis: `f_out = f_xtal × (PLL_mult) / (output_divider)`. The PLL multiplier is a fractional value (a + b/c), giving fine resolution. The math to derive (a, b, c, divider) for a target frequency is non-trivial — the driver does it.

### DT

```dts
&i2c1 {
    si5351: clock-generator@60 {
        compatible = "silabs,si5351a";
        reg = <0x60>;
        #clock-cells = <1>;
        clocks = <&ref25m>;            /* 25 MHz crystal input */
        clock-names = "xtal";

        /* Per-output config via child nodes */
        clkout0 {
            reg = <0>;
            silabs,drive-strength = <8>;        /* mA */
            silabs,multisynth-source = <0>;     /* PLL A */
            silabs,clock-source = <0>;
            clock-frequency = <100000000>;       /* 100 MHz */
        };
        clkout2 {
            reg = <2>;
            silabs,multisynth-source = <1>;     /* PLL B */
            clock-frequency = <27000000>;        /* 27 MHz */
        };
    };
};

/* A device consuming the Si5351's CLK0 */
some_device {
    clocks = <&si5351 0>;          /* phandle + output index */
    clock-names = "ref-clock";
};
```

The consuming device, in its driver, does:

```c
struct clk *clk = devm_clk_get(&pdev->dev, "ref-clock");
clk_prepare_enable(clk);
unsigned long rate = clk_get_rate(clk);    /* 100000000 */
clk_set_rate(clk, 48000000);                /* retune to 48 MHz */
```

So the Si5351's outputs become first-class kernel clocks — the same `clk_get` / `clk_set_rate` API used for SoC clocks. A consumer driver doesn't know or care that the clock comes from an external I²C chip.

### User-space access

```
[root@pa-mini:~]# cat /sys/kernel/debug/clk/clk_summary | grep si5351
   si5351_clkout0    1   1   100000000   ...
   si5351_clkout2    1   1    27000000   ...
```

The `clk_summary` debugfs file lists every clock in the tree, including the Si5351's outputs.

### Mainline driver

`drivers/clk/clk-si5351.c` (~1700 lines) implements the full frequency-synthesis math, PLL configuration, and clk-provider registration. Writing this from scratch is a *substantial* effort (the (a,b,c,divider) solver is the hard part). Reimplementing Si5351's PLL math is not a productive exercise — read the existing driver instead. The chapter shows the clk-framework integration conceptually; reimplementing the Si5351's PLL math is left as an advanced exercise.

A from-scratch clk provider *skeleton* (for a fixed-frequency case) looks like:

```c
static unsigned long my_clk_recalc_rate(struct clk_hw *hw, unsigned long parent)
{
    struct my_clk *c = to_my_clk(hw);
    return c->current_rate;
}

static int my_clk_set_rate(struct clk_hw *hw, unsigned long rate,
                           unsigned long parent)
{
    struct my_clk *c = to_my_clk(hw);
    /* Compute and program the chip's PLL + divider registers for `rate` */
    c->current_rate = rate;
    return 0;
}

static const struct clk_ops my_clk_ops = {
    .recalc_rate = my_clk_recalc_rate,
    .set_rate    = my_clk_set_rate,
    .round_rate  = my_clk_round_rate,
};

/* In probe: */
struct clk_init_data init = {
    .name = "my-clkout0",
    .ops = &my_clk_ops,
    .parent_names = (const char *[]){ "xtal" },
    .num_parents = 1,
};
c->hw.init = &init;
err = devm_clk_hw_register(&client->dev, &c->hw);
of_clk_add_hw_provider(client->dev.of_node, of_clk_hw_simple_get, &c->hw);
```

That registers a clk that consumers can `clk_get`. The hard part — the actual PLL math in `set_rate` — is chip-specific.

## 81.7  Lab

1. **MCP4725 bring-up.** Wire to I²C1 at 0x60. Build and load `mymcp4725.ko`.
2. **Voltage sweep.** Write 0, 1024, 2048, 3072, 4095 to `out_voltage0_raw`; measure output with a multimeter; verify linear 0 → VDD.
3. **Sine generation.** Run the shell script in §81.4; scope the output. Note the staircase quantization at 12-bit.
4. **Switch to mainline.** `compatible = "microchip,mcp4725"`. Try writing to EEPROM via the mainline driver's persistence (chip powers up at saved value next boot).
5. **AD5663** (if available). Configure on SPI; verify two channels with 16-bit resolution. Compare cleaner waveform vs MCP4725.
6. **Si5351 clock gen.** Configure in DT for 100 MHz on CLK0. Scope the output. Verify `cat /sys/kernel/debug/clk/clk_summary` shows the clock.
7. **Si5351 consumer.** Wire CLK0 to an external chip (e.g., an ADC's master clock). In the consuming driver, `clk_get` + `clk_set_rate`; verify the Si5351 retunes.

## 81.8  Pitfalls

- **MCP4725 bit-packing.** Fast-write packs 12 bits as 4+8; EEPROM-write packs as 8+4. Mixing them up produces a value 16× off. Datasheet figures 6-1 / 6-2.
- **DAC output loading.** MCP4725 can source or sink only a few mA. Driving a low-impedance load directly causes the output voltage to drop. Buffer with an op-amp follower for current.
- **DAC output range = VDD.** MCP4725's full-scale is VDD, not a fixed reference. If VDD is noisy (shared digital rail), the output is noisy. Use a clean rail or AD5663 with external reference.
- **EEPROM write endurance.** MCP4725's EEPROM is rated ~1M cycles. Don't write EEPROM on every output change (use fast-write); reserve EEPROM-write for "set the power-on default."
- **Si5351 PLL constraints.** Each PLL must run between 600 and 900 MHz internally. The output dividers are 4 to 2048. Not every target frequency is achievable on every output. The driver's solver picks the closest valid combination. Verify the actual rate via `clk_get_rate`.
- **Si5351 output drive vs load.** Output drive strength (2/4/6/8 mA) must match the load (50 Ω termination etc.). Wrong drive = distorted clock or ringing.
- **Clock consumer ordering.** If a device's `clk_get` happens before the Si5351 driver probes, it gets `-EPROBE_DEFER`. The kernel retries; usually fine. But circular clock dependencies deadlock.
- **#clock-cells mismatch.** Si5351 has `#clock-cells = <1>` (the output index is the cell). A consumer referencing `<&si5351>` without the index fails. Always `<&si5351 N>`.

## 81.9  Going deeper

- **`drivers/iio/dac/mcp4725.c`** — production MCP4725/4726 driver with EEPROM + power-down.
- **`drivers/iio/dac/ad5446.c`** — AD5446/AD5663 family.
- **`drivers/clk/clk-si5351.c`** — the Si5351 clk provider; study the `si5351_*_set_rate` math.
- **`Documentation/driver-api/clk.rst`** — the clk framework provider/consumer model.
- **`drivers/clk/clk.c`** — the clk core.
- **MCP4725 datasheet (Microchip)** — write-format figures.
- **AD5663 datasheet (ADI)** — 24-bit SPI frame layout.
- **Si5351 datasheet + AN619 (SiLabs)** — "Manually generating an Si5351 register map" — the PLL math reference.
- **`Documentation/devicetree/bindings/clock/silabs,si5351.yaml`** — DT binding.

---

> **End of Group G — Analog conversion & clock generation (Ch 80–81).** ADCs in (Ch 80), DACs + clocks out (Ch 81). Both wrap into IIO (`out_voltage`) or the clk framework. The Si5351 is also our first encounter with writing a kernel *clock provider*.

> Next chapter: **Chapter 82 — RGB parallel LCD on LCDIF.** Group H (Displays) opens with the i.MX6ULL's native parallel-RGB display interface: panel timings, `panel-simple`, the DRM bridge, and bringing up a real ATK panel.
