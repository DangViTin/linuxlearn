---
chapter: 78
title: MEMS microphones (INMP441 / ICS-43434)
part: VII — Device cookbook
estimated_pages: 18
status: draft
---

# Chapter 78 — MEMS microphones

> **What:** digital MEMS microphones — the chips that replaced analog electret mics in everything from phones to wearables. We focus on **I²S** mics (TDK InvenSense **INMP441**, TDK **ICS-43434**) and contrast with **PDM** mics. Plus the ASoC machine-driver pattern needed to wire one to the i.MX6ULL SAI, since this is one case where you really do write a small "machine driver" but not a chip driver.
>
> **Why:** every smart speaker, voice-assistant, voice-controlled IoT device, dashcam, drone for FAA-broadcast — they all have one or more digital microphones. The mic outputs already-digitized PCM (or PDM); no separate ADC or codec required. The driver structure is unusual: there's no codec chip with registers, just a simple I²S DAI. The ASoC `simple-card` machine driver handles this exact pattern.
>
> **Focus:** A digital MEMS mic is, from Linux's view, an I²S DAI without any control interface — clocks in, samples out. It samples audio internally, outputs PCM on SD when WS/LR-clock + BCLK are running. To the SAI driver, the mic is just an I²S slave. Wire SAI to the mic in DT via `simple-audio-card`, then `arecord` captures the audio. That is the whole audio-input pipeline.
>
> **Tooling.** This chapter uses `alsa-utils` (`arecord`, `aplay`), `i2c-tools`.
> - **Ubuntu-base (target):** `apt install alsa-utils i2c-tools`
> - **Buildroot:** `BR2_PACKAGE_ALSA_UTILS=y BR2_PACKAGE_I2C_TOOLS=y`
> - Full per-tool reference: [Userspace tooling appendix](../part5-rootfs/appendix-tooling.md).

## 78.1  Sensor comparison

| | TDK InvenSense INMP441 | TDK ICS-43434 | TDK ICS-41350 (PDM) |
|---|---|---|---|
| Interface | I²S | I²S | PDM (1-bit pulse-density) |
| Sample rate | 7.19 – 52.7 kHz | 7.19 – 51.6 kHz | 1.024 – 3.072 MHz PDM (decimates to ~48 kHz) |
| Resolution | 24-bit | 24-bit | 1-bit out, 16-bit after decimation |
| SNR | 61 dBA | 65 dBA | 64 dBA |
| Sensitivity | -26 dBFS @ 94 dB SPL | -26 dBFS | -26 dBFS |
| Acoustic overload (AOP) | 120 dB SPL | 116 dB SPL | 130 dB SPL |
| Idle current | 0.5 mA | 0.6 mA | 0.6 mA |
| Stereo (L/R select) | LR pin selects L or R channel | LR pin | LR pin |
| Package | 6-pin LGA | 6-pin LGA | 5-pin LGA |
| Volume price | $1.50–2.50 | $2–3.50 | $1.50–2.50 |

**Pick guide:**
- **INMP441**: cheap, common, fine for voice. Default choice.
- **ICS-43434**: lower noise; better for music or low-volume signal.
- **PDM**: more compact wiring (1-bit data); but needs the SoC's PDM-decoder hardware. i.MX6ULL's SAI has *only I²S*, no native PDM. So PDM mics are awkward on i.MX6ULL — skip.

## 78.2  I²S protocol primer

I²S is a 3-wire serial audio standard:

- **BCLK** (bit clock): one transition per bit.
- **LRCLK** (word/frame clock): toggles once per sample, marking left vs right channel.
- **SD** (serial data): the audio bits.

For a 48 kHz / 24-bit stereo stream:

- LRCLK = 48 kHz square wave (low = L word, high = R word).
- BCLK = 48 kHz × 64 = 3.072 MHz (64 bits per stereo sample, conventional even for 24-bit data).
- SD = MSB-first, 24 bits per word, padded with zeros to fill the 32-bit slot.

