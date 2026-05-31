# Part VIIa — Style/ESL Review (Ch 64–81 Cookbook)

## Cross-cutting patterns

- **Em-dash chaining is the dominant tic.** Every chapter uses " — " two or three times per paragraph to glue clauses. Often this should be a period. Examples flagged below per chapter; the pattern is everywhere.
- **Semicolons gluing two clauses.** Less than Parts II–V but still common, particularly in `Pitfalls` bullets ("X happens; Y is the fix"). Period reads better for an ESL reader.
- **"Not X — Y" / "Not X. It's Y." sledgehammer.** Recurring in chapter intros, "why" boxes, and physics explanations (Ch 69 "wrong by design", Ch 71 "this isn't X. It's Y.").
- **AI buzzwords that survived past Part VI**: `internalise`, `mechanical` (used as praise), `canonical`, `idiomatic`, `magic`, `magical`, `proper`, `genuinely`, `essentially`, `effectively`. Several chapters also use `traceable`, `non-trivial`, `radically different`, `clarifying`. Cull on a pass.
- **Cliché phrases.** "the workhorse bus" (Ch 64/65/70), "the right starting point" (Ch 67), "the magic" / "where the magic happens" (Ch 67, 73, 78), "a masterclass", "the heart of the framework" (Ch 64). All marketing-flavor.
- **Royal "we / let's"** still leaks in: "Let's prove we understand…" (Ch 65, 67), "Let's walk…" (Ch 64), "we'll write" (most chapters). Replace half with an imperative or just drop.
- **Triplet rhythm in lab/pitfall bullets.** "X. Y. Z." constructs (e.g. Ch 67 "you understand the chip"; Ch 76 "Measure, log, alert."). Once per chapter is fine; multiple is AI cadence.
- **"That's it." / "That's the whole protocol." / "That's the whole game."** Used at the end of subsections all over Ch 64–69. Pick one per chapter, drop the rest.
- **Editorialising tone slips in** ("wrong by design", "honest pedagogy", "marketing", "placebo", "fan-prose", "honestly", "don't experiment with…"). Some is fine for personality but it appears too often and reads opinionated rather than instructional. Cut where the technical point stands without it.
- **Bullet-as-prose sentences.** Particularly in intros ("Why" boxes) — long sentences listing 4–6 items separated by commas. Break or bullet.
- **"Build, load, exercise:" / "Build, load, test:" header.** Repeated verbatim in every from-scratch chapter (Ch 64, 65, 67, 68, 69, 70…). Vary: "Build and load." / "Bring it up." / "Try it."

## Ch64 — QSPI NOR flash

### AI wording / sledgehammer / buzzwords
- > "The mainline driver wraps this in regmap-like abstractions and parameter databases, but the wire protocol is dead simple."
  - "Dead simple" is informal English. Rewrite: "The mainline driver wraps this in abstractions and a parameter database, but the wire protocol itself is small."
- > "That's basically the entire interface."
  - "Basically" + cliché. Rewrite: "That is the full interface."
- > "If you ever encounter a chip that *isn't* in the database, you'll know how to add it (or replace the framework entirely with 200 lines)."
  - Boastful. Rewrite: "If you encounter a chip that is not in the database, you can add an entry — or replace the framework with about 200 lines of your own."
- > "**a NOR flash is a state machine driven by single-byte commands**. `0x9F` = read JEDEC ID. ..."
  - The triplet/quartet of `0x..` = X lines reads as a slogan. Keep the lead sentence; collapse the examples into a single line: "Common commands: `0x9F` JEDEC ID, `0x06` write-enable, `0x20` sector erase, `0x02` page program, `0x03` read."
- > "This is the heart of the framework: a polling loop that yields the CPU between checks."
  - "Heart of the framework" is cliché. Rewrite: "This polling loop is what makes the framework work on Linux: it yields the CPU between checks."
- > "Pedagogically, ordinary SPI is the right choice for this from-scratch driver."
  - "Pedagogically" is academic. Rewrite: "For this teaching example, ordinary SPI is the right choice."

### ESL readability
- > "QSPI NOR fits when storage need is < 32 MB, you want fast/deterministic boot, you want a soldered theft-resistant device, and you're not storing much user data."
  - 33-word bullet-as-prose, mixed comma grammar. Break: "QSPI NOR fits when your storage need is under 32 MB, when you want a fast, deterministic boot, when you want a soldered device that resists theft, and when there is little user data to store."
- > "(so they're HIGH while still in 1-bit / single-IO mode at boot — quad mode hasn't been enabled yet, IO2 acts as /WP, IO3 as /HOLD; both active-low, so pulled HIGH means 'not asserted')."
  - 38-word parenthetical with two em-dashes and a semicolon. Break out of the parenthesis: "These pull-ups keep IO2 and IO3 HIGH while the chip is still in single-IO mode at boot. Quad mode is not enabled yet, so IO2 acts as /WP and IO3 as /HOLD. Both are active-low, so 'HIGH' means 'not asserted.'"
- > "The page-boundary clamp in step 1 is critical — NOR chips wrap *within a page*: programming with an address of 0xFE and 4 bytes of data writes the last 2 bytes at 0xFE, 0xFF, then the next 2 bytes back at 0x00 and 0x01. Silent corruption."
  - Good content but dense. Rewrite: "Step 1's page-boundary clamp matters because NOR chips wrap *within a page*. If you program at address 0xFE with 4 bytes of data, the last 2 bytes go to 0xFE and 0xFF, then the next 2 bytes wrap back to 0x00 and 0x01 of the same page. Silent corruption."

### Needs more depth
- §64.6 mentions `spi_mem_op` and `spi_mem_exec_op` as "translating into whatever the underlying SPI/QSPI controller wants" — but the reader has not seen `spi_mem` before. One paragraph: `spi_mem` is the kernel's abstraction for "memory-mapped-style flash commands" (cmd + addr + dummy + data). On a plain SPI controller it falls through to `spi_message`s; on a dedicated QSPI controller it programs the controller's LUT. The mainline `spi-nor` is written against `spi_mem` so a single driver works on both.
- §64.8 MTD partitioning interacts with the U-Boot environment partition, but the chapter never explains *what U-Boot does with these partitions at boot* before showing the partition table. Add one sentence linking `partition@100000` ("u-boot-env") to the `fw_setenv` step in §64.10: "U-Boot reads its environment from this region at startup via raw `sf read`; Linux uses `fw_setenv` to update it from user-space. Both sides must agree on the offset — that is what `fw_env.config` is for."
- §64.9 XIP: "instruction-cache misses are expensive" is named but the *why* is not explained for an MCU reader who has seen XIP on Cortex-M before. One sentence: "On Cortex-A, an I-cache miss that hits QSPI stalls the pipeline for the chip's read latency — tens of ns at 80 MHz QSPI, versus single-digit ns from DDR3. A loop that misses cache repeatedly is the bottleneck."

## Ch65 — I²C / SPI EEPROM

### AI wording / sledgehammer / buzzwords
- > "The protocol is *trivial*; writing your own driver in 100 lines is genuinely possible and clarifying."
  - "Genuinely", "clarifying" both AI-flavored; semicolon. Rewrite: "The protocol is small. Writing your own driver in 100 lines is realistic and worth the time."
- > "Master those and the rest is byte arithmetic."
  - "Master those" is consultant-speak. Rewrite: "Get those two right and the rest is byte arithmetic."
- > "EEPROM is the 'metadata anchor' of an embedded board"
  - "Metadata anchor" is a coined phrase. Rewrite: "EEPROM is the place embedded boards store small permanent facts about themselves — MAC address, board serial, calibration."
- > "After this chapter the kernel's `at24.c` will look like ordinary plumbing, not magic."
  - "Magic" again. Rewrite: "After this chapter the kernel's `at24.c` will read as ordinary code, not a mystery."
- > "That's the whole driver. ~50 lines of meaningful code; the rest is parameter tables, DT plumbing, and edge-case handling…"
  - "That's the whole driver" + semicolon. Rewrite: "That is the whole driver. Around 50 lines of real code. The rest is parameter tables, DT plumbing, and edge cases (multi-address chips, write-protect GPIOs)."
- > "Same chip, more features."
  - Fragment-as-tagline. Rewrite: "Same chip, more features available." Or drop entirely.
- > "the production pattern — own it."
  - "Own it" is idiomatic American English. Rewrite: "this is the production pattern — get familiar with it." Or just: "This is the production pattern."

