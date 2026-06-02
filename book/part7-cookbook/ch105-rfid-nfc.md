---
chapter: 105
title: RFID / NFC (MFRC522, PN532, ST25R3911)
part: VII — Device cookbook
estimated_pages: 14
status: draft
---

# Chapter 105 — RFID / NFC

> **What:** **13.56 MHz HF RFID and NFC** — the technology behind contactless access cards, transit passes, phone Wallet, and "tap-to-pair." Three chips compared: **NXP MFRC522** (the ubiquitous Arduino-clone SPI/I²C/UART, ISO 14443A only), **NXP PN532** (more capable: 14443A/B + FeliCa, NFC initiator and target), **ST25R3911** (longer read range, high-end). On the i.MX6ULL we read tag UIDs over SPI, authenticate a Mifare Classic 1K block, walk the kernel `pn533` driver as the canonical mainline NFC stack reference, write a 200-line user-space MFRC522 driver from scratch, then bring up `libnfc` + `neard` for high-level NFC.
>
> **Why:** Access control is one of the most common embedded Linux applications — door readers, time-and-attendance kiosks, equipment-rental lockers, EV-charger user identification. NFC tagging extends to smart-home pairing (Tap to Wi-Fi), industrial asset tracking, and consumer-product authenticity verification. The chips are cheap (MFRC522 modules cost about $1). The standards are real. The security is half-broken — Mifare Classic was cracked in 2008. And Linux has an NFC subsystem (`net/nfc/`) that most engineers do not know exists.
>
> **Focus:** At 13.56 MHz, RFID and NFC use inductive coupling. The reader's antenna generates a magnetic field. That field powers the tag's IC, and the tag sends data back by modulating its load on the field. The reader chip uses a fixed sequence of register writes: configure carrier ON, set framing (Miller-encoded for tag→reader, Manchester for reader→tag), issue protocol-level commands (REQA, ATQA, ANTICOLL, SELECT, AUTH, READ_BLOCK), parse responses. Antenna matching is critical — a 5 mm misalignment between the reference design's antenna loop and yours = 30 % less read range.
>
> **Tooling.** This chapter uses `libnfc-bin` (`nfc-list`, `nfc-mfultralight`), `neard`; offensive-research only: `mfoc`, `mfcuk`.
> - **Ubuntu-base (target):** `apt install libnfc-bin libnfc-dev neard`
> - **Buildroot:** `BR2_PACKAGE_LIBNFC=y BR2_PACKAGE_NEARD=y`
> - Full per-tool reference: [Userspace tooling appendix](../part5-rootfs/appendix-tooling.md).

## 105.1  Chip comparison

| | MFRC522 | PN532 | ST25R3911 |
|---|---|---|---|
| Interfaces | SPI / I²C / UART | SPI / I²C / UART (HSU) | SPI |
| Standards | ISO 14443A | 14443A/B, FeliCa, NFC initiator + target | 14443A/B, FeliCa, longer range, V (ISO 15693) |
| Range (with standard tag) | 3–5 cm | 4–6 cm | 8–12 cm |
| TX power | ~100 mW | ~100 mW | ~1.4 W (with external antenna) |
| Mifare Classic Crypto1 | yes | yes | yes |
| NFC tag emulation | no | yes | yes |
| P2P NFC | no | yes | yes |
| Kernel mainline driver | none | `pn533` (drivers/nfc/) | none |
| Cost (module) | $1–3 | $5–10 | $15–25 |

**Pick guide:**
- **MFRC522** — door reader, asset tracker, anything that just needs a UID + Mifare R/W. Cheap and adequate for most access-control work.
- **PN532** — when you need NFC P2P (handover, peer transfer), phone-emulation, or FeliCa support. Mainline kernel driver exists.
- **ST25R3911** — when you need range (10 cm+), ISO 15693 (long-range industrial RFID), high reliability.

## 105.2  How 13.56 MHz RFID actually works

Two halves: reader and tag.

