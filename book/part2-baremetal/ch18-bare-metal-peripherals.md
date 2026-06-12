---
chapter: 18
title: Optional bare-metal peripherals
part: II - Bare-metal i.MX6ULL
estimated_pages: 22
status: draft
---

# Chapter 18: Optional bare-metal peripherals

> **What:** small, working bare-metal drivers for I²C (read an EEPROM byte), SPI (read a flash JEDEC ID), and a tiny eLCDIF "draw a color bar." Plus a one-section reflection on what's left to do bare-metal vs what we move to U-Boot for.
> **MCU bridge:** Think of U-Boot like a much larger boot stub plus debug monitor: it initializes hardware, loads the next image, and gives you commands before Linux starts.
> **U-Boot:** the bootloader that initializes enough hardware to load and start the Linux kernel.
>
> **Why:** the rest of Part VI will teach these same peripherals inside Linux, where the abstractions are thicker. Touching the raw controllers here, once, makes the Linux drivers feel like simplifications rather than magic.
>
> **Focus:** the driver pattern that repeats: clock, IOMUX, register init, polled state machine, optional IRQ. After writing a few bare-metal drivers, the Linux equivalents look mostly like glue.
> **MCU bridge:** Think of IOMUX like STM32 alternate-function selection, but with separate pad electrical settings and board-level ownership by Device Tree.
> **IRQ:** interrupt request, the signal path that tells the CPU or interrupt controller that hardware needs service.
> **IOMUX:** the pin multiplexer that decides which peripheral function appears on each package pin.


## 18.1  Why this chapter is optional

By Chapter 17 you can do everything Linux requires of a bootloader: clocks, DRAM, exceptions, MMU, caches. If you want, you can skip directly to **Part III, U-Boot**, where we will adopt a real bootloader and never touch bare-metal again.
> **MMU:** Memory Management Unit, hardware that translates virtual addresses to physical addresses and enforces permissions.

What this chapter buys you:

- **Familiarity with the register shape** of three common peripherals before you meet them under Linux.
- **A fall-back debugging skill**: if a Linux driver misbehaves, you can sometimes write a 50-line bare-metal stub to probe the hardware directly and isolate the issue.
- **Confidence that the Linux abstractions are not hiding anything you haven't seen.** Every subsystem callback eventually writes the registers in this chapter.

Read it if you have the appetite. Skip it if you are eager to see U-Boot. After Chapter 18, three more supplementary chapters (**18A** Project organization, **18B** Button + beep, **18C** Bare-metal RTC) extend bare-metal coverage further, those are independent of each other and of Chapter 18. You can read any combination of them.

## 18.2  I²C, read a byte from EEPROM

The Point Atom MINI exposes an I²C-connected EEPROM at I²C address `0x50` on **I2C1**. Pin wiring (from the schematic): I2C1_SCL on pad UART4_RX_DATA (alt 2), I2C1_SDA on UART4_TX_DATA (alt 2). Verify against your specific revision.

I2C1 base = `0x021A0000`. Registers:

| Register | Offset | Purpose |
|----------|--------|---------|
| `IADR` | `+0x00` | Slave own address (we leave 0; master only) |
| `IFDR` | `+0x04` | Frequency divider |
| `I2CR` | `+0x08` | Control |
| `I2SR` | `+0x0C` | Status |
| `I2DR` | `+0x10` | Data (read = RX, write = TX) |

For a master read of one byte at slave register `reg`:

```
START → write {addr<<1 | 0} → ack? → write reg → ack? → repeated START →
write {addr<<1 | 1} → ack? → set TXAK=1 (NAK after next byte) → read I2DR (dummy) →
read I2DR → STOP
```

The "read I2DR" step is doubled: the first read latches the byte, the second returns it.

`i2c.c`:

