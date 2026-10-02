---
chapter: 24I
title: U-Boot display and boot screen
part: III - U-Boot, deeply
estimated_pages: 16
status: draft
---

# Chapter 24I: U-Boot display and boot screen

> **What:** add a simple boot screen to the U-Boot board port from Chapter 22. We enable U-Boot video support, load a BMP file from the boot partition, and show it before Linux starts.
>
> **Why:** many products need visible feedback before the kernel and user space are ready. A boot screen can show the product logo, a recovery message, or a factory test result.
>
> **Result:** when the board powers on, U-Boot initializes the LCD, loads `splash.bmp` from the FAT boot partition, displays it, then continues into the normal Linux boot command.
>
> **Focus:** make the display work manually first. Only then add it to `bootcmd`.

This chapter assumes the board has an LCD panel connected to the i.MX6ULL eLCDIF controller. If your Point Atom MINI setup has no LCD carrier fitted, read the chapter for the method and skip the lab.

## 24I.1  What a U-Boot boot screen really is

A boot screen is not a Linux feature. It is just a framebuffer that U-Boot fills before it jumps to the kernel.

The path is:

```text
U-Boot starts
  |
  v
U-Boot initializes the LCD controller
  |
  v
U-Boot loads a BMP image into RAM
  |
  v
U-Boot copies the BMP into the framebuffer
  |
  v
U-Boot boots Linux
```

After Linux starts, Linux owns the display. If Linux has a framebuffer or DRM driver, it will reinitialize the panel and draw its own screen later.

So there are two separate display owners:

| Time | Owner | What draws |
|------|-------|------------|
| Before kernel entry | U-Boot | The BMP splash or text console. |
| After kernel display driver loads | Linux | Kernel console, logo, compositor, or application UI. |

Do not debug the U-Boot splash by changing Linux. They are separate stages.

## 24I.2  Files changed in this chapter

| File | What changes |
|------|--------------|
| `configs/mx6ull_pa_mini_defconfig` | Enable video, BMP, FAT loading, and optional splash support. |
| `arch/arm/dts/imx6ull-pa-mini.dts` | Describe eLCDIF, the panel timing, and the LCD pins. |
| `include/configs/mx6ull_pa_mini.h` | Add `splashimage`, `splashfile`, and `show_splash` defaults. |
| FAT boot partition on SD or eMMC | Add `splash.bmp`. |

No new board is created. This is a feature added to the Chapter 22 port.

## 24I.3  Enable the display-related configs

Open `configs/mx6ull_pa_mini_defconfig` and add:

```text
CONFIG_VIDEO=y
CONFIG_VIDEO_MXS=y
CONFIG_CMD_BMP=y
CONFIG_BMP=y
CONFIG_SPLASH_SCREEN=y
CONFIG_SPLASH_SCREEN_ALIGN=y
CONFIG_CMD_CLS=y
CONFIG_FS_FAT=y
CONFIG_CMD_FAT=y
```

What each option does:

| Config | Meaning |
|--------|---------|
| `CONFIG_VIDEO` | Enables U-Boot video support. Without this, there is no framebuffer console and no place to draw a BMP. |
| `CONFIG_VIDEO_MXS` | Enables the MXS/eLCDIF-style display driver used by i.MX6UL and i.MX6ULL in many U-Boot trees. If your tree renamed the driver, search `drivers/video/Kconfig` for `MXS` or `LCDIF`. |
| `CONFIG_CMD_BMP` | Adds the `bmp` command. We use `bmp info` and `bmp display` for manual testing. |
| `CONFIG_BMP` | Enables BMP image decoding. |
| `CONFIG_SPLASH_SCREEN` | Enables U-Boot's splash-screen support. Useful for automatic display paths. |
| `CONFIG_SPLASH_SCREEN_ALIGN` | Allows centered or positioned splash images when the splash framework is used. |
| `CONFIG_CMD_CLS` | Adds the `cls` command to clear the video console. |
| `CONFIG_FS_FAT` | Enables FAT filesystem support. |
| `CONFIG_CMD_FAT` | Adds commands such as `fatload`, used to load `splash.bmp`. |

Build once after adding the configs:

```sh
$ make mx6ull_pa_mini_defconfig
$ grep -E 'VIDEO|BMP|SPLASH|CMD_FAT|FS_FAT' .config
```

If `CONFIG_VIDEO_MXS` is not accepted by your U-Boot version, do not guess. Open `drivers/video/Kconfig` and find the i.MX6ULL eLCDIF driver symbol used by your tree.

## 24I.4  Add the LCD to the U-Boot Device Tree

The exact panel timing comes from the panel datasheet, not from U-Boot.

This example uses an 800 x 480 RGB panel with a 33 MHz pixel clock. Replace the timing values if your panel is different.

