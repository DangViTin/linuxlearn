# Embedded Linux on i.MX6ULL — From First Boot to First Driver
**Architecture, Interfaces, and Design Decisions**

**Target board:** Point Atom (正点原子) MINI, with revision-specific schematics: i.MX6ULL Cortex-A7 and a documented 512 MiB DDR3L core-board example. Check the fitted chip's speed grade before selecting clocks. Other boards require their own power, DDR, storage, pin, and peripheral configuration; a pin change alone is not a port.
**Target reader:** Embedded engineer fluent in MCU / bare-metal / RTOS, new to Linux.
**Host environment:** Native x86_64 Ubuntu 22.04 LTS is the Chapter 3 baseline. A VM needs working USB passthrough and a reachable board Ethernet connection.
**Linux kernel target:** v6.6 LTS. Driver-API signatures (`class_create`, `i2c_driver.probe`, `i2c_driver.remove`) and DTS paths (`arch/arm/boot/dts/nxp/imx/`) in this book follow v6.6 conventions.
**Philosophy:** Understand what each layer owns, the contracts between layers, and the consequences of a design choice. Code and commands make those mechanisms visible, not a sequence of assignments. Mainline sources, vendor documentation, and board schematics are reference material. Part VIII later covers toolchain construction and Yocto.

---

## Scope

**9 Parts, 178 chapters (131 numbered + 47 supplementary, "letter-suffix" convention).** The numbered chapters provide the conceptual reading path. Supplementary chapters (letter-suffixed: `18A`, `18B`, `35A`, `52A`, etc.) explore particular design problems and can be read when relevant. Each chapter ends with Key Notes rather than an assigned lab. Examples are not claims of qualified hardware behavior. Parts IV–IX still need full technical and hardware review.

## What the book covers

- **Part I — Foundations.** Host setup, the ARMv7-A architecture as it differs from Cortex-M, the i.MX6ULL SoC, the GNU toolchain, the Boot ROM's `IVT` / `DCD` / `BootData` contract, and a hardware bring-up checklist.
- **Part II — Bare-metal i.MX6ULL.** The mechanisms beneath a bootloader: reset entry, C runtime and linker layout, the ROM image contract, UART, clock and DDR initialization, exceptions, timers, MMU and caches. Peripheral examples connect register-level behavior to ownership, timing and data flow.
- **Part III — U-Boot, deeply.** A MINI-first vendor baseline and a separate mainline study tree show how startup, board support and boot policy fit together. GPIO, I2C, display, networking, board identity, rollback, recovery and power checks are design studies. `bootcmd`, `bootargs`, FIT and development transports expose the contracts between ROM, bootloader and kernel. MINI hardware and optional modules remain distinct.
- **Part IV — The Kernel.** Build mainline Linux for i.MX6ULL, boot it from U-Boot, debug failed boots, describe a custom board with Device Tree, validate DT bindings, trace `start_kernel()` to PID 1, build an initramfs, turn it into a recovery system, manage product configs, and choose a kernel lifecycle.
- **Part V — Root filesystem & user space.** A `busybox`-based hand-built rootfs; `/proc` `/sys` `devtmpfs`; init systems; libc and dynamic linking; Buildroot; bootable SD/eMMC and SPI NOR images; product board directories; Ubuntu-base as a fully-featured alternative; services, networking, time, logging, security, read-only root + overlayfs, and containers on embedded.
- **Part VI — Driver development.** ~33 chapters covering every common subsystem from char devices and platform drivers through I²C/SPI/PWM/RTC/IIO/regmap/DMA/Net/Sound/DRM/USB, with deeper treatment of CAN, multi-touch, block devices, WIFI, cellular modems, HDMI bridges, kernel timers, async notification, watchdog, power management, PREEMPT_RT real-time, MTD/UBI, V4L2/GStreamer, and a Rust-for-Linux sidebar. **One canonical example per subsystem** — depth on real chips lives in Part VII.
- **Part VII — Device cookbook.** 54 chapters compare device choices through electrical interfaces, Linux subsystem support, data flow, timing and failure limits. Schematics, Device Tree and code examples illustrate those choices. Storage, sensors, converters, displays, cameras, audio, wireless links, industrial buses and actuators can be read as independent references.
- **Part VIII — Debug, production, advanced.** Observability across layers, kernel and userspace debugging, board-port design contracts, build inputs, Yocto layer development, secure boot, field updates, upstream maintenance, CI evidence and BSP migration.
- **Part IX — Applied virtualization and mixed-criticality systems.** QEMU as a virtual hardware model, ARM HYP mode, Xen guest boundaries, device ownership, DMA and isolation limits, Jailhouse partitioning, and STM32MP1's Linux/RTOS A7/M4 split. Virtual examples explain architecture, not MINI electrical or timing qualification.

---

## How to read this book

Start with Chapter 1. Follow the problem, then the mechanism and its design consequences. A register listing or command can be read as evidence of an interface without reproducing it. Chapters use **Key Notes** to collect their important architectural decisions and limits, alongside pitfalls and primary references. They do not require a repeated section template or completed exercises.

---

## PART I — FOUNDATIONS

> *You are an MCU engineer. You know what a vector table is, what a linker script is, what `volatile` is for. This part exists to give you names for the things Linux adds on top.*

### Chapter 1 — Preface and how to use this book
- Who this book is for (the MCU/bare-metal engineer)
- What we mean by "raw" and where integrated build systems fit later
- Conceptual reading routes, optional references, and the limits of examples
- How chapters depend on each other (dependency graph)
- Conventions: prompt symbols, register notation, file paths
- **Key Notes:** **Layers have owners.** ROM, bootloader, kernel and application make different decisions. A failure becomes easier to reason about when the responsible layer is identified.

### Chapter 2 — What "Embedded Linux" actually is
- The four layers: Boot ROM → Bootloader → Kernel → User space
- Kernel space vs user space; the syscall boundary
- Process, thread, file descriptor — vocabulary first
- How this differs from your RTOS: virtual memory, demand paging, ELF loading
- Why Linux is "big" (and where its size actually lives)
- **Focus:** the *user/kernel split* is the single most important concept in the whole book
- **Key Notes:** Boot is a sequence of ownership transfers: the ROM selects and loads an image, the bootloader prepares Linux's inputs, and the kernel starts user space. Ordinary application requests do not return through the bootloader.

### Chapter 3 — Host environment setup
- Choosing a host OS (Ubuntu 22.04 LTS); why native Linux beats WSL/VM for this work
- Essential build/inspection packages first; TFTP/NFS services are a separate later-preparation track
- Installing two project-local Arm GNU toolchains: `arm-none-linux-gnueabihf-` for Linux and `arm-none-eabi-` for bare metal
- A short, explicitly sourced environment script; no global compiler installation or shell-startup changes
- Manual TFTP/NFS configuration with scoped access and undo instructions; explicit privileged serial/USB access
- Project-local NXP `uuu` (Universal Update Utility), pinned to a named release
- A reproducible workspace layout for the rest of the book
- **Key Notes:** Compiler installation and compiler selection are separate state. `. ~/imx6ull/scripts/env.sh` changes the current Bash shell and its future children, not another already-open terminal. Running the file in a child shell cannot change its parent.

