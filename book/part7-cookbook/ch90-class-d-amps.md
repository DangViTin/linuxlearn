---
chapter: 90
title: Digital class-D amplifiers (TAS5805M / MAX98357A / PCM5102A)
part: VII — Device cookbook
estimated_pages: 16
status: draft
---

# Chapter 90 — Digital class-D amplifiers

> **What:** "audio output without a codec." These chips take I²S directly and drive a speaker (class-D amp) or headphones (DAC). They have no ADC, no mic input, and no input mixer — just a digital-in, analog-out path. Three chips: **TI MAX98357A** (pure I²S → 3.2 W speaker, *no control interface at all*), **TI TAS5805M** (I²C-controlled DSP class-D amp), **TI PCM5102A** (I²S → headphone DAC, no control). For each: the ASoC component model for a control-less or simply-controlled device, and from-scratch drivers. The MAX98357A driver is extremely short. The TAS5805M shows DSP-coefficient loading.
> **ASoC** - ALSA System-on-Chip, the embedded audio layer that connects CPU audio ports, codecs, and board wiring.
>
> **Why:** for *playback-only* products — a Bluetooth speaker, a voice-announcement system, a doorbell chime, a kiosk that plays sounds — a full codec (Ch 89) is overkill. All you need is to turn I²S into sound. These chips do exactly that, cheaper and simpler. The MAX98357A needs zero configuration. Wire I²S, pick L/R/mono with a resistor, and it plays.
>
> **Focus:** an amp without a control bus is the simplest ASoC component you can write. The MAX98357A driver is ~100 lines and has no registers — it's a DAPM widget (the amp) + a DAI (the I²S sink) + maybe an enable GPIO. The TAS5805M adds I²C control + a DSP that needs a coefficient blob loaded. Driver complexity tracks chip capability — dumb amp short, DSP amp long.
> MCU bridge: Think of Linux GPIO like the same pin set/reset block you used on STM32, but accessed through a kernel subsystem that owns numbering, direction, interrupts, and user-space exposure.
> **GPIO** - General-Purpose Input/Output, a pin controlled as a digital input, output, or interrupt source.
>
> **Tooling.** This chapter uses `alsa-utils`, `i2c-tools`.
> **ALSA** - Linux's kernel and user-space audio stack.
> - **Ubuntu-base (target):** `apt install alsa-utils i2c-tools`
> - **Buildroot:** `BR2_PACKAGE_ALSA_UTILS=y BR2_PACKAGE_I2C_TOOLS=y`
> **Buildroot** - a configuration-driven build system that produces a complete root filesystem and related images.
> - Full per-tool reference: [Userspace tooling appendix](../part5-rootfs/appendix-tooling.md).
> MCU bridge: Think of the rootfs as the firmware image's file-backed runtime environment. On an MCU you link everything into flash. On Linux, programs and config live in this mounted tree.
> **rootfs** - root filesystem, the directory tree mounted at / that contains /bin, /etc, /dev, and libraries.


## 90.1  Chip comparison

| | TI MAX98357A | TI TAS5805M | TI PCM5102A |
|---|---|---|---|
| Function | I²S → speaker amp | I²S → DSP → speaker amp | I²S → headphone DAC |
| Power output | 3.2 W (4 Ω) | 2× 23 W (stereo) | line/headphone level |
| Control | none (config pins) | I²C (DSP + volume + EQ) | none (config pins) |
| DSP features | none | EQ, crossover, DRC, bass boost | none |
| Channels | mono (L/R/avg via pin) | stereo | stereo |
| DAC SNR | 98 dB | 110 dB | 112 dB |
| Sample rates | 8–96 kHz | 32–96 kHz | 8–384 kHz |
| Volume price | $1.50–2.50 | $4–6 | $2–4 |
| Mainline driver | `max98357a.c` | `tas5805m.c` | `pcm5102a` via `pcm512x.c` family / `simple-audio-card` |

**Pick guide:**
- **MAX98357A**: simplest possible "make sound from I²S." Mono. Bluetooth speakers, voice prompts. *Zero config.*
- **TAS5805M**: when you want EQ / bass boost / dynamic-range control done in hardware — a real speaker product with tuning.
- **PCM5102A**: headphone/line-out DAC. audiophile-grade SNR. no amp.

## 90.2  MAX98357A — the zero-config amp

The MAX98357A is as simple as it gets. It has **no I²C, no SPI, no registers**. Configuration is via *hardware pins*:

- **SD_MODE pin**: tied via a resistor to select left channel / right channel / (L+R)/2 average / shutdown. (A resistor divider on one pin encodes 4 states.)
- **GAIN_SLOT pin**: sets amp gain (3/6/9/12/15 dB) and which I²S slot to use.

Wire up I²S (BCLK, LRCLK, DIN), power, and a speaker. It plays. The "driver" just needs to:
1. Declare a DAI (the I²S sink).
2. Declare a DAPM widget (the amp output).
3. Optionally manage an enable/shutdown GPIO.

There is no register access in the driver because the chip has no registers.

## 90.3  Writing a MAX98357A-style driver from scratch

`mymax98357.c`:

```c
#include <linux/init.h>
#include <linux/module.h>
#include <linux/platform_device.h>
#include <linux/gpio/consumer.h>
#include <sound/soc.h>
#include <sound/soc-dapm.h>

struct mymax {
    struct gpio_desc *sdmode_gpio;     /* shutdown/mode control */
};

/* DAPM: the speaker amp output, gated by the SD_MODE GPIO */
static int mymax_event(struct snd_soc_dapm_widget *w,
                       struct snd_kcontrol *kc, int event)
{
    struct snd_soc_component *comp = snd_soc_dapm_to_component(w->dapm);
    struct mymax *m = snd_soc_component_get_drvdata(comp);

    /* Power the amp on when the route activates, off when it deactivates */
    gpiod_set_value_cansleep(m->sdmode_gpio,
                             SND_SOC_DAPM_EVENT_ON(event) ? 1 : 0);
    return 0;
}

static const struct snd_soc_dapm_widget mymax_widgets[] = {
    SND_SOC_DAPM_OUT_DRV_E("Amp", SND_SOC_NOPM, 0, 0, NULL, 0,
                           mymax_event,
                           SND_SOC_DAPM_PRE_PMU | SND_SOC_DAPM_POST_PMD),
    SND_SOC_DAPM_OUTPUT("Speaker"),
};

static const struct snd_soc_dapm_route mymax_routes[] = {
    { "Amp", NULL, "HiFi Playback" },
    { "Speaker", NULL, "Amp" },
};

static const struct snd_soc_component_driver mymax_component = {
    .dapm_widgets     = mymax_widgets,
    .num_dapm_widgets = ARRAY_SIZE(mymax_widgets),
    .dapm_routes      = mymax_routes,
    .num_dapm_routes  = ARRAY_SIZE(mymax_routes),
    .idle_bias_on     = 1,
};

/* The DAI: a pure I²S sink. No hw_params logic needed — the chip
 * auto-detects sample rate from the I²S clocks. */
static struct snd_soc_dai_driver mymax_dai = {
    .name = "HiFi",
    .playback = {
        .stream_name = "HiFi Playback",
        .formats = SNDRV_PCM_FMTBIT_S16_LE | SNDRV_PCM_FMTBIT_S24_LE
                 | SNDRV_PCM_FMTBIT_S32_LE,
        .rates = SNDRV_PCM_RATE_8000_96000,
        .rate_min = 8000, .rate_max = 96000,
        .channels_min = 1, .channels_max = 2,
    },
};

static int mymax_probe(struct platform_device *pdev)
{
    struct mymax *m;

    m = devm_kzalloc(&pdev->dev, sizeof(*m), GFP_KERNEL);
    if (!m) return -ENOMEM;

    /* Optional shutdown GPIO (SD_MODE) */
    m->sdmode_gpio = devm_gpiod_get_optional(&pdev->dev, "sdmode", GPIOD_OUT_LOW);
    if (IS_ERR(m->sdmode_gpio))
        return PTR_ERR(m->sdmode_gpio);

    platform_set_drvdata(pdev, m);

    return devm_snd_soc_register_component(&pdev->dev, &mymax_component,
                                           &mymax_dai, 1);
}

static const struct of_device_id mymax_of_match[] = {
    { .compatible = "linuxlearn,mymax98357a" },
    { }
};
MODULE_DEVICE_TABLE(of, mymax_of_match);

static struct platform_driver mymax_driver = {
    .driver = {
        .name = "mymax98357a",
        .of_match_table = mymax_of_match,
    },
    .probe = mymax_probe,
};
module_platform_driver(mymax_driver);

MODULE_LICENSE("GPL");
```

DT:

```dts
amp: codec {
    compatible = "linuxlearn,mymax98357a";
    #sound-dai-cells = <0>;
    sdmode-gpios = <&gpio4 14 GPIO_ACTIVE_HIGH>;
};

sound {
    compatible = "simple-audio-card";
    simple-audio-card,name = "imx-spk";
    simple-audio-card,format = "i2s";
    simple-audio-card,bitclock-master = <&cpudai>;
    simple-audio-card,frame-master = <&cpudai>;
    cpudai: simple-audio-card,cpu { sound-dai = <&sai2>; };
    simple-audio-card,codec { sound-dai = <&amp>; };
};
```

