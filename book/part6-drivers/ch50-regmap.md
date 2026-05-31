---
chapter: 50
title: regmap — the register-access abstraction
part: VI — Driver development
estimated_pages: 14
status: draft
---

# Chapter 50 — regmap

> **What:** **regmap** — the register-access layer that sits between your driver and the bus (I²C, SPI, MMIO, or a custom one). You describe the chip's register layout once; regmap gives you `regmap_read(rm, reg, &val)` and `regmap_write(rm, reg, val)` that just work, with optional caching, locking, debugging, and bulk transfers all handled for you.
> **Why:** before regmap (~2011), every driver duplicated the same boilerplate: an I²C wrapper, an SPI wrapper, register-cache invalidation, byte-swap dances, mutex protection. The same 40 lines were copy-pasted across hundreds of drivers, with subtle bugs each time. Regmap factored it out. A modern driver — especially an audio codec or PMIC with hundreds of registers — uses regmap exclusively and is half as long as it would have been pre-regmap.
> **Focus:** **declare-then-use**. You provide a `regmap_config` describing your chip's registers (bit widths, ranges, which are volatile vs cached, which are read-only) and a one-call regmap_init for your bus. From there every register access goes through the same two functions. Get the config right and the rest is mechanical.

## 50.1  Why regmap exists

A typical pre-regmap driver had code like this:

```c
/* Read register `reg` over I²C */
static int my_i2c_read(struct my_priv *p, u8 reg, u8 *val)
{
    struct i2c_msg msgs[2] = {
        { .addr = p->client->addr, .flags = 0,        .len = 1, .buf = &reg },
        { .addr = p->client->addr, .flags = I2C_M_RD, .len = 1, .buf = val  },
    };
    int n = i2c_transfer(p->client->adapter, msgs, 2);
    return n == 2 ? 0 : -EIO;
}

static int my_i2c_write(struct my_priv *p, u8 reg, u8 val)
{
    u8 tx[2] = { reg, val };
    return i2c_master_send(p->client, tx, 2) == 2 ? 0 : -EIO;
}

/* Now repeat for SPI, with mode 0, MSB first, etc., for the SPI variant of the chip... */
```

…repeated for every chip. Then you'd add:
- A mutex around register accesses (otherwise two threads racing the bus = corruption).
- A cache of writeable registers so you don't re-read after every write.
- Bulk-write support to set 4 registers in one transaction.
- Bit-field helpers to modify a single bit of a register.
- Endianness handling for chips with mixed-width registers.

That's a hundred lines of identical-feeling code. Regmap factors it all out. You declare *what your chip looks like*; regmap handles *how to talk to it*.

## 50.2  The minimal regmap

For a typical I²C chip with 8-bit registers and 8-bit register addresses:

```c
#include <linux/regmap.h>

static const struct regmap_config my_regmap_config = {
    .reg_bits = 8,
    .val_bits = 8,
    .max_register = 0xFF,
};

static int my_probe(struct i2c_client *client)
{
    struct regmap *regmap;
    unsigned int val;
    int err;

    regmap = devm_regmap_init_i2c(client, &my_regmap_config);
    if (IS_ERR(regmap))
        return PTR_ERR(regmap);

    err = regmap_read(regmap, 0xD0, &val);
    if (err)
        return err;
    dev_info(&client->dev, "chip-id = 0x%02x\n", val);

    err = regmap_write(regmap, 0xF4, 0x27);    /* configure */
    if (err)
        return err;

    return 0;
}
```

That's the whole pattern. `devm_regmap_init_i2c(client, &config)` creates a regmap bound to this I²C client; `regmap_read` / `regmap_write` do all the bus dancing.

For SPI, the only change is the init call:

```c
regmap = devm_regmap_init_spi(spi, &my_regmap_config);
```

For MMIO (a memory-mapped peripheral on the SoC):

```c
regmap = devm_regmap_init_mmio(&pdev->dev, base, &my_regmap_config);
```

The rest of the driver — `regmap_read`, `regmap_write`, `regmap_update_bits` — is *identical*. The driver becomes bus-agnostic.

## 50.3  Variations of the config

Real chips have quirks. The config struct accommodates them.

### Different register widths

```c
.reg_bits = 16,           /* 16-bit register address */
.val_bits = 16,           /* 16-bit value */
.reg_format_endian = REGMAP_ENDIAN_BIG,
.val_format_endian = REGMAP_ENDIAN_BIG,
```

Audio codecs commonly have 16-bit register space and 16-bit values, big-endian wire format.

### SPI command bits

Many SPI chips encode read/write in the top bit of the register address:

```c
.reg_bits = 8,
.val_bits = 8,
.read_flag_mask  = 0x80,    /* OR'd into reg for reads */
.write_flag_mask = 0x00,    /* OR'd into reg for writes */
```

When you call `regmap_read(rm, 0x40, &val)`, regmap actually sends `0xC0` on the wire (0x80 | 0x40). You don't think about it.

### Volatile / writable / readable ranges

Not every register is the same. ID registers are read-only; status registers change without you writing; some addresses are reserved. Regmap can cache writeable, non-volatile registers — saving bus traffic.

