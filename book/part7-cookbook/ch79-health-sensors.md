---
chapter: 79
title: Health sensors (MAX30100 / MAX30102)
part: VII - Device cookbook
estimated_pages: 18
status: draft
---

# Chapter 79: Health sensors

> **What:** **PPG** (photoplethysmography) sensors, Maxim **MAX30100** (the original) and **MAX30102** (the improved successor). Both: red + IR LED + photodiode + FIFO + I²C. They give you raw light-intensity samples from a finger (or earlobe, forehead). Your code extracts **heart rate** and **SpO₂** (blood-oxygen saturation) from those samples. Protocol, FIFO mechanics, from-scratch IIO driver, and a sketch of the HR/SpO₂ extraction algorithm.
> **IIO:** Industrial I/O, Linux's subsystem for sensors, ADCs, DACs, and buffered sampled data.
>
> **Why:** "wellness" features (fitness bands, smart watches, baby monitors, medical IoT) all use PPG. The chip is cheap, the wiring trivial, the principle is simple, but the work is in the signal processing on the host side. This chapter covers the chip end-to-end and points at what user-space must do.
>
> **Focus:** The chip delivers light-intensity samples. Your code turns those samples into heart rate and SpO₂, the chip cannot do this for you. Heart rate comes from counting peaks in the IR signal. SpO₂ comes from the ratio of red-AC/red-DC to IR-AC/IR-DC mapped through an empirical curve. The driver delivers raw 18-bit samples at 100 Hz. User-space filters, finds peaks, computes. Without good signal processing, the readings are unreliable. The chip cannot compensate for bad code on the host.


## 79.1  Chip comparison

| | Maxim MAX30100 | Maxim MAX30102 | Maxim MAX30105 |
|---|---|---|---|
| Channels | red + IR | red + IR | red + IR + green (particle sense) |
| Resolution | 14-bit | 18-bit | 18-bit |
| Sample rates | 50/100/167/200/400/600/800/1000 Hz | 50–3200 Hz | 50–3200 Hz |
| FIFO | 16 samples | 32 samples | 32 samples |
| Sensitivity | per-LED current 0–50 mA | 0–51 mA | 0–51 mA |
| Operating voltage | 1.7, 2.0 V (sensor) + 3.3 V (I/O) | 1.7, 2.0 V + 3.3 V | 1.7, 2.0 V + 3.3 V |
| I²C address | 0x57 | 0x57 | 0x57 |
| Idle current | 0.6 µA shutdown | 0.7 µA | 0.7 µA |
| Status | EOL, replaced by MAX30102 | active | active |
| Volume price | $4 (older modules) | $6–8 | $10–12 |

**Pick guide:**
- **MAX30102** for new designs. Better signal, larger FIFO.
- **MAX30100** for legacy / module-already-on-hand.
- **MAX30105** when you need a third LED (green for "is there a finger present?" via particle sensing).

## 79.2  The physics, photoplethysmography

Shine light into tissue. Some of it is absorbed by blood. The rest reflects or scatters back to a photodiode. As your heart beats, the volume of blood in capillaries fluctuates → light absorption fluctuates → photodiode current fluctuates. That AC component is the **PPG signal**.

The pulsatile signal is small, about 1 % of the DC level. Most of the light hitting the photodiode is the constant amount that passes through tissue without modulation. The pulsatile AC component is the signal we actually want.

For **SpO₂**, you measure with two wavelengths:
- **Red (660 nm)**: oxygenated hemoglobin absorbs *less* red light.
- **IR (940 nm)**: deoxygenated hemoglobin absorbs *less* IR light.

Compute:

```
R = (AC_red / DC_red) / (AC_IR / DC_IR)
SpO₂ ≈ 110 - 25·R    (empirical for fingertip PPG; calibration-dependent)
```

The "110 − 25·R" is fitted to clinical pulse-oximeter data. Different chips, different fits, Maxim publishes a recommended table for each.

For **heart rate**, you find peaks in the IR-AC signal. Peak-to-peak time × 60 = BPM. Modern algorithms use FFT-based methods or autocorrelation for robustness against motion artifacts.

## 79.3  Protocol, MAX30102

Register map (the highlights):

