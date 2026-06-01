---
chapter: 109
title: LIN bus (TJA1020, TJA1027, MCP2003B)
part: VII — Device cookbook
estimated_pages: 12
status: draft
---

# Chapter 109 — LIN bus

> **What:** **LIN (Local Interconnect Network)** — a single-wire, master/slave serial bus used in cars for low-cost peripherals where CAN is overkill (door modules, seat motors, mirror controls, HVAC fans, rain sensors, parking sensors). Three transceivers: **NXP TJA1020** (legacy 12 V), **TJA1027** (3.3/5 V LIN 2.x), **Microchip MCP2003B** (similar). On Linux there is no native LIN subsystem, so we drive it from a UART with custom break + parity handling, build a master node and a slave responder in C, and demonstrate talking to a real automotive LIN node (HVAC blower controller from a junkyard).
> **Why:** if you're integrating with automotive systems — retrofit modules, OBD diagnostic tools, custom dashboards, EV conversion kits — you'll meet LIN. Cars use 100+ LIN slaves; CAN buses delegate "is the user pressing the seat-heat button" to a LIN sub-bus underneath. LIN is also spreading into industrial actuator buses (HVAC valves, building blinds). At about $0.40 per node and one wire, it is the cheapest option for simple peripherals. Linux has no native LIN subsystem; you write the framing yourself. This is also a useful UART exercise.
> **Focus:** A LIN frame is: a UART start, a 'break' pulse, an 0x55 sync byte, a 6-bit Protected Identifier (PID) byte, one to eight data bytes, and a checksum byte. A single master schedules every frame. Slaves never transmit on their own. The break signal (≥13 dominant bits = ~1.4 ms low at 9600 LIN-baud) is *not* a normal UART feature — you either generate it with `tcsendbreak()` or by toggling baud rate momentarily. The protocol is simple. The trap is getting the timing right on a non-deterministic Linux UART.

## 109.1  LIN at a glance vs CAN, RS-485

| | LIN | CAN | RS-485 |
|---|---|---|---|
| Wires | 1 + GND | 2 (differential) + GND | 2 (differential) + GND |
| Speed | 1–20 kbps | 125 kbps – 1 Mbps (CAN-FD: 5+ Mbps) | up to 10 Mbps |
| Topology | bus, 1 master + 1–15 slaves | bus, multi-master | bus, multidrop |
| Arbitration | master-scheduled (no arbitration) | CSMA/CR | master-scheduled |
| Cost / node | $0.40 transceiver | $1–2 transceiver | $0.80 transceiver |
| Use cases | comfort, body (windows, mirrors, HVAC) | powertrain, safety | industrial sensors, energy meters |
| Standard | ISO 17987 / LIN 2.x | ISO 11898 | TIA-485 |
| OS support on Linux | none native | `SocketCAN` (great) | `serial` + `libmodbus` |

LIN's design philosophy: **deterministic schedule, no contention, cheap silicon**. The master polls each slave on a fixed schedule (e.g., poll temp sensor every 1 s, poll door switch every 100 ms). No collision, no priorities, no extra hardware.

## 109.2  LIN frame format

```
   Master generates HEADER:
      [Break field] [Sync byte=0x55] [PID byte]
        ≥13 dom bits   0x55           ID + 2 parity bits

   Slave (or master) responds with RESPONSE:
      [Data 1] [Data 2] ... [Data N] [Checksum]
        1–8 bytes               classic or enhanced CRC
```

PID byte (Protected Identifier):
```
   bit 7  6  5  4  3  2  1  0
       P1 P0 ID5 ID4 ID3 ID2 ID1 ID0
   P0 = ID0 ⊕ ID1 ⊕ ID2 ⊕ ID4
   P1 = !(ID1 ⊕ ID3 ⊕ ID4 ⊕ ID5)
```

The 6-bit ID is 0..63. Some IDs are reserved (0x3C, 0x3D = master/slave request frames; 0x3E, 0x3F = reserved).

Checksum:
- **Classic** (LIN 1.x): sum of data bytes only.
- **Enhanced** (LIN 2.x): sum of PID + data bytes. The same byte position has different semantics depending on which version the bus runs.

## 109.3  Wiring

