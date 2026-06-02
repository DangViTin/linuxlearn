---
chapter: 85
title: OLED & e-paper (SSD1306 / SH1106 / SSD1680)
part: VII — Device cookbook
estimated_pages: 20
status: draft
---

# Chapter 85 — OLED & e-paper

> **What:** two non-backlit display technologies. **OLED** — self-emissive monochrome dot-matrix: **Solomon SSD1306** (128×64, I²C/SPI), **Sino Wealth SH1106** (132×64, the "almost-SSD1306"). **E-paper** — bistable reflective: **Solomon SSD1680** (the controller behind most 1.5"–2.9" e-paper modules). For each: the framebuffer-RAM model, the refresh mechanics (instant for OLED, multi-second for e-paper), the mainline driver, and a from-scratch SSD1306 fbdev driver.
>
> **Why:** OLEDs are the cheapest "real display" you can buy. A 128×64 OLED costs around $2, draws ~20 mA, and has perfect contrast without a backlight. E-paper is the opposite. Zero idle power — the image persists with no power. Sunlight-readable. But slow to update. Both show up constantly in IoT status displays, instruments, smart-home panels, electronic shelf labels. They need very different driver thinking than the raster panels of Ch 82–84.
>
> **Focus:** OLED uses a page-addressed bitmap. E-paper uses a two-buffer waveform replay driven by a LUT. They need very different driver code. The SSD1306 stores a 1-bit-per-pixel image in internal RAM organized as 8 "pages" of 128 bytes; you push the whole bitmap and it displays instantly. The SSD1680 stores *two* images (old + new) and replays a per-pixel voltage *waveform* (the LUT) over ~2 seconds to flip the e-ink particles — a completely different mental model.

## 85.1  Technology & chip comparison

| | SSD1306 OLED | SH1106 OLED | SSD1680 e-paper |
|---|---|---|---|
| Tech | OLED (self-emissive) | OLED | E-ink (bistable reflective) |
| Resolution | 128×64 / 128×32 | 132×64 (128 visible) | up to 296×176 |
| Colors | mono (on/off) | mono | mono or B/W/Red |
| Interface | I²C (0x3C/0x3D) or SPI | I²C / SPI | SPI |
| RAM model | 8 pages × 128 cols | 8 pages × 132 cols (offset!) | dual buffer + LUT |
| Refresh | instant (<1 ms) | instant | full ~2 s, partial ~0.3 s |
| Idle power | ~5 µW off, ~20 mW on | similar | **0 W** (image persists) |
| Sunlight | poor (washes out) | poor | excellent |
| Lifetime | OLED burn-in over years | burn-in | ~1M refresh cycles |
| Volume price | $1.50–3 | $1.50–3 | $5–15 |
| Mainline driver | `ssd130x` (DRM tiny) / `ssd1307fb` (fbdev) | same `ssd130x` | `repaper.c`, `ssd1680` patches |

**Pick guide:**
- **SSD1306**: default tiny status display. Ubiquitous.
- **SH1106**: nearly identical; the catch is its 132-column RAM with a 2-pixel offset — drivers must account for it.
- **SSD1680**: e-paper for "set it and forget it" displays (shelf labels, room signs, low-power dashboards).

## 85.2  SSD1306 — page-addressed framebuffer

The SSD1306 has 128×64 = 8192 pixels = 1024 bytes of internal RAM (1 bit/pixel). It's organized as **8 pages**, each 128 bytes wide. Within a page, *each byte is a vertical column of 8 pixels* (bit 0 = top, bit 7 = bottom):

```
   Page 0: byte[0] = column 0, rows 0-7    (bit0=row0, bit7=row7)
           byte[1] = column 1, rows 0-7
           ...
           byte[127] = column 127, rows 0-7
   Page 1: rows 8-15
   ...
   Page 7: rows 56-63
```

This vertical-byte layout is unusual (most framebuffers are row-major with horizontal bytes). To set pixel (x, y): `page = y / 8; bit = y % 8; ram[page*128 + x] |= (1 << bit);`.

### Commands vs data

Like the SPI LCDs (Ch 83), the SSD1306 distinguishes commands from data. Over **I²C**, the distinction is a control byte:

```
   I²C write: [control byte] [data/command byte] ...
   control byte 0x00 → following bytes are COMMANDS
   control byte 0x40 → following bytes are DATA (pixels)
```

Over **SPI**, a D/C GPIO selects (like Ch 83).

### Key commands

