---
chapter: 24F
title: Watchdog, bootcount, and rollback in U-Boot
part: III - U-Boot, deeply
estimated_pages: 20
status: draft
---

# Chapter 24F: Watchdog, bootcount, and rollback in U-Boot

> **What:** add a simple A/B boot rollback policy to U-Boot. If Linux fails to boot successfully after an update, the board returns to the previous slot.
>
> **Why:** field updates fail. Power can drop during first boot, a kernel can panic, a rootfs can be broken, or a driver can hang. A product must recover without a technician connecting a serial cable.
>
> **Result:** U-Boot tries slot B after an update. If Linux does not mark slot B good within the allowed boot attempts, U-Boot falls back to slot A.
>
> **Focus:** U-Boot decides which slot to boot. Linux decides whether the boot was successful.

This chapter is not a full OTA system. It is the small bootloader part that every real OTA system needs.

## 24F.1  The problem in one timeline

Without rollback:

```text
1. Product runs good slot A.
2. Update writes bad slot B.
3. U-Boot boots slot B.
4. Linux panics before network comes up.
5. Product is stuck forever.
```

With rollback:

```text
1. Product runs good slot A.
2. Update writes candidate slot B.
3. U-Boot boots slot B and increments bootcount.
4. Linux fails before it marks B good.
5. Watchdog resets the board.
6. U-Boot sees bootcount exceeded bootlimit.
7. U-Boot boots known-good slot A.
```

The idea is simple:

| State | Owner |
|-------|-------|
| Which slot is active | U-Boot environment or boot metadata |
| How many failed attempts happened | U-Boot bootcount storage |
| Whether Linux booted successfully | Linux user space service |
| Hardware reset if Linux hangs | Watchdog |

## 24F.2  Terms

| Term | Meaning |
|------|---------|
| Slot A | One complete kernel plus rootfs set. |
| Slot B | Another complete kernel plus rootfs set. |
| Active slot | The slot U-Boot will boot now. |
| Good slot | A slot that Linux has already proven can boot far enough to run the health service. |
| Candidate slot | A newly updated slot that has not yet proven itself. |
| Bootcount | Counter incremented across failed boot attempts. |
| Bootlimit | Maximum attempts before U-Boot runs `altbootcmd`. |
| `altbootcmd` | Alternate command used when bootcount exceeds bootlimit. |

## 24F.3  Storage layout for the lab

Use one SD card or eMMC with four partitions:

| Partition | Name | Content |
|-----------|------|---------|
| `mmc 0:1` | `boot_a` | `zImage`, `imx6ull-pa-mini.dtb` for slot A |
| `mmc 0:2` | `rootfs_a` | root filesystem A |
| `mmc 0:3` | `boot_b` | `zImage`, `imx6ull-pa-mini.dtb` for slot B |
| `mmc 0:4` | `rootfs_b` | root filesystem B |

For a first lab, the two slots can contain the same kernel and rootfs. The rollback mechanism is what we are testing.

## 24F.4  Files changed in this chapter

| File | What changes |
|------|--------------|
| `configs/mx6ull_pa_mini_defconfig` | Enable bootcount, watchdog, filesystem loading, and environment storage. |
| `arch/arm/dts/imx6ull-pa-mini.dts` | Enable the watchdog node if it is not already enabled. |
| `include/configs/mx6ull_pa_mini.h` | Add A/B boot environment commands. |
| Linux rootfs | Add a small service that marks the active slot good after boot. |

## 24F.5  Enable the U-Boot features

Add these to `configs/mx6ull_pa_mini_defconfig`:

```text
CONFIG_BOOTCOUNT_LIMIT=y
CONFIG_BOOTCOUNT_ENV=y
CONFIG_WDT=y
CONFIG_WDT_IMX2=y
CONFIG_CMD_WDT=y
CONFIG_CMD_EXT4=y
CONFIG_FS_EXT4=y
CONFIG_CMD_FAT=y
CONFIG_FS_FAT=y
CONFIG_CMD_SETEXPR=y
```

What each option does:

| Config | Meaning |
|--------|---------|
| `CONFIG_BOOTCOUNT_LIMIT` | Enables the bootcount and bootlimit logic. |
| `CONFIG_BOOTCOUNT_ENV` | Stores bootcount in the U-Boot environment. Good for teaching. For production, prefer a more robust backend. |
| `CONFIG_WDT` | Enables watchdog driver model support. |
| `CONFIG_WDT_IMX2` | Enables the i.MX watchdog driver in many U-Boot trees. Check `drivers/watchdog/Kconfig` if your tree uses a different symbol. |
| `CONFIG_CMD_WDT` | Adds the `wdt` command for manual watchdog tests. |
| `CONFIG_CMD_EXT4` and `CONFIG_FS_EXT4` | Allow loading files from ext4 partitions. |
| `CONFIG_CMD_FAT` and `CONFIG_FS_FAT` | Allow loading files from FAT partitions. |
| `CONFIG_CMD_SETEXPR` | Useful for small environment logic. |

For real products, consider a bootcount backend outside the normal environment. The environment can be corrupted if power is cut during `saveenv`.

## 24F.6  Manual bootcount test

At the U-Boot prompt:

```text
pa-mini=> setenv bootlimit 3
pa-mini=> setenv bootcount 0
pa-mini=> setenv upgrade_available 1
pa-mini=> setenv altbootcmd 'echo rollback path'
pa-mini=> saveenv
pa-mini=> reset
```

When `upgrade_available` is non-zero, U-Boot updates `bootcount` on each reset. When `bootcount` exceeds `bootlimit`, U-Boot runs `altbootcmd` instead of `bootcmd`.

Check:

```text
pa-mini=> printenv bootcount bootlimit altbootcmd
```

This proves the mechanism before we add A/B slots.

## 24F.7  A/B environment variables

Add this to `include/configs/mx6ull_pa_mini.h`:

```c
#define PA_MINI_AB_ENV \
    "active_slot=A\0" \
    "upgrade_available=0\0" \
    "bootlimit=3\0" \
    "kernel_addr_r=0x82000000\0" \
    "fdt_addr_r=0x83000000\0" \
    "bootpart_a=0:1\0" \
    "bootpart_b=0:3\0" \
    "root_a=/dev/mmcblk0p2\0" \
    "root_b=/dev/mmcblk0p4\0" \
    "select_slot=if test \"${active_slot}\" = \"B\"; then " \
        "setenv bootpart ${bootpart_b}; " \
        "setenv rootpart ${root_b}; " \
    "else " \
        "setenv active_slot A; " \
        "setenv bootpart ${bootpart_a}; " \
        "setenv rootpart ${root_a}; " \
    "fi\0" \
    "boot_selected=run select_slot; " \
        "setenv bootargs console=ttymxc0,115200 root=${rootpart} rw rootwait " \
            "rauc.slot=${active_slot}; " \
        "load mmc ${bootpart} ${kernel_addr_r} zImage; " \
        "load mmc ${bootpart} ${fdt_addr_r} imx6ull-pa-mini.dtb; " \
        "bootz ${kernel_addr_r} - ${fdt_addr_r}\0" \
    "rollback=echo Rolling back to slot A; " \
        "setenv active_slot A; " \
        "setenv upgrade_available 0; " \
        "setenv bootcount 0; " \
        "saveenv; " \
        "run boot_selected\0" \
    "bootcmd=run boot_selected\0" \
    "altbootcmd=run rollback\0"
```

Then include it in `CFG_EXTRA_ENV_SETTINGS`.

The important variables:

| Variable | Meaning |
|----------|---------|
| `active_slot` | Slot U-Boot will boot. |
| `upgrade_available` | Non-zero means the active slot is a candidate update. |
| `bootcount` | Failed boot attempt counter. |
| `bootlimit` | Maximum candidate boot attempts. |
| `altbootcmd` | Rollback command. |

The `rauc.slot=${active_slot}` token is just an example of passing slot identity to Linux. You can name it `boot.slot=` or anything your user-space service understands.

## 24F.8  Mark slot B as candidate

Pretend the updater wrote slot B successfully:

```text
pa-mini=> setenv active_slot B
pa-mini=> setenv upgrade_available 1
pa-mini=> setenv bootcount 0
pa-mini=> saveenv
pa-mini=> reset
```

U-Boot now tries B.

If Linux never marks B good, repeated resets eventually run:

```text
Rolling back to slot A
```

## 24F.9  Linux marks the boot good

U-Boot can try a candidate slot, but Linux must decide whether the boot succeeded.

For the lab, add this script in the rootfs:

```sh
#!/bin/sh

# /usr/sbin/mark-boot-good

fw_setenv upgrade_available 0
fw_setenv bootcount 0
```

Call it late in boot, after the services you care about are running.

For a simple init script:

```sh
#!/bin/sh

case "$1" in
  start)
    /usr/sbin/mark-boot-good
    ;;
esac
```

Do not mark good too early. If the network daemon, UI, or main product service crashes after this point, U-Boot will think the update is good.

## 24F.10  Watchdog role

Bootcount handles repeated resets. The watchdog creates the reset when Linux hangs.

Manual U-Boot test:

```text
pa-mini=> wdt list
pa-mini=> wdt dev 0
pa-mini=> wdt start 10000
pa-mini=> sleep 20
```

If the watchdog is running and not serviced, the board resets.

In production:

1. U-Boot may start the watchdog.
2. U-Boot boots Linux.
3. Linux watchdog driver takes over.
4. A user-space watchdog daemon keeps feeding it only while the system is healthy.

Do not feed the watchdog blindly. Feeding it should mean the product is healthy enough to keep running.

## 24F.11  Environment storage warning

The lab uses:

```text
CONFIG_BOOTCOUNT_ENV=y
```

This is easy to understand, but it has two weaknesses:

- It writes the environment often.
- A power cut during environment write can corrupt it.

For real products, prefer one of these:

| Backend | Why |
|---------|-----|
| Bootcount in RTC or SNVS | Small persistent counter, separate from main storage. |
| Bootcount file on FAT or ext | Easier with partitioned storage, but still needs power-cut design. |
| Dedicated boot metadata partition | Common in OTA systems. Lets you make updates atomic. |
| Redundant environment | Better than one environment copy, but still design carefully. |

This chapter teaches the logic first. Production storage policy comes later in the field-update chapters.

## 24F.12  Lab

1. Enable bootcount and watchdog configs.
2. Confirm `bootcount`, `bootlimit`, and `altbootcmd` work with a simple echo command.
3. Add A/B environment variables.
4. Boot slot A normally.
5. Set slot B as candidate with `upgrade_available=1`.
6. Simulate failure by resetting before Linux marks good.
7. Confirm U-Boot rolls back to slot A.
8. Add `mark-boot-good` in Linux and confirm slot B becomes good.
9. Start the watchdog and prove it resets the board when not serviced.

## 24F.13  Pitfalls

- **Marking good too early.** Wait until the real product service is healthy.
- **No watchdog.** If Linux hangs forever, bootcount never gets another chance.
- **No rollback command.** If `altbootcmd` is missing, U-Boot may stop at the prompt instead of recovering.
- **Saving environment too often.** Flash and eMMC have finite write endurance.
- **Booting the wrong rootfs for the kernel.** Keep kernel, DTB, and rootfs slot mapping together.
- **No rescue slot.** A/B needs at least one known-good path.
- **Testing only the success path.** The whole point is failure behavior. Break it on purpose.

## 24F.14  Going deeper

- U-Boot bootcount documentation, for `CONFIG_BOOTCOUNT_LIMIT`, `bootcount`, `bootlimit`, and `altbootcmd`.
- `common/autoboot.c`, for where bootcount affects autoboot.
- `drivers/watchdog/`, for watchdog drivers.
- Linux `watchdog` subsystem and user-space watchdog daemons.
- Part VIII field-update chapters, for RAUC, SWUpdate, Mender, and production A/B update design.

---

**Previous:** [Chapter 24E: Multi-variant FIT images and DT overlays](ch24E-multi-variant-fit.md)

**Next:** [Chapter 24G: Factory and recovery modes in U-Boot](ch24G-uboot-factory-recovery-usb.md)
