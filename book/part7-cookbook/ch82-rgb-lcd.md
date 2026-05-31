---
chapter: 82
title: RGB parallel LCD on LCDIF (ATK4384 / ATK7016 / ATK10261)
part: VII — Device cookbook
estimated_pages: 22
status: draft
---

# Chapter 82 — RGB parallel LCD on LCDIF

> **What:** "dumb" RGB-parallel TFT panels driven by the i.MX6ULL's **LCDIF** controller. Three panels compared: **ATK4384** (4.3" 480×272), **ATK7016** (7" 1024×600), **ATK10261** (10.1" 1280×800). The panel has no controller — it just accepts pixel clock + sync + 24 data lines. The "driver" is therefore a *timing description* + the DRM panel framework. We cover panel timings deeply, how `panel-simple` works internally, and how to add a custom panel (two ways: DT-only via `panel-dpi`, or a real `drm_panel` driver from scratch).
> **Why:** parallel-RGB is the standard HMI display interface for i.MX6ULL. A parallel panel has no frame buffer of its own. The SoC streams pixels at the pixel clock and refreshes the glass 60 times a second. Get the timings right and the panel works. Get one porch wrong and the image rolls, tears, or stays blank. This chapter is mostly about *reading a panel datasheet's timing table and translating it to DT*.
> **Focus:** A working panel needs a pixel clock, six porch numbers, and three polarities. That is the entire job. The LCDIF is a raster generator: it outputs HSYNC/VSYNC/DE/PCLK and 24 RGB bits, scanning left-to-right, top-to-bottom, forever. The panel datasheet gives you the exact timing; you transcribe it into a `panel-timing` DT node. There is no negotiation. The numbers must match the glass.

## 82.1  Panel comparison

| | ATK4384 | ATK7016 | ATK10261 |
|---|---|---|---|
| Size | 4.3" | 7" | 10.1" |
| Resolution | 480×272 | 1024×600 | 1280×800 |
| Pixel clock | 9 MHz | 51.2 MHz | 71.1 MHz |
| Color depth | 24-bit (RGB888) | 24-bit | 24-bit |
| Interface | RGB parallel (DPI) | RGB parallel | RGB parallel |
| Backlight | LED, PWM dimming | LED, PWM | LED, PWM |
| Touch | resistive or capacitive option | capacitive (GT911) | capacitive (GT911) |
| i.MX6ULL feasible? | ✓ easily | ✓ (near LCDIF max) | ⚠ 71 MHz pclk exceeds safe LCDIF range (~70 MHz) |

**i.MX6ULL LCDIF pixel-clock ceiling** is ~70 MHz in practice. The ATK4384 (9 MHz) and ATK7016 (51 MHz) are comfortable; ATK10261 at 71 MHz is at the limit. It usually works but you may need to drop to a lower refresh rate.

## 82.2  How a parallel-RGB panel works

A parallel TFT has no memory. The SoC must *continuously* send every pixel, every frame, forever:

```
   for each frame (60×/sec):
     VSYNC pulse
     vertical back porch (blank lines)
     for each visible line (e.g., 272 or 600):
       HSYNC pulse
       horizontal back porch (blank pixels)
       for each visible pixel (e.g., 480 or 1024):
         drive R[7:0], G[7:0], B[7:0]; assert DE; tick PCLK
       horizontal front porch (blank pixels)
     vertical front porch (blank lines)
```

The signals:

- **PCLK** (pixel clock): one tick per pixel. The panel latches RGB on each edge.
- **HSYNC**: marks the start of each horizontal line.
- **VSYNC**: marks the start of each frame.
- **DE** (data enable): high during the visible region; the panel only shows pixels when DE is high.
- **R/G/B[7:0]**: 24 data lines (18 for RGB666 panels).

The "porches" are blanking intervals. They are a CRT legacy — the electron beam needed time to fly back. LCDs kept the timing model. The panel datasheet specifies exact porch widths.

### The timing math

Total horizontal pixels = hsync + hbackporch + hactive + hfrontporch.
Total vertical lines = vsync + vbackporch + vactive + vfrontporch.

```
pixel_clock = (h_total) × (v_total) × refresh_rate
```

