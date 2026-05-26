---
chapter: 94
title: WiFi+BT combo modules (AP6212 / RTL8723BS)
part: VII — Device cookbook
estimated_pages: 16
status: draft
---

# Chapter 94 — WiFi+BT combo modules

> **What:** modules that pack WiFi *and* Bluetooth into one chip sharing one 2.4 GHz antenna: **AP6212** (Broadcom BCM43438 — WiFi over SDIO + BT over UART), **RTL8723BS** (Realtek — WiFi over SDIO + BT over UART). The defining challenges: bringing up *two* radios on *one* chip over *two* different buses, and the **coexistence** problem — both radios fighting over the same 2.4 GHz band and the same antenna.
> **Why:** most embedded products that want WiFi *also* want Bluetooth (BLE for phone-app provisioning, classic BT for audio). A combo module is cheaper and smaller than two separate chips, and it solves the coexistence problem in hardware (the chip arbitrates between its own radios). But bringing up both halves — WiFi on SDIO (Ch 91) *and* BT on UART — and getting them to coexist is more than twice the work of either alone.
> **Focus:** **one chip, two buses, two subsystems, one antenna**. The WiFi half is SDIO + brcmfmac (Ch 91). The BT half is UART + the Bluetooth HCI subsystem + `btattach`/`hciattach`. They're independent driver stacks that happen to share silicon. The coexistence (PTA — Packet Traffic Arbitration) is internal to the chip but you must enable it and wire the BT_WAKE/WL_WAKE signals.

## 94.1  Module comparison

| | AP6212 (BCM43438) | RTL8723BS | AP6256 (BCM43456) |
|---|---|---|---|
| WiFi | 802.11 b/g/n 2.4 GHz | 802.11 b/g/n 2.4 GHz | 802.11 ac 2.4/5 GHz |
| Bluetooth | BT 4.1 + BLE | BT 3.0/4.0 + BLE | BT 5.0 + BLE |
| WiFi bus | SDIO | SDIO | SDIO |
| BT bus | UART (H4/H5) | UART | UART |
| WiFi driver | `brcmfmac` (in-tree) | `rtl8723bs` (in-tree, staging-graduated) | `brcmfmac` |
| BT driver | `hci_bcm` / `btbcm` (in-tree) | `hci_uart` + `btrtl` (in-tree) | `hci_bcm` |
| Coexistence | internal PTA | internal | internal |
| Volume price | $2–4 | $2–3 | $4–6 |

**Pick guide:**
- **AP6212**: best mainline support (brcmfmac + hci_bcm both in-tree). Default for i.MX boards.
- **RTL8723BS**: cheap, `rtl8723bs` is now in-tree; BT via btrtl. Decent.
- **AP6256**: when you need 5 GHz / 802.11ac / BT 5.0.

## 94.2  Two radios, two buses

```
   ┌───────────────────────────────────────────────┐
   │              AP6212 module                     │
   │   ┌──────────┐         ┌──────────┐            │
   │   │  WiFi    │         │   BT     │            │
   │   │  (SDIO)  │         │  (UART)  │            │
   │   └────┬─────┘         └────┬─────┘            │
   │        │  ┌──────────────┐  │                  │
   │        └──┤ coexistence  ├──┘                  │
   │           │ (PTA)        │                     │
   │           └──────┬───────┘                     │
   │                  │ shared 2.4 GHz radio + antenna│
   └──────────────────┼─────────────────────────────┘
        SDIO          │  UART
        ▼             ▼
   i.MX6ULL uSDHC2   i.MX6ULL UART3
   → brcmfmac        → hci_bcm (Bluetooth HCI)
   → wlan0           → hci0
```

The two radios share the silicon and the antenna but connect to the SoC over *different* buses:
- **WiFi → SDIO** (uSDHC2) → `brcmfmac` → `wlan0`. (Exactly Ch 91.)
- **BT → UART** (UART3) → the Bluetooth HCI stack → `hci0`.

These are independent driver stacks. WiFi working doesn't mean BT works, and vice versa.

## 94.3  The WiFi half (recap of Ch 91)

Identical to Ch 91 — SDIO bring-up, pwrseq, 32 kHz clock, firmware + NVRAM, `brcmfmac`, `wlan0`. Nothing new. The combo module's WiFi is just an AP6212-WiFi as in Ch 91.

## 94.4  The BT half — Bluetooth over UART

The BT radio connects via UART, speaking the **HCI** (Host Controller Interface) protocol — the standard host↔BT-controller protocol. The UART variant is "H4" (3-wire: TX/RX/no flow) or "H5"/"3-wire" (with software flow control) or H4 with hardware RTS/CTS.

Linux's Bluetooth stack:

```
   user-space: bluetoothctl, btmgmt, BlueZ daemon
        │
        ▼
   BlueZ (the Linux Bluetooth subsystem, net/bluetooth/)
        │ HCI commands/events
        ▼
   hci_uart line discipline + hci_bcm (vendor glue)
        │ UART (H4/H5)
        ▼
   AP6212 BT controller
```

