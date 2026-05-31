---
chapter: 107
title: GPS / GNSS + PPS time synchronization (u-blox NEO-6M/8M/9M, ATGM336H)
part: VII — Device cookbook
estimated_pages: 14
status: draft
---

# Chapter 107 — GPS / GNSS + PPS

> **What:** **GNSS receivers** (GPS + GLONASS + BeiDou + Galileo) and the **PPS (Pulse-Per-Second)** time-discipline signal. We compare **u-blox NEO-6M** (legacy, GPS-only), **NEO-8M** (multi-constellation), **NEO-9M** (concurrent multi-band, lower power, GNSS RAW data), and the cheap **ATGM336H** (BeiDou+GPS+GLONASS). On Linux, we parse **NMEA-0183**, decode u-blox's binary **UBX** protocol, bring up **gpsd** as the central daemon, and wire the **PPS GPIO** to **chrony** for sub-microsecond NTP — turning a $5 receiver into a **stratum-1 time server**.
> **Why:** GPS receivers do two things, both critical for embedded products:
> 1. **Position** for asset tracking, geo-fencing, fleet management, anti-theft.
> 2. **Time** — GPS atomic-clock-derived time, sub-µs precise, traceable to UTC. Telco basestations, financial exchanges, distributed databases (Spanner, CockroachDB), and any time-sensitive logging system uses GPS-disciplined clocks. A $5 chip + $20 antenna = stratum-1 NTP, no internet required.
>
> The technique generalizes — *any* time-domain measurement on Linux (audio sync between two boards, distributed scientific instruments, oscilloscope-on-IP) gets much easier with a real PPS time source.
> **Focus:** **NMEA gives you the wall-clock seconds but is laggy and jittery (~50–500 ms after the second); PPS is the actual nanosecond-accurate edge**. A naïve "set the clock from `$GPRMC`" gets you to ±100 ms. PPS-disciplined (kernel timestamps the GPIO edge with hardware-clock precision; chrony combines the slow-but-labelled NMEA with the fast-but-unlabelled PPS edge) gets you to ±100 ns. Understanding the PPS plumbing — pin → kernel `pps_gpio` driver → /dev/pps0 → chrony's refclock — is what separates "GPS time sync" from "real GPS time sync."

## 107.1  GNSS module comparison

| | u-blox NEO-6M | NEO-8M | NEO-9M | ATGM336H |
|---|---|---|---|---|
| Year | 2011 | 2014 | 2019 | 2017 |
| Constellations | GPS | GPS + GLONASS + Galileo + BeiDou + QZSS | concurrent dual-band L1/L5 | BeiDou + GPS + GLONASS |
| Channels | 50 | 72 | 184 | 33 |
| Position accuracy | ~2.5 m CEP | ~2.0 m | ~1.5 m (multi-band 0.5 m) | ~2.5 m |
| Cold-start time | ~27 s | ~26 s | ~24 s | ~32 s |
| Hot-start time | < 1 s | < 1 s | < 2 s | ~1 s |
| Sensitivity (acq) | –148 dBm | –148 dBm | –148 dBm | –148 dBm |
| Current (acq) | 67 mA | 67 mA | ~35 mA | 30 mA |
| Current (tracking) | 50 mA | 50 mA | 25 mA | 25 mA |
| PPS output | yes | yes | yes | yes |
| PPS jitter | ~30 ns | ~30 ns | ~20 ns | ~50 ns |
| UART default | 9600 8N1 | 9600 8N1 | 38400 8N1 | 9600 8N1 |
| Native protocol | NMEA + UBX | NMEA + UBX | NMEA + UBX + RAW measurements | NMEA only |
| Cost (module + antenna) | $8–15 | $10–18 | $40–60 | $5–8 |

**Pick guide:**
- **NEO-8M** — workhorse for most projects. Multi-constellation = better urban coverage, faster TTFF (time to first fix). Well-documented + UBX binary.
- **NEO-9M** — when you need < 1 m accuracy, RAW pseudorange data (RTK-able with a base station), or lowest power.
- **ATGM336H** — when BOM matters more than UBX support. Cheap, NMEA-only.

## 107.2  NMEA-0183 — the universal text protocol

NMEA is a 1980s-era ASCII protocol designed for marine instruments. Every GNSS receiver speaks it. Sentences look like:

```
$GPRMC,123519.00,A,4807.038,N,01131.000,E,022.4,084.4,230394,003.1,W*6A
       ↑           ↑↑           ↑           ↑     ↑     ↑          ↑
       UTC time   lat (DDMM.mmm)lon         spd  hdg   date       magvar
                  fix valid                 knots deg  ddmmyy
```