```
   ┌──── Reader antenna (loop, tuned to 13.56 MHz) ────┐
   │                                                    │
   │   ┌── Carrier on/off (ASK by reader)               │
   │   │   Field magnitude: 1.5–7.5 A/m                  │
   │   ▼                                                 │
   ╔═══╧═══╗                                              │
   ║       ║  13.56 MHz magnetic field                    │
   ║       ║                                              │
   ╚═══╤═══╝                                              │
   │   │                                                 │
   │   ▼                                                 │
   │   ┌── Tag antenna (loop, tuned to 13.56 MHz) ──┐    │
   │   │   Tag's IC rectifies field → powers itself  │    │
   │   │   To send data: tag shorts/opens a load     │    │
   │   │      → reader's antenna sees voltage dip   │    │
   │   │      → ASK demod recovers data             │    │
   │   └──────────────────────────────────────────  ┘    │
   │                                                    │
   └────────────────────────────────────────────────────┘
```

The tag is **passive** — no battery. The reader's field both powers the tag's chip and carries communication. Tag-to-reader uses load modulation with an 847.5 kHz subcarrier (Type A). Reader-to-tag uses direct ASK modulation, at either 100 % or 10 % depth.

The communication frames the **ISO 14443 anticollision and select protocol**:

```
Reader: REQA (request answer)         0x26  (Type A: short frame, 7 bits)
Tag:    ATQA (answer to request)      2 bytes — tag's basic capability
Reader: ANTICOLL (cascade level 1)    0x93 0x20
Tag:    UID CL1 + BCC                 5 bytes — 4 UID bytes + BCC checksum
Reader: SELECT (cascade level 1)      0x93 0x70 UID...
Tag:    SAK (select acknowledge)      1 byte — Mifare Classic, Mifare Ultralight, ...

For Mifare Classic, then:
Reader: AUTH(Key, Sector)             0x60 0x00 ... Crypto1 challenge-response
Tag:    encrypted from now on
Reader: READ_BLOCK 0x04                read block 4
Tag:    16 bytes (encrypted)
```

The MFRC522 implements ISO 14443A framing and timing in silicon; you don't bit-bang. You issue protocol-level commands and the chip handles the air interface.

## 105.3  MFRC522 register and command summary

The MFRC522 has 64 registers, 16 commands. Key ones:

| Register | Addr | Purpose |
|---|---|---|
| CommandReg | 0x01 | issue command (Idle, Transceive, Authent, ...) |
| ComIEnReg / DivIEnReg | 0x02 / 0x03 | interrupt enable |
| ComIrqReg | 0x04 | interrupt status (RxIRq, TxIRq, ErrIRq, TimerIRq) |
| ErrorReg | 0x06 | error flags (collision, parity, CRC) |
| FIFODataReg | 0x09 | TX/RX FIFO (64 bytes) |
| FIFOLevelReg | 0x0A | FIFO byte count |
| BitFramingReg | 0x0D | how many bits in last byte |
| ModeReg | 0x11 | CRC preset, polarity |
| TxControlReg | 0x14 | antenna driver enable |
| VersionReg | 0x37 | 0x92 = MFRC522 v2.0 |

| Command | Hex | Meaning |
|---|---|---|
| Idle | 0x00 | stop current command |
| Transceive | 0x0C | send FIFO bytes + receive response |
| Authent | 0x0E | Mifare Classic Crypto1 authentication |
| SoftReset | 0x0F | reset the chip |

The transceive flow:

1. Write payload into FIFODataReg (e.g., REQA = 0x26).
2. Write BitFramingReg with 7 (REQA is a 7-bit short frame).
3. Write CommandReg = Transceive.
4. Write BitFramingReg = 0x80 (set StartSend bit) — chip TXes + receives response.
5. Wait for RxIRq or TimerIRq.
6. Read FIFODataReg until FIFOLevelReg reads 0 — that's the tag's response.

That sequence — embedded in `MFRC522_TransceiveData()` — is what every Arduino library wraps. Below we write it ourselves.

## 105.4  Wiring MFRC522 (SPI) to the i.MX6ULL