### ESL readability
- > "Then the chip enters **internal write cycle** for ~5 ms. During this time it **NACKs every I²C transaction**. The host polls (issues address-write, sees NACK, retries) until it gets an ACK — that's 'ACK polling,' the standard way to know the write finished."
  - "ACK polling" is named at the end of a 60-word block. Rewrite leading with the name: "After the data bytes, the chip starts an *internal write cycle* of about 5 ms. During this time it NACKs every I²C transaction. The host keeps issuing address-write transactions; each NACK means 'still writing,' and the first ACK means 'done.' This is called **ACK polling**."
- > "Multiple EEPROMs on one bus. Strap each chip's A0/A1/A2 differently to give unique addresses (0x50–0x57). If two chips share an address, neither responds correctly."
  - Three sentences fine; keep.
- > "Reads return all-0xFF forever; writes silently fail. Tie WP low, or wire to a GPIO with default-low."
  - Semicolon + idiom ("default-low"). Rewrite: "Reads return all-0xFF and writes silently fail. Tie WP low, or wire it to a GPIO that defaults to low."

### Needs more depth
- §65.4 page-boundary explanation: the bytes "indexed 0x08" wrap back to "0x00" — but the *underlying mechanism* (each chip's write buffer is page-sized; the chip's address counter is only `log2(page_size)` bits wide) is not stated. One sentence: "The chip latches incoming bytes into a one-page RAM buffer; the buffer's address pointer is only as wide as `log2(page_size)` bits. After the last page byte, the pointer rolls over inside the page, not into the next page. The full byte address is only loaded once at the start of the transaction."
- §65.7 the **nvmem** subsystem is introduced as "an nvmem provider" without saying *what nvmem is*. Add a one-paragraph aside: "nvmem (Non-Volatile MEMory) is a tiny subsystem that lets one driver (the EEPROM, in this case) publish typed byte-regions called 'cells', and another driver (the Ethernet MAC) consume them at probe. The DT `nvmem-cells` / `nvmem-cell-names` properties on the consumer side wire them together. This decouples the MAC driver from where the MAC address physically lives — could be EEPROM, eFuse, or an OTP region."

## Ch66 — SD card and eMMC

### AI wording / sledgehammer / buzzwords
- > "**Writing one from scratch in a chapter is not honest pedagogy.**"
  - "Honest pedagogy" is academic. Rewrite: "Writing one from scratch in a single chapter is not realistic."
- > "What we *can* do — and what's productive — is **trace a single `read()` through the layers**"
  - Em-dash insertion + "productive" feels like a slide. Rewrite: "What we *can* do is trace a single `read()` through the layers."
- > "Dooms you to field failures or wasted engineering."
  - Overdramatic. Rewrite: "Picking wrong leads to field failures or wasted engineering effort."
- > "SD cards die. Often. In ways that surprise engineers used to flash chips:"
  - Triplet-fragment style, very common AI cadence. Rewrite: "SD cards fail often, in ways that surprise engineers used to flash chips."
- > "Make the engineering call early."
  - Consultant tagline. Rewrite: "Decide between SD and eMMC at schematic time, not after the first field unit fails."
- > "**That's the abstraction**."
  - Slogan. Rewrite: "That is the abstraction." Or drop and keep the next sentence.
- > "(soldered eMMC at HS200, 5-year industrial life)"
  - "5-year industrial life" is marketing claim and bare. Rewrite: "rated for 5+ years of continuous service in industrial-grade parts."

### ESL readability
- > "Card-detect ignored; system keeps trying after card removal."
  - Telegraphic. Rewrite: "The card-detect signal is ignored, so the system keeps trying to talk to the slot after the card is removed."
- > "eMMC `fsync` does a real flush-to-flash cycle (10s–100s of ms). If your app fsyncs after every write, performance tanks. Batch writes."
  - "Tanks" + fragment. Rewrite: "eMMC `fsync` does a real flush-to-flash, which takes 10 to 100 ms. If your application calls `fsync` after every write, throughput drops sharply. Batch your writes."
- > "A power loss can corrupt a *bigger area than you wrote*. Industrial eMMCs (Micron e.MMC, KIOXIA) have PFAIL protection; consumer ones don't."
  - Semicolon. Rewrite: "A power loss can corrupt a wider area than you actually wrote. Industrial eMMCs (Micron, KIOXIA) include PFAIL protection. Consumer parts do not."

### Needs more depth
- §66.3 speed-mode table mentions "UHS-I voltage switch" for SDR104 without explaining it. One paragraph: "Before SDR104, the bus runs at 3.3 V. To enter SDR104 the host issues CMD11 (SWITCH_VOLTAGE), the card pulls DAT0 low to confirm, the host re-clocks at 1.8 V on the VQMMC rail. The `vqmmc-supply` regulator must be able to make this 3.3 V → 1.8 V switch under software control; a fixed 3.3 V regulator leaves the controller stuck at slower modes."
- §66.4 the `pinctrl-1` / `pinctrl-2` mechanism is mentioned ("different pin slew rates at higher speeds") but the *Linux concept of multiple pinctrl states* is hidden. For someone who has only seen `pinctrl-0` it deserves one sentence: "`pinctrl-names = \"default\", \"state_100mhz\", \"state_200mhz\"` defines three named pin states. The driver switches between them via `pinctrl_select_state(p, state)` as the bus clock changes; faster modes need lower drive strength and tighter slew." (Then cross-link to Ch 44.)
- §66.7 EXT_CSD output reads as if `mmc extcsd read` is built in. Add one sentence: "`mmc` is from the `mmc-utils` package — not installed by default on most distros. Build from `git://git.kernel.org/pub/scm/linux/kernel/git/cjb/mmc-utils.git`."

## Ch67 — Temperature / humidity / pressure

### AI wording / sledgehammer / buzzwords
- > "By writing one from scratch you internalise both the chip and IIO."
  - "Internalise" again. Rewrite: "Writing one from scratch teaches you both the chip and IIO at the same time."
- > "Understanding this — and that the formula is in the *driver*, not the *chip* — is the whole game."
  - "The whole game" cliché. Rewrite: "Understanding this — that the compensation formula lives in the *driver*, not the *chip* — is the key insight."
- > "It's *not* an approximation we made up. It's lifted byte-for-byte from the Bosch datasheet's pseudocode, page 25."
  - Defensive tone. Rewrite: "These formulas are not approximations. They are lifted byte-for-byte from page 25 of the BME280 datasheet."
- > "Those are framework concerns, not 'do you understand the chip' concerns. You understand the chip."
  - Two-fragment slogan ending. Rewrite: "Those are framework features, not chip-understanding features. The chip is what we set out to teach."
- > "A working IIO driver that exposes temp + humidity + pressure"
  - Triplet-as-spec; fine, keep.
- > "Sensirion's philosophy: less state in the chip, more in the host."
  - "Philosophy" is grand. Rewrite: "Sensirion's design choice: keep state in the host, not the chip."
- > "The 'everyone's hobbyist humidity sensor.'"
  - Idiomatic English. Rewrite: "The default cheap humidity sensor on hobbyist boards."

### ESL readability
- > "User-space reads `/sys/bus/iio/devices/iio:device0/in_temp_input` → driver issues 'forced measurement,' waits ~8 ms, reads the 8 raw bytes, applies the compensation formula, returns '23420' (mC)."
  - Bullet-as-prose with arrow notation. Break: "When user-space reads `/sys/bus/iio/devices/iio:device0/in_temp_input`, the driver issues a 'forced measurement,' waits about 8 ms, reads the 8 raw bytes, applies the compensation formula, and returns `23420` (millidegrees Celsius)."
- > "The H and T raw values are 20-bit, packed across 5 bytes with a nibble split at byte 3."
  - "Nibble split" is jargon-y for ESL. Rewrite: "The H and T raw values are 20 bits each. They share a middle byte: the top 4 bits go to H, the bottom 4 bits to T."
- > "Ten minutes of work once you've done BME280."
  - Marketing claim. Rewrite: "After the BME280 driver, converting to AHT20 is mostly mechanical command-table substitution."

### Needs more depth
- §67.4 mentions "regmap" prominently as the abstraction but the BME280 mainline glue (`bmp280-i2c.c`) creating a regmap is treated as a one-liner. For the reader to understand why this is a win, one sentence: "The same `bmp280_common_probe` is called from `bmp280-spi.c` with a regmap built via `devm_regmap_init_spi` instead — and not a single line in the chip logic changes. That is the bus-decoupling regmap buys you."
- §67.4 compensation formulas with `t_fine` — the *reason* `t_fine` is a 32-bit "intermediate temperature value" tied to pressure/humidity compensation is mathematical (temperature affects gas density which affects pressure, and the saturation-vapor curve depends on T). One sentence helps the reader trust the cross-coupling: "The chip's sensors are physically affected by die temperature, so the pressure and humidity formulas use the temperature result via the shared `t_fine` intermediate. Always compute temperature first."
- §67.6 SHT3x "clock-stretching" appears once in the protocol table; no explanation of what clock-stretching is for an MCU reader who only knows fast I²C. One sentence: "Clock stretching is the slave holding SCL low to make the master wait — typically because the slave is busy with an internal measurement. The master's controller must tolerate SCL low for tens of ms. Some controllers time out; i.MX6ULL handles it correctly."