| Sentence | Content |
|---|---|
| `$GPRMC` | recommended minimum: time, lat/lon, speed, heading, date |
| `$GPGGA` | fix data with altitude, # satellites, HDOP |
| `$GPGSA` | active satellites + DOPs (PDOP, HDOP, VDOP) |
| `$GPGSV` | satellites in view (multiple sentences if > 4) |
| `$GPVTG` | velocity over ground |
| `$GPGLL` | lat/lon only |
| `$GNRMC` etc. | `GN` prefix = multi-constellation fix |

The checksum is XOR of all bytes between `$` and `*`, in hex. Parsers should always verify it; corrupt UART bytes (no flow control on most modules) flip bits silently.

NMEA's three weaknesses for time sync:
1. **Latent**: sentence is generated some time *after* the second; transmission at 9600 baud takes ~70 ms.
2. **Inconsistent**: different modules emit GPRMC at different points in the second.
3. **Verbose**: parsing ASCII costs CPU you don't need.

Hence PPS for sub-second timing.

## 107.3  UBX — u-blox binary protocol

u-blox's native protocol is binary and **labels each message with the exact GPS time the position is valid for**. Frame:

```
   [µB] [class] [id] [len_lo] [len_hi] [payload...] [ck_a] [ck_b]
    0xB5 0x62
```

Classes:
- `0x01` NAV (navigation results — POSLLH, VELNED, PVT, STATUS)
- `0x02` RXM (raw measurements — RAWX for RTK)
- `0x05` ACK (ack/nack from CFG operations)
- `0x06` CFG (configuration — port baud, message rates, GNSS selection)
- `0x0A` MON (monitor — HW status, jamming, RF antenna)

The killer message: `UBX-NAV-PVT` (Position, Velocity, Time — class 0x01, id 0x07, 92 bytes). One frame per fix, contains the iTOW (integer time of week, ms), year/month/day/hour/min/sec, lat/lon/h, velocity, accuracy estimates, fix type, # satellites. Replaces 5+ NMEA sentences.

The setup command to enable NAV-PVT at 1 Hz only:

```
B5 62 06 01 08 00 01 07 00 01 00 00 00 00 18 E1
       ↑ CFG-MSG       ↑ NAV-PVT, rate=1 on UART
```

