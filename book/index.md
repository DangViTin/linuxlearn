---
title: Home
description: Embedded Linux on i.MX6ULL — From First Boot to First Driver
---

# Embedded Linux on i.MX6ULL

### *From First Boot to First Driver — The Raw Approach*

> An explanatory, mainline-first guide to bringing up embedded Linux on the i.MX6ULL.
> Built for the MCU engineer who wants to understand every byte, not just `bitbake build`.

```{toctree}
:hidden:
:caption: Front matter
:maxdepth: 1

Table of contents <toc>
```

```{toctree}
:hidden:
:caption: Part I — Foundations
:maxdepth: 2

part1-foundations/ch01-preface
part1-foundations/ch02-what-is-embedded-linux
part1-foundations/ch03-host-setup
part1-foundations/ch04-armv7a-for-mcu-engineer
part1-foundations/ch05-imx6ull-tour
part1-foundations/ch06-toolchain
part1-foundations/ch07-boot-rom-ivt-dcd
part1-foundations/ch08-board-bring-up
```

```{toctree}
:hidden:
:caption: Part II — Bare-metal i.MX6ULL
:maxdepth: 2

part2-baremetal/ch09-asm-led
part2-baremetal/ch10-c-startup-linker
part2-baremetal/ch11-ivt-dcd-image
part2-baremetal/ch12-uart-printf
part2-baremetal/ch13-ccm-clocks
part2-baremetal/ch14-ddr3-init
part2-baremetal/ch15-exceptions-gic
part2-baremetal/ch16-timers
part2-baremetal/ch17-mmu-caches
part2-baremetal/ch18-bare-metal-peripherals
part2-baremetal/ch18A-project-organization
part2-baremetal/ch18B-button-beep
part2-baremetal/ch18C-baremetal-rtc
```

```{toctree}
:hidden:
:caption: Part III — U-Boot, deeply
:maxdepth: 2

part3-uboot/ch19-uboot-from-source
part3-uboot/ch20-uboot-spl
part3-uboot/ch21-uboot-internals
part3-uboot/ch22-uboot-board-port
part3-uboot/ch23-bootcmd-bootargs-fit
part3-uboot/ch23A-multi-variant-fit
part3-uboot/ch24-workflows-tftp-nfs-usb
```

```{toctree}
:hidden:
:caption: Part IV — The Kernel
:maxdepth: 2

part4-kernel/ch25-building-mainline-linux
part4-kernel/ch26-booting-kernel-from-uboot
part4-kernel/ch27-device-tree
part4-kernel/ch27A-dt-bindings-yaml
part4-kernel/ch28-kernel-startup-traced
part4-kernel/ch29-initramfs-from-scratch
part4-kernel/ch30-kernel-configuration
part4-kernel/ch30A-kernel-lifecycle
```

```{toctree}
:hidden:
:caption: Part V — Root filesystem & user space
:maxdepth: 2

part5-rootfs/ch31-rootfs-by-hand
part5-rootfs/ch32-proc-sys-devtmpfs
part5-rootfs/ch33-init-systems
part5-rootfs/ch34-libc-dynamic-linking
part5-rootfs/ch35-buildroot
part5-rootfs/ch35A-ubuntu-base
part5-rootfs/ch35B-readonly-rootfs-overlayfs
part5-rootfs/ch35C-containers-on-embedded
```

```{toctree}
:hidden:
:caption: Part VI — Driver development (foundations)
:maxdepth: 2

part6-drivers/ch36-hello-lkm
part6-drivers/ch37-character-driver
part6-drivers/ch38-auto-device-nodes
part6-drivers/ch39-platform-driver-dt
part6-drivers/ch40-misc-framework
part6-drivers/ch41-concurrency
part6-drivers/ch42-sleeping-waiting-polling
part6-drivers/ch43-interrupts
```

```{toctree}
:hidden:
:caption: Part VI — Driver development (common subsystems)
:maxdepth: 2

part6-drivers/ch44-gpio-subsystem
part6-drivers/ch45-input-subsystem
part6-drivers/ch46-i2c-drivers
part6-drivers/ch47-spi-drivers
part6-drivers/ch48-pwm-rtc
part6-drivers/ch49-iio-subsystem
part6-drivers/ch50-regmap
```

