# Embedded Linux on i.MX6ULL — From First Boot to First Driver
### The Raw Approach: Build It Yourself, Understand It Forever

**Target board:** Point Atom (正点原子) ALPHA / MINI — i.MX6ULL (Cortex-A7, 528–696 MHz, 512 MB DDR3)
**Target reader:** Embedded engineer fluent in MCU / bare-metal / RTOS, new to Linux
**Host environment:** Native Linux (Ubuntu 22.04 LTS or Debian stable)
**Philosophy:** No Yocto. No vendor BSP magic. No `defconfig && make` until you've already done it the long way. The only black box we allow ourselves is the C compiler — and even *that* we open up in Part VII.

---

## Scope

**8 Parts, 141 chapters (118 numbered + 23 supplementary, "letter-suffix" convention), ~2,470 pages.** The supplementary chapters expand specific topics where the numbered chapters' default depth is not enough for production work — they share a parent number (e.g., `18A` extends `Ch 18`) and can be read independently. The numbered chapters are the required path; the supplementary chapters are recommended.

v1.3 inserted **Part VII — Device Cookbook** (54 chapters, Ch 64–117), one chapter per device class with 2–4 real chips compared side-by-side. The old "Debug, production, advanced" Part VII became Part VIII (Ch 118–126 + insertions).

## What the book covers

- **Part I — Foundations.** Host setup, the ARMv7-A architecture as it differs from Cortex-M, the i.MX6ULL SoC, the GNU toolchain, the Boot ROM's `IVT` / `DCD` / `BootData` contract, and a hardware bring-up checklist.
- **Part II — Bare-metal i.MX6ULL.** Build the entire stack from the reset vector up: LED in pure assembly; a C runtime with hand-written startup and linker script; a Boot-ROM-acceptable image built by our own Python tool; UART + `printf`; CCM clocks; DDR3 + MMDC; exceptions and GIC; timers; MMU + caches; one chapter each of bare-metal I²C/SPI/LCD, button input, and bare-metal RTC.
- **Part III — U-Boot, deeply.** Build mainline U-Boot, recognize Part II inside its source, understand SPL, trace the boot flow line by line, port U-Boot to a custom board, master `bootcmd` / `bootargs` / FIT, build a multi-variant FIT image, set up the TFTP + NFS + USB-OTG development loop.
- **Part IV — The Kernel.** Build mainline Linux for i.MX6ULL, boot it from U-Boot, deep-dive on the Device Tree, trace `start_kernel()` to PID 1, build an initramfs from scratch, master `make menuconfig`, learn the kernel-lifecycle decision framework (mainline / LTS / vendor BSP), validate DT bindings against YAML schemas.
- **Part V — Root filesystem & user space.** A `busybox`-based hand-built rootfs; `/proc` `/sys` `devtmpfs`; init systems; libc and dynamic linking; Buildroot; Ubuntu-base as a fully-featured alternative; read-only root + overlayfs for industrial deployments; containers on embedded.
- **Part VI — Driver development.** ~33 chapters covering every common subsystem from char devices and platform drivers through I²C/SPI/PWM/RTC/IIO/regmap/DMA/Net/Sound/DRM/USB, with deeper treatment of CAN, multi-touch, block devices, WIFI, cellular modems, HDMI bridges, kernel timers, async notification, watchdog, power management, PREEMPT_RT real-time, MTD/UBI, V4L2/GStreamer, and a Rust-for-Linux sidebar. **One canonical example per subsystem** — depth on real chips lives in Part VII.
- **Part VII — Device cookbook** *(new in v1.3)*. 54 chapters, one per common device class, with 2–4 real chips compared side-by-side: schematic + DT example + driver code (or existing-driver enablement) + user-space access + lab + chip-specific pitfalls. Storage, environmental & motion sensors, ADCs/DACs, displays, cameras, audio codecs, WiFi/BT modules, LoRa/UWB/ZigBee/cellular, industrial buses (RS-485, LIN, CAN), RFID/NFC, fingerprint, smart LEDs (WS2812), motor drivers, external RTC. *This is the go-to reference Part.*
- **Part VIII — Debug, production, advanced.** JTAG/OpenOCD/GDB across layers; kernel debugging without JTAG (ftrace, eBPF, kgdb); user-space debugging; a capstone custom-board port; build your own toolchain with crosstool-NG; Yocto layer development; secure boot (HAB) and OP-TEE; field updates (RAUC, SWUpdate, Mender); the mainline patch-submission workflow; CI/CD for embedded; BSP → mainline migration playbook; VSCode + gdbserver remote debug.

## Revision history

- **v1.3 (2026-05-26)** — Added **Part VII — Device Cookbook** (54 new chapters, Ch 64–117): one chapter per device class with 2–4 real chips deeply compared. Covers storage (QSPI flash, EEPROM, SD/eMMC), environment / motion / position / power sensors, external ADCs+DACs+clock-gen, all display types (RGB-parallel / SPI / QSPI / OLED / e-paper / touch), cameras (parallel CSI + USB UVC), audio codecs and class-D amps, WiFi (SDIO/USB/hosted/combo), BLE (HCI/AT/mesh), LoRa/sub-GHz/ZigBee/UWB, cellular (USB 4G/UART/NB-IoT), identification (RFID/NFC, fingerprint), GPS/PPS, industrial buses (RS-485/LIN/CAN), motors & encoders, smart LEDs, dual-FEC + hosted Ethernet, PMICs, external RTC. Old Part VII (debug/production) renumbered to Part VIII (Ch 118–126). Total → 141 chapters, ~2,470 pages.
- **v1.2 (2026-05-25)** — Strengthened production-hardening coverage; added kernel-lifecycle, watchdog, power management, PREEMPT_RT, MTD/UBI, V4L2/GStreamer, Rust, mainline-submission workflow, CI/CD, BSP→mainline migration, Yocto layer development, multi-variant FIT, DT bindings YAML, container runtimes. Total → 87 chapters.
- **v1.1 (2026-05-25)** — Added project-organization chapter for bare-metal, button/beep, bare-metal RTC; Ubuntu-base rootfs; driver chapters for CAN, block device, WIFI, cellular, multi-touch, kernel timers, async I/O, HDMI bridge; VSCode remote-debug workflow.
- **v1.0 (2026-05-24)** — Initial TOC: 7 Parts, 64 chapters.

---

## How to read this book

Each chapter is structured the same way, so the reader always knows where to look:

1. **What** — the concrete artifact this chapter builds.
2. **Why** — what problem motivates this artifact; what the world looks like without it.
3. **How** — the mechanics, register-by-register or function-by-function.
4. **Focus** — the one or two ideas that, once internalized, unlock the next several chapters.
5. **Lab** — a hands-on deliverable. If you can't reproduce it from a clean shell, you have not finished the chapter.
6. **Pitfalls** — the specific traps real engineers fall into here.
7. **Going deeper** — pointers to the Linux source tree, NXP reference manual sections, and seminal papers.

---

# PART I — FOUNDATIONS

> *You are an MCU engineer. You know what a vector table is, what a linker script is, what `volatile` is for. This part exists to give you names for the things Linux adds on top.*

### Chapter 1 — Preface and how to use this book
- Who this book is for (the MCU/bare-metal engineer)
- What we mean by "raw" and why we refuse Yocto for ~50 chapters
- The lab discipline: every chapter has a deliverable; you don't skip
- How chapters depend on each other (dependency graph)
- Conventions: prompt symbols, register notation, file paths
- **Pages:** ~8

### Chapter 2 — What "Embedded Linux" actually is
- The four layers: Boot ROM → Bootloader → Kernel → User space
- Kernel space vs user space; the syscall boundary
- Process, thread, file descriptor — vocabulary first
- How this differs from your RTOS: virtual memory, demand paging, ELF loading
- Why Linux is "big" (and where its size actually lives)
- **Focus:** the *user/kernel split* is the single most important concept in the whole book
- **Pages:** ~14

### Chapter 3 — Host environment setup
- Choosing a host OS (Ubuntu 22.04 LTS); why native Linux beats WSL/VM for this work
- Required host packages: `build-essential`, `bison`, `flex`, `libssl-dev`, `bc`, `device-tree-compiler`, `u-boot-tools`, `nfs-kernel-server`, `tftpd-hpa`, `minicom`, `picocom`, `qemu-user-static`
- Installing the cross toolchain (`arm-linux-gnueabihf-gcc`) — pre-built for now, hand-built in Ch. 60
- Setting up TFTP, NFS, and a serial console on the host
- USB-OTG flashing tools: `imx_usb_loader`, NXP `uuu` (Universal Update Utility)
- A reproducible workspace layout for the rest of the book
- **Lab:** flash a stock image to SD with `dd`, boot, log in over UART — prove the pipeline
- **Pages:** ~16

