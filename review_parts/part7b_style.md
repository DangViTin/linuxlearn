# Part VIIb — Style/ESL Review (Ch 82–97: displays, touch, cameras, audio, Wi-Fi, Bluetooth)

## Cross-cutting patterns

- **Em-dash overload.** Driver chapters in this batch use " — " several times per paragraph, including triple em-dashes within one sentence. The first two pages of Ch 87, Ch 89, Ch 91 are especially heavy. Convert at least one em-dash per paragraph to a period.
- **Semicolon-glued clauses in `Pitfalls`.** "X happens; Y is the cure." reads AI-flavored. Use a period.
- **"Not X, it's Y" / "Not X — Y" sledgehammer.** Frequent in chapter intros and the "Why" callouts (Ch 82 §82.2, Ch 85 §85.6, Ch 87, Ch 91, Ch 95). Trim.
- **Buzzwords still present.** `crucial`, `essential`, `mandatory` (used 6+ times across Ch 85/87/89/95), `seamless`, `comprehensive` are mostly absent (good). But `landscape`, `realm`, `pivotal` show up in the Wi-Fi/BT chapters' intros. `internalize` / `mental model` is overused throughout this batch.
- **Triplet rhythm.** "X, Y, Z — all from one DT node." / "Three buffers, two pipelines, one mux." / "Pixel, plane, port." Rhythmic but reads AI when stacked.
- **Royal "we'll/let's" overuse.** Common in §X.4 "from scratch" sections ("Let's wire up the codec_dai"). Replace half with imperative.
- **"That's it." / "That's the whole pattern."** Drop most.
- **Cliché phrasing.** "the bread-and-butter HMI display interface" (Ch 82), "the cheapest possible 'real display'" (Ch 85), "alphabet soup of layers" (Ch 91 §91.2), "the kernel's most opinionated subsystem" (Ch 89). All flagged below in their chapters.
- **Bullet-list-as-prose inside §X.0 callouts.** The `> **What:** ...` blockquotes routinely run 60+ words with multiple em-dashes. Break into 2–3 short sentences.
- **Marketing tone on chip pricing.** "$3–6," "$1.50–3," "$5–15" appear in comparison tables and also as ad-copy in prose ("a $2 128×64 OLED"). Keep in tables, drop from prose.

---

## Ch 82 — RGB parallel LCD on LCDIF

### AI wording / sledgehammer / buzzwords
- > "**pixel clock + 6 porch numbers + 3 polarities = a working panel**."
  - Cute formula, but `Focus:` callout reads marketing. Rewrite: "A working panel needs a pixel clock, six porch numbers, and three polarities. That is the entire job."
- > "Get the timings right and the panel works; get one porch wrong and you see a rolling, torn, or blank screen."
  - Semicolon glue + triplet ("rolling, torn, or blank"). Rewrite: "Get the timings right and the panel works. Get one porch wrong and the image rolls, tears, or stays blank."
- > "Transcribing them is the entire job."
  - Bolded sledgehammer (second time in the chapter). Drop the bold, keep the sentence once.
- > "parallel-RGB is the bread-and-butter HMI display interface for i.MX6ULL."
  - Cliché. Rewrite: "Parallel-RGB is the standard HMI display interface for i.MX6ULL."
- > "Unlike a smart SPI panel (Ch 83), a parallel panel has no frame buffer of its own — the SoC continuously streams pixels at the pixel clock, refreshing 60× per second."
  - 31-word em-dash sentence. Rewrite: "A parallel panel has no frame buffer. The SoC streams pixels at the pixel clock and refreshes the glass 60 times a second."
- > "There is no 'smart' negotiation — the numbers must match the glass."
  - Em-dash glue. Rewrite: "There is no negotiation. The numbers must match the glass."
- > "The 'porches' are blanking intervals — legacy from CRT days (the electron beam needed time to fly back), but LCDs still use the timing model."
  - Em-dash + parenthetical + "but" clause = three clauses in one line. Rewrite: "The 'porches' are blanking intervals. They are a CRT legacy — the electron beam needed time to fly back. LCDs kept the timing model."
- > "The conversion is mechanical but easy to fumble."
  - "Mechanical but easy to fumble" is a stock Claude line (seen often in Parts II/V). Rewrite: "The conversion is simple but easy to get wrong."

### ESL readability
- > "ATK10261 (71 MHz) is at the edge — works but marginal, sometimes needs reducing to a lower-refresh timing."
  - "At the edge" idiomatic; "works but marginal" fragment. Rewrite: "ATK10261 at 71 MHz is at the limit. It usually works but you may need to drop to a lower refresh rate."
- > "For a panel needing custom power sequencing or init commands (rare for dumb RGB panels, common for panels with an init-controller), write a `drm_panel` driver:"
  - 28-word sentence with two parentheticals. Rewrite: "Some panels need custom power sequencing or init commands. This is rare for dumb RGB panels but common for panels with an init controller. For those, write a `drm_panel` driver."
- > "~120 lines. It registers a `drm_panel` with the timing and power sequencing; the LCDIF DRM driver finds it via the of_graph link and uses its mode."
  - Semicolon glue + dense vocabulary. Rewrite: "About 120 lines. It registers a `drm_panel` with the timing and power sequencing. The LCDIF DRM driver finds the panel through the of_graph link and uses its mode."

### Needs more depth
- §82.4 The DRM CRTC/encoder/connector/panel split is invoked ("The LCDIF DRM driver is the **CRTC + encoder**; the panel is the **connector's** mode source.") without ever explaining the four-role model. An MCU reader meets these terms first here. Add a 6–8 line paragraph: "DRM splits the display pipeline into four roles. The **CRTC** scans pixels out of memory at the right timing. The **encoder** translates the parallel pixel stream into a transport-level signal (parallel RGB, LVDS, HDMI, DSI). The **connector** is the physical port (or in our case, the panel input). The **panel/bridge** is the device hanging off the connector. On i.MX6ULL with parallel RGB the encoder is trivial (just wires) and the connector is the panel itself."
- §82.4 Atomic vs legacy KMS is never mentioned. The `myst7789.c` driver in Ch 83 uses `DRIVER_ATOMIC`, but it is never explained what atomic modesetting is or why it matters. Add one paragraph here in §82.4: "Modern DRM drivers use **atomic modeset**: every state change (mode, plane, cursor, format) is packaged into one transaction that the hardware applies on the next vblank, atomically. The legacy KMS path applied changes one at a time and could leave you with a half-configured display for a frame. All new drivers must be atomic; the helpers in this chapter assume it."
- §82.5 Approach 3 introduces `panel-bridge` indirectly (the driver is a `drm_panel`, not a `drm_bridge`). The bridge model is the natural follow-on (LVDS bridges, DSI-to-HDMI bridges) and is invoked offhand in later chapters. Add 4 lines: "Between the encoder and the panel sometimes sits a **bridge** — a chip that converts one signal type to another (parallel RGB → LVDS, DSI → HDMI). `drm_bridge` is the kernel object for it. A driver chain of bridges + a final panel is common on bigger SoCs. On i.MX6ULL with a direct-attached parallel panel, there is no bridge."

---

## Ch 83 — SPI LCD (ST7789 / ILI9341)

### AI wording / sledgehammer / buzzwords
- > "Unlike the dumb parallel panels of Ch 82, these have their own RAM — you send an init sequence + pixel data over SPI, and the controller refreshes the glass itself."
  - 28-word em-dash sentence + comma splice into "and the controller refreshes." Rewrite: "Unlike the dumb parallel panels in Ch 82, these have their own RAM. You send an init sequence and pixel data over SPI. The controller refreshes the glass on its own."
- > "SPI LCDs are cheap ($3–8), need only 4–5 wires (vs 28 for parallel), and are everywhere — smartwatches, thermostats, handheld instruments, hobbyist gadgets."
  - Marketing-flavor list, em-dash glue. Rewrite: "SPI LCDs are cheap and small. They need 4–5 wires versus 28 for parallel, and they appear in smartwatches, thermostats, handheld instruments, and hobby gadgets."
- > "**the MIPI-DBI command/data model + partial updates**"
  - Bolded equation-style heading in `Focus:`. Restate plainly.
- > "Only sending the *changed* rectangle (partial update) is the key to acceptable performance."
  - "The key to" cliché. Rewrite: "Send only the changed rectangle. That keeps refresh fast enough."
- > "What we got, ~200 lines:"
  - Informal contraction "What we got". Rewrite: "About 200 lines. We now have:"
- > "What *we* provided: the init sequence (the chip-specific magic) and the pixel dimensions."
  - "Magic" overused throughout the book. Rewrite: "We provided two things: the chip-specific init sequence and the pixel dimensions."
- > "What we'd add for production: rotation handling (MADCTL variations), power management (sleep on disable), and using the mainline `panel-mipi-dbi` generic driver instead of a custom one."
  - 28-word run-on with three parentheticals. Break into a bulleted list or three sentences: "For production: handle rotation through MADCTL. Add sleep on disable for power management. Better still, switch to the mainline `panel-mipi-dbi` generic driver and skip the custom code entirely."

### ESL readability
- > "the trade-off: SPI bandwidth limits refresh rate (a 240×240 16-bit frame is 115 KB; at 40 MHz SPI that's ~23 ms = ~40 fps max for a full refresh). For static or partial-update UIs, that's plenty."
  - Long parenthetical with semicolon glue inside. Break: "The trade-off is bandwidth. A 240×240 16-bit frame is 115 KB. At 40 MHz SPI that takes ~23 ms — about 40 fps for a full refresh. For static or partial-update UIs, that is plenty."
