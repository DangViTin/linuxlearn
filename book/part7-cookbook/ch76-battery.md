---
chapter: 76
title: Battery fuel gauge + charger (MAX17048 / TP4056 / BQ24074)
part: VII — Device cookbook
estimated_pages: 22
status: draft
---

# Chapter 76 — Battery fuel gauge + charger

> **What:** the three pieces of a battery-powered embedded product: a **fuel gauge** that tracks state-of-charge (Maxim MAX17048 — I²C, "ModelGauge" algorithm), a **charger** that manages the CC/CV cycle (TI TP4056 — analog, simple; or TI BQ24074 — I²C-configurable, path-managed), and the **`power_supply_class`** framework that ties them into Linux. For each: physics, protocol, mainline driver, plus a from-scratch MAX17048 driver implementing the `power_supply` provider model.
> **Why:** any battery-powered product needs to report "percent full" to the user *honestly*. The naive approach — voltage divider into ADC, lookup table — is wrong: Li-ion voltage doesn't track SoC linearly, and load voltage drops badly bias the reading. A fuel gauge chip does the right thing: integrates current (coulomb counting) or models the cell (impedance tracking) to get sub-2 % SoC accuracy. Plus a charger that knows when to terminate.
> **Focus:** **`power_supply_class` is how kernel and user-space cooperate on battery state**. Drivers register as `power_supply` providers; user-space (UPower, systemd-battery-monitor, your custom app) reads from `/sys/class/power_supply/`. Same shape for laptop batteries, e-bike packs, phones, embedded devices.

## 76.1  Chip comparison

| | Maxim MAX17048 | TI TP4056 | TI BQ24074 |
|---|---|---|---|
| Function | 1-cell fuel gauge | 1-cell Li-ion charger | 1-cell path-managed charger |
| Interface | I²C (0x36) | none (analog control) | I²C (0x6B) |
| Algorithm | ModelGauge (impedance) | linear CC/CV | linear CC/CV, dynamic-power-path mgmt |
| Charge current setting | n/a | resistor (≤ 1 A) | resistor (≤ 1.5 A) |
| Charge termination | n/a | C/10 | C/10 + safety timer |
| Power-path | n/a | no — battery powers load while charging | yes — input powers load directly, battery only when input absent |
| Idle current | 23 µA | none | 100 µA |
| Volume price | $2.50–4.00 | $0.30–0.80 | $2–4 |
| Mainline driver | `power/supply/max17040_battery.c` | none (no I²C; status detected via GPIO) | `power/supply/bq2415x_charger.c` |

**Pick guide:**
- **MAX17048**: lowest-cost real fuel gauge. Use unless you need coulomb-counting precision.
- **TP4056**: cheap charger; fine for "low-power device that mostly runs from battery." No power-path = device loses power when battery dies, even with USB plugged.
- **BQ24074**: production-quality charger with power-path. Device stays on with input even when battery is removed; charger negotiates input current. The right choice for a real product.

A complete battery system typically combines a charger + a gauge: TP4056 + MAX17048 is the cheap stack; BQ24074 + MAX17048 is the production stack.

## 76.2  The physics — why a fuel gauge is needed

A naïve "voltage → %" approach fails for two reasons:

1. **Voltage isn't linear with SoC.** A Li-ion cell goes 4.2 V (100 %) → 3.7 V (50 %) → 3.4 V (10 %) → 3.0 V (cutoff). The middle plateau is flat — a small voltage range covers most of the capacity.
2. **Voltage drops under load.** The cell's internal resistance (50–500 mΩ depending on age and chemistry) causes voltage to drop by `I × R_internal`. A 500 mA load on a 100 mΩ cell drops the measured voltage by 50 mV — equivalent to ~5 % SoC on the plateau. Read at the wrong moment, you tell the user 60 % when actual is 65 %.

Two real-world approaches:

- **Coulomb counting** (TI BQ27xxx, MAX17042). Measure current with a shunt; integrate over time; subtract from a known-full capacity. Pros: accurate. Cons: needs full charge cycle to calibrate; drift over time as full capacity changes with age.
- **Impedance tracking / ModelGauge** (MAX17048). Build an internal model of the cell's V/I/T/SoC relationship; use measured V and I (in MAX17048's case, just V — it estimates I from V swings) to look up SoC. Pros: no shunt needed; no full-charge required to calibrate. Cons: needs a per-chemistry pre-loaded model.

MAX17048's claim to fame: 23 µA standby, no shunt, factory-loaded "typical Li-ion" model, "good enough for most products" SoC.

## 76.3  Protocol — MAX17048

Register map (every register is 16 bits, big-endian):

| Reg | Name | Purpose |
|-----|------|---------|
| 0x02 | VCELL | Cell voltage, 78.125 µV/LSB |
| 0x04 | SOC | State of charge, bits 15:8 = %, bits 7:0 = fractional 256ths |
| 0x06 | MODE | Quick-start trigger |
| 0x08 | VERSION | IC version (0x0011 for MAX17048) |
| 0x0A | HIBRT | Hibernate threshold |
| 0x0C | CONFIG | Rcomp + alert threshold |
| 0x14 | VALRT | Voltage alert min/max |
| 0x16 | CRATE | C-rate estimate (current as fraction of capacity) |
| 0x18 | VRESET / ID | Soft-reset trigger; chip ID |
| 0x1A | STATUS | Alert flags |

### A reading

```
   Host: START | 0x6C | 0x02 | START | 0x6D | (2 bytes MSB,LSB) | STOP
   (0x36 << 1 = 0x6C for write; ... | 1 = 0x6D for read)
```

`raw = (buf[0] << 8) | buf[1]; vcell_uV = raw × 78.125;` — voltage in microvolts. Divide by 1000 for mV.

For SoC: `soc_pct = buf[0]; soc_frac = buf[1];` so a reading of `0x52 0xC0` is 82 + 192/256 = 82.75 %.

### Bring-up

Practically no init needed for default operation:

1. Read VERSION (0x08); verify chip is alive.
2. (Optional) write MODE = 0x4000 to issue "quick-start" — forces a fresh SoC estimate, useful after a brand-new pack is connected.
3. Start reading VCELL and SOC.

The "ModelGauge" runs continuously inside the chip on its own 30-second cycle. You just read the output.

## 76.4  power_supply_class — how Linux models batteries

`power_supply_class` (in `drivers/power/supply/power_supply_core.c`) is the framework that ties together battery / charger / AC-adapter into one consistent user-space view.

A driver registers as one or more **power_supply** objects, each with a type (BATTERY, MAINS, USB, etc.) and a set of *properties* it can report:

```c
enum power_supply_property {
    POWER_SUPPLY_PROP_STATUS,             /* CHARGING / DISCHARGING / FULL / NOT_CHARGING */
    POWER_SUPPLY_PROP_HEALTH,              /* GOOD / OVERHEAT / DEAD / OVERVOLTAGE / etc. */
    POWER_SUPPLY_PROP_PRESENT,             /* battery present (0/1) */
    POWER_SUPPLY_PROP_VOLTAGE_NOW,         /* µV */
    POWER_SUPPLY_PROP_CURRENT_NOW,         /* µA */
    POWER_SUPPLY_PROP_CHARGE_NOW,          /* µAh — coulomb counters */
    POWER_SUPPLY_PROP_CHARGE_FULL,         /* µAh capacity */
    POWER_SUPPLY_PROP_CAPACITY,            /* % (0..100) */
    POWER_SUPPLY_PROP_CAPACITY_LEVEL,      /* CRITICAL/LOW/NORMAL/HIGH/FULL */
    POWER_SUPPLY_PROP_TEMP,                /* deci-degrees C */
    POWER_SUPPLY_PROP_TIME_TO_EMPTY_NOW,   /* seconds */
    POWER_SUPPLY_PROP_TIME_TO_FULL_NOW,
    /* ... 40+ more */
};
```

