---
chapter: 92
title: USB WiFi (RTL8188EUS / MT7601 / RT5370)
part: VII — Device cookbook
estimated_pages: 16
status: draft
---

# Chapter 92 — USB WiFi

> **Driver choice:** Use the in-tree, maintained driver first.
> Use out-of-tree, spidev, or custom-driver paths only after you accept the kernel-version maintenance cost and document who owns updates.


> **What:** USB WiFi dongles — the plug-in alternative to soldered SDIO WiFi (Ch 91). Three chips compared: **Realtek RTL8188EUS** (the ubiquitous cheap dongle), **MediaTek MT7601** (common in $3 dongles), **Ralink RT5370** (older, very mainline-friendly). The big theme here is in-tree versus out-of-tree drivers. Some dongles just work. Others need a constantly-rebuilt DKMS module. Plus bandwidth contention with other USB devices on the i.MX6ULL's USB-2.0 bus.
>
> **Why:** USB WiFi is the *fastest* way to add WiFi to a board that has a spare USB port — no SDIO bring-up, no NVRAM, no 32 kHz clock. The catch is driver support: some chips have excellent in-tree drivers, others need out-of-tree modules that break on every kernel upgrade. Chip choice is most of the work.
>
> **Focus:** the chip you buy determines whether bringing up WiFi takes five minutes or five days. A `rtw88`- or `rt2800usb`-supported chip is plug-and-play. An RTL8188EUS needs the out-of-tree `rtl8188eus` driver, which you must rebuild for every kernel. This chapter is a buyer's guide as much as a driver guide.
>
> **Tooling.** This chapter uses `wpa_supplicant`, `iw`, chip firmware blob (Realtek/MediaTek/Ralink).
> - **Ubuntu-base (target):** `apt install wpasupplicant iw firmware-realtek firmware-misc-nonfree`
> - **Buildroot:** `BR2_PACKAGE_WPA_SUPPLICANT=y BR2_PACKAGE_IW=y`
> **Buildroot** - a configuration-driven build system that produces a complete root filesystem and related images.
> - Full per-tool reference: [Userspace tooling appendix](../part5-rootfs/appendix-tooling.md).
> MCU bridge: Think of the rootfs as the firmware image's file-backed runtime environment. On an MCU you link everything into flash. On Linux, programs and config live in this mounted tree.
> **rootfs** - root filesystem, the directory tree mounted at / that contains /bin, /etc, /dev, and libraries.


## 92.1  Chip comparison & driver status

| | RTL8188EUS | MT7601 | RT5370 |
|---|---|---|---|
| Vendor | Realtek | MediaTek | Ralink (now MediaTek) |
| Standard | 802.11n (2.4 GHz, 1×1) | 802.11n (2.4 GHz) | 802.11n (2.4 GHz) |
| Throughput | ~50 Mbps | ~50 Mbps | ~40 Mbps |
| **In-tree driver?** | partial (`r8188eu` since 5.18, in staging) | yes (`mt7601u`) | **yes (`rt2800usb`)** ✓ |
| Out-of-tree | `rtl8188eus` (aircrack-ng repo) | usually not needed | not needed |
| AP mode / monitor | yes (out-of-tree) | limited | yes |
| Volume price | $2–4 | $3–5 | $3–5 |

**The crucial column is "in-tree driver?":**
- **RT5370** (`rt2800usb`): the gold standard. Mainline since forever, rock-solid, supports AP + monitor mode. For the lowest-hassle path, buy an RT5370 dongle.
- **MT7601** (`mt7601u`): in-tree, works well. Good second choice.
- **RTL8188EUS**: the `r8188eu` staging driver works for basic STA mode (recent kernels), but AP/monitor mode + best performance needs the out-of-tree `rtl8188eus`. The most common dongle, but the most painful driver.

## 92.2  The plug-and-play case (RT5370)

```
[root@pa-mini:~]# lsusb
Bus 001 Device 004: ID 148f:5370 Ralink Technology RT5370 Wireless Adapter

[root@pa-mini:~]# dmesg | grep -iE 'rt2800|usb'
usb 1-1.3: new high-speed USB device number 4
usb 1-1.3: RT chipset 5390, rev 0502 detected
ieee80211 phy0: rt2x00_set_rt: Info - RT chipset 5390, rev 0502 detected
ieee80211 phy0: Selected rate control algorithm 'minstrel_ht'
usbcore: registered new interface driver rt2800usb

[root@pa-mini:~]# ip link
3: wlan0: <BROADCAST,MULTICAST> ...
```

Plug in → `wlan0` appears. Firmware (`rt2870.bin`) is loaded automatically from `/lib/firmware/` (ships with `linux-firmware`). Then scan/connect exactly as Ch 55E:

```
[root@pa-mini:~]# ip link set wlan0 up
[root@pa-mini:~]# wpa_supplicant -B -i wlan0 -c /etc/wpa_supplicant.conf -D nl80211
[root@pa-mini:~]# udhcpc -i wlan0
```

Total bring-up is three steps. Insert the dongle. Copy the firmware if it is not present. Connect. About five minutes.

RT5370 and MT7601 are *soft-MAC* chips. They use mac80211: the kernel does the 802.11 MAC, the chip is just a radio. This is why integration is clean. mac80211 and cfg80211 handle the protocol work, and the chip driver is a thin USB-to-radio shim.
**MAC** - Media Access Control in networking and radio chapters. It is the layer that owns framing and medium access.

## 92.3  The painful case (RTL8188EUS)

Most cheap "USB WiFi" dongles sold as "for Raspberry Pi" are RTL8188EUS. They're full-MAC-ish (Realtek's own MAC in a half-baked driver). Two driver options:

### Option A: in-tree `r8188eu` (staging)

Since kernel 5.18, there's a staging driver `drivers/staging/r8188eu/`. Enable `CONFIG_R8188EU=m`. It handles **station mode** (connect to an AP) adequately. For a product that just needs to join a WiFi network, this is enough and it's *in-tree* (builds with the kernel, tracks API changes).

```
[root@pa-mini:~]# dmesg | grep 8188
r8188eu 1-1.3:1.0: Firmware Version 11, SubVersion 1, Signature 0x88e0
r8188eu 1-1.3:1.0 wlan0: renamed from wlan0
```

### Option B: out-of-tree `rtl8188eus`

The aircrack-ng `rtl8188eus` driver supports AP mode, monitor mode, packet injection, and better performance. But it's **out-of-tree**:

```sh
# On the build host or target:
git clone https://github.com/aircrack-ng/rtl8188eus
cd rtl8188eus
make ARCH=arm CROSS_COMPILE=arm-linux-gnueabihf- KSRC=/path/to/kernel
# Install the resulting 8188eu.ko
```

The pain:
- **Breaks on kernel upgrade.** The driver uses internal kernel APIs that change between versions. Each kernel bump may require patching the driver.
- **DKMS** automates the rebuild but only if a compatible driver version exists for the new kernel.
- **Quality**: power management is poor (the dongle runs hot, drains battery), and it occasionally wedges requiring a re-plug.

### The recommendation

For a *product*: **don't use RTL8188EUS** unless you need its AP/monitor features. Use RT5370 or MT7601 (in-tree, clean). The RTL8188EUS is fine for a hobby project or a dev board where you'll manage the driver manually — but for an 8-year-life product, the out-of-tree maintenance cost is real.

## 92.4  How USB WiFi differs from SDIO WiFi

