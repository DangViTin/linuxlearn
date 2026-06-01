---
chapter: 89
title: I²S audio codecs (WM8960 / SGTL5000 / ES8388 / TLV320AIC3104)
part: VII — Device cookbook
estimated_pages: 22
status: draft
---

# Chapter 89 — I²S audio codecs

> **What:** the analog-front-end chips that give the i.MX6ULL real audio: DAC for playback, ADC for capture, headphone and speaker drivers, mic preamps. Four codecs compared: **Cirrus WM8960** (the i.MX favourite), **NXP SGTL5000** (on many i.MX EVKs), **Everest ES8388** (cheap, ESP32-popular), **TI TLV320AIC3104** (industrial). Builds on Ch 53 (ALSA/ASoC framework). For each: the codec's role, the register/DAPM model, and a from-scratch ASoC codec driver.
> **Why:** the i.MX6ULL's SAI is a digital I²S serializer only. It has no analog audio. A codec adds the DAC/ADC/amp/mic. Ch 53 showed the three-driver ASoC split (CPU-DAI + codec + machine) with WM8960; this chapter goes *deep on the codec side* — how a codec driver is structured, what DAPM (Dynamic Audio Power Management) actually does, and how to write one from scratch.
> **Focus:** a codec driver has three parts: a regmap for register access, DAPM widgets and routes for the analog graph, and DAI ops for I²S format negotiation. The regmap (Ch 50) handles register access. The DAPM graph models the analog signal paths: DAC → mixer → headphone amp → jack. Each block is powered up only when it lies on an active route, which saves power and avoids switching clicks. The DAI ops handle the I²S format negotiation. Once you understand these three, every codec driver looks familiar.
> **Tooling.** This chapter uses `alsa-utils`, `i2c-tools`.
> - **Ubuntu-base (target):** `apt install alsa-utils i2c-tools`
> - **Buildroot:** `BR2_PACKAGE_ALSA_UTILS=y BR2_PACKAGE_I2C_TOOLS=y`
> - Full per-tool reference: [Userspace tooling appendix](../part5-rootfs/appendix-tooling.md).

## 89.1  Codec comparison

| | Cirrus WM8960 | NXP SGTL5000 | Everest ES8388 | TI TLV320AIC3104 |
|---|---|---|---|---|
| DAC SNR | 98 dB | 99.9 dB | 96 dB | 92 dB |
| ADC SNR | 94 dB | 90.5 dB | 95 dB | 92 dB |
| Outputs | stereo HP + class-D speaker | HP + line | HP + line | HP + line |
| Speaker amp | built-in 1 W class-D | no (needs ext amp) | no | no |
| Mic preamp | yes (+ boost) | yes | yes | yes |
| Control bus | I²C or 3-wire SPI | I²C | I²C | I²C |
| I²S roles | master or slave | master or slave | master or slave | master or slave |
| Sample rates | 8–48 kHz | 8–96 kHz | 8–96 kHz | 8–96 kHz |
| Volume price | $2–4 | $3–5 | $1–2 | $3–5 |
| Mainline driver | `wm8960.c` | `sgtl5000.c` | `es8328.c` (covers ES8388) | `tlv320aic3x.c` |

**Pick guide:**
- **WM8960**: has a *built-in speaker amp* — drive a speaker directly, no external amp. Default for i.MX boards.
- **SGTL5000**: best SNR; on NXP EVKs; no speaker amp.
- **ES8388**: cheapest; common on Chinese audio boards.
- **TLV320AIC3104**: industrial temperature range, robust.

## 89.2  What a codec does (and the SAI doesn't)

```
   ┌──────────────────────────────────────────────────────────┐
   │  i.MX6ULL SAI (Ch 53)                                      │
   │  - digital I²S serializer: PCM samples ↔ I²S bits          │
   │  - NO analog. NO DAC. NO mic preamp.                       │
   └──────────────────────────────────────────────────────────┘
                          │ I²S (BCLK, LRCLK, SD_TX, SD_RX)
                          │ + I²C (control)
                          ▼
   ┌──────────────────────────────────────────────────────────┐
   │  Codec (WM8960)                                            │
   │  ┌─────────┐   ┌────────┐   ┌──────────┐   ┌────────────┐ │
   │  │  DAC    │──►│ mixer  │──►│ HP amp   │──►│ headphone  │ │
   │  └─────────┘   └────────┘   │ spk amp  │──►│ speaker    │ │
   │  ┌─────────┐   ┌────────┐   └──────────┘   └────────────┘ │
   │  │  ADC    │◄──│ PGA/   │◄──── mic boost ◄──── mic jack    │
   │  └─────────┘   │ mixer  │◄──── line-in                     │
   │     ▲          └────────┘                                 │
   │   I²S in/out from SAI                                      │
   └──────────────────────────────────────────────────────────┘
```

