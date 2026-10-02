---
chapter: 24D
title: Board identity and variant selection in U-Boot
part: III - U-Boot, deeply
estimated_pages: 18
status: draft
---

# Chapter 24D: Board identity and variant selection in U-Boot

> **What:** read a board identity from EEPROM or strap GPIOs, then choose the correct kernel Device Tree or FIT configuration before Linux starts.
>
> **Why:** real products often have several hardware variants. Same SoC, same PCB family, different LCD, RAM size, sensor option, PHY address, or customer configuration. Linux must receive the correct hardware description from the first instruction it runs.
>
> **Result:** one U-Boot binary can boot several board variants by reading a small identity value at boot time.
>
> **Focus:** identify the board before choosing the DTB. Do not make Linux guess hardware that U-Boot could have identified safely.

This chapter builds on Chapters 24B and 23. It teaches where the variant value comes from and how to make that value reliable. Chapter 24E then uses this value to select a FIT configuration or apply a Device Tree overlay.

## 24D.1  The real problem

A product family may look like this:

| Variant | Difference |
|---------|------------|
| Rev A | No LCD, 256 MiB DDR, one Ethernet port |
| Rev B | 4.3 inch LCD, 512 MiB DDR, one Ethernet port |
| Rev C | 7 inch LCD, 512 MiB DDR, Ethernet plus RS-485 |
| Customer X | Same as Rev C, but different I2C touch address |

The kernel Device Tree must match those differences. If it does not:

- Linux may drive a pin that is not connected on this board.
- The LCD timing may be wrong.
- The wrong I2C address may be used.
- The kernel may think more RAM exists than the board has.
- Ethernet PHY reset or address may be wrong.

U-Boot is the right place to choose the DTB because U-Boot already loads the DTB.

## 24D.2  Three ways to identify a board

| Method | Good for | Weakness |
|--------|----------|----------|
| Strap GPIOs | Very simple hardware variants | Limited number of variants. Requires resistors or jumpers. |
| I2C EEPROM | Board revision, serial, MAC address, calibration | Needs I2C working before boot. EEPROM must be programmed in factory. |
| SoC fuse or unique ID | Stable chip identity | Does not describe board options unless factory data maps chip ID to board data. |

Most products use EEPROM or fuses for identity and GPIO straps for emergency recovery or simple options.

For this chapter, we use an I2C EEPROM at address `0x50`, because Chapter 18 already introduced that hardware shape.

## 24D.3  Do not let the identity format grow by accident

Define a tiny EEPROM layout and keep it stable.

Example layout:

| Offset | Size | Field | Example |
|--------|------|-------|---------|
| `0x00` | 8 | Magic string | `PAMINI1` plus NUL |
| `0x08` | 1 | Hardware revision | `1`, `2`, `3` |
| `0x09` | 1 | LCD option | `0` none, `1` 4.3 inch, `2` 7 inch |
| `0x0A` | 1 | Ethernet option | `1` one port, `2` two ports |
| `0x0B` | 1 | Reserved | `0` |
| `0x10` | 6 | MAC address | `00 04 9f 12 34 56` |
| `0x20` | 16 | Serial string | ASCII serial, NUL padded |
| `0x30` | 4 | CRC32 over bytes `0x00` to `0x2F` | optional |

Start small. Add fields only when a real boot decision needs them.

Do not parse a human text file from EEPROM in early boot. A fixed binary layout is easier to validate.

## 24D.4  Files changed in this chapter

| File | What changes |
|------|--------------|
| `configs/mx6ull_pa_mini_defconfig` | Enable I2C, environment editing, and FIT or FDT selection commands. |
| `arch/arm/dts/imx6ull-pa-mini.dts` | Ensure the EEPROM's I2C bus is enabled. |
| `board/myorg/mx6ull_pa_mini/mx6ull_pa_mini.c` | Read EEPROM and set `board_rev`, `fdtfile`, or `fitconf`. |
| `include/configs/mx6ull_pa_mini.h` | Add default boot variables that use the selected identity. |

## 24D.5  Enable the useful configs

Add these to `configs/mx6ull_pa_mini_defconfig`:

```text
CONFIG_BOARD_LATE_INIT=y
CONFIG_DM_I2C=y
CONFIG_SYS_I2C_MXC=y
CONFIG_CMD_I2C=y
CONFIG_CMD_SETEXPR=y
CONFIG_FIT=y
CONFIG_CMD_BOOTM=y
CONFIG_CMD_FDT=y
CONFIG_OF_LIBFDT_OVERLAY=y
```

What each option does:

| Config | Meaning |
|--------|---------|
| `CONFIG_BOARD_LATE_INIT` | Lets board code run after normal board setup and before `bootcmd`. |
| `CONFIG_DM_I2C` | Enables driver-model I2C devices. |
| `CONFIG_SYS_I2C_MXC` | Enables the i.MX I2C controller driver in many U-Boot trees. Check `drivers/i2c/Kconfig` if your tree uses another symbol. |
| `CONFIG_CMD_I2C` | Adds manual I2C commands for testing. |
| `CONFIG_CMD_SETEXPR` | Useful for small environment string transformations. |
| `CONFIG_FIT` | Enables FIT image support. |
| `CONFIG_CMD_BOOTM` | Adds the `bootm` command used for FIT images. |
| `CONFIG_CMD_FDT` | Adds the `fdt` command. Useful for manual DT edits and overlay testing. |
| `CONFIG_OF_LIBFDT_OVERLAY` | Allows U-Boot to apply DT overlays. |

