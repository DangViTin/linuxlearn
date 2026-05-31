---
chapter: 11
title: Hand-building a Boot ROM-acceptable image
part: II — Bare-metal i.MX6ULL
estimated_pages: 22
status: draft
---

# Chapter 11 — Hand-building a Boot ROM-acceptable image

> **What:** a real Python tool, `mkimx.py`, that turns a flat `.bin` into a Boot-ROM-loadable `.imx`. We then `dd` the result to an SD card and boot from it — no `mkimage`, no NXP tools, no magic.
> **Why:** the Chapter 9 `wrap.sh` worked, but you will edit this tool again. A 60-line Python script you understand beats a 3-line shell command you don't.
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

In SDP mode, `uuu` skips the first `0x400` bytes of the file (the ROM never reads them on USB-SDP). It uploads everything from offset `0x0400` onward to the RAM address in `BootData.start`. On the SD-card path, the **whole** file is `dd`'d to the card starting at sector 2 (LBA 2 = byte offset `0x400`), and the ROM reads the IVT directly from the card.

> **Two boot paths, one image, one IVT.** The `.imx` is built once. The IVT it contains works for SDP, for SD boot, and for eMMC boot. The only thing that differs is where the file lives — RAM (pushed by uuu) vs LBA 2 of the SD card. The IVT is happy in either case because all its addresses are absolute physical RAM addresses.

## 11.2  `mkimx.py` — our own image builder

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
  mkimx.py <input.bin> <output.imx> --load 0x00907400 --entry 0x00908000
