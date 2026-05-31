# Part VIIc — Style/ESL Review (Ch 98–117, Group M–O cookbook)

## Cross-cutting patterns

- **Em-dash chaining of three clauses.** Still the book's signature tic. Every chapter's `What:` blurb does it (Ch98 LoRa: "long-range modulation (chirp spread spectrum) reaching multiple kilometres at sub-100 kbps — Four real radios compared — and bring up a real LoRaWAN gateway"). Within sections, especially in "Why" and "Focus" headers, three em-dashes per paragraph is the norm. Replace most with periods.
- **Semicolon-glued clauses.** Heaviest in Pitfalls bullets across all 20 chapters ("X happens; Y is the fix"). Convert to two sentences.
- **"Not X — but Y" / "X. Y." sledgehammer.** Especially in Focus blurbs: "The radio is easy. The link budget is the engineering." (Ch98), "The radio is easy. The RF path is where projects die." (Ch98), "Pick the cell. The bands pick you back." pattern recurs in Ch102, 103, 104. Use once per chapter at most.
- **Buzzwords this part overuses:** `crucial`, `critical`, `canonical`, `dominant`, `dominant pattern`, `dominates`, `the killer feature`, `killer detail`, `the whole engineering job`, `the engineering`, `brutal trade`, `cargo-cult`, `mechanical`, `genuinely possible`, `dance` (used twice for "register dance"), `landscape`, `realm`. Drop or vary.
- **Marketing-flavoured praise.** "the workhorse for…" (Ch98), "the killer feature" (Ch99 ×2, Ch100 ×1), "the dominant cheap radio" (Ch99 title), "the only short-message radio that…" (Ch98), "genuinely possible" (Ch98 §98.8), "the Linux skill is" (Ch100). Trim.
- **"That's it." / "That's the whole pattern." / "Done."** Used as a stand-alone sentence at least once per chapter (Ch98 §98.3 "That's it. Eighty registers…"; Ch99 §99.5 "Two boards, same binary…"; Ch100 §100.5 "Done."; Ch103 "Done."; Ch107 "Done.", etc.). Pick one or two per part.
- **Triplet rhythm.** "Read status, ack, snapshot, defer, return." style lists used to signal expertise. When repeated within a chapter it reads AI-generated.
- **Royal "we'll/let's"** is largely absent in Part VII (good), but "we" still appears as authorial voice in Ch98 §98.6 ("We build the smallest possible…") and Ch101 §101.4. Imperative ("Build…") reads cleaner.
- **Numeric drive-by claims without anchor.** "80 % of the budget" (Ch98), "80 % of the RF risk" (Ch98), "80 % of 'ZigBee unreliable' reports" (Ch100), "80 % of the engineering" (Ch101), "90 % of the bugs" (Ch103). The same "80 %" appears 5+ times across this part. Vary or drop.
- **"the X is the engineering" / "X is the whole job".** "The radio is easy. The link budget is the engineering." (Ch98), "the protocol on top … is the other 20 %" (Ch101), "the calibration is 80 % of the engineering" (Ch101). Authorial tic.

---

## Ch98 — LoRa

### AI wording / sledgehammer / buzzwords
- > "long-range modulation (chirp spread spectrum) reaching multiple kilometres at sub-100 kbps. Four real radios compared: … then bring up a real LoRaWAN gateway with **ChirpStack**."
  - One sentence, three colons, three em-dashes worth of structure. Break into three plain sentences in the `What:` blurb.
- > "Most engineers cargo-cult the 'Arduino LoRa library' without understanding the modulation, the registers, or why a bad antenna kills 80 % of the budget. This chapter strips the magic."
  - "Cargo-cult" is jargon; "strips the magic" is marketing. Rewrite: "Many engineers copy the 'Arduino LoRa library' without understanding the modulation, the registers, or why a bad antenna costs most of your link budget. This chapter walks the whole stack."
- > "The radio is easy. The link budget is the engineering."
  - Slogan. Keep at most once in the Focus blurb; do not repeat the same shape ("The radio is easy. The RF path is where projects die.") in §98.4.
- > "The trade is brutal: LoRa buys range with bitrate."
  - "Brutal trade" is fan-prose. Rewrite: "The trade is direct: LoRa buys range with bitrate."
- > "every commercial UWB anchor system uses it." / "every other chapter says 'the kernel driver does this.'"
  - Absolute "every" claims; soften ("most commercial anchor systems", "almost every other chapter").
- > "A private LoRaWAN network running on one i.MX6ULL is genuinely possible."
  - "Genuinely possible" is marketing hedging. Rewrite: "A private LoRaWAN network on one i.MX6ULL is realistic."
- > "Mandatory rules — every one of these has bricked a board somewhere"
  - Em-dash glue + "bricked somewhere" idiom. Rewrite: "Mandatory rules. Every one of these has destroyed a board in the field."
- > "*Especially* during bring-up when you're tempted to 'just see if it works.'"
  - Italics + quoted slang. Rewrite: "This matters most during bring-up, when it is tempting to power the radio without an antenna just to see if it responds."
- > "The chip is alive after `Sleep`."
  - Pitfall headline reads cute. Rewrite: "`Sleep` does not erase state on SX127x — but on SX1262 Cold Start it does."

### ESL readability
- > "Understanding the **spreading factor / bandwidth / coding rate / preamble** four-tuple — and what each costs in air-time, sensitivity, and power — is the whole engineering job."
  - 30 words, em-dash mid-clause. Rewrite: "The four-tuple of spreading factor, bandwidth, coding rate, and preamble is the whole engineering job. You must know what each one costs in air-time, sensitivity, and power."
- > "Sensitivity improves ~2.5 dB per SF step: SF7 ≈ –123 dBm, SF12 ≈ –137 dBm — that's **14 dB** range, or ~5× the distance."
  - Multi-clause with em-dash. Rewrite: "Sensitivity improves about 2.5 dB per SF step. SF7 is around −123 dBm; SF12 is around −137 dBm. That is 14 dB of headroom, or roughly 5× the range."
- > "Most engineers cargo-cult the 'Arduino LoRa library' without understanding the modulation, the registers, or why a bad antenna kills 80 % of the budget."
  - 28 words, idiom + triplet. See rewrite above.
- > "This is unusual in this book — every other chapter says 'the kernel driver does this.' Here the kernel is the bus controller and nothing more."
  - "Here the kernel is the bus controller and nothing more" — try "On LoRa, the kernel is only the SPI bus controller."

### Needs more depth
- §98.2 "Bitrate ≈ `SF × BW / 2^SF × CR`". The formula is given but **CR is undefined in the formula** (in CR = 4/5, do you mean the literal fraction 4/5, or just the numerator?). Spell it out: "CR here is the literal ratio (4/5 = 0.8, 4/8 = 0.5)." Otherwise the reader gets a number an order of magnitude off.
- §98.2 The CSS diagram is decorative; it does not show that the *start frequency* of each chirp encodes the symbol value. Add one line: "All chirps sweep the same `BW` Hz. The *starting* frequency of each chirp encodes `SF` bits — that is what gives you the data."
- §98.5 "Mainline has refused most LoRa kernel patches" — the reader does not know *why*. One sentence: "Mainline maintainers want a stable subsystem (like ieee802154 or nl80211); the LoRa community never converged on a common MAC, so each driver looks different and none have been accepted."
- §98.6 The `Frf = freq × 2^19 / 32e6` formula appears without derivation. One sentence: "The PLL divides the 32 MHz XTAL by `2^19 / Frf`; rearrange and `Frf = freq × 2^19 / 32e6` is the value you load."
- §98.6 RSSI math is asymmetric (HF subtracts 157, LF subtracts 164) is stated but **why** is left implicit. One sentence: "SX1276 routes HF (>525 MHz) and LF (<525 MHz) through different gain stages with different reference points, so the offset differs by 7 dB."
- §98.8 LoRaWAN classes A/B/C are *named* but not explained. One paragraph: "Class A devices open a 2-second RX window after each uplink only — lowest power. Class B adds beacon-aligned periodic RX windows. Class C keeps RX on continuously — only mains-powered devices."
- §98.10 Pitfall "Duty cycle violations": the math "1 % of 2 packets/min" feels arbitrary. Show the path: "EU 868 g1 = 1 % duty cycle = 36 s of transmit per hour. SF12 at 51 bytes = 2.3 s/packet → 36 / 2.3 = ~15 packets per hour, or two per ~minute."

---

## Ch99 — Sub-GHz proprietary (nRF24L01, CC1101, CC1200)

### AI wording / sledgehammer / buzzwords
- > "**these chips are state machines you drive with SPI commands**; the radio behavior is determined by which state you're in, not by individual register values"
  - Sledgehammer + semicolon. Rewrite: "These chips are state machines driven by SPI commands. The behavior depends on the current state, not on individual register values."
- > "Master the state diagram and the radios are trivial."
  - "Trivial" reads dismissive. Rewrite: "Learn the state diagram and the rest is straightforward."
- > "The killer feature" (used twice — for auto-ACK and for ACK piggyback).
  - Pick one. The auto-ACK one stays; rename the piggyback one to "Bidirectional in one transaction" or similar.
- > "This is why nRF24 dominates the BOM-conscious low-rate radio market."
  - Marketing phrasing. Rewrite: "This is why nRF24 is the default choice when BOM cost matters and rates stay below 1 Mbps."
- > "The single most common reason 'the modules I bought don't work.'"
  - Quoted-slang construction. Rewrite: "This is the most common reason a newly bought module appears dead."
- > "Two boards, same binary, one with `r` arg and one without — instant 1 Mbps ACKed point-to-point link."
  - "Instant" + em-dash glue. Rewrite: "Two boards, same binary — one with the `r` argument, one without — and you have a 1 Mbps ACKed point-to-point link."
- > "CC1101 is harder to use than nRF24L01 because TI gives you the modulator/demodulator + framing primitives but **no auto-ACK**. You build the MAC."
  - "You build the MAC" period-fragment for punch. Fine once. But §99.6 also closes with "the same template fits." Vary.
- > "TI ships **SmartRF Studio** which generates the register dump for any desired modulation / data rate / deviation — you'll absolutely use it."
  - "You'll absolutely use it" is informal. Rewrite: "TI's **SmartRF Studio** generates the register dump for any modulation, data rate, and deviation. Almost everyone uses it for CC1101 bring-up."
- > "The most useful CC1101 starting point is …"
  - "Most useful starting point" is consultant-flavour. Rewrite: "A good CC1101 starting point is …"

### ESL readability
- > "The state-transition rules that bite every newcomer:"
  - "Bite every newcomer" is idiom. Rewrite: "These transition rules catch every newcomer:"
- > "the chip parses it. Easier to use, but very different 'feel' from SX1276 code."
  - "Very different 'feel'" is informal/idiomatic. Rewrite: "Easier to use, but the code looks different from SX1276's."
- > "the in-tree wireless dir does not contain this — verify with current kernel"
  - Parenthetical to the reader mid-sentence. Move to a separate note or footnote.
- > "Switching between TX and RX requires going through Standby-I (`CE=0`, wait 130 µs, set `PRIM_RX`, `CE=1`)."
  - The parenthetical hides the procedure. Promote: "To switch between TX and RX you must pass through Standby-I. Set `CE=0`, wait 130 µs, set `PRIM_RX`, then set `CE=1`."

### Needs more depth
- §99.2 "Enhanced ShockBurst" — `ARD` and `ARC` are introduced inline ("auto-retry delay, auto-retry count") but their *units* are not given. ARD is in 250 µs steps (`SETUP_RETR[7:4]`), ARC is 0..15. The lab code uses `0x3F = ARD=3 (1000 µs), ARC=15` but the reader cannot decode that without the units. Add a sentence with the bit field layout.
- §99.2 The six-pipe diagram shows that pipes 2–5 share the upper 4 bytes with pipe 1. The *why* (per-pipe RX_ADDR is only 1 byte after P1) is missing. One sentence: "Per-pipe RX address registers P2..P5 are only one byte each; the high four bytes are inherited from P1's address. So all five satellites must share that prefix."
- §99.2 STATUS register comes back "for free" on every SPI command — make explicit *why* this is useful. One sentence: "Because the chip clocks STATUS out on the MISO line during the command byte, you read it without any extra SPI transaction. Use this for tight TX-done polling."
- §99.6 CC1101 state machine — 13 states are mentioned but the diagram only shows ~5. Either add the others (CALIBRATE, SETTLING, RX_OVERFLOW, TX_UNDERFLOW, FSTXON, plus IDLE/SLEEP/RX/TX) or downscope the claim to "the five states you use day-to-day".
- §99.6 "registers are write-once and survive across IDLE → RX/TX transitions" — *write-once* is misleading; they are writable any time, just not erased by mode changes. Rewrite: "Once configured, registers persist across IDLE ↔ RX/TX transitions. Strobing `SRX` or `STX` does not reset them. You can rewrite them at any time."
- §99.10 Pitfall "CE pulse too short" gives the spec (≥10 µs) but not what happens if you violate it. One sentence: "If CE is shorter than 10 µs, the chip never advances from Standby-I to TX, the FIFO is not emitted, and `TX_DS` never fires. The driver looks frozen."