If you only choose between separate `.dtb` files and do not use FIT overlays, `CONFIG_OF_LIBFDT_OVERLAY` is not required.

## 24D.6  Manual EEPROM read first

Boot to the U-Boot prompt:

```text
pa-mini=> i2c bus
pa-mini=> i2c dev 0
pa-mini=> i2c probe
Valid chip addresses: 50
```

Read the first 48 bytes:

```text
pa-mini=> i2c md 0x50 0x00.1 0x30
0000: 50 41 4d 49 4e 49 31 00 02 01 01 00 ff ff ff ff
0010: 00 04 9f 12 34 56 00 00 00 00 00 00 00 00 00 00
0020: 50 41 4d 49 4e 49 2d 30 30 31 00 00 00 00 00 00
```

Decode the first lines:

| Bytes | Meaning |
|-------|---------|
| `50 41 4d 49 4e 49 31 00` | ASCII `PAMINI1`, then NUL |
| `02` | hardware revision 2 |
| `01` | LCD option 1 |
| `01` | Ethernet option 1 |

Do not write board code until this manual read works.

## 24D.7  Board code to read identity

Open `board/myorg/mx6ull_pa_mini/mx6ull_pa_mini.c`.

Add includes:

```c
#include <dm.h>
#include <env.h>
#include <i2c.h>
#include <stdio.h>
#include <string.h>
#include <linux/errno.h>
```

Add a small structure:

```c
#define PA_MINI_ID_BUS      0
#define PA_MINI_ID_EEPROM   0x50
#define PA_MINI_ID_LEN      0x30

struct pa_mini_id {
    char magic[8];
    uint8_t hw_rev;
    uint8_t lcd_opt;
    uint8_t eth_opt;
    uint8_t reserved;
    uint8_t reserved2[4];
    uint8_t mac[6];
    uint8_t reserved3[10];
    char serial[16];
};
```

Add the reader:

```c
static int pa_mini_read_id(struct pa_mini_id *id)
{
    struct udevice *bus;
    struct udevice *chip;
    int ret;

    ret = uclass_get_device_by_seq(UCLASS_I2C, PA_MINI_ID_BUS, &bus);
    if (ret)
        return ret;

    ret = dm_i2c_probe(bus, PA_MINI_ID_EEPROM, 0, &chip);
    if (ret)
        return ret;

    ret = dm_i2c_read(chip, 0x00, (uint8_t *)id, sizeof(*id));
    if (ret)
        return ret;

    if (memcmp(id->magic, "PAMINI1", 7))
        return -EINVAL;

    return 0;
}
```

Then map the identity to environment variables:

```c
static void pa_mini_apply_id(const struct pa_mini_id *id)
{
    env_set_ulong("board_rev", id->hw_rev);
    env_set_ulong("lcd_opt", id->lcd_opt);
    env_set_ulong("eth_opt", id->eth_opt);

    if (id->serial[0])
        env_set("serial#", id->serial);

    if (id->mac[0] || id->mac[1] || id->mac[2] ||
        id->mac[3] || id->mac[4] || id->mac[5]) {
        char mac[18];

        snprintf(mac, sizeof(mac), "%02x:%02x:%02x:%02x:%02x:%02x",
                 id->mac[0], id->mac[1], id->mac[2],
                 id->mac[3], id->mac[4], id->mac[5]);
        env_set("ethaddr", mac);
    }

    switch (id->lcd_opt) {
    case 0:
        env_set("fitconf", "conf-no-lcd");
        env_set("fdtfile", "imx6ull-pa-mini-no-lcd.dtb");
        break;
    case 1:
        env_set("fitconf", "conf-lcd43");
        env_set("fdtfile", "imx6ull-pa-mini-lcd43.dtb");
        break;
    case 2:
        env_set("fitconf", "conf-lcd70");
        env_set("fdtfile", "imx6ull-pa-mini-lcd70.dtb");
        break;
    default:
        env_set("fitconf", "conf-safe");
        env_set("fdtfile", "imx6ull-pa-mini-safe.dtb");
        break;
    }
}
```

Call it from `board_late_init()`:

```c
int board_late_init(void)
{
    struct pa_mini_id id;
    int ret;

    ret = pa_mini_read_id(&id);
    if (ret) {
        printf("Board identity missing or invalid: %d\n", ret);
        env_set("fitconf", "conf-safe");
        env_set("fdtfile", "imx6ull-pa-mini-safe.dtb");
        return 0;
    }

    pa_mini_apply_id(&id);
    printf("Board rev %lu, LCD option %lu, DT %s\n",
           env_get_ulong("board_rev", 10, 0),
           env_get_ulong("lcd_opt", 10, 0),
           env_get("fdtfile"));
    return 0;
}
```

