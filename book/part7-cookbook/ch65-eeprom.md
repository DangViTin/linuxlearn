---
chapter: 65
title: I²C / SPI EEPROM (AT24Cxx / 25LCxx)
part: VII — Device cookbook
estimated_pages: 20
status: draft
---

# Chapter 65 — I²C / SPI EEPROM

> **What:** small persistent storage chips — bytes addressable, no erase-before-write needed, ~1M write cycles. We'll walk the chip-side protocol byte-by-byte, dissect how the mainline `at24` driver actually works, then write a tiny from-scratch I²C-EEPROM driver. Three chips compared — **Microchip AT24C02** (I²C, 256 B), **AT24C512** (I²C, 64 KB), **25LC512** (SPI, 64 KB).
>
> **Why:** EEPROM is the place embedded boards store small permanent facts about themselves — MAC address, board serial, calibration. The protocol is small. Writing your own driver in 100 lines is realistic and worth the time. After this chapter the kernel's `at24.c` will read as ordinary code, not a mystery.
>
> **Focus:** **two protocol gotchas** — (a) page-aligned writes (writing across a page boundary silently wraps within the same page), and (b) the ACK-poll loop (the chip NACKs while internally programming, you poll until it ACKs). Get those two right and the rest is byte arithmetic.

## 65.1  When EEPROM beats flash, OTP fuses, NVRAM

| Use case | Best fit | Why |
|---|---|---|
| Permanent board ID, read-only after factory | **OTP / eFuse** (i.MX6ULL OCOTP) | Indestructible; can't be erased |
| MAC address, serial number, calibration — rare writes | **EEPROM** (I²C / SPI) | ~1M cycles, byte-addressable |
| Frequently updated config (boot env, A/B slot) | **NOR flash** (QSPI; redundant pair) | Larger writes, faster |
| Bulk storage (firmware, user data) | **NAND flash / eMMC** | GB-scale |

The EEPROM niche: small, byte-addressable, rewriteable but rarely written, kept on the same I²C bus as your sensors anyway. ~$0.30 BOM cost for AT24C02.

## 65.2  Chip comparison

| | AT24C02 | AT24C512 | 25LC512 |
|---|---|---|---|
| Bus | I²C | I²C | SPI |
| Capacity | 256 B (2 Kbit) | 64 KB (512 Kbit) | 64 KB (512 Kbit) |
| Page size | 8 B | 128 B | 128 B |
| Write cycle | ≤ 5 ms | ≤ 5 ms | ≤ 5 ms |
| Endurance | 1 M cycles | 1 M cycles | 1 M cycles |
| Max bus clock | 1 MHz (1.7+ V) | 1 MHz | 20 MHz |
| I²C addr | 0x50–0x57 (A0/A1/A2 strap) | 0x50–0x57 | — |
| Addressing | 1 byte | 2 bytes | 2 bytes |
| Price | $0.30 | $1.00 | $1.50 |

Pick AT24C02 for tiny ID storage (MAC, serial), AT24C512 for calibration tables, 25LC512 for SPI bus or factory-speed bulk programming.

## 65.3  Schematic — AT24C02 (I²C)

```
 i.MX6ULL              AT24C02 (8-pin SOIC)
 ─────────             ──────────────────
                          ┌──┐
        ┌──── A0 ────────►│  │
        ├──── A1 ────────►│  │  (strap A0/A1/A2 to GND or VCC
        ├──── A2 ────────►│  │   to select among 8 addresses)
        ┌──── VSS ──────►│  │  GND
        │                 │  │
 SDA ─╳─┼──── SDA ◄──────►│  │  (4.7 kΩ pull-up to 3.3 V)
 SCL ─╳─┼──── SCL ──────►│  │
        ┌──── WP ───────►│  │  (tie low to allow writes, or to GPIO for SW WP)
        └──── VCC ───────┤  │  3.3 V
                          └──┘
```

