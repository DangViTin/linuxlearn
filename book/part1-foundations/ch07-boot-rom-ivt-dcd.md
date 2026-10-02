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
> **Focus:** the IVT is 32 bytes, BootData is 12 bytes, and DCD is variable-length. Their pointer, size, and placement relationships form the loading contract.


## 7.1  What the Boot ROM is

The Boot ROM is NXP's mask-programmed code at physical `0x00000000`: the documented region totals 96 KiB, including a protected area. `0x00100000` is reserved in this SoC's map, not a documented ROM alias. This chapter follows normal cold boot; low-power wake paths and ROM runtime APIs are separate topics.

On this path it selects a source, interprets image metadata, loads code, and hands off. Hardware, boot configuration, and authentication policy still constrain recovery.

Three useful facts about the Boot ROM:

1. **It is documented.** NXP publishes "Chapter 8, System Boot" of the i.MX6ULL Reference Manual specifically to describe ROM behavior. Read it before this chapter feels solid.
2. **It is the same across all i.MX6ULL chips** of a given silicon revision. Behavioral differences between dev boards are *not* in the ROM. They are in the boot pins and the boot-media contents.
3. **SDP is a recovery path.** With functional power/reset/USB hardware and a permitted image, USB Serial Download Protocol can load code without working storage. Chapter 8 checks enumeration; Chapter 9 transfers our first image. Closed-mode authentication is not bypassed by USB mode.

## 7.2  The boot sequence, step by step

From POR_B rising to your `_start` executing, the i.MX6ULL Boot ROM performs roughly the following:

1. **Internal initialization.** Set up the watchdog, the ROM's own stack at the top of OCRAM, and a few CCM defaults.
> **CCM:** Clock Controller Module. It selects clock sources, dividers, and gates for the SoC.
2. **Sample boot mode and configuration.** BOOT_MODE is the first decision; the meaning of `BT_FUSE_SEL` depends on that mode. See the decision table below [RM 8.2.3 and Table 8-2]. No fuse programming is required here.
3. **Select the source or downloader.** Internal boot uses either fuse configuration or the sampled GPIO override according to that decision, not a global "clear means pins" rule.
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
9. **Apply HAB authentication policy.** Closed mode rejects unauthenticated images; open mode can report authentication failures without preventing execution. SDP follows authentication policy too.
10. **Jump to `IVT.entry`.** Control transfers to your image's entry point. From here on, your code controls the machine.

The sequence normally takes tens of milliseconds, depending on the boot medium and image size. The Boot ROM does not print progress messages to the debug UART. UART output begins only after loaded code initializes the UART and prints.

| BOOT_MODE[1:0] | BT_FUSE_SEL clear | BT_FUSE_SEL set |
|---|---|---|
| `00`, Boot From Fuses | Enter Serial Downloader | Boot using fuse configuration |
| `01`, Serial Downloader | Enter SDP | Enter SDP, subject to security policy |
| `10`, Internal Boot | Use GPIO boot-configuration override | Use fuse boot configuration |
| `11` | Reserved | Reserved |

A board switch label such as "USB" encodes this SoC mode through wiring; it is not a third protocol beyond SDP.

## 7.3  The IVT, Image Vector Table

The IVT is **32 bytes**, eight 32-bit words. Lay it out explicitly:

| Offset | Field | Description |
|--------|-------|-------------|
| `+0x00` | `header` | 4 bytes: `0xD1` tag, `0x00 0x20` big-endian length, and `0x40` or `0x41` version |
| `+0x04` | `entry` | Absolute address the ROM jumps to after image is loaded. |
| `+0x08` | `reserved1` | Must be `0x00000000`. |
| `+0x0C` | `dcd` | Absolute address of the DCD, or 0 if none. |
| `+0x10` | `boot_data` | Absolute address of the BootData structure. |
| `+0x14` | `self` | The IVT's intended absolute address; pointer differences locate accompanying structures. |
| `+0x18` | `csf` | Address of the Command Sequence File (HAB signatures), or 0 if unsigned. |
| `+0x1C` | `reserved2` | Must be `0x00000000`. |

A few observations.

