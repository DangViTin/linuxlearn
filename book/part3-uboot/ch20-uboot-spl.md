---
chapter: 20
title: "U-Boot SPL: the missing link"
part: III - U-Boot, deeply
estimated_pages: 18
status: draft
---

# Chapter 20: U-Boot SPL: the missing link

Chapter 19 left us with a large U-Boot image and a small question: how could
the ROM load it into DDR before U-Boot's C code had initialized that DDR?

For the EVK configuration, the answer was the DCD. The ROM interpreted its
register writes first. Another board can give that job to a small program
instead. That program is **SPL**, the Secondary Program Loader.

SPL is an alternative boot stage, not a file missing from our EVK build.
Knowing which route you have is more useful than memorizing a universal
"ROM, SPL, U-Boot" diagram. We will read an actual SPL implementation, then
compare its responsibilities with the EVK's ROM-driven setup.

## 20.1  Why two stages

DDR cannot hold a useful stack or executable image until its controller,
pads, clocks, and memory device have been configured. The startup program
must therefore begin in memory that is already usable.

Two routes solve that dependency on this SoC family:

```{figure} ../illustrations/part3/02-two-ddr-boot-routes.png
:alt: The EVK route lets the ROM run DCD writes before U-Boot in DDR. The SPL route runs a small program in OCRAM to initialize DDR first.
:name: fig-p3-ddr-boot-routes
:figclass: concept-sketch
:width: 100%

Follow the point where DDR becomes usable. The upper route assigns that work to ROM-interpreted data. The lower route assigns it to SPL code. Both still need the correct board settings.
```

| Route | Who prepares DDR? | Where the first application code runs |
|-------|-------------------|--------------------------------------|
| EVK ROM + DCD | The Boot ROM executes the image's DDR setup data | Full U-Boot begins in DDR |
| ROM + SPL | A small executable runs its board-specific DDR setup | SPL begins in internal RAM, then loads full U-Boot into DDR |

Both routes still need correct board-specific DDR values. Moving the writes
from a DCD into C does not remove the electrical or calibration work from
Chapter 14. It changes where that knowledge is expressed and how much software
can run before the large image is loaded.

Some SPL configurations can select among memory arrangements, perform more
complex initialization, authenticate a payload, or boot an OS directly. Those
are configured features, not promises made by the name SPL.

## 20.2  What SPL is responsible for

For a typical i.MX6-family SPL loading full U-Boot, the responsibilities are:

1. Establish a usable CPU mode, early stack, and global-data area.
2. Prepare the clock and pad paths needed by its console, DDR, and boot medium.
3. Initialize the fitted DDR arrangement.
4. Initialize the selected SD, eMMC, SPI, or other loader path.
5. Read and interpret the configured payload format.
6. Place that payload at its load address and transfer control to its entry.

A console is often made available before DDR setup so that an early failure
can be reported. The exact order belongs to the board implementation. Do not
reorder the calls just to make them resemble a generic diagram.

Likewise, "SPL cannot use networking" is too broad. Some builds include it.
The usual engineering question is whether a feature is needed before the
larger runtime is available, and whether its memory and dependencies fit.

## 20.3  The size budget

The i.MX6ULL has 128 KiB of OCRAM. That physical capacity is not a promise that
all 128 KiB are available to a loaded program. ROM activity, image placement,
the early stack, global data, and any early allocation pool also need space.
Use the selected image format, ROM constraints, configuration, and linker map
together. Do not infer a free window by subtracting an approximate reservation
quoted for another board.

For the reference SPL used below, `CONFIG_SPL_MAX_SIZE` is `0x10000`, or
64 KiB. The Kconfig help describes this as the image limit **excluding BSS**.
That is different from a limit on `text + data + bss + stack`.

In this family, an SPL may place BSS in DDR and clear it only after DDR setup.
The early code must not use that BSS while DDR is unavailable. Its OCRAM code
and stack budget and its later DDR budget are separate checks.

Record these fields from the generated configuration rather than copying
another build's size report:

| Field or file | Check |
|---------------|-------|
| `CONFIG_SPL_TEXT_BASE` | Where SPL code is linked |
| `CONFIG_SPL_MAX_SIZE` | Which loadable image limit the linker checks |
| SPL stack selection | Where the early stack begins and what lies below it |
| `CONFIG_SPL_BSS_START_ADDR` and `CONFIG_SPL_BSS_MAX_SIZE` | Where BSS lives and when that memory becomes usable |
| `spl/u-boot-spl.map` | Actual linked ranges and reservations |
| `spl/u-boot-spl` | ELF section sizes and addresses |
| `SPL` | The ROM-facing packaged file, including its header |

Not every feature has a one-to-one `CONFIG_SPL_FOO` switch. Dependencies,
shared framework code, and stage-specific defaults matter too. Inspect the
expanded configuration after changing a feature.

## 20.4  Where SPL lives in the source

We need a real SPL-enabled configuration to read. In the same v2026.04 tree,
use **`pico-imx6ul_defconfig`** as a separate host-side reference. It describes
a TechNexion PICO i.MX6UL platform, not the i.MX6ULL EVK and not our MINI.
**Do not flash its outputs to either board.**

