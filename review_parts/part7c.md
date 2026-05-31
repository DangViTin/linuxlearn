# Part VIIc — Cookbook (Wireless/Cellular/Industrial/Power): Review

## Cross-cutting observations
- Recurring pattern of using the placeholder `compatible = "rohm,dh2228fv"` for spidev binding. Since Linux 4.15+, mainline kernels actively warn when this name is abused as a generic spidev stand-in (`spidev: warning: please use a real DT compatible`). The book should either (a) document binding via `spidev` module parameters / DT overlay with a proper non-warning compatible, or (b) acknowledge this warning explicitly so readers know `dmesg` complaints are expected. Today it appears unflagged in chapters 98, 99, 101, 105, 106.
- Many chapters claim "no mainline driver, use spidev + user space" without showing the *real* kernel infrastructure that does exist (e.g., `drivers/net/ieee802154/`, `nl802154`, `regmap-spi`, `serdev`). For a book about embedded Linux driver internals, "Part VII must show driver internals + a from-scratch implementation" — but chapters 100, 102, 103, 104 are mostly userspace-daemon configuration recipes with no kernel walk. Either tag those chapters as "integration recipes" or add a kernel-internals section.
- The reader is an MCU engineer. Almost no chapter explicitly relates the Linux device model back to "what you'd write on STM32." Comparisons like "this is the same as the STM32 HAL_SPI_Transmit you've used, except wrapped in an spi_device" would massively shorten the on-ramp. Currently the MCU bridge appears only in scattered asides.
- ASCII figures are often present but lack a key "subsystem stack" diagram for each chapter (e.g., where in the stack does the user lab code sit vs the kernel driver vs the userspace daemon). A consistent 5-row stack diagram per chapter (HW → kernel driver → uapi → daemon → app) would tie the whole Part VII together.
- Test/verification subsections give shell commands and expected outputs, but very few chapters show *expected dmesg lines* — the single most useful debug surface for an MCU engineer just learning Linux. Add a "what dmesg should look like on a healthy probe" block.
- Driver internals walks are paraphrased pseudo-C ("Walk of nrf24_write paraphrased"). For a reference book this should cite the file:line in the kernel tree (or out-of-tree repo) used so the reader can open it side-by-side. Without that the snippets read as invented.
- Cellular chapters (102–104) repeat ModemManager/NetworkManager bring-up. Consider consolidating that material into a shared "cellular concepts" intro chapter so the per-modem chapters can focus on what differs (band sets, AT extensions, low-power modes, certification).
- The book uses Unicode box-drawing in code blocks. On older terminals + PDF builds these may not render; consider providing ASCII-only fallbacks or noting font requirements.
- Several chapters reference "Ch 95–97" or "Ch 91" for cross-references; verify these chapter numbers are still correct after any TOC renumbering.

## Ch98 — LoRa
### Readability
- Sentence "The radio is easy. The link budget is the engineering." is good. But the intro `> Focus:` paragraph is one 4-line wall — break into two bullets ("CSS gives ~−137 dBm…" / "tune SF/BW/CR/preamble…").
- "Most engineers cargo-cult the 'Arduino LoRa library'…" is editorial; either embrace this tone consistently across Part VII or soften ("Most introductory tutorials hide the modulation details…").
- "the chip transmits OK at first but receive sensitivity is –80 dBm" — clarify "−80 dBm minimum detectable signal" (currently reads ambiguously, could be misread as "−80 dBm sensitivity is fine").

### MCU-engineer friendliness
- Reader knows SPI from MCU; reinforce by stating outright "in MCU code you'd do `HAL_SPI_Transmit(&hspi, &tx, 2, 100)` — `ioctl(SPI_IOC_MESSAGE)` is the Linux equivalent, with the kernel driver doing chip-select + clock-rate negotiation for you."
- The "command vs register-mapped" distinction between SX1276 and SX1262 should mention this is the same shift the reader saw between, e.g., a NOR flash (register-style) and an EEPROM with opcodes — make the analogy explicit.

### Missing examples / figures
- No diagram showing "where the user-space lab driver sits vs where a netdev-style kernel driver would live." Add a stack diagram: hardware → SPI controller (ecspi) → spidev OR sx127x kernel driver → userspace app OR daemon.
- A LoRaWAN class A/B/C timing diagram would massively help. Currently only mentioned as a list of three classes; show "JoinRequest uplink window + RX1/RX2 downlink windows" to make Class A concrete.
- Air-time formula is referenced but not shown. Either include the formula `Tpacket = Tpreamble + Tpayload(SF,BW,CR,n_bytes,DE,CRC,IH)` or link to Semtech AN1200.13.

### Insufficient depth
- §98.5 "the kernel side" lists three reasons no mainline driver exists, but should also discuss the existing `linux-wpan` infrastructure (ieee802154 subsystem) for comparison — explain why LoRa *couldn't* fit there cleanly (no MAC standard).
- The "translating to SX1262" table is a great hook, but the from-scratch SX1262 code is left as a stretch lab. For depth this chapter promises, include at minimum a `sx1262_setpacketparams()` function in real code.

### Technical errors
- Bitrate formula: "Bitrate ≈ SF × BW / 2^SF × CR" — the CR here should be the *coding rate fraction* (4/(4+CR_idx)), and the formula as written is dimensionally consistent only with specific conventions. Recommend stating it as `Rb = SF × (4/(4+CR_idx)) × BW / 2^SF`.
- "+22 dBm internal PA" for SX1262 is correct; "+118 mA at +22 dBm vs ~120 mA at +20 dBm for SX1276" — SX1276's +20 dBm PA_BOOST is typically ~120 mA but Semtech also lists +17 dBm at ~90 mA; clarify the operating point.
- RSSI offset claim "−157 + RSSI for HF; subtract 164 for LF" — the SX1276 datasheet has it as `RSSI = -164 + reg` for LF and `RSSI = -157 + reg` for HF; the code uses `-157 + reg` for HF correctly, but the comment "subtract 164 for LF" is misleading — it's *replace* with −164, not subtract.
- The DT placeholder `compatible = "rohm,dh2228fv"` is the well-known spidev hack; flag the kernel warning explicitly.
- `BURST_WRITE(FIFO, payload, N)` step 9 happens before step 7 (PayloadLength) in some example flows; clarify the FIFO/PayloadLength ordering — the SX1276 datasheet's TX flow has PayloadLength set before FIFO write in some modes.

### Knowledge prerequisites missing
- Assumes the reader knows what "duty cycle" is in regulatory terms (ETSI 1% per hour). One sentence on regulatory frameworks (ETSI EN 300 220, FCC Part 15.247) would help.
- Assumes familiarity with `libgpiod` (mentioned but not introduced); cross-ref the earlier GPIO chapter.

### Other
- Lab item 9 "Switch to SX1262 (stretch)" is too vague. Either commit to providing the SX1262 reference code in the book repo, or remove and replace with a smaller stretch item.
- §98.10 "Concentrator SPI clock too fast" — SX1303 supports up to 8 MHz; this is correct but mention also that SX1302 supports the same; the wording "8 MHz" needs a chip-rev qualifier.

## Ch99 — Sub-GHz proprietary
### Readability
- §99.1 table: "Address-aware? yes (Enhanced ShockBurst)" — the `Enhanced ShockBurst` markdown is inside a table cell with backticks; renders awkward in some markdown processors. Use bold or plain text.
- "the in-tree wireless dir does not contain this — verify with current kernel" parenthetical in §99.6 leaks author-note language into final text. Decide and commit ("There is no in-tree CC1101 driver in modern kernels (last reviewed against v6.x)").

### MCU-engineer friendliness
- The state-machine framing is excellent for an MCU reader. Reinforce: "this is essentially the same state diagram you'd code in an STM32 LL driver, except now it's distributed across SPI commands."
- Mention that "Enhanced ShockBurst" auto-ACK is functionally what STM32 + nRF24 Arduino libraries already gave the reader — but now you see the wire-level mechanism.

### Missing examples / figures
- A figure showing nRF24's TX FIFO → RF → auto-ACK → STATUS flag wakeup sequence (timeline diagram, microseconds-scale) would be golden for an MCU reader.
- No oscilloscope/logic-analyzer trace example for the SPI command stream during a TX burst. A captured trace would make the "STATUS comes back in the first byte, free" comment land much harder.

### Insufficient depth
- §99.6 CC1101 register configuration says "40 lines from SmartRF Studio" and stops there. For a from-scratch promise, include at least one fully filled register table for a specific configuration (e.g., 868 MHz / 2-FSK / 38.4 kbps / GFSK) so the reader can compile/run without an external tool.
- No discussion of how the CC1101 `MCSM*` registers govern automatic state transitions (RXOFF_MODE, TXOFF_MODE) — these are the most underdocumented and bite users in production.
- The "from-scratch CC1101" §99.6 is only 30 lines; promise of "300 lines" is unfulfilled. Either deliver the 300-line version or restate scope.

