---
chapter: 12
title: UART driver and printf
part: II — Bare-metal i.MX6ULL
estimated_pages: 18
status: draft
---

# Chapter 12 — UART driver and `printf`

> **What:** a polled UART1 driver and a tiny `printf` clone that uses it. By the end of the chapter your bare-metal program can say `Hello, world!` instead of blink.
>
> **Why:** debugging bare-metal without `printf` is doable but slow. Adding text output changes everything. Every later chapter in Part II uses `printf` freely.
>
> **Focus:** the **UART baud-divisor formula** and the **status-register polling loop**. Both repeat across most UART implementations. After this chapter you will recognize them anywhere.

## 12.1  Which UART, and on which pins

The i.MX6ULL has eight UART controllers (UART1 through UART8). The board's debug header from Chapter 8 brings out **UART1**. Its TX is `UART1_TX_DATA` and RX is `UART1_RX_DATA`. On the Point Atom MINI these signals come out on the pads literally named UART1_TX_DATA and UART1_RX_DATA, in their reset mux (ALT0). The 4-pin debug header from Chapter 8 brings them out.

For our purposes:

- Module: **UART1**, base address `0x02020000`.
- Pads: `UART1_TX_DATA` (ALT0 = UART1_TX_DATA), `UART1_RX_DATA` (ALT0 = UART1_RX_DATA).
- Pad IOMUXC registers: `IOMUXC_SW_MUX_CTL_PAD_UART1_TX_DATA` at `0x020E0084`, RX at `0x020E0088`. (Verify against your RM.)
- Daisy-chain register: `IOMUXC_UART1_RX_DATA_SELECT_INPUT` at `0x020E0624`, telling UART1 which pad to listen on for RX (usually `0` for the matching `UART1_RX_DATA` pad).

The UART1 controller is on AIPS-1; its clock gate is in **CCM_CCGR5**, bits 24-25 (CG12). UART1's input clock — `uart_clk_root` — has a default of **80 MHz** (PLL3 / 6, with the post-divider set to 1). We'll use that.

## 12.2  Baud rate, the i.MX way

Most UART chips compute baud as `f_in / (16 × divisor)`. i.MX is the same shape but with two divisor stages, so it can hit awkward baud rates:

```
   baud = (f_uart_clk / 16) × (UBIR + 1) / (UBMR + 1)
```

- `UBIR` is a 16-bit numerator register (Baud Rate Numerator).
- `UBMR` is a 16-bit denominator register (Baud Rate Modulator).
- The factor of 16 is the oversampling rate, fixed.
- There's a fractional adjustment (`UFCR.RFDIV` field) that further divides f_uart_clk by 1 / 2 / 4 / etc.; we leave it at "divide by 1" for now.

For our case:

- `f_uart_clk = 80 MHz`
- Target baud = 115200
- We want `(UBIR + 1) / (UBMR + 1) = 115200 × 16 / 80 000 000 = 0.02304`

The simplest values that yield this ratio cleanly are `(UBIR+1) = 71`, `(UBMR+1) = 3083`. (Choice not unique; we pick small numerators when possible.) So:

- `UBIR = 70`
- `UBMR = 3082`

If exact match is impossible, the chip rounds; up to ~3% baud error is tolerated by most receivers. A mismatched baud rate shows up as garbage characters that look like ASCII but are not.

## 12.3  Register map (the ones we actually use)

The UART has dozens of registers; we use six:

| Register | Offset | Purpose |
|----------|--------|---------|
| `URXD` | `+0x000` | Receive data (read) |
| `UTXD` | `+0x040` | Transmit data (write) |
| `UCR1` | `+0x080` | Control 1 (enable) |
| `UCR2` | `+0x084` | Control 2 (TX/RX/8N1) |
| `UCR3` | `+0x088` | Control 3 (various) |
| `UCR4` | `+0x08C` | Control 4 (DMA off, RX threshold) |
| `UFCR` | `+0x090` | FIFO control + clock div |
| `USR1` | `+0x094` | Status 1 (TRDY = TX FIFO has room) |
| `USR2` | `+0x098` | Status 2 (TXDC = TX complete; RDR = RX data ready) |
| `UESC` | `+0x09C` | Escape character (we ignore) |
| `UTIM` | `+0x0A0` | Escape timer (we ignore) |
| `UBIR` | `+0x0A4` | Baud numerator |
| `UBMR` | `+0x0A8` | Baud denominator |
| `UTS`  | `+0x0B4` | UART test register; TX FIFO full bit lives here |

The full list is RM Table 55-3. We will not visit most of them.

Three bits we will touch by name:

- **`UCR1.UARTEN`** (bit 0) — overall UART enable.
- **`UCR2.SRST`** (bit 0) — software reset, **active-low**. Clear the bit to *assert* reset; set it to release. (Yes, the polarity is unusual. That is what the RM says.)
- **`UCR2.TXEN | UCR2.RXEN`** (bits 1 and 2) — TX and RX enables.
- **`USR1.TRDY`** (bit 13) — TX FIFO has space for at least one byte.
- **`USR2.RDR`** (bit 0) — receive data ready.

## 12.4  The driver, top to bottom

`uart.h`:

```c
#ifndef UART_H
#define UART_H

#include <stdint.h>

void uart_init(void);
void uart_putc(char c);
void uart_puts(const char *s);
int  uart_getc(void);     /* -1 if no data */

#endif
```

`uart.c`:

```c
#include "uart.h"

#define REG(addr) (*(volatile uint32_t *)(addr))

#define UART1_BASE   0x02020000
#define UART_URXD    (UART1_BASE + 0x000)
#define UART_UTXD    (UART1_BASE + 0x040)
#define UART_UCR1    (UART1_BASE + 0x080)
#define UART_UCR2    (UART1_BASE + 0x084)
#define UART_UCR3    (UART1_BASE + 0x088)
#define UART_UCR4    (UART1_BASE + 0x08C)
#define UART_UFCR    (UART1_BASE + 0x090)
#define UART_USR1    (UART1_BASE + 0x094)
#define UART_USR2    (UART1_BASE + 0x098)
#define UART_UBIR    (UART1_BASE + 0x0A4)
#define UART_UBMR    (UART1_BASE + 0x0A8)
#define UART_UTS     (UART1_BASE + 0x0B4)

#define CCM_CCGR5    0x020C407C
#define IOMUX_MUX_TX 0x020E0084
#define IOMUX_MUX_RX 0x020E0088
#define IOMUX_PAD_TX 0x020E0310
#define IOMUX_PAD_RX 0x020E0314
#define IOMUX_DAISY  0x020E0624

#define USR1_TRDY    (1u << 13)
#define USR2_RDR     (1u << 0)

void uart_init(void)
{
    /* 1.  Gate the clock to UART1.  CG12 (bits 24-25) of CCGR5 = 0b11. */
    REG(CCM_CCGR5) |= (3u << 24);

    /* 2.  Pinmux: ALT0 on both TX and RX pads. */
    REG(IOMUX_MUX_TX) = 0;
    REG(IOMUX_MUX_RX) = 0;
    REG(IOMUX_PAD_TX) = 0x000010B0;   /* Push-pull, 50 MHz, no pull */
    REG(IOMUX_PAD_RX) = 0x000130B1;   /* With keeper for stable idle level */
    REG(IOMUX_DAISY)  = 3;            /* select UART1_RX_DATA pad (verify w/ RM) */

    /* 3.  Soft-reset the UART (SRST is active-low: clear to assert). */
    REG(UART_UCR2) = 0;
    while (!(REG(UART_UCR2) & 1)) { /* wait for SRST high (release) */ }

    /* 4.  Disable while configuring. */
    REG(UART_UCR1) = 0;

    /* 5.  No hardware flow control; 8N1; RX+TX enable; release SRST. */
    REG(UART_UCR2) = (1u << 14)   /* IRTS (ignore RTS) */
                   | (1u << 5)    /* WS = 8 data bits */
                   | (1u << 2)    /* TXEN */
                   | (1u << 1)    /* RXEN */
                   | (1u << 0);   /* SRST released */

    /* 6.  UCR3.RXDMUXSEL must be 1 for receive to work on the externally-muxed
          path -- yes, this trips people up; it's in the errata. */
    REG(UART_UCR3) |= (1u << 2);

    /* 7.  No DMA, no escape detection. */
    REG(UART_UCR4) = (1u << 0);    /* DREN: receive-ready interrupt enable bit; we don't use IRQ yet but writing 0 elsewhere is fine */

    /* 8.  FIFO control: RX trigger = 1, TX trigger = 2, RFDIV = /1.
          UFCR fields:
            RXTL  bits  5:0     RX FIFO trigger level
            RFDIV bits  9:7     reference freq divider (0b101 = /1 on i.MX6ULL)
            TXTL  bits 15:10    TX FIFO trigger level
    */
    REG(UART_UFCR) = (2u << 10)         /* TXTL = 2 */
                   | (5u << 7)          /* RFDIV = /1 */
                   | (1u << 0);         /* RXTL = 1 */

    /* 9.  Baud: 115200 from f_uart = 80 MHz.
          UBIR = 70, UBMR = 3082.  (UBIR must be written before UBMR!) */
    REG(UART_UBIR) = 70;
    REG(UART_UBMR) = 3082;

    /* 10. Enable UART. */
    REG(UART_UCR1) = (1u << 0);    /* UARTEN */
}

void uart_putc(char c)
{
    while (!(REG(UART_USR1) & USR1_TRDY)) { /* spin until TX has room */ }
    REG(UART_UTXD) = (uint8_t)c;
}

void uart_puts(const char *s)
{
    while (*s) {
        if (*s == '\n') uart_putc('\r');
        uart_putc(*s++);
    }
}

int uart_getc(void)
{
    if (!(REG(UART_USR2) & USR2_RDR)) return -1;
    return (int)(REG(UART_URXD) & 0xFF);
}
```

