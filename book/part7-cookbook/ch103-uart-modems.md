---
chapter: 103
title: UART AT-command modems (SIM7600 UART, A7670C, Air724UG, ML302)
part: VII — Device cookbook
estimated_pages: 14
status: draft
---

# Chapter 103 — UART AT-command modems

> **What:** the **UART-only cellular modem** — older or BOM-constrained designs where the modem has no USB, just a TTL UART. Modules: **SIMCom A7670C** (LTE Cat-1 UART, cheap), **SIMCom SIM7600 UART variant**, **Air724UG** (Chinese-domestic, LTE Cat-4 UART), **Quectel ML302** (Cat-1, UART + ECM). On Linux, you talk to it via `/dev/ttymxc*`, use **chat + pppd** for data, and AT commands for everything else (SMS, signal, OTA firmware update). No fancy QMI, no high speeds — just the AT command set + PPP framing + good UART discipline.
> **Why:** USB host is expensive. A USB modem requires USB-OTG/host hardware on your SoC, a 5 V supply that can deliver 2.5 A peaks, ESD protection on D+/D-, and a USB connector or board-to-board. A UART modem is 4 wires (TX/RX/RTS/CTS) + a small 3.3/4 V buck. On a price-sensitive IoT product (alarm panel, vending machine, agricultural sensor), the UART path saves $5–10 BOM + a USB-host integration headache. The trade: max ~5 Mbps (versus 150 Mbps over USB-QMI), and you live with PPP overhead.
> **Focus:** PPP is a 1989-vintage link protocol. It uses HDLC framing, LCP for link negotiation, IPCP for IPv4 address assignment, and PAP/CHAP for authentication. It still works on every modem ever made. The kernel's `ppp_generic.ko` provides the netdev; `pppd` is the user-space brain that runs the LCP/IPCP state machines and a chat script that converses with the modem to bring up the channel. With `pppd`, a chat script, and an init.d (or systemd) supervisor, you have a robust auto-reconnecting cellular link with no QMI/MBIM/RNDIS complexity.
> **Tooling.** This chapter uses `ppp` (`pppd`, `chat`); optional GSM mux via `ldattach` (`util-linux`).
> - **Ubuntu-base (target):** `apt install ppp util-linux`
> - **Buildroot:** `BR2_PACKAGE_PPP=y`
> - Full per-tool reference: [Userspace tooling appendix](../part5-rootfs/appendix-tooling.md).

## 103.1  When UART beats USB

| Constraint | UART modem | USB modem |
|---|---|---|
| Throughput | up to 5 Mbps (PPP), 50 Mbps (ECM if supported) | 150 Mbps+ |
| Host hardware | UART pins + 3.3/4 V supply | USB-host + 5 V × 2.5 A |
| BOM cost | $-5 to $-10 vs USB | baseline |
| Latency (TCP round-trip) | similar (~50 ms cellular) | similar |
| AT debug | yes (same UART) | separate /dev/ttyUSB |
| Firmware update | over UART (slow) | over USB (fast) |
| Voice (VoLTE PCM) | yes via separate PCM I²S | yes via USB audio |
| GPS | shared UART (mux NMEA + AT) or separate | separate USB interface |

Pick UART when: BOM-cost-sensitive, low-throughput app (SMS, telemetry, < 1 Mbps data), no spare USB host port. Pick USB otherwise.

## 103.2  Wiring

```
       ┌────────┐                                ┌──────────┐
i.MX  ─┤ TXD    ├───── 3.3 V level ───────────── ┤ RXD      │
UART4  │ RXD    ├──────────────────────────────  ┤ TXD      │
       │ RTS#   ├──────────────────────────────  ┤ CTS#     │  A7670C / SIM7600 / Air724UG
       │ CTS#   ├──────────────────────────────  ┤ RTS#     │
GPIO  ─┤ PWRKEY ├──────────────────────────────  ┤ PWRKEY   │  (pulse low ≥1 s to power on)
GPIO  ─┤ RESETn ├──────────────────────────────  ┤ RESET    │  (optional emergency reset)
       │        │   4 V  ── 470 µF ────────────  ┤ VBAT     │  ← critical: ~2 A peaks
       │        │   GND ───────────────────────  ┤ GND      │
       └────────┘                                └──────────┘
```

Mandatory rules:

1. **Above 9600 baud, hardware flow control is mandatory.** Most modules expect 115200 with flow control by default. Without it, the UART drops bytes, PPP LCP times out, and the modem looks broken.
2. **VBAT, not VDD_3V3.** The modem's RF block runs from a 4 V (typ.) supply directly to the PA. The internal LDO drops to 3.3 V for logic, but the PA pulls from VBAT. Sourcing VBAT from a weak 3.3 V LDO instead of a buck = TX brownouts.
3. **470 µF or larger bulk cap on VBAT.** TX is a 1.7 W burst at ~500 mA peak. The supply needs to hold that without sagging or PPP drops on every transmit.
4. **PWRKEY pulse.** Modules are off after VBAT applied. Pulse PWRKEY low for at least 1 s to power on. The Air724 needs 2 s. Some boards tie PWRKEY low through a resistor for automatic power-on; GPIO control is cleaner because it lets the host reset the modem.
5. **3.3 V vs 1.8 V UART logic.** Newer modules (LTE Cat-1bis) are 1.8 V. A direct 3.3 V tie kills the I/O. Level-shift if mismatched.

## 103.3  Powering on and the boot sequence

```sh
# Pulse PWRKEY low for 1.5 s via libgpiod
gpioset gpiochip4 22=0; sleep 1.5; gpioset gpiochip4 22=1

# Modem boots over ~5–15 s; spams URCs on UART
cat /dev/ttymxc3
# RDY
# +CFUN: 1
# +CPIN: READY
# Call Ready
# SMS Ready
# +CGEV: ME PDN ACT 1
# *IPGetv4: 10.x.x.x
```

These URCs (Unsolicited Result Codes) report boot progress. Do not send AT commands before "SMS Ready" — they will return spurious ERRORs. The right pattern: spawn a reader thread that consumes the boot URCs, then enter AT command mode.

## 103.4  PPP over UART, end-to-end

```sh
apt install ppp

# /etc/ppp/peers/cellular
cat > /etc/ppp/peers/cellular <<'EOF'
/dev/ttymxc3
115200
crtscts                  # hardware flow control
defaultroute             # add default route via this link
noauth                   # carrier doesn't auth us
usepeerdns               # accept DNS servers from carrier
persist                  # auto-reconnect if dropped
maxfail 0                # never give up
holdoff 10               # wait 10 s before retry
lcp-echo-failure 4
lcp-echo-interval 30
connect "/usr/sbin/chat -v -f /etc/ppp/peers/chat-cellular"
EOF

cat > /etc/ppp/peers/chat-cellular <<'EOF'
ABORT 'BUSY'
ABORT 'NO CARRIER'
ABORT 'ERROR'
'' AT
OK ATZ
OK AT+CGDCONT=1,"IP","internet"
OK ATD*99#
CONNECT ''
EOF

pppd call cellular
```

What this does, step by step:

1. **pppd opens `/dev/ttymxc3`** at 115200, CRTSCTS.
2. **chat script runs**: sends `AT` → expects nothing → sends `AT` → expects `OK` → sends `ATZ` (reset config) → expects `OK` → sends `AT+CGDCONT=1,"IP","internet"` (set APN) → expects `OK` → sends `ATD*99#` (dial PPP) → expects `CONNECT`.
3. After `CONNECT`, the UART has switched from AT mode to **HDLC framing** — every byte is now PPP-framed.
4. **pppd takes over the file descriptor**, runs **LCP** (Link Control Protocol) — both sides negotiate MTU, auth method, magic numbers.
5. If auth required, **PAP** or **CHAP** runs (most LTE carriers skip auth here since the SIM already authenticated).
6. **IPCP** (IP Control Protocol) runs: the modem assigns an IPv4 address to our side; we accept the DNS servers it offers.
7. pppd creates **`ppp0`** netdev; configures address; if `defaultroute`, adds the default route.
8. Connection is up; pppd monitors LCP echoes for liveness; `persist` makes it reconnect on drop.

```sh
ip addr show ppp0
# 7: ppp0: <POINTOPOINT,MULTICAST,UP,LOWER_UP> mtu 1500
#   inet 10.x.x.x peer 10.x.x.x/32 scope global ppp0
```

You now have internet over a 4-wire UART. Throughput: ~1–3 Mbps on Cat-1, limited by the UART baud rate × PPP overhead.

## 103.5  How the kernel ppp_generic driver works

`drivers/net/ppp/ppp_generic.c` is the netdev side; `drivers/net/ppp/ppp_async.c` (or `ppp_synctty.c`) handles HDLC framing over the UART.