The driver provides a single `get_property` callback that the framework calls with each property the user-space requests. User-space sees `/sys/class/power_supply/<name>/`:

```
[root@pa-mini:~]# ls /sys/class/power_supply/
battery   ac

[root@pa-mini:~]# cat /sys/class/power_supply/battery/capacity
82
[root@pa-mini:~]# cat /sys/class/power_supply/battery/voltage_now
3852000
[root@pa-mini:~]# cat /sys/class/power_supply/battery/status
Discharging
```

Standardised. Phones, laptops, IoT — all use this.

## 76.5  Writing a MAX17048 power_supply driver from scratch

Goal: register the chip as a `POWER_SUPPLY_BATTERY` and report at least capacity + voltage + status. ~200 lines.

`mymax17048.c`:

```c
#include <linux/init.h>
#include <linux/module.h>
#include <linux/i2c.h>
#include <linux/power_supply.h>

#define REG_VCELL    0x02
#define REG_SOC      0x04
#define REG_VERSION  0x08

struct mymax {
    struct i2c_client *client;
    struct power_supply *psy;
    struct mutex lock;
};

/* === Low-level I²C: 16-bit big-endian register reads === */

static int mm_read_reg(struct mymax *m, u8 reg, u16 *val)
{
    int err = i2c_smbus_read_word_swapped(m->client, reg);
    if (err < 0) return err;
    *val = err;
    return 0;
}

static int mm_read_voltage_uV(struct mymax *m, int *uV)
{
    u16 raw;
    int err = mm_read_reg(m, REG_VCELL, &raw);
    if (err) return err;
    /* MAX17048: 78.125 µV/LSB.
     * voltage_uV = raw × 78.125 = (raw × 78125) / 1000 */
    *uV = ((u32)raw * 78125) / 1000;
    return 0;
}

static int mm_read_soc_permille(struct mymax *m, int *permille)
{
    u16 raw;
    int err = mm_read_reg(m, REG_SOC, &raw);
    if (err) return err;
    /* High byte = percent; low byte = fractional 256ths.
     * Return as permille (parts per thousand) — power_supply_class uses integer % usually,
     * but we'll return tenths and let CAPACITY round. */
    int pct = (raw >> 8) & 0xFF;
    int frac256 = raw & 0xFF;
    /* permille = pct × 10 + frac256 × 10 / 256  */
    *permille = pct * 10 + frac256 * 10 / 256;
    return 0;
}

/* === power_supply_class callback === */

static enum power_supply_property mm_props[] = {
    POWER_SUPPLY_PROP_PRESENT,
    POWER_SUPPLY_PROP_VOLTAGE_NOW,
    POWER_SUPPLY_PROP_CAPACITY,
    POWER_SUPPLY_PROP_STATUS,
};

static int mm_get_property(struct power_supply *psy,
                           enum power_supply_property prop,
                           union power_supply_propval *val)
{
    struct mymax *m = power_supply_get_drvdata(psy);
    int err = 0;
    int v;

    mutex_lock(&m->lock);
    switch (prop) {
    case POWER_SUPPLY_PROP_PRESENT:
        val->intval = 1;       /* if we're talking to it, it's present */
        break;
    case POWER_SUPPLY_PROP_VOLTAGE_NOW:
        err = mm_read_voltage_uV(m, &v);
        if (!err) val->intval = v;
        break;
    case POWER_SUPPLY_PROP_CAPACITY:
        err = mm_read_soc_permille(m, &v);
        if (!err) val->intval = v / 10;     /* round to % */
        if (val->intval > 100) val->intval = 100;
        break;
    case POWER_SUPPLY_PROP_STATUS:
        /* MAX17048 doesn't know charge direction directly — would need to
         * monitor SoC trend or read CRATE.  Stub: report UNKNOWN. */
        val->intval = POWER_SUPPLY_STATUS_UNKNOWN;
        break;
    default:
        err = -EINVAL;
    }
    mutex_unlock(&m->lock);
    return err;
}

static const struct power_supply_desc mm_desc = {
    .name           = "battery",
    .type           = POWER_SUPPLY_TYPE_BATTERY,
    .properties     = mm_props,
    .num_properties = ARRAY_SIZE(mm_props),
    .get_property   = mm_get_property,
};

/* === Probe / Remove === */

static int mm_probe(struct i2c_client *client)
{
    struct mymax *m;
    struct power_supply_config psy_cfg = {};
    u16 version;
    int err;

    m = devm_kzalloc(&client->dev, sizeof(*m), GFP_KERNEL);
    if (!m) return -ENOMEM;
    m->client = client;
    mutex_init(&m->lock);

    err = mm_read_reg(m, REG_VERSION, &version);
    if (err) return dev_err_probe(&client->dev, err, "version read failed\n");
    if ((version & 0xFFF0) != 0x0010)
        return dev_err_probe(&client->dev, -ENODEV,
                             "unexpected version 0x%04x\n", version);
    dev_info(&client->dev, "MAX17048 ready, version 0x%04x\n", version);

    psy_cfg.drv_data = m;
    psy_cfg.of_node  = client->dev.of_node;

    m->psy = devm_power_supply_register(&client->dev, &mm_desc, &psy_cfg);
    if (IS_ERR(m->psy))
        return dev_err_probe(&client->dev, PTR_ERR(m->psy),
                             "power_supply register failed\n");

    i2c_set_clientdata(client, m);
    return 0;
}

static const struct of_device_id mm_of_match[] = {
    { .compatible = "linuxlearn,mymax17048" },
    { }
};
MODULE_DEVICE_TABLE(of, mm_of_match);

static const struct i2c_device_id mm_id[] = { { "mymax17048", 0 }, { } };
MODULE_DEVICE_TABLE(i2c, mm_id);

static struct i2c_driver mm_driver = {
    .driver = {
        .name = "mymax17048",
        .of_match_table = mm_of_match,
    },
    .probe    = mm_probe,
    .id_table = mm_id,
};
module_i2c_driver(mm_driver);

MODULE_LICENSE("GPL");
```