| Command | Hex | Purpose |
|---------|-----|---------|
| Display off / on | 0xAE / 0xAF | Power the panel |
| Set contrast | 0x81 + value | Brightness |
| Set memory mode | 0x20 + mode | Horizontal/vertical/page addressing |
| Set column range | 0x21 + start + end | (horizontal mode) |
| Set page range | 0x22 + start + end | (horizontal mode) |
| Charge pump | 0x8D + 0x14 | Enable internal boost (mandatory!) |
| Set COM pins | 0xDA + config | Panel geometry |

### The init sequence

A working SSD1306 init (the canonical sequence):

```
0xAE              display off
0x20 0x00         horizontal addressing mode
0xB0              page start
0xC8              COM scan direction (flip vertical)
0x00 0x10         column low/high
0x40              start line 0
0x81 0x7F         contrast
0xA1              segment remap (flip horizontal)
0xA6              normal (non-inverted)
0xA8 0x3F         multiplex 64
0xA4              output follows RAM
0xD3 0x00         display offset 0
0xD5 0xF0         clock divide
0xD9 0x22         pre-charge
0xDA 0x12         COM pins config
0xDB 0x20         VCOMH
0x8D 0x14         charge pump ON  ← without this, screen stays black
0xAF              display on
```

The `0x8D 0x14` (charge pump enable) is the #1 gotcha. The OLED needs an internal boost converter for the ~7 V it requires. Forget this command and the screen stays black.

## 85.3  How the mainline driver works

Two mainline drivers exist:

- **`drivers/video/fbdev/ssd1307fb.c`** — legacy fbdev driver. Exposes `/dev/fb0`; a 1-bit framebuffer.
- **`drivers/gpu/drm/solomon/ssd130x.c`** + `ssd130x-i2c.c` / `ssd130x-spi.c` — modern DRM driver. Covers SSD1305/1306/1307/1309 and SH1106.

The DRM `ssd130x` driver:
1. Reads geometry from DT (width, height, page-offset, COM config).
2. Runs the init sequence.
3. Registers a DRM device with a 1-bit (or emulated) framebuffer.
4. On framebuffer flush, converts the DRM XRGB8888 buffer to the SSD1306's packed-vertical-byte format and pushes the dirty pages.

```c
/* ssd130x.c — simplified flush */
static int ssd130x_update_rect(struct ssd130x_device *ssd130x,
                               struct drm_rect *rect, u8 *buf)
{
    unsigned int x = rect->x1, y = rect->y1;
    unsigned int width = drm_rect_width(rect);
    unsigned int pages = DIV_ROUND_UP(drm_rect_height(rect), 8);

    /* Set the column + page address window */
    ssd130x_write_cmd(ssd130x, 3, 0x21, x + ssd130x->col_offset,
                      x + ssd130x->col_offset + width - 1);
    ssd130x_write_cmd(ssd130x, 3, 0x22, y / 8, y / 8 + pages - 1);

    /* Pack the rect into vertical bytes and push as data */
    for (each page in the rect) {
        ... pack 8 vertical pixels per byte ...
        ssd130x_write_data(ssd130x, packed, width);
    }
    return 0;
}
```

The DRM helper does the XRGB→1bit conversion (any non-black pixel → on); the driver packs into vertical bytes and pushes only the dirty pages.

## 85.4  Writing an SSD1306 fbdev driver from scratch

A DRM driver is the modern way, but for a monochrome OLED a simple **fbdev** driver is more illustrative — it's the bare "here's a framebuffer, here's how I push it to the chip" model. ~200 lines.

`myssd1306.c`:

```c
#include <linux/init.h>
#include <linux/module.h>
#include <linux/i2c.h>
#include <linux/fb.h>
#include <linux/delay.h>
#include <linux/vmalloc.h>

#define WIDTH   128
#define HEIGHT  64
#define PAGES   (HEIGHT / 8)
#define FB_SIZE (WIDTH * PAGES)        /* 1024 bytes */

struct myssd {
    struct i2c_client *client;
    struct fb_info *info;
    u8 *vmem;                          /* the 1-bit framebuffer (1024 bytes) */
};

static int ms_cmd(struct myssd *m, u8 cmd)
{
    u8 buf[2] = { 0x00, cmd };          /* control 0x00 = command */
    return i2c_master_send(m->client, buf, 2);
}

static int ms_data(struct myssd *m, const u8 *data, int len)
{
    /* Prefix with control byte 0x40 = data */
    u8 *buf = kmalloc(len + 1, GFP_KERNEL);
    int ret;
    if (!buf) return -ENOMEM;
    buf[0] = 0x40;
    memcpy(buf + 1, data, len);
    ret = i2c_master_send(m->client, buf, len + 1);
    kfree(buf);
    return ret;
}

static const u8 ssd1306_init[] = {
    0xAE, 0x20, 0x00, 0xB0, 0xC8, 0x00, 0x10, 0x40,
    0x81, 0x7F, 0xA1, 0xA6, 0xA8, 0x3F, 0xA4, 0xD3,
    0x00, 0xD5, 0xF0, 0xD9, 0x22, 0xDA, 0x12, 0xDB,
    0x20, 0x8D, 0x14, 0xAF,
};

static int ms_init_panel(struct myssd *m)
{
    int i, err;
    for (i = 0; i < ARRAY_SIZE(ssd1306_init); i++) {
        err = ms_cmd(m, ssd1306_init[i]);
        if (err < 0) return err;
    }
    return 0;
}

/* Push the entire vmem framebuffer to the OLED */
static void ms_flush(struct myssd *m)
{
    /* Set full window: columns 0-127, pages 0-7 */
    ms_cmd(m, 0x21); ms_cmd(m, 0); ms_cmd(m, 127);
    ms_cmd(m, 0x22); ms_cmd(m, 0); ms_cmd(m, 7);
    ms_data(m, m->vmem, FB_SIZE);
}

/* fbdev deferred-io callback: called after the framebuffer is touched */
static void ms_deferred_io(struct fb_info *info, struct list_head *pagelist)
{
    struct myssd *m = info->par;
    ms_flush(m);
}

static struct fb_deferred_io ms_defio = {
    .delay = HZ / 30,                   /* flush at most 30×/sec */
    .deferred_io = ms_deferred_io,
};

static const struct fb_fix_screeninfo ms_fix = {
    .id = "myssd1306",
    .type = FB_TYPE_PACKED_PIXELS,
    .visual = FB_VISUAL_MONO10,
    .xpanstep = 0, .ypanstep = 0, .ywrapstep = 0,
    .line_length = WIDTH / 8,
    .accel = FB_ACCEL_NONE,
};

static const struct fb_var_screeninfo ms_var = {
    .xres = WIDTH, .yres = HEIGHT,
    .xres_virtual = WIDTH, .yres_virtual = HEIGHT,
    .bits_per_pixel = 1,
};

/* Standard fbdev ops backed by deferred-io */
static const struct fb_ops ms_fbops = {
    .owner       = THIS_MODULE,
    .fb_read     = fb_sys_read,
    .fb_write    = fb_sys_write,
    .fb_fillrect = sys_fillrect,
    .fb_copyarea = sys_copyarea,
    .fb_imageblit = sys_imageblit,
    .fb_mmap     = fb_deferred_io_mmap,
};

static int ms_probe(struct i2c_client *client)
{
    struct myssd *m;
    struct fb_info *info;
    int err;

    m = devm_kzalloc(&client->dev, sizeof(*m), GFP_KERNEL);
    if (!m) return -ENOMEM;
    m->client = client;

    m->vmem = vzalloc(FB_SIZE);
    if (!m->vmem) return -ENOMEM;

    err = ms_init_panel(m);
    if (err) goto free_vmem;

    info = framebuffer_alloc(0, &client->dev);
    if (!info) { err = -ENOMEM; goto free_vmem; }

    info->par = m;
    info->fbops = &ms_fbops;
    info->fix = ms_fix;
    info->var = ms_var;
    info->screen_buffer = m->vmem;
    info->screen_size = FB_SIZE;
    info->fbdefio = &ms_defio;
    fb_deferred_io_init(info);

    m->info = info;
    i2c_set_clientdata(client, m);

    err = register_framebuffer(info);
    if (err) goto release_fb;

    /* Clear screen */
    memset(m->vmem, 0, FB_SIZE);
    ms_flush(m);

    dev_info(&client->dev, "SSD1306 OLED at /dev/fb%d\n", info->node);
    return 0;

release_fb:
    fb_deferred_io_cleanup(info);
    framebuffer_release(info);
free_vmem:
    vfree(m->vmem);
    return err;
}

static void ms_remove(struct i2c_client *client)
{
    struct myssd *m = i2c_get_clientdata(client);
    unregister_framebuffer(m->info);
    fb_deferred_io_cleanup(m->info);
    framebuffer_release(m->info);
    vfree(m->vmem);
}

static const struct of_device_id ms_of_match[] = {
    { .compatible = "linuxlearn,myssd1306" },
    { }
};
MODULE_DEVICE_TABLE(of, ms_of_match);

static const struct i2c_device_id ms_id[] = { { "myssd1306", 0 }, { } };
MODULE_DEVICE_TABLE(i2c, ms_id);

static struct i2c_driver ms_driver = {
    .driver = {
        .name = "myssd1306",
        .of_match_table = ms_of_match,
    },
    .probe = ms_probe,
    .remove = ms_remove,
    .id_table = ms_id,
};
module_i2c_driver(ms_driver);

MODULE_LICENSE("GPL");
```