## Ch68 — Light & color sensors

### AI wording / sledgehammer / buzzwords
- > "After this chapter you can pick a sensor by understanding the trade-offs, and write your own driver for any of them."
  - Marketing. Rewrite: "After this chapter you can pick a sensor by its trade-offs, and write a driver for any of them."
- > "Internalise this hierarchy and you'll never trust an 'eCO₂' reading on its face again."
  - "Internalise" + idiom ("on its face"). Rewrite: "Once you see this hierarchy, you stop trusting 'eCO₂' as if it were a CO₂ reading." (This sentence is actually from Ch 69 — flag in that chapter; remove the duplicate critique here.)
- > "Light is non-trivial."
  - "Non-trivial" is overused. Rewrite: "Measuring light is harder than it looks."
- > "**Integration time governs both noise and saturation**."
  - Bold-as-slogan. Keep but soften the sentence around it: "Integration time controls both noise floor and saturation point."
- > "The 'right' integration time depends on what you're trying to measure."
  - Hedge ("the right"). Rewrite: "Pick integration time for the range you care about."
- > "The user never sees the lambdaweighting; it's all hidden."
  - Typo ("lambdaweighting") *and* semicolon *and* "magic" subtext. Rewrite: "The user never sees the wavelength weighting; the driver does it. Just `cat in_illuminance_input` gives lux."
- > "(BH1750 is unusual: it has no register map.) ... That's it. Two bytes on the wire, one division."
  - "That's it" + fragment. Rewrite: "Two bytes on the wire and one division — that is the whole protocol."

### ESL readability
- > "Different sensors solve this differently — BH1750 uses an analog filter, TSL2561 measures broad+IR and subtracts, VEML7700 uses an integrated correction."
  - Bullet-as-prose with three options. Bullet for real or rewrite: "Different sensors solve this differently. BH1750 uses an analog filter. TSL2561 measures a broadband channel and an IR channel and subtracts. VEML7700 uses an integrated correction."
- > "**Optical filter** (BH1750, VEML7700, TCS34725 clear channel): a colored glass cover on the die that approximates the photopic curve. Cheap, fixed."
  - Fragment ("Cheap, fixed.") for emphasis is fine once; this construction repeats three times in this list. Vary the third one.
- > "Bouncing between integration times causes flicker in the lux reading."
  - Idiomatic ("bouncing"). Rewrite: "Switching back and forth between integration times causes flicker in the reported lux."

### Needs more depth
- §68.2 the **CIE photopic curve** is named but never shown or described in numbers. A 4-line table — wavelength vs. relative response at 400 / 450 / 500 / 555 / 600 / 650 / 700 nm — anchors the abstract idea. ESL reader will benefit hugely.
- §68.4 the BH1750 mainline driver exposes raw + scale, not `_processed`. For an ESL reader new to IIO, the *difference* between `_raw + _scale + _offset` and `_processed` is worth one explicit sentence: "`_raw` is the chip's count. `_scale` is the conversion factor. `_processed = raw * scale + offset`, already in the unit named by the channel. Drivers expose one or the other; mainline `bh1750` exposes raw+scale (more flexible), the from-scratch one exposes processed (simpler)." Then mention `_offset` for completeness.

## Ch69 — Air quality / gas / PM

### AI wording / sledgehammer / buzzwords
- > "**NDIR is physics; metal-oxide is correlation; laser scatter is counting**."
  - Triplet with semicolons. Strong slogan but reads AI. Rewrite: "NDIR measures physics directly. Metal-oxide infers from a correlation. Laser scatter counts particles. Three very different things wearing the label 'air quality sensor.'"
- > "Internalise this hierarchy and you'll never trust an 'eCO₂' reading on its face again."
  - Already flagged: "internalise" + idiomatic "on its face". Rewrite: "Once you see this hierarchy, an 'eCO₂' reading reads as 'rough VOC trend that someone scaled into CO₂-looking numbers,' not as a CO₂ measurement."
- > "Expensive but honest."
  - Editorialising fragment. Rewrite: "Expensive but accurate."
- > "If your product advertises 'CO₂ sensor,' use SCD30, not CCS811."
  - Fine; keep. Useful concrete rule.
- > "Don't claim 'this is CO₂.'"
  - Fragment as caution. Rewrite: "Don't label CCS811 output as 'CO₂' to end users."
- > "Wrong by design when you have non-human VOC sources (cooking, cleaning, painting)."
  - "Wrong by design" is editorial. Rewrite: "Inaccurate by construction whenever a VOC source other than human breath is present — cooking, cleaning, painting all corrupt it."
- > "The whole protocol is a state machine over a UART stream."
  - Trailing slogan. Trim or keep as one sentence per chapter — already there in 64, 65.

### ESL readability
- > "Most products have a 'fan power' pin; cycle it."
  - "Cycle it" idiom + semicolon. Rewrite: "Most products bring out a 'fan power' pin. Toggle it off and on to reset the fan."
- > "(Skipping the CRC bytes at indices 2 and 5; check them and retry on mismatch.)"
  - Parenthetical instruction with semicolon. Rewrite: "Indices 2 and 5 are CRC bytes — skipped here for the value extraction, but check them and retry on mismatch."
- > "Particulate matter ... is calibrated against standard EPA reference. Use that one. The 'standard' column is uncalibrated."
  - Two-sentence pitfall with confusing naming ("standard" column is the uncalibrated one). Add a clarifying parenthetical: "In the frame, the columns labelled *atmospheric* are calibrated against EPA reference — use those. The columns labelled *standard* are uncalibrated (Plantower's chosen naming, not a quality statement)."

### Needs more depth
- §69.3 the chapter mentions "**I²C clock stretching**" with a one-line warning about Raspberry Pi. The MCU reader knows clock stretching as "slave drags SCL low" but may not know how the kernel host driver actually handles it. One sentence: "On i.MX6ULL the uSDHC's I²C blocks support clock-stretching natively — the controller just waits while SCL is held low, no driver intervention needed. The Pi's BCM2835 had a hardware bug where clock-stretching past a few µs broke; Sensirion's SCD30 stretches for tens of ms, which is why this is a recurring gotcha."
- §69.5 **SerDev** appears as a critical concept (the whole from-scratch driver depends on it) and is explained at the end of the chapter (§69.5 last subsection). Move that explanation *before* the code, not after — the reader needs to know what `serdev_device_driver` and `receive_buf` are before reading 100 lines that use them.
- §69.4 CCS811's "ENV_DATA register" cross-coupling with BME280 is mentioned ("feed it temperature and humidity from your BME280, and the chip adjusts its baseline"). Briefly say *what the chip does with it*: "MOX-film resistance is strongly temperature- and humidity-dependent. The driver writing T and H into ENV_DATA lets the chip apply a correction polynomial internally before computing eCO₂/TVOC — it does not change what the film measures, but it cancels the largest systematic error."

## Ch70 — I²C IMUs

### AI wording / sledgehammer / buzzwords
- > "and once you understand it you can use it for any high-rate sensor."
  - Marketing. Rewrite: "Once you understand it, the same pattern works for any high-rate sensor."
- > "**trigger + buffer is the path to thousands of samples per second**."
  - Slogan with "path to". Rewrite: "**Trigger + buffer is how IIO scales to thousands of samples per second.**"
- > "Untenable."
  - One-word fragment for impact; reads AI-emphatic. Rewrite: "Not workable."
- > "invaluable for time-aligned analysis."
  - "Invaluable" again. Rewrite: "essential when you need to time-align across sensors."
- > "The driver doesn't care whether the trigger came from a timer or from the chip's own data-ready IRQ — same handler either way."
  - Fine; keep.
- > "5000 atomic samples — accel + gyro + 64-bit timestamp — captured in 5 seconds. User-space can FFT for vibration analysis, or feed to a Madgwick filter for real-time orientation."
  - Two-sentence brag. Rewrite: "Five thousand atomic samples — accel, gyro, and 64-bit timestamp — captured in 5 seconds. From here, user-space can FFT for vibration analysis or feed a Madgwick filter for orientation."