```
       ┌────────┐                              ┌───────────┐
i.MX  ─┤ TXD    ├──────────────────────────────┤ TXD       │
UART4  │ RXD    ├──────────────────────────────┤ RXD       │  TJA1027 (3.3 V LIN transceiver)
GPIO  ─┤ EN     ├──────────────────────────────┤ EN        │  (sleep control)
       │        │   3.3 V  ── 100 nF ────────  ┤ VIO       │
       │        │   12 V   ── 220 µF ────────  ┤ VBAT      │  ← car battery
       │        │   GND ────────────────────── ┤ GND       │
       │        │                              ┌ LIN       │  ← LIN bus wire (single)
       │        │                              │            │  to other slaves
       │        │                              │   1 kΩ     │
       │        │                              │   pull-up  │
       │        │                              │   to VBAT  │  (master only)
       │        │                              └───         │
       └────────┘                              └───────────┘
```

The LIN bus is a single wire pulled up to 12 V (typically 7–18 V in practice). Each node pulls the wire low to transmit. Idle = recessive = 12 V; dominant = ~0 V. The master provides a 1 kΩ pull-up (slaves use 30 kΩ pull-up). The TJA1027 handles the level translation between the 12 V LIN domain and the 3.3 V UART domain.

## 109.4  Generating a LIN break + frame from a UART

The break field is the trick: 13+ consecutive dominant (low) bits at LIN baud. UART hardware can't natively emit that without one of these tricks:

### Trick 1 — `tcsendbreak()`

```c
tcsendbreak(uart_fd, 0);    /* 0 = at least 250 ms in POSIX; on Linux ~250 ms */
```

But 250 ms is way too long for a 20 kbps LIN bus. Linux Documentation/serial states the value is implementation-specific. The i.MX UART driver, by default, gives the minimum break (~13 bits at the current baud), which is exactly what we want — but you must verify with a scope.

### Trick 2 — baud-rate switch

Temporarily switch the UART to half-baud, send 0x00, switch back. At half baud, the 9 bit-times of 0x00's start+8data = 18 bit-times at full baud — exceeds the 13-bit minimum.

```c
struct termios t;
tcgetattr(fd, &t);
cfsetspeed(&t, B4800);                   /* 9600 / 2 */
tcsetattr(fd, TCSANOW, &t);
write(fd, "\0", 1);
tcdrain(fd);
cfsetspeed(&t, B9600);
tcsetattr(fd, TCSANOW, &t);
```

### Trick 3 — bit-bang with GPIO

For the most reliable timing, switch the TX pin to GPIO momentarily, pulse it low for the calculated time, switch back. Reliable but messy.

### Trick 4 — i.MX UART SEND_BREAK bit

The i.MX UART has a `SENDBRK` bit in UCR1 that asserts continuous TX while set. From user space, `ioctl(fd, TIOCSBRK)` then `usleep(1400)` then `ioctl(fd, TIOCCBRK)` gives a ~1.4 ms break at the line's baud — perfect for 9600 LIN.

## 109.5  From scratch — LIN master in C

lin_master.c:

```c
/* Minimal LIN 2.x master. Sends headers; reads slave responses.
 * Tested against an HVAC blower controller from a 2018 VW (LIN slave at ID 0x10).
 */
#include <fcntl.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <termios.h>
#include <unistd.h>
#include <sys/ioctl.h>

static int fd;

static uint8_t pid(uint8_t id) {
    uint8_t p0 = ((id >> 0) ^ (id >> 1) ^ (id >> 2) ^ (id >> 4)) & 1;
    uint8_t p1 = (~((id >> 1) ^ (id >> 3) ^ (id >> 4) ^ (id >> 5))) & 1;
    return (p1 << 7) | (p0 << 6) | (id & 0x3F);
}

static uint8_t cksum_enhanced(uint8_t pid_byte, const uint8_t *data, int n) {
    uint16_t s = pid_byte;
    for (int i = 0; i < n; i++) s += data[i];
    while (s > 0xFF) s = (s & 0xFF) + (s >> 8);
    return (uint8_t)(~s);
}

static void send_break(void) {
    /* i.MX-specific: assert TX low for 1.4 ms (>13 LIN bits at 9600) */
    ioctl(fd, TIOCSBRK, 0);
    usleep(1500);
    ioctl(fd, TIOCCBRK, 0);
    usleep(50);                         /* inter-byte gap before sync */
}

static void send_header(uint8_t id) {
    send_break();
    uint8_t sync = 0x55;
    write(fd, &sync, 1);
    uint8_t p = pid(id);
    write(fd, &p, 1);
    tcdrain(fd);
}

/* Master sending response (master broadcasting to slaves) */
static void send_response(uint8_t id, const uint8_t *data, int n) {
    send_header(id);
    write(fd, data, n);
    uint8_t c = cksum_enhanced(pid(id), data, n);
    write(fd, &c, 1);
    tcdrain(fd);
}

/* Master polling a slave (header only; slave fills the response) */
static int poll_slave(uint8_t id, uint8_t *out, int expected_len, int timeout_ms) {
    send_header(id);
    /* Now read what the slave sent + its checksum */
    int total = expected_len + 1;
    int got = 0;
    while (got < total && timeout_ms > 0) {
        int n = read(fd, &out[got], total - got);
        if (n > 0) got += n;
        else { usleep(1000); timeout_ms--; }
    }
    if (got < total) return -1;
    uint8_t c = cksum_enhanced(pid(id), out, expected_len);
    if (c != out[expected_len]) return -2;
    return expected_len;
}

int main(void) {
    fd = open("/dev/ttymxc3", O_RDWR | O_NOCTTY);
    struct termios t = {0};
    tcgetattr(fd, &t);
    cfsetspeed(&t, B9600);
    cfmakeraw(&t);
    t.c_cflag |= CLOCAL | CREAD;
    tcsetattr(fd, TCSANOW, &t);

    /* Send command frame: ID 0x20, "fan speed = 100" */
    uint8_t cmd[2] = { 100, 0 };
    send_response(0x20, cmd, 2);

    /* Poll status frame: ID 0x10, expecting 2-byte response */
    uint8_t buf[16];
    int n = poll_slave(0x10, buf, 2, 30);
    if (n > 0)
        printf("Slave responded: %02X %02X (status=0x%02X temp=%d)\n",
               buf[0], buf[1], buf[0], buf[1]);

    return 0;
}
```

That's a working LIN 2.x master in ~80 lines. To run a periodic schedule (poll ID 0x10 every 100 ms, broadcast control on 0x20 every 500 ms), add a scheduler loop.

## 109.6  LIN slave on the i.MX6ULL

The i.MX6ULL is overkill as a LIN slave (the typical slave is a Cypress PSoC or a $0.30 8-bit MCU), but for prototyping or aggregating multiple sensors onto one bus it's useful.

```c
/* Wait for break (UART detects framing error on receive). */
for (;;) {
    uint8_t b;
    int n = read(fd, &b, 1);
    /* Check for break via ioctl TIOCMIWAIT(TIOCM_BRK) or via TIOCGICOUNT */
    /* On break: read sync byte, PID, decide if we own this ID */
    uint8_t sync, p;
    read(fd, &sync, 1);
    if (sync != 0x55) continue;
    read(fd, &p, 1);
    uint8_t id = p & 0x3F;
    if (id == OUR_RESPONSE_ID) {
        /* We're publisher for this ID — send our 2-byte status + checksum */
        uint8_t data[2] = { sensor_status(), sensor_temp() };
        uint8_t c = cksum_enhanced(p, data, 2);
        write(fd, data, 2);
        write(fd, &c, 1);
    }
    /* Else: master broadcast we may want to subscribe to — capture data */
}
```

Detecting the break from user-space is hard on Linux; there is no dedicated API. Practical patterns:
- Look for a UART framing error followed by 0x00 byte (the break appears as 0x00 with a framing error flag).
- Poll `ioctl(fd, TIOCGICOUNT, &counts)` for `brk++` since last call.

Both methods work but neither is clean. For real products, run the LIN slave on a dedicated MCU.

## 109.7  LIN sleep + wake

LIN supports a deep sleep mode for low-power automotive ECUs:

- **Sleep command**: master sends ID 0x3C with data `[0x00, 0xFF×7]`. All slaves enter sleep.
- **Wake**: any node pulls the bus low for ≥250 µs. All nodes wake up.

The TJA1027 has an EN pin — when low, the transceiver itself is off (drawing ~10 µA from VBAT). Master pulls EN low; slaves are still on the bus but the bus is idle. To wake: master pulls EN high, then drives the wake pulse.

This is how a car can leave 50+ LIN slaves on a bus that drains 100 µA quiescent.

## 109.8  Talking to a real automotive LIN slave

Junkyard a VW/Audi HVAC blower controller (~$15). Pinout:
- 12 V power
- GND
- LIN

