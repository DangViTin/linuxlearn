---
chapter: 139
title: STM32MP1 Linux plus RTOS, the production pattern
part: IX - Applied virtualization and mixed-criticality systems
estimated_pages: 38
status: draft
---

# Chapter 139: STM32MP1 Linux plus RTOS, the production pattern

> **What:** build the mental and practical path for Linux on STM32MP1 Cortex-A7 plus firmware on the Cortex-M4.
>
> **Why:** many real Linux plus RTOS products do not need a hypervisor. They need the SoC's companion microcontroller core used properly.
>
> **Focus:** remoteproc, RPMsg, OpenAMP, firmware ownership, update policy, and when Jailhouse still makes sense.

## 139.1  Why this chapter belongs in the hypervisor part

This chapter is not a Jailhouse chapter.

That is the point.

A good engineer does not force every isolation problem into a hypervisor. On STM32MP1, the hardware already gives you a natural split:

```text
Cortex-A7 cores: Linux
Cortex-M4 core: RTOS or bare-metal firmware
```

That is often a better product boundary than running another A-core guest.

The hypervisor lesson is:

```text
choose the boundary that fits the hardware
```

For i.MX6ULL:

```text
one Cortex-A7
no companion M-core
```

For STM32MP157:

```text
two Cortex-A7 cores
one Cortex-M4 core
```

If your real-time workload fits on the M4, use the M4 first. Save Jailhouse for problems that really need A-core partitioning.

## 139.2  The production shape

The common STM32MP1 product shape:

```text
Linux on Cortex-A7:
  UI
  networking
  storage
  update agent
  logging
  supervision

RTOS or bare metal on Cortex-M4:
  fast control loop
  simple safety monitor
  deterministic peripheral handling
  wakeup task
  small protocol endpoint

communication:
  RPMsg over shared memory
  OpenAMP conventions
  mailbox or interrupt notifications

management:
  Linux remoteproc loads and starts M4 firmware
```

Linux and M4 are not two Linux processes. They are two processors in one SoC.

## 139.3  What remoteproc does

`remoteproc` is a Linux kernel framework for controlling another processor in the same system.

On a supported SoC, Linux can:

```text
load firmware
start the remote processor
stop the remote processor
report crashes
create RPMsg virtio devices when the firmware announces them
```

The key idea:

```text
Linux is the supervisor.
M4 firmware is firmware.
```

The M4 firmware is not a Linux process. It does not use Linux syscalls. It does not share the Linux scheduler.

## 139.4  What RPMsg does

`RPMsg` is a message bus for communication with remote processors.

The common implementation uses:

```text
shared memory buffers
virtio vrings
mailbox or interrupt notifications
named channels
endpoints
```

The mental model:

```text
Linux app
  -> Linux rpmsg driver
  -> RPMsg channel
  -> shared memory vring
  -> M4 OpenAMP endpoint
```

This is message passing. It is not two CPUs casually writing each other's global variables.

## 139.5  What OpenAMP does

OpenAMP is the ecosystem around this kind of asymmetric multiprocessing.

It gives firmware-side pieces for:

```text
RPMsg
virtio
resource tables
shared memory setup
remote processor communication
```

In practice, Zephyr can use OpenAMP samples to talk to Linux RPMsg drivers.

Important distinction:

```text
Jailhouse cell config describes A-core partitioning.
remoteproc resource table describes remote processor resources.
```

Do not mix those concepts.

## 139.6  First board assumptions

This chapter assumes an STM32MP157 Discovery style board such as:

```text
STM32MP157C-DK2
STM32MP157F-DK2
similar STM32MP15 board with Cortex-M4 enabled
```

Board names vary by BSP and Zephyr release. You must check your exact board.

On the Linux side:

```sh
# cat /proc/device-tree/model
# uname -a
# ls /sys/class/remoteproc
```

On the Zephyr side:

```sh
$ west boards | grep -i stm32mp
```

Write down:

```text
board model:
Linux BSP:
kernel version:
Zephyr board target:
remoteproc node:
```

## 139.7  Linux kernel features to check

Boot Linux on the STM32MP1 board.

Check remoteproc:

```sh
# ls /sys/class/remoteproc
```

Expected shape:

```text
remoteproc0
```

Check kernel messages:

```sh
# dmesg | grep -i remoteproc
# dmesg | grep -i rpmsg
```

Check config if available:

```sh
# zcat /proc/config.gz | grep -E "REMOTE_PROC|RPMSG|STM32"
```

Useful symbols may include:

```text
CONFIG_REMOTEPROC
CONFIG_STM32_RPROC
CONFIG_RPMSG
CONFIG_RPMSG_CHAR
CONFIG_RPMSG_TTY
```

