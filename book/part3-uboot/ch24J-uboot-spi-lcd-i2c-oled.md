---
chapter: 24J
title: SPI LCD and I2C OLED displays in U-Boot
part: III - U-Boot, deeply
estimated_pages: 14
status: draft
---

# Chapter 24J: SPI LCD and I2C OLED displays in U-Boot

> **What:** bring up small displays that are not connected to the i.MX6ULL eLCDIF RGB controller: SPI LCD modules such as ST7789, ST7735, or ILI9341, and I2C OLED modules such as SSD1306.
>
> **Why:** many products do not have a full RGB LCD. They have a small status screen: booting, recovery mode, update progress, error code, or factory-test result.
>
> **Result:** you know which U-Boot path to use: full video/framebuffer support for SPI LCDs when a driver exists, or a tiny board-specific status command for simple OLEDs.
>
> **Focus:** do not treat every display as the same thing. A 24-bit RGB panel, an SPI LCD, and a monochrome I2C OLED have different software shapes.

Chapter 24I used the i.MX6ULL eLCDIF controller. That is the "big display" path: U-Boot owns a framebuffer, draws a BMP, then Linux takes over.

This chapter covers small displays connected through serial buses.

## 24J.1  First decision: what kind of display is it?

| Display type | Example controller | Bus | Typical resolution | U-Boot approach |
|--------------|--------------------|-----|--------------------|-----------------|
| RGB LCD panel | Parallel RGB panel | eLCDIF | 480x272, 800x480 | Use U-Boot video framebuffer, as in Chapter 24I. |
| SPI color LCD | ST7735, ST7789, ILI9341 | SPI plus GPIOs | 128x160, 240x240, 320x240 | Use U-Boot video if supported. Otherwise write a tiny init/fill/status driver. |
| I2C monochrome OLED | SSD1306, SH1106 | I2C | 128x32, 128x64 | Usually write a small status driver or command. Do not use BMP splash first. |
| Smart display module | Nextion, UART LCD | UART | Varies | Send text or commands over UART. This is product-specific. |

The main question is:

```text
Do I need a real framebuffer before Linux starts?
```

If yes, use U-Boot's video model.

If no, use a small board-specific status path. For boot messages such as "RECOVERY", "UPDATING", "BOOT FAIL", a small custom command is simpler and more reliable.

## 24J.2  What belongs in U-Boot?

Good U-Boot display jobs:

- Show "booting" or "recovery mode".
- Show update progress while U-Boot writes flash.
- Show a factory-test pass/fail code.
- Show a clear reason before refusing to boot.

Bad U-Boot display jobs:

- Full UI.
- Menus with animations.
- Long localization strings.
- Touch-screen application logic.
- Anything that belongs to Linux user space.

U-Boot should communicate early state. Linux should run the product UI.

## 24J.3  SPI LCD hardware checklist

An SPI LCD is usually not "just SPI". It normally needs extra GPIOs:

| Signal | Meaning |
|--------|---------|
| `SCLK` | SPI clock. |
| `MOSI` | Pixel and command data from SoC to display. |
| `MISO` | Often unused. Some displays do not connect it. |
| `CS` | Chip select. |
| `D/C` or `A0` | Data/command select. Low usually means command, high usually means data. |
| `RESET` | Panel reset line. |
| `BL` | Backlight enable or PWM. |
| `VCC`, `IOVCC` | Power rails. Check voltage carefully. |

The important beginner mistake: SPI only transfers bytes. The LCD still needs controller-specific commands:

```text
reset panel
exit sleep mode
set pixel format
set memory access direction
set column range
set row range
write pixel data
turn display on
enable backlight
```

The command names are in the LCD controller datasheet, not in the i.MX6ULL reference manual.

## 24J.4  SPI LCD: Device Tree shape

The exact compatible string depends on the driver you use. This is the shape:

```dts
&ecspi1 {
    pinctrl-names = "default";
    pinctrl-0 = <&pinctrl_ecspi1>;
    cs-gpios = <&gpio4 26 GPIO_ACTIVE_LOW>;
    status = "okay";

    lcd@0 {
        compatible = "sitronix,st7789v";
        reg = <0>;
        spi-max-frequency = <32000000>;

        dc-gpios = <&gpio1 2 GPIO_ACTIVE_HIGH>;
        reset-gpios = <&gpio1 3 GPIO_ACTIVE_LOW>;
        backlight = <&lcd_backlight>;

        width = <240>;
        height = <240>;
        rotation = <0>;
    };
};

lcd_backlight: backlight {
    compatible = "gpio-backlight";
    gpios = <&gpio1 4 GPIO_ACTIVE_HIGH>;
    default-on;
};
```

