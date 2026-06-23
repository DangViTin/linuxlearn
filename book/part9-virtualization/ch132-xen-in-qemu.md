---
chapter: 132
title: Xen in QEMU
part: IX - Applied virtualization and mixed-criticality systems
estimated_pages: 34
status: draft
---

# Chapter 132: Xen in QEMU

> **What:** build Xen for 32-bit Arm, build a Dom0-capable Linux kernel, create a tiny Dom0 initramfs, build a Xen-aware DTB, and boot `QEMU -> Xen -> Dom0`.
>
> **Why:** Xen on the real i.MX6ULL adds board-specific failure modes. QEMU lets us prove the Xen boot contract first.
>
> **Focus:** Xen boots first. Linux is no longer the first privileged software. Dom0 is Linux, but Linux running as a Xen domain.
> **Xen:** a type-1 hypervisor. On ARM it runs before Linux and creates domains.
> **Dom0:** the first privileged Xen domain, usually Linux, responsible for control and device backends.
> **DomU:** an unprivileged guest domain created later by Dom0.

## 132.1  Boot path

The target boot path:

```text
qemu-system-arm
  -> loads Xen as the kernel image
  -> loads Dom0 kernel into RAM
  -> loads Dom0 initramfs into RAM
  -> passes a DTB describing those modules
Xen
  -> initializes CPU, GIC, timer, memory
  -> creates Domain 0
Dom0 Linux
  -> boots with console=hvc0
  -> unpacks initramfs
  -> runs /init
```

This is the first time Linux is not the owner of the machine.

## 132.2  Workspace

```sh
$ mkdir -p ~/imx6ull/xen-qemu/{src,build,rootfs,boot,logs,notes}
$ cd ~/imx6ull/xen-qemu
```

Final artifacts:

```text
boot/
  xen
  zImage-dom0
  dom0-initramfs.cpio.gz
  qemu-virt-arm-xen.dtb
  qemu-virt-arm-xen.dts
logs/
  xen-qemu-dom0.log
notes/
  xen-qemu-addresses.md
```

## 132.3  Install host packages

```sh
$ sudo apt update
$ sudo apt install build-essential git bc bison flex libssl-dev \
    gcc-arm-linux-gnueabihf qemu-system-arm device-tree-compiler \
    cpio gzip file
```

Set cross compiler:

```sh
$ export CROSS_COMPILE=arm-linux-gnueabihf-
$ export ARCH=arm
```

If you use the book's project-local toolchain, set `CROSS_COMPILE` to that prefix instead.

## 132.4  Choose addresses first

QEMU `virt` 32-bit RAM starts at `0x40000000`.

Use:

```text
0x44000000  Dom0 zImage
0x48000000  Dom0 initramfs
```

In this chapter, QEMU loads Xen with `-kernel boot/xen` and passes the DTB with `-dtb`. We do not manually choose Xen's own load address here. We do manually choose the Dom0 module addresses because Xen finds those modules through `/chosen/module@.../reg`.

Create notes:

```sh
$ cat > notes/xen-qemu-addresses.md <<'EOF'
# Xen QEMU addresses

QEMU RAM base: 0x40000000

| Artifact | Address | Why |
|----------|---------|-----|
| Dom0 zImage | 0x44000000 | module 1 |
| Dom0 initramfs | 0x48000000 | module 2 |

Xen itself is loaded by QEMU through -kernel.
The DTB is passed by QEMU through -dtb.
EOF
```

The DTB module nodes must match the Dom0 addresses exactly.

## 132.5  Build Xen

Get Xen:

```sh
$ cd ~/imx6ull/xen-qemu/src
$ git clone https://github.com/xen-project/xen.git
$ cd xen
$ git checkout RELEASE-4.21.1
```

If that exact tag is unavailable in the future, use a current supported release and record it.

Build only the hypervisor:

```sh
$ make XEN_TARGET_ARCH=arm32 CROSS_COMPILE=$CROSS_COMPILE dist-xen
```

Copy:

```sh
$ cp xen/xen ~/imx6ull/xen-qemu/boot/xen
$ file ~/imx6ull/xen-qemu/boot/xen
$ ls -lh ~/imx6ull/xen-qemu/boot/xen
```

The file must be an Arm Xen image, not x86.

## 132.6  Build Dom0 Linux

Get Linux:

```sh
$ cd ~/imx6ull/xen-qemu/src
$ git clone https://git.kernel.org/pub/scm/linux/kernel/git/stable/linux.git
$ cd linux
$ git checkout v6.6
```

Configure:

```sh
$ make ARCH=arm O=~/imx6ull/xen-qemu/build/linux-dom0 multi_v7_defconfig
```

Enable Dom0-relevant options:

```sh
$ scripts/config --file ~/imx6ull/xen-qemu/build/linux-dom0/.config \
    -e XEN \
    -e XEN_DOM0 \
    -e HVC_XEN \
    -e XEN_DEV_EVTCHN \
    -e XENFS \
    -e XEN_SYS_HYPERVISOR \
    -e BLK_DEV_INITRD \
    -e DEVTMPFS \
    -e DEVTMPFS_MOUNT

$ make ARCH=arm O=~/imx6ull/xen-qemu/build/linux-dom0 olddefconfig
```

