---
chapter: 54B
title: V4L2 + GStreamer for CSI cameras
part: VI — Driver development (supplementary v1.2)
estimated_pages: 14
status: draft
---

# Chapter 54B — V4L2 + GStreamer
**DMA** - Direct Memory Access. hardware moves data to or from memory without the CPU copying each byte.
MCU bridge: Think of DMA like the MCU DMA controller you used for UART or SPI, but with cache coherency, scatter-gather descriptors, and kernel ownership rules added.
**DDR** - external DRAM that must be configured and trained before most software can run from it.

> **What:** the **V4L2** (Video for Linux 2) subsystem — the kernel framework that abstracts video capture and output devices behind `/dev/videoN` — and **GStreamer**, the user-space pipeline framework that consumes V4L2 frames. We focus on the i.MX6ULL's **CSI** (Camera Serial Interface) for parallel cameras (OV5640, OV7725, GC2145), the only camera interface on this SoC.
>
> **Why:** every IP camera, dashcam, smart-doorbell, machine-vision product runs this stack. The complexity comes from V4L2's flexibility: sub-devices (the sensor, the CSI, the IPU) compose into pipelines that can be configured at runtime. Once the pipeline model clicks, the rest of the imaging stack reads easily.
>
> **Focus:** **the V4L2 subdev graph + GStreamer's `v4l2src`**. The kernel exposes the capture pipeline as a graph of sub-devices. GStreamer's `v4l2src` element grabs frames from `/dev/video0`. After that, the rest is image processing.
>
> **Tooling.** This chapter uses `v4l-utils` + `gstreamer1.0-tools` + base/good/bad plugins.
> - **Ubuntu-base (target):** `apt install v4l-utils gstreamer1.0-tools gstreamer1.0-plugins-base gstreamer1.0-plugins-good gstreamer1.0-plugins-bad`
> - **Buildroot:** `BR2_PACKAGE_V4L_UTILS=y BR2_PACKAGE_GSTREAMER1=y BR2_PACKAGE_GST1_PLUGINS_BASE=y BR2_PACKAGE_GST1_PLUGINS_GOOD=y BR2_PACKAGE_GST1_PLUGINS_BAD=y`
> **Buildroot** - a configuration-driven build system that produces a complete root filesystem and related images.
> - Full per-tool reference: [Userspace tooling appendix](../part5-rootfs/appendix-tooling.md).
> MCU bridge: Think of the rootfs as the firmware image's file-backed runtime environment. On an MCU you link everything into flash. On Linux, programs and config live in this mounted tree.
> **rootfs** - root filesystem, the directory tree mounted at / that contains /bin, /etc, /dev, and libraries.


## 54B.1  V4L2 architecture

```
   user-space:  GStreamer pipeline / OpenCV / your app
        │ open /dev/video0, ioctl, mmap, queue/dequeue buffers
        ▼
   ┌───────────────────────────────────────────────────────┐
   │   V4L2 core                                            │
   │   - Manages /dev/videoN chrdev                         │
   │   - VIDIOC_S_FMT, VIDIOC_REQBUFS, VIDIOC_QBUF, ...      │
   └───────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┴──────────────────────────┐
        ▼                                                ▼
   ┌──────────────┐                              ┌──────────────┐
   │ Video device │                              │ Sub-devices   │
   │ (capture)    │                              │ (sensors, etc)│
   │ - mxc_isi    │ ←── via media graph ────→    │ - ov5640      │
   │              │                              │ - csi-bridge  │
   └──────────────┘                              └──────────────┘
        │                                                │
        ▼                                                ▼
   DMA → DDR                                       I²C control
```

A V4L2 *device* is what user-space opens (`/dev/video0`). It connects to *sub-devices* — the sensor (OV5640) and the CSI bridge (i.MX CSI/ISI) — through a **media graph**. User-space sets the format (resolution, pixelformat) on both the video device and on each subdev.

## 54B.2  Device tree

