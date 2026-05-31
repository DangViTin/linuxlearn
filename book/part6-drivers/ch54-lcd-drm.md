---
chapter: 54
title: LCD framebuffer and DRM/KMS
part: VI — Driver development
estimated_pages: 18
status: draft
---

# Chapter 54 — LCD framebuffer and DRM/KMS

> **What:** the kernel's display stack — the legacy **fbdev** (`/dev/fb0`) API and the modern **DRM/KMS** (Direct Rendering Manager / Kernel Mode Setting) framework. Both still ship; new drivers target DRM. We cover the i.MX6ULL **LCDIF** controller, the `panel-simple` driver that handles dozens of RGB-parallel panels, and how mainline kernels expose displays to user-space.
> **Why:** LCDIF + RGB parallel LCDs are the bread and butter of i.MX6ULL HMI products. The framework has shifted significantly in the last 5 years (away from fbdev, toward DRM) and being current matters — DRM brings page-flipping, atomic mode-setting, fence-based synchronisation, and Wayland compatibility.
> **Focus:** **panel-simple + DT timings == working display**. For 90 % of products you don't write a panel driver; you describe panel timings in DT, point at `panel-simple`, and the LCDIF driver handles the rest. The remaining 10 % is custom panels needing a chip-specific init sequence, covered in Ch 80–84 of the cookbook.

## 54.1  fbdev vs DRM

| | fbdev | DRM/KMS |
|---|---|---|
| Era | 1990s–early 2010s | 2008-present |
| API style | mmap `/dev/fb0`, ioctl | Object-based (CRTCs, planes, encoders, connectors) |
| Multi-display | Awkward | Native |
| Atomic mode-set | No | Yes |
| Page-flipping | Hack | First-class |
| Wayland | No | Yes |
| User-space typical client | direct mmap | libdrm + Mesa / Cairo / GTK / Qt |

For embedded HMI with one panel and a single fullscreen Qt app, fbdev still works. For anything with multiple outputs, GPU acceleration, or Wayland, DRM is the only option. **Both are present** on modern kernels; fbdev is emulated on top of DRM via `fbdev_emulation`. Your fullscreen Qt app sees `/dev/fb0`; under the hood DRM is doing the work.

## 54.2  i.MX6ULL LCDIF

The LCDIF is a DPI / RGB-parallel controller. It outputs:

- **Pixel clock** (PCLK; 6–80 MHz typical).
- **HSYNC** (horizontal sync).
- **VSYNC** (vertical sync).
- **DE** (data enable).
- **24 data lines** (R[7:0], G[7:0], B[7:0]) — typically wired as 18-bit RGB666 or 24-bit RGB888.

The driver is `drivers/gpu/drm/mxsfb/`. It's a DRM driver; fbdev users get `/dev/fb0` via emulation.

## 54.3  RGB-parallel panel timings

Every RGB-parallel panel has:
- **Resolution** — e.g., 800 × 480.
- **Pixel clock frequency** — e.g., 33 MHz.
- **Horizontal porches** — `hsync-len`, `hback-porch`, `hfront-porch`.
- **Vertical porches** — `vsync-len`, `vback-porch`, `vfront-porch`.
- **Polarity bits** — HS, VS, DE, PCLK active edges.

In DT, these go in a `panel-timing` subnode:

```dts
panel {
    compatible = "panel-simple";
    backlight = <&backlight>;
    enable-gpios = <&gpio5 11 GPIO_ACTIVE_HIGH>;
    power-supply = <&reg_lcd_3v3>;

    port {
        panel_in: endpoint {
            remote-endpoint = <&lcdif_out>;
        };
    };

    panel-timing {
        clock-frequency = <33300000>;
        hactive = <800>;
        vactive = <480>;
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
};
```

These numbers come from the panel datasheet's *AC characteristics* page. Get them right; get them slightly wrong and you get a "rolling" image or no image at all.

The LCDIF side:

```dts
&lcdif {
    pinctrl-names = "default";
    pinctrl-0 = <&pinctrl_lcdif_dat>, <&pinctrl_lcdif_ctrl>;
    display = <&display0>;
    status = "okay";

    port {
        lcdif_out: endpoint {
            remote-endpoint = <&panel_in>;
        };
    };
};
```

The `port`/`endpoint` graph wires LCDIF's output to panel's input. This is the `of_graph` binding — used throughout DRM for "this output goes to that input."

## 54.4  panel-simple

`drivers/gpu/drm/panel/panel-simple.c` is a magnificent hack: it has a *database* of dozens of supported panels (vendor-id + part-number), each with a struct of timings hardcoded. For a panel that's already in the database, you just add `compatible = "vendor,partno"`:

```dts
panel {
    compatible = "ampire,am-480272h3tmqw-t01h", "panel-dpi";
    /* timings derived from the compatible */
};
```

If your panel isn't in the database, use `compatible = "panel-dpi"` and supply timings yourself (§54.3).

## 54.5  User-space usage

### fbdev style (legacy)

