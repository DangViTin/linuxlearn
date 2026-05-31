---
chapter: 52
title: Network driver (FEC + KSZ8081)
part: VI — Driver development
estimated_pages: 20
status: draft
---

# Chapter 52 — Network driver: FEC + KSZ8081

> **What:** the i.MX6ULL's **FEC** (Fast Ethernet Controller) and the **KSZ8081** RMII PHY that nearly every Point Atom board uses. The kernel's network-device framework (`netdev`), the PHY library (`phylib`), MDIO bus operations, RMII vs MII timing — the full anatomy of "Linux has eth0 working."
> **Why:** Ethernet is the most-debugged peripheral on any embedded board. Wrong PHY ID, wrong RMII clock direction, wrong delay-line settings — and you spend a week wondering why your `ping` drops every fifth packet. The mainline `fec_main.c` + `phylib` + `kszphy.c` stack is mature; understanding what it expects from DT and how to verify timing turns a one-week bug-hunt into a one-hour bring-up.
> **Focus:** **the FEC ↔ PHY ↔ Linux pipeline**. The FEC is the MAC (Media Access Controller). The PHY is the SerDes that turns digital frames into wire signals. The MDIO bus is the management interface between them. Linux's `netdev` exposes the result as `eth0`. Get the four layers right and packets flow.

## 52.1  The pipeline

```
              wire (CAT5e)
                  │
       ┌─────────────────────┐
       │   RJ45 magnetics    │
       └─────────────────────┘
                  │  4 differential pairs
       ┌─────────────────────┐
       │   KSZ8081 PHY        │  ← 10/100 Mbps, RMII to MAC, MDIO management
       │   - autoneg          │
       │   - link detect      │
       └─────────────────────┘
                  │  RMII data (2 pairs of pins + REF_CLK + CRS_DV)
                  │  MDIO/MDC (2 pins management)
       ┌─────────────────────┐
       │   FEC1 (i.MX6ULL)    │  ← The MAC; speaks RMII
       │   - DMA              │
       │   - Tx/Rx queues     │
       └─────────────────────┘
                  │  AXI / DMA → DDR
       ┌─────────────────────┐
       │   Linux: fec_main.c  │  ← netdev driver
       │   phylib             │  ← talks to KSZ8081 via MDIO
       └─────────────────────┘
                  │
                  ▼
       Linux: eth0 (network stack)
```

i.MX6ULL has **two FEC instances**, FEC1 and FEC2. Some boards wire both (giving dual Ethernet). Point Atom MINI typically has one wired, ALPHA may have two.

## 52.2  Device tree

The FEC node:

```dts
&fec1 {
    pinctrl-names = "default", "sleep";
    pinctrl-0 = <&pinctrl_enet1>;
    pinctrl-1 = <&pinctrl_enet1_sleep>;
    phy-mode = "rmii";
    phy-handle = <&ethphy0>;
    phy-supply = <&reg_enet_3v3>;
    fsl,magic-packet;
    status = "okay";

    mdio {
        #address-cells = <1>;
        #size-cells = <0>;

        ethphy0: ethernet-phy@2 {
            compatible = "ethernet-phy-ieee802.3-c22";
            reg = <2>;
            micrel,led-mode = <1>;
            clocks = <&clks IMX6UL_CLK_ENET_REF>;
            clock-names = "rmii-ref";
        };
    };
};
```

Critical fields:

- **`phy-mode = "rmii"`** — the data interface between MAC and PHY. RMII (2-pair, 50 MHz) is what i.MX6ULL boards use. RGMII is for gigabit; not on i.MX6ULL.
- **`phy-handle`** — points to the PHY node. The MAC driver uses phylib to talk to it.
- **`reg = <2>` (in the PHY node)** — the PHY's MDIO address. Set by board strapping (PHYAD pins).
- **`micrel,led-mode = <1>`** — Micrel/Microchip-specific tweak (link-on-bicolor vs blink-on-activity).
- **`clocks` and `clock-names = "rmii-ref"`** on the PHY — tell the PHY driver which clock provides the 50 MHz RMII reference. **This is the biggest bring-up gotcha**; see §52.5.

