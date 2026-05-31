---
chapter: 16
title: Timers — EPIT and GPT
part: II — Bare-metal i.MX6ULL
estimated_pages: 14
status: draft
---

# Chapter 16 — Timers — EPIT and GPT

> **What:** a 1 ms tick from EPIT1 (interrupt-driven) and a free-running 32-bit counter from GPT1 (polled). Together they give us `tick_ms()`, `udelay()`, `mdelay()`, and a cycle-precise way to measure code.
> **Why:** before we touch the MMU or write any real drivers, we need timing. Every scheduler, every protocol stack, every "wait at least N ns then check again" needs a primitive.
> **Focus:** the **separation of concerns** — EPIT for periodic interrupts (the kernel's tick source), GPT for free-running time (the kernel's clocksource). Linux uses two devices for the same reason; understanding the split here makes Linux's `arch_timer` and `clocksource` framework familiar.

## 16.1  Two timers, two jobs

The i.MX6ULL has multiple timer blocks. We use two:

- **GPT1** (General Purpose Timer 1) — 32-bit free-running counter. We poll it. Used for `udelay`, `mdelay`, and profiling.
- **EPIT1** (Enhanced Periodic Interrupt Timer 1) — 32-bit count-down with auto-reload. We let it fire an interrupt every 1 ms. Used for `tick_ms`.

You could use one timer for both jobs (and Linux on this part typically uses the generic timer for both), but separating them keeps each minimal.

## 16.2  GPT — free-running counter

GPT1 base = `0x02098000`. Registers we touch:

| Register | Offset | Notes |
|----------|--------|-------|
| `GPT_CR` | `+0x00` | Control |
| `GPT_PR` | `+0x04` | Prescaler |
| `GPT_SR` | `+0x08` | Status (output-compare bits) |
| `GPT_IR` | `+0x0C` | Interrupt enable mask |
| `GPT_OCR1..3` | `+0x10..18` | Output-compare values |
| `GPT_ICR1..2` | `+0x1C..20` | Input-capture |
| `GPT_CNT` | `+0x24` | The counter itself |

Bring-up:

```c
#define GPT1_BASE   0x02098000
#define GPT_CR      (GPT1_BASE + 0x00)
#define GPT_PR      (GPT1_BASE + 0x04)
#define GPT_CNT     (GPT1_BASE + 0x24)

#define CCM_CCGR1   0x020C406C   /* GPT1 gate = CG10 = bits 20:21 */

void gpt_init(void)
{
    /* Enable GPT1 clock. */
    REG(CCM_CCGR1) |= (3u << 20);

    /* Soft reset, then configure. */
    REG(GPT_CR) = (1u << 15);                 /* SWR = 1: software reset */
    while (REG(GPT_CR) & (1u << 15)) {}

    /* CLKSRC = 0b001 (peripheral clock = IPG = 66 MHz),
       ENMOD = 1 (reset count on enable),
       FRR = 1 (free-run mode),
       EN = 1 (enable).
       Prescaler: 66 MHz / 66 = 1 MHz counter (1 tick = 1 us). */
    REG(GPT_PR) = 65;                         /* divider = 66 */
    REG(GPT_CR) = (1u << 9)                   /* FRR free-run */
                | (1u << 1)                   /* ENMOD: reset on enable */
                | (1u << 6)                   /* CLKSRC = peripheral clk */
                | (1u << 0);                  /* EN = 1 */
}

static inline uint32_t gpt_now_us(void)
{
    return REG(GPT_CNT);
}

void udelay(uint32_t us)
{
    uint32_t start = gpt_now_us();
    while ((gpt_now_us() - start) < us) {}
}

void mdelay(uint32_t ms)
{
    while (ms--) udelay(1000);
}
```

A few notes:

- **Prescaler of 65 ⇒ divider 66.** The field is "divisor - 1," yet another N+1 register. With 66 MHz IPG, dividing by 66 gives a 1 MHz timer — one tick = 1 µs. Convenient.
- **`(gpt_now_us() - start) < us`** uses unsigned subtraction modulo 2^32. This correctly handles counter wraparound for delays shorter than 2^32 µs (~71 minutes). For longer delays, extend to 64-bit accumulation.
- **`FRR = 1`** means "free-running" — the counter keeps going past output-compare matches; it does not auto-reload to zero. This is what makes it a clocksource rather than a tick source.

