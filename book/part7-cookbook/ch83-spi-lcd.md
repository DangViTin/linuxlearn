---
chapter: 83
title: SPI LCD (ST7789 / ILI9341)
part: VII — Device cookbook
estimated_pages: 22
status: draft
---

# Chapter 83 — SPI LCD
**PWM** - Pulse-Width Modulation, a timer output whose duty cycle controls average power or encodes timing.
MCU bridge: Think of Linux PWM like an MCU timer output channel, except the driver exposes period, duty cycle, polarity, and enable state through a subsystem.

> **What:** "smart" TFT panels with an embedded controller and frame buffer, driven over SPI. Two controllers compared: **Sitronix ST7789** (240×240 / 240×320), **Ilitek ILI9341** (240×320). Unlike the dumb parallel panels in Ch 82, these have their own RAM. You send an init sequence and pixel data over SPI. The controller refreshes the glass on its own. We cover the MIPI-DBI command model, the DRM **tiny** driver framework (`mipi-dbi`), and a from-scratch DRM tiny driver for ST7789.
>
> **Why:** SPI LCDs are cheap and small. They need 4–5 wires versus 28 for parallel, and they appear in smartwatches, thermostats, handheld instruments, and hobby gadgets. The trade-off is bandwidth. A 240×240 16-bit frame is 115 KB. At 40 MHz SPI that takes ~23 ms — about 40 fps for a full refresh. For static or partial-update UIs, that is plenty.
>
> **Focus:** the MIPI-DBI command/data model and partial updates. The controller speaks a standardized command set (MIPI Display Bus Interface): `0x2A` set column range, `0x2B` set row range, `0x2C` write pixels. A D/C (data/command) GPIO distinguishes command bytes from data bytes. Send only the changed rectangle. That keeps refresh fast enough.
> MCU bridge: Think of Linux GPIO like the same pin set/reset block you used on STM32, but accessed through a kernel subsystem that owns numbering, direction, interrupts, and user-space exposure.
> **GPIO** - General-Purpose Input/Output, a pin controlled as a digital input, output, or interrupt source.


## 83.1  Controller comparison

| | Sitronix ST7789 | Ilitek ILI9341 | Sitronix ST7735 |
|---|---|---|---|
| Resolution | 240×240 / 240×320 | 240×320 | 128×160 |
| Color | 16/18-bit (RGB565/666) | 16/18-bit | 16-bit |
| Interface | SPI (3/4-wire), parallel | SPI, parallel | SPI |
| Frame buffer | yes (internal GRAM) | yes | yes |
| Max SPI clock | ~62 MHz | ~10 MHz (read), ~62 MHz (write) | ~15 MHz |
| Command set | MIPI-DBI-ish | MIPI-DBI-ish | MIPI-DBI-ish |
| Volume price | $3–6 | $4–8 | $2–4 |
| Mainline driver | `drm/tiny/st7789v` (via panel-mipi-dbi) | `drm/tiny/ili9341.c` | `drm/tiny/st7735r.c` |

**Pick guide:**
- **ST7789**: modern default. common on 1.3"–2" round and square modules.
- **ILI9341**: classic 2.4"–2.8" modules. slightly slower SPI.
- **ST7735**: tiny 0.96"–1.8" displays.

## 83.2  The MIPI-DBI command model

These controllers descend from the MIPI **DBI** (Display Bus Interface) Type C spec. Communication is command + parameters + pixel data, with a **D/C** (Data/Command) GPIO selecting which:

```
   D/C = 0 → the byte is a COMMAND
   D/C = 1 → the byte is DATA (command parameter or pixel)
```

Wiring:

```
   i.MX6ULL              ST7789
   ─────────             ──────
   SPI MOSI  ──────────► SDA (data in)
   SPI SCLK  ──────────► SCL
   SPI CS    ──────────► CS
   GPIO      ──────────► DC (data/command select)
   GPIO      ──────────► RESET (active-low)
   GPIO/PWM  ──────────► BLK (backlight)
   3.3V ───────────────► VCC
   GND  ───────────────► GND
```

A 3-wire mode also exists. The D/C bit becomes a 9th bit per byte, so there is no DC pin. Most SPI controllers cannot generate the 9-bit frame, so 4-wire (a separate DC GPIO) is the standard.

### Key commands