```
Userspace pppd
   │
   ▼ ioctl(/dev/ppp, PPPIOCATTACH)
   │
   ▼ ioctl(fd, TIOCSETD, N_PPP)         <- attach line discipline to /dev/ttymxc3
   │
ppp_async (line disc)                    <- de-frames HDLC, hands packets to ppp_generic
   │
   ▼
ppp_generic (netdev `ppp0`)              <- wraps PPP frames in skb, IP layer takes over
   │
   ▼
IP routing (decides next hop = ppp0)
```

Note the split: `pppd` does protocol negotiation entirely in user space (LCP, IPCP packets are sent/received by writing/reading PPP frames through the /dev/ppp ioctl), but the data path runs kernel-side via the line discipline. CPU stays low even on a Cortex-A7.

If you want to peek at the bytes:

```sh
# Trace PPP packets in/out
tcpdump -i ppp0 -nn
# Trace raw HDLC frames (rare; you'd use a logic analyzer instead)
```

## 103.6  Multiplexing AT commands with PPP — the GSM Mux problem

When you're in PPP mode, the UART can't accept AT commands — it's all HDLC. So you can't check signal strength, send SMS, or update the time while the data connection is up.

Two solutions:

### Option 1: pause PPP, send AT, resume

Bring the link down, send AT, bring it back up. Simple but works for low-frequency queries.

### Option 2: GSM 07.10 multiplexer (CMUX)

The 3GPP CMUX protocol multiplexes multiple virtual channels onto one UART. Modem implements: channel 1 = AT, channel 2 = PPP, channel 3 = NMEA GPS, etc. Linux kernel has `drivers/tty/n_gsm.c` to demux.

```sh
# Initiate CMUX on the modem
echo -e 'AT+CMUX=0\r' > /dev/ttymxc3
# Then attach n_gsm to that tty
ldattach GSM0710 /dev/ttymxc3
# /dev/gsmtty1, /dev/gsmtty2, ... appear

# PPP on channel 2
pppd /dev/gsmtty2 115200 ...
# AT commands on channel 1
echo 'AT+CSQ' > /dev/gsmtty1
```

This is the textbook embedded-cellular pattern. The kernel side (n_gsm) is small but the user-space side needs careful sequencing. Many production designs use a small daemon (e.g., `gsmmuxd`) that owns the channels and exposes them as fifos.

## 103.7  From scratch — a robust auto-reconnect daemon

Real products need PPP to come up at boot, retry on failure, and bring up an LED or report status. Here's a minimal supervisor:

`celld.sh`:

```bash
#!/bin/sh
# Cellular link supervisor: power-cycle modem, run pppd, restart on death.

MODEM_TTY=/dev/ttymxc3
PWRKEY_GPIO_CHIP=gpiochip4
PWRKEY_GPIO_LINE=22
LED_GPIO_LINE=23

set_led() { gpioset $PWRKEY_GPIO_CHIP $LED_GPIO_LINE=$1; }
pwr_pulse() {
    gpioset $PWRKEY_GPIO_CHIP $PWRKEY_GPIO_LINE=0
    sleep 1.5
    gpioset $PWRKEY_GPIO_CHIP $PWRKEY_GPIO_LINE=1
}

while true; do
    set_led 0    # off
    pwr_pulse
    sleep 8      # wait for boot
    # Wait for "SMS Ready" URC (or timeout)
    timeout 30 sh -c "while ! grep -q 'SMS Ready' $MODEM_TTY 2>/dev/null; do sleep 1; done" \
        < $MODEM_TTY
    set_led 1    # on (modem booted)

    # Bring up PPP
    pppd call cellular updetach
    rc=$?
    echo "pppd exited rc=$rc — restarting in 30 s"
    set_led 0
    sleep 30
done
```

Install as `/etc/init.d/celld` or a systemd unit. The link comes up at boot, recovers from any modem hang by power-cycling PWRKEY, and shows status on an LED. About 30 lines of shell, replacing several hundred lines of vendor C.

## 103.8  ECM mode — when the UART module has USB-style Ethernet

Newer Cat-1bis modules (Quectel ML302, EC200N) expose **USB CDC-ECM** via a built-in USB-to-UART bridge — so even though they're "UART modems," the data path is actually USB-ECM. Plug the module's microUSB into the host: `usb0` appears as Ethernet, `dhclient usb0` gets an IP, done. The UART carries only AT commands at that point.

This pattern eliminates PPP entirely while keeping the BOM low (one module, no separate USB modem chip). Recommended for any new design that can afford one USB port.

```sh
dmesg | grep cdc_ether
# cdc_ether 1-1.1:1.1: usb0: register 'cdc_ether' at ...
dhclient usb0
```

