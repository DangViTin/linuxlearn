---
chapter: 55G
title: Multi-touch (GT911)
part: VI - Driver development (supplementary v1.1)
estimated_pages: 12
status: draft
---

# Chapter 55G: Multi-touch (GT911)

> **What:** the **MT-B** (slot-based multi-touch) protocol, the kernel's standard for reporting per-finger touch coordinates, and the **Goodix GT911**, the common I²C capacitive touch controller that ships with most off-the-shelf RGB-parallel LCDs (ATK4384, ATK7016, ATK10261).
>
> **Why:** for any product with a touch panel, this is the input. The mainline `goodix` driver covers GT911, GT9110, GT9271 and other variants. You usually just configure DT correctly. Calibration is rarely needed for capacitive (unlike resistive). The panel's coordinate frame is wired in DT.
>
> **Focus:** **MT-B is slot-based**. Each tracked finger gets a *slot*. The driver reports per-slot position. Older code uses MT-A. Current code uses MT-B.


## 55G.1  MT-B vs MT-A

**MT-A** (legacy): each touch group is bracketed by `MT_SYNC` events. The kernel tracks which contact is which by proximity in successive frames. Order-dependent, confusing.

**MT-B** (current): the driver assigns each contact a *slot* number. As long as the same finger is down, its slot doesn't change. Cleaner code, cleaner user-space.

A two-finger touch event in MT-B:

```
EV_ABS  ABS_MT_SLOT       0
EV_ABS  ABS_MT_TRACKING_ID  42
EV_ABS  ABS_MT_POSITION_X 100
EV_ABS  ABS_MT_POSITION_Y 200

EV_ABS  ABS_MT_SLOT       1
EV_ABS  ABS_MT_TRACKING_ID  43
EV_ABS  ABS_MT_POSITION_X 300
EV_ABS  ABS_MT_POSITION_Y 400

EV_SYN  SYN_REPORT
```

Finger lift: write `ABS_MT_TRACKING_ID = -1` to that slot.

## 55G.2  GT911 in DT

```dts
&i2c2 {
    gt911@5d {
        compatible = "goodix,gt911";
        reg = <0x5d>;
        interrupt-parent = <&gpio1>;
        interrupts = <9 IRQ_TYPE_EDGE_FALLING>;
        irq-gpios = <&gpio1 9 GPIO_ACTIVE_HIGH>;
        reset-gpios = <&gpio5 2 GPIO_ACTIVE_HIGH>;
        touchscreen-size-x = <1024>;
        touchscreen-size-y = <600>;
        touchscreen-inverted-x;
        touchscreen-inverted-y;
        touchscreen-swapped-x-y;
    };
};
```

Key properties:
- **`reg = <0x5d>` or `<0x14>`**: the GT911 has two I²C addresses. The IRQ pin level at reset selects which: 0x5d when IRQ is low, 0x14 when IRQ is high.
- **`reset-gpios`**: pulsed at probe.
- **`touchscreen-size-x/y`**: physical resolution to report. Usually matches the LCD.
- **`touchscreen-inverted-x/y`, `touchscreen-swapped-x-y`**: rotate/flip the touch coordinate frame to match the LCD orientation.

## 55G.3  Wiring

GT911 needs:
- VDD (3.3V).
- GND.
- SDA, SCL.
- INT (touch-event interrupt. Also doubles as I²C-address-select at reset).
- RST.

The driver bring-up sequence for RST and INT selects the I²C address. The driver handles this for you.

## 55G.4  Verify it works

```
[root@pa-mini:~]# dmesg | grep -i goodix
Goodix-TS 1-005d: ID 911, version: 1060
[root@pa-mini:~]# ls /dev/input/event*
/dev/input/event0  /dev/input/event1
[root@pa-mini:~]# evtest /dev/input/event1
Supported events:
  Event type 1 (EV_KEY)
    Event code 330 (BTN_TOUCH)
  Event type 3 (EV_ABS)
    Event code 47 (ABS_MT_SLOT)
        Value      0
        Min        0
        Max        4
    Event code 53 (ABS_MT_POSITION_X)
        Min        0
        Max     1024
    ...

[Press a finger]
Event: time 12345.67, type 3 (EV_ABS), code 57 (ABS_MT_TRACKING_ID), value 0
Event: time 12345.67, type 3 (EV_ABS), code 53 (ABS_MT_POSITION_X), value 312
Event: time 12345.67, type 3 (EV_ABS), code 54 (ABS_MT_POSITION_Y), value 450
Event: time 12345.67, type 1 (EV_KEY), code 330 (BTN_TOUCH), value 1
Event: time 12345.67, ------------ SYN_REPORT ---------
```

Touch is now reported through standard input events. User-space tools (X11, Wayland, Qt eglfs/linuxfb) consume them.

## 55G.5  Coordinate frame fixes

If touch is "mirrored" or "rotated" relative to the visible LCD:

- **Inverted X** (left/right swapped): `touchscreen-inverted-x;`
- **Inverted Y** (top/bottom swapped): `touchscreen-inverted-y;`
- **Swapped X-Y** (touched a horizontal line, axis is vertical): `touchscreen-swapped-x-y;`

Try combinations until the touch matches the cursor on screen. For resistive touchscreens (XPT2046 etc.), this isn't enough, you need software calibration with `xinput_calibrator`, since the touch values are not linearly mapped to display pixels.

## 55G.6  Firmware

GT911 boots from internal ROM but accepts firmware updates via I²C. Some boards ship a firmware file. The driver auto-loads from `/lib/firmware/goodix_911.fw` if present. Without it, the chip uses its ROM firmware, usually adequate.

## 55G.7  Lab

1. **Bring up GT911 on a known LCD.** Verify probe in dmesg, touch event on evtest.
2. **Fix orientation.** Trial-and-error the `inverted-*` and `swapped` flags until touch matches LCD.
3. **Five-finger test.** Watch slot 0–4 fill as you put fingers down.
4. **Adapt for a different LCD.** Change `touchscreen-size-x/y` for a different panel. Verify proportions are correct.
5. **Long-press detection.** In user-space, time how long ABS_MT_TRACKING_ID stays non-(-1). After 500 ms, emit a "long-press" event.
6. **Gestures.** Write a libinput-based program that detects swipes.

## 55G.8  Pitfalls

- **Wrong I²C address.** RST/INT timing at reset selects 0x5d vs 0x14. If the driver's expected address doesn't match, no probe.
- **Missing reset-gpios.** Chip never wakes up. I²C-detect fails.
- **Polling instead of IRQ.** Without `interrupts`, driver polls (slow, laggy). Always wire and declare the IRQ.
- **`touchscreen-size-x/y` wrong.** Touch coordinates reported in wrong range. User-space scales weirdly.
- **Touch latency from kernel.** Default `goodix` driver is good. If you have weird latency, check `evtest` timestamps against vsync.
- **Two touchscreens conflict.** XPT2046 + GT911 both on the same panel? Pick one in DT.

## 55G.9  Going deeper

- **`Documentation/input/multi-touch-protocol.rst`**: MT-B protocol reference.
- **`drivers/input/touchscreen/goodix.c`**: the GT911 driver.
- **`Documentation/devicetree/bindings/input/touchscreen/goodix.yaml`**: DT binding.
- **`tools/testing/selftests/input/`**: input test tooling.

> Next chapter: **Chapter 55H: RGB-to-HDMI bridge (sii902x).** Adding HDMI output to an i.MX6ULL by hanging an HDMI transmitter chip off the LCDIF parallel RGB.
