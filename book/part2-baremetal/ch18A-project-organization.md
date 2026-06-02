---
chapter: 18A
title: Project organization — STM32-style headers, BSP layout, the SDK alternative
part: II — Bare-metal i.MX6ULL (inserted v1.1)
estimated_pages: 14
status: draft
---

# Chapter 18A — Project organization

> **What:** refactor the monolithic single-file layout we used through Chapter 17 into a real project tree — `bsp/` folder with one subdirectory per peripheral, a single `imx6ull.h` containing all register definitions, and a top-level Makefile that builds and links everything cleanly.
>
> **Why:** once a bare-metal project crosses ~500 lines and ~3 peripherals, the single-file layout costs more than it saves. Every new peripheral becomes a merge conflict with the one before it. Every register `#define` competes for namespace with every other. We refactor now, before Part III's U-Boot work pushes us into larger codebases.
>
> **Focus:** **the BSP folder pattern** (one driver = one folder = one `.h` + one `.c`) and `imx6ull.h` holds every register definition in one place. The NXP SDK's `MCIMX6Y2.h` does the same thing with auto-generated struct headers. We hand-write ours so the auto-generated version reads as a productivity tool, not a black box.

## 18A.1  The problem we are solving

Open the Chapter 16 code in your editor. You have:

- `main.c` — `main()` plus inline UART init, GPIO init, CCM writes
- `startup.S`, `link.ld` — unchanged
- A growing forest of `#define UART_UCR1 0x02020080` and friends, scattered across files
- Function names like `uart_init`, `gpio_init`, `epit_init` — fine when there are 3 of them, brittle when there are 30

Two specific kinds of pain start to appear:

1. **Header pollution.** `uart.c` defines `UART_UCR1`. `main.c` happens to define it again with a slightly different value (typo). Both compile. The behavior of the program depends on which `#define` `cpp` saw last.
2. **Reuse friction.** To use the Chapter 18 I²C driver in a new project, you copy `i2c.c`, plus the relevant `#define`s from `main.c`, plus the CCM gate bit, plus the IOMUX writes. Five files involved per peripheral.

The fix is structural: separate **what the hardware looks like** (one file: `imx6ull.h`) from **what each driver does** (one folder per peripheral). The NXP SDK does the same thing with auto-generated headers — we are reaching for the same structure by hand.

## 18A.2  Target layout

```
bare-metal/
├── Makefile                     # top-level build
├── link.ld                      # unchanged
├── startup.S                    # unchanged
├── imx6ull.h                    # ALL register #defines, in one place
├── main.c                       # only application logic
└── bsp/
    ├── clk/
    │   ├── bsp_clk.h
    │   └── bsp_clk.c            # was clocks.c
    ├── gpio/
    │   ├── bsp_gpio.h
    │   └── bsp_gpio.c
    ├── uart/
    │   ├── bsp_uart.h
    │   └── bsp_uart.c
    ├── int/                     # interrupts / GIC
    │   ├── bsp_int.h
    │   ├── bsp_int.c
    │   └── irq_entry.S          # the IRQ entry asm from Ch 15
    ├── gpt/
    │   ├── bsp_gpt.h
    │   └── bsp_gpt.c
    ├── epit/
    │   ├── bsp_epit.h
    │   └── bsp_epit.c
    └── delay/
        ├── bsp_delay.h
        └── bsp_delay.c
```

Conventions:

- **`bsp_<peripheral>.h`** has only public-facing declarations: the API functions, and the *enum types* the API uses. No raw register addresses.
- **`bsp_<peripheral>.c`** has the function bodies. Includes `imx6ull.h` for register addresses.
- **`imx6ull.h`** is the *only* place that names registers. Every other file uses those names.

That last rule is the one that matters.

## 18A.3  Writing `imx6ull.h`

The file is long but mechanical. Section it by peripheral block:

