---
chapter: 127
title: Why embedded products use hypervisors
part: IX - Applied virtualization and mixed-criticality systems
estimated_pages: 24
status: draft
---

# Chapter 127: Why embedded products use hypervisors

> **What:** decide whether an embedded Linux product needs a hypervisor, an RTOS companion core, TrustZone, containers, PREEMPT_RT, or just one well-designed Linux system.
>
> **Why:** HYP mode is a CPU feature, not a product requirement. A hypervisor is useful only when it creates a boundary the product actually needs.
>
> **Focus:** name the failure you are trying to contain. Then choose the smallest boundary that contains it.
> **MCU bridge:** Think of a hypervisor like a bootloader that never leaves. It stays below operating systems, owns the machine boundary, and decides which OS sees which memory, interrupts, and devices.
> **Hypervisor:** software running at the CPU virtualization privilege level. It creates and controls one or more operating-system guests.
> **Guest:** an operating system running under a hypervisor.

## 127.1  The wrong way to start

The wrong question:

```text
Can this Cortex-A7 run Xen or Jailhouse?
```

That question is not useless, but it is too early.

The right first question:

```text
What must survive when something else fails?
```

If the answer is "nothing special, reboot the product", you may not need a hypervisor.

If the answer is "the fieldbus must continue while the UI restarts", now there is a boundary to design.

If the answer is "private keys must remain protected even if Linux is compromised", that may be TrustZone, not Xen.

If the answer is "the motor loop needs 20 us jitter", that may be an MCU core, not a Linux guest.

The product failure decides the architecture.

## 127.2  What a hypervisor is not

A hypervisor is not:

- a faster Linux,
- a real-time patch,
- a security sticker,
- a replacement for watchdog design,
- a substitute for Device Tree discipline,
- a way to make one CPU behave like two physical CPUs,
- a shortcut around understanding boot and memory maps.

On a small SoC, a hypervisor usually makes the system harder before it makes anything better.

That is fine when the boundary is worth it. It is waste when the boundary is imaginary.

## 127.3  The failure-containment question

For every product, fill this table before choosing tools:

| Failure | Must keep running | Allowed response | Boundary needed |
|---------|-------------------|------------------|-----------------|
| UI process crash | field control | restart UI process | process supervisor |
| web stack compromised | private keys | deny key access | TrustZone or separate security chip |
| display driver crashes kernel | safety monitor | keep monitor alive | hypervisor or MCU core |
| fieldbus task blocks | cloud upload | restart fieldbus task | process or service boundary |
| old vendor BSP stuck on 4.1 | new app stack | run both temporarily | Xen-style VM boundary |
| motor loop jitter too high | motor control | move loop off Linux | MCU/RTOS or dedicated partition |

This table often kills a bad hypervisor idea early, which is a win.

## 127.4  Boundaries available to us

There are several ways to separate work.

### Process boundary

One Linux kernel. Multiple processes.

```text
Linux kernel
  app_ui
  app_network
  app_fieldbus
```

Use this when:

- one kernel can own all devices,
- a process crash is enough isolation,
- systemd/runit/supervision can restart services,
- security requirements fit Linux users, groups, seccomp, and MAC.

This is the default for many products.

### Container boundary

One Linux kernel. Multiple packaged user spaces.

```text
Linux kernel
  container: UI
  container: gateway service
  container: update agent
```

Use this when:

- deployment packaging matters,
- services need separate filesystem views,
- the kernel is trusted,
- device ownership remains centralized.

Avoid this when:

- you need a different kernel,
- a kernel crash must be contained,
- a hostile driver is in scope.

Containers are not virtual machines. They share the host kernel.

### PREEMPT_RT boundary

One Linux kernel with better scheduling latency.

```text
Linux + PREEMPT_RT
  realtime thread
  normal services
```

Use this when:

- Linux must respond faster,
- device drivers can be made RT-friendly,
- the timing budget is milliseconds or low hundreds of microseconds,
- security isolation is not the primary problem.

