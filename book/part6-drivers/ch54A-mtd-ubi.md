---
chapter: 54A
title: MTD / UBI for raw NAND
part: VI - Driver development (supplementary v1.2)
estimated_pages: 14
status: draft
---

# Chapter 54A: MTD / UBI for raw NAND

> **What:** the **MTD** (Memory Technology Devices) subsystem and the **UBI** (Unsorted Block Images) layer that sits on top of it. MTD partitions and exposes raw NAND/NOR flash to the kernel. UBI handles wear-levelling, bad-block management, and exposes UBI *volumes* that look like static block devices.
> **UBI:** Unsorted Block Images, a flash-management layer over raw NAND that handles wear leveling and bad blocks.
> **MTD:** Memory Technology Device, Linux's raw flash subsystem for eraseblock-based storage.
>
> **Why:** Raw NAND is common in industrial embedded, cheaper per GB than eMMC, longer-lived if managed correctly. But NAND is not a block device. It has erase blocks (about 128 KB) and pages (about 2 KB). Bad blocks appear over the device's lifetime. Erase cycles are limited. MTD/UBI is the kernel's solution.
>
> **Focus:** **the three layers**, MTD (NAND geometry), UBI (wear leveling + bad-block remapping), UBIFS (filesystem). Keep them separate in your head, each solves a different problem.
>
> **Tooling.** This chapter uses `mtd-utils` (`flash_erase`, `nandwrite`, `flashcp`, `mtdinfo`, `ubinfo`, `ubinize`, `ubiformat`).
> - **Ubuntu-base (target):** `apt install mtd-utils`
> - **Buildroot:** `BR2_PACKAGE_MTD=y`
> **Buildroot:** a configuration-driven build system that produces a complete root filesystem and related images.
> - Full per-tool reference: [Userspace tooling appendix](../part5-rootfs/appendix-tooling.md).
> **MCU bridge:** Think of the rootfs as the firmware image's file-backed runtime environment. On an MCU you link everything into flash. On Linux, programs and config live in this mounted tree.
> **rootfs:** root filesystem, the directory tree mounted at / that contains /bin, /etc, /dev, and libraries.


## 54A.1  Three layers

```
                   user-space (cp, vi, ...)
                              │
                              ▼
              ┌─────────────────────────────┐
              │   UBIFS or other UBI-aware  │  ← filesystem layer
              │   filesystem                │
              └─────────────────────────────┘
                              │
                              ▼
              ┌─────────────────────────────┐
              │            UBI               │  ← wear levelling, bad-block
              │   /dev/ubi0_0, ubi0_1, ...   │     remapping
              └─────────────────────────────┘
                              │
                              ▼
              ┌─────────────────────────────┐
              │           MTD                │  ← raw NAND access
              │   /dev/mtd0, mtd1, ...        │
              └─────────────────────────────┘
                              │
                              ▼
              ┌─────────────────────────────┐
              │  NAND chip + GPMI controller │
              └─────────────────────────────┘
```

You can use MTD without UBI for read-only partitions (kernel image). For writable storage, always use UBI.

## 54A.2  NAND on i.MX6ULL

i.MX6ULL has the **GPMI** (General Purpose Media Interface) NAND controller with BCH error correction. Connects to standard 8-bit NAND chips.

DT:

```dts
&gpmi {
    pinctrl-names = "default";
    pinctrl-0 = <&pinctrl_gpmi_nand>;
    nand-on-flash-bbt;
    fsl,no-blockmark-swap;
    status = "okay";

    partition@0 {
        label = "u-boot";
        reg = <0x0 0x400000>;          /* 4 MB */
    };
    partition@1 {
        label = "kernel";
        reg = <0x400000 0x800000>;     /* 8 MB */
    };
    partition@2 {
        label = "rootfs";
        reg = <0xc00000 0x0>;          /* rest of NAND */
    };
};
```

Each partition becomes `/dev/mtdN` (and a character-device `/dev/mtdNchar`).

## 54A.3  MTD operations

```
[root@pa-mini:~]# cat /proc/mtd
dev:    size   erasesize  name
mtd0: 00400000 00020000 "u-boot"
mtd1: 00800000 00020000 "kernel"
mtd2: 0f400000 00020000 "rootfs"

[root@pa-mini:~]# flash_erase /dev/mtd1 0 0       # erase entire kernel partition
[root@pa-mini:~]# nandwrite -p /dev/mtd1 zImage   # write kernel image
[root@pa-mini:~]# nanddump /dev/mtd1 > backup.bin # dump
```

`mtd-utils` (`flash_erase`, `flashcp`, `nandwrite`, `nanddump`, `flash_eraseall`) is the standard toolset.

## 54A.4  UBI on top

For the rootfs partition, layer UBI:

```
[root@pa-mini:~]# ubiformat /dev/mtd2 -O 2048 -s 2048   # format mtd2 for UBI
[root@pa-mini:~]# ubiattach -m 2 -d 0                    # attach as ubi0
[root@pa-mini:~]# ubimkvol /dev/ubi0 -N root -m         # max-size volume named "root"
[root@pa-mini:~]# ubimkvol /dev/ubi0 -N data -s 100MiB  # 100 MB volume "data"

[root@pa-mini:~]# cat /proc/partitions
major minor  #blocks  name
   31     0     4096  mtdblock0
   31     1     8192  mtdblock1
   31     2   249856  mtdblock2
  ...
```

UBI volumes appear as `/dev/ubi0_0` (root) and `/dev/ubi0_1` (data). To user-space they look like character devices. With a UBI-aware filesystem (UBIFS) on top, they look like filesystems.

