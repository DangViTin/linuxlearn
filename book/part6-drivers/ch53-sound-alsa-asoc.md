---
chapter: 53
title: Sound: ALSA and ASoC
part: VI - Driver development
estimated_pages: 18
status: draft
---

# Chapter 53: Sound: ALSA and ASoC

> **What:** the kernel's audio framework, **ALSA** (Advanced Linux Sound Architecture) and **ASoC** (ALSA System on Chip, the embedded refinement). ASoC splits an audio chain into three drivers. The **CPU-DAI** is the SoC's I²S/SAI controller. The **codec** is the analog chip (WM8960, SGTL5000). The **machine driver** wires them together for one specific board. By the end you can `aplay test.wav` over a WM8960 on the Point Atom ALPHA.
> **ASoC:** ALSA System-on-Chip, the embedded audio layer that connects CPU audio ports, codecs, and board wiring.
> **ALSA:** Linux's kernel and user-space audio stack.
>
> **Why:** audio is one of the tightest real-time loops in any embedded system. 48000 samples/second × 2 channels × 16 bits = a 96 KB/s data stream that must never glitch. ASoC's three-way split is the kernel's solution to *not* re-writing a complete audio driver for every new SoC + codec combination, you reuse the CPU-DAI and codec drivers, only writing a small machine driver per board.
>
> **Focus:** **the three drivers cooperate via `snd_soc_dai_link`**. The machine driver declares "CPU-DAI X drives codec Y over format Z at clock W." Once you understand this binding, ASoC drivers become readable.
>
> **Tooling.** This chapter uses `alsa-utils` (`alsamixer`, `aplay`, `arecord`, `amixer`).
> - **Ubuntu-base (target):** `apt install alsa-utils libasound2-dev`
> - **Buildroot:** `BR2_PACKAGE_ALSA_UTILS=y BR2_PACKAGE_ALSA_LIB=y`
> **Buildroot:** a configuration-driven build system that produces a complete root filesystem and related images.
> - Full per-tool reference: [Userspace tooling appendix](../part5-rootfs/appendix-tooling.md).
> **MCU bridge:** Think of the rootfs as the firmware image's file-backed runtime environment. On an MCU you link everything into flash. On Linux, programs and config live in this mounted tree.
> **rootfs:** root filesystem, the directory tree mounted at / that contains /bin, /etc, /dev, and libraries.


## 53.1  Three drivers cooperating

```
   ┌───────────────────────────────────────────────────┐
   │           ALSA user-space (aplay, PulseAudio)      │
   └───────────────────────────────────────────────────┘
                              │ /dev/snd/pcmC0D0p
                              ▼
   ┌───────────────────────────────────────────────────┐
   │              ALSA core (snd_pcm)                   │
   └───────────────────────────────────────────────────┘
                              │
                              ▼
   ┌───────────────────────────────────────────────────┐
   │   ASoC core (snd_soc_*)                             │
   └───────────────────────────────────────────────────┘
        │                    │                    │
        ▼                    ▼                    ▼
   ┌─────────┐         ┌─────────┐          ┌─────────┐
   │ Machine │   ←→    │   CPU   │   ←I²S→  │  Codec  │
   │ driver  │         │   DAI   │          │ (WM8960)│
   │ (board) │         │ (SAI3)  │          │         │
   └─────────┘         └─────────┘          └─────────┘
                          │                     │
                          │ MMIO + DMA          │ I²C control + I²S audio
                          ▼                     ▼
                      i.MX SoC               codec chip
```

- **CPU-DAI**: the SoC's audio peripheral driver. For i.MX6ULL: SAI (Synchronous Audio Interface). The driver is `drivers/sound/soc/fsl/fsl_sai.c`. Speaks I²S to the codec.
- **Codec**: the codec chip's driver, e.g., `sound/soc/codecs/wm8960.c`. Talks I²C for control (volume, mute, sample rate). Receives/sends I²S audio data.
- **Machine**: the board-specific glue. E.g., `sound/soc/fsl/imx-wm8960.c`. Declares the DAI link and any board-specific routing (which speaker/headphone outputs are wired, which mics are connected).

## 53.2  Device tree for WM8960 audio

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

&i2c2 {
    wm8960: codec@1a {
        compatible = "wlf,wm8960";
        reg = <0x1a>;
        wlf,shared-lrclk;
        clocks = <&clks IMX6UL_CLK_SAI2>;
        clock-names = "mclk";
    };
};