For 25LC512 (SPI): MOSI / MISO / SCK / /CS (4 wires) + /WP + /HOLD.

## 65.4  The I²C EEPROM protocol on the wire

An I²C transaction looks like this for a "read 4 bytes from offset 0x40":

```
   Master:    START | 0xA0 |   |    | 0x40 |   | START | 0xA1 |   |    |    |    |    |    | STOP
                            ACK ↑          ACK              ACK ↑   ACK  ACK  ACK  NACK
   Slave:                  ←─┘            ←┘                ←┘   ↓    ↓    ↓    ↓
                                                                D0   D1   D2   D3
```

- `0xA0` is the AT24's 7-bit address (0x50) shifted left + write bit (0): writing the **register pointer**.
- `0x40` is the byte address inside the EEPROM (since AT24C02 has only 256 bytes, one address byte suffices).
- A *repeated start*, then `0xA1` = address + read bit, then reads 4 bytes with the master ACKing each except the last (NACK signals "I'm done").

For a write of 4 bytes to offset 0x40:

```
   Master:    START | 0xA0 |   | 0x40 |   | D0 |   | D1 |   | D2 |   | D3 |   | STOP
                            ACK         ACK    ACK    ACK    ACK    ACK ↑
   Slave:                  ←─┘         ←─┘   ←─┘    ←─┘    ←─┘    ←─┘
```

After the data bytes, the chip starts an *internal write cycle* of about 5 ms. During this time it NACKs every I²C transaction. The host keeps issuing address-write transactions; each NACK means "still writing," and the first ACK means "done." This is called **ACK polling**.

For AT24C512 (and larger), the byte address is **2 bytes**: send 0xA0, ACK, addr_high, ACK, addr_low, ACK, then data. Same protocol, one more address byte.

### Page boundaries — the bite-you-once trap

The EEPROM's internal write buffer is one page. Writing 4 bytes starting at offset 0x06 of an 8-byte-page chip:

- Bytes 0x06 and 0x07 go to the buffer.
- Address auto-increments — but **wraps within the page**, not to the next page.
- So byte indexed "0x08" actually writes to **0x00**, and "0x09" to **0x01**.

The fix: split writes at page boundaries. A write of N bytes starting at offset O becomes:
- First chunk: bytes `[O, page_end)` where `page_end = (O + page_size) & ~(page_size - 1)`.
- Wait for ACK after that chunk.
- Next chunk: bytes `[page_end, page_end + page_size)`.
- And so on.

This is the AT24 driver's most important loop. Get it wrong = silent data corruption.

## 65.5  How the mainline `at24` driver works internally

Source: `drivers/misc/eeprom/at24.c` (~1000 lines).

The driver is structured around a **regmap** abstraction (Ch 50) over either `regmap_init_i2c` or `regmap_init_smbus` (for the 1-byte-address case). The regmap config encodes the address width and page size. Then the driver implements two callbacks for `nvmem` (Ch 65.7 below) and that's most of it.

### Probe walk

```c
/* drivers/misc/eeprom/at24.c — simplified */
static int at24_probe(struct i2c_client *client)
{
    struct at24_data *at24;
    const struct at24_chip_data *cdata;

    /* 1. Resolve chip parameters: byte_len, page_size, flags, addr_width */
    cdata = at24_get_chip_data(client);  /* from match table or DT */

    at24 = devm_kzalloc(&client->dev, sizeof(*at24), GFP_KERNEL);
    at24->byte_len  = cdata->byte_len;
    at24->page_size = cdata->page_size;

    /* 2. Build a regmap matching this chip's protocol */
    struct regmap_config regmap_config = {
        .val_bits = 8,
        .reg_bits = cdata->flags & AT24_FLAG_ADDR16 ? 16 : 8,
        .disable_locking = true,
    };
    at24->regmap = devm_regmap_init_i2c(client, &regmap_config);

    /* 3. Allocate "regions" — one regmap per I²C address when chip spans multiple */
    /* (large AT24s like 64 KB take multiple I²C addresses; the driver creates
       a regmap per address and routes reads/writes by offset) */
    at24->bank_addr_shift = ...;
    /* ... */

    /* 4. Set up nvmem-config */
    struct nvmem_config nvmem_config = {
        .name        = ...,
        .type        = NVMEM_TYPE_EEPROM,
        .read_only   = is_writeprotected(at24),
        .word_size   = 1,
        .size        = at24->byte_len,
        .reg_read    = at24_read,
        .reg_write   = at24_write,
        .priv        = at24,
    };
    at24->nvmem = devm_nvmem_register(&client->dev, &nvmem_config);

    return 0;
}
```