- **The `header` byte sequence `0xD1 0x00 0x20 0x40`** is the signature the ROM looks for. If you write the wrong byte order at offset 0, the ROM rejects the image with no diagnostic. You will see this byte pattern at offset `0x400` of every bootable SD card in this book.
- **`self` is required.** The ROM can initially read a header into temporary storage. A structure's relative position is found through its absolute-pointer difference from `self`. For this file, `structure_file_offset = 0x400 + (structure_pointer - self)`.
- **IVT pointers are absolute physical addresses**, not file offsets. Final `entry` must agree with linked code at the final destination. This header handling does not promise relocation of arbitrary machine code or repair of its embedded references.

### A worked example

Walk it from the SD card to the CPU.

Assume we build a small bare-metal image for OCRAM:

```text
SD-card image file
  offset 0x0000..0x03FF   padding / unused by the ROM
  offset 0x0400           IVT begins here
  offset 0x0420           BootData begins here
  offset 0x1000           our code begins here
```

For this image, we choose:

| Thing | Value | Meaning |
|-------|-------|---------|
| SD-card IVT offset | `0x400` | Where the ROM expects the IVT on SD/MMC boot. |
| Image start in OCRAM | `0x00907000` | File offset 0 corresponds to this RAM address. |
| IVT address in OCRAM | `0x00907400` | `0x00907000 + 0x400`, matching the IVT's file offset. |
| Code entry address | `0x00908000` | `0x00907000 + 0x1000`, matching the code's file offset. |

Now the ROM flow:

1. The ROM reads from SD-card offset `0x400` and checks for the IVT header bytes `D1 00 20 40`.
2. The IVT says `self = 0x00907400`, so the ROM knows the IVT is meant to live at OCRAM address `0x00907400`.
3. The IVT points to BootData at `0x00907420`. That is `0x00907400 + 0x20`: the IVT starts at `0x00907400` and is 32 bytes (`0x20`) long, so BootData sits immediately after it.
4. If the IVT has a DCD pointer, the ROM runs those register writes. For this small OCRAM-only example, we use `dcd = 0`, so there is no DCD work.
5. BootData says `start = 0x00907000` and `length = total file size`. The `self - start` difference is `0x400`, matching the IVT's offset in the file.
6. The ROM jumps to the IVT's `entry` address, `0x00908000`.

So the same bytes have a file offset before loading and an OCRAM address after loading:

| File view | RAM view after ROM load |
|-----------|-------------------------|
| SD offset `0x0000` | OCRAM address `0x00907000` |
| SD offset `0x0400` | OCRAM address `0x00907400` |
| SD offset `0x0420` | OCRAM address `0x00907420` |
| SD offset `0x1000` | OCRAM address `0x00908000` |

In OCRAM at address `0x00907400`, the IVT contains:

```
Offset    Field      Value
+0x00     header     0xD1 0x00 0x20 0x40
+0x04     entry      0x00908000
+0x08     reserved1  0x00000000
+0x0C     dcd        0x00000000   (no DCD for this tiny OCRAM-only image)
+0x10     boot_data  0x00907420   (BootData starts immediately after IVT)
+0x14     self       0x00907400   ← the address of this IVT
+0x18     csf        0x00000000   (no signature)
+0x1C     reserved2  0x00000000
```

Chapter 9 supplies the first small wrapper; Chapter 11 generalizes it. The first no-DCD image uses this same layout and fits below the ROM-active limit in Chapter 5.

## 7.4  BootData, telling the ROM how big the image is

BootData is **12 bytes**:

| Offset | Field | Description |
|--------|-------|-------------|
| `+0x00` | `start` | Physical address to load the image to. |
| `+0x04` | `length` | Number of bytes to load (including the IVT, DCD, and padding). |
| `+0x08` | `plugin` | 0 = normal image. A nonzero value selects a plugin image. We will not use plugins. |

For the book's padded file, `start` corresponds to file offset zero and `length` is the complete file size, including padding and headers. For another image generator, derive the relationship from its layout rather than its `.imx` extension. A length covering only code can omit later data.

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

The parameter uses width in **bits 2:0** as a byte count; **bit 3** is Mask and **bit 4** is Set [RM Tables 8-29/8-30]. All address/value pairs in one command use that parameter:

```text
bits:        7 6 5 | 4   | 3    | 2 1 0
             0 0 0 | Set | Mask | width
0x04:        0 0 0 | 0   | 0    | 1 0 0   plain 32-bit write
0x0C:        0 0 0 | 0   | 1    | 1 0 0   clear selected word bits
0x1C:        0 0 0 | 1   | 1    | 1 0 0   set selected word bits
```

Addresses and values in these command records are big-endian, unlike the IVT pointer words.

### CHECK format

```
0xCF <length:2-bytes-BE> <flags:1-byte> <addr:4> <mask:4>
```

Reads `addr`, ANDs with `mask`, loops until the condition specified by flags is met. Typically used for "wait until PLL locked."

### A minimal DCD

**Format-only, not a runnable DDR setup:** this byte record would write `0x12345678` to `0x80000000`. Do not submit it on a freshly reset board: DDR at that address has not been initialized. The first OCRAM image uses no DCD.

```
0xD2 0x00 0x10 0x40      # DCD header, 16 bytes total
0xCC 0x00 0x0C 0x04      # WRITE command, 12 bytes, 32-bit width
0x80 0x00 0x00 0x00      # address = 0x80000000
0x12 0x34 0x56 0x78      # value
```

This DCD is 16 bytes total: a 4-byte DCD header followed by one 12-byte WRITE command. A DDR initialization DCD is often several hundred bytes because it contains many register writes.

