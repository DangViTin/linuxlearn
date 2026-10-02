# Chapter 5: A tour of the i.MX6ULL SoC
> **What:** a top-down map of the chip, what blocks are inside it, where they live in memory, how they are clocked, and how their pins are routed.
>
> **Why:** every later chapter will name a peripheral. For each one you should be able to find it on the block diagram, locate its register base, find its clock root and gate bit, and know what pin it lands on. All of that in a few minutes.
>
> **Focus:** learn how to look up an address, clock, and pad function. These patterns transfer to other SoCs; the addresses, fields, and electrical constraints do not transfer unchanged.

> **IOMUX:** the pin multiplexer that decides which peripheral function appears on each package pin.


## 5.1  What is the i.MX6ULL

The i.MX6ULL is a low-cost member of NXP's i.MX6 family. It has one Cortex-A7 core and no GPU, VPU, or PCIe controller. It still provides Ethernet, USB, LCD, CSI camera, SAI audio, eMMC, NAND, QSPI, eight UARTs, four I²C controllers, and four ECSPI controllers. It targets applications such as industrial HMIs, point-of-sale terminals, smart meters, and gateways.

Key parameters of the part variant used on Point Atom MINI:

- **Core:** one Cortex-A7; permitted frequency depends on the fitted part's speed grade and supplies.
- **L1 cache:** 32 KB I + 32 KB D
- **L2 cache:** 128 KB unified, integrated inside the Cortex-A7 MPCore (no external PL310 controller)
- **On-chip memory:** 128 KB **OCRAM** at `0x00900000`, plus a separate 96 KB **Boot ROM** at `0x00000000` that is mask-programmed by NXP. There is **no TCM**. A-profile systems normally use caches and system RAM instead.
- **DRAM:** 16-bit LPDDR2/DDR3L/DDR3 controller (MMDC). The Point Atom core boards used in this book have 256 MiB or 512 MiB.
- **Boot media:** SD/MMC, eMMC, NAND, SPI NOR, QSPI, parallel NOR, and USB SDP recovery
- **Process:** 28 nm
- **Package:** BGA289 / BGA324 (depending on variant)

`Y` identifies the i.MX6ULL family; `G` identifies i.MX6UL, not a cheaper ULL tier. ULL differentiators include baseline (`Y0`), reduced-feature (`Y1`), and full-feature (`Y2`) variants. Use the complete marking and its matching datasheet, not a short prefix, to decide capabilities.

For example, the supplied core schematic labels U1 `MCIMX6Y2CVM05AB`:

| Field | Meaning in the supplied industrial datasheet |
|---|---|
| `MC` | Production qualification |
| `IMX6Y` | i.MX6ULL family |
| `2` | Full-feature differentiator |
| `C` | Industrial junction-temperature grade |
| `VM` | 14 x 14 mm MAPBGA package |
| `05` | 528 MHz speed grade |
| `A` | Fuse-option field |
| `B` | Silicon revision 1.1 |

That schematic label is not proof of the chip fitted on your board. Record its actual marking. **Do not apply a 696 MHz example to a 528 MHz-grade part.** A higher speed-grade limit also requires the documented voltage and temperature conditions; raising a PLL is not permission to overclock.

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

The i.MX6ULL exposes a 4 GiB physical address space. Use this selected-region table as a lookup aid, checked against RM Tables 2-1 through 2-4. Reserved addresses are not free peripheral space.

| Region | Base | Size | What's there |
|--------|------|------|--------------|
| **Boot ROM** | `0x00000000` | 96 KB | NXP's mask-programmed boot code (see Ch 7) |
| **OCRAM** | `0x00900000` | 128 KB | On-chip SRAM |
| GIC distributor | `0x00A01000` | 4 KB | (and CPU interface at `0x00A02000`) |
| External PL310 L2 controller | (absent) | - | i.MX6ULL's 128 KB L2 is integrated in the MPCore block. |
| **AIPS-1** | `0x02000000` | 1 MB region | Includes GPIO, UART1, IOMUXC, CCM/analog clocks, GPT/EPIT, SNVS |
| **AIPS-2** | `0x02100000` | 1 MB region | Includes USB, MMDC, USDHC and other peripheral blocks |
| **AIPS-3** | `0x02200000` | 1 MB region | Includes DCP, RNGB, UART8, EPDC and related blocks |
| **External Memory Interface (EIM)** | `0x50000000` | 128 MB | Parallel external memory; alias at `0x58000000` |
| **QSPI** | `0x60000000` | 256 MB | Memory-mapped QuadSPI flash |
| **MMDC0 (DRAM)** | `0x80000000` | up to 2 GB | External DDR3 |

