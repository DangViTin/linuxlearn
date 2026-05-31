---
chapter: 111
title: Quadrature encoders & rotary
part: VII — Device cookbook
estimated_pages: 12
status: draft
---

# Chapter 111 — Quadrature encoders & rotary

> **What:** **quadrature incremental encoders** (optical or magnetic — two phase-shifted square waves), **mechanical rotary encoders** (knob-style, low-res), and **absolute magnetic encoders** (AS5048A from Ch 74, here used as a position sensor not a sensor-out). Three implementations on the i.MX6ULL: (a) software quadrature decode via two GPIO IRQs (works ≤ ~10 kHz pulse rate), (b) hardware quadrature via the i.MX **XBAR + ENC** peripheral (works up to ~1 MHz pulse rate but needs the optional ENC IP block), (c) `rotary_encoder` kernel driver for low-rate user-interface knobs. Plus the IIO `angl` channel pattern for absolute encoders.
> **Why:** every closed-loop motor needs position feedback; every UI knob needs decoding. The i.MX6ULL has a strong NXP-BSP-only ENC peripheral that mainline Linux doesn't fully expose — so on a mainline kernel, you either do software decode (cheap, slow), use the partial mainline driver if it exists for your variant, or bridge to an external decoder IC. Understanding the four implementation tiers (software IRQ, hardware decoder, dedicated chip, sysfs `rotary_encoder` driver) lets you pick correctly for your use case.
> **Focus:** **quadrature decoding is "two channels 90° out of phase; the leading channel tells direction"**. A is high then B goes high = forward; B high then A high = backward. Four edges per full A+B cycle = 4× resolution multiplication. Mechanical encoders bounce horribly (5+ ms of noise per click) and need debouncing; optical encoders are clean but expensive; magnetic encoders are the middle ground.

## 111.1  Encoder types

| | Mechanical (knob) | Optical incremental | Magnetic incremental | Magnetic absolute |
|---|---|---|---|---|
| Resolution | 12–24 ppr | 100–10,000 ppr | 64–4096 ppr | 12–14 bits / rev |
| Max RPM | hand-spinning | 10,000+ | 30,000+ | 60,000+ |
| Index pulse | sometimes | yes | optional | n/a (absolute) |
| Bouncing | severe | none | none | none |
| Cost | $0.50 (Bourns PEC11) | $20–200 | $5–50 | $5 (AS5600) to $25 (AS5048A) |
| Use case | UI knob | CNC, servo | hobby/industrial servo | absolute position (joint angle) |

## 111.2  Quadrature signal — the math

```
A:  ───┐   ┌───┐   ┌───┐   ┌───┐    →  rotating forward
       │   │   │   │   │   │   │
       └───┘   └───┘   └───┘   └───
B:  ─┐   ┌───┐   ┌───┐   ┌───┐
     │   │   │   │   │   │   │
     └───┘   └───┘   └───┘   └────

   On A's rising edge:  if B==0 then count++   else count--
   On A's falling edge: if B==1 then count++   else count--
   On B's rising edge:  if A==1 then count++   else count--
   On B's falling edge: if A==0 then count++   else count--
```

That's 4× decoding (every edge of either channel = one count). The encoder spec ("100 PPR") refers to 100 pulses per revolution of just one channel; 4× decoded → 400 counts/rev.

State-machine view (current AB state + previous AB state):

| Prev | Curr | Direction |
|---|---|---|
| 00 | 01 | +1 |
| 01 | 11 | +1 |
| 11 | 10 | +1 |
| 10 | 00 | +1 |
| 00 | 10 | −1 |
| 10 | 11 | −1 |
| 11 | 01 | −1 |
| 01 | 00 | −1 |
| ?? | same | 0 |
| 00 | 11, 01→10, etc. | INVALID (missed an edge) |

Software-decode in C:

```c
static volatile int32_t count = 0;
static uint8_t prev_ab = 0;
static const int8_t QDEC_TABLE[16] = {
    /* prev:curr  00 01 10 11 */
    /* prev 00 */  0, +1, -1,  0,
    /* prev 01 */ -1,  0,  0, +1,
    /* prev 10 */ +1,  0,  0, -1,
    /* prev 11 */  0, -1, +1,  0,
};

static void encoder_irq_handler(void) {
    uint8_t a = gpio_read(GPIO_A);
    uint8_t b = gpio_read(GPIO_B);
    uint8_t curr_ab = (a << 1) | b;
    count += QDEC_TABLE[(prev_ab << 2) | curr_ab];
    prev_ab = curr_ab;
}
```

Both channels' rising + falling edges call this; it handles all 12 valid transitions and silently zeros the 4 invalid (missed-edge) transitions.

## 111.3  Software decode in user-space (libgpiod)

For low-rate encoders (≤10 kHz pulses, which covers most UI and slow-servo uses):

```c
/* code/ch111-encoder/qdec_userspace.c */
#include <gpiod.h>
#include <stdio.h>
#include <poll.h>

int main(void) {
    struct gpiod_chip *chip = gpiod_chip_open("/dev/gpiochip0");
    struct gpiod_line *a = gpiod_chip_get_line(chip, 20);
    struct gpiod_line *b = gpiod_chip_get_line(chip, 21);

    struct gpiod_line_request_config cfg = {
        .consumer = "qdec",
        .request_type = GPIOD_LINE_REQUEST_EVENT_BOTH_EDGES,
        .flags = 0,
    };
    gpiod_line_request(a, &cfg, 0);
    gpiod_line_request(b, &cfg, 0);

    struct pollfd pfd[2] = {
        { .fd = gpiod_line_event_get_fd(a), .events = POLLIN },
        { .fd = gpiod_line_event_get_fd(b), .events = POLLIN },
    };
    int32_t count = 0;
    uint8_t prev = (gpiod_line_get_value(a) << 1) | gpiod_line_get_value(b);

    static const int8_t TBL[16] = {
        0,+1,-1, 0, -1, 0, 0,+1, +1, 0, 0,-1, 0,-1,+1, 0
    };

    for (;;) {
        poll(pfd, 2, -1);
        struct gpiod_line_event ev;
        if (pfd[0].revents) gpiod_line_event_read(a, &ev);
        if (pfd[1].revents) gpiod_line_event_read(b, &ev);
        uint8_t curr = (gpiod_line_get_value(a) << 1) | gpiod_line_get_value(b);
        count += TBL[(prev << 2) | curr];
        prev = curr;
        printf("\rcount=%d   ", count);
        fflush(stdout);
    }
}
```