Pull-up 1 kΩ from LIN to 12 V (you're the master). Wire to your TJA1027. The blower controller's slave ID for "set fan speed" is typically `0x20`. The exact ID is vendor-specific; you find it by capturing bus traffic and matching commands to behaviour.

Send: ID 0x20, data `[speed_0..255, 0x00, 0x00, ..., 0x00]` (8 bytes total for VW). The fan should spin proportional to speed.

At this point you have driven an automotive comfort actuator from Linux. The same pattern works for door-lock modules, mirror-fold motors, sunroof tilt — all LIN slaves.

## 109.9  Lab

1. **Scope the break.** Wire TJA1027 + a scope on the LIN line. Trigger `send_break()`; verify the low pulse is 1.4 ms (13.5 bits at 9600). Tune until correct.
2. **Send a header.** Confirm sync byte is 0x55 (10 bit-times after the break). PID byte for ID 0x10 should be 0x50.
3. **Loopback test.** Connect two transceivers on the same LIN bus. Master sends a frame; slave (second board running the recv loop) prints what it received.
4. **Checksum classic vs enhanced.** Compare both implementations against a known correct frame from a LIN bus log.
5. **Multi-slave schedule.** Run a 100 ms scheduler polling 3 slave IDs in sequence. Verify each slave only responds to its own ID.
6. **Wake/sleep.** Implement the sleep command. Confirm slaves stop responding. Issue wake pulse (drive bus low 1 ms); verify slaves come back.
7. **Real-car interface.** Wire to an actual automotive LIN slave (junkyard module); reverse-engineer the protocol by sending common IDs and watching for responses. Many slaves respond to ID 0x3D (slave-info request) with their NAD (Network Address) + supplier ID.
8. **Logging.** Capture all bus traffic to a file with timestamps; build a simple LIN-trace viewer in Python.
9. **Compare with LIN-USB analyser.** Hook up a commercial analyser (PEAK PLIN-USB, Microchip MCP2003-EVB-LIN); confirm your master generates identical frames.

## 109.10  Pitfalls

- **Break too short or too long.** <13 bits → slave doesn't see it as break, treats as data → garbage frame. >50 bits → slave times out and ignores the rest.
- **No pull-up on bus.** Bus floats; nobody reads anything coherent. The master is responsible for the 1 kΩ pull-up.
- **Master powered from 3.3 V but bus needs 12 V.** TJA1027 needs VBAT 7–18 V on the BAT pin (not the 3.3 V VIO). Without it, the transceiver doesn't drive.
- **Mixed checksum types.** LIN 1.x checksum = sum of data only; LIN 2.x = sum of PID + data. A LIN 1.x slave on a 2.x bus rejects every frame because the checksum doesn't include the PID.
- **PID parity wrong.** Easy to invert the parity bits. Compute and verify with a known-good table.
- **Linux UART read latency.** When polling a slave, the master sends header then must read 1–9 bytes within 50 ms or so. A loaded Linux box may delay the read; the response is buffered but you miss the timing window for the next frame. Use higher process priority or RT scheduling.
- **TIOCSBRK on some UART drivers is too long.** Always scope-verify the break length.
- **Multiple masters.** LIN has exactly one master. Two masters on one bus is undefined; their schedules collide.
- **Bus-off via short.** A shorted-to-ground LIN line (a chafed wire in a car loom) puts the bus permanently dominant; no comms possible. Detection: the master's read-back of its own sync byte is 0x00. Recover by raising EN to put the transceiver in low-power mode.
- **Different car manufacturers use slightly different sleep timings.** VW's "wake-up pulse must be ≥250 µs" vs BMW's "≥150 µs vs full break"; follow the slave datasheet.

## 109.11  Going deeper

- **ISO 17987 — LIN specification** (all 7 parts).
- **LIN consortium** specification archives (LIN 1.3 / 2.0 / 2.1 / 2.2A).
- **NXP TJA1027 datasheet + application note** — the standard 3.3 V LIN transceiver.
- **`drivers/tty/serial/imx.c`** — see how the i.MX UART implements TIOCSBRK / TIOCCBRK.
- **Microchip MCP2003 + MCP2004 application notes** — alternative transceivers + reference designs.
- **`lin-bus.org` forum + GitHub** — community LIN code and dumps.
- **Ch 108 (RS-485)** — the industrial cousin; Ch 110 (CAN) — the heavyweight cousin.
- **Vector CANoe / LIN.SimulationKit** — commercial tools (expensive); great for reverse-engineering automotive LIN systems if you have access.

---

> Next chapter: **Chapter 110 — CAN deep dive** — CAN-FD, ISO-TP, SocketCAN advanced, MCP2515.
