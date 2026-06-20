# Chapter 8: Hardware bring-up checklist

> **What:** the physical, hands-on first contact with the Point Atom MINI. By the end you have checked power, opened the built-in USB-TTL serial console, identified the boot-mode switch, confirmed the USB-OTG recovery path, and prepared the SD-card workflow.
>
> **Why:** at this point we do **not** have a known-good boot image yet. That is normal. The goal of this chapter is not to boot Linux. The goal is to prove the board can power up, expose its debug ports, and use USB mode to enter the Boot ROM's SDP recovery path.
>
> **Focus:** the **USB-OTG Serial Downloader Protocol (SDP)** path. If SD boot fails later, SDP is the way back in.


## 8.1  What we can and cannot prove yet

Before touching the board, set the right expectation.

At the start of this book, we have:

- A host machine with toolchains and serial tools installed.
- A Point Atom MINI board.

So this chapter does **not** ask you to boot a stock image. It asks you to verify the things that do not require a boot image:

- The board has no obvious physical damage.
- The power rails are not shorted.
- The built-in USB-TTL serial bridge appears on the host.
- The boot-mode selector can select USB mode, where the Boot ROM starts SDP.
- The i.MX6ULL Boot ROM enumerates as a USB SDP device.
- You can identify the SD-card device on the host without guessing.

The first real image we trust will be built later by us. That is the point of Part II.

## 8.2  Unbox and inspect

Before connecting power, put the board on an anti-static mat and do a visual pass:

1. **Visible damage.** Look at every connector. Are any pins bent? Are any solder joints cracked or incomplete? Are any capacitors discolored? Did any screw hole damage a trace? Reject and return the board if you find serious damage.
2. **Connectors.** Locate the USB-OTG port, the built-in USB-TTL debug port, Ethernet RJ45, microSD slot, 40-pin expansion header, LCD ribbon connector, JTAG header, and any power input.
3. **Boot-mode selector.** Locate the selector and identify its four labeled modes: **SD**, **eMMC**, **NAND**, and **USB**. Record the switch pattern for each mode.

Photograph the top and bottom of the board. Also photograph the boot switch in each position. These photos save time later when the board is inside a case or under cables.

## 8.3  Power rails, measure before applying power

If you are a hardware engineer, this is normal practice. If you are not, do it once here and keep the habit.

Before any USB cable goes in:

1. Put a multimeter on **continuity** mode.
2. Probe **3V3** to **GND** on a header or test point. Expected: open circuit or several kOhm. **Direct short = do not power.**
3. Probe **5V** to **GND**. Expected: open circuit or several kOhm.

After connecting power:

1. Probe **3V3** to **GND**. Expected: about 3.30 V.
2. Probe **5V** to **GND** if accessible. Expected: about 5 V.

A board that resets after a few minutes is often a power problem. It is better to catch this before writing any boot code.

## 8.4  Built-in USB-TTL serial console

The Point Atom MINI already includes a USB-to-TTL serial bridge for the debug UART. You do **not** need an external CP2102, CH340, FTDI, or jumper wires for normal use.

Connect the board's **USB-TTL** or **DEBUG USB** port to the host. This is separate from the USB-OTG recovery port. Check the silkscreen.

On Linux, check which serial device appeared:

```sh
$ dmesg | tail -20
```

You should see something like one of these:

```text
ch341-uart converter now attached to ttyUSB0
```

Open it at 115200 8N1:

```sh
$ picocom -b 115200 /dev/ttyUSB0
```

If your host reports `/dev/ttyACM0`, use that instead:

```sh
$ picocom -b 115200 /dev/ttyACM0
```

At this point, silence is normal. We do not yet have a bootable SD image, and the Boot ROM does not print a banner on UART. The important test here is that the host can open the serial port and keep it open.

Later, when our own image prints text, this is where it will appear.

### Unreadable characters later

If you later see unreadable output after our code starts printing, the common causes are:

- Wrong baud rate. Use 115200 8N1.
- Opening the wrong `/dev/ttyUSBx` device.
- Bad USB cable or unstable power.

Do not debug UART text until you have a program that is supposed to print. Silence before that is not a serial failure.

## 8.5  Boot-mode selector

The Point Atom MINI exposes four boot modes:

| Board mode | What the Boot ROM tries | When we use it |
|------------|-------------------------|----------------|
| SD | Reads a boot image from the microSD card | Bare-metal labs and removable development images |
| eMMC | Reads a boot image from onboard eMMC | An installed system on an eMMC board |
| NAND | Reads a boot image from onboard raw NAND flash | An installed system on a NAND board |
| USB | Starts Serial Downloader Protocol (SDP) over USB-OTG | Recovery and early bring-up |

The board normally has either eMMC or NAND fitted, depending on the core-board version. A storage mode cannot boot if that device is not fitted or does not contain a valid image. Record all four switch patterns even if your core board does not contain both storage types.

The Boot ROM samples boot pins at reset. Do not expect a switch change to take effect while the board is already running.

## 8.6  Confirm USB mode and SDP enumeration

This test verifies that the Boot ROM and USB-OTG recovery path are available.

1. Power off the board.
2. Set the boot-mode switch to **USB** mode.
3. Connect the board's **USB-OTG** port to the host.
4. Power on the board.
5. On the host, run:

```sh
$ lsusb | grep 15a2
```

Expected output:

```text
Bus 001 Device 008: ID 15a2:0080 Freescale Semiconductor, Inc. i.MX 6ULL in Serial Downloader Mode
```

The exact text can vary, but `15a2:0080` is the key. It means the i.MX6ULL Boot ROM is alive and waiting for SDP commands.

You can also ask `uuu` to list visible i.MX devices:

```sh
$ uuu -lsusb
```

If you see the SDP device, USB mode works. We are not pushing an image yet because we have not built one. Later chapters will use this same path to load our bare-metal `.imx` images.

If you do not see `15a2:0080`:

1. Confirm the boot switch is in the **USB** position.
2. Confirm you are using the USB-OTG port, not the USB-TTL debug port.
3. Try another USB data cable.
4. Power-cycle the board with the switch already in **USB** mode.
5. Check `dmesg` for USB errors.

## 8.7  Prepare the SD-card workflow

We are not writing a boot image yet. We only prepare the safe workflow so that Chapter 11 does not start with SD-card confusion.

Insert a microSD card into the host and identify it:

```sh
$ lsblk
```

Example:

```text
sdc       8:32   1   7.5G  0 disk
|-sdc1    8:33   1   256M  0 part
`-sdc2    8:34   1   7.2G  0 part
```

Write the device name in your notes. In this example the device is `/dev/sdc`, not `/dev/sdc1`.

Do **not** run `dd` casually. A wrong device name can erase your host disk. Before every SD write in this book:

1. Run `lsblk`.
2. Insert or remove the SD card.
3. Run `lsblk` again.
4. Confirm which device appeared or disappeared.
5. Only then write to that device.

The first real SD write happens later when we build an image. For now, the task is to know the device name and make sure the card reader works.

> **SD-card rule:** write to the whole device, such as `/dev/sdc`, not to a partition such as `/dev/sdc1`.

## 8.8  What `uuu` will do later

`uuu` is NXP's host tool for talking to the Boot ROM over SDP.

When the board selector is in **USB** mode, the Boot ROM enters SDP. Later chapters will use commands like:

```sh
$ uuu -b sdp_recovery led.imx
```

Conceptually, that command does two things:

1. Sends an image file over USB-OTG into OCRAM.
2. Tells the Boot ROM to jump to the image entry point.

This is why Section 8.6 matters. If `15a2:0080` appears, the ROM interface needed for early bare-metal bring-up is available.

We will not use MfgTool in this book. MfgTool is NXP's older Windows manufacturing GUI. It speaks the same family of protocols, but `uuu` is the modern CLI tool and is easier to script.

## 8.9  JTAG, optional but useful

For Part II's bare-metal chapters, JTAG is helpful: hardware breakpoints, single-step, and register dumps. It is **not** required. You can debug the early chapters with UART prints and `uuu`.

Locate the JTAG header now. The important signals are:

- TMS
- TCK
- TDI
- TDO
- nTRST
- RESET
- GND
- 3V3 sense

Suitable adapters include:

- FT2232H-based adapters, which work with OpenOCD.
- J-Link EDU or J-Link Plus, which provide commercial tooling and device support.

Setup is deferred to Chapter 56. For now, only confirm where the header is and whether you need to solder pins.

> **OpenOCD:** the host program that talks to a JTAG adapter and exposes a GDB server.

## 8.10  Ethernet, only a physical check for now

The Point Atom MINI has one Ethernet port.

Because we do not have Linux or U-Boot running yet, we cannot test IP networking in this chapter. At most, do a physical check:

1. Plug in an Ethernet cable.
2. Confirm the connector fits firmly.
3. Observe whether the link LED lights.

Do not treat a dark link LED as a board failure yet. Some PHYs need software configuration before the link LED behaves as expected. Real Ethernet testing comes later, after U-Boot and Linux are running.

## 8.11  End-of-chapter checklist

| Item | Status |
|------|--------|
| Board revision recorded | [ ] |
| Connectors and boot switch photographed | [ ] |
| 3V3 and 5V rails checked for shorts before power | [ ] |
| 3V3 and 5V measured after power | [ ] |
| Built-in USB-TTL serial bridge appears on host | [ ] |
| `picocom` opens the serial port at 115200 8N1 | [ ] |
| USB mode confirmed by SDP device `15a2:0080` | [ ] |
| SD, eMMC, NAND, and USB switch patterns recorded | [ ] |
| SD-card device identification practiced with `lsblk` | [ ] |
| JTAG header located | [ ] |

When the checklist is complete, the board is ready for Part II. It may still have no bootable image. That is expected because this chapter verifies access paths, not a previously built system.

## 8.12  Lab

Complete these four tasks:

1. Photograph the board, connectors, boot switch, and cable positions.
2. Record the serial device name, for example `/dev/ttyUSB0` or `/dev/ttyACM0`.
3. Record the exact `lsusb` or `uuu -lsusb` output while the selector is in USB mode.
4. Insert an SD card into the host and practice identifying the whole-card device with `lsblk`.

Keep these results as the recovery checklist for later chapters.

## 8.13  Pitfalls

- **Confusing USB-TTL with USB-OTG.** USB-TTL is the serial console. USB-OTG is the Boot ROM recovery path. They are different functions and may be different connectors.
- **Expecting serial output too early.** With no valid image, silence is normal. The Boot ROM does not print progress messages on the debug UART.
- **Changing boot switches while powered.** Power off first. Boot pins are sampled at reset.
- **Using a charge-only USB cable.** The board may power up but never enumerate. Use a data cable.
- **Writing to the wrong SD device.** Always compare `lsblk` before and after inserting the card.
- **Powering the board from two sources.** Use one power source unless the board schematic explicitly permits both inputs at the same time.
- **Assuming Ethernet is broken because no link LED appears.** Full Ethernet testing waits until software configures the PHY.

## 8.14  Going deeper

- The Point Atom MINI schematic. Print the pages for power, boot mode, USB-OTG, USB-TTL, and SD card.
- NXP AN12085, *Designing a Hardware Solution Based on the i.MX 6UL/6ULL*.
- The `uuu` README at <https://github.com/nxp-imx/mfgtools>.
- An oscilloscope-based board bring-up guide. A 2-channel 100 MHz scope covers the measurements used in this book.

---

> Part I ends here. You have a host that can build, a board whose physical access paths are known, and a Boot ROM recovery path you have tested.
>
> Part II begins with a blinking LED in pure ARM assembly. We will create the first image ourselves, then use the serial console and USB-OTG recovery path from this chapter to run it.