The supplied RM specifies DCD version `0x41`, while [U-Boot v2024.01's image constants](https://github.com/u-boot/u-boot/blob/v2024.01/include/imximage.h) use `0x40`, as shown in the illustrative record. Do not infer board compatibility from this source disagreement; verify the selected DCD/tool/silicon combination when using DCD later. The documented maximum DCD size is 1,768 bytes.

### Why DCD exists

You could, in principle, do all of this in your own startup code instead of in DCD. People do. Two reasons to use DCD anyway:

1. **A monolithic ROM-loaded image may need DDR before loading.** DCD initializes it before that transfer. Another valid design loads a small OCRAM SPL, which initializes DDR and loads later code itself. The ROM-active free window is smaller than physical OCRAM, as Chapter 5 explains.
2. **Some peripherals need very early init.** Bringing up clocks to specific peripherals before your code runs can simplify SPL.

For a small bare-metal image that runs from OCRAM, the IVT can set the DCD pointer to zero. The program can initialize DDR later if needed. The Chapter 11 image follows this design because it fits in OCRAM.

## 7.6  Boot modes, in concrete detail

Re-summarizing §7.2 step 3 with the actual signals:

### Internal Boot (BOOT_MODE = 10)

The ROM reads `BOOT_CFG1[7:0]`, `BOOT_CFG2[7:0]`, `BOOT_CFG4[7:0]` from the boot-mode pins (or from fuses if `BT_FUSE_SEL` is set). The bit patterns encode:

| Device-class field | Meaning | Additional configuration |
|---|---|---|
| `BOOT_CFG1[7:6] = 01` | SD/MMC class | Controller, width, speed/protocol and other fields in RM SD/MMC tables |
| `BOOT_CFG1[7] = 1` | NAND class | Geometry and NAND-specific boot configuration |
| `BOOT_CFG1[7:4] = 0011` | Serial ROM through ECSPI | Port/chip-select/addressing fields, RM Table 8-20 |
| `BOOT_CFG1[7:4] = 0001` | QuadSPI class | Interface and other fields, RM Table 8-22; interface bit 3 value 1 is reserved |

These are class fields, not complete magic bytes for an "8-bit DDR eMMC" setup. Board wiring supplies additional bits. Chapter 8 decodes the reference selector; do not change arbitrary boot-configuration pins or burn fuses.

The Point Atom MINI boot selector exposes four labeled modes: **SD**, **eMMC**, **NAND**, and **USB**. SD, eMMC, and NAND are internal-boot configurations. USB selects Serial Downloader mode. The fitted storage depends on the core-board variant.

### Serial Downloader (BOOT_MODE = 01)

The ROM enumerates as a USB device on the USB-OTG port (VID `0x15A2`, PID `0x0080` for i.MX6ULL). It also listens for SDP commands on **UART1**, but USB is overwhelmingly the practical choice.

In SDP mode the ROM accepts a small command set:

- `0x0101` READ_REGISTER
- `0x0202` WRITE_REGISTER
- `0x0404` WRITE_FILE, push bytes to a target address
- `0x0505` ERROR_STATUS
- `0x0A0A` DCD_WRITE
- `0x0B0B` JUMP_ADDRESS, process a previously-loaded image's IVT

These identifiers come from RM Table 8-42; this is a protocol reference, not a request to implement SDP. `uuu` handles the transfer/handshake. For our image it uploads the IVT and following bytes, then asks the ROM to process that IVT; the final branch destination is `IVT.entry`.

USB mode provides the recovery path used throughout this book. If the Boot ROM enters SDP and accepts commands, software can still be loaded without relying on the installed flash contents.

## 7.7  The .imx image format

The extension alone does not specify placement. **The book's padded raw image** has this no-DCD layout and is written at card byte zero:

```
File offset    Content
0x0000         1 KB padding; no partition table in the tiny Part II image
0x0400         ┌─ IVT (32 bytes)
0x0420         │  BootData (12 bytes)
0x042C         │  padding (a later DCD layout must define its own location)
0x1000         │  Application image proper (.text, .rodata, .data)
   ...         │
              ─┘  end after BootData.length bytes
```

The exact layout is partly your choice, within the constraint that IVT.self must equal the load address of IVT, IVT.entry must point to where the application begins, and BootData.length must cover everything up to the last byte you want loaded.

Two placement conventions must not be mixed:

| Artifact | IVT file offset | Card write offset | Resulting IVT card offset |
|---|---|---|---|
| Book's padded raw image | `0x400` | `0` | `0x400` |
| Conventional IVT-first `mkimage` boot blob | `0` | `0x400` | `0x400` |

Check the actual generator/version before writing. The small Part II card has no partitions. When a later Linux image adds partitions, reserve the boot region explicitly; ordinary GPT puts its primary partition-entry array at LBA 2, conflicting with an IVT at byte `0x400`. A later-starting MBR partition layout is a different contract. See [UEFI GPT layout](https://uefi.org/specs/UEFI/2.10/05_GUID_Partition_Table_Format.html).

Tools that can generate IMX boot artifacts:

- `mkimage -T imximage -n image.cfg -d app.bin app.imx`: syntax illustration only, not a runnable alternative here. It needs a supplied configuration, entry/load settings, and a placement check. See [U-Boot v2024.01 imximage.c](https://github.com/u-boot/u-boot/blob/v2024.01/tools/imximage.c).
- `imx-mkimage`: NXP's standalone tool, used by their OS BSPs.
- **Your own script in Chapter 11.** We will write a 60-line Python program that emits an `.imx` file byte-by-byte, with no `mkimage`.

Writing the format once makes later `mkimage` and U-Boot configuration easier to understand.

## 7.8  HAB, High Assurance Boot, briefly

If `IVT.csf` is nonzero, the ROM jumps to a verification routine before executing your code. This is **HAB (High Assurance Boot)**, NXP's secure boot scheme. It uses the **SRK (Super Root Key)** hash burned into fuses, an X.509 certificate chain stored in your image, and a CST-generated signature.

Open-mode authentication failures do not necessarily block execution. Closed-mode policy requires valid authentication; closing the device is irreversible. An incorrectly signed image can sometimes be replaced through an authenticated recovery path using the provisioned trust configuration. Lost signing keys or unusable trust provisioning are different, potentially unrecoverable failures. SDP does not bypass closed-mode authentication.

We will not enable HAB in Parts I-VI of this book. Chapter 124 covers the full HAB workflow, including how to sign U-Boot and the kernel and how to extend verification to the root filesystem.

For now: leave `IVT.csf = 0`. Do not touch SEC_CONFIG fuses.

## 7.9  How to inspect an .imx image

After Chapter 11 creates an `.imx` file, inspect it with:

```sh
$ xxd -s 0x400 -l 32 app.imx
```

For the worked example in Section 7.3, the 32 IVT bytes at file offset `0x400` are:

```text
d1 00 20 40  00 80 90 00  00 00 00 00  00 00 00 00
20 74 90 00  00 74 90 00  00 00 00 00  00 00 00 00
```

The header stores its length bytes in big-endian order, as required by the IVT format. The pointer fields are 32-bit little-endian values:

| Bytes | Field | Decoded value |
|-------|-------|---------------|
| `d1 00 20 40` | header | tag `0xD1`, length 32, version `0x40` |
| `00 80 90 00` | entry | `0x00908000` |
| `00 00 00 00` | reserved1 | 0 |
| `00 00 00 00` | dcd | no DCD |
| `20 74 90 00` | boot_data | `0x00907420` |
| `00 74 90 00` | self | `0x00907400` |
| `00 00 00 00` | csf | unsigned image |
| `00 00 00 00` | reserved2 | 0 |

This gives you a known byte sequence to compare against the image builder in Chapter 11.

Do not use `dumpimage -l` as a promised validator for this custom padded/no-DCD file: tool support depends on header placement and format. Inspect these exact bytes and pointer relationships first; successful structural checks still do not prove execution.

## 7.10  Lab

Two short exercises, mostly reading.

### Lab A, Find your board's boot pins

Use the MINI v2.2 and matching core schematics named in Chapter 5; other revisions need their own selector decode. Locate:

1. The `BOOT_MODE0` and `BOOT_MODE1` pins. What do their default pull resistors do?
2. The `BOOT_CFG1[7:0]` pins. Which physical pin (on the SoC ball-out) becomes which BOOT_CFG bit?
3. The selector patterns for SD, eMMC, NAND, and USB modes.
4. Whether your core-board variant contains eMMC or raw NAND.

Write the wiring in `~/imx6ull/notes/ch07-boot-pins.md`. Photograph the relevant section of the schematic if helpful.

### Lab B, Decode the worked IVT

Use the 32 bytes in Section 7.9. Without looking at its decoded table, split the bytes into the eight IVT fields and decode each pointer as little-endian.

Verify these three relationships:

1. `boot_data = self + 0x20`.
2. `entry = self + 0xC00`. The file offsets have the same difference: `0x1000 - 0x400 = 0xC00`.
3. `dcd = 0` and `csf = 0`.

Chapter 11 repeats the exercise with an `.imx` file built by our own script.

Answer check: `self=0x00907400`, `boot_data=0x00907420`, and `entry=0x00908000`. If you change only `entry` to `0x00908100`, it is no longer the first instruction at file `0x1000`; header arithmetic can expose that mismatch before any transfer. For Lab A, `BOOT_MODE[1:0]=01` must be the resulting USB selector state, regardless of whether the printed switch ON direction represents zero or one.

## 7.11  Pitfalls

- **`IVT.self` mismatched with actual load address.** Symptom: the board reads the image, but does not branch to your entry. The ROM does branch, to the wrong place. Always set `self` to where the IVT *will be after loading*, not where it lives in the file.
- **`BootData.length` shorter than the image.** Tail of your image is not loaded. `.data` initial values become whatever was in RAM.
- **DCD CHECK that never completes.** If a `CHECK` waits for a bit that never changes, the ROM cannot continue. Set the board selector to USB mode and load a corrected image through SDP.
- **Wrong endianness in DCD header length.** The DCD header length is **big-endian**. Get this wrong, and the ROM either ignores the DCD or executes wrong data.
- **Mixing file and media offsets.** The book's padded file goes at card byte zero; an IVT-first boot blob uses another write offset. Generic partitioning, especially GPT, can overwrite the boot region. Recheck the exact layout before writing.
- **Closing HAB by accident.** It is a one-way fuse. Do not write to OCOTP_CFG5 unless you have read Chapter 124 carefully and have a key-management plan.

## 7.12  Going deeper

- **IMX6ULLRM**, *Chapter 8, System Boot*. The authoritative reference.
- For NAND and QSPI, start with the device-specific sections of IMX6ULLRM Chapter 8. Verify actual application-note titles before relying on a note number; AN12055/AN12056 are not NAND/QSPI guides for this route.
- **AN4581**: *i.MX 6 Series Boot Process*.
- U-Boot `tools/mkimage.c` and `tools/imximage.c`, which implement the production image-generation path.
- The `imx-mkimage` repository at `<https://github.com/nxp-imx/imx-mkimage>`.

> Next chapter: **Chapter 8: Hardware bring-up checklist.** We verify power, serial access, boot-mode selection, and USB SDP before running our own code.
