---
chapter: "24I"
title: "U-Boot display and boot screen"
part: "III - U-Boot, deeply"
estimated_pages: 16
status: draft
---

# Chapter 24I: U-Boot display and boot screen

A lit backlight can make a completely uninitialized LCD look alive. The
opposite is possible too: valid pixels are being scanned out, but the
backlight is off and the screen appears black. Before adding a logo, separate
those two paths: data reaches the panel through eLCDIF; light comes from a
board-specific power and backlight circuit.

We will prepare the U-Boot side of an RGB boot screen, using upstream
**v2026.04** and the Chapter 22 `mx6ull_pa_mini` port. The reference MINI does
not automatically include a qualified LCD carrier. Without the fitted
panel/carrier schematic and panel datasheet, do the source/image exercises
only; there is no universal LCD timing or backlight GPIO to copy.

## 24I.1  What a U-Boot boot screen really is

A framebuffer is a RAM region containing pixels. eLCDIF repeatedly reads
those pixels and produces the panel's clock, sync, and data signals. U-Boot
loads a BMP into a **different** RAM region, decodes it, and writes the
result into that framebuffer.

```text
trusted BMP on storage -> bounded image buffer -> BMP decoder -> framebuffer
                                                                  |
                                                       eLCDIF + board wiring
                                                                  |
                                                          powered RGB panel
```

| Stage | Display owner |
|---|---|
| U-Boot | Its video driver, framebuffer, and optional text/BMP output |
| Linux after its display driver probes | Its own driver and buffers |

Linux may reset the controller/panel and redraw. Preserving the image across
handoff is a separate integration project, not a property of `bmp display`.
Changing Linux Device Tree does not fix U-Boot's own control DT or driver.

```{figure} ../illustrations/part3/17-pixels-and-backlight.png
:name: fig-p3-pixels-backlight
:figclass: concept-sketch
:width: 100%
:alt: A BMP buffer is decoded into a separate framebuffer that eLCDIF reads to drive an RGB panel. Board power and backlight use a distinct path to the panel.

Image bytes, scanout pixels, and panel light follow different paths. A black screen can therefore have more than one cause. The drawing is a data-flow model, not a carrier schematic or proof of display operation.
```

## 24I.2  Files changed in this chapter

| File or area | Responsibility |
|---|---|
| `configs/mx6ull_pa_mini_defconfig` | DM video, MXS/eLCDIF driver, BMP formats, filesystem commands |
| `arch/arm/dts/imx6ull-pa-mini.dts` | Verified display timing/pinmux description |
| Board display integration | Rail, reset, and backlight sequencing, before the required operation |
| `include/configs/mx6ull_pa_mini.h` | Optional splash command, without replacing safety policy |
| Identified boot partition | Trusted, validated `splash.bmp` |

This extends the same board port. It does not create a second board or change
its ROM/DCD boot path. DDR, display clocks, memory reservations, and power
must already be qualified for the actual hardware.

## 24I.3  Enable the display-related configs

In v2026.04 use:

```text
CONFIG_VIDEO=y
CONFIG_VIDEO_MXS=y
CONFIG_VIDEO_BPP32=y
CONFIG_CMD_BMP=y
CONFIG_BMP=y
CONFIG_BMP_24BPP=y
CONFIG_CMD_FAT=y
CONFIG_FS_FAT=y
CONFIG_CMD_ITEST=y
```

`VIDEO` is the driver-model video option in this release; there is no separate
`DM_VIDEO` switch to add. `VIDEO_MXS` selects `drivers/video/mxsfb.c` for
this LCDIF family. The inherited i.MX6UL DT compatible includes
`fsl,imx6sx-lcdif`, which this driver matches. Its 24/18-bit output paths use
**32-bit framebuffer storage**. `BMP_24BPP` enables decoding a 24-bit source
BMP; the source-file format and framebuffer format are not the same setting.

`SPLASH_SCREEN`/`SPLASH_SCREEN_ALIGN` are optional framework choices, not
requirements for the manual `bmp display` path used here. Enabling them alone
does not load a file. Automatic framework loading requires its own preparation
hook/source configuration. `CMD_CLS` is optional for console experiments.

Build and inspect a separate output directory:

```sh
$ . ~/imx6ull/scripts/env.sh
$ cd ~/imx6ull/src/u-boot
$ make O="$IMX6ULL_HOME/build/uboot-video" ARCH=arm CROSS_COMPILE="$CROSS_COMPILE" mx6ull_pa_mini_defconfig
$ make O="$IMX6ULL_HOME/build/uboot-video" ARCH=arm CROSS_COMPILE="$CROSS_COMPILE" -j "$(nproc)"
$ grep -E 'CONFIG_(VIDEO|VIDEO_MXS|VIDEO_BPP32|BMP|BMP_24BPP|CMD_BMP|CMD_FAT|CMD_ITEST)=' "$IMX6ULL_HOME/build/uboot-video/.config"
```

The grep is an inspection after configuration, not a substitute for reading
Kconfig dependencies or a successful build. The unmodified EVK defconfig
has no enabled video path; it is not a ready-made MINI LCD configuration.

The ULL EVK header also does not supply the base alias required by this
driver. In the MINI header, retain the architecture register definitions and
add the same alias used by the upstream UL/Colibri-ULL ports:

```c
#include <asm/arch/imx-regs.h>
#define MXS_LCDIF_BASE MX6UL_LCDIF1_BASE_ADDR
```

Without it, enabling `VIDEO_MXS` on the ULL EVK-derived port fails to compile
at `MXS_LCDIF_BASE`. This is a source integration requirement, not permission
to write controller registers or a hardware validation result.

## 24I.4  Add the LCD to the U-Boot Device Tree

The MXS driver reads an LCDIF `display` phandle, then `bits-per-pixel` and the
**first** `display-timings` entry in that referenced node. In this version it
does not use `bus-width` to choose the wire format or `native-mode` to select
another timing entry. Match its actual parser, not just a Linux binding.

The following is a **timing-format example**, not a qualified MINI panel.
Do not enable it on hardware until every value and wire is checked against
the fitted carrier/panel. It assumes 24-bit RGB wiring and active-high DE:

```dts
&lcdif {
    pinctrl-names = "default";
    pinctrl-0 = <&pinctrl_lcdif>;
    display = <&display0>;
    status = "okay";

    display0: display {
        bits-per-pixel = <24>;
        display-timings {
            timing0 {
                clock-frequency = <33000000>;
                hactive = <800>;
                vactive = <480>;
                hfront-porch = <40>;
                hback-porch = <88>;
                hsync-len = <48>;
                vfront-porch = <13>;
                vback-porch = <32>;
                vsync-len = <3>;
                hsync-active = <0>;
                vsync-active = <0>;
                de-active = <1>;
                pixelclk-active = <0>;
            };
        };
    };
};
```

Supply the board-specific `pinctrl_lcdif` group under the existing IOMUXC
node. For 24-bit wiring that normally includes LCD_CLK, ENABLE/DE, HSYNC,
VSYNC, and DATA00..23 with the appropriate pad macros. An 18-bit panel needs
its documented signal mapping and driver format; do not arbitrarily remove
six wires. Review conflicts with NAND, Ethernet, and GPIO uses on the carrier.
Pad drive strength and slew are electrical choices, not universal `0x79`
settings.

The example's horizontal total is `800+40+88+48=976` clocks and vertical total
`480+13+32+3=528` lines. Divide the pixel clock by their product to obtain the
nominal frame rate. This is arithmetic, not a measured/calibrated clock or a
panel-approved refresh rate. Verify actual clock capability, edge semantics,
and DE polarity; this MXS implementation sets ENABLE polarity high during
setup, so a DE-low panel needs source-level investigation rather than a DT
promise alone.

The driver does **not** resolve a generic panel/backlight phandle and perform
all carrier power/reset sequencing for you. Provide that reviewed integration
before probe where needed: stabilize rails, apply reset timing, prepare valid
scanout, then enable the backlight in the panel-approved order. A
`gpio-backlight` node on its own is not proof that this path invokes it.
Critical power checks from Chapter 24H must precede the operation they guard,
not merely run later in `board_late_init()`.

## 24I.5  Prepare the BMP file

Use one trusted, uncompressed Windows-style BMP with a 40-byte DIB header,
24-bit BGR pixels, positive height (bottom-up rows), no palette, and dimensions
that fit the verified panel. Start with clear color bars and a border; they
make swapped colors and shifted edges visible without a complex logo.

For the **800 x 480 format example**, each row is padded to a multiple of
four bytes:

```text
row bytes = ((800 * 3 + 3) / 4 rounded down) * 4 = 2400
pixel bytes = 2400 * 480 = 1152000
file bytes = 14 + 40 + 1152000 = 1152054
framebuffer bytes for the driver's 32-bit path = 800 * 480 * 4 = 1536000
```

