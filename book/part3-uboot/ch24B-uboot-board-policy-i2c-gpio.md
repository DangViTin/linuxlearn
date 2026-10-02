---
chapter: 24B
title: U-Boot board policy with GPIO and I2C
part: III - U-Boot, deeply
estimated_pages: 18
status: draft
---

# Chapter 24B: U-Boot board policy with GPIO and I2C

> **What:** add board-specific boot decisions to the U-Boot port from Chapter 22. We read a GPIO button, read an I2C temperature sensor, and block Linux boot when the board is too hot.
>
> **Why:** many products must make one or two decisions before Linux starts. Maybe the board is too hot. Maybe a factory button is held. Maybe an EEPROM says this is a different hardware revision.
>
> **Result:** the board still boots normally when the sensor reads below 50 C. If the sensor reads 50 C or higher, U-Boot prints the reason and stops at the prompt instead of starting Linux.
>
> **Focus:** keep U-Boot policy small. U-Boot is a bootloader, not an application runtime. Use it for decisions that must happen before the kernel.

This chapter starts from the board port in Chapter 22:

```text
board/myorg/mx6ull_pa_mini/
configs/mx6ull_pa_mini_defconfig
arch/arm/dts/imx6ull-pa-mini.dts
include/configs/mx6ull_pa_mini.h
```

We do not make a new board port. We extend the one we already have.

## 24B.1  What belongs in U-Boot policy

Use U-Boot for a decision only when the decision must happen before Linux.

| Scenario | Good U-Boot job? | Why |
|----------|------------------|-----|
| Stop boot when board temperature is unsafe | Yes | Linux should not start if the hardware may already be outside the safe range. |
| Read a factory key button and enter recovery | Yes | The user needs recovery before the kernel and rootfs are trusted. |
| Read an EEPROM board revision and choose a DTB | Yes | The kernel needs the right hardware description from the start. |
| Poll a sensor every second forever | No | That is an application or kernel driver job. |
| Run fan control while Linux is alive | No | The kernel has thermal and PWM frameworks for this. |
| Download updates over the network | Usually no | U-Boot can do it, but Linux is better for complex networking. |

The rule is simple:

> If the result changes what image we boot, what DTB we pass, or whether we boot at all, U-Boot is a reasonable place.

Everything else should move to Linux.

## 24B.2  Files changed in this chapter

We touch four places.

| File | What changes |
|------|--------------|
| `configs/mx6ull_pa_mini_defconfig` | Enable GPIO, I2C, and the board late-init hook. |
| `arch/arm/dts/imx6ull-pa-mini.dts` | Describe the I2C bus and the temperature sensor. |
| `board/myorg/mx6ull_pa_mini/mx6ull_pa_mini.c` | Add the C code that reads the sensor and changes `bootcmd`. |
| `include/configs/mx6ull_pa_mini.h` | Add default environment variables used by the policy. |

This is the same method as Chapter 22:

1. Enable the generic U-Boot feature in defconfig.
2. Describe the hardware in the U-Boot Device Tree.
3. Put board-specific behavior in the board directory.
4. Keep default boot commands in the board config or default environment.

## 24B.3  Enable the needed U-Boot features

Open `configs/mx6ull_pa_mini_defconfig` and add:

```text
CONFIG_BOARD_LATE_INIT=y
CONFIG_DM_GPIO=y
CONFIG_CMD_GPIO=y
CONFIG_DM_I2C=y
CONFIG_SYS_I2C_MXC=y
CONFIG_CMD_I2C=y
CONFIG_CMD_SETEXPR=y
```

What each option does:

| Config | Meaning |
|--------|---------|
| `CONFIG_BOARD_LATE_INIT` | Calls your board's `board_late_init()` before the autoboot command runs. This is where we set policy variables. |
| `CONFIG_DM_GPIO` | Enables U-Boot driver-model GPIO support. Driver model means U-Boot finds devices from the Device Tree. |
| `CONFIG_CMD_GPIO` | Adds the `gpio` command at the U-Boot prompt. Useful for manual testing. |
| `CONFIG_DM_I2C` | Enables driver-model I2C support. |
| `CONFIG_SYS_I2C_MXC` | Enables the i.MX I2C controller driver in many U-Boot trees. If your tree uses a renamed symbol, search `drivers/i2c/Kconfig` for the i.MX or MXC I2C driver. |
| `CONFIG_CMD_I2C` | Adds the `i2c` command at the U-Boot prompt. Useful before writing C policy code. |
| `CONFIG_CMD_SETEXPR` | Adds simple integer and string expression support to U-Boot scripts. Useful for later environment-only experiments. |