The `udelay` is now precise to within a microsecond (limited by the spin-loop's reaction time, which on a 696 MHz core is sub-microsecond).

## 16.3  EPIT — periodic interrupt

EPIT1 base = `0x020D0000`. Registers:

| Register | Offset | Notes |
|----------|--------|-------|
| `EPIT_CR` | `+0x00` | Control |
| `EPIT_SR` | `+0x04` | Status (compare match) |
| `EPIT_LR` | `+0x08` | Load value |
| `EPIT_CMPR` | `+0x0C` | Compare value (usually 0) |
| `EPIT_CNR` | `+0x10` | Current count (read-only) |

For a 1 ms tick from 66 MHz: count down 66000 cycles per tick.

```c
#define EPIT1_BASE  0x020D0000
#define EPIT_CR     (EPIT1_BASE + 0x00)
#define EPIT_SR     (EPIT1_BASE + 0x04)
#define EPIT_LR     (EPIT1_BASE + 0x08)
#define EPIT_CMPR   (EPIT1_BASE + 0x0C)

#define CCM_CCGR1_EPIT1_GATE (3u << 12)   /* CG6 of CCGR1 */

static volatile uint32_t jiffies_ms;

static void epit_isr(void)
{
    REG(EPIT_SR) = 1;          /* W1C: clear the compare flag */
    jiffies_ms++;
}

void epit_init(void)
{
    REG(CCM_CCGR1) |= CCM_CCGR1_EPIT1_GATE;

    REG(EPIT_CR) = (1u << 16);                /* SWR */
    while (REG(EPIT_CR) & (1u << 16)) {}

    /* CLKSRC=01 (peripheral=IPG), RLD=1 (reload from LR), ENMOD=1 (load on enable),
       OCIEN=1 (interrupt on compare), IOVW=1 (write LR overwrites immediately),
       PRESCALER=0 (divide-by-1).
       LR = 66000 = (66 MHz / 1000 Hz) for 1 ms. */
    REG(EPIT_LR) = 66000;
    REG(EPIT_CMPR) = 0;
    /* Per RM §30.5.1 (EPIT_CR):
     *   CLKSRC is the 2-bit field at [25:24]; 0b01 = peripheral clock → (1 << 24).
     *   IOVW is bit 17 (NOT bit 22 — earlier drafts of this listing had that wrong).
     *   PRESCALER is bits [15:4]; 0 = divide-by-1.
     *   RLD = bit 3, OCIEN = bit 2, ENMOD = bit 1, EN = bit 0. */
    REG(EPIT_CR) = (1u << 24)                 /* CLKSRC[25:24] = 0b01 (peripheral) */
                 | (1u << 17)                 /* IOVW */
                 | (1u << 3)                  /* RLD */
                 | (1u << 2)                  /* OCIEN */
                 | (1u << 1)                  /* ENMOD */
                 | (1u << 0);                 /* EN */
}

/* GIC SPI ID for EPIT1 = 88 on i.MX6ULL (RM Table 3-1).  Verify. */
void epit_install_isr(void)
{
    gic_register(88, epit_isr);
    gic_enable_irq(88);
}

uint32_t tick_ms(void)
{
    return jiffies_ms;
}
```

`jiffies_ms` is global, volatile, and incremented from interrupt context — read it carefully from non-ISR code:

```c
uint32_t ms = tick_ms();   /* harmless: a 32-bit read is atomic */
```

A 32-bit unsigned wraps every ~49 days. Sufficient for our purposes; production code would track 64-bit ticks (read low, read high, re-read low, retry on wrap — the standard 32-bit pair pattern).

## 16.4  Putting it together

```c
int main(void)
{
    uart_init();
    clocks_init();
    uart_init();
    gic_init();
    gpt_init();
    epit_init();
    epit_install_isr();
    irq_enable();

    printf("Timers running.\r\n");

    /* Use udelay to time a quick test: */
    uint32_t t0 = gpt_now_us();
    udelay(10000);                     /* 10 ms */
    uint32_t t1 = gpt_now_us();
    printf("10 ms udelay actually took %u us\r\n", t1 - t0);

    /* Print a heartbeat every second using mdelay. */
    for (uint32_t i = 0;; i++) {
        printf("[%u ms]  heartbeat %u\r\n", tick_ms(), i);
        mdelay(1000);
    }
}
```

Expected:

```
Timers running.
10 ms udelay actually took 10000 us
[0 ms]  heartbeat 0
[1000 ms]  heartbeat 1
[2000 ms]  heartbeat 2
...
```

If `tick_ms()` does not advance, EPIT's IRQ isn't firing. Re-check:

- CCGR gate bit. Right register, right field.
- GIC ID 88 enabled.
- `EPIT_CR.OCIEN = 1` and `EPIT_SR` cleared on each tick.
- CPSR.I cleared via `irq_enable()`.

## 16.5  Profiling with PMU CCNT and GPT

Two ways to measure short intervals:

### PMU cycle counter (chapter 13's introduction)

```c
static inline uint32_t pmu_ccnt(void)
{
    uint32_t v;
    asm volatile ("mrc p15, 0, %0, c9, c13, 0" : "=r"(v));
    return v;
}
```

This is *cycle-precise* but reset on power-cycle. It tells you "how many cycles did this code take" — independent of clock changes.

### GPT counter

`gpt_now_us()` is *time-precise* — microseconds always mean microseconds, regardless of how the ARM core has been reclocked. (Until you change MMDC/IPG clocks; the GPT divider then needs adjusting.)

Use PMU for **how efficient is this code on this CPU**; use GPT for **how long does this real-time operation take**. They answer different questions.

Example: profile our 4 MB memtest from Chapter 14:

```c
uint32_t c0 = pmu_ccnt();
uint32_t u0 = gpt_now_us();
ddr_selftest();
uint32_t c1 = pmu_ccnt();
uint32_t u1 = gpt_now_us();
printf("memtest: %u cycles = %u us\r\n", c1 - c0, u1 - u0);
```

A 4 MB write + 4 MB read on DDR3 at 396 MHz takes ~30 ms (≈ 250 MB/s). At 696 MHz CPU that's ~21 million CPU cycles. The cycle/µs ratio should be ~696, matching the CPU clock; if it isn't, your clock initialization (Chapter 13) is wrong.

## 16.6  Lab

1. **Heartbeat for an hour.** Run the example and observe `tick_ms` rolling forward predictably. Check that one hour of heartbeats produces ~3600 increments.
2. **Drift test.** Compare `tick_ms()` after 60 seconds against a stopwatch. The error tells you the crystal accuracy and the prescaler precision. Typical: < 0.01% (60 ms over 60 s).
3. **Measure `udelay(1)`.** Loop `udelay(1)` a million times; time the wall clock; divide. Confirm it's within 1% of 1 second.
4. **Nested-IRQ test.** Inside `epit_isr`, `printf("tick\n")`. `uart_putc` polls TX, so this is okay even though we're in ISR. Confirm output every 1 ms (you won't see individual ticks at 115200 baud — but the *rate* should be steady).
5. **Use GPT to validate Chapter 13's clocks.** Make a fixed-cycle-count loop (200 nops, exactly). Measure with PMU; confirm 200 cycles. Measure with GPT; confirm 200/696 ≈ 287 ns.

