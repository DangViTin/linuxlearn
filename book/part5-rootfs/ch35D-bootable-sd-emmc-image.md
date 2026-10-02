---
chapter: 35D
title: Bootable SD and eMMC image layout
part: V - Root filesystem and user space
estimated_pages: 18
status: draft
---

# Chapter 35D: Bootable SD and eMMC image layout

Chapters 31 and 35 got a root filesystem running over NFS. NFS is perfect for development, but a product needs local storage.

This chapter builds the storage layout you will use again and again:

```text
SD/eMMC
  p1  FAT32   boot files: zImage, DTB, optional initramfs
  p2  ext4    root filesystem
  p3  ext4    persistent data
```

The exact partition sizes change per product. The pattern does not.

## 35D.1  Why split boot, rootfs, and data?

Do not put everything in one writable ext4 partition.

| Partition | Mounted at | Purpose |
|-----------|------------|---------|
| Boot | `/boot` or not mounted | Files U-Boot reads: kernel, DTB, initramfs |
| Rootfs | `/` | Operating system files |
| Data | `/data` | App config, logs, databases, user files |

This gives you clean boundaries:

- You can replace the rootfs without erasing user data.
- You can mount rootfs read-only later.
- You can factory reset by clearing `/data` or the overlay partition.
- You can update boot files separately from application data.

## 35D.2  Use labels, not guessed device names

On one board, the SD card may appear as `/dev/mmcblk0`. On another boot path, eMMC may be `/dev/mmcblk1`.

Use filesystem labels:

```text
root=LABEL=rootfs rootwait
```

Then the kernel searches for the partition labeled `rootfs`.

Create labels when formatting:

```sh
$ sudo mkfs.vfat -F 32 -n BOOT /dev/sdb1
$ sudo mkfs.ext4 -L rootfs /dev/sdb2
$ sudo mkfs.ext4 -L data /dev/sdb3
```

Labels make bootargs easier to read and harder to break.

## 35D.3  Manual image build

Manual partitioning is useful once. It teaches what the image builder later automates.

First, identify the target card:

```sh
$ lsblk -o NAME,SIZE,MODEL,TRAN,TYPE,MOUNTPOINTS
```

Assume the SD card is `/dev/sdb`. Replace this with the correct device on your host.

Create partitions:

```sh
$ sudo parted /dev/sdb --script \
      mklabel msdos \
      mkpart primary fat32 1MiB 129MiB \
      set 1 boot on \
      mkpart primary ext4 129MiB 641MiB \
      mkpart primary ext4 641MiB 100%
```

Format:

```sh
$ sudo mkfs.vfat -F 32 -n BOOT /dev/sdb1
$ sudo mkfs.ext4 -L rootfs /dev/sdb2
$ sudo mkfs.ext4 -L data /dev/sdb3
```

Mount:

```sh
$ mkdir -p /tmp/imx6ull-card/boot /tmp/imx6ull-card/rootfs /tmp/imx6ull-card/data
$ sudo mount /dev/sdb1 /tmp/imx6ull-card/boot
$ sudo mount /dev/sdb2 /tmp/imx6ull-card/rootfs
$ sudo mount /dev/sdb3 /tmp/imx6ull-card/data
```

Copy boot files:

```sh
$ sudo cp ~/imx6ull/src/linux-v6.6/arch/arm/boot/zImage /tmp/imx6ull-card/boot/
$ sudo cp ~/imx6ull/src/linux-v6.6/arch/arm/boot/dts/nxp/imx/imx6ull-your-board.dtb \
      /tmp/imx6ull-card/boot/
```

Install the rootfs:

```sh
$ sudo tar -xf ~/imx6ull/buildroot/output/images/rootfs.tar \
      -C /tmp/imx6ull-card/rootfs
```

Create data directories:

```sh
$ sudo mkdir -p /tmp/imx6ull-card/data/myapp /tmp/imx6ull-card/data/log
```

Unmount:

```sh
$ sync
$ sudo umount /tmp/imx6ull-card/boot
$ sudo umount /tmp/imx6ull-card/rootfs
$ sudo umount /tmp/imx6ull-card/data
```

