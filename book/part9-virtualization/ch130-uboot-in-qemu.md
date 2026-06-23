---
chapter: 130
title: U-Boot in QEMU
part: IX - Applied virtualization and mixed-criticality systems
estimated_pages: 26
status: draft
---

# Chapter 130: U-Boot in QEMU

> **What:** build U-Boot for QEMU ARM, create a FAT boot disk, manually boot the Chapter 129 Linux system, then turn the commands into a U-Boot script.
>
> **Why:** real boards do not usually jump straight from reset into Linux. Xen also depends on firmware to load images, edit Device Tree, choose addresses, and enter the next stage correctly.
>
> **Focus:** U-Boot is the handoff engineer. It loads bytes, edits metadata, chooses bootargs, and jumps. If you cannot make U-Boot boot Linux in QEMU, Xen handoff will feel like luck.
> **U-Boot:** the bootloader used throughout the book. It initializes enough hardware to load and start the next image.
> **boot script:** a text file wrapped by `mkimage` so U-Boot can execute it with `source`.

## 130.1  What changes from Chapter 129

Chapter 129:

```text
QEMU -> Linux kernel -> initramfs -> shell
```

This chapter:

```text
QEMU -> U-Boot -> Linux kernel -> initramfs -> shell
```

The Linux kernel, DTB, and initramfs are the same artifacts. The loader changes.

That is the lesson. Boot artifacts are not tied to one loader. A loader's job is to place them in RAM and describe them correctly.

## 130.2  Prerequisites

You should already have:

```text
~/imx6ull/virt-lab/boot/zImage
~/imx6ull/virt-lab/boot/qemu-virt-arm.dtb
~/imx6ull/virt-lab/boot/initramfs.cpio.gz
```

Check:

```sh
$ cd ~/imx6ull/virt-lab
$ ls -lh boot/zImage boot/qemu-virt-arm.dtb boot/initramfs.cpio.gz
```

Also use the same cross-compiler setting:

```sh
$ export CROSS_COMPILE=arm-linux-gnueabihf-
```

or your project-local:

```sh
$ export CROSS_COMPILE=arm-none-linux-gnueabihf-
```

## 130.3  Install disk-image tools

```sh
$ sudo apt install mtools dosfstools
```

We use `mtools` because it can copy files into a FAT image without mounting it as root.

## 130.4  Build U-Boot for QEMU ARM

Get U-Boot:

```sh
$ cd ~/imx6ull/virt-lab/src
$ git clone https://source.denx.de/u-boot/u-boot.git
$ cd u-boot
```

Configure:

```sh
$ make qemu_arm_defconfig
```

Build:

```sh
$ make CROSS_COMPILE=$CROSS_COMPILE -j$(nproc)
```

Inspect:

```sh
$ file u-boot
$ file u-boot.bin
$ ls -lh u-boot u-boot.bin
```

`u-boot.bin` is the raw firmware image QEMU will load with `-bios`.

Copy it:

```sh
$ cp u-boot.bin ~/imx6ull/virt-lab/boot/u-boot-qemu-arm.bin
```

## 130.5  Create a FAT boot disk

Create a 64 MiB image:

```sh
$ cd ~/imx6ull/virt-lab
$ dd if=/dev/zero of=boot/qemu-fat.img bs=1M count=64
$ mkfs.vfat boot/qemu-fat.img
```

Create `/boot` inside it:

```sh
$ mmd -i boot/qemu-fat.img ::/boot
```

Copy artifacts:

```sh
$ mcopy -i boot/qemu-fat.img boot/zImage ::/boot/zImage
$ mcopy -i boot/qemu-fat.img boot/qemu-virt-arm.dtb ::/boot/qemu-virt-arm.dtb
$ mcopy -i boot/qemu-fat.img boot/initramfs.cpio.gz ::/boot/initramfs.cpio.gz
```

List the image:

```sh
$ mdir -i boot/qemu-fat.img ::/boot
```

If the files are not visible here, U-Boot will not see them either.

## 130.6  Start U-Boot

Run:

```sh
$ qemu-system-arm \
    -M virt \
    -cpu cortex-a15 \
    -m 256M \
    -nographic \
    -bios boot/u-boot-qemu-arm.bin \
    -drive if=none,file=boot/qemu-fat.img,format=raw,id=hd0 \
    -device virtio-blk-device,drive=hd0
```

