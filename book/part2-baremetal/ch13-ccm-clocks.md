---
chapter: 13
title: CCM clock tree bring-up
part: II — Bare-metal i.MX6ULL
estimated_pages: 22
status: draft
---

# Chapter 13 — CCM clock tree bring-up

> **What:** code that takes the i.MX6ULL from its 396 MHz reset default to 696 MHz, with explicit configuration of the bus clocks. By the end we can read back, from registers, exactly what the chip is running at and verify with a hardware measurement.
> **Why:** every later chapter (DDR especially) depends on knowing the bus clocks precisely. The Boot ROM leaves clocks in a known but conservative state; we must own them before we trust their values in initialization tables.
> **Focus:** the **four-layer clock tree** from Chapter 5 made concrete — XTAL → PLL → root mux+divider → CCGR gate. Each peripheral hangs off one root clock; each root clock hangs off one PLL. Once you can trace a peripheral's frequency through these four hops, you can predict and debug any clocking issue.

## 13.1  What we want to set up

By the end of this chapter, the clock tree looks like:

| Domain | Frequency | Source |
|--------|-----------|--------|
| ARM core | 696 MHz | PLL1 (ARM PLL) |
| AHB | 132 MHz | PLL2_PFD2 (396 MHz) ÷ 3 |
| IPG (peripheral bus) | 66 MHz | AHB ÷ 2 |
| AXI | 198 MHz | PLL2_PFD2 (396 MHz) ÷ 2 |
| UART | 80 MHz | PLL3 (480 MHz) ÷ 6 |
| MMDC (DDR) | 396 MHz | PLL2 (528 MHz) PFD or direct |

This matches what U-Boot will set up in Chapter 19. We are running U-Boot's preamble by hand.

## 13.2  The ANATOP block — PLLs and PFDs

PLLs live in **ANATOP** (Analog Top), base address `0x020C8000`. Each PLL has its own register set. The relevant ones for us:

| Register | Offset | Notes |
|----------|--------|-------|
| `ANATOP_PLL_ARM` | `+0x000` | PLL1 (ARM core) |
| `ANATOP_PLL_USB1` | `+0x010` | PLL3 |
| `ANATOP_PLL_USB2` | `+0x020` | PLL7 |
| `ANATOP_PLL_SYS` | `+0x030` | PLL2 |
| `ANATOP_PFD_528` | `+0x100` | PLL2's four PFDs |
| `ANATOP_PFD_480` | `+0x0F0` | PLL3's four PFDs |
| `ANATOP_PLL_VIDEO` | `+0x0A0` | PLL5 |
| `ANATOP_PLL_ENET` | `+0x0E0` | PLL6 |

Each PLL has `SET` (`+0x4`), `CLR` (`+0x8`), and `TOG` (`+0xC`) sibling addresses that let you set/clear/toggle bits atomically without read-modify-write. We will use the main offset and OR/AND values when clarity matters more than atomicity (there is no concurrency on bare-metal yet).

### PLL1 (ARM PLL)

The PLL1 register has these bit fields:

| Bits | Field | Meaning |
|------|-------|---------|
| 6:0 | DIV_SELECT | Loop divider (54..108). `f_pll1 = 24 MHz × DIV_SELECT / 2`. |
| 12 | POWERDOWN | 1 = powered down (the default after reset is 0). |
| 13 | ENABLE | 1 = output enabled |
| 14 | BYPASS_CLK_SRC | Source of bypass clock (we don't use bypass) |
| 16 | BYPASS | 1 = output is the bypass clock, not the PLL |
| 31 | LOCK | Read-only; 1 = PLL has acquired lock |

For 696 MHz: we want `24 × DIV / 2 = 696`, so DIV = 58. The encoding "DIV_SELECT" is the *raw divider value*, so we write 58.

### PLL2 (System PLL)

PLL2 is **fixed at 528 MHz** by hardware. Its register has fewer knobs (DIV_SELECT is 1-bit: 0 = 528 MHz, 1 = 480 MHz). We leave it alone.

What we care about on PLL2 are its **PFDs**: four fractional dividers, each 6-bit (FRAC = 12..35), generating `f_pll2 × 18 / FRAC`. The four PFDs of PLL2 typically produce:

- PFD0: 352 MHz (FRAC = 27) — ~352 MHz
- PFD1: 594 MHz (FRAC = 16)
- PFD2: 396 MHz (FRAC = 24)
- PFD3: 297 MHz (FRAC = 32)

We will use **PLL2_PFD2 at 396 MHz** for the bus clocks. That's the default after reset, but we configure it explicitly to remove ambiguity.

### PLL3 (USB1 PLL, also feeds peripherals)

PLL3 is fixed at 480 MHz. Its PFDs:

- PFD0: 720 MHz
- PFD1: 540 MHz
- PFD2: 508 MHz
- PFD3: 454 MHz

UART can be fed either from PLL3 directly with a /6 divider (giving 80 MHz, what we set in Chapter 12) or from a PFD.

## 13.3  The CCM block — root clocks and gates

CCM base = `0x020C4000`. The registers we touch:

| Register | Offset | Purpose |
|----------|--------|---------|
| `CCM_CCR` | `+0x00` | Control |
| `CCM_CACRR` | `+0x10` | ARM clock root register (post-PLL1 divider) |
| `CCM_CBCDR` | `+0x14` | Bus clock divider |
| `CCM_CBCMR` | `+0x18` | Bus clock mux |
| `CCM_CSCMR1` | `+0x1C` | Serial clock mux 1 (UART src) |
| `CCM_CSCMR2` | `+0x20` | Serial clock mux 2 |
| `CCM_CSCDR1` | `+0x24` | UART, USDHC dividers |
| `CCM_CDHIPR` | `+0x48` | Divider handshake-in-progress flags |
| `CCM_CCGRx` | `+0x68` .. `+0x80` | Clock gates (CCGR0..CCGR6) |

The flow when you change a divider:

1. Write the new value to the mux/divider field.
2. **Wait for `CCM_CDHIPR` to clear** the corresponding "busy" bit. The hardware needs a few cycles to switch.
3. *Then* the new clock is in effect.

If you don't wait, subsequent reads/writes can race the clock change. Symptom: works on the 5th run, fails on the 6th.

## 13.4  The bring-up code

`clocks.h`:

```c
#ifndef CLOCKS_H
#define CLOCKS_H
#include <stdint.h>
void clocks_init(void);
uint32_t clocks_get_arm_hz(void);
uint32_t clocks_get_ahb_hz(void);
uint32_t clocks_get_ipg_hz(void);
uint32_t clocks_get_uart_hz(void);
#endif
```

`clocks.c`:

```c
#include "clocks.h"

#define REG(addr) (*(volatile uint32_t *)(addr))

/* CCM */
#define CCM_CCR     0x020C4000
#define CCM_CACRR   0x020C4010
#define CCM_CBCDR   0x020C4014
#define CCM_CBCMR   0x020C4018
#define CCM_CSCMR1  0x020C401C
#define CCM_CSCDR1  0x020C4024
#define CCM_CDHIPR  0x020C4048

/* ANATOP */
#define ANATOP_BASE       0x020C8000
#define ANATOP_PLL_ARM    (ANATOP_BASE + 0x000)
#define ANATOP_PLL_SYS    (ANATOP_BASE + 0x030)
#define ANATOP_PFD_528    (ANATOP_BASE + 0x100)
#define ANATOP_PLL_USB1   (ANATOP_BASE + 0x010)

#define XTAL_HZ           24000000U

static void wait_pll_lock(uint32_t reg)
{
    while (!(REG(reg) & (1u << 31))) { /* spin */ }
}

static void wait_handshake(uint32_t mask)
{
    while (REG(CCM_CDHIPR) & mask) { /* spin */ }
}

void clocks_init(void)
{
    /* ----------------------------------------------------------------
     * Step 1: Switch ARM core *off* PLL1 temporarily, so we can reprogram
     *         PLL1 without crashing.  Source ARM clock from "step_clk"
     *         (the secondary clock path) by setting CCM_CCSR.step_sel = 0
     *         (24 MHz osc) and CCM_CCSR.pll1_sw_sel = 1.
     *
     * Or, more simply: put PLL1 in bypass while reprogramming.
     * Bypassed PLL1 outputs the 24 MHz reference, so the core runs slow
     * but never crashes.
     * ---------------------------------------------------------------- */
    REG(ANATOP_PLL_ARM) |= (1u << 16);    /* PLL1.BYPASS = 1 */

    /* Step 2: Reprogram PLL1.
     *   24 MHz × 58 / 2 = 696 MHz
     *   DIV_SELECT field is bits [6:0]; value 58. */
    {
        uint32_t v = REG(ANATOP_PLL_ARM);
        v &= ~0x7Fu;            /* clear DIV_SELECT */
        v |= 58u;               /* DIV_SELECT = 58 */
        v &= ~(1u << 12);       /* POWERDOWN = 0 */
        v |=  (1u << 13);       /* ENABLE = 1 */
        REG(ANATOP_PLL_ARM) = v;
    }

    /* Step 3: Wait for PLL1 lock. */
    wait_pll_lock(ANATOP_PLL_ARM);

    /* Step 4: Release bypass. */
    REG(ANATOP_PLL_ARM) &= ~(1u << 16);

    /* Step 5: ARM clock divider = 1 (CACRR[ARM_PODF] = 0). */
    REG(CCM_CACRR) = 0;

    /* ----------------------------------------------------------------
     * Step 6: Configure PLL2_PFD2 = 396 MHz.  Already the reset default,
     *         but be explicit.  PFD2 is in ANATOP_PFD_528 bits 16:21
     *         (PFD2_FRAC).  Bit 23 (PFD2_CLKGATE) must be 0.
     *   f_PFD = 528 × 18 / FRAC ; for 396 MHz, FRAC = 24.
     * ---------------------------------------------------------------- */
    {
        uint32_t v = REG(ANATOP_PFD_528);
        v &= ~(0x3F << 16);             /* clear FRAC */
        v |=  (24u  << 16);             /* FRAC = 24 */
        v &= ~(1u   << 23);             /* CLKGATE off */
        REG(ANATOP_PFD_528) = v;
    }

    /* ----------------------------------------------------------------
     * Step 7: Configure bus mux (CCM_CBCMR.PRE_PERIPH_CLK_SEL).
     *   Bits [19:18] -- select what feeds the periph_clk mux:
     *     00 = PLL2 (528 MHz)
     *     01 = PLL2_PFD2 (396 MHz)
     *     10 = PLL2_PFD0
     *     11 = PLL2_PFD2 / 2
     *   We want 01 = 396 MHz.
     * ---------------------------------------------------------------- */
    {
        uint32_t v = REG(CCM_CBCMR);
        v &= ~(3u << 18);
        v |=  (1u << 18);
        REG(CCM_CBCMR) = v;
    }

    /* ----------------------------------------------------------------
     * Step 8: Bus dividers in CBCDR.
     *   AHB_PODF (bits 12:10): AHB = periph_clk / (AHB_PODF + 1)
     *     periph_clk = 396 MHz; AHB target = 132 MHz; divider = 3 ⇒ field = 2
     *   IPG_PODF (bits  9: 8): IPG = AHB / (IPG_PODF + 1)
     *     IPG target = 66 MHz; divider = 2 ⇒ field = 1
     *   AXI_PODF (bits 18:16): AXI = periph_clk / (AXI_PODF + 1)
     *     AXI target = 198 MHz; divider = 2 ⇒ field = 1
     * ---------------------------------------------------------------- */
    {
        uint32_t v = REG(CCM_CBCDR);
        v &= ~((7u << 10) | (3u << 8) | (7u << 16));
        v |=  (2u << 10) | (1u << 8) | (1u << 16);
        REG(CCM_CBCDR) = v;
    }
    wait_handshake((1u << 0) | (1u << 1) | (1u << 2));

    /* ----------------------------------------------------------------
     * Step 9: UART source: PLL3 / 6 = 80 MHz.
     *   CSCDR1.UART_CLK_SEL  (bit 6) = 0  -> PLL3_80M  (already /6)
     *   CSCDR1.UART_CLK_PODF (bits 5:0) = 0 -> /1
     * ---------------------------------------------------------------- */
    {
        uint32_t v = REG(CCM_CSCDR1);
        v &= ~((1u << 6) | 0x3Fu);
        REG(CCM_CSCDR1) = v;
    }
}

uint32_t clocks_get_arm_hz(void)
{
    uint32_t pll = REG(ANATOP_PLL_ARM);
    uint32_t div = pll & 0x7F;
    uint32_t cacrr = REG(CCM_CACRR) & 0x07;
    return (uint32_t)((uint64_t)XTAL_HZ * div / 2 / (cacrr + 1));
}

uint32_t clocks_get_ahb_hz(void)
{
    uint32_t v = REG(CCM_CBCDR);
    uint32_t periph_div_field = (v >> 10) & 7;
    /* periph_clk = 396 MHz (we set PFD2 to that) */
    return 396000000U / (periph_div_field + 1);
}

uint32_t clocks_get_ipg_hz(void)
{
    uint32_t v = REG(CCM_CBCDR);
    uint32_t ipg_div_field = (v >> 8) & 3;
    return clocks_get_ahb_hz() / (ipg_div_field + 1);
}

uint32_t clocks_get_uart_hz(void)
{
    return 80000000U;
}
```

What is conspicuously absent from this code:

- **No CCGR writes.** We do not gate or ungate any peripheral here. Each subsystem's `*_init()` function gates its own clock (as `uart_init()` does in Chapter 12). This keeps responsibility local.
- **No fancy interrupt nesting / atomicity guards.** We are bare-metal; we have nothing pre-empting us.

## 13.5  Verifying with `printf`

In `main()`:

```c
#include "uart.h"
#include "clocks.h"
int printf(const char *fmt, ...);

int main(void)
{
    uart_init();
    printf("\r\nPre-clocks_init():\r\n");
    printf("  ARM = %u Hz\r\n", clocks_get_arm_hz());
    printf("  AHB = %u Hz\r\n", clocks_get_ahb_hz());
    printf("  IPG = %u Hz\r\n", clocks_get_ipg_hz());

    clocks_init();
    uart_init();    /* re-init: UART clock might have changed */

    printf("\r\nPost-clocks_init():\r\n");
    printf("  ARM = %u Hz\r\n", clocks_get_arm_hz());
    printf("  AHB = %u Hz\r\n", clocks_get_ahb_hz());
    printf("  IPG = %u Hz\r\n", clocks_get_ipg_hz());

    for (;;) {}
}
```

Expected:

```
Pre-clocks_init():
  ARM = 396000000 Hz
  AHB = 132000000 Hz
  IPG = 66000000 Hz

Post-clocks_init():
  ARM = 696000000 Hz
  AHB = 132000000 Hz
  IPG = 66000000 Hz
```

The Boot ROM leaves the chip at ARM = 396 MHz already (PLL1 at 792 MHz, divided). After our init, ARM is 696 MHz, the bus clocks are unchanged.

## 13.6  Verifying with hardware

Software-reads-software-writes is the easiest check to lie to itself. For confidence, measure.

### Quick check: blink rate

The Chapter 9 / 10 delay loop ran at 396 MHz. After clocks_init() we should see almost twice the blink rate at 696 MHz for the same delay constant. Add a blink to `main()`; observe.

### Better check: count cycles with PMU

The Cortex-A7 has a **Performance Monitor Unit** (PMU) — including a 32-bit cycle counter (CCNT). Enable it:

```asm
mrc p15, 0, r0, c9, c14, 0  @ read PMUSERENR
orr r0, r0, #1               @ enable user-mode access (not strictly needed in PL1)
mcr p15, 0, r0, c9, c14, 0

mov r0, #1
mcr p15, 0, r0, c9, c12, 0   @ PMCR.E = 1: enable all counters
mov r0, #0x80000000
mcr p15, 0, r0, c9, c12, 1   @ PMCNTENSET: enable CCNT
```

Then to read:

```c
static inline uint32_t pmu_ccnt(void)
{
    uint32_t v;
    asm volatile ("mrc p15, 0, %0, c9, c13, 0" : "=r"(v));
    return v;
}
```

Measure a known loop:

```c
uint32_t t0 = pmu_ccnt();
for (volatile int i = 0; i < 1000000; i++) {}
uint32_t t1 = pmu_ccnt();
printf("loop took %u cycles\r\n", t1 - t0);
```

At 696 MHz a million-iteration empty loop should take ~5 million cycles (roughly 7 ns per iteration on a Cortex-A7). At 396 MHz, the same loop count takes the same *cycles* — but with a slower clock, the wall-time it consumes is longer. The number of cycles is therefore the most precise measurement of clock changes.

### Hardware check: scope a GPIO

Toggle a GPIO in a tight loop:

```c
for (;;) {
    REG(GPIO1_DR) ^= LED_BIT;
}
```

The frequency of the resulting square wave is determined by (CPU clock / 5 instructions per iteration). Scope it. With ARM at 696 MHz and 5 cycles per iteration → ~70 MHz toggle, which the scope and the GPIO drive strength will not produce cleanly; you'll see a degraded waveform but the *period* is measurable. The same loop at 396 MHz produces 40 MHz. A 2× change in frequency between the two builds is the proof.

## 13.7  Why we set up clocks before DDR

We do not, strictly, *have* to set the ARM clock to 696 MHz before DDR — DDR works at the default ARM speed. But we *do* need to know the AHB and IPG clocks before DDR init, because:

- **DDR timing parameters are absolute (nanoseconds).** The MMDC controller converts ns to cycles using *its own* input clock. If we set the bus clocks wrong, the DDR controller computes the wrong number of clocks per timing parameter, and DRAM accesses corrupt.
- **MMDC's clock comes from CBCDR.MMDC_PODF**, which divides periph_clk. Setting MMDC clock = 396 MHz makes the conversion factors easy: 1 cycle = 2.525 ns.

So this chapter and Chapter 14 are coupled: get clocks right here, and DDR init can use the values verbatim.

## 13.8  Lab

1. **Build, push, observe pre/post clocks.** Confirm ARM goes from 396 to 696 MHz.
2. **Enable PMU CCNT.** Measure a known busy loop's cycle count. Confirm it matches the loop length.
3. **Scope a GPIO toggle loop.** Measure frequency. Compute the cycles-per-iteration the compiler emitted; compare to `objdump`.
4. **Try to set ARM to 792 MHz.** This is the upper bin; some chips can take it. (Many MINIs can. Yours may or may not.) Set DIV_SELECT = 66. Observe — does it lock, does it crash? **Restore 696 MHz** before next chapter.
5. **Read CCM_CBCMR after init and decode every field by hand.** Cross-check with what your code wrote.

## 13.9  Pitfalls

- **Reprogramming PLL1 while running on it.** The CPU stalls. Always BYPASS first or switch ARM clock to the step source. We chose bypass.
- **Forgetting to wait for handshake.** Symptom: works at 396 MHz, fails at 696 MHz with intermittent crashes near `clocks_init` return.
- **PLL lock never asserts.** Most likely: POWERDOWN bit still set, or you're reading the wrong PLL register. Double-check addresses.
- **Wrong PFD FRAC formula.** It's `f_PLL × 18 / FRAC`, not `f_PLL / FRAC`. The 18× makes the math counterintuitive.
- **CCM_CBCDR divider fields off-by-one.** "Divider N" = "field value (N-1)". For divider 3, write 2.
- **Boot ROM did something useful that you undid.** The ROM configures DDR (via DCD if present) and sometimes the USB PLL. If you blow those away, you may break things that depended on them. Only modify what you understand.

## 13.10  Going deeper

- **IMX6ULLRM Chapter 18 — CCM**. The complete register descriptions.
- **IMX6ULLRM Chapter 19 — CCM_ANALOG, PMU, TEMPMON**. PLLs and PFDs.
- **AN12086** — *i.MX 6 Series Hardware Development Guide*. Has clock diagrams.
- **U-Boot source: `arch/arm/mach-imx/mx6/clock.c`**. Read after this chapter. Note how it does the same operations with a much larger configuration table.
- **Linux source: `drivers/clk/imx/clk-imx6ul.c`** — the kernel's clock framework view of the same tree. The same hardware, viewed through a much higher abstraction.

> Next chapter: **Chapter 14 — DDR3 initialization with MMDC.** This is the longest chapter in the bare-metal Part. Block out an afternoon. The reward is 512 MB of usable DRAM and the engineering insight that distinguishes you from someone who only ever uses eval kits.
