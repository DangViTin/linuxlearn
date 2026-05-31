---
chapter: 99
title: Sub-GHz proprietary radios (nRF24L01, CC1101, CC1200)
part: VII — Device cookbook
estimated_pages: 18
status: draft
---

# Chapter 99 — Sub-GHz proprietary

> **What:** **non-LoRa short-range radios** for fleets that need higher throughput than LoRa or have no infrastructure: **Nordic nRF24L01+** (2.4 GHz, 250 kbps – 2 Mbps GFSK, the dominant cheap mesh radio), **TI CC1101** (sub-GHz 300–928 MHz multi-mode), **TI CC1200** (newer, lower phase noise, higher data rate, better Wi-SUN candidate). We dissect each chip's SPI command/register model, the **Enhanced ShockBurst** auto-ACK in nRF24, the CC1101 state machine, write a 200-line nRF24 P2P driver from scratch in user space, then wire DT for the existing kernel drivers where they exist.
> **Why:** LoRa (Ch 98) buys range with bandwidth. The opposite trade — sub-second latency, multi-kbps throughput, no MAC stack, no infrastructure, $1–4 BOM — is what nRF24L01 and CC1101 give you. Every consumer remote control, garage opener, weather station, and dozens-of-nodes IoT prototype uses one of these. The kernel has *some* support (`nrf24` is out-of-tree; CC1101 has an old in-tree driver), but as with LoRa, most production stacks live in user space against `spidev`. Understanding the chip's state machine + SPI command shape is everything.
> **Focus:** **these chips are state machines you drive with SPI commands; the radio behavior is determined by which state you're in, not by individual register values**. nRF24's state machine has 7 states (Power-Down, Standby-I, Standby-II, RX, TX, etc.); CC1101's has 13. Almost every "the chip doesn't work" bug is the chip being in the wrong state — TX commanded from RX, FIFO read while still receiving, command issued before the previous one's settling time elapsed. Master the state diagram and the radios are trivial.

## 99.1  Choosing the chip

| | nRF24L01+ | CC1101 | CC1200 |
|---|---|---|---|
| Frequency | 2.4 GHz ISM | 300–348 / 387–464 / 779–928 MHz | 164–192 / 274–320 / 410–480 / 820–960 MHz |
| Modulation | GFSK | OOK / 2-FSK / 4-FSK / GFSK / MSK | 2-FSK / 4-FSK / OOK / GFSK / 4-GFSK / MSK |
| Data rate | 250 kbps / 1 / 2 Mbps | 0.6–500 kbps | 0.6 kbps – 1.25 Mbps |
| Range (open, +0 dBm) | 50–200 m | 100–500 m | 500 m – 1.5 km |
| Range (open, +20 dBm w/ PA) | 1 km | 1–2 km | 2–5 km |
| RX current | 12.6 mA | 14.7 mA | 17 mA |
| Sleep | 900 nA | 200 nA | 120 nA |
| Address-aware? | yes (`Enhanced ShockBurst`) | no (raw FSK only) | no |
| Auto-ACK | yes (the killer feature) | no (must build in software) | no |
| Multi-receiver pipes | 6 simultaneous PRX from 1 PTX | none | none |
| Cost | $0.80 (module) | $1.20 | $3.50 |
| Kernel driver | out-of-tree `nrf24` | in-tree `cc1101` (legacy, broken on modern kernels) | none |
| Use case | low-cost mesh, RC, hub-and-spoke | sub-GHz remotes, garage door, smart-home | longer-range industrial, Wi-SUN |

**Pick guide:**
- **nRF24L01+** — when 2.4 GHz is acceptable, you have 1–32 nodes, and the auto-ACK + pipes feature saves you from building a MAC. Caveat: 2.4 GHz is crowded; WiFi will eat you in a busy office.
- **CC1101** — sub-GHz remote-control style, when 2.4 GHz coexistence is a problem, you can tolerate building your own ACK protocol, and BOM cost is critical. Most "smart" home AC remotes, weather stations, and security sensors use this.
- **CC1200** — the modern CC1101 successor; pick this for new designs over CC1101 (better phase noise, easier registers, mainstream Wi-SUN support).