Add or update the LCD node in `arch/arm/dts/imx6ull-pa-mini.dts`:

```dts
&lcdif {
    pinctrl-names = "default";
    pinctrl-0 = <&pinctrl_lcdif>;
    display = <&display0>;
    status = "okay";

    display0: display {
        bits-per-pixel = <24>;
        bus-width = <24>;

        display-timings {
            native-mode = <&timing0>;

            timing0: timing0 {
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

Then add the pin group under `&iomuxc`:

```dts
&iomuxc {
    pinctrl_lcdif: lcdifgrp {
        fsl,pins = <
            MX6UL_PAD_LCD_CLK__LCDIF_CLK        0x79
            MX6UL_PAD_LCD_ENABLE__LCDIF_ENABLE  0x79
            MX6UL_PAD_LCD_HSYNC__LCDIF_HSYNC    0x79
            MX6UL_PAD_LCD_VSYNC__LCDIF_VSYNC    0x79

            MX6UL_PAD_LCD_DATA00__LCDIF_DATA00  0x79
            MX6UL_PAD_LCD_DATA01__LCDIF_DATA01  0x79
            MX6UL_PAD_LCD_DATA02__LCDIF_DATA02  0x79
            MX6UL_PAD_LCD_DATA03__LCDIF_DATA03  0x79
            MX6UL_PAD_LCD_DATA04__LCDIF_DATA04  0x79
            MX6UL_PAD_LCD_DATA05__LCDIF_DATA05  0x79
            MX6UL_PAD_LCD_DATA06__LCDIF_DATA06  0x79
            MX6UL_PAD_LCD_DATA07__LCDIF_DATA07  0x79
            MX6UL_PAD_LCD_DATA08__LCDIF_DATA08  0x79
            MX6UL_PAD_LCD_DATA09__LCDIF_DATA09  0x79
            MX6UL_PAD_LCD_DATA10__LCDIF_DATA10  0x79
            MX6UL_PAD_LCD_DATA11__LCDIF_DATA11  0x79
            MX6UL_PAD_LCD_DATA12__LCDIF_DATA12  0x79
            MX6UL_PAD_LCD_DATA13__LCDIF_DATA13  0x79
            MX6UL_PAD_LCD_DATA14__LCDIF_DATA14  0x79
            MX6UL_PAD_LCD_DATA15__LCDIF_DATA15  0x79
            MX6UL_PAD_LCD_DATA16__LCDIF_DATA16  0x79
            MX6UL_PAD_LCD_DATA17__LCDIF_DATA17  0x79
            MX6UL_PAD_LCD_DATA18__LCDIF_DATA18  0x79
            MX6UL_PAD_LCD_DATA19__LCDIF_DATA19  0x79
            MX6UL_PAD_LCD_DATA20__LCDIF_DATA20  0x79
            MX6UL_PAD_LCD_DATA21__LCDIF_DATA21  0x79
            MX6UL_PAD_LCD_DATA22__LCDIF_DATA22  0x79
            MX6UL_PAD_LCD_DATA23__LCDIF_DATA23  0x79
        >;
    };
};
```

This only routes pins and describes timing. It does not power the backlight.

If the panel has a backlight enable GPIO, add a GPIO node and enable it in board code or in the video driver path. If the backlight is off, the framebuffer can be correct and the screen will still look black.

## 24I.5  Prepare the BMP file

Use a simple 24-bit uncompressed BMP.

For an 800 x 480 panel, create:

```text
splash.bmp
size: 800 x 480
format: 24-bit BMP
compression: none
```

Keep the first test boring. Use a solid background, large text, and a few color bars. Do not start with a complex image. A simple image makes wrong colors and wrong alignment easy to see.

Copy it to the FAT boot partition:

```sh
$ sudo mount /dev/sdX1 /mnt
$ sudo cp splash.bmp /mnt/
$ sync
$ sudo umount /mnt
```

If your boot partition is on eMMC, copy it there after booting Linux or use U-Boot's USB mass-storage command from Chapter 24.

## 24I.6  Manual U-Boot display test

Boot to the U-Boot prompt and run:

```text
pa-mini=> mmc dev 0
pa-mini=> fatls mmc 0:1
pa-mini=> setenv splashimage 0x88000000
pa-mini=> fatload mmc 0:1 ${splashimage} splash.bmp
pa-mini=> bmp info ${splashimage}
pa-mini=> bmp display ${splashimage} 0 0
```

Expected result:

- `fatload` reports bytes read.
- `bmp info` reports `800 x 480`, `24 bits`.
- The image appears at the top-left of the LCD.

If the image appears manually, U-Boot video is working.

Only after this test passes should you add the splash to `bootcmd`.

## 24I.7  Add the splash command to the default environment

In `include/configs/mx6ull_pa_mini.h`, add:

```c
#define PA_MINI_SPLASH_ENV \
    "splashimage=0x88000000\0" \
    "splashfile=splash.bmp\0" \
    "show_splash=if fatload mmc ${mmcdev}:1 ${splashimage} ${splashfile}; then " \
        "bmp display ${splashimage} 0 0; " \
    "fi\0"