The "master" generates BCLK + LRCLK. The "slave" follows. For a microphone, the SoC is master, mic is slave. The mic drives SD whenever LRCLK matches its programmed channel.

```
   LRCLK:  ──────────┐         ┌─────────────┐
                     │  L word │             R word ...
                     └─────────┘
   BCLK:   ┐_┌─┐_┌─┐_┌─┐_┌─┐_┌─┐ ...  (free-running)

   SD:     ────── 24 bits of L sample ──────── 24 bits of R sample ────
```

The mic outputs its sample MSB-first during its assigned LRCLK phase. Single mic → mono; two mics with LR-select pin strapped opposite → stereo.

## 78.3  How the data flows in Linux

```
   Microphone (INMP441) ──[I²S]──► SAI (CPU DAI on i.MX6ULL)
                                       ↓ DMA
                                  DDR ring buffer
                                       ↓
                                  ALSA core
                                       ↓
                              /dev/snd/pcmC0D0c  ← user-space arecord reads
```

There's no I²C control — the mic has no registers. The wires alone (BCLK, LRCLK, SD, LR-select strap) determine its behavior.

### What the kernel needs

The kernel needs an ASoC sound card consisting of:

1. **CPU DAI**: the i.MX SAI driver (mainline, no work).
2. **Codec DAI**: a stub representing the mic. The mainline driver for this is called **`dmic`** (digital mic) or — for I²S mics specifically — there's no chip driver because the mic has no registers; the *ASoC machine driver* uses a fake codec.
3. **Machine driver**: wires the two DAIs together. Use **`simple-audio-card`** for this.

`simple-audio-card` (in `sound/soc/generic/simple-card.c`) is a generic ASoC machine driver. You describe the audio topology in DT; the driver builds a working sound card from the description. No coding required.

## 78.4  Device tree for INMP441 → SAI2

```dts
&sai2 {
    pinctrl-names = "default";
    pinctrl-0 = <&pinctrl_sai2>;
    assigned-clocks = <&clks IMX6UL_CLK_SAI2_SEL>,
                      <&clks IMX6UL_CLK_SAI2>;
    assigned-clock-parents = <&clks IMX6UL_CLK_PLL4_AUDIO_DIV>;
    assigned-clock-rates = <0>, <24576000>;
    status = "okay";
};

/* The "codec" is a fake — INMP441 has no control interface */
dmic_codec: dmic-codec {
    compatible = "dmic-codec";
    #sound-dai-cells = <0>;
};

sound {
    compatible = "simple-audio-card";
    simple-audio-card,name = "imx-inmp441";
    simple-audio-card,format = "i2s";
    simple-audio-card,bitclock-master = <&cpu_dai>;
    simple-audio-card,frame-master = <&cpu_dai>;

    cpu_dai: simple-audio-card,cpu {
        sound-dai = <&sai2>;
    };

    simple-audio-card,codec {
        sound-dai = <&dmic_codec>;
    };
};
```

Three nodes:

1. **`&sai2`**: enable the i.MX SAI2 peripheral. The mainline `fsl_sai.c` handles it.
2. **`dmic_codec`**: a *fake* codec node. The mainline `sound/soc/codecs/dmic.c` driver (`compatible = "dmic-codec"`) is a generic "digital microphone" placeholder — no registers, no control, just claims to be an ASoC codec DAI.
3. **`sound`**: the machine. `simple-audio-card` reads this and builds the sound card by wiring sai2's DAI to dmic_codec's DAI. `bitclock-master = <&cpu_dai>` tells the framework that the SoC generates BCLK.

After boot:

```
[root@pa-mini:~]# arecord -l
**** List of CAPTURE Hardware Devices ****
card 0: imxinmp441 [imx-inmp441], device 0: 308b000.sai-dmic-hifi dmic-hifi-0 []
```

The mic appears as a capture device. Now record:

```
[root@pa-mini:~]# arecord -D plughw:0,0 -f S32_LE -r 48000 -c 1 -d 5 test.wav
Recording WAVE 'test.wav' : Signed 32 bit Little Endian, Rate 48000 Hz, Mono
```

