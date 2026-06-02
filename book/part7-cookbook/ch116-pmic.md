---
chapter: 116
title: PMICs and the regulator framework (PCA9450, PF8200, BD71850)
part: VII — Device cookbook
estimated_pages: 14
status: draft
---

# Chapter 116 — PMICs and regulator framework

> **What:** **Power Management ICs** — single-chip power solutions that replace the half-dozen discrete LDOs and buck converters around an SoC. We cover **NXP PCA9450** (the i.MX-recommended PMIC for i.MX8M; also used on some i.MX6 designs), **NXP PF8200** (industrial), **Rohm BD71850MWV** (compact, integrated for i.MX6/8 cores). On the i.MX6ULL we walk the I²C register map of a typical PMIC, configure voltage rails for SoC + DDR + I/O via the kernel **regulator framework**, integrate with **DVFS** (Ch 51B), and measure the power savings from PMIC-coordinated voltage scaling vs always-on discrete LDOs.
>
> **Why:** every i.MX6ULL design has 4–6 voltage rails: 3.3 V (I/O), 1.35 V (DDR3), 1.275 V (SoC core), 2.5 V (analog), 1.8 V (some I/O), 5 V (USB). Discrete LDOs work but: (a) bring-up sequencing is tricky (DDR before SoC core, etc.), (b) no central control for sleep, (c) BOM = 6+ chips. A PMIC consolidates these into 1 chip with I²C control, programmable voltages, ramp-rate control, sequencing, and per-rail enable for runtime power management. For products that ship in volume or need real sleep/wake, a PMIC isn't optional — it's the only practical path.
>
> **Focus:** The regulator framework treats every rail as a "supply". Drivers declare their consumer-supply relationship in the DT. The kernel computes the power-on order from the dependency graph, and waits for each rail to stabilise before letting consumers probe. The PMIC driver translates "set supply VDDARM to 1.275 V" into the right I²C writes. DVFS uses this: when cpufreq drops to 396 MHz, it calls `regulator_set_voltage(VDDARM, 1.150 V)` first, saving ~30 % of core power. If you get the boot-sequence wrong — for example the kernel starts the FEC before its PHY's 1.8 V rail is stable — you will see PHY probe failures that look random.

## 116.1  Discrete vs PMIC

| | Discrete LDOs/bucks | PMIC |
|---|---|---|
| Chip count | 5–10 | 1 |
| PCB area | ~600 mm² | ~200 mm² |
| BOM cost (qty 1k) | $4–6 | $3–5 |
| Sequencing | external supervisor IC | built-in, programmable |
| Per-rail enable | additional GPIOs | I²C |
| DVFS support | software-toggling LDO enable (slow, noisy) | I²C voltage change (fast, glitch-free) |
| Sleep modes | external GPIOs + LDOs | per-rail sleep states + global low-power mode |
| Fault detection | per-LDO PG pin | unified PMIC FAULT line |

PMICs are better in every dimension once a board has more than three rails or needs runtime power management. Discrete LDOs remain common only for the cheapest designs, or for battery rails where the PMIC's ~50 µA quiescent is too high.

## 116.2  Anatomy of a typical PMIC (PCA9450)

The PCA9450 (i.MX8M-recommended; technically over-specified for i.MX6ULL but illustrative):
- 4× Buck DC-DC (BUCK1: 1.0–1.65 V @ 3.5 A for VDDARM, BUCK2: same for SOC, BUCK3: 1.0–1.65 V @ 1.5 A, BUCK4: 0.6–2.1875 V)
- 1× Buck for DDR (BUCK5: 1.1 V / 1.35 V)
- 6× LDO (LDO1: 1.6/3.3 V @ 100 mA, LDO2: 1.5–3.3 V @ 250 mA, LDO3–5: similar)
- I²C control + interrupt
- Programmable power-up sequence
- Sleep state with selectable rails on/off
- Fault detection (over-current, over-temp, under-voltage)

I²C register map (~80 registers):

| Reg | Name | Purpose |
|---|---|---|
| 0x01 | DEV_ID | chip ID (0x10 for PCA9450A) |
| 0x14 | BUCK1OUT | output voltage code |
| 0x15 | BUCK1CTRL | enable, soft-start, ramp rate |
| 0x18 | BUCK2OUT | |
| 0x20 | BUCK5OUT | DDR voltage |
| 0x21 | BUCK5CTRL | |
| 0x30 | LDO1CTRL | |
| 0x40 | PWRON_DELAY | sequencing |
| 0x70 | INT_LATCH | interrupt status |

