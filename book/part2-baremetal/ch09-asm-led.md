---
chapter: 9
title: First LED, pure assembly
part: II — Bare-metal i.MX6ULL
estimated_pages: 16
status: draft
---

# Chapter 9 — First LED, pure assembly

> **What:** code that blinks an LED on the Point Atom MINI. No C. No libc. No bootloader. ~25 lines of ARM assembly, < 1 KB image, loaded into OCRAM by the Boot ROM over USB-OTG.
>
> **Why:** This is the moment you really own the chip. Higher layers exist to make hard things easy, but you can only judge them if you have done it the hard way once.
>
> **Focus:** the **three-write pattern** that brings up any GPIO on any i.MX SoC — `CCGR` (clock), `IOMUXC` (pin), `GPIO_GDIR + GPIO_DR` (use). Memorize it. We use it for every peripheral in the book.

## 9.1  What we are about to build

A program with the following structure:

```
_start:                          ; ROM jumps here
    set SP to top of OCRAM
    enable clock to GPIO1        ; one write to CCM_CCGR1
    set pin GPIO1_IO03 to ALT5   ; one write to IOMUXC
    configure pad properties     ; one write to IOMUXC
    set GPIO1_IO03 as output     ; one write to GPIO1_GDIR
loop:
    toggle GPIO1_IO03            ; toggle bit 3 of GPIO1_DR
    delay  (busy loop)
    branch loop
```

That is, literally, the program. About 50 instructions, 200 bytes of `.text`, zero data. We push it to OCRAM via `uuu` in SDP mode. The Boot ROM transfers control and the LED blinks.

No linker script this chapter. The program is small enough to hand-place. Chapter 10 introduces the linker script as soon as we want C.

> **Which pin?** On both Point Atom ALPHA and MINI, the user LED (D1 on the silkscreen) is on **GPIO1_IO03**. The wiring is active-low: the anode goes to 3.3 V through a current-limiting resistor; the GPIO pulls the cathode low to turn the LED on. *Confirm against your board's schematic for safety.* If your LED is on a different pin, every register address in this chapter changes, but the pattern does not. Because we only toggle the bit, active-low wiring does not change our code. The LED just blinks with inverted phase.

## 9.2  The three-write pattern, explained

To make any pin output a level under software control on i.MX6ULL, you do exactly three things:

1. **Enable the clock to the GPIO controller**, by setting two bits in `CCM_CCGRx`. Without this, all writes to the GPIO registers go into the void.
2. **Route the pin to its GPIO function**, by writing the ALT number to `IOMUXC_SW_MUX_CTL_PAD_<padname>`. Without this, the pin still belongs to whatever default function the silicon picked at reset (often a different peripheral).
3. **Make it an output**, by setting the corresponding bit in `GPIO<bank>_GDIR`. **Then** write 0/1 to the same bit position in `GPIO<bank>_DR` to drive the level.

Optionally, you also write to `IOMUXC_SW_PAD_CTL_PAD_<padname>` to set drive strength, slew rate, pull, etc. For an LED you can usually leave this at reset defaults.

Addresses for GPIO1_IO03, from the Reference Manual:

| Register | Address | Purpose |
|----------|---------|---------|
| `CCM_CCGR1` | `0x020C406C` | Bits 26:27 (CG13) = GPIO1 clock gate |
| `IOMUXC_SW_MUX_CTL_PAD_GPIO1_IO03` | `0x020E0068` | MUX select for pin GPIO1_IO03 |
| `IOMUXC_SW_PAD_CTL_PAD_GPIO1_IO03` | `0x020E02F4` | Pad properties for pin GPIO1_IO03 |
| `GPIO1_DR` | `0x0209C000` | GPIO1 data register (bit 3 = our pin, i.e. `1 << 3` for GPIO1_IO03) |
| `GPIO1_GDIR` | `0x0209C004` | GPIO1 direction register (bit 3 = direction for GPIO1_IO03; 1 = output) |

