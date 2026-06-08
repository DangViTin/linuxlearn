---
chapter: 38
title: Auto-creating /dev nodes (class + device + uevent)
part: VI — Driver development
estimated_pages: 14
status: draft
---

# Chapter 38 — Auto-creating `/dev/` nodes

> **Privilege boundary:** $ means normal user. # or sudo means root and can change host or target state.
> After a privileged command, verify the expected device, service, or file appears before continuing. Roll back by undoing the config change or stopping the service you just enabled.


> **What:** `class_create` + `device_create` — the two calls that let your driver tell the kernel "I have a new device. please broadcast a hot-plug event so user-space creates `/dev/<name>` for me." With these in place you never `mknod` by hand again.
>
> **Why:** real drivers don't burden users with manual `mknod` steps after every `insmod`. Modern Linux uses the **uevent** mechanism — the kernel broadcasts a netlink message describing the new device, and a user-space agent (udev on workstations, mdev on embedded) reacts by creating the right file in `/dev/`, setting permissions, and possibly running scripts. Your driver's only responsibility is to register the device and let the framework do the rest.
> **udev** - the user-space device manager that reacts to kernel device events and creates policy-driven /dev nodes.
>
> **Focus:** **the relationship between `/sys/class/...` and `/dev/...`**. The class hierarchy in sysfs is the *source of truth* — that's where the kernel describes what devices exist. The `/dev/` tree is a **shadow** of sysfs maintained by the hot-plug agent. Get this picture right and most "why is my device file missing?" debugging becomes trivial.


## 38.1  The hot-plug pipeline

When your driver calls `device_create(...)`, this happens:

```
   driver: device_create(class, NULL, devid, NULL, "hello")
                │
                ▼
   kernel: creates /sys/class/hello/hello/  with attributes:
              ├─ dev              (the "240:0" string)
              ├─ uevent           (writable trigger)
              └─ subsystem        (symlink back up)
                │
                ▼
   kernel: emits a uevent of type "add"
              ACTION=add
              DEVNAME=hello
              MAJOR=240
              MINOR=0
              SUBSYSTEM=hello
                │
                ▼ (netlink broadcast)
   udev/mdev: receives the event, looks up rules
                │
                ▼
   udev/mdev: mknod /dev/hello c 240 0
              chmod 0660 /dev/hello
              chown root:plugdev /dev/hello
```

The driver call (`device_create`) doesn't itself create `/dev/hello`. It creates the **sysfs entry** at `/sys/class/hello/hello/`, which the kernel uses to broadcast the uevent. The actual `/dev/hello` is created by the **listener**.

This is different from how you might imagine it. The kernel does not maintain `/dev/`. It publishes events. User-space decides what to do with them. Different listeners can make wildly different choices (udev creates rich-permission nodes with named symlinks. mdev creates minimal nodes. both work).

(Aside: there is a fallback. If `CONFIG_DEVTMPFS=y` and the kernel mounts devtmpfs on `/dev/` — Ch 32 — the *kernel itself* auto-creates the device node, no user-space listener required. Then udev/mdev's job becomes just refining permissions and creating symlinks. We'll assume devtmpfs is on, which it is in 99% of modern setups.)

## 38.2  Adding to the chardev driver

Take the Ch 37 driver and add a class, a device, and matching cleanup — about a dozen lines.

```c
#include <linux/device.h>

struct hello_dev {
    struct cdev cdev;
    dev_t devid;
    struct class *class;
    struct device *device;
    char *buffer;
    size_t buf_len;
    struct mutex lock;
};
```

In `hello_init`, after `cdev_add` succeeds:

```c
    hd->class = class_create("hello");
    if (IS_ERR(hd->class)) {
        err = PTR_ERR(hd->class);
        goto del_cdev;
    }

    hd->device = device_create(hd->class, NULL, hd->devid, NULL, "hello");
    if (IS_ERR(hd->device)) {
        err = PTR_ERR(hd->device);
        goto destroy_class;
    }
```

And the new cleanup labels:

```c
destroy_class:
    class_destroy(hd->class);
del_cdev:
    cdev_del(&hd->cdev);
```

In `hello_exit`, balance them (in reverse order):