Run this after editing:

```sh
$ make mx6ull_pa_mini_defconfig
$ grep -E 'BOARD_LATE_INIT|DM_GPIO|CMD_GPIO|DM_I2C|I2C|CMD_SETEXPR' .config
```

The `grep` output should show each option as `=y`.

## 24B.4  Add the I2C sensor to the U-Boot Device Tree

This example assumes a TMP102-compatible temperature sensor at 7-bit I2C address `0x48` on I2C1.

If your real board uses a different sensor, keep the method and change the address and conversion code.

Add this to `arch/arm/dts/imx6ull-pa-mini.dts`:

```dts
&i2c1 {
    pinctrl-names = "default";
    pinctrl-0 = <&pinctrl_i2c1>;
    clock-frequency = <100000>;
    status = "okay";

    temp_sensor: temperature-sensor@48 {
        compatible = "ti,tmp102";
        reg = <0x48>;
    };
};

&iomuxc {
    pinctrl_i2c1: i2c1grp {
        fsl,pins = <
            MX6UL_PAD_UART4_RX_DATA__I2C1_SCL 0x4001b8b0
            MX6UL_PAD_UART4_TX_DATA__I2C1_SDA 0x4001b8b0
        >;
    };
};
```

The two pad lines are board-specific. They mean:

| Line | Meaning |
|------|---------|
| `MX6UL_PAD_UART4_RX_DATA__I2C1_SCL` | Route the physical pad normally called `UART4_RX_DATA` to the I2C1 clock function. |
| `MX6UL_PAD_UART4_TX_DATA__I2C1_SDA` | Route the physical pad normally called `UART4_TX_DATA` to the I2C1 data function. |
| `0x4001b8b0` | Electrical pad settings. This value enables the open-drain and pull behavior normally needed by I2C on i.MX6ULL boards. |

The pad name can look strange. A pad name is not the function you must use. It is the package pin name. The mux part after `__` is the function selected on that pin.

If your schematic says I2C1 uses different pads, use the matching macros from the i.MX6ULL pin header.

## 24B.5  Test I2C before writing policy code

Build and boot U-Boot, then test from the prompt:

```text
pa-mini=> i2c bus
Bus 0:  i2c@21a0000

pa-mini=> i2c dev 0
Setting bus to 0

pa-mini=> i2c probe
Valid chip addresses: 48 50
```

Address `0x48` is the temperature sensor in this example. Address `0x50` may be an EEPROM from Chapter 18.

Read the TMP102 temperature register:

```text
pa-mini=> i2c md 0x48 0x00.1 2
0000: 19 00
```

`0x19 0x00` is 25 C on a TMP102-like sensor:

```text
0x19 = decimal 25
```

Do this manual test first. If manual I2C does not work, C code will not fix it.

## 24B.6  Add default policy variables

In `include/configs/mx6ull_pa_mini.h`, add defaults like this to your extra environment:

```c
#define PA_MINI_EXTRA_ENV_SETTINGS \
    "temp_limit_c=50\0" \
    "boot_block_reason=\0" \
    "normal_boot=run mmcboot\0" \
    "blocked_boot=echo Boot blocked: ${boot_block_reason}; false\0"
```

Then include those defaults in the board environment block. The exact macro name depends on how your Chapter 22 board header is organized. A common pattern is:

```c
#define CFG_EXTRA_ENV_SETTINGS \
    PA_MINI_EXTRA_ENV_SETTINGS \
    "console=ttymxc0,115200\0" \
    "fdtfile=imx6ull-pa-mini.dtb\0" \
    "bootcmd=run normal_boot\0"
```

These variables are not magic:

| Variable | Used for |
|----------|----------|
| `temp_limit_c` | Temperature threshold in degrees C. |
| `boot_block_reason` | Text printed when the board refuses to boot. |
| `normal_boot` | The normal Linux boot path. This should point to the boot command you already use. |
| `blocked_boot` | A command that prints the reason and returns failure. |
| `bootcmd` | The command U-Boot runs automatically after `bootdelay`. |