The `S32_LE` format is required because INMP441 outputs 24 bits in a 32-bit slot. ALSA can downconvert to 16-bit via `plughw` (the `plug` prefix); writing directly to `hw:0,0` requires S32_LE.

Listen back on the host machine: it'll be quiet (single mic, low input) but speech should be audible.

## 78.5  How the SAI + DMA + ALSA pipeline works

Worth understanding even when you do not write the drivers yourself:

1. **SAI** is the i.MX's I²S peripheral. The mainline `fsl_sai.c` driver:
   - Configures BCLK and LRCLK from a parent clock (the PLL4_AUDIO_DIV in our DT, at 24.576 MHz — exactly 512 × 48 kHz, a "perfect" rate for audio).
   - Programs its TX/RX FIFO settings.
   - Sets up an SDMA channel to copy RX FIFO → DDR (Ch 51).
   - Implements the ASoC `snd_soc_dai_ops`: `set_fmt` (I²S vs left-justified), `hw_params` (sample rate, channels), `trigger` (start/stop).

2. **ASoC core** binds the SAI DAI (CPU side) to the `dmic-codec` DAI (codec side). At `hw_params` time, both DAIs negotiate format and sample rate.

3. **PCM substream**: ALSA creates a substream backed by a DMA-coherent ring buffer in DDR. The SAI's SDMA channel writes into it cyclically (Ch 51.5).

4. **User-space**: opens `/dev/snd/pcmC0D0c`, configures format/rate via ioctl, reads samples. Reads block until enough data is available; ALSA copies from the ring buffer.

In the data path: mic → BCLK timing → SD bits → SAI's RX FIFO → SDMA → DDR ring buffer → memcpy → user-space buffer. Zero CPU between mic and SDMA; one memcpy per `read()`.

## 78.6  A "machine driver" you might write

`simple-audio-card` handles most use cases. But for unusual topologies (multiple mics with different formats; on-the-fly clock-rate changes; DAPM widgets representing mute relays), you may write a custom machine driver. The shape:

```c
/* sound/soc/fsl/my-mic-machine.c — sketch */

static struct snd_soc_dai_link my_dai = {
    .name           = "mic-link",
    .stream_name    = "mic-capture",
    .cpus           = SND_SOC_DAILINK_REGn(cpu, "30030000.sai"),
    .codecs         = SND_SOC_DAILINK_REGn(codec, "dmic-codec"),
    .platforms      = SND_SOC_DAILINK_REGn(platform, "30030000.sai"),
    .dai_fmt        = SND_SOC_DAIFMT_I2S
                    | SND_SOC_DAIFMT_NB_NF
                    | SND_SOC_DAIFMT_CBC_CFC,
    .ops            = &my_dai_ops,
};

static struct snd_soc_card my_card = {
    .name      = "imx-inmp441-custom",
    .owner     = THIS_MODULE,
    .dai_link  = &my_dai,
    .num_links = 1,
};

static int my_probe(struct platform_device *pdev)
{
    my_card.dev = &pdev->dev;
    return devm_snd_soc_register_card(&pdev->dev, &my_card);
}
```

Roughly 70 lines. Same shape as Ch 53's WM8960 machine driver, only without the codec controls, DAPM widgets, and jack-detection.

For most cases: Most projects do not need a custom machine driver. Use `simple-audio-card` in DT.

## 78.7  Stereo with two mics

Two INMP441s on the same bus, one strapped LR=GND (Left), one strapped LR=VDD (Right):

```
   ┌── SD ─────────────────► both mics share SD
   ├── BCLK ───────────────► both
   ├── LRCLK ──────────────► both
   ┌── INMP441 #1, LR → GND  (drives SD during left phase)
   └── INMP441 #2, LR → VDD  (drives SD during right phase)
```

Both mics monitor LRCLK; each drives SD only during its assigned phase. The SoC sees stereo without any extra wires.

DT: change `simple-audio-card,routing` to declare two channels; the kernel doesn't need to know how many mics — that's a wiring choice.