---

## Ch100 — ZigBee / Thread / 802.15.4

### AI wording / sledgehammer / buzzwords
- > "the **IEEE 802.15.4** family — the certified mesh networking stack used by Philips Hue, Aqara, Eve, IKEA Trådfri, Google Nest."
  - Bullet-list-as-prose with brand-name parade. Rewrite: "The IEEE 802.15.4 family powers most retail smart-home meshes: Philips Hue, Aqara, Eve, IKEA Trådfri, Google Nest."
- > "Nodes you don't write — you buy them. The Linux skill is **gateway integration**"
  - Three em-dashes worth of telegraphing. Rewrite: "You do not write the nodes; you buy them. The Linux skill is gateway integration."
- > "**the radio firmware is a black box; you talk to it over a serial protocol (EZSP, Thread Spinel, ZNP) that mirrors the network layer**"
  - Sledgehammer + semicolon. Rewrite: "The radio firmware is a black box. You talk to it over a serial protocol (EZSP, Thread Spinel, ZNP) that mirrors the network layer."
- > "the cause of *every* 'my ZigBee network is flaky' thread"
  - "Every" is absolute; "thread" is slang for forum post. Rewrite: "the most common cause of 'my ZigBee network is flaky' reports"
- > "the user's home WiFi is on a different channel than the customer's"
  - Two contradictory roles ("user" vs "customer"). Pick one term.
- > "Devices are categorized by ZCL **clusters**."
  - Fine; keep.
- > "This is the Thread killer feature: every node is a normal IPv6 endpoint."
  - "Killer feature" again. Rewrite: "This is what makes Thread different from ZigBee: every node is a normal IPv6 endpoint."
- > "You'd rarely send raw — the adapter does it — but `btmon`-style debugging (zigbee2mqtt has `debug:true`) shows you the frame stream so you can trace 'why is my pairing failing.'"
  - 37 words, two em-dashes, quoted slang. Break: "You rarely send raw frames; the adapter does it for you. But `btmon`-style debugging (set `debug:true` in zigbee2mqtt) prints the frame stream. This is how you trace a failed pairing."
- > "Modern path."
  - Two-word section opener that reads AI. Rewrite: "This is the modern path."

### ESL readability
- > "Linux's CPU schedule, plus SPI/USB latency, makes a hosted Linux implementation hard."
  - "Linux's CPU schedule" is awkward; "hosted Linux implementation" is jargon. Rewrite: "Between Linux's scheduling jitter and SPI/USB latency, running the MAC on the host CPU is not reliable."
- > "the radio chip runs **its own firmware** containing the PHY + MAC + (optionally) the higher layers."
  - Parenthetical mid-clause. Rewrite: "The radio chip runs its own firmware. The firmware contains the PHY and MAC, and may also contain the higher network layers."
- > "Once running, `wpan0` shows up"
  - "Shows up" idiom. Fine, but follow with concrete output (it does — keep).
- > "A poorly chosen channel gives a network with 30 % packet loss that 'mysteriously works fine at home' (because the user's home WiFi is on a different channel than the customer's)."
  - 30-word run-on, parenthetical mid-sentence. Rewrite: "A poorly chosen channel can give 30 % packet loss in the field. The same network 'works fine at home' because the home WiFi happens to sit on a different channel."

### Needs more depth
- §100.2 The RCP vs NCP vs ZNP table is the heart of the chapter but the *boundary moves* are not described in plain language. Add one paragraph: "Moving the boundary higher (NCP, ZNP) means less work on Linux but a per-stack firmware blob; moving it lower (RCP) means Linux runs the full stack (heavy CPU/RAM) but lets you change MAC behaviour without re-flashing the radio."
- §100.5 ZNP framing protocol "TYPE+SUBSYSTEM selects whose API" — `whose API` is ungrammatical; should be "which subsystem's API." Also the `[TYPE=0x4 MSB | SUBSYSTEM]` byte is described but the four TYPE values (POLL/SREQ/AREQ/SRSP) are not named. Add them so the reader can decode a btmon log.
- §100.5 FCS is "XOR of LEN through last data byte" — confirm: ZNP MT FCS is actually an XOR over LEN+CMD0+CMD1+data. Either confirm or correct.
- §100.6 Spinel header bits "encode flow-control state, transaction IDs, priority" — too vague. Add the actual layout: "Bits 7..6 = flag (always 0b10), bits 5..4 = interface ID, bits 3..0 = TID. Look in `spec/spinel-protocol-src/spinel-frame.md` for the full layout."
- §100.6 The relationship between `wpan0` (Linux netdev), the Thread mesh, and the upstream `eth0` is the trickiest concept for a new reader. Add a short topology paragraph: "otbr-agent runs as a Linux daemon. It owns the radio over a serial line, runs the Thread network stack in user space, and exposes the mesh as a Linux netdev (`wpan0`). It also acts as an IPv6 router between `wpan0` and `eth0`, advertising routes both ways."
- §100.7 nRF52840 802.15.4 hardware accelerator deserves a sentence on *why this matters for Linux*: "Because the hard timing (ACK within 192 µs) is in silicon, the host CPU only needs to handle higher-layer events — milliseconds, not microseconds. That is why RCP-mode Linux Thread works at all."
- §100.11 Pitfall "Network key rotation" — the consequence is given ("un-joins everything") but not the *correct* way to migrate. One sentence: "If you must rotate, use Thread's *commissioner-driven* key update (sends the new key encrypted under the old one); a manual config-file change strands every device."

---

## Ch101 — UWB ranging

### AI wording / sledgehammer / buzzwords
- > "**UWB ranging is a time-of-flight measurement, and ToF accuracy depends on how cleanly the radio captures the first arriving signal**."
  - The whole Focus paragraph is one 75-word block. Break: "UWB ranging is a time-of-flight measurement. ToF accuracy depends on how cleanly the radio captures the first arriving signal. Multipath corrupts the measurement if the demodulator latches the wrong peak. The DW3000 has hardware leading-edge detection and per-antenna delay calibration."
- > "getting the calibration right is 80 % of the engineering. The protocol on top — single-sided two-way ranging vs double-sided TWR vs TDoA — is the other 20 %."
  - "80 % / 20 %" rhetorical split appears elsewhere in this part too. Rewrite: "Calibration is most of the engineering. The protocol on top — SS-TWR, DS-TWR, TDoA — is the smaller piece."
- > "If you're building anything that *positions* objects indoors at sub-metre accuracy, this is the radio."
  - "This is the radio" marketing close. Rewrite: "For sub-metre indoor positioning, UWB is the only practical choice."
- > "the dominant path is **user-space + spidev**."
  - "Dominant path" again (also Ch98, Ch99, Ch101). Rewrite: "Most projects use `spidev` + a user-space driver."
- > "the +10 cm is uncalibrated antenna delay" / "Always calibrate at a known distance first."
  - Fine; useful concrete advice.

### ESL readability
- > "Each pulse is a marker the receiver can timestamp with sub-nanosecond precision. Because radio waves travel ~30 cm/ns, **1 ns of timing error = 30 cm of range error**."
  - Fine; keep.
- > "Error: any clock drift between initiator and responder during Treply scales into the ToF estimate. For ±20 ppm crystals + 200 µs Treply, drift error is ~4 ns ≈ 1.2 m. Bad."
  - Sentence-final "Bad." reads slangy. Rewrite: "For ±20 ppm crystals and 200 µs Treply, the drift is about 4 ns, or 1.2 m of range error. That is unusable."
- > "The trick: scheduling TX at a *future* exact DWT time (the chip has its own 40-bit timestamp counter at 64 GHz / 16 µs wraparound)."
  - "64 GHz / 16 µs wraparound" is wrong: a 40-bit counter at 64 GHz wraps in ~17 s, not 16 µs (the 16 µs is the *low 24 bits* used for delayed-TX scheduling). Fix or clarify the relationship.
- > "Even this skeleton reveals the protocol: ToF = (response-time at initiator − reply-time at responder) / 2."
  - "Reveals the protocol" reads grand. Rewrite: "Even this skeleton shows the protocol: ToF = (response-time at initiator − reply-time at responder) / 2."

### Needs more depth
- §101.1 The DS-TWR formula `ToF = (Tround1×Tround2 - Treply1×Treply2) / (Tround1+Tround2+Treply1+Treply2)` is given without derivation. The reader who has not seen the symmetric DS-TWR paper does not know *why* this cancels drift. Two sentences: "DS-TWR cancels first-order clock drift because each side measures one full round-trip and the asymmetric-Treply formula divides them. The numerator's product/difference structure makes the drift cancel out — see McElroy 2014 for the algebra."
- §101.2 The TX/RX timestamp registers are 40-bit (`5 bytes`). The chapter mentions "5-byte timestamp arithmetic with the DWT 40-bit rollover" only in the closing paragraph of §101.5. Move this fact to §101.2 where it belongs: "Timestamps are 40 bits at 64 GHz × 128 / 499.2 ≈ 15.65 ps per tick. They wrap every 17.2 s. Use uint64 arithmetic and a wrap-aware subtract."
- §101.4 `dwt_setdelayedtrxtime(resp_tx_ts >> 8)` discards the low 8 bits — the reader will ask why. One sentence: "The delayed-TX register has 32 bits (the low 8 bits of the 40-bit timestamp are zero on the wire). Shift right by 8 to load it."
- §101.5 The `poll_msg` byte array `{ 0x41, 0x88, 0, 0xCA, 0xDE, 'R','X','I','N',0xE0 }` is opaque. Decode the IEEE 802.15.4 MHR fields: FCF=0x8841 (data frame, short addr, PAN-ID compress), seq=0, dest PAN=0xDECA, dest short=…, function code 0xE0. Otherwise the reader cannot adapt the code.
- §101.7 Antenna-delay calibration is mentioned but never quantified. Add the typical magnitude (the DWM3000 default is around 16450 ticks ≈ 258 ns; you tune ±200 ticks at a known 1.000 m).
- §101.10 Pitfall "Treply too short" gives `<200 µs` as the failure threshold but does not say what the chip does (does it silently drop the TX? abort with a status flag?). Add: "If Treply is shorter than the responder's scheduled TX time, the DW3000 sets `TXPUTE` (TX power-up time error) in SYS_STATUS and never transmits. Always check this bit on the responder."

---

## Ch102 — USB 4G LTE modems

### AI wording / sledgehammer / buzzwords
- > "the **USB-attached cellular modem** — by far the dominant cellular path on Linux."
  - "By far the dominant" is marketing. Rewrite: "The USB-attached cellular modem is the most common cellular path on Linux."
- > "the trick is the four-layer onion of *which interface mode the modem is in* … *which kernel driver matches it* … *which user-space tool brings up data*."
  - "Onion" metaphor + triplet + italics. Rewrite: "There are three layers to keep straight: the USB interface mode the modem advertises, the kernel driver that binds to it, and the user-space tool that activates the data session."
- > "This chapter strips the mystery: you'll know what every `lsusb` line means…"
  - "Strips the mystery" is marketing. Rewrite: "After this chapter you can read an `lsusb` line, name the driver that bound each endpoint, and trace the data path."
- > "**the modem is a tiny Linux box inside a USB shell**, exposing multiple interfaces simultaneously"
  - "Tiny Linux box inside a USB shell" — cute but vague. Rewrite: "The modem is a small embedded system in a USB case. It exposes several USB interfaces at once."
- > "The split is unusual on Linux but maps cleanly once you draw the picture."
  - "Maps cleanly" is consultant. Rewrite: "The split is unusual on Linux. The diagram in §102.3 makes it concrete."
- > "**This is the single biggest source of 'my modem is in the wrong mode' confusion**"
  - Quoted-slang + bold. Rewrite: "This is the most common reason a modem appears in the wrong mode."
- > "The 'understand it forever' approach: do everything ModemManager would do, by hand."
  - "Understand it forever" reads slangy. Rewrite: "If you want to understand the path, do everything ModemManager would do by hand."
- > "Quectel ships a reference connection manager (`quectel-CM`) that wraps the above. ~3000 lines of C. It's open source; reading it is a tour of the QMI protocol."
  - "Tour" is informal. Rewrite: "Quectel ships a reference connection manager, `quectel-CM`, that wraps the above (~3000 lines of C, open source). Read it as a worked example of the QMI protocol."

### ESL readability
- > "the trick is the four-layer onion of *which interface mode the modem is in* (RNDIS vs ECM vs MBIM vs QMI vs PPP), *which kernel driver matches it*, and *which user-space tool brings up data*."
  - 40-word, three-italic clauses, five-way parenthetical. See rewrite above.
- > "When you buy a new modem and it appears as nothing, **the missing PID in `option_ids[]` is usually why**."
  - "Appears as nothing" and "is usually why" are awkward English. Rewrite: "When you plug in a new modem and no `/dev/ttyUSB*` appears, the most common cause is a missing PID in `option_ids[]`."
- > "Wait for ModemManager to detect the modem"
  - Fine; keep.
- > "`dnsmasq` integration handles DNS."
  - Fine; keep.
- > "Result: random modem resets mid-call."
  - "Mid-call" is OK but consider "mid-transmission" for ESL clarity (call/voice has a different meaning here).
