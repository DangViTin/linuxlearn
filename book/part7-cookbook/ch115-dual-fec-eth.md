---
chapter: 115
title: Dual FEC + hosted Ethernet (W5500, ENC28J60)
part: VII — Device cookbook
estimated_pages: 14
status: draft
---

# Chapter 115 — Dual FEC + hosted Ethernet

> **What:** putting **multiple Ethernet interfaces** on an i.MX6ULL. The SoC has two on-chip **FEC (Fast Ethernet Controller)** instances at 100 Mbps; we bring both up simultaneously as `eth0` and `eth1` with separate PHYs. For a third (or fourth) interface, we add **WIZnet W5500** (SPI Ethernet with hardware TCP/IP) or **Microchip ENC28J60** (older, slower, mainline-supported) as `spi-ethernet` chips. We then build typical multi-NIC scenarios: a **router** (eth0 WAN, eth1 LAN), a **bridge** (eth0+eth1 transparent L2), and an **isolated subnet** for industrial bus traffic (eth1 talks only to PLCs, eth0 to corporate network).
> **Why:** any "edge gateway" product has 2+ Ethernet ports — one to the internet, one to a local industrial network — because mixing the two on a single physical port creates security and reliability problems. The i.MX6ULL is unusual in having two on-chip FECs (most SoCs in this class have one); this is a feature you should exploit. When you need a third interface (e.g., a separate management LAN, or a Modbus-TCP island), SPI Ethernet chips are the only way without an external switch — and they're easy on Linux thanks to mainline drivers.
> **Focus:** **dual-MAC on one SoC means two PHYs, each with its own pin-mux + clock + interrupt; the kernel netdev model already isolates them so they look like two cards. The hard part is the bring-up: pinmux conflicts (FEC1 shares many pins with FEC2 + UART), separate PHY addresses on MDIO, and per-PHY interrupt routing**. For SPI Ethernet: the W5500 is *hardware TCP/IP* (you talk to it at the socket layer over SPI, not as a netdev) which is alien on Linux; mainline-friendly choices are ENC28J60 (slow, netdev-presenting) and TI's KSZ8851 / Davicom DM9051 (10/100, netdev, faster). We cover all three patterns.

## 115.1  i.MX6ULL FEC overview

The i.MX6ULL has **2× FEC** (FEC1 and FEC2 in the reference manual), each:
- 10/100 Mbps MAC
- RMII PHY interface (4 wires for data + 1 clock vs 8+ for MII; cheaper, fewer pins)
- IEEE 1588 PTP timestamp support
- Separate DMA channel
- Separate IRQ

