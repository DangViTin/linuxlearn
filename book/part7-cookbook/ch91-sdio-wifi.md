---
chapter: 91
title: SDIO WiFi (AP6212 / RTL8189FTV / SD8801)
part: VII — Device cookbook
estimated_pages: 22
status: draft
---

# Chapter 91 — SDIO WiFi
**IRQ** - interrupt request, the signal path that tells the CPU or interrupt controller that hardware needs service.
> **MCU bridge:** Think of an IRQ like an EXTI/NVIC interrupt path, except Linux splits the hard interrupt from deferred work and must share lines across drivers.

> **What:** WiFi modules attached over the **SDIO** bus (the same physical interface as an SD card, repurposed for I/O). Three modules compared: **AP6212** (Broadcom BCM43438, on many i.MX boards), **RTL8189FTV** (Realtek), **SD8801** (Marvell/NXP). Builds on Ch 55E (the WiFi stack). For each: the SDIO bring-up sequence, firmware + NVRAM loading, and — since full-MAC WiFi drivers are 30k+ lines you won't write from scratch — a *trace of how a packet flows through the stack* and how to bring up the SDIO transport (the part that actually trips up every new board).
> **MAC** - Media Access Control in networking and radio chapters. It is the layer that owns framing and medium access.
>
> **Why:** SDIO WiFi is the standard embedded WiFi: soldered-down, low-cost, no USB port consumed. It is also the hardest peripheral to bring up on a new board. Five things must be exactly right: the SDIO transport, the power sequence, the 32 kHz clock, the per-board NVRAM, and the firmware blob. When any one is wrong, the symptom is usually "nothing in dmesg." This chapter is mostly about the bring-up sequence and debugging.
>
> **Focus:** the WiFi chip is a full-MAC co-processor. The Linux driver does two things only: it loads firmware, and it shuttles SDIO packets. The chip runs the entire 802.11 stack in its own firmware. The Linux driver (brcmfmac, etc.) loads that firmware over SDIO at boot, then ferries data packets and control commands back and forth. Bring-up is two jobs: get the SDIO bus working, then supply the right firmware and NVRAM. After that, the chip handles the actual WiFi.
>
> **Tooling.** This chapter uses `wpa_supplicant`, `iw`, chip firmware blob (Cypress/Realtek/Marvell).
> - **Ubuntu-base (target):** `apt install wpasupplicant iw firmware-brcm80211 firmware-realtek`
> - **Buildroot:** `BR2_PACKAGE_WPA_SUPPLICANT=y BR2_PACKAGE_IW=y`
> **Buildroot** - a configuration-driven build system that produces a complete root filesystem and related images.
> - Full per-tool reference: [Userspace tooling appendix](../part5-rootfs/appendix-tooling.md).
> **MCU bridge:** Think of the rootfs as the firmware image's file-backed runtime environment. On an MCU you link everything into flash. On Linux, programs and config live in this mounted tree.
> **rootfs** - root filesystem, the directory tree mounted at / that contains /bin, /etc, /dev, and libraries.


## 91.1  Module comparison

> **Driver choice:** Use the in-tree, maintained driver first.
> Use out-of-tree, spidev, or custom-driver paths only after you accept the kernel-version maintenance cost and document who owns updates.


| | AP6212 (BCM43438) | RTL8189FTV | SD8801 (Marvell) |
|---|---|---|---|
| Vendor | Broadcom (AmPak module) | Realtek | Marvell/NXP |
| Standard | 802.11 b/g/n (2.4 GHz) | 802.11 b/g/n | 802.11 b/g/n |
| Combo | + Bluetooth 4.1 | WiFi only | + Bluetooth (8997 variant) |
| Bus | SDIO 2.0 | SDIO | SDIO |
| Driver | `brcmfmac` (in-tree) | `rtl8189es`/`rtl8189fs` (out-of-tree) or `rtw88` | `mwifiex` (in-tree) |
| Firmware | yes + per-board NVRAM | yes (in driver or blob) | yes |
| 32 kHz clock | required | required | required |
| Throughput (real) | ~30–50 Mbps | ~30–40 Mbps | ~40 Mbps |
| Volume price | $2–4 | $1.50–3 | $3–5 |

