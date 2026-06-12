---
chapter: 84
title: QSPI LCD (high-bandwidth quad-SPI displays)
part: VII - Device cookbook
estimated_pages: 16
status: draft
---

# Chapter 84: QSPI LCD

> **What:** displays driven over **quad-SPI** (4 data lanes instead of 1) for ~4× the bandwidth of plain SPI. Common on round smartwatch-style LCDs: **GC9D01** (round 160×160), **ST77916** (round 360×360), **SH8601** (AMOLED). We cover why QSPI matters for displays, the quad-mode MIPI-DBI command framing, the i.MX6ULL QSPI controller's display-mode constraints, and how the mainline `mipi-dbi` helper handles quad transfers.
>
> **Why:** a plain-SPI 360×360 16-bit display needs 259 KB per frame, at 40 MHz SPI that's 52 ms = ~19 fps full-refresh, too slow for smooth animation. Quad-SPI quadruples the data rate to about 13 ms per frame, or 75 fps. That is the difference between smooth animation and a slideshow. QSPI is newer and less common. Fewer mainline drivers exist, so you are more likely to write your own.
>
> **Focus:** **QSPI display = MIPI-DBI commands sent over 4 data lanes**. The command model is identical to Ch 83 (CASET/RASET/RAMWR), but each byte's 8 bits are spread across 4 IO lines (2 bits per line per clock), so pixels stream 4× faster. The challenge is that the i.MX6ULL QSPI controller is designed for *flash*, not displays, using it for a display means working within its command-LUT model.


## 84.1  Why QSPI for displays

Bandwidth math for a full-frame refresh at 16-bit color:

| Display | Pixels | Bytes/frame | @40 MHz SPI (1-bit) | @40 MHz QSPI (4-bit) |
|---------|--------|-------------|---------------------|----------------------|
| 240×240 | 57600 | 115 KB | 23 ms (43 fps) | 6 ms (170 fps) |
| 360×360 | 129600 | 259 KB | 52 ms (19 fps) | 13 ms (77 fps) |
| 454×454 | 206116 | 412 KB | 82 ms (12 fps) | 21 ms (48 fps) |

For small displays plain SPI is fine. For 360×360+ round AMOLEDs (smartwatch class), QSPI is needed for smooth animation. Partial updates (Ch 83) help, but full-frame animation (a sweeping watch hand redrawing the whole face) needs the bandwidth.

## 84.2  Quad-SPI signaling

Plain SPI: 1 data line (MOSI), 1 bit per clock. Quad-SPI: 4 data lines (IO0–IO3), 4 bits per clock, 4× the throughput at the same clock rate.

```
   Plain SPI:   MOSI ─ b7 b6 b5 b4 b3 b2 b1 b0   (8 clocks per byte)

   Quad SPI:    IO3 ─ b7 b3      (2 clocks per byte)
                IO2 ─ b6 b2
                IO1 ─ b5 b1
                IO0 ─ b4 b0
```

For displays, a common framing (the "QSPI display" convention used by these controllers):

- **Command phase**: single-lane (IO0 only), with a leading "command marker" byte.
- **Address phase**: single-lane or quad.
- **Data phase**: quad-lane (pixels stream 4× fast).

The exact framing is controller-specific. A typical ST77916 write:

```
   /CS↓
   single-lane: 0x02 (write marker) + 0x00 + cmd + 0x00
   quad-lane:   pixel data ...
   /CS↑
```

## 84.3  The i.MX6ULL QSPI-for-display problem

The i.MX6ULL QSPI controller (`fsl-quadspi`) was designed for **NOR flash** (Ch 64), not displays. It works through a **LUT** (look-up table) of pre-programmed command sequences, you fill LUT entries describing "command + address + dummy + data" phases, then trigger them.

For a display, this is awkward:

- The flash-oriented driver assumes memory-mapped reads (XIP). Displays are write-only streams.
- The LUT model doesn't naturally fit "send command on 1 lane, then stream N KB of pixels on 4 lanes."
- Mainline `fsl-quadspi.c` (the MTD driver) doesn't expose a display path.
> **MTD:** Memory Technology Device, Linux's raw flash subsystem for eraseblock-based storage.

Two practical approaches on i.MX6ULL:

1. **Use the QSPI in `spi-mem` mode.** Recent kernels expose the QSPI controller via the `spi_mem` API, which `mipi_dbi` can drive for quad transfers. The mainline `spi-nxp-fspi.c` (for i.MX8) supports this. The older `fsl-quadspi.c` (i.MX6) has limited support. Check your kernel.
2. **Bit-bang or use a different SoC.** If the QSPI controller can't do display-style transfers, you're stuck with plain SPI on i.MX6ULL. QSPI displays are more at home on i.MX8M / RP2040 / ESP32-S3 which have flexible QSPI/PIO peripherals.

Honest assessment: the i.MX6ULL is *not* a great host for QSPI displays. Its QSPI is flash-centric. For a product needing a QSPI AMOLED, an i.MX8M Mini (with FlexSPI) or a dedicated display co-processor is a better fit. We still cover the topic. The displays are increasingly common, and you will likely meet them on a more capable SoC.

## 84.4  How mipi_dbi handles quad mode

Some SPI controllers expose `spi_mem` with quad support. On those SoCs, the `mipi_dbi` helper can issue quad transfers. The newer DRM tiny drivers (e.g., for the ST77903, SH8601 AMOLEDs) use `spi_mem_op` structures:

```c
/* Conceptual — quad pixel write via spi_mem */
struct spi_mem_op op = SPI_MEM_OP(
    SPI_MEM_OP_CMD(0x32, 1),                  /* command on 1 lane */
    SPI_MEM_OP_ADDR(3, (0x002C00), 1),         /* RAMWR address, 1 lane */
    SPI_MEM_OP_NO_DUMMY,
    SPI_MEM_OP_DATA_OUT(len, pixels, 4));      /* pixels on 4 lanes! */

spi_mem_exec_op(spimem, &op);
```

The `SPI_MEM_OP_DATA_OUT(len, buf, 4)`, the trailing `4` says "4-lane (quad) data phase." The controller spreads the bytes across IO0–IO3. This is the same `spi_mem_op` abstraction we saw in the QSPI flash chapter (Ch 64.6), repurposed for display data.

A from-scratch QSPI display driver on a supporting SoC would:

1. Acquire the `spi_mem` device.
2. Send the init sequence via single-lane `spi_mem_op`s.
3. Implement the `mipi_dbi` `fb_dirty` callback to send CASET/RASET (single-lane) then RAMWR pixels (quad-lane) via `spi_mem_exec_op`.

The structure mirrors Ch 83's `myst7789.c`, but the pixel-write path uses a quad `spi_mem_op` instead of a plain `spi_sync`. We do not reproduce the full driver. It is the Ch 83 driver with the data phase changed to quad. It only works on an SoC whose controller supports quad `spi_mem` writes, stock i.MX6ULL does not.

## 84.5  When QSPI display makes sense

| Scenario | Bus choice |
|----------|-----------|
| 240×240 static UI, occasional updates | plain SPI (Ch 83) |
| 360×360 round watch face, full-screen animation | QSPI (on a capable SoC) |
| Large UI, video | parallel RGB (Ch 82) or MIPI-DSI (not on i.MX6ULL) |
| i.MX6ULL specifically | plain SPI or parallel RGB, QSPI display support is weak |

For the i.MX6ULL reader: **prefer parallel RGB (Ch 82) for big/fast displays, plain SPI (Ch 83) for small ones.** QSPI displays are a "know it exists, use on a better SoC" topic.

## 84.6  Lab