### The read callback

```c
static int at24_read(void *priv, unsigned int off, void *val, size_t count)
{
    struct at24_data *at24 = priv;

    while (count) {
        struct regmap *regmap;
        size_t addr;
        size_t chunk;

        /* Pick the right regmap (i.e., the right I²C address)
         * for chips that span multiple I²C addresses. */
        regmap = at24_select_regmap(at24, &off);
        addr = off & 0xFF;       /* mask to the device's address space */

        /* Cap each chunk to whatever the controller can do in one go */
        chunk = min(count, AT24_MAX_READ);

        int err = regmap_bulk_read(regmap, addr, val, chunk);
        if (err) return err;

        val   += chunk;
        off   += chunk;
        count -= chunk;
    }
    return 0;
}
```

Reads don't need to respect page boundaries — only writes do. The wrap-within-page behaviour applies to programming, not reading. So `at24_read` is a simple linear loop.

### The write callback (the interesting one)

```c
static int at24_write(void *priv, unsigned int off, void *val, size_t count)
{
    struct at24_data *at24 = priv;
    int err;

    mutex_lock(&at24->lock);

    while (count) {
        size_t page_offset = off & (at24->page_size - 1);
        size_t in_page     = at24->page_size - page_offset;
        size_t chunk       = min(count, in_page);

        struct regmap *regmap = at24_select_regmap(at24, &off);
        unsigned int addr = off & 0xFF;

        /* Bulk-write up to one page worth at this offset */
        err = regmap_bulk_write(regmap, addr, val, chunk);
        if (err) break;

        /* ACK-poll: issue dummy reads of register 0 until they succeed.
         * The chip NACKs until its internal write cycle finishes (~5 ms). */
        unsigned long deadline = jiffies + msecs_to_jiffies(at24->write_max_ms);
        do {
            u8 dummy;
            err = regmap_read(regmap, 0, &dummy);
            if (err == 0) break;   /* ACK received: write cycle done */
            usleep_range(100, 500);
        } while (time_before(jiffies, deadline));

        if (err) break;

        val   += chunk;
        off   += chunk;
        count -= chunk;
    }

    mutex_unlock(&at24->lock);
    return err;
}
```

Two things to notice:

1. **The page-boundary split**: `chunk = min(count, at24->page_size - page_offset)` ensures we never cross a page boundary in one transaction.
2. **ACK polling**: the loop with `regmap_read(regmap, 0, &dummy)` tests whether the chip ACKs *yet*. While the chip is writing internally, it NACKs every transaction; the loop spins (yielding with `usleep_range`) until it gets an ACK.

That is the whole driver. Around 50 lines of real code. The rest is parameter tables, DT plumbing, and edge cases (multi-address chips, write-protect GPIOs).

## 65.6  Writing an I²C EEPROM driver from scratch

Let's prove we understand by writing the minimal version. ~150 lines, no regmap, no nvmem, just an `i2c_driver` + chardev. Targets AT24C02 specifically.

`myeeprom.c`:

```c
#include <linux/init.h>
#include <linux/module.h>
#include <linux/i2c.h>
#include <linux/cdev.h>
#include <linux/fs.h>
#include <linux/uaccess.h>
#include <linux/delay.h>

#define EEPROM_SIZE     256
#define EEPROM_PAGE     8
#define WRITE_MAX_MS    25      /* upper bound on internal write cycle + slack */

struct myeeprom {
    struct i2c_client *client;
    struct cdev cdev;
    dev_t devid;
    struct class *class;
    struct mutex lock;
};

/* === Low-level: write reg-address, then read N bytes === */

static int me_read(struct myeeprom *e, u8 off, u8 *buf, size_t count)
{
    struct i2c_msg msgs[2] = {
        { .addr = e->client->addr, .flags = 0,        .len = 1, .buf = &off },
        { .addr = e->client->addr, .flags = I2C_M_RD, .len = count, .buf = buf },
    };
    int n = i2c_transfer(e->client->adapter, msgs, 2);
    return n == 2 ? 0 : (n < 0 ? n : -EIO);
}

/* === Mid-level: write one page (caller must ensure no boundary crossing) === */

static int me_write_page(struct myeeprom *e, u8 off, const u8 *buf, size_t count)
{
    u8 tx[1 + EEPROM_PAGE];
    struct i2c_msg msg = {
        .addr = e->client->addr, .flags = 0,
        .len = count + 1, .buf = tx,
    };
    int n;
    unsigned long deadline;

    if (count == 0 || count > EEPROM_PAGE) return -EINVAL;
    if ((off & (EEPROM_PAGE - 1)) + count > EEPROM_PAGE) return -EINVAL;

    tx[0] = off;
    memcpy(tx + 1, buf, count);

    n = i2c_transfer(e->client->adapter, &msg, 1);
    if (n != 1) return n < 0 ? n : -EIO;

    /* ACK-poll: keep issuing 1-byte writes (just the address byte) until ACK */
    deadline = jiffies + msecs_to_jiffies(WRITE_MAX_MS);
    while (time_before(jiffies, deadline)) {
        u8 zero = 0;
        struct i2c_msg poll = { .addr = e->client->addr, .flags = 0,
                                .len = 1, .buf = &zero };
        n = i2c_transfer(e->client->adapter, &poll, 1);
        if (n == 1) return 0;
        usleep_range(200, 500);
    }
    return -ETIMEDOUT;
}

/* === Char-device fops === */

static int me_open(struct inode *inode, struct file *filp)
{
    struct myeeprom *e = container_of(inode->i_cdev, struct myeeprom, cdev);
    filp->private_data = e;
    return 0;
}

static ssize_t me_fops_read(struct file *filp, char __user *u,
                            size_t count, loff_t *ppos)
{
    struct myeeprom *e = filp->private_data;
    u8 kbuf[EEPROM_SIZE];
    int err;

    if (*ppos >= EEPROM_SIZE) return 0;
    if (*ppos + count > EEPROM_SIZE) count = EEPROM_SIZE - *ppos;

    mutex_lock(&e->lock);
    err = me_read(e, *ppos, kbuf, count);
    mutex_unlock(&e->lock);
    if (err) return err;

    if (copy_to_user(u, kbuf, count)) return -EFAULT;
    *ppos += count;
    return count;
}

static ssize_t me_fops_write(struct file *filp, const char __user *u,
                             size_t count, loff_t *ppos)
{
    struct myeeprom *e = filp->private_data;
    u8 kbuf[EEPROM_SIZE];
    int err = 0;
    size_t done = 0;

    if (*ppos >= EEPROM_SIZE) return -ENOSPC;
    if (*ppos + count > EEPROM_SIZE) count = EEPROM_SIZE - *ppos;

    if (copy_from_user(kbuf, u, count)) return -EFAULT;

    mutex_lock(&e->lock);
    while (done < count) {
        size_t page_off = (*ppos + done) & (EEPROM_PAGE - 1);
        size_t chunk    = min((size_t)(EEPROM_PAGE - page_off), count - done);
        err = me_write_page(e, *ppos + done, kbuf + done, chunk);
        if (err) break;
        done += chunk;
    }
    mutex_unlock(&e->lock);
    if (err) return err;

    *ppos += done;
    return done;
}

static loff_t me_fops_llseek(struct file *filp, loff_t off, int whence)
{
    return fixed_size_llseek(filp, off, whence, EEPROM_SIZE);
}

static const struct file_operations me_fops = {
    .owner   = THIS_MODULE,
    .open    = me_open,
    .read    = me_fops_read,
    .write   = me_fops_write,
    .llseek  = me_fops_llseek,
};

/* === Probe / Remove === */

static int me_probe(struct i2c_client *client)
{
    struct myeeprom *e;
    u8 probe_byte;
    int err;

    e = devm_kzalloc(&client->dev, sizeof(*e), GFP_KERNEL);
    if (!e) return -ENOMEM;
    e->client = client;
    mutex_init(&e->lock);

    /* Sanity read: does anything respond at this address? */
    err = me_read(e, 0, &probe_byte, 1);
    if (err) return dev_err_probe(&client->dev, err, "EEPROM not responding\n");
    dev_info(&client->dev, "myeeprom alive at 0x%02x (byte0=0x%02x)\n",
             client->addr, probe_byte);

    err = alloc_chrdev_region(&e->devid, 0, 1, "myeeprom");
    if (err) return err;
    cdev_init(&e->cdev, &me_fops);
    e->cdev.owner = THIS_MODULE;
    err = cdev_add(&e->cdev, e->devid, 1);
    if (err) goto unreg;

    e->class = class_create("myeeprom");
    if (IS_ERR(e->class)) { err = PTR_ERR(e->class); goto del_cdev; }
    device_create(e->class, NULL, e->devid, NULL, "myeeprom");

    i2c_set_clientdata(client, e);
    return 0;

del_cdev:
    cdev_del(&e->cdev);
unreg:
    unregister_chrdev_region(e->devid, 1);
    return err;
}

static void me_remove(struct i2c_client *client)
{
    struct myeeprom *e = i2c_get_clientdata(client);
    device_destroy(e->class, e->devid);
    class_destroy(e->class);
    cdev_del(&e->cdev);
    unregister_chrdev_region(e->devid, 1);
}

static const struct of_device_id me_of_match[] = {
    { .compatible = "linuxlearn,myeeprom" },
    { }
};
MODULE_DEVICE_TABLE(of, me_of_match);

static const struct i2c_device_id me_id[] = {
    { "myeeprom", 0 },
    { }
};
MODULE_DEVICE_TABLE(i2c, me_id);

static struct i2c_driver me_driver = {
    .driver = {
        .name = "myeeprom",
        .of_match_table = me_of_match,
    },
    .probe    = me_probe,
    .remove   = me_remove,
    .id_table = me_id,
};
module_i2c_driver(me_driver);

MODULE_LICENSE("GPL");
```

