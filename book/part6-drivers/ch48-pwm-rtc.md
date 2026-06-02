---
chapter: 48
title: PWM and RTC subsystems
part: VI — Driver development
estimated_pages: 16
status: draft
---

# Chapter 48 — PWM and RTC subsystems

> **What:** two short, unrelated subsystems combined here — each is small enough on its own, and the patterns reinforce each other. **PWM** — the `pwm_*` API and the `pwm-backlight` / `pwm-fan` / `pwm-beeper` consumers. **RTC** — the `rtc_class` framework, sysfs `/sys/class/rtc/`, the `hwclock` user-space tool, and how an external RTC chip plugs into Linux's wall-clock time.
>
> **Why:** *backlight dimming, fan speed, audible beeper, servo control* all use PWM — and every product that doesn't have continuous network access needs an RTC to keep time across reboots. These are subsystems you'll touch on almost every embedded project; knowing the consumer-side API saves you from re-inventing it.
>
> **Focus:** **consumer vs provider model**. PWM and RTC both expose two APIs: one for the *producer* (chip driver that owns the PWM controller or RTC silicon) and one for the *consumer* (driver/code that wants a PWM signal or a wall-clock read). You almost always write *consumers*. The SoC vendor wrote the producers. Knowing which side you're on tells you which API to look up.

---

## 48.1  PWM subsystem

### 48.1.1  Architecture

```
   ┌──────────────────────────────────────────────────────┐
   │   PWM consumers                                       │
   │   pwm-backlight, pwm-fan, pwm-beeper, your driver     │
   └──────────────────────────────────────────────────────┘
                              │ pwm_apply_state, pwm_enable, pwm_disable
                              ▼
   ┌──────────────────────────────────────────────────────┐
   │   PWM core (pwm_get / pwm_put / state machine)        │
   └──────────────────────────────────────────────────────┘
                              │ ops->apply
                              ▼
   ┌──────────────────────────────────────────────────────┐
   │   PWM provider (pwm-imx, pwm-cros-ec, pca9685, ...)   │
   └──────────────────────────────────────────────────────┘
                              │
                              ▼ MMIO / I²C / SPI
                           hardware
```

The provider talks to the hardware; the consumer asks for a `period` and `duty_cycle`. The core mediates and enforces invariants (e.g., duty ≤ period, period ≤ chip max).

i.MX6ULL has 8 PWM channels (PWM1–PWM8). The mainline `pwm-imx27` driver covers them.

### 48.1.2  DT representation

In the SoC DT:

```dts
&pwm1 {
    pinctrl-names = "default";
    pinctrl-0 = <&pinctrl_pwm1>;
    status = "okay";
};
```

Consumer side — e.g., a backlight on PWM1:

```dts
backlight: backlight {
    compatible = "pwm-backlight";
    pwms = <&pwm1 0 5000000 0>;
    /*       ^   ^   ^         ^
             │   │   │         flags (0 = normal polarity)
             │   │   period in ns (5 ms = 200 Hz)
             │   channel 0 of this PWM controller
             phandle to pwm1
     */
    brightness-levels = <0 4 8 16 32 64 128 255>;
    default-brightness-level = <5>;
    power-supply = <&reg_lcd_3v3>;
};
```

The `pwms` property is the binding. It's analogous to `gpios` — references the controller phandle, channel number within the controller, the period in nanoseconds, and flags. The consumer ("pwm-backlight") looks it up with `devm_pwm_get(&pdev->dev, NULL)`.

### 48.1.3  Consumer API

`#include <linux/pwm.h>`

```c
struct pwm_device *pwm = devm_pwm_get(&pdev->dev, NULL);
if (IS_ERR(pwm))
    return PTR_ERR(pwm);

struct pwm_state state = {
    .period = 5000000,           /* 5 ms = 200 Hz */
    .duty_cycle = 2500000,       /* 50 % */
    .polarity = PWM_POLARITY_NORMAL,
    .enabled = true,
};
err = pwm_apply_state(pwm, &state);
```

That's the whole API for static use. For dynamic adjustment:

```c
/* Adjust brightness; period stays fixed */
pwm_get_state(pwm, &state);
state.duty_cycle = (state.period * percent) / 100;
pwm_apply_state(pwm, &state);
```

Convenience helpers for the most common case:

```c
pwm_config(pwm, duty_ns, period_ns);    /* set duty + period */
pwm_enable(pwm);
pwm_disable(pwm);
```

`pwm_config` / `pwm_enable` are wrappers over `pwm_apply_state`. New code prefers the explicit state struct; legacy code uses the simpler form.

### 48.1.4  Built-in consumer drivers

You almost never need to write a custom PWM consumer. Use the in-tree generics:

| Driver | Binding | Use case |
|--------|---------|----------|
| `pwm-backlight` | `compatible = "pwm-backlight"` | LCD backlight |
| `pwm-fan` | `compatible = "pwm-fan"` | Cooling fan |
| `pwm-beeper` | `compatible = "pwm-beeper"` | Active or passive beeper |
| `pwm-vibrator` | `compatible = "pwm-vibrator"` | Haptic motor |
| `pwm-leds` | `compatible = "pwm-leds"` | LED brightness via PWM |
| `pwm-ir-tx` | `compatible = "pwm-ir-tx"` | IR transmitter |

