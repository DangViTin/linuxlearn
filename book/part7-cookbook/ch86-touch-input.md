---
chapter: 86
title: Touch input ICs (TTP223 / MPR121 / XPT2046)
part: VII — Device cookbook
estimated_pages: 20
status: draft
---

# Chapter 86 — Touch input ICs

> **What:** three touch technologies at increasing complexity. **TTP223** (single capacitive button, GPIO output — `gpio-keys`), **MPR121** (12-channel capacitive, I²C, with IRQ), **XPT2046/ADS7846** (4-wire resistive touchscreen controller, SPI, ADC-based, needs calibration). For each: physics, protocol, the input subsystem integration, and a from-scratch XPT2046 input driver — the most interesting, since resistive touch requires reading X/Y ADC channels and software calibration.
> **Why:** a display without touch is a monitor; with touch it's an interface. Capacitive buttons replace mechanical ones (no wear, sealed enclosures). Capacitive matrices give you piano keys, sliders, proximity. Resistive touch is the cheap way to make any LCD interactive (works with gloves and stylus, unlike capacitive). Each is a different input-subsystem pattern — this chapter completes the input picture started in Ch 45 and the multi-touch GT911 of Ch 55G.
> **Focus:** **capacitive = threshold detection, resistive = ADC + calibration**. A cap button outputs a clean digital "touched"; you wire it to `gpio-keys` and you're done. Resistive touch gives you two ADC readings (X, Y position) that map non-linearly to screen pixels — calibration (the `tslib` / `xinput_calibrator` step) turns raw ADC counts into pixel coordinates.

## 86.1  Technology comparison

| | TTP223 | MPR121 | XPT2046 (ADS7846 clone) |
|---|---|---|---|
| Tech | single cap button | 12-channel cap | 4-wire resistive |
| Output | GPIO (digital touch/no-touch) | I²C (per-channel + IRQ) | SPI (X/Y/Z ADC values) |
| Touch type | finger only | finger only | finger, gloved, stylus, anything |
| Multi-touch | no | per-channel (12 buttons) | no (single point) |
| Position | none (button) | none (discrete buttons) | continuous X/Y |
| Needs calibration | no | threshold tuning | yes (per-panel) |
| Sealed enclosure | yes (touch through glass) | yes | no (touch surface exposed) |
| Volume price | $0.10–0.30 | $1–2 | $1–2 |
| Mainline driver | `gpio-keys` | `mpr121_touchkey.c` | `ads7846.c` |

**Pick guide:**
- **TTP223**: a single touch button — power, mode, wake. Cheapest possible touch input.
- **MPR121**: capacitive keypad, slider, or proximity — 12 electrodes.
- **XPT2046**: make any resistive-overlay LCD touch-interactive. Works with gloves/stylus; needs calibration.

For *capacitive multi-touch* (a modern phone-style glass touchscreen), see Ch 55G (GT911).

## 86.2  TTP223 — capacitive button via gpio-keys

The TTP223 is a self-contained capacitive touch sensor: a copper pad (on your PCB or a separate electrode) connects to its input; its output pin goes high (or toggles, configurable) when touched. From Linux's view it's just a GPIO that changes state.

No driver needed — use the in-tree **`gpio-keys`** (Ch 45):

```dts
gpio_keys {
    compatible = "gpio-keys";

    touch_power {
        label = "PowerTouch";
        linux,code = <KEY_POWER>;
        gpios = <&gpio4 14 GPIO_ACTIVE_HIGH>;
        debounce-interval = <50>;
    };

    touch_menu {
        label = "MenuTouch";
        linux,code = <KEY_MENU>;
        gpios = <&gpio4 15 GPIO_ACTIVE_HIGH>;
    };
};
```

Each TTP223's output → a GPIO → a `gpio-keys` button. Touching the pad generates a `KEY_POWER` / `KEY_MENU` input event. `evtest /dev/input/eventN` shows them. Done — zero driver code.

The TTP223 has configuration pads (TOG, AHLB) you bridge to set: momentary vs toggle output, active-high vs active-low, fast vs low-power mode. These are *hardware* straps, not software — set them on the PCB.

## 86.3  MPR121 — 12-channel capacitive

