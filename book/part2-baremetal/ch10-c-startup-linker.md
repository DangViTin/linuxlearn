# Chapter 10: C + startup.S + linker script

The LED already blinks. Rewriting its loop in C ought to be a small change, but C arrives with expectations: a usable stack, initialized globals and zero-initialized static storage. The compiler generates code on that basis. It does not arrange those conditions for this flat, ROM-loaded image.

We will keep the same LED and supply the missing work before calling `main()`. The linker script describes where code and objects belong. `startup.S` uses that description to prepare memory. Seeing those two files agree is more useful than treating startup as a block to paste into every project.


## 10.1  What an initialized global needs

Consider a C file with three globals:

```c
int   x = 7;           // initialized → .data
int   y;               // uninitialized → .bss
const int z = 42;      // const + initialized → .rodata
```

On Linux, the loader establishes the ELF's loadable memory segments and zero-filled storage before the C runtime calls `main()`. Here the Boot ROM loads our image, but it does not interpret the ELF or initialize C objects. We give it a flat binary wrapped in an IVT.

So we, ourselves, must:
- **Set an aligned stack pointer.** A C function may use the stack even when its source has no obvious local array or function call.
- **Zero `.bss`.** Otherwise `y` is whatever was in OCRAM when we arrived.
- **Copy `.data` from its load location to its run location when those differ.** This is the LMA-versus-VMA distinction from Chapter 6.
- **Branch to `main`.**

Optionally, also: set up exception vectors, configure caches, enable the FPU. We do these later as we need them.

```{figure} ../illustrations/part2/02-startup-before-c.png
:alt: Before calling main, startup establishes a stack, clears BSS and prepares initialized data. A stored value of seven agrees with the value the C object must hold.
:width: 100%
:figclass: concept-sketch
:name: fig-part2-startup-before-c

These are promises made to C before it runs. Preparing data means putting the initial value at its runtime address. In our first layout it is already there, so a copy is not yet a relocation test.
```

## 10.2  A linker script worth keeping
Create `~/imx6ull/src/ch10-c-startup` in your editor. Save the four complete listings in this chapter as `link.ld`, `startup.S`, `main.c` and `Makefile`. Copy Chapter 9's `wrap.py` into this directory. In each new build terminal, run `. ~/imx6ull/scripts/env.sh` before entering the directory.

The Chapter 9 program needed only `.text`. Now we also describe initialized storage, zero-initialized storage and space for a stack. Save this as `link.ld`:

```text
ENTRY(_vectors)

MEMORY
{
    OCRAM (rwx) : ORIGIN = 0x00908000, LENGTH = 0x00018000  /* 96 KB */
}

SECTIONS
{
    . = ORIGIN(OCRAM);

    .text ALIGN(32) : {
        KEEP(*(.vectors))      /* room for vector table later (Ch 15) */
        *(.text*)
        *(.rodata*)
        . = ALIGN(4);
    } > OCRAM

    /* Mark the end of .text -- LMA of .data begins here. */
    _etext = .;

    /*
     * .data : runtime in OCRAM, image-time directly after .text.
     * Because OCRAM and our image both live in the same region, LMA == VMA
     * for this layout. The startup copy writes each word back to itself.
     * Keep the source and destination explicit for a later split layout.
     */
    .data ALIGN(4) : AT(_etext) {
        _sdata = .;
        *(.data*)
        . = ALIGN(4);
        _edata = .;
    } > OCRAM
    _sidata = LOADADDR(.data);

    .bss ALIGN(4) (NOLOAD) : {
        _sbss = .;
        *(.bss*)
        *(COMMON)
        . = ALIGN(4);
        _ebss = .;
    } > OCRAM

    _stack_top = ORIGIN(OCRAM) + LENGTH(OCRAM);
    _stack_limit = _stack_top - 0x1000;  /* reserve 4 KiB after ROM handoff */
    ASSERT(_ebss <= _stack_limit, "Objects overlap the reserved stack")
    ASSERT(_edata <= 0x00918000, "Loaded bytes overlap ROM-active RAM")

    /DISCARD/ : { *(.note*) *(.comment) *(.ARM.exidx*) *(.ARM.extab*) }
}
```

Decoded line by line:

- **`ENTRY(_vectors)`** records the ELF entry at our first instruction, `b _start`, at `0x00908000`. The wrapper uses the same address in the IVT. `_start` itself follows the eight vector slots. The ROM reads the IVT, not this ELF field.
- **`MEMORY { OCRAM ... }`**: describes our one available region. `ORIGIN` is where the wrapper places the first program byte. `LENGTH` covers the remaining 96 KB up to the end of OCRAM at `0x00920000`.
- **`. = ORIGIN(OCRAM);`**: the location counter starts at the region's base.
- **`.text` section**: gathers all `.text*`, `.rodata*`, plus a `KEEP(*(.vectors))` placeholder for a future vector table. `KEEP` tells the linker not to remove this as unused, even if no symbol references it. The final `. = ALIGN(4);` makes `_etext` word-aligned.
- **`_etext = .;`**: captures the location counter. This is where `.text` ends. It is also where the `.data` *load image* will be placed (see next line).
- **`.data ALIGN(4) : AT(_etext)`**: `ALIGN(4)` aligns the runtime address. `AT(_etext)` sets the load address. Notice their positions around the colon. GNU `ld` rejects `.data : ALIGN(4) AT(_etext)` because `AT(...)` must come before a post-colon `ALIGN(...)`.
- **`_sidata = LOADADDR(.data)`**: asks the linker for `.data`'s actual load address. Startup code uses this symbol as its copy source.
- **`_sdata` / `_edata`**: boundary symbols our startup uses to know how much to copy.
- **`.bss (NOLOAD)`** reserves zero-initialized storage without carrying its contents in our load image. Startup clears the range between `_sbss` and `_ebss`. We round both data-section ends to four bytes because our loops copy or clear whole words.
- **`_stack_top` / `_stack_limit`** reserve 4 KiB for a descending stack. This is a budget, not an automatic stack-overflow guard. Loaded bytes must fit below `0x00918000` while ROM is active. Our own stack uses the upper OCRAM only after handoff, without returning to ROM services.
- **`/DISCARD/`**: throws away ELF notes and attributes that have no place in a bare-metal binary.

Four things in this script are easy to get wrong. Check them now.

1. **Putting `ALIGN` and `AT` in the wrong order.** Use `.data ALIGN(4) : AT(_etext)`. Linker-script keywords have a fixed grammar, and `ld` reports only a line number when this order is wrong.
2. **Forgetting `KEEP` around the vector table.** When you later link with `-gc-sections`, the linker removes the table because nothing in C references it. `KEEP` prevents this.
3. **Assuming the linker moves bytes.** `AT(...)` describes a load address. It does not perform the startup copy. Without an explicit LMA, GNU ld uses layout-dependent rules, not a universal promise that it equals the VMA.
4. **Assuming `.bss` needs stored zeros.** Ordinary ELF `.bss` is normally `NOBITS` even without `NOLOAD`. Check its type and the raw binary size. The explicit `NOLOAD` makes our layout's intention clear.

## 10.3  startup.S, the bridge from reset to `main`

```asm
    .syntax unified
    .cpu    cortex-a7
    .arm
    .section .vectors, "ax"
    .align  5                       @ vector table must be 32-byte aligned
    .global _vectors
_vectors:
    b       _start                  @ Reset, replaced in Ch 15
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
    /* Direct entry from a fresh open-device ROM boot, not U-Boot.
       Mask asynchronous interrupts and select our working mode. */
    cpsid   if, #0x13               @ mode = SVC, mask IRQ+FIQ

    /* Use our aligned placeholder vectors instead of ROM handlers. */
    mrc     p15, 0, r0, c1, c0, 0
    bic     r0, r0, #(1 << 13)      @ SCTLR.V = 0, use VBAR
    mcr     p15, 0, r0, c1, c0, 0
    ldr     r0, =_vectors
    mcr     p15, 0, r0, c12, c0, 0
    isb

    /*  Stack: top of OCRAM, defined by the linker. */
    ldr     sp, =_stack_top

    /*  Zero .bss : for (p = &_sbss; p < &_ebss; p++) *p = 0; */
    ldr     r0, =_sbss
    ldr     r1, =_ebss
    mov     r2, #0
1:  cmp     r0, r1
    strlo   r2, [r0], #4
    blo     1b

    /*  Copy .data from LMA to VMA. In our current layout they are equal,
        so each word is copied onto itself. When .data moves to another
        memory region, this same loop performs the required relocation. */
    ldr     r0, =_sidata            @ source (LMA)
    ldr     r1, =_sdata             @ destination (VMA)
    ldr     r2, =_edata
2:  cmp     r1, r2
    ldrlo   r3, [r0], #4
    strlo   r3, [r1], #4
    blo     2b

    /* main(void) takes no arguments. */
    bl      main

    /*  main() should never return.  If it does, halt cleanly. */
hang:
    wfi
    b       hang
```