For ATK7016 (1024×600 @ 60 Hz):
```
h_total = 1 (hsync) + 46 (hbp) + 1024 (active) + 210 (hfp) = 1281
v_total = 1 (vsync) + 23 (vbp) + 600 (active) + 22 (vfp) = 646
pclk = 1281 × 646 × 60 ≈ 49.6 MHz
```

Close to the datasheet's 51.2 MHz (the difference is the exact refresh rate they spec). The point: **the porches and pixel clock are interdependent**, and the panel datasheet gives the authoritative numbers.

## 82.3  Device tree — the timing description

The LCDIF side:

```dts
&lcdif {
    pinctrl-names = "default";
    pinctrl-0 = <&pinctrl_lcdif_dat>, <&pinctrl_lcdif_ctrl>;
    display = <&display0>;
    status = "okay";

    display0: display0 {
        bits-per-pixel = <24>;
        bus-width = <24>;

        display-timings {
            native-mode = <&timing_atk7016>;
            timing_atk7016: timing0 {
                clock-frequency = <51200000>;
                hactive = <1024>;
                vactive = <600>;
                hfront-porch = <210>;
                hback-porch = <46>;
                hsync-len = <1>;
                vback-porch = <23>;
                vfront-porch = <22>;
                vsync-len = <1>;
                hsync-active = <0>;   /* HSYNC active-low */
                vsync-active = <0>;   /* VSYNC active-low */
                de-active = <1>;      /* DE active-high */
                pixelclk-active = <0>; /* latch on falling edge */
            };
        };
    };
};
```

For ATK4384 substitute: `clock-frequency = <9000000>; hactive = <480>; vactive = <272>; hfront-porch = <5>; hback-porch = <40>; hsync-len = <1>; vback-porch = <8>; vfront-porch = <8>; vsync-len = <1>;`.

These numbers come directly from the panel datasheet's "AC Timing Characteristics" / "Display Timing" table. Transcribing them is the entire job.

### The modern DRM way: panel-simple + of_graph

The above uses the older `display-timings` binding. The modern DRM/KMS approach uses `panel-simple` and the `of_graph` port/endpoint binding:

```dts
&lcdif {
    status = "okay";
    port {
        lcdif_out: endpoint {
            remote-endpoint = <&panel_in>;
        };
    };
};

panel {
    compatible = "panel-dpi";
    backlight = <&backlight>;
    enable-gpios = <&gpio5 11 GPIO_ACTIVE_HIGH>;
    power-supply = <&reg_lcd_3v3>;

    width-mm = <154>;
    height-mm = <86>;

    panel-timing {
        clock-frequency = <51200000>;
        hactive = <1024>;
        vactive = <600>;
        hfront-porch = <210>;
        hback-porch = <46>;
        hsync-len = <1>;
        vback-porch = <23>;
        vfront-porch = <22>;
        vsync-len = <1>;
        hsync-active = <0>;
        vsync-active = <0>;
        de-active = <1>;
        pixelclk-active = <0>;
    };

    port {
        panel_in: endpoint {
            remote-endpoint = <&lcdif_out>;
        };
    };
};
```

`panel-dpi` is `panel-simple`'s generic "describe-your-own-timing" variant. The `port`/`endpoint` graph wires the LCDIF output to the panel input.

## 82.4  How `panel-simple` works internally

Source: `drivers/gpu/drm/panel/panel-simple.c` (~5000 lines, but most is the panel *database*).

The driver is a **`drm_panel`** provider. It has:

1. A giant database of known panels (vendor+part → hardcoded `display_mode` struct).
2. A generic `panel-dpi` / `panel-lvds` path that reads timings from DT.
3. Power-sequencing logic: enable regulator, wait, assert enable-gpio, wait, turn on backlight.

