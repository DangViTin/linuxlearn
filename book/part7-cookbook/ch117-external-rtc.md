---
chapter: 117
title: External RTC (DS3231, PCF8563, MCP79410)
part: VII — Device cookbook
estimated_pages: 12
status: draft
---

# Chapter 117 — External RTC

> **What:** **external battery-backed real-time clocks**. **Maxim DS3231** (TCXO, ±2 ppm, the high-end favorite), **NXP PCF8563** (cheap, common, ±20 ppm), **Microchip MCP79410** (with built-in EEPROM, plus a unique ID). On the i.MX6ULL we wire I²C, walk the kernel `rtc-i2c` family of drivers (`rtc-ds1307` covers DS3231; `rtc-pcf8563` for PCF8563; `rtc-mcp7941x` for Microchip), use `hwclock` to sync between system clock and RTC, configure **alarm interrupts** for wake-from-suspend, and integrate with **Ch 51B's runtime PM** so the i.MX6ULL can sleep for hours and wake exactly on a scheduled RTC alarm.
> **Why:** the i.MX6ULL has an *internal* RTC in the SNVS (Secure Non-Volatile Storage) domain — it survives reboots but loses time without a backup battery on the VDD_SNVS rail. Many board designs skip the SNVS battery to save 50 cents → the SoC's RTC is useless. The external RTC fix: $0.50 chip + $0.30 coin cell on the I²C bus = the device knows the right time on every cold boot, runs scheduled alarms even when Linux is off, and stays calibrated across years. For products that schedule actions ("daily sensor upload at 06:00") or need accurate timestamps in logs across power outages, an external RTC isn't optional.
> **Focus:** **the RTC chip is a 32.768 kHz oscillator + counters + I²C; the kernel `rtc-*` driver exposes it as `/dev/rtcN`; `hwclock` syncs between hardware clock and system clock; chrony or systemd-timesyncd updates the system clock from NTP/PPS and writes back to the RTC**. Three clock domains coexist (hardware RTC, system clock, NTP source); their interactions are what's tricky. Alarm interrupts let the RTC wake the SoC from suspend — but the alarm pin must be wired to a real GPIO that's mappable to a wake-up source in the kernel, which is the most-skipped detail.

## 117.1  Chip comparison

| | DS3231 | PCF8563 | MCP79410 |
|---|---|---|---|
| Crystal | integrated TCXO | external 32.768 kHz | external 32.768 kHz |
| Accuracy | ±2 ppm (1 min/year) | ±20 ppm (10 min/year) | ±20 ppm |
| Temperature compensation | yes, internal | no | no |
| Battery life | 6–10 years on CR2032 | 6–10 years | 6–10 years |
| Alarm interrupts | 2 | 1 | 2 |
| EEPROM | no | no | 64 B EEPROM + 128 B SRAM |
| Unique ID | no | no | yes (6 bytes) |
| Power supply | 2.3–5.5 V | 1.8–5.5 V | 1.8–5.5 V |
| Cost | $1.50 (chip) / $2.50 (module with battery) | $0.30 | $0.80 |
| Kernel driver | `rtc-ds1307` (covers DS3231 too) | `rtc-pcf8563` | `rtc-mcp7941x` |

**Pick guide:**
- **DS3231** — accuracy matters (logs, scheduling, fleet sync); willing to pay $1.50.
- **PCF8563** — BOM critical; ±10 min/year drift acceptable; you have NTP to correct.
- **MCP79410** — when you also want a tiny EEPROM (board serial, calibration data) without adding a separate chip.

## 117.2  Wiring DS3231

```
       ┌───────────┐                              ┌──────────┐
i.MX  ─┤ SDA       ├──────────────────────────────┤ SDA      │
I²C1   │ SCL       ├──────────────────────────────┤ SCL      │  DS3231
GPIO  ─┤ INT       ├──────────────────────────────┤ /INT     │  (alarm pin, active-low)
       │           │   3.3 V ────────────────────  ┤ VCC      │
       │           │   GND ─────────────────────── ┤ GND      │
       │           │                  CR2032 (3 V) ┤ VBAT     │  ← coin cell
       └───────────┘                              └──────────┘
```

The INT pin is an open-drain output; pull-up to 3.3 V. Wire to a GPIO that maps to a wake source (the i.MX6ULL EXTRBOOT or ONOFF wake pins are ideal; otherwise any GPIO with `wake-up-source` capability).

## 117.3  Device tree

