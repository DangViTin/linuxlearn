---
chapter: 40
title: The misc framework
part: VI - Driver development
estimated_pages: 10
status: draft
---

# Chapter 40: The misc framework

> **What:** `miscdevice`, a one-call shortcut that turns 80 lines of "allocate major, register cdev, create class, create device" boilerplate into 10 lines. Use it for simple character devices that don't fit a standard subsystem.
>
> **Why:** the Ch 37–38 pattern (alloc_chrdev_region + cdev_init + cdev_add + class_create + device_create) is correct but verbose. The misc framework is the kernel's pre-canned version. Many real drivers, `/dev/watchdog`, `/dev/hwrng`, `/dev/rfkill`, `/dev/btrfs-control`, `/dev/loop-control`, use it. Knowing when to use it saves you the chardev boilerplate.
>
> **Focus:** **misc is just chardev with shared major 10**. There's no new mechanism, the kernel reserves major 10 for "miscellaneous" devices and the misc framework hands out minor numbers within that major. Your driver provides just minor + name + fops. The rest is done for you.


## 40.1  When to use misc (and when not to)

Use misc when:

- You need a chardev for a single device (or a small fixed number of them).
- The device doesn't fit any existing subsystem (LED, RTC, GPIO, input, sound, etc.). If it does fit, register with that subsystem instead, you get richer integration (sysfs attributes, common ioctls, user-space tooling).
> **MCU bridge:** Think of Linux GPIO like the same pin set/reset block you used on STM32, but accessed through a kernel subsystem that owns numbering, direction, interrupts, and user-space exposure.
> **GPIO:** General-Purpose Input/Output, a pin controlled as a digital input, output, or interrupt source.
> **sysfs:** a kernel-generated filesystem under /sys that exposes devices, drivers, and attributes.
- You don't need to publish custom class-level attributes (those go on `/sys/class/<your-class>/`).

Don't use misc when:

- You need *many* dynamically-numbered instances (loop devices, USB serial ports). Misc minor space is limited.
- You're writing a driver that should integrate with a framework (LED → `leds-class`. Input device → `input_register_device`. Sound → ALSA/ASoC. Network → `netdev`). The Part VI subsystem chapters will cover these.
> **ASoC:** ALSA System-on-Chip, the embedded audio layer that connects CPU audio ports, codecs, and board wiring.
> **ALSA:** Linux's kernel and user-space audio stack.

For these in-between cases, simple chardev, one or two instances, no matching framework, misc fits.

## 40.2  The API

`#include <linux/miscdevice.h>`

```c
struct miscdevice {
    int                  minor;      /* MISC_DYNAMIC_MINOR for "let kernel pick" */
    const char          *name;       /* device name, becomes /dev/<name> */
    const struct file_operations *fops;
    struct list_head     list;
    struct device       *parent;
    struct device       *this_device;
    const struct attribute_group **groups;
    const char          *nodename;   /* optional: name override for /dev */
    umode_t              mode;       /* permission mode */
};

int  misc_register(struct miscdevice *misc);
void misc_deregister(struct miscdevice *misc);
```

Two functions. The full API.

## 40.3  Hello, misc

Take the chardev from Ch 37 and rewrite it as a misc device. The before:

```c
/* Ch 37 — by hand */
err = alloc_chrdev_region(&hd->devid, 0, 1, "hello");      /* 1 line */
cdev_init(&hd->cdev, &hello_fops);                          /* 2 */
hd->cdev.owner = THIS_MODULE;                               /* 3 */
err = cdev_add(&hd->cdev, hd->devid, 1);                    /* 4 */
hd->class = class_create("hello");             /* 5 */
hd->device = device_create(hd->class, NULL, hd->devid, NULL, "hello");  /* 6 */
/* +cleanup labels, +reverse-order unwind */
```

The after, using misc:

```c
/* Ch 40 — using misc */
static struct miscdevice hello_misc = {
    .minor = MISC_DYNAMIC_MINOR,
    .name  = "hello",
    .fops  = &hello_fops,
    .mode  = 0660,
};

static int __init hello_init(void)
{
    return misc_register(&hello_misc);
}

static void __exit hello_exit(void)
{
    misc_deregister(&hello_misc);
}
```

Six lines to register, one to deregister. The kernel:
- Allocates a free minor in the misc major (10).
- Creates `/dev/hello` automatically via the device-model hot-plug.
- Sets the mode (0660 here, so the device is group-readable/writable).
- Increments your module's refcount on every open.

