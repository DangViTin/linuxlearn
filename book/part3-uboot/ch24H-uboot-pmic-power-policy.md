---
chapter: 24H
title: PMIC and power policy in U-Boot
part: III - U-Boot, deeply
estimated_pages: 18
status: draft
---

# Chapter 24H: PMIC and power policy in U-Boot

> **What:** add early power checks to U-Boot. We read a PMIC or power-monitor over I2C, verify that important rails are present, and decide whether to continue, recover, or power off.
>
> **Why:** many boot failures are not software bugs. They are low input voltage, a disabled regulator, a PMIC fault bit, brown-out, or a rail that comes up too slowly.
>
> **Result:** U-Boot prints clear power status before Linux starts and blocks boot when a critical rail or fault state is unsafe.
>
> **Focus:** U-Boot should not become a full power manager. It should verify the minimum conditions needed to boot safely.

This chapter is written as a pattern because PMIC chips vary by board. Use your schematic and PMIC datasheet for addresses and register meanings.

## 24H.1  What U-Boot should check

Good U-Boot power checks are short and decisive.

| Check | Why it belongs before Linux |
|-------|-----------------------------|
| Input voltage too low | Booting may brown out during DDR, eMMC, or LCD current spikes. |
| PMIC reports thermal shutdown or fault | Linux may not boot far enough to log the real cause. |
| DDR rail not enabled | Continuing will produce random crashes. |
| eMMC rail off | U-Boot cannot load kernel reliably. |
| Battery too low for update | A field update may corrupt storage if power dies mid-write. |

Do not implement long-term charging policy here. Linux should manage normal runtime power.

## 24H.2  Three hardware patterns

| Pattern | U-Boot access |
|---------|---------------|
| PMIC on I2C | Read fault/status/voltage registers with I2C. |
| Regulator enable GPIOs | Read or set GPIOs before using peripherals. |
| ADC or fuel gauge on I2C | Read battery or input voltage. |

The i.MX6ULL board you use may have a simple discrete power tree or a PMIC. If there is no PMIC, still read this chapter. The method applies to any I2C power monitor or fuel gauge.

## 24H.3  Files changed in this chapter

| File | What changes |
|------|--------------|
| `configs/mx6ull_pa_mini_defconfig` | Enable I2C, GPIO, regulator, and optional power commands. |
| `arch/arm/dts/imx6ull-pa-mini.dts` | Describe the PMIC or power monitor and regulator GPIOs. |
| `board/myorg/mx6ull_pa_mini/mx6ull_pa_mini.c` | Read power status and set `bootcmd` or recovery state. |
| `include/configs/mx6ull_pa_mini.h` | Add power-fail boot command or recovery command. |

## 24H.4  Enable useful configs

Add these to `configs/mx6ull_pa_mini_defconfig`:

```text
CONFIG_BOARD_LATE_INIT=y
CONFIG_DM_I2C=y
CONFIG_SYS_I2C_MXC=y
CONFIG_CMD_I2C=y
CONFIG_DM_GPIO=y
CONFIG_CMD_GPIO=y
CONFIG_DM_REGULATOR=y
CONFIG_DM_REGULATOR_FIXED=y
CONFIG_CMD_POWEROFF=y
```

What each option does:

| Config | Meaning |
|--------|---------|
| `CONFIG_BOARD_LATE_INIT` | Runs board policy before autoboot. |
| `CONFIG_DM_I2C` | Lets U-Boot talk to I2C PMICs or monitors. |
| `CONFIG_SYS_I2C_MXC` | Enables the i.MX I2C controller driver in many U-Boot trees. |
| `CONFIG_CMD_I2C` | Adds manual I2C debugging commands. |
| `CONFIG_DM_GPIO` | Enables GPIO access through driver model. |
| `CONFIG_CMD_GPIO` | Adds manual GPIO commands. |
| `CONFIG_DM_REGULATOR` | Enables U-Boot regulator framework. |
| `CONFIG_DM_REGULATOR_FIXED` | Supports simple fixed regulators controlled by GPIO. |
| `CONFIG_CMD_POWEROFF` | Adds a poweroff command if the platform supports it. |

Not every board can power off from U-Boot. If `poweroff` is unavailable, stop at the prompt or reset into recovery.

