---
chapter: 102
title: USB 4G LTE modems (Quectel EC20/EC25, SimCom SIM7600, Telit LM940)
part: VII — Device cookbook
estimated_pages: 18
status: draft
---

# Chapter 102 — USB 4G LTE modems

> **What:** the **USB-attached cellular modem** — the most common cellular path on Linux. Three modules compared: **Quectel EC20/EC25** (the canonical, LTE Cat-4 / Cat-6), **SimCom SIM7600** (cheaper, more variants), **Telit LM940** (industrial Cat-11, premium pricing). We dissect the **USB composite device** the modem presents (typically 4–7 endpoints: AT, GPS, modem, QMI/MBIM data), walk the kernel's `option`/`qmi_wwan`/`cdc_mbim` drivers, write a from-scratch AT-command client + a QMI session opener using libqmi, and bring up data via **ModemManager + NetworkManager** (the modern path) or **`quectel-CM`** / `qmi-network` (manual).
> **Why:** every embedded device that talks to a cellular network uses one of these. The kernel handles the USB plumbing. There are three layers to keep straight: the USB interface mode the modem advertises (RNDIS, ECM, MBIM, QMI, or PPP), the kernel driver that binds to it, and the user-space tool that activates the data session. Most "modem doesn't connect" bugs are a mismatch between these three layers. After this chapter you can read an `lsusb` line, name the driver that bound each endpoint, and trace the data path the IP packets take.
> **Focus:** **the modem is a small embedded system in a USB case. It exposes several USB interfaces at once.** AT commands on `/dev/ttyUSB2` give you SMS, signal strength, and configuration. GPS NMEA on `/dev/ttyUSB1` gives you location. The data path is a separate USB interface that becomes `wwan0` (QMI) or `cdc-wdm0`+`wwan0` (MBIM) — once activated, it's a normal network interface that `ip route` sees. The split is unusual on Linux. The diagram in §102.3 makes it concrete.
> **Tooling.** This chapter uses `ModemManager` + `NetworkManager`, `libqmi-utils` (`qmicli`), `libmbim-utils` (`mbimcli`).
> - **Ubuntu-base (target):** `apt install modemmanager network-manager libqmi-utils libmbim-utils`
> - **Buildroot:** `BR2_PACKAGE_MODEM_MANAGER=y BR2_PACKAGE_NETWORK_MANAGER=y BR2_PACKAGE_LIBQMI=y BR2_PACKAGE_LIBMBIM=y`
> - Full per-tool reference: [Userspace tooling appendix](../part5-rootfs/appendix-tooling.md).

## 102.1  Module comparison

| | Quectel EC25 | Quectel EC20 | SimCom SIM7600 | Telit LM940 |
|---|---|---|---|---|
| Category | LTE Cat-4 | LTE Cat-4 | LTE Cat-4 | LTE Cat-11 |
| Downlink | 150 Mbps | 150 Mbps | 150 Mbps | 600 Mbps |
| Uplink | 50 Mbps | 50 Mbps | 50 Mbps | 75 Mbps |
| 3G fallback | yes (WCDMA/HSPA) | yes | yes | yes |
| 2G fallback | yes (GSM) | yes | yes | no |
| GPS / GNSS | yes (GPS+GLONASS+BeiDou+Galileo) | yes (GPS+GLONASS) | yes (multi-GNSS) | yes |
| USB modes | QMI / MBIM / RNDIS / ECM / PPP | QMI / RNDIS / ECM / PPP | QMI / MBIM / ECM / PPP | QMI / MBIM / RNDIS / ECM |
| Voice (VoLTE) | yes | yes | yes | yes |
| Form factor | M.2 / Mini-PCIe / LCC | M.2 / Mini-PCIe / LGA | M.2 / Mini-PCIe | M.2 / Mini-PCIe |
| Approx cost | $30–50 | $25–40 | $25–40 | $200+ |
| Power (peak TX) | 2.5 W | 2.5 W | 2.0 W | 3.0 W |

**Pick guide:**
- **EC25** — the default for most new designs; well-supported on Linux, widely available, multi-region SKUs (EC25-E for EMEA, EC25-A for North America, EC25-AU for Asia-Pacific…).
- **EC20** — older but cheaper; identical software.
- **SIM7600** — slightly cheaper, supports more legacy bands (GSM-only fallback in rural areas).
- **LM940** — when you need Cat-11 (600 Mbps DL) for video uplink or backhaul; pay the premium.

## 102.2  What the modem looks like to Linux

Plug in a modem; `lsusb -v` shows something like:

```
Bus 001 Device 003: ID 2c7c:0125 Quectel Wireless EC25
  bConfigurationValue 1
  bNumInterfaces 5
    Interface 0: 0xff/0xff/0xff vendor-specific  (diagnostic — DM)
    Interface 1: 0xff/0xff/0xff vendor-specific  (GPS NMEA)
    Interface 2: 0xff/0xff/0xff vendor-specific  (AT command)
    Interface 3: 0xff/0xff/0xff vendor-specific  (AT modem aux)
    Interface 4: 0xff/0xff/ff   QMI (data)
```

This is a **USB composite device** with 5 interfaces. The kernel binds each interface independently:

- Interfaces 0/1/2/3 → `option` driver → `/dev/ttyUSB0..3` (serial channels)
- Interface 4 → `qmi_wwan` driver → `wwan0` (network) + `cdc-wdm0` (QMI control)

If the modem is in **MBIM mode**:
- Last interface bound by `cdc_mbim` → `wwan0` + `cdc-wdm0`

If in **RNDIS** mode:
- Last interface bound by `rndis_host` → `usb0`

If in **ECM** mode:
- Last interface bound by `cdc_ether` → `usb0` (no SIM control — appears as a simple Ethernet)

If in **PPP** mode (legacy):
- All interfaces are `option`; `pppd` runs `/dev/ttyUSB3` and brings up `ppp0`

`lsusb` won't tell you which mode you're in — the **PID** does:

| PID | Mode |
|---|---|
| 2c7c:0125 | QMI default (EC25) |
| 2c7c:0306 | MBIM (EC25 reconfigured via AT+QCFG="usbnet",2) |
| 2c7c:0900 | RNDIS (AT+QCFG="usbnet",3) |
| 2c7c:0121 | ECM (AT+QCFG="usbnet",1) |
| 2c7c:0123 | PPP-only (no high-speed data interface) |

Switching modes is one AT command + reset. **This is the most common reason a modem appears in the wrong mode** — the modem boots in whichever mode was last configured, persisted in its NV memory.

## 102.3  The kernel drivers in detail

```
┌────────────────────────────────────────────────────────────────────┐
│ USB layer (drivers/usb/core/)                                       │
│   Probes the device → matches PID against driver tables             │
└────────────────────────────────────────────────────────────────────┘
           │                  │                  │                  │
           ▼                  ▼                  ▼                  ▼
┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐ ┌────────────┐
│ option           │ │ qmi_wwan         │ │ cdc_mbim         │ │ rndis_host │
│ (serial)         │ │                  │ │                  │ │ cdc_ether  │
│                  │ │                  │ │                  │ │            │
│ creates /dev/    │ │ creates wwan0    │ │ creates wwan0    │ │ creates    │
│   ttyUSB0..3     │ │   (netdev) +     │ │   (netdev) +     │ │ usb0       │
│                  │ │ cdc-wdm0         │ │ cdc-wdm0         │ │ (netdev    │
│                  │ │ (control)        │ │ (control)        │ │ only)      │
└──────────────────┘ └──────────────────┘ └──────────────────┘ └────────────┘
        │                    │                    │                    │
        ▼                    ▼                    ▼                    ▼
┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐ ┌────────────┐
│ minicom, picocom │ │ libqmi:          │ │ libmbim:         │ │ dhclient   │
│ for AT commands  │ │ qmicli           │ │ mbimcli          │ │ usb0       │
│                  │ │ quectel-CM       │ │ ModemManager     │ │            │
│                  │ │ ModemManager     │ │                  │ │            │
└──────────────────┘ └──────────────────┘ └──────────────────┘ └────────────┘
```

Each kernel driver:

- **`option`** (`drivers/usb/serial/option.c`) — recognizes vendor-specific USB serial interfaces from cellular modems. The driver is essentially a giant `option_ids[]` table mapping (vendor, product, interface) → "make this interface a /dev/ttyUSBN serial port." When you plug in a new modem and no `/dev/ttyUSB*` appears, **the most common cause is a missing PID in `option_ids[]`**.
- **`qmi_wwan`** (`drivers/net/usb/qmi_wwan.c`) — handles QMI (Qualcomm MSM Interface) over USB. Creates `wwan0` (netdev for data) and `cdc-wdm0` (character device for QMI control messages). Data packets go in/out of `wwan0` once a session is opened via cdc-wdm0.
- **`cdc_mbim`** (`drivers/net/usb/cdc_mbim.c`) — handles MBIM (Mobile Broadband Interface Model — the USB-IF standard). Same pattern as qmi_wwan but uses MBIM protocol. Preferred for new designs.
- **`rndis_host`** (`drivers/net/usb/rndis_host.c`) — Windows RNDIS Ethernet emulation. Easy: looks like Ethernet, `dhcp`, done. But no fine-grained control (no signal strength, no roaming control).

