---
chapter: 93
title: Hosted WiFi via ESP32 / ESP8266
part: VII — Device cookbook
estimated_pages: 18
status: draft
---

# Chapter 93 — Hosted WiFi via ESP32 / ESP8266

> **What:** offloading WiFi to an **ESP32** (or ESP8266) co-processor connected over SPI or UART. Two architectures: **esp-hosted** (the ESP runs firmware that makes Linux see a normal `wlan0` — full network-stack integration), and **AT-command mode** (the ESP runs the TCP/IP stack itself; Linux talks to it like a modem). For each: the architecture, the bring-up, and how the host-side driver shuttles data.
>
> **Why:** sometimes the SoC has no SDIO and no spare USB (or you want to add WiFi to an existing design without changing the SoC). An ESP32 is a $2 WiFi+BT co-processor you connect over a couple of GPIOs. It's also the answer for *MCU + Linux co-existence* designs, and for adding WiFi to legacy SoCs that predate good WiFi support. The trade-off: lower throughput than SDIO/USB, and you now have *two* firmwares to manage.
>
> **Focus:** two very different offload models. esp-hosted treats the ESP as a *dumb radio*. Linux runs the IP stack and just sends 802.11 frames through the ESP. From Linux's view there is a normal `wlan0` with wpa_supplicant on top. AT-command treats the ESP as a *smart modem*. The ESP runs its own TCP/IP stack and Linux speaks `AT+CIPSTART` to open sockets. Simple, but limited and non-standard. The choice between them shapes the rest of the design.
>
> **Tooling.** This chapter uses `wpa_supplicant`, `iw`, the `esp-hosted` kernel module + firmware on the ESP.
> - **Ubuntu-base (target):** `apt install wpasupplicant iw`
> - **Buildroot:** `BR2_PACKAGE_WPA_SUPPLICANT=y BR2_PACKAGE_IW=y`
> - Full per-tool reference: [Userspace tooling appendix](../part5-rootfs/appendix-tooling.md).

## 93.1  Why hosted WiFi

| Scenario | Why hosted WiFi |
|----------|-----------------|
| SoC has no SDIO and no free USB | ESP over SPI/UART uses just GPIOs |
| Adding WiFi to a legacy design | no SoC change; bolt on an ESP module |
| MCU + Linux hybrid product | the ESP can also do real-time tasks |
| Want WiFi + BT in one cheap part | ESP32 has both |
| Strict EMC / certification | the ESP module is pre-certified (FCC/CE) — saves you RF certification |

One often-missed advantage: an ESP32 *module* (not the bare chip) ships with FCC/CE/IC modular certification. If you mount the module without changing the antenna, your product inherits the certification. You skip an expensive antenna-certification step. For low-volume products, this alone can justify hosted WiFi.

The cost: throughput tops out around 20 Mbps (SPI) or much less (UART), vs 30–50 Mbps for SDIO/USB. You also maintain the ESP firmware on top of the Linux side.

## 93.2  The two architectures

### esp-hosted: ESP as a dumb radio

```
   Linux: wpa_supplicant, full IP stack, wlan0
        │ nl80211 / netdev
        ▼
   esp32_sdio / esp32_spi driver (Espressif's Linux driver)
        │ SPI or SDIO transport (a custom framed protocol)
        ▼
   ESP32 running esp-hosted firmware
        │  (just relays 802.11 frames + control)
        ▼
   radio
```

Linux sees a normal `wlan0`. wpa_supplicant runs on Linux. The ESP is a transport — it moves frames and relays cfg80211 commands. This is the "proper" integration: standard tools, standard behavior, the ESP's own IP stack is *not* used.

esp-hosted also relays Bluetooth, sending HCI over the same transport. So one ESP32 gives Linux both `wlan0` and `hci0`.

### AT-command: ESP as a smart modem

```
   Linux: your app sends AT commands over a UART
        │ /dev/ttymxc1 (raw UART)
        ▼
   ESP8266/ESP32 running AT firmware
        │  (runs its OWN TCP/IP stack)
        ▼
   radio
```

Linux talks to the ESP like a dial-up modem:

```
AT+CWJAP="MySSID","password"      ← join an AP
AT+CIPSTART="TCP","192.168.1.10",80  ← open a TCP socket
AT+CIPSEND=18                      ← send 18 bytes
GET / HTTP/1.0\r\n\r\n
```

The ESP runs the entire network stack; Linux just orchestrates via AT strings. Simple, but: no standard `wlan0`, no wpa_supplicant, no Linux sockets — your app speaks the AT dialect. Limited to a handful of simultaneous connections. Non-standard.

### Choosing

- **esp-hosted**: when you want WiFi to behave like real WiFi — standard tools, multiple sockets, Linux's IP stack, TLS via OpenSSL, etc. It is the right choice for production. You need both the esp-hosted firmware on the ESP and the matching Linux driver.
- **AT-command**: when you want dead-simple, a few connections, and don't mind a non-standard interface. AT-command mode is common in quick prototypes and in MCU-style code. Avoid it for any product that needs Linux's network ecosystem (sockets, TLS, multiple connections, NetworkManager).