```c
/* Simplified */
struct panel_simple {
    struct drm_panel base;
    struct regulator *supply;
    struct gpio_desc *enable_gpio;
    struct backlight_device *backlight;
    const struct panel_desc *desc;   /* timings + delays */
};

static int panel_simple_prepare(struct drm_panel *panel)
{
    struct panel_simple *p = to_panel_simple(panel);

    regulator_enable(p->supply);
    if (p->desc->delay.prepare)
        msleep(p->desc->delay.prepare);
    gpiod_set_value_cansleep(p->enable_gpio, 1);
    if (p->desc->delay.enable)
        msleep(p->desc->delay.enable);
    return 0;
}

static int panel_simple_get_modes(struct drm_panel *panel,
                                  struct drm_connector *connector)
{
    struct panel_simple *p = to_panel_simple(panel);
    struct drm_display_mode *mode = drm_mode_create(connector->dev);

    /* Copy the timing from desc (database) or DT into a drm_display_mode */
    drm_display_mode_from_videomode(&p->vm, mode);
    mode->type = DRM_MODE_TYPE_DRIVER | DRM_MODE_TYPE_PREFERRED;
    drm_mode_probed_add(connector, mode);
    return 1;
}

static const struct drm_panel_funcs panel_simple_funcs = {
    .prepare    = panel_simple_prepare,
    .enable     = panel_simple_enable,    /* turns on backlight */
    .disable    = panel_simple_disable,
    .unprepare  = panel_simple_unprepare,
    .get_modes  = panel_simple_get_modes,
};
```

The LCDIF DRM driver (`mxsfb`) is the **CRTC + encoder**; the panel is the **connector's** mode source. At modeset time, DRM:

1. Calls `panel->prepare` (power on).
2. Reads modes via `panel->get_modes`.
3. Programs the LCDIF's timing registers from the chosen mode.
4. Calls `panel->enable` (backlight on).
5. Streams pixels.

## 82.5  Adding a custom panel — three approaches

### Approach 1: DT-only via panel-dpi (no code)

If your panel isn't in the database, use `compatible = "panel-dpi"` and put the timing in DT (§82.3). Zero code. **This is the right answer for 90 % of custom panels.**

### Approach 2: Add to the panel-simple database (small patch)

If you want a clean `compatible = "vendor,part"` and intend to upstream:

```c
/* In panel-simple.c */
static const struct drm_display_mode atk7016_mode = {
    .clock = 51200,
    .hdisplay = 1024,
    .hsync_start = 1024 + 210,
    .hsync_end = 1024 + 210 + 1,
    .htotal = 1024 + 210 + 1 + 46,
    .vdisplay = 600,
    .vsync_start = 600 + 22,
    .vsync_end = 600 + 22 + 1,
    .vtotal = 600 + 22 + 1 + 23,
    .flags = DRM_MODE_FLAG_NHSYNC | DRM_MODE_FLAG_NVSYNC,
};

static const struct panel_desc atk7016 = {
    .modes = &atk7016_mode,
    .num_modes = 1,
    .bpc = 8,
    .size = { .width = 154, .height = 86 },
    .bus_format = MEDIA_BUS_FMT_RGB888_1X24,
    .bus_flags = DRM_BUS_FLAG_DE_HIGH | DRM_BUS_FLAG_PIXDATA_DRIVE_NEGEDGE,
};

/* Add to of_device_id table: */
{ .compatible = "alientek,atk7016", .data = &atk7016 },
```

Notice the DRM `drm_display_mode` uses *cumulative* values (hsync_start = hdisplay + front_porch) rather than the DT's separate porch fields. The conversion is simple but easy to get wrong.

### Approach 3: A full drm_panel driver from scratch

Some panels need custom power sequencing or init commands. This is rare for dumb RGB panels but common for panels with an init controller. For those, write a `drm_panel` driver:

```c
#include <drm/drm_panel.h>
#include <drm/drm_modes.h>
#include <linux/platform_device.h>
#include <linux/gpio/consumer.h>
#include <linux/regulator/consumer.h>

struct mypanel {
    struct drm_panel panel;
    struct gpio_desc *enable_gpio;
    struct regulator *supply;
    struct backlight_device *backlight;
};

#define to_mypanel(p) container_of(p, struct mypanel, panel)

static const struct drm_display_mode mypanel_mode = {
    .clock = 51200,
    .hdisplay = 1024, .hsync_start = 1234, .hsync_end = 1235, .htotal = 1281,
    .vdisplay = 600,  .vsync_start = 622,  .vsync_end = 623,  .vtotal = 646,
    .flags = DRM_MODE_FLAG_NHSYNC | DRM_MODE_FLAG_NVSYNC,
};

static int mypanel_prepare(struct drm_panel *panel)
{
    struct mypanel *p = to_mypanel(panel);
    int err = regulator_enable(p->supply);
    if (err) return err;
    msleep(20);
    gpiod_set_value_cansleep(p->enable_gpio, 1);
    msleep(50);
    return 0;
}

static int mypanel_unprepare(struct drm_panel *panel)
{
    struct mypanel *p = to_mypanel(panel);
    gpiod_set_value_cansleep(p->enable_gpio, 0);
    regulator_disable(p->supply);
    return 0;
}

static int mypanel_get_modes(struct drm_panel *panel, struct drm_connector *connector)
{
    struct drm_display_mode *mode = drm_mode_duplicate(connector->dev, &mypanel_mode);
    if (!mode) return -ENOMEM;
    mode->type = DRM_MODE_TYPE_DRIVER | DRM_MODE_TYPE_PREFERRED;
    drm_mode_probed_add(connector, mode);
    connector->display_info.width_mm = 154;
    connector->display_info.height_mm = 86;
    return 1;
}

static const struct drm_panel_funcs mypanel_funcs = {
    .prepare   = mypanel_prepare,
    .unprepare = mypanel_unprepare,
    .get_modes = mypanel_get_modes,
};

static int mypanel_probe(struct platform_device *pdev)
{
    struct mypanel *p;
    int err;

    p = devm_kzalloc(&pdev->dev, sizeof(*p), GFP_KERNEL);
    if (!p) return -ENOMEM;

    p->supply = devm_regulator_get(&pdev->dev, "power");
    if (IS_ERR(p->supply)) return PTR_ERR(p->supply);

    p->enable_gpio = devm_gpiod_get(&pdev->dev, "enable", GPIOD_OUT_LOW);
    if (IS_ERR(p->enable_gpio)) return PTR_ERR(p->enable_gpio);

    drm_panel_init(&p->panel, &pdev->dev, &mypanel_funcs, DRM_MODE_CONNECTOR_DPI);

    err = drm_panel_of_backlight(&p->panel);   /* finds backlight from DT */
    if (err) return err;

    drm_panel_add(&p->panel);
    platform_set_drvdata(pdev, p);
    return 0;
}

static void mypanel_remove(struct platform_device *pdev)
{
    struct mypanel *p = platform_get_drvdata(pdev);
    drm_panel_remove(&p->panel);
}

static const struct of_device_id mypanel_of_match[] = {
    { .compatible = "linuxlearn,mypanel" },
    { }
};
MODULE_DEVICE_TABLE(of, mypanel_of_match);

static struct platform_driver mypanel_driver = {
    .driver = {
        .name = "linuxlearn-mypanel",
        .of_match_table = mypanel_of_match,
    },
    .probe = mypanel_probe,
    .remove = mypanel_remove,
};
module_platform_driver(mypanel_driver);

MODULE_LICENSE("GPL");
```

DT:

```dts
panel {
    compatible = "linuxlearn,mypanel";
    power-supply = <&reg_lcd_3v3>;
    enable-gpios = <&gpio5 11 GPIO_ACTIVE_HIGH>;
    backlight = <&backlight>;
    port {
        panel_in: endpoint {
            remote-endpoint = <&lcdif_out>;
        };
    };
};
```

About 120 lines. It registers a `drm_panel` with the timing and power sequencing. The LCDIF DRM driver finds the panel through the of_graph link and uses its mode. For a *dumb* panel this is overkill (use panel-dpi), but for a panel that needs an init sequence (e.g., a panel with an embedded controller requiring SPI commands before it accepts RGB — covered in Ch 83), this is the structure you extend.

## 82.6  Backlight + power sequencing

A panel needs:
1. Logic power (3.3 V) — `power-supply`.
2. An enable/standby GPIO — `enable-gpios`.
3. Backlight (LED, PWM-dimmed) — `backlight` phandle to a `pwm-backlight` node (Ch 48).