Read `uart_init()` carefully. Each line is in the RM, and each line costs someone an afternoon when it is skipped. A few specific points:

- **UBIR must be written before UBMR.** The order matters; the controller's internal divider is latched on the UBMR write. Reverse and you'll get baud rates 6.8% off, which still looks like text but has occasional corruption.
- **The `\n` → `\r\n` translation in `uart_puts`** is here because dumb terminals (and `picocom` by default) expect CRLF endings to advance to a new line *and* return to column 0. We do not get this for free.
- **`UCR3.RXDMUXSEL = 1`** is the errata fix that I lost an afternoon to once. Without it, RX appears dead.

## 12.5  A 200-line `printf`

You should use a third-party printf (`mpaland/printf` is excellent) in real projects. For the book we write our own, ~120 lines.

`mini_printf.c`:

```c
#include <stdarg.h>
#include <stdint.h>
#include "uart.h"

static void emit_char(char c)            { uart_putc(c); }
static void emit_str(const char *s)      { while (*s) emit_char(*s++); }

static void emit_uint(unsigned long v, unsigned base, int width, char pad)
{
    char buf[32];
    const char *digits = "0123456789abcdef";
    int i = 0;
    if (v == 0) buf[i++] = '0';
    while (v) { buf[i++] = digits[v % base]; v /= base; }
    while (i < width) buf[i++] = pad;
    while (i--) emit_char(buf[i]);
}

static void emit_int(long v, int width, char pad)
{
    if (v < 0) { emit_char('-'); v = -v; if (width) width--; }
    emit_uint((unsigned long)v, 10, width, pad);
}

int mini_vprintf(const char *fmt, va_list ap)
{
    while (*fmt) {
        if (*fmt != '%') { emit_char(*fmt++); continue; }
        fmt++;                                 /* skip '%' */
        char pad = ' ';
        int  width = 0;
        if (*fmt == '0') { pad = '0'; fmt++; }
        while (*fmt >= '0' && *fmt <= '9') { width = width*10 + (*fmt - '0'); fmt++; }

        switch (*fmt) {
        case 'c':  emit_char((char)va_arg(ap, int));         break;
        case 's':  emit_str(va_arg(ap, const char *));       break;
        case 'd':  emit_int (va_arg(ap, int),  width, pad);  break;
        case 'u':  emit_uint(va_arg(ap, unsigned), 10, width, pad); break;
        case 'x':  emit_uint(va_arg(ap, unsigned), 16, width, pad); break;
        case 'p':  emit_str("0x"); emit_uint((uintptr_t)va_arg(ap, void*), 16, 8, '0'); break;
        case '%':  emit_char('%');                           break;
        default:   emit_char('%'); emit_char(*fmt);          break;
        }
        if (*fmt) fmt++;
    }
    return 0;
}

int printf(const char *fmt, ...)
{
    va_list ap;
    va_start(ap, fmt);
    int r = mini_vprintf(fmt, ap);
    va_end(ap);
    return r;
}
```

Features we support: `%c %s %d %u %x %p %%`. Width and `0`-padding. Negative `%d`.

Features we do **not** support: `%f` (we have no floats in the kernel of this book), `%lld`, `%ll`, locales, precision (`%.5s`), left-justification (`%-5d`), `%n`. Cover them when you need them.

A note on `va_arg(ap, unsigned)`: AAPCS promotes `unsigned short` and `unsigned char` to `unsigned int` when passing to a variadic function. So `unsigned` is the correct type. For `unsigned long` on 32-bit Linux/ARM it would be the same size; we keep it simple.

## 12.6  `main()` that actually says hello

