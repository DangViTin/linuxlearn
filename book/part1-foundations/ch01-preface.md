# Chapter 1: Preface and how to use this book

## 1.1  Why this book exists

Imagine this: the build finishes without an error, you prepare the image as instructed, and the board gives you nothing. No Linux prompt. No useful serial message. The files on the host look convincing, but you cannot yet tell whether the processor reached your code.

If you have brought up a microcontroller board, you already have a way to approach that silence. Follow reset to startup, startup to `main()`, and `main()` to the GPIO register. There may be a mistake somewhere, but the path is small enough to inspect. On an embedded Linux board, several programs run before your application gets a turn. Memory must be prepared, images must be loaded, and hardware must be described. Which of those steps did the board actually reach?

```{figure} ../illustrations/part1/01-build-is-not-execution.png
:alt: A laptop reports BUILD OK, but the board asks whether its code is running. A successful host build is not proof of execution on the board.
:width: 100%
:figclass: concept-sketch
:name: fig-build-is-not-execution

The laptop is pleased with itself. We still need an answer from the board. A clean build checks the host's work. A response from our program, such as an LED change or a printed message, tells us it ran on the board.
```

A vendor board-support package, usually shortened to **BSP**, can give you a working system quickly. Install its tools, build an image, write an SD card, and you may have a Linux prompt. That is a useful starting point. The harder moment comes when you change the design: a different DDR chip, a UART on different pins, a board that no longer matches the supplied image. Now you need to know which setting belongs to the bootloader, which belongs to Linux, and which assumption came from the old hardware.

This book follows those questions on the i.MX6ULL. Our first visible result will be modest: an LED controlled by a program small enough to follow from its first instruction. To get there, we write startup code, choose its memory layout, and give the Boot ROM the header it expects. Each part has a job we can explain.

The same board then takes us further. We build a page table, describe the hardware with a **device tree** (the hardware description passed to Linux), and build U-Boot and Linux from their existing sources. We are learning how those projects work, not writing replacements for them. Our first root filesystem contains just one statically-linked program. Even when the software becomes large, we keep asking what happened before the next step could run.

Buildroot enters in Chapter 35, toolchain construction in Chapter 122, Yocto in Chapter 123, and secure boot in Chapter 124. Their inputs will make more sense after we have worked with the pieces ourselves. A large build may still fail. The difference we want is that you can choose something specific to inspect instead of starting over and hoping.

## 1.2  Who this book is for

If you can read C, find a register in a reference manual, and follow a signal through a schematic, you have the starting point this book needs. Experience with a Cortex-M part, such as an STM32, gives us something familiar to return to when the Cortex-A7 behaves differently.

Linux experience is not required. The terminal may be new to you; the hardware is not. Perhaps you have built a vendor image but still cannot explain why the directory contains both `vmlinux` and `zImage`. You do not need to settle that question before opening Chapter 2. We will meet those files when we have a reason to inspect them.

Chapter 3 explains the shell operations needed for setup. When a new command appears, read the explanation beside it and note what changed: a file, a directory, this terminal's environment, or a setting on the host. That habit matters more at the beginning than remembering every option.

Before a hardware lab, have these items ready:

- An i.MX6ULL board supported by the lab. Our worked schematic lookups use the Point Atom MINI v2.2 baseboard and its supplied core-board schematic; check the actual revision fitted to your board.
- The matching baseboard/core schematics and the supplier's power instructions for that combination. The schematics supplied with this book are not a validated power-connection guide. Obtain that guide from the board supplier before attaching a supply, USB cable, or adapter.
- A suitable digital multimeter, the documented supply, and USB **data** cables for the debug bridge and OTG port. An external UART adapter is optional where the built-in bridge is available.
- An x86_64 Linux host, or a suitable Ubuntu VM with device access, prepared in Chapter 3. The host-only exercises can proceed before the board is connected.

A spare SD card and Ethernet connection are needed for later storage/network labs, not for the first USB-loaded LED image. JTAG and the peripheral add-ons are optional.

## 1.3  What "raw" means in this book

Here, "raw" means being able to point to the thing that did the work. Which compiler produced the instructions? Which file described where they belong in memory? Which header told the chip where to begin? We start with two official prebuilt Arm compilers, one for bare metal and one for Linux. They stay in the project directory, and we choose between them explicitly. Building a compiler is a separate subject, covered in Chapter 122.

For U-Boot and Linux, we use **mainline** sources: the upstream projects rather than a board vendor's modified distribution. The later [BSP-to-mainline migration](../part8-debug/ch122A-bsp-mainline-migration.md) chapter compares the two approaches. Configuration files are edited by hand, with the relevant fields explained beside the example. We postpone Yocto, Buildroot, and similar frameworks until we have done the underlying work ourselves.