A few notes on the assembly choices:

- **`cpsid if, #0x13`** is a `cps` instruction with the side effect of setting the mode bits to `0b10011` (SVC) and the I and F mask bits. One instruction. Three guarantees.
- **`strlo r2, [r0], #4`** stores a word, then advances the pointer by four bytes when the preceding unsigned comparison says `r0 < r1`. `lo` is the condition-code spelling for unsigned lower, not an AAPCS-specific flag.
- **`bl main`** records a return address in LR and branches. If `main` returns, `hang` repeatedly executes `wfi`. This supplies a defined place to stop, not a full power-management configuration.
- **`.section .text.startup`** puts our startup code in a named subsection. The linker script's `*(.text*)` matches `.text.startup` and pulls it in early. We could put it in plain `.text`, but the explicit name makes the startup code easier to find.
- The vector table contains a reset-slot branch followed by seven self-loops. We install its address in VBAR here, but do not enable IRQ/FIQ. Chapter 15 replaces the placeholders with useful handlers.

Do not read CPU reset defaults as ROM handoff defaults. RM 8.4.4 says the ROM enables the instruction cache during download and disables the data caches and MMU after authentication. This startup is for that direct ROM path. A jump from an existing bootloader may require cache cleanup, MMU changes and peripheral reinitialization that this listing does not supply. Chapter 17 handles our own memory attributes and caches.

## 10.4  `main.c`, the LED, again
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
    REG(IOMUX_PAD) = 0x17059;       /* vendor LED pad setting */
    REG(GPIO1_DR) |= LED_BIT;       /* preload LED off */
    REG(GPIO1_GDIR) |= LED_BIT;     /* output */

    for (;;) {
        REG(GPIO1_DR) ^= LED_BIT;
        delay(500000);
    }
}
```

Three things that look small but matter:

- **`volatile` on the cast.** Without `volatile`, the optimizer is free to assume `REG(GPIO1_DR)` reads always return the same value, and to elide the second read entirely in a tight loop. With `volatile`, the compiler emits a real load-store every time. Every MMIO access in this book is `volatile`.
- **The busy delay.** The volatile counter and `asm volatile ("nop")` keep observable work in the loop. Neither makes the duration precise. A `nop` is not a memory barrier. Chapter 16 replaces instruction counting with a timer.
- **`(3u << 26)`.** Unsigned masks make bitwise intent explicit. This particular signed shift would also fit a 32-bit `int`, but higher-bit masks may not.

## 10.5  The Makefile

```make
CROSS    := arm-none-eabi-
CC       := $(CROSS)gcc
LD       := $(CROSS)ld
OC       := $(CROSS)objcopy
SIZE     := $(CROSS)size

ARCH     := -mcpu=cortex-a7 -marm -mfloat-abi=soft -mgeneral-regs-only
CFLAGS   := $(ARCH) \
            -ffreestanding -fno-builtin -nostdlib \
            -fno-common -fno-unwind-tables -fno-asynchronous-unwind-tables \
            -MMD -MP -O2 -g -Wall -Wextra -Werror=implicit-function-declaration

LDFLAGS  := $(ARCH) -T link.ld -nostdlib

OBJS     := startup.o main.o
DEPS     := $(OBJS:.o=.d)

all: led.bin

%.o: %.S Makefile
	$(CC) $(CFLAGS) -c -o $@ $<

%.o: %.c Makefile
	$(CC) $(CFLAGS) -c -o $@ $<

led.elf: $(OBJS) link.ld Makefile
	$(CC) $(LDFLAGS) -o $@ $(OBJS) -lgcc
	$(SIZE) $@

led.bin: led.elf
	$(OC) -O binary $< $@

clean:
	rm -f $(OBJS) $(DEPS) led.elf led.bin led.imx

-include $(DEPS)