| Command | Hex | Parameters | Purpose |
|---------|-----|-----------|---------|
| SWRESET | 0x01 | none | Software reset |
| SLPOUT | 0x11 | none | Sleep out (wake) |
| COLMOD | 0x3A | 1 byte | Pixel format (0x55 = RGB565, 0x66 = RGB666) |
| MADCTL | 0x36 | 1 byte | Memory access control (rotation, RGB/BGR order) |
| CASET | 0x2A | 4 bytes | Column address range (x_start, x_end) |
| RASET | 0x2B | 4 bytes | Row address range (y_start, y_end) |
| RAMWR | 0x2C | pixel data | Write pixels into the addressed window |
| DISPON | 0x29 | none | Display on |
| INVON | 0x21 | none | Invert (many ST7789 modules need this) |

### Drawing a pixel rectangle

```
1. CASET (0x2A) with x_start, x_end          (D/C=0 for cmd, D/C=1 for the 4 param bytes)
2. RASET (0x2B) with y_start, y_end
3. RAMWR (0x2C)                                (D/C=0)
4. stream (x_end-x_start+1) × (y_end-y_start+1) pixels  (D/C=1)
   each pixel = 2 bytes (RGB565: RRRRRGGG GGGBBBBB)
```

The controller auto-increments its internal address pointer as you stream pixels, wrapping within the window. So a full-screen update is: set window to (0,0)-(239,239), RAMWR, stream 57600 pixels.

## 83.3  The DRM "tiny" framework

For these small SPI displays, DRM has a dedicated lightweight subsystem: `drivers/gpu/drm/tiny/`. It provides `mipi_dbi` — a helper library that implements the CASET/RASET/RAMWR dance, dirty-rectangle tracking, and the DRM plumbing (CRTC, connector, framebuffer). A tiny driver only needs to provide the chip's init sequence.

```
drivers/gpu/drm/tiny/
├── mi0283qt.c     (ILI9341-based)
├── ili9341.c
├── ili9486.c
├── st7586.c
├── st7735r.c
├── st7789v.c       (via panel-mipi-dbi)
├── repaper.c       (e-paper — Ch 85)
└── ...
drivers/gpu/drm/drm_mipi_dbi.c    ← the shared mipi_dbi helper
```

The `mipi_dbi` helper exposes:

- `mipi_dbi_spi_init()` — set up the SPI + DC-GPIO transport.
- `mipi_dbi_command(dbi, cmd, params...)` — send a command + parameters.
- `mipi_dbi_buf_copy()` + the `fb_dirty` callback — the partial-update path that sends only changed pixels.
- `mipi_dbi_dev_init()` — register the DRM device with a given mode.

## 83.4  Writing an ST7789 DRM tiny driver from scratch

Goal: a working DRM driver exposing `/dev/fb0` (via DRM fbdev emulation) for a 240×240 ST7789. ~200 lines, leveraging the `mipi_dbi` helper for the heavy lifting.

`myst7789.c`:

```c
#include <linux/module.h>
#include <linux/spi/spi.h>
#include <linux/gpio/consumer.h>
#include <linux/delay.h>
#include <linux/property.h>

#include <drm/drm_atomic_helper.h>
#include <drm/drm_drv.h>
#include <drm/drm_fbdev_generic.h>
#include <drm/drm_gem_atomic_helper.h>
#include <drm/drm_gem_dma_helper.h>
#include <drm/drm_managed.h>
#include <drm/drm_mipi_dbi.h>
#include <drm/drm_modeset_helper.h>

/* The display's native timing — for an SPI display, the "mode" is just
 * the pixel dimensions; there are no porches (the controller self-refreshes). */
static const struct drm_display_mode myst7789_mode = {
    DRM_SIMPLE_MODE(240, 240, 28, 28),    /* 240×240, ~28×28 mm */
};

/* The init + pipe-enable callback: runs once when the display is turned on */
static void myst7789_pipe_enable(struct drm_simple_display_pipe *pipe,
                                 struct drm_crtc_state *crtc_state,
                                 struct drm_plane_state *plane_state)
{
    struct mipi_dbi_dev *dbidev = drm_to_mipi_dbi_dev(pipe->crtc.dev);
    struct mipi_dbi *dbi = &dbidev->dbi;
    int ret, idx;

    if (!drm_dev_enter(pipe->crtc.dev, &idx))
        return;

    /* Hardware reset via the reset GPIO (mipi_dbi handles it) */
    mipi_dbi_hw_reset(dbi);

    /* --- The ST7789 init sequence (from the datasheet / module vendor) --- */
    mipi_dbi_command(dbi, MIPI_DCS_SOFT_RESET);
    msleep(150);
    mipi_dbi_command(dbi, MIPI_DCS_EXIT_SLEEP_MODE);
    msleep(10);

    /* COLMOD = RGB565 (16-bit) */
    mipi_dbi_command(dbi, MIPI_DCS_SET_PIXEL_FORMAT, 0x55);

    /* MADCTL: orientation + BGR/RGB order */
    mipi_dbi_command(dbi, MIPI_DCS_SET_ADDRESS_MODE, 0x00);

    /* Porch, gate, voltage control — module-specific magic from the datasheet */
    mipi_dbi_command(dbi, 0xB2, 0x0C, 0x0C, 0x00, 0x33, 0x33);  /* PORCTRL */
    mipi_dbi_command(dbi, 0xB7, 0x35);                           /* GCTRL */
    mipi_dbi_command(dbi, 0xBB, 0x19);                           /* VCOMS */
    mipi_dbi_command(dbi, 0xC0, 0x2C);                           /* LCMCTRL */
    mipi_dbi_command(dbi, 0xC2, 0x01);                           /* VDVVRHEN */
    mipi_dbi_command(dbi, 0xC3, 0x12);                           /* VRHS */
    mipi_dbi_command(dbi, 0xC4, 0x20);                           /* VDVS */
    mipi_dbi_command(dbi, 0xC6, 0x0F);                           /* FRCTRL2 */
    mipi_dbi_command(dbi, 0xD0, 0xA4, 0xA1);                     /* PWCTRL1 */

    /* Most cheap ST7789 modules need display inversion ON */
    mipi_dbi_command(dbi, MIPI_DCS_ENTER_INVERT_MODE);

    mipi_dbi_command(dbi, MIPI_DCS_SET_DISPLAY_ON);
    msleep(50);

    /* mipi_dbi's helper flushes the framebuffer to the panel */
    mipi_dbi_enable_flush(dbidev, crtc_state, plane_state);

    drm_dev_exit(idx);
}

static const struct drm_simple_display_pipe_funcs myst7789_pipe_funcs = {
    .enable    = myst7789_pipe_enable,
    .disable   = mipi_dbi_pipe_disable,
    .update    = mipi_dbi_pipe_update,
};

DEFINE_DRM_GEM_DMA_FOPS(myst7789_fops);

static struct drm_driver myst7789_driver = {
    .driver_features    = DRIVER_GEM | DRIVER_MODESET | DRIVER_ATOMIC,
    .fops               = &myst7789_fops,
    DRM_GEM_DMA_DRIVER_OPS_VMAP,
    .name               = "myst7789",
    .desc               = "ST7789 SPI panel (linuxlearn)",
    .date               = "20260101",
    .major              = 1,
    .minor              = 0,
};

static int myst7789_probe(struct spi_device *spi)
{
    struct device *dev = &spi->dev;
    struct mipi_dbi_dev *dbidev;
    struct drm_device *drm;
    struct mipi_dbi *dbi;
    struct gpio_desc *dc;
    int ret;

    dbidev = devm_drm_dev_alloc(dev, &myst7789_driver,
                                struct mipi_dbi_dev, drm);
    if (IS_ERR(dbidev))
        return PTR_ERR(dbidev);

    dbi = &dbidev->dbi;
    drm = &dbidev->drm;

    /* D/C GPIO (data/command select) */
    dc = devm_gpiod_get(dev, "dc", GPIOD_OUT_LOW);
    if (IS_ERR(dc))
        return dev_err_probe(dev, PTR_ERR(dc), "no dc gpio\n");

    /* Reset GPIO */
    dbi->reset = devm_gpiod_get(dev, "reset", GPIOD_OUT_HIGH);
    if (IS_ERR(dbi->reset))
        return dev_err_probe(dev, PTR_ERR(dbi->reset), "no reset gpio\n");

    /* Backlight (optional) */
    dbidev->backlight = devm_of_find_backlight(dev);
    if (IS_ERR(dbidev->backlight))
        return PTR_ERR(dbidev->backlight);

    /* Initialize the SPI + DC transport */
    ret = mipi_dbi_spi_init(spi, dbi, dc);
    if (ret)
        return ret;

    /* Register the DRM device with our mode + pipe funcs */
    ret = mipi_dbi_dev_init(dbidev, &myst7789_pipe_funcs, &myst7789_mode, 0);
    if (ret)
        return ret;

    drm_mode_config_reset(drm);

    ret = drm_dev_register(drm, 0);
    if (ret)
        return ret;

    /* Enable fbdev emulation so /dev/fb0 appears */
    drm_fbdev_generic_setup(drm, 16);     /* 16 bpp */

    spi_set_drvdata(spi, drm);
    return 0;
}

static void myst7789_remove(struct spi_device *spi)
{
    struct drm_device *drm = spi_get_drvdata(spi);
    drm_dev_unplug(drm);
    drm_atomic_helper_shutdown(drm);
}

static const struct of_device_id myst7789_of_match[] = {
    { .compatible = "linuxlearn,myst7789" },
    { }
};
MODULE_DEVICE_TABLE(of, myst7789_of_match);

static const struct spi_device_id myst7789_spi_id[] = {
    { "myst7789", 0 },
    { }
};
MODULE_DEVICE_TABLE(spi, myst7789_spi_id);

static struct spi_driver myst7789_spi_driver = {
    .driver = {
        .name = "myst7789",
        .of_match_table = myst7789_of_match,
    },
    .id_table = myst7789_spi_id,
    .probe = myst7789_probe,
    .remove = myst7789_remove,
};
module_spi_driver(myst7789_spi_driver);

MODULE_LICENSE("GPL");
```

