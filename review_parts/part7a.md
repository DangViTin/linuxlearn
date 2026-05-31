# Part VIIa — Cookbook (Storage + Sensors): Review

## Cross-cutting observations

These issues appear across multiple chapters; per-chapter notes only call them out where the instance is particularly bad or where there is something specific to add.

- **`class_create(THIS_MODULE, ...)` is wrong on modern kernels.** Ch64 `mf_probe` and Ch65 `me_probe` both call `class_create(THIS_MODULE, "name")`. Since v6.4 (and signaled as deprecated long before), `class_create` takes only `(const char *name)` — the `THIS_MODULE` argument was dropped. Code as written will not compile against a current mainline kernel. Either drop the argument, or note explicitly that the snippet targets a specific older kernel.
- **`i2c_driver.probe` prototype is wrong on modern kernels.** Ch65/Ch67/Ch68/Ch70/Ch72/Ch73/Ch75/Ch76/Ch79/Ch80/Ch81 all declare `static int X_probe(struct i2c_client *client, const struct i2c_device_id *id)`. Since v6.3 the framework switched to single-argument `probe(struct i2c_client *)` (the legacy form is `probe_new`, now removed). Either pick the modern prototype throughout, or add one footnote explaining the kernel-version dependency. The book has just spent Part VI teaching probe patterns — the cookbook code should not silently regress.
- **`i2c_driver.remove` returns void in modern kernels.** Ch65 has `static int me_remove(struct i2c_client *client) { ... return 0; }`. Mainline switched `remove` to `void` in v6.x. Same fix-or-footnote remark.
- **`module_init`/`THIS_MODULE` & misc kernel-API churn.** A general "these snippets are pseudocode targeting kernel ~5.10–6.1; mainline ≥ 6.5 needs minor API tweaks" disclaimer would save the reader hours.
- **MCU-engineer bridge is uneven.** The intro paragraphs of each chapter often mention what an MCU engineer would do, but inside the driver walk-throughs the analogy disappears just when it would help most (e.g., "on STM32 you'd write `I2C->DR = byte; while(!(I2C->SR1 & TXE));`; here `i2c_smbus_write_byte_data` blocks because the kernel scheduler may put you to sleep — so never call it from an IRQ handler"). Add 1–2 explicit STM32/HAL-vs-Linux-API comparisons per chapter, especially around the first I²C and first SPI calls.
- **Sleeping vs atomic context is never spelled out.** A reader fresh from STM32 will see `msleep`, `usleep_range`, `mutex_lock`, `i2c_smbus_*` and `spi_sync` next to each other without being told these may sleep — and therefore why they cannot live inside a hard IRQ. Part VI introduced this, but in the cookbook chapters there is no recap, and several drivers (Ch71 `ma_irq_thread`, Ch79 `mh_irq_thread`) explicitly run sleeping calls from threaded IRQs without explaining *why that's legal here but not in a top-half hardirq*. One paragraph in the cross-cutting prelude or at the first appearance would settle this.
- **No `dmesg` "expected output" for most from-scratch drivers.** Most chapters show `cat /sys/.../value` succeeding, but skip the `dmesg | tail` after `insmod` that shows the `dev_info` line(s), bus-id, IIO device-name, IRQ allocation. That output is the *first* thing the reader will look at; show what "good" looks like.
- **No ASCII wiring diagrams in many chapters.** Ch64 and Ch65 have good wiring sketches; Ch67/68/69/70/71/72/73/74/75/76/77/78/79/80/81 either have none or only a partial physics diagram. A 6-line "i.MX6ULL pad ➜ chip pin" sketch per chapter would set the reader up before they hit the DT.
- **DT `pinctrl_*` references are unresolved.** Almost every chapter shows `pinctrl-0 = <&pinctrl_xxxx>` or `&i2c1 { ... }` without showing what's in `pinctrl_xxxx` or where `&i2c1` is declared. The reader needs to be told once ("`&i2c1` and `pinctrl_i2c1` come from `imx6ull.dtsi` and your board's pinctrl group respectively — see Ch 40"), then it can be assumed.
- **Pin assignments are never cross-checked against the reference manual.** No chapter cites the IOMUXC table from `IMX6ULL_Reference_Manual.md`. For example Ch78 says `&sai2 { ... pinctrl-0 = <&pinctrl_sai2>; ... }` without telling the reader which physical pads carry SAI2_TX_BCLK / SAI2_TX_SYNC / SAI2_RX_DATA on the iMX6ULL — yet picking the wrong pad is the most common bring-up failure. Add one "pad table" per chapter (or one shared appendix referenced from each).
- **`pa-mini` shell prompts and the implied board.** The transcripts use `[root@pa-mini:~]#` — fine — but the book has not yet introduced "pa-mini" as a board name in earlier parts (per the TOC). A single sentence at the start of Part VII saying "the prompt `pa-mini` is our reference iMX6ULL board; substitute your own hostname" would head off confusion.
- **The "from-scratch driver" is sometimes a thin wrapper around the mainline driver's logic without acknowledging it.** Ch67/68/70/73/75/76/79/80 are *good* examples of true from-scratch (per cookbook-depth requirement). Ch66 and Ch78 explicitly *do not* implement from-scratch and explain why — also good. But Ch65 and others would benefit from a one-line "what makes this 'from scratch' vs the mainline is X" sentence to keep the contract clear.
- **No glossary callouts for first-use IIO terms.** "INFO_RAW", "INFO_PROCESSED", "INFO_SCALE", "scan_index", "scan_type", "INDIO_DIRECT_MODE", "INDIO_BUFFER_TRIGGERED" appear without a quick recap. Part VI presumably covers this, but a 5-line "IIO sysfs key" recap at the start of Group B (Ch67) would help — the reader will be flipping back constantly otherwise.
- **English/readability.** Many chapter intros use compressed noun-phrase sentences ("Cookbook chapters should be HIGH-VALUE recipes — DT snippet, kernel config..."). For a non-native English reader, these read as bullet-lists masquerading as prose. The body text is usually fine; the intros are the worst. Smooth them out: "These chapters are recipes. Each gives you a DT snippet, the kernel config it needs, an expected `dmesg`, an expected `/sys` or `/dev` path, a userspace test command, and the common ways it fails."
- **`i2c_smbus_read_i2c_block_data` semantics.** Ch67, Ch70, Ch72, Ch79, Ch80 all use this. It is limited to 32 bytes per call, sets the register pointer with one byte, and uses SMBUS "block read with length byte" semantics on some adapters. Most i.MX users get away with it, but flagging this once would prevent surprise when ports get to a controller that's stricter.
- **`devm_iio_triggered_buffer_setup` called with all-NULL handlers (Ch71, Ch79).** Passing `NULL, NULL, NULL` registers the triggered-buffer infrastructure with *no* handler — meaning if a user does `echo 1 > buffer/enable` against an hrtimer trigger, nothing pushes samples. The drivers depend instead on the chip's own watermark/data-ready IRQ to push samples. Spell this out, otherwise a reader trying to bind an hrtimer trigger will get an empty buffer and have no idea why.

## Ch64 — QSPI NOR flash

