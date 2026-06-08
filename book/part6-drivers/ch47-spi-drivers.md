---
chapter: 47
title: SPI drivers
part: VI — Driver development
estimated_pages: 18
status: draft
---

# Chapter 47 — SPI drivers

> **What:** the Linux **SPI subsystem** — `spi_master` (the controller, again written by the SoC vendor), `spi_device` (one chip on a chip-select), `spi_driver` (the per-chip code), `spi_message` (a sequence of transfers). Same shape as I²C but with full-duplex transactions and per-CS independent configuration (mode, speed, word size).
>
> **Why:** SPI carries the high-bandwidth peripherals — NOR flash, LCDs, fast ADCs, IMUs at >1 kHz, Ethernet PHYs over SPI (W5500, ENC28J60), CAN controllers over SPI (MCP2515). Speeds from 1 MHz to 50 MHz are common, vs I²C's 100–400 kHz. The Linux model lets each chip-select have its own mode and clock without the driver caring about the controller's specifics.
>
> **Focus:** **`spi_message` is a list of `spi_transfer`s, executed back-to-back without releasing CS unless you ask**. Mastering this lets you build any chip's command sequence — "write 1 cmd byte, then read 4 data bytes, holding CS through both" is just a two-transfer message.


## 47.1  How SPI differs from I²C

| Property | I²C | SPI |
|----------|-----|-----|
| Wires | 2 (SDA, SCL) | 4 (MOSI, MISO, SCK, CS) + 1 per chip-select |
| Topology | Multi-drop on one pair | Star: separate CS per chip |
| Addressing | 7-bit on the wire | Implicit (CS asserted) |
| Direction | Half-duplex (one direction at a time) | Full-duplex (both at once) |
| Speed | 100 kHz – 1 MHz typical | 1 – 50 MHz typical |
| Bus arbitration | Built-in (NAK, arbitration loss) | None (only one master per CS) |
| Protocol overhead | Address + ACK per byte | None — just clock bits |

For an SPI bus, you pick one **chip-select** per device. The controller asserts CS, clocks bytes, deasserts CS. Each CS has its own configuration: clock speed, polarity (CPOL), phase (CPHA), word size (usually 8 bits, sometimes 16/32 for DMA-friendly).
> **MCU bridge:** Think of DMA like the MCU DMA controller you used for UART or SPI, but with cache coherency, scatter-gather descriptors, and kernel ownership rules added.
**DMA** - Direct Memory Access. hardware moves data to or from memory without the CPU copying each byte.

The i.MX6ULL has 4 **eCSPI** controllers (eCSPI1–4), each with up to 4 chip-select lines (so up to 16 SPI devices on the SoC in theory).

## 47.2  Device tree for SPI

```dts
&ecspi3 {
    pinctrl-names = "default";
    pinctrl-0 = <&pinctrl_ecspi3>;
    cs-gpios = <&gpio4 5 GPIO_ACTIVE_LOW>;   /* optional GPIO-CS */
    status = "okay";

    flash@0 {
        compatible = "winbond,w25q128", "jedec,spi-nor";
        reg = <0>;                            /* chip-select 0 */
        spi-max-frequency = <50000000>;        /* 50 MHz */
        spi-tx-bus-width = <1>;
        spi-rx-bus-width = <1>;
    };

    adc@1 {
        compatible = "linuxlearn,fastadc";
        reg = <1>;                            /* chip-select 1 */
        spi-max-frequency = <10000000>;        /* 10 MHz */
        spi-cpol;                              /* CPOL=1, CPHA=0 (mode 2) */
    };
};
```

Differences from I²C:
- **`reg` is the chip-select index**, not an address.
- **`spi-max-frequency`** is per-device. The controller uses the lower of (its max, this).
- **`spi-cpol` / `spi-cpha`** set the SPI mode (omit both = mode 0. both = mode 3).
- **`cs-gpios`** — optionally specify GPIO-based CS lines instead of the controller's native CS pins. Common when the controller's native CS doesn't quite behave the way you want (e.g., toggling between messages).
> **MCU bridge:** Think of Linux GPIO like the same pin set/reset block you used on STM32, but accessed through a kernel subsystem that owns numbering, direction, interrupts, and user-space exposure.
**GPIO** - General-Purpose Input/Output, a pin controlled as a digital input, output, or interrupt source.

