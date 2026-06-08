---
chapter: 113
title: WS2812 / SK6812 / APA102 addressable LEDs
part: VII — Device cookbook
estimated_pages: 14
status: draft
---

# Chapter 113 — WS2812 / SK6812 / APA102 addressable LEDs

> **What:** the **addressable RGB LED strip** — daisy-chained programmable pixels where each pixel is RGB (WS2812) or RGBW (SK6812) or has independent global brightness (APA102). We cover the timing-critical 800 kHz one-wire protocol of WS2812 + SK6812, why bit-banging from Linux fails without PREEMPT_RT, the three production-quality implementations on the i.MX6ULL — (1) **SPI + DMA encoding** (the workhorse), (2) **PWM + DMA** (alternative for boards with spare PWM), (3) **bit-bang under PREEMPT_RT** (only viable for short strips). Then APA102's clean SPI native protocol that sidesteps all the timing pain.
> **MCU bridge:** Think of DMA like the MCU DMA controller you used for UART or SPI, but with cache coherency, scatter-gather descriptors, and kernel ownership rules added.
> **MCU bridge:** Think of Linux PWM like an MCU timer output channel, except the driver exposes period, duty cycle, polarity, and enable state through a subsystem.
> **DMA** - Direct Memory Access. hardware moves data to or from memory without the CPU copying each byte.
> **PWM** - Pulse-Width Modulation, a timer output whose duty cycle controls average power or encodes timing.
> **PREEMPT_RT** - the Linux real-time patch set that makes more kernel paths preemptible and reduces latency.
>
> **Why:** every modern indicator strip, status display, mood-lighting product, holiday string light, LED ring around a Wi-Fi-enabled doorbell, automotive interior accent — all use these three families. Hundreds of pixels per meter, $0.05 per pixel at volume, the only daisy-chained interface that scales to 1000+ LEDs on a single data line. Yet driving them from Linux is "interesting" — the WS2812 wire protocol uses 350 ns and 800 ns pulses. Linux IRQ jitter is microseconds. Understanding the SPI + DMA trick lets you drive any-length strip at 30+ fps with < 5 % CPU.
> **IRQ** - interrupt request, the signal path that tells the CPU or interrupt controller that hardware needs service.
>
> **Focus:** WS2812 and SK6812 encode bits as pulse widths on a single wire. A "0" bit is 350 ns high followed by 800 ns low. A "1" bit is 800 ns high followed by 450 ns low. A reset is 50 µs or more of low. Each LED takes 24 bits (3 channels × 8) — or 32 bits for RGBW — and the whole strip is one back-to-back stream. Bit-banging from Linux user-space does not work. The IRQ jitter is microseconds. The WS2812 timing budget is hundreds of nanoseconds. The trick: each WS2812 "bit" becomes 4 SPI bits at 3.2 MHz. a "0" is encoded as `1000`, a "1" as `1110`. The SPI bitstream becomes the WS2812 waveform after DMA pushes it out hands-off. APA102 is the escape hatch — separate clock + data lines, no timing constraints.
>
> **Tooling.** This chapter uses `libgpiod` (`gpioset`) for hello-world. The SPI-DMA path uses raw `/dev/spidev`. optional `python3-spidev`.
> - **Ubuntu-base (target):** `apt install gpiod libgpiod-dev python3-spidev`
> - **Buildroot:** `BR2_PACKAGE_LIBGPIOD=y BR2_PACKAGE_PYTHON3_SPIDEV=y`
> **Buildroot** - a configuration-driven build system that produces a complete root filesystem and related images.
> - Full per-tool reference: [Userspace tooling appendix](../part5-rootfs/appendix-tooling.md).
> **MCU bridge:** Think of the rootfs as the firmware image's file-backed runtime environment. On an MCU you link everything into flash. On Linux, programs and config live in this mounted tree.
> **rootfs** - root filesystem, the directory tree mounted at / that contains /bin, /etc, /dev, and libraries.


