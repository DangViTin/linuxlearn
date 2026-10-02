---
chapter: 24G
title: Factory and recovery modes in U-Boot
part: III - U-Boot, deeply
estimated_pages: 18
status: draft
---

# Chapter 24G: Factory and recovery modes in U-Boot

> **What:** add a recovery mode to U-Boot. When a button is held at power-on, U-Boot exposes storage over USB or enters DFU mode instead of booting Linux.
>
> **Why:** every product needs a way back when the rootfs is broken, the kernel is missing, or the normal boot command is wrong. Factory also needs a controlled mode for flashing and test.
>
> **Result:** holding the recovery key at reset starts a USB service. The host can reflash or inspect the board without Linux running.
>
> **Focus:** recovery must be simple, visible, and hard to enter by accident.

This chapter is about service and factory workflows. It is not a replacement for the Boot ROM's USB SDP mode from Chapter 8. SDP can recover a dead bootloader. U-Boot recovery can recover a dead kernel or rootfs after U-Boot still starts.

## 24G.1  Recovery levels

| Level | Who runs | What it can fix |
|-------|----------|-----------------|
| Boot ROM SDP | i.MX6ULL ROM | Broken or erased U-Boot. |
| U-Boot recovery | U-Boot | Broken kernel, DTB, rootfs, environment, or application. |
| Linux recovery image | Small Linux system | Complex repair, logs, networking, UI. |
| Main Linux | Normal product OS | Normal operation. |

Do not confuse them. If U-Boot itself is corrupted, U-Boot recovery cannot run. Use SDP.

## 24G.2  Files changed in this chapter

| File | What changes |
|------|--------------|
| `configs/mx6ull_pa_mini_defconfig` | Enable USB gadget, UMS, and DFU commands. |
| `arch/arm/dts/imx6ull-pa-mini.dts` | Ensure USB OTG controller and recovery button are described. |
| `board/myorg/mx6ull_pa_mini/mx6ull_pa_mini.c` | Detect the recovery key and set `bootcmd`. |
| `include/configs/mx6ull_pa_mini.h` | Add recovery commands. |

## 24G.3  Choose the recovery method

U-Boot gives several useful recovery tools.

| Method | Host view | Good for |
|--------|-----------|----------|
| UMS | Board appears as a USB mass-storage disk | Simple copying and reflashing by humans. |
| DFU | Host uses `dfu-util` | Factory flashing with named targets. |
| Fastboot | Host uses `fastboot` or `uuu` scripts | Android-style or NXP-style flashing flows. |
| TFTP recovery | Board pulls files from host over Ethernet | Lab networks and production test fixtures. |

For a beginner-friendly chapter, use UMS first. It is visible on the host as a disk.

Then add DFU for a more controlled factory path.

## 24G.4  Enable USB recovery configs

Add these to `configs/mx6ull_pa_mini_defconfig`:

```text
CONFIG_USB=y
CONFIG_DM_USB=y
CONFIG_USB_GADGET=y
CONFIG_USB_GADGET_DOWNLOAD=y
CONFIG_USB_GADGET_MANUFACTURER="MyOrg"
CONFIG_USB_GADGET_VENDOR_NUM=0x1fc9
CONFIG_USB_GADGET_PRODUCT_NUM=0x0152
CONFIG_CMD_USB_MASS_STORAGE=y
CONFIG_DFU=y
CONFIG_DFU_OVER_USB=y
CONFIG_DFU_MMC=y
CONFIG_CMD_DFU=y
CONFIG_DM_GPIO=y
CONFIG_CMD_GPIO=y
```

What each option does:

| Config | Meaning |
|--------|---------|
| `CONFIG_USB` | Enables USB support. |
| `CONFIG_DM_USB` | Enables driver-model USB devices. |
| `CONFIG_USB_GADGET` | Lets the board act as a USB device, not only as a USB host. |
| `CONFIG_USB_GADGET_DOWNLOAD` | Common gadget support used by download-style USB commands. |
| `CONFIG_USB_GADGET_MANUFACTURER` | String shown to the host. |
| `CONFIG_USB_GADGET_VENDOR_NUM` | USB vendor ID. Use your assigned VID in a real product. Lab values are not for shipping. |
| `CONFIG_USB_GADGET_PRODUCT_NUM` | USB product ID. |
| `CONFIG_CMD_USB_MASS_STORAGE` | Adds the `ums` command. |
| `CONFIG_DFU` and `CONFIG_DFU_OVER_USB` | Enable Device Firmware Upgrade support over USB. |
| `CONFIG_DFU_MMC` | Lets DFU read and write MMC or SD storage. |
| `CONFIG_CMD_DFU` | Adds the `dfu` command. |
| `CONFIG_DM_GPIO` and `CONFIG_CMD_GPIO` | Used to read the recovery key. |

The exact USB controller symbols depend on the U-Boot tree and SoC support. If these options do not select the i.MX USB controller, inspect `drivers/usb/Kconfig` and the existing i.MX6ULL EVK defconfig.

## 24G.5  Manual UMS test

At the U-Boot prompt:

```text
pa-mini=> mmc list
pa-mini=> mmc dev 0
pa-mini=> ums 0 mmc 0
```

On the host, a new USB storage device should appear.

Use it carefully:

```sh
$ lsblk
$ sudo mount /dev/sdX1 /mnt
$ ls /mnt
$ sudo umount /mnt
```

Press `Ctrl-C` in the U-Boot console to exit UMS.

Important:

> Do not let Linux on the target and the host write the same filesystem at the same time. In this chapter Linux is not running, so UMS is safe.

## 24G.6  Manual DFU test

Set DFU targets:

```text
pa-mini=> setenv dfu_alt_info 'spl raw 0x2 0x80;u-boot raw 0x8a 0x400;boot fat 0 1'
pa-mini=> dfu 0 mmc 0 list
pa-mini=> dfu 0 mmc 0
```

On the host:

```sh
$ dfu-util -l
```

You should see named targets such as `spl`, `u-boot`, and `boot`.

The offsets above are examples. Use the storage layout from your board. Wrong raw offsets can overwrite the wrong part of the boot medium.

## 24G.7  Add recovery environment commands

In `include/configs/mx6ull_pa_mini.h`:

```c
#define PA_MINI_RECOVERY_ENV \
    "normal_boot=run mmcboot\0" \
    "recovery_ums=echo Starting USB mass storage recovery; ums 0 mmc 0\0" \
    "dfu_alt_info=spl raw 0x2 0x80;u-boot raw 0x8a 0x400;boot fat 0 1\0" \
    "recovery_dfu=echo Starting DFU recovery; dfu 0 mmc 0\0" \
    "recovery_boot=run recovery_ums\0" \
    "bootcmd=run normal_boot\0"
```

Start with:

```text
recovery_boot=run recovery_ums
```

After UMS works, switch to:

```text
recovery_boot=run recovery_dfu
```

DFU is better for factory scripts because the host sees named targets instead of a whole writable disk.

## 24G.8  Detect the recovery key in board code

Use the GPIO method from Chapter 24B. The exact GPIO name depends on your Device Tree and U-Boot version.

In `board/myorg/mx6ull_pa_mini/mx6ull_pa_mini.c`, keep the idea simple:

```c
#include <env.h>
#include <stdio.h>

static int pa_mini_recovery_key_pressed(void)
{
    /*
     * Replace this stub with a real GPIO read:
     * - get GPIO by name or phandle
     * - configure input
     * - return 1 when active-low key is pressed
     */
    return 0;
}

int board_late_init(void)
{
    if (pa_mini_recovery_key_pressed()) {
        printf("Recovery key held\n");
        env_set("bootcmd", "run recovery_boot");
    }

    return 0;
}
```