**Pick guide:**
- **AP6212**: well-supported mainline (`brcmfmac`), combo BT. Default for i.MX boards.
- **RTL8189**: cheapest. but the driver is usually out-of-tree (DKMS pain — see Ch 92's lesson, applies here too).
- **SD8801**: mainline `mwifiex`, decent. combo variants exist.

Strongly prefer modules with in-tree drivers — AP6212 with brcmfmac, SD8801 with mwifiex. Out-of-tree drivers (most RTL8189 variants) are a maintenance burden — see §91.8.

## 91.2  SDIO — SD card bus, repurposed

SDIO uses the same physical bus and protocol as an SD card (Ch 66). Instead of reading and writing storage blocks, the device exposes **I/O functions** — a set of registers and an interrupt line. The WiFi chip is "SDIO function 1 (and 2)". The host reads/writes its registers and data FIFOs over SDIO commands (CMD52 single-byte, CMD53 block).

```
   i.MX6ULL uSDHC2 ──[SDIO 4-bit]──► AP6212
       CLK, CMD, DAT0-3                WL_SDIO
       + WL_REG_ON (GPIO reset)        WL_REG_ON
       + WL_HOST_WAKE (IRQ)            out-of-band IRQ
       + 32.768 kHz LPO clock          32K_CLK
       + 3.3V + 1.8V rails
```

Key signals beyond the 6-wire SDIO:
- **WL_REG_ON**: a GPIO that powers/resets the WiFi block. Must be pulsed to wake the chip.
> **MCU bridge:** Think of Linux GPIO like the same pin set/reset block you used on STM32, but accessed through a kernel subsystem that owns numbering, direction, interrupts, and user-space exposure.
**GPIO** - General-Purpose Input/Output, a pin controlled as a digital input, output, or interrupt source.
- **32.768 kHz LPO clock**: the low-power oscillator the chip needs for its sleep timing. Without it, the chip is unreliable or won't init.
- **WL_HOST_WAKE**: an out-of-band interrupt (the chip can wake the host even when SDIO is idle).

## 91.3  The full WiFi stack (recap from Ch 55E)

```
   user-space: wpa_supplicant, NetworkManager
        │ nl80211
        ▼
   cfg80211 (config API)
        │
        ▼
   ┌──────────────────────────────────────────┐
   │ brcmfmac (the chip driver)                │
   │  - loads firmware + NVRAM over SDIO        │
   │  - implements cfg80211 ops (scan, connect) │
   │  - shuttles data frames chip ↔ network stack│
   └──────────────────────────────────────────┘
        │ SDIO (CMD52/CMD53)
        ▼
   AP6212 firmware (runs the actual 802.11 MAC)
```

For a **full-MAC** chip like the AP6212, mac80211 is *not* used — the chip's firmware is the MAC. brcmfmac talks cfg80211 directly. (Soft-MAC chips like some Atheros parts use mac80211. full-MAC chips like Broadcom/Marvell don't.)

## 91.4  Device-tree bring-up

This is where boards fail. The DT must describe: the SDIO bus, the power sequence, the chip node, and the 32 kHz clock.

