---
chapter: 18C
title: Bare-metal RTC — SNVS, the always-on domain
part: II — Bare-metal i.MX6ULL (inserted v1.1)
estimated_pages: 10
status: draft
---

# Chapter 18C — Bare-metal RTC

> **What:** access the **SNVS** (Secure Non-Volatile Storage) RTC on i.MX6ULL: set the wall-clock time, read it back at runtime, and watch it survive a deliberate main-power brown-out.
>
> **Why:** Any product that needs to log timestamps, run scheduled actions, or check license expiration relies on an RTC that survives power cycles. SNVS is the only always-on domain on i.MX6ULL; we need to know how to talk to it.
>
> **Focus:** the separate power domain. SNVS has its own supply pin (`VDD_SNVS_IN`, usually tied to a coin cell or supercap), its own 32.768 kHz oscillator, and its own counter. When the rest of the SoC sleeps or browns out, SNVS keeps counting.

## 18C.1  What the SNVS provides

The i.MX6ULL SNVS block (RM Chapter 47) contains:

- A **32-bit second counter** (`SNVS_LPSRTCMR` high word, `SNVS_LPSRTCLR` low word) — when concatenated, a 64-bit count of seconds since "SNVS was first powered."
- A separate **alarm register** (`SNVS_LPTAR`) — fires an interrupt when `LPSRTC == LPTAR`.
- 24 bytes of always-on **scratch SRAM** (`SNVS_LPGPR0..LPGPR5`) — survives main-power-off as long as VDD_SNVS_IN has power.
- A **monotonic counter** that increments on every chip reset — useful as a tamper-evident reboot counter.
- A small set of **tamper inputs** that, on certain board designs, trigger erasure of secure secrets.

For this chapter we use only the second counter, the scratch SRAM (LPGPR registers), and we read but do not arm the alarm.

## 18C.2  Powering SNVS

The Point Atom MINI exposes a **VBAT** pin on the schematic (typically populated with a CR1220 coin cell holder or a small supercap). When main power is removed, VDD_SNVS_IN is supplied from VBAT. While the SoC's main rails are off, SNVS's 32 kHz oscillator continues, its counter continues to increment, and its LPGPR scratch SRAM retains its contents.

If your board has no battery: SNVS still works, but power-loss = SNVS reset. Useful for boot-counting but not for wall-clock survival across reboots.

The clocks the SNVS controller needs come from:

- **`xtal32k`**: the 32.768 kHz crystal (always on while SNVS has power)
- **`ipg`** for the register interface (only needed when CPU is alive and accessing SNVS)

## 18C.3  Register map (relevant subset)

SNVS base = `0x020CC000` (RM ch. 47).

| Register | Offset | Purpose |
|----------|--------|---------|
| `SNVS_HPLR` | `+0x00` | High-power lock register |
| `SNVS_HPCOMR` | `+0x04` | High-power command |
| `SNVS_HPSR` | `+0x14` | High-power status |
| `SNVS_LPCR` | `+0x38` | Low-power control |
| `SNVS_LPSR` | `+0x4C` | Low-power status |
| `SNVS_LPSRTCMR` | `+0x50` | Secure RTC, upper 32 bits (47:32) |
| `SNVS_LPSRTCLR` | `+0x54` | Secure RTC, lower 32 bits (31:0) — count of 32 kHz ticks |
| `SNVS_LPTAR` | `+0x58` | Alarm register |
| `SNVS_LPGPR0..5` | `+0x68..7C` | 24 bytes of scratch SRAM |

The actual counter ticks at **32 kHz**, but the architectural view splits it: bit 14 of `LPSRTCLR` increments at 2 Hz; treat **upper 32 bits of the 48-bit concatenation** as seconds.

For the purposes of this chapter we use a simpler model: read `LPSRTCMR` and `LPSRTCLR`, concatenate as 48 bits, shift right by 15 to get seconds. (Why 15: 32768 = 2^15, so each tick is 1/2^15 of a second; shifting right by 15 divides ticks by 32768.) Verify the exact bit layout against your RM revision.

## 18C.4  Driver

`bsp_rtc.h`:

```c
#ifndef __BSP_RTC_H__
#define __BSP_RTC_H__
#include <stdint.h>

void rtc_init(void);
uint64_t rtc_get_seconds(void);
void rtc_set_seconds(uint64_t s);

uint32_t rtc_scratch_read(int idx);    /* idx in 0..5 */
void rtc_scratch_write(int idx, uint32_t v);

#endif
```

`bsp_rtc.c`:

```c
#include "bsp_rtc.h"
#include "imx6ull.h"

#define SNVS_BASE       0x020CC000U
#define SNVS_HPCOMR     (SNVS_BASE + 0x04)
#define SNVS_LPCR       (SNVS_BASE + 0x38)
#define SNVS_LPSRTCMR   (SNVS_BASE + 0x50)
#define SNVS_LPSRTCLR   (SNVS_BASE + 0x54)
#define SNVS_LPGPR(n)   (SNVS_BASE + 0x68 + 4*(n))

#define HPCOMR_NPSWA_EN (1u << 31)
#define LPCR_SRTC_ENV   (1u << 0)

void rtc_init(void)
{
    /* Allow non-privileged software access (we run in PL1; this is a no-op
     * for our case but harmless). */
    REG(SNVS_HPCOMR) |= HPCOMR_NPSWA_EN;

    /* Enable the Secure RTC counter, if not already running. */
    REG(SNVS_LPCR) |= LPCR_SRTC_ENV;

    /* Wait for it to actually start. */
    while ((REG(SNVS_LPCR) & LPCR_SRTC_ENV) == 0) { }
}

uint64_t rtc_get_seconds(void)
{
    /* Read twice and retry on rollover. The high word can increment
     * between our reads of low and high. */
    uint32_t hi1, hi2, lo;
    do {
        hi1 = REG(SNVS_LPSRTCMR);
        lo  = REG(SNVS_LPSRTCLR);
        hi2 = REG(SNVS_LPSRTCMR);
    } while (hi1 != hi2);

    /* The 48-bit raw count is (hi << 32) | lo, in 32 kHz ticks.
     * Shift right by 15 to convert to seconds. */
    uint64_t raw = ((uint64_t)hi1 << 32) | lo;
    return raw >> 15;
}

void rtc_set_seconds(uint64_t s)
{
    /* The Secure RTC must be disabled to write a new value. */
    REG(SNVS_LPCR) &= ~LPCR_SRTC_ENV;
    while (REG(SNVS_LPCR) & LPCR_SRTC_ENV) { }

    uint64_t raw = s << 15;
    REG(SNVS_LPSRTCMR) = (uint32_t)(raw >> 32);
    REG(SNVS_LPSRTCLR) = (uint32_t)raw;

    /* Re-enable. */
    REG(SNVS_LPCR) |= LPCR_SRTC_ENV;
    while ((REG(SNVS_LPCR) & LPCR_SRTC_ENV) == 0) { }
}

uint32_t rtc_scratch_read(int idx)
{
    if (idx < 0 || idx > 5) return 0;
    return REG(SNVS_LPGPR(idx));
}

void rtc_scratch_write(int idx, uint32_t v)
{
    if (idx < 0 || idx > 5) return;
    REG(SNVS_LPGPR(idx)) = v;
}
```

## 18C.5  Test program

```c
#include "bsp_clk.h"
#include "bsp_uart.h"
#include "bsp_rtc.h"
#include "bsp_delay.h"

int printf(const char *fmt, ...);

static void format_secs(uint64_t s, char *out)
{
    /* Print as DDD:HH:MM:SS for the casual case (RTC seconds since enable). */
    uint32_t days = (uint32_t)(s / 86400);
    s %= 86400;
    uint32_t h = (uint32_t)(s / 3600);
    s %= 3600;
    uint32_t m = (uint32_t)(s / 60);
    uint32_t sec = (uint32_t)(s % 60);
    /* Use mini_printf style; here just sprintf via uart_puts: */
    static char buf[40];
    /* Implement with multiple uart_puts() calls instead of sprintf to
     * keep dependencies minimal. */
    (void)out; (void)buf; (void)days; (void)h; (void)m; (void)sec;
    printf("%u days, %02u:%02u:%02u", days, h, m, sec);
}

int main(void)
{
    clk_init_main();
    uart_init();
    rtc_init();

    /* Has SNVS been set before?  Use scratch[0] as a magic-marker.
     * If 0xDEADBEEF, the RTC has been initialized previously. */
    if (rtc_scratch_read(0) != 0xDEADBEEF) {
        printf("First boot since SNVS power-on; setting time.\r\n");
        rtc_set_seconds(0);
        rtc_scratch_write(0, 0xDEADBEEF);
    } else {
        printf("SNVS survived power-cycle.  Reading time.\r\n");
    }

    for (;;) {
        uint64_t s = rtc_get_seconds();
        printf("[t = %lu s] uptime: ", (unsigned long)s);
        format_secs(s, 0);
        printf("\r\n");
        mdelay(1000);
    }
}
```