Keep `normal_boot` as a separate variable. That way the policy code can switch `bootcmd` between `run normal_boot` and `run blocked_boot` without rewriting your real boot command.

## 24B.7  Add the temperature read code

Open `board/myorg/mx6ull_pa_mini/mx6ull_pa_mini.c`.

Add these includes near the top:

```c
#include <dm.h>
#include <env.h>
#include <i2c.h>
#include <stdio.h>
#include <linux/errno.h>
```

Add this code:

```c
#define PA_MINI_TEMP_BUS     0
#define PA_MINI_TEMP_ADDR    0x48
#define PA_MINI_TEMP_LIMIT_C 50

static int pa_mini_read_tmp102_c(int *temp_cp)
{
    struct udevice *bus;
    struct udevice *chip;
    uint8_t raw[2];
    int sample;
    int ret;

    ret = uclass_get_device_by_seq(UCLASS_I2C, PA_MINI_TEMP_BUS, &bus);
    if (ret)
        return ret;

    ret = dm_i2c_probe(bus, PA_MINI_TEMP_ADDR, 0, &chip);
    if (ret)
        return ret;

    ret = dm_i2c_read(chip, 0x00, raw, sizeof(raw));
    if (ret)
        return ret;

    /*
     * TMP102 temperature register:
     * raw[0] bits 7..0 are the upper temperature bits.
     * raw[1] bits 7..4 are the lower temperature bits.
     * The 12-bit value is signed and each count is 0.0625 C.
     */
    sample = ((int)raw[0] << 4) | (raw[1] >> 4);
    if (sample & 0x800)
        sample |= ~0xfff;

    *temp_cp = (sample * 625) / 10000;
    return 0;
}

static void pa_mini_block_boot(const char *reason)
{
    env_set("boot_block_reason", reason);
    env_set("bootcmd", "run blocked_boot");
}

static void pa_mini_apply_temperature_policy(void)
{
    int limit = env_get_ulong("temp_limit_c", 10, PA_MINI_TEMP_LIMIT_C);
    int temp_c;
    int ret;

    ret = pa_mini_read_tmp102_c(&temp_c);
    if (ret) {
        printf("Temperature sensor not readable: %d\n", ret);
        pa_mini_block_boot("temperature sensor missing");
        return;
    }

    printf("Board temperature: %d C\n", temp_c);
    env_set_ulong("board_temp_c", temp_c);

    if (temp_c >= limit) {
        printf("Temperature limit is %d C\n", limit);
        pa_mini_block_boot("temperature too high");
    }
}
```

Then call it from `board_late_init()`:

```c
int board_late_init(void)
{
    pa_mini_apply_temperature_policy();
    return 0;
}
```

If your board already has a `board_late_init()`, add the call inside the existing function instead of creating a second one.

## 24B.8  Why `board_late_init()` is the right hook

U-Boot has many board hooks. Use the latest hook that still happens before the decision is needed.

| Hook | When it runs | Good for this? |
|------|--------------|----------------|
| `board_init_f()` | Very early, before relocation | No. Too early for normal driver model devices. |
| `board_init()` | Board setup before many commands are ready | Sometimes, but still early. |
| `board_late_init()` | After core board setup, before autoboot | Yes. Good for setting environment variables and board policy. |
| `bootcmd` | In the command interpreter | Yes for script policy, but C code is cleaner for sensor conversion. |

For I2C temperature policy, `board_late_init()` is a good place because:

- I2C driver model is available.
- The environment is available.
- Autoboot has not run yet.
- The code still runs once per boot, not forever.

## 24B.9  Build and test

Rebuild:

```sh
$ make distclean
$ make mx6ull_pa_mini_defconfig
$ make -j$(nproc)
```

Boot the board. A normal boot should print something like:

```text
Board temperature: 27 C
Hit any key to stop autoboot:  2
```

At the prompt:

```text
pa-mini=> printenv board_temp_c temp_limit_c bootcmd
board_temp_c=27
temp_limit_c=50
bootcmd=run normal_boot
```

Force the blocked path without heating the board:

```text
pa-mini=> setenv temp_limit_c 1
pa-mini=> reset
```

