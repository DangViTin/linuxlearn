---
chapter: 104
title: NB-IoT / Cat-M1 (Quectel BC95, BC26, SimCom SIM7080G)
part: VII — Device cookbook
estimated_pages: 14
status: draft
---

# Chapter 104 — NB-IoT / Cat-M1

> **What:** the **low-power-cellular** subset of LTE — **NB-IoT (Cat-NB1/NB2)** and **LTE-M (Cat-M1)**. Modules: **Quectel BC95-G** (NB-IoT only, ~$8), **Quectel BC26** (NB-IoT + GNSS), **SimCom SIM7080G** (NB-IoT + Cat-M1, multi-region). We cover the PHY differences from LTE Cat-1+, the PSM and eDRX features that let a 19 Ah Li-SOCl2 cell run a sensor for up to ten years, the AT command set, MQTT/CoAP profiles tailored for low data rates, and an end-to-end battery-powered sensor that hits 10 mA average over a 1-uplink-per-hour cycle.
> **Why:** standard LTE (Ch 102/103) wakes the radio, registers, transmits, idles — total energy per uplink ~5 Joules. NB-IoT/Cat-M1, with PSM, parks the radio in "deep sleep" between uplinks while keeping its network registration alive. The result: ~1 J per uplink → years of battery life. This is the technology behind smart water meters, GPS livestock trackers, vending-machine telemetry, and rural emergency call-boxes. If your product needs cellular + battery for years (not days), this is the only path.
> **Focus:** PSM is the primary power saver; eDRX is a smaller secondary saving. Use PSM correctly or your battery life estimate is wrong by orders of magnitude. The cycle is: TX, wait for the downlink ACK, then enter PSM. The radio and modem are off, but the network still considers the device registered (IP, PDP context, and security keys are kept). On the next wake — by timer or external GPIO — the device resumes immediately, with no re-registration. The 19 Ah → 10 year math depends on TX every hour at 50 bytes and PSM at <5 µA between. If the AT commands are wrong, the modem stays at 100 mA always-on. Battery life drops by a factor of 1000.

## 104.1  NB-IoT vs LTE-M vs LTE Cat-1

| | NB-IoT (Cat-NB1) | LTE-M (Cat-M1) | LTE Cat-1 |
|---|---|---|---|
| Downlink | 27 kbps | 1 Mbps | 10 Mbps |
| Uplink | 62 kbps | 1 Mbps | 5 Mbps |
| Bandwidth | 180 kHz | 1.4 MHz | 20 MHz |
| Latency | 1.6–10 s | 50–200 ms | 50 ms |
| Mobility | stationary or pedestrian | pedestrian + vehicle | full |
| Voice (VoLTE) | no | yes | yes |
| PSM (Power Save) | yes (essential) | yes | yes (rare) |
| eDRX | yes | yes | yes |
| MCL (max coupling loss) | 164 dB | 156 dB | 142 dB |
| Penetration | excellent (basements, deep indoor) | good | OK |
| Cost (per byte) | low (carrier plans optimized for IoT) | mid | high |
| Module cost | $5–10 | $10–20 | $25–40 |

**MCL (Maximum Coupling Loss)** is the critical metric: NB-IoT's 164 dB MCL means it can reach receivers 20 dB weaker than standard LTE — i.e., it penetrates concrete basements, underground meter chambers, and remote rural cells where Cat-1 has no signal.

**Pick guide:**
- **NB-IoT (BC95-G)** — your sensor sends < 1 kB/day, stationary, lives in a basement/manhole/field for 10 years. Cheapest.
- **Cat-M1 (SIM7080G)** — needs mobility (asset tracker on a truck), faster latency (alarm system), or occasional firmware update (1 MB OTA over the air in < 30 min vs hours on NB-IoT).
- **Multi-mode (SIM7080G)** — falls back to whichever the carrier supports; best for products shipped to multiple regions.

## 104.2  PSM, eDRX, and the power model