## 93.3  esp-hosted bring-up (SPI transport)

Espressif's esp-hosted has two parts: firmware flashed to the ESP32, and a Linux driver (out-of-tree, from Espressif's `esp-hosted` repo).

Wiring (SPI mode):

```
   i.MX6ULL eCSPI3        ESP32
   ──────────────         ─────
   MOSI ───────────────►  GPIO13 (HSPI MOSI)
   MISO ◄───────────────  GPIO12
   SCLK ───────────────►  GPIO14
   CS   ───────────────►  GPIO15
   GPIO (handshake) ◄───  GPIO2   (ESP signals "data ready")
   GPIO (data-ready) ◄──  GPIO4
   reset GPIO ─────────►  EN (reset the ESP)
```

The two extra GPIOs (handshake + data-ready) are the ESP's way of telling the host "I have data" without the host polling — essential for the SPI transport's flow control.

DT:

```dts
&ecspi3 {
    esp32@0 {
        compatible = "espressif,esp32-spi";
        reg = <0>;
        spi-max-frequency = <10000000>;
        reset-gpios = <&gpio4 10 GPIO_ACTIVE_LOW>;
        data-ready-gpios = <&gpio4 11 GPIO_ACTIVE_HIGH>;
        handshake-gpios = <&gpio4 12 GPIO_ACTIVE_HIGH>;
    };
};
```

Build + load Espressif's driver (out-of-tree):

```
[root@pa-mini:~]# insmod esp32_spi.ko
[root@pa-mini:~]# dmesg | grep -i esp
esp32: Resetting ESP32
esp32: ESP32 chip detected, firmware version 1.0.3
esp32: Features: WLAN + BT/BLE
esp32_spi: Network interface 'espsta0' created
esp32_spi: Bluetooth HCI interface created

[root@pa-mini:~]# ip link
3: espsta0: <BROADCAST,MULTICAST> ...     ← the WiFi interface
```

Now `espsta0` behaves like any `wlan0` — wpa_supplicant, DHCP, etc.:

```
[root@pa-mini:~]# wpa_supplicant -B -i espsta0 -c /etc/wpa_supplicant.conf -D nl80211
[root@pa-mini:~]# udhcpc -i espsta0
[root@pa-mini:~]# ping 8.8.8.8
```

Throughput: ~10–20 Mbps over SPI at 10 MHz. Adequate for IoT telemetry, MQTT, OTA updates; not for video streaming.

## 93.4  How the esp-hosted driver works

The driver is a **netdev** (network device) that wraps the SPI transport:

```c
/* Conceptual — esp-hosted SPI driver structure */

/* Transmit: kernel hands us an skb, we frame + SPI it to the ESP */
static netdev_tx_t esp_xmit(struct sk_buff *skb, struct net_device *ndev)
{
    struct esp_priv *priv = netdev_priv(ndev);
    /* Prepend the esp-hosted protocol header (interface type, length) */
    struct esp_payload_header *hdr = skb_push(skb, sizeof(*hdr));
    hdr->if_type = ESP_STA_IF;
    hdr->len = skb->len;
    /* Queue for the SPI worker to send on the next transaction */
    skb_queue_tail(&priv->tx_q, skb);
    schedule_work(&priv->tx_work);
    return NETDEV_TX_OK;
}

/* The SPI worker: full-duplex transaction exchanges TX and RX simultaneously */
static void esp_spi_work(struct work_struct *w)
{
    /* Wait for the ESP's data-ready/handshake GPIO */
    /* Do a full-duplex SPI transfer: send a queued TX packet,
       receive whatever the ESP has pending */
    spi_sync(priv->spi, &msg);
    /* Parse the received buffer's esp header; if it's a data frame,
       build an skb and netif_rx() it up the stack */
}

static const struct net_device_ops esp_netdev_ops = {
    .ndo_start_xmit = esp_xmit,
    .ndo_open  = esp_open,
    .ndo_stop  = esp_stop,
};
```

The ESP's transport protocol multiplexes several streams over the same SPI link: WiFi-STA frames, WiFi-AP frames, BT-HCI packets, and control commands. An `if_type` field in the header distinguishes them. The driver demuxes received packets to the right interface (`espsta0`, `hci0`, etc.).

Control (scan, connect) goes through a separate control path — the driver sends "control request" packets (a protobuf-encoded command) and the ESP firmware executes them, mimicking cfg80211 ops. So `wpa_supplicant`'s nl80211 scan request → cfg80211 → the esp driver's `.scan` → a control packet to the ESP → the ESP scans → results come back → reported up. The structure mirrors brcmfmac (Ch 91). Only the transport changes — the esp-hosted SPI protocol instead of SDIO.

## 93.5  AT-command mode

For the simpler AT approach, the ESP runs Espressif's AT firmware. Linux talks raw UART:

```c
/* User-space, talking to the ESP over /dev/ttymxc1 */
int fd = open("/dev/ttymxc1", O_RDWR);
/* set 115200 8N1 via termios */

write(fd, "AT+CWMODE=1\r\n", 13);          /* station mode */
expect_ok(fd);
write(fd, "AT+CWJAP=\"MySSID\",\"pass\"\r\n", ...);  /* join AP */
expect("WIFI CONNECTED", fd);
write(fd, "AT+CIPSTART=\"TCP\",\"192.168.1.10\",80\r\n", ...);
expect("CONNECT", fd);
write(fd, "AT+CIPSEND=18\r\n", ...);
expect(">", fd);
write(fd, "GET / HTTP/1.0\r\n\r\n", 18);
/* read +IPD response with the HTTP reply */
```

This is *user-space* code talking to a UART — no kernel driver at all (just the standard UART tty). It's the same pattern as a cellular AT modem (Ch 103). Simple, but: parsing AT responses is fiddly, only ~5 simultaneous connections, no TLS unless the firmware supports it, no integration with Linux sockets.

If you want AT-mode to look like a network interface, the kernel's PPP driver (`drivers/net/ppp/`) plus a chat script can layer PPP over the AT link. esp-hosted is still the better choice for a real `wlan0`, though.

## 93.6  esp-hosted vs AT — decision table

| | esp-hosted | AT-command |
|---|---|---|
| Linux sees | `wlan0` (standard) | a UART |
| Network stack | Linux's (full) | the ESP's (limited) |
| Tools | wpa_supplicant, ip, sockets | custom AT parser |
| TLS | OpenSSL on Linux | only if firmware supports |
| Simultaneous connections | unlimited (Linux sockets) | ~5 |
| Throughput | ~10–20 Mbps (SPI) | ~1–5 Mbps (UART) |
| Complexity | out-of-tree driver + firmware | just a UART + your AT parser |
| Bluetooth | yes (hci0 too) | ESP-dependent |
| Best for | real products | quick prototypes, MCU-style |

## 93.7  Lab

1. **Flash esp-hosted firmware** to an ESP32 (Espressif's tool). Wire SPI + handshake/data-ready GPIOs.
2. **Build + load the esp32_spi driver.** Verify `espsta0` appears + the BT `hci0`.
3. **Connect.** wpa_supplicant on `espsta0`, DHCP, ping. Measure throughput with iperf3 (~10–20 Mbps).
4. **Bluetooth too.** `hciconfig hci0 up`; scan for BLE devices — the same ESP provides BT.
5. **AT-command comparison.** Flash AT firmware to a second ESP. Talk to it over UART: join AP, open a TCP socket, fetch a web page. Compare effort vs esp-hosted.
6. **Throughput vs SPI clock.** Vary the esp-hosted SPI clock (5/10/20 MHz); measure throughput scaling.
7. **Co-existence role.** Use the ESP32 *also* for a real-time GPIO task (it has its own CPU); demonstrate WiFi + a real-time job on the co-processor while Linux does the heavy lifting.

## 93.8  Pitfalls

- **Firmware version mismatch.** The esp-hosted Linux driver and the ESP firmware must be compatible versions. A mismatch → the driver loads but no interface, or garbled transport. Pin both versions.
- **Missing handshake/data-ready GPIOs.** The SPI transport needs them for flow control. Without them, the host polls blindly and loses packets. Wire and declare both.
- **Out-of-tree driver maintenance.** esp-hosted's Linux driver is out-of-tree (Espressif's repo) — same kernel-upgrade fragility as Ch 92's RTL8188EUS. Plan for it.
- **AT response parsing fragility.** AT firmware responses vary across firmware versions ("OK" vs "SEND OK" vs "+CIPSEND:"). A brittle parser breaks on a firmware update. Parse defensively.
- **UART throughput ceiling.** AT over 115200 baud = ~11 KB/s raw, less after framing. For anything but tiny telemetry, use SPI esp-hosted or a higher UART baud.
- **Two firmwares to manage.** You now own the ESP firmware *and* the Linux side. OTA must update both, in a safe order.
- **Shared SPI bus contention.** If the ESP shares an SPI bus with other devices, the esp-hosted transport's latency suffers. Give it a dedicated bus or chip-select with priority.
- **ESP brownout.** The ESP32 draws current spikes (~500 mA) on TX. A weak rail → brownout resets → WiFi drops. Decouple well.

## 93.9  Going deeper

- **Espressif `esp-hosted` repo** (github.com/espressif/esp-hosted) — firmware + Linux driver + protocol docs.
- **`esp-hosted` protocol documentation** — the framed SPI/SDIO transport.
- **Espressif AT firmware documentation** — the AT command set.
- **`drivers/net/` netdev model** — how a network interface driver is structured (esp-hosted is a netdev).
- **`Documentation/networking/`** — Linux network device internals.
- **`drivers/bluetooth/`** — for the HCI side of esp-hosted (Ch 95).

> Next chapter: **Chapter 94 — WiFi+BT combo modules.** One chip, two radios, one antenna — the AP6212 and RTL8723, the shared-antenna coexistence problem, and bringing up WiFi (SDIO) + Bluetooth (UART) simultaneously.