```sh
$ . ~/imx6ull/scripts/env.sh
$ cd ~/imx6ull/src/u-boot
$ make O="$HOME/imx6ull/build/uboot-pico-study" pico-imx6ul_defconfig
$ make O="$HOME/imx6ull/build/uboot-pico-study" -j4
$ arm-none-linux-gnueabihf-size \
    ~/imx6ull/build/uboot-pico-study/spl/u-boot-spl
```

The different `O=` directory keeps this configuration out of our EVK build.
The Arm-prefixed `size` program reads the target ELF on the host. It does not
execute it. Its BSS count is useful, but does not describe stack usage or all
packaging overhead.

Read these source files with the generated `.config` beside them:

| Path | Responsibility |
|------|----------------|
| `board/technexion/pico-imx6ul/spl.c` | This board's early setup, DDR data, and MMC setup |
| `arch/arm/cpu/armv7/start.S` | Shared ARMv7 CPU startup |
| `arch/arm/lib/crt0.S` | Early C-runtime arrangements and stage-dependent paths |
| `common/spl/spl.c` | SPL framework and boot-device selection |
| `common/spl/spl_mmc.c` | MMC payload loading |
| `arch/arm/mach-imx/mx6/ddr.c` | Shared MMDC configuration routines |
| `common/spl/Kconfig` | Stage limits, formats, and loader defaults |

An SPL file appears only when the build includes that stage. Looking for TI's
`MLO`, or guessing an `.imx` filename, is not a way to repair a no-SPL EVK build.

## 20.5  Reading `start.S`

Open `arch/arm/cpu/armv7/start.S`, then follow its branch into `_main` in
`arch/arm/lib/crt0.S`. The names are familiar from Part II, but the framework
must accommodate more than our one experiment.

| Startup work | What to look for |
|--------------|------------------|
| Preserve incoming boot information | `save_boot_params` and its return label |
| Select or respect CPU mode, mask IRQ/FIQ | The CPSR manipulation and conditional mode check |
| Establish architecture state | `cpu_init_cp15` and the selected critical-init path |
| Make early C calls possible | Initial stack selection, alignment, and global-data reservation in `_main` |
| Enter board setup | The call to `board_init_f` |

The generic mode check is not evidence that this board normally enters in HYP
mode. The handoff policy depends on the ROM or preceding firmware and the
selected platform. Similarly, masking IRQ and FIQ does not make bad memory
accesses harmless.

Notice the explicit `r9` global-data setup in `crt0.S`. A stack alone is not
the whole early environment. The framework gives early code a place to retain
state even before its normal runtime is ready.

In v2026.04, assembly and shared code use `CONFIG_XPL_BUILD` for these small
loader stages. Older excerpts may say `CONFIG_SPL_BUILD`. Read the pinned tree's
conditions, not just a function with a familiar name.

## 20.6  `board_init_f`, the "before relocation" stage

The PICO implementation's sequence can be summarized as:

```text
clock gates
    -> architecture and board early setup
    -> timer
    -> preloader console
    -> board DDR configuration
    -> BSS clear
    -> SPL board_init_r
```

This is a reading map, not replacement code. Open the actual function to see
the calls and the DDR data they use.

The order explains something important: this implementation clears BSS after
DDR setup because its BSS location is in DDR. That region is not available for
an early timeout counter merely because the C declaration compiled.

Also notice that this board's `board_init_f` calls `board_init_r` directly.
Other SPL implementations return to `crt0.S`, which completes the stage's
runtime setup. **The chosen board path decides.** A direct call is not a
universal rule that every function named `board_init_f` never returns.

Find the PICO DDR geometry and calibration structures, then follow the call
to `mx6_dram_cfg`. They are examples of how one supported board supplies data
to common MMDC code. They are not calibration results for our MINI.

## 20.7  `board_init_r`, the "after relocation" stage

Full U-Boot uses this name for its post-relocation runtime. SPL keeps the name
for its later framework phase, even when its code has not relocated.

Follow `board_init_r` in `common/spl/spl.c` into boot-order selection, registered
loaders, and the selected image-loading function. The framework is not simply
a hard-coded call with `BOOT_DEVICE_MMC1` on every board.

For the PICO raw-MMC reference, inspect
`CONFIG_SYS_MMCSD_RAW_MODE_U_BOOT_SECTOR`. The family default is `0x8A`:

```text
0x8A = 138 sectors
138 * 512 bytes = 70656 bytes = 69 KiB
```

That explains an offset you may have seen in other i.MX6 SPL instructions.
It does **not** change the EVK image placement in Chapter 19. The loader's
expected payload format matters as well: a legacy `u-boot.img`, a FIT, and a
ROM-facing DCD image are not interchangeable just because they contain U-Boot.

The loader records a load address, entry address, and size in
`struct spl_image_info`. On success, the selected handoff enters that payload.
On failure, the configured boot order may try another supported loader or stop.
Find the actual error path before interpreting a later boot message.

