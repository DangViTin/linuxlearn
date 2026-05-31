# Part VIIb — Cookbook (Displays/Cameras/Audio/WiFi/BT): Review

## Cross-cutting observations

- **Almost no explicit MCU contrast.** Across all 16 chapters the only direct STM32/MCU comparison is one passing nod ("like a cellular AT modem"). For a reader who has done LCDs on FSMC, cameras on DCMI, I2S on STM32 SAI, WiFi via ESP8266 AT, this is the highest-leverage analogy and it is consistently missing. Each chapter intro should include 2–4 lines: "On STM32 you would X (FSMC/DCMI/SAI/AT-WiFi); on Linux it is the same idea but with [framework] in the middle, which buys you Y but costs Z."
- **No system-level ASCII figures.** The chapters draw small per-peripheral diagrams (wire pinouts, register packets) but never the *Linux stack layering* the reader actually needs to internalize. Required figures: (a) DRM CRTC/encoder/connector/panel → mxsfb→ panel-simple wiring (Ch 82–85); (b) V4L2 sensor-subdev → CSI bridge → video-node media graph with pad-format propagation (Ch 87); (c) ASoC machine ↔ codec_dai ↔ cpu_dai (SAI) ↔ DAPM graph (Ch 89–90); (d) wpa_supplicant ↔ nl80211 ↔ cfg80211 ↔ driver / mac80211 layering (Ch 91–94); (e) HCI ↔ kernel BT ↔ bluetoothd ↔ D-Bus app (Ch 95–97). Each appears in prose but never as a picture, even though Part VI presumably set this up.
- **Knowledge prerequisites are referenced but never refreshed.** Many chapters say "as in Ch 53/55E/55G" and assume the reader carries the framework concept fresh. Cookbook chapters should re-state the one or two concepts they depend on in a 3–5 line callout ("DAPM, from Ch 53: ..."), then build on top. A reader skimming Part VII out of order will be lost.
- **`status: draft` and `estimated_pages` everywhere.** Either remove or commit to a meaning. Some page counts seem optimistic for the depth shown (Ch 84 says 16 pages but is mostly a "this doesn't really work on i.MX6ULL" disclaimer).
- **Many "from scratch" drivers omit error-path cleanup, locking, suspend/resume, and `MODULE_AUTHOR`/`MODULE_DESCRIPTION`.** They are explicitly minimal but readers will copy them. Add at least one comment per driver: "production code must add: error rollback in probe, runtime_pm hooks, locking around shared state." Some explicitly do (Ch 87), but most do not.
- **The `.remove` callback signature has changed in recent kernels (returns void in 6.11+).** Several chapters use `static int xxx_remove(...)` and others use `static void`. Inconsistent. Pick a kernel target and state it once.
- **`dev_err_probe` is used but never explained.** It appears in Ch 83/85/86/87 with no introduction. A one-line gloss ("returns the err while deferring nicely if -EPROBE_DEFER") would help.
- **Volume prices and BOM costs are scattered all over.** Useful for the practising engineer but verge on the dated. Add a once-only note: "prices Q1 2026, indicative."
- **Lab sections are good and consistent — keep them.** They turn each chapter into a real recipe, which matches the cookbook framing.
- **Choice between fbdev and DRM is treated inconsistently.** Ch 82/83/84 are DRM-first (correct, modern), Ch 85 says "DRM is modern, fbdev is more illustrative" and then writes an fbdev driver. The justification is fine but the reader is left wondering whether to write fbdev for new code. Add a one-line policy: "For new code: DRM unless the device is 1-bit + frame-buffer-style. The fbdev path is shown here for didactic reasons; mainline `ssd130x` is DRM."
- **The book consistently uses `[root@pa-mini:~]#` prompts. Good** — keep this consistency, but a reader on QEMU/another board may be confused; one footnote in Ch 82 explaining "pa-mini" suffices.
- **i.MX6ULL specificity is sometimes glossed.** Ch 82, 84, 87 are pretty clear about limits; Ch 89/90/91 should probably mention SAI vs SSI peripheral naming on i.MX6ULL (the chip has both; the audio chapters say only "SAI"), and Ch 87 should note that the i.MX6ULL CSI has *only* 8 data lines (CSI_DATA00–07), reinforcing why 10/12-bit RAW from OV5640 is moot.

## Ch82 — RGB LCD

### MCU-engineer friendliness
- Add an intro paragraph contrasting against STM32 LTDC: "On an STM32F7/H7 with LTDC you DMA a framebuffer to RGB pins; on Linux mxsfb (DRM driver) does the same DMA, but a *panel driver* describes the timing instead of you typing it into LTDC registers, and DRM owns the buffer allocation." The reader has done this on bare metal and will click immediately.

### Missing examples / figures
- The LCDIF clocking diagram is asked for in the brief — none present. Show: PLL5_VIDEO → LCDIF_PIX clock divider → LCDIF → PCLK on pad. Helps explain *why* ~70 MHz is the ceiling.
- A picture of the DRM pipeline (`drm_panel ↔ drm_connector ↔ drm_encoder ↔ drm_crtc ↔ mxsfb` + `of_graph` edges) would replace ~200 words. It is the central concept of the chapter.

### Insufficient depth
- §82.4 ("How `panel-simple` works internally") is too brief — half a page of pseudocode and stops. Either go deeper (how `drm_panel_funcs` is called by which DRM helper, the prepare/enable/disable/unprepare ordering and what the encoder does between them), or trim it and lean on §82.5's full driver.