## 24H.5  Example Device Tree for a PMIC

This is a generic example. Replace the compatible string and registers with your real PMIC.

```dts
&i2c1 {
    pinctrl-names = "default";
    pinctrl-0 = <&pinctrl_i2c1>;
    clock-frequency = <100000>;
    status = "okay";

    pmic@2d {
        compatible = "myorg,teaching-pmic";
        reg = <0x2d>;
    };
};
```

For a regulator controlled by GPIO:

```dts
reg_emmc_vmmc: regulator-emmc-vmmc {
    compatible = "regulator-fixed";
    regulator-name = "emmc-vmmc";
    regulator-min-microvolt = <3300000>;
    regulator-max-microvolt = <3300000>;
    gpio = <&gpio4 10 GPIO_ACTIVE_HIGH>;
    enable-active-high;
    regulator-always-on;
};
```

The Device Tree tells U-Boot what exists. The board code still decides policy.

## 24H.6  Manual PMIC read first

At the U-Boot prompt:

```text
pa-mini=> i2c bus
pa-mini=> i2c dev 0
pa-mini=> i2c probe
Valid chip addresses: 2d 50
```

Read a made-up status register:

```text
pa-mini=> i2c md 0x2d 0x10.1 1
0010: 00
```

For your real PMIC, replace:

| Example | Replace with |
|---------|--------------|
| I2C address `0x2d` | PMIC address from schematic |
| Register `0x10` | Fault/status register from PMIC datasheet |
| Bit meanings | Exact fault bits from PMIC datasheet |

Manual read must work before C policy code is useful.

## 24H.7  Example power policy code

Open `board/myorg/mx6ull_pa_mini/mx6ull_pa_mini.c`.

Add includes:

```c
#include <dm.h>
#include <env.h>
#include <i2c.h>
#include <stdio.h>
#include <linux/bitops.h>
#include <linux/errno.h>
```

Add a small PMIC reader:

```c
#define PA_MINI_PMIC_BUS       0
#define PA_MINI_PMIC_ADDR      0x2d
#define PMIC_REG_FAULT         0x10
#define PMIC_REG_INPUT_MV_HI   0x20
#define PMIC_REG_INPUT_MV_LO   0x21

#define PMIC_FAULT_THERMAL     BIT(0)
#define PMIC_FAULT_UVLO        BIT(1)
#define PMIC_FAULT_RAIL        BIT(2)

static int pa_mini_pmic_reg_read(uint reg)
{
    struct udevice *bus;
    struct udevice *chip;
    int ret;

    ret = uclass_get_device_by_seq(UCLASS_I2C, PA_MINI_PMIC_BUS, &bus);
    if (ret)
        return ret;

    ret = dm_i2c_probe(bus, PA_MINI_PMIC_ADDR, 0, &chip);
    if (ret)
        return ret;

    return dm_i2c_reg_read(chip, reg);
}
```

Add input-voltage read:

```c
static int pa_mini_read_input_mv(void)
{
    int hi = pa_mini_pmic_reg_read(PMIC_REG_INPUT_MV_HI);
    int lo = pa_mini_pmic_reg_read(PMIC_REG_INPUT_MV_LO);

    if (hi < 0)
        return hi;
    if (lo < 0)
        return lo;

    /*
     * Teaching example only.
     * Replace this conversion with the formula from your PMIC datasheet.
     */
    return ((hi << 8) | lo);
}
```

Add policy:

```c
#define PA_MINI_MIN_INPUT_MV 4700

static void pa_mini_block_power_boot(const char *reason)
{
    env_set("power_fail_reason", reason);
    env_set("bootcmd", "run power_fail_boot");
}

static void pa_mini_apply_power_policy(void)
{
    int fault = pa_mini_pmic_reg_read(PMIC_REG_FAULT);
    int input_mv = pa_mini_read_input_mv();

    if (fault < 0) {
        printf("PMIC not readable: %d\n", fault);
        pa_mini_block_power_boot("pmic missing");
        return;
    }

    printf("PMIC fault register: 0x%02x\n", fault);

    if (fault & PMIC_FAULT_THERMAL) {
        pa_mini_block_power_boot("pmic thermal fault");
        return;
    }

    if (fault & PMIC_FAULT_UVLO) {
        pa_mini_block_power_boot("input undervoltage");
        return;
    }

    if (fault & PMIC_FAULT_RAIL) {
        pa_mini_block_power_boot("power rail fault");
        return;
    }

    if (input_mv < 0) {
        printf("Input voltage not readable: %d\n", input_mv);
        pa_mini_block_power_boot("input voltage unknown");
        return;
    }

    printf("Input voltage: %d mV\n", input_mv);

    if (input_mv < PA_MINI_MIN_INPUT_MV) {
        pa_mini_block_power_boot("input voltage too low");
        return;
    }
}
```

