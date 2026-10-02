# Chapter 1: Preface and how to use this book

## 1.1  Why this book exists

Many books and tutorials show how to get embedded Linux running on a board. Most follow the same process: install a vendor BSP, run `bitbake` or `make`, flash an SD card, and log in. This can produce a Linux prompt quickly.

But this process does not explain how the system works. The BSP set up DDR, Yocto built the toolchain, U-Boot's defconfig selected its configuration, and the kernel's `imx_v7_defconfig` enabled drivers. If a different DRAM chip or custom IOMUX setting causes a failure, you may not know which layer to debug.

This book explains the path from power on to a running Linux system on the i.MX6ULL. You will implement selected mechanisms yourself: a boot-image header, startup code, a linker script, a page table, and a device tree. You will then build existing U-Boot and Linux sources rather than reimplement them. The first root filesystem contains a single statically-linked program.

After doing this work directly, we use the higher-level tools: Buildroot in Chapter 35, our own toolchain in Chapter 122, Yocto in Chapter 123, and secure boot in Chapter 124. You will know what each tool does because you have already performed the underlying steps.

This takes patience, but it gives you the knowledge needed to diagnose failures in those tools later.

## 1.2  Who this book is for

You are an embedded engineer with microcontroller experience. You have written firmware in C for Cortex-M or similar parts, read a reference manual, and configured pin multiplexers and clock trees.

You can read a schematic, solder a wire, and you know what a power rail is.

You may have used Linux on an embedded target or followed a vendor BSP through a Yocto build, but you want to understand each layer in detail.

You are not a Linux expert. You may not know what a "wait queue" is, or whether `/sys/class/gpio` is a real filesystem, or what the difference between `vmlinux` and `zImage` is. By Chapter 30, you will.

No prior Linux shell experience is assumed. Chapter 3 explains the shell operations used during setup. Keep a notebook of unfamiliar commands and their effects.

## 1.3  What "raw" means in this book

A few concrete commitments:

- We begin with two official prebuilt Arm compilers, one for bare metal and one for Linux. Chapter 122 explains toolchain construction.
- We use **mainline** sources for U-Boot and Linux. [BSP-to-mainline migration](../part8-debug/ch122A-bsp-mainline-migration.md) is a later comparison study.
- Runnable labs give input files, a working directory, build commands, and a result to check. Reproduction means following the documented versions and prerequisites; it does not imply byte-identical output across hosts.
- Configuration is edited explicitly, with explanations of the fields used. Repeated register settings can refer back to an earlier explanation.
- We **avoid Yocto, Buildroot, and other build frameworks** until we have performed the same work by hand.

## 1.4  Scope and optional extensions

- **Main path:** one i.MX6ULL board, from bare metal through Linux drivers. Board-specific registers and DDR settings do not transfer unchanged to another SoC.
- **Optional extensions:** [PREEMPT_RT](../part6-drivers/ch52A-preempt-rt.md), [containers](../part5-rootfs/ch35C-containers-on-embedded.md), and Part IX's QEMU/STM32MP1 targets come after the fundamentals. They are not prerequisites for the first Linux boot.
- **Android.** It is a wholly separate userspace stack on top of the same kernel, different init (`init.rc`), different libc (Bionic), different IPC (Binder), different build (Soong). The kernel chapters of this book apply directly. The userspace chapters do not. If your target is Android, follow this book through Chapter 35 and then branch to AOSP documentation.
- **Kubernetes at the edge:** not a deployment guide covered here.
- **Application programming on Linux.** You will use a shell and write a few C test programs, but we are not teaching POSIX threads or `select`/`epoll` as such.

## 1.5  How each chapter is organized

Practical chapters use recurring teaching elements, but their section counts and order vary with the task. Conceptual chapters may produce an explanation rather than an executable artifact.

1. **What**: the concrete artifact this chapter builds. *Object first.* A bootable image, a working driver, a measurable behavior change.
2. **Why**: the problem that motivates the artifact. What does the system look like *without* this chapter's work? What breaks?
3. **How**: the mechanics. Register-by-register, function-by-function, with the exact NXP reference-manual section or Linux source file cited.
4. **Focus**: one or two ideas needed by the next several chapters.
5. **Lab**: a deliverable with explicit prerequisites and an observable check.
6. **Pitfalls**: failure mechanisms, symptoms, and checks to distinguish them.
7. **Going deeper**: pointers to the i.MX6ULL Reference Manual, Linux source paths, LWN articles, mailing-list threads, and academic papers for readers who want to go past what the chapter covers.