Also add the pin group:

```dts
&iomuxc {
    pinctrl_ecspi1: ecspi1grp {
        fsl,pins = <
            MX6UL_PAD_CSI_DATA04__ECSPI1_SCLK  0x10b0
            MX6UL_PAD_CSI_DATA06__ECSPI1_MOSI  0x10b0
            MX6UL_PAD_CSI_DATA07__ECSPI1_MISO  0x10b0
            MX6UL_PAD_CSI_DATA05__GPIO4_IO26   0x10b0
        >;
    };
};
```

Check the actual pins on your schematic. Do not copy this pin group blindly.

## 24J.5  SPI LCD: useful configs

Start with the bus and test commands:

```text
CONFIG_DM_SPI=y
CONFIG_SPI=y
CONFIG_MXC_SPI=y
CONFIG_CMD_SPI=y
CONFIG_DM_GPIO=y
```

If your U-Boot tree has a matching video driver for the panel, also enable the video path:

```text
CONFIG_VIDEO=y
CONFIG_DM_VIDEO=y
CONFIG_CMD_BMP=y
CONFIG_BMP=y
CONFIG_FS_FAT=y
CONFIG_CMD_FAT=y
```

If there is no matching panel driver, do not force the BMP splash path yet. First write the smallest status routine that can:

1. Reset the panel.
2. Send the init command list.
3. Fill the screen with one color.
4. Draw one simple status shape or message.

Only after that works should you decide whether to turn it into a real U-Boot video driver.

## 24J.6  SPI LCD manual bring-up order

Bring the display up in this order:

1. Confirm the display has power.
2. Confirm reset and backlight GPIOs work.
3. Confirm `ecspi1` appears in `dm tree`.
4. Confirm the chip select toggles with an SPI transfer.
5. Send the panel reset sequence.
6. Send the init commands from the panel datasheet.
7. Fill the whole display red, green, blue, then black.
8. Only then try text, logos, or BMP files.

If the screen stays white, the backlight may be on but the controller is not initialized.

If the screen stays black, the backlight may be off, reset may be asserted, or the panel may have no power.

If colors are wrong, check RGB/BGR order and 16-bit pixel endianness.

## 24J.7  I2C OLED: why it feels different

An SSD1306-style OLED is not a framebuffer in the same sense as the RGB LCD from Chapter 24I.

Typical SSD1306 facts:

| Item | Meaning |
|------|---------|
| Bus | I2C, usually address `0x3c` or `0x3d`. |
| Color | Monochrome. One bit per pixel. |
| Memory layout | Pages. One byte often controls 8 vertical pixels. |
| Backlight | None. OLED pixels emit light directly. |
| Useful U-Boot role | Status text, progress bars, error codes. |

For a beginner, the I2C OLED path should be:

```text
probe I2C address
send SSD1306 init commands
clear screen
draw minimal status
boot Linux
```

Do not start with fonts, logos, or bitmap conversion. Prove the display with `clear` and a filled rectangle first.

## 24J.8  I2C OLED Device Tree shape

Linux may use a compatible like this:

```dts
&i2c1 {
    status = "okay";

    oled@3c {
        compatible = "solomon,ssd1306fb-i2c";
        reg = <0x3c>;
        solomon,width = <128>;
        solomon,height = <64>;
        solomon,page-offset = <0>;
    };
};
```

U-Boot may or may not have a driver that binds to this node. That is fine.

For early boot status, it is acceptable to use a small board command that talks directly to bus 0, address `0x3c`, while Linux uses the proper Device Tree node later.

## 24J.9  I2C OLED configs

Enable I2C and the command-line tools:

```text
CONFIG_DM_I2C=y
CONFIG_SYS_I2C_MXC=y
CONFIG_CMD_I2C=y
CONFIG_DM_GPIO=y
CONFIG_BOARD_LATE_INIT=y
```

Then test from the U-Boot prompt:

```text
=> i2c bus
=> i2c dev 0
=> i2c probe
```

You should see the OLED address, usually `3c`:

```text
Valid chip addresses: 3C
```

If nothing appears:

- Check pull-up resistors on SDA and SCL.
- Check the bus number. U-Boot bus numbering may not match the schematic name.
- Check the OLED module voltage.
- Check whether the board holds the OLED reset pin low.

## 24J.10  A tiny SSD1306 U-Boot command

This is the small, honest version. It does not pretend the OLED is a full graphics subsystem. It gives you a reliable early status path.

Create `board/myorg/mx6ull_pa_mini/oled_ssd1306.c`:

```c
// SPDX-License-Identifier: GPL-2.0+
#include <command.h>
#include <dm.h>
#include <i2c.h>
#include <linux/kernel.h>
#include <linux/delay.h>
#include <linux/string.h>

#define OLED_BUS        0
#define OLED_ADDR       0x3c
#define OLED_WIDTH      128
#define OLED_PAGES      8       /* 64 pixels high / 8 pixels per page */

static int oled_get(struct udevice **devp)
{
    return i2c_get_chip_for_busnum(OLED_BUS, OLED_ADDR, 0, devp);
}

static int oled_write(struct udevice *dev, u8 control, const u8 *data, int len)
{
    u8 buf[17];
    int pos = 0;
    int ret;

    while (pos < len) {
        int chunk = len - pos;

        if (chunk > 16)
            chunk = 16;

        buf[0] = control;
        memcpy(&buf[1], &data[pos], chunk);

        ret = dm_i2c_write(dev, 0, buf, chunk + 1);
        if (ret)
            return ret;

        pos += chunk;
    }

    return 0;
}

static int oled_cmd(struct udevice *dev, u8 cmd)
{
    return oled_write(dev, 0x00, &cmd, 1);
}

static int oled_data(struct udevice *dev, const u8 *data, int len)
{
    return oled_write(dev, 0x40, data, len);
}

static int oled_init(struct udevice *dev)
{
    static const u8 init[] = {
        0xae,       /* display off */
        0xd5, 0x80, /* clock */
        0xa8, 0x3f, /* multiplex: 64 rows */
        0xd3, 0x00, /* display offset */
        0x40,       /* start line */
        0x8d, 0x14, /* charge pump on */
        0x20, 0x00, /* horizontal addressing */
        0xa1,       /* segment remap */
        0xc8,       /* COM scan direction */
        0xda, 0x12, /* COM pins */
        0x81, 0xcf, /* contrast */
        0xd9, 0xf1, /* pre-charge */
        0xdb, 0x40, /* VCOMH */
        0xa4,       /* resume RAM display */
        0xa6,       /* normal display */
        0xaf,       /* display on */
    };
    int i;
    int ret;

    for (i = 0; i < ARRAY_SIZE(init); i++) {
        ret = oled_cmd(dev, init[i]);
        if (ret)
            return ret;
    }

    return 0;
}

static int oled_clear(struct udevice *dev)
{
    u8 zeros[OLED_WIDTH];
    int page;
    int ret;

    memset(zeros, 0, sizeof(zeros));

    for (page = 0; page < OLED_PAGES; page++) {
        ret = oled_cmd(dev, 0xb0 + page);
        if (ret)
            return ret;
        ret = oled_cmd(dev, 0x00);
        if (ret)
            return ret;
        ret = oled_cmd(dev, 0x10);
        if (ret)
            return ret;
        ret = oled_data(dev, zeros, sizeof(zeros));
        if (ret)
            return ret;
    }

    return 0;
}

static int oled_bar(struct udevice *dev)
{
    u8 data[OLED_WIDTH];
    int page;
    int ret;

    for (page = 0; page < OLED_PAGES; page++) {
        memset(data, page < 2 ? 0xff : 0x00, sizeof(data));

        ret = oled_cmd(dev, 0xb0 + page);
        if (ret)
            return ret;
        ret = oled_cmd(dev, 0x00);
        if (ret)
            return ret;
        ret = oled_cmd(dev, 0x10);
        if (ret)
            return ret;
        ret = oled_data(dev, data, sizeof(data));
        if (ret)
            return ret;
    }

    return 0;
}

static int do_oled(struct cmd_tbl *cmdtp, int flag, int argc, char *const argv[])
{
    struct udevice *dev;
    int ret;

    ret = oled_get(&dev);
    if (ret) {
        printf("OLED: not found on I2C bus %d addr 0x%02x, ret=%d\n",
               OLED_BUS, OLED_ADDR, ret);
        return CMD_RET_FAILURE;
    }

    ret = oled_init(dev);
    if (ret) {
        printf("OLED: init failed, ret=%d\n", ret);
        return CMD_RET_FAILURE;
    }

    if (argc > 1 && !strcmp(argv[1], "bar"))
        ret = oled_bar(dev);
    else
        ret = oled_clear(dev);

    if (ret) {
        printf("OLED: draw failed, ret=%d\n", ret);
        return CMD_RET_FAILURE;
    }

    return CMD_RET_SUCCESS;
}

U_BOOT_CMD(
    oled, 2, 1, do_oled,
    "control SSD1306 OLED",
    "clear - initialize and clear the display\n"
    "oled bar   - draw a simple status bar"
);
```

