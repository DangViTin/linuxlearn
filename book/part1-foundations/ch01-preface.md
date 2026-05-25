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

The trouble is that you have learned almost nothing. The vendor BSP brought up your DDR. Yocto cross-compiled your toolchain. U-Boot's `defconfig` set every register on your behalf. The kernel's `imx_v7_defconfig` enabled the right drivers because someone, somewhere, already did the work. If anything breaks — a different DRAM chip, a custom IOMUX, a peripheral the BSP doesn't know about — you have no foothold to debug from. You can read the Linux source but you cannot *see* where the system came from.

This book is the opposite path. We will build, by hand, every layer between *power-on-reset* and a running multi-process Linux system on the i.MX6ULL. We will write the boot image bytewise. We will configure the DDR controller register-by-register against the JEDEC sequence. We will hand-write the linker script, the page table, the device tree. We will compile U-Boot, then read its source until every line is familiar. We will boot a mainline Linux kernel — not a vendor fork — with a root filesystem built from a single statically-linked binary.

Only after we can do all of this from scratch do we permit ourselves the convenience tools: Buildroot in Chapter 35, our own toolchain in Chapter 60, Yocto in Chapter 61, secure boot in Chapter 62. By that point, the tools will feel like productivity wins rather than magic. You will know what each of them does because you have already done it the hard way.

The cost is patience. The reward is that no future bug in any of those tools can hide from you.

## 1.2  Who this book is for

You are an embedded engineer with a few years of microcontroller experience. You have written firmware in C for Cortex-M or similar parts. You have read a reference manual. You have configured pin multiplexers and clock trees. You have stared at an oscilloscope at 3 a.m. wondering why an interrupt isn't firing.

You can read a schematic, solder a wire, and you know what a power rail is.

You have heard about Linux on embedded targets — maybe shipped a product with it, maybe followed a vendor BSP through a Yocto build — but you have never been certain you understood what was happening underneath. You want that certainty.

You are not a Linux expert. You may not know what a "wait queue" is, or whether `/sys/class/gpio` is a real filesystem, or what the difference between `vmlinux` and `zImage` is. By Chapter 30, you will.

If that is roughly you, this book is written for you. If you have *no* embedded background at all — if "register" means "bank teller window" — the bare-metal chapters in Part II will feel cruel. There are gentler introductions; come back here after.

## 1.3  What "raw" means in this book

A few concrete commitments:

- The only black-box tool we permit ourselves for the first ~50 chapters is the **C compiler**, and we open even that one up in Chapter 60.
- We use **mainline** sources for U-Boot and Linux. Vendor BSPs are read in Part VII as a comparison study; they do not drive the main narrative.
- Every artifact — boot image, kernel image, device tree, root filesystem — is **built from a clean tree** by a script you can read. If you cannot regenerate the artifact, the chapter is not finished.
- We **never** copy-paste a configuration without explaining what each field does. The first time you see a DDR controller register, every bit of it is decoded. The second time you can look it up in the appendix.
- We **avoid Yocto, Buildroot, and other "framework" builders** until they have been thoroughly demystified by us having done the same work by hand.

This discipline is the entire point of the book. Skip it at your own risk.

## 1.4  What this book does not cover

- **Other SoCs.** We pick the i.MX6ULL because it is a single-core Cortex-A7 part — simple enough that we can hold the whole boot path in our head — with excellent NXP documentation, an active mainline upstreaming history, and abundant cheap dev boards. The principles transfer to STM32MP1, AllWinner H3, Rockchip RK3308 and similar SoCs, but the register tables do not.
- **Real-time Linux.** PREEMPT_RT is mentioned in Chapter 30 and Chapter 43 but is not the focus.
- **Android.** It is a wholly separate userspace stack on top of the same kernel — different init (`init.rc`), different libc (Bionic), different IPC (Binder), different build (Soong). The kernel chapters of this book apply directly; the userspace chapters do not. If your target is Android, follow this book through Chapter 35 and then branch to AOSP documentation.
- **Container runtimes, Docker on embedded, Kubernetes at the edge.** Out of scope.
- **Application programming on Linux.** You will use a shell and write a few C test programs, but we are not teaching POSIX threads or `select`/`epoll` as such.

## 1.4a  How this book differs from the Point Atom (正点原子) guide

The Point Atom *i.MX6U Embedded Linux Driver Development Guide* (V1.81, ~1888 pages, free at openedv.com) is the most popular Chinese-language reference for this hardware. It is excellent and pragmatic — your board likely came with it. We use it as a companion text for board specifics (schematic pin lookups, ALPHA-vs-MINI variance).

We aim higher than parity. Three categories of difference:

### (a) Surface-level differences

| | Point Atom | This book |
|---|---|---|
| U-Boot version | 2016.03 (NXP fork `imx_v2016.03_4.1.15`) | Current mainline |
| Linux kernel version | 4.1.15 (NXP fork) | Current mainline |
| Bare-metal register style | NXP SDK header `MCIMX6Y2.h` from Ch 12 onward | Hand-rolled `#define`s; SDK as a sidebar in Ch 18A |
| Image deployment | NXP MfgTool (Windows GUI) | `uuu` / `imx_usb_loader` (CLI, Linux-first) |
| Image builder | `imxdownload` + `mkimage` | Our own `mkimx.py` (Ch 11) |
| Pedagogy | "Here is the procedure" | What / Why / How / Focus / Lab / Pitfalls / Going deeper |

