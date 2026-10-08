---
chapter: 17
title: MMU and caches
part: II - Bare-metal i.MX6ULL
estimated_pages: 26
status: draft
---

# Chapter 17: MMU and caches

A UART status register and a byte in OCRAM are both reached through pointers. Yet only one should be remembered in a cache. If the CPU keeps yesterday's UART status, your familiar polling loop can wait forever. If it keeps a recently used RAM byte, the same mechanism can save a bus transaction.

The Memory Management Unit (MMU) translates virtual addresses to physical addresses and checks access permissions. It also tells the CPU which kind of memory a pointer reaches. We will build an identity map, so the pointer values stay familiar while their permissions and memory attributes change. A cache keeps copies of instructions or data closer to the CPU.

Start with the program already running in OCRAM. Our table and small benchmark can stay there too, provided the linked image and reserved stacks fit. DDR is an optional extension, not a prerequisite for this lab. The example uses one privileged address space and 1 MiB sections; its startup sequence is limited to the book's fresh-ROM path.

## 17.1  What we are not doing

Our first-level table has 4096 entries: one for each possible 1 MiB virtual region. Having a slot for every region does not mean we should grant access to all of them.

- **No second-level tables:** sections are enough for this first map. Smaller pages would let us protect code, data and holes within a section separately.
- **No address-space switching:** entries are global (`nG=0`); we do not use per-process ASIDs (address-space identifiers).
- **No process isolation:** everything here runs at PL1, the privileged level. PL0 is the unprivileged level used by Linux applications.
- **No LPAE:** the short-descriptor format is sufficient for this map. Large Physical Address Extension is a separate translation format, not something required just to enable caches.
- **No stage-2 translation:** there is no active hypervisor mapping beneath our stage-1 map.

We will map the GIC and AIPS peripheral windows as Device memory and OCRAM as Normal memory. The GIC routes interrupts; MMDC, within the peripheral windows, controls DDR. Neither controller's registers belong in a RAM cache. If you later qualify DDR on your exact board, you can add only that qualified capacity to the map.

The table occupies 16 KiB. TTBR0, the Translation Table Base Register, points to its physical address. Once translation is enabled, the regions we chose still have virtual address = physical address. The benefit we will investigate comes from caching, not from changing the numbers in pointers.

## 17.2  Short-descriptor first-level entry, decoded

For a 1 MiB section, the 32-bit descriptor has these fields:

| Bits | Field | Choice in this chapter |
| --- | --- | --- |
| `31:20` | Physical section base | A 1 MiB-aligned physical address |
| `19` | NS | Zero; we do not change the current security state |
| `18` | Supersection | Zero: a section, not a 16 MiB supersection |
| `17` | nG | Zero: global translation |
| `16` | S | Zero for our single-core Normal RAM mapping; see Device encoding below |
| `15` | AP[2] | Zero |
| `14:12` | TEX[2:0] | Memory-type encoding |
| `11:10` | AP[1:0] | `01`: PL1 read/write, PL0 no access, with `SCTLR.AFE=0` |
| `9` | Implementation-defined | Zero |
| `8:5` | Domain | Zero, checked through DACR |
| `4` | XN | One for registers, zero for executable RAM in this simplified map |
| `3` | C | Part of the memory-type encoding |
| `2` | B | Part of the memory-type encoding |
| `1` | Section selector | One |
| `0` | PXN on implementations supporting it | Zero here, giving low bits `10` |

Do not reuse this layout for a page-table pointer or a second-level page. Low bits `00` mean a fault entry; `01` points to a second-level table. Bit 18 distinguishes sections from supersections. On implementations supporting PXN (Privileged Execute Never), low bits `11` can also describe a section/supersection with PXN set. We use `10` throughout.

Two control bits make the following interpretation possible: `SCTLR.TRE=0` disables TEX remapping, and `SCTLR.AFE=0` selects the AP permission interpretation above. With AFE set, AP[0] is an access flag instead. In Non-secure tables NS must be zero; in Secure tables it selects the Secure/Non-secure physical address space. This example does not switch between those worlds.