1. **Bandwidth measurement.** On your plain-SPI ST7789 from Ch 83, measure full-frame update time. Compute the theoretical QSPI improvement (4×).
2. **Check QSPI spi_mem support.** On your i.MX6ULL kernel, look for whether the QSPI controller registers as a `spi_mem` controller capable of quad data-out. `dmesg | grep -i qspi` and inspect `drivers/spi/spi-fsl-qspi.c` capabilities.
3. **If on a capable SoC** (i.MX8M, etc.): wire a QSPI round display. Adapt the Ch 83 driver's data path to quad `spi_mem_op`. Measure the frame-rate improvement.
4. **Round-display geometry.** A round display still has a square framebuffer. The corners are simply not visible. Verify your UI accounts for the circular visible area (draw within the inscribed circle).
5. **Comparison writeup.** Document, for your specific board, whether QSPI display is feasible. If not, justify the fallback (plain SPI / parallel RGB).

## 84.7  Pitfalls

- **Assuming i.MX6ULL QSPI does displays well.** It doesn't, it's flash-centric. Verify `spi_mem` quad-out support before committing to a QSPI display on this SoC.
- **Quad-mode lane order.** The bit-to-lane mapping (which bits go on IO0 vs IO3) varies. A wrong mapping gives scrambled pixels. Match the controller's convention.
- **Command vs data lane count.** Commands usually go on 1 lane, pixels on 4. Sending the command on 4 lanes confuses the controller. The `spi_mem_op` cmd/data buswidth fields must be set per phase.
- **Pull-ups on IO2/IO3.** In single-lane mode, IO2/IO3 may double as /WP and /HOLD. For display use they're data. Ensure no conflicting pulls.
- **Frame tearing at high fps.** Without vsync/TE-pin synchronization, fast full-frame updates tear. Many QSPI AMOLEDs have a TE (tearing-effect) output. Wire it to a GPIO IRQ and sync updates.
> **MCU bridge:** Think of an IRQ like an EXTI/NVIC interrupt path, except Linux splits the hard interrupt from deferred work and must share lines across drivers.
> **MCU bridge:** Think of Linux GPIO like the same pin set/reset block you used on STM32, but accessed through a kernel subsystem that owns numbering, direction, interrupts, and user-space exposure.
> **IRQ:** interrupt request, the signal path that tells the CPU or interrupt controller that hardware needs service.
> **GPIO:** General-Purpose Input/Output, a pin controlled as a digital input, output, or interrupt source.
- **Power: AMOLED inrush.** QSPI AMOLEDs can draw significant current when displaying bright white. Budget the rail accordingly.
- **Init sequence length.** AMOLED init sequences are long (50–100 commands) with vendor-specific gamma/voltage. Get the exact sequence from the module vendor.

## 84.8  Going deeper

- **`drivers/gpu/drm/tiny/`**: newer entries (st7571, sh8601-style) show quad approaches on capable SoCs.
- **`drivers/spi/spi-mem.c`**: the `spi_mem_op` abstraction shared between flash and these displays.
- **`drivers/spi/spi-nxp-fspi.c`**: i.MX8 FlexSPI driver with quad support (contrast with i.MX6's `fsl-quadspi.c`).
- **`Documentation/spi/spi-summary.rst`**: SPI/QSPI overview.
- **ST77916 / SH8601 datasheets**: QSPI display command framing.
- **i.MX6ULL Reference Manual, QuadSPI chapter**: the LUT model and its constraints.

---

> **Note on Group H so far:** parallel RGB (Ch 82) for big/fast on i.MX6ULL, plain SPI (Ch 83) for small/cheap, QSPI (Ch 84) for high-bandwidth-on-capable-SoCs. The next two chapters cover the *non-raster* display technologies: OLED character/graphic displays + e-paper (Ch 85), and the touch input that turns a display into an interface (Ch 86).

> Next chapter: **Chapter 85: OLED & e-paper (SSD1306 / SH1106 / SSD1680).** Tiny monochrome OLEDs and the radically different e-paper refresh model.