### Technical errors
- `clock-frequency = <51200000>; hactive=1024 hfront=210 hback=46 hsync=1 vactive=600 vfront=22 vback=23 vsync=1` → h_total=1281, v_total=646, pclk required = 1281·646·60 = 49.65 MHz, not 51.2 MHz. The chapter notes the discrepancy but reports `51200000` as the binding value — DRM will either round the actual PCLK to the nearest the PLL can produce or refuse. Worth a sentence: "the kernel computes the required pclk from the timings, the `clock-frequency` value is informative." This is exactly the gotcha the brief is asking for.
- `pixelclk-active = <0>; /* latch on falling edge */` — DT property here is `pixelclk-active`, which is the *invert* of the panel's sample edge. Worth confirming against `Documentation/devicetree/bindings/display/panel/panel-timing.yaml` and re-stating which polarity = "latch on falling": the wording "active = 0 means latch on falling edge" is correct for `pixelclk-active`, but DRM/panel-simple uses `DRM_BUS_FLAG_PIXDATA_DRIVE_NEGEDGE` in `bus_flags`. Mention that the DT property and the DRM bus flag must agree (and that the kernel sometimes silently inverts).
- "ATK10261 71 MHz pclk exceeds safe LCDIF range (~70 MHz)" — the IMX6ULL RM does not give an explicit LCDIF pclk ceiling in the chapters I scanned; common community guidance is ~50–70 MHz depending on SoC speed grade. Soften to "practically capped around 50–70 MHz depending on speed grade and CCM configuration" with a reference.
- `bits-per-pixel = <24>; bus-width = <24>;` are *legacy* `display-timings` properties; the modern `panel-dpi` binding uses `bus-format = "rgb888"` (or `MEDIA_BUS_FMT_RGB888_1X24`) at the endpoint, not bus-width. The chapter shows both but doesn't flag which is current — mainline `panel-dpi.yaml` lists `bus-width` as the DT property still, but production code increasingly uses `data-mapping` and bus-format. Verify against a current binding doc and clarify.

### Knowledge prerequisites missing
- The reader needs to know what a `drm_panel` is before §82.4. A 2-line refresher ("a `drm_panel` is a kernel object representing an external panel; the encoder calls into it for prepare/enable/get_modes — Ch 53 introduced this") helps.
- §82.5 approach 3 uses `drm_panel_of_backlight` without explaining what it does (it walks the `backlight` phandle and returns the registered `backlight_device`). Two lines.

### Other
- "Backlight forgotten" pitfall is great. Move it into a callout at the top of §82.6 since it is the #1 first-bring-up symptom.
- Lab step 4 ("deliberately wrong porch") is excellent — keep.
- Approach 3 driver: `mypanel_remove` is shown without freeing the backlight; `drm_panel_of_backlight` uses devm under the hood, so this is fine, but say so.

## Ch83 — SPI LCD

### Readability
- "Drawing a pixel rectangle" pseudocode (§83.2) mixes prose and code in a confusing way. Lift it into a clear C-like block: command then data with explicit DC-toggle markers.
- "What we'd add for production: rotation handling (MADCTL variations)..." — the abrupt segue from §83.4 to §83.5 is choppy; tie them with one sentence: "In production you would not write the C above — you would use the firmware-blob path described next."

### MCU-engineer friendliness
- The reader has driven an ST7789 from STM32 with HAL_SPI + a manual init array. State it: "On STM32 you wrote a 300-line `st7789_init()` and a `draw_pixel()` that pushed bytes to SPI. On Linux that init array goes into the kernel's `mipi_dbi` helper (or a firmware blob), and `draw_pixel()` becomes `cat foo > /dev/fb0` because the DRM helper does dirty-rect tracking for you."

### Missing examples / figures
- A picture of MOSI/SCLK/DC/CS with the byte stream for `0x2A, 0x00, 0x00, 0x00, 0xEF` (CASET 0..239) with DC low/high annotated would cement the protocol better than the table.

### Insufficient depth
- §83.3 lists the `mipi_dbi` helper functions but does not show what `mipi_dbi_fb_dirty` actually does (the dirty-rect → CASET/RASET/RAMWR walk). Since this is the "what does the framework do for me" payoff, half a page of the helper's pseudocode would be excellent — it is the canonical example of how a Linux framework saves you work.

### Technical errors
- "Sitronix ST7789 max SPI clock ~62 MHz" — the ST7789 datasheet caps writes around 62.5 MHz (16 ns SCK cycle) but most modules in the wild fail above ~40 MHz. Caveat: "datasheet 62 MHz, practical 20–40 MHz, varies per module and PCB."
- `DRM_SIMPLE_MODE(240, 240, 28, 28)` macro signature is `DRM_SIMPLE_MODE(hdisplay, vdisplay, width_mm, height_mm)` — correct, just note this for the reader.
- `mipi_dbi_dev_init` is shown but its current signature requires `rotation` argument (`mipi_dbi_dev_init(dbidev, funcs, mode, rotation)`) on recent kernels, with no `bpp` parameter. The example passes `0` as the last arg which would be `rotation=0`; OK but worth a comment "rotation; we ignore the DT property here."
- "DRM headers version mismatch... `mipi_dbi_dev_init` signature changed across 5.x/6.x" — true and important. State the *target* kernel for the example (likely 6.6+ given `drm_fbdev_generic_setup`, which has itself been replaced by `drm_fbdev_dma_setup` in 6.11+). Pick one and pin it.

### Other
- "Mainline driver `drm/tiny/st7789v` (via panel-mipi-dbi)" — there is no `st7789v.c` standalone driver in mainline; ST7789-based panels are handled via `panel-mipi-dbi-spi` + a firmware blob (e.g., for Pimoroni HyperPixel). Correct the table footnote.
- INVON pitfall is excellent — keep.
- Lab 7 ("Switch to panel-mipi-dbi with a firmware init blob") needs a pointer to the `mipi-dbi-cmd` source (`Documentation/gpu/drivers/drm-panel.rst` and the kernel's `tools/mipi-dbi-cmd/` if present, or the linux-firmware repo's example).