DT:

```dts
&i2c1 {
    oled@3c {
        compatible = "linuxlearn,myssd1306";
        reg = <0x3c>;
    };
};
```

Test:

```
[root@pa-mini:~]# insmod myssd1306.ko
[root@pa-mini:~]# dmesg | tail -1
myssd1306 1-003c: SSD1306 OLED at /dev/fb0

[root@pa-mini:~]# cat /sys/class/graphics/fb0/virtual_size
128,64

# The framebuffer is 1-bit-per-pixel, 16 bytes per line.
# Write a pattern (every byte 0xFF = alternating columns lit):
[root@pa-mini:~]# python3 -c "import sys; sys.stdout.buffer.write(bytes([0xFF,0x00]*512))" > /dev/fb0
[root@pa-mini:~]# # → vertical stripes appear on the OLED
```

The key abstraction: **`fb_deferred_io`**. The framebuffer lives in vmalloc'd RAM; user-space writes to it via mmap or write(). The deferred-io machinery batches writes and calls `ms_deferred_io` (which calls `ms_flush`) at most 30×/second — so a flurry of pixel writes results in one I²C burst, not thousands.

What we got, ~200 lines:
- `/dev/fb0` at 128×64, 1-bit.
- Deferred-io batched flushing.
- Standard fbdev ops (fillrect, imageblit) work — so toolkits like `fbi`, `fbcon`, simple Cairo apps render.

What we skipped vs the mainline `ssd130x` DRM driver:
- DRM integration (mainline is DRM; fbdev is legacy).
- SPI transport (we did I²C only).
- SH1106 column-offset handling.
- Contrast / inversion runtime control.
- Partial-page updates (we flush the whole frame).

## 85.5  SH1106 — the off-by-2 sibling

SH1106 is nearly pin- and command-compatible with SSD1306, *except* its RAM is **132 columns wide** while the visible panel is 128. The visible area is centered, so columns 2–129 are shown; columns 0–1 and 130–131 are off-screen.

The consequence: when you set the column window, you must offset by 2. A driver written for SSD1306 (offset 0) shows the SH1106 image shifted 2 pixels right, with garbage wrapping on the left edge. The mainline `ssd130x` driver reads a `col_offset` value from DT to handle this case.

For SH1106, change the column window from 0–127 to 2–129. Some SH1106 variants do not support horizontal addressing mode at all — for those, set the page and column manually for each page.

## 85.6  SSD1680 e-paper — a completely different model

E-paper is *bistable*: each pixel is a microcapsule of black and white particles that move under an electric field and *stay put* with no power. This gives zero-power image retention but makes refreshing slow and weird.

### The dual-buffer + LUT model

The SSD1680 holds **two image buffers**: the "old" image (currently on the glass) and the "new" image. To refresh, the controller replays a **waveform** — a sequence of voltage pulses per pixel — that moves the particles from old to new state. The waveform is defined by a **LUT** (look-up table) loaded into the controller.

```
   1. Write new image to the "new" buffer (SPI, like SSD1306 RAM).
   2. (Optional) write old image to "old" buffer for differential update.
   3. Load the waveform LUT (or use the OTP built-in LUT).
   4. Trigger DISPLAY UPDATE (command 0x22 + 0x20).
   5. Wait for BUSY pin to go inactive (~2 seconds for full refresh).
```

Two refresh modes:

- **Full refresh** (~2 s): flashes the whole screen black→white→target several times to clear ghosting. Clean image, slow, visible flicker.
- **Partial refresh** (~0.3 s): updates only changed pixels without the full flash. Fast, but accumulates **ghosting** (faint remnants of old images). Must do a full refresh periodically to clear.

### Why this is hard for a generic framebuffer

