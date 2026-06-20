# Chapter 5: A tour of the i.MX6ULL SoC
> **What:** a top-down map of the chip, what blocks are inside it, where they live in memory, how they are clocked, and how their pins are routed.
>
> **Why:** every later chapter will name a peripheral. For each one you should be able to find it on the block diagram, locate its register base, find its clock root and gate bit, and know what pin it lands on. All of that in a few minutes.
>
> **Focus:** the **memory map**, the **clock tree at one level of detail**, and the **IOMUX pattern**. These three structures repeat across every NXP i.MX SoC. The names change, the shapes do not.

> **IOMUX:** the pin multiplexer that decides which peripheral function appears on each package pin.


## 5.1  What is the i.MX6ULL

The i.MX6ULL is a low-cost member of NXP's i.MX6 family. It has one Cortex-A7 core and no GPU, VPU, or PCIe controller. It still provides Ethernet, USB, LCD, CSI camera, SAI audio, eMMC, NAND, QSPI, eight UARTs, four I²C controllers, and four ECSPI controllers. It targets applications such as industrial HMIs, point-of-sale terminals, smart meters, and gateways.

Key parameters of the part variant used on Point Atom MINI:

- **Core:** 1 × Cortex-A7 @ 528 / 696 MHz
- **L1 cache:** 32 KB I + 32 KB D
- **L2 cache:** 128 KB unified, integrated inside the Cortex-A7 MPCore (no external PL310 controller)
- **On-chip memory:** 128 KB **OCRAM** at `0x00900000`, plus a separate 96 KB **Boot ROM** at `0x00000000` that is mask-programmed by NXP. There is **no TCM**. A-profile systems normally use caches and system RAM instead.
- **DRAM:** 16-bit LPDDR2/DDR3L/DDR3 controller (MMDC). The Point Atom core boards used in this book have 256 MiB or 512 MiB.
- **Boot media:** SD/MMC, eMMC, NAND, SPI NOR, QSPI, parallel NOR, and USB SDP recovery
- **Process:** 28 nm
- **Package:** BGA289 / BGA324 (depending on variant)

Two part-number suffixes you will see: **MX6Y2** (i.MX6ULL with crypto), **MX6G2** (lower-cost, fewer peripherals). The Point Atom MINI uses MX6Y2.

## 5.2  Block diagram

A simplified view (omitting buses for clarity):

```
                  ┌─────────────────────────────────────────────┐
                  │             Cortex-A7 (1 core)              │
                  │   L1-I 32KB │ L1-D 32KB │ NEON │ VFPv4      │
                  └────────────┬────────────────────────────────┘
                               │ AXI
   ┌───────────────────────────┼────────────────────────────────┐
   │                         BUS MATRIX (AXI/AHB/IPS)           │
   └─┬───────┬────────────┬──────────────┬────────┬─────────────┘
     │       │            │              │        │
     ▼       ▼            ▼              ▼        ▼
   OCRAM   ROM         MMDC            EIM      Peripherals
   128KB   96KB        DDR ctrl    parallel mem  via IPS bus
                       │
                       ▼
                   external DDR3
                   (256/512 MB on MINI)
```

The **bus matrix** connects bus masters, such as the CPU and DMA engines, to targets such as OCRAM, DDR, and peripheral bridges. Most early software does not configure the matrix directly, but it becomes relevant when analyzing bandwidth and latency.

## 5.3  System memory map

The i.MX6ULL exposes a 4 GB physical address space. Most of it is unused. The rest is divided into regions whose function does not change. Memorize this table. It is the geography of the chip.

| Region | Base | Size | What's there |
|--------|------|------|--------------|
| **Boot ROM** | `0x00000000` | 96 KB | NXP's mask-programmed boot code (see Ch 7) |
| Caches debug | `0x00018000` | 16 KB | (alias of ROM in normal modes) |
| **Boot ROM alias** | `0x00100000` | 96 KB | Same ROM, second alias used after high-vectors |
| **OCRAM** | `0x00900000` | 128 KB | On-chip SRAM |
| GIC distributor | `0x00A01000` | 4 KB | (and CPU interface at `0x00A02000`) |
| External PL310 L2 controller | (absent) | - | i.MX6ULL's 128 KB L2 is integrated in the MPCore block. |
| **AIPS-1** | `0x02000000` | 1 MB | IP slaves group 1: SDMA, GPIOs, UARTs, IOMUXC |
| **AIPS-2** | `0x02100000` | 1 MB | IP slaves group 2: USB, MMDC, CCM, ANATOP, SNVS, EPIT, GPT |
| **AIPS-3** | `0x02200000` | 1 MB | IP slaves group 3, including CAAM and SJC |
| **External Memory Interface (EIM)** | `0x08000000` | 128 MB | Parallel NOR / FPGA / external SRAM |
| **QSPI** | `0x60000000` | 256 MB | Memory-mapped QuadSPI flash |
| **MMDC0 (DRAM)** | `0x80000000` | up to 2 GB | External DDR3 |