### Readability
- §64.1 opening: "QSPI NOR fits when storage need is < 32 MB, you want fast/deterministic boot..." — comma splices and missing "if". Suggest: "QSPI NOR fits when the storage need is under 32 MB, the system wants fast and deterministic boot, the device should be theft-resistant (soldered), and there is no bulk user data to store."
- §64.4 "Three invariants that catch beginners" — strong section, just fix point 3's grammar: "first requires the relevant sector to have been erased to all-0xFF" → "first requires the sector to have been erased to all 0xFF".
- §64.10 prose around `boot_qspi=...` is dense — break into the three command lines and explain each. Currently relies on the reader knowing U-Boot env syntax.

### MCU-engineer friendliness
- The opening §64.4 protocol description is excellent — exactly the right tone for a reader who has bit-banged an SPI flash on an STM32. Keep doing this. Reinforce: "on bare metal you'd write `SPI->DR = 0x9F` and busy-wait `SPI->SR & RXNE`; here `spi_mem_exec_op` does the equivalent — but may sleep waiting on DMA completion, so it cannot be called from an IRQ handler."

### Missing examples / figures
- Show the actual `dmesg` after `insmod myflash.ko` (just the bus enumeration line + JEDEC line) — not only the `cat /dev/myflash | hexdump` output.
- A timing diagram of "page program 256 B + status poll loop" with annotated µs ranges would crystallise §64.4's three invariants.
- No `i2cdetect`-equivalent for SPI — show that `/dev/spidev3.0` exists (or that `ls /sys/class/spi_master/spi3/` shows the bus) so the reader knows how to verify SPI is alive before loading the chip driver.

### Insufficient depth
- This chapter meets the cookbook-depth requirement well (mainline internals, then from-scratch ~250-line driver, then mainline DT). Nothing to flag.

### Technical errors
- §64.6, `spi_nor_read` skeleton uses `nor->addr_nbytes` — the mainline field is currently `nor->addr_nbytes` in 6.x but was `nor->addr_width` historically. Footnote the kernel version, or accept that small skew is OK.
- §64.6, `spi_nor_wait_till_ready` uses a 40-second deadline — true for chip-erase but wildly long for sector-erase. Real driver uses per-operation deadlines from `info->mfr_flags`. Not wrong, just simplified — flag it.
- §64.7 `mf_probe` calls `class_create(THIS_MODULE, ...)` — see cross-cutting.
- §64.7 `mf_xfer` builds `hdr[5]` but only ever writes 4 bytes (`hdr_len = 4` at most). Fine but suggestive of "I planned to support 4-byte addressing"; either drop the unused byte or implement 4-byte mode.
- §64.7 — the chip type checking `if (id[0] != 0xEF || id[2] != 0x18)` only accepts a 16 MB W25Q128 (manufacturer 0xEF, capacity-code 0x18). Fine for the from-scratch demo, but call out explicitly that a W25Q64 (0xEF 40 17) will refuse to probe even though the protocol is identical.
- §64.9 "XIP from QSPI" claims max ~50 MB/s on i.MX6ULL — the i.MX6ULL QSPI controller maxes out at 60 MHz quad-mode = ~30 MB/s sustained from typical NOR. The 50 MB/s figure looks lifted from a higher-spec part (i.MX6Q/SX QSPI). Verify against the i.MX6ULL reference manual §8.6 or substitute a measured number.

### Other
- Lab #1 says "Without your driver loaded, use raw SPI via `/dev/spidev*` to send `0x9F`" — but `/dev/spidev*` only appears if the DT binds something to `compatible = "spidev"`. Tell the reader how to get spidev exposed for this lab (DT snippet, kernel config, the `spidev` ACL warnings in dmesg). Otherwise the lab is a dead end.
- `flash_erase` and `nandwrite` are used in §64.8 — but those come from `mtd-utils`. Mention that and that `nandwrite` works on NOR despite the name. Beginners often don't realize.

## Ch65 — I²C / SPI EEPROM

### Readability
- §65.2 table comment "Pick AT24C02 for tiny ID storage (MAC, serial), AT24C512 for calibration tables, 25LC512 for SPI bus or factory-speed bulk programming." reads fine.
- §65.4 ASCII diagram of I²C transaction has misaligned ACK arrows on the second line; the byte boundaries don't line up with the arrow positions. Either fix the alignment, or replace with a clean per-byte table.

### MCU-engineer friendliness
- Add: "On STM32 you'd write the register pointer with `HAL_I2C_Mem_Write(... &addr, 1, ...)` then `HAL_I2C_Master_Receive`. Here `i2c_transfer(adapter, msgs, 2)` does the same two-segment transaction in one kernel call — the second `i2c_msg` with `I2C_M_RD` flag is the read phase."

### Missing examples / figures
- No `i2cdetect -y 1` output shown anywhere in this chapter. Add a 3-line example.
- No `dmesg` after `insmod myeeprom.ko` — only the `cat` output.

### Technical errors
- §65.6 `me_probe` signature uses the legacy two-argument form — see cross-cutting.
- §65.6 `me_remove` returns int — see cross-cutting.
- §65.6 `class_create(THIS_MODULE, "myeeprom")` — see cross-cutting.
- §65.6 `me_fops_read` allocates `u8 kbuf[EEPROM_SIZE]` on the kernel stack (256 B). Fine for this tiny EEPROM, but generalising the pattern to larger AT24C512 would put 64 KB on the stack — disaster. Add a remark.
- §65.6 The ACK-poll loop sends a 1-byte write (`zero = 0`) as the poll. Cleaner is `i2c_smbus_xfer` with a zero-length write (the canonical "address probe"). Functionally equivalent here — but worth a sentence noting the convention used in `at24.c`.
- §65.7 "The mainline `at24` driver registers an nvmem provider. The FEC driver consumes the `mac-address` cell at probe — six bytes from offset 0 become eth0's MAC address." This is *the* killer feature, but the link from "FEC" to "Ethernet MAC" is left implicit. One sentence: "FEC is the iMX6ULL's Ethernet MAC peripheral (Ch 88 onwards in this book) — `fec1`'s `nvmem-cells` property pulls the MAC address from EEPROM at boot."
- §65.8 `awk -F: '{for(i=1;i<=NF;i++) printf "%c", strtonum("0x"$i)}'` is a busybox-awk gotcha — `strtonum` is gawk-specific. On a typical busybox-based iMX6ULL rootfs this command fails silently. Use `printf` + a small shell loop instead.

### Insufficient depth
- The mainline `at24` walk-through skips the multi-bank machinery (large chips that span multiple I²C addresses). The footnote mentions it but doesn't show. Half a paragraph on how `at24_select_regmap` picks the right bank would be welcome.

## Ch66 — SD card and eMMC deep dive

### Readability
- §66.5 opening: "Unlike QSPI and EEPROM (Ch 64/65) — where a from-scratch driver was tractable in ~200 lines — an MMC/SD host controller driver is genuinely a different scale." — overlong em-dash sentence. Suggest: "QSPI and EEPROM each fit in ~200 lines of from-scratch driver. An MMC/SD host controller is a different scale: the SD spec is ~700 pages, the eMMC spec ~400."
- §66.6 "**That's the abstraction**." — bold standalone sentence reads as a slogan; just integrate into the surrounding paragraph.

### MCU-engineer friendliness
- The "trace a single 4-KB read" walkthrough in §66.6 is the highlight of the chapter. Add an MCU mental model: "On STM32 the SDIO peripheral does a similar dance: program CMD register, kick off DMA, wait for transfer-complete IRQ. The big difference in Linux is the layering — block → MMC core → host driver. Each layer adds queueing, scheduling, and error recovery that bare-metal SDIO code doesn't have."

