---
chapter: 55H
title: RGB-to-HDMI bridge (sii902x)
part: VI — Driver development (supplementary v1.1)
estimated_pages: 10
status: draft
---

# Chapter 55H — RGB-to-HDMI bridge (sii902x)

> **What:** the **Silicon Image SiI902x** family of RGB-parallel-to-HDMI transmitter chips, and the kernel's **DRM bridge** subsystem. The i.MX6ULL has no native HDMI; an SiI9022/SiI9024 chip on the LCDIF parallel output gives you HDMI. The mainline `sii902x.c` DRM bridge driver handles config and EDID parsing.
> **Why:** any product that needs an external display (HMI, kiosk, signage) usually wants HDMI compatibility. SiI902x is a tiny, ~$2 chip that takes 24-bit RGB + HSYNC/VSYNC/PCLK and outputs HDMI 1.4 at up to 1080p60. Drops onto any i.MX6ULL board.
> **Focus:** **the bridge concept**. A DRM "bridge" sits between a CRTC (LCDIF) and a connector (HDMI port). Linux's DRM framework chains bridges automatically; you describe the chain in DT and the driver activates appropriately.

## 55H.1  Hardware

SiI902x has:
- **Input**: 24 parallel RGB + HSYNC + VSYNC + PCLK + DE. From i.MX6ULL LCDIF.
- **Output**: 4 differential pairs + DDC (HPD + I²C). To HDMI connector.
- **I²C control**: 0x39 typically.
- **HPD (Hot Plug Detect)** interrupt: tells the bridge when an HDMI cable is attached.

Connect LCDIF parallel out → SiI902x in, HDMI cable → SiI902x out, I²C2 + HPD-IRQ → host. The bridge handles EDID negotiation with the sink (TV/monitor).

## 55H.2  Device tree

```dts
&i2c2 {
    sii902x: hdmi@39 {
        compatible = "sil,sii9022";
        reg = <0x39>;
        reset-gpios = <&gpio2 5 GPIO_ACTIVE_LOW>;
        interrupt-parent = <&gpio2>;
        interrupts = <6 IRQ_TYPE_EDGE_FALLING>;
        #sound-dai-cells = <0>;

        ports {
            #address-cells = <1>;
            #size-cells = <0>;

            port@0 {
                reg = <0>;
                sii902x_in: endpoint {
                    remote-endpoint = <&lcdif_out>;
                };
            };

            port@1 {
                reg = <1>;
                sii902x_out: endpoint {
                    remote-endpoint = <&hdmi_connector_in>;
                };
            };
        };
    };
};

&lcdif {
    status = "okay";
    port {
        lcdif_out: endpoint {
            remote-endpoint = <&sii902x_in>;
        };
    };
};

hdmi_connector: hdmi-connector {
    compatible = "hdmi-connector";
    type = "a";
    port {
        hdmi_connector_in: endpoint {
            remote-endpoint = <&sii902x_out>;
        };
    };
};
```

Three nodes form the graph: LCDIF → SiI902x → HDMI-connector. DRM bridge chain wires them.

## 55H.3  How it works

At boot:
1. SiI902x's `sii902x_probe` registers a DRM bridge.
2. LCDIF's DRM driver sees a downstream bridge instead of a panel.
3. SiI902x's `attach` callback runs; it queries the connector for HPD state.
4. If HPD is asserted (cable plugged), it reads EDID from the sink (via DDC I²C on the HDMI connector).
5. Available modes derived from EDID become valid DRM modes.

`modetest` shows the modes:

```
[root@pa-mini:~]# modetest -M mxsfb
Connectors:
id      encoder status          name            size (mm)       modes   encoders
42      40      connected       HDMI-A-1        598x336         18      40
        modes:
            #0 1920x1080 60.00 1920 2008 2052 2200 1080 1084 1089 1125 148500 flags: phsync, pvsync; type: preferred
            #1 1280x720 60.00 1280 1390 1430 1650 720 725 730 750 74250 flags: phsync, pvsync;
            ...
```

Set a mode:

```
[root@pa-mini:~]# modetest -M mxsfb -s 42:1920x1080
```

But: i.MX6ULL's LCDIF clocks ceilings at ~80 MHz pixel clock. 1080p60 is 148.5 MHz; doesn't work. Practical max on i.MX6ULL via SiI902x is 720p (74.25 MHz). 480p, 576p, 720p all work.

## 55H.4  Audio over HDMI

SiI902x also carries audio. With `#sound-dai-cells = <0>;`, the chip exposes an audio DAI; build an ASoC machine driver (Ch 53) that connects SAI → SiI902x → HDMI. Most products skip this and use HDMI for video only.

## 55H.5  Lab

1. **Add SiI902x to your DT.** Boot; check `dmesg | grep sil` for "SiI902x bridge ready" or similar.
2. **Plug an HDMI monitor.** `modetest -M mxsfb -c` lists connected outputs; HDMI-A-1 should be `connected` with valid modes.
3. **Set 720p.** `modetest -M mxsfb -s <id>:1280x720`. Verify monitor displays.
4. **`/dev/fb0` painting.** Default fbdev emulation shows it; `cat /dev/urandom > /dev/fb0` paints noise on the HDMI output.
5. **HPD detection.** Unplug cable; observe disconnected event in dmesg / `modetest -c`.
6. **Try 1080p.** Confirm it fails (LCDIF pixel clock limit). Read drm.debug=15 dmesg for the rejection.

Commit code to `code/ch55H-hdmi/`.

## 55H.6  Pitfalls

- **No HPD wiring.** Bridge thinks nothing connected; mode list is empty.
- **Reset-gpios polarity wrong.** Chip held in reset forever.
- **DDC pull-ups missing.** EDID read fails. Schematic check.
- **Pixel clock > 80 MHz.** LCDIF chokes. Stay ≤ 720p on i.MX6ULL.
- **No frame-rate match.** Some monitors require specific timings; the EDID list filters out invalid ones but check the kernel debug output.
- **Output looks blank but kernel says "modeset OK."** Often the HDMI receiver is using a different format than the bridge is sending. SiI902x defaults to RGB; some old TVs want YCbCr. Force RGB via property if needed.

## 55H.7  Going deeper

- **`drivers/gpu/drm/bridge/sii902x.c`** — the SiI902x DRM bridge driver.
- **`Documentation/gpu/drm-kms.rst`** — KMS bridge chain.
- **SiI9022 datasheet** — register map, EDID handling, audio config.

> Next chapter: **Chapter 55I — Rust-for-Linux.** A small kernel-module written in Rust, demonstrating the upcoming second kernel language.