```dts
&i2c1 {
    pinctrl-names = "default";
    pinctrl-0 = <&pinctrl_i2c1>;
    clock-frequency = <100000>;
    status = "okay";

    rtc@68 {
        compatible = "maxim,ds3231";       /* uses rtc-ds1307 driver */
        reg = <0x68>;
        interrupt-parent = <&gpio4>;
        interrupts = <23 IRQ_TYPE_EDGE_FALLING>;
        interrupts-extended = <&gpio4 23 IRQ_TYPE_EDGE_FALLING>;
        wakeup-source;
    };
};
```

After boot:

```sh
dmesg | grep rtc
# rtc-ds1307 1-0068: registered as rtc0
# rtc-ds1307 1-0068: setting system clock to 2026-05-31 12:34:56 UTC (...)
```

`/dev/rtc0` (and `/dev/rtc` symlink) appears. The kernel automatically reads the RTC at boot, sets the system clock to it.

If the i.MX6ULL has its SNVS RTC enabled, you'll have *two* RTCs (`rtc0` = SNVS, `rtc1` = DS3231). Decide which is primary (DS3231 if your SNVS lacks battery). Override:

```sh
# Force hwclock to use the DS3231
hwclock --rtc=/dev/rtc1 --systohc
```

## 117.4  hwclock — system clock ↔ RTC sync

```sh
hwclock --show                    # read hw clock
# 2026-05-31 12:34:56.123456+00:00

hwclock --systohc                 # write system → hw
hwclock --hctosys                 # write hw → system

date -s "2026-05-31 15:00:00"
hwclock --systohc                 # save new time to RTC battery
```

