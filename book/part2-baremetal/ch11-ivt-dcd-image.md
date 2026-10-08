# Chapter 11: Hand-building a Boot ROM-acceptable image

So far, every blink has needed a host upload. Can the same program start with only an SD card in the board?

The ROM does not need a filesystem for this small image. It looks for a boot structure at a particular media offset, reads the image into RAM and uses the entry field to start execution. We will inspect those bytes before writing them. The useful result is not merely an SD boot: it is knowing why the first instruction lands where the linker put it.

This remains an unsigned, OCRAM-only image for an open development device. A dedicated spare card is required for the SD route. USB loading can be completed without writing any card.


## 11.1  What we produced last chapter, in detail

Recap the structure of `led.imx` from Chapter 9, viewed as a sequence of file offsets:

```
file offset    content                                size
0x0000         (pad)                                  0x400 bytes
0x0400         IVT header                             4 bytes
0x0404         IVT.entry                              4 bytes
0x0408         IVT.reserved1                          4 bytes
0x040C         IVT.dcd                                4 bytes
0x0410         IVT.boot_data                          4 bytes
0x0414         IVT.self                               4 bytes
0x0418         IVT.csf                                4 bytes
0x041C         IVT.reserved2                          4 bytes
0x0420         BootData.start                         4 bytes
0x0424         BootData.length                        4 bytes
0x0428         BootData.plugin                        4 bytes
0x042C         (pad)                                  0xBD4 bytes
0x1000         _start                                 first instruction
0x1000+N       end of code
```

In SDP mode, `uuu` finds the IVT, skips the first `0x400` bytes, and uploads the IVT to its `self` address. In SD-card mode, we write the whole file at byte 0 of the card. The `0x400` bytes of padding in the file place the IVT at LBA 2, where the ROM expects it.

For this primary SD boot layout, the file starts at media byte zero and its IVT lands at byte `0x400`. Other boot areas, secondary-image settings and devices need their own placement checks. Do not turn this example into a rule for every eMMC configuration.

```{figure} ../illustrations/part2/03-image-and-card-offset-v2.png
:alt: The padded image file and primary SD card layout begin at byte zero. Their IVT starts at offset 0x400, with BootData and padding before code at offset 0x1000.
:width: 100%
:figclass: concept-sketch
:name: fig-part2-image-card-offset

The file already supplies the gap before its IVT. Adding another gap at the card would shift the structure away from the expected offset. These are file and media coordinates, not RAM addresses. Block widths are not to scale.
```

## 11.2  `mkimx.py`, our own image builder
Save as `~/imx6ull/scripts/mkimx.py`:

```python
#!/usr/bin/env python3
"""
mkimx.py -- build an i.MX6ULL boot image from a flat binary.

The output is a file that:
  - Has a 0x400-byte leading pad before the primary SD IVT.
  - Then an IVT at file offset 0x400 (= byte 1024).
  - Then BootData immediately after the IVT.
  - Then padding to offset 0x1000.
  - Then the user binary at file offset 0x1000.

Usage:
  mkimx.py <input.bin> <output.imx>
"""
import argparse
import struct
from pathlib import Path

IVT_TAG       = 0xD1
IVT_LENGTH    = 0x0020   # 32 bytes, big-endian per spec
IVT_VERSION   = 0x40

IVT_OFFSET    = 0x400    # IVT offset from the beginning of the file
CODE_OFFSET   = 0x1000   # user binary offset from the beginning of the file

def ivt_header():
    # The IVT header is 4 bytes:
    #   byte 0 = tag (0xD1)
    #   byte 1-2 = length (BIG endian, 16-bit)
    #   byte 3 = version (0x40 = HAB v4)
    return struct.pack('>BHB', IVT_TAG, IVT_LENGTH, IVT_VERSION)

def build(input_bin: str, output_imx: str, image_start: int):
    with open(input_bin, 'rb') as f:
        code = f.read()

    if Path(input_bin).resolve() == Path(output_imx).resolve():
        raise ValueError('Input and output paths must differ')
    if image_start < 0x00907000 or image_start % 32:
        raise ValueError('Use a 32-byte-aligned base in the free OCRAM window')
    if not code or image_start + CODE_OFFSET + len(code) > 0x00918000:
        raise ValueError('Payload must be nonempty and fit ROM-active OCRAM')

    ivt_addr        = image_start + IVT_OFFSET
    bootdata_addr   = ivt_addr + 0x20
    entry_addr      = image_start + CODE_OFFSET
    csf_addr        = 0
    dcd_addr        = 0
    image_size      = CODE_OFFSET + len(code)

    # IVT: header (4) + 7 little-endian words = 32 bytes
    ivt  = ivt_header()
    ivt += struct.pack('<IIIIIII',
        entry_addr,
        0,                  # reserved1
        dcd_addr,
        bootdata_addr,
        ivt_addr,           # self
        csf_addr,
        0)                  # reserved2

    assert len(ivt) == 0x20, len(ivt)

    # BootData: start, length, plugin
    bootdata = struct.pack('<III', image_start, image_size, 0)
    assert len(bootdata) == 12

    # Lay out the complete file header, including the leading 0x400 bytes.
    header = bytearray(CODE_OFFSET)
    header[IVT_OFFSET:IVT_OFFSET + 0x20] = ivt
    header[IVT_OFFSET + 0x20:IVT_OFFSET + 0x2C] = bootdata

    out = bytes(header) + code

    # UUU uploads the IVT at ivt_addr. The code must then land at entry_addr.
    loaded_code_addr = ivt_addr + (CODE_OFFSET - IVT_OFFSET)
    assert loaded_code_addr == entry_addr

    with open(output_imx, 'wb') as f:
        f.write(out)

    print(f"  image  = 0x{image_start:08X}")
    print(f"  entry  = 0x{entry_addr:08X}")
    print(f"  IVT    @ 0x{ivt_addr:08X}  (file offset 0x{IVT_OFFSET:04X})")
    print(f"  bdata  @ 0x{bootdata_addr:08X}")
    print(f"  code   @ 0x{entry_addr:08X}  (file offset 0x{CODE_OFFSET:04X})")
    print(f"  total  = {len(out)} bytes")
    print(f"  wrote  {output_imx}")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('input')
    ap.add_argument('output')
    ap.add_argument('--image-start', type=lambda s: int(s, 0),
                    default=0x00907000,
                    help='RAM address corresponding to file offset 0')
    args = ap.parse_args()
    try:
        build(args.input, args.output, args.image_start)
    except (OSError, ValueError) as exc:
        ap.error(str(exc))

if __name__ == '__main__':
    main()
```

Run the script with `python3`, so it needs no executable-permission change. It builds the same simple layout as Chapter 9, with input and output filenames supplied explicitly. DCD, DDR-resident images and signatures are outside this tool's scope.

- **The length field in the IVT header is big-endian.** Everything else in the IVT is little-endian. The `struct.pack('>BHB', ...)` line handles this difference. This is the most common "I wrote my own mkimage and the ROM rejects it" bug.
- **`BootData.start` is `0x00907000`.** File offset `0` corresponds to that address. The IVT at file offset `0x400` therefore corresponds to `0x00907400`.
- **`BootData.length` includes all bytes through the end of the code.** It is not only the code size. If you forget the `CODE_OFFSET` part, the ROM stops loading before your `.text` begins.
- **`csf_addr = 0`** says this image provides no Command Sequence File for HAB authentication. It does **not** disable the device's security policy or bypass authentication on a closed device. Our unsigned lab depends on an open development configuration. Do not program fuses to make it run. Chapter 124 covers signed boot.

## 11.3  Building and inspecting

Rebuild Chapter 10's LED:

```sh
$ cd ~/imx6ull/src/ch10-c-startup
$ make
$ python3 ~/imx6ull/scripts/mkimx.py led.bin led.imx
  image  = 0x00907000
  entry  = 0x00908000
  IVT    @ 0x00907400  (file offset 0x0400)
  bdata  @ 0x00907420
  code   @ 0x00908000  (file offset 0x1000)
  total  = ... bytes
  wrote  led.imx
```

Source `~/imx6ull/scripts/env.sh` first in a new build terminal. The total size depends on your `led.bin`. The address lines must match this default layout. The builder keeps its offsets consistent, but it cannot discover how the input binary was linked. Check the ELF entry and first instruction as well. In Chapter 10, that instruction is the vector-slot branch to `_start`.

Verify the IVT with raw `xxd`:

```sh
$ xxd -s 0x400 -l 32 led.imx
00000400: d100 2040 0080 9000 0000 0000 0000 0000  .. @............
00000410: 2074 9000 0074 9000 0000 0000 0000 0000   t...t..........
$ xxd -s 0x420 -l 4 led.imx
00000420: 0070 9000                                .p..
```

Decode:

| Word | Bytes (LE) | Value | Field |
|------|-----------|-------|-------|
| `0x400` | `D1 00 20 40` | tag/length/version (big-endian length!) | IVT header |
| `0x404` | `00 80 90 00` | `0x00908000` | entry ✓ |
| `0x408` | `00 00 00 00` | 0 | reserved1 |
| `0x40C` | `00 00 00 00` | 0 | dcd (none) |
| `0x410` | `20 74 90 00` | `0x00907420` | boot_data ✓ |
| `0x414` | `00 74 90 00` | `0x00907400` | self ✓ |
| `0x418` | `00 00 00 00` | 0 | csf |
| `0x41C` | `00 00 00 00` | 0 | reserved2 |
| `0x420` | `00 70 90 00` | `0x00907000` | BootData.start ✓ |
| `0x424` | Varies | Complete file size | BootData.length |
| `0x428` | `00 00 00 00` | 0 | BootData.plugin |

`BootData.length` must equal the complete file size. It covers the leading pad, IVT, BootData, padding, and program code.

## 11.4  Path A, SDP push, again

Push to the board exactly as in Chapter 9:

```sh
$ sudo "$IMX6ULL_HOME/build/mfgtools/uuu/uuu" led.imx
1:18    1/ 1 [Done                                  ] SDP: boot -f led.imx
```

If the LED blinks, record that observation as an SDP execution check for your board. A valid-looking header alone would only prove the file structure.

## 11.5  Path B, SD card boot, the real thing

> **Storage safety:** Before any command that names /dev/sdX, run lsblk -o NAME,SIZE,MODEL,TRAN,TYPE,MOUNTPOINTS.
> Verify the removable card using insertion/removal, capacity and available identity fields. A USB reader's model or serial may identify the reader, not the card. Unmount its partitions and stop if the path is uncertain. Writing the wrong device can destroy the host disk.


Now the part we have not yet done in this book: boot from the SD card itself.

On the i.MX6ULL with `BOOT_CFG` set for SD card, the ROM looks for an IVT at **LBA 2**, which is byte offset `0x400`. Our `.imx` file already contains `0x400` bytes before its IVT. Therefore the file must be written starting at byte 0 of the card.

Use Chapter 8's manual identification flow, not a disk-letter filter. Run `lsblk -o NAME,PATH,SIZE,MODEL,SERIAL,TRAN,RM,TYPE,MOUNTPOINTS` before and after insertion. Match the spare card by identity and capacity. Reject host, system and data disks. Recheck every time: `/dev/sdc` below is only an example. Unmount each mounted card partition with its actual path, then inspect `lsblk` again. Stop if any identity or mountpoint is uncertain.

From the directory containing the built `led.imx`, check the input with `ls -l led.imx`, then write from byte zero to the **identified whole card**:

```sh
$ sudo dd if=led.imx of=/dev/sdc bs=1M conv=fsync status=progress
$ sync
```