- > "If you `qmicli --start-network` while ModemManager is running, it'll fight you."
  - "Fight you" idiom. Rewrite: "If you call `qmicli --start-network` while ModemManager is running, the two will race each other and the connection will drop."

### Needs more depth
- §102.2 The PID table is excellent but the *reason* QCFG values map non-monotonically (0=PPP, 1=ECM, 2=MBIM, 3=RNDIS, 5=QMI on Quectel) is confusing for the reader who tries to memorise it. Add: "QCFG values are vendor-defined and not consistent across vendors. Always check the AT manual for your specific module before issuing `AT+QCFG=\"usbnet\",N`."
- §102.3 QMI vs MBIM — the chapter says "preferred for new designs" but never explains *why* (MBIM is the open USB-IF standard; QMI is Qualcomm-proprietary). Add one sentence so the reader can defend the choice.
- §102.3 `qmi_wwan_probe()` skeleton ends at "wwan0 appears, but no IP until QMI session opens." The QMI session-open dance is the chapter's central concept but lives only as bullet steps in the prose. Add the actual QMI message sequence: "Open WDS service → set IP family → start network → get runtime settings → configure netdev. The five steps are the same whether `qmicli`, `quectel-CM`, or ModemManager does it."
- §102.5 The bring-up checklist is great. Add the AT response that means each step failed — `AT+CPIN?` may return `SIM PIN`, `SIM PUK`, `READY`, `NOT INSERTED`. The reader should know what each one demands ("PUK is unlocked only with the carrier's PUK code; three wrong PIN attempts is the usual cause").
- §102.5 PPP path closes with "max ~1–2 Mbps due to byte-stuffing overhead." The mechanism is left implicit. One sentence: "PPP uses HDLC byte-stuffing; bytes 0x7E (frame), 0x7D (escape), and any control byte (0x00–0x1F) are escaped, costing ~10–15 % overhead. Combined with the UART speed limit, this caps PPP at 1–2 Mbps regardless of the cellular link."
- §102.10 Pitfall "CGEV events drop the connection unnoticed" — the example `IPv6 routing advertisement` is vague. Concrete: "Carriers periodically send PDP DEACT or PDP MODIFY in CGEV URCs. Without `AT+CGEREP=2,1` you never see them. Subscribe at boot and reconnect on a DEACT event."

---

## Ch103 — UART AT-command modems

### AI wording / sledgehammer / buzzwords
- > "**PPP is a circa-1989 link protocol with HDLC framing, LCP negotiation, IPCP for IPv4 address, and pap/chap auth — and it still works on every modem ever made**."
  - 35-word sentence, four jargon terms, sledgehammer close. Break: "PPP is a 1989-vintage link protocol. It uses HDLC framing, LCP for link negotiation, IPCP for IPv4 address assignment, and PAP/CHAP for authentication. It still works on every modem ever made."
- > "Master `pppd` + chat + an init.d script and you have a robust auto-reconnecting cellular link"
  - "Master X and you have Y" preachy. Rewrite: "With `pppd`, a chat script, and an init.d (or systemd) supervisor, you have a robust auto-reconnecting cellular link."
- > "good UART discipline."
  - "UART discipline" is jargon. Rewrite: "careful UART setup (flow control, baud, framing)."
- > "**Hardware flow control (RTS/CTS) is non-negotiable** above 9600 baud."
  - "Non-negotiable" is corporate. Rewrite: "Above 9600 baud, hardware flow control is mandatory."
- > "Skip it = packets corrupted = PPP LCP timeouts = 'modem doesn't work.'"
  - Equation-as-prose tic appears again. Rewrite: "Without it, the UART drops bytes, PPP LCP times out, and the modem looks broken."
- > "The clever part: `pppd` does protocol negotiation entirely in user space … but data path is fully kernel-side via the line discipline. Result: low CPU even on a Cortex-A7."
  - "Clever part" + "Result:" rhetorical pair. Rewrite: "Note the split: `pppd` does protocol negotiation entirely in user space (LCP, IPCP packets pass through the `/dev/ppp` ioctl), but the data path runs kernel-side via the line discipline. CPU stays low even on a Cortex-A7."
- > "Crude but works for low-frequency queries."
  - Fine, but "crude" is judgmental. Rewrite: "Simple but works for low-frequency queries."

### ESL readability
- > "PWRKEY pulse low for ≥1 s (≥2 s on Air724) to power on. Some boards tie PWRKEY low through a resistor for auto-on; the cleaner pattern is GPIO control so the host can reset the modem."
  - Two thoughts in one bullet. Rewrite: "Pulse PWRKEY low for at least 1 s to power on. The Air724 needs 2 s. Some boards tie PWRKEY low through a resistor for automatic power-on; GPIO control is cleaner because it lets the host reset the modem."
- > "These **URCs (Unsolicited Result Codes)** are the modem reporting boot progress. Don't talk to it before 'SMS Ready' or you'll get spurious ERROR responses."
  - "Don't talk to it" idiom. Rewrite: "These URCs (Unsolicited Result Codes) report boot progress. Do not send AT commands before 'SMS Ready' — they will return spurious ERRORs."
- > "Add `/etc/init.d/celld` or a systemd unit and the cellular link comes up at boot, recovers from any modem hang via PWRKEY power-cycle, and signals status via an LED. ~30 lines of shell that replace 200 lines of C in many vendor SDKs."
  - 35 words, triplet, closing brag. Rewrite: "Install as `/etc/init.d/celld` or a systemd unit. The link comes up at boot, recovers from any modem hang by power-cycling PWRKEY, and shows status on an LED. About 30 lines of shell, replacing several hundred lines of vendor C."

### Needs more depth
- §103.4 The chat script's quoting and pacing rules are obscure. Add one sentence about pacing: "Each chat line is `EXPECT SEND`. An empty `''` expect means 'send immediately.' If the expect string is not seen within the chat timeout (default 45 s), the script aborts. Set `-T 90` if your network is slow."
- §103.4 LCP/IPCP — the reader sees the names but not what is negotiated. Add: "LCP negotiates link options (MTU, magic number, async control character map). IPCP negotiates IPv4 address, DNS servers, and optionally IPCP-CompressionProtocol. Both run after `CONNECT` and before traffic flows. `pppd -v` shows each packet."
- §103.5 The `TIOCSETD, N_PPP` ioctl is the actual mechanism but is mentioned without explanation. One sentence: "`TIOCSETD` swaps the tty's line discipline. The default (`N_TTY`) treats input as text lines; `N_PPP` treats input as HDLC frames and hands assembled frames to `ppp_generic`. This is how the kernel converts a UART into a netdev."
- §103.6 CMUX framing — the user is told to run `ldattach GSM0710` but the *frame format* is opaque. A short ASCII diagram of a GSM 07.10 basic frame (F8 | DLCI/CR/EA | C/EA | data | FCS | F8) would land well. Cross-reference n_gsm.c so the curious reader can grep.
- §103.8 ECM-via-built-in-USB is described well, but the *mechanism* (the module has an internal USB-to-cell bridge) deserves one sentence: "These modules embed a USB device controller and a CDC-ECM gadget driver inside the module firmware. Linux on the host sees a regular USB Ethernet adapter; the module's own MCU forwards frames to the cellular MAC."
- §103.10 Pitfall "Default route conflict" mentions `replacedefaultroute` and "set metric" but does not show how. One concrete line: "Either pass `replacedefaultroute` to pppd, or omit `defaultroute` and add the route manually with `ip route add default via $PEER_IP dev ppp0 metric 700`."

---

## Ch104 — NB-IoT / Cat-M1

### AI wording / sledgehammer / buzzwords
- > "the **low-power-cellular** subset of LTE — **NB-IoT (Cat-NB1/NB2)** and **LTE-M (Cat-M1)**."
  - Em-dash glue. Fine in a header blurb; keep.
- > "the **PSM (Power Saving Mode)** and **eDRX (extended DRX)** features that make a 19 Ah Li-SOCl2 cell last 10 years"
  - "Make X last 10 years" is marketing. Rewrite: "the PSM and eDRX features that let a 19 Ah Li-SOCl2 cell run a sensor for up to ten years."
- > "**PSM is the killer feature; eDRX is the secondary lever.**"
  - "Killer feature" again (Ch99, Ch100, here). "Secondary lever" is corporate. Rewrite: "PSM is the primary power saver; eDRX is a smaller secondary saving."
- > "**Use PSM aggressively or your battery life numbers are fiction**."
  - "Aggressively / fiction" is fan-prose. Rewrite: "Use PSM correctly or your battery life estimate is wrong by orders of magnitude."
- > "Get the AT commands right or you regress to 100 mA always-on and miss the spec by 1000×."
  - "Regress / miss the spec by 1000×" is consultant. Rewrite: "If the AT commands are wrong, the modem stays at 100 mA always-on. Battery life drops by a factor of 1000."
- > "This is the technology behind smart water meters, GPS livestock trackers, vending-machine telemetry, and rural emergency call-boxes."
  - Brand-name parade. Fine for color; keep.
- > "the engineering is **religiously enforcing PSM duty cycle**."
  - "Religiously" is rhetorical. Rewrite: "the engineering is enforcing PSM duty cycle on every wake."
- > "Still: 10 years on one D-cell with no maintenance. The technology is real; the engineering is …"
  - "The technology is real" reads like a sales line. Rewrite: "Ten years on one D-cell with no maintenance is achievable. The engineering is …"

### ESL readability
- > "TX → wait for downlink ACK → enter PSM, radio off, modem off-but-registered. Network keeps the IP/PDP/security context. Next wake (timer or external GPIO): instant resume, no re-registration."
  - "Instant resume" + arrow-as-prose + parenthetical. Break: "The cycle is: TX, wait for the downlink ACK, then enter PSM. The radio and modem are off, but the network still considers the device registered (IP, PDP context, and security keys are kept). On the next wake — by timer or external GPIO — the device resumes immediately, with no re-registration."
- > "The two timers:" with `T3324`/`T3412` listed as bullets is OK, but the units of `"00000100"` are opaque (it is the 8-bit 3GPP timer encoding). Add one sentence: "The argument is a 3GPP timer value encoded as 8 bits — bits 7..5 are the unit (10 minutes, 1 hour, 10 hours…), bits 4..0 are the count. `00000100` = unit 0 (2 seconds) × 4 = 8 s, *or* by another unit code, 4 hours. Decode with Table 10.5.163 in TS 24.008 to avoid surprise."
- > "annoying but simple."
  - "Annoying" is judgmental. Rewrite: "verbose but simple."
- > "Realistic constraints knock this to **8–12 years**:"
  - "Knock this to" is informal. Rewrite: "Real-world constraints reduce this to 8–12 years:"

### Needs more depth
- §104.2 PSM diagram shows currents but does not explain *why* idle DRX is ~5 mA: the radio is off most of the time but wakes every DRX cycle (typically 1.28 s in LTE idle) to listen for paging. Add: "In idle DRX, the modem wakes every paging cycle (default 1.28 s) to listen for downlink. That dominant cycle averages to ~5 mA."
- §104.2 T3412 / T3324 — the chapter mentions the *names* but not the **fact that PSM lasts up to T3412 minus T3324**. Add: "The math: the modem stays idle-listening for T3324, then enters PSM for the remainder of T3412. So T3412=24h, T3324=4s gives 23h:59m:56s of deep sleep per cycle."
- §104.2 eDRX numbers (~2.92 hours) is the *maximum*; the reader does not know what the *typical* values are. Add a sentence: "Typical eDRX cycles are 20 s, 40 s, 81 s, 163 s, up to 2.92 hours. The carrier negotiates the actual value; many grant only up to 81 s."
- §104.3 `AT+NSOST=0,...,5,68656C6C6F` — explain the structure once: "The arguments are socket-id, remote-ip, remote-port, payload-length, payload-as-hex. `68656C6C6F` is ASCII 'hello.'"
- §104.5 The 47-µAh-per-hour table is excellent. Add the **measurement method**: "These numbers are from a 1 Ω shunt on VBAT with a Tek MDO scope at 1 MS/s and the area integrated in software. A handheld DMM averages and hides the TX spike — do not trust it for this work."
- §104.7 Pitfall "Voltage drop at cold temp" — the "wake-warmer" is mentioned but the *passivation* mechanism is left implicit. One sentence: "Li-SOCl2 cells form a lithium-chloride passivation layer on the anode during storage. This layer raises internal resistance, so the first high-current pulse can drop VBAT to 2.7 V momentarily. A low-current 'depassivation' pulse (e.g., 50 mA for 100 ms) breaks the layer before the modem TX."
- §104.7 "PSM not granted by carrier" — add the *visible* symptom that confirms it: "After `AT+CPSMS=1,,,...`, query `AT+CPSMS?`. If T3412 returns a much smaller value than requested (or `0`), the carrier did not grant your requested PSM and your modem will not enter deep sleep."

---

## Ch105 — RFID / NFC