Voltage encoding: per-buck typically `Vout = 0.6 + N × 0.025 V` for codes 0..63, so 1.275 V = code 27. The driver's translation table maps mV ↔ code.

## 116.3  The Linux regulator framework

`drivers/regulator/` — central framework. Every rail is a `struct regulator_dev`. Consumers `regulator_get()` by supply name in DT, then `regulator_enable()` / `regulator_disable()` / `regulator_set_voltage()`.

```
   Hardware                  Driver                  Consumer
   ──────                    ──────                  ──────
   PCA9450 BUCK1 ────► pca9450-regulator.c ──► CPU clock driver (DVFS)
                                                "vddarm-supply = <&buck1>;"
   PCA9450 BUCK5 ────► pca9450-regulator.c ──► DDR3 driver
                                                "ddr-supply = <&buck5>;"
   PCA9450 LDO1  ────► pca9450-regulator.c ──► Ethernet PHY
                                                "vio-supply = <&ldo1>;"
```

DT:

```dts
&i2c1 {
    pca9450: pmic@25 {
        compatible = "nxp,pca9450a";
        reg = <0x25>;
        interrupt-parent = <&gpio4>;
        interrupts = <22 IRQ_TYPE_LEVEL_LOW>;

        regulators {
            buck1: BUCK1 {
                regulator-name = "VDD_ARM";
                regulator-min-microvolt = <600000>;
                regulator-max-microvolt = <1650000>;
                regulator-boot-on;
                regulator-always-on;
                regulator-ramp-delay = <3125>;
            };
            buck5: BUCK5 {
                regulator-name = "VDD_DRAM";
                regulator-min-microvolt = <1100000>;
                regulator-max-microvolt = <1350000>;
                regulator-boot-on;
                regulator-always-on;
            };
            ldo1: LDO1 {
                regulator-name = "VDD_SNVS";
                regulator-min-microvolt = <1600000>;
                regulator-max-microvolt = <3300000>;
                regulator-always-on;
            };
            /* ... etc ... */
        };
    };
};

&cpu0 {
    vddarm-supply = <&buck1>;
};

&fec1 {
    phy-supply = <&ldo1>;
};
```

After boot:

```sh
ls /sys/class/regulator/
# regulator.0  regulator.1  ...

cat /sys/class/regulator/regulator.0/name
# VDD_ARM

cat /sys/class/regulator/regulator.0/microvolts
# 1275000
```

Or `regulator_summary` (debugfs):

```sh
mount -t debugfs none /sys/kernel/debug
cat /sys/kernel/debug/regulator/regulator_summary
# regulator                       use open bypass voltage current     min     max
# regulator-dummy                    0   0      0     0mV     0mA     0mV     0mV
# VDD_SNVS                           2   2      0  3300mV     0mA  1600mV  3300mV
# VDD_ARM                            1   1      0  1275mV     0mA   600mV  1650mV
```

The regulator summary makes the power tree visible: you can see exactly which consumer keeps each rail enabled.

## 116.4  Power-up sequencing — the most subtle bring-up trap

i.MX6ULL has a required power-up sequence:
1. VDD_SNVS (always-on RTC domain) — must be first
2. VDD_HIGH_IN (analog supply) — within 10 ms of SNVS
3. VDD_ARM_IN, VDD_SOC_IN — together, within 100 ms
4. NVCC_DRAM (1.35 V for DDR3) — before any DDR access
5. Per-bank I/O supplies (NVCC_GPIO_*) — before any GPIO use
6. POR_B released (reset deassert) — last

If you violate this, behavior ranges from "doesn't boot" to "boots but crashes intermittently" to "silicon damage." The PMIC's programmable sequencer enforces this in hardware — set PWRON_DELAY registers per rail and the PMIC powers them in the right order at the right intervals.

At runtime, `regulator_enable()` walks the supply dependency graph and powers parent supplies first. Mark each rail with `regulator-boot-on` if the kernel inherits an already-on rail; mark with `regulator-always-on` if it must never disable.

## 116.5  DVFS — coordinated voltage and frequency scaling

When cpufreq drops the CPU clock (Ch 51B), it should also drop the core voltage. The `cpufreq-dt` driver does this via the regulator framework:

```dts
&cpu0 {
    cpu-supply = <&buck1>;
    operating-points-v2 = <&cpu_opp_table>;
};

cpu_opp_table: opp-table {
    compatible = "operating-points-v2";

    opp-396000000 {
        opp-hz = /bits/ 64 <396000000>;
        opp-microvolt = <1150000>;
        opp-supported-hw = <0xc>, <0x7>;
    };
    opp-528000000 {
        opp-hz = /bits/ 64 <528000000>;
        opp-microvolt = <1200000>;
    };
    opp-696000000 {
        opp-hz = /bits/ 64 <696000000>;
        opp-microvolt = <1275000>;
    };
};
```

The OPP table tells cpufreq: "at 396 MHz, 1.15 V is sufficient." On transition:

```
1. cpufreq decides to drop to 396 MHz
2. regulator_set_voltage(buck1, 1150000) - PMIC ramps down via I²C
3. After ramp + settling, write new clock divider
4. CPU now runs at 396 MHz / 1.15 V
```

Power saving from 1.275 V to 1.150 V:
- Static (leakage) power ∝ V; ~10 % reduction.
- Dynamic power ∝ V² × f; ~28 % reduction at same frequency, more if f drops too.

Combined with f drop from 696 → 396 MHz: ~60 % total power saving for "idle background" load. This is why DVFS exists.

## 116.6  Sleep state coordination

In suspend-to-RAM:
- Most rails disable.
- DDR rail stays on (self-refresh).
- VDD_SNVS always on (so RTC + wake circuits work).

The PMIC's `SLEEP` mode does this in one command from Linux suspend callback:

```c
/* Inside i.MX6ULL suspend driver */
if (pmic->sleep_mode) {
    /* PMIC enters its preconfigured sleep state */
    pca9450_set_state(pmic, PCA9450_STATE_SLEEP);
    /* Now SoC enters WFI; only SNVS and DDR are powered */
}
```

On wake: PMIC's wake pin (typically tied to an i.MX EXTRBOOT or PMIC's WAKE_IN) brings the PMIC back to active state, which restores all rails to their pre-sleep values, in the correct sequence. Linux resumes.

Without a PMIC, each rail needs its own GPIO with its own timing; the suspend driver grows complex. With a PMIC, suspend is one I²C transaction.

## 116.7  From scratch — minimal PMIC interaction over I²C

If you're prototyping with a discrete-LDO board, but want to demonstrate the principles, here's how you'd talk to a hypothetical PMIC's BUCK1 register directly:

```c
/* pmic_test.c */
#include <linux/i2c-dev.h>
#include <fcntl.h>
#include <stdio.h>
#include <sys/ioctl.h>
#include <unistd.h>

#define PMIC_ADDR 0x25
#define REG_DEV_ID 0x00
#define REG_BUCK1_VSET 0x14

static int i2c_write(int fd, uint8_t reg, uint8_t val) {
    uint8_t buf[2] = { reg, val };
    return write(fd, buf, 2) == 2 ? 0 : -1;
}

static int i2c_read(int fd, uint8_t reg, uint8_t *val) {
    if (write(fd, &reg, 1) != 1) return -1;
    return read(fd, val, 1) == 1 ? 0 : -1;
}

int main(void) {
    int fd = open("/dev/i2c-0", O_RDWR);
    ioctl(fd, I2C_SLAVE, PMIC_ADDR);

    uint8_t id;
    i2c_read(fd, REG_DEV_ID, &id);
    printf("PMIC ID: 0x%02X\n", id);

    /* Read current BUCK1 setting */
    uint8_t v;
    i2c_read(fd, REG_BUCK1_VSET, &v);
    printf("BUCK1 code: 0x%02X (Vout = %.3f V)\n", v, 0.6 + v * 0.025);

    /* Lower BUCK1 to 1.150 V (code 22 = 0.6 + 22*0.025) */
    i2c_write(fd, REG_BUCK1_VSET, 22);
    sleep(1);

    i2c_read(fd, REG_BUCK1_VSET, &v);
    printf("After: BUCK1 code: 0x%02X (Vout = %.3f V)\n", v, 0.6 + v * 0.025);

    /* WARNING: directly writing PMIC registers bypasses the regulator framework.
     * Don't do this when consumers depend on the rail (you may starve VDDARM).
     * Use only for bring-up exploration. */
    return 0;
}
```

This is for understanding; in real Linux code you go through the regulator framework via the consumer driver — never directly poke PMIC registers from an unrelated process.

## 116.8  Lab