The codec turns digital PCM into analog you can hear, and analog mic/line signals into digital PCM. The I²S carries the digital samples; I²C carries the control (volume, routing, power).

## 89.3  DAPM — Dynamic Audio Power Management

The single most important codec concept. A codec has many analog blocks (DAC, ADC, mixers, amps, bias generators). Powering them all on wastes power and the audible "click" when amps switch. **DAPM** models the analog signal flow as a *graph of widgets* and powers each widget only when it's part of an active route from a running stream to a connected jack.

Widget types:

- **Endpoints**: `SND_SOC_DAPM_HP` (headphone jack), `SND_SOC_DAPM_SPK` (speaker), `SND_SOC_DAPM_MIC` (mic jack), `SND_SOC_DAPM_LINE`.
- **DAC/ADC**: `SND_SOC_DAPM_DAC`, `SND_SOC_DAPM_ADC`.
- **Mixers**: `SND_SOC_DAPM_MIXER` (combine sources).
- **PGAs / amps**: `SND_SOC_DAPM_PGA`, `SND_SOC_DAPM_OUT_DRV`.
- **Supplies**: `SND_SOC_DAPM_SUPPLY` (a shared resource like a bias generator or PLL).

And **routes** connecting them:

```c
static const struct snd_soc_dapm_route wm8960_routes[] = {
    { "Headphone Jack", NULL, "LOUT1 PGA" },
    { "Headphone Jack", NULL, "ROUT1 PGA" },
    { "LOUT1 PGA", NULL, "Left Output Mixer" },
    { "Left Output Mixer", "PCM Playback Switch", "Left DAC" },
    { "Left DAC", NULL, "DACL" },
    ...
};
```

When you play audio: the stream activates "Left DAC"; DAPM walks the graph forward — DAC → mixer → PGA → Headphone Jack — and powers on each widget in that path. When you stop, it powers them down (in the right order to avoid pops). Blocks *not* in an active route stay off.

DAPM is why a well-written codec driver consumes µA at idle and doesn't click — and why a *badly* written one pops on every play/stop. Getting the routes and power-sequencing right is the bulk of codec-driver effort.

## 89.4  How the mainline `wm8960` driver works

Source: `sound/soc/codecs/wm8960.c` (~1500 lines).

```c
/* Simplified structure */
struct wm8960_priv {
    struct regmap *regmap;
    struct clk *mclk;
    struct snd_soc_component *component;
    /* PLL + clocking state */
};

/* Regmap config: WM8960 has 56 7-bit-address, 9-bit-value registers,
 * write-only (no read-back), so we use a register cache. */
static const struct regmap_config wm8960_regmap = {
    .reg_bits = 7,
    .val_bits = 9,
    .max_register = WM8960_PLL4,
    .reg_defaults = wm8960_reg_defaults,    /* the power-on values */
    .num_reg_defaults = ARRAY_SIZE(wm8960_reg_defaults),
    .cache_type = REGCACHE_RBTREE,           /* must cache — chip is write-only */
};
```