```c
#include <stdint.h>
#define REG(addr) (*(volatile uint32_t *)(addr))

#define I2C1_BASE 0x021A0000
#define I2C_IADR (I2C1_BASE + 0x00)
#define I2C_IFDR (I2C1_BASE + 0x04)
#define I2C_I2CR (I2C1_BASE + 0x08)
#define I2C_I2SR (I2C1_BASE + 0x0C)
#define I2C_I2DR (I2C1_BASE + 0x10)

#define I2CR_IEN  (1u << 7)   /* I2C enable */
#define I2CR_IIEN (1u << 6)
#define I2CR_MSTA (1u << 5)   /* master mode */
#define I2CR_MTX  (1u << 4)   /* transmit */
#define I2CR_TXAK (1u << 3)   /* transmit ACK = 0; 1 = NAK */
#define I2CR_RSTA (1u << 2)   /* repeated start */

#define I2SR_IBB  (1u << 5)   /* bus busy */
#define I2SR_IIF  (1u << 1)   /* interrupt flag */
#define I2SR_RXAK (1u << 0)   /* received ACK; 0 = ACKed */

static void i2c_wait_iif(void)
{
    while (!(REG(I2C_I2SR) & I2SR_IIF)) {}
    REG(I2C_I2SR) &= ~I2SR_IIF;
}

void i2c_init(void)
{
    /* Clock + IOMUX assumed configured elsewhere (see lab). */
    REG(I2C_IFDR) = 0x1E;     /* IFDR=0x1E → divider 640 → 66 MHz / 640 ≈ 103 kHz.
                                 (IFDR=0x15 would be divider 320 → ~206 kHz — wrong
                                 for standard-mode I²C; the RM Table 31-3 maps the
                                 6-bit IFDR code to a non-monotonic divider list.) */
    REG(I2C_I2CR) = I2CR_IEN; /* enable, master not yet asserted */
}

int i2c_read_byte(uint8_t addr7, uint8_t reg)
{
    /* Wait for bus idle */
    while (REG(I2C_I2SR) & I2SR_IBB) {}

    /* START + transmit address-write */
    REG(I2C_I2CR) = I2CR_IEN | I2CR_MSTA | I2CR_MTX;
    REG(I2C_I2DR) = (uint32_t)(addr7 << 1);
    i2c_wait_iif();
    if (REG(I2C_I2SR) & I2SR_RXAK) return -1;   /* NAK */

    /* Send register address */
    REG(I2C_I2DR) = reg;
    i2c_wait_iif();
    if (REG(I2C_I2SR) & I2SR_RXAK) return -1;

    /* Repeated START + transmit address-read */
    REG(I2C_I2CR) = I2CR_IEN | I2CR_MSTA | I2CR_MTX | I2CR_RSTA;
    REG(I2C_I2DR) = (uint32_t)((addr7 << 1) | 1);
    i2c_wait_iif();
    if (REG(I2C_I2SR) & I2SR_RXAK) return -1;

    /* Receive mode: NAK after this one byte */
    REG(I2C_I2CR) = I2CR_IEN | I2CR_MSTA | I2CR_TXAK;
    (void)REG(I2C_I2DR);      /* dummy read to clock in first byte */
    i2c_wait_iif();

    /* STOP before final read so the slave releases */
    REG(I2C_I2CR) = I2CR_IEN;
    uint8_t v = (uint8_t)REG(I2C_I2DR);
    return v;
}
```

Test from `main()`:

```c
i2c_init();
int v = i2c_read_byte(0x50, 0x00);
if (v < 0) printf("EEPROM not responding\r\n");
else printf("EEPROM[0x00] = 0x%02x\r\n", v);
```

You should see the byte the EEPROM previously held. If the EEPROM is virgin, it likely reads `0xFF`.

## 18.3  SPI, read flash JEDEC ID

ECSPI on i.MX6ULL is a flexible SPI controller, up to 4 chip-selects, configurable word size, FIFO TX/RX. The Point Atom MINI has a SPI flash (W25Q32 or similar) on ECSPI1. Chip-select 0. CPOL=0, CPHA=0. Max ~30 MHz.

ECSPI1 base = `0x02008000`. Registers (the ones we use):