The power sequence matters: most panels want logic power *before* enabling, and the backlight *last* (so you don't show garbage during init). The `prepare`/`enable` split in `drm_panel_funcs` enforces this — `prepare` powers logic, `enable` turns on backlight.

```dts
backlight: backlight {
    compatible = "pwm-backlight";
    pwms = <&pwm1 0 5000000 0>;
    brightness-levels = <0 4 8 16 32 64 128 255>;
    default-brightness-level = <6>;
    power-supply = <&reg_lcd_vled>;
};
```

## 82.7  User-space

After bring-up:

```
[root@pa-mini:~]# cat /sys/class/graphics/fb0/modes
U:1024x600p-60

[root@pa-mini:~]# fbset
mode "1024x600-60"
    geometry 1024 600 1024 600 32
    timings 19531 46 210 23 22 1 1
endmode

[root@pa-mini:~]# cat /dev/urandom > /dev/fb0      # noise on screen
[root@pa-mini:~]# modetest -M mxsfb -s <connector_id>:1024x600   # DRM modeset test
```

For a Qt app: `./app -platform linuxfb`. For backlight: `echo 4 > /sys/class/backlight/backlight/brightness`.

## 82.8  Lab

1. **Bring up the ATK7016.** Transcribe its datasheet timings into a `panel-dpi` DT node. Boot; verify `/dev/fb0` exists with the right geometry.
2. **Paint the screen.** `cat /dev/urandom > /dev/fb0` — noise. `cat /dev/zero > /dev/fb0` — black. Confirm the panel responds.
3. **Backlight.** Wire `pwm-backlight`. Sweep `/sys/class/backlight/backlight/brightness` 0→255; verify dimming.
4. **Deliberately wrong porch.** Change `hfront-porch` by 100; reboot. Observe the image shift / tear. Restore.
5. **Custom drm_panel driver.** Build `mypanel.ko` from §82.5 approach 3. Verify it registers and the LCDIF picks up its mode.
6. **modetest.** Run a DRM-only kernel; use `modetest` to list connectors and set the mode.
7. **Qt app.** Run a simple Qt `-platform linuxfb` app; verify it renders.
8. **Pixel-clock limit.** Try the ATK10261 (71 MHz pclk). Note if it works or glitches; if it glitches, reduce to a 50 Hz refresh timing (lower pclk) and retest.

## 82.9  Pitfalls

- **One porch wrong = rolling/torn image.** The classic symptom. Re-check every porch value against the datasheet.
- **Polarity wrong.** `hsync-active`, `vsync-active`, `de-active`, `pixelclk-active` must match the panel. Inverted DE = black screen. Inverted pixelclk = data latched on wrong edge = garbled.
- **Pixel clock exceeds LCDIF max.** ~70 MHz ceiling on i.MX6ULL. Above this, the LCDIF can't generate stable timing. Use a lower-resolution or lower-refresh mode.
- **Backlight forgotten.** "Display broken!" — backlight off. Always test in daylight first; the LCD content is there even with backlight off (faintly visible).
- **Pinmux clash.** LCDIF uses 24 data + 4 control = 28 pins. Conflicts with other peripherals muxed onto those pins → garbled or no output. Audit pinmux.
- **bits-per-pixel vs bus-width.** A 24-bit framebuffer on an 18-bit (RGB666) bus needs dithering or truncation. Set `bus-width = <18>` for RGB666 panels.
- **enable-gpio polarity.** Active-high vs active-low. Wrong → panel stays in standby, blank.
- **Power sequencing race.** Backlight on before logic power stabilises → flash of garbage. Use prepare/enable split.
- **DE-only vs sync mode.** Some panels use DE-only timing (ignore HSYNC/VSYNC, rely on DE). Set `de-active` and ensure the panel's mode-select pins agree.

## 82.10  Going deeper

- **`drivers/gpu/drm/mxsfb/`** — the i.MX LCDIF DRM driver.
- **`drivers/gpu/drm/panel/panel-simple.c`** — the panel database + panel-dpi/lvds generic paths.
- **`Documentation/devicetree/bindings/display/panel/`** — panel bindings; `panel-dpi.yaml`, `simple-panel.yaml`.
- **`include/drm/drm_panel.h`** — the drm_panel API.
- **`Documentation/gpu/drm-kms.rst`** — CRTC/encoder/connector/panel model.
- **ATK7016 / ATK4384 datasheets** — the timing tables.
- **`drivers/video/of_display_timing.c`** — how DT `display-timings` are parsed.

> Next chapter: **Chapter 83 — SPI LCD.** Smart panels (ST7789, ILI9341) with an embedded controller and frame buffer — driven over SPI with command/data framing. The DRM "tiny" driver framework and `mipi-dbi`.
