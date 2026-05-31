---
chapter: 77
title: 1-Wire sensors (DS18B20 / DHT22)
part: VII — Device cookbook
estimated_pages: 18
status: draft
---

# Chapter 77 — 1-Wire sensors

> **What:** Maxim's **1-Wire** protocol — one digital pin (plus ground) carries bidirectional half-duplex data with timing-based bit framing. The well-supported case: **DS18B20** (digital thermometer, real 1-Wire, kernel `w1` subsystem). The pretender: **DHT22** (single-wire T/H, *not* 1-Wire, hostile to Linux GPIO timing). For DS18B20: protocol, the `w1` master / slave architecture, mainline driver internals, and a from-scratch w1-slave driver. For DHT22: a brutally honest "Linux is the wrong host" discussion plus what to do instead.
> **Why:** 1-Wire is the cheap, long-cable, parasitically-powered alternative to I²C. A 30-meter cable with 10 DS18B20s on it works. *Real* 1-Wire devices (with proper protocol implementations) are kernel-friendly. DHT22 borrows the wire and the parasitic power but invented its own timing — and that timing requires µs-accurate edge detection that Linux GPIO can't reliably deliver.
> **Focus:** **the master must generate tightly-timed pulse widths** (15 µs reset, 60 µs slot, 1 µs sample window). For DS18B20 this is done by the **w1 master** driver — usually a "GPIO bit-bang" master with PREEMPT_RT helping, or a hardware UART repurposed as a w1 master. The slave devices live in `drivers/w1/slaves/`. Get the master right and slaves are trivial.

## 77.1  1-Wire protocol — what's on the wire

1-Wire uses a single GPIO with a ~4.7 kΩ pull-up to 3.3 V. Idle = high. The master pulls low for specific durations to send bits and to query slaves. Slaves also pull low to respond, sharing the same wire.

### Reset / Presence

```
   master pulls LOW for ≥ 480 µs            ← RESET
   master releases (pull-up takes line HIGH)
   ... 15..60 µs settling ...
   if a slave is present, it pulls LOW       ← PRESENCE
   for 60..240 µs, then releases.
```

The master samples the line at ~60 µs after release: low = at least one slave present.

### Write 1 / Write 0 bits

```
   Write 1:
       master pulls LOW for 1..15 µs, then releases.
       Slave samples at ~30 µs after master pulls low; sees HIGH → reads 1.

   Write 0:
       master pulls LOW for 60..120 µs.
       Slave samples at ~30 µs after master pulls low; still LOW → reads 0.
```

The slave's sample point (~30 µs) discriminates 1 vs 0 based on whether the line has recovered.

### Read bit

```
   master pulls LOW for 1..15 µs, then releases.
   If slave wants to send 0, it keeps the line LOW for ~30 µs.
   If slave wants to send 1, it leaves the line HIGH (pull-up).
   Master samples at ~13 µs after starting the pulse:
       LOW = 0, HIGH = 1.
```

The whole protocol is timing-based; **edge detection is not the same as edge timing**. The host must drive transitions with ±5 µs accuracy.

### Standard commands

After a reset/presence, the master sends 8-bit commands LSB-first:

| Command | Hex | Purpose |
|---------|-----|---------|
| READ ROM | 0x33 | Read slave's 64-bit ROM ID (only one slave on bus) |
| SKIP ROM | 0xCC | Broadcast to all slaves (skip addressing) |
| MATCH ROM | 0x55 | Address one slave by ROM ID (8 bytes) |
| SEARCH ROM | 0xF0 | Enumerate slaves (multi-drop) |