```sh
[root@pa-mini:~]# arecord -D plughw:0,0 -f S32_LE -r 48000 -c 2 -d 5 stereo.wav
```

The captured file plays back in stereo on the host.

## 78.8  Lab

1. **Wire INMP441 to SAI2** on the i.MX6ULL: BCLK, LRCLK (=WS), SD, VDD, GND, LR-strap.
2. **Add DT.** Both `&sai2` and `simple-audio-card` as in §78.4.
3. **Verify enumeration.** `arecord -l` should show the mic. `cat /proc/asound/cards`.
4. **Record.** `arecord -D plughw:0,0 -f S32_LE -r 48000 -c 1 -d 5 voice.wav`. Speak; copy file to host; play back. Speech should be clear though quiet.
5. **Check volume.** Run `arecord ... | aplay` (loopback on the same i.MX, with speakers via Ch 53). Hear yourself.
6. **Stereo.** Add a second INMP441, strap LR opposite. Record 2-channel. Check L and R are different (cover one mic while recording; that channel goes quiet).
7. **Sample-rate variation.** Try 16 kHz, 32 kHz, 48 kHz. Verify the chip + SAI cooperate.
8. **FFT in user-space.** Pipe `arecord` into a small program that does FFT over 8192-sample windows; plot spectrum live with gnuplot. Watch frequencies appear as you whistle.

## 78.9  Pitfalls

- **Wrong format.** INMP441 outputs 24-bit MSB-first I²S. Configure for S32_LE in ALSA. The 24 audio bits sit in the high 24 bits of the 32-bit slot; the bottom 8 bits are zero. S24_LE *may* work depending on ASoC version.
- **MCLK not provided.** Some I²S mics need an MCLK in addition to BCLK + LRCLK. INMP441 does *not*; ICS-43434 also doesn't. But other I²S codecs do. Verify against datasheet.
- **Master/slave mismatch.** Both SoC and mic configured as slaves → no clock generated. INMP441 is always a slave (chip can't generate clocks).
- **WS polarity wrong.** Some chips expect LRCLK = HIGH for left; others use LOW. `simple-audio-card,format = "i2s"` defaults to "left = LOW" (LJ vs I²S subtly differ).
- **LR-strap floating.** INMP441 reads middle state; outputs nothing or noisy data. Strap explicitly.
- **Single mic, stereo requested.** ALSA gives you a stereo stream with the second channel duplicated (or zero, depending on plug setup). For real stereo, wire two physical mics.
- **DC-offset / wind noise.** MEMS mics pick up low-frequency rumble. Apply a high-pass filter in user-space (`sox` has a `highpass 100` effect).
- **Self-noise floor not what's specified.** A 61 dBA SNR INMP441 in a quiet room measures ~33 dB SPL noise floor — anything quieter is masked. To capture whispers, choose ICS-43434 (4 dB lower noise).
- **dmic-codec compatible string.** Must be exactly `"dmic-codec"`. If the kernel was built without `CONFIG_SND_SOC_DMIC=y`, the placeholder driver is missing and the card fails to probe.

## 78.10  Going deeper

- **`sound/soc/generic/simple-card.c`** — read the parsing logic to understand what `simple-audio-card` accepts.
- **`sound/soc/codecs/dmic.c`** — the dmic placeholder driver (~150 lines).
- **`sound/soc/fsl/fsl_sai.c`** — the i.MX SAI driver.
- **`Documentation/devicetree/bindings/sound/simple-card.yaml`** — DT binding reference.
- **INMP441 datasheet (TDK InvenSense)** — timing diagram, LR-strap behavior.
- **ICS-43434 datasheet** — similar, with the SNR improvement.
- **ALSA documentation** at <https://www.alsa-project.org/> for advanced topics (ringbuffer tuning, sample-rate conversion).

> Next chapter: **Chapter 79 — Health sensors (MAX30100 / MAX30102).** PPG-based heart-rate and SpO₂ measurement; the I²C interface with FIFO + the user-space DSP to extract HR/SpO₂.