### Technical errors
- "TX_ADDR ≠ RX_ADDR_P0" pitfall: phrased awkwardly. Should say "On the PTX, RX_ADDR_P0 must equal TX_ADDR so the auto-ACK frame is received on pipe 0." Currently reads as if the inequality itself is the bug.
- "CC1101 has no auto-ACK" — true that there's no hardware auto-ACK frame, but CC1101 does have hardware CRC, address filtering, and an "ACKnowledgement" handled via `MCSM1` RX→TX flip on packet receipt. Worth mentioning to be precise.
- "every WiFi, BT, microwave oven, baby monitor uses 2.4 GHz" — "Sub-GHz (CC1101 433/868) is 10× quieter" — quantification is hand-wave; soften to "typically much less congested."
- nRF24L01+ "1 Mbps TX burst draws ~12 mA peaks" — datasheet lists ~11.3 mA at 0 dBm 1 Mbps; "peaks" is misleading because that's a continuous current, not a burst peak. The PA causes the rail droop, but for a different reason than implied.

### Knowledge prerequisites missing
- "FCS is XOR of LEN through last data byte" appears in chapter 100, not here; for CC1101 the chapter doesn't define FCS at all. Define on first use.

### Other
- The DT example uses `compatible = "rohm,dh2228fv"` (see cross-cutting).
- Lab item 8 "Bridge test" references Grafana with no prior context; either omit or hand off to a chapter that covers MQTT→Grafana.

## Ch100 — ZigBee / Thread / 802.15.4
### Readability
- Intro `> What:` is overlong; the bullet "i.MX6ULL is the gateway, not a node" is the load-bearing insight — pull it to the very first sentence.
- §100.2 RCP/NCP/SoC table is good. But "Spinel" appears with no expansion until §100.6. Define on first mention.

### MCU-engineer friendliness
- An MCU reader is unlikely to have used HCI-style host-controller protocols. Forward-reference Ch 95's BLE HCI section explicitly and say "Spinel is to Thread what HCI is to BLE."
- Highlight that nRF52840 firmware is in C (Zephyr/nrfx) — this matters because the reader can in principle modify it. Make the boundary "this is the chip-side firmware you don't write" vs "this is the Linux side you do" sharper.

### Missing examples / figures
- No diagram of the otbr data plane: Thread mesh → wpan0 (netdev) → IPv6 routing → eth0 upstream. The §100.6 description is text-only.
- Sequence diagram of a Thread device joining (KEK exchange, MeshLocal address allocation) would help readers reason about pairing failures.

### Insufficient depth
- This chapter is mostly *daemon configuration* (zigbee2mqtt, otbr-agent). Per the cookbook depth requirement, add at least one section that walks an actual in-tree kernel driver: `drivers/net/ieee802154/at86rf230.c` is mentioned but never walked. Show `at86rf230_xmit_complete()` or `at86rf230_isr()` to fulfill the driver-internals promise.
- The "from-scratch" §100.9 is a single 4-line `iwpan` invocation. That's not a from-scratch implementation. Either build a tiny `AF_IEEE802154` raw socket sender/receiver in C, or rename the section.