## 113.1  Chip comparison

| | WS2812B | SK6812 (RGBW) | APA102 | WS2811 |
|---|---|---|---|---|
| Channels per pixel | RGB (3 × 8 bit) | RGBW (4 × 8 bit) | RGB + 5-bit global brightness | RGB (off-strip controller) |
| Protocol | one-wire, 800 kHz | one-wire, 800 kHz | SPI (clock + data) | one-wire, 800 kHz |
| Refresh rate (100 LEDs) | 30 fps max | 30 fps max | 4500 fps max | 30 fps |
| Strip current (white max) | 60 mA/LED | 60 mA/LED | 60 mA/LED | 60 mA/LED |
| Timing tolerance | ±150 ns | ±150 ns | clock-recovered (any) | ±150 ns |
| Cost (per LED, bulk) | $0.05 | $0.08 | $0.15 | $0.06 |
| Power | 5 V | 5 V | 5 V | 12 V (controller) + 12 V LEDs |
| Reset gap | 50 µs (some need 250 µs) | 50 µs | n/a | 50 µs |

**Pick guide:**
- **WS2812B** — workhorse for any non-time-critical visual. Cheap, ubiquitous.
- **SK6812 RGBW** — when you need warm white (not RGB-mixed). The dedicated white LED is much truer than RGB-mixed white.
- **APA102** — when you need ultra-high refresh (POV displays, audio-reactive bars at kHz update). also when you want to drive from a "dumb" 3.3 V SPI without level shifting tricks. More expensive.

## 113.2  WS2812 timing in detail

The datasheet specifies (per the chip, not the strip):

| Bit | Description | T_HIGH | T_LOW |
|---|---|---|---|
| 0 | "0" code | 0.4 µs ±150 ns | 0.85 µs ±150 ns |
| 1 | "1" code | 0.8 µs ±150 ns | 0.45 µs ±150 ns |
| Reset | latch | 0 | ≥50 µs |

Each LED captures 24 bits of data (or 32 for RGBW), then forwards the rest down the chain. Data order: GRB (not RGB) — the green byte first.

A 100-LED strip = 2400 bits × 1.25 µs/bit = 3 ms transfer + 50 µs reset → max ~328 fps theoretical, but the data line settling and chip latch reduce this. 30 fps is comfortable for most apps.

## 113.3  The SPI + DMA pattern — the standard approach in embedded Linux

Encode each WS2812 bit as 4 SPI bits at 3.2 MHz (312.5 ns per SPI bit):
- WS2812 "0" = SPI `1000` → 312.5 ns high + 937.5 ns low ≈ within spec
- WS2812 "1" = SPI `1110` → 937.5 ns high + 312.5 ns low ≈ within spec

So each WS2812 byte (8 bits) becomes 4 SPI bytes (32 bits). For 100 LEDs × 3 bytes = 300 WS2812 bytes → 1200 SPI bytes. At 3.2 MHz SPI = 3 ms transfer. DMA pushes it autonomously. CPU does the encoding once per frame and starts the SPI transfer.

```c
/* Encode one WS2812 byte (8 bits) into 4 SPI bytes (32 bits). */
static void encode_byte(uint8_t in, uint8_t out[4]) {
    static const uint8_t bit_lut[4] = { 0x88, 0x8E, 0xE8, 0xEE };
    out[0] = bit_lut[(in >> 6) & 3];
    out[1] = bit_lut[(in >> 4) & 3];
    out[2] = bit_lut[(in >> 2) & 3];
    out[3] = bit_lut[(in >> 0) & 3];
}
```

This encodes 2 WS2812 bits at a time → 1 SPI byte. Each WS2812 bit is 4 SPI bits. two WS2812 bits = 8 SPI bits = 1 SPI byte. The LUT pre-computes all 4 combinations:
- `00` → `1000 1000` → 0x88
- `01` → `1000 1110` → 0x8E
- `10` → `1110 1000` → 0xE8
- `11` → `1110 1110` → 0xEE