Walk of `qmi_wwan_probe()`:

```c
static int qmi_wwan_probe(struct usb_interface *intf, ...) {
    struct usbnet *dev;
    int status = usbnet_probe(intf, id);   /* allocate netdev, set up ops */
    if (status) return status;

    /* QMI control channel is a separate USB interface; bind cdc-wdm to it */
    if (qmi_wwan_register_subdriver(dev) == 0) {
        /* /dev/cdc-wdm0 now exists */
    }

    /* Data interface is set up — wwan0 appears, but no IP until QMI session opens */
    return 0;
}
```

Once probed, the data interface waits in an IDLE state. The user-space `qmicli` or ModemManager sends QMI control messages over `cdc-wdm0` (`WDS_START_NETWORK` with APN), the modem allocates a PDP context, returns an IP+gateway+DNS via `WDS_GET_RUNTIME_SETTINGS`, the user-space tool configures `wwan0` with that IP, and traffic flows.

## 102.4  Bringing up data — the modern path (ModemManager + NetworkManager)

```sh
apt install modemmanager network-manager libqmi-utils libmbim-utils

systemctl enable --now ModemManager
systemctl enable --now NetworkManager

# Wait for ModemManager to detect the modem
mmcli -L
# /org/freedesktop/ModemManager1/Modem/0 [Quectel] EC25

mmcli -m 0
#   Modem
#     status: enabled
#     IMEI: 86xxxxxxxxxxxx
#     hardware: Quectel EC25
#     access tech: lte
#     signal quality: 78%

# Create a connection profile
nmcli c add type gsm ifname '*' con-name 4g apn internet
nmcli c up 4g
# Connection successfully activated (D-Bus active path: ...)

ip addr show wwan0
# wwan0: <UP,LOWER_UP> mtu 1500
#   inet 10.x.x.x/30 scope global wwan0
```

ModemManager handles the entire SIM unlock → APN → PDP → DHCP-like-handshake → connection-up chain. NetworkManager adds it to the routing table. `dnsmasq` integration handles DNS.

## 102.5  Bringing up data — manual, from scratch

If you want to understand the path, do everything ModemManager would do by hand.

### QMI path — `qmicli`

```sh
# Check the modem is alive
qmicli -d /dev/cdc-wdm0 --dms-get-ids
# IMEI: 86xxxxxxxxxxxxx

# Set IP family
qmicli -d /dev/cdc-wdm0 --wds-set-ip-family=4

# Open a data session for APN
qmicli -d /dev/cdc-wdm0 --wds-start-network=apn=internet,ip-type=4 \
       --client-no-release-cid
# Network started
# Packet data handle: 0xdeadbeef
# CID: 8

# Get runtime IP
qmicli -d /dev/cdc-wdm0 --wds-get-current-settings --client-cid=8
#   IPv4 address: 10.x.x.x
#   IPv4 gateway: 10.x.x.x
#   IPv4 subnet mask: 255.255.255.252
#   IPv4 primary DNS: ...
#   MTU: 1430

# Configure the netdev manually
ip link set wwan0 up
ip addr add 10.x.x.x/30 dev wwan0
ip route add default via 10.x.x.x dev wwan0
echo "nameserver 8.8.8.8" > /etc/resolv.conf
```

### Equivalent in one binary — `quectel-CM`

Quectel ships a reference connection manager, `quectel-CM`, that wraps the above (~3000 lines of C, open source). Read it as a worked example of the QMI protocol.

```sh
quectel-CM -s internet
# Find modem at /dev/cdc-wdm0
# QMI Get IP Family: V4
# QMI Start Network: pdh = 0xdeadbeef
# QMI Get Settings: IP=10.x.x.x, GW=10.x.x.x, DNS1=...
# ip link set wwan0 up
# ip addr add ...
# Connected.
```

### MBIM path — `mbimcli`

```sh
mbimcli -d /dev/cdc-wdm0 --query-device-caps
mbimcli -d /dev/cdc-wdm0 --connect=apn=internet
# Successfully connected
# IPv4 address: 10.x.x.x ...
```

### PPP path — legacy 2G/3G