```dts
/* The 32.768 kHz clock the WiFi needs */
wifi_lpo_clk: wifi-lpo-clk {
    compatible = "fixed-clock";
    #clock-cells = <0>;
    clock-frequency = <32768>;
};

/* Power sequence: pulse WL_REG_ON, provide the LPO clock */
wifi_pwrseq: wifi-pwrseq {
    compatible = "mmc-pwrseq-simple";
    reset-gpios = <&gpio5 9 GPIO_ACTIVE_LOW>;     /* WL_REG_ON */
    clocks = <&wifi_lpo_clk>;
    clock-names = "ext_clock";
    post-power-on-delay-ms = <100>;
};

&usdhc2 {
    pinctrl-names = "default";
    pinctrl-0 = <&pinctrl_usdhc2>;
    bus-width = <4>;
    non-removable;                /* soldered chip, not a removable card */
    keep-power-in-suspend;
    cap-power-off-card;
    mmc-pwrseq = <&wifi_pwrseq>;
    vmmc-supply = <&reg_wlan_3v3>;
    vqmmc-supply = <&reg_wlan_1v8>;
    no-1-8-v;                     /* or allow it, depending on module */
    status = "okay";

    #address-cells = <1>;
    #size-cells = <0>;

    wifi@1 {
        compatible = "brcm,bcm4329-fmac";    /* covers BCM43438/AP6212 */
        reg = <1>;                            /* SDIO function 1 */
        interrupt-parent = <&gpio5>;
        interrupts = <8 IRQ_TYPE_LEVEL_HIGH>; /* WL_HOST_WAKE */
        interrupt-names = "host-wake";
    };
};
```

The five things that must all be right:
1. **SDIO bus config** (`bus-width`, `non-removable`, no card-detect).
2. **Power sequence** (`mmc-pwrseq-simple` pulsing WL_REG_ON).
3. **The 32 kHz clock** supplied to the pwrseq.
4. **The chip node** with the right `compatible` and SDIO function `reg = <1>`.
5. **Voltage rails** (`vmmc`, `vqmmc`).

Miss any one of these and dmesg is silent.

## 91.5  Firmware + NVRAM

brcmfmac loads two files from `/lib/firmware/brcm/`:

```
brcmfmac43430-sdio.bin      ← the firmware blob (the 802.11 MAC code)
brcmfmac43430-sdio.txt      ← the per-board NVRAM (calibration + config)
```

The exact filename depends on the chip ID (read over SDIO at probe). For BCM43438: `brcmfmac43430-sdio.*`.

**The firmware blob** is the chip's program — get it from `linux-firmware.git`. It's chip-specific but board-independent.

**The NVRAM** (`.txt`) is **per-board**: antenna configuration, regulatory domain, board-specific RF calibration, crystal frequency trim. It comes from the *module vendor* (AmPak for AP6212) or the board vendor. Using the wrong NVRAM gives: terrible range, wrong country code, or a chip that enumerates but won't connect.

```
[root@pa-mini:~]# ls /lib/firmware/brcm/
brcmfmac43430-sdio.bin
brcmfmac43430-sdio.txt        ← you must supply this for your board
brcmfmac43430-sdio.clm_blob   ← optional regulatory blob
```

The `.clm_blob` (Country Locale Matrix) holds regulatory limits. newer firmware needs it.

## 91.6  Bring-up trace

A successful bring-up in dmesg:

```
[root@pa-mini:~]# dmesg | grep -iE 'mmc|brcm|wifi'
mmc1: SDHCI controller on 2194000.usdhc [2194000.usdhc] using ADMA
mmc1: queuing unknown CIS tuple 0x80 (2 bytes)        ← SDIO enumeration
mmc1: new high speed SDIO card at address 0001        ← chip responded!
brcmfmac: brcmf_fw_alloc_request: using brcm/brcmfmac43430-sdio for chip BCM43430/1
brcmfmac: brcmf_fw_complete_request: firmware brcm/brcmfmac43430-sdio.bin found
brcmfmac: brcmf_fw_complete_request: nvram brcm/brcmfmac43430-sdio.txt found
brcmfmac: brcmf_c_preinit_dcmds: Firmware: BCM43430/1 wl0: ...
brcmfmac_sdio mmc1:0001:1 wlan0: renamed from wlan0
```

The progression:
1. `mmc1: new high speed SDIO card` — **the SDIO transport works**, the chip responded to enumeration. If this line is missing, the problem is the SDIO bus / power sequence / 32 kHz clock — *not* WiFi.
2. `brcmfmac: ... firmware ... found` — the firmware blob loaded.
3. `nvram ... found` — the NVRAM loaded.
4. `Firmware: BCM43430/1` — the chip booted its firmware and reported its version.
5. `wlan0` — the network interface appeared.

