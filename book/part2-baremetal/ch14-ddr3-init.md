---
chapter: 14
title: DDR3 initialization with MMDC
part: II — Bare-metal i.MX6ULL
estimated_pages: 30
status: draft
---

# Chapter 14 — DDR3 initialization with MMDC

> **What:** code that takes the Point Atom MINI's DDR3 chip from "powered on but uninitialized" to "512 MiB of usable memory at `0x80000000`," by hand. Then code that copies itself from OCRAM to DRAM and continues running from DRAM.
> **Why:** until this works, your bare-metal world is 100 KB. After it works, it is 512 MiB. More fundamentally: every dev board you have ever used had someone solve this problem for you in a vendor BSP. Solving it once yourself collapses several "magic" layers down to "I know what those registers do."
> **Focus:** the **JEDEC initialization sequence** for DDR3 — universal — and the **MMDC register groups** that implement it — i.MX-specific. Understanding both means you can port to a different DRAM part or different SoC without panic.

## 14.1  This chapter takes time

Set an afternoon aside. This is the most complex bring-up step in the book. The number of values that must be exactly right is large; the diagnostic for "wrong value" is usually "DRAM doesn't work." When DRAM doesn't work, you cannot `printf` from DRAM, cannot load test patterns into DRAM, cannot do much.

We will keep the entire chapter in **OCRAM** until the very last section, where DRAM works and we relocate to it.

## 14.2  DDR3, in just enough detail

A DDR3 chip is a 2D array (or 3D, with multiple banks) of capacitor cells, accessed by:

- **Activate** a row in a bank: latches the row's contents into a sense-amplifier ("page open").
- **Read or Write** a column within the open row: data flows on the bus.
- **Precharge** the bank: closes the page and prepares for the next activation.
- **Refresh** all rows periodically: capacitors leak; without refresh, data is lost in ~64 ms.

The controller schedules these operations subject to **timing parameters**:

| Symbol | Meaning | Typical (DDR3-1600) |
|--------|---------|---------------------|
| `tRCD` | Row-to-column delay | 13.75 ns |
| `tRP`  | Precharge time | 13.75 ns |
| `tRAS` | Row-active time min | 35 ns |
| `tRC`  | Row cycle time (= tRAS + tRP) | 48.75 ns |
| `tRFC` | Refresh cycle time | 260 ns (4 Gb) |
| `tWR`  | Write recovery time | 15 ns |
| `tFAW` | Four-activate window | 40 ns |
| `CL`   | CAS latency | 11 clocks @ DDR3-1600 |
| `tWL`  | Write latency | CL - 2 = 9 clocks |
| `tREFI` | Average refresh interval | 7.8 µs |

These come from the **chip's datasheet**. You cannot guess them; you must look them up. Our Point Atom MINI has a Micron MT41K128M16 (typical) — 256 MB, 16-bit, ×2 chips for 512 MiB total, ×8 banks each, 14-bit row × 10-bit column.

> **The first thing you do in this chapter is open your specific DDR chip's datasheet.** If you guess timings, the DRAM may "kind of work" — pass a 1 MB memtest, fail at 16 MB — which is the worst kind of bug. Look up your part. Write the timings down. They feed every register value below.

## 14.3  Two chips, one bus — channels, ranks, banks

The MMDC controller on i.MX6ULL is **16 bits wide**. The Point Atom MINI uses **two ×8 DDR3 chips in parallel** to form a 16-bit bus. (Some variants use a single ×16 chip; same idea.) Both chips receive the same address and command; one drives bus bits [7:0], the other [15:8].

A "rank" is a set of chips that share a Chip Select. The MINI has **1 rank**. (Larger boards might have 2 ranks on the same channel; a CS0/CS1 pair selects between them.) Each chip has 8 internal banks; the controller can have up to 8 banks open at once (interleaved).

Total capacity:

```
chip:    256 MB × 2 chips    = 512 MiB
or:      4 Gb total × 1 rank = 4 Gb = 512 MiB
```