### Chapter 4 — ARMv7-A and the Cortex-A7, for the MCU engineer
- ARMv7-A vs ARMv7-M: what Cortex-A adds (MMU, privilege levels, generic timer, NEON, multicore option)
- Exception model: USR / SYS / SVC / IRQ / FIQ / ABT / UND (and how this maps to Linux's user/kernel split)
- Banked registers, the program status register, mode switching
- Generic-timer architecture versus the actual timer enabled by the selected Linux configuration
- Cache hierarchy: L1 I/D, integrated L2 inside the Cortex-A7 MPCore (128 KB on i.MX6ULL — no external PL310), inner/outer shareable, MESI
- MMU concepts: virtual address, page table walk, TLB, ASIDs, domains
- NEON / VFP overview
- **Focus:** MMU + privilege modes on this Cortex-A7 Linux path, with worked exception/register examples
- **Key Notes:** A Cortex-A7 exception selects banked SP/LR and saves status, but does not push a Cortex-M-style register frame. Shared registers, usable mode stacks, and return-state preservation remain software responsibilities.

### Chapter 5 — A tour of the i.MX6ULL SoC
- Block diagram and what each block does
- Memory map: OCRAM, ROM, DDR aperture, peripheral regions
- Clock tree at 30,000 ft: oscillators → PLLs → CCM → root clocks → peripheral gates
- Power domains and the PMU
- IOMUX: the universal-multiplexer pattern (and how `iomuxc.h` is generated)
- Boot fuses (eFuses) and BOOT_MODE pins
- The supplied 4,127-page reference manual: a verified chapter catalog and worked UART1 lookup
- **Key Notes:** A usable peripheral path combines a controller address, a live clock, the selected pad function, electrical settings, and board routing. Correctness at one point does not establish the rest of that path.

### Chapter 6 — The toolchain
- `gcc` is *not* one tool: cpp, cc1, as, collect2, ld
- `binutils`: `as`, `ld`, `objcopy`, `objdump`, `nm`, `readelf`, `strip`, `ar`, `addr2line`
- The C library: glibc vs musl vs uClibc-ng vs newlib; why our first bare-metal builds use no C library
- ABI: EABI vs hard-float vs soft-float; `arm-none-linux-gnueabihf` decoded
- ELF format: program headers vs section headers; what the loader actually reads
- Linker scripts: `MEMORY`, `SECTIONS`, `VMA` vs `LMA`, `ENTRY`, `KEEP`
- Make basics that matter: implicit rules, pattern rules, automatic variables, `.PHONY`, recursive vs non-recursive
- **Key Notes:** The GCC driver coordinates preprocessing, compilation, assembly, and linking. A valid object file does not establish that symbol resolution or final placement succeeded, and an old output file can survive a failed rebuild.

### Chapter 7 — The Boot ROM, IVT, DCD, and BootData
- What the Boot ROM does on power-on (in order, with addresses)
- Reading `BOOT_MODE[1:0]` and `BOOT_CFG` pins
- Boot device options: SD/eMMC, NAND, SPI-NOR, USB-SDP, EIM-NOR
- The **IVT (Image Vector Table)**: layout, every field decoded
- The **DCD (Device Configuration Data)**: a tiny scripting language the ROM executes to bring up DDR and clocks *before your code runs*
- The **BootData** structure: load address and image length
- USB-SDP (Serial Download Protocol): command IDs and the later `uuu` transfer path
- HAB (High Assurance Boot) introduction (deep-dived in Ch. 124)
- **Focus:** distinguish image placement, linked addresses, DCD initialization, and the alternative SPL-first path
- **Key Notes:** The Boot ROM is a loader with a fixed contract. The IVT names the entry point and associated structures, BootData describes the loaded extent, and DCD supplies initialization before application code can run.

### Chapter 8 — Hardware bring-up checklist
- Unboxing the Point Atom board: physical inspection, jumpers, SD slot, OTG cable
- Establish the exact input rating, polarity, selector/jumper settings, and USB power interactions from the matching supplier guide before applying power
- Unpowered short screening is not proof of healthy rails; powered measurements need documented test points and limits
- UART1 wiring (TXD/RXD/GND), correct voltage levels, 115200 8N1
- Identify the removable card and record its identity; re-identify it before every later write
- Optional: JTAG header pinout, OpenOCD interface adapter (FT2232H, J-Link)
- Revision-specific USB boot selector and ROM SDP enumeration; transfer/execution are later milestones
- **Key Notes:** Bring-up evidence belongs to a particular board revision, fitted core and power arrangement. A matching product name is not enough to transfer another board's connector, voltage or selector assumptions.


---

## PART II — BARE-METAL i.MX6ULL

> *Before Linux can manage a board, something must establish memory, clocks and a way to report errors. These chapters show those responsibilities directly, in OCRAM and then DDR, so they remain recognizable inside a bootloader.*

### Chapter 9 — First LED, pure assembly
- Reset vector and where the Boot ROM jumps to
- Setting up the SVC-mode stack in OCRAM
- Enabling the GPIO clock via CCM_CCGR registers
- IOMUX configuration for the LED pin (Point Atom schematic pin)
- Direct GPIO data register write
- Infinite loop (no return, no exit)
- Building with `as`, linking with `ld`, image with `objcopy -O binary`
- **Key Notes:** The ROM owns loading and the initial handoff. The assembly payload owns the GPIO configuration after entry, with no C runtime, scheduler or DDR dependency.

### Chapter 10 — C + startup.S + linker script
- Why pure C cannot run yet: who sets the stack pointer, who clears `.bss`, who copies `.data`?
- `startup.S`: stack init, `.bss` zero, `.data` copy from LMA to VMA, branch to `main`
- A complete linker script: `MEMORY` block, `SECTIONS`, `_etext` / `_sdata` / `_edata` / `_sbss` / `_ebss` symbols
- The `.init`, `.text`, `.rodata`, `.data`, `.bss` regions and why each exists
- `__attribute__((section(...)))` and when to reach for it
- Makefile that compiles `.S` and `.c` together, links, makes raw binary
- **Key Notes:** The linker describes placement and exports boundaries. Startup establishes the aligned stack and object contents before calling C. Neither the compiler nor the IVT supplies that runtime preparation.

### Chapter 11 — Hand-building a Boot ROM-acceptable image
- Recap of Ch. 7: what the Boot ROM expects to find at offset 0x400 of the boot media
- Writing a `.cfg` file for `mkimage -T imximage` — *but first*, do it manually so we know what the tool generates
- Walking the IVT byte-by-byte in a hex editor
- Writing a DCD script that initializes SDRAM controller for DDR3 (we'll use NXP's tested values for now; we derive them ourselves in Ch. 14)
- Padding and offsets for the SD card layout: where the IVT lives, where the image lives
- File, media and RAM offsets are separate parts of the ROM image contract
- **Pitfall:** off-by-one in the IVT `self` pointer is the #1 reason boards "do nothing"
- **Key Notes:** File offsets, media offsets and RAM addresses are different coordinates. In this primary SD layout, writing the already-padded file at media byte zero places the IVT at `0x400`. An extra seek would shift it out of place.

### Chapter 12 — UART driver and `printf`
- UART1 register map: USR1, URXD, UTXD, UCR1–4, UFCR, UBIR, UBMR
- Computing the baud divisor from the module's input clock
- Polling-mode TX/RX
- Implementing a minimal `_putchar()` so we can hook up `printf`
- A 200-line `printf` clone (or use a tiny third-party one like `mpaland/printf`) — we explicitly avoid pulling in newlib
- **Key Notes:** UART1 transport and number formatting are separate interfaces. The integrated USB-TTL bridge carries console bytes, while USB-OTG carries ROM downloader commands.

### Chapter 13 — CCM clock tree bring-up
- The clock tree, drawn end-to-end for i.MX6ULL: 24 MHz XTAL → ARM PLL / System PLL → root clocks → peripheral gates
- CCM, CCM_ANALOG, and PMU register groups
- Auditing selected clock paths without changing live operating points
- AHB and IPG bus clocks
- The CCGR gating registers: each peripheral has 2 bits, what they mean
- Side topic: how to compute power for a given clock configuration
- **Key Notes:** A frequency belongs to a complete selected path: reference, PLL or bypass, PFD where used, muxes and dividers. CCGR gates control availability, not rate.

### Chapter 14 — DDR3 initialization with MMDC
- DDR3 fundamentals refresher: banks, ranks, rows, columns, CL/tRCD/tRP/tRAS
- Reading your specific DDR3 chip's datasheet (Point Atom schematic → part number)
- The MMDC (Multi-Mode DDR Controller) register groups: MDCTL, MDPDC, MDOTC, MDCFG0/1/2, MDMISC, MAARCR, MAPSR, MPPDCMPR1/2, MPWLDECTRL0/1, MPDGCTRL0/1, MPRDDLCTL, MPWRDLCTL, MPMUR0…
- The DDR3 initialization sequence per JEDEC: precharge all → MR2 → MR3 → MR1 → MR0 → ZQCAL
- Calibration: write leveling, DQS gating, read/write delay calibration
- Using NXP's DDR Stress Tool to verify your settings before trusting them
- Translating verified register values into a DCD script
- **Focus:** matching initialization assumptions to fitted memory and its qualification limits
- **Key Notes:** DDR availability depends on a matched clock, geometry, electrical setup, timing/command sequence, refresh and calibration. A valid address or a copied delay table establishes none of that configuration by itself.

### Chapter 15 — Exceptions and the GIC
- The ARMv7-A exception vector table (8 entries) and its software responsibilities
- High vs low vectors (`VBAR` register)
- The GIC v2 (Generic Interrupt Controller): Distributor + CPU Interface, register maps
- Configuring an SPI (Shared Peripheral Interrupt) and an SGI (Software-Generated Interrupt)
- Top-half ISR pattern in bare-metal: save context, ack the GIC, call C handler, return from exception
- **Key Notes:** Cortex-A7 banks IRQ SP/LR and saves CPSR, but software owns shared-register preservation, stack alignment and exception return. A C handler alone is not an exception-entry interface.

### Chapter 16 — Timers (EPIT and GPT)
- EPIT (Enhanced Periodic Interrupt Timer): a 1 ms tick
- GPT (General Purpose Timer): free-running counter for delay/timestamp
- Building `udelay()` and `mdelay()` primitives
- Using GPT as a profiling tool: cycle-count any function
- **Key Notes:** GPT's free-running count represents elapsed ticks. EPIT requests periodic service. Their clocksource/clockevent roles separate time measurement from scheduling, without prescribing Linux's eventual timer selection.

### Chapter 17 — MMU and caches
- Why we want the MMU on, even in "bare-metal": cache control
- Translation regimes: TTBR0/TTBR1, 32-bit short-descriptor format
- Building a first-level page table that maps SoC peripherals as Device memory and DRAM as Normal Cacheable
- Domains and access permissions
- Enabling the I-cache and D-cache (`SCTLR` bits)
- Cache maintenance: invalidate, clean, clean+invalidate by VA, set/way
- Measuring the performance difference with the GPT
- **Focus:** you now possess *every* primitive Linux needs from firmware. Carry this fact through Part III.
- **Key Notes:** Identity mapping preserves pointer values but changes access checks and memory behavior. Device/XN register mappings and Normal RAM mappings are policy choices, not consequences of `volatile`.

### Chapter 18 — Optional bare-metal peripherals
- I²C (I2C1) to an EEPROM on the board
- SPI to an external flash
- LCD via eLCDIF — bring up the framebuffer manually, draw a pattern
- Why we stop here and move to U-Boot
- **Key Notes:** The controller's presence does not establish an attached device. EEPROM address width, flash command set and panel timing belong to the actual populated part and routed board, not a generic i.MX6ULL peripheral name.

### Chapter 18A — Supplementary: Project organization the "STM32-style"
Once a bare-metal program crosses ~500 lines, the single-file layout we used through Ch 14 stops scaling. This chapter refactors our work-so-far into proper header/source separation, register-definition macros in a single `imx6ull.h`, BSP folder layout (`bsp/clk/`, `bsp/gpio/`, `bsp/uart/`, ...), and a top-level `Makefile` that builds the BSP and links it against `main.c`. Also discusses the NXP SDK's `MCIMX6Y2.h` struct-based register approach as an alternative — when to adopt it, when to stay hand-rolled.
- **Focus:** the moment you have ≥2 peripherals, organization saves more time than it costs
- **Key Notes:** SoC offsets, board wiring and driver behavior describe different ownership domains. A shared hardware header prevents duplicate definitions without making every board's routes interchangeable.

### Chapter 18B — Supplementary: Button input and beep (active buzzer)
A polled GPIO input example separates electrical input behavior from software debounce and logical key events. The fitted active buzzer is an on/off output. A passive piezo requiring PWM is a different device, not an interchangeable implementation.
- **Key Notes:** A pad level and an application event are different interfaces. PSR reports the input now. The history filter reports one qualified press or release rather than repeating while a level is held.

### Chapter 18C — Supplementary: Bare-metal RTC (SNVS)
The SNVS (Secure Non-Volatile Storage) is the only always-on domain on the chip; its 32-bit second counter survives main-power-off. We initialize it, set the time, sleep the rest of the SoC, wake it, read it back. Then a small sidebar on how this maps to Linux's `struct rtc_class_ops` in Chapter 48.
- **Key Notes:** The LP counter's 47 bits represent 32.768 kHz ticks, including 15 fractional bits. Whole seconds still need a software-chosen epoch and calendar conversion. Zero is not a valid wall-clock setting by itself.


---

## PART III — U-BOOT, DEEPLY

> *The register-level work from Part II gives us a way to read U-Boot's source. We will trace its framework, distinguish a build from board qualification, and test each boot decision before trusting it.*

### Chapter 19 — U-Boot from source, first boot
- Pin Point Atom's public tutorial source for the documented 512 MiB DDR / 8 GB eMMC MINI core
- Inspect its board files, make the initial configuration visible, and use Chapter 3's existing portable compiler
- Build the MINI vendor target and inspect its no-SPL ROM+DCD image
- Separate file offsets, SD placement, runtime addresses and the reserved environment range
- Inspect commands without sweeping live memory or saving experimental policy
- **Key Notes:** The pinned vendor target describes the documented 512 MiB eMMC core. Shared ALPHA/MINI software does not make every carrier connection or PHY revision interchangeable.

### Chapter 20 — U-Boot SPL: the missing link
- Compare the MINI's ROM+DCD route with ROM+SPL and identify who initializes DDR
- Introduce a separate pinned upstream v2026.04 study tree without replacing the vendor MINI image
- Build a separate PICO i.MX6UL SPL reference for source study, not MINI flashing
- Trace OCRAM startup, DDR-resident BSS, size limits and the board's handoff path
- Distinguish the SPL wrapper, full payload format and raw MMC load sector
- **Key Notes:** DCD and SPL solve the same early-memory dependency with different owners: ROM interprets a table, while SPL executes board-specific initialization code.

### Chapter 21 — U-Boot internals
- Follow ARM entry, current initcall machinery, `board_init_f`, relocation and `board_init_r`
- Explain early stack/global data, selected relocation fixes and the BSS overlay
- Compile and register a complete `book_hello` command
- Separate compiled defaults, RAM environment changes and persistent backend selection
- Distinguish driver binding from probing and U-Boot's control DT from the kernel DT
- **Key Notes:** The ARM full-U-Boot path divides work between C planning and assembly handoff. `board_init_f` records reservations in GD, then `crt0.S` changes stack/GD and relocates execution.

### Chapter 22 — Porting U-Boot to the MINI
- Build a concrete `mx6ull_pa_mini` modern migration from documented MINI/core wiring
- Connect board Kconfig, defconfig, control DTS, header and ROM DCD
- Supply a MINI control tree without the EVK carrier include, and verify the ordered vendor DCD
- Integrate UART1, TF, eight-bit eMMC reset and single ENET2 with a datasheet-matched PHY candidate
- **Key Notes:** A board port connects build selection, control DT, image configuration and board hooks. A matching SoC target alone does not describe the MINI carrier or populated core.

### Chapter 23 — `bootcmd`, `bootargs`, FIT images
- Gate storage selection, root identification, every required load and argument construction
- Explain `bootm`, `bootz`, raw initramfs sizes and separate image buffers
- Trace `/chosen/bootargs`, kernel console/root prerequisites and root versus init failure
- Package a complete script and a kernel+DTB hash-only FIT
- Separate hashes, trusted required signatures and the boot-chain policy
- **Key Notes:** `bootcmd` is U-Boot execution policy, while `bootargs` becomes a candidate Linux command line through the OS FDT. Helpers and kernel configuration can alter what `/proc/cmdline` ultimately reports.

### Chapter 24 — Workflows: TFTP, NFS, USB-OTG
- Stage matched artifacts as real files under the established TFTP server root
- Keep U-Boot's network loader separate from Linux's Ethernet/IP/NFS-root path
- Explain built-in root-network drivers, export permissions and the observed command line
- Separate userspace and kernel rebuild/restart loops
- **Key Notes:** TFTP loads boot payloads into RAM, NFS backs Linux's root filesystem, and ROM USB download enters an earlier recovery stage. They solve different failures and have different prerequisites.

## Optional deep dive

(chapter-24a-supplementary-building-i-mx6ull-u-boot-from-nothing)=
### Chapter 24A — Supplementary: Building an i.MX6ULL teaching port from scratch
- Reuse generic ARMv7 startup and U-Boot frameworks under an independent teaching architecture
- Show complete UART1, clock, GPT1 and USDHC2 PIO driver files and manual integration edits
- Trace bounded polling, baud/clock calculations, reset behavior and card error recovery
- Include the full pinned vendor DDR sequence for the documented 512 MiB eMMC core
- Explain IVT/Boot Data fields, file/media/RAM offsets and evidence checkpoints
- **Key Notes:** The port joins several contracts: ROM image layout, early ARM runtime, U-Boot relocation, Device Tree discovery and peripheral framework callbacks. A correct interface at one stage does not establish the next.

## Applied U-Boot scenarios

### Chapter 24B - Supplementary: U-Boot board policy with GPIO and I2C
- Add late policy to the existing port without duplicating its hook
- Use MINI's stock KEY0 as the first policy input; keep TMP102 as an optional I2C1 add-on
- Claim the GPIO1_IO18 descriptor, handle logical polarity and debounce, then release ownership
- Keep failure closed and dispatch exactly one normal or recovery path
- **Key Notes:** `board_late_init()` runs after environment import but before normal dispatch. A blocked-first hook prevents stale saved commands from opening the gate before required inputs are valid.

### Chapter 24C - Supplementary: Ethernet fallback boot in U-Boot
- Use MINI's single ENET2 route and distinguish older LAN8720 from V2.2 SR8201F support
- Review reset/clock ownership, driver matching and uniquely allocated MAC addresses
- Apply explicit static network state and test DHCP separately
- Gate fresh kernel/DTB loads and arguments on both local and TFTP paths
- Keep fallback before kernel handoff and distinguish a local rootfs from network payloads
- **Key Notes:** Local-first fallback responds to load failures or a boot command returning before handoff. It cannot diagnose a later Linux failure or recover a bootloader that never starts.

### Chapter 24D - Supplementary: Board identity and variant selection in U-Boot
- Define a bounded versioned 64-byte record for an optional external EEPROM, absent from stock MINI
- Validate complete fields, MAC/serial values and supported hardware combinations
- Publish readiness only after checked selection and identity assignments
- Keep unknown identity closed rather than inventing a universally safe DTB
- **Key Notes:** The 64-byte record is a proposed optional-EEPROM interface, not a stock MINI factory format. Fixed hardware can select its matching OS tree explicitly without invented identity data.

### Chapter 24E — Supplementary: Multi-variant FIT images and DT overlays at runtime
- Package fixed-core no-display, ID4342 and ID7016 configurations with matching OS DTBs
- Stage the FIT separately from its kernel destination and name the selected configuration
- Use a complete harmless host overlay fixture and reload both inputs after apply failure
- Distinguish the working OS tree from U-Boot's control tree
- **Key Notes:** FIT configurations share payloads through named references. One bundle simplifies release bookkeeping but does not reduce the set of hardware combinations that need qualification or make updates atomic.

### Chapter 24F - Supplementary: Watchdog, bootcount, and rollback in U-Boot
- Require a separately qualified persistent backend and layout beyond the RAM-only scaffold
- Count candidate attempts and roll back to the recorded good slot
- Gate complete slot loads, root PARTUUID and grouped metadata changes
- Let Linux verify the actual running root, kernel, slot and health before acceptance
- Explain ignored save failures, metadata durability and watchdog-handoff limits
- **Key Notes:** Bootcount measures attempts, not diagnosed kernel failures. With an initial zero and limit three, counts one through three use the candidate and count four selects the alternate command.

### Chapter 24G - Supplementary: Factory and recovery modes in U-Boot
- Distinguish ROM SDP, working-U-Boot services and Linux recovery dependencies
- Distinguish MINI USB_TTL, USB_OTG1 service and USB_OTG2 host connectors
- Review modern controller support and authorized device identity
- Expose only a reviewed disposable target through UMS or DFU
- Require fresh write authorization and preserve exclusive host/target storage ownership
- **Key Notes:** ROM SDP, U-Boot USB service and Linux recovery require progressively more working software. A U-Boot gadget cannot repair an image that prevents U-Boot from starting.

### Chapter 24H - Supplementary: PMIC and power policy in U-Boot
- Trace MINI's discrete regulators, reset supervision and SNVS backup supply
- Separate status/enable requests from coherent measured rail/energy evidence
- Keep an optional monitor's refusal adapter out of stock MINI boot until its hardware is implemented
- Prioritize power veto over normal, alternate and writable recovery paths
- **Key Notes:** The documented MINI/core uses discrete regulators with no fitted I2C PMIC or rail monitor. `PMIC_ON_REQ` is a sequencing net, and the CR1220 backs SNVS rather than powering updates.

### Chapter 24I - Supplementary: U-Boot display and boot screen
- Review the actual video/BMP symbols, LCDIF driver parsing and board header requirement
- Use MINI J1 RGB888 wiring and preserve panel-ID/boot-strap isolation
- Qualify the added panel's timing, power and GPIO1_IO08 backlight separately
- Keep the bounded BMP file buffer distinct from scanout framebuffer and other RAM users
- Make optional splash failure unable to bypass recovery, rollback or power policy
- **Key Notes:** BMP source data, framebuffer pixels and RGB wires are separate formats. The MXS 24/18-bit output paths use 32-bit framebuffer storage, independent of a 24-bit BMP decoder.

### Chapter 24J - Supplementary: SPI LCD and I2C OLED displays in U-Boot
- Distinguish RGB scanout, SPI display RAM and I2C OLED page data
- Do not infer a U-Boot driver from a Linux compatible string
- Implement bounded SPI transport with explicit D/C, CS, byte order and cleanup
- Use a qualified SSD1306 profile, zero offset length and correct command/data control bytes
- **Key Notes:** The stock MINI has neither serial display, and v2026.04 lacks the named panel drivers used in these examples. A compatible string or working bus driver does not supply reset, initialization or rendering.


---

## PART IV — THE KERNEL

> *The kernel is large but knowable. Its boot interfaces, hardware descriptions and configuration form separate parts of the design.*

### Chapter 25 — Building mainline Linux for i.MX6ULL
- Clone the stable tree at the book's pinned tag, `v6.6`
- `make ARCH=arm imx_v6_v7_defconfig`
- The build artifacts: `vmlinux`, `Image`, `zImage`, `arch/arm/boot/dts/nxp/imx/*.dtb`
- `vmlinux` vs `zImage`: who decompresses, when, where
- Modules: `make modules && make modules_install INSTALL_MOD_PATH=...`
- **Key Notes:** A kernel build is defined by its source revision, resolved `.config` and toolchain. An output directory separates generated state from source, but does not make different configurations interchangeable.

### Chapter 26 — Booting the kernel from U-Boot
- Loading via TFTP into RAM with `&&`, so failed downloads stop the boot
- `bootz 0x82000000 - 0x83000000`
- The first 30 lines of kernel boot log — every line decoded
- "Uncompressing Linux... done, booting the kernel." — *where* in the kernel source this happens (`arch/arm/boot/compressed/head.S`)
- **Key Notes:** U-Boot owns image loading and the CPU handoff state. Linux then owns its memory mappings, interrupt handling and driver initialization.

### Chapter 26A — Supplementary: Kernel boot failure playbook
- Keep one known-good `bootz` command and one known-good `bootargs`
- Classify failures: no output, early output then silence, VFS panic, init panic, or driver probe failure
- Use `earlycon`, `loglevel=8`, `ignore_loglevel`, and `initcall_debug`
- Debug wrong DTB, wrong console, bad rootfs, missing init, and NFS root hangs
- **Key Notes:** A boot failure has a stage: image handoff, console availability, root mounting, init execution or device probing. Similar visible symptoms can originate in different stages.

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
- **Key Notes:** The SoC `.dtsi` describes controllers and shared resources. The board `.dts` describes connections, supplies and enabled devices, so a shared SoC does not make two boards' DTBs interchangeable.

### Chapter 27A — Supplementary: DT bindings YAML + `dt_binding_check`
A 2018+ mainline-hygiene requirement. Since kernel v4.18 every new device-tree binding must ship a YAML schema and pass `make dt_binding_check`. Without it, your patch will not be accepted upstream. Without it, your binding can drift silently between board variants and you will not know.
- Why JSON-Schema for DT bindings (vs the old `.txt` files)
- A binding for a custom node, written from scratch, validated
- `make dt_binding_check` and `make dtbs_check` — what each does
- Common errors and how to read them
- **Key Notes:** A binding is the contract between hardware description and driver interpretation. YAML expresses that contract using JSON Schema constraints rather than replacing it with implementation details.

### Chapter 27B — Supplementary: Device Tree for a custom i.MX6ULL board
- Start from `imx6ull.dtsi` and write the board `.dts`
- Add memory, `/chosen`, aliases, UART console, regulators, SD/eMMC, Ethernet, I2C, SPI, LEDs, and keys
- Update the kernel DTS Makefile so the board DTB is built
- Bring up one peripheral at a time and check each driver from the boot log
- Use `dtbs_check` to catch binding mistakes before hardware testing
- **Key Notes:** A board DTS owns external topology, not the SoC register description or driver implementation. Included SoC nodes provide the base that board-specific references refine.

### Chapter 28 — Kernel startup, traced
- `start_kernel()` — read it function-by-function
- `setup_arch()`, `setup_machine_fdt()`, memblock, paging_init, mm_init
- `rest_init()` → `kernel_init` thread → `run_init_process("/sbin/init")`
- `kthreadd`, the idle thread, init's pid 1
- Where `printk` ring buffer lives; how early-boot printk works before serial drivers exist
- **Key Notes:** Architecture entry establishes CPU recognition and the initial address mappings before ordinary kernel C services exist. Failures there may precede a usable console.

### Chapter 29 — Initramfs from scratch
- What an initramfs *is* (cpio archive, not a filesystem image)
- Building a one-binary initramfs: a single statically-linked program that prints "hello" and `reboot()`s
- Then a BusyBox initramfs with a real shell
- Embedding the initramfs in the kernel image vs loading it separately
- The handoff: kernel mounts initramfs as `/`, runs `/init`
- **Key Notes:** An initramfs supplies files before the normal storage-backed root is available. The kernel unpacks a cpio archive, then early user space owns the next boot or recovery decision.

### Chapter 29A — Supplementary: Initramfs as a recovery system
- Turn the Chapter 29 BusyBox initramfs into a small recovery environment
- Add a recovery `/init` with shell, read-only rootfs mount, log collection, and reset/update placeholders
- Boot a raw `initramfs.cpio.gz` with `bootz kernel initrd_addr:initrd_size dtb`
- Add safe update rules: checksum, target confirmation, unmounted partition, and factory-data protection
- Connect recovery selection to U-Boot bootmode, button, bootcount, or failed normal boot
- **Key Notes:** Recovery independence depends on the whole boot path: firmware must still load a working kernel, board DTB and archive. Running from RAM avoids reliance on the main rootfs, not every storage or hardware dependency.

### Chapter 30 — Kernel configuration deep-dive
- `make menuconfig` — but reading the `.config`, not clicking blindly
- The big knobs: `CONFIG_PREEMPT*`, `CONFIG_HZ`, `CONFIG_TICK_ONESHOT`, `CONFIG_NO_HZ`, `CONFIG_HIGH_RES_TIMERS`
- Tracing, debug, lockdep options
- Module vs built-in: when does it matter?
- Generating your own custom `defconfig` and saving it under `arch/arm/configs/`
- **Key Notes:** Kconfig resolves requested options against dependencies and defaults. A hand-edited symbol does not necessarily survive resolution or become compiled code.

### Chapter 30A — Supplementary: Kernel lifecycle — mainline, stable, LTS, vendor BSPs
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
- **Key Notes:** A release tag fixes source identity, while a maintained branch supplies an ongoing stream of changes. A teaching baseline and a supported shipping baseline serve different purposes.

### Chapter 30B — Supplementary: Product kernel configs
- Split kernel configuration into base, development, production, and recovery fragments
- Use `scripts/kconfig/merge_config.sh`, separate `O=` build directories, and `olddefconfig`
- Decide which drivers must be built in and which can be modules
- Use `scripts/diffconfig` and `savedefconfig` before release
- Set `CONFIG_LOCALVERSION` so the board reports the exact kernel flavor
- **Key Notes:** Development, production and recovery kernels share hardware needs but serve different operational roles. A diagnostic interface useful in development is not automatically a production requirement.


---

## PART V — ROOT FILESYSTEM & USER SPACE

### Chapter 31 — A root filesystem, by hand
- The FHS (Filesystem Hierarchy Standard) cheat sheet
- Building BusyBox from source, statically linked
- Creating `/bin`, `/sbin`, `/etc`, `/dev`, `/proc`, `/sys`, `/tmp`, `/var`, `/root`, `/lib`
- A minimal `/etc/inittab`, `/etc/init.d/rcS`, `/etc/fstab`, `/etc/passwd`, `/etc/group`, `/etc/profile`
- Exporting via NFS, mounting from kernel cmdline `root=/dev/nfs`
- **Key Notes:** A rootfs supplies executables, libraries and configuration. Directories such as `/proc`, `/sys` and `/dev` are mount points whose runtime contents are not produced by copying ordinary files.

### Chapter 32 — /proc, /sys, devtmpfs
- `/proc` — the original process FS, now also a kernel-info FS
- Useful files: `/proc/cpuinfo`, `/proc/meminfo`, `/proc/interrupts`, `/proc/iomem`, `/proc/devices`, `/proc/<pid>/maps`, `/proc/<pid>/status`
- `/sys` — the modern device model surface
- `/sys/class/gpio/`, `/sys/bus/i2c/devices/`, `/sys/devices/platform/`
- `devtmpfs` vs static `/dev` vs `mdev` vs `udev`
- **Key Notes:** procfs exposes process and system state, sysfs exposes the device model, and devtmpfs supplies device nodes. Their common file-shaped interface does not give them the same purpose.

### Chapter 33 — Init systems
- BusyBox `init`: minimal, inittab-based
- `sysvinit` / OpenRC: the classical world
- `systemd`: services, sockets, targets, journals — a brief sober tour
- Why an embedded target may not want any of these
- **Key Notes:** PID 1 has system-lifetime responsibilities, including child reaping and shutdown coordination. Running an application directly as init transfers those responsibilities to the application rather than removing them.

### Chapter 34 — libc, dynamic linking, and the loader
- glibc vs musl vs uClibc-ng (size, license, compatibility)
- ELF dynamic linking: PLT, GOT, `LD_LIBRARY_PATH`, `RPATH`
- `ldd`, `readelf -d`, `LD_DEBUG=files`
- `/lib/ld-linux-armhf.so.3` — what it actually does
- Static linking, when to use it on embedded
- **Key Notes:** A dynamically linked ELF declares an interpreter path and needed libraries. The target must provide a compatible loader and dependency set before application startup can succeed.

### Chapter 35 — Buildroot, *after* you can do it by hand
- Why Buildroot exists; what it really automates
- `make menuconfig` for Buildroot
- Reading `output/build/` and `output/target/` — recognizing every step you already did in Ch. 31
- Adding a custom package
- Comparing the generated rootfs against your hand-built one
- **Key Notes:** Buildroot owns the dependency-ordered assembly of selected packages into images. Its configuration describes the intended system rather than a sequence of edits performed on a live target.

### Chapter 35D — Supplementary: Bootable SD and eMMC image layout
- Split storage into boot, rootfs, and data partitions
- Use filesystem labels instead of guessed `/dev/mmcblkXpY` names
- Manually partition and format an SD card once, so the image builder is understandable
- Add `/data` to `/etc/fstab`
- Automate the layout with `genimage`
- **Key Notes:** Boot files, the root filesystem and application data have different owners and update lifetimes. Separate partitions make those boundaries visible but do not by themselves provide rollback.

### Chapter 35I — Supplementary: Boot from SPI NOR flash
- Explain when the Boot ROM can really boot from SPI/QSPI NOR
- Compare block devices with MTD devices
- Design a small SPI NOR partition map for U-Boot, env, kernel, DTB, rootfs, and data
- Add Device Tree fixed partitions
- Build a SquashFS rootfs and flash it with U-Boot `sf update`
- **Key Notes:** SPI NOR offers eraseblock-based storage through MTD, not an eMMC-style block device. Filesystem and update choices must account for erase geometry and limited capacity.

### Chapter 35E — Supplementary: Buildroot product board directory
- Build a product-style `board/<vendor>/<board>/` directory
- Use `rootfs-overlay`, `post-build.sh`, `post-image.sh`, and `genimage.cfg`
- Add kernel and BusyBox config fragments
- Save and rebuild from a product defconfig
- Decide what to commit and what to leave as generated output
- **Key Notes:** A product board directory is the reviewable source of image policy. Generated output is a build result, not the place to preserve product configuration.

### Chapter 35A — Supplementary: Ubuntu-base rootfs as a peer to BusyBox/Buildroot
For projects where binary size is not the constraint but **familiarity is** (engineers used to `apt install` on their dev machines), an Ubuntu-base rootfs gives you a fully-fledged Debian-family userland on the target — `apt`, `bash`, full `coreutils`, glibc. We unpack Ubuntu-base, `chroot` into it under `qemu-user-static` to install packages on the host, then NFS-mount it from the target.
- When to choose this vs BusyBox (size, cold-start) or Buildroot (reproducibility)
- The `chroot` + `qemu-user-static` trick for installing target packages from the host
- DHCP and `apt` on the target
- **Key Notes:** Ubuntu-base trades a small, tightly controlled image for familiar packages and a larger maintenance surface. The choice depends on product storage, memory and update policy, not on whether a shell can start.

### Chapter 35F — Supplementary: Your application as a service
- Write an app that behaves well under an init system
- Add a BusyBox init script with start, stop, and restart
- Add a systemd unit for Ubuntu-base or systemd Buildroot images
- Decide where config, logs, runtime files, and data belong
- Add simple health checks
- **Key Notes:** A service has a lifecycle contract: dependencies, readiness, shutdown, failure handling and ownership of its files. Installing an executable establishes only one part of that contract.

### Chapter 35G — Supplementary: Networking, time, and logging
- Bring up Ethernet manually and with DHCP
- Debug gateway vs DNS failures
- Configure hostname and `/etc/hosts`
- Start NTP and explain why wrong time breaks TLS and package managers
- Configure BusyBox syslog and persistent logs under `/data`
- **Key Notes:** Link state, IP configuration, routing and DNS are separate layers. Success at one layer narrows a diagnosis but does not establish that the next layer works.

### Chapter 35B — Supplementary: Read-only rootfs + overlayfs (the industrial pattern)
An immutable base separates the shipped system from writable runtime state. Tmpfs and persistent overlays have different lifetimes, durability requirements and recovery policies. A read-only mount does not make the complete product immune to power loss.
- Mounting `ext4` with `ro`; what fails (`/etc/resolv.conf`, `/var/run/utmp`, `/tmp`)
- `overlayfs` mount syntax: `lowerdir`, `upperdir`, `workdir`
- `/etc/fstab` for an RO root + writable overlays
- The data-partition split: `/data/` for app data, `/var/log/` for logs
- Power-loss boundaries, application commit policy and storage qualification
- Factory reset as a data-lifecycle decision, not live-overlay deletion
- **Key Notes:** An immutable rootfs separates the shipped system from changing data. Read-only mounting reduces exposure to interrupted writes to that filesystem, but does not make the storage device or the entire product immune to power loss.

### Chapter 35H — Supplementary: Rootfs security basics
- Separate development convenience from release policy
- Lock root login and use SSH keys
- Run the product app as a non-root user
- Review file permissions, setuid files, secrets, and listening services
- Use read-only rootfs and `/data` mount options as part of defense
- **Key Notes:** Security begins with authority: which account owns a service, which files it can change, and which interfaces it exposes. Running everything as root erases useful boundaries.

### Chapter 35C — Supplementary: Container runtimes on embedded (Podman + OCI)
Some products use containers to isolate the application from the base system, so the same base rootfs can host many app updates. We bring up Podman on the i.MX6ULL, run a tiny Alpine container, talk to a host GPIO from inside it, and manage the container with Quadlet.
- Why containers on embedded: app/OS split for OTA, sandboxing, reproducibility
- Podman vs Docker on small devices
- Kernel namespaces, cgroups, and overlayfs requirements
- Bind-mounting `/sys/class/leds` into a container to talk to hardware
- OCI image format; how to build one without Docker on the host

### Appendix — Userspace tooling reference
- One table per tool family (networking, audio, BT, cellular, sensors, debug, …) with both **Ubuntu-base `apt install`** and **Buildroot `BR2_PACKAGE_*`** lines
- "Install everything" cheat sheets (Ubuntu-base one-liner, Buildroot Kconfig fragment)
- Per-Part subsets so a reader doing only Part VI/VII/VIII can install just what they need
- Pitfalls (libgpiod v1↔v2 CLI, missing WiFi firmware, mesh-vs-classic BlueZ, etc.)
- **Key Notes:** Containers package applications separately from the base system, but share its kernel. Application rollback and kernel or bootloader rollback are different update boundaries.


---

## PART VI — DRIVER DEVELOPMENT

> *A driver connects a hardware contract to a Linux subsystem. These chapters follow that boundary through discovery, ownership, execution context, data flow and removal. Listings make the contract inspectable; Key Notes collect its design consequences.*

### Chapter 36 — Your first kernel module
- The Loadable Kernel Module (LKM) build system: `obj-m`, Kbuild, `KDIR`
- `module_init`, `module_exit`, `MODULE_LICENSE`, `MODULE_AUTHOR`
- `printk` log levels, dmesg
- `insmod`, `rmmod`, `lsmod`, `modinfo`, `depmod`, `modprobe`
- Cross-compiling against the kernel tree you built in Ch. 25
- **Key Notes:** A loadable module joins the kernel's address space. Its callbacks have kernel privileges and no process-level fault isolation.

### Chapter 37 — Character device drivers
- The classical chardev pattern
- `register_chrdev_region` / `alloc_chrdev_region`
- `struct cdev` and `cdev_add`
- `struct file_operations`: `open`, `release`, `read`, `write`, `llseek`, `unlocked_ioctl`
- `copy_to_user` / `copy_from_user` — and *why* you can't just memcpy
- A 200-line driver exposing a software FIFO over `/dev/myfifo`
- **Key Notes:** The device number selects a `cdev`, and the VFS dispatches operations through its `file_operations`. The pathname alone does not define device behavior.

### Chapter 38 — Auto device nodes (class + device)
- `class_create`, `device_create` and what udev/mdev do with `/sys/class/.../uevent`
- The uevent protocol, hotplug
- **Key Notes:** `cdev` registration provides operation dispatch, while class/device registration describes the instance in sysfs. Publishing a node before its backing interface is ready creates an access race.

### Chapter 39 — The platform driver + device tree binding
- Why platform drivers replace the old "register a chardev manually" pattern
- `struct platform_driver`, `of_match_table`, `probe`, `remove`
- The bind dance: DT node + driver `compatible` → `probe()` called
- `platform_get_resource`, `devm_ioremap`, `devm_request_irq`
- Adding your driver's DT binding under `Documentation/devicetree/bindings/`
- **Focus:** once this clicks, every kernel subsystem looks the same
- **Key Notes:** Device Tree describes a hardware instance, the driver supplies behavior, and the platform bus matches the two. One driver can bind to several devices with separate private state.

### Chapter 40 — The misc framework (shortcut chardev)
- When `miscdevice` is enough
- A `/dev/hwrng`-style driver in 80 lines
- **Key Notes:** Misc devices share major 10 and obtain an individual minor. The framework reduces registration plumbing without changing the `file_operations` contract.

### Chapter 41 — Concurrency
- The four "lock" families: atomic_t, spinlock, mutex, rwlock + sequence locks
- When to use each (interrupt context vs process context)
- Per-CPU variables
- RCU at an introductory level
- Preemption rules: `preempt_disable`, `local_irq_save`
- Lockdep and how to read its splats
- **Key Notes:** Concurrency depends on access paths, not only CPU count. Syscalls, interrupts, timers, and deferred work can interleave on a single-core system.

### Chapter 42 — Sleeping, waiting, polling
- `wait_queue_head_t`, `wait_event_interruptible`, `wake_up`
- Implementing blocking `read()`
- `poll_wait`, `EPOLL` from the driver side
- `O_NONBLOCK` semantics
- **Key Notes:** A wait queue records interest in a condition. The producer owns state changes and wakeups, while the reader remains responsible for checking whether its condition is satisfied.

### Chapter 43 — Interrupts (top half, bottom half, threaded)
- `request_irq`, `IRQF_*` flags, shared interrupts
- Top half: keep it short, ack the device, schedule deferred work
- Bottom halves: softirq, tasklet (deprecated), workqueue, threaded IRQ
- DT `interrupts` property and the `interrupt-parent` chain
- **Key Notes:** IRQ domains translate controller-specific interrupt descriptions into the virtual IRQ used by a driver. A DT hardware number is not a portable `request_irq` argument.

### Chapter 44 — The GPIO subsystem
- The old `gpio_request`/`gpio_set_value` interface vs the new `gpiod_*` interface
- pinctrl bindings revisited
- Userspace: `/sys/class/gpio` (deprecated) vs `gpiochipN` + `libgpiod`
- **Key Notes:** Pinctrl owns mux and pad configuration, while GPIO consumers own direction and logical value through descriptors. Successful descriptor acquisition does not establish correct board wiring.

### Chapter 45 — Input subsystem (button driver)
- `input_dev`, `input_event`, `EV_KEY`, `EV_ABS`, `input_register_device`
- `/dev/input/eventN` and `evtest`
- **Key Notes:** An input driver translates device-specific observations into declared type/code/value events. Evdev and higher-level user-space consumers own delivery and interpretation.

### Chapter 46 — I²C drivers
- Master controller (i.MX6ULL has 4 × I²C) vs client driver split
- The i.MX I²C controller (I2C1..4) register-level overview
- Writing a *client* driver for an EEPROM or sensor (e.g., AP3216 ambient light on the Point Atom board)
- DT binding for I²C devices
- Using `i2c-tools` (`i2cdetect`, `i2cdump`, `i2cset`, `i2cget`) to validate
- **Key Notes:** The adapter owns controller operation, the client identifies one bus address, and the chip driver owns device semantics. A DT client description is not proof of a responding chip.

### Chapter 47 — SPI drivers
- SPI subsystem, master + slave
- ECSPI controller on i.MX6ULL
- Writing a driver for an SPI flash or ADC
- `spidev` for quick userspace prototyping
- **Key Notes:** The SPI controller owns bus scheduling and signaling, while each `spi_device` carries chip-select and configuration constraints. The chip driver owns command framing and interpretation.

### Chapter 48 — PWM and RTC
- PWM framework, `pwm_chip`, sysfs `/sys/class/pwm/`
- RTC framework: `rtc_class_ops`, `hwclock`, NTP integration
- **Key Notes:** A PWM provider implements hardware timing, while a consumer owns the signal's purpose. Backlight, fan, and beeper frameworks add role-specific policy above raw period and duty cycle.

### Chapter 49 — IIO (Industrial I/O) for ADC and sensors
- Why IIO replaced ad-hoc sensor drivers
- Channels, triggers, buffers
- A driver for the on-chip ADC1 of the i.MX6ULL
- Reading from `/sys/bus/iio/devices/iio:device0/in_voltage0_raw`
- **Key Notes:** Channels describe measurable quantities and their attributes. The sensor driver supplies acquisition and conversion semantics, while IIO supplies a common user-space interface.

### Chapter 50 — regmap
- The pattern: every device driver was duplicating "read/modify/write a register" code
- `regmap_init_mmio`, `regmap_init_i2c`, `regmap_init_spi`
- `regmap_update_bits`, cache types, debugfs integration
- Refactor an earlier chapter's driver to use regmap
- **Key Notes:** Regmap separates register semantics from bus encoding. Address width, value width, endianness, and command flags must describe the actual chip protocol.

### Chapter 51 — DMA
- The DMA-API: `dma_alloc_coherent` vs streaming `dma_map_single`
- Cache coherency: why the kernel cares about direction and ownership
- i.MX6ULL SDMA controller overview
- A DMA-driven UART example (or audio DMA preview)
- **Key Notes:** The DMA provider owns the controller, while a consumer owns transfer intent, buffers, and completion handling. A channel request must match the peripheral's routing and capabilities.

### Chapter 51A — Supplementary: Watchdog driver and brown-out resilience
No product ships without one. The i.MX6ULL `WDOG1/WDOG2` modules generate a system reset if not "kicked" within a programmable window. We write the kernel driver, plumb the user-space daemon (`systemd-watchdog` or `busybox watchdog`), and design the application-level kick policy.
- The kernel `watchdog` framework, `struct watchdog_device`, `wdog_ops`
- `/dev/watchdog` and the `ioctl` interface
- Window timing: too-fast kicks are as bad as too-slow
- Boot-time vs runtime: when does the WDOG arm?
- Pre-timeout warnings for graceful shutdown
- **Key Notes:** A hardware watchdog provides a reset path that is less dependent on kernel scheduling than a software timer. Its actual clock, power, and reset dependencies bound its independence.

### Chapter 51B — Supplementary: Power management — runtime PM, suspend/resume, DVFS
Battery-powered or thermal-constrained products demand real PM. The Linux PM core supports four orthogonal mechanisms: runtime PM (per-device idle), system suspend (whole-board sleep), DVFS (frequency/voltage scaling), and CPU idle (low-power C-states).
- The PM-runtime callbacks: `runtime_suspend`, `runtime_resume`, `runtime_idle`
- `pm_runtime_get_sync` / `pm_runtime_put` discipline in drivers
- System sleep states: `freeze`, `standby`, `mem`, `disk` — what's implemented on i.MX6ULL
- DVFS: `cpufreq` governors (ondemand, schedutil, conservative)
- The CPU idle subsystem (`cpuidle`); WFI as the C1 state
- `tickless` (`CONFIG_NO_HZ_IDLE`) for power
- **Key Notes:** Runtime PM follows a device's activity, DVFS changes operating points under load, and system sleep coordinates the whole platform. These are distinct policies with different dependency and wakeup requirements.

### Chapter 52 — Network driver (FEC + KSZ8081 PHY)
- The netdev model: `struct net_device`, `ndo_*` ops, NAPI
- The FEC (Fast Ethernet Controller) on i.MX6ULL
- The PHY subsystem and MDIO
- DT bindings for ethernet
- Bringing the interface up, running `ping`, `iperf`, `tcpdump`
- **Key Notes:** Ethernet divides responsibility between the MAC, PHY and Linux network stack. MDIO manages PHY state, while RMII carries the frame data and clock relationship.

### Chapter 52A — Supplementary: PREEMPT_RT — real-time Linux as a full chapter
For motion control, audio, robotics, industrial protocols, mainline Linux's PREEMPT_RT patchset turns the kernel into a deterministic real-time kernel without giving up the Linux API. Since v6.12 most of PREEMPT_RT has been merged into mainline; the rest is in flight.
- What "real-time" means precisely (worst-case latency, not "fast")
- The PREEMPT_RT design: threaded IRQs, sleeping spinlocks, rt_mutex with priority inheritance, ftrace-anchored measurement
- Building a PREEMPT_RT kernel on i.MX6ULL
- `cyclictest` — the standard latency benchmark
- Affinity, isolation (`isolcpus=`), and the `SCHED_FIFO`/`SCHED_DEADLINE` schedulers
- Tuning: disable CPU-idle deeper states, pin IRQs, lock memory with `mlockall`
- What still cannot meet hard-RT requirements on a Cortex-A7 single-core
- **Key Notes:** Real-time design concerns deadlines and worst-case interference, not average throughput. PREEMPT_RT reduces sources of kernel scheduling latency but does not establish a universal deadline guarantee.

### Chapter 53 — Sound (ALSA / ASoC)
- The "Sound Open Architecture" stack
- ASoC: machine driver + codec driver + platform driver
- SAI controller on i.MX6ULL + WM8960 codec (typical Point Atom config)
- `aplay`, `arecord`, `alsamixer`
- **Key Notes:** ASoC separates the CPU audio interface, codec and board-specific connection. The machine description joins reusable drivers rather than replacing their responsibilities.

### Chapter 54 — LCD framebuffer and DRM
- The eLCDIF controller
- Legacy fbdev (`/dev/fb0`) vs modern DRM/KMS (`/dev/dri/card0`)
- Writing pixels from user space; testing with `fbset`, `modetest`
- Touchscreen integration (GT9147 typical Point Atom)
- **Key Notes:** DRM/KMS separates framebuffer storage, scanout, mode selection and output connections. Legacy fbdev exposure does not describe the whole display pipeline.

### Chapter 54A — Supplementary: MTD / UBI / UBIFS for raw NAND
If your product flashes raw NAND (not eMMC), you need the MTD subsystem under the kernel and UBI/UBIFS on top for wear-leveling and bad-block management.
- MTD model: `struct mtd_info`, `mtd_read/write/erase`
- The NAND subsystem (`nand_chip`) on top of MTD
- Bad-block management (BBT, OOB layout)
- UBI: volumes, wear-leveling, attach/detach
- UBIFS: a journaling FS on UBI
- `mtdinfo`, `ubinfo`, `ubiformat`, `ubinize`
- **Key Notes:** MTD exposes raw flash geometry and operations, UBI manages logical eraseblocks and wear, and UBIFS provides a filesystem above UBI. These layers solve different problems.

### Chapter 54B — Supplementary: V4L2 + GStreamer for camera input (CSI)
The i.MX6ULL CSI is paired with an OV5640 (typical) or OV2640 sensor. V4L2 (Video4Linux 2) is the kernel framework; GStreamer is the user-space pipeline glue.
- V4L2 model: `struct v4l2_device`, `struct video_device`, `v4l2_ioctl_ops`
- The i.MX6ULL `imx-pxp` and `imx-csi` drivers
- A user-space `v4l2-ctl` capture: `v4l2-ctl --stream-mmap --stream-to=...`
- GStreamer pipeline: `v4l2src ! videoconvert ! kmssink` → fullscreen camera
- The bayer/YUV/RGB conversion path
- Encoding to JPEG/H.264 on i.MX6ULL (none in HW; software encoder via `libjpeg`/`x264`)
- **Key Notes:** The capture pipeline joins sensor, interface and memory buffers through V4L2 and, where applicable, the media graph. GStreamer consumes that exposed stream in user space.

### Chapter 55 — USB gadget
- USB host vs device modes; OTG role detection
- `libcomposite` and ConfigFS-based gadgets
- A "USB serial" and a "USB mass storage" gadget walkthrough
- **Key Notes:** A USB gadget is the device side of a connection, not a USB host. The controller role, connector wiring and VBUS handling must support that role.

### Chapter 55A — Supplementary: Kernel timers and high-resolution timers (hrtimers)
Three timer APIs in the kernel: legacy `timer_list` (jiffies-based, ms resolution), `delayed_work` (workqueue-driven), and `hrtimer` (sub-µs, the modern default for new code). When to use which; how each is implemented under the hood; how the tick subsystem multiplexes many timers on one hardware event.
- `mod_timer`, `del_timer_sync`, the `timer_list.function` callback
- `hrtimer_init`, `hrtimer_start`, `HRTIMER_MODE_REL` vs `_ABS`, `_PINNED`
- `timer_setup` (the modern, type-safe API)
- **Key Notes:** Kernel timers schedule callbacks, not private threads. Their execution context determines which operations are legal, while workqueues provide a place for work that may sleep.

### Chapter 55B — Supplementary: Asynchronous notification (SIGIO / fasync)
The fourth I/O model after blocking/non-blocking/poll: the driver delivers a `SIGIO` to a registered user-space process when data is ready, so the process is "informed" without ever calling `read()`. `fasync_helper`, `kill_fasync`, the `F_SETOWN`/`F_SETFL O_ASYNC` user-space dance.
- When SIGIO matters: legacy code, signal-driven simple loops, low-latency without busy-poll
- Why epoll/io_uring have mostly replaced it for new code, and why drivers still ship it
- **Key Notes:** SIGIO is a notification that device state may need attention, not the data itself. The application's queue or read interface remains the source of events.

### Chapter 55C — Supplementary: CAN bus and FlexCAN
Industrial automation runs on CAN. The i.MX6ULL has two **FlexCAN** controllers. The Linux SocketCAN subsystem treats CAN like a network interface: `ip link set can0 up type can bitrate 500000`. Then `cansend`, `candump`, `can-utils`.
- The FlexCAN controller register map and message-buffer model
- SocketCAN: `PF_CAN`, `SOCK_RAW`, `struct can_frame`
- `iproute2` CAN extensions; `can-utils`
- ISO-TP, CAN-FD — what i.MX6ULL supports and what it doesn't
- **Key Notes:** SocketCAN exposes CAN through Linux networking while FlexCAN owns controller behavior. The external transceiver and bus wiring remain essential physical dependencies.

### Chapter 55D — Supplementary: Block device drivers
Char devices are sequential; block devices are random-access in fixed-size sectors. The block-I/O layer multiplexes requests from many filesystems onto one device with elevator/scheduling policies.
- `struct block_device`, `struct gendisk`, `struct block_device_operations`
- The `request_queue`, `make_request_fn`, modern `blk_mq` multi-queue
- A 4 MB RAM-disk block driver in < 200 lines
- How `/dev/mmcblk0` and `/dev/sda` look under the hood
- **Key Notes:** The block layer describes sector-oriented I/O through bios, requests and queues. A block driver must honor offsets, lengths and completion semantics rather than act like an unstructured byte stream.

### Chapter 55E — Supplementary: WIFI — wpa_supplicant, USB and SDIO dongles
Connecting an i.MX6ULL to Wi-Fi in 2026 is rarely an in-house driver job — you pick a chip with mainline support and stand up `wpa_supplicant`. We walk an RTL8188EUS USB Wi-Fi dongle (cfg80211) and an RTL8189FS SDIO module (vendor staging tree) end-to-end.
- Kernel: `CONFIG_CFG80211`, `CONFIG_WIRELESS_EXT`, `CONFIG_RTL8XXXU`
- Firmware blobs in `/lib/firmware/`
- `wpa_supplicant.conf`, WPA2-PSK, hidden SSIDs, EAP-PEAP
- `wpa_cli` and the `D-Bus` interface
- Diagnosing "no SSID found": antenna, country code, channel-12/13, regulatory domain
- **Key Notes:** Wi-Fi spans bus discovery, chip firmware, kernel wireless interfaces, authentication and IP networking. Failure at one layer should not be diagnosed as a failure of the whole stack.

### Chapter 55F — Supplementary: Cellular modems (PPP, ECM/NCM, GNSS)
Quectel EC20-style modems present themselves as USB composite devices: PPP serial, RNDIS/ECM data, NMEA GNSS. We cover all three modes, plus `quectel-CM` and `qmi_wwan` for the QMI-based path.
- USB option driver, vendor/product IDs, the `option_ids[]` table in `drivers/usb/serial/option.c`
- PPP path: `pppd` chat script, APN, MTU
- ECM/NCM: a virtual Ethernet over USB; `usb0`
- GNSS: `/dev/ttyUSB1` NMEA stream → `gpsd` → `gpsmon`
- **Key Notes:** Cellular integration separates modem control, the data interface and host network configuration. QMI, MBIM, Ethernet-like modes and PPP imply different drivers and management paths.

### Chapter 55G — Supplementary: Multi-touch — MT-A, MT-B protocols, GT911
The Linux input subsystem evolved two multi-touch protocols: **Type A** (per-frame, packed) and **Type B** (per-slot, persistent). Most modern panels use Type B. We bring up a Goodix **GT911** capacitive touch controller (5-point), the typical pairing for the Point Atom MINI's optional LCD.
- I²C wiring + interrupt + reset of GT911
- `input_mt_init_slots`, `input_mt_slot`, `input_report_abs(ABS_MT_POSITION_X/Y)`
- `evtest` and how to read a multi-touch event stream
- `tslib` user-space library for legacy single-touch panels
- **Key Notes:** MT-B reports contacts through slots and tracking IDs. Finger lifetime is different from the number of coordinate samples received.

### Chapter 55H — Supplementary: RGB-to-HDMI via sii902x
The i.MX6ULL has no native HDMI. An external parallel-RGB-to-HDMI bridge illustrates the DRM bridge model, board wiring and mode constraints shared by controller, bridge and sink.
- The bridge chip's I²C control path vs. its parallel-RGB data path
- `drm/bridge` model in the kernel; `drm_bridge_add`
- EDID reading; mode selection from a list
- **Key Notes:** A DRM bridge transforms one display interface into another between the controller and connector. The i.MX6ULL has no native HDMI, so the external bridge and its wiring are part of the design.

### Chapter 55I — Supplementary: Rust-for-Linux — first kernel module
Since Linux 6.1, Rust is a supported language for kernel modules. As of 2026 the support is still gated to a small set of subsystems but is growing fast. We write our Chapter 36 hello-LKM in Rust, as a sidebar / supplemental experiment — not because we recommend Rust for production embedded yet, but because the reader will see it land in their next kernel update.
- Why Rust in the kernel (memory safety, type-state)
- `rust/` directory tour; how the build picks up Rust source
- `kernel::prelude::*`, `module!{}` macro
- Compare side-by-side with the C version from Chapter 36
- What's stable, what's nightly, what's blocked
- **Key Notes:** Rust changes how memory ownership and some concurrency rules are expressed, but a driver still needs a correct hardware and kernel-interface design.


---

## PART VII — DEVICE COOKBOOK

> *Part VI taught you the kernel's driver frameworks with one good example each. This Part is the reference: for each common device class, two or three real chips compared side-by-side, with schematics, DT bindings, driver code or kernel-driver enablement, user-space access, and the pitfalls specific to each chip.*
>
> *The device chapters are independent design references. Compare the physical measurement or output, its electrical and timing requirements, Linux support and the application interface. Schematics and listings explain those relationships without requiring a separate project for every chip.*

## Group A — Storage devices

### Chapter 64 — QSPI NOR flash
- **Chips:** Winbond W25Q128 / W25Q64; Macronix MX25L256; Micron MT25Q. Trade-offs (size, speed, erase granularity, security features).
- The i.MX6ULL QSPI controller and its limits
- DT bindings for `spi-nor`; `m25p80`; the `jedec,spi-nor` compatible
- MTD partitions for u-boot env, kernel, dtb, rootfs slot A/B
- Erasing and writing from user-space: `mtd-utils` (`flash_erase`, `nandwrite`, `flashcp`)
- XIP from QSPI — when it makes sense, when it doesn't
- **Pitfalls:** read-only mode after lockdown; quad-mode vs single-mode performance trap
- **Key Notes:** NOR programming, erase and read are different operations with different alignment and timing rules. Write-enable and bounded busy polling belong to the device state machine, not just to a convenient API.

### Chapter 65 — I²C / SPI EEPROM
- **Chips:** Microchip AT24C02/32/256/512 (I²C); AT25-series (SPI); 25LCxx (SPI).
- The `at24` kernel driver and what its DT properties really do (`pagesize`, `read-only`, `wp-gpios`)
- The `nvmem` framework: where EEPROM cells become typed kernel-side accessors
- Writing the MAC address from EEPROM into the FEC at probe time
- Wear: page-write counting, the "spread your writes" pattern
- **Pitfalls:** I²C addressing scheme variants; the 256-byte boundary "rollover" bug
- **Key Notes:** EEPROM is useful for small persistent records such as identity and calibration. Its byte-oriented interface still has page-program, completion and endurance constraints.

### Chapter 66 — SD card and eMMC deep dive
- The MMC subsystem; SDIO is the same machinery (Ch 91 will reuse it)
- Speed modes: DS, HS, HS200, HS400 — what your eMMC and your i.MX SDHC support
- CMD23 vs CMD12 multi-block read terminators
- eMMC partition table: boot partitions, RPMB, GP areas
- Wear-levelling: what eMMC firmware does, what UBI does, what neither does
- TRIM/discard for eMMC vs SD
- **Key Notes:** The MMC core manages card protocols, the host driver manages the controller, and the block layer exposes storage requests. A failure can occur at any of these boundaries.

## Group B — Environmental sensors

### Chapter 67 — Temperature / humidity / pressure
- **Chips:** Bosch BME280 (T/H/P I²C+SPI); Sensirion SHT3x (T/H I²C, lab-grade); ASAir AHT20 (T/H I²C, cheap).
- IIO drivers for each; how user-space reads via `/sys/bus/iio/devices/`
- Calibration registers in BME280; why the raw reading isn't the temperature
- Polling vs trigger-driven sampling
- Time-averaging in user-space: simple moving average vs exponential
- **Pitfalls:** self-heating in BME280 (the device's own current warms its sensor); the "after power-on wait 2 ms" SHT3x trap
- **Key Notes:** Raw sensor counts become useful measurements only through the correct scale or compensation path. BME280 calibration coefficients belong to the individual chip.

### Chapter 68 — Light & color sensors
- **Chips:** Rohm BH1750 (ambient lux, I²C); AMS TSL2561 (broad-band + IR-channel, I²C); Vishay VEML7700 (low-power lux).
- IIO drivers, `in_illuminance_input` interpretation
- The "logarithmic eye" — what lux means and when it lies
- **Bonus:** AMS TCS34725 (RGB color sensor) and Avago APDS-9960 (RGB + gesture); driver and DT included
- **Pitfalls:** TSL2561's IR-saturation regime; lens / window choice on enclosure
- **Key Notes:** Light sensors do not all observe the same spectral response. Lux conversion, color channels and infrared rejection are device-specific design choices.

### Chapter 69 — Air quality, gas, particulate matter
- **Chips:** Sensirion SCD30 (CO₂ NDIR, I²C); AMS CCS811 (eCO₂/TVOC, I²C); Plantower PMS5003 (PM1/2.5/10, UART); Nova SDS011 (PM2.5/10, UART); MQ-x analog series + ADC.
- Why "eCO₂" is *not* CO₂ (CCS811 estimates from VOCs and resistance drift)
- NDIR true-CO₂ measurement (SCD30); cost vs accuracy
- Laser-scattering PM sensors; airflow control via fan PWM
- The 24-hour warm-up problem with CCS811
- **Pitfalls:** MQ-x cross-sensitivity (most "MQ-2 = LPG" claims are wrong); PM-sensor fan failure detection
- **Key Notes:** NDIR CO2, metal-oxide gas response and optical particle sensing measure different quantities. An inferred eCO2 value must not be presented as a direct CO2 measurement.

## Group C — Motion sensors

### Chapter 70 — I²C IMUs
- **Chips:** InvenSense MPU6050 (6-axis, classic); MPU9250 (9-axis with mag); InvenSense ICM-20948 (newer 9-axis).
- The IIO trigger/buffer mechanism for 6-/9-axis IMUs at 1000 Hz
- DMP firmware blob in MPU6050 — what it gives you (quaternions), what it costs (closed-source, less control)
- The magnetometer-as-slave-I²C-master quirk in MPU9250
- Tilt-compensated heading; sensor fusion via Madgwick filter in user-space
- **Pitfalls:** stale I²C addresses (0x68/0x69); gyro bias drift after temp changes
- **Key Notes:** An IIO trigger and buffer decouple capture from user-space reads. Channel layout, scale and timestamps form the sample interface consumed by later processing.

### Chapter 71 — SPI IMUs (high-rate / low-noise)
- **Chips:** ST LSM6DSO (6-axis); InvenSense ICM-42688 (high-rate, low-noise); Analog Devices ADXL345 (3-axis accel only).
- Why SPI for IMUs above ~400 Hz
- ICM-42688's FIFO and watermark-IRQ — sampling thousands of points per second efficiently
- ODR / range / filter settings
- **Pitfalls:** SPI mode 3 vs mode 0 confusion; ODR vs filter-cutoff mismatch
- **Key Notes:** A FIFO watermark batches samples to reduce interrupt and bus overhead. Larger batches also increase delivery latency and the amount of data at risk during a stall.

## Group D — Position & distance

### Chapter 72 — Distance & proximity
- **Chips:** STMicro VL53L0X (ToF laser, I²C); VL53L1X (longer range); HC-SR04 (ultrasonic GPIO); Sharp GP2Y0A (IR analog).
- The VL53L0X firmware-loading dance
- ToF lighting/glass surface failure modes
- HC-SR04 vs GPIO timing — why this is hard on Linux without a high-precision timer or PRU
- **Pitfalls:** VL53L0X bus collisions (I²C address conflicts); HC-SR04 +5 V level-shifting
- **Key Notes:** Distance sensors use different physical mechanisms, so target shape, ambient conditions and range affect them differently. Software cannot make their limitations interchangeable.

### Chapter 73 — Magnetometer / compass
- **Chips:** Honeywell HMC5883L (I²C, common but EOL); QST QMC5883L (cheap clone); Memsic MMC5983MA (newer, lower noise).
- Hard-iron and soft-iron calibration; why your compass points 23° wrong from the start
- IIO `magn_x/y/z` output and the `scale` attribute
- **Pitfalls:** mounting the magnetometer near a buck regulator destroys readings
- **Key Notes:** A magnetometer measures a field vector, not an already-correct compass heading. Scale, axis orientation and calibration belong in the interpretation path.

### Chapter 74 — Hall-effect & rotary position sensors
- **Chips:** AMS AS5048A (magnetic rotary, SPI/I²C); Allegro A1324 (linear Hall analog); Infineon TLE5012 (high-rate angular sensor).
- Off-axis vs on-axis sensor placement
- The IIO `angl` channel and absolute-position rotary encoders
- High-rate angular sampling for motor commutation
- **Pitfalls:** magnet-distance sensitivity (1 mm changes everything); diametric vs axial magnets
- **Key Notes:** Rotary magnetic sensing depends on magnet type, alignment and field strength as well as electronics. Mechanical geometry is part of the measurement design.

## Group E — Power & current

### Chapter 75 — Current and power monitoring
- **Chips:** TI INA219 (low-side, I²C); INA226 (improved, calibration); INA3221 (3-channel); Allegro ACS712 (Hall analog).
- Shunt selection: heat, accuracy, layout
- INA226 calibration register — why "current_lsb = max_current / 32768"
- 3-rail simultaneous monitoring via INA3221
- **Pitfalls:** shared-ground violations; the "ACS712 zero point isn't 2.5 V" calibration
- **Key Notes:** The shunt, analog input range and calibration setting define the current measurement. Digital resolution alone does not determine useful accuracy.

### Chapter 76 — Battery fuel gauge + charger
- **Chips:** Maxim MAX17048 (1-cell fuel gauge, I²C); TI BQ27441-G1; TP4056 (cheap charger); MCP73833; TI BQ24074 (path-managed charger).
- The battery-empty problem and SoC (state-of-charge) estimation
- Charger thermal regulation and JEITA temperature profiles
- The `power_supply_class` kernel framework; `/sys/class/power_supply/`
- **Pitfalls:** TP4056 mass-production cells without temperature monitoring; SoC drift over months
- **Key Notes:** Fuel estimation, charging, cell protection and power-path management are separate responsibilities. A Linux battery percentage is not a charging-safety mechanism.

## Group F — Specialty sensors

### Chapter 77 — 1-Wire sensors
- **Chips:** Maxim DS18B20 (digital thermometer, 1-Wire); DHT11 / DHT22 (single-wire T/H, *not* true 1-Wire); DS2480B (1-Wire master).
- The kernel `w1` subsystem and its slave drivers
- Why DHT11/22 is a timing-critical mess on a non-RT Linux (and why dedicated MCU helper is sometimes the answer)
- Parasitic-power mode for DS18B20
- **Pitfalls:** the "USB-Serial DS9097 emulator does the parity tricks for you" pattern
- **Key Notes:** Maxim 1-Wire and the DHT22's single-signal protocol are not the same interface. Similar wiring does not imply compatible timing or drivers.

### Chapter 78 — MEMS microphones (I²S)
- **Chips:** InvenSense INMP441 (I²S MEMS); ICS-43434 (lower noise); SPH0645 (similar).
- ASoC DAI for I²S microphones; sampling via `arecord`
- Stereo via two mono mics; beamforming basics
- **Pitfalls:** WS line ringing on long cables; PDM vs I²S confusion
- **Key Notes:** An I2S microphone supplies digital samples through a clocked audio interface. ASoC joins that interface to the CPU DAI and DMA path without inventing a register-controlled codec.

### Chapter 79 — Health sensors (HR / SpO2)
- **Chips:** Maxim MAX30100 (basic); MAX30102 (improved, smaller); MAX30105 (with particle-sensing channel).
- PPG (photoplethysmography) raw signal, IR vs red channel
- Heart-rate extraction in user-space; SpO2 calibration constants
- **Pitfalls:** motion artifacts (this is why a Fitbit's HR is noisy when you walk); SpO2 accuracy claims
- **Key Notes:** The sensor supplies optical samples, while signal processing estimates pulse-related quantities. Raw red and infrared counts are not heart rate or oxygen saturation.

## Group G — Analog conversion & clock generation

### Chapter 80 — External ADCs
- **Chips:** TI ADS1115 (16-bit I²C); ADS1256 (24-bit SPI low-noise); Microchip MCP3008 (10-bit 8-ch SPI cheap); Analog Devices AD7606 (16-bit 8-ch parallel sampling, true simultaneous).
- IIO drivers; sample rate vs ENOB trade-offs
- AD7606's true-simultaneous sampling for power-quality / vibration
- Ratiometric measurements (load cell, RTD)
- **Pitfalls:** input filter loading; reference-voltage stability
- **Key Notes:** Resolution, conversion rate, input range and simultaneous sampling are independent selection criteria. A larger nominal bit count does not ensure more useful information.

### Chapter 81 — External DACs + clock generators
- **Chips:** Microchip MCP4725 (12-bit I²C DAC); Analog Devices AD5663 (16-bit SPI DAC); SiLabs Si5351 (programmable 3-output clock generator); CDCE9xx series.
- IIO `out_voltage*` for DACs
- Si5351 — generating arbitrary clocks for SDR or for chip evaluation
- The kernel `clk` framework integration with external clock chips
- **Pitfalls:** PLL closed-loop stability; Si5351's "frequency = output * 2^N / M" config nightmare
- **Key Notes:** A DAC is an analog-output provider, while a clock generator is a clock provider. They share a control bus but expose different contracts to Linux consumers.

## Group H — Displays

### Chapter 82 — RGB parallel LCD on LCDIF
- **Panels:** ATK4384 (4.3" 480×272); ATK7016 (7" 1024×600); ATK10261 (10.1" 1280×800).
- The DPI / RGB-parallel timing model: pixel clock, hsync, vsync, porches
- `panel-simple` and how to add a custom panel
- DRM/KMS basics for our case; the `imx-lcdif` driver
- Backlight via PWM + `pwm_bl`
- **Pitfalls:** pixel-clock too fast → tearing; reversed RGB swap on the connector
- **Key Notes:** A parallel RGB panel consumes a continuously timed pixel stream from LCDIF. Active pixels, blanking intervals and polarities must agree with its electrical specification.

### Chapter 83 — SPI LCD
- **Panels:** ST7789 (240×320, 16-bit/18-bit color); ILI9341 (320×240); ILI9488 (320×480).
- mainline `panel-mipi-dbi` driver + DRM tiny architecture
- fbtft legacy and why we don't use it for new designs
- Tearing-effect output and synchronized updates
- **Pitfalls:** SPI clock ceiling vs panel refresh; backlight-PWM bleed
- **Key Notes:** An SPI display controller stores pixels and refreshes its glass independently. The host updates controller memory rather than generating every raster timing edge.

### Chapter 84 — QSPI LCD
- **Panels:** GC9D01, ST77916, Sitronix SF055A; round LCDs popular for smart watches
- Quad-SPI mode in the i.MX6ULL QSPI controller
- The high-bandwidth bytes-per-frame budget
- mipi-dbi-spi quad-mode driver
- **Pitfalls:** quad mode timing margins; data-order swap
- **Key Notes:** Quad data lanes can reduce pixel-transfer time, but command phases, overhead and refresh synchronization still affect usable frame rate.

### Chapter 85 — OLED & e-paper
- **Panels:** SSD1306, SH1106 (small OLED I²C/SPI); SSD1322 (large yellow OLED); SSD1680 (2.9" e-paper); IT8951 (large e-paper controller).
- `ssd1307fb` legacy framebuffer driver; `repaper` (e-paper DRM driver)
- e-paper refresh modes: full vs partial; ghosting
- **Pitfalls:** OLED burn-in; e-paper partial-refresh ghost mitigation
- **Key Notes:** OLED and e-paper have different refresh architectures. OLED updates controller memory for an active display, while e-paper applies a panel-specific waveform to change a retained image.

### Chapter 86 — Touch input ICs
- **Chips:** Vishay TTP223 (single-key cap, GPIO output); NXP MPR121 (12-key cap, I²C); XPT2046 (4-wire resistive touch, SPI).
- Adding capacitive touch buttons to a Linux input device via `gpio-keys`
- MPR121 IIR baseline tracking; setting touch/release thresholds
- 4-wire resistive touch + ADS7846/XPT2046 kernel driver; calibration via `xinput_calibrator`
- Compare with GT911 multi-touch (covered in Ch 55G — separate chip class)
- **Pitfalls:** XPT2046's interrupt-pin pulldown; resistive panels' temperature drift
- **Key Notes:** A capacitive button, multi-electrode touch controller and resistive panel expose different signals. The input subsystem can unify events without erasing their physical differences.

## Group I — Cameras

### Chapter 87 — Parallel CSI cameras
- **Sensors:** OmniVision OV7725 (0.3 MP); OV5640 (5 MP, parallel mode); OV2640 (2 MP); GalaxyCore GC2145 (2 MP).
- The i.MX6ULL parallel CSI (no MIPI-CSI on this SoC)
- V4L2 sensor sub-device model
- Sensor-side: PLL, clocks, exposure, gain, white balance, autofocus (OV5640)
- IPU/CSI capture pipeline
- **Pitfalls:** the 5 MP "still mode" of OV5640 vs streaming; FOV vs lens choice
- **Key Notes:** A parallel camera has a control path over I2C and a pixel path into CSI. A sensor probe proves only the first of those boundaries.

### Chapter 88 — USB UVC cameras
- The `uvcvideo` driver; what works mainstream, what doesn't
- Bandwidth budgeting on USB 2.0 (480 Mbps theoretical; ~30 MB/s practical) — implications for resolution × frame rate
- MJPEG vs YUYV vs H.264 modes
- **Pitfalls:** bandwidth contention with USB WiFi or USB Ethernet; non-UVC "drivers needed" cameras
- **Key Notes:** UVC describes a class-based control and streaming interface. Reusing a class driver reduces integration work but does not remove device quirks or mode constraints.

## Group J — Audio devices

### Chapter 89 — I²S audio codecs
- **Chips:** Cirrus WM8960 (used on many i.MX boards); SGTL5000 (NXP); Everest ES8388 (cheap, ESP32 favourite); TI TLV320AIC3104; Realtek ALC5640.
- ASoC machine + codec + cpu-DAI triplet (referenced in Ch 53)
- Differences: built-in DAC quality, PGA capability, mic-preamp
- Headphone-jack detection
- **Pitfalls:** master/slave clock-mode mismatch with i.MX SSI; sample-rate clock-derivation
- **Key Notes:** A codec driver joins register control, digital audio format and analog routing. The board's machine description connects it to the CPU audio interface.

### Chapter 90 — Digital class-D amplifiers
- **Chips:** TI TAS5805M (I²C-controlled DSP amp); Maxim MAX98357A (pure I²S, no I²C); TI PCM5102A (audio DAC + headphone).
- The "amp without a codec" pattern: send raw I²S, amp does the rest
- TAS5805M's DSP coefficients (EQ, compression, dynamic-range control)
- The Bluetooth-speaker product pattern: A2DP source → I²S → MAX98357A
- **Pitfalls:** ground-loop hum in class-D speakers; TAS5805M's I²C dance during startup
- **Key Notes:** A digital amplifier can accept I2S without offering a register interface. Linux still needs a component and DAI description to connect the audio path.

## Group K — WiFi modules

### Chapter 91 — SDIO WiFi
- **Modules:** AP6212 (Broadcom-based, used on Point Atom boards); Realtek RTL8189FTV; Marvell SD8801.
- The `brcmfmac` driver for Broadcom; `rtl8xxxu` and out-of-tree `rtl8189es`
- Firmware loading and per-board NVRAM file
- SDIO-WiFi clock and pin signal-integrity issues
- **Pitfalls:** AP6212 + Realtek firmware blob version mismatch; NVRAM regulatory-domain
- **Key Notes:** SDIO discovery is a transport milestone before Wi-Fi firmware, calibration and authentication can work. Each stage provides different diagnostic evidence.

### Chapter 92 — USB WiFi
- **Modules:** Realtek RTL8188EUS (cheap dongles); MediaTek MT7601; Ralink RT5370.
- `rtl8xxxu` (mainline) vs out-of-tree `rtl8188eus` (better)
- Driver kernel-version compatibility hell
- Bandwidth contention vs USB Camera
- **Pitfalls:** out-of-tree DKMS pain; ralink stale signal
- **Key Notes:** USB removes much board-specific bus wiring but does not remove firmware, driver or radio-policy dependencies.

### Chapter 93 — Hosted WiFi via ESP32 / ESP8266
- **Modules:** ESP32 (esp-hosted firmware); ESP8266 (AT-command firmware).
- The `esp-hosted` driver: SPI/UART transport, Linux sees a normal `wlan0`
- AT-command mode: ESP as a TCP/IP offload engine
- When this beats SDIO: legacy SoCs without SDIO, MCU+Linux co-existence
- **Pitfalls:** AT-command flow control; esp-hosted firmware version pinning
- **Key Notes:** Hosted networking and AT-command networking put the IP-stack boundary in different places. That choice determines whether Linux sees a normal network interface or an application-specific socket service.

### Chapter 94 — WiFi+BT combo modules
- **Modules:** AP6212 (BCM43438 — combined); Realtek RTL8723BS (SDIO combo).
- The shared-antenna problem and PTA (packet-traffic arbitration)
- Bringing up both Wi-Fi and BT simultaneously on a shared module
- BT-over-UART + Wi-Fi-over-SDIO on the same chip
- **Pitfalls:** BT/Wi-Fi co-channel coexistence (2.4 GHz crowded)
- **Key Notes:** A combo module contains distinct Wi-Fi and Bluetooth paths, often using SDIO and UART respectively. Success of one interface does not prove the other works.

## Group L — Bluetooth & mesh

### Chapter 95 — HCI BLE over UART/USB
- **Modules:** Nordic nRF52 with Zephyr HCI firmware; Broadcom BCM4343 BT; CSR8510 USB.
- The Bluetooth HCI specification; how Linux's `bluez` talks HCI over UART or USB
- `hciattach`, `btmgmt`, `bluetoothctl`
- BLE central vs peripheral; GATT services
- **Pitfalls:** UART flow-control; HCI command/event timing
- **Key Notes:** HCI separates the radio controller from the Bluetooth host stack. BlueZ exposes application services above that boundary rather than requiring applications to implement link-layer behavior.

### Chapter 96 — AT-command BLE modules
- **Modules:** HM-10 (CC2540 with AT-command firmware); HC-08; JDY-08.
- The "easy" path: BLE without a kernel stack — UART AT commands
- Limitations: max throughput, no real GATT control, vendor-specific quirks
- When this is the right choice (legacy, simplicity, BOM cost)
- **Pitfalls:** firmware variant differences (HM-10 cloned five ways)
- **Key Notes:** An AT-BLE module owns most of the Bluetooth stack and exposes a serial-facing service. Linux sees its command/data protocol, not necessarily an HCI controller managed by BlueZ.

### Chapter 97 — BLE Mesh
- BLE Mesh protocol layers; provisioning, addressing, models
- `bluez-mesh` daemon and the `meshctl` tool
- Sample mesh networks: 20-node room lighting controller
- **Pitfalls:** provisioning friction; mesh-traffic flood prevention
- **Key Notes:** Mesh models define application behavior, elements contain models, and publication and subscription connect them through addresses. Network membership alone does not configure useful application behavior.

## Group M — Long-range & specialty wireless

### Chapter 98 — LoRa
- **Chips:** Semtech SX1278 (legacy, 433/868/915 MHz); SX1262 (current); LLCC68 (cheap SX1262 alternative); EByte E22 modules.
- The kernel `sx127x` driver and user-space LoRa stacks
- LoRaWAN vs LoRa-P2P; ChirpStack vs The Things Network
- Spreading factor, bandwidth, coding rate trade-offs
- **Pitfalls:** frequency-band regulation per region; antenna SWR
- **Key Notes:** LoRa is a modulation and packet-radio mechanism, while LoRaWAN adds network roles, joining, security and regional behavior. A point-to-point radio is not a multichannel gateway.

### Chapter 99 — Sub-GHz proprietary
- **Chips:** Nordic nRF24L01 (2.4 GHz proprietary, 250 kbps – 2 Mbps); TI CC1101 (sub-GHz multi-band); CC1200.
- When nRF24L01 beats BLE (raw throughput, latency, multi-PRX one-PTX hub)
- CC1101 for sub-GHz remote controls and "smart" home devices
- **Pitfalls:** crystal-frequency mismatch tank-circuit issues; ack-timing in nRF24
- **Key Notes:** These radios implement different state machines and packet services. The nRF24L01+ is a 2.4 GHz device, while CC1101 represents the sub-GHz path.

### Chapter 100 — ZigBee / Thread / 802.15.4
- **Chips:** TI CC2530 (legacy ZigBee, Z-Stack); Nordic nRF52840 (modern, OpenThread); Silicon Labs EFR32MG.
- ZigBee / Thread / 802.15.4 mesh tech compared
- The CC2530 as ZNP (ZigBee Network Processor) → Linux runs zigbee2mqtt
- nRF52840 OpenThread Border Router for the Matter ecosystem
- **Pitfalls:** Thread certification and credential setup; ZigBee profile compatibility
- **Key Notes:** IEEE 802.15.4 is a radio/MAC foundation, not a synonym for Zigbee, Thread or Matter. Shared radio hardware does not make those networks interchangeable.

### Chapter 101 — UWB ranging
- **Chips:** Qorvo (Decawave) DWM1000; DWM3000 (newer, AirTag-compatible UWB IC); NXP NCJ29D5.
- Time-of-flight ranging principle; centimeter-accuracy indoor positioning
- Two-way ranging vs TDoA
- iPhone / AirTag UWB ecosystem and FiRa standard
- **Pitfalls:** antenna delay calibration; multipath in real environments
- **Key Notes:** UWB ranging depends on radio-captured transmit and receive times, not Linux's time to service an interrupt. Host scheduling still limits how quickly exchanges can be prepared.

## Group N — Cellular

### Chapter 102 — USB 4G LTE modems
- **Modules:** Quectel EC20, EC25; SimCom SIM7600; Telit LM940.
- QMI vs MBIM vs RNDIS modes (how the modem appears to Linux)
- ModemManager + nm-connection
- Multi-band, LTE Cat-4 vs Cat-6 vs CA
- **Pitfalls:** USB power draw of LTE modems (>2A on TX); APN-vs-SIM mismatch
- **Key Notes:** A cellular modem exposes separate control, data and sometimes positioning interfaces. Their Linux device nodes represent different functions of the same system.

### Chapter 103 — UART AT-command modems
- **Modules:** SIMCom A7670C, SIM7600 (UART variants); Air724UG; ML302.
- The PPP+chat approach for legacy modems
- AT-command discovery and capabilities probing
- The 2G/3G legacy chains
- **Pitfalls:** chat script timing; carrier-specific AT command quirks
- **Key Notes:** PPP divides responsibility between modem transport, user-space negotiation and the kernel network interface. A UART stream becomes a link only after that negotiation succeeds.

### Chapter 104 — NB-IoT / Cat-M1
- **Modules:** Quectel BC95, BC26; SimCom SIM7080G.
- Low-power cellular IoT — when it makes sense vs LoRa vs WiFi
- AT command flows for ~30 mA RX, sub-mA PSM/eDRX sleep
- MQTT and CoAP profiles for NB-IoT
- **Pitfalls:** carrier band availability (NB-IoT not universal); PSM wake-up latency
- **Key Notes:** NB-IoT and LTE-M offer different coverage, latency and mobility tradeoffs. The selected module and operator must support the intended service.

## Group O — Identification

### Chapter 105 — RFID / NFC
- **Chips:** NXP MFRC522 (SPI 13.56 MHz, ubiquitous Arduino-clone); PN532 (I²C/SPI/UART, NFC-A/B/F); NCV6 series (HF-only).
- The MFRC522 register-level dance
- libnfc + neard for high-level NFC
- Mifare Classic vs DESFire — security tier comparison
- **Pitfalls:** Mifare Classic broken-by-default cryptanalysis; NFC reading-range limits
- **Key Notes:** Reader transport, tag protocol and application authorization are separate layers. Reading a tag UID identifies a presented value, not proof of an authorized person.

### Chapter 106 — Fingerprint sensors
- **Modules:** Grow R503 (capacitive, UART); FPM10A (optical, UART); GT-521F (capacitive); AS608.
- UART command protocols; template enrollment and matching
- libfprint for direct USB fingerprint scanners
- Privacy implications: template storage and revocation
- **Pitfalls:** sensor warm-up on first scan; template-format incompatibility across vendors
- **Key Notes:** The module owns image capture and matching, while the host owns enrollment authority, user identity and the action permitted after a result.

## Group P — Positioning

### Chapter 107 — GPS / GNSS + PPS time synchronization
- **Modules:** u-blox NEO-6M / 8M / 9M (multi-GNSS); ATGM336H (cheap Chinese alternative); SiRFStar V; Quectel L86.
- NMEA-0183 parsing; UBX binary protocol for u-blox
- gpsd + chrony for sub-microsecond PPS time sync
- A stratum-1 NTP server from a Pi-class device + GPS
- **Pitfalls:** cold/warm start times; multipath in urban canyons; PPS pulse polarity
- **Key Notes:** GNSS messages identify time and position, while PPS provides a timing edge. Combining them requires associating that edge with the correct second and validity state.

## Group Q — Industrial buses

### Chapter 108 — RS-485 + Modbus RTU
- **Transceivers:** Maxim MAX485, SP3485; Analog Devices ADM2483 (isolated); MAX13487 (auto-direction).
- RS-485 physical layer: differential pair, biasing, termination, fail-safe
- DE/RE direction control via GPIO or auto-direction transceivers
- Linux RS-485 mode in the UART driver (`SER_RS485_ENABLED`)
- Modbus RTU framing and libmodbus
- **Pitfalls:** termination resistor placement; ground reference between segments
- **Key Notes:** RS-485 defines an electrical link, while Modbus RTU defines framing and operations above it. Good electrical signaling does not establish correct register semantics.

### Chapter 109 — LIN bus
- **Transceivers:** NXP TJA1020, TJA1027; Microchip MCP2003B.
- LIN as a "UART with break and checksum" sub-CAN bus
- Master/slave roles; PID, response, classic checksum vs enhanced
- Linux's lack of native LIN — userspace SLIP-style or custom driver
- **Pitfalls:** LIN frame timing tolerance; cable-length-vs-baud trade-offs
- **Key Notes:** LIN uses one schedule owner to issue headers and coordinate responses. Adding another sender without that role agreement creates collisions.

### Chapter 110 — CAN deep dive
- (Extension of Ch 55C) **Transceivers:** TJA1051 (5 V), TJA1463 (CAN-FD), MCP2562; SPI-CAN bridge MCP2515 (when SoC has no FlexCAN free).
- CAN-FD vs classic CAN; bit-stuffing and frame-rate trade-offs
- ISO-TP for ISO-15765 diagnostics
- SocketCAN advanced: BCM (broadcast manager), CAN-J1939
- **Pitfalls:** termination 60 Ω vs 120 Ω; differential signal-integrity at 1 Mbit/s
- **Key Notes:** CAN controller capability, transceiver capability and network protocol are separate choices. A CAN-FD-capable transceiver cannot turn the i.MX6ULL's classic FlexCAN controller into a CAN-FD controller.

## Group R — Motors & encoders

### Chapter 111 — Quadrature encoders & rotary
- **Devices:** incremental optical encoders; magnetic encoders; the `rotary_encoder` driver and `gpio-keys` for low-res.
- Hardware quadrature decode on i.MX6ULL's eXtended quadrature decoder (XBAR + ENC)
- A 2-pin GPIO quadrature decode in software (and why it doesn't work at high speed)
- IIO `angl` channel
- **Pitfalls:** Z-index pulse handling; debouncing mechanical encoders
- **Key Notes:** Quadrature encoders report relative transitions, while absolute encoders report a position within their defined range. Homing and accumulated turns are different state problems.

### Chapter 112 — Stepper & DC motor drivers
- **Drivers:** TI DRV8825 (stepper, micro-stepping); Allegro A4988; Trinamic TMC2209 (silent stepper with UART config); BTS7960 (43 A H-bridge DC); DRV8302 (BLDC).
- Step-Dir control via PWM/GPIO with a kernel `pwm` driver
- TMC2209 UART config of microstep, RMS current, stallGuard
- BLDC commutation: trapezoidal vs sinusoidal vs FOC
- **Pitfalls:** missed steps from EMI; back-EMF damage to drivers
- **Key Notes:** Stepper pulse generation, brushed-motor PWM and BLDC commutation have different timing contracts. Linux can supervise a system without owning every fast control loop.

## Group S — Indicators & smart LEDs

### Chapter 113 — WS2812 / SK6812 / APA102 addressable LEDs
- **Chips:** WS2812B (timing-strict 1-wire); SK6812 (similar, RGBW variant); APA102 (SPI-based, no timing issues).
- Three implementation approaches:
  1. **GPIO bit-bang** with PREEMPT_RT — only viable for short strips
  2. **PWM + DMA** — repurpose PWM for serial bitstream
  3. **SPI + DMA** — encode WS2812 timing in SPI bytes; cheap and robust
- APA102's SPI native protocol; per-pixel global brightness
- **Pitfalls:** 5 V level shifting from 3.3 V GPIOs; long-strip data-line integrity
- **Key Notes:** Pulse-width-coded LEDs need a continuous waveform with the selected part's timing. Encoding into a hardware-driven stream moves that responsibility away from scheduled bit toggles.

### Chapter 114 — Beepers, relays, SSRs
- Passive beepers via PWM; active beepers via GPIO
- Mechanical relays vs MOSFETs vs SSRs — when to use which
- AC SSR safety: opto-isolation, zero-cross switching, snubber circuits
- **Pitfalls:** relay-coil flyback; SSR sub-cycle leakage
- **Key Notes:** Buzzer, relay, MOSFET and SSR interfaces differ in load behavior and protection requirements. A GPIO can request a state without safely supplying the load.

## Group T — Network & system power

### Chapter 115 — Dual FEC + hosted Ethernet
- Both i.MX6ULL FEC1 + FEC2 simultaneously: pin-mux, PHY-per-MAC, sep subnets
- IP forwarding, bridging, and bonding between the two
- **Chips:** WIZnet W5500 (SPI Ethernet with hardware TCP/IP); Microchip ENC28J60 (cheaper but slower).
- Adding a 3rd Ethernet via SPI when you need 3+ network interfaces
- **Pitfalls:** clock skew between PHYs; W5500 socket exhaustion
- **Key Notes:** Multiple network interfaces provide distinct links, while routing, bridging and segmentation define how traffic crosses between them.

### Chapter 116 — PMICs and regulator framework
- **Chips:** NXP PCA9450 (i.MX-recommended PMIC); PF8200; Rohm BD71850MWV.
- The `regulator` framework: consumer/provider model
- Voltage sequencing for SoC + DDR + I/O rails
- Dynamic voltage scaling integration with DVFS (Ch 51B)
- **Pitfalls:** boot-sequence races (kernel boots before PMIC's voltage settles); thermal throttling
- **Key Notes:** Regulator providers describe rails and consumers request the supplies they need. This dependency graph should match the physical power tree.

### Chapter 117 — External RTC
- **Chips:** Maxim DS3231 (TCXO, ±2 ppm); NXP PCF8563 (common cheap); Microchip MCP79410 (with EEPROM).
- Why crystal RTCs drift (and why TCXO is worth the money for fleets)
- Battery-backed time keeping; the "RTC dead but device works" failure mode
- `hwclock`, `rtc-i2c` family of drivers
- Alarm interrupts for wake-from-suspend (Ch 51B integration)
- **Pitfalls:** the i.MX6ULL internal RTC is part of SNVS and loses time without backup battery; DS3231 alarm-pin polarity
- **Key Notes:** The RTC retains time independently of the system clock, while NTP or another reference disciplines system time. Synchronization direction and validity need one clear policy.


---

## PART VIII — DEBUG, PRODUCTION, ADVANCED

### Chapter 118 — JTAG, OpenOCD, GDB at every layer
- Connecting a JTAG adapter (FT2232H / J-Link) to the Point Atom JTAG header
- OpenOCD config for i.MX6ULL
- GDB scripts for bare-metal, U-Boot (`gdb-multiarch u-boot`), and the kernel (`vmlinux` symbols)
- Hardware breakpoints, watchpoints
- **Key Notes:** JTAG provides a hardware access path when the target cannot run a software debug agent. The adapter, OpenOCD configuration, and GDB symbol files have separate responsibilities.

### Chapter 119 — Kernel debugging without JTAG
- `printk` and log levels
- `pr_debug` and `CONFIG_DYNAMIC_DEBUG`
- ftrace: `function`, `function_graph`, events
- trace-cmd and KernelShark
- `bpftrace` and `bcc` tools (introductory)
- kgdb over UART
- Decoding an oops: `addr2line`, `scripts/decode_stacktrace.sh`, `CONFIG_DEBUG_INFO`
- **Key Notes:** Software observability depends on code paths that still execute. Logs and trace buffers cannot replace hardware debug access when the required kernel infrastructure is unavailable.

### Chapter 120 — User-space debugging
- `gdbserver` on target, `gdb-multiarch` on host
- `strace`, `ltrace`
- `perf` (sampling, counters, flamegraphs)
- Core dumps and `coredumpctl`
- **Key Notes:** `gdbserver` controls the target process while host GDB owns symbols and source lookup. The host executable and target libraries must describe the deployed build.

### Chapter 120A — Supplementary: Mainline patch submission workflow
If you write a driver in this book and it's good, it can go upstream. We walk the entire process end-to-end on a real candidate patch (e.g., a tweak to the FEC driver, or a YAML binding for a new sensor).
- `git format-patch` and the one-patch-per-fix discipline
- `scripts/checkpatch.pl --strict`; the warnings that matter, the ones that don't
- `scripts/get_maintainer.pl` to find the right list and the right reviewer
- `git send-email` setup (the only patch-submission tool the kernel community accepts)
- Subject-line conventions: `[PATCH] drivers/net/ethernet/freescale/fec: ...`
- Cover letters; v1 / v2 / v3 etiquette; `Reviewed-by`, `Acked-by`, `Tested-by`, `Reported-by`, `Suggested-by`, `Co-developed-by`
- Replying to review feedback — what to do, what not to do
- The Lore archive, `b4` for series management
- **Key Notes:** A patch carries both a code change and its rationale. One logical change per patch makes the affected interface and regression risk visible.

### Chapter 121 — Custom board port as a system design
- Compare unchanged MINI hardware, attached-device variants and custom PCBs
- Follow ownership across early hardware, U-Boot, kernel description and rootfs
- Separate reproducible artifact production from physical deployment
- Explain failure boundaries, recovery and the evidence behind design decisions
- **Key Notes:** A board port connects fitted hardware to several software descriptions. Power and reset behavior, early DDR setup, U-Boot configuration, kernel DT, and rootfs contents have distinct owners.

### Chapter 121A — Supplementary: CI/CD for embedded Linux
Modern teams build U-Boot, kernel, rootfs, and run a smoke test on the actual hardware on every commit. We set this up using GitHub Actions (or GitLab CI), a self-hosted runner with USB-OTG to a board, and a small Labgrid-style harness.
- Cross-builds in CI: caching, deterministic builds, `bitbake-no-network` patterns
- Image artifact storage (size budget: ~150 MB per build × 20 commits/day)
- A self-hosted runner with a board on a USB hub
- The minimal smoke test: boot, wait for `=>`, run a 5-second sysfs check, capture serial log
- Pass/fail signaling back to the PR
- Notifications when the board farm is offline
- **Key Notes:** Cloud runners construct cross-built artifacts and check source. A hardware runner owns the physical board and provides a different kind of evidence.

### Chapter 122 — Build your own cross-toolchain
- Bootstrap problem: gcc needs libc, libc needs gcc, gcc needs binutils
- crosstool-NG step-by-step: kernel headers → binutils → gcc stage 1 → glibc/musl → gcc stage 2
- Comparing your toolchain against a pre-built Arm GNU one (size, behavior, sysroot)
- **Key Notes:** A toolchain combines code-generation tools, target runtime components, and a debugger. Its target ABI and libraries must agree with the deployed rootfs.

### Chapter 122A — Supplementary: BSP → mainline migration playbook
You inherited a Linux 4.1.15 vendor BSP from a previous project or a customer. The product needs to ship updates for the next eight years. You must move to a supportable mainline kernel. Here is the playbook.
- Inventory: list every patch the vendor applied; classify (vendor-feature / vendor-bugfix / mainline-merged / dead-code)
- The pinned-driver problem and how to break each pin
- Per-subsystem upstreaming order (most-self-contained first: clk → pinctrl → gpio → i2c → ... → display/network last)
- Maintaining two trees during the migration (vendor "shipping" + mainline "next")
- Bisection across kernel versions when an old hack now breaks
- When to **not** migrate (truly captive silicon with no mainline future)
- A concrete worked example: NXP i.MX6ULL 4.1.15 → 6.x mainline
- **Key Notes:** Migration preserves required product behavior across changing interfaces, rather than replaying every vendor patch onto a newer tree.

### Chapter 123 — Yocto vs Buildroot, an honest comparison
- The mental model: package metadata vs configuration system
- Layers, recipes, BBLAYERS
- When Buildroot is better; when Yocto is better; when *neither* is right
- A single recipe written for Yocto and for Buildroot, side by side
- **Key Notes:** Buildroot organizes an image around configuration and package definitions. Yocto composes recipes, layers, machines, distribution policy, and image contents.

### Chapter 123A — Supplementary: Yocto layer development in depth
For shipping at scale, Yocto is industry standard, and the meat of using it is *writing layers*. We build a vendor layer (`meta-mybsp`), a board layer (`meta-mybsp-mini`), and an application layer (`meta-mybsp-myapp`), with the right bbappend pattern between them.
- Layer anatomy: `conf/`, `recipes-*/`, `classes/`, `wic/`
- `bbappend` and the layer-priority dance
- Writing a `.bb` for our LED-driver kernel module (Chapter 41)
- Writing a `.bb` for an in-house Qt app
- `wic` for image layouts (partition tables, RAUC slots)
- Distro layers (`meta-mybsp-distro`) vs board layers
- `IMAGE_FEATURES`, `EXTRA_IMAGE_FEATURES`, `DISTRO_FEATURES`
- The `SRC_URI` cache that makes the build reproducible without internet
- **Key Notes:** `MACHINE` describes hardware, `DISTRO` expresses shared policy, and image recipes select shipped contents. Separating these responsibilities limits variant leakage.

### Chapter 124 — Secure boot (HAB) and OP-TEE
- The chain of trust: ROM → SRK fuses → CSF → signed U-Boot → signed kernel → dm-verity rootfs
- HAB CST (Code Signing Tool), `csf` files, key ceremony
- TrustZone primer, `monitor` mode, SMC calls
- OP-TEE basics: TA (Trusted Application) lifecycle
- **Key Notes:** HAB anchors bootloader authentication in ROM and a provisioned key hash. FIT verification, rootfs integrity, and module policy extend trust only when their inputs are protected.

### Chapter 125 — Field updates
- A/B partition scheme with U-Boot
- RAUC, SWUpdate, Mender — comparison
- Atomic updates, rollback, fail-safe boot
- **Key Notes:** An A/B update preserves the running slot while constructing a candidate in the inactive slot. Completion must precede changing persistent boot selection.

### Chapter 125A — Supplementary: VSCode + gdbserver remote-debug workflow
Many readers came here from VSCode and would rather debug there than learn `tui` mode. We set up `gdbserver` on the target, `gdb-multiarch` on the host, the VSCode `launch.json` that joins them, and the `.vscode/c_cpp_properties.json` that resolves headers from the cross-sysroot — so `Go to Definition` works on kernel sources too.
- Source Insight as a faster alternative for kernel-source navigation only (read-only, but very fast)
- The minimum target setup: a statically-linked `gdbserver` binary in `/usr/bin/`
- Single-stepping a kernel module loaded with `insmod`
- **Key Notes:** VSCode presents debugger state but does not implement target debugging. Host GDB and target `gdbserver` retain their command-line responsibilities.

### Chapter 126 — Closing: what to read next
- LDD3 (still relevant where it isn't outdated)
- Bootlin training material
- `kernelnewbies.org`
- LWN — the single most useful periodical for a Linux engineer
- The mailing list etiquette guide; how to send your first patch
- **Key Notes:** Every layer needs an owner and a contract: what it receives, what it changes, what it promises, and how failure is reported.


---

## PART IX — APPLIED VIRTUALIZATION AND MIXED-CRITICALITY SYSTEMS

> *This part is optional and advanced. It exists for readers who want real hypervisor experiments, not only HYP-mode vocabulary. The path starts in QEMU, moves to Xen on the i.MX6ULL, then uses Jailhouse and STM32MP1 where the hardware model is a better fit.*

### Chapter 127 — Why embedded products use hypervisors
- The real product problems: crash isolation, security boundaries, mixed criticality, legacy BSP containment, and device ownership
- Containers vs PREEMPT_RT vs TrustZone vs remoteproc/OpenAMP vs Xen vs Jailhouse
- Why a hypervisor is sometimes the clean answer and sometimes architectural overkill
- The rule for this part: every chapter must end with something visible and testable
- **Key Notes:** The choice begins with a failure to contain and the workload that must survive it. A process, container, guest, partition or companion MCU provides a different boundary.

### Chapter 128 — QEMU as a virtual hardware model
- QEMU as a repeatable ARM hardware model, not an i.MX6ULL clone
- ARMv7-A `virt`, ARM64 `virt`, and when `vexpress` is useful
- Serial console, memory size, CPU model, DTB, kernel, initrd, and command line as explicit hardware choices
- GDB with `-S -s` before Linux prints anything
- **Key Notes:** A QEMU launch describes a virtual machine: CPU, memory, interrupt controller, devices and firmware are explicit inputs. Its generated DTB describes that selected model.

### Chapter 129 — Build and boot tiny Linux in QEMU
- Build a tiny ARM Linux kernel and BusyBox/Buildroot initramfs
- Direct boot: `QEMU → Linux → initramfs → /init`
- DTB, `console=`, `rdinit=`, and the first shell
- Failure-driven learning: wrong console, missing init, wrong DTB
- **Key Notes:** The kernel, Device Tree and initramfs are separate boot inputs. They provide executable kernel code, a hardware description and the initial user-space tree respectively.

### Chapter 130 — U-Boot in QEMU
- Put U-Boot in front of the QEMU Linux boot
- Manual `bootz` / `booti`: load kernel, DTB, initramfs into non-overlapping RAM
- `bootargs`, scripted boot, and FIT handoff
- Why hypervisors depend on firmware doing the next-stage handoff correctly
- **Key Notes:** U-Boot owns artifact loading and the next-stage handoff. The kernel owns interpreting its DTB, arguments and initial filesystem after that handoff.

### Chapter 131 — HYP mode, stage-2 MMU, and virtual interrupts
- PL0, PL1, PL2, HYP mode, `svc`, and `hvc`
- HYP mode vs TrustZone Monitor mode
- Stage-1 translation: virtual → physical
- Stage-2 translation: guest physical → real physical
- Virtual timer, virtual GIC, and why guests need believable interrupts
- **Key Notes:** Stage 1 belongs to the guest operating system when it uses translation. Stage 2 gives the hypervisor a separate CPU memory boundary.

### Chapter 132 — Xen in QEMU
- Boot path: `QEMU → Xen → Dom0 Linux`
- Xen binary, Dom0 kernel, initramfs/rootfs, DTB, and console
- `xl info`, memory allocation, and where control moves from Xen to Dom0
- Keeping the first Xen boot small and serial-only
- **Key Notes:** Xen takes control before Dom0 Linux. Dom0 is a privileged domain with platform responsibilities, not native Linux outside the hypervisor.

### Chapter 133 — First DomU Linux
- Boot path: `Xen → Dom0 → xl create → DomU`
- Domain config explained line by line: name, kernel, ramdisk, memory, vCPUs, console, command line
- Tiny BusyBox/Buildroot guest first, not a full distribution
- Failure isolation: DomU can die while Dom0 survives
- **Key Notes:** A DomU is another kernel with assigned memory, virtual CPUs and interfaces. It is not an ordinary process in Dom0's PID namespace.

### Chapter 134 — Xen on i.MX6ULL
- Moving from QEMU to the real board
- i.MX6ULL reality: one Cortex-A7, limited RAM, real DTB, real UART, real U-Boot handoff
- Build Xen for ARM32 and boot Dom0 Linux on the Point Atom board
- Confirm that the board demonstrates HYP-mode mechanics but is not a rich virtualization platform
- **Key Notes:** The physical boot path adds U-Boot and MINI-specific hardware dependencies before Xen can start. QEMU success cannot supply evidence for those dependencies.

### Chapter 135 — DomU Linux on i.MX6ULL
- A tiny DomU on the real board: one vCPU, small RAM, initramfs, console only
- `xl list`, DomU console, `uname -a` in both worlds
- What this proves: real guest isolation
- What it does not prove: performance, device pass-through safety, or hard real-time behavior
- **Key Notes:** Dom0 and DomU have separate kernel and memory views while sharing the i.MX6ULL's one physical CPU. Scheduling capacity and failure containment are different objectives.

### Chapter 136 — Devices, memory, and DMA boundaries
- Device ownership tables: owner, shared/not shared, DMA, reset, clock, pinctrl, debug
- Why the CPU MMU does not automatically protect against DMA
- UART, Ethernet, GPIO bank, SPI/I2C, timers, and interrupt ownership
- Xen grant tables, event channels, virtual network, shared memory
- **Key Notes:** Every hardware resource needs one control owner, including its configuration, reset and recovery path. Sharing requires a defined mediation interface.

### Chapter 137 — Jailhouse in QEMU ARM64
- Why Jailhouse is taught on QEMU ARM64 first: multiple CPUs and a known demo platform
- Boot path: `QEMU ARM64 → Linux root cell → jailhouse.ko → system cell → inmate cell`
- Root cell vs inmate cell, CPU assignment, memory regions, interrupts, and no scheduler
- Why i.MX6ULL is a poor Jailhouse target even though Cortex-A7 can implement virtualization extensions
- **Key Notes:** Jailhouse partitions resources after Linux has booted. It does not provide Xen's general domain-management model.

### Chapter 138 — Bare-metal or Zephyr inmate cell
- Start with a minimal bare-metal inmate before adding Zephyr
- Link address, assigned RAM, console ownership, timer, and stop/reload path
- Zephyr as the RTOS-flavored inmate once the bare-metal path is understood
- Shared memory and interrupt discipline
- **Key Notes:** Cell configuration, link address, entry point and stack form one runtime contract. They must agree before a C function can execute.

### Chapter 139 — STM32MP1 Linux plus RTOS, the production pattern
- Why STM32MP157 is a better Linux+RTOS teaching target than i.MX6ULL: dual A7 plus M4
- Main production path: Linux on Cortex-A7, Zephyr/FreeRTOS on Cortex-M4, RPMsg/OpenAMP between them
- Optional Jailhouse path for A7-to-A7 partitioning when the M4 is not enough
- Decision checklist: Xen vs Jailhouse vs remoteproc/OpenAMP vs no hypervisor
- **Key Notes:** Remoteproc manages a remote processor's firmware and lifecycle, RPMsg carries messages, and OpenAMP supplies software for those mechanisms. They are related but not interchangeable responsibilities.


---

## Chapter coverage

| Part | Numbered | Supplementary | Total |
|------|---------:|--------------:|------:|
| I — Foundations | 8 | 0 | 8 |
| II — Bare-metal i.MX6ULL | 10 | 3 | 13 |
| III — U-Boot | 6 | 10 | 16 |
| IV — Kernel | 6 | 6 | 12 |
| V — Rootfs & user space | 5 | 9 | 14 |
| VI — Driver development | 20 | 14 | 34 |
| VII — Device cookbook | 54 | 0 | 54 |
| VIII — Debug & advanced | 9 | 5 | 14 |
| IX — Applied virtualization | 13 | 0 | 13 |
| **Total** | **131** | **47** | **178** |

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
                                                          │
                                                          ▼
                                            Ch127..Ch139 (optional virtualization path: QEMU → Xen → Jailhouse/STM32MP1)
```

The arrows describe conceptual dependencies, not required builds. A kernel or driver reader can revisit the bare-metal mechanism when an address, clock or interrupt assumption needs explanation. The device chapters and advanced design studies are references, not a sequence of assignments.

### Where the supplementary chapters fit

```
Ch10 ──┬──► Ch18A (project organization)  ──► informs every subsequent bare-metal Ch
       └──► Ch11..Ch16 (proceed normally)
Ch16 ──► Ch18B (button+beep)  ──► Ch17 MMU
Ch18 ──► Ch18C (bare-metal RTC)
Ch24 ──┬──► Ch24A (separate new-SoC design study)
       └──► Ch24B..Ch24J (applied U-Boot design studies)
Ch26 ──► Ch26A (kernel boot failure playbook) ──► Ch27
Ch27A ──► Ch27B (custom-board Device Tree)
Ch29 ──► Ch29A (initramfs recovery system)
Ch30A ──► Ch30B (product kernel configs)
Ch35 ──► Ch35D (bootable SD/eMMC layout) ──► Ch35I (boot from SPI NOR)
Ch35I ──► Ch35E (Buildroot board directory)
Ch35E ──► Ch35A (Ubuntu-base, optional alternative) ──► Ch35F (app as service)
Ch35F ──► Ch35G (network/time/logging) ──► Ch35B (read-only rootfs)
Ch35B ──► Ch35H (rootfs security basics) ──► Ch35C (containers)
Ch43 ──► any of Ch55A..Ch55H (siblings, independent)
Ch44..Ch55I ──► any chapter of Part VII Device Cookbook (Ch 64..Ch 117) — pick the chip class you need
Ch120 ──► Ch125A (VSCode workflow; can be read after any driver chapter)
Ch126 ──► Ch127..Ch139 (optional virtualization and mixed-criticality path)
```

---

## Project decisions

1. **Target board.** Point Atom MINI with a revision-specific 512 MiB DDR3L core-board example is the primary reference. Clock limits come from the actual chip marking and electrical conditions, not the board name. Parts IV–VIII teach concepts applicable to other Linux-capable ARM SoCs, but their board configuration and drivers still need porting.
2. **Language.** English only. No bilingual edition planned.
3. **Source baselines.** Linux **v6.6** API conventions; the supplied MINI vendor U-Boot **2016.03** tree for the board baseline and **v2026.04** for the separate mainline study; two Arm GNU **13.2.Rel1** toolchains. Later Buildroot and Yocto chapters name their own source versions. Do not silently mix board support, generated artifacts or API signatures from different trees.
4. **Code-listing license.** MIT. Reuse does not establish that a snippet is complete, safe for a particular board, or compatible with another source version.
5. **Tooling.** Markdown sources + **Sphinx + Furo + MyST-Parser**, hosted on GitHub Pages and auto-rebuilt on push. The reading path begins at Chapter 1. Publishing instructions live in the repository's `PUBLISH.md`.
6. **Examples.** **Inline in the chapters.** There is no companion `code/` repository. Listings illustrate mechanisms and interface contracts rather than assigned projects. Architecture review and physical qualification are separate responsibilities, even when implementation is generated by a tool.