| | SDIO WiFi (Ch 91) | USB WiFi |
|---|---|---|
| Bring-up effort | high (transport, pwrseq, NVRAM, clock) | low (plug in) |
| Per-board config | NVRAM file required | none (firmware is generic) |
| Bus | dedicated SDIO | shared USB |
| Bandwidth contention | none | competes with other USB devices |
| Power | soldered, low | dongle, often higher (no PM tuning out-of-tree) |
| Antenna | on-board (you design it) | on the dongle (vendor's) |
| Form factor | soldered chip | external dongle (or soldered USB module) |

USB WiFi trades bring-up ease for bus contention and (often) worse power management. For a quick bring-up or a field-swappable WiFi, it's great. For a polished low-power product, soldered SDIO with an in-tree driver is better.

## 92.5  USB bandwidth contention

The i.MX6ULL has USB-2.0 (480 Mbps theoretical, ~320 practical). A USB WiFi dongle + another bandwidth-heavy USB device (a UVC camera from Ch 88, USB Ethernet) on the *same* USB controller compete:

```
[root@pa-mini:~]# # Camera + WiFi on the same hub:
[root@pa-mini:~]# # iperf3 over WiFi while streaming the camera → both degrade
```

Mitigation: the i.MX6ULL has **two USB OTG controllers**. Put the camera on one, WiFi on the other. Each gets its own 480 Mbps.

```
[root@pa-mini:~]# lsusb -t      # shows the bus topology
/:  Bus 01.Port 1: Dev 1, Class=root_hub, Driver=ci_hdrc/1p, 480M
    |__ Port 1: Dev 4, ... rt2800usb         ← WiFi on controller 1
/:  Bus 02.Port 1: Dev 1, Class=root_hub, Driver=ci_hdrc/1p, 480M
    |__ Port 1: Dev 2, ... uvcvideo          ← camera on controller 2
```

## 92.6  AP mode (hostapd)

USB dongles with mac80211 (RT5370, MT7601) and AP-capable firmware can be an *access point*, not just a client:

```sh
# /etc/hostapd.conf
interface=wlan0
driver=nl80211
ssid=MyEmbeddedAP
hw_mode=g
channel=6
wpa=2
wpa_passphrase=secretpassword
wpa_key_mgmt=WPA-PSK
rsn_pairwise=CCMP

[root@pa-mini:~]# hostapd /etc/hostapd.conf &
[root@pa-mini:~]# # Now devices can connect to "MyEmbeddedAP"
# Add a DHCP server (dnsmasq) + IP forwarding for a full hotspot.
```

This turns your i.MX6ULL into a WiFi hotspot — useful for "configure-the-device-from-your-phone" setup flows. RT5370 and MT7601 support this in-tree. RTL8188EUS needs the out-of-tree driver for AP mode.

## 92.7  Lab

1. **RT5370 plug-and-play.** Insert an RT5370 dongle. Verify `wlan0` appears with zero config (firmware from linux-firmware). Connect.
2. **Compare an RTL8188EUS.** Insert one. With the in-tree `r8188eu`, verify station mode works. Note any AP-mode limitation.
3. **Out-of-tree build (RTL8188EUS).** Build the aircrack-ng `rtl8188eus` driver against your kernel. Load it. Test AP mode.
4. **Kernel-upgrade pain demo.** Note the out-of-tree driver's kernel-version assumptions. (Conceptually: a kernel bump may break it.)
5. **Bandwidth contention.** Run iperf3 over USB WiFi while streaming a UVC camera on the *same* USB controller. measure degradation. Move to the second controller. measure improvement.
6. **AP mode.** With RT5370, run hostapd + dnsmasq. connect a phone to your i.MX6ULL hotspot.
7. **Power.** Measure idle current with the USB dongle vs an SDIO module. USB dongles (especially RTL out-of-tree) often run hotter / draw more.

## 92.8  Pitfalls

- **Buying RTL8188EUS expecting it to "just work."** The most common dongle, the most painful driver. For a product, prefer RT5370/MT7601.
- **Out-of-tree driver + kernel upgrade.** Breaks. Pin the kernel, use DKMS with a compatible version, or — better — switch to an in-tree chip.
- **Missing firmware.** `rt2800usb` needs `rt2870.bin`. `mt7601u` needs `mt7601u.bin`. Copy from linux-firmware. Symptom: chip detected, no `wlan0`.
- **Bandwidth contention.** Camera + WiFi on one USB controller → both degrade. Spread across the two controllers.
- **Bus-power limits.** Some dongles draw 400+ mA on TX. A weak VBUS rail browns out → disconnects. Ensure adequate USB power.
- **Counterfeit chips.** A dongle sold as "RT5370" may contain an RTL8188 (or vice versa). Always `lsusb` to confirm the actual chip before committing a design.
- **Monitor/AP mode on the wrong chip.** Not all chips/drivers support AP or monitor mode. Check before designing a feature around it.
- **regdb / country code.** Same as SDIO — install `wireless-regdb` or you're limited to restrictive channels.
- **Soldered USB-WiFi modules.** Some "USB WiFi" is a soldered-on module, not a removable dongle. The driver situation is the same, but now you cannot swap the chip if the driver turns out to be bad. Choose the chip even more carefully.

## 92.9  Going deeper

- **`drivers/net/wireless/ralink/rt2x00/`** — the `rt2800usb` driver (RT5370). A clean mac80211 USB driver.
- **`drivers/net/wireless/mediatek/mt7601u/`** — MT7601.
- **`drivers/staging/r8188eu/`** — the in-tree RTL8188EU staging driver.
- **`drivers/net/wireless/realtek/rtw88/`** — newer Realtek parts coming in-tree.
- **`linux-firmware.git`** — `rt2870.bin`, `mt7601u.bin`.
- **`hostapd` documentation** — for AP mode.
- **aircrack-ng `rtl8188eus` repo** — the out-of-tree driver (and its README's kernel-compatibility notes).
- **`Documentation/networking/mac80211-injection.rst`** — monitor/injection mode.

---

> **Note on Group K so far:** SDIO WiFi (Ch 91) for soldered, low-power, in-tree (AP6212). USB WiFi (Ch 92) for quick/swappable but watch the driver story (prefer RT5370/MT7601 in-tree over RTL8188EUS out-of-tree). The next two chapters cover the hosted approach (Ch 93: WiFi via an ESP32 co-processor) and WiFi+BT combo modules (Ch 94).

> Next chapter: **Chapter 93 — Hosted WiFi via ESP32 / ESP8266.** When the SoC has no SDIO and no spare USB — offload WiFi to an ESP co-processor over UART or SPI.