**Debugging by stage**: if you don't see line 1, it's a transport problem (most common). If line 1 appears but not line 2, the firmware file is missing/misnamed. If lines 1–4 appear but WiFi behaves badly, it's the NVRAM.

Then scan + connect (Ch 55E):

```
[root@pa-mini:~]# ip link set wlan0 up
[root@pa-mini:~]# iw wlan0 scan | grep SSID
[root@pa-mini:~]# wpa_supplicant -B -i wlan0 -c /etc/wpa_supplicant.conf -D nl80211
[root@pa-mini:~]# udhcpc -i wlan0
[root@pa-mini:~]# ping 8.8.8.8
```

## 91.7  How a packet flows (since you won't write this driver)

Full-MAC WiFi drivers are tens of thousands of lines — you won't reimplement brcmfmac. But understanding the data path demystifies it:

### Transmit (your app sends a packet)

```
1. App: send(socket, data)
2. Kernel network stack builds an skb (socket buffer), routes it to wlan0.
3. brcmfmac's ndo_start_xmit(skb, wlan0) is called.
4. brcmfmac wraps the skb with a BDC/BCMC header (Broadcom's framing).
5. It writes the framed packet to the chip's SDIO data FIFO via CMD53 block write.
6. The AP6212 firmware takes over: 802.11 framing, encryption (CCMP), 
   rate selection, retransmission, the actual radio transmission.
```

The Linux side stops at "write bytes to SDIO FIFO." Everything 802.11 happens in the chip's firmware.

### Receive

```
1. AP6212 firmware receives an 802.11 frame, decrypts it, de-frames to Ethernet.
2. It asserts the SDIO interrupt (or WL_HOST_WAKE).
3. brcmfmac's SDIO IRQ handler reads the chip's status, then reads the 
   pending data from the SDIO FIFO via CMD53 block read.
4. It strips the BDC header, builds an skb.
5. netif_rx(skb) hands it to the network stack → up to the app.
```

### Control (scan, connect)

```
1. wpa_supplicant: nl80211 "scan request" → cfg80211 → brcmfmac's .scan op.
2. brcmfmac sends a "WLC_SCAN" command (Broadcom's ioctl-over-SDIO protocol)
   to the chip's control FIFO.
3. The chip's firmware does the scan (off-channel sweeps), reports results back.
4. brcmfmac reads the results, converts to cfg80211 BSS entries, reports up.
```

So brcmfmac is three things: a firmware loader, an SDIO packet shuttle, and a cfg80211-to-Broadcom command translator. The source is ~15000 lines, but conceptually it is those three jobs.

## 91.8  In-tree vs out-of-tree — a strong recommendation

The AP6212 (brcmfmac) and SD8801 (mwifiex) have **in-tree** drivers — they ship with the kernel, build automatically, and track kernel API changes. The RTL8189FTV usually needs an **out-of-tree** driver (`rtl8189es` from a GitHub repo).