This matches the MINI's "512 MB DDR3" spec.

## 14.4  The MMDC register groups

MMDC base = `0x021B0000` (MMDC0; only one channel on i.MX6ULL). The registers fall into groups by responsibility:

| Group | Address range | Purpose |
|-------|--------------|---------|
| MDCTL | `+0x000` | Master control: rank/bank/row/col counts, bus width |
| MDPDC | `+0x004` | Power-down config |
| MDOTC | `+0x008` | ODT timing |
| MDCFG0 | `+0x00C` | tRFC, tXS, tXP, tXPDLL |
| MDCFG1 | `+0x010` | tRP, tRAS, tRC, tRPA, tWR, tMRD, tCWL |
| MDCFG2 | `+0x014` | tDLLK, tRTP, tWTR, tRRD |
| MDMISC | `+0x018` | DDR type, bank interleave, mode flags |
| MDSCR | `+0x01C` | Command register (Mode Register Set, ZQ calibration, etc.) |
| MDREF | `+0x020` | Refresh control |
| MDPDC | (rep) | (alias) |
| MDRWD | `+0x02C` | Read/write data path delay |
| MDOR | `+0x030` | Out-of-reset timing |
| MAARCR | `+0x040` | Auto-refresh control |
| MAPSR | `+0x404` | Power saving / status |
| MPZQHWCTRL | `+0x800` | ZQ calibration control |
| MPWLGCR | `+0x808` | Write leveling start |
| MPWLDECTRL0 | `+0x80C` | Write leveling delay 0 |
| MPWLDECTRL1 | `+0x810` | Write leveling delay 1 |
| MPDGCTRL0 | `+0x83C` | DQS gating delay 0 |
| MPDGCTRL1 | `+0x840` | DQS gating delay 1 |
| MPRDDLCTL | `+0x848` | Read delay |
| MPWRDLCTL | `+0x850` | Write delay |
| MPRDDQBY0DL..3DL | `+0x860..86C` | Per-byte read DQ delay |
| MPMUR0 | `+0x8B8` | Calibration request |

There are more. Don't memorize them; learn the *groups*.

The order in which we write these matters less than you'd think, with one important exception: **MDSCR (the command register)** is how we send DDR3 commands to the chip (load mode register, ZQ cal, refresh, etc.). It must be used at specific points in the sequence; otherwise it is one register among many.

## 14.5  IOMUX before MMDC

The DDR3 bus pins (DDR_ADDR, DDR_DQ, DDR_DQS, etc.) need their drive strength and ODT (On-Die Termination) configured **before** the controller starts driving them. These live in IOMUXC under names like `IOMUXC_SW_PAD_CTL_PAD_DRAM_*`.

Typical settings:

| Pin group | PAD_CTL value | Meaning |
|-----------|---------------|---------|
| `DRAM_ADDR*`, `DRAM_RAS_B`, `DRAM_CAS_B`, etc. | `0x000000F0` | Strong drive, no pull |
| `DRAM_DQ[15:0]`, `DRAM_DQS[1:0]_B`, `DRAM_DQS[1:0]` | `0x00000030` | Slightly weaker; ODT capable |
| `DRAM_SDQS[1:0]_B`, `DRAM_SDQS[1:0]` | `0x00000030` | |
| `DRAM_RESET`, `DRAM_ODT[1:0]`, `DRAM_CKE[1:0]`, `DRAM_SDCKE[1:0]` | `0x000030B0` | With keeper for stable idle |

There are about 80 DRAM pin pads on i.MX6ULL; configuring them all takes ~30 register writes. Source: RM Chapter 32 → search for "DRAM" pad names.

> **Why pad config first?** Because the MMDC controller, once enabled, starts driving these pins. If their drive strength is wrong, the signals are weak (under-drive: ringing, EMI) or unstable (over-drive: cross-talk).

## 14.6  The JEDEC DDR3 initialization sequence

