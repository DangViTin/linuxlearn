# Chapter 8: Hardware bring-up checklist

> **What:** inspect the MINI, document its power arrangement, open its serial bridge, confirm ROM SDP enumeration, and identify the spare card. Image transfer and code execution are later milestones.
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
- An unpowered resistance screen shows no suspected short; this is not proof that every rail is healthy.
- The built-in USB-TTL serial bridge appears on the host.
- The boot-mode selector can select USB mode, where the Boot ROM starts SDP.
- The i.MX6ULL Boot ROM enumerates as a USB SDP device.
- You can identify the SD-card device on the host without guessing.

The first real image we trust will be built later by us. That is the point of Part II.

## 8.2  Unbox and inspect

Before connecting power, put the board on an anti-static mat and do a visual pass:

1. **Visible damage.** Look at every connector. Are any pins bent? Are any solder joints cracked or incomplete? Are any capacitors discolored? Did any screw hole damage a trace? Reject and return the board if you find serious damage.
2. **Connectors.** Locate the USB-OTG port, the built-in USB-TTL debug port, Ethernet RJ45, microSD slot, 40-pin expansion header, LCD ribbon connector, JTAG header, and any power input.
3. **Boot-mode selector.** Match your PCB revision to the MINI v2.2 schematic. Record switch numbering/ON direction and compare the patterns in Section 8.5. Do not infer positions from mode names alone.

Photograph the top and bottom of the board. Also photograph the boot switch in each position. These photos save time later when the board is inside a case or under cables.

## 8.3  Power rails, measure before applying power

### Choose the power arrangement before any cable

The reference MINI v2.2 power sheet (sheet 3, PDF page 4) has a DC converter, `USB_TTL` VBUS (`VUSB`), OTG VBUS circuitry, K1, and rail headers JP2/JP3. The schematic's `DCDC_5V` rail is **not** a specification for the barrel input. Do not plug a guessed 5 V/12 V supply into that input.

Use the supplier's arrangement for your **exact baseboard and core revision**. Record the input connector, rated voltage/current/polarity, K1 position, and any jumper settings before applying power. Attach the two USB data cables only if that arrangement documents their VBUS paths. If you have only the schematic and cannot establish those details, stop and obtain the matching board power guide; the book does not provide an electrically validated universal jumper recipe.

| Connection | Role | Power check before attachment |
|---|---|---|
| Supplier-approved supply input | Main board supply in the selected arrangement | Rating, polarity, selector/jumpers match the guide |
| USB-TTL / DEBUG USB | Host serial bridge | Cable carries VBUS; determine whether `VUSB` can feed the board in the selected K1 state |
| USB-OTG | ROM SDP data link | Cable also carries VBUS; check the documented OTG isolation/power path |
| External TTL adapter, if used | UART data only | 3.3 V signal levels; leave adapter VCC disconnected |

A power switch may leave the bridge or other circuitry partly supplied through USB. For a **cold power cycle**, disconnect the main input and every USB/power-capable adapter, allow rails to discharge, then reconnect in the documented order. Never move power jumpers on a powered board. This conservative prerequisite is deliberate: the schematic has been inspected, but simultaneous-input behavior has not been measured here.

If you are a hardware engineer, this is normal practice. If you are not, do it once here and keep the habit.

Before any USB cable goes in:

1. Disconnect all supplies, USB cables, and adapters; allow capacitors to discharge. Use known labeled test points, not guessed adjacent pins.
2. Select **resistance** mode and measure 3V3-to-GND, then 5V-to-GND where accessible. Record settled values. A brief continuity beep can be capacitors charging; the beep threshold is meter-dependent.
3. A persistent near-zero reading suggests a short: stop and investigate. No normal-resistance threshold is specified here without measurements for this revision. A higher reading alone does not certify every rail.

After connecting the documented supply arrangement, switch the meter to **DC voltage**, with the black probe on known GND. Secure the probe so it cannot slip across nearby pins:

1. Probe **3V3** to **GND**. Expected: about 3.30 V.
2. Probe **5V** to **GND** if accessible. Expected: about 5 V.

A board that resets after a few minutes is often a power problem. It is better to catch this before writing any boot code.

These external-rail readings do not validate core/DDR rail sequencing or every supply. If values are unexpected, disconnect power before investigating.

## 8.4  Built-in USB-TTL serial console

The Point Atom MINI already includes a USB-to-TTL serial bridge for the debug UART. You do **not** need an external CP2102, CH340, FTDI, or jumper wires for normal use.

