---
chapter: 138
title: Bare-metal or Zephyr inmate cell
part: IX - Applied virtualization and mixed-criticality systems
estimated_pages: 36
status: draft
---

# Chapter 138: Bare-metal or Zephyr inmate cell

> **What:** build a tiny non-Linux workload and run it as a Jailhouse inmate cell.
>
> **Why:** the most useful Jailhouse product pattern is often Linux plus one small deterministic workload.
>
> **Focus:** start with bare metal, then move to Zephyr only after the cell contract is clear.

## 138.1  Why not start with Zephyr

Zephyr is not the hard part.

The hard part is the contract:

```text
where does the inmate start?
where is its RAM?
which CPU runs it?
which MMIO regions can it touch?
which interrupt lines can reach it?
how does it talk to Linux?
```

If you start with Zephyr and it fails, you have too many possible causes:

```text
wrong Jailhouse cell config
wrong link address
wrong Zephyr board target
wrong devicetree
wrong console driver
wrong interrupt setup
wrong shared memory setup
```

So we start with a tiny bare-metal inmate. It is not a product. It is a flashlight.

Once the flashlight works, Zephyr becomes much less mysterious.

## 138.2  The inmate is not a Linux program

A normal Linux program starts because the kernel does a lot of work:

```text
loads ELF segments
sets up virtual memory
maps shared libraries
builds a stack
passes argc and argv
jumps to user mode
```

A Jailhouse inmate does not get that environment.

For a simple bare-metal inmate, you provide:

```text
entry point
link address
stack
exception vector choice if needed
MMIO access code
loop or shutdown path
```

That is why this command is wrong:

```sh
# jailhouse cell load inmate-demo /bin/ls
```

`/bin/ls` expects Linux. An inmate binary expects the cell environment.

## 138.3  The three addresses

Keep these three addresses separate:

| Address | Meaning |
|---------|---------|
| Cell memory physical address | The RAM range assigned in the inmate cell config. |
| Inmate link address | The address the compiler and linker assume at build time. |
| Load address | The address where `jailhouse cell load` places the binary. |

For the simplest bare-metal inmate, make all three match:

```text
cell memory starts at 0x7c000000
binary is linked at 0x7c000000
binary is loaded at 0x7c000000
```

If the cell config gives the inmate RAM at one address but the binary is linked for another, the first branch or global variable access may go into nonsense.

## 138.4  Workspace

Continue from the previous chapter:

```sh
$ mkdir -p ~/imx6ull/jailhouse-lab/inmates/baremetal
$ cd ~/imx6ull/jailhouse-lab/inmates/baremetal
```

We will create:

```text
start.S
main.c
inmate.ld
Makefile
README-notes.txt
```

This chapter shows the shape. You will fill in the exact base addresses from your QEMU ARM64 inmate config.

## 138.5  Read the demo inmate config first

Open the demo inmate config:

```sh
$ cd ~/imx6ull/jailhouse-lab/src/jailhouse
$ less configs/arm64/qemu-arm64-inmate-demo.c
```

Find the RAM region assigned to the inmate.

Write it down:

```text
inmate RAM physical start:
inmate RAM size:
inmate load address:
inmate CPU:
inmate console type:
inmate console MMIO base:
```

Do not write code until those lines are filled.

## 138.6  The smallest useful startup code

Create `start.S`:

```asm
.section .text.start
.global _start

_start:
    ldr x0, =_stack_top
    mov sp, x0
    bl inmate_main

1:
    wfi
    b 1b
```

What this does:

```text
set stack pointer
call C code
wait forever when C returns
```

There is no C runtime here. No `main(argc, argv)`. No libc. No exit syscall.

## 138.7  The linker script

Create `inmate.ld`.

Replace `0x7c000000` with the inmate RAM start from your cell config:

```ld
ENTRY(_start)

MEMORY
{
    RAM (rwx) : ORIGIN = 0x7c000000, LENGTH = 16M
}

SECTIONS
{
    . = ORIGIN(RAM);

    .text : {
        *(.text.start)
        *(.text*)
    } > RAM

    .rodata : {
        *(.rodata*)
    } > RAM

    .data : {
        *(.data*)
    } > RAM

    .bss : {
        __bss_start = .;
        *(.bss*)
        *(COMMON)
        __bss_end = .;
    } > RAM

    . = ALIGN(16);
    . = ORIGIN(RAM) + LENGTH(RAM);
    _stack_top = .;
}
```

This script says:

```text
put code at the start of inmate RAM
put read only data after code
put initialized data after that
put zero data after that
place stack at the top of inmate RAM
```

For a real inmate, you may reserve a fixed stack size and detect overflow. For the first lab, this is enough.

