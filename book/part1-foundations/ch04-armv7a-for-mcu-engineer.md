# Chapter 4: ARMv7-A and the Cortex-A7, for the MCU engineer

The last chapter prepared compilers for our board. Before using them to write startup code, we need to know what the Cortex-A7 expects from that code. Some parts are familiar: integer registers, a stack, and load/store instructions. Others change the way we handle exceptions and memory.

For example, a Cortex-M interrupt handler benefits from hardware stacking. On the Cortex-A7, entering an exception selects different registers, but software must save the rest of the context. That difference will matter when we write our own interrupt handler. The MMU, meanwhile, supplies the address translation behind Chapter 2's separate process address spaces.

On a first reading, follow the integer registers, SVC and IRQ modes, banked SP/LR, and physical versus virtual addresses. The detailed tables and the sections on caches, timers, security, and virtualization are also here for later reference. You can return to their register encodings when a lab actually uses them.


## 4.1  Where the Cortex-A7 sits in the ARM lineup

The name "Cortex-A7" can be misleading if you already use a Cortex-M7. The matching number does not mean that the cores share an architecture. Arm names describe two different things:

- **Profile letter.** `A` for "Application" (smartphones, set-top boxes, embedded Linux), `R` for "Real-time" (storage controllers, automotive), `M` for "Microcontroller" (the Cortex-M0/M3/M4/M7/M33 you have worked with).
- **Architecture version.** v6, v7, v8, v9. The version determines the instruction set and which features are present. The core implementation determines pipeline depth, cache topology, and clock ceiling.

Our i.MX6ULL has one Cortex-A7, using the ARMv7-A architecture. It includes the VFPv4 floating-point unit and NEON vector instructions, but no Cortex-M companion. Some other i.MX6 parts, such as SoloX, include an M4; do not infer the contents of this chip from that family name.

The core name also does not specify the board's clock frequency. Clock limits come from the fitted silicon's speed grade and electrical conditions. The supplied industrial datasheet lists 528 and 792 MHz grades, while Linux v6.6's ULL device tree lists operating points to be constrained by the part and board. A later example selects 696 MHz, but that is not a universal reset, BSP, or Linux frequency. Chapter 5 shows how to read the part marking before choosing a clock setting.

The Cortex-A7 is an in-order, dual-issue core with an 8-stage pipeline. We do not need to study the pipeline to write the first program. Its register and exception model, however, gives us a manageable place to learn the ARMv7-A mechanisms later used by U-Boot and Linux.

## 4.2  The features Cortex-M does not have

Use the following table to place familiar MCU features beside the Cortex-A7 equivalents. It is a comparison, not a specification for every Cortex-M part:

| Feature | Cortex-M (typical) | Cortex-A7 |
|---------|---------------------|-----------|
| Address space | Single, flat, physical | Virtual, per-context, via MMU |
| MMU | No (some have MPU) | Yes, 2-level page tables |
| Privilege levels | Privileged / Unprivileged | PL0/PL1, plus PL2 for HYP; modes below |
| Banked registers | A few (MSP, PSP) | Selected registers are banked in exception modes |
| Caches | L1 I/D on M7+, sometimes none | L1 I/D mandatory. L2 is integrated inside the Cortex-A7 MPCore platform (128 KB on i.MX6ULL), with no separate PL310 controller |
| TLB (Translation Lookaside Buffer, the MMU's address-translation cache) | No | Yes |
| Generic timer | No (SysTick) | Yes, architected |
| Interrupt controller | NVIC (in-core, vectored) | **GIC**, an external Generic Interrupt Controller block. Prioritized, not auto-vectored |
| Exception model | Tail-chained, automatic stacking | Mode switch, software-saved context |
| FPU | Optional VFP variant | VFPv4 (mandatory in i.MX6ULL) |
| SIMD | DSP extensions (limited) | NEON (64-/128-bit) |
| Atomic ops | Exclusives on M3/M4/M7; not M0/M0+ | LDREX/STREX |
| Instruction set | Thumb; M0/M0+ have a smaller subset than M3/M4/M7 | ARM and Thumb-2 for this book |

Two rows explain much of the early learning curve. The MMU lets the operating system give processes separate memory mappings. The exception model makes software responsible for context that Cortex-M hardware stacks automatically. We will follow that exception model first. Timer and NEON support are useful later, but their presence does not mean every Linux configuration uses them.

## 4.3  Exception modes and banked registers

Start with an ordinary interrupt in your MCU project. You wrote a C handler, but the core did work before its first instruction ran:

On Cortex-M, the usual sequence is:

1. Hardware automatically saves R0-R3, R12, LR, PC, and xPSR to the current stack.
2. Hardware loads PC from the vector table.
3. Your ISR runs.
4. `BX LR` (with the special EXC_RETURN value in LR) tells the CPU to unstack and resume.

Our Cortex-A7 does not do that automatic stack push. Instead, an exception changes the **processor mode** and selects the register view for that mode. Some register names now refer to different physical registers. These separate copies are called **banked registers**.

Consider `sp`. Code in SVC mode uses `sp_svc`; after an IRQ is accepted, `sp` refers to `sp_irq`. The old stack pointer has not been pushed anywhere. It is still in its own banked register, while the IRQ handler needs its separate stack to have been initialized already. Ordinary registers such as `r0` remain shared, so the handler must save them if it needs to use them without losing the interrupted value.

The tables below describe this Cortex-A7's nine modes. Other A-profile cores need not implement exactly the same set. First use the tables to follow SVC and IRQ; the extra security and hypervisor modes can wait.

### The registers you are looking at

Ordinary integer instructions use `r0` through `r15`. Several have familiar aliases: `sp` for the stack pointer, `lr` for the link register, and `pc` for the program counter. `CPSR` records the current status and mode; an exception mode also has an `SPSR` for saved status. The table connects these names to their roles in C calls and exception handling:

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

Knowing what a register does is one question. Knowing which physical copy is visible is another. The next two tables separate those questions by putting modes in columns and register names in rows.

First, the Cortex-M view:

| Register | Thread mode | Handler mode |
|----------|-------------|--------------|
| `r0`-`r12` | Same physical registers. | Same physical registers, exception entry stacks `r0`-`r3` and `r12` automatically. |
| `r13` / `sp` | `MSP` or `PSP`, selected by `CONTROL.SPSEL`. | `MSP`. |
| `r14` / `lr` | Normal function return address. | `EXC_RETURN`, the special value used by `BX LR` to leave the exception. |
| `r15` / `pc` | Current instruction stream. | Handler instruction stream loaded from the vector table. |
| status | Active `xPSR`. | Active `xPSR`. The previous `xPSR` is stacked automatically. |

Here the general-purpose registers are shared. Hardware saves the listed interrupted values on entry and restores them on exception return. Thread mode may use MSP or PSP, while Handler mode uses MSP.

Now the Cortex-A7 view:

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

The mode bits live in `CPSR.M[4:0]`. An exception records the old CPSR in the destination mode's `SPSR`, giving the return sequence a way to restore the interrupted mode and status.

MON serves security-state transitions, and HYP serves virtualization. This Cortex-A7 supports those extensions, but our first bring-up path does not use them. Keep USR, SVC, IRQ, ABT, and UND in view first. Part IX returns to HYP.

Total physical register count exposed by Cortex-A7: **34 general-purpose**, **8 status (CPSR + 7×SPSR)**, plus `ELR_hyp`. That is 43 registers. A normal non-HYP mode sees at most 18 at once: `r0`-`r15`, `CPSR`, and its `SPSR`. HYP sees `ELR_hyp` as its extra exception-return address.

To read the table as a sequence, imagine an IRQ arriving while SVC code is running. The CPU copies CPSR into `SPSR_irq`, records an exception return address in `lr_irq`, selects `sp_irq`, and enters the IRQ vector. `r0` still contains the interrupted code's value. If the handler uses it, software must save and later restore it.

This gives banked registers a useful but limited job: they preserve selected exception state, not every register the handler might overwrite. Chapter 15 turns this sequence into an executable handler with the appropriate return instructions. HYP has a different return arrangement using `ELR_hyp`, which is why it has its own row above.

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

The Cortex-M core hides much of this work from the C handler. On A-profile, entry and exit assembly becomes part of the software we must understand. Linux's `entry-armv.S` contains that machinery for its own exception handling.

### PL0 vs PL1 vs PL2

Across the nine modes, ARM defines three **privilege levels**:

- **PL0** (unprivileged, like Cortex-M unprivileged Thread mode): only USR mode. This is the mode applications run in.
- **PL1** (privileged): most modes, including SVC, IRQ, FIQ, ABT, UND, and SYS. This is the level the kernel runs at.
- **PL2** (hypervisor): only HYP mode. It can intercept selected PL1 operations and transfer control to the hypervisor.

ARM TrustZone adds a separate **Security state**: Normal World or Secure World. This is independent of PL0/PL1/PL2. MON mode is the mode used to switch between the two worlds.

MMU/control and cache-maintenance operations generally require privileged execution. Some CP15 registers, such as user thread-ID registers, are user-accessible; access rights are defined per register.

You will also meet the name **CP15** in startup assembly. It is the ARMv7-A access path for system-control registers, not another chip on the board. Instructions such as `mrc` and `mcr` access controls including the MMU enable bits in `SCTLR`, page-table bases in `TTBR0` and `TTBR1`, and the exception-vector base in `VBAR`. Cache maintenance and generic-timer access also use this path. AArch64 uses named system-register instructions instead.

Linux runs user space in USR mode (PL0) and the kernel in SVC mode (PL1). The transition between them, what the kernel calls "userspace ↔ kernelspace", is a hardware mode switch triggered by an `svc` instruction or an interrupt.

HYP mode is the extra layer used by a hypervisor. A guest kernel runs as if it controls PL1, but sensitive actions can be redirected to PL2. The hypervisor can then decide whether to allow the action, emulate it, or stop the guest. The matching instruction is `hvc` (Hypervisor Call), similar to `svc` but for calls into the hypervisor.

Do not confuse HYP mode with Monitor mode:

- **HYP / PL2:** virtualizes Normal World operating systems.
- **MON / Monitor mode:** switches between Secure World and Normal World for TrustZone.

Part IX uses this distinction in real labs: Xen uses HYP mode for guests, while OP-TEE in Chapter 124 uses Monitor/Secure-world mechanisms.

Return now to Chapter 2's syscall. The `svc` instruction triggers a Supervisor Call exception from USR mode to SVC mode. SP and LR select their SVC copies, and the kernel handler runs with privileged access. It follows the exception model we have just studied, even though the application requested the transition deliberately rather than a peripheral raising an IRQ.

## 4.4  The CPSR / SPSR program status registers

CPSR (Current Program Status Register) is the A-profile equivalent of M-profile's xPSR, but more is in it:

```
 Selected fields only:
 31 30 29 28 27 ...  9  8  7  6  5  4  3  2  1  0
 N  Z  C  V  Q       E  A  I  F  T  M4 M3 M2 M1 M0
```

- **N, Z, C, V:** condition flags (the same as M-profile: negative, zero, carry, overflow)
- **Q:** saturation flag, set by saturating arithmetic instructions
- **IT[7:0]** (split bits 26:25 + 15:10): IF-THEN block state for Thumb-2 conditional execution
- **J** (bit 24), **T** (bit 5): together select the active instruction set: ARM (J=0,T=0), Thumb (J=0,T=1), ThumbEE (J=1,T=1), Jazelle (J=1,T=0)
- **GE[3:0]** (bits 19:16): flags used by packed integer instructions such as `UADD8`, not NEON comparisons.
- **E:** current data-endianness state where applicable, not a choice attached to each load/store. This book uses little-endian data.
- **A:** asynchronous abort mask
- **I:** IRQ mask (`I=1` disables IRQs)
- **F:** FIQ mask
- **T:** Thumb state (`T=1` means executing in Thumb)
- **M[4:0]:** current processor mode (encoding for USR/SVC/IRQ/...)

When an exception is taken, the CPU copies CPSR into `SPSR_<mode>` and writes the new mode into CPSR.M[4:0]. The handler can use `mrs Rn, spsr` to read the saved value. A `cps` instruction can change the current mode and interrupt-mask bits.

For the first labs, pay particular attention to the mode field and the I/F interrupt masks. They let us describe which register bank is active and whether IRQ or FIQ may interrupt the code. The remaining status fields become useful when reading instruction behavior and more advanced exception paths.

## 4.5  Memory model and the MMU

Chapter 2 described the MMU from an application's point of view. Here we can name the structures that make its translation work. On our non-virtualized path, **stage 1** translates a virtual address into a physical address using translation tables in memory.

The Cortex-A7 also supports a second translation stage for virtualization. Do not confuse a translation *stage* with a table *level*: two stages are guest and hypervisor translations, while two levels are successive table lookups within one translation. We only need stage 1 for the initial labs.

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

An entry that points to another table has a different format from one that maps memory directly. Section and small-page mappings also differ. Rather than memorizing all the fields now, ask what each mapping must tell the MMU: the physical address, who may access it, and how accesses to that memory should behave.

The corresponding leaf fields include access permissions (AP), execute-never (XN), and memory attributes (TEX/C/B and shareability). Relevant L1 descriptors also select a domain; a domain in "client" mode applies the mapping's permissions. Chapter 17 decodes the exact section format used by its example.

The **TLB** caches recent address translations. There is also an **ASID** (Address Space ID, 8 bits) that tags TLB entries so context switches do not need a full TLB flush.

We will build, by hand, a minimal L1-only page table in Chapter 17. Once you have done that exercise, kernel memory bugs are much easier to read.

### What the kernel does with this

Linux on ARMv7-A:

- In the v6.6 non-LPAE two-level path, uses unsplit tables and switches the process table through **TTBR0**. Other configurations can select TTBR0/TTBR1 regions; a virtual-address user/kernel split does not imply that hardware-register split. See [proc-v7-2level.S](https://github.com/torvalds/linux/blob/v6.6/arch/arm/mm/proc-v7-2level.S).
- Splits the 4 GB virtual address space into a user range (`0x00000000`-`0xBFFFFFFF`) and kernel range (`0xC0000000`-`0xFFFFFFFF`) by default. `CONFIG_PAGE_OFFSET` controls this split.
- Uses a fixed offset for the **linear mapping of low RAM** (`PHYS_OFFSET` to `PAGE_OFFSET`), not arbitrary `vmalloc`, `ioremap`, or high-memory pointers. Drivers use mapping and DMA APIs, not subtraction from any kernel pointer. See the [ARM memory layout](https://www.kernel.org/doc/html/v6.6/arch/arm/memory.html).

With that default split, the user range occupies about 3 GiB of virtual address space. This is a layout choice, not a statement that each process has 3 GiB of physical RAM.

## 4.6  Caches

A cache keeps copies of memory close to the CPU. That makes repeated instruction fetches and data accesses faster, but creates another question for low-level code: does the copy agree with the memory another agent sees? Before discussing maintenance, distinguish the two L1 caches implemented in the i.MX6ULL:

| Cache | Size | Ways | Line size | Organization |
|---|---|---|---|---|
| L1 instruction | 32 KiB | 2 | 32 bytes | VIPT: virtually indexed, physically tagged |
| L1 data | 32 KiB | 4 | 64 bytes | PIPT: physically indexed, physically tagged |

These properties are specified separately in the [Cortex-A7 TRM DDI 0464F, Chapter 6](https://documentation-service.arm.com/static/602cf701083323480d479d18?token=). NXP RM Chapter 12 specifies the implemented sizes and integrated 128 KiB unified L2. This SoC does not have the separate PL310 controller used by some earlier i.MX6 parts.

Two A-profile cache properties are important here:

1. **Caches are off at reset.** Our first small programs can run without them. Larger programs benefit greatly from caching, but enabling it also makes memory attributes and coherency part of startup. Chapter 17 introduces that setup.
2. **I/D geometry differs.** Do not use one line size for both maintenance loops. DMA sharing and changed executable instructions require operation-specific coherency work in Chapters 17 and 51.

The maintenance names describe different actions. **Clean** writes modified, or *dirty*, data toward the required coherency point. **Invalidate** discards a cached copy so it will not be reused. Discarding dirty data without first cleaning it can lose writes. **Clean and invalidate** performs both actions; the word "flush" alone does not tell you which was intended.

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

The familiar SysTick combines a counter with an interrupt mechanism. The **ARMv7 generic timer** separates these ideas: a shared system counter supplies time, while per-CPU comparators decide when to raise an interrupt. Cortex-A7 supports this interface, but the SoC's clocks and power integration still determine when it operates.

Key registers (CP15 access):

- `CNTFRQ`: counter frequency (Hz). Software writes this once at boot to inform the rest of the system.
- `CNTPCT`: current counter value (64-bit physical counter).
- `CNTP_CVAL`: comparator value. The timer fires when CNTPCT >= CNTP_CVAL.
- `CNTP_CTL`: enable + interrupt mask + status.

Linux's `arch_timer` supports it, but v6.6 [imx6ul.dtsi](https://github.com/torvalds/linux/blob/v6.6/arch/arm/boot/dts/nxp/imx/imx6ul.dtsi) disables the generic timer, and [imx6ull.dtsi](https://github.com/torvalds/linux/blob/v6.6/arch/arm/boot/dts/nxp/imx/imx6ull.dtsi) does not enable it. The inherited setup uses SoC timer facilities such as GPT; do not enable a node merely because the core implements its architecture. Chapter 16 uses GPT/EPIT on bare metal. After Linux boots, inspect timer/clocksource messages and `/sys/devices/system/clocksource/clocksource0/current_clocksource` to identify the actual configuration.

Keep that separation in mind when reading the register names: SysTick is a per-core 24-bit down-counter, while the generic timer uses a shared 64-bit counter and per-CPU comparator state. Reading the time and arranging a future interrupt are related operations, but not the same one.

## 4.8  The Generic Interrupt Controller (GIC)

The Cortex-M NVIC was inside the core. The A-profile equivalent, the **GIC**, is outside the core. The i.MX6ULL integrates a **GIC-400** (an implementation of GIC v2).

The familiar job is still deciding which pending interrupt the CPU should handle. The GIC splits that job between a system-wide distributor and a CPU interface:

GICv2 has two parts:

- **Distributor** (`GICD_*` registers, base `0x00A01000` on i.MX6ULL): one per system. It arbitrates which interrupt goes to which CPU, sets priorities, masks, and trigger types (level/edge).
- **CPU Interface** (`GICC_*` registers, base `0x00A02000`): one per CPU. The core reads acknowledgement and writes end-of-interrupt here.

Three flavors of interrupt:

| Type | ID range | Purpose |
|------|----------|---------|
| SGI, Software-Generated | 0-15 | Software-generated interrupts, including inter-processor interrupts in SMP systems |
| PPI, Private Peripheral | 16-31 | Per-CPU peripherals. The generic timer interrupt is a PPI. |
| SPI, Shared Peripheral | 32-1019 | Architectural range for shared peripheral interrupts; not all are implemented on this SoC |

The i.MX6ULL maps SoC peripheral interrupts to SPI IDs. The mapping is in the reference manual's Chapter 3, "Interrupts and DMA Events". For example, `UART1` is SPI 26 (which the GIC sees as ID 26+32 = 58).

Unlike the NVIC's vector selection, the GIC does not send the CPU directly to a different handler address for every peripheral. An IRQ enters the CPU's IRQ exception path. Software reads `GICC_IAR` to obtain the interrupt ID, dispatches to the appropriate handler, and writes `GICC_EOIR` when handling is complete. This is the other half of the interrupt story: the CPU's banked registers handle exception state; the GIC tells software which source needs attention.

## 4.9  Atomics, barriers, and memory ordering

Source-code order is not always enough to describe when another agent observes memory accesses. ARMv7-A is **weakly ordered**, so low-level software uses barriers where ordering or completion matters. Three instruction names recur in later startup code:

- `dsb` (Data Synchronization Barrier): waits for outstanding memory accesses to complete.
- `dmb` (Data Memory Barrier): orders accesses but does not necessarily wait.
- `isb` (Instruction Synchronization Barrier): synchronizes subsequent instruction execution with relevant context changes. It is not a complete page-table update recipe, nor required after every condition-flag change. A particular operation may require DSB, cache maintenance, TLB invalidation, and ISB in a specified sequence.

**LDREX/STREX** solves a different problem: updating a word without losing an intervening update. The pair attempts an exclusive load and store; if the store fails, this example retries. It assumes a suitably aligned word in normal memory, not an arbitrary device register. Atomicity by itself does not order all other accesses.

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

For now, our startup exercises use integer instructions. User programs can use NEON once the operating system enables and manages its context. Whether a particular library function does so depends on that library's build and implementation; we will inspect actual binaries rather than assume every `memcpy` uses vector instructions.

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

The chapter introduced more names than the first program needs. This exercise gives three of them a location in the manuals: processor modes, translation tables, and interrupt IDs. Locate the sections below and bookmark them; use the titles as well as the numbers when comparing editions.

1. From the **ARM Architecture Reference Manual, ARMv7-A and ARMv7-R edition** (DDI 0406C.d), locate:
   - Section B1.3: Processor modes
   - Section B3.5: Short-descriptor translation table
   - Chapter B8: Generic timer
2. From the **Cortex-A7 MPCore Technical Reference Manual** (DDI 0464F), locate:
   - Chapter 6: L1 memory system (cache sizes, line length)
   - Chapter 4: System control, including CP15 registers
3. From the **i.MX 6ULL Applications Processor Reference Manual** (IMX6ULLRM), locate:
   - Chapter 3: Interrupts and DMA Events (SPI ID table)
   - Chapter 8: System Boot (so you are ready for Chapter 7 of this book)

Bookmark each. We will refer to them often.

Answer check: the NXP interrupt table gives UART1 SPI index 26, hence GIC ID 58. The A7 TRM gives different L1 I/D line sizes (32/64 bytes); CP15 is not in its revision-history appendix. Use section titles as well as numbers when comparing other editions.

## 4.13  Pitfalls

- **Assuming A-profile exceptions auto-stack like M-profile.** They do not. An IRQ handler that fails to save the required registers corrupts the interrupted context.
- **Forgetting `isb` after writing system registers.** Changes to TTBR, SCTLR, and VBAR require the barriers specified by the architecture. Without them, later instructions may execute using old state.
- **Thinking the GIC is in the core.** It is a separate memory-mapped block. You configure it via loads/stores to MMIO, not CP15. **MMIO** means memory-mapped I/O, where software accesses peripheral registers through normal load and store instructions.
- **Mixing up SPI (Shared Peripheral Interrupt) with SPI (Serial Peripheral Interface bus).** Context disambiguates, but every paragraph that mentions both is hard to read. This book will say "GIC SPI" or "SPI bus" whenever it could be ambiguous.
- **Treating one cache operation as a universal recipe.** Set/way maintenance visits physical sets/ways for whole-cache work; it is not simply a scheme that misses virtual aliases. Buffer-specific maintenance needs the correct address range, line boundaries, coherency point, and synchronization. Multi-core coordination adds requirements. Follow the operation's sequence, and use Linux DMA APIs in drivers.

## 4.14  Going deeper

- ARM DDI 0406: *ARM Architecture Reference Manual, ARMv7-A/R*. The authoritative architecture reference.
- ARM DDI 0464: *Cortex-A7 MPCore Technical Reference Manual*. The implementation specifics.
- ARM IHI 0048B: *ARM Generic Interrupt Controller v2 Architecture Specification*.
- ARM DEN 0013: *Cortex-A Series Programmer's Guide*. A tutorial-style overview.
- LWN: "An introduction to the ARM Generic Interrupt Controller" (2014).
- Linux source: `arch/arm/include/asm/{system,memory,page,pgtable}.h`, `arch/arm/mm/proc-v7.S`, `arch/arm/kernel/entry-armv.S`.

We can now distinguish CPU registers, exception state, and system-control registers. The LED and UART, however, live outside the CPU core. Chapter 5 follows the memory map, clocks, and pin routing that connect the Cortex-A7 to those peripherals.