```
Normal LTE (always-on RRC connected):
  Active ──────────────────────────────────────── Active
  100 mA, 24/7 = 2.4 Ah/day → 0.3 days on a 19 Ah pack

Cat-1 with idle DRX (sleeping radio, kept-registered):
  Active ─┐    ┌───── 1 s DRX ─────┐    ┌─ Active
  10 mA   │5 mA│                    │5 mA│
  ~5 mA average → 0.12 Ah/day → 158 days

NB-IoT with PSM (deep sleep, kept-registered for hours):
  TX ─┐ idle ─┐                                    ┌─ TX
  100 mA  10 mA│         ───── PSM, 5 µA ──────    │
  5 µA average → 0.12 mAh/day → > 10 years on 19 Ah
```

The two timers:

- **T3324** — "active timer" after going idle. Modem stays idle-but-listening for T3324 (so a downlink can reach it quickly). Then enters PSM.
- **T3412** — "TAU (Tracking Area Update) timer." The modem MUST send a TAU before this expires or the network will deregister it. PSM lasts up to T3412.

Negotiation via `AT+CPSMS=1,,,"00000100","00000010"`:
- 4th arg = T3412 (granularity bits): `00000100` = 4 hours
- 5th arg = T3324: `00000010` = 4 s

Carrier-side caveat: the network may grant less than requested. Always `AT+CPSMS?` after activation to see the *granted* values.

**eDRX** (extended DRX) is an alternative for slightly less power saving but faster downlink response — the modem sleeps for up to 2.92 hours but wakes briefly to listen for paging. Use eDRX when you need occasional downlink commands; PSM when you only need uplinks + scheduled wake.

## 104.3  Bringing up NB-IoT on the BC95-G

The BC95-G presents a single UART (9600 baud default!). No USB, no PPP for data — uses an "AT-shell" data path (`AT+NSOCR` for socket-create, `AT+NSOSD` for send) which is much simpler than QMI but limited to UDP/TCP/CoAP.

```sh
# Power on (PWRKEY pulse + wait for "Neul" greeting)
gpioset gpiochip4 22=0; sleep 0.5; gpioset gpiochip4 22=1
sleep 10
cat /dev/ttymxc3 &
# Neul
# +CFUN: 1
# +CPIN: READY
# +IP: 10.x.x.x

# AT bring-up
echo 'AT' > /dev/ttymxc3
# OK
echo 'AT+NBAND=8' > /dev/ttymxc3      # band 8 (900 MHz, EU NB-IoT)
echo 'AT+CFUN=1' > /dev/ttymxc3       # full functionality
echo 'AT+CGATT=1' > /dev/ttymxc3      # attach
echo 'AT+CSCON?' > /dev/ttymxc3       # +CSCON: 0,1 (idle but registered)

# Configure PSM
echo 'AT+CPSMS=1,,,"00000110","00000010"' > /dev/ttymxc3
# 00000110 = T3412 24 hours; 00000010 = T3324 4 s
# Modem will enter PSM 4 s after data idle, wake every 24 h for TAU

# Send a UDP packet
echo 'AT+NSOCR=DGRAM,17,5683,1' > /dev/ttymxc3       # create UDP socket
# +NSOCR: 0
echo 'AT+NSOST=0,52.34.12.34,5683,5,68656C6C6F' > /dev/ttymxc3   # send "hello"
# +NSOST: 0,5

# Close + sleep
echo 'AT+NSOCL=0' > /dev/ttymxc3
# Modem auto-enters PSM 4 s later
```

The `+NSOST` command takes hex-encoded payload — verbose but simple. For larger payloads use `+NMGS` (Network Message Send) which queues a transmission for the next radio wake.

## 104.4  Cat-M1 on the SIM7080G

Cat-M1 supports IP networking like Cat-1; you can use PPP (Ch 103) or the simpler AT-socket interface. SimCom calls these `+CASOPEN`, `+CASEND`, `+CIPSEND` depending on firmware version.