## 138.8  A C file that does not need libc

This first version uses a PL011 UART because it is easy to understand. Treat it as a template, not as a guaranteed QEMU ARM64 Jailhouse demo binary.

Create `main.c`:

```c
#include <stdint.h>

#define UART_BASE 0x09000000UL
#define UART_DR   (*(volatile uint32_t *)(UART_BASE + 0x00))
#define UART_FR   (*(volatile uint32_t *)(UART_BASE + 0x18))
#define UART_FR_TXFF (1U << 5)

static void uart_putc(char c)
{
    while (UART_FR & UART_FR_TXFF) {
    }

    UART_DR = (uint32_t)c;
}

static void uart_puts(const char *s)
{
    while (*s != '\0') {
        if (*s == '\n') {
            uart_putc('\r');
        }
        uart_putc(*s);
        s++;
    }
}

void inmate_main(void)
{
    uart_puts("hello from bare-metal Jailhouse inmate\n");

    for (;;) {
        __asm__ volatile("wfi");
    }
}
```

This assumes a PL011 UART at `0x09000000`, which is the QEMU `virt` UART base used by many ARM examples.

But do not trust the example. Check the inmate config:

```text
If the UART is not assigned to the inmate, this code is wrong.
If Linux still owns that UART, this code is wrong.
If the console uses a virtual Jailhouse console instead, this code is not the right output path.
```

One device has one owner. That rule is the whole game.

The stock Jailhouse `gic-demo.bin` is a better first proof because its source and cell config are already matched by the Jailhouse project. Your own PL011 inmate is the next experiment after you have identified which console or MMIO region the inmate really owns.

## 138.9  Build without libc

Create `Makefile`:

```make
CROSS_COMPILE ?= aarch64-linux-gnu-
CC := $(CROSS_COMPILE)gcc
OBJCOPY := $(CROSS_COMPILE)objcopy

CFLAGS := -Wall -Wextra -ffreestanding -fno-stack-protector -fno-pic \
          -mgeneral-regs-only -O2
LDFLAGS := -nostdlib -Wl,-T,inmate.ld -Wl,-Map,inmate.map

all: inmate.bin

inmate.elf: start.S main.c inmate.ld
	$(CC) $(CFLAGS) $(LDFLAGS) start.S main.c -o $@

inmate.bin: inmate.elf
	$(OBJCOPY) -O binary $< $@

clean:
	rm -f inmate.elf inmate.bin inmate.map
```

Build:

```sh
$ make
$ file inmate.elf inmate.bin
$ aarch64-linux-gnu-objdump -h inmate.elf
```

Check the map:

```sh
$ grep -E "_start|_stack_top|\\.text" inmate.map
```

Expected idea:

```text
_start is at the inmate link address
stack top is inside the inmate RAM region
```

## 138.10  Load your inmate

Boot the QEMU ARM64 Jailhouse image from Chapter 137.

Copy your binary into the guest. Use the easiest path available:

```sh
$ scp inmate.bin root@QEMU_IP:/root/
```

If networking is not available, use a shared folder, rebuild the image, or copy through the QEMU disk image. The transport is not the lesson.

Inside the QEMU guest, first prove the stock demo still works:

```sh
# modprobe jailhouse
# jailhouse enable /path/to/qemu-arm64.cell
# jailhouse cell create /path/to/qemu-arm64-inmate-demo.cell
# jailhouse cell load inmate-demo /path/to/gic-demo.bin
# jailhouse cell start inmate-demo
```

Watch the console or the output path used by the demo image.

Expected result:

```text
the stock inmate produces timer or interrupt output
Linux root cell stays alive
```

Only after that proof should you shut down the cell and load your own binary:

```sh
# jailhouse cell shutdown inmate-demo
# jailhouse cell load inmate-demo /root/inmate.bin
# jailhouse cell start inmate-demo
```

Expected result if the PL011 ownership assumption is correct:

```text
hello from bare-metal Jailhouse inmate
```

If you do not see output, first check whether the inmate is running:

```sh
# jailhouse cell list
```

A silent inmate is not automatically a dead inmate.

## 138.11  If the UART path is wrong

Many first attempts fail because the console assumption is wrong.

There are three common output paths:

```text
real or emulated UART MMIO
Jailhouse virtual debug console
shared memory buffer
```

If your config does not assign the PL011 UART to the inmate, do not keep poking `0x09000000`.

Instead, use the demo binary and config as the reference:

```sh
# jailhouse cell load inmate-demo /path/to/gic-demo.bin
# jailhouse cell start inmate-demo
```

If the stock demo prints but your binary does not, compare:

```text
entry address
link address
console path
binary format
CPU mode expectation
```