The MPR121 measures capacitance on 12 electrodes. Each electrode's capacitance rises when a finger approaches (the finger adds capacitance to ground). The chip tracks a per-electrode baseline and reports "touched" when capacitance exceeds a threshold.

Register map highlights:

| Reg | Name | Purpose |
|-----|------|---------|
| 0x00–0x01 | Touch Status | 12 bits, one per electrode (1 = touched) |
| 0x04–0x1D | Electrode filtered data | per-electrode capacitance reading |
| 0x1E–0x2A | Baseline values | per-electrode baseline |
| 0x41–0x5A | Touch/Release thresholds | per-electrode |
| 0x5B–0x7F | Configuration | filter, debounce, auto-config |
| 0x80 | Soft reset | write 0x63 |

The IRQ pin asserts when the touch status changes. Bring-up:

1. Soft reset (write 0x63 to 0x80).
2. Configure per-electrode touch/release thresholds (typical: touch 12, release 6 — hysteresis).
3. Configure filtering + auto-configuration.
4. Write Electrode Configuration (0x5E) to enable N electrodes + start.
5. On IRQ, read touch status (0x00–0x01); 12 bits tell you which electrodes are touched.

### Mainline driver + input

`drivers/input/keyboard/mpr121_touchkey.c` registers each electrode as a key. DT:

```dts
&i2c1 {
    mpr121@5a {
        compatible = "freescale,mpr121-touchkey";
        reg = <0x5a>;
        interrupt-parent = <&gpio4>;
        interrupts = <14 IRQ_TYPE_EDGE_FALLING>;
        autorepeat;
        linux,keycodes = <KEY_0 KEY_1 KEY_2 KEY_3 KEY_4 KEY_5
                          KEY_6 KEY_7 KEY_8 KEY_9 KEY_A KEY_B>;
        vdd-supply = <&reg_3v3>;
    };
};
```

12 electrodes → 12 key codes. Touching electrode 0 emits `KEY_0`, etc. The driver reads the touch-status register on each IRQ and reports key-down/up events. `evtest` shows them.

For a slider or proximity (analog), you'd read the filtered-data registers directly (the mainline keytouch driver only does discrete keys; a custom IIO or input driver could expose the analog capacitance).

## 86.4  XPT2046 — 4-wire resistive touch

Resistive touch is two transparent resistive layers separated by spacer dots. Pressing pushes the layers together at the touch point. To find the position:

```
   Measure X: drive a voltage gradient across the X layer (left=0V, right=3.3V);
              read the voltage at the touch point on the Y layer (an ADC reading
              proportional to the X position).
   Measure Y: drive a voltage gradient across the Y layer (top/bottom);
              read on the X layer.
   Measure Z (pressure): drive one axis, measure resistance — tells you if/how
              hard it's pressed.
```

The XPT2046 is an SPI-controlled 12-bit ADC + analog mux that automates this. You send a control byte selecting which measurement (X, Y, Z1, Z2); it drives the right layers and returns the ADC value.

### Protocol

Each measurement is a 3-byte SPI transaction:

```
   byte 0: control byte:
       bit 7:   start (1)
       bits 6:4: channel select (A2 A1 A0)
                 101 = X position
                 001 = Y position
                 011 = Z1, 100 = Z2 (pressure)
       bit 3:   mode (0 = 12-bit, 1 = 8-bit)
       bit 2:   SER/DFR (0 = differential — better noise rejection)
       bits 1:0: power-down mode
   bytes 1-2: read the 12-bit result (in the upper 12 of 16 bits)
```

Reading X position:

```
   tx = { 0xD0, 0x00, 0x00 };    /* 0xD0 = start + X channel + 12-bit + differential */
   rx = spi_transfer(tx, 3);
   x = ((rx[1] << 8) | rx[2]) >> 3;   /* 12-bit result, right-justified */
```

A touch IRQ (the PENIRQ pin) asserts when the panel is pressed — wire it to a GPIO IRQ to avoid polling.

## 86.5  Writing an XPT2046 input driver from scratch

Goal: an `input_dev` reporting `ABS_X` / `ABS_Y` / `ABS_PRESSURE` + `BTN_TOUCH`, driven by the PENIRQ. ~250 lines.