## Ch84 — QSPI LCD

### Readability
- The chapter's honesty about "i.MX6ULL is not a great QSPI display host" is refreshing but the chapter then doesn't quite know whether it is a real cookbook recipe or a survey. Reframe the intro: "This chapter is a *survey* (concepts + when to consider QSPI) rather than a bring-up recipe — i.MX6ULL is not a good host. Read it to recognize when you have outgrown the i.MX6ULL."

### MCU-engineer friendliness
- The reader has used QSPI on STM32 for NOR flash (XIP). The analogy is right there: "STM32 QSPI is also flash-centric (Indirect-Write mode can stream display data, but the controller's CCR fields are awkward for displays — same problem as i.MX6ULL)."

### Missing examples / figures
- An ASCII showing how `SPI_MEM_OP_CMD(1lane) + SPI_MEM_OP_ADDR(1lane) + SPI_MEM_OP_DATA_OUT(4lane)` maps to the four IO lines vs single-lane writes would clarify the §84.4 description.

### Insufficient depth
- The chapter sidesteps a from-scratch driver because i.MX6ULL doesn't support it. Fair, but at least show the *delta* from Ch 83: which one function in Ch 83's `myst7789` would change (the SPI sync call becomes a `spi_mem_exec_op` with `.buswidth = 4` on the data phase) and that's it. Three or four lines is enough.

### Technical errors
- §84.2 lane-mapping diagram: `IO3 ─ b7 b3`, `IO2 ─ b6 b2`, etc. — the bit-to-lane mapping isn't part of QSPI itself, it depends on the controller. Display QSPI controllers often pack as: each *nibble* per clock = (IO3 IO2 IO1 IO0) = (b7 b6 b5 b4) first clock, (b3 b2 b1 b0) next. The diagram you drew implies `IO3 = b7 then b3` across two clocks, which is the *opposite* nibble order. Verify against ST77916 datasheet and fix; this is exactly the "wrong lane mapping" pitfall §84.7 warns about, so getting it right here matters.
- "i.MX8M Mini (with FlexSPI)" — correct, but worth noting that FlexSPI on i.MX8M Mini still has rough mainline display support; the SoC where this really works is i.MX RT1170 (NXP MCU world) or RP2040 (PIO) — clarify the better-target advice.

### Other
- The chapter could end at "for i.MX6ULL, just don't" rather than spend half the page on i.MX8M speculation. Two paragraphs total of "if you must, here's the spi_mem approach on a capable SoC" is enough.

## Ch85 — OLED & e-paper

### Readability
- "OLED is a page-addressed bitmap; e-paper is a two-buffer LUT-driven waveform machine" — excellent contrast, keep.
- "[...the chip's logic is clocked by MCLK...]" reuse from later chapter — OK; consistency is good.

### MCU-engineer friendliness
- The reader has bit-banged SSD1306 from STM32 via I²C with `_init[]` arrays just like this. Say so explicitly: "Compared to your STM32 driver, the *protocol code is identical* — the same 0x8D 0x14 charge-pump command. The Linux difference is `fb_deferred_io` doing the batched flush so user-space writes don't saturate I²C."

### Missing examples / figures
- A pixel-layout diagram (8 pages × 128 cols, bit0=top, bit7=bottom, byte 0 = column 0 rows 0–7) drawn properly as ASCII would prevent the "scrambled image" pitfall.
- A timeline figure: write → vmem → fb_deferred_io callback fires → 1 KB I²C burst → screen. Shows where the 33 ms batching window sits.

### Insufficient depth
- §85.6 (SSD1680 e-paper) describes the model but does not show *any* code — even a stub. A 30-line `epaper_update()` showing CASET-like commands + waveform LUT trigger + BUSY wait would be in keeping with the chapter's "show the structure" approach. As is, e-paper feels like an afterthought.

### Technical errors
- `fb_deferred_io.delay = HZ / 30` — `HZ` on most i.MX kernels is 100, so this is 3 jiffies ≈ 30 ms. For HZ=250 this becomes 8 ms. Use the more portable `msecs_to_jiffies(33)` and note it.
- `info->screen_buffer = m->vmem;` — `screen_buffer` is used for vmalloc'd buffers; for deferred-io on a sysram fb you typically also set `info->fix.smem_start = (unsigned long) m->vmem` and a `screen_size`. Verify against `Documentation/fb/deferred_io.rst`.
- "SSD1680 RAM model: dual buffer + LUT" — the SSD1680 uses two RAM buffers ("BW RAM" and "Red RAM" for tricolor, or "previous" + "current" for monochrome differential refresh). The text conflates the BW/Red dual-buffer with the differential-update dual-buffer. Clarify which buffer pair you mean.
- `i2c_master_send(m->client, buf, len+1)` with `buf` from kmalloc — fine, but `i2c_master_send` requires GFP_ATOMIC vs GFP_KERNEL depending on context; for an fbdev write path you may be in atomic context if called from a tasklet. The deferred-io callback runs in workqueue context (process), so GFP_KERNEL is fine, but mention it.

### Knowledge prerequisites missing
- The reader has not used `fb_deferred_io` before. Introduce the concept properly (one paragraph): the kernel mmaps your vmem to user-space write-protected; the page-fault handler queues dirty pages; a workqueue calls your callback after `delay` jiffies. Without this the mechanism feels magic.

### Other
- The SH1106 "off-by-2" pitfall is gold — many real engineers have hit this. Keep.
- Lab 3 ("comment out charge-pump command, observe black screen") is excellent pedagogy. Keep.

## Ch86 — Touch input ICs

### Readability
- "A display without touch is a monitor; with touch it's an interface" — keep, it's good.
- §86.4 "Each measurement is a 3-byte SPI transaction" → the control-byte bit breakdown is hard to read inline; render as a table.