Load:

```
[root@pa-mini:~]# insmod hello_misc.ko
[root@pa-mini:~]# ls -l /dev/hello
crw-rw---- 1 root root 10, 122 May 24 09:30 /dev/hello
```

The major is `10` (the misc-class major), the minor is whatever the kernel picked. `cat /proc/devices` confirms:

```
[root@pa-mini:~]# cat /proc/devices | head -10
Character devices:
...
 10 misc
...
```

Inside `/sys/class/misc/`:

```
[root@pa-mini:~]# ls /sys/class/misc/
device-tree-id  hello  hpet  hwrng  loop-control  rfkill  ...
```

Your device sits alongside the kernel's other misc devices.

## 40.4  Real-world examples to study

The kernel has dozens of misc drivers, small files, easy to read. The instructive ones:

| Driver | File | What it does |
|--------|------|--------------|
| `loop-control` | `drivers/block/loop.c` | Helper to create/free loop devices |
| `watchdog` | `drivers/watchdog/watchdog_dev.c` | The `/dev/watchdog` interface (Ch 51A) |
| `hwrng` | `drivers/char/hw_random/core.c` | The hardware RNG framework |
| `rfkill` | `net/rfkill/core.c` | WiFi/Bluetooth kill-switch interface |

Read any of them: you'll see `misc_register` used exactly as we used it, surrounded by the subsystem's own initialization. Misc is *one piece* of a real driver, not the whole driver.

## 40.5  Comparison table

| Feature | Manual chardev (Ch 37–38) | misc |
|---------|--------------------------|------|
| Boilerplate lines | ~30 | ~6 |
| Major number | Dynamic (yours) | Fixed (10) |
| Minor numbers | All yours, 0..N-1 | One from misc's pool |
| Custom class in sysfs | Yes (you control name) | No (lives under `/sys/class/misc/`) |
| Multiple instances of same driver | Easy | Each needs its own `miscdevice` struct |
| Right for: | "Custom subsystem feel"; many instances | Simple one-off chardev |

## 40.6  Lab

1. **Convert your Ch 38 driver to misc.** Drop `alloc_chrdev_region`, `cdev_*`, `class_create`, `device_create`. Replace with `misc_register`. Verify same external behavior.
2. **Two misc devices in one module.** Define two `miscdevice` structs (`hello_a`, `hello_b`) and `misc_register` both. Confirm `/dev/hello_a` and `/dev/hello_b` appear.
3. **Combine misc + platform driver.** In your Ch 39 demo platform driver, register a misc device from inside `probe()` and `misc_deregister` from `remove()`. Now you have a DT-described platform driver that exposes a `/dev/` interface, the canonical pattern for embedded chardev drivers.
4. **Read `drivers/char/hw_random/core.c`.** Specifically the calls to `misc_register`. Note how the hwrng subsystem manages multiple RNG backends with one shared misc device.

## 40.7  Pitfalls

- **`miscdevice` must outlive the registration**, because the misc layer holds a pointer to it. Don't put it on the stack of `init()`, make it `static` or allocate it with `kmalloc`.
- **Multiple modules registering with the same `name`.** `misc_register` returns `-EBUSY`. The first one wins. Pick a unique name.
- **Forgetting `.mode`.** Default is 0600 (root-only). Set 0660 (or whatever) explicitly if you want non-root access.
- **Need a custom class but using misc.** Misc devices all live in `/sys/class/misc/`. If you need your own class with shared attributes across instances, drop back to manual chardev (Ch 37–38), misc isn't the right tool.
- **Hot-add/hot-remove during shutdown.** If you `misc_deregister` while a `/dev/hello` is still open, the kernel safely refuses the unregister via refcount. Cleanly close all fds first.

## 40.8  Going deeper

- **`Documentation/driver-api/miscellaneous.rst`**: the misc framework's official short doc.
- **`include/linux/miscdevice.h`**: the small header with all the well-known minor numbers reserved (e.g., minor 130 = `/dev/watchdog`).
- **`drivers/char/misc.c`**: implementation. ~250 lines. Easy read.

> Next chapter: **Chapter 41: Concurrency in the kernel.** With a working chardev (whether manual or misc) we now look at the synchronization primitives every driver needs: atomics, spinlocks, mutexes, and when to use which.
