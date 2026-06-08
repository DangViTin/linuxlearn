---
chapter: 55E
title: WiFi + wpa_supplicant
part: VI — Driver development (supplementary v1.1)
estimated_pages: 14
status: draft
---

# Chapter 55E — WiFi + wpa_supplicant
**DMA** - Direct Memory Access. hardware moves data to or from memory without the CPU copying each byte.
MCU bridge: Think of DMA like the MCU DMA controller you used for UART or SPI, but with cache coherency, scatter-gather descriptors, and kernel ownership rules added.

> **What:** Linux's **WiFi stack** — `mac80211` (the kernel's 802.11 implementation), `cfg80211` (the configuration API), per-chip drivers (`brcmfmac`, `rtl8xxxu`, etc.), and the user-space **wpa_supplicant** that handles WPA2/WPA3 authentication. We focus on SDIO WiFi (AP6212 / RTL8189 on Point Atom-class boards) as the most common embedded case.
>
> **Why:** WiFi is a vertical stack — driver, kernel WiFi core, supplicant, network manager. If any layer is wrong, nothing works. Knowing the layers and how to debug each one turns "WiFi doesn't work" from a multi-day debug into a methodical bring-up.
>
> **Focus:** **firmware + nvram + supplicant**. The driver loads vendor firmware from `/lib/firmware/`, plus a per-board nvram (channel list, antennas, regulatory). wpa_supplicant handles the 4-way handshake. All three must be right.
>
> **Tooling.** This chapter uses `wpa_supplicant`, `iw`, optional `hostapd`. chip firmware blob.
> - **Ubuntu-base (target):** `apt install wpasupplicant iw hostapd firmware-realtek firmware-brcm80211`
> - **Buildroot:** `BR2_PACKAGE_WPA_SUPPLICANT=y BR2_PACKAGE_IW=y BR2_PACKAGE_HOSTAPD=y`
> **Buildroot** - a configuration-driven build system that produces a complete root filesystem and related images.
> - Full per-tool reference: [Userspace tooling appendix](../part5-rootfs/appendix-tooling.md).
> MCU bridge: Think of the rootfs as the firmware image's file-backed runtime environment. On an MCU you link everything into flash. On Linux, programs and config live in this mounted tree.
> **rootfs** - root filesystem, the directory tree mounted at / that contains /bin, /etc, /dev, and libraries.


## 55E.1  The stack

```
    user-space:  wpa_supplicant, NetworkManager, ifupdown
        │ nl80211 + DBus
        ▼
   ┌──────────────────────────────────────────┐
   │ cfg80211 (configuration / management API) │
   └──────────────────────────────────────────┘
        │
        ▼
   ┌──────────────────────────────────────────┐
   │ mac80211 (kernel 802.11 implementation)   │
   │   - filters, queues, rate control         │
   │   - regulatory domain enforcement         │
   └──────────────────────────────────────────┘
        │
        ▼
   ┌──────────────────────────────────────────┐
   │ chip driver: brcmfmac, rtl8xxxu, ...       │
   │   - SDIO / USB / SPI transport             │
   │   - firmware loading                        │
   └──────────────────────────────────────────┘
        │
        ▼
   wifi hardware (AP6212 / RTL8189 / etc.)
```

For "full-MAC" chips (most embedded modules), much of the 802.11 logic is in chip firmware. The driver is thin. For "soft-MAC" chips, mac80211 does more.
**MAC** - Media Access Control in networking and radio chapters. It is the layer that owns framing and medium access.

## 55E.2  AP6212 on SDIO (representative case)

DT:

```dts
&usdhc2 {
    pinctrl-names = "default";
    pinctrl-0 = <&pinctrl_usdhc2>;
    bus-width = <4>;
    non-removable;
    keep-power-in-suspend;
    wakeup-source;
    vmmc-supply = <&reg_wlan>;
    mmc-pwrseq = <&wifi_pwrseq>;
    status = "okay";

    wifi@1 {
        compatible = "brcm,bcm4329-fmac";
        reg = <1>;
        interrupt-parent = <&gpio5>;
        interrupts = <8 IRQ_TYPE_LEVEL_HIGH>;
    };
};

wifi_pwrseq: wifi_pwrseq {
    compatible = "mmc-pwrseq-simple";
    reset-gpios = <&gpio5 9 GPIO_ACTIVE_LOW>;
    clocks = <&clks IMX6UL_CLK_OSC>;
    clock-names = "ext_clock";
};
```

Three things to notice:
- **SDIO bus configured** with `bus-width = 4`, no card-detect, `non-removable`.
- **Power sequence** drives the WL_REG_ON reset GPIO high to enable the chip.
MCU bridge: Think of Linux GPIO like the same pin set/reset block you used on STM32, but accessed through a kernel subsystem that owns numbering, direction, interrupts, and user-space exposure.
**GPIO** - General-Purpose Input/Output, a pin controlled as a digital input, output, or interrupt source.
- **`brcm,bcm4329-fmac`** matches the brcmfmac driver.

