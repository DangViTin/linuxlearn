---
chapter: 98
title: LoRa (SX127x / SX126x / LLCC68 / E22)
part: VII — Device cookbook
estimated_pages: 22
status: draft
---

# Chapter 98 — LoRa

> **What:** **LoRa** — a Semtech-proprietary sub-GHz long-range modulation (chirp spread spectrum) reaching multiple kilometres at sub-100 kbps. Four real radios compared: **Semtech SX1276/78** (legacy LoRa, 433/868/915 MHz), **SX1262** (current generation, lower power, FSK + LoRa), **LLCC68** (cheap SX1262 sibling, limited SF range), and **EByte E22-900M30S** (a ready-to-fly SX1262 module with PA + LNA). We dissect the radio's SPI register map, walk the kernel `sx127x` / `sx1301` candidate drivers (and why **most production LoRa stacks live in user space**), write a tiny SPI-only LoRa driver from scratch in user space (no kernel driver), then bring up a real LoRaWAN gateway with **ChirpStack**.
>
> **Why:** LoRa is the only short-message radio that crosses kilometres without infrastructure, sub-watt, and into deep building penetration. It's the workhorse for agricultural sensors, wildlife trackers, water-meter telemetry, and remote alarms. Many engineers copy the "Arduino LoRa library" without understanding the modulation, the registers, or why a bad antenna costs most of your link budget. This chapter walks the whole stack.
>
> **Focus:** **LoRa is a SPI radio with two state machines on top — modem and packet handler — and a tightly coupled antenna RF chain you cannot ignore**. Chirp spread spectrum (CSS) gives ~–137 dBm sensitivity at SF12/125 kHz, but the air-time at SF12 is *seconds per packet*, throttled by duty-cycle regulation (1 % on 868 MHz EU). The four-tuple of spreading factor, bandwidth, coding rate, and preamble is the whole engineering job. You must know what each one costs in air-time, sensitivity, and power. The radio is easy. The link budget is the engineering.

## 98.1  LoRa vs everything else short-message

| | LoRa (CSS) | BLE (Ch 95–97) | Sub-GHz FSK (Ch 99) | NB-IoT (Ch 104) | WiFi |
|---|---|---|---|---|---|
| Range (open field) | 5–15 km | ~30 m | ~1 km | cellular cell | ~50 m |
| Range (urban, dense) | 1–3 km | ~10 m | ~300 m | cellular cell | ~20 m |
| Bitrate | 0.3–50 kbps | 1 Mbps | 1–500 kbps | 30 kbps | 10–600 Mbps |
| RX current | ~10 mA | ~5 mA | ~13 mA | ~30 mA | ~80 mA |
| Sleep / cold | 200 nA | 1 µA | 1 µA | 1 µA (PSM) | 1 mA |
| Infrastructure needed | optional (LoRaWAN GW) | none / phone | none | carrier cell | router |
| Spectrum | ISM sub-GHz | 2.4 GHz | ISM sub-GHz | licensed cellular | 2.4/5 GHz |
| Cost (radio IC) | $3–6 | $1–3 | $1–4 | $5–10 | $2–5 |
| Air time per packet | **seconds at SF12** | 1 ms | 5 ms | 200 ms | <1 ms |
| Duty cycle limit | 0.1–10 % (regional) | none | 0.1–10 % | none | none |

The trade is direct: LoRa buys range with bitrate. At SF12/BW125, you transmit ~250 bits per *second* (yes, per second). A 50-byte payload costs **~2 seconds of air time**. EU 868 MHz lets you transmit only 1 % of the time → ~30 packets/hour. That single number drives every product decision.

