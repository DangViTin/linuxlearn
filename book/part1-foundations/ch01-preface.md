---
chapter: 1
title: Preface and how to use this book
part: I — Foundations
estimated_pages: 8
status: draft
---

# Chapter 1 — Preface and how to use this book

## 1.1  Why this book exists

There is no shortage of books and tutorials that show you how to get embedded Linux running on a board. Most of them follow the same script: install a vendor BSP, run `bitbake` or `make`, flash an SD card, log in. Twenty minutes from `git clone` to a Linux prompt. Beautiful.

The trouble is that you learned almost nothing. The BSP set up the DDR, Yocto built your toolchain, U-Boot's defconfig set every register, and the kernel's `imx_v7_defconfig` enabled the drivers — all because someone else had done the work. If anything breaks, like a different DRAM chip or a custom IOMUX, you have no foothold to debug from. You can read the Linux source but you cannot *see* where the system came from.

This book is the opposite path. You will build every layer between power-on-reset and a running Linux system on the i.MX6ULL by hand. That means writing the boot image bytewise, setting DDR registers against the JEDEC sequence, hand-writing the linker script, page table, and device tree, then compiling U-Boot from source. You will read its source until every line is familiar, and boot a mainline Linux kernel — not a vendor fork — with a root filesystem built from a single statically-linked binary.

Only after we can do all of this from scratch do we permit ourselves the convenience tools: Buildroot in Chapter 35, our own toolchain in Chapter 122, Yocto in Chapter 123, secure boot in Chapter 124. By then the tools will feel like time-savers, not magic. You will know what each of them does because you have already done it the hard way.

It takes patience. The payoff is that no bug in those tools can hide from you later.

## 1.2  Who this book is for

You are an embedded engineer with a few years of microcontroller experience. You have written firmware in C for Cortex-M or similar parts. You have read a reference manual. You have configured pin multiplexers and clock trees. You have stared at an oscilloscope at 3 a.m. wondering why an interrupt isn't firing.

You can read a schematic, solder a wire, and you know what a power rail is.

You have heard about Linux on embedded targets — maybe shipped a product with it, maybe followed a vendor BSP through a Yocto build — but you have never been certain you understood what was happening underneath. You want that certainty.

You are not a Linux expert. You may not know what a "wait queue" is, or whether `/sys/class/gpio` is a real filesystem, or what the difference between `vmlinux` and `zImage` is. By Chapter 30, you will.

If that is roughly you, this book is written for you. If you have *no* embedded background at all — if "register" makes you think of a bank teller's window, Part II will feel cruel. There are gentler introductions; come back here after.

## 1.3  What "raw" means in this book

A few concrete commitments:

- The only black-box tool we permit ourselves for the first ~50 chapters is the **C compiler**, and we open even that one up in Chapter 122.
- We use **mainline** sources for U-Boot and Linux. Vendor BSPs are read in Part VII as a comparison study; they do not drive the main narrative.
- Every artifact — boot image, kernel image, device tree, root filesystem — is **built from a clean tree** by a script you can read. If you cannot regenerate the artifact, the chapter is not finished.
- We **never** copy-paste a configuration without explaining what each field does. The first time you see a DDR controller register, every bit of it is decoded. The second time you can look it up in the appendix.
- We **avoid Yocto, Buildroot, and other "framework" builders** until they have been thoroughly demystified by us having done the same work by hand.

This discipline is the point of the book. Skip it and you lose the point.

## 1.4  What this book does not cover

- **Other SoCs.** We pick the i.MX6ULL because it is a single-core Cortex-A7 part — simple enough that we can hold the whole boot path in our head — with excellent NXP documentation, an active mainline upstreaming history, and abundant cheap dev boards. The principles transfer to STM32MP1, AllWinner H3, Rockchip RK3308 and similar SoCs, but the register tables do not.
- **Real-time Linux.** PREEMPT_RT is mentioned in Chapter 30 and Chapter 43 but is not the focus.
- **Android.** It is a wholly separate userspace stack on top of the same kernel — different init (`init.rc`), different libc (Bionic), different IPC (Binder), different build (Soong). The kernel chapters of this book apply directly; the userspace chapters do not. If your target is Android, follow this book through Chapter 35 and then branch to AOSP documentation.
- **Container runtimes, Docker on embedded, Kubernetes at the edge.** Out of scope.
- **Application programming on Linux.** You will use a shell and write a few C test programs, but we are not teaching POSIX threads or `select`/`epoll` as such.

## 1.5  How each chapter is organized

Every chapter follows the same seven-section template. We will not deviate from it. The point is that once you have read three chapters you know exactly where to look for what you need.

1. **What** — the concrete artifact this chapter builds. *Object first.* A bootable image, a working driver, a measurable behavior change.
2. **Why** — the problem that motivates the artifact. What does the system look like *without* this chapter's work? What breaks?
3. **How** — the mechanics. Register-by-register, function-by-function, with the exact NXP reference-manual section or Linux source file cited.
4. **Focus** — one or two ideas that, once internalized, unlock the next several chapters. These are the lines you should underline if you read on paper.
5. **Lab** — a step-by-step deliverable. If you cannot reproduce it from a clean shell in your kitchen tomorrow morning, you have not finished the chapter.
6. **Pitfalls** — the specific traps real engineers fall into here. Each pitfall is something at least one experienced engineer has been burned by; not theoretical concerns.
7. **Going deeper** — pointers to the i.MX6ULL Reference Manual, Linux source paths, LWN articles, mailing-list threads, and academic papers for readers who want to go past what the chapter covers.

## 1.6  Lab discipline