- > "This is *user-space* math, not driver math. The driver's job is to deliver clean samples; the application owns the fusion."
  - "Owns the fusion" idiomatic; semicolon. Rewrite: "Fusion belongs in user-space, not in the driver. The driver delivers clean samples; the application turns them into orientation."

### ESL readability
- > "For a 1 kHz IMU, a one-sample-per-sysfs-read loop hits the syscall path 1000 times per second per axis. That's ~30 µs per sysfs read × 6 axes × 1000 Hz = 18 % of one CPU just on the syscall overhead."
  - The math line "× 6 × 1000 = 18 %" is dense but clear; keep. The "hits the syscall path" idiom should change: "crosses the syscall boundary 1000 times per second per axis."
- > "Adding a magnetometer gives an Earth-field reference: the chip measures the geomagnetic vector (~50 µT, pointing roughly north + downward). Combined with the accel's gravity vector, the fusion algorithm can pin all three rotational axes."
  - "Pin all three rotational axes" is technical idiom. Rewrite: "Combined with the accel's gravity vector, the fusion algorithm can lock down all three rotation angles — roll, pitch, *and* yaw."
- > "So even at 1 kHz, the CPU only wakes once per sample — and only briefly. Compare to `read()` polling: 30 µs per syscall × 6 channels = 180 µs of CPU per sample (18 %). With trigger+buffer: maybe 5 µs per sample (0.5 %)."
  - "Only briefly" + telegraphic comparison; rewrite to a normal sentence: "At 1 kHz the CPU wakes once per sample for a few microseconds. Compare to `read()` polling, which is 30 µs per syscall and 6 channels = 180 µs per sample, or 18 % of one CPU. Trigger+buffer is closer to 5 µs per sample, around 0.5 %."

### Needs more depth
- §70.4 IIO buffered mode is the main topic of the chapter and explained well, but a few essential terms are unnamed:
  - `scan_elements/*_en` is shown as user-space writes "1" to enable a channel — but the chapter never says "the IIO buffer's *scan mask* is the bitfield of enabled channels." Add one sentence so the reader can grep for `scan_mask` in driver code.
  - `iio_pollfunc_store_time` is named in the probe as the "pre-handler" but never explained. One sentence: "`iio_pollfunc_store_time` is a stock pre-handler that runs in the trigger's hardirq context and timestamps the trigger event. The main handler runs later, in thread context. The pair is the standard top-half / bottom-half split for IIO triggers."
  - `scan_index` and `scan_type` are used in the channel macro but the *layout in the buffer* is left implicit. One sentence: "Each enabled channel's `scan_type` (storagebits) defines how many bytes it consumes in the sample; channels are packed in ascending `scan_index` order; `IIO_CHAN_SOFT_TIMESTAMP(N)` always sits at the end at an 8-byte aligned offset." Important because user-space parsers rely on this contract.
- §70.5 "Two-stage IRQ path" subsection mentions SCHED_FIFO and `IRQ_WAKE_THREAD` but does not cross-link to Ch 43's threaded IRQ discussion. One sentence: "See Ch 43 §43.4.1 for how threaded IRQs work in general; the IIO trigger path is a specialisation of that pattern."
- §70.10 Madgwick — fine to keep at a high level, but the `quat_mul`, `compute_gradient`, `normalize` functions are referenced as if defined elsewhere. Either add one paragraph noting "these are standard quaternion ops; reference implementation at https://x-io.co.uk", or drop the code snippet and just describe the algorithm.

## Ch71 — SPI IMUs

### AI wording / sledgehammer / buzzwords
- > "**the FIFO + watermark IRQ pattern**. Instead of getting an IRQ per sample (8000/s = unacceptable), configure the chip's internal FIFO with a watermark threshold."
  - "= unacceptable" reads as a slide annotation. Rewrite: "Instead of taking one IRQ per sample (8000/s, far too many), configure the chip's internal FIFO with a watermark threshold."
- > "making multi-IMU systems easy."
  - "Easy" is marketing. Rewrite: "which makes multi-IMU systems straightforward to wire."
- > "Distinguishing feature: **two SPI ports**"
  - Slide-bullet fragment. Rewrite: "Its distinguishing feature is two SPI ports."
- > "If you need them, the LSM6DSO is irreplaceable."
  - "Irreplaceable" is dramatic. Rewrite: "When you need FSM or MLC, no other current-production part offers the same."
- > "Beyond ~400 Hz per axis, I²C's 400 kHz × ~10 bits-per-byte budget is exhausted."
  - "Budget is exhausted" idiom for ESL. Rewrite: "Beyond ~400 Hz per axis, you run out of I²C bandwidth: 400 kHz divided by ~10 bits per byte does not leave room for many channels."
- > "CPU load drops 16-fold; data is identical."
  - Semicolon + slogan. Rewrite: "CPU load drops 16-fold, and the captured data is the same."

### ESL readability
- > "The chip IRQs only when N samples have accumulated; the driver drains them all in one SPI burst."
  - "IRQs" as verb + semicolon. Rewrite: "The chip raises its IRQ only when N samples have accumulated. The driver then drains them in a single SPI burst."
- > "ADXL345 outputs *little-endian*; MPU6050 outputs *big-endian*. Easy to swap by accident."
  - Semicolon. Rewrite: "ADXL345 puts data out little-endian. MPU6050 puts it out big-endian. Easy to swap by accident."
- > "Some boards leave /CS floating during SoC reset; chip enters undefined state. Tie /CS HIGH at idle (10 kΩ to VCC or controller-default)."
  - Semicolon + telegraphic. Rewrite: "Some boards leave /CS floating during SoC reset. The chip then sits in an undefined state. Tie /CS HIGH at idle — 10 kΩ to VCC, or rely on the SPI controller's default."