Stop autoboot when prompted. You should reach:

```text
=>
```

If you miss the countdown, quit with `Ctrl-a x` and restart.

## 130.7  Inspect U-Boot's view of the machine

At the U-Boot prompt:

```text
=> version
=> bdinfo
=> printenv
```

Now scan virtio:

```text
=> virtio scan
=> virtio info
```

List the FAT filesystem:

```text
=> fatls virtio 0:0 /
=> fatls virtio 0:0 /boot
```

Expected:

```text
zImage
qemu-virt-arm.dtb
initramfs.cpio.gz
```

If this fails, debug storage before booting Linux.

## 130.8  Choose load addresses

We need three non-overlapping regions:

```text
0x40200000  zImage
0x43000000  DTB
0x44000000  initramfs
```

Why:

- QEMU `virt` RAM starts at `0x40000000`.
- `0x40200000` leaves room below the kernel.
- DTB and initramfs are far enough away not to collide.
- The addresses are easy to recognize in logs.

Set them:

```text
=> setenv kernel_addr_r 0x40200000
=> setenv fdt_addr_r 0x43000000
=> setenv ramdisk_addr_r 0x44000000
```

## 130.9  Load Linux artifacts by hand

Load kernel:

```text
=> fatload virtio 0:0 ${kernel_addr_r} /boot/zImage
```

Load DTB:

```text
=> fatload virtio 0:0 ${fdt_addr_r} /boot/qemu-virt-arm.dtb
```

Load initramfs and save its size:

```text
=> fatload virtio 0:0 ${ramdisk_addr_r} /boot/initramfs.cpio.gz
=> setenv ramdisk_size ${filesize}
=> echo ${ramdisk_size}
```

Inspect memory:

```text
=> iminfo ${kernel_addr_r}
```

`iminfo` may not understand `zImage` on all builds. That is fine. The important evidence is the `fatload` byte count.

## 130.10  Inspect and edit the DTB

Tell U-Boot where the DTB is:

```text
=> fdt addr ${fdt_addr_r}
=> fdt header
=> fdt print /chosen
```

If `/chosen` does not exist, create it:

```text
=> fdt mknode / chosen
```

Usually QEMU's DTB already has `/chosen`.

Set bootargs:

```text
=> setenv bootargs "console=ttyAMA0 root=/dev/ram0 rdinit=/init"
=> fdt set /chosen bootargs "${bootargs}"
=> fdt print /chosen
```

This makes the handoff visible. U-Boot will also pass bootargs to `bootz`, but printing `/chosen` now trains the habit needed for Xen.

## 130.11  Boot manually

Run:

```text
=> bootz ${kernel_addr_r} ${ramdisk_addr_r}:${ramdisk_size} ${fdt_addr_r}
```

Expected:

```text
QEMU tiny Linux is alive
/ #
```

Inside Linux:

```sh
/ # cat /proc/cmdline
/ # tr '\0' '\n' < /sys/firmware/devicetree/base/compatible
/ # poweroff -f
```

If `poweroff -f` does not exit QEMU, use `Ctrl-a x`.

## 130.12  Save a manual boot log

Run QEMU again and tee the host terminal:

```sh
$ qemu-system-arm \
    -M virt \
    -cpu cortex-a15 \
    -m 256M \
    -nographic \
    -bios boot/u-boot-qemu-arm.bin \
    -drive if=none,file=boot/qemu-fat.img,format=raw,id=hd0 \
    -device virtio-blk-device,drive=hd0 \
    2>&1 | tee logs/qemu-uboot-manual.log
```

Repeat the manual commands. This log is your proof before scripting.

## 130.13  Write a U-Boot script

Create `boot-qemu-linux.cmd` on the host:

```text
virtio scan

setenv kernel_addr_r 0x40200000
setenv fdt_addr_r 0x43000000
setenv ramdisk_addr_r 0x44000000

fatload virtio 0:0 ${kernel_addr_r} /boot/zImage
fatload virtio 0:0 ${fdt_addr_r} /boot/qemu-virt-arm.dtb
fatload virtio 0:0 ${ramdisk_addr_r} /boot/initramfs.cpio.gz
setenv ramdisk_size ${filesize}

setenv bootargs "console=ttyAMA0 root=/dev/ram0 rdinit=/init"

fdt addr ${fdt_addr_r}
fdt resize 4096
fdt set /chosen bootargs "${bootargs}"
fdt print /chosen

bootz ${kernel_addr_r} ${ramdisk_addr_r}:${ramdisk_size} ${fdt_addr_r}
```