Add it to the board `Makefile`:

```make
obj-y += oled_ssd1306.o
```

Build, boot, and test:

```text
=> i2c dev 0
=> i2c probe
=> oled clear
=> oled bar
```

This gives you a working path before you write a font renderer.

## 24J.11  Showing status automatically

Once manual testing works, call the OLED command from the environment:

```text
setenv show_oled 'oled bar'
setenv bootcmd 'run show_oled; run distro_bootcmd'
saveenv
```

Or call the OLED helper from `board_late_init()` only for special states:

| State | Display action |
|-------|----------------|
| Normal boot | Optional: clear or show one short boot mark. |
| Recovery key held | Show recovery symbol or status bar. |
| Power unsafe | Show a power error before stopping. |
| Factory test | Show pass/fail result. |
| Boot rollback | Show which slot is being tried. |

Do not print long logs on the OLED. Serial is still the debug console.

## 24J.12  Which path should you choose?

| Requirement | Best path |
|-------------|-----------|
| Full logo before Linux | Use U-Boot video and BMP, if the panel has a proper video driver. |
| Small SPI LCD with no U-Boot driver | Start with a tiny init/fill driver. Convert to U-Boot video only if needed. |
| I2C OLED status text | Board-specific OLED command or small driver. |
| Same display also used by Linux | Describe it in Linux Device Tree too. Let Linux own it after boot. |
| Secure boot/update status | Keep the display code tiny and deterministic. |

For most small OLEDs, the right first implementation is not "port the whole graphics stack". It is:

```text
probe bus
init display
draw simple status
boot Linux
```

## 24J.13  Pitfalls

- **Calling an OLED an LCD.** OLED and LCD panels are different hardware. Say "OLED" when it is OLED.
- **Forgetting the D/C GPIO on SPI LCDs.** Without it, commands and pixel data are indistinguishable.
- **Backlight confused with panel init.** A white screen often means backlight is on but the controller is not configured.
- **Wrong I2C address.** Many SSD1306 modules can be `0x3c` or `0x3d`.
- **No I2C pull-ups.** I2C needs pull-ups. The SoC cannot fix missing board resistors in software.
- **Using Linux driver names as proof U-Boot supports it.** Linux and U-Boot have separate driver sets.
- **Putting too much UI in U-Boot.** U-Boot should show state, not run the product interface.

## 24J.14  Lab

1. Pick one small display: SPI LCD or I2C OLED.
2. Identify the controller chip from the module marking or schematic.
3. Add the bus pins and display node to the Device Tree.
4. Enable the bus configs and confirm the device appears from the U-Boot prompt.
5. For SPI LCD: reset the panel and fill the display with one color.
6. For I2C OLED: run `oled clear`, then `oled bar`.
7. Add one boot-state hook: recovery mode, rollback mode, or power-fault mode.
8. Confirm Linux still owns the display after it boots.

## 24J.15  Going deeper

- U-Boot `drivers/video/`, for framebuffer-style display drivers.
- U-Boot `drivers/spi/`, for SPI controller drivers.
- U-Boot `drivers/i2c/`, for I2C controller drivers.
- Linux `drivers/gpu/drm/tiny/`, for many small SPI and I2C display drivers.
- The controller datasheet: SSD1306, SH1106, ST7735, ST7789, ILI9341.

---

**End of Part III.**

You can build and port U-Boot, understand the SPL and full-U-Boot flow, boot Linux in several ways, apply common product policies before Linux starts, and handle both full-size and small status displays.

**Previous:** [Chapter 24I: U-Boot display and boot screen](ch24I-uboot-display-splash.md)

**Next:** [Chapter 25: Building mainline Linux for i.MX6ULL](../part4-kernel/ch25-building-mainline-linux.md)
