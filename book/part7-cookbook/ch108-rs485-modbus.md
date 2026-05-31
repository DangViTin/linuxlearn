---
chapter: 108
title: RS-485 + Modbus RTU (MAX485, SP3485, ADM2483, MAX13487)
part: VII — Device cookbook
estimated_pages: 14
status: draft
---

# Chapter 108 — RS-485 + Modbus RTU

> **What:** **RS-485** — the differential half-duplex serial bus that has carried industrial data since 1983, still ubiquitous in factories, building automation, solar inverters, and HVAC. We compare **MAX485** (5 V, 5 Mbps, the canonical chip), **SP3485** (3.3 V, 10 Mbps), **ADM2483** (isolated, for noisy environments), **MAX13487** (auto-direction — eliminates the GPIO control headache). On Linux, we wire RS-485 to a UART, enable the kernel's RS-485 mode (`SER_RS485_ENABLED`), and use **`libmodbus`** to implement a **Modbus RTU** master/slave talking to real inverters, energy meters, and PLCs.
> **Why:** every industrial site has Modbus RTU. Solar inverters, energy meters, BMS systems, irrigation controllers, VFDs (variable-frequency drives), even building HVAC — they all expose data over Modbus RTU on RS-485. Your i.MX6ULL becomes the data collector / gateway, polling 5–50 devices and bridging to MQTT/cloud. RS-485 is unglamorous but irreplaceable; learning it opens an enormous market (industrial IoT) that pure-WiFi/Ethernet devices can't touch.
> **Focus:** **RS-485 is half-duplex differential signaling on a 2-wire bus; you must control the line driver direction (TX or RX) at sub-bit-time precision, and Modbus framing depends on inter-character timeouts that vary with baud rate**. The kernel's RS-485 ioctl handles DE/RE control automatically *if* your UART supports it; otherwise you bit-bang via a GPIO with sub-microsecond latency requirements that are hard on a non-RT Linux. Auto-direction transceivers (MAX13487) solve this in hardware. Termination (120 Ω at each bus end), biasing (fail-safe to known idle state), and ground reference (a multi-meter check across grounds is mandatory before connecting devices powered from different sources) are the three things that break a working bench setup when you deploy it.

## 108.1  RS-485 physics

```
   Differential pair (twisted), 120 Ω characteristic impedance
   A line: ─────────────┐ ┌───────┐ ┌──────────────
                        │ │       │ │
                         X         X        <- signal swing 1.5–5 V
                        │ │       │ │
   B line: ─────────────┘ └───────┘ └──────────────

   Receiver sees (A − B). Above +200 mV = "1"; below −200 mV = "0".
   ~24 V common-mode range. Tolerant of ~7 V ground difference.
```

Why it works for long distance:
- Differential rejects common-mode noise (motor brushes, switching supplies).
- 120 Ω matched impedance + termination resistors → no reflections at high baud / long cable.
- Multidrop: up to 32 standard receivers (more with low-load chips); one transmitter at a time.

Cable lengths:
- 100 m at 1 Mbps
- 1200 m at 100 kbps
- Up to 4 km at 9600 (the Modbus default)

Topology: **daisy-chain only** (no star, no T-stubs > 30 cm). Termination at both physical ends.

```
   [Master] ───── stub ─── ┬ ────────── ┬ ─── stub ─── [Slave 3]
                          [Slave 1]   [Slave 2]
   120 Ω here ┘                                              └ 120 Ω here
              and pull-up to +5V (bias)
              and pull-down to GND (bias)
              for fail-safe (idle line = logic "1")
```

## 108.2  Transceiver comparison

| | MAX485 | SP3485 | ADM2483 | MAX13487 |
|---|---|---|---|---|
| Supply | 5 V | 3.3 V | 5 V (isolated) | 3.3 V or 5 V |
| Max speed | 2.5 Mbps | 10 Mbps | 0.5 Mbps | 16 Mbps |
| DE/RE control | GPIO | GPIO | GPIO | **automatic** (senses TX activity) |
| Isolation | none | none | 2.5 kV galvanic | none |
| Receivers per bus | 32 | 32 | 256 | 256 |
| Cost | $0.50 | $0.80 | $5 | $1.50 |