Independent of which controller you use, DDR3 requires this sequence after power-on:

1. **De-assert RESET#** after at least 200 µs (with stable clock and Vdd).
2. **De-assert CKE** after at least 500 µs since power-on.
3. Issue **NOPs** for at least 500 µs.
4. **MRS — Load Mode Register 2 (MR2):** CWL, ASR (auto self-refresh).
5. **MRS — Load Mode Register 3 (MR3):** typically 0.
6. **MRS — Load Mode Register 1 (MR1):** ODT, DLL enable, output drive, Rtt_Nom, write leveling off.
7. **MRS — Load Mode Register 0 (MR0):** Burst length, CL, DLL reset.
8. **ZQ calibration long (ZQCL):** wait for completion.
9. Optionally: **Write leveling**, **DQS gating calibration**, **Read calibration**.
10. **Enable refresh.**

The MMDC controller does most of this for you via the **MDSCR** command interface, but you still configure each MR's value (which goes into MDSCR.CMD_VAL and is sent to the chip).

### Mode Register encodings (relevant fields)

**MR0** (operating mode):

| Bits | Field | Our value |
|------|-------|----------|
| 1:0 | Burst length | 00 (BL8 fixed) |
| 6:4 + 2 | CAS latency | CL = 11 → 1110_1 → 0b01110 |
| 8 | DLL reset | 1 (reset DLL at init) |
| 11:9 | Write recovery (tWR) | depends; for tWR=15ns@800MHz, 6 ⇒ 0b101 |

**MR1**:

| Bits | Field | Our value |
|------|-------|----------|
| 0 | DLL enable | 0 (enabled, active-low) |
| 2,6 | Output drive | RZQ/7 (typical) |
| 1,5,9 | Rtt_Nom | RZQ/4 = 60 Ω (typical) |
| 7 | Write leveling | 0 (off) |

**MR2**: ODT for Rtt_WR; CWL.

**MR3**: typically 0.

For our part with CL=11 and CWL=8:

- MR0 = `0x00000A50` (depends on exact tWR/CL; this is a representative value)
- MR1 = `0x00000044`
- MR2 = `0x00000018`
- MR3 = `0x00000000`

> **Real numbers will differ.** I gave illustrative bit patterns; you must compute yours from your DDR3 chip's datasheet, your target clock, and your tWR/CL choices. NXP's DDR Stress Tool (§14.13) is the easiest way to derive them.

## 14.7  A complete DDR3 init for the Point Atom MINI

Below is the bring-up function. It is long; that is the nature of DDR. Read it; do not run it without first running NXP's DDR Stress Tool on your specific board and replacing the calibration values.

`ddr.h`:

```c
#ifndef DDR_H
#define DDR_H
void ddr_init(void);
int  ddr_selftest(void);   /* returns 0 on success */
#endif
```

`ddr.c` (abbreviated to the structural skeleton; the full version is in `code/ch14-ddr/`):

