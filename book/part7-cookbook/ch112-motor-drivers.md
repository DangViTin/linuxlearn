---
chapter: 112
title: Stepper & DC motor drivers (DRV8825, A4988, TMC2209, BTS7960, DRV8302)
part: VII — Device cookbook
estimated_pages: 16
status: draft
---

# Chapter 112 — Stepper & DC motor drivers

> **What:** the four motor-driver families: **stepper** (DRV8825, A4988 — basic step/dir; TMC2209 — silent stallGuard UART config), **DC brush** (BTS7960 — 43 A H-bridge), **BLDC** (DRV8302 — trapezoidal / sinusoidal / FOC), and **servo** (PWM-controlled hobby servos). On the i.MX6ULL we drive a stepper via PWM-step + GPIO-dir, configure TMC2209's RMS current and microstepping over UART, run a closed-loop velocity on a brushed motor with PWM + encoder feedback (Ch 111), and drive a BLDC with trapezoidal commutation. Emphasis on the **electrical safety + thermal limits** that are easy to overlook and fatal to ignore.
> **Why:** any product that *moves* needs one of these. 3D printers (steppers), automated blinds (DC), drone ESCs (BLDC), CNC mills (everything), conveyor belts, robotic arms, automated valves — motor control is its own discipline. Linux makes the *control* easy (Cortex-A7 has plenty of MIPS for PID); the hard parts are the silicon-protection details, the EMI from chopping inductive currents, and the mechanical resonance of the load. Get these wrong and the result ranges from "motor whines" to "MOSFET explodes."
> **Focus:** **steppers need precise step-rate generation (PWM); DC motors need PWM + H-bridge + current feedback; BLDC needs commutation (rotor-position-aware switching of 3 half-bridges)**. The kernel's PWM framework (Ch 48) handles step generation for steppers. For DC/BLDC closed-loop, you'll bolt together: encoder (Ch 111) + PID + PWM + current sense (INA226 from Ch 75). For absolute-torque or smooth-low-RPM BLDC, you need FOC (Field-Oriented Control) which most engineers offload to a dedicated MCU (e.g., SimpleFOC on STM32) because Linux's jitter exceeds the 10 kHz current-loop budget.

## 112.1  Driver type pick-guide

| Motor | Best driver | When |
|---|---|---|
| NEMA17 stepper, 1 A, low noise | TMC2209 | 3D printer, lab automation, anywhere quiet matters |
| NEMA17 stepper, 1 A, BOM critical | DRV8825 / A4988 | cost-sensitive, noise OK |
| NEMA23+ stepper, 3+ A | TMC2226 / DM542 (external driver) | larger machines |
| Small DC brush motor, ≤ 1 A | TB6612FNG | simple bidirectional control |
| Large DC brush motor, 5–40 A | BTS7960 | electric scooters, automation actuators |
| BLDC outrunner (drone motor) | DRV8302 / ODrive ESC | low-RPM torque, smooth |
| RC servo (positioning) | (no driver — PWM direct) | hobby pan-tilt, robotic joints |

## 112.2  Steppers — step/dir interface

A stepper rotates 1.8° (200 steps) or 0.9° (400 steps) per full step. Microstepping (1/2, 1/4, ..., 1/256) interpolates between full steps for smoother motion and finer resolution (at lower torque per microstep).

Driver interface (DRV8825, A4988):
- **STEP** pin — rising edge advances one (micro)step.
- **DIR** pin — 0 = CW, 1 = CCW.
- **ENABLE** pin (active low) — disables the outputs (motor freewheels).
- **M0, M1, M2** pins — microstep configuration (000 = full, 001 = 1/2, …, 101 = 1/32).
- **SLEEP, RESET** — typically tied high.

Wiring:

```
   i.MX6ULL PWM ────── STEP            ┌────── A+ ─── motor coil A ─── A−
   GPIO         ────── DIR             │       B+ ─── motor coil B ─── B−
   GPIO         ────── ENABLE     DRV8825         (motor terminals)
   GPIO ×3      ────── M0/M1/M2     │       Vmot (12–45 V) + bulk cap
                                       └──────  GND
   Logic supply 3.3/5 V
```

