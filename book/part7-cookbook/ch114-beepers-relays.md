---
chapter: 114
title: Beepers, relays, SSRs
part: VII — Device cookbook
estimated_pages: 10
status: draft
---

# Chapter 114 — Beepers, relays, SSRs

> **What:** the **discrete actuators** that fall outside the main subsystems but appear in every product: **passive piezo buzzers** (need PWM to make sound), **active buzzers** (fixed-frequency, GPIO on/off), **mechanical relays** (5 V or 12 V coils driving 240 V AC contacts), **MOSFETs** (DC switching, fast, no contact wear), and **SSRs (Solid State Relays)** (AC switching, opto-isolated, zero-cross, the production-grade choice for mains-load control). On the i.MX6ULL we drive each with the matching kernel framework (PWM for passive, GPIO for the rest), wire the protection circuits (flyback diodes, snubbers, isolation), and build a 4-channel home automation relay board controlled via MQTT.
>
> **Why:** real products take physical actions: beep on user input, switch a pump, turn on a heater, drive a solenoid valve, ring a bell. Each actuator has different electrical requirements and different safety pitfalls. Get them wrong and you damage the driver, miss a debounce, energize an AC load while the relay's contact is half-open (arcing → contact welding → can't turn off → fire). This chapter is short but covers the engineering details that separate a demo from a five-year shipping product.
>
> **Focus:** three non-negotiable rules for the actuators in this chapter. Inductive loads (relays, solenoids, motors) need a flyback diode. AC loads need isolation. Zero-cross AC switching needs a zero-cross SSR; non-zero-cross switching arcs, generates harmonics, and burns contacts. The Linux side is trivial — sysfs PWM or GPIO. The electrical-engineering side is most of the work.

## 114.1  Buzzers — passive vs active

| | Passive piezo | Active buzzer |
|---|---|---|
| Construction | bare piezo disc | piezo + oscillator IC |
| Drive | needs AC signal (PWM) | GPIO on/off (it self-oscillates) |
| Frequency | you choose (typ. 2–4 kHz) | fixed (typ. 2.7 kHz) |
| Volume control | yes (PWM duty) | no |
| Cost | $0.15 | $0.30 |
| Use | melodies, tones, frequency-encoded info | "beep" indicators |

### Passive buzzer

```
   i.MX PWM ──── 1 kΩ ──── Gate of small MOSFET (e.g. 2N7000)
                                  │
                              Drain ── one terminal of piezo
   Other piezo terminal ────── 5 V

   Or simpler: PWM pin direct to piezo (works if piezo low-capacitance + low current)
```

Drive a 2 kHz square wave at 50 % duty:

```sh
echo 0 > /sys/class/pwm/pwmchip0/export
echo 500000 > /sys/class/pwm/pwmchip0/pwm0/period      # 500 µs = 2 kHz
echo 250000 > /sys/class/pwm/pwmchip0/pwm0/duty_cycle  # 50 %
echo 1 > /sys/class/pwm/pwmchip0/pwm0/enable

sleep 0.2   # beep
echo 0 > /sys/class/pwm/pwmchip0/pwm0/enable
```

Volume = duty cycle (max at 50 %; both 0 % and 100 % = silence). Pitch = frequency.

Play a melody: change the period over time. A "Mario" tone sequence is just a list of `(freq, duration)` tuples.

### Active buzzer

Simpler:

```c
gpio_write(BUZZER, 1); usleep(100000);
gpio_write(BUZZER, 0);
```

No PWM, no MOSFET (most active buzzers tolerate direct 3.3/5 V GPIO drive at < 30 mA). Pitch is whatever the buzzer's internal oscillator gives.

## 114.2  Mechanical relays — the basics

A relay = electromagnetically actuated switch. Coil (5/12/24 V DC) energizes → moves armature → switches contacts.

```
Logic side             Load side
─────────              ────────────
                                       NC ───┐
                                              │
                                              ├─── one side of load
                                              │
3.3 V GPIO ───┐                         NO ───┘
              │
              │       ┌────┐
              ├──── ▲ │coil│ ───── 12 V
              │     │ └────┘
              │     │      ┌──── 1N4007 flyback diode
              │     └─◄────┤    (cathode to +12, anode to GND-side coil terminal)
              │            └──── GND
              │
            NPN BJT, 2N2222 (relay coil current 30 mA at 12 V → 3.3 V GPIO can't sink directly)
```

**The flyback diode is mandatory.** When the GPIO drops and the BJT turns off, the relay coil's inductance generates a back-EMF spike (hundreds of volts). Without the diode, the spike kills the BJT, propagates back, damages the SoC. The diode shorts the spike harmlessly.

Linux side:

```sh
gpioset gpiochip4 22=1   # relay on
gpioset gpiochip4 22=0   # relay off
```