| Reg | Name | Purpose |
|-----|------|---------|
| 0x00 | Interrupt Status 1 | Bit 7 = FIFO almost full, bit 6 = new sample, bit 0 = power-ready |
| 0x02 | Interrupt Enable 1 | Mask of interrupts |
| 0x04 | FIFO Write Pointer | Index where chip writes next sample |
| 0x05 | FIFO Overflow Counter | How many samples lost |
| 0x06 | FIFO Read Pointer | Reader-controlled pointer; chip ignores beyond this |
| 0x07 | FIFO Data Register | Read here to get samples |
| 0x08 | FIFO Configuration | Sample averaging, rollover, almost-full threshold |
| 0x09 | Mode Configuration | Reset, shutdown, mode (HR=0x02, SpO₂=0x03, multi-LED=0x07) |
| 0x0A | SpO₂ Configuration | ADC range, sample rate, pulse width |
| 0x0C | LED1 (red) Pulse Amplitude | 0..255, controls LED current |
| 0x0D | LED2 (IR) Pulse Amplitude | 0..255 |
| 0xFF | Part ID | 0x15 for MAX30102 |

### Bring-up sequence

1. Write 0x09 = 0x40 → reset.
2. Wait ~10 ms.
3. Write 0x02 = 0xC0 → enable FIFO-almost-full + new-data IRQs.
4. Write 0x08 = 0x4F → average 4 samples per FIFO entry, FIFO rollover OFF, almost-full at 17 samples (=32-15).
5. Write 0x09 = 0x03 → SpO₂ mode (both LEDs).
6. Write 0x0A = 0x27 → ADC range 4096 nA, sample rate 100 Hz, pulse width 411 µs (18-bit).
7. Write 0x0C = 0x24 → LED1 (red) current ~7 mA.
8. Write 0x0D = 0x24 → LED2 (IR) current ~7 mA.
9. Wait for IRQ or poll. Each FIFO entry is 6 bytes: 3 bytes red + 3 bytes IR.
> **MCU bridge:** Think of an IRQ like an EXTI/NVIC interrupt path, except Linux splits the hard interrupt from deferred work and must share lines across drivers.
> **IRQ:** interrupt request, the signal path that tells the CPU or interrupt controller that hardware needs service.

### Reading the FIFO

```
Host: write 0x07 to set register pointer, then read N×6 bytes back.
       N = (write_ptr - read_ptr) mod 32
```

Each 3-byte sample is *18 bits packed in 24 bits*, the top 6 bits are zero. To extract:

```c
u32 red_sample = ((buf[0] << 16) | (buf[1] << 8) | buf[2]) & 0x3FFFF;
u32 ir_sample  = ((buf[3] << 16) | (buf[4] << 8) | buf[5]) & 0x3FFFF;
```

The chip increments its write pointer. You increment your read pointer (write to 0x06). FIFO empty when write_ptr == read_ptr.

## 79.4  How a mainline driver would work

As of v6.6, mainline does include IIO drivers, `drivers/iio/health/max30100.c` and `drivers/iio/health/max30102.c`, that handle the basics (FIFO drain via IRQ, raw red/IR/green samples to a triggered buffer). Most ecosystems still ship Arduino-style ports with the HR/SpO₂ math built in. The mainline drivers deliberately leave the DSP for user space. A complete in-kernel driver would:

1. Read part-id at probe (verify 0x15 for MAX30102).
2. Configure via DT properties (sample rate, LED current).
3. Register an IIO device with two `IIO_INTENSITY` channels (red, IR).
4. Set up triggered buffered capture using either the chip's data-ready IRQ or an hrtimer.
5. Push samples into the IIO buffer on FIFO-almost-full IRQ.

User-space then sees `/dev/iio:device0` streaming 6-byte samples at 100 Hz, processes them.

The MAX30102's data-ready IRQ pin connects to a GPIO. The driver uses `request_threaded_irq` (Ch 43) → drains the FIFO → pushes to IIO buffer (Ch 49/70). It's an IIO driver with a FIFO. Structurally identical to the IMU drivers in Ch 70–71, just with intensity channels instead of accel/gyro.
> **MCU bridge:** Think of Linux GPIO like the same pin set/reset block you used on STM32, but accessed through a kernel subsystem that owns numbering, direction, interrupts, and user-space exposure.
> **GPIO:** General-Purpose Input/Output, a pin controlled as a digital input, output, or interrupt source.