A few things worth committing to long-term memory:

1. **The DRAM address range starts at `0x80000000`.** A U-Boot script may set `loadaddr=0x80800000`, which is 8 MiB above the DRAM base. The offset leaves working space around the loaded image.
> **U-Boot:** the bootloader that initializes enough hardware to load and start the Linux kernel.
2. **OCRAM at `0x00900000`** is where the Boot ROM places your SPL and where bare-metal images live before DRAM is up. 128 KB is enough for a substantial bootloader stage.
> **SPL:** Secondary Program Loader, a tiny first U-Boot stage that fits in OCRAM and initializes DDR.
3. **Most peripheral registers live in AIPS-1, AIPS-2, or AIPS-3.** For example, CCM at `0x020C4000` is inside the AIPS-1 range that starts at `0x02000000`. The high address digits help identify the containing region.
> **CCM:** Clock Controller Module. It selects clock sources, dividers, and gates for the SoC.

The reference manual has the full map in Chapter 2 ("Memory Maps"). You can print that table and tape it to the wall.

## 5.4  OCRAM and the boot footprint

The Boot ROM uses part of OCRAM (`0x00900000`-`0x0091FFFF`) while running the boot sequence. The low end holds exception vectors. The top end holds the MMU table, stack, and ROM working state. The following ranges come from i.MX6ULL Reference Manual §8, Figure 8-3, "OCRAM Memory Map During Boot":

| Start | End | Approx size | During Boot ROM execution | What it means for us |
|-------|-----|-------------|---------------------------|----------------------|
| `0x00900000` | `0x009001FF` | 0.5 KB | ROM exception-vector region. | Do not place your image here while the ROM may still be involved. |
| `0x00900200` | `0x00906FFF` | 27.5 KB | ROM working state and scratch area. | Treat as reserved during boot. |
| `0x00907000` | `0x00917FF0` | ~68 KB | OCRAM Free Area during boot. | This is where your bootable image or U-Boot SPL is loaded. |
| `0x00918000` | `0x0091FFFF` | ~32 KB | ROM MMU table, stack, and per-boot state. | Reserved until the ROM has handed off. |

During Boot ROM execution, the usable window is the ~68 KB middle range. **After the ROM transfers control and its services are no longer needed**, software can use the entire 128 KB OCRAM range, `0x00900000`-`0x0091FFFF`.

This means **U-Boot SPL must fit in ~64 KB** (with a small reserve under the 68 KB window). The lab in Chapter 9 (LED in pure assembly) will be < 1 KB. The full bare-metal stack with DDR init in Chapter 14 will be < 30 KB. U-Boot SPL is designed for exactly this window.

## 5.5  The clock tree (at one level of detail)

The i.MX6ULL clock tree has about 200 leaf signals. A full drawing is too large for this chapter. What you need is the four-layer structure:

```
External oscillators ─► PLLs (ANATOP) ─► Root clocks (CCM) ─► Gates (CCGR) ─► Peripherals
```

### Layer 1, Oscillators

- **XTALOSC24M**: 24 MHz crystal. Everything derives from this. The Point Atom MINI has a 24 MHz crystal on Y2.
- **XTALOSC32K**: 32.768 kHz crystal for the RTC / SNVS domain. Optional. If absent, the RTC is less accurate.

### Layer 2, PLLs (in the ANATOP block)

Seven PLLs:

| PLL | Default rate | Purpose |
|-----|--------------|---------|
| PLL1, ARM PLL | 528 or 696 MHz | Core clock |
| PLL2, System PLL | 528 MHz (fixed) | Bus clocks, peripherals |
| PLL3, USB1 PLL | 480 MHz (fixed) | USB, peripheral references |
| PLL4, Audio PLL | variable (44.1/48 kHz multiples) | SAI |
| PLL5, Video PLL | variable (LCD pixel rates) | eLCDIF |
| PLL6, ENET PLL | 500 MHz | Ethernet refclk |
| PLL7, USB2 PLL | 480 MHz | Host USB |

PLL2 and PLL3 expose **PFDs** (Phase Fractional Dividers): four per PLL, each producing a fractionally-divided output. E.g., PLL2_PFD2 at 396 MHz is commonly used as the AHB root.
> **PLL:** Phase-Locked Loop, a clock block that multiplies a reference clock to create faster clocks.