sound {
    compatible = "fsl,imx-audio-wm8960";
    model = "wm8960-audio";
    audio-cpu = <&sai2>;
    audio-codec = <&wm8960>;
    audio-routing =
        "Headphone Jack", "HP_L",
        "Headphone Jack", "HP_R",
        "Ext Spk", "SPK_LP",
        "Ext Spk", "SPK_LN",
        "Ext Spk", "SPK_RP",
        "Ext Spk", "SPK_RN",
        "LINPUT1", "Mic Jack",
        "LINPUT3", "Mic Jack",
        "Mic Jack", "MICB";
    mux-int-port = <2>;
    mux-ext-port = <6>;
    hp-det-gpio = <&gpio5 4 GPIO_ACTIVE_HIGH>;
};
```

Three nodes:
- **`&sai2`**: the SoC's SAI2 audio peripheral. Provides the I²S link.
- **`&i2c2` / `wm8960`**: the codec on I²C2. The `clocks = <&clks IMX6UL_CLK_SAI2>` is the master clock supplying the codec.
- **`sound`**: the machine driver binding. `compatible = "fsl,imx-audio-wm8960"` picks the i.MX-WM8960 machine driver. `audio-routing` declares which codec outputs are connected to which physical jacks.

## 53.3  How a sample plays

```
   aplay test.wav
       │
       │ open(/dev/snd/pcmC0D0p)
       │ ioctl(SNDRV_PCM_IOCTL_HW_PARAMS, format=S16_LE, rate=48000, channels=2)
       │ write() loop ── packed into period-sized chunks ──
       │
       ▼
   ALSA core fills a periodic DMA ring buffer
       │
       │ via dmaengine — cyclic transfer (Ch 51.5)
       ▼
   SDMA continuously transfers from ring buffer → SAI2 TX FIFO
       │
       │ I²S serial clock + frame sync + data
       ▼
   WM8960 sigma-delta DAC ──→ analog audio ──→ amp ──→ speaker
```

DMA fires an IRQ every period (typically 1024 samples, about 21 ms at 48 kHz). ALSA refills that period from the user-space buffer. The cycle continues. If user-space writes fast enough to avoid an underrun, playback continues without glitches.
> **MCU bridge:** Think of an IRQ like an EXTI/NVIC interrupt path, except Linux splits the hard interrupt from deferred work and must share lines across drivers.
> **MCU bridge:** Think of DMA like the MCU DMA controller you used for UART or SPI, but with cache coherency, scatter-gather descriptors, and kernel ownership rules added.
> **IRQ:** interrupt request, the signal path that tells the CPU or interrupt controller that hardware needs service.
> **DMA:** Direct Memory Access. Hardware moves data to or from memory without the CPU copying each byte.

If userspace can't keep up: **xrun** (underrun). ALSA logs it. Sound clicks or pauses. Reasons: CPU too loaded, period too short, user-space process scheduling jitter (Ch 52A's PREEMPT_RT helps).
> **PREEMPT_RT:** the Linux real-time patch set that makes more kernel paths preemptible and reduces latency.

## 53.4  Writing a machine driver

The machine driver is the thing you'd write for a new board. The CPU-DAI and codec drivers come from mainline. Sketch:

```c
#include <sound/soc.h>

static const struct snd_soc_dapm_widget my_dapm_widgets[] = {
    SND_SOC_DAPM_HP("Headphone Jack", NULL),
    SND_SOC_DAPM_SPK("Ext Spk", NULL),
    SND_SOC_DAPM_MIC("Mic Jack", NULL),
};

static int my_init(struct snd_soc_pcm_runtime *rtd)
{
    struct snd_soc_card *card = rtd->card;
    /* Optional: clk routing, ALC settings, etc. */
    return 0;
}

SND_SOC_DAILINK_DEFS(hifi,
    DAILINK_COMP_ARRAY(COMP_CPU("imx-sai2")),
    DAILINK_COMP_ARRAY(COMP_CODEC("wm8960.1-001a", "wm8960-hifi")),
    DAILINK_COMP_ARRAY(COMP_PLATFORM("imx-sai2")));

static struct snd_soc_dai_link my_dai_link = {
    .name = "HiFi",
    .stream_name = "HiFi",
    .init = my_init,
    SND_SOC_DAILINK_REG(hifi),
    .dai_fmt = SND_SOC_DAIFMT_I2S
             | SND_SOC_DAIFMT_NB_NF
             | SND_SOC_DAIFMT_CBS_CFS,
};

static struct snd_soc_card my_card = {
    .name = "my-board-audio",
    .owner = THIS_MODULE,
    .dai_link = &my_dai_link,
    .num_links = 1,
    .dapm_widgets = my_dapm_widgets,
    .num_dapm_widgets = ARRAY_SIZE(my_dapm_widgets),
};