## 1.6  Lab discipline

The main path's labs are checkpoints for the next practical step. Optional tracks have their own prerequisites; they do not block the first-image path.

If you read Chapter 14 without bringing up DDR on a board, you will learn the names of steps such as ZQ calibration and write leveling, but not how to diagnose a failing memory test. The lab provides that practical experience.

To get the most out of the book:

- Run every command yourself. **Do not** paste a snippet from a chapter without first reading what it does.
- Stop immediately if power wiring, a storage destination, or an irreversible operation is uncertain. Do not experiment past a safety warning.
- For other failures, find the last successful checkpoint, confirm the working directory and environment, and record the exact command and complete error. Consult the relevant pitfalls section, then seek help with that evidence. A missing prerequisite or book error is not a test of persistence.

## 1.7  Code listings

Lab code is **included in the chapters**; there is no separate code download. Create the named files in your workspace. Listings labeled pseudocode, fragments, or illustrative output explain a concept and are not standalone runnable programs.

## 1.8  Conventions

### Prompts

We distinguish two machines and several command contexts:

```
$        a regular user prompt on the host PC
#        a root prompt on the host PC (used sparingly)
=>       the U-Boot prompt
target$  a regular user prompt on the i.MX6ULL board
target#  a root prompt on the i.MX6ULL board
```

Prompt markers are not part of the command: do not type `$`, `#`, `target#`, or `=>`. In prompt examples, `#` means a root shell; inside a shell script it starts a comment. Commands using `sudo` still start at the normal user's `$` prompt. A block without prompts is file content or an explicitly identified command block.

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

ASCII. We do not require any rendering tools to read the book.

## 1.9  How the chapters depend on each other

For the first pass, follow Chapters 1-8, then build the first LED image in Chapter 9 and the UART program in Chapter 12 with their intervening prerequisites. Chapters 3, 6, and 8 prepare or inspect; they do not yet prove that your code runs on the board. The first Linux boot comes after U-Boot and the kernel builds.

Experienced readers can skip Part II if they already have a working board and can complete Chapter 19's U-Boot build/transfer prerequisites. Part II explains the clocks, DDR, exceptions, and MMU work otherwise performed by U-Boot and Linux.

A pruning guide for readers in different situations:

| If you... | Read | Skim | Skip |
|-----------|------|------|------|
| Want the full experience | All | none | none |
| Already wrote MCU firmware and want Linux | 1-3, 4-8, 19+ | 9, 17 | 10-16, 18 |
| Already shipped Linux on a different SoC, want i.MX6ULL specifics | 1, 5, 7, 19-24, 27 | 25-35 | 9-18 |
| Maintain an existing BSP, want driver depth | 1, 27, 36+ | 25-35 | 2-24 |

Even with these shorter reading paths, each chapter's *Why* and *Focus* sections provide the context needed to start in the middle of the book.

## 1.10  A note on the i.MX 6ULL Reference Manual

Keep revision 1 (11/2017) of the *i.MX 6ULL Applications Processor Reference Manual* open beside you. The supplied PDF has 4,127 pages. You will not read it cover to cover; use its contents and register index to locate:

1. The register base address (the system memory map chapter).
2. The clock input to the block (the CCM chapter).
3. The IOMUX requirements for any external pins (the IOMUXC chapter).
4. The interrupt vector number, if any (the GIC SPI table).
5. The initialization sequence the manufacturer recommends (usually a numbered list at the start of the block's chapter).

Use this five-item check for every new peripheral. It provides a repeatable starting point for custom-board bring-up.

---

> This book is intentionally detailed. Take time to complete the labs and verify the expected results before moving on.

> Next: [Chapter 2: What embedded Linux is](ch02-what-is-embedded-linux.md). The [full table of contents](../toc.md) and [draft status](../status.md) are reference pages, not prerequisites before Chapter 1.

```{include} ../_navigation.md
```