These are calculated sizes for that format, not observed output. Inspect the
actual file's header, offset, dimensions, compression, and total length on the
host. U-Boot's `bmp info` reads header fields; it does not fully validate a
file against a supplied buffer length. Do not feed arbitrary recovery-uploaded
BMPs to a bootloader decoder as if it were a hardened image service.

Put the checked file on the **identified** intended boot partition using the
already approved storage-copy workflow. Do not use a guessed `/dev/sdX1`
mount/copy recipe. If using Chapter 24G UMS, the host must own the exposed
range exclusively and release it before U-Boot loads the file.

## 24I.6  Manual U-Boot display test

First establish the image-buffer reservation using `bdinfo`, the port's
memory layout, and the video framebuffer reservation. The image buffer must
fit entirely inside qualified DDR and avoid U-Boot relocation/stack/malloc,
control DT, framebuffer, kernel/DTB/initrd ranges, and decompression space.
`0x88000000` is not safe merely because it is in DDR: video reserves memory
near the top and the allocation depends on the build and RAM size.

These placeholders must be replaced by the reviewed layout:

```text
pa-mini=> bdinfo
pa-mini=> dm tree
pa-mini=> setenv splashimage <reserved image-buffer start>
pa-mini=> setenv splash_max <reserved buffer size in hexadecimal bytes>
pa-mini=> setenv splashpart <identified MMC device:boot-partition>
pa-mini=> fatsize mmc ${splashpart} splash.bmp
pa-mini=> printenv filesize
```

Confirm a nonzero file size no larger than `splash_max`, then load and inspect
it. No host/other target writer may alter the file between size-check and load.

```text
pa-mini=> fatload mmc ${splashpart} ${splashimage} splash.bmp
pa-mini=> bmp info ${splashimage}
pa-mini=> bmp display ${splashimage} 0 0
```

Require actual successful commands and sensible dimensions/bit depth. A
successful display command means the software path accepted the image; the
panel observation is another checkpoint. Record both rather than copying an
invented success log. If U-Boot console output also targets video, later text
or scrolling may overwrite the splash. Retain serial as the debug console;
change display console routing only after diagnosing it explicitly.

## 24I.7  Add the splash command to the default environment

Only after the manual path works, merge this macro with the existing defaults.
It deliberately leaves buffer address/size and partition to the reviewed
board layout:

```c
#define PA_MINI_SPLASH_ENV \
    "splashfile=splash.bmp\0" \
    "show_splash=if test -n \"${splashimage}\" && " \
        "test -n \"${splash_max}\" && test -n \"${splashpart}\"; then " \
        "if fatsize mmc ${splashpart} ${splashfile}; then " \
            "if itest ${filesize} -gt 0 && itest ${filesize} -le ${splash_max}; then " \
                "if fatload mmc ${splashpart} ${splashimage} ${splashfile}; then " \
                    "bmp display ${splashimage} 0 0; " \
                "else echo Splash load failed; false; fi; " \
            "else echo Splash exceeds reserved buffer or is empty; false; fi; " \
        "else echo Splash file unavailable; false; fi; " \
    "else echo Splash buffer not configured; false; fi\0"
```

`fatsize` produces hexadecimal `filesize`; `itest` handles the numeric
comparison. The command bounds the file load, not malformed BMP header reads.
Use only the prevalidated trusted asset. Do not replace this with a truncated
load and then try to decode an incomplete file.

For Chapter 24F's policy, a reviewed normal-path wrapper is:

```text
normal_with_splash=run show_splash; run boot_selected
bootcmd=run normal_with_splash
```

Make that the single normal command definition, with matching compiled boot
command settings. Keep `altbootcmd` and Chapter 24G/H overrides intact.
Do not introduce a new `normal_boot=run mmcboot` that bypasses A/B selection
or safety. Updating defaults does not replace saved variables; reconcile them
manually without deleting unrelated settings. No `saveenv` is needed for
initial RAM-only trials.

## 24I.8  If the display is black