Avoid this when:

- you need hard MCU-style timing,
- the control loop is small enough for an M-core,
- a Linux kernel fault must not stop control.

PREEMPT_RT improves latency. It does not isolate faults.

### TrustZone boundary

One CPU complex, two worlds:

```text
Secure World: OP-TEE, keys, secure services
Normal World: Linux
```

Use this when:

- keys must survive Linux compromise,
- secure boot must chain into runtime secrets,
- a small trusted service is enough.

Avoid this when:

- you want two normal operating systems,
- you want a rich RTOS beside Linux,
- the codebase in Secure World would become large.

TrustZone is for trusted services. It is not a general two-Linux mechanism.

### remoteproc/OpenAMP boundary

Linux on an A-core. RTOS or firmware on an M-core.

```text
Cortex-A7: Linux
Cortex-M4: Zephyr or FreeRTOS
communication: RPMsg/OpenAMP
```

Use this when:

- the SoC has an MCU companion core,
- control logic fits there,
- message passing is acceptable,
- Linux should supervise firmware load and recovery.

This is the natural STM32MP157 pattern.

### Xen boundary

Hypervisor first, then virtual machines:

```text
Xen
  Dom0 Linux: control domain
  DomU Linux: guest
```

Use this when:

- you need multiple Linux systems,
- a legacy BSP must be contained,
- guest lifecycle matters,
- domains may be restarted independently,
- paravirtual console, block, and network devices help.

Avoid this when:

- one Linux is enough,
- static device partitioning is all you need,
- RAM is too small,
- boot complexity is not justified.

Xen is the right tool for "two Linux systems" in this part.

### Jailhouse boundary

Linux boots first, then gives hardware away:

```text
Linux root cell
Jailhouse
  inmate cell: CPU + RAM + device
```

Use this when:

- you have spare CPU cores,
- cells can be statically partitioned,
- the isolated workload is small,
- you want a bare-metal or RTOS inmate.

Avoid this when:

- the SoC has one CPU,
- guests need dynamic resource sharing,
- you want rich virtual devices,
- the device ownership table is messy.

Jailhouse is not a scheduler. It is a partitioner.

## 127.5  Why i.MX6ULL is still worth using

The i.MX6ULL is not a perfect virtualization board:

- one Cortex-A7 core,
- small RAM budget,
- no Cortex-M companion,
- no spare A-core for Jailhouse-style partitioning.

But it is still useful:

- ARMv7-A mode structure is visible,
- HYP mode is real on this Cortex-A7,
- U-Boot handoff is real,
- Device Tree is real,
- Xen Dom0 and DomU concepts can be demonstrated,
- the board's limitations teach honest architecture.

We do not use i.MX6ULL to pretend a small single-core SoC is a cloud host. We use it because the whole book already built this board from reset vector upward. Seeing Xen on the same board completes the mental map.

## 127.6  Why QEMU comes first

QEMU gives us a clean failure surface.

With QEMU:

- reset is instant,
- boot logs are easy to capture,
- memory size is configurable,
- CPU count is configurable,
- no SD card is corrupted,
- no board is wedged,
- GDB can attach before the first instruction we care about.

That is why the path is:

```text
QEMU plain Linux
QEMU U-Boot
QEMU Xen
i.MX6ULL Xen
QEMU Jailhouse ARM64
STM32MP1 Linux + RTOS
```

QEMU teaches the pattern. Real hardware teaches the cost.

## 127.7  Why STM32MP1 appears in an i.MX6ULL book

The book's main board is i.MX6ULL, but the question "Linux + RTOS" deserves an honest answer.

On i.MX6ULL:

```text
one Cortex-A7
Linux and RTOS must share the same CPU if both run there
```

On STM32MP157:

```text
dual Cortex-A7 + Cortex-M4
Linux can run on A7
RTOS can run on M4
```

That is a better production split for many products.

So Part IX says:

- Xen on i.MX6ULL is a real HYP-mode experiment.
- Jailhouse on i.MX6ULL is not a good first target.
- Jailhouse in QEMU ARM64 is a good partitioning lab.
- STM32MP1 Linux + M4 RTOS is the realistic Linux+RTOS product pattern.

That distinction matters. It prevents the reader from forcing one board to teach every lesson.

## 127.8  Case study: field gateway

Product:

- Ethernet or LTE uplink,
- RS-485 Modbus fieldbus,
- local web UI,
- OTA updates,
- must keep polling field devices even if UI crashes.

### Bad first answer

```text
Run everything in one process.
```

One crash kills everything.

### Better simple answer

```text
One Linux
  systemd service: fieldbusd
  systemd service: webui
  systemd service: updater
```

If `webui` crashes, `fieldbusd` continues.

This may be enough.

### Container answer

```text
One Linux
  container: web UI
  host service: fieldbusd
  host service: updater
```

Use this if packaging and update separation are important.

### Hypervisor answer

```text
Xen
  Dom0: fieldbus and watchdog
  DomU: web UI and cloud stack
```

Use this only if the web/cloud stack is risky enough that a kernel or driver fault must be contained.

### Likely decision

Start with one Linux and separate services. Move to Xen only if field evidence or security requirements justify a kernel boundary.

## 127.9  Case study: industrial HMI with safety monitor

Product:

- touchscreen UI,
- display stack,
- data logging,
- safety output,
- watchdog,
- remote update.

Display stacks are large. UI code changes often. Safety logic should be small and boring.

### One-Linux design

```text
Linux
  UI process
  safety-monitor process
  watchdog daemon
```

This is easy but weak. A kernel/display-driver failure can still stop safety logic.

### TrustZone design

```text
Secure World: small safety or key service
Normal World: Linux UI
```

This is suitable only if the secure part is tiny. Do not put a large control application into Secure World.

### MCU companion design

```text
A-core Linux: UI, display, logging
M-core RTOS: safety monitor, watchdog policy, safety output
```

This is often best if the SoC has an M-core.

### Xen design

```text
Xen
  Dom0: safety supervisor, watchdog, selected hardware
  DomU: UI Linux
```

This can work when the safety workload needs an A-core or when no M-core exists.

### Likely decision

On STM32MP157, use the M4 for the safety monitor if it fits. On i.MX6ULL, consider Xen only if a separate safety microcontroller is not available and the risk justifies the complexity.

## 127.10  Case study: legacy BSP containment

Product:

- old vendor camera stack works only on Linux 4.1,
- product application wants Linux 6.x,
- hardware cannot change this generation,
- camera feature must ship.

This is one of the clearest Xen-style cases.

Possible architecture:

```text
Xen
  Dom0 Linux 6.x: networking, update, storage, product app
  DomU Linux 4.1: camera vendor stack
shared channel: frame transfer or network
```

This design is not pretty, but it may isolate the old BSP while the rest of the product moves forward.

Questions:

- Who owns the camera hardware?
- Does old Linux need direct device access?
- Can frames cross domains safely?
- How is the old guest updated?
- Can the product tolerate the RAM cost?
- What is the exit plan for removing the old guest?

Hypervisors are often used as migration scaffolding. Scaffolding should not become architecture forever.

## 127.11  Case study: motor control

Product:

- user interface,
- Ethernet,
- motor-control loop,
- hard fault input,
- PWM outputs,
- current feedback.

If the control loop needs tight timing, do not start with Xen.

Likely order:

1. Dedicated motor-control MCU.
2. SoC M-core with RTOS.
3. Bare-metal or RTOS partition on a spare A-core.
4. PREEMPT_RT only if measured latency fits.
5. Xen only if the problem is OS isolation, not microsecond control.

Reason:

```text
Hypervisor isolation != hard real-time control
```

The hypervisor can isolate worlds. It does not make Linux a motor-control MCU.

## 127.12  Device ownership decides architecture

