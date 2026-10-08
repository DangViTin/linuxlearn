---
chapter: 18C
title: "Bare-metal RTC: SNVS, the always-on domain"
part: II - Bare-metal i.MX6ULL (inserted v1.1)
estimated_pages: 10
status: draft
---

# Chapter 18C: Bare-metal RTC

After a restart, the ordinary uptime counter begins again at zero. A log
timestamp should not. Which counter can keep advancing while the CPU and
DDR have no power, and how does the CPU read it after returning?

The **Secure Non-Volatile Storage (SNVS)** block has separate high-power
(HP) and low-power (LP) sections. We use its LP real-time counter and one
retained general-purpose register. "Always-on" is a supply requirement, not
a promise: if the LP supply disappears, so does its retained state.

This is a bare-metal counter/retention lab. Setting a counter to zero does
not set a wall clock, and deliberately causing a brown-out is not needed.
Keep Chapter 18A's startup, linker, toolchain, and fresh-ROM handoff policy;
initialize Chapter 16's GPT delay source before using the driver below.

## 18C.1  What the SNVS provides

The supplied **IMX6ULLRM Rev. 1, Chapter 48** describes:

- An HP real-time counter and its alarm, which lose state with system power.
- An LP section with the retained counter, control/security state, monotonic counter, and general-purpose register.
- A **32-bit LPGPR at offset 0x68** described in Section 48.7.14: retained space for one marker or counter, not a general byte-addressable buffer.
- A monotonic counter incremented by permitted **writes**, not automatically by every chip reset. It has security and fuse-era behavior; we do not use it as a reboot counter or program its fuses.

