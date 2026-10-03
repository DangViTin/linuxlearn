# Chapter 1: Preface and how to use this book

## 1.1  Why this book exists

If you have brought up a microcontroller board, you know the satisfaction of the first working LED. There is not much software between the reset handler and the GPIO register, so you can usually follow the whole path. Moving to embedded Linux changes that. Before your application runs, several programs have already configured memory, loaded other programs, and decided which hardware they can use.

A vendor board-support package, usually shortened to **BSP**, can get all of this running for you. Install its tools, build an image, write an SD card, and you may soon have a Linux prompt. That is useful, especially when you need to evaluate a board. But a successful build does not tell you why the board boots, or where to look when a modified board stops booting.

Suppose the DDR chip changes, or a UART moves to a different pair of pins. Which setting belongs to the bootloader? Which belongs to Linux? Why does a program that compiled successfully produce nothing on the board? These are the questions we will work through on the i.MX6ULL.

We begin with small programs whose behavior we can follow from start to finish. We write startup code, place it with a linker script, and give the Boot ROM the header it expects. Later we build a page table and describe the board with a device tree. Then we build U-Boot and Linux from their existing sources; we are learning how they work, not writing replacements for them. Our first root filesystem contains just one statically-linked program.

Buildroot enters in Chapter 35, toolchain construction in Chapter 122, Yocto in Chapter 123, and secure boot in Chapter 124. By then, their inputs and outputs will be familiar. When a large build fails, you will have smaller pieces you can inspect and test separately.

## 1.2  Who this book is for

This book is written for someone who has worked with microcontrollers and now wants to understand embedded Linux. You should be comfortable reading C, finding a register in a reference manual, and following a signal through a schematic. Experience with a Cortex-M part, such as an STM32, gives us useful comparisons throughout the early chapters.

Linux experience is not required. Perhaps you have never opened a Linux terminal. Perhaps you have built a vendor image but still cannot explain the difference between `vmlinux` and `zImage`. We will introduce those details when there is a reason to use them.

Chapter 3 explains the shell operations needed for setup. When a new command appears, read the explanation beside it and note what changed: a file, a directory, this terminal's environment, or a setting on the host. That habit matters more at the beginning than remembering every option.

## 1.3  What "raw" means in this book

Here, "raw" means making the early steps visible. We start with two official prebuilt Arm compilers: one for bare metal and one for Linux. They stay in the project directory, and we choose between them explicitly. Building a compiler is a separate subject, covered in Chapter 122.

For U-Boot and Linux, we use **mainline** sources: the upstream projects rather than a board vendor's modified distribution. The later [BSP-to-mainline migration](../part8-debug/ch122A-bsp-mainline-migration.md) chapter compares the two approaches. Configuration files are edited by hand, with the relevant fields explained beside the example. We postpone Yocto, Buildroot, and similar frameworks until we have done the underlying work ourselves.

A runnable lab supplies the input files, working directory, commands, and an observation to check. Follow its selected versions and prerequisites. Your output need not be byte-for-byte identical to another host's output; what matters is that it has the properties the lab asks you to inspect.

## 1.4  Scope and optional extensions

The main route follows one i.MX6ULL board from bare metal to Linux drivers. Staying with one target lets us return to the same LED, UART, and memory controller as the software grows. The reasoning is useful on other boards, but register addresses, DDR settings, and electrical requirements must be checked again.

There are optional routes into [PREEMPT_RT](../part6-drivers/ch52A-preempt-rt.md), [containers](../part5-rootfs/ch35C-containers-on-embedded.md), and Part IX's QEMU and STM32MP1 experiments. None is needed for the first Linux boot. Leave them until the main route makes sense, unless one directly matches your work.

This is not a Linux application-programming book. We use a shell and small C test programs, but do not teach POSIX threads or `select`/`epoll` in depth. Nor is this a Kubernetes deployment guide. Android also has its own userspace, including Bionic, Binder, and a different init and build system. The kernel material provides useful background for Android work, but the root-filesystem chapters here are not an AOSP setup guide.

## 1.5  How each chapter is organized

A chapter starts with a question or a practical task, then develops the explanation needed to work through it. Sometimes the result is a bootable image or a driver. Sometimes it is an understanding we need before touching the board. The section order follows that task rather than a fixed template.

Code and register descriptions are accompanied by explanations of what to look for. The labs give you a chance to check that understanding against a build, a hardware observation, or a manual lookup. The pitfalls sections collect symptoms worth recognizing when an experiment does not work.

