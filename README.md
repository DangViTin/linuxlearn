# Embedded Linux on i.MX6ULL

From First Boot to First Driver - The Raw Approach.

This repository contains the Markdown source for a first-principles embedded Linux book aimed at engineers who already know MCU, bare-metal, or RTOS development and want to understand Linux from the reset vector up.

Read at https://dangvitin.github.io/linuxlearn/
## Current Scope

The book covers bare-metal i.MX6ULL bring-up, U-Boot, mainline Linux, root filesystem construction, Linux driver development, a device cookbook, debugging, production flows, secure boot, field updates, CI/CD, and upstream patch submission.

## Target Reader

This book is written for firmware engineers who already understand concepts such as registers, interrupts, linker scripts, startup code, UART, GPIO, and board bring-up, but are new to the Linux boot stack, kernel/user split, Device Tree, root filesystems, and Linux driver APIs.

## Target Board

Primary target:

- Point Atom MINI / ALPHA i.MX6ULL board
- NXP i.MX6ULL Cortex-A7 at 696 MHz
- 512 MiB DDR3L
- UART console, SD/eMMC boot, USB-OTG recovery, optional JTAG

Most Part IV through Part VIII material transfers to other Linux-capable ARM SoCs. Parts II and III are intentionally i.MX6ULL-specific because they teach Boot ROM, DCD, DDR, IOMUX, clock, and U-Boot porting details.