# Embedded Linux on i.MX6ULL

From First Boot to First Driver - The Raw Approach.

This repository contains the Markdown source for an architecture-first embedded Linux book aimed at engineers who already know MCU, bare-metal, or RTOS development. It explains the responsibilities, interfaces and design tradeoffs from the reset vector to Linux applications and drivers.

Read at https://dangvitin.github.io/linuxlearn/ (opens Chapter 1 directly). In the source tree, start with [Chapter 1](book/part1-foundations/ch01-preface.md).

[Download the whole book as one PDF](https://dangvitin.github.io/linuxlearn/downloads/embedded-linux-imx6ull.pdf). The website's Download PDF control retrieves the same file, rebuilt on every deployment with all chapters, sketches, bookmarks and a linked contents list.
## Current Scope

The book covers bare-metal i.MX6ULL startup, U-Boot, mainline Linux, root filesystems, driver architecture, a device cookbook, debugging, production flows, secure boot, field updates, CI/CD, upstream maintenance, and virtualization. Chapter-specific Key Notes replace hands-on labs. Code and commands remain explanatory examples, not assignments or proof of hardware qualification.

## Target Reader

This book is written for firmware engineers who already understand concepts such as registers, interrupts, linker scripts, startup code, UART, GPIO, and board bring-up, but are new to the Linux boot stack, kernel/user split, Device Tree, root filesystems, and Linux driver APIs.

## Target Board

Primary target:

- Point Atom MINI i.MX6ULL board, with ALPHA/vendor sources used only where the shared core and specific wiring are established
- NXP i.MX6ULL Cortex-A7; permitted clocks depend on the fitted chip's speed grade and board conditions
- 512 MiB DDR3L
- UART console, SD/eMMC boot, USB-OTG recovery, optional JTAG

Most Part IV through Part VIII material transfers to other Linux-capable ARM SoCs. Parts II and III are intentionally i.MX6ULL-specific because they teach Boot ROM, DCD, DDR, IOMUX, clock, and U-Boot porting details. Part IX is an applied virtualization path: QEMU first, Xen on i.MX6ULL where useful, Jailhouse in QEMU ARM64, and STM32MP1 Linux+RTOS for the more production-realistic A7/M4 split.