The value to write into `MUX_CTL` for GPIO function is **5**. The IOMUX table in RM Chapter 32 says, for the pad `GPIO1_IO03`, ALT5 is `GPIO1_IO03`. (The naming is circular: the *pad* is named for the GPIO function it has at ALT5.)

### CCM_CCGR encoding (2 bits per gate)

Every CCM_CCGRx register holds **16 clock gates × 2 bits each** = 32 bits. The 2-bit field per gate is:

| Bits | Meaning |
|------|---------|
| `00` | **Clock off** in all CPU run modes — peripheral cannot be accessed |
| `01` | Clock on in RUN mode, **off** in WAIT and STOP — low-power-friendly |
| `10` | *Reserved* — do not program this value |
| `11` | Clock on in all CPU run modes (RUN/WAIT/STOP) — "always on" |

So "enable GPIO1 always" is `0b11` written into CG13's bit-pair. CG13 occupies bits 26–27 of CCGR1 (CG0 is bits 0–1, CG1 bits 2–3, …, CG15 bits 30–31). The OR-mask is `0b11 << 26 = 0x0C000000`. We can either OR-in that mask or just write `0xFFFFFFFF` to CCGR1 (turning every gate in CCGR1 on); for a learning exercise the OR form is cleaner because it leaves the other gates unchanged. **This 2-bit encoding applies to every CCGR write throughout the book** — Chapters 13, 14, 18 reuse it.

## 9.3  The assembly source

`led.S`:

```asm
    .syntax unified
    .cpu    cortex-a7
    .text
    .global _start

_start:
    /* --------------------------------------------------------------
     *  1. Establish a stack.  The Boot ROM has used part of OCRAM
     *     for its own bookkeeping, but the top of OCRAM is free.
     *     OCRAM ends at 0x00920000 (128 KB starting at 0x00900000).
     *     We set SP just below that.  An LED blink doesn't actually
     *     touch the stack, but it's hygienic.
     * -------------------------------------------------------------- */
    ldr     sp, =0x00920000

    /* --------------------------------------------------------------
     *  2. Enable the GPIO1 clock gate.
     *     CCM_CCGR1 @ 0x020C406C, CG13 = bits 26:27 = 0b11 (always on)
     * -------------------------------------------------------------- */
    ldr     r0, =0x020C406C         @ &CCM_CCGR1
    ldr     r1, [r0]
    orr     r1, r1, #(3 << 26)      @ set CG13 = 0b11
    str     r1, [r0]

    /* --------------------------------------------------------------
     *  3. IOMUX: select ALT5 (GPIO function) for pad GPIO1_IO03.
     * -------------------------------------------------------------- */
    ldr     r0, =0x020E0068         @ &IOMUXC_SW_MUX_CTL_PAD_GPIO1_IO03
    mov     r1, #5
    str     r1, [r0]

    /* --------------------------------------------------------------
     *  4. (Optional) configure pad: 50 MHz slew, push-pull, no pull.
     *     0x10B0 = typical "low-speed digital output" stanza.
     * -------------------------------------------------------------- */
    ldr     r0, =0x020E02F4         @ &IOMUXC_SW_PAD_CTL_PAD_GPIO1_IO03
    ldr     r1, =0x000010B0
    str     r1, [r0]

    /* --------------------------------------------------------------
     *  5. Set GPIO1_IO03 as output.
     * -------------------------------------------------------------- */
    ldr     r0, =0x0209C004         @ &GPIO1_GDIR
    ldr     r1, [r0]
    orr     r1, r1, #(1 << 3)
    str     r1, [r0]

    /* --------------------------------------------------------------
     *  6. Blink loop.  Toggle bit 3 in GPIO1_DR, delay, repeat.
     *     A delay loop of ~1.5M iterations at 396 MHz is about 8 ms.
     *     Doesn't have to be precise; we just want a visible blink.
     * -------------------------------------------------------------- */
    ldr     r4, =0x0209C000         @ &GPIO1_DR
    ldr     r5, [r4]                @ current value
    mov     r6, #(1 << 3)           @ bit mask for pin 3

blink:
    eor     r5, r5, r6              @ toggle bit 3 in cached value
    str     r5, [r4]                @ write back

    ldr     r7, =1500000            @ delay counter
1:  subs    r7, r7, #1
    bne     1b

    b       blink

    .end
```