- > "Note: 3-wire mode (no DC pin; the D/C bit is embedded as a 9th bit per byte) exists but is awkward on most SPI controllers — 4-wire (separate DC GPIO) is standard."
  - 30-word sentence, three clauses, semicolon glue inside parenthetical. Rewrite: "A 3-wire mode also exists. The D/C bit becomes a 9th bit per byte, so there is no DC pin. Most SPI controllers cannot generate the 9-bit frame, so 4-wire (a separate DC GPIO) is the standard."
- > "Did the CASET/RASET/RAMWR command sequence per flush."
  - Bullet starts with past-tense verb in a list of "What the helper did for us." Awkward English for ESL. Rewrite all bullets in parallel form: "Tracked dirty rectangles..." → "It tracked dirty rectangles..." for each.

### Needs more depth
- §83.3 The DRM "tiny" framework and the `drm_simple_display_pipe` abstraction are introduced without context. An MCU reader has not seen DRM's full pipeline yet (CRTC + plane + connector). Add a 4–5 line paragraph: "A full DRM driver wires four objects together: a CRTC for timing, a plane for the source buffer, a connector for the output port, and an encoder for the signal conversion. For tiny displays this is overkill. `drm_simple_display_pipe` collapses CRTC + plane + encoder into one object with one set of callbacks. You only fill in `.enable`, `.disable`, and `.update`; the helpers handle the rest."
- §83.4 The `DRIVER_ATOMIC` flag appears with no introduction. Forward-reference or inline one sentence: "All modern DRM drivers must support atomic modeset — see Ch 82 §82.4."
- §83.6 Vsync / tearing handling ("No tearing if you respect the vblank") deserves 3 lines. For an MCU reader who has not seen vblank in a CPU-driven panel context: "Tearing happens when the SPI flush overlaps the controller's own refresh of the glass. Some panels expose a **TE (tearing effect)** pin that pulses at the start of each refresh cycle; route it to a GPIO IRQ and start each flush just after the TE pulse to land the data outside the controller's scan window."

---

## Ch 84 — QSPI LCD

### AI wording / sledgehammer / buzzwords
- > "QSPI quadruples the data rate: ~13 ms = ~75 fps. For round watch faces and animated UIs, QSPI is the difference between 'smooth' and 'slideshow.'"
  - "The difference between X and Y" cliché; quoted contrast is marketing. Rewrite: "Quad-SPI quadruples the data rate to about 13 ms per frame, or 75 fps. That is the difference between smooth animation and a slideshow."
- > "This is a newer, less-common interface — fewer mainline drivers, more chance you'll write your own."
  - Em-dash list-as-prose. Rewrite: "QSPI is newer and less common. Fewer mainline drivers exist, so you are more likely to write your own."
- > "**Honest assessment**: the i.MX6ULL is *not* a great host for QSPI displays. Its QSPI is flash-centric."
  - Bolded editorial header. Drop the bold, keep the content.
- > "We cover the topic because the *displays* are increasingly common, and you may meet them on a more capable SoC."
  - "You may meet them" is awkward English (you may encounter them). Rewrite: "We still cover the topic. The displays are increasingly common, and you will likely meet them on a more capable SoC."

### ESL readability
- > "The exact framing is controller-specific."
  - Fine; keep.
- > "On SoCs whose SPI controller exposes `spi_mem` with quad support, the `mipi_dbi` helper can issue quad transfers."
  - "On SoCs whose..." is grammatically dense for ESL. Rewrite: "Some SPI controllers expose `spi_mem` with quad support. On those SoCs, the `mipi_dbi` helper can issue quad transfers."
- > "We won't reproduce the full driver — it's Ch 83's driver with the data phase changed to quad, *and* it only works on an SoC whose controller supports quad `spi_mem` writes (not stock i.MX6ULL)."
  - 36-word sentence with em-dash + italic "and" + parenthetical. Rewrite: "We do not reproduce the full driver. It is the Ch 83 driver with the data phase changed to quad. It only works on an SoC whose controller supports quad `spi_mem` writes — stock i.MX6ULL does not."

### Needs more depth
- §84.3 The "QSPI controller is designed for flash" claim is correct but unmotivated. One paragraph explaining the LUT model: "The i.MX6ULL QSPI controller does not have a generic 'send N bytes on 4 lanes' command. Instead, it programs a 16-entry **LUT** (look-up table) where each entry is a phase descriptor (CMD/ADDR/DUMMY/DATA), and a transfer is built by selecting a sequence of LUT entries. For NOR flash, this matches the JEDEC command set perfectly. For displays, the framing (single-lane command marker → quad-lane pixel stream) does not map cleanly onto the LUT phases, and the driver `fsl-quadspi.c` never exposes a non-flash data path."

(Short chapter, only 3-4 worst offenders flagged. §84.4–§84.6 are clean enough.)

---

## Ch 85 — OLED & e-paper

### AI wording / sledgehammer / buzzwords
- > "**OLED is a page-addressed bitmap; e-paper is a two-buffer LUT-driven waveform machine**."
  - Bolded "X is A; Y is B" parallelism in `Focus:`. Rewrite: "OLED uses a page-addressed bitmap. E-paper uses a two-buffer waveform replay driven by a LUT. They need very different driver code."
- > "OLEDs are the cheapest possible 'real display' — a $2 128×64 OLED gives you a crisp status screen with no backlight, perfect contrast, ~20 mA."
  - "The cheapest possible 'real display'" cliché + triplet ("crisp..., perfect..., ~20 mA"). Rewrite: "OLEDs are the cheapest 'real display' you can buy. A 128×64 OLED costs around $2, draws ~20 mA, and has perfect contrast without a backlight."
- > "E-paper is the opposite extreme: zero idle power (the image persists with no power), sunlight-readable, but slow to update."
  - Triplet rhythm. Rewrite: "E-paper is the opposite. Zero idle power — the image persists with no power. Sunlight-readable. But slow to update."
- > "Both show up constantly in IoT status displays, instruments, smart-home panels, electronic shelf labels."
  - List-as-prose. Keep as is or break the sentence into "Both show up in IoT status displays: instruments, smart-home panels, electronic shelf labels."
- > "The `0x8D 0x14` (charge pump enable) is the #1 gotcha — the OLED needs an internal boost converter for the ~7 V it requires; forget this command and the screen never lights."
  - 28-word sentence, em-dash + semicolon. Rewrite: "The `0x8D 0x14` (charge pump enable) is the #1 gotcha. The OLED needs an internal boost converter for the ~7 V it requires. Forget this command and the screen stays black."
- > "A normal framebuffer driver assumes 'write pixel, see it.' E-paper assumes 'write image, trigger a 2-second update, then see it.'"
  - "X assumes Y. Y assumes Z." parallel sledgehammer. Keep, but trim quotes: "A normal framebuffer is 'write pixel, see it.' E-paper is 'write image, trigger update, wait 2 seconds, see it.'"

### ESL readability
- > "Within a page, *each byte is a vertical column of 8 pixels* (bit 0 = top, bit 7 = bottom):"
  - Fine; the diagram below clarifies. Keep.
- > "The mainline `ssd130x` driver has a `col_offset` field set from DT for exactly this."
  - "set from DT for exactly this" is dense for ESL. Rewrite: "The mainline `ssd130x` driver reads a `col_offset` value from DT to handle this case."
- > "To adapt the from-scratch driver: change `ms_cmd(m, 0x21); ms_cmd(m, 0); ms_cmd(m, 127);` to `ms_cmd(m, 0x21); ms_cmd(m, 2); ms_cmd(m, 129);`. (Or — SH1106 doesn't support horizontal addressing mode at all in some variants; you set page + column manually per page.)"
  - 40+ word sentence with parenthetical. Rewrite: "For SH1106, change the column window from 0–127 to 2–129. Some SH1106 variants do not support horizontal addressing mode at all — for those, set the page and column manually for each page."
- > "Below ~0 °C, e-paper refreshes very slowly or not at all. The waveform LUT is temperature-dependent; good modules have a temperature sensor + multiple LUTs."
  - Semicolon glue + "+" used as conjunction. Rewrite: "Below ~0 °C, e-paper refreshes very slowly or not at all. The waveform LUT is temperature-dependent. Good modules include a temperature sensor and ship multiple LUTs for the controller to switch between."

### Needs more depth
- §85.6 The e-paper waveform LUT is described but the *electrochemistry* is hand-waved. One paragraph: "Each e-ink pixel is a microcapsule of black and white pigment particles, each pigment with the opposite charge. A positive pulse at the top electrode attracts white particles up (pixel appears white). The waveform LUT is a per-pixel sequence of voltage levels over time that *moves* the particles from their current position to the target. Why the multi-second flicker? The particles must be pushed all the way to one extreme, then the other, then the target — to break free of mechanical sticking ('hysteresis'). Skipping the bounce gives partial-refresh: faster, but particles do not fully detach, leaving the ghost of the old image."

---

## Ch 86 — Touch input ICs

### AI wording / sledgehammer / buzzwords
- > "a display without touch is a monitor; with touch it's an interface."
  - Semicolon glue + "X is A; X is B" cliché. Rewrite: "A display without touch is a monitor. Add touch and it becomes an interface."
- > "**capacitive = threshold detection, resistive = ADC + calibration**."
  - Equation-style `Focus:` heading. Rewrite into prose: "Capacitive touch is threshold detection — a digital touched/not-touched. Resistive touch is two ADC readings plus a calibration step."
- > "A cap button outputs a clean digital 'touched'; you wire it to `gpio-keys` and you're done."
  - Semicolon glue. Rewrite: "A capacitive button outputs a clean digital 'touched' signal. Wire it to `gpio-keys` and you are done."