1. **Identify PMIC.** If your i.MX6ULL board has a PMIC: `i2cdetect -y 0` to find it. Read DEV_ID register; verify it matches the chip's datasheet.
2. **DT skeleton.** If your kernel isn't using the PMIC: write a DT overlay with the PMIC node + a few rails; rebuild kernel; verify `regulator_summary` lists them.
3. **Power measurement.** Insert a shunt resistor between PSU and VDDARM rail. Measure current at 696 MHz idle, then at 396 MHz idle, then with cpufreq's `userspace` governor forcing each freq. Compute power.
4. **DVFS active.** Set the cpufreq governor to `ondemand`. Run a CPU-bound benchmark (`stress-ng --cpu 1`). Watch the regulator voltage change in real-time:
   ```sh
   watch -n0.1 cat /sys/class/regulator/regulator.0/microvolts
   ```
5. **Per-rail enable test.** Identify a non-critical rail (e.g., one for an unused peripheral). Manually disable it via sysfs `enable` knob; verify the peripheral indeed goes dead.
6. **Sleep state.** Trigger suspend-to-RAM (`echo mem > /sys/power/state`). Measure VDDARM rail — should be 0 V during suspend. Wake; resume; verify rail restored.
7. **Fault interrupt.** PMICs typically have an INT pin. Configure it as a kernel IRQ; over-current the chip (short a rail momentarily); verify the kernel sees the fault.
8. **OPP tuning.** Add a custom OPP (e.g., 528 MHz at 1.1 V — slightly under the safe-spec to see what fails). Run stress tests; record where the SoC starts to glitch (you may corrupt files; use a scratch SD).
9. **From-scratch I²C peek.** Use `pmic_test.c` to read every register; dump them; identify which rail is which by toggling each and observing what dies.
10. **Cold start sequencing trace.** With a scope on each rail's output, capture the power-on sequence. Verify timing matches the i.MX6ULL datasheet's required order.

## 116.9  Pitfalls

- **Direct PMIC register pokes bypass safety.** Lowering VDDARM below the OPP minimum mid-execution = SoC crashes immediately. Always use the regulator framework.
- **OPP table wrong voltage.** Setting 396 MHz at 1.0 V (below spec) may "work" most of the time but crashes randomly. Match the SoC datasheet exactly.
- **Sleep-mode rails not configured.** PMIC enters sleep; user-relevant rail (e.g., backlight) stays on — wakes everything via leakage. Configure SLEEP_REG for each rail.
- **No `regulator-boot-on` on rails the kernel finds already on.** Kernel assumes off, tries to enable, may sequence wrongly. Mark every pre-up rail.
- **`regulator-always-on` everywhere.** Defeats DVFS and sleep. Use only for rails that genuinely cannot disable (DDR, RTC, etc.).
- **I²C bus contention.** PMIC, EEPROM, RTC, sensors all on i2c0. PMIC ops during heavy traffic delay → DVFS transitions slow → cpufreq stalls. Put PMIC on a dedicated I²C bus if you have one spare.
- **PMIC requires VDDA before I²C.** Some PMICs (PCA9450) won't ACK I²C until their internal LDOs are up; the kernel I²C probe must retry. The driver handles this; ad-hoc test scripts may not.
- **OTP-programmed PMIC defaults.** Some PMICs ship with vendor-specific OTP values. If you got a "datasheet default" example, your part may differ. Read all registers at boot, verify against your design.
- **Ramp rate too fast.** Fast voltage steps cause overshoot. PMIC `regulator-ramp-delay` (µV/µs) controls slew; default may be too aggressive for sensitive consumers.
- **WAKE_IN polarity wrong.** Active-low vs active-high — wrong polarity = PMIC ignores wake. Spec mismatch.
- **DDR rail timing.** DDR3 needs ≤1 ms from VREF to VDDQ stable. PMIC sequence must enforce this; otherwise DDR initializes corruptly.

## 116.10  Going deeper

- **NXP PCA9450 Datasheet** + **AN12575 application note** (the design guide for i.MX8 power).
- **NXP PF8200 Datasheet** — industrial 14-rail PMIC.
- **Rohm BD71850MWV Datasheet** — compact i.MX-focused PMIC.
- **`drivers/regulator/`** — kernel framework + chip drivers.
- **`Documentation/devicetree/bindings/regulator/`** — DT binding docs.
- **`Documentation/power/regulator/`** — kernel regulator framework guide.
- **i.MX6ULL Reference Manual ch. 11 (Power Supply Strategy)** — the canonical power-up sequence.
- **Ch 51B** — runtime PM + DVFS chapter; the consumer side.
- **Ch 75** — INA226 + current monitoring; how you measure rail consumption.

---

> Next chapter: **Chapter 117 — External RTC** — the last chapter of Part VII.
