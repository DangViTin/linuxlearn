---
chapter: 87
title: Parallel CSI cameras (OV5640 / OV7725 / GC2145)
part: VII — Device cookbook
estimated_pages: 24
status: draft
---

# Chapter 87 — Parallel CSI cameras

> **What:** image sensors connected to the i.MX6ULL's **parallel CSI** (Camera Sensor Interface — 8-bit data + pixel/line/frame sync, *not* MIPI). Three sensors compared: **OmniVision OV5640** (5 MP, the common default), **OV7725** (0.3 MP VGA, simple), **GalaxyCore GC2145** (2 MP, budget). For each: the dual-bus model (I²C for control + parallel for pixels), the V4L2 **sub-device** architecture, the media-controller graph, and a from-scratch V4L2 sensor subdev driver.
> **Why:** Any i.MX6ULL product with a camera uses parallel CSI. The i.MX6ULL has no MIPI-CSI. Smart doorbells, barcode scanners, and machine-vision sensors all run through this interface. The driver model has more moving parts than most subsystems. A *sensor* sub-device feeds a *CSI bridge* sub-device, which feeds a *video* device. The media controller wires them all together. Understand this graph and the rest of V4L2 falls into place.
> **Focus:** A camera sensor is two devices in one. It has an I²C control interface and a parallel pixel stream. V4L2 models the combination as a sub-device. The sensor's driver lives on I²C (configure resolution, exposure, format via registers) but exposes a *pad* that emits a pixel-format on the parallel bus. The CSI bridge captures that stream into DRAM. The media graph connects sensor-pad → CSI-pad → video-node.
> **Tooling.** This chapter uses `v4l-utils`, `gstreamer1.0-tools` + plugins, `i2c-tools`.
> - **Ubuntu-base (target):** `apt install v4l-utils gstreamer1.0-tools gstreamer1.0-plugins-base gstreamer1.0-plugins-good gstreamer1.0-plugins-bad i2c-tools`
> - **Buildroot:** `BR2_PACKAGE_V4L_UTILS=y BR2_PACKAGE_GSTREAMER1=y BR2_PACKAGE_GST1_PLUGINS_BASE=y BR2_PACKAGE_I2C_TOOLS=y`
> - Full per-tool reference: [Userspace tooling appendix](../part5-rootfs/appendix-tooling.md).

## 87.1  Sensor comparison

| | OmniVision OV5640 | OmniVision OV7725 | GalaxyCore GC2145 |
|---|---|---|---|
| Resolution | 2592×1944 (5 MP) | 640×480 (VGA) | 1600×1200 (2 MP) |
| Output formats | YUV422, RGB565, RAW, JPEG | YUV422, RGB565, RAW | YUV422, RGB565, RAW |
| Interface | 8/10-bit parallel + MIPI | 8-bit parallel | 8-bit parallel + MIPI |
| Control | I²C (0x3C) | I²C (0x21) | I²C (0x3C) |
| Frame rate | 30 fps @ 1080p, 15 fps @ 5 MP | 60 fps @ VGA | 30 fps @ UXGA |
| Autofocus | VCM (voice-coil motor) option | no (fixed focus) | no |
| Built-in ISP | yes (AWB, AE, gamma) | basic | basic |
| Init complexity | ~250 register writes | ~100 | ~200 |
| Volume price | $5–10 (module) | $2–4 | $3–5 |
| Mainline driver | `ov5640.c` | `ov772x.c` | `gc2145.c` (recent) |

**i.MX6ULL CSI bandwidth**: the parallel CSI captures 8-bit data at the sensor's pixel clock (typically up to ~96 MHz). For 5 MP at full res, the data rate exceeds what the i.MX6ULL can comfortably DMA to DRAM — practical use is QVGA/VGA streaming or occasional full-res stills.

**Pick guide:**
- **OV5640**: when you need quality + the built-in ISP (auto-exposure, auto-white-balance). The default.
- **OV7725**: VGA is enough, want simplicity and high frame rate.
- **GC2145**: cheap 2 MP; the budget option.

## 87.2  The dual-bus camera model

A parallel camera sensor has *two* connections to the SoC:

```
   i.MX6ULL                      OV5640
   ─────────                     ──────
   I²C (SCL/SDA) ◄──────────────► SIOC/SIOD   (control: registers)
   CSI_PCLK     ◄──────────────── PCLK         (pixel clock from sensor)
   CSI_HSYNC    ◄──────────────── HREF         (line valid)
   CSI_VSYNC    ◄──────────────── VSYNC        (frame valid)
   CSI_D[7:0]   ◄──────────────── D[9:2]        (8-bit pixel data)
   CSI_MCLK     ────────────────► XCLK          (master clock TO sensor, ~24 MHz)
   GPIO         ────────────────► PWDN          (power down)
   GPIO         ────────────────► RESET
```

Two roles:
- **I²C**: the host configures the sensor — resolution, output format, exposure, gain, test patterns. Hundreds of register writes.
- **Parallel bus**: the sensor *continuously* streams pixels (like the RGB LCD of Ch 82, but inbound). The sensor is the *master* of the pixel clock (it generates PCLK); the CSI captures on each PCLK edge when HREF+VSYNC indicate valid data.
- **MCLK**: the SoC provides the sensor's master clock (typically 24 MHz); the sensor's internal PLL multiplies it up to the pixel clock.

The sensor needs its MCLK running *before* I²C communication works (the sensor's logic is clocked by MCLK). This is a common bring-up gotcha.

## 87.3  The V4L2 sub-device + media-controller model

V4L2 models a capture pipeline as a graph of **entities** connected by **pads** and **links**:

```
   ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
   │   ov5640     │     │   imx-csi    │     │  /dev/video0 │
   │  (subdev)    │ pad │  (subdev)    │ pad │  (video dev) │
   │      source ●──────►● sink  src ●──────►● sink         │
   └──────────────┘     └──────────────┘     └──────────────┘
   sensor: emits          CSI bridge:          video node:
   YUV422 640×480         captures parallel     user-space mmaps
   on its source pad      stream → DRAM          frames here
```

- **Sub-device** (`v4l2_subdev`): a sensor or a processing block. The OV5640 is a subdev; the CSI is a subdev. Subdevs have **pads** (source = output, sink = input).
- **Video device** (`/dev/video0`): the user-space-facing node where frames are dequeued.
- **Media controller** (`/dev/media0`): the graph topology. `media-ctl` inspects and configures links.

The user-space app:
1. Opens `/dev/media0`, inspects the graph.
2. Sets the format on each pad (sensor source, CSI sink, CSI source) — they must match through the pipeline.
3. Opens `/dev/video0`, sets the buffer format, queues buffers, streams.

All this indirection — separate subdevs, explicit format propagation — feels heavy for one camera. It is what lets V4L2 handle complex pipelines (multiple sensors, ISP stages, scalers) with the same code paths.

## 87.4  How the mainline `ov5640` driver works

Source: `drivers/media/i2c/ov5640.c` (~3700 lines — sensors are big because of the register init tables and the ISP control).

The driver is a **`v4l2_subdev`** registered on I²C. Its structure:

```c
struct ov5640_dev {
    struct i2c_client *i2c_client;
    struct v4l2_subdev sd;            /* the subdev */
    struct media_pad pad;             /* its source pad */
    struct v4l2_ctrl_handler ctrls;   /* exposure, gain, AWB, etc. */
    struct clk *xclk;                  /* master clock input */
    struct gpio_desc *reset_gpio;
    struct gpio_desc *pwdn_gpio;
    struct regulator_bulk_data supplies[OV5640_NUM_SUPPLIES];
    /* current mode */
    const struct ov5640_mode_info *current_mode;
};
```

### Probe

```c
static int ov5640_probe(struct i2c_client *client)
{
    struct ov5640_dev *sensor;

    sensor = devm_kzalloc(&client->dev, sizeof(*sensor), GFP_KERNEL);
    sensor->i2c_client = client;

    /* Get clocks, regulators, GPIOs */
    sensor->xclk = devm_clk_get(&client->dev, "xclk");
    sensor->reset_gpio = devm_gpiod_get(&client->dev, "reset", GPIOD_OUT_HIGH);
    sensor->pwdn_gpio = devm_gpiod_get(&client->dev, "powerdown", GPIOD_OUT_HIGH);
    devm_regulator_bulk_get(&client->dev, ..., sensor->supplies);

    /* Power on + verify chip id */
    ov5640_power_on(sensor);                  /* MCLK on, GPIOs sequenced */
    ov5640_read_reg(sensor, OV5640_REG_CHIP_ID_HIGH, &id);   /* expect 0x5640 */

    /* Init V4L2 subdev */
    v4l2_i2c_subdev_init(&sensor->sd, client, &ov5640_subdev_ops);
    sensor->sd.flags |= V4L2_SUBDEV_FL_HAS_DEVNODE;
    sensor->pad.flags = MEDIA_PAD_FL_SOURCE;
    media_entity_pads_init(&sensor->sd.entity, 1, &sensor->pad);

    /* Register controls (exposure, gain, AWB, test pattern) */
    ov5640_init_controls(sensor);

    /* Register the subdev asynchronously (the CSI bridge will bind to it) */
    v4l2_async_register_subdev_sensor(&sensor->sd);
    return 0;
}
```

### The subdev ops

```c
static const struct v4l2_subdev_video_ops ov5640_video_ops = {
    .s_stream = ov5640_s_stream,       /* start/stop streaming */
};

static const struct v4l2_subdev_pad_ops ov5640_pad_ops = {
    .enum_mbus_code = ov5640_enum_mbus_code,    /* what formats can I emit? */
    .get_fmt        = ov5640_get_fmt,
    .set_fmt        = ov5640_set_fmt,            /* set resolution + format */
    .enum_frame_size = ov5640_enum_frame_size,
};
```

`s_stream(1)` writes the registers to start the sensor outputting pixels; `set_fmt` programs the resolution + format registers. The sensor's "pad format" tells the CSI bridge what to expect.

### The register init tables

The bulk of `ov5640.c` is **mode tables** — arrays of (register, value) pairs for each supported resolution:

```c
static const struct reg_value ov5640_init_setting[] = {
    {0x3103, 0x11, 0, 0}, {0x3008, 0x82, 0, 5}, {0x3008, 0x42, 0, 0},
    {0x3103, 0x03, 0, 0}, {0x3630, 0x36, 0, 0}, {0x3631, 0x0e, 0, 0},
    /* ... ~250 more ... */
};

static const struct reg_value ov5640_setting_VGA_640_480[] = {
    {0x3c07, 0x08, 0, 0}, {0x3814, 0x31, 0, 0}, {0x3815, 0x31, 0, 0},
    /* resolution-specific registers */
};
```

These come from OmniVision's reference code. They configure the sensor's internal ISP, PLL, timing, and pixel pipeline. Like the BME280 compensation formulas (Ch 67) or the VL53L0X tuning blob (Ch 72), these are vendor IP transcribed verbatim — you don't derive them, you apply them.

## 87.5  Writing a minimal V4L2 sensor subdev from scratch

A full OV5640 driver is 3700 lines (mostly mode tables). For learning, we'll write a *minimal* subdev for a simple sensor — a fixed-format VGA YUV422 sensor (modeling an OV7725-class part) — that registers in the media graph and streams one fixed mode. ~250 lines.

`mysensor.c`:

```c
#include <linux/init.h>
#include <linux/module.h>
#include <linux/i2c.h>
#include <linux/clk.h>
#include <linux/gpio/consumer.h>
#include <linux/delay.h>
#include <media/v4l2-subdev.h>
#include <media/v4l2-async.h>
#include <media/v4l2-ctrls.h>
#include <media/v4l2-fwnode.h>

#define SENSOR_WIDTH   640
#define SENSOR_HEIGHT  480
#define REG_CHIP_ID    0x0A
#define CHIP_ID_VAL    0x77

struct mysensor {
    struct i2c_client *client;
    struct v4l2_subdev sd;
    struct media_pad pad;
    struct clk *xclk;
    struct gpio_desc *reset_gpio;
    struct v4l2_ctrl_handler ctrls;
    bool streaming;
};

#define to_mysensor(s) container_of(s, struct mysensor, sd)

static int ms_read(struct mysensor *m, u8 reg)
{
    return i2c_smbus_read_byte_data(m->client, reg);
}

static int ms_write(struct mysensor *m, u8 reg, u8 val)
{
    return i2c_smbus_write_byte_data(m->client, reg, val);
}

/* A (tiny, illustrative) init sequence — real sensors have hundreds */
static const u8 ms_init_seq[][2] = {
    { 0x12, 0x80 },   /* soft reset */
    { 0x11, 0x01 },   /* clock prescaler */
    { 0x0C, 0x00 },   /* output format = YUV422 */
    { 0x12, 0x00 },   /* VGA, YUV */
    /* ... real sensors: hundreds more ... */
};

static int ms_apply_init(struct mysensor *m)
{
    int i, err;
    err = ms_write(m, 0x12, 0x80);   /* reset */
    if (err) return err;
    msleep(10);
    for (i = 0; i < ARRAY_SIZE(ms_init_seq); i++) {
        err = ms_write(m, ms_init_seq[i][0], ms_init_seq[i][1]);
        if (err) return err;
    }
    return 0;
}

/* --- subdev pad ops: tell the pipeline what format we emit --- */

static int ms_enum_mbus_code(struct v4l2_subdev *sd,
                             struct v4l2_subdev_state *state,
                             struct v4l2_subdev_mbus_code_enum *code)
{
    if (code->index != 0) return -EINVAL;
    code->code = MEDIA_BUS_FMT_YUYV8_2X8;    /* YUV422, 8-bit parallel */
    return 0;
}

static int ms_get_fmt(struct v4l2_subdev *sd,
                      struct v4l2_subdev_state *state,
                      struct v4l2_subdev_format *fmt)
{
    fmt->format.width  = SENSOR_WIDTH;
    fmt->format.height = SENSOR_HEIGHT;
    fmt->format.code   = MEDIA_BUS_FMT_YUYV8_2X8;
    fmt->format.field  = V4L2_FIELD_NONE;
    fmt->format.colorspace = V4L2_COLORSPACE_SRGB;
    return 0;
}

/* We only support one fixed format, so set_fmt = get_fmt */
#define ms_set_fmt ms_get_fmt

static int ms_enum_frame_size(struct v4l2_subdev *sd,
                              struct v4l2_subdev_state *state,
                              struct v4l2_subdev_frame_size_enum *fse)
{
    if (fse->index != 0) return -EINVAL;
    fse->min_width = fse->max_width = SENSOR_WIDTH;
    fse->min_height = fse->max_height = SENSOR_HEIGHT;
    return 0;
}

/* --- subdev video ops: start/stop streaming --- */

static int ms_s_stream(struct v4l2_subdev *sd, int enable)
{
    struct mysensor *m = to_mysensor(sd);
    int err = 0;

    if (enable == m->streaming) return 0;

    if (enable) {
        /* Write registers to start pixel output */
        err = ms_write(m, 0x12, 0x00);   /* enable output */
    } else {
        err = ms_write(m, 0x12, 0x40);   /* standby */
    }
    if (!err) m->streaming = enable;
    return err;
}

static const struct v4l2_subdev_video_ops ms_video_ops = {
    .s_stream = ms_s_stream,
};

static const struct v4l2_subdev_pad_ops ms_pad_ops = {
    .enum_mbus_code  = ms_enum_mbus_code,
    .get_fmt         = ms_get_fmt,
    .set_fmt         = ms_set_fmt,
    .enum_frame_size = ms_enum_frame_size,
};

static const struct v4l2_subdev_ops ms_subdev_ops = {
    .video = &ms_video_ops,
    .pad   = &ms_pad_ops,
};

/* --- power sequencing --- */

static int ms_power_on(struct mysensor *m)
{
    int err;
    err = clk_prepare_enable(m->xclk);    /* MCLK must run before I²C works */
    if (err) return err;
    gpiod_set_value_cansleep(m->reset_gpio, 0);   /* release reset */
    msleep(20);
    return 0;
}

static int ms_probe(struct i2c_client *client)
{
    struct mysensor *m;
    int id, err;

    m = devm_kzalloc(&client->dev, sizeof(*m), GFP_KERNEL);
    if (!m) return -ENOMEM;
    m->client = client;

    m->xclk = devm_clk_get(&client->dev, "xclk");
    if (IS_ERR(m->xclk))
        return dev_err_probe(&client->dev, PTR_ERR(m->xclk), "no xclk\n");

    m->reset_gpio = devm_gpiod_get_optional(&client->dev, "reset", GPIOD_OUT_HIGH);

    err = ms_power_on(m);
    if (err) return err;

    /* Verify chip ID (now that MCLK is running) */
    id = ms_read(m, REG_CHIP_ID);
    if (id < 0) return dev_err_probe(&client->dev, id, "chip-id read failed\n");
    if (id != CHIP_ID_VAL)
        return dev_err_probe(&client->dev, -ENODEV,
                             "unexpected chip-id 0x%02x\n", id);

    err = ms_apply_init(m);
    if (err) return err;

    /* Init the V4L2 subdev */
    v4l2_i2c_subdev_init(&m->sd, client, &ms_subdev_ops);
    m->sd.flags |= V4L2_SUBDEV_FL_HAS_DEVNODE;
    m->sd.entity.function = MEDIA_ENT_F_CAM_SENSOR;
    m->pad.flags = MEDIA_PAD_FL_SOURCE;
    err = media_entity_pads_init(&m->sd.entity, 1, &m->pad);
    if (err) return err;

    /* Register asynchronously — the CSI bridge binds to us */
    err = v4l2_async_register_subdev_sensor(&m->sd);
    if (err) {
        media_entity_cleanup(&m->sd.entity);
        return err;
    }

    dev_info(&client->dev, "mysensor VGA YUV422 ready\n");
    return 0;
}

static void ms_remove(struct i2c_client *client)
{
    struct v4l2_subdev *sd = i2c_get_clientdata(client);
    struct mysensor *m = to_mysensor(sd);
    v4l2_async_unregister_subdev(sd);
    media_entity_cleanup(&sd->entity);
    clk_disable_unprepare(m->xclk);
}

static const struct of_device_id ms_of_match[] = {
    { .compatible = "linuxlearn,mysensor" },
    { }
};
MODULE_DEVICE_TABLE(of, ms_of_match);

static struct i2c_driver ms_driver = {
    .driver = {
        .name = "mysensor",
        .of_match_table = ms_of_match,
    },
    .probe = ms_probe,
    .remove = ms_remove,
};
module_i2c_driver(ms_driver);

MODULE_LICENSE("GPL");
```

DT — the sensor *and* its link to the CSI bridge via of_graph:

```dts
&i2c1 {
    sensor@21 {
        compatible = "linuxlearn,mysensor";
        reg = <0x21>;
        clocks = <&clks IMX6UL_CLK_CSI>;
        clock-names = "xclk";
        reset-gpios = <&gpio4 25 GPIO_ACTIVE_LOW>;
        pinctrl-names = "default";
        pinctrl-0 = <&pinctrl_csi_mclk>;

        port {
            sensor_out: endpoint {
                remote-endpoint = <&csi_in>;
                bus-width = <8>;
                hsync-active = <1>;
                vsync-active = <1>;
                pclk-sample = <1>;
            };
        };
    };
};

&csi {
    status = "okay";
    port {
        csi_in: endpoint {
            remote-endpoint = <&sensor_out>;
        };
    };
};
```

The `port`/`endpoint` graph links `sensor_out` → `csi_in`. The endpoint properties (`bus-width`, `hsync-active`, `pclk-sample`) describe the parallel bus electrical timing — the CSI bridge needs them to capture correctly.

Build, load:

```
[root@pa-mini:~]# insmod mysensor.ko
[root@pa-mini:~]# dmesg | grep mysensor
mysensor 1-0021: mysensor VGA YUV422 ready

[root@pa-mini:~]# media-ctl -p -d /dev/media0
Entity 1: mysensor 1-0021 (1 pad, 1 link)
            type V4L2 subdev subtype Sensor
        pad0: Source [fmt:YUYV8_2X8/640x480]
                -> "imx-csi":0 [ENABLED]
Entity 2: imx-csi (2 pads, ...)
...

[root@pa-mini:~]# ls /dev/video0
/dev/video0
```

The sensor appears in the media graph, linked to the CSI bridge, with `/dev/video0` available for capture. Capture with the V4L2 ioctl sequence from Ch 54B, or:

```
[root@pa-mini:~]# v4l2-ctl --device /dev/video0 \
    --set-fmt-video=width=640,height=480,pixelformat=YUYV \
    --stream-mmap=3 --stream-count=10 --stream-to=frames.raw
```

10 VGA YUV422 frames captured to `frames.raw`.

What we got, ~250 lines:
- A V4L2 sensor subdev registered in the media graph.
- Power sequencing (MCLK before I²C).
- One fixed VGA YUV422 mode.
- Streaming start/stop.

What a real OV5640 driver adds (the other ~3500 lines):
- Dozens of resolution modes with full register tables.
- Exposure/gain/AWB/AF V4L2 controls.
- Frame-rate control.
- Test patterns.
- The full ISP configuration.

## 87.6  The CSI bridge side

The i.MX6ULL CSI driver (`drivers/staging/media/imx/imx7-media-csi.c` or the imx6 variant) is the *other* subdev — it captures the parallel stream into DRAM via DMA. You don't write this (it's the SoC's silicon driver). It:

1. Binds to the sensor subdev (via the of_graph link + v4l2-async).
2. Reads the sensor's pad format.
3. Configures the CSI peripheral's capture format + DMA.
4. Provides `/dev/video0` (the video device).

The bridge + sensor must agree on format: if the sensor emits YUYV8_2X8 640×480, the CSI captures that. `media-ctl --set-v4l2` can override pad formats during bring-up debugging.

## 87.7  GStreamer + processing

Once `/dev/video0` works (Ch 54B covers this), GStreamer pipelines do the rest:

```sh
# Display on the LCD (Ch 82)
gst-launch-1.0 v4l2src device=/dev/video0 ! video/x-raw,format=YUY2,width=640,height=480 \
    ! videoconvert ! fbdevsink

# JPEG-encode and save
gst-launch-1.0 v4l2src device=/dev/video0 num-buffers=1 ! jpegenc ! filesink location=snap.jpg

# Stream over network
gst-launch-1.0 v4l2src device=/dev/video0 ! jpegenc ! rtpjpegpay ! udpsink host=192.168.1.100 port=5000
```

i.MX6ULL has no GPU/VPU, so JPEG/H.264 encoding is software — slow. Practical: ~5–10 fps at VGA for encoded streams; raw capture is faster.

## 87.8  Lab

1. **Power + clock first.** Verify the sensor's MCLK is present (scope CSI_MCLK) before debugging I²C. Without MCLK, the sensor won't ACK I²C.
2. **Detect the sensor.** `i2cdetect -y 1` — OV5640 at 0x3C, OV7725 at 0x21. Read the chip-id register.
3. **From-scratch subdev.** Build `mysensor.ko` (adapt the chip-id + init to your actual sensor). Verify it appears in `media-ctl -p`.
4. **Capture raw.** `v4l2-ctl --stream-to=frames.raw --stream-count=10`. Convert a YUYV frame to PNG with ffmpeg; verify you see an image.
5. **Mainline OV5640.** Switch to `compatible = "ovti,ov5640"`. Configure full pipeline; capture; verify the built-in AE/AWB give a properly-exposed image.
6. **Resolution change.** With the OV5640, set QVGA, VGA, 720p. Note the frame-rate and bandwidth changes.
7. **Exposure control.** `v4l2-ctl --set-ctrl=exposure_auto=1` then manual exposure; observe brightness changes.
8. **GStreamer display.** Pipe the camera to the LCD via fbdevsink; live preview.

## 87.9  Pitfalls

- **MCLK not running before I²C.** The sensor's logic is clocked by MCLK; no MCLK = no I²C ACK. Enable the xclk in power-on *before* the chip-id read.
- **Reset/powerdown GPIO polarity.** Wrong polarity holds the sensor in reset; I²C-detect fails.
- **Pad format mismatch through the pipeline.** Sensor emits YUYV but CSI configured for RGB → no frames or garbage. Use `media-ctl` to verify each pad's format matches.
- **Parallel bus timing (hsync/vsync/pclk polarity).** Wrong polarity in the endpoint properties → torn/shifted/blank frames. Match the sensor datasheet.
- **Bandwidth exceeds CSI capability.** 5 MP at 30 fps is ~220 MB/s — i.MX6ULL can't sustain it. Use lower res or lower frame rate.
- **No GPU/VPU.** Software JPEG/H.264 on i.MX6ULL is slow. Budget for raw capture or low-fps encoded streams.
- **Sensor lens not focused.** Fixed-focus modules have a screw-adjustable lens; ship-from-factory focus may be off. Adjust for your working distance.
- **async subdev never binds.** If the of_graph link is wrong, the CSI bridge never finds the sensor; `/dev/video0` may not appear or has no source. Check `dmesg` for v4l2-async timeout warnings.

## 87.10  Going deeper

- **`drivers/media/i2c/ov5640.c`** — the production OV5640 driver. The mode tables are the bulk; the subdev ops match the from-scratch version's shape.
- **`drivers/staging/media/imx/`** — the i.MX CSI/IPU capture drivers.
- **`Documentation/userspace-api/media/v4l/`** — the V4L2 API reference.
- **`Documentation/driver-api/media/v4l2-subdev.rst`** — the subdev model.
- **`Documentation/admin-guide/media/imx.rst`** — i.MX media pipeline specifics.
- **OV5640 datasheet + software application notes (OmniVision)** — the register init sequences.
- **`v4l-utils`**: `v4l2-ctl`, `media-ctl`, `qv4l2`.
- **`yavta`** — a minimal V4L2 capture test tool, good for understanding the ioctl flow.

> Next chapter: **Chapter 88 — USB UVC cameras.** The opposite of bring-up effort: plug in a webcam and `uvcvideo` just works — but understanding the UVC protocol and bandwidth budgeting tells you *why* it works and when it won't.