Do not add `seek=1`. The image already includes the first 1 KB. Adding another 1 KB would move the IVT to byte offset `0x800`, and the ROM would not find it.

After flushing, remove/reinsert the card and identify it again. Compare exactly the image's byte count, substituting the newly confirmed device path:

```sh
$ sudo cmp -n "$(stat -c %s led.imx)" led.imx /dev/sdc
```

`stat -c %s` prints the file size; `cmp -n` compares that many bytes. Success is silent with exit status zero. A difference/read error means stop and investigate. This tiny raw image creates no filesystem or Linux partitions, so a partition listing is not its verification. Readback proves stored bytes, not ROM execution. Use a dedicated spare card; this layout is not a generic GPT-compatible image.

Before installing the card, follow Chapter 8's power-down procedure and leave the board unpowered:

1. Eject the SD card.
2. Insert into the board.
3. Set boot-mode switch to **SD**.
4. Power on.
5. Watch the LED.

If it blinks, you have booted an i.MX6ULL from an SD card you produced byte by byte. No U-Boot, no `mkimage`, and no Yocto were involved.

## 11.6  Lab

1. **Build and SDP-boot.** Confirm `mkimx.py` produces the same working blink as Chapter 9's `wrap.py`.
2. **Build and SD-boot.** Eject the card, insert into the board with the switch set to SD. Confirm the LED blinks without `uuu` involvement.
3. **Study an entry mismatch without running it.** Copy the generated image to a scratch file, change its entry word by `0x100`, and decode it with `xxd`. Compare that entry against the ELF and file layout. Do not upload the intentionally corrupt image: branching into unintended instructions is not a controlled experiment.
4. **Spot an endian mistake.** On paper, write the four IVT header bytes with a little-endian length. Which bytes differ from `D1 00 20 40`? The answer is `D1 20 00 40`. You can identify the invalid length before asking the ROM to interpret it.
5. **Dissect a vendor image.** Pick any `u-boot*.imx` you have on hand. Decode every IVT/BootData field. Identify whether a DCD is present and roughly how large it is.

## 11.7  Pitfalls

- **Endianness of IVT header length.** Big-endian. The rest of the IVT is little-endian. Easy to miss.
- **`BootData.length` shorter than the file.** Tail bytes are not loaded. We always set it to "everything from start of image to end of code, including the 4 KB header gap."
- **Changing one offset without changing the address calculation.** Keep the assertion in the script. It catches a code-location and entry mismatch before the image reaches the board.
- **Writing to the wrong block device.** Repeat Chapter 8's manual identification and mount checks at the moment of writing. There is no helper that turns an uncertain device into a safe target.
- **`sync` forgotten after `dd`.** Linux's page cache is fast. A "complete" `dd` may still have a buffer in RAM. Always `sync` (or `dd conv=fsync`) before pulling the card.
- **Booting the same SD card on a different SoC.** This image is i.MX6ULL-specific. Reusing it on another i.MX6 variant may or may not work. The IVT is the same format but load addresses change. Build per board.

## 11.8  Going deeper

- **IMX6ULLRM Chapter 8, Section 8.7**: program-image structures, including IVT and BootData. Section 8.1 describes open-versus-closed HAB behavior.
- **U-Boot source: `tools/imximage.c`**: the reference C implementation. Compare against `mkimx.py`. You'll see we covered the simple case correctly.
- **NXP `imx-mkimage` source**: `<https://github.com/nxp-imx/imx-mkimage>`. Its newer-SoC image recipes are not the i.MX6ULL image format taught here. Chapter 22 does not require a TF-A stage for this Cortex-A7 board.
- **`uuu` script reference**: `man uuu.1` or the README in `mfgtools`. Especially the SDP commands list.

The LED now gives the same execution checkpoint through two boot paths. Chapter 12 adds a more expressive one: UART text, so a program can report which step it reached rather than asking us to infer everything from a blink.