Pick the one that matches and configure via DT. The generic drivers expose user-space interfaces (e.g., `/sys/class/backlight/`, `/sys/class/leds/`).

### 48.1.5  /sys/class/pwm — sysfs access

For prototyping, export PWMs to user-space:

```
[root@pa-mini:~]# ls /sys/class/pwm/
pwmchip0  pwmchip1  pwmchip2  pwmchip3  pwmchip4  pwmchip5  pwmchip6  pwmchip7

[root@pa-mini:~]# cd /sys/class/pwm/pwmchip0
[root@pa-mini:~]# echo 0 > export       ← claim channel 0
[root@pa-mini:~]# cd pwm0
[root@pa-mini:~]# echo 1000000 > period
[root@pa-mini:~]# echo 500000  > duty_cycle    ← 50 %
[root@pa-mini:~]# echo 1 > enable
```

A 1 kHz, 50 % duty PWM is now on the corresponding pin. Useful for quick bring-up; production drivers should use the consumer API.

---

## 48.2  RTC subsystem

### 48.2.1  Two RTCs to know about

Most boards have *two* sources of timekeeping:

1. **The SoC's internal RTC.** On i.MX6ULL this is the **SNVS_LP** block — a low-power domain with its own RTC, optionally backed by a coin-cell battery on the `VBAT` pin. The mainline driver is `rtc-snvs`. The internal RTC is "free" — no extra BOM — but has the SoC's main XTAL accuracy (~50 ppm uncompensated).
2. **An external RTC chip.** DS3231 (TCXO, ±2 ppm), PCF8563, MCP79410, etc. Better accuracy, battery-backed, talks I²C or SPI. Mainline drivers in `drivers/rtc/`.

Boards often have one, sometimes both. The kernel uses **the first registered RTC as `/dev/rtc0`** and exposes the rest as `rtc1`, `rtc2`, etc. The Real-Time Clock that *systemd* / *busybox-init* read is `/dev/rtc0` by default — choose carefully.

### 48.2.2  DT for an external RTC

DS3231 on I²C:

```dts
&i2c1 {
    rtc@68 {
        compatible = "maxim,ds3231", "dallas,ds1307";
        reg = <0x68>;
        interrupt-parent = <&gpio1>;
        interrupts = <22 IRQ_TYPE_EDGE_FALLING>;
        wakeup-source;
    };
};
```

The `wakeup-source` flag lets the RTC's alarm wake the SoC from suspend (Ch 51B).

Once probed, `/dev/rtc1` (or whichever number) appears, and `/sys/class/rtc/rtcN/` exposes attributes.

### 48.2.3  rtc_class consumer API

For *most* drivers, you don't talk to the RTC directly. User-space's `hwclock` reads `/dev/rtcN`. The kernel's time-of-day comes from the RTC at boot (`hctosys`).

If you do need to read or set time from a kernel driver:

```c
#include <linux/rtc.h>

struct rtc_device *rtc = rtc_class_open("rtc0");
if (!rtc) return -ENODEV;

struct rtc_time tm;
err = rtc_read_time(rtc, &tm);     /* tm is in UTC */
pr_info("now: %d-%02d-%02d %02d:%02d:%02d\n",
        tm.tm_year + 1900, tm.tm_mon + 1, tm.tm_mday,
        tm.tm_hour, tm.tm_min, tm.tm_sec);

rtc_class_close(rtc);
```

For alarms (e.g., wake at a specific time):

```c
struct rtc_wkalrm alm = {
    .enabled = 1,
    .time = future_tm,
};
rtc_set_alarm(rtc, &alm);
```

The kernel coordinates with PM to use the RTC alarm as the wakeup source.

### 48.2.4  RTC provider (driver) — quick sketch

If you ever do need to write an RTC driver (e.g., for a chip without a mainline driver), the shape is:

```c
static int my_rtc_read_time(struct device *dev, struct rtc_time *tm) { ... }
static int my_rtc_set_time(struct device *dev, struct rtc_time *tm) { ... }
static int my_rtc_alarm_irq_enable(struct device *dev, unsigned int enabled) { ... }

static const struct rtc_class_ops my_rtc_ops = {
    .read_time   = my_rtc_read_time,
    .set_time    = my_rtc_set_time,
    .alarm_irq_enable = my_rtc_alarm_irq_enable,
    /* ... read_alarm, set_alarm, etc */
};

/* In probe: */
struct rtc_device *rtc = devm_rtc_allocate_device(&pdev->dev);
if (IS_ERR(rtc))
    return PTR_ERR(rtc);
rtc->ops = &my_rtc_ops;
rtc->range_min = RTC_TIMESTAMP_BEGIN_2000;
rtc->range_max = RTC_TIMESTAMP_END_2099;
err = devm_rtc_register_device(rtc);
```

The core handles `/dev/rtcN` and `/sys/class/rtc/` for you.

### 48.2.5  User-space — hwclock and timedatectl