```dts
&i2c2 {
    ov5640: camera@3c {
        compatible = "ovti,ov5640";
        reg = <0x3c>;
        pinctrl-names = "default";
        pinctrl-0 = <&pinctrl_csi1>;
        clocks = <&clks IMX6UL_CLK_CSI>;
        clock-names = "xclk";
        powerdown-gpios = <&gpio4 24 GPIO_ACTIVE_HIGH>;
        reset-gpios = <&gpio4 25 GPIO_ACTIVE_LOW>;

        port {
            ov5640_to_csi: endpoint {
                remote-endpoint = <&csi_from_ov5640>;
                clock-lanes = <0>;
                data-lanes = <1>;
            };
        };
    };
};

&csi {
    status = "okay";

    port {
        csi_from_ov5640: endpoint {
            remote-endpoint = <&ov5640_to_csi>;
        };
    };
};
```

Two things to notice:
- **Endpoints + remote-endpoint** form the graph. The OV5640's output endpoint links to the CSI's input endpoint, forming a media-controller pipeline.
- The OV5640 needs a master clock (XCLK) from the SoC, powerdown and reset GPIOs, and I²C for control.

## 54B.3  V4L2 user-space — the bare minimum

```c
int fd = open("/dev/video0", O_RDWR);

/* 1. Set the desired format */
struct v4l2_format fmt = {
    .type = V4L2_BUF_TYPE_VIDEO_CAPTURE,
    .fmt.pix = {
        .width = 640, .height = 480,
        .pixelformat = V4L2_PIX_FMT_YUYV,
        .field = V4L2_FIELD_NONE,
    },
};
ioctl(fd, VIDIOC_S_FMT, &fmt);

/* 2. Request buffers */
struct v4l2_requestbuffers reqbufs = {
    .count = 4,
    .type = V4L2_BUF_TYPE_VIDEO_CAPTURE,
    .memory = V4L2_MEMORY_MMAP,
};
ioctl(fd, VIDIOC_REQBUFS, &reqbufs);

/* 3. Map them, queue them */
struct v4l2_buffer buf;
void *mappings[4];
for (int i = 0; i < 4; i++) {
    buf = (struct v4l2_buffer){
        .type = V4L2_BUF_TYPE_VIDEO_CAPTURE,
        .memory = V4L2_MEMORY_MMAP,
        .index = i,
    };
    ioctl(fd, VIDIOC_QUERYBUF, &buf);
    mappings[i] = mmap(NULL, buf.length, PROT_READ|PROT_WRITE, MAP_SHARED, fd, buf.m.offset);
    ioctl(fd, VIDIOC_QBUF, &buf);
}

/* 4. Start streaming */
int type = V4L2_BUF_TYPE_VIDEO_CAPTURE;
ioctl(fd, VIDIOC_STREAMON, &type);

/* 5. Dequeue / process / re-queue loop */
while (1) {
    ioctl(fd, VIDIOC_DQBUF, &buf);
    process_frame(mappings[buf.index], buf.bytesused);
    ioctl(fd, VIDIOC_QBUF, &buf);
}
```

100 lines for a complete capture loop. Tedious but predictable.

For everyday work, use **libv4l2** or **GStreamer**, which wrap this.

## 54B.4  GStreamer in 30 seconds

GStreamer is a *pipeline* engine: elements connected with `!` pipes form a data flow.

```sh
# Display camera at 640x480
[root@pa-mini:~]# gst-launch-1.0 v4l2src device=/dev/video0 \
    ! video/x-raw,width=640,height=480,framerate=30/1 \
    ! videoconvert ! fbdevsink

# Record to file
[root@pa-mini:~]# gst-launch-1.0 v4l2src device=/dev/video0 \
    ! video/x-raw,width=640,height=480 \
    ! jpegenc ! avimux ! filesink location=out.avi

# Stream to network
[root@pa-mini:~]# gst-launch-1.0 v4l2src device=/dev/video0 \
    ! video/x-raw,width=640,height=480 \
    ! jpegenc ! rtpjpegpay ! udpsink host=192.168.1.100 port=5000
```