## 47.3  An SPI driver skeleton

```c
#include <linux/init.h>
#include <linux/module.h>
#include <linux/spi/spi.h>
#include <linux/of.h>

struct fastadc_priv {
    struct spi_device *spi;
    struct mutex lock;
};

static int fastadc_read_word(struct fastadc_priv *p, u16 *out)
{
    u8 tx[2] = { 0x80, 0x00 };   /* read command */
    u8 rx[2];
    struct spi_transfer xfer = {
        .tx_buf = tx,
        .rx_buf = rx,
        .len    = 2,
        .speed_hz = 10000000,    /* override device default if desired */
    };
    int err = spi_sync_transfer(p->spi, &xfer, 1);
    if (err < 0)
        return err;
    *out = ((u16)rx[0] << 8) | rx[1];
    return 0;
}

static int fastadc_probe(struct spi_device *spi)
{
    struct fastadc_priv *p;
    u16 sample;
    int err;

    p = devm_kzalloc(&spi->dev, sizeof(*p), GFP_KERNEL);
    if (!p)
        return -ENOMEM;
    p->spi = spi;
    mutex_init(&p->lock);

    /* Configure SPI bus parameters */
    spi->mode          = SPI_MODE_0;
    spi->bits_per_word = 8;
    err = spi_setup(spi);
    if (err)
        return dev_err_probe(&spi->dev, err, "spi_setup failed\n");

    err = fastadc_read_word(p, &sample);
    if (err)
        return dev_err_probe(&spi->dev, err, "test read failed\n");

    dev_info(&spi->dev, "fastadc ready (test sample = %u)\n", sample);
    spi_set_drvdata(spi, p);
    return 0;
}

static void fastadc_remove(struct spi_device *spi)
{
    /* devm_* handles cleanup */
}

static const struct of_device_id fastadc_of_match[] = {
    { .compatible = "linuxlearn,fastadc" },
    { }
};
MODULE_DEVICE_TABLE(of, fastadc_of_match);

static const struct spi_device_id fastadc_id[] = {
    { "fastadc", 0 },
    { }
};
MODULE_DEVICE_TABLE(spi, fastadc_id);

static struct spi_driver fastadc_driver = {
    .driver = {
        .name = "linuxlearn-fastadc",
        .of_match_table = fastadc_of_match,
    },
    .probe    = fastadc_probe,
    .remove   = fastadc_remove,
    .id_table = fastadc_id,
};
module_spi_driver(fastadc_driver);

MODULE_LICENSE("GPL");
```

Mirror image of the I²C driver from Ch 46 — same idioms: `module_spi_driver`, two match tables, `devm_kzalloc`, `dev_err_probe`.

## 47.4  Transfers and messages

The data model is two levels:

- **`spi_transfer`** — one back-and-forth burst. Has `tx_buf` (or NULL for read-only), `rx_buf` (or NULL for write-only), `len`, optional per-transfer overrides (`speed_hz`, `bits_per_word`, `cs_change`, `delay`).
- **`spi_message`** — a list of `spi_transfer`s executed atomically. CS asserts before the first transfer, deasserts after the last (unless overridden).

For simple sequences, **`spi_sync_transfer(spi, xfers, n)`** is a one-call wrapper that builds the `spi_message`, submits it, waits, and returns.

For a complex case — say, write a register address then read 16 bytes, with no STOP between (CS held continuously):

```c
u8 tx_cmd[2] = { 0x80, reg_addr };
u8 rx_data[16];
struct spi_transfer xfers[2] = {
    {
        .tx_buf = tx_cmd,
        .len    = 2,
    },
    {
        .rx_buf = rx_data,
        .len    = 16,
    },
};
err = spi_sync_transfer(spi, xfers, 2);
```

CS is asserted for the entire 18-byte sequence. The first transfer sends 2 bytes (clocking nothing in particular into `rx`), the second reads 16 bytes (clocking dummy 0s out of `tx`).