```c
    device_destroy(hd->class, hd->devid);
    class_destroy(hd->class);
    cdev_del(&hd->cdev);
    unregister_chrdev_region(hd->devid, 1);
```

That's it. Build, load:

```
[root@pa-mini:~]# insmod hello_chrdev.ko
[root@pa-mini:~]# ls -l /dev/hello
crw-rw---- 1 root root 240, 0 May 24 09:30 /dev/hello
[root@pa-mini:~]# echo "ping" > /dev/hello
[root@pa-mini:~]# cat /dev/hello
ping
[root@pa-mini:~]# rmmod hello_chrdev
[root@pa-mini:~]# ls -l /dev/hello
ls: cannot access '/dev/hello': No such file or directory
```

No `mknod` step. The file appears at load and disappears at unload.

## 38.3  Anatomy of class and device

### `class_create`

```c
struct class *class_create(struct module *owner, const char *name);
```

Creates a directory `/sys/class/<name>/`. A *class* is a group of devices that share a role — LED, RTC, GPIO chip, network interface, sound card. The class directory holds one entry per device in that group. It also publishes group-level attributes that udev/mdev rules can match on.
MCU bridge: Think of Linux GPIO like the same pin set/reset block you used on STM32, but accessed through a kernel subsystem that owns numbering, direction, interrupts, and user-space exposure.
**GPIO** - General-Purpose Input/Output, a pin controlled as a digital input, output, or interrupt source.

The kernel ships dozens of standard classes:

```
[root@pa-mini:~]# ls /sys/class/
backlight   gpio        leds       power_supply  rtc
block       i2c-adapter mdio_bus   pwm           sound
bluetooth   input       net        regulator     spi_master
...
```

When you create your own class (`"hello"`), `/sys/class/hello/` appears. New custom-driver chardevs that *don't fit* an existing class do this — make a class with the driver's name. Drivers that fit an existing class skip `class_create` and register with the subsystem framework directly. For example, an LED driver belongs in `leds` and an RTC in `rtc`. Ch 44–48 cover these subsystems.

### `device_create`

```c
struct device *device_create(struct class *class, struct device *parent,
                              dev_t devt, void *drvdata,
                              const char *fmt, ...);
```

