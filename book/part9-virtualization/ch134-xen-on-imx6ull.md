---
chapter: 134
title: Xen on i.MX6ULL
part: IX - Applied virtualization and mixed-criticality systems
estimated_pages: 30
status: draft
---

# Chapter 134: Xen on i.MX6ULL

> **What:** boot Xen on the real i.MX6ULL board, then let Xen boot a small Dom0 Linux.
>
> **Why:** QEMU proved the shape. The real board proves the uncomfortable details: U-Boot handoff mode, real Device Tree, real serial console, real RAM limits, and real "nothing prints" failures.
>
> **Focus:** Xen is now the first privileged software after U-Boot. Linux is no longer bare metal.

## 134.1  What success looks like

This chapter is complete when the serial log shows this sequence:

```
U-Boot prompt
  -> loads Xen
  -> loads Dom0 Linux zImage
  -> loads Dom0 initramfs
  -> loads and edits the board DTB
  -> jumps to Xen
Xen prints first
Xen creates Domain 0
Dom0 Linux boots
Dom0 reaches a shell
```

Do not start with DomU. Do not start with networking. Do not start with passthrough. The first milestone is only:

```
U-Boot -> Xen -> Dom0 shell
```

If that works, Chapter 135 starts a DomU.

## 134.2  Reality check for i.MX6ULL

The i.MX6ULL is a good learning target for Xen mechanics, but not a comfortable virtualization product target.

| Property | i.MX6ULL consequence |
|----------|----------------------|
| One Cortex-A7 core | Xen can time-slice domains, but there is no physical parallelism. |
| 512 MiB RAM on our board | Dom0 must be small. DomU must be tiny. |
| No spare A-core | Jailhouse-style static CPU partitioning is not useful here. |
| Real board DTB | Xen and Dom0 must agree on UART, GIC, timer, memory, and devices. |
| DMA-capable devices | Device assignment must be conservative without an IOMMU story. |

The point is not to make the i.MX6ULL a server. The point is to see HYP mode, stage-2 translation, Dom0, and real boot handoff on the same board used in the rest of the book.

## 134.3  Prerequisites

You should already have:

- Chapter 24's TFTP/NFS workflow or a working FAT boot partition.
- Chapter 26's mainline Linux boot on the i.MX6ULL.
- Chapter 29's initramfs skills.
- Chapter 132's Xen-in-QEMU result.
- A serial console that captures the full U-Boot and Linux log.

Use serial logging. Hypervisor bring-up without a saved log is self-inflicted fog.

Host tools:

```sh
$ sudo apt install build-essential git bison flex bc libssl-dev \
    device-tree-compiler u-boot-tools gcc-arm-linux-gnueabihf
```

If your book workspace already uses a project-local toolchain, keep using it:

```sh
$ export CROSS_COMPILE=$HOME/imx6ull/toolchains/arm-gnu-toolchain-*/bin/arm-none-linux-gnueabihf-
$ export ARCH=arm
```

In command examples below, adjust `CROSS_COMPILE` to match your actual toolchain prefix.

## 134.4  Artifact layout

Use one workspace directory for this chapter:

```sh
$ mkdir -p ~/imx6ull/xen-lab/{src,out,boot,logs}
$ cd ~/imx6ull/xen-lab
```

The final boot directory will contain:

```text
boot/
  xen
  zImage-dom0
  dom0-initramfs.cpio.gz
  imx6ull-mini-xen.dtb
  boot-xen.scr
```

The names are intentionally boring. During failure analysis, boring filenames are kindness.

## 134.5  The boot contract

On 32-bit ARM, Xen follows the Linux `zImage` boot protocol closely enough that U-Boot can jump to it like a kernel image. The important differences:

- Xen must be entered in **HYP mode**.
- Xen requires **Device Tree**.
- U-Boot passes the DTB address in `r2`.
- Dom0 kernel and ramdisk are not passed as the normal Linux initramfs argument. They are described as **multiboot modules** in `/chosen`.

So U-Boot does not boot Dom0 directly. It boots Xen and hands Xen a DTB that says:

```text
/chosen
  xen,xen-bootargs = "..."
  xen,dom0-bootargs = "..."
  module@...  -> Dom0 kernel
  module@...  -> Dom0 initramfs
```