The `gpiod_line_event_get_fd` lets you poll multiple GPIO lines via standard `poll()`. Latency per edge: ~50–500 µs on a non-RT i.MX6ULL — fine for hand-spun knobs, fails for a 10,000 ppr encoder spinning at 60 RPM (= 40 kHz edge rate, exceeds Linux's interrupt budget).

For higher rates: kernel driver, hardware decoder, or external decoder chip.

## 111.4  Kernel `rotary_encoder` driver — for UI knobs

For UI-style mechanical encoders (10–30 detents per turn), the kernel provides `drivers/input/misc/rotary_encoder.c` — wires two GPIOs and exposes the knob as a Linux input device.

DT:

```dts
rotary@0 {
    compatible = "rotary-encoder";
    pinctrl-names = "default";
    pinctrl-0 = <&pinctrl_rotary>;
    gpios = <&gpio4 20 GPIO_ACTIVE_LOW>,        /* A */
            <&gpio4 21 GPIO_ACTIVE_LOW>;        /* B */
    linux,axis = <REL_X>;                       /* report as REL_X relative event */
    rotary-encoder,steps-per-period = <4>;      /* 4 for full-quadrature */
    rotary-encoder,encoding = "gray";            /* or "binary" */
    rotary-encoder,relative-axis;
};
```

A new `/dev/input/eventN` appears. Use `evtest /dev/input/event3`:

```
Event: time 1709236745.123, type 2 (EV_REL), code 0 (REL_X), value 1
Event: time 1709236745.234, type 2 (EV_REL), code 0 (REL_X), value 1
Event: time 1709236745.345, type 2 (EV_REL), code 0 (REL_X), value -1
```

This is the right pattern for a volume knob, menu scroll, jog wheel. Bouncing? The driver does some debouncing internally; for very bouncy mechanical encoders, add an RC filter on the GPIO inputs.

## 111.5  i.MX hardware quadrature — the ENC peripheral (and its mainline state)

The i.MX6ULL **eXtended Quadrature Encoder (ENC)** module — 32-bit counter, hardware-accelerated direction detection, index-pulse support, count up to ~10 MHz edge rate. Documented in NXP's reference manual ch. 33-ish.

Status in mainline Linux:
- **NXP BSP kernels**: full support via `drivers/staging/iio/quadrature_encoder.c` or vendor patches.
- **Mainline**: partial; some i.MX variants (i.MX7, i.MX8) have IIO-exposed encoder counters; i.MX6ULL coverage varies by kernel version. Check `find /sys/bus/iio/devices/ -iname '*encoder*'` after enabling `CONFIG_IIO_ST_LSM6DSX` or relevant config.

If your kernel has it, exposing via DT:

```dts
&qei1 {
    pinctrl-0 = <&pinctrl_qei1>;
    status = "okay";
};
```

User-space reads the count via IIO:

```sh
cat /sys/bus/iio/devices/iio:device0/in_count0_raw
```

If your mainline doesn't include i.MX6ULL ENC, fall back to GPIO-IRQ software decode (≤10 kHz) or an external decoder chip (LS7366R via SPI for unlimited speed).

## 111.6  External SPI decoder — LSI/CSI LS7366R

For "I need a fast quadrature counter and my SoC doesn't have one":

```
   Encoder A,B,Z   →  LS7366R (32-bit counter, debouncer, SPI interface)
                      i.MX6ULL ← SPI ← LS7366R
```

LS7366R is a $5 chip; 4× decode in hardware; 32-bit counter; up to 40 MHz pulse rate. Driver: write your own ~200-line userspace SPI driver. Sequence: write MDR0 register (filter, decode mode), then `READ_CNTR` over SPI returns the current count.

No mainline driver, but SPI access is straightforward.

```c
uint8_t cmd = 0x88;      /* CLR | CNTR */
write(spi, &cmd, 1);     /* clear counter */
uint8_t read_cnt[5] = { 0x60, 0,0,0,0 };  /* READ_CNTR + 4 dummy */
uint8_t resp[5];
spi_transfer(read_cnt, resp, 5);
int32_t count = (resp[1] << 24) | (resp[2] << 16) | (resp[3] << 8) | resp[4];
```

For multi-axis: chain multiple LS7366Rs on the same SPI bus with separate CS.

## 111.7  Absolute encoders — AS5048A pattern

AS5048A (Ch 74) — magnetic absolute, 14-bit / revolution, SPI interface. Mainline IIO driver: `drivers/iio/position/ams5048.c` exposes `in_angl0_raw`:

```sh
cat /sys/bus/iio/devices/iio:device0/in_angl0_raw
# 8192       (out of 16384 = 180°)
cat /sys/bus/iio/devices/iio:device0/in_angl0_scale
# 0.000383   (radians per count: 2π / 16384)
```

For position control, absolute beats incremental every time — no homing, no missed-count drift, instant boot-up state. The trade: cost ($5 vs $0.50) and harder mounting (needs precisely-placed magnet on the shaft).

## 111.8  Closed-loop motor control — the velocity-feedback example

A 1024-ppr encoder on a brushed DC motor. Goal: maintain constant 1000 RPM regardless of load.

```c
/* Velocity loop running at 100 Hz (every 10 ms) */
int32_t prev_count = 0;
double target_rpm = 1000.0;
double Kp = 0.5, Ki = 0.1;
double integral = 0;

for (;;) {
    int32_t count = read_encoder();
    int32_t delta = count - prev_count;
    prev_count = count;

    /* delta counts in 10 ms × 60/(0.01*1024) = RPM */
    double rpm = delta * 60.0 / (0.01 * 1024);
    double err = target_rpm - rpm;
    integral += err * 0.01;
    double pwm = Kp * err + Ki * integral;
    if (pwm > 100) pwm = 100;
    if (pwm < 0)   pwm = 0;
    set_pwm_duty(pwm);

    usleep(10000);
}
```

100 Hz loop is plenty for a brushed motor (much slower mechanical dynamics). PWM drives the H-bridge from Ch 112.

## 111.9  Lab

1. **Knob → terminal.** Wire a Bourns PEC11 mechanical encoder (5-pin: A, B, common, switch, common). Use `rotary_encoder` DT binding; `evtest` to see relative events.
2. **Software qdec.** Wire an optical incremental (LPD3806-100BM-G5-24C-100ppr, $20). Run the user-space qdec; spin the encoder by hand; verify count tracks. Spin fast; note where counts start dropping (~10 kHz on i.MX6ULL).
3. **LS7366R external.** Wire LS7366R between encoder and i.MX SPI. Read the 32-bit count via SPI. Spin the encoder at 5,000 RPM (use a drill); verify no missed counts.
4. **Index pulse / homing.** Add Z (index) input. On every revolution, the Z pulse should fire; verify your count is a multiple of `4 × PPR`. Use Z to home an axis on startup.
5. **AS5048A absolute.** Wire AS5048A; verify IIO `in_angl0_raw` tracks shaft rotation. Verify boot-up reads the correct angle without homing.
6. **Velocity closed loop.** Combine the velocity loop with the DC motor driver from Ch 112 (BTS7960). Tune Kp, Ki for stable 1000 RPM.
7. **Position closed loop.** Same loop, but track a target angle. Test for steady-state error; add an integrator if needed.
8. **Direction-detection robustness.** Spin the encoder back-and-forth rapidly; verify the count is consistent and direction is right. Software bug? Look at the QDEC_TABLE.

Commit code + a CSV of count-vs-RPM measurements to `code/ch111-encoder/`.

## 111.10  Pitfalls

- **GPIO interrupt latency too high.** At 40 kHz edges, the IRQ handler takes 5–20 µs on a Cortex-A7. Above that, edges are lost. Use a hardware decoder.
- **No pull-ups on encoder inputs.** Open-collector outputs from optical encoders need external 4.7 kΩ pull-ups. Without, signals float and you see ghost counts.
- **No debouncing on mechanical encoder.** 5 ms of bounce per detent → 100s of false counts per click. Use RC filter or the kernel driver's debounce.
- **Reversed A/B.** Direction is wrong. Swap two wires in software or DT.
- **Index pulse double-trigger.** Z is often longer than one count's worth of time; trigger on its rising edge only, or you'll home twice per revolution.
- **Encoder loses counts on power loss.** Incremental encoders need re-homing after every boot. Use absolute encoders (AS5048A) or a homing routine.
- **Software qdec scheduled but missed under load.** A user-space loop on a busy Linux box loses edges when the scheduler holds it. RT priority (`chrt -f 99`) or move to a kernel module.
- **AS5048A magnet alignment.** The magnet must be on the shaft axis (radially polarized, diametric) within ±0.5 mm; misalignment → non-linear angle errors of several degrees.
- **Index of LS7366R registers wrong.** MDR0 vs MDR1; common mistake. Default values don't enable filters → noisy signals cause false counts.

## 111.11  Going deeper

- **`Documentation/devicetree/bindings/input/rotary-encoder.txt`** — kernel rotary encoder binding.
- **`drivers/input/misc/rotary_encoder.c`** — readable source.
- **NXP IMX6ULL Reference Manual, ch. 33 (ENC)** — full peripheral docs.
- **LS7366R datasheet** — 12-page chip; SPI register tour.
- **AMS AS5048A datasheet** — absolute encoder.
- **Bourns PEC11 series** — the classic UI knob.
- **`libgpiod`** — for user-space GPIO event-based code.
- **Ch 74** — magnetic position sensors (same AS5048A chip).
- **Ch 112** — pairs with this for closed-loop motor control.

---

> Next chapter: **Chapter 112 — Stepper & DC motor drivers** — DRV8825, TMC2209, BTS7960, BLDC FOC.