DT:

```dts
&i2c1 {
    fuelgauge@36 {
        compatible = "linuxlearn,mymax17048";
        reg = <0x36>;
    };
};
```

Test:

```
[root@pa-mini:~]# insmod mymax17048.ko
[root@pa-mini:~]# ls /sys/class/power_supply/
battery
[root@pa-mini:~]# cat /sys/class/power_supply/battery/capacity
82
[root@pa-mini:~]# cat /sys/class/power_supply/battery/voltage_now
3852023
[root@pa-mini:~]# cat /sys/class/power_supply/battery/present
1
[root@pa-mini:~]# upower -i /org/freedesktop/UPower/devices/battery_battery
  native-path:          battery
  power supply:         yes
  state:                unknown
  energy-percentage:    82%
  voltage:              3.85 V
```

`upower` (the desktop daemon) auto-discovers the battery and presents it as a standard battery device. Same applies to systemd's logind, fwupd, and many other userspace consumers.

To improve: implement STATUS by reading CRATE (register 0x16) — a positive C-rate means charging, negative means discharging. Add it as a third property type the driver supports.

## 76.6  TP4056 — the analog charger

TP4056 is a simple linear Li-ion charger:

```
    USB 5V ──► VIN  ┌─────────┐  BAT ──► Li-ion cell
                    │         │
                    │ TP4056  │  CHRG (active-low LED indicator)
                    │         │  STDBY (active-low LED indicator)
                    │         │  PROG (resistor to GND sets charge current)
                    └─────────┘
```

Charge current is set by `R_PROG`:

```
I_charge = 1200 / R_prog   amps
```

R = 1.2 kΩ → 1 A; R = 2.4 kΩ → 500 mA, etc.

The chip does:
1. **Trickle charge** (8 % of programmed current) until cell > 2.9 V.
2. **Constant current** at programmed current up to 4.2 V.
3. **Constant voltage** at 4.2 V; current tapers.
4. **Termination** when current drops to 10 % of programmed.

No I²C, no control. CHRG and STDBY pins drive LEDs (or GPIOs into the SoC for status detection).

To integrate with Linux: wire CHRG to a GPIO; in DT, declare a `power_supply` of type AC with this GPIO. The mainline framework `gpio-charger.c` does this generic pattern:

```dts
charger {
    compatible = "gpio-charger";
    charger-type = "mains";
    gpios = <&gpio4 5 GPIO_ACTIVE_LOW>;     /* CHRG LED line */
    charge-status-gpios = <&gpio4 6 GPIO_ACTIVE_LOW>;
};
```

`/sys/class/power_supply/main_charger/online` reads 1 when charging.

**TP4056 limitations**: No power-path. When battery is empty *and* USB is plugged in, the chip charges the battery but does not separately power the load. Voltage on BAT depends on cell state. For a Linux SoC needing 4.2 V min at 500+ mA, this can cause boot loops on a deeply-discharged battery.

## 76.7  BQ24074 — production-quality

BQ24074 adds:
- **Power-path**: input feeds VOUT directly when present; battery feeds VOUT only when input absent. Device stays on regardless of battery state, as long as input is present.
- **Dynamic Power-Path Management (DPPM)**: monitors input voltage. If input collapses below the threshold (overloaded USB port), the chip reduces charge current to keep the load alive.
- **Configurable via I²C**: programmed charge current, termination voltage, safety timer.

