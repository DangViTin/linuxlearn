---
chapter: 18B
title: Button input and beep (passive buzzer)
part: II — Bare-metal i.MX6ULL (inserted v1.1)
estimated_pages: 12
status: draft
---

# Chapter 18B — Button input and beep

> **What:** read a GPIO input with software debouncing, then drive a passive buzzer at an audible frequency from a polled GPIO toggle loop. Two new peripherals; both built on the GPIO and timer primitives we already own.
> **Why:** every product accepts input and emits feedback. Until now, our only input was UART and our only output was an LED. Adding a button and a buzzer rounds out the minimal HMI vocabulary, and forces us to confront **debouncing**, which is one of those topics every embedded engineer needs to nail down once.
> **Focus:** the **debounce decision** — when to spin-debounce, when to use a timer, when to do it in hardware. The right answer depends on what else the CPU is supposed to be doing, and we will see all three approaches.

## 18B.1  The hardware on the Point Atom MINI

From the Point Atom V1.81 schematics (consistent across ALPHA and MINI):

- **KEY0** — a normally-open momentary tactile switch wired between the **UART1_CTS_B** pad (which in ALT5 becomes **GPIO1_IO18**) and **GND**. The pin sits high through an external 10 kΩ pull-up. Pressed: low; released: high. **Active-low.**
- **BEEP** — a passive piezo buzzer driven through a **PNP transistor (Q1, 8550-class)** whose base is controlled by the **SNVS_TAMPER1** pad (ALT5 = **GPIO5_IO01**). When GPIO5_IO01 = **0**, the PNP turns on, the buzzer's positive terminal sees 3V3, and the buzzer beeps. When GPIO5_IO01 = **1**, the PNP is off and the buzzer is silent. **Active-low** at the GPIO. The buzzer itself is *passive* (no internal oscillator) — you must toggle GPIO5_IO01 at the audible frequency to produce a tone.

Why active-low via a transistor? The buzzer draws more current than a bare GPIO can sink without risking the SoC's IO drive specs. The PNP is a small driver stage that lets us sink/source the buzzer's coil current via the 3V3 rail rather than directly through the SoC.

For the rest of this chapter:

- **KEY0**: pad `UART1_CTS_B` → ALT5 → GPIO1_IO18, **active-low**.
- **BEEP**: pad `SNVS_TAMPER1` → ALT5 → GPIO5_IO01, **active-low** (`DR &= ~bit` turns ON; `DR |= bit` turns OFF).

Pad addresses (from RM IOMUXC chapter):

- `IOMUXC_SW_MUX_CTL_PAD_UART1_CTS_B` (for KEY0)
- `IOMUXC_SW_PAD_CTL_PAD_UART1_CTS_B`
- `IOMUXC_SNVS_SW_MUX_CTL_PAD_SNVS_TAMPER1` (for BEEP — note the `SNVS_` prefix; SNVS-domain pads live in a separate IOMUXC bank)
- `IOMUXC_SNVS_SW_PAD_CTL_PAD_SNVS_TAMPER1`

GPIO5 is in the **SNVS domain**, with base `0x020AC000`. Its clock gate is in a different CCGR bit than GPIO1's. Always cross-check the RM table for "GPIO5 is in the SNVS domain" — this is one of the i.MX6ULL's idiosyncrasies and the source of the "I clocked the wrong GPIO bank" debugging story every i.MX6ULL engineer has told once.

## 18B.2  Button driver — polled with software debounce

The naive read-and-act:

```c
if ((GPIO_DR(GPIO1_BASE) & (1 << 18)) == 0) {
    /* button pressed */
}
```

…works once. The problem: **switch bounce**. When the mechanical contacts close, they bounce — make-break-make-break for typically 1–10 ms. A polled read can sample mid-bounce and report "pressed → released → pressed" several times for a single physical press.

The classical fix in 1980s firmware was a 20 ms hardware RC filter on the input. We do it in software instead:

```c
int key_read_debounced(void)
{
    /* Sample, wait, sample again; return 1 only if both samples match. */
    int s1 = (GPIO_DR(GPIO1_BASE) & (1 << 18)) ? 0 : 1;
    mdelay(20);  /* 20 ms is overkill; tactile switches usually < 5 ms */
    int s2 = (GPIO_DR(GPIO1_BASE) & (1 << 18)) ? 0 : 1;
    return (s1 == s2) ? s1 : -1;   /* -1 = bouncing */
}
```