| Region | TEX | C | B | XN | AP[2:0] | Meaning with TRE=0 |
| --- | --- | --- | --- | --- | --- | --- |
| Device registers | `000` | `0` | `1` | `1` | `001` | Shareable Device, PL1 RW, no execution |
| Normal cacheable RAM | `001` | `1` | `1` | `0` | `001` | Inner/outer write-back, write-allocate; S=0 here |
| Normal non-cacheable RAM | `001` | `0` | `0` | As needed | `001` | Ordinary RAM without caching |
| Strongly-ordered reference | `000` | `0` | `0` | `1` | `001` | Separate memory type, not a variety of Normal memory |

The Device encoding `000/0/1` selects Shareable Device even though our descriptor's S bit is zero. Non-shareable Device has a different TEX encoding. Shareable does **not** mean that a peripheral automatically snoops CPU caches.

Try one decode before reading the code: the OCRAM descriptor `0x0090140E` selects physical section `0x00900000`, AP=`001`, TEX=`001`, C=B=1 and XN=0. Its low bits are `10`. A Device descriptor for `0x02000000` is `0x02000416`. The authoritative layouts and attribute encodings are in [Arm DDI 0406C.d](https://documentation-service.arm.com/static/5f8daeb7f86e16515cdb8c4e), Figure B3-4 and Table B3-10.

## 17.3  Building the L1 table

This fragment follows the book's **direct, freshly reset Boot ROM path on an open development device**, not entry from U-Boot, Linux or an arbitrary debugger session. Establish these conditions before calling it:

1. Code, constants, cleared BSS, table, benchmark buffers and every reserved stack fit in Chapter 10's application OCRAM interval, `0x00908000..0x0091FFFF`. The table is 16 KiB and the two benchmark arrays total 8 KiB; account for alignment gaps and other objects in the link map. Reserve their space and keep unrelated tests away from it.
2. The OCRAM mapping covers Chapter 10's `_vectors` entry at `0x00908000`, the installed VBAR and its handlers. Execution is little-endian at PL1, IRQ/FIQ are masked during the transition, and no DMA agent owns these buffers. Resolve any CP15 security restrictions before this point. For an optional DDR payload, also verify that its code, stacks and VBAR lie in qualified, mapped DDR.
3. `SCTLR.M=0` and `SCTLR.C=0`; the application has not yet enabled data caching. I-cache may already be enabled. IMX6ULLRM §8.4.4 says ROM enables I-cache for image download and disables D-cache/L2/MMU following authentication. That is not a claim that every cache is off at entry.

The invalidate-only routine below discards inherited cache contents under this fresh-ROM contract, before the application creates dirty cacheable data. It is **not** a handoff repair routine. If an earlier application or bootloader could own dirty lines, clean and invalidate them while the old mappings still work, using a separately reviewed transition. Clearing C alone can leave the only current copy of your stack in cache.

Use Chapter 10's integer-only flags for these fragments: `-mcpu=cortex-a7 -marm -mfloat-abi=soft -mgeneral-regs-only`, also at link time, with `-lgcc`. That avoids introducing VFP/NEON use before its startup policy is established.

Leave `DDR_MIB` at zero for the OCRAM lab. The only other accepted values are 256 and 512. Set one only after board-specific DDR initialization and an owned-range memory test have qualified that **exact installed capacity**, beginning at `0x80000000`. The build-time guard checks the value, not the hardware. Mapping DDR does not initialize it, and a successful test of a small buffer does not establish the full capacity.

`mmu.c`, a single-core initialization fragment for that contract:

```c
#include <stdint.h>

#ifndef DDR_MIB
#define DDR_MIB 0                 /* OCRAM-only default */
#endif
#if DDR_MIB != 0 && DDR_MIB != 256 && DDR_MIB != 512
#error "DDR_MIB must be 0, 256, or 512; qualify the exact board capacity"
#endif

#define L1_SECTION       2u
#define L1_AP_PL1_RW     (1u << 10)
#define L1_XN            (1u << 4)
#define L1_DEVICE        (1u << 2)  /* TEX=000, C=0, B=1 */
#define L1_NORMAL_WBWA   ((1u << 12) | (1u << 3) | (1u << 2))
#define ATTR_DEVICE     (L1_SECTION | L1_AP_PL1_RW | L1_DEVICE | L1_XN)
#define ATTR_NORMAL     (L1_SECTION | L1_AP_PL1_RW | L1_NORMAL_WBWA)

static uint32_t l1_table[4096] __attribute__((aligned(16384)));

void mmu_build_table(void)
{
    for (uint32_t i = 0; i < 4096; ++i)
        l1_table[i] = 0;             /* Unlisted regions fault. */

    l1_table[0x009] = 0x00900000u | ATTR_NORMAL; /* OCRAM section */
    l1_table[0x00A] = 0x00A00000u | ATTR_DEVICE; /* Cortex-A7/GIC */
    l1_table[0x020] = 0x02000000u | ATTR_DEVICE; /* AIPS-1 */
    l1_table[0x021] = 0x02100000u | ATTR_DEVICE; /* AIPS-2, MMDC */

    /* Opt-in only: one section per qualified MiB, beginning at 0x80000000. */
#if DDR_MIB > 0
    for (uint32_t i = 0x800; i < 0x800u + DDR_MIB; ++i)
        l1_table[i] = (i << 20) | ATTR_NORMAL;
#endif
}

static inline uint32_t read_sctlr(void)
{
    uint32_t v;
    __asm__ volatile ("mrc p15, 0, %0, c1, c0, 0" : "=r"(v));
    return v;
}

/* Invalidate-only: valid ONLY when no dirty data needs preserving. */
static void invalidate_data_caches(void)
{
    uint32_t clidr;
    __asm__ volatile ("dsb sy" ::: "memory");
    __asm__ volatile ("mrc p15, 1, %0, c0, c0, 1" : "=r"(clidr));

    for (uint32_t level = 0; level < 7; ++level) {
        uint32_t type = (clidr >> (3u * level)) & 7u;
        if (type == 0) break;
        if (type < 2 || type > 4) continue; /* No data/unified cache. */

        uint32_t selector = level << 1;    /* Data/unified side */
        uint32_t ccsidr;
        __asm__ volatile ("mcr p15, 2, %0, c0, c0, 0"
                          :: "r"(selector) : "memory");
        __asm__ volatile ("isb" ::: "memory");
        __asm__ volatile ("mrc p15, 1, %0, c0, c0, 0" : "=r"(ccsidr));
        uint32_t line_shift = (ccsidr & 7u) + 4u;
        uint32_t ways = ((ccsidr >> 3) & 0x3FFu) + 1u;
        uint32_t sets = ((ccsidr >> 13) & 0x7FFFu) + 1u;
        uint32_t way_shift = ways > 1 ? __builtin_clz(ways - 1u) : 0;

        for (uint32_t way = 0; way < ways; ++way)
            for (uint32_t set = 0; set < sets; ++set) {
                uint32_t sw = selector | (set << line_shift);
                if (ways > 1) sw |= way << way_shift;
                __asm__ volatile ("mcr p15, 0, %0, c7, c6, 2"
                                  :: "r"(sw) : "memory"); /* DCISW */
            }
        /* Finish this level before changing levels: ERR008958. */
        __asm__ volatile ("dsb sy" ::: "memory");
    }
    uint32_t zero = 0;
    __asm__ volatile ("mcr p15, 2, %0, c0, c0, 0" :: "r"(zero) : "memory");
    __asm__ volatile ("isb" ::: "memory");
}

int mmu_enable(void)
{
    uint32_t sctlr = read_sctlr();
    if (sctlr & ((1u << 0) | (1u << 2))) return -1;

    invalidate_data_caches();
    mmu_build_table();             /* Written while data caching is off. */
    __asm__ volatile ("dsb sy" ::: "memory");

    uint32_t zero = 0, domain0_client = 1;
    uint32_t table_pa = (uint32_t)(uintptr_t)l1_table;
    __asm__ volatile ("mcr p15, 0, %0, c2, c0, 2"
                      :: "r"(zero) : "memory"); /* TTBCR: EAE=0, N=0 */
    __asm__ volatile ("mcr p15, 0, %0, c2, c0, 0"
                      :: "r"(table_pa) : "memory"); /* TTBR0, NC table walks */
    __asm__ volatile ("mcr p15, 0, %0, c3, c0, 0"
                      :: "r"(domain0_client) : "memory");
    __asm__ volatile ("isb" ::: "memory");
    __asm__ volatile ("mcr p15, 0, %0, c8, c7, 0"
                      :: "r"(zero) : "memory"); /* TLBIALL, current state */
    __asm__ volatile ("mcr p15, 0, %0, c7, c5, 0"
                      :: "r"(zero) : "memory"); /* ICIALLU */
    __asm__ volatile ("mcr p15, 0, %0, c7, c5, 6"
                      :: "r"(zero) : "memory"); /* BPIALL */
    __asm__ volatile ("dsb sy; isb" ::: "memory");

    /* Direct TEX/AP encoding, little-endian tables, writable lab code. */
    sctlr &= ~((1u << 28) | (1u << 29) | (1u << 25)
               | (1u << 19) | (1u << 20)); /* TRE, AFE, EE, WXN, UWXN */
    sctlr |= (1u << 0) | (1u << 2) | (1u << 12) | (1u << 11);
    __asm__ volatile ("mcr p15, 0, %0, c1, c0, 0"
                      :: "r"(sctlr) : "memory"); /* M, C, I, Z */
    __asm__ volatile ("isb" ::: "memory");
    return 0;
}
```

Pause at the table's first entry: it is zero, not a Device mapping for address zero. An accidental pointer should fault rather than reach an unknown bus target.

- **Section granularity has a cost.** OCRAM occupies `0x00900000..0x0091FFFF`, but this descriptor covers through `0x009FFFFF`. It does not create RAM in the holes. Likewise, the peripheral sections include reserved addresses; do not probe them.
- **Alignment is part of the descriptor contract.** With N=0 the table base must be 16 KiB aligned. TTBR0's low bits include table-walk attributes, not address bits; passing an unaligned pointer can corrupt those attributes as well as select the wrong base. Check the linked ELF, not just the C declaration.
- **Check the application bounds before loading.** With Chapter 10's layout, loaded bytes must respect its ROM-active limit (`_edata <= 0x00918000`), BSS must stay below the reserved stack (`_ebss <= _stack_limit`), and the complete allocation ends no later than `0x00920000` (exclusive). Include any extra mode stacks added in Chapter 15. Inspect the link map and retain the linker assertions; a small raw binary can still have large BSS reservations. The table and arrays alone do not prove the whole image fits.
- **DACR controls domains.** Here `DACR=1` makes domain 0 a client and all other domains inaccessible. Clients enforce AP permissions. Manager domains bypass AP checks; they are not needed for this example.
- **L2 is real.** i.MX6ULL has 32 KiB L1 instruction/data caches and a 128 KiB integrated unified L2. The loop reads CLIDR/CCSIDR rather than invalidating only a hardcoded L1. ERR008958 requires a DSB before changing levels in set/way cleaning sequences; that boundary is also kept here.
- **The table is static after enable.** TTBR0 uses non-cacheable walks for simplicity. Editing a now-cached table later requires cleaning the descriptors, completing that maintenance, invalidating affected TLB entries and synchronizing. Some mapping changes require break-before-make; changing a live entry is not an ordinary array update.

This map deliberately leaves RAM writable and executable. A later design should separate read-only executable code from XN data. We are exposing the mechanism, not establishing Linux-style protection.

## 17.4  Calling `mmu_enable()`

After the OCRAM startup and link-layout checks above, use the same owned test buffers before and after enable. No relocation is required. If you choose the Chapter 14 DDR extension, establish its initialization, capacity and payload-placement contract separately; never run a destructive memory test over the live image, stack, BSS or table.

Application integration fragment; `bench_bytes()` is defined in §17.8 and `printf` is your existing UART output routine:

```c
void bench_bytes(void);

int main(void)
{
    /* Board/UART/timer setup and startup contract established earlier. */
    bench_bytes();
    if (mmu_enable() != 0) {
        printf("MMU setup refused: M or C already set\r\n");
        for (;;) {}             /* Intentional fatal stop, not a status wait. */
    }
    printf("MMU setup returned; checking the same workload\r\n");
    bench_bytes();
    for (;;) {}
}
```

A returned function and working UART are useful first checks. They are not proof of every permission or every RAM address. Record the actual timings, clock configuration, build flags and checksum; no timing transcript in this chapter represents a measured board run.

## 17.5  What happened

For the populated entries, virtual and physical addresses still match. Loads and stores to Device registers are not cached or speculatively performed like Normal-memory accesses. OCRAM can now be served through L1 and the integrated L2, and instruction fetches can use I-cache. With `DDR_MIB=0`, DDR entries remain faults; an accidental DDR pointer has not been given access to uninitialized memory.

Device memory is not a replacement for all ordering rules. A buffer in Normal RAM and a start register in Device memory are different parts of a transaction. You still need barriers and, where applicable, cache maintenance between preparing that buffer and starting hardware. A barrier can complete a register write; it cannot prove that the operation requested by that write has finished. Check the peripheral's completion condition.

Chapter 18's I2C and SPI fragments can use these Device register windows and small Normal buffers in OCRAM. Its optional LCD experiment needs a much larger framebuffer in separately qualified and mapped DDR. The same Device/Normal distinction matters when the LCD begins reading that buffer without the CPU's help.

## 17.6  Cache maintenance, when you must intervene

Suppose the CPU fills a buffer and then asks a peripheral to read it. The pointer is correct, but the newest bytes may exist only in dirty cache lines. DMA (Direct Memory Access) is another bus master; on this path it does not snoop those CPU copies.

```{figure} ../illustrations/part2/09-cache-and-ram-views.png
:alt: In a write-back example, the CPU's cache contains new buffer data while RAM still contains an older copy that a non-snooping DMA reader would see.
:width: 100%
:figclass: concept-sketch
:name: fig-part2-cache-dma

The picture shows the state before cleaning. The clean arrow is work still to do. Complete that work and the required barrier before starting the device, then keep the submitted buffer unchanged until the transfer finishes.
```

Three verbs describe different operations:

| Operation | What it does | Main risk |
| --- | --- | --- |
| Clean | Writes dirty data toward the specified coherency point; keeps a valid copy | Cleaning too late can overwrite data a device has just produced |
| Invalidate | Discards a cached copy | Dirty CPU data can be lost |
| Clean + invalidate | Writes back, then discards | Still needs ownership and completion ordering |

Use a buffer owned exclusively by one side at a time:

- **Device reads RAM:** CPU prepares buffer/descriptors, cleans to the Point of Coherency (PoC), executes DSB, then publishes the device-visible address and starts the transfer. The CPU must not change the submitted buffer until the device finishes.
- **Device writes RAM:** before submission, clean+invalidate the dedicated receive buffer to PoC and execute DSB. Keep the CPU away from it while DMA owns it. After confirmed device completion, invalidate again and execute DSB before CPU reads. The second invalidate removes any stale copy brought in during the transfer. Do not clean stale lines *after* DMA has written new data.
- **CPU writes instructions:** clean the changed D-cache lines to the Point of Unification (PoU), DSB, invalidate the corresponding I-cache lines and any required branch-predictor state, DSB, then ISB before executing. This is distinct from DMA maintenance to PoC.

PoU is where instruction and data views meet; PoC is where the relevant memory observers agree. On this integrated Cortex-A7 hierarchy, maintenance to PoC must account for L2 too, not merely put bytes into L2 while a peripheral reads DRAM.

These are single-line primitives, **not** complete transfer operations:

```c
#include <stdint.h>
#include <stddef.h>

static inline void dcache_clean_va(uintptr_t p)
{
    __asm__ volatile ("mcr p15, 0, %0, c7, c10, 1"
                      :: "r"(p) : "memory"); /* DCCMVAC: PoC */
}

static inline void dcache_invalidate_va(uintptr_t p)
{
    __asm__ volatile ("mcr p15, 0, %0, c7, c6, 1"
                      :: "r"(p) : "memory"); /* DCIMVAC: PoC */
}

static inline void dcache_clean_inv_va(uintptr_t p)
{
    __asm__ volatile ("mcr p15, 0, %0, c7, c14, 1"
                      :: "r"(p) : "memory"); /* DCCIMVAC: PoC */
}

static inline void icache_invalidate_va(uintptr_t p)
{
    __asm__ volatile ("mcr p15, 0, %0, c7, c5, 1"
                      :: "r"(p) : "memory"); /* ICIMVAU: PoU */
}
```

The `"memory"` clobber constrains the compiler. DSB/ISB constrain hardware. Neither substitutes for the other, and `volatile` MMIO alone does not order ordinary buffer stores around a start-register write.

Cortex-A7 L1 D-cache and L2 lines are 64 bytes; L1 **I-cache lines are 32 bytes**. This clean-range helper is therefore for the data side only:

```c
/* Same translation/ownership assumptions as the primitives above. */
int dcache_clean_range(const void *start, size_t len)
{
    if (len == 0) return 0;
    uintptr_t first = (uintptr_t)start;
    if (len - 1u > UINTPTR_MAX - first) return -1;
    uintptr_t last = (first + len - 1u) & ~(uintptr_t)63u;
    uintptr_t a = first & ~(uintptr_t)63u;
    for (;;) {
        dcache_clean_va(a);
        if (a == last) break;
        a += 64u;
    }
    __asm__ volatile ("dsb sy" ::: "memory");
    return 0;
}
```

Rounding out a **clean** range preserves neighbouring bytes. Blindly rounding an **invalidate** range can discard unrelated dirty objects. For DMA, align and pad dedicated buffers to complete 64-byte lines; ownership includes the padding. A four-byte receive object sharing a line with your counter is not a safe DMA buffer.

In Linux, use the [DMA API](https://docs.kernel.org/core-api/dma-api-howto.html), including mapping-error checks and the appropriate sync/unmap operations, rather than calling these bare-metal CP15 helpers. A CPU virtual pointer, a physical address and a DMA address are not generally interchangeable.

## 17.7  Why MMIO must be Device, not Normal Cacheable

Consider `while (!(UART_STATUS & READY)) {}`. Its `volatile` load asks the compiler to read each time. If the register window is Normal Cacheable, the CPU can still answer those reads from a cache. Compiler correctness does not repair the memory type.

The consequences go beyond slow write visibility: Normal accesses can be speculative, merged or reordered in ways a register protocol does not permit. A read with side effects may be particularly destructive. Do not test this by making a live peripheral cacheable.

Our table grants Device mappings only to the register windows we use and leaves other sections faulting. This catches some mistakes without claiming that every address inside a broad Device section is safe. A DSB also cannot repair a wrong memory type or clear a peripheral's status flag for you.

## 17.8  Performance measurement, in more detail

A benchmark needs an observable result. Otherwise the compiler may remove the copying that you intended to time. The following integration fragment uses volatile bytes to make each load/store happen. It is deliberately a **byte-copy workload**, not an optimized `memcpy` or a DRAM-bandwidth test.

Provide your existing UART `printf` and a free-running hardware-timer helper `gpt_now_us()` that really returns modulo-2^32 microseconds. A raw GPT counter is not automatically in microseconds; derive its tick rate as in Chapter 16. This test does not require timer interrupts.

```c
#include <stdint.h>

void bench_bytes(void)
{
    static volatile uint8_t src[4096], dst[4096];
    for (unsigned i = 0; i < 4096; ++i) src[i] = (uint8_t)i;

    __asm__ volatile ("dsb sy" ::: "memory");
    uint32_t before = gpt_now_us();
    for (unsigned n = 0; n < 1000; ++n)
        for (unsigned i = 0; i < 4096; ++i) dst[i] = src[i];
    __asm__ volatile ("dsb sy" ::: "memory");
    uint32_t elapsed = gpt_now_us() - before;

    uint32_t sum = 0;
    for (unsigned i = 0; i < 4096; ++i) sum += dst[i];
    printf("4096000 bytes: %u us, checksum %u\r\n",
           (unsigned)elapsed, (unsigned)sum);
}
```

The expected checksum is **522240**, calculated from sixteen copies of the byte values 0 through 255. That is a data check, not an invented timing result. The elapsed subtraction handles a counter wrap provided the interval is shorter than one full timer period.

| Configuration to record | What the comparison tells you |
| --- | --- |
| Startup contract: MMU/D-cache off; record I-cache state | Baseline for your actual startup state |
| MMU and caches enabled, same buffers and build | Effect of the combined configuration |
| Separate cold run, test RAM Normal non-cacheable | Helps separate translation from data caching |

The arrays total 8 KiB and are copied repeatedly. Most repetitions can hit cache; they do not stream through 4 MiB of distinct DRAM. Report 4,096,000 copied bytes, access pattern, CPU/timer clocks, compiler flags and cache state. If you use the PMU cycle counter instead, first configure its enable/divide-by-64 controls and account for its wrap. Do not convert counts to MB/s using an assumed CPU clock.

## 17.9  Lab

1. **Decode before enabling.** Compute the two descriptors in §17.2, then inspect the generated entries. Check the linked table's 16 KiB alignment, placement and reserved space. Which descriptor makes a peripheral non-executable?
2. **Measure your workload in OCRAM.** Keep `DDR_MIB=0`, check the complete linked OCRAM allocation, and run §17.8 before and after enable under the startup contract. Both checksums must be 522240. Record results rather than trying to match a promised speed-up. DDR relocation is an optional later comparison, not a condition for passing this lab.
3. **Separate MMU from caching.** In a separate cold-start build, make the benchmark's RAM sections Normal non-cacheable (`TEX=001, C=B=0`). Keep live code/stack mappings valid. Compare timings; do not change live descriptors without the maintenance sequence.
4. **Reason about aliases on paper.** Decode two virtual sections pointing to one physical RAM section with identical attributes. Predict their physical addresses. Cortex-A7 D-cache is PIPT (physically indexed, physically tagged). Both translations refer to the same physical data, but their memory attributes must remain compatible.
5. **Check range boundaries and ownership.** Work out the lines touched for zero length, an aligned 64-byte range, and a range crossing a line. Explain why an unaligned DMA receive buffer can damage a neighbouring object. A CPU-only clean/read test does not prove DMA coherency; an actual device test requires its completion/ownership protocol.

Answer checks: XN is bit 4; the Device example sets it. A zero-length clean touches no line, an aligned 64-byte clean touches one, and a boundary-crossing range touches at least two. Invalidating a shared dirty line can discard bytes outside the DMA payload.

## 17.10  Pitfalls

- **Treating MMU-off as reset state.** Check both the control bits and the direct fresh-ROM contract. Never invalidate dirty live data merely because C is now zero.
- **Maintaining L1 but forgetting L2.** Read cache geometry and cover the hierarchy. Apply the DSB-between-levels requirement in supplied erratum ERR008958, especially in clean+invalidate handoff code.
- **Unmapped execution path.** Include the current PC, return address, stack, vector table and its handlers, table and UART/timer registers before setting M. Check VBAR and SCTLR.V; the example does not relocate vectors.
- **Wrong descriptor interpretation.** AFE, TRE and TTBCR.EAE change how the fields are interpreted. N=0 selects a full TTBR0 table; TTBR low bits are walk attributes, not a spare part of the base address.
- **Missing compiler or hardware barriers.** A bare `asm volatile` is not a compiler memory barrier. DSB completes the relevant accesses/maintenance; ISB synchronizes the instruction stream after control changes.
- **Changing a DMA-owned buffer.** Clean/invalidate operations cannot make simultaneous CPU/device modification safe. Confirm completion before reclaiming ownership.
- **Broad executable RAM mappings.** Useful for a first controlled lab, not a protection policy. Leave unknown sections faulting and use finer granularity when you need code/data separation.

## 17.11  Going deeper

- [Arm DDI 0406C.d](https://documentation-service.arm.com/static/5f8daeb7f86e16515cdb8c4e): B3.5 descriptor formats, B3.7 access control, B3.8 memory attributes and B4 cache/TLB operations.
- [Cortex-A7 TRM, DDI 0464B](https://documentation-service.arm.com/static/5e8f089d88295d1e18d3b906): cache line sizes, PIPT D-cache/VIPT I-cache and CP15 controls. Pair it with the i.MX6ULL-specific configuration in IMX6ULLRM Chapter 12.
- Supplied **IMX6ULLRM Rev. 1**, §8.4.4 for ROM cache use; supplied **IMX6ULL errata Rev. 1.2**, ERR008958 and ERR010449. Authentication/cache errata are not an invitation to change fuses in this lab.
- [Linux v6.12 `proc-v7-2level.S`](https://github.com/torvalds/linux/blob/v6.12/arch/arm/mm/proc-v7-2level.S) and [`mmu.c`](https://github.com/torvalds/linux/blob/v6.12/arch/arm/mm/mmu.c): compare the policies and platform handling with our static table.
- [Linux DMA API guide](https://docs.kernel.org/core-api/dma-api-howto.html): ownership, coherent versus streaming mappings, CPU pointers versus device addresses, and barriers even for coherent memory.

> Next: **Chapter 18, Optional bare-metal peripherals.** Follow one I2C transaction, one SPI command and an LCD framebuffer handoff. The supplementary Chapters 18A-18C offer more bare-metal practice; you can also continue to U-Boot in Part III.
