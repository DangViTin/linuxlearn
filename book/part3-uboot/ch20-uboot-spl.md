---
chapter: 20
title: U-Boot SPL — the missing link
part: III — U-Boot, deeply
estimated_pages: 18
status: draft
---

# Chapter 20 — U-Boot SPL: the missing link
**IRQ** - interrupt request, the signal path that tells the CPU or interrupt controller that hardware needs service.
**PLL** - Phase-Locked Loop, a clock block that multiplies a reference clock to create faster clocks.
> **MCU bridge:** Think of a PLL like the clock multiplier setup you used on STM32, but with more clock roots, gates, and consumers that Linux later needs to describe.
**CCM** - Clock Controller Module. It selects clock sources, dividers, and gates for the SoC.

> **What:** the **SPL** (Secondary Program Loader) — the first stage of the two-stage U-Boot — explained in enough detail that you can read its source and modify it for a custom board.
> **SPL** - Secondary Program Loader, a tiny first U-Boot stage that fits in OCRAM and initializes DDR.
> **U-Boot** - the bootloader that initializes enough hardware to load and start the Linux kernel.
>
> **Why:** The i.MX6ULL OCRAM is 128 KB at `0x00900000`. The Boot ROM reserves the bottom ~28 KB (`0x00900000–0x00906FFF`) for its own scratch space. That leaves a ~68 KB window for SPL (`0x00907000–0x0091FFFF`). Full U-Boot is ~600 KB and does not fit. SPL is the small first-stage program that bridges the gap: it brings up DRAM, loads full U-Boot into DRAM, and jumps to it. Mechanically, SPL is the production version of Chapters 11–14.
> **FIT** - Flattened Image Tree, U-Boot's container format for kernels, DTBs, initramfs images, hashes, and signatures.
>
> **Focus:** the **size constraint** as a design pressure. NXP's `mx6ull_14x14_evk_defconfig` caps `CONFIG_SPL_MAX_SIZE` near **64 KB** with a small reserve. treat that as your ceiling. Every feature pays for itself in bytes. Understanding what SPL chooses to include and what it skips is how you understand what is and isn't expected to work in the first 100 ms of a board's life.


## 20.1  Why two stages

If you have read Chapters 7, 11, and 14, you already know the constraint: the Boot ROM reads a fixed amount of bytes into a fixed location in OCRAM, then transfers control. Full U-Boot does not fit.

Three possible solutions:

1. **DCD-driven big load.** Put DRAM init into the DCD. The ROM then loads U-Boot directly into DRAM, bypassing OCRAM size limits. This works and was the dominant pattern in the i.MX5 era. Mainline U-Boot for i.MX6 has moved away from it. The DCD becomes unwieldy at ~800 bytes and is hard to maintain when DRAM timings change.
**DCD** - Device Configuration Data: ROM-executed register writes that prepare clocks and DDR before your code runs.
2. **Multi-stage boot with SPL.** ROM loads a small SPL into OCRAM. SPL initializes DRAM. SPL loads the full U-Boot from the boot medium into DRAM. SPL jumps to it. Mainline does this.
3. **Static link to a small U-Boot.** Strip features until U-Boot fits in ~64 KB. Has been done. Painful.

Mainline uses Pattern 2: two stages, one for setup, one for the main work. The same pattern repeats up the stack — U-Boot loads Linux, Linux loads `/sbin/init`. Each stage has more resources than the one before.

## 20.2  What SPL is responsible for

The SPL's job, in order:

1. **CPU init.** Mode-set to SVC, vectors, stack pointer in OCRAM. (Your Chapter 10.)
2. **Clock init.** PLLs, AHB/IPG bus, CCGR gates for what SPL needs. (Your Chapter 13.)
3. **DRAM init.** MMDC setup with timings for the specific DRAM part. (Your Chapter 14.)
**MMDC** - the i.MX6ULL DDR controller block that owns timing, calibration, and DRAM command sequencing.
**DDR** - external DRAM that must be configured and trained before most software can run from it.
4. **Console init.** UART so we can see what's happening. (Your Chapter 12.)
5. **Boot-medium init.** Driver for SD/eMMC/NAND/SPI-NOR — whichever the strap pins indicate.
6. **Load full U-Boot.** Read the second-stage image from the boot medium into DRAM at a known address.
7. **Jump to it.** Branch to the loaded image. full U-Boot takes over.

