---
chapter: 44
title: GPIO subsystem + pinctrl
part: VI — Driver development
estimated_pages: 22
status: draft
---

# Chapter 44 — GPIO subsystem + pinctrl

> **What:** the two halves of Linux's pin handling — **pinctrl** (which decides what *function* a pin has — GPIO vs UART vs I²C, plus electrical properties: drive strength, pull-up, slew rate) and **gpiod** (the modern descriptor-based API for the pins that *do* end up as GPIOs: direction and value). By the end you can request a GPIO from DT, configure pull-up, drive it, watch it for IRQs — all without ever touching an MMIO register.
> **GPIO** - General-Purpose Input/Output, a pin controlled as a digital input, output, or interrupt source.
> **MMIO** - memory-mapped I/O, where software accesses peripheral registers through normal load and store instructions.
>
> **Why:** every real driver eventually wants a GPIO. A reset pin on a peripheral chip. A power-enable on a regulator. A `data-ready` line from a sensor. Hard-coding the MMIO writes (as we did in Part II bare-metal) couples the driver to one specific SoC. The kernel's `gpiod_*` API gives you a portable, DT-described abstraction: "this driver wants the GPIO whose DT property is `reset-gpios`," and the gpiod subsystem figures out which bank, which pin, and which register to touch.
>
> **Focus:** **the descriptor abstraction**. `struct gpio_desc *` hides the bank, the pin offset, the polarity (`ACTIVE_LOW`), and the SoC-specific register layout behind one opaque handle. Once you accept that — and stop thinking in "GPIO numbers" — every GPIO-using driver in Linux looks the same.


## 44.1  The two-step pin model

Almost every pin on an SoC is *multiplexed*: it can act as one of several functions. The i.MX6ULL's `UART1_RTS_B` ball, for example, can be:

| Mux value | Function |
|-----------|----------|
| 0 | UART1 RTS (default — the pin's name) |
| 1 | ENET1 transmit error |
| 2 | USDHC1 card-detect |
| 3 | CSI camera data bit 5 |
| 4 | Ethernet 1588 event output |
| **5** | **GPIO1 IO19** |
| 8 | USDHC2 card-detect |

Picking *which* function the pin performs is **pin multiplexing** (pinmux). Setting drive strength, pull-up, slew rate, etc. is **pin configuration** (pinconf). Together they are managed by the **pinctrl subsystem**.

Only *after* you've muxed a pin as GPIO does it become a GPIO. Then a separate API — the **gpiod** subsystem — handles its direction (input/output) and value (high/low).

The two-step model is fixed across Linux:

```
   DT says:        pinctrl-0 = <&pinctrl_my_button>;
                   button-gpios = <&gpio1 19 GPIO_ACTIVE_LOW>;
                                  └──┬──┘ └┬┘ └──────┬───────┘
                                     │     │     polarity
                                     │     pin within bank
                                     bank phandle

   step 1:  pinctrl sets the iomux register so pin GPIO1_IO19 is in GPIO mode
            (mux value 5; conf_reg gets 0x17059: pull-up, drive strength, etc.)

   step 2:  driver calls devm_gpiod_get(dev, "button", GPIOD_IN);
            gpiod subsystem looks up the descriptor, configures direction
```

If you forget step 1 — leave the pin in its default UART function — step 2 reads garbage and your driver thinks the button is always pressed. The two are coupled but managed separately. Most boards do step 1 once in DT (via a `pinctrl-0` reference), then drivers ask for descriptors as needed.

## 44.2  pinctrl in the device tree

The pinctrl entries live under the SoC's `iomuxc` node. For i.MX6ULL:

```dts
&iomuxc {
    pinctrl-names = "default";
    pinctrl-0 = <&pinctrl_hog>;

    pinctrl_hog: hoggrp {
        fsl,pins = <
            MX6UL_PAD_UART1_RTS_B__GPIO1_IO19  0x17059
            MX6UL_PAD_GPIO1_IO09__GPIO1_IO09   0x17059
        >;
    };

    pinctrl_button: buttongrp {
        fsl,pins = <
            MX6UL_PAD_UART1_RTS_B__GPIO1_IO19  0x17059
        >;
    };
};
```

Two things going on:

**Pin groups.** `pinctrl_hog` and `pinctrl_button` are pin **groups**. A group is a named bundle of pin configurations that can be applied as a unit. Drivers reference groups by name.

**The hog.** A `hog` is special: pinctrl applies it at boot time, not at any driver's probe. Pins owned by the core (e.g., a `card-detect` line that nothing else will claim) go in the hog. Pins owned by a specific peripheral go in that peripheral's group, which the peripheral's driver activates.

**The macro.** `MX6UL_PAD_UART1_RTS_B__GPIO1_IO19` is defined in `arch/arm/boot/dts/imx6ul-pinfunc.h`. It expands to five integers (`mux_reg, conf_reg, input_reg, mux_mode, input_val`). The trailing `0x17059` is the **electrical configuration** (the conf_reg value): pull-up enabled, fast speed, drive strength = 40 Ω, etc. The format of that 32-bit word is documented in the i.MX6ULL reference manual under `IOMUXC_SW_PAD_CTL_PAD_*`.

You don't compute these by hand for every pin. NXP publishes a tool called **Pins Tool for i.MX** with a GUI for picking mux and electrical settings. Or you read the macros that other in-tree boards have already used (`imx6ul-evk.dts`, `imx6ull-14x14-evk.dts`) and copy the ones that match your hardware.

### Multiple states

A peripheral can declare *multiple* pinctrl states — typically `default` (active) and `sleep` (low-power):

```dts
my_uart {
    pinctrl-names = "default", "sleep";
    pinctrl-0 = <&pinctrl_uart_active>;
    pinctrl-1 = <&pinctrl_uart_sleep>;
};
```

The driver switches states via `pinctrl_pm_select_default_state(dev)` and `pinctrl_pm_select_sleep_state(dev)`. The sleep state typically muxes the pins to GPIO with pull-down enabled, so the peripheral's input pins don't float when the peripheral itself is powered off. We'll return to this in Ch 51B (power management).

## 44.3  GPIO in the device tree

A driver that wants a GPIO declares it in its DT node:

```dts
my_device {
    compatible = "linuxlearn,my-device";
    reset-gpios = <&gpio5 11 GPIO_ACTIVE_LOW>;
    button-gpios = <&gpio1 19 GPIO_ACTIVE_LOW>;
    led-gpios = <&gpio4 14 GPIO_ACTIVE_HIGH>;
};
```

Each entry is three cells:

1. **The bank phandle** (`&gpio5`) — names which GPIO controller bank the pin lives on. i.MX6ULL has 5 banks (`gpio1`–`gpio5`). Most are 32-pin. **`gpio5` exposes only 12 pins (0–11)** because of package pin-count, and `gpio4` is partial on some packages too. Check the IOMUX table before assuming a pin number is wired out.
MCU bridge: Think of IOMUX like STM32 alternate-function selection, but with separate pad electrical settings and board-level ownership by Device Tree.
**IOMUX** - the pin multiplexer that decides which peripheral function appears on each package pin.
2. **The pin number** within the bank (0–31).
3. **Flags** — usually `GPIO_ACTIVE_HIGH` or `GPIO_ACTIVE_LOW`. The polarity is **part of the abstraction**. Code below operates on logical "asserted" / "deasserted". physical level is hidden.

The property name pattern is `<purpose>-gpios`. The kernel strips the `-gpios` suffix to form the *connection ID* drivers use to fetch the descriptor.

## 44.4  The gpiod descriptor API

`#include <linux/gpio/consumer.h>`

Fetching a GPIO:

```c
struct gpio_desc *reset;

reset = devm_gpiod_get(&pdev->dev, "reset", GPIOD_OUT_HIGH);
if (IS_ERR(reset))
    return PTR_ERR(reset);
```

`devm_gpiod_get(dev, "reset", GPIOD_OUT_HIGH)` says: "look up the `reset-gpios` property on this device's DT node, claim the pin, set it as an output, and initialise it to **asserted** (`GPIOD_OUT_HIGH`) or **deasserted** (`GPIOD_OUT_LOW`)." Because the DT declared `GPIO_ACTIVE_LOW`, "asserted" means physical low — the API hides that.

Flag options:
- `GPIOD_ASIS` — don't set direction. just acquire the descriptor.
- `GPIOD_IN` — input.
- `GPIOD_OUT_LOW` — output, initial value deasserted.
- `GPIOD_OUT_HIGH` — output, initial value asserted.

The `devm_` prefix gives us automatic release on driver-unbind, same as Ch 39.

Reading and writing:

```c
int val = gpiod_get_value(reset);     /* returns 0 or 1, logical */
gpiod_set_value(reset, 1);             /* asserts (physical low if ACTIVE_LOW) */

/* From sleeping context only (these may sleep on I²C-based GPIO expanders): */
val = gpiod_get_value_cansleep(reset);
gpiod_set_value_cansleep(reset, 0);
```

Two variants per operation. The plain version is safe to call from atomic context (IRQ handler, spinlock held). The `_cansleep` version is required when the underlying GPIO chip is on an I²C or SPI bus (where the bus transaction itself may sleep). **Use `_cansleep` in process context** — it works for both bus-backed and direct GPIOs.
MCU bridge: Think of an IRQ like an EXTI/NVIC interrupt path, except Linux splits the hard interrupt from deferred work and must share lines across drivers.
**IRQ** - interrupt request, the signal path that tells the CPU or interrupt controller that hardware needs service.

Direction change at runtime:

```c
gpiod_direction_input(desc);
gpiod_direction_output(desc, 1);   /* output, value = asserted */
```

Plus the helpers we saw in Ch 43:

```c
int irq = gpiod_to_irq(desc);
err = devm_request_threaded_irq(dev, irq, NULL, my_thread,
                                IRQF_TRIGGER_RISING | IRQF_ONESHOT,
                                "my-button", priv);
```

## 44.5  A complete example: button + LED platform driver

DT:

```dts
my_blinker {
    compatible = "linuxlearn,blinker";
    button-gpios = <&gpio1 19 GPIO_ACTIVE_LOW>;
    led-gpios = <&gpio4 14 GPIO_ACTIVE_HIGH>;
    status = "okay";
};
```

The pinctrl side (in the iomuxc block):

```dts
&iomuxc {
    pinctrl_blinker: blinkergrp {
        fsl,pins = <
            MX6UL_PAD_UART1_RTS_B__GPIO1_IO19  0x17059  /* button: pull-up, schmitt */
            MX6UL_PAD_NAND_CE1_B__GPIO4_IO14   0x10b0   /* LED: drive strength 40Ω */
        >;
    };
};
```

…and the consumer references it:

```dts
my_blinker {
    /* ... */
    pinctrl-names = "default";
    pinctrl-0 = <&pinctrl_blinker>;
};
```

Driver:

```c
#include <linux/init.h>
#include <linux/module.h>
#include <linux/platform_device.h>
#include <linux/gpio/consumer.h>
#include <linux/interrupt.h>

struct blinker {
    struct gpio_desc *button;
    struct gpio_desc *led;
    int irq;
};

static irqreturn_t blinker_thread(int irq, void *dev_id)
{
    struct blinker *b = dev_id;
    int val = gpiod_get_value_cansleep(b->led);
    gpiod_set_value_cansleep(b->led, !val);   /* toggle LED */
    return IRQ_HANDLED;
}

static int blinker_probe(struct platform_device *pdev)
{
    struct blinker *b;
    int err;

    b = devm_kzalloc(&pdev->dev, sizeof(*b), GFP_KERNEL);
    if (!b)
        return -ENOMEM;

    b->led = devm_gpiod_get(&pdev->dev, "led", GPIOD_OUT_LOW);
    if (IS_ERR(b->led))
        return dev_err_probe(&pdev->dev, PTR_ERR(b->led), "no led gpio\n");

    b->button = devm_gpiod_get(&pdev->dev, "button", GPIOD_IN);
    if (IS_ERR(b->button))
        return dev_err_probe(&pdev->dev, PTR_ERR(b->button), "no button gpio\n");

    b->irq = gpiod_to_irq(b->button);
    if (b->irq < 0)
        return dev_err_probe(&pdev->dev, b->irq, "irq lookup failed\n");

    err = devm_request_threaded_irq(&pdev->dev, b->irq, NULL, blinker_thread,
                                     IRQF_TRIGGER_FALLING | IRQF_ONESHOT,
                                     "blinker", b);
    if (err)
        return err;

    platform_set_drvdata(pdev, b);
    dev_info(&pdev->dev, "ready\n");
    return 0;
}

static const struct of_device_id blinker_of_match[] = {
    { .compatible = "linuxlearn,blinker" },
    { }
};
MODULE_DEVICE_TABLE(of, blinker_of_match);

static struct platform_driver blinker_driver = {
    .driver = {
        .name = "linuxlearn-blinker",
        .of_match_table = blinker_of_match,
    },
    .probe = blinker_probe,
};
module_platform_driver(blinker_driver);

MODULE_LICENSE("GPL");
```

Build, load, press the button: the LED toggles. About 90 lines, zero MMIO writes, portable to any SoC with a Linux GPIO driver.

## 44.6  User-space access — libgpiod

For one-off scripting and prototyping, you can drive GPIOs from user-space *without* a kernel driver. The traditional way (`/sys/class/gpio/`) is **deprecated** since 4.8 and gone in some distros — never write new code for it. The current way is the **character-device API** at `/dev/gpiochipN`, accessed via the `libgpiod` library and its CLI tools.

```
[root@pa-mini:~]# gpiodetect
gpiochip0 [209c000.gpio] (32 lines)
gpiochip1 [20a0000.gpio] (32 lines)
gpiochip2 [20a4000.gpio] (32 lines)
gpiochip3 [20a8000.gpio] (32 lines)
gpiochip4 [20ac000.gpio] (24 lines)

[root@pa-mini:~]# gpioinfo gpiochip0
gpiochip0 - 32 lines:
        line   0:      unnamed       unused   input  active-high
        line   1:      unnamed       unused   input  active-high
        ...
        line  19:      unnamed   "blinker"   input  active-low [used]
        ...
```

Reading and writing:

```
# Read pin 19 of bank 1
[root@pa-mini:~]# gpioget gpiochip0 19
1   ← button not pressed (active-low; physical high = logical 1 if asked as inverted)

# Set GPIO4 pin 14 to 1
[root@pa-mini:~]# gpioset gpiochip3 14=1
[root@pa-mini:~]# gpioset gpiochip3 14=0

# Monitor for events
[root@pa-mini:~]# gpiomon --rising-edge gpiochip0 19
event:  RISING EDGE offset: 19 timestamp: [   1234.567890123]
```

`libgpiod` is the same API your driver code uses, but from user-space. Great for board bring-up: confirm a GPIO works at the hardware level before writing a driver around it.

## 44.7  GPIO expanders — when GPIOs come over a bus

What if you need more GPIOs than the SoC has? Solution: a **GPIO expander** chip on I²C or SPI. The MCP23017 (I²C, 16 GPIOs), PCA9555 (I²C, 16 GPIOs), and PCF8575 are common choices.

From the kernel's perspective, an I²C GPIO expander registers itself as a `gpio_chip` just like the SoC banks. Once registered, `gpiochip5` (or whatever number) appears in `/sys/class/gpio/` and the descriptor API works identically. Drivers don't know or care that the GPIO is "remote."

DT:

```dts
&i2c1 {
    mcp23017: gpio@20 {
        compatible = "microchip,mcp23017";
        reg = <0x20>;
        gpio-controller;
        #gpio-cells = <2>;
        interrupt-parent = <&gpio4>;
        interrupts = <14 IRQ_TYPE_LEVEL_LOW>;
    };
};

my_device {
    /* GPIOs come from the expander */
    reset-gpios = <&mcp23017 5 GPIO_ACTIVE_LOW>;
};
```

The driver code is *unchanged* — `devm_gpiod_get(&pdev->dev, "reset", ...)` works the same way. The only difference is that operations like `gpiod_set_value` may now sleep (they trigger an I²C transaction), so you must use `gpiod_set_value_cansleep` when the GPIO might be on an expander. **For portable driver code, always use `_cansleep` in process context.**

## 44.8  Lab

1. **Build and run the button-blinker driver.** Verify it works end-to-end.
2. **Use libgpiod to drive the LED instead.** `gpioset gpiochip3 14=1`. Confirm same outcome.
3. **Monitor button events from user-space.** `gpiomon --falling-edge gpiochip0 19` while pressing the button. Compare latency against your driver's IRQ-handler latency (ftrace).
4. **Add a sleep state.** Define `pinctrl_blinker_sleep` that pulls down the button pin and tristates the LED. In probe, set both states. Add a runtime sysfs attribute to switch states.
**sysfs** - a kernel-generated filesystem under /sys that exposes devices, drivers, and attributes.
5. **Wire a fake GPIO expander.** Add an `mcp23017` node to your DT (even if you don't have the chip — just to verify the binding parses). With the chip absent, the driver will fail to probe. observe `dev_err_probe` deferring and the eventual timeout.
6. **Read pin state without a driver.** Cold-boot, then `gpioinfo` — see which pins are claimed by which drivers. Useful for debugging "is the kernel using this pin I want?"

## 44.9  Pitfalls

- **Forgetting the pinctrl group.** Pin is still in its default mux (for example, UART). `gpiod_get` succeeds — the GPIO controller has no idea the pin is muxed elsewhere. But the GPIO seems "stuck": reads and writes hit the GPIO register, while the IOMUX routes the pin to UART. Always declare a pinctrl group that muxes the pin as GPIO, and reference it from `pinctrl-0`.
- **`GPIO_ACTIVE_LOW` confusion.** The kernel's logical "asserted" hides physical polarity. If you read raw via `/sys/class/gpio/`, you see physical level. If you read via `gpiod_get_value`, you see logical. Match your DT flag to your hardware schematic.
- **Wrong bank phandle.** `<&gpio1 ...>` vs `<&gpio2 ...>` — typo costs you hours. `gpioinfo` is your friend after boot.
- **Calling `gpiod_set_value` (atomic) on an I²C-backed GPIO.** Kernel BUG: "scheduling while atomic." Always use `_cansleep` unless you're 100 % sure the GPIO is direct (and even then, for new code, use `_cansleep` for portability).
- **Hog vs driver-owned pin.** Don't hog a pin that a driver will claim. The driver's `pinctrl_select_state` will fail. Hog only ownerless pins.
- **Using GPIO sysfs.** Old `/sys/class/gpio/export` interface is deprecated. Use `libgpiod` and `gpioset/gpioget/gpiomon` for user-space access. Sysfs may be missing entirely on newer kernels.
- **Pin number arithmetic.** "GPIO1 IO19 = global GPIO number 19" is wrong in some places, right in others. Global numbers are legacy. The descriptor API doesn't care about numbers. just use the DT phandle + pin offset.
- **Forgetting `MODULE_DEVICE_TABLE`.** Driver works manually, doesn't autoload. Easy to miss. always include it.

## 44.10  Going deeper

- **`Documentation/driver-api/pin-control.rst`** — the pinctrl subsystem's official architecture document.
- **`Documentation/driver-api/gpio/`** — gpiod consumer and provider APIs.
- **`Documentation/devicetree/bindings/pinctrl/fsl,imx-pinctrl.txt`** — the i.MX-specific pinctrl binding.
- **`arch/arm/boot/dts/imx6ul-pinfunc.h`** — all `MX6UL_PAD_*` macros defined here. Skim for an hour and you'll start to recognise the patterns.
- **`drivers/pinctrl/freescale/pinctrl-imx6ul.c`** — the i.MX6UL pinctrl driver (and yes, it works for 6ULL too).
- **`drivers/gpio/gpio-mxc.c`** — the i.MX GPIO controller driver. Demuxes 32 pins per bank into per-pin virqs, handles the chained IRQ.
- **`tools/gpio/`** — small helper utilities. useful for one-off scripts.
- **`libgpiod` source on kernel.org** — the canonical user-space API.

> Next chapter: **Chapter 45 — Input subsystem.** With GPIOs and IRQs in hand, the natural next step is "turn a button into a key-press event the OS recognises." That's the `input_dev` framework, and `gpio-keys` is its perfect canonical example.
