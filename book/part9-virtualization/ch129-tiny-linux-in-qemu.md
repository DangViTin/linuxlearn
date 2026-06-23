---
chapter: 129
title: Build and boot tiny Linux in QEMU
part: IX - Applied virtualization and mixed-criticality systems
estimated_pages: 30
status: draft
---

# Chapter 129: Build and boot tiny Linux in QEMU

> **What:** build a 32-bit ARM Linux kernel, build a static BusyBox initramfs, generate a QEMU Device Tree, and boot to a shell in QEMU.
>
> **Why:** before Xen, Dom0, DomU, or Jailhouse enter the story, the reader must understand a plain ARM Linux boot with no hidden board support package. Kernel, DTB, initramfs, command line, console. Those are the pieces.
>
> **Focus:** QEMU is our clean-room board. We will build every input explicitly, boot it, inspect it from inside Linux, then break each input on purpose.
> **QEMU:** a machine emulator. Here it creates a fake ARM board with RAM, CPU, UART, timer, interrupt controller, and virtio devices.
> **DTB:** Device Tree Blob, the binary hardware description passed to the Linux kernel.
> **initramfs:** a cpio archive the kernel unpacks into RAM and runs as the first root filesystem.

## 129.1  What we are about to build

The boot path is:

```text
qemu-system-arm
  -> creates an ARMv7-A "virt" board
  -> loads zImage into guest RAM
  -> loads qemu-virt-arm.dtb into guest RAM
  -> loads initramfs.cpio.gz into guest RAM
  -> starts the kernel
Linux
  -> reads the DTB
  -> initializes the PL011 UART
  -> unpacks the initramfs
  -> runs /init
/init
  -> mounts /proc, /sys, /dev
  -> gives us a BusyBox shell
```

No U-Boot. No Xen. No Dom0. No virtual disks.

We remove those layers on purpose. If this chapter fails, the failure is in one of four inputs:

- kernel image,
- DTB,
- initramfs,
- command line.

That is the mental model we want before Chapter 130 adds U-Boot and Chapter 132 adds Xen.

## 129.2  Host packages

On Ubuntu or Debian:

```sh
$ sudo apt update
$ sudo apt install build-essential git bc bison flex libssl-dev \
    gcc-arm-linux-gnueabihf qemu-system-arm device-tree-compiler \
    cpio gzip xz-utils rsync file wget
```

Check the tools:

```sh
$ arm-linux-gnueabihf-gcc --version | head -1
$ qemu-system-arm --version | head -1
$ dtc --version
```

This chapter uses Debian/Ubuntu's `arm-linux-gnueabihf-` toolchain name. If you prefer the book's project-local Arm GNU toolchain, set:

```sh
$ export CROSS_COMPILE=arm-none-linux-gnueabihf-
```

Otherwise:

```sh
$ export CROSS_COMPILE=arm-linux-gnueabihf-
```

Everything below uses `$CROSS_COMPILE`.

## 129.3  Workspace

```sh
$ mkdir -p ~/imx6ull/virt-lab/{src,build,rootfs,boot,logs}
$ cd ~/imx6ull/virt-lab
```

By the end, the important files will be:

```text
boot/
  zImage
  qemu-virt-arm.dtb
  qemu-virt-arm.dts
  initramfs.cpio.gz
logs/
  qemu-linux-direct.log
  qemu-linux-wrong-console.log
  qemu-linux-no-initramfs.log
  qemu-linux-no-init.log
```

## 129.4  Build BusyBox first

We need a user space. The smallest useful one is a static BusyBox.

Download:

```sh
$ cd ~/imx6ull/virt-lab/src
$ wget https://busybox.net/downloads/busybox-1.36.1.tar.bz2
$ tar xf busybox-1.36.1.tar.bz2
$ cd busybox-1.36.1
```

Configure:

```sh
$ make ARCH=arm CROSS_COMPILE=$CROSS_COMPILE defconfig
```

Enable static linking:

```sh
$ scripts/config -e STATIC
$ make ARCH=arm CROSS_COMPILE=$CROSS_COMPILE olddefconfig
```

Build:

```sh
$ make ARCH=arm CROSS_COMPILE=$CROSS_COMPILE -j$(nproc)
```

Inspect the result:

```sh
$ file busybox
busybox: ELF 32-bit LSB executable, ARM, EABI5, statically linked, ...

$ ls -lh busybox
```

