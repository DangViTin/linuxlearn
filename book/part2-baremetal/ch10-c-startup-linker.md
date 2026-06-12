---
chapter: 10
title: C + startup.S + linker script
part: II - Bare-metal i.MX6ULL
estimated_pages: 20
status: draft
---

# Chapter 10: C + startup.S + linker script
> **IRQ:** interrupt request, the signal path that tells the CPU or interrupt controller that hardware needs service.
> **MCU bridge:** Think of an IRQ like an EXTI/NVIC interrupt path, except Linux splits the hard interrupt from deferred work and must share lines across drivers.

> **What:** the same blinking LED as Chapter 9, but with `main()` written in C. To get there we need a proper startup that sets the stack, zeroes `.bss`, copies `.data` from its load address to its run address, then branches to `main`. We also write our first real linker script.
>
> **Why:** every later chapter in Part II is in C. C demands an environment, initialized globals, zeroed uninitialized globals, a stack, a stable entry point. The toolchain does *not* provide these on bare-metal. You do. This chapter is the one place where we set these up once so the next eight chapters can ignore them.
>
> **Focus:** the **LMA vs VMA** distinction for `.data` (introduced in Chapter 6, made concrete here). If you can answer where the initial value of a global lives and how it reaches RAM, you understand startup.


## 10.1  What `int x = 7;` actually needs

Consider a C file with three globals:

```c
int   x = 7;           // initialized → .data
int   y;               // uninitialized → .bss
const int z = 42;      // const + initialized → .rodata
```

On a hosted system (your Linux laptop), the loader reads the ELF, mmaps `.data` and `.rodata` from disk, allocates and zero-fills `.bss`, and your program starts. On bare-metal, *there is no loader*. We are loaded as a flat blob into OCRAM (or DRAM, later). Whoever loaded us is done. The rest is on us.
> **ELF:** Executable and Linkable Format, the standard Linux object and executable file format.

So we, ourselves, must:

- **Set a stack pointer.** Without it, the first C function call crashes.
- **Zero `.bss`.** Otherwise `y` is whatever was in OCRAM when we arrived.
- **Copy `.data` from its load location to its run location** (when those differ). This is the LMA-vs-VMA dance from Chapter 6.
- **Branch to `main`.**

Optionally, also: set up exception vectors, configure caches, enable the FPU. We do these later as we need them.

## 10.2  A linker script worth keeping

> **Template warning:** This block contains placeholder values.
> Replace compatible strings, GPIO numbers, addresses, and paths with values from your board before using it.
> **MCU bridge:** Think of Linux GPIO like the same pin set/reset block you used on STM32, but accessed through a kernel subsystem that owns numbering, direction, interrupts, and user-space exposure.
> **GPIO:** General-Purpose Input/Output, a pin controlled as a digital input, output, or interrupt source.


The Chapter 9 program had no `.data` and no `.bss`. We slapped `-Ttext=0x00907400` on the command line and let it ride. For C code, we need a real script. Save it as `link.ld`:

```text
ENTRY(_start)

MEMORY
{
    OCRAM (rwx) : ORIGIN = 0x00907400, LENGTH = 0x00018C00  /* ~99 KB */
}

SECTIONS
{
    . = ORIGIN(OCRAM);

    .text : ALIGN(4) {
        KEEP(*(.vectors))      /* room for vector table later (Ch 15) */
        *(.text*)
        *(.rodata*)
    } > OCRAM

    /* Mark the end of .text -- LMA of .data begins here. */
    _etext = .;

    /*
     * .data : runtime in OCRAM, image-time directly after .text.
     * Because OCRAM and our image both live in the same region, LMA == VMA
     * for this layout, and the copy loop in startup.S is technically a no-op.
     * We still write the copy loop, because:
     *   (a) we want startup.S to work unchanged when we move .data to DRAM in Ch 14,
     *   (b) habit is cheap, and bugs from "we will never need this" are expensive.
     */
    .data : ALIGN(4) AT(_etext) {
        _sdata = .;
        *(.data*)
        _edata = .;
    } > OCRAM

    .bss (NOLOAD) : ALIGN(4) {
        _sbss = .;
        *(.bss*)
        *(COMMON)
        _ebss = .;
    } > OCRAM

    _stack_top = ORIGIN(OCRAM) + LENGTH(OCRAM);

    /DISCARD/ : { *(.note*) *(.comment) *(.ARM.attributes) }
}
```

Decoded line by line:

- **`ENTRY(_start)`**: names the symbol that `objdump` and `gdb` will treat as the executable entry. The Boot ROM does not consult this. It uses the IVT's `entry` field. But debuggers do, and getting it right keeps `gdb` from being puzzled.
- **`MEMORY { OCRAM ... }`**: describes our one available region. ORIGIN is the load address. LENGTH is conservative: 128 KB total OCRAM, minus the first 28 KB the ROM uses for its working area = ~99 KB free starting at `0x00907400`.
- **`. = ORIGIN(OCRAM);`**: the location counter starts at the region's base.
- **`.text` section**: gathers all `.text*`, `.rodata*`, plus a `KEEP(*(.vectors))` placeholder for a future vector table. `KEEP` tells the linker not to garbage-collect this even if no symbol references it. `ALIGN(4)` keeps us word-aligned.
- **`_etext = .;`**: captures the location counter. This is where `.text` ends. It is also where the `.data` *load image* will be placed (see next line).
- **`.data` section with `AT(_etext)`**: the magic line. `AT(addr)` specifies a different LMA for the section. The VMA still flows from the location counter (immediately after `.text` in this case), but the load-address-stored content starts at `_etext`. Because in our layout both are equal, this is currently a no-op, but the *machinery* is in place for when we move `.data` to DRAM later.
- **`_sdata` / `_edata`**: boundary symbols our startup uses to know how much to copy.
- **`.bss (NOLOAD)`**: `NOLOAD` means: the linker does not write any bytes into the image for this section. The boundary symbols `_sbss` / `_ebss` are still exported so startup can zero the region.
- **`_stack_top`**: computed at link time as the high water mark. The startup loads SP from this.
- **`/DISCARD/`**: throws away ELF notes and attributes that have no place in a bare-metal binary.

Three things in this script are easy to get wrong. Each one bites only once.

1. **Forgetting `KEEP` around the vector table.** When you later link with `-gc-sections`, the linker removes the table because nothing in C references it. `KEEP` prevents this.
2. **Forgetting `AT(_etext)` for `.data`.** Then VMA = LMA always, and you don't notice anything is missing, until you move `.data` to DRAM and your initial values turn out to be whatever was in DRAM at boot.
3. **Forgetting `NOLOAD` for `.bss`.** Without it, the linker may emit zero bytes for `.bss` into the image, inflating it from 200 bytes to 64 KB the moment you declare a global array.

## 10.3  startup.S, the bridge from reset to `main`

```asm
    .syntax unified
    .cpu    cortex-a7
    .section .vectors, "ax"
    .align  5                       @ vector table must be 32-byte aligned
    .global _vectors
_vectors:
    b       _start                  @ Reset           — we will replace these in Ch 15
    b       .                       @ Undef
    b       .                       @ SVC
    b       .                       @ Prefetch abort
    b       .                       @ Data abort
    b       .                       @ Reserved
    b       .                       @ IRQ
    b       .                       @ FIQ

    .section .text.startup, "ax"
    .global _start
_start:
    /* ------------------------------------------------------------------
     *  We are entered in SVC mode with IRQ/FIQ masked (CPSR.I = CPSR.F = 1).
     *  The MMU is off.  Caches are off.  Nothing is enabled.  Welcome.
     * ------------------------------------------------------------------ */

    /*  Make sure we're in SVC mode with both interrupt masks set.
        The ROM may have left us in another mode; SVC is what we want
        until Chapter 15 introduces a proper exception model.        */
    cpsid   if, #0x13               @ mode = SVC, mask IRQ+FIQ

    /*  Stack: top of OCRAM, defined by the linker. */
    ldr     sp, =_stack_top

    /*  Zero .bss : for (p = &_sbss; p < &_ebss; p++) *p = 0; */
    ldr     r0, =_sbss
    ldr     r1, =_ebss
    mov     r2, #0
1:  cmp     r0, r1
    strlo   r2, [r0], #4
    blo     1b

    /*  Copy .data from LMA to VMA.  In our current layout they are equal,
        so this loop copies zero bytes.  Keep it; the day we move .data to
        DRAM it earns its salary. */
    ldr     r0, =_etext             @ source (LMA)
    ldr     r1, =_sdata             @ destination (VMA)
    ldr     r2, =_edata
2:  cmp     r1, r2
    ldrlo   r3, [r0], #4
    strlo   r3, [r1], #4
    blo     2b

    /*  Branch to main.  Pass argc=0, argv=NULL, just to be polite. */
    mov     r0, #0
    mov     r1, #0
    bl      main

    /*  main() should never return.  If it does, halt cleanly. */
hang:
    wfi
    b       hang
```

