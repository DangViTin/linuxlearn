---
chapter: 101
title: UWB ranging (DWM1000, DWM3000, NCJ29D5)
part: VII — Device cookbook
estimated_pages: 16
status: draft
---

# Chapter 101 — UWB ranging

> **What:** **Ultra-wideband** (UWB) two-way ranging for centimetre-accuracy indoor positioning. Three radios: **Qorvo (Decawave) DWM1000** (the classic, IEEE 802.15.4-2011 UWB), **DWM3000** (newer, FiRa/Apple-AirTag-compatible, lower power, 802.15.4-2020), **NXP NCJ29D5** (automotive-grade UWB for car access). On the i.MX6ULL we wire DWM3000 over SPI, dissect the IEEE 802.15.4 UWB frame, walk the Qorvo "DW3xxx Software API" reference driver, write a 300-line user-space two-way-ranging (TWR) client from scratch, and demonstrate 3-anchor TDoA for 2-D position.
> **Why:** every modern phone (iPhone 11+, Galaxy S21+ Ultra, Pixel 6 Pro+) has UWB. Logistics warehouses are deploying UWB for forklift / asset tracking. Car keys (Apple Car Key, Tesla 3) use UWB to defeat relay attacks. Indoor venues use it for "blue-dot" navigation. None of this is BLE — BLE RSSI ranging is ±2 m on a good day; UWB ToF is ±10 cm. If you're building anything that *positions* objects indoors at sub-metre accuracy, this is the radio.
> **Focus:** **UWB ranging is a time-of-flight measurement, and ToF accuracy depends on how cleanly the radio captures the first arriving signal**. Multipath (the signal bouncing off walls and arriving second) corrupts ToF if the demodulator latches the wrong peak. The DW3000 has hardware-supported leading-edge detection and per-receive antenna-delay calibration; getting the calibration right is 80 % of the engineering. The protocol on top — single-sided two-way ranging vs double-sided TWR vs TDoA — is the other 20 %.

## 101.1  How UWB measures distance

UWB transmits very short (~2 ns) pulses spread over 500 MHz (or 1 GHz) of bandwidth at 6.5/8.0 GHz. Each pulse is a marker the receiver can timestamp with sub-nanosecond precision. Because radio waves travel ~30 cm/ns, **1 ns of timing error = 30 cm of range error**. UWB hardware achieves ~100 ps timestamp precision → ~3 cm range precision in theory; ~10 cm in practice after multipath.

The simplest protocol — **Single-Sided Two-Way Ranging (SS-TWR)**:

```
Initiator                Responder
   │ ── Poll msg ──►        │   t1 = TX timestamp (initiator)
   │                         │   t2 = RX timestamp (responder)
   │                         │   wait Treply (known)
   │ ◄── Resp msg ──         │   t3 = TX timestamp (responder)
   │                         │   t4 = RX timestamp (initiator)
   │                         │
   │  ToF = ((t4-t1) - Treply) / 2
   │  distance = ToF × c
```

Error: any clock drift between initiator and responder during Treply scales into the ToF estimate. For ±20 ppm crystals + 200 µs Treply, drift error is ~4 ns ≈ 1.2 m. Bad.

**Double-Sided TWR (DS-TWR)** adds a second message so both clocks measure intervals, cancelling drift:

```
Initiator               Responder
   │ ── Poll ──►            │   t1
   │                         │   t2
   │ ◄── Resp ──             │   wait T_reply1
   │ t4 ◄                    │   t3
   │                         │
   │ ── Final ──►            │   t5
   │                         │   t6
   │                         │
   │  Treply1 = t3-t2  (responder)
   │  Treply2 = t6-t5  (responder)
   │  Tround1 = t4-t1  (initiator)
   │  Tround2 = t5-t4  (initiator)
   │  ToF = (Tround1×Tround2 - Treply1×Treply2) / (Tround1+Tround2+Treply1+Treply2)
```

DS-TWR achieves the ~10 cm accuracy spec. Every commercial UWB anchor system uses it.

