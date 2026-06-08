---
chapter: 7
title: The Boot ROM, IVT, DCD, and BootData
part: I — Foundations
estimated_pages: 22
status: draft
---

# Chapter 7 — The Boot ROM, IVT, DCD, and BootData

> **Lab vs production:** Do not burn fuses, enroll production keys, or sign release images while following the lab.
> Use throwaway keys and back up the unsigned image plus the key directory before testing irreversible security flows.


> **Acronyms used in this chapter** *(introduced here once. referenced through Parts II and III)*:
> - **POR_B** — Power-On Reset (active low). The pin that, when low, holds the SoC in reset.
> - **IVT** — Image Vector Table. The header structure at the start of a bootable image that tells the ROM where everything else is.
> - **DCD** — Device Configuration Data. A list of address/value pairs the ROM writes before loading your code (used to bring up DDR and PLLs).
> **DCD** - Device Configuration Data: ROM-executed register writes that prepare clocks and DDR before your code runs.
> **DDR** - external DRAM that must be configured and trained before most software can run from it.
> - **BootData** — a small struct holding the image's load address and total length.
> - **SDP** — Serial Download Protocol. The USB-OTG fallback the ROM enters when boot fuses say so.
> - **HAB** — High Assurance Boot. The cryptographic chain-of-trust feature (signed images). Detail in Ch 124.
> **HAB** - High Assurance Boot, NXP's ROM-enforced secure boot mechanism on i.MX SoCs.
> - **CSF** — Command Sequence File. The signature blob HAB consumes.
>
> **What:** what the i.MX6ULL does between the rising edge on POR_B and the moment it jumps to your code.
>
> **Why:** the Boot ROM is the first program that runs and you cannot change it. You can only obey it. The price of misunderstanding it is "the board does nothing" — the worst kind of bug, because there is no log to read.
>
> **Focus:** the **IVT** (where the ROM finds your image's metadata), the **DCD** (a tiny scripting language the ROM runs to prepare hardware before your code), and the **BootData** struct (load address and image length). These three structures, all under 100 bytes, are the contract.


## 7.1  What the Boot ROM is

The Boot ROM is a 96 KB block of code burned into the silicon at fabrication. It lives at physical address `0x00000000` (and is aliased to `0x00100000`). You did not write it. NXP wrote it. It runs first at every power-on and every reset, on every i.MX6ULL ever shipped.

Its sole job is to load some other code (your bootloader, or your bare-metal image) into RAM and jump to it. Everything you ever do on this chip happens after the Boot ROM has finished its work.

Three useful facts about the Boot ROM:

1. **It is documented.** NXP publishes "Chapter 8 — System Boot" of the i.MX6ULL Reference Manual specifically to describe ROM behavior. Read it before this chapter feels solid.
2. **It is the same across all i.MX6ULL chips** of a given silicon revision. Behavioral differences between dev boards are *not* in the ROM. they are in the boot pins and the boot-media contents.
3. **It is recoverable.** Even if you have written garbage to every flash on the board, you can still drop into **USB Serial Download Protocol (SDP)** and push a new image directly into OCRAM over USB-OTG. We rely on this in Chapter 8.

## 7.2  The boot sequence, step by step

From POR_B rising to your `_start` executing, the i.MX6ULL Boot ROM performs roughly the following:

1. **Internal initialization.** Set up the watchdog, the ROM's own stack at the top of OCRAM, and a few CCM defaults.
**CCM** - Clock Controller Module. It selects clock sources, dividers, and gates for the SoC.
2. **Sample boot fuses + boot pins.**
   - The ROM reads `OCOTP_CFG5[BT_FUSE_SEL]`. If that bit is set, the boot device is taken from the fuses in `OCOTP_CFG4`. If clear, it comes from the BOOT_MODE[1:0] pins together with the BOOT_CFG pins.
3. **Determine boot mode.**
   - `BOOT_MODE` = 0b00 → Boot from fuses (rare on dev boards).
   - `BOOT_MODE` = 0b01 → **Serial Downloader (SDP)** — wait for a host to push code over USB-OTG or UART. This is the recovery mode.
   - `BOOT_MODE` = 0b10 → **Internal boot** — read from the device selected by `BOOT_CFG`.
   - `BOOT_MODE` = 0b11 → Reserved.
4. *(Internal boot only)* **Probe the selected device.** SD card, eMMC, NAND, SPI-NOR, QSPI-NOR, or parallel NOR — each has a different probing path.
5. **Read the IVT at the fixed offset** for that device (per i.MX6ULL RM §8, Table 8-25 "First image / IVT offset per boot device"):
   - **SD / eMMC / eSD / SDXC**: IVT at offset **`0x400`** (1 KB into the boot device).
   - **SPI EEPROM (SPI-NOR)**: IVT at offset **`0x400`**.
   - **QSPI NOR**: IVT at offset **`0x1000`** (4 KB) on typical i.MX6ULL configurations — verify against your specific BSP / mkimage settings.
**BSP** - Board Support Package: vendor patches, configs, bootloader files, and scripts needed to boot one board.
   - **Parallel NOR / EIM**: IVT at offset **`0x1000`** (4 KB).
   - **OneNAND**: IVT at offset **`0x100`** (256 B).
   - **Raw NAND** (non-OneNAND): handled via the **FCB (Firmware Configuration Block)** — the IVT does *not* live at a fixed offset. It is reached after the ROM parses the FCB. We do not cover raw-NAND boot in detail in this book.
6. **Validate the IVT.** Check its tag byte (`0xD1`), version, and self-pointer.
7. **Walk the DCD** (if pointed-to by the IVT). The DCD is a list of register writes the ROM will perform before loading your image. Typical use: configure DDR controller and PLLs so the image can be loaded into DRAM.
8. **Load the image.** Read `BootData.length` bytes from the boot device into `BootData.start` (the destination address).
9. *(If HAB is enabled)* **Verify signatures.** Walk the CSF (Command Sequence File). If verification fails, halt.
10. **Jump to `IVT.entry`.** Control transfers to your image's entry point. From here on, your code owns the machine.

The whole sequence takes 10–100 ms depending on boot media and image size. The Boot ROM's `printf`-equivalent goes nowhere — there is no UART output unless you build in your own as soon as you take control.

## 7.3  The IVT — Image Vector Table

The IVT is **32 bytes**, eight 32-bit words. Lay it out explicitly:

| Offset | Field | Description |
|--------|-------|-------------|
| `+0x00` | `header` | 4 bytes: `0xD1` (tag), `0x00 0x20` (length = 32, big-endian), `0x40` or `0x41` (version — both are accepted; U-Boot's `mkimage` emits one or the other depending on options) |
| `+0x04` | `entry` | Absolute address the ROM jumps to after image is loaded. |
| `+0x08` | `reserved1` | Must be `0x00000000`. |
| `+0x0C` | `dcd` | Absolute address of the DCD, or 0 if none. |
| `+0x10` | `boot_data` | Absolute address of the BootData structure. |
| `+0x14` | `self` | The IVT's own absolute address. **This is how the ROM knows the relocation offset.** |
| `+0x18` | `csf` | Address of the Command Sequence File (HAB signatures), or 0 if unsigned. |
| `+0x1C` | `reserved2` | Must be `0x00000000`. |

A few observations.

- **The `header` byte sequence `0xD1 0x00 0x20 0x40`** is the magic the ROM looks for. If you write the wrong byte order at offset 0, the ROM rejects the image with no diagnostic. You will see this byte pattern at offset `0x400` of every bootable SD card in this book.
- **The `self` field is load-bearing.** It is the IVT's own physical address. The ROM compares `self` against where it actually loaded the image and uses the difference to relocate `entry`, `dcd`, and `boot_data` if necessary. Getting `self` wrong is the most common way to brick an otherwise correct image.
- **All addresses in the IVT are absolute physical addresses**, not file offsets. The ROM understands that the image was at file offset `X` but ends up in OCRAM (or DRAM, post-DCD) at address `Y`, and it adjusts.

### A worked example

Assume you build a bare-metal image whose IVT will be loaded to OCRAM at `0x00907400` (chosen so that the entry point lands at `0x00907400 + 0x1000 = 0x00908400` after a 4 KB pad). The IVT then reads:

```
Offset    Field      Value
+0x00     header     0xD1 0x00 0x20 0x40
+0x04     entry      0x00908400
+0x08     reserved1  0x00000000
+0x0C     dcd        0x00907420   (DCD starts immediately after IVT)
+0x10     boot_data  0x00907424   (after DCD if no DCD, or after DCD's end)
+0x14     self       0x00907400   ← the address of this IVT
+0x18     csf        0x00000000   (no signature)
+0x1C     reserved2  0x00000000
```

For SD card boot: this IVT lives at SD-card file offset `0x400`. The image data following starts at offset `0x400` in the file, gets loaded to `BootData.start` in RAM. The ROM walks the DCD, then loads the rest, then jumps to `0x00908400`.

We will build this layout literally in Chapter 11.

## 7.4  BootData — telling the ROM how big the image is

BootData is **12 bytes**:

| Offset | Field | Description |
|--------|-------|-------------|
| `+0x00` | `start` | Physical address to load the image to. |
| `+0x04` | `length` | Number of bytes to load (including the IVT, DCD, and padding). |
| `+0x08` | `plugin` | 0 = normal image; nonzero = plugin (a small program the ROM runs but doesn't transfer control to). We will not use plugins. |

`length` includes everything from the start of the file as loaded — IVT and your code. A common bug: you set `length` to "just the code size" and the ROM stops loading before your `.data` is copied. Always include header bytes in `length`.

## 7.5  The DCD — Device Configuration Data

The DCD is one of the more clever and least-documented parts of i.MX boot.

The DCD is a list of operations the Boot ROM will perform on your behalf *before* loading your image. Its purpose is to bring up hardware that you cannot bring up yourself yet — most importantly, the **DDR controller**, so that the ROM can load your image into DRAM rather than the cramped OCRAM.

Each DCD entry is one instruction in a small, one-byte-opcode language:

| Opcode | Name | Description |
|--------|------|-------------|
| `0xCC` | WRITE | Write value(s) to register(s) |
| `0xCF` | CHECK | Poll register until condition is met |
| `0xC0` | NOP | No-op |

(The full set in the reference manual includes a few more, but these three are 95% of real DCDs.)

### WRITE format

```
0xCC <length:2-bytes-BE> <flags:1-byte> <addr0:4> <val0:4> <addr1:4> <val1:4> ...
```

`flags` selects between byte/halfword/word writes (bits 3:2) and "set bits" / "clear bits" / "write" semantics (bits 1:0). The most common flags byte is `0x04` ("write 32-bit words").

### CHECK format

```
0xCF <length:2-bytes-BE> <flags:1-byte> <addr:4> <mask:4>
```

Reads `addr`, ANDs with `mask`, loops until the condition specified by flags is met. Typically used for "wait until PLL locked."
MCU bridge: Think of a PLL like the clock multiplier setup you used on STM32, but with more clock roots, gates, and consumers that Linux later needs to describe.
**PLL** - Phase-Locked Loop, a clock block that multiplies a reference clock to create faster clocks.

### A minimal DCD

A DCD that does nothing more than write `0x12345678` to `0x80000000` and then complete looks like:

```
0xD2 0x00 0x10 0x40      ; DCD header: tag=0xD2, length=0x0010 (16 bytes), version=0x40
0xCC 0x00 0x0C 0x04      ; WRITE, length=0x000C, flags=0x04 (32-bit)
0x80 0x00 0x00 0x00      ; address = 0x80000000
0x12 0x34 0x56 0x78      ; value
```

Sixteen bytes of data, four bytes of overhead. A real DCD for DDR3 initialization is roughly **400–800 bytes** — say 100 register writes — and is the entire content of the file we will inspect in Chapter 14.

### Why DCD exists

You could, in principle, do all of this in your own startup code instead of in DCD. People do. Two reasons to use DCD anyway:

1. **You may need DRAM up *before* your image is loaded.** If your image is bigger than OCRAM (128 KB), the only way to use it is for the ROM to load it into DRAM. The ROM can only load into DRAM after DDR is initialized, and the ROM cannot initialize DDR on its own. The DCD is the script you hand it that does that initialization.
2. **Some peripherals need very early init.** Bringing up clocks to specific peripherals before your code runs can simplify SPL.
MCU bridge: Think of SPL like the tiny early startup code that runs from internal SRAM before DDR is usable.
**SPL** - Secondary Program Loader, a tiny first U-Boot stage that fits in OCRAM and initializes DDR.
MCU bridge: Think of U-Boot like a much larger boot stub plus debug monitor: it initializes hardware, loads the next image, and gives you commands before Linux starts.

For a small bare-metal image that runs purely from OCRAM, you don't need a DCD. Your IVT can leave the DCD pointer as zero and bring up DDR yourself. We will do exactly that in Chapter 14 to keep things honest. The image we build in Chapter 11 also has no DCD — it's small enough to fit in OCRAM.

## 7.6  Boot modes, in concrete detail

Re-summarizing §7.2 step 3 with the actual signals:

### Internal Boot (BOOT_MODE = 10)

The ROM reads `BOOT_CFG1[7:0]`, `BOOT_CFG2[7:0]`, `BOOT_CFG4[7:0]` from the boot-mode pins (or from fuses if `BT_FUSE_SEL` is set). The bit patterns encode:

| `BOOT_CFG1` | Boot device |
|------------|-------------|
| `0x60` | eMMC, 8-bit DDR |
| `0x40` | SD card 4-bit, USDHC1 or USDHC2 (selected by another bit) |
| `0x80` | NAND Flash |
| `0x10` | SPI-NOR via ECSPI |
| `0x18` | QSPI-NOR |
| ... | ... |

The Point Atom MINI uses SD card boot by default, with a jumper to select between SD and eMMC. Verify on your specific board's silkscreen.

### Serial Downloader (BOOT_MODE = 01)

The ROM enumerates as a USB device on the USB-OTG port (VID `0x15A2`, PID `0x0080` for i.MX6ULL). It also listens for SDP commands on **UART1**, but USB is overwhelmingly the practical choice.

In SDP mode the ROM accepts a small command set:

- `0x0101` READ_REGISTER
- `0x0202` WRITE_REGISTER
- `0x0404` WRITE_FILE — push bytes to a target address
- `0x0505` ERROR_STATUS
- `0x0808` DCD_WRITE
- `0x0A0A` JUMP_ADDRESS — jump to a previously-loaded address

Your `uuu` or `imx_usb_loader` tool wraps these into a friendly script. Under the hood it is `WRITE_FILE` to push an IMX image to RAM, then `JUMP_ADDRESS` to the loaded IVT.

This is your recovery path. Drill this procedure until it is automatic. A board that boots into SDP mode is **not bricked**, whatever is on its flash.

## 7.7  The .imx image format

Putting it all together, an `.imx` file (the artifact you `dd` to an SD card) has this layout:

```
File offset    Content
0x0000         (1 KB of padding, sometimes contains partition table or zero)
0x0400         ┌─ IVT (32 bytes)
0x0420         │  DCD (variable; typically 16 to ~800 bytes; may be absent)
0x04XX         │  BootData (12 bytes)
0x0500ish      │  more padding
0x1000         │  Application image proper (.text, .rodata, .data)
   ...         │
              ─┘  end after BootData.length bytes
```

The exact layout is partly your choice — within the constraint that IVT.self must equal the load address of IVT, IVT.entry must point to where the application begins, and BootData.length must cover everything up to the last byte you want loaded.

Tools that generate `.imx` files:

- `mkimage -T imximage -n image.cfg -d app.bin app.imx` — the U-Boot tool. Takes a `.cfg` describing DCD writes and produces the final image.
**U-Boot** - the bootloader that initializes enough hardware to load and start the Linux kernel.
- `imx-mkimage` — NXP's standalone tool, used by their OS BSPs.
- **Your own script in Chapter 11.** We will write a 60-line Python program that emits an `.imx` file byte-by-byte, with no `mkimage`.

The point of doing it ourselves once is the same as the point of the whole book.

## 7.8  HAB — High Assurance Boot, briefly

If `IVT.csf` is nonzero, the ROM jumps to a verification routine before executing your code. This is **HAB (High Assurance Boot)**, NXP's secure boot scheme. It uses the **SRK (Super Root Key)** hash burned into fuses, an X.509 certificate chain stored in your image, and a CST-generated signature.

On a freshly-fabricated chip, HAB is in "open" mode — verification is performed but failures do not stop the boot. Once you burn the `SEC_CONFIG[1]` fuse, HAB is in "closed" mode — failures stop the boot, permanently. There is no recovery from a botched closed-mode signing.

We will not enable HAB in Parts I–VI of this book. Chapter 124 covers the full HAB workflow, including how to sign U-Boot and the kernel and how to chain that trust into a verified rootfs.
MCU bridge: Think of the rootfs as the firmware image's file-backed runtime environment. On an MCU you link everything into flash. On Linux, programs and config live in this mounted tree.
**rootfs** - root filesystem, the directory tree mounted at / that contains /bin, /etc, /dev, and libraries.

For now: leave `IVT.csf = 0`. Do not touch SEC_CONFIG fuses.

## 7.9  How to inspect an existing .imx

You can dissect any `.imx` from any source — your own builds, U-Boot, a vendor BSP — with two tools:

```sh
$ dumpimage -l u-boot-dtb.imx     # tries to identify, prints summary
$ xxd u-boot-dtb.imx | head -20
00000000: 4000 0040 ffff ffff ffff ffff ffff ffff  @..@............
00000010: ffff ffff ffff ffff ffff ffff ffff ffff  ................
...
00000400: d100 2040 0000 7880 0000 0000 2c04 7880  .. @..x.....,.x.
00000410: 8000 7880 0014 7880 0000 0000 0000 0000  ..x...x.........
```

At offset `0x0400` you should see the IVT magic `D1 00 20 40`. Decode the next words:

- `00 00 78 80` (little-endian) → entry = `0x80780000`
- `00 00 00 00` reserved
- `2C 04 78 80` → dcd = `0x8078042C`
- `80 00 78 80` → boot_data = `0x80780080`
- `00 14 78 80` → self = `0x80781400`

These look inconsistent at first glance. They aren't, once you remember that the byte order is little-endian and the image is meant to be loaded at `0x80700000` in DRAM. With a little practice you read these in your head. We'll do exactly this for our own image in Chapter 11.

## 7.10  Lab

Two short exercises, mostly reading.

### Lab A — Find your board's boot pins

From the Point Atom MINI schematic, locate:

1. The `BOOT_MODE0` and `BOOT_MODE1` pins. What do their default pull resistors do?
2. The `BOOT_CFG1[7:0]` pins. Which physical pin (on the SoC ball-out) becomes which BOOT_CFG bit?
3. The jumper or DIP switch that selects between SD-card boot and SDP / recovery mode.
4. Identify which boot device (SD vs eMMC) the board defaults to.

Write the wiring in `~/imx6ull/notes/ch07-boot-pins.md`. Photograph the relevant section of the schematic if helpful.

### Lab B — Decode a known-good .imx

Grab any prebuilt `u-boot.imx` for i.MX6ULL (e.g., from an existing Buildroot output, or download one from NXP). Without using `dumpimage`:
**Buildroot** - a configuration-driven build system that produces a complete root filesystem and related images.

```sh
$ xxd -s 0x400 -l 32 u-boot.imx
```

In your notes, decode every field of the IVT. Compute `BootData.length` from the file size and verify it matches what BootData says. Identify whether a DCD is present.

You do not need to *run* the image. The point is to read it.

## 7.11  Pitfalls

- **`IVT.self` mismatched with actual load address.** Symptom: the board reads the image, but does not branch to your entry. The ROM does branch — to the wrong place. Always set `self` to where the IVT *will be after loading*, not where it lives in the file.
- **`BootData.length` shorter than the image.** Tail of your image is not loaded. `.data` initial values become whatever was in RAM.
- **DCD writes that hang the system.** A DCD `CHECK` waiting for a bit that never sets locks the ROM. The board appears dead. Workaround: boot in SDP mode and push a known-good image.
- **Wrong endianness in DCD header length.** The DCD header length is **big-endian**. Get this wrong, the ROM either ignores the DCD or executes garbage.
- **Forgetting the 1 KB pre-IVT padding.** On SD/MMC the IVT lives at offset `0x400`, not at offset 0. The first 1 KB is a "no-man's-land" partitioning systems can use without touching the IVT.
- **Closing HAB by accident.** It is a one-way fuse. Do not write to OCOTP_CFG5 unless you have read Chapter 124 carefully and have a key-management plan.

## 7.12  Going deeper

- **IMX6ULLRM**, *Chapter 8 — System Boot*. The canonical reference. ~80 pages.
- **AN12055** — *Boot from CMOS NAND for the i.MX 6UL/6ULL*.
- **AN12056** — *Boot from QSPI Flash on i.MX 6UL/6ULL*.
- **AN4581** — *i.MX 6 Series Boot Process*.
- The U-Boot `tools/mkimage.c` and `tools/imximage.c` source — read these *after* you have written your own image-builder, not before.
- The `imx-mkimage` repository at `<https://github.com/nxp-imx/imx-mkimage>`. Useful reference, but our goal in Ch 11 is to do without it.

> Next chapter: **Chapter 8 — Hardware bring-up checklist.** The last conceptual chapter. From Ch 9 onward, every chapter ends with running code on the board.