```sh
# Power on, wait for "+CPIN: READY"
echo 'AT+CNMP=38' > /dev/ttymxc3       # LTE only (no GSM fallback)
echo 'AT+CMNB=2' > /dev/ttymxc3        # Cat-M1 preferred
echo 'AT+CGDCONT=1,"IP","iot.t-mobile"' > /dev/ttymxc3
echo 'AT+CNACT=0,1' > /dev/ttymxc3     # PDP context up
# +CNACT: 0,1,"10.x.x.x"

# MQTT publish (built-in MQTT client on SIM7080)
echo 'AT+SMCONF="URL","mqtt.example.com",1883' > /dev/ttymxc3
echo 'AT+SMCONN' > /dev/ttymxc3
echo 'AT+SMPUB="sensor/01",5,1,0' > /dev/ttymxc3
echo '23.45' > /dev/ttymxc3
echo 'AT+SMDISC' > /dev/ttymxc3
echo 'AT+CPSMS=1,,,"00000110","00000010"' > /dev/ttymxc3
echo 'AT+CFUN=0' > /dev/ttymxc3        # force minimum functionality → sleep
```

The built-in MQTT/CoAP clients of SIM7080/BC95 mean you don't need a TCP stack on Linux — the modem firmware does it. This is invaluable for tiny MCU products, but on Linux you can also run `mosquitto_pub` over PPP if you prefer.

## 104.5  The 10-year battery sensor — a worked example

Sensor: BME280 temperature/humidity/pressure (Ch 67) read once per hour, value sent via UDP to a cloud receiver. Hardware budget:

- 19 Ah Li-SOCl2 D-cell (Saft LSH20) — nominal 19 Ah at 3.6 V, OK to 100 mA pulse with a 47 µF tantalum across.
- BC95-G NB-IoT modem.
- STM32L0 (or i.MX6ULL in suspend) as wake controller.
- BME280 powered from a GPIO (no quiescent).

Per-cycle energy:

| Phase | Time | Current | Charge (µAs) |
|---|---|---|---|
| Wake STM32 from STOP, read BME280 | 50 ms | 5 mA | 250 |
| Wake modem from PSM | 200 ms | 80 mA | 16,000 |
| RRC reconnect + UL TX (50 bytes via UDP) | 1.5 s | 80 mA avg | 120,000 |
| Idle waiting for DL ACK | 500 ms | 30 mA | 15,000 |
| Re-enter PSM | 100 ms | 10 mA | 1,000 |
| **Total per cycle** | 2.35 s | | **~152,000 µAs = 42 µAh** |
| PSM between cycles (3600 s) | 1 hour | 5 µA | 18,000 µAs = 5 µAh |
| **Total per hour** | | | **47 µAh** |
| **Per day** | | | **1.13 mAh** |
| **Per year** | | | **413 mAh** |
| **Battery life at 19 Ah usable** | | | **~46 years** (but limited by self-discharge & temperature) |

Real-world constraints reduce this to **8–12 years**:
- LSH20 self-discharge ~1 %/year = ~190 mAh/year baseline.
- Cold-temperature operation derates capacity 30 % at –20 °C.
- Network re-registration after every TAU can cost 200+ mAh/year of extra time-on-air.

Ten years on one D-cell with no maintenance is achievable. The engineering is enforcing PSM duty cycle on every wake.

## 104.6  Lab