If your board already uses `board_late_init()` for temperature or identity, merge the checks:

```c
int board_late_init(void)
{
    pa_mini_apply_identity();
    pa_mini_apply_temperature_policy();

    if (pa_mini_recovery_key_pressed())
        env_set("bootcmd", "run recovery_boot");

    return 0;
}
```

Recovery key should override normal boot. It should also override network fallback boot, because recovery is how you repair boot-path mistakes.

## 24G.9  Environment-only recovery key

For a quick lab, use the `gpio` command:

```text
recovery_check=gpio input gpio1_18; gpio read recovery gpio1_18; \
    if test "${recovery}" = "0"; then \
        setenv bootcmd run recovery_boot; \
    fi
bootcmd=run recovery_check; run normal_boot
```

This is fine for learning. For production, use C board code so the behavior is less fragile and easier to review.

## 24G.10  Factory test mode

Recovery is for repair. Factory mode is for controlled production.

A simple factory command:

```text
factory_test=echo Factory test start; \
    mmc dev 0; mmc info; \
    i2c probe; \
    gpio status -a; \
    echo Factory test done
```

Trigger it with a different key or an EEPROM flag:

```text
bootcmd=if test "${factory_mode}" = "1"; then run factory_test; else run normal_boot; fi
```

A real factory test should print clear pass/fail lines. Example:

```text
TEST:MMC:PASS
TEST:I2C:PASS
TEST:GPIO:PASS
```

That lets a host script parse the serial log.

## 24G.11  Recovery safety rules

| Rule | Reason |
|------|--------|
| Require a physical action to enter recovery | Prevent accidental recovery mode in the field. |
| Print an obvious message | Technicians need to know what mode the board entered. |
| Time out if appropriate | Some products should return to normal boot after no host connects. |
| Protect raw flashing commands | DFU raw offsets can destroy the bootloader. |
| Keep SDP documented | U-Boot recovery cannot repair broken U-Boot. |
| Do not expose secrets over UMS | The host sees storage directly. |

## 24G.12  Lab

1. Enable UMS and DFU config options.
2. Boot to U-Boot and run `ums 0 mmc 0`.
3. Confirm the host sees the board as a USB disk.
4. Exit UMS with `Ctrl-C`.
5. Configure `dfu_alt_info`.
6. Run `dfu 0 mmc 0 list`, then `dfu 0 mmc 0`.
7. Confirm `dfu-util -l` sees the targets.
8. Add a recovery key check.
9. Power on with the key held and confirm U-Boot enters recovery.
10. Power on without the key and confirm normal boot.

## 24G.13  Pitfalls

- **Wrong raw offsets in DFU.** This can overwrite SPL, U-Boot, or partition tables.
- **Using lab USB IDs in a product.** Get a real VID/PID for shipping hardware.
- **No way to leave recovery.** Make sure the technician can reset or press `Ctrl-C`.
- **Recovery key bouncing.** Sample it once after GPIO is stable. Do not use an interrupt here.
- **Host auto-mount writing unexpected data.** Be careful with UMS on development machines.
- **Factory test hidden in normal boot.** Keep factory mode explicit and visible.
- **No serial log.** Recovery without logs is guesswork.

## 24G.14  Going deeper

- U-Boot `doc/usage/cmd/ums.rst`, for USB mass-storage mode.
- U-Boot `doc/usage/dfu.rst`, for DFU targets and `dfu_alt_info`.
- `cmd/dfu.c`, for the DFU command.
- `cmd/usb_mass_storage.c`, for UMS.
- NXP `uuu` scripts, for host-driven flashing flows.

---

**Previous:** [Chapter 24F: Watchdog, bootcount, and rollback](ch24F-uboot-bootcount-watchdog-rollback.md)

**Next:** [Chapter 24H: PMIC and power policy in U-Boot](ch24H-uboot-pmic-power-policy.md)
