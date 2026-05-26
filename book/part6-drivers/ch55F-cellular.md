---
chapter: 55F
title: Cellular modems
part: VI — Driver development (supplementary v1.1)
estimated_pages: 12
status: draft
---

# Chapter 55F — Cellular modems

> **What:** integrating a 4G/LTE modem with embedded Linux. The two big paths: **USB modems** with QMI/MBIM/RNDIS data interfaces (Quectel EC20/EC25, SimCom SIM7600), and **UART AT-command modems** with PPP (older parts and NB-IoT chips). The user-space orchestrator is **ModemManager**, supplemented by `qmicli` / `mbimcli` or, for AT modems, raw chat scripts.
> **Why:** every IoT device that ships without WiFi+wired backhaul has a cellular modem. Bringing one up correctly the first time saves weeks of customer-side debugging.
> **Focus:** **picking the data mode**. EC25 alone exposes 4 USB modes (RNDIS, ECM, QMI, MBIM) — pick wrong and nothing works. QMI is the modern industry-standard for Linux; default to that unless you have a specific reason.

## 55F.1  Hardware connection

USB modems plug into a USB host port (i.MX6ULL USB OTG configured as host). They draw 1–2 A during TX bursts — your power supply must handle it. Bench testing failures are almost always power.

UART modems wire to a UART (typically 115200 baud + flow control). Plus an "enable" GPIO and a "status" GPIO.

## 55F.2  USB EC25 (QMI mode)

After plugging in, `lsusb` shows:

```
[root@pa-mini:~]# lsusb
Bus 001 Device 002: ID 2c7c:0125 Quectel Wireless Solutions Co., Ltd. EC25 LTE modem
```

The driver `qmi_wwan` handles QMI; `option` provides AT-command serial ports.

```
[root@pa-mini:~]# dmesg | tail -20
usb 1-1: New USB device found, idVendor=2c7c, idProduct=0125
qmi_wwan 1-1:1.4 wwan0: register 'qmi_wwan' at usb-...
option 1-1:1.0: GSM modem (1-port) converter detected
usb 1-1: GSM modem (1-port) converter now attached to ttyUSB0
usb 1-1: GSM modem (1-port) converter now attached to ttyUSB1
...
```

`/dev/ttyUSB0`–`/dev/ttyUSB3` are AT-command channels. `wwan0` is the data interface. `/dev/cdc-wdm0` is the QMI control channel.

## 55F.3  ModemManager — the easy path

```sh
[root@pa-mini:~]# systemctl start ModemManager
[root@pa-mini:~]# mmcli -L
    /org/freedesktop/ModemManager1/Modem/0 [Quectel] EC25

[root@pa-mini:~]# mmcli -m 0
  -------------------------
  Hardware |   manufacturer: Quectel
           |          model: EC25
           |       revision: EC25EFAR05A04M4G
  System   |         device: /sys/devices/...
  ...
  Status   |  unlock retries: sim-pin (3), sim-puk (10)
           |          state: registered
           |    power state: on
           |        signal: 75 %
```

Set up a connection:

```sh
[root@pa-mini:~]# mmcli -m 0 --simple-connect="apn=internet"
successfully connected the modem
[root@pa-mini:~]# ip link show wwan0
wwan0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc fq_codel state UP qlen 1000
[root@pa-mini:~]# dhclient wwan0
[root@pa-mini:~]# ping 8.8.8.8
```

For NetworkManager / nmcli users:

```sh
nmcli connection add type gsm con-name lte apn internet
nmcli connection up lte
```

## 55F.4  Manual QMI

If you don't want ModemManager:

```sh
# Set raw mode for the wwan0 interface
[root@pa-mini:~]# qmicli -d /dev/cdc-wdm0 --dms-set-operating-mode='online'
[root@pa-mini:~]# qmicli -d /dev/cdc-wdm0 --wda-set-data-format='raw-ip'
[root@pa-mini:~]# ip link set wwan0 down
[root@pa-mini:~]# echo Y > /sys/class/net/wwan0/qmi/raw_ip
[root@pa-mini:~]# ip link set wwan0 up

# Start data session
[root@pa-mini:~]# qmicli -d /dev/cdc-wdm0 --wds-start-network="apn='internet',ip-type=4" --client-no-release-cid
        Packet data handle: '...'
        CID: '...'

[root@pa-mini:~]# udhcpc -i wwan0
```

Manual is fragile. ModemManager is the way.

## 55F.5  UART AT-command modem (e.g., A7670C)

Wire UART TX/RX to a UART on the i.MX6ULL. Power-on sequence: assert PWRKEY GPIO for ~500 ms.

```sh
[root@pa-mini:~]# echo 1 > /sys/class/gpio/gpioN/value
[root@pa-mini:~]# sleep 0.5
[root@pa-mini:~]# echo 0 > /sys/class/gpio/gpioN/value

[root@pa-mini:~]# minicom -D /dev/ttymxc1 -b 115200
AT
OK
AT+CSQ
+CSQ: 22,99
OK
AT+CGREG?
+CGREG: 0,1
OK
```

For data: PPP via `pppd` + chat script.

`/etc/ppp/peers/a7670`:

```
/dev/ttymxc1
115200
crtscts
connect '/usr/sbin/chat -v -f /etc/ppp/chat-a7670'
defaultroute
usepeerdns
noauth
```

`/etc/ppp/chat-a7670`:

```
ABORT BUSY
ABORT 'NO CARRIER'
'' AT
OK ATD*99#
CONNECT ''
```

Then `pppd call a7670`. A `ppp0` interface appears, with internet routed through the modem.

PPP is slow (~10 Mbit/s max) and adds latency. Use only for old modems without USB.

## 55F.6  Lab

1. **Plug in an EC25.** Verify `lsusb`, `ttyUSB*`, `wwan0`, `cdc-wdm0` all appear.
2. **ModemManager connect.** `mmcli --simple-connect`; verify `ip` is up, ping works.
3. **AT-command echo.** Open `/dev/ttyUSB2`, send `AT`, get `OK`. Try `AT+CSQ`, `AT+QSPN`.
4. **SMS send.** `mmcli --modem=0 --messaging-create-sms="text='hello',number='+...'`; `--send`. (Cost: ~$0.05.)
5. **Failover to WiFi.** Write a script that periodically pings the gateway; switch routes if cellular fails.
6. **Power consumption.** Measure idle vs RX vs TX-burst current. Plan your battery accordingly.

Commit code to `code/ch55F-cellular/`.

## 55F.7  Pitfalls

- **USB power.** EC25 spikes to >1.5 A on TX bursts. 5V/2A is the minimum; less = USB resets at the worst moments.
- **Wrong USB mode.** EC25 boots in RNDIS by default in some firmware. Switch to QMI: `AT+QCFG="usbnet",0`.
- **APN wrong / missing.** Carriers reject your registration silently. Cross-check with your SIM provider.
- **Regulatory.** Some bands are illegal in some countries. Use a regional-specific modem variant.
- **Antenna SWR.** Bad antenna match = poor signal. Cellular antennas matter as much as WiFi antennas.
- **`raw_ip` mode trap.** EC25 needs `raw_ip` mode. ModemManager sets it; manual QMI must too.

## 55F.8  Going deeper

- **<https://www.freedesktop.org/wiki/Software/ModemManager/>** — ModemManager docs.
- **`libqmi` / `libmbim`** — the C libraries beneath qmicli/mbimcli.
- **`drivers/net/usb/qmi_wwan.c`** — kernel QMI driver.
- **`drivers/usb/serial/option.c`** — AT-command channel exposure.
- **3GPP TS 27.007** — AT command set standard.

> Next chapter: **Chapter 55G — Multi-touch GT911.** Touchscreens, MT-B slot protocol, calibration.
