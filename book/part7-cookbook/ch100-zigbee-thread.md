---
chapter: 100
title: ZigBee / Thread / 802.15.4
part: VII - Device cookbook
estimated_pages: 18
status: draft
---

# Chapter 100: ZigBee / Thread / 802.15.4

> **Privilege boundary:** $ means normal user. # or sudo means root and can change host or target state.
> After a privileged command, verify the expected device, service, or file appears before continuing. Roll back by undoing the config change or stopping the service you just enabled.


> **What:** the **IEEE 802.15.4** family. It is the certified mesh networking stack that powers most retail smart-home meshes: Philips Hue, Aqara, Eve, IKEA Trådfri, Google Nest. We compare **TI CC2530** (legacy ZigBee 3.0), **Nordic nRF52840** (modern, OpenThread + ZigBee + BLE in one chip), and **Silicon Labs EFR32MG** (commercial-grade ZigBee/Thread). On Linux, the i.MX6ULL is the **gateway** (running zigbee2mqtt, Thread Border Router, or Home Assistant), not a node. The radio is on a coprocessor module. Linux talks to it over UART/USB as a **ZNP** (ZigBee Network Processor) or **NCP** (Network Coprocessor).
>
> **Why:** 802.15.4 is the only mesh radio with serious certification, vendor cross-compat, and consumer-product penetration. If you're building a *gateway* (smart-home hub, factory data collector, gateway-as-a-service), you're integrating with 802.15.4 modules. You do not write the nodes. You buy them. The Linux skill is **gateway integration**: pairing the radio coprocessor, serial framing of the host-controller protocol, MQTT bridging, OTA upgrade management.
>
> **Focus:** **the radio firmware is a black box. You talk to it over a serial protocol (EZSP, Thread Spinel, ZNP) that mirrors the network layer**. Just like BLE HCI (Ch 95), the host-controller boundary is what you debug. Once the gateway daemon (zigbee2mqtt, OpenThread Border Router) is up, MQTT/MDNS handles the rest. No kernel driver to write, `ttyUSB`/`spidev` is the chip-side interface and a user-space daemon is the brain.
>
> **Tooling.** This chapter uses Node.js 18+, `zigbee2mqtt` (via npm), Mosquitto broker. For Thread, build `openthread/ot-br-posix` from source.
> - **Ubuntu-base (target):** `apt install nodejs npm mosquitto mosquitto-clients`
> - **Buildroot:** `BR2_PACKAGE_NODEJS=y BR2_PACKAGE_MOSQUITTO=y  # otbr typically self-built`
> **Buildroot:** a configuration-driven build system that produces a complete root filesystem and related images.
> - Full per-tool reference: [Userspace tooling appendix](../part5-rootfs/appendix-tooling.md).
> **MCU bridge:** Think of the rootfs as the firmware image's file-backed runtime environment. On an MCU you link everything into flash. On Linux, programs and config live in this mounted tree.
> **rootfs:** root filesystem, the directory tree mounted at / that contains /bin, /etc, /dev, and libraries.


## 100.1  The three protocols at a glance

| | ZigBee 3.0 | Thread | 802.15.4 raw |
|---|---|---|---|
| PHY | 802.15.4 (2.4 GHz) | 802.15.4 (2.4 GHz) | 802.15.4 |
| MAC | ZigBee | IPv6/6LoWPAN | raw |
| Network | mesh, ZigBee | mesh, IPv6 routers | none (you build it) |
| Addressing | 16-bit short + 64-bit IEEE | IPv6 (linklocal + mesh-local + global) | 64-bit IEEE |
| Ecosystem | Philips Hue, Aqara, IKEA, Sengled | Apple HomeKit, Google Nest, Matter | DIY mesh, RPL |
| Linux gateway | zigbee2mqtt + Z2M | OpenThread Border Router (otbr) | custom |
| Certification path | ZigBee Alliance | Thread Group | none |
| Best for | retail smart-home product | next-gen smart home (Matter) | research / one-off |

The big shift: **Matter** (the new consumer smart-home standard) runs *over* Thread (or WiFi). So new gateway designs target **Thread** with the **OpenThread Border Router** stack, while still supporting legacy ZigBee for installed-base reasons. Hence: serious products today bring up both stacks on the same coprocessor (nRF52840 can do both).

## 100.2  Why the radio lives on a coprocessor