Xen reads those nodes, creates Domain 0, and starts the Dom0 kernel.

## 134.6  Pick memory addresses

Our board DRAM starts at `0x80000000`. Use conservative, separated load addresses:

```text
0x80800000  Xen
0x83000000  DTB
0x84000000  Dom0 zImage
0x88000000  Dom0 initramfs
```

Why these numbers:

- they are inside DRAM,
- they avoid the low DRAM region where boot code often works,
- they leave room between artifacts,
- they are easy to recognize in logs.

If your Dom0 initramfs is large, move it higher or make it smaller. Do not guess. Check sizes:

```sh
$ ls -lh boot/
```

## 134.7  Build Xen

Use a current supported Xen release. At the time this chapter was drafted, the Xen 4.21 series is current, and Xen 4.20 is also a supported series. If your package manager or release tarball has a newer supported stable release, use it and record the exact version in your lab notes.

```sh
$ cd ~/imx6ull/xen-lab/src
$ git clone https://github.com/xen-project/xen.git
$ cd xen
$ git checkout RELEASE-4.21.1
```

Build only the hypervisor first:

```sh
$ make XEN_TARGET_ARCH=arm32 CROSS_COMPILE=arm-none-linux-gnueabihf- dist-xen
```

Expected output artifact:

```sh
$ ls -lh xen/xen
```

Copy it:

```sh
$ cp xen/xen ~/imx6ull/xen-lab/boot/xen
```

If your Xen tree produces a differently named ARM boot image, inspect the `xen/` directory:

```sh
$ find xen -maxdepth 1 -type f -printf '%f\n' | sort
```

The artifact must be the ARM Xen image, not the host tools and not an x86 binary.

## 134.8  Build a Dom0-capable Linux kernel

Start from the same Linux tree used in Part IV. Create a separate build directory so this experiment does not disturb your normal kernel:

```sh
$ cd ~/imx6ull/linux
$ make ARCH=arm O=../linux-dom0 imx_v6_v7_defconfig
```

Enable Xen support:

```sh
$ make ARCH=arm O=../linux-dom0 menuconfig
```

Minimum options to check:

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

You do not need every Xen feature for the first boot, but Dom0 should have enough infrastructure for Chapter 135.

Build:

```sh
$ make ARCH=arm O=../linux-dom0 CROSS_COMPILE=arm-none-linux-gnueabihf- -j$(nproc) zImage dtbs
```

Copy the kernel and the normal board DTB:

```sh
$ cp ../linux-dom0/arch/arm/boot/zImage ~/imx6ull/xen-lab/boot/zImage-dom0
$ cp ../linux-dom0/arch/arm/boot/dts/nxp/imx/imx6ull-*.dtb ~/imx6ull/xen-lab/boot/
```

Rename the exact DTB you use:

```sh
$ cd ~/imx6ull/xen-lab/boot
$ cp imx6ull-your-board.dtb imx6ull-mini-xen.dtb
```

Replace `imx6ull-your-board.dtb` with the DTB that already boots native Linux on your board.

## 134.9  Build a tiny Dom0 initramfs

Dom0 should be small. Reuse the BusyBox initramfs pattern from Chapter 29.

Minimum `/init`:

```sh
#!/bin/sh
mount -t proc none /proc
mount -t sysfs none /sys
mount -t devtmpfs none /dev
echo
echo "Dom0 is alive"
uname -a
cat /proc/cmdline
exec sh
```

Build the archive:

```sh
$ cd ~/imx6ull/xen-lab/dom0-root
$ find . -print0 | cpio --null -ov --format=newc | gzip -9 > ../boot/dom0-initramfs.cpio.gz
```

Keep it tiny:

```sh
$ ls -lh ../boot/dom0-initramfs.cpio.gz
```

If it is tens of megabytes, stop and shrink it. The first Dom0 needs a shell, not a distribution.

## 134.10  Prepare the DTB

We will let U-Boot edit the DTB at boot time. That keeps the original board DTB reusable for native Linux.

The DTB must contain:

- the normal board description,
- `/chosen/xen,xen-bootargs`,
- `/chosen/xen,dom0-bootargs`,
- a Dom0 kernel module node,
- a Dom0 ramdisk module node.