Elements:
- **`v4l2src`** — V4L2 capture source.
- **`videoconvert`** — color-space conversion (YUYV → RGB if needed).
- **`fbdevsink`** — output to `/dev/fb0`.
- **`jpegenc`** — JPEG-encode each frame.
- **`avimux`** — wrap in AVI container.
- **`rtpjpegpay`** — RTP packetize.

i.MX6ULL has no GPU/VPU, so video encoding is software (slow). Useful up to ~5–10 fps at QVGA. For higher framerates and resolutions you need a different SoC.

## 54B.5  Controls — exposure, gain, white balance

```sh
[root@pa-mini:~]# v4l2-ctl --list-ctrls
                     brightness 0x00980900 (int)    : min=0 max=255 step=1 default=128 value=128
                       contrast 0x00980901 (int)    : min=0 max=255 step=1 default=32 value=32
                     saturation 0x00980902 (int)    : min=0 max=255 step=1 default=64 value=64
...

[root@pa-mini:~]# v4l2-ctl --set-ctrl=brightness=200
[root@pa-mini:~]# v4l2-ctl --set-ctrl=exposure_auto=1     # manual
[root@pa-mini:~]# v4l2-ctl --set-ctrl=exposure_absolute=300
```

The sensor driver (ov5640) exposes a stack of controls. user-space tunes them. Auto-exposure and auto-white-balance are good enough for general use.

## 54B.6  Lab

1. **Bring up the OV5640.** DT, kernel config (`CONFIG_VIDEO_OV5640`), reboot, look for `/dev/video0`.
2. **Inspect the pipeline.** `media-ctl -p -d /dev/media0` shows the graph.
3. **GStreamer capture + display.** Run the launch line above. see your camera on the LCD.
4. **Save snapshots.** `v4l2-ctl --device /dev/video0 --stream-mmap=3 --stream-to=img.raw --stream-count=1`. Convert to PNG with ImageMagick.
5. **Auto-exposure off.** Set manual exposure. sweep values. observe brightness changes.
6. **Network stream + viewer.** Stream H.264 (software-encoded. slow) over UDP to a desktop running `vlc udp://@:5000`.

## 54B.7  Pitfalls

- **Sensor reset/powerdown GPIO polarity.** Wrong polarity → I²C-detect fails for the sensor.
MCU bridge: Think of Linux GPIO like the same pin set/reset block you used on STM32, but accessed through a kernel subsystem that owns numbering, direction, interrupts, and user-space exposure.
**GPIO** - General-Purpose Input/Output, a pin controlled as a digital input, output, or interrupt source.
- **Wrong XCLK rate.** OV5640 wants 12–27 MHz. outside that range, sensor doesn't enumerate.
- **Pixel format mismatch.** Sensor outputs YUYV, but you request RGB. GStreamer can convert, but it costs CPU.
- **Buffer underrun.** 4 buffers minimum for smooth capture. fewer cause dropped frames.
- **Concurrent open.** Only one user-space client per `/dev/video0`. Either GStreamer or your custom app, not both.
- **Frame size > VPU/memory budget.** 5 MP at 30 fps needs about 140 MB/s of memory bandwidth. This is close to the i.MX6ULL's practical limit.

## 54B.8  Going deeper

> **Driver choice:** Use the in-tree, maintained driver first.
> Use out-of-tree, spidev, or custom-driver paths only after you accept the kernel-version maintenance cost and document who owns updates.


- **`Documentation/userspace-api/media/`** — V4L2 user-space API.
- **`Documentation/userspace-api/media/v4l/`** — V4L2 user-space programming reference (the bible).
- **`drivers/media/i2c/ov5640.c`** — production OmniVision driver.
- **`drivers/staging/media/imx/`** — i.MX CSI/IPU drivers (historically out-of-tree).
- **<https://gstreamer.freedesktop.org/documentation/>** — GStreamer manual.
- **`v4l-utils` package** — `v4l2-ctl`, `media-ctl`, `qv4l2`.

> Next chapter: **Chapter 55 — USB gadget.** With the host side covered earlier, the gadget side turns the i.MX6ULL into a USB device: USB mass storage, USB serial, USB Ethernet, custom HID.