## 52.3  netdev framework — what the driver provides

A network driver implements `net_device_ops`:

```c
static const struct net_device_ops fec_netdev_ops = {
    .ndo_open       = fec_enet_open,        /* ifconfig eth0 up */
    .ndo_stop       = fec_enet_close,        /* ifconfig eth0 down */
    .ndo_start_xmit = fec_enet_start_xmit,   /* TX one packet */
    .ndo_set_mac_address = eth_mac_addr,
    .ndo_validate_addr   = eth_validate_addr,
    .ndo_tx_timeout      = fec_timeout,
    .ndo_get_stats64     = fec_enet_get_stats,
    /* ... */
};

/* In probe: */
struct net_device *ndev = alloc_etherdev_mqs(sizeof(struct fec_enet_private), num_tx_queues, num_rx_queues);
ndev->netdev_ops = &fec_netdev_ops;
ndev->ethtool_ops = &fec_enet_ethtool_ops;
SET_NETDEV_DEV(ndev, &pdev->dev);
register_netdev(ndev);
```

`alloc_etherdev_mqs` allocates a `net_device` with Ethernet defaults plus private storage. `register_netdev` creates the `eth0` interface and starts ifupdown / network manager hooks.

The driver receives packets in `napi_poll` (NAPI: New API; the polled receive model used since Linux 2.6) and transmits in `ndo_start_xmit`. NAPI batches RX interrupts to reduce the IRQ rate at high packet rates — instead of one IRQ per packet, the driver gets one IRQ, then polls until the RX queue is empty, then re-arms IRQ.

## 52.4  phylib — the PHY library

PHYs all speak (mostly) the same management protocol: **MDIO/MDC clauses 22 and 45** define a small register space (32 registers in C22, 65536 in C45) accessed over a 2-wire bus.

The MAC driver doesn't directly talk to the PHY. It uses **phylib**:

```c
phydev = of_phy_connect(ndev, phy_handle, fec_link_state_change_cb,
                        0, PHY_INTERFACE_MODE_RMII);
```

The PHY's per-chip quirks live in a vendor PHY driver (`drivers/net/phy/micrel.c` for Microchip KSZ). The MAC driver just calls phylib functions:
- `phy_start(phydev)` — start autonegotiation.
- `phy_stop(phydev)` — halt.
- `phy_print_status(phydev)` — print link state.

The kernel autoloads the right PHY driver based on the PHY's identification registers (read via MDIO at boot).

```
[root@pa-mini:~]# dmesg | grep -i fec
fec 20b4000.ethernet: Falling back to support FF-MAC address
Micrel KSZ8081 RNB stepping 1.4: probed
fec 20b4000.ethernet eth0: registered PHC device 0
[root@pa-mini:~]# ip link show eth0
2: eth0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc fq_codel state UP mode DEFAULT group default qlen 1000
    link/ether 00:11:22:33:44:55 brd ff:ff:ff:ff:ff:ff
```

## 52.5  The RMII clock direction trap

The KSZ8081 can operate in two RMII modes:

- **PHY supplies REF_CLK** (50 MHz oscillator inside the PHY package).
- **MAC supplies REF_CLK** (i.MX6ULL's ENET_TX_CLK pin drives the PHY).

Which? **Depends on the board.** Point Atom boards historically use *MAC-supplied* clock (i.MX provides the 50 MHz to the PHY). Other boards do the reverse.

Wrong direction = no link, no MDIO communication, mysterious failures. The DT must declare:

- The PHY's `clocks = <&clks IMX6UL_CLK_ENET_REF>;` if MAC supplies clock.
- Omit the `clocks` and instead have the PHY's `clock-names = "rmii-ref";` if PHY supplies clock — but the PHY chip itself must be ordered with the "RNB" or "RND" variant.

Cross-check schematic ↔ DT ↔ PHY chip ordering code. Mismatch is the #1 cause of "Ethernet doesn't work" on new i.MX6ULL boards.

## 52.6  RMII pinmux

The RMII interface uses 7 pins:

| Signal | Direction | Purpose |
|--------|-----------|---------|
| TXD0, TXD1 | MAC → PHY | Outgoing data |
| TX_EN | MAC → PHY | Transmit enable |
| RXD0, RXD1 | PHY → MAC | Incoming data |
| CRS_DV | PHY → MAC | Carrier sense / data valid |
| REF_CLK | MAC↔PHY (one direction) | 50 MHz reference |

Plus MDIO and MDC (2 pins for PHY management). All 9 must be muxed correctly:

```dts
pinctrl_enet1: enet1grp {
    fsl,pins = <
        MX6UL_PAD_GPIO1_IO07__ENET1_MDC      0x1b0b0
        MX6UL_PAD_GPIO1_IO06__ENET1_MDIO     0x1b0b0
        MX6UL_PAD_ENET1_RX_DATA0__ENET1_RDATA00 0x1b0b0
        MX6UL_PAD_ENET1_RX_DATA1__ENET1_RDATA01 0x1b0b0
        MX6UL_PAD_ENET1_RX_EN__ENET1_RX_EN   0x1b0b0
        MX6UL_PAD_ENET1_RX_ER__ENET1_RX_ER   0x1b0b0
        MX6UL_PAD_ENET1_TX_DATA0__ENET1_TDATA00 0x1b0b0
        MX6UL_PAD_ENET1_TX_DATA1__ENET1_TDATA01 0x1b0b0
        MX6UL_PAD_ENET1_TX_EN__ENET1_TX_EN   0x1b0b0
        MX6UL_PAD_ENET1_TX_CLK__ENET1_REF_CLK1 0x4001b031
    >;
};
```

The last line's `0x4001b031` is the conf_reg value for the RMII reference clock — it sets the SION (Software Input ON) bit, which is required for the clock to be both an input and output. Forgetting this is a classic bug.

## 52.7  MAC address sources

Where does `eth0`'s MAC address come from?

1. **FEC's MAC register** (preserved across warm reset, set by bootloader).
2. **OCOTP fuses** (i.MX6ULL has MAC fuses; written once at factory).
3. **DT property `mac-address`**.
4. **Random** (last resort; address with locally-administered bit).

The mainline `fec_main.c` checks in this order: DT mac-address → OCOTP fuse → MAC register → random. For production: program the OCOTP at factory test (one-time, indelible). For development: pass via U-Boot's `bootargs` (`eth0=...`).

## 52.8  Bringing it up

After kernel boot with correct DT:

```
[root@pa-mini:~]# ip link show eth0
2: eth0: <BROADCAST,MULTICAST> mtu 1500 ...

[root@pa-mini:~]# ip link set eth0 up
[root@pa-mini:~]# dmesg | tail -2
fec 20b4000.ethernet eth0: Link is Up - 100Mbps/Full - flow control rx/tx

[root@pa-mini:~]# ip addr add 192.168.1.100/24 dev eth0
[root@pa-mini:~]# ping 192.168.1.1
PING 192.168.1.1 (192.168.1.1) 56(84) bytes of data.
64 bytes from 192.168.1.1: icmp_seq=1 ttl=64 time=0.452 ms
```

`ethtool` for inspection:

```
[root@pa-mini:~]# ethtool eth0
Settings for eth0:
        Supported ports: [ TP MII ]
        Supported link modes:   10baseT/Half 10baseT/Full
                                100baseT/Half 100baseT/Full
        Auto-negotiation: on
        Speed: 100Mb/s
        Duplex: Full
        Link detected: yes
```

`ethtool -S eth0` for hardware statistics (RX errors, TX collisions, etc.).

## 52.9  Dual FEC

For a board with both FEC1 and FEC2:

```dts
&fec1 { ... phy-handle = <&ethphy0>; ... };
&fec2 { ... phy-handle = <&ethphy1>; ... };
```

Two separate PHYs, two MDIO buses (one per FEC). Two independent `net_device`s appear (eth0 and eth1). They can be:
- Independent subnets (router scenario).
- Bonded (`ip link add bond0 type bond ...`) for redundancy.
- Bridged (`ip link add br0 type bridge ...`) for switching.

We'll go deeper on dual FEC in Part VII Ch 115 (Device Cookbook: Dual FEC + W5500).

## 52.10  Lab

1. **Verify Ethernet on Point Atom.** Boot a mainline-FEC-enabled kernel, plug Ethernet cable, observe link-up in dmesg, ping the gateway.
2. **Inspect the PHY.** `mii-diag eth0` or `ethtool eth0` to confirm PHY ID and link mode.
3. **Read MDIO directly.** `mii-tool -v eth0` shows raw PHY registers (status, control, ID).
4. **Set a custom MAC.** Via DT `mac-address` property; reboot; verify `ip link show eth0`.
5. **Throughput test.** `iperf3 -s` on the host, `iperf3 -c <host>` on the target. Expect ~94 Mbps (line-rate 100). Below 50 Mbps → debug.
6. **Recover from cable unplug.** Pull and replug; watch dmesg for the link-state transition. Confirm `eth0` recovers cleanly.

## 52.11  Pitfalls

- **RMII clock direction reversed.** No link. The most common, most painful. Confirm against schematic and PHY chip ordering code.
- **SION bit not set on REF_CLK pad.** Same symptom. Use `0x4001b031` (or whatever your conf_reg should be with `IMX_PAD_SION` set) for the REF_CLK pinmux.
- **Wrong PHY MDIO address.** PHY chip's `PHYAD` strapping pin determines its MDIO address; DT's `reg = <N>` must match. Default for KSZ8081 with PHYAD=1 strapped high is 1, but some boards strap it to 2.
- **Missing PHY supply.** PHY needs ~100 mA from a 3.3V rail. If reg_enet_3v3 isn't enabled at the right time, MDIO reads return 0xFFFF.
- **MII vs RMII pinmux swap.** Pads with similar names but different signals. Cross-check `imx6ul-pinfunc.h` macros.
- **MAC address all zeros.** Set OCOTP at factory, or pass via bootargs. Linux's "random" fallback won't survive reboots, breaking DHCP-leased systems.
- **Forgot phy-mode.** Without `phy-mode = "rmii"`, default may be MII (different signals); link won't come up.
- **NAPI weight too low** for high-rate traffic. Default 64 is fine for 100 Mbps; bump higher for gigabit (not on i.MX6ULL).
- **Cable issue.** Half the "FEC not working" reports turn out to be a bent CAT5e or a dead RJ45 jack. Try a different cable before debugging software.

## 52.12  Going deeper

- **`drivers/net/ethernet/freescale/fec_main.c`** — the mainline FEC driver. Important read.
- **`drivers/net/phy/micrel.c`** — KSZ8081 / KSZ9031 / etc. PHY drivers.
- **`Documentation/networking/`** — kernel networking documentation.
- **`Documentation/devicetree/bindings/net/ethernet-controller.yaml`** — generic Ethernet binding.
- **`Documentation/devicetree/bindings/net/fsl-fec.yaml`** — FEC-specific binding.
- **`Documentation/networking/phy.rst`** — phylib internals.
- **`tools/testing/selftests/net/`** — kernel's network self-tests; useful templates for your own.

> Next chapter: **Chapter 52A — PREEMPT_RT.** When latency matters more than throughput, the real-time kernel patches turn Linux into a viable hard-real-time platform. We cover what they do, how to measure, and the trade-offs.