```c
#include "ddr.h"
#include <stdint.h>
#define REG(addr) (*(volatile uint32_t *)(addr))

#define MMDC0_BASE       0x021B0000
#define MMDC_MDCTL       (MMDC0_BASE + 0x000)
#define MMDC_MDPDC       (MMDC0_BASE + 0x004)
#define MMDC_MDOTC       (MMDC0_BASE + 0x008)
#define MMDC_MDCFG0      (MMDC0_BASE + 0x00C)
#define MMDC_MDCFG1      (MMDC0_BASE + 0x010)
#define MMDC_MDCFG2      (MMDC0_BASE + 0x014)
#define MMDC_MDMISC      (MMDC0_BASE + 0x018)
#define MMDC_MDSCR       (MMDC0_BASE + 0x01C)
#define MMDC_MDREF       (MMDC0_BASE + 0x020)
#define MMDC_MDRWD       (MMDC0_BASE + 0x02C)
#define MMDC_MDOR        (MMDC0_BASE + 0x030)
#define MMDC_MAPSR       (MMDC0_BASE + 0x404)
#define MMDC_MPZQHWCTRL  (MMDC0_BASE + 0x800)
#define MMDC_MPWLGCR     (MMDC0_BASE + 0x808)
#define MMDC_MPWLDECTRL0 (MMDC0_BASE + 0x80C)
#define MMDC_MPDGCTRL0   (MMDC0_BASE + 0x83C)
#define MMDC_MPRDDLCTL   (MMDC0_BASE + 0x848)
#define MMDC_MPWRDLCTL   (MMDC0_BASE + 0x850)
#define MMDC_MPMUR0      (MMDC0_BASE + 0x8B8)

#define IOMUXC_DRAM_PADS_BASE 0x020E0290    /* approximate; see RM */

static void ddr_iomux(void)
{
    /* ---- Address / control pads: strong drive, no pull ---- */
    /* (For brevity, only key pads shown.  Full list in code/ch14-ddr/.) */
    REG(0x020E0500) = 0x000000F0;   /* DRAM_ADDR00 .. */
    /* ... (all DRAM pads) ... */
}

static void ddr_calibrate(void)
{
    /* These values come from the DDR Stress Tool.
       They are SPECIFIC to your board's layout and DRAM. */
    REG(MMDC_MPWLDECTRL0) = 0x001F001F;
    REG(MMDC_MPDGCTRL0)   = 0x4140414C;
    REG(MMDC_MPRDDLCTL)   = 0x40404546;
    REG(MMDC_MPWRDLCTL)   = 0x40402E32;
}

void ddr_init(void)
{
    ddr_iomux();

    /* ---- MMDC core configuration ---- */
    REG(MMDC_MDMISC)  = 0x00001740;   /* DDR3 mode, 8-bank interleave */
    REG(MMDC_MDOTC)   = 0x12554000;
    REG(MMDC_MDCFG0)  = 0xBABF7954;   /* tRFC, tXS, tXP, tXPDLL */
    REG(MMDC_MDCFG1)  = 0xDB538F64;   /* tRP, tRAS, tRC, tWR, tCWL */
    REG(MMDC_MDCFG2)  = 0x01FF00DB;   /* tDLLK, tRTP, tWTR, tRRD */
    REG(MMDC_MDRWD)   = 0x000026D2;
    REG(MMDC_MDOR)    = 0x005B0E21;
    REG(MMDC_MDPDC)   = 0x00020024;
    REG(MMDC_MDCTL)   = 0x83180000;   /* row=14, col=10, BL=8, 16-bit, CS0 only */

    ddr_calibrate();

    /* ---- Issue mode register sets via MDSCR ---- */
    REG(MMDC_MDSCR)   = 0x00008032;   /* MR2 = 0x18 -> MDSCR */
    REG(MMDC_MDSCR)   = 0x00008033;   /* MR3 = 0x00 */
    REG(MMDC_MDSCR)   = 0x00048031;   /* MR1 = 0x004 */
    REG(MMDC_MDSCR)   = 0x15208030;   /* MR0 = 0x1520 (CL=11, tWR=12, DLL_reset=1) */

    /* ---- ZQ calibration ---- */
    REG(MMDC_MDSCR)   = 0x04008040;   /* ZQ long */

    /* ---- Hardware ZQ continuous + refresh ---- */
    REG(MMDC_MPZQHWCTRL) = 0xA1390003;
    REG(MMDC_MDREF)      = 0x00007800; /* tREFI counter for 7.8 us */
    REG(MMDC_MAPSR)      = 0x00011006;

    /* ---- Final: take controller out of config mode ---- */
    REG(MMDC_MDSCR)   = 0x00000000;
}

/* Memtest: write pattern, read back, count bit errors. */
int ddr_selftest(void)
{
    volatile uint32_t *p = (uint32_t *)0x80000000;
    const uint32_t size_words = 1024 * 1024;  /* 4 MB scan */
    uint32_t errors = 0;

    for (uint32_t i = 0; i < size_words; i++) p[i] = i ^ 0xA5A5A5A5;
    for (uint32_t i = 0; i < size_words; i++) {
        if (p[i] != (i ^ 0xA5A5A5A5)) errors++;
    }
    return (int)errors;
}
```