- > "Resistive touch gives you two ADC readings (X, Y position) that map non-linearly to screen pixels — calibration (the `tslib` / `xinput_calibrator` step) turns raw ADC counts into pixel coordinates."
  - 30-word em-dash sentence with parenthetical-inside-parenthetical. Rewrite: "Resistive touch gives you two ADC readings, X and Y, that do not map directly to screen pixels. A calibration step (using `tslib` or `xinput_calibrator`) converts raw ADC counts into pixel coordinates."
- > "Touching the pad generates a `KEY_POWER` / `KEY_MENU` input event. `evtest /dev/input/eventN` shows them. Done — zero driver code."
  - "Done — zero driver code." trim-and-mic-drop pattern. Rewrite: "Touching the pad generates a `KEY_POWER` or `KEY_MENU` input event, which `evtest /dev/input/eventN` will show. No driver code needed."
- > "These are *hardware* straps, not software — set them on the PCB."
  - Em-dash glue. Rewrite: "These are hardware straps, not software-configurable. Set them on the PCB."
- > "Raw ADC ≠ pixels."
  - Cute but math-notation-in-prose is unusual. Rewrite: "Raw ADC values are not pixel coordinates."

### ESL readability
- > "Each electrode's capacitance rises when a finger approaches (the finger adds capacitance to ground). The chip tracks a per-electrode baseline and reports 'touched' when capacitance exceeds a threshold."
  - Two parentheticals, but readable. Keep.
- > "Sampling toggles the panel layers, which can spuriously trigger PENIRQ."
  - "Spuriously trigger" is technical English. For ESL: "Sampling toggles the panel layers, and that can trigger PENIRQ even when no one is touching."
- > "The mainline driver masks PENIRQ during sampling. Our simple driver polls the GPIO instead — works but less clean."
  - "works but less clean" fragment. Rewrite: "The mainline driver masks PENIRQ during sampling. Our simple driver polls the GPIO instead — it works, but the mainline approach is cleaner."

### Needs more depth
- §86.6 Calibration: the 3×2 affine matrix is presented as a formula without explaining *why* an affine works. For an MCU reader: "Why an affine? A 3×2 affine handles four real-world distortions in one matrix: (1) origin offset (touchscreen edge not aligned with LCD edge), (2) per-axis scale (raw ADC range smaller than the panel), (3) X/Y swap, and (4) small rotation if the touch overlay was glued slightly off-square. It does not handle non-linear distortion (corners pulling inward), but resistive panels have very little of that — affine is good enough in practice."
- §86.4 ADC differential mode is mentioned in the protocol table ("SER/DFR (0 = differential — better noise rejection)") but not explained. One line: "Differential mode reads the touch-point voltage against the drive layer's far rail in one conversion, canceling supply noise that would otherwise creep into the single-ended reading."
- §86.4 The mainline `ads7846.c` driver uses a *hardware* settle-time and interleaved sample sequences ("X-+ X-- Y-+ Y-- Z-+ Z--") that the from-scratch driver skips. Mention this trade-off explicitly in §86.5's "what we skipped" list: "The mainline driver runs each axis in both polarities and averages — cancels switch-charge artifacts in the resistive layers. We just median-filter five same-polarity samples, which is simpler but noisier under EMI."

---

## Ch 87 — Parallel CSI cameras

### AI wording / sledgehammer / buzzwords
- > "Three sensors compared: **OmniVision OV5640** (5 MP, the workhorse), **OV7725** (0.3 MP VGA, simple), **GalaxyCore GC2145** (2 MP, cheap)."
  - "Workhorse" cliché. Rewrite: "Three sensors compared: OmniVision OV5640 (5 MP, the common default), OV7725 (0.3 MP VGA, simple), GalaxyCore GC2145 (2 MP, budget)."
- > "any i.MX6ULL product with a camera — a smart doorbell, a barcode scanner, a machine-vision sensor — uses parallel CSI (the i.MX6ULL has *no* MIPI-CSI)."
  - Double em-dash interjection + parenthetical. Rewrite: "Any i.MX6ULL product with a camera uses parallel CSI. The i.MX6ULL has no MIPI-CSI. Smart doorbells, barcode scanners, and machine-vision sensors all run through this interface."
- > "The driver model is the most elaborate in the kernel: a *sensor* sub-device feeds a *CSI bridge* sub-device feeds a *video* device, all wired via the media controller."
  - "Most elaborate in the kernel" is editorial. "Feeds a X feeds a Y" reads like a chain. Rewrite: "The driver model has more moving parts than most subsystems. A *sensor* sub-device feeds a *CSI bridge* sub-device, which feeds a *video* device. The media controller wires them all together."
- > "Understanding this graph is the key that unlocks all of V4L2."
  - "The key that unlocks" cliché. Rewrite: "Understand this graph and the rest of V4L2 falls into place."
- > "**a camera sensor is two devices in one — an I²C control interface and a parallel pixel stream — modeled as a V4L2 sub-device**."
  - Bolded `Focus:` with triple em-dashes. Rewrite: "A camera sensor is two devices in one. It has an I²C control interface and a parallel pixel stream. V4L2 models the combination as a sub-device."
- > "This indirection (separate subdevs, explicit format propagation) seems heavyweight for one camera, but it's what lets V4L2 handle complex pipelines (multiple sensors, ISP stages, scalers) uniformly."
  - 31-word sentence, two parentheticals. Rewrite: "All this indirection — separate subdevs, explicit format propagation — feels heavy for one camera. It is what lets V4L2 handle complex pipelines (multiple sensors, ISP stages, scalers) with the same code paths."
- > "These come from OmniVision's reference code. They configure the sensor's internal ISP, PLL, timing, and pixel pipeline. Like the BME280 compensation formulas (Ch 67) or the VL53L0X tuning blob (Ch 72), these are vendor IP transcribed verbatim — you don't derive them, you apply them."
  - Triplet ("ISP, PLL, timing, and pixel pipeline" is fine; the second triplet "you don't derive them, you apply them" reads AI). Rewrite the last sentence: "Like the BME280 compensation formulas (Ch 67) or the VL53L0X tuning blob (Ch 72), these are vendor IP. You copy them in, you do not derive them."

### ESL readability
- > "The sensor needs its MCLK running *before* I²C communication works (the sensor's logic is clocked by MCLK). This is a common bring-up gotcha."
  - Fine, but "gotcha" is idiomatic. Rewrite: "The sensor's logic runs off MCLK. Until MCLK is running, the sensor will not even ACK on I²C. This catches many people."
- > "**MCLK not running before I²C.** The sensor's logic is clocked by MCLK; no MCLK = no I²C ACK. Enable the xclk in power-on *before* the chip-id read."
  - Equation-as-prose ("no MCLK = no I²C ACK"). Rewrite: "Without MCLK, the sensor cannot ACK on I²C. Enable the xclk in `power_on()` before any I²C read."
- > "The bridge + sensor must agree on format: if the sensor emits YUYV8_2X8 640×480, the CSI captures that. `media-ctl --set-v4l2` can override pad formats during bring-up debugging."
  - "+" used as conjunction. Rewrite: "The bridge and the sensor must agree on format. If the sensor emits YUYV8_2X8 at 640×480, the CSI must capture that. During bring-up, `media-ctl --set-v4l2` can override pad formats for debugging."

### Needs more depth
- §87.3 The V4L2 subdev pipeline is the chapter's core concept but is described only at the "boxes and arrows" level. An MCU reader has not seen async subdev registration, pad format propagation, or the media-controller link semantics. Add a 12-line block after the diagram explaining:
  - **Async subdev registration.** "Sensors and CSI bridges probe independently and at unknown times — the I²C bus enumerates separately from the platform bus. `v4l2_async_register_subdev_sensor` says 'I am ready, find me.' The CSI bridge driver registers a *notifier* with a list of of_graph endpoints it expects. The async core matches them and calls `bound` when both sides are present. This is why your `/dev/video0` may not appear if the of_graph link in DT is wrong — the bridge waits forever."
  - **Pad format propagation.** "Each pad has its own current format. The format does *not* automatically flow through links — you set it on each pad with `VIDIOC_SUBDEV_S_FMT` (via `media-ctl --set-v4l2`). All pads in a chain must match; if the sensor emits YUYV but the CSI is configured for RGB565, the pipeline refuses to start or you get garbage."
  - **V4L2 controls vs subdev controls.** "Sensor controls (exposure, gain, AWB) live on the sensor subdev, not on `/dev/video0`. `v4l2-ctl --device /dev/v4l-subdev0 --list-ctrls` for the sensor's controls. The video node only owns frame-buffer-level controls."

---

## Ch 88 — USB UVC cameras

### AI wording / sledgehammer / buzzwords
- > "Unlike the parallel-CSI sensors of Ch 87 (which need a custom driver per sensor), a UVC camera is class-compliant: plug it in, `/dev/video0` appears, no driver work."
  - 28-word sentence with parenthetical + colon + comma triplet. Rewrite: "Unlike the parallel-CSI sensors in Ch 87, a UVC camera is class-compliant. Plug it in, `/dev/video0` appears, and there is no driver to write."
- > "**UVC is a class driver — the protocol is standardized, so one driver handles all cameras**."
  - Bolded sledgehammer. Rewrite: "UVC is a class driver. The protocol is standardized, so one kernel driver covers every UVC camera."
- > "The complexity isn't in a per-device driver (there isn't one); it's in *bandwidth budgeting* and *format selection*."
  - "Not X — it's Y" sledgehammer + semicolon glue. Rewrite: "The hard part is no longer per-device driver code. It is bandwidth budgeting and format selection."
- > "Understanding this is the whole game."
  - Cliché. Drop or rewrite: "Get the bandwidth math right and the rest is easy."