```sh
cat > /etc/ppp/peers/3g <<EOF
/dev/ttyUSB3
115200
defaultroute
noauth
usepeerdns
crtscts
connect 'chat -v "" AT OK ATDT*99# CONNECT'
EOF
pppd call 3g
# Serial connection established.
# Using interface ppp0
# Connect: ppp0 <--> /dev/ttyUSB3
# local  IP address 10.x.x.x
# remote IP address 10.x.x.x
```

PPP is universal (works on every modem ever made) but slow (max ~1–2 Mbps due to byte-stuffing overhead) and CPU-intensive. Only use for legacy 2G/3G fallback.

## 102.6  From scratch — a tiny AT-command client in Python

The most important debugging tool: a script that opens the AT interface and exchanges commands. This is what tells you *why* the modem isn't connecting.

`at_client.py`:

```python
#!/usr/bin/env python3
"""Minimal AT-command client for cellular modems.
Usage: ./at_client.py /dev/ttyUSB2 'AT+CSQ'
"""
import serial, sys, time

def at(port, cmd, timeout=3):
    port.write((cmd + '\r').encode())
    port.flush()
    deadline = time.time() + timeout
    resp = b''
    while time.time() < deadline:
        resp += port.read(port.in_waiting or 1)
        if b'OK\r\n' in resp or b'ERROR\r\n' in resp or b'+CME ERROR' in resp:
            break
    return resp.decode(errors='replace')

if __name__ == '__main__':
    dev, cmd = sys.argv[1], sys.argv[2]
    p = serial.Serial(dev, 115200, timeout=1)
    p.write(b'AT\r'); time.sleep(0.5); p.read(64)        # flush boot noise
    print(at(p, cmd))
```

Then:

```sh
./at_client.py /dev/ttyUSB2 'AT+CPIN?'                  # SIM status
./at_client.py /dev/ttyUSB2 'AT+CSQ'                    # signal quality (CSQ 0–31, higher = better)
./at_client.py /dev/ttyUSB2 'AT+COPS?'                  # current operator
./at_client.py /dev/ttyUSB2 'AT+QNWINFO'                # network info (Quectel ext)
./at_client.py /dev/ttyUSB2 'AT+CGDCONT=1,"IP","internet"'  # set APN
./at_client.py /dev/ttyUSB2 'AT+CGACT=1,1'              # activate PDP context 1
./at_client.py /dev/ttyUSB2 'AT+CGPADDR=1'              # show its IP
```

This is the **bring-up checklist** every time a new SIM goes into a new modem: 

1. `AT` → `OK`? Modem alive.
2. `AT+CPIN?` → `READY`? SIM unlocked.
3. `AT+CSQ` → CSQ > 10? Adequate signal.
4. `AT+COPS?` → operator name? Registered to a network.
5. `AT+CGDCONT?` → APN configured?
6. `AT+CGACT?` → PDP context active?
7. `AT+CGPADDR=1` → IP assigned?

Fail at step 1 → wiring/power. Step 2 → wrong PIN or SIM not seated. Step 3 → antenna problem or no coverage. Step 4 → wrong band/region. Step 5–6 → APN wrong. Step 7 → carrier rejected the PDP context (billing, APN typo, IP family wrong).

## 102.7  Switching modem modes

If your modem comes up as PPP-only (PID 2c7c:0123) but you want QMI, switch via AT:

```sh
# Check current mode
./at_client.py /dev/ttyUSB2 'AT+QCFG="usbnet"'
# +QCFG: "usbnet",0       (PPP+RMNET)

# Set to QMI/RMNET
./at_client.py /dev/ttyUSB2 'AT+QCFG="usbnet",0'
# OK

# Reboot the modem
./at_client.py /dev/ttyUSB2 'AT+CFUN=1,1'
# (modem reboots; lsusb shows new PID)
```

SimCom equivalents: `AT+CUSBPIDSWITCH=9011,1,1` for QMI mode.

This is persistent — the modem will boot in QMI mode forever after. **Common mistake**: customer ships a modem in PPP mode, you flash a kernel expecting QMI, nothing works. Always check `lsusb` PID first.

## 102.8  Device tree (for USB modems on i.MX6ULL)

USB modems are autobound — no DT needed beyond ensuring USB-OTG/Host is enabled.

```dts
&usbotg1 {
    dr_mode = "host";        /* not "otg" — must be fixed host */
    vbus-supply = <&reg_usb_otg1_vbus>;
    status = "okay";
};
```

The 5 V supply must source ~2.5 A during TX bursts; weak USB power = brownout = modem resets mid-connection.

## 102.9  Lab