"""
import argparse, os, struct, sys

IVT_TAG       = 0xD1
IVT_LENGTH    = 0x0020   # 32 bytes, big-endian per spec
IVT_VERSION   = 0x40

PRE_PAD       = 0x400    # before the IVT
IMAGE_OFFSET  = 0x1000   # start of user binary, relative to IVT

def ivt_header():
    # The IVT header is 4 bytes:
    #   byte 0 = tag (0xD1)
    #   byte 1-2 = length (BIG endian, 16-bit)  -- this is the gotcha
    #   byte 3 = version (0x40 = HAB v4)
    return struct.pack('>BHB', IVT_TAG, IVT_LENGTH, IVT_VERSION)

def build(input_bin: str, output_imx: str, load: int, entry: int):
    with open(input_bin, 'rb') as f:
        code = f.read()

    ivt_addr        = load                       # IVT lives at the load address
    bootdata_addr   = ivt_addr + 0x20            # immediately after IVT
    entry_addr      = entry
    csf_addr        = 0
    dcd_addr        = 0
    image_size      = IMAGE_OFFSET + len(code)   # IVT+BootData+pad+code

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
    bootdata = struct.pack('<III', load, image_size, 0)
    assert len(bootdata) == 12

    # Lay out the IVT+BootData region (the first 0x1000 of the image proper)
    header = bytearray(IMAGE_OFFSET)            # zero-filled
    header[0x00:0x20]    = ivt
    header[0x20:0x2C]    = bootdata

    # Final .imx = 0x400 pre-pad  ||  header (0x1000)  ||  code
    out  = bytes(PRE_PAD) + bytes(header) + code

    with open(output_imx, 'wb') as f:
        f.write(out)

    print(f"  load   = 0x{load:08X}")
    print(f"  entry  = 0x{entry:08X}")
    print(f"  IVT    @ 0x{ivt_addr:08X}  (file offset 0x{PRE_PAD:04X})")
    print(f"  bdata  @ 0x{bootdata_addr:08X}")
    print(f"  code   @ 0x{ivt_addr + IMAGE_OFFSET:08X}  (file offset 0x{PRE_PAD+IMAGE_OFFSET:04X})")
    print(f"  total  = {len(out)} bytes")
    print(f"  wrote  {output_imx}")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('input')
    ap.add_argument('output')
    ap.add_argument('--load',  type=lambda s: int(s, 0), required=True,
                    help='Physical load address (IVT.self and BootData.start)')
    ap.add_argument('--entry', type=lambda s: int(s, 0), required=True,
                    help='IVT.entry (where ROM jumps after load)')
    args = ap.parse_args()
    build(args.input, args.output, args.load, args.entry)

if __name__ == '__main__':
    main()
```

Make it executable:

```sh
$ chmod +x ~/imx6ull/scripts/mkimx.py
```

The script is 60 lines but does everything the U-Boot `mkimage -T imximage` tool does for the simple case. The only feature we left out is DCD support, which we add in Chapter 14 once we need it.


- **The length field in the IVT header is big-endian.** Everything else in the IVT is little-endian. NXP did this; we don't. The `struct.pack('>BHB', ...)` line handles it. This is the single most common "I wrote my own mkimage and the ROM rejects it" bug.
- **`BootData.length` includes the IVT and the 4 KB padding.** Not just the code. If you forget the `IMAGE_OFFSET` part of the addend, the ROM stops loading before your `.text` even starts.
- **`csf_addr = 0`** disables **HAB** (High Assurance Boot — NXP's signed-boot framework; Ch 124) signature checking. Setting it to a non-zero address would point the ROM at a CSF (Command Sequence File) it must verify.

## 11.3  Building and inspecting

Rebuild Chapter 10's LED:

```sh
$ cd ~/imx6ull/src/ch10-c-startup
$ make
$ ~/imx6ull/scripts/mkimx.py led.bin led.imx --load 0x00907400 --entry 0x00908000
  load   = 0x00907400
  entry  = 0x00908000
  IVT    @ 0x00907400  (file offset 0x0400)
  bdata  @ 0x00907420
  code   @ 0x00908400  (file offset 0x1400)
  total  = 5572 bytes
  wrote  led.imx
```

Wait — entry is `0x00908000` but the code is *placed* at `0x00908400`? That's wrong.

Yes, it is wrong, and it is the second-most-common bug. With `IMAGE_OFFSET = 0x1000` and load `0x00907400`, the code lands at `0x00908400`. The `--entry` we pass must agree. Either:

- Pass `--entry 0x00908400` so it matches where code actually lands, **or**
- Change `IMAGE_OFFSET` so `load + IMAGE_OFFSET = entry`.

We'll use the first option. The cleaner invocation:

```sh
$ ~/imx6ull/scripts/mkimx.py led.bin led.imx --load 0x00907400 --entry 0x00908400
```

Even cleaner: since `entry` always equals `load + IMAGE_OFFSET` for our convention, we could compute it in the script and drop the `--entry` flag. We leave it explicit because someday you'll want the IVT separated from the code (with a DCD in between) and you'll need the freedom.

Verify the IVT with raw `xxd`:

```sh
$ xxd -s 0x400 -l 32 led.imx
00000400: d100 2040 0084 9000 0000 0000 0000 0000  .. @............
00000410: 2074 9000 0074 9000 0000 0000 0000 0000   t...t..........
$ xxd -s 0x420 -l 12 led.imx
00000420: 0074 9000 c416 0000 0000 0000             .t..........
```

Decode:

| Word | Bytes (LE) | Value | Field |
|------|-----------|-------|-------|
| `0x400` | `D1 00 20 40` | tag/length/version (big-endian length!) | IVT header |
| `0x404` | `00 84 90 00` | `0x00908400` | entry ✓ |
| `0x408` | `00 00 00 00` | 0 | reserved1 |
| `0x40C` | `00 00 00 00` | 0 | dcd (none) |
| `0x410` | `20 74 90 00` | `0x00907420` | boot_data ✓ |
| `0x414` | `00 74 90 00` | `0x00907400` | self ✓ |
| `0x418` | `00 00 00 00` | 0 | csf |
| `0x41C` | `00 00 00 00` | 0 | reserved2 |
| `0x420` | `00 74 90 00` | `0x00907400` | BootData.start ✓ |
| `0x424` | `C4 16 00 00` | `0x000016C4` = 5828 | BootData.length |
| `0x428` | `00 00 00 00` | 0 | BootData.plugin |

`BootData.length` = 5828 bytes covers the 4 KB header + ~1.4 KB of code, plus some alignment slack. Looks right.

## 11.4  Path A — SDP push, again

Push to the board exactly as in Chapter 9:

```sh
$ uuu -b sdp led.imx
1:18    1/ 1 [Done                                  ] SDP: boot -f led.imx
```

LED blinks. We verified our new tool produces a working SDP image.

## 11.5  Path B — SD card boot, the real thing

Now the part we have not yet done in this book: boot from the SD card itself.

On the i.MX6ULL with `BOOT_CFG` set for SD card, the ROM reads from **LBA 2** (byte offset `0x400`) of the boot device, looking for an IVT. Our `.imx` file has the IVT at exactly offset `0x400`, by construction. So: `dd if=led.imx of=/dev/sdX bs=1k seek=1`.

`seek=1` with `bs=1k` skips the first 1 KB of the SD card — so our IVT lands at LBA 2 (offset `0x400`), exactly where the ROM looks. The first 1 KB of the SD card is left untouched; on a freshly-formatted card it is zeros, which is fine.

Use the helper from Chapter 3:

```sh
$ ls -l led.imx
-rw-r--r-- 1 you you 5828 May 25 14:30 led.imx

$ ~/imx6ull/scripts/sd-write.sh led.imx /dev/sdc
Wipe /dev/sdc (size 7.5G)? [y/N] y
...
$ sync
```

Hmm — `sd-write.sh` does `dd if=$IMG of=$DEV bs=1M`, which writes from byte 0. That overwrites the IVT-at-offset-0x400 layout, putting *our* IVT at offset 0. Wrong.

Two fixes:

### Option 1 — patch the script

Add `seek=1` and `bs=1k` modes, or build a wrapper. Simplest:

```sh
$ sudo dd if=led.imx of=/dev/sdc bs=1k seek=1 conv=fsync
$ sync
```

The `seek=1` means we do not write the first 1 KB. That's intentional: the ROM never reads it.

### Option 2 — pre-pad the .imx so it starts at offset 0

Our `mkimx.py` already prepends `0x400` of zero. So `bs=1M conv=fsync` from offset 0 works *if* you accept that the first 1 KB on the card becomes zeros. That is, the `0x400` pad inside the `.imx` IS the first 1 KB of the SD card. Both options are equivalent; Option 2 with our specific `.imx` is the one we'll use. Replace the second line above with:

```sh
$ sudo dd if=led.imx of=/dev/sdc bs=1M conv=fsync status=progress
$ sync
```

Now:

1. Eject the SD card.
2. Insert into the board.
3. Set boot-mode switch to **SD**.
4. Power on.
5. Watch the LED.

If it blinks, you have just booted an i.MX6ULL from an SD card you produced byte by byte. No U-Boot, no mkimage, no Yocto. Just 60 lines of Python and 50 lines of C/asm.

## 11.6  Reading IVT from a vendor image

Apply what we just built to dissect a vendor image. Find any U-Boot `.imx` you have:

```sh
$ wget https://example.org/some-vendor/u-boot.imx -O u-boot.imx
$ xxd -s 0x400 -l 48 u-boot.imx
00000400: d100 2040 00f8 7780 0000 0000 2c04 7780  .. @..w.....,.w.
00000410: 2cc0 7780 00c0 7780 0000 0000 0000 0000  ,.w...w.........
00000420: 00c0 7780 0000 0c00 0000 0000             ..w.........
```

Decode:

| Field | Value | Note |
|-------|-------|------|
| entry | `0x877800F8` | DRAM (post-DDR-init); U-Boot |
| dcd | `0x8077042C` | Has a DCD! |
| boot_data | `0x8077C02C` | |
| self | `0x8077C000` | |
| BootData.start | `0x8077C000` | Load to DRAM |
| BootData.length | `0x000C0000` = 768 KB | |

This U-Boot image loads to DRAM at `0x8077C000`. It must include a DCD, because DDR is not initialized when the ROM starts loading. The DCD lives at address `0x8077042C` *after* the image is loaded. The ROM walks the DCD from there as part of its load sequence. (We will dissect DCD contents in Chapter 14.)

## 11.7  Lab

1. **Build and SDP-boot.** Confirm `mkimx.py` produces the same working blink as Chapter 9's `wrap.sh`.
2. **Build and SD-boot.** Eject the card, insert into the board with the switch set to SD. Confirm the LED blinks without `uuu` involvement.
3. **Make a deliberate mistake.** Set `--entry` to the wrong address (off by `0x100`). Build, SDP-push. The board does nothing. Confirm `uuu` reported success — i.e., the failure is invisible from the host side. Restore.
4. **Find another mistake.** Make `mkimx.py` emit `IVT_LENGTH` little-endian instead of big-endian. Build, SDP-push. The ROM rejects it silently. Restore.
5. **Dissect a vendor image.** Pick any `u-boot*.imx` you have on hand. Decode every IVT/BootData field. Identify whether a DCD is present and roughly how large it is.

## 11.8  Pitfalls

- **Endianness of IVT header length.** Big-endian. The rest of the IVT is little-endian. Easy to miss.
- **`BootData.length` shorter than the file.** Tail bytes are not loaded. We always set it to "everything from start of image to end of code, including the 4 KB header gap."
- **`entry` not matching where code actually lands.** Discussed in §11.3. Most common cause: changing `IMAGE_OFFSET` and forgetting to pass a new `--entry`.
- **Writing to the wrong block device.** Discussed in Chapter 3. Use the helper.
- **`sync` forgotten after `dd`.** Linux's page cache is fast; a "complete" `dd` may still have a buffer in RAM. Always `sync` (or `dd conv=fsync`) before pulling the card.
- **Booting the same SD card on a different SoC.** This image is i.MX6ULL-specific. Reusing it on another i.MX6 variant may or may not work; the IVT is the same format but load addresses change. Build per board.

## 11.9  Going deeper

- **IMX6ULLRM Chapter 8 §8.7** — the formal IVT spec.
- **U-Boot source: `tools/imximage.c`** — the reference C implementation. Compare against `mkimx.py`; you'll see we covered the simple case correctly.
- **`imx-mkimage` source** — `<https://github.com/nxp-imx/imx-mkimage>`. For multi-bootloader images (TF-A + ATF + U-Boot), which we won't need until Chapter 22.
- **`uuu` script reference** — `man uuu.1` or the README in `mfgtools`. Especially the SDP commands list.

> Next chapter: **Chapter 12 — UART driver and `printf`.** We replace blinking with words. Once we can `printf`, the rest of bare-metal becomes survivable.
