---
chapter: 46
title: I²C drivers
part: VI — Driver development
estimated_pages: 22
status: draft
---

# Chapter 46 — I²C drivers

> **What:** the Linux **I²C subsystem** — `i2c_adapter` (the controller, which we don't write), `i2c_client` (one chip on the bus), `i2c_driver` (the per-chip driver), `i2c_msg` (one transaction). By the end you'll have a driver that probes when a DT node says `compatible = "your,chip"`, talks to it with `i2c_transfer`, and exposes it via chardev or sysfs.
> **sysfs** - a kernel-generated filesystem under /sys that exposes devices, drivers, and attributes.
>
> **Why:** I²C is the most common slow bus in embedded systems: temp sensors, EEPROMs, GPIO expanders, RTCs, audio codecs, touch controllers, PMICs, battery gauges — half of Part VII's cookbook chapters are I²C devices. The Linux I²C model is a *clean* example of the bus/driver/device split first introduced in Ch 39 — and every I²C driver looks the same once you know the shape.
> MCU bridge: Think of Linux GPIO like the same pin set/reset block you used on STM32, but accessed through a kernel subsystem that owns numbering, direction, interrupts, and user-space exposure.
> **GPIO** - General-Purpose Input/Output, a pin controlled as a digital input, output, or interrupt source.
>
> **Focus:** **i2c_msg is the universal transaction**. `i2c_transfer(adapter, msgs, count)` sends a sequence of `i2c_msg` structs. each is one read or write, and adjacent ones share the bus without a STOP between them. Get this primitive right and you can talk to any I²C chip: write-then-read, repeated-start, 10-bit addressing, SMBus quirks.
>
> **Tooling.** This chapter uses `i2c-tools` (`i2cdetect`, `i2cdump`, `i2cset`, `i2cget`).
> - **Ubuntu-base (target):** `apt install i2c-tools`
> - **Buildroot:** `BR2_PACKAGE_I2C_TOOLS=y`
> **Buildroot** - a configuration-driven build system that produces a complete root filesystem and related images.
> - Full per-tool reference: [Userspace tooling appendix](../part5-rootfs/appendix-tooling.md).
> MCU bridge: Think of the rootfs as the firmware image's file-backed runtime environment. On an MCU you link everything into flash. On Linux, programs and config live in this mounted tree.
> **rootfs** - root filesystem, the directory tree mounted at / that contains /bin, /etc, /dev, and libraries.


## 46.1  The split: adapter vs client vs driver

Three players:

```
   i2c_adapter      i2c_client       i2c_driver
   ───────────      ──────────       ──────────
   the controller   one chip on      the code that
   (SoC peripheral) the bus           knows the chip's
                                       registers
   "i2c-imx"        "BME280 at 0x76"  "bme280"
   on bus #1
```

- **`i2c_adapter`** is the I²C controller driver — i.MX6ULL has 4 (I2C1, I2C2, I2C3, I2C4). NXP wrote `drivers/i2c/busses/i2c-imx.c`. You don't touch this unless you're porting Linux to a new SoC. It exposes the bus as `/dev/i2c-N` and registers with the kernel's I²C core.
- **`i2c_client`** describes one chip: bus number, 7-bit address, name. The kernel creates these from DT nodes — for every child node of an `&i2c1` block, you get one `i2c_client`.
- **`i2c_driver`** is what you write. It declares "I handle chips whose DT `compatible` is X" and provides `probe()` / `remove()` callbacks.

When the kernel parses DT, it sees:

```dts
&i2c1 {
    bme280@76 {
        compatible = "bosch,bme280";
        reg = <0x76>;
    };
};
```

…and creates an `i2c_client` with `addr = 0x76`, `name = "bme280"`. When your `i2c_driver` registers, the I²C core walks every client on every adapter. For each one whose `compatible` is in your `of_match_table`, it calls your `probe()`.

## 46.2  Device tree for I²C

The i.MX6ULL has 4 I²C controllers. Enable one in your board DT:

```dts
&i2c1 {
    clock-frequency = <100000>;    /* 100 kHz standard mode */
    pinctrl-names = "default";
    pinctrl-0 = <&pinctrl_i2c1>;
    status = "okay";

    /* children = devices on the bus */
    eeprom: at24@50 {
        compatible = "atmel,24c02";
        reg = <0x50>;
        pagesize = <8>;
    };

    bme280: bme280@76 {
        compatible = "bosch,bme280";
        reg = <0x76>;
    };

    expander: gpio@20 {
        compatible = "microchip,mcp23017";
        reg = <0x20>;
        gpio-controller;
        #gpio-cells = <2>;
    };
};
```

Three rules:

1. **`reg` is the I²C address** (7-bit, low 7 bits — so 0x76 means address pattern `1110110`). Not a memory address.
2. **The unit-name** (`bme280@76`) must match `reg` in hex. This is a DT lint rule. mismatch produces a warning.
3. **`clock-frequency`** sets the bus speed: 100 kHz (standard), 400 kHz (fast), 1 MHz (fast-plus), or 3.4 MHz (high-speed). Limited by your slowest device on the bus.

## 46.3  Anatomy of an I²C driver

The minimal skeleton:

```c
#include <linux/init.h>
#include <linux/module.h>
#include <linux/i2c.h>
#include <linux/of.h>

struct mychip_priv {
    struct i2c_client *client;
    /* device state */
};

static int mychip_probe(struct i2c_client *client)
{
    struct mychip_priv *priv;
    int chip_id;

    priv = devm_kzalloc(&client->dev, sizeof(*priv), GFP_KERNEL);
    if (!priv)
        return -ENOMEM;
    priv->client = client;
    i2c_set_clientdata(client, priv);

    /* Read chip-id register to verify the chip is present */
    chip_id = i2c_smbus_read_byte_data(client, 0xD0);   /* chip-id reg */
    if (chip_id < 0)
        return dev_err_probe(&client->dev, chip_id, "read chip-id failed\n");
    if (chip_id != 0x60)
        return dev_err_probe(&client->dev, -ENODEV,
                             "unexpected chip-id 0x%02x\n", chip_id);

    dev_info(&client->dev, "mychip ready at 0x%02x\n", client->addr);
    return 0;
}

static void mychip_remove(struct i2c_client *client)
{
    /* devm_* cleans up; nothing to do */
}

static const struct i2c_device_id mychip_id[] = {
    { "mychip", 0 },
    { }
};
MODULE_DEVICE_TABLE(i2c, mychip_id);

static const struct of_device_id mychip_of_match[] = {
    { .compatible = "linuxlearn,mychip" },
    { }
};
MODULE_DEVICE_TABLE(of, mychip_of_match);

static struct i2c_driver mychip_driver = {
    .driver = {
        .name = "mychip",
        .of_match_table = mychip_of_match,
    },
    .probe = mychip_probe,
    .remove = mychip_remove,
    .id_table = mychip_id,
};
module_i2c_driver(mychip_driver);

MODULE_LICENSE("GPL");
```

Key things to notice:

**`module_i2c_driver(mychip_driver)`** — like `module_platform_driver`, this is a macro that generates the `module_init`/`module_exit` pair. One-liner registration.

**`i2c_set_clientdata` / `i2c_get_clientdata`** — store and retrieve your private struct pointer on the client. Used to find the priv struct from later callbacks.

**Two match tables** — `i2c_device_id` for non-DT systems (the `id_table`) *and* `of_device_id` for DT. Modern systems use DT. The `i2c_device_id` is the historical fallback. Include both for portability.

**`MODULE_DEVICE_TABLE(i2c, mychip_id)`** — exposes the table to depmod so the right module autoloads when an I²C device with that name is detected.

## 46.4  SMBus API — the simple case

For one-byte, one-word, and block transfers, use the **SMBus** API:

```c
int  i2c_smbus_read_byte_data(struct i2c_client *client, u8 reg);
int  i2c_smbus_write_byte_data(struct i2c_client *client, u8 reg, u8 val);
int  i2c_smbus_read_word_data(struct i2c_client *client, u8 reg);
int  i2c_smbus_write_word_data(struct i2c_client *client, u8 reg, u16 val);
int  i2c_smbus_read_i2c_block_data(struct i2c_client *client, u8 reg, u8 len, u8 *buf);
int  i2c_smbus_write_i2c_block_data(struct i2c_client *client, u8 reg, u8 len, const u8 *buf);
```

Each function does the "write the register address, then read N bytes" pattern (or write equivalent) in one call. They return the read value (or negative errno) for the read variants. 0 or negative for writes.

A typical sensor read:

```c
/* Read temperature: register 0xFA, 3 bytes */
u8 raw[3];
int err = i2c_smbus_read_i2c_block_data(client, 0xFA, 3, raw);
if (err < 0)
    return err;
int temp_raw = (raw[0] << 12) | (raw[1] << 4) | (raw[2] >> 4);
```

SMBus is technically a subset of I²C with stricter timing, but the SMBus helpers work on any standard I²C bus. Almost all chips with "register N, read M bytes" semantics work with SMBus calls.

## 46.5  Raw `i2c_transfer` — when SMBus isn't enough

Some chips need transactions SMBus doesn't model directly — for example, a write of 5 bytes followed by a read of 200 bytes, or a write with no repeated-start. For those, drop down to the lowest-level API:

```c
struct i2c_msg msgs[2] = {
    {
        .addr  = client->addr,
        .flags = 0,                  /* write */
        .len   = 2,
        .buf   = (u8[]){ 0xFA, 0x00 }, /* 2-byte register address */
    },
    {
        .addr  = client->addr,
        .flags = I2C_M_RD,           /* read; repeated-start before this msg */
        .len   = 16,
        .buf   = rxbuf,
    },
};

int ret = i2c_transfer(client->adapter, msgs, ARRAY_SIZE(msgs));
if (ret != 2)
    return ret < 0 ? ret : -EIO;
```

The kernel issues the entire message group atomically — START, addr+W, two write bytes, repeated-START, addr+R, 16 read bytes, STOP. Between two `i2c_msg`s there's a *repeated start* (no STOP). If you wanted separate transactions with bus release in between, two separate `i2c_transfer` calls.

`i2c_msg.flags` bits:
- `I2C_M_RD` — this message is a read.
- `I2C_M_TEN` — 10-bit address (rare).
- `I2C_M_NOSTART` — don't issue START for this message (concatenates with previous. rare).
- `I2C_M_IGNORE_NAK` — don't treat NAK as an error (for "best-effort" writes).

## 46.6  A complete example: AT24C02 EEPROM-backed sysfs

Let's make this concrete with a worked example: a driver for the AT24C02 (256-byte EEPROM) that exposes its contents via a sysfs `data` binary attribute. (Note: the real `at24` driver in the kernel does this and more. This is a simplified version for learning.)

```c
#include <linux/init.h>
#include <linux/module.h>
#include <linux/i2c.h>
#include <linux/sysfs.h>

struct at24_priv {
    struct i2c_client *client;
    struct bin_attribute attr;
    size_t size;
};

static ssize_t at24_read(struct file *filp, struct kobject *kobj,
                         struct bin_attribute *attr,
                         char *buf, loff_t off, size_t count)
{
    struct at24_priv *p = dev_get_drvdata(kobj_to_dev(kobj));
    struct i2c_msg msgs[2];
    u8 addr = off;

    if (off + count > p->size)
        count = p->size - off;
    if (count == 0)
        return 0;

    msgs[0] = (struct i2c_msg){
        .addr = p->client->addr, .flags = 0, .len = 1, .buf = &addr,
    };
    msgs[1] = (struct i2c_msg){
        .addr = p->client->addr, .flags = I2C_M_RD, .len = count, .buf = buf,
    };

    int n = i2c_transfer(p->client->adapter, msgs, 2);
    return n == 2 ? count : -EIO;
}

static ssize_t at24_write(struct file *filp, struct kobject *kobj,
                          struct bin_attribute *attr,
                          char *buf, loff_t off, size_t count)
{
    struct at24_priv *p = dev_get_drvdata(kobj_to_dev(kobj));
    u8 tx[1 + 8];      /* 1 addr + page-size data */
    size_t done = 0;

    if (off + count > p->size)
        count = p->size - off;

    while (done < count) {
        /* AT24C02 has 8-byte pages; can't cross a page boundary in one write */
        size_t pageoff = (off + done) % 8;
        size_t chunk = min_t(size_t, count - done, 8 - pageoff);
        tx[0] = off + done;
        memcpy(tx + 1, buf + done, chunk);

        struct i2c_msg msg = {
            .addr = p->client->addr, .flags = 0, .len = chunk + 1, .buf = tx,
        };
        int n = i2c_transfer(p->client->adapter, &msg, 1);
        if (n != 1) return -EIO;

        msleep(5);     /* AT24C02 internal write cycle: ≤5 ms */
        done += chunk;
    }
    return count;
}

static int at24_probe(struct i2c_client *client)
{
    struct at24_priv *p;
    int err;

    p = devm_kzalloc(&client->dev, sizeof(*p), GFP_KERNEL);
    if (!p) return -ENOMEM;

    p->client = client;
    p->size = 256;     /* AT24C02 = 256 bytes */

    sysfs_bin_attr_init(&p->attr);
    p->attr.attr.name = "data";
    p->attr.attr.mode = 0660;
    p->attr.size      = p->size;
    p->attr.read      = at24_read;
    p->attr.write     = at24_write;

    dev_set_drvdata(&client->dev, p);

    err = sysfs_create_bin_file(&client->dev.kobj, &p->attr);
    if (err)
        return dev_err_probe(&client->dev, err, "sysfs create failed\n");

    dev_info(&client->dev, "AT24C02 %zu-byte EEPROM ready\n", p->size);
    return 0;
}

static void at24_remove(struct i2c_client *client)
{
    struct at24_priv *p = dev_get_drvdata(&client->dev);
    sysfs_remove_bin_file(&client->dev.kobj, &p->attr);
}

static const struct of_device_id at24_of_match[] = {
    { .compatible = "linuxlearn,at24c02" },
    { }
};
MODULE_DEVICE_TABLE(of, at24_of_match);

static struct i2c_driver at24_driver = {
    .driver = {
        .name = "linuxlearn-at24",
        .of_match_table = at24_of_match,
    },
    .probe  = at24_probe,
    .remove = at24_remove,
};
module_i2c_driver(at24_driver);

MODULE_LICENSE("GPL");
```

Build, load. From user-space:

```
[root@pa-mini:~]# ls /sys/bus/i2c/devices/1-0050/
data  driver/  name  ...

[root@pa-mini:~]# echo -n "hello world" > /sys/bus/i2c/devices/1-0050/data
[root@pa-mini:~]# dd if=/sys/bus/i2c/devices/1-0050/data bs=11 count=1
hello world
```

11 bytes wrote, 11 bytes read. The `dd` triggered an `at24_read` that issued a write-then-read transaction. The `echo` triggered an `at24_write` that paged out the data 8 bytes at a time with 5 ms waits between pages.

The mainline `at24` driver (`drivers/misc/eeprom/at24.c`) does this and more — nvmem integration, large-EEPROM support, write-protect-GPIO, etc. Read it.

## 46.7  /dev/i2c-N — user-space access

For development, prototyping, and quick chip inspection, user-space can talk directly to any I²C bus via the `i2c-dev` chardev:

```
[root@pa-mini:~]# modprobe i2c-dev
[root@pa-mini:~]# ls /dev/i2c-*
/dev/i2c-0  /dev/i2c-1  /dev/i2c-2  /dev/i2c-3
```

Install the `i2c-tools` package and you get `i2cdetect`, `i2cget`, `i2cset`, `i2cdump`, `i2ctransfer`:

```
[root@pa-mini:~]# i2cdetect -y 1
     0  1  2  3  4  5  6  7  8  9  a  b  c  d  e  f
00:                         -- -- -- -- -- -- -- --
10: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
20: 20 -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
30: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
40: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
50: 50 -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
60: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
70: -- -- -- -- -- -- 76 -- -- -- -- -- -- -- -- --

[root@pa-mini:~]# i2cget -y 1 0x76 0xD0
0x60                                    ← BME280 chip-id read

[root@pa-mini:~]# i2cset -y 1 0x50 0x00 0xAB
                                        ← write 0xAB to AT24 address 0
```

If a kernel driver has already bound to the device, `i2c-tools` will refuse to touch it (you would race the driver). Pass `-y -f` to override — only for known-safe testing.

## 46.8  Lab

1. **Build and load the AT24 driver.** Connect an AT24C02 to I²C1, populate the DT node, verify sysfs `data` attribute reads back what you wrote.
2. **Try i2cdetect.** Identify the AT24's address, confirm it matches your DT `reg`.
3. **Switch to SMBus calls.** Rewrite the read path using `i2c_smbus_read_i2c_block_data`. Verify identical behavior. Discuss when each form is appropriate.
4. **Test write-protect.** Add a `wp-gpios` GPIO. in your write path, deassert WP before writing, assert after. Compare against the in-tree `at24` driver, which has this feature.
5. **Stress-test page alignment.** Write 256 bytes starting at offset 3. Verify the driver correctly handles the page boundaries at 8, 16, 24, …
6. **Inspect with strace.** `strace -e read,write,ioctl i2cget -y 1 0x76 0xD0` — see the `I2C_RDWR` ioctl in action. that's how i2c-tools talk to the i2c-dev chardev.

## 46.9  Pitfalls

- **Wrong unit-name vs `reg`.** `bme280@76` with `reg = <0x77>` doesn't match — kernel warns, but the device may still probe at 0x77 (the `reg` wins). DT lint catches it. Check your DT compilation log.
- **Missing pinctrl.** SDA/SCL pins not muxed to I²C function. Symptom: `i2cdetect` shows nothing. Use `gpioinfo` to confirm pins aren't claimed as GPIO instead.
- **Pull-up resistors missing.** I²C requires external pull-ups (typically 4.7 kΩ to 3.3 V). The SoC's internal pull-ups (~50 kΩ) usually work at 100 kHz but fail at 400 kHz. Schematic problem, not software.
- **Bus contention with multiple drivers.** Two drivers each claiming the same address → second one fails to probe. `dmesg` says `"address 0x76 already in use"`. Check for hidden DT children.
- **Wrong clock-frequency.** Some chips can't handle 400 kHz. The bus runs as fast as `clock-frequency` says. slower devices NAK or corrupt data. Drop to 100 kHz when in doubt.
- **Calling SMBus block read with the wrong size.** SMBus has `read_i2c_block_data` (variable length) and `read_block_data` (size sent by chip). They look similar. Check your chip's protocol.
- **Mixing `i2c_master_send/recv` and `i2c_transfer` styles.** They work, but `i2c_transfer` is more flexible. New code should prefer it.
- **Forgetting `MODULE_DEVICE_TABLE`.** Auto-loading silently fails.
- **Address aliasing.** Some chips support multiple addresses based on address-pin pull. If two of the same chip are on the bus, configure them with different pull strappings. otherwise both respond to the same address.

## 46.10  Going deeper

- **`Documentation/i2c/`** — full I²C subsystem documentation. Read `summary.rst`, `writing-clients.rst`, `instantiating-devices.rst`.
- **`Documentation/devicetree/bindings/i2c/`** — DT bindings for the I²C subsystem.
- **`drivers/i2c/busses/i2c-imx.c`** — the i.MX I²C controller driver. ~1200 lines. Worth reading once.
- **`drivers/misc/eeprom/at24.c`** — production-grade EEPROM driver with nvmem, regmap, and write-protect support.
MCU bridge: Think of regmap like a typed wrapper around your read_reg() and write_reg() helpers, with caching, locking, and bus differences handled centrally.
**regmap** - a kernel helper that wraps register reads and writes over I2C, SPI, or MMIO.
- **`drivers/iio/pressure/bmp280-i2c.c`** + `bmp280-core.c` — clean modern I²C IIO driver. Pairs nicely with Ch 49.
**IIO** - Industrial I/O, Linux's subsystem for sensors, ADCs, DACs, and buffered sampled data.
- **`drivers/i2c/i2c-core.c`** — the I²C core itself. Hundreds of pages of API to skim.

> Next chapter: **Chapter 47 — SPI drivers.** Same shape as I²C: a controller subsystem we don't write, a `spi_device` per chip, a `spi_driver` per chip-class — but now with full-duplex transactions and per-CS configuration.