- > "The killer advantage of UVC: **the camera does the compression**."
  - "Killer advantage" idiom. Rewrite: "The big advantage of UVC: the camera does the compression."
- > "This makes UVC *better* than CSI for the i.MX6ULL in many cases — the webcam's silicon encodes, the SoC just receives compressed frames."
  - Em-dash glue with comma splice. Rewrite: "For the i.MX6ULL, this often makes UVC the better choice. The webcam's silicon does the encoding, and the SoC only has to receive the compressed bytes."
- > "From the application's view, a UVC camera and a CSI camera are *identical* (both V4L2 video devices); only the bring-up differs."
  - Semicolon glue. Rewrite: "From the application's view, a UVC camera and a CSI camera are identical. Both are V4L2 video devices. Only the bring-up differs."

### ESL readability
- > "UVC streams video over USB **isochronous** transfers — guaranteed bandwidth, no retransmission (a dropped frame is just dropped)."
  - 19 words but stacked qualifications. Rewrite: "UVC video runs over USB **isochronous** transfers. These guarantee bandwidth but never retransmit — a dropped microframe is simply lost."
- > "MJPEG isn't a video codec. It's per-frame JPEG — no inter-frame compression. 10:1 typical, not the 100:1 of H.264. For bandwidth-critical streaming, prefer an H.264 UVC camera."
  - Choppy fragments ("10:1 typical, not the 100:1 of H.264"). Rewrite: "MJPEG is not a true video codec. It is per-frame JPEG with no compression between frames. Typical ratio is 10:1, against H.264's 100:1. For bandwidth-critical streams, pick an H.264 UVC camera."

### Needs more depth
- §88.2 Isochronous vs bulk USB transfers: an MCU reader who has only seen USB-CDC or HID may not have a mental model of isochronous. Add one short paragraph: "USB transfers come in four flavors. **Bulk** is best-effort with retransmission — used for mass-storage and most data. **Interrupt** is small, low-latency polled — keyboards, mice. **Control** is the setup channel. **Isochronous** reserves a fixed slice of every 125 µs microframe and never retransmits — used for audio and video where a late packet is worthless. The host scheduler allocates isochronous bandwidth at enumeration; if it cannot fit the camera's request, the device fails to start."
- §88.2 UVC descriptors and their parsing: one sentence describing what a descriptor *is* in USB terms: "USB descriptors are small fixed-format read-only blocks the device exposes during enumeration. UVC adds a class-specific descriptor tree under the standard Configuration descriptor — VS Format/Frame/Frame-Interval tables that enumerate every (format, resolution, frame-rate) combination the camera supports. `uvcvideo` walks this tree and turns each combination into a V4L2 enum entry."

---

## Ch 89 — I²S audio codecs

### AI wording / sledgehammer / buzzwords
- > "the analog-front-end chips that give the i.MX6ULL real audio — DAC for playback, ADC for capture, headphone/speaker drivers, mic preamps."
  - Triplet-plus list-as-prose. Rewrite: "These are the analog-front-end chips that give the i.MX6ULL real audio: DAC for playback, ADC for capture, headphone and speaker drivers, mic preamps."
- > "the i.MX6ULL's SAI is just a digital I²S serializer — it has no analog audio."
  - Em-dash glue. Rewrite: "The i.MX6ULL's SAI is a digital I²S serializer only. It has no analog audio."
- > "**a codec driver is regmap + DAPM widgets + DAI ops**."
  - Equation-as-prose bolded `Focus:`. Rewrite: "A codec driver has three parts: a regmap for register access, DAPM widgets and routes for the analog graph, and DAI ops for I²S format negotiation."
- > "Master these three and any codec driver reads the same."
  - "Master these three" is cliché. Rewrite: "Once you understand these three, every codec driver looks familiar."
- > "The single most important codec concept."
  - Hype line. Drop and let the section title carry it, or rewrite: "DAPM is the central concept in ASoC codec design."
- > "DAPM is why a well-written codec driver consumes µA at idle and doesn't click — and why a *badly* written one pops on every play/stop."
  - "Not X — and why Y" parallel sledgehammer. Rewrite: "DAPM is the reason a well-written codec driver draws µA at idle and stays silent between tracks. A badly-written one pops on every play and stop."
- > "Getting the routes and power-sequencing right is the bulk of codec-driver effort."
  - Fine, but "the bulk of effort" is cliché. Rewrite: "Getting the routes and power-sequence right is most of the work in a codec driver."
- > "That's the whole codec driver shape: regmap + DAI ops + component (controls + DAPM)."
  - Equation-as-prose. Rewrite: "Those four pieces — regmap, DAI ops, component (controls + DAPM) — are the whole codec driver."
- > "Real codecs are bigger, but the *structure* is identical."
  - Stock Claude line. Keep, but trim italics.

### ESL readability
- > "The DAPM graph models the analog signal paths (DAC → mixer → headphone-amp → jack) and powers each block only when it's in an active route — saving power and clicks."
  - 28-word sentence with parenthetical + em-dash + double benefit. Rewrite: "The DAPM graph models the analog signal paths: DAC → mixer → headphone amp → jack. Each block is powered up only when it lies on an active route, which saves power and avoids switching clicks."
- > "When you play audio: the stream activates 'Left DAC'; DAPM walks the graph forward — DAC → mixer → PGA → Headphone Jack — and powers on each widget in that path."
  - Colon + semicolon + em-dashes in 30 words. Rewrite: "When you play audio, the stream activates the 'Left DAC' widget. DAPM walks the graph forward: DAC → mixer → PGA → Headphone Jack. It powers on each widget along the way."
- > "Codecs need MCLK = a specific multiple of the sample rate (e.g., 256× or 512× fs). For 48 kHz: 12.288 MHz or 24.576 MHz."
  - Equation glyph in prose. Rewrite: "A codec needs MCLK to be a specific multiple of the sample rate, typically 256× or 512× fs. For 48 kHz that means 12.288 MHz or 24.576 MHz."

### Needs more depth — IMPORTANT for ESL/MCU reader, ASoC is hard
- §89.4 The three-driver ASoC split (machine/CPU-DAI/codec) is referenced ("Ch 53 showed the three-driver ASoC split (CPU-DAI + codec + machine) with WM8960") but never recapped in this chapter. The reader landing here without re-reading Ch 53 has no map. Add a 6-line recap at the start of §89.4:
  - "Three drivers cooperate to make ALSA audio work:
    1. **CPU-DAI driver** — owns the SAI (or SSI/I²S) peripheral. Knows how to push samples into the I²S serializer. Lives in `sound/soc/fsl/fsl_sai.c`. You do not write this for i.MX6ULL.
    2. **Codec driver** — owns the codec chip over I²C. Knows the codec's registers, DAPM graph, and DAI format constraints. This chapter is about writing one of these.
    3. **Machine driver** — the glue. Says 'connect the SAI's playback DAI to the WM8960's hifi DAI, in I²S format, with the WM8960 as clock slave.' Lives in either a custom `imx-audmux-wm8960.c` or, more commonly, the generic `simple-audio-card` driver consuming a DT description."
- §89.3 DAPM widget-vs-control-vs-route trio is dense. Add a 4-line example clarifying widget power bits: "A widget like `SND_SOC_DAPM_DAC('DAC', 'Playback', REG_POWER, 0, 0)` says: 'There is a DAC named DAC. Its DMA stream binding name is Playback. To power it on, set bit 0 of REG_POWER. The fifth argument (`0`) means active-high — write 1 to enable.' When DAPM decides this widget should be on, it does `update_bits(REG_POWER, 1<<0, 1<<0)` for you. You never set the bit by hand — DAPM owns it."
- §89.4 Regmap *write-only* register handling is mentioned correctly but the implication is buried. Add one sentence: "Write-only chips appear often in audio. Without `reg_defaults` and a cache, every read returns the cached zero, and `update_bits` (read-modify-write) silently corrupts state. The regmap cache is not optional — it is the only correct way to handle these chips."

---

## Ch 90 — Digital class-D amplifiers

### AI wording / sledgehammer / buzzwords
- > "'audio output without a codec' — chips that take I²S directly and drive a speaker (class-D amp) or headphones (DAC), with no ADC, no mic, no analog input mixing."
  - Triplet "no ADC, no mic, no analog input mixing" + em-dash chain. Rewrite: "These chips take I²S directly and drive a speaker (class-D amp) or headphones (DAC). They have no ADC, no mic input, and no input mixer — just a digital-in, analog-out path."
- > "(the MAX98357A is almost comically simple; the TAS5805M shows DSP-coefficient loading)."
  - "Almost comically simple" reads as editorial. Rewrite: "The MAX98357A driver is extremely short. The TAS5805M shows DSP-coefficient loading."
- > "you don't need a full codec (Ch 89). You need to turn I²S into sound."
  - "Not X. Y." sledgehammer. Rewrite: "A full codec (Ch 89) is overkill for playback-only products. All you need is to turn I²S into sound."
- > "The MAX98357A in particular needs *zero* configuration — wire I²S, pick L/R/mono via a resistor, done."
  - "Done." trim-and-stop pattern. Rewrite: "The MAX98357A needs zero configuration. Wire I²S, pick L/R/mono with a resistor, and it plays."
- > "**an amp-without-control is the simplest ASoC component possible**."
  - Bolded sledgehammer. Rewrite: "An amp without a control bus is the simplest ASoC component you can write."
- > "The spectrum from 'dumb amp' to 'smart DSP amp' maps cleanly to driver complexity."
  - Marketing-flavor. Rewrite: "Driver complexity tracks chip capability — dumb amp short, DSP amp long."