The module nodes must include:

- `compatible`,
- `reg`,
- optional `bootargs` if you choose per-module bootargs.

The `reg` property must use the address-cell and size-cell format expected by the DTB. Many 32-bit ARM board DTBs use:

```dts
#address-cells = <1>;
#size-cells = <1>;
```

For those, a module looks like:

```dts
reg = <0x84000000 0x006a1234>;
```

Some generated or 64-bit-oriented trees use more cells. In that case the same module may need:

```dts
reg = <0x0 0x84000000 0x0 0x006a1234>;
```

Check your actual DTB before writing the U-Boot script:

```sh
$ dtc -I dtb -O dts imx6ull-mini-xen.dtb | grep -n "#address-cells\\|#size-cells" | head
```

This is a common source of "Xen cannot find Dom0" failures.

For the first boot, keep Xen arguments quiet but visible:

```text
console=dtuart dtuart=serial0 dom0_mem=192M dom0_max_vcpus=1
```

Dom0 arguments:

```text
console=hvc0 earlycon=xenboot root=/dev/ram0 rdinit=/init
```

`hvc0` is the Xen paravirtual console. If Dom0 prints nothing after Xen starts it, console selection is the first thing to suspect.

## 134.11  U-Boot boot script

Create `boot-xen.cmd`:

```text
setenv xen_addr_r 0x80800000
setenv fdt_addr_r 0x83000000
setenv dom0_kernel_addr_r 0x84000000
setenv dom0_ramdisk_addr_r 0x88000000

setenv xen_file xen
setenv dom0_kernel_file zImage-dom0
setenv dom0_ramdisk_file dom0-initramfs.cpio.gz
setenv fdt_file imx6ull-mini-xen.dtb

fatload mmc 0:1 ${xen_addr_r} ${xen_file}
fatload mmc 0:1 ${dom0_kernel_addr_r} ${dom0_kernel_file}
setenv dom0_kernel_size ${filesize}
fatload mmc 0:1 ${dom0_ramdisk_addr_r} ${dom0_ramdisk_file}
setenv dom0_ramdisk_size ${filesize}
fatload mmc 0:1 ${fdt_addr_r} ${fdt_file}

fdt addr ${fdt_addr_r}
fdt resize 8192

fdt set /chosen xen,xen-bootargs "console=dtuart dtuart=serial0 dom0_mem=192M dom0_max_vcpus=1"
fdt set /chosen xen,dom0-bootargs "console=hvc0 earlycon=xenboot root=/dev/ram0 rdinit=/init"

fdt mknode /chosen module@84000000
fdt set /chosen/module@84000000 compatible "multiboot,kernel" "multiboot,module"
fdt set /chosen/module@84000000 reg <0x84000000 ${dom0_kernel_size}>

fdt mknode /chosen module@88000000
fdt set /chosen/module@88000000 compatible "multiboot,ramdisk" "multiboot,module"
fdt set /chosen/module@88000000 reg <0x88000000 ${dom0_ramdisk_size}>

fdt print /chosen
bootz ${xen_addr_r} - ${fdt_addr_r}
```

This script assumes the board DTB uses one address cell and one size cell for these `/chosen` module nodes. That is the normal shape for many 32-bit ARM board trees. If your DTB uses a different cell width, change both `fdt set ... reg` lines before booting.

Build the script:

```sh
$ mkimage -A arm -T script -C none -n "boot Xen on i.MX6ULL" \
    -d boot-xen.cmd boot-xen.scr
```

Copy `boot/` files to the FAT boot partition.

> **Why `fdt print /chosen` before boot?** Because it shows the exact handoff Xen will see. If Xen cannot find Dom0, the answer is often visible there.

## 134.12  First boot

At the U-Boot prompt:

```text
=> load mmc 0:1 ${scriptaddr} boot-xen.scr
=> source ${scriptaddr}
```

Capture the full serial log:

```sh
$ picocom -b 115200 /dev/ttyUSB0 | tee ~/imx6ull/xen-lab/logs/xen-dom0-first-boot.log
```

Expected stages:

1. U-Boot loads four files.
2. `fdt print /chosen` shows Xen and Dom0 bootargs plus two module nodes.
3. Xen prints before Linux.
4. Xen reports CPU, GIC, timer, and memory.
5. Xen says it is loading or booting Domain 0.
6. Linux Dom0 prints with `hvc0` console.
7. `/init` prints `Dom0 is alive`.