## 79.5  Writing a MAX30102 driver from scratch

We'll implement the full driver with triggered buffered IIO capture driven by the chip's data-ready IRQ. ~300 lines.

`mymax30102.c`:

```c
#include <linux/init.h>
#include <linux/module.h>
#include <linux/i2c.h>
#include <linux/delay.h>
#include <linux/iio/iio.h>
#include <linux/iio/buffer.h>
#include <linux/iio/triggered_buffer.h>
#include <linux/iio/trigger_consumer.h>
#include <linux/interrupt.h>

#define REG_INT_STATUS_1  0x00
#define REG_INT_ENABLE_1  0x02
#define REG_FIFO_WR_PTR   0x04
#define REG_FIFO_OVF      0x05
#define REG_FIFO_RD_PTR   0x06
#define REG_FIFO_DATA     0x07
#define REG_FIFO_CONFIG   0x08
#define REG_MODE_CONFIG   0x09
#define REG_SPO2_CONFIG   0x0A
#define REG_LED1_PA       0x0C
#define REG_LED2_PA       0x0D
#define REG_PART_ID       0xFF

#define PART_ID_VAL       0x15

struct mymax30102 {
    struct i2c_client *client;
    struct mutex lock;
};

static int mh_init(struct mymax30102 *m)
{
    int err, part_id;

    part_id = i2c_smbus_read_byte_data(m->client, REG_PART_ID);
    if (part_id < 0) return part_id;
    if (part_id != PART_ID_VAL) return -ENODEV;

    /* Reset */
    err = i2c_smbus_write_byte_data(m->client, REG_MODE_CONFIG, 0x40);
    if (err) return err;
    msleep(10);

    /* Enable data-ready IRQ + FIFO-almost-full */
    err = i2c_smbus_write_byte_data(m->client, REG_INT_ENABLE_1, 0xC0);
    if (err) return err;

    /* FIFO config: avg=4 samples per entry, rollover OFF, almost-full at 15 */
    err = i2c_smbus_write_byte_data(m->client, REG_FIFO_CONFIG, 0x4F);
    if (err) return err;

    /* Mode: SpO2 (both LEDs) */
    err = i2c_smbus_write_byte_data(m->client, REG_MODE_CONFIG, 0x03);
    if (err) return err;

    /* SpO2 config: ADC 4096 nA, sample rate 100 Hz, pulse width 411 µs (18-bit) */
    err = i2c_smbus_write_byte_data(m->client, REG_SPO2_CONFIG, 0x27);
    if (err) return err;

    /* LED currents (~7 mA each — about right for a fingertip; reduce for earlobe) */
    err = i2c_smbus_write_byte_data(m->client, REG_LED1_PA, 0x24);
    if (err) return err;
    err = i2c_smbus_write_byte_data(m->client, REG_LED2_PA, 0x24);
    if (err) return err;

    /* Reset FIFO pointers */
    i2c_smbus_write_byte_data(m->client, REG_FIFO_WR_PTR, 0);
    i2c_smbus_write_byte_data(m->client, REG_FIFO_OVF, 0);
    i2c_smbus_write_byte_data(m->client, REG_FIFO_RD_PTR, 0);

    return 0;
}

static int mh_read_fifo_count(struct mymax30102 *m)
{
    int wr = i2c_smbus_read_byte_data(m->client, REG_FIFO_WR_PTR);
    int rd = i2c_smbus_read_byte_data(m->client, REG_FIFO_RD_PTR);
    if (wr < 0 || rd < 0) return -EIO;
    int count = wr - rd;
    if (count < 0) count += 32;
    return count;
}

static int mh_read_one_sample(struct mymax30102 *m, u32 *red, u32 *ir)
{
    u8 buf[6];
    int err = i2c_smbus_read_i2c_block_data(m->client, REG_FIFO_DATA, 6, buf);
    if (err < 0) return err;
    if (err != 6) return -EIO;
    *red = ((buf[0] << 16) | (buf[1] << 8) | buf[2]) & 0x3FFFF;
    *ir  = ((buf[3] << 16) | (buf[4] << 8) | buf[5]) & 0x3FFFF;
    return 0;
}

/* === IIO INFO_PROCESSED (one-shot read; drains entire FIFO, returns latest) === */

static int mh_read_raw(struct iio_dev *idev,
                       struct iio_chan_spec const *chan,
                       int *val, int *val2, long mask)
{
    struct mymax30102 *m = iio_priv(idev);
    u32 red, ir;
    int err, n;

    if (mask != IIO_CHAN_INFO_RAW) return -EINVAL;

    mutex_lock(&m->lock);
    n = mh_read_fifo_count(m);
    if (n <= 0) {
        mutex_unlock(&m->lock);
        return -EAGAIN;
    }
    /* Drain all but the latest */
    while (n-- > 1) mh_read_one_sample(m, &red, &ir);
    err = mh_read_one_sample(m, &red, &ir);
    mutex_unlock(&m->lock);

    if (err) return err;

    switch (chan->channel2) {
    case IIO_MOD_LIGHT_RED:  *val = red; return IIO_VAL_INT;
    case IIO_MOD_LIGHT_IR:   *val = ir;  return IIO_VAL_INT;
    }
    return -EINVAL;
}

#define MAX_CHAN(_mod, _idx) {                                        \
    .type = IIO_INTENSITY, .modified = 1, .channel2 = (_mod),          \
    .info_mask_separate = BIT(IIO_CHAN_INFO_RAW),                      \
    .scan_index = (_idx),                                              \
    .scan_type = { .sign='u', .realbits=18, .storagebits=32,           \
                   .endianness=IIO_BE },                                \
}

static const struct iio_chan_spec mh_channels[] = {
    MAX_CHAN(IIO_MOD_LIGHT_RED, 0),
    MAX_CHAN(IIO_MOD_LIGHT_IR,  1),
    IIO_CHAN_SOFT_TIMESTAMP(2),
};

static const struct iio_info mh_iio_info = {
    .read_raw = mh_read_raw,
};

/* === IRQ handler: drain FIFO and push samples to IIO buffer === */

static irqreturn_t mh_irq_thread(int irq, void *p)
{
    struct iio_dev *idev = p;
    struct mymax30102 *m = iio_priv(idev);
    int int_status, count;
    u32 red, ir;
    u32 sample[2 + 2];     /* 2 u32 channels + 8 bytes timestamp */

    mutex_lock(&m->lock);

    int_status = i2c_smbus_read_byte_data(m->client, REG_INT_STATUS_1);
    if (int_status < 0) goto out;

    /* Either FIFO_A_FULL (bit 7) or PPG_RDY (bit 6) brought us here */
    count = mh_read_fifo_count(m);

    while (count-- > 0) {
        if (mh_read_one_sample(m, &red, &ir)) break;
        sample[0] = red;
        sample[1] = ir;
        iio_push_to_buffers_with_timestamp(idev, sample,
                                            iio_get_time_ns(idev));
    }
out:
    mutex_unlock(&m->lock);
    return IRQ_HANDLED;
}

/* === Probe / Remove === */

static int mh_probe(struct i2c_client *client)
{
    struct iio_dev *idev;
    struct mymax30102 *m;
    int err;

    idev = devm_iio_device_alloc(&client->dev, sizeof(*m));
    if (!idev) return -ENOMEM;
    m = iio_priv(idev);
    m->client = client;
    mutex_init(&m->lock);

    err = mh_init(m);
    if (err) return dev_err_probe(&client->dev, err, "init failed\n");

    idev->name = "mymax30102";
    idev->info = &mh_iio_info;
    idev->modes = INDIO_DIRECT_MODE | INDIO_BUFFER_TRIGGERED;
    idev->channels = mh_channels;
    idev->num_channels = ARRAY_SIZE(mh_channels);

    err = devm_iio_triggered_buffer_setup(&client->dev, idev,
                                           NULL, NULL, NULL);
    if (err) return err;

    if (client->irq > 0) {
        err = devm_request_threaded_irq(&client->dev, client->irq, NULL,
                                         mh_irq_thread,
                                         IRQF_TRIGGER_FALLING | IRQF_ONESHOT,
                                         "mymax30102", idev);
        if (err) return err;
    }

    return devm_iio_device_register(&client->dev, idev);
}

static const struct of_device_id mh_of_match[] = {
    { .compatible = "linuxlearn,mymax30102" },
    { }
};
MODULE_DEVICE_TABLE(of, mh_of_match);

static const struct i2c_device_id mh_id[] = { { "mymax30102", 0 }, { } };
MODULE_DEVICE_TABLE(i2c, mh_id);

static struct i2c_driver mh_driver = {
    .driver = {
        .name = "mymax30102",
        .of_match_table = mh_of_match,
    },
    .probe = mh_probe,
    .id_table = mh_id,
};
module_i2c_driver(mh_driver);

MODULE_LICENSE("GPL");
```