## 99.2  nRF24L01+ — the dominant cheap radio

### State machine

```
              ┌──────────────────┐
              │   Power Down     │ ◄──── PWR_UP=0 (CONFIG reg)
              │   1 µA           │
              └────────┬─────────┘
                       │ PWR_UP=1
                       ▼
              ┌──────────────────┐
              │   Crystal startup│  (~1.5 ms)
              └────────┬─────────┘
                       ▼
              ┌──────────────────┐
              │   Standby-I      │ ◄──┐  CE=0
              │   26 µA          │    │
              └──────┬─────┬─────┘    │
            PRIM_RX=0│     │PRIM_RX=1 │
                CE=1 │     │CE=1      │
                     ▼     ▼          │
              ┌──────┐    ┌──────┐    │
              │  TX  │    │  RX  │────┘
              │ Mode │    │ Mode │
              │ ~12 mA    │ ~13 mA
              └──────┘    └──────┘
```

The two GPIO-style control pins:
- **CSN** (Chip Select Not) — SPI CS, frames each command.
- **CE** (Chip Enable) — controls active TX/RX. CE=0 means "go to Standby-I and hold there"; CE=1 means "start TX (if PRIM_RX=0) or stay in RX (if PRIM_RX=1)."

The state-transition rules that bite every newcomer:
- Switching between TX and RX requires going through Standby-I (`CE=0`, wait 130 µs, set `PRIM_RX`, `CE=1`).
- The TX FIFO is loaded *before* CE goes high; pulsing CE for ≥10 µs triggers transmission of one packet.

### SPI commands

The nRF24 has **commands** (not direct register writes):

| Command | Hex | Meaning |
|---|---|---|
| `R_REGISTER addr` | `0x00 \| addr` | read register addr (5 bits) |
| `W_REGISTER addr` | `0x20 \| addr` | write register |
| `R_RX_PAYLOAD` | `0x61` | read RX FIFO (1–32 bytes) |
| `W_TX_PAYLOAD` | `0xA0` | write TX FIFO |
| `FLUSH_TX` | `0xE1` | empty TX FIFO |
| `FLUSH_RX` | `0xE2` | empty RX FIFO |
| `REUSE_TX_PL` | `0xE3` | resend last TX on next CE pulse |
| `R_RX_PL_WID` | `0x60` | get length of top RX FIFO entry (dynamic payloads) |
| `W_ACK_PAYLOAD pipe` | `0xA8 \| pipe` | piggyback an ACK payload back to PTX |
| `W_TX_PAYLOAD_NOACK` | `0xB0` | TX with auto-ACK disabled for this frame |
| `NOP` | `0xFF` | read STATUS register only |

Every SPI transaction returns the STATUS register in the first byte — useful "for free" status polling.

Key registers (5-bit addresses):