This works for slow UI buttons but blocks the caller for 20 ms — unacceptable if the CPU has anything else to do.

### Better: integrate, then decide

The standard non-blocking pattern is a state machine driven by an EPIT-style periodic tick:

```c
/* Called every 10 ms from the EPIT ISR. */
static uint32_t key_history;       /* 32-tick sliding window */
static int      key_state;         /* 0=up, 1=down */

void key_tick(void)
{
    int raw = (GPIO_DR(GPIO1_BASE) & (1 << 18)) ? 0 : 1;
    key_history = (key_history << 1) | raw;

    /* "Pressed" = last 8 ticks (80 ms) all 1.
     * "Released" = last 8 ticks all 0. */
    if ((key_history & 0xFF) == 0xFF && !key_state) {
        key_state = 1;
        on_key_press();
    } else if ((key_history & 0xFF) == 0x00 && key_state) {
        key_state = 0;
        on_key_release();
    }
}
```

This pattern is the basis of every modern keypad-scan implementation. The 80 ms validation window is conservative; tune to 30 ms (3 ticks) for snappier response if your switch is good quality.

### Best (for production): hardware debouncing + interrupt

A Schmitt-trigger gate + RC filter on the input gives clean edges and lets you use a GPIO IRQ instead of polling. Point Atom MINI does not include this; many production boards do. We will see the kernel-level analog in Part VI Chapter 45 — the input subsystem includes a `gpio-keys` driver that ties this all together.

## 18B.3  Buzzer — a square wave on GPIO5_IO01 (active-low via PNP)

A passive piezo emits sound at the frequency of the applied square wave. A 1 kHz tone is well within human hearing; 4 kHz is shrill; 200 Hz is a low buzz.

Because BEEP is driven through an active-low PNP transistor, the polarities below look "inverted" — but a square wave is symmetric, so the *toggling* still produces sound at the right frequency. The only place polarity matters is at idle (the buzzer must be **silent** when we are not playing a tone, which means GPIO5_IO01 = **1**).

```c
void beep_init(void)
{
    /* GPIO5 lives in SNVS domain; gate clock via CCM_CCGR1[31:30] */
    REG(CCM_CCGR1) |= (3u << 30);

    /* IOMUX: SNVS_TAMPER1 -> ALT5 (GPIO5_IO01).  Address per your RM. */
    REG(IOMUXC_SNVS_BASE + 0x00) = 5;    /* MUX = ALT5 */
    REG(IOMUXC_SNVS_BASE + 0x18) = 0x10B0;

    GPIO_GDIR(GPIO5_BASE) |= (1u << 1);   /* output */
    GPIO_DR(GPIO5_BASE)   |= (1u << 1);   /* idle HIGH (PNP off, buzzer silent) */
}

/* Drive a square wave on GPIO5_IO01 at `hz`, for `ms` milliseconds.
 * Buzzer is sound-producing whenever PIN=0 (PNP on); we toggle around idle. */
void beep_tone(uint32_t hz, uint32_t ms)
{
    uint32_t half_period_us = 500000 / hz;   /* half-period in microseconds */
    uint32_t cycles = (uint32_t)((uint64_t)hz * ms / 1000);
    for (uint32_t i = 0; i < cycles; i++) {
        GPIO_DR(GPIO5_BASE) ^= (1u << 1);    /* toggle: 0 (on) / 1 (off) */
        udelay(half_period_us);
        GPIO_DR(GPIO5_BASE) ^= (1u << 1);
        udelay(half_period_us);
    }
    GPIO_DR(GPIO5_BASE) |= (1u << 1);        /* leave pin HIGH (silent) */
}
```

`beep_tone(1000, 200)` — a 1 kHz tone for 200 ms. Annoying but unambiguous.

A small but real bug to watch for: if you forget the final `GPIO_DR |= bit`, you may exit `beep_tone` with the PNP on and the buzzer stuck mid-cycle, drawing power and emitting a click. The explicit silencing line is not decoration.

### Why not just a GPIO toggle in a tight loop?

That works for tones in the multi-kHz range when nothing else is happening. It does *not* work the moment you want to play the tone *while* doing anything else. The right answer for production: drive BEEP from a **PWM peripheral** (i.MX6ULL has eight PWM channels), which generates the square wave in hardware. Chapter 48 (Linux PWM) covers exactly this — we plumb the same buzzer via the PWM framework instead of bit-banging.