Names vary by kernel version and BSP. The important evidence is:

```text
Linux exposes a remoteproc device for the M4
Linux can create RPMsg devices when firmware supports them
```

## 139.8  Device Tree features to check

Remoteproc is SoC specific. If the Device Tree does not describe the M4 and shared memory correctly, Linux cannot manage it.

Inspect the running tree:

```sh
# find /proc/device-tree -iname "*m4*" -o -iname "*rproc*" -o -iname "*rpmsg*"
```

Also save the boot DTB if your boot flow makes it available.

Things to look for:

```text
M4 remoteproc node
reserved memory for firmware or vrings
mailbox nodes
shared memory regions
RPMsg related nodes
status = "okay"
```

If `/sys/class/remoteproc` is empty, debug Device Tree and kernel config before debugging Zephyr.

## 139.9  Build the simplest M4 firmware first

Start with a firmware that does one visible thing:

```text
prints on the M4 console
or toggles an LED owned by M4
or creates an RPMsg hello channel
```

Do not start with a control loop.

Do not start with a product protocol.

First prove:

```text
Linux can load firmware
Linux can start M4
M4 actually runs
Linux can stop M4
Linux can start M4 again
```

## 139.10  Zephyr setup

Use a separate workspace:

```sh
$ sudo apt install python3-venv python3-pip
$ mkdir -p ~/stm32mp1-m4-lab
$ cd ~/stm32mp1-m4-lab
$ python3 -m venv .venv
$ . .venv/bin/activate
$ pip install west
$ west init zephyrproject
$ cd zephyrproject
$ west update
$ west zephyr-export
$ pip install -r zephyr/scripts/requirements.txt
```

Find STM32MP1 boards:

```sh
$ cd zephyr
$ west boards | grep -i stm32mp
```

A board name may look like:

```text
stm32mp157c_dk2/stm32mp157cxx
```

Older Zephyr releases may accept the shorter `stm32mp157c_dk2` name. Use the board target from your Zephyr checkout, not from memory.

## 139.11  Build a basic Zephyr sample

Build hello world:

```sh
$ west build -b stm32mp157c_dk2/stm32mp157cxx samples/hello_world
```

If your Zephyr release uses the older short board name, replace the target with `stm32mp157c_dk2`. If your board revision differs, use the target shown by `west boards`.

Find the output:

```sh
$ ls build/zephyr
$ file build/zephyr/zephyr.elf
```

For remoteproc, the ELF is often the useful artifact because it contains loadable sections and metadata. Some BSP flows use a different packaged firmware file. Use the format required by your Linux remoteproc driver and board documentation.

Record:

```text
Zephyr board:
Zephyr sample:
firmware file:
firmware size:
```

## 139.12  Install firmware on the board

Copy the firmware to the board:

```sh
$ scp build/zephyr/zephyr.elf root@BOARD_IP:/lib/firmware/stm32mp1-m4.elf
```

On the board:

```sh
# ls -l /lib/firmware/stm32mp1-m4.elf
# file /lib/firmware/stm32mp1-m4.elf
```

The firmware path matters because remoteproc asks the Linux firmware loader for a file name.

## 139.13  Start M4 with remoteproc

On the board:

```sh
# ls /sys/class/remoteproc
# cat /sys/class/remoteproc/remoteproc0/state
# echo stm32mp1-m4.elf > /sys/class/remoteproc/remoteproc0/firmware
# echo start > /sys/class/remoteproc/remoteproc0/state
# cat /sys/class/remoteproc/remoteproc0/state
```

Expected result:

```text
running
```

Check logs:

```sh
# dmesg | tail -n 120
```

Stop:

```sh
# echo stop > /sys/class/remoteproc/remoteproc0/state
# cat /sys/class/remoteproc/remoteproc0/state
```

Expected result:

```text
offline
```

Start again:

```sh
# echo start > /sys/class/remoteproc/remoteproc0/state
```

This start-stop-start loop is your first production-relevant test.

## 139.14  If start fails

Do not guess. Classify the failure.

**Firmware file not found**

Check:

```sh
# ls -l /lib/firmware
# dmesg | tail -n 80
```

**Bad firmware format**

Check:

```sh
# file /lib/firmware/stm32mp1-m4.elf
# readelf -h /lib/firmware/stm32mp1-m4.elf
```

**Wrong load address**

Check the Zephyr linker map and the STM32MP1 memory layout.

**Remoteproc node missing**

Check kernel config and Device Tree.

**M4 starts but no output**