Call it from `board_late_init()`:

```c
int board_late_init(void)
{
    pa_mini_apply_power_policy();
    return 0;
}
```

If you already have identity, temperature, or recovery checks, call power policy early. There is no point reading many optional devices if the power tree is unsafe.

## 24H.8  Default environment for power failure

In `include/configs/mx6ull_pa_mini.h`:

```c
#define PA_MINI_POWER_ENV \
    "power_fail_reason=\0" \
    "power_fail_boot=echo Power check failed: ${power_fail_reason}; " \
        "echo Connect stable power and reset; false\0"
```

If your platform supports poweroff:

```c
"power_fail_boot=echo Power check failed: ${power_fail_reason}; poweroff\0"
```

For a lab, stopping at the prompt is better because the reader can inspect variables:

```text
pa-mini=> printenv power_fail_reason
```

## 24H.9  Low battery update block

A power check can also block updates while still allowing normal boot.

Example:

```text
update_allowed=1
```

Board code:

```c
if (input_mv < 4800)
    env_set("update_allowed", "0");
else
    env_set("update_allowed", "1");
```

Update command:

```text
safe_update=if test "${update_allowed}" = "1"; then run do_update; else echo Update blocked: low power; false; fi
```

This is useful for battery products. A low battery may be enough for normal boot but not safe for flashing.

## 24H.10  When to fail open

Power policy is usually fail-closed for critical rails:

| Failure | Boot? |
|---------|-------|
| PMIC thermal fault | No |
| Undervoltage lockout | No |
| DDR rail fault | No |
| PMIC unreadable on a PMIC-based board | No |
| Battery gauge unreadable on a non-battery board | Maybe yes |
| Optional peripheral rail fault | Maybe boot with that peripheral disabled |

Write the rule down in the board README. Future engineers should not have to infer why U-Boot refuses to boot.

## 24H.11  Lab

1. Identify whether your board has a PMIC, power monitor, battery gauge, or only fixed regulators.
2. Find the I2C address and status registers in the schematic and datasheet.
3. Prove manual reads with `i2c probe` and `i2c md`.
4. Add a small PMIC read function.
5. Print fault status and input voltage at boot.
6. Add `power_fail_boot`.
7. Force the failure path by temporarily raising `PA_MINI_MIN_INPUT_MV`.
8. Confirm U-Boot blocks boot and prints the reason.
9. Restore the threshold and confirm normal boot.

## 24H.12  Pitfalls

- **Copying PMIC register meanings from another chip.** PMICs are not interchangeable.
- **Blocking boot on an optional monitor.** If the hardware is optional, define the fallback behavior.
- **Doing charging policy in U-Boot.** Linux should manage normal charging and thermal policy.
- **No visible reason.** Always print why boot was blocked.
- **Poweroff without serial output.** A board that powers off instantly is hard to debug.
- **Ignoring rail timing.** A rail can be enabled but not yet stable. Respect PMIC timing specs.
- **Forgetting update current.** Flashing can draw more current than idle boot.

## 24H.13  Going deeper

- U-Boot `drivers/power/pmic/`, for PMIC drivers.
- U-Boot `drivers/power/regulator/`, for regulator support.
- U-Boot `cmd/i2c.c`, for manual I2C access.
- Linux regulator framework, for the runtime version of the same power tree.
- PMIC datasheet fault registers and startup timing diagrams.

---

**Previous:** [Chapter 24G: Factory and recovery modes in U-Boot](ch24G-uboot-factory-recovery-usb.md)

**Next:** [Chapter 24I: U-Boot display and boot screen](ch24I-uboot-display-splash.md)