| Observation/check | Next evidence |
|---|---|
| Backlight dark | Approved rail/enable measurement; a flashlight may reveal faint pixels |
| File not loaded | Storage identity, `fatsize`, load status, actual asset path |
| Header implausible | Reinspect trusted host file, do not keep decoding it |
| No video device | Generated config, compatible match, control DT and probe errors |
| Lit but blank/shifted panel | Reset sequence, pinmux, signal routing, clock/porches/polarities |
| Wrong colors | Wire RGB order, framebuffer format, BMP format/conversion |
| Image changes after display | Video-console output or Linux reinitialization |
| Corruption elsewhere | Image/framebuffer/load/decompression memory overlap |

Work outward from a known observation. A lit backlight does not prove pixel
traffic, and a framebuffer in RAM does not prove electrical timing. Use only
approved probing points and instruments; never change supply voltages to
try to make the image brighter.

## 24I.9  Make the splash optional

`run show_splash; run boot_selected` intentionally ignores the first command's
failure and still attempts the recorded normal boot policy. The second
command's success/failure remains the wrapper's result. A missing logo does
not choose another slot or mark a candidate good.

For a factory image test, use a different wrapper:

```text
factory_splash=if run show_splash; then echo TEST:SPLASH:COMMAND_OK; else echo TEST:SPLASH:FAIL; false; fi
```

`COMMAND_OK` is not a panel inspection PASS. The fixture still needs optical
or electrical evidence if display output is part of acceptance. Avoid an
unconditional trailing success message that hides a failed BMP command.

## 24I.10  Production choices

| Asset location | Tradeoff |
|---|---|
| Boot-partition BMP | Easy replacement, but file validity/access must be controlled |
| Embedded asset | Fixed with the U-Boot build; requires a defined decode/display integration |
| Verified FIT/partition | Authentication can cover the asset, only if it is actually checked before decoding |

A file residing inside a signed container is not automatically verified by
`fatload` followed by `bmp display`. Keep image-size validation even when
integrity is authenticated. Optional visual feedback must not weaken the
recovery/power decision or delay watchdog service unpredictably.

## 24I.11  Lab

1. Without hardware, inspect v2026.04's MXS parser and configuration. Explain
   the difference between source BMP depth, framebuffer depth, and RGB wires.
2. Calculate file/framebuffer sizes for a chosen geometry, including row
   padding. Reject an oversized or truncated host asset.
3. With a documented fitted panel/carrier, review timing, all signal routes,
   power/reset/backlight sequence, and operation-phase guards.
4. Build the MINI port and reserve non-overlapping RAM before loading anything.
5. On approved hardware, record actual load/header results and color-bar/panel
   observations separately. No panel is assumed working by this chapter.
6. Add the optional wrapper. Missing, empty, or oversized files must fail the
   splash command while preserving the normal boot policy.
7. Test held-key recovery and a modeled power fault: neither may fall into
   the splash/normal path. Check the intentional Linux display handoff.

## 24I.12  Pitfalls

- **Backlight equals initialized panel.** They are separate paths.
- **Linux binding equals U-Boot behavior.** Read this version's actual parser.
- **Missing `BMP_24BPP`.** Generic BMP support alone is not every source format.
- **Universal timing/pad settings.** Carrier and panel determine them.
- **Loading over the framebuffer or kernel.** Reserve the complete range first.
- **Decoding an untrusted/truncated image.** Header output is not full validation.
- **A splash wrapper replacing safety policy.** Preserve A/B and both veto paths.
- **Expecting seamless Linux takeover.** Reinitialization is a separate contract.

## 24I.13  Going deeper

- [v2026.04 MXS video driver](https://github.com/u-boot/u-boot/blob/v2026.04/drivers/video/mxsfb.c)
  and [video Kconfig](https://github.com/u-boot/u-boot/blob/v2026.04/drivers/video/Kconfig).
- [BMP command](https://github.com/u-boot/u-boot/blob/v2026.04/cmd/bmp.c) and
  [video BMP conversion](https://github.com/u-boot/u-boot/blob/v2026.04/drivers/video/video_bmp.c).
- [Splash preparation](https://github.com/u-boot/u-boot/blob/v2026.04/doc/README.splashprepare)
  and [splash code](https://github.com/u-boot/u-boot/blob/v2026.04/common/splash.c),
  for the optional framework rather than this manual path.
- The fitted panel's official timing/electrical specification and the carrier
  schematic are prerequisites for a hardware exercise.

---

**Previous:** [Chapter 24H: PMIC and power policy in U-Boot](ch24H-uboot-pmic-power-policy.md)

**Next:** [Chapter 24J: SPI LCD and I2C OLED displays in U-Boot](ch24J-uboot-spi-lcd-i2c-oled.md)