DT:

```dts
&i2c1 {
    max30102@57 {
        compatible = "linuxlearn,mymax30102";
        reg = <0x57>;
        interrupt-parent = <&gpio4>;
        interrupts = <13 IRQ_TYPE_EDGE_FALLING>;     /* data-ready IRQ */
    };
};
```

Test (one-shot via sysfs):
> **sysfs:** a kernel-generated filesystem under /sys that exposes devices, drivers, and attributes.

```
[root@pa-mini:~]# insmod mymax30102.ko
[root@pa-mini:~]# # Put your finger on the sensor:
[root@pa-mini:~]# cat /sys/bus/iio/devices/iio:device0/in_intensity_red_raw
102842
[root@pa-mini:~]# cat /sys/bus/iio/devices/iio:device0/in_intensity_ir_raw
108391
[root@pa-mini:~]# # Remove finger:
[root@pa-mini:~]# cat /sys/bus/iio/devices/iio:device0/in_intensity_red_raw
3214        ← ambient light only
```

Streaming via buffer:

```sh
# Enable both intensity channels + timestamp
for ch in red ir; do
    echo 1 > /sys/bus/iio/devices/iio:device0/scan_elements/in_intensity_${ch}_en
done
echo 1 > /sys/bus/iio/devices/iio:device0/scan_elements/in_timestamp_en

echo 256 > /sys/bus/iio/devices/iio:device0/buffer/length
echo 1   > /sys/bus/iio/devices/iio:device0/buffer/enable

# Each sample: 4 (red u32) + 4 (ir u32) + 8 (timestamp) = 16 bytes
dd if=/dev/iio:device0 of=ppg.bin bs=16 count=3000
```