Check which UART, LED, or RPMsg endpoint the firmware uses. The M4 may be running with no visible output path.

## 139.15  Move from hello world to RPMsg

Once start and stop work, build an RPMsg/OpenAMP sample.

Zephyr has an OpenAMP resource-table sample:

```text
samples/subsys/ipc/openamp_rsc_table
```

Build shape:

```sh
$ west build -b stm32mp157c_dk2/stm32mp157cxx samples/subsys/ipc/openamp_rsc_table
```

If the sample requires an overlay for your board, add it only after reading the sample README and your board documentation.

The firmware must describe the RPMsg resources in a way Linux remoteproc understands. That is what the resource table is for.

## 139.16  Linux RPMsg checks

After starting RPMsg-capable firmware:

```sh
# dmesg | grep -i rpmsg
# ls /sys/bus/rpmsg/devices
# ls /dev/rpmsg* 2>/dev/null
# ls /dev/ttyRPMSG* 2>/dev/null
```

Depending on the Linux BSP, user-space access may appear as:

```text
/dev/rpmsg_ctrl*
/dev/rpmsg*
/dev/ttyRPMSG*
kernel sample driver only
```

The exact device node is less important than the evidence:

```text
the M4 firmware announced an RPMsg service
Linux created a matching RPMsg device or driver binding
messages can cross the boundary
```

## 139.17  RPMsg echo test

If your BSP exposes a TTY-style RPMsg device:

```sh
# echo hello > /dev/ttyRPMSG0
# cat /dev/ttyRPMSG0
```

If your BSP exposes rpmsg char devices, use the matching test tool from the BSP or kernel samples.

Record:

```text
RPMsg service name:
Linux device node:
message sent:
message received:
dmesg evidence:
```

Do not hide the mechanism behind "it works". A future update will break this unless you know which service name and driver binding made it work.

## 139.18  The shared memory picture

RPMsg is built on shared memory, but you should think in messages.

The physical picture:

```text
DDR or SRAM region visible to both processors
two vrings
shared buffers
mailbox notification
```

The software picture:

```text
Linux endpoint sends message
M4 endpoint receives message
M4 endpoint replies
Linux endpoint receives reply
```

This prevents a bad habit:

```text
two processors sharing arbitrary structs with no ownership rules
```

For a product, write a protocol:

```text
message type
version
sequence number
payload length
checksum if needed
timeout behavior
reset behavior
```

## 139.19  Who owns the peripherals

STM32MP1 can route many peripherals to the A7 side or the M4 side.

Before firmware uses a peripheral, decide:

```text
Linux owns it
or M4 owns it
or it is shared through a proper driver and protocol
```

Do not let Linux and M4 both program the same hardware block casually.

Make a table:

| Peripheral | Owner | Reason | Linux node | M4 driver |
|------------|-------|--------|------------|-----------|
| UART for Linux console | Linux | debug access | enabled | disabled |
| Timer for control loop | M4 | deterministic timing | disabled | enabled |
| Ethernet | Linux | network stack | enabled | disabled |
| Safety GPIO | M4 | fast reaction | disabled | enabled |
| RPMsg shared memory | both | communication | reserved | OpenAMP |

Device ownership is the embedded version of process isolation.

## 139.20  Watchdog policy

A mixed Linux plus RTOS product needs a watchdog policy.

Answer these:

```text
which side kicks the hardware watchdog?
can Linux restart M4 firmware?
can M4 reset Linux?
what happens if RPMsg stops?
what happens if M4 firmware crashes?
what happens if Linux update installs incompatible firmware?
```

Common safe pattern:

```text
M4 owns fast safety reaction
Linux owns update and logging
Linux supervises M4 heartbeat
M4 supervises critical output state
hardware watchdog resets the whole system only for unrecoverable faults
```

The exact answer depends on the product. The important part is to write it down.

## 139.21  Firmware versioning

Linux and M4 firmware are updated together or deliberately versioned apart.

Every RPMsg protocol should have:

```text
protocol version
firmware version
minimum Linux driver version
feature flags
unknown message handling
```

First message after boot:

```text
M4 -> Linux: hello, firmware version, protocol version, feature flags
Linux -> M4: accepted or rejected
```

If Linux and M4 disagree, fail clearly.

Do not let a field update produce a silent protocol mismatch.

## 139.22  Failure lab A: missing firmware

Set a wrong firmware name:

```sh
# echo does-not-exist.elf > /sys/class/remoteproc/remoteproc0/firmware
# echo start > /sys/class/remoteproc/remoteproc0/state
```

Expected result:

```text
start fails
dmesg reports firmware load failure
```

Lesson:

```text
remoteproc uses the Linux firmware loader
```