### DT for the BT half

Modern kernels use the **serdev** model (Ch 69's SerDev) to attach the BT controller to a UART:

```dts
&uart3 {
    pinctrl-names = "default";
    pinctrl-0 = <&pinctrl_uart3>;
    uart-has-rtscts;                 /* hardware flow control — important for BT */
    status = "okay";

    bluetooth {
        compatible = "brcm,bcm43438-bt";
        max-speed = <3000000>;        /* 3 Mbps after baud-rate switch */
        shutdown-gpios = <&gpio5 10 GPIO_ACTIVE_HIGH>;   /* BT_REG_ON */
        device-wakeup-gpios = <&gpio5 11 GPIO_ACTIVE_HIGH>;  /* BT_WAKE */
        host-wakeup-gpios = <&gpio5 12 GPIO_ACTIVE_HIGH>;    /* HOST_WAKE */
        clocks = <&wifi_lpo_clk>;     /* same 32 kHz LPO as WiFi */
        clock-names = "lpo";
    };
};
```

The `hci_bcm` driver binds to this node (via the `brcm,bcm43438-bt` compatible), powers the BT block (`shutdown-gpios` = BT_REG_ON), loads the BT firmware patch, switches to high baud, and registers `hci0`.

### BT firmware

Like WiFi, the BT controller needs a firmware patch (`.hcd` file for Broadcom):

```
/lib/firmware/brcm/BCM43430A1.hcd
```

`hci_bcm` loads this over HCI at init. Without it, BT works at reduced functionality (or not at all). Get it from the module vendor or linux-firmware.

### Bring-up trace

```
[root@pa-mini:~]# dmesg | grep -i blue
Bluetooth: Core ver 2.22
Bluetooth: HCI device and connection manager initialized
Bluetooth: HCI UART driver
hci_uart_bcm serial1-0: supply vbat not found, using dummy regulator
Bluetooth: hci0: BCM: chip id 94
Bluetooth: hci0: BCM43430A1
Bluetooth: hci0: BCM43430A1 'brcm/BCM43430A1.hcd' Patch
Bluetooth: hci0: BCM43430A1 (...) build 0000

[root@pa-mini:~]# hciconfig
hci0:   Type: Primary  Bus: UART
        BD Address: 43:43:A1:12:34:56  ACL MTU: 1021:8  SCO MTU: 64:1
        UP RUNNING
```

`hci0` is up. Now use BlueZ:

```
[root@pa-mini:~]# bluetoothctl
[bluetooth]# power on
[bluetooth]# scan on            ← discovers nearby devices
[bluetooth]# pair AA:BB:CC:DD:EE:FF
[bluetooth]# connect AA:BB:CC:DD:EE:FF
```

For older / non-serdev setups, you attach manually:

```
[root@pa-mini:~]# btattach -B /dev/ttymxc2 -P bcm -S 3000000
# or the legacy:
[root@pa-mini:~]# hciattach /dev/ttymxc2 bcm43xx 3000000 flow
```

But the serdev DT approach (above) is preferred — the BT comes up automatically at boot.

## 94.5  Coexistence — the shared-antenna problem

WiFi and BT both use 2.4 GHz, and the combo module has *one* antenna. If both radios transmit simultaneously, they interfere — WiFi throughput craters, BT audio stutters.

The chip solves this internally with **PTA** (Packet Traffic Arbitration, also called coexistence or "coex"): a hardware arbiter that time-slices the radio between WiFi and BT, prioritizing based on packet type (BT audio is latency-sensitive → high priority; WiFi bulk data → can wait a few ms).

For the combo module (WiFi + BT on the *same* chip), PTA is internal — both radios are on one die, the arbiter is built in, and it "just works" once both halves are up. You don't wire external coex signals.

For *separate* WiFi and BT chips (two dies), you'd wire 3-wire coex signals (BT_PRIORITY, BT_ACTIVE, WLAN_ACTIVE) between them — but combo modules avoid this by integrating.

What you *do* manage:
- **BT_WAKE / HOST_WAKE** (declared in DT) — power-management handshakes letting BT wake the host and vice versa.
- Enabling coex in firmware (usually default-on for combo modules).
- Antenna design: one antenna, one matching network, shared by both radios. The module datasheet specifies the antenna requirements.

Observable effect: run iperf3 over WiFi while streaming BT audio. Without coex, both break. With coex (combo module), WiFi throughput drops modestly (the radio is time-shared) but both function. The drop is the "cost" of coexistence — typically 10–30 % WiFi throughput reduction during active BT.

## 94.6  Bringing up both — the order

1. **WiFi first** (Ch 91): SDIO + pwrseq + 32 kHz clock + firmware + NVRAM → `wlan0`. Verify it works alone.
2. **BT second**: UART + serdev BT node + BT firmware patch → `hci0`. Verify it works alone.
3. **Shared resources**: both halves share the 32 kHz LPO clock (declare it once, reference from both pwrseq and the BT node) and often share power rails. The WL_REG_ON and BT_REG_ON are usually *separate* GPIOs — power each half independently.
4. **Coexistence test**: run both simultaneously; confirm acceptable performance.

Common mistake: getting WiFi working, declaring victory, shipping — then discovering BT was never wired up correctly. Test both, separately and together.

## 94.7  Lab

1. **WiFi half.** Bring up the AP6212 WiFi per Ch 91. Confirm `wlan0` + connect.
2. **BT half.** Add the serdev `bluetooth` node under your UART. Copy the BT firmware patch. Boot; verify `hci0` via `hciconfig`.
3. **BLE scan.** `bluetoothctl` → `scan on`. Discover nearby BLE devices (your phone, a fitness tracker).
4. **Classic BT.** Pair with a BT speaker or keyboard; verify it connects.
5. **Coexistence test.** Stream A2DP audio to a BT speaker *while* running iperf3 over WiFi. Measure WiFi throughput with and without BT active; quantify the coex cost.
6. **Shared LPO clock.** Verify both halves reference the same 32 kHz clock in DT. Remove it from one; observe that half fail.
7. **Power management.** Suspend; verify both WiFi and BT survive resume (with the wake GPIOs configured).
8. **BD address.** Note the BT controller's BD_ADDR. For production, program a unique one (from your EEPROM, Ch 65) — many modules ship with a default/duplicate address.

Commit DT + configs to `code/ch94-wifi-bt-combo/`.

## 94.8  Pitfalls

- **WiFi works, BT forgotten.** The two halves are independent. Test both. A working `wlan0` says nothing about `hci0`.
- **Missing BT firmware patch.** `hci0` comes up but with reduced functionality or wrong BD address. Copy the `.hcd` (Broadcom) or firmware (Realtek) to `/lib/firmware/brcm/` (or `/rtl_bt/`).
- **UART without hardware flow control.** BT at 3 Mbps needs RTS/CTS; without `uart-has-rtscts`, you get HCI packet corruption at high baud. Wire and enable flow control.
- **Shared 32 kHz clock declared twice / not at all.** Both halves need the LPO. Declare it once (a `fixed-clock`) and reference from both. Missing it → flaky or dead radios.
- **Baud-rate switch failure.** BT starts at 115200, then `hci_bcm` switches to 3 Mbps. If the UART or flow control can't handle the switch, BT init fails after the firmware load. Check `dmesg` for the baud-switch step.
- **Default/duplicate BD address.** Many modules ship with `43:43:A1:00:00:00` or similar. Two devices with the same BD address can't both be paired by one phone. Program a unique address at factory.
- **Coex not enabled.** On a *combo* module it's usually internal/automatic, but some firmwares need a coex-enable command. If WiFi + BT together perform terribly, check coex config.
- **Antenna shared but matched for one band.** The single antenna + matching network must work for both WiFi and BT (both 2.4 GHz, so usually fine). A poor match hurts both. Follow the module's reference antenna design.
- **BT_REG_ON vs WL_REG_ON confusion.** Separate GPIOs, separate power domains. Don't tie them together unless the module datasheet says to.

## 94.9  Going deeper

- **`drivers/bluetooth/hci_bcm.c`** — the Broadcom BT-over-UART driver (AP6212).
- **`drivers/bluetooth/btrtl.c`** + `hci_h5.c` — Realtek BT (RTL8723BS).
- **`drivers/bluetooth/hci_serdev.c`** — the serdev attachment glue.
- **`net/bluetooth/`** — the BlueZ kernel Bluetooth subsystem.
- **`drivers/net/wireless/broadcom/brcm80211/brcmfmac/`** — the WiFi half (Ch 91).
- **`Documentation/devicetree/bindings/net/broadcom-bluetooth.yaml`** — the BT DT binding.
- **AP6212 datasheet + reference schematic** — the canonical combo wiring, coex, antenna.
- **Bluetooth Core Specification (HCI section)** — the host-controller protocol.
- **`btattach` / `hciattach` man pages** — manual BT-UART attachment.

---

> **End of Group K — WiFi (Ch 91–94).** SDIO WiFi (soldered, in-tree, Ch 91), USB WiFi (swappable, watch the driver, Ch 92), hosted WiFi (ESP co-processor, Ch 93), and WiFi+BT combo (one chip, two radios, coexistence, Ch 94). Together they cover every practical way to get a 2.4 GHz radio onto an i.MX6ULL.

> Next chapter: **Chapter 95 — HCI Bluetooth over UART/USB.** Group L (Bluetooth) — the dedicated BT controllers (nRF52, BCM4343, CSR), the HCI protocol in depth, and the BlueZ stack for GATT/BLE.
