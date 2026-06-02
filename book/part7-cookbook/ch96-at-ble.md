---
chapter: 96
title: AT-command BLE modules (HM-10 / HC-08 / JDY-08)
part: VII — Device cookbook
estimated_pages: 12
status: draft
---

# Chapter 96 — AT-command BLE modules

> **What:** BLE modules that hide the entire Bluetooth stack behind a simple UART AT-command interface. **HM-10** (CC2540/CC2541-based), **HC-08**, **JDY-08** — you send `AT+...` strings over a UART, and the module handles advertising, connection, and a transparent serial data pipe to a connected phone. No BlueZ, no kernel BT stack, no GATT programming.
>
> **Why:** for products that need "send a few bytes to/from a phone app" and nothing more, the AT-BLE module is dramatically simpler than the full HCI + BlueZ stack of Ch 95. The module is the Bluetooth stack. Linux only talks to a UART. The trade-off is real. You are stuck with the module's fixed GATT profile, usually a single "transparent UART" characteristic. Throughput tops out at a few hundred bytes per second. The AT command set is vendor-specific and non-standard.
>
> **Focus:** the module behaves like a wireless serial cable. After configuration, anything you write to the UART appears in the phone app (via a notify characteristic), and anything the phone sends appears on the UART RX. It is a wireless serial port. Linux needs no Bluetooth code — just open `/dev/ttymxc2` and call `read`/`write`.
>
> **Tooling.** This chapter uses Just a UART terminal: `picocom` or `minicom`.
> - **Ubuntu-base (target):** `apt install picocom minicom`
> - **Buildroot:** `BR2_PACKAGE_PICOCOM=y`
> - Full per-tool reference: [Userspace tooling appendix](../part5-rootfs/appendix-tooling.md).

## 96.1  Module comparison

| | HM-10 | HC-08 | JDY-08 |
|---|---|---|---|
| Chip | TI CC2540/CC2541 | unknown (clone) | Beken BK3431 |
| BLE version | 4.0 | 4.0 | 4.2 |
| Profile | transparent UART (custom service) | transparent UART | transparent UART |
| Default baud | 9600 | 9600 | 9600 |
| Range | ~30 m | ~20 m | ~30 m |
| Config | AT commands | AT commands | AT commands |
| Cloned variants | many (firmware varies!) | several | several |
| Volume price | $3–6 (genuine), $1–2 (clone) | $1–2 | $1–2 |

**Clone variants are a real problem.** There are at least five different "HM-10" modules in the market, each with different firmware and different AT command syntax. A genuine HM-10 (from Jnhuamao) responds to one command set; clones may differ. Always verify the exact AT dialect of *your* module.

**Pick guide:**
- **HM-10 genuine**: best-documented, most-supported. Worth the premium for the known command set.
- **HC-08 / JDY-08**: cheaper; verify the command set before designing around it.

## 96.2  The transparent-UART model

```
   Linux              AT-BLE module           Phone app
   ─────              ─────────────           ─────────
   /dev/ttymxc2  ◄──► UART ◄──► [BLE stack] ◄──► BLE ◄──► custom characteristic

   Two modes:
   - COMMAND mode: AT strings configure the module (name, baud, role).
   - DATA mode (connected): bytes flow transparently both ways.
```

After a phone connects, the module enters **data mode**: every byte Linux writes to the UART is sent to the phone (as a GATT notification on the module's TX characteristic); every byte the phone writes (to the module's RX characteristic) appears on Linux's UART RX. It's literally a wireless UART cable.

This is the main reason to choose an AT-BLE module. Your application is plain serial I/O — no D-Bus, no GATT objects, no BlueZ daemon.

## 96.3  Configuration via AT commands

In command mode (before a connection, or after entering it via a mode pin):

```
AT              → OK              (is the module alive?)
AT+NAME?        → +NAME=HMSoft    (query name)
AT+NAMEMyDevice → OK              (set name to "MyDevice")
AT+BAUD?        → +BAUD=0         (0 = 9600)
AT+BAUD4        → OK              (set to 115200)
AT+ROLE0        → OK              (0 = peripheral/slave, 1 = central/master)
AT+ADTY0        → OK              (advertising type)
AT+RESET        → OK              (apply + reboot)
AT+VERS?        → +VERS:HMSoft V540  (firmware version — tells you the clone variant)
```

Caveat on syntax. The genuine HM-10 commands omit the `\r\n` terminator and the `=` sign for set commands in older firmware (e.g., `AT+NAMEMyDevice`, not `AT+NAME=MyDevice`). Clone command sets vary. Run `AT+VERS?` first — the version response identifies your variant.

A configuration sequence from Linux:

```c
int fd = open("/dev/ttymxc2", O_RDWR | O_NOCTTY);
/* set 9600 8N1 */
write(fd, "AT+NAMEMySensor", 15);   expect_ok(fd);
write(fd, "AT+BAUD4", 8);            expect_ok(fd);   /* 115200 */
write(fd, "AT+ROLE0", 8);            expect_ok(fd);   /* peripheral */
write(fd, "AT+RESET", 8);
/* reopen at 115200 */
```