The labs are not optional. They are the book.

If you read the prose of Chapter 14 (DDR3 initialization) without ever bringing up your own DDR, you will not learn what you came for. You will learn the *names* of the steps — "ZQ calibration", "write leveling" — but you will not have internalized the experience of seeing your board fail to read back what it wrote and discovering it was a single-bit timing skew.

To get the most out of the book:

- Keep a **lab journal**. A plain-text or Markdown file is fine. Write what you did, what worked, what did not, what you suspect. The journal is more valuable than the book.
- Run every command yourself. **Do not** paste a snippet from a chapter without first reading what it does.
- When something does not work — and many things will not — debug it for at least an hour before looking up the answer. The book includes "expected output" blocks specifically so you can tell when you are stuck.

## 1.7  Code listings

All code in this guide is **inline in the chapters** — there is no companion repository. Snippets are short enough to read end-to-end and copy directly into your own workspace. They are licensed **MIT**; kernel-module excerpts that quote GPL kernel sources inherit GPL-2.0-only per the kernel's license.

Keep your own per-chapter folder (`~/imx6ull-lab/chXX/` is one convention) for the work you build as you go. The guide does not ship a reference solution.

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

Hex values are written with the C `0x` prefix everywhere except inside hex dumps. Megabytes and gigabytes use the IEC binary prefixes (MiB, GiB) when precision matters. "MB" is shorthand for the marketed quantity (board has "512 MB DDR3" — the chip is actually 512 MiB).

### Addresses

When we cite a memory address, we cite the *physical* address unless we are inside a discussion of MMU mapping. Physical addresses on i.MX6ULL are 32 bits. Virtual addresses are written as `0xC00xxxxx` (kernel) or `0x00xxxxxx`–`0xBFxxxxxx` (user) once we get to MMU territory in Chapter 17.

### Citations

References to the i.MX6ULL Reference Manual are written as **\[RM §28.5.3\]** — meaning "Chapter 28, section 5.3 of the i.MX 6ULL Applications Processor Reference Manual, rev. 1, 11/2017". Linux source citations look like **\[linux: drivers/gpio/gpio-mxc.c:142\]**, against `v6.6` unless noted.

### Diagrams

ASCII first, SVG when ASCII fails. We do not require any rendering tools to read the book. Where a diagram is essential, it is also reproduced as a PNG in `figures/`.

## 1.9  How the chapters depend on each other

Part II (Chapters 9–18) is the only part an impatient reader can skip without losing the thread. You should not skip it anyway. It is where this book differs from every other embedded-Linux book on the shelf. It is also the part that will save you six months from now, when some bring-up problem traces back to a misconfigured AHB clock.

A pruning guide for readers in different situations:

| If you... | Read | Skim | Skip |
|-----------|------|------|------|
| Want the full experience | All | — | — |
| Already wrote MCU firmware and *just* want Linux | 1–3, 4–8, 19+ | 9, 17 | 10–16, 18 |
| Already shipped Linux on a different SoC, want i.MX6ULL specifics | 1, 5, 7, 19–24, 27 | 25–35 | 9–18 |
| Maintain an existing BSP, want driver depth | 1, 27, 36+ | 25–35 | 2–24 |

Even with these pruning paths, the seven-section template makes it cheap to jump in mid-book: each chapter's *Why* and *Focus* sections will catch you up on what you skipped.

## 1.10  A note on the i.MX 6ULL Reference Manual

You will need it open next to you for most of the book. It is roughly 5000 pages. You will not read it cover to cover. What you *will* do is learn how to navigate it. The single most useful skill in embedded Linux work, in this author's experience, is the ability to look at an unfamiliar peripheral block in a reference manual and within ten minutes locate:

1. The register base address (the system memory map chapter).
2. The clock input to the block (the CCM chapter).
3. The IOMUX requirements for any external pins (the IOMUXC chapter).
4. The interrupt vector number, if any (the GIC SPI table).
5. The initialization sequence the manufacturer recommends (usually a numbered list at the start of the block's chapter).

Five items, ten minutes, every new peripheral. That habit is what separates engineers who can bring up a custom board from engineers who can only run someone else's eval kit.

## 1.11  Where to ask for help

When the book leaves you stuck, the following are, in this author's experience, the best places to look:

- **The i.MX community forum** at NXP (free account). Real engineers from NXP read it, and many problems you will hit have already been answered.
- **The U-Boot mailing list** (`u-boot@lists.denx.de`). Read-only for a few weeks before posting.
- **The Linux kernel mailing lists** (`linux-arm-kernel`, the relevant subsystem list — `linux-i2c`, `linux-spi`, `linux-rtc`, etc.). Etiquette matters; read `Documentation/process/` before posting.
- **The Bootlin training material** (free, public). The best second source after this book.
- **LWN.net**. A subscription is one of the best deals in technical writing.

Stack Overflow is the worst place to ask about Linux internals. The kernel changes too fast and the upvoted answers go stale. Go to the source.

## 1.12  Acknowledgements

This book stands on work from the maintainers of mainline U-Boot and Linux, the Bootlin team, NXP's public documentation and community answers, and the Point Atom project that put low-cost i.MX6ULL hardware in the hands of many learners. Thanks also to the colleagues and readers who test commands, question unclear explanations, and send corrections.

## 1.13  Errata and corrections

The book's GitHub repository is the canonical place for errata. Open an issue or a pull request against the chapter file you found the error in.

---

> **One last thing before you turn the page.** This is a slow book. It rewards patience and punishes shortcut-taking. If you find yourself wanting to skip from Chapter 7 to Chapter 19, close the book and come back later. It will still be here.