## 20.8  Comparing SPL to your Ch 11 image-builder

Our Chapter 11 file included a leading pad, an IVT at file offset `0x400`,
BootData, a header gap, and an OCRAM payload. U-Boot's packaged `SPL` has its
own placement convention. Inspect the artifact rather than assuming that its
name implies the same leading pad.

```sh
$ xxd -l 32 ~/imx6ull/build/uboot-pico-study/SPL
$ ~/imx6ull/build/uboot-pico-study/tools/mkimage -l \
    ~/imx6ull/build/uboot-pico-study/SPL
```

For this packaged SPL, examine the IVT at file byte zero. Its entry and self
pointers refer to internal RAM rather than the DDR entry of the EVK image.
Use the image tool and selected configuration to interpret the remaining
fields. Do not substitute the entry from a full-U-Boot `.imx` dump.

The tool may print `Mode: DCD` for both files. In this implementation that
label distinguishes the non-plugin header mode, not proof that a DDR setup
table is present. The PICO wrapper selected by `arch/arm/mach-imx/spl_sd.cfg`
does not supply the EVK's DDR writes. Check the actual DCD pointer and table
before deciding who initialized memory.

An OCRAM-loaded SPL does not need the ROM to initialize DDR just to load the
SPL itself. Its own board code can do that afterward. A DDR-loaded full image
does need DDR before it can execute, which is why the EVK supplies a DCD.

The meaningful comparison is the dependency, not an identical filename or
an identical amount of padding:

> Which memory must already work before the next instruction can be fetched?

## 20.9  The SPL-to-U-Boot handshake

`spl_image_info` is the SPL loader's record. It tells the handoff where an image
was placed and where to enter it. It is not automatically an argument that full
U-Boot reads from the SPL's old stack.

The payload also depends on established state:

- Its code and required data must actually be present in usable memory.
- Its load and entry addresses must agree with the selected format and build.
- Memory writes must be visible to the instruction-fetch path when needed.
- CPU mode, caches, MMU, and device state must satisfy the selected entry path.

The exact cache-maintenance and jump behavior belongs to the selected loader,
architecture, and configuration. Do not infer that every SPL automatically
performs `cleanup_before_linux()` before every possible handoff. Read the
selected `jump_to_image_no_args` implementation and any board override.

Some configurations provide additional handoff records through facilities such
as a blob list. Those are separate interfaces. For our reading exercise, trace
the normal full-U-Boot entry into `crt0.S`; it establishes its own runtime
instead of treating the preceding program's stack as its permanent stack.

## 20.10  Lab

1. Confirm that the EVK build has no SPL and the separate PICO study build does.
   Record the two output-directory names so the artifacts cannot be confused.
2. Read the complete PICO `board_init_f`. Mark which memory is usable at each
   call, and find the moment its DDR-resident BSS becomes usable.
3. Inspect the SPL ELF with the Arm `size` and `readelf -S` tools. Compare its
   linked sections with the configuration limits and map file.
4. Inspect the packaged `SPL` header. Compare its memory pointers and file
   layout with the EVK image and the Chapter 11 builder.
5. Trace one raw-MMC loader setting from Kconfig to `.config` to its use in
   `common/spl/spl_mmc.c`. State its units and expected payload format.
6. In a separate experimental output directory, change one understood SPL
   feature through `menuconfig`, rebuild, and compare the map and sizes. Keep
   this host-side. Do not flash a PICO image or deliberately corrupt DDR timings.

## 20.11  Pitfalls

- **Looking for SPL in every build.** Check `CONFIG_SPL` first. Our EVK does not
  use it, and a missing file there is expected.
- **Treating 64 KiB as the whole runtime budget.** The loadable image limit,
  BSS location, early stack, header, and allocation pool are different facts.
- **Accessing DDR-resident BSS before DDR setup.** Successful compilation says
  nothing about whether that address is usable at that moment.
- **Copying another board's DDR structures.** They describe its memory and
  calibration, not a generic i.MX6UL/ULL memory device.
- **Using full-U-Boot DT assumptions for SPL.** Stage filtering and available
  drivers determine what an SPL can bind and probe. Inspect the stage's output.
- **Guessing handoff cleanup.** Follow the actual path and its ownership rules.
  A function-pointer call does not by itself synchronize cached instructions.

## 20.12  Going deeper

- [SPL development documentation](https://docs.u-boot.org/en/v2026.04/develop/spl.html).
- [Pinned PICO configuration](https://github.com/u-boot/u-boot/blob/v2026.04/configs/pico-imx6ul_defconfig).
- [PICO board SPL](https://github.com/u-boot/u-boot/blob/v2026.04/board/technexion/pico-imx6ul/spl.c).
- [SPL Kconfig limits and loader settings](https://github.com/u-boot/u-boot/blob/v2026.04/common/spl/Kconfig).
- [The common ARM runtime entry](https://github.com/u-boot/u-boot/blob/v2026.04/arch/arm/lib/crt0.S).

Next we return to full U-Boot. Whether the ROM or an SPL made DDR usable, the
large program still has to arrange its own stack, relocation, devices, and shell.
