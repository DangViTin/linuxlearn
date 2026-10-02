# Chapter 11: Hand-building a Boot ROM-acceptable image

> **What:** a real Python tool, `mkimx.py`, that turns a flat `.bin` into a Boot-ROM-loadable `.imx`. We then `dd` the result to an SD card and boot from it, with no `mkimage` and no NXP tools.
>
> **Why:** the Chapter 9 `wrap.py` worked, but it was fixed to one input file and one memory layout. Here we turn it into a reusable command-line tool.
>
> **Focus:** the **byte-for-byte layout** of the `.imx` file at offset `0x400` of the boot media, and the precise meaning of every word in IVT and BootData. Also: where to write the image on an SD card so the ROM finds it.


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

> **Two boot paths, one image, one IVT.** The `.imx` is built once. With SDP, UUU reads its structures and uploads it. With SD or eMMC, the file starts at byte 0 of the boot area and its IVT lands at LBA 2.

## 11.2  `mkimx.py`, our own image builder
Save as `~/imx6ull/scripts/mkimx.py`:

```python
#!/usr/bin/env python3
"""
mkimx.py -- build an i.MX6ULL boot image from a flat binary.

The output is a file that:
  - Has a 0x400-byte leading pad (the area the Boot ROM never reads).
  - Then an IVT at file offset 0x400 (= byte 1024).
  - Then BootData immediately after the IVT.
  - Then padding to offset 0x1000.
  - Then the user binary at file offset 0x1000.

Usage:
  mkimx.py <input.bin> <output.imx>
"""
import argparse
import struct

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
    build(args.input, args.output, args.image_start)

if __name__ == '__main__':
    main()
```

Make it executable:

```sh
$ chmod +x ~/imx6ull/scripts/mkimx.py
```
The script does the essential work of U-Boot's `mkimage -T imximage` for this simple case. We leave out DCD and signed-image support.

- **The length field in the IVT header is big-endian.** Everything else in the IVT is little-endian. The `struct.pack('>BHB', ...)` line handles this difference. This is the most common "I wrote my own mkimage and the ROM rejects it" bug.
- **`BootData.start` is `0x00907000`.** File offset `0` corresponds to that address. The IVT at file offset `0x400` therefore corresponds to `0x00907400`.
- **`BootData.length` includes all bytes through the end of the code.** It is not only the code size. If you forget the `CODE_OFFSET` part, the ROM stops loading before your `.text` begins.
- **`csf_addr = 0`** disables **HAB** (High Assurance Boot, NXP's signed-boot framework. Ch 124) signature checking. Setting it to a non-zero address would point the ROM at a CSF (Command Sequence File) it must verify.

## 11.3  Building and inspecting

Rebuild Chapter 10's LED:

```sh
$ cd ~/imx6ull/src/ch10-c-startup
$ make
$ ~/imx6ull/scripts/mkimx.py led.bin led.imx
  image  = 0x00907000
  entry  = 0x00908000
  IVT    @ 0x00907400  (file offset 0x0400)
  bdata  @ 0x00907420
  code   @ 0x00908000  (file offset 0x1000)
  total  = 4384 bytes
  wrote  led.imx
```

The total size depends on your `led.bin`. The address lines must match this example. The script computes the entry address from `image_start + CODE_OFFSET`, so an entry and code-location mismatch cannot be requested accidentally.

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

LED blinks. We verified our new tool produces a working SDP image.

## 11.5  Path B, SD card boot, the real thing

> **Storage safety:** Before any command that names /dev/sdX, run lsblk -o NAME,SIZE,MODEL,TRAN,TYPE,MOUNTPOINTS.
> Verify the removable card by size and model, unmount its partitions, and stop if the path is not the target card. Writing the wrong /dev node can destroy the host disk.


Now the part we have not yet done in this book: boot from the SD card itself.

On the i.MX6ULL with `BOOT_CFG` set for SD card, the ROM looks for an IVT at **LBA 2**, which is byte offset `0x400`. Our `.imx` file already contains `0x400` bytes before its IVT. Therefore the file must be written starting at byte 0 of the card.

Use Chapter 3's manual identification flow, not a disk-letter filter. Run `lsblk -o NAME,PATH,SIZE,MODEL,SERIAL,TRAN,RM,TYPE,MOUNTPOINTS` before and after insertion. Match the spare card by identity and capacity; reject host/system/data disks. Recheck every time: `/dev/sdc` below is only an example. Unmount each mounted card partition with its actual path, then inspect `lsblk` again. Stop if any identity or mountpoint is uncertain.

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

Now:

1. Eject the SD card.
2. Insert into the board.
3. Set boot-mode switch to **SD**.
4. Power on.
5. Watch the LED.

If it blinks, you have booted an i.MX6ULL from an SD card you produced byte by byte. No U-Boot, no `mkimage`, and no Yocto were involved.

## 11.6  Lab

1. **Build and SDP-boot.** Confirm `mkimx.py` produces the same working blink as Chapter 9's `wrap.py`.
2. **Build and SD-boot.** Eject the card, insert into the board with the switch set to SD. Confirm the LED blinks without `uuu` involvement.
3. **Study an entry mismatch.** Temporarily add `0x100` to `entry_addr` inside `mkimx.py`. Build and SDP-push. The board does nothing even though `uuu` reports success. Restore the calculation afterward.
4. **Find another mistake.** Make `mkimx.py` emit `IVT_LENGTH` little-endian instead of big-endian. Build, SDP-push. The ROM rejects it silently. Restore.
5. **Dissect a vendor image.** Pick any `u-boot*.imx` you have on hand. Decode every IVT/BootData field. Identify whether a DCD is present and roughly how large it is.

## 11.7  Pitfalls

- **Endianness of IVT header length.** Big-endian. The rest of the IVT is little-endian. Easy to miss.
- **`BootData.length` shorter than the file.** Tail bytes are not loaded. We always set it to "everything from start of image to end of code, including the 4 KB header gap."
- **Changing one offset without changing the address calculation.** Keep the assertion in the script. It catches a code-location and entry mismatch before the image reaches the board.
- **Writing to the wrong block device.** Discussed in Chapter 3. Use the helper.
- **`sync` forgotten after `dd`.** Linux's page cache is fast. A "complete" `dd` may still have a buffer in RAM. Always `sync` (or `dd conv=fsync`) before pulling the card.
- **Booting the same SD card on a different SoC.** This image is i.MX6ULL-specific. Reusing it on another i.MX6 variant may or may not work. The IVT is the same format but load addresses change. Build per board.

## 11.8  Going deeper

- **IMX6ULLRM Chapter 8 §8.7**: the formal IVT spec.
- **U-Boot source: `tools/imximage.c`**: the reference C implementation. Compare against `mkimx.py`. You'll see we covered the simple case correctly.
- **`imx-mkimage` source**: `<https://github.com/nxp-imx/imx-mkimage>`. For multi-bootloader images (TF-A + ATF + U-Boot), which we won't need until Chapter 22.
- **`uuu` script reference**: `man uuu.1` or the README in `mfgtools`. Especially the SDP commands list.

> Next chapter: **Chapter 12: UART driver and `printf`.** We replace blinking with words. Once we can `printf`, the rest of bare-metal becomes survivable.
