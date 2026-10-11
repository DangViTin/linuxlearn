---
chapter: 128
title: QEMU as a virtual hardware model
part: IX - Applied virtualization and mixed-criticality systems
estimated_pages: 26
status: draft
---

<span id="chapter-128-qemu-as-a-virtual-hardware-lab"></span>
# Chapter 128: QEMU as a virtual hardware model

> **What:** install QEMU, create 32-bit and 64-bit Arm virtual machines, inspect QEMU's generated Device Tree, and attach GDB before any kernel exists.
>
> **Why:** hypervisor bring-up fails before Linux can help you. QEMU gives us a board we can reset in one second, script exactly, and inspect from the outside.
>
> **Focus:** a QEMU command line is a hardware description. Treat it like a schematic: CPU, RAM, UART, interrupt controller, timer, storage, and firmware are all explicit choices.
> **QEMU:** a machine emulator. `qemu-system-arm` creates a complete Arm machine, not just one process.
> **virt machine:** QEMU's generic virtual Arm board. It is designed for virtual machines, not for matching one physical board.
> **GDB remote stub:** a tiny debug server built into QEMU that lets GDB halt and inspect the emulated CPU.

## 128.1  What QEMU is, and what it is not

QEMU can emulate several kinds of things:

| Program | Meaning |
|---------|---------|
| `qemu-system-arm` | emulates a complete 32-bit Arm machine |
| `qemu-system-aarch64` | emulates a complete 64-bit Arm machine, and can also run some 32-bit Arm machines |
| `qemu-arm` | runs one Arm Linux user-space program on the host |

This chapter uses **system emulation**:

```text
host Linux
  qemu-system-arm
    virtual CPU
    virtual RAM
    virtual UART
    virtual GIC
    virtual timer
    generated DTB
```

It does not emulate the i.MX6ULL. The QEMU `virt` board gives us a simpler Arm hardware model for examining Linux and hypervisor boot contracts. Its successful boot cannot establish compatibility with the MINI's controllers or wiring.

What QEMU `virt` gives us:

- configurable RAM,
- configurable CPU count,
- GIC interrupt controller,
- ARM architectural timer,
- PL011 UART,
- virtio devices,
- generated Device Tree,
- a platform supported by Linux, U-Boot, Xen, and Jailhouse examples.

What it does **not** give us:

- i.MX6ULL IOMUXC,
- MMDC DDR training,
- FEC Ethernet,
- SNVS,
- OCOTP fuses,
- HAB,
- the Point Atom board schematic.

Use QEMU to learn the contract. Use i.MX6ULL to learn the board.

## 128.2  Install tools

On Ubuntu or Debian:

```sh
$ sudo apt update
$ sudo apt install qemu-system-arm qemu-system-aarch64 gdb-multiarch \
    device-tree-compiler u-boot-tools file
```

Create the workspace:

```sh
$ mkdir -p ~/imx6ull/virt-lab/{boot,logs,notes}
$ cd ~/imx6ull/virt-lab
```

Record tool versions:

```sh
$ qemu-system-arm --version | tee logs/qemu-system-arm-version.txt
$ qemu-system-aarch64 --version | tee logs/qemu-system-aarch64-version.txt
$ gdb-multiarch --version | head -1 | tee logs/gdb-version.txt
$ dtc --version | tee logs/dtc-version.txt
```

hypervisor examples are version-sensitive. Keep the versions with the logs.

## 128.3  Start a 32-bit Arm board with no kernel

Run:

```sh
$ qemu-system-arm \
    -M virt \
    -cpu cortex-a15 \
    -m 256M \
    -nographic
```

Expected behavior: not much. There is no kernel, no firmware, and no bootloader. QEMU created a machine and then had nothing useful to execute.

Quit:

```text
Ctrl-a x
```

In `-nographic` mode, `Ctrl-a` is QEMU's escape prefix. `x` exits.

Now write down what each option means:

| Option | Meaning |
|--------|---------|
| `-M virt` | create the generic Arm virtual board |
| `-cpu cortex-a15` | use a 32-bit ARMv7-A CPU model |
| `-m 256M` | give the guest 256 MiB RAM |
| `-nographic` | route guest serial and QEMU monitor through the terminal |

The machine did not boot, but this was not a failure. It proved QEMU is installed and the virtual board can be created.

## 128.4  Start a 64-bit Arm board

The later Jailhouse example needs spare CPUs. ARM64 QEMU supplies a multicore model:

```sh
$ qemu-system-aarch64 \
    -M virt \
    -cpu cortex-a53 \
    -smp 4 \
    -m 1024M \
    -nographic
```

Quit with `Ctrl-a x`.

New option:

| Option | Meaning |
|--------|---------|
| `-smp 4` | create four virtual CPUs |

The i.MX6ULL cannot give us four A-cores. QEMU can. That is why Jailhouse appears first on QEMU ARM64 instead of on i.MX6ULL.

## 128.5  Ask QEMU what machines it knows

List supported 32-bit Arm machines:

```sh
$ qemu-system-arm -machine help | less
```

Search for `virt`:

```sh
$ qemu-system-arm -machine help | grep virt
```

List CPU models:

```sh
$ qemu-system-arm -cpu help | less
```

This is the QEMU equivalent of opening a board catalog. We choose `virt` because it is generic and maintained for virtual machine use.

## 128.6  Dump the generated Device Tree

QEMU can generate the DTB for the virtual board and write it to a file:

```sh
$ cd ~/imx6ull/virt-lab
$ qemu-system-arm \
    -M virt,dumpdtb=boot/qemu-virt-arm.dtb \
    -cpu cortex-a15 \
    -m 256M \
    -nographic
```

If QEMU sits after dumping, quit with `Ctrl-a x`.

Convert to DTS:

```sh
$ dtc -I dtb -O dts -o boot/qemu-virt-arm.dts boot/qemu-virt-arm.dtb
```

Inspect:

```sh
$ less boot/qemu-virt-arm.dts
```

Find the root compatible:

```sh
$ grep -n "compatible" boot/qemu-virt-arm.dts | head
```

Find memory:

```sh
$ grep -n "memory@" boot/qemu-virt-arm.dts
```

Find CPUs:

```sh
$ grep -n "cpu@" boot/qemu-virt-arm.dts
```

Find serial:

```sh
$ grep -n -A6 -B2 "pl011" boot/qemu-virt-arm.dts
```

Find interrupt controller:

```sh
$ grep -n -A10 -B2 "interrupt-controller" boot/qemu-virt-arm.dts | head -40
```

Find timer:

```sh
$ grep -n -A10 -B2 "timer" boot/qemu-virt-arm.dts | head -40
```

This DTB is the "schematic" Linux will read in Chapter 129.

## 128.7  Prove RAM size changes the DTB

Dump a second DTB with 512 MiB:

```sh
$ qemu-system-arm \
    -M virt,dumpdtb=boot/qemu-virt-arm-512m.dtb \
    -cpu cortex-a15 \
    -m 512M \
    -nographic
```

Convert:

```sh
$ dtc -I dtb -O dts -o boot/qemu-virt-arm-512m.dts boot/qemu-virt-arm-512m.dtb
```

Compare memory nodes:

```sh
$ grep -n -A4 "memory@" boot/qemu-virt-arm.dts
$ grep -n -A4 "memory@" boot/qemu-virt-arm-512m.dts
```

The hardware description changed because the virtual hardware changed. This is exactly what happens on real boards too, just with a DTS file maintained by humans instead of generated by QEMU.

## 128.8  Halt the virtual CPU and attach GDB

Start QEMU halted:

```sh
$ qemu-system-arm \
    -M virt \
    -cpu cortex-a15 \
    -m 256M \
    -nographic \
    -S -s
```

Options:

| Option | Meaning |
|--------|---------|
| `-S` | create the machine but do not start the CPU |
| `-s` | open GDB server on TCP port 1234 |

In another terminal:

```sh
$ gdb-multiarch
(gdb) set architecture arm
(gdb) target remote :1234
(gdb) info registers
(gdb) x/8i $pc
```

Save the transcript:

```gdb
(gdb) set logging file logs/gdb-qemu-no-kernel.txt
(gdb) set logging enabled on
(gdb) info registers
(gdb) x/8i $pc
(gdb) set logging enabled off
```

Continue:

```gdb
(gdb) c
```

Stop QEMU with `Ctrl-a x`.

There is still no kernel. That is the point. We have proven that GDB can attach before any operating system exists.

## 128.9  Use the QEMU monitor

Start QEMU with a monitor on stdio:

```sh
$ qemu-system-arm \
    -M virt \
    -cpu cortex-a15 \
    -m 256M \
    -nographic \
    -monitor stdio
```

Try:

```text
(qemu) info version
(qemu) info registers
(qemu) info mtree
(qemu) quit
```

`info mtree` is useful later. It shows QEMU's memory map from the emulator side.

Save a copy:

```text
(qemu) log none
```

for most examples we use the serial console, not the monitor, but knowing the monitor exists is useful when a guest is silent.

## 128.10  The virtual board memory map

Use:

```text
(qemu) info mtree
```

Look for:

- RAM,
- UART MMIO,
- GIC MMIO,
- virtio MMIO,
- flash or firmware regions if present.

This is the QEMU-side equivalent of a reference manual memory map. In Chapter 129, Linux will show its view through `/proc/iomem`. Comparing the two is a good sanity check.

## 128.11  What to save

After this chapter, your workspace should contain:

```text
boot/
  qemu-virt-arm.dtb
  qemu-virt-arm.dts
  qemu-virt-arm-512m.dtb
  qemu-virt-arm-512m.dts
logs/
  qemu-system-arm-version.txt
  qemu-system-aarch64-version.txt
  gdb-version.txt
  dtc-version.txt
  gdb-qemu-no-kernel.txt
notes/
  qemu-command-line.md
```

Create `notes/qemu-command-line.md`:

```md
# QEMU command line notes

<span id="bit-arm-lab-machine"></span>
## 32-bit ARM model

Command:

...

Options:

- `-M virt`:
- `-cpu cortex-a15`:
- `-m 256M`:
- `-nographic`:

## Hardware visible in DTB

- RAM:
- UART:
- interrupt controller:
- timer:
- CPU count:
```

If you cannot fill that note, do not go to Chapter 129 yet.

<span id="lab"></span>
## 128.12  Key Notes

- A QEMU launch describes a virtual machine: CPU, memory, interrupt controller, devices and firmware are explicit inputs. Its generated DTB describes that selected model.
- System emulation and user-mode emulation have different boundaries. `qemu-system-arm` models a machine, while `qemu-arm` executes an ARM user-space program using host services.
- The `virt` machine is not an i.MX6ULL replica. It exposes boot and virtualization contracts without qualifying MINI pinmux, DDR, clocks or electrical behavior.
- Halting the virtual CPU and providing a GDB connection are independent controls. They make startup inspectable without making the model identical to physical timing.
- Machine parameters, artifact versions and logs are reproducibility evidence. Changing memory or devices changes the system being described.

## 128.13  Pitfalls

- **Expecting i.MX6ULL devices.** `virt` will not have IOMUXC, MMDC, FEC, SNVS, or OCOTP.
- **Using user-mode QEMU by accident.** `qemu-arm` is not a machine.
- **Forgetting `Ctrl-a x`.** Closing the terminal is a clumsy reset button.
- **No GDB architecture selected.** Use `set architecture arm` before inspecting a 32-bit target.
- **Treating generated DTB as permanent.** It describes the QEMU command line you used. Change the command line, regenerate it.
- **Skipping notes.** Later Xen failures often reduce to "I forgot what machine I built."

## 128.14  Going deeper

- QEMU Arm system emulator documentation.
- QEMU `virt` machine documentation.
- QEMU monitor documentation.
- GDB remote debugging documentation.
- U-Boot QEMU ARM documentation.
