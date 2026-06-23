---
chapter: 135
title: DomU Linux on i.MX6ULL
part: IX - Applied virtualization and mixed-criticality systems
estimated_pages: 28
status: draft
---

# Chapter 135: DomU Linux on i.MX6ULL

> **What:** start a tiny DomU Linux guest on the real i.MX6ULL board after Xen and Dom0 are working.
>
> **Why:** QEMU proved the mechanics. The i.MX6ULL proves the real constraints: one CPU, small RAM, real storage, real serial logs, and no room for vague boot assumptions.
>
> **Focus:** success is isolation, not performance. A tiny DomU that can die without killing Dom0 is the goal.
> **DomU:** an unprivileged Xen guest domain.
> **Dom0:** the privileged Xen control domain that creates and manages DomU guests.

## 135.1  Starting point

Do not begin here until Chapter 134 works:

```text
U-Boot -> Xen -> Dom0 Linux -> shell
```

Minimum Dom0 proof:

```sh
# uname -a
# cat /proc/cmdline
# ls /sys/hypervisor
# dmesg | grep -i xen
```

If Dom0 is unstable, adding DomU only hides the bug.

## 135.2  What changes from QEMU

QEMU gave us comfort:

- easy reset,
- plenty of fake RAM,
- configurable CPU count,
- no SD-card wear,
- easy file injection.

i.MX6ULL gives us reality:

- one Cortex-A7 core,
- 512 MiB RAM on the reference board,
- real U-Boot environment,
- real SD/eMMC,
- real serial console,
- real DTB,
- real memory pressure.

So the first DomU must be modest:

```text
memory = 32 or 64 MiB
vcpus = 1
initramfs root
Xen console only
no networking
no block device
no passthrough
```

## 135.3  Upgrade Dom0 from "proof shell" to "control domain"

Chapter 134's smallest Dom0 may not include `xl`. For DomU, Dom0 needs:

- Xen toolstack,
- xenstore,
- xenfs,
- event channel support,
- enough filesystem to hold DomU kernel/initramfs/config.

Check:

```sh
# which xl
# xl info
# xl list
```

If `xl` is missing, rebuild Dom0 rootfs with Xen tools, or use an NFS rootfs while developing.

## 135.4  Dom0 kernel options

Dom0 should have:

```text
CONFIG_XEN=y
CONFIG_XEN_DOM0=y
CONFIG_HVC_XEN=y
CONFIG_XEN_DEV_EVTCHN=y
CONFIG_XENFS=y
CONFIG_XEN_SYS_HYPERVISOR=y
CONFIG_XEN_BACKEND=y
CONFIG_XEN_BLKDEV_BACKEND=y
CONFIG_XEN_NETDEV_BACKEND=y
```

For this chapter, block and net backend are not strictly needed, but enabling them avoids rebuilding immediately in the next experiment.

## 135.5  Prepare transfer path

You need a way to place DomU files into Dom0:

```text
/boot/domu-zImage
/boot/domu-initramfs.cpio.gz
/etc/xen/imx6ull-domu.cfg
```

Good options:

- NFS mount from host,
- TFTP fetch into Dom0,
- copy to SD card boot partition,
- include files in Dom0 rootfs image.

For iteration, NFS is easiest:

```sh
# mkdir -p /mnt/host
# mount -t nfs -o nolock 192.168.7.1:/srv/nfs/imx6ull /mnt/host
# mkdir -p /boot /etc/xen
# cp /mnt/host/domu-zImage /boot/
# cp /mnt/host/domu-initramfs.cpio.gz /boot/
# cp /mnt/host/imx6ull-domu.cfg /etc/xen/
```

If NFS is not working yet, use the SD card. Do not debug NFS and DomU at the same time.

## 135.6  Build DomU kernel

Use the same Linux source as Chapter 133 or the Part IV kernel tree.

Configure a DomU build:

```sh
$ make ARCH=arm O=../linux-domu-imx6ull imx_v6_v7_defconfig
```

Enable:

```sh
$ scripts/config --file ../linux-domu-imx6ull/.config \
    -e XEN \
    -e HVC_XEN \
    -e XEN_DEV_EVTCHN \
    -e XENFS \
    -e BLK_DEV_INITRD \
    -e DEVTMPFS \
    -e DEVTMPFS_MOUNT

$ make ARCH=arm O=../linux-domu-imx6ull olddefconfig
```

Build:

```sh
$ make ARCH=arm O=../linux-domu-imx6ull \
    CROSS_COMPILE=arm-none-linux-gnueabihf- -j$(nproc) zImage
```

Copy:

```sh
$ cp ../linux-domu-imx6ull/arch/arm/boot/zImage /srv/nfs/imx6ull/domu-zImage
```

## 135.7  Build DomU initramfs

Use static BusyBox. DomU `/init`:

```sh
#!/bin/sh
mount -t proc none /proc
mount -t sysfs none /sys
mount -t devtmpfs none /dev

echo
echo "======================"
echo " i.MX6ULL DomU alive"
echo "======================"
echo

uname -a
cat /proc/cmdline
head -5 /proc/meminfo

echo
echo "Try killing me from Dom0 with: xl destroy imx6ull-domu"

exec /bin/sh
```

Pack:

```sh
$ find rootfs-domu -print0 | cpio --null -ov --format=newc | gzip -9 \
    > /srv/nfs/imx6ull/domu-initramfs.cpio.gz
```

