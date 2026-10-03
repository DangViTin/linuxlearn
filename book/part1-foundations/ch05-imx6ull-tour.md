# Chapter 5: A tour of the i.MX6ULL SoC

Knowing the Cortex-A7 registers does not yet tell us how to light an LED. We also need the GPIO block's address, its clock, and the pin connected to the LED. A UART raises the same questions. On a new MCU you would look for these in its reference manual and schematic; the i.MX6ULL uses the same approach, spread across a larger chip.

This chapter gives us a map for that search. We will separate the CPU core from the rest of the SoC, follow the clock and pin paths, then work through a UART1 lookup. The aim is not to memorize a peripheral catalog. It is to know where to start when the next lab names a block you have not used before.

## 5.1  What is the i.MX6ULL

The i.MX6ULL is a **system on chip**, or SoC: the CPU core is one part of a device that also includes memory controllers, clocks, and peripherals. It is a low-cost member of NXP's i.MX6 family, with one Cortex-A7 and no GPU, VPU, or PCIe controller.

Many of its peripheral names will be familiar: UART, I2C, SPI, timers, and GPIO. Others serve the larger system: the external DDR controller, Ethernet, USB, and storage interfaces. The chip also provides LCD, CSI camera, and SAI audio interfaces. These resources suit systems such as industrial control panels, meters, and gateways.

Keep the following summary nearby as we examine the map. Where a resource depends on the part variant or fitted components, check the actual board rather than relying on the MINI name alone:

- **Core:** one Cortex-A7; permitted frequency depends on the fitted part's speed grade and supplies.
- **L1 cache:** 32 KB I + 32 KB D
- **L2 cache:** 128 KB unified, integrated inside the Cortex-A7 MPCore (no external PL310 controller)
- **On-chip memory:** 128 KB **OCRAM** at `0x00900000`, plus a separate 96 KB **Boot ROM** at `0x00000000` that is mask-programmed by NXP. There is **no TCM**. A-profile systems normally use caches and system RAM instead.
- **DRAM:** 16-bit LPDDR2/DDR3L/DDR3 controller (MMDC). The Point Atom core boards used in this book have 256 MiB or 512 MiB.
- **Boot media:** SD/MMC, eMMC, NAND, SPI NOR, QSPI, parallel NOR, and USB SDP recovery
- **Process:** 28 nm
- **Package:** BGA289 / BGA324 (depending on variant)

Before choosing a clock or a peripheral lab, read the chip's full marking. `Y` identifies i.MX6ULL, while `G` identifies i.MX6UL; those are different families, not price grades of the same part. Within ULL, the `Y0`, `Y1`, and `Y2` differentiators identify baseline, reduced-feature, and full-feature variants.

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

The useful result of decoding this example is the `05` speed grade: 528 MHz. The schematic describes its design, but you must still check the marking fitted on your board. **Do not apply a 696 MHz example to a 528 MHz-grade part.** Even a higher-grade part needs the documented voltage and temperature conditions for its chosen frequency.

## 5.2  Block diagram

Here is a simplified view of how the major blocks connect. Some buses are omitted so we can follow the path from the CPU to memory and peripherals:

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

The **bus matrix** carries accesses from a master, such as the CPU or a DMA engine, to a target, such as RAM or a peripheral bridge. A register write is therefore not a write into the CPU core itself: it travels to the addressed block. We rarely configure the matrix in the first labs, but this distinction helps us read the physical memory map.

## 5.3  System memory map

Where does a CPU load or store go? The physical address selects a region in the SoC's 4 GiB map. Some regions contain memory, others contain registers, and others are reserved. This selected-region table follows RM Tables 2-1 through 2-4; an address marked reserved is not spare space for our code.

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

For the early labs, three parts of the map are especially useful. First, **DRAM begins at `0x80000000`**. A U-Boot setting such as `loadaddr=0x80800000` therefore places an image 8 MiB above that base, leaving working space around it. Remember that this is external memory and needs initialization before use.

Second, **OCRAM begins at `0x00900000`**. This is on-chip SRAM, available before DDR has been configured. Our first bare-metal images use it. A small U-Boot **SPL**, or Secondary Program Loader, can also run here, initialize DDR, and load a larger next stage. The full 128 KB is not all available while the ROM is still loading, as the next section explains.

Third, most peripheral registers lie in **AIPS-1, AIPS-2, or AIPS-3**. For example, the Clock Controller Module, **CCM**, starts at `0x020C4000`, inside AIPS-1. The high address digits help you identify the containing region, but use the block's own register table for the exact address.

The full map is RM Chapter 2. In particular, `0x00018000-0x000FFFFF`, `0x00100000-0x00107FFF`, and the region containing `0x08000000` are reserved, not the ROM aliases or EIM base sometimes listed for other configurations.