**TDoA (Time Difference of Arrival)** is the multilateration alternative: anchors are time-synced (wired or via a "sync anchor" broadcast); a tag broadcasts one packet; each anchor records the receive timestamp; differences yield position. Better for crowded tag populations (one TX, N anchors RX) but requires anchor time-sync infrastructure.

## 101.2  DW3000 register and command summary

The DW3000 (in the DWM3000 module) is a register-mapped SPI radio with ~150 documented registers. Key registers for ranging:

| Addr | Name | Purpose |
|------|------|---------|
| 0x00 | DEV_ID | should read 0xDECA0302 |
| 0x01 | EUI | 64-bit IEEE address |
| 0x03 | PANADR | PAN ID + 16-bit short address |
| 0x10 | SYS_CFG | RX/TX configuration flags |
| 0x14 | SYS_STATUS | IRQ flags (write-1-to-clear) |
| 0x24 | TX_FCTRL | frame control: length, data rate, PRF |
| 0x2A | TX_TIME | TX timestamp (32 bits + 8-bit antenna delay) |
| 0x36 | RX_TIME | RX timestamp |
| 0x39 | CHAN_CTRL | channel + preamble + SFD |
| 0x12 | TX_BUFFER | raw frame to transmit |
| 0x1A | RX_BUFFER | raw frame received |

Channels: 5 (6.5 GHz) and 9 (8.0 GHz) on DW3000. Higher PRF (pulse repetition frequency) = better multipath rejection but more crowded if multiple tags transmit simultaneously.

The SPI transaction format:

```
   Command byte:
     [WR=1/RD=0] [SUB_INDEX=0/1] [REG_INDEX 6 bits]
   If SUB_INDEX:
     [E=extended=0/1] [SUB_INDEX 7 bits]
   Then data.
```

Reading DEV_ID:

```
TX: 0x00              <- read REG=0
RX: 0x00 0x32 0x03 0xCA 0xDE  <- 4 bytes back, little-endian
```

That's the chip identification — if you don't get 0xDECA0302 (DW3000) or 0xDECA0130 (DW1000), nothing works downstream.

## 101.3  Wiring DWM3000 to the i.MX6ULL

DWM3000 is a packaged module with chip, crystal, antenna, regulator. Wires:

```
      ┌────────┐                              ┌─────────┐
ECSPI ┤ MOSI   ├──────────────────────────────┤ MOSI    │
      │ MISO   ├──────────────────────────────┤ MISO    │
      │ SCK    ├──────────────────────────────┤ SCK     │  DWM3000
      │ CS#    ├──────────────────────────────┤ CSn     │
GPIO  ┤ IRQ    ├──────────────────────────────┤ IRQ     │
GPIO  ┤ RESETn ├──────────────────────────────┤ RSTn    │
      │        │   3.3 V  ── 4.7 µF ──────────┤ VDD     │
      │        │   GND ───────────────────────┤ GND     │
      └────────┘                              └─────────┘
```

Critical: the antenna is on the module; **do not put metal within 5 cm** of it. UWB pulses are sensitive to nearfield ground planes; even a bench multimeter clip nearby skews ToF.

## 101.4  How the Qorvo driver actually works

Qorvo ships a reference "DW3xxx Software API" (~10k lines C) used in their reference designs and copied into community projects (`Makerfabs/DW3000`, etc.). It's not in mainline Linux — the dominant path is **user-space + spidev**.

The driver structure:

```
   port/      ← SPI + GPIO abstraction (you implement these for your platform)
   decadriver/dwt_uwb_driver.c  ← register access, calibration, basic TX/RX
   decadriver/lib/             ← state machines for TWR, dual-receive, etc.
   examples/                   ← SS-TWR initiator/responder, DS-TWR, TDoA
```

Walk of `dwt_starttx()` (paraphrased):