Keep it small:

```sh
$ ls -lh /srv/nfs/imx6ull/domu-initramfs.cpio.gz
```

If it is large, stop and shrink it. This board has no RAM to waste.

## 135.8  Domain config

Create `imx6ull-domu.cfg`:

```python
name = "imx6ull-domu"
kernel = "/boot/domu-zImage"
ramdisk = "/boot/domu-initramfs.cpio.gz"
memory = 64
vcpus = 1
extra = "console=hvc0 rdinit=/init"
on_crash = "preserve"
```

If 64 MiB is too much for your Dom0 memory budget, try 32 MiB. If 32 MiB is too small for your kernel/initramfs, reduce the initramfs before raising memory.

## 135.9  Start DomU

In Dom0:

```sh
# xl create -c /etc/xen/imx6ull-domu.cfg
```

Expected:

```text
i.MX6ULL DomU alive
/ #
```

Detach:

```text
Ctrl-]
```

List:

```sh
# xl list
```

Expected shape:

```text
Name                                        ID   Mem VCPUs      State   Time(s)
Domain-0                                     0   ...     1     r-----     ...
imx6ull-domu                                 1    64     1     r-----     ...
```

## 135.10  Prove there are two Linux systems

In Dom0:

```sh
# uname -a
# cat /proc/cmdline
# xl list
```

In DomU:

```sh
# uname -a
# cat /proc/cmdline
# head -5 /proc/meminfo
```

Record both. The kernels may be built from the same source, but they are not the same running system.

## 135.11  Restart DomU

From Dom0:

```sh
# xl shutdown imx6ull-domu
# xl list
```

If graceful shutdown is not supported by the tiny guest:

```sh
# xl destroy imx6ull-domu
```

Start again:

```sh
# xl create -c /etc/xen/imx6ull-domu.cfg
```

The restart is important. A domain that boots only once is not an understood domain.

## 135.12  Prove failure isolation

Inside DomU:

```sh
# kill -SEGV 1
```

or from Dom0:

```sh
# xl destroy imx6ull-domu
```

Now prove Dom0 survived:

```sh
# date
# xl list
# dmesg | tail -40
```

The board must not reset. Dom0 must remain responsive.

This is the core result of the chapter.

## 135.13  Memory pressure check

In Dom0:

```sh
# free -m
# xl info | grep -i memory
```

Start DomU and run again:

```sh
# xl create /etc/xen/imx6ull-domu.cfg
# free -m
# xl list
```

Write down:

```text
Dom0 memory before:
Dom0 memory after:
DomU assigned:
Free memory remaining:
```

This keeps the experiment honest. The i.MX6ULL is small.

## 135.14  What this proves

This chapter proves:

- Xen can create a second Linux domain on real i.MX6ULL hardware.
- Dom0 and DomU have separate assigned memory.
- DomU has a separate kernel command line.
- DomU can be destroyed without resetting the board.
- The serial log can show real HYP-mode virtualization, not only QEMU.

## 135.15  What this does not prove

It does not prove:

- good performance,
- hard real-time behavior,
- safe device passthrough,
- production-ready update flow,
- that single-core i.MX6ULL is a good multi-guest product platform.

One Cortex-A7 means one physical execution engine. Xen can schedule domains. It cannot create another core.

## 135.16  Break it on purpose

### Failure 1: too much memory

Set:

```python
memory = 384
```

Expected: domain creation fails or Dom0 becomes memory-starved.

### Failure 2: wrong console

Set:

```python
extra = "console=ttymxc0 rdinit=/init"
```

Expected: DomU output disappears. DomU does not own the physical i.MX UART.

### Failure 3: missing initramfs

Rename:

```sh
# mv /boot/domu-initramfs.cpio.gz /boot/domu-initramfs.cpio.gz.missing
```

Expected: `xl create` or DomU boot fails.

### Failure 4: bad `/init`

Use an initramfs without executable `/init`.

Expected: DomU kernel panics, Dom0 survives.

## 135.17  Lab

Deliverables:

1. Dom0 boot log from Chapter 134.
2. Dom0 `xl info` output.
3. `/etc/xen/imx6ull-domu.cfg`.
4. DomU boot log.
5. `xl list` showing Dom0 and DomU.
6. Dom0 and DomU `uname -a` outputs.
7. Memory pressure notes.
8. Failure-isolation log.
9. Failure notes for too much memory, wrong console, missing initramfs, and bad `/init`.

The lab is complete when the serial log proves:

```text
Dom0 alive
DomU alive
DomU dies
Dom0 still alive
```

## 135.18  Pitfalls

- **Using a giant Dom0.** The board has limited RAM.
- **Using a giant DomU.** Start with 32 or 64 MiB.
- **Expecting physical UART in DomU.** Use `hvc0`.
- **Debugging DomU before `xl info` works.** Toolstack first.
- **Forgetting this is one physical CPU.** Do not expect parallel throughput.
- **Treating destroy as production shutdown.** It is fine for first lab, not for a product.
- **Skipping memory accounting.** Small boards punish optimism.

## 135.19  Going deeper

- Xen `xl` toolstack documentation.
- Xen ARM DomU documentation.
- Xen console documentation.
- Chapter 136 for device assignment and DMA boundaries.
