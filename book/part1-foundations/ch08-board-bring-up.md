---
chapter: 8
title: Hardware bring-up checklist
part: I — Foundations
estimated_pages: 12
status: draft
---

# Chapter 8 — Hardware bring-up checklist

> **What:** the physical, hands-on first contact with the Point Atom MINI. By the end you have a board you trust, a serial connection that works, an SD-card workflow, and a tested recovery path.
> **Why:** every later chapter assumes the hardware works. The cheapest place to discover a flaky cable or a wrong jumper is *now*, not at 1 a.m. in Chapter 14 when you cannot tell whether your DDR init or your wiring is the problem.
> **Focus:** the **recovery flow over USB-OTG**. Until you have done it once with a deliberately broken SD card, you will not believe it.

## 8.1  Unbox and inspect

Before connecting any power, put the board on an anti-static mat and do a visual pass:

1. **Visible damage.** Look at every connector. Any pins bent? Any solder joints obviously cold? Any tantalum capacitors discolored? Any screw-holes that punched through a trace? Reject and return if so.
2. **Connectors.** The MINI has, at minimum: a microUSB or USB-C **power + OTG** port, an Ethernet RJ45, a microSD slot, a 40-pin expansion header, an LCD ribbon connector, a JTAG header, and a 4-pin debug-UART header. Locate each.
3. **Jumpers / DIP switches.** Identify the **boot-mode** selector. On most Point Atom MINI revisions this is a 2-position DIP switch or a single jumper near the SoC. The two positions are typically labelled **SD** (boot from SD) and **USB** / **DOWN** (Serial Downloader / recovery). Sometimes a third position selects eMMC.
4. **Silkscreen IDs.** Note the board revision (printed on the top side). When you ask the Point Atom forum for help, the first question they will ask is the revision.

Photograph the top and bottom of the board for your notes. You will refer to these photographs later.

## 8.2  Power rails — measure before applying

If you are a hardware engineer this is reflex. If you are not, do it once and the habit will save you later.

Before any USB cable goes in:

1. Put a multimeter on **continuity** mode.
2. Probe **3V3** to **GND** (any test-point pair on the silkscreen). Expected: open or several kΩ. **Direct short = do not power.**
3. Probe **5V** to **GND**. Expected: open or several kΩ.
4. Probe **VDD_ARM_IN** to **GND** (if exposed). Expected: same.

After connecting power:

1. Probe **3V3** to **GND**. Expected: 3.30 ± 0.05 V.
2. Probe **5V** to **GND** (if accessible from a header). Expected: 4.85 – 5.10 V.
3. (If you have an oscilloscope) — look at the 3V3 rail with AC coupling at 50 mV/div. Anything > 100 mV peak-peak is suspicious.

A board that boots happily for 5 minutes and then resets is almost always a power problem. Catching it early saves debugging time later.

## 8.3  Serial console — the first feedback channel

The Point Atom MINI exposes UART1 (the boot-debug UART) on a 4-pin header, typically labelled **TX**, **RX**, **GND**, **VCC** or similar. **Do not connect VCC** — your CP2102 / CH340 dongle is powered over USB, and double-feeding the rail can damage the board.

Wiring:

| Board pin | Dongle pin |
|-----------|-----------|
| TX (out from board) | RX (into dongle) |
| RX (into board) | TX (out from dongle) |
| GND | GND |
| VCC | **leave open** |

Plug the dongle into the host PC and check:

```sh
$ dmesg | tail -5
[ 1234.567890] usb 1-1.4: new full-speed USB device number 7 using xhci_hcd
[ 1234.689012] cp210x 1-1.4:1.0: cp210x converter detected
[ 1234.689345] usb 1-1.4: cp210x converter now attached to ttyUSB0
$ picocom -b 115200 /dev/ttyUSB0
```

