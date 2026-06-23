---
chapter: 137
title: Jailhouse in QEMU ARM64
part: IX - Applied virtualization and mixed-criticality systems
estimated_pages: 34
status: draft
---

# Chapter 137: Jailhouse in QEMU ARM64

> **What:** boot a QEMU ARM64 Linux system, enable Jailhouse, and start a small inmate cell.
>
> **Why:** Jailhouse is useful only when you understand what it removes from Linux and gives to another cell.
>
> **Focus:** no magic VM language. We will track CPUs, RAM, MMIO, interrupts, and console ownership.

## 137.1  Why this chapter is not on i.MX6ULL

The i.MX6ULL has one Cortex-A7 core.

That matters.

Jailhouse is a partitioning hypervisor. Its cleanest teaching example is:

```text
CPU 0..N: Linux root cell
CPU M: inmate cell
some RAM: Linux root cell
some RAM: inmate cell
some devices: Linux root cell
some devices: inmate cell
```

On a one-core chip, there is no spare CPU to hand to the inmate. You can still study concepts, but the lab becomes awkward and less useful.

QEMU ARM64 can give us a fake machine with many CPUs. The official Jailhouse QEMU ARM64 configuration uses a virtual ARM machine with 1 GiB of RAM and multiple virtual CPUs. That is a much better first lab.

This is the honest path:

```text
first: QEMU ARM64, so the model is visible
later: real board only when the hardware shape fits
```

The goal is not to pretend QEMU is your product. The goal is to learn the Jailhouse workflow without fighting board bring-up at the same time.

## 137.2  Jailhouse in one picture

Xen boots before Linux:

```text
firmware -> Xen -> Dom0 Linux -> DomU guests
```

Jailhouse starts after Linux:

```text
firmware -> Linux -> jailhouse.ko -> Jailhouse active -> inmate cells
```

Before Jailhouse is enabled, Linux owns the whole machine.

After Jailhouse is enabled, Linux becomes the **root cell**. Jailhouse then blocks Linux from touching resources that belong to other cells.

That is the core idea:

```text
Linux does not become stronger.
Linux gives resources away.
Jailhouse enforces the new ownership table.
```

Jailhouse is not trying to emulate a PC for each guest. It is trying to partition real hardware.

## 137.3  Vocabulary we need

**Root cell**

The Linux system that booted first. It loads `jailhouse.ko`, enables Jailhouse, creates inmate cells, and remains responsible for management.

**Inmate cell**

The isolated workload. It can be bare-metal code, an RTOS, or sometimes a small Linux guest.

**Cell config**

A compiled hardware ownership table. It describes CPUs, memory regions, interrupt controllers, PCI or MMIO devices, and console settings.

**Root-cell config**

The system-wide config used when enabling Jailhouse. On QEMU ARM64 this is commonly built from `configs/arm64/qemu-arm64.c`.

**Inmate config**

The config for one non-root cell. On the QEMU ARM64 demo path this is commonly built from `configs/arm64/qemu-arm64-inmate-demo.c`.

**Inmate binary**

The code loaded into the inmate cell. For the first demo this is usually a small test binary such as `gic-demo.bin`.

## 137.4  What the QEMU ARM64 demo proves

The first Jailhouse demo should prove only five things:

1. Linux can boot on the QEMU ARM64 virtual machine.
2. Linux can load the Jailhouse kernel module.
3. Jailhouse can be enabled with the QEMU ARM64 root-cell config.
4. A non-root inmate cell can be created, loaded, and started.
5. Linux root cell stays alive while the inmate runs.

Do not add Zephyr yet.

Do not add a second Linux yet.

Do not edit the cell config yet.

First make the known-good demo work. Then change one thing at a time.

## 137.5  Workspace

Use a separate workspace because this lab will create images, logs, configs, and notes:

```sh
$ mkdir -p ~/imx6ull/jailhouse-lab/{src,build,logs,notes}
$ cd ~/imx6ull/jailhouse-lab
```

Record host versions:

```sh
$ uname -a | tee logs/host-uname.txt
$ lsb_release -a 2>/dev/null | tee logs/host-release.txt
```