For bare-metal pedagogy, the bit-bang loop is fine. It shows that the buzzer is just a frequency-controlled output.

## 18B.4  Putting it together

```c
#include "bsp_clk.h"
#include "bsp_gpio.h"
#include "bsp_uart.h"
#include "bsp_epit.h"
#include "bsp_delay.h"
#include "bsp_key.h"     /* new */
#include "bsp_beep.h"    /* new */
#include "imx6ull.h"

int printf(const char *fmt, ...);
extern void irq_enable(void);

void on_key_press(void)
{
    printf("press\r\n");
    GPIO_DR(GPIO1_BASE) ^= (1u << 4);   /* toggle LED */
}

void on_key_release(void)
{
    printf("release\r\n");
}

/* This function is the EPIT ISR's payload (registered in bsp_epit.c) */
void epit_tick_handler(void)
{
    key_tick();
}

int main(void)
{
    clk_init_main();
    uart_init();
    gic_init();
    led_init();        /* unchanged from Ch 9 */
    key_init();
    beep_init();
    epit_init(10);     /* 10 ms tick -> calls epit_tick_handler() */
    irq_enable();

    printf("\r\nButton + beep ready.\r\n");
    beep_tone(2000, 100);   /* startup chirp */

    for (;;) { asm volatile ("wfi"); }
}
```

Press the button. The LED toggles, the UART prints `press` / `release`, and the buzzer chirped once at boot. The main loop sleeps in `wfi` — all the interesting work happens in the EPIT ISR.

## 18B.5  Lab

1. **Build and run.** Confirm a single press gives a single `press`/`release` pair on UART, and the LED toggles cleanly.
2. **Disable the debounce.** Comment out the sliding-window check; respond to every raw edge. Time how many spurious events you get per real press. (10–50 is typical for a cheap tactile switch.)
3. **Double-tap detection.** Add a 300 ms timer: if two presses occur within 300 ms, beep at 4 kHz for 50 ms.
4. **Beep tones.** Play a 5-note sequence (C-D-E-F-G, 200 ms each). Hum the result; you should recognize the scale.
5. **Power measurement.** Compare current draw with and without `wfi` in `main`. The difference is the CPU's idle savings, which on Cortex-A7 is real.

Commit to `code/ch18B-button-beep/`.

## 18B.6  Pitfalls

- **GPIO5 vs GPIO1 clock gates.** GPIO5 is in the SNVS domain and has its own gate bit (CCGR1[31:30]). Easy to miss.
- **Active-low vs active-high.** Your schematic decides. If pressed-reads-1, your `key_history` test should be inverted.
- **EPIT tick too fast.** A 1 ms tick × 8-deep history = 8 ms of debounce, which is *too short* for many switches. 10 ms × 8 = 80 ms is safe.
- **`udelay(1)` calibration.** From Ch 16, `udelay` is GPT-based; should be accurate to within 1 µs. If your beep is off-pitch, GPT prescaler is wrong.
- **Floating button pin.** If the external 10 kΩ pull-up is missing, your reads are random. Always verify pull resistors with a scope (or just by reading the pin steady-state).
- **Active vs passive buzzer.** An *active* buzzer has its own oscillator inside; you drive it with DC. Toggling it at audio frequencies makes it click and buzz, not play tones. *Passive* needs a square wave. Check your part.

## 18B.7  Going deeper

- **IMX6ULLRM Chapter 28** — GPIO interrupt configuration (we ignored it here; Chapter 15's GIC code can be wired to a GPIO IRQ instead of using a polled tick).
- **Jack Ganssle**, *A Guide to Debouncing* — the canonical engineering reference. Available free online.
- **Linux source: `drivers/input/keyboard/gpio_keys.c`** — the kernel's gpio-keys driver. Reads GPIOs, debounces them, emits input events. We meet it in Chapter 45.
- **Linux source: `drivers/pwm/pwm-imx27.c`** — i.MX PWM driver, which we'll use in Chapter 48 to replace `beep_tone` with hardware PWM.

> Next chapter: **Chapter 18C — Bare-metal RTC.** The SNVS domain again, this time for timekeeping that survives main-power-off.