## 18C.6  The brown-out demo

Run this lab to see SNVS in action.

1. Boot, set the wall clock, observe the counter ticking up.
2. Power-cycle the board (just unplug VBUS; keep the coin cell installed).
3. Re-power. Observe the counter resumes from where it left off, *plus* the ~2 seconds you spent unplugged.

The scratch SRAM at `LPGPR0..5` also survives. You can write a counter into it, increment every reboot, and observe an "n-th boot" indicator that the SoC reset cannot clear. Useful in production for tamper detection and reboot accounting.

## 18C.7  Lab

1. **Build and run §18C.5.** Confirm the counter advances at 1 Hz.
2. **Brown-out test.** As described above. Don't expect millisecond accuracy across the power cycle. The first read after power-on may show 1–2 seconds of slack while SNVS internals settle.
3. **Boot counter.** Add a `boot_count = rtc_scratch_read(1); rtc_scratch_write(1, boot_count + 1);` to `main`. Print it at startup. Power-cycle 10 times; confirm it counts up.
4. **Lose VBAT.** If your coin cell is removable, pop it out, power-cycle the main rail, observe the SNVS reset (boot_count back to 0, scratch RAM at `0xDEADBEEF` lost).
5. **Wall-clock UNIX time.** Have the user enter `t=1716595200\n` over UART; call `rtc_set_seconds`. Then print the date in a real human-readable form (`gmtime`-style). This is a small but pleasant integration exercise.

## 18C.8  Pitfalls

- **Reading the counter without rollover protection.** Without the `do { hi1 = ...; lo = ...; hi2 = ...; } while (hi1 != hi2);` pattern, you can occasionally read a stale `hi` paired with an already-incremented `lo`. The error is rare (~once per 2^15 reads) but real.
- **Forgetting that scratch SRAM is only 24 bytes.** Six 32-bit words. Allocate carefully.
- **Writing to LPSRTC while it's running.** The RM requires you to clear `LPCR_SRTC_ENV` first. Our `rtc_set_seconds` does this.
- **No VBAT supply.** Behavior is identical until you power-cycle. Then SNVS resets. Symptom: the boot-counter mysteriously resets to zero only on power-cycle, not on warm-reset. The fix is in hardware.
- **SNVS tamper inputs floating.** If your board exposes tamper pins (TAMPER_IN_x) and they float, the SNVS may go into "tampered" state and refuse to release secrets. Tie them via the schematic.

## 18C.9  Going deeper

- **IMX6ULLRM Chapter 47** — SNVS, complete register description. Most of the chapter is about secure features (tamper, key zeroize) we did not touch.
- **AN12077** — *i.MX 6/7 Series SNVS Application Note*. Concise overview, with circuit examples for VBAT supply.
- **Linux source: `drivers/rtc/rtc-snvs.c`** — the kernel's SNVS RTC driver. Same registers, full implementation. We meet it in Chapter 48.
- **POSIX `time()`, `gmtime()`, `localtime()`** — what user-space sees of all this once Linux is running.

---

End of Part II's inserted chapters. Part II proper ends with Chapter 18. Chapters 18A–C are supplementary deep-dives; read them in any order, or skip them entirely.

> Next chapter: **Chapter 19 — U-Boot from source, first boot.** With the bare-metal foundation in place, we move from writing it ourselves to reading a real bootloader that does the same things.