The references at the end are for a second pass. You do not need to read every linked manual or source file before continuing. Use them when you want a fuller explanation or need to settle a specific question.

## 1.6  Lab discipline

Reading and experimenting teach different things. Chapter 14 can explain DDR calibration, but watching a memory test fail gives those settings a different meaning. Where you have the hardware, complete the main-route labs before depending on their results in a later chapter. Optional experiments have their own prerequisites and can wait.

Keep a short lab journal: what you built, what you expected, and what actually happened. A useful entry includes the working directory, compiler path, exact command, and complete error or observation. These details make a failed experiment much easier to revisit.

A few habits are worth keeping from the first lab:

- When a lab asks you to run a command, read it first and enter it yourself. A preview or an illustrative listing is not an instruction to execute it now.
- Stop immediately if power wiring, a storage destination, or an irreversible operation is uncertain. Do not experiment past a safety warning.
- For other failures, return to the last working step and check its prerequisites. Use the pitfalls section to narrow the problem, then ask for help with your recorded evidence. A missing prerequisite or an error in the book will not be fixed by repeating the same command.

## 1.7  Code listings

The lab code is **included in the chapters**. There is no separate download to unpack: create each named file in the workspace and save the corresponding listing there. Reading the explanation as you enter the code helps you see which parts belong to startup, the application, and the build.

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

This is register pseudocode, not a complete UART setup. UART1's two-bit gate is in `CCM_CCGR5` at `0x020C407C`; `11` selects the documented always-enabled gate state [RM 18.6.28]. MMIO definitions, pin mux, and the UART root clock are supplied later.

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

The diagrams are drawn with text, so they remain readable in the Markdown source as well as on the website. No separate diagram-rendering tool is needed.

## 1.9  How the chapters depend on each other

On a first reading, follow Chapters 1-8 in order. They prepare the host, explain the chip and its boot format, and check access to the board. Chapter 9 then puts those pieces together in the first LED image. Continue through the intervening chapters to the UART program in Chapter 12. U-Boot and the kernel builds come later, before the first Linux boot.

There is a useful distinction along this route: a successful build tells us about the host tools and the image; a visible response from our program tells us it executed on the board. Chapters 3, 6, and 8 prepare for that response but do not substitute for it.

Experienced readers can skip Part II if they already have a working board and can complete Chapter 19's U-Boot build/transfer prerequisites. Part II explains the clocks, DDR, exceptions, and MMU work otherwise performed by U-Boot and Linux.

If you already have experience in part of this route, the table below suggests a shorter reading path. Check the practical prerequisites before skipping a lab:

| If you... | Read | Skim | Skip |
|-----------|------|------|------|
| Want the full experience | All | none | none |
| Already wrote MCU firmware and want Linux | 1-3, 4-8, 19+ | 9, 17 | 10-16, 18 |
| Already shipped Linux on a different SoC, want i.MX6ULL specifics | 1, 5, 7, 19-24, 27 | 25-35 | 9-18 |
| Maintain an existing BSP, want driver depth | 1, 27, 36+ | 25-35 | 2-24 |

When starting in the middle, read the chapter's opening and check which earlier results it uses. Knowing a similar mechanism on another chip does not necessarily give you the board configuration this lab needs.

## 1.10  A note on the i.MX 6ULL Reference Manual

Keep revision 1 (11/2017) of the *i.MX 6ULL Applications Processor Reference Manual* nearby. Its 4,127 pages can look intimidating, but we will usually be looking for an answer about one block, not reading it from beginning to end.

For a new peripheral, start with these five questions:

1. Where are its registers? Start with the system memory map.
2. Which clock reaches the block? Follow the CCM clock path and gate.
3. Which pads carry its signals? Check the IOMUXC tables against the schematic.
4. Which interrupt ID identifies it? Look in the GIC SPI table if the block generates interrupts.
5. In what order should it be initialized? Look for the manufacturer's sequence near the start of the block's chapter.

The answers give you a starting point for both the code and the schematic. Chapter 5 walks through this search for UART1, and the later peripheral chapters repeat it in context. With practice, the manual becomes a place to answer questions rather than a document you have to memorize.

---

We begin with the part of Linux that changes the familiar MCU picture most: the separation between the kernel and an application. Once that distinction is clear, the tools and boot stages in the following chapters have a place to fit.

> Next: [Chapter 2: What embedded Linux is](ch02-what-is-embedded-linux.md). The [full table of contents](../toc.md) and [draft status](../status.md) are reference pages, not prerequisites before Chapter 1.

```{include} ../_navigation.md
```