Need to deassert CS between transfers? Set `xfers[0].cs_change = 1`. Need a delay? `xfers[0].delay.value = 10. xfers[0].delay.unit = SPI_DELAY_UNIT_USECS;`.

### Async transfers

For high-rate sampling, `spi_async()` submits a message without waiting. a callback fires on completion. Drivers that sample continuously (audio codecs, fast IMUs) use this. Initialise:

```c
static void my_complete(void *context)
{
    struct my_priv *p = context;
    /* runs in workqueue context after transfer finishes */
}

struct spi_message msg;
spi_message_init(&msg);
spi_message_add_tail(&xfer, &msg);
msg.complete = my_complete;
msg.context  = priv;
spi_async(spi, &msg);
```

## 47.5  Half-duplex helpers

For chips that don't really use full-duplex, the helpers `spi_write`, `spi_read`, and `spi_write_then_read` are simpler than building transfers by hand:

```c
err = spi_write(spi, txbuf, len);                       /* TX only, RX discarded */
err = spi_read(spi, rxbuf, len);                        /* RX only, TX = 0 */
err = spi_write_then_read(spi, txbuf, tlen, rxbuf, rlen); /* TX then RX, CS held */
```

`spi_write_then_read` is what you reach for 90% of the time. It builds two transfers internally with CS held throughout.

## 47.6  /dev/spidevN — user-space access

> **Template warning:** This block contains placeholder values.
> Replace compatible strings, GPIO numbers, addresses, and paths with values from your board before using it.


Like `/dev/i2c-N`, there's a user-space chardev for SPI: `/dev/spidev<bus>.<cs>`. To enable, add the binding to your DT:

```dts
&ecspi3 {
    spidev@0 {
        compatible = "rohm,dh2228fv";   /* historical placeholder for spidev */
        reg = <0>;
        spi-max-frequency = <10000000>;
    };
};
```

Why `"rohm,dh2228fv"`? The kernel maintainers will not accept `"spidev"` as a generic compatible — spidev is not a chip, just a user-space access mechanism. The `dh2228fv` is one of several chip names "registered" to spidev as a workaround for development. For production, use the actual chip's compatible string with a real driver.

> **Kernel warning since v4.15.** If you use this placeholder in a DT, `spidev_probe` prints `WARNING: Probing spidev with broken DT entry` and refuses to bind unless `CONFIG_SPI_SPIDEV` overrides are set. Modern best practice: either pick a real-chip compatible that already appears in `drivers/spi/spidev.c`'s `spidev_dt_ids[]` (e.g., `"semtech,sx1301"` for a known SPI radio), or write a proper DT overlay that adds a `compatible` your kernel build accepts. The cookbook chapters (Ch 98, 99, 101, 105, 106) use `rohm,dh2228fv` as shorthand. in production swap for the chip's real string + a tiny accepting driver, or build with the `spidev_compatible_array` patch.

The spidev userspace API uses ioctl:

```c
int fd = open("/dev/spidev2.0", O_RDWR);
u8 mode = SPI_MODE_0;
ioctl(fd, SPI_IOC_WR_MODE, &mode);
u32 speed = 10000000;
ioctl(fd, SPI_IOC_WR_MAX_SPEED_HZ, &speed);

struct spi_ioc_transfer xfer = {
    .tx_buf = (uintptr_t)tx, .rx_buf = (uintptr_t)rx, .len = 4,
};
ioctl(fd, SPI_IOC_MESSAGE(1), &xfer);
```

Useful for bring-up. Production code should be a real `spi_driver`.

## 47.7  A worked example — driving an MCP3008 ADC

The MCP3008 is a popular SPI ADC: 10-bit, 8 channels, single-ended. Communication protocol:

- Write a 3-byte command: `0x01`, `(0x80 | channel<<4)`, `0x00`.
- Read 3 bytes back. The 10-bit value lives in `rx[1] & 0x03` (high 2 bits) and `rx[2]` (low 8 bits).

A minimal driver function:

```c
static int mcp3008_read_channel(struct mcp3008_priv *p, int channel, u16 *out)
{
    u8 tx[3] = { 0x01, (u8)(0x80 | (channel << 4)), 0x00 };
    u8 rx[3];
    struct spi_transfer xfer = {
        .tx_buf = tx, .rx_buf = rx, .len = 3,
    };
    int err = spi_sync_transfer(p->spi, &xfer, 1);
    if (err < 0)
        return err;
    *out = ((rx[1] & 0x03) << 8) | rx[2];
    return 0;
}
```

