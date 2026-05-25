---
chapter: 19
title: U-Boot from source — first boot
part: III — U-Boot, deeply
estimated_pages: 16
status: draft
---

# Chapter 19 — U-Boot from source, first boot

> **What:** clone mainline U-Boot, build it for the i.MX6ULL, `dd` the result to an SD card, boot it, get a `=>` prompt. Then run a few commands and recognize, in U-Boot's output, every step we did by hand in Chapters 9–17.
> **Why:** Part II proved we can boot the chip ourselves. From here on the question is no longer "can we?" but "what does the professional version of this work look like?" U-Boot is that version. Reading its source is the most concentrated lesson in real-world embedded-Linux engineering available.
> **Focus:** **recognition**. By the end of Part III you should be able to point at any line of U-Boot's `arch/arm/cpu/armv7/start.S` or `arch/arm/mach-imx/spl.c` and say "that is Chapter 14 §14.6, rewritten by someone who has done it a thousand times." That recognition is what Part II bought us.

## 19.1  Why mainline U-Boot, not the NXP fork

There are two U-Boot trees you will see referenced for the i.MX6ULL:

- **Mainline U-Boot**, hosted at `https://source.denx.de/u-boot/u-boot.git` (a.k.a. `git.denx.de`). The canonical project. Current version as of 2026 is in the v2024.x → v2025.x range.
- **NXP's vendor fork**, `https://github.com/nxp-imx/uboot-imx.git`, tagged `imx_v2016.03_4.1.15_2.0.0_ga` and later. The Point Atom guide uses this.

We use mainline. Three reasons:

1. **Mainline has full support for the i.MX6ULL EVK** since 2017 and tracks every silicon revision and DT change. Nothing about the i.MX6ULL requires a fork.
2. **The fork is from 2016**. Eight years of kernel and U-Boot security fixes are missing.
3. **Mainline is what every shipping product should converge on** (Ch 60A is the playbook). Starting on mainline avoids the migration cost later.

The Point Atom defconfig (`mx6ull_alientek_emmc`) is *not* in mainline. We use mainline's `mx6ull_14x14_evk_defconfig` (NXP's reference EVK) and port it to the Point Atom MINI in Chapter 22. The boards are close enough that the EVK config boots on the MINI with only minor DT changes for IOMUX and DDR timings.

## 19.2  Clone and look around

```sh
$ cd ~/imx6ull/src
$ git clone https://source.denx.de/u-boot/u-boot.git
$ cd u-boot
$ git log --oneline -3
abc123def (HEAD -> master, tag: v2025.01, origin/master) Release v2025.01
fed456abc Merge tag 'efi-2025-01-rc7' of ...
789abc456 board: foo: enable CONFIG_BAR
```

If you want a stable release rather than the development tip:

```sh
$ git checkout v2025.01           # or whichever release is current
```

Older systems may need an explicit `--depth=1` to avoid pulling ~50 MB of git history. Disk is cheap; we keep history.

### Directory layout

```
u-boot/
├── arch/                # CPU and SoC support
│   └── arm/
│       ├── cpu/armv7/
│       ├── mach-imx/    # the SoC-family code we care about
│       │   └── mx6/
│       ├── dts/         # device-tree sources for ARM boards
│       └── lib/
├── board/               # board-specific code, one folder per board
│   └── freescale/
│       └── mx6ull_14x14_evk/   # our starting point
├── cmd/                 # one .c per U-Boot command
├── common/              # shared core: main loop, env, image handling
├── configs/             # *_defconfig files
├── doc/                 # docs (read these!)
├── drivers/             # drivers (DM-style), organized by subsystem
├── env/                 # environment storage backends
├── fs/                  # filesystem support (FAT, ext4, UBIFS, ...)
├── include/             # public headers and per-board config headers
│   └── configs/
├── lib/                 # generic library code
├── net/                 # network stack
├── post/                # Power-On Self Test framework
├── scripts/             # build helpers
├── test/                # unit tests (you can run them on the host)
├── tools/               # mkimage, dumpimage, etc.
├── Kconfig              # top-level Kconfig
├── Makefile             # the build system entry point
└── ...
```

Read `doc/README.imx6` and `board/freescale/mx6ull_14x14_evk/README` before going further. They are short and answer the most common bring-up questions.

## 19.3  Build for the EVK

We already have `CROSS_COMPILE` and `ARCH` exported from Chapter 3's `~/imx6ull/scripts/env.sh`. If you forgot to source it:

```sh
$ export CROSS_COMPILE=arm-linux-gnueabihf-
$ export ARCH=arm
```