The important words are **ARM** and **statically linked**. If `file` says x86-64, you built for the host by accident. If it says dynamically linked, the initramfs will need shared libraries, which we are deliberately avoiding.

## 129.5  Install BusyBox into the rootfs tree

Use BusyBox's installer. Do not create every applet symlink by hand.

```sh
$ rm -rf ~/imx6ull/virt-lab/rootfs/*
$ make ARCH=arm CROSS_COMPILE=$CROSS_COMPILE \
    CONFIG_PREFIX=~/imx6ull/virt-lab/rootfs install
```

Check:

```sh
$ cd ~/imx6ull/virt-lab/rootfs
$ ls
bin  linuxrc  sbin  usr

$ file bin/busybox
bin/busybox: ELF 32-bit LSB executable, ARM, EABI5, statically linked, ...

$ ls -l bin/sh
```

BusyBox should have installed `bin/sh` as a symlink to `busybox`.

Now add the directories Linux user space expects:

```sh
$ mkdir -p proc sys dev tmp run mnt root etc
$ chmod 1777 tmp
```

## 129.6  Write `/init`

The kernel's first user-space process will be `/init` because we will pass `rdinit=/init`.

Create it:

```sh
$ cat > init <<'EOF'
#!/bin/sh

mount -t proc none /proc
mount -t sysfs none /sys
mount -t devtmpfs none /dev

echo
echo "================================="
echo " QEMU tiny Linux is alive"
echo "================================="
echo

echo "[init] kernel:"
uname -a

echo
echo "[init] command line:"
cat /proc/cmdline

echo
echo "[init] CPU:"
grep -E 'Processor|model name|Hardware|Features' /proc/cpuinfo || true

echo
echo "[init] memory:"
head -5 /proc/meminfo

echo
echo "[init] device-tree compatible:"
tr '\0' '\n' < /sys/firmware/devicetree/base/compatible 2>/dev/null || true

echo
echo "[init] starting shell"
exec /bin/sh
EOF

$ chmod +x init
```

This script does three important mounts:

- `/proc`: kernel process and system information,
- `/sys`: device model and sysfs,
- `/dev`: device nodes from `devtmpfs`.

Without `/dev`, a real system quickly becomes annoying. Without `/proc` and `/sys`, you are blind.

## 129.7  Pack the initramfs

From inside the rootfs directory:

```sh
$ cd ~/imx6ull/virt-lab/rootfs
$ find . -print0 | cpio --null -ov --format=newc | gzip -9 > ../boot/initramfs.cpio.gz
```

Inspect the archive without unpacking it:

```sh
$ cd ~/imx6ull/virt-lab
$ ls -lh boot/initramfs.cpio.gz
$ gzip -dc boot/initramfs.cpio.gz | cpio -it | head -30
```

You must see:

```text
.
bin
bin/busybox
bin/sh
init
proc
sys
dev
```

If `/init` is missing, the kernel cannot run it. If `bin/sh` is missing, `/init` will fail at the final `exec`.

## 129.8  Build Linux for QEMU ARM `virt`

Get Linux:

```sh
$ cd ~/imx6ull/virt-lab/src
$ git clone https://git.kernel.org/pub/scm/linux/kernel/git/stable/linux.git
$ cd linux
$ git checkout v6.6
```

Configure:

```sh
$ make ARCH=arm O=~/imx6ull/virt-lab/build/linux-qemu multi_v7_defconfig
```

Enable the pieces this boot needs:

```sh
$ cd ~/imx6ull/virt-lab/src/linux
$ scripts/config --file ~/imx6ull/virt-lab/build/linux-qemu/.config \
    -e DEVTMPFS \
    -e DEVTMPFS_MOUNT \
    -e BLK_DEV_INITRD \
    -e SERIAL_AMBA_PL011 \
    -e SERIAL_AMBA_PL011_CONSOLE \
    -e VIRTIO \
    -e VIRTIO_MMIO

$ make ARCH=arm O=~/imx6ull/virt-lab/build/linux-qemu olddefconfig
```

Build:

```sh
$ make ARCH=arm O=~/imx6ull/virt-lab/build/linux-qemu \
    CROSS_COMPILE=$CROSS_COMPILE -j$(nproc) zImage
```

Copy:

```sh
$ cp ~/imx6ull/virt-lab/build/linux-qemu/arch/arm/boot/zImage \
    ~/imx6ull/virt-lab/boot/zImage
```

Inspect:

```sh
$ file ~/imx6ull/virt-lab/boot/zImage
$ ls -lh ~/imx6ull/virt-lab/boot/zImage
```

`zImage` is a compressed ARM kernel image. It is not an ELF file you can run on the host.

## 129.9  Get QEMU's Device Tree

The `virt` machine generates its own hardware description. Dump it:

```sh
$ cd ~/imx6ull/virt-lab
$ qemu-system-arm \
    -M virt,dumpdtb=boot/qemu-virt-arm.dtb \
    -cpu cortex-a15 \
    -m 256M \
    -nographic
```

Depending on QEMU version, it may exit immediately after dumping the DTB or sit with no useful boot. If it sits, quit:

```text
Ctrl-a x
```

Convert the DTB to readable DTS:

```sh
$ dtc -I dtb -O dts -o boot/qemu-virt-arm.dts boot/qemu-virt-arm.dtb
```

Now inspect the hardware Linux will see:

```sh
$ grep -n "compatible" boot/qemu-virt-arm.dts | head
$ grep -n "pl011" boot/qemu-virt-arm.dts
$ grep -n "memory@" boot/qemu-virt-arm.dts
$ grep -n "interrupt-controller" boot/qemu-virt-arm.dts | head
```

You should find a PL011 UART. That is why the Linux console will be `ttyAMA0`.

## 129.10  Boot Linux directly

Run:

```sh
$ cd ~/imx6ull/virt-lab
$ qemu-system-arm \
    -M virt \
    -cpu cortex-a15 \
    -m 256M \
    -nographic \
    -kernel boot/zImage \
    -dtb boot/qemu-virt-arm.dtb \
    -initrd boot/initramfs.cpio.gz \
    -append "console=ttyAMA0 root=/dev/ram0 rdinit=/init"
```

Expected output near the end:

```text
Run /init as init process

=================================
 QEMU tiny Linux is alive
=================================

[init] kernel:
Linux (none) ...

[init] command line:
console=ttyAMA0 root=/dev/ram0 rdinit=/init

[init] starting shell
/ #
```

Save a clean log:

```sh
$ qemu-system-arm \
    -M virt \
    -cpu cortex-a15 \
    -m 256M \
    -nographic \
    -kernel boot/zImage \
    -dtb boot/qemu-virt-arm.dtb \
    -initrd boot/initramfs.cpio.gz \
    -append "console=ttyAMA0 root=/dev/ram0 rdinit=/init" \
    2>&1 | tee logs/qemu-linux-direct.log
```

Inside the guest:

```sh
/ # cat /proc/iomem
/ # ls /sys/firmware/devicetree/base
/ # tr '\0' '\n' < /sys/firmware/devicetree/base/compatible
/ # mount
/ # poweroff -f
```

If `poweroff -f` does not exit QEMU, use:

```text
Ctrl-a x
```

## 129.11  Every QEMU option explained

| Option | Meaning |
|--------|---------|
| `-M virt` | create QEMU's generic ARM virtual board |
| `-cpu cortex-a15` | emulate an ARMv7-A CPU suitable for this lab |
| `-m 256M` | give the guest 256 MiB RAM |
| `-nographic` | connect guest serial to the terminal |
| `-kernel boot/zImage` | load the Linux kernel directly |
| `-dtb boot/qemu-virt-arm.dtb` | pass this Device Tree to the kernel |
| `-initrd boot/initramfs.cpio.gz` | load this cpio archive as initramfs |
| `-append "..."` | pass the kernel command line |

The command line is the virtual hardware bench. Change one piece at a time.

## 129.12  What `rdinit=/init` did

The kernel unpacks the initramfs into a RAM filesystem and looks for a first program.

With:

```text
rdinit=/init
```

the kernel runs `/init` from the initramfs.

Without `rdinit=`, the kernel tries the usual paths:

```text
/sbin/init
/etc/init
/bin/init
/bin/sh
```

Our initramfs has `/init`, so we tell the kernel exactly what to run.

## 129.13  Break it on purpose

This chapter is not finished until you have seen the common failures.

### Failure 1: wrong console

Change:

```text
console=ttyS0
```

Run and save:

```sh
$ qemu-system-arm ... \
    -append "console=ttyS0 root=/dev/ram0 rdinit=/init" \
    2>&1 | tee logs/qemu-linux-wrong-console.log
```

Expected symptom: QEMU starts, but useful Linux output disappears or appears only before the console handoff. The kernel is talking to the wrong UART.

Lesson: `console=` must match the UART driver and DTB.

### Failure 2: no initramfs

Remove:

```text
-initrd boot/initramfs.cpio.gz
```

Expected symptom: kernel panic because there is no root filesystem and no init.

Look for text like:

```text
VFS: Cannot open root device
Kernel panic - not syncing
```

Lesson: the kernel image is not user space.

### Failure 3: `/init` not executable

Break it:

```sh
$ chmod -x rootfs/init
$ cd rootfs
$ find . -print0 | cpio --null -ov --format=newc | gzip -9 > ../boot/initramfs-bad-init.cpio.gz
```

Boot with:

```text
-initrd boot/initramfs-bad-init.cpio.gz
```

Expected symptom: the kernel finds `/init` but cannot execute it, then panics.

Restore:

```sh
$ chmod +x rootfs/init
```

### Failure 4: wrong architecture user space

Copy a host binary into the initramfs as `/init`:

```sh
$ cp /bin/echo rootfs/init
```

Pack and boot.

Expected symptom: exec format error or failure to run init.

Restore the shell script after the test.

Lesson: the kernel is ARM. User-space binaries must be ARM too.

### Failure 5: wrong DTB

Boot with no DTB:

```sh
$ qemu-system-arm \
    -M virt \
    -cpu cortex-a15 \
    -m 256M \
    -nographic \
    -kernel boot/zImage \
    -initrd boot/initramfs.cpio.gz \
    -append "console=ttyAMA0 root=/dev/ram0 rdinit=/init"
```

Depending on QEMU and kernel behavior, QEMU may provide a DTB automatically or the boot may fail differently. The lesson is still important: on real ARM boards, the DTB is not decoration. It is how Linux discovers devices.

For a stronger failure, pass a DTB from a different machine and watch devices disappear.

## 129.14  Clean rebuild script

Create `run-direct.sh`:

```sh
#!/bin/sh
set -eu

qemu-system-arm \
    -M virt \
    -cpu cortex-a15 \
    -m 256M \
    -nographic \
    -kernel boot/zImage \
    -dtb boot/qemu-virt-arm.dtb \
    -initrd boot/initramfs.cpio.gz \
    -append "console=ttyAMA0 root=/dev/ram0 rdinit=/init"
```

Make it executable:

```sh
$ chmod +x run-direct.sh
$ ./run-direct.sh
```

This script is the input to Chapter 130. U-Boot will replace QEMU's direct loader, but the artifacts stay the same.

## 129.15  Lab

Deliverables:

1. `boot/zImage`
2. `boot/qemu-virt-arm.dtb`
3. `boot/qemu-virt-arm.dts`
4. `boot/initramfs.cpio.gz`
5. `run-direct.sh`
6. `logs/qemu-linux-direct.log`
7. Failure logs for wrong console, missing initramfs, bad `/init`, and wrong-architecture `/init`

The lab is complete when you can answer without looking:

- Which file is the kernel?
- Which file describes hardware?
- Which file becomes `/`?
- Which program becomes PID 1?
- Which UART is the console?
- What breaks when each input is missing?

## 129.16  Pitfalls

- **Building BusyBox for the host.** Check with `file bin/busybox`.
- **Dynamic BusyBox.** Static is simpler for initramfs.
- **Missing `/init` executable bit.** The kernel cannot execute it.
- **Wrong `console=`.** QEMU `virt` uses PL011, which appears as `ttyAMA0`.
- **Confusing `qemu-system-arm` with `qemu-arm`.** `qemu-system-arm` emulates a whole machine. `qemu-arm` runs one ARM user-space program.
- **Assuming QEMU `virt` equals i.MX6ULL.** It does not. It teaches the boot contract.
- **Changing kernel, DTB, and initramfs together.** Change one input at a time.

## 129.17  Going deeper

- QEMU Arm `virt` machine documentation.
- Linux ARM boot protocol.
- Linux initramfs documentation.
- BusyBox build documentation.
- Chapter 130: U-Boot in QEMU.