The PWM generates step pulses; the driver chops the current. Current is set by a trimpot (or in TMC2209 via UART).

**Critical**: every driver has a "current limit" you set with a trimpot (sense resistor + reference voltage). Set too high → driver overheats and shuts down. Set too low → motor stalls. For NEMA17 + DRV8825 + 0.1 Ω sense → Vref = Imax × 5 × 0.1 = ~0.4 V for 0.8 A current. Measure with multimeter on the trimpot wiper; adjust slowly.

## 112.3  Stepper from Linux — PWM step generation

Use the kernel PWM (Ch 48) to generate steps:

```sh
# Configure PWM for 1 kHz step rate
echo 0 > /sys/class/pwm/pwmchip0/export
echo 1000000 > /sys/class/pwm/pwmchip0/pwm0/period       # 1 ms = 1 kHz
echo 500000  > /sys/class/pwm/pwmchip0/pwm0/duty_cycle   # 50 %
echo 1 > /sys/class/pwm/pwmchip0/pwm0/enable

# Set direction
gpioset gpiochip4 22=0     # CW

# At 1 kHz and 1/8 microstepping, motor rotates at 1000/(8×200) = 0.625 rev/s = 37.5 RPM
```

For variable speed (acceleration profile), modify the PWM period over time:

```c
/* Accelerate from 100 Hz to 5 kHz over 1 second */
for (int hz = 100; hz <= 5000; hz += 100) {
    int period_ns = 1000000000 / hz;
    int duty_ns   = period_ns / 2;
    write_file("/sys/class/pwm/pwmchip0/pwm0/period", period_ns);
    write_file("/sys/class/pwm/pwmchip0/pwm0/duty_cycle", duty_ns);
    usleep(20000);                                       /* 20 ms per step */
}
```

For coordinated multi-axis motion (CNC, 3D printer) this isn't enough — you need a lookahead planner (Marlin, Klipper architecture). Klipper runs the motion planner on Linux and offloads the step-generation to an STM32 over USB serial; this is the canonical "Linux + MCU" split for serious CNC.

## 112.4  TMC2209 — UART configuration for silent stepping

TMC2209 (Trinamic) is the modern silent stepper driver. Same step/dir interface as DRV8825, but a **UART configuration interface** lets you set:
- Microstepping (up to 1/256, smooth interpolation)
- RMS current (in mA, very precise)
- stealthChop (silent voltage-mode chop) vs spreadCycle (fast current-mode chop)
- stallGuard (sensorless homing — detects when motor stalls into an end-stop)
- CoolStep (auto-reduce current when load is low)

The UART is single-wire (TX and RX share); driver auto-direction-switches:

```
   i.MX UART TX ───┬─── TMC2209 PDN_UART
                   │
                   └── 1 kΩ ───── i.MX UART RX
```