- > "The MAX98357A is the minimalist's dream."
  - Cliché. Rewrite: "The MAX98357A is as simple as it gets."
- > "That's it. No register access because there are no registers."
  - "That's it." pattern. Rewrite: "There is no register access in the driver because the chip has no registers."
- > "This is the *simplest possible ASoC component*."
  - Italic superlative. Rewrite: "This is the floor of ASoC complexity."
- > "The TAS5805M is the opposite extreme: a 2×23 W stereo class-D amp with an **on-chip DSP** offering:"
  - "The opposite extreme" cliché. Rewrite: "The TAS5805M sits at the other end. It is a 2×23 W stereo class-D amp with an on-chip DSP that provides:"
- > "a $5 speaker can sound like a $50 one with good DSP tuning. This is why class-D DSP amps dominate smart speakers."
  - Marketing. Rewrite: "Good DSP tuning makes a $5 speaker sound much better than its physical parts deserve. This is why DSP class-D amps are standard in smart speakers."
- > "The driver replays this blob at probe — like the camera (Ch 87) and ToF (Ch 72) register blobs."
  - Reasonable cross-reference. Keep.
- > "This is the canonical 'amp without a codec' use case."
  - "Canonical" overused. Rewrite: "This is the standard 'amp without a codec' product pattern."

### ESL readability
- > "Wire I²S (BCLK, LRCLK, DIN), power, speaker — and it plays."
  - List + dash + verb-without-subject. Rewrite: "Wire up I²S (BCLK, LRCLK, DIN), power, and a speaker. It plays."
- > "The DAPM `OUT_DRV_E` widget's event callback toggles the SD_MODE GPIO when the route activates (amp on during playback, off when idle — saving power)."
  - 24-word sentence with parenthetical-em-dash chain. Rewrite: "The `OUT_DRV_E` widget's event callback toggles the SD_MODE GPIO with the route. The amp is on during playback and off when idle, saving power."
- > "All configured over I²C. The DSP runs a *coefficient set* — you compute biquad coefficients (e.g., from a target frequency response) and load them into the chip's coefficient RAM."
  - Fragment "All configured over I²C." starts a paragraph. Rewrite: "All of this is configured over I²C. The DSP runs a *coefficient set*. You compute biquad coefficients (for example, from a target frequency response) and load them into the chip's coefficient RAM."

### Needs more depth
- §90.3 The DAPM `OUT_DRV_E` event mechanism is shown but the *event types* (`PRE_PMU`/`POST_PMU`/`PRE_PMD`/`POST_PMD`) are barely explained. An MCU reader who has not absorbed Ch 89's DAPM detail needs one sentence: "DAPM fires the event callback four times around any power transition — `PRE_PMU` before powering up, `POST_PMU` after, `PRE_PMD` before powering down, `POST_PMD` after. Class-D amps need `PRE_PMU` (settle the enable before the DAC drives signal) and `POST_PMD` (clear the GPIO after the DAC stops, to avoid pop)."
- §90.5 TAS5805M book/page register paging is unique enough to deserve a short example. Add 4 lines: "Selecting a coefficient page on the TAS5805M looks like: `write(0x00, 0x00); write(0x7F, 0x8C); write(0x00, 0x18);` — that is page 0x00, book 0x8C, page 0x18. Now register addresses 0x08..0xFF on this page are the biquad coefficients for filter slot 0. Forget the sequence and you write to whatever page was last selected — a different filter, the DRC config, or the device-id register."

---

## Ch 91 — SDIO WiFi

### AI wording / sledgehammer / buzzwords
- > "But it's also the hardest peripheral to bring up on a new board — the SDIO transport, the power sequence, the 32 kHz clock, the per-board NVRAM, and the firmware blob all have to be exactly right, and the failure mode is usually 'nothing in dmesg.'"
  - 44-word sentence with five-item list-as-prose. Rewrite: "SDIO WiFi is also the hardest peripheral to bring up on a new board. Five things must be exactly right: the SDIO transport, the power sequence, the 32 kHz clock, the per-board NVRAM, and the firmware blob. When any one is wrong, the symptom is usually 'nothing in dmesg.'"
- > "This chapter is mostly about the bring-up sequence and debugging."
  - Fine; keep.
- > "**the WiFi chip is a full-MAC co-processor; the driver is a firmware-loader + a SDIO-packet shuttle**."
  - Bolded sledgehammer with semicolon glue + equation-style "+". Rewrite: "The WiFi chip is a full-MAC co-processor. The Linux driver does two things only: it loads firmware, and it shuttles SDIO packets."
- > "Bring-up = getting the SDIO bus working + getting the right firmware + NVRAM. After that, the chip does the WiFi."
  - Equation-as-prose. Rewrite: "Bring-up is two jobs: get the SDIO bus working, then supply the right firmware and NVRAM. After that, the chip handles the actual WiFi."
- > "Miss any one and you get silence in dmesg."
  - Sledgehammer one-liner. Keep, but consider: "Miss any one of these and dmesg is silent."
- > "**Strongly prefer modules with in-tree drivers** (AP6212/brcmfmac, SD8801/mwifiex)."
  - Bolded recommendation followed by a parenthetical. Rewrite: "Strongly prefer modules with in-tree drivers — AP6212 with brcmfmac, SD8801 with mwifiex."
- > "The $0.50 you save on an RTL8189 vs an AP6212 is dwarfed by the engineering cost of maintaining an out-of-tree driver across an 8-year product life."
  - "Dwarfed by" cliché. Rewrite: "Saving $0.50 on an RTL8189 versus an AP6212 is nothing compared to the engineering cost of maintaining an out-of-tree driver for an 8-year product life."
- > "So brcmfmac is fundamentally: a firmware loader + an SDIO packet shuttle + a cfg80211↔Broadcom-command translator. ~15000 lines, but conceptually those three jobs."
  - Equation-as-prose + sentence-fragment "~15000 lines, but conceptually those three jobs." Rewrite: "So brcmfmac is three things: a firmware loader, an SDIO packet shuttle, and a cfg80211-to-Broadcom command translator. The source is ~15000 lines, but conceptually it is those three jobs."

### ESL readability
- > "SDIO uses the same physical bus and protocol as an SD card (Ch 66), but instead of 'read/write blocks of storage,' the device exposes **I/O functions** — registers and an interrupt."
  - 30-word sentence with embedded quote + em-dash. Rewrite: "SDIO uses the same physical bus and protocol as an SD card (Ch 66). Instead of reading and writing storage blocks, the device exposes **I/O functions** — a set of registers and an interrupt line."
- > "The progression:"
  - Fine.
- > "The Linux side stops at 'write bytes to SDIO FIFO.' Everything 802.11 happens in the chip's firmware."
  - Two short sentences with embedded quote — keep.
- > "For a *product*, **don't use RTL8188EUS** unless you need its AP/monitor features."
  - "For a *product*" italic stress. Keep, but the bold is unnecessary; the imperative is clear.

### Needs more depth — important, the wpa_supplicant/nl80211/cfg80211 stack is hard
- §91.3 The cfg80211 / nl80211 / mac80211 / mac-driver layering is dense. The current §91.3 diagram lists boxes but does not explain *which* layer does what. An MCU reader needs a clear breakdown — this is one of the hardest concepts in Linux networking. Add a 12-line block:
  - "**nl80211** is a kernel-internal netlink protocol — the wire format wpa_supplicant uses to talk to the kernel WiFi stack. Think of it as 'WiFi's ioctl, but on a netlink socket.' Userspace tools (`iw`, `wpa_supplicant`, NetworkManager) all speak nl80211.
  - **cfg80211** is the kernel-side server for nl80211. It receives nl80211 messages (scan, connect, set-key) and calls per-driver callbacks. Every WiFi driver registers cfg80211 ops. cfg80211 also enforces the regulatory database (what channels are allowed in what country) and tracks scan results.
  - **mac80211** is an optional middleware layer between cfg80211 and the chip driver. It implements the 802.11 MAC state machine (authentication, association, rate selection, encryption) in software, for chips that are 'soft-MAC' — i.e., where the chip is just a radio and Linux runs the MAC. RT5370 (Ch 92), MT7601, and most Atheros chips use mac80211.
  - **Full-MAC chips** (BCM43438, Marvell SD8801, Realtek RTW88 family) run the 802.11 MAC inside the chip's firmware. Their Linux drivers skip mac80211 and implement cfg80211 ops directly. brcmfmac is full-MAC.
  - From wpa_supplicant's view, the layering is transparent — it sends nl80211 'connect' and the kernel handles the rest. Knowing which layer your chip uses tells you where to read the kernel source when something goes wrong."

---

## Ch 92 — USB WiFi

### AI wording / sledgehammer / buzzwords
- > "USB WiFi dongles — the plug-in alternative to soldered SDIO WiFi (Ch 91)."
  - Fine.
- > "The defining theme: the **in-tree vs out-of-tree driver saga** — which dongles 'just work' and which require a DKMS nightmare."
  - "Saga," "nightmare" — both loaded. Rewrite: "The big theme here is in-tree versus out-of-tree drivers. Some dongles just work. Others need a constantly-rebuilt DKMS module."
- > "**the chip you buy determines whether WiFi is a 5-minute job or a 5-day ordeal**."
  - Bolded marketing. Rewrite: "The chip you buy determines whether bringing up WiFi takes five minutes or five days."
- > "Choosing the right chip is the entire game."
  - Cliché. Rewrite: "Chip choice is most of the work."
- > "**If you want zero hassle, buy an RT5370 dongle.**"
  - Bolded conversational instruction. Rewrite: "For the lowest-hassle path, buy an RT5370 dongle."