A few things worth committing to long-term memory:

1. **The DRAM address range starts at `0x80000000`.** A U-Boot script may set `loadaddr=0x80800000`, which is 8 MiB above the DRAM base. The offset leaves working space around the loaded image.
> **U-Boot:** the bootloader that initializes enough hardware to load and start the Linux kernel.
2. **OCRAM at `0x00900000`** is where the Boot ROM places your SPL and where bare-metal images live before DRAM is up. 128 KB is enough for a substantial bootloader stage.
> **SPL:** Secondary Program Loader, a tiny first U-Boot stage that fits in OCRAM and initializes DDR.
3. **Most peripheral registers live in AIPS-1, AIPS-2, or AIPS-3.** For example, CCM at `0x020C4000` is inside the AIPS-1 range that starts at `0x02000000`. The high address digits help identify the containing region.
> **CCM:** Clock Controller Module. It selects clock sources, dividers, and gates for the SoC.

The full map is RM Chapter 2. In particular, `0x00018000-0x000FFFFF`, `0x00100000-0x00107FFF`, and the region containing `0x08000000` are reserved, not the ROM aliases or EIM base sometimes listed for other configurations.

## 5.4  OCRAM and the boot footprint

The Boot ROM uses part of OCRAM while loading. RM 8.4.1, Figure 8-3 gives these boundaries; do not invent additional subdivisions of the lower reservation:

| Start | End | Approx size | During Boot ROM execution | What it means for us |
|-------|-----|-------------|---------------------------|----------------------|
| `0x00900000` | `0x00906FFF` | 28 KiB | Reserved. | Do not load over it while ROM is active. |
| `0x00907000` | `0x00917FFF` | 68 KiB | OCRAM free area. | Image headers, loaded payload, and any concurrent allocations must fit. |
| `0x00918000` | `0x0091FFFF` | ~32 KB | ROM MMU table, stack, and per-boot state. | Reserved until the ROM has handed off. |

During Boot ROM execution, the usable window is the ~68 KB middle range. **After the ROM transfers control and its services are no longer needed**, software can use the entire 128 KB OCRAM range, `0x00900000`-`0x0091FFFF`.

The exclusive upper load limit is `0x00918000`, not the physical OCRAM end `0x00920000`. Check actual image and stack sizes rather than assuming a program will fit. The first padded image uses base `0x00907000`, IVT `0x00907400`, and code entry `0x00908000`; Chapters 6-7 distinguish that header space from linked code. Reclaiming the top area after handoff is different from loading bytes there while the ROM is still running.

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

| PLL | Example output/rate | Purpose |
|-----|--------------|---------|
| PLL1, ARM PLL | Depends on DIV_SELECT | Feeds ARM root through downstream division; not automatically the final core rate |
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

One later configuration, subject to the fitted part's limits (not a reset guarantee):

- ARM core: 696 MHz (PLL1)
- AXI bus: 198 MHz (PLL2_PFD2 / 2)
- AHB: 132 MHz
- IPG (peripheral bus): 66 MHz
- UART input: 80 MHz (PLL3 / 6)

Chapter 13 explicitly configures clocks. Before that, our ROM-loaded program inherits the ROM starting state described in RM 8.4.3; U-Boot has not run on this path. Always distinguish PLL output from a divided root frequency.

### Layer 4, Gates (CCGR0..CCGR6)

Every peripheral has a **gate bit** (or pair of bits) in one of seven `CCM_CCGRx` registers. The bits have three possible values:

- `00`: clock off in all modes
- `01`: clock on in run mode only, off in WAIT/STOP
- `11`: on in RUN and WAIT; STOP behavior follows the documented CCM/low-power conditions.

Bare-metal examples often select `11`. Production code selects a state according to the peripheral's run, wakeup, and low-power requirements; `01` is not a universal production setting.

The mapping of peripheral to CCGR bit lives in the reference manual's CCM chapter, Table 18-5. You will visit that table dozens of times during this book.

**The most common NXP bring-up pitfall:** forgetting to enable a peripheral's clock gate. Symptom: the peripheral's registers read as zero or unexpected values, and writes have no effect. Always check the gate first.

## 5.6  IOMUX, the universal multiplexer

Most package pads can carry several alternate functions. Depending on the pad, the choices may include GPIO, UART, I²C, Ethernet, USB control, timer output, or camera signals. Each pad has its own ALT table, so always look up the exact pad in the IOMUXC chapter of the reference manual.