DT:

```dts
&i2c1 {
    eeprom@50 {
        compatible = "linuxlearn,myeeprom";
        reg = <0x50>;
    };
};
```

Build, load, exercise:

```
[root@pa-mini:~]# insmod myeeprom.ko
[root@pa-mini:~]# dmesg | tail -1
myeeprom 1-0050: myeeprom alive at 0x50 (byte0=0xff)

[root@pa-mini:~]# echo -n "Hello world!" > /dev/myeeprom
[root@pa-mini:~]# dd if=/dev/myeeprom bs=12 count=1
Hello world!
12+0 records in
12+0 records out

[root@pa-mini:~]# hexdump -C /dev/myeeprom | head -1
00000000  48 65 6c 6c 6f 20 77 6f  72 6c 64 21 ff ff ff ff  |Hello world!....|
```

The page-aligned write loop handled the "Hello world!" (12 bytes starting at offset 0, which crosses the 8-byte page boundary) correctly — split into [0..7] and [8..11], each its own page-program with ACK-poll.

What we got, in ~150 lines:
- I²C read/write split correctly at page boundaries.
- ACK polling for write completion.
- Mutex-protected chardev.
- Probe-time sanity check.

What we *skipped* compared to `at24`:
- nvmem integration (so the FEC can't read MAC from us — we don't appear under `/sys/bus/nvmem/`).
- Multi-address chips (AT24C512 spans 4 I²C addresses).
- 2-byte addressing (we hardcoded 1-byte AT24C02).
- Write-protect GPIO.
- Sysfs binary attribute (we exposed via /dev only).
- read-only mode for DT `read-only` boolean.

