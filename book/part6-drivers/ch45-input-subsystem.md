---
chapter: 45
title: Input subsystem
part: VI — Driver development
estimated_pages: 18
status: draft
---

# Chapter 45 — Input subsystem

> **What:** the **input subsystem** — the kernel framework that turns "a GPIO went low" or "an I²C read returned a touch coordinate" into a standardised event stream consumed by `evdev`, X11, Wayland, framebuffer toolkits, and command-line tools. We'll build a `gpio-keys` derivative — the canonical "GPIO as keyboard key" driver — and walk every byte from the IRQ handler to `evtest` reading `/dev/input/eventN`.
>
> **Why:** every input device on a Linux box — keyboard, mouse, touchscreen, joystick, IR remote — goes through the input subsystem. Once you understand `input_register_device` and `input_event`, *every* input driver in the kernel looks familiar. The framework handles event multiplexing, queueing, sysfs/`evdev` integration, autorepeat, and userspace device-node creation — your driver just calls `input_report_key()` and `input_sync()`.
>
> **Focus:** **type, code, value** — the three-element tuple that describes every input event. Once that triple makes sense — `EV_KEY` + `KEY_ENTER` + `1` means "Enter was pressed" — the rest of the input subsystem (abs axes, relative motion, multi-touch slots) is just different combinations of type/code/value.

## 45.1  The picture

When you press a key on a USB keyboard:

```
   physical key down
        │
   USB-HID interrupt-in transfer reports scan-code 0x28 (Enter)
        │
   usbhid driver: hid_input_report → input_report_key(dev, KEY_ENTER, 1)
        │
   input core:  queue an event {EV_KEY, KEY_ENTER, 1} on every evdev handler
        │
   /dev/input/event3 becomes readable
        │
   user-space: read() returns 24 bytes — a struct input_event
        │
   X11 / Wayland / your application: "Enter was pressed"
```

The driver's only job is to call `input_report_*()` and `input_sync()`. The core handles queueing, multiplexing, and user-space delivery. **Your driver feeds events into the type/code/value protocol**; the input core delivers them to user-space. You never talk to user-space directly.

## 45.2  Event types and codes

`#include <linux/input.h>` — defines hundreds of `EV_*`, `KEY_*`, `BTN_*`, `ABS_*`, `REL_*`, `SW_*`, `LED_*`, `SND_*`, `MSC_*` constants.

Common event types:

| Type | Meaning | Typical codes |
|------|---------|---------------|
| `EV_SYN` | Synchronization — end-of-event-group marker | `SYN_REPORT` (always 0) |
| `EV_KEY` | Key/button pressed/released | `KEY_A`...`KEY_Z`, `KEY_ENTER`, `BTN_LEFT`, `BTN_TOUCH` |
| `EV_REL` | Relative axis (mouse motion, scroll wheel) | `REL_X`, `REL_Y`, `REL_WHEEL` |
| `EV_ABS` | Absolute axis (touchscreen, joystick, IMU) | `ABS_X`, `ABS_Y`, `ABS_PRESSURE`, `ABS_MT_SLOT` |
| `EV_MSC` | Miscellaneous (scancode, raw value pass-through) | `MSC_SCAN`, `MSC_RAW` |
| `EV_SW` | Switch (lid open/closed, headphone jack, dock) | `SW_LID`, `SW_HEADPHONE_INSERT` |
| `EV_LED` | LED state output (driver consumes from userspace) | `LED_NUML`, `LED_CAPSL` |
| `EV_SND` | Sound output (PC speaker beep) | `SND_BELL`, `SND_TONE` |

Each event has a **value** appropriate to its type:

- `EV_KEY` value: `0` = released, `1` = pressed, `2` = autorepeat.
- `EV_REL` value: signed delta (+1, -3, etc.).
- `EV_ABS` value: absolute position, in whatever range the driver declared.
- `EV_SYN` value: usually 0.

A coherent group of events ends with `EV_SYN`/`SYN_REPORT`. The input core delivers all events between two `SYN_REPORT`s atomically to userspace — important when a single touch update sends multiple coordinates that must arrive together.

## 45.3  The mainline `gpio-keys` driver

Before we write our own, let's notice that **the kernel already has `gpio-keys`** — the in-tree driver that exposes any number of DT-described GPIOs as keyboard keys. For real production use, just use it. The DT looks like this:

```dts
gpio_keys {
    compatible = "gpio-keys";

    key-enter {
        label = "Enter";
        linux,code = <KEY_ENTER>;
        gpios = <&gpio1 19 GPIO_ACTIVE_LOW>;
        debounce-interval = <50>;
        wakeup-source;
    };

    key-up {
        label = "Up";
        linux,code = <KEY_UP>;
        gpios = <&gpio4 14 GPIO_ACTIVE_LOW>;
        debounce-interval = <50>;
    };
};
```

Set `CONFIG_KEYBOARD_GPIO=y` in the kernel config, boot. Pressing the GPIO19 button now generates real `KEY_ENTER` events on `/dev/input/eventN`.

For learning purposes, though, we'll write our own version so we know what the framework is doing.

## 45.4  Writing our own button driver

`button_input.c`:

```c
#include <linux/init.h>
#include <linux/module.h>
#include <linux/platform_device.h>
#include <linux/gpio/consumer.h>
#include <linux/input.h>
#include <linux/interrupt.h>

struct button_dev {
    struct input_dev *input;
    struct gpio_desc *gpio;
    int irq;
};

static irqreturn_t button_irq(int irq, void *dev_id)
{
    struct button_dev *bd = dev_id;
    int pressed = gpiod_get_value_cansleep(bd->gpio);
    /* The gpiod API has already applied ACTIVE_LOW polarity:
       pressed=1 here means logically pressed. */
    input_report_key(bd->input, KEY_ENTER, pressed);
    input_sync(bd->input);
    return IRQ_HANDLED;
}

static int button_probe(struct platform_device *pdev)
{
    struct button_dev *bd;
    int err;

    bd = devm_kzalloc(&pdev->dev, sizeof(*bd), GFP_KERNEL);
    if (!bd)
        return -ENOMEM;

    bd->gpio = devm_gpiod_get(&pdev->dev, "button", GPIOD_IN);
    if (IS_ERR(bd->gpio))
        return dev_err_probe(&pdev->dev, PTR_ERR(bd->gpio), "no button gpio\n");

    bd->irq = gpiod_to_irq(bd->gpio);
    if (bd->irq < 0)
        return bd->irq;

    bd->input = devm_input_allocate_device(&pdev->dev);
    if (!bd->input)
        return -ENOMEM;

    bd->input->name = "linuxlearn-button";
    bd->input->phys = "button/input0";
    bd->input->id.bustype = BUS_HOST;

    /* Declare what events this device can emit */
    input_set_capability(bd->input, EV_KEY, KEY_ENTER);

    err = input_register_device(bd->input);
    if (err)
        return dev_err_probe(&pdev->dev, err, "input register failed\n");

    err = devm_request_threaded_irq(&pdev->dev, bd->irq, NULL, button_irq,
                                     IRQF_TRIGGER_RISING | IRQF_TRIGGER_FALLING
                                     | IRQF_ONESHOT,
                                     "linuxlearn-button", bd);
    if (err)
        return err;

    platform_set_drvdata(pdev, bd);
    return 0;
}

static const struct of_device_id button_of_match[] = {
    { .compatible = "linuxlearn,input-button" },
    { }
};
MODULE_DEVICE_TABLE(of, button_of_match);

static struct platform_driver button_driver = {
    .driver = {
        .name = "linuxlearn-input-button",
        .of_match_table = button_of_match,
    },
    .probe = button_probe,
};
module_platform_driver(button_driver);

MODULE_LICENSE("GPL");
```

The flow:

1. `devm_input_allocate_device()` allocates an `input_dev` and ties its lifetime to the parent device.
2. We fill in identification — `name` (visible in `evtest`), `phys` (physical-bus path), `id.bustype` (origin family).
3. `input_set_capability(input, EV_KEY, KEY_ENTER)` declares "this device can emit `EV_KEY` events with code `KEY_ENTER`." User-space tools query this via the EVIOCGBIT ioctl to learn what events to expect.
4. `input_register_device()` registers with the core. A `/dev/input/eventN` node appears.
5. In the IRQ handler, `input_report_key()` + `input_sync()` deliver one event.

DT:

```dts
my_button {
    compatible = "linuxlearn,input-button";
    button-gpios = <&gpio1 19 GPIO_ACTIVE_LOW>;
    pinctrl-names = "default";
    pinctrl-0 = <&pinctrl_button>;
};
```

Build, load:

```
[root@pa-mini:~]# insmod button_input.ko
[root@pa-mini:~]# cat /proc/bus/input/devices
I: Bus=0019 Vendor=0000 Product=0000 Version=0000
N: Name="linuxlearn-button"
P: Phys=button/input0
S: Sysfs=/devices/platform/my_button/input/input2
H: Handlers=evdev event2
B: PROP=0
B: EV=3
B: KEY=10000000 ... (sparse bit; KEY_ENTER is bit 28)

[root@pa-mini:~]# evtest /dev/input/event2
... waits ...
Press button: Event: time 4242.12, type 1 (EV_KEY), code 28 (KEY_ENTER), value 1
            Event: time 4242.12, ------------ SYN_REPORT -----------
Release:    Event: time 4242.45, type 1 (EV_KEY), code 28 (KEY_ENTER), value 0
            Event: time 4242.45, ------------ SYN_REPORT -----------
```

Done. Button is a real keyboard key.

## 45.5  Auto-repeat, debounce, and key mapping

The `input` core provides **autorepeat** for free: register `EV_REP` capability and the core will generate repeat events (value=2) while a key is held. `gpio-keys` does this automatically; our minimal driver doesn't bother.

**Debounce** is software (or hardware). `gpio-keys` uses a timer (`debounce-interval` ms) — on the falling edge, schedule a delayed work; only report the event if the GPIO is still low after the delay. Implementing this in our driver is an exercise. The pattern: cancel the previous delayed work, schedule a new one for the debounce interval, only `input_report_key` from the work handler.

**Key mapping.** The `KEY_*` codes are *logical* — `KEY_ENTER` is the same value regardless of whether the user's keymap is US QWERTY or Dvorak. The user-space keymap translates `KEY_*` to characters. For embedded devices with only a few buttons, you pick meaningful `KEY_*` codes:

- `KEY_VOLUMEUP` / `KEY_VOLUMEDOWN` for media buttons.
- `KEY_POWER` for the power button (the kernel and systemd both recognise this).
- `KEY_HOME`, `KEY_BACK`, `KEY_MENU` for navigation.
- `KEY_WAKEUP` for a wakeup-from-suspend button.

The full list is in `include/uapi/linux/input-event-codes.h`. Pick a code that matches the *role* of the button; user-space will know what to do with it.

## 45.6  Absolute axes — touchscreens and joysticks

For a touchscreen or joystick, you have *coordinates*, not key presses. Declare `EV_ABS` capabilities and report values:

```c
input_set_abs_params(input, ABS_X, 0, 4095, 0, 0);
input_set_abs_params(input, ABS_Y, 0, 4095, 0, 0);
input_set_abs_params(input, ABS_PRESSURE, 0, 255, 0, 0);

/* In the IRQ/work handler when a sample arrives: */
input_report_abs(input, ABS_X, x_coord);
input_report_abs(input, ABS_Y, y_coord);
input_report_abs(input, ABS_PRESSURE, pressure);
input_report_key(input, BTN_TOUCH, 1);
input_sync(input);
```

`input_set_abs_params(dev, code, min, max, fuzz, flat)` — `min/max` is the valid range, `fuzz` is the noise floor (changes ≤ fuzz are suppressed), `flat` is the center deadzone for joysticks.

For **multi-touch**, the protocol is more involved — the MT-B (slot-based) protocol uses `ABS_MT_SLOT` + per-finger `ABS_MT_POSITION_X/Y`. We'll cover that in Ch 55G (GT911 multi-touch driver).

## 45.7  Polled vs interrupt-driven

Some input devices don't have IRQs — accelerometers configured for continuous mode, for instance, or a button on a slow I²C expander where IRQ wiring isn't practical. The `input_polled_dev` framework (now subsumed into the regular `input_dev` via `input_setup_polling`) polls a device at a fixed rate:

```c
input_setup_polling(input, my_poll_callback);
input_set_poll_interval(input, 20);   /* 20 ms = 50 Hz */
input_register_device(input);
```

The core calls `my_poll_callback(input)` every 20 ms. Inside, sample the hardware, `input_report_*`, `input_sync`. No IRQ wiring needed.

## 45.8  User-space — evdev

`/dev/input/event*` is the chardev that streams `struct input_event` records to user-space:

```c
struct input_event {
    struct timeval time;
    __u16 type;
    __u16 code;
    __s32 value;
};
```

Read one record per event. The most common tool is `evtest` (interactive) for debugging; for production, applications either use `libevdev` (a thin wrapper) or higher-level libraries:

- **`libinput`** — used by Wayland and modern X11; handles gesture recognition, palm rejection, tap-to-click, etc.
- **`libevdev`** — minimal wrapper for reading raw events.
- **`/dev/input/eventN` directly** — fine for embedded with one app.

For a quick test from shell:

```sh
$ sudo evtest /dev/input/event2     # interactive
$ sudo cat /dev/input/event2 | hexdump -C
```

## 45.9  Lab

1. **Build and load the button-input driver.** Verify `evtest` shows `KEY_ENTER` events.
2. **Add a second button** with `KEY_VOLUMEUP`. Update DT to use two `button-gpios`, modify driver to allocate one `input_dev` with both keys (or two devices — the kernel allows both).
3. **Add debounce.** Schedule a `delayed_work` from the IRQ handler with a 30 ms delay; only report the event from the work-handler.
4. **Compare to `gpio-keys`.** Drop your driver, configure DT with `compatible = "gpio-keys"` and `linux,code = <KEY_ENTER>;`. Confirm identical behavior. Look at `drivers/input/keyboard/gpio_keys.c` — note how much more it handles (autorepeat, wakeup, runtime PM).
5. **Touchscreen simulator.** Adapt your driver to emit `ABS_X` / `ABS_Y` / `BTN_TOUCH` events with random values once per second. Verify `evtest` shows touch events. This is the foundation for a real touchscreen driver (Ch 55G).
6. **Power-button integration.** Reconfigure your button to emit `KEY_POWER`. With systemd, a long press should trigger a graceful shutdown.

## 45.10  Pitfalls

- **Forgetting `input_sync`.** Events are buffered until `SYN_REPORT`; without it, user-space never sees them. After any group of `input_report_*` calls, call `input_sync`.
- **Reporting an unsupported event.** If you `input_report_key(input, KEY_ENTER, 1)` but didn't `input_set_capability(..., EV_KEY, KEY_ENTER)`, the event is silently dropped. Always declare capabilities first.
- **Not using `devm_input_allocate_device`.** Forgetting `input_free_device` in error paths leaks the device. `devm_` handles it.
- **Calling `input_register_device` before setting capabilities.** Capabilities must be set *before* register. Order: alloc → set_capability → register.
- **Mixing `input_allocate_device` with separate `input_register_device`.** Both can fail, at different points. Use standard `goto` cleanup, or just use `devm_input_allocate_device` to avoid the problem.
- **Confusing absolute and relative axes.** Mice use `EV_REL` (delta motion); touchscreens use `EV_ABS` (absolute position). Mixing them gives weird user-space behavior.
- **Multi-touch with single-touch protocol.** Don't try to emit `ABS_X` for multiple fingers — that's not how it works. Use the MT-B slot protocol (Ch 55G).
- **Repeating events that haven't actually changed.** The core does *not* dedupe; every `input_report_key(..., 1)` followed by `input_sync` is one event. Polling a held button without state-tracking spams the queue.
- **IRQ flag `IRQF_TRIGGER_FALLING` without `IRQF_TRIGGER_RISING`** — you only get press events, not release. For a press/release-capable button, request *both* edges (`IRQF_TRIGGER_RISING | IRQF_TRIGGER_FALLING`).

## 45.11  Going deeper

- **`Documentation/input/`** — the input subsystem's full documentation. Read `input.rst`, `event-codes.rst`, `multi-touch-protocol.rst`.
- **`include/uapi/linux/input-event-codes.h`** — the canonical list of `EV_*`, `KEY_*`, `ABS_*`, etc.
- **`drivers/input/keyboard/gpio_keys.c`** — the in-tree gpio-keys driver. Read it. ~600 lines and covers debounce, wakeup, autorepeat, runtime PM, polling — every feature you'd add to a production button driver.
- **`drivers/input/evdev.c`** — the evdev "handler" that exposes input events as `/dev/input/eventN`.
- **`libevdev` source** (freedesktop.org) — for high-level user-space input access.
- **`Documentation/input/input.rst`** — overview of the input architecture, including the handler/handle/dev triangle.

> Next chapter: **Chapter 46 — I²C drivers.** With GPIO and input behind us, we move to a real bus: the i.MX6ULL's I²C controllers, the `i2c_client` / `i2c_driver` model, and how a single I²C bus accommodates a half-dozen sensors at different addresses.