The **IOMUXC** (IO Multiplexer Controller) block contains, for every pin:

- A **MUX_CTL** register selecting which ALT (and a few other bits, SION, "Software Input On", which forces the pad's input buffer on even when output-driven).
- A **PAD_CTL** register controlling drive strength, slew rate, pull-up/down, hysteresis, open-drain.
- Some input functions also require a **SELECT_INPUT** register. This register chooses which eligible pad feeds the peripheral input. NXP calls this selection a "daisy chain."

A typical pin setup is two writes, sometimes three. The following symbolic register pseudocode is not a standalone C program:

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
- **SNVS**: Secure Non-Volatile Storage, including RTC, security state, tamper inputs, and retained registers. For example, `SNVS_LPGPR` is a 32-bit retained general-purpose register [RM 48.7.14], not a general byte-addressable SRAM. Retention requires its supply to remain present; board battery wiring matters.

This book first uses SNVS for its real-time clock and retained registers. Later chapters also discuss its security and low-power functions.

## 5.8  Fuses and identification

The **OCOTP** block exposes fuse fields and shadow registers. NXP-programmed unique identity differs from OEM-programmable boot/security/MAC fields and their locks [RM Chapter 5]. MAC slots may be unprogrammed; a board can obtain its address from another provisioning source. Reading shadow registers does not program fuses. The following is read-only symbolic pseudocode:
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
| Analog CCM (ANATOP) | 18.7 | PLL registers, Ch 5, 13 |
| IOMUXC | 32 | Pin mux, every peripheral chapter |
| GPIO | 28 | 5 GPIO banks × 32 = 160 pins, Ch 9, 44 |
| GIC | (ARM TRM) | Interrupt controller, Ch 4, 15 |
| GPT | 30 | General-purpose timer, Ch 16 |
| EPIT | 24 | Enhanced periodic interrupt timer, Ch 16 |
| UART | 55 | 8 UARTs, IrDA-capable, Ch 12 |
| I²C | 31 | 4 I²C controllers, Ch 46 |
| ECSPI | 20 | 4 SPI controllers, Ch 47 |
| USDHC | 58 | SD/MMC and boot media, Ch 11 |
| MMDC | 35 | DDR controller, Ch 14 |
| FEC | 22 | Ethernet MAC, Ch 52 |
| USB | 56 | OTG + host, Ch 55 |
| eLCDIF | 34 | LCD controller, Ch 54 |
| CSI | 19 | Camera input, optional |
| SAI | 45 | Audio I²S, Ch 53 |
| ADC | 13 | 12-bit, 10 channels, Ch 49 |
| PWM | 40 | PWM, Ch 48 |
| SNVS | 48 | RTC + secure storage, Ch 48 |
| OCOTP | 37 | Fuses |
| WDOG | 59 | Watchdog |
| GPC | 27 | Power controller |
| SRC | 51 | System reset controller |

That table is the rough sequence of when we meet each peripheral. Bookmark it.

## 5.9a  Board revisions and available labs

Separate **SoC capability**, **core-board parts**, and **baseboard wiring**. The reference documents used here are the MINI v2.2 schematic and the core schematic whose internal project title is `CL6Y2CB_V1.9` (the distributed filename says CORE v2.0). Check those internal titles and your PCB silkscreen; a filename is not a universal BOM.

| Hardware in the reference setup | What to check | Relevant lab |
|---|---|---|
| User LED, GPIO1_IO03 | Pad and active level | [Assembly LED](../part2-baremetal/ch09-asm-led.md) |
| KEY/BEEP | GPIO1_IO18 / GPIO5_IO01 and schematic circuit | [Button and beep](../part2-baremetal/ch18B-button-beep.md) |
| Built-in UART1 bridge | TX/RX pads, bridge identity, power path | [UART](../part2-baremetal/ch12-uart-printf.md) |
| DDR3L on core | Schematic names `NT5CC256M16EP-EK`; compare fitted marking and topology | [DDR initialization](../part2-baremetal/ch14-ddr3-init.md) |
| eMMC on core | Schematic names `KLM8G1GETF`; verify fitted storage | [SD/eMMC](../part7-cookbook/ch66-sd-emmc.md) |
| Ethernet | Actual FEC routing, PHY, reset, reference clock | [FEC driver](../part6-drivers/ch52-network-fec.md), [dual Ethernet](../part7-cookbook/ch115-dual-fec-eth.md) |
| LCD/add-on display | Connector, panel supply, timings and touch controller | [RGB LCD](../part7-cookbook/ch82-rgb-lcd.md), [HDMI bridge](../part6-drivers/ch55H-hdmi-bridge.md) |
| RTC supply | SNVS/battery wiring | [Bare-metal RTC](../part2-baremetal/ch18C-baremetal-rtc.md), [external RTC](../part7-cookbook/ch117-external-rtc.md) |
| JTAG connector | Population and adapter wiring | [JTAG debugging](../part8-debug/ch118-jtag-openocd-gdb.md) |

ALPHA baseboards and NAND cores are revision-dependent alternatives, not verified equivalents of this schematic set. Before doing their labs, obtain their matching schematic/BOM and identify the fitted components. Audio, CAN, light sensors, IMUs, Wi-Fi, and modems may require add-ons: see [audio codecs](../part7-cookbook/ch89-audio-codecs.md), [CAN](../part6-drivers/ch55C-can-flexcan.md), [light sensors](../part7-cookbook/ch68-light-color.md), [SPI IMUs](../part7-cookbook/ch71-spi-imus.md), [SDIO Wi-Fi](../part7-cookbook/ch91-sdio-wifi.md), and [USB modems](../part7-cookbook/ch102-usb-lte.md). RS485 and GPS are covered in [RS485/Modbus](../part7-cookbook/ch108-rs485-modbus.md) and [GPS/PPS](../part7-cookbook/ch107-gps-pps.md).

For another board, re-derive power/reset policy, oscillator sources, DDR topology/timings, boot-storage routing, PHY wiring, and pin assignments. The [board-directory pattern](../part2-baremetal/ch18A-project-organization.md) organizes those differences; it does not make incompatible hardware work unchanged. Do not use Chapter 14's DDR values without that comparison.

## 5.10  Navigating the i.MX6ULL Reference Manual

Revision 1 (11/2017) of IMX6ULLRM has 4,127 PDF pages. Use the following process:

1. **Read Chapter 2 (Memory Maps) once.** It provides the address ranges used throughout this book.
2. **Skim Chapter 1 (Introduction).** It provides the block overview and part variants.
3. **Read Chapter 8 (System Boot)** before Chapter 7 of this book; Chapter 5 is Fusemap.
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

### Worked UART1 lookup and answer check

Start in RM Chapter 2: UART1 is at `0x02020000`, within AIPS-1. In CCM, find `CCM_CCGR5.CG12`, bits 25:24, register address `0x020C407C` [RM 18.6.28]. In Chapter 3, UART1 has GIC SPI index 26; adding the architectural SPI base 32 gives interrupt ID 58. In the MINI v2.2 schematic, follow UART1 TX/RX to the bridge and the package pads. TX uses `IOMUXC_SW_MUX_CTL_PAD_UART1_TX_DATA`; check its ALT setting in Chapter 32, rather than inferring it from the UART controller's name.

Use the same chain for the LED and I2C: address -> clock -> interrupt -> pad -> board net. Record both register names and manual locations so another reader can reproduce your lookup.

## 5.12  Pitfalls

- **Ignoring document and silicon revisions.** This book cites RM rev. 1, 11/2017. Check errata for your silicon mask; they can document behavior or workarounds without changing a field definition. Compare newer manuals explicitly rather than silently mixing section numbers.
- **Believing the i.MX6ULL has a Cortex-M4.** It does not. The bigger i.MX6 SoloX / 7Solo have one. The 6ULL is single-A7 only.
- **Trusting marketing block diagrams.** The block diagram on page 1 of the datasheet omits *most* of the chip. The real block diagram is in Chapter 1 of the reference manual.
- **Treating UL/ULL or speed grades as interchangeable.** `G` and `Y` name different families. Decode the complete ULL marking and its feature/speed grade before choosing a clock or peripheral lab.

## 5.13  Going deeper

- **IMX6ULLRM**: *i.MX 6ULL Applications Processor Reference Manual*, rev. 1, 11/2017.
- **IMX6ULLIEC**: *i.MX 6ULL Industrial Electrical Characteristics* (timings, IO drive characteristics).
- **IMX6ULLHDG**: *i.MX6ULL Hardware Development Guide*, available in [NXP's i.MX6ULL documentation](https://www.nxp.com/products/i.MX6ULL?linkline=Data+Sheet). Check the document's actual title/revision before using a cited application-note number.
- The **Point Atom MINI schematic** (provided with your board). You will look at this constantly.

> Next chapter: **Chapter 6: The toolchain.** We examine the roles of `gcc`, `ld`, and the other binary utilities.
