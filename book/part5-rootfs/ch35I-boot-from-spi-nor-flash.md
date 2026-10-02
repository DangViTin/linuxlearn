---
chapter: 35I
title: Boot from SPI NOR flash
part: V - Root filesystem and user space
estimated_pages: 18
status: draft
---

# Chapter 35I: Boot from SPI NOR flash

Chapter 35D used SD/eMMC. That is the normal bulk-storage path.

SPI NOR flash is different:

- small, often 4 MB to 32 MB,
- soldered to the board,
- accessed through the MTD subsystem, not the block layer,
- erase-before-write,
- good for bootloaders, kernels, DTBs, rescue images, and small read-only root filesystems.

This chapter is about the system layout, not the flash command protocol. The low-level NOR protocol and Linux `spi-nor` driver are covered later in Chapter 64.

## 35I.1  First question: can your board boot from it?

The i.MX6ULL Boot ROM can boot from SPI-NOR and QSPI-NOR when the boot pins select that mode and the board wiring matches the ROM boot path.

That last sentence matters.

Some development boards expose only SD, eMMC, NAND, and USB boot modes in their DIP switches. They may still have an SPI flash connected to ECSPI for storage, but the Boot ROM may not be strapped to boot from it on that board.

So there are two cases:

| Case | What works |
|------|------------|
| Board boot pins support SPI/QSPI NOR | Boot ROM loads U-Boot directly from SPI flash |
| Board has SPI flash but no SPI boot strap | U-Boot/Linux can use the flash after boot, but ROM boot must still come from SD/eMMC/NAND/USB |

This chapter is most useful for a custom product board or a dev board whose boot switches expose SPI/QSPI boot.

## 35I.2  SPI NOR is not eMMC

Do not use `fdisk` on SPI NOR.

eMMC and SD are block devices:

```text
/dev/mmcblk0
/dev/mmcblk0p1
/dev/mmcblk0p2
```

SPI NOR is an MTD device:

```text
/dev/mtd0        raw character device
/dev/mtdblock0   block wrapper, useful only for read-only filesystems
```

The partition table is usually not stored on the flash itself. It is described by:

- Device Tree fixed partitions, preferred,
- U-Boot `mtdparts`,
- kernel command line `mtdparts=...`.

For a product, use Device Tree fixed partitions so Linux and U-Boot agree.

## 35I.3  A realistic 16 MB layout

For a 16 MB SPI NOR, a practical layout is tight:

```text
Offset      Size      Name        Content
0x000000    1 MB      bootloader  U-Boot image, or SPL + U-Boot
0x100000    128 KB    env         U-Boot environment
0x120000    128 KB    env-r       Redundant U-Boot environment
0x140000    6 MB      kernel      zImage
0x740000    128 KB    dtb         board DTB
0x760000    8 MB      rootfs      SquashFS root filesystem
0xF60000    640 KB    data        tiny config/log area, optional
```

This is not a universal layout. It is a teaching layout.

The key rules:

- Align partitions to erase-block boundaries.
- Leave room for kernel growth.
- Keep rootfs read-only and compressed.
- Do not put large logs in SPI NOR.
- Keep U-Boot environment away from kernel/rootfs partitions.

For a 32 MB NOR, give rootfs and recovery more room. For a 4 MB NOR, store only bootloader + recovery loader, and keep rootfs elsewhere.

## 35I.4  Device Tree fixed partitions

For QSPI NOR, your board DTS will contain a flash node under the QSPI controller. Exact controller node names vary by kernel and board.

The important part is the `fixed-partitions` block:

```dts
flash@0 {
    compatible = "jedec,spi-nor";
    reg = <0>;
    spi-max-frequency = <50000000>;
    #address-cells = <1>;
    #size-cells = <1>;

    partitions {
        compatible = "fixed-partitions";
        #address-cells = <1>;
        #size-cells = <1>;

        bootloader@0 {
            label = "bootloader";
            reg = <0x000000 0x100000>;
            read-only;
        };

        env@100000 {
            label = "env";
            reg = <0x100000 0x020000>;
        };

        env-redundant@120000 {
            label = "env-r";
            reg = <0x120000 0x020000>;
        };

        kernel@140000 {
            label = "kernel";
            reg = <0x140000 0x600000>;
        };

        dtb@740000 {
            label = "dtb";
            reg = <0x740000 0x020000>;
        };

        rootfs@760000 {
            label = "rootfs";
            reg = <0x760000 0x800000>;
        };

        data@f60000 {
            label = "data";
            reg = <0xF60000 0x0A0000>;
        };
    };
};
```

After Linux boots:

```sh
[root@pa-mini:~]# cat /proc/mtd
dev:    size   erasesize  name
mtd0: 00100000 00010000 "bootloader"
mtd1: 00020000 00010000 "env"
mtd2: 00020000 00010000 "env-r"
mtd3: 00600000 00010000 "kernel"
mtd4: 00020000 00010000 "dtb"
mtd5: 00800000 00010000 "rootfs"
mtd6: 000a0000 00010000 "data"
```

The partition numbers come from the DT order.

## 35I.5  Kernel config

The kernel needs SPI NOR, MTD, and the root filesystem format.

Example fragment:

```text
CONFIG_MTD=y
CONFIG_MTD_BLOCK=y
CONFIG_MTD_SPI_NOR=y
CONFIG_SPI=y
CONFIG_SPI_IMX=y
CONFIG_SPI_FSL_QUADSPI=y
CONFIG_SQUASHFS=y
CONFIG_SQUASHFS_XZ=y
```

Use the controller option that matches your hardware:

| Hardware path | Likely kernel area |
|---------------|--------------------|
| ECSPI + SPI NOR | SPI controller + `spi-nor` |
| QSPI NOR | QSPI controller + `spi-nor` |

If you store the rootfs in SPI NOR, build the flash driver and SquashFS support into the kernel, not as modules. The kernel needs them before rootfs is mounted.

## 35I.6  Buildroot rootfs for SPI NOR

For a small NOR rootfs, use SquashFS:

```text
Filesystem images  --->
  [*] squashfs root filesystem
      Compression method = xz
```

Useful config symbols:

```text
BR2_TARGET_ROOTFS_SQUASHFS=y
BR2_TARGET_ROOTFS_SQUASHFS_XZ=y
BR2_PACKAGE_MTD=y
```

Output:

```text
output/images/rootfs.squashfs
```

A SquashFS rootfs is read-only. That is a feature here. Put writable data somewhere else:

- small JFFS2 partition in the same SPI NOR,
- external eMMC/SD `/data`,
- RAM-only tmpfs for stateless products.

For SPI NOR, avoid ext4 on `/dev/mtdblockN`. It is not a real block device with wear leveling.

## 35I.7  Flash from U-Boot

Load images over TFTP, then write them to SPI NOR.

Probe flash:

```text
=> sf probe
```

Write kernel:

```text
=> tftp 0x82000000 zImage
=> sf update 0x82000000 0x140000 ${filesize}
```

Write DTB:

```text
=> tftp 0x82000000 imx6ull-your-board.dtb
=> sf update 0x82000000 0x740000 ${filesize}
```

Write rootfs:

```text
=> tftp 0x82000000 rootfs.squashfs
=> sf update 0x82000000 0x760000 ${filesize}
```

`sf update` erases the needed sectors and writes the new data. If your U-Boot does not have `sf update`, use `sf erase` followed by `sf write`, but make sure erase length is sector-aligned.

Be careful with the bootloader region. During bring-up, keep a USB SDP or SD-card recovery path available before overwriting the flash region that contains U-Boot.

## 35I.8  Boot from SPI NOR

In U-Boot:

```text
=> sf probe
=> sf read 0x82000000 0x140000 0x600000
=> sf read 0x83000000 0x740000 0x020000
=> setenv bootargs 'console=ttymxc0,115200 earlycon root=/dev/mtdblock5 rootfstype=squashfs ro'
=> bootz 0x82000000 - 0x83000000
```

Save:

```text
=> setenv bootargs 'console=ttymxc0,115200 earlycon root=/dev/mtdblock5 rootfstype=squashfs ro'
=> setenv bootcmd 'sf probe && sf read 0x82000000 0x140000 0x600000 && sf read 0x83000000 0x740000 0x020000 && bootz 0x82000000 - 0x83000000'
=> saveenv
```

Why `mtdblock5`? In the example DT, the `rootfs` partition is the sixth partition, so it becomes `mtd5`, and the block wrapper is `/dev/mtdblock5`.

This is why fixed partition order matters.

## 35I.9  Kernel + DTB in SPI, rootfs elsewhere

A common product compromise:

```text
SPI NOR:  U-Boot, env, kernel, DTB, recovery initramfs
eMMC:     main rootfs, data
```

Bootargs:

```text
root=LABEL=rootfs rw rootwait
```

Boot flow:

```text
Boot ROM -> U-Boot from SPI NOR
U-Boot -> kernel + DTB from SPI NOR
Kernel -> rootfs from eMMC
```

This gives fast, soldered boot firmware, while leaving the large rootfs on eMMC.

For many i.MX6ULL products, this is more practical than putting the whole OS in a 16 MB NOR.

## 35I.10  Writable data in SPI NOR

Small writable data can live in SPI NOR, but treat it carefully.

Options:

| Option | Use |
|--------|-----|
| U-Boot env | Boot variables only |
| JFFS2 | Tiny writable config partition |
| Raw MTD | Fixed records, counters, calibration |
| eMMC `/data` | Better for logs and databases |

Do not write logs continuously to SPI NOR. NOR has erase-cycle limits, and log traffic can wear a small partition quickly.

## 35I.11  Lab

1. Add fixed partitions for your SPI NOR in the board DTS.
2. Enable MTD, SPI NOR, and SquashFS in the kernel.
3. Build `rootfs.squashfs` with Buildroot.
4. From U-Boot, `sf probe`.
5. Flash `zImage`, DTB, and `rootfs.squashfs` to their offsets.
6. Boot with `root=/dev/mtdblockN rootfstype=squashfs ro`.
7. Confirm:

```sh
[root@pa-mini:~]# cat /proc/mtd
[root@pa-mini:~]# findmnt /
[root@pa-mini:~]# mount | head -1
```

## 35I.12  Pitfalls

- **Board can use SPI flash, but ROM cannot boot from it.** Check boot straps, not only the schematic.
- **Wrong IVT offset.** Boot ROM image placement differs between SPI-NOR and QSPI-NOR. Chapter 7 explains the ROM offsets. Verify against your SoC and U-Boot image format.
- **Rootfs too large.** A normal glibc rootfs will not fit in 16 MB. Use BusyBox + SquashFS or keep rootfs on eMMC.
- **Using ext4 on MTD.** MTD is not a normal block device. Use SquashFS for read-only or JFFS2 for tiny writable areas.
- **Forgetting to erase before write.** NOR can change bits from 1 to 0 by programming, but needs erase to return 0 to 1.
- **Overlapping U-Boot env.** If rootfs overlaps the env sector, `saveenv` corrupts the filesystem.
- **Saving environment every boot.** Each `saveenv` erases a sector. Do not write U-Boot env as a normal boot counter unless you designed for wear.

---

Previous chapter: [Chapter 35D - Bootable SD and eMMC image layout](ch35D-bootable-sd-emmc-image.md)

Next chapter: [Chapter 35E - Buildroot product board directory](ch35E-buildroot-product-board-directory.md)
