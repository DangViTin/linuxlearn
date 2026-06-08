---
chapter: 110
title: CAN deep dive (TJA1051, TJA1463 CAN-FD, MCP2515 SPI, ISO-TP, J1939)
part: VII — Device cookbook
estimated_pages: 18
status: draft
---

# Chapter 110 — CAN deep dive

> **What:** the deep follow-up to Ch 55C's FlexCAN intro. We compare CAN transceivers — **NXP TJA1051** (5 V classic CAN), **TJA1463** (CAN-FD with fast bit timing), **Microchip MCP2562** (5 V or 3.3 V flexible), plus the **MCP2515** SPI-CAN-controller for adding CAN to a board with no spare FlexCAN. We dig into the **CAN-FD** frame format and why arbitration vs data phase have different baud rates, **ISO-TP (ISO-15765-2)** for multi-frame transport (the basis of OBD-II / UDS diagnostics), **SocketCAN** advanced features (BCM = Broadcast Manager, J1939 daemon, CAN-XL preview), and an end-to-end **OBD-II diagnostic tool** that reads engine RPM, coolant temp, and DTCs from a real car.
>
> **Why:** CAN is everywhere — every car since 2008 (US OBD-II mandate), most industrial automation, every drone autopilot, half the modern medical devices, every BLDC servo. Mainline Linux's SocketCAN is the most complete CAN stack of any general-purpose OS: every interface looks like a network device, packets are skbs, you read/write via `sendto`/`recvfrom` on a `PF_CAN` socket. After this chapter you can take on most vehicle and industrial CAN integration work.
>
> **Focus:** Classic CAN is a bit-stuffed differential bus with priority arbitration via CSMA/CR. CAN-FD adds a second, faster bit rate during the data phase. The result: 64 bytes through a 1 Mbps arbitration bus in about 120 µs. The kernel handles bit-timing, error recovery, bus-off detection. The hard parts you write: ISO-TP segmentation for messages >8 bytes (every diagnostic command is one), filters to subset thousands of frames/second down to what your app cares about, and BCM cyclic-broadcast for periodic frames (heart-beats, control loops). Get the bit timing right (sample point, SJW, prop and phase segments). Otherwise you will see CAN bus errors that look like a wiring fault but are caused by configuration.
>
> **Tooling.** This chapter uses `can-utils` (full suite), `libsocketcan`, optional `python-can`.
> - **Ubuntu-base (target):** `apt install can-utils libsocketcan-dev python3-can`
> - **Buildroot:** `BR2_PACKAGE_CAN_UTILS=y BR2_PACKAGE_LIBSOCKETCAN=y BR2_PACKAGE_PYTHON3_PYTHON_CAN=y`
> **Buildroot** - a configuration-driven build system that produces a complete root filesystem and related images.
> - Full per-tool reference: [Userspace tooling appendix](../part5-rootfs/appendix-tooling.md).
> MCU bridge: Think of the rootfs as the firmware image's file-backed runtime environment. On an MCU you link everything into flash. On Linux, programs and config live in this mounted tree.
> **rootfs** - root filesystem, the directory tree mounted at / that contains /bin, /etc, /dev, and libraries.


## 110.1  Transceiver and controller comparison

| | TJA1051 | TJA1463 | MCP2562 | MCP2515 (with TJA1051) |
|---|---|---|---|---|
| Type | transceiver | transceiver | transceiver | **standalone controller + transceiver** |
| Speed | 1 Mbps (classic) | 5 Mbps (CAN-FD data phase) | 1 Mbps | 1 Mbps |
| CAN-FD | no | yes | no | no |
| Supply | 5 V | 5 V (3.3 V opt) | 5 V or 3.3 V | 5 V controller, 3.3 V SPI |
| Need on-SoC controller | yes (FlexCAN) | yes (FlexCAN with FD) | yes | no — SPI from host |
| Use case | basic CAN | modern auto + CAN-FD | flexible designs | adding CAN to a board with no FlexCAN |
| Cost | $0.80 | $1.50 | $1.00 | $4 (MCP2515) + $0.80 (TJA1051) |

