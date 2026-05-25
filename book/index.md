---
title: Home
description: Embedded Linux on i.MX6ULL — From First Boot to First Driver
---

# Embedded Linux on i.MX6ULL

### *From First Boot to First Driver — The Raw Approach*

> An explanatory, mainline-first guide to bringing up embedded Linux on the i.MX6ULL.
> Built for the MCU engineer who wants to understand every byte, not just `bitbake build`.

---

## What this is

A 1,700-page book in progress (~21 of 87 chapters drafted as of May 2026), aimed at engineers who already write firmware for microcontrollers and want to take the same first-principles approach to Linux. We build the entire stack by hand — bare-metal startup, U-Boot from source, mainline Linux, hand-built root filesystem, every driver subsystem — before adopting any framework that hides what just happened.

The target board is the **Point Atom (正点原子) i.MX6ULL ALPHA / MINI**, but every chapter explains the *pattern* — pin lookups, register layouts, kernel APIs — that transfers to any i.MX6ULL board, and most patterns transfer to any Cortex-A Linux SoC.

## Why another i.MX6ULL book

The Point Atom guide already exists and is excellent at what it does (a procedural how-to on top of a 2017-era vendor BSP). We aim higher: mainline Linux and U-Boot throughout; pedagogy that names *what / why / how / focus / pitfalls* for every step; and the production-grade chapters (kernel-lifecycle, PREEMPT_RT, watchdog, OTA, secure boot, BSP-to-mainline migration, mainline patch-submission workflow) that PA structurally cannot teach because it commits to a frozen vendor fork. See [How this book differs from Point Atom](part1-foundations/ch01-preface.md#14a-how-this-book-differs-from-the-point-atom-正点原子-guide) in Chapter 1 for the detail.

## Reading order

1. **Start with [Chapter 1 — Preface](part1-foundations/ch01-preface.md)** for the philosophy and the 7-section chapter template (*What / Why / How / Focus / Lab / Pitfalls / Going deeper*).
2. **Then [Chapter 2 — What "Embedded Linux" actually is](part1-foundations/ch02-what-is-embedded-linux.md)** for the vocabulary.
3. **Follow Part I and Part II in order** — they build on each other and the labs assume prior chapters.
4. **Part VI's driver chapters are mostly sibling-independent** — pick the subsystem you need; the rest can wait.

The full [Table of Contents](toc.md) gives the chapter list, dependency graph, and what each Part covers.

## Status

| Part | Chapters | Status |
|------|----------|--------|
| Part I — Foundations | 8 | ✅ Drafted |
| Part II — Bare-metal i.MX6ULL | 10 + 3 inserted (18A–C) | ✅ Drafted |
| Part III — U-Boot, deeply | 6 + 1 inserted (23A) | ⬜ Not yet drafted |
| Part IV — The Kernel | 6 + 2 inserted (27A, 30A) | ⬜ Not yet drafted |
| Part V — Root filesystem & user space | 5 + 3 inserted (35A–C) | ⬜ Not yet drafted |
| Part VI — Driver development | 20 + 13 inserted (51A, 51B, 52A, 54A, 54B, 55A–I) | ⬜ Not yet drafted |
| Part VII — Debug, production, advanced | 9 + 5 inserted (58A, 59A, 60A, 61A, 63A) | ⬜ Not yet drafted |
| **Total** | **64 numbered + 23 inserted = 87** | **~24 % drafted** |

## Hardware

- **Board:** Point Atom (正点原子) i.MX6ULL MINI (or ALPHA — both work; the boards differ in onboard peripherals)
- **SoC:** NXP i.MX6ULL, Cortex-A7 @ 696 MHz
- **DRAM:** 512 MiB DDR3L
- **Boot media:** SD card / eMMC
- **Debug:** UART1 over USB-serial (CP2102 / CH340), optional JTAG via FT2232H or J-Link

## Host

- **OS:** Native Linux (Ubuntu 22.04 LTS recommended)
- **Toolchain:** `arm-linux-gnueabihf-gcc` (current GCC) and `arm-none-eabi-gcc` for bare-metal
- **Tools:** TFTP server, NFS server, picocom, `uuu` / `imx_usb_loader` for USB-OTG flashing

## License

- **Book prose** (this site): CC-BY-SA-4.0 *(tentative — finalized before public release)*
- **Companion code** (in `code/` of the repository): MIT OR Apache-2.0, with GPL-2.0-only for kernel-module chapters where required

## Contributing & errata

This is a work in progress. If you spot an error or have suggestions:

- **Errata:** open an issue on the [GitHub repository](https://github.com/DangViTin/linuxlearn/issues) (will be live after first push).
- **Pull requests** for typos, broken links, and clarifications are welcome.
- **Substantive changes** — please open an issue first to discuss.

---

> *Continue to [Chapter 1 — Preface](part1-foundations/ch01-preface.md) →*