**Note**: WM8960 registers are *write-only* (you can't read them back). The regmap cache (Ch 50) is essential — it's the only way the driver knows the current register state. `cache_type = REGCACHE_RBTREE` + `reg_defaults` gives the driver a software shadow of the chip.

### The component + DAI

```c
static const struct snd_soc_dai_ops wm8960_dai_ops = {
    .hw_params  = wm8960_hw_params,     /* set sample rate, word length */
    .set_fmt    = wm8960_set_dai_fmt,    /* I²S vs LJ, master/slave */
    .set_sysclk = wm8960_set_dai_sysclk, /* MCLK config */
    .set_pll    = wm8960_set_dai_pll,    /* internal PLL for non-integer rates */
    .mute_stream = wm8960_mute,          /* soft-mute on start/stop (anti-pop) */
};

static struct snd_soc_dai_driver wm8960_dai = {
    .name = "wm8960-hifi",
    .playback = { .stream_name = "Playback", .channels_min = 1, .channels_max = 2,
                  .rates = SNDRV_PCM_RATE_8000_48000,
                  .formats = SNDRV_PCM_FMTBIT_S16_LE | SNDRV_PCM_FMTBIT_S24_LE },
    .capture  = { .stream_name = "Capture", ... },
    .ops = &wm8960_dai_ops,
    .symmetric_rate = 1,
};

static const struct snd_soc_component_driver wm8960_component = {
    .probe              = wm8960_probe,
    .set_bias_level     = wm8960_set_bias_level,   /* power state transitions */
    .controls           = wm8960_snd_controls,      /* volume, mute, etc. */
    .num_controls       = ARRAY_SIZE(wm8960_snd_controls),
    .dapm_widgets       = wm8960_dapm_widgets,
    .num_dapm_widgets   = ARRAY_SIZE(wm8960_dapm_widgets),
    .dapm_routes        = wm8960_dapm_routes,
    .num_dapm_routes    = ARRAY_SIZE(wm8960_dapm_routes),
};
```

### Probe

```c
static int wm8960_i2c_probe(struct i2c_client *client)
{
    struct wm8960_priv *wm8960;

    wm8960 = devm_kzalloc(&client->dev, sizeof(*wm8960), GFP_KERNEL);
    wm8960->regmap = devm_regmap_init_i2c(client, &wm8960_regmap);

    /* Reset the chip to known defaults */
    regmap_write(wm8960->regmap, WM8960_RESET, 0);

    i2c_set_clientdata(client, wm8960);

    /* Register the ASoC component + DAI */
    return devm_snd_soc_register_component(&client->dev, &wm8960_component,
                                           &wm8960_dai, 1);
}
```

That's the whole codec driver shape: regmap + DAI ops + component (controls + DAPM). The machine driver (Ch 53) wires this codec's DAI to the SAI's DAI.

## 89.5  Writing an ASoC codec driver from scratch

We'll write a minimal codec driver for a simplified codec (model: a stereo-DAC-only codec with a headphone output and a master-volume control). Real codecs are bigger, but the *structure* is identical. ~200 lines.

`mycodec.c`:

```c
#include <linux/init.h>
#include <linux/module.h>
#include <linux/i2c.h>
#include <linux/regmap.h>
#include <sound/soc.h>
#include <sound/tlv.h>

/* Imaginary register map */
#define REG_RESET     0x00
#define REG_POWER     0x01
#define REG_DAC_CTRL  0x02
#define REG_VOL_L     0x03
#define REG_VOL_R     0x04
#define REG_FORMAT    0x05
#define REG_MAX       0x10

static const struct reg_default mycodec_reg_defaults[] = {
    { REG_POWER, 0x00 }, { REG_DAC_CTRL, 0x00 },
    { REG_VOL_L, 0x79 }, { REG_VOL_R, 0x79 },
    { REG_FORMAT, 0x02 },
};

static const struct regmap_config mycodec_regmap = {
    .reg_bits = 8,
    .val_bits = 8,
    .max_register = REG_MAX,
    .reg_defaults = mycodec_reg_defaults,
    .num_reg_defaults = ARRAY_SIZE(mycodec_reg_defaults),
    .cache_type = REGCACHE_RBTREE,
};

/* --- Controls: a stereo master volume (0..127, -73 to +6 dB) --- */
static const DECLARE_TLV_DB_SCALE(vol_tlv, -7300, 100, 0);

static const struct snd_kcontrol_new mycodec_controls[] = {
    SOC_DOUBLE_R_TLV("Master Playback Volume",
                     REG_VOL_L, REG_VOL_R, 0, 127, 0, vol_tlv),
    SOC_SINGLE("DAC Mute Switch", REG_DAC_CTRL, 3, 1, 0),
};

/* --- DAPM widgets + routes --- */
static const struct snd_soc_dapm_widget mycodec_widgets[] = {
    SND_SOC_DAPM_DAC("DAC", "Playback", REG_POWER, 0, 0),
    SND_SOC_DAPM_PGA("HP Amp", REG_POWER, 1, 0, NULL, 0),
    SND_SOC_DAPM_OUTPUT("HPOUT"),
};

static const struct snd_soc_dapm_route mycodec_routes[] = {
    { "HP Amp", NULL, "DAC" },
    { "HPOUT", NULL, "HP Amp" },
};

/* --- DAI ops --- */
static int mycodec_hw_params(struct snd_pcm_substream *substream,
                             struct snd_pcm_hw_params *params,
                             struct snd_soc_dai *dai)
{
    struct snd_soc_component *comp = dai->component;
    u8 fmt;

    /* Set word length from params */
    switch (params_width(params)) {
    case 16: fmt = 0x00; break;
    case 24: fmt = 0x02; break;
    default: return -EINVAL;
    }
    snd_soc_component_update_bits(comp, REG_FORMAT, 0x03, fmt);
    return 0;
}

static int mycodec_set_fmt(struct snd_soc_dai *dai, unsigned int fmt)
{
    struct snd_soc_component *comp = dai->component;

    /* We only support I²S, codec as slave */
    if ((fmt & SND_SOC_DAIFMT_FORMAT_MASK) != SND_SOC_DAIFMT_I2S)
        return -EINVAL;
    if ((fmt & SND_SOC_DAIFMT_CLOCK_PROVIDER_MASK) != SND_SOC_DAIFMT_CBC_CFC)
        return -EINVAL;     /* codec consumer (slave) only */
    return 0;
}

static const struct snd_soc_dai_ops mycodec_dai_ops = {
    .hw_params = mycodec_hw_params,
    .set_fmt   = mycodec_set_fmt,
};

static struct snd_soc_dai_driver mycodec_dai = {
    .name = "mycodec-hifi",
    .playback = {
        .stream_name = "Playback",
        .channels_min = 2, .channels_max = 2,
        .rates = SNDRV_PCM_RATE_8000_48000,
        .formats = SNDRV_PCM_FMTBIT_S16_LE | SNDRV_PCM_FMTBIT_S24_LE,
    },
    .ops = &mycodec_dai_ops,
};

static const struct snd_soc_component_driver mycodec_component = {
    .controls         = mycodec_controls,
    .num_controls     = ARRAY_SIZE(mycodec_controls),
    .dapm_widgets     = mycodec_widgets,
    .num_dapm_widgets = ARRAY_SIZE(mycodec_widgets),
    .dapm_routes      = mycodec_routes,
    .num_dapm_routes  = ARRAY_SIZE(mycodec_routes),
    .idle_bias_on     = 1,
    .use_pmdown_time  = 1,
    .endianness       = 1,
};

static int mycodec_probe(struct i2c_client *client)
{
    struct regmap *regmap;

    regmap = devm_regmap_init_i2c(client, &mycodec_regmap);
    if (IS_ERR(regmap))
        return PTR_ERR(regmap);

    /* Reset */
    regmap_write(regmap, REG_RESET, 0x00);

    return devm_snd_soc_register_component(&client->dev, &mycodec_component,
                                           &mycodec_dai, 1);
}

static const struct of_device_id mycodec_of_match[] = {
    { .compatible = "linuxlearn,mycodec" },
    { }
};
MODULE_DEVICE_TABLE(of, mycodec_of_match);

static const struct i2c_device_id mycodec_id[] = { { "mycodec", 0 }, { } };
MODULE_DEVICE_TABLE(i2c, mycodec_id);

static struct i2c_driver mycodec_driver = {
    .driver = {
        .name = "mycodec",
        .of_match_table = mycodec_of_match,
    },
    .probe = mycodec_probe,
    .id_table = mycodec_id,
};
module_i2c_driver(mycodec_driver);

MODULE_LICENSE("GPL");
```

Three things to notice:

1. **`SOC_DOUBLE_R_TLV`** — declares a stereo volume control with a dB scale (`vol_tlv`). ALSA tools (`alsamixer`) show it as a slider with dB readout. The macro handles the L/R register pair.
2. **DAPM widgets reference power-control bits** — `SND_SOC_DAPM_DAC("DAC", "Playback", REG_POWER, 0, 0)` means "the DAC widget's power is bit 0 of REG_POWER." DAPM sets/clears that bit as the route activates/deactivates.
3. **`snd_soc_component_update_bits`** — the ASoC wrapper over regmap for read-modify-write of a register field.

The machine driver (Ch 53) binds this codec to the SAI:

```dts
sound {
    compatible = "fsl,imx-audio-mycodec";   /* or simple-audio-card */
    audio-codec = <&mycodec>;
    audio-cpu = <&sai2>;
    audio-routing = "Headphone Jack", "HPOUT";
};
```

Or with `simple-audio-card`:

```dts
sound {
    compatible = "simple-audio-card";
    simple-audio-card,name = "imx-mycodec";
    simple-audio-card,format = "i2s";
    simple-audio-card,bitclock-master = <&cpudai>;
    simple-audio-card,frame-master = <&cpudai>;
    cpudai: simple-audio-card,cpu { sound-dai = <&sai2>; };
    simple-audio-card,codec { sound-dai = <&mycodec>; };
};
```

Test:

```
[root@pa-mini:~]# insmod mycodec.ko
[root@pa-mini:~]# aplay -l
card 0: imxmycodec [imx-mycodec], device 0: ...
[root@pa-mini:~]# alsamixer        # shows "Master Playback Volume"
[root@pa-mini:~]# aplay test.wav   # plays through the codec
```

What we got, ~200 lines:
- A registered ASoC codec component.
- A master-volume control visible in `alsamixer`.
- DAPM power management of the DAC and HP amp.
- I²S format negotiation.

What WM8960 adds (the other ~1300 lines): ADC + capture path, mic preamp + boost, the speaker class-D amp, the internal PLL for non-integer sample rates, jack detection, dozens more controls, full DAPM graph with mixers.

## 89.6  Codec differences that matter

- **WM8960**: built-in 1 W class-D speaker amp — the `Speaker` DAPM route + the `SPK_LP/LN/RP/RN` outputs. Drive a speaker directly. Unique among these four.
- **SGTL5000**: best SNR; needs a specific power-up sequence (the chip has analog + digital + I/O rails that must come up in order). The mainline driver enforces it.
- **ES8388**: cheap; the mainline `es8328.c` driver covers it but the ES8388 has minor register differences — check the compatible.
- **TLV320AIC3104**: highly configurable routing (a "miniDSP" in bigger siblings); industrial temp range.

## 89.7  Lab

1. **Bring up WM8960** (or your codec) per Ch 53. Verify `aplay -l` shows it; play a WAV.
2. **From-scratch codec.** Build `mycodec.ko` (adapt registers to a real simple codec, or test the registration logic). Verify the component registers and `alsamixer` shows the volume control.
3. **DAPM trace.** `cat /sys/kernel/debug/asoc/*/dapm/*` while playing/stopping. Watch widgets power on/off. Confirm the DAC powers down when playback stops.
4. **Volume + dB.** In `alsamixer`, adjust Master volume; verify the dB readout matches the TLV scale.
5. **Capture (WM8960).** `arecord` from the mic input; verify the capture path + mic boost.
6. **Speaker (WM8960).** Route to the built-in class-D speaker amp; drive a small speaker directly (no external amp).
7. **Anti-pop.** Play/stop repeatedly; listen for clicks. A correct DAPM power-sequence + soft-mute eliminates them; comment out the mute_stream op and hear the difference.

## 89.8  Pitfalls

- **Write-only registers without a cache.** WM8960 (and many codecs) can't be read back. Without `cache_type` + `reg_defaults`, the driver loses track of state. Always cache.
- **Master/slave clock mismatch.** If both SAI and codec think they're I²S master, no bit clock. One must be slave. Set `bitclock-master`/`frame-master` in the machine DT.
- **MCLK rate wrong.** Codecs need MCLK = a specific multiple of the sample rate (e.g., 256× or 512× fs). For 48 kHz: 12.288 MHz or 24.576 MHz. Wrong MCLK → wrong pitch or no audio. Configure the SAI's clock to produce the right MCLK.
- **DAPM routes incomplete.** Audio "plays" (DMA flows) but is silent because DAPM never powered the output path. Trace the dapm debugfs.
- **Pop/click on play/stop.** Missing soft-mute or wrong power-up/down order. Implement `mute_stream` and order DAPM events.
- **Wrong codec I²C address.** WM8960 = 0x1A, SGTL5000 = 0x0A, ES8388 = 0x10/0x11. Check `i2cdetect`.
- **SGTL5000 power sequencing.** Its rails must come up in order; out-of-order = chip doesn't respond. The mainline driver handles it; a hand-rolled one must too.
- **Non-integer sample rates.** 44.1 kHz needs a fractional PLL ratio from a 12 MHz MCLK. Codecs have an internal PLL; configure `set_pll` or you only get the integer-related rates.

## 89.9  Going deeper

- **`sound/soc/codecs/wm8960.c`** — the production codec driver. Compare structure to the from-scratch version.
- **`sound/soc/codecs/sgtl5000.c`** — note the power-sequencing.
- **`sound/soc/codecs/es8328.c`** — ES8388/ES8328.
- **`sound/soc/codecs/tlv320aic3x.c`** — TI codec.
- **`Documentation/sound/soc/dapm.rst`** — the DAPM model, in depth.
- **`Documentation/sound/soc/codec.rst`** — the codec-driver author's guide.
- **`include/sound/soc.h`** — the `SOC_*` control macros and DAPM widget macros.
- **WM8960 datasheet (Cirrus)** — register map; the DAPM graph mirrors its block diagram.

> Next chapter: **Chapter 90 — Digital class-D amplifiers.** When you don't need a full codec — just turn I²S into sound through a speaker. MAX98357A (no control at all), TAS5805M (DSP amp), PCM5102A (DAC).