**Pick guide:**
- **SX1276/78** — legacy projects, abundant code, OK power; pick SX1262 instead for anything new.
- **SX1262** — the default new design. Lower TX current (~118 mA at +22 dBm vs ~120 mA at +20 dBm for SX1276), better RX sensitivity, FSK + LoRa in one chip, +22 dBm internal PA.
- **LLCC68** — SX1262 register-compatible *almost*; only SF5–SF11 (no SF12). Save $0.50/unit if SF12 isn't needed.
- **EByte E22** — buy this if you want a finished module with PA, LNA, SMA connector, RF shield. Slightly closed (you can't change the matching network) but eliminates 80 % of the RF risk.

## 98.2  How chirp spread spectrum actually works (the 5-minute primer)

LoRa modulation is **chirp spread spectrum (CSS)**: each symbol is a frequency *sweep* (a chirp) over the channel bandwidth. A symbol encodes `SF` bits, where **SF (spreading factor)** is 7..12. The chirp starts at a frequency offset proportional to the symbol value and sweeps linearly.

```
Frequency
   ▲
BW │      ╱╲      ╱╲       ╱╲          ╱╲
   │     ╱  ╲    ╱  ╲     ╱  ╲        ╱  ╲
   │    ╱    ╲  ╱    ╲   ╱    ╲      ╱    ╲
   │   ╱      ╲╱      ╲ ╱      ╲    ╱      ╲
   │  ╱       ╳        ╳        ╲  ╱        ╲
   │ ╱        ╳        ╳         ╲╱          ╲
   │╱          ╳        ╳         ╳            ╲
   └──────────────────────────────────────────► time
       sym0   sym1     sym2      sym3
        ↑      ↑         ↑        ↑
   each chirp = SF bits encoded by starting frequency offset
```

Key consequences:

- **Symbol time** doubles every increase of SF: `Tsym = 2^SF / BW`. At SF12/BW125: 32.768 ms *per symbol*. At SF7/BW125: 1.024 ms.
- **Bitrate** ≈ `SF × BW / 2^SF × CR`. At SF12/BW125/CR4/5: ~293 bps. At SF7/BW125/CR4/5: ~5.5 kbps.
- **Sensitivity** improves about 2.5 dB per SF step. SF7 is around −123 dBm; SF12 is around −137 dBm. That is **14 dB** of headroom, or roughly 5× the range.
- **Demodulation** is processing-gain-based: even buried in noise, the chirp correlation pulls the signal out. This is why LoRa works below the noise floor.

The four-tuple you tune for every link:

| Knob | Range | What it costs |
|------|-------|---------------|
| **SF** (spreading factor) | 7–12 | doubles air time per step; +2.5 dB sensitivity per step |
| **BW** (bandwidth) | 7.8 / 10.4 / 15.6 / 20.8 / 31.25 / 41.7 / 62.5 / 125 / 250 / 500 kHz | wider = faster but less sensitive; 125 kHz is the universal default |
| **CR** (coding rate) | 4/5, 4/6, 4/7, 4/8 | extra parity → +overhead, +robustness |
| **Preamble length** | 6–65535 symbols | longer = receiver wake-up time, but consumes air time |

A 50-byte payload at SF12/BW125/CR4/5: ~2.3 s. At SF7/BW125/CR4/5: ~110 ms. Same payload, 20× the throughput. *But*: SF7 reaches ~3 km open field; SF12 reaches ~10 km. The product choice is in that ratio.

## 98.3  SX1276 and SX1262 — what's in the chip

Both are single-chip transceivers: digital baseband + IF + RF front-end + PA. Antenna in/out is one or two pins (TX vs RX path selected by an internal RF switch on SX1262; external pin selection on SX1276).

Block diagram (SX1262, the one to use for new designs):

```
        ┌─────────────────────────────────────────────────────────┐
        │  SX1262                                                  │
        │  ┌────────┐   ┌───────────┐   ┌──────┐   ┌───────────┐   │
   SPI ─┼─►│ Config │──►│ Modem     │──►│ +22  │──►│ RF switch │──┼─► RFO
        │  │ regs   │   │ (LoRa/FSK)│   │ dBm  │   │           │  │
        │  └────┬───┘   │           │   │ PA   │   │           │◄─┼─◄ RFI
        │       │       └───────────┘   └──────┘   └───────────┘  │
        │       │        ▲         ▲                              │
        │       └────────┘         │                              │
        │   command interpreter    │                              │
        │   (op-codes, not regs!)  │                              │
        │                                                          │
        │  XTAL 32 MHz ── PLL ── digital + analog clocks            │
        │  TCXO opt.                                                │
        └─────────────────────────────────────────────────────────┘
                        ▲     ▲      ▲
                       BUSY  DIO1   DIO2
                              (IRQ) (RF switch / RX-en)
```

The two chips differ in interface style:

- **SX1276/78** are **register-mapped**: `WRITE_REG addr value`, `READ_REG addr` on SPI. ~120 registers documented in the datasheet. You configure by writing each register.
- **SX1262** is **command-based**: `SetPacketType`, `SetRfFrequency`, `SetTxParams`, `SetModulationParams`, `WriteBuffer`, `SetTx`. Each is an opcode + payload over SPI; the chip parses it. Easier to use, but the code looks different from SX1276's.

This is the #1 source of porting pain when moving SX1276 code to SX1262.

### SX1276 register map (the parts that matter)

| Addr | Name | Purpose |
|------|------|---------|
| 0x00 | FIFO | TX/RX FIFO data (R/W) — burst-read pulls bytes |
| 0x01 | OpMode | LoRa/FSK toggle, mode (sleep/standby/tx/rx) |
| 0x06–08 | FrfMsb/Mid/Lsb | RF frequency: `Fcarrier = Frf × 32e6 / 2^19` |
| 0x09 | PaConfig | PA selection (RFO vs PA_BOOST), output power |
| 0x0E | FifoTxBaseAddr | where in the 256-byte chip RAM TX starts |
| 0x0F | FifoRxBaseAddr | where RX starts |
| 0x10 | FifoAddrPtr | current FIFO read/write pointer |
| 0x12 | IrqFlags | IRQ status — write 1 to clear |
| 0x13 | RxNbBytes | bytes in the last received packet |
| 0x1D | ModemConfig1 | BW (upper 4 bits), CR (3 bits), explicit/implicit header |
| 0x1E | ModemConfig2 | SF (upper 4), CRC enable, TX continuous |
| 0x20 | PreambleMsb | preamble length (in symbols) |
| 0x21 | PreambleLsb | |
| 0x22 | PayloadLength | TX length (or expected RX in implicit mode) |
| 0x39 | SyncWord | 0x12 (private) or 0x34 (LoRaWAN) |
| 0x40 | DioMapping1 | which IRQ source each DIO pin signals |
| 0x42 | Version | 0x12 for SX1276 |

The TX sequence in pseudocode:

```
1. WRITE_REG(OpMode, LoRa|Standby)
2. WRITE_REG(FrfMsb..Lsb, freq)
3. WRITE_REG(PaConfig, PA_BOOST | output_power)
4. WRITE_REG(ModemConfig1, BW125 | CR45 | explicit_hdr)
5. WRITE_REG(ModemConfig2, SF7 | CRC_on)
6. WRITE_REG(PreambleLsb, 8)
7. WRITE_REG(PayloadLength, N)
8. WRITE_REG(FifoTxBaseAddr, 0); WRITE_REG(FifoAddrPtr, 0)
9. BURST_WRITE(FIFO, payload, N)
10. WRITE_REG(DioMapping1, DIO0=TxDone)
11. WRITE_REG(OpMode, LoRa|Tx)        ← starts TX
12. wait for DIO0 rising edge        ← TxDone interrupt
13. WRITE_REG(IrqFlags, 0xFF)          ← clear all flags
14. WRITE_REG(OpMode, LoRa|Standby)
```

That's it. Eighty registers in the datasheet; this loop uses twelve.

## 98.4  Wiring — what the schematic must do

The radio is easy. The RF path is where projects die.

```
       ┌──────────────┐                                  ┌────────┐
i.MX  ─┤ MOSI         ├─── 3.3 V SPI ────────────────────┤ MOSI   │
ECSPI ─┤ MISO         ├──────────────────────────────────┤ MISO   │
       │ SCK          ├──────────────────────────────────┤ SCK    │
       │ CS#  (GPIO)  ├──────────────────────────────────┤ NSS    │
GPIO  ─┤ RESET#       ├──────────────────────────────────┤ RESET# │
GPIO  ─┤ DIO0/IRQ     ├──────────────────────────────────┤ DIO0/  │   SX1276/SX1262
       │              │                                  │  DIO1  │
       │              │                          (3.3V) ─┤ VDD    │   ┌──────┐
       │              │                            GND ──┤ GND    ├──◄┤ π-net├──◄ SMA antenna
       │              │                                  │ RFO/   │   │ match │
       │              │                                  │  ANT   ├──►└──────┘
       └──────────────┘                                  └────────┘
```

Mandatory rules. Every one of these has destroyed a board in the field:

1. **Antenna or 50 Ω dummy load at TX every time.** Transmitting into an open or short pin destroys the PA in milliseconds. This matters most during bring-up, when it is tempting to power the radio without an antenna just to see if it responds.
2. **VDD bulk capacitor ≥ 10 µF + 100 nF near the chip.** Each transmit pulse is ~120 mA at +22 dBm — the supply must hold up. A weak rail = power droop = the modem retransmits = battery dies overnight.
3. **Ground plane under the radio.** Single-sided protoboard works at SF12 for ~30 m. Move to a real PCB with continuous ground for anything beyond eval.
4. **TCXO recommended for SF11/SF12.** The crystal must hold ±20 ppm over temperature; a cheap XTAL drifts and the SF12 demodulator (very narrow effective bandwidth) loses the signal. SX1262 has TCXO control built in (`SetDIO3AsTCXOCtrl`).
5. **PA_BOOST vs RFO on SX1276.** Two output paths. PA_BOOST is the high-power one (up to +20 dBm); RFO is the lower one (max +14 dBm). Pick *one* and route only that to your antenna. Asserting +20 dBm on RFO destroys the chip.
6. **EByte modules** integrate the matching network and add a +30 dBm PA. They eliminate steps 1–5 if you also buy a real antenna. Total project savings: enormous.

## 98.5  The kernel side — and why most LoRa stacks aren't in the kernel

There's no `subsystem/lora/` in mainline. There are out-of-tree drivers (`sx127x-driver`, `sx1301-cpld-driver` for the concentrator chip used in LoRaWAN gateways), but the dominant pattern is **`spidev` + a user-space stack**. Reasons:

1. **LoRaWAN MAC is huge and stateful.** The link-layer (network/application keys, ADR, retransmission, multi-channel scanning) lives in a daemon (ChirpStack, lora-net, lorawan-stack). A kernel driver isn't where this belongs.
2. **No standard MAC.** P2P LoRa is application-defined; LoRaWAN is the most common but not the only. Every product wraps the PHY differently.
3. **Timing is not RT-critical.** LoRa packets are tens-to-thousands of milliseconds long. User-space SPI latency (a few ms) is irrelevant.
4. **Mainline has refused most LoRa kernel patches** for these reasons. The community converged on user-space.

This is unusual in this book. Almost every other chapter says "the kernel driver does this." On LoRa, the kernel is only the SPI bus controller.

There *is* one important exception: **LoRaWAN gateway concentrators** (Semtech SX1301, SX1302, SX1303) — multi-channel parallel demodulators on PCIe or SPI used in *gateways* (not nodes). Even these are bound by `spidev`, with a user-space "packet forwarder" (`lora_pkt_fwd`, ChirpStack-MP-Packet-Forwarder). The hardware is FPGA-like; the abstraction is in user space.

### What an out-of-tree LoRa kernel driver looks like (for context)

The community `sx127x-driver` and `lora-net` Linux trees expose the radio as a **netdev** — `lora0` shows up like `wlan0`, you `ip link set lora0 up`, and a SOCK_RAW socket gives you packets. The driver pattern is:

```c
// Simplified from lora-net out-of-tree
static const struct net_device_ops sx127x_netdev_ops = {
    .ndo_open       = sx127x_open,        /* set RX mode, enable IRQ */
    .ndo_stop       = sx127x_stop,        /* sleep mode */
    .ndo_start_xmit = sx127x_xmit,        /* push frame to FIFO, start TX */
};

static int sx127x_probe(struct spi_device *spi) {
    struct net_device *ndev = alloc_netdev(sizeof(*priv), "lora%d", ...);
    /* attach SPI, IRQ on DIO0, GPIO reset */
    request_threaded_irq(spi->irq, NULL, sx127x_irq_thread,
                         IRQF_ONESHOT, "sx127x", priv);
    /* probe by reading reg 0x42 — must be 0x12 for SX1276 */
    if (sx127x_read_reg(spi, 0x42) != 0x12) return -ENODEV;
    sx127x_reset(priv);
    sx127x_init_modem(priv, SF7, BW125, CR45);
    return register_netdev(ndev);
}
```

The threaded IRQ on DIO0 fires on `TxDone`/`RxDone`, the handler reads `IrqFlags`, pulls the FIFO, hands the skb up. It looks like every Linux netdev driver, just with chirp modulation under the hood.

But the **MAC** — addressing, ADR, retransmission, LoRaWAN OTAA join — is *not* in the driver. That's the daemon's job in user space.

For this book, we follow the dominant pattern: **`spidev` + user-space driver + ChirpStack daemon**. The driver internals above are for understanding what a netdev-wrapped path would look like.

## 98.6  From scratch — a user-space SX1276 driver in C (transmit + receive)

We build the smallest possible LoRa driver: open `spidev`, reset the chip, configure modem, transmit a packet, receive a packet. ~200 lines, no LoRaWAN, no MAC. Pure PHY. Two boards running this can ping each other at 5 km.

sx1276_min.c:

```c
/* Minimal user-space SX1276 LoRa driver — PHY only, no LoRaWAN.
 * Pair: two i.MX6ULL boards, each with an SX1276 module on ECSPI1.
 * Lab: board A sends "hello %d"; board B prints received with RSSI/SNR.
 */
#include <fcntl.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>
#include <sys/ioctl.h>
#include <linux/spi/spidev.h>
#include <linux/gpio.h>

#define REG_FIFO         0x00
#define REG_OP_MODE      0x01
#define REG_FRF_MSB      0x06
#define REG_PA_CONFIG    0x09
#define REG_FIFO_TX_BASE 0x0E
#define REG_FIFO_RX_BASE 0x0F
#define REG_FIFO_ADDR    0x10
#define REG_FIFO_RX_CUR  0x10  /* same reg in standby */
#define REG_IRQ_FLAGS    0x12
#define REG_RX_NB_BYTES  0x13
#define REG_PKT_SNR      0x19
#define REG_PKT_RSSI     0x1A
#define REG_MODEM_CFG1   0x1D
#define REG_MODEM_CFG2   0x1E
#define REG_PREAMBLE_LSB 0x21
#define REG_PAYLOAD_LEN  0x22
#define REG_SYNC_WORD    0x39
#define REG_DIO_MAPPING1 0x40
#define REG_VERSION      0x42

#define OP_LONG_RANGE    0x80
#define OP_SLEEP         0x00
#define OP_STDBY         0x01
#define OP_TX            0x03
#define OP_RX_CONT       0x05

#define IRQ_TX_DONE      0x08
#define IRQ_RX_DONE      0x40

static int spi_fd;

static uint8_t reg_read(uint8_t addr) {
    uint8_t tx[2] = { addr & 0x7F, 0 }, rx[2];
    struct spi_ioc_transfer t = { .tx_buf=(unsigned long)tx, .rx_buf=(unsigned long)rx,
                                  .len=2, .speed_hz=1000000 };
    ioctl(spi_fd, SPI_IOC_MESSAGE(1), &t);
    return rx[1];
}

static void reg_write(uint8_t addr, uint8_t val) {
    uint8_t tx[2] = { addr | 0x80, val };
    struct spi_ioc_transfer t = { .tx_buf=(unsigned long)tx, .len=2, .speed_hz=1000000 };
    ioctl(spi_fd, SPI_IOC_MESSAGE(1), &t);
}

static void burst_read(uint8_t addr, uint8_t *buf, int n) {
    uint8_t cmd = addr & 0x7F;
    struct spi_ioc_transfer t[2] = {
        { .tx_buf=(unsigned long)&cmd, .len=1, .speed_hz=1000000 },
        { .rx_buf=(unsigned long)buf,  .len=n, .speed_hz=1000000 },
    };
    ioctl(spi_fd, SPI_IOC_MESSAGE(2), t);
}

static void burst_write(uint8_t addr, const uint8_t *buf, int n) {
    uint8_t cmd = addr | 0x80;
    struct spi_ioc_transfer t[2] = {
        { .tx_buf=(unsigned long)&cmd, .len=1, .speed_hz=1000000 },
        { .tx_buf=(unsigned long)buf,  .len=n, .speed_hz=1000000 },
    };
    ioctl(spi_fd, SPI_IOC_MESSAGE(2), t);
}

static void sx_reset(void) {
    /* assume RESET gpio handled via libgpiod or a sysfs poke — pulse low 1 ms */
    /* omitted here; the lab repo wires this to gpiod_line_set_value() */
}

static void sx_init(uint32_t freq_hz, uint8_t sf, uint8_t bw_idx) {
    /* Sleep → switch to LoRa → standby */
    reg_write(REG_OP_MODE, OP_LONG_RANGE | OP_SLEEP);
    reg_write(REG_OP_MODE, OP_LONG_RANGE | OP_STDBY);

    /* Frequency: Frf = freq * 2^19 / 32e6 */
    uint64_t frf = ((uint64_t)freq_hz << 19) / 32000000;
    reg_write(REG_FRF_MSB,     (frf >> 16) & 0xFF);
    reg_write(REG_FRF_MSB + 1, (frf >>  8) & 0xFF);
    reg_write(REG_FRF_MSB + 2,  frf        & 0xFF);

    /* PA_BOOST, output power = 17 dBm (PaSelect=1, OutputPower=14, MaxPower=7) */
    reg_write(REG_PA_CONFIG, 0x80 | 0x70 | 0x0E);

    /* ModemConfig1: BW (bw_idx<<4) | CR=4/5 (001<<1) | explicit header (0) */
    reg_write(REG_MODEM_CFG1, (bw_idx << 4) | (0x01 << 1) | 0x00);

    /* ModemConfig2: SF (sf<<4) | CRC on (0x04) */
    reg_write(REG_MODEM_CFG2, (sf << 4) | 0x04);

    /* Preamble 8 symbols */
    reg_write(REG_PREAMBLE_LSB, 8);

    /* Private sync word (0x12); 0x34 reserved for LoRaWAN */
    reg_write(REG_SYNC_WORD, 0x12);

    /* FIFO bases: TX=0x00, RX=0x00 (we never use both at once) */
    reg_write(REG_FIFO_TX_BASE, 0x00);
    reg_write(REG_FIFO_RX_BASE, 0x00);
}

static void sx_send(const uint8_t *data, uint8_t len) {
    reg_write(REG_OP_MODE, OP_LONG_RANGE | OP_STDBY);
    reg_write(REG_FIFO_ADDR, 0x00);
    burst_write(REG_FIFO, data, len);
    reg_write(REG_PAYLOAD_LEN, len);
    reg_write(REG_DIO_MAPPING1, 0x40);  /* DIO0 = TxDone */
    reg_write(REG_OP_MODE, OP_LONG_RANGE | OP_TX);

    /* Poll IRQ flag — production would use a GPIO IRQ on DIO0 */
    while ((reg_read(REG_IRQ_FLAGS) & IRQ_TX_DONE) == 0) usleep(1000);
    reg_write(REG_IRQ_FLAGS, 0xFF);  /* clear all flags */
    reg_write(REG_OP_MODE, OP_LONG_RANGE | OP_STDBY);
}

static int sx_recv(uint8_t *buf, uint8_t maxlen, int8_t *snr, int16_t *rssi) {
    reg_write(REG_DIO_MAPPING1, 0x00);  /* DIO0 = RxDone */
    reg_write(REG_FIFO_ADDR, 0x00);
    reg_write(REG_OP_MODE, OP_LONG_RANGE | OP_RX_CONT);

    while ((reg_read(REG_IRQ_FLAGS) & IRQ_RX_DONE) == 0) usleep(10000);

    uint8_t n = reg_read(REG_RX_NB_BYTES);
    if (n > maxlen) n = maxlen;

    uint8_t rx_cur = reg_read(0x10);          /* FifoRxCurrentAddr */
    reg_write(REG_FIFO_ADDR, rx_cur);
    burst_read(REG_FIFO, buf, n);

    *snr  = ((int8_t)reg_read(REG_PKT_SNR)) / 4;
    *rssi = -157 + reg_read(REG_PKT_RSSI);    /* HF port; subtract 164 for LF */

    reg_write(REG_IRQ_FLAGS, 0xFF);
    return n;
}

int main(int argc, char **argv) {
    spi_fd = open("/dev/spidev0.0", O_RDWR);
    uint8_t mode = SPI_MODE_0;
    ioctl(spi_fd, SPI_IOC_WR_MODE, &mode);

    sx_reset();
    uint8_t ver = reg_read(REG_VERSION);
    if (ver != 0x12) { fprintf(stderr, "SX1276 not found (got 0x%02x)\n", ver); return 1; }
    printf("SX1276 detected\n");

    sx_init(868100000, /*SF*/ 7, /*BW=125 kHz idx=*/ 0x07);

    if (argc > 1 && argv[1][0] == 't') {
        for (int i = 0;; i++) {
            char msg[32];
            int n = snprintf(msg, sizeof msg, "hello %d", i);
            sx_send((uint8_t *)msg, n);
            printf("TX %s\n", msg);
            sleep(2);
        }
    } else {
        for (;;) {
            uint8_t buf[256]; int8_t snr; int16_t rssi;
            int n = sx_recv(buf, sizeof buf, &snr, &rssi);
            printf("RX %.*s  RSSI=%d dBm  SNR=%d dB\n", n, buf, rssi, snr);
        }
    }
}
```

What this driver shows that the framework hides:

- **Frequency programming.** The `Frf = freq × 2^19 / 32e6` formula appears nowhere in `lora-net` — it's hidden by `set_frequency()`. Here you see the raw three-byte divider write.
- **SPI access pattern.** A read is `addr & 0x7F`; a write is `addr | 0x80`. Burst FIFO read/write are sequential reads after one address byte.
- **FIFO is a 256-byte chip RAM with a pointer.** Set `FifoAddrPtr` to where you want to read/write; then read/write the FIFO register repeatedly. Easy to get wrong — `FifoTxBaseAddr` is "where TX should start," `FifoAddrPtr` is "where the next byte goes/comes from."
- **IRQ flags are level-and-cleared.** Until you write back to `REG_IRQ_FLAGS`, the next operation sees a stale flag and you think the prior TX is still in progress.
- **RSSI math is asymmetric.** HF (above 525 MHz) and LF (below) subtract different offsets. Forget the offset, your "RSSI" is meaningless.
- **The whole driver is 200 lines.** With a real GPIO IRQ on DIO0 (`libgpiod`'s `gpiod_line_event_wait`) it becomes interrupt-driven. With a small framing layer (length + CRC + sequence) it becomes a usable PHY for point-to-point telemetry.

When you read the mainline-candidate `sx127x` driver later, you'll recognize *exactly* this sequence inside `sx127x_tx_pkt()` and `sx127x_rx_handler()`, wrapped in a netdev shell. The framework adds netdev plumbing, threaded IRQs, and skb-based queueing — but the radio dance is the same twelve register writes.

### Translating to SX1262 (the chip you should use for new designs)

The same physical actions become **opcodes**:

| SX1276 register write | SX1262 command |
|---|---|
| `WriteReg(OpMode, STDBY)` | `SetStandby(STDBY_RC)` |
| `WriteReg(Frf*, ...)` | `SetRfFrequency(freq)` |
| `WriteReg(PaConfig, ...)` | `SetPaConfig(...)` + `SetTxParams(power, ramp)` |
| `WriteReg(ModemConfig*, ...)` | `SetModulationParams(SF, BW, CR, LDRO)` |
| `WriteReg(PayloadLength, n)` | `SetPacketParams(preamble, hdr_type, len, crc, iq)` |
| `WriteReg(FIFO, ...)` (burst) | `WriteBuffer(offset, data, n)` |
| `WriteReg(OpMode, TX)` | `SetTx(timeout)` |
| poll `IrqFlags` | `GetIrqStatus()` + `ClearIrqStatus()` |

Same dozen actions, different SPI shape. The Semtech "SX126x driver" reference implementation in their open-source repo is a clean read; port it from there.

## 98.7  Device tree — wiring spidev to the radio

For the user-space approach, all you need is `spidev` on the right CS:

```dts
&ecspi3 {
    pinctrl-names = "default";
    pinctrl-0 = <&pinctrl_ecspi3>;
    cs-gpios = <&gpio1 20 GPIO_ACTIVE_LOW>;
    status = "okay";

    lora@0 {
        compatible = "rohm,dh2228fv";        /* the universal spidev stand-in */
        reg = <0>;
        spi-max-frequency = <1000000>;
    };
};

&gpio1 {
    /* DIO0 (IRQ) and RESET are plain GPIOs accessed via libgpiod */
};
```


> *Production note: `rohm,dh2228fv` is a development-time spidev placeholder; modern kernels print a warning when it appears in DT. See Chapter 47's `spidev` warning for the proper DT overlay path or a real-chip compatible swap.*
`/dev/spidev3.0` appears; `libgpiod` lines manage RESET and DIO0.

If you instead use the out-of-tree `sx127x-driver`:

```dts
lora@0 {
    compatible = "semtech,sx1276";
    reg = <0>;
    spi-max-frequency = <1000000>;
    reset-gpios = <&gpio1 21 GPIO_ACTIVE_LOW>;
    dio-gpios = <&gpio1 22 GPIO_ACTIVE_HIGH>,    /* DIO0 = TxDone/RxDone */
                <&gpio1 23 GPIO_ACTIVE_HIGH>;    /* DIO1 = RxTimeout */
    semtech,clock-frequency = <32000000>;
};
```

You then get `lora0` and (in some out-of-tree forks) a SOCK_DGRAM/SOCK_RAW socket interface. This path is *not* mainline; if you go here, pin your kernel version.

## 98.8  LoRaWAN vs LoRa P2P

We've covered the **PHY** (LoRa modulation). The two product paths from here:

- **LoRa P2P** — your own framing on top of the PHY. Two boards talk directly. Best for a fleet of your own devices, no gateway, no infrastructure. The user-space driver above is enough.
- **LoRaWAN** — the *MAC* on top: device addressing (DevEUI/AppEUI/AppKey), OTAA join, three classes (A polling, B beacon, C continuous-RX), regional ISM channel plans, ADR (Adaptive Data Rate). Requires a **gateway** (multi-channel concentrator like SX1301/SX1303) + a **network server** (ChirpStack, The Things Stack) + an **application server**. Best for products joining a shared network (The Things Network, Helium, private deployments).

### A LoRaWAN gateway on the i.MX6ULL

The gateway is a Linux box with a **concentrator card** (RAK2287/SX1303 SPI module, or a USB IC-880A). It listens to 8 channels in parallel — the SX1301/SX1303 is essentially 8 LoRa modems in one die — and forwards every received packet to a network server.

Stack:

```
   LoRa device  ── LoRa air ──►   Gateway
   (your SX1262)                 ┌─────────────────────────────────────┐
                                 │  i.MX6ULL                            │
                                 │  ┌───────────┐                       │
                                 │  │ SX1303    │◄── SPI ─── kernel    │
                                 │  │ concentr. │                       │
                                 │  └─────┬─────┘                       │
                                 │        │ via spidev                  │
                                 │        ▼                              │
                                 │  ┌─────────────────┐                  │
                                 │  │ lora-pkt-fwd    │  (Semtech ref)   │
                                 │  │ (user-space)    │  binds to SPI    │
                                 │  └─────┬───────────┘  forwards UDP    │
                                 │        │ UDP semtech-fwd protocol     │
                                 │        ▼                              │
                                 │  ┌─────────────────┐                  │
                                 │  │ chirpstack-gw   │  bridge to MQTT  │
                                 │  │ -bridge         │                  │
                                 │  └─────┬───────────┘                  │
                                 │        │ MQTT                         │
                                 └────────┼──────────────────────────────┘
                                          ▼
                                   ┌──────────────┐
                                   │ ChirpStack   │  (server, can run on
                                   │ network srv  │   the same box for a
                                   │ + app srv    │   private network)
                                   └──────────────┘
```

Bring-up:

```sh
# Concentrator (SX1303) on SPI
echo dtoverlay=sx1303-spi >> /boot/config.txt    # or your DT equivalent
# Build sx1302_hal (Semtech's reference; works for sx1303 too)
git clone https://github.com/Lora-net/sx1302_hal && cd sx1302_hal
make
# Edit global_conf.json: region (EU868/US915), SPI device, channel plan
./packet_forwarder/lora_pkt_fwd
# In parallel:
docker run -p 1700:1700/udp chirpstack/chirpstack-gateway-bridge
docker run chirpstack/chirpstack
```

End-to-end, an SX1262 node running OTAA-joined LoRaWAN will:

1. JoinRequest → uplinked over the air → received by 8-channel concentrator
2. → forwarded UDP to gateway-bridge
3. → bridged to MQTT
4. → received by ChirpStack network server, which validates AppKey, generates DevAddr, returns JoinAccept
5. → downlinked through gateway-bridge → packet-forwarder → over the air → node receives the JoinAccept
6. Node now sends uplinks; ChirpStack decrypts; your application server (or an MQTT subscriber) consumes them

A private LoRaWAN network on one i.MX6ULL is realistic. The kernel is involved as the SPI driver and nothing else.

## 98.9  Lab

1. **Hello, SX1276.** Wire a SX1276 module to ECSPI3 + GPIO for RESET/DIO0. Build `sx1276_min.c`. Confirm `REG_VERSION` reads `0x12`. **If it doesn't, your SPI mode/wiring is wrong — fix before continuing.**
2. **TX one packet.** Run with `t` arg; another board (or a hand-held LoRa sniffer like the RAK Wireless WisGate) should see the packet on 868.1 MHz / SF7 / BW125.
3. **RX one packet.** On the second board, run without args; observe the message and RSSI/SNR. Move the boards apart; watch RSSI drop ~6 dB per doubling of distance (free-space).
4. **Spreading-factor sweep.** Set SF7, then SF12; measure round-trip per-packet time. SF12 should be **~30× longer** than SF7. Confirm with a stopwatch.
5. **Air-time calculator sanity check.** Use Semtech's air-time calculator (or the formula from §98.2): predict air-time for SF10/BW125/CR4/5/preamble 8/payload 20. Match against your measured `TxDone` timing. Should agree within 5 %.
6. **Range walk.** With SF7/CR4/5/+17 dBm, walk away from a TX board with an RX board. Note where the packets stop being received (RSSI ≈ –123 dBm at the limit). Open-field outdoor: expect 2–5 km with a half-decent antenna.
7. **DIO0 IRQ.** Replace the `while(... & IRQ_TX_DONE)` polling with `libgpiod` edge-event wait on the DIO0 pin. TX completion latency should drop from ~1 ms polling jitter to ~tens of µs.
8. **Two boards ping-pong with sequence numbers + CRC.** Add a 4-byte header (`magic, seq_lo, seq_hi, crc8`); each side increments its `seq` on RX-success; lost packets are visible as gaps. This is a real point-to-point protocol.
9. **Switch to SX1262 (stretch).** Port `sx1276_min.c` to SX1262's command-based interface using Semtech's open driver as reference. Same physical sequence, different SPI shape.
10. **LoRaWAN gateway (capstone).** Acquire an SX1303 concentrator module (RAK2287 or similar). Bring up `sx1302_hal` + `chirpstack-gateway-bridge` + `chirpstack` on the i.MX6ULL. Provision an OTAA device. Watch the JoinRequest → JoinAccept handshake in ChirpStack's logs. Send 5 uplinks; receive them on MQTT.

## 98.10  Pitfalls

- **Transmitting without an antenna.** Will destroy the PA within a few transmissions. The chip's "safe" RFO output is +14 dBm — even that wants a load. Always have a real antenna or a 50 Ω dummy load attached during TX.
- **Wrong PA output selected on SX1276.** `PA_BOOST` (RFO_HF/RFO_LF pins) vs `RFO` pin. The schematic must route exactly one to the antenna. Sending +20 dBm into the wrong pin is permanent damage.
- **Sync word collision with LoRaWAN.** Private LoRa networks must use sync 0x12. The LoRaWAN value 0x34 is reserved; using it in P2P will make every LoRaWAN gateway in earshot try to demodulate your packets and crash.
- **Bandwidth misnumbering.** The `BW` field is an *index* into a table, not the bandwidth in kHz. `0x07 = 125 kHz`, `0x08 = 250 kHz`, `0x09 = 500 kHz`. Putting `125` in the register sets ~3.9 MHz — out of spec, doesn't work.
- **SF12 timing.** A SF12/BW125 packet of 51 bytes takes ~2.3 seconds. Your `while(... & TX_DONE)` poll loop must allow for it; many sample drivers time out at 1 s. Use 5+ seconds or compute from the air-time formula.
- **Duty cycle violations.** EU 868 g1 sub-band is **1 %**. At SF12, that's two packets per minute, period. Build a duty-cycle tracker in firmware or you'll be illegally transmitting and the regulator can fine you.
- **TCXO not started.** SX1262 with TCXO: you must call `SetDIO3AsTCXOCtrl(voltage, delay)` before any frequency operation. Skip it and the radio's PLL drifts → packets demodulate with high error or not at all on SF11/SF12.
- **`Sleep` does not erase state on SX127x — but on SX1262 Cold Start it does.** SX127x in Sleep mode preserves register state and consumes ~200 nA. SX1262 in Cold Start (`SetSleep(0x00)`) loses configuration — you must reconfigure on wake. Check the datasheet.
- **Single-chip "RF switch destroyed" failure.** A common module fault: the chip transmits OK at first but receive sensitivity is –80 dBm instead of –123 dBm — the internal/external RF switch was killed during a TX-into-open. Detect by measuring RSSI of a known close transmitter; if it's >40 dB worse than spec, the switch is gone.
- **Out-of-tree driver kernel-version pinning.** `sx127x-driver` is community-maintained; major kernel updates break it. If you go the kernel-netdev route, pin your kernel until you have time to forward-port.
- **Concentrator SPI clock too fast.** SX1303 SPI tops out at 8 MHz; some carrier boards expose 50 MHz `ecspi`. Set `spi-max-frequency = <8000000>;` or it works in the lab and fails on customer hardware.
- **Channel plan mismatch.** US915 has 64 uplink channels in 8 sub-bands; EU868 has 3 mandatory + 5 optional. A node configured for EU and a gateway for US never talk. The mistake is invisible until you check both sides' `region` parameter.

## 98.11  Going deeper

- **Semtech SX127x datasheet** + **SX126x datasheet** — the canonical reference for register / command behavior.
- **`semtech-prh/sx127x-driver` and `lora-net/lora-modules`** — out-of-tree Linux drivers; read the `sx127x.c` / `sx126x.c` source for "what a netdev wrap would look like."
- **`Lora-net/sx1302_hal`** — Semtech's reference packet-forwarder for SX1301/SX1302/SX1303 concentrators; this is what every commercial LoRaWAN gateway ships.
- **ChirpStack** (`chirpstack/chirpstack`) — open-source LoRaWAN network + application server, designed to run on a small Linux box.
- **LoRa Alliance LoRaWAN Specification** (1.0.3 / 1.1) — the MAC standard.
- **Semtech AN1200.22 — LoRa Modulation Basics** — the formal CSS math (a more rigorous version of §98.2).
- **The Things Industries documentation** — practical channel-plan and ADR notes for production fleets.
- **Ch 99** — the *non*-LoRa sub-GHz alternatives (nRF24L01, CC1101) when you don't need range but you do need throughput.
- **Ch 95** — for comparison: BLE's GATT/HCI model vs LoRaWAN's MAC/PHY split.

---

> **End of Chapter 98 — LoRa.** Group M starts here: long-range and specialty wireless where the kernel is "just" the SPI controller and the protocol stack lives in user space. The next two chapters cover the alternatives — proprietary sub-GHz FSK (nRF24L01 / CC1101) and the IEEE 802.15.4 family (ZigBee, Thread).

> Next chapter: **Chapter 99 — Sub-GHz proprietary radios (nRF24L01, CC1101).** Same sub-GHz spectrum, FSK instead of CSS, much higher throughput, no LoRaWAN-style infrastructure.
