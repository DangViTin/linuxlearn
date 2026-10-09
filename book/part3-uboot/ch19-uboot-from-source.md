---
chapter: 19
title: "U-Boot from source: first boot"
part: III - U-Boot, deeply
estimated_pages: 16
status: draft
---

# Chapter 19: U-Boot from source, first boot

Our LED program had a modest job. It reached one pin, changed its level, and
stayed there. Now imagine extending it until it can find a file on an SD card,
read a device tree, choose a boot policy, and start Linux. The register writes
would be only a small part of the work.

U-Boot already provides that larger framework. We will build it, inspect the
image the ROM will see, and follow its startup back to the mechanisms from
Part II. The first useful result is not just a new binary. It is knowing which
board that binary describes.

This chapter builds an **NXP i.MX6ULL EVK reference image**. Our Point Atom MINI
port comes in Chapter 22. The EVK image is not a qualified MINI image: a shared
SoC does not establish matching DDR timings, pad routes, power hardware, or
storage wiring. Readers with a MINI can complete the host-side work here and
keep their existing known-good board image while preparing that port.

## 19.1  Why mainline U-Boot

```{figure} ../illustrations/part3/01-same-chip-different-board.png
:alt: Two conceptual i.MX6ULL boards need separate checks of DDR settings, pin routes, and power wiring.
:name: fig-p3-board-qualification
:figclass: concept-sketch
:width: 100%

The chip name identifies shared SoC logic. The empty checklist represents board facts still needing verification. These drawings are not real board layouts.
```

Two source families commonly appear in i.MX projects:

| Source | What to expect |
|--------|----------------|
| [Upstream U-Boot](https://source.denx.de/u-boot/u-boot.git) | The main project, with release tags, board configurations, documentation, and subsystem development |
| [NXP's U-Boot tree](https://github.com/nxp-imx/uboot-imx) | NXP BSP integration and release-specific changes that may matter to a product |

Neither label proves that an arbitrary checkout supports your board. A vendor
BSP may contain board-specific work you still need to understand. An upstream
configuration may target a reference board rather than yours.

For a repeatable reading exercise, Part III uses **upstream v2026.04**. This is
a fixed study release, not a claim that it is the newest or the right release
for every product. Keep that tag throughout this part. Changing the source
version halfway through also changes the files, APIs, and configuration names
we are trying to connect.

The selected configuration is `mx6ull_14x14_evk_defconfig`. In this release it
does **not** enable SPL. Its image contains a DCD, the Device Configuration Data
table that the Boot ROM executes to prepare DDR before loading U-Boot there.
Full U-Boot does not need to fit inside OCRAM in this design. Chapter 20 examines
the other design, where a small SPL initializes DDR in software.

## 19.2  Clone and look around

Use the lab Ubuntu environment from Chapter 3. These are host-terminal commands,
shown with `$`. Later, `=>` will identify commands entered in U-Boot instead.

```sh
$ . ~/imx6ull/scripts/env.sh
$ cd ~/imx6ull/src
$ git clone --branch v2026.04 https://source.denx.de/u-boot/u-boot.git u-boot
$ cd u-boot
$ git describe --tags --exact-match
v2026.04
$ git rev-parse HEAD
88dc2788777babfd6322fa655df549a019aa1e69
```

`--branch` selects the release tag while cloning. Git may report a *detached
HEAD*: you are looking at that fixed revision rather than a branch that moves
with new commits. It is not an error. Before making your own code changes in
Chapter 21, create a local branch.

If `~/imx6ull/src/u-boot` already exists, inspect it rather than cloning over it.
Check its revision and preserve local changes. A separate checkout is often
clearer than trying to make another project's tree match this exercise.

Start with these paths. They describe different levels of responsibility:

| Path in v2026.04 | Question it answers |
|-----------------|---------------------|
| `configs/mx6ull_14x14_evk_defconfig` | Which features and defaults does this board select? |
| `board/nxp/mx6ullevk/` | What is specific to the EVK? |
| `board/nxp/mx6ullevk/imximage.cfg` | Which ROM image format and DDR writes are selected? |
| `arch/arm/cpu/armv7/start.S` | How does the ARMv7 startup begin? |
| `arch/arm/lib/crt0.S` | How are the early stack, global data, and relocation arranged? |
| `arch/arm/mach-imx/` | What is shared by the i.MX family? |
| `drivers/`, `cmd/`, `env/`, `fs/`, `net/` | Where do devices, commands, storage, files, and networking belong? |
| `tools/` | Which programs run on the host to construct or inspect images? |

Read `doc/board/nxp/mx6ullevk.rst` alongside the defconfig. Notice the output
filename and its SD-card placement. Those two details will prevent a common
mistake before any card is written.

## 19.3  Build for the EVK

The environment script selects `arm-none-linux-gnueabihf-` for the book's
U-Boot builds. U-Boot uses its own freestanding build rules, not the compiler's
Linux user-space startup or glibc. The `HOSTCC` programs, on the other hand,
must run on your Ubuntu host and use its native compiler.

The build also needs host development tools and headers. Besides the Chapter 3
basics, the unmodified v2026.04 build may need `libgnutls28-dev` for its host
EFI-capsule tool. That dependency does not mean our board boots through EFI.
Resolve missing host packages in the isolated lab environment, not by replacing
either of our project-local Arm toolchains. See the release's
[GCC build instructions](https://docs.u-boot.org/en/v2026.04/build/gcc.html).

Keep generated files outside the source tree:

```sh
$ make O="$HOME/imx6ull/build/uboot-evk" mx6ull_14x14_evk_defconfig
$ make O="$HOME/imx6ull/build/uboot-evk" -j4
```

`O=` names the output directory. Both commands use the same one: the first
writes its configuration, and the second builds that configuration. `-j4`
allows four parallel jobs. Use `-j1` if memory is tight. There is no guaranteed
build time to wait for. The useful checkpoint is a successful exit followed by
the expected files.

Several kinds of work appear in the log:

- `HOSTCC` builds host programs such as image tools.
- `CC` and `AS` compile target C and assembly.
- `LD u-boot` links the symbol-bearing target ELF.
- `OBJCOPY` produces binary data without the ELF's debugging view.
- The image-generation step adds the i.MX header and DCD for the ROM.

For this configuration, inspect these outputs:

| File under `~/imx6ull/build/uboot-evk` | Use |
|------------------------------------|-----|
| `u-boot` | ELF executable with symbols for disassembly and debugging |
| `u-boot.map` | Linker's record of sections and symbol addresses |
| `.config` | Expanded configuration, including defaults not written in the defconfig |
| `u-boot.bin` | Main binary with the selected separate control DTB appended by the build |
| `u-boot-dtb.imx` | ROM-loadable EVK image with its i.MX header and DCD |
| `tools/mkimage` and `tools/dumpimage` | Host image-construction and inspection programs |

There is no `SPL` output for this EVK defconfig. A missing SPL file is not a
failed build. It is evidence about the boot route you selected.

```sh
$ ~/imx6ull/build/uboot-evk/tools/mkimage -l \
    ~/imx6ull/build/uboot-evk/u-boot-dtb.imx
$ xxd -l 32 ~/imx6ull/build/uboot-evk/u-boot-dtb.imx
```

Look for i.MX image version 2, DCD mode, and the entry address selected by
`CONFIG_TEXT_BASE`, `0x87800000`. In this file the IVT header starts at file
byte zero. The first four bytes are `d1 00 20 40`.

One tool label needs care: this release's i.MX image summary prints the IVT's
BootData pointer as `Load Address`. That is not the ELF's text address or
BootData's `start` field. When checking the complete loaded range, decode the
IVT and BootData fields as in Chapter 7 rather than relying on that label.

That differs from our Chapter 11 builder, which included a leading 1 KiB pad.
The same ROM-visible IVT location can come from different file layouts. Keep
the file offset and the media offset separate.

## 19.4  Flash to SD

**This section is only for a matching EVK, or a separately qualified board
image. Do not write this EVK build to a MINI and assume that Chapter 22 is
optional.** You can finish the inspection exercise without flashing anything.

For this EVK SD image:

| Location | Meaning |
|----------|---------|
| Image file byte `0` | Start of the IVT |
| SD-card byte `0x400`, or 1 KiB | Where that IVT must appear on the medium |
| SD-card byte `0xC0000` | Default configured environment offset, with size `0x2000` |

There is one image write, not an SPL write followed by another image at 69 KiB.
The environment region is a separate storage reservation. Check that the image
length plus its 1 KiB placement ends before that reservation, and that your
card layout reserves these raw ranges before its filesystem partitions. Changing
the image or environment layout requires checking the ranges again.

Use a dedicated, disposable lab card. A DOS/MBR layout with appropriately
reserved space is different from GPT: the primary GPT entries occupy sectors
that overlap this raw boot placement. Do not combine these instructions with
an arbitrary existing partition table.

Before writing, repeat Chapter 11's card-identification procedure. Confirm the
whole-device path from its size and physical removal/reinsertion, inspect all
mounted partitions, and unmount only those belonging to that card. `/dev/sdX`
below is a placeholder to replace with that confirmed device, not a command to
run unchanged. A wrong destination can destroy another disk's data.

After those checks, the EVK image write is:

```sh
$ sudo dd if="$HOME/imx6ull/build/uboot-evk/u-boot-dtb.imx" \
    of=/dev/sdX bs=1K seek=1 conv=notrunc,fsync status=progress
```

`seek=1` skips one output block, which is 1024 bytes because of `bs=1K`.
`notrunc` avoids truncation when the destination is a regular file. `fsync`
requests synchronization before `dd` finishes. None of these options verifies
that the destination was the right card.

Read back and compare exactly the written bytes before moving the card to the
board:

```sh
$ image="$HOME/imx6ull/build/uboot-evk/u-boot-dtb.imx"
$ bytes=$(stat -c %s "$image")
$ sudo dd if=/dev/sdX bs=1K skip=1 count="$bytes" iflag=count_bytes \
    status=none | cmp -n "$bytes" "$image" -
```

Here `skip=1` still skips 1 KiB. `iflag=count_bytes` makes `count` a byte count.
`cmp` prints nothing and returns success when the compared bytes match. A
mismatch is a stop point, not a reason to try booting anyway. This checks media
bytes, not the suitability of the EVK's DDR settings for another board.

## 19.5  First boot

Open the serial terminal before powering the matching board. Use the board's
documented SD boot setting and the confirmed console connection at 115200 baud,
8 data bits, no parity, and one stop bit. Chapter 8's power and USB checks still
apply. EVK switch labels are not MINI switch instructions.

The banner should identify the build you selected. This abbreviated example
shows the shape of a log, not a measured board run:

```text
U-Boot 2026.04 (...)
...
Hit any key to stop autoboot: ...
=>
```

Press a key during the countdown. The `=>` prompt means the command interpreter
is available. It does not prove that Ethernet, every storage device, or DDR at
all operating conditions has been validated.

For the EVK route we built, the ROM executed the DCD before the banner. There
is no required `U-Boot SPL` banner. If your existing board image prints one,
record that observation: it describes a different configured boot route, not
a missing stage in this build.

A silent board can fail before U-Boot has a working console. Keep the checks
separate: power and boot selection, ROM-readable image placement, correct
board DDR setup, then U-Boot's console route. Rewriting a UART driver cannot
repair a DCD that never made DDR usable.

## 19.6  First commands

Begin with inspection rather than writes:

```text
=> version
=> help
=> printenv bootcmd bootargs loadaddr fdt_addr fdt_file
=> bdinfo
=> mmc list
```

`version` identifies the running program, not the directory on your host.
`printenv` shows the environment currently in RAM. Some variables may be
absent, and a saved environment can override compiled defaults.

In `bdinfo`, find the DRAM bank start and size, `relocaddr`, and `reloc off`.
Chapter 21 will connect those values to the linker map. Treat them as values
to record from your session, not numbers to copy from another board's log.

Use `mmc list` to identify U-Boot's device numbering. After selecting the
intended device with `mmc dev <number>`, `mmc info` reports that device. U-Boot
MMC indices are not automatically Linux's `/dev/mmcblkN` indices, and neither
is a host `/dev/sdX` name.

Two commands deserve restraint:

- **`md` displays memory.** It needs a valid, intentionally chosen RAM range
  or an appropriate register whose read behavior you understand. It is not a
  DRAM qualification test, and some peripheral reads have side effects.
- **`mw` and `mtest` write memory.** A broad range can overwrite U-Boot's code,
  stack, heap, control device tree, or loaded images. Do not run a generic
  256 MiB test across live RAM. Chapter 14's ownership and qualification rules
  apply even when a command is already built in.

We will use load buffers later, after identifying their addresses, sizes, and
reservations. For now, a good page of recorded `bdinfo` and configuration
evidence is more useful than a destructive test with an uncertain range.

(recognizing-chapter-14-in-spl)=
## 19.7  Recognizing Chapter 14 in the ROM's DCD

Open `board/nxp/mx6ullevk/imximage.cfg`. Its `DATA` entries tell the image tool
which writes to place in the DCD. Two entries from that EVK table are:

```text
DATA 4 0x021B000C 0x676B52F3
DATA 4 0x021B0010 0xB66D0B63
```

The `4` means a 32-bit write. The addresses select MMDC timing registers,
including `MDCFG0` and `MDCFG1`. The values belong to this EVK configuration.
They are not substitutes for the fitted DDR part, calibration record, and
board-specific worksheet from Chapter 14.

Follow one entry into `tools/imximage.c`: the host program converts the textual
configuration into a DCD inside the image. The ROM performs the writes before
loading and entering the DDR-resident program. Full U-Boot then establishes
its own runtime and reports available memory.

This is the connection to Part II. The responsibility is familiar, but the
program performing it has changed. A DCD is data interpreted by the ROM. An
SPL is executable software that can perform DDR setup itself. Neither route
can guess which timing values are safe for your PCB.

The upstream EVK table also enables broad clock-gate masks. Reading that table
explains its behavior; it does not make all-ones clock writes a good default
for our smaller, explicitly owned bare-metal experiments.

## 19.8  Lab

1. Clone the fixed tag and record its commit. Keep your original board image.
2. Build the EVK reference in its own `O=` directory. Confirm `.config`,
   `u-boot`, `u-boot.map`, and `u-boot-dtb.imx` exist. Explain why no SPL is expected.
3. Inspect the image with `mkimage -l` and `xxd`. Identify the IVT tag, entry
   address, and the distinction between file byte zero and SD byte `0x400`.
4. Find `CONFIG_IMX_CONFIG` in the expanded configuration and open that file.
   Match one MMDC entry to the reference manual and Chapter 14's worksheet.
5. For a MINI, list the board facts still needed before this reference can
   become a qualified port. Continue to Chapter 22 without flashing it.
6. If you have a matching EVK and qualified spare card, follow the conditional
   write/readback procedure. Record the actual prompt and inspection commands.
   Otherwise, keep this as a host-side lab. Do not invent a boot result.

## 19.9  Pitfalls

- **A filename is not a boot plan.** This EVK build uses one DCD-bearing image
  at media 1 KiB. Another board's `SPL` and `u-boot.img` layout does not apply.
- **A configuration is not a board measurement.** Declaring 512 MiB or finding
  EVK timing writes does not qualify the MINI's fitted memory and routing.
- **Mixing source and output directories.** Repeat the same `O=` argument on
  every build command. Use a different directory for a different board.
- **Using yesterday's terminal environment.** Source the Chapter 3 script in
  each new host terminal and check the compiler path before building.
- **Writing over the environment or a partition table.** Check byte ranges,
  image size, and the selected card layout. Do not assume 1 KiB is free on GPT.
- **Treating a bad environment CRC as harmless in every case.** It may mean
  unused storage, a changed layout, corruption, or a failed read. Inspect the
  backend and device first. Do not use `saveenv` merely to silence a warning.

## 19.10  Going deeper

- [EVK build and SD placement](https://docs.u-boot.org/en/v2026.04/board/nxp/mx6ullevk.html).
- [Pinned EVK defconfig](https://github.com/u-boot/u-boot/blob/v2026.04/configs/mx6ull_14x14_evk_defconfig).
- [EVK image configuration](https://github.com/u-boot/u-boot/blob/v2026.04/board/nxp/mx6ullevk/imximage.cfg).
- [The host i.MX image builder](https://github.com/u-boot/u-boot/blob/v2026.04/tools/imximage.c).

The next chapter follows the alternative SPL route. Keep the EVK build beside
you: its absence of SPL will make the difference easier to see.
