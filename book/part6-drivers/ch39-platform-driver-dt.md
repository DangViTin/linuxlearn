---
chapter: 39
title: Platform drivers + device tree
part: VI — Driver development
estimated_pages: 22
status: draft
---

# Chapter 39 — Platform drivers + device tree

> **What:** the `platform_driver` model — the canonical way Linux describes *on-SoC* peripherals (UART, I²C controllers, GPIO blocks, PWM, ADC, all the things memory-mapped into the SoC's address space). A platform driver registers with the kernel saying "I drive devices that match `compatible = "vendor,part"`"; the kernel walks the device tree, finds matching nodes, and invokes the driver's `probe()` once per match.
> **Why:** the kernel doesn't probe address ranges blindly looking for hardware (that's how PC BIOSes work, and it doesn't scale to SoCs with no buses to enumerate). It needs to be **told** what devices exist and where their registers live — that's exactly what the device tree does. The `platform_driver` API is the kernel-side half of the DT contract: you describe the driver, the DT describes the device, the kernel matches them.
> **Focus:** **driver and device are separate**. The driver is a `.ko` (or built-in code) that knows *how* to talk to a hardware block. The device is a DT node that says *where the block is* (registers, IRQs, clocks, pins). The bus (platform bus, here) matches them by `compatible` string. Once this trinity clicks, every subsystem driver in the kernel looks the same.

## 39.1  Why "platform" exists

You've already seen platform devices in passing. Open any imx6ull DT and you see things like:

```dts
gpio1: gpio@209c000 {
    compatible = "fsl,imx6ul-gpio", "fsl,imx35-gpio";
    reg = <0x209c000 0x4000>;
    interrupts = <0 66 IRQ_TYPE_LEVEL_HIGH>, <0 67 IRQ_TYPE_LEVEL_HIGH>;
    clocks = <&clks IMX6UL_CLK_GPIO1>;
    gpio-controller;
    #gpio-cells = <2>;
    interrupt-controller;
    #interrupt-cells = <2>;
};
```

This is a **platform device**: a hardware block on the SoC, described by a DT node, with no enumerable bus connecting it (compared to USB, PCI, or even I²C, where a discovery protocol enumerates children). The CPU just has memory-mapped registers at a fixed physical address and an IRQ line connected to the GIC.

The **platform bus** in the kernel is a virtual abstraction over this "no bus" case. It exists solely to give the driver/device model something to attach to. When the kernel parses the DT at boot, every node whose parent has no `compatible` for a real bus (i.e., everything directly under the SoC node) becomes a platform device. When you `insmod` a `platform_driver`, the platform bus walks the device list looking for matches.

There are two kinds of buses in Linux:

1. **Enumerable** — USB, PCI, I²C (devices can be discovered by polling). The bus driver enumerates; child devices appear automatically.
2. **Non-enumerable** — platform, plus a few others. Devices must be described externally (DT, ACPI, board file). The platform bus is the catch-all for SoC peripherals.

Almost everything on an i.MX6ULL is platform: GPIO blocks, UARTs, I²C controllers (the controllers themselves; the *devices on them* are I²C-bus children), SPI controllers, PWM, ADC, timers, FlexCAN, Ethernet MAC, USB OTG controllers, LCDIF, eCSPI, etc.

## 39.2  The pieces

To write a platform driver for an on-SoC peripheral, you need three things:

1. **A device-tree node** describing the hardware (`compatible`, `reg`, `interrupts`, `clocks`, pinctrl). This usually exists already — the SoC's vendor wrote it.
2. **A `platform_driver` struct** in your code that declares which `compatible` strings it handles and points to your `probe` / `remove` functions.
3. **A `probe()` function** that does what `module_init` did before: claim resources, request IRQs, register the chardev/class, set up internal state. Returns 0 on success, negative `errno` on failure.

When the kernel finds a DT node whose `compatible` matches your driver, the bus calls your `probe(struct platform_device *pdev)`. Your `probe` finds resources via `pdev->dev.of_node` (the DT node) or via `platform_get_resource()`. When the driver is unloaded — or the device is removed (rare on SoC peripherals; common on hotpluggable hardware) — `remove()` runs.

## 39.3  A minimal example: a "demo" platform driver

Let's write the world's simplest platform driver — one that just logs when it probes a device, reads `reg` from the DT, and ioremaps the registers.

### Step 1 — add a DT node

In a DTS overlay (or directly in your board's DTS), add:

```dts
&{/} {
    demo0: demo@1000 {
        compatible = "linuxlearn,demo";
        reg = <0x00001000 0x100>;
        status = "okay";
    };
};
```

The address `0x1000` is fake — there's no real hardware here. For a real driver you'd use the actual peripheral's base. For demo purposes we'll ioremap unused-but-readable memory.

Rebuild the DTB and reboot. After boot:

```
[root@pa-mini:~]# ls /sys/firmware/devicetree/base/demo@1000/
compatible  name  reg  status
[root@pa-mini:~]# cat /sys/firmware/devicetree/base/demo@1000/compatible
linuxlearn,demo
```

The DT node exists, but no driver has claimed it — `dmesg` shows nothing yet because no `platform_driver` matches.

### Step 2 — the driver

`demo.c`:

```c
#include <linux/init.h>
#include <linux/module.h>
#include <linux/platform_device.h>
#include <linux/of.h>
#include <linux/io.h>

struct demo_priv {
    void __iomem *base;
    int irq;
};

static int demo_probe(struct platform_device *pdev)
{
    struct demo_priv *priv;
    struct resource *res;

    dev_info(&pdev->dev, "probe: matched compatible '%s'\n",
             pdev->dev.of_node->name);

    priv = devm_kzalloc(&pdev->dev, sizeof(*priv), GFP_KERNEL);
    if (!priv)
        return -ENOMEM;

    res = platform_get_resource(pdev, IORESOURCE_MEM, 0);
    if (!res)
        return dev_err_probe(&pdev->dev, -EINVAL, "no memory resource\n");

    priv->base = devm_ioremap_resource(&pdev->dev, res);
    if (IS_ERR(priv->base))
        return PTR_ERR(priv->base);

    dev_info(&pdev->dev, "registers at %pa, mapped to %p\n",
             &res->start, priv->base);

    platform_set_drvdata(pdev, priv);
    return 0;
}

static int demo_remove(struct platform_device *pdev)
{
    struct demo_priv *priv = platform_get_drvdata(pdev);
    dev_info(&pdev->dev, "remove\n");
    (void)priv;   /* nothing to free; devm_* handles all */
    return 0;
}

static const struct of_device_id demo_of_match[] = {
    { .compatible = "linuxlearn,demo" },
    { /* sentinel */ }
};
MODULE_DEVICE_TABLE(of, demo_of_match);

static struct platform_driver demo_driver = {
    .driver = {
        .name           = "demo",
        .of_match_table = demo_of_match,
    },
    .probe  = demo_probe,
    .remove = demo_remove,
};

module_platform_driver(demo_driver);

MODULE_LICENSE("GPL");
MODULE_DESCRIPTION("Demo platform driver");
```

That's the whole template. Let's pull apart the four interesting pieces.

### Piece A: `of_match_table` + `MODULE_DEVICE_TABLE`

```c
static const struct of_device_id demo_of_match[] = {
    { .compatible = "linuxlearn,demo" },
    { /* sentinel */ }
};
MODULE_DEVICE_TABLE(of, demo_of_match);
```

The `of_device_id` table lists every `compatible` string this driver handles. The kernel's DT matcher compares each entry against every DT node's `compatible` (which may be a list; first match wins).

`MODULE_DEVICE_TABLE(of, demo_of_match)` exposes the table to `depmod`. When the user runs `modprobe`, `depmod` knows which `.ko` to autoload for a given `compatible` string. This is how the kernel can auto-load drivers at boot: parse DT → find unmatched compatible → search through modules' DEVICE_TABLE → modprobe the right one.

If you omit `MODULE_DEVICE_TABLE`, your driver still works when manually `insmod`'d, but **auto-loading from DT will silently fail**. Always include it.

### Piece B: `platform_driver` + `module_platform_driver`

```c
static struct platform_driver demo_driver = {
    .driver = {
        .name           = "demo",
        .of_match_table = demo_of_match,
    },
    .probe  = demo_probe,
    .remove = demo_remove,
};

module_platform_driver(demo_driver);
```

The `platform_driver` struct ties the matching table to your callbacks. The `module_platform_driver()` macro expands to a `module_init` + `module_exit` pair that calls `platform_driver_register` / `platform_driver_unregister`. **You no longer write `module_init` / `module_exit` by hand** — the macro does it. (Look it up; it's literally a one-liner each way.)

### Piece C: `devm_*` (managed) allocations

```c
priv = devm_kzalloc(&pdev->dev, sizeof(*priv), GFP_KERNEL);
...
priv->base = devm_ioremap_resource(&pdev->dev, res);
```

The `devm_` prefix is a kernel pattern that means **device-managed**: resources allocated this way are *automatically freed when the device goes away*. No `kfree`, no `iounmap`, no `free_irq` in your `remove()` function — it's all handled.

This is the biggest stylistic win in modern kernel code. Compare:

```c
/* Without devm_ */
priv = kzalloc(sizeof(*priv), GFP_KERNEL);
if (!priv) return -ENOMEM;
priv->base = ioremap(res->start, resource_size(res));
if (!priv->base) { kfree(priv); return -ENOMEM; }
priv->buffer = kmalloc(4096, GFP_KERNEL);
if (!priv->buffer) { iounmap(priv->base); kfree(priv); return -ENOMEM; }
...
/* And in remove(): */
kfree(priv->buffer);
iounmap(priv->base);
kfree(priv);
```

vs.

```c
/* With devm_ */
priv = devm_kzalloc(&pdev->dev, sizeof(*priv), GFP_KERNEL);
if (!priv) return -ENOMEM;
priv->base = devm_ioremap_resource(&pdev->dev, res);
if (IS_ERR(priv->base)) return PTR_ERR(priv->base);
priv->buffer = devm_kmalloc(&pdev->dev, 4096, GFP_KERNEL);
if (!priv->buffer) return -ENOMEM;
...
/* remove() can be empty (or omitted entirely if there's nothing to do). */
```

Every common resource has a `devm_` variant: `devm_kmalloc`, `devm_kzalloc`, `devm_kasprintf`, `devm_ioremap_resource`, `devm_request_irq`, `devm_clk_get`, `devm_regulator_get`, `devm_reset_control_get`, etc. Use them. The error-path goto cascade from Ch 37 mostly disappears.

### Piece D: `dev_err_probe`

```c
return dev_err_probe(&pdev->dev, -EINVAL, "no memory resource\n");
```

`dev_err_probe` is two functions in one: it logs the message **and** returns the errno. If the errno is `-EPROBE_DEFER` (a special "try again later" return), it logs at debug level instead of error to avoid spam (because probe deferrals are usually transient). For all other errno values, it logs at error level. Always prefer it to `dev_err(...) + return -EINVAL;`.

## 39.4  Building and loading

`Makefile` (same as Ch 36's):

```makefile
obj-m += demo.o
KDIR ?= /home/$(USER)/linux-imx6ull/build
all:
	$(MAKE) -C $(KDIR) ARCH=arm CROSS_COMPILE=arm-linux-gnueabihf- M=$(PWD) modules
```

On the target:

```
[root@pa-mini:~]# insmod demo.ko
[root@pa-mini:~]# dmesg | tail -2
demo demo@1000: probe: matched compatible 'demo'
demo demo@1000: registers at 0x00001000, mapped to (ptrval)

[root@pa-mini:~]# rmmod demo
[root@pa-mini:~]# dmesg | tail -1
demo demo@1000: remove
```

The probe fired automatically — no manual `mknod` or device registration. The DT node was there; the driver matched it; `probe()` ran with all the right context.

### Verify in sysfs

```
[root@pa-mini:~]# ls /sys/bus/platform/drivers/demo/
bind  module  uevent  unbind  demo@1000  

[root@pa-mini:~]# ls /sys/bus/platform/devices/demo@1000/
driver  driver_override  modalias  of_node  power  subsystem  uevent

[root@pa-mini:~]# readlink /sys/bus/platform/devices/demo@1000/driver
../../../../bus/platform/drivers/demo

[root@pa-mini:~]# cat /sys/bus/platform/devices/demo@1000/modalias
of:Ndemo@1000T(null)Clinuxlearn,demo
```

`/sys/bus/platform/drivers/demo/` lists devices currently bound to this driver (`demo@1000` here). `/sys/bus/platform/devices/demo@1000/` shows the device, its driver, and a `modalias` that `depmod` uses to autoload the right module.

## 39.5  Manual bind / unbind

Sysfs lets you unbind a device from its driver and rebind later, without unloading the module:

```
[root@pa-mini:~]# echo demo@1000 > /sys/bus/platform/drivers/demo/unbind
[root@pa-mini:~]# dmesg | tail -1
demo demo@1000: remove

[root@pa-mini:~]# echo demo@1000 > /sys/bus/platform/drivers/demo/bind
[root@pa-mini:~]# dmesg | tail -1
demo demo@1000: probe: matched compatible 'demo'
```

Useful in development: re-probe a device after fixing a hardware glitch, without rebooting. Also useful in production for power-saving (unbind unused hardware to drop its clocks).

## 39.6  Getting more from the DT

`platform_get_resource` returns one resource (`reg` or `interrupt` etc). For richer DT data, use the `of_*` API directly:

```c
/* Read a u32 property */
u32 val;
if (of_property_read_u32(pdev->dev.of_node, "linuxlearn,speed-hz", &val))
    val = 100000;   /* default */

/* Read a string */
const char *mode;
if (of_property_read_string(pdev->dev.of_node, "linuxlearn,mode", &mode))
    mode = "polled";

/* A GPIO descriptor */
struct gpio_desc *reset_gpio;
reset_gpio = devm_gpiod_get(&pdev->dev, "reset", GPIOD_OUT_LOW);
if (IS_ERR(reset_gpio))
    return PTR_ERR(reset_gpio);

/* A clock */
struct clk *clk;
clk = devm_clk_get(&pdev->dev, "main");
if (IS_ERR(clk))
    return PTR_ERR(clk);
clk_prepare_enable(clk);
```

Notice these are all subsystem APIs (`of_*`, `gpiod_*`, `clk_*`), not raw DT-parsing code. The DT layer is the data layer; subsystems above it provide *typed* access. We'll see clocks in Ch 50, GPIOs in Ch 44, etc.

## 39.7  Two probe-related patterns to know

### Pattern: `probe_defer` for ordering

A driver's `probe()` may depend on something that isn't ready yet — e.g., the PMIC regulator the driver wants hasn't probed itself. The driver returns `-EPROBE_DEFER`:

```c
priv->vcc = devm_regulator_get(&pdev->dev, "vcc");
if (IS_ERR(priv->vcc)) {
    if (PTR_ERR(priv->vcc) == -EPROBE_DEFER)
        return -EPROBE_DEFER;
    return dev_err_probe(&pdev->dev, PTR_ERR(priv->vcc), "no vcc regulator\n");
}
```

The kernel notes the deferred device and retries it after every other probe attempt, until all probes have stabilised. This means you don't have to manage init order manually across drivers; the kernel does it for you.

`dev_err_probe` handles this for you: if the errno is `-EPROBE_DEFER`, it logs quietly. So a one-line `return dev_err_probe(&pdev->dev, PTR_ERR(priv->vcc), "no vcc\n");` is fine — `EPROBE_DEFER` and real errors both flow through it.

### Pattern: shutdown vs remove

`remove()` is called when the driver is unloaded or the device is unbound.
`shutdown()` is called during system shutdown/reboot — only on devices that need to be quiesced (DMA stopped, watchdog disabled, etc.). For most drivers `remove()` suffices; for drivers that own DMA engines or watchdogs, add a `.shutdown = my_shutdown`. It runs in atomic context — keep it short.

## 39.8  Lab

1. **Write a demo platform driver** matching `compatible = "linuxlearn,demo"`. Add a DT node for it via overlay or by editing your board DTS. Verify `probe` runs at load and `remove` runs at unload.
2. **Try `EPROBE_DEFER`.** Add an unrequited dependency:
   ```c
   if (some_condition_initially_false)
       return -EPROBE_DEFER;
   ```
   Watch the kernel re-probe periodically. Set the condition true (via `module_param` from a sysfs file) and watch probe succeed.
3. **Read custom DT properties.** Add `linuxlearn,speed-hz = <50000>;` to your DT node and read it with `of_property_read_u32`. Print the value in probe.
4. **Manual bind/unbind.** From a shell, unbind your device; observe `remove` log. Rebind; observe `probe`. No `insmod`/`rmmod` involved.
5. **Multiple instances.** Add a second DT node, `demo@2000`, also with `compatible = "linuxlearn,demo"`. Verify `probe` is called twice, once per node. Each gets its own `platform_device`.
6. **Inspect modalias and depmod.** Run `depmod -a` on the build host, then check `/lib/modules/.../modules.alias` for an entry pointing your DT compatible to `demo.ko`. Verify `modprobe demo` does the right thing on the target.

## 39.9  Pitfalls

- **DT node has wrong `status`.** A node with `status = "disabled"` is skipped by the platform bus. Many vendor DTs ship peripherals as `disabled`; you must overlay `status = "okay";` to activate.
- **`compatible` typo.** A typo in either the DT or the driver's `of_match_table` is silent: no probe, no error message. Always cross-check both spellings.
- **Forgetting `MODULE_DEVICE_TABLE`.** Driver works manually but won't auto-load. Symptom: must `modprobe demo` by hand at every boot. Fix is a one-liner.
- **Calling `kfree` on a `devm_kmalloc` pointer.** Double-free. Symptom: memory corruption that may take hours to manifest. Pick one allocator and stay consistent. If you `devm_kmalloc`, never `kfree` it; if you `kmalloc`, never let it slip past `remove` without `kfree`.
- **Calling sleeping functions in atomic context.** `dev_err_probe` is fine. `devm_kmalloc(... GFP_KERNEL)` is fine in probe. But if `probe` itself is called from atomic context (rare for platform drivers but real for some buses), use `GFP_ATOMIC`. Misuse triggers `BUG: sleeping function called from invalid context` at runtime.
- **Driver and device names with hyphens vs underscores.** Some subsystems are picky. The convention: driver `.name` and `compatible` use **hyphens** ("snps,dwc-mshc"). Avoid underscores; the kernel won't reject them but tools may treat them differently.
- **Trying to mix `platform_driver` and direct chardev registration.** It works — many real drivers do both: probe registers the chardev — but the **order matters**. Always do chardev/class/device_create *inside* `probe`, not at module load time. Otherwise a probe failure leaves a partially-registered chardev with no backing.

## 39.10  Going deeper

- **`Documentation/driver-api/driver-model/platform.rst`** — the platform bus's official documentation.
- **`Documentation/devicetree/bindings/`** — the YAML bindings (Ch 27A); the source-of-truth for what each `compatible` expects.
- **`drivers/gpio/gpio-mxc.c`** — i.MX GPIO controller driver. A small, clean platform driver. Read it.
- **`Documentation/driver-api/devres.rst`** — full list of `devm_*` helpers.
- **`MAINTAINERS`** — when your driver is upstream-quality, this is where you find which subsystem maintainer it belongs to.

---

> **End of foundation chapters (Ch 36–39).** With LKM, chardev, hot-plug, and platform-driver patterns understood, you have the skeleton every subsequent driver in Part VI hangs off. The next chapters (40–43) add the *behaviors* that real drivers need: the misc-device shortcut for trivial chardevs, concurrency primitives, sleeping/polling, and interrupts.

> Next chapter: **Chapter 40 — The misc framework.** For dead-simple chardevs that don't deserve their own class, `miscdevice` is a one-call shortcut that handles dev_t allocation, class registration, and device-node creation in one shot.