If your distribution does not have `lsb_release`, use:

```sh
$ cat /etc/os-release | tee logs/host-release.txt
```

## 137.6  Install host tools

Install the tools used by the demo and by later inspection:

```sh
$ sudo apt update
$ sudo apt install qemu-system-aarch64 git make gcc-aarch64-linux-gnu \
    device-tree-compiler flex bison libssl-dev bc cpio rsync file \
    docker.io
```

Check the important tools:

```sh
$ qemu-system-aarch64 --version | tee logs/qemu-version.txt
$ aarch64-linux-gnu-gcc --version | head -n 1 | tee logs/aarch64-gcc-version.txt
$ dtc --version | tee logs/dtc-version.txt
```

The upstream Jailhouse README says the ARM64 QEMU demo needs QEMU 3.0 or newer. Modern Ubuntu and Debian releases are normally far beyond that.

The `jailhouse-images` reference flow uses `kas-container`, so Docker must also work for your normal user or through `sudo`. Check:

```sh
$ docker --version
$ docker run --rm hello-world
```

If Docker permission fails, fix that before starting the image build. Do not debug Jailhouse while Docker itself is broken.

## 137.7  Get the source

Clone Jailhouse:

```sh
$ cd ~/imx6ull/jailhouse-lab/src
$ git clone https://github.com/siemens/jailhouse.git
$ cd jailhouse
$ git rev-parse HEAD | tee ../../logs/jailhouse-commit.txt
```

Now find the QEMU ARM64 configs:

```sh
$ ls configs/arm64 | tee ../../logs/jailhouse-arm64-configs.txt
$ ls inmates/demos/arm64 | tee ../../logs/jailhouse-arm64-inmates.txt
```

Expected names may include:

```text
qemu-arm64.c
qemu-arm64-inmate-demo.c
gic-demo.c
```

Do not worry if the exact list changes across releases. The concepts do not change:

```text
root-cell config
inmate-cell config
inmate binary
```

## 137.8  Use the reference image path first

Jailhouse has a lot of moving parts:

```text
QEMU command line
Linux kernel image
root filesystem image
Jailhouse kernel module
Jailhouse user tool
root-cell config
inmate config
inmate binary
```

For the first successful run, use the Jailhouse reference image project:

```sh
$ cd ~/imx6ull/jailhouse-lab/src
$ git clone https://github.com/siemens/jailhouse-images.git
$ cd jailhouse-images
$ git rev-parse HEAD | tee ../../logs/jailhouse-images-commit.txt
```

The reference image project is built around `kas-container`. It provides a menu for virtual targets:

```sh
$ ./kas-container menu
```

Select the QEMU ARM64 Jailhouse target from the menu. After the image is generated, start it with:

```sh
$ ./start-qemu.sh arm64
```

This is intentionally the shortest path. The first time, your job is to get a working root cell and inmate cell, not to debug every package in the image build.

Expect this build to download and compile a full reference image stack. It is much heavier than building the tiny BusyBox initramfs in Chapter 129.

If the menu names have changed in your release, look at the repository README and `conf/multiconfig`:

```sh
$ ls conf/multiconfig
$ grep -R "arm64" -n conf scripts start-qemu.sh
```

Write down the exact target name you used:

```text
Jailhouse image target:
```

That line belongs in your lab notes.

## 137.9  The manual QEMU shape

The reference image scripts hide details. Before running Jailhouse commands, understand the QEMU machine they are creating.

The upstream ARM64 demo has this shape:

```sh
$ qemu-system-aarch64 \
    -cpu cortex-a57 \
    -smp 16 \
    -m 1G \
    -machine virt,gic-version=3,virtualization=on,its=off \
    -nographic \
    -netdev user,id=net \
    -device virtio-net-device,netdev=net \
    -drive file=LinuxInstallation.img,format=raw,id=disk,if=none \
    -device virtio-blk-device,drive=disk \
    -kernel Image \
    -append "root=/dev/vda1 mem=768M"
```

Do not copy this blindly yet. Use it as a map.

Important pieces:

| Option | Meaning |
|--------|---------|
| `-cpu cortex-a57` | Run an ARMv8-A CPU model. |
| `-smp 16` | Create sixteen virtual CPUs. |
| `-m 1G` | Give the machine 1 GiB RAM. |
| `virtualization=on` | Expose virtualization support to the guest. |
| `gic-version=3` | Use a GICv3 interrupt controller. |
| `its=off` | Match the demo platform expectation. |
| `mem=768M` | Leave the top RAM area unused by Linux. |

That last line is critical.

Linux sees only 768 MiB:

```text
0x40000000 .. lower RAM used by Linux
```

The rest can be used by Jailhouse and inmate cells:

```text
top RAM reserved for Jailhouse and inmates
```

If Linux uses the same memory as an inmate, isolation is already broken. The system may crash before you learn anything useful.

## 137.10  Inspect the root-cell config

Open the QEMU ARM64 root-cell config:

```sh
$ cd ~/imx6ull/jailhouse-lab/src/jailhouse
$ less configs/arm64/qemu-arm64.c
```

Find the comment near the top:

```text
NOTE: Add "mem=768M" to the kernel command line.
```

That comment is not decoration. It is the contract between Linux boot arguments and the Jailhouse memory map.

Now search for the hypervisor memory region:

```sh
$ grep -n "hypervisor_memory" -A5 configs/arm64/qemu-arm64.c
```

You should see a physical start address and a size.

Write it in your notes:

```text
Jailhouse hypervisor memory:
```

Now search for CPUs:

```sh
$ grep -n "cpus" -A4 configs/arm64/qemu-arm64.c
```

On this demo config, the CPU bitmap represents the CPUs available to the root cell config. A bitmap of `0xffff` means sixteen CPUs are described.

This is why the demo QEMU command uses:

```text
-smp 16
```

The QEMU command and the cell config must describe the same machine.

## 137.11  Inspect the inmate config

Now open the inmate config:

```sh
$ less configs/arm64/qemu-arm64-inmate-demo.c
```

Look for:

```text
.name
.cpus
.mem_regions
.irqchips
.console
```

The inmate config answers four practical questions:

```text
Which CPU can the inmate run on?
Where is the inmate RAM?
Which interrupts can reach the inmate?
How does the inmate print?
```

This is the file you will annotate later.

## 137.12  Boot the reference image

Start the reference image:

```sh
$ cd ~/imx6ull/jailhouse-lab/src/jailhouse-images
$ ./start-qemu.sh arm64 | tee ../../logs/qemu-arm64-boot.txt
```

Login using the credentials documented by the image project.

Inside the QEMU guest, collect basic evidence:

```sh
# uname -a
# cat /proc/cmdline
# nproc
# free -m
```

Expected ideas:

```text
many CPUs visible before Jailhouse is enabled
kernel command line contains mem=768M
memory is less than the full 1 GiB QEMU machine
```

The exact numbers depend on the image, but the shape should match.

## 137.13  Find Jailhouse inside the guest

Inside the QEMU guest:

```sh
# which jailhouse
# find /lib/modules -name "jailhouse.ko*"
# find /usr -name "*.cell" | grep jailhouse
# find /usr -name "gic-demo.bin" -o -name "*demo*.bin"
```

Common locations include:

```text
/usr/share/jailhouse/cells/
/usr/libexec/jailhouse/
/lib/modules/.../extra/
```

Do not memorize paths. Learn to find the artifacts.

Record them:

```text
jailhouse tool:
jailhouse module:
root-cell config:
inmate-cell config:
inmate binary:
```

## 137.14  Enable Jailhouse

Load the module:

```sh
# modprobe jailhouse
```

If that fails, check:

```sh
# dmesg | tail -n 80
# uname -r
# find /lib/modules/$(uname -r) -name "jailhouse.ko*"
```

The module must match the running kernel.

Now enable Jailhouse with the QEMU ARM64 root-cell config:

```sh
# jailhouse enable /path/to/qemu-arm64.cell
```

Replace the path with the real path you found in the image.

Collect evidence:

```sh
# dmesg | tail -n 120
# jailhouse cell list
```

Expected concept:

```text
Jailhouse enabled
root cell listed
Linux still responsive
```