Wrap it:

```sh
$ mkimage -A arm -T script -C none -n "QEMU Linux boot" \
    -d boot-qemu-linux.cmd boot-qemu-linux.scr
```

Copy to the FAT image:

```sh
$ mcopy -o -i boot/qemu-fat.img boot-qemu-linux.scr ::/boot/boot-qemu-linux.scr
$ mdir -i boot/qemu-fat.img ::/boot
```

## 130.14  Run the script

Start QEMU again. At U-Boot:

```text
=> virtio scan
=> fatload virtio 0:0 ${scriptaddr} /boot/boot-qemu-linux.scr
=> source ${scriptaddr}
```

Expected result: same Linux shell as manual boot.

Save:

```sh
$ qemu-system-arm ... 2>&1 | tee logs/qemu-uboot-script.log
```

## 130.15  Make autoboot use the script

For QEMU labs, we can type `source` manually. For real boards, we eventually want a repeatable boot command.

At U-Boot:

```text
=> setenv bootcmd 'virtio scan; fatload virtio 0:0 ${scriptaddr} /boot/boot-qemu-linux.scr; source ${scriptaddr}'
=> boot
```

Do not save the environment yet. QEMU's environment persistence depends on the build and storage setup. For this chapter, proving `bootcmd` works is enough.

## 130.16  Break it on purpose

### Failure 1: wrong initramfs size

Skip:

```text
setenv ramdisk_size ${filesize}
```

or set:

```text
=> setenv ramdisk_size 100
```

Expected symptom: kernel cannot unpack the archive or cannot run `/init`.

Lesson: `bootz` needs the real initramfs size.

### Failure 2: overlapping addresses

Set:

```text
=> setenv fdt_addr_r 0x40200000
```

Then load kernel and DTB. You overwrite the kernel.

Expected symptom: boot failure or strange decompressor error.

Lesson: load addresses are part of the design.

### Failure 3: wrong console

Set:

```text
=> setenv bootargs "console=ttyS0 root=/dev/ram0 rdinit=/init"
```

Expected symptom: Linux output disappears after console handoff.

Lesson: firmware can break Linux with one wrong bootarg.

### Failure 4: missing `virtio scan`

Run:

```text
=> fatls virtio 0:0 /boot
```

before `virtio scan`.

Expected symptom: U-Boot may not know the device yet.

Lesson: boot scripts must initialize the buses they use.

## 130.17  Why this matters for Xen

Xen on ARM uses the same skills with more files:

```text
load Xen
load Dom0 kernel
load Dom0 initramfs
load DTB
edit /chosen for Xen bootargs
add /chosen module nodes
jump to Xen
```

If this chapter feels mechanical, good. Chapter 134 is the same handoff pattern with a hypervisor instead of a plain kernel.

## 130.18  Lab

Deliverables:

1. `boot/u-boot-qemu-arm.bin`
2. `boot/qemu-fat.img`
3. `boot-qemu-linux.cmd`
4. `boot-qemu-linux.scr`
5. `logs/qemu-uboot-manual.log`
6. `logs/qemu-uboot-script.log`
7. Failure notes for wrong size, overlap, wrong console, and missing `virtio scan`

The lab is complete when:

- manual U-Boot commands boot Linux,
- the script boots Linux,
- `fdt print /chosen` shows the bootargs,
- you can explain every load address.

## 130.19  Pitfalls

- **Wrong disk interface.** With virtio disks, run `virtio scan`.
- **Overlapping load addresses.** Kernel, DTB, and initramfs must not collide.
- **Forgetting ramdisk size.** `bootz` needs `addr:size`.
- **Trusting default bootargs.** Print `/chosen`.
- **Scripting before manual boot works.** Manual first, script second.
- **Saving a bad environment.** Do not persist experiments until the command is proven.
- **Forgetting logs.** The serial log is the only witness once a boot goes wrong.

## 130.20  Going deeper

- U-Boot QEMU ARM documentation.
- U-Boot `bootz`, `source`, `mkimage`, `fdt`, and `virtio` command documentation.
- QEMU block-device documentation.
- Chapter 134 for the same pattern booting Xen on i.MX6ULL.