```c
int dwt_starttx(uint8_t mode) {
    /* Read SYS_STATUS to check we're not mid-RX */
    uint32_t status = dwt_read32bitreg(SYS_STATUS_ID);
    if (status & RX_IN_PROGRESS) return DWT_ERROR;

    if (mode & DWT_START_TX_DELAYED) {
        /* Delayed TX — use TX_TIME register to schedule */
        dwt_writefastCMD(CMD_DTX);
    } else {
        dwt_writefastCMD(CMD_TX);
    }

    if (mode & DWT_RESPONSE_EXPECTED) {
        /* Auto-enable RX after TX completes — for TWR responses */
        dwt_writefastCMD(CMD_TX_W4R);
    }
    return DWT_SUCCESS;
}
```

The "fast commands" (single-byte SPI writes) are the modern way to trigger state transitions without a full register write. CMD_TX, CMD_RX, CMD_DTX, CMD_TX_W4R cover most cases.

The TWR responder loop:

```c
/* In dwt_irq_handler — fires on RX done */
if (status & RX_FRAME_VALID) {
    dwt_readrxdata(rx_buf, frame_len, 0);
    if (is_poll_msg(rx_buf)) {
        /* Build response with our TX timestamp embedded */
        uint64_t resp_tx_ts = poll_rx_ts + UUS_TO_DWT_TIME * REPLY_DELAY_UUS;
        dwt_setdelayedtrxtime(resp_tx_ts >> 8);
        build_resp_msg(tx_buf, resp_tx_ts);
        dwt_writetxdata(sizeof(tx_buf), tx_buf, 0);
        dwt_writetxfctrl(sizeof(tx_buf), 0, 1);
        dwt_starttx(DWT_START_TX_DELAYED | DWT_RESPONSE_EXPECTED);
    }
}
```

The trick: scheduling TX at a *future* exact DWT time (the chip has its own 40-bit timestamp counter at 64 GHz / 16 µs wraparound). This lets the responder reply at a deterministic Treply for the math to work.

## 101.5  From scratch — DS-TWR initiator in user space

`code/ch101-uwb/twr_init.c` (abbreviated; full ~400 lines):