## 65.7  Now: the mainline driver and nvmem

DT for the mainline driver:

```dts
&i2c1 {
    eeprom: eeprom@50 {
        compatible = "atmel,24c02";
        reg = <0x50>;
        pagesize = <8>;
        #address-cells = <1>;
        #size-cells = <1>;

        /* nvmem cells — typed sub-regions */
        mac_address: mac@0 {
            reg = <0x0 0x6>;     /* 6 bytes at offset 0 */
        };
        serial_number: serial@10 {
            reg = <0x10 0x10>;   /* 16 bytes at offset 0x10 */
        };
    };
};

&fec1 {
    nvmem-cells = <&mac_address>;
    nvmem-cell-names = "mac-address";
    /* ... */
};
```

The mainline `at24` driver registers an nvmem provider. The FEC driver consumes the `mac-address` cell at probe — six bytes from offset 0 become eth0's MAC address. **No board-specific kernel code**. Production: write the MAC in the factory test, the kernel picks it up automatically every boot.

For SPI 25LC512:

```dts
&ecspi3 {
    eeprom@1 {
        compatible = "microchip,25lc512", "atmel,at25";
        reg = <1>;
        spi-max-frequency = <10000000>;
        size = <65536>;
        pagesize = <128>;
        address-width = <16>;
    };
};
```

The `"atmel,at25"` fallback covers most SPI EEPROMs with the same protocol; the explicit `size`, `pagesize`, `address-width` tell the driver the geometry.

After probe, the EEPROM exposes a binary attribute (sysfs-bin):

```
[root@pa-mini:~]# ls /sys/bus/i2c/devices/1-0050/
driver/  eeprom  name  ...

[root@pa-mini:~]# hexdump -C /sys/bus/i2c/devices/1-0050/eeprom | head
00000000  ff ff ff ff ff ff ff ff  ff ff ff ff ff ff ff ff  |................|

[root@pa-mini:~]# echo -n "SN12345" > /tmp/serial
[root@pa-mini:~]# dd if=/tmp/serial of=/sys/bus/i2c/devices/1-0050/eeprom bs=1 seek=0
[root@pa-mini:~]# dd if=/sys/bus/i2c/devices/1-0050/eeprom bs=1 count=7
SN12345
```

## 65.8  Factory programming workflow

```sh
# 1. Generate per-unit serial + MAC
SERIAL=$(uuidgen | tr -d - | cut -c1-12)
MAC=$(printf '02:%02x:%02x:%02x:%02x:%02x' \
      $((RANDOM % 256)) $((RANDOM % 256)) $((RANDOM % 256)) \
      $((RANDOM % 256)) $((RANDOM % 256)))
echo "Serial: $SERIAL  MAC: $MAC"

# 2. Write MAC (6 bytes at offset 0)
echo "$MAC" | awk -F: '{for(i=1;i<=NF;i++) printf "%c", strtonum("0x"$i)}' \
    > /sys/bus/i2c/devices/1-0050/eeprom

# 3. Write serial (16 bytes at offset 0x10)
printf "%-16s" "$SERIAL" | dd of=/sys/bus/i2c/devices/1-0050/eeprom \
    bs=1 seek=16 conv=notrunc 2>/dev/null

# 4. Verify
xxd /sys/bus/i2c/devices/1-0050/eeprom | head -2

# 5. (Optional, 25LC512) drive WP pin high
echo 1 > /sys/class/gpio/.../wp_value
```