Mechanical relay characteristics:
- **Switching time**: ~10 ms on, ~5 ms off.
- **Contact rating**: typically 10 A AC at 250 V (per relay datasheet).
- **Life**: ~10⁵ switches at rated load; 10⁷ at much-reduced load.
- **Noise**: audible click; some applications (libraries, hospitals) prefer SSRs to avoid noise.

## 114.3  MOSFET for DC loads — fast, silent, infinite life

For DC loads (LEDs, fans, small heaters, solenoid valves), use a logic-level N-FET (IRLZ44N, AOD508, IRF3205) instead of a relay:

```
Logic              Load
─────              ───────
                    Vload (+12 V)
                       │
                     Load
                       │
GPIO ─── 100 Ω ── ┤ Gate
                  ├ Drain
                  ┤ Source
                       │
                      GND
                       │
                  10 kΩ pull-down on gate
                  (so the gate doesn't float when GPIO is tri-stated during boot)
```

PWM the gate to dim a load (LEDs, motor speed):

```sh
# 25 kHz PWM (above audio range) at 40 % duty
echo 40000 > /sys/class/pwm/pwmchip0/pwm0/period
echo 16000 > /sys/class/pwm/pwmchip0/pwm0/duty_cycle
```

For inductive DC loads (DC motor, solenoid): add a flyback diode (Schottky for fast loads) across the load.

## 114.4  Solid-state relays (SSRs) for AC loads — the production choice

For mains AC loads (heaters, lamps, pumps, fans on AC):

```
Logic side                   Load side
─────────                   ──────────
GPIO 3.3 V ─── 330 Ω ─── ┌──┴── Opto ──┐── Triac/SCR ─── L (Live)
                          │             │
                          │             │       ┌── snubber R+C
GND ──────────────────── └──────────────┘       │   across triac
                                                  │
                          Load (heater, lamp, etc.)   N (Neutral)
```

A typical 25 A SSR module (Fotek SSR-25DA, Crydom A2425) handles 240 VAC × 25 A. Key features:

- **Optical isolation** between logic and load (typically 4 kV).
- **Zero-cross switching** — triac fires only at the AC zero-crossing; eliminates inrush and harmonics. Mandatory for resistive (heater) loads; rough for motor loads (the motor may lag).
- **No moving parts** — silent, fast, infinite life if not abused.
- **Always-on leakage** — even when "off," a few mA leaks through. Don't rely on the SSR to make a load *electrically dead* for service work; use a contactor or pull the plug.

Linux side: just GPIO toggle, same as mechanical relay. The SSR's internal opto + zero-cross logic handles the rest.

## 114.5  AC safety — non-negotiable rules

Live AC kills. Working with mains:

1. **Isolation 4 kV minimum** between logic and mains side. Module SSRs deliver this; bench-built circuits often don't.
2. **Fuses on the AC side.** A shorted load (motor stalls, heater coil melts) without a fuse will burn wiring or weld SSR contacts.
3. **Proper wire gauge.** 16 AWG minimum for 10 A circuits; 14 AWG for 15 A. Solid copper, properly crimped to terminals.
4. **Insulated enclosure** with no exposed mains-side conductors when assembled. Use commercial enclosures with strain reliefs.
5. **Earth bonding.** Any metal enclosure must be earthed. A pre-failure short-to-chassis trips the earth-leakage breaker instead of electrocuting the user.
6. **GFCI / RCD upstream.** Your distribution panel should have residual-current protection. Don't rely on it as primary safety, but it saves lives on partial failures.
7. **No live work.** Never wire or troubleshoot a powered-up circuit. Pull the plug, even for "quick checks."
8. **Voltmeter before touching.** After unplugging, verify no voltage. Capacitors hold charge.
9. **Certification for products.** UL (US), CE (EU), CCC (China) require safety testing of any mains-load product before sale.

This chapter cannot replace a proper electrical-safety class. Get a qualified electrician to review your design if you are not one.

## 114.6  Worked example — 4-channel home-automation relay board

Hardware:
- i.MX6ULL on a DIN-rail enclosure
- 4× Songle SRD-05VDC-SL-C relays driving 240 VAC outputs through screw terminals
- 4× 2N2222 BJT + 1N4007 flyback for coil drive
- 4× LEDs showing each channel state
- Input: PIR motion sensor on a GPIO (Ch 67-style)

Software:
- A Python daemon listening on MQTT `home/relay/N/set`
- States published on `home/relay/N/state`
- Home Assistant subscribes via MQTT integration → 4 toggle switches in the dashboard