```c
#include "uart.h"
int printf(const char *fmt, ...);

int main(void)
{
    uart_init();

    printf("\r\nHello, i.MX6ULL bare-metal world!\r\n");
    printf("CPU running at boot-default clock.\r\n");
    printf("This text travels at 115200 baud.\r\n");
    printf("printf supports %%d=%d %%u=%u %%x=0x%08x %%s=\"%s\" %%c=%c\r\n",
           -42, 0xCAFE, 0xDEADBEEF, "rainbow", 'Z');

    /* Echo loop so you can confirm RX works. */
    printf("\r\nType characters. They will echo back.\r\n> ");
    for (;;) {
        int c = uart_getc();
        if (c >= 0) uart_putc((char)c);
    }
}
```

Build:

```sh
$ make
$ ~/imx6ull/scripts/mkimx.py led.bin led.imx --load 0x00907400 --entry 0x00908400
$ uuu -b sdp led.imx
```

In the picocom window:

```
Hello, i.MX6ULL bare-metal world!
CPU running at boot-default clock.
This text travels at 115200 baud.
printf supports %d=-42 %u=51966 %x=0xdeadbeef %s="rainbow" %c=Z

Type characters. They will echo back.
> hello
```

The echo confirms RX works. We have a console.

## 12.7  Why polled UART, not interrupt-driven

We are deliberately using polling. Reasons:

- **No interrupt controller yet.** The GIC will be set up properly in Chapter 15.
- **Polling is enough for `printf`.** Even at 115200 baud, transmitting one character takes 87 µs. Worst case we spin 87 µs per character. For diagnostic output that's fine; in a high-throughput application it wouldn't be.
- **Simplicity reveals more.** Polling shows you the status-bit pattern in full. After you do it once, the interrupt version is just "the same thing, but the FIFO threshold triggers an ISR."

We will write an interrupt-driven echo as a lab in Chapter 15.

## 12.8  Lab

1. **Build, push via SDP, observe `Hello, world`.** Confirm baud rate by typing fast and slow; characters should echo back at any speed.
2. **Measure the baud error.** Insert a `for` loop that emits `'U'` (0x55, the canonical alternating-bit-pattern character) 1 million times. Capture on a scope; measure one bit period; compute actual baud; compare to 115200. Should be within 1%.
3. **Add `%b`** to `mini_printf` — binary representation, for register dumps. Use it to dump `UCR1`, `UCR2`, `USR1`, `USR2` at startup.
4. **Print system info.** Read OCOTP_CFG0 and OCOTP_CFG1 (RM Chapter 37) and print the chip's unique ID.
5. **Stress test.** Connect picocom and a script on the host that types 10 KB of text. Confirm none is lost. (We don't have flow control; at 115200 with a polled receiver, 10 KB should still be safe.)

## 12.9  Pitfalls

- **Wrong RFDIV in UFCR.** Setting `RFDIV = 0` divides by 6, not 1. Symptom: baud rate is six times too slow. The encoding is: 000=/6, 001=/5, 010=/4, 011=/3, 100=/2, 101=/1. Always `0b101`.
- **Forgot to release SRST.** Symptom: UART silent. `UCR2.SRST = 0` means *asserted*. Set it to release.
- **Wrong daisy-chain (SELECT_INPUT).** Symptom: TX works (you see `Hello`), RX doesn't (no echo). The UART_RX_DATA_SELECT_INPUT register decides which pad routes to UART1's receiver. Wrong value = data goes nowhere.
- **CRLF vs LF.** `picocom` defaults to translating LF to CRLF on receive. Newer terminals don't. If your output is "stairstepped," your `\n` is not being followed by `\r`. Our `uart_puts` handles it.
- **`printf` with `float`s.** Compiles, runs, prints garbage (we never wrote `%f`). Don't pass floats to a printf you haven't taught.
- **UBIR after UBMR.** Discussed in §12.4. Don't.
- **Forgot the CCGR.** Always. Every. Time.

## 12.10  Going deeper

- **IMX6ULLRM Chapter 55** — UART. Read once cover-to-cover; you'll come back.
- **AN3956** — *Configuring the i.MX UART Module*. Concise; useful.
- **`mpaland/printf`** at `<https://github.com/mpaland/printf>` — a production-quality tiny printf, MIT-licensed.
- **The 16550 UART datasheet** — every embedded engineer should read this once. It's the platonic UART.
- **Linux source: `drivers/tty/serial/imx.c`** — the same hardware, the same registers, vastly more sophisticated driver. Read it after Chapter 12 here; you'll recognize every bit.

> Next chapter: **Chapter 13 — CCM clock tree bring-up.** So far we've been running on whatever clock the ROM left us. Time to take ownership.