### Missing examples / figures
- Show `cat /proc/mounts` and `lsblk` or `cat /sys/block/mmcblk1/...` after eMMC enumerates — confirms the kernel saw the chip and what partitions are present.
- The "tracing a single 4-KB read" section would benefit from an actual ftrace snippet of output, not just the prose description. Lab #1 says to run ftrace; show the expected trace lines.

### Insufficient depth
- This chapter deliberately doesn't include a from-scratch driver — and explains why (the SD spec is 700 pages). That's the right call given the cookbook-depth requirement *would* technically be violated, but the chapter justifies the omission and replaces it with a layer-tracing walkthrough that is genuinely educational. Author-memory note: this might still trip the "Part VII chapters MUST show driver internals + a from-scratch implementation" rule. Recommend you either (a) keep this exception and add a paragraph in the Part VII introduction listing it explicitly, or (b) write a tiny "host driver skeleton" beyond the 20-line one in §66.6 — say, a 100-line "pretend the host is bit-banged on GPIO" implementation showing how the `mmc_host_ops` callbacks plug in.

### Technical errors
- §66.5 command table has "CMD8 (eMMC) | SEND_EXT_CSD | Read 512-byte EXT_CSD block". CMD8 sent to an eMMC during init is SEND_EXT_CSD, but the same opcode to an SD card is SEND_IF_COND — the row above. The table is correct but the dual-meaning is the kind of detail that catches beginners; add a footnote.
- §66.6 `sdhci_xxx_probe` uses `sdhci_pltfm_init` and `sdhci_get_of_property` — `sdhci_get_of_property` was renamed `sdhci_get_property` in 5.15. Pick one and footnote.
- §66.10 `fio --name=randwr` — the line `write: IOPS=2500, BW=10MiB/s` for HS200 eMMC is plausible for budget eMMC but optimistic for high-end industrial parts. Worth qualifying with "depends heavily on chip; budget consumer eMMC may be 5× slower at random 4k write."

### Other
- §66.7 `mmc extcsd read /dev/mmcblk1` — confirm the user has installed `mmc-utils` (separate package). Add one line.

## Ch67 — Temperature / humidity / pressure

### Readability
- §67.2 "All three are 4–6 pin packages" — fine but the ASCII schematic that follows uses `─╳─` to denote what exactly? Pull-up resistor? Pad? The two leftmost glyphs `┌── A0 ────────►` look like there are extra `┌` brackets that don't close. Clean up the ASCII.
- §67.5 "The chip's calibration coefficients (silicon process variation)" — slightly tense-mismatched. "These coefficients capture per-chip silicon process variation."

### MCU-engineer friendliness
- The §67.4 "compensation formula is in the driver, not the chip" point is exactly the kind of insight an MCU engineer needs. Sharpen: "On an STM32 you'd port Bosch's reference C functions directly into your project; the Linux driver does the same thing — *the math doesn't move into the kernel*, it just lives in the kernel module rather than your application." That tells the reader the Bosch code is identical across all platforms.

### Missing examples / figures
- Show `i2cdetect -y 1` and `i2cdump -y 1 0x76` snippets — the chapter mentions them in the lab but doesn't show what they look like.
- A flowchart of "forced measurement: write ctrl_meas → sleep 10 ms → read 8 bytes → 3 compensation calls → return" would lock in the data path.

### Technical errors
- §67.1 table: "`sht3x.c` (hwmon) + `humidity/shtc1.c`-style IIO not yet for SHT3x in IIO; `sht3x` is hwmon" — actually `drivers/iio/humidity/sht3x.c` exists in modern kernels (added in 6.8). Update.
- §67.5 `mb_probe` legacy two-argument form — see cross-cutting.
- §67.5 `mb_read_calib` uses `i2c_smbus_read_i2c_block_data` for 24 bytes — but the SMBus block-data limit is 32, and *some* I²C controllers reject blocks of 24 bytes (only 32 or smaller multiples). Mostly works on i.MX, but worth flagging.
- §67.5 H4/H5 decoding: `m->H4 = (s16)(((s8)buf[3] << 4) | (buf[4] & 0x0F))` — this is wrong if `buf[4] & 0x0F` has the top nibble overlap with the sign-extended high byte. The Bosch reference code uses unsigned shifts then sign-extends explicitly. Cross-check this byte by byte against datasheet §8.2.
- §67.6 "SHT3x reset = `0x30 41`" — Sensirion's soft-reset command is actually `0x30 A2`. Verify against the datasheet command table.
- §67.7 AHT20 reset is `0xBA` — the datasheet says reset command is `0xBA` (single byte, written without register). OK.
- §67.7 AHT20 packing: "H and T raw values are 20-bit, packed across 5 bytes with a nibble split at byte 3" — text says 5 bytes, but the worked read shows 7 bytes (S, H0, H1, H2/T0, T1, T2, CRC = 7). The pack is 6 data bytes + 1 CRC. Fix the description.
- §67.8 mainline DT for BME280 — `compatible = "bosch,bme280"` is correct, but `CONFIG_BMP280=y` plus `CONFIG_BMP280_I2C=y` — the second now requires `CONFIG_BMP280_I2C=m` to be a separate module, or both `y`. Mention dependency.

### Insufficient depth
- The chapter is excellent — protocol + mainline internals + from-scratch + compensation math + SHT3x/AHT20 conversion sketches. No depth complaints.

### Knowledge prerequisites missing
- "regmap" appears in §67.4 ("decoupled via regmap") — this *was* introduced in Ch 50 per the memory note. Just a forward-ref pointer "(Ch 50)" would help readers who skipped ahead.
- "IIO_VAL_INT_PLUS_MICRO" and "IIO_VAL_INT_PLUS_NANO" appear without explanation; a one-line "scale conventions" callout would help.

## Ch68 — Light & color sensors

### Readability
- §68.2 "The user never sees the lambdaweighting" — "lambda-weighting" with a hyphen (and a word missing space).
- §68.4 ends abruptly after the read_raw snippet; segue into §68.5.

### MCU-engineer friendliness
- Bring across the MCU analogy explicitly: "If you've used a BH1750 on Arduino, you wrote `Wire.write(0x10); delay(180); Wire.requestFrom(...,2);`. Linux's `i2c_smbus_write_byte` + `msleep` + `i2c_master_recv` is the same sequence — but `msleep(180)` actually puts your driver context to sleep, releasing the CPU; on Arduino `delay()` busy-waits."

### Missing examples / figures
- Show actual `cat /sys/.../in_illuminance_raw` and `_scale` for a few lighting scenarios (dark, indoor, sunny window) — the chapter only shows two readings.
- No physical wiring diagram for the BH1750. The chip has VCC, GND, SDA, SCL, ADDR (and DVI on some breakouts). Show it.