`myxpt2046.c`:

```c
#include <linux/init.h>
#include <linux/module.h>
#include <linux/spi/spi.h>
#include <linux/input.h>
#include <linux/interrupt.h>
#include <linux/gpio/consumer.h>
#include <linux/delay.h>

#define CMD_X   0xD0    /* start + X + 12-bit + differential */
#define CMD_Y   0x90    /* start + Y */
#define CMD_Z1  0xB0
#define CMD_Z2  0xC0

#define MAX_ADC 4095

struct myxpt {
    struct spi_device *spi;
    struct input_dev *input;
    int irq;
    struct gpio_desc *pen_gpio;     /* PENIRQ line, also readable */
};

static int xp_read_channel(struct myxpt *x, u8 cmd)
{
    u8 tx[3] = { cmd, 0x00, 0x00 };
    u8 rx[3];
    struct spi_transfer xfer = { .tx_buf = tx, .rx_buf = rx, .len = 3 };
    int err = spi_sync_transfer(x->spi, &xfer, 1);
    if (err) return err;
    return ((rx[1] << 8) | rx[2]) >> 3;     /* 12-bit, right-justified */
}

/* Read X/Y a few times and median-filter for noise rejection */
static int xp_read_filtered(struct myxpt *x, u8 cmd)
{
    int samples[5], i, j, tmp;
    for (i = 0; i < 5; i++)
        samples[i] = xp_read_channel(x, cmd);
    /* tiny bubble sort */
    for (i = 0; i < 4; i++)
        for (j = 0; j < 4 - i; j++)
            if (samples[j] > samples[j+1]) {
                tmp = samples[j]; samples[j] = samples[j+1]; samples[j+1] = tmp;
            }
    return samples[2];      /* median */
}

static irqreturn_t xp_irq_thread(int irq, void *dev_id)
{
    struct myxpt *x = dev_id;

    /* While the pen is down (PENIRQ low), sample continuously */
    while (gpiod_get_value(x->pen_gpio) == 0) {   /* active-low PENIRQ */
        int rx = xp_read_filtered(x, CMD_X);
        int ry = xp_read_filtered(x, CMD_Y);
        int z1 = xp_read_channel(x, CMD_Z1);

        /* Crude pressure check: ignore ghost touches with z1 too low */
        if (z1 > 100) {
            input_report_abs(x->input, ABS_X, rx);
            input_report_abs(x->input, ABS_Y, ry);
            input_report_abs(x->input, ABS_PRESSURE, z1);
            input_report_key(x->input, BTN_TOUCH, 1);
            input_sync(x->input);
        }
        msleep(10);     /* ~100 Hz sampling while touched */
    }

    /* Pen up */
    input_report_key(x->input, BTN_TOUCH, 0);
    input_report_abs(x->input, ABS_PRESSURE, 0);
    input_sync(x->input);

    return IRQ_HANDLED;
}

static int xp_probe(struct spi_device *spi)
{
    struct myxpt *x;
    int err;

    x = devm_kzalloc(&spi->dev, sizeof(*x), GFP_KERNEL);
    if (!x) return -ENOMEM;
    x->spi = spi;

    spi->mode = SPI_MODE_0;
    spi->bits_per_word = 8;
    err = spi_setup(spi);
    if (err) return err;

    x->pen_gpio = devm_gpiod_get(&spi->dev, "pendown", GPIOD_IN);
    if (IS_ERR(x->pen_gpio))
        return dev_err_probe(&spi->dev, PTR_ERR(x->pen_gpio), "no pendown gpio\n");

    x->input = devm_input_allocate_device(&spi->dev);
    if (!x->input) return -ENOMEM;

    x->input->name = "myxpt2046";
    x->input->phys = "myxpt2046/input0";
    x->input->id.bustype = BUS_SPI;

    /* Report ABS_X / ABS_Y in raw 12-bit ADC range; calibration done in user-space */
    input_set_abs_params(x->input, ABS_X, 0, MAX_ADC, 0, 0);
    input_set_abs_params(x->input, ABS_Y, 0, MAX_ADC, 0, 0);
    input_set_abs_params(x->input, ABS_PRESSURE, 0, MAX_ADC, 0, 0);
    input_set_capability(x->input, EV_KEY, BTN_TOUCH);

    err = input_register_device(x->input);
    if (err) return err;

    x->irq = gpiod_to_irq(x->pen_gpio);
    err = devm_request_threaded_irq(&spi->dev, x->irq, NULL, xp_irq_thread,
                                    IRQF_TRIGGER_FALLING | IRQF_ONESHOT,
                                    "myxpt2046", x);
    if (err) return err;

    spi_set_drvdata(spi, x);
    return 0;
}

static const struct of_device_id xp_of_match[] = {
    { .compatible = "linuxlearn,myxpt2046" },
    { }
};
MODULE_DEVICE_TABLE(of, xp_of_match);

static const struct spi_device_id xp_id[] = { { "myxpt2046", 0 }, { } };
MODULE_DEVICE_TABLE(spi, xp_id);

static struct spi_driver xp_driver = {
    .driver = {
        .name = "myxpt2046",
        .of_match_table = xp_of_match,
    },
    .probe = xp_probe,
    .id_table = xp_id,
};
module_spi_driver(xp_driver);

MODULE_LICENSE("GPL");
```

