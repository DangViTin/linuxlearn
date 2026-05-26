---
chapter: 69
title: Air quality / gas / particulate matter (SCD30 / CCS811 / PMS5003)
part: VII — Device cookbook
estimated_pages: 22
status: draft
---

# Chapter 69 — Air quality, gas, particulate matter

> **What:** three radically different "what's in the air" sensors: **Sensirion SCD30** (NDIR CO₂, I²C with clock-stretching), **AMS CCS811** (metal-oxide TVOC + eCO₂, I²C with interrupt), **Plantower PMS5003** (laser-scattering PM, UART). Each represents a different sensing physics, a different bus, a different protocol shape. For each: physics, protocol, the mainline driver, plus a from-scratch UART-based PMS5003 driver (since it's the most pedagogically interesting and the existing IIO support is fragmented).
> **Why:** the air-quality market is exploding (post-pandemic; IAQ in offices; outdoor pollution dashboards). These three sensors together cover the dimensions that matter: CO₂ (occupancy, ventilation), VOCs (cleaning chemicals, paint, formaldehyde), particulate matter (combustion, dust, wildfire smoke). Knowing which chip claims to measure what — and what it *actually* measures — separates a useful product from a placebo.
> **Focus:** **NDIR is physics; metal-oxide is correlation; laser scatter is counting**. NDIR (CO₂): direct absorbance measurement, traceable to the molecule. MOX (CCS811): a tin-oxide film whose resistance changes with reducing gases — the "eCO₂" is *inferred* from VOC trends, **not** actually measured. PM: literally counting particles flowing through a laser beam. Internalise this hierarchy and you'll never trust an "eCO₂" reading on its face again.

## 69.1  Sensor comparison

| | Sensirion SCD30 | AMS CCS811 | Plantower PMS5003 |
|---|---|---|---|
| Measures | CO₂ (NDIR), T, H | TVOC + eCO₂ (inferred) | PM1.0, PM2.5, PM10 |
| Physics | IR absorbance at 4.26 µm | Metal-oxide resistance | Laser scattering + counting |
| Interface | I²C (clock-stretch) or Modbus or UART | I²C with /WAKE pin | UART |
| Range | 400–10000 ppm | TVOC 0–32k ppb, eCO₂ 400–32k ppm | 0–500 µg/m³ |
| Accuracy | ±(30 ppm + 3 %) | "indicative" — not certified | ±10 µg/m³ + 10 % |
| Warm-up | < 5 s for first reading | 20 min for stability; 48 h burn-in | 30 s for stable fan |
| Idle current | 19 mA average | 0.6 mA average | 100 mA (laser+fan) |
| Calibration | ASC (auto self-calibration) using 7-day low | factory; baseline drift | factory only |
| Volume price | $50–80 | $5–15 | $20–40 |
| Mainline driver | `scd30_core.c` + `scd30_i2c.c` | `ccs811.c` | none in mainline; SerDev driver in some BSPs |

**Pick guide:**
- **SCD30**: when you need **real CO₂**, traceable to a standard, for ventilation control or occupancy detection. Expensive but honest.
- **CCS811**: when you want **a trend** in air quality (VOC build-up from cleaning chemicals, paint, body odour). Don't claim "this is CO₂."
- **PMS5003**: when you need **PM monitoring** — air quality monitor product, wildfire-smoke alert, HVAC filter health.

You often combine all three. A complete IAQ (indoor air quality) sensor stack is: temp/humidity (Ch 67) + real CO₂ (SCD30) + VOC trend (CCS811) + PM (PMS5003).

## 69.2  Physics — what each sensor actually measures

### SCD30 — NDIR (Non-Dispersive InfraRed)

CO₂ absorbs strongly at 4.26 µm. The chip contains an IR emitter, a small chamber, and two photodetectors with bandpass filters:

```
   ┌──────────────────────────────────────────┐
   │                              ╲           │
   │   IR emitter ───────────────► ╲          │
   │                                ╲ filter @ 4.26 µm
   │                                 ╲ → CO₂-sensitive detector
   │                                 ╱
   │                       gas      ╱
   │                       sample  ╱  filter @ 3.95 µm (reference)
   │                              ╱  → reference detector
   └──────────────────────────────────────────┘
   ratio of detectors → directly tied to CO₂ concentration via Beer-Lambert law
```

The chamber is ~10 cm long; gas diffuses in passively (no pump). The two-detector design rejects emitter intensity drift and dust. **The output is calibrated CO₂ ppm**, traceable to NIST CO₂ standards.

### CCS811 — MOX (Metal-OXide gas sensor)

A heated SnO₂ film. In dry air, oxygen ions adsorb on the film, raising its resistance. Reducing gases (CO, H₂, ethanol, formaldehyde — VOCs collectively) react with the surface oxygen, freeing electrons, lowering resistance.

```
   resistance(VOC) = R₀ / (1 + k × [VOC])
```

The chip's firmware maps resistance to two output numbers:
- **TVOC** (Total Volatile Organic Compounds, ppb).
- **eCO₂** (equivalent CO₂, ppm) — *not* CO₂; it's an estimate based on the assumption that human-occupancy CO₂ rise tracks human-occupancy VOC rise. **Wrong by design** when you have non-human VOC sources (cooking, cleaning, painting).

The film "burns in" over the first 48 hours (chemistry stabilises), drifts over months (poisoning), and ages over years.

### PMS5003 — Laser scattering

A small laser shines across a sample stream pulled through by a fan. Particles passing through scatter light; a photodiode at an angle catches the scatter. The chip's controller analyses pulse height (→ particle size) and pulse count rate (→ particle density). Output: counts per size bin, plus three "summary" estimates (PM1.0, PM2.5, PM10 µg/m³).

```
   ┌───────────────┐    fan (suction)
   │  intake ──►   │    →  laser ──→  ╳╳╳ (particle)  →  beam dump
   │               │                   ↓
   │               │                photodiode
   └───────────────┘
```

Cheap, accurate enough for trend, *not* certified-quality (which requires beta-attenuation or gravimetric monitors costing $20k+).

## 69.3  Protocol — SCD30 I²C with clock stretching

SCD30 uses a Sensirion-style command set: 2-byte commands with optional 2-byte payload + CRC-8.

| Command | Payload | Purpose |
|---------|---------|---------|
| `0x00 10` | 2 bytes (0 = ambient pressure) | Trigger continuous measurement |
| `0x01 04` | none | Stop continuous |
| `0x46 00` | 2 bytes (interval in seconds) | Set measurement interval |
| `0x02 02` | none, returns 2 bytes | Get data-ready status |
| `0x03 00` | none, returns 18 bytes | Read measurement |
| `0xD0 04` | none | Reset |

Key gotcha: SCD30 uses **I²C clock stretching** — it holds SCL low for tens of milliseconds while doing internal work. Many SoC I²C controllers handle this fine; some (notably Broadcom's BCM2835 on Raspberry Pi) do not. **i.MX6ULL handles clock-stretching correctly**, but verify your `clock-frequency` is ≤ 400 kHz.

A read of CO₂+T+H:

```
   Host: START | 0xC2 | 0x03 | 0x00 | STOP                          (cmd 0x0300)
   ... wait 3 ms ...
   Host: START | 0xC3 | (18 bytes) | STOP

   18 bytes = CO₂_msb | CO₂_lsb | CRC | CO₂_xmsb | CO₂_xlsb | CRC |
              T_msb   | T_lsb   | CRC | T_xmsb   | T_xlsb   | CRC |
              H_msb   | H_lsb   | CRC | H_xmsb   | H_xlsb   | CRC
```

Each measurement is a **32-bit IEEE-754 float** split across 4 data bytes (with CRC after every 2). Decode:

```c
uint32_t bits = (raw[0]<<24) | (raw[1]<<16) | (raw[3]<<8) | raw[4];
float co2_ppm = *(float*)&bits;
```

(Skipping the CRC bytes at indices 2 and 5; check them and retry on mismatch.)

### Mainline SCD30 driver

`drivers/iio/chemical/scd30_core.c` (~700 lines) + `scd30_i2c.c` (~150 lines).

```c
/* Simplified */
static int scd30_command_read(struct scd30_state *state, enum scd30_cmd cmd,
                               u16 *out, int nresp)
{
    /* Send the 2-byte command */
    err = scd30_write(state, cmd, NULL, 0);
    /* Wait for chip's internal processing */
    msleep(state->cmd[cmd].timeout_ms);
    /* Read 2*nresp bytes (each result is 2 bytes + 1 CRC) */
    err = scd30_read_resp(state, out, nresp);
    /* Validate each CRC */
    return crc8_check(...);
}
```

The IIO `read_raw` callback issues `0x0300` (read measurement), parses 18 bytes into three floats, returns CO₂ in PPM, T in mC, H in mRH.

The CRC verification is what makes SCD30/SHT3x drivers heavier than BME280 — every 2-byte word is CRC-checked, every read either succeeds with all-good CRCs or retries.

## 69.4  Protocol — CCS811 I²C with /WAKE pin

CCS811 has a register map (similar to BME280) but a quirk: the **/WAKE pin must be held low** when communicating. Internal sleep saves power; the host wakes the chip with /WAKE = low, transacts, then releases /WAKE.

| Register | Purpose |
|----------|---------|
| 0x00 STATUS | Bit 7 = APP_RUNNING, bit 3 = DATA_READY |
| 0x01 MEAS_MODE | Drive mode (0 = idle, 1 = 1 reading/sec, 2 = 10 sec, 3 = 60 sec, 4 = 250 ms raw) |
| 0x02 ALG_RESULT_DATA | 8 bytes: eCO₂[2], TVOC[2], STATUS, ERROR_ID, RAW_DATA[2] |
| 0x05 ENV_DATA | Set host's T/H (so chip can compensate baseline drift) |
| 0xB0 SW_RESET | Write `0x11 0xE5 0x72 0x8A` to reset |
| 0xF4 APP_START | "Boot from firmware"; mandatory at startup |

Bring-up sequence:
1. Power on; chip is in boot mode.
2. Wait ≥ 70 ms.
3. Issue `0xF4` (no data) — switch to app mode.
4. Wait 70 ms.
5. Write `0x01 = 1` to MEAS_MODE.
6. From now on, the chip measures every 1 s; poll STATUS for DATA_READY bit.
7. Read `0x02` (8 bytes) on data-ready; bytes 0-1 = eCO₂ ppm, bytes 2-3 = TVOC ppb.

### Mainline CCS811 driver

`drivers/iio/chemical/ccs811.c` (~600 lines).

```c
static int ccs811_get_measurement(struct ccs811_data *data)
{
    int err, count = 0;
    u8 status;

    /* Wait for DATA_READY (poll up to 1s) */
    do {
        err = i2c_smbus_read_byte_data(client, CCS811_REG_STATUS);
        if (err < 0) return err;
        status = err;
        if (status & STATUS_DATA_READY) break;
        msleep(10);
    } while (count++ < 100);

    return i2c_smbus_read_i2c_block_data(client, CCS811_REG_ALG_RESULT,
                                          8, data->buffer);
}

static int ccs811_read_raw(struct iio_dev *idev, ...,  int *val, int *val2, long mask)
{
    struct ccs811_data *data = iio_priv(idev);
    err = ccs811_get_measurement(data);
    switch (chan->type) {
    case IIO_CONCENTRATION:
        if (chan->channel2 == IIO_MOD_CO2)
            *val = (data->buffer[0] << 8) | data->buffer[1];   /* eCO2 ppm */
        else
            *val = (data->buffer[2] << 8) | data->buffer[3];   /* TVOC ppb */
        return IIO_VAL_INT;
    }
}
```

User-space: `cat /sys/bus/iio/devices/iio:device0/in_concentration_co2_input` returns eCO₂ ppm.

The driver also implements an **environmental compensation** hook — feed it temperature and humidity from your BME280, and the chip adjusts its baseline. Without compensation, the eCO₂/TVOC drift over the seasons.

## 69.5  PMS5003 — UART protocol

PMS5003 isn't I²C — it's a 9600-baud UART with a custom binary framing. No mainline IIO driver as of writing (a SerDev-based driver exists out-of-tree, but mainline support is fragmented). Perfect for a from-scratch implementation.

### Frame format

Every frame is 32 bytes:

```
   offset  bytes  meaning
   0       2      0x42 0x4D     (sync: "BM")
   2       2      frame length (= 28 = 0x001C)
   4       2      PM1.0 standard (µg/m³)
   6       2      PM2.5 standard
   8       2      PM10 standard
   10      2      PM1.0 atmospheric
   12      2      PM2.5 atmospheric  ← the most often-quoted PM2.5
   14      2      PM10 atmospheric
   16      2      particle count > 0.3 µm in 0.1 L
   18      2      particle count > 0.5 µm
   20      2      particle count > 1.0 µm
   22      2      particle count > 2.5 µm
   24      2      particle count > 5.0 µm
   26      2      particle count > 10.0 µm
   28      2      reserved
   30      2      checksum (sum of bytes 0..29)
```

The chip auto-sends a frame every ~800 ms when active. So a driver doesn't *request* data; it listens for frames.

### A from-scratch UART driver

We'll use the kernel's **SerDev** subsystem — `serdev_device_driver` — which lets a driver bind to a UART port via DT and receive raw bytes. The frame parsing is a small state machine.

`mypms5003.c`:

```c
#include <linux/init.h>
#include <linux/module.h>
#include <linux/serdev.h>
#include <linux/iio/iio.h>
#include <linux/of.h>

#define PMS_FRAME_LEN 32

struct mypms {
    struct serdev_device *serdev;
    struct mutex lock;

    /* Latest values */
    u16 pm1_0, pm2_5, pm10;

    /* Frame-assembly state */
    u8  buf[PMS_FRAME_LEN];
    int idx;

    struct iio_dev *idev;
};

/* Called by serdev with raw RX bytes — runs in IRQ-thread context */
static int mp_receive_buf(struct serdev_device *serdev,
                          const unsigned char *data, size_t count)
{
    struct mypms *m = serdev_device_get_drvdata(serdev);
    size_t i;

    for (i = 0; i < count; i++) {
        u8 c = data[i];

        /* Sync state machine */
        if (m->idx == 0) {
            if (c == 0x42) { m->buf[m->idx++] = c; }
            continue;
        }
        if (m->idx == 1) {
            if (c != 0x4D) { m->idx = 0; continue; }   /* resync */
            m->buf[m->idx++] = c;
            continue;
        }
        m->buf[m->idx++] = c;
        if (m->idx < PMS_FRAME_LEN) continue;

        /* Full frame — validate checksum */
        u16 sum = 0;
        for (int j = 0; j < 30; j++) sum += m->buf[j];
        u16 frame_sum = (m->buf[30] << 8) | m->buf[31];
        if (sum != frame_sum) {
            m->idx = 0;
            continue;
        }

        /* Decode (big-endian 16-bit fields) */
        mutex_lock(&m->lock);
        m->pm1_0 = (m->buf[10] << 8) | m->buf[11];
        m->pm2_5 = (m->buf[12] << 8) | m->buf[13];
        m->pm10  = (m->buf[14] << 8) | m->buf[15];
        mutex_unlock(&m->lock);

        m->idx = 0;
    }
    return count;
}

static const struct serdev_device_ops mp_serdev_ops = {
    .receive_buf = mp_receive_buf,
};

/* IIO callback */
static int mp_read_raw(struct iio_dev *idev,
                       struct iio_chan_spec const *chan,
                       int *val, int *val2, long mask)
{
    struct mypms *m = iio_priv(idev);

    if (mask != IIO_CHAN_INFO_PROCESSED) return -EINVAL;
    if (chan->type != IIO_MASSCONCENTRATION) return -EINVAL;

    mutex_lock(&m->lock);
    switch (chan->channel2) {
    case IIO_MOD_PM1:   *val = m->pm1_0; break;
    case IIO_MOD_PM2P5: *val = m->pm2_5; break;
    case IIO_MOD_PM10:  *val = m->pm10;  break;
    default:            mutex_unlock(&m->lock); return -EINVAL;
    }
    mutex_unlock(&m->lock);
    return IIO_VAL_INT;
}

#define PMS_CHAN(idx, _mod) {                                  \
    .type = IIO_MASSCONCENTRATION,                              \
    .modified = 1,                                               \
    .channel2 = (_mod),                                          \
    .info_mask_separate = BIT(IIO_CHAN_INFO_PROCESSED),          \
    .scan_index = (idx),                                         \
}

static const struct iio_chan_spec mp_channels[] = {
    PMS_CHAN(0, IIO_MOD_PM1),
    PMS_CHAN(1, IIO_MOD_PM2P5),
    PMS_CHAN(2, IIO_MOD_PM10),
};

static const struct iio_info mp_iio_info = {
    .read_raw = mp_read_raw,
};

/* Probe / Remove */

static int mp_probe(struct serdev_device *serdev)
{
    struct iio_dev *idev;
    struct mypms *m;
    int err;

    idev = devm_iio_device_alloc(&serdev->dev, sizeof(*m));
    if (!idev) return -ENOMEM;
    m = iio_priv(idev);
    m->serdev = serdev;
    m->idev = idev;
    mutex_init(&m->lock);

    serdev_device_set_drvdata(serdev, m);
    serdev_device_set_client_ops(serdev, &mp_serdev_ops);

    err = serdev_device_open(serdev);
    if (err) return err;

    serdev_device_set_baudrate(serdev, 9600);
    serdev_device_set_flow_control(serdev, false);
    serdev_device_set_parity(serdev, SERDEV_PARITY_NONE);

    idev->name = "mypms5003";
    idev->info = &mp_iio_info;
    idev->modes = INDIO_DIRECT_MODE;
    idev->channels = mp_channels;
    idev->num_channels = ARRAY_SIZE(mp_channels);

    return devm_iio_device_register(&serdev->dev, idev);
}

static void mp_remove(struct serdev_device *serdev)
{
    serdev_device_close(serdev);
}

static const struct of_device_id mp_of_match[] = {
    { .compatible = "linuxlearn,mypms5003" },
    { }
};
MODULE_DEVICE_TABLE(of, mp_of_match);

static struct serdev_device_driver mp_driver = {
    .driver = {
        .name = "mypms5003",
        .of_match_table = mp_of_match,
    },
    .probe  = mp_probe,
    .remove = mp_remove,
};
module_serdev_device_driver(mp_driver);

MODULE_LICENSE("GPL");
```

DT — attach to UART2:

```dts
&uart2 {
    pinctrl-names = "default";
    pinctrl-0 = <&pinctrl_uart2>;
    status = "okay";

    pms5003 {
        compatible = "linuxlearn,mypms5003";
        current-speed = <9600>;
    };
};
```

Build, load, exercise:

```
[root@pa-mini:~]# insmod mypms5003.ko
[root@pa-mini:~]# ls /sys/bus/iio/devices/iio:device0/
in_massconcentration_pm10_input
in_massconcentration_pm1_input
in_massconcentration_pm2p5_input
name

[root@pa-mini:~]# cat /sys/bus/iio/devices/iio:device0/in_massconcentration_pm2p5_input
12
[root@pa-mini:~]# # → 12 µg/m³ (clean indoor air)
```

In wildfire smoke: same code reads "180" or "220" µg/m³, the standard "very unhealthy" range.

Driver is ~150 lines including IIO. The whole protocol is a state machine over a UART stream.

### Why SerDev?

SerDev — kernel/SerDev — is the "I want a UART-attached device, not a tty" subsystem. Before SerDev, drivers either polled a `/dev/ttyN` from user space (ugly), or set up a custom `line discipline` (painful kernel API). SerDev lets a kernel driver bind to a DT-described UART port; the framework handles the tty plumbing, exposes a small API (`set_baudrate`, `set_flow_control`, `receive_buf`), and the driver gets clean byte streams.

Many UART-protocol devices fit this mould: GPS NMEA receivers, Bluetooth HCI, LoRa modules, Nextion displays, PMS5003. SerDev makes them all tractable.

## 69.6  Putting it together — a full IAQ stack

For an indoor-air-quality monitor product:

```dts
&i2c1 {
    bme280@76 { compatible = "bosch,bme280"; reg = <0x76>; };
    scd30@61  { compatible = "sensirion,scd30"; reg = <0x61>; };
    ccs811@5a { compatible = "ams,ccs811"; reg = <0x5a>;
                 wake-gpios = <&gpio4 14 GPIO_ACTIVE_LOW>; };
};

&uart2 {
    pms5003 { compatible = "plantower,pms7003"; };   /* or your linuxlearn one */
};
```

User-space reads all of them via IIO + serdev, feeds an MQTT topic, plots in Grafana. Bonus: feed the BME280's T+H to the CCS811's ENV_DATA register for compensation.

## 69.7  Lab

1. **SCD30 NDIR with i2c-tools.** `i2cdetect -y 1` (should show 0x61). Manually issue `0x0300` and read 18 bytes; verify CRCs; decode the first 4 bytes as float — your CO₂ reading.
2. **CCS811 bring-up.** Wire up with the /WAKE pin to a GPIO; verify probe in dmesg; read eCO₂ before and after a window-open / hot-meal scenario. Watch it climb when cooking.
3. **PMS5003 from scratch.** Build `mypms5003.ko`; verify frame parsing; expose `in_massconcentration_pm2p5_input`.
4. **PMS5003 with a smoke source.** Light a match near the sensor (carefully); watch PM2.5 spike 100× then settle over 30 s.
5. **Cross-correlate.** Run all three sensors for an hour; log to CSV. After cooking, see CO₂ rise (people present), TVOC rise (cooking emissions), PM2.5 rise (smoke). Three signals from three physics.
6. **Mainline SCD30**. Switch from manual i2c-tools to the mainline driver via `compatible = "sensirion,scd30"`. Verify same numbers.

Commit code to `code/ch69-air-quality/`.

## 69.8  Pitfalls

- **Calling eCO₂ "CO₂".** It isn't. CCS811's eCO₂ is calibrated to track human-occupancy *if and only if* there are no other VOC sources. Cooking, paint, cleaning products, smoking — all corrupt it. If your product advertises "CO₂ sensor," use SCD30, not CCS811.
- **CCS811 24-hour burn-in.** Brand-new chip reports nonsense for the first 20 minutes; reasonable after 24 hours of continuous operation. Document this; don't show users readings during burn-in.
- **SCD30 ASC corrupting calibration.** Auto self-calibration assumes your room reaches outdoor CO₂ (400 ppm) sometime each week — fails for hermetically sealed environments. Disable ASC via the FRC command if the room never opens up.
- **PMS5003 fan failure.** Particle count silently goes to zero or near-zero. Detect by: count is identically zero for > 10 frames in a row → likely fan failure. Most products have a "fan power" pin; cycle it.
- **PMS5003 in dust storms.** The chip's saturation limit is ~500 µg/m³. In actual dust storms (Sahara, wildfire heart) values can hit 1500+; PMS5003 will report 500 forever.
- **SCD30 clock-stretching beyond timeout.** I²C controllers vary in their max-stretch tolerance. i.MX6ULL is fine at 400 kHz; some bridges fail. Use scope to check SCL low durations if reads are flaky.
- **CCS811 /WAKE polarity.** Active low. Tying it permanently low works (no sleep), but increases power. For battery products, GPIO it.
- **PM2.5 standard vs atmospheric**. Two columns in the frame; the "atmospheric" one is calibrated against standard EPA reference. Use that one. The "standard" column is uncalibrated.
- **Mixing PM2.5 µg/m³ with AQI.** AQI is a country-specific transformation (US EPA different from China MEE). Don't confuse the two.

## 69.9  Going deeper

- **`drivers/iio/chemical/scd30_core.c`** + **`scd30_i2c.c`** — the SCD30 mainline driver.
- **`drivers/iio/chemical/ccs811.c`** — CCS811.
- **`drivers/iio/chemical/sps30_i2c.c`** — Sensirion SPS30 PM driver (the higher-end alternative to PMS5003; full IIO support).
- **SCD30 Interface Description (Sensirion)** — protocol reference; command list with CRCs.
- **CCS811 datasheet (AMS)** — register map; warm-up notes.
- **PMS5003 / PMS7003 manual** (search "PMS5003 transport protocol") — frame format and command list.
- **`Documentation/networking/serdev.rst`** — SerDev framework reference.
- **EPA AQI definition** — for converting µg/m³ to the human-friendly index.

---

> **End of Group B — Environmental sensors (Ch 67–69).** You now have temperature/humidity/pressure (Ch 67), light (Ch 68), and gas + PM (Ch 69) — the three pillars of "what's the environment doing?" Each with protocol, mainline driver internals, and at least one from-scratch implementation.

> Next chapter: **Chapter 70 — I²C IMUs (MPU6050 / MPU9250 / ICM-20948).** From environmental into motion: 6- and 9-axis IMUs, the IIO trigger/buffer mechanism, and sensor-fusion math at 1 kHz.
