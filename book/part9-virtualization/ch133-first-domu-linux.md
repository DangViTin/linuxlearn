---
chapter: 133
title: First DomU Linux
part: IX - Applied virtualization and mixed-criticality systems
estimated_pages: 30
status: draft
---

# Chapter 133: First DomU Linux

> **What:** add the Xen toolstack to Dom0, build a tiny DomU kernel and initramfs, write an `xl` domain config, and start a second Linux kernel under Xen.
>
> **Why:** Xen is not interesting until a guest exists. This chapter produces the first real "two Linux systems are alive" result.
>
> **Focus:** Dom0 controls the platform. DomU receives only the memory, vCPU, console, and devices Xen gives it.
> **xl:** Xen's command-line tool for creating, listing, controlling, and destroying domains.
> **xenstore:** Xen's shared configuration/state database used by domains and tools.
> **event channel:** Xen's lightweight notification mechanism between domains and Xen.

## 133.1  Boot path

We extend Chapter 132:

```text
QEMU -> Xen -> Dom0 Linux -> xl create -> DomU Linux
```

The new moving parts are:

- a Dom0 rootfs with Xen tools,
- a DomU kernel,
- a DomU initramfs,
- an `xl` config file.

## 133.2  Why the Chapter 132 Dom0 is too small

Chapter 132 used a tiny BusyBox initramfs. It was perfect for proving:

```text
Xen -> Dom0 -> shell
```

But `xl` needs more user space:

- libraries,
- xenstore daemon,
- xenfs,
- event channel device,
- control scripts or minimal replacements.

For this chapter, use a small Buildroot Dom0. That is still buildable, but less fragile than hand-copying every toolstack dependency.

## 133.3  Buildroot Dom0 shape

Create a Buildroot config for ARMv7 with:

```text
Target architecture: ARM little endian
Target ABI: EABIhf
Target CPU: cortex-A15 for QEMU
Init system: BusyBox or systemd, BusyBox is smaller
Root filesystem: cpio gzip
```

Packages:

```text
Xen tools
dtc, optional
busybox shell utilities
```

Buildroot symbol names vary. Search:

```sh
$ make menuconfig
```

Then use `/` search for:

```text
xen
```

Enable the Xen toolstack package if available in your Buildroot release.

The output should include a rootfs cpio archive and `/usr/sbin/xl` or `/usr/bin/xl` inside it.

## 133.4  Dom0 kernel config

Dom0 Linux needs:

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

For the first DomU, block/net backends are optional if the guest uses only initramfs and console. Enable them anyway so Chapter 135 has a smoother path.

## 133.5  Dom0 startup script

Dom0 must mount xenfs and start xenstore if your rootfs does not do it automatically.

Minimal init sequence:

```sh
mount -t proc none /proc
mount -t sysfs none /sys
mount -t devtmpfs none /dev
mkdir -p /proc/xen
mount -t xenfs none /proc/xen

# Depending on packaging:
xenstored --pid-file /run/xenstored.pid &
sleep 1
```

Some distributions start xenstored through init scripts. Buildroot packaging may provide a service. The test is not "did a service file exist", it is:

```sh
# xl info
```

## 133.6  Dom0 checks before DomU

Boot Xen + Dom0 as in Chapter 132, but with the richer Dom0 initramfs.

Inside Dom0:

```sh
# which xl
# mount | grep xen
# ls /proc/xen
# ls /dev/xen 2>/dev/null || true
# xl info
# xl list
```

Expected `xl list`:

```text
Name                                        ID   Mem VCPUs      State   Time(s)
Domain-0                                     0   ...     1     r-----     ...
```

If `xl info` fails, stop. DomU cannot work until Dom0 tooling works.

## 133.7  Build DomU Linux

Use a separate kernel build directory:

```sh
$ cd ~/imx6ull/xen-qemu/src/linux
$ make ARCH=arm O=~/imx6ull/xen-qemu/build/linux-domu multi_v7_defconfig
```

Enable:

```sh
$ scripts/config --file ~/imx6ull/xen-qemu/build/linux-domu/.config \
    -e XEN \
    -e HVC_XEN \
    -e XEN_DEV_EVTCHN \
    -e XENFS \
    -e BLK_DEV_INITRD \
    -e DEVTMPFS \
    -e DEVTMPFS_MOUNT

$ make ARCH=arm O=~/imx6ull/xen-qemu/build/linux-domu olddefconfig
```

Build:

```sh
$ make ARCH=arm O=~/imx6ull/xen-qemu/build/linux-domu \
    CROSS_COMPILE=$CROSS_COMPILE -j$(nproc) zImage
```

Copy into Dom0 rootfs or a location Dom0 can read:

```text
/boot/domu-zImage
```

## 133.8  Build DomU initramfs

DomU `/init`:

```sh
#!/bin/sh
mount -t proc none /proc
mount -t sysfs none /sys
mount -t devtmpfs none /dev

echo
echo "================"
echo " DomU is alive"
echo "================"
echo

uname -a
cat /proc/cmdline
head -5 /proc/meminfo

exec /bin/sh
```

Pack:

```sh
$ find . -print0 | cpio --null -ov --format=newc | gzip -9 > domu-initramfs.cpio.gz
```

Copy into Dom0:

```text
/boot/domu-initramfs.cpio.gz
```

## 133.9  Domain config

Create `/etc/xen/domu-tiny.cfg` inside Dom0:

```python
name = "domu-tiny"
kernel = "/boot/domu-zImage"
ramdisk = "/boot/domu-initramfs.cpio.gz"
memory = 64
vcpus = 1
extra = "console=hvc0 rdinit=/init"
on_crash = "preserve"
```

Line by line:

| Line | Meaning |
|------|---------|
| `name` | domain name shown by `xl list` |
| `kernel` | path inside Dom0 rootfs |
| `ramdisk` | path inside Dom0 rootfs |
| `memory` | MiB assigned to DomU |
| `vcpus` | virtual CPUs assigned to DomU |
| `extra` | DomU kernel command line |
| `on_crash` | keep crashed domain for inspection |

Start with 64 MiB. It is enough for an initramfs shell and small enough to keep memory pressure visible.

## 133.10  Start DomU

Inside Dom0:

```sh
# xl create -c /etc/xen/domu-tiny.cfg
```

Expected:

```text
DomU is alive
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

Attach again:

```sh
# xl console domu-tiny
```

## 133.11  Prove there are two Linux kernels

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

The two command lines should differ:

- Dom0 has Xen Dom0 bootargs.
- DomU has `console=hvc0 rdinit=/init`.

The memory sizes should differ too.

## 133.12  Shut down and restart

Try graceful shutdown:

```sh
# xl shutdown domu-tiny
# xl list
```

If the tiny DomU lacks enough user-space support for graceful shutdown:

```sh
# xl destroy domu-tiny
```

Start it again:

```sh
# xl create -c /etc/xen/domu-tiny.cfg
```

Lifecycle matters. A guest that can boot once but not restart is not understood yet.

## 133.13  Prove failure isolation

Inside DomU:

```sh
# kill -SEGV 1
```

If the guest remains alive, try:

```sh
# echo c > /proc/sysrq-trigger
```

This requires sysrq support and may not be enabled. The goal is simple: break DomU.

Back in Dom0:

```sh
# xl list
# dmesg | tail -40
```

Dom0 should survive. Xen should survive. QEMU should keep running.

This is the first concrete hypervisor payoff.

## 133.14  Save logs

Capture:

```sh
# xl info > /root/xl-info.txt
# xl list > /root/xl-list-with-domu.txt
# dmesg > /root/dom0-dmesg-after-domu.txt
```

On the host, save the whole QEMU serial run:

```sh
$ qemu-system-arm ... 2>&1 | tee logs/xen-qemu-domu.log
```

## 133.15  Break it on purpose

### Failure 1: missing DomU kernel

Rename:

```sh
# mv /boot/domu-zImage /boot/domu-zImage.missing
# xl create -c /etc/xen/domu-tiny.cfg
```

Expected: `xl` fails before creating a useful guest.

### Failure 2: too much memory

Set:

```python
memory = 4096
```

Expected: domain creation fails because the platform does not have that memory.

### Failure 3: wrong console

Set:

```python
extra = "console=ttyAMA0 rdinit=/init"
```

Expected: guest may boot but console output is missing.

### Failure 4: bad initramfs

Point `ramdisk` at a file that is not a cpio archive.

Expected: DomU kernel boots, then panics when it cannot run init.

## 133.16  Lab

Deliverables:

1. Dom0 boot log with `xl info`.
2. `/etc/xen/domu-tiny.cfg`.
3. DomU kernel and initramfs paths.
4. DomU boot log.
5. `xl list` showing Dom0 and DomU.
6. Dom0 and DomU `uname -a` output.
7. Failure-isolation evidence.
8. Failure notes for missing kernel, too much memory, wrong console, and bad initramfs.

The lab is complete when two Linux kernels have printed `uname -a` in one QEMU run and Dom0 survives a DomU failure.

## 133.17  Pitfalls

- **Using the tiny Chapter 132 Dom0.** It probably lacks `xl`.
- **No xenfs.** Mount `/proc/xen`.
- **xenstored not running.** `xl info` will fail.
- **Wrong DomU console.** Start with `console=hvc0`.
- **Too much DomU memory.** Use 64 MiB first.
- **Confusing host files and Dom0 files.** `kernel = "/boot/domu-zImage"` is a path inside Dom0.
- **Skipping restart.** Boot once, destroy, boot again.

## 133.18  Going deeper

- Xen `xl` documentation.
- Xen `xl.cfg` documentation.
- Xen event channels.
- Xen xenstore documentation.
- Chapter 135 for DomU on real i.MX6ULL.