If your Chapter 22 board already has `board_late_init()`, merge this code into the existing function.

## 24D.8  Boot with separate DTB files

This is the easiest path:

```text
load mmc 0:1 ${kernel_addr_r} zImage
load mmc 0:1 ${fdt_addr_r} ${fdtfile}
bootz ${kernel_addr_r} - ${fdt_addr_r}
```

Your board code sets `fdtfile`. The boot command simply uses it.

Default environment:

```c
"kernel_addr_r=0x82000000\0" \
"fdt_addr_r=0x83000000\0" \
"bootcmd=load mmc 0:1 ${kernel_addr_r} zImage; " \
    "load mmc 0:1 ${fdt_addr_r} ${fdtfile}; " \
    "bootz ${kernel_addr_r} - ${fdt_addr_r}\0"
```

This is simple and works well when you have only a few variants.

## 24D.9  Boot with a FIT configuration

If you ship one FIT image, let board code choose the FIT configuration.

Default environment:

```c
"fit_addr_r=0x82000000\0" \
"fitfile=kernel.itb\0" \
"fitconf=conf-safe\0" \
"bootcmd=load mmc 0:1 ${fit_addr_r} ${fitfile}; " \
    "bootm ${fit_addr_r}#${fitconf}\0"
```

The board code sets:

```text
fitconf=conf-lcd43
```

Then `bootm` selects:

```text
kernel.itb#conf-lcd43
```

This avoids carrying many loose `.dtb` files on the boot partition.

## 24D.10  Boot with a base DTB plus overlay

For options that can be layered, use one base DTB and overlays.

Example environment:

```text
base_dtb=imx6ull-pa-mini-base.dtb
overlay_lcd43=overlays/lcd43.dtbo
overlay_rs485=overlays/rs485.dtbo
```

Manual test:

```text
pa-mini=> load mmc 0:1 ${fdt_addr_r} ${base_dtb}
pa-mini=> fdt addr ${fdt_addr_r}
pa-mini=> fdt resize 8192
pa-mini=> load mmc 0:1 ${fdtoverlay_addr_r} ${overlay_lcd43}
pa-mini=> fdt apply ${fdtoverlay_addr_r}
pa-mini=> bootz ${kernel_addr_r} - ${fdt_addr_r}
```

Important details:

- `fdt resize` gives the base DTB room to grow.
- The overlay must be compiled with symbols using `dtc -@`.
- Apply overlays before `bootz` or `bootm`.

Use overlays when variants differ by small optional hardware blocks. Use separate DTBs when the whole board description changes.

## 24D.11  What if identity is missing?

Decide this before production.

| Missing data | Suggested behavior |
|--------------|--------------------|
| Missing board revision | Boot `conf-safe` or stop at prompt. |
| Missing MAC address | Generate temporary MAC only for lab. In production, stop or mark factory failure. |
| Missing serial number | Boot is usually okay, but factory test should fail. |
| Invalid CRC | Stop or safe config. Do not trust partially corrupted data. |

For a shipping product, avoid guessing. A board with unknown identity should enter recovery or factory mode, not boot with a random DTB.

## 24D.12  Lab

1. Define a simple EEPROM identity layout.
2. Read it manually with `i2c md`.
3. Add `pa_mini_read_id()` to board code.
4. Set `board_rev`, `lcd_opt`, `serial#`, and `ethaddr`.
5. Choose either `fdtfile` or `fitconf`.
6. Boot two fake variants by changing only the EEPROM byte or a test override variable.
7. Remove or corrupt the magic string and confirm the board uses `conf-safe` or stops.

## 24D.13  Pitfalls

- **Using Linux Device Tree to identify the board.** U-Boot must choose the DTB before Linux receives it.
- **No factory programming step.** EEPROM identity is useless if nobody writes it during manufacturing.
- **No CRC.** A single corrupted byte can select the wrong hardware.
- **Saving auto-detected values permanently.** Usually let U-Boot detect on every boot. Do not `saveenv` auto-detected `fdtfile` unless you mean it.
- **Board identity mixed with user settings.** Keep factory identity in EEPROM or fuses. Keep user boot preferences in U-Boot environment.
- **Too many variants too early.** Start with two. Prove the mechanism. Then scale.

## 24D.14  Going deeper

- U-Boot `include/i2c.h`, for the driver-model I2C API.
- U-Boot `doc/usage/fdt_overlays.rst`, for manual overlay flow.
- U-Boot `doc/usage/fit/overlay-fdt-boot.rst`, for FIT configurations with overlays.
- `cmd/fdt.c`, for the `fdt resize` and `fdt apply` commands.
- `cmd/bootm.c`, for FIT configuration selection.

---

**Previous:** [Chapter 24C: Ethernet fallback boot in U-Boot](ch24C-uboot-ethernet-fallback-boot.md)

**Next:** [Chapter 24E: Multi-variant FIT images and DT overlays](ch24E-multi-variant-fit.md)
