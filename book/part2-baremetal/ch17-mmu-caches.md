---
chapter: 17
title: MMU and caches
part: II — Bare-metal i.MX6ULL
estimated_pages: 26
status: draft
---

# Chapter 17 — MMU and caches

> **What:** build a first-level page table by hand, map our peripherals as Device memory and our RAM as Normal Cacheable, switch on the MMU and both caches, and measure the speed-up.
>
> **Why:** The MMU and caches are the last hardware blocks Linux abstracts from you. Turn them on once by hand and every kernel page-table operation looks like a variation on this.
>
> **Focus:** the short-descriptor format: a 4096-entry first-level table covering 4 GiB in 1 MiB sections, with per-section permissions and memory attributes. LPAE (3 levels, 40-bit PA) is overkill for our 512 MiB DRAM.

## 17.1  What we are not doing

We will use *only the first-level page table*, mapping the entire 4 GiB virtual space in 1 MiB sections. Specifically:

- **No L2 tables** — we don't need 4 KiB page granularity for bare-metal.
- **No ASIDs** — single address space; one global mapping.
- **No process isolation** — that's a Linux concern.
- **No LPAE** — short-descriptor format is sufficient.

What we *are* doing:

- Define which 1 MiB regions are Device memory (peripherals: AIPS, GIC, MMDC registers) and which are Normal cacheable (OCRAM, DRAM).
- Build a 16 KiB table containing 4096 first-level entries.
- Point TTBR0 at our table.
- Enable the MMU, then I-cache, then D-cache.

After this, our code runs out of DRAM with virtual = physical, but accessing cached memory is ~10× faster than before. We will measure.

## 17.2  Short-descriptor first-level entry, decoded

Each L1 entry is 32 bits:

```
 31      20  19   18   17   16  15  14:12   11:10   9    8:5   4   3 2  1:0
┌──────────┬────┬────┬────┬────┬────┬──────┬───────┬───┬──────┬───┬───┬─────┐
│ Sect base│ NS │  0 │ nG │ S  │ AP2│ TEX  │ AP    │IMP│Domain│ XN│ C B│ 1 0 │
│ [31:20]  │    │    │    │    │    │[2:0] │ [1:0] │   │      │   │    │type │
└──────────┴────┴────┴────┴────┴────┴──────┴───────┴───┴──────┴───┴───┴─────┘
```

(`type = 0b10` selects "section"; `type = 0b01` selects "page-table pointer" — not used here.)

(There are also other entry types: page-table pointer, supersection. We use only "section" — type bits = `0b10`.)

For our purposes, three fields matter most:

- **AP[2:0]** (Access Permissions) — combines AP2 (bit 15), AP[1:0] (bits 11:10). For "full access at PL1, no access at PL0," AP = `0b001` → AP2=0, AP[1:0]=01. For "full access at PL1 and PL0," AP = `0b011`.
- **TEX[2:0]C B** (memory attributes) — selects Device vs Normal-Strongly-Ordered vs Normal-Cacheable.
- **XN** (eXecute Never) — bit 4. Set to 1 for peripherals to prevent the CPU from speculatively fetching from MMIO.

Common combinations we will use:

| Region | TEX | C | B | XN | AP[2:0] | Meaning |
|--------|-----|---|---|----|---------|---------|
| Device (peripherals, GIC) | `000` | `0` | `1` | `1` | `001` | Device, non-shareable, no exec, PL1 RW |
| Normal Cacheable (OCRAM, DRAM) | `001` | `1` | `1` | `0` | `001` | Inner+outer write-back, allocate on write |
| Strongly-ordered (rare) | `000` | `0` | `0` | `1` | `001` | Most restrictive |

The full encoding tables are in ARM DDI 0406, section B3.7.

## 17.3  Building the L1 table

A 16 KiB array of 4096 32-bit entries. Aligned to 16 KiB (the MMU expects this).

`mmu.c`:

```c
#include <stdint.h>

#define REG(addr) (*(volatile uint32_t *)(addr))

/* Section entry type bits: 0b10 = section */
#define L1_TYPE_SECTION   (2u << 0)

/* TEX[2:0] C B encoding for memory attributes:
   - 0b000 0 1 : Device, shareable
   - 0b001 1 1 : Normal, inner+outer Write-Back, Write-Allocate */
#define L1_DEVICE         ((0u << 12) | (0u << 3) | (1u << 2))
#define L1_NORMAL_CACHE   ((1u << 12) | (1u << 3) | (1u << 2))

/* AP[2:0]: 0b011 = PL1 RW, PL0 RW; 0b001 = PL1 RW, PL0 none */
#define L1_AP_RW_KERNEL   ((0u << 15) | (1u << 10))     /* AP2=0, AP[1:0]=01 */

/* XN bit */
#define L1_XN             (1u << 4)

/* Domain field (bits 5:8): use domain 0 */
#define L1_DOMAIN0        (0u << 5)

/* L1 base attributes for our two main region types */
#define ATTR_DEVICE       (L1_TYPE_SECTION | L1_DEVICE      | L1_AP_RW_KERNEL | L1_XN | L1_DOMAIN0)
#define ATTR_NORMAL       (L1_TYPE_SECTION | L1_NORMAL_CACHE | L1_AP_RW_KERNEL | L1_DOMAIN0)

/* 16 KiB-aligned page table */
__attribute__((aligned(16384)))
static uint32_t l1_table[4096];

void mmu_build_table(void)
{
    /* Default: identity-map everything as Device, no access from PL0.
       We then overlay "Normal Cacheable" for the RAM regions. */
    for (uint32_t i = 0; i < 4096; i++) {
        uint32_t pa = i << 20;       /* section base = i * 1 MiB */
        l1_table[i] = pa | ATTR_DEVICE;
    }

    /* OCRAM at 0x00900000..0x0091FFFF (1 MiB section index 9). */
    l1_table[0x009] = (0x009u << 20) | ATTR_NORMAL;

    /* DRAM at 0x80000000..0x9FFFFFFF (512 MiB = 512 sections starting at index 2048). */
    for (uint32_t i = 2048; i < 2048 + 512; i++) {
        uint32_t pa = i << 20;
        l1_table[i] = pa | ATTR_NORMAL;
    }
}

/* CP15 helpers */
static inline void cp15_write_ttbr0(uint32_t v)
{
    asm volatile ("mcr p15, 0, %0, c2, c0, 0" :: "r"(v));
}

static inline void cp15_write_ttbcr(uint32_t v)
{
    asm volatile ("mcr p15, 0, %0, c2, c0, 2" :: "r"(v));
}

static inline void cp15_write_dacr(uint32_t v)
{
    asm volatile ("mcr p15, 0, %0, c3, c0, 0" :: "r"(v));
}

static inline uint32_t cp15_read_sctlr(void)
{
    uint32_t v;
    asm volatile ("mrc p15, 0, %0, c1, c0, 0" : "=r"(v));
    return v;
}

static inline void cp15_write_sctlr(uint32_t v)
{
    asm volatile ("mcr p15, 0, %0, c1, c0, 0" :: "r"(v));
}

static inline void invalidate_tlb_all(void)
{
    asm volatile ("mcr p15, 0, %0, c8, c7, 0" :: "r"(0));
    asm volatile ("dsb; isb");
}

static inline void invalidate_dcache_all(void)
{
    /* Set/way invalidate of L1 D-cache.  Cortex-A7 L1-D is 32 KB,
       4-way set-associative, 64-byte lines → 32768 / (4 × 64) = 128 sets.
       (Confirm at runtime by reading CCSIDR; we hardcode here for clarity.)
       set bits go in [12:6]; way bits in [31:30].  See ARM ARM B4.2.2. */
    for (uint32_t way = 0; way < 4; way++) {
        for (uint32_t set = 0; set < 128; set++) {
            uint32_t setway = (way << 30) | (set << 6);
            asm volatile ("mcr p15, 0, %0, c7, c6, 2" :: "r"(setway));
        }
    }
    asm volatile ("dsb");
}

static inline void invalidate_icache_all(void)
{
    asm volatile ("mcr p15, 0, %0, c7, c5, 0" :: "r"(0));
    asm volatile ("dsb; isb");
}

void mmu_enable(void)
{
    mmu_build_table();

    cp15_write_ttbr0((uint32_t)l1_table);     /* TTBR0 = &table */
    cp15_write_ttbcr(0);                       /* full TTBR0 control, no split */
    cp15_write_dacr(0x55555555);               /* every domain = "client" */
    invalidate_tlb_all();
    invalidate_dcache_all();
    invalidate_icache_all();

    uint32_t sctlr = cp15_read_sctlr();
    sctlr |= (1u << 0);   /* M: MMU enable */
    sctlr |= (1u << 2);   /* C: D-cache enable */
    sctlr |= (1u << 12);  /* I: I-cache enable */
    sctlr |= (1u << 11);  /* Z: branch prediction enable */
    cp15_write_sctlr(sctlr);
    asm volatile ("isb");
}
```

A few notes:

- **`__attribute__((aligned(16384)))`** ensures the table starts at a 16 KiB boundary, which TTBR requires. Skip it and TTBR drops the low 14 bits silently, leaving your MMU pointing at garbage.
- **`DACR = 0x55555555`** sets every domain to "client," which means accesses respect AP bits. The other valid value is "manager" (`0xFFFFFFFF`), which ignores AP entirely. Linux uses client; we follow.
- **Order matters at enable time.** Invalidate the caches *before* enabling them. Otherwise pre-MMU stale lines stay valid and corrupt your data.
- **The set/way D-cache invalidate** in `invalidate_dcache_all` uses the Cortex-A7 cache geometry: 32 KB L1-D, 4-way set-associative, 64-byte lines → **128 sets**, 4 ways. On a different CPU, look up the geometry from `CCSIDR`.

## 17.4  Calling `mmu_enable()`

After DDR is up and we've relocated to DRAM:

```c
int main(void)
{
    /* ... usual init ... */

    printf("Before MMU: memtest 4 MB ");
    uint32_t t0 = gpt_now_us();
    ddr_selftest();
    uint32_t t1 = gpt_now_us();
    printf("took %u us\r\n", t1 - t0);

    printf("Enabling MMU + caches...\r\n");
    mmu_enable();
    printf("MMU on.\r\n");

    printf("After MMU: memtest 4 MB ");
    t0 = gpt_now_us();
    ddr_selftest();
    t1 = gpt_now_us();
    printf("took %u us\r\n", t1 - t0);

    for (;;) {}
}
```

Expected output:

```
Before MMU: memtest 4 MB took 32500 us
Enabling MMU + caches...
MMU on.
After MMU: memtest 4 MB took 4100 us
```

Roughly an 8× speedup on the memtest. The exact ratio depends on the access pattern. Sequential memcpy can hit 10–15× with both caches on.

## 17.5  What just happened

After `mmu_enable()`:

- The 4 GiB virtual address space is mapped to physical 1:1 (we built an identity map).
- Accesses to peripherals (`0x02000000..0x021FFFFF`) go through the bus as Device, no caching, no reordering, non-speculative — exactly what MMIO needs.
- Accesses to OCRAM and DRAM are cached in L1 D-cache. Reads of recently-written addresses hit cache (~3 cycles vs ~30 cycles for DRAM).
- Instruction fetches are cached in L1 I-cache.
- Branch prediction is on.

For the rest of Part II, we leave the MMU on. Chapter 18's bare-metal peripherals work transparently — Device memory mapping ensures their MMIO behaves correctly.

## 17.6  Cache maintenance — when you must intervene

The MMU handles attributes; the cache handles its own coherency for ordinary loads/stores. But sometimes you must explicitly maintain:

- **Before a DMA peripheral reads from a buffer**, the CPU must **clean** the buffer's cache lines so the DMA sees the latest data.
- **After a DMA peripheral writes to a buffer**, the CPU must **invalidate** the buffer's cache lines so the next load sees the new data and not stale L1 contents.
- **After writing instructions**, the CPU must **clean D-cache** (so I-cache sees them in unified memory) and **invalidate I-cache** (so it re-fetches).

The CP15 ops by virtual address:

```c
static inline void dcache_clean_va(void *p)
{
    asm volatile ("mcr p15, 0, %0, c7, c10, 1" :: "r"(p));  /* DCCMVAC */
}

static inline void dcache_invalidate_va(void *p)
{
    asm volatile ("mcr p15, 0, %0, c7, c6, 1" :: "r"(p));   /* DCIMVAC */
}

static inline void dcache_clean_inv_va(void *p)
{
    asm volatile ("mcr p15, 0, %0, c7, c14, 1" :: "r"(p));  /* DCCIMVAC */
}

static inline void icache_invalidate_va(void *p)
{
    asm volatile ("mcr p15, 0, %0, c7, c5, 1" :: "r"(p));   /* ICIMVAU */
}
```

Granularity: one cache line (64 bytes on Cortex-A7). To clean a 4 KB buffer:

```c
void dcache_clean_range(void *start, size_t len)
{
    uintptr_t a = (uintptr_t)start & ~63;
    uintptr_t end = ((uintptr_t)start + len + 63) & ~63;
    for (; a < end; a += 64) dcache_clean_va((void *)a);
    asm volatile ("dsb");
}
```

We will use exactly these primitives in Part VI Chapter 51 when we write DMA drivers.

## 17.7  Why MMIO must be Device, not Normal Cacheable

If you accidentally map a peripheral region as Normal Cacheable:

- Writes get buffered. The peripheral sees them late.
- Reads return cached values. Status-register polling spins forever on stale data.
- Memory ordering is relaxed. Writes can be reordered relative to each other.