```python
import paho.mqtt.client as mqtt
import gpiod

chip = gpiod.Chip('gpiochip0')
relays = [chip.get_line(p) for p in [20, 21, 22, 23]]
for r in relays:
    r.request(consumer='relay', type=gpiod.LINE_REQ_DIR_OUT, default_vals=[0])

state = [0, 0, 0, 0]

def on_message(c, userdata, msg):
    parts = msg.topic.split('/')
    if len(parts) >= 4 and parts[3] == 'set':
        n = int(parts[2])
        val = 1 if msg.payload.decode().lower() in ('on', '1', 'true') else 0
        relays[n].set_value(val)
        state[n] = val
        c.publish(f'home/relay/{n}/state', 'ON' if val else 'OFF', retain=True)

c = mqtt.Client()
c.on_connect = lambda c, u, f, rc: c.subscribe('home/relay/+/set')
c.on_message = on_message
c.connect('localhost')
c.loop_forever()
```

About 40 lines. Install as a systemd unit. Open Home Assistant on a phone, tap "Living Room Lamp", and the relay clicks the lamp on via MQTT.

## 114.7  Lab

1. **Passive buzzer melody.** PWM the buzzer to play "Twinkle Twinkle Little Star" (12 notes, each ~250 ms).
2. **Active buzzer alarm.** GPIO-toggled active buzzer; pulse on/off pattern for a fire-alarm cadence (250 ms on, 250 ms off, repeat).
3. **MOSFET dimmer.** N-FET driving a 12 V LED strip; PWM at 1 kHz with adjustable duty. Set up a sysfs knob to vary brightness.
4. **Mechanical relay safe-switch.** Driver: BJT + flyback. Scope the BJT collector with no diode → see the spike. Add diode → spike gone.
5. **SSR + AC load.** Use a 5 V SSR module to switch a desk lamp (with proper isolation + fuse + enclosure). GPIO toggles every 2 s; lamp blinks.
6. **MQTT relay board.** Build the 4-channel example. Toggle from Home Assistant dashboard.
7. **Inrush measurement.** Switch an incandescent bulb (or motor) with a non-zero-cross SSR; capture the inrush on a current probe. Switch with a zero-cross SSR; compare.
8. **Relay endurance.** Cycle a relay at 1 Hz with rated AC load; count failures over 100,000 cycles (will take 28 hours). Make notes about contact wear.

## 114.8  Pitfalls

- **No flyback diode on relay coil.** Repeated back-EMF spikes will eventually damage the BJT and SoC.
- **GPIO direct-driving a relay coil.** Coil draws 30 mA at 5 V (= 150 mW); GPIO typically tolerates 20 mA max. Burn-out symptom: GPIO works once, then never again.
- **Cheap SSR with rated current.** Fotek SSR-40DA rated "40 A" — actually good for ~25 A continuous and only with a real heatsink. De-rate aggressively.
- **Zero-cross SSR with inductive load.** Motors lag; zero-cross switching at voltage-zero is at current-peak for inductive load → contact stress. For inductive loads use random-fire SSR.
- **Buzzer at the right pitch for piezo resonance.** Most piezos have a sharp resonant peak around 2.7 kHz; driving off-resonance gets you 10 dB less SPL. Find the peak with a sweep.
- **PWM frequency in audio range.** A motor PWM at 1 kHz whines audibly. Bump to 20 kHz+.
- **No GPIO pull-down on MOSFET gate.** During boot, the GPIO is high-impedance for a few seconds; the load floats and may spuriously partially-on. 10 kΩ pull-down ensures off-on-boot.
- **AC neutral switching.** Always switch the LIVE wire, never the NEUTRAL. Switching neutral leaves the load energized when "off" → shock hazard.
- **SSR on the AC neutral.** Same problem; SSR must be on live.
- **No fuses.** A failed driver shorts the load; without a fuse, the wiring becomes the fuse.
- **Inadequate creepage / clearance.** PCB tracks carrying mains must be ≥4 mm apart with no solder bridges. Use a real PCB house with mains-safety design rules.
- **Treating an off SSR as electrically isolated.** SSR leakage is 1–5 mA. Enough to make an LED glow faintly, or — for service — to give a small shock. Pull the plug for service.

## 114.9  Going deeper

- **Songle SRD relay datasheet** — most common 5 V coil mechanical relay.
- **Crydom and Omron SSR catalogs** — quality vs Fotek.
- **IRLZ44N / AOD508 datasheets** — logic-level MOSFETs.
- **IPC-2221** — PCB design standards for creepage and clearance for mains.
- **UL 508A** — industrial control panel safety standard.
- **`pwm-fan` driver in mainline** — PWM-controlled fan with tach feedback, a related actuator pattern.
- **Home Assistant MQTT integration docs** — for the dashboard side.
- **Ch 48** — PWM kernel framework.
- **Ch 51A** — watchdog (essential for safety-critical relay control).

---

> Next chapter: **Chapter 115 — Dual FEC + hosted Ethernet** — networking with both i.MX6ULL FECs plus W5500 / ENC28J60 SPI Ethernet.