| Register | Offset | Purpose |
|----------|--------|---------|
| `ECSPI_RXDATA` | `+0x00` | RX FIFO (read) |
| `ECSPI_TXDATA` | `+0x04` | TX FIFO (write) |
| `ECSPI_CONREG` | `+0x08` | Main control |
| `ECSPI_CONFIGREG` | `+0x0C` | Per-CS configuration |
| `ECSPI_INTREG` | `+0x10` | Interrupt enables |
| `ECSPI_DMAREG` | `+0x14` | DMA enables |
| `ECSPI_STATREG` | `+0x18` | Status flags |
| `ECSPI_PERIODREG` | `+0x1C` | Inter-burst period |
| `ECSPI_TESTREG` | `+0x20` | Loopback (testing) |

We are not trying to be efficient. We want correctness, so we send and receive one byte at a time.

```c
#define ECSPI1_BASE 0x02008000
#define ECSPI_RXDATA  (ECSPI1_BASE + 0x00)
#define ECSPI_TXDATA  (ECSPI1_BASE + 0x04)
#define ECSPI_CONREG  (ECSPI1_BASE + 0x08)
#define ECSPI_CONFIG  (ECSPI1_BASE + 0x0C)
#define ECSPI_STATREG (ECSPI1_BASE + 0x18)

#define STATREG_TC (1u << 7)
#define STATREG_RR (1u << 3)

void spi_init(void)
{
    /* Clock + IOMUX assumed.  Refer to lab. */
    /* CONREG: enable, master, CHANNEL = 0, burst length = 7 (= 8 bits),
       SMC = 1 (start with TX), PRE_DIV = 4, POST_DIV = 0 -> ~16 MHz from 80 MHz. */
    REG(ECSPI_CONREG) = (0x07 << 20)   /* burst length 8 bits */
                      | (4 << 12)      /* pre-divider */
                      | (1u << 3)      /* SMC: start mode = TXFIFO push */
                      | (1u << 4)      /* MASTER (CHANNEL_MODE for CH0) */
                      | (1u << 0);     /* EN */
    REG(ECSPI_CONFIG) = (1u << 0) | (1u << 12);   /* SS_CTL_0 + SS_POL_0 */
}

uint32_t spi_xfer8(uint8_t tx)
{
    REG(ECSPI_TXDATA) = tx;
    while (!(REG(ECSPI_STATREG) & STATREG_TC)) {}
    REG(ECSPI_STATREG) = STATREG_TC;  /* W1C */
    return REG(ECSPI_RXDATA) & 0xFF;
}

void spi_read_jedec(uint8_t out[3])
{
    spi_xfer8(0x9F);             /* read JEDEC ID */
    out[0] = spi_xfer8(0);
    out[1] = spi_xfer8(0);
    out[2] = spi_xfer8(0);
}
```

Test:

```c
spi_init();
uint8_t id[3];
spi_read_jedec(id);
printf("Flash JEDEC ID: %02x %02x %02x\r\n", id[0], id[1], id[2]);
```

For Winbond W25Q32JV, you should see `EF 40 16`. (`EF` = Winbond, `40 16` = 25Q32 family, 32 Mb.)

## 18.4  eLCDIF, draw a color bar

This is the most board-specific section. The Point Atom MINI's LCD interface and panel vary by revision. Some MINI variants ship with no LCD at all (it's mounted on an optional carrier). If your board lacks an LCD, skip this section.

The high-level recipe:

1. Configure pixel clock (PLL5 / VIDEO PLL, dividers in CCM_CSCDR2).
> **PLL:** Phase-Locked Loop, a clock block that multiplies a reference clock to create faster clocks.
2. Configure the LCD timing parameters: HSYNC/VSYNC widths, front/back porches, active width × height. From your panel datasheet.
3. Configure eLCDIF: data format (24-bit RGB), framebuffer base, line size.
4. Enable eLCDIF. LCD scans the framebuffer continuously.

Pseudocode:

```c
#define LCDIF_BASE     0x021C8000
#define LCDIF_CTRL     (LCDIF_BASE + 0x00)
#define LCDIF_TRANSFER_COUNT (LCDIF_BASE + 0x30)
#define LCDIF_CUR_BUF  (LCDIF_BASE + 0x40)
#define LCDIF_NEXT_BUF (LCDIF_BASE + 0x50)
#define LCDIF_TIMING   (LCDIF_BASE + 0x60)
#define LCDIF_VDCTRL0..4 (LCDIF_BASE + 0x70..)

static uint32_t framebuffer[800 * 480];   /* 1.5 MiB in DRAM */

void lcd_init_color_bars(void)
{
    /* Fill framebuffer with vertical color bars (8 colors, 100 px each). */
    static const uint32_t colors[8] = {
        0xFFFFFFFF, 0xFFFF00FF, 0xFFFFFF00, 0xFF00FFFF,
        0xFFFF0000, 0xFF00FF00, 0xFF0000FF, 0xFF000000
    };
    for (int y = 0; y < 480; y++)
        for (int x = 0; x < 800; x++)
            framebuffer[y * 800 + x] = colors[x / 100];

    /* (lots of register writes for LCD timings ...) */

    REG(LCDIF_NEXT_BUF) = (uint32_t)framebuffer;
    REG(LCDIF_CUR_BUF)  = (uint32_t)framebuffer;
    /* Enable RUN bit in LCDIF_CTRL. */
}
```

A full set of timing values is about 30 register writes for a typical 800×480 RGB panel. They are panel-specific, so we omit them here.

> **Cache caveat.** Because we enabled the D-cache in Chapter 17, our writes to `framebuffer` are cached. The eLCDIF DMA-reads from physical DRAM, it does **not** snoop the L1 cache. Result: the panel shows stale or partial data. Fix: either map the framebuffer as Device memory (slower writes), or call `dcache_clean_range(framebuffer, sizeof(framebuffer))` after each frame update. The same issue under Linux is solved by allocating the framebuffer with `dma_alloc_coherent`, which gives you a non-cached mapping.
> **MCU bridge:** Think of DMA like the MCU DMA controller you used for UART or SPI, but with cache coherency, scatter-gather descriptors, and kernel ownership rules added.
> **DMA:** Direct Memory Access. Hardware moves data to or from memory without the CPU copying each byte.

This is the kind of thing you only discover when you do it bare-metal.

## 18.5  The driver shape that repeats

Look back at the I²C, SPI, and (sketched) LCD drivers. The structure is the same:

```
1. enable_clock()          // CCGR write
2. configure_iomux()       // pad mux + SELECT_INPUT
3. reset_controller()      // optional soft reset, wait for clear
4. configure_registers()   // mode, baud, format
5. transfer_function()     // polled state machine, or IRQ-driven
6. teardown()              // disable on shutdown (we usually skip on bare metal)
```

Every peripheral in this book, and every Linux driver in Part VI, follows this shape. The Linux abstractions (`platform_driver`, `i2c_driver`, `spi_driver`) hide the boilerplate, but the underlying register choreography is identical. Doing it raw once removes the mystery.

## 18.6  Why the required-path ends here

Part II's purpose was to remove the magic between you and the chip. We have done that:

- We can build a Boot ROM-acceptable image (Ch 11).
- We can talk over UART (Ch 12).
- We can bring up the clock tree (Ch 13).
- We can initialize DRAM and run from it (Ch 14).
- We can install exception vectors and handle interrupts (Ch 15).
- We can measure time (Ch 16).
- We can drive the MMU and caches (Ch 17).
- We can talk to peripherals over I²C, SPI, and LCD (Ch 18).

Every one of these is what U-Boot does internally, and what Linux's early-boot path does on top of U-Boot. We could keep going, write Ethernet drivers, USB stacks, filesystem code, all bare-metal. People have done this. It is called LK or Zephyr.