A few notes on the assembly choices:

- **`cpsid if, #0x13`** is a `cps` instruction with the side effect of setting the mode bits to `0b10011` (SVC) and the I and F mask bits. One instruction. Three guarantees.
- **`strlo r2, [r0], #4`** is post-indexed: store, *then* add 4 to r0. `lo` (= `cc` = unsigned less-than) is the AAPCS-comparison flag that pairs with `cmp` in our loop. This conditional store/post-increment idiom is so common in ARM startup that you should be able to read it instantly.
- **`bl main`** is *branch-and-link*: it sets LR to the return address before branching. If `main` does return, we fall through to `hang`. The `wfi` (Wait For Interrupt) instruction makes the core idle in a low-power state instead of busy-spinning at 396 MHz, which is at least polite to the power budget.
- **`.section .text.startup`** puts our startup code in a named subsection. The linker script's `*(.text*)` matches `.text.startup` and pulls it in early. We could just put it in plain `.text`, naming it explicitly is hygiene, not necessity.
- The vector table at the top is mostly placeholder `b .` (branch-to-self). In Chapter 15 we replace those self-loops with real handlers.

## 10.4  `main.c`, the LED, again

> **Lab vs production:** Do not burn fuses, enroll production keys, or sign release images while following the lab.
> Use throwaway keys and back up the unsigned image plus the key directory before testing irreversible security flows.


```c
#include <stdint.h>

#define REG(addr) (*(volatile uint32_t *)(addr))

#define CCM_CCGR1   0x020C406C
#define IOMUX_MUX   0x020E0068
#define IOMUX_PAD   0x020E02F4
#define GPIO1_DR    0x0209C000
#define GPIO1_GDIR  0x0209C004
#define LED_BIT     (1u << 3)

static void delay(volatile uint32_t n)
{
    while (n--) { asm volatile ("nop"); }
}

int main(void)
{
    REG(CCM_CCGR1) |= (3u << 26);   /* GPIO1 clock on */
    REG(IOMUX_MUX) = 5;             /* ALT5 = GPIO */
    REG(IOMUX_PAD) = 0x10B0;        /* standard low-speed output */
    REG(GPIO1_GDIR) |= LED_BIT;     /* output */

    for (;;) {
        REG(GPIO1_DR) ^= LED_BIT;
        delay(2000000);
    }
}
```

Three things that look small but matter:

- **`volatile` on the cast.** Without `volatile`, the optimizer is free to assume `REG(GPIO1_DR)` reads always return the same value, and to elide the second read entirely in a tight loop. With `volatile`, the compiler emits a real load-store every time. Every MMIO access in this book is `volatile`.
> **MMIO:** memory-mapped I/O, where software accesses peripheral registers through normal load and store instructions.
- **`volatile` on `delay`'s argument.** Same reason: prevents the compiler from observing that the loop has no side effects and deleting it. The `asm volatile ("nop")` inside is belt-and-braces, even if the optimizer somehow folded the decrement, the nop forces a barrier.
- **`(3u << 26)` not `(3 << 26)`.** `26` plus a signed `3` is fine on 32-bit but the `u` suffix silences certain `-Wconversion` warnings cleanly. House style.

## 10.5  The Makefile

```make
CROSS    := arm-none-eabi-
CC       := $(CROSS)gcc
LD       := $(CROSS)ld
OC       := $(CROSS)objcopy
SIZE     := $(CROSS)size

CFLAGS   := -mcpu=cortex-a7 -mfpu=neon-vfpv4 -mfloat-abi=hard \
            -ffreestanding -fno-builtin -nostdlib \
            -fno-common -O2 -g -Wall -Wextra -Werror=implicit-function-declaration

LDFLAGS  := -T link.ld -nostdlib

OBJS     := startup.o main.o

all: led.bin

%.o: %.S
	$(CC) $(CFLAGS) -c -o $@ $<

%.o: %.c
	$(CC) $(CFLAGS) -c -o $@ $<

led.elf: $(OBJS) link.ld
	$(CC) $(LDFLAGS) -o $@ $(OBJS)
	$(SIZE) $@

led.bin: led.elf
	$(OC) -O binary $< $@

clean:
	rm -f *.o *.elf *.bin

.PHONY: all clean
```