### Chapter 4 — ARMv7-A and the Cortex-A7, for the MCU engineer
- ARMv7-A vs ARMv7-M: what Cortex-A adds (MMU, privilege levels, generic timer, NEON, multicore option)
- Exception model: USR / SYS / SVC / IRQ / FIQ / ABT / UND (and how this maps to Linux's user/kernel split)
- Banked registers, the program status register, mode switching
- The generic timer and how it differs from SysTick
- Cache hierarchy: L1 I/D, L2 (none on iMX6ULL), inner/outer shareable, MOESI
- MMU concepts: virtual address, page table walk, TLB, ASIDs, domains
- NEON / VFP overview
- **Focus:** MMU + privilege levels. Linux *cannot exist* without them.
- **Pages:** ~22

### Chapter 5 — A tour of the i.MX6ULL SoC
- Block diagram and what each block does
- Memory map: OCRAM, ROM, DDR aperture, peripheral regions
- Clock tree at 30,000 ft: oscillators → PLLs → CCM → root clocks → peripheral gates
- Power domains and the PMU
- IOMUX: the universal-multiplexer pattern (and how `iomuxc.h` is generated)
- Boot fuses (eFuses) and BOOT_MODE pins
- The reference manual: how to navigate ~5000 pages without drowning
- **Pages:** ~18

### Chapter 6 — The toolchain
- `gcc` is *not* one tool: cpp, cc1, as, collect2, ld
- `binutils`: `as`, `ld`, `objcopy`, `objdump`, `nm`, `readelf`, `strip`, `ar`, `addr2line`
- The C library: glibc vs musl vs uClibc-ng vs newlib (and why bare-metal needs none of them)
- ABI: EABI vs hard-float vs soft-float; `arm-linux-gnueabihf` decoded
- ELF format: program headers vs section headers; what the loader actually reads
- Linker scripts: `MEMORY`, `SECTIONS`, `VMA` vs `LMA`, `ENTRY`, `KEEP`
- Make basics that matter: implicit rules, pattern rules, automatic variables, `.PHONY`, recursive vs non-recursive
- **Lab:** compile a "hello world" for the host *and* for the target, compare `readelf -a` output
- **Pages:** ~24

### Chapter 7 — The Boot ROM, IVT, DCD, and BootData
- What the Boot ROM does on power-on (in order, with addresses)
- Reading `BOOT_MODE[1:0]` and `BOOT_CFG` pins
- Boot device options: SD/eMMC, NAND, SPI-NOR, USB-SDP, EIM-NOR
- The **IVT (Image Vector Table)**: layout, every field decoded
- The **DCD (Device Configuration Data)**: a tiny scripting language the ROM executes to bring up DDR and clocks *before your code runs*
- The **BootData** structure: load address and image length
- USB-SDP (Serial Download Protocol): how `uuu` and `imx_usb_loader` talk to a brand-new chip
- HAB (High Assurance Boot) introduction (deep-dived in Ch. 62)
- **Focus:** the DCD is the *most under-explained* feature of i.MX SoCs. Understand it and U-Boot SPL becomes obvious.
- **Pages:** ~22

### Chapter 8 — Hardware bring-up checklist
- Unboxing the Point Atom board: physical inspection, jumpers, SD slot, OTG cable
- Power rails to probe with a multimeter before applying power
- UART1 wiring (TXD/RXD/GND), correct voltage levels, 115200 8N1
- First-time SD card preparation (raw layout we will use throughout)
- Optional: JTAG header pinout, OpenOCD interface adapter (FT2232H, J-Link)
- The "I bricked it" recovery flow via USB-OTG SDP
- **Lab:** prove you can reflash a bricked board purely over USB-OTG. *You will need this skill.*
- **Pages:** ~12

---

# PART II — BARE-METAL i.MX6ULL

> *This is the chapter set MCU engineers love and most Linux books skip. You will write a complete bare-metal stack from reset vector to interrupt-driven UART, in **OCRAM and then DDR**, with **no help from U-Boot**. By the end you will have built, by hand, every primitive U-Boot relies on.*

### Chapter 9 — First LED, pure assembly
- Reset vector and where the Boot ROM jumps to
- Setting up the SVC-mode stack in OCRAM
- Enabling the GPIO clock via CCM_CCGR registers
- IOMUX configuration for the LED pin (Point Atom schematic pin)
- Direct GPIO data register write
- Infinite loop (no return, no exit)
- Building with `as`, linking with `ld`, image with `objcopy -O binary`
- **Lab:** LED blinks. Image is < 1 KB. You compiled it from `.S` files only.
- **Pages:** ~16

### Chapter 10 — C + startup.S + linker script
- Why pure C cannot run yet: who sets the stack pointer, who clears `.bss`, who copies `.data`?
- `startup.S`: stack init, `.bss` zero, `.data` copy from LMA to VMA, branch to `main`
- A complete linker script: `MEMORY` block, `SECTIONS`, `_etext` / `_sdata` / `_edata` / `_sbss` / `_ebss` symbols
- The `.init`, `.text`, `.rodata`, `.data`, `.bss` regions and why each exists
- `__attribute__((section(...)))` and when to reach for it
- Makefile that compiles `.S` and `.c` together, links, makes raw binary
- **Lab:** LED blink, now from `main()` in C. Inspect `readelf -S` and `objdump -h` to see your sections.
- **Pages:** ~20

### Chapter 11 — Hand-building a Boot ROM-acceptable image
- Recap of Ch. 7: what the Boot ROM expects to find at offset 0x400 of the boot media
- Writing a `.cfg` file for `mkimage -T imximage` — *but first*, do it manually so we know what the tool generates
- Walking the IVT byte-by-byte in a hex editor
- Writing a DCD script that initializes SDRAM controller for DDR3 (we'll use NXP's tested values for now; we derive them ourselves in Ch. 14)
- Padding and offsets for the SD card layout: where the IVT lives, where the image lives
- `dd if=image.imx of=/dev/sdX bs=1k seek=1`
- **Lab:** an image you built with no `mkimage`, byte by byte, boots and blinks the LED
- **Pitfall:** off-by-one in the IVT `self` pointer is the #1 reason boards "do nothing"
- **Pages:** ~22

### Chapter 12 — UART driver and `printf`
- UART1 register map: USR1, URXD, UTXD, UCR1–4, UFCR, UBIR, UBMR
- Computing the baud divisor from the module's input clock
- Polling-mode TX/RX
- Implementing a minimal `_putchar()` so we can hook up `printf`
- A 200-line `printf` clone (or use a tiny third-party one like `mpaland/printf`) — we explicitly avoid pulling in newlib
- **Lab:** debug-via-printf working over UART; replace LED blinks with status messages
- **Pages:** ~18

### Chapter 13 — CCM clock tree bring-up
- The clock tree, drawn end-to-end for i.MX6ULL: 24 MHz XTAL → ARM PLL / System PLL → root clocks → peripheral gates
- CCM, CCM_ANALOG, and PMU register groups
- Booting the ARM core at 696 MHz (vs the 396 MHz default)
- AHB and IPG bus clocks
- The CCGR gating registers: each peripheral has 2 bits, what they mean
- Side topic: how to compute power for a given clock configuration
- **Lab:** measure with an oscilloscope (or the on-chip GPT timer) that the core really is running at the rate you set
- **Pages:** ~22

### Chapter 14 — DDR3 initialization with MMDC
- DDR3 fundamentals refresher: banks, ranks, rows, columns, CL/tRCD/tRP/tRAS
- Reading your specific DDR3 chip's datasheet (Point Atom schematic → part number)
- The MMDC (Multi-Mode DDR Controller) register groups: MDCTL, MDPDC, MDOTC, MDCFG0/1/2, MDMISC, MAARCR, MAPSR, MPPDCMPR1/2, MPWLDECTRL0/1, MPDGCTRL0/1, MPRDDLCTL, MPWRDLCTL, MPMUR0…
- The DDR3 initialization sequence per JEDEC: precharge all → MR2 → MR3 → MR1 → MR0 → ZQCAL
- Calibration: write leveling, DQS gating, read/write delay calibration
- Using NXP's DDR Stress Tool to verify your settings before trusting them
- Translating verified register values into a DCD script
- **Lab:** code in OCRAM jumps to DRAM (`memcpy` itself to 0x80000000, runs from there)
- **Focus:** this is the chapter that distinguishes you from someone who only ever used eval boards
- **Pages:** ~30

### Chapter 15 — Exceptions and the GIC
- The ARMv7-A exception vector table (8 entries) — write it by hand
- High vs low vectors (`VBAR` register)
- The GIC v2 (Generic Interrupt Controller): Distributor + CPU Interface, register maps
- Configuring an SPI (Shared Peripheral Interrupt) and an SGI (Software-Generated Interrupt)
- Top-half ISR pattern in bare-metal: save context, ack the GIC, call C handler, return from exception
- **Lab:** UART RX interrupt driven; echo back over UART
- **Pages:** ~26

### Chapter 16 — Timers (EPIT and GPT)
- EPIT (Enhanced Periodic Interrupt Timer): a 1 ms tick
- GPT (General Purpose Timer): free-running counter for delay/timestamp
- Building `udelay()` and `mdelay()` primitives
- Using GPT as a profiling tool: cycle-count any function
- **Pages:** ~14

### Chapter 17 — MMU and caches
- Why we want the MMU on, even in "bare-metal": cache control
- Translation regimes: TTBR0/TTBR1, 32-bit short-descriptor format
- Building a first-level page table that maps SoC peripherals as Device memory and DRAM as Normal Cacheable
- Domains and access permissions
- Enabling the I-cache and D-cache (`SCTLR` bits)
- Cache maintenance: invalidate, clean, clean+invalidate by VA, set/way
- Measuring the performance difference with the GPT
- **Focus:** you now possess *every* primitive Linux needs from firmware. Carry this fact through Part III.
- **Pages:** ~26

### Chapter 18 — Optional bare-metal peripherals
- I²C (I2C1) to an EEPROM on the board
- SPI to an external flash
- LCD via eLCDIF — bring up the framebuffer manually, draw a pattern
- Why we stop here and move to U-Boot
- **Pages:** ~22

### Chapter 18A — Inserted (v1.1): Project organization the "STM32-style"
Once a bare-metal program crosses ~500 lines, the single-file layout we used through Ch 14 stops scaling. This chapter refactors our work-so-far into proper header/source separation, register-definition macros in a single `imx6ull.h`, BSP folder layout (`bsp/clk/`, `bsp/gpio/`, `bsp/uart/`, ...), and a top-level `Makefile` that builds the BSP and links it against `main.c`. Also discusses the NXP SDK's `MCIMX6Y2.h` struct-based register approach as an alternative — when to adopt it, when to stay hand-rolled.
- **Focus:** the moment you have ≥2 peripherals, organization saves more time than it costs
- **Lab:** refactor Chapters 9–17 into a `bsp/` tree; rebuild and confirm bit-identical binaries
- **Pages:** ~14

### Chapter 18B — Inserted (v1.1): Button input and beep (passive buzzer)
A polled GPIO input driver with hardware debounce (Schmitt trigger on KEY0), then a software debounce as a fallback exercise. Then a passive-buzzer "beep" driver, which is morally a GPIO output but with a duty-cycle question — the natural lead-in to Chapter 48 (Linux PWM) much later.
- **Lab:** button-pressed-while-held lights an LED; double-tap triggers a 200 ms beep
- **Pages:** ~12

### Chapter 18C — Inserted (v1.1): Bare-metal RTC (SNVS)
The SNVS (Secure Non-Volatile Storage) is the only always-on domain on the chip; its 32-bit second counter survives main-power-off. We initialize it, set the time, sleep the rest of the SoC, wake it, read it back. Then a small sidebar on how this maps to Linux's `struct rtc_class_ops` in Chapter 48.
- **Lab:** print the wall clock every second across a deliberate brown-out
- **Pages:** ~10

---

# PART III — U-BOOT, DEEPLY

> *We now switch to using U-Boot — but only after re-implementing, by hand, everything it does. You will read U-Boot's source and recognize every step.*

### Chapter 19 — U-Boot from source, first boot
- Cloning mainline U-Boot (`git.denx.de`)
- The directory layout: `arch/`, `board/`, `cmd/`, `common/`, `drivers/`, `lib/`, `include/configs/`
- `make mx6ull_14x14_evk_defconfig && make` — what each step produces
- Output artifacts: `u-boot.bin`, `u-boot.imx`, `SPL`, `u-boot-dtb.imx`, `MLO`
- Burning to SD, booting, getting the `=>` prompt
- First commands: `printenv`, `bdinfo`, `md`, `mw`, `mtest`, `mmc info`
- **Lab:** boot U-Boot, dump the DDR pattern with `md`, compare to your bare-metal expectations
- **Pages:** ~16

### Chapter 20 — U-Boot SPL: the missing link
- Why SPL exists at all: OCRAM is 128 KB; full U-Boot is bigger; DDR isn't up yet
- SPL is *your Chapter 14 productized*
- `arch/arm/mach-imx/spl.c`, `board/freescale/mx6ull_14x14_evk/MX6ULL_*.cfg`
- Reading the SPL DDR setup and mapping it to MMDC registers you already know
- The IVT/DCD-vs-SPL choice: when does U-Boot use DCD, when does it use SPL?
- **Focus:** by mapping SPL onto Ch. 14, you remove the last bit of magic
- **Pages:** ~18

### Chapter 21 — U-Boot internals
- The boot flow: `_start` → `reset` → `lowlevel_init` → `_main` → `board_init_f` → relocation → `board_init_r` → `main_loop`
- The two `board_init` halves and *why* there are two
- **Relocation**: copying U-Boot from its load address to high DRAM, fixing up GOT
- The U-Boot environment: where it lives (mmc / SPI flash / NAND), how `saveenv` works
- The command system: `U_BOOT_CMD()`, how `printenv` finds commands at link time
- The driver model (DM): `UCLASS_*`, `udevice`, `driver`, parse-time vs runtime
- **Lab:** add a custom command `hello` that runs from the U-Boot prompt
- **Pages:** ~26

### Chapter 22 — Porting U-Boot to a custom board
- Forking `mx6ull_14x14_evk` into your own `board/<yours>/`
- New defconfig, new device tree (`arch/arm/dts/imx6ull-yours.dts`)
- Changing pinmux for your LEDs, buttons, MAC PHY
- Re-running DDR Stress Tool with your DRAM and updating the SPL DDR config
- Boot and verify
- **Lab:** even if you use the Point Atom board, *pretend* it's a custom one — change the model string, hostname, default bootcmd
- **Pages:** ~22

### Chapter 23 — `bootcmd`, `bootargs`, FIT images
- `bootm`, `bootz`, `booti` — what each expects
- The kernel cmdline syntax: `console=`, `root=`, `rootfstype=`, `rw`, `ip=`, `nfsroot=`, `init=`
- FIT (Flattened Image Tree): kernel + DTB + initramfs in one signed bundle
- `mkimage -f kernel.its kernel.itb`
- Why FIT replaces uImage for modern systems
- **Lab:** boot kernel with three different `bootargs` (NFS root, ramdisk root, SD root) without recompiling anything
- **Pages:** ~18

### Chapter 23A — Inserted (v1.2): Multi-variant FIT images and DT overlays at runtime
In modern shipping products one binary often serves several board variants (different displays, different I/O headers, different sensors). The mainline pattern is one FIT image carrying multiple DTBs, plus optional DT overlays applied at boot time based on a strap pin or an EEPROM-read variant ID.
- Building a FIT with `images { kernel { ... } fdt-1 { ... } fdt-2 { ... } } configurations { conf-rev-a { ... } conf-rev-b { ... } }`
- U-Boot `bootm` selecting `#conf-rev-a` from the cmdline
- DT overlays applied by U-Boot `fdt apply`
- Reading a variant ID from EEPROM at boot (the `i2c md` → `setenv variant` → `bootm` chain)
- **Lab:** one image boots correctly on three different "virtual variants" (LCD enabled, LCD disabled, alt-I²C address) selected by a U-Boot env var
- **Pages:** ~14

### Chapter 24 — Workflows: TFTP, NFS, USB-OTG
- Iterating fast: don't reflash, network-boot
- Setting up `tftpd-hpa` on the host
- Setting up `nfs-kernel-server` and exporting the rootfs
- A canonical "edit, build, `make` install to NFS, reboot board" loop
- Recovery flow: USB-OTG SDP if SD/eMMC is corrupted
- **Pages:** ~14

---

# PART IV — THE KERNEL

> *The kernel is large but knowable. We boot mainline first; vendor BSPs come later, as a comparison exercise.*

### Chapter 25 — Building mainline Linux for i.MX6ULL
- `git clone git.kernel.org/.../linux.git`
- `make ARCH=arm imx_v7_defconfig`
- The build artifacts: `vmlinux`, `Image`, `zImage`, `arch/arm/boot/dts/*.dtb`
- `vmlinux` vs `zImage`: who decompresses, when, where
- Modules: `make modules && make modules_install INSTALL_MOD_PATH=...`
- **Lab:** produce a `zImage` and `imx6ull-14x14-evk.dtb` that match the U-Boot you built
- **Pages:** ~16

### Chapter 26 — Booting the kernel from U-Boot
- Loading via TFTP into RAM: `tftp 0x80800000 zImage; tftp 0x83000000 imx6ull.dtb`
- `bootz 0x80800000 - 0x83000000`
- The first 30 lines of kernel boot log — every line decoded
- "Uncompressing Linux... done, booting the kernel." — *where* in the kernel source this happens (`arch/arm/boot/compressed/head.S`)
- **Pages:** ~14

### Chapter 27 — Device Tree: the contract between firmware and kernel
- What problem DT solves (no more board-files, no more #ifdefs)
- DTS syntax: nodes, properties, phandles, labels, references
- `.dtsi` vs `.dts`, includes, overlays
- `compatible` strings — the single field that determines which driver binds
- `reg`, `interrupts`, `clocks`, `pinctrl-0`, `status` — the universal properties
- Walking `imx6ull.dtsi` → `imx6ull-14x14-evk.dts` end-to-end
- `dtc` and the `dtbs_check` flow against YAML bindings
- Writing your first overlay to add a new I²C device
- **Focus:** for an MCU engineer this is the largest mental shift. Spend extra time here.
- **Pages:** ~30

### Chapter 27A — Inserted (v1.2): DT bindings YAML + `dt_binding_check`
A 2018+ mainline-hygiene requirement. Since kernel v4.18 every new device-tree binding must ship a YAML schema and pass `make dt_binding_check`. Without it, your patch will not be accepted upstream. Without it, your binding can drift silently between board variants and you will not know.
- Why JSON-Schema for DT bindings (vs the old `.txt` files)
- A binding for a custom node, written from scratch, validated
- `make dt_binding_check` and `make dtbs_check` — what each does
- Common errors and how to read them
- **Lab:** write a binding for the Chapter 39 LED driver; pass `dt_binding_check`; deliberately break a property and watch the error fire
- **Pages:** ~14

### Chapter 28 — Kernel startup, traced
- `start_kernel()` — read it function-by-function
- `setup_arch()`, `setup_machine_fdt()`, memblock, paging_init, mm_init
- `rest_init()` → `kernel_init` thread → `run_init_process("/sbin/init")`
- `kthreadd`, the idle thread, init's pid 1
- Where `printk` ring buffer lives; how early-boot printk works before serial drivers exist
- **Pages:** ~24

### Chapter 29 — Initramfs from scratch
- What an initramfs *is* (cpio archive, not a filesystem image)
- Building a one-binary initramfs: a single statically-linked program that prints "hello" and `reboot()`s
- Then a BusyBox initramfs with a real shell
- Embedding the initramfs in the kernel image vs loading it separately
- The handoff: kernel mounts initramfs as `/`, runs `/init`
- **Lab:** boot to a shell with literally one file (`/init`) in the rootfs. Nothing simpler exists.
- **Pages:** ~16

### Chapter 30 — Kernel configuration deep-dive
- `make menuconfig` — but reading the `.config`, not clicking blindly
- The big knobs: `CONFIG_PREEMPT*`, `CONFIG_HZ`, `CONFIG_TICK_ONESHOT`, `CONFIG_NO_HZ`, `CONFIG_HIGH_RES_TIMERS`
- Tracing, debug, lockdep options
- Module vs built-in: when does it matter?
- Generating your own custom `defconfig` and saving it under `arch/arm/configs/`
- **Pages:** ~18

### Chapter 30A — Inserted (v1.2): Kernel lifecycle — mainline, stable, LTS, vendor BSPs
The decision framework most readers never see laid out explicitly. Six release tracks, each with different stability/feature/security guarantees:
- **Mainline** (Linus's tree, ~weekly rc, 9-week cycle)
- **Stable** (Greg KH's tree, fixes only, ~1 month lifetime per minor)
- **Long-Term Support (LTS)** (selected mainline releases get fixes for 2 or 6 years)
- **Vendor BSP** (NXP, ST, TI; usually a frozen mainline + thousands of patches)
- **Yocto/Buildroot-curated** (a vendor BSP plus a layer or two of patches, retargeted)
- **Distribution kernels** (Debian, Ubuntu, Fedora; not for embedded targets in general)
- When each is right: dev, shipping a product, shipping into critical/long-life environments
- The **migration cost** of a vendor BSP — pinned forever to that minor version's API
- How to read a kernel release announcement and decide what it means for you
- **Why old kernel forks are a trap**: a 2017-era kernel has missed eight years of security fixes
- **Lab:** decide-and-defend exercise — given three product scenarios (consumer toy, factory PLC, medical device), pick a kernel track for each and write the argument
- **Pages:** ~16

---

# PART V — ROOT FILESYSTEM & USER SPACE

### Chapter 31 — A root filesystem, by hand
- The FHS (Filesystem Hierarchy Standard) cheat sheet
- Building BusyBox from source, statically linked
- Creating `/bin`, `/sbin`, `/etc`, `/dev`, `/proc`, `/sys`, `/tmp`, `/var`, `/root`, `/lib`
- A minimal `/etc/inittab`, `/etc/init.d/rcS`, `/etc/fstab`, `/etc/passwd`, `/etc/group`, `/etc/profile`
- Exporting via NFS, mounting from kernel cmdline `root=/dev/nfs`
- **Lab:** boot, get a shell, run `ls /`, `ps`, `mount`
- **Pages:** ~22

### Chapter 32 — /proc, /sys, devtmpfs
- `/proc` — the original process FS, now also a kernel-info FS
- Useful files: `/proc/cpuinfo`, `/proc/meminfo`, `/proc/interrupts`, `/proc/iomem`, `/proc/devices`, `/proc/<pid>/maps`, `/proc/<pid>/status`
- `/sys` — the modern device model surface
- `/sys/class/gpio/`, `/sys/bus/i2c/devices/`, `/sys/devices/platform/`
- `devtmpfs` vs static `/dev` vs `mdev` vs `udev`
- **Pages:** ~18

### Chapter 33 — Init systems
- BusyBox `init`: minimal, inittab-based
- `sysvinit` / OpenRC: the classical world
- `systemd`: services, sockets, targets, journals — a brief sober tour
- Why an embedded target may not want any of these
- **Pages:** ~14

### Chapter 34 — libc, dynamic linking, and the loader
- glibc vs musl vs uClibc-ng (size, license, compatibility)
- ELF dynamic linking: PLT, GOT, `LD_LIBRARY_PATH`, `RPATH`
- `ldd`, `readelf -d`, `LD_DEBUG=files`
- `/lib/ld-linux-armhf.so.3` — what it actually does
- Static linking, when to use it on embedded
- **Lab:** rebuild BusyBox dynamically against musl, compare image sizes
- **Pages:** ~18

### Chapter 35 — Buildroot, *after* you can do it by hand
- Why Buildroot exists; what it really automates
- `make menuconfig` for Buildroot
- Reading `output/build/` and `output/target/` — recognizing every step you already did in Ch. 31
- Adding a custom package
- Comparing the generated rootfs against your hand-built one
- **Pages:** ~20

### Chapter 35B — Inserted (v1.2): Read-only rootfs + overlayfs (the industrial pattern)
Every shipping industrial product does this. A read-only rootfs means: power-cycle anywhere, corrupt nothing. The overlayfs trick lets `/var/log/`, `/etc/`, and other writable subtrees live in tmpfs (lost on reboot, by design) or on a separate persistent partition.
- Mounting `ext4` with `ro`; what fails (`/etc/resolv.conf`, `/var/run/utmp`, `/tmp`)
- `overlayfs` mount syntax: `lowerdir`, `upperdir`, `workdir`
- `/etc/fstab` for an RO root + writable overlays
- The data-partition split: `/data/` for app data, `/var/log/` for logs
- Power-cycle test: 100 reboots, mid-write, no corruption
- **Lab:** convert a Buildroot rootfs to RO-with-overlays; survive 100 randomly-timed power yanks
- **Pages:** ~16

### Chapter 35C — Inserted (v1.2): Container runtimes on embedded (Podman + OCI)
Increasingly, shipping products use containers to isolate the application from the base system — so the same vendor BSP can host many app updates without rebuilding the rootfs. We bring up rootless Podman on the i.MX6ULL, run a tiny Alpine container, talk to a host GPIO from inside it.
- Why containers on embedded: app/OS split for OTA, sandboxing, reproducibility
- Podman vs Docker on small devices (footprint, rootless)
- Kernel namespaces (`CONFIG_USER_NS`, etc.) and what your kernel needs
- Bind-mounting `/sys/class/gpio` into a container to talk to hardware
- OCI image format; how to build one without docker on the host
- **Lab:** boot an Alpine container on the board; from inside, blink a host LED via sysfs
- **Pages:** ~16

### Chapter 35A — Inserted (v1.1): Ubuntu-base rootfs as a peer to BusyBox/Buildroot
For projects where binary size is not the constraint but **familiarity is** (engineers used to `apt-get install` on their dev machines), an Ubuntu-base rootfs gives you a fully-fledged Debian-family userland on the target — `apt`, `bash`, full `coreutils`, glibc. We unpack `ubuntu-base-22.04-arm.tar.gz`, `chroot` into it under `qemu-user-static` to install packages on the host, then NFS-mount it from the target.
- When to choose this vs BusyBox (size, cold-start) or Buildroot (reproducibility)
- The `chroot` + `qemu-user-static` trick for installing target packages from the host
- DHCP and `apt` on the target
- **Lab:** boot a target with a 600 MB Ubuntu-base rootfs and `apt install htop` from the board itself
- **Pages:** ~16

---

# PART VI — DRIVER DEVELOPMENT

> *This is the longest and most lab-heavy Part. Each driver chapter has the same six-section shape: hardware, DT binding, driver code, user-space test, "what if I remove line X" experiment, pitfalls.*

### Chapter 36 — Your first kernel module
- The Loadable Kernel Module (LKM) build system: `obj-m`, Kbuild, `KDIR`
- `module_init`, `module_exit`, `MODULE_LICENSE`, `MODULE_AUTHOR`
- `printk` log levels, dmesg
- `insmod`, `rmmod`, `lsmod`, `modinfo`, `depmod`, `modprobe`
- Cross-compiling against the kernel tree you built in Ch. 25
- **Lab:** load a module that prints "hello from $current->comm"
- **Pages:** ~16

### Chapter 37 — Character device drivers
- The classical chardev pattern
- `register_chrdev_region` / `alloc_chrdev_region`
- `struct cdev` and `cdev_add`
- `struct file_operations`: `open`, `release`, `read`, `write`, `llseek`, `unlocked_ioctl`
- `copy_to_user` / `copy_from_user` — and *why* you can't just memcpy
- A 200-line driver exposing a software FIFO over `/dev/myfifo`
- **Pages:** ~22

### Chapter 38 — Auto device nodes (class + device)
- `class_create`, `device_create` and what udev/mdev do with `/sys/class/.../uevent`
- The uevent protocol, hotplug
- **Pages:** ~12

### Chapter 39 — The platform driver + device tree binding
- Why platform drivers replace the old "register a chardev manually" pattern
- `struct platform_driver`, `of_match_table`, `probe`, `remove`
- The bind dance: DT node + driver `compatible` → `probe()` called
- `platform_get_resource`, `devm_ioremap`, `devm_request_irq`
- Adding your driver's DT binding under `Documentation/devicetree/bindings/`
- **Lab:** an LED platform driver bound from DT; toggling via `/sys` attribute
- **Focus:** once this clicks, every kernel subsystem looks the same
- **Pages:** ~26

### Chapter 40 — The misc framework (shortcut chardev)
- When `miscdevice` is enough
- A `/dev/hwrng`-style driver in 80 lines
- **Pages:** ~10

### Chapter 41 — Concurrency
- The four "lock" families: atomic_t, spinlock, mutex, rwlock + sequence locks
- When to use each (interrupt context vs process context)
- Per-CPU variables
- RCU at an introductory level
- Preemption rules: `preempt_disable`, `local_irq_save`
- Lockdep and how to read its splats
- **Pages:** ~24

### Chapter 42 — Sleeping, waiting, polling
- `wait_queue_head_t`, `wait_event_interruptible`, `wake_up`
- Implementing blocking `read()`
- `poll_wait`, `EPOLL` from the driver side
- `O_NONBLOCK` semantics
- **Pages:** ~18

### Chapter 43 — Interrupts (top half, bottom half, threaded)
- `request_irq`, `IRQF_*` flags, shared interrupts
- Top half: keep it short, ack the device, schedule deferred work
- Bottom halves: softirq, tasklet (deprecated), workqueue, threaded IRQ
- DT `interrupts` property and the `interrupt-parent` chain
- **Lab:** GPIO button → IRQ → workqueue → input event
- **Pages:** ~24

### Chapter 44 — The GPIO subsystem
- The old `gpio_request`/`gpio_set_value` interface vs the new `gpiod_*` interface
- pinctrl bindings revisited
- Userspace: `/sys/class/gpio` (deprecated) vs `gpiochipN` + `libgpiod`
- **Pages:** ~16

### Chapter 45 — Input subsystem (button driver)
- `input_dev`, `input_event`, `EV_KEY`, `EV_ABS`, `input_register_device`
- `/dev/input/eventN` and `evtest`
- **Pages:** ~14

### Chapter 46 — I²C drivers
- Master controller (i.MX6ULL has 4 × I²C) vs client driver split
- The i.MX I²C controller (I2C1..4) register-level overview
- Writing a *client* driver for an EEPROM or sensor (e.g., AP3216 ambient light on the Point Atom board)
- DT binding for I²C devices
- Using `i2c-tools` (`i2cdetect`, `i2cdump`, `i2cset`, `i2cget`) to validate
- **Pages:** ~22

### Chapter 47 — SPI drivers
- SPI subsystem, master + slave
- ECSPI controller on i.MX6ULL
- Writing a driver for an SPI flash or ADC
- `spidev` for quick userspace prototyping
- **Pages:** ~20

### Chapter 48 — PWM and RTC
- PWM framework, `pwm_chip`, sysfs `/sys/class/pwm/`
- RTC framework: `rtc_class_ops`, `hwclock`, NTP integration
- **Pages:** ~16

### Chapter 49 — IIO (Industrial I/O) for ADC and sensors
- Why IIO replaced ad-hoc sensor drivers
- Channels, triggers, buffers
- A driver for the on-chip ADC1 of the i.MX6ULL
- Reading from `/sys/bus/iio/devices/iio:device0/in_voltage0_raw`
- **Pages:** ~22

### Chapter 50 — regmap
- The pattern: every device driver was duplicating "read/modify/write a register" code
- `regmap_init_mmio`, `regmap_init_i2c`, `regmap_init_spi`
- `regmap_update_bits`, cache types, debugfs integration
- Refactor an earlier chapter's driver to use regmap
- **Pages:** ~14

### Chapter 51 — DMA
- The DMA-API: `dma_alloc_coherent` vs streaming `dma_map_single`
- Cache coherency: why the kernel cares about direction and ownership
- i.MX6ULL SDMA controller overview
- A DMA-driven UART example (or audio DMA preview)
- **Pages:** ~22

### Chapter 51A — Inserted (v1.2): Watchdog driver and brown-out resilience
No product ships without one. The i.MX6ULL `WDOG1/WDOG2` modules generate a system reset if not "kicked" within a programmable window. We write the kernel driver, plumb the user-space daemon (`systemd-watchdog` or `busybox watchdog`), and design the application-level kick policy.
- The kernel `watchdog` framework, `struct watchdog_device`, `wdog_ops`
- `/dev/watchdog` and the `ioctl` interface
- Window timing: too-fast kicks are as bad as too-slow
- Boot-time vs runtime: when does the WDOG arm?
- Pre-timeout warnings for graceful shutdown
- **Lab:** application crashes → watchdog fires → board reboots into known-good state, with a counter in SNVS RAM recording the reset cause
- **Pages:** ~16

### Chapter 51B — Inserted (v1.2): Power management — runtime PM, suspend/resume, DVFS
Battery-powered or thermal-constrained products demand real PM. The Linux PM core supports four orthogonal mechanisms: runtime PM (per-device idle), system suspend (whole-board sleep), DVFS (frequency/voltage scaling), and CPU idle (low-power C-states).
- The PM-runtime callbacks: `runtime_suspend`, `runtime_resume`, `runtime_idle`
- `pm_runtime_get_sync` / `pm_runtime_put` discipline in drivers
- System sleep states: `freeze`, `standby`, `mem`, `disk` — what's implemented on i.MX6ULL
- DVFS: `cpufreq` governors (ondemand, schedutil, conservative)
- The CPU idle subsystem (`cpuidle`); WFI as the C1 state
- `tickless` (`CONFIG_NO_HZ_IDLE`) for power
- **Lab:** measure the board's current draw at 696 MHz active, 396 MHz active, idle, and suspend-to-RAM; quantify each mode's contribution
- **Pages:** ~22

### Chapter 52 — Network driver (FEC + KSZ8081 PHY)
- The netdev model: `struct net_device`, `ndo_*` ops, NAPI
- The FEC (Fast Ethernet Controller) on i.MX6ULL
- The PHY subsystem and MDIO
- DT bindings for ethernet
- Bringing the interface up, running `ping`, `iperf`, `tcpdump`
- **Pages:** ~26

### Chapter 52A — Inserted (v1.2): PREEMPT_RT — real-time Linux as a full chapter
For motion control, audio, robotics, industrial protocols, mainline Linux's PREEMPT_RT patchset turns the kernel into a deterministic real-time kernel without giving up the Linux API. Since v6.12 most of PREEMPT_RT has been merged into mainline; the rest is in flight.
- What "real-time" means precisely (worst-case latency, not "fast")
- The PREEMPT_RT design: threaded IRQs, sleeping spinlocks, rt_mutex with priority inheritance, ftrace-anchored measurement
- Building a PREEMPT_RT kernel on i.MX6ULL
- `cyclictest` — the standard latency benchmark
- Affinity, isolation (`isolcpus=`), and the `SCHED_FIFO`/`SCHED_DEADLINE` schedulers
- Tuning: disable CPU-idle deeper states, pin IRQs, lock memory with `mlockall`
- What still cannot meet hard-RT requirements on a Cortex-A7 single-core
- **Lab:** baseline Linux vs PREEMPT_RT side-by-side cyclictest run under network and disk load; show the worst-case latency change
- **Pages:** ~26

### Chapter 53 — Sound (ALSA / ASoC)
- The "Sound Open Architecture" stack
- ASoC: machine driver + codec driver + platform driver
- SAI controller on i.MX6ULL + WM8960 codec (typical Point Atom config)
- `aplay`, `arecord`, `alsamixer`
- **Pages:** ~24

### Chapter 54 — LCD framebuffer and DRM
- The eLCDIF controller
- Legacy fbdev (`/dev/fb0`) vs modern DRM/KMS (`/dev/dri/card0`)
- Writing pixels from user space; testing with `fbset`, `modetest`
- Touchscreen integration (GT9147 typical Point Atom)
- **Pages:** ~22

### Chapter 54A — Inserted (v1.2): MTD / UBI / UBIFS for raw NAND
If your product flashes raw NAND (not eMMC), you need the MTD subsystem under the kernel and UBI/UBIFS on top for wear-leveling and bad-block management.
- MTD model: `struct mtd_info`, `mtd_read/write/erase`
- The NAND subsystem (`nand_chip`) on top of MTD
- Bad-block management (BBT, OOB layout)
- UBI: volumes, wear-leveling, attach/detach
- UBIFS: a journaling FS on UBI
- `mtdinfo`, `ubinfo`, `ubiformat`, `ubinize`
- **Lab:** flash an entire layout (SPL → U-Boot → kernel → UBI rootfs) to NAND; power-cycle 1000 times; confirm zero bit errors after wear-leveling
- **Pages:** ~22

### Chapter 54B — Inserted (v1.2): V4L2 + GStreamer for camera input (CSI)
The i.MX6ULL CSI is paired with an OV5640 (typical) or OV2640 sensor. V4L2 (Video4Linux 2) is the kernel framework; GStreamer is the user-space pipeline glue.
- V4L2 model: `struct v4l2_device`, `struct video_device`, `v4l2_ioctl_ops`
- The i.MX6ULL `imx-pxp` and `imx-csi` drivers
- A user-space `v4l2-ctl` capture: `v4l2-ctl --stream-mmap --stream-to=...`
- GStreamer pipeline: `v4l2src ! videoconvert ! kmssink` → fullscreen camera
- The bayer/YUV/RGB conversion path
- Encoding to JPEG/H.264 on i.MX6ULL (none in HW; software encoder via `libjpeg`/`x264`)
- **Lab:** live camera preview onto the LCD via a one-line GStreamer pipeline; then capture 30 s to a file on the rootfs
- **Pages:** ~22

### Chapter 55 — USB gadget
- USB host vs device modes; OTG role detection
- `libcomposite` and ConfigFS-based gadgets
- A "USB serial" and a "USB mass storage" gadget walkthrough
- **Pages:** ~18

### Chapter 55A — Inserted (v1.1): Kernel timers and high-resolution timers (hrtimers)
Three timer APIs in the kernel: legacy `timer_list` (jiffies-based, ms resolution), `delayed_work` (workqueue-driven), and `hrtimer` (sub-µs, the modern default for new code). When to use which; how each is implemented under the hood; how the tick subsystem multiplexes many timers on one hardware event.
- `mod_timer`, `del_timer_sync`, the `timer_list.function` callback
- `hrtimer_init`, `hrtimer_start`, `HRTIMER_MODE_REL` vs `_ABS`, `_PINNED`
- `timer_setup` (the modern, type-safe API)
- **Lab:** an `hrtimer`-driven 1 kHz square wave on a GPIO, measured with a scope; compare jitter vs `mdelay` in a kthread
- **Pages:** ~18

### Chapter 55B — Inserted (v1.1): Asynchronous notification (SIGIO / fasync)
The fourth I/O model after blocking/non-blocking/poll: the driver delivers a `SIGIO` to a registered user-space process when data is ready, so the process is "informed" without ever calling `read()`. `fasync_helper`, `kill_fasync`, the `F_SETOWN`/`F_SETFL O_ASYNC` user-space dance.
- When SIGIO matters: legacy code, signal-driven simple loops, low-latency without busy-poll
- Why epoll/io_uring have mostly replaced it for new code, and why drivers still ship it
- **Lab:** the Chapter 45 button driver gains SIGIO; a user-space program receives signals on press
- **Pages:** ~12

### Chapter 55C — Inserted (v1.1): CAN bus and FlexCAN
Industrial automation runs on CAN. The i.MX6ULL has two **FlexCAN** controllers. The Linux SocketCAN subsystem treats CAN like a network interface: `ip link set can0 up type can bitrate 500000`. Then `cansend`, `candump`, `can-utils`.
- The FlexCAN controller register map and message-buffer model
- SocketCAN: `PF_CAN`, `SOCK_RAW`, `struct can_frame`
- `iproute2` CAN extensions; `can-utils`
- ISO-TP, CAN-FD — what i.MX6ULL supports and what it doesn't
- **Lab:** loopback two FlexCANs on the same board; then bridge to an external CAN node and exchange frames
- **Pages:** ~22

### Chapter 55D — Inserted (v1.1): Block device drivers
Char devices are sequential; block devices are random-access in fixed-size sectors. The block-I/O layer multiplexes requests from many filesystems onto one device with elevator/scheduling policies.
- `struct block_device`, `struct gendisk`, `struct block_device_operations`
- The `request_queue`, `make_request_fn`, modern `blk_mq` multi-queue
- A 4 MB RAM-disk block driver in < 200 lines
- How `/dev/mmcblk0` and `/dev/sda` look under the hood
- **Lab:** the RAM-disk works as `mkfs.ext4` target and is mountable
- **Pages:** ~24

### Chapter 55E — Inserted (v1.1): WIFI — wpa_supplicant, USB and SDIO dongles
Connecting an i.MX6ULL to Wi-Fi in 2026 is rarely an in-house driver job — you pick a chip with mainline support and stand up `wpa_supplicant`. We walk an RTL8188EUS USB Wi-Fi dongle (cfg80211) and an RTL8189FS SDIO module (vendor staging tree) end-to-end.
- Kernel: `CONFIG_CFG80211`, `CONFIG_WIRELESS_EXT`, `CONFIG_RTL8XXXU`
- Firmware blobs in `/lib/firmware/`
- `wpa_supplicant.conf`, WPA2-PSK, hidden SSIDs, EAP-PEAP
- `wpa_cli` and the `D-Bus` interface
- Diagnosing "no SSID found": antenna, country code, channel-12/13, regulatory domain
- **Lab:** the board joins your Wi-Fi from `/etc/init.d/`, gets a DHCP lease, pings the gateway
- **Pages:** ~24

### Chapter 55F — Inserted (v1.1): Cellular modems (PPP, ECM/NCM, GNSS)
Quectel EC20-style modems present themselves as USB composite devices: PPP serial, RNDIS/ECM data, NMEA GNSS. We cover all three modes, plus `quectel-CM` and `qmi_wwan` for the QMI-based path.
- USB option driver, vendor/product IDs, the `option_ids[]` table in `drivers/usb/serial/option.c`
- PPP path: `pppd` chat script, APN, MTU
- ECM/NCM: a virtual Ethernet over USB; `usb0`
- GNSS: `/dev/ttyUSB1` NMEA stream → `gpsd` → `gpsmon`
- **Lab:** boot, modem dials, board has internet via cellular; concurrent GPS fix logged
- **Pages:** ~22

### Chapter 55G — Inserted (v1.1): Multi-touch — MT-A, MT-B protocols, GT911
The Linux input subsystem evolved two multi-touch protocols: **Type A** (per-frame, packed) and **Type B** (per-slot, persistent). Most modern panels use Type B. We bring up a Goodix **GT911** capacitive touch controller (5-point), the typical pairing for the Point Atom MINI's optional LCD.
- I²C wiring + interrupt + reset of GT911
- `input_mt_init_slots`, `input_mt_slot`, `input_report_abs(ABS_MT_POSITION_X/Y)`
- `evtest` and how to read a multi-touch event stream
- `tslib` user-space library for legacy single-touch panels
- **Lab:** five fingers tracked simultaneously, printed by `evtest`
- **Pages:** ~18

### Chapter 55H — Inserted (v1.1): RGB-to-HDMI via sii902x
The i.MX6ULL has no native HDMI; a parallel-RGB-to-HDMI bridge chip (Silicon Image SiI902x) is the standard solution. The kernel has a mainline driver; the lab is wiring + DT bindings + EDID-based mode negotiation.
- The bridge chip's I²C control path vs. its parallel-RGB data path
- `drm/bridge` model in the kernel; `drm_bridge_add`
- EDID reading; mode selection from a list
- **Lab:** boot to a 1080p HDMI monitor with `weston` showing color bars
- **Pages:** ~16

### Chapter 55I — Inserted (v1.2): Rust-for-Linux — first kernel module
Since Linux 6.1, Rust is a supported language for kernel modules. As of 2026 the support is still gated to a small set of subsystems but is growing fast. We write our Chapter 36 hello-LKM in Rust, as a sidebar / supplemental experiment — not because we recommend Rust for production embedded yet, but because the reader will see it land in their next kernel update.
- Why Rust in the kernel (memory safety, type-state)
- `rust/` directory tour; how the build picks up Rust source
- `kernel::prelude::*`, `module!{}` macro
- Compare side-by-side with the C version from Chapter 36
- What's stable, what's nightly, what's blocked
- **Lab:** the Chapter 36 LKM, rewritten in Rust, `insmod`s and `printk`s
- **Pages:** ~14

---

# PART VII — DEVICE COOKBOOK *(v1.3, new)*

> *Part VI taught you the kernel's driver frameworks with one good example each. This Part is the reference: for each common device class, two or three real chips compared side-by-side, with schematics, DT bindings, driver code or kernel-driver enablement, user-space access, and the pitfalls specific to each chip.*
>
> *Each chapter follows a tighter template: **What it does → Compare alternatives → Wiring/schematic → DT example → Driver (existing or write) → User-space access → Lab → Pitfalls**. Most chapters are ~12–14 pages. Read sequentially or hop directly to the chapter for the chip in front of you — chapters in this Part are almost entirely independent of each other.*

## Group A — Storage devices

### Chapter 64 — QSPI NOR flash
- **Chips:** Winbond W25Q128 / W25Q64; Macronix MX25L256; Micron MT25Q. Trade-offs (size, speed, erase granularity, security features).
- The i.MX6ULL QSPI controller and its limits
- DT bindings for `spi-nor`; `m25p80`; the `jedec,spi-nor` compatible
- MTD partitions for u-boot env, kernel, dtb, rootfs slot A/B
- Erasing and writing from user-space: `mtd-utils` (`flash_erase`, `nandwrite`, `flashcp`)
- XIP from QSPI — when it makes sense, when it doesn't
- **Lab:** partition a W25Q128, store the U-Boot env on it, boot kernel from it via FIT
- **Pitfalls:** read-only mode after lockdown; quad-mode vs single-mode performance trap
- **Pages:** ~16

### Chapter 65 — I²C / SPI EEPROM
- **Chips:** Microchip AT24C02/32/256/512 (I²C); AT25-series (SPI); 25LCxx (SPI).
- The `at24` kernel driver and what its DT properties really do (`pagesize`, `read-only`, `wp-gpios`)
- The `nvmem` framework: where EEPROM cells become typed kernel-side accessors
- Writing the MAC address from EEPROM into the FEC at probe time
- Wear: page-write counting, the "spread your writes" pattern
- **Lab:** store board serial number + MAC in an EEPROM; verify FEC picks it up
- **Pitfalls:** I²C addressing scheme variants; the 256-byte boundary "rollover" bug
- **Pages:** ~12

### Chapter 66 — SD card and eMMC deep dive
- The MMC subsystem; SDIO is the same machinery (Ch 91 will reuse it)
- Speed modes: DS, HS, HS200, HS400 — what your eMMC and your i.MX SDHC support
- CMD23 vs CMD12 multi-block read terminators
- eMMC partition table: boot partitions, RPMB, GP areas
- Wear-levelling: what eMMC firmware does, what UBI does, what neither does
- TRIM/discard for eMMC vs SD
- **Lab:** read out an eMMC's "device life-time estimation" via the EXT_CSD register; measure HS200 throughput vs HS
- **Pages:** ~16

## Group B — Environmental sensors

### Chapter 67 — Temperature / humidity / pressure
- **Chips:** Bosch BME280 (T/H/P I²C+SPI); Sensirion SHT3x (T/H I²C, lab-grade); ASAir AHT20 (T/H I²C, cheap).
- IIO drivers for each; how user-space reads via `/sys/bus/iio/devices/`
- Calibration registers in BME280; why the raw reading isn't the temperature
- Polling vs trigger-driven sampling
- Time-averaging in user-space: simple moving average vs exponential
- **Lab:** record T/H/P to CSV every 10 s for 24 h; plot drift
- **Pitfalls:** self-heating in BME280 (the device's own current warms its sensor); the "after power-on wait 2 ms" SHT3x trap
- **Pages:** ~14

### Chapter 68 — Light & color sensors
- **Chips:** Rohm BH1750 (ambient lux, I²C); AMS TSL2561 (broad-band + IR-channel, I²C); Vishay VEML7700 (low-power lux).
- IIO drivers, `in_illuminance_input` interpretation
- The "logarithmic eye" — what lux means and when it lies
- **Bonus:** AMS TCS34725 (RGB color sensor) and Avago APDS-9960 (RGB + gesture); driver and DT included
- **Lab:** an ambient-light-driven backlight regulator in user-space
- **Pitfalls:** TSL2561's IR-saturation regime; lens / window choice on enclosure
- **Pages:** ~14

### Chapter 69 — Air quality, gas, particulate matter
- **Chips:** Sensirion SCD30 (CO₂ NDIR, I²C); AMS CCS811 (eCO₂/TVOC, I²C); Plantower PMS5003 (PM1/2.5/10, UART); Nova SDS011 (PM2.5/10, UART); MQ-x analog series + ADC.
- Why "eCO₂" is *not* CO₂ (CCS811 estimates from VOCs and resistance drift)
- NDIR true-CO₂ measurement (SCD30); cost vs accuracy
- Laser-scattering PM sensors; airflow control via fan PWM
- The 24-hour warm-up problem with CCS811
- **Lab:** a 5-channel home air-quality monitor → MQTT → Grafana
- **Pitfalls:** MQ-x cross-sensitivity (most "MQ-2 = LPG" claims are wrong); PM-sensor fan failure detection
- **Pages:** ~14

## Group C — Motion sensors

### Chapter 70 — I²C IMUs
- **Chips:** InvenSense MPU6050 (6-axis, classic); MPU9250 (9-axis with mag); InvenSense ICM-20948 (newer 9-axis).
- The IIO trigger/buffer mechanism for 6-/9-axis IMUs at 1000 Hz
- DMP firmware blob in MPU6050 — what it gives you (quaternions), what it costs (closed-source, less control)
- The magnetometer-as-slave-I²C-master quirk in MPU9250
- Tilt-compensated heading; sensor fusion via Madgwick filter in user-space
- **Lab:** a 100 Hz orientation tracker with a quaternion-output API
- **Pitfalls:** stale I²C addresses (0x68/0x69); gyro bias drift after temp changes
- **Pages:** ~16

### Chapter 71 — SPI IMUs (high-rate / low-noise)
- **Chips:** ST LSM6DSO (6-axis); InvenSense ICM-42688 (high-rate, low-noise); Analog Devices ADXL345 (3-axis accel only).
- Why SPI for IMUs above ~400 Hz
- ICM-42688's FIFO and watermark-IRQ — sampling thousands of points per second efficiently
- ODR / range / filter settings
- **Lab:** capture 1 kHz vibration data; FFT analysis for resonance detection
- **Pitfalls:** SPI mode 3 vs mode 0 confusion; ODR vs filter-cutoff mismatch
- **Pages:** ~14

## Group D — Position & distance

### Chapter 72 — Distance & proximity
- **Chips:** STMicro VL53L0X (ToF laser, I²C); VL53L1X (longer range); HC-SR04 (ultrasonic GPIO); Sharp GP2Y0A (IR analog).
- The VL53L0X firmware-loading dance
- ToF lighting/glass surface failure modes
- HC-SR04 vs GPIO timing — why this is hard on Linux without a high-precision timer or PRU
- **Lab:** an "approach detector" with 3 different sensors compared side-by-side
- **Pitfalls:** VL53L0X bus collisions (I²C address conflicts); HC-SR04 +5 V level-shifting
- **Pages:** ~14

### Chapter 73 — Magnetometer / compass
- **Chips:** Honeywell HMC5883L (I²C, common but EOL); QST QMC5883L (cheap clone); Memsic MMC5983MA (newer, lower noise).
- Hard-iron and soft-iron calibration; why your compass points 23° wrong from the start
- IIO `magn_x/y/z` output and the `scale` attribute
- **Lab:** a calibrated digital compass with tilt compensation
- **Pitfalls:** mounting the magnetometer near a buck regulator destroys readings
- **Pages:** ~12

### Chapter 74 — Hall-effect & rotary position sensors
- **Chips:** AMS AS5048A (magnetic rotary, SPI/I²C); Allegro A1324 (linear Hall analog); Infineon TLE5012 (high-rate angular sensor).
- Off-axis vs on-axis sensor placement
- The IIO `angl` channel and absolute-position rotary encoders
- High-rate angular sampling for motor commutation
- **Lab:** an absolute-angle joystick using AS5048A
- **Pitfalls:** magnet-distance sensitivity (1 mm changes everything); diametric vs axial magnets
- **Pages:** ~12

## Group E — Power & current

### Chapter 75 — Current and power monitoring
- **Chips:** TI INA219 (low-side, I²C); INA226 (improved, calibration); INA3221 (3-channel); Allegro ACS712 (Hall analog).
- Shunt selection: heat, accuracy, layout
- INA226 calibration register — why "current_lsb = max_current / 32768"
- 3-rail simultaneous monitoring via INA3221
- **Lab:** a hot-plug power meter with 100 µA resolution
- **Pitfalls:** shared-ground violations; the "ACS712 zero point isn't 2.5 V" calibration
- **Pages:** ~12

### Chapter 76 — Battery fuel gauge + charger
- **Chips:** Maxim MAX17048 (1-cell fuel gauge, I²C); TI BQ27441-G1; TP4056 (cheap charger); MCP73833; TI BQ24074 (path-managed charger).
- The battery-empty problem and SoC (state-of-charge) estimation
- Charger thermal regulation and JEITA temperature profiles
- The `power_supply_class` kernel framework; `/sys/class/power_supply/`
- **Lab:** a Linux laptop-style battery indicator on a Li-ion-powered i.MX6ULL device
- **Pitfalls:** TP4056 mass-production cells without temperature monitoring; SoC drift over months
- **Pages:** ~14

## Group F — Specialty sensors

### Chapter 77 — 1-Wire sensors
- **Chips:** Maxim DS18B20 (digital thermometer, 1-Wire); DHT11 / DHT22 (single-wire T/H, *not* true 1-Wire); DS2480B (1-Wire master).
- The kernel `w1` subsystem and its slave drivers
- Why DHT11/22 is a timing-critical mess on a non-RT Linux (and why dedicated MCU helper is sometimes the answer)
- Parasitic-power mode for DS18B20
- **Lab:** a 10-sensor temperature bus with one GPIO and a long cable
- **Pitfalls:** the "USB-Serial DS9097 emulator does the parity tricks for you" pattern
- **Pages:** ~14

### Chapter 78 — MEMS microphones (I²S)
- **Chips:** InvenSense INMP441 (I²S MEMS); ICS-43434 (lower noise); SPH0645 (similar).
- ASoC DAI for I²S microphones; sampling via `arecord`
- Stereo via two mono mics; beamforming basics
- **Lab:** record 48 kHz stereo from two INMP441s; visualize FFT in real-time
- **Pitfalls:** WS line ringing on long cables; PDM vs I²S confusion
- **Pages:** ~12

### Chapter 79 — Health sensors (HR / SpO2)
- **Chips:** Maxim MAX30100 (basic); MAX30102 (improved, smaller); MAX30105 (with particle-sensing channel).
- PPG (photoplethysmography) raw signal, IR vs red channel
- Heart-rate extraction in user-space; SpO2 calibration constants
- **Lab:** a finger-clip pulse oximeter with continuous HR/SpO2 over MQTT
- **Pitfalls:** motion artifacts (this is why a Fitbit's HR is noisy when you walk); SpO2 accuracy claims
- **Pages:** ~12

## Group G — Analog conversion & clock generation

### Chapter 80 — External ADCs
- **Chips:** TI ADS1115 (16-bit I²C); ADS1256 (24-bit SPI low-noise); Microchip MCP3008 (10-bit 8-ch SPI cheap); Analog Devices AD7606 (16-bit 8-ch parallel sampling, true simultaneous).
- IIO drivers; sample rate vs ENOB trade-offs
- AD7606's true-simultaneous sampling for power-quality / vibration
- Ratiometric measurements (load cell, RTD)
- **Lab:** 8-channel strain-gauge logger with AD7606
- **Pitfalls:** input filter loading; reference-voltage stability
- **Pages:** ~14

### Chapter 81 — External DACs + clock generators
- **Chips:** Microchip MCP4725 (12-bit I²C DAC); Analog Devices AD5663 (16-bit SPI DAC); SiLabs Si5351 (programmable 3-output clock generator); CDCE9xx series.
- IIO `out_voltage*` for DACs
- Si5351 — generating arbitrary clocks for SDR or for chip evaluation
- The kernel `clk` framework integration with external clock chips
- **Lab:** signal generator + clock chain for an SDR front-end
- **Pitfalls:** PLL closed-loop stability; Si5351's "frequency = output * 2^N / M" config nightmare
- **Pages:** ~12

## Group H — Displays

### Chapter 82 — RGB parallel LCD on LCDIF
- **Panels:** ATK4384 (4.3" 480×272); ATK7016 (7" 1024×600); ATK10261 (10.1" 1280×800).
- The DPI / RGB-parallel timing model: pixel clock, hsync, vsync, porches
- `panel-simple` and how to add a custom panel
- DRM/KMS basics for our case; the `imx-lcdif` driver
- Backlight via PWM + `pwm_bl`
- **Lab:** add a custom 5" 800×480 panel; modetest at full refresh rate
- **Pitfalls:** pixel-clock too fast → tearing; reversed RGB swap on the connector
- **Pages:** ~18

### Chapter 83 — SPI LCD
- **Panels:** ST7789 (240×320, 16-bit/18-bit color); ILI9341 (320×240); ILI9488 (320×480).
- mainline `panel-mipi-dbi` driver + DRM tiny architecture
- fbtft legacy and why we don't use it for new designs
- Tearing-effect output and synchronized updates
- **Lab:** a 320×240 ST7789 from `cat /dev/fb0` in 30 lines of DT
- **Pitfalls:** SPI clock ceiling vs panel refresh; backlight-PWM bleed
- **Pages:** ~16

### Chapter 84 — QSPI LCD
- **Panels:** GC9D01, ST77916, Sitronix SF055A; round LCDs popular for smart watches
- Quad-SPI mode in the i.MX6ULL QSPI controller
- The high-bandwidth bytes-per-frame budget
- mipi-dbi-spi quad-mode driver
- **Lab:** drive a 240×240 round display at 60 fps with a system load of < 5 %
- **Pitfalls:** quad mode timing margins; data-order swap
- **Pages:** ~12

### Chapter 85 — OLED & e-paper
- **Panels:** SSD1306, SH1106 (small OLED I²C/SPI); SSD1322 (large yellow OLED); SSD1680 (2.9" e-paper); IT8951 (large e-paper controller).
- `ssd1307fb` legacy framebuffer driver; `repaper` (e-paper DRM driver)
- e-paper refresh modes: full vs partial; ghosting
- **Lab:** a desk indicator + a weather e-paper status panel
- **Pitfalls:** OLED burn-in; e-paper partial-refresh ghost mitigation
- **Pages:** ~14

### Chapter 86 — Touch input ICs
- **Chips:** Vishay TTP223 (single-key cap, GPIO output); NXP MPR121 (12-key cap, I²C); XPT2046 (4-wire resistive touch, SPI).
- Adding capacitive touch buttons to a Linux input device via `gpio-keys`
- MPR121 IIR baseline tracking; setting touch/release thresholds
- 4-wire resistive touch + ADS7846/XPT2046 kernel driver; calibration via `xinput_calibrator`
- Compare with GT911 multi-touch (covered in Ch 55G — separate chip class)
- **Lab:** retrofit a resistive panel to a 4.3" RGB LCD; calibrate in 60 s
- **Pitfalls:** XPT2046's interrupt-pin pulldown; resistive panels' temperature drift
- **Pages:** ~14

## Group I — Cameras

### Chapter 87 — Parallel CSI cameras
- **Sensors:** OmniVision OV7725 (0.3 MP); OV5640 (5 MP, parallel mode); OV2640 (2 MP); GalaxyCore GC2145 (2 MP).
- The i.MX6ULL parallel CSI (no MIPI-CSI on this SoC)
- V4L2 sensor sub-device model
- Sensor-side: PLL, clocks, exposure, gain, white balance, autofocus (OV5640)
- IPU/CSI capture pipeline
- **Lab:** a GStreamer pipeline grabbing 30 fps QVGA video from OV5640
- **Pitfalls:** the 5 MP "still mode" of OV5640 vs streaming; FOV vs lens choice
- **Pages:** ~18

### Chapter 88 — USB UVC cameras
- The `uvcvideo` driver; what works mainstream, what doesn't
- Bandwidth budgeting on USB 2.0 (480 Mbps theoretical; ~30 MB/s practical) — implications for resolution × frame rate
- MJPEG vs YUYV vs H.264 modes
- **Lab:** capture from a standard webcam; record 1080p30 to disk
- **Pitfalls:** bandwidth contention with USB WiFi or USB Ethernet; non-UVC "drivers needed" cameras
- **Pages:** ~10

## Group J — Audio devices

### Chapter 89 — I²S audio codecs
- **Chips:** Cirrus WM8960 (used on many i.MX boards); SGTL5000 (NXP); Everest ES8388 (cheap, ESP32 favourite); TI TLV320AIC3104; Realtek ALC5640.
- ASoC machine + codec + cpu-DAI triplet (referenced in Ch 53)
- Differences: built-in DAC quality, PGA capability, mic-preamp
- Headphone-jack detection
- **Lab:** a stereo MP3 + line-in voice-loopback program
- **Pitfalls:** master/slave clock-mode mismatch with i.MX SSI; sample-rate clock-derivation
- **Pages:** ~16

### Chapter 90 — Digital class-D amplifiers
- **Chips:** TI TAS5805M (I²C-controlled DSP amp); Maxim MAX98357A (pure I²S, no I²C); TI PCM5102A (audio DAC + headphone).
- The "amp without a codec" pattern: send raw I²S, amp does the rest
- TAS5805M's DSP coefficients (EQ, compression, dynamic-range control)
- The Bluetooth-speaker product pattern: A2DP source → I²S → MAX98357A
- **Lab:** add a tunable EQ to a Bluetooth speaker
- **Pitfalls:** ground-loop hum in class-D speakers; TAS5805M's I²C dance during startup
- **Pages:** ~12

## Group K — WiFi modules

### Chapter 91 — SDIO WiFi
- **Modules:** AP6212 (Broadcom-based, used on Point Atom boards); Realtek RTL8189FTV; Marvell SD8801.
- The `brcmfmac` driver for Broadcom; `rtl8xxxu` and out-of-tree `rtl8189es`
- Firmware loading and per-board NVRAM file
- SDIO-WiFi clock and pin signal-integrity issues
- **Lab:** boot Linux with WiFi-only networking; iperf3 over WiFi at 30+ Mbps
- **Pitfalls:** AP6212 + Realtek firmware blob version mismatch; NVRAM regulatory-domain
- **Pages:** ~18

### Chapter 92 — USB WiFi
- **Modules:** Realtek RTL8188EUS (cheap dongles); MediaTek MT7601; Ralink RT5370.
- `rtl8xxxu` (mainline) vs out-of-tree `rtl8188eus` (better)
- Driver kernel-version compatibility hell
- Bandwidth contention vs USB Camera
- **Lab:** swap WiFi between three USB dongles; compare throughput and latency
- **Pitfalls:** out-of-tree DKMS pain; ralink stale signal
- **Pages:** ~14

### Chapter 93 — Hosted WiFi via ESP32 / ESP8266
- **Modules:** ESP32 (esp-hosted firmware); ESP8266 (AT-command firmware).
- The `esp-hosted` driver: SPI/UART transport, Linux sees a normal `wlan0`
- AT-command mode: ESP as a TCP/IP offload engine
- When this beats SDIO: legacy SoCs without SDIO, MCU+Linux co-existence
- **Lab:** Linux WiFi via ESP32 over a single UART; iperf3 measurements
- **Pitfalls:** AT-command flow control; esp-hosted firmware version pinning
- **Pages:** ~14

### Chapter 94 — WiFi+BT combo modules
- **Modules:** AP6212 (BCM43438 — combined); Realtek RTL8723BS (SDIO combo).
- The shared-antenna problem and PTA (packet-traffic arbitration)
- Bringing up both Wi-Fi and BT simultaneously on a shared module
- BT-over-UART + Wi-Fi-over-SDIO on the same chip
- **Lab:** Wi-Fi tethering + BLE peripheral on the same module
- **Pitfalls:** BT/Wi-Fi co-channel coexistence (2.4 GHz crowded)
- **Pages:** ~12

## Group L — Bluetooth & mesh

### Chapter 95 — HCI BLE over UART/USB
- **Modules:** Nordic nRF52 with Zephyr HCI firmware; Broadcom BCM4343 BT; CSR8510 USB.
- The Bluetooth HCI specification; how Linux's `bluez` talks HCI over UART or USB
- `hciattach`, `btmgmt`, `bluetoothctl`
- BLE central vs peripheral; GATT services
- **Lab:** a BLE peripheral that exposes a custom GATT service for temperature/humidity
- **Pitfalls:** UART flow-control; HCI command/event timing
- **Pages:** ~16

### Chapter 96 — AT-command BLE modules
- **Modules:** HM-10 (CC2540 with AT-command firmware); HC-08; JDY-08.
- The "easy" path: BLE without a kernel stack — UART AT commands
- Limitations: max throughput, no real GATT control, vendor-specific quirks
- When this is the right choice (legacy, simplicity, BOM cost)
- **Lab:** a UART-based "BLE serial port" data link in user-space
- **Pitfalls:** firmware variant differences (HM-10 cloned five ways)
- **Pages:** ~10

### Chapter 97 — BLE Mesh
- BLE Mesh protocol layers; provisioning, addressing, models
- `bluez-mesh` daemon and the `meshctl` tool
- Sample mesh networks: 20-node room lighting controller
- **Lab:** provision and control 5 mesh nodes from a Linux gateway
- **Pitfalls:** provisioning friction; mesh-traffic flood prevention
- **Pages:** ~16

## Group M — Long-range & specialty wireless

### Chapter 98 — LoRa
- **Chips:** Semtech SX1278 (legacy, 433/868/915 MHz); SX1262 (current); LLCC68 (cheap SX1262 alternative); EByte E22 modules.
- The kernel `sx127x` driver and user-space LoRa stacks
- LoRaWAN vs LoRa-P2P; ChirpStack vs The Things Network
- Spreading factor, bandwidth, coding rate trade-offs
- **Lab:** a 1 km point-to-point LoRa link with retries and acknowledgement
- **Pitfalls:** frequency-band regulation per region; antenna SWR
- **Pages:** ~16

### Chapter 99 — Sub-GHz proprietary
- **Chips:** Nordic nRF24L01 (2.4 GHz proprietary, 250 kbps – 2 Mbps); TI CC1101 (sub-GHz multi-band); CC1200.
- When nRF24L01 beats BLE (raw throughput, latency, multi-PRX one-PTX hub)
- CC1101 for sub-GHz remote controls and "smart" home devices
- **Lab:** a 50-node star-topology nRF24L01 sensor network
- **Pitfalls:** crystal-frequency mismatch tank-circuit issues; ack-timing in nRF24
- **Pages:** ~12

### Chapter 100 — ZigBee / Thread / 802.15.4
- **Chips:** TI CC2530 (legacy ZigBee, Z-Stack); Nordic nRF52840 (modern, OpenThread); Silicon Labs EFR32MG.
- ZigBee / Thread / 802.15.4 mesh tech compared
- The CC2530 as ZNP (ZigBee Network Processor) → Linux runs zigbee2mqtt
- nRF52840 OpenThread Border Router for the Matter ecosystem
- **Lab:** a 10-node ZigBee mesh in zigbee2mqtt + Home Assistant
- **Pitfalls:** Thread certification and credential setup; ZigBee profile compatibility
- **Pages:** ~16

### Chapter 101 — UWB ranging
- **Chips:** Qorvo (Decawave) DWM1000; DWM3000 (newer, AirTag-compatible UWB IC); NXP NCJ29D5.
- Time-of-flight ranging principle; centimeter-accuracy indoor positioning
- Two-way ranging vs TDoA
- iPhone / AirTag UWB ecosystem and FiRa standard
- **Lab:** 3-anchor 2D position estimation with sub-10-cm RMSE
- **Pitfalls:** antenna delay calibration; multipath in real environments
- **Pages:** ~14

## Group N — Cellular

### Chapter 102 — USB 4G LTE modems
- **Modules:** Quectel EC20, EC25; SimCom SIM7600; Telit LM940.
- QMI vs MBIM vs RNDIS modes (how the modem appears to Linux)
- ModemManager + nm-connection
- Multi-band, LTE Cat-4 vs Cat-6 vs CA
- **Lab:** auto-failover from WiFi to LTE when WiFi drops
- **Pitfalls:** USB power draw of LTE modems (>2A on TX); APN-vs-SIM mismatch
- **Pages:** ~16

### Chapter 103 — UART AT-command modems
- **Modules:** SIMCom A7670C, SIM7600 (UART variants); Air724UG; ML302.
- The PPP+chat approach for legacy modems
- AT-command discovery and capabilities probing
- The 2G/3G legacy chains
- **Lab:** SMS + GPRS data on a UART-only A7670C
- **Pitfalls:** chat script timing; carrier-specific AT command quirks
- **Pages:** ~12

### Chapter 104 — NB-IoT / Cat-M1
- **Modules:** Quectel BC95, BC26; SimCom SIM7080G.
- Low-power cellular IoT — when it makes sense vs LoRa vs WiFi
- AT command flows for ~30 mA RX, sub-mA PSM/eDRX sleep
- MQTT and CoAP profiles for NB-IoT
- **Lab:** a battery-powered NB-IoT sensor that runs 1+ year on a 19 Ah Li-SOCl2 cell
- **Pitfalls:** carrier band availability (NB-IoT not universal); PSM wake-up latency
- **Pages:** ~14

## Group O — Identification

### Chapter 105 — RFID / NFC
- **Chips:** NXP MFRC522 (SPI 13.56 MHz, ubiquitous Arduino-clone); PN532 (I²C/SPI/UART, NFC-A/B/F); NCV6 series (HF-only).
- The MFRC522 register-level dance
- libnfc + neard for high-level NFC
- Mifare Classic vs DESFire — security tier comparison
- **Lab:** an access-control reader with logging; clone-tag warning detection
- **Pitfalls:** Mifare Classic broken-by-default cryptanalysis; NFC reading-range limits
- **Pages:** ~14

### Chapter 106 — Fingerprint sensors
- **Modules:** Grow R503 (capacitive, UART); FPM10A (optical, UART); GT-521F (capacitive); AS608.
- UART command protocols; template enrollment and matching
- libfprint for direct USB fingerprint scanners
- Privacy implications: template storage and revocation
- **Lab:** a 2-factor login flow combining password + fingerprint
- **Pitfalls:** sensor warm-up on first scan; template-format incompatibility across vendors
- **Pages:** ~12

## Group P — Positioning

### Chapter 107 — GPS / GNSS + PPS time synchronization
- **Modules:** u-blox NEO-6M / 8M / 9M (multi-GNSS); ATGM336H (cheap Chinese alternative); SiRFStar V; Quectel L86.
- NMEA-0183 parsing; UBX binary protocol for u-blox
- gpsd + chrony for sub-microsecond PPS time sync
- A stratum-1 NTP server from a Pi-class device + GPS
- **Lab:** a GPS-disciplined NTP server hitting < 1 µs offset
- **Pitfalls:** cold/warm start times; multipath in urban canyons; PPS pulse polarity
- **Pages:** ~14

## Group Q — Industrial buses

### Chapter 108 — RS-485 + Modbus RTU
- **Transceivers:** Maxim MAX485, SP3485; Analog Devices ADM2483 (isolated); MAX13487 (auto-direction).
- RS-485 physical layer: differential pair, biasing, termination, fail-safe
- DE/RE direction control via GPIO or auto-direction transceivers
- Linux RS-485 mode in the UART driver (`SER_RS485_ENABLED`)
- Modbus RTU framing and libmodbus
- **Lab:** a 5-slave Modbus RTU network with PV inverters
- **Pitfalls:** termination resistor placement; ground reference between segments
- **Pages:** ~14

### Chapter 109 — LIN bus
- **Transceivers:** NXP TJA1020, TJA1027; Microchip MCP2003B.
- LIN as a "UART with break and checksum" sub-CAN bus
- Master/slave roles; PID, response, classic checksum vs enhanced
- Linux's lack of native LIN — userspace SLIP-style or custom driver
- **Lab:** an HVAC blower-control LIN slave talking to a real automotive ECU
- **Pitfalls:** LIN frame timing tolerance; cable-length-vs-baud trade-offs
- **Pages:** ~12

### Chapter 110 — CAN deep dive
- (Extension of Ch 55C) **Transceivers:** TJA1051 (5 V), TJA1463 (CAN-FD), MCP2562; SPI-CAN bridge MCP2515 (when SoC has no FlexCAN free).
- CAN-FD vs classic CAN; bit-stuffing and frame-rate trade-offs
- ISO-TP for ISO-15765 diagnostics
- SocketCAN advanced: BCM (broadcast manager), CAN-J1939
- **Lab:** an OBD-II diagnostic tool reading PIDs from a real car
- **Pitfalls:** termination 60 Ω vs 120 Ω; differential signal-integrity at 1 Mbit/s
- **Pages:** ~16

## Group R — Motors & encoders

### Chapter 111 — Quadrature encoders & rotary
- **Devices:** incremental optical encoders; magnetic encoders; the `rotary_encoder` driver and `gpio-keys` for low-res.
- Hardware quadrature decode on i.MX6ULL's eXtended quadrature decoder (XBAR + ENC)
- A 2-pin GPIO quadrature decode in software (and why it doesn't work at high speed)
- IIO `angl` channel
- **Lab:** a velocity-controlled motor closed-loop with a 1024-line encoder
- **Pitfalls:** Z-index pulse handling; debouncing mechanical encoders
- **Pages:** ~12

### Chapter 112 — Stepper & DC motor drivers
- **Drivers:** TI DRV8825 (stepper, micro-stepping); Allegro A4988; Trinamic TMC2209 (silent stepper with UART config); BTS7960 (43 A H-bridge DC); DRV8302 (BLDC).
- Step-Dir control via PWM/GPIO with a kernel `pwm` driver
- TMC2209 UART config of microstep, RMS current, stallGuard
- BLDC commutation: trapezoidal vs sinusoidal vs FOC
- **Lab:** a 3-axis CNC with TMC2209 silent steppers
- **Pitfalls:** missed steps from EMI; back-EMF damage to drivers
- **Pages:** ~16

## Group S — Indicators & smart LEDs

### Chapter 113 — WS2812 / SK6812 / APA102 addressable LEDs
- **Chips:** WS2812B (timing-strict 1-wire); SK6812 (similar, RGBW variant); APA102 (SPI-based, no timing issues).
- Three implementation approaches:
  1. **GPIO bit-bang** with PREEMPT_RT — only viable for short strips
  2. **PWM + DMA** — repurpose PWM for serial bitstream
  3. **SPI + DMA** — encode WS2812 timing in SPI bytes; cheap and robust
- APA102's SPI native protocol; per-pixel global brightness
- **Lab:** a 100-pixel WS2812 ring at 30 fps via SPI+DMA
- **Pitfalls:** 5 V level shifting from 3.3 V GPIOs; long-strip data-line integrity
- **Pages:** ~14

### Chapter 114 — Beepers, relays, SSRs
- Passive beepers via PWM; active beepers via GPIO
- Mechanical relays vs MOSFETs vs SSRs — when to use which
- AC SSR safety: opto-isolation, zero-cross switching, snubber circuits
- **Lab:** a 4-channel home automation relay board with software-debounced switching
- **Pitfalls:** relay-coil flyback; SSR sub-cycle leakage
- **Pages:** ~10

## Group T — Network & system power

### Chapter 115 — Dual FEC + hosted Ethernet
- Both i.MX6ULL FEC1 + FEC2 simultaneously: pin-mux, PHY-per-MAC, sep subnets
- IP forwarding, bridging, and bonding between the two
- **Chips:** WIZnet W5500 (SPI Ethernet with hardware TCP/IP); Microchip ENC28J60 (cheaper but slower).
- Adding a 3rd Ethernet via SPI when you need 3+ network interfaces
- **Lab:** a router with two Ethernet ports + one SPI Ethernet port; iperf3 throughput
- **Pitfalls:** clock skew between PHYs; W5500 socket exhaustion
- **Pages:** ~16

### Chapter 116 — PMICs and regulator framework
- **Chips:** NXP PCA9450 (i.MX-recommended PMIC); PF8200; Rohm BD71850MWV.
- The `regulator` framework: consumer/provider model
- Voltage sequencing for SoC + DDR + I/O rails
- Dynamic voltage scaling integration with DVFS (Ch 51B)
- **Lab:** add a PMIC to a board that previously used discrete LDOs; measure power savings
- **Pitfalls:** boot-sequence races (kernel boots before PMIC's voltage settles); thermal throttling
- **Pages:** ~16

### Chapter 117 — External RTC
- **Chips:** Maxim DS3231 (TCXO, ±2 ppm); NXP PCF8563 (common cheap); Microchip MCP79410 (with EEPROM).
- Why crystal RTCs drift (and why TCXO is worth the money for fleets)
- Battery-backed time keeping; the "RTC dead but device works" failure mode
- `hwclock`, `rtc-i2c` family of drivers
- Alarm interrupts for wake-from-suspend (Ch 51B integration)
- **Lab:** sub-second RTC tracking across power cycles; calibrate DS3231 over a week
- **Pitfalls:** the i.MX6ULL internal RTC is part of SNVS and loses time without backup battery; DS3231 alarm-pin polarity
- **Pages:** ~12

---

# PART VIII — DEBUG, PRODUCTION, ADVANCED

> *(Originally Part VII in v1.2; renumbered to Part VIII when Part VII / Device Cookbook was inserted in v1.3.)*

### Chapter 118 — JTAG, OpenOCD, GDB at every layer
- Connecting a JTAG adapter (FT2232H / J-Link) to the Point Atom JTAG header
- OpenOCD config for i.MX6ULL
- GDB scripts for bare-metal, U-Boot (`gdb-multiarch u-boot`), and the kernel (`vmlinux` symbols)
- Hardware breakpoints, watchpoints
- **Pages:** ~20

### Chapter 119 — Kernel debugging without JTAG
- `printk` and log levels
- `pr_debug` and `CONFIG_DYNAMIC_DEBUG`
- ftrace: `function`, `function_graph`, events
- trace-cmd and KernelShark
- `bpftrace` and `bcc` tools (introductory)
- kgdb over UART
- Decoding an oops: `addr2line`, `scripts/decode_stacktrace.sh`, `CONFIG_DEBUG_INFO`
- **Pages:** ~26

### Chapter 120 — User-space debugging
- `gdbserver` on target, `gdb-multiarch` on host
- `strace`, `ltrace`
- `perf` (sampling, counters, flamegraphs)
- Core dumps and `coredumpctl`
- **Pages:** ~20

### Chapter 120A — Inserted (v1.2): Mainline patch submission workflow
If you write a driver in this book and it's good, it can go upstream. We walk the entire process end-to-end on a real candidate patch (e.g., a tweak to the FEC driver, or a YAML binding for a new sensor).
- `git format-patch` and the one-patch-per-fix discipline
- `scripts/checkpatch.pl --strict`; the warnings that matter, the ones that don't
- `scripts/get_maintainer.pl` to find the right list and the right reviewer
- `git send-email` setup (the only patch-submission tool the kernel community accepts)
- Subject-line conventions: `[PATCH] drivers/net/ethernet/freescale/fec: ...`
- Cover letters; v1 / v2 / v3 etiquette; `Reviewed-by`, `Acked-by`, `Tested-by`, `Reported-by`, `Suggested-by`, `Co-developed-by`
- Replying to review feedback — what to do, what not to do
- The Lore archive, `b4` for series management
- **Lab:** prepare a real, sendable patch series for one of your earlier driver chapters (do NOT actually send it without a real bug to fix)
- **Pages:** ~18

### Chapter 121 — Capstone: custom board port
- Take your *own* PCB (or rework the Point Atom into a non-trivial variant)
- Port U-Boot, port kernel DT, write at least one peripheral driver for something the original board didn't have
- Reproducible build script: clean checkout → bootable SD in one command
- **Pages:** ~30

### Chapter 121A — Inserted (v1.2): CI/CD for embedded Linux
Modern teams build U-Boot, kernel, rootfs, and run a smoke test on the actual hardware on every commit. We set this up using GitHub Actions (or GitLab CI), a self-hosted runner with USB-OTG to a board, and a small Labgrid-style harness.
- Cross-builds in CI: caching, deterministic builds, `bitbake-no-network` patterns
- Image artifact storage (size budget: ~150 MB per build × 20 commits/day)
- A self-hosted runner with a board on a USB hub
- The minimal smoke test: boot, wait for `=>`, run a 5-second sysfs check, capture serial log
- Pass/fail signaling back to the PR
- Notifications when the board farm is offline
- **Lab:** a GitHub Actions workflow that builds U-Boot+kernel and `uuu`-flashes a real board on every push to `main`
- **Pages:** ~18

### Chapter 122 — Build your own cross-toolchain
- Bootstrap problem: gcc needs libc, libc needs gcc, gcc needs binutils
- crosstool-NG step-by-step: kernel headers → binutils → gcc stage 1 → glibc/musl → gcc stage 2
- Comparing your toolchain against a pre-built Linaro one (size, behavior, sysroot)
- **Pages:** ~24

### Chapter 122A — Inserted (v1.2): BSP → mainline migration playbook
You inherited a Linux 4.1.15 vendor BSP from a previous project or a customer. The product needs to ship updates for the next eight years. You must move to a supportable mainline kernel. Here is the playbook.
- Inventory: list every patch the vendor applied; classify (vendor-feature / vendor-bugfix / mainline-merged / dead-code)
- The pinned-driver problem and how to break each pin
- Per-subsystem upstreaming order (most-self-contained first: clk → pinctrl → gpio → i2c → ... → display/network last)
- Maintaining two trees during the migration (vendor "shipping" + mainline "next")
- Bisection across kernel versions when an old hack now breaks
- When to **not** migrate (truly captive silicon with no mainline future)
- A concrete worked example: NXP i.MX6ULL 4.1.15 → 6.x mainline
- **Pages:** ~22

### Chapter 123 — Yocto vs Buildroot, an honest comparison
- The mental model: package metadata vs configuration system
- Layers, recipes, BBLAYERS
- When Buildroot is better; when Yocto is better; when *neither* is right
- A single recipe written for Yocto and for Buildroot, side by side
- **Pages:** ~22

### Chapter 123A — Inserted (v1.2): Yocto layer development in depth
For shipping at scale, Yocto is industry standard, and the meat of using it is *writing layers*. We build a vendor layer (`meta-mybsp`), a board layer (`meta-mybsp-mini`), and an application layer (`meta-mybsp-myapp`), with the right bbappend pattern between them.
- Layer anatomy: `conf/`, `recipes-*/`, `classes/`, `wic/`
- `bbappend` and the layer-priority dance
- Writing a `.bb` for our LED-driver kernel module (Chapter 41)
- Writing a `.bb` for an in-house Qt app
- `wic` for image layouts (partition tables, RAUC slots)
- Distro layers (`meta-mybsp-distro`) vs board layers
- `IMAGE_FEATURES`, `EXTRA_IMAGE_FEATURES`, `DISTRO_FEATURES`
- The `SRC_URI` cache that makes the build reproducible without internet
- **Lab:** `meta-mybsp/` produces a flashable image with our Chapter 41 LED driver baked in, in < 30 minutes from `bitbake core-image-minimal`
- **Pages:** ~26

### Chapter 124 — Secure boot (HAB) and OP-TEE
- The chain of trust: ROM → SRK fuses → CSF → signed U-Boot → signed kernel → dm-verity rootfs
- HAB CST (Code Signing Tool), `csf` files, key ceremony
- TrustZone primer, `monitor` mode, SMC calls
- OP-TEE basics: TA (Trusted Application) lifecycle
- **Pages:** ~26

### Chapter 125 — Field updates
- A/B partition scheme with U-Boot
- RAUC, SWUpdate, Mender — comparison
- Atomic updates, rollback, fail-safe boot
- **Pages:** ~20

### Chapter 125A — Inserted (v1.1): VSCode + gdbserver remote-debug workflow
Many readers came here from VSCode and would rather debug there than learn `tui` mode. We set up `gdbserver` on the target, `gdb-multiarch` on the host, the VSCode `launch.json` that joins them, and the `.vscode/c_cpp_properties.json` that resolves headers from the cross-sysroot — so `Go to Definition` works on kernel sources too.
- Source Insight as a faster alternative for kernel-source navigation only (read-only, but very fast)
- The minimum target setup: a statically-linked `gdbserver` binary in `/usr/bin/`
- Single-stepping a kernel module loaded with `insmod`
- **Lab:** set a breakpoint in your Chapter 41 LED driver's `probe()`, hit it from `insmod`, inspect `dev`
- **Pages:** ~12

### Chapter 126 — Closing: what to read next
- LDD3 (still relevant where it isn't outdated)
- Bootlin training material
- `kernelnewbies.org`
- LWN — the single most useful periodical for a Linux engineer
- The mailing list etiquette guide; how to send your first patch
- **Pages:** ~6

---

## Total page estimate (v1.3)

| Part | Numbered | v1.1 inserts | v1.2 inserts | v1.3 inserts | Pages |
|------|----------|--------------|--------------|--------------|-------|
| I — Foundations | 8 | — | — | — | 136 |
| II — Bare-metal i.MX6ULL | 10 | +3 (18A–C) | — | — | 252 |
| III — U-Boot | 6 | — | +1 (23A) | — | 128 |
| IV — Kernel | 6 | — | +2 (27A, 30A) | — | 148 |
| V — Rootfs & user space | 5 | +1 (35A) | +2 (35B, 35C) | — | 140 |
| VI — Driver development | 20 | +8 (55A–H) | +5 (51A,B; 52A; 54A,B; 55I) | — | 644 |
| **VII — Device cookbook** *(new)* | **54** | — | — | — | **~735** |
| VIII — Debug & advanced | 9 | +1 (125A) | +4 (120A; 121A; 122A; 123A) | — | 290 |
| **Total** | **118** | **+13** | **+14** | **(none)** | **~2,473 pages** |

### What v1.3 changed at a glance

- **New Part VII — Device Cookbook (54 chapters).** Comprehensive chip-by-chip reference for storage, sensors of all kinds, ADCs/DACs/clock-gen, all display types, cameras, audio, every wireless module class, industrial buses, identification (RFID/NFC, fingerprint), motors/encoders, smart LEDs, network expansion, system power, external RTC. Each chapter covers 2–4 real chips side-by-side with schematic / DT / driver / lab / pitfalls.
- **Renumbering.** Old Part VII (debug, production, advanced) became Part VIII. Old chapter numbers Ch 56–64 are now Ch 118–126; old letter-suffixed insertions (58A, 59A, 60A, 61A, 63A) are now (120A, 121A, 122A, 123A, 125A). The chapter numbers in already-drafted Parts I–VI stay unchanged.

### What v1.2 had changed at a glance

- **Part III**: +Multi-variant FIT images + DT overlays (23A)
- **Part IV**: +DT bindings YAML validation (27A); +Kernel-lifecycle decision framework (30A)
- **Part V**: +Read-only rootfs with overlayfs (35B); +Containers on embedded (35C)
- **Part VI**: +Watchdog (51A); +Power management — runtime PM, DVFS, suspend (51B); +PREEMPT_RT real-time (52A); +MTD/UBI for raw NAND (54A); +V4L2/GStreamer for CSI camera (54B); +Rust-for-Linux (55I)
- **Part VII (old → now VIII)**: +Mainline patch submission workflow (now 120A); +CI/CD for embedded (now 121A); +BSP→mainline migration playbook (now 122A); +Yocto layer dev in depth (now 123A)

---

## Dependency graph (so the reader can prune)

```
Ch1 → Ch2 → Ch3 ─┐
                 ├→ Ch4 ─┐
                 ├→ Ch5 ─┼→ Ch6 → Ch7 → Ch8 → Ch9 → Ch10 → Ch11 → Ch12 ─┐
                 └────── ┘                                              │
                                                                       Ch13 → Ch14 → Ch15 → Ch16 → Ch17 → (Ch18 optional)
                                                                                                      │
                                                          ┌───────────────────────────────────────────┘
                                                          ▼
                                            Ch19 → Ch20 → Ch21 → Ch22 → Ch23 → Ch24
                                                                                  │
                                                          ┌───────────────────────┘
                                                          ▼
                                            Ch25 → Ch26 → Ch27 → Ch28 → Ch29 → Ch30
                                                                                  │
                                                          ┌───────────────────────┘
                                                          ▼
                                            Ch31 → Ch32 → Ch33 → Ch34 → (Ch35 optional)
                                                                                  │
                                                          ┌───────────────────────┘
                                                          ▼
                                            Ch36 → Ch37 → Ch38 → Ch39 → (Ch40..Ch55 mostly independent siblings)
                                                                                  │
                                                          ┌───────────────────────┘
                                                          ▼
                                            Ch64..Ch117 (Device Cookbook — independent chapters; pick the chip you need)
                                                                                  │
                                                          ┌───────────────────────┘
                                                          ▼
                                            Ch118..Ch126 (cross-cutting; read alongside earlier parts)
```

Bare-metal Part II is the *only* part that can be safely skipped by a reader who only wants kernel/drivers. For *your* learning, do not skip it — it's the chapter set that will set this book apart.

### Where the inserted chapters fit in the dependency graph

```
Ch10 ──┬──► Ch18A (project organization)  ──► informs every subsequent bare-metal Ch
       └──► Ch11..Ch16 (proceed normally)
Ch16 ──► Ch18B (button+beep)  ──► Ch17 MMU
Ch18 ──► Ch18C (bare-metal RTC)
Ch35 ──► Ch35A (Ubuntu-base, optional alternative to Ch31/35)
Ch43 ──► any of Ch55A..Ch55H (siblings, independent)
Ch44..Ch55I ──► any chapter of Part VII Device Cookbook (Ch 64..Ch 117) — pick the chip class you need
Ch120 ──► Ch125A (VSCode workflow; can be read after any driver chapter)
```

---

## Project decisions (resolved)

1. **Target board.** Point Atom MINI (i.MX6ULL @ 696 MHz, 512 MiB DDR3L) is the primary reference. The guide deliberately stays general where it can — most chapters work on any i.MX6ULL board, and Parts IV–VIII (kernel, rootfs, drivers, debug, production) transfer to any Linux-capable ARM SoC. Board-specific divergences are called out inline.
2. **Language.** English only. No bilingual edition planned.
3. **Code-listing license.** MIT. Snippets in chapters are copy-paste-into-your-project friendly; no attribution required.
4. **Tooling.** Markdown sources + **Sphinx + sphinx-rtd-theme + myst-parser** rendered to a Read-the-Docs-style site. Hosted on GitHub Pages, auto-rebuilt on push. See [PUBLISH.md](PUBLISH.md).
5. **Code delivery.** **Inline in the chapters.** There is no companion `code/` repository. The drivers, scripts, and configurations shown are complete enough to read, type, and adapt; the lab sections describe what to build but do not ship a reference solution.