Now:

```sh
$ make mx6ull_14x14_evk_defconfig
$ make -j$(nproc)
```

The first build takes 1–2 minutes on a modern host. A few interesting moments scroll past:

- `HOSTCC scripts/...` — building host-side helpers (tools, dtc, mkimage) with the *host's* compiler.
- `CC arch/arm/cpu/armv7/start.o` — that file is the bare-metal startup. You just compiled the i.MX6ULL equivalent of your Chapter 10 `startup.S`. **Open it. Read it.**
- `LD spl/u-boot-spl` — building the SPL (Chapter 20).
- `LD u-boot` — building the main U-Boot ELF.
- `OBJCOPY u-boot.bin` — the raw binary (Chapter 6).
- `MKIMAGE u-boot.imx` — wrapping with an IVT + BootData (Chapter 7), the same operation our `mkimx.py` performs.

When `make` returns to the prompt without errors, the build artefacts are:

| File | What it is |
|------|------------|
| `u-boot` | The main U-Boot ELF (with symbols, useful for `gdb`) |
| `u-boot.bin` | The same, stripped to raw binary |
| `u-boot.imx` | The above wrapped with an IVT — **the file to flash for SD-boot** when no SPL is needed |
| `SPL` | The SPL ELF |
| `u-boot.img` | A U-Boot-formatted image of `u-boot.bin` (legacy, used by some flow paths) |
| `u-boot-dtb.imx` | U-Boot binary + DT blob, wrapped — current preferred form |
| `MLO` | Symbolic link / copy of the SPL image used by some SoCs (TI / OMAP heritage) |
| `arch/arm/dts/imx6ull-14x14-evk.dtb` | Compiled device tree for the EVK |

Two of these are what we will actually use:

- **`SPL`** — the first stage, gets `dd`'d to the SD card at offset `0x400` (LBA 2). This is what the i.MX6ULL Boot ROM finds and runs.
- **`u-boot-dtb.imx`** — the second stage, gets `dd`'d to the SD card at offset `69 KiB` (the location SPL's defconfig is built to look for).

Actually, for the SD-boot case the SPL is what carries the IVT, and the SPL loads `u-boot-dtb.imx` (or `u-boot.img`) from a later offset on the card. There is also a simpler **no-SPL** flow where `u-boot-dtb.imx` itself is what the ROM loads — used when U-Boot fits in OCRAM (rarely true these days). We will use the SPL flow throughout this book.

## 19.4  Flash to SD

The mainline `mx6ull_14x14_evk` SD-boot layout is:

| Offset (KiB) | Content |
|--------------|---------|
| 0 | (untouched / partition table) |
| 1 (= LBA 2) | SPL — contains the IVT |
| 69 | `u-boot-dtb.imx` (the second-stage image) |
| 8192 | Reserved for partitions (the rootfs partition begins around here) |

To write both stages:

```sh
$ sudo dd if=SPL of=/dev/sdX bs=1k seek=1 conv=fsync     # uses your sd-write helper
$ sudo dd if=u-boot-dtb.imx of=/dev/sdX bs=1k seek=69 conv=fsync
$ sync
```

(Or use the helper from Chapter 3 with two invocations; or write a small wrapper.)

A more pleasant alternative: `uuu` can do the whole thing over USB-OTG without an SD card. We will use that in Chapter 24. For now, SD is concrete and the steps are the most explicit.

## 19.5  First boot

Power on with the SD card inserted and the boot switch on SD. Within 2 seconds picocom should show:

```
U-Boot SPL 2025.01 (Jan 12 2026 - 17:42:31 +0700)
Trying to boot from MMC1


U-Boot 2025.01 (Jan 12 2026 - 17:42:31 +0700)

CPU:   i.MX6ULL rev1.1 at 396 MHz
Reset cause: POR
Model: Freescale i.MX6 UltraLiteLite 14x14 EVK Board
DRAM:  512 MiB
PMIC:  PFUZE3000 DEV_ID=0x30 REV_ID=0x11
MMC:   FSL_SDHC: 0, FSL_SDHC: 1
Loading Environment from MMC... *** Warning - bad CRC, using default environment

In:    serial
Out:   serial
Err:   serial
Switch to partitions #0, OK
mmc0 is current device
Net:   FEC0
Hit any key to stop autoboot:  3 ...
=>
```

If you press a key before the autoboot counts down, you land at the `=>` prompt. We did it.

Pause. Read the boot log a third time. Notice:

- "U-Boot SPL" prints first. That's a small program, loaded by ROM, that initialized DDR. **The exact responsibilities you wrote in Chapter 14.**
- "Trying to boot from MMC1" — SPL is reading `u-boot-dtb.imx` from the SD card and loading it into DRAM.
- "U-Boot 2025.01" — the second stage has taken over, running from DRAM, with full peripheral support.
- "CPU: i.MX6ULL rev1.1 at 396 MHz" — the boot-default ARM clock. Notice it didn't go to 696 MHz; the EVK config is conservative. Chapter 13's PLL config can apply here too.
- "DRAM: 512 MiB" — SPL's DDR setup worked. The same 100-line MMDC dance as our Chapter 14, but tested across thousands of boards.
- "Loading Environment from MMC..." — U-Boot tries to read its persistent env from the SD card. There isn't one yet; it falls back to defaults. `*** Warning - bad CRC` is normal on first boot.
- "Hit any key to stop autoboot" — without intervention, U-Boot would run `bootcmd` (Chapter 23) which on the EVK config tries to find a kernel and chain-boot Linux.

## 19.6  First commands

At the `=>` prompt:

### `printenv`

```
=> printenv
arch=arm
baudrate=115200
board=mx6ull_14x14_evk
board_name=EVK
bootcmd=run findfdt; mmc dev ${mmcdev}; mmc rescan; ...
bootdelay=3
console=ttymxc0
ethact=FEC0
ethaddr=00:04:9f:01:30:ad
...
```

Every variable here was set by the EVK board's source code or by the *default environment* compiled into U-Boot. Most are convenience shortcuts. We will spend Chapter 23 understanding `bootcmd` and `bootargs`.

### `bdinfo`

```
=> bdinfo
arch_number = 0x00000000
boot_params = 0x80000100
DRAM bank   = 0x00000000
-> start    = 0x80000000
-> size     = 0x20000000
flashstart  = 0x00000000
flashsize   = 0x00000000
flashoffset = 0x00000000
baudrate    = 115200 bps
relocaddr   = 0x9ff37000
reloc off   = 0x1f737000
Build       = 32-bit
current eth = FEC0
ethaddr     = 00:04:9f:01:30:ad
IP addr     = <NULL>
fdt_blob    = 0x9ed3d2c0
new_fdt     = 0x9ed3d2c0
fdt_size    = 0x00007b80
```

Several things to notice:

- `DRAM start = 0x80000000`, `size = 0x20000000` (512 MiB). Same map we used in Chapter 14.
- `relocaddr = 0x9ff37000`. **This is the actual address U-Boot is running from right now**, near the top of DRAM. U-Boot started executing somewhere lower in DRAM, then *relocated itself* to high DRAM to free the low addresses for the kernel. We'll trace that in Chapter 21.
- `reloc off = 0x1f737000` — the offset between the linker's idea of where U-Boot lives and where it actually lives. Pointer fixups everywhere use this.
- `fdt_blob = 0x9ed3d2c0` — U-Boot loaded its own copy of the device tree into DRAM. It will pass this address to the kernel via `r2` when it eventually `bootz`'s Linux.

### `md` — memory display

The Chapter 14 memtest equivalent:

```
=> md 0x80000000 4
80000000: 12345678 deadbeef ffffffff ffffffff    xV4....

=> mw 0x80000000 0xcafebabe
=> md 0x80000000 1
80000000: cafebabe                              ....
```

DRAM works. Same DRAM we configured by hand in Chapter 14, but the SPL did it for us this time.

### `mmc info`

```
=> mmc info
Device: FSL_SDHC
Manufacturer ID: 27
OEM: 5048
Name: SD32G
Bus Speed: 50000000
Mode: SD High Speed (50MHz)
Rd Block Len: 512
SD version 3.0
High Capacity: Yes
Capacity: 29 GiB
Bus Width: 4-bit
Erase Group Size: 512 Bytes
```

The SD card U-Boot booted from is also enumerated for runtime use — we'll read kernel images from it shortly.

### `mtest`

```
=> mtest 0x80000000 0x80100000 0x12345678 1
Testing 80000000 ... 80100000:
Pattern 12345678  Writing... Reading...Tested 1 iteration(s) with 0 errors.
```

Built-in DRAM memtest. Same principle as our Chapter 14 `ddr_selftest`, with more patterns. If it reports errors, your SPL's DDR config is wrong.

### `help`

```
=> help
?         - alias for 'help'
askenv    - get environment variables from stdin
base      - print or set address offset
...
```