A 802.15.4 PHY is timing-strict: ack-on-receive is required within 1 ms, channel hopping happens at sub-ms boundaries, and the MAC retransmit logic must run reliably. Between Linux's scheduling jitter and SPI/USB latency, running the MAC on the host CPU is not reliable.
> **MAC:** Media Access Control in networking and radio chapters. It is the layer that owns framing and medium access.
> **PHY:** physical-layer block or chip that converts digital MAC signals to electrical or radio signals.

Solution: the radio chip runs **its own firmware**. The firmware contains the PHY and MAC, and may also contain the higher network layers. The Linux host talks to it over UART/USB/SPI using a serial control protocol. There are three common splits:

```
RCP (Radio Co-Processor)        NCP (Network Co-Processor)        SoC (full host)
─────────────────────────       ──────────────────────────        ───────────────
Application                     Application                       Application
Routing                         Routing                          ╱
MAC               ◄── chip ──►  MAC               ◄── chip ──►  Routing
PHY                             PHY                              MAC
                                                                  PHY
        Linux                            Linux                    (no Linux)
        runs everything                  runs application
        above MAC                        only
```

| Split | Chip firmware | Linux side | When to use |
|---|---|---|---|
| **RCP** | PHY + MAC only | full Thread stack (otbr) | OpenThread Border Router; modern Thread/Matter |
| **NCP** | PHY + MAC + network | application-only (Spinel commands) | older Thread setups |
| **ZNP** | PHY + MAC + ZigBee NWK + APS | application + framework (zigpy) | zigbee2mqtt + zigpy_znp |
| **EZSP** | PHY + MAC + ZigBee NWK + APS | EZSP host (bellows) | Silicon Labs ZigBee dongles |

This chapter focuses on the **gateway role**: RCP for Thread, ZNP/EZSP for ZigBee.

## 100.3  The physical layer (because it matters even when you don't write it)

802.15.4 PHY:
- 2.4 GHz, channels 11–26 (5 MHz spacing). Channel 11 = 2405 MHz. Channel 26 = 2480 MHz.
- O-QPSK modulation, 250 kbps gross, ~128 byte max frame.
- –96 dBm receiver sensitivity (vs LoRa SF12's –137. Vs BLE 1M's –93). 
- Range similar to BLE.

Channel/WiFi overlap (the most common cause of "my ZigBee network is flaky" reports):

```
Channel:  11   12   13   14   15   16   17   18   19   20   21   22   23   24   25   26
Freq:    2405 2410 2415 2420 2425 2430 2435 2440 2445 2450 2455 2460 2465 2470 2475 2480

WiFi ch 1:  ████████████████████████
WiFi ch 6:                ████████████████████████
WiFi ch 11:                              ████████████████████████

ZigBee-friendly: 15, 20, 25, 26 (avoid WiFi 1/6/11)
Thread default: 11, 15, 20, 25
```

Plan the ZigBee/Thread channel with `nmcli dev wifi list` and `iwlist scan` to see local WiFi channels first. A poorly chosen channel can give 30 % packet loss in the field. The same network "works fine at home" because the home WiFi happens to sit on a different channel than the customer's.

## 100.4  The ZigBee stack (vendor-rolled, you don't touch it)

For context, the ZigBee stack the coprocessor runs:

```
   ┌────────────────────────────┐
   │  Application (your cluster) │   ← Lighting, OnOff, Color, Thermostat...
   ├────────────────────────────┤
   │  ZCL — ZigBee Cluster Lib  │   ← attribute + command sets per device class
   ├────────────────────────────┤
   │  APS (Application Support) │   ← binding, group addressing
   ├────────────────────────────┤
   │  NWK — Network             │   ← routing (AODV-derived), addressing
   ├────────────────────────────┤
   │  MAC (802.15.4)            │   ← CSMA/CA, ACK, frame format
   ├────────────────────────────┤
   │  PHY (802.15.4)            │   ← O-QPSK, channel selection
   └────────────────────────────┘
```

Devices are categorized by ZCL **clusters**. A light is a "Color Light" endpoint with clusters: OnOff (0x0006), LevelControl (0x0008), ColorControl (0x0300). A sensor exposes Temperature (0x0402), RelativeHumidity (0x0405). Zigbee2mqtt knows all of this and maps each device to MQTT topics.

## 100.5  Bringing up a CC2530 ZNP on the i.MX6ULL

The CC2530 is the most common cheap ZigBee dongle (Aliexpress + CC2531 USB sticks). Flash it with TI's **ZNP firmware** (`CC2531ZNP-Prod.hex`), wire UART (or USB if a CC2531 USB stick), then bring up **zigbee2mqtt**.