### Technical errors
- §68.5 `mb_probe` two-argument legacy form — see cross-cutting.
- §68.5 `mb_read_raw` returns `IIO_VAL_INT` for `_PROCESSED` after computing `((u32)count * 1000) / 12 * 10` — but the IIO `_processed` ABI expects the value in the *natural unit* (lx) and `IIO_VAL_INT_PLUS_MICRO` for fractions. Reporting `lux × 1000` as `IIO_VAL_INT` makes user-space think it's reading 410000 lx, not 410 lx. The mainline driver uses `_processed` returning lx (an integer), not millilux. Re-check the unit.
- §68.5 `mb_remove` returns 0 (int) — see cross-cutting.
- §68.6 TSL2561 formula coefficients (`0.0304`, `0.062`, etc.) — these come from the datasheet's "CS package" formulation. The "T/FN package" has different coefficients. Most modules sold are T-package; clarify.
- §68.7 "VEML7700 has 6 integration times (25/50/100/200/400/800 ms) and 4 gains" — datasheet actually lists `IT = 25/50/100/200/400/800` × `gain = 1, 2, 1/4, 1/8`. The integration values and gains both list correctly; just worth a footnote on which combinations are valid (not all 6×4 work due to internal saturation).

### Other
- Lab #4 "expose `_integration_time` as a writable IIO attribute. Verify writing 1 / 0.5 / 2 changes the effective integration time." — but BH1750's integration is fixed at "L-mode 16 ms / H-mode 120 ms / H-mode2 240 ms" — there's no continuous scaling. The MTREG trim varies sensitivity, not integration time. Re-word the lab.

## Ch69 — Air quality / gas / particulate matter

### Readability
- §69 intro "**NDIR is physics; metal-oxide is correlation; laser scatter is counting**" — strong and memorable. Keep.
- §69.4 transitions abruptly between "user-space: `cat /sys/.../in_concentration_co2_input` returns eCO₂ ppm" and the next paragraph. Add a one-line bridge.

### MCU-engineer friendliness
- For the PMS5003 SerDev section: tell the MCU reader that SerDev is essentially a "kernel UART line discipline" with cleaner API — equivalent to "I used to call `HAL_UART_Receive_IT` and accumulate bytes in a callback; SerDev's `receive_buf` is the same callback, just with kernel context."

### Missing examples / figures
- The PMS5003 wiring diagram is missing. Show: PMS5003 TX → iMX6ULL UART2_RX, common ground, 5 V supply (PMS5003 cannot tolerate 3.3 V supply but its TX is 3.3 V CMOS compatible). The 5 V supply detail catches people.
- Show the actual UART2 DT node and which iMX6ULL pads back it. Cross-reference IOMUX.

### Technical errors
- §69.3 SCD30 float decoding: `bits = (raw[0]<<24) | (raw[1]<<16) | (raw[3]<<8) | raw[4];` — correct in that it skips the CRC bytes at indices 2 and 5. Cast `*(float*)&bits` is technically undefined behaviour by strict aliasing; use `memcpy(&f, &bits, 4)` or a union. Production drivers do this; mention it.
- §69.4 CCS811 reset register address: "0xFF SW_RESET" — wait, the chapter says "0xB0 SW_RESET" in the same table. Pick one. Datasheet: SW_RESET is at register 0xFF; 0xB0 is BASELINE. Cross-check.
- §69.4 "Wait ≥ 70 ms" after power-on for CCS811 — actually datasheet specifies ≥ 1 second (boot time). The 70 ms figure is the *minimum delay between writes*, not the boot delay. Verify.
- §69.5 `mp_probe` for serdev — `serdev_device_open` returns 0 on success; missing close-on-error path. devm doesn't auto-close serdev unless you use `devm_serdev_device_open` (kernel 5.5+). Either use the devm variant or add explicit cleanup.
- §69.5 PMS5003 frame field at offset 30 is the checksum — and the checksum is *sum of bytes 0..29* per the manual, which the code matches. Good. But you should mention that the frame's "length" field at offset 2 is the *remaining* bytes count, not the total — useful for handling other PMSxx variants with different sizes.

### Insufficient depth
- The CCS811 section says "writes `0xF4` (no data) to switch to app mode" but doesn't show the actual I²C transaction (it's a one-byte write with no register address — special form). Demonstrate.
- The SerDev section is treated almost too lightly — it's pedagogically the most interesting framework introduced here. Spend another half-page on what `serdev_device_set_client_ops` does and how the kernel knows when bytes arrive (versus polling).

## Ch70 — I²C IMUs

### Readability
- §70.4 "1000/s = unacceptable" reads as a stat aside in the middle of a sentence. Move to a parenthetical or break out. Also: "30 µs per sysfs read × 6 axes × 1000 Hz = 18 % of one CPU just on the syscall overhead" — the arithmetic is `30e-6 × 6 × 1000 = 0.18`, i.e. 18 %. Good. But "1000 Hz" reads as if it's the *per-axis* rate; clarify that's the full sample rate.
- §70.10 Madgwick C-snippet is *almost* C but uses operator overloading (`q + q`, `q * 0.5`) — non-native readers will assume that's real C. Either use explicit function calls (`quat_add`, `quat_scale`) or label the snippet "pseudocode".

### MCU-engineer friendliness
- The "30 µs per sysfs syscall" budgeting is gold. Add an explicit comparison: "On STM32 you'd just write a tight ISR reading the FIFO into a circular buffer; in Linux that 'tight ISR' is the kernel scheduler waking your trigger-handler thread — same effect, more layers."

### Missing examples / figures
- Show actual `dmesg` after probe (the IIO device assignment, trigger registration, IRQ allocation).
- Show what the captured `imu.bin` looks like — a hex dump of one sample to make the byte layout concrete.
- No physical wiring diagram. INT pin → which GPIO, what pull-up?

### Insufficient depth
- This chapter is the longest and most thorough in the part. Excellent. Just confirm the IIO buffer / trigger explanation in §70.4 actually matches what Part VI introduced — if Part VI's IIO chapter is light on triggers, expand here. The "Two-stage IRQ path for hardware trigger" passage is a good place to point out where the threaded-IRQ pattern fits (Ch 43 per cross-reference).

### Technical errors
- §70.1 table: "Mainline driver | `inv_mpu6050_*.c` family | same | same" — the ICM-20948 mainline support is in `drivers/iio/imu/inv_mpu6050/` but registered as a *new* `inv_icm20948` family in recent kernels (formerly `inv_mpu6050` with bank quirks). Slight historical mismatch.
- §70.5 `inv_mpu_core_probe` skeleton uses `devm_iio_triggered_buffer_setup(...)` — pass the function names but skip the actual function signature; OK as illustrative.
- §70.5 channel macros: `INV_MPU6050_CHAN` defines `scan_type = { .endianness = IIO_BE }` — correct for MPU6050. ICM-42688 outputs *little-endian* — a footnote helps here, especially since the SPI IMU chapter (Ch71) makes a big deal of this.
- §70.6 `mp_read_raw` does `mp_read_accel_axis(m, chan->scan_index - 1, &raw)` — `scan_index` for X is 1, so `1-1 = 0` ⇒ X reg base + 0 = ACCEL_X. OK. But the index math is fragile: if you ever rearrange the channel table, the off-by-one breaks. Better to use `chan->channel2` (`IIO_MOD_X/Y/Z`) and a switch.
- §70.6 `mp_probe` legacy two-arg form — see cross-cutting.
- §70.6 scale calculation: "Accel: 1/16384 g/LSB = 9.80665 / 16384 m/s² per LSB ≈ 0.000598" — yes, 9.80665/16384 = 5.985e-4. So `*val2 = 598` would be `598e-6 = 5.98e-4` — correct to 0.1 %. Just note that mainline drivers usually express this with more precision (`*val2 = 598407`).

