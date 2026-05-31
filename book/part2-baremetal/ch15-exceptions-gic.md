---
chapter: 15
title: Exceptions and the GIC
part: II — Bare-metal i.MX6ULL
estimated_pages: 26
status: draft
---

# Chapter 15 — Exceptions and the GIC

> **What:** install a real ARMv7-A exception vector table, configure the GIC v2 distributor and CPU interface, route the UART1 interrupt to the core, and write an ISR that echoes received characters.
> **Why:** every kernel, every RTOS, and most useful bare-metal programs are interrupt-driven. The polling we have used so far works for hello-world; it falls apart the moment more than one peripheral needs attention.
> **Focus:** the **two-stage IRQ flow** — the GIC routes to the CPU; the CPU vectors to your handler; the handler reads the GIC for the IRQ ID, dispatches, writes EOI. Once you can draw this without looking, every other A-profile system makes sense.

## 15.1  What is different from Cortex-M

In Cortex-M:

- The NVIC is inside the CPU.
- Hardware auto-stacks R0–R3, R12, LR, PC, xPSR on the active stack.
- The vector table is an array of *function pointers*; the CPU loads PC directly from the slot.
- `BX LR` (with magic EXC_RETURN) tells hardware to unstack.

In Cortex-A7:

- The GIC is outside the CPU (memory-mapped block).
- **No auto-stacking.** Your handler must save and restore registers itself.
- The vector table is an array of *branch instructions*, not function pointers.
- Return is an explicit `rfeia sp!` or equivalent.

The trade-off: A-profile gives you more flexibility (you can split handlers across modes, share register banks, etc.) at the cost of writing more boilerplate. Linux's `arch/arm/kernel/entry-armv.S` is several hundred lines of this boilerplate, all of it correct, all of it terrifying the first time you read it.

We will write a smaller version. The pattern is identical.

## 15.2  The exception vector table

ARMv7-A has eight exception entries, each 4 bytes (one instruction). They must be 32-byte aligned, and the CPU jumps to the appropriate offset based on what happened:

| Offset | Exception | Triggered by |
|--------|-----------|--------------|
| `+0x00` | Reset | POR, soft reset |
| `+0x04` | Undefined instruction | UND opcode |
| `+0x08` | SVC (Supervisor Call) | `svc` instruction (syscall on Linux) |
| `+0x0C` | Prefetch abort | Instruction-fetch fault |
| `+0x10` | Data abort | Load/store fault |
| `+0x14` | Reserved | (Was an "address exception" in ARMv4 — unused now) |
| `+0x18` | IRQ | External IRQ asserted by GIC |
| `+0x1C` | FIQ | External FIQ asserted by GIC |

Each entry is one instruction. Universally that instruction is `b <label>` or `ldr pc, =<label>` (the latter for far branches).

The table can live at one of two locations:

- **Low vectors** at virtual `0x00000000` — historical default; conflicts with our OCRAM/DRAM layout.
- **High vectors** at virtual `0xFFFF0000` — set by SCTLR.V=1.
- **VBAR** (Vector Base Address Register) — modern: set VBAR to *any* aligned address. We use this.

VBAR is a CP15 register:

```asm
ldr r0, =_vectors
mcr p15, 0, r0, c12, c0, 0  @ VBAR <- r0
```

After this write (plus an `isb`), exceptions vector to our table wherever we put it.

## 15.3  The new vector table

`vectors.S`:

```asm
    .syntax unified
    .cpu    cortex-a7
    .section .vectors, "ax"
    .align  5                       @ 32-byte aligned
    .global _vectors

_vectors:
    ldr     pc, =reset_handler       @ +0x00 Reset
    ldr     pc, =undef_handler       @ +0x04 Undefined
    ldr     pc, =svc_handler         @ +0x08 SVC
    ldr     pc, =prefetch_handler    @ +0x0C Prefetch abort
    ldr     pc, =data_handler        @ +0x10 Data abort
    ldr     pc, =unused_handler      @ +0x14 (reserved)
    ldr     pc, =irq_entry           @ +0x18 IRQ
    ldr     pc, =fiq_handler         @ +0x1C FIQ

    .text
    .global reset_handler
reset_handler:
    b       _start                   @ defined in startup.S

undef_handler:
prefetch_handler:
data_handler:
unused_handler:
svc_handler:
fiq_handler:
    b       .                        @ trap: branch to self forever

    .global irq_entry
irq_entry:
    /*
     * On entry to IRQ mode:
     *   LR_irq    = PC of interrupted instruction + 4
     *   SPSR_irq  = saved CPSR
     *   CPSR.M    = IRQ (0x12), CPSR.I = 1 (IRQs masked)
     *   r0..r12   = whatever was running
     */

    sub     lr, lr, #4              @ adjust LR_irq to point at the *interrupted*
                                    @ instruction (so RFE re-executes it... no, it
                                    @ resumes correctly with this -4 fixup)

    /* Save the interrupted state to the IRQ-mode stack as a "return frame". */
    srsdb   sp!, #0x12              @ store LR_irq and SPSR_irq to IRQ stack

    /* Switch to SVC mode for the body of the handler (still with IRQs masked).
       This way we use a more spacious stack and can call C functions safely. */
    cpsid   i, #0x13                @ mode=SVC, IRQ masked

    push    {r0-r3, r12, lr}        @ save caller-saved regs

    bl      c_irq_dispatch          @ <-- the C interrupt handler

    pop     {r0-r3, r12, lr}

    /* Switch back to IRQ mode and return via RFE */
    cpsid   i, #0x12
    rfeia   sp!                     @ pop {LR_irq, SPSR_irq} -> PC, CPSR
```

What is happening:

- **The `ldr pc, =sym` form** rather than `b sym` is used because `b` has a ±32 MB range, and our handler labels are far away in flash/DRAM. `ldr pc, =sym` is the universal far-branch idiom on ARM.
- **`sub lr, lr, #4`** before `srsdb`. The CPU put `PC_interrupted + 4` in `LR_irq`. The IRQ exception model has an architectural offset of 4 for IRQ (4 for IRQ, 8 for prefetch abort, 0 for SVC, etc., per RM table). Subtracting 4 gives us the correct address to return to.
- **`srsdb sp!, #0x12`** stores `{LR, SPSR}` to the IRQ-mode stack pointer. Mode 0x12 = IRQ. The `db` (decrement-before) and `!` (writeback) make it a stack push.
- **`cpsid i, #0x13`** switches to SVC mode and masks IRQs (which were already masked, but explicit). After this, we are on the SVC-mode stack.
- **`push {r0-r3, r12, lr}`** saves the caller-saved registers AAPCS expects us to preserve across the C function call.
- **`bl c_irq_dispatch`** is the standard branch-and-link, but with our preserved state. C function returns; SP back to where it was.
- **`cpsid i, #0x12`** moves back to IRQ mode (so `rfeia sp!` pops from the IRQ stack, where we pushed in `srsdb`).
- **`rfeia sp!`** pops two words: PC and CPSR. The CPU resumes with that PC and that mode/CPSR. Masking of IRQs is automatically restored from the SPSR we saved.

## 15.4  Setting up VBAR and a separate IRQ stack

In `startup.S`, after the existing prologue, add:

```asm
    /* Install vector table */
    ldr     r0, =_vectors
    mcr     p15, 0, r0, c12, c0, 0   @ VBAR
    isb

    /* IRQ mode needs its own stack.  Switch to IRQ mode, set sp_irq, return. */
    cps     #0x12                    @ mode = IRQ (no mask change)
    ldr     sp, =_irq_stack_top
    cps     #0x13                    @ back to SVC
```

In the linker script, reserve an IRQ stack:

```ld
SECTIONS
{
    ...
    .irq_stack (NOLOAD) : ALIGN(8) {
        . += 4096;                   /* 4 KB IRQ stack */
        _irq_stack_top = .;
    } > OCRAM
}
```

4 KB is generous; we will not stack deeply in an ISR.

## 15.5  The GIC v2 distributor + CPU interface

GIC v2 has two memory-mapped regions:

- **Distributor**: `0x00A01000`, 4 KB. Configures priorities, enables, sets targets, sees all interrupts in the system.
- **CPU Interface**: `0x00A02000`, 4 KB. Acknowledges interrupts, ends interrupts, masks based on priority. Per-CPU on multi-core; here we have one core.

Registers we will use (offsets within their region):

### Distributor (`GICD_*`)