- **`class`** — which class this device belongs to.
- **`parent`** — the device's parent in the device hierarchy. `NULL` is fine for top-level chardev. Real subsystem drivers set this to the platform device or USB device that hosts them, so sysfs reflects the bus topology.
- **`devt`** — the `dev_t` (major:minor). The kernel writes `MAJOR:MINOR` into the device's `dev` attribute, which is what udev/mdev reads.
- **`drvdata`** — a `void *` stored in the `device`'s `driver_data` field. Use it (or `dev_set_drvdata` later) to attach your own state.
- **`fmt, ...`** — `printf`-style device name. Becomes the directory name in `/sys/class/<class>/<name>/` *and* (via the uevent's `DEVNAME`) the filename in `/dev/`.

A few naming conventions to know:

- For a single-instance device, use `"hello"`.
- For multiple instances, use a format like `"hello%d", index`. The result is `/dev/hello0`, `/dev/hello1`, etc.
- For sub-devices, use a slash: `"input/event%d"` puts the result at `/dev/input/eventN`.

Inspect what got created:

```
[root@pa-mini:~]# ls /sys/class/hello/hello/
dev    power/    subsystem    uevent

[root@pa-mini:~]# cat /sys/class/hello/hello/dev
240:0

[root@pa-mini:~]# cat /sys/class/hello/hello/uevent
DEVNAME=hello
DEVTYPE=
MAJOR=240
MINOR=0
SUBSYSTEM=hello
```

The `uevent` file is special: reading it prints the current state, **writing** to it re-broadcasts the event. Writing `echo add > uevent` re-triggers the event. This is useful for replaying events on a system that booted before udev was running.

## 38.4  Picking permissions and ownership

By default, udev/mdev creates `/dev/hello` with permissions 0600 (root-only). That's safe but unhelpful — your test programs running as a regular user can't open the device.

Three places to set device permissions, in order of preference:

### A. udev rule (cleanest)

Create `/etc/udev/rules.d/99-hello.rules`:

```
KERNEL=="hello", MODE="0660", GROUP="plugdev"
```

Reload:

```
[root@pa-mini:~]# udevadm control --reload
[root@pa-mini:~]# udevadm trigger --subsystem-match=hello
```

Now `/dev/hello` is mode 0660, owned by `root:plugdev`. Add your user to the `plugdev` group and they can read/write it.

### B. mdev rule (embedded with BusyBox)

`/etc/mdev.conf`:

```
hello   0:plugdev 0660
```

`mdev`'s syntax is positional, not key=value: name, owner:group, mode. mdev applies these on every new device event. (Re-trigger by `mdev -s` to apply to already-created files.)

### C. Devnode callback in the driver

For permissions that *must* be a property of the driver (because user-space rule files might not exist), set a `devnode` callback on the class:

```c
static char *hello_devnode(struct device *dev, umode_t *mode)
{
    if (mode)
        *mode = 0660;   /* readable by group */
    return NULL;
}

/* In init: */
hd->class->devnode = hello_devnode;
```

The kernel's devtmpfs runs `devnode` when creating the device and respects the returned mode. This is the most reliable but least configurable approach — most production systems use udev rules instead.

## 38.5  Multiple devices in one driver

If your driver controls *N* identical devices (e.g., 4 LEDs, 8 GPIO chips), you want a single driver creating multiple `/dev/` nodes. The pattern:

```c
#define N_DEVICES 4

static struct hello_dev *hds[N_DEVICES];
static struct class *hello_class;
static dev_t hello_base_devid;

static int __init hello_init(void)
{
    int i, err;

    err = alloc_chrdev_region(&hello_base_devid, 0, N_DEVICES, "hello");
    if (err) return err;

    hello_class = class_create("hello");
    if (IS_ERR(hello_class)) {
        err = PTR_ERR(hello_class);
        goto unreg;
    }

    for (i = 0; i < N_DEVICES; i++) {
        hds[i] = kzalloc(sizeof(*hds[i]), GFP_KERNEL);
        if (!hds[i]) { err = -ENOMEM; goto unwind; }
        hds[i]->devid = MKDEV(MAJOR(hello_base_devid), i);
        cdev_init(&hds[i]->cdev, &hello_fops);
        hds[i]->cdev.owner = THIS_MODULE;
        err = cdev_add(&hds[i]->cdev, hds[i]->devid, 1);
        if (err) goto unwind;

        device_create(hello_class, NULL, hds[i]->devid, NULL, "hello%d", i);
    }
    return 0;

unwind:
    while (--i >= 0) {
        device_destroy(hello_class, hds[i]->devid);
        cdev_del(&hds[i]->cdev);
        kfree(hds[i]);
    }
    class_destroy(hello_class);
unreg:
    unregister_chrdev_region(hello_base_devid, N_DEVICES);
    return err;
}
```

After load:

```
[root@pa-mini:~]# ls /dev/hello*
/dev/hello0  /dev/hello1  /dev/hello2  /dev/hello3
```

Each is an independent chardev sharing the same `file_operations`. Use `iminor(filp->f_inode)` to figure out which one a given open is referring to.

## 38.6  Exposing custom sysfs attributes

A device file is one way to talk to your driver. Sysfs attributes are another, and they're often *better* for set-once configuration or one-shot commands.

Add a `state` attribute:

```c
static ssize_t state_show(struct device *dev, struct device_attribute *attr,
                          char *buf)
{
    return sysfs_emit(buf, "loaded\n");   /* bounds-checked since 5.10; prefer over sprintf */
}

static ssize_t state_store(struct device *dev, struct device_attribute *attr,
                           const char *buf, size_t count)
{
    pr_info("hello: state set to %.*s", (int)count, buf);
    return count;
}

static DEVICE_ATTR_RW(state);   /* creates `state` read+write attr */

/* In init, after device_create succeeds: */
err = device_create_file(hd->device, &dev_attr_state);
```

Now:

```
[root@pa-mini:~]# cat /sys/class/hello/hello/state
loaded
[root@pa-mini:~]# echo run > /sys/class/hello/hello/state
[root@pa-mini:~]# dmesg | tail -1
hello: state set to run
```

`sysfs` files are limited to **PAGE_SIZE** (4 KB on i.MX6ULL) per show callback, but that's plenty for status / configuration. They're great for things like:

- Read-only stats (`bytes_processed`, `irq_count`).
- One-shot commands (`echo reset > /sys/class/.../control`).
- Toggles (`echo 1 > /sys/class/leds/led0/brightness`).

For things like streaming data, stick to the chardev `read`/`write`. Sysfs is for control, not bandwidth.

For multiple attributes, group them and use `device_create_file` per attribute, *or* `sysfs_create_group(&dev->kobj, &attr_group)` for atomic group creation/deletion.

## 38.7  Lab

1. **Add `class_create` + `device_create`** to the Ch 37 driver. Verify `/dev/hello` appears at load and disappears at unload.
2. **Switch to multi-device.** Modify your driver to create 4 instances (`/dev/hello0` … `/dev/hello3`). Each instance has its own buffer.
3. **Make it user-accessible.** Write a udev rule that gives your devices mode 0660 in group `plugdev`. Verify a non-root user can `cat /dev/hello0`.
4. **Add a sysfs attribute.** Create `state_show`/`state_store` to expose a runtime knob — say, an integer that throttles your write speed.
5. **Inspect the uevent.** Open two terminals on the target. In one, run `udevadm monitor` (or `mdev -d` if using mdev). In the other, `insmod` and `rmmod`. Watch the events fire.
6. **Use the `devnode` callback** to set 0660 mode in the driver itself. Verify `/dev/hello` comes up with the right mode even without a udev rule.

## 38.8  Pitfalls

- **Calling `device_create` before `cdev_add`.** Device node appears but `open` on it returns `-ENXIO` because no cdev is registered for that major. Always `cdev_add` first, then `device_create`. Cleanup in reverse order.
- **Forgetting `device_destroy` in cleanup.** The `/dev/` node lingers (kernel side) — udev/mdev never gets the "remove" event. Next load creates `/dev/hello` *again*, double-registered. Eventually you'll trip over name conflicts.
- **`IS_ERR(class)` vs `class == NULL`.** `class_create` returns an `ERR_PTR` on failure, not `NULL`. Test with `IS_ERR(class)` and recover with `PTR_ERR(class)`. Same for `device_create`.
- **Race between insmod and udev.** If your user-space code does `insmod hello.ko && cat /dev/hello`, the second part may run before udev has created `/dev/hello`. Mitigation: use `udevadm settle` between `insmod` and the access, or have your user-space code retry with a short delay.
- **Class name collisions.** Two drivers trying to register a class with the same name fail loudly. Use unique names. If you're adding a driver to an existing subsystem, use that subsystem's `register` API (e.g., `led_classdev_register`) instead of creating a competing class.
- **Sysfs attribute permissions.** `DEVICE_ATTR_RW` creates 0644 attributes. For root-only writes, use `DEVICE_ATTR(name, 0640, show, store)` or one of `DEVICE_ATTR_RO`, `DEVICE_ATTR_WO`, `DEVICE_ATTR_ADMIN_RO`.
- **Returning >PAGE_SIZE from a `show` callback.** Silently truncated by sysfs. Don't use sysfs to stream large data. Use a chardev or `debugfs` instead.

## 38.9  Going deeper

- **`Documentation/driver-api/driver-model/overview.rst`** — the device model is much richer than what we use here. classes are one slice of it.
- **`Documentation/admin-guide/devices.rst`** — udev/mdev rule syntax in detail.
- **`drivers/leds/led-class.c`** — a real subsystem class, fully fleshed out. Read it once.
- **`Documentation/filesystems/sysfs.rst`** — the sysfs design rationale. explains why each file is limited to PAGE_SIZE and how the kobject hierarchy works.

> Next chapter: **Chapter 39 — Platform drivers + device tree.** With manual device registration understood, we move to the *real* way Linux drivers describe themselves: a `platform_driver` that gets matched to a device-tree `compatible` string, with `probe`/`remove` doing what `module_init`/`module_exit` did up until now.