| Addr | Name | Purpose |
|---|---|---|
| 0x00 | CONFIG | EN_CRC, CRCO, PWR_UP, PRIM_RX |
| 0x01 | EN_AA | per-pipe Enhanced ShockBurst auto-ACK enable |
| 0x02 | EN_RXADDR | per-pipe RX enable |
| 0x03 | SETUP_AW | address width (3/4/5 bytes) |
| 0x04 | SETUP_RETR | ARD (auto-retry delay), ARC (auto-retry count) |
| 0x05 | RF_CH | RF channel (0–125, freq = 2400 + channel MHz) |
| 0x06 | RF_SETUP | PA power (0/-6/-12/-18 dBm), data rate (1 / 2 / 250 kbps) |
| 0x07 | STATUS | RX_DR, TX_DS, MAX_RT, RX_P_NO, TX_FULL |
| 0x08 | OBSERVE_TX | retransmission + lost-packet counts |
| 0x09 | RPD (CD on non-plus) | received-power detector |
| 0x0A–0x0F | RX_ADDR_P0..P5 | per-pipe RX address (5 bytes for P0,P1; 1 byte for P2..P5) |
| 0x10 | TX_ADDR | TX address (must match PRX's RX_ADDR_P0 for auto-ACK) |
| 0x11–0x16 | RX_PW_P0..P5 | static payload length per pipe (1–32) |
| 0x17 | FIFO_STATUS | TX_REUSE, TX_FULL, TX_EMPTY, RX_FULL, RX_EMPTY |
| 0x1C | DYNPD | per-pipe dynamic-payload enable |
| 0x1D | FEATURE | EN_DPL (dynamic payloads), EN_ACK_PAY, EN_DYN_ACK |

### Enhanced ShockBurst — the killer feature

ShockBurst is the auto-retransmit + auto-ACK layer built into the chip. Setup:

1. PTX writes a frame; sets `EN_AA` on pipe 0 (or whichever).
2. PTX pulses CE; chip transmits.
3. Chip *automatically* flips to RX, listens for an ACK (an empty frame on the same address).
4. If ACK received within ARD (`SETUP_RETR`), `TX_DS` IRQ — success.
5. If not, retry up to ARC times; if still no ACK, `MAX_RT` IRQ — failure.

The PRX side automatically generates the ACK on receipt. The CPU doesn't run code for this round trip — it's all in chip silicon. Result: reliable point-to-point delivery at sub-millisecond latency, with zero MAC code on either side.

You can even piggyback an **ACK payload**: PRX's `W_ACK_PAYLOAD` queues a payload that rides back inside the ACK frame, giving 32-byte bidirectional half-duplex with one transmit + auto-ACK pair.

This is why nRF24 dominates the BOM-conscious low-rate radio market.

### Six receive pipes — the multi-PRX, one-PTX pattern

A single nRF24 in RX mode can listen for 6 different addresses simultaneously (pipes P0..P5). The canonical use:

```
   Hub (one nRF24 in PRX mode)
   ├─ Pipe 0: 0xE7E7E7E7E7  (default broadcast)
   ├─ Pipe 1: 0xC2C2C2C2C2  (Node A)
   ├─ Pipe 2:           D3  (Node B — shares 4-byte prefix with P1)
   ├─ Pipe 3:           D4  (Node C)
   ├─ Pipe 4:           D5  (Node D)
   └─ Pipe 5:           D6  (Node E)
```

Pipes 2–5 share the high 4 address bytes with pipe 1; only the last byte differs. So you get one hub talking to 5 satellites, each individually addressed and auto-ACKed. Add ACK payloads and the hub can send commands back inside each ACK — a 6-node star network without a MAC layer.

## 99.3  Wiring an nRF24 to the i.MX6ULL

Six wires + power:

```
      ┌─────────┐                          ┌──────────┐
ECSPI ┤ MOSI    ├──────────────────────────┤ MOSI     │
      │ MISO    ├──────────────────────────┤ MISO     │  nRF24L01+
      │ SCK     ├──────────────────────────┤ SCK      │
      │ CS (gpio├──────────────────────────┤ CSN      │
GPIO  ┤ CE (gpio├──────────────────────────┤ CE       │
GPIO  ┤ IRQ     ├──────────────────────────┤ IRQ#     │  (active low)
      │         │   3.3 V  ── 10 µF + 100 nF ┤ VDD     │  ← critical for TX bursts
      │         │   GND ─────────────────────┤ GND     │
      └─────────┘                          └──────────┘
```

The IRQ pin is active-low; it asserts on `RX_DR`, `TX_DS`, or `MAX_RT`. Reading `STATUS` and writing 1 back to the bit clears the interrupt.

**Power supply gotcha**: the 1 Mbps TX burst draws ~12 mA peaks at the rail; without the 10 µF bulk + 100 nF local decoupling, the supply droops and the next TX corrupts. The single most common reason "the modules I bought don't work."

## 99.4  How the out-of-tree nRF24 kernel drivers actually work

There are two community kernel drivers:
- **`nrf24` by Marcin Ciupak** (out-of-tree, GitHub `nRF24/nRF24L01_plus_Linux_Driver`). Presents the chip as a char device per pipe (`/dev/nrf24-pipe0`...). Read = receive; write = transmit.
- **`nrf24-network` patches by Andre Renaud** (one attempt to make it netdev; never accepted upstream).

Walk of the char-device driver's TX path (paraphrased from `nrf24/nrf24.c`):

```c
static ssize_t nrf24_write(struct file *f, const char __user *buf,
                           size_t len, loff_t *off) {
    struct nrf24_pipe *p = f->private_data;
    if (len > 32) return -EINVAL;
    if (copy_from_user(p->tx_buf, buf, len)) return -EFAULT;
    mutex_lock(&p->dev->tx_lock);
    nrf24_set_mode_tx(p->dev);                 /* PRIM_RX=0; CE=0 (Standby-I) */
    nrf24_set_tx_addr(p->dev, p->cfg.address); /* TX_ADDR + RX_ADDR_P0 (for ACK) */
    nrf24_send_packet(p->dev, p->tx_buf, len); /* W_TX_PAYLOAD + pulse CE */
    wait_event_interruptible_timeout(
        p->dev->tx_done_wait,
        atomic_read(&p->dev->tx_status) != TX_PENDING, ARD * (ARC + 1));
    int status = atomic_read(&p->dev->tx_status);
    nrf24_set_mode_rx(p->dev);                 /* PRIM_RX=1 again */
    mutex_unlock(&p->dev->tx_lock);
    return (status == TX_SUCCESS) ? len : -EIO;
}
```

The threaded IRQ handler:

```c
static irqreturn_t nrf24_irq(int irq, void *data) {
    struct nrf24_device *d = data;
    uint8_t status = nrf24_cmd(d, NOP, NULL, 0, NULL, 0);
    if (status & STATUS_TX_DS)  atomic_set(&d->tx_status, TX_SUCCESS);
    if (status & STATUS_MAX_RT) atomic_set(&d->tx_status, TX_FAILED);
    if (status & STATUS_RX_DR) {
        uint8_t pipe = (status >> 1) & 0x07;
        uint8_t len;
        nrf24_cmd(d, R_RX_PL_WID, NULL, 0, &len, 1);
        nrf24_cmd(d, R_RX_PAYLOAD, NULL, 0, d->rx_buf, len);
        kfifo_in(&d->pipes[pipe].rx_fifo, d->rx_buf, len);
        wake_up_interruptible(&d->pipes[pipe].rx_wait);
    }
    nrf24_cmd(d, W_REGISTER | STATUS, &status, 1, NULL, 0);  /* clear flags */
    wake_up_interruptible(&d->tx_done_wait);
    return IRQ_HANDLED;
}
```

The architecture: one chip, six per-pipe char devices, one shared TX lock (because the chip can only TX to one address at a time), one IRQ thread, a kfifo per pipe holding received bytes. Read() blocks on the kfifo; write() pumps the TX path.

That's a lot of machinery to handle six addresses on one chip. The from-scratch version below skips it and uses `spidev` + libgpiod directly.

## 99.5  From scratch — a user-space nRF24 driver in C

nrf24_min.c:

```c
/* Minimal user-space nRF24L01+ driver. PTX or PRX role at startup.
 * Pair: board A as PTX (sends "ping %d"); board B as PRX (prints with RSSI).
 */
#include <fcntl.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>
#include <sys/ioctl.h>
#include <linux/spi/spidev.h>
#include <gpiod.h>

#define CMD_R_REG     0x00
#define CMD_W_REG     0x20
#define CMD_R_RX_PL   0x61
#define CMD_W_TX_PL   0xA0
#define CMD_FLUSH_TX  0xE1
#define CMD_FLUSH_RX  0xE2
#define CMD_NOP       0xFF

#define REG_CONFIG    0x00
#define REG_EN_AA     0x01
#define REG_EN_RXADDR 0x02
#define REG_SETUP_AW  0x03
#define REG_SETUP_RETR 0x04
#define REG_RF_CH     0x05
#define REG_RF_SETUP  0x06
#define REG_STATUS    0x07
#define REG_RX_ADDR_P0 0x0A
#define REG_TX_ADDR   0x10
#define REG_RX_PW_P0  0x11
#define REG_DYNPD     0x1C
#define REG_FEATURE   0x1D

static int spi_fd;
static struct gpiod_line *ce_line, *irq_line;

static uint8_t cmd(uint8_t opcode, const uint8_t *tx, uint8_t *rx, int n) {
    uint8_t buf_tx[33], buf_rx[33];
    buf_tx[0] = opcode;
    if (tx) memcpy(&buf_tx[1], tx, n);
    else    memset(&buf_tx[1], 0, n);
    struct spi_ioc_transfer t = {
        .tx_buf=(unsigned long)buf_tx, .rx_buf=(unsigned long)buf_rx,
        .len=n+1, .speed_hz=4000000,
    };
    ioctl(spi_fd, SPI_IOC_MESSAGE(1), &t);
    if (rx) memcpy(rx, &buf_rx[1], n);
    return buf_rx[0];  /* STATUS comes back in the first byte, free */
}

static uint8_t reg_read(uint8_t a) {
    uint8_t v;
    cmd(CMD_R_REG | (a & 0x1F), NULL, &v, 1);
    return v;
}
static void reg_write(uint8_t a, uint8_t v) {
    cmd(CMD_W_REG | (a & 0x1F), &v, NULL, 1);
}
static void reg_write_n(uint8_t a, const uint8_t *v, int n) {
    cmd(CMD_W_REG | (a & 0x1F), v, NULL, n);
}

static void ce(int on) { gpiod_line_set_value(ce_line, on); }

static void nrf_init(int as_prx) {
    /* Reset config: CRC=2bytes, PWR_UP=1, PRIM_RX as requested */
    reg_write(REG_CONFIG, 0x0C | 0x02 | (as_prx ? 0x01 : 0x00));
    usleep(2000);                            /* crystal settling */

    reg_write(REG_SETUP_AW, 0x03);           /* 5-byte addresses */
    reg_write(REG_RF_CH, 76);                /* 2476 MHz — away from WiFi ch1/6/11 */
    reg_write(REG_RF_SETUP, 0x06);           /* 1 Mbps, 0 dBm */
    reg_write(REG_EN_AA, 0x01);              /* auto-ACK on pipe 0 */
    reg_write(REG_EN_RXADDR, 0x01);          /* RX on pipe 0 */
    reg_write(REG_SETUP_RETR, 0x3F);         /* ARD=1000us, ARC=15 retries */

    uint8_t addr[5] = { 0xE7, 0xE7, 0xE7, 0xE7, 0xE7 };
    reg_write_n(REG_RX_ADDR_P0, addr, 5);
    reg_write_n(REG_TX_ADDR,    addr, 5);
    reg_write(REG_RX_PW_P0, 32);             /* static 32-byte payload */

    cmd(CMD_FLUSH_TX, NULL, NULL, 0);
    cmd(CMD_FLUSH_RX, NULL, NULL, 0);
    reg_write(REG_STATUS, 0x70);             /* clear RX_DR/TX_DS/MAX_RT */
}

static int nrf_send(const uint8_t *data, int len) {
    ce(0);
    cmd(CMD_W_TX_PL, data, NULL, len);
    ce(1);
    usleep(15);                              /* >10 µs trigger pulse */
    ce(0);
    /* poll status until TX_DS or MAX_RT */
    for (int i = 0; i < 100; i++) {
        uint8_t st = cmd(CMD_NOP, NULL, NULL, 0);
        if (st & 0x20) { reg_write(REG_STATUS, 0x20); return 0; }   /* TX_DS */
        if (st & 0x10) {                                            /* MAX_RT */
            reg_write(REG_STATUS, 0x10);
            cmd(CMD_FLUSH_TX, NULL, NULL, 0);
            return -1;
        }
        usleep(1000);
    }
    return -2;
}

static int nrf_recv(uint8_t *buf, int maxlen) {
    ce(1);  /* enter RX */
    for (;;) {
        uint8_t st = cmd(CMD_NOP, NULL, NULL, 0);
        if (st & 0x40) {                                            /* RX_DR */
            int len = (maxlen > 32) ? 32 : maxlen;
            cmd(CMD_R_RX_PL, NULL, buf, len);
            reg_write(REG_STATUS, 0x40);
            ce(0);
            return len;
        }
        usleep(1000);
    }
}

int main(int argc, char **argv) {
    spi_fd = open("/dev/spidev0.0", O_RDWR);
    uint8_t mode = SPI_MODE_0;
    ioctl(spi_fd, SPI_IOC_WR_MODE, &mode);

    struct gpiod_chip *chip = gpiod_chip_open("/dev/gpiochip0");
    ce_line  = gpiod_chip_get_line(chip, 20);
    irq_line = gpiod_chip_get_line(chip, 21);
    gpiod_line_request_output(ce_line, "nrf24-ce", 0);
    gpiod_line_request_input(irq_line, "nrf24-irq");

    int as_prx = (argc > 1 && argv[1][0] == 'r');
    nrf_init(as_prx);

    if (as_prx) {
        printf("Listening...\n");
        for (;;) {
            uint8_t buf[32];
            int n = nrf_recv(buf, 32);
            printf("RX: %.*s\n", n, buf);
        }
    } else {
        for (int i = 0; ; i++) {
            char msg[32];
            int n = snprintf(msg, 32, "ping %d", i);
            int r = nrf_send((uint8_t *)msg, n);
            printf("TX %s [%s]\n", msg, r == 0 ? "ACK" : "no-ACK");
            sleep(1);
        }
    }
}
```

Two boards, same binary, one with `r` arg and one without — instant 1 Mbps ACKed point-to-point link. Add `OBSERVE_TX` reading to see retry counts; add multi-pipe addresses to make a hub.

## 99.6  CC1101 — sub-GHz state-machine radio

CC1101 is harder to use than nRF24L01 because TI gives you the modulator/demodulator + framing primitives but **no auto-ACK**. You build the MAC.

### State machine (13 states)

```
   SLEEP ──► IDLE ──► CALIBRATE ──► SETTLING ──► RX
                ▲                              │
                │                              │ packet received
                │                              ▼
                │                          RXFIFO_OVERFLOW (error)
                │
                ├──► TX ──► TXFIFO_UNDERFLOW (error)
                ▼
            FSTXON (frequency synth on, ready to TX without re-cal)
```

Command strobes (single-byte SPI):
- `SRES` (0x30) reset
- `SCAL` (0x33) calibrate frequency synthesizer
- `SRX` (0x34) enter RX
- `STX` (0x35) enter TX
- `SIDLE` (0x36) leave RX/TX → IDLE
- `SFRX` (0x3A) flush RX FIFO
- `SFTX` (0x3B) flush TX FIFO

Configuration is ~40 registers (IOCFG2/1/0, FIFOTHR, SYNC1/0, PKTLEN, PKTCTRL1/0, ADDR, CHANNR, FSCTRL1/0, FREQ2/1/0, MDMCFG4/3/2/1/0, DEVIATN, MCSM2/1/0, FOCCFG, BSCFG, AGCCTRL2/1/0, ...). TI ships **SmartRF Studio** which generates the register dump for any desired modulation / data rate / deviation — you'll absolutely use it.

The killer detail: registers are write-once and survive across IDLE → RX/TX transitions, so you configure at startup and then just strobe `SRX` / `STX` to flip mode.

### Walk of the kernel CC1101 driver

The in-tree `drivers/net/wireless/ti/cc1101.c` (an out-of-tree fork, never merged; *the in-tree wireless dir does not contain this — verify with current kernel*) follows a pattern similar to nRF24: SPI device, GPIO IRQ (GDO0 = pkt_rx, GDO2 = chip_ready), char device. The full driver is ~1500 lines because it implements packet framing + length-byte vs fixed-length modes + address filtering — features the chip supports in hardware but the driver must enable per use case.

The most useful CC1101 starting point is **`elechouse/CC1101` on GitHub** (Arduino-derived but C99) — clean code that walks register init → packet send → receive. Port that to user space on `spidev` + libgpiod and you have a working sub-GHz radio in ~300 lines.

### A 30-line user-space CC1101 send

```c
/* Skeleton — assumes you have generated reg_table[] via SmartRF Studio. */
static const uint8_t reg_table[][2] = {
    {0x00, 0x29}, /* IOCFG2: GDO2 = chip-ready */
    {0x02, 0x06}, /* IOCFG0: GDO0 = pkt-received */
    {0x07, 0xFF}, /* PKTCTRL1: address filter + status appended */
    {0x08, 0x05}, /* PKTCTRL0: variable length, CRC, whitening */
    {0x0A, 0xAA}, /* ADDR (our address) */
    /* ... 40 lines from SmartRF Studio ... */
    {0xFF, 0xFF}, /* end */
};

static void cc1101_init(void) {
    strobe(SRES); usleep(1000);
    for (int i = 0; reg_table[i][0] != 0xFF; i++)
        reg_write(reg_table[i][0], reg_table[i][1]);
    strobe(SCAL);
}

static void cc1101_send(uint8_t dst, const uint8_t *data, int n) {
    strobe(SIDLE);
    strobe(SFTX);
    uint8_t hdr[2] = { n + 1, dst };          /* length, destination */
    burst_write(0x3F | 0x40, hdr, 2);         /* 0x3F = TX FIFO */
    burst_write(0x3F | 0x40, data, n);
    strobe(STX);
    while ((reg_read(0x35) & 0x70) != 0)      /* MARCSTATE != IDLE */
        usleep(100);
}
```

CC1200 is essentially CC1101 with a cleaner register set and higher symbol rates — the same template fits.

## 99.7  Device tree examples

For the user-space approach (`spidev` + libgpiod), the DT is just a `spidev` slot:

```dts
&ecspi3 {
    cs-gpios = <&gpio4 26 GPIO_ACTIVE_LOW>;
    status = "okay";

    nrf24@0 {
        compatible = "rohm,dh2228fv";   /* spidev stand-in */
        reg = <0>;
        spi-max-frequency = <8000000>;  /* nRF24 max 10 MHz */
    };
};

&gpio4 {
    /* CE, IRQ — accessed via libgpiod */
};
```

For the `nrf24` out-of-tree driver:

```dts
nrf24@0 {
    compatible = "nordic,nrf24l01p";
    reg = <0>;
    spi-max-frequency = <8000000>;
    ce-gpios = <&gpio4 27 GPIO_ACTIVE_HIGH>;
    interrupts-extended = <&gpio4 28 IRQ_TYPE_EDGE_FALLING>;
};
```

## 99.8  When to pick CC1101 vs nRF24L01

| Scenario | Pick |
|---|---|
| 1-PTX, ≤6 PRX, BOM critical, 2.4 GHz OK | **nRF24L01+** (auto-ACK + pipes do the MAC) |
| Sub-GHz, no MAC needed (each device transmits + I'll dedupe in app) | **CC1101** |
| Coexistence with WiFi a worry | **CC1101** (sub-GHz, less crowded) |
| Need 1+ km range without LoRa | CC1101 + PA + LNA module (E07 series) or **CC1200** |
| Need range *and* multi-node + auto-ACK | LoRa P2P (Ch 98) — neither nRF24 nor CC1101 gives both |
| 802.15.4 / ZigBee / Thread | not these — Ch 100 |

## 99.9  Lab

1. **nRF24 identify.** Wire 2 boards, each with nRF24 module. Read `CONFIG` (default `0x08`), verify SPI works.
2. **PTX ↔ PRX.** Build `nrf24_min.c`; one board as `r`, one without. Confirm ACKs at 1 m. `OBSERVE_TX` should show 0 retries.
3. **Range walk.** Move boards apart. Note where ACK rate drops below 90 %. Plot retry counts (`OBSERVE_TX[3:0]`) vs distance.
4. **Multi-pipe hub.** 1 hub (PRX) + 3 satellites (each PTX with a different `TX_ADDR`). Hub listens on pipes 1, 2, 3. Each satellite sends every 2 s; hub prints `pipe=N msg=...`. Add ACK payloads so the hub replies inside each ACK.
5. **WiFi co-existence test.** Run hub on channel 76 (2476 MHz). Then run `iperf3` on the same i.MX6ULL via WiFi. Watch retry counts. Move to channel 100 (2500 MHz, above WiFi band). Compare.
6. **CC1101 with SmartRF Studio.** Download SmartRF Studio (free, Windows/Linux); generate a register table for 868 MHz / 4-FSK / 38.4 kbps; flash that table to a CC1101 module. Confirm a packet exchange between two boards.
7. **CC1101 build-your-own-ACK.** CC1101 has no auto-ACK; add a 2-byte sequence + 1-byte ACK frame in user space. Measure round-trip vs nRF24's hardware ACK at similar conditions.
8. **Bridge test.** Two networks: nRF24 satellites + an i.MX6ULL hub bridging them to MQTT. Sensor data via nRF24 → JSON → mosquitto → Grafana.

## 99.10  Pitfalls

- **nRF24 vs nRF24+ clones.** The "+" variant added 250 kbps data rate and is what most modules sell. Some Chinese clones (NRF24L01 RFM73 etc.) drop quirks. Verify with `CONFIG` default = 0x08 and the auto-ACK setting.
- **Bad VDD decoupling.** Without 10 µF bulk + 100 nF, TX bursts droop the rail, all packets MAX_RT fail. The single most common nRF24 problem.
- **CE pulse too short.** ≥10 µs is the spec. On a slow CPU + sysfs GPIO you'll comfortably exceed that; on libgpiod with cached lines or an FPGA-fast GPIO it can be 1 µs and the chip never enters TX.
- **TX_ADDR ≠ RX_ADDR_P0.** The PTX's `RX_ADDR_P0` must equal its own `TX_ADDR` for auto-ACK to work (the ACK comes back to P0). Easy to overlook.
- **TX-then-RX without going through Standby-I.** Always `CE=0`, change `PRIM_RX`, `CE=1`. Going directly puts the chip in an undefined state.
- **CC1101 register dump from wrong frequency band.** The register table for 433 MHz won't work at 868; SmartRF Studio regenerates entirely. Don't copy/paste blindly between band setups.
- **CC1101 manual calibration needed periodically.** The frequency synth needs `SCAL` after temperature changes or long sleeps. The `MCSM*` registers can be set to auto-calibrate, but watch the timing — `MCSM0 = 0x18` means "calibrate every 4th transition from IDLE to RX/TX."
- **2.4 GHz crowded.** Every WiFi, BT, microwave oven, baby monitor uses 2.4 GHz. Sub-GHz (CC1101 433/868) is 10× quieter. Test in realistic environment, not on an isolated bench.
- **Antenna critical at sub-GHz.** A quarter-wave at 868 MHz is 86 mm. A 25 mm "stub" antenna costs you 10+ dB. Use a proper helical or PCB-trace antenna designed for the band.
- **No FCC certification path with home-made matching network.** Buying a pre-certified module (E07, RAK, etc.) saves a $20k+ FCC test cycle if you're shipping a product.

## 99.11  Going deeper

- **Nordic nRF24L01+ Product Specification v1.0** — the canonical reference, all register and state semantics.
- **TI CC1101 Datasheet** + **TI Design Note DN500** (CC1101 in C). And **SmartRF Studio** for register-table generation.
- **TI CC1200 Datasheet** + Wi-SUN reference designs.
- **`nRF24/nRF24L01_plus_Linux_Driver`** (out-of-tree GitHub) — char-device driver, useful for "what does a kernel driver for this look like."
- **`elechouse/CC1101`** — clean reference C library.
- **`tmrh20/RF24` / `RF24Network` / `RF24Mesh`** — Arduino-world but readable; the RF24Mesh layer shows how to build a multi-hop MAC over nRF24's PHY+ACK.
- **Ch 98** for the LoRa-vs-FSK trade-off.
- **Ch 100** for IEEE 802.15.4 (Thread/ZigBee) as the certified-network alternative.

---

> Next chapter: **Chapter 100 — ZigBee / Thread / 802.15.4** — the certified mesh-network alternatives to nRF24 ad-hoc.