But the marginal lesson per chapter is diminishing for the *required* path. From here on, the productive move is to **adopt U-Boot** and learn it by reading. Part III is built around exactly that: build mainline U-Boot, then read its source until every line maps back to something you wrote yourself in Chapters 9–17.

Three **supplementary** chapters follow this one before Part III opens:

- **Chapter 18A, Project organization.** Refactor the monolithic Part II code into a BSP folder tree. Introduce `imx6ull.h` as the single source of truth for register addresses. Sidebar on the NXP SDK header style.
> **BSP:** Board Support Package: vendor patches, configs, bootloader files, and scripts needed to boot one board.
- **Chapter 18B, Button input and beep.** A polled GPIO input with debouncing, and a polled square-wave buzzer driver.
> **MCU bridge:** Think of Linux GPIO like the same pin set/reset block you used on STM32, but accessed through a kernel subsystem that owns numbering, direction, interrupts, and user-space exposure.
> **GPIO:** General-Purpose Input/Output, a pin controlled as a digital input, output, or interrupt source.
- **Chapter 18C, Bare-metal RTC.** Talk to the SNVS always-on domain. Demonstrate brown-out-survival via VBAT.

Read any combination. They are independent. If you are eager to see U-Boot, skip them and come back later, they pay back when you need them, not at first read.

This is how the rest of the book uses the bare-metal foundation: not as a thing we keep building on, but as a **mental rosetta stone** for understanding the higher layers.

## 18.7  Lab

Pick at least one:

1. **I²C EEPROM read + write.** Extend `i2c_read_byte` to `i2c_write_byte`. Write `0xAA` to address `0x00`. Power-cycle. Read it back. Confirm.
2. **SPI flash dump.** Read the first 256 bytes of the SPI flash. Print as a hex dump. Identify any U-Boot environment or magic numbers at the start.
3. **LCD color bars.** If you have the LCD carrier, draw the color bars. Then add a moving pixel (XOR a single pixel position each frame. `mdelay(16)` between frames). Note the cache-flush requirement.
4. **All three together.** A bare-metal program that, on startup: reads EEPROM byte 0. Treats it as a color index. Draws that color across the whole LCD. Three peripherals, one program.

## 18.8  Pitfalls

- **I²C: forgetting to W1C the IIF flag.** Spins forever.
- **I²C: ACK polling.** When a slave is busy (e.g., EEPROM during a write), it NAKs. Production code retries.
- **SPI: chip-select timing.** Some flashes need CS to assert before the first clock and de-assert after the last. The MMC mode "SMC" automates this if your CONREG is right.
- **SPI: byte order.** Reading 4 bytes into a 32-bit RX register gives them in *MSB-first* order, but `& 0xFF` returns the last byte, which is the *first* over the wire. Easy to confuse on multi-byte transfers.
- **LCDIF: cache vs DMA.** Discussed in §18.4. Defining moment for understanding why `dma_alloc_coherent` exists.
- **All peripherals: CCGR omission.** Always.

## 18.9  Going deeper

- **IMX6ULLRM Chapter 31 (I²C)**, Chapter 21 (ECSPI), Chapter 23 (eLCDIF).
- **AN5050**: *Using the i.MX I²C Peripheral*.
- **Linux source: `drivers/i2c/busses/i2c-imx.c`**: same hardware, full implementation. Read after this chapter.
- **Linux source: `drivers/spi/spi-imx.c`**: same.
- **Linux source: `drivers/video/fbdev/mxsfb.c`**: eLCDIF driver.

---

**End of the required path through Part II.**

You have written, by hand, a complete bare-metal stack from reset vector to interrupt-driven peripherals running from DRAM with MMU and caches on. Come back to Chapters 9–18 whenever something deep goes wrong in Parts III–VII.

> **Next, choose:** read one or more of the supplementary chapters **18A** (Project organization), **18B** (Button + beep), **18C** (Bare-metal RTC), or skip directly to **Part III, Chapter 19, U-Boot, from source, first boot.** Next we read U-Boot and see how a production bootloader packages the same work.