About 80 commands ship with the EVK defconfig. We will use perhaps 15 of them in this book. The rest are board-specific or for use cases we don't reach (USB host, JTAG, fuse programming, etc.).

## 19.7  Recognizing Chapter 14 in SPL

This is the moment Part II earns its keep.

Open `arch/arm/mach-imx/spl.c` in your editor. Find `spl_dram_init` (or `arch_cpu_init`, depending on the SoC). It calls a board-specific function that, on the EVK, lives in `board/freescale/mx6ull_14x14_evk/spl.c`. Find `spl_dram_init` in that file. You will see something like:

```c
static void ccgr_init(void) { /* enable clocks to MMDC, IOMUXC, etc. */ }
static void iomux_setup_uart(void) { /* IOMUX pad config */ }
static struct mx6_ddr_sysinfo sysinfo = { /* timing tables */ };
static struct mx6_mmdc_calibration mx6_mmcd_calib = { /* calibration */ };
static struct mx6_ddr3_cfg mt41k128m16jt_125 = { /* JEDEC params */ };

static void spl_dram_init(void)
{
    mx6_ddr3_cfg(&sysinfo, &mx6_mmcd_calib, &mt41k128m16jt_125);
}
```

That's it. Three structs and one function call. Inside `mx6_ddr3_cfg` (in `arch/arm/mach-imx/mx6/ddr.c`) you will find ~600 lines that do *exactly* what your Chapter 14 `ddr_init` does — pad config, MMDC core registers, MR loads, ZQ cal, write-leveling — but parameterized, table-driven, and validated across every Micron / Nanya / ISSI DDR3 part NXP supports.

Read it. It is the cleanest production-grade DDR3 init code in any open-source project. The fact that it does not look magical to you is the entire point of Chapter 14.

## 19.8  Lab

1. **Clone, build, flash, boot.** Confirm `=>` appears.
2. **Hit a key to stop autoboot.** Explore: `printenv`, `bdinfo`, `mmc info`, `md`, `mw`, `help`.
3. **Run `mtest 0x80000000 0x90000000 0xa5a5a5a5 1`** — a 256 MB memtest. Should report 0 errors.
4. **Open `board/freescale/mx6ull_14x14_evk/spl.c`** and find the DDR struct definitions. Cross-reference each field against your Chapter 14 register values. Annotate.
5. **Open `arch/arm/mach-imx/mx6/ddr.c`** and find the DDR3 init flow. Match it section-by-section to your Chapter 14 code. Note where it does more (e.g., periodic recalibration) and where it does less (e.g., it does not run the stress tool inline; values are precomputed).

Commit your annotations to `code/ch19-uboot-first-boot/NOTES.md`.

## 19.9  Pitfalls

- **Building without `ARCH=arm CROSS_COMPILE=...`.** You will get a confusing host-build error halfway through. Always export these *before* `make`.
- **Reusing a build dir between defconfigs.** `make foo_defconfig && make bar_defconfig` does not fully reset state. Always `make distclean` between configs.
- **Wrong SD-card offsets.** SPL goes to LBA 2 (`bs=1k seek=1`); the second stage goes to `seek=69`. If you swap them or use a different offset, the ROM either finds nothing or loads garbage. The exact offsets are SoC-family-specific and controlled by `CONFIG_SPL_PAD_TO` and similar; the EVK defaults are what we used above.
- **Build artefacts left over from a previous board.** `make clean` keeps the `.config`; `make distclean` resets everything. When in doubt, distclean.
- **Bad CRC env warning** — *not* an error. Means the SD card has no saved env yet. `saveenv` once and the warning disappears on future boots.
- **`make -j` with not enough RAM.** U-Boot is small enough to build single-threaded if your host is constrained, but `-j$(nproc)` is fine on anything with ≥4 GB RAM.

## 19.10  Going deeper

- **U-Boot documentation** at `https://docs.u-boot.org/`. Specifically `arch/arm/cpu/armv7/Kconfig` and `doc/README.imx`.
- **`doc/board/freescale/`** in the source tree — the board-specific docs. Often the answer to "why this defconfig?"
- The **U-Boot mailing list** at `u-boot@lists.denx.de`. Read-only for weeks; learn how patches flow.
- **DENX's `Bootloader_with_U-Boot`** article series (free). The clearest single intro.
- The **U-Boot README** at the top of the source tree. Skim section by section; bookmark the parts that surprise you.

> Next chapter: **Chapter 20 — U-Boot SPL: the missing link.** We zoom into the SPL specifically — what makes it different from full U-Boot, what fits in 64 KB of OCRAM, and how it loads its successor.