```
       ┌────────┐                              ┌──────────┐
ECSPI ─┤ MOSI   ├──────────────────────────────┤ MOSI     │
       │ MISO   ├──────────────────────────────┤ MISO     │  MFRC522
       │ SCK    ├──────────────────────────────┤ SCK      │
       │ CS#    ├──────────────────────────────┤ SDA      │  (NSS)
GPIO  ─┤ IRQ    ├──────────────────────────────┤ IRQ      │  (active low, edge-falling)
GPIO  ─┤ RESETn ├──────────────────────────────┤ RST      │
       │        │   3.3 V ──────────────────── ┤ 3.3V     │
       │        │   GND ──────────────────────  ┤ GND      │
       │        │                              ┌ ANT1     │  ← antenna pads
       │        │                              └ ANT2     │  (matched 13.56 MHz loop)
       └────────┘                              └──────────┘
```

The antenna is the critical part. A bad-design module gets 1 cm read range; the cheap-but-correct modules (the green "RC522" boards with the small ferrite antenna trace) get 3–5 cm. Do not wind your own antenna unless you have an impedance analyser. Buy a tuned module instead.

## 105.5  How the kernel pn533 driver works

The kernel NFC subsystem (`net/nfc/`) provides netlink socket interface + the device-specific drivers. PN532 is in `drivers/nfc/pn533/`.

```
   User-space (neard, libnfc, your app)
        │ AF_NFC netlink
        ▼
   net/nfc/                      <-- core, target table, polling
        │
        ▼
   drivers/nfc/pn533/             <-- chip-specific
        │                         <-- USB or UART or I²C variant
        ▼
   USB / serdev / i2c bus
```

Walk of `pn533_send_cmd_frame_async()` (paraphrased):

```c
static int pn533_send_cmd_frame_async(struct pn533 *dev,
                                       struct pn533_frame *out_frame,
                                       struct pn533_frame *in_frame,
                                       ...) {
    /* Build a PN532 frame: preamble + start + length + cmd + data + DCS + postamble */
    pn533_build_cmd_frame(out_frame, cmd, params, params_len);

    /* Submit URB (for USB) or write tty (for UART) */
    return dev->phy_ops->send_frame_async(dev, out_frame, in_frame, ...);
}
```

The phy_ops separation lets the same protocol layer work for USB, I²C, UART variants of the PN532.

Polling for tags:

```c
static int pn533_send_poll_frame(struct pn533 *dev) {
    /* InListPassiveTarget command, 1 target max, baudrate 106 kbps Type A */
    pn533_build_cmd_frame(frame, PN533_CMD_IN_LIST_PASSIVE_TARGET,
                          (u8[]){ 1, 0 }, 2);
    return pn533_send_cmd_frame_async(dev, frame, &dev->resp_frame, ...);
}
```

When a tag enters the field, the response includes UID, ATQA, SAK; `pn533` calls into `net/nfc/core.c::nfc_targets_found()` which broadcasts netlink events to user-space. neard receives the events and runs the higher-level NDEF/handover state machines.

User-space:

```sh
modprobe pn533_usb       # or pn533_i2c, pn533_uart
nfctool list             # via libnfc
neardctl tags            # via neard
```

This is the "proper" Linux path. Most projects skip the kernel NFC stack. They use `libnfc` directly against `/dev/spidev`, or one of the MFRC522 user-space drivers shown below.

## 105.6  From scratch — user-space MFRC522 driver

mfrc522_min.c (compressed; full ~400 lines):