If stage 3 never appears, U-Boot did not successfully enter Xen.

If stage 3 appears but stage 5 does not, Xen is alive but cannot create Dom0.

If stage 5 appears but Dom0 prints nothing, debug Dom0 console and kernel config.

## 134.13  Verification commands in Dom0

Inside the Dom0 shell:

```sh
# uname -a
# cat /proc/cmdline
# ls /proc/xen
# ls /sys/hypervisor
# dmesg | grep -i xen
```

If `/proc/xen` or `/sys/hypervisor` is missing, Dom0 either lacks Xen support or did not boot as a Xen domain.

For this chapter, `xl` is optional. The toolstack is useful in Chapter 135, but the first proof is lower-level: Dom0 knows it is running under Xen.

## 134.14  Troubleshooting

### U-Boot rejects the Xen image

Symptoms:

```text
Bad Linux ARM zImage magic
```

or no jump at all.

Check:

- you copied the ARM Xen image, not a host binary,
- `file boot/xen` on the host,
- Xen build target was `XEN_TARGET_ARCH=arm32`,
- the image was not corrupted by text-mode copy.

If your U-Boot cannot boot the raw Xen artifact with `bootz`, use a FIT image in a later pass. Do not mix FIT debugging into the first raw-module experiment.

### Xen prints, then stops before Dom0

Most likely causes:

- missing `/chosen/module@...` nodes,
- bad `compatible` strings,
- bad `reg` address or size,
- Dom0 kernel address overlaps Xen or DTB,
- Dom0 memory too large.

Use:

```text
=> fdt print /chosen
```

before `bootz`. The DTB handoff is evidence.

### Dom0 starts but no shell appears

Most likely causes:

- wrong Dom0 `console=`,
- missing `CONFIG_HVC_XEN`,
- initramfs missing `/init`,
- `/init` not executable,
- wrong `rdinit=`.

Try Dom0 bootargs:

```text
console=hvc0 earlycon=xenboot root=/dev/ram0 rdinit=/bin/sh
```

If `/bin/sh` works, your `/init` script is the bug.

### Native Linux used UART but Dom0 uses `hvc0`

That is expected. Native Linux owns the physical UART. Dom0 under Xen normally speaks through the Xen console. Xen owns the early physical UART path.

### Xen reports not in HYP mode

Xen requires HYP mode on ARM. Check U-Boot configuration and handoff path. This is not a Linux config problem. It is a firmware/CPU-mode problem.

## 134.15  Lab

Deliverables:

1. `boot-xen.cmd`
2. `boot-xen.scr`
3. `xen`
4. `zImage-dom0`
5. `dom0-initramfs.cpio.gz`
6. `imx6ull-mini-xen.dtb`
7. `logs/xen-dom0-first-boot.log`
8. A short note with:
   - Xen version,
   - Linux commit or release,
   - U-Boot version,
   - board revision,
   - exact DTB used,
   - whether Dom0 reached shell.

The lab is complete only when the serial log proves:

```text
U-Boot -> Xen -> Dom0 Linux -> shell
```

## 134.16  Pitfalls

- **Treating Dom0 like native Linux.** Dom0 is privileged, but it is still a Xen domain.
- **Changing five things at once.** First boot uses serial console and initramfs only.
- **Using a large distro Dom0.** Save that for later. Boot the smallest possible rootfs first.
- **Forgetting exact versions.** Xen, Linux, and U-Boot version drift matters.
- **Assuming device assignment is safe.** Booting Dom0 says nothing about safe DMA isolation.
- **Skipping the DTB print.** If the `/chosen` nodes are wrong, Xen cannot guess your intent.

## 134.17  Going deeper

- Xen ARM booting documentation: `docs/misc/arm/booting.txt`.
- Xen ARM Device Tree boot modules: `docs/misc/arm/device-tree/booting.txt`.
- Xen command-line documentation.
- U-Boot `bootz`, `fdt`, and FIT image documentation.
- Chapter 135: DomU Linux on i.MX6ULL.
- Chapter 136: devices, memory, and DMA boundaries.