## 5.4  OCRAM and the boot footprint

Our first program needs both code space and a stack. It is tempting to budget all 128 KB of OCRAM, but the Boot ROM uses some of that memory during loading. RM 8.4.1, Figure 8-3 gives the boundaries below; it does not assign further subdivisions within the lower reservation.

| Start | End | Approx size | During Boot ROM execution | What it means for us |
|-------|-----|-------------|---------------------------|----------------------|
| `0x00900000` | `0x00906FFF` | 28 KiB | Reserved. | Do not load over it while ROM is active. |
| `0x00907000` | `0x00917FFF` | 68 KiB | OCRAM free area. | Image headers, loaded payload, and any concurrent allocations must fit. |
| `0x00918000` | `0x0091FFFF` | ~32 KB | ROM MMU table, stack, and per-boot state. | Reserved until the ROM has handed off. |

During Boot ROM execution, the usable window is the ~68 KB middle range. **After the ROM transfers control and its services are no longer needed**, software can use the entire 128 KB OCRAM range, `0x00900000`-`0x0091FFFF`.

That gives our loader a different limit from the physical memory limit: loaded bytes must remain below `0x00918000`, not merely below `0x00920000`. In the first padded image, we use `0x00907000` as the image base, `0x00907400` for the IVT header, and `0x00908000` for the code entry. Chapters 6 and 7 show how those choices fit together.

Always budget the actual image and stack. Memory we may reclaim after the ROM has handed over control is not memory we may overwrite while it is still using it.

## 5.5  The clock tree (at one level of detail)

Finding a register address answers only part of the peripheral question. A block also needs its clock. Instead of beginning with the full clock tree and its roughly 200 leaf signals, follow one path from a source to a peripheral:

```
External oscillators ─► PLLs (ANATOP) ─► Root clocks (CCM) ─► Gates (CCGR) ─► Peripherals
```

### Layer 1, Oscillators

- **XTALOSC24M**: the 24 MHz crystal reference for the main clock tree. The Point Atom MINI has a 24 MHz crystal on Y2.
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

A **PLL**, or Phase-Locked Loop, produces faster clocks from a reference. PLL2 and PLL3 also expose four **PFDs**, Phase Fractional Dividers, per PLL. These provide divided outputs; PLL2_PFD2 at 396 MHz, for example, is commonly used as a source in the AHB clock path.

### Layer 3, Root clocks (in CCM)

The CCM selects among PLL and PFD outputs and applies dividers to produce named **root clocks**. Names such as `AHB_CLK_ROOT`, `IPG_CLK_ROOT`, and `UART_CLK_ROOT` tell you which part of the system they serve. There are roughly 60 of these roots; we follow the one needed by a peripheral rather than configuring them all at once.

The following rates illustrate a later configuration, subject to the fitted part's limits. They are not the frequencies to assume just after reset:

- ARM core: 696 MHz (PLL1)
- AXI bus: 198 MHz (PLL2_PFD2 / 2)
- AHB: 132 MHz
- IPG (peripheral bus): 66 MHz
- UART input: 80 MHz (PLL3 / 6)

Chapter 13 performs the explicit clock setup. Before then, our ROM-loaded program inherits the ROM's starting state described in RM 8.4.3, not a configuration from U-Boot. When checking a frequency, follow its source and divider: a PLL's output rate is not necessarily the rate reaching the CPU or peripheral.

### Layer 4, Gates (CCGR0..CCGR6)

Every peripheral has a **gate bit** (or pair of bits) in one of seven `CCM_CCGRx` registers. The bits have three possible values:

- `00`: clock off in all modes
- `01`: clock on in run mode only, off in WAIT/STOP
- `11`: on in RUN and WAIT; STOP behavior follows the documented CCM/low-power conditions.

Bare-metal examples often select `11`. Production code selects a state according to the peripheral's run, wakeup, and low-power requirements; `01` is not a universal production setting.

The mapping of peripheral to CCGR bit lives in the reference manual's CCM chapter, Table 18-5. You will visit that table dozens of times during this book.

If a peripheral's registers give unexpected values or writes seem to have no effect, check its clock gate early. An address can be correct while the block behind it is not receiving the clock it needs.

## 5.6  IOMUX, the universal multiplexer

Even a clocked UART cannot print if its signal never reaches the connected pin. Most package **pads**, the chip's external signal connections, can carry several alternate functions. A pad might offer GPIO, UART, I2C, Ethernet, or a timer signal. The **IOMUX**, the I/O multiplexer, selects which function reaches it.

Do not choose a setting from another pad just because its name looks similar. Each pad has its own ALT table in the reference manual's IOMUXC chapter.

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