### AI wording / sledgehammer / buzzwords
- > "The chips are cheap (MFRC522 modules are $1), the standards are real, the security is half-broken (Mifare Classic was cracked in 2008), and the kernel actually has an NFC subsystem (`net/nfc/`) most engineers don't know about."
  - 40-word triplet-plus-bonus with two parentheticals. Break: "The chips are cheap (MFRC522 modules cost about $1). The standards are real. The security is half-broken — Mifare Classic was cracked in 2008. And Linux has an NFC subsystem (`net/nfc/`) that most engineers do not know exists."
- > "**RFID/NFC at 13.56 MHz is inductive coupling — the reader's antenna creates a magnetic field at 13.56 MHz, which powers the tag's IC AND carries data via load modulation**."
  - 35 words with a capitalised "AND" for emphasis. Rewrite: "At 13.56 MHz, RFID and NFC use inductive coupling. The reader's antenna generates a magnetic field. That field powers the tag's IC, and the tag sends data back by modulating its load on the field."
- > "The 'register dance' with the reader chip is mostly:"
  - "Register dance" is informal (used twice in this chapter and earlier in Ch98). Rewrite: "The reader chip uses a fixed sequence of register writes:"
- > "the security is half-broken"
  - Fine but reads as opinion. Quantify: "the basic-Mifare-Classic Crypto1 cipher has been broken since 2008."
- > "Cheap and good enough for 90 % of jobs."
  - "90 % of jobs" is filler. Rewrite: "Cheap and adequate for most access-control work."
- > "Don't try to wind your own without an impedance analyzer — buy a module."
  - "Don't try" + em-dash. Rewrite: "Do not wind your own antenna unless you have an impedance analyser. Buy a tuned module instead."
- > "modules that get this wrong are quietly broken."
  - "Quietly broken" is informal. Rewrite: "modules that compute BCC wrong report a passing read but with corrupt UIDs."

### ESL readability
- > "Tag→reader is **load modulation** at 847.5 kHz subcarrier (Type A); reader→tag is direct ASK modulation at 100 % or 10 %."
  - Two technical claims, one semicolon. Rewrite: "Tag-to-reader uses load modulation with an 847.5 kHz subcarrier (Type A). Reader-to-tag uses direct ASK modulation, at either 100 % or 10 % depth."
- > "Most projects skip it for simplicity and use libnfc directly on `/dev/spidev` or the MFRC522 user-space drivers below."
  - 25 words, one clause. Rewrite: "Most projects skip the kernel NFC stack. They use `libnfc` directly against `/dev/spidev`, or one of the MFRC522 user-space drivers shown below."
- > "What this exposes: …" three-bullet list.
  - The list is concise but mixes API points and edge cases. Consider grouping: "API points: transceive does both TX and RX; bit framing must be set before transceive. Edge cases: BCC byte is a sanity check; HALT must come before the next REQA."

### Needs more depth
- §105.2 The diagram is decorative but the *encoding* (Miller for tag-to-reader, Modified-Miller / Manchester for reader-to-tag) is mentioned in the Focus blurb and never illustrated. A simple ASCII waveform of one bit in each direction would land well for the curious reader. At minimum, name the encoding directions correctly in §105.2.
- §105.2 Anticollision steps are shown but the algorithm is not explained — the reader is told it produces the UID without seeing the binary search. One paragraph: "When two or more tags answer REQA, their UIDs collide. The reader sends ANTICOLL with a known prefix length; tags whose UID matches the prefix respond. The reader detects the first colliding bit, fixes its prefix to one side, and recurses. This is a binary tree walk on the UID — log2(N) rounds for N tags."
- §105.3 Crypto1 / Authent — the chapter mentions the Authent command but does not explain that **the tag never sends the key**; it is a challenge-response. One sentence: "Authent never transmits the key on the air; the reader and tag both use the key to encrypt a 32-bit nonce challenge. A correct response proves both sides know the key."
- §105.6 The driver only does REQA + ANTICOLL — the chapter promises authentication and block read in §105.9 lab 3, but the driver skeleton stops at ANTICOLL. Either show the SELECT-then-AUTH commands here, or be explicit that the lab requires the reader to add SELECT + Authent + Read (and cross-reference an example repo with the full code).
- §105.7 "Crypto1 is fundamentally broken" — name the attacks (Nack reuse, Darkside attack, sector-key recovery via mfoc/mfcuk) so the reader can defend the choice of DESFire to a stakeholder. Two sentences max.
- §105.10 Pitfall "Tag already in HALT state" — say *why* this happens (the previous read sent HALT) and add the practical fix: "Use WUPA (0x52) instead of REQA after a HALT or in a multi-reader environment; WUPA wakes HALTed tags too."

---

## Ch106 — Fingerprint sensors

### AI wording / sledgehammer / buzzwords
- > "**standalone fingerprint modules** that do the imaging + matching internally and expose a UART command protocol."
  - Fine.
- > "Fingerprint is the dominant biometric for low-friction access control (vs face: privacy issues, harder to enroll; vs iris: $$$)."
  - "$$$" is slang. Rewrite: "Fingerprint is the dominant biometric for low-friction access control. Face recognition has privacy and enrolment problems; iris is expensive."
- > "**modules are stateful — they remember which template ID is enrolled in which slot, and protocol commands operate on that state**. Enrollment is a 3-step dance: …"
  - "3-step dance" again (also Ch98 §98.3, Ch99 §99.4). Pick one chapter to use this phrase. Here, rewrite: "Enrollment is a three-step sequence:"
- > "Perfect for: smart-lock products, time-and-attendance kiosks, equipment-checkout terminals, secure-area entry."
  - "Perfect for" + bullet-as-prose. Rewrite: "Common applications: smart locks, time-and-attendance kiosks, equipment-checkout terminals, secure-area entry."
- > "trips most integrations."
  - "Trips" idiom. Rewrite: "is where most integrations fail."
- > "The double-capture is for robustness — fingerprints don't sample identically each time; the union improves matching tolerance."
  - Em-dash + semicolon. Rewrite: "Double-capture improves robustness. Fingerprints do not sample identically each time, so the union of two captures gives better matching tolerance."
- > "That's the entire reader: ~150 lines for the core, ~50 for SPI/GPIO setup."
  - "That's the entire" cliché. Rewrite: "The whole reader fits in about 200 lines (150 core, 50 SPI/GPIO setup)."
- > "It's the 'premium feel' choice."
  - "Premium feel" is marketing. Rewrite: "Choose the R503 when the product needs a polished user experience."

### ESL readability
- > "vs face: privacy issues, harder to enroll; vs iris: $$$"
  - The "vs" / colon / semicolon syntax is hard for ESL. See rewrite above.
- > "(or i.MX6ULL in suspend) as wake controller."
  - Parenthetical alternative. Rewrite: "An STM32L0 acts as the wake controller (the i.MX6ULL can be used in suspend, but its standby current is higher)."
- > "Hostile re-enroll detection."
  - "Hostile re-enroll" is jargon. Rewrite: "Detect malicious re-enrolment."
- > "Plus the kernel **`libfprint`** path for USB fingerprint scanners (laptop-style)."
  - Sentence fragment in the What blurb. Rewrite: "This chapter also covers the libfprint path for USB fingerprint scanners — the laptop-style readers."

### Needs more depth
- §106.3 The packet framing protocol description omits a *crucial* point: the checksum is over Packet ID, Length, and Data — **not** the header or the address. The example values implicitly use this rule but the prose says "sum of bytes from Packet ID to last data byte" — which is correct, but ambiguous because the "last data byte" includes the command code. Add one explicit example: "For GetImg (cmd=0x01, no payload): checksum = 0x01 + 0x00 + 0x03 + 0x01 = 0x05. Stored as 0x00 0x05."
- §106.5 Score 0..2000 with threshold 50 is stated but the FAR/FRR curve is not described. One sentence: "Above 50 = match. Raising to 100 cuts false accepts to <0.0001 % but rejects ~5 % of legitimate fingers. Tune for your application's risk profile."
- §106.5 "1:N search" is shown but the chapter does not explain that the chip iterates internally — *the host does not send each candidate*. One sentence: "Search runs entirely on the module's DSP. The host issues one Search command; the module scans all stored templates and returns the best match (or no-match) in about 1 second."
- §106.6 The 9-byte header structure is in the source as a magic literal `{0xEF, 0x01, 0xFF, ..., (n+2) & 0xFF}`. Add a one-line comment in the listing labelling each byte (the prose at §106.3 explains it, but the reader will copy this file and want it self-documenting).
- §106.7 PAM module skeleton — `pam_get_user` and `is_user_authorized` are skeletons. Either show the per-user authorisation file format (e.g., `/etc/r503/users.allow` with lines `alice 1` for slot 1) or note where the example repo has the full code.
- §106.9 Lab 9 "Hostile re-enroll detection" — the prevention is to require admin re-confirmation, but the chapter does not say *how* the firmware should know an admin is present (a second admin fingerprint? a hardware key? a physical lock-out switch?). Add one sentence: "Tie admin re-confirmation to a known admin fingerprint slot (e.g., slot 0) — re-enrolment requires a successful admin match within the last 60 seconds."
- §106.10 "Privacy / GDPR" — biometric data handling deserves more than one bullet. Add: "Templates are not raw images, but they are still biometric data under GDPR / CCPA. Store encrypted at rest (use the kernel's `keyctl` or fscrypt). Never transmit templates over an unencrypted link. Provide a documented deletion path."

---

## Ch107 — GPS / GNSS + PPS

### AI wording / sledgehammer / buzzwords
- > "We compare … turning a $5 receiver into a **stratum-1 time server**."
  - "Turning a $X receiver into a stratum-1 server" is a marketing line. Fine in the blurb; keep.
- > "**NMEA gives you the wall-clock seconds but is laggy and jittery (~50–500 ms after the second); PPS is the actual nanosecond-accurate edge**."
  - "Laggy" is informal. Rewrite: "NMEA reports the wall-clock second, but it arrives 50–500 ms after the actual second. PPS is the nanosecond-accurate edge."
- > "Understanding the PPS plumbing — pin → kernel `pps_gpio` driver → /dev/pps0 → chrony's refclock — is what separates 'GPS time sync' from 'real GPS time sync.'"
  - 30 words, four em-dash steps, quoted-slang close. Rewrite: "The PPS path is the key: GPS pin → kernel `pps_gpio` driver → `/dev/pps0` → chrony refclock. Get this right and you have sub-microsecond GPS time. Skip the PPS and you have NMEA-only ±100 ms."
- > "The killer message: `UBX-NAV-PVT`"
  - "Killer message" again. Rewrite: "The single most useful message: `UBX-NAV-PVT`."
- > "You just built a stratum-1 NTP server with $20 of parts."
  - Marketing close. Rewrite: "Total parts cost is about $20. The result is a stratum-1 NTP server."
- > "The `u-center` Windows tool (or `ubxtool` in Linux's `gpsd` package) is invaluable for crafting these."
  - "Invaluable" is marketing. Rewrite: "Use `u-center` on Windows or `ubxtool` from `gpsd-clients` to build these CFG messages."
- > "The technique generalizes — *any* time-domain measurement on Linux … gets much easier with a real PPS time source."
  - "Generalizes" + italic "any" + closing flourish. Rewrite: "The same PPS technique works for any time-domain measurement on Linux: synchronised audio between boards, distributed instruments, IP-connected oscilloscopes."
- > "30 seconds of Python, ~$15 of hardware, you have your inverter on Home Assistant / Grafana."
  - Time-and-money-then-result tic. Rewrite: "About 30 lines of Python and $15 of hardware put the inverter on Home Assistant or Grafana." *(Note: this quote is actually from Ch108 §108.7 but the same form recurs in Ch107 §107.6 — flag the pattern across chapters.)*

### ESL readability
- > "GNSS time vs UTC leap seconds. GPS time is leap-second-free; UTC isn't."
  - "Leap-second-free" / "isn't" rapid contractions. Rewrite: "GPS time vs UTC leap seconds. GPS time has no leap seconds; UTC does."
- > "PPS-disciplined (kernel timestamps the GPIO edge with hardware-clock precision; chrony combines the slow-but-labelled NMEA with the fast-but-unlabelled PPS edge) gets you to ±100 ns."
  - 32 words, one nested parenthetical, two compound modifiers. Rewrite: "With PPS, the kernel timestamps each GPIO edge using the hardware clock. Chrony combines two streams: NMEA, which is slow but tells you *which* second this is; PPS, which is fast but does not name the second. Together they reach ±100 ns."