### Knowledge prerequisites missing
- "hrtimer" trigger — readers may not know that has to be enabled via `CONFIG_IIO_HRTIMER_TRIGGER=y` and instantiated via configfs (Ch83 in TOC). One-line forward-ref.

## Ch71 — SPI IMUs

### Readability
- §71 intro is solid. §71.3 "The 'MB' (multi-byte) flag tells the chip to auto-increment the register pointer between bytes — efficient way to dump consecutive registers." → fine.

### MCU-engineer friendliness
- Add: "On STM32 you'd write `*(uint8_t*)&SPI->DR = 0xC0 | reg; while(!(SPI->SR & RXNE)); discard; ...` for each byte. Linux's `spi_message` builds the whole sequence and submits to a kernel thread that does the same — but with DMA, IRQs, and per-CS configuration handled for you."

### Missing examples / figures
- Wiring diagram for ADXL345 with IRQ pin to a GPIO. Pull-up resistor needed? Active-high or active-low IRQ?
- Show `cat /proc/interrupts` before/after — to demonstrate the IRQ rate dropping ~10× with watermark enabled (lab #4 mentions this without showing target numbers).

### Insufficient depth
- The "FIFO + watermark" pattern is the gem of the chapter. Make sure the reader sees, in code, the *full* round-trip: chip configured to assert INT on FIFO ≥ N; kernel `request_threaded_irq`; IRQ thread reads FIFO_STATUS, drains N × 6 bytes, clears the IRQ. The chapter has this but the linkage between `INT_ENABLE = 0x02` and "IRQ now fires on watermark" is implicit. Spell it out.

### Technical errors
- §71.4 driver fragment uses `devm_request_threaded_irq(dev, irq, NULL, adxl345_irq_handler, IRQF_TRIGGER_HIGH | IRQF_ONESHOT, name, indio_dev);` — that's correct (NULL primary, secondary on thread). Good.
- §71.5 `ma_probe` `spi->mode = SPI_MODE_3` — correct for ADXL345. Then `spi_setup(spi);` — but the DT also specifies `spi-cpha` and `spi-cpol`. Either trust the DT and remove the explicit mode assignment, or trust the explicit one — having both with conflicting intent is the kind of thing that catches people. (Here they agree, but flag the pattern.)
- §71.5 `devm_iio_triggered_buffer_setup(&spi->dev, idev, NULL, NULL, NULL);` — all-NULL handlers. See cross-cutting. Add a comment: "we push samples from the watermark IRQ; this call just registers the buffer infrastructure."
- §71.5 endianness: `ma_read_axis` reads `*out = (s16)(buf[0] | (buf[1] << 8));` — ADXL345 outputs *little-endian* (low byte at lower address). The `IIO_LE` in scan_type matches. Verify against datasheet — ADXL345 datasheet does say LSB-first byte order. OK.
- §71.10 pitfall "ADXL345 is mode 3 (CPOL=1, CPHA=1)" — datasheet confirms mode 3. OK.

### Other
- `INV_MPU6050_CHAN` macro was reused across chapters but the name suggests it's MPU-specific. In Ch71 it's `ACCEL_CH`/`GYRO_CH`. Fine.

## Ch72 — Distance & proximity

### Readability
- §72.1 sub-bullets read naturally.
- §72.6 "Bottom line: don't ship HC-SR04 connected to Linux GPIO" — perfect blunt advice. The whole §72.6 is one of the best "honest about Linux limitations" passages in the book.

### MCU-engineer friendliness
- The HC-SR04 discussion is genuinely useful — but the comparison to "what you'd do on STM32" (capture-compare on a timer input) is implicit. Spell it out: "On STM32 you'd configure TIM2_CH1 in input-capture mode, get an IRQ on rising-then-falling edges, read the capture register difference — ±1 µs accuracy with zero CPU. Linux's GPIO IRQ + ktime has 100× worse latency."

### Missing examples / figures
- No wiring diagram for VL53L0X. The chip has XSHUT and INT pins — wire them. Also the I²C pull-ups.
- Show `dmesg | grep vl53` after the from-scratch driver loads.

### Technical errors
- §72.4 mainline driver: "ID register 0xC0 — Always 0xEE (or 0xEEAA depending on rev)" — VL53L0X model-ID at register 0xC0 is one byte 0xEE; the "0xEEAA" might be referring to the 16-bit MODEL_ID at 0xC0:0xC1 read as a word (0xEE 0xAA). Clarify.
- §72.5 `myvl53l0x` minimal tuning blob: "{0x70, 0x04}, {0x71, 0x08}, /* set measurement-timing-budget for ~33 ms */" — the official ST API sets timing budget via much more elaborate VHV+phase calibration registers, not these two. The blob shown will probably produce *some* reading but will not give the ±3 % accuracy quoted in §72.1 — the reader's measurements will be off by 5–10 %. Be more upfront: this is a "smoke-test" tuning, not a calibrated one.
- §72.5 `mv_probe` legacy two-arg form.
- §72.6 HC-SR04 driver fragment busy-waits with `cpu_relax()` inside `gpiod_get_value` — but doesn't disable preemption. A scheduler tick during the wait will easily cost 100+ µs. Either add `local_irq_disable()` around the timing-critical loop (matching the technique used by `w1-gpio` in Ch77), or be explicit that this driver alone doesn't bring the accuracy claim — only RT-kernel does.
- §72.7 GP2Y0A on i.MX6ULL ADC — i.MX6ULL has 2 ADC blocks (ADC1, ADC2) per the reference manual, each with 10 input channels (ADC1_IN0..ADC1_IN9). Not "2 channels total". Update §72.7 phrasing.

### Other
- Lab #4 says to use `gpiomon` — but libgpiod versioning matters here (`gpiomon` was renamed in libgpiod 2.0). Note the version.

## Ch73 — Magnetometer / compass

### Readability
- §73.1 trap callout "If your 'HMC5883L' doesn't probe at 0x1E, try QMC5883L at 0x0D" — superb concrete pitfall. Keep.
- §73.7 "Phase 1: collect ~1000 samples while the user rotates the sensor" — slot in "the user rotates the sensor in 3D, ideally covering as much of the imaginary sphere around it as possible."

### MCU-engineer friendliness
- Calibration is universal across MCU and Linux. Helpful explicit note: "This calibration script runs in user-space because IIO drivers should not bake board-specific magnetic environment into the kernel. On an MCU you'd do the same fit in your application code."

### Missing examples / figures
- A wiring diagram for QMC5883L on I²C1 — same as the other I²C sensors but the chapter never shows one.
- A scatter plot (ASCII or callout to a generated image) of "raw mag data on uncalibrated chip" versus "after hard-iron correction" would be the single most impactful figure in the chapter.

### Technical errors
- §73.4 QMC5883L bring-up: "Write 0x0B = 0x01: set the 'period' register (mandatory; chip won't work without it)." — datasheet says SET/RESET period register at 0x0B should be 0x01 for typical use; this is correct.
- §73.6 `mq_probe` legacy two-arg form.
- §73.6 `mq_read_axes` uses `i2c_smbus_read_i2c_block_data(..., 6, buf)` from REG_DATA = 0x00. QMC5883L data registers are 0x00..0x05 — works. Just note that some I²C controllers refuse a block-read at register 0 (interprets as length byte in SMBus block-read semantics) — i.MX6ULL is fine.
- §73.6 scale: "±8 G range, 16-bit signed ⇒ 32768 LSB / 8 G = 4096 LSB/G. Convert to Tesla: 1 G = 100 µT, so 1 LSB = 100/4096 µT" → 24.4 nT/LSB = `*val2 = 24414` with IIO_VAL_INT_PLUS_NANO. Verify against the mainline `qmc5883.c` scale convention — it might publish scale in Gauss not Tesla.

### Insufficient depth
- §73.7 calibration math is intentionally simplified — author calls it out. Could add a 10-line "proper" ellipsoid-fit pseudocode (the eigen-decomposition step) so the reader sees what the simplified version is approximating.

## Ch74 — Hall-effect & rotary position

### Readability
- §74.2 "The magnet must be: ..." bullet list is good.
- §74.5 ends at "ADC-based. For 'is there a magnet nearby?' (lid open/closed, latch position): A1324 + ADC + a threshold is enough." — fine but feels a bit terse compared to the AS5048 walkthrough.

### MCU-engineer friendliness
- Two-frame SPI sequence is an MCU concept readers will already know; just say "if you've used the AS5048 from STM32, the same two-frame trick applies — first transaction sends the command, the chip's response appears in the *next* transaction."

### Missing examples / figures
- Show a wiring diagram. AS5048A on ECSPI3, INT pin connected to a GPIO? Datasheet doesn't have a data-ready INT pin (the chip has ABI/UVW outputs and a PWM output); clarify.
- Show what the magnitude register reads with no magnet vs with the correct magnet at 1 mm — concrete numbers tell the reader what "good" looks like.

### Technical errors
- §74.3 "Each SPI frame is 16 bits: bit 15 = parity (even parity over remaining 15 bits)" — AS5048A actually uses even parity over bits 14:0 (the 15 lower bits), and bit 15 is the parity bit itself. The text says exactly that. OK.
- §74.4 `ma_probe` SPI mode 1 — datasheet says CPOL=0, CPHA=1, which is mode 1. OK.
- §74.4 `ma_read_reg`: the second read of MAGNITUDE in probe to "get the actual answer (first frame is throwaway)" — yes, two-frame protocol. But this means probe issues 4 SPI transactions where 2 would do; it's clearer to do "issue cmd, then issue cmd again" *both* explicitly named "first is throwaway." Cosmetic.
- §74.4 scale: "14-bit = 16384 LSB per full turn = 2π rad. 1 LSB = 2π / 16384 ≈ 383.5 µrad." → `*val2 = 383495` for IIO_VAL_INT_PLUS_NANO ⇒ 383.495 µrad/LSB. 2π / 16384 = 383,495.18 nrad. OK.
- §74.6 "Mainline driver: `drivers/iio/position/iqs62x.c` covers some Iqs sensors; TLE5012 has out-of-tree drivers from Infineon." — `iqs62x` is unrelated to TLE5012. Either remove the misleading sentence or replace with the correct mainline status.
- §74.7 "`drivers/iio/position/as5048.c` is the mainline AS5048 driver" — the mainline file is `drivers/iio/position/as5011.c` and the AS5048 driver is `drivers/iio/position/as5048a.c` historically. Check current upstream.

### Other
- §74.10 last pitfall mentions "Hot-plug/start-up race" — phrase it as "AS5048 boot delay" for clarity; "hot-plug" suggests removable bus device.

## Ch75 — Current & power monitoring

### Readability
- §75.1 column "I²C clock | 100 kHz / 400 kHz / 2.94 MHz (HS) | up to 2.94 MHz | up to 2.94 MHz" — 2.94 MHz is the High-speed-mode max. i.MX6ULL I²C controllers don't do HS-mode — they max out at 400 kHz Fast-mode. Add a footnote: "i.MX6ULL drives the bus at 100/400 kHz; the 2.94 MHz figure is the chip's max with an HS-mode-capable controller."
- §75.3 "Calibration = trunc(0.04096 / (Current_LSB × R_shunt))" — formula text and worked example are excellent. Keep.

### MCU-engineer friendliness
- The calibration-register-is-the-trap insight is a classic MCU gotcha (anyone who's used INA219 from Arduino has hit it). Acknowledge: "This is the exact same trap Arduino INA219 users hit; the difference is on Linux you discover it via `cat curr1_input` reading 0 forever, instead of `Serial.println` reading 0 forever."

### Missing examples / figures
- The schematic in §75.2 is *almost* useful but the ASCII art has issues — the V+, V- arrows don't visually attach to anything. Redraw as a cleaner block diagram.

### Technical errors
- §75.4 `ina2xx_config` table — `[ina226]`'s `calibration_value = 2048`: datasheet INA226 calibration formula is `Cal = 0.00512 / (Current_LSB × R_shunt)`. Confirm the magic constant against datasheet.
- §75.5 `mi_probe` legacy two-arg form.
- §75.5 `mi_probe` references `&m->client->client_dev` — there's no `client_dev` member; it's `&m->client->dev`. Compilation error.
- §75.5 calibration math: "cal = 40960000u / (m->current_lsb_uA * (m->shunt_uohms / 1000))" — for shunt_uohms = 25000 and current_lsb_uA = 100: `40960000 / (100 * 25) = 16384`. OK. But the `shunt_uohms / 1000` integer divide loses precision for shunts not divisible by 1000 (e.g., 1500 µΩ ⇒ 1 ⇒ wrong). Use a 64-bit do_div() pattern or document the assumed precision.
- §75.5 hwmon attribute `in0_input` for shunt voltage returns mV — `uV / 1000` truncates microvolts of detail. For a ~3 mV shunt voltage, the result is "3" — that's 33 % rounding error. Either return microvolts (which `in0_input` doesn't quite mean per hwmon convention) or round properly.

### Insufficient depth
- The hwmon vs IIO sidebar (§75.6) is a key insight the rest of the book has been ducking. Keep it. Could add: "if you implemented this same chip in IIO, what would change?" — answer is the framework name and the attribute layout, but the per-register reading code is identical.

## Ch76 — Battery fuel gauge + charger

### Readability
- §76.2 "voltage isn't linear with SoC" — solid pedagogically. The "discharge curve" is well-described in prose. An ASCII chart would make it click instantly.

### MCU-engineer friendliness
- "On STM32 you might wire a voltage divider to the ADC and read battery voltage directly. That gives you the cell's open-circuit voltage *only when there's no load* — under load the voltage drops by I × R_internal, which on a Li-ion cell looks identical to 'low battery'. Fuel gauges solve this; ADC dividers don't." That's the kind of MCU-to-Linux bridge.

### Missing examples / figures
- Wiring diagram: MAX17048 (just I²C + cell). Trivial but include for consistency.
- ASCII discharge curve: 4.2 V at 100 % falling through 3.7 V at 50 % to 3.4 V at 10 %.

### Technical errors
- §76.3 SoC raw encoding: "bits 15:8 = %, bits 7:0 = fractional 256ths" — correct per MAX17048 datasheet.
- §76.5 `mm_probe` legacy two-arg form.
- §76.5 `mm_read_reg(m, REG_VERSION, &version)` returns the value via `i2c_smbus_read_word_swapped`; the version check `(version & 0xFFF0) != 0x0010` — MAX17048 datasheet says version is 0x0010 to 0x001F range. Verify the mask matches the actual silicon-id range.
- §76.5 `power_supply_register` uses `devm_power_supply_register` — correct.
- §76.6 "Charge current is set by `R_PROG`: `I_charge = 1200 / R_prog`" — TP4056 datasheet equation is `I_BAT = V_PROG / R_PROG × 1200` where V_PROG = 1.0 V typical, so `I = 1200 / R_PROG` with R in ohms gives I in mA. So R = 1.2 kΩ ⇒ 1000 mA, R = 2.4 kΩ ⇒ 500 mA. The text "R = 1.2 kΩ → 1 A; R = 2.4 kΩ → 500 mA" matches. OK. But mention units clearly: "R in kΩ, I in mA, or equivalently R in Ω with I in A."

### Insufficient depth
- The chapter only implements PRESENT/VOLTAGE_NOW/CAPACITY/STATUS (and STATUS is stubbed). Reading CRATE (register 0x16) to derive STATUS = CHARGING/DISCHARGING is straightforward and would round out the driver. The author explicitly notes this in the closing paragraph; consider just doing it inline rather than as homework.

## Ch77 — 1-Wire sensors

### Readability
- §77.6 "Bottom line: if you see DHT22 in someone's product schematic, suggest a swap to SHT3x." — great closing line.
- §77.4 "imaginary family — say, a custom sensor with family code 0xA5" — fine, but flag explicitly that 0xA5 is *not* a registered Maxim family code (real ones are listed in Maxim AN155). The reader could otherwise accidentally claim an in-use code.

### MCU-engineer friendliness
- "On STM32 you'd bit-bang the same timing in a tight loop with DWT cycle counter for sub-µs timing. Linux's `udelay` + `local_irq_disable` is the same idea — but interrupts off in Linux is more *consequential* than on STM32 (no other RTOS task runs)."

### Missing examples / figures
- Show the wiring diagram: GPIO4_IO14 ↔ 4.7 kΩ to 3.3 V ↔ DS18B20 DQ; DS18B20 VDD and GND.
- Show the actual SEARCH-ROM dance — even just one cycle — would deepen the "binary-tree enumeration" claim.

### Technical errors
- §77.3 `w1-gpio` `w1_gpio_read_bit` timing: "Pull low for ~6 µs / sample at 15 µs / finish 55 µs" — close to standard 1-Wire spec (Maxim AN126 gives "tLOW1 ≤ 15 µs, tRDV = 15 µs, tRELEASE ≈ 45 µs total slot = 60 µs"). Numbers are slightly off but within tolerance. OK as illustrative.
- §77.3 says "wraps the bit operations in `local_irq_disable()` / `local_irq_enable()` around the timing-critical region" — actually the mainline `w1-gpio.c` does *not* unconditionally disable IRQs; it relies on `udelay` accuracy plus 1-Wire's timing tolerance. The `slaves/w1_therm.c` may use specific atomic windows. Verify.
- §77.4 `w1_reset_select_slave(sl)` returns 0 on success, but the doc check `if (w1_reset_select_slave(sl)) { ... return -EIO; }` treats non-zero as failure — that means "returns 0 on success" semantic, which matches `w1.h`. OK but inverts the natural reading.

### Other
- DS18B20 temperature decode: "temp_C = temp_raw / 16.0 (signed!)" — yes, 16-bit signed with 4 fractional bits. Correct.

## Ch78 — MEMS microphones

### Readability
- §78.1 table "PDM | needs the SoC's PDM-decoder hardware. i.MX6ULL's SAI has *only I²S*, no native PDM. So PDM mics are awkward on i.MX6ULL — skip." — straight talk, good.
- §78.4 "There's no I²C control — the mic has no registers. The wires alone (BCLK, LRCLK, SD, LR-select strap) determine its behavior." — excellent framing.

### MCU-engineer friendliness
- "On STM32 with the SAI peripheral, you'd use HAL_SAI_Receive_DMA into a circular buffer. Linux's SAI driver + SDMA does exactly the same — but ALSA owns the ring buffer, and user-space `arecord` reads from it via ioctl/mmap. The DMA hardware doesn't care which layer is on top."

### Missing examples / figures
- The data-flow box in §78.5 is good; consider a parallel "where the kernel symbols live" diagram (so the reader knows `fsl_sai.c`, `dmic.c`, `simple-card.c` correspond to each layer).
- Show the SAI2 IOMUX pin assignments from the reference manual (SAI2_TX_BCLK at which pad, SAI2_TX_SYNC at which pad — these are the user's actual schematic decisions).
- Show actual `arecord` output for `arecord -l` and `cat /proc/asound/cards` so the reader knows what success looks like.

### Insufficient depth
- The chapter intentionally skips writing a codec driver for the INMP441 because *there is no chip to drive*. That's pedagogically correct — but per the cookbook-depth requirement, the chapter should still show "what writing a machine driver looks like" beyond the 30-line sketch. The §78.6 sketch *is* mostly that, but it could be a complete, compilable example with the `module_platform_driver` boilerplate, even if it duplicates `simple-audio-card`.

### Technical errors
- §78.4 DT `assigned-clock-rates = <0>, <24576000>;` — the IMX6UL_CLK_SAI2_SEL doesn't take a rate (it's a mux), so `<0>` is correct as a "don't change". The MCLK rate 24.576 MHz is correct for 48 kHz audio. OK.
- §78.4 `bitclock-master = <&cpu_dai>; frame-master = <&cpu_dai>;` — these properties were renamed in newer kernels to `bitclock-master = <&cpu>` style with phandles to the appropriate child. The DT shown is correct for current `simple-card.c`. Verify in 6.x.
- §78.4 `dmic_codec` node uses `compatible = "dmic-codec"`. Mainline `sound/soc/codecs/dmic.c` registers a platform driver for that compatible. Confirm `CONFIG_SND_SOC_DMIC=y` is required (the §78.9 pitfall already notes this).

### Other
- Lab #8 "FFT in user-space" is a great teaser but assumes Python availability — many minimal iMX6ULL rootfs don't ship Python. Note this or provide a tiny C alternative.

## Ch79 — Health sensors

### Readability
- §79 intro reads well. "Without good signal processing, the readings are garbage — and the chip can't fix bad processing." Strong.
- §79.6 Python sketch is clear.

### MCU-engineer friendliness
- "Most MAX30102 Arduino examples do their HR/SpO₂ math on-MCU. On Linux you can do the same — but for a one-off product, doing the DSP in Python or NumPy in user-space is far faster to iterate on."

### Missing examples / figures
- Show the IRQ wiring (the chip's INT pin to which GPIO).
- An ASCII waveform of "PPG signal: DC pedestal + small AC ripple" would crystallize §79.2 way better than the prose.

### Technical errors
- §79.5 `mh_probe` legacy two-arg form.
- §79.5 `devm_iio_triggered_buffer_setup(..., NULL, NULL, NULL)` — same as Ch71, all-NULL handlers; the chip's IRQ pushes samples directly. Document this.
- §79.5 18-bit packing: `((buf[0] << 16) | (buf[1] << 8) | buf[2]) & 0x3FFFF` — the mask `0x3FFFF` keeps low 18 bits. But the MAX30102 outputs already zero the top 6 bits when ADC range is 18-bit; if range is 17-bit/16-bit (configurable), the field is different. Note dependence on §79.3 step 6's `SPO2_CONFIG` value.
- §79.5 `mh_read_raw` "drain all but the latest, return latest" — this is acceptable for sysfs reads but has poor semantics: each sysfs read silently discards 30+ samples that the buffered-capture path *would* have wanted. If the buffer is enabled, both paths conflict. Caveat the reader.
- §79.6 SpO₂ formula "110 - 25·R" — the original literature uses different fits (Maxim AN6409 gives a piecewise formula). The 110-25R approximation is roughly right for R ≈ 0.4–1.0 (95–100 % SpO₂) but breaks badly outside that range. Mention the limitation.

### Other
- §79.4 "There is no IIO mainline driver for MAX30100/30102 as of this writing (early 2026)" — there is `drivers/iio/health/max30100.c` and `max30102.c` already mainline since 4.x. Update the chapter intro and §79.4.

## Ch80 — External ADCs

### Readability
- §80.1 table is well structured; "ENOB" column needs a one-line definition somewhere (probably § "Why not use the SoC's internal ADC?") for non-EE readers.
- §80.3 "ADS1115 has just 4 registers" — clear.
- §80.9 "Ratiometric measurement — the noise-cancellation trick" — keep this section; it's exactly the kind of physical insight that separates a textbook ADC writer from a competent engineer.

### MCU-engineer friendliness
- "On STM32 you'd use the internal ADC with DMA-circular mode for continuous capture. ADS1115 over I²C is much slower but vastly more accurate — the trade-off is the same one as MCU-onboard vs external ADC, just with kernel layers in the middle."

### Missing examples / figures
- Wiring: ADS1115 ADDR pin straps (4 addresses available), the AIN0..AIN3 inputs.
- Show what `cat /sys/.../in_voltage_scale_available` looks like for the mainline driver (a list of PGA scales) — readers don't always know that `_available` files exist.

### Technical errors
- §80.2 "The i.MX6ULL has 2× 12-bit SAR ADCs" — correct: ADC1 and ADC2 each are 12-bit SAR. But then "2 channels: not enough for a multi-sensor product" — wrong. Each ADC has up to 10 external input channels (ADC1_IN0..ADC1_IN9 per the reference manual at line 22435+). The constraint is the *number of ADC blocks*, not channels. Rewrite as "limited to two simultaneous conversions; each ADC has multiple input pins but they're muxed."
- §80.5 `ma_probe` legacy two-arg form.
- §80.5 `ma_read_channel` OS-bit polling logic comment: "note: OS reads 1 when conversion is DONE in single-shot; check datasheet" — the chapter author *correctly* flags this in the §80.11 pitfall, but the polling loop `while (!(status & CFG_OS_SINGLE) && retries--)` matches "1 = done" reading. Good.
- §80.5 scale: "±2.048 V over 2^15 = 62.5 µV/LSB" → `*val2 = 62500` with `IIO_VAL_INT_PLUS_NANO` ⇒ 62500 nV/LSB = 62.5 µV/LSB. Correct.
- §80.6 MCP3008 protocol is correct. The vref-supply phrase "(ratiometric: scale = vref / 1024)" — MCP3008 is 10-bit ⇒ 1024 codes ⇒ scale = vref / 1024 V/LSB. Correct.
- §80.8 AD7606 "16-bit, 8-channel simultaneous-sampling" — verify max sample rate per channel. AD7606 datasheet says 200 kSPS *per channel* with all 8 sampling simultaneously, total 1.6 MSPS aggregate. The table at §80.1 "200 kSPS/ch (all at once)" matches. OK.

### Other
- §80.9 ratiometric explanation could include an explicit example using HX711 (which is *literally* a 24-bit ratiometric ADC chip for load cells) — that's the chip readers will actually buy if they want a scale. HX711 is mentioned in passing; expand it.

## Ch81 — External DACs + clock generators

### Readability
- §81.1 table is fine. §81.3 IIO output channels primer is well-placed.
- §81.6 clk-framework section is dense — could use one more paragraph of orientation. "The kernel clock tree (Ch 13, Ch 25) is a graph of clocks where each clock has a parent. SoC clocks plug in at the top; the Si5351 adds *external* nodes consumers can use just like internal ones."

### MCU-engineer friendliness
- The DAC IIO output channel is a new concept for the IIO mental model. Bridge it: "If `read_raw` is 'kernel reading from sensor', `write_raw` is 'kernel pushing to actuator'. Same API, opposite direction." That's the one-line summary.
- For Si5351: "On STM32 you'd configure the on-chip PLL via RCC registers. An external Si5351 does the same job for external chips that need a non-standard clock; the Linux clk framework just makes the Si5351's outputs look like any other clock in the tree."

### Missing examples / figures
- Wiring diagram for MCP4725 — show VDD, GND, SDA, SCL, A0 (address-select), VOUT.
- Show the actual `cat /sys/kernel/debug/clk/clk_summary` output (a few representative lines) for an Si5351 — most readers will not have seen `clk_summary` before. Note `CONFIG_DEBUG_FS=y` and `mount -t debugfs none /sys/kernel/debug` requirements.

### Technical errors
- §81.4 `mc_probe` legacy two-arg form.
- §81.4 `mc_set` fast-write packing: `buf[0] = (value >> 8) & 0x0F; buf[1] = value & 0xFF;` — datasheet figure 6-2 (fast-write) shows byte0 = bits PD1,PD0,D11,D10,D9,D8 in low 6 bits, with top two bits being command-mode 00. For "normal mode" (no power-down), PD1=PD0=0. So `buf[0] = (value >> 8) & 0x0F` does write D11..D8 in low nibble and zeros for PD; that matches "normal mode fast write." OK. But the macro semantics is fragile — datasheet table 6-2 makes the bit layout clear; the chapter should reproduce it.
- §81.5 AD5663 SPI frame: "24-bit SPI frame: 8 command/address bits + 16 data bits" — actually datasheet says 24-bit frame with 6 bits reserved + 3 command + 3 address + 16 data + extra. Verify.
- §81.6 Si5351 — DT example uses `silabs,multisynth-source` and `silabs,clock-source` — verify against current binding (`Documentation/devicetree/bindings/clock/silabs,si5351.yaml`).
- §81.6 clk-framework reference: "the same framework that manages the SoC's internal clock tree (Ch 13, Ch 25)" — verify those chapter numbers cover the clk framework introduction (per current TOC).
- §81.6 example "f_out = f_xtal × (PLL_mult) / (output_divider)" — Si5351 actually has *two* dividers (Multisynth + R-divider) plus the PLL fractional divide. The simplified expression is OK as an introduction but flag the simplification.

### Other
- §81.7 lab #4 "Try writing to EEPROM via the mainline driver's persistence" — confirm the mainline `mcp4725.c` does expose EEPROM-write via a sysfs attribute. As of 6.x it does, via the `_powerdown_mode` and writing the persistent-flag DT property. Reader will likely struggle without the exact attribute name.
- §81.8 last pitfall "Clock consumer ordering ... `-EPROBE_DEFER`" — good. Add: "the kernel retries deferred probes after every successful probe of any other driver, so eventual success is the norm; but circular dependencies (A waits on B, B waits on A) deadlock — verify with `cat /sys/kernel/debug/devices_deferred`."