After Section 8.3's power-path check, attach USB-TTL/DEBUG USB. It is separate from the USB-OTG port; check the silkscreen.

On Linux, check which serial device appeared:

```sh
$ sudo dmesg | tail -20
```

You should see something like one of these:

```text
ch341-uart converter now attached to ttyUSB0
```

Open it at 115200 8N1:

```sh
$ sudo picocom -b 115200 /dev/ttyUSB0
```

If your host reports `/dev/ttyACM0`, use that instead:

```sh
$ sudo picocom -b 115200 /dev/ttyACM0
```

At this point, silence is normal. We do not yet have a bootable SD image, and the Boot ROM does not print a banner on UART. The important test here is that the host can open the serial port and keep it open.

Opening the bridge does not prove the SoC's UART TX pin or baud setup. A factory image in eMMC/NAND may print in its storage mode: record that output rather than erasing it. If no device appears inside an Ubuntu VM, attach the bridge to the guest and close any Windows-side serial session. Permission denied on logs is handled by the explicit `sudo dmesg`; restricted device access uses `sudo` without changing groups.

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

For the **MINI v2.2 schematic's printed D1-D8 order**, its BOOT table gives:

| Board selection | D1 | D2 | D3 | D4 | D5 | D6 | D7 | D8 |
|---|---|---|---|---|---|---|---|---|
| USB | OFF | ON | OFF | OFF | OFF | OFF | OFF | OFF |
| MicroSD | ON | OFF | OFF | OFF | OFF | OFF | ON | OFF |
| eMMC | ON | OFF | ON | OFF | OFF | ON | ON | OFF |
| NAND | ON | OFF | OFF | OFF | ON | OFF | OFF | OFF |

This is transcribed from the schematic, not a hardware-tested table for every MINI/ALPHA revision. Match D1 to the PCB's actual switch number 1 and use its printed ON mark; do not reverse the row because the board is rotated. D1/D2 route BOOT_MODE1/0; the remaining switches configure storage-related straps. USB must result in SoC mode `01`; storage selections use Internal Boot with additional configuration. Confirm your core's fuse state and routing rather than assuming an unprovisioned board.

Straps are latched on the documented reset event [RM 8.2.1]. Change them only while fully unpowered and use the cold-cycle procedure above; a warm reset button need not re-sample every setting.

## 8.6  Confirm USB mode and SDP enumeration

This checks **ROM SDP enumeration**, not a recovery download or execution.

1. Disconnect all sources for a cold cycle as in Section 8.3.
2. Set the boot-mode switch to **USB** mode.
3. Verify the power-guide arrangement permits the USB-OTG cable's VBUS connection.
4. Reconnect the documented power/USB arrangement with the switch already set.
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
$ sudo "$IMX6ULL_HOME/build/mfgtools/uuu/uuu" -lsusb
```

Seeing SDP proves visibility of the ROM interface. It does not prove command acceptance, image transfer, authentication, or entry-point execution. Chapter 9's observed LED is the first execution check.

If you do not see `15a2:0080`:

1. Confirm the boot switch is in the **USB** position.
2. Confirm you are using the USB-OTG port, not the USB-TTL debug port.
3. Try another USB data cable.
4. Power-cycle the board with the switch already in **USB** mode.
5. Check `sudo dmesg` for USB errors and, in a VM, confirm the ROM device is attached to Ubuntu rather than Windows.

## 8.7  Prepare the SD-card workflow

We are not writing a boot image yet. We only prepare the safe workflow so that Chapter 11 does not start with SD-card confusion.

Insert a microSD card into the host and identify it:

```sh
$ lsblk -o NAME,PATH,SIZE,MODEL,SERIAL,TRAN,RM,TYPE,MOUNTPOINTS
```

Read the `PATH`, `TYPE`, and `MOUNTPOINTS` columns in your actual output. For a card observed as `/dev/sdc`, the whole card is that `disk` row, not a `part` row such as `/dev/sdc1`. This is an example name, not a promised result.

Record capacity, model/serial, reader connection, and today's device name. Names can change after reconnecting; a note is not future authorization to write that path. Where available, also record `/dev/disk/by-id/` identity.

Do **not** run `dd` casually. A wrong device name can erase your host disk. Before every SD write in this book:

1. Run `lsblk`.
2. Insert or remove the SD card.
3. Run `lsblk` again.
4. Confirm which device appeared or disappeared.
5. Match capacity/model/serial, reject host/system/data disks, and unmount every mounted card partition. Write only when the later chapter supplies a real image and the identity is unambiguous.

The first real SD write happens later when we build an image. For now, the task is to know the device name and make sure the card reader works.

> **Raw/full-card image rule:** the images used by these labs are written to the whole card. That is not a universal rule for every block-device operation or filesystem image.

## 8.8  What `uuu` will do later

`uuu` is NXP's host tool for talking to the Boot ROM over SDP.

When the board selector is in **USB** mode, the Boot ROM enters SDP. Later chapters will use commands like:

```sh
$ sudo "$IMX6ULL_HOME/build/mfgtools/uuu/uuu" led.imx
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