Full encoder for a 100-LED strip:

```c
#define N_LEDS 100
uint8_t pixels[N_LEDS][3];          /* G, R, B */
uint8_t spi_buf[N_LEDS * 3 * 4];    /* 4× expansion */

static void encode_strip(void) {
    for (int i = 0; i < N_LEDS; i++) {
        encode_byte(pixels[i][0], &spi_buf[i*12 + 0]);   /* G */
        encode_byte(pixels[i][1], &spi_buf[i*12 + 4]);   /* R */
        encode_byte(pixels[i][2], &spi_buf[i*12 + 8]);   /* B */
    }
}

static void send_strip(int spi_fd) {
    encode_strip();
    struct spi_ioc_transfer t = {
        .tx_buf = (unsigned long)spi_buf,
        .len = sizeof spi_buf,
        .speed_hz = 3200000,
    };
    ioctl(spi_fd, SPI_IOC_MESSAGE(1), &t);
    /* The trailing low time of the last bit is naturally followed by SPI idle
       (line stays low after CS rises), giving the >50 µs reset for free. */
}
```

Wire MOSI to the strip's DIN. Always add a 74AHCT125 buffer to convert 3.3 V MOSI to 5 V. The WS2812 datasheet specifies VIH = 0.7 × VDD = 3.5 V. 3.3 V is below that. Some strip batches accept it. many do not. Buffer every time.

Now you have 30+ fps RGB animations on a strip with ~3 % CPU. Add animation logic (rainbow shift, fade, audio-reactive) on top.

## 113.4  Alternative — PWM + DMA encoding

Some i.MX6ULL board designs free SPI for other devices. Use PWM with DMA:

```
PWM period = 1.25 µs (800 kHz)
DMA writes new duty-cycle on every PWM cycle:
  "0" bit → duty = 32 % (T_HIGH = 0.4 µs)
  "1" bit → duty = 64 % (T_HIGH = 0.8 µs)
```

Linux PWM doesn't expose dynamic per-cycle duty changes via sysfs. This needs a kernel-side DMA-fed PWM driver. The mainline `pwm-imx27.c` doesn't support this. vendor BSPs sometimes do. Effort/reward: lower than SPI approach for most uses. SPI wins.
**sysfs** - a kernel-generated filesystem under /sys that exposes devices, drivers, and attributes.

## 113.5  PREEMPT_RT bit-bang — for short strips only

With PREEMPT_RT (Ch 52A), a high-priority RT thread can busy-loop on `clock_gettime(CLOCK_MONOTONIC)` and toggle a GPIO with ~150 ns jitter. Just barely within WS2812 spec.
> **MCU bridge:** Think of Linux GPIO like the same pin set/reset block you used on STM32, but accessed through a kernel subsystem that owns numbering, direction, interrupts, and user-space exposure.
**GPIO** - General-Purpose Input/Output, a pin controlled as a digital input, output, or interrupt source.

```c
struct sched_param sp = { .sched_priority = 90 };
sched_setscheduler(0, SCHED_FIFO, &sp);
mlockall(MCL_CURRENT | MCL_FUTURE);

/* Pin to one CPU */
cpu_set_t mask; CPU_ZERO(&mask); CPU_SET(0, &mask);
sched_setaffinity(0, sizeof mask, &mask);

for (int led = 0; led < N_LEDS; led++) {
    for (int bit = 23; bit >= 0; bit--) {
        if (pixel[led] & (1 << bit)) {
            gpio_high(); busy_wait_ns(800);
            gpio_low();  busy_wait_ns(450);
        } else {
            gpio_high(); busy_wait_ns(400);
            gpio_low();  busy_wait_ns(850);
        }
    }
}
```

`busy_wait_ns` is a tight `clock_gettime` loop. Works for 10–30 LEDs reliably. fails above ~50 (a single interrupt or migration jitter corrupts a bit, all subsequent LEDs latch the wrong data).

