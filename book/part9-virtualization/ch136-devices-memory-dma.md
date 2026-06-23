---
chapter: 136
title: Devices, memory, and DMA boundaries
part: IX - Applied virtualization and mixed-criticality systems
estimated_pages: 30
status: draft
---

# Chapter 136: Devices, memory, and DMA boundaries

> **What:** decide which domain owns which hardware, and understand why DMA makes embedded virtualization dangerous if treated casually.
>
> **Why:** booting two kernels is only the easy half. The hard half is proving that one domain cannot corrupt another through devices, clocks, resets, interrupts, or DMA.
>
> **Focus:** CPU memory isolation is not the same as platform isolation. Stage 2 protects CPU translations. Devices need their own ownership story.
> **DMA:** Direct Memory Access, where a device reads or writes RAM without the CPU copying each byte.
> **Passthrough:** assigning a real hardware device to a guest.
> **Backend/frontend:** a split driver model where Dom0 owns real hardware and guests use virtual devices.

## 136.1  The ownership rule

Every real device needs one owner.

Owner means control of:

- MMIO registers,
- IRQ line,
- clock gate,
- reset line,
- pinctrl state,
- regulator or power switch,
- DMA channels,
- error recovery,
- suspend/resume policy,
- debug responsibility.

If two domains both think they own one controller, the design is already broken.

## 136.2  Start with the safest design

The safest first Xen design on i.MX6ULL:

```text
Xen
  Dom0 Linux
    owns all real devices
    owns storage
    owns network
    owns UART
    owns watchdog
  DomU Linux
    uses Xen console
    uses initramfs
    no real devices
```

This is boring, and boring is good. It proves domain lifecycle before hardware sharing.

## 136.3  Device ownership table

Create `notes/device-ownership-imx6ull-xen.md`:

```md
# Device ownership: i.MX6ULL Xen

| Device | MMIO | IRQ | DMA | Owner | Shared? | Notes |
|--------|------|-----|-----|-------|---------|-------|
| UART1 console |      |     | no  | Xen/Dom0 | no | early debug |
| FEC Ethernet |      |     | yes | Dom0 | virtual net later | DMA risk |
| USDHC SD/eMMC |     |     | yes | Dom0 | virtual block later | rootfs |
| GPIO1 |             |     | no  | Dom0 | avoid | mixed pins |
| I2C1 |              |     | maybe | Dom0 | proxy if needed | shared bus |
| watchdog |          |     | no | Dom0/safety | no | reset policy |
```

Fill MMIO and IRQ from the board DTB:

```sh
$ dtc -I dtb -O dts -o imx6ull-board.dts imx6ull-board.dtb
$ grep -n -A20 "uart" imx6ull-board.dts
$ grep -n -A20 "ethernet" imx6ull-board.dts
$ grep -n -A20 "usdhc" imx6ull-board.dts
```

Do not guess. Device Tree is the evidence.

## 136.4  Why GPIO banks are tricky

A GPIO controller owns many pins.

Example:

```text
GPIO1_IO03  LED
GPIO1_IO09  button
GPIO1_IO16  reset line for peripheral
GPIO1_IO28  unrelated board strap
```

Passing the whole GPIO1 controller to DomU gives DomU access to every pin in that bank, not just "the LED."

Safer pattern:

- Dom0 owns GPIO controller,
- Dom0 exposes a narrow service,
- DomU asks through a controlled channel.

For first labs, do not pass GPIO controllers.

## 136.5  Why I2C and SPI buses are tricky

An I2C controller is a bus master. Many devices may sit behind it:

```text
i2c1
  pmic
  rtc
  sensor
  touch controller
```

If DomU owns the controller, DomU can talk to everything on that bus.

SPI has the same issue with chip selects. Passing the controller may expose devices you did not intend to expose.

Safer pattern:

- Dom0 owns the bus,
- Dom0 runs the real driver,
- DomU receives data through virtual channel or shared memory.

## 136.6  CPU MMU vs DMA

CPU access:

```text
guest virtual -> guest physical -> real physical
```

Stage 2 can block that.

DMA access:

```text
device -> bus -> RAM
```

The CPU may not be involved.

If a guest owns a DMA-capable device, that device may be able to write outside the guest's memory unless the platform has an IOMMU or bus firewall configured.

So before passthrough, ask:

```text
Can this device DMA?
Can its DMA addresses be restricted?
Who programs the DMA descriptors?
Can the guest point DMA at Dom0 memory?
Does this SoC have an IOMMU for this device?
```

If you cannot answer, do not pass it through.

## 136.7  Device models ranked by risk

| Model | Risk | Example |
|-------|------|---------|
| Dom0 owns real device, DomU has no access | lowest | first labs |
| Dom0 owns real device, DomU uses paravirtual frontend | low | virtual network/block |
| Dom0 owns device, exports narrow custom service | medium | sensor proxy |
| DomU owns simple non-DMA MMIO device | medium | simple UART |
| DomU owns DMA-capable device | high | Ethernet, SD/MMC, USB |
| Multiple domains touch one controller | unacceptable first design | shared GPIO/I2C controller |