```c
static bool my_readable(struct device *dev, unsigned int reg)
{
    return reg <= 0x7F;
}

static bool my_writeable(struct device *dev, unsigned int reg)
{
    return reg >= 0x40 && reg <= 0x7F;
}

static bool my_volatile(struct device *dev, unsigned int reg)
{
    return reg == 0x00 || reg == 0x01;     /* status regs */
}

static const struct regmap_config my_regmap_config = {
    .reg_bits = 8,
    .val_bits = 8,
    .max_register = 0xFF,
    .readable_reg = my_readable,
    .writeable_reg = my_writeable,
    .volatile_reg = my_volatile,
    .cache_type = REGCACHE_RBTREE,
};
```

With `cache_type = REGCACHE_RBTREE`, regmap caches all non-volatile, non-read-only registers in a red-black tree. A `regmap_read` of a cached register returns the cached value instantly; only volatile registers hit the bus. A `regmap_write` updates the cache *and* the bus; if power is restored after suspend, `regcache_sync(regmap)` flushes the cache back to the chip.

This last point — `regcache_sync` — is a huge win for power management. After resume, instead of re-reading every config register, the driver calls `regcache_sync` and regmap replays only the registers whose cached value differs from defaults.

Three cache types:

- `REGCACHE_NONE` — no caching; every access hits the bus. Default.
- `REGCACHE_RBTREE` — red-black tree; sparse register space, good for chips with thousands of registers used sparsely.
- `REGCACHE_FLAT` — flat array; dense register space, fastest, good for chips with <128 registers all used.

### Default values

Combined with caching, you can provide the chip's register power-on defaults. Regmap uses these to decide what to push to hardware on `regcache_sync`:

```c
static const struct reg_default my_defaults[] = {
    { 0x40, 0x10 },
    { 0x41, 0x00 },
    { 0x42, 0xFF },
    /* ... */
};

static const struct regmap_config my_regmap_config = {
    /* ... */
    .reg_defaults = my_defaults,
    .num_reg_defaults = ARRAY_SIZE(my_defaults),
};
```

## 50.4  The API — what you'll actually call

```c
int regmap_read(struct regmap *rm, unsigned int reg, unsigned int *val);
int regmap_write(struct regmap *rm, unsigned int reg, unsigned int val);

int regmap_update_bits(struct regmap *rm, unsigned int reg,
                       unsigned int mask, unsigned int val);
/* atomic read-modify-write: val = (cur & ~mask) | (val & mask) */

int regmap_bulk_read(struct regmap *rm, unsigned int reg, void *val, size_t count);
int regmap_bulk_write(struct regmap *rm, unsigned int reg, const void *val, size_t count);
/* sequence of count registers starting at reg */

int regmap_multi_reg_write(struct regmap *rm, const struct reg_sequence *regs, int num);
/* a list of (reg, val) pairs, written in one go */
```

For one-shot ops, `regmap_read` and `regmap_write`. For bit twiddling, `regmap_update_bits`. For initialisation of many registers in one go, `regmap_multi_reg_write` with a static `reg_sequence` array.

Example — a chip init sequence:

```c
static const struct reg_sequence my_init_sequence[] = {
    { 0x40, 0x00 },        /* disable */
    { 0x41, 0x80 },        /* enable mode */
    { 0x42, 0x33 },        /* set sample rate */
    { 0x43, 0x05 },        /* set gain */
    { 0x40, 0x01 },        /* enable */
};

err = regmap_multi_reg_write(regmap, my_init_sequence,
                              ARRAY_SIZE(my_init_sequence));
```

Six bus transactions but one line of driver code.

## 50.5  regmap + IIO + interrupts — the full pattern

Here's a sketch of a complete modern driver — say, an environmental sensor — combining everything from Ch 36–49:

```c
struct mysensor {
    struct regmap *regmap;
    int irq;
};

static const struct regmap_config mysensor_regmap_config = {
    .reg_bits = 8,
    .val_bits = 8,
    .max_register = 0xFF,
    .cache_type = REGCACHE_RBTREE,
};

static int mysensor_read_raw(struct iio_dev *idev, ...)
{
    struct mysensor *p = iio_priv(idev);
    unsigned int hi, lo;

    switch (info) {
    case IIO_CHAN_INFO_RAW:
        regmap_read(p->regmap, REG_DATA_HI, &hi);
        regmap_read(p->regmap, REG_DATA_LO, &lo);
        *val = (hi << 8) | lo;
        return IIO_VAL_INT;
    /* ... */
    }
}

static irqreturn_t mysensor_irq(int irq, void *data)
{
    struct iio_dev *idev = data;
    /* read data, push to buffer ... */
    iio_trigger_notify_done(idev->trig);
    return IRQ_HANDLED;
}

static int mysensor_probe(struct i2c_client *client, ...)
{
    struct iio_dev *idev = devm_iio_device_alloc(&client->dev, sizeof(struct mysensor));
    struct mysensor *p = iio_priv(idev);

    p->regmap = devm_regmap_init_i2c(client, &mysensor_regmap_config);
    /* configure chip */
    regmap_multi_reg_write(p->regmap, mysensor_init_seq, ...);

    /* request irq */
    devm_request_threaded_irq(&client->dev, gpiod_to_irq(...), NULL, mysensor_irq, ...);

    idev->name = "mysensor";
    idev->info = &mysensor_iio_info;
    idev->channels = mysensor_channels;
    /* ... */
    return devm_iio_device_register(&client->dev, idev);
}
```