Wrap with IIO (Ch 49) and you have an 8-channel ADC exposed via `/sys/bus/iio/devices/iio:device0/in_voltage*_raw`. The mainline `drivers/iio/adc/mcp320x.c` does this for the entire MCP320x family.

## 47.8  Lab

1. **Configure ecspi3** in DT (or whichever you have). Add a generic spidev node, verify `/dev/spidev2.0` appears.
2. **Loopback test.** Short MOSI to MISO. Write a small user-space program that opens `/dev/spidev2.0`, sends 4 bytes, reads them back. Confirm what came out comes back in.
3. **Build the fastadc / MCP3008 skeleton.** Wire up an MCP3008 (or use a real spidev device). Verify `dev_info` reports the test sample.
4. **Try full-duplex.** Send `0xA5` while reading. print what comes back simultaneously. SPI's full-duplex nature is unique among common buses — appreciate it.
5. **Speed sweep.** Vary `spi-max-frequency` from 100 kHz to 25 MHz in DT. observe where signal integrity breaks (your scope or analyzer is your friend). Linux honors `spi-max-frequency` literally. The controller picks the highest divisor below it.
6. **Multiple chip-selects.** Configure two devices on the same bus (CS0 and CS1) and access both. Verify each gets its own SPI mode/speed.

## 47.9  Pitfalls

- **Wrong CS polarity.** If a chip wants active-high CS, the controller's default (active-low) won't drive it correctly. Use `spi-cs-high` in DT.
- **CPOL/CPHA wrong.** Symptom: reads return 0xFF or junk. Cross-check the chip's datasheet *mode* against your DT. Mode 0 is most common. mode 3 next.
- **Speed too high for layout.** Long traces, missing termination, no ground reference plane → garbage at 20 MHz that works fine at 1 MHz. Start slow, ramp up.
- **Sending a single read transfer with `len` larger than your `rx_buf`.** Buffer overflow → kernel panic. The `len` field is the SPI clock count, so you need at least that many bytes in `rx_buf`.
- **Calling `spi_sync_transfer` from atomic context.** It sleeps. Use `spi_async` from atomic context, or defer to a workqueue.
- **Native CS vs GPIO-CS subtleties.** The i.MX eCSPI native CS asserts and deasserts for *each* `spi_transfer`. To hold CS across multiple transfers, either (a) put them all in one `spi_message`, or (b) use GPIO-based CS via `cs-gpios` — software holds GPIO-CS for the whole message.
- **`bits_per_word` != 8.** Most chips use 8-bit words. If you set 16, the controller packs two bytes per "word" — and the byte order may not be what you expect. Stay at 8 unless you have a reason.
- **Forgetting `spi_setup` after changing mode/speed.** Changes to `spi->mode`, `spi->bits_per_word`, etc., don't take effect until you call `spi_setup`. Probe should always call it once.

## 47.10  Going deeper

- **`Documentation/spi/`** — SPI subsystem documentation.
- **`Documentation/devicetree/bindings/spi/`** — DT bindings for SPI controllers and devices.
- **`drivers/spi/spi-imx.c`** — the i.MX SPI controller driver.
- **`drivers/iio/adc/mcp320x.c`** — production MCP3008 driver as a clean IIO reference.
- **`drivers/spi/spidev.c`** — the spidev chardev driver. how `/dev/spidevN` is implemented.
- **`Documentation/spi/spidev.rst`** — when/how to use spidev (and the controversial `dh2228fv` workaround explained).

> Next chapter: **Chapter 48 — PWM and RTC.** Two short but practical subsystems for ubiquitous embedded needs: dimming backlights, generating tones, and keeping time across power cycles.
> **MCU bridge:** Think of Linux PWM like an MCU timer output channel, except the driver exposes period, duty cycle, polarity, and enable state through a subsystem.
> **PWM** - Pulse-Width Modulation, a timer output whose duty cycle controls average power or encodes timing.