```c
#ifndef __IMX6ULL_H__
#define __IMX6ULL_H__

#include <stdint.h>
#define REG(addr) (*(volatile uint32_t *)(addr))

/* ============================================================
 * CCM — Clock Controller Module (RM ch. 18)
 * Base: 0x020C4000
 * ============================================================ */
#define CCM_BASE        0x020C4000U
#define CCM_CCR         (CCM_BASE + 0x00)
#define CCM_CACRR       (CCM_BASE + 0x10)
#define CCM_CBCDR       (CCM_BASE + 0x14)
#define CCM_CBCMR       (CCM_BASE + 0x18)
#define CCM_CSCMR1      (CCM_BASE + 0x1C)
#define CCM_CSCDR1      (CCM_BASE + 0x24)
#define CCM_CCGR0       (CCM_BASE + 0x68)
#define CCM_CCGR1       (CCM_BASE + 0x6C)
#define CCM_CCGR2       (CCM_BASE + 0x70)
#define CCM_CCGR3       (CCM_BASE + 0x74)
#define CCM_CCGR4       (CCM_BASE + 0x78)
#define CCM_CCGR5       (CCM_BASE + 0x7C)
#define CCM_CCGR6       (CCM_BASE + 0x80)
#define CCM_CDHIPR      (CCM_BASE + 0x48)

/* CCGR per-peripheral gates -- 2 bits each, 16 gates per CCGRx register */
#define CCGR_GPIO1_GATE   (3u << 26)   /* CCGR1[27:26] */
#define CCGR_GPIO5_GATE   (3u << 30)   /* CCGR1[31:30] */
#define CCGR_GPT1_GATE    (3u << 20)   /* CCGR1[21:20] */
#define CCGR_EPIT1_GATE   (3u << 12)   /* CCGR1[13:12] */
#define CCGR_UART1_GATE   (3u << 24)   /* CCGR5[25:24] */
#define CCGR_I2C1_GATE    (3u << 6)    /* CCGR2[7:6]   */

/* ============================================================
 * ANATOP — PLLs and PFDs (RM ch. 19)
 * Base: 0x020C8000
 * ============================================================ */
#define ANATOP_BASE     0x020C8000U
#define ANATOP_PLL_ARM  (ANATOP_BASE + 0x000)
#define ANATOP_PLL_SYS  (ANATOP_BASE + 0x030)
#define ANATOP_PFD_528  (ANATOP_BASE + 0x100)
#define ANATOP_PFD_480  (ANATOP_BASE + 0x0F0)

/* ============================================================
 * GPIO1..GPIO5 (RM ch. 28)
 * ============================================================ */
#define GPIO1_BASE      0x0209C000U
#define GPIO2_BASE      0x020A0000U
#define GPIO3_BASE      0x020A4000U
#define GPIO4_BASE      0x020A8000U
#define GPIO5_BASE      0x020AC000U

/* Per-bank register offsets */
#define GPIO_DR_OFS     0x000
#define GPIO_GDIR_OFS   0x004
#define GPIO_PSR_OFS    0x008
#define GPIO_ICR1_OFS   0x00C
#define GPIO_ICR2_OFS   0x010
#define GPIO_IMR_OFS    0x014
#define GPIO_ISR_OFS    0x018
#define GPIO_EDGE_OFS   0x01C

/* Helper for indexed access */
#define GPIO_DR(bank)   REG((bank) + GPIO_DR_OFS)
#define GPIO_GDIR(bank) REG((bank) + GPIO_GDIR_OFS)

/* ============================================================
 * UART1..UART8 (RM ch. 55)
 * ============================================================ */
#define UART1_BASE      0x02020000U
#define UART2_BASE      0x021E8000U
/* ... etc ... */
#define UART_URXD_OFS   0x000
#define UART_UTXD_OFS   0x040
#define UART_UCR1_OFS   0x080
#define UART_UCR2_OFS   0x084
#define UART_UCR3_OFS   0x088
#define UART_UCR4_OFS   0x08C
#define UART_UFCR_OFS   0x090
#define UART_USR1_OFS   0x094
#define UART_USR2_OFS   0x098
#define UART_UBIR_OFS   0x0A4
#define UART_UBMR_OFS   0x0A8
#define UART_UTS_OFS    0x0B4

/* ============================================================
 * GPT1, EPIT1 (RM ch. 29, 30)
 * ============================================================ */
#define GPT1_BASE       0x02098000U
#define EPIT1_BASE      0x020D0000U
#define EPIT2_BASE      0x020D4000U

/* ============================================================
 * IOMUXC (RM ch. 32)
 * ============================================================ */
#define IOMUXC_BASE     0x020E0000U
/* Pad mux + pad ctl offsets vary per pad; use the pad-specific addresses
 * directly, looked up from the RM IOMUX tables. */

/* ============================================================
 * GIC v2 (Cortex-A7 internal at 0x00A01000 / 0x00A02000)
 * ============================================================ */
#define GICD_BASE       0x00A01000U
#define GICC_BASE       0x00A02000U

#endif /* __IMX6ULL_H__ */
```