3000 samples in 30 seconds (100 Hz). Parse offline.

## 79.6  Extracting heart rate + SpO₂ in user-space

The driver gives raw samples. The interesting work is now:

```python
import numpy as np, struct, sys
from scipy.signal import butter, filtfilt, find_peaks

# Load samples
data = np.fromfile("ppg.bin", dtype=np.uint32).reshape(-1, 4)
red = data[:, 0].astype(float)
ir  = data[:, 1].astype(float)
# (columns 2,3 are the 64-bit timestamp split as two u32; ignore for now)

# 1. Band-pass filter the IR signal: keep 0.5–4 Hz (30–240 BPM)
fs = 100.0    # sample rate
b, a = butter(4, [0.5/(fs/2), 4.0/(fs/2)], btype='band')
ir_ac = filtfilt(b, a, ir)
red_ac = filtfilt(b, a, red)

# 2. Find peaks for heart rate
peaks, _ = find_peaks(ir_ac, distance=fs * 0.4)    # min 400 ms between peaks
if len(peaks) > 1:
    intervals = np.diff(peaks) / fs   # seconds between beats
    bpm = 60.0 / intervals.mean()
    print(f"Heart rate: {bpm:.1f} BPM")

# 3. SpO2 from R-ratio
red_dc = red.mean()
ir_dc  = ir.mean()
red_ac_rms = np.sqrt(np.mean(red_ac**2))
ir_ac_rms  = np.sqrt(np.mean(ir_ac**2))
R = (red_ac_rms / red_dc) / (ir_ac_rms / ir_dc)
spo2 = 110 - 25 * R
print(f"SpO2: {spo2:.1f}% (R-ratio {R:.3f})")
```

That's the textbook approach. Production systems add:

- **Motion artifact rejection** (accelerometer cross-correlation. Gate readings during walking).
- **Auto-gain** (adjust LED currents to keep DC within the ADC's sweet spot).
- **Finger-detection** (if ir_dc < threshold, no finger present. Report "no signal").
- **FFT/autocorrelation** instead of peak-finding for noisy signals.

Maxim's reference code includes the algorithm. Apple Watch's algorithm is patented and proprietary. For a hobby/demo: peak-finding + a 10-second running average works.

## 79.7  Lab

1. **Wire MAX30102** to your I²C bus + a GPIO for the IRQ.
2. **Build and load `mymax30102.ko`.** Verify probe in dmesg.
3. **Bare-finger test.** Cover the sensor with your fingertip. Verify red_raw and ir_raw jump from ~3000 (ambient) to 100k+.
4. **Stream + process.** Capture 30 s of data. Use a Python script (see §79.6) to extract HR. Compare to a real pulse oximeter or your own pulse rate (count for 15 s × 4).
5. **SpO₂ check.** Compute R-ratio + SpO₂. At rest, healthy adults are 95–99 %. Compare to medical pulse-oximeter on the other finger if available.
6. **Motion artifacts.** Capture while moving the sensor. Verify HR-extraction algorithm goes haywire. This is why fitness watches use accelerometer-gated HR.
7. **LED current sweep.** Vary `LED1_PA` and `LED2_PA` from 0x10 to 0x60. Observe DC level scaling linearly. Higher currents = stronger signal but higher noise from photodiode saturation.
8. **Compare against a MAX30100** (if available). Same code. Different chip-id. ~14-bit vs 18-bit visible in signal SNR.

## 79.8  Pitfalls

> **Driver choice:** Use the in-tree, maintained driver first.
> Use out-of-tree, spidev, or custom-driver paths only after you accept the kernel-version maintenance cost and document who owns updates.


- **Sensor in direct sun.** Photodiode saturated by ambient IR. DC level pinned at max. No pulsatile signal. Use indoor or covered.
- **Loose finger placement.** Tiny finger movements look like enormous "pulses." Mechanical fixturing matters, clip designs work, finger-on-flat-board doesn't.
- **Cold fingers.** Reduced peripheral perfusion → weak AC signal. SpO₂ readings unreliable. Warm hands. Or use earlobe.
- **No DC tracking.** Naive AC extraction (just band-pass) fails when DC drifts with finger pressure. Real algorithms track DC adaptively.
- **R-ratio calibration off.** The 110-25·R formula is for one specific chip's geometry. Use Maxim's chip-specific table for accuracy. Don't claim "medical-grade SpO₂" without proper calibration against a reference oximeter.
- **FIFO overflow.** If user-space drains slower than 100 Hz × 6 bytes = 600 B/s, FIFO overflows. Check REG_FIFO_OVF (0x05) and warn.
- **IRQ pin polarity.** Open-drain output, active-low. Pull-up to 3.3V required.
- **18-bit data in 24-bit container.** Top 6 bits are zero, they're padding. Mask with 0x3FFFF or the math goes wrong.
- **No mainline IIO driver.** Multiple out-of-tree implementations exist. Quality varies. Writing your own from §79.5 is reasonable.

## 79.9  Going deeper

- **MAX30102 datasheet (Maxim 19-7740 Rev 1)**: full register map.
- **Maxim app note AN6409**: "PPG signal processing on MAX30102."
- **Maxim's reference C library** (Arduino-flavored but algorithmically clear), at `github.com/MaximIntegratedRefDesTeam/`.
- **`drivers/iio/light/`**: IIO INTENSITY-channel drivers for comparison.
- **`scipy.signal`** documentation, Butterworth, peak-finding.
- **PhysioNet**: open-access ECG/PPG signal databases for testing algorithms.
- **WHO SpO₂ measurement guidelines**: for understanding what "medical-grade" means.

---

> **End of Group F, Specialty sensors (Ch 77–79).** Three sensors that each represent a different driver pattern: 1-Wire's bit-bang master + slave-driver split (Ch 77), I²S audio capture without a chip driver (Ch 78), and an IIO chip with FIFO + user-space DSP (Ch 79).

> Next chapter: **Chapter 80: External ADCs (ADS1115 / ADS1256 / MCP3008 / AD7606).** When the SoC's internal ADC isn't accurate enough, fast enough, or has the wrong number of channels.