A few notes on what's there and what isn't:

- **No exception vectors.** The Boot ROM doesn't require them. We are running with interrupts disabled (CPSR.I=1 from reset) and we don't enable them, so no exception ever fires. Chapter 15 will install a real vector table.
- **No `.data`, no `.bss`.** Every value we use is an immediate or computed at run time. Therefore no startup code is needed to copy or zero anything.
- **No `main()`.** `_start` is the entry; it never returns. An assembly program has no caller to return to; you must explicitly loop forever.
- **`ldr r0, =0x...`** is GNU assembler syntax for "load-pc-relative pool constant". The assembler generates a literal pool somewhere after the function and the `ldr` becomes a load from that pool. Cortex-A7 cannot encode arbitrary 32-bit immediates in one instruction. This pseudo-form is the standard idiom.
- **`1:` is a local label.** `1b` means "branch to the nearest `1` label going backward." This is a GAS convention for local loops; it avoids us inventing new names.
- **`.syntax unified`** says "use the modern ARM/Thumb-unified mnemonics", which lets us write `orr r1, r1, ...` even in ARM mode without surprises.

## 9.4  Building the image

Two files: `led.S` (above) and a one-line `Makefile`.

```make
# Makefile
CROSS := arm-none-eabi-

all: led.bin

led.elf: led.S
	$(CROSS)gcc -mcpu=cortex-a7 -nostdlib -Wl,-Ttext=0x00907400 -o $@ $<

led.bin: led.elf
	$(CROSS)objcopy -O binary $< $@

clean:
	rm -f led.elf led.bin

.PHONY: all clean
```

What is going on:

- **`-Wl,-Ttext=0x00907400`** tells the linker "place `.text` at virtual address `0x00907400`". This is the address where the image will live after loading into OCRAM (well above the ROM's bookkeeping at the bottom of OCRAM). The assembled `ldr r0, =0x...` constants are relocated relative to this base when the pool is materialized.
- **`-nostdlib`** keeps `crt0` and libc out. We have no startup code to call ours.
- We do *not* pass `-Wl,-e _start` because GCC's default entry is `_start` already.

Build:

```sh
$ make
arm-none-eabi-gcc -mcpu=cortex-a7 -nostdlib -Wl,-Ttext=0x00907400 -o led.elf led.S
arm-none-eabi-objcopy -O binary led.elf led.bin
$ wc -c led.bin
160 led.bin
```

About 160 bytes. Now we know how small bare-metal can be.

Inspect to make sure we got what we expect:

```sh
$ arm-none-eabi-objdump -d led.elf | head -30

led.elf:     file format elf32-littlearm

Disassembly of section .text:

00907400 <_start>:
  907400:   e59fd054    ldr sp, [pc, #84]   ; 0x90745c
  907404:   e59f0054    ldr r0, [pc, #84]   ; 0x907460
  907408:   e5901000    ldr r1, [r0]
  90740c:   e3811cc0    orr r1, r1, #49152, 6  ; 0xc000000
  ...
```

`pc, #84` is the offset to the literal pool, where the constants `0x00920000`, `0x020C406C`, etc., live. That is the assembler's translation of our `ldr r0, =0x...`.

## 9.5  Wrapping the .bin in an .imx

`led.bin` is raw machine code. The Boot ROM in SDP mode does *not* execute raw bins — it executes images that present an IVT (Chapter 7). We need to wrap.

For this chapter we use the simplest possible wrapper: a 3-line shell command that builds an IVT and BootData in front of our code. We will write a Python tool that does this cleanly in **Chapter 11**; for now, accept the magic and let it work.

Save as `wrap.sh`:

```sh
#!/bin/bash
# Build led.imx = [pad-to-0x400][IVT 32B][BootData 12B][pad to 0x1000][led.bin]
# IVT.self  = 0x00907400  (where the IVT lives after load)
# IVT.entry = 0x00908000  (where led.bin starts)
# BootData.start  = 0x00907400  (load the whole image here)
# BootData.length = file size
set -euo pipefail
LOAD_ADDR=0x00907400
ENTRY=0x00908000
BIN_OFFSET=0x1000   # entry is at file_offset 0x1000 from start of image
                    # IVT is at file_offset 0x000 of image (=0x400 in .imx file)

# Build header in Python (saves us from messy printf-hex)
python3 - <<EOF > header.bin
import struct
hdr = struct.pack('<BBBB', 0xD1, 0x00, 0x20, 0x40)           # IVT tag/len/ver
hdr += struct.pack('<IIIIIII',
    0x00908000,    # entry
    0x00000000,    # reserved
    0x00000000,    # dcd (none)
    0x00907420,    # boot_data (right after IVT)
    0x00907400,    # self
    0x00000000,    # csf (no HAB)
    0x00000000)    # reserved
# BootData immediately follows IVT (offset +0x20)
import os
codesize = os.path.getsize('led.bin')
total = codesize + 0x1000   # code + 4 KB headroom for IVT+pad
hdr += struct.pack('<III', 0x00907400, total, 0x00000000)    # start, length, plugin
# pad header region to 0x1000 (so led.bin starts at offset 0x1000)
hdr += b'\xff' * (0x1000 - len(hdr))
import sys
sys.stdout.buffer.write(hdr)
EOF

# Assemble: 0x400 of leading pad, then header.bin (0x1000), then led.bin
( head -c 0x400 /dev/zero
  cat header.bin
  cat led.bin
) > led.imx

rm -f header.bin
ls -l led.imx
```

```sh
$ chmod +x wrap.sh && ./wrap.sh
-rw-r--r-- 1 you you 5536 May 25 14:02 led.imx
```

If you decode the IVT now you should see exactly the values we set:

```sh
$ xxd -s 0x400 -l 32 led.imx
00000400: d100 2040 0080 9000 0000 0000 0000 0000  .. @............
00000410: 2074 9000 0074 9000 0000 0000 0000 0000   t...t..........
```

Tag `D1 00 20 40`, entry `00 80 90 00` (little-endian → `0x00908000`), dcd zero, boot_data `20 74 90 00` (→ `0x00907420`), self `00 74 90 00` (→ `0x00907400`). Matches.

## 9.6  Pushing to the board with `uuu`

1. Power off the board, flip the boot-mode switch to **SDP** (USB-Downloader).
2. Connect the USB-OTG cable to the host.
3. Power on.
4. Confirm enumeration:

```sh
$ lsusb | grep 15a2
Bus 001 Device 010: ID 15a2:0080 Freescale SemiConductor Inc i.MX 6 SystemOnChip in RecoveryMode
```

5. Push the image:

```sh
$ uuu -b sdp led.imx
uuu (Universal Update Utility) for nxp imx chips -- 1.5.x-0
1:18    1/ 1 [Done                                  ] SDP: boot -f led.imx
Success 1    Failure 0
```

That `uuu -b sdp` invocation runs a built-in script that does, in essence:

```
SDP: boot -f <image>
```

which translates into:

- `WRITE_FILE` — push `led.imx` (starting at offset `0x400`, the IVT) to the IVT.self address in RAM.
- `JUMP_ADDRESS` — jump to IVT.self. The ROM there interprets the IVT, transfers control to IVT.entry.

Watch the LED. It should blink.

If it does not:

1. **Check the LED's polarity.** If your board's LED is active-low, our toggle still blinks it but the on/off pattern is inverted from what you might expect.
2. **Check the IOMUX value.** Did your board's schematic say GPIO1_IO03 or a different pin? If different, every register address in §9.2 changes.
3. **Confirm `uuu` reported success.** If `uuu` reported failure, the image was rejected by the ROM — most often because IVT.self does not match the load address. Re-decode the IVT and confirm.
4. **Power-cycle and retry.** The ROM, once it jumps to user code, will not accept another SDP push without a reset.

## 9.7  What just happened, sequence-level

If you got the blink, this sequence ran on real silicon:

```
Power on
  → Boot ROM runs from internal ROM at 0x00000000
    → reads BOOT_MODE pins, sees SDP
    → enumerates as USB device 15a2:0080
    → waits for host commands
host: uuu pushes led.imx over USB
  → ROM receives WRITE_FILE: payload at RAM offset 0x00907400+
  → ROM receives JUMP_ADDRESS: 0x00907400
ROM:
  → finds IVT magic 0xD1 at 0x00907400 ✓
  → reads IVT.dcd (zero, skip DCD)
  → reads IVT.entry = 0x00908000, jumps there
Your code:
  → _start sets SP
  → enables GPIO1 clock gate
  → sets pin ALT5
  → sets pin direction = output
  → enters blink loop
LED blinks. You wrote every instruction the CPU executed to get here.
```

Nothing sits between your code and the chip. The next 50 chapters add layers on top of what you just built.

## 9.8  Lab

You have already done the lab if the LED blinked. To deepen:

1. **Change the blink rate** by editing the delay constant. Measure the resulting frequency with a scope or with a phone's slow-motion camera. The CPU's reset clock is 396 MHz, so an inner-loop body of 4 instructions and a counter of 1.5M is ~15 ms per half-period. Verify experimentally.
2. **Use a different pin.** Look up the schematic. Find a second LED, or an unused GPIO that goes to a header pin you can probe. Modify the source to use that pin instead. *Do not* read register addresses from the previous example; look them up in the RM yourself.
3. **Add a second LED** that blinks at half the rate. Now you have a counter.
4. **Measure image size growth.** Run `wc -c led.bin` before and after; observe the marginal cost.

## 9.9  Pitfalls

- **Forgetting the CCGR write.** Symptoms: register reads return 0, writes have no effect. *Always* enable the clock before touching a peripheral. Always.
- **Wrong IOMUX ALT.** Symptom: writes to GPIO_DR succeed but the pin doesn't move. Some pads default to "GPIO" in their reset ALT; many do not. Always set ALT explicitly.
- **`IVT.self` ≠ load address.** Symptoms: `uuu` reports success, board does nothing, no blink. The ROM jumped — but to the wrong place. Decode the IVT again; ensure `self` and the load argument match.
- **Leaving the boot-mode switch in SDP.** After your image runs, if you reset the board, it goes back into SDP and does nothing visible. Move the switch back to SD when you are done with SDP work for the day.
- **Push-pull vs open-drain.** If your LED is wired to VCC through a resistor (common for active-low LEDs), driving the GPIO high turns it off, not on. Read the schematic.
- **Optimization eating your loop.** GCC with `-O2` may unroll or completely eliminate a delay loop with no side-effects. We avoided this here by leaving the loop in raw asm; if you port to C, mark the counter `volatile`.

## 9.10  Going deeper

- **IMX6ULLRM Chapter 28 — GPIO**. Specifically Table 28-1 (register summary) and Table 28-3 (GPIOx_DR bit layout).
- **IMX6ULLRM Chapter 32 — IOMUXC**. Look up GPIO1_IO03 in the IOMUX table.
- **IMX6ULLRM Chapter 18 — CCM**. Table 18-5 (CCGR bit definitions).
- **ARM DDI 0406** Section A8.8.62 — `LDR (literal)` form, which is what `ldr Rn, =const` expands into.
- The GNU Assembler manual, "ARM Dependent Features" — `.syntax unified`, `.cpu`, `.global`, literal pools.
- Your **Point Atom MINI schematic** — the only authoritative source for which LED is on which pin on *your* board.

> Next chapter: **Chapter 10 — C + startup.S + linker script.** We graduate from one-shot assembly to a real bare-metal C environment with proper `.data` initialization and `.bss` zeroing. Same LED, ten times more useful.