### MCU-engineer friendliness
- The reader has done XPT2046 on STM32 with `HAL_SPI_TransmitReceive` and a software calibration table. Say: "The Linux structure is exactly your STM32 version split in two — the SPI read+median is the same, but instead of mapping ADC→pixel in your loop, you report the raw ADC to `input_dev` and `tslib`/`libinput` does the calibration."

### Missing examples / figures
- A wiring diagram: 4-wire resistive panel (X+, X-, Y+, Y-) → XPT2046 → SPI. Many readers haven't seen a resistive overlay before.
- The 3x2 affine transform `pixel_x = a·adc_x + b·adc_y + c` — show an actual measured set of (adc, pixel) tuples and the resulting matrix, even if approximated. Reader will want to know "what does ts_calibrate's `/etc/pointercal` file actually look like".

### Insufficient depth
- "PENIRQ during sampling" pitfall is mentioned but the from-scratch driver does *not* mask PENIRQ during sampling — it polls the GPIO. That's the wrong pattern for production and the reader copying this will get spurious IRQs. At least show how the mainline `ads7846` masks PENIRQ around the SPI transaction (`disable_irq_nosync` / `enable_irq` pattern).

### Technical errors
- `xp_read_filtered` uses `msleep(10)` in an IRQ thread loop — that's 100 Hz sampling. Fine, but mention that real touch needs ~125–200 Hz to feel smooth and 1 kHz for stylus work. Mainline `ads7846` uses an hrtimer for higher rates.
- `IRQF_TRIGGER_FALLING | IRQF_ONESHOT` then inside the thread loop polling `gpiod_get_value(x->pen_gpio) == 0` until PENUP — that's polling the GPIO from a sleeping thread. Works but is awkward; the more idiomatic pattern is one IRQ → one report → re-enable IRQ → wait for next falling edge. Note this.
- `input_set_abs_params(..., ABS_X, 0, MAX_ADC, 0, 0)` — values 4 and 5 are `fuzz` and `flat`. The chapter passes 0 for both; common practice is `fuzz=8` to swallow ADC noise. Mention this.
- MPR121 datasheet — NXP/Freescale yes, but make it clear MPR121 originated at Freescale (now NXP) and is *not* TI.

### Other
- "Resistive touch needs calibration, always" — perfect, very practical.
- Lab 7 ("Compare to GT911") implies Ch 55G covers GT911; double-check that reference exists.

## Ch87 — CSI cameras

### Readability
- "The driver model is the most elaborate in the kernel" — bold claim; soften or qualify ("among the most" or "more involved than most platform drivers").
- §87.4 has long mode-table snippets — break them with prose; the reader's eyes glaze.

### MCU-engineer friendliness
- The reader has used DCMI on STM32 with a sensor's init table. *That is exactly the OV5640 init.* Say so: "The init array in §87.4 is identical to what you'd write for STM32 DCMI — same registers, same OmniVision reference code. The Linux difference is *who calls it*: the `v4l2_subdev`'s `s_stream(1)` op, invoked from user-space via VIDIOC_STREAMON. Everything else (frame DMA, format negotiation) is the same hardware, just wrapped in V4L2."

### Missing examples / figures
- The brief explicitly asks for a CSI parallel-data → IPU → memory pipeline figure. None present. Show: sensor → CSI pads → CSI capture → DMA → DRAM ring buffer → V4L2 queue → user-space mmap. This is the *single most important figure* in Part VIIb cameras and it is missing.
- The media-graph ASCII in §87.3 (the boxes for ov5640, imx-csi, /dev/video0) is decent but should also show *pad numbers* (pad 0 source on sensor, pad 0 sink + pad 1 source on csi) — those are what `media-ctl --set-fmt` uses.

### Technical errors
- "i.MX6ULL CSI bandwidth: the parallel CSI captures 8-bit data at the sensor's pixel clock (typically up to ~96 MHz)". The i.MX6ULL CSI in the RM is 8-bit-only (CSI_DATA00..CSI_DATA07 pins; no CSI_DATA08+), and the max input clock is ~96 MHz per the datasheet electricals. OV5640 supports 10-bit output but on i.MX6ULL you must use 8-bit mode. The table says "8/10-bit parallel" for OV5640 — true for the chip but misleading on i.MX6ULL specifically. Add a footnote.
- `drivers/staging/media/imx/imx7-media-csi.c` — the i.MX7 driver in staging *also* covers i.MX6ULL (they share the same CSI IP). State this; reader will look for an `imx6ull-` named file and not find one.
- `bus-width = <8>;` in the endpoint — correct property name is fine, but newer bindings prefer the named-form `bus-type = <5>` (parallel) + `bus-width`. Check current binding.
- "the i.MX6ULL has *no* MIPI-CSI" — correct.
- `MEDIA_ENT_F_CAM_SENSOR` — correct function ID, good.
- `v4l2_async_register_subdev_sensor` exists; on older kernels it was `v4l2_async_register_subdev`. State the kernel target.

### Insufficient depth
- §87.6 ("The CSI bridge side") says "you don't write this." Fair, but the reader is curious what the bridge driver *does* — show three or four lines of pseudocode: configure CSI capture format, set up DMA descriptors, on EOF interrupt hand the buffer to vb2. This demystifies "the bridge" without writing one.

### Knowledge prerequisites missing
- `media_entity_pads_init` and the entity/pad/link triple deserve a paragraph before they appear. Reader saw it briefly in Ch 54B; refresh.
- The "v4l2-async" mechanism — sensor probes independently of the bridge, then they bind via fwnode-graph — should be explained explicitly. "Async" is non-obvious if you're used to "probe wires you up immediately."