Do not ship this approach. It is useful as a demo only. Production designs should use SPI + DMA.

## 113.6  APA102 — the timing-painless alternative

APA102 has two wires: CLOCK + DATA, normal SPI. No timing constraints (any clock rate. APA102 syncs to your clock). Wire to SPI. bit-bang or use the kernel SPI driver — all work.

Protocol per frame:
```
   Start frame:  32 bits of zero
   For each LED: 1 byte (111 + 5-bit global brightness 0..31), then BGR (24 bits)
   End frame:    32+ bits of ones (or zeros — both work)
```

Code:

```c
uint8_t buf[4 + 4*N_LEDS + 4];
memset(&buf[0], 0, 4);                                /* start */
for (int i = 0; i < N_LEDS; i++) {
    buf[4 + i*4 + 0] = 0xE0 | (brightness & 0x1F);   /* 5-bit brightness */
    buf[4 + i*4 + 1] = pixel[i].b;
    buf[4 + i*4 + 2] = pixel[i].g;
    buf[4 + i*4 + 3] = pixel[i].r;
}
memset(&buf[sizeof buf - 4], 0xFF, 4);                /* end */
spi_send(buf, sizeof buf);
```

That's it. No 4× encoding, no level-shift requirement (APA102 accepts 3.3 V logic directly), no reset-gap concern. The 5-bit global brightness is a separate PWM domain at ~700 Hz — useful for low-light, but it flickers in camera footage (frame-rate beating against the 700 Hz). For studio use, disable global PWM (set brightness 0x1F, control color via the 8-bit channels).

## 113.7  Color and gamma

Naïvely lerping RGB doesn't look right. The eye perceives brightness logarithmically. a "50 % bright red" set to `(128, 0, 0)` looks far too bright. Apply gamma 2.2:

```c
static const uint8_t GAMMA8[256] = { /* precomputed table */ };
uint8_t corrected = GAMMA8[raw];
```

Generate the table:
```python
[int((i/255.0)**2.2 * 255 + 0.5) for i in range(256)]
```

For mood-lighting or status indicators, always apply gamma. For data visualization (e.g., "32 % CPU load"), maybe not.

For RGB→HSV color manipulation:
- Hue rotates around the rainbow.
- Saturation = how vivid.
- Value (brightness) = how bright.

Animations (rainbow shift, breathing) become 5-line `for` loops over HSV.

## 113.8  Power budgeting — the elephant in the room

> **Lab vs production:** Do not burn fuses, enroll production keys, or sign release images while following the lab.
> Use throwaway keys and back up the unsigned image plus the key directory before testing irreversible security flows.


Each LED at full white = 60 mA. 100 LEDs at full white = 6 A. A USB 5 V supply (1 A) can't even light 17 LEDs. Real numbers:

| Strip length | Max current at white | Required PSU |
|---|---|---|
| 30 | 1.8 A | 5 V × 2 A |
| 100 | 6 A | 5 V × 8 A |
| 300 | 18 A | 5 V × 20 A |
| 1000 | 60 A | 5 V × 70 A (specialty supply) |

For long strips:
- Inject power every 50–100 LEDs (extra 5 V + GND from a beefier supply).
- Voltage drop along the strip turns "white" at the end into "yellow" (red survives the drop, blue dies first).
- Use thick wire (14 AWG for 10+ A).
- Add a fuse — a shorted addressable strip can dump 20 A through a thin wire and start a fire.

For mood lighting, cap brightness at 64/255 (~25 %) — visually plenty, current draw 1/4. Software-enforced.

## 113.9  Lab