**Pick guide:**
- **TJA1051** + i.MX6ULL FlexCAN — default for classic CAN at ≤ 1 Mbps.
- **TJA1463** — when the bus uses CAN-FD (modern cars, new industrial designs).
- **MCP2515 SPI controller** — when both i.MX6ULL FlexCAN1 + FlexCAN2 are used and you need a third CAN bus.

## 110.2  Classic CAN frame (refresher)

```
   SOF | Arbitration (ID + RTR) | Control | Data | CRC | ACK | EOF
   1 bit  11 or 29 bits + 1     6 bits   0–64b  16b   2b   7b
```

- **Arbitration**: lower ID wins. loser backs off. winner continues uninterrupted. This is **CSMA/CR** (collision resolution, not avoidance).
- Dominant is logical 0 (actively driven). Recessive is logical 1 (idle). Dominant always overwrites recessive, so the lowest-numbered ID wins arbitration.
- **Bit-stuffing**: 5 consecutive identical bits → insert opposite bit. Receiver removes it. Adds ~20 % overhead.
- **CRC15**: protects the frame.
- **ACK slot**: a single bit. receivers pull it dominant if they got the frame. Lack of ACK = error.

CAN-FD extends this:
- Optional second bit rate (5+ Mbps) during data phase.
- Data length up to 64 bytes (vs 8).
- 17- or 21-bit CRC.
- Bus-load math: classic CAN at 500 kbps = ~5500 frames/s. CAN-FD at 500 kbps arb / 5 Mbps data = ~9000 of-up-to-64-byte frames/s = ~10× the throughput.

## 110.3  Bit timing — the hidden trap

Each CAN bit is divided into segments:

```
   |─ Sync ─|─ Prop ─|─ Phase1 ─|─ Phase2 ─|
       1       1–8     1–8        2–8         (TQ = Time Quanta)
                                  ↑
                              sample point (typ. 75–87.5 %)
```

The clock = `CAN_clk = SoC_clk / (prescaler × TQ)`. For 500 kbps on a 33 MHz CAN clock:
- 33 MHz / 500 kbps = 66 TQ per bit → too many.
- Use prescaler 4: 33 / 4 = 8.25 MHz → 8.25 / 0.5 = 16.5 → round to 16 TQ per bit.
- Then split 16 TQ: 1 Sync + 7 Prop + 4 Phase1 + 4 Phase2 → sample at (1+7+4)/16 = 75 %.

DT for FlexCAN:

```dts
&can1 {
    pinctrl-names = "default";
    pinctrl-0 = <&pinctrl_can1>;
    xceiver-supply = <&reg_can_xcvr>;
    status = "okay";
};
```

The kernel SocketCAN handles bit-timing computation automatically when you set:

```sh
ip link set can0 type can bitrate 500000 sample-point 0.875
ip link set can0 up
```

For CAN-FD:

```sh
ip link set can0 type can bitrate 500000 dbitrate 2000000 fd on
ip link set can0 up
```

Verify the actual programmed timing:

```sh
ip -d link show can0
# 6: can0: <NOARP,UP,LOWER_UP,ECHO> mtu 16 ...
#   can state ERROR-ACTIVE (berr-counter tx 0 rx 0) restart-ms 0
#   bitrate 500000 sample-point 0.875 ...
```

A wrong sample point + long bus = sporadic errors that look intermittent. Set sample-point explicitly when troubleshooting.

## 110.4  Bringing up CAN with SocketCAN

```sh
modprobe flexcan       # for FlexCAN
modprobe can-raw
modprobe can-bcm
modprobe can-isotp     # for ISO-TP

ip link set can0 type can bitrate 500000
ip link set can0 up

ip link show can0      # state ERROR-ACTIVE = up + healthy

# Dump
candump can0
# can0  123   [8]  DE AD BE EF 00 01 02 03

# Send
cansend can0 123#DEADBEEF00010203

# Generate test traffic
cangen can0 -g 10
```

`can-utils` is the SocketCAN swiss army knife:
- `candump` — sniff
- `cansend` — send one frame
- `cangen` — generate
- `canplayer` — replay a log
- `cansniffer` — diff display (highlight changed bytes)
- `cangw` — kernel CAN-to-CAN gateway with filters
- `isotpsend` / `isotprecv` — multi-frame ISO-TP