### (b) Topics PA has and we add depth to

| Topic | PA approach | Our approach |
|-------|-------------|--------------|
| Bare-metal MMU + caches | Briefly touched via CP15 | A full chapter (Ch 17) with measured ~10× speedup |
| Yocto | One appendix chapter (A2) | Comparison chapter (Ch 61) **plus** layer-development deep dive (Ch 61A) |
| Driver subsystems | Walks every common subsystem | Same coverage, plus DT bindings YAML validation (Ch 27A) and regmap pattern as core, not afterthought |

### (c) Chapters PA *structurally cannot teach*

These are the chapters that make this book worth the extra time. PA pins itself to a 2017-era vendor BSP; its readers never confront the questions these chapters answer:

| Topic | Chapter |
|-------|---------|
| Kernel lifecycle: mainline / LTS / vendor BSP decision framework | 30A |
| Multi-variant FIT image + DT overlays for product variants | 23A |
| Read-only rootfs + overlayfs (the industrial-product pattern) | 35B |
| Container runtimes on embedded (Podman + OCI) | 35C |
| Watchdog driver and brown-out resilience | 51A |
| Power management: runtime PM, DVFS, suspend/resume | 51B |
| PREEMPT_RT real-time as a full chapter | 52A |
| MTD/UBI/UBIFS for raw NAND | 54A |
| V4L2 + GStreamer for camera input | 54B |
| Rust-for-Linux first module | 55I |
| HAB / secure boot end-to-end | 62 |
| OTA: RAUC, SWUpdate, Mender compared | 63 |
| Mainline patch submission workflow | 58A |
| BSP → mainline migration playbook | 60A |
| CI/CD for embedded Linux (board-farm-on-PR) | 59A |

### When to use PA anyway

The Point Atom guide is *faster* if your task is bounded by "make this peripheral work today on the vendor BSP." Use it as a quick reference for:

- Board schematic pin lookups (it has the ALPHA/MINI schematics drawn in-line, chapter by chapter)
- NXP BSP-specific quirks (their patches you may inherit on a customer site)
- Chinese-language community references on openedv.com forum

When your work needs to last more than three years, come back here.

> **The simplest framing.** PA teaches you to use the i.MX6ULL. This book teaches you to be the engineer that other people ask for help with the i.MX6ULL.

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
- Run every command yourself. **Do not** paste it from the companion repo without first reading what it does.
- When something does not work — and many things will not — debug it for at least an hour before looking up the answer. The book includes "expected output" blocks specifically so you can tell when you are stuck.
- Commit your code per chapter. The companion repo's `code/chXX/` layout is a hint; mirror it.

## 1.7  The companion repository

Source code for every chapter lives in `code/chXX-<short-name>/`. It is dual-licensed MIT OR Apache-2.0, with one exception: kernel module chapters that link against GPL'd kernel symbols inherit GPL-2.0-only as required.

The repository is structured so that a reader who has lost their way can `git checkout` the snapshot at the end of any chapter and resume. Treat it as a safety net, not the main path.

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

Bare-metal Part II (Chapters 9–18) is the only part the impatient reader can skip without losing the thread. But: *you should not skip it*. It is where this book differs from every other embedded-Linux book on the shelf, and it is the part that will save you, six months from now, when a bring-up problem traces all the way back to a misconfigured AHB clock.

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

Five items, ten minutes, every new peripheral. This habit, more than anything else, is what separates engineers who can bring up a custom board from engineers who can only operate on someone else's eval kit.

## 1.11  Where to ask for help

When the book leaves you stuck, the following are, in this author's experience, the best places to look:

- **The i.MX community forum** at NXP (free account). Real engineers from NXP read it, and many problems you will hit have already been answered.
- **The U-Boot mailing list** (`u-boot@lists.denx.de`). Read-only for a few weeks before posting.
- **The Linux kernel mailing lists** (`linux-arm-kernel`, the relevant subsystem list — `linux-i2c`, `linux-spi`, `linux-rtc`, etc.). Etiquette matters; read `Documentation/process/` before posting.
- **The Bootlin training material** (free, public). The best second source after this book.
- **LWN.net**. A subscription is among the best dollars per byte in technical journalism.

Stack Overflow is the worst place to ask about Linux internals. The kernel changes too fast and the upvoted answers go stale. Go to the source.

## 1.12  Acknowledgements (placeholder)

*(Add when the manuscript is closer to complete. Reserve a paragraph for the maintainers of mainline U-Boot and Linux who answered patient questions; for the Bootlin team; for the Point Atom project that put low-cost i.MX6ULL hardware in the hands of so many learners; and for the colleagues and reviewers who read drafts.)*

## 1.13  Errata and corrections

The companion repository's `ERRATA.md` is the canonical list. Pull requests welcome.

---

> **One last thing before you turn the page.** This is a slow book. It rewards patience and punishes shortcut-taking. If you find yourself wanting to skip from Chapter 7 to Chapter 19, close the book and come back later. It will still be here.

— *(Author)*
*(City), 2026*