```
[root@pa-mini:~]# ls /dev/fb*
/dev/fb0

[root@pa-mini:~]# fbset
mode "800x480-60"
    geometry 800 480 800 480 32
    timings 30030 210 46 23 22 1 1
    ...

[root@pa-mini:~]# cat /dev/urandom > /dev/fb0   # paint random pixels
```

For a Qt app: just run it with `-platform linuxfb` and Qt mmaps `/dev/fb0`.

### DRM style (modern)

```
[root@pa-mini:~]# modetest -M mxsfb
Encoders:
id    crtc    type    possible crtcs    possible clones
35    33      DPI     0x00000001        0x00000000

Connectors:
id      encoder status          name            size (mm)       modes   encoders
36      35      connected       DPI-1           0x0             1       35
        modes:
            #0 800x480 60.00 800 1010 1056 1066 480 502 524 547 33300 flags: nhsync, nvsync; type: preferred, driver

[root@pa-mini:~]# modetest -M mxsfb -s 36:800x480   # set 800x480 mode
```

For user-space drawing: libdrm + GBM (Generic Buffer Management) + a 2D library like Cairo. For Qt: `-platform eglfs` (full GPU, not on i.MX6ULL — no GPU) or `-platform linuxfb` (falls through to fbdev emulation).

## 54.6  Backlight

A typical RGB panel needs:
- VLED rail (12 V or boosted).
- PWM dimming via a transistor driver.

DT:

```dts
backlight: backlight {
    compatible = "pwm-backlight";
    pwms = <&pwm1 0 5000000 0>;
    brightness-levels = <0 4 8 16 32 64 128 255>;
    default-brightness-level = <6>;
    power-supply = <&reg_lcd_vled>;
};
```

Ch 48 covered pwm-backlight; the LCDIF driver references it via `backlight = <&backlight>;` to coordinate power-on/off ordering.

## 54.7  Bring-up checklist

When a new panel doesn't display:

1. **Verify the pixel clock is generated.** Scope PCLK; should be at the rate in DT.
2. **Verify HSYNC and VSYNC.** Polarity matches DT (`hsync-active = <0>` = active-low).
3. **Verify data lines** with a scope. Pattern depends on what's in `/dev/fb0`; `cat /dev/zero > /dev/fb0` gives all-zero data.
4. **Verify enable pin.** Some panels need a "panel-on" GPIO held high.
5. **Verify backlight.** Even if the panel is showing correctly, with backlight off you see nothing.
6. **Verify timings against the datasheet.** Off-by-one in front-porch is the most common error.

`drm.debug=15` on kernel cmdline floods dmesg with DRM info; invaluable for chasing modeset issues.

## 54.8  Lab

1. **Bring up a panel.** Use a known-good panel (Ampire, ATK7016) with mainline timings. Boot; confirm `/dev/fb0` and `modetest` output. `cat /dev/urandom > /dev/fb0` shows pixels.
2. **Custom panel timings.** Add timings for a panel that isn't in panel-simple's database. Iterate until display is stable.
3. **Backlight.** Verify `/sys/class/backlight/backlight/brightness` adjusts visibly.
4. **modetest.** Run on a kernel with DRM-only; see the modes; pick one; observe modeset.
5. **A Qt app.** Compile a simple Qt app with `-platform linuxfb`; run; verify it draws.
6. **DRM client.** Write a small libdrm program that creates a dumb buffer, fills it red, and presents it. Useful for understanding DRM bring-up.

## 54.9  Pitfalls

- **Pixel clock too high.** PCLK > ~80 MHz on i.MX6ULL LCDIF → silent failure. Use lower pixel clock or smaller resolution.
- **Wrong polarity.** Image inverted vertically or shifted; classic "porch off by one" symptom.
- **Backlight forgot.** "Display broken!" — backlight is off. Always test with daylight first.
- **Pinmux clash.** LCDIF uses many pins (24 data + 4 control). Conflict with another peripheral muxed onto the same pin → garbled output.
- **DT enable-gpios missing or wrong polarity.** Panel power-up sequence broken.
- **Wrong DRM mode.** modetest's "preferred" mode may not be what you want; specify explicitly.
- **`fbcon` console** drawing on top of your Qt app. Disable: `vt.global_cursor_default=0` + `fbcon=null`.

## 54.10  Going deeper

- **`Documentation/gpu/drm-internals.rst`** — DRM architecture.
- **`Documentation/gpu/drm-kms.rst`** — KMS (Kernel Mode Setting) detailed.
- **`drivers/gpu/drm/mxsfb/`** — i.MX LCDIF DRM driver.
- **`drivers/gpu/drm/panel/panel-simple.c`** — panel database.
- **`Documentation/devicetree/bindings/display/panel/`** — panel bindings.
- **`libdrm`** at `kernel.org` — user-space DRM library and `modetest` source.

> Next chapter: **Chapter 54A — MTD/UBI for raw NAND.** When your storage isn't an eMMC/SD card but raw NAND, MTD partitions it and UBI manages wear levelling above MTD.