## 55E.3  Firmware and nvram

brcmfmac loads two files from `/lib/firmware/brcm/`:

```
brcmfmac43430-sdio.bin           ← firmware blob
brcmfmac43430-sdio.txt           ← nvram (per-board calibration & config)
```

The exact filename depends on chip ID. Find current names at <https://git.kernel.org/pub/scm/linux/kernel/git/firmware/linux-firmware.git/tree/brcm>.

Without the nvram, the driver probes but channels do not enumerate correctly (or at all). The nvram is per-board. Copying from another board gives the wrong antenna config, the wrong regulatory domain, and broken behavior. Always get the matching nvram from your board vendor.

## 55E.4  Bring-up trace

```
[root@pa-mini:~]# dmesg | grep -iE 'brcm|wifi|mmc'
mmc1: SDHCI controller on 2194000.usdhc [2194000.usdhc] using DMA
mmc1: new high speed SDIO card at address 0001
brcmfmac: brcmf_fw_alloc_request: using brcm/brcmfmac43430-sdio
brcmfmac: F1 signature read @0x18000000=0x4040a9a6
brcmfmac: brcmf_fw_complete_request: Found firmware (...)
brcmfmac: bcm4330-fmac initialized
[root@pa-mini:~]# ip link
3: wlan0: <BROADCAST,MULTICAST> mtu 1500 ...
```

`wlan0` appears. Now scan and connect:

```
[root@pa-mini:~]# ip link set wlan0 up
[root@pa-mini:~]# iw wlan0 scan | grep -E 'SSID|signal'
        SSID: MyHomeWiFi
        signal: -45.00 dBm
        SSID: GuestNet
        signal: -67.00 dBm
```

## 55E.5  wpa_supplicant

`/etc/wpa_supplicant.conf`:

```
ctrl_interface=/var/run/wpa_supplicant
update_config=1

network={
    ssid="MyHomeWiFi"
    psk="my-password"
    key_mgmt=WPA-PSK
}
```

Start:

```sh
# Manual:
wpa_supplicant -B -i wlan0 -c /etc/wpa_supplicant.conf -D nl80211

# Then get an IP:
udhcpc -i wlan0
# or:
dhclient wlan0
```

WPA3 (SAE — Simultaneous Authentication of Equals):

```
network={
    ssid="MyWPA3Net"
    sae_password="my-password"
    key_mgmt=SAE
    ieee80211w=2
}
```

## 55E.6  Useful tools

```
[root@pa-mini:~]# iw dev                  # show interfaces and modes
[root@pa-mini:~]# iw wlan0 link            # current connection
[root@pa-mini:~]# iw wlan0 station dump    # signal, throughput, retries
[root@pa-mini:~]# wpa_cli                  # interactive supplicant control
[root@pa-mini:~]# iwconfig wlan0           # legacy tool; still useful
```

## 55E.7  Lab

1. **Add the AP6212 to your DT.** Verify SDIO enumerates, firmware loads, `wlan0` appears.
2. **Scan.** `iw wlan0 scan` should return SSIDs.
3. **Connect WPA2.** Configure wpa_supplicant, start it, get an IP, ping the gateway.
4. **Throughput.** iperf3 to a wired host. expect 30–80 Mbps on a 2.4 GHz network (i.MX6ULL with SDIO has limited bandwidth).
5. **Roam test.** Move between APs of the same SSID. observe BSSID change.
6. **Switch to softAP.** Run hostapd to make `wlan0` an access point.

## 55E.8  Pitfalls

- **Missing firmware.** Symptom: "Direct firmware load failed -2." Copy the right blob to `/lib/firmware/brcm/`.
- **Wrong nvram.** WiFi enumerates but signal is terrible or country code wrong. Get vendor's nvram.
- **MMC pwrseq not triggering.** Reset GPIO not toggled before SDIO init. Symptom: chip doesn't respond at all. Check the `mmc-pwrseq-simple` node.
- **32 KHz clock missing.** Most BCM and Realtek modules need a 32 kHz LPO clock. Without it, sleep modes fail and the chip becomes unreliable.
- **regdb missing.** Kernel won't tune above channel 11 without a regulatory database loaded. Install `wireless-regdb`.
- **WPA3 / SAE not supported by chip firmware.** Older AP6212 firmware lacks SAE. Upgrade firmware or fall back to WPA2.

## 55E.9  Going deeper

- **`Documentation/networking/cfg80211.rst`** — cfg80211 API.
- **`Documentation/networking/mac80211_hwsim.rst`** — for testing without hardware.
- **`drivers/net/wireless/broadcom/brcm80211/brcmfmac/`** — brcmfmac driver source.
- **`hostap.git/wpa_supplicant/`** — wpa_supplicant source and configuration examples.
- **<https://wireless.wiki.kernel.org/>** — the canonical kernel wireless wiki.

> Next chapter: **Chapter 55F — Cellular modems.** USB 4G modems (EC25) and the QMI/MBIM modes. UART AT-command modems.