### Layer 3, Root clocks (in CCM)

The CCM (Clock Controller Module) takes PLL outputs and PFDs, multiplexes them, divides them, and produces ~60 named root clocks: `AHB_CLK_ROOT`, `IPG_CLK_ROOT`, `UART_CLK_ROOT`, `USDHC1_CLK_ROOT`, `CSI_CLK_ROOT`, and so on.

A typical setting on i.MX6ULL:

- ARM core: 696 MHz (PLL1)
- AXI bus: 198 MHz (PLL2_PFD2 / 2)
- AHB: 132 MHz
- IPG (peripheral bus): 66 MHz
- UART input: 80 MHz (PLL3 / 6)

You will set these explicitly in Chapter 13. Until then, the Boot ROM and U-Boot do it for you.

### Layer 4, Gates (CCGR0..CCGR6)

Every peripheral has a **gate bit** (or pair of bits) in one of seven `CCM_CCGRx` registers. The bits have three possible values:

- `00`: clock off in all modes
- `01`: clock on in run mode only, off in WAIT/STOP
- `11`: clock on in all modes

In bare-metal code you'll typically write `11`. In production you'd write `01` to save power.

The mapping of peripheral to CCGR bit lives in the reference manual's CCM chapter, Table 18-5. You will visit that table dozens of times during this book.

**The most common NXP bring-up pitfall:** forgetting to enable a peripheral's clock gate. Symptom: the peripheral's registers read as zero or unexpected values, and writes have no effect. Always check the gate first.

## 5.6  IOMUX, the universal multiplexer

Most package pads can carry several alternate functions. Depending on the pad, the choices may include GPIO, UART, I²C, Ethernet, USB control, timer output, or camera signals. Each pad has its own ALT table, so always look up the exact pad in the IOMUXC chapter of the reference manual.

The **IOMUXC** (IO Multiplexer Controller) block contains, for every pin:

- A **MUX_CTL** register selecting which ALT (and a few other bits, SION, "Software Input On", which forces the pad's input buffer on even when output-driven).
- A **PAD_CTL** register controlling drive strength, slew rate, pull-up/down, hysteresis, open-drain.
- Some input functions also require a **SELECT_INPUT** register. This register chooses which eligible pad feeds the peripheral input. NXP calls this selection a "daisy chain."

A complete pin setup is therefore *two* writes (sometimes three):

```c
IOMUXC_SW_MUX_CTL_PAD_GPIO1_IO03 = 0x5;   /* ALT5 = GPIO1_IO03 */
IOMUXC_SW_PAD_CTL_PAD_GPIO1_IO03 = 0xB0B1; /* pad electrical settings */
/* if the pin's function has a SELECT_INPUT, write that too */
```

The value `0xB0B1` appears in many NXP examples. It configures electrical properties such as pull resistance, drive strength, and slew rate. Chapter 9 decodes the fields before using a pad-control value.

> **Focus.** After checking a peripheral's clock gate, check its IOMUX settings. Missing output, no input, or a constant read value can result from the wrong MUX_CTL, PAD_CTL, SELECT_INPUT, or SION setting.

The IOMUX tables fill about 300 pages of the reference manual. You will not read them all. You will spend a lot of time searching them for a pin you care about.

## 5.7  Power domains and the SNVS

The chip has three power domains worth knowing:

- **VDD_SOC**: main digital supply (the part you turn off in deep sleep).
- **VDD_ARM**: core supply (separated so you can DVFS it).
- **SNVS**: Secure Non-Volatile Storage: a tiny always-on domain with its own oscillator, RTC, and 24 bytes of SRAM. This block stores the chip's secure boot state, handles RTC wake alarms, and receives the "tamper" inputs.

This book first uses SNVS for its real-time clock and retained registers. Later chapters also discuss its security and low-power functions.

## 5.8  Fuses and identification

The **OCOTP** (One-Time Programmable) block contains ~96 words of fuse-burnable storage. Some fuses are factory-programmed and read-only (unique chip ID, MAC address slots, silicon revision). Others can be burned by your code (boot device selection, HAB SRK hashes, NX bits). Reading is cheap:
> **HAB:** High Assurance Boot, NXP's ROM-enforced secure boot mechanism on i.MX SoCs.

```c
uint32_t chip_id_lo = OCOTP_HW_OCOTP_CFG0;
uint32_t chip_id_hi = OCOTP_HW_OCOTP_CFG1;
```

Boot configuration can depend on both fuses and external boot-mode pins. OTP fuse programming is permanent, so this book reads OCOTP fields before it writes any. Never program boot or security fuses without checking the reference manual, the board schematic, and the recovery consequences.

## 5.9  Peripherals catalog

The peripherals you will touch in this book, with reference-manual chapter numbers (rev 1, 11/2017):

| Block | RM Chapter | Notes |
|-------|-----------|-------|
| CCM | 18 | Clock controller, Ch 5, 13 |
| ANATOP | 19 | Analog top: PLLs, Ch 5, 13 |
| IOMUXC | 32 | Pin mux, every peripheral chapter |
| GPIO | 28 | 5 GPIO banks × 32 = 160 pins, Ch 9, 44 |
| GIC | (ARM TRM) | Interrupt controller, Ch 4, 15 |
| GPT | 29 | General-purpose timer, Ch 16 |
| EPIT | 30 | Enhanced periodic interrupt timer, Ch 16 |
| UART | 55 | 8 UARTs, IrDA-capable, Ch 12 |
| I²C | 31 | 4 I²C controllers, Ch 46 |
| ECSPI | 21 | 4 SPI controllers, Ch 47 |
| USDHC | 58 | SD/MMC and boot media, Ch 11 |
| MMDC | 39 | DDR controller, Ch 14 |
| FEC | 22 | Ethernet MAC, Ch 52 |
| USB | 66 | OTG + host, Ch 55 |
| eLCDIF | 23 | LCD controller, Ch 54 |
| CSI | 14 | Camera input, (optional) |
| SAI | 38 | Audio I²S, Ch 53 |
| ADC | 13 | 12-bit, 10 channels, Ch 49 |
| PWM | 41 | PWM, Ch 48 |
| SNVS | 47 | RTC + secure storage, Ch 48 |
| OCOTP | 37 | Fuses |
| WDOG | 64 | Watchdog |
| GPC | 26 | Power controller |
| SRC | 50 | System reset controller |

That table is the rough sequence of when we meet each peripheral. Bookmark it.

## 5.9a  Point Atom ALPHA vs MINI, what's on each board

The two Point Atom dev boards built around the i.MX6ULL share the same SoC but differ in onboard peripherals. Knowing which board you have changes which chapters' labs you can do without external add-ons.

| Peripheral | i.MX6ULL signal / pin | ALPHA | MINI | Used in chapter(s) |
|---|---|---|---|---|
| **LED0** (user LED) | GPIO1_IO03 | yes | yes | 9, 10, 41 |
| **KEY0** (user button) | GPIO1_IO18 (UART1_CTS_B pad) | yes | yes | 18B, 45, 49 |
| **BEEP** (passive buzzer, PNP-driven, active-low) | GPIO5_IO01 (SNVS_TAMPER1 pad) | yes | yes | 18B, 46 |
| **UART1** (debug console through built-in USB-TTL) | UART1_TX_DATA / UART1_RX_DATA | yes | yes | 3, 12, 13, all |
| **DDR3L** size | Core-board memory bus | 256 MiB (NAND core) / 512 MiB (eMMC core) | 256 MiB / 512 MiB | 14, 25+ |
| **DDR3L part** | Core-board memory bus | Nanya NT5CC128M16JR-EK (256 MiB) or NT5CC256M16EP-EK (512 MiB) | same | 14 |
| **NAND part** (when present) | NAND interface | Micron MT29F2G08ABAEAWP-IT (256 MiB) or MT29F4G08ABADAWP-IT (512 MiB) | same | 14, 30, 54A |
| **eMMC** | USDHC2 | Samsung KLM8G1GET (8 GiB) | Samsung KLM8G1GET (8 GiB) | 30, 39 |
| **NAND** alternate boot | NAND interface | optional (rev-dependent) | optional | 30, 54A |
| **RGB LCD** | LCDIF + capacitive touch (GT911 typical) | on the board | optional add-on | 18, 24, 54, 64 |
| **WM8960 audio codec** + headphone jack + mic | SAI2 + I²C2 | yes | no | 53, 65 |
| **WiFi USB/SDIO** | USB host / USDHC1 | RTL8188 USB header | RTL8189 SDIO module | 70 |
| **4G modem header** (USB) | USB host | header present | header present | 71 |
| **Wired Ethernet** | FEC1 + KSZ8081 PHY | 2 × RJ45 | 1 × RJ45 | 52, 69 |
| **CAN transceiver** | FlexCAN | yes, 2 channels | no onboard transceiver | 66 |
| **RS232 / RS485** | UART3, UART2 + transceiver IC | yes | RS485 only | 63 |
| **GPS UART** | UART | yes | yes | 63 |
| **I²C light sensor AP3216C** | I2C1 | yes | no | 26, 61 |
| **SPI 6-axis ICM-20608** | ECSPI3 | yes | no | 27, 62 |
| **VBAT for RTC** | SNVS | coin-cell holder | yes | 18C, 60 |
| **JTAG header** | JTAG | populated | populated | 56 |
| **HDMI out** (RGB→HDMI via SiI902x) | LCDIF + I²C | optional add-on | optional add-on | 55H, 72 |

**Three practical consequences:**

1. **Core-board variant matters more than ALPHA-vs-MINI baseboard.** Both boards accept the same i.MX6ULL "BTB" core-board module. The same core board plugs into either base. There are two flavors of core board, a **NAND** flavor with 256 MiB DDR3L + 256-512 MiB NAND, and an **eMMC** flavor with 512 MiB DDR3L + 8 GiB eMMC. Identify which you have. Chapter 14's DDR3 init values depend on it.
2. **The MINI lacks** the on-board WM8960 audio codec, AP3216C light sensor, ICM-20608 IMU, and CAN transceivers that the ALPHA base carries. The corresponding chapters (53/65 audio, 26/61 I²C+AP3216C, 27/62 SPI+ICM-20608, 66 CAN) still teach the *subsystems*, but the lab requires either skipping or wiring an external part. Each affected chapter calls this out.
3. **Pin assignments for LED, KEY, BEEP, UART1 debug, eMMC, USDHC2 are identical** between ALPHA and MINI. The bare-metal Part II labs work unchanged on both.

If you have a third-party i.MX6ULL board (NXP MCIMX6ULL-EVK, ToraDex Colibri, BoundaryDevices Nitrogen, ...), all chapters apply but the LED/KEY/BEEP pin assignments must be re-derived from your board's schematic. The `bsp/` folder pattern from Chapter 18A makes that a per-folder edit, not a per-chapter rewrite.

## 5.10  Navigating the i.MX6ULL Reference Manual

Revision 1 of the reference manual (IMX6ULLRM) is 5191 pages. Do not read it from beginning to end. Use the following process:

1. **Read Chapter 2 (Memory Maps) once.** It provides the address ranges used throughout this book.
2. **Skim Chapter 1 (Introduction).** It provides the block overview and part variants.
3. **Read Chapter 5 (System Boot)** before Chapter 7 of this book.
4. **For each peripheral, first read:** the overview and block diagram, the initialization sequence, and the descriptions of the registers your code accesses. Read other sections when a specific question requires them.
5. **Keep Chapter 32 (IOMUXC) open in another window.** You will reference it constantly.

## 5.11  Lab

The lab contains two reference-manual lookup exercises.

1. Open the reference manual. Locate, by chapter and page:
   - The **register base address** of UART1.
   - The **CCGR register and bit** that gates UART1's clock.
   - The **GIC SPI ID** for UART1's interrupt.
   - The **IOMUXC MUX_CTL register name** for the pin that carries UART1 TXD on the Point Atom MINI (consult the board schematic).
2. From the same manual, locate the corresponding clock, interrupt, and IOMUX information for **GPIO1_IO03**, the Point Atom user LED pin, and for **I2C1_SDA / I2C1_SCL**.

## 5.12  Pitfalls

- **Reading the wrong manual revision.** NXP issues errata that change register fields. Always check the rev date. This book targets *rev 1, 11/2017*. If you have a newer rev, prefer it but expect minor discrepancies.
- **Believing the i.MX6ULL has a Cortex-M4.** It does not. The bigger i.MX6 SoloX / 7Solo have one. The 6ULL is single-A7 only.
- **Trusting marketing block diagrams.** The block diagram on page 1 of the datasheet omits *most* of the chip. The real block diagram is in Chapter 1 of the reference manual.
- **Assuming all i.MX6ULL parts are the same.** MX6Y2 (full) vs MX6Y1 (-cs, fewer peripherals) vs MX6G2 (lowest-tier) differ in subtle ways. Always cross-check your specific part number's datasheet against the reference manual.

## 5.13  Going deeper

- **IMX6ULLRM**: *i.MX 6ULL Applications Processor Reference Manual* (the 5191-page document).
- **IMX6ULLIEC**: *i.MX 6ULL Industrial Electrical Characteristics* (timings, IO drive characteristics).
- **AN12085**: *Designing a Hardware Solution Based on the i.MX 6UL/6ULL*. NXP's bring-up application note. Concise and useful for hardware engineers.
- **AN12117**: *iMX6ULL Power Consumption Measurement*.
- The **Point Atom MINI schematic** (provided with your board). You will look at this constantly.

> Next chapter: **Chapter 6: The toolchain.** We examine the roles of `gcc`, `ld`, and the other binary utilities.