```c
/* DS-TWR initiator. Reads DEV_ID, configures channel/PRF/preamble,
 * then ping-loops a responder, prints distance.
 */
#include <fcntl.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>
#include <sys/ioctl.h>
#include <linux/spi/spidev.h>
#include <gpiod.h>

#define REG_DEV_ID      0x00
#define REG_SYS_STATUS  0x44
#define REG_TX_FCTRL    0x24
#define REG_TX_BUFFER   0x14
#define REG_TX_TIME     0x2A
#define REG_RX_BUFFER   0x12
#define REG_RX_TIME     0x15
#define REG_CHAN_CTRL   0x1F

#define CMD_TX         0x09
#define CMD_DTX        0x0A
#define CMD_TX_W4R     0x0D
#define CMD_RX         0x02

/* DS-TWR constants */
#define POLL_TX_TO_RESP_RX_DLY_UUS  240
#define RESP_RX_TO_FINAL_TX_DLY_UUS 500
#define UUS_TO_DWT_TIME             65536    /* 1 µs = 65536 DWT ticks */
#define SPEED_OF_LIGHT              299702547.0  /* in air, m/s */
#define DWT_TIME_UNITS              (1.0/499.2e6/128.0)  /* one DWT tick */

static int spi_fd;
static struct gpiod_line *irq_line, *rst_line;

static void dw_reset(void) {
    gpiod_line_set_value(rst_line, 0);
    usleep(2000);
    gpiod_line_set_value(rst_line, 1);
    usleep(5000);
}

static uint32_t dw_read32(uint8_t reg) {
    uint8_t tx[5] = { reg & 0x3F, 0 }, rx[5];
    struct spi_ioc_transfer t = { .tx_buf=(unsigned long)tx, .rx_buf=(unsigned long)rx,
                                  .len=5, .speed_hz=8000000 };
    ioctl(spi_fd, SPI_IOC_MESSAGE(1), &t);
    return rx[1] | (rx[2]<<8) | (rx[3]<<16) | (rx[4]<<24);
}

static void dw_write_buf(uint8_t reg, const uint8_t *data, int n) {
    uint8_t hdr = 0x80 | (reg & 0x3F);
    struct spi_ioc_transfer t[2] = {
        { .tx_buf=(unsigned long)&hdr, .len=1, .speed_hz=8000000 },
        { .tx_buf=(unsigned long)data, .len=n, .speed_hz=8000000 },
    };
    ioctl(spi_fd, SPI_IOC_MESSAGE(2), t);
}

static void dw_fast_cmd(uint8_t cmd) {
    uint8_t tx = 0x81 | (cmd << 1);
    struct spi_ioc_transfer t = { .tx_buf=(unsigned long)&tx, .len=1, .speed_hz=8000000 };
    ioctl(spi_fd, SPI_IOC_MESSAGE(1), &t);
}

static uint64_t dw_read_tx_ts(void) {
    /* 5-byte timestamp */
    uint8_t tx[6] = { REG_TX_TIME & 0x3F, 0 }, rx[6];
    struct spi_ioc_transfer t = { .tx_buf=(unsigned long)tx, .rx_buf=(unsigned long)rx,
                                  .len=6, .speed_hz=8000000 };
    ioctl(spi_fd, SPI_IOC_MESSAGE(1), &t);
    return (uint64_t)rx[1] | ((uint64_t)rx[2]<<8) | ((uint64_t)rx[3]<<16) |
           ((uint64_t)rx[4]<<24) | ((uint64_t)rx[5]<<32);
}

static void dw_init(void) {
    dw_reset();
    uint32_t id = dw_read32(REG_DEV_ID);
    if (id != 0xDECA0302) { fprintf(stderr,"DW3000 not found (got 0x%08x)\n", id); exit(1); }
    /* Configure: channel 5, preamble 128, 6.8 Mbps; standard for SS/DS-TWR */
    /* (Full chan_ctrl + sys_cfg config omitted for brevity — see Qorvo example) */
}

static int do_twr_cycle(double *out_distance) {
    uint8_t poll_msg[] = { 0x41, 0x88, 0, 0xCA, 0xDE, 'R','X','I','N',0xE0 };
    dw_write_buf(REG_TX_BUFFER, poll_msg, sizeof poll_msg);
    /* Configure TX frame length + control */
    uint32_t fctrl = sizeof(poll_msg) + 2;  /* +2 = FCS */
    dw_write_buf(REG_TX_FCTRL, (uint8_t*)&fctrl, 4);
    dw_fast_cmd(CMD_TX_W4R);                 /* TX then auto-enter RX */

    /* Wait for response (poll IRQ via libgpiod edge wait, omitted) */
    /* When RX_FRAME_VALID:                                        */
    uint64_t poll_tx_ts = dw_read_tx_ts();
    uint64_t resp_rx_ts;                     /* read REG_RX_TIME */
    uint8_t resp_msg[20];                    /* read REG_RX_BUFFER */
    /* ...read responder's TX timestamp from inside resp_msg[] ... */
    uint64_t poll_rx_ts_responder, resp_tx_ts_responder;
    memcpy(&poll_rx_ts_responder, &resp_msg[10], 5);
    memcpy(&resp_tx_ts_responder, &resp_msg[15], 5);

    /* Send final message that embeds these timestamps */
    /* ... (omitted for brevity) ... */

    /* After final is acknowledged or transmitted, compute ToF */
    uint64_t Tround1 = resp_rx_ts - poll_tx_ts;
    uint64_t Treply1 = resp_tx_ts_responder - poll_rx_ts_responder;
    /* Tround2, Treply2 come from a 4th final-RX message at the responder; */
    /* in some DS-TWR variants the responder computes range and returns it */
    /* Here we use SS-TWR shortcut (assume same crystal): */
    uint64_t tof_dtu = (Tround1 - Treply1) / 2;
    double tof = tof_dtu * DWT_TIME_UNITS;
    *out_distance = tof * SPEED_OF_LIGHT;
    return 0;
}

int main(void) {
    spi_fd = open("/dev/spidev0.0", O_RDWR);
    /* ... SPI mode setup, gpiod open, request irq + rst lines ... */
    dw_init();

    for (;;) {
        double dist;
        if (do_twr_cycle(&dist) == 0)
            printf("Range: %.2f m\n", dist);
        usleep(50000);
    }
}
```

