---
chapter: 95
title: HCI Bluetooth over UART/USB (nRF52 / BCM4343 / CSR8510)
part: VII - Device cookbook
estimated_pages: 22
status: draft
---

# Chapter 95: HCI Bluetooth over UART/USB

> **What:** dedicated Bluetooth controllers and the Linux Bluetooth stack (**BlueZ**). Three controllers compared: **Nordic nRF52** (with Zephyr HCI firmware, UART), **Broadcom BCM4343** (UART), **CSR8510/Realtek RTL8761** (USB dongle). We cover the **HCI protocol** in depth and the BlueZ architecture. You will not write the HCI controller, that lives in the chip's firmware. What you do build is a **BLE GATT peripheral**, in user-space, through BlueZ's D-Bus API.
>
> **Why:** Bluetooth is how embedded products talk to phones, BLE for "configure-my-device-from-an-app" provisioning, GATT for sensor data, classic BT for audio. Ch 94 brought up the combo-module BT half. This chapter goes deep on the protocol and on *building a GATT service*, the part you actually write. Understanding HCI makes the rest of the stack feel less magical. Building a GATT peripheral is the practical skill.
>
> **Focus:** the controller (chip firmware) runs the BT link layer. You build the GATT application on top. The chip's firmware is the "controller" (radio, link layer, encryption). BlueZ is the "host" (L2CAP, GATT, SMP). Your code is the "application" layer. It is a GATT server that exposes characteristics. You do not touch HCI directly. You define services, and BlueZ handles the rest. The from-scratch deliverable is a GATT peripheral, written against BlueZ's D-Bus API.
>
> **Tooling.** This chapter uses `bluez` (`bluetoothctl`, `btmon`, `btmgmt`, `hciattach`), Python `dbus` for the GATT-server example.
> - **Ubuntu-base (target):** `apt install bluez bluez-tools python3-dbus`
> - **Buildroot:** `BR2_PACKAGE_BLUEZ5_UTILS=y BR2_PACKAGE_BLUEZ5_UTILS_DEPRECATED=y BR2_PACKAGE_PYTHON3_DBUS=y`
> **Buildroot:** a configuration-driven build system that produces a complete root filesystem and related images.
> - Full per-tool reference: [Userspace tooling appendix](../part5-rootfs/appendix-tooling.md).
> **MCU bridge:** Think of the rootfs as the firmware image's file-backed runtime environment. On an MCU you link everything into flash. On Linux, programs and config live in this mounted tree.
> **rootfs:** root filesystem, the directory tree mounted at / that contains /bin, /etc, /dev, and libraries.


## 95.1  Controller comparison

| | Nordic nRF52 (Zephyr HCI) | Broadcom BCM4343 | CSR8510 / RTL8761 |
|---|---|---|---|
| Connection | UART | UART | USB |
| BT version | 5.x (nRF52840) | 4.1/4.2 | 4.0 / 5.0 (RTL8761) |
| BLE | yes (excellent) | yes | yes |
| Classic BT | nRF52: no (BLE only) | yes | yes |
| Firmware | Zephyr `hci_uart` sample | Broadcom `.hcd` patch | in dongle |
| Driver | `hci_uart` (h4/h5) | `hci_bcm` | `btusb` |
| Use case | BLE-only products | combo / classic+BLE | quick dev dongle |
| Volume price | $3–6 (module) | $2–4 | $3–8 (dongle) |

**Pick guide:**
- **nRF52840**: best BLE. Zephyr HCI firmware turns it into a clean HCI controller. BLE-only.
- **BCM4343 / AP6212-BT** (Ch 94): classic BT + BLE. Combo with WiFi.
- **CSR8510/RTL8761 USB dongle**: zero-effort dev, plug into USB, `btusb` handles it.

## 95.2  The HCI protocol

**HCI** (Host Controller Interface) is the standardised boundary between two halves of any Bluetooth system: the *host* (Linux plus BlueZ) and the *controller* (the BT chip). HCI is a packet protocol. It defines four packet types:

| Type | Direction | Purpose |
|------|-----------|---------|
| Command | host → controller | "do something" (scan, connect, set advertising data) |
| Event | controller → host | "something happened" (device found, connected, data received) |
| ACL data | both | bulk data (GATT, L2CAP payloads) |
| SCO data | both | synchronous (classic BT audio) |

A command packet:

```
   [0x01] [opcode_lo] [opcode_hi] [param_len] [params...]
    ↑ type=command
   opcode = OGF (group) << 10 | OCF (command)
   e.g., LE Set Advertising Enable = OGF 0x08, OCF 0x000A
```

An event packet:

```
   [0x04] [event_code] [param_len] [params...]
    ↑ type=event
   e.g., LE Advertising Report (a scan found a device)
```

Over UART, these packets are framed with the **H4** protocol (just the type byte prefix, no checksum, relies on UART reliability) or **H5/3-wire** (adds sequence numbers + CRC + retransmission for unreliable UARTs).

You rarely send raw HCI yourself. BlueZ does it for you. Knowing the format lets you read `btmon` traces and debug.

## 95.3  The BlueZ architecture

```
   ┌──────────────────────────────────────────────────────┐
   │  Applications                                          │
   │  bluetoothctl, your GATT server (via D-Bus), btmgmt    │
   └──────────────────────────────────────────────────────┘
        │ D-Bus (org.bluez)
        ▼
   ┌──────────────────────────────────────────────────────┐
   │  bluetoothd (the BlueZ daemon, user-space)             │
   │  - GATT, GAP, SMP (pairing), profiles (A2DP, HID, ...) │
   └──────────────────────────────────────────────────────┘
        │ HCI sockets (AF_BLUETOOTH)
        ▼
   ┌──────────────────────────────────────────────────────┐
   │  Kernel BT subsystem (net/bluetooth/)                  │
   │  - L2CAP, HCI core, socket interface                   │
   └──────────────────────────────────────────────────────┘
        │ HCI (H4/H5 over UART, or USB)
        ▼
   ┌──────────────────────────────────────────────────────┐
   │  Controller (nRF52 / BCM4343 firmware)                 │
   │  - link layer, radio, encryption                       │
   └──────────────────────────────────────────────────────┘
```

Three layers:
- **Controller** (the chip firmware): radio + link layer. You don't write this.
- **Kernel BT** (`net/bluetooth/`): HCI transport, L2CAP, sockets. You don't write this.
- **bluetoothd** (BlueZ daemon): GATT, pairing, profiles, exposed over **D-Bus**. You don't write this either.
- **Your application**: talks to bluetoothd over D-Bus to define GATT services, advertise, handle reads/writes. **This is what you build.**

## 95.4  Bringing up the controller

### nRF52 with Zephyr HCI (UART)

Flash the nRF52 with Zephyr's `hci_uart` sample (it turns the nRF52 into a pure HCI controller). Wire UART (with flow control). DT:

```dts
&uart3 {
    uart-has-rtscts;
    status = "okay";

    bluetooth {
        compatible = "zephyr,hci-uart";   /* or generic via btattach */
        max-speed = <1000000>;
    };
};
```

If no specific compatible exists, attach manually:

```
[root@pa-mini:~]# btattach -B /dev/ttymxc2 -S 1000000 -P h4
[root@pa-mini:~]# hciconfig
hci0:   Type: Primary  Bus: UART  ...  UP RUNNING
```

### BCM4343 (UART)

As Ch 94, `hci_bcm` + the `.hcd` firmware patch, serdev DT node.

### USB dongle (CSR8510 / RTL8761)

The easiest:

```
[root@pa-mini:~]# lsusb
Bus 001 Device 005: ID 0a12:0001 Cambridge Silicon Radio CSR8510 A10
[root@pa-mini:~]# dmesg | grep -i blue
Bluetooth: hci0: BCM: chip ...   (or CSR/RTL)
[root@pa-mini:~]# hciconfig hci0 up
```

`btusb` handles USB BT dongles class-compliantly, plug in, `hci0` appears.

## 95.5  bluetoothctl, the interactive tool

```
[root@pa-mini:~]# bluetoothctl
[bluetooth]# power on
[bluetooth]# scan on
[NEW] Device AA:BB:CC:DD:EE:FF MyPhone
[bluetooth]# scan off
[bluetooth]# pair AA:BB:CC:DD:EE:FF
[bluetooth]# connect AA:BB:CC:DD:EE:FF
[bluetooth]# menu gatt
[bluetooth]# list-attributes   ← shows the connected device's GATT services
```

`btmon` decodes the HCI traffic live, invaluable for debugging:

```
[root@pa-mini:~]# btmon
> HCI Event: LE Meta Event (0x3e) ...
        LE Advertising Report
          Address: AA:BB:CC:DD:EE:FF
          Data: ...
```