DT:

```dts
&ecspi3 {
    touch@0 {
        compatible = "linuxlearn,myxpt2046";
        reg = <0>;
        spi-max-frequency = <2000000>;
        pendown-gpios = <&gpio4 14 GPIO_ACTIVE_LOW>;
        interrupt-parent = <&gpio4>;
        interrupts = <14 IRQ_TYPE_EDGE_FALLING>;
    };
};
```

Test:

```
[root@pa-mini:~]# insmod myxpt2046.ko
[root@pa-mini:~]# evtest /dev/input/event2
Supported events:
  EV_KEY: BTN_TOUCH
  EV_ABS: ABS_X (0-4095), ABS_Y (0-4095), ABS_PRESSURE

# Touch the panel:
Event: type 3 (EV_ABS), code 0 (ABS_X), value 1834
Event: type 3 (EV_ABS), code 1 (ABS_Y), value 2201
Event: type 1 (EV_KEY), code 330 (BTN_TOUCH), value 1
Event: ---------- SYN_REPORT ----------
```

It reports **raw ADC coordinates** (0–4095), not screen pixels. The mapping from ADC to pixels is the calibration step.

What we got, ~250 lines:
- PENIRQ-driven sampling (no polling when idle).
- Median-filtered X/Y for noise rejection.
- Pressure-gated to reject ghost touches.
- Standard `input_dev` with ABS axes.

What we skipped vs mainline `ads7846.c`:
- Hardware debounce settling-time tuning.
- The `ti,x-plate-ohms` pressure-to-resistance conversion.
- Runtime configuration of sample count, settle delay.
- Proper PENIRQ vs sample interleaving (the mainline driver disables PENIRQ during sampling to avoid spurious IRQs).

## 86.6  Calibration — raw ADC to screen pixels

The XPT2046 gives raw ADC values. They don't map 1:1 to pixels:
- The touch panel's edges don't align with the LCD's edges (mechanical offset).
- The ADC range isn't the full panel (the resistive gradient has dead zones).
- X/Y may be swapped or inverted relative to the display.