After factory: WP held high, field firmware can read but not write. Reboot → kernel's nvmem cells pull the MAC into the FEC → networking comes up with the right address.

## 65.9  Lab

1. **Probe with i2c-tools first.** `i2cdetect -y 1` — expect 0x50. `i2cdump -y 1 0x50 b` — expect all 0xFF on virgin chip.
2. **Build and load `myeeprom.ko`.** Write 12 bytes ("Hello world!"), read back. Verify it survives reboot.
3. **Provoke the page-boundary bug.** Modify `me_fops_write` to skip the split — write 12 bytes in one `me_write_page` call (relax the validation `if`). Observe data corruption: bytes 8–11 overwrite bytes 0–3 of page 0, not bytes 0–3 of page 1. Restore the split.
4. **ACK-poll timing.** Add `ktime` measurement around the ACK-poll loop. With a 5 ms internal cycle, expect ~5 ms per write.
5. **Switch to mainline `at24`.** Unload `myeeprom`; bind the same chip with `compatible = "atmel,24c02"`. Verify `/sys/bus/i2c/devices/1-0050/eeprom` appears. Same chip, more features available.
6. **nvmem MAC.** Configure DT as in §65.7. Boot; `ip link show eth0`; verify the MAC matches the bytes you wrote at offset 0. This is the production pattern.

## 65.10  Pitfalls

- **Wrong pagesize.** Writes across page boundaries wrap silently. Always set `pagesize = <N>` in DT (mainline) or hardcode correctly (from-scratch); the AT24C512's 128-byte pages are not the same as AT24C02's 8-byte pages.
- **Address-width confusion.** AT24C02 uses 1-byte address; AT24C512 uses 2-byte. The mainline driver derives this from chip size; the from-scratch driver hardcodes one or the other.
- **5 ms write cycle not waited for.** Issuing the next command before the cycle finishes → NACK → kernel error. The ACK-poll loop is mandatory.
- **Multiple EEPROMs on one bus.** Strap each chip's A0/A1/A2 differently to give unique addresses (0x50–0x57). If two chips share an address, neither responds correctly.
- **WP pin floating.** Reads return all-0xFF and writes silently fail. Tie WP low, or wire it to a GPIO that defaults to low.
- **Wrong nvmem cell offset.** Driver reads garbage as the MAC. Cross-check `reg = <offset size>` against your factory-write script.
- **`/WP` and software write-protect register coexist.** Some chips have *both* a hardware /WP pin *and* a software status-register write-protect. Make sure both allow writes.
- **The "WC" pin.** Some EEPROMs name it WC (write control) instead of WP. Same idea, different polarity sometimes — read the datasheet.

## 65.11  Going deeper

- **`drivers/misc/eeprom/at24.c`** — the production driver. ~1000 lines. Read after writing the from-scratch version above — you'll recognise every block.
- **`drivers/misc/eeprom/at25.c`** — SPI EEPROM driver.
- **`Documentation/devicetree/bindings/eeprom/at24.yaml`** — DT binding.
- **`Documentation/devicetree/bindings/nvmem/nvmem.yaml`** — nvmem provider binding.
- **`Documentation/ABI/testing/sysfs-bus-nvmem`** — nvmem sysfs.
- **AT24C02 datasheet** (Microchip) — has timing diagrams for the ACK-poll loop on page 11.

> Next chapter: **Chapter 66 — SD card and eMMC deep dive.** A different beast: you wouldn't write an MMC host controller driver from scratch in 200 lines (the protocol has 40+ commands, multiple state machines, signal-voltage switching, tuning). Instead we'll trace a single `read()` through the kernel's MMC stack — host driver → core → block layer — to see how the layers fit, and inspect EXT_CSD to manage device life. That gets you "understand the framework" without "rewrite the framework."