**Pick guide:**
- **MAX485 / SP3485** — bench testing, simple single-board projects. Manual DE/RE control via GPIO.
- **MAX13487** — production, especially on Linux where sub-bit-time DE control is hard. Auto-direction = "wire it up and forget."
- **ADM2483** — when your bus has 24 V power devices, motors nearby, long outdoor runs. Isolation prevents ground loops from blowing up the SoC.

## 108.3  Wiring RS-485 to the i.MX6ULL

For a manual-direction transceiver (MAX485):

```
       ┌─────────┐                              ┌────────┐
i.MX  ─┤ TXD     ├──────────────────────────────┤ DI     │
UART4  │ RXD     ├──────────────────────────────┤ RO     │  MAX485
GPIO  ─┤ DE+RE   ├──────┬───────────────────────┤ DE     │
       │         │      └───────────────────────┤ RE     │  (active high)
       │         │   5 V ─────────────────────  ┤ VCC    │
       │         │   GND ────────────────────── ┤ GND    │
       │         │                              ┌ A      │ ──── twisted ─── A line
       │         │                              └ B      │ ──── twisted ─── B line
       └─────────┘                              └────────┘
                              120 Ω termination at both ends of A-B
                              +5V via 680Ω to A; GND via 680Ω to B (bias)
```

DE and RE are tied (active-high for DE, active-low for RE = same line drives both, so you assert it high to transmit).

For MAX13487 auto-direction, no DE/RE — just connect; the chip senses TX activity and switches direction.

Termination: 120 Ω across A-B at both ends of the bus. Bias resistors (680 Ω to +5 V on A, 680 Ω to GND on B) ensure the bus reads logic-1 when no one is driving — required by Modbus RTU's frame-detection.

## 108.4  Kernel RS-485 mode

The i.MX UART driver can manage DE/RE automatically if your DT specifies it. This is much better than bit-banging from user-space (which is jitter-prone on non-RT Linux).

```dts
&uart4 {
    pinctrl-names = "default";
    pinctrl-0 = <&pinctrl_uart4>;
    rts-gpios = <&gpio1 28 GPIO_ACTIVE_HIGH>;
    linux,rs485-enabled-at-boot-time;
    rs485-rts-active-high;
    rs485-rts-delay = <0 0>;       /* µs before/after frame */
    status = "okay";
};
```

The driver toggles RTS automatically around each TX. From user-space, also:

```c
struct serial_rs485 conf = {0};
conf.flags = SER_RS485_ENABLED | SER_RS485_RTS_ON_SEND;
conf.delay_rts_before_send = 0;
conf.delay_rts_after_send = 0;
ioctl(fd, TIOCSRS485, &conf);
```

Verify:

```sh
ioctl-test /dev/ttymxc3 TIOCGRS485
# flags: enabled, RTS_ON_SEND
```

Some UARTs (i.MX has integrated "9-bit mode" with hardware DE) do this directly without GPIO toggling — check your reference manual for SER_RS485_AUTO.

If the kernel can't manage it, user-space `libmodbus` does GPIO toggling — works at 9600 (1 ms per byte = plenty of margin), struggles above 115200.

## 108.5  Modbus RTU framing

The protocol on the wire:

```
   [SlaveAddr] [FunctionCode] [Data...] [CRC16-Lo] [CRC16-Hi]
       1B            1B          N B         2B
   Frame end: 3.5-character silent gap (no bytes for 3.5 × char-time)
```

Slave addresses 1–247; 0 = broadcast. Function codes:

| Code | Name | What |
|---|---|---|
| 0x01 | Read Coils | read bit-addressed outputs |
| 0x02 | Read Discrete Inputs | read bit-addressed inputs |
| 0x03 | Read Holding Registers | read 16-bit registers |
| 0x04 | Read Input Registers | read read-only 16-bit registers |
| 0x05 | Write Single Coil | write one bit |
| 0x06 | Write Single Register | write one 16-bit register |
| 0x0F | Write Multiple Coils | write many bits |
| 0x10 | Write Multiple Registers | write many 16-bit registers |
| 0x17 | Read/Write Multiple Registers | combined |

CRC: standard Modbus CRC-16, polynomial 0xA001, initial 0xFFFF.