DT:

```dts
&ecspi3 {
    display@0 {
        compatible = "linuxlearn,myst7789";
        reg = <0>;
        spi-max-frequency = <40000000>;
        dc-gpios = <&gpio4 14 GPIO_ACTIVE_HIGH>;
        reset-gpios = <&gpio4 15 GPIO_ACTIVE_LOW>;
        backlight = <&backlight_lcd>;
        rotation = <0>;
    };
};
```

Build (needs the kernel's DRM headers — build against your kernel tree). Load:

```
[root@pa-mini:~]# insmod myst7789.ko
[root@pa-mini:~]# dmesg | grep -i myst7789
[drm] Initialized myst7789 1.0.0 for spi3.0 on minor 0
[root@pa-mini:~]# ls /dev/fb0
/dev/fb0
[root@pa-mini:~]# cat /sys/class/graphics/fb0/virtual_size
240,240

[root@pa-mini:~]# cat /dev/urandom > /dev/fb0      # noise on the LCD
[root@pa-mini:~]# # The mipi_dbi helper auto-flushes dirty regions to the panel
```

What the `mipi_dbi` helper did for us:
- Tracked dirty rectangles (only changed regions sent over SPI).
- Did the CASET/RASET/RAMWR command sequence per flush.
- Converted the XRGB8888 DRM framebuffer to RGB565 on the fly.
- Provided the DRM CRTC/connector/plane plumbing.
- Provided `/dev/fb0` fbdev emulation.

We provided two things: the chip-specific init sequence and the pixel dimensions. About 200 lines, mostly the init sequence.

For production: handle rotation through MADCTL. Add sleep on disable for power management. Better still, switch to the mainline `panel-mipi-dbi` generic driver and skip the custom code entirely.

## 83.5  The even-easier way: panel-mipi-dbi

Mainline has a *generic* DRM tiny driver, `drivers/gpu/drm/tiny/panel-mipi-dbi.c`, that reads the init sequence from a **firmware blob** rather than hardcoded C. You write the init sequence in a text file, compile it with a tool, and the generic driver runs it. No C code at all.

DT:

```dts
&ecspi3 {
    display@0 {
        compatible = "sitronix,st7789v", "panel-mipi-dbi-spi";
        reg = <0>;
        spi-max-frequency = <40000000>;
        dc-gpios = <&gpio4 14 GPIO_ACTIVE_HIGH>;
        reset-gpios = <&gpio4 15 GPIO_ACTIVE_LOW>;
        backlight = <&backlight_lcd>;
        width-mm = <28>;
        height-mm = <28>;

        panel-timing {
            hactive = <240>;
            vactive = <240>;
            hback-porch = <0>;
            vback-porch = <0>;
            clock-frequency = <0>;
            hfront-porch = <0>;
            hsync-len = <0>;
            vfront-porch = <0>;
            vsync-len = <0>;
        };
    };
};
```

The init sequence lives in `/lib/firmware/mydisplay.bin`, compiled from a human-readable description with the `mipi-dbi-cmd` tool (in the kernel tree). For a panel already supported by an existing init blob, you reuse it.

For most production: **use panel-mipi-dbi with a firmware init blob**. Write a custom DRM driver only if the panel needs runtime logic the firmware-blob can't express.

## 83.6  Performance — partial updates

A full 240×240 RGB565 frame = 115200 bytes. At 40 MHz SPI: ~23 ms = ~43 fps theoretical max for full refresh. In practice, ~30 fps with overhead.

The trick: **only send what changed**. The `mipi_dbi` helper tracks dirty rectangles. If your UI updates a small clock digit, only that rectangle is sent — a few KB, sub-millisecond. This is why SPI LCDs feel snappy for typical UIs (mostly static with small dynamic regions) even though full-screen video would be a slideshow.

For a Qt or LVGL app, the toolkit reports dirty regions to DRM. The helper sends only those. No tearing if you respect the vblank.

## 83.7  Lab

1. **Wire an ST7789** 240×240 module: MOSI, SCLK, CS, DC, RESET, BLK, VCC, GND.
2. **Build and load `myst7789.ko`.** Verify `/dev/fb0` appears at 240×240.
3. **Paint.** `cat /dev/urandom > /dev/fb0` (noise), `cat /dev/zero > /dev/fb0` (black or white depending on INVON).
4. **Fix colors.** If colors are wrong (red shows blue), toggle the BGR bit in MADCTL (0x36 param) or INVON/INVOFF.
5. **Rotation.** Change MADCTL to rotate 90°/180°/270°. Verify the image orientation.
6. **Performance.** Measure full-frame update time: time `cat /dev/zero > /dev/fb0`. Then a partial update (write a small region). confirm it's much faster.
7. **panel-mipi-dbi.** Switch to the generic driver with a firmware init blob. Compile the blob with `mipi-dbi-cmd`. Verify same result, no custom C.
8. **LVGL or Qt.** Run a GUI toolkit on `/dev/fb0`. verify a real UI renders and updates smoothly.

## 83.8  Pitfalls

- **Missing DC GPIO toggle.** Commands and data get confused. controller does nothing or garbage. The `mipi_dbi` helper handles DC. a hand-rolled driver must toggle it correctly (low for command byte, high for parameters/pixels).
- **Wrong init sequence.** Each module vendor tweaks the gamma/voltage commands. A generic ST7789 init may give washed-out or dark colors. Use the vendor's recommended sequence.
- **INVON vs INVOFF.** Many cheap ST7789 modules have inverted pixels — black shows as white. Toggle MIPI_DCS_ENTER_INVERT_MODE.
- **BGR vs RGB.** MADCTL bit 3 swaps red and blue. If red text shows as blue, flip it.
- **Column/row offset.** Some 240×240 ST7789 modules are actually 240×320 panels with the display window offset — you must add an x/y offset in CASET/RASET or the image is shifted. Vendor-specific.
- **SPI too fast.** ST7789 tolerates ~62 MHz. ILI9341 writes at ~30 MHz reliably. Above the limit: corrupt pixels. Start at 20 MHz, ramp up.
- **No reset pulse.** Without a hardware reset at probe, the controller may be in an undefined state. Always pulse RESET low for ~10 µs at init.
- **Backlight not handled.** Display "works" (data flows) but screen dark. Wire and enable the backlight.
- **DRM headers version mismatch.** The DRM API churns between kernel versions. `mipi_dbi_dev_init` signature changed across 5.x/6.x. Match your driver to your kernel.

## 83.9  Going deeper

- **`drivers/gpu/drm/drm_mipi_dbi.c`** — the shared mipi_dbi helper. Read `mipi_dbi_fb_dirty` for the partial-update path.
- **`drivers/gpu/drm/tiny/ili9341.c`** — a complete tiny driver. compare to the from-scratch version.
- **`drivers/gpu/drm/tiny/panel-mipi-dbi.c`** — the generic firmware-blob driver.
- **`Documentation/gpu/drm-kms-helpers.rst`** — the simple-display-pipe + mipi_dbi helpers.
- **`tools/` → `mipi-dbi-cmd`** — the firmware-blob compiler.
- **ST7789 datasheet (Sitronix)** — command list. init recommendations.
- **ILI9341 datasheet (Ilitek)** — command list.
- **MIPI DBI specification** — the standard these controllers descend from.

> Next chapter: **Chapter 84 — QSPI LCD.** When SPI bandwidth isn't enough — quad-SPI displays for higher frame rates and the round LCDs popular in smartwatches.