The public RM describes the LP counter but omits its register fields.
The starred entries in Section 18C.3 use the
[Linux v6.12 SNVS RTC implementation](https://github.com/torvalds/linux/blob/v6.12/drivers/rtc/rtc-snvs.c)
as an additional reference. [NXP's migration guide, Table 1](https://www.nxp.com/docs/en/application-note/AN5350.pdf)
and [clarification of the omission](https://community.nxp.com/t5/i-MX-Processors/The-LP-SNVS-RTC-in-the-iMX6ULL-what-is-the-story-about-it/m-p/833519?profile.language=ja)
explain the UL-to-ULL relationship. Obtain matching NXP security/reference
documentation for production use; this lab does not provision security.

## 18C.2  Powering SNVS

Follow the actual nets, rather than a generic VBAT label:

| Reference sheet | What it shows |
|---|---|
| MINI v2.2 sheet 4 | CR1, labelled 1220, feeding VDD_COIN_3V |
| CORE sheet 8, internal project CL6Y2CB_V1.9 | VDD_COIN_3V on J1 pin 41 |
| CORE sheet 2 | D1 from VDD_SNVS_3V3 and D2 from VDD_COIN_3V feeding VDD_SNVS_IN; R34 1.5 kOhm is also drawn across the coin-cell diode path |
| CORE sheet 6 | Y1 32.768 kHz at RTC_XTALI/RTC_XTALO, separate from the 24 MHz main reference |

These connections are not a battery compatibility or lifetime guarantee.
Check the fitted circuit, cell chemistry/polarity, and supplier-approved
arrangement, including any current through R34. Do not assume every "1220"
holder accepts a rechargeable cell or that a supercapacitor can be substituted.

The supplied industrial electrical datasheet
Sections 4.1.6.3 and 4.2 require the SNVS supply first on and last off, and
forbid externally driving an unpowered I/O domain. Follow the matching
datasheet and Chapter 8's power/back-power inventory. CPU register access
still needs the main-powered HP interface and its clocks; a coin cell
does not keep the Cortex-A7 or that bus interface running.

An ordinary main-power cycle can retain LP state when its supply remains
valid. It is different from LP power-on reset or LP software reset. With no
working backup path, warm reset may preserve the count while complete
power removal does not. Measure and document the supply conditions before
interpreting a retention result.

## 18C.3  Register map (relevant subset)

SNVS base is `0x020CC000`. Offsets here are relative to that base, **not**
to the LP subrange used by some Linux device-tree nodes.

| Register | Offset | Purpose |
|---|---|---|
| SNVS_HPLR | +0x00 | HP lock register; do not set locks in this lab |
| SNVS_HPCOMR | +0x04 | HP command/access policy; not an innocuous initialization write |
| SNVS_LPLR | +0x34 | LP lock register |
| SNVS_LPCR | +0x38 | LP control; SRTC_ENV is bit 0* |
| SNVS_LPSR | +0x4C | LP status, including write-one-to-clear fields |
| SNVS_LPSRTCMR* | +0x50 | Counter bits 46:32 in register bits 14:0 |
| SNVS_LPSRTCLR* | +0x54 | Counter bits 31:0 |
| SNVS_LPTAR* | +0x58 | LP alarm's 32-bit seconds value; not armed in this lab |
| SNVS_LPGPR | +0x68 | One 32-bit retained general-purpose register |

The LP counter is **47 bits of 32.768 kHz ticks**: 32 whole-second bits and
15 fractional bits. Form `((uint64_t)(hi & 0x7FFF) << 32) | lo`, then
shift right by 15. Equivalently, seconds are
`((hi & 0x7FFF) << 17) | (lo >> 15)`. At 32768 ticks, seconds must be 1;
at 65536 ticks, 2. These are useful arithmetic checks without a board.

The counter stores a number, not a calendar or a timezone. Software chooses
the epoch by setting that number. An unsigned 32-bit Unix-seconds choice
reaches its limit in 2106; a signed 32-bit software representation has a
different 2038 limit. Neither is a 64-bit-seconds hardware RTC.

## 18C.4  Driver

```{figure} ../illustrations/part2/13-rtc-counter-and-calendar.png
:alt: A whole-second value derived from the RTC counter is converted into a date and time using a software-chosen epoch. The counter does not supply a calendar itself.
:width: 100%
:figclass: concept-sketch
:name: fig-part2-rtc-calendar

The raw SNVS counter counts ticks. Here, "seconds" means the value after removing its fractional bits. Turning that number into a calendar needs an agreed epoch and software conversion. A running counter alone does not establish a valid date.
```

Add the following definitions inside `imx6ull.h`, keeping the hardware map
out of `bsp_rtc.c`. The starred offsets/bit use the implementation evidence
identified above:

```c
#define SNVS_BASE           0x020CC000u
#define SNVS_LPCR           (SNVS_BASE + 0x38u)
#define SNVS_LPSRTCMR       (SNVS_BASE + 0x50u)
#define SNVS_LPSRTCLR       (SNVS_BASE + 0x54u)
#define SNVS_LPGPR          (SNVS_BASE + 0x68u)
#define LPCR_SRTC_ENV       (1u << 0)
#define SRTC_MSB_MASK       0x7FFFu
#define CCGR_SNVS_HP_GATE   (3u << 18) /* CCGR5[19:18] */
#define CCGR_SNVS_LP_GATE   (3u << 20) /* CCGR5[21:20] */
```

Create `bsp/rtc/bsp_rtc.h`:

```c
#ifndef BSP_RTC_H
#define BSP_RTC_H
#include <stdint.h>

int rtc_init(void);
int rtc_get_seconds(uint32_t *seconds);
int rtc_set_seconds(uint32_t seconds);
uint32_t rtc_scratch_read(void);
int rtc_scratch_write(uint32_t value);

#endif
```

Create `bsp/rtc/bsp_rtc.c`:

```c
#include "bsp_rtc.h"
#include "bsp_delay.h"
#include "imx6ull.h"

static int rtc_enable(unsigned enable)
{
    uint32_t control = REG(SNVS_LPCR);
    if (enable != 0u)
        control |= LPCR_SRTC_ENV;
    else
        control &= ~LPCR_SRTC_ENV;
    REG(SNVS_LPCR) = control;

    for (unsigned attempt = 0u; attempt < 1000u; ++attempt) {
        unsigned running = (REG(SNVS_LPCR) & LPCR_SRTC_ENV) != 0u;
        if (running == (enable != 0u))
            return 0;
        udelay(10u);
    }
    return -1;
}

int rtc_init(void)
{
    REG(CCM_CCGR5) |= CCGR_SNVS_HP_GATE | CCGR_SNVS_LP_GATE;
    return rtc_enable(1u);           /* Preserve the existing counter value. */
}

static uint64_t rtc_raw(void)
{
    uint32_t hi = REG(SNVS_LPSRTCMR) & SRTC_MSB_MASK;
    uint32_t lo = REG(SNVS_LPSRTCLR);
    return ((uint64_t)hi << 32) | lo;
}

int rtc_get_seconds(uint32_t *seconds)
{
    if (seconds == 0)
        return -1;

    /* Compare complete samples, not only the upper word. */
    uint64_t previous = rtc_raw();
    for (unsigned attempt = 0u; attempt < 100u; ++attempt) {
        uint64_t current = rtc_raw();
        if (current == previous) {
            *seconds = (uint32_t)(current >> 15);
            return 0;
        }
        previous = current;
    }
    return -1;                      /* No output update on failure. */
}

int rtc_set_seconds(uint32_t seconds)
{
    if (rtc_enable(0u) != 0)
        return -1;                  /* Never write a running/locked counter. */

    REG(SNVS_LPSRTCLR) = seconds << 15;
    REG(SNVS_LPSRTCMR) = seconds >> 17;
    return rtc_enable(1u);
}

uint32_t rtc_scratch_read(void)
{
    return REG(SNVS_LPGPR);
}

int rtc_scratch_write(uint32_t value)
{
    REG(SNVS_LPGPR) = value;
    for (unsigned attempt = 0u; attempt < 1000u; ++attempt) {
        if (REG(SNVS_LPGPR) == value)
            return 0;
        udelay(10u);
    }
    return -1;
}
```

The setter clears SRTC_ENV, waits for the observed state, writes the low
word and high word with fractional bits zero, then re-enables and waits
again. It preserves the other LPCR fields. At most 1000 failed polls request
10 us delays: roughly 10 ms plus GPT guard ticks and software overhead,
not a hard wall-clock deadline. This assumes GPT delays already work.
A failed restart can leave the counter stopped. Report the error and
inspect access/lock/clock state rather than proceeding as though time was set.

RM 48.6.2 describes both asynchronous sampling and a split-register update
hazard. A high-low-high read addresses carry between words but not every
partially synchronized value. This small driver requires two identical
**whole-counter samples**, with a bounded retry. Linux instead accepts a
small forward difference between full samples. Equality is practical for
fast polled reads between 32 kHz ticks, but can time out on a slow or
interrupted access path. Neither a retry count nor compilation certifies
the hardware's clock/synchronization behavior.

A stopped counter can also return a stable value. The getter checks read
consistency; enable-state readback and successive time readings tell us
whether it is running and advancing.

This driver deliberately does **not** set HPCOMR.NPSWA_EN. RM 48.7.2 says
that bit broadens non-privileged access; privileged execution does not make
the write a harmless no-op. Access rights, security state, and locks must
already permit this development-board experiment. The upstream driver also
initializes the power-glitch detector and clears status during probe. We
do not copy its blanket status clear into a bare-metal security policy:
pending tamper/security indications must not be erased just to obtain a
successful lab. A cold-board failure may require vendor-documented SNVS
initialization for the exact device/provisioning. Stop there, without guessed
security-bit writes, LP reset, or fuse changes.

LPGPR can be locked or cleared by documented reset/tamper behavior. The
write helper checks readback and reports failure. That is evidence of a
matching read, not proof that a previously equal value was newly written
or that it will survive power loss. Use only a board on which this register
is not owned by boot/security software. Do not interpret arbitrary retained
data as tamper-proof storage.

## 18C.5  Test program

This program first reads the existing counter. It does **not** reset time
on every boot or infer time validity from a marker. Set the lab constant to
1 only for one deliberate initialization run, then build with it back at 0
before the retention test. A bootloader or later Linux RTC driver must not
also reset the counter during that test.

The application uses the Chapter 12 mini-printf formats `%u` and `%02u`;
its formatter does not support `%lu` or a 64-bit length modifier. Cast
variadic arguments to the unsigned type it expects.

```c
#include <stdint.h>
#include "bsp_clk.h"
#include "bsp_uart.h"
#include "bsp_gpt.h"
#include "bsp_delay.h"
#include "bsp_rtc.h"

#define SET_RTC_ON_THIS_BOOT 0

int printf(const char *fmt, ...);

static void stop(const char *message)
{
    printf("%s\r\n", message);
    for (;;) { }
}

static void print_seconds(uint32_t seconds)
{
    uint32_t days = seconds / 86400u;
    uint32_t rest = seconds % 86400u;
    printf("%u days, %02u:%02u:%02u",
           (unsigned)days, (unsigned)(rest / 3600u),
           (unsigned)((rest / 60u) % 60u), (unsigned)(rest % 60u));
}

int main(void)
{
    clk_enable_lab_gates();
    uart_init();
    uint32_t ipg_hz = clocks_get_ipg_hz();
    if (gpt_init(ipg_hz) != 0)
        stop("GPT setup failed; inspect the clock audit.");
    if (rtc_init() != 0)
        stop("RTC enable timed out; inspect clocks, access, and locks.");

    if (SET_RTC_ON_THIS_BOOT != 0) {
        if (rtc_set_seconds(0u) != 0)
            stop("RTC set failed.");
        if (rtc_scratch_write(0x52544331u) != 0)
            stop("LPGPR readback failed; do not claim retention.");
    }
    printf("LPGPR = 0x%08x\r\n", (unsigned)rtc_scratch_read());

    for (;;) {
        uint32_t seconds;
        if (rtc_get_seconds(&seconds) != 0)
            stop("RTC read did not stabilize.");
        printf("[RTC = %u s] ", (unsigned)seconds);
        print_seconds(seconds);
        printf("\r\n");
        mdelay(1000u);
    }
}
```

With the one-time zero setting, the display means elapsed time since that
setting, including time the CPU was off. It is not this boot's uptime.
If you instead set Unix seconds, the same day/hour decomposition remains a
numeric interval; it is not yet a date conversion. UART output and the
foreground delay also mean lines are not an exact one-second measurement
cadence. Compare counter differences with an independent elapsed-time source.

(c-6-the-brown-out-demo)=
## 18C.6  Controlled retention check

Use **controlled main-power removal**, not an induced brown-out. Keep the
backup supply valid throughout; undervoltage and rail manipulation are not
part of this experiment.

Before removing anything, confirm the supplier-approved backup arrangement,
the board revision, and all main-power/back-power paths. Follow the Chapter
8 checks and the datasheet's supply order. The supplied schematics alone
do not establish a universal unplugging recipe.

1. In the one-time initialization build, set zero and a marker, and check that the counter advances. Record the value and an independent time reference.
2. Rebuild with SET_RTC_ON_THIS_BOOT = 0. Boot this read-only-time version and confirm it does not change the counter. Keep this exact image for the restart.
3. Remove main power by the approved procedure while maintaining the verified SNVS supply. Account for DC input, USB-TTL, USB-OTG, debug adapters, and powered add-ons. Disconnecting one VBUS cable does not establish that main rails are off.
4. After a recorded off interval, restore main power and load the same image by the fresh-ROM route. Compare the counter advance with **all elapsed time between readings**, including startup and download, and check LPGPR separately.

A retained marker and an advancing counter test different things. A marker
can remain while the counter stops; a running counter does not prove that
every retained register is valid. Do not invent a fixed two-second advance
or unexplained "settling slack." If the readings disagree, investigate the
supply, clock, resets, and intervening firmware.

## 18C.7  Lab

1. **Build and inspect.** Use Chapter 18A's integer-only flags and explicit libgcc link. Confirm GPT initialization precedes RTC polling. With hardware prerequisites satisfied, verify that the counter advances at approximately one second per elapsed second.
2. **Retention test.** Use Section 18C.6. Record the off interval and total read-to-read interval, not just the time spent unplugged.
3. **Software boot count.** As a separate experiment, reserve the single LPGPR for a count. Read it, handle an uninitialized/saturated value deliberately, write the increment, and verify readback. It counts executions reaching that code, not every reset, and is not tamper evidence. Do not also store the marker in the same word.
4. **Model backup loss first.** Predict what LP POR would erase and how the program detects invalid data. Actual backup removal is optional only under the matching board's approved procedure, with all other sources off and SNVS removed last/restored first. Do not pull a cell from a powered board or short a supply to force a reset.
5. **Unix time.** Parse a UART command such as t=1716595200 with overflow/error checks and require a value within UINT32_MAX. Call the setter only after accepting the command; read it back and report failure. Calendar conversion and timezone display are software work. Retain UTC as the stored convention and test leap-year/month boundaries in your conversion code.

## 18C.8  Pitfalls

- **Confusing 47-bit ticks with seconds.** The high register contributes 15 bits, the low 32; the lowest 15 bits are fractional. One tick is not one second.
- **Using an LP-relative offset with the full base.** Linux may add 0x34 before its LP-local offsets. Here +0x50 and +0x54 are already relative to 0x020CC000.
- **Reading only high-low-high.** Carry protection alone does not address asynchronous sampling. Compare full samples and report exhausted retries.
- **Writing before observed disable.** Do not merely clear SRTC_ENV and immediately write the counter. The transition crosses clock domains, and locks/access state can prevent it.
- **Treating access-policy writes as harmless.** NPSWA_EN changes who can access privileged registers. Do not broaden permissions, clear security status, or program locks/fuses in this lab.
- **Assuming six scratch words.** This subset uses only the documented 32-bit LPGPR. Other SoC variants and separate GPR blocks are not evidence for consecutive scratch RAM here.
- **A marker that proves too much.** It is application data, not proof of battery health, RTC accuracy, or resistance to resets/tampering.
- **A frozen counter with a readable interface.** Enable readback alone is not proof that the 32 kHz timebase advances. Check successive seconds as well as control state.

## 18C.9  Going deeper

- **IMX6ULLRM Rev. 1, Chapter 48**: HP/LP domains, synchronization guidance, locks, access policy, and LPGPR. Note its LP RTC field omissions.
- **Supplied industrial/commercial datasheets**, Sections 4.1.6 and 4.2, plus **MINI sheet 4 / CORE sheets 2, 6, 8**: supply states, ordering, crystal, and the real backup route.
- **AN5350, i.MX 6ULL Migration Guide**, and the linked NXP clarification: the UL-to-ULL SNVS relationship and the missing public register fields.
- **Linux drivers/rtc/rtc-snvs.c**: the LP offsets, 47-bit conversion, full-sample retry, enable/disable acknowledgement, and separate alarm setup. Chapter 48 introduces the Linux RTC interface.
- **POSIX time(), gmtime(), localtime()**: software epoch/calendar/timezone services. They do not supply a bare-metal RTC driver merely by being declared.

---

Chapters 18A-18C supplement Part II. The button and RTC implementations use
the Chapter 18A layout and earlier startup, UART, and delay code; they are
not independent copy-and-boot projects. From here, Chapter 19 moves to
U-Boot, which prepares hardware and loads the next image before Linux runs.

> Next chapter: **Chapter 19: U-Boot from source, first boot.**