- > "The receiver synchronizes its 1 kHz timepulse generator to its GNSS-derived clock; jitter is ~20–50 ns."
  - "1 kHz timepulse generator" — but PPS is 1 Hz, not 1 kHz. Is this a typo (the chip's *internal* timepulse can be configured up to 25 MHz; PPS by default is 1 Hz)? Verify and fix.

### Needs more depth
- §107.4 The PPS path from GPIO IRQ to `/dev/pps0` is described well but the **kernel timestamping mechanism** (`pps_event` → `pps_get_ts`) is hidden. One sentence: "On each GPIO edge, the `pps_gpio` IRQ handler calls `pps_event(pps, &timestamp, ...)`. The PPS core stores the timestamp in a ring buffer keyed by sequence number. Chrony reads it via `PPS_FETCH` ioctl on `/dev/pps0`."
- §107.4 The phrase "captured with `getnstimeofday()` precision — typically sub-microsecond on a Cortex-A7" is misleading. `getnstimeofday` is deprecated; modern kernels use `ktime_get_real_ts64`. Also the *latency* (not the precision of the clock read) is what matters — IRQ-to-handler latency on a non-RT Linux is the bottleneck. Rewrite: "The actual precision is limited by IRQ latency: ~1–10 µs on a non-RT Linux Cortex-A7. PREEMPT_RT brings it under 1 µs."
- §107.6 Chrony refclock — explain *why* PPS needs to be `lock`-ed to a slow source. The `lock GPS prefer trust` clause is given but not derived. One sentence: "PPS edges arrive every second but carry no second-number. Chrony needs a slow 'labelled' source (SHM from gpsd) to assign integer seconds to the PPS edges. `lock GPS` tells chrony to use GPS for labelling and PPS for fine timing."
- §107.7 The Fletcher checksum is computed inline but never *named* — the reader who has only seen CRC16 will wonder what algorithm this is. One sentence: "UBX uses the Fletcher-8 checksum (two byte-wide accumulators, ck_a and ck_b). It is weaker than CRC16 but cheap to compute on small MCUs."
- §107.9 Pitfall "GNSS time vs UTC leap seconds" — the user is told to use `LeapSeconds` but the standard place to look is named differently in each vendor. For u-blox: `UBX-NAV-TIMEUTC` has the `valid` bits including `leapSValid`. One concrete sentence about *where* to find the right field would help.

---

## Ch108 — RS-485 + Modbus RTU

### AI wording / sledgehammer / buzzwords
- > "RS-485 is unglamorous but irreplaceable; learning it opens an enormous market"
  - "Unglamorous but irreplaceable" + "enormous market" = marketing. Rewrite: "RS-485 is everywhere in industrial systems. Knowing it gives you access to the industrial IoT market that pure-WiFi devices cannot reach."
- > "**RS-485 is half-duplex differential signaling on a 2-wire bus; you must control the line driver direction (TX or RX) at sub-bit-time precision, and Modbus framing depends on inter-character timeouts that vary with baud rate**."
  - 45 words, two clauses bridged by "and". Break: "RS-485 is half-duplex differential signalling on a two-wire bus. You must switch the driver between TX and RX with sub-bit-time precision. On top of that, Modbus RTU detects frames by inter-character timeouts that scale with baud rate."
- > "Termination (120 Ω at each bus end), biasing (fail-safe to known idle state), and ground reference (a multi-meter check across grounds is mandatory before connecting devices powered from different sources) are the three things that break a working bench setup when you deploy it."
  - 50-word sentence with three nested parentheticals. Break: "Three things break a bench setup when you deploy it on a real factory floor. Termination — 120 Ω at each end of the bus. Biasing — fail-safe pull-ups so the idle line is a known logic level. Ground reference — measure the voltage between grounds before connecting devices powered from different supplies."
- > "MAX13487 — production, especially on Linux where sub-bit-time DE control is hard. Auto-direction = 'wire it up and forget.'"
  - "Wire it up and forget" is slang. Rewrite: "MAX13487 — recommended for production. Auto-direction removes the timing-critical DE/RE control."
- > "Auto-direction's main benefit."
  - Fragment. Rewrite: "This is auto-direction's main benefit."
- > "30 seconds of Python, ~$15 of hardware, you have your inverter on Home Assistant / Grafana."
  - Marketing tic also flagged in Ch107 above. Rewrite: "About 30 lines of Python and $15 of hardware put the inverter on Home Assistant or Grafana."

### ESL readability
- > "Auto-direction transceivers (MAX13487) solve this in hardware."
  - Fine.
- > "Daisy-chain only (no star, no T-stubs > 30 cm). Termination at both physical ends."
  - "T-stubs" is jargon. Rewrite: "Daisy-chain topology only. No star or branch wiring. Spurs from the main bus must be shorter than 30 cm. Terminate both physical ends."
- > "At 9600 baud, 1 char = 11 bits / 9600 = 1.146 ms; 3.5 char = 4 ms idle to detect end-of-frame."
  - Compressed math with two semicolons. Rewrite: "At 9600 baud, one 11-bit character takes 1.146 ms. The 3.5-character inter-frame gap is therefore about 4 ms — that is the idle time after which a receiver declares end-of-frame."
- > "Holding vs input registers. Function 0x03 = holding (R/W); 0x04 = input (R-only)."
  - Semicolon glue. Fine in a pitfall bullet; keep.
- > "Now your i.MX6ULL is slave 5 on the bus; any master can poll it for sensor data."
  - "Slave" wording — keep terminology consistent with the section header. The Modbus spec uses "server" in newer versions; the rest of the chapter uses "slave." That is fine if consistent.

### Needs more depth
- §108.1 Fail-safe biasing — the diagram shows "+5V via 680 Ω to A; GND via 680 Ω to B (bias)" but does not derive *why* this is required. One sentence: "When no driver is active, the bus floats and the receiver's output is undefined. A weak pull-up on A and pull-down on B forces a defined idle ('1') so frame-start detection works. Some modern transceivers (SP485E, ISL81387) integrate this internally."
- §108.4 Kernel RS-485 mode — the chapter says "Some UARTs (i.MX has integrated '9-bit mode' with hardware DE) do this directly without GPIO toggling — check your reference manual for SER_RS485_AUTO." This is the **single most useful** trick for production. Promote it to its own paragraph: "On i.MX6ULL, the UART's `UCR3.DSR` and `UTS.RXFULL` bits combined with the *RTS-as-DE* function (selected in the IOMUX) make hardware DE control possible. The driver toggles DE inside the UART state machine itself — no IRQ-context GPIO writes, no jitter. Enable via the DT properties shown; verify with a scope on the DE line during TX."
- §108.5 Modbus inter-character timeout — at high baud (115200) the 3.5-char gap is 280 µs. Most Linux UART drivers buffer for at least 10 ms before delivering. So Modbus RTU at 115200 needs *hardware*-assisted byte timestamping or a low-latency reads. Add: "At 115200 baud, the 3.5-char inter-frame gap shrinks to ~280 µs. This is below the kernel's default UART poll/deliver interval (~10 ms). `libmodbus` uses select() and timing heuristics that work to about 38400 baud; above that, you need either kernel-side RS-485 framing support or a hardware timestamper."
- §108.5 CRC16 polynomial 0xA001 — name it: "this is the reversed polynomial of the standard CRC-16-IBM (0x8005). Initial value 0xFFFF, no final XOR. Tables and code are everywhere; do not hand-roll."
- §108.7 The float-encoding pitfall (§108.10) deserves a worked example in §108.7. One sentence: "Inverters often pack a 32-bit float as `(reg[0] << 16) | reg[1]` *or* `(reg[1] << 16) | reg[0]` *or* `reg[0]` and `reg[1]` byte-swapped. Read a known value (the grid voltage, ~230 V) and check which interpretation gives a plausible number."
- §108.9 Lab 4 multi-slave bus — useful to add a sentence about how to detect collisions: "If two devices share an address, one will respond first and the other's response will collide on the wire. The master sees a CRC error or a malformed frame. Use `modpoll -1` to query each slave individually during bring-up to find duplicates."

---

## Ch109 — LIN bus

### AI wording / sledgehammer / buzzwords
- > "LIN is also creeping into industrial actuator buses (HVAC valves, building blinds) for the same reason: $0.40 per node + 1-wire bus is unbeatable for 'dumb' peripherals."
  - "Creeping into" + "unbeatable" + "dumb peripherals" — all informal. Rewrite: "LIN is also spreading into industrial actuator buses (HVAC valves, building blinds). At about $0.40 per node and one wire, it is the cheapest option for simple peripherals."
- > "Linux's lack of native support means you write the framing yourself, which is a great UART exercise."
  - "A great UART exercise" reads like a tutorial blurb. Rewrite: "Linux has no native LIN subsystem; you write the framing yourself. This is also a useful UART exercise."
- > "**LIN is UART + a 'break' pulse + an 8-bit 'sync' byte + a 6-bit 'PID' + 1–8 data bytes + 8-bit checksum, all run by a single master broadcasting schedules; slaves never speak unprompted**."
  - 40 words, six pluses, one semicolon. Rewrite: "A LIN frame is: a UART start, a 'break' pulse, an 0x55 sync byte, a 6-bit Protected Identifier (PID) byte, one to eight data bytes, and a checksum byte. A single master schedules every frame. Slaves never transmit on their own."
- > "The protocol is dirt simple; the trap is getting the timing right on a non-deterministic Linux UART."
  - "Dirt simple" + semicolon. Rewrite: "The protocol is simple. The trap is getting the timing right on a non-deterministic Linux UART."
- > "Robust but ugly."
  - "Ugly" is informal. Rewrite: "Reliable but messy."
- > "That's a working LIN 2.x master in ~80 lines."
  - "That's a working X" close. Fine once per chapter. Pair with the same phrase in §106.6 ("the entire reader: ~150 lines") — vary across chapters.
- > "You've now controlled an automotive comfort actuator from Linux."
  - "You've now …" celebratory close. Rewrite: "At this point you have driven an automotive comfort actuator from Linux."

### ESL readability
- > "The LIN bus is **a single wire pulled up to 12 V (or 7–18 V in practice)**, with each node yanking it low to transmit."
  - "Yanking" is slang. Rewrite: "The LIN bus is a single wire pulled up to 12 V (typically 7–18 V in practice). Each node pulls the wire low to transmit."
- > "Detecting the break from user-space is the awkward part on Linux — there's no clean API."
  - "Awkward / clean API" idiom. Rewrite: "Detecting the break from user-space is hard on Linux; there is no dedicated API."
- > "Both work, neither is elegant. A proper LIN slave belongs on an MCU."
  - "Neither is elegant" / "proper" — opinion. Rewrite: "Both methods work but neither is clean. For real products, run the LIN slave on a dedicated MCU."
- > "The blower controller's slave ID for 'set fan speed' is typically `0x20` (vendor-specific; reverse-engineering via LIN-bus traffic dumps from forums)."
  - 25-word parenthetical run-on. Rewrite: "The blower controller's slave ID for 'set fan speed' is typically `0x20`. The exact ID is vendor-specific; you find it by capturing bus traffic and matching commands to behaviour."

### Needs more depth
- §109.4 The four "tricks" for generating the break are listed but the chapter does not say *which one the example code uses*. The C code in §109.5 picks trick #4 (TIOCSBRK/TIOCCBRK). State that explicitly at the top of §109.5: "The sample code uses trick #4 (i.MX-specific TIOCSBRK). On other SoCs, fall back to trick #2 (baud-rate switch)."
- §109.5 The `cksum_enhanced` function returns the inverted sum, but the chapter says "classic checksum = sum of data only; enhanced = sum of PID + data" without mentioning the **inversion (NOT)** step. Add: "Both classic and enhanced checksums invert the final byte (`~sum`). Forget the inversion and every frame is rejected."
- §109.6 Detecting the break — `TIOCMIWAIT(TIOCM_BRK)` and `TIOCGICOUNT` are the two methods given. Add one sentence about which is more reliable: "`TIOCMIWAIT(TIOCM_BRK)` blocks until the next break event, which is the cleanest option on i.MX UARTs that report it. `TIOCGICOUNT` polling is the fallback if your driver does not raise TIOCM_BRK."
- §109.2 PID parity formulas — list them but also include a worked example so the reader can sanity-check: "For ID=0x10 (binary 010000), P0 = 0^0^0^0 = 0 and P1 = ~(0^0^0^1) = 0. Final PID = 0b01010000 = 0x50." (The lab in §109.9 step 2 already asserts this, so the example is consistent.)
- §109.7 Sleep/wake — the wake pulse is described as "any node pulls the bus low for ≥250 µs." But the *master* also has to power the bus and re-start the schedule. Add: "After a wake pulse, the master must wait at least 50 ms (in LIN 2.x) before issuing the next break — slaves use that time to leave low-power mode and prepare their UARTs."
- §109.10 Pitfall "Bus-off via short" — "Recover by raising EN to put the transceiver in low-power mode" is unclear. Rewrite the recovery: "Recovery: pull EN low for at least 10 µs (transceiver enters sleep), then raise EN. If the short is still present, the bus stays dominant; if the short cleared, the bus returns to idle (recessive)."

---

## Ch110 — CAN deep dive

### AI wording / sledgehammer / buzzwords
- > "Mainline Linux's SocketCAN is the best CAN stack on any OS"
  - Marketing claim. Rewrite: "Mainline Linux's SocketCAN is the most complete CAN stack of any general-purpose OS."
- > "Build deep familiarity here and you become the team's go-to for vehicle/industrial integration."
  - "Go-to / build deep familiarity" — career-coaching tone. Rewrite: "After this chapter you can take on most vehicle and industrial CAN integration work."
- > "**classic CAN is bit-stuffed differential bus with priority arbitration via CSMA/CR; CAN-FD adds a second bit rate during the data phase to squeeze 64 bytes through a 1 Mbps bus in ~120 µs**."
  - 40-word sledgehammer + "squeeze" verb. Break: "Classic CAN is a bit-stuffed differential bus with priority arbitration via CSMA/CR. CAN-FD adds a second, faster bit rate during the data phase. The result: 64 bytes through a 1 Mbps arbitration bus in about 120 µs."
- > "Get the bit-timing right (sample point, SJW, prop+phase segments) or you'll see 'CAN bus errors' that look like wiring problems but are firmware."
  - "But are firmware" awkward phrase. Rewrite: "Get the bit timing right (sample point, SJW, prop and phase segments). Otherwise you will see CAN bus errors that look like a wiring fault but are caused by configuration."
- > "Tries to falter near 1 Mbps under load."
  - "Tries to falter" is awkward English. Rewrite: "Struggles near 1 Mbps under load."
- > "Surprising when first writing code."
  - Fragment. Rewrite: "This surprises people writing CAN code for the first time."
- > "You can build a complete car-diagnostics dashboard in 200 lines of C + a fast Linux box."
  - "Fast Linux box" + plus-sign-as-prose. Rewrite: "About 200 lines of C and a Linux board are enough to build a complete OBD-II dashboard."

### ESL readability
- > "**Dominant** = 0 (driven), **recessive** = 1 (idle). A dominant always overwrites a recessive → low-ID wins."
  - Arrow-as-prose. Rewrite: "Dominant is logical 0 (actively driven). Recessive is logical 1 (idle). Dominant always overwrites recessive, so the lowest-numbered ID wins arbitration."
- > "ID 0 is highest priority. A node that always sends ID 0 starves everyone else."
  - Fine; the consequence is clear.
- > "Use kernel-side RS-485 framing support or a hardware timestamper."
  - This is from §108 — but the same pattern recurs. Keep as a flag for the cross-cutting list.
- > "Some IDs are reserved (0x3C, 0x3D = master/slave request frames; 0x3E, 0x3F = reserved)."
  - Semicolon glue. Fine.
- > "ID 0 is highest priority. A node that always sends ID 0 starves everyone else. Reserve low IDs for hard-real-time critical messages only."
  - "Starves" is OK but consider "blocks everyone else from transmitting" for clarity.

### Needs more depth
- §110.3 Bit timing example — the math is shown but the **propagation segment derivation** is left implicit. Add one sentence: "The propagation segment must cover the round-trip delay between any two nodes on the bus: bus length × 2 × 5 ns/m + transceiver delays (~150 ns each end) + sampling latency. For a 50 m bus, this is ~700 ns — at 16 TQ × 125 ns/TQ, that is 5.6 TQ, so a prop segment of 6+ TQ is required."
- §110.3 SJW (Synchronisation Jump Width) is mentioned only in passing in the Focus blurb and never explained. Add a sentence in §110.3: "SJW is how many TQ the receiver may shift the sample point in either direction to re-synchronise on each edge. Typical SJW = 1 (minimum) to 4 (maximum). Set it equal to the smaller of Phase1/Phase2 for best noise tolerance."
- §110.5 Filters — the example uses `can_id` + `can_mask` but the rule (`(received_id & mask) == (can_id & mask)`) is not stated. Add: "Each filter matches when `(received_id & can_mask) == (can_id & can_mask)`. You can chain up to 64 filters per socket; the kernel ORs them."
- §110.6 ISO-TP — the example sends a UDS request but does not show how the **kernel handles flow control** (FC frames). One sentence: "When the response is multi-frame, the kernel automatically sends FC frames (with BS and STmin from setsockopt or defaults). User-space only sees the reassembled 19-byte VIN."
- §110.6 The chapter says "Without ISO-TP, you'd be writing the segmentation state machine yourself" but does not name the spec. Add: "The segmentation rules are in ISO 15765-2:2016. The kernel `can-isotp` module implements the full state machine."
- §110.8 BCM — `TX_SETUP` is just one BCM opcode; the others (RX_SETUP for receive filters with content change detection, TX_DELETE, etc.) are not mentioned. One sentence: "BCM also has `RX_SETUP` for content-change notification (only wake user-space when a frame's data actually changes), `TX_DELETE`/`RX_DELETE`, and `*_READ`. See `Documentation/networking/can.rst`."
- §110.12 Pitfall "ID 0 is highest priority" — add the practical guidance: "On most automotive buses, IDs below 0x100 are reserved for safety-critical messages (powertrain, ABS). Use IDs in the 0x500–0x7FF range for application traffic."

---

## Ch111 — Quadrature encoders & rotary

### AI wording / sledgehammer / buzzwords
- > "**quadrature decoding is 'two channels 90° out of phase; the leading channel tells direction'**."
  - Sledgehammer + semicolon. Rewrite: "Quadrature decoding works on two channels that are 90° out of phase. The leading channel tells you the direction of rotation."
- > "Mechanical encoders bounce horribly (5+ ms of noise per click) and need debouncing; optical encoders are clean but expensive; magnetic encoders are the middle ground."
  - 25-word triplet with two semicolons. Rewrite: "Mechanical encoders bounce badly — 5 ms or more of noise per click — and need debouncing. Optical encoders are clean but expensive. Magnetic encoders are the middle ground."
- > "For position control, absolute beats incremental every time"
  - "Beats every time" is informal. Rewrite: "For position control, absolute encoders are better in nearly every case."
- > "100 Hz loop is plenty for a brushed motor (much slower mechanical dynamics)."
  - "Is plenty" informal. Rewrite: "A 100 Hz control loop is adequate for a brushed motor. Mechanical dynamics are much slower than that."
- > "Both channels' rising + falling edges call this; it handles all 12 valid transitions and silently zeros the 4 invalid (missed-edge) transitions."
  - Semicolon + "silently zeros" awkward. Rewrite: "Both channels call this on rising and falling edges. The 12 valid transitions produce ±1; the 4 invalid transitions (where both bits changed at once = missed edge) produce 0."
- > "Software bug? Look at the QDEC_TABLE."
  - Fragment-as-question. Rewrite: "If counts are wrong, check the QDEC_TABLE."

### ESL readability
- > "Software-decode in C:" / "Software qdec in user-space (libgpiod)"
  - "Software-decode" / "qdec" mixed terms within one chapter. Use one term ("software decode") consistently.
- > "Status in mainline Linux:"
  - Section heading style; OK.
- > "Software qdec scheduled but missed under load."
  - Pitfall headline. Rewrite: "User-space decode misses edges under CPU load."
- > "AS5048A magnet alignment. The magnet must be on the shaft axis (radially polarized, diametric) within ±0.5 mm; misalignment → non-linear angle errors of several degrees."
  - "Radially polarized, diametric" — these two terms are not the same (radial vs diametric magnetisation). Pick one and define it. Likely should be "diametrically magnetised."

### Needs more depth
- §111.2 The four-row QDEC table maps `prev:curr → ±1`. The table has 8 valid transitions but the prose says "all 12 valid transitions." Re-count: 4 forward + 4 backward = 8 valid, 4 invalid (00↔11, 01↔10), 4 same-state = 16 total. Either say "8 valid transitions" or list the missing four.
- §111.3 The user-space decode latency claim "fails for a 10,000 ppr encoder spinning at 60 RPM (= 40 kHz edge rate)" is short. Add the derivation: "10,000 PPR × 4 edges/cycle × (60 RPM / 60 s) = 40,000 edges/s. At 50 µs latency per edge, the CPU is fully consumed by encoder IRQs alone."
- §111.4 The kernel `rotary_encoder` driver does **not** do 4× decoding; it reports one event per detent. Note this: "This driver is designed for human-operated knobs (detented mechanical encoders), not high-resolution servo feedback. It reports one event per detent step, not per quadrature edge."
- §111.5 The i.MX6ULL ENC peripheral — the chapter says mainline coverage "varies by kernel version." Be more concrete: "As of 6.6, mainline has no i.MX6ULL ENC driver. The NXP downstream BSP (`linux-imx`) ships one in `drivers/iio/counter/`. Check `make menuconfig → Counter Support → Freescale eQEP support` in your tree."
- §111.6 LS7366R sequence — the `0x88` and `0x60` opcodes are given but the *MDR0/MDR1 configuration* (which is what enables filters and 4× decode) is not shown. Add the typical init sequence: `WRITE_MDR0 (0x88, 0x03)` for 4× quadrature + free-running counter; `WRITE_MDR1 (0x90, 0x00)` for 32-bit mode, no flags.
- §111.8 The velocity loop uses fixed `Ki = 0.1` without scaling for sample rate. Add one sentence: "At a 100 Hz loop, integrator accumulates `err * 0.01` per cycle. Scale Ki by your loop period if you change the rate; otherwise the response changes shape."

---

## Ch112 — Stepper & DC motor drivers

### AI wording / sledgehammer / buzzwords
- > "Get these wrong and the result ranges from 'motor whines' to 'MOSFET explodes.'"
  - Cute but informal close. Rewrite: "Get these wrong and the result ranges from an audible whine to a destroyed MOSFET."
- > "**steppers need precise step-rate generation (PWM); DC motors need PWM + H-bridge + current feedback; BLDC needs commutation (rotor-position-aware switching of 3 half-bridges)**."
  - 30-word triplet with semicolons. Rewrite: "Steppers need precise step-rate generation, usually from a PWM. DC motors need a PWM and an H-bridge, with current feedback for control. BLDC motors need commutation — switching three half-bridges in sync with rotor position."
- > "Each must be timed within ~50 µs or torque ripple shows."
  - "Torque ripple shows" awkward. Rewrite: "Each commutation must hit within ~50 µs of the right rotor angle, or torque ripple becomes audible."
- > "Linux's interrupt jitter > 100 µs."
  - Equation-as-prose. Rewrite: "Linux interrupt jitter is typically > 100 µs."
- > "TMC2209 (Trinamic) is the modern silent stepper driver."
  - Marketing. Rewrite: "TMC2209 (Trinamic) is the current go-to silent stepper driver." *(Note: "go-to" is informal too — "common choice" is cleaner.)*
- > "Once configured, the motor is whisper-quiet — a 3D printer goes from 'rocket launch' to 'fridge hum.'"
  - Marketing simile. Rewrite: "Once configured, the motor is near-silent. A 3D printer with TMC2209 drivers is roughly the volume of a fridge fan."
- > "Klipper runs the motion planner on Linux and offloads the step-generation to an STM32 over USB serial; this is the canonical 'Linux + MCU' split for serious CNC."
  - "Canonical / serious CNC" is fan-prose. Rewrite: "Klipper runs the motion planner on Linux and offloads step generation to an STM32 over USB serial. This split is the dominant pattern for high-end CNC and 3D printing."

### ESL readability
- > "**Critical**: every driver has a 'current limit' you set with a trimpot (sense resistor + reference voltage)."
  - "**Critical**:" opener is overused (this part has 6+ bold "Critical:" markers across chapters). Vary: "Important: …" or just lead with the sentence.
- > "Don't rely on coil-color conventions — they're not standard."
  - Fine.
- > "Powering driver Vmot before logic Vcc."
  - Fragment in a pitfall list. Fine.
- > "For absolute-torque or smooth-low-RPM BLDC, you need FOC (Field-Oriented Control) which most engineers offload to a dedicated MCU (e.g., SimpleFOC on STM32) because Linux's jitter exceeds the 10 kHz current-loop budget."
  - 40 words, three parentheticals, one because-clause. Break: "For absolute torque control or smooth low-RPM behaviour, you need FOC (Field-Oriented Control). The current loop runs at 10 kHz or higher, which exceeds Linux's scheduling jitter. Most engineers offload FOC to a dedicated MCU — SimpleFOC on STM32 is the open-source standard."

### Needs more depth
- §112.2 Current limit setting — the formula "Vref = Imax × 5 × 0.1" is given without naming variables. Expand: "Vref = Imax × R_sense × 8 (for DRV8825) or × 5 (for A4988). For a 0.1 Ω sense resistor and 0.8 A target: 0.8 × 5 × 0.1 = 0.4 V. Check the driver datasheet for the exact constant."
- §112.4 TMC2209 UART CRC — "TMC's specific CRC8" — name the polynomial. The CRC8 used is `x^8 + x^2 + x + 1` (poly 0x07), MSB-first, init 0. Without that, the example code is unimplementable.
- §112.4 The `tmc_write` struct uses `uint8_t sync = 0x05` — this is a default member initialiser, which is a C++ feature, not C. In C you must initialise via `= { .sync = 0x05, ... }`. Fix the code or note it is pseudocode.
- §112.5 H-bridge shoot-through — the chapter mentions dead-time but does not give a typical value. Add: "Dead-time between high-side off and low-side on must exceed the FET turn-off time + 20 % margin. For typical TO-220 N-FETs, ~500 ns is safe; for fast logic-level FETs, 100 ns."
- §112.6 BLDC commutation table — the COMMUTATE_TBL has eight entries indexed by 3-bit Hall state. The mapping in the comment ("hall: 000 001 010 011 100 101 110 111" → "gate: inv 4 2 3 6 5 1 inv") is non-obvious. Add one sentence: "The mapping is rotor-angle-to-coil-pair. Halls 000 and 111 are invalid (all sensors off or on = sensor fault). The other six map to the six commutation states; the exact permutation depends on Hall sensor mounting and motor wind direction — swap any two entries if the motor runs backward."
- §112.6 The 2,333 commutations/s number assumes 14 magnetic poles (7 pole pairs). State the formula: "Commutations/s = (electrical RPM) / 60 × 6 steps/cycle = (mechanical RPM × pole pairs) / 60 × 6. For 10,000 RPM × 7 pole pairs = 70,000 electrical RPM, six steps per electrical revolution, so 7,000 commutations/s." (The text's 2,333 number appears off by 3× — verify with the formula.)
- §112.8 Pitfall "PWM frequency in motor's audible range" — the *cause* of the whine is left implicit. One sentence: "The motor's coils act as a speaker driven by the PWM ripple. Audible PWM (1–10 kHz) makes the motor whine in the same frequency. Move above 20 kHz to push the whine into ultrasonic, or use stealthChop which spreads the spectrum."

---

## Ch113 — WS2812 / SK6812 / APA102 addressable LEDs

### AI wording / sledgehammer / buzzwords
- > "**WS2812/SK6812 encode bits as pulse widths on a single wire: a '0' bit = 350 ns high + 800 ns low; a '1' bit = 800 ns high + 450 ns low; reset = 50+ µs low; one byte per channel × 3/4 channels × N LEDs all back-to-back**."
  - 50-word sledgehammer with four semicolons. Break: "WS2812 and SK6812 encode bits as pulse widths on a single wire. A '0' bit is 350 ns high followed by 800 ns low. A '1' bit is 800 ns high followed by 450 ns low. A reset is 50 µs or more of low. Each LED takes 24 bits (3 channels × 8) — or 32 bits for RGBW — and the whole strip is one back-to-back stream."
- > "Bit-banging from Linux user-space is hopeless (microsecond IRQ jitter > nanosecond timing budget)."
  - "Hopeless" judgmental. Rewrite: "Bit-banging from Linux user-space does not work. The IRQ jitter is microseconds; the WS2812 timing budget is hundreds of nanoseconds."
- > "**Don't ship this** — it's a demo trick, not a production approach. Use SPI + DMA."
  - "Demo trick" informal. Rewrite: "Do not ship this approach. It is useful as a demo only. Production designs should use SPI + DMA."
- > "The SPI + DMA trick — gospel for embedded Linux"
  - "Gospel" is religious slang. Rewrite: "The SPI + DMA pattern — the standard approach in embedded Linux."
- > "The timing-painless alternative"
  - "Painless" marketing. Rewrite: "APA102 — no timing constraints"
- > "The elephant in the room."
  - Cliché section title. Rewrite: "Power budgeting — the most-skipped detail."
- > "Quality varies wildly between batches."
  - "Wildly" informal. Rewrite: "Quality varies substantially between batches."

### ESL readability
- > "Encode each WS2812 bit as 4 SPI bits at 3.2 MHz (312.5 ns per SPI bit):"
  - Fine; keep.
- > "Wire MOSI → strip's DIN. Use a 74AHCT125 buffer to convert 3.3 V MOSI to 5 V logic level (WS2812 expects 0.7 × VDD = 3.5 V 'high' threshold; 3.3 V may or may not work depending on strip batch — buffer always)."
  - 40 words, one parenthetical with semicolon and dash. Break: "Wire MOSI to the strip's DIN. Always add a 74AHCT125 buffer to convert 3.3 V MOSI to 5 V. The WS2812 datasheet specifies VIH = 0.7 × VDD = 3.5 V; 3.3 V is below that. Some strip batches accept it; many do not. Buffer every time."
- > "The 5-bit global brightness is a separate PWM domain at ~700 Hz — useful for low-light, but it flickers in camera footage (frame-rate beating against the 700 Hz)."
  - "Frame-rate beating against" — technical jargon. Rewrite: "APA102's 5-bit global brightness is implemented by a separate PWM at about 700 Hz. It is useful for low-light effects, but on camera the 700 Hz beats against the camera's frame rate and shows flicker."
- > "Each LED at full white = 60 mA."
  - Equation-as-prose. Rewrite: "Each LED at full white draws about 60 mA."

### Needs more depth
- §113.3 The encoding LUT (`bit_lut[4] = { 0x88, 0x8E, 0xE8, 0xEE }`) is shown but the **SPI mode / endianness** required for it to work is not stated. Add: "The encoding assumes SPI mode 0, MSB-first byte order. On i.MX eCSPI, this is the default; on other SPI controllers verify with a scope before debugging mysterious 'wrong colour' bugs."
- §113.3 The trailing-low → free reset note is mentioned but the reader may not realise the SPI driver might *not* hold MOSI low after CS rises. Add a sentence: "Some SPI drivers leave MOSI high after the last bit. If you see the first LED of the *next* frame corrupted, your driver does this — work around it by appending 8 zero bytes to `spi_buf`."
- §113.6 APA102 end frame — the chapter says "32+ bits of ones (or zeros — both work)" but the **real** end-frame length is `N/2` bits where N is the number of LEDs. One sentence: "The end frame must be at least `N/2` bits long (where N is the LED count). The clock pulses pass through each LED's latch chain to commit the data. For 100 LEDs, 50 clock bits — 7 bytes of trailing 0xFF or 0x00 — is enough."
- §113.7 Gamma — the python list comprehension is given but the rounding (`+ 0.5`) and clamp are not explained. One sentence: "The `+ 0.5` rounds to nearest integer (Python's `int()` truncates). For very low values (`(1/255)^2.2 = 0.000007`) the result is 0, which is what you want — black truly black."
- §113.8 Power-injection diagram is missing; the reader is told to inject every 50–100 LEDs but the *wiring topology* is not shown. Add a simple ASCII diagram: PSU → wire to start, then taps at LED 50 and LED 100, all GNDs commoned.
- §113.10 Pitfall "Wrong color order" — list each chip's order in a tiny table for quick lookup, not in prose. "WS2812B = GRB. SK6812 = GRB or GRBW. APA102 = BGR. WS2811 = RGB." (The prose already lists most of this — just consolidate into one bullet.)

---

## Ch114 — Beepers, relays, SSRs

### AI wording / sledgehammer / buzzwords
- > "the **discrete actuators** that don't fit anywhere else but appear in every product"
  - "That don't fit anywhere else" is awkward. Rewrite: "the discrete actuators that fall outside the main subsystems but appear in every product."
- > "every product *does things* — beep on user action, switch a pump, turn on a heater, energize a solenoid valve, ring a bell."
  - Italics + bullet-as-prose. Rewrite: "Real products take physical actions: beep on user input, switch a pump, turn on a heater, drive a solenoid valve, ring a bell."
- > "Each actuator has a different electrical personality"
  - "Electrical personality" is a metaphor that does not translate well. Rewrite: "Each actuator has different electrical requirements"
- > "the engineering details that make the difference between 'the demo works' and 'we shipped this for 5 years and it never fails.'"
  - Long quoted-slang construction. Rewrite: "the engineering details that separate a demo from a five-year shipping product."
- > "**for inductive loads (relays, solenoids, motors) you MUST have a flyback diode; for AC loads you MUST have isolation; for zero-cross AC switching you MUST use a zero-cross SSR or you'll arc, generate harmonics, and burn contacts**"
  - 40-word triplet with three "MUSTs" in caps. Break: "Three non-negotiable rules for the actuators in this chapter. Inductive loads (relays, solenoids, motors) need a flyback diode. AC loads need isolation. Zero-cross AC switching needs a zero-cross SSR; non-zero-cross switching arcs, generates harmonics, and burns contacts."
- > "*Know what you're doing or hire someone who does.*"
  - Italic warning reads as a slogan. Rewrite: "Get a qualified electrician to review your design if you are not one."
- > "40 lines. Drop into systemd. From any phone with Home Assistant: tap 'Living Room Lamp' → MQTT → relay clicks → lamp on."
  - Arrow-chain showcase. Rewrite: "About 40 lines. Install as a systemd unit. Open Home Assistant on a phone, tap 'Living Room Lamp', and the relay clicks the lamp on via MQTT."

### ESL readability
- > "Live AC kills."
  - Two-word sentence. Effective for emphasis but reads abrupt. Keep.
- > "Treating 'off' SSR as 'isolated.'"
  - Quoted slang in a pitfall headline. Rewrite: "Treating an off SSR as electrically isolated."
- > "BJT and SoC are slowly killed by repeated back-EMF spikes."
  - "Slowly killed" personification. Rewrite: "Repeated back-EMF spikes will eventually damage the BJT and SoC."

### Needs more depth
- §114.2 Mechanical relay coil current — 30 mA at 12 V = 360 mW, not 150 mW as in §114.8 pitfall. Verify and unify the numbers across §114.2 and the pitfall list. (The relay's coil power depends on the part; quote a typical Songle SRD-05VDC: 5 V at 71 mA = 355 mW.)
- §114.3 The 10 kΩ pull-down — the chapter explains *why* (GPIO floats during boot) but not the **value choice**. One sentence: "10 kΩ is a compromise: low enough to overcome any leakage and pull the gate firmly to ground, high enough not to interfere with the GPIO drive when active. 1 kΩ to 100 kΩ all work; 10 kΩ is the default."
- §114.4 Zero-cross vs random-fire SSR — the chapter says "for inductive loads use random-fire SSR" but does not explain *why*. One paragraph: "A zero-cross SSR switches at the AC voltage zero-crossing. For resistive loads, this means current also starts at zero (no inrush). But an inductive load lags current by 90°: switching at voltage-zero is switching at current-peak. The arc on turn-off is severe. Random-fire SSRs (also called instant-on) switch whenever commanded — pair them with an external current-zero-cross detector for inductive switching."
- §114.5 GFCI/RCD — one sentence on the trip threshold would help: "Residential RCDs trip at ~30 mA imbalance between live and neutral. This will not stop you from feeling a shock, but it should stop you from being killed."
- §114.7 MQTT relay board — the example uses `paho.mqtt.client` and the older `gpiod` Python API (0.x). Modern Buildroot and Debian ship gpiod 2.x with a different API. Note the version: "This example uses python-gpiod 1.x. For gpiod 2.x (Bookworm and later), the API changed: use `gpiod.request_lines(...)` instead of `chip.get_line(...).request(...)`."
- §114.8 Pitfall "AC neutral switching" — add a one-line check the reader can use: "Use a non-contact voltage tester. Touch it to the load wire when the relay is OFF. If the tester chirps, you switched neutral. Rewire to switch live."
- §114.9 The "Going deeper" links — the chapter cross-references Ch 51A (watchdog) for safety but does not explain *why* a watchdog matters for relay control. One sentence in §114.5: "Pair every relay-driving application with a hardware watchdog (Ch 51A). If the controlling process hangs while a heater relay is closed, the load will run until manually disconnected. A 30-second watchdog with a fail-safe-open relay state prevents fires."

---

## Ch115 — Dual FEC + hosted Ethernet

### AI wording / sledgehammer / buzzwords
- > "**dual-MAC on one SoC means two PHYs, each with its own pin-mux + clock + interrupt; the kernel netdev model already isolates them so they look like two cards. The hard part is the bring-up:**"
  - 40 words, one semicolon, one closing colon. Break: "Dual-MAC on one SoC means two PHYs. Each needs its own pinmux, reference clock, and IRQ. The kernel netdev model already isolates the two MACs — they look like two NICs. The hard part is the bring-up."
- > "For SPI Ethernet: the W5500 is *hardware TCP/IP* (you talk to it at the socket layer over SPI, not as a netdev) which is alien on Linux"
  - "Alien on Linux" idiom. Rewrite: "The W5500 implements TCP/IP in hardware. You talk to it at the socket layer over SPI, not as a netdev. This does not fit the Linux netdev model."
- > "We cover all three patterns."
  - Fine.
- > "PMICs win on every axis"
  - "Win on every axis" is sports metaphor. Rewrite: "PMICs are better than discrete LDOs in every dimension"
- > "**Beautiful introspection — see exactly which consumer holds which rail enabled.**"
  - From Ch116 — flagged below.
- > "DM9051 is fine for a 3rd 'management interface' or a Modbus-TCP island bus. Don't expect it to handle real traffic."
  - "Real traffic" is dismissive. Rewrite: "DM9051 is adequate for a management interface or a low-rate Modbus-TCP island. It is not suitable for primary high-bandwidth traffic."
- > "Done. Your i.MX6ULL is a router."
  - "Done." then declarative. Rewrite: "That is the full router setup."
- > "Awkward on Linux."
  - Fragment. Rewrite: "This makes W5500 awkward to use on Linux."

### ESL readability
- > "**Practical Linux choice**: use W5500's sockets directly from user-space via SPI. Or — pick a different chip."
  - "Or — pick a different chip" is choppy. Rewrite: "The practical Linux approach: use W5500's sockets directly from user-space via SPI, or choose a different chip (DM9051, ENC28J60) that presents as a netdev."
- > "Critical: each PHY has a **strap-pin-set MDIO address** (typically 0, 1, 2, …). FEC1's PHY at address 0; FEC2's PHY at address 1. Both share the MDIO bus (MDC/MDIO can be shared on most designs), and FEC2 reads address-1's registers."
  - 45-word block with parenthetical and semicolon. Break: "Each PHY has an MDIO address set by strap pins (typically 0, 1, 2, …). Put FEC1's PHY at address 0 and FEC2's PHY at address 1. Both PHYs can share the same MDIO bus; the FEC reads the address that matches its `phy-handle` in the DT."
- > "The MDIO node is under FEC1 (one MDIO instance), with both PHYs as children. FEC2 references `ethphy1` via `phy-handle`."
  - Fine.

### Needs more depth
- §115.2 The MDIO bus is described as shared in prose but the DT example only shows it under `&fec1`. The reader should know that **only one FEC owns the MDIO controller**; the other accesses PHYs via `phy-handle` referencing the first FEC's MDIO subtree. State this: "Only one FEC owns the physical MDIO controller. The DT puts both PHY child nodes under that FEC's `mdio { }`. The second FEC's `phy-handle` points across to the PHY in the first FEC's MDIO tree. The kernel reads PHY registers through the owning FEC."
- §115.6 W5500 sockets — the chapter notes "out-of-tree drivers that wrap W5500 sockets as Linux `AF_INET` sockets" but does not link or name them. Add: "See `wiznet/W5500-EVB-Pico` for user-space examples, and the out-of-tree `kernel/drivers/net/w5x00` patches (never accepted upstream)."
- §115.7 DM9051 vs ENC28J60 throughput numbers (8 vs 3 Mbps) — show the math so the reader understands the limit: "DM9051 transfers one packet via two SPI transactions (TX = burst write to TX buffer; RX = burst read). At 20 MHz SPI and 1500-byte packets, raw byte time is 600 µs/packet → max ~13 Mbps. SPI overhead (CS settling, header bytes, IRQ servicing) drops effective throughput to ~8 Mbps."
- §115.8 FEC NAPI walk — the `napi_alloc_skb` + `memcpy` line is misleading. Modern fec_main.c uses `napi_build_skb` over DMA-mapped pages (zero-copy). Update the snippet or note: "The NAPI fast path in current kernels uses `napi_build_skb` with the DMA buffer directly, avoiding the memcpy shown here. The memcpy version is the simpler form for explanation."
- §115.10 Pitfall "Pinmux conflict" — be concrete about which pins to check. On i.MX6ULL: ENET2 RXD0/RXD1 share package pins with UART2 TX/RX and ECSPI3 SCK/MOSI on some packages. Name one or two specific conflicts so the reader knows where to look.
- §115.9 Lab 9 PTP — the chapter sets up `ptp4l` but does not explain what success looks like. Add expected output: "After `ptp4l -i eth0` is running on a master and slave, the slave's offset converges to < 1 µs within a minute. Verify with `pmc -u -b 0 'GET CURRENT_DATA_SET'`."

---

## Ch116 — PMICs and the regulator framework

### AI wording / sledgehammer / buzzwords
- > "Get the **boot-sequence races** wrong (kernel starts the FEC before its PHY's 1.8 V rail is stable → PHY doesn't probe), and you'll chase ghost bugs forever."
  - "Chase ghost bugs forever" is fan-prose. Rewrite: "If you get the boot-sequence wrong — for example the kernel starts the FEC before its PHY's 1.8 V rail is stable — you will see PHY probe failures that look random."
- > "PMICs win on every axis once your board has >3 rails or needs real power management."
  - "Win on every axis / real power management" — both opinion-flavoured. Rewrite: "PMICs are better in every dimension once a board has more than three rails or needs runtime power management."
- > "Beautiful introspection — see exactly which consumer holds which rail enabled."
  - "Beautiful" is marketing. Rewrite: "The regulator summary makes the power tree visible: you can see exactly which consumer keeps each rail enabled."
- > "Without PMIC: each rail must be enabled by a separate GPIO with separate timing; the suspend driver becomes ugly. With PMIC: 1 line of code."
  - "Becomes ugly" + "1 line of code" — slogan pair. Rewrite: "Without a PMIC, each rail needs its own GPIO with its own timing; the suspend driver grows complex. With a PMIC, suspend is one I²C transaction."
- > "**the regulator framework treats every rail as a 'supply'; drivers declare their consumer-supply relationships in DT; the kernel computes the power-on order and ensures voltages are stable before any consumer probes**"
  - 40 words, three semicolons. Break: "The regulator framework treats every rail as a 'supply'. Drivers declare their consumer-supply relationship in the DT. The kernel computes the power-on order from the dependency graph, and waits for each rail to stabilise before letting consumers probe."
- > "This is why DVFS exists."
  - Fine.
- > "the silent killer"
  - Section heading "Power-up sequencing — the silent killer". Cliché. Rewrite: "Power-up sequencing — the most subtle bring-up trap."

### ESL readability
- > "ROHM BD71850MWV (compact, integrated for i.MX6/8 cores)."
  - Fine.
- > "Discrete remains common only for ultra-low-cost designs or where you want zero-quiescent on a battery rail (some PMICs have annoying 50 µA quiescent)."
  - "Annoying" is judgmental. Rewrite: "Discrete LDOs remain common only for the cheapest designs, or for battery rails where the PMIC's ~50 µA quiescent is too high."
- > "Linux runtime: the regulator framework's `regulator_enable()` walks dependencies."
  - "Walks dependencies" jargon for ESL. Rewrite: "At runtime, `regulator_enable()` walks the supply dependency graph and powers parent supplies first."

### Needs more depth
- §116.2 PCA9450 voltage encoding — `Vout = 0.6 + N × 0.025 V` is "typical." Be precise: "PCA9450 BUCK1: code = round((Vout − 0.60) / 0.025), valid 0..63 (0.60 V to 2.175 V). Different bucks have different formulas; check the datasheet's Table 27."
- §116.3 The "consumer probes after supply enabled" claim is the heart of the chapter and deserves one more sentence: "If a consumer driver's `probe()` is called before its supply is registered, the framework returns `-EPROBE_DEFER`. The kernel retries the probe later, after the missing supply appears. This is why the order of drivers loading does not matter — the deferral mechanism handles it."
- §116.4 Power-up sequencing list — the constraints (≤10 ms, ≤100 ms) are taken from the i.MX6ULL reference manual. Cite the source explicitly: "These timing limits are from the i.MX6ULL Reference Manual, Chapter 11 (Power Supply Strategy), Table 11-3."
- §116.5 DVFS — the power saving math says "Static (leakage) power ∝ V; ~10 % reduction." This is roughly right at 27 °C but leakage grows exponentially with temperature. One sentence: "Leakage scales linearly with V at constant temperature but doubles for each ~10 °C rise. Real-world DVFS gains are larger on a hot device than on a cool one."
- §116.7 The "don't write registers directly" warning is the right message, but the example does exactly that. Add a more explicit footnote: "This code is for one-time bring-up exploration only. In a production system, even reading these registers from user-space races with the regulator framework's runtime updates. Use `cat /sys/class/regulator/regulator.N/microvolts` instead."
- §116.9 Pitfall "OPP table wrong voltage" — be specific about how to find the right values: "The authoritative source is the i.MX6ULL Data Sheet, Table 12 (Operating Ranges). Each frequency has a Vmin; the OPP table must equal or exceed it. The NXP BSP's `imx6ull.dtsi` `cpu_opp_table` is correct by construction."
- §116.9 Pitfall "Ramp rate too fast" — name the symptom: "Symptom of too-fast ramp: a regulator-clocked consumer (DDR, PLL) glitches on every voltage change. Reduce `regulator-ramp-delay` (units are µV/µs — counterintuitively, *higher* number = slower because it means more µV per µs of allowed change)." (Verify: `regulator-ramp-delay` in DT is documented as "the soft-start ramp rate in µV/s"; double-check units.)

---

## Ch117 — External RTC

### AI wording / sledgehammer / buzzwords
- > "**the RTC chip is a 32.768 kHz oscillator + counters + I²C; the kernel `rtc-*` driver exposes it as `/dev/rtcN`; `hwclock` syncs between hardware clock and system clock; chrony or systemd-timesyncd updates the system clock from NTP/PPS and writes back to the RTC**"
  - 50-word block with five semicolons. Break: "The RTC chip is a 32.768 kHz oscillator plus counters, accessed over I²C. The kernel `rtc-*` driver exposes it as `/dev/rtcN`. `hwclock` syncs between the hardware clock and the system clock. `chrony` (or `systemd-timesyncd`) keeps the system clock disciplined from NTP or PPS, and writes the corrected time back to the RTC."
- > "Alarm interrupts let the RTC wake the SoC from suspend — but the alarm pin must be wired to a real GPIO that's mappable to a wake-up source in the kernel, which is the most-skipped detail."
  - 30-word with em-dash and trailing clause. Rewrite: "Alarm interrupts let the RTC wake the SoC from suspend. The alarm pin must be wired to a GPIO that the kernel can use as a wake source. This wiring requirement is the most-skipped detail in RTC bring-up."
- > "The external RTC fix: $0.50 chip + $0.30 coin cell on the I²C bus = the device knows the right time on every cold boot"
  - Equation-as-prose. Rewrite: "The external RTC fix: a $0.50 chip plus a $0.30 coin cell on the I²C bus. The device knows the correct time on every cold boot, runs scheduled alarms even when Linux is off, and stays calibrated for years."
- > "the high-end favorite"
  - Marketing. Rewrite: "the highest-accuracy popular choice"
- > "**End of Part VII — Device Cookbook (Ch 64–117, 54 chapters).**" closing paragraph claims "Every common device class has been covered" and "every external chip an i.MX6ULL product is likely to integrate is in this Part."
  - "Every X" double absolute. Soften: "Part VII covers most device classes you will integrate on an i.MX6ULL product: from QSPI flash to a GPS-disciplined time server."

### ESL readability
- > "The DS3231's built-in thermometer is a neat freebie — drives the TCXO temperature compensation but is also a usable ±3 °C ambient sensor."
  - "Neat freebie" + em-dash glue. Rewrite: "The DS3231's built-in thermometer is a useful bonus. It drives the TCXO temperature compensation internally and can also be read as a ±3 °C ambient sensor."
- > "battery only protects across short main outages"
  - "Short main outages" — the word "main" is ambiguous (could be "mains" power, or "primary"). Clarify: "The CR2032 only protects against short *main supply* outages. If both the main supply and the battery are removed at the same time, the RTC loses time."
- > "MPU-6050 IMU also defaults to 0x68. Bus conflict. Reroute one to a different address (DS3231 doesn't reconfigure; MPU-6050 has AD0 strap)."
  - Three sentence fragments. Rewrite: "The MPU-6050 IMU also defaults to address 0x68 — bus conflict. The DS3231 address is fixed. Strap the MPU-6050's AD0 pin to move it to 0x69."
- > "Time zone: hwclock can store the RTC in UTC or local time. UTC is the only sensible choice — `/etc/adjtime` records the policy."
  - "Only sensible choice" is opinion. Rewrite: "hwclock can store the RTC in UTC or local time. UTC is strongly recommended — local time breaks across DST transitions. `/etc/adjtime` records which is in use."

### Needs more depth
- §117.3 The `interrupts` line `interrupts = <23 IRQ_TYPE_EDGE_FALLING>;` appears alongside `interrupts-extended = <&gpio4 23 IRQ_TYPE_EDGE_FALLING>;` — these are duplicate (or conflicting) bindings. One sentence to resolve: "Use `interrupts-extended` for cross-controller IRQ references; the plain `interrupts` form is only valid when the parent specifies `interrupt-parent`. The duplicate here is an error; pick one."
- §117.4 `/etc/adjtime` policy — name the three columns: "The file has three lines: drift rate in seconds/day, last calibration time, and either `UTC` or `LOCAL`. hwclock reads all three on each invocation."
- §117.5 `rtcwake` — show the wake source verification: "After `rtcwake -m mem -s 30`, the next `dmesg | grep -i wakeup` should show `PM: suspend exit` with the cause. If the cause is anything other than the RTC alarm, your wake source is misconfigured."
- §117.5 The `tm_min += 5; if (tm_min >= 60) tm_min -= 60, tm_hour++;` adjustment is wrong if the resulting `tm_hour` ≥ 24, or if the day rolls. Use `mktime + timegm` properly: "Computing an alarm time by adjusting `tm_*` fields directly is error-prone. Convert to `time_t` with `timegm`, add seconds, convert back with `gmtime_r`."
- §117.7 chrony `rtcsync` — write-back is every 11 minutes, but only **if** the system clock is well-disciplined. One sentence: "chrony only writes the RTC when it considers the system clock 'trusted' (offset stable for several minutes after NTP convergence). On a freshly-booted, ill-disciplined system, the first RTC write may be delayed by 10–20 minutes."
- §117.9 Lab 6 daily scheduled task — the implementation is sketched but the actual `rtcwake` invocation with a wall-clock target is missing. Add: "Use `rtcwake -m mem -t $(date -d 'tomorrow 06:00' +%s)`. This sets the alarm to the absolute time 06:00 tomorrow."
- §117.10 Pitfall "OSF not cleared" — explain what OSF is: "OSF (Oscillator Stop Flag) is set when the DS3231 detects an oscillator stop (typically VCC and VBAT both lost). After replacing the battery, clear OSF by writing 0 to bit 7 of the STATUS register (0x0F). Until cleared, alarms are inhibited."

---