Notice that these controls answer separate questions. MUX_CTL selects the function, PAD_CTL sets electrical behavior, and SELECT_INPUT, where present, chooses the input route. A missing signal can come from any of them, even if the peripheral's own registers are correct. Check them after the clock path when debugging a silent device.

The IOMUX tables occupy about 300 pages, but each experiment uses only a few pads. The schematic tells you which pad to search for; its table tells you the setting to use.

## 5.7  Power domains and the SNVS

Clocks and pads also depend on the board's supplies. Three names recur in the power and low-power chapters:

- **VDD_SOC**: main digital supply (the part you turn off in deep sleep).
- **VDD_ARM**: the CPU core supply, allowing voltage and frequency to be adjusted together. This is called dynamic voltage and frequency scaling, or **DVFS**.
- **SNVS**: Secure Non-Volatile Storage, including RTC, security state, tamper inputs, and retained registers. For example, `SNVS_LPGPR` is a 32-bit retained general-purpose register [RM 48.7.14], not a general byte-addressable SRAM. Retention requires its supply to remain present; board battery wiring matters.

This book first uses SNVS for its real-time clock and retained registers. Later chapters also discuss its security and low-power functions.

## 5.8  Fuses and identification

Some settings outlast both a reset and removal of power. The **OCOTP** block exposes one-time-programmable fuse fields and their shadow registers. NXP's programmed chip identity is different from fields a manufacturer may provision for boot, security, or a MAC address, and from the locks protecting those fields [RM Chapter 5]. A MAC slot can be unprogrammed, with the board obtaining its address elsewhere.

Reading a shadow register does not program a fuse. This symbolic example reads identity fields only:

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

Use this as a lookup table when one of these names appears in a lab. The chapter links explain its use in the book; the RM column takes you to the register definitions.

## 5.9a  Board revisions and available labs

The chip's catalog does not tell us what is usable on every board. There are three separate checks: whether the SoC supports the function, whether the required part is fitted on the core board, and how the baseboard connects it.

Our reference documents are the MINI v2.2 schematic and the core schematic with internal project title `CL6Y2CB_V1.9`, distributed under a CORE v2.0 filename. Compare the internal titles with your PCB silkscreen. The table below shows what to check before using each lab:

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

We have used several parts of revision 1 (11/2017) of IMX6ULLRM. Its 4,127 pages are easier to navigate when you give each search a purpose:

1. **Start with Chapter 2 (Memory Maps)** when you need to locate a block's address range.
2. **Use Chapter 1 (Introduction)** for the block overview and part variants.
3. **Keep Chapter 8 (System Boot) beside Chapter 7 of this book** for boot-mode and image-format questions. RM Chapter 5 is Fusemap, not System Boot.
4. **For each peripheral, first read:** the overview and block diagram, the initialization sequence, and the descriptions of the registers your code accesses. Read other sections when a specific question requires them.
5. **Keep Chapter 32 (IOMUXC) open in another window.** You will reference it constantly.

## 5.11  Lab

Use UART1 to practice the address, clock, interrupt, and pad search as one connected task. The worked answer follows, so try the lookup first and then compare how you got there:

1. Open the reference manual. Locate, by chapter and page:
   - The **register base address** of UART1.
   - The **CCGR register and bit** that gates UART1's clock.
   - The **GIC SPI ID** for UART1's interrupt.
   - The **IOMUXC MUX_CTL register name** for the pin that carries UART1 TXD on the Point Atom MINI (consult the board schematic).
2. From the same manual, locate the corresponding clock, interrupt, and IOMUX information for **GPIO1_IO03**, the Point Atom user LED pin, and for **I2C1_SDA / I2C1_SCL**.

### Worked UART1 lookup and answer check

Start with **where**: RM Chapter 2 places UART1 at `0x02020000`, within AIPS-1. This locates the controller's registers, not the pins on the board.

Next find **its clock gate**. In the CCM chapter, UART1 uses `CCM_CCGR5.CG12`, bits 25:24, at register address `0x020C407C` [RM 18.6.28]. This is the gate field our code must select, not a UART baud-rate register.

For **the interrupt**, RM Chapter 3 gives UART1 GIC SPI index 26. Adding the GIC's architectural SPI base of 32 gives interrupt ID 58, using the distinction from Chapter 4.

Finally, follow **the board connection**. In the MINI v2.2 schematic, trace UART1 TX/RX to the bridge and package pads. TX uses `IOMUXC_SW_MUX_CTL_PAD_UART1_TX_DATA`. Look up its ALT setting in RM Chapter 32 instead of inferring a mux value from the UART controller's name.

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

We now know how to find a peripheral's place in the chip and its connection to the board. Next we turn back to the host: Chapter 6 follows a source file through compilation and linking, so we can see how the tools place our code into the memory we have just examined.