| Register | Offset | Purpose |
|----------|--------|---------|
| `GICD_CTLR` | `+0x000` | Enable distributor (bit 0) |
| `GICD_TYPER` | `+0x004` | Read: number of supported IRQs |
| `GICD_ISENABLERn` | `+0x100 + 4n` | Enable bit per IRQ (bit `(irq % 32)` in word `irq/32`) |
| `GICD_ICENABLERn` | `+0x180 + 4n` | Disable (write-1-to-clear) |
| `GICD_ISPENDRn` | `+0x200 + 4n` | Set pending |
| `GICD_ICPENDRn` | `+0x280 + 4n` | Clear pending |
| `GICD_IPRIORITYRn` | `+0x400 + n` | Priority (8 bits each; 256 bytes for 256 IRQs) |
| `GICD_ITARGETSRn` | `+0x800 + n` | Target CPU mask (per IRQ; SPI only; PPI/SGI are fixed) |
| `GICD_ICFGRn` | `+0xC00 + 4n` | Trigger type (edge/level), 2 bits per IRQ |

### CPU Interface (`GICC_*`)

| Register | Offset | Purpose |
|----------|--------|---------|
| `GICC_CTLR` | `+0x000` | Enable CPU interface |
| `GICC_PMR` | `+0x004` | Priority mask (must be ≥ priority of IRQ to allow) |
| `GICC_BPR` | `+0x008` | Binary point (we set 0 = full priority resolution) |
| `GICC_IAR` | `+0x00C` | Read: pending IRQ ID + ack |
| `GICC_EOIR` | `+0x010` | Write: end-of-interrupt |
| `GICC_RPR` | `+0x014` | Running priority |
| `GICC_HPPIR` | `+0x018` | Highest priority pending |

A typical IRQ flow:

```
peripheral asserts SPI line
   ↓
GIC distributor sees it, latches in ISPENDR
   ↓
distributor compares priority against running priority on each CPU
   ↓
selects highest-priority CPU, asserts IRQ signal to that core
   ↓
core takes IRQ exception → our irq_entry
   ↓
our handler reads GICC_IAR  → gets the IRQ ID (e.g., 58 for UART1)
   ↓
dispatch on ID → call peripheral's ISR
   ↓
write IRQ ID to GICC_EOIR (signal "I'm done")
   ↓
return from exception → resume interrupted code
```

The pattern is identical in every GIC-based system, including the kernel.

## 15.6  GIC bring-up code

`gic.h`:

```c
#ifndef GIC_H
#define GIC_H
#include <stdint.h>

typedef void (*irq_handler_t)(void);

void gic_init(void);
void gic_register(uint32_t irq_id, irq_handler_t fn);
void gic_enable_irq(uint32_t irq_id);
void gic_disable_irq(uint32_t irq_id);

void c_irq_dispatch(void);  /* called from irq_entry assembly */

static inline void irq_enable(void)  { asm volatile ("cpsie i" ::: "memory"); }
static inline void irq_disable(void) { asm volatile ("cpsid i" ::: "memory"); }

#endif
```

`gic.c`:

```c
#include "gic.h"

#define REG(addr) (*(volatile uint32_t *)(addr))
#define GICD_BASE   0x00A01000
#define GICC_BASE   0x00A02000

#define GICD_CTLR        (GICD_BASE + 0x000)
#define GICD_TYPER       (GICD_BASE + 0x004)
#define GICD_ISENABLER(n) (GICD_BASE + 0x100 + 4*(n))
#define GICD_ICENABLER(n) (GICD_BASE + 0x180 + 4*(n))
#define GICD_IPRIORITYR(n) (GICD_BASE + 0x400 + (n))
#define GICD_ITARGETSR(n)  (GICD_BASE + 0x800 + (n))
#define GICD_ICFGR(n)     (GICD_BASE + 0xC00 + 4*(n))

#define GICC_CTLR    (GICC_BASE + 0x000)
#define GICC_PMR     (GICC_BASE + 0x004)
#define GICC_BPR     (GICC_BASE + 0x008)
#define GICC_IAR     (GICC_BASE + 0x00C)
#define GICC_EOIR    (GICC_BASE + 0x010)

#define MAX_IRQ      192          /* GIC reports 32 + 32×N total */

static irq_handler_t handlers[MAX_IRQ];

void gic_init(void)
{
    /* Read how many interrupts the distributor supports. */
    uint32_t typer = REG(GICD_TYPER);
    uint32_t num_lines = ((typer & 0x1F) + 1) * 32;
    if (num_lines > MAX_IRQ) num_lines = MAX_IRQ;

    /* Disable all interrupts at the distributor. */
    for (uint32_t i = 0; i < num_lines; i += 32) {
        REG(GICD_ICENABLER(i/32)) = 0xFFFFFFFFu;
    }

    /* Default priority = 0xA0 (medium-low), targets = CPU0 for all SPIs. */
    for (uint32_t i = 32; i < num_lines; i++) {
        ((volatile uint8_t *)(GICD_BASE + 0x400))[i] = 0xA0;
        ((volatile uint8_t *)(GICD_BASE + 0x800))[i] = 0x01; /* CPU0 */
    }

    /* Enable distributor. */
    REG(GICD_CTLR) = 1;

    /* CPU interface: priority mask wide open, no binary point. */
    REG(GICC_PMR)  = 0xFF;
    REG(GICC_BPR)  = 0x00;
    REG(GICC_CTLR) = 1;
}

void gic_register(uint32_t irq, irq_handler_t fn)
{
    if (irq < MAX_IRQ) handlers[irq] = fn;
}

void gic_enable_irq(uint32_t irq)
{
    REG(GICD_ISENABLER(irq/32)) = 1u << (irq & 0x1F);
}

void gic_disable_irq(uint32_t irq)
{
    REG(GICD_ICENABLER(irq/32)) = 1u << (irq & 0x1F);
}

void c_irq_dispatch(void)
{
    uint32_t iar = REG(GICC_IAR);
    uint32_t irq = iar & 0x3FF;
    if (irq < MAX_IRQ && handlers[irq]) handlers[irq]();
    REG(GICC_EOIR) = iar;   /* end of interrupt */
}
```

A note on the `GICD_IPRIORITYR` writes: each IRQ has *one byte* of priority, not one word. The array `0x400..0x4FF` is 256 bytes covering IRQ 0..255. We index by byte, which is why the cast to `volatile uint8_t *` is there.

## 15.7  Hooking up the UART1 IRQ

UART1's IRQ goes through GIC SPI ID **26**. In GIC terms that's `26 + 32 = 58` — but the *GIC's view* of the IRQ ID also adds 32 internally. Conventionally we use the SoC's labeling, which on i.MX6ULL puts UART1 at GIC ID 58. Verify in RM Chapter 3 table.

Modify `uart_init` (Chapter 12) to enable the RX-ready interrupt:

```c
void uart_irq_enable(void)
{
    REG(UART_UCR1) |= (1u << 9);   /* RRDYEN: receive ready IRQ enable */
}
```

Write a UART ISR:

```c
#include "uart.h"
#include "gic.h"

static volatile int rx_count;

static void uart1_isr(void)
{
    while (REG(UART_USR2) & USR2_RDR) {
        int c = REG(UART_URXD) & 0xFF;
        uart_putc(c);              /* echo */
        rx_count++;
    }
}

void uart1_install_isr(void)
{
    gic_register(58, uart1_isr);
    gic_enable_irq(58);
    uart_irq_enable();
}
```

And in `main()`:

```c
int main(void)
{
    /* ... clocks, ddr, etc. as before ... */
    gic_init();
    uart1_install_isr();
    irq_enable();   /* unmask CPSR.I */

    printf("Interrupt-driven echo.  Type to test.\r\n");
    for (;;) {
        asm volatile ("wfi");      /* sleep until interrupt */
    }
}
```

`wfi` (Wait For Interrupt) puts the core to sleep until an interrupt fires. After each ISR returns, we resume here, immediately re-enter `wfi`. Power-efficient idle.

The echo is now driven entirely by the UART1 ISR. The main thread literally does nothing except sleep.

## 15.8  What happens when you type a character

Pin-level: dongle TX pulls UART1_RX_DATA from idle high to start bit.