If the guest freezes here, do not continue. Debug the enable step first.

## 137.15  What changed after enable

Before enable:

```text
Linux kernel controls the whole virtual machine.
```

After enable:

```text
Jailhouse controls the partition boundaries.
Linux is still running, but only as the root cell.
```

This distinction matters for debugging.

If Linux tries to use memory that no longer belongs to it, Jailhouse can block that access.

If an inmate tries to touch a device that does not belong to it, Jailhouse can block that access.

If the cell config is wrong, the wrong thing gets blocked or the wrong thing is allowed.

So the cell config is not a helper file. It is the security boundary.

## 137.16  Create the inmate cell

Create the demo inmate:

```sh
# jailhouse cell create /path/to/qemu-arm64-inmate-demo.cell
```

List cells:

```sh
# jailhouse cell list
```

Expected concept:

```text
root cell exists
inmate cell exists
inmate not running yet
```

Creating a cell builds the partition. It does not mean code is running inside it.

## 137.17  Load and start the inmate

Load the demo binary:

```sh
# jailhouse cell load inmate-demo /path/to/gic-demo.bin
```

Start it:

```sh
# jailhouse cell start inmate-demo
```

Check the cell list:

```sh
# jailhouse cell list
```

Expected concept:

```text
inmate-demo running
root Linux still responsive
```

Depending on the demo image, output may appear on the serial console, the Jailhouse console, or the QEMU terminal. Check:

```sh
# jailhouse console
# dmesg | tail -n 120
```

The exact demo output is less important than the state transition:

```text
created -> loaded -> running
```

## 137.18  Stop and disable

Stop the inmate if the demo supports shutdown:

```sh
# jailhouse cell shutdown inmate-demo
```

Destroy the cell:

```sh
# jailhouse cell destroy inmate-demo
```

Disable Jailhouse:

```sh
# jailhouse disable
```

If a running cell prevents disable, stop or destroy the cell and run disable again.

Final evidence:

```sh
# jailhouse cell list
# dmesg | tail -n 120
```

The clean development loop is:

```text
enable root-cell config
create inmate
load inmate binary
start inmate
stop inmate
destroy inmate
disable Jailhouse
```

## 137.19  Build the mental map

Draw this in your notes:

```text
QEMU virt machine

RAM: 1 GiB total
  lower area: Linux root cell
  top area: Jailhouse plus inmates

CPUs: 16 virtual CPUs
  root cell: Linux management side
  inmate: CPU subset from inmate config

Interrupt controller:
  GICv3

Console:
  root Linux console
  Jailhouse debug console
  inmate console path
```

Then fill in real addresses from the configs.

This is the moment where Jailhouse stops being a command sequence and becomes an ownership table.

## 137.20  Failure lab A: remove the memory limit

This is a thinking lab. Do it only in QEMU, not on a real board.

Make a copy of the QEMU launch command or script. Remove:

```text
mem=768M
```

Boot again and try to enable Jailhouse.

Expected result:

```text
enable fails
or the guest becomes unstable
or Jailhouse reports a memory conflict
```

Reason:

```text
Linux may use memory that the cell config expects to reserve.
```

Put `mem=768M` back.

Lesson:

```text
reserved memory is not optional
```

## 137.21  Failure lab B: wrong CPU count

Make a copy of the QEMU launch command and reduce:

```text
-smp 16
```

to:

```text
-smp 4
```

Boot and try the same root-cell config.

Expected result:

```text
enable fails
or later cell creation fails
```

Reason:

```text
the config describes a different CPU layout than the machine provides
```

Lesson:

```text
cell configs must match the hardware
```

## 137.22  Failure lab C: wrong inmate binary

Create the inmate cell, but load the wrong binary or a random file:

```sh
# jailhouse cell create /path/to/qemu-arm64-inmate-demo.cell
# jailhouse cell load inmate-demo /bin/ls
# jailhouse cell start inmate-demo
```

Expected result:

```text
load fails
or start fails
or the inmate crashes immediately
```

Reason:

```text
an inmate binary is not a Linux program
```

It is code linked for the inmate entry address and runtime environment.

Lesson:

```text
cell load is not execve
```