## 110.5  Filters — surviving high-rate buses

A car CAN bus at 500 kbps carries 1500+ frames/s. Reading every frame on a Cortex-A7 is fine, but processing every one wastes CPU. **Filters** in the kernel drop unwanted frames before they hit user-space.

```c
int s = socket(PF_CAN, SOCK_RAW, CAN_RAW);
struct sockaddr_can addr = { .can_family = AF_CAN };
struct ifreq ifr; strcpy(ifr.ifr_name, "can0"); ioctl(s, SIOCGIFINDEX, &ifr);
addr.can_ifindex = ifr.ifr_ifindex;
bind(s, (struct sockaddr*)&addr, sizeof addr);

/* Filter: accept only IDs 0x7E0..0x7EF (OBD-II range) */
struct can_filter filt[] = {
    { .can_id = 0x7E0, .can_mask = 0x7F0 },     /* match 0x7Ex */
};
setsockopt(s, SOL_CAN_RAW, CAN_RAW_FILTER, &filt, sizeof filt);

struct can_frame frame;
while (read(s, &frame, sizeof frame) > 0) {
    printf("ID=%X DLC=%d data[0]=%02X\n",
           frame.can_id, frame.can_dlc, frame.data[0]);
}
```

The kernel applies the filter. user-space only sees matching frames. Critical for performance.

## 110.6  ISO-TP (ISO-15765-2)

CAN frames carry 8 bytes (64 for FD). diagnostic messages are often 30+ bytes. ISO-TP fragments them.

Three frame types:
- **SF (Single Frame)** — payload ≤ 7 bytes, sent in one CAN frame.
- **FF (First Frame)** — payload > 7 bytes, contains total length + first 6 bytes.
- **CF (Consecutive Frame)** — subsequent fragments with a 4-bit sequence number.
- **FC (Flow Control)** — receiver tells sender block size + separation time.

The kernel `can-isotp` module exposes this as a SOCK_DGRAM:

```c
int s = socket(PF_CAN, SOCK_DGRAM, CAN_ISOTP);
struct sockaddr_can addr = { .can_family = AF_CAN };
addr.can_ifindex = ifr.ifr_ifindex;
addr.can_addr.tp.tx_id = 0x7E0;     /* ECM request ID */
addr.can_addr.tp.rx_id = 0x7E8;     /* ECM response ID */
bind(s, ...);

/* Send a UDS read-DID command */
uint8_t cmd[] = { 0x22, 0xF1, 0x90 };       /* Read DID: VIN */
send(s, cmd, sizeof cmd, 0);

uint8_t resp[256];
int n = recv(s, resp, sizeof resp, 0);
/* resp[0] = 0x62 (positive response); resp[1..2] = 0xF1 0x90; resp[3..19] = VIN */
```

That's a 19-byte response (positive response + DID + 17-byte VIN) auto-fragmented and reassembled by the kernel. Without ISO-TP, you'd be writing the segmentation state machine yourself.

## 110.7  J1939 — heavy-duty truck protocol

J1939 layers on CAN with 29-bit IDs encoding source + destination + parameter group number (PGN). Used in trucks, agricultural machinery, marine engines.

```sh
modprobe can-j1939
ip link set can0 type can bitrate 250000
ip link set can0 up

# Talk to source address 0x80, listen for SPN-based messages
# j1939_set_address(s, 0x80)
# ... j1939-utils provides example sender/receiver
```

J1939's PGN dictionary lists thousands of standardized parameters (engine RPM, fuel consumption, brake pressure, …). For agricultural/marine integrations, this is standard.

## 110.8  BCM — Broadcast Manager for periodic frames

Need to send a frame every 20 ms for a control loop? BCM does it in kernel:

```c
int s = socket(PF_CAN, SOCK_DGRAM, CAN_BCM);
connect(s, (struct sockaddr*)&addr, sizeof addr);

struct {
    struct bcm_msg_head head;
    struct can_frame frame;
} msg = {0};
msg.head.opcode = TX_SETUP;
msg.head.flags = SETTIMER | STARTTIMER;
msg.head.can_id = 0x123;
msg.head.nframes = 1;
msg.head.ival2.tv_sec = 0;
msg.head.ival2.tv_usec = 20000;        /* 20 ms cycle */
msg.frame.can_id = 0x123;
msg.frame.can_dlc = 8;
memcpy(msg.frame.data, "HEARTBT!", 8);
send(s, &msg, sizeof msg, 0);
```