Maybe 200 lines total. The same chip, hand-written without regmap and without IIO, would be 600+. The frameworks are leverage.

## 50.6  Debug: /sys/kernel/debug/regmap

With `CONFIG_REGMAP_DEBUG=y`, every regmap is exposed via debugfs:

```
[root@pa-mini:~]# ls /sys/kernel/debug/regmap/
1-0076

[root@pa-mini:~]# cd /sys/kernel/debug/regmap/1-0076
[root@pa-mini:~]# ls
cache_only  cache_bypass  name  range  registers  rbtree

[root@pa-mini:~]# cat name
1-0076

[root@pa-mini:~]# cat registers
00: 60
01: 00
02: 00
...
F4: 27
```

`registers` dumps the cached or read register values. `cache_only = 1` makes subsequent regmap accesses return cached values without touching the bus (useful for debugging "what does my driver *think* the chip looks like?"). `cache_bypass = 1` forces every access to the bus (useful for "is the bus actually working?").

For interactive driver debugging during bring-up, this is invaluable.

## 50.7  Lab

1. **Convert a previous driver to regmap.** Take your AT24 driver from Ch 46 — replace the `i2c_transfer` calls with regmap. Compare line count.
2. **Add a register cache.** Mark which registers are volatile; build a regmap with `REGCACHE_RBTREE`. Observe (via `cache_only`) what gets cached.
3. **Use `regmap_update_bits`.** Find a chip with bitfield-packed registers (e.g., MCP23017 — IODIRA is direction per pin in 8 bits). Set one bit without reading the rest manually.
4. **Inspect with debugfs.** `cat /sys/kernel/debug/regmap/<name>/registers`. Flip cache modes and observe behavior.
5. **regcache_sync after suspend.** In an `.suspend` callback, `regcache_mark_dirty(regmap)`; in `.resume`, `regcache_sync(regmap)`. Confirm the chip's registers are restored after a `echo mem > /sys/power/state` cycle.

## 50.8  Pitfalls

- **Wrong `reg_bits` or `val_bits`.** Symptom: writes appear to "work" but reads come back wrong, or two-register chips return garbage. Check the chip's datasheet bus-protocol section carefully.
- **`read_flag_mask` for SPI.** If the chip uses the top bit as R/W, you must set this. Symptom: reads return zeros (the chip thinks every transaction is a write).
- **Caching a volatile register.** Subsequent reads return stale data. Always mark status/event registers as volatile.
- **Not marking the read-only registers as such.** `regmap_write` to a read-only register silently fails on the chip, but regmap still caches the value. Next read returns the cached (wrong) value. Always declare readability/writability.
- **`regcache_sync` without `regcache_mark_dirty` first.** `sync` only pushes registers that have been marked dirty since the last sync. After a real power-loss/restore, mark dirty first.
- **Mixing regmap and direct bus access on the same chip.** Don't. Pick one. The cache will diverge from the chip.
- **Forgetting to free the regmap.** With `devm_regmap_init_*`, you don't — but without `devm_`, you must `regmap_exit` in remove.
- **Endianness mismatch.** Chip is big-endian, driver assumes little-endian. Symptom: 16-bit values appear byte-swapped. Set `reg_format_endian = REGMAP_ENDIAN_BIG` in config.

## 50.9  Going deeper

- **`Documentation/driver-api/regmap.rst`** — the regmap kernel documentation.
- **`include/linux/regmap.h`** — the API. Skim once for the full set of functions.
- **`drivers/base/regmap/`** — implementation. `regcache-rbtree.c`, `regcache-flat.c` are short and instructive.
- **`drivers/iio/pressure/bmp280-core.c`** — clean regmap + IIO example.
- **`drivers/mfd/`** — MFD (multi-function device) drivers heavily use regmap for chip-wide register layouts shared across cell drivers.
- **`sound/soc/codecs/wm8960.c`** — a real audio codec driver showing what 200+ registers looks like with regmap.

---

> **End of Phase 2 (Ch 44–50).** You now have the seven foundational subsystems: GPIO/pinctrl, input, I²C, SPI, PWM/RTC, IIO, regmap. With these, almost every peripheral driver in the kernel becomes legible. The remaining Part VI chapters (51–55I) layer on DMA, watchdog, power management, networking, sound, display, USB, kernel timers, and PREEMPT_RT — but the *shape* of every one of those drivers is now familiar.

> Next chapter: **Chapter 51 — DMA.** When CPU-driven memcpy is too slow, the DMA controller takes over. The kernel's `dmaengine` framework gives drivers a portable API to set up and submit transfers across any SoC's DMA hardware.