Setup is deferred to [JTAG/OpenOCD/GDB](../part8-debug/ch118-jtag-openocd-gdb.md). Header location is optional now. Before connecting an adapter later, verify the exact pinout: voltage sense is normally a reference input, not permission to power the target from the probe.

> **OpenOCD:** the host program that talks to a JTAG adapter and exposes a GDB server.

## 8.10  Ethernet, only a physical check for now

The Point Atom MINI has one Ethernet port.

Because we do not have Linux or U-Boot running yet, we cannot test IP networking in this chapter. At most, do a physical check:

1. Plug in an Ethernet cable.
2. Confirm the connector fits firmly.
3. Observe whether the link LED lights.

Do not treat a dark link LED as a board failure yet. Some PHYs need software configuration before the link LED behaves as expected. Real Ethernet testing comes later, after U-Boot and Linux are running.

## 8.11  End-of-chapter checklist

| Required-now record | Observation / failure reason |
|---|---|
| Base/core PCB revision and matching guide | |
| Supply input, rating/polarity, selector/jumpers, USB power paths | |
| Unpowered resistance screen, settled values | |
| Accessible powered 3V3/5V readings | |
| Serial bridge identity and port opened at 115200 8N1 | |
| USB switch pattern and ROM VID:PID `15a2:0080` | |
| Spare card capacity/model/serial and today's device path | |
| Photographs of connectors, switch order, and cabling | |

Optional: locate JTAG and observe Ethernet. Neither is a prerequisite for the first LED image. Serial opening and ROM enumeration are access checks; transfer and execution are not yet checked.

When the checklist is complete, the board is ready for Part II. It may still have no bootable image. That is expected because this chapter verifies access paths, not a previously built system.

## 8.12  Lab

Complete the required-now table in `~/imx6ull/notes/ch08-bring-up.md`, including actual readings and any reason a step cannot proceed. Attach your board/cabling photos, serial identity, exact ROM enumeration output, and card identity. Mark unperformed checks as unperformed rather than filling a box from an expected-output example.

Keep these results as the recovery checklist for later chapters.

## 8.13  Pitfalls

- **Confusing USB-TTL with USB-OTG.** USB-TTL is the serial console. USB-OTG is the Boot ROM recovery path. They are different functions and may be different connectors.
- **Expecting serial output too early.** With no valid image, silence is normal. The Boot ROM does not print progress messages on the debug UART.
- **Changing boot switches while powered.** Power off first. Boot pins are sampled at reset.
- **Using a charge-only USB cable.** The board may power up but never enumerate. Use a data cable.
- **Writing to the wrong SD device.** Always compare `lsblk` before and after inserting the card.
- **Assuming a data cable cannot supply power.** USB-TTL and OTG carry VBUS. Use only the revision-specific documented combination; unplug all supply paths for a real cold cycle.
- **Assuming Ethernet is broken because no link LED appears.** Full Ethernet testing waits until software configures the PHY.

## 8.14  Going deeper

- The Point Atom MINI schematic. Print the pages for power, boot mode, USB-OTG, USB-TTL, and SD card.
- **IMX6ULLHDG**, *i.MX6ULL Hardware Development Guide*, in [NXP's documentation catalog](https://www.nxp.com/products/i.MX6ULL?linkline=Data+Sheet). It is a SoC guide, not the MINI barrel-supply specification.
- The `uuu` README at <https://github.com/nxp-imx/mfgtools>.
- An oscilloscope is optional for the checks here. Select probes/bandwidth for a later specific signal measurement; a generic scope rating does not certify DDR or every interface.

---

> Part I ends with a configured host, recorded physical checks, and confirmed ROM SDP enumeration. Recovery transfer/execution remains to be tested.
>
> Part II begins with a blinking LED in pure ARM assembly. We will create the first image ourselves, then use the serial console and USB-OTG recovery path from this chapter to run it.