1. **lsusb identify.** Plug in modem; `lsusb -v`; identify the mode from PID. Check `dmesg | grep -E 'option|qmi_wwan|cdc_mbim'` to see which drivers bound.
2. **AT bring-up checklist.** Run all 7 AT checks above. Fix at the failing step.
3. **Switch USB mode.** Move from default mode to QMI (if not already). Reboot. Verify new PID.
4. **ModemManager auto.** Install ModemManager; `mmcli -L`; `nmcli c add ... apn ...`; bring up; `curl ifconfig.io` to confirm public IP.
5. **Manual qmicli bring-up.** Stop ModemManager. Use `qmicli` to start the network manually. Verify `wwan0` data flows.
6. **Compare MBIM vs QMI.** Switch the modem to MBIM mode; use `mbimcli`. Note same end result, different control protocol.
7. **PPP fallback.** Force PPP mode; run `pppd`. Note throughput cap of ~1 Mbps.
8. **GPS data.** While data is up, `cat /dev/ttyUSB1` shows NMEA. Pipe to `gpsd` (Ch 107) to use as a time source.
9. **Signal degradation.** Watch `mmcli -m 0` while moving the antenna. Note RSSI/RSRP changes.
10. **Auto-failover.** Pair WiFi (Ch 91) + LTE; configure metric so WiFi wins when up; disconnect WiFi and watch LTE take over within 5 s (NetworkManager handles this with right metric config).

## 102.10  Pitfalls

- **USB power inadequate.** EC25 TX burst hits 2.5 A peaks; many i.MX6ULL boards source 1 A max. Result: random modem resets mid-transmission. Use a powered hub or a board with proper USB power design.
- **Wrong PID — wrong mode.** Modem in PPP mode but you expected QMI. Check `lsusb -v` first; switch with `AT+QCFG="usbnet"`.
- **APN typo / wrong.** Carrier-specific APNs are non-obvious (T-Mobile: `fast.t-mobile.com`; AT&T: `broadband`; Vodafone: `internet`). Wrong APN → modem registers but PDP context fails.
- **SIM not seated / locked.** `AT+CPIN?` returns `SIM PIN` → SIM needs unlock with `AT+CPIN=1234`. Returns `NOT INSERTED` → physical contact problem.
- **Wrong band on a regional SIM.** EC25-E for European bands; EC25-A for NA. Cross-using → registration fails or restricted.
- **Antenna missing / SMA loose.** Cellular antennas need a real impedance-matched antenna. A stub wire gives 20 dB worse signal — barely works in dense urban, fails in rural.
- **Multiple modems → ttyUSB renumbering.** Plug in 2 modems → ttyUSB0..7. udev rules with serial numbers are essential for predictable naming.
- **CGEV events drop the connection unnoticed.** `AT+CGEREP=2,1` enables PDP event reporting; without it, an `IPv6 routing advertisement` or `PDP DEACT` from the carrier silently kills your `wwan0` and you don't notice until the timeout.
- **qmi-firmware-update needed.** Some EC25 firmware versions have known bugs; check Quectel's release notes and use `quectel-firmware-flash` to update.
- **ModemManager fights with manual scripts.** If you call `qmicli --start-network` while ModemManager is running, the two will race each other and the connection will drop. Stop ModemManager (`systemctl stop ModemManager`) or use only the daemon.
- **Default route conflict.** With Ethernet + WiFi + wwan0, default-route metric matters. NetworkManager's default policy (Ethernet 100, WiFi 600, GSM 700) means LTE is last-resort. Override per-connection if needed.

## 102.11  Going deeper

- **Quectel EC25 User Manual + AT Commands Manual** — every modem's AT extension is non-trivial; the manual is the reference.
- **libqmi + libmbim** (`gitlab.freedesktop.org/mobile-broadband/libqmi`) — read `qmicli.c` for the full QMI protocol.
- **`quectel-CM`** (Quectel's reference QMI connection manager) — a self-contained C reference.
- **ModemManager + NetworkManager** — the modern integrated path.
- **`drivers/usb/serial/option.c`** — see how the kernel decides which interface is a serial port (the `option_ids[]` table).
- **`drivers/net/usb/qmi_wwan.c` + `cdc_mbim.c`** — the netdev wrapping the data path.
- **3GPP TS 27.007** — the standard AT command set for cellular modems.
- **Ch 103** for UART-attached (not USB) modems.
- **Ch 104** for low-power NB-IoT / Cat-M1 variants.

---

> Next chapter: **Chapter 103 — UART AT-command modems** — when you have no USB and an old PPP+chat is enough.