## 137.23  Annotate the root-cell config

Create a note file:

```sh
$ cp src/jailhouse/configs/arm64/qemu-arm64.c notes/qemu-arm64-annotated.c
```

Add comments beside:

```text
hypervisor_memory
debug_console
platform_info.arm.gic_version
platform_info.arm.gicd_base
platform_info.arm.gicr_base
root_cell.name
cpus
mem_regions
irqchips
pci_devices
```

Your comments should answer:

```text
what is this resource?
who owns it?
why is it here?
which QEMU option must match it?
```

This is more valuable than memorizing commands.

## 137.24  Annotate the inmate config

Copy the inmate config:

```sh
$ cp src/jailhouse/configs/arm64/qemu-arm64-inmate-demo.c notes/qemu-arm64-inmate-annotated.c
```

Add comments beside:

```text
cell name
CPU bitmap
memory regions
communication region
interrupt chip
console
```

For each memory region, classify it:

```text
RAM
MMIO
communication
loadable area
read only
read write
executable
```

The flags tell you what the inmate is allowed to do with that region.

## 137.25  Why this is useful in real products

Jailhouse is useful when your product has a clear static split.

Good shape:

```text
Linux UI and network stack on CPU 0..2
control workload on CPU 3
dedicated device for control workload
shared memory protocol between the two sides
```

Weak shape:

```text
one CPU
many shared devices
unclear ownership
need to start and stop guests dynamically
need rich virtual hardware
```

For the weak shape, Xen, Linux processes, containers, PREEMPT_RT, or a separate MCU may be better.

The professional skill is not "use a hypervisor". The professional skill is choosing the smallest boundary that solves the product problem.

## 137.26  Lab deliverables

Create:

```text
~/imx6ull/jailhouse-lab/logs/host-uname.txt
~/imx6ull/jailhouse-lab/logs/qemu-version.txt
~/imx6ull/jailhouse-lab/logs/jailhouse-commit.txt
~/imx6ull/jailhouse-lab/logs/jailhouse-images-commit.txt
~/imx6ull/jailhouse-lab/logs/qemu-arm64-boot.txt
~/imx6ull/jailhouse-lab/notes/qemu-arm64-annotated.c
~/imx6ull/jailhouse-lab/notes/qemu-arm64-inmate-annotated.c
```

Also write this short report:

```text
QEMU command:
Linux cmdline:
root-cell config path:
inmate config path:
inmate binary path:
Jailhouse enable result:
cell list after create:
cell list after start:
cell list after cleanup:
one failure tested:
what failed:
why it failed:
```

The chapter is complete when you can explain this sentence without hand waving:

```text
Jailhouse did not boot a VM. It changed the hardware ownership table while Linux was running.
```

## 137.27  Troubleshooting

**`modprobe jailhouse` fails**

The module may not match the running kernel.

Check:

```sh
# uname -r
# find /lib/modules/$(uname -r) -name "jailhouse.ko*"
# dmesg | tail -n 80
```

**`jailhouse enable` freezes the guest**

The root-cell config likely does not match the QEMU machine or Linux memory reservation.

Check:

```text
QEMU RAM size
QEMU CPU count
QEMU GIC version
kernel command line
root-cell config
```

**`cell create` fails**

The inmate config may reference CPUs, memory, or IRQs not available to that cell.

Check the inmate config and the root-cell config together.

**The inmate starts but prints nothing**

The inmate may still be running. The console may be somewhere else.

Check:

```sh
# jailhouse cell list
# jailhouse console
# dmesg | tail -n 120
```

**`jailhouse disable` fails**

An inmate may still be running.

Stop or destroy non-root cells first:

```sh
# jailhouse cell list
# jailhouse cell shutdown inmate-demo
# jailhouse cell destroy inmate-demo
# jailhouse disable
```

## 137.28  What comes next

You have now used the official style of Jailhouse lab:

```text
Linux root cell
Jailhouse module
root-cell config
inmate-cell config
inmate binary
cell lifecycle commands
```

Chapter 138 removes one more layer of magic. Instead of running the stock demo inmate, we will build and reason about a tiny non-Linux inmate workload.