Out-of-tree WiFi drivers are a recurring maintenance nightmare:
- They break on every kernel upgrade (the kernel's internal APIs change. out-of-tree drivers must be patched to match).
- DKMS rebuilds them on kernel upgrade, but only if a matching version exists.
- Quality varies wildly. many are vendor dumps with poor power management.

**For a product, choose a module with an in-tree driver.** Saving $0.50 on an RTL8189 versus an AP6212 is nothing compared to the engineering cost of maintaining an out-of-tree driver for an 8-year product life. (Note: `rtw88` is bringing more Realtek parts in-tree — check current status.)

## 91.9  Lab

> **Privilege boundary:** $ means normal user. # or sudo means root and can change host or target state.
> After a privileged command, verify the expected device, service, or file appears before continuing. Roll back by undoing the config change or stopping the service you just enabled.


1. **DT bring-up.** Configure uSDHC2 + pwrseq + 32 kHz clock + the wifi node. Boot.
2. **Stage-1 check.** `dmesg | grep mmc` — look for "new high speed SDIO card." If absent, debug the transport: scope WL_REG_ON (should pulse), scope the 32 kHz clock, verify rails.
3. **Firmware.** Copy `brcmfmac43430-sdio.bin` + your board's `.txt` to `/lib/firmware/brcm/`. Reboot. verify "firmware found" + "nvram found."
4. **wlan0.** `ip link` shows wlan0. Scan, connect (WPA2), DHCP, ping.
5. **Throughput.** `iperf3` to a wired host. expect 30–50 Mbps on 2.4 GHz.
6. **NVRAM experiment.** Swap in a *different* board's NVRAM. Observe degraded range / wrong country code. Restore.
7. **Power management.** Suspend the system (`echo mem`). verify WiFi reconnects on resume (with `keep-power-in-suspend`).
8. **SDIO debugging.** `cat /sys/kernel/debug/mmc1/...` for SDIO bus state. Enable `brcmfmac` debug: `modprobe brcmfmac debug=0x1404`.

## 91.10  Pitfalls

- **No "new SDIO card" in dmesg.** The transport failed. 90% of bring-up problems are here, not in WiFi. Check: WL_REG_ON pulsing (mmc-pwrseq), 32 kHz clock present, rails up, SDIO pinmux correct.
- **Missing 32 kHz clock.** The chip needs the LPO for sleep timing. Without it, it may enumerate but be flaky, or not enumerate. Provide it (a `fixed-clock` in DT + a physical 32 kHz source, often from the PMIC).
> **MCU bridge:** Think of a PMIC like a programmable power-tree supervisor: it replaces discrete enables and LDO assumptions with sequenced rails the kernel can model.
**PMIC** - Power Management IC, a chip that sequences and regulates the board's voltage rails.
- **Wrong/missing NVRAM.** Chip enumerates, firmware loads, but range is awful or it won't associate. The NVRAM is per-board. get the right one from the module vendor.
- **Wrong firmware filename.** brcmfmac derives the name from the chip ID. If your chip variant maps to a different filename, "firmware not found." Check the exact name in the dmesg "using brcm/..." line.
- **`no-1-8-v` mismatch.** Some modules require 1.8 V SDIO signaling, others 3.3 V only. Mismatch = enumeration failure or corruption. Match `vqmmc` + the `no-1-8-v` flag to the module.
- **Card-detect on a soldered chip.** Forgetting `non-removable` makes the kernel poll for card removal. The chip may get powered off. Always `non-removable` for soldered WiFi.
- **regdb missing.** Without `wireless-regdb` + CRDA (or the in-kernel regdb), the chip is limited to the most restrictive channels. Install it.
- **Out-of-tree driver + kernel upgrade.** The RTL8189 out-of-tree driver breaks. Pin the kernel or use DKMS — or pick an in-tree module.
- **BT half of a combo not coming up.** The AP6212 is WiFi+BT. The BT half (Ch 94) needs separate UART bring-up. WiFi working doesn't mean BT works.

## 91.11  Going deeper

- **`drivers/net/wireless/broadcom/brcm80211/brcmfmac/`** — the brcmfmac driver. `sdio.c` is the SDIO transport. `core.c` the cfg80211 glue.
- **`drivers/net/wireless/marvell/mwifiex/`** — Marvell SD8801.
- **`drivers/mmc/core/sdio.c`** — the SDIO bus enumeration.
- **`Documentation/devicetree/bindings/net/wireless/brcm,bcm4329-fmac.yaml`** — the DT binding.
- **`Documentation/devicetree/bindings/mmc/mmc-pwrseq-simple.yaml`** — power sequencer.
- **`linux-firmware.git/brcm/`** — the firmware blobs.
- **AmPak AP6212 datasheet + reference schematic** — the canonical wiring + NVRAM.
- **`Documentation/networking/regulatory.rst`** — the WiFi regulatory framework.

> Next chapter: **Chapter 92 — USB WiFi.** The dongle approach — RTL8188EUS, MT7601 — and the in-tree-vs-out-of-tree driver saga that defines the USB-WiFi experience.