Now the card has a boot partition, rootfs partition, and data partition.

## 35D.4  Bootargs for local rootfs

In U-Boot:

```text
=> setenv bootargs 'console=ttymxc0,115200 earlycon root=LABEL=rootfs rw rootwait'
=> fatload mmc 0:1 0x82000000 zImage
=> fatload mmc 0:1 0x83000000 imx6ull-your-board.dtb
=> bootz 0x82000000 - 0x83000000
```

Save it:

```text
=> setenv bootcmd 'fatload mmc 0:1 0x82000000 zImage && fatload mmc 0:1 0x83000000 imx6ull-your-board.dtb && bootz 0x82000000 - 0x83000000'
=> saveenv
```

Use `&&` so a failed load stops the boot.

## 35D.5  Mount `/data`

In the rootfs, add this to `/etc/fstab`:

```text
LABEL=data  /data  ext4  defaults,noatime  0  2
```

Create the mountpoint:

```sh
$ sudo mkdir -p /tmp/imx6ull-card/rootfs/data
```

On target:

```sh
[root@pa-mini:~]# mount /data
[root@pa-mini:~]# touch /data/test
[root@pa-mini:~]# reboot
[root@pa-mini:~]# ls /data/test
```

If the file survives, persistent data works.

## 35D.6  Automate with genimage

Manual partitioning is not release engineering. For repeatable images, use `genimage`.

Buildroot can run `genimage` as a post-image step. The core file is `genimage.cfg`:

```text
image sdcard.img {
  hdimage {
  }

  partition boot {
    partition-type = 0x0C
    bootable = true
    image = "boot.vfat"
    size = 128M
  }

  partition rootfs {
    partition-type = 0x83
    image = "rootfs.ext4"
    size = 512M
  }

  partition data {
    partition-type = 0x83
    size = 512M
  }
}

image boot.vfat {
  vfat {
    files = {
      "zImage",
      "imx6ull-your-board.dtb"
    }
  }
  size = 128M
}
```

The result is one flashable file:

```sh
$ sudo dd if=sdcard.img of=/dev/sdb bs=4M conv=fsync status=progress
```

Buildroot board directories usually keep this under:

```text
board/myorg/myboard/genimage.cfg
```

Chapter 35E later uses that structure.

## 35D.7  Verify the card

Before booting, check:

```sh
$ lsblk -f /dev/sdb
NAME   FSTYPE LABEL  SIZE
sdb
├─sdb1 vfat   BOOT   128M
├─sdb2 ext4   rootfs 512M
└─sdb3 ext4   data   ...
```

After boot:

```sh
[root@pa-mini:~]# cat /proc/cmdline
[root@pa-mini:~]# findmnt /
[root@pa-mini:~]# findmnt /data
[root@pa-mini:~]# df -h
```

You want:

- `/` mounted from `LABEL=rootfs`,
- `/data` mounted from `LABEL=data`,
- boot files loaded from the FAT partition.

## 35D.8  Lab

1. Partition an SD card with boot, rootfs, and data partitions.
2. Boot using `root=LABEL=rootfs`.
3. Mount `/data` from `LABEL=data`.
4. Create `/data/persistent.txt`, reboot, and verify it survives.
5. Change U-Boot `bootcmd` to use `&&`.
6. Break the DTB filename on purpose and confirm U-Boot stops before `bootz`.

## 35D.9  Pitfalls

- **Writing the wrong `/dev/sdX`.** Always run `lsblk` before `dd`, `parted`, or `mkfs`.
- **Using `/dev/mmcblk0p2` in bootargs.** It may change when boot source changes. Prefer `LABEL=` or `PARTUUID=`.
- **Forgetting `rootwait`.** MMC may not be ready when the kernel tries to mount root.
- **Putting mutable app data in `/etc`.** Use `/data` for runtime data.
- **Mounting `/data` too late.** If your app starts before `/data` is mounted, it may create files on the rootfs instead.

---

Previous chapter: [Chapter 35 - Buildroot](ch35-buildroot.md)

Next chapter: [Chapter 35I - Boot from SPI NOR flash](ch35I-boot-from-spi-nor-flash.md)