```

Then make your default boot command run it before normal boot:

```c
#define CFG_EXTRA_ENV_SETTINGS \
    PA_MINI_SPLASH_ENV \
    "mmcdev=0\0" \
    "normal_boot=run mmcboot\0" \
    "bootcmd=run show_splash; run normal_boot\0"
```

The `bootcmd` line contains semicolons because U-Boot command strings need separators. That is normal inside shell-like command text.

## 24I.8  If the display is black

A black display does not always mean the LCD driver failed.

Check in this order:

| Check | How to test |
|-------|-------------|
| Backlight power | Shine a flashlight at the panel. If the image is faintly visible, only the backlight is off. |
| BMP loaded | `fatload` must report bytes read. |
| BMP format | `bmp info ${splashimage}` must print sane width, height, and bit depth. |
| Video device exists | Run `dm tree` and look for the video device. |
| LCD pins | Recheck the `pinctrl_lcdif` pad list against the schematic. |
| Panel timing | Recheck pixel clock, porches, sync polarity, and active size against the panel datasheet. |
| Framebuffer address | Use a safe DDR address. Do not overlap U-Boot, the malloc area, kernel load address, or DTB load address. |

For this chapter we use `0x88000000` as the image load address because it is in DDR and away from the common kernel and DTB load addresses used earlier.

## 24I.9  Make the splash optional

During development, a broken splash should not stop boot.

The command above is intentionally written like this:

```text
if fatload ...; then bmp display ...; fi
```

If the file is missing, `fatload` fails and the board still continues to `normal_boot`.

That is usually the right behavior for a logo. A missing logo is not a reason to brick the device.

For factory test, you may want the opposite:

```text
show_splash=fatload mmc ${mmcdev}:1 ${splashimage} ${splashfile} && bmp display ${splashimage} 0 0
```

Now a missing image makes `show_splash` fail. Use this only when the boot screen is part of a test result.

## 24I.10  Production choices

There are three common ways to store the boot screen.

| Choice | Pros | Cons |
|--------|------|------|
| `splash.bmp` on FAT boot partition | Easy to change without rebuilding U-Boot. Good for products with field branding. | Anyone who can edit the boot partition can change it. |
| BMP embedded in U-Boot | Cannot disappear from the boot partition. Good for fixed branding. | Requires rebuilding U-Boot to change the image. |
| BMP in a signed FIT or verified partition | Can be authenticated. Good for secure products. | More setup. Save this for the secure boot chapters. |

For this book, use the FAT file first. It is visible, simple, and easy to debug.

## 24I.11  Lab

1. Enable the video and BMP config options.
2. Add or verify the LCD node in the U-Boot Device Tree.
3. Build U-Boot and confirm a video device appears in `dm tree`.
4. Copy a simple 24-bit `splash.bmp` to the FAT boot partition.
5. Load and display it manually with `fatload`, `bmp info`, and `bmp display`.
6. Add `show_splash` to the default environment.
7. Reboot and confirm the screen appears before Linux starts.

## 24I.12  Pitfalls

- **Trying to use PNG or JPEG.** Use BMP for the first boot screen. U-Boot BMP support is simple and predictable.
- **Using a compressed BMP.** Start with uncompressed 24-bit BMP.
- **Wrong panel timing.** The panel may stay white, black, shifted, or rolling.
- **Backlight not enabled.** The framebuffer can be correct while the user sees nothing.
- **Loading over the framebuffer.** Do not load the BMP on top of U-Boot or the framebuffer.
- **Expecting Linux to keep the image.** Linux usually reinitializes the display. That is normal.
- **Adding splash to `bootcmd` before manual testing.** This hides the real error. Prove the pieces one by one.

## 24I.13  Going deeper

- `drivers/video/`, for U-Boot video drivers.
- `cmd/bmp.c`, for the `bmp info` and `bmp display` commands.
- `common/splash.c`, for the automatic splash-screen flow.
- `doc/README.splashprepare`, in older U-Boot trees, for the board hook used by the splash framework.
- Linux `drivers/gpu/drm/mxsfb/` or `drivers/video/fbdev/mxsfb.c`, for the kernel-side eLCDIF driver.

---

**Previous:** [Chapter 24H: PMIC and power policy in U-Boot](ch24H-uboot-pmic-power-policy.md)

**Next:** [Chapter 24J: SPI LCD and I2C OLED displays in U-Boot](ch24J-uboot-spi-lcd-i2c-oled.md)