```
[root@pa-mini:~]# mkfs.ubifs -m 2048 -e 126976 -c 1000 -o root.ubifs /path/to/staging
[root@pa-mini:~]# ubiupdatevol /dev/ubi0_0 root.ubifs
[root@pa-mini:~]# mount -t ubifs ubi0:root /mnt
```

The `-m` (min I/O size, equals NAND page size), `-e` (logical eraseblock size), and `-c` (max LEB count) come from `ubinfo /dev/ubi0`.

## 54A.5  Boot config

Kernel cmdline:

```
ubi.mtd=2 root=ubi0:root rootfstype=ubifs
```

This says: attach mtd2 as UBI, then mount the UBI volume named "root" as the rootfs.

U-Boot:
> **MCU bridge:** Think of U-Boot like a much larger boot stub plus debug monitor: it initializes hardware, loads the next image, and gives you commands before Linux starts.
> **U-Boot:** the bootloader that initializes enough hardware to load and start the Linux kernel.

```
setenv bootargs 'console=ttymxc0,115200 ubi.mtd=2 root=ubi0:root rootfstype=ubifs rw'
nand read 80800000 kernel
bootz 80800000 - 81000000
```

## 54A.6  Wear levelling

NAND erase blocks survive ~10,000–100,000 erase cycles (chip-dependent). UBI tracks per-block erase counts and migrates rarely-erased blocks toward "hot" data, averaging wear across the whole device.

```
[root@pa-mini:~]# ubinfo -a /dev/ubi0
ubi0
Volumes count:                           2
Logical eraseblock size:                 126976 bytes, 124.0 KiB
Total amount of logical eraseblocks:     1888 (239708672 bytes, 228.6 MiB)
Amount of available logical eraseblocks: 0 (0 bytes)
Maximum count of volumes                 128
Count of bad physical eraseblocks:       3
Count of reserved physical eraseblocks:  40
Current maximum erase counter value:     145
Minimum input/output unit size:          2048 bytes
Character device major/minor:            246:0
Present volumes:                         0, 1
```

Bad blocks (3 here) are remapped to reserved blocks (40 set aside). Max erase counter is 145, far below the 10k+ chip limit, so the device is healthy.

## 54A.7  UBIFS, the filesystem

UBIFS is a journalling filesystem designed for UBI. Features:
- Atomic operations (power-loss safe).
- Compression (LZO or zstd), typically 1.5–2× compression of typical embedded filesystems.
- Read/write performance ~2–3× ext4-on-eMMC for typical workloads (NAND fundamentals. Ext4 not designed for NAND).

When *not* to use:
- Random small writes, UBIFS is bad at this.
- Large databases, consider a separate ext4-on-eMMC slot if you have both.

## 54A.8  Lab

> **Storage safety:** Before any command that names /dev/sdX, run lsblk -o NAME,SIZE,MODEL,TRAN,TYPE,MOUNTPOINTS.
> Verify the removable card by size and model, unmount its partitions, and stop if the path is not the target card. Writing the wrong /dev node can destroy the host disk.


1. **Identify NAND partitions.** Boot a kernel with GPMI enabled and partitions in DT. `cat /proc/mtd`.
2. **Format and use UBI.** `ubiformat`, `ubiattach`, `ubimkvol`. Confirm `ubi0` and volumes appear.
3. **Make a UBIFS rootfs.** From your existing Buildroot output, `mkfs.ubifs`. Flash to NAND.
4. **Boot from NAND.** Configure U-Boot to load kernel + dtb from NAND, set `bootargs` for ubi root.
5. **Wear test.** Write a script that writes a 1 MB file in a loop, deleting and recreating. Run for an hour. Check max erase counter via `ubinfo`. Verify wear levelling spreads writes.
6. **Recover from bad block.** Use `nandtest` to mark a block bad. Reformat UBI. Observe it being remapped.

## 54A.9  Pitfalls

- **Wrong page/OOB size.** `ubiformat` defaults may not match your chip. Specify `-O 2048 -e 131072` explicitly to match `cat /proc/mtd` output.
- **Mounting UBIFS over ext4.** "Why does my UBIFS feel slow?", UBIFS atop a block layer that's atop NAND is double-translation. Use UBIFS directly on a UBI volume.
- **No bbt (Bad Block Table) reservation.** Pre-existing factory bad blocks become "good" in UBI's view, then fail unpredictably. Always `nand-on-flash-bbt` or `fsl,use-bbt` in DT.
- **Erasing the wrong partition.** `flash_erase /dev/mtd0` erases U-Boot. Always confirm partition number. Back up before erase.
- **Power-loss during write.** UBIFS handles this well. Ext4-on-mtdblock does not. Use UBIFS for writable partitions.
- **`ubi.mtd=` mismatch with DT partition number.** If you add/remove partitions in DT, the numbering shifts. Kernel cmdline gets stale. Lock both at the same time.

## 54A.10  Going deeper

- **`Documentation/filesystems/ubifs.rst`**: UBIFS documentation.
- **`Documentation/ABI/stable/sysfs-bus-ubi`**: UBI sysfs ABI.
> **ABI:** Application Binary Interface: the calling convention, register use, binary format, and library contract that let separately built code run together.
> **sysfs:** a kernel-generated filesystem under /sys that exposes devices, drivers, and attributes.
- **`drivers/mtd/nand/raw/gpmi-nand/`**: i.MX GPMI NAND driver.
- **`drivers/mtd/ubi/`**: UBI implementation.
- **`mtd-utils` source**: user-space tools.
- **<http://linux-mtd.infradead.org/>**: the canonical MTD/UBI website.

> Next chapter: **Chapter 54B: V4L2 + GStreamer for the CSI camera.** Capture video frames from the i.MX6ULL CSI parallel camera interface and pipe them through GStreamer for processing or display.