That is the whole list. SPL does not run the kernel, handle networking, or offer a command prompt. It is the smallest program that can do the seven steps above on this hardware.

## 20.3  The size budget

For i.MX6ULL, the Boot ROM's effective load window for SPL is **~64 KB** of usable OCRAM (the chip has 128 KB at `0x00900000`, but the ROM reserves the bottom ~28 KB for its scatter buffers and working state, and `CONFIG_SPL_MAX_SIZE` in `mx6ull_14x14_evk_defconfig` is set to about 64 KB). The mainline SPL builds at roughly **40 KB**. The headroom exists, but the discipline is mandatory.

Configuration items that respect the budget:

```
CONFIG_SPL=y
CONFIG_SPL_LIBCOMMON_SUPPORT=y
CONFIG_SPL_LIBDISK_SUPPORT=y
CONFIG_SPL_MMC=y
CONFIG_SPL_DM=y                    # driver model in SPL (minimal)
CONFIG_SPL_OF_CONTROL=y            # SPL also uses device tree
CONFIG_SPL_DM_MMC=y
CONFIG_SPL_GPIO=y
CONFIG_SPL_SERIAL=y
# CONFIG_SPL_NET is NOT set        # SPL doesn't need network
# CONFIG_SPL_USB_HOST is NOT set
```

For every feature, the build system has both `CONFIG_FOO` (for full U-Boot) and `CONFIG_SPL_FOO` (for SPL). Turning off `CONFIG_SPL_FOO` keeps `FOO` in full U-Boot but excludes it from SPL. This is how SPL stays small.

The current size is reported at the end of build:

```
$ size spl/u-boot-spl
   text	   data	    bss	    dec	    hex	filename
  39204	   1872	   8112	  49188	   c024	spl/u-boot-spl
```

If `text + data + bss > CONFIG_SPL_MAX_SIZE` (~64 KB on the EVK defconfig), the build usually warns. The warning is not reliable under every linker config, so always check with `size` after a change. If SPL exceeds the OCRAM window, the ROM silently refuses to load it.

## 20.4  Where SPL lives in the source

```
common/spl/                    # the SPL framework
├── spl.c                      # generic entry, board_init_r/f, weak hooks
├── spl_mmc.c                  # MMC boot-medium loader
├── spl_nand.c                 # NAND boot-medium loader
├── spl_spi.c                  # SPI-NOR boot-medium loader
├── spl_fit.c                  # FIT image support inside SPL
└── ...
arch/arm/cpu/armv7/
├── start.S                    # SPL/U-Boot shared startup asm
├── lowlevel_init.S            # earliest C-callable code
└── ...
arch/arm/mach-imx/
├── spl.c                      # i.MX-family SPL hooks
└── mx6/
    └── ddr.c                  # the MMDC driver SPL relies on
board/freescale/mx6ull_14x14_evk/
├── spl.c                      # board-specific SPL: which DDR, which pinmux
└── mx6ull_14x14_evk.c         # full U-Boot's board code
```

The SPL is built as a separate binary from these files. The flow:

```
                       Boot ROM
                          │ loads SPL (~40 KB) into OCRAM @ 0x00907400
                          ▼
                       start.S      (CPU init: stack, mode, vectors)
                          │
                          ▼
                  lowlevel_init.S   (very-early C-callable hooks)
                          │
                          ▼
                   board_init_f     (in common/spl/spl.c; "front-end")
                          │
                          ├──► arch_cpu_init        (CCM, clocks)
                          ├──► spl_dram_init        (MMDC bring-up)
                          ├──► preloader_console_init
                          ▼
                   board_init_r     (in common/spl/spl.c; "rear-end")
                          │
                          ├──► spl_mmc_load_image  (read u-boot.imx from SD)
                          │            │
                          │            └──► copy to DRAM @ 0x87800000
                          ▼
                   jump_to_image_no_args
                          │ branches to the loaded U-Boot
                          ▼
                   (full U-Boot now running in DRAM)
```