Next boot:

```text
Board temperature: 27 C
Temperature limit is 1 C
Hit any key to stop autoboot:  2
Boot blocked: temperature too high
pa-mini=>
```

Undo the test:

```text
pa-mini=> setenv temp_limit_c 50
pa-mini=> saveenv
```

## 24B.10  Add a GPIO recovery button

The same pattern works for a button.

For manual testing, use the `gpio` command:

```text
pa-mini=> gpio status -a
pa-mini=> gpio input gpio1_18
pa-mini=> gpio read key0 gpio1_18
pa-mini=> echo ${key0}
```

Different U-Boot versions name GPIOs differently. Some use names like `gpio1_18`. Some use numeric GPIO numbers. Use `gpio status -a` to see what your build exposes.

For a production board, prefer the Device Tree button driver or a named GPIO from the Device Tree. The idea is the same:

1. Read the pin.
2. If the button is pressed, set `bootcmd` to recovery.
3. If not pressed, leave `bootcmd` normal.

Environment-only version:

```text
recovery_check=gpio input gpio1_18; gpio read key0 gpio1_18; \
    if test "${key0}" = "0"; then \
        echo Factory key held; \
        setenv bootcmd run recovery_boot; \
    fi
```

Then call it before normal boot:

```text
bootcmd=run recovery_check; run normal_boot
```

The exact command uses semicolons because this is U-Boot shell syntax. Keep the prose simple, but do not remove shell separators from command strings.

## 24B.11  Fail-open or fail-closed

A policy check must say what happens if the peripheral is missing.

| Check | Safer default |
|-------|---------------|
| Temperature too high | Block boot. |
| Temperature sensor missing | Usually block boot in production. Allow boot in early lab work if the sensor is optional. |
| Factory recovery button unreadable | Usually boot normally, unless the product has no other recovery path. |
| EEPROM board ID unreadable | Usually stop, because the wrong DTB can drive pins incorrectly. |
| PMIC fault pin asserted | Block boot. |

For this chapter we fail closed for temperature:

```c
if (ret) {
    pa_mini_block_boot("temperature sensor missing");
    return;
}
```

In a teaching lab without the sensor fitted, change that to a warning and return.

## 24B.12  Lab

1. Enable the GPIO and I2C config options.
2. Add the I2C1 node to the U-Boot Device Tree.
3. Prove `i2c probe` sees the expected address.
4. Add the C temperature reader.
5. Boot with `temp_limit_c=50` and confirm normal boot.
6. Boot with `temp_limit_c=1` and confirm U-Boot blocks Linux.
7. Add one GPIO recovery key check, either in C or as a `bootcmd` helper.

## 24B.13  Pitfalls

- **Using the 8-bit I2C address.** U-Boot uses the 7-bit address. Use `0x48`, not `0x90`.
- **Wrong I2C bus number.** `i2c bus` shows U-Boot bus numbering. It may not match the Linux adapter number.
- **Pad mux not set.** If the pads are still UART pins, I2C will not respond.
- **Missing pull-ups.** I2C needs pull-up resistors. Software cannot fix missing hardware pull-ups.
- **Calling I2C too early.** Do not put driver-model I2C reads in very early init code.
- **Saving a test `bootcmd`.** If you save a temporary blocked `bootcmd`, the board will keep blocking on every boot. Use `env default bootcmd` to restore the compiled default.
- **Doing too much in U-Boot.** A short gate is fine. A full thermal manager belongs in Linux.

## 24B.14  Going deeper

- `include/i2c.h`, for `dm_i2c_read()`, `dm_i2c_probe()`, and `i2c_get_chip_for_busnum()`.
- `cmd/i2c.c`, for how the U-Boot `i2c` command talks to the same driver-model API.
- `cmd/gpio.c`, for how `gpio read` stores a pin value into an environment variable.
- `common/autoboot.c`, for where `bootcmd` is run.
- `common/board_r.c`, for the late init sequence.

---

**Previous:** [Chapter 24A: Building i.MX6ULL U-Boot from nothing](ch24A-uboot-new-soc-from-scratch.md)

**Next:** [Chapter 24C: Ethernet fallback boot in U-Boot](ch24C-uboot-ethernet-fallback-boot.md)