Before writing code, make a device table:

| Device | Owner | Shared? | DMA? | Reset owner | Notes |
|--------|-------|---------|------|-------------|-------|
| UART console | Dom0 or Xen | no | no | Dom0 | debugging lifeline |
| Ethernet | Dom0 | virtual net to guest | yes | Dom0 | do not pass through first |
| eMMC/SD | Dom0 | virtual block to guest | yes | Dom0 | rootfs and updates |
| Watchdog | Dom0 or safety core | no | no | safety policy | must be explicit |
| GPIO bank | one owner | avoid | no | owner | banks contain mixed pins |
| I2C controller | one owner | proxy | maybe | owner | bus has many devices |
| Display | UI domain | no | yes | UI owner | large driver stack |

If the table is confusing, the product will be confusing.

## 127.13  Watchdog policy

Ask this early:

```text
Who pets the watchdog?
```

Possible answers:

- Linux init system,
- Dom0 watchdog daemon,
- hypervisor-aware watchdog service,
- M-core safety firmware,
- external supervisor MCU.

Bad answer:

```text
Everyone pets it.
```

If every world can pet the watchdog, one broken world can hide another broken world.

A useful policy says:

- what "healthy" means,
- who reports health,
- who aggregates health,
- who pets the hardware watchdog,
- what happens when DomU dies,
- what happens when Dom0 dies,
- what gets logged before reset.

## 127.14  Update policy

Virtualization changes updates.

One Linux product:

```text
A/B rootfs update
rollback if boot fails
```

Xen product:

```text
Xen binary
Dom0 kernel
Dom0 rootfs
DomU kernel
DomU rootfs
guest configs
shared protocol version
rollback rules
```

Linux + M4 product:

```text
Linux image
M4 firmware
RPMsg protocol version
resource table
rollback compatibility
```

Every extra world is another artifact to version, sign, test, and roll back.

This is one reason "no hypervisor" is often the professional answer.

## 127.15  Security boundary sanity check

A boundary is only useful if the attack path cannot simply walk around it.

Ask:

- Can this domain program DMA into another domain's RAM?
- Can this domain reconfigure clocks or resets for another domain's device?
- Can this domain change pinmux?
- Can this domain access the update partition for another domain?
- Can this domain pet the global watchdog?
- Can this domain read secrets?
- Can this domain write bootloader environment?

If yes, write down why that is acceptable or fix the design.

## 127.16  Choosing between Xen and Jailhouse

Use Xen when the product wants virtual machines:

- multiple Linux systems,
- Dom0 control,
- guest lifecycle,
- paravirtual console/block/network,
- migration away from old BSPs,
- guest restart as a normal operation.

Use Jailhouse when the product wants static partitions:

- one Linux root cell,
- one or more isolated inmate cells,
- dedicated CPUs,
- dedicated memory,
- dedicated devices,
- no rich scheduling or virtual device model.

Quick rule:

```text
If you want "two Linux systems", think Xen.
If you want "Linux plus a dedicated bare-metal/RTOS island", think Jailhouse or M-core.
```

On i.MX6ULL, use Xen for the real-board experiment. Use QEMU ARM64 for the first Jailhouse experiment.

## 127.17  The Part IX path

The chapters are ordered to avoid magic:

| Chapter | Result |
|---------|--------|
| 128 | QEMU starts, GDB attaches, DTB is visible |
| 129 | Tiny ARM Linux boots directly in QEMU |
| 130 | U-Boot boots that Linux in QEMU |
| 131 | HYP, stage-2 MMU, virtual IRQs explained |
| 132 | Xen boots Dom0 in QEMU |
| 133 | DomU Linux starts in QEMU |
| 134 | Xen boots Dom0 on i.MX6ULL |
| 135 | DomU Linux starts on i.MX6ULL |
| 136 | Device, memory, DMA ownership is analyzed |
| 137 | Jailhouse starts an inmate in QEMU ARM64 |
| 138 | Bare-metal or Zephyr inmate runs |
| 139 | STM32MP1 Linux + M4 RTOS pattern is built |