- > "The most *common* dongle, the most *painful* driver."
  - Stylized rhetorical balance. Rewrite: "The most common dongle, but the most painful driver."
- > "Total bring-up: insert dongle, copy firmware (if not present), connect. Five minutes."
  - List-as-prose with mic-drop "Five minutes." Rewrite: "Total bring-up is three steps. Insert the dongle. Copy the firmware if it is not present. Connect. About five minutes."
- > "**RT5370 / MT7601 use mac80211** (soft-MAC) — the kernel does the 802.11 MAC, the chip is a radio. This is why they integrate so cleanly: mac80211 + cfg80211 handle everything; the chip driver is a thin USB+radio shim."
  - 30 words with em-dash + semicolon + "+". Rewrite: "RT5370 and MT7601 are *soft-MAC* chips. They use mac80211: the kernel does the 802.11 MAC, the chip is just a radio. This is why integration is clean. mac80211 and cfg80211 handle the protocol work, and the chip driver is a thin USB-to-radio shim."

### ESL readability
- > "But it's out-of-tree:"
  - Fragment to introduce a code block. Acceptable.
- > "Each kernel bump may require patching the driver."
  - Fine.
- > "Pin the kernel or use DKMS — or pick an in-tree module."
  - Double em-dash. Rewrite: "Pin the kernel, use DKMS, or — better — pick an in-tree module."
- > "Some 'USB WiFi' is a soldered module (not a dongle) — same driver story, but now you can't swap the chip if the driver is bad."
  - "Same driver story" idiom. Rewrite: "Some 'USB WiFi' is a soldered-on module, not a removable dongle. The driver situation is the same, but now you cannot swap the chip if the driver turns out to be bad."

### Needs more depth
- §92.2 The mac80211 path is good, but the mention is one parenthetical. Forward-link to Ch 91's added cfg80211/mac80211 explanation, or recap two lines: "RT5370 is a *soft-MAC* chip. Its driver implements mac80211 ops (transmit a single frame, receive, set-channel) and mac80211 handles the rest of 802.11. Compare to AP6212 (Ch 91), where the chip firmware runs the MAC and Linux's mac80211 is bypassed entirely."
- §92.5 USB-2.0 isochronous bandwidth and how WiFi reservations interact with cameras (Ch 88) — the chapter mentions "compete" but never names *isochronous bandwidth reservation* as the mechanism. One sentence: "USB WiFi uses bulk transfers, not isochronous, so it cannot 'reserve' bandwidth. UVC cameras (Ch 88) do reserve isochronous bandwidth. The net effect: a high-res webcam can starve the WiFi dongle's bulk endpoint, but rarely the reverse."

(Short chapter — kept findings to top-5 highest impact.)

---

## Ch 93 — Hosted WiFi via ESP32 / ESP8266

### AI wording / sledgehammer / buzzwords
- > "**two fundamentally different offload models**."
  - Bolded "fundamentally." Rewrite: "Two very different offload models."
- > "esp-hosted: the ESP is a *dumb radio* — Linux runs the IP stack, the ESP just moves 802.11 frames (Linux sees `wlan0`, runs wpa_supplicant, full control). AT-command: the ESP is a *smart modem* — it runs its own TCP/IP, Linux sends `AT+CIPSTART` and gets a socket-like abstraction (simple, but limited and non-standard)."
  - 55-word two-sentence pair with double em-dashes and parentheticals. Break into four sentences: "esp-hosted treats the ESP as a *dumb radio*. Linux runs the IP stack and just sends 802.11 frames through the ESP. From Linux's view there is a normal `wlan0` with wpa_supplicant on top. AT-command treats the ESP as a *smart modem*. The ESP runs its own TCP/IP stack and Linux speaks `AT+CIPSTART` to open sockets. Simple, but limited and non-standard."
- > "Picking between them shapes everything."
  - Cliché. Rewrite: "The choice between them shapes the rest of the design."
- > "The last point is underrated:"
  - Editorial. Rewrite: "One often-missed advantage:"
- > "an ESP32 *module* (not bare chip) ships with FCC/CE/IC modular certification. Bolt it on, and your product inherits the RF certification — no expensive antenna-certification of your own design. This alone justifies hosted WiFi for low-volume products."
  - 41-word run with em-dash and editorial "alone justifies." Rewrite: "An ESP32 *module* (not the bare chip) ships with FCC/CE/IC modular certification. If you mount the module without changing the antenna, your product inherits the certification. You skip an expensive antenna-certification step. For low-volume products, this alone can justify hosted WiFi."
- > "And you maintain the ESP firmware in addition to the Linux side."
  - "And you maintain" sentence-starter. Rewrite: "You also maintain the ESP firmware on top of the Linux side."
- > "Linux talks to the ESP like a dial-up modem:"
  - Fine; keep.
- > "The right choice for a real product. Requires the esp-hosted firmware + the Linux driver."
  - Two fragments. Rewrite: "It is the right choice for production. You need both the esp-hosted firmware on the ESP and the matching Linux driver."
- > "Common in quick prototypes and MCU-style code. Avoid for anything that needs the Linux network ecosystem."
  - Two fragments. Rewrite: "AT-command mode is common in quick prototypes and in MCU-style code. Avoid it for any product that needs Linux's network ecosystem (sockets, TLS, multiple connections, NetworkManager)."

### ESL readability
- > "esp-hosted also relays Bluetooth (HCI over the same transport) — so one ESP32 gives Linux both `wlan0` and an `hci0`."
  - Em-dash glue. Rewrite: "esp-hosted also relays Bluetooth, sending HCI over the same transport. So one ESP32 gives Linux both `wlan0` and `hci0`."
- > "The ESP's transport protocol multiplexes: WiFi-STA frames, WiFi-AP frames, BT-HCI packets, and control commands all flow over the same SPI link, distinguished by an `if_type` field in the header."
  - 31-word colon-introducing run-on. Rewrite: "The ESP's transport protocol multiplexes several streams over the same SPI link: WiFi-STA frames, WiFi-AP frames, BT-HCI packets, and control commands. An `if_type` field in the header distinguishes them."
- > "Same shape as brcmfmac (Ch 91), but the transport is the esp-hosted SPI protocol instead of SDIO."
  - "Same shape" idiom. Keep, but rewrite: "The structure mirrors brcmfmac (Ch 91). Only the transport changes — the esp-hosted SPI protocol instead of SDIO."
- > "For a kernel-integrated AT-mode (making it look like a network interface), `drivers/net/ppp/` + a chat script can layer PPP over the AT link — but esp-hosted is the better path if you want a real `wlan0`."
  - 38-word sentence with parenthetical-as-clarifier + em-dash. Rewrite: "If you want AT-mode to look like a network interface, the kernel's PPP driver (`drivers/net/ppp/`) plus a chat script can layer PPP over the AT link. esp-hosted is still the better choice for a real `wlan0`, though."

### Needs more depth
- §93.4 The "control packet" path (cfg80211 op → protobuf-encoded control request → ESP firmware → response) is described in one sentence but is the most interesting part. Add 6 lines: "On the control side, esp-hosted defines a small protobuf-based RPC. cfg80211 ops on the Linux side (`.scan`, `.connect`, `.set_key`) build a protobuf request, prepend the same `if_type` framing as data packets but with `if_type=CTRL`, and send it over the SPI link. The ESP firmware deserializes the protobuf, calls Espressif's `esp_wifi_*` APIs in its own RTOS, and returns the result framed the same way. This RPC pattern is how a single transport carries data and control without ambiguity — the same model FlexCAN, slcan, and many radio modems use."
- §93.5 The AT-command "you'll need a TLS-capable firmware" caveat is one parenthetical. Worth a sentence: "Espressif's AT firmware ships in two variants: bare TCP and a larger TLS-capable build with mbedTLS. The TLS variant is bigger and slower on the ESP, but it lets a small Linux host avoid bringing in OpenSSL. Pick at firmware-flash time."

---

## Ch 94 — WiFi+BT combo modules

### AI wording / sledgehammer / buzzwords
- > "modules that pack WiFi *and* Bluetooth into one chip sharing one 2.4 GHz antenna"
  - "Pack X and Y" idiom. Rewrite: "Modules that combine WiFi and Bluetooth on one chip, sharing one 2.4 GHz antenna."
- > "The defining challenges: bringing up *two* radios on *one* chip over *two* different buses, and the **coexistence** problem — both radios fighting over the same 2.4 GHz band and the same antenna."
  - 32 words, italics, em-dash, "fighting over" metaphor. Rewrite: "Two challenges define the topic. First, you must bring up two radios on one chip over two different buses. Second, the coexistence problem: both radios share the same 2.4 GHz band and the same antenna."
- > "But bringing up both halves — WiFi on SDIO (Ch 91) *and* BT on UART — and getting them to coexist is more than twice the work of either alone."
  - 26-word run-on with double em-dash. Rewrite: "Bringing up both halves takes more than twice the effort of either alone — WiFi on SDIO (Ch 91), BT on UART, then making them coexist."
- > "**one chip, two buses, two subsystems, one antenna**."
  - Bolded four-item triplet (quadruplet) `Focus:`. Keep but un-bold or rewrite as prose: "One chip carries two radios on two buses. They share one antenna and are managed by two independent kernel subsystems."
- > "They're independent driver stacks that happen to share silicon."
  - "Happen to share" idiom. Rewrite: "The two stacks are independent. They share silicon, but nothing else in software."
