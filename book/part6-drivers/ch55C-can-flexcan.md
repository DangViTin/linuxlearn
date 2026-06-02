---
chapter: 55C
title: CAN bus (SocketCAN + FlexCAN)
part: VI — Driver development (supplementary v1.1)
estimated_pages: 14
status: draft
---

# Chapter 55C — CAN bus (SocketCAN + FlexCAN)

> **What:** **SocketCAN** — Linux's abstraction that exposes a CAN interface as a network device (`can0`) and CAN frames as `struct sockaddr_can` / `struct can_frame` over a normal socket. The **FlexCAN** driver covers i.MX6ULL's 2 FlexCAN controllers; user-space speaks the socket API. By the end you can `cansend can0 123#DEADBEEF` and watch the frame on a scope.
>
> **Why:** CAN is the dominant bus in automotive and a strong second in industrial automation. The SocketCAN abstraction means you write CAN apps with `socket()` / `sendto()` / `recvmsg()` — same APIs as TCP/UDP. No proprietary library; tools work across all CAN hardware on Linux.
>
> **Focus:** **CAN looks like a network device.** Once `can0` is "up," everything is generic — Wireshark, tcpdump-equivalent (`candump`), `iproute2` configuration, even SO_TIMESTAMP for nanosecond-accurate receive timestamps.
>
> **Tooling.** This chapter uses `can-utils` + `iproute2` (`ip link set canX type can ...`).
> - **Ubuntu-base (target):** `apt install can-utils iproute2`
> - **Buildroot:** `BR2_PACKAGE_CAN_UTILS=y BR2_PACKAGE_IPROUTE2=y`
> - Full per-tool reference: [Userspace tooling appendix](../part5-rootfs/appendix-tooling.md).

## 55C.1  CAN basics

**CAN 2.0** is a differential, multi-master, contention-resolved bus:
- 2 wires (CAN_H, CAN_L), 60 Ω termination each end.
- 1 Mbps max (high-speed CAN).
- 11-bit (standard) or 29-bit (extended) frame identifier.
- 0–8 data bytes per frame.

**CAN-FD** (Flexible Data-rate) extends payload to 64 bytes and allows 5 Mbps data-phase. i.MX6ULL FlexCAN supports CAN-FD on the newer revisions.

Physical layer needs a *transceiver* between SoC and bus: TJA1051 (5V), TJA1463 (CAN-FD), MCP2562. The SoC speaks 3.3V TTL CAN_TX/CAN_RX; the transceiver speaks differential CAN_H/CAN_L.

## 55C.2  i.MX FlexCAN in DT

```dts
&can1 {
    pinctrl-names = "default";
    pinctrl-0 = <&pinctrl_flexcan1>;
    xceiver-supply = <&reg_can_3v3>;
    status = "okay";
};

&can2 {
    pinctrl-names = "default";
    pinctrl-0 = <&pinctrl_flexcan2>;
    status = "okay";
};
```

Once enabled, `can0` and `can1` appear:

```
[root@pa-mini:~]# ip link show | grep can
3: can0: <NOARP,ECHO> mtu 16 qdisc noop state DOWN ...
4: can1: <NOARP,ECHO> mtu 16 qdisc noop state DOWN ...
```

## 55C.3  Bringing up the interface

```
[root@pa-mini:~]# ip link set can0 type can bitrate 500000
[root@pa-mini:~]# ip link set can0 up
[root@pa-mini:~]# ip -s link show can0
3: can0: <NOARP,UP,LOWER_UP,ECHO> mtu 16 qdisc fq_codel state UP qlen 10
    link/can
    RX: bytes  packets  errors  dropped overrun mcast
    0          0        0       0       0       0
    TX: bytes  packets  errors  dropped carrier collsns
    0          0        0       0       0       0
```

Send and receive:

```
[root@pa-mini:~]# cansend can0 123#11.22.33.44       # send frame, ID 0x123
[root@pa-mini:~]# candump can0                       # passive monitor
  can0  123   [4]  11 22 33 44

# CAN-FD with bit-rate switch:
[root@pa-mini:~]# ip link set can0 type can bitrate 500000 dbitrate 2000000 fd on
[root@pa-mini:~]# cansend can0 123##1.11.22.33.44.55.66.77.88
```

## 55C.4  Programming with sockets

```c
#include <sys/socket.h>
#include <linux/can.h>
#include <linux/can/raw.h>
#include <net/if.h>

int sock = socket(PF_CAN, SOCK_RAW, CAN_RAW);

struct ifreq ifr;
strncpy(ifr.ifr_name, "can0", IFNAMSIZ);
ioctl(sock, SIOCGIFINDEX, &ifr);

struct sockaddr_can addr = {
    .can_family = AF_CAN,
    .can_ifindex = ifr.ifr_ifindex,
};
bind(sock, (struct sockaddr *)&addr, sizeof(addr));

/* Send */
struct can_frame frame = {
    .can_id  = 0x123,
    .can_dlc = 4,
    .data    = { 0x11, 0x22, 0x33, 0x44 },
};
write(sock, &frame, sizeof(frame));

/* Receive */
struct can_frame rxframe;
int n = read(sock, &rxframe, sizeof(rxframe));
printf("rx id=%x dlc=%d\n", rxframe.can_id, rxframe.can_dlc);
```