A couple of flags worth highlighting:

- **`-fno-common`**: forces every uninitialized global into `.bss` instead of "common" symbols. Without this, two files declaring `int foo;` would silently coalesce, which is convenient on hosted Linux and dangerous on bare-metal.
- **`-Werror=implicit-function-declaration`**: we never tolerate "I forgot to include the header." It is one of the cheapest bugs to prevent.
- **`-O2 -g`** together, optimize but keep DWARF. The `-g` does not affect the binary. It only enlarges the ELF.

## 10.6  Building and running

```sh
$ make
arm-none-eabi-gcc ... -c -o startup.o startup.S
arm-none-eabi-gcc ... -c -o main.o main.c
arm-none-eabi-gcc -T link.ld -nostdlib -o led.elf startup.o main.o
arm-none-eabi-size led.elf
   text    data     bss     dec     hex filename
    288       0       0     288     120 led.elf
arm-none-eabi-objcopy -O binary led.elf led.bin
$ wc -c led.bin
288 led.bin
```

A few observations:

- **`text` grew from ~160 bytes (Ch 9) to 288 bytes.** We added a vector table (32 bytes) and the C function-call prologue/epilogue. Cheap.
- **`data` is 0.** No initialized globals in our C.
- **`bss` is 0.** No uninitialized globals.

Now `data` and `bss` are exercised but we are not yet using them. Let us add a `.data` value just to confirm the copy loop works:

In `main.c`, change `LED_BIT`:

```c
static uint32_t led_mask = (1u << 3);   /* now in .data */
```

Use `led_mask` in place of the `LED_BIT` macro. Rebuild:

```sh
$ arm-none-eabi-size led.elf
   text    data     bss     dec     hex filename
    296       4       0     300     12c led.elf
```

`data` is 4. The copy loop in `startup.S` now copies 4 bytes from LMA to VMA. Same end behavior. Meaningful test of the machinery.

Wrap into `.imx` (same `wrap.sh` from Chapter 9) and push:

```sh
$ ./wrap.sh
$ uuu -b sdp led.imx
```

LED blinks. We're now running compiled C on bare metal.

## 10.7  Stepping through with `objdump`

It is worth reading the disassembled startup once. After `make`:

```sh
$ arm-none-eabi-objdump -d led.elf | head -80
```

Find `_start`. You will see the four blocks:

1. The mode-setting `cpsid` instruction.
2. The `ldr sp, =_stack_top` literal load.
3. The `.bss` zero loop.
4. The `.data` copy loop.
5. The `bl main`.

The literal pool follows the function. You can see the resolved addresses there.

If you change the linker script's `OCRAM` origin, *every* literal-pool address changes, and that is what `ldr ... =const` is for. Try it: change ORIGIN to `0x00908000`, rebuild, redump. Confirm the literals updated. Then change it back.

## 10.8  What if `main()` returns?

In `startup.S`, after `bl main`, we fall through to a `hang` loop. In real life `main()` should never return on bare-metal. But during development it does happen, you `return` accidentally, you let an `if (...) return;` slip in. The `hang` saves you from "what the hell, the LED stopped" without obvious cause.

You can make the dependency explicit by giving `main` the `__attribute__((noreturn))`:

```c
__attribute__((noreturn)) int main(void) { ... }
```

GCC then warns if `main` has a code path that returns. Optional but informative.

## 10.9  Why `volatile`, one more time

A common bug:

```c
*(uint32_t *)CCM_CCGR1 |= (3u << 26);
```

Without `volatile`, the compiler is allowed to:

- assume that `*(uint32_t *)CCM_CCGR1` does not change between reads,
- merge consecutive accesses to the same address,
- eliminate the read entirely if the value isn't used.

In the LED program, these freedoms produce code that happens to work, because we touch each register exactly once. But the moment you write code like:

```c
while ((REG(UART_STATUS) & TX_EMPTY) == 0) {}
```

…without `volatile`, the compiler treats `UART_STATUS` as constant inside the loop, reads it once before the loop, and spins forever. Most embedded engineers hit this bug once. Avoid it by reflex.

Rule: **every memory-mapped register access uses `volatile`. Every one.** Macroize it once (as we did with `REG()`) and stop thinking about it.

## 10.10  Lab