```c
/* Minimal MFRC522 driver: detect tag, read UID, dump Mifare Classic block 0.
 * Build: gcc -o mfrc522 mfrc522_min.c -lgpiod
 */
#include <fcntl.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>
#include <sys/ioctl.h>
#include <linux/spi/spidev.h>
#include <gpiod.h>

#define REG_COMMAND       0x01
#define REG_COM_IRQ       0x04
#define REG_ERROR         0x06
#define REG_FIFO_DATA     0x09
#define REG_FIFO_LEVEL    0x0A
#define REG_CONTROL       0x0C
#define REG_BIT_FRAMING   0x0D
#define REG_MODE          0x11
#define REG_TX_MODE       0x12
#define REG_RX_MODE       0x13
#define REG_TX_CONTROL    0x14
#define REG_TX_AUTO       0x15
#define REG_T_MODE        0x2A
#define REG_T_PRESCALER   0x2B
#define REG_T_RELOAD_H    0x2C
#define REG_T_RELOAD_L    0x2D
#define REG_VERSION       0x37

#define CMD_IDLE          0x00
#define CMD_TRANSCEIVE    0x0C
#define CMD_AUTHENT       0x0E
#define CMD_SOFTRESET     0x0F

#define PICC_REQA         0x26
#define PICC_ANTICOLL_CL1 0x93
#define PICC_AUTH_A       0x60
#define PICC_AUTH_B       0x61
#define PICC_READ         0x30
#define PICC_HALT         0x50

static int spi_fd;
static struct gpiod_line *rst;

static uint8_t reg_read(uint8_t r) {
    uint8_t tx[2] = { 0x80 | ((r << 1) & 0x7E), 0 }, rx[2];
    struct spi_ioc_transfer t = { .tx_buf=(unsigned long)tx, .rx_buf=(unsigned long)rx,
                                  .len=2, .speed_hz=1000000 };
    ioctl(spi_fd, SPI_IOC_MESSAGE(1), &t);
    return rx[1];
}
static void reg_write(uint8_t r, uint8_t v) {
    uint8_t tx[2] = { (r << 1) & 0x7E, v };
    struct spi_ioc_transfer t = { .tx_buf=(unsigned long)tx, .len=2, .speed_hz=1000000 };
    ioctl(spi_fd, SPI_IOC_MESSAGE(1), &t);
}
static void set_bits(uint8_t r, uint8_t mask) { reg_write(r, reg_read(r) | mask); }
static void clr_bits(uint8_t r, uint8_t mask) { reg_write(r, reg_read(r) & ~mask); }

static void antenna_on(void) { set_bits(REG_TX_CONTROL, 0x03); }

static int transceive(uint8_t cmd, const uint8_t *send, int send_len,
                      uint8_t *recv, int *recv_len, uint8_t last_bits) {
    reg_write(REG_COMMAND, CMD_IDLE);
    reg_write(REG_COM_IRQ, 0x7F);                 /* clear all flags */
    reg_write(REG_FIFO_LEVEL, 0x80);              /* flush FIFO */
    for (int i = 0; i < send_len; i++) reg_write(REG_FIFO_DATA, send[i]);
    reg_write(REG_COMMAND, cmd);
    if (cmd == CMD_TRANSCEIVE) set_bits(REG_BIT_FRAMING, 0x80);   /* StartSend */

    uint8_t irq;
    for (int i = 0; i < 200; i++) {              /* ~40 ms timeout */
        irq = reg_read(REG_COM_IRQ);
        if (irq & 0x30) break;                   /* RxIRq or IdleIRq */
        if (irq & 0x01) return -2;               /* TimerIRq */
        usleep(200);
    }
    clr_bits(REG_BIT_FRAMING, 0x80);

    if (reg_read(REG_ERROR) & 0x13) return -1;   /* BufferOvfl, ParityErr, ProtocolErr */

    int n = reg_read(REG_FIFO_LEVEL);
    if (n > *recv_len) n = *recv_len;
    for (int i = 0; i < n; i++) recv[i] = reg_read(REG_FIFO_DATA);
    *recv_len = n;
    return 0;
}

static int picc_request(uint8_t *atqa) {
    reg_write(REG_BIT_FRAMING, 0x07);            /* 7 bits last byte */
    uint8_t cmd = PICC_REQA;
    int n = 2;
    return transceive(CMD_TRANSCEIVE, &cmd, 1, atqa, &n, 7);
}

static int picc_anticoll(uint8_t *uid_out) {
    reg_write(REG_BIT_FRAMING, 0x00);
    uint8_t cmd[2] = { PICC_ANTICOLL_CL1, 0x20 };
    uint8_t resp[5];
    int n = 5;
    int r = transceive(CMD_TRANSCEIVE, cmd, 2, resp, &n, 0);
    if (r) return r;
    uint8_t bcc = resp[0] ^ resp[1] ^ resp[2] ^ resp[3];
    if (bcc != resp[4]) return -3;
    memcpy(uid_out, resp, 4);
    return 0;
}

static void mfrc_init(void) {
    /* Hardware reset */
    gpiod_line_set_value(rst, 0); usleep(2000);
    gpiod_line_set_value(rst, 1); usleep(50000);

    reg_write(REG_COMMAND, CMD_SOFTRESET);
    usleep(50000);

    /* TX/RX modulation: 100% ASK, CRC preset 6363 */
    reg_write(REG_T_MODE, 0x8D);
    reg_write(REG_T_PRESCALER, 0x3E);
    reg_write(REG_T_RELOAD_L, 30);
    reg_write(REG_T_RELOAD_H, 0);
    reg_write(REG_TX_AUTO, 0x40);
    reg_write(REG_MODE, 0x3D);
    antenna_on();
}

int main(void) {
    spi_fd = open("/dev/spidev0.0", O_RDWR);
    uint8_t mode = SPI_MODE_0;
    ioctl(spi_fd, SPI_IOC_WR_MODE, &mode);

    struct gpiod_chip *chip = gpiod_chip_open("/dev/gpiochip0");
    rst = gpiod_chip_get_line(chip, 24);
    gpiod_line_request_output(rst, "mfrc-rst", 1);

    mfrc_init();
    printf("MFRC522 v=0x%02X\n", reg_read(REG_VERSION));

    printf("Present a tag.\n");
    for (;;) {
        uint8_t atqa[2], uid[4];
        if (picc_request(atqa) == 0 && picc_anticoll(uid) == 0) {
            printf("UID: %02X %02X %02X %02X  ATQA: %02X %02X\n",
                   uid[0], uid[1], uid[2], uid[3], atqa[0], atqa[1]);
            /* HALT the tag so we don't keep re-reading */
            uint8_t halt[2] = { PICC_HALT, 0 };
            int n = 0;
            transceive(CMD_TRANSCEIVE, halt, 2, NULL, &n, 0);
            sleep(1);
        }
        usleep(100000);
    }
}
```

