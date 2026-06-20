# Chapter 7: The Boot ROM, IVT, DCD, and BootData

> **Acronyms used in this chapter** *(introduced here once. Referenced through Parts II and III)*:
> - **POR_B**, Power-On Reset (active low). The pin that, when low, holds the SoC in reset.
> - **IVT**, Image Vector Table. The header structure at the start of a bootable image that tells the ROM where everything else is.
> - **DCD**, Device Configuration Data. A list of address/value pairs the ROM writes before loading your code (used to bring up DDR and PLLs).
> - **BootData**, a small struct holding the image's load address and total length.
> - **SDP**, Serial Download Protocol. The download protocol entered when the board selector is in USB mode.
> - **HAB**, High Assurance Boot. The cryptographic chain-of-trust feature (signed images). Detail in Ch 124.
> - **CSF**, Command Sequence File. The signature blob HAB consumes.
>
> **What:** what the i.MX6ULL does between the rising edge on POR_B and the moment it jumps to your code.
>
> **Why:** the Boot ROM is the first program that runs and you cannot change it. You can only obey it. The price of misunderstanding it is "the board does nothing", the worst kind of bug, because there is no log to read.
>
> **Focus:** the **IVT** (where the ROM finds your image's metadata), the **DCD** (a tiny scripting language the ROM runs to prepare hardware before your code), and the **BootData** struct (load address and image length). These three structures, all under 100 bytes, are the contract.


## 7.1  What the Boot ROM is

The Boot ROM is a 96 KB block of code burned into the silicon at fabrication. It lives at physical address `0x00000000` (and is aliased to `0x00100000`). You did not write it. NXP wrote it. It runs first at every power-on and every reset, on every i.MX6ULL ever shipped.

Its sole job is to load some other code (your bootloader, or your bare-metal image) into RAM and jump to it. Everything you ever do on this chip happens after the Boot ROM has finished its work.

Three useful facts about the Boot ROM:

1. **It is documented.** NXP publishes "Chapter 8, System Boot" of the i.MX6ULL Reference Manual specifically to describe ROM behavior. Read it before this chapter feels solid.
2. **It is the same across all i.MX6ULL chips** of a given silicon revision. Behavioral differences between dev boards are *not* in the ROM. They are in the boot pins and the boot-media contents.
3. **It is recoverable.** Even if every boot device on the board contains a bad image, you can still enter **USB Serial Download Protocol (SDP)** and push a new image directly into OCRAM over USB-OTG. We rely on this in Chapter 8.

## 7.2  The boot sequence, step by step

From POR_B rising to your `_start` executing, the i.MX6ULL Boot ROM performs roughly the following:

1. **Internal initialization.** Set up the watchdog, the ROM's own stack at the top of OCRAM, and a few CCM defaults.
> **CCM:** Clock Controller Module. It selects clock sources, dividers, and gates for the SoC.
2. **Sample boot fuses + boot pins.**
   - The ROM reads `OCOTP_CFG5[BT_FUSE_SEL]`. If that bit is set, the boot device is taken from the fuses in `OCOTP_CFG4`. If clear, it comes from the BOOT_MODE[1:0] pins together with the BOOT_CFG pins.
3. **Determine boot mode.**
   - `BOOT_MODE` = 0b00 → Boot from fuses (rare on dev boards).
   - `BOOT_MODE` = 0b01 → **Serial Downloader (SDP)**, wait for a host to push code over USB-OTG or UART. This is the recovery mode.
   - `BOOT_MODE` = 0b10 → **Internal boot**, read from the device selected by `BOOT_CFG`.
   - `BOOT_MODE` = 0b11 → Reserved.
4. *(Internal boot only)* **Probe the selected device.** SD card, eMMC, NAND, SPI-NOR, QSPI-NOR, or parallel NOR, each has a different probing path.
5. **Read the IVT at the fixed offset** for that device (per i.MX6ULL RM §8, Table 8-25 "First image / IVT offset per boot device"):
   - **SD / eMMC / eSD / SDXC**: IVT at offset **`0x400`** (1 KB into the boot device).
   - **SPI EEPROM (SPI-NOR)**: IVT at offset **`0x400`**.
   - **QSPI NOR**: IVT at offset **`0x1000`** (4 KB) on typical i.MX6ULL configurations, verify against your specific BSP / mkimage settings.
   - **Parallel NOR / EIM**: IVT at offset **`0x1000`** (4 KB).
   - **OneNAND**: IVT at offset **`0x100`** (256 B).
   - **Raw NAND** (non-OneNAND): handled via the **FCB (Firmware Configuration Block)**, the IVT does *not* live at a fixed offset. It is reached after the ROM parses the FCB. We do not cover raw-NAND boot in detail in this book.
6. **Validate the IVT.** Check its tag byte (`0xD1`), version, and self-pointer.
7. **Execute the DCD** if the IVT points to one. The DCD contains register operations that the ROM performs before loading the main image. It commonly configures clocks and DDR so the image can be loaded into DRAM.
8. **Load the image.** Read `BootData.length` bytes from the boot device into `BootData.start` (the destination address).
9. *(If HAB is enabled)* **Verify signatures.** Walk the CSF (Command Sequence File). If verification fails, halt.
10. **Jump to `IVT.entry`.** Control transfers to your image's entry point. From here on, your code controls the machine.

The sequence normally takes tens of milliseconds, depending on the boot medium and image size. The Boot ROM does not print progress messages to the debug UART. UART output begins only after loaded code initializes the UART and prints.

## 7.3  The IVT, Image Vector Table

The IVT is **32 bytes**, eight 32-bit words. Lay it out explicitly:

| Offset | Field | Description |
|--------|-------|-------------|
| `+0x00` | `header` | 4 bytes: `0xD1` tag, `0x00 0x20` big-endian length, and `0x40` or `0x41` version |
| `+0x04` | `entry` | Absolute address the ROM jumps to after image is loaded. |
| `+0x08` | `reserved1` | Must be `0x00000000`. |
| `+0x0C` | `dcd` | Absolute address of the DCD, or 0 if none. |
| `+0x10` | `boot_data` | Absolute address of the BootData structure. |
| `+0x14` | `self` | The IVT's own absolute address. **This is how the ROM knows the relocation offset.** |
| `+0x18` | `csf` | Address of the Command Sequence File (HAB signatures), or 0 if unsigned. |
| `+0x1C` | `reserved2` | Must be `0x00000000`. |

A few observations.

- **The `header` byte sequence `0xD1 0x00 0x20 0x40`** is the signature the ROM looks for. If you write the wrong byte order at offset 0, the ROM rejects the image with no diagnostic. You will see this byte pattern at offset `0x400` of every bootable SD card in this book.
- **The `self` field is required.** It is the IVT's own physical address. The ROM compares `self` against where it actually loaded the image and uses the difference to relocate `entry`, `dcd`, and `boot_data` if necessary. Getting `self` wrong is the most common way to make an otherwise correct image fail to boot.
- **All addresses in the IVT are absolute physical addresses**, not file offsets. The ROM understands that the image was at file offset `X` but ends up in OCRAM (or DRAM, post-DCD) at address `Y`, and it adjusts.

### A worked example

Walk it from the SD card to the CPU.

Assume we build a small bare-metal image for OCRAM:

```text
SD-card image file
  offset 0x0000..0x03FF   padding / unused by the ROM
  offset 0x0400           IVT begins here
  offset 0x0420           BootData begins here
  offset 0x1400           our code begins here
```

For this image, we choose:

| Thing | Value | Meaning |
|-------|-------|---------|
| SD-card IVT offset | `0x400` | Where the ROM expects the IVT on SD/MMC boot. |
| OCRAM load address | `0x00907400` | Where the IVT and image will live in RAM. |
| Code entry address | `0x00908400` | `0x00907400 + 0x1000`, because we leave a 4 KB pad before code. |

Now the ROM flow:

1. The ROM reads from SD-card offset `0x400` and checks for the IVT header bytes `D1 00 20 40`.
2. The IVT says `self = 0x00907400`, so the ROM knows the IVT is meant to live at OCRAM address `0x00907400`.
3. The IVT points to BootData at `0x00907420`. That is `0x00907400 + 0x20`: the IVT starts at `0x00907400` and is 32 bytes (`0x20`) long, so BootData sits immediately after it.
4. If the IVT has a DCD pointer, the ROM runs those register writes. For this small OCRAM-only example, we use `dcd = 0`, so there is no DCD work.
5. BootData says `start = 0x00907400` and `length = total image size`, so the ROM copies that many bytes from the SD card into OCRAM starting at `0x00907400`.
6. The ROM jumps to the IVT's `entry` address, `0x00908400`.

So the same bytes have a file offset before loading and an OCRAM address after loading:

| File view | RAM view after ROM load |
|-----------|-------------------------|
| SD offset `0x0400` | OCRAM address `0x00907400` |
| SD offset `0x0420` | OCRAM address `0x00907420` |
| SD offset `0x1400` | OCRAM address `0x00908400` |

In OCRAM at address `0x00907400`, the IVT contains:

```
Offset    Field      Value
+0x00     header     0xD1 0x00 0x20 0x40
+0x04     entry      0x00908400
+0x08     reserved1  0x00000000
+0x0C     dcd        0x00000000   (no DCD for this tiny OCRAM-only image)
+0x10     boot_data  0x00907420   (BootData starts immediately after IVT)
+0x14     self       0x00907400   ← the address of this IVT
+0x18     csf        0x00000000   (no signature)
+0x1C     reserved2  0x00000000
```

We will build exactly this layout in Chapter 11.

## 7.4  BootData, telling the ROM how big the image is

BootData is **12 bytes**:

| Offset | Field | Description |
|--------|-------|-------------|
| `+0x00` | `start` | Physical address to load the image to. |
| `+0x04` | `length` | Number of bytes to load (including the IVT, DCD, and padding). |
| `+0x08` | `plugin` | 0 = normal image. A nonzero value selects a plugin image. We will not use plugins. |

`length` covers the complete range loaded into memory, including the IVT, optional DCD, BootData, padding, and program bytes. If it covers only the program code, later data may not be loaded.

## 7.5  The DCD, Device Configuration Data

The DCD is powerful, but the reference-manual explanation is short.

The DCD is a list of operations that the Boot ROM performs before loading the main image. Its main use is to initialize the **DDR controller**, allowing the ROM to load a large image into DRAM instead of OCRAM.

Each DCD entry is one instruction in a small, one-byte-opcode language:

| Opcode | Name | Description |
|--------|------|-------------|
| `0xCC` | WRITE | Write value(s) to register(s) |
| `0xCF` | CHECK | Poll register until condition is met |
| `0xC0` | NOP | No-op |

The reference manual defines additional commands. WRITE and CHECK are the commands most relevant to the examples in this book.

### WRITE format

```
0xCC <length:2-bytes-BE> <flags:1-byte> <addr0:4> <val0:4> <addr1:4> <val1:4> ...
```

`flags` selects the write width, byte/halfword/word (bits 3:2), and the operation, "set bits" / "clear bits" / "write" (bits 1:0). The most common flags byte is `0x04` ("write 32-bit words").

### CHECK format

```
0xCF <length:2-bytes-BE> <flags:1-byte> <addr:4> <mask:4>
```

Reads `addr`, ANDs with `mask`, loops until the condition specified by flags is met. Typically used for "wait until PLL locked."

### A minimal DCD

A DCD that does nothing more than write `0x12345678` to `0x80000000` and then complete looks like:

```
0xD2 0x00 0x10 0x40      # DCD header, 16 bytes total
0xCC 0x00 0x0C 0x04      # WRITE command, 12 bytes, 32-bit width
0x80 0x00 0x00 0x00      # address = 0x80000000
0x12 0x34 0x56 0x78      # value
```

This DCD is 16 bytes total: a 4-byte DCD header followed by one 12-byte WRITE command. A DDR initialization DCD is often several hundred bytes because it contains many register writes.

### Why DCD exists

You could, in principle, do all of this in your own startup code instead of in DCD. People do. Two reasons to use DCD anyway:

1. **You may need DRAM up *before* your image is loaded.** If your image is bigger than OCRAM (128 KB), the only way to use it is for the ROM to load it into DRAM. The ROM can only load into DRAM after DDR is initialized, and the ROM cannot initialize DDR on its own. The DCD is the script you hand it that does that initialization.
2. **Some peripherals need very early init.** Bringing up clocks to specific peripherals before your code runs can simplify SPL.

For a small bare-metal image that runs from OCRAM, the IVT can set the DCD pointer to zero. The program can initialize DDR later if needed. The Chapter 11 image follows this design because it fits in OCRAM.

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

The Point Atom MINI boot selector exposes four labeled modes: **SD**, **eMMC**, **NAND**, and **USB**. SD, eMMC, and NAND are internal-boot configurations. USB selects Serial Downloader mode. The fitted storage depends on the core-board variant.

### Serial Downloader (BOOT_MODE = 01)

The ROM enumerates as a USB device on the USB-OTG port (VID `0x15A2`, PID `0x0080` for i.MX6ULL). It also listens for SDP commands on **UART1**, but USB is overwhelmingly the practical choice.

In SDP mode the ROM accepts a small command set:

- `0x0101` READ_REGISTER
- `0x0202` WRITE_REGISTER
- `0x0404` WRITE_FILE, push bytes to a target address
- `0x0505` ERROR_STATUS
- `0x0808` DCD_WRITE
- `0x0A0A` JUMP_ADDRESS, jump to a previously-loaded address

`uuu` and `imx_usb_loader` send these commands for you. A typical sequence uses `WRITE_FILE` to place an IMX image in RAM and `JUMP_ADDRESS` to start it.

USB mode provides the recovery path used throughout this book. If the Boot ROM enters SDP and accepts commands, software can still be loaded without relying on the installed flash contents.

## 7.7  The .imx image format

Putting it all together, an `.imx` file (the artifact you `dd` to an SD card) has this layout:

```
File offset    Content
0x0000         (1 KB of padding, sometimes contains partition table or zero)
0x0400         ┌─ IVT (32 bytes)
0x0420         │  DCD (variable, typically 16 to ~800 bytes, may be absent)
0x04XX         │  BootData (12 bytes)
0x0500ish      │  more padding
0x1000         │  Application image proper (.text, .rodata, .data)
   ...         │
              ─┘  end after BootData.length bytes
```

The exact layout is partly your choice, within the constraint that IVT.self must equal the load address of IVT, IVT.entry must point to where the application begins, and BootData.length must cover everything up to the last byte you want loaded.

Tools that generate `.imx` files:

- `mkimage -T imximage -n image.cfg -d app.bin app.imx`: the U-Boot tool. Takes a `.cfg` describing DCD writes and produces the final image.
- `imx-mkimage`: NXP's standalone tool, used by their OS BSPs.
- **Your own script in Chapter 11.** We will write a 60-line Python program that emits an `.imx` file byte-by-byte, with no `mkimage`.

Writing the format once makes later `mkimage` and U-Boot configuration easier to understand.

## 7.8  HAB, High Assurance Boot, briefly

If `IVT.csf` is nonzero, the ROM jumps to a verification routine before executing your code. This is **HAB (High Assurance Boot)**, NXP's secure boot scheme. It uses the **SRK (Super Root Key)** hash burned into fuses, an X.509 certificate chain stored in your image, and a CST-generated signature.

On a freshly-fabricated chip, HAB is in "open" mode, verification is performed but failures do not stop the boot. Once you burn the `SEC_CONFIG[1]` fuse, HAB is in "closed" mode, failures stop the boot, permanently. There is no recovery from a botched closed-mode signing.

We will not enable HAB in Parts I-VI of this book. Chapter 124 covers the full HAB workflow, including how to sign U-Boot and the kernel and how to extend verification to the root filesystem.

For now: leave `IVT.csf = 0`. Do not touch SEC_CONFIG fuses.

## 7.9  How to inspect an .imx image

After Chapter 11 creates an `.imx` file, inspect it with:

```sh
$ dumpimage -l app.imx
$ xxd -s 0x400 -l 32 app.imx
```

For the worked example in Section 7.3, the 32 IVT bytes at file offset `0x400` are:

```text
d1 00 20 40  00 84 90 00  00 00 00 00  00 00 00 00
20 74 90 00  00 74 90 00  00 00 00 00  00 00 00 00
```

The header stores its length bytes in big-endian order, as required by the IVT format. The pointer fields are 32-bit little-endian values:

| Bytes | Field | Decoded value |
|-------|-------|---------------|
| `d1 00 20 40` | header | tag `0xD1`, length 32, version `0x40` |
| `00 84 90 00` | entry | `0x00908400` |
| `00 00 00 00` | reserved1 | 0 |
| `00 00 00 00` | dcd | no DCD |
| `20 74 90 00` | boot_data | `0x00907420` |
| `00 74 90 00` | self | `0x00907400` |
| `00 00 00 00` | csf | unsigned image |
| `00 00 00 00` | reserved2 | 0 |

This gives you a known byte sequence to compare against the image builder in Chapter 11.

## 7.10  Lab

Two short exercises, mostly reading.

### Lab A, Find your board's boot pins

From the Point Atom MINI schematic, locate:

1. The `BOOT_MODE0` and `BOOT_MODE1` pins. What do their default pull resistors do?
2. The `BOOT_CFG1[7:0]` pins. Which physical pin (on the SoC ball-out) becomes which BOOT_CFG bit?
3. The selector patterns for SD, eMMC, NAND, and USB modes.
4. Whether your core-board variant contains eMMC or raw NAND.

Write the wiring in `~/imx6ull/notes/ch07-boot-pins.md`. Photograph the relevant section of the schematic if helpful.

### Lab B, Decode the worked IVT

Use the 32 bytes in Section 7.9. Without looking at its decoded table, split the bytes into the eight IVT fields and decode each pointer as little-endian.

Verify these three relationships:

1. `boot_data = self + 0x20`.
2. `entry = self + 0x1000`.
3. `dcd = 0` and `csf = 0`.

Chapter 11 repeats the exercise with an `.imx` file built by our own script.

## 7.11  Pitfalls

- **`IVT.self` mismatched with actual load address.** Symptom: the board reads the image, but does not branch to your entry. The ROM does branch, to the wrong place. Always set `self` to where the IVT *will be after loading*, not where it lives in the file.
- **`BootData.length` shorter than the image.** Tail of your image is not loaded. `.data` initial values become whatever was in RAM.
- **DCD CHECK that never completes.** If a `CHECK` waits for a bit that never changes, the ROM cannot continue. Set the board selector to USB mode and load a corrected image through SDP.
- **Wrong endianness in DCD header length.** The DCD header length is **big-endian**. Get this wrong, and the ROM either ignores the DCD or executes wrong data.
- **Forgetting the 1 KB pre-IVT padding.** On SD/MMC the IVT lives at offset `0x400`, not at offset 0. Partitioning tools can use the first 1 KB without touching the IVT.
- **Closing HAB by accident.** It is a one-way fuse. Do not write to OCOTP_CFG5 unless you have read Chapter 124 carefully and have a key-management plan.

## 7.12  Going deeper

- **IMX6ULLRM**, *Chapter 8, System Boot*. The authoritative reference.
- **AN12055**: *Boot from CMOS NAND for the i.MX 6UL/6ULL*.
- **AN12056**: *Boot from QSPI Flash on i.MX 6UL/6ULL*.
- **AN4581**: *i.MX 6 Series Boot Process*.
- U-Boot `tools/mkimage.c` and `tools/imximage.c`, which implement the production image-generation path.
- The `imx-mkimage` repository at `<https://github.com/nxp-imx/imx-mkimage>`.

> Next chapter: **Chapter 8: Hardware bring-up checklist.** We verify power, serial access, boot-mode selection, and USB SDP before running our own code.
