---
chapter: 131
title: HYP mode, stage-2 MMU, and virtual interrupts
part: IX - Applied virtualization and mixed-criticality systems
estimated_pages: 32
status: draft
---

# Chapter 131: HYP mode, stage-2 MMU, and virtual interrupts

> **What:** understand the CPU and memory mechanisms that let Xen and Jailhouse run operating systems under another layer of control.
>
> **Why:** without HYP mode, stage-2 translation, and virtual interrupts, the later chapters become cargo-cult boot commands. This chapter gives every later log line a hook.
>
> **Focus:** a guest kernel is not a process. It is a kernel running at PL1, with a hypervisor at PL2 deciding what that kernel is allowed to see.
> **HYP mode:** the ARMv7-A hypervisor processor mode, privilege level PL2.
> **Stage-2 MMU:** the hypervisor-controlled translation from guest physical addresses to real physical addresses.
> **Virtual interrupt:** an interrupt presented to a guest by the hypervisor, whether or not it is currently a physical interrupt line.

## 131.1  Start from the non-virtualized machine

Normal ARMv7-A Linux on our board uses:

```text
User process      PL0   USR mode
Linux kernel      PL1   SVC/IRQ/ABT/UND modes
```

When a user program calls `write()`:

```text
user code
  -> svc instruction
  -> CPU enters SVC mode
  -> Linux syscall handler runs
  -> return to user
```

When UART interrupt fires:

```text
UART asserts IRQ
  -> GIC signals CPU
  -> CPU enters IRQ mode
  -> Linux IRQ handler runs
  -> return to interrupted context
```

Linux owns the privileged machine.

## 131.2  Add the hypervisor layer

With virtualization:

```text
Guest user process       PL0
Guest kernel             PL1
Hypervisor               PL2 / HYP
```

The guest kernel still runs privileged code. It still has page tables. It still handles syscalls. It still thinks it owns a machine.

But the hypervisor controls the machine behind that machine.

The hypervisor can:

- trap selected guest operations,
- control guest physical memory,
- inject virtual interrupts,
- expose or hide devices,
- pause or destroy a guest,
- switch between guests.

This is the key sentence:

```text
The guest owns a virtual machine. The hypervisor owns the real machine.
```

## 131.3  `svc`, `hvc`, and `smc`

Three instructions look similar because all are deliberate exceptions.

| Instruction | Goes to | Typical meaning |
|-------------|---------|-----------------|
| `svc` | PL1 kernel | user asks kernel |
| `hvc` | PL2 hypervisor | guest asks hypervisor |
| `smc` | Monitor/Secure World | Normal World asks Secure World |

Examples:

```text
printf()
  -> write()
  -> svc
  -> Linux syscall

Xen hypercall
  -> hvc
  -> Xen

OP-TEE call
  -> smc
  -> secure monitor / secure world
```

Do not blur these:

- HYP mode is for virtualization.
- Monitor mode is for TrustZone world switching.

They both feel "below Linux", but they solve different problems.

## 131.4  What can trap to HYP

The hypervisor can configure traps for sensitive operations. Exact controls depend on the ARM virtualization extension registers, but conceptually traps include:

- selected CP15/system register accesses,
- guest WFI/WFE behavior,
- guest interrupt-controller accesses,
- guest timer behavior,
- stage-2 translation faults,
- hypercalls through `hvc`.

Trap flow:

```text
guest kernel instruction
  -> CPU decides this action must trap
  -> CPU enters HYP mode
  -> hypervisor handler runs
  -> hypervisor emulates/allows/denies
  -> guest resumes or is killed
```

The guest may never know the trap happened.

## 131.5  Stage 1 without virtualization

Chapter 17 built a simple stage-1 mapping:

```text
virtual address -> physical address
```

Linux uses a more complex version:

```text
user VA 0x40001000 -> PA 0x81234000
kernel VA 0xc0200000 -> PA 0x80200000
```

The stage-1 page tables answer:

```text
What physical address does this virtual address mean?
Can this access read?
Can this access write?
Can this access execute?
Is it cacheable?
Is it device memory?
```

In normal Linux, the answer's physical address is real physical memory.

## 131.6  Stage 1 inside a guest

Inside a guest, stage 1 still exists:

```text
guest virtual -> guest physical
```

The guest kernel builds those page tables. From the guest's point of view, nothing strange happened.

Example:

```text
DomU process VA     0x40001000
DomU stage 1 maps   0x40001000 -> 0x80200000
```

The guest calls `0x80200000` physical.

But it is only **guest physical**.

## 131.7  Stage 2

The hypervisor adds:

```text
guest physical -> real physical
```

Full path:

```text
guest virtual -> guest physical -> real physical
```

Example:

```text
DomU process VA       0x40001000
guest stage 1         0x40001000 -> 0x80200000
hypervisor stage 2    0x80200000 -> 0x8a200000
real DRAM access      0x8a200000
```

The guest sees:

```text
0x80200000
```

The bus sees:

```text
0x8a200000
```

That is the memory isolation boundary.

## 131.8  Stage-2 fault

If the guest touches a guest physical address that stage 2 does not map:

```text
guest load/store/fetch
  -> stage 1 succeeds
  -> stage 2 fails
  -> CPU traps to HYP
  -> hypervisor handles stage-2 fault
```

The hypervisor can:

- map a page lazily,
- emulate a device,
- inject an abort into the guest,
- kill the guest.

This is why a bad guest memory access does not have to corrupt Dom0.

## 131.9  Stage 2 and MMIO

MMIO is just address space from the CPU's point of view.

If a guest reads:

```text
0x0209c000
```

the hypervisor chooses:

- map it to the real GPIO register,
- leave it unmapped and fault,
- map it to an emulated device,
- map it only for Dom0.

On a small embedded SoC, passing real MMIO to a guest is serious. The register may control clocks, resets, interrupts, pins, or DMA.

## 131.10  Stage 2 does not solve DMA

This warning deserves its own section.

Stage 2 protects CPU translations.

DMA is different:

```text
device bus master -> RAM
```

A DMA-capable device may write memory without the guest CPU executing a load or store. If the SoC has no IOMMU or firewall for that device, a passed-through device may be able to write outside the guest's assigned memory.

So:

```text
CPU isolation: stage 2
DMA isolation: IOMMU/firewall/platform design
```

Do not claim safe passthrough until both are handled.

## 131.11  Interrupts before virtualization

Normal path:

```text
device raises interrupt
  -> GIC distributor
  -> GIC CPU interface
  -> CPU enters IRQ mode
  -> Linux handler
```

Linux expects to:

- configure interrupt priority,
- enable/disable IRQs,
- acknowledge interrupts,
- send end-of-interrupt,
- mask/unmask devices,
- map IRQ numbers to drivers.

## 131.12  Interrupts with a hypervisor

With a hypervisor:

```text
physical interrupt
  -> hypervisor or assigned guest policy
  -> maybe virtual interrupt injection
  -> guest IRQ handler
```

The hypervisor decides:

- which physical interrupt belongs to Dom0,
- which belongs to a DomU,
- which is virtual,
- which is hidden,
- which should wake a paused guest,
- which should never be exposed.

The guest still sees something that looks like an interrupt controller. It must, or Linux will not boot.

## 131.13  Virtual GIC

ARM systems use the GIC. A guest kernel expects a GIC-like interface.

The hypervisor can provide a **virtual GIC**:

```text
guest writes virtual GIC register
  -> trap or virtual interface
  -> hypervisor updates virtual interrupt state
```

This is why Xen logs mention GIC details and why the DTB must describe interrupt controllers correctly.

If GIC setup is wrong, failure is often early and quiet.

## 131.14  Timers before virtualization

Every OS needs a timer for:

- scheduler ticks,
- timeouts,
- sleeps,
- TCP retransmits,
- RCU,
- soft lockup detection,
- watchdog userspace.

On ARMv7-A, the architected timer is a central piece of Linux boot.

## 131.15  Virtual timers

A guest needs a timer it can believe.

The hypervisor must ensure:

- the guest can read time,
- timer interrupts arrive,
- one guest cannot break another guest's time,
- time continues sensibly when guests are scheduled.

Timer bugs look weird:

- boot stalls,
- sleeps never wake,
- RCU stalls,
- scheduler warnings,
- networking timeouts.

Always read timer lines in Xen and Linux logs.

## 131.16  Device models

Three common models:

| Model | What guest sees | Example |
|-------|-----------------|---------|
| Emulated | fake device implemented by hypervisor | legacy PC devices in desktop VMs |
| Paravirtual | hypervisor-aware virtual device | Xen console, Xen block, Xen net |
| Passthrough | real hardware device | assigning a UART or controller |

Embedded Xen often starts with:

- Dom0 owns physical devices,
- guests use paravirtual console/block/net,
- passthrough is delayed until the ownership table is clean.

That is the safe order.

## 131.17  Dom0 and DomU

Xen names its domains:

```text
Dom0: privileged control domain
DomU: unprivileged guest domain
```

Dom0 is Linux, but not normal bare-metal Linux.

Dom0 can:

- run the Xen toolstack,
- create DomU guests,
- provide virtual block/network backends,
- own real devices,
- mediate guest lifecycle.

DomU can:

- run Linux,
- use assigned memory,
- use virtual devices,
- crash without necessarily killing Dom0.