static int my_probe(struct platform_device *pdev)
{
    my_card.dev = &pdev->dev;
    return devm_snd_soc_register_card(&pdev->dev, &my_card);
}
```

The DAI link declares:
- **CPU side**: which SAI peripheral.
- **Codec side**: which I²C-bound chip + which DAI on that chip (codecs may have multiple DAIs).
- **DAI format**: I²S protocol, normal bit clock + frame clock polarity (`NB_NF`), codec is bit-clock-slave + frame-clock-slave (`CBS_CFS`, meaning the SoC is the master).

That's 99% of what a machine driver does. The hard work is in the codec driver and CPU-DAI driver, which are upstream.

## 53.5  User-space, ALSA tools

```
[root@pa-mini:~]# aplay -l                          # list playback devices
**** List of PLAYBACK Hardware Devices ****
card 0: wm8960audio [wm8960-audio], device 0: HiFi wm8960-hifi-0 []

[root@pa-mini:~]# arecord -l                        # list capture devices
**** List of CAPTURE Hardware Devices ****
card 0: wm8960audio [wm8960-audio], device 0: HiFi wm8960-hifi-0 []

[root@pa-mini:~]# alsamixer                         # interactive mixer
[root@pa-mini:~]# aplay -D plughw:0,0 -f S16_LE -r 48000 -c 2 test.wav
[root@pa-mini:~]# arecord -D plughw:0,0 -f S16_LE -r 48000 -c 2 -d 5 rec.wav
[root@pa-mini:~]# amixer set 'Headphone' 80%
```

For higher-level audio (Bluetooth, network), you'd stack PulseAudio or PipeWire on top. For embedded one-app systems, raw ALSA is fine.

## 53.6  Lab

1. **Get audio working on a board with WM8960.** Enable in DT, boot, `aplay test.wav`, hear sound.
2. **Capture.** `arecord -d 5 rec.wav`. Play back. Confirm round-trip works.
3. **Adjust mixer settings.** `alsamixer`, try Headphone volume, capture-channel selection.
4. **Diagnose an xrun.** Use `aplay -v test.wav`. Reduce period size with `--period-size=128`. Observe xruns appearing as load increases.
5. **Listen at different rates.** `aplay -f S24_LE -r 44100 ...`, verify codec accepts non-48k rates.
6. **Read the WM8960 driver.** `sound/soc/codecs/wm8960.c`, find the regmap config, the DAPM (Dynamic Audio Power Management) routing, the bias-level callbacks.
> **MCU bridge:** Think of regmap like a typed wrapper around your read_reg() and write_reg() helpers, with caching, locking, and bus differences handled centrally.
> **regmap:** a kernel helper that wraps register reads and writes over I2C, SPI, or MMIO.
> **MMIO:** memory-mapped I/O, where software accesses peripheral registers through normal load and store instructions.

## 53.7  Pitfalls

- **Wrong I²S format.** Codec expects "left-justified," driver sends "I²S": you hear silence or noise. Fix `.dai_fmt = SND_SOC_DAIFMT_LEFT_J` etc.
- **Master/slave clock mismatch.** Both SoC and codec think they're masters → no clock at all. One must be slave (`CBS_CFS` or `CBM_CFM`).
- **MCLK rate wrong.** Codec needs e.g., 256× sample rate as master clock. Set `assigned-clock-rates` in DT for the codec's MCLK input.
- **DAPM routes incomplete.** Headphone outputs muted because DAPM thinks they're not connected. Trace `cat /sys/kernel/debug/asoc/.../dapm/*`.
- **Wrong codec address.** `&i2c2 { wm8960: codec@1a { reg = <0x1a> ... } }`, verify with `i2cdetect`.
- **MASTER clock not enabled.** Codec needs MCLK to be running before any I²C command. Tie the codec's clock to the SAI's clock-gate so they enable together.
- **No DAPM widgets for jacks.** Audio "plays" (DMA happily transfers) but mute amps because DAPM doesn't know to route. Always declare physical jacks as widgets.

## 53.8  Going deeper

- **`Documentation/sound/`**: ALSA documentation.
- **`Documentation/sound/soc/`**: ASoC documentation. Start with `overview.rst`.
- **`sound/soc/fsl/imx-wm8960.c`**: i.MX-WM8960 machine driver (~600 lines). Read this to understand a complete machine driver.
- **`sound/soc/codecs/wm8960.c`**: production codec driver (~1500 lines). Excellent example of regmap + ASoC + DAPM.
- **`sound/soc/fsl/fsl_sai.c`**: i.MX SAI CPU-DAI driver.
- **`Documentation/devicetree/bindings/sound/`**: DT bindings.

> Next chapter: **Chapter 54: LCD framebuffer and DRM/KMS.** Audio done, video next. From "Linux has /dev/fb0" to "Linux has DRM/KMS with mode-setting and Wayland-compatible output."