```
# Read RTC into system time at boot (standard init scripts do this automatically)
[root@pa-mini:~]# hwclock -s

# Set RTC from system time
[root@pa-mini:~]# date -s "2026-05-26 14:30:00"
[root@pa-mini:~]# hwclock -w

# Read RTC directly
[root@pa-mini:~]# hwclock
2026-05-26 14:30:42.123456+00:00

# systemd-aware tooling
[root@pa-mini:~]# timedatectl
                Local time: Tue 2026-05-26 14:30:42 UTC
            Universal time: Tue 2026-05-26 14:30:42 UTC
                  RTC time: Tue 2026-05-26 14:30:42
                 Time zone: Etc/UTC
 System clock synchronized: yes
               NTP service: active
```

For a fleet product, run `chrony` or `systemd-timesyncd` to sync system time to NTP. Then write the RTC periodically — via systemd's `systemd-time-sync-target`, or an init `-11` hook.

### 48.2.6  Alarms for wake-from-suspend

Combine the RTC with PM (Ch 51B) to wake the system at a specific time:

```sh
# Wake the system 60 seconds from now
$ echo $(($(date +%s) + 60)) > /sys/class/rtc/rtc0/wakealarm
$ echo mem > /sys/power/state         ← suspend
# … 60 seconds later, system resumes ...
```

This is the foundation of low-power data-logger products: sleep deeply, wake on RTC, sample sensors, log, sleep again.

---

## 48.3  Lab

1. **Backlight via pwm-backlight.** Configure DT to use `pwm-backlight` for your LCD. Verify `/sys/class/backlight/backlight/brightness` controls it.
2. **Beeper.** Configure `pwm-beeper` on PWM2 (or unused PWM); send tones via `/sys/class/input/eventN`.
3. **Direct PWM via sysfs.** Generate a 1 kHz 25% duty signal on PWM3; scope it.
4. **Add DS3231 to your board** (or use the internal SNVS RTC if no external). Verify `hwclock` reads sensibly, `date -s` + `hwclock -w` persists across reboots.
5. **Wake from suspend.** Set a 30-second alarm via `wakealarm`, suspend, watch the system come back up.
6. **Compare RTC accuracy.** Run `chronyd` for an hour, check `/sys/class/rtc/rtc0/since_epoch` against `date +%s` — drift should be under 100 ms for DS3231, under a second for raw SoC RTC.

## 48.4  Pitfalls

- **PWM period too short.** The provider's hardware has a max-period and a frequency resolution. Asking for 1 ns period or 1 Hz frequency may snap to the nearest achievable value silently. Always read back the actual state with `pwm_get_state`.
- **Polarity inversion forgotten.** Some backlights are active-low (full brightness = 0% duty). Use `PWM_POLARITY_INVERTED` in `pwm_state` or `pwms = <..., PWM_POLARITY_INVERTED>` in DT.
- **PWM stops when consumer driver unloads.** `pwm_put` (or `devm_*` cleanup) disables the PWM. If you want the signal to keep running after unload, that's a design choice you must explicitly handle.
- **Multiple consumers fighting over one PWM.** Only one consumer per PWM. Verify with `/sys/class/pwm/pwmchipN/pwmN/`.
- **RTC time-zone confusion.** RTC by convention stores UTC; some legacy systems store local time. `timedatectl set-local-rtc 0` to enforce UTC.
- **No backup battery on SNVS_LP.** SoC's internal RTC loses time on power-loss without `VBAT`. Symptom: every reboot starts in 1970. Wire up a CR2032. If you cannot, accept the limit and sync via NTP at boot.
- **Multiple RTCs, hctosys reads the wrong one.** `CONFIG_RTC_HCTOSYS_DEVICE="rtc0"` (default) picks the first registered. If you have both SoC RTC (registers first) and DS3231 (registers later, more accurate), you get the wrong one. Either rename via udev or change kernel config.
- **DS3231 alarm-mask register quirk.** The alarm fires for the first match across multiple fields; misconfiguring the mask gives a once-per-second wake instead of once-per-day. Read the datasheet carefully.

## 48.5  Going deeper

- **`Documentation/pwm.rst`** — the PWM subsystem documentation.
- **`Documentation/admin-guide/rtc.rst`** — RTC subsystem and `hwclock`.
- **`drivers/pwm/pwm-imx27.c`** — i.MX PWM driver. Small and clean.
- **`drivers/rtc/rtc-snvs.c`** — i.MX SNVS RTC driver.
- **`drivers/rtc/rtc-ds1307.c`** — handles DS1307, DS1338, DS1340, DS3231, DS3232, MCP7940x — one driver for the whole family. A good reference for handling chip-family variants.
- **`Documentation/devicetree/bindings/pwm/`** and **`/rtc/`** — DT bindings.

> Next chapter: **Chapter 49 — IIO subsystem.** ADCs, DACs, light/temp/pressure/IMU sensors — they all live in IIO, the "Industrial I/O" subsystem. Once you internalise IIO, every sensor in Part VII's cookbook becomes "DT + driver registers channels + user-space reads /sys/bus/iio/devices/."