Build:

```sh
$ make ARCH=arm O=~/imx6ull/xen-qemu/build/linux-dom0 \
    CROSS_COMPILE=$CROSS_COMPILE -j$(nproc) zImage
```

Copy:

```sh
$ cp ~/imx6ull/xen-qemu/build/linux-dom0/arch/arm/boot/zImage \
    ~/imx6ull/xen-qemu/boot/zImage-dom0
$ ls -lh ~/imx6ull/xen-qemu/boot/zImage-dom0
```

## 132.7  Build Dom0 initramfs

Use a tiny BusyBox rootfs. You can reuse the static BusyBox from Chapter 129.

```sh
$ cd ~/imx6ull/xen-qemu
$ rm -rf rootfs/*
$ mkdir -p rootfs/{bin,sbin,proc,sys,dev,tmp,run,etc,root}
$ cp ~/imx6ull/virt-lab/rootfs/bin/busybox rootfs/bin/busybox
$ chmod +x rootfs/bin/busybox
$ cd rootfs/bin
$ for app in $(./busybox --list); do ln -sf busybox $app; done
$ cd ..
```

Create `/init`:

```sh
$ cat > init <<'EOF'
#!/bin/sh
mount -t proc none /proc
mount -t sysfs none /sys
mount -t devtmpfs none /dev

echo
echo "===================="
echo " QEMU Dom0 is alive"
echo "===================="
echo

echo "[dom0] kernel:"
uname -a

echo
echo "[dom0] cmdline:"
cat /proc/cmdline

echo
echo "[dom0] xen evidence:"
ls /sys/hypervisor 2>/dev/null || true
dmesg | grep -i xen | head -20 || true

exec /bin/sh
EOF
$ chmod +x init
```

Pack:

```sh
$ find . -print0 | cpio --null -ov --format=newc | gzip -9 > ../boot/dom0-initramfs.cpio.gz
```

Check:

```sh
$ cd ~/imx6ull/xen-qemu
$ ls -lh boot/dom0-initramfs.cpio.gz
$ gzip -dc boot/dom0-initramfs.cpio.gz | cpio -it | grep '^init$'
```

## 132.8  Get a QEMU DTB

Dump:

```sh
$ cd ~/imx6ull/xen-qemu
$ qemu-system-arm \
    -M virt,virtualization=on,dumpdtb=boot/qemu-virt-arm-base.dtb \
    -cpu cortex-a15 \
    -m 512M \
    -nographic
```

Quit with `Ctrl-a x` if it stays open.

Convert:

```sh
$ dtc -I dtb -O dts -o boot/qemu-virt-arm-base.dts boot/qemu-virt-arm-base.dtb
```

The `virtualization=on` part matters. Xen needs virtualization support exposed by QEMU.

## 132.9  Add Xen `/chosen` nodes

Copy the base DTS:

```sh
$ cp boot/qemu-virt-arm-base.dts boot/qemu-virt-arm-xen.dts
```

Open `boot/qemu-virt-arm-xen.dts` and find `/chosen`. Add or replace the contents so it has this shape:

```dts
chosen {
    xen,xen-bootargs = "console=dtuart dtuart=serial0 dom0_mem=256M dom0_max_vcpus=1";
    xen,dom0-bootargs = "console=hvc0 earlycon=xenboot root=/dev/ram0 rdinit=/init";

    module@44000000 {
        compatible = "multiboot,kernel", "multiboot,module";
        reg = <0x44000000 0x0>;
    };

    module@48000000 {
        compatible = "multiboot,ramdisk", "multiboot,module";
        reg = <0x48000000 0x0>;
    };
};
```

Now replace the two `0x0` sizes with real file sizes.

Before doing that, check how many cells this DTB expects for addresses and sizes:

```sh
$ grep -n "#address-cells\\|#size-cells" boot/qemu-virt-arm-xen.dts | head
```

For the 32-bit QEMU `virt` DTB used in this chapter, the simple two-cell form is the common shape:

```dts
reg = <address size>;
```

If your dumped DTB uses two address cells or two size cells at the relevant parent node, write the `reg` property with the matching number of cells instead:

```dts
reg = <0x0 0x44000000 0x0 0x006a1234>;
```

Do not guess. `dtc` can compile a syntactically valid DTB that still describes the module address in the wrong cell format.

Get sizes in hex:

```sh
$ printf '0x%x\n' $(stat -c%s boot/zImage-dom0)
$ printf '0x%x\n' $(stat -c%s boot/dom0-initramfs.cpio.gz)
```

If the DTB uses the simple two-cell form and Dom0 kernel size is `0x6a1234`, the first `reg` becomes:

```dts
reg = <0x44000000 0x6a1234>;
```

If initramfs size is `0x91234`, the second becomes:

```dts
reg = <0x48000000 0x91234>;
```

Compile:

```sh
$ dtc -I dts -O dtb -o boot/qemu-virt-arm-xen.dtb boot/qemu-virt-arm-xen.dts
```

Inspect:

```sh
$ dtc -I dtb -O dts boot/qemu-virt-arm-xen.dtb | less
```

Search for:

- `xen,xen-bootargs`,
- `xen,dom0-bootargs`,
- `module@44000000`,
- `module@48000000`.

Also re-check the final `reg` properties. They must match:

```text
Dom0 kernel load address and size
Dom0 initramfs load address and size
the address-cell and size-cell format used by this DTB
```

## 132.10  Boot Xen

Run:

```sh
$ cd ~/imx6ull/xen-qemu
$ qemu-system-arm \
    -M virt,virtualization=on \
    -cpu cortex-a15 \
    -m 512M \
    -nographic \
    -kernel boot/xen \
    -dtb boot/qemu-virt-arm-xen.dtb \
    -device loader,file=boot/zImage-dom0,addr=0x44000000 \
    -device loader,file=boot/dom0-initramfs.cpio.gz,addr=0x48000000
```

Expected sequence:

```text
Xen ...
Booting on ARM ...
Loading Dom0 kernel ...
Linux version ...
QEMU Dom0 is alive
/ #
```

Save a log:

```sh
$ qemu-system-arm \
    -M virt,virtualization=on \
    -cpu cortex-a15 \
    -m 512M \
    -nographic \
    -kernel boot/xen \
    -dtb boot/qemu-virt-arm-xen.dtb \
    -device loader,file=boot/zImage-dom0,addr=0x44000000 \
    -device loader,file=boot/dom0-initramfs.cpio.gz,addr=0x48000000 \
    2>&1 | tee logs/xen-qemu-dom0.log
```

## 132.11  Verify from Dom0

Inside Dom0:

```sh
/ # cat /proc/cmdline
/ # ls /sys/hypervisor
/ # dmesg | grep -i xen
/ # mount
/ # poweroff -f
```

The command line should contain:

```text
console=hvc0 earlycon=xenboot root=/dev/ram0 rdinit=/init
```

The console is `hvc0` because Dom0 is using Xen's paravirtual console, not the physical PL011 UART directly.

## 132.12  Annotate the log

Create:

```sh
$ cp logs/xen-qemu-dom0.log logs/xen-qemu-dom0.annotated.log
```

Add comments manually around:

```text
Xen first line:
Xen command line:
CPU/GIC/timer:
Dom0 creation:
Linux first line:
Dom0 command line:
/init output:
```

This annotation becomes input for Chapter 131's log-reading exercise.

## 132.13  Break it on purpose

### Failure 1: no virtualization support

Remove:

```text
virtualization=on
```

Expected symptom: Xen cannot run correctly because QEMU did not expose the virtualization extensions.

Lesson: HYP mode is hardware support, not a Xen preference.

### Failure 2: wrong module size

Set Dom0 ramdisk size to a tiny value in the DTS:

```dts
reg = <0x48000000 0x100>;
```

Rebuild DTB and boot.

Expected symptom: Dom0 kernel starts but cannot unpack or run the initramfs.

Lesson: Xen trusts the DTB module metadata.

### Failure 3: wrong Dom0 console

Change:

```text
console=ttyAMA0
```

Expected symptom: Xen prints, Dom0 may boot, but expected Dom0 console output is missing.

Lesson: Dom0's first console is Xen's `hvc0`, not necessarily the physical UART.

### Failure 4: address mismatch

Load Dom0 kernel at `0x45000000` but leave DTB module node at `0x44000000`.

Expected symptom: Xen reads the wrong memory as the Dom0 kernel.

Lesson: loader addresses and DTB `reg` values are one contract.

## 132.14  Lab

Deliverables:

1. `boot/xen`
2. `boot/zImage-dom0`
3. `boot/dom0-initramfs.cpio.gz`
4. `boot/qemu-virt-arm-xen.dtb`
5. `boot/qemu-virt-arm-xen.dts`
6. `logs/xen-qemu-dom0.log`
7. `logs/xen-qemu-dom0.annotated.log`
8. Failure notes for missing virtualization, wrong module size, wrong console, and address mismatch

The lab is complete when the log proves:

```text
QEMU -> Xen -> Dom0 Linux -> /init -> shell
```

## 132.15  Pitfalls

- **No `virtualization=on`.** Xen needs virtualization support exposed.
- **DTB module address mismatch.** QEMU loader address and DTB `reg` must agree.
- **Wrong module size.** Xen does not know your file size unless you tell it.
- **Dom0 console wrong.** Start with `console=hvc0 earlycon=xenboot`.
- **Too large Dom0.** Keep the initramfs small.
- **Skipping annotation.** If you cannot mark the handoff in the log, you do not understand the boot yet.

## 132.16  Going deeper

- Xen ARM booting documentation.
- Xen ARM Device Tree boot module documentation.
- QEMU loader device documentation.
- Linux Xen guest configuration options.
- Chapter 133 for starting the first DomU.