The sequence is deliberate. We do not start by throwing Xen at a real board and hoping the serial log is kind.

## 127.18  Lab: architecture decision memo

This chapter's lab is a written engineering artifact. That is intentional. Real virtualization decisions are made before code.

Create:

```text
~/imx6ull/virt-lab/decision-memo.md
```

Use this template:

```text
# Virtualization decision memo

## Product

Name:
Board:
CPU cores:
RAM:
Storage:
Network:
Safety or uptime requirement:

## Workloads

| Workload | Timing | Security | Update rate | Device needs |
|----------|--------|----------|-------------|--------------|
|          |        |          |             |              |

## Failures to contain

| Failure | Must keep running | Allowed recovery | Boundary candidate |
|---------|-------------------|------------------|--------------------|
|         |                   |                  |                    |

## Device ownership

| Device | Owner | Shared? | DMA? | Notes |
|--------|-------|---------|------|-------|
|        |       |         |      |       |

## Watchdog policy

Who reports health:
Who pets watchdog:
What happens when UI dies:
What happens when control dies:
What happens when Dom0/root Linux dies:

## Update policy

Artifacts:
Compatibility rules:
Rollback rules:
Who verifies signatures:

## Decision

Chosen architecture:
Why:
Rejected alternatives:
Biggest risk:
First lab to prove it:
```

## 127.19  Lab cases

Fill the memo for three products.

### Case A: field gateway

Requirements:

- Ethernet or LTE uplink,
- Modbus or CAN fieldbus,
- local web UI,
- OTA updates,
- field polling should recover if UI crashes.

Expected likely answer: one Linux with separate services first, possibly containers. Xen only if kernel-level isolation or legacy containment is required.

### Case B: industrial HMI with safety monitor

Requirements:

- display and touch,
- data logging,
- safety output,
- watchdog,
- updateable UI.

Expected likely answer: M-core or external MCU for safety if available. Xen only if the safety workload must run on an A-core and the risk justifies it.

### Case C: legacy BSP containment

Requirements:

- old camera stack works only on old Linux,
- new product software wants mainline Linux,
- both must ship temporarily,
- RAM budget can tolerate two kernels.

Expected likely answer: Xen is plausible.

## 127.20  Lab review checklist

Your memo is acceptable only if:

- it names specific failures,
- it says what survives each failure,
- it assigns watchdog ownership,
- it assigns device ownership,
- it identifies DMA-capable devices,
- it has an update and rollback story,
- it rejects at least one tempting but wrong architecture,
- it names the first lab that would prove the decision.

If the memo only says "use Xen because isolation", it is not done.

## 127.21  Pitfalls

- **Starting with the tool.** Start with the failure boundary.
- **Mistaking scheduling for isolation.** PREEMPT_RT improves latency. It does not isolate a malicious driver.
- **Mistaking containers for virtual machines.** Containers share the host kernel.
- **Ignoring DMA.** CPU page tables do not automatically stop a device from writing memory.
- **Ignoring watchdog policy.** A watchdog with no owner is just a timer.
- **Ignoring updates.** Two worlds mean two version histories and two rollback plans.
- **Overusing TrustZone.** Secure World should stay small.
- **Overusing the M-core.** The M4 is useful, but it is not a tiny Linux machine.
- **Overusing Xen.** Xen is powerful, but one Linux is better when one Linux is enough.
- **Overusing Jailhouse.** Jailhouse needs clean static partitioning and spare CPUs.

## 127.22  Going deeper

- QEMU Arm `virt` machine documentation.
- Xen Project ARM documentation.
- Jailhouse README and QEMU ARM64 demo notes.
- Linux remoteproc documentation.
- Linux RPMsg documentation.
- OpenAMP documentation.
- STM32MP1 reference manuals.
- Zephyr STM32MP157 board documentation.