A normal framebuffer is "write pixel, see it." E-paper is "write image, trigger update, wait 2 seconds, see it." The deferred-io model breaks (you can't flush 30×/sec — each flush takes 2 s). E-paper drivers expose a custom update trigger and let user-space decide *when* to refresh.

Mainline: `drivers/gpu/drm/tiny/repaper.c` (for Pervasive Displays panels) and various SSD1680 patches. The DRM driver does a full refresh on each DRM page-flip — acceptable for "update once per minute" status displays, terrible for anything interactive.

### Practical use

```
# After bring-up, a typical e-paper update from user-space:
[root@pa-mini:~]# cat dashboard.bin > /dev/fb0     # write the image
[root@pa-mini:~]# echo 1 > /sys/class/graphics/fb0/refresh   # trigger (driver-specific)
# ... 2 seconds of flicker ...
# Image now on screen, persists with power off.
```

For e-paper, you design the UI around the refresh model: update once per minute (weather, room booking), use partial refresh for a clock-style digit, full refresh periodically to de-ghost.

## 85.7  Lab

1. **SSD1306 bring-up.** Wire to I²C1 at 0x3C. Build and load `myssd1306.ko`. Verify `/dev/fb0`.
2. **Draw patterns.** Write 0xFF/0x00 patterns; verify stripes. Write all 0xFF; full screen lit.
3. **The charge-pump test.** Comment out the `0x8D 0x14` command in the init; reload. Screen stays black — proving the charge pump's necessity. Restore.
4. **fbcon.** If your kernel has `CONFIG_FRAMEBUFFER_CONSOLE`, the boot console might appear on the OLED. Tiny but readable.
5. **Cairo / Python PIL.** Use Python PIL to render text into a 128×64 1-bit image; write to `/dev/fb0`. A real status display.
6. **SH1106 offset.** If you have an SH1106, run the SSD1306 driver; observe the 2-pixel shift; fix with the column offset.
7. **E-paper (if available).** Bring up an SSD1680 module. Display an image; measure refresh time (~2 s). Cut power; verify the image persists. Do 10 partial refreshes; observe ghosting accumulate; do a full refresh; observe it clear.

## 85.8  Pitfalls

- **Charge pump not enabled.** `0x8D 0x14` is mandatory for the internal boost; without it, the OLED is black. The #1 SSD1306 gotcha.
- **Wrong I²C address.** SSD1306 is 0x3C (or 0x3D if the addr-select pad is bridged). Check with `i2cdetect`.
- **SH1106 treated as SSD1306.** 2-pixel horizontal shift + edge garbage. Set the column offset.
- **Vertical-byte confusion.** The SSD1306 RAM layout is column-of-8-vertical-pixels per byte. A driver that assumes row-major bytes shows a scrambled image. Pack correctly.
- **Flushing too often.** Without deferred-io, every pixel write triggers a full 1 KB I²C transfer — the bus saturates. Batch with `fb_deferred_io`.
- **OLED burn-in.** A static image (a logo, a fixed UI) burns in over months. Invert/shift periodically, or dim, for always-on displays.
- **E-paper partial-refresh ghosting.** Accumulates; schedule periodic full refreshes.
- **E-paper update while busy.** Triggering a new update before BUSY clears corrupts the image. Always wait for BUSY.
- **E-paper temperature sensitivity.** Below ~0 °C, e-paper refreshes very slowly or not at all. The waveform LUT is temperature-dependent. Good modules include a temperature sensor and ship multiple LUTs for the controller to switch between.

## 85.9  Going deeper

- **`drivers/gpu/drm/solomon/ssd130x.c`** — modern DRM OLED driver (SSD1306/SH1106).
- **`drivers/video/fbdev/ssd1307fb.c`** — legacy fbdev OLED driver; compare to the from-scratch version.
- **`drivers/gpu/drm/tiny/repaper.c`** — e-paper DRM driver (Pervasive Displays).
- **`Documentation/fb/deferred_io.rst`** — the deferred-io framework.
- **SSD1306 datasheet (Solomon Systech)** — command table; page-addressing model.
- **SH1106 datasheet** — note the 132-column RAM.
- **SSD1680 datasheet** — the dual-buffer + LUT waveform model.
- **`drivers/video/fbdev/core/fb_defio.c`** — deferred-io implementation.

> Next chapter: **Chapter 86 — Touch input ICs.** Turning a display into an interface: capacitive buttons (TTP223), capacitive matrices (MPR121), and resistive 4-wire touch (XPT2046) with its calibration story.