Switching to UBX-only at startup reduces UART traffic 5× and gives you nanosecond-precise per-message timing. The `u-center` Windows tool (or `ubxtool` in Linux's `gpsd` package) is invaluable for crafting these.

## 107.4  PPS — the sub-microsecond signal

The PPS pin pulses high for ~100 ms exactly on the UTC second boundary. The receiver synchronizes its 1 kHz timepulse generator to its GNSS-derived clock; jitter is ~20–50 ns.

```
   GNSS receiver
      │  TX (NMEA / UBX) ────────► /dev/ttymxc3
      │  PPS              ────────► GPIO5_3 → kernel pps_gpio driver → /dev/pps0
      └─────────────────────────► chrony combines them
```

Linux kernel side: `drivers/pps/`. The `pps_gpio` driver registers an IRQ on the GPIO, and on each edge records a hardware timestamp (`ktime_get_ts()`) plus the GPIO event time. User-space (chrony) reads `/dev/pps0` ioctl-style to get the latest edge timestamp and computes the offset between GPIO-edge-time and system-clock-time.

DT binding:

```dts
pps {
    compatible = "pps-gpio";
    gpios = <&gpio5 3 GPIO_ACTIVE_HIGH>;
    assert-falling-edge;       /* or omit for rising-edge */
    pinctrl-names = "default";
    pinctrl-0 = <&pinctrl_pps>;
};
```

After `dmesg | grep pps`:

```
pps_core: LinuxPPS API ver. 1 registered
pps_core: Software ver. 5.3.6 - Copyright 2005-2007 Rodolfo Giometti
pps pps0: new PPS source pps.-1
pps pps0: Registered IRQ 67 as PPS source
```

`/dev/pps0` exists. The tool to dump edges:

```sh
ppstest /dev/pps0
# trying PPS source "/dev/pps0"
# source 0 - assert 1709236745.000001234, sequence: 1234
# source 0 - assert 1709236746.000001456, sequence: 1235
```

Each pulse's timestamp is captured with `getnstimeofday()` precision — typically sub-microsecond on a Cortex-A7 with hardware IRQ.

## 107.5  gpsd — the central daemon

gpsd opens the GPS receiver UART, parses NMEA/UBX, and exposes the parsed fix via a JSON socket protocol on `localhost:2947`. Applications (your code, chrony, navit, foxtrotgps, qmapshack) talk to gpsd, not the receiver directly.

```sh
apt install gpsd gpsd-clients

# /etc/default/gpsd
DEVICES="/dev/ttymxc3 /dev/pps0"
GPSD_OPTIONS="-n"               # don't wait for client; always read

systemctl restart gpsd

# Inspect live fix
gpsmon
# Or in JSON
gpspipe -w
#  {"class":"TPV","time":"2026-05-31T12:34:56.000Z","lat":52.3,"lon":13.4,...}

# Status check
cgps -s
```

For Python:

```python
import gps
session = gps.gps(mode=gps.WATCH_ENABLE)
for report in session:
    if report['class'] == 'TPV':
        print(report.lat, report.lon, report.time)
```

## 107.6  Chrony + PPS — the stratum-1 NTP server

Once gpsd is up and `/dev/pps0` is alive, chrony combines NMEA (gives the second number) + PPS (gives the precise edge) to discipline the system clock.

```sh
apt install chrony

# /etc/chrony/chrony.conf — append:
refclock SHM 0 refid GPS poll 4 noselect    # gpsd's SHM segment (low precision, just for the second)
refclock PPS /dev/pps0 refid PPS lock GPS prefer trust   # PPS (high precision)

systemctl restart chrony

# Verify
chronyc sources -v
# MS Name/IP address  Stratum Poll Reach LastRx Last sample
# #? GPS                     0    4   377    13   -45ms[  -45ms] +/-  100ms
# #* PPS                     0    4   377    14   -100ns[ -100ns] +/-   200ns
```

The `*` next to PPS means it's the chosen reference; the offset is < 200 ns. The system clock is now disciplined to GPS time at sub-microsecond accuracy. `date +%N.%9N` shows nanosecond-precise time.

To serve NTP to your LAN:

```sh
# chrony.conf
allow 192.168.0.0/24

# Now other Linux/Windows boxes can ntpd-sync from this i.MX6ULL
# On a client:
chronyc sources
# ^* mygpsbox.local              1   6   377    25    +12µs[  +15µs] +/-  410µs
```

You just built a stratum-1 NTP server with $20 of parts.

## 107.7  From scratch — UBX parser in C

Use NMEA for debugging, UBX for production. The skeleton parser:

```c
/* ubx_parse.c — fragment */
struct ubx_nav_pvt {
    uint32_t iTOW;
    uint16_t year;
    uint8_t  month, day, hour, min, sec;
    uint8_t  valid;
    uint32_t tAcc;
    int32_t  nano;
    uint8_t  fixType;
    /* ... lat, lon, height, vel, etc ... */
};

static int read_ubx_frame(int fd, uint8_t *cls, uint8_t *id,
                          uint8_t *payload, int *plen) {
    uint8_t buf;
    /* Wait for 0xB5 0x62 */
    do { if (read(fd, &buf, 1) != 1) return -1; } while (buf != 0xB5);
    read(fd, &buf, 1);
    if (buf != 0x62) return -2;
    read(fd, cls, 1);
    read(fd, id, 1);
    uint8_t len_lo, len_hi;
    read(fd, &len_lo, 1); read(fd, &len_hi, 1);
    int len = len_lo | (len_hi << 8);
    if (len > 200) return -3;
    for (int i = 0; i < len; ) {
        int n = read(fd, &payload[i], len - i);
        if (n <= 0) return -4;
        i += n;
    }
    /* Read + verify Fletcher checksum */
    uint8_t ck_a = 0, ck_b = 0;
    ck_a += *cls; ck_b += ck_a;
    ck_a += *id;  ck_b += ck_a;
    ck_a += len_lo; ck_b += ck_a;
    ck_a += len_hi; ck_b += ck_a;
    for (int i = 0; i < len; i++) { ck_a += payload[i]; ck_b += ck_a; }
    uint8_t rx_a, rx_b;
    read(fd, &rx_a, 1); read(fd, &rx_b, 1);
    if (ck_a != rx_a || ck_b != rx_b) return -5;
    *plen = len;
    return 0;
}

int main(void) {
    int fd = open("/dev/ttymxc3", O_RDWR | O_NOCTTY);
    /* configure 38400 8N1 ... */
    for (;;) {
        uint8_t cls, id, payload[200]; int len;
        if (read_ubx_frame(fd, &cls, &id, payload, &len) == 0
            && cls == 0x01 && id == 0x07) {
            struct ubx_nav_pvt *p = (void *)payload;
            printf("%04d-%02d-%02dT%02d:%02d:%02d.%09d  fix=%d\n",
                   p->year, p->month, p->day, p->hour, p->min, p->sec,
                   p->nano, p->fixType);
        }
    }
}
```

Run this; you'll see each fix printed with the exact GPS-derived UTC time it was valid for. Compare with the PPS-disciplined system clock to verify they agree.

## 107.8  Lab

1. **Antenna + first fix.** Wire the module's UART; place the antenna with sky view. Launch `cat /dev/ttymxc3`; watch NMEA stream; wait for `$GPGGA` with non-zero "fix quality" — TTFF should be < 60 s outdoors.
2. **gpsd up.** Configure gpsd; run `cgps -s` to see live position. Indoors near a window may work for u-blox; ATGM336H usually won't.
3. **PPS wired.** Add the DT pps-gpio node; reboot; verify `/dev/pps0`; run `ppstest /dev/pps0`. Each pulse should print one second later.
4. **chrony stratum-1.** Configure refclock SHM+PPS; restart chrony; `chronyc sources` should show PPS selected. `date +%N.%9N` should show stable sub-µs precision.
5. **UBX binary mode.** Use `ubxtool -p MON-VER` to verify u-blox; then `ubxtool -e UBX -d NMEA` to disable NMEA + enable UBX. Verify with `ubxtool -p NAV-PVT`.
6. **NTP client benchmark.** From another Linux box, `chronyc -h <gpsbox> sources` should show your box at stratum 1, offset < 1 µs.
7. **Cold-start time.** Power-cycle the module; measure TTFF outdoors vs indoors-by-window. Multi-constellation modules should win.
8. **PPS jitter measurement.** Capture 1000 PPS edges; histogram the timestamp delta from 1.000000000 s. Should show ±20–50 ns.
9. **Geofencing.** Write a script that alerts when the lat/lon leaves a circle (haversine distance > 100 m). Useful for asset-theft alerts.
10. **TPS6594 + GPS for outage survival.** If your product is a stratum-1 server, hooking a UPS so the clock survives mains outages buys you 24+ hours of holdover (the OCXO inside drifts, but GPS resyncs as soon as power is back).

## 107.9  Pitfalls

- **Antenna missing or shielded.** GPS needs sky view. An indoor desk position usually fails. Use a roof or window-mount antenna with a coax extension.
- **No PPS GPIO.** Some "GPS modules" omit the PPS pin or it's not bonded out. Verify before buying.
- **PPS GPIO not configured.** Without the DT `pps-gpio` node, `/dev/pps0` doesn't appear. `modprobe pps_gpio` only works if the platform driver instantiated it from DT.
- **PPS polarity wrong.** Rising-edge vs falling-edge — check the module datasheet. Wrong polarity → chrony sees no edges.
- **NMEA-only refclock = poor accuracy.** Without PPS, system clock accuracy is ~30 ms (NMEA latency). Insist on PPS for sub-µs.
- **Baud rate too low for UBX-NAV-PVT at 10 Hz.** At 9600, the 92-byte NAV-PVT plus other UBX leaves no headroom for 10 Hz updates. Switch to 38400 or 115200.
- **NMEA checksum bytes flipped.** No flow control + heavy bus traffic = bit flips. Always verify the checksum and discard bad sentences.
- **Multi-constellation overrides single-constellation in NMEA.** GNRMC, GNGGA replace GPRMC, GPGGA. Parsers must accept both prefixes.
- **u-blox jamming detection.** The MON-RF message reports interference; if jamming is detected (drone show, military jammer, RF leak), the module may report no fix. Don't blame the antenna without checking MON-RF.
- **GNSS time vs UTC leap seconds.** GPS time is leap-second-free; UTC isn't. Old or unprogrammed modules may emit times off by 18 s after a leap second. Use the `LeapSeconds` field if exposed.
- **TPS regulator + GPS together = noise.** Switching regulators inject noise on the GPS antenna's RF input. Use an LDO close to the antenna, or shield the regulator.

## 107.10  Going deeper

- **u-blox NEO-8M / NEO-9M Protocol Specification** — the canonical UBX reference (1500+ pages).
- **`gpsd` documentation** — covers many receivers, JSON protocol, refclock SHM mechanism.
- **`chrony` documentation** — refclock PPS, GPS, SHM integration.
- **`drivers/pps/`** + `Documentation/pps/pps.rst` — kernel side.
- **NMEA-0183** standard (proprietary; many free summaries online).
- **NTPv4 + IEEE 1588 PTP** — for sub-µs over Ethernet (after you have a local stratum-1).
- **RTKLIB** — for RTK centimetre-accurate positioning using u-blox RAW data.
- **Ch 51B** — for using PPS to wake a sleeping device every second.

---

> Next chapter: **Chapter 108 — RS-485 + Modbus RTU** — beginning Group Q (Industrial buses).
