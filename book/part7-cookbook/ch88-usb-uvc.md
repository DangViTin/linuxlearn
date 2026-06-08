---
chapter: 88
title: USB UVC cameras
part: VII — Device cookbook
estimated_pages: 14
status: draft
---

# Chapter 88 — USB UVC cameras

> **What:** USB webcams — the standardized **UVC** (USB Video Class) devices that the kernel's `uvcvideo` driver supports out of the box. Unlike the parallel-CSI sensors in Ch 87, a UVC camera is class-compliant. Plug it in, `/dev/video0` appears, and there is no driver to write. We cover the UVC protocol model, why it "just works," USB-2.0 bandwidth budgeting (the real constraint on i.MX6ULL), MJPEG vs YUYV vs H.264 modes, and the practical gotchas.
>
> **Why:** for many products, a USB webcam is the *easiest* camera — no sensor bring-up, no register tables, no CSI timing. The trade-off is USB bandwidth and the fact that the camera's quality is whatever the webcam vendor shipped. Knowing the bandwidth math tells you what resolution/frame-rate is achievable on the i.MX6ULL's USB-2.0 host.
>
> **Focus:** UVC is a class driver. The protocol is standardized, so one kernel driver covers every UVC camera. The hard part is no longer per-device driver code. It is bandwidth budgeting and format selection. A USB-2.0 bus is ~480 Mbps theoretical, ~320 Mbps practical. Uncompressed 1080p30 needs ~750 Mbps — impossible. MJPEG-compressed 1080p30 fits. Get the bandwidth math right and the rest is easy.
>
> **Tooling.** This chapter uses `v4l-utils`, `gstreamer1.0-tools` + plugins, `ffmpeg`.
> - **Ubuntu-base (target):** `apt install v4l-utils gstreamer1.0-tools gstreamer1.0-plugins-base gstreamer1.0-plugins-good gstreamer1.0-plugins-bad ffmpeg`
> - **Buildroot:** `BR2_PACKAGE_V4L_UTILS=y BR2_PACKAGE_GSTREAMER1=y BR2_PACKAGE_FFMPEG=y`
> **Buildroot** - a configuration-driven build system that produces a complete root filesystem and related images.
> - Full per-tool reference: [Userspace tooling appendix](../part5-rootfs/appendix-tooling.md).
> MCU bridge: Think of the rootfs as the firmware image's file-backed runtime environment. On an MCU you link everything into flash. On Linux, programs and config live in this mounted tree.
> **rootfs** - root filesystem, the directory tree mounted at / that contains /bin, /etc, /dev, and libraries.


## 88.1  Why UVC is different from CSI

| | Parallel CSI (Ch 87) | USB UVC |
|---|---|---|
| Driver | custom per sensor (~3700 lines) | `uvcvideo` handles all (class-compliant) |
| Bring-up | sensor registers, CSI timing, power seq | plug in, `/dev/video0` appears |
| Bus bandwidth | up to ~96 MHz parallel | USB-2.0 ~320 Mbps practical |
| Quality | you pick the sensor | whatever the webcam vendor shipped |
| Compression | raw (you encode in software) | camera does MJPEG/H.264 in hardware |
| Cost | sensor module $2–10 | webcam $10–50 |
| Power | ~100 mW | ~500 mW – 2.5 W (USB powered) |

The big advantage of UVC: the camera does the compression. A UVC camera with hardware MJPEG/H.264 offloads encoding from the i.MX6ULL (which has no VPU). For the i.MX6ULL, this often makes UVC the better choice. The webcam's silicon does the encoding, and the SoC only has to receive the compressed bytes.

## 88.2  The UVC protocol model

UVC is a USB device class (like HID for keyboards, mass-storage for drives). A UVC camera exposes:

- **A Video Control (VC) interface**: controls — brightness, exposure, focus, zoom, white balance.
- **One or more Video Streaming (VS) interfaces**: the actual frame data, with negotiated format + resolution + frame rate.