Each FEC needs:
- An external PHY chip (KSZ8081, LAN8720A, RTL8201F are common).
- A 50 MHz clock to the RMII interface (either from the PHY's own crystal or from the SoC).
- Pin-muxed RGMII/RMII signals.
- MDIO (a 2-wire management bus shared between both PHYs on most designs).

## 115.2  Wiring two PHYs

The reference Point Atom MINI board has only FEC1 wired (single Ethernet); to bring up FEC2 you must either choose a board with both routed (some i.MX6ULL devkits have it), or wire FEC2 to a second PHY breakout. Pinout (RMII):

```
   FEC1                       PHY 1 (KSZ8081)
   ENET1_TX_EN  ────────────  TXEN
   ENET1_TX_DATA[1:0]  ─────  TXD[1:0]
   ENET1_RX_EN/CRS  ─────────  CRS_DV
   ENET1_RX_DATA[1:0]  ──────  RXD[1:0]
   ENET1_RX_ER  ────────────  RXER
   ENET1_TX_CLK (RMII REF)  ──  REF_CLK   (50 MHz; can be SoC-out or PHY-out)
   ENET1_MDIO  ─────────────  MDIO
   ENET1_MDC   ─────────────  MDC

   FEC2                       PHY 2 (KSZ8081, different MDIO address)
   ENET2_*   ────────────────  same as above, separate pins
```

Critical: each PHY has a **strap-pin-set MDIO address** (typically 0, 1, 2, …). FEC1's PHY at address 0; FEC2's PHY at address 1. Both share the MDIO bus (MDC/MDIO can be shared on most designs), and FEC2 reads address-1's registers.

DT for both FECs (excerpt from `arch/arm/boot/dts/imx6ull-myboard.dts`):

```dts
&fec1 {
    pinctrl-names = "default";
    pinctrl-0 = <&pinctrl_enet1>;
    phy-mode = "rmii";
    phy-handle = <&ethphy0>;
    status = "okay";

    mdio {
        #address-cells = <1>;
        #size-cells = <0>;

        ethphy0: ethernet-phy@0 {
            reg = <0>;
            micrel,led-mode = <1>;
            clocks = <&clks IMX6UL_CLK_ENET_REF>;
            clock-names = "rmii-ref";
        };

        ethphy1: ethernet-phy@1 {
            reg = <1>;
            micrel,led-mode = <1>;
            clocks = <&clks IMX6UL_CLK_ENET2_REF>;
            clock-names = "rmii-ref";
        };
    };
};

&fec2 {
    pinctrl-names = "default";
    pinctrl-0 = <&pinctrl_enet2>;
    phy-mode = "rmii";
    phy-handle = <&ethphy1>;
    status = "okay";
};
```

The MDIO node is under FEC1 (one MDIO instance), with both PHYs as children. FEC2 references `ethphy1` via `phy-handle`.

After boot:

```sh
ip link
# 2: eth0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 ... ether AA:BB:CC:00:00:01
# 3: eth1: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 ... ether AA:BB:CC:00:00:02
```

`ethtool eth0` and `ethtool eth1` should show "Link detected: yes" when cables are plugged.

## 115.3  Router pattern — WAN on eth0, LAN on eth1

```sh
# Bring up
ip addr add 192.168.1.1/24 dev eth1
ip link set eth1 up

dhclient eth0          # WAN gets its IP from upstream

# Enable IP forwarding
sysctl -w net.ipv4.ip_forward=1

# NAT (masquerade LAN behind WAN)
iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE
iptables -A FORWARD -i eth1 -o eth0 -j ACCEPT
iptables -A FORWARD -i eth0 -o eth1 -m state --state RELATED,ESTABLISHED -j ACCEPT

# DHCP server for LAN
apt install dnsmasq
cat >> /etc/dnsmasq.conf <<EOF
interface=eth1
dhcp-range=192.168.1.50,192.168.1.150,12h
EOF
systemctl restart dnsmasq
```

Done. Your i.MX6ULL is a router. Add `nftables` for modern filtering, or stick with `iptables` for familiarity.

## 115.4  Bridge pattern — transparent L2 between eth0 + eth1

For when you want the i.MX6ULL to be invisible to upstream traffic but still observe / log it:

```sh
ip link add br0 type bridge
ip link set eth0 master br0
ip link set eth1 master br0
ip link set br0 up
ip addr add 192.168.1.5/24 dev br0    # optional, for management
```

Traffic flows transparently between eth0 and eth1; the i.MX6ULL can sniff via `tcpdump -i br0`, optionally filter / mirror via `tc` qdiscs. Useful for inline industrial-traffic monitoring.

## 115.5  Isolated subnet pattern — eth1 for industrial bus

For security + reliability: eth0 is the corporate network (with internet); eth1 is a dedicated subnet to PLCs / sensors. No bridge, no routing — packets do not cross.

```sh
ip addr add 192.168.2.1/24 dev eth1     # private industrial subnet
ip link set eth1 up
# No forwarding; eth1 traffic stays on eth1

# Your application reads modbus from 192.168.2.x devices via eth1
# Your application reports to cloud via eth0
```

Compromise of corporate side doesn't expose PLCs. Compromise of PLC subnet doesn't pivot to cloud. This is the industrial-IoT best practice and a major reason for needing dual-NIC.

## 115.6  Adding a third NIC via SPI — the W5500 (hardware TCP/IP)

W5500 is unusual: it's not a netdev; it's a **hardware TCP/IP stack** with 8 sockets, accessed over SPI. You don't talk Ethernet frames to it — you `OPEN`, `CONNECT`, `SEND`, `RECV` at the TCP/UDP level.

This is great for tiny MCUs but awkward on Linux. The mainline kernel does not have a W5500 driver in `drivers/net/`. There are out-of-tree drivers that wrap W5500 sockets as Linux `AF_INET` sockets, but they're niche.

**Practical Linux choice**: use W5500's sockets directly from user-space via SPI. Or — pick a different chip.

## 115.7  Adding a third NIC via SPI — ENC28J60 / DM9051 (mainline netdev)

For a third netdev, use ENC28J60 (slow but ubiquitous) or DM9051 (faster, both mainline). DM9051 is 10/100; ENC28J60 is 10 Mbps only.

DT for DM9051:

```dts
&ecspi3 {
    cs-gpios = <&gpio4 26 GPIO_ACTIVE_LOW>;
    status = "okay";

    eth: ethernet@0 {
        compatible = "davicom,dm9051";
        reg = <0>;
        spi-max-frequency = <20000000>;
        interrupts-extended = <&gpio4 27 IRQ_TYPE_LEVEL_LOW>;
        reset-gpios = <&gpio4 28 GPIO_ACTIVE_LOW>;
        local-mac-address = [DE AD BE EF 00 03];
    };
};
```

After `modprobe dm9051`:

```sh
ip link
# 4: eth2: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 ... ether DE:AD:BE:EF:00:03
```

You now have eth0 (FEC1), eth1 (FEC2), eth2 (DM9051 SPI). Three independent Ethernet interfaces.

Throughput limits:
- FEC1/FEC2: ~95 Mbps each (line rate at 100 Mbps).
- DM9051 SPI at 20 MHz: ~8 Mbps (SPI overhead dominates).
- ENC28J60 SPI at 20 MHz: ~3 Mbps.

DM9051 is fine for a 3rd "management interface" or a Modbus-TCP island bus. Don't expect it to handle real traffic.

## 115.8  How the FEC driver works

`drivers/net/ethernet/freescale/fec_main.c` — the mainline FEC driver, ~3500 lines. Key points:

- One netdev per `&fecN` DT node.
- Setup at probe: enable clocks, reset MAC, attach PHY via `of_phy_connect`, allocate BD ring buffers.
- TX: `fec_enet_start_xmit` → fills a BD, kicks the DMA, returns.
- RX: NAPI poll; the driver's interrupt schedules NAPI; NAPI loops over the RX ring, calls `napi_gro_receive` per packet.
- PHY: `linkstate` change events from the PHY (via MDIO polling) update netif_carrier_on/off, triggering `ifconfig` to show link state.

Walk of `fec_enet_start_xmit` (paraphrased):

```c
static netdev_tx_t fec_enet_start_xmit(struct sk_buff *skb, struct net_device *ndev) {
    struct fec_enet_private *fep = netdev_priv(ndev);
    struct bufdesc *bd = fec_enet_get_nextbd(fep->bd_tx);
    /* Map skb data to a DMA-coherent buffer (or use the skb's own DMA-mapped page) */
    dma_addr_t addr = dma_map_single(..., skb->data, skb->len, DMA_TO_DEVICE);
    bd->cbd_bufaddr = addr;
    bd->cbd_datlen = skb->len;
    bd->cbd_sc = BD_ENET_TX_READY | BD_ENET_TX_LAST | BD_ENET_TX_INTR | BD_ENET_TX_TC;
    /* Write 1 to FEC TX descriptor active register to kick TX */
    writel(0, fep->hwp + FEC_TX_DESC_ACTIVE);
    return NETDEV_TX_OK;
}
```

NAPI receive:

```c
static int fec_enet_rx_napi(struct napi_struct *napi, int budget) {
    int pkts_received = 0;
    while (pkts_received < budget) {
        struct bufdesc *bd = next_rx_bd(fep);
        if (bd->cbd_sc & BD_ENET_RX_EMPTY) break;   /* no more packets */
        struct sk_buff *skb = napi_alloc_skb(napi, bd->cbd_datlen);
        memcpy(skb->data, dma_data, bd->cbd_datlen);
        skb->protocol = eth_type_trans(skb, ndev);
        napi_gro_receive(napi, skb);
        bd->cbd_sc |= BD_ENET_RX_EMPTY;             /* return BD to RX ring */
        pkts_received++;
    }
    if (pkts_received < budget) napi_complete_done(napi, pkts_received);
    return pkts_received;
}
```

This is canonical NAPI: process up to `budget` packets per call; if fewer, complete and re-enable IRQ. Higher latency, much higher throughput than per-packet interrupts.

## 115.9  Lab

1. **Single FEC up.** Default config: confirm eth0 works (`ping`, `curl`).
2. **Add second PHY.** Wire up FEC2 + a second PHY (KSZ8081 on a breakout). Configure DT. Verify eth1 appears + carrier detects when cable plugged.
3. **MAC address uniqueness.** Confirm eth0 and eth1 have different MAC addresses (the kernel auto-generates from the chip UID if DT doesn't specify). Set explicit MACs in DT via `local-mac-address` if needed.
4. **Router scenario.** Configure eth0 as WAN + DHCP client; eth1 as LAN + DHCP server. Plug a laptop into eth1; it should DHCP an IP and route to internet via eth0.
5. **Bridge scenario.** Same boards as a transparent L2 bridge; tcpdump traffic on br0; verify no MAC NAT.
6. **Industrial isolation.** eth1 in 192.168.2.0/24 (no route to/from eth0); attach 5 simulated Modbus-TCP devices; verify your collector reads them and forwards summaries via eth0 with strict iptables rules.
7. **Add DM9051 SPI Ethernet.** Wire DM9051 to ECSPI3 + IRQ + RESET GPIOs. DT update. `modprobe dm9051`. Confirm eth2 appears.
8. **Throughput test.** `iperf3` between two i.MX6ULLs via FEC (95 Mbps), then via DM9051 (8 Mbps). Quantify.
9. **PTP timestamping.** Enable `ethtool -T eth0` PTP HW timestamping. Run `ptp4l` to discipline the clock via PTP. Measure offset over time.
10. **Mixed routing.** Three interfaces; routing rules send VLAN 1 → eth0, VLAN 2 → eth1, mgmt → eth2.

Commit DT overlays, iptables/nftables rules, dnsmasq config to `code/ch115-eth/`.

## 115.10  Pitfalls

- **MDIO address conflict.** Both PHYs configured to address 0 → only one responds; the other looks like "not present." Verify PHY strap pins.
- **Pinmux conflict.** FEC2 pins overlap UART2 + I²C on some i.MX6ULL packages. Check `pinctrl-imx6ull.h` carefully; some functions are mutually exclusive.
- **RMII REF_CLK direction.** Either the SoC supplies REF_CLK to the PHY, or the PHY's crystal does, and the PHY supplies it back to the SoC. Wrong direction = no link. Configurable in DT via `clocks` property + PHY strap pins.
- **EMC noise.** Two RMII interfaces close together radiate similarly; common-mode chokes on each Ethernet jack help.
- **No explicit MAC address.** Kernel generates from chip UID; random reboots can yield different MACs if UID isn't read correctly. Set `local-mac-address` in DT for production.
- **Setting MAC after `ip link up`.** Some PHYs latch the MAC at link-up; changes after may not take effect. Set before `up`.
- **DM9051 IRQ level vs edge.** DM9051 datasheet specifies active-low level-triggered IRQ; misconfigured edge-triggered loses interrupts and the interface hangs.
- **SPI Ethernet under load.** Even DM9051 caps at ~10 Mbps; if you try to use it as a primary interface, performance suffers. Use it as a management or low-bandwidth interface only.
- **W5500 expectation mismatch.** W5500 is not a netdev; if you ordered "SPI Ethernet" thinking it would integrate with `ip link`, you'll be surprised. Order DM9051 or ENC28J60 for true netdev.
- **Bridge + ip address on members.** Once an interface is enslaved to a bridge, only the bridge gets an IP. The slave interfaces don't participate in L3.

## 115.11  Going deeper

- **`drivers/net/ethernet/freescale/fec_main.c`** — read it; canonical mainline NIC driver.
- **`drivers/net/ethernet/davicom/dm9051.c`** — SPI Ethernet driver.
- **`Documentation/networking/`** kernel docs — NAPI, bridging, VLAN, bonding.
- **`iproute2` manuals** — `ip link`, `ip addr`, `ip route`.
- **`nftables` wiki** — modern firewall/NAT.
- **NXP IMX6ULL Reference Manual ch. 22 (ENET)** — register-level FEC details.
- **KSZ8081 datasheet** — most-used PHY, strap-pin docs are critical.
- **IEEE 1588 / PTP** — for clock distribution over Ethernet (extends Ch 107's GPS-time use case).
- **Ch 52** — the original FEC driver chapter.
- **Ch 91** — for WiFi as an alternative network interface.

---

> Next chapter: **Chapter 116 — PMICs and the regulator framework** — power-management ICs (PCA9450, PF8200).