1. **BC95-G bring-up.** Wire UART + PWRKEY. Confirm `Neul` boot URC. Run AT bring-up checklist.
2. **Force a specific band.** `AT+NBAND=?` to list supported; pick one your carrier uses; `AT+NBAND=8`. Reboot.
3. **Send a UDP packet.** `AT+NSOCR` + `AT+NSOST`. Capture on a server with `nc -ul 5683`.
4. **PSM enable + verify.** Set T3324=4 s. Watch the modem's PWR_IND pin — should drop within 5 s of idle. Measure VBAT current; should drop to <10 µA.
5. **Measure full uplink cycle energy.** Insert a 1 Ω shunt + scope on VBAT. Capture the full TX cycle; integrate area to get charge.
6. **10-year sensor.** Implement: wake STM32 → read BME280 → wake BC95 → send UDP → re-enter PSM. Project battery life from measured energy + 1 cycle/hour.
7. **Cat-M1 with MQTT.** On a SIM7080G, configure MQTT URL, publish a sensor value, sleep. Compare cycle energy with NB-IoT (Cat-M1 is ~1.5–2× per cycle but faster latency).
8. **eDRX vs PSM.** Configure eDRX (`AT+CEDRXS=1,5,"0010"`) instead of PSM. Verify downlink latency improves (≤30 s) at cost of higher idle current.
9. **OTA firmware update over Cat-M1.** Most LTE-M modules support FOTA via AT commands. Time a 1 MB firmware update — should take ~10–30 min over Cat-M1 vs hours on NB-IoT.
10. **Carrier coverage map.** Take the device to a basement / underground / rural location where Cat-1 (Ch 102) failed. NB-IoT should still register at –135 dBm RSRP.

## 104.7  Pitfalls

- **PSM not granted by carrier.** Your `AT+CPSMS?` after registration shows `T3412 = default`. Some carriers (US Verizon) restrict PSM to certain plans. Without it, your "10 year battery" sensor is a "3 week" sensor.
- **NB-IoT not deployed by your carrier.** US carriers (Verizon, AT&T) have NB-IoT in some bands but not all; check before committing.
- **Wrong band for the region.** NB-IoT band 8 (EU 900) doesn't work in NA; need band 5/12/13 (US). Per-region SKUs avoid this.
- **PSM wakes too often for TAU.** T3412 of 24 h is the max in most networks; carriers may grant only 1 h. Recalculate battery budget accordingly.
- **Modem-side TCP timeout drops the link.** Long PSM intervals + an open TCP socket = the network's NAT entry expires. Always close sockets before sleep; reopen on wake. UDP is friendlier for this.
- **TX power higher than expected.** NB-IoT can transmit at up to +23 dBm (200 mW) for coverage extension. Battery budget collapses if you assume 100 mW. Measure real currents.
- **Voltage drop at cold temp.** Li-SOCl2 cells passivate; first pulse after a long sleep can drop to 2.7 V momentarily. Add a "wake-warmer" — a 100 ms low-current pre-pulse before the modem TX — to depassivate.
- **No coverage indicator.** Without a +CEREG event listener, your firmware doesn't know it lost the network until a TX fails. Subscribe to URCs.
- **Firmware bugs in PSM transition.** Some BC95 firmware revisions enter PSM but don't wake on the GPIO trigger. Update modem firmware before relying on PSM hardware wake.
- **Wrong APN for IoT plan.** IoT SIMs often use a separate APN (e.g., `iot.1nce.net`). Using the default consumer APN may register but fail to get an IP.

## 104.8  Going deeper

- **Quectel BC95-G AT Commands Manual** — Quectel's NB-IoT extensions (`AT+NSOCR`, `AT+NMGS`).
- **SimCom SIM7080G AT Commands Manual** — built-in MQTT/HTTP/CoAP clients.
- **3GPP TS 23.682** — the PSM and eDRX specification.
- **`drivers/net/wwan/` modern subsystem** — newer kernel WWAN drivers for some Cat-M1 modules.
- **1NCE / Hologram / Soracom** — IoT-focused carriers with NB-IoT/Cat-M1 plans and global SIMs.
- **Saft LSH20 datasheet** — the canonical 19 Ah D-cell for long-life IoT.
- **Ch 102 / Ch 103** for LTE Cat-1 baseline comparison.

---

> Next chapter: **Chapter 105 — RFID / NFC** — MFRC522 + PN532 for tag reading.