Each file reads in under 10 minutes. Together they are a clean reference for a bootloader's first stage.

## 20.5  Reading `start.S`

Open `arch/arm/cpu/armv7/start.S`:

```asm
ENTRY(reset)
    /* Allow the board to save important registers */
    b   save_boot_params

    .globl  save_boot_params_ret
save_boot_params_ret:
    /*
     * disable interrupts (FIQ and IRQ), also set the cpu to SVC32 mode,
     * except if in HYP mode already
     */
    mrs r0, cpsr
    and r1, r0, #0x1f       @ mask mode bits
    teq r1, #0x1a           @ test for HYP mode
    bicne   r0, r0, #0x1f   @ clear all mode bits
    orrne   r0, r0, #0x13   @ set SVC mode
    orr r0, r0, #0xc0       @ disable FIQ and IRQ
    msr cpsr,r0

    /* the mask ROM code should have PLL and others stable */
    bl  cpu_init_cp15
    bl  cpu_init_crit
    bl  _main
```

You wrote almost every line of this in Chapter 10's `startup.S`. The differences:

- `save_boot_params` is a hook the SoC family uses to capture boot-mode info the ROM leaves in registers. We never needed it in bare-metal.
- The HYP-mode check is for Cortex-A15+ which can boot in hypervisor mode. The Cortex-A7 on i.MX6ULL does not have HYP, so the check is a no-op for us.
- `cpu_init_cp15` configures cache and MMU registers to a known state.
> **MCU bridge:** Think of the MMU as a hardware address translator in front of every load/store. Cortex-M usually runs physical addresses directly. Linux relies on virtual addresses and page permissions.
**MMU** - Memory Management Unit, hardware that translates virtual addresses to physical addresses and enforces permissions.
- `cpu_init_crit` does very-early board-critical init (memory remapping, system control register tweaks).
- `_main` (defined in `arch/arm/lib/crt0.S`) is the C-runtime entry — sets up the stack, then calls `board_init_f`.

The structure matches ours. Production U-Boot adds the safety nets and SoC-family abstractions we skipped because we targeted only one SoC.

## 20.6  `board_init_f` — the "before relocation" stage

The "f" stands for "flash" (historical — back when U-Boot ran first from flash, before it relocated itself to RAM). In SPL, `board_init_f` runs from OCRAM and its job is "set up everything DRAM needs":

```c
void board_init_f(ulong dummy)
{
    arch_cpu_init();           /* clocks, etc. */
    timer_init();              /* GPT-based timer */
    preloader_console_init();  /* UART up; printf works */
    spl_dram_init();           /* THE BIG ONE: DRAM up */
    memset(__bss_start, 0, __bss_end - __bss_start);  /* zero .bss */
    board_init_r(NULL, 0);     /* hand off to next stage */
}
```

Five calls. Each is a chapter from Part II.

`board_init_f` does not return. It tail-calls `board_init_r`, which also never returns. SPL keeps running until it jumps to U-Boot. The `board_init_f` stack frame is reused by `board_init_r`.

## 20.7  `board_init_r` — the "after relocation" stage

The "r" originally meant "RAM" — after relocation to RAM. In SPL, there is no relocation (SPL stays in OCRAM throughout its life). The name is kept for symmetry with full U-Boot, where the distinction matters (Chapter 21).

In SPL, `board_init_r` (defined in `common/spl/spl.c`):

```c
void board_init_r(gd_t *dummy1, ulong dummy2)
{
    /* ... */
    struct spl_image_info spl_image;
    int ret = spl_load_image(BOOT_DEVICE_MMC1, &spl_image);
    if (ret)
        hang();
    jump_to_image_no_args(&spl_image);
}
```

`spl_load_image` dispatches to the right loader based on the boot device:

- `BOOT_DEVICE_MMC1` → `spl_mmc_load_image` → reads `u-boot.imx` from SD card LBA 138 (= `seek=69` in 1 KB blocks)
- `BOOT_DEVICE_NAND` → `spl_nand_load_image`
- `BOOT_DEVICE_SPI` → `spl_spi_load_image`
- `BOOT_DEVICE_USB` → `spl_usb_load_image` (for USB SDP recovery)

The loader copies bytes to `spl_image.load_addr` (typically `0x87800000`, near the top of DRAM). Then `jump_to_image_no_args`:

```c
typedef void __noreturn (*image_entry_noargs_t)(void);
void jump_to_image_no_args(struct spl_image_info *spl_image)
{
    image_entry_noargs_t entry = (image_entry_noargs_t)spl_image->entry_point;
    entry();
}
```

The handoff is one C statement: cast the load address to a function pointer and call it. The next instruction executed is full U-Boot's `_start`, but now running from DRAM. SPL's OCRAM stack and code are discarded.

## 20.8  Comparing SPL to your Ch 11 image-builder

Bring up your `mkimx.py` from Chapter 11. The output of that tool is an `.imx` file:

- A 1 KB pre-pad
- An IVT
- Optional DCD (we didn't use one in Ch 11)
- BootData
- Padding to offset `0x1000`
- The code

When U-Boot builds `SPL`, it produces an `.imx` file with **exactly the same structure**. Run:

```sh
$ xxd -s 0x400 -l 32 SPL
00000400: d100 2040 0000 7880 0000 0000 0000 0000  .. @..x.........
00000410: 0090 0900 0000 7780 0000 0000 0000 0000  ......w.........
```

Decode:

- Magic `D1 00 20 40` ✓
- Entry `0x80780000` — a **DRAM** address. That tells us this file is **not** the SPL. It's *full U-Boot's* `.imx`, which loads to DRAM. The dump above is from `u-boot.imx`, not `spl/u-boot-spl.imx`.

The SPL's `.imx` is a different file. To inspect it:

```sh
$ xxd -s 0x400 -l 32 spl/u-boot-spl.imx     # name varies by U-Boot version
```

If that file doesn't exist, look for `MLO` or `u-boot-spl-dtb.imx` in the build root, or run `find . -name "*.imx" -ls` to enumerate the IVT-bearing artifacts. When you find the correct SPL file, its IVT will have:

- `entry`        = somewhere in OCRAM (`~0x00908000`)
- `self`         = same OCRAM region (the IVT's own load address)
- `BootData.start`  = OCRAM load address (`~0x00907400`)
- `BootData.length` = SPL size + headers

Identical structure to your Chapter 11 output, just with OCRAM addresses instead of DRAM addresses.

**Does SPL have a DCD?** It can, but on i.MX6ULL it usually doesn't need one — and that is the deliberate design choice:

- The ROM runs the DCD (if present) *before* it transfers control to the loaded image. The DCD's job is to configure whatever pads, clocks, or registers the loaded image *cannot configure for itself* — typically DDR, so the image can be loaded into DRAM.
- **SPL is loaded into OCRAM, not DRAM.** So the DCD doesn't need to bring up DDR before loading SPL. SPL's *own C code* (the C function `spl_dram_init` / `mx6_dram_cfg`) brings up DDR — that's literally Ch 14 productized.
- The SPL `.imx`'s DCD is therefore typically empty or near-empty, and full U-Boot's `.imx` doesn't have a meaningful DCD either (full U-Boot is loaded by SPL into DRAM that SPL just brought up).

Compare your SPL's DCD against the EVK board's `.cfg` file (`board/freescale/mx6ull_14x14_evk/mx6ull_14x14_evk.cfg`) to see what is actually written.

## 20.9  The SPL-to-U-Boot handshake

When SPL loads full U-Boot, it passes information through a small structure called the **`spl_image_info`**:

```c
struct spl_image_info {
    const char *name;
    u8 os;                 /* IH_OS_U_BOOT, IH_OS_LINUX, ... */
    uintptr_t load_addr;   /* where the image was loaded */
    uintptr_t entry_point; /* where to jump */
    u32 size;
    u32 flags;
    /* ... */
};
```

Full U-Boot, on entry, *does not consult* `spl_image_info` directly (the structure is in SPL's OCRAM-resident memory, which U-Boot is about to overwrite). Instead, SPL has already arranged for the right things to be true:

- Full U-Boot's code is at `entry_point` in DRAM.
- DRAM is alive (SPL did it).
- The cache is in a known state (SPL flushed/disabled before jumping).
- The stack is wherever full U-Boot's `_main` decides.

Full U-Boot's `_main` then proceeds with *its* `board_init_f` → relocation → `board_init_r` → main loop. We trace this in Chapter 21.

## 20.10  Lab

1. **Find your SPL.** After your Chapter 19 build, locate the SPL ELF and its `.imx` wrapper. Use `size` to see how big each section is.
**ELF** - Executable and Linkable Format, the standard Linux object and executable file format.
2. **Read `board/freescale/mx6ull_14x14_evk/spl.c` end-to-end.** Annotate which functions you wrote analogues of in Part II and which are new.
3. **Trace one DDR register write.** Pick `MDCFG1` (Chapter 14's tRP/tRAS/tRC/tWR setting). Find where it's set in `arch/arm/mach-imx/mx6/ddr.c`. Compare to your Chapter 14 constant.
4. **Shrink the SPL.** In `make menuconfig`, disable an unused SPL feature (e.g., `CONFIG_SPL_USB_GADGET`). Rebuild. Note the change in `size spl/u-boot-spl`.
5. **Break the SPL deliberately.** Edit `board/freescale/mx6ull_14x14_evk/spl.c`'s `spl_dram_init` to write a bogus value (e.g., `MDCFG1 = 0;`). Rebuild, flash, boot. Observe the freeze. *Restore.*
6. **Reset cause investigation.** Boot, then immediately reset (button or short PWR). Compare the "Reset cause: ..." line on the second boot vs. The first. (POR vs. WDOG-RESET, etc.)

## 20.11  Pitfalls

- **`spl/u-boot-spl-dtb.bin` vs `spl/u-boot-spl-dtb.imx`.** The first is the raw SPL. The second is wrapped with an IVT for the Boot ROM. Use the second for SD-boot.
- **Mixing SPL and full-U-Boot defconfigs.** They share one `.config`. The same defconfig builds both stages. You can't have separate configs without significant work.
- **Forgetting that SPL has its own device tree.** SPL uses a *cut-down* DT — `u-boot-spl.dts` if defined — that only describes peripherals SPL actually uses. Adding a DT node for full U-Boot does not automatically make it visible to SPL.
- **Out-of-bounds OCRAM access.** SPL has ~64 KB of usable OCRAM (the lower ~28 KB belongs to the Boot ROM). If you accidentally grow it (large global arrays, large stack frames), boot fails silently — the image is bigger than the ROM expects.
- **Cache state at handoff.** If SPL leaves caches dirty, full U-Boot may not see what SPL wrote. The standard pattern is `cleanup_before_linux()`-equivalent before jumping — clean caches, disable MMU. Mainline does this. If you hand-edit you must too.
- **Calling SPL functions from full U-Boot.** They don't exist there — different binary, different memory map. Build errors usually catch this. runtime errors when they don't.

## 20.12  Going deeper

- **`doc/README.SPL`** in the U-Boot source — the canonical SPL doc.
- **`common/spl/spl.c`** — the generic SPL framework. ~600 lines. Read it.
- **`arch/arm/mach-imx/spl.c`** — i.MX-family SPL. ~400 lines.
- **`board/freescale/mx6ull_14x14_evk/spl.c`** — board-specific SPL. ~500 lines.
- **`arch/arm/mach-imx/mx6/ddr.c`** — the production DDR3 driver for i.MX6. This is the file to read alongside our Chapter 14.
- **AN5331** — *Programming NAND Flash with U-Boot on the i.MX 6/7 series* (for NAND-boot SPL flows).

> Next chapter: **Chapter 21 — U-Boot internals.** Now that we have SPL loading full U-Boot, we follow full U-Boot through reset → relocation → `main_loop`, and trace the command dispatcher that runs when you type at the `=>` prompt.