## 96.4  Using it — just a serial port

After configuration, the module advertises automatically. When a phone connects, you're in data mode. From Linux:

```c
int fd = open("/dev/ttymxc2", O_RDWR | O_NOCTTY);
/* configured at 115200 8N1 */

/* Send a sensor reading to the phone */
char msg[32];
int temp = read_bme280();          /* Ch 67 */
snprintf(msg, sizeof(msg), "T=%d.%02d\n", temp/100, temp%100);
write(fd, msg, strlen(msg));        /* appears in the phone app */

/* Receive commands from the phone */
char buf[64];
int n = read(fd, buf, sizeof(buf));  /* whatever the phone sent */
if (n > 0 && strncmp(buf, "LED ON", 6) == 0)
    gpiod_set_value(led, 1);
```

That is the whole integration. There is no Bluetooth code — just `read` and `write` on a UART. A phone app (e.g., "Serial Bluetooth Terminal" or "LightBlue") connects to the module's name, opens the transparent characteristic, and exchanges text.

Compare to Ch 95's GATT server: about 250 lines of D-Bus code versus ten lines of serial I/O. AT modules trade features for simplicity.

## 96.5  When AT-BLE is the right choice (and when it isn't)

**Right choice when:**
- You need a simple bidirectional data pipe to a phone app.
- "A few hundred bytes per second" is enough throughput.
- You want zero Bluetooth code on the Linux side.
- The product is simple (a sensor that reports + takes a few commands).
- BOM cost matters and a $1.50 module beats a $4 controller + the dev effort.

**Wrong choice when:**
- You need standard GATT services (so any BLE app, not just a serial-terminal app, works).
- You need multiple characteristics, proper service UUIDs, or BLE standard profiles (HID, HRS, etc.).
- You need >few hundred bytes/sec throughput.
- You need control over advertising, security/pairing, or connection parameters.
- You're building a polished product where the phone app is a real app (not a serial terminal).

For a real product with a custom phone app, the BlueZ GATT path (Ch 95) is better — it gives standard GATT the app can use cleanly. The AT module fits quick, simple "wireless serial cable" use cases.

## 96.6  Lab

1. **Identify your module.** Wire to a UART. Send `AT+VERS?`; record the firmware version (tells you the clone variant + command dialect).
2. **Configure.** Set name, baud, peripheral role. Reset.
3. **Connect from a phone.** Use "Serial Bluetooth Terminal" (Android) or "LightBlue" (iOS). Find your module's name; connect.
4. **Bidirectional data.** From Linux, write text to the UART → see it in the phone app. From the phone, send text → read it on the UART.
5. **Real integration.** Wire it to a BME280 (Ch 67): Linux sends temperature every 5 s; the phone app shows it. Add a command parser (phone sends "LED ON" → Linux toggles a GPIO).
6. **Compare effort.** Reflect on the ~10 lines here vs the ~250-line GATT server of Ch 95. Note what you gave up (standard GATT, throughput, multiple characteristics).
7. **Range test.** Walk away with the phone; note where the connection drops (~20–30 m).

## 96.7  Pitfalls

- **Clone command-set differences.** "HM-10" clones use different AT syntax (`AT+NAME=x` vs `AT+NAMEx`, with/without `\r\n`). Always `AT+VERS?` first and match your module's dialect.
- **No line terminator (genuine HM-10).** Genuine HM-10 v5xx commands have *no* CR/LF. Sending `AT\r\n` to one may fail; send bare `AT`. Clones often *require* `\r\n`. Test.
- **Command mode vs data mode confusion.** Once connected, the module is in data mode — AT commands are passed through as data, not interpreted. To reconfigure, disconnect first (or use a mode pin if the module has one).
- **Baud mismatch after AT+BAUD.** Set the baud, reset, then *reopen the UART at the new baud*. Forgetting this = no communication.
- **Throughput ceiling.** BLE's connection interval limits throughput to a few hundred bytes/sec to a few KB/sec. Don't expect serial-cable speeds.
- **No pairing/security by default.** Most AT modules connect without pairing — anyone can connect. For sensitive data, this is a security hole. The full BlueZ stack (Ch 95) gives proper pairing/encryption.
- **Single connection.** AT modules typically support one connection at a time. For multiple simultaneous phones, you need a real GATT server.
- **Auto-advertising can't be fully disabled on some.** The module advertises whenever not connected — a power and security consideration.

## 96.8  Going deeper

- **HM-10 datasheet + AT command guide (Jnhuamao)** — the genuine command set.
- **The Linux `termios` API** — UART configuration (the only "driver" you need).
- **Ch 95** — the full BlueZ GATT path, for when AT-BLE is too limited.
- **Ch 103** — UART AT-command cellular modems use the same "talk-to-a-UART" pattern.
- **"Serial Bluetooth Terminal" (Android) / "LightBlue" (iOS)** — phone-side test apps.

> Next chapter: **Chapter 97 — BLE Mesh.** Beyond point-to-point — a self-healing mesh of dozens of BLE nodes, the bluez-mesh stack, provisioning, and mesh models for lighting/sensor networks.