## 95.6  Building a BLE GATT peripheral (the from-scratch part)

The meaningful "build it yourself" deliverable: a **GATT server** that advertises a custom service and exposes characteristics a phone app can read/write/subscribe. You build this in user-space via BlueZ's D-Bus API.

GATT structure:
- A **service** (a UUID) groups related data.
- **Characteristics** (each a UUID) are the data points, readable, writable, or notifiable.
- A phone app discovers the service, reads/writes characteristics, subscribes to notifications.

Example: a temperature sensor peripheral. Service = "Environmental Sensing". Characteristic = "Temperature" (notify the phone when it changes).

Here's a minimal GATT server using Python + `dbus` (the most readable. C with GLib/sd-bus is the production path):

```python
#!/usr/bin/env python3
# A minimal BLE GATT peripheral: exposes a temperature characteristic.
import dbus, dbus.service, dbus.mainloop.glib
from gi.repository import GLib
import struct, random

BLUEZ = 'org.bluez'
GATT_SERVICE_IFACE = 'org.bluez.GattService1'
GATT_CHRC_IFACE = 'org.bluez.GattCharacteristic1'
ADV_IFACE = 'org.bluez.LEAdvertisement1'

TEMP_SVC_UUID  = '0000181a-0000-1000-8000-00805f9b34fb'   # Environmental Sensing
TEMP_CHRC_UUID = '00002a6e-0000-1000-8000-00805f9b34fb'   # Temperature

class TempCharacteristic(dbus.service.Object):
    def __init__(self, bus, index, service):
        self.path = service.path + '/char' + str(index)
        self.notifying = False
        self.value = 2300   # 23.00 °C in 0.01 units
        super().__init__(bus, self.path)
        GLib.timeout_add_seconds(2, self.update_temp)

    def get_properties(self):
        return { GATT_CHRC_IFACE: {
            'Service': self.service_path,
            'UUID': TEMP_CHRC_UUID,
            'Flags': ['read', 'notify'],
        }}

    @dbus.service.method(GATT_CHRC_IFACE, in_signature='a{sv}', out_signature='ay')
    def ReadValue(self, options):
        return [dbus.Byte(b) for b in struct.pack('<h', self.value)]

    @dbus.service.method(GATT_CHRC_IFACE)
    def StartNotify(self):
        self.notifying = True

    @dbus.service.method(GATT_CHRC_IFACE)
    def StopNotify(self):
        self.notifying = False

    def update_temp(self):
        # Simulate a reading (real: read from your BME280, Ch 67)
        self.value = 2300 + random.randint(-50, 50)
        if self.notifying:
            val = [dbus.Byte(b) for b in struct.pack('<h', self.value)]
            self.PropertiesChanged(GATT_CHRC_IFACE, {'Value': val}, [])
        return True

    @dbus.service.signal('org.freedesktop.DBus.Properties', signature='sa{sv}as')
    def PropertiesChanged(self, iface, changed, invalidated):
        pass

# ... (service registration + advertisement registration boilerplate) ...
# Register the service+characteristic with org.bluez via
# GattManager1.RegisterApplication, and an advertisement via
# LEAdvertisingManager1.RegisterAdvertisement.

if __name__ == '__main__':
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    # ... setup, register service + advertisement ...
    print("Advertising temperature service. Connect from a phone (nRF Connect app).")
    GLib.MainLoop().run()
```

The full example needs the service-object and advertisement-object registration boilerplate, about 250 lines in total. BlueZ ships `example-gatt-server` in `test/` and most production code starts from that.

What this gives you: a phone running the **nRF Connect** app (or your own app) discovers "Environmental Sensing," reads the temperature, and subscribes to notifications, getting a push every 2 seconds. This is the standard pattern: a BLE sensor talking to a phone app.

Wire the `update_temp()` to a real BME280 (Ch 67) and you have a working BLE environmental sensor.

### The C / production path

For a real product, write the GATT server in C against **sd-bus** (systemd) or **GDBus** (GLib), or use BlueZ's `gdbus` C helpers. The structure mirrors the Python: define the service + characteristics as D-Bus objects, register with `org.bluez`, handle ReadValue/WriteValue/StartNotify. More code, but no Python runtime and better performance.

## 95.7  GAP, advertising + the connection flow