After ROM-addressing, slave-specific function commands follow (e.g., DS18B20's 0x44 = Convert Temperature).

## 77.2  DS18B20 — a proper 1-Wire device

DS18B20 is a 9–12 bit programmable thermometer. Power 3.0–5.5 V, range −55 to +125 °C, accuracy ±0.5 °C at typical room temperature, ~750 ms for a 12-bit conversion.

Sequence to read temperature:

```
1. Reset + presence pulse.
2. SKIP ROM (0xCC) — assuming only one slave or broadcasting.
3. CONVERT T (0x44) — start a temperature conversion.
4. Wait 750 ms (or poll the bus: while the chip is converting, it holds the
   bus LOW; release means done).
5. Reset + presence pulse.
6. SKIP ROM (0xCC).
7. READ SCRATCHPAD (0xBE).
8. Read 9 bytes: temp_lsb, temp_msb, TH, TL, config, reserved×3, CRC.
9. Validate CRC-8.
10. Decode: temp_raw = (msb << 8) | lsb; temp_C = temp_raw / 16.0  (signed!).
```

Multiple DS18B20s on the same bus: SEARCH ROM enumerates them; MATCH ROM addresses each by 64-bit ID; otherwise SKIP ROM broadcasts to all.

## 77.3  The Linux `w1` subsystem

Source: `drivers/w1/`.

```
drivers/w1/
├── w1.c            ← core (slave registration, search)
├── w1_io.c         ← bus primitives (reset, read/write byte, sample)
├── w1_int.c        ← internal interfaces
├── w1_netlink.c    ← user-space notification
├── masters/        ← bus-master drivers
│   ├── w1-gpio.c
│   ├── ds2482.c     (I²C-to-1-Wire bridge)
│   ├── ds2490.c     (USB-to-1-Wire dongle)
│   └── omap_hdq.c   (TI's hardware w1 controller)
└── slaves/         ← slave drivers
    ├── w1_therm.c   (DS18B20, DS1822, DS28EA00)
    ├── w1_ds2406.c
    ├── w1_ds2438.c
    └── ...
```

**Two layers**: a *master* implements bus primitives; *slaves* are registered after enumeration.

### A master's contract

```c
struct w1_bus_master {
    void *data;
    u8  (*read_byte) (void *);
    void (*write_byte)(void *, u8);
    u8  (*read_bit)  (void *);
    void (*write_bit) (void *, u8);
    u8  (*touch_bit) (void *, u8);
    u8  (*reset_bus) (void *);
    /* ... */
};
```

A master can choose to implement either bit-level or byte-level primitives; the core synthesises the missing operations. A *GPIO bit-bang master* implements `reset_bus`, `read_bit`, `write_bit` using `gpiod_*` + `udelay`/`ndelay`; the core composes those into byte reads/writes.

### `w1-gpio` master

```c
/* drivers/w1/masters/w1-gpio.c — simplified */

static u8 w1_gpio_read_bit(void *data)
{
    struct w1_gpio_platform_data *pdata = data;
    u8 bit;

    /* Pull low for ~6 µs */
    gpiod_direction_output(pdata->gpiod, 0);
    udelay(6);
    /* Release; let pull-up recover */
    gpiod_direction_input(pdata->gpiod);
    udelay(9);    /* sample at ~15 µs after low pulse start */
    bit = gpiod_get_value(pdata->gpiod);
    udelay(55);   /* finish the slot */
    return bit;
}

static void w1_gpio_write_bit(void *data, u8 bit)
{
    struct w1_gpio_platform_data *pdata = data;
    if (bit) {
        gpiod_direction_output(pdata->gpiod, 0);
        udelay(6);
        gpiod_direction_input(pdata->gpiod);
        udelay(64);
    } else {
        gpiod_direction_output(pdata->gpiod, 0);
        udelay(60);
        gpiod_direction_input(pdata->gpiod);
        udelay(10);
    }
}

static u8 w1_gpio_reset_bus(void *data)
{
    struct w1_gpio_platform_data *pdata = data;
    u8 presence;

    gpiod_direction_output(pdata->gpiod, 0);
    udelay(480);
    gpiod_direction_input(pdata->gpiod);
    udelay(70);
    presence = gpiod_get_value(pdata->gpiod);
    udelay(410);
    return presence;
}
```

`udelay()` is **busy-wait**, not sleep. The whole sequence holds the CPU for ~70 µs (worst case) per bit. Reading the 9-byte scratchpad takes ~5 ms of busy-wait, during which other userspace can't preempt. Acceptable for "read every 5 seconds"; not acceptable for thousands of reads per second.

Crucially, `udelay` and the GPIO writes happen *with preemption disabled*. Without that protection, a scheduler tick mid-pulse would distort timing — bit becomes garbage. The `w1-gpio` driver wraps the bit operations in `local_irq_disable()` / `local_irq_enable()` around the timing-critical region.

This is why `w1-gpio` *works* on standard Linux: the master driver explicitly disables interrupts during each bit. The timing tolerance (1-Wire allows ±15 µs slop) absorbs the latency of one tick worth of pending IRQs.

### Slave enumeration

After registering a master, the w1 core starts a kthread that:

1. Issues SEARCH ROM (0xF0) periodically.
2. Walks the binary-tree search algorithm to enumerate all slave ROM IDs.
3. For each new ROM ID, looks up the *family code* (top byte) — 0x28 for DS18B20, 0x26 for DS2438, etc.
4. Looks up the corresponding slave driver; calls its `add_slave` callback.
5. The slave driver registers per-device sysfs attributes.

User-space sees:

```
/sys/bus/w1/devices/28-0000054321ab/   ← one DS18B20
  ├── temperature       (read this)
  ├── ext_power
  ├── eeprom_cmd
  ├── name
  └── ...

/sys/bus/w1/devices/w1_bus_master1/    ← the master
  ├── w1_master_slave_count
  ├── w1_master_slaves
  └── w1_master_search
```

A read of `/sys/bus/w1/devices/28-.../temperature` triggers the conversion + read sequence, returning ASCII milli-degrees:

```
[root@pa-mini:~]# cat /sys/bus/w1/devices/28-0000054321ab/temperature
23187
[root@pa-mini:~]# # → 23.187 °C
```

## 77.4  Writing a w1 slave driver from scratch

We won't rewrite the master (the bit-bang master is well-engineered already and re-doing it teaches little). Instead we'll write a **slave driver** for an imaginary family — say, a custom sensor with family code 0xA5 that returns 4 bytes when commanded with 0xCC, 0xBE.

The w1 core handles enumeration; we provide a `w1_family` with `add_slave` / `remove_slave` callbacks:

`my_w1_slave.c`:

```c
#include <linux/init.h>
#include <linux/module.h>
#include <linux/slab.h>
#include <linux/sysfs.h>
#include <linux/w1.h>

#define W1_FAMILY_LL_CUSTOM 0xA5
#define CMD_READ_DATA       0xBE   /* slave-specific function command */

static ssize_t value_show(struct device *dev, struct device_attribute *attr, char *buf)
{
    struct w1_slave *sl = dev_to_w1_slave(dev);
    u8 cmd[2];
    u8 rx[4];
    u32 value;

    mutex_lock(&sl->master->bus_mutex);

    if (w1_reset_select_slave(sl)) {
        mutex_unlock(&sl->master->bus_mutex);
        return -EIO;
    }

    cmd[0] = CMD_READ_DATA;
    w1_write_block(sl->master, cmd, 1);

    w1_read_block(sl->master, rx, 4);

    mutex_unlock(&sl->master->bus_mutex);

    /* Big-endian on the wire */
    value = (rx[0] << 24) | (rx[1] << 16) | (rx[2] << 8) | rx[3];
    return sprintf(buf, "%u\n", value);
}
static DEVICE_ATTR_RO(value);

static struct attribute *my_w1_attrs[] = {
    &dev_attr_value.attr,
    NULL,
};
ATTRIBUTE_GROUPS(my_w1);

static const struct w1_family_ops my_w1_fops = {
    .groups = my_w1_groups,
};

static struct w1_family my_w1_family = {
    .fid = W1_FAMILY_LL_CUSTOM,
    .fops = &my_w1_fops,
};

module_w1_family(my_w1_family);

MODULE_LICENSE("GPL");
MODULE_ALIAS("w1-family-" __stringify(W1_FAMILY_LL_CUSTOM));
```

That's it — 50 lines. The w1 core handles enumeration; when a slave with family code 0xA5 is discovered, the core calls our driver's `groups`, creating `/sys/bus/w1/devices/a5-XXXXXXX/value`.

Three w1-core helpers used:

- **`w1_reset_select_slave(sl)`** — reset bus, issue MATCH ROM with this slave's ID. Returns 0 on success.
- **`w1_write_block(master, buf, n)`** — write N bytes (each as 8 individual bit-write operations).
- **`w1_read_block(master, buf, n)`** — read N bytes.

These wrap the master's bit-level primitives. The slave driver doesn't see GPIO toggles at all — clean abstraction.

For comparison, the **mainline `w1_therm.c`** (DS18B20 slave) is ~1200 lines because it handles: family codes for multiple chips (DS18B20, DS1822, DS18S20, MAX31850), CRC validation, conversion timing with bus-power detection, resolution programming, alarm thresholds, EEPROM read/write, async conversions, multiple temperature-format conversions. The shape is the same as our 50-line version — just multiplied by features.

## 77.5  Setting up `w1-gpio` master in DT

```dts
onewire {
    compatible = "w1-gpio";
    gpios = <&gpio4 14 GPIO_ACTIVE_HIGH>;
    /* Optional: external pull-up control, parasitic mode, etc. */
};
```

`w1-gpio` master accepts a single `gpios` property (the data pin); the pull-up is assumed to be external (4.7 kΩ to 3.3 V). With slow polling and PREEMPT_RT, this works at 1-Wire's nominal timing on any GPIO that supports a few microseconds of `local_irq_disable()`.

Kernel config: `CONFIG_W1=y`, `CONFIG_W1_MASTER_GPIO=y`, `CONFIG_W1_SLAVE_THERM=y`.

Test:

```
[root@pa-mini:~]# ls /sys/bus/w1/devices/
28-0000054321ab    w1_bus_master1
[root@pa-mini:~]# cat /sys/bus/w1/devices/28-0000054321ab/temperature
23187
[root@pa-mini:~]# cat /sys/bus/w1/devices/w1_bus_master1/w1_master_slave_count
1
```

Long cables (10 m+) with multiple DS18B20s on a single GPIO — works.

## 77.6  DHT22 — the imposter, and why Linux is wrong

DHT22 ("AM2302") *uses the same physical wiring* as 1-Wire but **invents its own incompatible protocol**:

1. Master pulls low for 1–10 ms.
2. Master releases; pull-up takes line high.
3. Sensor pulls low for 80 µs (acknowledgment).
4. Sensor pulls high for 80 µs.
5. Sensor sends 40 bits of data, each as:
   - Low for **50 µs** (start of bit).
   - High for **26 µs** = 0, **70 µs** = 1.

The host must time the duration of each "high" segment to discriminate 0 from 1. **40 bits per measurement** = the host must accurately measure 40 short pulses (26 µs vs 70 µs — a 44 µs delta).

Why Linux struggles:

- Standard kernel preemption: any other ISR can delay your GPIO read by 100+ µs → bit misread.
- Even with PREEMPT_RT, scheduling jitter can be 50 µs+.
- Once one bit is misread, the whole frame is corrupt (no resync).
- DHT22's CRC catches it, but you just retry — every read potentially fails.

The honest options:

1. **Don't.** Use SHT3x or AHT20 (proper I²C) instead. They cost the same.
2. **PREEMPT_RT + busy-wait GPIO** in a driver. Works ~80 % of the time; you retry until success.
3. **MCU helper.** An ATtiny / ESP8266 does the DHT22 timing and exposes the result via I²C / UART to Linux. The right answer if you must support DHT22.
4. **PRU coprocessor** on chips that have one (TI AM335x, Beaglebone Black). Not on i.MX6ULL.

The mainline `dht11.c` driver (`drivers/iio/humidity/dht11.c`) takes approach (2) — uses high-resolution timers and IRQ-on-edge to measure pulse widths. It works on RPi-class hardware most of the time; reliability varies by load.

**Bottom line: if you see DHT22 in someone's product schematic, suggest a swap to SHT3x.**

## 77.7  Other 1-Wire devices worth knowing

| Device | Family | Purpose |
|--------|--------|---------|
| DS18B20 | 0x28 | Temperature |
| DS18S20 | 0x10 | Older temperature, 9-bit only |
| DS1822 | 0x22 | Lower-precision DS18B20 sibling |
| DS2406 | 0x12 | 1-Wire GPIO extender (2 ports) |
| DS2438 | 0x26 | Battery monitor (V, T, current via shunt) |
| DS2431 | 0x2D | 1-Kbit EEPROM |
| DS2433 | 0x23 | 4-Kbit EEPROM |
| DS2401 | 0x01 | Unique 48-bit silicon serial number (= ROM ID only) |
| MAX31850 | 0x3B | K-type thermocouple-to-1-Wire |

DS2401 is interesting for embedded products: it's a unique serial number you can solder onto a board and read over a single GPIO. Anti-counterfeiting, asset tracking. ~$0.30.

## 77.8  Lab

1. **Wire a DS18B20** to GPIO4_IO14 with a 4.7 kΩ pull-up to 3.3 V. Configure `w1-gpio` in DT.
2. **Verify enumeration.** After boot, `ls /sys/bus/w1/devices/`. The 64-bit ROM ID is part of the directory name.
3. **Read temperature.** Heat the chip with a finger; verify reading rises by a few degrees.
4. **Multi-chip.** Add a second DS18B20 in parallel. Verify both enumerate as separate `28-*` entries.
5. **Long-cable test.** Use a 5-meter CAT5 cable. Verify reads still succeed (1-Wire is unusually robust to long cables).
6. **Write the custom slave driver.** Use the skeleton from §77.4. Even without a custom chip, you can test the registration via a fake family-code mismatch report.
7. **Try DHT22.** Wire one up. Read with the mainline `dht11` driver (which also handles DHT22). Note the retry rate — count successes vs failures over 100 reads. Compare to a properly-wired SHT3x: 100/100 success.
8. **Read DS2401 ROM ID** as a board serial number. Add to your factory-test script: log each board's unique 48-bit ID.

## 77.9  Pitfalls

- **Missing pull-up.** No pull-up = bus floats = no devices enumerate. 4.7 kΩ is standard; longer cables may need 2.2 kΩ.
- **Insufficient parasitic-power current.** DS18B20 in parasitic mode (3-pin connection, VDD tied to GND, draws power from the bus) needs the master to drive a strong pull-up *during conversion* (750 ms). `w1-gpio` doesn't do this; use a 3-pin parasitic config only with the master that supports "strong pull-up."
- **GPIO open-drain capability.** 1-Wire requires the GPIO to switch between output-low and input (with pull-up). Some SoC GPIOs are limited. i.MX6ULL is fine.
- **Search ROM with bus contention.** With many slaves on a long cable, signal integrity degrades. Search may fail to find all slaves. Reduce cable length or use a ds2482 hardware master.
- **CRC errors.** w1-therm's `temperature` sysfs file returns "-1" or stale on CRC failure. Check `dmesg` for `w1_slave: crc mismatch`. Increase pull-up strength.
- **DHT22 expecting tight Linux GPIO timing.** It won't work reliably. See §77.6.
- **w1 polling thread CPU usage.** The w1 core re-enumerates every 10 seconds by default. On a busy bus this is ~50 ms of CPU. Adjustable via `/sys/bus/w1/devices/w1_bus_master1/w1_master_timeout`.

## 77.10  Going deeper

- **`drivers/w1/w1.c`** + `w1_io.c` — w1 core.
- **`drivers/w1/masters/w1-gpio.c`** — bit-bang master.
- **`drivers/w1/slaves/w1_therm.c`** — DS18B20 driver (~1200 lines, includes everything).
- **`drivers/w1/slaves/w1_ds2438.c`** — battery-monitor slave for comparison.
- **`drivers/iio/humidity/dht11.c`** — the "best-effort" DHT22 driver.
- **`Documentation/w1/`** — w1 framework documentation.
- **Maxim 1-Wire app notes** at maximintegrated.com (now analog.com) — `AN187`, `AN126`, `AN148`.
- **DS18B20 datasheet (Maxim)** — protocol reference.
- **`drivers/w1/masters/ds2482.c`** — I²C-to-1-Wire bridge driver for systems where GPIO timing isn't tolerable.

> Next chapter: **Chapter 78 — MEMS microphones.** Digital I²S microphones (INMP441, ICS-43434) — capture audio with no analog audio chain.