This is one of the hardest bugs to diagnose in low-level code. Symptoms: it works with MMU off and breaks when caches turn on. Cause: a peripheral region was wrongly marked cacheable.

Our `mmu_build_table()` defaults *every* unrecognized region to Device, which is the safe choice. We only explicitly mark RAM as Normal. This is the inverse of what some books suggest ("mark everything Normal and explicitly mark peripherals Device"). Our way is harder to misconfigure.

## 17.8  Performance measurement, in more detail

Add a microbenchmark:

```c
void bench_memcpy(void)
{
    static uint8_t src[4096], dst[4096];
    for (int i = 0; i < 4096; i++) src[i] = i & 0xFF;

    uint32_t cycles_before = pmu_ccnt();
    for (int n = 0; n < 1000; n++) {
        for (int i = 0; i < 4096; i++) dst[i] = src[i];
    }
    uint32_t cycles_after = pmu_ccnt();

    printf("memcpy 4 MB: %u cycles\r\n", cycles_after - cycles_before);
}
```

Run this before and after `mmu_enable()`. Typical results on Cortex-A7 @ 696 MHz:

| Config | Cycles for 4 MB | Effective MB/s |
|--------|----------------|----------------|
| No MMU, no caches | ~120 million | ~25 |
| MMU on, caches on | ~12 million | ~250 |

The 10× difference is why Linux brings caches up early in arch_setup.

## 17.9  Lab

1. **Build, run, observe speedup.** Confirm memtest goes from ~30 ms to ~4 ms.
2. **Try mapping DRAM as Device.** Change `mmu_build_table` to mark DRAM as Device. Re-run. The memtest will succeed but at ~25 ms (the slow-DRAM-access path); compare with no-MMU. Demonstrates that the MMU itself isn't the speedup — the cache attribute is.
3. **Try mapping peripherals as Normal Cacheable.** Predict the failure mode. Implement it. Observe — UART output may stop, or characters appear bunched, or `tick_ms()` stops advancing. **Restore.**
4. **Cache-line aliasing experiment.** Write to a buffer, then read it from a *different virtual address* that maps to the same physical address. (Construct this by adding a second mapping in your page table.) Confirm the read sees the right value despite VIPT cache being involved — Linux handles this for you in the page allocator; here you can see the issue raw.
5. **Implement `dcache_clean_range`** and verify with a flush-then-DMA-style pattern.

## 17.10  Pitfalls

- **Page table not 16 KiB aligned.** Symptom: enabling MMU traps to data abort. Cause: TTBR's low 14 bits are reserved zero; if your table address has any of them set, the actual base is silently truncated.
- **Forgetting `dsb; isb` around MMU/cache changes.** Required by the architecture. Symptom: works most of the time; fails intermittently.
- **Cache enabled with stale lines.** Invalidate before enable. Always.
- **Peripheral mapped Normal Cacheable.** Diagnosed above; pernicious. Bare-metal habit: peripheral writes always followed by a `dsb` if the next access depends on the write actually reaching the device.
- **Wrong cache geometry.** Cortex-A7 L1-D is **128 sets × 4 ways × 64-byte lines** (32 KB total). The exact geometry is in `CCSIDR`; portable code reads `CCSIDR` rather than hardcoding.
- **TTBCR misconfigured.** Setting `N != 0` splits the address space between TTBR0 and TTBR1. We use `N = 0` to put everything under TTBR0.
- **DACR with manager domain.** Manager-domain entries ignore AP. Useful for kernel; dangerous for user-facing code. Use "client" (0b01 per domain).

## 17.11  Going deeper

- **ARM DDI 0406**, sections B3.5 (short descriptor format) and B3.7 (memory attributes). The canonical reference.
- **ARM DEN 0013** — *Cortex-A Series Programmer's Guide*, Chapters 10 (caches) and 11 (MMU).
- **Linux source: `arch/arm/mm/proc-v7-2level.S`** and `arch/arm/mm/mmu.c`. The kernel version of what we just did.
- **`Documentation/arm/memory.txt`** in the Linux kernel tree. Describes the virtual memory layout.
- *Computer Architecture: A Quantitative Approach* (Hennessy & Patterson), Chapter 5, for the cache theory.

> Next chapter: **Chapter 18 — Optional bare-metal peripherals.** I²C and SPI bare-metal, just enough to prove we can. Chapter 18 ends the required path of Part II. After that, three supplementary chapters (18A Project organization, 18B Button + beep, 18C Bare-metal RTC) are inserted for readers who want to fully match the Point Atom-style depth of bare-metal coverage before moving to U-Boot in Part III. They are independent of each other; skip any.