That's the entire reader: ~150 lines for the core, ~50 for SPI/GPIO setup. Add Crypto1 auth + block read (another ~100 lines) and you have a working Mifare Classic 1K reader/writer.

What the framework hides:
- The MFRC522's transceive command does both TX and RX in one go using its FIFO.
- The 7-bit short frame for REQA is configured via BitFramingReg before the transceive — easy to forget.
- The BCC byte after the 4-byte UID is a sanity check; modules that compute BCC wrong report a passing read but with corrupt UIDs.
- The HALT command must be sent before the next REQA, or the tag won't respond again (it's already "active").

## 105.7  Mifare Classic security — broken but still used

The Crypto1 cipher (proprietary, never published, reverse-engineered in 2008) protects Mifare Classic blocks. **Crypto1 is fundamentally broken** — anyone with a $30 reader and `mfoc`/`mfcuk` tools can dump all keys from a card in ~5 minutes.

Despite this, Mifare Classic dominates legacy access systems because:
- Vendor lock-in (the building's reader infrastructure).
- The keys you don't know stay encrypted enough for a casual attacker.

Modern systems use **Mifare DESFire EV2/EV3** (AES-128, properly designed) or **iCLASS SE**. If you're designing new, use DESFire; if you're integrating with existing infrastructure, you may be stuck with Classic.

For DESFire: the MFRC522 supports the framing but not the AES; you implement Crypto on the host side (or use a chip like ST25R3911 with hardware AES).

## 105.8  Bringing up libnfc + neard (the kernel-stack path)

For a PN532 module (USB or UART), the proper path:

```sh
modprobe pn533_i2c                                    # or _usb, depending on attach
apt install libnfc-bin libnfc-dev neard

# Identify devices
nfc-list
# NFC device: pn532_uart:/dev/ttymxc1 opened
# 1 ISO14443A passive target(s) found:
# ATQA (SENS_RES): 00 04
# UID (NFCID1): 12 34 56 78
# SAK (SEL_RES): 08

# Read NDEF (NFC Data Exchange Format) tags
nfc-mfultralight r tag.dump

# neard for high-level NFC: tap to pair, web URLs
neard &
neardctl tags
neardctl record-uri https://example.com
```

`neard`'s big advantage: implements the NFC Forum's connection-handover spec, so a "tap-to-pair-Wi-Fi" works without you writing any of it.

## 105.9  Lab

1. **MFRC522 identify.** Wire to ECSPI; build `mfrc522_min.c`. VersionReg must read `0x91` or `0x92`. If 0x00 or 0xFF, SPI wrong.
2. **Tag detection.** Present a Mifare Classic 1K card; print its UID. Try a Mifare Ultralight (different ATQA); confirm.
3. **Block read with auth.** Extend the driver: `picc_auth(block, key_a, uid)` + `picc_read(block, buf)`. Default key for new cards is `FFFFFFFFFFFF`. Read block 0; first 4 bytes should match the UID.
4. **Read all 16 sectors.** Loop over sectors 0..15; read 4 blocks each; dump.
5. **Write a sector.** Write a value to a non-trailer block (e.g., 0x14). Re-read; confirm.
6. **NFC NDEF.** Use libnfc to write an NDEF URI record onto an NTAG215; verify with your phone's NFC reader.
7. **PN532 mainline path.** If you have a PN532, attach via I²C; `modprobe pn533_i2c`; `neardctl tags`; verify the kernel sees the same tag the user-space driver sees.
8. **Access control flow.** Build a 50-line door-controller: read UID, check against allow-list, fire a GPIO to a relay if allowed. Log all attempts.
9. **Antenna range test.** Measure read distance with a stock card. Then add a 5 mm spacer (PCB sleeve) between reader and card; range should drop ~20 %. Reposition card axially vs perpendicular; field is directional.

## 105.10  Pitfalls

- **Module quality varies wildly.** Cheap MFRC522 modules have detuned antennas; 1 cm range vs the 5 cm spec. Buy from known suppliers or accept the variance.
- **CRC preset wrong.** ModeReg = 0x3D sets CRC preset 6363h. Wrong value = tag rejects every command.
- **Tag already in HALT state.** A tag that's been HALTed by a prior reader cycle won't respond to REQA — use WUPA (0x52) instead.
- **Crypto1 timing.** The Authent command has tight timing requirements; on slow SPI buses (<1 MHz) you can miss the window. Bump SPI to 4+ MHz.
- **DESFire mistaken for Mifare Classic.** DESFire ATQA is 0x4403 + SAK 0x20; trying Crypto1 on it fails. Detect by SAK and switch protocols.
- **Multiple tags in field.** ISO 14443 anticollision picks one tag; the others starve. The cascade-level-1/2/3 dance handles 7- or 10-byte UIDs (NTAG2xx). Simple drivers fail on 7-byte tags by ignoring CL2.
- **Mifare Classic key not default.** Most production cards have rotated keys; the manufacturer/vendor key is in the access-control software's database. Don't expect FF×6 to work on a real building card.
- **Cloning detection.** Mifare Classic clones (UID-changeable "magic cards") are common; security systems should check that re-reads are consistent and that the AppId block matches expectations, not just the UID.
- **Antenna detuning by metal nearby.** Mounting an MFRC522 against a metal backplate detunes the 13.56 MHz LC tank → no read. Use a ferrite shield (the NXP CLRC663 reference design shows the layout).

## 105.11  Going deeper

- **NXP MFRC522 Datasheet** + **MF1S50yyX_V1** (Mifare Classic 1K product data sheet).
- **NXP PN532 User Manual** (UM0701-02) — the canonical reference.
- **`drivers/nfc/`** and **`net/nfc/`** in the kernel.
- **`libnfc` (https://github.com/nfc-tools/libnfc)** — covers most readers, including MFRC522 via the `mfrc522_spi` driver.
- **`mfoc` / `mfcuk`** — Mifare Classic key recovery (offensive security; useful for understanding what *not* to rely on).
- **NFC Forum specifications** — NDEF, RTD, Connection Handover.
- **ISO/IEC 14443** (Type A and Type B) — the air-interface standard.
- **`neard` daemon** — high-level NFC stack on Linux.
- **Ch 95** — Bluetooth handover via NFC (the "tap to pair" use case bridges the two stacks).

---

> Next chapter: **Chapter 106 — Fingerprint sensors** — UART command protocols for R503, FPM10A, AS608.