Frame separation by **inter-character timeout**:
- Inter-character (within frame): < 1.5 char-times
- Inter-frame: ≥ 3.5 char-times

At 9600 baud, 1 char = 11 bits / 9600 = 1.146 ms; 3.5 char = 4 ms idle to detect end-of-frame.

This is where Linux can struggle: the kernel buffers UART data; user-space sees it in chunks; reconstructing the precise inter-character gaps requires the kernel to timestamp byte arrivals. `libmodbus` handles this with `select()` + read-timeout heuristics; it works fine at ≤ 38400.

## 108.6  Using libmodbus from C

```c
#include <modbus/modbus.h>

modbus_t *ctx = modbus_new_rtu("/dev/ttymxc3", 9600, 'N', 8, 1);
modbus_rtu_set_serial_mode(ctx, MODBUS_RTU_RS485);   /* uses kernel RS485 mode */
modbus_set_slave(ctx, 1);
modbus_connect(ctx);

uint16_t regs[32];
int rc = modbus_read_registers(ctx, 0x0000, 16, regs);
if (rc == -1) {
    fprintf(stderr, "Read failed: %s\n", modbus_strerror(errno));
} else {
    for (int i = 0; i < 16; i++)
        printf("reg[0x%04X] = %u (0x%04X)\n", i, regs[i], regs[i]);
}

modbus_close(ctx);
modbus_free(ctx);
```

That's an entire Modbus master. Replace `modbus_read_registers` with `modbus_write_register`, `modbus_read_bits` etc. for other ops.

For a Python prototype: `pymodbus` mirrors the API and is great for interactive testing.

## 108.7  A worked example — reading a solar inverter

Solar inverters (Growatt, Goodwe, SMA, Sungrow) speak Modbus RTU at 9600 8N1 on a built-in RS-485 port. Map (typical, vendor-specific):

| Register | Meaning |
|---|---|
| 0x0001 | inverter status (0=waiting, 1=running, ...) |
| 0x0003 | PV1 voltage (×0.1 V) |
| 0x0004 | PV1 current (×0.1 A) |
| 0x0007 | total grid frequency (×0.01 Hz) |
| 0x000C | total active power (×0.1 W) |
| 0x001A | today's energy (×0.1 kWh) |

Polling loop:

```python
import time, json, paho.mqtt.publish as publish
from pymodbus.client.sync import ModbusSerialClient

client = ModbusSerialClient(method='rtu', port='/dev/ttymxc3',
                            baudrate=9600, stopbits=1, parity='N', timeout=1)
client.connect()
while True:
    rr = client.read_holding_registers(0x0001, 30, unit=1)
    if rr.isError(): time.sleep(5); continue
    data = {
        'status': rr.registers[0],
        'pv1_v':  rr.registers[2] / 10.0,
        'pv1_i':  rr.registers[3] / 10.0,
        'freq':   rr.registers[6] / 100.0,
        'power':  rr.registers[11] / 10.0,
        'energy_today': rr.registers[25] / 10.0,
    }
    publish.single('home/solar/inverter', json.dumps(data), hostname='localhost')
    time.sleep(5)
```

30 seconds of Python, ~$15 of hardware, you have your inverter on Home Assistant / Grafana.

## 108.8  Modbus slave — make your i.MX6ULL a peripheral

```c
modbus_t *ctx = modbus_new_rtu("/dev/ttymxc3", 9600, 'N', 8, 1);
modbus_set_slave(ctx, 5);                          /* our address */
modbus_rtu_set_serial_mode(ctx, MODBUS_RTU_RS485);
modbus_connect(ctx);

modbus_mapping_t *mb = modbus_mapping_new(100, 100, 100, 100);  /* coils, discrete, holding, input */

for (;;) {
    uint8_t query[MODBUS_RTU_MAX_ADU_LENGTH];
    int n = modbus_receive(ctx, query);
    if (n > 0) {
        /* Update mb->tab_input_registers etc. from your sensors */
        mb->tab_input_registers[0] = read_temperature();
        modbus_reply(ctx, query, n, mb);
    }
}
```

Now your i.MX6ULL is slave 5 on the bus; any master can poll it for sensor data.

## 108.9  Lab