Use BQ24074 for: any product where the user expects the device to power up immediately when plugged in (and the battery isn't presumed alive).

Mainline driver: `drivers/power/supply/bq24190_charger.c` covers the BQ241xx family. DT:

```dts
&i2c1 {
    charger@6b {
        compatible = "ti,bq24074";
        reg = <0x6b>;
        ti,charge-current = <500000>;       /* 500 mA */
        ti,input-current-limit = <1000000>;  /* 1 A USB-3 capable port */
        interrupt-parent = <&gpio4>;
        interrupts = <12 IRQ_TYPE_EDGE_FALLING>;
    };
};
```

`/sys/class/power_supply/bq24074-charger/`:

```
input_current_limit
charge_current_limit
status                    ← Charging / Not Charging / Full
online                    ← input present
voltage_now
```

A user-space battery daemon (UPower, your own) combines this with the MAX17048's capacity to give a complete view.

## 76.8  Integrating: charger + gauge → battery status

To synthesise a full picture, your application reads:

```python
charger_online = read("/sys/class/power_supply/charger/online")
charger_status = read("/sys/class/power_supply/charger/status")
battery_capacity = read("/sys/class/power_supply/battery/capacity")
battery_voltage  = read("/sys/class/power_supply/battery/voltage_now")

if charger_online:
    if battery_capacity == 100:
        print("Plugged in, fully charged")
    else:
        print(f"Charging: {battery_capacity}%")
else:
    if battery_capacity < 10:
        print(f"Low battery: {battery_capacity}%, shut down soon")
    else:
        print(f"On battery: {battery_capacity}%")
```

In product UI, do *time-averaged* SoC display — instantaneous readings can wobble ±1 % under varying load. EMA with τ = 30 s smooths the indicator.

## 76.9  Lab

1. **Wire a MAX17048** to your i.MX6ULL I²C bus, with a Li-ion cell on its VCELL input.
2. **i2cdetect.** Verify 0x36 appears.
3. **Build and load `mymax17048.ko`.** Read capacity and voltage. Disconnect / reconnect the cell; capacity should jump after a 30-second model-recompute period.
4. **Cell discharge test.** Connect a load (resistor); log capacity + voltage every 10 s for an hour. Plot. You should see voltage drop and capacity decline together, but not in a strictly linear relationship.
5. **upower integration.** Install UPower; verify `upower -i /org/freedesktop/UPower/devices/battery_battery` reports your readings.
6. **TP4056 charging.** Wire a TP4056 to charge the cell from USB. Wire CHRG to a GPIO. Use `gpio-charger` in DT. Verify `online` reports correctly.
7. **Switch to mainline MAX17048 driver.** `compatible = "maxim,max17048";`. Verify same data; gain access to extra properties (alerts, capacity-level).
8. **Capacity-level logic.** Write a user-space daemon that reads capacity every 30 s; logs to syslog when crossing thresholds (low 20 %, critical 5 %); triggers `poweroff` at critical-3 %.

## 76.10  Pitfalls

- **Quick-start without justification.** Writing 0x4000 to MODE clears the chip's internal model and forces a fresh estimate. Useful on fresh-pack-insertion; harmful if done routinely (degrades SoC accuracy).
- **Reading SoC immediately after power-on.** Chip needs ~250 ms to initialise. The first read returns the cached value from last shutdown.
- **Trusting MAX17048 SoC on a cell-chemistry mismatch.** Factory-loaded model is "typical Li-ion 3.7 V nominal." LiFePO₄ (3.2 V nominal) reads wildly wrong. Use BQ27xxx with the right chemistry profile for non-standard cells.
- **TP4056 without thermal management.** At 1 A charge, the chip dissipates ~1 W. Without thermal vias and a ground plane, it overheats and reduces charge current — slower charging.
- **TP4056 in deep-discharge cells.** Cells below 2.5 V might fail TP4056's pre-charge. Use a chip with adjustable pre-charge current.
- **BQ24074 without I²C in the boot path.** If the chip needs config at boot to set higher input current, U-Boot must initialize it — otherwise it defaults to 100 mA input, which can't power the SoC.
- **Power-path absent on production-bound product.** User unplugs charger; device dies. They expected the battery to take over. Verify your topology before laying out.
- **Forgetting `present` property.** Some user-space code refuses to talk to a battery whose `present` is 0. Always report 1 if the chip is responding.
- **Capacity hysteresis.** Naïve daemons toggle "5% low warning" at 4.9 % then back at 5.0 %. Add hysteresis (warn at 5 %, clear at 8 %).

## 76.11  Going deeper

- **`drivers/power/supply/max17040_battery.c`** — production MAX17048/40/44 driver.
- **`drivers/power/supply/bq27xxx_battery.c`** — coulomb-counting gauges from TI.
- **`drivers/power/supply/gpio-charger.c`** — generic "charging status from GPIO" driver.
- **`drivers/power/supply/bq2415x_charger.c`** + `bq24190_charger.c` — TI charger family.
- **`Documentation/power/power_supply_class.rst`** — framework documentation.
- **`Documentation/ABI/testing/sysfs-class-power`** — full sysfs attribute list.
- **MAX17048 datasheet (Maxim)** — register map; quickstart guide.
- **TP4056 datasheet (NanJing Top Power)** — application circuit.
- **BQ24074 datasheet (TI SLUS818)** — power-path explained.
- **UPower source** at <https://gitlab.freedesktop.org/upower/upower> — how user-space consumes power_supply_class.

---

> **End of Group E — Power & current (Ch 75–76).** Together with Ch 51B (power management) you now have all three pieces of low-power product engineering: PM saves power, INA reports it, fuel gauge predicts remaining time.

> Next chapter: **Chapter 77 — 1-Wire sensors (DS18B20 / DHT22).** Maxim's odd "one wire + ground" protocol. Slow but charming; the kernel's w1 subsystem; why DHT22 is a worse fit for Linux than for an MCU.