```{toctree}
:hidden:
:caption: Part VI — Driver development (advanced + insertions)
:maxdepth: 2

part6-drivers/ch51-dma
part6-drivers/ch51A-watchdog
part6-drivers/ch51B-power-management
part6-drivers/ch52-network-fec
part6-drivers/ch52A-preempt-rt
part6-drivers/ch53-sound-alsa-asoc
part6-drivers/ch54-lcd-drm
part6-drivers/ch54A-mtd-ubi
part6-drivers/ch54B-v4l2-gstreamer
part6-drivers/ch55-usb-gadget
part6-drivers/ch55A-kernel-timers
part6-drivers/ch55B-async-sigio
part6-drivers/ch55C-can-flexcan
part6-drivers/ch55D-block-device
part6-drivers/ch55E-wifi
part6-drivers/ch55F-cellular
part6-drivers/ch55G-multi-touch
part6-drivers/ch55H-hdmi-bridge
part6-drivers/ch55I-rust-for-linux
```

```{toctree}
:hidden:
:caption: Part VII — Device cookbook (Storage)
:maxdepth: 2

part7-cookbook/ch64-qspi-flash
part7-cookbook/ch65-eeprom
part7-cookbook/ch66-sd-emmc
```

---

## What this is

A 1,700-page book in progress, aimed at engineers who already write firmware for microcontrollers and want to take the same first-principles approach to Linux. We build the entire stack by hand — bare-metal startup, U-Boot from source, mainline Linux, hand-built root filesystem, every driver subsystem — before adopting any framework that hides what just happened.

The target board is the **i.MX6ULL on the Point Atom MINI** (or ALPHA — both work; pin assignments are noted where they differ). Every chapter explains the *pattern* — pin lookups, register layouts, kernel APIs — that transfers to any i.MX6ULL board, and most patterns transfer to any Cortex-A Linux SoC.

## Approach

- **Mainline-first.** We use current mainline U-Boot and Linux throughout. The 5–10 hours saved up front by adopting a vendor fork is paid back many times over the life of a product as security fixes, new toolchains, and modern features (DT bindings YAML validation, FIT image overlays, PREEMPT_RT in mainline, Rust-for-Linux) become reachable.
- **Explanatory, not procedural.** Every chapter follows the same seven-section template: *What / Why / How / Focus / Lab / Pitfalls / Going deeper*. Reading a chapter, you should always know which paragraph answers which question.
- **Hand-built where it teaches.** Our own bare-metal stack (Part II), our own image-builder (Ch 11), our own cross-toolchain (Ch 60). Tools become productivity wins only after you can do without them.
- **Production-grade where it matters.** Watchdog, runtime PM, PREEMPT_RT real-time, secure boot, OTA, mainline patch-submission, CI/CD — these chapters appear because real products require them, not because the dev board does.

## Reading order

1. **Start with [Chapter 1 — Preface](part1-foundations/ch01-preface.md)** for the philosophy and the 7-section chapter template (*What / Why / How / Focus / Lab / Pitfalls / Going deeper*).
2. **Then [Chapter 2 — What "Embedded Linux" actually is](part1-foundations/ch02-what-is-embedded-linux.md)** for the vocabulary.
3. **Follow Part I and Part II in order** — they build on each other and the labs assume prior chapters.
4. **Part VI's driver chapters are mostly sibling-independent** — pick the subsystem you need; the rest can wait.

The full [Table of Contents](toc.md) gives the chapter list, dependency graph, and what each Part covers.

## Status

```{list-table}
:header-rows: 1
:widths: 40 30 30

* - Part
  - Chapters
  - Status
* - Part I — Foundations
  - 8
  - ✅ Drafted
* - Part II — Bare-metal i.MX6ULL
  - 10 + 3 supplementary (18A–C)
  - ✅ Drafted
* - Part III — U-Boot, deeply
  - 6 + 1 supplementary (23A)
  - ✅ Drafted
* - Part IV — The Kernel
  - 6 + 2 supplementary (27A, 30A)
  - ✅ Drafted
* - Part V — Root filesystem & user space
  - 5 + 3 supplementary (35A–C)
  - ✅ Drafted
* - Part VI — Driver development
  - 20 + 13 supplementary
  - ✅ Drafted (Ch 36–55I + all insertions)
* - Part VII — Device cookbook *(v1.3, new)*
  - 54 chapters (Ch 64–117)
  - ⬜ Not yet drafted
* - Part VIII — Debug, production, advanced
  - 9 + 5 supplementary
  - ⬜ Not yet drafted
* - **Total**
  - **118 numbered + 23 supplementary = 141**
  - **~38 % drafted**
```

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

- **Errata:** open an issue on the [GitHub repository](https://github.com/DangViTin/linuxlearn/issues).
- **Pull requests** for typos, broken links, and clarifications are welcome.
- **Substantive changes** — please open an issue first to discuss.

---

> *Continue to [Chapter 1 — Preface](part1-foundations/ch01-preface.md) →*