Before GATT, a BLE peripheral **advertises**: it broadcasts small packets ("I exist, here's my name + service UUIDs") on the 3 advertising channels. A central (phone) scans, sees the advert, connects.

```
   Peripheral (i.MX6ULL):  advertise "TempSensor" + service UUID 0x181A
   Central (phone):        scan → sees advert → connect
   → GATT discovery → read/subscribe characteristics
```

BlueZ exposes a `LEAdvertisingManager1` D-Bus interface that controls advertising. You register an advertisement object with the name, service UUIDs, and any manufacturer-specific data. The example-gatt-server includes this.

## 95.8  Lab

1. **Bring up a controller.** nRF52 with Zephyr HCI (UART), or a USB dongle (`btusb`). Verify `hciconfig` shows `hci0 UP RUNNING`.
2. **Scan + pair.** `bluetoothctl` → scan for your phone → pair.
3. **btmon trace.** Run `btmon` during a scan. Watch the HCI LE Advertising Report events decode.
4. **GATT server.** Adapt BlueZ's `test/example-gatt-server` (or the Python above) to expose a temperature characteristic. Run it.
5. **Connect from a phone.** Install nRF Connect. Scan. Connect to your i.MX6ULL. Read the temperature. Subscribe to notifications. Watch them push every 2 s.
6. **Real sensor.** Wire `update_temp()` to a BME280 (Ch 67). Now it's a real BLE thermometer.
7. **Provisioning use case.** Add a writable "WiFi credentials" characteristic. A phone app writes SSID+password. The i.MX6ULL then joins WiFi (Ch 91). This is the canonical "configure my headless device from a phone" flow.
8. **Range + RSSI.** Move the phone away. Observe RSSI drop in `bluetoothctl`. Note BLE's ~10–30 m practical range.

## 95.9  Pitfalls

- **No hardware flow control on UART BT.** At 1–3 Mbps, BT HCI needs RTS/CTS. Without it, HCI packets corrupt → `hci0` flaky or dead. `uart-has-rtscts` + wire the lines.
- **Firmware patch missing.** BCM controllers need the `.hcd`. Without it, reduced functionality or a default BD address.
- **bluetoothd not running.** `bluetoothctl` and the D-Bus API need the `bluetoothd` daemon. `systemctl start bluetooth` (or run `bluetoothd` manually).
- **D-Bus permission denied.** Your GATT server needs permission to talk to `org.bluez`. Run as root, or add a D-Bus policy file granting access.
- **Advertising not enabled.** A GATT server with no advertisement is invisible, the phone can't find it. Register an `LEAdvertisement1` object.
- **Characteristic flags wrong.** A "read" characteristic the app tries to subscribe to fails. Match flags (`read`/`write`/`notify`) to intended use.
- **BD address duplicate.** Two devices with the same BD_ADDR confuse a phone. Program unique addresses (Ch 65 EEPROM).
- **Classic BT on a BLE-only controller.** nRF52 is BLE-only. Trying classic BT (A2DP, etc.) fails. Use a BCM/CSR for classic.
- **MTU too small.** Default BLE ATT MTU is 23 bytes (20 usable). Large characteristic values need MTU negotiation. Otherwise they're truncated. Negotiate a larger MTU.

## 95.10  Going deeper

- **`net/bluetooth/`**: the kernel Bluetooth subsystem (HCI core, L2CAP, sockets).
- **`drivers/bluetooth/`**: `hci_uart.c`, `hci_bcm.c`, `btusb.c`, `btnordic`/Zephyr-HCI support.
- **BlueZ `test/example-gatt-server`** + `example-advertisement`, adapt these for your GATT peripheral.
- **BlueZ D-Bus API docs** (`doc/gatt-api.txt`, `doc/advertising-api.txt`), the interfaces your app calls.
- **`btmon`, `btmgmt`, `bluetoothctl`**: the BlueZ tools.
- **Bluetooth Core Specification**: HCI (Vol 4 Part E), GATT (Vol 3 Part G), GAP (Vol 3 Part C).
- **Nordic nRF Connect app**: the indispensable BLE-peripheral test tool (phone-side).
- **`Documentation/devicetree/bindings/net/` (bluetooth bindings)**: the DT for UART controllers.

> Next chapter: **Chapter 96: AT-command BLE modules.** The easy path, HM-10, HC-08, BLE without a kernel stack, just UART AT commands. When simplicity beats integration.