Now the kernel emits this frame every 20 ms forever. user-space process can sleep. Useful for safety heartbeats, periodic control updates, slow telemetry.

## 110.9  MCP2515 — adding CAN to a board with no FlexCAN

> **Privilege boundary:** $ means normal user. # or sudo means root and can change host or target state.
> After a privileged command, verify the expected device, service, or file appears before continuing. Roll back by undoing the config change or stopping the service you just enabled.


If you've used both i.MX6ULL FlexCANs and need a third bus, the MCP2515 is the standard SPI add-on. Kernel driver `drivers/net/can/spi/mcp251x.c`.

DT:

```dts
&ecspi3 {
    cs-gpios = <&gpio4 26 GPIO_ACTIVE_LOW>;
    status = "okay";

    can@0 {
        compatible = "microchip,mcp2515";
        reg = <0>;
        spi-max-frequency = <10000000>;
        clocks = <&clk16m>;             /* 16 MHz crystal */
        interrupts-extended = <&gpio4 27 IRQ_TYPE_LEVEL_LOW>;
    };
};

clk16m: clk16m {
    compatible = "fixed-clock";
    #clock-cells = <0>;
    clock-frequency = <16000000>;
};
```

After `modprobe mcp251x` you get `can1`, identical SocketCAN semantics to FlexCAN. Throughput limited by SPI: 10 MHz SPI handles 500 kbps CAN cleanly. Struggles near 1 Mbps under load.

## 110.10  OBD-II — talking to a real car

Plug an OBD-II to DB9 adapter into the car's port (under the dashboard). connect to your i.MX6ULL's CAN1. bitrate 500 kbps.

```c
int s = socket(PF_CAN, SOCK_DGRAM, CAN_ISOTP);
struct sockaddr_can addr = { .can_family = AF_CAN };
addr.can_ifindex = if_nametoindex("can0");
addr.can_addr.tp.tx_id = 0x7DF;      /* OBD-II functional request */
addr.can_addr.tp.rx_id = 0x7E8;      /* ECU response (engine) */
bind(s, ...);

/* Mode 01 PID 0C: engine RPM */
uint8_t req[] = { 0x01, 0x0C };
send(s, req, sizeof req, 0);

uint8_t resp[8];
recv(s, resp, sizeof resp, 0);
/* resp[0]=0x41 mode echo, resp[1]=0x0C PID, resp[2]+resp[3] = RPM*4 */
int rpm = ((resp[2] << 8) | resp[3]) / 4;
printf("RPM: %d\n", rpm);
```

OBD-II mode/PID list:
- 01 0C → engine RPM
- 01 0D → vehicle speed
- 01 05 → coolant temp
- 01 0F → intake air temp
- 01 11 → throttle position
- 03 → diagnostic trouble codes (DTCs)
- 04 → clear DTCs
- 09 02 → VIN

About 200 lines of C and a Linux board are enough to build a complete OBD-II dashboard.

## 110.11  Lab

1. **Two boards, one bus.** Wire two TJA1051 transceivers on a 1 m twisted pair with 120 Ω termination. Both run SocketCAN at 500 kbps. `cangen` from one, `candump` on the other.
2. **CAN-FD.** If you have TJA1463: enable CAN-FD. set dbitrate 2 Mbps. `cangen -L 64` for full-size frames. Compare throughput vs classic CAN.
3. **Filter performance.** On a bus with `cangen -g 0.5 can0` running, install a tight filter. Verify CPU load drops dramatically.
4. **ISO-TP loopback.** Two boards: one acts as ECU (request_id=0x7E0, response_id=0x7E8). The other sends UDS Read-DID. Verify multi-frame messages assemble correctly.
5. **BCM cyclic.** Set up a 100 Hz heartbeat via BCM. Watch with `candump -t a` and verify the cycle time stays within ±200 µs.
6. **MCP2515 third bus.** If your board has spare SPI: wire MCP2515. bring up `can1`. verify it works concurrently with FlexCAN's can0.
7. **OBD-II real car (capstone).** Get an OBD-II cable. Connect to a car (ignition on). Read RPM, coolant temp, speed at 10 Hz. Plot in real-time.
8. **DTC reading.** Send mode 03. parse DTC codes. map to human-readable (e.g., P0420 = "catalyst efficiency"). Even on a healthy car you'll usually get a few "pending" codes.
9. **Gateway with cangw.** `cangw -A -s can0 -d can1 -e -m SET:CI:7E8:0x12345678` — forward all received frames from can0 to can1 with a different ID. Useful for bridging two networks.
10. **Bus-off recovery.** Short the CAN_H and CAN_L (carefully — your transceiver should survive). The controller goes bus-off. Configure `restart-ms 100` so it auto-recovers when the short clears.