### Needs more depth
- §71.4 the regmap config trick `read_flag_mask = 0x80 | 0x40` is shown without enough context. The MCU reader has seen R/W bit at MSB before, but the *regmap mechanism* (regmap OR's `read_flag_mask` into the register address on every read) is new. One sentence: "Regmap OR's `read_flag_mask` into the register byte for every read, and `write_flag_mask` for every write. Setting both is how you encode the chip's R/W + multi-byte protocol once and forget about it."
- §71.5 the watermark IRQ handler reads the FIFO sample-by-sample in a loop: `for (i=0; i<entries; i++) ma_read(m, REG_DATAX0, sample, 6);`. Each call is one SPI transaction. The mainline driver does a single bulk read of all `entries*6` bytes. Explicitly mention this as a follow-up improvement: "The mainline driver does a single `regmap_noinc_read` of all `entries × 6` bytes in one SPI transaction, instead of one transaction per sample. At 800 Hz × 16-sample watermark, that is one SPI burst vs 16 — measurable CPU saving."
- §71.6 LSM6DSO FSM/MLC mentioned with intriguing examples ("doorbell pressed", "drone has crashed") but no concrete pointer to *how to compile a program for them*. One sentence: "ST's UNICO-GUI tool (`st.com/en/embedded-software/unico-gui.html`) converts a labelled motion dataset to the binary blob the chip executes; the IIO config interface uploads it at runtime via firmware-loader."

## Ch72 — Distance & proximity

### AI wording / sledgehammer / buzzwords
- > "the bane of Linux's preemption"
  - Cute but slangy for ESL. Rewrite: "famously hard to time accurately under Linux."
- > "promise customers ranging accuracy you can't deliver."
  - "Customers" is unusual register; consultant-speak. Rewrite: "promising users a ranging accuracy you cannot actually deliver."
- > "**time-of-flight is electronics; ultrasonic is physics; IR is photometry**."
  - Three-way semicolon triplet. Rewrite: "Time-of-flight measures with electronics. Ultrasonic measures with sound. IR measures with reflected brightness. Three different physics."
- > "The 'magic' of the driver is mostly the tuning-blob loop."
  - "Magic" again. Rewrite: "What looks complex in the driver is mostly the tuning-blob loop."
- > "VL53L0X is *the chip with a firmware blob*."
  - Slide-tagline. Rewrite: "VL53L0X is unusual: it needs a long initial register-write sequence — effectively a firmware blob — uploaded at every probe."
- > "**Bottom line:** don't ship HC-SR04 connected to Linux GPIO."
  - "Bottom line" is corporate-English. Rewrite: "In short: do not ship products with HC-SR04 wired directly to Linux GPIO."
- > "an honest discussion of why HC-SR04 is hard on Linux."
  - "Honest discussion" is editorial. Rewrite: "a clear-eyed look at why HC-SR04 is hard on Linux."
- > "Each driver's complexity reflects this hierarchy."
  - Tidy slogan; harmless once but combined with everything above reads polished. Trim: "Each driver's complexity tracks the physics."

### ESL readability
- > "The chip's own emitter reflects off the inner glass surface; 'or '0 mm' reading forever. Mount with a recessed window or angled cover."
  - Semicolon + jargon-y "recessed window". Rewrite: "The chip's emitter reflects off the inner surface of the glass, and you read 0 mm forever. Use a recessed window or tilt the cover slightly."
- > "Note the **two busy-wait loops** in the kernel. This burns a CPU during the ~25 ms measurement."
  - "Burns a CPU" idiomatic. Rewrite: "The kernel busy-waits in two loops here. That keeps one CPU pinned for the full ~25 ms measurement."
- > "Range = 2 m at indoor light, drops to ~0.6 m in direct sunlight (940 nm ambient noise dominates). Accurate, fast, but more complex than the alternatives."
  - Fragment ending. Rewrite: "Range is 2 m in indoor light. In direct sunlight it drops to ~0.6 m because 940 nm ambient noise dominates. The chip is accurate and fast, but more complex than the alternatives."
- > "User-space converts voltage to mm via the datasheet's piecewise table or polynomial."
  - Fine; keep.

### Needs more depth
- §72.3 the VL53L0X tuning blob is described as "STMicro's IP", not documented. For an ESL/MCU reader, the *practical consequence* of this for the kernel driver is worth one sentence: "The tuning blob is reverse-engineerable from STMicro's open-source `STSW-IMG005` C SDK, which the kernel driver imports. Treat it as a vendor-provided initialization script."
- §72.6 the four options for HC-SR04 timing — PREEMPT_RT, capture-input timer, MCU helper, PRU — are listed but none gets a sense of *which is realistic for a Linux beginner*. Add one ranking sentence: "For learning: PREEMPT_RT + threaded IRQ (option 1) is the lowest-effort path. For production: a $1 MCU helper (option 3) is the standard solution and the one shipped in actual products."
- §72.7 the GP2Y0A's non-linear curve is mentioned but not shown. A small table (5 points: 100 mm, 200 mm, 400 mm, 600 mm, 800 mm → V) gives the MCU reader a concrete sense of "how non-linear" and lets them write the polynomial fit immediately.

## Ch73 — Magnetometer / compass

### AI wording / sledgehammer / buzzwords
- > "Most engineers ship without calibration and wonder why their bearing is off — sometimes they blame the IMU."
  - Editorial swipe. Rewrite: "Many products ship without calibration; their compass is off by 10–30°, and the IMU often gets blamed."
- > "**calibration happens in user-space, but the driver must enable it**."
  - Bold-as-tagline. Slim the surrounding paragraph: "Calibration runs in user-space; the driver's job is to deliver raw X/Y/Z in stable, scaled units."
- > "the most important non-driver content of the chapter"
  - Self-referential. Rewrite: "Most of this chapter is not driver code. It is calibration."
- > "the part everyone skips"
  - Slogan in subsection title. Keep — actually a fine ESL signal that this matters. But change "everyone" to "most products": "Calibration — the part most products skip."
- > "**Trap**: HMC5883L's name is on every $1 eBay 'HMC5883L' breakout. Those modules are *QMC5883L*."
  - Fine; the lead "Trap:" reads like a slide bullet. Rewrite: "Watch for this: every $1 eBay 'HMC5883L' breakout is actually a QMC5883L."
- > "completely unusable for navigation."
  - "Completely unusable" is dramatic. Rewrite: "Heading is wrong enough to be useless for navigation."
- > "**You cannot drive a QMC5883L with HMC5883L code; the chip will appear inert.**"
  - Bold + semicolon. Rewrite: "HMC5883L code does not work on a QMC5883L — the chip will simply not respond."

### ESL readability
- > "The samples will fit on an ellipsoid; you compute: 1. The **offset** ... 2. The **3x3 matrix** to rotate-and-scale the ellipsoid into a sphere — soft-iron correction."
  - The introductory sentence has a semicolon and ends with a colon into a numbered list. Rewrite the lead: "The samples fall on an ellipsoid. From the ellipsoid you compute two things:"
- > "Tilt unaccounted for. XY-only heading assumes the sensor is level. For real attitude-aware compass, use tilt-compensation: combine with accel to project the magnetic vector onto the horizontal plane."
  - Two-fragment lead + colon + jargon. Rewrite: "**XY-only heading assumes the sensor is held level.** If the device can tilt, combine the magnetometer with the accelerometer and project the magnetic vector onto the horizontal plane. This is 'tilt compensation' and it is mandatory for any device a user holds in their hand."
- > "the killer differences"
  - Idiom. Rewrite: "the breaking differences" or just "the differences that matter."

### Needs more depth
- §73.7 the "proper" ellipsoid fit (10 parameters via least-squares) is named but never broken down. For the engineer-at-whiteboard reader, *one* paragraph describing the algorithm at a high level is worth more than the literature pointer: "The full method: collect ~1000 samples spanning all orientations; assemble a 10×N design matrix from each sample's `(x²,y²,z²,xy,xz,yz,x,y,z,1)`; solve the generalised eigenvalue problem to get the ellipsoid's quadratic form; decompose into center (hard-iron offset) and 3×3 symmetric matrix (soft-iron). The matrix's Cholesky factor is the linear map that turns ellipsoid into sphere."
- §73.5 mainline drivers expose `sampling_frequency` etc. but the *relationship between sampling rate and noise floor* for a magnetometer is left out. One sentence: "Higher sampling rate widens the noise bandwidth (noise floor ∝ √Hz). For a stationary compass, ~10 Hz is plenty and gives the lowest noise; for fast-moving gimbals, 100 Hz or higher trades noise for latency."
- §73.10 "Slow rotation during calibration" pitfall — would be much more useful with a *concrete cadence*: "Aim for ~2 full rotations per axis over 30 seconds; faster and you skip arcs of the sphere, slower and bias drift creeps in."

## Ch74 — Hall-effect & rotary position

### AI wording / sledgehammer / buzzwords
- > "**the magnet matters as much as the chip**."
  - Bold tagline. Rewrite: "**The magnet matters as much as the chip — get it wrong and the chip reads garbage.**"
- > "Most 'AS5048 doesn't work' reports trace to magnet selection."
  - Editorial. Rewrite: "Most 'AS5048 doesn't work' threads online trace back to the wrong magnet."
- > "Hall-on-magnet replaces optical encoders for lower cost, infinite life (no slip-rings or photo-emitter aging), and tolerance to oil/dust."
  - 26-word bullet-as-prose. Break: "Hall-on-magnet sensors replace optical encoders. They cost less, last longer (no slip-rings, no aging photo-emitters), and tolerate oil and dust."
- > "Buy a small (6 mm × 2.5 mm) **diametrically-magnetised** disc-magnet separately."
  - Fine; keep.
- > "Default choice."
  - Slogan fragment. Rewrite: "The general-purpose choice." Or just attach to previous sentence.
- > "The 14-bit absolute angle is now in IIO, ready for any consumer."
  - "Ready for any consumer" is consultant-speak. Rewrite: "The 14-bit absolute angle is in IIO, ready for any application that needs it."

### ESL readability
- > "Each SPI frame is 16 bits: ... You send a *command frame* this transaction; the *response* comes in the *next* transaction."
  - "This transaction" / "next transaction" reads awkwardly without articles. Rewrite: "You send a *command frame* in the current transaction. The matching *response* arrives in the next transaction."
- > "Datasheet specifies 1–3 mm typical."
  - Telegraphic. Rewrite: "The datasheet specifies a typical air gap of 1–3 mm."
- > "Hot-plug/start-up race."
  - Pitfall heading fragment. Rewrite: "**Hot-plug / start-up race.** The chip needs about 10 ms after VCC rises. A read earlier returns junk. The mainline driver handles this delay; the from-scratch driver must too."

### Needs more depth
- §74.3 the "two-frame protocol" (command this frame, result next frame) is a real conceptual hurdle for someone used to register-read-returns-value chips. The chapter mentions it but does not say *why* the chip is designed this way. One sentence: "AS5048 returns whatever it has staged in its output register on the *current* SPI clock cycle, while latching the new command for the *next* cycle. The first transaction's response is therefore stale (or zero on the first read after power-up). Always issue a 'priming' read and discard, or expect to ignore the first answer."
- §74.4 the from-scratch driver uses one 4-byte `spi_transfer` to issue command + read response. The mainline `as5048.c` uses two separate `spi_message`s. Worth a sentence: "Combining both frames in a single `spi_transfer` keeps /CS asserted the whole time, which is *not* what AS5048 specifies. Some chips tolerate it; some do not. For correctness, use two separate `spi_message`s with their own CS toggle, or set `cs_change=1` on the first transfer."
- §74.6 TLE5012 "SSC protocol" is named but not explained. One sentence: "SSC is a 3-wire SPI variant where MOSI and MISO share one bidirectional line. The chip drives it during the response phase. This saves a pin but requires the SoC's SPI controller to support tri-state SDI/SDO — i.MX6ULL eCSPI can with extra GPIO management, not natively."

## Ch75 — Current & power monitoring

### AI wording / sledgehammer / buzzwords
- > "the *calibration register* that everyone gets wrong"
  - "Everyone gets wrong" editorial. Rewrite: "the *calibration register* that is the most common bug."
- > "**the shunt converts current to voltage; the chip converts voltage to digital, then divides by shunt to recover current**."
  - Triplet with semicolons. Rewrite: "The shunt converts current to voltage. The chip's ADC converts voltage to a count. The calibration register tells the chip the shunt's value, so the chip can report current directly."
- > "Forget the calibration register and you read garbage scaled by an unknown factor."
  - "Garbage scaled by an unknown factor" is informal. Rewrite: "Without the calibration register, the Current and Power registers read zero (or numbers in unknown units, depending on the chip)."
- > "the part everyone gets wrong"
  - Tagline repeated. Rewrite: "the part most people miss on the first try."
- > "This is the part everyone gets wrong."
  - Same. Pick one and drop the repeated framing.
- > "**Current monitors → hwmon**. IMUs, ADCs, environmental sensors → IIO. Some chips have both drivers (legacy + modern). Don't enable both."
  - Slide-fragment style. Rewrite: "Current monitors live in hwmon. IMUs, ADCs, and environmental sensors live in IIO. A few chips have both drivers — pick one in your kernel config and disable the other."

### ESL readability
- > "The chip's internal `Current` register doesn't measure current directly. It computes: `Current_register = (Shunt_voltage × Calibration_register) / 4096`"
  - Fine; keep.
- > "Where: `Current_LSB` is the unit you want ... `R_shunt` is in ohms."
  - "Where:" is mathematical English. Fine for an engineer.
- > "Common-mode voltage limit. Both INA pins must be within the chip's input range. For a high-side shunt on a 24 V rail, V+ and V− are both around 24 V — INA219 spec'd to 26 V, fine."
  - "Spec'd" idiomatic; em-dash. Rewrite: "Common-mode voltage limit. Both INA pins must sit within the chip's input range. On a high-side shunt at 24 V, V+ and V- are both close to 24 V. INA219 is rated up to 26 V, so that is fine."
- > "Common-mode voltage" is named but not defined for an MCU reader who may not have analog-IC vocabulary. One sentence: "Common-mode voltage is the absolute voltage of both inputs above ground (not the difference between them). High-side shunts have a high common-mode (~VBUS); low-side shunts have a low common-mode (~0 V)."

### Needs more depth
- §75.3 the LSB constants `4096`, `0.04096`, `2048` are called "physical constants of the chip's design" but never traced to a derivation. For a curious reader: "The 4096 divisor in `Current = Shunt × Cal / 4096` comes from the chip's internal 12-bit fixed-point format. The 0.04096 in the calibration formula falls out of `4096 × Current_LSB × R_shunt` after solving for Cal — it carries the constant scaling between the chip's internal counts and SI units of A·Ω."
- §75.6 the hwmon/IIO table is good. Add one row: **"Per-sample timestamp"** — hwmon has none; IIO buffers do. Reinforces the buffering distinction.
- §75.4 the driver writes the calibration as `cal = data->config->calibration_value * 1000000 / data->shunt_uohms`. The DT property `shunt-resistor` is in *micro-ohms*. Worth one sentence in the prose: "The DT binding takes the shunt value in micro-ohms (`shunt-resistor-micro-ohms`). Putting it in micro-units keeps the math integer-only in the kernel and matches Linux convention for sub-SI scaled DT properties."

## Ch76 — Battery fuel gauge + charger

### AI wording / sledgehammer / buzzwords
- > "report 'percent full' to the user *honestly*."
  - "Honestly" editorial. Rewrite: "report 'percent full' to the user accurately."
- > "**`power_supply_class` is how kernel and user-space cooperate on battery state**."
  - Slogan. Rewrite: "The kernel exposes battery state to user-space through `power_supply_class`, the same framework used by laptops, phones, and embedded boards."
- > "ModelGauge's claim to fame"
  - Marketing English. Rewrite: "MAX17048's main selling point" — or drop and just state the facts.
- > "The right choice for a real product."
  - "Real product" is editorial. Rewrite: "The standard choice for production-grade hardware."
- > "**Use BQ24074 for**: any product where the user expects the device to power up immediately when plugged in (and the battery isn't presumed alive)."
  - "Bold-then-colon" slide pattern + nested parenthetical. Rewrite: "Pick BQ24074 for any product that must come up the moment a USB cable is plugged in, regardless of whether the battery is alive."
- > "Standardised. Phones, laptops, IoT — all use this."
  - Fragment tagline. Rewrite: "The naming is standardised across phones, laptops, and embedded boards."
- > "Slow but charming"
  - Editorial. (This is in Ch 77's preview line.) Leave for Ch 77.

### ESL readability
- > "MAX17048's claim to fame: 23 µA standby, no shunt, factory-loaded 'typical Li-ion' model, 'good enough for most products' SoC."
  - Bullet-as-prose with quoted-as-aside. Rewrite: "MAX17048's main selling point: 23 µA standby current, no shunt resistor required, a factory-loaded 'typical Li-ion' model, and SoC accurate enough for most consumer products."
- > "The middle plateau is flat — a small voltage range covers most of the capacity."
  - Fine; keep.
- > "Read at the wrong moment, you tell the user 60 % when actual is 65 %."
  - "Read at the wrong moment" telegraphic. Rewrite: "If you read while a high-current load is active, you may tell the user 60 % when the resting SoC is actually 65 %."
- > "instantaneous readings can wobble ±1 % under varying load."
  - "Wobble" colloquial. Rewrite: "instantaneous readings vary by ±1 % when the load is unsteady."

### Needs more depth
- §76.2 ModelGauge is described as "build an internal model of the cell's V/I/T/SoC relationship". This is the chapter's deep concept and deserves a small diagram (or table) showing how SoC is *not* a function of just V. A 5-row table with (V_cell, load_current, true_SoC) showing the same voltage giving two different SoCs under different loads would land the point much better than the current prose alone.
- §76.4 `power_supply_class` is introduced via the enum and a sysfs example. Missing: *how driver and user-space stay in sync when state changes*. One paragraph: "When the driver detects a state change (charger plugged in, capacity dropped past a threshold), it calls `power_supply_changed(psy)`. The framework sends a uevent on the device; user-space daemons (UPower, systemd) react. This is how 'battery low' notifications appear without any polling on the user-space side. A from-scratch driver should call `power_supply_changed` from an interrupt handler or a polling thread that compares the new reading to the cached old one."
- §76.5 the from-scratch driver returns `POWER_SUPPLY_STATUS_UNKNOWN` for STATUS — but the chapter never wires up the CRATE register to make it real. Either add the 10-line CRATE read + sign-check in the example code, or move that hint into a dedicated "exercise for the reader" pitfall.
- §76.6 TP4056 limitation about "no power-path" is well stated, but the *symptom* on Linux ("boot loops on a deeply-discharged battery") is named without explanation. One sentence: "On TP4056, the SoC's input rail sags as soon as it draws current, because the battery voltage at 2.7 V cannot sustain the load. The SoC resets, releases the load, voltage recovers, the SoC tries again — classic crowbar boot loop. With a power-path charger (BQ24074), the USB input takes over instantly and the SoC sees a stable 5 V regardless of cell state."
- §76.10 "Quick-start without justification" — say *what quick-start does internally* in one line: "Quick-start zeroes the internal accumulators and recomputes SoC from the next ~30 seconds of V/dV samples. Useful right after a fresh cell; harmful in normal operation because it discards the model's learning."

## Ch77 — 1-Wire sensors

### AI wording / sledgehammer / buzzwords
- > "Slow but charming"
  - Editorial. Rewrite: "Slow but easy to wire" — or just drop the adjective and lead with the technical fact.
- > "a brutally honest 'Linux is the wrong host' discussion"
  - "Brutally honest" is editorial. Rewrite: "a clear-eyed look at why DHT22 is a poor fit for Linux."
- > "Get the master right and slaves are trivial."
  - "Trivial" minimizes. Rewrite: "Once the master is reliable, writing a slave driver is short — the w1 core does the work."
- > "**Bottom line: if you see DHT22 in someone's product schematic, suggest a swap to SHT3x.**"
  - "Bottom line" idiom. Rewrite: "**Verdict: if you see DHT22 on someone's product schematic, replace it with SHT3x.**"
- > "**a digital MEMS mic is 'an I²S DAI with no control interface'**"
  - (This belongs to Ch 78.) Same pattern; covered there.
- > "Once you can wire SAI → mic in DT via `simple-audio-card` and capture with `arecord`, you have a working audio-input pipeline."
  - "Once you can…, you have…" reads as a marketing tagline. Rewrite: "Wire SAI to the mic in DT via `simple-audio-card`, then `arecord` captures the audio. That is the whole audio-input pipeline." (Belongs to Ch 78.)
- > "the pretender"
  - Slangy. Rewrite: "the lookalike."
- > "DHT22 borrows the wire and the parasitic power but invented its own timing"
  - "Borrows" / "invented its own timing" is editorial. Rewrite: "DHT22 uses the same physical wiring (one signal line plus ground, with parasitic power) but a different, incompatible bit-framing scheme."

### ESL readability
- > "**edge detection is not the same as edge timing**. The host must drive transitions with ±5 µs accuracy."
  - Strong distinction; keep — but soften the bold-as-slogan style: "Detecting that an edge happened is not the same as knowing *when* it happened. The host must drive transitions with about ±5 µs accuracy."
- > "Once one bit is misread, the whole frame is corrupt (no resync)."
  - "Resync" is jargon; fine but rephrase: "Once one bit is misread, the whole 40-bit frame is wrong — there is no resync point until the next measurement starts."
- > "Acceptable for 'read every 5 seconds'; not acceptable for thousands of reads per second."
  - Semicolon. Rewrite: "Fine for 'read every 5 seconds.' Not fine for thousands of reads per second."

### Needs more depth
- §77.1 the *parasitic-power* concept is mentioned in §77.3 only briefly. For an MCU reader, it deserves one paragraph here: "1-Wire supports a 3-pin mode where VDD is tied to GND at the slave, and the slave draws power from the bus's pull-up during 'high' periods, charging an internal capacitor. This works at low duty cycles. During long operations like a temperature conversion, the master must drive the line *actively high* (not just pull-up) for tens of ms — this is the 'strong pull-up' the chapter mentions in pitfalls."
- §77.3 `w1_reset_select_slave`, `w1_write_block`, `w1_read_block` are listed but the *kthread that calls them* is not explained. The MCU reader, after Ch 41–42, is primed for "what context does my slave driver run in?". One sentence: "The w1 core runs a kthread per master. All slave driver callbacks (sysfs attribute show/store, etc.) run in process context on user-space's request, taking `master->bus_mutex` to serialize with the enumeration kthread."
- §77.6 the four options for DHT22 are listed but for the engineer-reader, one concrete latency number per option would clinch it: "PREEMPT_RT + threaded IRQ: 20 µs typical, 150 µs worst case → ~95 % success rate. Hardware capture timer: ~10 ns resolution → 100 %. MCU helper via I²C: zero Linux timing concern → 100 %. PRU: nanoseconds → 100 %."

## Ch78 — MEMS microphones

### AI wording / sledgehammer / buzzwords
- > "**a digital MEMS mic is 'an I²S DAI with no control interface'**"
  - Bold tagline. Rewrite: "A digital MEMS mic is, from Linux's view, an I²S DAI without any control interface — clocks in, samples out."
- > "From Linux's perspective it's just a slave of the SAI."
  - "From X's perspective" tic. Rewrite: "To the SAI driver, the mic is just an I²S slave."
- > "**don't write this**"
  - Slogan. Rewrite: "Most projects do not need a custom machine driver. Use `simple-audio-card`."
- > "Plays back in stereo on the host."
  - Telegraphic. Rewrite: "The captured file plays back in stereo on the host."
- > "This is the part worth understanding even when you don't write the drivers"
  - Slide-tagline. Rewrite: "Worth understanding even when you do not write the drivers yourself."
- > "70 lines — same shape as Ch 53's WM8960 machine driver but simpler"
  - Editorial brevity. Rewrite: "Roughly 70 lines. Same shape as Ch 53's WM8960 machine driver, only without the codec controls, DAPM widgets, and jack-detection."

### ESL readability
- > "There's no I²C control — the mic has no registers. The wires alone (BCLK, LRCLK, SD, LR-select strap) determine its behavior."
  - Good; keep.
- > "the 24 bits go in the upper bits of the 32-bit container"
  - "Container" is OK but could be clearer: "the 24 audio bits sit in the high 24 bits of the 32-bit slot; the bottom 8 bits are zero."
- > "Configure for S32_LE in ALSA; the 24 bits go in the upper bits of the 32-bit container."
  - Semicolon. Rewrite per above.

### Needs more depth
- §78.4 the `dmic-codec` "fake codec" is a key conceptual hurdle. The chapter says it has no registers but does not say *what its role* in ASoC is. One paragraph: "ASoC's machine driver requires a CPU DAI and a codec DAI; the framework expects both. `dmic-codec` is a stub codec driver that satisfies this requirement without doing anything — it has no register accesses, no DAPM widgets, no controls. Its only purpose is to be the 'other end' of the SAI ↔ codec link in the ASoC framework. A real codec driver would handle volume, jack detection, etc.; here those are all hard-wired in the mic hardware itself."
- §78.5 the SDMA data path is mentioned ("Zero CPU between mic and SDMA; one memcpy per `read()`."). For the MCU reader who learned about DMA in Ch 51, this deserves a cross-link: "See Ch 51.5 for how the SDMA ring buffer between SAI and DDR is built. The audio ALSA pipeline reuses the same generic DMA-coherent ring pattern."
- §78.9 "S32_LE vs S24_LE" — the chapter says "S24_LE *may* work depending on ASoC version" but does not say what to actually do. One sentence: "Set ALSA's format to S32_LE unconditionally; the mainline ASoC core handles the 24-in-32 packing. S24_LE is technically '24 bits in 24 bits' (no padding), which the SAI's TDM-slot config does not support on i.MX6ULL — so use S32_LE."

## Ch79 — Health sensors (PPG)

### AI wording / sledgehammer / buzzwords
- > "**the chip captures light intensity, you compute physiology**."
  - Slogan with bold. Rewrite: "The chip delivers light-intensity samples. Your code turns those samples into heart rate and SpO₂ — the chip cannot do this for you."
- > "Without good signal processing, the readings are garbage — and the chip can't fix bad processing."
  - "Garbage" colloquial. Rewrite: "Without good signal processing, the readings are unreliable. The chip cannot compensate for bad code on the host."
- > "the principle elegant — but the *signal processing* is where the real work lives"
  - "Where the real work lives" idiom. Rewrite: "the principle is simple, but the work is in the signal processing on the host side."
- > "real production systems add: motion artifact rejection ..., auto-gain ..., finger-detection ..."
  - Bullet list fine; the lead "real production systems add" is editorial. Rewrite: "Production systems add motion-artifact rejection (using accelerometer cross-correlation to gate readings during movement), auto-gain (adjusting LED current to keep DC in range), and finger-detection (treating low DC as 'no finger')."
- > "Don't claim 'medical-grade SpO₂' without proper calibration against a reference oximeter."
  - Editorial caution; fine and useful, keep.

### ESL readability
- > "Some of it gets absorbed by blood; the rest reflects/scatters back to a photodiode."
  - Semicolon + slash. Rewrite: "Some of it is absorbed by blood. The rest reflects or scatters back to a photodiode."
- > "The signal is tiny — ~1 % of the DC level. The bulk of what hits the photodiode is the constant amount that gets through tissue."
  - "The bulk of" idiomatic. Rewrite: "The pulsatile signal is small — about 1 % of the DC level. Most of the light hitting the photodiode is the constant amount that passes through tissue without modulation."
- > "Compute: ... 110 − 25·R (empirical for fingertip PPG; calibration-dependent)"
  - Parenthetical with semicolon. Rewrite: "Compute `SpO₂ ≈ 110 − 25 × R`. This linear formula is empirical for fingertip PPG and depends on the specific chip's geometry."
- > "The bulk of what hits the photodiode is the constant amount that gets through tissue. The pulsatile 'AC' component is the interesting bit."
  - "Interesting bit" idiom. Rewrite: "The pulsatile AC component is the signal we actually want."

### Needs more depth
- §79.2 SpO₂ formula `110 − 25·R` is presented with one parenthetical "empirical for fingertip PPG; calibration-dependent." For a chapter that aims at depth, *why* this formula form (linear) versus a polynomial fit deserves one sentence: "The linear approximation is the first-order term of the Beer-Lambert relationship between R-ratio and oxygen saturation, valid in the SpO₂ 70–100 % range. Below 70 %, the curve becomes noticeably nonlinear; pulse oximeters that report low values use a piecewise table instead."
- §79.4 says mainline IIO drivers exist (`max30100.c`, `max30102.c`) but never explains what they expose — only that they leave DSP to user-space. Add one sentence: "The mainline drivers register `IIO_INTENSITY` channels with `IIO_MOD_LIGHT_RED` / `IIO_MOD_LIGHT_IR` and a soft-timestamp channel; the chip's data-ready IRQ drives a triggered buffer. User-space reads `/dev/iio:device0` at the configured sample rate and applies the HR/SpO₂ DSP described in §79.6."
- §79.5 the driver's `mh_read_raw` for `INFO_RAW` returns "the latest" by draining all but one. This is a debatable design choice — sysfs reads should usually return *one* sample, not "whatever is freshest after discarding queued data." Mention the trade-off: "This implementation drains the FIFO down to its last sample on each sysfs read so the user always sees recent data. The alternative (return the next-queued sample) means stale readings during slow polling. Buffered mode is the correct path for high-rate logging — sysfs is meant for the occasional one-shot."

## Ch80 — External ADCs

### AI wording / sledgehammer / buzzwords
- > "saves you from chasing noise in a design that was doomed at the silicon level."
  - "Doomed" dramatic. Rewrite: "saves you from chasing noise that the silicon will never let you remove."
- > "**bits, speed, channels, and simultaneity are independent axes**."
  - Slogan. Trim: "Bits, speed, channels, and simultaneity are independent design axes."
- > "ADS1115 = high-bit, slow, multiplexed. MCP3008 = low-bit, medium-speed, cheap. ADS1256 = very-high-bit, low-noise, slow. AD7606 = high-bit, fast, *simultaneous*."
  - Slide-bullet `=` style. Rewrite as a sentence or a proper bullet list with verbs: "**ADS1115** is high-bit, slow, and multiplexed. **MCP3008** is low-bit, medium-speed, and cheap. **ADS1256** is very-high-bit, low-noise, and slow. **AD7606** is high-bit, fast, and *simultaneous*."
- > "An external ADC ... transforms what's measurable."
  - "Transforms what's measurable" reads like marketing. Rewrite: "An external ADC with a clean reference, a PGA, and more bits lets you see signals the SoC's internal ADC cannot."
- > "the everyday precision choice."
  - Marketing. Rewrite: "the standard precision choice."
- > "beautiful trick"
  - Editorial. Rewrite: "useful trick."
- > "Pick by which axis your application stresses."
  - "Stresses" odd word. Rewrite: "Pick by which axis matters most for your application."

### ESL readability
- > "Each register is 16-bit, **big-endian** on the wire. The MUX field selects which input pair; you re-write Config to switch channels (one conversion at a time — it's multiplexed)."
  - Semicolon + parenthetical. Rewrite: "Each register is 16 bits, big-endian on the wire. The MUX field selects which input pair. To switch channels you re-write Config — the chip handles one conversion at a time, since it is multiplexed."
- > "The Vexc *cancels*. Any noise or drift in the excitation voltage cancels too — the reading depends only on the load, not on the absolute excitation."
  - Em-dash chain. Rewrite: "The Vexc *cancels*. Any noise or drift in the excitation voltage also cancels. The reading depends only on the load, not on the absolute excitation."
- > "A 12-bit ADC with a clean reference, a PGA, and more bits"
  - Fine; keep.
- > "Easy to get backwards. Check the datasheet's 'Operational Status' description carefully (it's counterintuitive)."
  - Two-fragment + parenthetical. Rewrite: "Easy to get backwards. The datasheet's 'Operational Status' description is counterintuitive — read it carefully."

### Needs more depth
- §80.3 the ADS1115 OS-bit semantics are flagged in pitfalls but never resolved in the protocol section. The chapter's own from-scratch driver has a comment "note: OS reads 1 when conversion is DONE in single-shot; check datasheet" — which is exactly the wrong place to leave the reader. Fix in §80.3 with one clear sentence: "In single-shot mode, **writing OS=1** triggers a conversion. **Reading OS** then returns 0 while the conversion is in progress, and 1 once it completes. So your poll loop reads Config and waits for OS to flip back to 1."
- §80.4 ENOB (effective number of bits) appears in the comparison table without definition. For the engineer who has heard 'ENOB' but never quite pinned down: "ENOB is the resolution after subtracting the chip's noise floor. A nominal 24-bit ADC with ~22 ENOB means 2 bits at the bottom are noise — the meaningful range is 22 bits."
- §80.9 ratiometric measurement is well explained, but the *reverse* point — when *not* to use ratiometric — deserves one sentence: "Ratiometric measurement requires the sensor's excitation and the ADC's reference to be the same node. If the sensor is excited by a constant-current source (4-20 mA loops, thermocouples with cold-junction comp ICs), use an absolute reference instead — the ADC measures the actual voltage, not a ratio."

## Ch81 — External DACs + clock generators

### AI wording / sledgehammer / buzzwords
- > "**a DAC is an IIO channel that flows the other way; a clock generator is a clk provider**."
  - Bold-with-semicolon slogan. Rewrite: "A DAC is an IIO channel that flows out instead of in. A clock generator is a `clk` provider."
- > "These three chips fill the gap, and they introduce two frameworks we haven't used: IIO's *output* channels and the kernel's *clk provider* model."
  - "Fill the gap" idiom. Rewrite: "These three chips cover the common cases, and they introduce two new frameworks: IIO's output channels and the kernel's `clk` provider model."
- > "this is one of the cases where 'understand the existing driver, don't replace it' is the right call."
  - "Right call" idiom. Rewrite: "Reimplementing Si5351's PLL math is not a productive exercise — read the existing driver instead."
- > "Two different frameworks, both worth knowing."
  - Trailing tagline. Drop or fold: "These are two different frameworks; both are useful."
- > "the inverse of Chapter 80"
  - Fine; keep.

### ESL readability
- > "MCP4725 can source/sink only ~a few mA. Driving a low-impedance load directly causes the voltage to sag."
  - "Sag" colloquial. Rewrite: "MCP4725 can source or sink only a few mA. Driving a low-impedance load directly causes the output voltage to drop."
- > "Each PLL must run 600–900 MHz internally. Output dividers are 4–2048. Not every frequency is achievable on every output; the driver's solver picks the closest."
  - Semicolon. Rewrite: "Each PLL must run between 600 and 900 MHz internally. The output dividers are 4 to 2048. Not every target frequency is achievable on every output. The driver's solver picks the closest valid combination."
- > "The mainline driver does it."
  - Telegraphic. Rewrite: "The mainline driver implements the solver for you."

### Needs more depth
- §81.3 the IIO output-channel concept is explained at the channel-spec level (`.output = 1`) but the *user-space write semantics* are not pinned down: does writing `out_voltage0_raw` block until the chip has settled? Is there a `write_*_available` for valid range? One sentence: "Writing `out_voltage0_raw` calls the driver's `write_raw` synchronously. For an I²C DAC this returns after the bus transaction completes (~100 µs at 400 kHz); for SPI it is faster. There is no settling-time wait in the framework — the driver should add `udelay` if the chip needs it before the next write."
- §81.6 the **clk framework provider role** is the harder concept of this chapter; the explanation is good but ends abruptly. Add one paragraph naming the three required `clk_ops`: "A clk provider must implement at least `recalc_rate` (report current rate when the framework asks), `set_rate` (program the hardware to a requested rate), and `round_rate` (compute the closest achievable rate without programming). Optional ops include `prepare`/`unprepare` (gate the clock on/off), `enable`/`disable` (the atomic equivalents), and `set_parent` (switch input source). For a simple frequency-synthesizer chip, just `recalc_rate` + `set_rate` + `round_rate` is enough."
- §81.6 `clock-frequency = <100000000>;` in DT — the chapter does not explain *when* the frequency takes effect. One sentence: "`clock-frequency` is a soft hint, applied when the consumer driver enables the clock. If no consumer enables it, the clock stays at the chip's reset default."
- §81.5 AD5663 is mentioned but its actual driver is `ad5446.c`. For someone hunting the source, the name mismatch is a stumbling block. Add: "Confusingly, the mainline driver file is `ad5446.c`, named after the original chip in the family. The probe table inside the file lists every variant — including AD5663 — that shares the same SPI command framing."