.PHONY: all clean
```

A couple of flags worth highlighting:

- **`-marm -mfloat-abi=soft -mgeneral-regs-only`** keeps these early integer-only C examples in ARM state and prevents GCC from using VFP/NEON registers before we enable that hardware. Use the same architecture/ABI options at link time. We explicitly add `-lgcc` after our objects for compiler helpers such as integer division. This is not libc.
- **`-MMD -MP` and `Makefile` prerequisites** rebuild objects when included headers or build flags change. Otherwise an old object can survive an apparently successful `make`.

- **`-fno-common`**: forces every uninitialized global into `.bss` instead of "common" symbols. Without this, two files declaring `int foo;` would merge without a clear warning. That is convenient on hosted Linux and dangerous on bare-metal.
- **`-Werror=implicit-function-declaration`**: we never tolerate "I forgot to include the header." It is one of the cheapest bugs to prevent.
- **`-O2 -g`** together, optimize but keep DWARF. The `-g` does not affect the binary. It only enlarges the ELF.

## 10.6  Building and running

```sh
$ make
$ arm-none-eabi-size led.elf
$ arm-none-eabi-readelf -h led.elf
$ arm-none-eabi-nm -n led.elf
$ wc -c led.bin
```

A few observations:

- **`text` grows.** The image now includes the vector slots, memory-initialization loops and compiled C. Read your own size output rather than expecting one fixed byte count.
- **`data` is 0.** No initialized globals in our C.
- **`bss` is 0.** No uninitialized globals.

The loops are present, but their ranges are empty. To give `.data` a visible object, replace the `LED_BIT` macro with:

In `main.c`, change `LED_BIT`:

```c
static volatile uint32_t led_mask = (1u << 3);   /* stored in .data */
```

Use `led_mask` in place of every use of `LED_BIT`. The volatile qualifier keeps GCC from replacing this demonstration object with a constant. Rebuild and inspect:

```sh
$ arm-none-eabi-size led.elf
$ arm-none-eabi-readelf -SW led.elf
$ arm-none-eabi-nm -n led.elf
```

The object occupies four bytes. Compare `_sidata` and `_sdata`: in this layout they are equal. The ROM has already placed the initial value at its runtime address. The loop copies it onto itself, so disabling the copy would not demonstrate a failure. A separate source and destination are needed to test relocation, as in the later DDR work.

Check `_vectors` and the ELF entry at `0x00908000`. `_start` is after the vector slots. If GNU ld reports an RWX load-segment warning, it describes this small combined code/data layout. It is not a report that the MMU has installed page permissions.

Wrap into `.imx` with the same `wrap.py` from Chapter 9 and push:

```sh
$ python3 wrap.py
$ sudo "$IMX6ULL_HOME/build/mfgtools/uuu/uuu" led.imx
```

If the LED blinks again, our startup has reached compiled C. That observation alone does not test empty `.bss` or a relocated `.data` section. The lab below makes those limits explicit.

## 10.7  Stepping through with `objdump`

It is worth reading the disassembled startup once. After `make`:

```sh
$ arm-none-eabi-objdump -d led.elf | head -80
```

Find `_start`. Follow the working-mode and vector setup, then the stack, clear, copy and call blocks:

1. The mode-setting `cpsid` instruction.
2. The `ldr sp, =_stack_top` literal load.
3. The `.bss` zero loop.
4. The `.data` copy loop.
5. The `bl main`.

The literal pool follows the function. You can see the resolved addresses there.

If you change the linker script's `OCRAM` origin, every code address changes. The image wrapper's entry and code placement must change with it. Try changing `ORIGIN` to `0x00909000`, rebuild, and inspect the new addresses. Then restore `0x00908000` before wrapping the image.

## 10.8  What if `main()` returns?

In `startup.S`, after `bl main`, we fall through to a `hang` loop. In normal bare-metal code, `main()` should never return. During development, it can happen by accident, for example from an unintended `return` or `if (...) return;`. The `hang` loop gives you a stable failure state instead of letting execution continue into unknown memory.

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
- remove or combine accesses when ordinary-memory rules permit it.

In the LED program, these freedoms produce code that happens to work, because we touch each register exactly once. But the moment you write code like:

```c
while ((REG(UART_STATUS) & TX_EMPTY) == 0) {}
```

…without `volatile`, the compiler treats `UART_STATUS` as constant inside the loop, reads it once before the loop, and spins forever. Most embedded engineers hit this bug once. Avoid it by reflex.

Use volatile access for MMIO, but keep reading the register definition. `REG(x) |= mask` is still a read-modify-write operation. It can be wrong for write-one-to-clear status bits or registers with read side effects. Volatile also does not supply atomicity, cache maintenance or CPU memory ordering. Those are separate decisions.

## 10.10  Lab

1. **Build and run.** Confirm LED blinks.
2. **Inspect the ELF.** Use `readelf -SW led.elf` for section types and `objdump -h led.elf` for VMA/LMA. The `led_mask` variant changes `.data`, not `.bss`.
3. **Add a `.bss` object.** Add `static volatile uint32_t counter;`. Before the loop, stop in a `for (;;) {}` if it is nonzero. Increment it in the blink loop. Confirm four bytes of `.bss` storage and a `NOBITS` section. A blinking result checks the initial value, not whether SRAM happened to be zero without startup.
4. **Make the clear test deterministic.** In `startup.S`, immediately before the clear loop, load `_sbss` into `r0`, load `0xA5A5A5A5` into `r2`, and store `r2` through `r0`. Do this only with the four-byte counter variant. With the clear loop present, the counter begins at zero. With it removed, the nonzero check stops the LED. Restore the normal startup afterward. Do not rely on power-up RAM being randomly nonzero.
5. **Predict the copy result.** With the current equal LMA/VMA, would omitting the copy change `led_mask`? No: its initialization bytes are already there. Record that result rather than trying to provoke a failure the layout cannot produce.

## 10.11  Pitfalls

- **`bss` not zeroed.** Symptom: nondeterministic startup behavior across resets. Cause: forgot the loop, or got the `_sbss`/`_ebss` symbols wrong in the linker script.
- **`.data` not copied in a split layout.** When LMA differs from VMA, the initial values must reach the runtime destination before C reads them. The current equal-address layout cannot expose a missing copy.
- **Stack not aligned at function entry.** AAPCS requires SP to be 8-byte aligned at every public function entry. `_stack_top = ORIGIN + LENGTH` aligns naturally as long as LENGTH is a multiple of 8. Change LENGTH to an odd value and expect crashes inside libgcc helpers.
- **`-fno-common` not set.** Two `int foo;` declarations in two `.c` files merge into one symbol without a clear warning. Sometimes the result works, sometimes it corrupts memory. Always enable.
- **Forgot `volatile`.** Discussed above.
- **Linker script does not declare `.rodata`.** GCC may emit string literals into `.rodata`, which falls through to the next region. We folded `.rodata` into `.text` here. If you split them out, make sure both are placed in OCRAM.
- **Misaligned section boundaries.** Our word loops require aligned starts and rounded-up ends. An unrounded byte-sized object can otherwise make the final word store cross a section boundary. Do not rely on a particular alignment-fault configuration to catch it.

## 10.12  Going deeper

- [GNU ld: output-section attributes](https://sourceware.org/binutils/docs/ld/Output-Section-Attributes.html) and [load addresses](https://sourceware.org/binutils/docs/ld/Output-Section-LMA.html).
- LLVM's `lld` manual has a much shorter introduction to the same concepts, useful for the second-time reader.
- `arm-none-eabi-gcc -E -P -x c /dev/null -include stdint.h`: inspect the target's integer typedefs. Do not put shell redirection brackets around the header name.
- [GCC: Arm options](https://gcc.gnu.org/onlinedocs/gcc/ARM-Options.html) and [volatile accesses](https://gcc.gnu.org/onlinedocs/gcc/Volatiles.html).
- The U-Boot source's `arch/arm/lib/crt0.S`, read it after this chapter. The patterns are the same.

## Sidebar, `REG(addr)` macro vs the NXP SDK header

We use raw addresses to keep the register lookup visible. A matching, verified vendor header can instead provide typed register layouts and bit masks. The following illustrates that style, not an extra dependency required for this lab. Obtain the header from the exact vendor SDK or board package and check its SoC and revision:

```c
#include "MCIMX6Y2.h"

UART1->UCR1 = 0;                  // typed access; the struct knows offsets
UART1->UCR2 |= UART_UCR2_TXEN_MASK;
GPIO1->GDIR |= (1u << 3);    // GPIO1_IO03 = output (LED0 cathode side)
```

With matching addresses and types, both styles can produce the same register-access instructions. The trade-offs:

| | `REG(addr)` (this book) | NXP SDK header |
|---|---|---|
| Explicitness | The address is in your face | Hidden inside the struct |
| Risk of typos | High, `0x020E0068` vs `0x020E006B` | Low, autocomplete saves you |
| Portability | One `.h` per SoC family at most | One `.h` per exact part |
| Debugger view | `*(uint32_t *)0x020E0068` | `IOMUXC->SW_MUX_CTL_PAD_GPIO1_IO03` |
| Reading focus | Address and bit-field lookup | Named peripheral layout, still checked against the RM |

Chapter 18A separates register definitions from driver policy. Raw addresses and typed headers can both be appropriate. Neither removes the need to verify offsets, reserved bits and register access semantics.

> Next chapter: **Chapter 11: Hand-building a Boot ROM-acceptable image.** We extend `wrap.py` into a reusable tool, decode every byte of the IVT, and `dd` an SD card by hand.