### Other
- §87.7 ("GStreamer + processing") gives three example pipelines. Add `fbdevsink` is actually deprecated; modern is `kmssink` or `v4l2sink`. Verify.
- Lab 1 ("scope CSI_MCLK") is great — physical-world debugging is exactly what the MCU reader values.

## Ch88 — USB UVC

### Readability
- Very tight chapter — well-paced, good. Keep.

### MCU-engineer friendliness
- The reader has likely never written a UVC host driver (it's a kernel class driver, not MCU territory). Connect via "you've probably wired a UVC camera to a Raspberry Pi or Linux desktop and had it just work — same `/dev/video0`, same `v4l2-ctl`. The lesson is *why* it works (class driver) and what the bandwidth budget actually allows on USB 2.0."

### Missing examples / figures
- A bandwidth-budget diagram: USB 2.0 480 Mbps → -20% protocol overhead → -20% isochronous cap → ~320 Mbps available. Same info as the table but graphical aids retention.

### Technical errors
- "USB-2.0 high-speed = 480 Mbps theoretical, ~320 Mbps usable for isochronous (after protocol overhead + the spec's 80% isochronous cap)." The spec's isochronous cap is 80% of *each microframe* (so ~384 Mbps); the further drop to ~320 Mbps accounts for handshake/SOF/etc. overhead. Numbers are roughly right, but the wording conflates the two reductions. Tighten.
- "The i.MX6ULL has 2 USB controllers" — correct; both are USB OTG 2.0. Add: each is on its own root hub, so each has the full 480 Mbps.
- "PREEMPT_RT (Ch 52A) helps for deterministic capture" — RT does not change USB isochronous timing meaningfully (isoc is hardware-scheduled); it helps user-space schedule the dequeue. Phrase more carefully.

### Other
- §88.7 "USB gadget side" is useful — short and links cleanly to Ch 55.
- "MJPEG isn't a video codec" pitfall is excellent.

## Ch89 — Audio codecs

### Readability
- Long chapter; consider splitting "How `wm8960` works" and "Writing from scratch" with a transition sentence. Reader needs a breather.

### MCU-engineer friendliness
- The reader has driven SAI on STM32 + a WM8978 via I²C. Say: "On STM32 you wrote `wm8978_init()` (register array) + `SAI_Transmit_DMA()`; that's exactly the WM8960 driver here (regmap + the DMA is the SAI's `cpu_dai`). What's new on Linux: **DAPM** — there's no STM32 equivalent. DAPM is the runtime power graph that turns off the DAC/amp when no stream is active. On bare metal you either left everything on (clicks + power) or wrote it yourself. DAPM does it for you and is the bulk of any codec driver."

### Missing examples / figures
- The brief asks for "ASoC machine-driver linking codec_dai to cpu_dai". The chapter has a block diagram of the WM8960 internals but not the *ASoC layering*. Show: simple-audio-card / machine driver → codec_dai (wm8960) + cpu_dai (sai) → DAI link → PCM → user-space (ALSA aplay). This is the highest-leverage figure.
- The DAPM widget graph for `mycodec` (DAC → HP Amp → HPOUT, plus the Playback stream endpoint) should be drawn — three boxes and two arrows would make `mycodec_routes` self-explanatory.

### Insufficient depth
- §89.3 (DAPM) is good but stops short of showing the *traversal*. Add: "When the stream activates, DAPM walks back from the DAI's 'Playback' stream endpoint, finds all widgets that connect via active routes, and powers each. When deactivated, it walks the graph in reverse order and powers down — pop-aware ordering matters." That sentence is the key insight.

### Technical errors
- `.cache_type = REGCACHE_RBTREE` — fine; modern code may prefer `REGCACHE_MAPLE`. Note the choice but RBTREE is still valid.
- `SND_SOC_DAIFMT_CBC_CFC` — "Codec Bclk Consumer, Codec Fsync Consumer" is the modern name (replaces the older `CBS_CFS` slave-as-consumer wording). Good that you used the new constants; mention the naming change briefly because readers will find both in tutorials.
- `wm8960_set_dai_pll` is shown but never explained — when does ASoC call it? Answer: from the machine driver via `snd_soc_dai_set_pll()`. A 1-liner suffices.
- "WM8960 = 0x1A, SGTL5000 = 0x0A, ES8388 = 0x10/0x11" — WM8960's I²C address is actually 0x1A (per datasheet ADDR-pin low; 0x1B with ADDR high). Verify the others, especially SGTL5000 which is 0x0A. Quick sanity check warranted.
- `i.MX6ULL` has both SAI and SSI (Synchronous Serial Interface) peripherals; the chapter speaks only of SAI. Most i.MX6ULL boards use SAI2 for audio. Add a footnote: "i.MX6ULL also has SSI but new designs prefer SAI; mainline `fsl-sai.c` is the driver."

### Knowledge prerequisites missing
- `DECLARE_TLV_DB_SCALE` macro is used without explanation — what is TLV? (Threshold Level Volume — describes a dB scale so userspace can show "-73.00 dB" instead of "value=0".) One line.
- `snd_soc_component_update_bits` shorthand for regmap RMW — say so.

### Other
- Lab 3 ("DAPM trace from debugfs") is great — exactly the kind of "look inside" exercise the reader wants.
- The "Pop/click on play/stop" pitfall and §89.5's reference to `mute_stream` are linked well.

## Ch90 — Class-D amps

### Readability
- Strong chapter — "the simplest possible ASoC component" framing works. Keep.
- "The MAX98357A is the minimalist's dream" — keep this tone, it's engaging.

### MCU-engineer friendliness
- Reader has driven a MAX98357 from STM32 with literally three pin connections and no software. Say: "On STM32 you don't write a 'driver' for the MAX98357A — you just enable I²S. On Linux you *still* don't write a driver in the usual sense; you write a 100-line ASoC component that declares 'I'm a sink for I²S'. The reason: the ALSA framework requires a `snd_soc_dai_driver` on both ends of the DAI link, even if one end is just a dumb pin."

### Missing examples / figures
- A wiring diagram for the SD_MODE resistor table (4 states encoded by one analog resistor) is genuinely interesting — show a small table with the actual resistor values from the datasheet.
- Block diagram of TAS5805M (I²S → DSP → PWM → H-bridge → speaker) would help the "what is the DSP doing" question.

### Insufficient depth
- TAS5805M section (§90.5) is too thin given its importance. The book commits to "driver internals + from-scratch implementation" (per the user memory), but here it explicitly skips the from-scratch driver because "it's WM8960-shaped plus paging + firmware blob." Either show the regmap config for the paged register access (`reg_bits = 8, val_bits = 8, max_register, but with custom read/write via book-page select`), or show a minimal `tas5805m_load_blob()`. As written, the reader cannot actually build it.

### Technical errors
- "**SND_SOC_DAPM_OUT_DRV_E**" — the `_E` suffix means "with event callback" — say so, since the reader needs to understand why this variant vs `OUT_DRV`.
- `SND_SOC_DAPM_PRE_PMU | SND_SOC_DAPM_POST_PMD` — these mean "before powering up, after powering down" — write that out, because the reader will copy the line and not know which point in the cycle their callback fires.
- "TI MAX98357A" — MAX98357 is a Maxim part (now Analog Devices), not TI. Correct in §90.1 footer ("TI/Maxim"), wrong in the chapter's lead "What" sentence. Fix.
- "PCM5102A" — the PCM5102/5102A is TI (originally Burr-Brown). Correct.
- "TAS5805M needs 32–96 kHz" — datasheet allows 32–96 kHz; many products run it at 48 kHz only. Fine as written.

### Knowledge prerequisites missing
- `DECLARE_TLV_DB_SCALE` reappears here (it does not — was Ch 89). Not an issue.
- "platform_device (not I²C/SPI) because there's no control bus" is a good pedagogical point and a *new* concept for the reader (they've only seen I²C/SPI codecs). Spell it out: a platform_device is a "device described purely by DT, no enumeration bus."

### Other
- Lab 3 ("scope SD_MODE GPIO during play/stop") is exactly the right MCU-style verification. Keep.
- Pitfall "Class-D EMI" — correct and important; many products fail EMC pre-compliance here.

## Ch91 — SDIO WiFi

### Readability
- "This chapter is mostly about the bring-up sequence and debugging" — honest framing, good.
- "Bring-up trace" §91.6 (the dmesg progression with explicit "if you don't see line 1, …") is exactly the right "debugging by stage" approach. Keep and replicate elsewhere.

### MCU-engineer friendliness
- The reader probably has *not* done SDIO WiFi on bare metal (it's heavy). The right framing is the *opposite*: "On an MCU you typically use ESP-AT (Ch 93). SDIO WiFi is the 'real Linux' way, but in exchange for being mainstream, you accept that bring-up means describing 5 things in DT exactly right."

### Missing examples / figures
- The brief asks for "wpa_supplicant ↔ nl80211 ↔ cfg80211 ↔ driver layering." §91.3's diagram has the boxes but should also show *netlink sockets* between userspace and kernel (NL80211 = a netlink family). Adding the "netlink socket" arrow makes the user/kernel boundary explicit.
- An ASCII timing diagram of the SDIO power sequence: WL_REG_ON low → wait → high → LPO clock running → SDIO CMD0 → enumeration. Would clarify the §91.4 prose.

### Technical errors
- `compatible = "brcm,bcm4329-fmac"` — the canonical for AP6212/BCM43438 is `brcm,bcm4329-fmac` *or* `cypress,cyw43438-fmac` (after Cypress acquired Broadcom's IoT business; then Infineon). Some mainlines prefer the bcm4329 fallback as a generic. Note both compatibles.
- "Out-of-tree (`rtl8189es`/`rtl8189fs`)" — for the RTL8189FTV the relevant out-of-tree is `8189fs` not `8189es` (those are different chip variants). Verify with a current repo.
- `cap-power-off-card` — used in the example. This flag's semantics changed; it's also worth pairing with `non-removable`. Worth a sentence.
- "regdb missing... CRDA" — CRDA is largely deprecated in favor of in-kernel `CFG80211_DEFAULT_PS` + the kernel reading `regulatory.db` directly. Update.

### Insufficient depth
- §91.7 "How a packet flows" is the right level. Keep — this is the "framework internals" the user memory demands, done correctly: it explains the structure without re-implementing the entire driver.

### Other
- "BT half of a combo not coming up" pitfall is great — direct link to Ch 94.
- Lab 6 (swap NVRAM, observe degraded range) is brilliant pedagogy — keep.

## Ch92 — USB WiFi

### Readability
- "The chip you buy determines whether WiFi is a 5-minute job or a 5-day ordeal" — keep, perfect.
- "Soft-MAC (rt2x00) vs full-MAC (rtl8188eus)" — implicit in the text but never stated. Add a sentence: this is *why* the rt2800usb experience is so different from the rtl8188eus experience: mac80211 handles the MAC for soft-MAC chips, so the chip driver is a thin shim.

### MCU-engineer friendliness
- Reader has plugged USB WiFi into a Pi and had it work / not work; they want the buying guide. The chapter is good as-is on this dimension.

### Missing examples / figures
- A soft-MAC vs full-MAC layered diagram (mac80211 + cfg80211 boxes for soft-MAC; just cfg80211 for full-MAC) would make the in-tree/out-of-tree story click.

### Technical errors
- "RTL8188EUS... partial (`r8188eu` since 5.18, in staging)" — the staging driver `drivers/staging/r8188eu/` was added in 5.17 and graduated/removed from staging in 6.7 (with another iteration as `rtw88` family for newer parts). Recheck against the current mainline tree; the RTL8188EU support story has moved.
- "RT5370... in-tree since forever" — yes, `rt2800usb` is mainline for a decade+.
- "Counterfeit chips" pitfall — true. Add a note about `lsusb -v` showing the iManufacturer string (which is often *wrong* on clones — can't trust either).

### Knowledge prerequisites missing
- `wireless-regdb` and "country code" — quick gloss for the reader who hasn't met regulatory domains.

### Other
- AP-mode + hostapd section is solid. Keep.

## Ch93 — Hosted WiFi via ESP32

### Readability
- "Two fundamentally different offload models" — clean framing. Keep.
- "It's a wireless serial port" (later, for AT) — keep this phrase.

### MCU-engineer friendliness
- This is *the* chapter where the MCU-engineer reader is most at home — they've done ESP-AT from STM32. Lean into it: "If you've done ESP8266 AT from STM32, AT-mode is identical. esp-hosted is what you'd build if you wanted Linux to see a real `wlan0` — same ESP, different firmware on it."

### Missing examples / figures
- esp-hosted SPI transport timing: handshake GPIO assertion → host SCK → simultaneous TX/RX data → handshake deassert. Helps explain why both `handshake` and `data-ready` GPIOs are needed.

### Insufficient depth
- §93.4 "How the esp-hosted driver works" is at the right level — keep.
- §93.5 "AT-command mode" — show one *complete* working code sample (open, configure termios, send AT, parse response, send data, read +IPD). The current snippet `expect_ok(fd)` is hand-waved. A 60-line working C example would be the highest-value addition.

### Technical errors
- "The ESP32... it has its own CPU" — ESP32 has two cores (Xtensa LX6); ESP32-S2/C3 have one; ESP8266 has one (Tensilica L106). Be precise or just say "an embedded CPU."
- "esp-hosted... out-of-tree" — true (github.com/espressif/esp-hosted); state the Linux driver licensing (Apache-2.0).
- "FCC/CE/IC modular certification" — yes, this is a real product advantage. Verify against current ESP32-WROOM-32E module spec (which does carry FCC/IC/CE certifications). Good as written.

### Knowledge prerequisites missing
- `netdev_ops`, `ndo_start_xmit`, `skb` — refresh briefly. Reader has had network drivers in Part VI but a 2-line callout helps.

### Other
- Decision table §93.6 is excellent.
- Lab 4 (Bluetooth on the same ESP) — note that not all esp-hosted firmware builds include BT; explicit configure step.

## Ch94 — WiFi+BT combo

### Readability
- Strong chapter overall. "WiFi works, BT forgotten" pitfall captures a *very* real failure mode.

### MCU-engineer friendliness
- Reader has used AP6212-style modules on STM32 (rare, usually as a co-processor module). Connect: "On Linux the combo module's two halves talk to *different kernel subsystems* on different buses. There's no single 'WiFi+BT driver' — it's two drivers that happen to share silicon. This is unusual coming from a one-firmware-blob MCU world."

### Missing examples / figures
- The block diagram in §94.2 is solid. Keep.
- A sequence diagram of "boot → uSDHC2 enum → wlan0 up → UART3 serdev probe → hci_bcm fw patch load → hci0 up" with timing would clarify the order.

### Technical errors
- "RTL8723BS driver... `rtl8723bs` (in-tree, staging-graduated)" — `r8723bs` is currently in `drivers/staging/rtl8723bs/` in some kernels and graduated/moved in others; pin the kernel version.
- "uart-has-rtscts" — correct DT property for the uart3 node.
- `compatible = "brcm,bcm43438-bt"` — correct. The `hci_bcm` driver matches this; check Documentation/devicetree/bindings/net/brcm,bcm4329-bt.yaml or similar for the canonical spec.
- "BT_REG_ON vs WL_REG_ON" — for the AP6212, they're typically *separate* signals (good, as stated); but for some pin-constrained boards they're tied. Mention both possibilities.

### Insufficient depth
- §94.5 "Coexistence" describes PTA but does not say *how the user observes* whether coex is working. A practical "scope" or "iperf3 with/without A2DP" measurement procedure (which Lab 5 does propose) should be tied directly to the §94.5 prose.

### Other
- "Default/duplicate BD address" pitfall is gold — many products ship with `00:00:00:00:00:00` from the factory. Keep.

## Ch95 — HCI Bluetooth

### Readability
- Long chapter, well-structured. The "controller + host + app" split (§95.3) is the key insight; surface it earlier and reuse the phrase.
- "the controller runs the BT link layer; you build the GATT application" — keep this thesis line, repeat it.

### MCU-engineer friendliness
- Reader has done HM-10 AT-BLE from STM32. The pivot here is: "On STM32 you used the HM-10 (Ch 96). On Linux you can also use HM-10 — but Linux gives you a *real* GATT server via BlueZ. The cost: 250 lines of D-Bus glue, but you get standard GATT and any BLE app can talk to it."

### Missing examples / figures
- The brief asks for "HCI ↔ BlueZ ↔ driver layering." §95.3 has the diagram. Good. Add to it: where in this stack does `btmon` snoop? (Between kernel BT and the controller — show an arrow pointing at the HCI level.)
- A GATT service tree (service UUID → characteristic UUIDs → descriptors) drawn as ASCII would help the §95.6 model.

### Insufficient depth
- §95.6's Python example is incomplete — it admits "the full example needs the service-object + advertisement-object registration boilerplate ~250 lines total" and points at BlueZ's `test/example-gatt-server`. For a "from scratch" cookbook chapter, this is a cop-out. Either include the full ~250 lines in an appendix, or rewrite to show the *complete* minimal example. As is, the reader cannot build the lab.
- The HCI protocol (§95.2) is described at the surface level. Since you're not asking the reader to send raw HCI, this is fine — but a `btmon` decoded trace of one connection (HCI Reset, Read BD_ADDR, LE Set Advertising Data, LE Set Advertising Enable, LE Connection Complete) would make the protocol tangible.

### Technical errors
- "**HCI**: the standardized boundary between the host (Linux + BlueZ) and the controller (the BT chip)." Strictly, HCI is BT Core Spec Vol 4 Part E; H4/H5/USB are transport bindings. The text conflates HCI (the protocol) with HCI-UART (a transport). Disambiguate.
- nRF52 with Zephyr `hci_uart` sample — true and well-documented. Good.
- "DEFAULT_BD_ADDR... `43:43:A1:00:00:00`" — that's a plausible example, but the actual default for many AP6212 modules is `43:34:B1:...`. Don't fabricate addresses; say "often a vendor-prefix MAC with zeros for the unit field."
- "MTU too small. Default BLE ATT MTU is 23 bytes (20 usable)" — correct; LE legacy ATT is 23, with MTU exchange negotiating up to 247 (LE Data Length Extension) or 517 (max ATT MTU). State the cap.

### Knowledge prerequisites missing
- D-Bus as a concept — reader's first encounter? If so, two sentences: "D-Bus is the desktop-Linux RPC bus; BlueZ exposes its API via D-Bus so any language with bindings (Python, C, Rust) can drive it." Without this, the Python example is impenetrable.
- "GATT" / "GAP" / "SMP" / "L2CAP" acronyms — define on first use.

### Other
- "MTU too small" pitfall is real — keep.
- The provisioning use-case (Lab 7) is a fantastic real-world application — keep.

## Ch96 — AT-command BLE

### Readability
- "BLE-to-serial cable" phrase is perfect. Use it more.
- Very crisp chapter. Keep.

### MCU-engineer friendliness
- This is the chapter that *most* matches the reader's existing experience. They've literally done this from STM32. The "compare ~10 lines here vs ~250-line GATT server of Ch 95" is the lesson. Reinforce: "Ch 95 buys you the full BLE ecosystem; Ch 96 buys you simplicity. Pick the right tool."

### Missing examples / figures
- Show a side-by-side: HM-10 module → UART → STM32 (familiar) vs HM-10 module → UART → i.MX6ULL (now). Same wiring, same AT commands; reinforce that the embedded engineer's knowledge transfers directly.

### Technical errors
- "HM-10 (CC2540/CC2541-based)" — CC2540 is BT 4.0 classic+BLE dual; CC2541 is BLE-only. HM-10 uses CC2540 typically. Verify.
- "AT+NAME=MyDevice" vs "AT+NAMEMyDevice" — true variation across clones. Keep the warning.
- "BLE point-to-point... reaches ~30 m" — depends heavily on antenna; HM-10 with PCB antenna is more like 10–20 m line-of-sight. Don't overstate.

### Insufficient depth
- "Single connection" pitfall is mentioned briefly but not deeply — the AT modules can only act as one role (peripheral OR central) at a time on most firmwares. Worth one more sentence.

### Other
- Lab 5 (wire to BME280, command parser, LED control) — the perfect end-to-end example.

## Ch97 — BLE Mesh

### Readability
- Mesh is genuinely hard; the chapter does a reasonable job. The "publish/subscribe over flooded BLE adverts, addressed by models" thesis line is good.

### MCU-engineer friendliness
- Reader has not done mesh. The framing should be: "BLE Mesh is conceptually closer to CAN-bus broadcast or MQTT pub/sub than to the BLE you've used. There's no concept of 'connecting to one device' — you publish to addresses; subscribers act."

### Missing examples / figures
- A figure showing 5 nodes with relay paths, one node out of direct range relayed via another. The §97.7 Lab 7 hints at this; a picture would land it.
- A picture of an element/model/state hierarchy (Node → Element[0..n] → Model[OnOff, Lightness, Health]) would clarify §97.2's prose.

### Insufficient depth
- The chapter's "from scratch" content (per the cookbook depth requirement) is thin — the §97.6 says "writing a mesh node application is analogous to Ch 95's GATT server but for mesh models — more involved, and the bluez-mesh D-Bus API is less mature." Then no code. The cookbook needs at minimum a `Application1`+`Element1` skeleton showing the model registration. Even 50 lines of pseudo-D-Bus would be enough. Without it, the chapter is purely descriptive and violates the user-memory requirement.

### Technical errors
- "thousands of nodes" — BLE Mesh's hard cap is 32767 unicast addresses minus reserved; practical networks are ~100–500 nodes due to flood control. "Thousands" is technically defensible but practically optimistic. Soften.
- "bluez-mesh maturity. The Linux mesh stack and D-Bus API are less polished than GATT." — Fair and honest. Keep.
- "address 0xC000" — `0xC000-0xFEFF` is the group-address range, correct.
- "AppKey 0... bind 0 0 1000" — model ID 0x1000 is Generic OnOff Server, correct.

### Knowledge prerequisites missing
- "Element" vs "Model" — both are first-mentioned in §97.2 and could use one more concrete example: "A 4-gang switch is one *node* with 4 *elements* (one per gang), each with a Generic OnOff Server model — so the phone app can address them independently."
- The NetKey/AppKey two-tier scheme — readers familiar with TLS will get it, but a one-line analogy ("NetKey is like the WPA pre-shared key; AppKey is like an application-layer TLS key — relay nodes have NetKey but not AppKey") helps.

### Other
- Lab 7 (relay test) is the magic-moment lab. Keep.
- Pitfalls "bluetooth-meshd vs bluetoothd conflict" is real — keep.