For filtering — only receive frames with specific IDs:

```c
struct can_filter rfilter[2];
rfilter[0].can_id   = 0x123;
rfilter[0].can_mask = CAN_SFF_MASK;
rfilter[1].can_id   = 0x200;
rfilter[1].can_mask = 0x700;     /* match 0x200–0x2FF */
setsockopt(sock, SOL_CAN_RAW, CAN_RAW_FILTER, &rfilter, sizeof(rfilter));
```

The kernel filters in software, or in hardware where the controller supports it. FlexCAN has message-buffer (MB) filtering. High-throughput receivers should always set filters. Otherwise, every frame on the bus is delivered to every socket.

## 55C.5  Higher protocols

CAN-RAW is the bottom layer. Real applications use one of:

- **ISO-TP** (ISO-15765-2) — fragmentation/reassembly for >8-byte payloads. `linux/can/isotp.h`. Used by OBD-II and UDS automotive diagnostics.
- **J1939** — heavy-duty truck/agricultural protocol. `linux/can/j1939.h`.
- **CAN BCM** (Broadcast Manager) — kernel-side periodic frame TX/RX with filtering. Reduces user-space wakeups.

```c
/* ISO-TP socket */
int sock = socket(PF_CAN, SOCK_DGRAM, CAN_ISOTP);
struct sockaddr_can addr = {
    .can_family = AF_CAN,
    .can_ifindex = ifr.ifr_ifindex,
    .can_addr.tp = { .tx_id = 0x7E0, .rx_id = 0x7E8 },
};
bind(sock, (struct sockaddr *)&addr, sizeof(addr));
write(sock, "Hello, this is an ISO-TP message longer than 8 bytes", 53);
```

## 55C.6  Error frames and bus health

CAN reports "bus-off" when error count exceeds 255. SocketCAN exposes these as special error frames with `can_id` flag `CAN_ERR_FLAG`. Enable:

```c
can_err_mask_t err_mask = CAN_ERR_TX_TIMEOUT | CAN_ERR_LOSTARB | CAN_ERR_CRTL | CAN_ERR_PROT | CAN_ERR_TRX | CAN_ERR_BUSOFF;
setsockopt(sock, SOL_CAN_RAW, CAN_RAW_ERR_FILTER, &err_mask, sizeof(err_mask));
```

When the bus goes bus-off, restart it:

```sh
ip link set can0 type can restart-ms 100      # auto-restart 100 ms after bus-off
```

Or do it manually with `ip link set can0 down; ip link set can0 up;` after sorting the wiring/termination.

## 55C.7  Lab

1. **Bring up FlexCAN1.** DT, bitrate 500 kbit, `ip link set can0 up`.
2. **Loop two nodes.** Connect can0 on i.MX6ULL to a USB-CAN adapter on a host PC, terminated with 60 Ω each end. Send frames with `cansend` from one side, watch `candump` on the other.
3. **Throughput test.** `cangen can0 -g 0 -I 0x123 -L 8` floods at maximum rate. `canbusload can0 500000` reports utilization.
4. **Filter receive.** Set up two sockets with different filters; verify each receives only matching frames.
5. **ISO-TP echo.** Write a small ISO-TP server that replies with what it received; client sends 50-byte payloads.
6. **Bus-off recovery.** Disconnect transceiver during transmission; observe bus-off error frame; verify `restart-ms` auto-recovers.

## 55C.8  Pitfalls

- **Missing/wrong terminations.** Without 120 Ω termination at each end of the bus (60 Ω total), signal integrity collapses. For a single-node bench setup, put one 120 Ω resistor across CAN_H/CAN_L. Robustness is lower but it works.
- **Wrong bitrate on one end.** Symptom: all frames error. Both sides must agree.
- **CAN_TX/RX swapped at transceiver.** Symptom: no transmit. Verify schematic.
- **No transceiver supply.** Many transceivers need their own VCC; without it, no signaling.
- **Bus-off and no restart-ms.** Bus stuck off after first error storm. Set `restart-ms`.
- **Different CAN-FD speeds.** Old nodes can't handle CAN-FD speed-shift frames; bus collapses. Use CAN-FD only on segments where all nodes support it.

## 55C.9  Going deeper

- **`Documentation/networking/can.rst`** — SocketCAN documentation.
- **`drivers/net/can/flexcan.c`** — i.MX FlexCAN driver.
- **`can-utils`** — `cansend`, `candump`, `cangen`, `canbusload`, `isotpdump`. Required.
- **`linux/can/isotp.h`**, **`linux/can/j1939.h`** — higher-protocol headers.
- **OpenXC** project — open-source automotive data over CAN.

> Next chapter: **Chapter 55D — Block device drivers.** The other half of "storage" — `gendisk`, request queues, blk-mq.