The constants are the dangerous part. **Do not trust the numbers above blindly.** They are typical for a particular MT41K128M16 layout but vary across board revisions, trace lengths, and chip vendors. The correct values for *your* board come from:

1. Running the **NXP DDR Stress Tool** on your board.
2. Reading the values from a known-good vendor BSP for your specific MINI revision.
3. Sweeping calibration values experimentally (slow but possible).

## 14.8  Calibration: write leveling, DQS gating, read/write delay

DDR3 chips need three calibrations beyond the standard initialization:

- **Write leveling**: aligns the controller's data clock (DQS) with the chip's clock (CK). The chip enters a special mode where it samples DQS rising edges; the controller increments its DQS delay until the chip reports a transition. Result: per-byte DQS delay value.
- **DQS gating**: tunes when the controller looks for the chip's response DQS during reads. Without this, reads return data, but framed incorrectly.
- **Read/write delay**: per-bit fine-tuning across the data lane.

The MMDC can do this **in hardware** if you set the right bits — write 1 to `MPWLGCR` to start write leveling, poll for completion, read back the resulting delay. Or do it manually by sweeping values and running a memtest at each.

Real-world flow: NXP's DDR Stress Tool runs the hardware calibration *with diagnostics*, reports the optimal values, and emits a "DCD list" — a sequence of register writes you can drop into your code (or your DCD blob).

**For this book**, we copy the values the DDR Stress Tool emits. Treat them as a black box you can re-derive at any time by running the tool. If your DRAM begins to fail occasionally during DRAM workloads, re-run the tool — calibration drifts with temperature.

## 14.9  Calling from `main()` and the OCRAM → DRAM jump

In `main()`:

```c
#include "uart.h"
#include "clocks.h"
#include "ddr.h"
int printf(const char *fmt, ...);

int main(void)
{
    uart_init();
    clocks_init();
    uart_init();   /* re-init after clock change */

    printf("\r\n== DDR3 initialization ==\r\n");
    ddr_init();
    int errs = ddr_selftest();
    printf("DDR memtest (4 MB): %d errors\r\n", errs);
    if (errs) {
        printf("DDR failed; halting.\r\n");
        for (;;) {}
    }
    printf("DDR ok. 512 MiB at 0x80000000.\r\n");

    /* Write a marker; read back; print. */
    *(volatile uint32_t *)0x80000000 = 0xCAFEBABE;
    printf("Wrote 0x%08x at 0x80000000, read back 0x%08x\r\n",
           0xCAFEBABE, *(volatile uint32_t *)0x80000000);

    /* TODO: in §14.10, copy ourselves to DRAM and jump there. */

    for (;;) {}
}
```

Expected output:

```
== DDR3 initialization ==
DDR memtest (4 MB): 0 errors
DDR ok. 512 MiB at 0x80000000.
Wrote 0xcafebabe at 0x80000000, read back 0xcafebabe
```

If the memtest is non-zero: your calibration is wrong (most likely), or your IOMUX pad settings are wrong (less common), or your timing parameters don't match the chip (third most common).

## 14.10  Copying ourselves to DRAM

Now the trick. Right now we are executing from OCRAM at `0x009xxxxx`. DRAM works. We want to copy the *entire* image to DRAM at `0x80100000` (1 MB into DRAM, for headroom) and jump to it.

The mechanics:

```c
/* In main(), after DDR is up: */
extern uint32_t _text_start;
extern uint32_t _text_end;
extern uint32_t _data_start;
extern uint32_t _data_end;

void relocate_to_dram(void)
{
    /* Symbols come from linker script: addresses of our current image. */
    uint32_t img_size = (uint32_t)&_text_end - (uint32_t)&_text_start;
    img_size += (uint32_t)&_data_end - (uint32_t)&_data_start;

    uint32_t *src = (uint32_t *)0x00907400;   /* OCRAM load address */
    uint32_t *dst = (uint32_t *)0x80100000;   /* DRAM target */
    for (uint32_t i = 0; i < (img_size + 3) / 4; i++) dst[i] = src[i];

    /* The DRAM copy is identical to the OCRAM copy.  The 'jump' is just
       calling a function pointer to the DRAM-resident entry. */
    typedef void (*entry_t)(void) __attribute__((noreturn));
    entry_t entry = (entry_t)(0x80100000 + ((uint32_t)main - 0x00907400));
    entry();
}
```

Caveat: the call to `entry()` enters the DRAM-resident copy of `main`, which then re-initializes everything. To avoid infinite recursion, use a flag:

```c
static uint32_t already_in_dram = 0;

int main(void)
{
    if (!already_in_dram) {
        uart_init();
        clocks_init();
        uart_init();
        ddr_init();
        if (ddr_selftest() == 0) {
            already_in_dram = 1;
            relocate_to_dram();   /* never returns */
        }
    }
    /* We're now running from DRAM. */
    printf("\r\nRunning from DRAM at 0x80100000!\r\n");
    printf("My PC is somewhere near %p\r\n", (void*)main);
    for (;;) {}
}
```

The flag-in-`.data` works because we copy `.data` along with `.text`, so the DRAM copy sees `already_in_dram = 1`. The OCRAM copy still has `0` but never runs again — we jumped past it.

When you run this, picocom should show:

```
== DDR3 initialization ==
DDR memtest (4 MB): 0 errors
DDR ok. 512 MiB at 0x80000000.
Wrote 0xcafebabe at 0x80000000, read back 0xcafebabe

Running from DRAM at 0x80100000!
My PC is somewhere near 0x80100xxx
```