If neither prints, debug the cell config and QEMU console setup.

## 138.12  Add a shared-memory heartbeat

Printing is useful, but products communicate through protocols.

Add one shared page to the inmate config only after the print path works.

A simple memory layout:

```text
offset 0x00: magic
offset 0x04: version
offset 0x08: root_to_inmate_counter
offset 0x0c: inmate_to_root_counter
offset 0x10: status
```

Define a struct:

```c
#include <stdint.h>

#define SHMEM_BASE 0x7faf0000UL

struct shared_page {
    volatile uint32_t magic;
    volatile uint32_t version;
    volatile uint32_t root_to_inmate_counter;
    volatile uint32_t inmate_to_root_counter;
    volatile uint32_t status;
};

static struct shared_page *const shmem = (void *)SHMEM_BASE;
```

Then update a counter:

```c
shmem->magic = 0x4a48494dU;
shmem->version = 1;

for (;;) {
    shmem->inmate_to_root_counter++;
    __asm__ volatile("wfi");
}
```

The root cell can inspect that memory only if the root cell also has a mapping for it through a driver or test tool.

Do not build a product protocol by opening `/dev/mem` and hoping. This is a lab trick, not an architecture.

## 138.13  Shared memory rules

Shared memory is where many mixed-criticality designs get messy.

Use rules:

```text
fixed layout
explicit version
single writer for each field
bounded message size
clear reset state
no pointers across the boundary
no unbounded strings
no shared ownership of hardware registers
```

Bad protocol:

```text
Linux writes any field whenever it wants
inmate writes any field whenever it wants
both sides share pointers
both sides assume the other side is alive
```

Good protocol:

```text
Linux owns command fields
inmate owns status fields
both sides check version
both sides can detect stale data
watchdog policy is written down
```

This is more important than the hypervisor.

## 138.14  Reload loop

During development you need a repeatable loop:

```sh
# jailhouse cell shutdown inmate-demo
# jailhouse cell destroy inmate-demo
# jailhouse cell create /path/to/qemu-arm64-inmate-demo.cell
# jailhouse cell load inmate-demo /root/inmate.bin
# jailhouse cell start inmate-demo
```

If `shutdown` is not implemented, `destroy` may be the only practical development path.

Record what your inmate supports:

```text
clean shutdown: yes or no
reload without disabling Jailhouse: yes or no
requires full QEMU restart: yes or no
```

Production systems need a clean stop and recovery story. Labs can be rough, but the notes should be honest.

## 138.15  Failure lab A: wrong link address

Change the linker origin to a wrong address:

```ld
ORIGIN = 0x70000000
```

Build again and load the binary.

Expected result:

```text
no output
cell crash
or invalid memory access reported by Jailhouse
```

Reason:

```text
the binary executes as if RAM starts somewhere else
```

Put the correct address back.

Lesson:

```text
cell config and linker script are one contract
```

## 138.16  Failure lab B: touch a device you do not own

Change the UART base to a nonsense MMIO address:

```c
#define UART_BASE 0x0a000000UL
```

Build and run.

Expected result:

```text
no output
data abort
Jailhouse access violation
or an inmate that waits forever
```

Reason:

```text
the inmate can only touch assigned memory and MMIO regions
```

Lesson:

```text
MMIO belongs in the cell config before code uses it
```

## 138.17  Failure lab C: remove the stack

Move `_stack_top` outside the inmate RAM region.

Expected result:

```text
crash on first C call
or silent failure
```

Reason:

```text
the first function call stores state through the stack pointer
```

Lesson:

```text
bare-metal code needs a real runtime contract, even when it is tiny
```

## 138.18  Move to Zephyr

Now Zephyr is reasonable.

Zephyr gives you:

```text
scheduler
drivers
devicetree
logging
timers
IPC libraries
build system
```

But Zephyr still must obey the same Jailhouse contract:

```text
link address matches cell RAM
drivers match assigned devices
interrupts match assigned IRQs
shared memory matches both sides
console path is real
```

The cell config does not become optional because Zephyr is present.

## 138.19  Install Zephyr tools

Use a Python virtual environment:

```sh
$ sudo apt install python3-venv python3-pip
$ mkdir -p ~/imx6ull/zephyr-lab
$ cd ~/imx6ull/zephyr-lab
$ python3 -m venv .venv
$ . .venv/bin/activate
$ pip install west
```

Fetch Zephyr:

```sh
$ west init zephyrproject
$ cd zephyrproject
$ west update
$ west zephyr-export
$ pip install -r zephyr/scripts/requirements.txt
```

Record versions:

```sh
$ west --version | tee ~/imx6ull/jailhouse-lab/logs/west-version.txt
$ git -C zephyr rev-parse HEAD | tee ~/imx6ull/jailhouse-lab/logs/zephyr-commit.txt
```

## 138.20  Build a normal Zephyr QEMU sample first

Before Jailhouse, prove Zephyr builds:

```sh
$ cd ~/imx6ull/zephyr-lab/zephyrproject/zephyr
$ west boards | grep -i qemu
$ west build -b qemu_cortex_a53/qemu_cortex_a53 samples/hello_world
```

If your Zephyr release uses the older short board name, use:

```sh
$ west build -b qemu_cortex_a53 samples/hello_world
```

Use the exact target printed by `west boards`. The important part is that this is the ARM64 QEMU Cortex-A53 board, not a Cortex-M board.

Run the normal Zephyr QEMU target if supported by your setup:

```sh
$ west build -t run
```

This test is not Jailhouse. It proves the Zephyr toolchain and board support before you mix in cells.

## 138.21  What must change for Zephyr as an inmate

A normal Zephyr QEMU board assumes it owns the machine.

A Zephyr inmate owns only a partition.

You must align:

```text
Zephyr link address
Zephyr RAM size
Zephyr device tree
Zephyr console
Zephyr interrupt controller view
Jailhouse inmate cell config
```

Start from the smallest sample:

```text
samples/hello_world
```

Avoid networking, storage, and complex drivers until hello-world prints from the inmate cell.

## 138.22  Zephyr resource-table path

For Linux plus a remote processor, Zephyr has OpenAMP resource-table samples. That is especially relevant on STM32MP1 in Chapter 139.

For Jailhouse, the resource table is not the root mechanism. Jailhouse uses cell configs.

So separate the two paths:

```text
Jailhouse inmate on A-core:
  Jailhouse cell config is the hardware ownership contract.

STM32MP1 M4 firmware:
  remoteproc resource table and RPMsg describe communication resources.
```

This distinction prevents a lot of confusion.

## 138.23  Lab A deliverables: bare-metal inmate

Create:

```text
~/imx6ull/jailhouse-lab/inmates/baremetal/start.S
~/imx6ull/jailhouse-lab/inmates/baremetal/main.c
~/imx6ull/jailhouse-lab/inmates/baremetal/inmate.ld
~/imx6ull/jailhouse-lab/inmates/baremetal/Makefile
~/imx6ull/jailhouse-lab/inmates/baremetal/inmate.map
~/imx6ull/jailhouse-lab/inmates/baremetal/inmate.bin
```

Write this note:

```text
cell RAM start:
cell RAM size:
link address:
stack top:
console path:
inmate output:
reload loop:
one failure tested:
```

The lab is complete when:

```text
Linux root cell is alive
bare-metal inmate starts
bare-metal inmate produces visible evidence
Linux root cell is still alive
```

## 138.24  Lab B deliverables: Zephyr inmate planning

Before making Zephyr run as an inmate, create a mapping table:

```text
Jailhouse inmate RAM start:
Zephyr CONFIG_SRAM_BASE_ADDRESS:
Jailhouse inmate RAM size:
Zephyr CONFIG_SRAM_SIZE:
Jailhouse console MMIO:
Zephyr console device:
Jailhouse inmate CPU:
Zephyr CPU assumption:
Jailhouse shared memory:
Zephyr shared memory node:
```

If any line is unknown, do not debug Zephyr yet. The contract is incomplete.

## 138.25  Product lesson

The useful product pattern is not:

```text
we ran an RTOS under a hypervisor
```

The useful product pattern is:

```text
Linux owns complex services
the inmate owns one bounded real-time responsibility
the two sides communicate through a small protocol
the hardware ownership table is reviewed like safety code
```

That is why the bare-metal inmate matters. It shows the boundary without hiding it inside an RTOS.

## 138.26  Troubleshooting

**The inmate does not print**

Check:

```text
is the cell running?
is the console assigned?
does the UART base match the assigned MMIO?
does the inmate use the right output path?
```

**The inmate crashes immediately**

Check:

```text
link address
load address
stack address
binary format
cell RAM flags
```

**The root cell freezes**

Check:

```text
memory overlap
device ownership overlap
wrong interrupt assignment
bad cell config
```

**Zephyr builds but does not run as inmate**

Return to the bare-metal inmate.

Then compare:

```text
entry point
linker map
devicetree memory
console device
interrupt controller setup
```

## 138.27  What comes next

Jailhouse taught us static partitioning.

Chapter 139 studies a different and very practical production pattern: Linux on Cortex-A7 plus RTOS firmware on a Cortex-M4 companion core. That is not a hypervisor lab, but for STM32MP1 it is often the better architecture.