### Technical errors
- "WiFi ch 1: ████ ... WiFi ch 6: ████ ... WiFi ch 11: ████" — visually places these as if they're discrete; clarify that each WiFi 2.4 GHz channel is ~22 MHz wide and overlaps multiple ZigBee channels.
- "802.15.4 PHY: −96 dBm receiver sensitivity (vs LoRa SF12's −137; vs BLE 1M's −93)" — typical 802.15.4 sensitivity is −97 to −101 dBm depending on chip; −96 is conservative but worth citing the chip rather than asserting as a PHY property.
- "Frame format: SOF=0xFE, …, FCS is XOR of LEN through last data byte" — the TI ZNP framing FCS is correct; verify this is XOR (some texts call it "CRC-XOR"). The cited TI document is "Z-Stack Monitor and Test API," confirm spelling.
- "Apple HomeKit, Google Nest, Matter" under Thread ecosystem — Matter is a separate row (it's an *application* layer over Thread/WiFi). Putting it in the same cell is technically wrong even though §100.8 clarifies.

### Knowledge prerequisites missing
- Reader hasn't necessarily met IPv6 link-local vs ULA addressing; one paragraph on `fe80::/10` vs `fd00::/8` would help (or forward to the networking part of the book).
- 6LoWPAN compression isn't explained even though `lowpan0` is created. A sentence on header compression would close the loop.

### Other
- Channel-selection guidance "ZigBee-friendly: 15, 20, 25, 26" — channel 26 has FCC TX-power restrictions in the US; flag this.

## Ch101 — UWB ranging
### Readability
- §101.1 SS-TWR vs DS-TWR equations are dense; introduce the *intuition* first ("DS-TWR adds a second round-trip so any constant clock drift appears symmetrically and cancels in the math").
- Some sentences mix abbreviations (DWT, DTU, dtu, uus). Standardize and define on first use: DTU (device time unit), UUS (microseconds, scaled). Currently §101.5 uses both `dtu` and `DWT_TIME_UNITS` without unifying.

### MCU-engineer friendliness
- MCU reader knows time-of-flight from MCU TIM input-capture (e.g., ultrasonic range sensors). Relate: "this is the same as input-capture timestamping a pulse, except the timestamp has 64 GHz resolution in chip silicon."
- The antenna-delay calibration is a familiar concept (cable-delay calibration in lab equipment); make that bridge.

### Missing examples / figures
- A figure showing the leading-edge detection / first-path correlation vs multipath peaks would convey *why* UWB is accurate where BLE/RSSI is not. Reference Qorvo's "Channel Impulse Response" plot.
- A trilateration geometry figure (3 anchors + tag, three circles intersecting) for §101.6 — currently it's algebra only.

### Insufficient depth
- §101.5 from-scratch DS-TWR initiator code is incomplete (full version is hand-waved at end). Either include the full responder counterpart in the book or in a clearly linked code repo path.
- The chapter does not walk an out-of-tree driver (`thotro/dw1000-driver` is just listed in §101.11). Drop in a code walk of the most interesting function (the IRQ handler that extracts the RX timestamp from the FAQS register).
- No mention of the `nl802154` infrastructure or whether UWB could plug in as a 4z-MAC variant on top of `at86rf230`. Even a one-line "this is currently not in the kernel ieee802154 subsystem" closes the loop.

### Technical errors
- DEV_ID values: DW1000 returns `0xDECA0130` (correct in §101.10) but the code in §101.5 checks `0xDECA0302` for DW3000. Datasheet confirms DW3000 reads `0xDECA0302`; double-check the responder code mirrors this.
- "the 40-bit counter at 64 GHz wraps every ~17 s" — 2^40 / 64e9 = 17.18 s, correct.
- "1 µs = 65536 DWT ticks" — DWT tick is 1/(499.2e6 × 128) ≈ 15.65 ps; 1 µs / 15.65 ps ≈ 63897, not 65536. The factor 65536 is `UUS_TO_DWT_TIME` where UUS is a "scaled µs" used internally — clarify the unit; otherwise readers computing distances will get them wrong by ~2.5%.
- "DS-TWR achieves the ~10 cm accuracy spec" — typical figure is 10 cm 1-sigma in benign environments; in NLOS/multipath it degrades to 30–50 cm. Caveat needed.
- "60 µAs" / "75 µAs" energy budget for TWR — units inconsistent (Coulombs vs Ah). Recheck.

### Knowledge prerequisites missing
- No introduction to "PRF" (pulse repetition frequency) before the table cites it. Define on first use.
- Reader needs to know that UWB transmit power is FCC-restricted to −41 dBm/MHz EIRP — mention this constraint upfront.

### Other
- "Most readers won't do this" preamble for §101.9 is honest but odd for a cookbook; either commit to the recipe or drop it.

## Ch102 — USB 4G LTE modems
### Readability
- Intro `> What:` paragraph is one long sentence; break it. "Four-layer onion" metaphor in `> Why:` is nice; carry it forward into §102.3.
- "Switching modes is one AT command + reset" — true but reader may want to know which AT command lives where; the actual command is later in §102.7.

### MCU-engineer friendliness
- MCU reader has likely used AT-command modems via UART. Lead with "the AT interface you know from SIM800/SIM900 is unchanged — what's new is the USB composite device and the QMI/MBIM data path."
- The driver-binding table in §102.3 is exactly the kind of "where does my packet actually go" diagram MCU readers need. Reinforce by mapping back to: "on STM32 + USB-host, you'd write code to enumerate each interface yourself."

### Missing examples / figures
- A `dmesg` walkthrough showing the actual kernel lines as a Quectel EC25 enumerates would be invaluable (drivers binding to each interface). Currently only mentioned in lab step 1.
- Sequence diagram of QMI session start: `qmicli` → `cdc-wdm0` → modem → `WDS_START_NETWORK` reply → `wwan0` IP assignment.

### Insufficient depth
- The chapter promises "a QMI session opener using libqmi from scratch" but never delivers a code listing — only `qmicli` invocations. For depth, add a small C example using `libqmi-glib` to send `QmiMessageWdsStartNetwork`.
- `qmi_wwan_probe()` walk is 8 lines and uninformative. Either expand to show the QMI/QMAP data-path framing or remove.

### Technical errors
- "USB modems are autobound — no DT needed beyond ensuring USB-OTG/Host is enabled" — true. But the `vbus-supply` example doesn't always provide 2.5 A; consider clarifying that the regulator on iMX6ULL EVK is typically a 500 mA `reg_usb_otg1_vbus`, hence the brownout pitfall.
- "PPP throughput cap of ~1 Mbps" — closer to 0.5–1 Mbps with byte stuffing; "1–2 Mbps" elsewhere in the chapter contradicts.
- Quectel PIDs: 2c7c:0125 is correct for EC25 in default ECM+AT mode; pure-QMI is sometimes 0x0121 or 0x0125 depending on firmware. Worth caveating: "PIDs depend on firmware build; treat the table as illustrative."
- "AT+QCFG="usbnet",0 sets QMI" — value 0 is RMNET/QMI for EC25 firmware ≥ some build; older firmware uses different mapping. Add firmware version caveat.
- "T-Mobile: `fast.t-mobile.com`" — that APN is obsolete; current is `fast.t-mobile.com` or `epc.tmobile.com` depending on plan; recommend pointing to a maintained APN database rather than hardcoding.

### Knowledge prerequisites missing
- USB composite-device concept (one device, multiple interfaces) should be introduced or back-referenced; an MCU reader who's only used UART modems may not know this.
- ModemManager's D-Bus integration is implied; one line on "ModemManager is a D-Bus daemon; mmcli/nmcli are D-Bus clients" would help.

### Other
- Lab item 10 cross-references Ch 91 (WiFi); verify chapter numbering.
- §102.10 "qmi-firmware-update needed" — link to Quectel's official tool, not a community wrapper, to avoid bricking risk.

## Ch103 — UART AT-command modems
### Readability
- `> What:` intro is dense. Splitting on "the trade:" into its own bullet would be cleaner.
- "PPP is a circa-1989 link protocol" tone is good; consistent voice with Ch 98.

### MCU-engineer friendliness
- MCU readers have used SIM800/SIM900 over UART; this is a fantastic anchor. State up front: "This is the same modem you've already used from STM32 + UART. The only new thing is `pppd` and the kernel `n_ppp_async` line discipline."
- Walk the line-discipline concept explicitly — MCU readers don't know what a `TIOCSETD` is. One paragraph: "in MCU code you'd parse PPP in your own code; on Linux, `setldisc(N_PPP)` tells the kernel `tty` subsystem to do HDLC framing in-kernel."

### Missing examples / figures
- A timing diagram of the PPP bring-up: AT mode → ATDT*99# → CONNECT → LCP CONFREQ/CONFACK → IPCP CONFREQ/CONFACK. Currently only described in prose.
- A figure for the n_gsm CMUX channel multiplexing: one UART → many `gsmttyN` virtual UARTs.

### Insufficient depth
- §103.5 "How ppp_generic works" is half a page; for a from-scratch-internals book this should walk `ppp_input()` and `ppp_async_input()`. Show the HDLC byte-stuffing and FCS-16 logic.
- The "from-scratch supervisor" §103.7 is a shell script. The cookbook depth requirement wants driver internals — consider adding a tiny C program that uses raw HDLC framing without pppd, to demonstrate what pppd actually does.

### Technical errors
- "max ~5 Mbps (versus 150 Mbps over USB-QMI), and you live with PPP overhead" — at 115200 baud, PPP throughput is bounded to ~10 KB/s ≈ 80 kbps after framing. To get "5 Mbps" you'd need >5 Mbps UART (Linux supports up to 4 Mbaud on many i.MX UARTs but not all). State the baud rate explicitly.
- "PPP over UART, ~1–3 Mbps on Cat-1" — at 115200 baud, this is impossible (115.2 kbps line rate); needs higher baud rate. Recommend mentioning 921600 baud and clarifying that "5 Mbps" requires the modem's high-speed UART option.
- "echo 'AT' > /dev/ttymxc3" — this approach reads back to a separate `cat` process. Many newcomers will be confused why their `echo` "didn't return anything." Better to use `at_client.py` from Ch 102 consistently.
- §103.4 chat script: `'' AT` then `OK ATZ` — the `''` expect-empty then send `AT` is correct, but newcomers often write `OK AT` thinking it expects OK first. Add a one-line "first chat line is unusual: expect nothing, send AT to wake the modem."
- "n_gsm framing errors silent" pitfall is good; add that the kernel exposes line-discipline counters in `/proc/tty/driver/ttymxc` for debugging.

### Knowledge prerequisites missing
- HDLC byte stuffing / FCS-16 isn't explained. Either explain or cite RFC 1662.
- `ldattach` is mentioned but not introduced; cross-link to its man page or explain.

### Other
- Lab item 9 mentions baud "115200 (~80 kbps), 921600 (~600 kbps)" — these match expectation, good. But step 6 (CMUX) requires the modem to support `AT+CMUX=0`; not all do. Add a "if your modem doesn't support CMUX" note.
- The PPP material in §103.4 is excellent and worth being the canonical "how PPP comes up on Linux" reference; consider promoting some of it to a Part VI networking chapter.

## Ch104 — NB-IoT / Cat-M1
### Readability
- `> Why:` energy budget "5 J → 1 J" is great anchor. Quote real numbers (Joules/uplink) more in §104.5 to make the case land.
- §104.3 "9600 baud default!" deserves a sidebar — newcomers will set 115200 and see garbage.

### MCU-engineer friendliness
- The PSM/eDRX discussion lands well for an MCU reader who's used STM32 STOP/STANDBY modes. Explicitly call out: "PSM is the modem's equivalent of STM32 STANDBY: deep sleep with state preserved."
- The "wake-controller MCU + modem" pattern in §104.5 is classic embedded — call out that you don't need the i.MX6ULL at all for a 10-year sensor; if i.MX6ULL is overkill, an STM32L0 is cheaper. This is honest and reinforces the trade-off.

### Missing examples / figures
- No oscilloscope trace of the PSM enter/exit transition. A real-world current-vs-time plot for the BC95 going from active → PSM → wake → TX is the "show, don't tell" the chapter needs.
- A timeline showing T3324 and T3412 firing relative to the modem state would help. Currently the two timers are explained as bullets but the temporal relationship isn't visualized.

### Insufficient depth
- §104.5 "10-year sensor" walks the math but doesn't show the actual firmware. Add at least a state-machine pseudocode: sleep → wake → read BME280 → AT+CFUN=1 → wait CEREG=1 → AT+NSOST → AT+CFUN=0 → sleep.
- The new kernel `drivers/net/wwan/` subsystem is only mentioned in passing — given this is the modern path for QMI/MBIM, a one-page walk of the WWAN device model would close a gap left from Ch 102.

### Technical errors
- "Active Timer (T3324)" — per 3GPP TS 24.008, T3324 granularity is 2 s base unit (encoded 8-bit), not "4 s = `00000010`". Verify the bit encoding: `00000010` in the T3324 byte = unit "deactivated" or "2 s × 2 = 4 s"? The encoding is `[3 bits unit][5 bits value]`. `00000010` = unit 000 (2 s) × value 2 = 4 s — correct. State the encoding explicitly.
- Similarly for T3412: `00000110` is asserted as "24 hours" — verify: `[3 bits unit][5 bits value]`. `00000110` = unit 000 (10 min) × value 6 = 60 min. To get 24 h, unit 010 (1 hour, encoded `010`) × value 24 = `0_1011000`. The example value in the chapter computes to 60 min, not 24 h. Recompute.
- "NB-IoT can transmit at up to +23 dBm (200 mW)" — correct.
- "MCL 164 dB" is the Cat-NB1 max; Cat-NB2 is 164 dB also; verify and cite the 3GPP source.
- "Per cycle 152,000 µAs = 42 µAh" — `µAs / 3600 = µAh`, so `152000 / 3600 = 42.2 µAh`. Correct.
- "Per year 413 mAh" → "Battery life at 19 Ah usable: ~46 years" — `19000 / 413 = 46 years`, correct. But the "limited by self-discharge & temperature" caveat earlier is critical; consider stating "shelf life-bound" up front.

### Knowledge prerequisites missing
- T3324/T3412 are introduced as 3GPP timer names without saying these come from EMM (EPS Mobility Management). One sentence on EMM context would help readers grep the spec.
- Reader needs to understand "registered but idle" vs "RRC Connected" states. A one-paragraph 3GPP state model (EMM-DEREGISTERED → EMM-REGISTERED + ECM-IDLE → ECM-CONNECTED) would massively clarify why PSM works.

### Other
- §104.7 "PSM not granted by carrier" is the most realistic pitfall; consider promoting it to the chapter's introduction so readers don't design products based on an unverifiable assumption.
- Lab item 5 "Measure full uplink cycle energy" — note you need a low-side current monitor (INA226 or similar); a multimeter won't capture the µs-scale TX peaks.

## Ch105 — RFID / NFC
### Readability
- `> Focus:` paragraph is excellent ("inductive coupling"). Strong start.
- §105.6 from-scratch code is fine, but the comment "(full ~400 lines)" with a 150-line listing is confusing — clarify what's in the omitted 250 lines (Crypto1 + block read, presumably).

### MCU-engineer friendliness
- MCU readers may have used MFRC522 with Arduino. State this explicitly: "If you've used the Adafruit `MFRC522.h` library, this chapter is the Linux equivalent with the framework stripped."
- The "the chip's silicon does the framing" point is huge for MCU readers used to bit-banging — reinforce.

### Missing examples / figures
- A figure showing the LC tank circuit + matching network + tag inductive coupling would explain "antenna detuning" pitfalls visually.
- No diagram of the ISO 14443 anticollision tree (the bit-by-bit binary search for tag UIDs). For readers wanting to understand multi-tag environments, this is essential.

### Insufficient depth
- "Crypto1 implementation" is left as an exercise. For depth, walk the LFSR-feedback structure of Crypto1, or at minimum point at the Crapto1 / mfoc reference implementation file:line.
- Walk of the in-kernel `pn533` driver is shallow (8 lines of pseudocode). For driver-internals promise, walk the full RX path: USB URB → `pn533_recv_response()` → `nfc_targets_found()` → netlink event. Trace through real source.

### Technical errors
- "Mifare Classic Crypto1 ... reverse-engineered in 2008" — true (Nohl & Plötz, CCC 2007/2008). Crapto1 paper.
- "MFRC522 v2.0 = VersionReg 0x92" — datasheet says VersionReg returns 0x91 (v1.0) or 0x92 (v2.0). The lab step 1 says "0x91 or 0x92" — consistent, good.
- "Mifare Ultralight" — chapter calls it Type A, no Crypto1. NTAG21x (NTAG213/215/216) are Mifare Ultralight C derivatives with optional 3DES. Distinguish UL vs NTAG.
- "DESFire ATQA is 0x4403 + SAK 0x20" — accurate for DESFire EV1+; verify EV2 SAK behavior.
- "MFRC522 modules ... 1 cm range" — typical actual range for cheap modules is 2–3 cm; "1 cm" is the worst case. Soften.

### Knowledge prerequisites missing
- ISO 14443 Type A vs Type B isn't differentiated in body; only "Type A: short frame, 7 bits" appears. Mention Type B (different modulation) briefly even if not implemented.
- "ASK modulation" introduced without expansion (Amplitude Shift Keying). Define on first use.

### Other
- §105.7 "DESFire: MFRC522 supports framing but not the AES" — actually MFRC522 has no AES at all; host must implement. Worth saying "use OpenSSL/mbedtls AES for DESFire on the host side."
- The `compatible = "rohm,dh2228fv"` pattern reappears (see cross-cutting).

## Ch106 — Fingerprint sensors
### Readability
- `> Why:` is good. The "fingerprint = dominant biometric" framing is right.
- §106.3 framing protocol — the byte breakdown is good but the example `EF 01 FF FF FF FF 01 00 03 01 00 05` reads as a single line; consider laying it out vertically with annotations.

### MCU-engineer friendliness
- MCU readers will have done UART command-response protocols (e.g., AT modems, Modbus); explicitly map "this is structurally the same as Modbus RTU: address + function + length + data + CRC."
- The biometric template *state* on the module is unfamiliar — call out the closest MCU analog: "templates in module flash are like persistent EEPROM slots on STM32; once written, they survive power loss."

### Missing examples / figures
- A figure showing the enrollment 3-step dance (capture 1, lift, capture 2, combine, store) would help. Currently text-only.
- A timing chart: "place finger" → IRQ asserts → GetImg returns → GenChar runs in 200 ms → Store takes 50 ms. Concrete latencies help product design.

### Insufficient depth
- The chapter doesn't touch on the kernel side (input subsystem, evdev) — but for typical embedded uses (UART command-response with the module doing matching) that's actually fine. State explicitly: "there is no kernel driver here; the module is purely a UART peer."
- `libfprint` is mentioned in one paragraph (§106.8). For depth, walk one libfprint driver (e.g., `drivers/synaptics/synaptics.c`) to show how USB scanners differ.
- No discussion of presentation-attack detection (liveness). For real-world security this matters; state outright "these modules have no liveness detection — a gummy-bear print can fool them."

### Technical errors
- "Score is 0..2000 (higher = better match); chip's threshold is typically 50" — for R503/Grow modules the typical score range is 0..2400 with default match threshold around 50; some firmware uses 0..400 ranges. State this is module-firmware-specific.
- "Default key for new cards is `FFFFFFFFFFFF`" — this is in Ch105 not 106; should not appear here. (Verified: it's not — false alarm.)
- "FAR < 0.001%" and "FRR < 1%" are vendor-spec — caveat that real-world numbers depend on enrollment quality.
- §106.6 `recv_pkt` reads exactly 9-byte header then `len` payload. But `len` includes the 2-byte checksum (per spec: "length = payload + checksum"). The code reads `len` bytes total into payload, then claims `len - 2` is the payload size. Correct, but the comment "Verify checksum (skipped for brevity)" should at least note that production code MUST verify it.
- "Slot overwrite on re-enroll" is correct; this pitfall is well-placed.

### Knowledge prerequisites missing
- PAM is introduced without explaining its module model; one paragraph on PAM stack (auth → account → session) would help readers who've never written one.
- "Address `0xFFFFFFFF` broadcast" — explain that this is the default but module address can be changed via SetAddress command; once changed, broadcasts won't work.

### Other
- Lab item 1 references `AT+VFY-PWD` — this isn't an AT command, R503 uses its own framing. Either show the framed VfyPwd packet (command 0x13) or remove the AT pretense.
- §106.7 PAM module example missing the `Makefile` / build steps; learners need to know it's compiled with `pam_dev` headers.

## Ch107 — GPS / GNSS + PPS
### Readability
- `> Focus:` paragraph distinguishes NMEA latency vs PPS edge precision excellently — best of any chapter so far.
- "stratum-1 NTP server" framing in `> Why:` is concrete and exciting; carry the same energy into the lab section.

### MCU-engineer friendliness
- MCU readers may have hooked a GPS module to STM32 PA10 RX and parsed `$GPRMC` manually. State explicitly: "if you've done this on MCU, you parsed NMEA in software; on Linux, `gpsd` parses for you and exposes JSON, and the kernel timestamps PPS edges with nanosecond precision (which an STM32 needs an input-capture timer to do)."
- The `chrony refclock` model deserves an MCU analog: "PPS to chrony is like a sync pulse to your SPI master — it tells the disciplinator 'this is the exact moment'."

### Missing examples / figures
- A figure showing the PPS edge vs NMEA sentence arrival timeline (PPS rises at T=0; NMEA arrives at T=50-200ms after) would visualize the latency story.
- No oscilloscope/logic-analyzer capture of the PPS pin + NMEA UART line during a one-second interval. Even ASCII art would help.

### Insufficient depth
- §107.4 PPS kernel side is one paragraph. For internals depth, walk `drivers/pps/pps.c::pps_event()` and how the IRQ handler timestamps the edge. Show the `ts_real` vs `ts_raw` distinction.
- The UBX parser in §107.7 is a great start but doesn't show how to *configure* the receiver — only how to parse. Add a `ubx_send_cfg()` function with the CFG-MSG / CFG-PRT / CFG-NAV5 sequence.

### Technical errors
- "PPS jitter: ~30 ns" for NEO-6M — datasheet states ~50 ns RMS; "20 ns" for NEO-9M is achievable but typically with TCXO; cite the datasheet figure type (RMS vs peak-to-peak).
- "u-blox NEO-9M ... concurrent dual-band L1/L5" — NEO-M9N is *single-band L1 only*; ZED-F9P is dual-band L1+L5. Verify which chip is meant. NEO-9 family vs ZED-9 family is a critical distinction for RTK.
- "u-blox NEO-9M ... 184 channels" — NEO-M9N has up to 184 receive channels but that's the GNSS engine, not "tracking" channels in the historical sense. Wording is fine but worth qualifying.
- "$GPRMC,123519.00,A,4807.038,N,01131.000,E,022.4,084.4,230394,003.1,W*6A" — this is the textbook NMEA example (taken from many references); fine but cite it as the canonical example.
- "8-bit PID byte" structure in §109 (LIN); here in §107: "$GPGGA fix quality" — fix quality is a single digit 0..8; mention what each value means.
- The chrony refclock example uses `noselect` on GPS — correct since GPS via SHM is just a label provider. Add a one-liner "noselect means 'don't use as time source, just use for the seconds label'."

### Knowledge prerequisites missing
- IRIG-B / PTP / NTP layering isn't introduced; for a reader new to time sync, "stratum" needs a sentence.
- Cold-start vs warm-start vs hot-start TTFF distinction isn't defined.

### Other
- Lab item 10 cross-references "TPS6594 + GPS for outage survival" — TPS6594 is the PMIC chapter (Ch 116); good cross-link, but verify the TPS6594 lab actually covers UPS-style operation.
- §107.10 references "Ch 51B" for PPS-wake — verify chapter exists.

## Ch108 — RS-485 + Modbus RTU
### Readability
- `> Focus:` paragraph is dense but accurate; consider breaking into two: "RS-485 physical layer" then "Modbus timing requirements."
- "ground reference (a multi-meter check across grounds is mandatory)" is great practical advice — call this out as a numbered checklist item.

### MCU-engineer friendliness
- MCU readers have used Modbus extensively on STM32; the chapter currently treats Modbus as new. Lead with: "you've done Modbus master from STM32 + libmodbus or hand-rolled code. The Linux path uses the same protocol with `libmodbus` (same author!) — the only new thing is kernel RS-485 mode."
- The "kernel toggles DE/RE via TIOCSRS485" pattern is the load-bearing Linux insight — make it the highlight.

### Missing examples / figures
- A timing diagram of DE/RE toggle vs UART TX would clarify "sub-bit-time precision" claim. Show: TX byte starts → DE asserts → bytes shift out → DE deasserts after last stop bit.
- Frame-on-the-wire ASCII capture: `[01][03][00][00][00][08][CRC_LO][CRC_HI] ... gap ... [01][03][10]...response`.

### Insufficient depth
- The chapter is short on driver internals. Walk `drivers/tty/serial/imx.c::imx_uart_rs485_config()` to show how the i.MX UART manages DE via RTS automatically.
- §108.5 inter-character timeout: explain `select()` timeout heuristic in libmodbus more concretely. The current "works fine at ≤38400" is too vague — what about 115200?
- No mention of `Documentation/driver-api/serial/serial-rs485.rst` in the kernel tree as the canonical reference.

### Technical errors
- "MAX485 ... Max speed 2.5 Mbps" — the basic MAX485 is 2.5 Mbit; MAX485E and MAX485EU vary. Worth caveating.
- "ADM2483 ... Max speed 0.5 Mbps" — actually ADM2483 supports up to 500 kbps; ADM2587 supports 16 Mbps with isolation. Confirm which model.
- "9600 default" for Modbus — many devices default to 19200 8E1; the spec defines both but most field devices default to 19200. Confirm and add nuance.
- "Bias resistors 680 Ω" — actual recommended is typically 560–680 Ω depending on supply voltage. For 5 V supplies, 680 Ω gives ~3 mA bias current and ~200 mV differential. For 24 V isolated buses, higher values. Add the formula.
- "Inter-character < 1.5 char-times; Inter-frame ≥ 3.5 char-times" — at >19200 baud, the Modbus spec switches to fixed 750 µs and 1750 µs respectively (since 3.5 char times become impractical). Mention this exception.

### Knowledge prerequisites missing
- Common-mode voltage / differential signaling intro is brief; readers unfamiliar with EIA-485 may want a more thorough physics primer (or cross-ref RS-485 chapter elsewhere).
- The Modbus "register addressing 0-based vs 1-based" trap is mentioned in pitfalls but deserves earlier prominent treatment.

### Other
- Lab item 6 "Bias test" — clarify what happens without bias: "expect to see slaves randomly assert ERROR responses or stop answering" so readers know what to look for.
- §108.7 inverter register map is "typical, vendor-specific" — readers may try this against any inverter and fail. Recommend they obtain the inverter's Modbus map document.

## Ch109 — LIN bus
### Readability
- `> Focus:` paragraph captures LIN's essence well. The break-signal explanation in particular is clear.
- "Linux's lack of native support means you write the framing yourself, which is a great UART exercise" — good framing; but a more positive tone would be "Linux's lack of native support makes LIN the perfect UART internals exercise."

### MCU-engineer friendliness
- MCU readers may have done LIN on STM32 via the dedicated LIN UART (USART_CR2_LINEN). State: "STM32's USART has hardware LIN mode that generates break + sync automatically; on Linux you must orchestrate this manually because the kernel UART driver doesn't expose LINEN equivalents."
- The reverse-engineering-junkyard-HVAC story in §109.8 is exactly the kind of project that hooks MCU readers. Lead with it.

### Missing examples / figures
- Oscilloscope capture of a LIN frame (break + sync + PID + data + checksum) with annotations is essential and missing. ASCII representation would suffice.
- LIN scheduler table diagram: e.g., "100 ms: poll ID 0x10; 200 ms: poll ID 0x11; ..." showing the master's polling schedule.

### Insufficient depth
- §109.6 LIN slave implementation is incomplete; the break-detection problem is acknowledged but no working code. Either provide a tested solution (TIOCGICOUNT polling loop with sample handling) or remove the slave section.
- The chapter promises "build a master and slave responder in C." Slave is left as half-done.
- Walking the i.MX `drivers/tty/serial/imx.c::imx_uart_handle_irq()` to see how break detection is reported via PARENB+framing errors would close the loop and fulfill driver-internals.

### Technical errors
- PID parity formula: P0 = ID0 ⊕ ID1 ⊕ ID2 ⊕ ID4 — correct per LIN 2.x.
- P1 = !(ID1 ⊕ ID3 ⊕ ID4 ⊕ ID5) — correct.
- Verified PID(0x10) = 0x50: bits = 010000; P0 = 0⊕0⊕0⊕1 = 1; P1 = !(0⊕0⊕1⊕0) = !1 = 0; PID = 01_010000 = 0x50. Matches §109.9 step 2. Good.
- "Wake pulse must be ≥250 µs" — LIN 2.x spec says ≥250 µs but ≤5 ms; the wake-pulse upper bound is also important.
- "tcsendbreak(uart_fd, 0); 250 ms in POSIX" — Linux man page says POSIX-undefined but Linux behavior is "min break length" when argument is 0 (about 250–500 ms in some drivers, ~13 bit-times in others). State that scope-verifying is mandatory.
- "Break field ≥13 dominant bits = ~1.4 ms low at 9600 LIN-baud" — 13 × (1/9600) = 1.354 ms; "1.4 ms" is a safe rounding. Correct.

### Knowledge prerequisites missing
- LIN sleep-mode + EN-pin behavior is introduced in §109.7 but the reader hasn't seen automotive sleep current budgeting; one sentence on car KL30 vs KL15 wake signals would help.
- Reverse engineering a real LIN slave requires knowing the slave's published `.ldf` (LIN Description File) format — mention it.

### Other
- §109.8 junkyard VW HVAC example is great. Add a safety note: "use a bench supply, NOT the car's 12 V, when reverse-engineering — bad commands can blow fuses or trigger airbag DTCs in the car's ECM."

## Ch110 — CAN deep dive
### Readability
- `> Focus:` paragraph balances depth + accessibility very well. Best `> Focus:` in the cookbook.
- "CAN-FD adds a second bit rate during the data phase" — could be clarified with a one-line drawing showing arbitration phase at 500 kbps + data phase at 2 Mbps.

### MCU-engineer friendliness
- MCU readers know CAN deeply from STM32 bxCAN/FDCAN. Lead with: "everything you know about CAN on STM32 applies; SocketCAN is just `bxCAN_Receive()` → skbs → PF_CAN sockets." This is a transition the reader will love.
- BCM is the standout Linux feature MCU readers don't have — call this out as "the kernel does periodic broadcast for you, freeing user-space from real-time scheduling."

### Missing examples / figures
- Bit-timing diagram in §110.3 needs more visual clarity. Show TQ count = 16, with each segment colored differently and the sample point marked.
- SocketCAN data-flow diagram: hardware → CAN controller IRQ → flexcan driver → can-raw socket OR can-bcm OR can-isotp → user app. Currently spread across the chapter.
- ISO-TP frame-type diagram (SF / FF / CF / FC) is missing despite being central to §110.6.

### Insufficient depth
- §110.4–§110.5 list the kernel modules but don't walk any. For depth, walk `net/can/raw.c::raw_rcv()` and how the kernel demultiplexes received frames to sockets via the `dev_add_pack(&can_packet_type)` mechanism.
- BCM section is a working example but doesn't walk the kernel side. `net/can/bcm.c::bcm_tx_setup()` is the key function.
- ISO-TP section is correct but doesn't explain *why* a kernel module is needed (rather than user-space libisotp). Touch on the kernel timer + STmin enforcement that makes a kernel impl more reliable.

### Technical errors
- "33 MHz CAN clock" — i.MX6ULL FlexCAN clock source is typically PLL3 USB-derived (e.g., 60 MHz) or peripheral clock; not 33 MHz. The example calculation is good but the input clock should be from i.MX6ULL's actual clock tree (likely 30/60 MHz).
- "CAN-FD ... CRC15" — classic CAN has CRC-15; CAN-FD has CRC-17 (≤16 byte) and CRC-21 (>16 byte). Chapter is correct on FD but uses "CRC15" only as classic's.
- "33 MHz / 500 kbps = 66 TQ per bit" — math correct (66 = 33e6/500e3). But i.MX6ULL FlexCAN typically uses 30 MHz, giving 60 TQ — a more realistic example.
- "ISO 11898-1:2015 (CAN-FD)" — ISO 11898-1:2015 is the data-link spec; CAN-FD requires also -2:2016 for physical. Both editions.
- "candump can0  123   [8]  DE AD BE EF 00 01 02 03" — the `[8]` is the DLC; correct format.
- Bus-off pitfall mentions `restart-ms 100` — kernel correctly supports this. Worth mentioning `restart-ms 0` (no auto-restart, manual `ip link set can0 down` then `up` required).
- "MCP2515 ... up to 10 MHz SPI" — datasheet specifies up to 10 MHz; some clones top out earlier. Add caveat.

### Knowledge prerequisites missing
- "CSMA/CR" introduced as an aside; for readers new to network MAC protocols this needs one sentence on how it differs from CSMA/CD (Ethernet) and CSMA/CA (WiFi).
- The UDS application layer is referenced in §110.6 (mode/PID 0x22 0xF1 0x90) but not explained. Either provide a short UDS primer or forward-ref ISO 14229.

### Other
- Lab item 7 (capstone OBD-II) is gold. Add a safety note: "engine running, not driving; some PIDs are only valid when engine is on; double-check the OBD-II adapter wiring before plugging into the car."
- Lab item 10 (bus-off recovery via shorting) — add big warning: "ESD-safe environment; transceiver may survive but not all do; risk of damage to non-isolated SoC."
- The chapter is excellent; consider promoting some material (BCM, ISO-TP) to a dedicated "advanced CAN" chapter if length becomes an issue.

## Ch111 — Quadrature encoders & rotary
### Readability
- The QDEC truth-table at §111.2 is excellent. The "INVALID (missed an edge)" row is great — readers must understand this failure mode.
- "1.4 ms" vs "13 bits" is mixed terminology between Ch109 and Ch111; here keep it consistent within the chapter.

### MCU-engineer friendliness
- MCU readers have used STM32 TIM_EncoderMode (TIM1/2/3/4/5 support quadrature in hardware with zero IRQs). State this loudly: "STM32 has a TIM peripheral that does this in silicon at MHz rates with zero CPU. i.MX6ULL has the ENC peripheral but mainline Linux doesn't always expose it; this is why you'll often resort to GPIO IRQ software decode (slower) or an external chip."
- This is a great chance to talk about the trade-off "Linux gives you a powerful CPU but loses tight peripheral integration."

### Missing examples / figures
- Oscilloscope/timing capture of A and B signals during forward + backward rotation would be invaluable. ASCII fine but a real capture better.
- No diagram for the LS7366R wiring or the i.MX XBAR routing to the ENC peripheral.

### Insufficient depth
- "i.MX hardware quadrature ... Status in mainline" is honest but should commit to a concrete recommendation: at kernel v6.x specifically, what's supported? Without that the reader has to test themselves.
- The `rotary_encoder` kernel driver walk is shallow. The driver source is small and readable; walk its IRQ handler.

### Technical errors
- "QDEC_TABLE[16]" — indexing is `(prev_ab << 2) | curr_ab` which gives 0..15. Table values look correct for 4× decode. Confirm by tracing prev=00 curr=01 → index 1 → +1. Good.
- "i.MX6ULL ENC peripheral up to ~10 MHz edge rate" — the reference manual specifies maximum input frequency; verify against the RM. The IMX6ULL has ENC1/2/3 peripherals (multiple instances).
- "LPD3806-100BM-G5-24C-100ppr, $20" — LPD3806 is a real Chinese optical encoder; verify part number suffix.
- "LS7366R ... up to 40 MHz pulse rate" — datasheet specifies 40 MHz max quadrature input clock. Good.
- "ENC peripheral ... documented in NXP reference manual ch. 33-ish" — vague. Look up the actual chapter (the IMX6ULLRM has ENC at chapter 32 or so depending on revision).

### Knowledge prerequisites missing
- "Gray code" mentioned in DT binding (`encoding = "gray"`); not explained. One sentence: "Gray code = each step flips exactly one bit, which is what quadrature happens to produce."
- Index pulse / homing concept assumes the reader knows what "homing" is from CNC; new readers don't. One sentence.

### Other
- The chapter would benefit from forward-referencing Ch 112's closed-loop velocity example (§111.8) since it depends on the motor driver — currently it's standalone.
- Lab item 7 cross-references PID tuning; consider giving a brief Ziegler-Nichols recipe or pointing to a tuning chapter.

## Ch112 — Stepper & DC motor drivers
### Readability
- `> Focus:` paragraph is strong; covers steppers, DC, BLDC, FOC in 4 sentences.
- "FOC ... most engineers offload to a dedicated MCU because Linux's jitter exceeds the 10 kHz current-loop budget" — this is the key insight; emphasize it as the chapter's takeaway.

### MCU-engineer friendliness
- MCU readers will have used L298, BTS7960, DRV8825 from STM32. Lead with: "everything you've done on STM32 + step/dir works the same here; the only new thing is that the i.MX6ULL is faster CPU-wise but jitterier IRQ-wise."
- The "Klipper architecture: Linux planner + MCU stepper" model is exactly the right pattern for ex-MCU engineers — they instantly grasp the split.

### Missing examples / figures
- Stepper microstepping waveform diagram (full step vs 1/8 vs 1/256 current sine waves) would clarify the "smoother but lower torque" trade-off.
- H-bridge state diagram (forward, reverse, brake, coast) — there's the text drawing but a 4-state diagram would be cleaner.
- BLDC commutation table is good but a sketch of the 6 vector states (clock face with arrows) would help readers understand "rotating field."

### Insufficient depth
- TMC2209 UART CRC is referenced but not shown. For a from-scratch chapter, provide the full CRC-8 routine: `crc = (crc ^ byte) << 1` style.
- DRV8302 BLDC section is text-only. No code, no DT, no kernel walk. Either provide the gate-driver init code or scope it to "for BLDC use SimpleFOC on an external MCU."
- No discussion of the kernel `drivers/i2c/busses/i2c-rk808.c` style framework for motor control — current loop typically isn't kernel-level on Linux, but it would close the loop to acknowledge there's no in-tree FOC framework.

### Technical errors
- "Vref = Imax × 5 × 0.1 V" — DRV8825 formula is `Iref = Vref / (5 × Rsense)`. With Rsense = 0.1 Ω: `Vref = 5 × 0.1 × Iref = 0.5 × Iref`. For 0.8 A: `Vref = 0.4 V`. Matches the chapter. Good but the formula is written as `Vref = Imax × 5 × 0.1` which simplifies to `0.5 × Imax`; clarify.
- "NEMA17 stalled: 12 V / 3 Ω = 4 A" — NEMA17 typical winding resistance is 1.5–3 Ω; 4 A from 12 V is plausible. Good.
- "BLDC at 10,000 RPM with 14 magnetic poles cycles 14 × 10,000 / 60 = 2,333 commutations/s" — should be "14/2 = 7 pole-pairs × 6 commutations/electrical-rev × 10000/60 mechanical-RPS = 7000 commutations/s." Recompute. The point about Linux jitter is still valid but the number is wrong.
- "stepper microstepping ... lower torque per microstep" — actually, microstepping doesn't reduce holding torque (within ±5%); it reduces *step* torque granularity. Common misconception; clarify.
- TMC2209 has a built-in CRC (CRC-8/ATM); chapter shows pseudocode but not the polynomial. Add `polynomial 0x07` for completeness.

### Knowledge prerequisites missing
- PWM / duty-cycle / frequency intro is assumed from Ch 48; if Ch 48 hasn't covered, this might leave readers behind.
- PID intro assumed; for readers new to control loops, a one-paragraph "P controls now-error, I integrates past, D anticipates" would help.
- "Field-Oriented Control" is name-dropped; one sentence on Park/Clarke transforms or forward-ref a control textbook.

### Other
- Lab item 10 "Safety stop" is great and should be promoted to the start of the lab section — emergency stops are a topic readers should always think of first.
- §112.6 BLDC code references `apply_gates(pattern, pwm_duty)` — never defined. Either provide implementation or annotate as pseudo-code.

## Ch113 — WS2812 / SK6812 / APA102
### Readability
- `> Focus:` covers the SPI-4× trick perfectly. Best in the cookbook so far.
- The §113.3 LUT explanation (`0x88, 0x8E, 0xE8, 0xEE`) walks the encoding well.

### MCU-engineer friendliness
- MCU readers have written WS2812 drivers using DMA on STM32 (HAL_TIM_PWM_Start_DMA with a precomputed waveform). State explicitly: "this is the exact same trick you'd use on STM32 — encode 4 SPI bits per WS2812 bit, push via DMA. The encoding is identical."
- The "Klipper-style offload" pattern from Ch 112 could be invoked: "if you have 5000+ LEDs and 60 fps, you'd run an STM32 dedicated WS2812 driver and Linux as the animation source."

### Missing examples / figures
- ASCII timing diagram showing one WS2812 "0" and "1" bit (with annotated 0.4 µs / 0.85 µs vs 0.8 µs / 0.45 µs) would visualize the spec.
- A diagram showing the SPI bytes `0x88` and `0xEE` overlaid with the resulting WS2812 waveform would *make* the trick.

### Insufficient depth
- The chapter doesn't walk the kernel SPI DMA infrastructure (`spi_message_add_tail`, `dma_async`). For internals, add a short walk of `drivers/spi/spi-imx.c::spi_imx_setup_dma()` to explain *why* DMA works for big transfers.
- No mention of `drivers/leds/leds-ws2812-spi.c` (if it exists in any out-of-tree fork) or the LED class subsystem (`drivers/leds/`). Worth a one-liner acknowledging the LED framework.

### Technical errors
- WS2812 timing: T0H = 0.4 µs ±150 ns, T0L = 0.85 µs; T1H = 0.8 µs, T1L = 0.45 µs. The chapter's numbers are correct.
- "SPI `1000`" for "0" bit at 3.2 MHz → 312.5 ns high + 937.5 ns low. T0H spec is 0.4 µs ±150 ns (range 0.25–0.55); 312.5 ns is within range. Good.
- "SPI `1110`" → 937.5 ns high + 312.5 ns low. T1H spec is 0.8 µs ±150 ns (range 0.65–0.95); 937.5 ns is at the upper end but within. Good.
- "first WS2812 byte = G then R then B" — correct.
- "APA102 ... 5-bit global brightness 0..31" — correct; the start byte is `0b111_xxxxx` where the upper 3 bits are the marker.
- "Encode each WS2812 byte (8 bits) into 4 SPI bytes" — actually each WS2812 byte (8 bits) × 4 = 32 SPI bits = 4 SPI bytes. Chapter says this; the lookup table uses 2 WS2812 bits → 1 SPI byte (= 8 SPI bits = 2 WS2812 bits × 4). So 8 WS2812 bits = 4 SPI bytes via 4 LUT lookups. Correct.
- "1000-LED strip × 4× = 12 KB DMA buffer" — actually `1000 × 3 × 4 = 12000 bytes`. Correct.
- "SK6812 RGBW is GRBW" — verify; some SK6812 datasheets specify GRB+W order, others RGBW.

### Knowledge prerequisites missing
- "Gamma 2.2" — explain why eye perception is logarithmic.
- "HSV color space" — many MCU readers haven't thought beyond RGB; one paragraph on hue/saturation/value would help.

### Other
- Lab item 4 (power injection) is critical for any reader building a strip > 1 m. Add a wiring diagram explicitly.
- §113.7 gamma table generator Python expression is correct: `int((i/255.0)**2.2 * 255 + 0.5)` — but reader expects this to be C. Provide a static C array.

## Ch114 — Beepers, relays, SSRs
### Readability
- `> Why:` "shipped this for 5 years and it never fails" is exactly the right tone. Hold that.
- "AC safety — non-negotiable rules" §114.5 is excellent and should perhaps be a sidebar elsewhere (this material should never be skipped).

### MCU-engineer friendliness
- MCU readers have driven relays from STM32 with BJT + diode dozens of times. State: "this is mechanically identical to MCU practice; the only Linux-specific aspect is that the GPIO sysfs/gpiod is your interface instead of HAL_GPIO_WritePin."
- For the SSR section, contrast with the MCU reader's experience of "TRIAC + opto-isolator from STM32" — same circuit, different name.

### Missing examples / figures
- Relay back-EMF spike scope shot (with and without flyback diode) is mentioned in lab but the figure isn't shown in body. Add an ASCII representation of the voltage waveform.
- Zero-cross vs random-fire SSR timing diagram for inductive loads is missing despite being a critical pitfall.

### Insufficient depth
- This chapter is the most "thin" in the cookbook depth sense — it's almost entirely circuit guidance, no kernel walks, no driver internals. For Part VII depth requirement, add at least a short walk of `drivers/leds/leds-gpio.c` or `drivers/pwm/pwm-imx27.c` to show how GPIO/PWM frameworks bind to these actuators.
- No mention of the kernel `gpio-leds` for buzzer driving as LED-style trigger (`echo timer > /sys/class/leds/buzzer/trigger`). Add this — it's a clean abstraction.

### Technical errors
- "Songle SRD-05VDC-SL-C ... coil draws 30 mA at 5 V" — actually datasheet says ~70 mA at 5 V (coil resistance ~70 Ω); 30 mA is way off. Recheck — this matters for BJT base-resistor sizing.
- "2N2222 BJT ... 30 mA at 12 V" — BC547/2N3904/2N2222 typically rated for 200 mA collector current, but driving a 12 V coil through 2N2222 with 0.6 V Vbe + ~3 V Vsat means ~9 V across the coil. If coil resistance is 80 Ω → 110 mA — beyond 2N2222 spec edge. Use a Darlington (BC549) or MOSFET for relays.
- "GPIO direct-driving a relay coil. Coil draws 30 mA at 5 V" — see above; 30 mA is likely wrong.
- "VIH = 0.7 × VDD = 3.5 V" (Ch 113 reference) — accurate.
- "passive piezo ... drive at 2 kHz at 50% duty" — correct, though most piezos resonate at 3–4 kHz; mention the resonance lookup.
- "active buzzer ... most tolerate direct 3.3/5 V GPIO drive at <30 mA" — many Chinese active buzzers pull 50+ mA peak; check the datasheet. Recommend always using a transistor for safety.
- "Fotek SSR-40DA rated 40 A — actually good for 25 A with heatsink" — true; Fotek SSRs are notorious for over-rating. Good pitfall.

### Knowledge prerequisites missing
- Triac / SCR conduction modes not explained for SSRs.
- "Snubber" mentioned in SSR schematic but not explained. One paragraph on inductive-load snubbers (R+C across the triac for inductive loads).
- "Earth bonding" / GFCI / RCD are mentioned; for readers in regions without these, briefly explain.

### Other
- The chapter's safety emphasis is excellent. Consider adding a "Required reading before mains AC work" sidebar pointing to a real electrical safety course.
- Lab item 5 "SSR + AC load" — add an explicit "DO THIS LAB WITH A QUALIFIED ELECTRICIAN if you're not certified" warning.
- The chapter is short (~10 pages); this is fine — the topic doesn't need more — but add a closing forward-reference to Ch 116 (PMIC) for "controlling power rails as well as loads."

## Ch115 — Dual FEC + hosted Ethernet
### Readability
- `> Focus:` paragraph is accurate but dense. Splitting into "dual MAC" vs "SPI Ethernet" sub-paragraphs would improve scanability.
- Pitfall about "Bridge + ip address on members" is worth highlighting earlier (in §115.4).

### MCU-engineer friendliness
- MCU readers might have never used dual-NIC systems. Lead with: "if you've used STM32 + W5500 for a single Ethernet port, this chapter shows how Linux handles 2+ ports trivially via the netdev model — something STM32 + LwIP can't easily do."
- The W5500 "hardware TCP/IP" vs Linux netdev distinction will be familiar — many MCU folks have used W5500 for offload. Make the contrast explicit.

### Missing examples / figures
- A diagram of the two FECs sharing one MDIO bus (with separate PHY addresses 0 and 1) is essential — currently text-only.
- Router/bridge/isolated topology diagrams for §115.3-115.5 would clarify the use cases visually.
- A flow diagram showing NAPI poll (IRQ → schedule NAPI → poll budget → napi_complete) would help readers understand the receive path in §115.8.

### Insufficient depth
- §115.8 FEC driver walk is decent (~2 functions). Could go deeper on BD ring management — explain how the descriptor ring wraps and why it's allocated in DMA-coherent memory.
- PTP support is mentioned in §115.1 but not walked in §115.8 or anywhere. Cross-link to a "Linux PTP" chapter or add a short section.
- §115.6 W5500 paragraph could include the actual SPI command structure (W5500 has command/data registers) so readers see why it's "hardware TCP/IP" not netdev.

### Technical errors
- "i.MX6ULL ... 2× FEC each 10/100 Mbps" — correct.
- "Each FEC needs ... 50 MHz clock to RMII" — correct; the SoC's ENET_REF clock can source or be sourced.
- "Per-PHY address straps" — verify the KSZ8081 has a strap for `PHYAD[0]` etc.
- "DM9051 SPI at 20 MHz: ~8 Mbps" — realistic; DM9051 has 16-bit SPI burst mode that improves on this.
- "ENC28J60 SPI at 20 MHz: ~3 Mbps" — realistic; the chip's own MAC is bottleneck.
- "WIZnet W5500 ... mainline does not have W5500 driver" — there are out-of-tree W5500 drivers (w5100/w5300 are in `drivers/net/ethernet/wiznet/`). Verify if W5500 is in there too. The wiznet directory does have w5100-spi.c which supports W5100, W5200, W5300; W5500 support is in some out-of-tree forks but reaching mainline.
- Actually, mainline has `drivers/net/ethernet/wiznet/w5100-spi.c` (covers W5100); W5500 has been submitted but check version. Update wording if needed.
- "AAhB:CC" placeholder MAC — fine.

### Knowledge prerequisites missing
- RMII vs MII vs RGMII vs SGMII distinction isn't discussed; assumed familiarity. A one-paragraph summary would help readers picking PHYs.
- "NAPI" is referenced; one sentence on "NAPI = adaptive interrupt mitigation; combines IRQ + polling" would help.

### Other
- §115.7 mentions DM9051 throughput but doesn't mention KSZ8851 which is generally faster. Worth including in the comparison.
- Lab item 9 (PTP) is excellent and underexplored elsewhere — verify if there's a follow-up chapter on PTP.

## Ch116 — PMICs and regulator framework
### Readability
- `> Focus:` paragraph is excellent — the boot-sequence races warning is exactly the kind of thing MCU readers don't know they need.
- "Voltage encoding: per-buck typically `Vout = 0.6 + N × 0.025 V`" — show the actual conversion table or formula derivation for one buck.

### MCU-engineer friendliness
- MCU readers have used discrete LDOs many times. The "5–10 chips → 1 PMIC" transition is the right framing.
- The DVFS coordination is *unique to Linux* (MCU readers don't do this); call it out as "Linux's killer power-management feature."
- Mention that the regulator framework's "consumers declare in DT" pattern is the Linux equivalent of "STM32 LL_BUS_GRP1_EnableClock(...) for each peripheral."

### Missing examples / figures
- A power tree diagram (PSU → PMIC → BUCK1/BUCK2/.../LDO1/... → SoC rails → consumer drivers) is essential and missing.
- A timing diagram of DVFS transition (clock decision → regulator ramp → frequency change) would clarify §116.5 — the ordering is critical.
- A sequence diagram of suspend-to-RAM showing which rails go off and when.

### Insufficient depth
- The regulator framework walk in §116.3 is sysfs-level. For depth, walk `drivers/regulator/core.c::regulator_enable()` to show how the framework computes the dependency graph and enforces ordering.
- §116.4 power-up sequencing is described as "the PMIC enforces this" — but how does the kernel handle a rail that was *not* enabled by the PMIC at boot but needs enabling later? Touch on `of_get_regulator()` and `regulator_dev_register()`.
- The PMIC driver walk is missing. `drivers/regulator/pca9450-regulator.c` is small and readable; walk `pca9450_probe()` and `pca9450_set_voltage_sel()`.

### Technical errors
- "BUCK1: 1.0–1.65 V @ 3.5 A" — verify against PCA9450 datasheet; BUCK1's range is 0.6–2.187 V with up to 3.5 A.
- "BUCK5: 1.1 V / 1.35 V" — PCA9450 BUCK5 is the DDR rail; 1.1 V (DDR4) / 1.35 V (DDR3). Correct.
- "Power saving from 1.275 V to 1.150 V: static ~10%, dynamic ~28% at same f" — math: `(1.150/1.275)^2 = 0.81`, so dynamic decrease ~19%, not 28%. Re-derive: `1 - (1.150/1.275)^2 = 1 - 0.814 = 0.186`. Closer to 19%. Verify or rephrase.
- "i.MX6ULL has required power-up sequence" — correct that there is a sequence; specifics need to match i.MX6ULLRM ch. 11.
- "PCA9450 ... over-specified for i.MX6ULL but illustrative" — fair to use as illustration since i.MX6ULL more often pairs with PF3000 or BD71850; PCA9450 is technically i.MX8M.
- `regulator_summary` output indentation — verify it matches actual kernel output.
- "ramp-delay = <3125>" microvolts/microsecond — PCA9450 default ramp is around 6.25 mV/µs; verify the unit (kernel doc says µV/µs).

### Knowledge prerequisites missing
- "DDR3 needs ≤1 ms from VREF to VDDQ stable" — JEDEC spec; mention for readers unfamiliar with DDR timing.
- "VDD_SNVS always on" — what SNVS is hasn't been introduced; cross-ref Ch 8 or wherever it's defined.
- OPP table introduction is brief; one sentence on "OPP = Operating Performance Point: a kHz+voltage tuple."

### Other
- Lab item 8 "Add a custom OPP under-spec" is brave — but also risky. Add a strong warning about potential silicon damage from under-voltage operation.
- Lab item 9 "From-scratch I²C peek" — make explicit that this requires the regulator framework to NOT have already claimed the rail (else two writers).
- The chapter is excellent overall and ties together Ch 51B (DVFS) and Ch 75 (current measurement) — make these cross-references prominent.

## Ch117 — External RTC
### Readability
- `> What:` and `> Why:` paragraphs are well-structured. The "$0.50 chip + $0.30 coin cell" framing is effective.
- §117.7 "three clock domains coexist" is well-explained but the table format would be even clearer.

### MCU-engineer friendliness
- MCU readers have used DS3231 from STM32 endless times. State explicitly: "the chip and registers are identical to what you've done from MCU; the only new thing is Linux's rtc subsystem and `hwclock`."
- The `RTC_WKALM_SET` ioctl pattern is unique to Linux; explain "this is how userspace tells the kernel to enable a wake-on-alarm without touching the I²C bus directly."

### Missing examples / figures
- Timeline diagram of suspend → RTC alarm fires → wake → resume would clarify §117.5 wake-from-suspend flow.
- A diagram showing the three clock domains (RTC ↔ system clock ↔ NTP/PPS) with arrows for "sync direction" would help §117.7.

### Insufficient depth
- §117.6 driver walk is decent for `get_time` but doesn't walk `rtc_register_device()` or the IRQ chain registration. For depth, show how `rtc-ds1307.c` registers with the `rtc_class_ops` framework.
- Wakeup-source handling is non-trivial. Cross-link or explain how `device_init_wakeup()` interacts with `enable_irq_wake()` to make the GPIO IRQ a wake source.
- No mention of `nvmem` (some RTCs expose backed-up SRAM as nvmem-cells); MCP79410's 128B SRAM could be exposed this way.

### Technical errors
- "DS3231 ... ±2 ppm (1 min/year)" — 2 ppm × 365 days × 86400 s = 63 s/year ≈ 1 min/year. Correct.
- "PCF8563 ... ±20 ppm (10 min/year)" — 20 ppm × 365 × 86400 = 630 s = 10.5 min. Correct.
- "DS3231 has two alarms; PCF8563 has one" — DS3231 has Alarm1 + Alarm2 (correct); PCF8563 has one (verify against datasheet — PCF8563 has 1 alarm).
- "MPU-6050 IMU also defaults to 0x68. Bus conflict." — Correct. AD0 strap on MPU-6050 changes to 0x69.
- "Year-2100 problem" — DS3231 stores year as 00–99 + century bit; in 2100 the century bit flips. Some drivers handle it, some don't. Worth a one-liner about kernel `rtc-ds1307.c` century handling.
- "rtcwake -m mem -s 30" — correct invocation.
- BCD vs binary conversion code is correct.

### Knowledge prerequisites missing
- "BCD" needs one-sentence intro on first use (0x23 = decimal 23, not 35).
- "OSF (Oscillator Stop Flag)" — explain its meaning: latched when the oscillator stopped, indicating possible time corruption.
- Suspend-to-RAM concept not introduced; cross-ref Ch 51B.

### Other
- Lab item 3 (battery hot-swap) is great practical knowledge.
- §117.4 timezone discussion — recommend explicitly that for embedded products in cross-timezone use, UTC + chrony is the only sane choice; "local time in /etc/adjtime" is a deprecated quirk.
- §117.5 `alarm.time.tm_min += 5; if (...) tm_min -= 60, tm_hour++` — naïve. Doesn't handle hour overflow into next day, month, year. Better: use `mktime()` and `localtime_r()`. Worth a footnote since readers may copy-paste.
- The chapter is a strong closing for Part VII; the "wake every hour, suspend in between" pattern ties together Ch 51B + Ch 116 + Ch 117 nicely.