Start at the top. Move down only when evidence forces you.

## 136.8  Watchdog ownership

Never leave watchdog ownership implicit.

Bad design:

```text
Dom0 pets watchdog
DomU pets watchdog
maybe a script pets watchdog too
```

Good design:

```text
Dom0 owns hardware watchdog.
DomU reports heartbeat to Dom0.
Dom0 pets watchdog only if Dom0 and required DomUs are healthy.
If DomU dies, Dom0 restarts DomU.
If Dom0 dies, watchdog resets board.
```

Even better for some products:

```text
external MCU or M-core owns safety watchdog
Linux reports health
```

## 136.9  Reset ownership

Devices often share reset lines.

Example:

```text
GPIO reset line controls radio module
same module also uses UART and power regulator
```

If DomU owns the UART but Dom0 owns reset, failure recovery requires cooperation.

Write it down:

```text
Who can reset the device?
Who can power-cycle it?
Who reloads firmware?
Who handles stuck IRQ?
Who logs failures?
```

## 136.10  Clocks and pinctrl

Linux drivers assume they can request clocks, resets, pinctrl states, and regulators.

If DomU gets a device but not its supporting resources, the driver may fail or hang.

If DomU gets the supporting resources too broadly, it may affect Dom0 devices.

This is why passthrough on embedded SoCs is not just "map MMIO and IRQ."

## 136.11  Shared communication patterns

Safer communication options:

- Xen console,
- Xen virtual network,
- Xen virtual block,
- event channels,
- grant tables,
- shared memory ring buffer,
- RPMsg/OpenAMP on heterogeneous SoCs.

For each shared channel, define:

```text
Who allocates memory:
Who writes:
Who reads:
How notification works:
What happens if one side resets:
How protocol versions are checked:
```

## 136.12  Example: safe first i.MX6ULL design

```text
Dom0:
  UART console
  SD/eMMC
  Ethernet
  GPIO/I2C/SPI
  watchdog
  update system

DomU:
  no passthrough
  initramfs or virtual block
  hvc console
  virtual network later
```

Product use:

- DomU runs risky app logic,
- Dom0 supervises,
- Dom0 can restart DomU,
- hardware remains under one kernel.

This is the first design to try.

## 136.13  Example: risky design

```text
DomU owns Ethernet MAC directly.
```

Questions:

- Does FEC DMA?
- Can DMA be restricted?
- Who owns PHY reset GPIO?
- Who owns MDIO bus?
- Who owns clocks?
- Can DomU wedge the network hardware?
- Can Dom0 recover it?

If the answer is "not sure", this is not a first design.

## 136.14  Lab A: extract device facts from DTB

Use your board DTB:

```sh
$ dtc -I dtb -O dts -o imx6ull-board.dts imx6ull-board.dtb
```

Find:

```sh
$ grep -n -A12 "serial" imx6ull-board.dts
$ grep -n -A20 "ethernet" imx6ull-board.dts
$ grep -n -A20 "usdhc" imx6ull-board.dts
$ grep -n -A20 "gpio@" imx6ull-board.dts | head -80
$ grep -n -A20 "i2c@" imx6ull-board.dts
$ grep -n -A20 "spi@" imx6ull-board.dts
```

Fill:

```text
Device:
MMIO reg:
IRQ:
Clocks:
Pinctrl:
DMA:
Reset GPIO:
Owner:
```

## 136.15  Lab B: ownership table

Create:

```text
notes/device-ownership-imx6ull-xen.md
```

Include:

| Device | Owner | Shared? | DMA? | Why |
|--------|-------|---------|------|-----|
| UART console | | | | |
| SD/eMMC | | | | |
| Ethernet | | | | |
| watchdog | | | | |
| GPIO banks | | | | |
| I2C buses | | | | |
| SPI buses | | | | |

The table is complete only if every device has one owner.

## 136.16  Lab C: passthrough rejection note

Pick one device you are tempted to give to DomU.

Write:

```text
Device:
Why DomU wants it:
MMIO:
IRQ:
DMA risk:
Clock/reset/pinctrl dependencies:
Recovery owner:
Reason accepted or rejected:
```

It is fine if the answer is "rejected." A rejected unsafe design is progress.

## 136.17  Pitfalls

- **"It boots" mistaken for "it is isolated."** Boot success says little about DMA safety.
- **Mapping MMIO without clocks/resets.** Drivers need supporting resources.
- **Passing GPIO banks casually.** A bank is many pins.
- **Passing DMA devices without an IOMMU story.** Dangerous.
- **Letting everyone pet the watchdog.** That hides failures.
- **No reset owner.** Stuck hardware needs a recovery path.
- **No update owner.** Device firmware and guest software must be versioned.
- **No logs.** A product that cannot explain reset reason cannot be debugged in the field.

## 136.18  Going deeper

- Linux DMA API documentation.
- Xen grant tables and event channels.
- Linux Device Tree bindings for the device you want to pass through.
- i.MX6ULL Reference Manual bus, DMA, clock, reset, and IOMUX chapters.
- STM32MP1 remoteproc/RPMsg/OpenAMP documentation.