1. **Build and run.** Confirm LED blinks.
2. **Inspect the ELF.** `objdump -h led.elf`, list every section. Match each against the linker script. Note that `.bss` reports a size > 0 (if you added the `led_mask` variant) but is `NOBITS` type, meaning no file bytes.
3. **Add a `.bss` global.** Add `static uint32_t counter;` and increment it in the loop. Confirm `.bss` grows by 4 bytes in `size led.elf` and that the program still works (i.e., your zero-loop is doing its job).
4. **Break the zero-loop on purpose.** Comment out the `.bss` zero loop in startup. Re-add the counter. Now `counter`'s initial value is whatever was in OCRAM. Observe non-deterministic behavior across power cycles. Restore.
5. **Break the data-copy loop on purpose.** Initialize `static uint32_t led_mask = (1u << 3);` again, and comment out the copy loop. Without the copy, `led_mask` reads whatever was in OCRAM at boot. Observe failure. Restore.

## 10.11  Pitfalls

- **`bss` not zeroed.** Symptom: nondeterministic startup behavior across resets. Cause: forgot the loop, or got the `_sbss`/`_ebss` symbols wrong in the linker script.
- **`.data` not copied.** Symptom: globals appear to have random initial values. Cause: forgot the copy loop, or `AT(_etext)` not in the linker script (so LMA and VMA collided in a way the loop didn't notice).
- **Stack not aligned at function entry.** AAPCS requires SP to be 8-byte aligned at every public function entry. `_stack_top = ORIGIN + LENGTH` aligns naturally as long as LENGTH is a multiple of 8. Change LENGTH to an odd value and expect crashes inside libgcc helpers.
- **`-fno-common` not set.** Two `int foo;` declarations in two `.c` files silently merge into one symbol. Sometimes the result works, sometimes it corrupts memory. Always enable.
- **Forgot `volatile`.** Discussed above.
- **Linker script does not declare `.rodata`.** GCC may emit string literals into `.rodata`, which falls through to the next region. We folded `.rodata` into `.text` here. If you split them out, make sure both are placed in OCRAM.
- **`_sbss` is not 4-byte aligned.** Our `ALIGN(4)` on `.bss` handles this. If you ever remove it, the `strlo r2, [r0], #4` in startup will hit an unaligned-address fault.

## 10.12  Going deeper

- The GNU `ld` manual, section "Output Section Description", the full SECTIONS grammar.
- LLVM's `lld` manual has a much shorter introduction to the same concepts, useful for the second-time reader.
- `arm-none-eabi-gcc -E -P -x c /dev/null -include <stdint.h>`: see what `stdint.h` actually defines on your target.
- *Mastering ARM Embedded Programming* (Marwedel, 2018), the chapter on startup code is excellent.
- The U-Boot source's `arch/arm/lib/crt0.S`, read it after this chapter. The patterns are the same.
> **MCU bridge:** Think of U-Boot like a much larger boot stub plus debug monitor: it initializes hardware, loads the next image, and gives you commands before Linux starts.
> **U-Boot:** the bootloader that initializes enough hardware to load and start the Linux kernel.

## Sidebar, `REG(addr)` macro vs the NXP SDK header

We are using `#define REG(addr) (*(volatile uint32_t *)(addr))` plus raw addresses. The professional alternative is the **NXP SDK header** `MCIMX6Y2.h` (downloadable from `mcuxpresso.nxp.com`), which provides struct-based register access:

```c
#include "MCIMX6Y2.h"

UART1->UCR1 = 0;                  // typed access; the struct knows offsets
UART1->UCR2 |= UART_UCR2_TXEN_MASK;
GPIO1->GDIR |= (1u << 3);    // GPIO1_IO03 = output (LED0 cathode side)
```

Both styles compile to identical machine code. The trade-offs:

| | `REG(addr)` (this book) | NXP SDK header |
|---|---|---|
| Explicitness | The address is in your face | Hidden inside the struct |
| Risk of typos | High, `0x020E0068` vs `0x020E006B` | Low, autocomplete saves you |
| Portability | One `.h` per SoC family at most | One `.h` per exact part |
| Debugger view | `*(uint32_t *)0x020E0068` | `IOMUXC->SW_MUX_CTL_PAD_GPIO1_IO03` |
| Learning value | Maximum (you see the addresses) | Lower (you trust the header) |

In Chapter 18A we refactor a few chapters' code to show the SDK style side-by-side. For learning, we recommend the raw style. For production, the SDK style.

> Next chapter: **Chapter 11: Hand-building a Boot ROM-acceptable image.** We promote `wrap.sh` into a real tool, decode every byte of the IVT, and `dd` an SD card by hand.