Calibration computes a **3×2 affine transform** (`tslib`'s model):

```
   pixel_x = a·adc_x + b·adc_y + c
   pixel_y = d·adc_x + e·adc_y + f
```

You collect 5 calibration points (corners + center), solve for (a..f) by least-squares. The standard tools:

- **`tslib`** (`ts_calibrate`): writes a calibration file `/etc/pointercal`; apps use `tslib` to transform raw events.
- **`xinput_calibrator`** (X11): generates an Xorg config snippet.
- The kernel's **`touchscreen` properties** in DT (`touchscreen-size-x`, `touchscreen-inverted-x`, etc.) handle simple cases (swap/invert/scale) but not the full affine.

For our driver to integrate with `tslib`:

```sh
[root@pa-mini:~]# export TSLIB_TSDEVICE=/dev/input/event2
[root@pa-mini:~]# ts_calibrate            # touch the 5 crosshairs
[root@pa-mini:~]# ts_test                 # verify the transform
```

After calibration, `/etc/pointercal` holds the transform; `tslib`-linked apps (or the `evdev`+`libinput` path with a calibration matrix) report pixel coordinates.

For a cleaner kernel-side approach, the mainline `ads7846` driver + the `touchscreen` DT properties + `libinput`'s calibration matrix handle it without `tslib`.

## 86.7  Lab

1. **TTP223 button.** Wire one to a GPIO; use `gpio-keys` with `KEY_POWER`. `evtest` shows the key on touch.
2. **MPR121 keypad.** Wire to I²C; use mainline `mpr121_touchkey`. Configure 12 keycodes. Touch each electrode; verify distinct keys in `evtest`.
3. **XPT2046 raw.** Build and load `myxpt2046.ko`. `evtest` shows raw ABS_X/Y (0–4095). Touch corners; note the raw values.
4. **Calibrate.** Run `ts_calibrate` (tslib). Touch the crosshairs. Verify `ts_test` shows the cursor tracking your finger correctly.
5. **Full UI.** Pair the XPT2046 (Ch 86) with the parallel LCD (Ch 82). Run a Qt/LVGL app with touch; verify taps land where expected.
6. **Pressure.** Read ABS_PRESSURE; verify harder presses give higher values. Use it to reject light/ghost touches.
7. **Compare to GT911.** If you have a capacitive panel (Ch 55G), compare the experience: cap is smoother and multi-touch; resistive works with gloves but is single-point and needs calibration.

## 86.8  Pitfalls

- **TTP223 strap config.** Momentary vs toggle, active-high vs low — set by PCB straps (TOG, AHLB pads), not software. Get them right at layout.
- **MPR121 thresholds too sensitive.** Default thresholds may trigger on proximity, not touch. Tune touch/release thresholds with hysteresis (touch > release).
- **XPT2046 PENIRQ during sampling.** Sampling toggles the panel layers, which can spuriously trigger PENIRQ. The mainline driver masks PENIRQ during sampling. Our simple driver polls the GPIO instead — works but less clean.
- **Resistive touch needs calibration, always.** Raw ADC ≠ pixels. Ship `ts_calibrate` or a kernel-side calibration matrix. Uncalibrated touch is unusable.
- **X/Y swapped or inverted.** Depends on panel mounting. Fix via calibration or DT `touchscreen-swapped-x-y` / `touchscreen-inverted-x`.
- **Noisy resistive readings.** Median-filter (we do 5 samples). Single-sample touch jitters badly.
- **Ghost touches at light pressure.** Gate on pressure (Z) — reject touches below a Z threshold.
- **SPI clock too fast for XPT2046.** Max ~2 MHz for reliable conversion. Faster gives noisy ADC values.
- **MPR121 needs the IRQ.** Polling the touch-status register works but is laggy. Wire the IRQ.

## 86.9  Going deeper

- **`drivers/input/touchscreen/ads7846.c`** — the production XPT2046/ADS7846 driver. Compare to the from-scratch version; note the PENIRQ masking.
- **`drivers/input/keyboard/mpr121_touchkey.c`** — MPR121 driver.
- **`drivers/input/keyboard/gpio_keys.c`** — for TTP223-style buttons.
- **`Documentation/devicetree/bindings/input/touchscreen/touchscreen.yaml`** — the common touchscreen properties (swap/invert/scale).
- **`tslib`** at <https://github.com/libts/tslib> — calibration + filtering library.
- **XPT2046 / ADS7846 datasheets** — control-byte format, differential vs single-ended.
- **MPR121 datasheet (NXP/Freescale)** — register map, auto-config.
- **`libinput` calibration matrix docs** — the modern alternative to tslib.

---

> **End of Group H — Displays (Ch 82–86).** The full display spectrum: parallel RGB (big/fast), SPI (small/smart), QSPI (high-bandwidth), OLED (tiny/crisp), e-paper (zero-power/slow), plus the touch input (capacitive button/matrix, resistive) that makes them interactive.

> Next chapter: **Chapter 87 — Parallel CSI cameras (OV5640 / OV7725 / GC2145).** Group I (Cameras) — the i.MX6ULL's parallel camera interface, the V4L2 sensor sub-device model, and bringing up a real camera sensor.