That `0x80100xxx` for `main` is the proof. We are executing instructions out of DDR3. Every later chapter in Part II (and all of Part III's U-Boot) lives here.

## 14.11  Sanity tests beyond the basic memtest

A 4 MB memtest is necessary but not sufficient. Common further tests:

### Walking ones / zeros

```c
for (int bit = 0; bit < 32; bit++) {
    uint32_t pat = 1u << bit;
    *(volatile uint32_t *)0x80000000 = pat;
    if (*(volatile uint32_t *)0x80000000 != pat) report_failure(bit);
}
```

Catches stuck-at-bit faults.

### Address-as-data

```c
for (uint32_t a = 0x80000000; a < 0x80100000; a += 4)
    *(volatile uint32_t *)a = a;
for (uint32_t a = 0x80000000; a < 0x80100000; a += 4)
    if (*(volatile uint32_t *)a != a) report_failure_at(a);
```

Catches address-line shorts.

### Long memtest

Sweep the **entire 512 MiB** with random patterns. Takes a few minutes. Run before declaring DRAM good.

The reference open-source tool is `memtester` (a Linux user-space program in Part V, not a bare-metal one). For bare-metal, copy the loops from above and extend.

## 14.12  Why the DCD is the elegant alternative

In Chapter 7 we discussed how the Boot ROM walks a DCD before loading your image. A DCD that initializes DRAM is just our function above expressed as `(address, value)` pairs — no procedural logic, just writes.

In production, you ship a DCD inside your `.imx`. The ROM brings up DRAM. Then it loads U-Boot (which is multi-megabyte) *into* DRAM. U-Boot, in turn, loads the kernel.

For *learning*, doing it in C (as we did) is better — you see the logic. For *deployment*, the DCD is better — it lets you load larger images.

We will update `mkimx.py` in **Chapter 19** to support DCDs so that we can re-use our DDR init values when we want to load a >100 KB image. Until then, our bare-metal images are small enough to fit in OCRAM and bootstrap DRAM themselves.

## 14.13  NXP's DDR Stress Tool

This deserves its own section.

The DDR Stress Tool (`mscale_ddr_tool` in modern NXP releases) is a Windows GUI / CLI program that:

1. Connects to your board over USB-OTG (SDP).
2. Pushes a small bare-metal helper into OCRAM and runs it.
3. The helper runs hardware calibration with extensive diagnostics.
4. Reports the optimal write-leveling, DQS-gating, and read/write delay values.
5. Optionally generates a DCD blob you can drop into your image.

**Use it on every new board.** Even if you use values from a vendor BSP, validate with the tool. Calibration drifts with temperature, board layout, and DRAM lot.

Download from NXP's website (free, registration required). Documentation: AN4467 and AN5223. There is an open-source replacement effort but the NXP tool is what everyone uses.

## 14.14  Lab

This is the central lab of Part II.

1. **Run DDR Stress Tool** on your board. Record the calibration values.
2. **Replace the placeholder constants** in `ddr.c` with your measured values.
3. **Build, push via SDP, run.** Watch picocom for "DDR ok" or for memtest failures.
4. **Run the long memtest.** Sweep all 512 MiB. Confirm zero errors.
5. **Relocate to DRAM.** Implement §14.10. Confirm `main` reports an address in `0x80100000` range.
6. **Vary DRAM clock.** In `clocks_init()`, reduce MMDC clock to 198 MHz (PFD2 / 2 instead of PFD2). Re-run DDR init with adjusted timing values (compute from datasheet ns). Re-test. Compare error rate.
7. **Heat the chip.** Run a long memtest while gently heating the DRAM with a hot-air station or a hairdryer (be careful). Observe whether calibration holds.

Commit to `code/ch14-ddr/`.

## 14.15  Pitfalls

- **Trusting copied calibration values.** They were calibrated on someone else's board. Use them as a starting point; re-validate.
- **IOMUX not configured.** The MMDC pads default to weak drive after reset. Signals look correct on a scope but cross-talk causes occasional bit errors. Configure pads first.
- **Wrong MR0 CAS latency.** Symptom: memtest fails immediately. The chip and the controller must agree on CL. CL=11 on chip = `MR0[6:4,2] = 0b1110_1`; CL=11 in MMDC's MDCFG1.tRL field = different encoding.
- **MMDC clock mismatch.** Timings in MDCFG0/1/2 are converted to cycles using the *current* MMDC clock. If you change MMDC clock after MMDC init, the timings are no longer correct.
- **Forgetting to disable MDSCR config mode.** After MR sets, write 0 to MDSCR to leave config mode. Otherwise reads/writes are interpreted as MMDC commands.
- **Heating the chip in a way that destroys it.** Hairdryers are fine. Heat guns are not. Be careful in the temperature lab.
- **Not power-cycling after a failed bring-up.** A partially-initialized MMDC can produce stuck states. When in doubt, power off, count to 5, power on.

## 14.16  Going deeper

- **JEDEC JESD79-3F** — *DDR3 SDRAM Specification*. The original. Free download with registration.
- Your **DRAM chip datasheet** (Micron MT41K128M16, ISSI IS43TR16128, Nanya NT5CC128M16, etc.). Authoritative for tRCD/tRP/tRAS values and MR bit fields.
- **IMX6ULLRM Chapter 39 — MMDC**. The controller's complete register reference. Long but skimmable.
- **AN4467** — *MX6 DDR Stress Test*. How to use the NXP tool.
- **AN5223** — *MX6 DDR Calibration*. The theory behind the calibration the tool performs.
- **U-Boot source: `board/freescale/mx6ul_14x14_evk/MX6UL_14x14_EVK_4x_MT41K256M16HA-125.cfg`** — a real DCD for a similar Micron DDR. Compare against your tool output.
- **Bootlin training material on DRAM controllers** — accessible, free.

> Next chapter: **Chapter 15 — Exceptions and the GIC.** We have CPU clocks, UART, and DRAM. Now we install proper exception vectors and write our first real interrupt handler.
