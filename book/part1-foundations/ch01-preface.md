# Chapter 1: Preface and how to use this book

## 1.1  Why this book exists

Many books and tutorials show how to get embedded Linux running on a board. Most follow the same process: install a vendor BSP, run `bitbake` or `make`, flash an SD card, and log in. This can produce a Linux prompt quickly.

But this process does not explain how the system works. The BSP set up DDR, Yocto built the toolchain, U-Boot's defconfig selected its configuration, and the kernel's `imx_v7_defconfig` enabled drivers. If a different DRAM chip or custom IOMUX setting causes a failure, you may not know which layer to debug.

This book is the opposite path. You will build every layer from power on to a running Linux system on the i.MX6ULL by hand. That means writing the boot image bytewise, setting DDR registers against the JEDEC sequence, hand-writing the linker script, page table, and device tree, then compiling U-Boot from source. You will boot a mainline Linux kernel, not a vendor fork, with a root filesystem built from a single statically-linked binary.

After doing this work directly, we use the higher-level tools: Buildroot in Chapter 35, our own toolchain in Chapter 122, Yocto in Chapter 123, and secure boot in Chapter 124. You will know what each tool does because you have already performed the underlying steps.

This takes patience, but it gives you the knowledge needed to diagnose failures in those tools later.

## 1.2  Who this book is for

You are an embedded engineer with microcontroller experience. You have written firmware in C for Cortex-M or similar parts, read a reference manual, and configured pin multiplexers and clock trees.

You can read a schematic, solder a wire, and you know what a power rail is.

You may have used Linux on an embedded target or followed a vendor BSP through a Yocto build, but you want to understand each layer in detail.

You are not a Linux expert. You may not know what a "wait queue" is, or whether `/sys/class/gpio` is a real filesystem, or what the difference between `vmlinux` and `zImage` is. By Chapter 30, you will.

## 1.3  What "raw" means in this book

A few concrete commitments:

- For the first ~50 chapters, the **C compiler** is the only major tool whose internals we do not inspect. Chapter 122 explains how the toolchain is built.
- We use **mainline** sources for U-Boot and Linux. Vendor BSPs are read in Part VII as a comparison study. They do not drive the main narrative.
- Every artifact, including the boot image, kernel image, device tree, and root filesystem, is **built from a clean tree** by a script you can read. If you cannot regenerate the artifact, the chapter is not finished.
- We **never** copy and paste a configuration without explaining what each field does. The first time you see a DDR controller register, we decode every field. Later uses can refer back to that explanation.
- We **avoid Yocto, Buildroot, and other build frameworks** until we have performed the same work by hand.

## 1.4  What this book does not cover

- **Other SoCs.** We use the i.MX6ULL because it is a single-core Cortex-A7 part with good NXP documentation, mainline support, and affordable development boards. The principles also apply to STM32MP1, Allwinner H3, Rockchip RK3308, and similar SoCs.
- **Real-time Linux.** PREEMPT_RT is mentioned in Chapter 30 and Chapter 43 but is not the focus.
- **Android.** It is a wholly separate userspace stack on top of the same kernel, different init (`init.rc`), different libc (Bionic), different IPC (Binder), different build (Soong). The kernel chapters of this book apply directly. The userspace chapters do not. If your target is Android, follow this book through Chapter 35 and then branch to AOSP documentation.
- **Container runtimes, Docker on embedded, Kubernetes at the edge.** Out of scope.
- **Application programming on Linux.** You will use a shell and write a few C test programs, but we are not teaching POSIX threads or `select`/`epoll` as such.

## 1.5  How each chapter is organized

Every chapter follows the same seven-section template. We will not deviate from it. The point is that once you have read three chapters you know exactly where to look for what you need.

1. **What**: the concrete artifact this chapter builds. *Object first.* A bootable image, a working driver, a measurable behavior change.
2. **Why**: the problem that motivates the artifact. What does the system look like *without* this chapter's work? What breaks?
3. **How**: the mechanics. Register-by-register, function-by-function, with the exact NXP reference-manual section or Linux source file cited.
4. **Focus**: one or two ideas needed by the next several chapters.
5. **Lab**: a step-by-step deliverable that you can reproduce from a clean shell.
6. **Pitfalls**: the specific mistakes real engineers make here. Each pitfall is something at least one experienced engineer has hit, not a theoretical concern.
7. **Going deeper**: pointers to the i.MX6ULL Reference Manual, Linux source paths, LWN articles, mailing-list threads, and academic papers for readers who want to go past what the chapter covers.

## 1.6  Lab discipline

The labs are not optional.

If you read Chapter 14 without bringing up DDR on a board, you will learn the names of steps such as ZQ calibration and write leveling, but not how to diagnose a failing memory test. The lab provides that practical experience.

To get the most out of the book:

- Run every command yourself. **Do not** paste a snippet from a chapter without first reading what it does.
- When something does not work, and many things will not, debug it for at least an hour before looking up the answer. The book includes "expected output" blocks specifically so you can tell when you are stuck.

## 1.7  Code listings

All code in this guide is **included in the chapters**. There is no companion repository. Snippets are short enough to read completely and place in your own workspace.

## 1.8  Conventions

### Prompts

We distinguish two shells:

```
$        a regular user prompt on the host PC
#        a root prompt on the host PC (used sparingly)
=>       the U-Boot prompt
target$  a regular user prompt on the i.MX6ULL board
target#  a root prompt on the i.MX6ULL board
```

When a command is host-only or target-only, the prompt makes it unambiguous.

### Registers and bits

Registers are written in uppercase with the bank prefix from the reference manual:

```
CCM_CCGR1 |= (1 << 12);     /* gate UART1 clock on */
```

When a single bit field is named, we use the manual's exact field name:

```
CCM_ANALOG_PLL_ARM[DIV_SELECT] = 88;   /* 24 MHz × 88 / 2 = 1056 MHz, then ÷2 again */
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

Part II (Chapters 9-18) can be skipped without breaking the later Linux sequence, but it explains the low-level work performed by U-Boot and the kernel. It is useful when a bring-up failure comes from clocks, DDR, exceptions, or the MMU.

A pruning guide for readers in different situations:

| If you... | Read | Skim | Skip |
|-----------|------|------|------|
| Want the full experience | All | none | none |
| Already wrote MCU firmware and want Linux | 1-3, 4-8, 19+ | 9, 17 | 10-16, 18 |
| Already shipped Linux on a different SoC, want i.MX6ULL specifics | 1, 5, 7, 19-24, 27 | 25-35 | 9-18 |
| Maintain an existing BSP, want driver depth | 1, 27, 36+ | 25-35 | 2-24 |

Even with these shorter reading paths, each chapter's *Why* and *Focus* sections provide the context needed to start in the middle of the book.

## 1.10  A note on the i.MX 6ULL Reference Manual

You will need it open next to you for most of the book. It is roughly 5000 pages. You will not read it cover to cover. What you *will* do is learn how to navigate it. The single most useful skill in embedded Linux work, in this author's experience, is the ability to look at an unfamiliar peripheral block in a reference manual and within ten minutes locate:

1. The register base address (the system memory map chapter).
2. The clock input to the block (the CCM chapter).
3. The IOMUX requirements for any external pins (the IOMUXC chapter).
4. The interrupt vector number, if any (the GIC SPI table).
5. The initialization sequence the manufacturer recommends (usually a numbered list at the start of the block's chapter).

Use this five-item check for every new peripheral. It provides a repeatable starting point for custom-board bring-up.

---

> This book is intentionally detailed. Take time to complete the labs and verify the expected results before moving on.