A runnable lab supplies the input files, working directory, commands, and an observation to check. Follow its selected versions and prerequisites. Your output need not be byte-for-byte identical to another host's output; what matters is that it has the properties the lab asks you to inspect.

## 1.4  Scope and optional extensions

The main route follows one i.MX6ULL board from bare metal to Linux drivers. The LED in the first experiment will still be there when Linux owns its GPIO. So will the UART whose registers we configured by hand. Returning to familiar hardware lets us see what the new software layer changes. The reasoning is useful on other boards, but register addresses, DDR settings, and electrical requirements must be checked again.

```{figure} ../illustrations/part1/09-same-led-two-routes.png
:alt: Two experiments use the same LED. Bare-metal code controls GPIO directly. Later, a Linux application requests an operation through a kernel driver that controls GPIO.
:width: 100%
:figclass: concept-sketch
:name: fig-same-led-two-routes

We will visit this LED twice. First, our small program does the register work. Later, a Linux application uses a driver interface. The two rows are different experiments on the same hardware, not two programs trying to drive it at once.
```

There are optional routes into [PREEMPT_RT](../part6-drivers/ch52A-preempt-rt.md), [containers](../part5-rootfs/ch35C-containers-on-embedded.md), and Part IX's QEMU and STM32MP1 experiments. None is needed for the first Linux boot. Leave them until the main route makes sense, unless one directly matches your work.

This is not a Linux application-programming book. We use a shell and small C test programs, but do not teach POSIX threads or `select`/`epoll` in depth. Kubernetes deployment and Android system builds are outside the route.

## 1.5  How each chapter is organized

Read the early chapters with a result in mind. Sometimes it is a program; sometimes it is an explanation for a puzzling observation. Chapter 6, for example, starts with a build command and asks why it produces several different files. The names and formats become useful because they help us answer that question.

The explanation beside a listing tells you what to look for. A lab then gives you something to compare with your expectation: a build result, a hardware observation, or a manual lookup. If the two disagree, the pitfalls section can help you decide what to check next. There is no need to turn every unfamiliar name into a memorization task.

The references at the end are for a second pass. You do not need to read every linked manual or source file before continuing. Use them when you want a fuller explanation or need to settle a specific question.

## 1.6  Lab discipline

Reading and experimenting teach different things. Chapter 14 can explain DDR calibration, but watching a memory test fail gives those settings a different meaning. Where you have the hardware, complete the main-route labs before depending on their results in a later chapter. Optional experiments have their own prerequisites and can wait.

When a test fails, it is tempting to change three settings and build again. If that works, you have a running program but may still have no explanation. Keep a short lab journal instead: what you built, what you expected, and what actually happened. Include the working directory, compiler path, exact command, and complete error or observation. A week later, those details are much more useful than "it worked after another rebuild."

A few habits are worth keeping from the first lab:

- When a lab asks you to run a command, read it first and enter it yourself. A preview or an illustrative listing is not an instruction to execute it now.
- Stop immediately if power wiring, a storage destination, or an irreversible operation is uncertain. Do not experiment past a safety warning.
- For other failures, return to the last working step and check its prerequisites. Use the pitfalls section to narrow the problem, then ask for help with your recorded evidence. A missing prerequisite or an error in the book will not be fixed by repeating the same command.

## 1.7  Code listings

The lab code is **included in the chapters**. There is no separate download to unpack: create each named file in the workspace and save the corresponding listing there. A startup file can look uninviting at first. Read it in the groups explained beside it: prepare the stack, clear a memory range, call the C function. Its lines will have a purpose before you ask them to run.

Not every listing is a program to run. Pseudocode shows an idea; a fragment shows part of a larger implementation; illustrative output shows what a tool may report. Those labels are there to distinguish them from complete lab inputs.

## 1.8  Conventions

### Prompts

Once the board runs software, you will often have two terminals open: one on the host and one connected to the board. The prompt tells you where a command belongs:

```
$        a regular user prompt on the host PC
#        a root prompt on the host PC (used sparingly)
=>       the U-Boot prompt
target$  a regular user prompt on the i.MX6ULL board
target#  a root prompt on the i.MX6ULL board
```

Type the command after the prompt, not the prompt itself. For example, `$ sudo picocom ...` means enter `sudo picocom ...` in your normal host terminal. The `#` in a root-prompt example is different from the `#` that begins a comment inside a shell script. Blocks without prompts are file contents or command blocks identified in the surrounding text.

### Registers and bits

Registers are written in uppercase with the bank prefix from the reference manual:

```
CCM_CCGR5 |= (3u << 24);    /* UART1 CG12: bits 25:24 = 11 */
```