## 131.18  Jailhouse root cell and inmate

Jailhouse uses different language:

```text
root cell: Linux after Jailhouse is enabled
inmate cell: isolated partition
```

Xen boots first. Jailhouse is enabled after Linux boots.

Compare:

```text
Xen:
  firmware -> Xen -> Dom0 -> DomU

Jailhouse:
  firmware -> Linux -> enable Jailhouse -> inmate
```

Both use virtualization hardware. Their product models are different.

## 131.19  What to look for in logs

When reading logs, mark these:

```text
Who printed first:
CPU model:
CPU count:
virtualization extension visible:
GIC version:
timer:
memory map:
Xen command line:
Dom0 command line:
Dom0 start:
DomU start:
console:
```

The most useful skill is seeing the layer boundary in a log.

## 131.20  Example annotation: plain Linux

Plain QEMU Linux from Chapter 129:

```text
Booting Linux on physical CPU 0x0
Linux version ...
Machine model: linux,dummy-virt
Kernel command line: console=ttyAMA0 root=/dev/ram0 rdinit=/init
GIC: ...
clocksource: arch_sys_counter
Run /init as init process
```

Interpretation:

- Linux printed first.
- No Xen before it.
- Linux owns the machine.
- Console is physical PL011 as `ttyAMA0`.
- `/init` came from initramfs.

## 131.21  Example annotation: Xen + Dom0

Xen boot:

```text
Xen ...
Command line: console=dtuart ...
Booting on ARM ...
GICv2 initialization
Bringing up CPU0
Loading Dom0 kernel
```

Dom0 Linux later:

```text
Linux version ...
Kernel command line: console=hvc0 ...
Xen: initializing event channel driver
Run /init as init process
```

Interpretation:

- Xen printed first.
- Linux is Dom0.
- Dom0 console is `hvc0`, not the physical UART.
- Xen controls the machine boundary.

## 131.22  Exercise: address translation worksheet

Fill this table:

| Access | Stage 1 result | Stage 2 result | Who controls stage 1 | Who controls stage 2 |
|--------|----------------|----------------|----------------------|----------------------|
| native Linux user load | PA | none | Linux | none |
| Dom0 user load | guest PA | real PA | Dom0 Linux | Xen |
| DomU user load | guest PA | real PA | DomU Linux | Xen |
| bare-metal inmate load | depends | depends | inmate or none | Jailhouse |

Then answer:

- Which row can fault at stage 2?
- Which row can be killed without rebooting the host?
- Which row still has DMA risk?

## 131.23  Lab: log reading

Use three logs:

1. Chapter 129 plain QEMU Linux.
2. Chapter 132 Xen + Dom0 in QEMU.
3. Chapter 134 Xen + Dom0 on i.MX6ULL.

Create:

```text
notes/hyp-stage2-log-reading.md
```

Template:

```md
# HYP/stage-2 log reading

## Log 1: plain QEMU Linux

First software that prints:
Kernel command line:
CPU count:
Interrupt controller:
Timer:
Console:
Evidence that Linux is bare metal:

## Log 2: Xen + Dom0 in QEMU

First software that prints:
Xen command line:
Dom0 command line:
CPU count:
Interrupt controller:
Timer:
Console:
Evidence of Xen:
Evidence of Dom0:

## Log 3: Xen + Dom0 on i.MX6ULL

First software that prints:
Xen command line:
Dom0 command line:
CPU count:
Interrupt controller:
Timer:
Console:
Evidence of real board:
Evidence of Dom0:
```

The lab is complete when you can point to the exact line where Linux stops being bare-metal Linux and becomes Dom0 Linux.

## 131.24  Pitfalls

- **Thinking guest physical is real physical.** It is real only inside the guest.
- **Thinking HYP is Secure World.** HYP virtualizes Normal World. Monitor mode switches worlds.
- **Ignoring stage-2 faults.** They are the hypervisor memory boundary doing its job.
- **Ignoring interrupts.** A guest with broken virtual interrupts is not a usable OS.
- **Ignoring timer messages.** Time bugs look like random boot hangs.
- **Assuming stage 2 protects DMA.** It protects CPU translations, not every bus master.
- **Treating Dom0 as ordinary Linux.** Dom0 is privileged, but still a Xen domain.
- **Confusing Xen and Jailhouse.** Xen creates and manages domains. Jailhouse partitions hardware after Linux boots.

## 131.25  Going deeper

- ARMv7-A Virtualization Extensions documentation.
- Cortex-A7 MPCore Technical Reference Manual.
- Xen ARM boot and Device Tree documentation.
- Xen event channels and grant tables.
- Jailhouse documentation.
- Chapter 17 for stage-1 MMU foundations.
- Chapter 136 for DMA and device ownership.