1. **RS-485 transceiver up.** Wire MAX485. Connect A↔A, B↔B between two boards. Enable kernel RS-485 mode. Send raw bytes; verify echo on the other end.
2. **CRC check.** Send a Modbus query by hand (8 bytes); compute CRC with the standard table; verify the slave's response.
3. **libmodbus master.** Compile the master example; talk to a real device (DDS energy meter, Growatt inverter, MAX31865 RTD module with Modbus-RTU). Read all available registers.
4. **Multi-slave bus.** Add 3+ devices to the same bus with unique addresses (1, 2, 3). Round-robin poll them; verify no collisions.
5. **Termination test.** Remove the 120 Ω termination. Long cable (10+ m). Watch for CRC errors. Add termination back; verify clean.
6. **Bias test.** Disconnect master. Without bias resistors, the bus floats and slaves see random noise as start-bits. Add bias; bus stays idle-high.
7. **Auto-direction.** Replace MAX485 with MAX13487. Confirm communication works without DE GPIO. Try at 115200 — auto-direction's main benefit.
8. **Slave mode.** Implement a Modbus slave on the i.MX6ULL exposing 16 registers; have a separate master poll it.
9. **MQTT gateway.** Bridge the inverter data through MQTT (use the worked example). Plumb to Grafana for a 24-hour solar production chart.
10. **Long-cable test.** Run 100 m of CAT5 between two boards; baud test at 9600/19200/38400/115200; note where errors start.

Commit modbus configs, register maps for one real device, gateway script to `code/ch108-rs485-modbus/`.

## 108.10  Pitfalls

- **No bias resistors → idle floats.** Bus reads garbage; slaves think the master is constantly framing data. Fail-safe biasing (typically built into MAX13487 and similar) is mandatory.
- **One-end termination only.** Reflections cause CRC errors on long buses. Always terminate both ends.
- **Ground potential difference.** Long bus → different equipment grounds may differ by several volts. RS-485 tolerates ±7 V common-mode; beyond that, transceivers latch up or die. Use isolated transceivers (ADM2483) for long outdoor runs or different-power-source bus segments.
- **GPIO DE jitter.** User-space-toggled DE has tens-of-µs jitter on non-RT Linux — at 115200 baud, one bit is 9 µs. Half a byte can be lost. Use kernel RS-485 mode or auto-direction transceivers.
- **Inter-character timeout too short.** Linux may deliver bytes in chunks every 10 ms; libmodbus's read loop must allow for that. Default timeouts work; very tight timeouts cause spurious "incomplete frame" errors.
- **Wrong baud / parity.** Modbus default is 9600 8N1, but devices often use 19200 8E1 or 38400 8N2. Always check the device manual; libmodbus's `parity` parameter is 'N', 'E', or 'O'.
- **Wrong register addressing convention.** Some vendors document registers as 1-based (40001); the actual wire-level is 0-based (0x0000). The mapping is "subtract 1 and use the 0x03 function code."
- **Holding vs input registers.** Function 0x03 = holding (R/W); 0x04 = input (R-only). Vendors mix these confusingly. Trial-and-error or careful manual reading.
- **Float-encoding ambiguity.** A 32-bit float spans two 16-bit registers; the byte/word order varies per vendor (big/little/mixed endian). Test with a known reading (e.g., grid voltage near 230 V).
- **Modbus TCP confusion.** Some devices speak Modbus TCP on Ethernet; the protocol's data section is the same as RTU but with an MBAP header instead of CRC. libmodbus has separate `modbus_new_tcp()` for that. Don't mix them up.

## 108.11  Going deeper

- **Modicon Modbus Protocol Reference (Schneider)** — the original specification.
- **Modbus.org** — current spec downloads (free registration).
- **`libmodbus`** docs — RTU + TCP, master + slave, mature.
- **`pymodbus`** — Python alternative, great for prototyping.
- **TI / Maxim RS-485 application notes** — termination, biasing, ESD protection.
- **Drivers/tty/serial/imx.c** — the i.MX UART driver's RS-485 implementation.
- **EIA-485 standard** (TIA-485-A) — the physical layer spec.
- **Ch 109 (LIN)** + **Ch 110 (CAN)** — siblings in the "industrial bus" family.

---

> Next chapter: **Chapter 109 — LIN bus** — sub-CAN bus for automotive bodywork.
