---
chapter: 75
title: Current & power monitoring (INA219 / INA226 / INA3221)
part: VII — Device cookbook
estimated_pages: 20
status: draft
---

# Chapter 75 — Current & power monitoring

> **What:** three I²C high-side current/voltage monitors from Texas Instruments: **INA219** (12-bit, the classic), **INA226** (16-bit, modern, programmable averaging), **INA3221** (3-channel, simultaneous-sample 3-rail monitor). For each: physics, register map, the *calibration register* that everyone gets wrong, and a from-scratch INA219 driver. Plus the **hwmon** subsystem — the sibling of IIO that current monitors usually live in.
> **Why:** every device that draws power benefits from knowing how much. Production telemetry (per-rail consumption logged to fleet management), fault detection (overcurrent → shutdown), low-power optimisation (which subsystem ate the budget?), battery-life prediction. INA219 in particular costs $1.50 and lets you watch any 0–26 V rail at 1 mA resolution.
> **Focus:** **the shunt converts current to voltage; the chip converts voltage to digital, then divides by shunt to recover current**. Get the shunt size right (low enough to not waste power; high enough to get good resolution) and program the calibration register to match — the chip then reports current directly in amperes. Forget the calibration register and you read garbage scaled by an unknown factor.

## 75.1  Chip comparison

| | TI INA219 | TI INA226 | TI INA3221 |
|---|---|---|---|
| Channels | 1 | 1 | 3 |
| Bus voltage range | 0–26 V | 0–36 V | 0–26 V |
| Shunt voltage resolution | 10 µV (LSB, 12-bit) | 2.5 µV (LSB, 16-bit) | 40 µV (LSB, 13-bit) |
| Max shunt voltage | ±320 mV | ±81.92 mV | ±163.8 mV |
| Bus voltage LSB | 4 mV | 1.25 mV | 8 mV |
| ADC conversion time | 532 µs (12-bit) | 8.244 ms (16-bit, 1024 avg) | configurable |
| Average filter | none | up to 1024-sample average | up to 1024 average per chan |
| I²C address | 0x40 (4 pin-strapped variants → up to 16 chips on one bus) | 0x40 (16 variants) | 0x40 (4 variants) |
| I²C clock | 100 kHz / 400 kHz / 2.94 MHz (HS) | up to 2.94 MHz | up to 2.94 MHz |
| Alert pin | none | overcurrent / under/over voltage / power threshold | one per channel |
| Volume price | $1.50–2.50 | $3–5 | $4–6 |
| Linux driver | `hwmon/ina2xx.c` | `hwmon/ina2xx.c` | `hwmon/ina3221.c` |

**Pick guide:**
- **INA219**: cheap, fast (~500 µs), one rail. 1 mA resolution typically.
- **INA226**: better noise, programmable averaging, alert pin. Power-budget profiling.
- **INA3221**: 3 rails at once with their own alerts. Multi-rail system telemetry.

## 75.2  The physics — shunt + amplifier

You measure current with a low-value precision resistor (the **shunt**) in series with the load:

```
   ┌────── VBUS_IN ──────────────────► load
   │                     ┌────────┐
   │   ┌─────────────────┤        │   (V_shunt = I_load × R_shunt)
   │   │                 │ shunt  │
   │   │  ┌──────────────┤   R    │
   │   │  │              │        │
   │   │  │              └────────┘
   │   ↓  ↓ V+, V-
   │   ┌──┴──┐
   │   │ INA │ ADC of (V+ − V−)
   │   │ 2xx │ ADC of (VBUS to GND)
   │   └─────┘
   │
   GND
```

The INA's two inputs straddle the shunt; the chip's ADC measures the differential voltage. A separate ADC measures the bus voltage relative to GND.

**Shunt selection** is the design decision:

- Too small (< 0.01 Ω): poor resolution; noise limits accuracy.
- Too large (> 0.5 Ω): wastes power; voltage drop on the rail.
- Sweet spot: choose `R_shunt = V_shunt_max / I_max` where V_shunt_max ≈ 50 mV (well below INA's 320 mV max).

Example: monitoring a rail expected to draw up to 2 A. R_shunt = 50 mV / 2 A = 25 mΩ. Power dissipation: I² × R = 4 × 0.025 = 100 mW (use a 1/4 W resistor with margin). Resolution: 10 µV / 25 mΩ = 0.4 mA per LSB.

## 75.3  Protocol — INA219

Register map:

| Reg | Name | Purpose |
|-----|------|---------|
| 0x00 | Configuration | bus range, gain, ADC resolution, mode |
| 0x01 | Shunt Voltage | signed 16-bit, LSB = 10 µV |
| 0x02 | Bus Voltage | bits 15:3 = bus voltage / 4 mV; bit 1 = CNVR; bit 0 = OVF |
| 0x03 | Power | calculated by chip = current × bus_voltage (LSB = 20 × current_LSB) |
| 0x04 | Current | calculated by chip = shunt_voltage × CAL >> 12 |
| 0x05 | Calibration | the magic register |

Each register is 16 bits, **big-endian** on the wire. A read of register 0x02 looks like:

```
   Host: START | 0x80 | 0x02 | START | 0x81 | (2 bytes MSB,LSB) | STOP
```

(0x40 << 1 = 0x80 for write; 0x40 << 1 | 1 = 0x81 for read.)

### The calibration register — finally explained

The chip's internal `Current` register doesn't measure current directly. It computes:

```
Current_register = (Shunt_voltage × Calibration_register) / 4096
```

You program the Calibration register with a value that makes Current_register read out in your chosen units (mA, 100 µA, etc.).

The formula (from datasheet):

```
Calibration = trunc(0.04096 / (Current_LSB × R_shunt))
```

Where:
- `Current_LSB` is the unit you want for the current reading. E.g., 0.0001 A/LSB = 100 µA per count.
- `R_shunt` is in ohms.

Example: 25 mΩ shunt, want 100 µA/LSB.

```
Cal = trunc(0.04096 / (0.0001 × 0.025))
    = trunc(0.04096 / 0.0000025)
    = trunc(16384)
    = 16384
```

Write 16384 (0x4000) to register 0x05. Now `Current_register` reads in units of 100 µA. A reading of 1234 → 1234 × 100 µA = 123.4 mA.

**Power register** (0x03) auto-computes as `(Current × BusVoltage) >> 11` with LSB = `20 × Current_LSB`. If `Current_LSB = 100 µA`, `Power_LSB = 2 mW`.

The fixed `4096` and `0.04096` and `2048` (for power) come from the ADC's internal scaling — they're not adjustable, they're physical constants of the chip's design. The Calibration register is just a multiplier that maps "raw shunt voltage" to "current in your units."

This is the part everyone gets wrong. Without programming Calibration:

- The Shunt Voltage register *does* work — it reads in 10 µV units regardless.
- The Bus Voltage register works.
- The Current register reads zero (Cal = 0 ⇒ Current = 0).
- The Power register reads zero.

So a "first-light" sanity check that just reads Shunt Voltage will work fine and seem to confirm everything... and then you wonder why Current reads zero.

## 75.4  How the mainline `ina2xx` driver works

Source: `drivers/hwmon/ina2xx.c` (~700 lines). Covers INA219, INA220, INA226, INA230, INA231 — the whole INA family.

The driver auto-detects which chip based on `compatible` strings, looks up its parameters from a per-chip `ina2xx_config` table, and registers an hwmon device. The hwmon framework exposes `/sys/class/hwmon/hwmon0/in0_input`, `curr1_input`, `power1_input` — same shape across all hwmon-class drivers.

```c
/* Simplified */
struct ina2xx_config {
    u16  config_default;
    int  calibration_value;   /* default; user can override via shunt-resistor + current-lsb */
    int  registers;            /* number of valid registers */
    int  shunt_div;            /* divisor mapping raw shunt voltage to µV */
    int  bus_voltage_shift;    /* shift for bus-voltage register */
    int  bus_voltage_lsb;      /* µV/LSB */
    int  power_lsb_factor;    /* multiplier to current_lsb */
};

static const struct ina2xx_config ina2xx_config[] = {
    [ina219] = {
        .config_default     = 0x399F,         /* 32 V, ±320 mV, 12-bit, continuous */
        .calibration_value  = 4096,
        .shunt_div          = 100,            /* 10 µV/LSB ⇒ multiply by 10 to get µV  */
        .bus_voltage_shift  = 3,
        .bus_voltage_lsb    = 4000,           /* 4 mV/LSB */
        .power_lsb_factor   = 20,             /* power_lsb = 20 × current_lsb */
    },
    [ina226] = {
        .config_default     = 0x4127,
        .calibration_value  = 2048,
        .shunt_div          = 400,            /* 2.5 µV/LSB */
        .bus_voltage_shift  = 0,
        .bus_voltage_lsb    = 1250,
        .power_lsb_factor   = 25,
    },
};

static int ina2xx_init(struct ina2xx_data *data, struct device *dev)
{
    int err;

    /* Write configuration register (set ranges, gain, conversion mode) */
    err = regmap_write(data->regmap, INA2XX_CONFIG, data->config->config_default);

    /* Compute calibration based on user-supplied shunt resistor */
    /* shunt_resistor in DT is in µΩ; current_lsb auto-computed */
    u64 cal = data->config->calibration_value * 1000000;
    do_div(cal, data->shunt_uohms);
    /* cal now has dimension that matches what's required */

    err = regmap_write(data->regmap, INA2XX_CALIBRATION, cal);
    return 0;
}

static ssize_t ina2xx_show(struct device *dev, struct device_attribute *attr, char *buf)
{
    struct ina2xx_data *data = dev_get_drvdata(dev);
    struct sensor_device_attribute *sda = to_sensor_dev_attr(attr);
    int reg = sda->index;
    unsigned int raw;
    int val;

    regmap_read(data->regmap, reg, &raw);
    val = ina2xx_get_value(data, reg, raw);    /* scale by per-register factor */
    return sprintf(buf, "%d\n", val);
}

/* Attribute table */
static SENSOR_DEVICE_ATTR_RO(in0_input,   ina2xx, INA2XX_SHUNT_VOLTAGE);
static SENSOR_DEVICE_ATTR_RO(in1_input,   ina2xx, INA2XX_BUS_VOLTAGE);
static SENSOR_DEVICE_ATTR_RO(curr1_input, ina2xx, INA2XX_CURRENT);
static SENSOR_DEVICE_ATTR_RO(power1_input, ina2xx, INA2XX_POWER);
```

The hwmon framework's standard attribute names: `in*_input` = voltage in millivolts, `curr*_input` = current in milliamps, `power*_input` = power in microwatts, `temp*_input` = temperature in milli-degrees. User-space tools (`lm-sensors`, `sensors`, Grafana exporters) all consume this conventional naming.

## 75.5  Writing an INA219 driver from scratch

We'll write a from-scratch driver that follows the hwmon convention (not IIO this time — hwmon is the canonical home for power monitoring). ~250 lines.

`myina219.c`:

```c
#include <linux/init.h>
#include <linux/module.h>
#include <linux/i2c.h>
#include <linux/hwmon.h>
#include <linux/hwmon-sysfs.h>
#include <linux/of.h>

#define REG_CONFIG       0x00
#define REG_SHUNT_V      0x01
#define REG_BUS_V        0x02
#define REG_POWER        0x03
#define REG_CURRENT      0x04
#define REG_CALIBRATION  0x05

#define CFG_DEFAULT      0x399F     /* 32V range, ±320mV, 12-bit, continuous */

struct myina {
    struct i2c_client *client;
    struct mutex lock;
    u32 shunt_uohms;       /* shunt resistor in micro-ohms (from DT) */
    s32 current_lsb_uA;    /* µA per LSB */
};

/* === Low-level: 16-bit big-endian I²C registers === */

static int mi_read16(struct myina *m, u8 reg, s16 *out)
{
    int err;
    err = i2c_smbus_read_word_swapped(m->client, reg);
    if (err < 0) return err;
    *out = (s16)err;
    return 0;
}

static int mi_write16(struct myina *m, u8 reg, u16 val)
{
    return i2c_smbus_write_word_swapped(m->client, reg, val);
}

/* === Bring-up: program config + calibration === */

static int mi_init(struct myina *m)
{
    int err;
    u32 cal;

    /* Config register: 32 V range, gain /8 (±320 mV), 12-bit, continuous */
    err = mi_write16(m, REG_CONFIG, CFG_DEFAULT);
    if (err) return err;

    /* Auto-compute calibration:
       Cal = 0.04096 / (Current_LSB × R_shunt)
       Pick Current_LSB so the chip's 16-bit register covers our expected max:
       For 2 A max: Current_LSB = 2 A / 32767 ≈ 61 µA, round up to 100 µA
       Then Cal = 0.04096 / (100e-6 × shunt_ohms)
                = 0.04096 / (current_lsb_uA × 1e-6 × shunt_uohms × 1e-6)
                = 0.04096 / (current_lsb_uA × shunt_uohms × 1e-12)
                = 0.04096 × 1e12 / (current_lsb_uA × shunt_uohms)
                = 40960000 / (current_lsb_uA × shunt_uohms)  (need integer)

       More carefully: Cal = trunc(40960000 × 1000 / (current_lsb_uA × shunt_uohms))
       ... after working through units cleanly with the mainline algorithm. */
    m->current_lsb_uA = 100;     /* 100 µA per LSB — works for shunts up to a few hundred mΩ */
    cal = 40960000u / (m->current_lsb_uA * (m->shunt_uohms / 1000));
    /* Simpler: with shunt = 25 mΩ = 25000 µΩ, current_lsb = 100 µA:
       Cal = 40960000 / (100 × 25) = 16384 ✓ */

    if (cal > 0xFFFF) cal = 0xFFFF;
    err = mi_write16(m, REG_CALIBRATION, cal);
    if (err) return err;

    dev_info(&m->client->dev,
             "INA219 config: shunt=%u µΩ, current_lsb=%d µA, cal=%u\n",
             m->shunt_uohms, m->current_lsb_uA, cal);
    return 0;
}

/* === Read functions returning values in hwmon units === */

static int mi_read_shunt_uV(struct myina *m, s32 *uV)
{
    s16 raw;
    int err = mi_read16(m, REG_SHUNT_V, &raw);
    if (err) return err;
    /* INA219 raw LSB = 10 µV */
    *uV = (s32)raw * 10;
    return 0;
}

static int mi_read_bus_mV(struct myina *m, s32 *mV)
{
    s16 raw;
    int err = mi_read16(m, REG_BUS_V, &raw);
    if (err) return err;
    /* bits 15:3 = bus voltage in 4 mV units */
    *mV = (raw >> 3) * 4;
    return 0;
}

static int mi_read_current_mA(struct myina *m, s32 *mA)
{
    s16 raw;
    int err = mi_read16(m, REG_CURRENT, &raw);
    if (err) return err;
    /* current_uA = raw × current_lsb_uA */
    *mA = ((s32)raw * m->current_lsb_uA) / 1000;
    return 0;
}

static int mi_read_power_uW(struct myina *m, s32 *uW)
{
    s16 raw;
    int err = mi_read16(m, REG_POWER, &raw);
    if (err) return err;
    /* Power LSB = 20 × current_LSB */
    *uW = (s32)raw * m->current_lsb_uA * 20;
    return 0;
}

/* === hwmon-style sysfs attributes === */

static ssize_t in0_input_show(struct device *dev, struct device_attribute *a, char *buf)
{
    struct myina *m = dev_get_drvdata(dev);
    s32 uV;
    int err;
    mutex_lock(&m->lock);
    err = mi_read_shunt_uV(m, &uV);
    mutex_unlock(&m->lock);
    if (err) return err;
    /* hwmon convention: in*_input is in mV; shunt voltage is small, report in mV */
    return sprintf(buf, "%d\n", uV / 1000);
}

static ssize_t in1_input_show(struct device *dev, struct device_attribute *a, char *buf)
{
    struct myina *m = dev_get_drvdata(dev);
    s32 mV;
    int err;
    mutex_lock(&m->lock);
    err = mi_read_bus_mV(m, &mV);
    mutex_unlock(&m->lock);
    if (err) return err;
    return sprintf(buf, "%d\n", mV);
}

static ssize_t curr1_input_show(struct device *dev, struct device_attribute *a, char *buf)
{
    struct myina *m = dev_get_drvdata(dev);
    s32 mA;
    int err;
    mutex_lock(&m->lock);
    err = mi_read_current_mA(m, &mA);
    mutex_unlock(&m->lock);
    if (err) return err;
    return sprintf(buf, "%d\n", mA);
}

static ssize_t power1_input_show(struct device *dev, struct device_attribute *a, char *buf)
{
    struct myina *m = dev_get_drvdata(dev);
    s32 uW;
    int err;
    mutex_lock(&m->lock);
    err = mi_read_power_uW(m, &uW);
    mutex_unlock(&m->lock);
    if (err) return err;
    return sprintf(buf, "%d\n", uW);
}

static DEVICE_ATTR_RO(in0_input);
static DEVICE_ATTR_RO(in1_input);
static DEVICE_ATTR_RO(curr1_input);
static DEVICE_ATTR_RO(power1_input);

static struct attribute *mi_attrs[] = {
    &dev_attr_in0_input.attr,
    &dev_attr_in1_input.attr,
    &dev_attr_curr1_input.attr,
    &dev_attr_power1_input.attr,
    NULL,
};
ATTRIBUTE_GROUPS(mi);

/* === Probe / Remove === */

static int mi_probe(struct i2c_client *client)
{
    struct myina *m;
    struct device *hwmon_dev;
    u32 shunt_uohms = 25000;     /* default 25 mΩ if DT doesn't say */
    int err;

    m = devm_kzalloc(&client->dev, sizeof(*m), GFP_KERNEL);
    if (!m) return -ENOMEM;
    m->client = client;
    mutex_init(&m->lock);

    of_property_read_u32(client->dev.of_node, "shunt-resistor-micro-ohms",
                         &shunt_uohms);
    m->shunt_uohms = shunt_uohms;

    err = mi_init(m);
    if (err) return err;

    hwmon_dev = devm_hwmon_device_register_with_groups(&client->dev,
                                                       "myina219", m, mi_groups);
    return PTR_ERR_OR_ZERO(hwmon_dev);
}

static const struct of_device_id mi_of_match[] = {
    { .compatible = "linuxlearn,myina219" },
    { }
};
MODULE_DEVICE_TABLE(of, mi_of_match);

static const struct i2c_device_id mi_id[] = { { "myina219", 0 }, { } };
MODULE_DEVICE_TABLE(i2c, mi_id);

static struct i2c_driver mi_driver = {
    .driver = {
        .name = "myina219",
        .of_match_table = mi_of_match,
    },
    .probe = mi_probe,
    .id_table = mi_id,
};
module_i2c_driver(mi_driver);

MODULE_LICENSE("GPL");
```

DT:

```dts
&i2c1 {
    ina219@40 {
        compatible = "linuxlearn,myina219";
        reg = <0x40>;
        shunt-resistor-micro-ohms = <25000>;    /* 25 mΩ */
    };
};
```

Test:

```
[root@pa-mini:~]# insmod myina219.ko
[root@pa-mini:~]# ls /sys/class/hwmon/hwmon0/
curr1_input  in0_input  in1_input  name  power1_input

[root@pa-mini:~]# cat /sys/class/hwmon/hwmon0/in1_input
5023          ← bus voltage = 5.023 V

[root@pa-mini:~]# cat /sys/class/hwmon/hwmon0/curr1_input
124           ← current = 124 mA

[root@pa-mini:~]# cat /sys/class/hwmon/hwmon0/power1_input
622000        ← power = 622 mW = 0.622 W

[root@pa-mini:~]# sensors
myina219-i2c-1-40
Adapter: i.MX6UL I2C adapter
in0:           1.24 mV    (shunt voltage)
in1:           5.02 V     (bus voltage)
curr1:       124.00 mA
power1:        0.62 W
```

`sensors` (from lm-sensors package) auto-discovers and prints all hwmon devices. Production telemetry scrapes `/sys/class/hwmon/` directly.

## 75.6  hwmon vs IIO — when to use which

Both expose sensor readings via sysfs. Conventions and audience differ:

| | hwmon | IIO |
|---|---|---|
| Primary use | System health monitoring | General-purpose sensing |
| Typical readers | `sensors`, fan-control daemons, Grafana | Custom user-space apps, scientific apps |
| Units | Fixed (mV, mA, mW, mC) | Raw + scale; user multiplies |
| Buffered capture | no | yes (triggers + buffers) |
| Multi-axis sensors | awkward (would need many channels) | first-class (X/Y/Z modifiers) |
| Naming | `in*_input`, `curr*_input` | `in_<type>_<modifier>_raw` |

**Current monitors → hwmon**. IMUs, ADCs, environmental sensors → IIO. Some chips have both drivers (legacy + modern). Don't enable both.

## 75.7  INA226 — improved sibling

INA226's interface is nearly identical to INA219; the registers are mostly the same. Improvements:

- **16-bit shunt-voltage ADC** with 2.5 µV LSB (vs INA219's 10 µV).
- **Programmable averaging**: 1, 4, 16, 64, 128, 256, 512, 1024 samples averaged per result.
- **Alert pin** + alert configuration: assert ALERT on overcurrent, undervoltage, etc.
- **Mask/enable register** to select which alert sources fire.

Driver-wise: same `ina2xx.c`, just with `compatible = "ti,ina226"` and different per-register multipliers. From-scratch, you'd copy the INA219 driver and update the constants.

## 75.8  INA3221 — 3-channel

INA3221 is **three independent measurement channels** in one chip, with three pairs of shunt-voltage / bus-voltage registers (channels 1, 2, 3). Plus three alert pins.

Mainline driver: `drivers/hwmon/ina3221.c`. The DT specifies channels via subnodes:

```dts
&i2c1 {
    ina3221@40 {
        compatible = "ti,ina3221";
        reg = <0x40>;
        #address-cells = <1>;
        #size-cells = <0>;

        input@0 {
            reg = <0>;
            label = "VBUS_5V";
            shunt-resistor-micro-ohms = <10000>;
        };
        input@1 {
            reg = <1>;
            label = "VBUS_3V3";
            shunt-resistor-micro-ohms = <50000>;
        };
        input@2 {
            reg = <2>;
            label = "VBUS_1V8";
            shunt-resistor-micro-ohms = <100000>;
        };
    };
};
```

Result: `/sys/class/hwmon/hwmon0/in*_label`, `in*_input`, `curr*_input` × 3 channels. Production-grade 3-rail monitoring on one chip with one I²C address.

## 75.9  Lab

1. **Build a test rig.** Wire INA219 high-side on a 5 V rail going to your i.MX6ULL through a known current — say a 47 Ω resistor to GND (≈ 100 mA load).
2. **i2cdetect.** Verify 0x40. With A0/A1 pin strapping you can put up to 16 INA219s on one bus.
3. **Build and load `myina219.ko`.** Verify `in1_input` ≈ 5000 (5 V), `curr1_input` ≈ 106 mA.
4. **Vary the load.** Swap the resistor; verify current scales linearly.
5. **Sanity-check shunt voltage.** `in0_input` should equal `R_shunt × I = 0.025 × 0.106 = 2.65 mV`. The 16-bit shunt-voltage register holds raw value 265 (since 265 × 10 µV = 2650 µV = 2.65 mV).
6. **Forget the calibration.** Modify `mi_init` to skip the `mi_write16(... REG_CALIBRATION ...)` line. Reload. Verify Current/Power read zero, while Shunt and Bus still work. This is the classic gotcha.
7. **Switch to the mainline driver.** Use `compatible = "ti,ina219"`, set `shunt-resistor`, reboot. Confirm same values.
8. **`sensors` output.** Install lm-sensors; run `sensors`; verify your INA appears with all channels.

## 75.10  Pitfalls

- **Calibration register left at zero.** Current and Power read zero forever. The #1 INA gotcha; you'll lose an hour to it.
- **Shunt placement on low-side.** INA219 is *high-side* (V+ and V− both near VBUS). Low-side measurement is also possible (V+ at shunt-load side, V− at GND) but limits range to bus voltages near GND. For motor PWM where you want to keep GND clean, high-side is mandatory.
- **Shunt too small.** 1 mΩ shunt + 100 mA load = 100 µV shunt voltage = 10 LSB on INA219 = 5–10 LSB of noise. Get a bigger shunt or use INA226.
- **Shunt too big.** 1 Ω shunt + 1 A load = 1 W dissipated in the resistor. Resistor heats, drift, power waste.
- **Bus voltage > 26 V.** INA219's max bus voltage. Higher = damage. INA226 goes to 36 V; even higher needs different chips (INA138, INA260).
- **Common-mode voltage limit.** Both INA pins must be within the chip's input range. For a high-side shunt on a 24 V rail, V+ and V− are both around 24 V — INA219 spec'd to 26 V, fine. On a 36 V rail, use INA226.
- **PWM-controlled load measurement.** Switching loads at kHz rates produce ripple that the INA's slow ADC averages — you get the mean current, not peak. For peak measurement, use a faster current-sense amplifier + scope.
- **DC blocking on dynamic loads.** If your "current monitor" is reading near zero and you're sure load is drawing power, check if there's a series capacitor isolating DC — capacitor blocks DC current entirely; the shunt-amplifier reads zero.
- **Mismatched A0/A1 strapping in DT vs hardware.** DT says `reg = <0x40>` but board pinned to 0x44. Silent failure.

## 75.11  Going deeper

- **`drivers/hwmon/ina2xx.c`** — production driver covering the INA family.
- **`drivers/hwmon/ina3221.c`** — multi-channel.
- **INA219 datasheet (TI SBOS448G)** — calibration formula appendix; current_LSB choice guide.
- **INA226 datasheet (TI SBOS547A)** — averaging mode tradeoffs; alert configuration.
- **`Documentation/hwmon/`** — hwmon framework documentation; ABI; convention.
- **`Documentation/hwmon/sysfs-interface.rst`** — the canonical attribute naming reference.
- **`sensors-detect` / `sensors`** — lm-sensors user-space tooling.

> Next chapter: **Chapter 76 — Battery fuel gauge + charger.** Linux's `power_supply_class` framework, MAX17048 ModelGauge for SoC estimation, TP4056 single-cell charger, BQ24074 path-managed charger.