Linux driver: none in mainline (TMC's official driver is C++ and runs on STM32). For Linux, write a small user-space UART driver matching the TMC datagram format:

```c
struct tmc_write {
    uint8_t sync = 0x05;       /* sync nibble + reserved nibble */
    uint8_t slave_addr;
    uint8_t reg_addr | 0x80;   /* MSB set = write */
    uint32_t data;
    uint8_t crc;               /* TMC's specific CRC8 */
};

/* Set RMS current = 800 mA */
tmc_write(addr=0, IHOLD_IRUN, (HOLD_CURRENT << 0) | (RUN_CURRENT << 8) | (IHOLDDELAY << 16));
```

The TMC2209 datasheet (1MB PDF, very readable) walks every register. Once configured, the motor is whisper-quiet — a 3D printer goes from "rocket launch" to "fridge hum."

## 112.5  DC brushed motor — H-bridge + PWM

```
                     Vbat
                       │
              ┌───────┴───────┐
              │                │
      ┌── H1 (high-side)    H3 (high-side)──┐
      │                                      │
   Motor terminal A                Motor terminal B
      │                                      │
      ┌── L1 (low-side)     L3 (low-side)──┐
              │                │
              └───────┬───────┘
                      GND

   Forward:  H1+L3 on  (current A→B)
   Reverse:  H3+L1 on  (current B→A)
   Brake:    L1+L3 on  (both terminals shorted to GND)
   Coast:    all off (motor freewheels)
```

PWM the high-side (or both sides) to control voltage/torque. The BTS7960 packages all of this in two ICs (BTS7960 each is a half-bridge); you wire two together for full H-bridge.

```
   i.MX PWM1 → BTS7960 #1 RPWM (forward PWM)
   i.MX PWM2 → BTS7960 #2 RPWM (reverse PWM)
   i.MX GPIO → both enables
   Vbat (5–27 V) → both BTS7960 Vmot
   Motor → between the two BTS7960 outputs
```

To drive forward at 50 %:
```sh
echo 50% > /sys/class/pwm/pwmchip1/pwm0/duty_cycle  # forward PWM
echo 0   > /sys/class/pwm/pwmchip1/pwm1/duty_cycle  # reverse off
```

To brake: set both PWMs to 0 and assert enable; both low-sides switch on → motor terminals shorted → fast brake.

**Critical**: never assert both high-sides (forward + reverse) simultaneously — that's a shoot-through short across Vbat. The BTS7960 has internal cross-conduction protection but external H-bridges from discrete MOSFETs need software interlock + dead-time.

## 112.6  BLDC — commutation 101

A BLDC motor has 3 stator coils and a permanent-magnet rotor. To spin, you cycle current through pairs of coils in synchronism with the rotor position:

```
   Rotor angle:    0°        60°       120°      180°      240°      300°
   Energize:       A+B-       A+C-      B+C-      B+A-      C+A-      C+B-
   (i.e., "A to B" means current from coil A's terminal to coil B's)
```

To know rotor position:
- **Hall sensors** (3 of them, integrated on the motor) — gives 60° resolution → trapezoidal commutation.
- **Encoder** — finer resolution → sinusoidal commutation.
- **Sensorless back-EMF detection** — measure the un-energized coil's voltage; zero-crossing tells you where you are. Works above ~10 % nominal speed.

DRV8302 (TI) is the gate driver for 3 half-bridges + provides current-sense amplifiers. You add 6 N-FETs and you have a BLDC ESC. The MCU (or Linux) runs commutation logic.

For Linux: the **timing is too tight for closed-loop control** at full speed. A BLDC at 10,000 RPM with 14 magnetic poles cycles 14 × 10,000 / 60 = 2,333 commutations/s. Each must be timed within ~50 µs or torque ripple shows. Linux's interrupt jitter > 100 µs.

**Solution**: offload commutation to a dedicated MCU. Use **SimpleFOC** (Arduino-based, STM32) or **ODrive** (a dedicated BLDC controller). Linux supervises (sends target speed via UART or USB); MCU does the kHz current loop.

For hobbyist trapezoidal commutation on a slow BLDC (< 1000 RPM):

```c
/* Sensored trapezoidal commutation — 6-step */
uint8_t hall_state = (gpio_read(HALL_A) << 2) | (gpio_read(HALL_B) << 1) | gpio_read(HALL_C);
/* Map hall_state (1..6, two invalid) to gate pattern */
static const uint8_t COMMUTATE_TBL[8] = {
    /* hall: 000  001  010  011  100  101  110  111 */
    /* gate: inv  4    2    3    6    5    1    inv  */
        0,   4,   2,   3,   6,   5,   1,   0,
};
uint8_t pattern = COMMUTATE_TBL[hall_state];
apply_gates(pattern, pwm_duty);
```

This runs on hall-IRQ → at 1000 RPM × 14 poles = 234 IRQ/s. Linux can handle that.

## 112.7  Lab

1. **Stepper basic.** Wire DRV8825 + a NEMA17. Vref to 0.4 V (~0.8 A). PWM 1 kHz on STEP. Confirm motor turns at 0.625 rev/s.
2. **Microstepping.** Set M0/M1/M2 = 1/16. Spin at same step rate → 1/8 the angular velocity but smoother.
3. **Acceleration profile.** Linear ramp from 100 Hz to 5 kHz over 1 second. Test for missed steps (motor stalls under acceleration).
4. **TMC2209 silent mode.** Wire UART. Write IHOLD_IRUN to set 800 mA RUN, 400 mA HOLD. Compare noise vs DRV8825 — TMC should be near-silent.
5. **stallGuard homing.** Send a slow move; monitor TMC2209's DIAG pin; when motor hits an end-stop, DIAG asserts → use as a sensor-less home switch.
6. **DC motor open loop.** Wire BTS7960 + a 12 V motor. PWM duty 50 %; motor spins. Reverse direction by swapping which PWM is active.
7. **DC motor closed-loop velocity.** Add encoder (Ch 111); PID loop targets 1000 RPM regardless of load. Tune Kp/Ki.
8. **BLDC trapezoidal.** Wire DRV8302 + 6 MOSFETs + a sensored BLDC. Implement 6-step commutation in user-space. Spin at low RPM.
9. **BLDC FOC offload (stretch).** Buy an ODrive or BL-MGN board. Linux sends UART commands; the dedicated MCU does FOC. Compare torque smoothness.
10. **Safety stop.** Add an emergency-stop GPIO that asserts all driver ENABLE pins low → motor freewheels. Wire to a physical button.

## 112.8  Pitfalls

- **Stepper current too high.** DRV8825 / A4988 overheat and thermally shut down. Set Vref carefully; add heat sink + airflow.
- **Stepper missed steps.** Acceleration too aggressive or current too low. Add longer ramp or increase current.
- **No back-EMF clamp diodes.** Switching off an inductive load (motor coil) generates voltage spikes that destroy MOSFETs. Drivers like BTS7960 have internal clamps; discrete designs need flyback diodes.
- **PWM frequency in motor's audible range.** 1–10 kHz PWM makes motors whine. Bump to >20 kHz (ultrasonic) or use stealthChop (TMC).
- **H-bridge shoot-through.** Never enable both high and low side of the same leg simultaneously. Use a driver IC with dead-time, or software interlock.
- **Powering driver Vmot before logic Vcc.** Some drivers latch up; check the datasheet sequence. BTS7960 is tolerant; A4988 is sensitive.
- **Insufficient bulk capacitance on Vmot.** Motor inrush sags the rail; logic supply brown-outs. Add 470 µF+ low-ESR cap per driver.
- **EMI from motor brushes.** A DC brushed motor radiates broadband RF. Add ceramic caps (100 nF) across motor terminals + an LC filter on the supply line. WiFi and CAN buses near unfiltered motors fail intermittently.
- **TMC2209 UART CRC mismatch.** Easy to compute wrong. Use the official polynomial table or copy from the TMC library.
- **BLDC wrong phase order.** If the motor spins backward when you command forward, swap any two motor phases (e.g., A ↔ B). Don't rely on coil-color conventions — they're not standard.
- **No current limit on the supply.** A stalled motor draws stall current = Vbat / Rcoil. NEMA17 stalled: 12 V / 3 Ω = 4 A. Without a current-limited supply or a fuse, the wiring smokes.

## 112.9  Going deeper

- **TI DRV8825 datasheet + application notes** — the canonical stepper-driver tutorial.
- **Trinamic TMC2209 datasheet + datagram structure** — for UART config.
- **Infineon BTS7960 datasheet** — H-bridge integration.
- **TI DRV8302 datasheet** — BLDC gate driver.
- **SimpleFOC project (Arduino-based)** — readable FOC implementation; runs on STM32 or ESP32.
- **ODrive project** — open-source BLDC controller for high-performance robotics.
- **Klipper firmware** — Linux + MCU split architecture for 3D printers; great reference for "Linux as motion planner."
- **Ch 48** — PWM kernel framework.
- **Ch 111** — encoder feedback (essential for closed-loop control).

---

> Next chapter: **Chapter 113 — WS2812 / SK6812 / APA102 addressable LEDs** — Group S (Indicators & smart LEDs).