## 103.9  Lab

1. **Power on, capture boot URCs.** Wire the modem; pulse PWRKEY; `cat /dev/ttymxc3`. Watch for `RDY`, `+CPIN: READY`, `SMS Ready`.
2. **AT bring-up checklist.** Reuse `at_client.py` from Ch 102. Confirm `AT+CPIN?`, `AT+CSQ`, `AT+COPS?`.
3. **PPP up.** Configure `/etc/ppp/peers/cellular` + chat script. `pppd call cellular`. Verify `ppp0` has an IP; `curl ifconfig.io` shows the public address.
4. **Reconnect test.** Pull the antenna; LCP echo timeouts fire; `persist` makes pppd reconnect. Time the recovery.
5. **Chat script trace.** Run `pppd call cellular debug logfile /tmp/pppd.log`. Read the log line-by-line; understand every chat exchange and LCP/IPCP packet.
6. **GSM 07.10 mux.** Enable CMUX; bring up PPP on `/dev/gsmtty2` while simultaneously querying `AT+CSQ` on `/dev/gsmtty1`. Verify both work concurrently.
7. **Supervisor script.** Implement `celld.sh`; install as init. Reboot; verify `ppp0` comes up automatically.
8. **Cat-1bis with USB-ECM.** If you have an ML302 or EC200N, switch it to ECM mode; bring up `usb0` via DHCP. Compare bring-up complexity vs PPP.
9. **Throughput measurement.** `iperf3 -c <server>` over PPP at 115200 (~80 kbps), 921600 (~600 kbps), and ECM (~5 Mbps). The UART speed dominates PPP throughput; ECM is limited by Cat-1 cell capacity.
10. **SMS send/receive.** While PPP is up (via CMUX), `AT+CMGF=1`, `AT+CMGS="+1234..."`, type message, Ctrl-Z. Confirm receipt on the destination phone.

## 103.10  Pitfalls

- **No hardware flow control.** Above 9600 baud, PPP breaks. Always wire RTS/CTS and pass `crtscts` to pppd.
- **VBAT not VDD.** Powering the modem's RF section from a weak 3.3 V LDO causes TX brownouts → connection drops on transmit.
- **PWRKEY pulse too short.** Some modules want ≥2 s for power-on (Air724) and ≥3 s for power-off. Read the AT command and hardware manuals.
- **AT commands sent during boot.** Spurious ERRORs because the modem isn't ready. Wait for "SMS Ready" URC before talking.
- **Chat script timeout too short.** Default 45 s per step. LTE registration can take 30–60 s on a cold start in poor coverage. Increase `connect-delay` and chat timeouts.
- **APN typo.** Same as Ch 102 — wrong APN → PDP context fails. Carriers don't make this discoverable.
- **PPP holds the tty.** Once pppd takes the line, you can't `cat /dev/ttymxc3` to debug AT. Use CMUX or a second UART for debug.
- **NetworkManager fights pppd.** If NM is running, it may auto-take the modem. Disable NM for that tty or use NM exclusively.
- **Default route conflict.** PPP's `defaultroute` plus existing eth0 default route → routing loops. Use `replacedefaultroute` or set metric.
- **MTU 1500 vs operator MTU.** Some operators clamp at 1460 or 1430; pppd negotiates LCP MTU but TCP path-MTU discovery can still fail. Set `mtu 1430` explicitly if you see hung-large-packet symptoms.
- **CMUX framing errors silent.** Bad CRTS/CTS on the underlying UART causes n_gsm to drop frames; the per-channel ttys appear functional but data is garbled. Verify hardware flow first.

## 103.11  Going deeper

- **`pppd(8)` manual** — the canonical reference; every option matters for production reliability.
- **`chat(8)`** — the connect-script DSL.
- **`drivers/net/ppp/ppp_generic.c` + `ppp_async.c`** — the kernel side.
- **`drivers/tty/n_gsm.c`** — 3GPP 27.010 multiplexer.
- **3GPP TS 27.010** — the CMUX specification.
- **SIMCom A7670C AT Commands Manual** — module-specific extensions.
- **`gnokii`** — legacy but instructive open-source modem manager.
- **Ch 102** for USB modem comparison.
- **Ch 104** for low-power NB-IoT/Cat-M1 over UART (same toolchain, different power profile).

---

> Next chapter: **Chapter 104 — NB-IoT / Cat-M1** — the low-power-cellular subset designed for battery-powered IoT sensors.