This is register pseudocode, not a complete UART setup. UART1's two-bit gate is in `CCM_CCGR5` at `0x020C407C`; `11` enables it in run and WAIT modes, but not STOP [RM 18.6.28]. MMIO definitions, pin mux, and the UART root clock are supplied later.

When a bit field is named, square brackets denote a field rather than C array syntax:

```
CCM_CCGR5[CG12] = 3;       /* the same gate field, notation only */
```

### Numeric notation

Hex values are written with the C `0x` prefix everywhere except inside hex dumps. Megabytes and gigabytes use the IEC binary prefixes (MiB, GiB) when precision matters. "MB" is shorthand for the marketed quantity (board has "512 MB DDR3", the chip is actually 512 MiB).

### Addresses

When we cite a memory address, we cite the *physical* address unless we are discussing MMU mappings. Physical addresses on i.MX6ULL are 32 bits. In Chapter 17, virtual addresses are shown in the kernel and user ranges being discussed.

### Citations

References to the i.MX6ULL Reference Manual are written as **\[RM §28.5.3\]**. This means Chapter 28, Section 5.3 of the *i.MX 6ULL Applications Processor Reference Manual*, revision 1, 11/2017. Linux source citations look like **\[linux: drivers/gpio/gpio-mxc.c:142\]** and refer to `v6.6` unless noted.

### Diagrams

The small concept sketches pause over one idea at a time. Their captions explain the important distinction in ordinary text, too. A smiling chip is a character in the explanation, not an extra component to find on your board; these drawings are not wiring instructions or to-scale memory maps.

Detailed reference diagrams are also drawn with text, so they remain readable in the Markdown source as well as on the website. The sketches are ordinary image files; you do not need a separate diagram-rendering tool to read or build the book.

## 1.9  How the chapters depend on each other

On a first reading, follow Chapters 1-8 in order. They prepare the host, explain the chip and its boot format, and check access to the board. Chapter 9 then puts those pieces together in the first LED image. Continue through the intervening chapters to the UART program in Chapter 12. U-Boot and the kernel builds come later, before the first Linux boot.

Experienced readers can take a Linux-first route if they already have a working, supported board and meet [Chapter 19's build/transfer prerequisites](../part3-uboot/ch19-uboot-from-source.md). MCU experience alone is not that prerequisite. Part II explains the clocks, DDR, exceptions, and MMU work otherwise performed by U-Boot and Linux.

If you already have experience in part of this route, the table below suggests a shorter reading path. Check the practical prerequisites before skipping a lab:

| If you... | Read | Skim | Skip |
|-----------|------|------|------|
| Want the full experience | All | none | none |
| Have MCU experience but are new to Linux | 1-17, 19+ | none | optional Chapter 18/add-ons |
| Want Linux first and already meet Chapter 19's prerequisites | 1-8, 19+ | 9-17 | 18 |
| Already shipped Linux on a different SoC, want i.MX6ULL specifics | 1, 5, 7, 19-24, 27 | 25-35 | 9-18 |
| Maintain an existing BSP, want driver depth | 1, 27, 36+ | 25-35 | 2-24 |

When starting in the middle, read the chapter's opening and check which earlier results it uses. Knowing a similar mechanism on another chip does not necessarily give you the board configuration this lab needs.

## 1.10  A note on the i.MX 6ULL Reference Manual

Keep revision 1 (11/2017) of the *i.MX 6ULL Applications Processor Reference Manual* nearby. At 4,127 pages, it is a poor place to start with "I should learn all of this." Start with "I need the clock gate for UART1." That question takes you to a few relevant pages and gives you a reason to read them carefully.

For a new peripheral, start with these five questions:

1. Where are its registers? Start with the system memory map.
2. Which clock reaches the block? Follow the CCM clock path and gate.
3. Which pads carry its signals? Check the IOMUXC tables against the schematic.
4. Which interrupt ID identifies it? Look in the GIC SPI table if the block generates interrupts.
5. In what order should it be initialized? Look for the manufacturer's sequence near the start of the block's chapter.

The answers give you a starting point for both the code and the schematic. Chapter 5 works through this search for UART1, and the later peripheral chapters repeat it in context. You will not finish reading the whole manual before your first LED works. You will learn to find the pages that explain why it should work.

---

Before following the boot sequence, there is one change to the MCU picture worth understanding. You know how to write a GPIO register. Why would Linux put a driver interface between your application and that perfectly ordinary operation? That is where we begin.

> Next: [Chapter 2: What embedded Linux is](ch02-what-is-embedded-linux.md). The [full table of contents](../toc.md) and [draft status](../status.md) are reference pages, not prerequisites before Chapter 1.

```{include} ../_navigation.md
```