### Step 1: flash ZNP firmware

You need a TI CC Debugger or a Raspberry Pi running `cc2538-bsl` (some firmwares support over-air-bootloader. Most don't on first flash). The firmware blob is from TI's Z-Stack SDK.

### Step 2: device tree (UART variant)

```dts
&uart3 {
    pinctrl-names = "default";
    pinctrl-0 = <&pinctrl_uart3>;
    status = "okay";
    /* ZNP talks at 115200 8N1, no flow control needed for ZNP */
};
```

For USB CC2531 dongle, nothing in DT, `cdc-acm` autobinds and you get `/dev/ttyACM0`.

### Step 3: install + configure zigbee2mqtt

```sh
# Node 18+ required
apt install nodejs npm
npm install -g zigbee2mqtt

# /opt/zigbee2mqtt/data/configuration.yaml
mqtt:
  base_topic: zigbee2mqtt
  server: 'mqtt://localhost:1883'
serial:
  port: /dev/ttyACM0      # or /dev/ttymxc2 for UART CC2530
  adapter: zstack          # for TI CC253x
advanced:
  pan_id: 0x1a62
  channel: 25              # avoid WiFi 1/6/11
  network_key: GENERATE    # generates on first start; pin afterwards
permit_join: true          # for initial pairing; set false in prod
```

### Step 4: pair a device

```sh
zigbee2mqtt &
# log: "Zigbee: started"
# Hold the IKEA bulb's reset button 6s; bulb joins
# log: "Successfully interviewed IKEA TRADFRI bulb"
```

zigbee2mqtt's strength: it knows ~3000 device types and maps each to MQTT topics:

```sh
mosquitto_sub -t 'zigbee2mqtt/+/+' -v
# zigbee2mqtt/0xabcd1234/state ON
# zigbee2mqtt/0xabcd1234/brightness 254
```

To control:

```sh
mosquitto_pub -t 'zigbee2mqtt/0xabcd1234/set' -m '{"state":"OFF"}'
```

### How the zigpy_znp adapter actually works

`zigbee2mqtt` uses the `zigbee-herdsman` library, which speaks the **ZNP framing protocol** over UART. Each frame:

```
   [SOF=0xFE] [LEN] [TYPE=0x4 MSB | SUBSYSTEM] [CMD0] [CMD1] [data...] [FCS]
```

- TYPE+SUBSYSTEM selects whose API (AF=application, ZDO=ZigBee Device Object, SAPI=simple API, SYS=system).
- CMD0/CMD1 identifies the command (e.g., AF_DATA_REQUEST_EXT to send a packet).
- FCS is XOR of LEN through last data byte.

You rarely send raw frames. The adapter does it for you. But `btmon`-style debugging (set `debug:true` in zigbee2mqtt) prints the frame stream. This is how you trace a failed pairing. The protocol is documented in TI's "Z-Stack Monitor and Test API" PDF.

## 100.6  Bringing up an nRF52840 as Thread RCP

This is the modern path. Same chip can do OpenThread Border Router (Matter-ready), BLE Mesh (Ch 97), or ZigBee, your firmware choice.

### Step 1: flash RCP firmware

Build from `openthread/ot-nrf528xx`:

```sh
git clone https://github.com/openthread/ot-nrf528xx
cd ot-nrf528xx && ./script/bootstrap
./script/build nrf52840 USB_trans       # build RCP firmware with USB
nrfjprog --program build/bin/ot-rcp.hex --chiperase --reset
```

Alternatively, Nordic's Connect SDK has a precompiled RCP. The CC2538 is similar but flash via `cc2538-bsl`.

### Step 2: bring up otbr (OpenThread Border Router) on the i.MX6ULL

```sh
git clone https://github.com/openthread/ot-br-posix
cd ot-br-posix && ./script/bootstrap
./script/setup
otbr-agent -I wpan0 -B eth0 spinel+hdlc+uart:///dev/ttyUSB0?uart-baudrate=460800 &
```

What this does:
- `wpan0`: a virtual netdev created by otbr, presents the Thread mesh as a Linux interface.
- `eth0`: the upstream IPv6 interface (otbr advertises a route to the Thread mesh).
- `spinel+hdlc+uart`: the **Spinel** protocol (Thread's equivalent of HCI) framed in HDLC over the USB serial line.

Once running, `wpan0` shows up:

```sh
ip link show wpan0
# 6: wpan0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1280 ...
ip -6 addr show wpan0
# inet6 fd11:22::1/64 scope global
# inet6 fe80::abcd:.../64 scope link
```

A Thread device joining the network gets an IPv6 in `fd11:22::/64`. You ping it like any IPv6 host. **This is what makes Thread different from ZigBee**: every node is a normal IPv6 endpoint. Matter rides on top of this.

### Step 3: pair a Thread device

The simplest: a Nordic nRF52840 DK flashed with the `cli` or `srp_client` sample. Get the Thread network credential dataset from otbr:

```sh
otbr-agent
> dataset active -x        # prints hex dataset
0e080000000000010000000300001135060004001fffe002083a900b4e9e30...
```

On the device, paste that dataset and `thread start`. Done, the device joins the mesh and gets an IPv6.

### The Spinel protocol (what's on the wire)

Spinel is a simple TLV-style protocol. Example frame (after HDLC unframing):

```
[Header] [Command-ID] [Property-ID] [Value]
   80          5            17       <dataset>
   ↑           ↑            ↑
   priority    PROP_VALUE_SET  THREAD_DATASET_ACTIVE
   transaction id
```

The Spinel header bits encode flow-control state, transaction IDs, priority. Otbr-agent maps Spinel properties to Linux netdev events. You don't see this unless `--verbose`.

## 100.7  Walk of the openthread `radio` adapter

For curiosity, the radio-side firmware. OpenThread RCP firmware exposes the radio as a Spinel coprocessor. The key file: `src/lib/spinel/radio_spinel.cpp` on the *host* side. `examples/platforms/nrf528xx/src/radio.c` on the *device* side.

Device-side `otPlatRadioTransmit`:

```c
otError otPlatRadioTransmit(otInstance *aInstance, otRadioFrame *aFrame) {
    nrf_802154_buffer_t *buf = nrf_802154_buffer_get();
    memcpy(buf->data, aFrame->mPsdu, aFrame->mLength);
    /* Schedule TX via nrf_802154 driver */
    nrf_802154_transmit_raw(buf->data, NRF_802154_TRANSMIT_DEFAULT);
    /* on TX done, callback fires up to host via Spinel */
}
```

The nRF52840 has a dedicated 802.15.4 hardware accelerator (the `RADIO` peripheral in 802.15.4 mode) that does PHY + MAC ack/retry in silicon. The firmware just orchestrates. This is why even very small MCUs (nRF52833 → 256 KB flash) can do Thread + BLE simultaneously.

You don't write this code unless you're porting OpenThread to a new SoC, you flash a release build.

## 100.8  Matter, what changes

Matter is an application-layer protocol (built on top of Thread or WiFi). For Matter-over-Thread, the gateway role is unchanged, otbr brings up Thread. Matter devices are normal IPv6 nodes on that mesh. The **commissioner** (a phone) provisions devices into the fabric using BLE for the initial pairing handshake, then Thread for subsequent traffic.

For a gateway-class Linux device, install `chip-tool` (the Matter CLI), and your i.MX6ULL becomes a Matter commissioner:

```sh
chip-tool pairing onnetwork-long 1 20202021 0x12CE
chip-tool onoff on 1 1
```

Device 1, endpoint 1, OnOff cluster, On command. This is Matter. Under the hood, it's a packet via otbr's Thread network.

## 100.9  The from-scratch part, a raw 802.15.4 PHY app over an at86rf233

Most readers won't do this, but for completeness: the **at86rf233** (Atmel/Microchip) is a 802.15.4 SPI radio with **no built-in stack**. You drive PHY + minimal MAC in software. Mainline Linux has `drivers/net/ieee802154/at86rf230.c` which exposes the radio as a `wpan0` netdev under the `ieee802154` subsystem (no Thread, raw 802.15.4). You then run `wpan-tools`:

```sh
modprobe at86rf230
iwpan dev wpan0 set pan_id 0xbeef
iwpan dev wpan0 set short_addr 0xabcd
ip link set wpan0 up
# Now you can send raw 802.15.4 frames via SOCK_DGRAM on AF_IEEE802154
```

You can build 6LoWPAN over this:

```sh
ip link add link wpan0 name lowpan0 type lowpan
ip link set lowpan0 up
# Now lowpan0 is IPv6-over-802.15.4 — every node has fe80:: addresses
```

This is the **raw research path**. RPL (the IPv6 routing protocol for 802.15.4 meshes) can run on top via `contiki-ng` or `unstrung` daemons. But for products, Thread + otbr wins.

## 100.10  Lab

1. **CC2531 USB ZigBee.** Buy a Sonoff CC2652P stick (or CC2531 if you find one). Plug into i.MX6ULL's USB. Confirm `/dev/ttyACM0` appears.
2. **Bring up zigbee2mqtt.** Install, configure `configuration.yaml`, start. Watch logs for "started."
3. **Pair an IKEA bulb / Aqara sensor.** Permit-join, factory-reset the device. Observe zigbee2mqtt's interview + MQTT topic generation.
4. **Control via MQTT.** `mosquitto_pub` to the device's `set` topic. Watch the bulb toggle. Subscribe to its state. See the report come back.
5. **Multi-node + relay.** Add 3+ mains-powered devices (they become routers). Add a battery sensor (end device). Move the sensor far from the gateway. Verify it still reports (it routes through a mains-powered intermediate).
6. **nRF52840 as RCP.** Flash OpenThread RCP firmware. Plug in via USB. Bring up otbr-agent on i.MX6ULL.
7. **Thread CLI device.** Flash a second nRF52840 with the `cli` sample. Paste the dataset from otbr. `thread start`. Observe the joining log on otbr. `ip -6 neigh show dev wpan0` lists the new node.
8. **IPv6 ping a Thread node.** From the i.MX6ULL, `ping6 fd11:22::abcd...`. Latency ~10–50 ms. Throughput ~30 kbps (one hop).
9. **Matter commissioning (stretch).** Install `chip-tool`. Commission a Matter device (Eve Door & Window sensor is cheap and Matter-native). Read its attributes via `chip-tool`.
10. **Home Assistant integration.** Install HA. Auto-discover the MQTT-bridged ZigBee devices and the Matter devices. Build a dashboard that shows them and reacts to one.

## 100.11  Pitfalls

- **Channel collision with WiFi.** 80 % of "ZigBee unreliable" reports are this. Pick channel 15/20/25/26. Verify with `iwlist scan` on a phone.
- **USB power for the dongle.** Sonoff CC2652P pulls ~80 mA peaks. Some hubs brown-out. Use a powered hub or solder direct.
- **Old ZNP firmware.** TI ships multiple ZNP firmware versions. The protocol changes subtly between Z-Stack 2.x and 3.x. Pin your firmware version + match the zigbee2mqtt-supported list.
- **`permit_join` left on.** A rogue ZigBee device could join your network. Always set `permit_join: false` outside of pairing windows.
- **Network key rotation.** Once set, do not change. Devices store the network key in their non-volatile memory and a key change un-joins everything.
- **otbr-agent without IPv6 in upstream network.** otbr forwards Thread IPv6 to the upstream, if upstream isn't IPv6-capable, advertised routes go nowhere. Test with `ping6 google.com` on the otbr host first.
- **Matter requires precise time.** Devices reject commissioning if the commissioner's clock is wrong by more than ~30 s. Run NTP on the i.MX6ULL.
- **Spinel HDLC framing**: bad UART flow control corrupts Spinel frames silently. The otbr-agent will log "spinel: bad checksum", that's almost always a missing RTS/CTS on the UART path.
- **ZigBee != Thread.** They share PHY/MAC but not MAC commands. A ZigBee device cannot join a Thread network and vice versa. Choose your firmware stack accordingly.
- **End-device sleep timing.** End devices poll their parent for downlink data every `keep_alive` seconds. A control command takes up to one polling interval to arrive. Tune accordingly (faster polling = shorter battery life).

## 100.12  Going deeper

- **`zigpy/zigpy-znp`**: the Python adapter for TI CC2530/CC2538 ZNP firmware. Readable code for the framing protocol.
- **`Koenkk/zigbee2mqtt`** + **`Koenkk/zigbee-herdsman`**, the dominant ZigBee gateway daemon.
- **`openthread/openthread` and `openthread/ot-br-posix`**: Thread + Border Router. The `src/core/api/` docs are good.
- **Silicon Labs EmberZNet**: commercial alternative. If you go this path, EZSP + bellows.
- **Matter SDK (`project-chip/connectedhomeip`)**: the open-source Matter implementation. `chip-tool` is the CLI.
- **IEEE 802.15.4-2020**: the PHY/MAC standard.
- **`drivers/net/ieee802154/`**: kernel-level 802.15.4 + 6LoWPAN drivers (for raw experiments).
- **Ch 95**: HCI/Bluetooth, same host-controller pattern.
- **Ch 99**: nRF24L01 ad-hoc, the unstandardized alternative.

---

> Next chapter: **Chapter 101: UWB ranging**, sub-10-cm indoor positioning with DWM1000/DWM3000.