The driver above is intentionally compressed. The full lab version includes:

- A complete responder counterpart (`twr_resp.c`) that builds the response with embedded RX/TX timestamps.
- Antenna-delay calibration (the chip-to-antenna trace + matching network adds ~16 ns of delay that must be subtracted from every ToF measurement; calibrated once per board).
- Proper IRQ-driven polling using libgpiod's `gpiod_line_event_wait`.
- The 5-byte timestamp arithmetic with the DWT 40-bit rollover handling.

Even this skeleton reveals the protocol: ToF = (response-time at initiator − reply-time at responder) / 2.

## 101.6  Three-anchor 2-D position via DS-TWR

With three anchors at known positions (A1, A2, A3) and a tag, sequentially do TWR with each anchor → 3 ranges → trilateration:

```
r1² = (x − x1)² + (y − y1)²
r2² = (x − x2)² + (y − y2)²
r3² = (x − x3)² + (y − y3)²

Subtract pairs to linearize:
  (r1² − r2²) − (x1² + y1²) + (x2² + y2²) = 2(x2 − x1)x + 2(y2 − y1)y
  (r2² − r3²) − (x2² + y2²) + (x3² + y3²) = 2(x3 − x2)x + 2(y3 − y2)y
2 equations, 2 unknowns → solve directly.
```

With 4 anchors you can get 3-D (add z) or 2-D over-determined (least-squares for noise reduction).

A Kalman filter on top smooths the trajectory between updates and rejects outliers.

## 101.7  Device tree and userspace plumbing

DT (same as any spidev radio):

```dts
&ecspi3 {
    cs-gpios = <&gpio4 26 GPIO_ACTIVE_LOW>;
    status = "okay";

    uwb@0 {
        compatible = "rohm,dh2228fv";
        reg = <0>;
        spi-max-frequency = <8000000>;
    };
};

&gpio4 {
    /* IRQ on gpio4-27, RST on gpio4-28 via libgpiod */
};
```

There *is* an in-tree `drivers/net/ieee802154/mcr20a.c` for one Freescale UWB chip and out-of-tree drivers for DW1000 (`thotro/dw1000-driver`), but the dominant pattern remains user-space + spidev for DW3000.

## 101.8  Apple Find My / FiRa interop

DW3000 supports the **FiRa Consortium**'s "MAC and PHY for UWB" interop spec, which is what iPhones use for "Find My" UWB. With the right firmware and OPS framework, your DW3000-based tag is detectable by an iPhone. Practical caveat: Apple's "Find My Network Accessory Program" requires hardware certification and a license, so DIY tags can only be ranged peer-to-peer with your own app, not by random nearby iPhones.

Apple's UWB chip (U1 / U2) is a black-box DW3000 derivative; reverse-engineering work (e.g., `nfc-tools/proxmark3`-adjacent UWB research) has documented enough for hobbyist interop with caveats.

## 101.9  Lab