## 110.12  Pitfalls

- **Wrong sample point.** A 75 % sample on a 50 m bus may sample inside the prop-delay. bumping to 87.5 % cures "random errors." Always set explicit sample-point on long buses.
- **No termination.** Bus reflections cause CRC errors at higher speeds. 1 Mbps unterminated barely works at 1 m, breaks at 5 m.
- **Termination too close together.** 120 Ω at both physical ends. not "120 Ω near the master + 120 Ω in the middle."
- **Mixing CAN and CAN-FD nodes.** Classic-only nodes see the FD flag bit as a form error and fault. Either all nodes do CAN-FD or none do (some modern transceivers tolerate FD frames as "noise" but not standardized).
- **MCP2515 silicon errata.** Some revs have known SPI-glitch bugs at high SPI clocks. cap at 5 MHz on errata silicon.
- **Bit-stuffing eats throughput.** Effective bandwidth on classic CAN is 60–80 % of nominal due to stuffing + acks + interframe space.
- **ID 0 is highest priority.** A node that always sends ID 0 starves everyone else. Reserve low IDs for hard-real-time critical messages only.
- **No ACK on a single-node bus.** A node alone on the bus sends a frame. no other node ACKs. The transmitter errors and retries forever. Bus-off after ~256 errors. To debug solo: add a `cangen --rx-ack` simulator, or loopback.
- **`flexcan` driver vs CONFIG_CAN_CALC_BITTIMING.** Without CAN_CALC_BITTIMING in your kernel config, you must specify all timing parameters explicitly. Newer kernels enable it by default.
- **ISO-TP block size = 0 (no flow control).** Some ECUs send STmin and BS=0 (means "send everything as fast as you can"). Your transmit loop may overwhelm slower receivers. The receiver's flow control says BS=1 — respect it.
- **J1939 source address claims.** Multi-master J1939 requires arbitration of source addresses at startup. out-of-the-box examples may skip this and you get address conflicts on a real bus.
- **CAN_RAW_LOOPBACK on by default.** Sent frames are echoed back to your own socket. This surprises people writing CAN code for the first time.

## 110.13  Going deeper

- **ISO 11898-1/2 (classic CAN), ISO 11898-1:2015 (CAN-FD)** — physical and data link layers.
- **ISO 15765-2 (ISO-TP)** — multi-frame transport for diagnostics.
- **ISO 14229 (UDS)** — Unified Diagnostic Services. The application protocol over ISO-TP.
- **SAE J1939** — heavy-duty truck protocol.
- **SAE J1979** — OBD-II legislated emissions PIDs.
- **`drivers/net/can/`** in the kernel. especially `flexcan.c`, `mcp251x.c`, `mcp251xfd.c` (CAN-FD).
- **`net/can/`** for SOCK_RAW, SOCK_DGRAM CAN_BCM, CAN_ISOTP, CAN_J1939.
- **`can-utils`** — the canonical user-space toolkit.
- **`python-can`** — Python bindings to SocketCAN. great for prototyping.
- **`SavvyCAN`** — open-source CAN analyzer with reverse-engineering tools.
- **Hardware: Peak PCAN, Kvaser, Vector** — reference-grade USB-CAN analyzers when you need certainty.

---

> Next chapter: **Chapter 111 — Quadrature encoders & rotary** — Group R (Motors & encoders) starts here.