The camera advertises its capabilities in **descriptors** read at enumeration:
- Supported formats (YUYV / MJPEG / H.264 / NV12).
- Per-format supported frame sizes.
- Per-frame-size supported frame intervals (frame rates).

The `uvcvideo` driver parses these descriptors and exposes them through V4L2 — exactly the same `/dev/video0` interface as a CSI camera. From the application's view, a UVC camera and a CSI camera are identical. Both are V4L2 video devices. Only the bring-up differs.

### Isochronous vs bulk transfers

UVC video runs over USB **isochronous** transfers. These guarantee bandwidth but never retransmit — a dropped microframe is simply lost. The camera reserves a slice of each USB frame's bandwidth. This is why a UVC camera "claims" bandwidth on enumeration. plugging two high-res cameras into one USB-2.0 bus can fail because the combined isochronous bandwidth exceeds the bus.

Some cameras support **bulk** transfers (used by a few MJPEG cameras) — best-effort, retransmitted, but no bandwidth guarantee.

## 88.3  Bandwidth budgeting — the real constraint

USB-2.0 high-speed = 480 Mbps theoretical, ~320 Mbps usable for isochronous (after protocol overhead + the spec's 80% isochronous cap).

Uncompressed (YUYV, 16 bits/pixel) bandwidth:

| Resolution | @30 fps | @15 fps | Fits USB-2.0? |
|------------|---------|---------|---------------|
| 320×240 (QVGA) | 37 Mbps | 18 Mbps | ✓ |
| 640×480 (VGA) | 147 Mbps | 74 Mbps | ✓ (VGA30 tight but OK) |
| 1280×720 (720p) | 442 Mbps | 221 Mbps | ✗ @30, ✓ @15 |
| 1920×1080 (1080p) | 996 Mbps | 498 Mbps | ✗ |

MJPEG-compressed (typically ~10:1):

| Resolution | @30 fps MJPEG | Fits? |
|------------|---------------|-------|
| 640×480 | ~15 Mbps | ✓ easily |
| 1280×720 | ~44 Mbps | ✓ |
| 1920×1080 | ~100 Mbps | ✓ |

**Conclusion**: for anything above VGA on USB-2.0, use **MJPEG** (or H.264). Uncompressed YUYV is limited to VGA30 or 720p15. The i.MX6ULL has only USB-2.0 (no USB-3.0), so this ceiling is hard.

The CPU cost: receiving MJPEG is cheap (just DMA). *Decoding* MJPEG to raw (for processing or display) costs CPU — i.MX6ULL software JPEG decode does ~30 fps VGA, ~10 fps 720p. If you only need to *store* or *forward* the MJPEG (e.g., to a network client that decodes), no decode needed — full frame rate.
MCU bridge: Think of DMA like the MCU DMA controller you used for UART or SPI, but with cache coherency, scatter-gather descriptors, and kernel ownership rules added.
**DMA** - Direct Memory Access. hardware moves data to or from memory without the CPU copying each byte.

## 88.4  Bring-up — there isn't much

```
[root@pa-mini:~]# lsusb
Bus 001 Device 005: ID 046d:0825 Logitech, Inc. Webcam C270

[root@pa-mini:~]# dmesg | grep -i uvc
usb 1-1.2: new high-speed USB device number 5
uvcvideo: Found UVC 1.00 device Webcam C270 (046d:0825)
input: Webcam C270 as /devices/.../input/input5
usb 1-1.2: UVC device initialized.

[root@pa-mini:~]# ls /dev/video*
/dev/video0
```

Plug in, `/dev/video0` appears. List capabilities:

```
[root@pa-mini:~]# v4l2-ctl --device /dev/video0 --list-formats-ext
ioctl: VIDIOC_ENUM_FMT
    Index: 0  Type: Video Capture  Pixel Format: 'YUYV'
        Size: Discrete 640x480
            Interval: Discrete 0.033s (30.000 fps)
        Size: Discrete 1280x720
            Interval: Discrete 0.133s (7.500 fps)
    Index: 1  Type: Video Capture  Pixel Format: 'MJPG' (compressed)
        Size: Discrete 1280x720
            Interval: Discrete 0.033s (30.000 fps)
        Size: Discrete 1920x1080
            Interval: Discrete 0.040s (25.000 fps)
```

Notice: YUYV maxes at 720p7.5 (bandwidth-limited), but MJPG does 720p30 and 1080p25 (compression fits the bus). The camera's descriptors tell you exactly what's possible.

Capture:

```
# Raw YUYV VGA
v4l2-ctl --device /dev/video0 --set-fmt-video=width=640,height=480,pixelformat=YUYV \
    --stream-mmap=3 --stream-count=30 --stream-to=vga.raw

# MJPEG 720p (frames are already JPEG — just save them)
v4l2-ctl --device /dev/video0 --set-fmt-video=width=1280,height=720,pixelformat=MJPG \
    --stream-mmap=3 --stream-count=1 --stream-to=frame.mjpg

# GStreamer: MJPEG → decode → display
gst-launch-1.0 v4l2src device=/dev/video0 ! image/jpeg,width=1280,height=720,framerate=30/1 \
    ! jpegdec ! videoconvert ! fbdevsink
```

## 88.5  Controls

UVC cameras expose standardized controls:

```
[root@pa-mini:~]# v4l2-ctl --device /dev/video0 --list-ctrls
                     brightness 0x00980900 (int)    : min=0 max=255 default=128 value=128
                       contrast 0x00980901 (int)    : min=0 max=255 default=32 value=32
                     saturation 0x00980902 (int)    : min=0 max=255 default=32 value=32
        white_balance_automatic 0x0098090c (bool)   : default=1 value=1
                  power_line_freq 0x00980918 (menu)  : ...
                exposure_auto    0x009a0901 (menu)   : ...
            exposure_time_absolute 0x009a0902 (int)  : min=1 max=10000 value=166
                     focus_auto   0x009a090c (bool)   : ...

[root@pa-mini:~]# v4l2-ctl --set-ctrl=brightness=200
[root@pa-mini:~]# v4l2-ctl --set-ctrl=exposure_auto=1     # manual
[root@pa-mini:~]# v4l2-ctl --set-ctrl=exposure_time_absolute=500
```

These map to UVC's standardized control requests. `uvcvideo` translates V4L2 control IDs to USB control transfers. Not every camera supports every control — `--list-ctrls` shows what's available.

## 88.6  When UVC doesn't "just work"

- **"Driver needed" cameras**: some cheap cameras claim UVC but ship non-compliant descriptors, or need a vendor driver (rare these days). `dmesg` shows enumeration errors.
- **Bandwidth contention**: a USB WiFi dongle (Ch 92) + a UVC camera on the same USB-2.0 bus compete. The camera may fail to start, or the WiFi throughput drops. The i.MX6ULL has 2 USB controllers — put bandwidth-heavy devices on separate ones.
- **Power**: a 2.5 W webcam on a bus-powered hub may brown out. Use a powered hub or wire the camera's VBUS to a beefier rail.
- **H.264 UVC cameras**: some webcams output H.264. `uvcvideo` exposes it as a pixel format. You save the H.264 stream directly (no decode needed for storage/forwarding).
- **Multiple `/dev/videoN` per camera**: many UVC cameras expose two nodes — one for video, one for metadata. The video one is usually the lower-numbered.

## 88.7  USB gadget side — being a UVC camera

The inverse: making the i.MX6ULL *appear* as a webcam to a host PC (Ch 55's USB gadget). The `uvc` gadget function streams frames the i.MX6ULL generates (e.g., from a CSI camera) to a host as a standard webcam. Useful for "camera-over-USB" products. The ConfigFS `uvc` function (Ch 55.3) does this.

## 88.8  Lab

1. **Plug in a UVC webcam.** Verify `lsusb`, `dmesg`, `/dev/video0`.
2. **List capabilities.** `v4l2-ctl --list-formats-ext`. Note which resolutions support which formats and frame rates. Map them to the bandwidth table.
3. **Capture YUYV VGA.** Save 30 frames. convert one to PNG. verify the image.
4. **Capture MJPEG 720p.** Save frames. they're already JPEG — open directly.
5. **Bandwidth limit test.** Try YUYV 720p30. observe it fail or fall back (bandwidth exceeded). Switch to MJPEG 720p30. observe success.
6. **Controls.** Adjust brightness, exposure, focus. observe changes in captured frames.
7. **Contention.** Add a USB WiFi dongle on the same bus. stream the camera + run iperf3. observe degradation. Move the camera to the second USB controller. observe improvement.
8. **Network stream.** GStreamer: camera MJPEG → RTP → UDP to a desktop running VLC. No decode on the i.MX6ULL (forward the JPEG directly).

## 88.9  Pitfalls

- **Uncompressed above VGA on USB-2.0.** Won't fit. Use MJPEG. The bandwidth table is the design constraint.
- **Software decode is the bottleneck, not the bus.** Receiving MJPEG is cheap. decoding it to raw for display/processing on the GPU-less i.MX6ULL is slow. Forward the MJPEG undecoded where possible.
- **Bus-power brownout.** High-res webcams draw 1–2.5 W. Bus-powered hubs may not deliver it. Use a powered hub or dedicate a USB port with a strong VBUS rail.
- **Two bandwidth-heavy USB devices on one controller.** Camera + WiFi/Ethernet contend. Spread across the i.MX6ULL's two USB controllers.
- **`uvcvideo` quirks.** Some cameras need quirk flags (`uvcvideo.quirks=`). `dmesg` hints at enumeration issues. The `uvcvideo` source has a quirks table for known-bad cameras.
- **Frame drops on isochronous.** Isochronous has no retransmission. a missed USB microframe = a dropped/corrupt frame. Under heavy system load, frames drop silently. PREEMPT_RT (Ch 52A) helps for deterministic capture.
- **MJPEG is not a true video codec.** It is per-frame JPEG with no compression between frames. Typical ratio is 10:1, against H.264's 100:1. For bandwidth-critical streams, pick an H.264 UVC camera.

## 88.10  Going deeper

> **Driver choice:** Use the in-tree, maintained driver first.
> Use out-of-tree, spidev, or custom-driver paths only after you accept the kernel-version maintenance cost and document who owns updates.


- **`drivers/media/usb/uvc/`** — the `uvcvideo` driver. `uvc_driver.c` has the quirks table.
- **`Documentation/userspace-api/media/v4l/`** — V4L2 API (same as for CSI cameras).
- **USB Video Class specification (usb.org)** — the UVC standard.
- **`v4l-utils`**: `v4l2-ctl`, `qv4l2`, `v4l2-compliance` (tests a camera's V4L2 conformance).
- **`drivers/usb/gadget/function/f_uvc.c`** — the UVC *gadget* function (being a camera).
- **`guvcview`, `cheese`** — desktop tools for testing UVC cameras.

---

> **End of Group I — Cameras (Ch 87–88).** Parallel CSI (custom driver, you control the sensor) vs USB UVC (class-compliant, plug-and-play, camera does compression). On the GPU/VPU-less i.MX6ULL, UVC's hardware compression often wins for anything above VGA.

> Next chapter: **Chapter 89 — I²S audio codecs.** Group J (Audio) — the codec chips (WM8960, SGTL5000, ES8388, TLV320) that give the i.MX6ULL line-in/line-out/headphone/mic, and the ASoC machine driver that wires them up.
> **ASoC** - ALSA System-on-Chip, the embedded audio layer that connects CPU audio ports, codecs, and board wiring.