## 139.23  Failure lab B: wrong board target

Build firmware for a different Zephyr board and try to start it.

Expected result:

```text
load failure
crash
no output
or no RPMsg channel
```

Reason:

```text
memory layout and devices do not match the board
```

Lesson:

```text
board target is part of the firmware ABI
```

## 139.24  Failure lab C: RPMsg service mismatch

Run firmware that announces a service name Linux does not bind to.

Expected result:

```text
remoteproc running
no useful user-space device
or dmesg shows unbound RPMsg device
```

Reason:

```text
RPMsg channel names must match Linux-side drivers or user-space access paths
```

Lesson:

```text
M4 running is not the same as Linux communication working
```

## 139.25  When Jailhouse is useful on STM32MP1

Jailhouse can still make sense on STM32MP1 when:

```text
the workload needs A7 performance
the M4 is too small
you have a dual-A7 variant
static CPU and device partitioning is acceptable
the device ownership map is simple
you can dedicate one A7 core to the isolated workload
```

Example:

```text
A7 core 0: Linux UI and networking
A7 core 1: isolated control Linux or RTOS cell
M4: low-power monitor or safety fallback
```

But do not choose this first.

First ask:

```text
can the M4 do the real-time job?
can Linux plus PREEMPT_RT handle it?
can a normal Linux process boundary handle it?
```

If yes, Jailhouse may be unnecessary complexity.

## 139.26  Xen versus Jailhouse versus M4

Choose **M4 remoteproc** when:

```text
the workload fits on Cortex-M4
you need MCU-style timing
message passing is enough
Linux can supervise firmware
```

Choose **Jailhouse** when:

```text
you need static A-core partitioning
you can dedicate CPU and devices
guest lifecycle is simple
low overhead matters
```

Choose **Xen** when:

```text
you need multiple Linux guests
you need richer guest lifecycle
you need Dom0 style management
you accept more virtualization complexity
```

Choose **plain Linux** when:

```text
process isolation is enough
containers are enough
PREEMPT_RT is enough
the hardware ownership problem is simple
```

This decision is more important than tool preference.

## 139.27  Lab deliverables

Create:

```text
logs/linux-uname.txt
logs/device-tree-model.txt
logs/remoteproc-list.txt
logs/remoteproc-dmesg.txt
logs/zephyr-board-list.txt
logs/zephyr-build.txt
logs/remoteproc-start-stop.txt
logs/rpmsg-dmesg.txt
notes/peripheral-ownership-table.txt
notes/watchdog-policy.txt
notes/protocol-versioning.txt
```

Minimum success:

```text
Linux exposes remoteproc0
Linux loads M4 firmware
Linux starts M4
Linux stops M4
Linux starts M4 again
```

Full success:

```text
Linux and M4 exchange an RPMsg message
the protocol and ownership table are documented
```

## 139.28  Troubleshooting

**No `/sys/class/remoteproc`**

Check:

```text
kernel config
Device Tree
BSP support
remoteproc driver loaded
M4 node status
```

**Firmware loads but M4 does nothing visible**

Check:

```text
firmware entry address
M4 clock and reset
console ownership
LED or GPIO ownership
Zephyr board target
```

**RPMsg devices do not appear**

Check:

```text
resource table
shared memory reservation
mailbox setup
service name
Linux RPMsg driver
kernel log
```

**Stop fails**

Check whether the firmware cooperates with shutdown. Some remote processors or firmware images may not stop cleanly without board-specific support.

**Everything works once but not after restart**

Check reset state:

```text
shared memory cleared
vrings reinitialized
peripherals reset
firmware does not assume power-on defaults
Linux driver handles remove and probe
```

## 139.29  Product checklist

Before calling a Linux plus M4 design production-ready, fill this out:

```text
M4 firmware owner:
Linux supervisor owner:
firmware storage location:
firmware update mechanism:
rollback mechanism:
protocol version field:
heartbeat interval:
Linux action on missed heartbeat:
M4 action on Linux silence:
watchdog owner:
shared memory region:
peripheral ownership table:
crash log path:
field diagnostic command:
factory recovery path:
```

Blank lines are architecture debt.

## 139.30  Closing Part IX

Part IX started with hypervisor mode because ARM virtualization is real and useful.

But the deeper lesson is broader:

```text
isolation is a design tool
```

Sometimes the right boundary is a hypervisor.

Sometimes it is an MMU process boundary.

Sometimes it is a Linux driver.

Sometimes it is an M4 companion core.

The grown-up embedded Linux skill is to match the boundary to the product, then make the boundary visible enough that another engineer can debug it at 2 a.m.