At boot, systemd runs `hwclock --hctosys` automatically (or kernel does it via the rtc-* driver's `set_system_time_from_rtc` if `CONFIG_RTC_HCTOSYS=y`).

Time zone: hwclock can store the RTC in UTC or local time. UTC is the only sensible choice — `/etc/adjtime` records the policy.

## 117.5  Alarm interrupts — waking from suspend

DS3231 has two alarms; PCF8563 has one. Set an alarm:

```sh
# Wake in 30 seconds via rtcwake
rtcwake -m mem -s 30
# (system suspends; in 30 s, RTC alarm fires → SoC wakes via INT pin → kernel resumes)
```

`rtcwake` is the universal tool. Under the hood:
1. `ioctl(rtc_fd, RTC_WKALM_SET, &alarm)` to set the alarm time + enable.
2. `echo mem > /sys/power/state` to suspend.
3. RTC's INT pin pulled low at the alarm time.
4. INT pin wired to a wake-capable GPIO → ARM core wakes from WFI.
5. Kernel resumes; alarm is cleared.

From C:

```c
#include <linux/rtc.h>
#include <fcntl.h>
#include <sys/ioctl.h>

int fd = open("/dev/rtc0", O_RDWR);

struct rtc_wkalrm alarm = {0};
alarm.enabled = 1;
/* Set to current time + 5 minutes */
ioctl(fd, RTC_RD_TIME, &alarm.time);
alarm.time.tm_min += 5; if (alarm.time.tm_min >= 60) alarm.time.tm_min -= 60, alarm.time.tm_hour++;
ioctl(fd, RTC_WKALM_SET, &alarm);

/* Now suspend the system */
system("echo mem > /sys/power/state");
/* Execution resumes here after wake */
```

For a battery-powered sensor: sleep 10 minutes; wake; read sensors; transmit; sleep again. With DVFS + suspend-to-RAM + RTC alarm + power-managed peripherals, the i.MX6ULL idles at < 5 mA between samples.

## 117.6  How the rtc-ds1307 driver actually works

`drivers/rtc/rtc-ds1307.c` — covers DS1307, DS1337, DS1338, DS1339, DS3231, DS3232, ... — a family of register-compatible chips.

Key functions:

```c
static int ds3231_get_time(struct device *dev, struct rtc_time *t) {
    struct ds1307 *ds = dev_get_drvdata(dev);
    u8 regs[7];
    regmap_bulk_read(ds->regmap, 0x00, regs, 7);   /* read sec..year */
    t->tm_sec  = bcd2bin(regs[0] & 0x7F);
    t->tm_min  = bcd2bin(regs[1] & 0x7F);
    t->tm_hour = bcd2bin(regs[2] & 0x3F);          /* 24h mode */
    t->tm_wday = bcd2bin(regs[3] & 0x07) - 1;
    t->tm_mday = bcd2bin(regs[4] & 0x3F);
    t->tm_mon  = bcd2bin(regs[5] & 0x1F) - 1;
    t->tm_year = bcd2bin(regs[6]) + 100;           /* RTC stores year-2000 */
    return 0;
}
```

The RTC chips store time in **BCD** (Binary-Coded Decimal — each nibble is a decimal digit). The driver does the bcd↔bin conversion. The 7-byte read covers all date/time registers in one I²C transaction.

For the alarm:

```c
static int ds3231_set_alarm(struct device *dev, struct rtc_wkalrm *t) {
    /* Write alarm-time registers (similar BCD encoding) */
    /* Set ALARM_INTERRUPT_ENABLE bit */
    /* Clear OSCILLATOR_STOP_FLAG if set (otherwise alarm may miss) */
    return 0;
}

static irqreturn_t ds3231_irq(int irq, void *dev_id) {
    /* Read STATUS_REG; if alarm flag set, clear it + call rtc_update_irq */
    rtc_update_irq(rtc, 1, RTC_AF | RTC_IRQF);
    return IRQ_HANDLED;
}
```

`rtc_update_irq` notifies user-space (via select/poll on `/dev/rtcN`) that the alarm fired.

## 117.7  Time discipline — RTC + NTP + chrony together

Your system has three clock sources:
1. **External RTC** (hardware, battery-backed, ±2 to ±20 ppm)
2. **System clock** (software, derived from CPU timer or LPC timer)
3. **NTP / PPS** (network or GPS — Ch 107)

chrony's job: discipline the system clock from the best available source, and write back to the RTC.

```conf
# /etc/chrony/chrony.conf
pool 2.pool.ntp.org iburst                # NTP source

# RTC: use as backup when network unavailable
rtcfile /var/lib/chrony/chrony.rtc
rtcsync                                    # write system→RTC periodically

# If you have a GPS PPS (Ch 107)
refclock SHM 0 refid GPS poll 4 noselect
refclock PPS /dev/pps0 refid PPS lock GPS prefer trust
```

`rtcsync` makes chrony sync the system→RTC every 11 minutes. On reboot, the RTC has accurate time even if NTP isn't immediately available.

## 117.8  From scratch — minimal DS3231 reader in C

For when you want to debug RTC behavior without the kernel driver:

```c
/* code/ch117-rtc/ds3231_min.c */
#include <fcntl.h>
#include <linux/i2c-dev.h>
#include <stdio.h>
#include <sys/ioctl.h>
#include <unistd.h>

#define DS3231_ADDR 0x68

static int i2c_fd;

static uint8_t bcd2bin(uint8_t v) { return (v >> 4) * 10 + (v & 0x0F); }
static uint8_t bin2bcd(uint8_t v) { return ((v / 10) << 4) | (v % 10); }

int main(void) {
    i2c_fd = open("/dev/i2c-0", O_RDWR);
    ioctl(i2c_fd, I2C_SLAVE, DS3231_ADDR);

    /* Read 7-byte time block (sec, min, hour, dow, day, mon, year-2000) */
    uint8_t reg = 0;
    write(i2c_fd, &reg, 1);
    uint8_t buf[7];
    read(i2c_fd, buf, 7);

    int sec  = bcd2bin(buf[0] & 0x7F);
    int min  = bcd2bin(buf[1] & 0x7F);
    int hour = bcd2bin(buf[2] & 0x3F);
    int day  = bcd2bin(buf[4] & 0x3F);
    int mon  = bcd2bin(buf[5] & 0x1F);
    int year = bcd2bin(buf[6]) + 2000;
    printf("DS3231: %04d-%02d-%02d %02d:%02d:%02d\n",
           year, mon, day, hour, min, sec);

    /* Read temperature (DS3231 has a built-in temp sensor for TCXO compensation) */
    reg = 0x11;
    write(i2c_fd, &reg, 1);
    uint8_t t[2];
    read(i2c_fd, t, 2);
    int temp_int = (int8_t)t[0];
    int temp_frac = (t[1] >> 6) * 25;
    printf("Temp: %d.%02d °C\n", temp_int, temp_frac);

    return 0;
}
```

The DS3231's built-in thermometer is a neat freebie — drives the TCXO temperature compensation but is also a usable ±3 °C ambient sensor. Use it for "is the device too hot" alerts.

## 117.9  Lab

1. **RTC up.** Wire DS3231; verify in `dmesg` that the kernel finds it (`rtc-ds1307`). `hwclock --show` reads the time.
2. **Set + persist.** `date -s ...`; `hwclock --systohc`; pull power; reboot; `hwclock --show` — time persists.
3. **Battery hot-swap test.** Remove the CR2032 with power on; replace; verify time still correct. Then remove battery + power; replace battery; reapply power → time lost (RTC needs both — main and battery — to *never* lose power; battery only protects across short main outages).
4. **From scratch I²C.** Run `ds3231_min.c`; cross-check with `hwclock --show`.
5. **Alarm wake.** `rtcwake -m mem -s 60` — system suspends; wakes 60 s later. Measure power during the suspended interval (should be < 5 mA if other rails are PMIC-managed).
6. **Daily scheduled task.** Use a cron-like scheduler: at boot, set an RTC alarm for the next 06:00; suspend; wake at 06:00; run the task; sleep again. Total energy per day: ~30 s of active + 86,370 s of suspend → battery life × 100 vs always-on.
7. **chrony integration.** Configure chrony with NTP + RTC backup. Disconnect network; reboot; verify time is correct from RTC.
8. **Drift measurement.** Power up; sync to NTP; wait 7 days; compare RTC time vs NTP. DS3231 should be within ±5 s; PCF8563 within ±100 s.
9. **Multi-RTC.** If your board has both SNVS RTC and DS3231, configure DS3231 as primary in `/etc/adjtime`; verify `hwclock --show` reads from DS3231.
10. **Temperature monitor.** Read DS3231's internal temp register every 10 s; log to a CSV; plot a day's worth — see room temperature variation.

Commit code + chrony config + a daily-schedule script to `code/ch117-rtc/`.

## 117.10  Pitfalls

- **No backup battery.** Battery socket present but empty. Time resets on every power-cycle. Always populate the battery (or use a supercap with charging circuit).
- **Battery dead, no monitoring.** CR2032 lasts 6–10 years but does die. After 8 years, the RTC silently loses time on next outage. Monitor the OSF (Oscillator Stop Flag) bit; alert when set.
- **VBAT < VCC on power-up.** Some RTCs (DS3231) need VCC ≥ VBAT before they start counting. If VCC ramps slowly, RTC may not start. Add a power-good supervisor or check OSF after every boot.
- **OSF not cleared.** DS3231 latches OSF after VBAT loss; if you don't clear it, the alarm interrupts are inhibited. Clear in CONTROL_STATUS register at boot.
- **I²C bus pull-up missing or too weak.** DS3231 expects 4.7 kΩ to 10 kΩ pull-ups; weaker = slow edges = errors at 400 kHz.
- **Multiple chips at 0x68.** MPU-6050 IMU also defaults to 0x68. Bus conflict. Reroute one to a different address (DS3231 doesn't reconfigure; MPU-6050 has AD0 strap).
- **BCD vs binary confusion.** Direct register reads return BCD; treating as binary gives nonsense (0x13 read as 19 instead of 13). Convert with bcd2bin.
- **Year-2100 problem.** Some RTCs store year as 0..99; the "century" bit handles 2000–2099 only. Post-2100 these RTCs roll over to 2000.
- **INT pin not wake-capable.** GPIO wired but not configurable as a wake source → suspend works but never wakes. Verify with `dmesg | grep wakeup`.
- **Alarm time wrong fields.** DS3231 alarm requires specific masks (DY/DT bit for day-of-week vs day-of-month). Wrong mask = alarm fires constantly or never.
- **MCP79410 EEPROM at separate I²C address.** Same chip, but the EEPROM section is at 0x57, not 0x6F (the RTC's address). Easy to miss.
- **Temperature sensor not used for TCXO comp without proper init.** DS3231 has automatic TCXO compensation but require Convert Temp bit to be set periodically (or run once and rely on automatic 64-second updates).

## 117.11  Going deeper

- **Maxim DS3231 Datasheet** — TCXO theory, alarm registers, OSF semantics.
- **NXP PCF8563 Datasheet** — sibling cheap RTC.
- **Microchip MCP79410 Datasheet** — RTC + EEPROM + Unique ID.
- **`drivers/rtc/rtc-ds1307.c`** — covers DS3231 too; readable.
- **`drivers/rtc/`** — see other RTC drivers; same pattern.
- **`Documentation/rtc.txt`** — RTC subsystem overview.
- **`hwclock(8)`, `rtcwake(8)`, `chrony.conf(5)`** — the user-space toolchain.
- **NTPv4 + chrony architecture** — for the multi-source clock discipline math.
- **Ch 51B** — runtime PM + suspend; the consumer side of "wake on RTC alarm."
- **Ch 107** — GPS+PPS for the sub-µs precision case where an RTC alone isn't enough.

---

> **End of Part VII — Device Cookbook (Ch 64–117, 54 chapters).** Every common device class has been covered with 2–4 real chips, schematics, DT, driver internals, from-scratch implementations, labs, and pitfalls. From the cheapest QSPI flash to a precision GPS-disciplined time server, every external chip an i.MX6ULL product is likely to integrate is in this Part. Use it as a reference: jump to the chapter for the chip in front of you.

> Next: **Part VIII — Debug, production, advanced** — JTAG, kernel debugging, OPCS-grade build infrastructure, secure boot, OTA, mainline patch submission. The chapters that take your Linux skills from "I can make this work" to "I can ship this product."