- > "Nothing new. The combo module's WiFi is just an AP6212-WiFi as in Ch 91."
  - Two-fragment dismissal. Acceptable in context (it's recapping). Could merge: "Nothing new — the combo module's WiFi is exactly the AP6212 case from Ch 91."
- > "Common mistake: getting WiFi working, declaring victory, shipping — then discovering BT was never wired up correctly. Test both, separately and together."
  - "Declaring victory" idiom + em-dash sting. Rewrite: "A common mistake is to get WiFi working and assume the job is done. Then a field unit fails because the BT side was never wired correctly. Test both, separately and together."

### ESL readability
- > "WiFi throughput craters, BT audio stutters."
  - "Craters" is informal English. Rewrite: "WiFi throughput collapses and BT audio stutters."
- > "The chip solves this internally with **PTA** (Packet Traffic Arbitration, also called coexistence or 'coex'): a hardware arbiter that time-slices the radio between WiFi and BT, prioritizing based on packet type (BT audio is latency-sensitive → high priority; WiFi bulk data → can wait a few ms)."
  - 47-word colon-introducing run-on with arrow and parenthetical. Break: "The chip solves this internally with **PTA** (Packet Traffic Arbitration, also called coexistence or 'coex'). PTA is a hardware arbiter that time-slices the radio between WiFi and BT, prioritising by packet type. BT audio is latency-sensitive and gets high priority. WiFi bulk data can wait a few ms."
- > "The drop is the 'cost' of coexistence — typically 10–30 % WiFi throughput reduction during active BT."
  - Fragment-quoted "cost" + em-dash. Rewrite: "This drop is the cost of coexistence — typically 10 to 30 percent less WiFi throughput while BT is active."
- > "(declare it once, reference from both pwrseq and the BT node)"
  - Concise; keep.

### Needs more depth
- §94.4 The HCI layering (BlueZ daemon → kernel BT subsystem → hci_uart line discipline → controller) is one diagram with no explanation of what each layer does. For an MCU reader meeting Bluetooth here, add 6 lines:
  - "**bluetoothd** is the BlueZ user-space daemon. It owns GAP (advertising/scanning), GATT (services and characteristics), SMP (pairing), and the higher profiles (A2DP audio, HID keyboards). Applications talk to it over D-Bus.
  - **The kernel BT subsystem** (`net/bluetooth/`) exposes a socket family (`AF_BLUETOOTH`) and implements HCI transport, L2CAP, and the lower stack. bluetoothd opens an HCI socket and sends commands through this layer.
  - **hci_uart line discipline** turns a UART into an HCI transport. It frames H4 packets (one type byte + payload) on the wire and presents `hci0` to the kernel. `hci_bcm` is a vendor-glue module that loads the Broadcom firmware patch and handles the baud-rate switch."
- §94.5 Coexistence: the "three-wire coex" between separate WiFi and BT chips is mentioned in one sentence but never named in standard form. Add: "When WiFi and BT live on separate chips, they negotiate over a three-wire PTA bus: BT_PRIORITY (BT says 'I am about to transmit, importance is X'), BT_ACTIVE (BT is transmitting now), and WLAN_ACTIVE (WiFi is transmitting now). Each chip uses the other's signals to defer or steal the radio. Combo modules collapse this into on-die arbitration, which is faster and quieter."

---

## Ch 95 — HCI Bluetooth over UART/USB

### AI wording / sledgehammer / buzzwords
- > "since you don't write the HCI controller (it's the chip's firmware) — building a **BLE GATT peripheral** in user-space via BlueZ's D-Bus API (the meaningful 'build it yourself' part)."
  - 30+ word sentence with em-dash and quoted "build it yourself." Rewrite: "You will not write the HCI controller — that lives in the chip's firmware. What you do build is a **BLE GATT peripheral**, in user-space, through BlueZ's D-Bus API."
- > "Understanding HCI demystifies the whole stack; building a GATT peripheral is the practical skill."
  - "Demystifies" is buzzy. Semicolon glue. Rewrite: "Understanding HCI makes the rest of the stack feel less magical. Building a GATT peripheral is the practical skill."
- > "**the controller runs the BT link layer; you build the GATT application**."
  - Bolded `Focus:` with semicolon glue. Rewrite: "The controller (chip firmware) runs the BT link layer. You build the GATT application on top."
- > "Your code is the 'application' — a GATT server exposing characteristics."
  - Em-dash glue. Rewrite: "Your code is the 'application' layer. It is a GATT server that exposes characteristics."
- > "You don't touch HCI directly; you define services and BlueZ handles the rest."
  - Semicolon glue. Rewrite: "You do not touch HCI directly. You define services, and BlueZ handles the rest."
- > "The from-scratch deliverable is a GATT peripheral, written against BlueZ's D-Bus API."
  - Fine.
- > "You rarely send raw HCI — BlueZ does. But understanding it lets you read `btmon` traces (which decode every HCI packet) and debug."
  - Two short sentences but "But understanding" is awkward. Rewrite: "You rarely send raw HCI yourself. BlueZ does it for you. Knowing the format lets you read `btmon` traces and debug."
- > "(The full example needs the service-object + advertisement-object registration boilerplate — ~250 lines total. BlueZ ships a complete `example-gatt-server` in `test/` that you adapt.)"
  - Parenthetical-as-paragraph + em-dash. Move out of parentheses: "The full example needs the service-object and advertisement-object registration boilerplate — about 250 lines in total. BlueZ ships `example-gatt-server` in `test/` and most production code starts from that."
- > "This is the canonical 'BLE sensor that talks to a phone app' pattern."
  - "Canonical" overused in this batch (5+ occurrences). Drop: "This is the standard pattern: a BLE sensor talking to a phone app."

### ESL readability — multiple long sentences
- > "**HCI** (Host Controller Interface) is the standardized boundary between the *host* (Linux + BlueZ) and the *controller* (the BT chip). It's a packet protocol with four packet types:"
  - 28-word sentence with three parentheticals. Rewrite: "**HCI** (Host Controller Interface) is the standardised boundary between two halves of any Bluetooth system: the *host* (Linux plus BlueZ) and the *controller* (the BT chip). HCI is a packet protocol. It defines four packet types:"
- > "BlueZ's `LEAdvertisingManager1` D-Bus interface controls advertising; you register an advertisement object specifying the name, service UUIDs, and any manufacturer-specific data."
  - Semicolon glue, 22 words. Rewrite: "BlueZ exposes a `LEAdvertisingManager1` D-Bus interface that controls advertising. You register an advertisement object with the name, service UUIDs, and any manufacturer-specific data."
- > "More code, but no Python runtime + better performance."
  - "+" used as conjunction. Rewrite: "More code, but no Python runtime and better performance."

### Needs more depth — IMPORTANT, BlueZ + GATT + D-Bus is dense
- §95.3 The BlueZ architecture diagram lists four layers but does not explain *what GATT is* in protocol terms. For an MCU reader who has only read about UART-style serial Bluetooth, add 6 lines:
  - "**GATT** (Generic Attribute Profile) is BLE's data model — every BLE service exposed by a peripheral is a tree of *attributes*, each addressed by a 16-bit *handle* and tagged with a UUID. A *service* attribute groups *characteristic* attributes; a characteristic attribute groups a *value* attribute and any *descriptors* (units, format, configuration). A central reads or writes a characteristic by handle and UUID, or it *subscribes* (writes 0x01 to the Client Characteristic Configuration descriptor) and the peripheral notifies it on change.
  - GATT runs on top of **ATT** (Attribute Protocol), a tiny request/response protocol on top of **L2CAP**, which runs on top of HCI ACL packets. Five layers, but you only ever touch the top one through BlueZ's D-Bus API."
- §95.6 The Python GATT-server example is presented but the *D-Bus object registration* is elided as "boilerplate." For a reader new to D-Bus, add a short paragraph naming the missing pieces: "The missing boilerplate is: (1) a service object inheriting `dbus.service.Object` and exporting `GetManagedObjects` so `org.bluez` can discover the tree; (2) registration with `org.bluez.GattManager1.RegisterApplication`; (3) an `LEAdvertisement1` object describing the advertising data; (4) registration with `org.bluez.LEAdvertisingManager1.RegisterAdvertisement`. The BlueZ sample in `test/example-gatt-server` shows all four. Read that file alongside this chapter."
- §95.7 GAP is only mentioned in passing. One paragraph: "**GAP** (Generic Access Profile) is BLE's connection lifecycle. It defines the *roles* (peripheral, central, broadcaster, observer), the *advertising* and *scanning* state machines, and the *connection parameters* (interval, latency, supervision timeout). A peripheral advertises in one of three modes (connectable undirected, connectable directed, non-connectable). A central scans (passive or active) and may initiate a connection. After connection, GAP yields to GATT. BlueZ's `Adapter1` interface owns the GAP-level controls; once you connect, you mostly use `GattCharacteristic1` instead."

---

## Ch 96 — AT-command BLE modules

### AI wording / sledgehammer / buzzwords
- > "The module *is* the Bluetooth stack; Linux just talks to a UART."
  - Italic "is" + semicolon glue. Rewrite: "The module is the Bluetooth stack. Linux only talks to a UART."
- > "The trade-off: you're limited to the module's fixed GATT profile (usually a single 'transparent UART' characteristic), max ~few hundred bytes/sec, and a non-standard, vendor-specific command set."
  - 30-word colon-introducing run-on with two parentheticals. Rewrite: "The trade-off is real. You are stuck with the module's fixed GATT profile, usually a single 'transparent UART' characteristic. Throughput tops out at a few hundred bytes per second. The AT command set is vendor-specific and non-standard."
- > "**the module is a 'BLE-to-serial cable'**."
  - Bolded `Focus:`. Rewrite: "The module behaves like a wireless serial cable."
- > "It's a wireless serial port. Linux needs *zero* Bluetooth code — just open `/dev/ttymxc2` and read/write."
  - "Zero" + italic + em-dash. Rewrite: "It is a wireless serial port. Linux needs no Bluetooth code — just open `/dev/ttymxc2` and call `read`/`write`."
- > "**The cloning problem**: 'HM-10' modules are cloned five ways, with different firmware and *different AT command syntax*."
  - "Cloned five ways" is idiomatic + bolded subheading-in-prose. Rewrite: "**Clone variants are a real problem.** There are at least five different 'HM-10' modules in the market, each with different firmware and different AT command syntax."
- > "This is *the* reason to use an AT-BLE module: your application code is just serial I/O. No D-Bus, no GATT objects, no BlueZ daemon."
  - Italic "the" + triplet rhythm. Rewrite: "This is the main reason to choose an AT-BLE module. Your application is plain serial I/O — no D-Bus, no GATT objects, no BlueZ daemon."
- > "Compare to Ch 95's GATT server: ~250 lines of D-Bus code vs ~10 lines of serial I/O. The AT module trades capability for simplicity."
  - "Trades capability for simplicity" is reasonable but Claude-flavored. Keep, but rewrite: "Compare to Ch 95's GATT server: about 250 lines of D-Bus code versus ten lines of serial I/O. AT modules trade features for simplicity."
- > "The AT module is for quick, simple, 'wireless serial cable' use."
  - Triplet ("quick, simple, 'wireless serial cable'"). Rewrite: "The AT module fits quick, simple 'wireless serial cable' use cases."

### ESL readability
- > "(Note: genuine HM-10 commands have *no* `\r\n` terminator and *no* `=` for sets in older firmware — e.g., `AT+NAMEMyDevice` not `AT+NAME=MyDevice`. Clones vary. The `AT+VERS?` response identifies your variant.)"
  - 32-word parenthetical block. Move out: "Caveat on syntax. The genuine HM-10 commands omit the `\r\n` terminator and the `=` sign for set commands in older firmware (e.g., `AT+NAMEMyDevice`, not `AT+NAME=MyDevice`). Clone command sets vary. Run `AT+VERS?` first — the version response identifies your variant."
- > "That's the entire integration — no Bluetooth code, just `read`/`write` on a UART."
  - "That's the entire" trim-and-stop. Rewrite: "That is the whole integration. There is no Bluetooth code — just `read` and `write` on a UART."

### Needs more depth
- §96.2 The "transparent UART" model is the chapter's central idea but never explains *how* the module presents it on the BLE side. Add 4 lines: "On the BLE side, the module exposes a single vendor service (UUID varies by module — `ffe0` for HM-10) with two characteristics: a notify characteristic for module-to-phone data, and a write characteristic for phone-to-module data. The phone app subscribes to notifications and writes to the write characteristic. The module bridges these characteristics to its UART TX and RX. No GATT discovery is needed by the user — phone apps like 'Serial Bluetooth Terminal' know the HM-10's UUIDs by name."
- §96.5 The "wrong choice when" list is good, but the *throughput limit* deserves the math: "BLE 4.x connection events run at intervals of 7.5 ms to 4 s, negotiated. Each event can carry one ATT MTU's worth of data (default 23 bytes, often negotiated to 247). At a 30 ms connection interval and 20-byte payload, raw rate is ~5.3 KB/s. Most AT modules cap at the default MTU and a 100 ms interval, giving ~200 B/s in practice. Above this rate, modules drop bytes silently — there is no flow control between the UART side and the BLE side."

(Short chapter — kept to top issues.)

---

## Ch 97 — BLE Mesh

### AI wording / sledgehammer / buzzwords
- > "We cover the mesh architecture (elements, models, addresses, publish/subscribe), the **bluez-mesh** stack on Linux, provisioning a node into a network, and a worked lighting-control example with the i.MX6ULL as a mesh gateway/provisioner."
  - 35-word list-as-prose. Rewrite: "This chapter covers four things: the mesh architecture (elements, models, addresses, publish/subscribe), the **bluez-mesh** stack on Linux, the provisioning flow that adds a node to a network, and a worked lighting-control example with the i.MX6ULL as gateway and provisioner."
- > "smart lighting (the killer app), building sensors, industrial monitoring — by having nodes *relay* each other's messages."
  - "Killer app" cliché. Rewrite: "smart lighting (the dominant use case), building sensors, industrial monitoring. Nodes relay each other's messages to extend coverage."
- > "It's the technology behind commercial smart-lighting systems (the kind in offices and warehouses)."
  - Editorial parenthetical. Rewrite: "It is the technology behind commercial smart-lighting systems, the kind installed in offices and warehouses."
- > "An i.MX6ULL makes an excellent mesh **gateway** (bridging the mesh to WiFi/cloud) or **provisioner** (adding nodes to the network)."
  - 23-word sentence with two parentheticals. Rewrite: "An i.MX6ULL makes a good mesh gateway, bridging mesh traffic to WiFi or the cloud. It can also act as a provisioner, adding new nodes to the network."
- > "**mesh is publish/subscribe over flooded BLE adverts, addressed by models**."
  - Bolded equation-style `Focus:`. Rewrite: "Mesh is a publish/subscribe protocol layered on flooded BLE advertisements, with addresses tied to models."
- > "'Turn off all kitchen lights' = publish OnOff=0 to the 'kitchen' group; every light subscribed to 'kitchen' responds."
  - Equation glyph + semicolon. Rewrite: "'Turn off all kitchen lights' means: publish OnOff=0 to the 'kitchen' group. Every light subscribed to 'kitchen' responds."
- > "Flooding + relay gives whole-building coverage without infrastructure."
  - "+" + buzzword "infrastructure." Rewrite: "Flooding plus relay gives whole-building coverage without any backbone wiring."
- > "Mesh trades the simplicity of point-to-point for scale and coverage."
  - Stock Claude phrasing ("trades X for Y"). Rewrite: "Mesh sacrifices some point-to-point simplicity. In return you get scale and coverage."
- > "A message 'hops' node-to-node: a light in the far room relays a message it overhears, extending range far beyond one radio's reach."
  - 23-word sentence with colon + comma chain. Rewrite: "A message hops node-to-node. A light in a far room can relay a message it overhears, extending the range far beyond a single radio's reach."
- > "That's the power of group addressing."
  - Mic-drop line. Rewrite: "Group addressing is what makes this possible."
- > "the canonical role for a Linux device in a mesh network"
  - "Canonical" overused. Rewrite: "the typical role for a Linux device in a mesh network."
- > "This is analogous to the GATT server of Ch 95 but for mesh models — more involved, and the bluez-mesh D-Bus API is less mature than the GATT one."
  - "Analogous to" formal + em-dash + "more involved" fragment-ish. Rewrite: "The structure is similar to the GATT server of Ch 95 but applies to mesh models. It is more involved, and the bluez-mesh D-Bus API is less mature than the GATT one."

### ESL readability
- > "BLE point-to-point (Ch 95) reaches one device at ~30 m. BLE Mesh covers an entire building with hundreds of nodes — smart lighting (the killer app), building sensors, industrial monitoring — by having nodes *relay* each other's messages."
  - 41-word two-sentence run with double em-dash. Already addressed above.
- > "Mesh has sequence-number replay protection; if a node's stored sequence state is lost (flash erased), it may be rejected."
  - Semicolon glue. Rewrite: "Mesh uses sequence numbers as replay protection. If a node's stored sequence state is lost (because its flash was erased), the network may reject it."
- > "Plan addressing (unicast ranges, group allocation) before deploying hundreds of nodes."
  - Parenthetical readable; keep.

### Needs more depth
- §97.2 The mesh `model` concept is the key abstraction but described only as "the functional units." For an MCU reader, add a worked example showing the bytes on the wire: "A 'Generic OnOff Set' message published by a wall switch to address 0xC000 is a 7-byte access payload: opcode 0x8202 (Generic OnOff Set Unacknowledged), 1 byte OnOff value (0x01 or 0x00), 1 byte transaction ID, optional 2 transition-time bytes. Encrypted with the AppKey, prepended with sequence number + source address + destination 0xC000, encrypted again with the NetKey, then transmitted on the BLE advertising channels. Subscribed Generic OnOff Server models on every kitchen light receive, decrypt twice, decode the opcode, and act on the value. The model defines which opcodes a server handles and which messages a client may publish."
- §97.4 The split between bluetoothd and bluetooth-meshd is mentioned in the pitfalls but never explained where it matters. Add a paragraph in §97.4: "bluetoothd and bluetooth-meshd cannot both own the same HCI controller. Both want exclusive access to advertising and scanning. On a single-controller system, you either run mesh (lose GATT/classic) or run GATT/classic (lose mesh). Production designs that need both use two controllers — one for mesh, one for non-mesh BT — typically a combo module for GATT/classic and a separate dongle (USB or a second UART) for mesh."
- §97.3 Provisioning is one of the most security-critical operations in any IoT product. The current description is procedural but does not explain *why* each step matters. Add three short notes after the seven-step list:
  - "**Why ECDH?** The provisioner and the unprovisioned device derive a session key without ever transmitting it. An attacker passively sniffing the air sees the public keys but cannot reconstruct the shared secret. Without this, mesh would be trivially crackable.
  - **Why OOB authentication?** ECDH defeats passive sniffing but not active man-in-the-middle. OOB (a code on the device's label, a number to confirm on its display, a QR code) lets the user verify they are provisioning *this* device, not an attacker's clone sitting next to it.
  - **Why does the NetKey not encrypt the payload?** Relay nodes need to read the destination address and forward the packet. They do not need to read the application data. The two-key scheme (NetKey for routing, AppKey for content) is what lets cheap relay nodes participate without holding application secrets."