Note: it's a **platform_device** (not I²C/SPI) because there's no control bus — the chip is configured by pins. Test:

```
[root@pa-mini:~]# insmod mymax98357a.ko
[root@pa-mini:~]# aplay -l
card 0: imxspk [imx-spk], device 0: ...
[root@pa-mini:~]# aplay test.wav     # plays through the speaker
```

~100 lines. The `OUT_DRV_E` widget's event callback toggles the SD_MODE GPIO with the route. The amp is on during playback and off when idle, saving power. That is the only "logic" in the driver.

The mainline `max98357a.c` is similar (~150 lines) — adds the GAIN gpio and a small refinement, but it's the same shape. This is the floor of ASoC complexity.

## 90.4  PCM5102A — same idea, headphone DAC

The PCM5102A is also control-less (config via pins: format, de-emphasis, mute). It outputs analog line/headphone level from I²S. The "driver" is the same shape as the MAX98357A — a DAI + a DAPM output widget, no registers.

In fact, many such control-less DACs/amps don't need a *custom* driver at all — `simple-audio-card` can use a generic "spdif-transmitter" or "dummy codec" stand-in, or the chip-specific stub driver. For PCM5102A, the `pcm512x` family driver covers the controllable variants (PCM5121/5122 with I²C). The bare PCM5102A uses a fixed-function stub.

## 90.5  TAS5805M — the DSP amp

The TAS5805M sits at the other end. It is a 2×23 W stereo class-D amp with an **on-chip DSP** that provides:
- Parametric EQ (15 biquads per channel).
- Dynamic range control (compression/limiting).
- Bass boost / loudness.
- Crossover filters (for biamped speakers).

All of this is configured over I²C. The DSP runs a *coefficient set*. You compute biquad coefficients (for example, from a target frequency response) and load them into the chip's coefficient RAM.

### The configuration model

```
1. Reset, set I²S format, sample rate.
2. Load a "book + page" of register settings (TI's tool generates these).
3. Load DSP coefficients (the EQ/DRC/crossover tuning) into coefficient pages.
4. Set volume.
5. Switch from HiZ → PLAY mode.
```

The "book + page" model: the TAS5805M's register space is paged (256 registers per page, multiple pages, organized into "books"). You select a book (write reg 0x7F), select a page (write reg 0x00), then access the page's registers. The DSP coefficients live in specific book/page locations.

TI provides **PPC3** (a GUI tool) to design the EQ/DRC and export a register-write sequence (a `.h` file or a binary blob). The driver replays this blob at probe — like the camera (Ch 87) and ToF (Ch 72) register blobs.

### Mainline driver

`sound/soc/codecs/tas5805m.c` registers an ASoC component with:
- A volume control.
- The init sequence loaded from a firmware blob (`/lib/firmware/tas5805m_dsp.bin`).
- DAPM for the amp.

```c
/* Simplified: load the DSP config blob */
static int tas5805m_load_config(struct tas5805m_priv *tas)
{
    const struct firmware *fw;
    int err = request_firmware(&fw, "tas5805m_dsp.bin", tas->dev);
    if (err) return err;

    /* The blob is a sequence of (reg, val) or book/page-switch commands */
    err = tas5805m_process_block(tas, fw->data, fw->size);
    release_firmware(fw);
    return err;
}
```

The blob is your speaker tuning. A from-scratch TAS5805M driver would: regmap for the paged register access, a firmware-blob loader for the DSP config, a volume control, and DAPM — roughly the WM8960 shape from Ch 89 plus the book/page paging and the firmware blob. We won't reproduce the full driver. The *new* concept beyond Ch 89 is the book/page paging + the externally-designed DSP coefficient blob.
MCU bridge: Think of regmap like a typed wrapper around your read_reg() and write_reg() helpers, with caching, locking, and bus differences handled centrally.
**regmap** - a kernel helper that wraps register reads and writes over I2C, SPI, or MMIO.

### Designing the DSP config

The interesting part for a product: you measure your speaker's frequency response (with a calibrated mic), design a corrective EQ in PPC3, and export the blob. The TAS5805M then *fixes the speaker's acoustic flaws in hardware*. Good DSP tuning makes a $5 speaker sound much better than its physical parts deserve. This is why DSP class-D amps are standard in smart speakers.