1. **WS2812 + SPI + DMA.** Build the encoder. wire SPI MOSI → 74AHCT125 → strip DIN. Make the first LED red, second green, third blue. Verify with phone camera (visible).
2. **Strip of 100.** Light all 100 with a rainbow gradient. Measure CPU usage during 30 fps animation — should be < 5 %.
3. **Frame rate test.** How fast can you push? Time `send_strip()`. For 100 LEDs it's ~4 ms → 250 fps theoretical, 30 fps practical (limited by reset gap + your animation logic).
4. **Power injection.** Strip of 200. inject 5 V at the middle. Confirm the end-of-strip white is no longer yellow.
5. **APA102 comparison.** Same lab but with APA102. Note: no buffer needed, no timing concerns. SPI clock can be 10 MHz+ → 1000+ fps possible. Measure.
6. **PREEMPT_RT bit-bang.** Build with PREEMPT_RT kernel. bit-bang 30 LEDs. Run under load (compile a kernel in parallel). verify no glitches. Try 100 LEDs. observe corruption.
7. **Audio-reactive.** Sample microphone (Ch 78). FFT. map low/mid/high bins to red/green/blue intensity. Drive the strip at 60 fps.
8. **Status indicator.** A 24-LED ring on top of an i.MX6ULL device acting as: blue = booting, green = healthy, yellow = warning, red = error. Tie to systemd state.
9. **Fade-to-color helper.** Implement smooth color transitions (HSV interpolation) for state changes.

## 113.10  Pitfalls

- **3.3 V → 5 V level shifting.** WS2812 datasheet says VIH = 0.7 × VDD = 3.5 V. A 3.3 V GPIO is *below* this. Most strips work anyway but some batches don't. Always use a 74AHCT125 buffer for reliability.
- **First LED bright random color on power-up.** Strip powers up before MCU sends data → LEDs latch garbage. Send a frame of all-zero immediately on boot.
- **Reset gap too short.** Some clone WS2812 chips need 250 µs reset, not 50 µs. If frames intermittently corrupt mid-strip, lengthen the reset.
- **Power injection without ground tie.** Inject +5 V but forget to tie the injected supply's GND to the strip's GND. Now the strip floats, signals to misbehave. Always tie all GNDs.
- **Voltage droop on long strips.** Red survives, blue dies. Inject power every 100 LEDs or shorten the strip.
- **DMA SPI buffer too large.** 1000-LED strip × 4× = 12 KB DMA buffer. some SPI drivers cap at 4 KB and silently truncate. Test full strip. verify all LEDs animated.
- **Wrong color order.** WS2812 is GRB (Green-Red-Blue), not RGB. WS2812B is GRB. SK6812 RGBW is GRBW. APA102 is BGR. Easy to swap. "red doesn't work" is the symptom.
- **Capacitor between V+ and GND missing.** Add 1000 µF + 100 nF at the strip's start. The inrush spike at "all-white" stresses your PSU and causes voltage droop.
- **Fuse missing.** A shorted strip dumps PSU's max current — start a fire. 10 A fuse for 5 m of WS2812 minimum.
- **Quality varies wildly between batches.** Cheap strips have miscalibrated chips. The same code looks subtly different (pinker reds, dim blues) on different strips. Production: buy from one reliable supplier and stick.
- **APA102 5-bit brightness PWM beats with camera frame rate.** For video shoots, max global brightness. control via 8-bit channels.

## 113.11  Going deeper

- **WS2812B datasheet** (~5 pages, full timing).
- **APA102 datasheet** — clean spec. no timing pain.
- **Adafruit NeoPixel uberguide** — bible of WS2812 power, wiring, troubleshooting.
- **Tim Bauwens' (xy_pi) Linux WS2812 driver patches** — for understanding kernel-side approaches.
- **FastLED library (Arduino)** — readable C++ for color manipulation, gamma, HSV.
- **`drivers/leds/leds-pca9685.c`** — for 16-channel PWM I²C alternatives.
- **rPi DMA-WS2812 implementations (`rpi_ws281x`)** — the canonical reference (different SoC but same principles).
- **Ch 78** (MEMS mic) for audio-reactive applications.
- **Ch 52A** (PREEMPT_RT) for short-strip bit-bang viability.

---

> Next chapter: **Chapter 114 — Beepers, relays, SSRs** — the everyday actuators.