The full file is ~300 lines for our part-coverage so far. It is boring. It is also the file you reach for most often on every i.MX6ULL project.

## 18A.4  A peripheral driver, refactored

The Chapter 13 `clocks.c` becomes `bsp/clk/bsp_clk.c`:

```c
#include "bsp_clk.h"
#include "imx6ull.h"

void clk_enable_all(void)
{
    /* Brutal: turn every CCGR to "always on".
     * Production code would be selective. */
    REG(CCM_CCGR0) = 0xFFFFFFFFu;
    REG(CCM_CCGR1) = 0xFFFFFFFFu;
    REG(CCM_CCGR2) = 0xFFFFFFFFu;
    REG(CCM_CCGR3) = 0xFFFFFFFFu;
    REG(CCM_CCGR4) = 0xFFFFFFFFu;
    REG(CCM_CCGR5) = 0xFFFFFFFFu;
    REG(CCM_CCGR6) = 0xFFFFFFFFu;
}

void clk_init_main(void)
{
    /* From Ch 13 -- unchanged logic, names from imx6ull.h */
    REG(ANATOP_PLL_ARM) |= (1u << 16);   /* bypass while reprogramming */
    /* ... rest of clk init ... */
}
```

The corresponding header:

```c
#ifndef __BSP_CLK_H__
#define __BSP_CLK_H__

void clk_enable_all(void);
void clk_init_main(void);

#endif
```

Two files. Both small. The implementation does not leak register addresses into anyone else's namespace.

## 18A.5  The top-level Makefile

```make
CROSS    := arm-none-eabi-
CC       := $(CROSS)gcc
LD       := $(CROSS)ld
OC       := $(CROSS)objcopy
SIZE     := $(CROSS)size

CFLAGS   := -mcpu=cortex-a7 -mfpu=neon-vfpv4 -mfloat-abi=hard \
            -ffreestanding -fno-builtin -nostdlib \
            -fno-common -O2 -g -Wall -Wextra

# All BSP source files
BSP_DIRS := bsp/clk bsp/gpio bsp/uart bsp/int bsp/gpt bsp/epit bsp/delay
INCS     := -I. $(addprefix -I,$(BSP_DIRS))

BSP_C    := $(wildcard bsp/*/*.c)
BSP_S    := $(wildcard bsp/*/*.S)
TOP_C    := $(wildcard *.c)
TOP_S    := startup.S

OBJS     := $(BSP_C:.c=.o) $(BSP_S:.S=.o) $(TOP_C:.c=.o) $(TOP_S:.S=.o)

all: app.bin

%.o: %.c
	$(CC) $(CFLAGS) $(INCS) -c -o $@ $<

%.o: %.S
	$(CC) $(CFLAGS) $(INCS) -c -o $@ $<

app.elf: $(OBJS) link.ld
	$(CC) $(CFLAGS) -T link.ld -nostdlib -o $@ $(OBJS)
	$(SIZE) $@

app.bin: app.elf
	$(OC) -O binary $< $@

clean:
	find . -name '*.o' -delete
	rm -f app.elf app.bin

.PHONY: all clean
```

Two things to notice:

- **`$(wildcard bsp/*/*.c)`** picks up every BSP source file automatically. Adding a new peripheral means making a new folder and dropping `bsp_foo.c` + `bsp_foo.h` into it. No Makefile edit.
- **`$(addprefix -I,$(BSP_DIRS))`** makes every BSP header reachable from every other BSP. (If you want strict layering — only `main.c` includes `bsp_*.h`, BSPs include `imx6ull.h` only — drop the addprefix and add only `-I.`.)

## 18A.6  Cost of the refactor

For the LED-blink-with-IRQ-echo program we've been building, the refactor:

- **Files:** 3 → 18. The eye registers this as "more complexity."
- **Total LoC:** ~600 → ~620. (Header skeletons add ~20 lines.)
- **Build time:** unchanged (it's still seconds).
- **Time to add the next peripheral:** ~30 min in the monolithic layout (find the right place in main.c, avoid name collisions); ~10 min in the BSP layout (copy a template folder, edit two files).
- **Re-reading the code 6 months later:** much easier.

The 30-vs-10-minute gap is the point. The refactor pays back over the rest of Part II and the lab work that follows.

## 18A.7  Sidebar — the NXP SDK alternative

The NXP MCUXpresso SDK ships `MCIMX6Y2.h` (downloadable from `mcuxpresso.nxp.com` after free registration). The same content as our `imx6ull.h`, but expressed differently — as **struct definitions** rather than `#define`s:

```c
typedef struct {
    __IO uint32_t CCR;        /* 0x000 */
    uint32_t      RESERVED_0;
    __IO uint32_t CSR;        /* 0x008 */
    __IO uint32_t CCSR;       /* 0x00C */
    __IO uint32_t CACRR;      /* 0x010 */
    __IO uint32_t CBCDR;      /* 0x014 */
    __IO uint32_t CBCMR;      /* 0x018 */
    __IO uint32_t CSCMR1;     /* 0x01C */
    /* ... ~50 more fields, all auto-generated from NXP IP-XACT ... */
} CCM_Type;

#define CCM_BASE          (0x020C4000u)
#define CCM               ((CCM_Type *)CCM_BASE)
```

Usage in driver code becomes:

```c
CCM->CCGR1 |= (3u << 26);   /* enable GPIO1 clock */
```

Compared to our:

```c
REG(CCM_CCGR1) |= (3u << 26);
```

Both compile to the same machine code. The struct version:

- Has typed access (the struct knows offsets), so a typo like `CCM->CGGR1` is a compile error rather than runtime garbage.
- Plays nicely with debuggers: GDB displays `CCM` as a struct with named fields.
- Hides the address. You can `printf("base = %p\r\n", CCM)` to recover it, but it's not in your face.

Most production projects on NXP parts adopt the struct style by the time they have three peripherals. We do not — at least not in this book. The same reason applies as in Chapter 9: once you can hand-roll it, the SDK becomes a productivity tool instead of a black box.

If you ship products with NXP parts, use the SDK headers in production. They are correct, kept in sync with silicon revisions, and save typos. Use the macro style in this book to *learn*; switch styles when you are ready to ship.

## 18A.8  Lab

1. **Refactor.** Take your most-complete Chapter 17 build (MMU + caches + everything before). Refactor it into the layout in §18A.2. The diffs should compile bit-identical to your original — verify with `cmp app.bin original_app.bin`.
2. **Add one new peripheral the new way.** Pick I²C (we did it monolithically in Chapter 18; redo it as `bsp/i2c/`). Time how long it takes vs the original — keep notes.
3. **Stress-test header layering.** Try moving `imx6ull.h` into `bsp/include/`. What needs to change in the Makefile? In each `bsp_*.c`?
4. **Try the SDK style.** Take just `bsp_clk.c` and rewrite it using `MCIMX6Y2.h` (download from NXP). Same output? Compare disassembly with `arm-none-eabi-objdump -d app.elf` between the two builds and confirm identical machine code.

## 18A.9  Pitfalls

- **Naming the BSP folder `lib/` or `drv/`.** Both names collide with conventions used by other projects' build systems. `bsp/` is unambiguous.
- **Letting `imx6ull.h` `#include "bsp_xxx.h"`.** Circular dependency in waiting. `imx6ull.h` declares nothing about your code; it only describes the hardware.
- **Header-only "drivers" via `static inline`.** Tempting; bloats every `.o` that includes the header; defeats the point. Keep declarations in `.h`, definitions in `.c`.
- **Forgetting `-I` for every BSP folder.** Symptom: `bsp_clk.h: No such file or directory`. The `$(addprefix -I,$(BSP_DIRS))` line saves you.
- **Mixing the macro style and the SDK struct style in the same project.** Pick one. The conversion is a global search-and-replace; doing it partway makes the codebase confusing.

## 18A.10  Going deeper

- **Linux kernel** `arch/arm/include/asm/io.h` and `arch/arm/include/asm/hardware/` — the kernel uses the same "one header per controller" pattern at scale.
- **U-Boot** `arch/arm/include/asm/arch-mx6/imx-regs.h` — register addresses for i.MX6 family in U-Boot.
- **NXP MCUXpresso SDK** — download the i.MX6ULL SDK; read `MCIMX6Y2.h` for the canonical struct-based register definition.
- **Cortex-A Series Programmer's Guide §10.2** — recommended startup-and-BSP project layout for ARM Cortex-A bare-metal.

> Next chapter: **Chapter 18B — Button input and beep.** First input peripheral, plus our first PWM-adjacent output.