1. **DW3000 identify.** Wire DWM3000 to ECSPI. Read DEV_ID → must be `0xDECA0302`. If wrong: SPI mode (mode 0), wiring, or fake module from Aliexpress.
2. **DS-TWR initiator + responder.** Flash one i.MX6ULL board as initiator, one as responder. Run the lab code. Place 1 m apart; expect a reading of ~1.0–1.1 m (the +10 cm is uncalibrated antenna delay).
3. **Antenna-delay calibration.** Place at known 1.000 m. Measured 1.10 m? Subtract 0.10 m's worth of DWT ticks from `tof_dtu`. Persist this calibration in a config file per board.
4. **Distance vs. range.** Walk the responder out to 5 m, 10 m, 20 m. Note when packets stop arriving (typically ~30 m line-of-sight at 6.8 Mbps; more at lower data rates).
5. **Multipath test.** Place the boards 2 m apart in a small room with metal furniture. Note distance noise. Move to open space; noise drops dramatically.
6. **3-anchor 2-D position.** Place 3 responder anchors in a triangle. The initiator's app does 3 TWR cycles and computes trilateration. Print (x, y) every second. Walk around; verify position tracks within ±20 cm.
7. **Kalman smoothing.** Add a 2-D constant-velocity Kalman filter; visualize raw vs. filtered trajectory in matplotlib.
8. **Throughput-vs-rate test.** Try 110 kbps, 850 kbps, 6.8 Mbps data rates. Higher rate = shorter air time = more TWR cycles/second but slightly worse range. Measure cycles/sec at each.

Commit all to `code/ch101-uwb/` including calibration values per board.

## 101.10  Pitfalls

- **Fake DWM3000 modules.** Common on Aliexpress; chip reads 0xDECA0130 (DW1000) instead. The register maps and command set are different. Buy from Qorvo distributors or Makerfabs.
- **Antenna-delay uncalibrated.** Out of the box, distances read 10–30 cm long. Always calibrate at a known distance first.
- **Metal nearby.** The UWB antenna is omnidirectional in free space; a metal plate within 5 cm distorts the pattern → multipath errors. Mount the module away from PCB ground planes, batteries, USB shields.
- **Clock drift in SS-TWR.** With cheap ±20 ppm crystals, Treply of 240 µs gives ±10 ns drift error = ±3 m. Always use DS-TWR for production accuracy; SS-TWR is for quick demos only.
- **Treply too short.** The responder needs time to process the poll and schedule its TX. <200 µs and the chip TX-fail. Spec values are 200–500 µs.
- **TX time exceeds 40-bit DWT counter wrap.** The 40-bit counter at 64 GHz wraps every ~17 s; scheduled TX times that cross the wrap go to the wrong epoch. Mask to 40 bits before scheduling.
- **Channel licensing.** Channel 5 (6.5 GHz) is allowed worldwide; channel 9 (8 GHz) has regional restrictions (US OK, EU OK under power limits, Japan stricter). Ship the right channel for the market.
- **Tag battery life with many anchors.** Each TWR cycle is ~1.5 ms of RX+TX = ~50 mA*1.5 ms = 75 µAs. 10 Hz update = 750 µAh per second = ~10 hours on a 250 mAh coin cell. Plan accordingly; lower update rate when stationary.
- **Outdoor weather.** UWB is line-of-sight sensitive; heavy rain attenuates noticeably at 6.5 GHz. Indoor or sheltered deployments only.
- **No mainline kernel driver for DW3000.** If you want one, you write it. Most projects accept user-space + spidev as the pattern.

## 101.11  Going deeper

- **Qorvo DW3000 User Manual + DW3000 Datasheet** — the canonical reference for registers and commands.
- **Qorvo "DW3xxx Software API"** (downloadable from Qorvo's site) — the reference C driver.
- **`Makerfabs/DW3000` and `Makerfabs/DW3000_DS_TWR`** — community ports of the above, Arduino-derived but readable.
- **`thotro/dw1000-driver`** — for the legacy DW1000 chip (still common on $30 modules).
- **`uwb-research/uwb-positioning` (university research repos)** — Kalman + multilateration implementations.
- **FiRa Consortium specifications** — the interop standard for "phone-compatible" UWB.
- **IEEE 802.15.4-2020 + 4z amendment** — the standardized UWB PHY/MAC the DW3000 implements.
- **Ch 99 / Ch 100** for non-UWB alternatives (FSK, ZigBee — neither does sub-metre).

---

> Next chapter: **Chapter 102 — USB 4G LTE modems** — beginning Group N (Cellular).