## 90.6  The Bluetooth-speaker product pattern

A common product: a Bluetooth speaker on i.MX6ULL.

```
   Phone ──[A2DP/Bluetooth]──► BlueZ (Ch 95) ──► ALSA ──► SAI (I²S) ──► TAS5805M ──► speaker
```

- BlueZ receives the A2DP stream, decodes SBC/AAC to PCM.
- PCM goes to ALSA → the SAI → I²S.
- The TAS5805M's DSP applies EQ + limiting, drives the speaker.

The i.MX6ULL does the Bluetooth + decode. The TAS5805M does the analog + acoustic tuning. No full codec needed (playback only). This is the standard "amp without a codec" product pattern.

## 90.7  Lab

1. **MAX98357A bring-up.** Wire I²S + SD_MODE + speaker. Build `mymax98357a.ko`. `aplay test.wav`. hear sound.
2. **SD_MODE channel select.** Change the SD_MODE resistor to select L / R / (L+R)/2. verify the channel routing.
3. **DAPM power.** Confirm the SD_MODE GPIO goes high on play, low on stop (scope it or read the GPIO). Amp is off when idle → no idle hiss.
4. **PCM5102A.** Wire one as a headphone DAC. Use `simple-audio-card`. verify line-out audio.
5. **TAS5805M bring-up.** Wire I²C + I²S + speaker. Use the mainline driver with a DSP blob. Verify playback.
6. **EQ tuning.** Use TI PPC3 (on a PC) to design a bass boost. export the blob. load it. A/B the sound with/without.
7. **Bluetooth speaker.** Combine BlueZ A2DP (Ch 95) + TAS5805M. pair a phone. play music. tune the EQ for your enclosure.

## 90.8  Pitfalls

- **MAX98357A SD_MODE resistor wrong.** The resistor value encodes channel select. wrong value = wrong channel or shutdown. Use the datasheet's resistor table exactly.
- **No DAI → no sound.** Even a control-less amp needs an ASoC DAI registered so the machine driver can bind it. The "dummy codec" must still expose a DAI.
- **MAX98357A idle hiss.** If SD_MODE stays high when idle, the amp's output stage hisses. Gate it via the DAPM event callback (amp off when no stream).
- **TAS5805M book/page confusion.** Forgetting to select the right book/page before a register access writes to the wrong location → garbage config or no sound. The paging model is error-prone. follow TI's sequence exactly.
- **TAS5805M PLAY/HiZ state.** The amp must be explicitly switched to PLAY mode after config. Left in HiZ → silent.
- **Sample-rate mismatch.** The amp auto-detects rate from I²S clocks (MAX98357A) or must be told (TAS5805M). A mismatch → wrong pitch or no audio.
- **Speaker impedance vs amp.** A 3.2 W amp into a 4 Ω speaker is fine. into 32 Ω headphones it's too weak. Match amp to load.
- **Class-D EMI.** Class-D amps switch at ~400 kHz. The speaker leads radiate. Keep leads short, use ferrites/filters, or fail EMC.
- **Power supply for the amp.** A 2×23 W TAS5805M needs a beefy supply (peaks > 4 A). Brownouts cause clipping/reset. Budget the rail.

## 90.9  Going deeper

- **`sound/soc/codecs/max98357a.c`** — the production driver. Compare to the from-scratch version — nearly identical, ~150 lines.
- **`sound/soc/codecs/tas5805m.c`** — the DSP amp driver with firmware-blob loading.
- **`sound/soc/codecs/pcm512x.c`** — PCM510x/512x family.
- **`Documentation/sound/soc/`** — ASoC framework (same as Ch 89).
- **MAX98357A datasheet (TI/Maxim)** — the SD_MODE / GAIN resistor tables.
- **TAS5805M datasheet + PPC3 tool (TI)** — the book/page model and the EQ designer.
- **TI app note SLAA738** — TAS5805M DSP configuration.

---

> **End of Group J — Audio (Ch 89–90).** Full codecs (Ch 89: DAC+ADC+amp+mic, the WM8960 class) vs playback-only amps/DACs (Ch 90: I²S → speaker/headphone, the MAX98357A/TAS5805M class). The driver complexity spectrum — control-less amp (~100 lines) → simple codec (~200) → full codec (~1500) → DSP amp (regmap + firmware blob) — maps directly to the chip's capabilities.

> Next chapter: **Chapter 91 — SDIO WiFi.** Group K (WiFi) opens with the SDIO-attached modules (AP6212, RTL8189) — firmware loading, the brcmfmac/rtl driver stack, and the SDIO bring-up that trips up every new board.