Power the board (USB-OTG cable into a wall adapter, or the board's dedicated power input if present). If the board has an SD card with a known-good Linux image on it, you should immediately see boot messages from U-Boot. If the SD card is empty or absent, you should see nothing — but the serial console should still be alive (just idle).

To prove the serial is alive *without* anything booting on the board, short the dongle's TX to its RX (no board) and type — you should see your keystrokes echo. That confirms the host side.

### Garbage characters?

Almost always one of three causes:

- **Wrong baud rate.** i.MX6ULL ROM and U-Boot speak 115200 8N1 by default. Confirm picocom.
- **Reversed TX/RX.** Swap and retry.
- **Voltage mismatch.** A 5 V dongle on a 3.3 V UART can produce intermittent garbage that looks like a baud problem. Verify your dongle is 3.3 V logic.

## 8.4  The boot-mode selector

The Point Atom MINI's boot-mode switch lets you choose, mechanically, between:

- **Internal boot** → ROM reads SD or eMMC, runs whatever's there.
- **Serial Downloader (SDP)** → ROM enumerates as a USB device and waits for `uuu` / `imx_usb_loader`.

You will use both. Flip the switch to SDP **once now** to confirm it works.

With the switch in SDP and the USB-OTG cable connected to your host PC:

```sh
$ lsusb | grep 15a2
Bus 001 Device 008: ID 15a2:0080 Freescale SemiConductor Inc i.MX 6 SystemOnChip in RecoveryMode
```

That VID:PID `15a2:0080` is the i.MX6ULL Boot ROM in SDP mode. If you see it, the recovery path works. **This is the most important sentence in this chapter.**

If you do not see it:

1. Confirm the boot switch is in SDP position.
2. Confirm the USB-OTG cable is OTG-capable (not all microUSB cables are). On Point Atom MINI, this is the "OTG" labelled port.
3. Power-cycle the board with the switch in SDP from the start (some revisions only sample boot pins at POR).

Flip the switch back to **SD** when done.

## 8.5  Prepare an SD card

Following §3.9 from the host setup chapter:

```sh
$ lsblk
sdc       8:32   1   7.5G  0 disk
```

Identify your SD-card device. **Then identify it again.** Then write a known-good image — either a stock Point Atom-provided image or a Buildroot output from a previous experiment — using the `sd-write.sh` helper:

```sh
$ ~/imx6ull/scripts/sd-write.sh stock-buildroot.img /dev/sdc
Wipe /dev/sdc (size 8.0G)? [y/N] y
... dd output ...
```

Insert the SD card into the board, set the boot switch to SD, power on, watch picocom.

You should see U-Boot greet you within a few seconds:

```
U-Boot 2024.04 (May 12 2024 - 14:33:12 +0700)

CPU:   i.MX6ULL rev1.1 696 MHz (running at 396 MHz)
CPU:   Industrial temperature grade (-40C to 105C) at 38C
Reset cause: POR
Model: Point Atom MINI i.MX6ULL Board
DRAM:  512 MiB
...
=>
```

If you see the `=>` prompt, the hardware works. You can stop here for the first session.

## 8.6  The recovery drill — practice on a "bricked" board

This is the most important exercise in Part I. Do it now, with a working board, so you know how to do it under pressure when a board is genuinely stuck.

1. Confirm the board boots from SD.
2. Power off, eject the SD card.
3. With no SD card, power on. The ROM finds no boot device on USDHC. After a short timeout it falls back to SDP.
4. On the host:

```sh
$ lsusb | grep 15a2
Bus 001 Device 009: ID 15a2:0080 Freescale SemiConductor Inc i.MX 6 SystemOnChip in RecoveryMode
```

5. Push a known-good image to RAM and jump to it:

```sh
$ uuu -b spl u-boot-dtb.imx
uuu (Universal Update Utility) for nxp imx chips -- 1.5.x-0-gxxxxxxx
1:18    1/ 1 [Done                                  ] HID:    -> CMD:hid_dump
1:18    2/ 2 [Done                                  ] FB:     -> ACmd: bootloader
Success 1    Failure 0
```

If picocom shows U-Boot's banner, recovery worked. The board never had an SD card; the ROM loaded U-Boot directly over USB.

Once you've done this, no boot-flash mishap can scare you. You always have a path back.

### Variation — pushing a bare-metal image

In Part II we will push our own bare-metal images this same way:

```sh
$ uuu -b sdp_recovery led.imx
```

The `sdp_recovery` script in `uuu` does exactly what the recovery flow does: `WRITE_FILE` to push our image to OCRAM, then `JUMP_ADDRESS` to its entry. We will use this constantly.

### 8.6a  `uuu` vs MfgTool — same protocol, different shells

Two host-side tools speak the i.MX SDP protocol over the `15a2:0080` USB enumeration:

- **`uuu`** (Universal Update Utility) — NXP's modern, cross-platform CLI tool. What this book uses throughout.
- **MfgTool** (Manufacturing Tool) — NXP's older Windows-only GUI utility. Still widely used in factory programming flows.

Both push the same byte sequences to the same Boot ROM. The translation is straightforward:

- "Run MfgTool to flash" → `uuu -b emmc u-boot.imx zImage.itb rootfs.tar.xz`
- "Manufacturing profile" (MfgTool's XML config) → a `uuu_script.uuu` file with one line per `WRITE_FILE` / `JUMP_ADDRESS` step
- "Stop the MfgTool process" → not needed; `uuu` exits after the script

Pick whichever one your team standardizes on.

## 8.7  JTAG (optional but recommended)

For Part II's bare-metal chapters, JTAG is enormously helpful: hardware breakpoints, single-step, register dumps. It is **not** required — you can debug entirely with `printf` over UART — but the productivity gain is real.

The Point Atom MINI exposes a 10-pin JTAG header (sometimes 20-pin; check the silkscreen). The signals:

- TMS, TCK, TDI, TDO, nTRST, RESET, GND, 3V3 sense

Suitable adapters:

- **FT2232H minimodule** — cheap (~$25), works with OpenOCD.
- **J-Link EDU / J-Link Plus** — best support, more expensive (~$60 / $400).

Setup is deferred to Chapter 56, where we configure OpenOCD for both U-Boot and bare-metal debugging.

For now, simply identify the header and confirm it is populated. If your board revision has unpopulated JTAG pads, you may need to solder a header. This is the cheapest hardware upgrade you can buy yourself for this book.

## 8.8  Network connectivity

The Point Atom MINI has at least one Ethernet port (some revisions have two). The PHY is a KSZ8081RNB or similar.

Wiring:

- Connect the board's Ethernet to your dev host via a switch or directly.
- Confirm link LED on the board's RJ45.

We will not configure IP yet — that comes after Chapter 23 when U-Boot's network commands work and Chapter 31 when the Linux rootfs runs `ifconfig`. For now, simply verify the cable is present and the link LED lights when connected.

## 8.9  End-of-chapter checklist

| Item | Status |
|------|--------|
| Power rails verified with multimeter | ☐ |
| Serial console working at 115200 8N1 | ☐ |
| Stock SD-card image boots; U-Boot prompt obtained | ☐ |
| Boot-mode switch positions identified | ☐ |
| SDP mode confirmed: `lsusb` shows `15a2:0080` | ☐ |
| Recovery via `uuu` succeeded with no SD card | ☐ |
| Ethernet link LED lights when cabled | ☐ |
| JTAG header located (and adapter ordered if you don't have one) | ☐ |

When all boxes are ticked, we are ready for Part II.

## 8.10  Lab

The chapter itself is the lab. Specifically:

- **Photograph** every connector, switch, jumper, and the boot-mode selector in known states. Annotate the photographs in your notes.
- **Document** the exact `uuu` command line that performs recovery on your board, including the path to the known-good image you used. This entry in your notes will save you in the future.
- **Make a deliberate failure.** Eject the SD, flip the switch to SD anyway, power on. Note what happens (the board falls into SDP after a timeout, or sits silently — record which). Then flip to SDP, power-cycle, recover. Document the timing.

## 8.11  Pitfalls

- **USB-OTG cable confusion.** A standard "charging" microUSB cable lacks the ID pin pulldown that signals OTG-host mode. Some boards work with any cable; some don't. If `lsusb` doesn't show the SDP device, try a different cable before suspecting the board.
- **Hot-swapping SD cards.** The Point Atom MINI's SD slot is not always hot-swap-safe. Power off before inserting / ejecting unless you have explicit confirmation otherwise from the schematic.
- **Plugging the 3.3 V serial dongle into a 5 V port.** The dongle survives; the board may not. Double-check pin labels.
- **Powering from OTG and a separate barrel jack simultaneously.** Some boards have protection; some don't. Pick one source.
- **Leaving the boot-mode switch in SDP after recovery.** Easy to forget. Symptom: next boot, board does nothing. Always flip back to SD when done.
- **Trusting LED indicators alone.** Some boards have a "PWR" LED that simply means USB power is present, not that the SoC is alive. Always trust serial output, not LEDs.

## 8.12  Going deeper

- The Point Atom MINI **schematic** (PDF that came with your board). Print the page that shows the SoC ball-out and the boot-pin section; tape it to the wall above your bench.
- *Designing a Hardware Solution Based on the i.MX 6UL/6ULL* (NXP AN12085) — bring-up checklist from NXP's perspective.
- The `uuu` README at <https://github.com/nxp-imx/mfgtools> — exhaustive command reference.
- Any oscilloscope-based bring-up guide. A 2-channel scope at 100 MHz is sufficient for everything in this book.

---

> Part I ends here. You have a host that can build, a board that you trust, a recovery path you have tested, and a mental model of what the hardware looks like.
>
> Part II begins with the most fun chapter in the book: a blinking LED, in pure ARM assembly, on a Cortex-A7. We are going to build the entire bare-metal stack ourselves, register by register, before we ever again let someone else's bootloader do it for us.
