---
chapter: 4
title: ARMv7-A and the Cortex-A7, for the MCU engineer
part: I — Foundations
estimated_pages: 22
status: draft
---

# Chapter 4 — ARMv7-A and the Cortex-A7, for the MCU engineer

> **What:** a structural understanding of the CPU core inside the i.MX6ULL, expressed as differences from Cortex-M parts you already know.
> **Why:** Linux exists *because* the A-profile cores have features the M-profile cores lack. If MMU, privilege levels, and the generic timer are vague, the kernel's boot sequence will be vague too.
> **Focus:** the three concepts that justify the entire kernel — **privilege levels**, **the MMU**, and **banked registers / exception modes**. Internalize these and most kernel design choices follow.

## 4.1  Where the Cortex-A7 sits in the ARM lineup

ARM names its cores along two axes:

- **Profile letter.** `A` for "Application" (smartphones, set-top boxes, embedded Linux), `R` for "Real-time" (storage controllers, automotive), `M` for "Microcontroller" (the Cortex-M0/M3/M4/M7/M33 you have worked with).
- **Architecture version.** v6, v7, v8, v9. The version determines the instruction set and which features are present; the core implementation determines pipeline depth, cache topology, and clock ceiling.

The i.MX6ULL contains a single **Cortex-A7** core, which implements **ARMv7-A** with the **VFPv4** floating-point unit and **NEON** SIMD. There is also a small **Cortex-M4** companion on i.MX6 *SoloX* and bigger family members — there is **no Cortex-M4** on i.MX6ULL. The single A7 is alone, running at up to **528 MHz** (commercial) or **696 MHz** (industrial). The Point Atom MINI runs the industrial bin.

Cortex-A7 is, by the standards of 2026, a slow core. It is in-order, dual-issue, with a short pipeline (8 stages). Its strength is power efficiency, silicon area, and *price*. It is also, for our purposes, **simpler to reason about** than its big-core siblings (A53/A72/A76), which is why we picked it.

## 4.2  The features Cortex-M does not have

Stand a Cortex-M7 datasheet next to a Cortex-A7 TRM and the list of "things only A has" runs to:

| Feature | Cortex-M (typical) | Cortex-A7 |
|---------|---------------------|-----------|
| Address space | Single, flat, physical | Virtual, per-context, via MMU |
| MMU | No (some have MPU) | Yes, 2-level page tables |
| Privilege levels | 2 (Privileged / Unprivileged) | 2 *practical* (PL0 / PL1) but seven modes |
| Banked registers | A few (MSP, PSP) | Yes — most registers banked per mode |
| Caches | L1 I/D on M7+, sometimes none | L1 I/D mandatory; L2 optional (no L2 on i.MX6ULL) |
| TLB | No | Yes |
| Generic timer | No (SysTick) | Yes, architected |
| Interrupt controller | NVIC (in-core, vectored) | GIC (external, prioritized, not auto-vectored) |
| Exception model | Tail-chained, automatic stacking | Modal, software-saved context |
| FPU | Optional VFP variant | VFPv4 (mandatory in i.MX6ULL) |
| SIMD | DSP extensions (limited) | NEON (64-/128-bit) |
| Atomic ops | LDREX/STREX | LDREX/STREX (same family) |
| Instruction set | Thumb-2 only | ARM + Thumb-2, sometimes ThumbEE |

Every row above explains *something* about Linux. The MMU exists so multiple processes can have private address spaces. Banked registers exist so taking an exception does not corrupt user-space state. The generic timer exists so the kernel does not have to argue with the bootloader over who programs the tick source. NEON exists so glibc's `memcpy` is fast. And so on.

## 4.3  Exception modes and banked registers

This is the most jarring difference for an engineer coming from Cortex-M, so we cover it carefully.

In Cortex-M, when an interrupt fires:

1. Hardware automatically saves R0–R3, R12, LR, PC, xPSR to the current stack.
2. Hardware loads PC from the vector table.
3. Your ISR runs.
4. `BX LR` (with the magic EXC_RETURN value in LR) tells the CPU to unstack and resume.

In Cortex-A (ARMv7-A), there is no auto-stacking. Instead, the CPU has **nine processor modes**, each with its own banked copies of certain registers. When an exception fires, the CPU switches to the appropriate mode; the new mode's banked registers shadow the user-mode ones; *your handler is responsible* for saving anything else it wants to preserve.

### The nine modes

| Mode | Abbreviation | Entered on | Banked regs (in addition to USR's R0–R14) | `M[4:0]` |
|------|-------------|-----------|-------------------------------------------|----------|
| User | USR | (normal program execution) | — | `10000` |
| FIQ | FIQ | Fast-interrupt | R8–R12, R13, R14, SPSR | `10001` |
| IRQ | IRQ | Normal interrupt | R13, R14, SPSR | `10010` |
| Supervisor | SVC | Reset, `svc` instruction | R13, R14, SPSR | `10011` |
| Monitor | MON | Secure Monitor Call (`smc`) | R13, R14, SPSR | `10110` |
| Abort | ABT | Memory/prefetch abort | R13, R14, SPSR | `10111` |
| Hyp | HYP | Hypervisor (virtualization) | R13, ELR_hyp, SPSR | `11010` |
| Undefined | UND | Undefined instruction | R13, R14, SPSR | `11011` |
| System | SYS | (privileged user-equivalent) | — | `11111` |

R13 is SP. R14 is LR. SPSR is the saved-program-status register — the snapshot of CPSR at the moment the exception was taken.

> **Cortex-A7 specifics.** All nine modes exist on every Cortex-A profile core, but their use varies. On Cortex-A7 in i.MX6ULL, **MON mode is real** and used by TrustZone-enabled secure-boot flows (Ch 62). **HYP mode is present in the architecture** but not used in our work — the i.MX6ULL is a single-core part rarely used as a hypervisor host. SYS mode is rarely entered by anyone except in low-level diagnostics. Our daily work concerns USR, SVC, IRQ, FIQ, ABT, and UND.

The full banked-register layout, columns showing per-mode visibility:

```
            USR/SYS   FIQ        IRQ      SVC      ABT      UND      MON      HYP
  R0-R7     shared    shared     shared   shared   shared   shared   shared   shared
  R8-R12    shared    R8-12_fiq  shared   shared   shared   shared   shared   shared
  R13(SP)   sp_usr    sp_fiq     sp_irq   sp_svc   sp_abt   sp_und   sp_mon   sp_hyp
  R14(LR)   lr_usr    lr_fiq     lr_irq   lr_svc   lr_abt   lr_und   lr_mon   lr_usr*
  R15(PC)   shared
  CPSR      shared
  SPSR      —         SPSR_fiq   SPSR_irq SPSR_svc SPSR_abt SPSR_und SPSR_mon SPSR_hyp + ELR_hyp
```

`*` HYP mode shares the LR with USR (uses ELR_hyp instead for exception-return).

Total physical register count exposed by Cortex-A7: **34 general-purpose**, **8 status (CPSR + 7×SPSR)**, plus ELR_hyp — 43 registers, of which at most 18 are visible from any single mode.

In other words, each exception mode has **its own stack pointer** and **its own link register**. When an IRQ fires, the CPU does not push anything; it simply switches to IRQ mode, and now `SP` refers to a different physical register than it did a microsecond ago. The IRQ handler runs with that IRQ-mode stack. To return, it copies `SPSR_irq` back into CPSR and `LR_irq` back into PC.

### What this means in practice

The first time you write an A-profile exception handler (Chapter 15), it is sobering:

```asm
irq_entry:
    sub     lr, lr, #4          @ adjust LR_irq (taken from PC+4 by hardware)
    srsdb   sp!, #0x12          @ save LR_irq, SPSR_irq to IRQ stack
    cpsid   if, #0x13           @ switch to SVC mode, IRQ+FIQ disabled
    push    {r0-r12, lr}        @ now save everything we may clobber
    bl      c_irq_handler
    pop     {r0-r12, lr}
    rfeia   sp!                 @ return from exception
```

The Cortex-M equivalent is nothing — the hardware did it for you. The A-profile design trades hardware simplicity (cheaper silicon) for software complexity (more careful entry/exit code). Linux's `entry-armv.S` is one large fortress of code dedicated to exactly this.

### PL0 vs PL1 vs PL2

Across the nine modes, ARM defines three **privilege levels**:

- **PL0** (unprivileged, user-mode equivalent) — only USR mode. The mode applications run in.
- **PL1** (privileged) — most modes: SVC, IRQ, FIQ, ABT, UND, SYS. The level the kernel runs at.
- **PL2** (hypervisor) — only HYP mode. Above PL1; allows trapping of PL1 actions.

A separate **Security state** (Normal World / Secure World) is orthogonal to PL: MON mode straddles the boundary.

Every system register, every cache maintenance instruction, every CP15 access requires at least PL1.

Linux runs user space in USR mode (PL0) and the kernel in SVC mode (PL1). The transition between them — what the kernel calls "userspace ↔ kernelspace" — is, mechanically, a mode switch triggered by an `svc` instruction or an interrupt.

> **Focus.** When you read in a Linux kernel book that "syscall switches to kernel mode", what that *means*, on this hardware, is: an `svc` instruction triggered a Supervisor Call exception, which moved the CPU from USR mode (PL0) to SVC mode (PL1), banked LR and SP swapped to their SVC-mode copies, and the exception handler began running with full privileges. There is nothing magical about it. It is a normal exception, same family as IRQ.

## 4.4  The CPSR / SPSR program status registers

CPSR (Current Program Status Register) is the A-profile equivalent of M-profile's xPSR, but more is in it:

```
 31 30 29 28 27 ...  9  8  7  6  5  4  3  2  1  0
 N  Z  C  V  Q       E  A  I  F  T  M4 M3 M2 M1 M0
```

- **N, Z, C, V** — condition flags (the same as M-profile: negative, zero, carry, overflow)
- **Q** — saturation flag (ARMv5TE-J and later; set by saturating arithmetic instructions)
- **IT[7:0]** (split bits 26:25 + 15:10) — IF-THEN block state for Thumb-2 conditional execution
- **J** (bit 24), **T** (bit 5) — together select the active instruction set: ARM (J=0,T=0), Thumb (J=0,T=1), ThumbEE (J=1,T=1), Jazelle (J=1,T=0)
- **GE[3:0]** (bits 19:16) — SIMD greater-or-equal flags, set by NEON parallel comparisons
- **E** — endianness (set per-load/store; ARMv7-A supports mixed)
- **A** — asynchronous abort mask
- **I** — IRQ mask (`I=1` disables IRQs)
- **F** — FIQ mask
- **T** — Thumb state (`T=1` means executing in Thumb)
- **M[4:0]** — current processor mode (encoding for USR/SVC/IRQ/...)

When an exception is taken, CPSR snapshots into SPSR_<mode>, and the new mode's M[4:0] gets written to CPSR. The handler can `mrs Rn, spsr` to read it; `cps` instructions can change mode and mask bits in-place.

Linux's preemption logic, IRQ masking, and "is this code running in user or kernel context" predicates all reduce, at the bottom, to bits in CPSR.

## 4.5  Memory model and the MMU

The Cortex-A7 has a **2-stage MMU** capability, but on a single-core, non-virtualized system like ours, we use only **stage 1**: translation from virtual addresses to physical addresses.

### Translation table formats

ARMv7-A supports two translation table formats:

- **Short descriptor (32-bit physical addresses, 2-level tables).** What we will use.
- **Long descriptor (LPAE, 40-bit physical, 3-level tables).** Required for >4 GB of physical memory. The i.MX6ULL has at most 512 MiB; we don't need LPAE.

The short-descriptor walk:

```
  Virtual address (32-bit):
  ┌─────────────────────┬────────────┬──────────────────┐
  │ 31              20  │ 19      12 │ 11             0 │
  │  Level-1 index      │ Level-2 idx│  Page offset     │
  └──┬──────────────────┴──┬─────────┴──────────────────┘
     │                      │
     ▼                      ▼
   TTBR0/1 → L1 table   L2 table       Physical page
   (16 KB, 4096 entries)(1 KB, 256 ent) (4 KB or 1 MB section)
```

Each Level-1 entry can:

- Point to a Level-2 table (resolves a 1 MB region in 4 KB pages).
- Be a **1 MB "section"** directly (no Level-2 walk needed; saves a memory access).
- Be a **16 MB "supersection"** (less common).

Each L1 / L2 entry also carries:

- **AP** (Access Permissions): read/write/none, separately for PL0 and PL1.
- **TEX, C, B** (memory attributes): cacheable, bufferable, shareable, device vs normal.
- **Domain** (legacy access-control, mostly set to "client" and ignored these days).
- **nG** (non-global, for ASID-tagged TLB entries).
- **XN** (eXecute Never): bit that makes the page non-executable.

The **TLB** caches recent walks. There is also an **ASID** (Address Space ID, 8 bits) that tags TLB entries so context switches do not need a full TLB flush.

We will build, by hand, a minimal L1-only page table in Chapter 17. Once you have done that exercise, every kernel memory-management bug will be ten times easier to think about.

### What the kernel does with this

Linux on ARMv7-A:

- Uses **TTBR0** for user-space (per-process) and **TTBR1** for kernel-space.
- Splits the 4 GB virtual address space into user (0x00000000 – 0xBFFFFFFF) and kernel (0xC0000000 – 0xFFFFFFFF) by default, controllable via `CONFIG_PAGE_OFFSET`.
- Maps the kernel image with a fixed offset (PHYS_OFFSET to PAGE_OFFSET) so virtual-to-physical translation is a single subtraction for kernel-space pointers.

The split is why a 32-bit Linux user process can address at most ~3 GB.

## 4.6  Caches

Cortex-A7 has separate **L1 instruction** and **L1 data** caches (32 KB each, 4-way, 64-byte lines on i.MX6ULL). There is no L2 on this part (no PL310 controller is integrated).

Two things about A-profile caches that bite Cortex-M-trained engineers:

1. **Caches are off at reset.** Just like Cortex-M, but unlike Cortex-M, you cannot easily run usefully fast without them. Enabling caches is one of the first things any A-profile bootloader does after MMU setup.
2. **Caches are VIPT for L1-D** (Virtually Indexed, Physically Tagged) on Cortex-A7. The implication is that two virtual addresses mapping to the same physical address can cause aliasing if cache lines are managed by VA. The kernel knows about this and inserts flushes; you only care if you write your own DMA-coherent code (Chapter 51).

Cache maintenance is done via **CP15** coprocessor instructions:

- `dc ivac, Rt` — invalidate D-cache by VA
- `dc cvac, Rt` — clean (write back) D-cache by VA
- `dc civac, Rt` — clean + invalidate by VA
- `ic ialluis` — invalidate I-cache, inner shareable
- Set/way variants for full-cache flushes

You will write a tiny cache-flush primitive in Chapter 17. Linux's `arch/arm/mm/cache-v7.S` is the full version.

## 4.7  The generic timer

Cortex-A7 includes the **ARMv7 generic timer**: an architected, always-running counter with comparator-based interrupts. It exists at the CPU level — every CPU sees the same counter — and it survives sleep states.

Key registers (CP15 access):

- `CNTFRQ` — counter frequency (Hz). Software writes this once at boot to inform the rest of the system.
- `CNTPCT` — current counter value (64-bit physical counter).
- `CNTP_CVAL` — comparator value; the timer fires when CNTPCT ≥ CNTP_CVAL.
- `CNTP_CTL` — enable + interrupt mask + status.

The generic timer is the kernel's preferred tick source on ARMv7-A. Linux's `arch_timer` driver targets it directly. The i.MX6ULL also has legacy GPT and EPIT timer blocks; we use those in bare-metal Chapter 16 because they are simpler to demonstrate, then switch to the generic timer when Linux takes over.

> **Contrast with SysTick:** SysTick is a 24-bit down-counter, per-CPU, inside the M-profile core. The ARMv7-A generic timer is a 64-bit counter, per-CPU but globally synchronized, accessed via CP15. Both serve the same purpose (kernel/RTOS tick); the A-profile version is what enables coherent multi-CPU time on big systems.

## 4.8  The Generic Interrupt Controller (GIC)

The Cortex-M NVIC was inside the core. The A-profile equivalent, the **GIC**, is outside the core. The i.MX6ULL integrates a **GIC-400** (an implementation of GIC v2).

GICv2 has two parts:

- **Distributor** (`GICD_*` registers, base `0x00A01000` on i.MX6ULL): one per system; arbitrates which interrupt goes to which CPU, sets priorities, masks, and trigger types (level/edge).
- **CPU Interface** (`GICC_*` registers, base `0x00A02000`): one per CPU; the core reads acknowledgement and writes end-of-interrupt here.

Three flavors of interrupt:

| Type | ID range | Purpose |
|------|----------|---------|
| SGI — Software-Generated | 0–15 | One CPU pokes another (used for IPIs in SMP). |
| PPI — Private Peripheral | 16–31 | Per-CPU peripherals: the generic timer interrupt is a PPI. |
| SPI — Shared Peripheral | 32–1019 | Everything else: UART, I²C, GPIO, FEC, USB, ... |

The i.MX6ULL maps SoC peripheral interrupts to SPI IDs. The mapping is in the reference manual's Chapter 3, "Interrupts and DMA Events". For example, `UART1` is SPI 26 (which the GIC sees as ID 26+32 = 58).

The GIC does **not** auto-vector. When the CPU takes an IRQ exception, it does not know which interrupt fired. The handler must read `GICC_IAR` to get the current interrupt's ID, dispatch on that ID, and write `GICC_EOIR` when done. This is the loop your IRQ handler must run.

## 4.9  Atomics, barriers, and memory ordering

ARMv7-A is **weakly ordered**. Stores and loads can be reordered by the CPU. Linux assumes this and inserts barriers where necessary. Two facts to keep:

- `dsb` (Data Synchronization Barrier) — waits for outstanding memory accesses to complete.
- `dmb` (Data Memory Barrier) — orders accesses but does not necessarily wait.
- `isb` (Instruction Synchronization Barrier) — flushes the pipeline; required after changing CPSR, system registers, or page tables.

The atomic primitive is **LDREX/STREX**:

```asm
retry:
    ldrex   r1, [r0]      @ load-exclusive
    add     r1, r1, #1
    strex   r2, r1, [r0]  @ store-exclusive; r2=0 on success
    cmp     r2, #0
    bne     retry
```

Cortex-M has the same instructions; the surprise on A-profile is that you must also use the right barrier afterwards if you need ordering against unrelated memory.

## 4.10  NEON and VFP

VFPv4 gives you 32 double-precision FP registers and the usual IEEE-754 operations. NEON shares the same register file (viewed as 16 × 128-bit Q registers, or 32 × 64-bit D registers) and adds packed integer/float SIMD.

For kernel code, NEON/VFP are **disabled by default**. Touching them in kernel context requires `kernel_neon_begin()` / `kernel_neon_end()` — failing to do so corrupts user-space FP state on context switch. Most drivers never need NEON; some crypto and codec paths do.

For user space, NEON is just there — `libc`'s `memcpy`, `memset`, `strcmp` use it. You will see it in `objdump -d` of any glibc binary.

## 4.11  Differences between Cortex-A7 and the bigger A-cores

For completeness, since some of you may have read about Cortex-A53 or A72 elsewhere:

| Feature | Cortex-A7 | Cortex-A53 | Cortex-A72 |
|---------|-----------|------------|------------|
| ISA | ARMv7-A (32-bit only) | ARMv8-A (32+64-bit) | ARMv8-A |
| Pipeline | In-order, 8 stages | In-order, 8 stages | Out-of-order, 15 stages |
| L1 D-cache | 32 KB VIPT | 32 KB PIPT | 32 KB PIPT |
| Generic timer | Yes (CP15) | Yes (system reg) | Yes (system reg) |
| GIC version | GICv2 | GICv2/v3 | GICv2/v3 |

The most important difference for our purposes is ISA: Cortex-A7 is 32-bit only. Everything we write — assembly, page tables, registers — is 32-bit. If you later move to AArch64 (Cortex-A53+ in 64-bit mode), the *concepts* transfer almost cleanly, but every system register name and bit layout changes.

## 4.12  Lab

No code yet (we have not installed our bare-metal toolchain in earnest). The lab here is a research exercise — by the end of it you should be able to find any piece of A-profile architectural information quickly.

1. From the **ARM Architecture Reference Manual, ARMv7-A and ARMv7-R edition** (ARM DDI 0406), locate:
   - Section B1.3 — Processor modes
   - Section B3.5 — Short-descriptor translation table
   - Section B4.1 — Generic timer
2. From the **Cortex-A7 MPCore Technical Reference Manual** (ARM DDI 0464), locate:
   - Chapter 6 — L1 memory system (cache sizes, line length)
   - Appendix B — CP15 system registers, alphabetical
3. From the **i.MX 6ULL Applications Processor Reference Manual** (IMX6ULLRM), locate:
   - Chapter 3 — Interrupts and DMA Events (SPI ID table)
   - Chapter 2 — System Boot (so you are ready for Chapter 7 of this book)

Bookmark each. We will refer to them often.

## 4.13  Pitfalls

- **Assuming A-profile exceptions auto-stack like M-profile.** They do not. Forget this once and your IRQ handler will trash USR-mode registers.
- **Forgetting `isb` after writing system registers.** Changes to TTBR, SCTLR, VBAR do not take effect until you barrier and the pipeline refills. Symptom: code "should work" but doesn't, until you add an unrelated `printk` (which happens to insert a barrier).
- **Thinking the GIC is in the core.** It is a separate memory-mapped block. You configure it via loads/stores to MMIO, not CP15.
- **Mixing up SPI (Shared Peripheral Interrupt) with SPI (Serial Peripheral Interface bus).** Context disambiguates, but every paragraph that mentions both is hard to read. This book will say "GIC SPI" or "SPI bus" whenever it could be ambiguous.
- **Cache flush by set/way for "flush everything"** — common on Cortex-M code carried over; on A-profile, set/way flushes are *not* broadcast and miss aliased lines. Use the VA-based ops for correctness; only the initial cold-boot all-cache flush should use set/way.

## 4.14  Going deeper

- ARM DDI 0406 — *ARM Architecture Reference Manual, ARMv7-A/R*. The bible.
- ARM DDI 0464 — *Cortex-A7 MPCore Technical Reference Manual*. The implementation specifics.
- ARM IHI 0048B — *ARM Generic Interrupt Controller v2 Architecture Specification*.
- ARM DEN 0013 — *Cortex-A Series Programmer's Guide*. The friendliest tutorial-style overview.
- LWN: "An introduction to the ARM Generic Interrupt Controller" (2014).
- Linux source: `arch/arm/include/asm/{system,memory,page,pgtable}.h`, `arch/arm/mm/proc-v7.S`, `arch/arm/kernel/entry-armv.S`.

> Next chapter: **Chapter 5 — A tour of the i.MX6ULL SoC.** We zoom out from the core to the chip around it.