## 16.7  Pitfalls

- **Wrong CCGR bit.** GPT1 is CG10; EPIT1 is CG6; both in CCGR1. Easy to confuse.
- **Forgetting to W1C the status flag.** EPIT_SR bit 0 is set on compare; you must write 1 to clear it inside the ISR. Otherwise the interrupt re-fires immediately and you spin forever in IRQ context.
- **Wrong prescaler register.** GPT_PR is "divisor minus 1". For 66 MHz → 1 MHz, write 65. Not 66.
- **EPIT_LR vs EPIT_CMPR.** LR is the reload value; CMPR is the compare threshold (usually 0). Don't swap.
- **Drift from forgotten clock changes.** If you call `clocks_init` *after* `gpt_init`, the GPT prescaler is now wrong for the new IPG. Initialize clocks first, then timers.
- **Reading `jiffies_ms` torn across an update.** 32-bit reads are single-instruction on ARMv7-A; safe. A 64-bit counter would need a lo/hi retry loop.

## 16.8  Going deeper

- **IMX6ULLRM Chapter 29 (GPT) and Chapter 30 (EPIT).** Complete register descriptions.
- **Cortex-A7 TRM, Chapter 8** — generic timer (which you can use *instead* of EPIT/GPT; we use it in Linux later).
- **Linux source: `drivers/clocksource/timer-imx-gpt.c`** — the same hardware as a Linux clocksource.
- **POSIX `clock_gettime(CLOCK_MONOTONIC)`** — what user-space sees of all this; backed eventually by these timers.

> Next chapter: **Chapter 17 — MMU and caches.** The last bare-metal infrastructure piece. Turn on the MMU, run our code with virtual memory, enable I/D caches, measure the speed-up. After this we are ready for U-Boot in Part III.
