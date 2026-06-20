# Chapter 4: ARMv7-A and the Cortex-A7, for the MCU engineer

> **What:** a structural understanding of the CPU core inside the i.MX6ULL, expressed as differences from Cortex-M parts you already know.
>
> **Why:** Linux exists *because* the A-profile cores have features the M-profile cores lack. If MMU, privilege levels, and the generic timer are unclear, the kernel's boot sequence will be unclear too.
>
> **Focus:** the three concepts that justify the entire kernel: privilege levels, the MMU, and banked registers / exception modes. Get these and most kernel design choices follow.


## 4.1  Where the Cortex-A7 sits in the ARM lineup

ARM names its cores along two axes:

- **Profile letter.** `A` for "Application" (smartphones, set-top boxes, embedded Linux), `R` for "Real-time" (storage controllers, automotive), `M` for "Microcontroller" (the Cortex-M0/M3/M4/M7/M33 you have worked with).
- **Architecture version.** v6, v7, v8, v9. The version determines the instruction set and which features are present. The core implementation determines pipeline depth, cache topology, and clock ceiling.

The i.MX6ULL has one Cortex-A7 core with VFPv4 and NEON. Bigger i.MX6 parts, such as SoloX, also carry a Cortex-M4 companion. The i.MX6ULL is A7 only. The silicon's **architectural maximum** is around **800 MHz** for the industrial bin or around **900 MHz** for the consumer/commercial bin, per the i.MX6ULL reference manual. Most BSPs, including the Point Atom factory image, clock the part at **528 MHz** or **696 MHz** to stay in a more comfortable voltage, power, and thermal envelope. A **BSP** is a Board Support Package: the vendor patches, configs, bootloader files, and scripts needed to boot one board. We run at the BSP-default **696 MHz** throughout this book.

The Cortex-A7 is an in-order, dual-issue core with an 8-stage pipeline. It is slower than newer Cortex-A cores, but uses less silicon area and power. Its simpler design also makes it suitable for learning ARMv7-A.

## 4.2  The features Cortex-M does not have

Stand a Cortex-M7 datasheet next to a Cortex-A7 TRM and the list of "things only A has" runs to:

| Feature | Cortex-M (typical) | Cortex-A7 |
|---------|---------------------|-----------|
| Address space | Single, flat, physical | Virtual, per-context, via MMU |
| MMU | No (some have MPU) | Yes, 2-level page tables |
| Privilege levels | 2 (Privileged / Unprivileged) | 2 *practical* levels, PL0 and PL1, plus seven modes |
| Banked registers | A few (MSP, PSP) | Selected registers are banked in exception modes |
| Caches | L1 I/D on M7+, sometimes none | L1 I/D mandatory. L2 is integrated inside the Cortex-A7 MPCore platform (128 KB on i.MX6ULL), with no separate PL310 controller |
| TLB (Translation Lookaside Buffer, the MMU's address-translation cache) | No | Yes |
| Generic timer | No (SysTick) | Yes, architected |
| Interrupt controller | NVIC (in-core, vectored) | **GIC**, an external Generic Interrupt Controller block. Prioritized, not auto-vectored |
| Exception model | Tail-chained, automatic stacking | Mode switch, software-saved context |
| FPU | Optional VFP variant | VFPv4 (mandatory in i.MX6ULL) |
| SIMD | DSP extensions (limited) | NEON (64-/128-bit) |
| Atomic ops | LDREX/STREX on M7 onwards. M0/M0+ have none | LDREX/STREX (same family) |
| Instruction set | Thumb-2 only | ARM + Thumb-2, sometimes ThumbEE |

Each feature supports part of Linux. The MMU gives each process a private address space. Banked registers preserve selected state across exceptions. The generic timer provides a standard kernel time source. NEON accelerates operations such as `memcpy`.

## 4.3  Exception modes and banked registers

This is one of the largest differences for an engineer coming from Cortex-M, so we cover it carefully.

In Cortex-M, when an interrupt fires:

1. Hardware automatically saves R0-R3, R12, LR, PC, and xPSR to the current stack.
2. Hardware loads PC from the vector table.
3. Your ISR runs.
4. `BX LR` (with the special EXC_RETURN value in LR) tells the CPU to unstack and resume.

In Cortex-A (ARMv7-A) there is no auto-stacking. The CPU has **nine processor modes**, each with its own banked copies of certain registers. When an exception fires, the CPU switches to the right mode. The banked registers for the new mode become the registers that instructions see. Your handler must save anything else it wants to keep.

### The registers you are looking at

Before the mode table, review the core integer and status registers. MMU, timer, cache, and NEON/VFP registers appear later when needed. Ordinary code uses `r0` through `r15` plus `CPSR`. Each exception mode also has an `SPSR`. Some names, including `sp` and `lr`, refer to different physical registers in different modes.

| Register | Common alias | What it does | Beginner note |
|----------|--------------|--------------|---------------|
| `r0`-`r3` | argument / result registers | Hold the first four integer function arguments and return values under the ARM calling convention. | Exception handlers must save them before calling C if they need the interrupted code's values later. |
| `r4`-`r8` | general saved registers | General-purpose registers that C functions normally preserve for their caller. | `r8` is ordinary in most modes, but FIQ mode has its own banked `r8_fiq`. |
| `r9` | platform register | ABI-defined register. Some systems use it for a static base, thread pointer, or other platform role. | Treat it as "do not assume" in hand-written assembly that calls C. |
| `r10` | `sl` | General saved register. Some older ABIs used it as a stack limit. | Usually another callee-saved register in Linux code. |
| `r11` | `fp` | Frame pointer when frame pointers are enabled. | Useful when reading backtraces or compiler-generated assembly. |
| `r12` | `ip` | Scratch register used during function calls. Linker-generated branch stubs may use it. | Caller-saved. Do not expect it to survive a function call. FIQ also has `r12_fiq`. |
| `r13` | `sp` | Stack pointer. Points at the current mode's stack. | Banked in exception modes, so `sp_irq` and `sp_svc` are different physical registers. |
| `r14` | `lr` | Link register. Holds a subroutine return address, or an exception return address after an exception. | Banked in most exception modes, so `lr_irq` is not the same as user `lr`. |
| `r15` | `pc` | Program counter, the address of the instruction stream. | Writing to `pc` causes a branch. Exception return often restores a value into `pc`. |
| `CPSR` | current status | Holds condition flags, interrupt masks, Thumb/ARM state, and current processor mode. | The CPU changes CPSR when it enters an exception. |
| `SPSR_<mode>` | saved status | Snapshot of CPSR taken when an exception entered that mode. | Used on exception return to restore the old mode, flags, and interrupt-mask state. User/System mode do not have an SPSR. |
| `ELR_hyp` | hypervisor exception link | Return address used by HYP mode. | HYP is special: it uses `ELR_hyp` instead of a banked `lr_hyp` for exception return. |

Now turn that into the table you actually need while reading exception code: columns are modes, rows are register names.

On Cortex-M, the mode story is small:

| Register | Thread mode | Handler mode |
|----------|-------------|--------------|
| `r0`-`r12` | Same physical registers. | Same physical registers, exception entry stacks `r0`-`r3` and `r12` automatically. |
| `r13` / `sp` | `MSP` or `PSP`, selected by `CONTROL.SPSEL`. | `MSP`. |
| `r14` / `lr` | Normal function return address. | `EXC_RETURN`, the special value used by `BX LR` to leave the exception. |
| `r15` / `pc` | Current instruction stream. | Handler instruction stream loaded from the vector table. |
| status | Active `xPSR`. | Active `xPSR`. The previous `xPSR` is stacked automatically. |

On Cortex-M, the general-purpose registers are shared between Thread and Handler mode. The big convenience is that hardware automatically saves the interrupted context on exception entry and restores it on exception return. The one stack-pointer wrinkle is that Thread mode may use `MSP` or `PSP`, while Handler mode always uses `MSP`.

On Cortex-A, the mode story is the real map:

| Register | USR | SYS | FIQ | IRQ | SVC | ABT | UND | MON | HYP |
|----------|-----|-----|-----|-----|-----|-----|-----|-----|-----|
| `r0`-`r7` | shared | shared | shared | shared | shared | shared | shared | shared | shared |
| `r8`-`r12` | shared | shared | `r8_fiq`-`r12_fiq` | shared | shared | shared | shared | shared | shared |
| `r13` / `sp` | `sp_usr` | `sp_usr` | `sp_fiq` | `sp_irq` | `sp_svc` | `sp_abt` | `sp_und` | `sp_mon` | `sp_hyp` |
| `r14` / `lr` | `lr_usr` | `lr_usr` | `lr_fiq` | `lr_irq` | `lr_svc` | `lr_abt` | `lr_und` | `lr_mon` | `lr_usr`* |
| `r15` / `pc` | shared | shared | shared | shared | shared | shared | shared | shared | shared |
| `CPSR` | shared | shared | shared | shared | shared | shared | shared | shared | shared |
| `SPSR` | none | none | `SPSR_fiq` | `SPSR_irq` | `SPSR_svc` | `SPSR_abt` | `SPSR_und` | `SPSR_mon` | `SPSR_hyp` |
| HYP return address | none | none | none | none | none | none | none | none | `ELR_hyp` |

`shared` means the same physical register is visible in that mode. For `r8`-`r12`, FIQ uses its own banked copies while the other modes share the ordinary registers. A suffix such as `_irq` means that mode has its own banked physical register. HYP mode shares `lr_usr` and uses `ELR_hyp` for exception return, as marked by `*` in the table.

### The nine modes

| Mode | Abbreviation | Entered on | Banked regs | `M[4:0]` |
|------|-------------|-----------|-------------------------------------------|----------|
| User | USR | (normal program execution) | none | `10000` |
| FIQ | FIQ | Fast interrupt | R8-R12, R13, R14, SPSR | `10001` |
| IRQ | IRQ | Normal interrupt | R13, R14, SPSR | `10010` |
| Supervisor | SVC | Reset, `svc` instruction | R13, R14, SPSR | `10011` |
| Monitor | MON | Secure Monitor Call (`smc`) | R13, R14, SPSR | `10110` |
| Abort | ABT | Memory/prefetch abort | R13, R14, SPSR | `10111` |
| Hyp | HYP | Hypervisor (virtualization) | R13, ELR_hyp, SPSR | `11010` |
| Undefined | UND | Undefined instruction | R13, R14, SPSR | `11011` |
| System | SYS | Privileged mode using the user register view | none | `11111` |

R13 is SP. R14 is LR. SPSR is the saved-program-status register. It holds a snapshot of CPSR at the moment the exception was taken.

> **Cortex-A7 specifics.** All nine modes exist on every Cortex-A profile core, but their use varies. On Cortex-A7 in i.MX6ULL, **MON mode** is used by TrustZone-enabled secure-boot flows (Chapter 124). **HYP mode** is on the i.MX6ULL Cortex-A7, but it is not part of the required bring-up path. We return to it in Part IX for QEMU, Xen, and mixed-criticality experiments. The i.MX6ULL is a single-core part, so it is useful for learning HYP-mode mechanics but not a strong virtualization platform. SYS mode is rarely entered by anyone except in low-level diagnostics. Our daily work concerns USR, SVC, IRQ, FIQ, ABT, and UND.

Total physical register count exposed by Cortex-A7: **34 general-purpose**, **8 status (CPSR + 7×SPSR)**, plus `ELR_hyp`. That is 43 registers. A normal non-HYP mode sees at most 18 at once: `r0`-`r15`, `CPSR`, and its `SPSR`. HYP sees `ELR_hyp` as its extra exception-return address.

Each exception mode has **its own stack pointer** and **its own link register**. When an IRQ occurs, the CPU does not push registers automatically. It switches to IRQ mode, where `sp` and `lr` refer to the IRQ-mode register bank. The handler saves any additional state it needs. Exception return restores CPSR from `SPSR_irq` and resumes at the address derived from `lr_irq`.

### What this means in practice

Put the two worlds side by side:

| Moment | Cortex-M | Cortex-A / ARMv7-A |
|--------|----------|--------------------|
| Interrupt accepted | Hardware picks the vector and starts exception entry. | Hardware switches to IRQ mode and branches through the exception vector. |
| Registers saved automatically | `r0`-`r3`, `r12`, `lr`, `pc`, `xPSR` are pushed to the current stack. | Nothing is pushed. `CPSR` is copied to `SPSR_irq`, and the return address goes into `LR_irq`. |
| Stack pointer used | The active MSP or PSP. | The banked `sp_irq`, which must already point at a valid IRQ stack. |
| What `lr` means inside the handler | A special `EXC_RETURN` value that tells the CPU how to unstack. | The banked `LR_irq`, holding an exception return address that often needs an offset adjustment. |
| Handler prologue | Often no assembly is needed, a C ISR can start immediately. | Assembly must save enough state before calling C. |
| Return | `BX LR` triggers hardware unstacking. | Software restores the saved state, copies `SPSR_irq` back to `CPSR`, and restores the return PC. |

The Cortex-M equivalent is mostly hidden inside the core. A-profile gives the kernel more control, but it also makes entry/exit code part of the operating system. Linux's `entry-armv.S` is the file that handles all of it.

### PL0 vs PL1 vs PL2

Across the nine modes, ARM defines three **privilege levels**:

- **PL0** (unprivileged, like Cortex-M unprivileged Thread mode): only USR mode. This is the mode applications run in.
- **PL1** (privileged): most modes, including SVC, IRQ, FIQ, ABT, UND, and SYS. This is the level the kernel runs at.
- **PL2** (hypervisor): only HYP mode. It can intercept selected PL1 operations and transfer control to the hypervisor.

ARM TrustZone adds a separate **Security state**: Normal World or Secure World. This is independent of PL0/PL1/PL2. MON mode is the mode used to switch between the two worlds.

Every system register, every cache maintenance instruction, every CP15 access requires at least PL1.

**CP15** is ARMv7-A's system-control register access path. Despite the name, it is not a separate chip you wire up. It is how privileged code controls the core: MMU enable bits (`SCTLR`), page-table base registers (`TTBR0` / `TTBR1`), the exception-vector base (`VBAR`), cache/TLB maintenance operations, and the generic timer registers. ARM instructions such as `mrc` and `mcr` read and write CP15 registers. On AArch64, the same idea becomes named system registers instead of "CP15."

Linux runs user space in USR mode (PL0) and the kernel in SVC mode (PL1). The transition between them, what the kernel calls "userspace ↔ kernelspace", is a hardware mode switch triggered by an `svc` instruction or an interrupt.

HYP mode is the extra layer used by a hypervisor. A guest kernel runs as if it controls PL1, but sensitive actions can be redirected to PL2. The hypervisor can then decide whether to allow the action, emulate it, or stop the guest. The matching instruction is `hvc` (Hypervisor Call), similar to `svc` but for calls into the hypervisor.

Do not confuse HYP mode with Monitor mode:

- **HYP / PL2:** virtualizes Normal World operating systems.
- **MON / Monitor mode:** switches between Secure World and Normal World for TrustZone.

Part IX uses this distinction in real labs: Xen uses HYP mode for guests, while OP-TEE in Chapter 124 uses Monitor/Secure-world mechanisms.

> **Focus.** When a Linux kernel book says "syscall switches to kernel mode", here is what happens on this hardware. An `svc` instruction triggers a Supervisor Call exception. The CPU moves from USR mode (PL0) to SVC mode (PL1). LR and SP swap to their SVC-mode copies, and the handler runs with full privileges. It is a normal exception, same family as IRQ.

## 4.4  The CPSR / SPSR program status registers

CPSR (Current Program Status Register) is the A-profile equivalent of M-profile's xPSR, but more is in it:

```
 31 30 29 28 27 ...  9  8  7  6  5  4  3  2  1  0
 N  Z  C  V  Q       E  A  I  F  T  M4 M3 M2 M1 M0
```

- **N, Z, C, V:** condition flags (the same as M-profile: negative, zero, carry, overflow)
- **Q:** saturation flag, set by saturating arithmetic instructions
- **IT[7:0]** (split bits 26:25 + 15:10): IF-THEN block state for Thumb-2 conditional execution
- **J** (bit 24), **T** (bit 5): together select the active instruction set: ARM (J=0,T=0), Thumb (J=0,T=1), ThumbEE (J=1,T=1), Jazelle (J=1,T=0)
- **GE[3:0]** (bits 19:16): SIMD greater-or-equal flags, set by NEON parallel comparisons
- **E:** endianness. ARMv7-A can select endianness per load/store
- **A:** asynchronous abort mask
- **I:** IRQ mask (`I=1` disables IRQs)
- **F:** FIQ mask
- **T:** Thumb state (`T=1` means executing in Thumb)
- **M[4:0]:** current processor mode (encoding for USR/SVC/IRQ/...)

When an exception is taken, the CPU copies CPSR into `SPSR_<mode>` and writes the new mode into CPSR.M[4:0]. The handler can use `mrs Rn, spsr` to read the saved value. A `cps` instruction can change the current mode and interrupt-mask bits.

Linux uses CPSR fields when managing preemption, interrupt masking, and transitions between user and kernel modes.

## 4.5  Memory model and the MMU

The Cortex-A7 has a **2-stage MMU** capability, but on a single-core, non-virtualized system like ours, we use only **stage 1**: translation from virtual addresses to physical addresses.

### Translation table formats

ARMv7-A supports two translation table formats:

- **Short descriptor (32-bit physical addresses, 2-level tables).** What we will use.
- **Long descriptor (LPAE, 40-bit physical, 3-level tables).** Used when a system needs larger physical addresses or LPAE features. Our board has at most 512 MiB of DRAM, so this book does not need LPAE.

The short-descriptor translation steps:

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
- Be a **1 MB "section"** directly (no Level-2 lookup needed, saving a memory access).
- Be a **16 MB "supersection"** (less common).

Each L1 / L2 entry also carries:

- **AP** (Access Permissions): read/write/none, separately for PL0 and PL1.
- **TEX, C, B** (memory attributes): cacheable, bufferable, shareable, device vs normal.
- **Domain** (legacy access-control, mostly set to "client" and ignored these days).
- **nG** (non-global, for ASID-tagged TLB entries).
- **XN** (eXecute Never): bit that makes the page non-executable.

The **TLB** caches recent address translations. There is also an **ASID** (Address Space ID, 8 bits) that tags TLB entries so context switches do not need a full TLB flush.

We will build, by hand, a minimal L1-only page table in Chapter 17. Once you have done that exercise, kernel memory bugs are much easier to read.

### What the kernel does with this

Linux on ARMv7-A:

- Uses **TTBR0** for user-space (per-process) and **TTBR1** for kernel-space.
- Splits the 4 GB virtual address space into a user range (`0x00000000`-`0xBFFFFFFF`) and kernel range (`0xC0000000`-`0xFFFFFFFF`) by default. `CONFIG_PAGE_OFFSET` controls this split.
- Maps the kernel image with a fixed offset (PHYS_OFFSET to PAGE_OFFSET) so virtual-to-physical translation is a single subtraction for kernel-space pointers.

The split is why a 32-bit Linux user process can address at most ~3 GB.

## 4.6  Caches

Cortex-A7 has separate **L1 instruction** and **L1 data** caches (32 KB each, 4-way, 64-byte lines on i.MX6ULL). The Cortex-A7 MPCore platform also contains an **integrated 128 KB unified L2** cache (i.MX6ULL Reference Manual, §11, "L2 cache"). The i.MX6ULL does *not* have an external L2 controller. Earlier i.MX6 family members, such as i.MX6Q, integrate ARM's separate **PL310** controller. Here L2 is built into the MPCore block instead.

Two A-profile cache properties are important here:

1. **Caches are off at reset.** Same as Cortex-M. The difference is that on A-profile you cannot get useful performance without them. Enabling caches is one of the first things any A-profile bootloader does after MMU setup.
2. **L1 caches are PIPT on Cortex-A7** (Physically Indexed, Physically Tagged, per the Cortex-A7 MPCore TRM, ARM DDI 0464). PIPT avoids virtual-address aliases for normal cache lines. Cache maintenance is still required when the CPU shares buffers with DMA devices, as explained in Chapter 51.

ARMv7-A performs cache maintenance through **CP15** operations. The assembly uses `mcr` with an operation-specific CP15 encoding:

| Operation | ARMv7-A form | Architectural name |
|-----------|--------------|--------------------|
| Invalidate D-cache line by virtual address | `mcr p15, 0, Rt, c7, c6, 1` | `DCIMVAC` |
| Clean D-cache line by virtual address | `mcr p15, 0, Rt, c7, c10, 1` | `DCCMVAC` |
| Clean and invalidate D-cache line by virtual address | `mcr p15, 0, Rt, c7, c14, 1` | `DCCIMVAC` |
| Invalidate all instruction caches to PoU | `mcr p15, 0, Rt, c7, c5, 0` | `ICIALLU` |

Set/way operations are also available for whole-cache maintenance during early boot.

You will write a tiny cache-flush primitive in Chapter 17. Linux's `arch/arm/mm/cache-v7.S` is the full version.

## 4.7  The generic timer

Cortex-A7 includes the **ARMv7 generic timer**: an architected, always-running counter with comparator-based interrupts. It exists at the CPU level. Every CPU sees the same counter, and it survives sleep states.

Key registers (CP15 access):

- `CNTFRQ`: counter frequency (Hz). Software writes this once at boot to inform the rest of the system.
- `CNTPCT`: current counter value (64-bit physical counter).
- `CNTP_CVAL`: comparator value. The timer fires when CNTPCT >= CNTP_CVAL.
- `CNTP_CTL`: enable + interrupt mask + status.

The generic timer is the kernel's preferred tick source on ARMv7-A. Linux's `arch_timer` driver targets it directly. The i.MX6ULL also has legacy GPT and EPIT timer blocks. We use those in bare-metal Chapter 16 because they are simpler to demonstrate, then switch to the generic timer when Linux takes over.

> **Contrast with SysTick:** SysTick is a 24-bit down-counter, per-CPU, inside the M-profile core. The ARMv7-A generic timer is a 64-bit counter, per-CPU but globally synchronized, accessed via CP15. Both serve the same purpose (kernel/RTOS tick). The A-profile version is what enables coherent multi-CPU time on big systems.

## 4.8  The Generic Interrupt Controller (GIC)

The Cortex-M NVIC was inside the core. The A-profile equivalent, the **GIC**, is outside the core. The i.MX6ULL integrates a **GIC-400** (an implementation of GIC v2).

> **MCU bridge:** Think of the GIC like the Cortex-M NVIC scaled up for Cortex-A: it routes peripheral interrupts to CPU cores and has separate distributor and CPU-interface blocks.
>
> **GIC:** ARM's Generic Interrupt Controller, the Cortex-A interrupt router roughly analogous to NVIC on Cortex-M.

GICv2 has two parts:

- **Distributor** (`GICD_*` registers, base `0x00A01000` on i.MX6ULL): one per system. It arbitrates which interrupt goes to which CPU, sets priorities, masks, and trigger types (level/edge).
- **CPU Interface** (`GICC_*` registers, base `0x00A02000`): one per CPU. The core reads acknowledgement and writes end-of-interrupt here.

Three flavors of interrupt:

| Type | ID range | Purpose |
|------|----------|---------|
| SGI, Software-Generated | 0-15 | Software-generated interrupts, including inter-processor interrupts in SMP systems |
| PPI, Private Peripheral | 16-31 | Per-CPU peripherals. The generic timer interrupt is a PPI. |
| SPI, Shared Peripheral | 32-1019 | Shared peripheral interrupts such as UART, I²C, GPIO, FEC, and USB |

The i.MX6ULL maps SoC peripheral interrupts to SPI IDs. The mapping is in the reference manual's Chapter 3, "Interrupts and DMA Events". For example, `UART1` is SPI 26 (which the GIC sees as ID 26+32 = 58).

The GIC does **not** auto-vector. When the CPU takes an IRQ exception, it does not know which interrupt fired. The handler must read `GICC_IAR` to get the current interrupt's ID, dispatch on that ID, and write `GICC_EOIR` when done. This is the loop your IRQ handler must run.

## 4.9  Atomics, barriers, and memory ordering

ARMv7-A is **weakly ordered**. Stores and loads can be reordered by the CPU. Linux assumes this and inserts barriers where necessary. Two facts to keep:

- `dsb` (Data Synchronization Barrier): waits for outstanding memory accesses to complete.
- `dmb` (Data Memory Barrier): orders accesses but does not necessarily wait.
- `isb` (Instruction Synchronization Barrier): flushes the pipeline. It is required after changing CPSR, system registers, or page tables.

The atomic primitive is **LDREX/STREX**:

```asm
retry:
    ldrex   r1, [r0]      @ load-exclusive
    add     r1, r1, #1
    strex   r2, r1, [r0]  @ store-exclusive, r2=0 on success
    cmp     r2, #0
    bne     retry
```

Cortex-M has the same exclusive-load and exclusive-store instruction family. On A-profile, use the required memory barriers when the operation must also order other memory accesses.

## 4.10  NEON and VFP

VFPv4 gives you 32 double-precision FP registers and the usual IEEE-754 operations. NEON shares the same register file (viewed as 16 × 128-bit Q registers, or 32 × 64-bit D registers) and adds packed integer/float SIMD.

For kernel code, NEON/VFP are **disabled by default**. Touching them in kernel context requires `kernel_neon_begin()` / `kernel_neon_end()`. Failing to do so corrupts user-space FP state on context switch. Most drivers never need NEON. Some crypto and codec paths do.

For user space, NEON is always available. `libc`'s `memcpy`, `memset`, and `strcmp` use it, and you will see it in any glibc `objdump -d`.

## 4.11  Differences between Cortex-A7 and the bigger A-cores

The following table compares Cortex-A7 with two newer Cortex-A cores:

| Feature | Cortex-A7 | Cortex-A53 | Cortex-A72 |
|---------|-----------|------------|------------|
| ISA | ARMv7-A (32-bit only) | ARMv8-A (32+64-bit) | ARMv8-A |
| Pipeline | In-order, 8 stages | In-order, 8 stages | Out-of-order, 15 stages |
| L1 D-cache | 32 KB PIPT | 32 KB PIPT | 32 KB PIPT |
| Generic timer | Yes (CP15) | Yes (system reg) | Yes (system reg) |
| GIC version | GICv2 | GICv2/v3 | GICv2/v3 |

The most important difference for this book is the instruction set. Cortex-A7 is 32-bit only, so our assembly, page tables, and system registers use ARMv7-A definitions. The same high-level concepts apply to AArch64, but system register names and many bit layouts change.

## 4.12  Lab

This lab is a documentation exercise. Its purpose is to practice locating A-profile architectural information in the ARM and NXP manuals.

1. From the **ARM Architecture Reference Manual, ARMv7-A and ARMv7-R edition** (ARM DDI 0406), locate:
   - Section B1.3: Processor modes
   - Section B3.5: Short-descriptor translation table
   - Section B4.1: Generic timer
2. From the **Cortex-A7 MPCore Technical Reference Manual** (ARM DDI 0464), locate:
   - Chapter 6: L1 memory system (cache sizes, line length)
   - Appendix B: CP15 system registers, alphabetical
3. From the **i.MX 6ULL Applications Processor Reference Manual** (IMX6ULLRM), locate:
   - Chapter 3: Interrupts and DMA Events (SPI ID table)
   - Chapter 2: System Boot (so you are ready for Chapter 7 of this book)

Bookmark each. We will refer to them often.

## 4.13  Pitfalls

- **Assuming A-profile exceptions auto-stack like M-profile.** They do not. An IRQ handler that fails to save the required registers corrupts the interrupted context.
- **Forgetting `isb` after writing system registers.** Changes to TTBR, SCTLR, and VBAR require the barriers specified by the architecture. Without them, later instructions may execute using old state.
- **Thinking the GIC is in the core.** It is a separate memory-mapped block. You configure it via loads/stores to MMIO, not CP15. **MMIO** means memory-mapped I/O, where software accesses peripheral registers through normal load and store instructions.
- **Mixing up SPI (Shared Peripheral Interrupt) with SPI (Serial Peripheral Interface bus).** Context disambiguates, but every paragraph that mentions both is hard to read. This book will say "GIC SPI" or "SPI bus" whenever it could be ambiguous.
- **Cache flush by set/way for "flush everything".** This habit often comes from Cortex-M code. On A-profile, set/way flushes are *not* broadcast and can miss aliased lines. Use the VA-based ops for correctness. Only the initial cold-boot all-cache flush should use set/way.

## 4.14  Going deeper

- ARM DDI 0406: *ARM Architecture Reference Manual, ARMv7-A/R*. The authoritative architecture reference.
- ARM DDI 0464: *Cortex-A7 MPCore Technical Reference Manual*. The implementation specifics.
- ARM IHI 0048B: *ARM Generic Interrupt Controller v2 Architecture Specification*.
- ARM DEN 0013: *Cortex-A Series Programmer's Guide*. A tutorial-style overview.
- LWN: "An introduction to the ARM Generic Interrupt Controller" (2014).
- Linux source: `arch/arm/include/asm/{system,memory,page,pgtable}.h`, `arch/arm/mm/proc-v7.S`, `arch/arm/kernel/entry-armv.S`.

> Next chapter: **Chapter 5: A tour of the i.MX6ULL SoC.** We zoom out from the core to the chip around it.