1. UART1 receiver shifts in 8 bits, raises `USR2.RDR`.
2. Because we set `UCR1.RRDYEN`, the UART asserts its interrupt line.
3. GIC distributor: IRQ 58 becomes pending.
4. Distributor: IRQ 58's priority (0xA0) ≤ CPU's running priority mask (0xFF), so it asserts IRQ to CPU.
5. CPU takes IRQ exception:
   - CPSR ↦ SPSR_irq
   - CPSR.M ↦ IRQ, CPSR.I ↦ 1
   - SP and LR banked to IRQ-mode
   - PC ↦ VBAR + 0x18 ↦ our table's IRQ slot ↦ `irq_entry`
6. `irq_entry` runs: subtracts 4 from LR, srsdb's the return frame, switches to SVC mode, pushes scratch regs, calls `c_irq_dispatch`.
7. `c_irq_dispatch` reads `GICC_IAR` (returns 58), looks up handlers[58], calls `uart1_isr`.
8. `uart1_isr` reads the character, calls `uart_putc(c)` (which polls TX), increments `rx_count`.
9. Back to dispatch; write 58 to `GICC_EOIR`.
10. Return to `irq_entry`: pop scratch regs, switch to IRQ mode, `rfeia sp!`: restores SPSR (which has SVC mode and IRQ-unmasked), PC back to whatever was running.
11. Resumed `wfi` returns; loop body runs; we hit `wfi` again.

Eleven steps. Every Linux IRQ in user space follows the same pattern.

## 15.9  Lab

1. **Build, push, type characters, see them echo.** Confirm IRQ-driven.
2. **Replace polling printf with IRQ-driven printf.** Wrap `uart_putc` in a small queue; when TX FIFO has space (`UCR1.TRDYEN`), drain queue from ISR. Now your `printf` returns immediately.
3. **Count IRQs.** Increment `rx_count` in the ISR. After 1000 characters, dump it from `main`. Confirm exact match.
4. **Try without `wfi`.** Replace `for(;;){wfi}` with `for(;;)`. Observe: same correctness, much higher idle power. (You won't *see* the power difference, but it's there.)
5. **Trigger a data abort.** From `main`, do `*(volatile uint32_t *)0x1 = 0;`. Confirm `data_handler` (currently `b .`) is hit. Add a `printf` to `data_handler` (it must run in ABT mode — easy way: just hang and let JTAG inspect; or copy the `cpsid` dance to switch to SVC).
6. **Add an SVC instruction** (`asm volatile ("svc #0")`) and observe the SVC handler is hit. This is the foundation of syscalls.

## 15.10  Pitfalls

- **Forgetting `isb` after VBAR write.** The CPU may keep using stale vectors. Always `isb`.
- **Wrong IRQ-mode return offset.** IRQ uses `-4`, prefetch abort uses `-4`, data abort uses `-8`. Mismatched: you re-execute or skip the faulting instruction.
- **`srsdb` to the wrong mode.** The encoded mode bits must match the current mode you're saving for. `0x12` = IRQ.
- **Not enabling at both distributor and CPU interface.** `GICD_CTLR.Enable` and `GICC_CTLR.Enable` must both be 1.
- **Priority mask too low.** `GICC_PMR = 0` blocks all interrupts. `GICC_PMR = 0xFF` allows all. Default mask of `0xFF` on init.
- **Forgetting EOI.** If you don't write `GICC_EOIR`, the GIC thinks the interrupt is still active and won't deliver the next instance.
- **Re-entrant ISR for a non-reentrant peripheral.** Don't enable IRQs inside an ISR unless you know what you're doing.
- **`cpsie i` in user-mode code.** PL0 can't change CPSR.I. We're always in SVC, so fine.

## 15.11  Going deeper

- **ARM IHI 0048B** — *Generic Interrupt Controller v2 Architecture Specification*. The canonical reference.
- **ARM DDI 0464** — *Cortex-A7 MPCore TRM*. The CPU side of interrupts.
- **Linux source: `arch/arm/kernel/entry-armv.S`** — the production-grade version of `irq_entry`. Read it after this chapter.
- **Linux source: `drivers/irqchip/irq-gic.c`** — kernel's GIC driver. Same registers, vastly more abstraction.
- **xv6-arm** (an educational port of xv6 to ARMv7) — has a small, readable interrupt subsystem.

> Next chapter: **Chapter 16 — Timers (EPIT and GPT).** A 1 ms tick and a free-running counter give us `udelay`, profiling, and the foundation for any scheduler we might write.
