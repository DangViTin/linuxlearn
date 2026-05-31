---
chapter: 66
title: SD card and eMMC deep dive
part: VII — Device cookbook
estimated_pages: 16
status: draft
---

# Chapter 66 — SD card and eMMC deep dive

> **What:** the **MMC subsystem** that backs both SD cards and eMMC. Speed modes (DS, HS, HS200, HS400, SDR104), the **EXT_CSD** register (the eMMC's metadata block), boot partitions, RPMB, wear monitoring, and the "removable card in a production product" antipattern. Three configurations compared: **µSD on a card slot**, **soldered eMMC at HS200**, **soldered eMMC with secure boot via RPMB**.
> **Why:** for most i.MX6ULL products with > 32 MB storage need, the choice is "SD or eMMC." Picking wrong dooms you to field failures or wasted engineering. eMMC is the right choice for production; SD is fine for dev boards. This chapter is mostly the why behind that statement, plus the bring-up + monitoring details.
> **Compare**: removable SD (cheap, accessible, dies first), soldered eMMC HS200 (200 MB/s, 5-year industrial life), eMMC with RPMB (~10 % overhead, replay-protected for secure boot).

## 66.1  SD card vs eMMC — the production reality

SD cards die. Often. In ways that surprise engineers used to flash chips:

- **No wear levelling guarantees**. The card's controller does *some* — but cheap cards (the kind whose price you negotiate down) skimp on it.
- **Power-loss corruption**. A write in progress when power drops can corrupt the entire FAT/ext4 metadata, not just the in-flight sector. eMMC has better resilience (built-in caching with battery backup in some packages), but SD cards are notoriously fragile.
- **Temperature**. Industrial-grade SD exists (-40 to +85 °C) but consumer ones spec 0–70.
- **Counterfeit**. The single biggest reliability issue. A "32 GB SanDisk" purchased on a forum reseller might be a 4 GB chip with the controller faked to report 32 GB; writes beyond 4 GB silently fail. Even reputable distributors get hit with fakes.

For a dev board or a product where the user *expects* removable media (a kiosk that takes SD-card content updates), SD is fine. **For any product that's supposed to "just work" for years untouched, solder an eMMC.**

eMMC advantages:
- Soldered = no socket reliability issues.
- Built-in wear leveling, bad-block management, controller-level health monitoring (EXT_CSD).
- Faster (HS200 ~200 MB/s vs SD DDR50 ~50 MB/s).
- Authenticated boot partitions (RPMB).
- Industrial grade available, AEC-Q100 for automotive.

The cost difference is < $1 in volume. Make the engineering call early.

## 66.2  i.MX6ULL MMC hardware

The SoC has **two uSDHC controllers**: uSDHC1 and uSDHC2. Each supports:
- SD cards up to SDR104 (~104 MB/s).
- eMMC up to HS200 (~200 MB/s).
- SDIO (used by SDIO WiFi modules — Ch 91).
- 1, 4, or 8-bit data widths.

Typically Point Atom boards wire uSDHC1 to the SD slot, uSDHC2 to onboard WiFi or eMMC.

## 66.3  Speed modes

| Mode | Clock | Data lines | Bandwidth (theoretical) | Required pinmux |
|------|-------|------------|--------------------------|------------------|
| DS (Default Speed) | 25 MHz | 4-bit | 12.5 MB/s | basic |
| HS (High Speed) | 50 MHz | 4-bit | 25 MB/s | basic |
| DDR50 | 50 MHz double-rate | 4-bit | 50 MB/s | basic |
| SDR50 | 100 MHz | 4-bit | 50 MB/s | basic |
| SDR104 | 200 MHz | 4-bit | 100 MB/s | UHS-I voltage switch |
| HS200 (eMMC) | 200 MHz SDR | 8-bit | 200 MB/s | 8-bit, 1.8 V signal |
| HS400 (eMMC) | 200 MHz DDR | 8-bit | 400 MB/s | strobe-aware (i.MX6ULL does NOT support HS400) |

i.MX6ULL supports up to HS200 (200 MB/s on 8-bit eMMC) and SDR104 (104 MB/s on 4-bit SD). HS400 is i.MX8M+ territory.

## 66.4  Device tree — uSDHC2 with eMMC

```dts
&usdhc2 {
    pinctrl-names = "default", "state_100mhz", "state_200mhz";
    pinctrl-0 = <&pinctrl_usdhc2>;
    pinctrl-1 = <&pinctrl_usdhc2_100mhz>;
    pinctrl-2 = <&pinctrl_usdhc2_200mhz>;
    bus-width = <8>;
    non-removable;
    mmc-hs200-1_8v;
    keep-power-in-suspend;
    no-sd;
    no-sdio;
    vmmc-supply = <&reg_emmc_3v3>;
    vqmmc-supply = <&reg_emmc_1v8>;
    status = "okay";
};
```

Critical pieces:
- **`bus-width = <8>`** — eMMC's 8 data lines; gets HS200's full bandwidth.
- **`non-removable`** — kernel knows not to poll for card removal.
- **`mmc-hs200-1_8v`** — declares HS200 mode is supported (requires switching VQMMC to 1.8 V).
- **`vqmmc-supply`** — the I/O voltage rail; needs to support 1.8 V for HS200.
- **`pinctrl-1` and `-2`** — different pin slew rates at higher speeds (pull strengths change).
- **`no-sd`, `no-sdio`** — speeds up probing; we know this is eMMC.

For an SD slot on uSDHC1:

```dts
&usdhc1 {
    pinctrl-names = "default", "state_100mhz", "state_200mhz";
    pinctrl-0 = <&pinctrl_usdhc1>;
    pinctrl-1 = <&pinctrl_usdhc1_100mhz>;
    pinctrl-2 = <&pinctrl_usdhc1_200mhz>;
    bus-width = <4>;
    cd-gpios = <&gpio1 19 GPIO_ACTIVE_LOW>;
    keep-power-in-suspend;
    vmmc-supply = <&reg_sd1_vmmc>;
    sd-uhs-sdr104;
    no-mmc;
    status = "okay";
};
```

`cd-gpios` declares the card-detect line (a switch in the SD socket).

## 66.5  The MMC protocol — what's actually on the wire

Unlike QSPI and EEPROM (Ch 64/65) — where a from-scratch driver was tractable in ~200 lines — an MMC/SD **host controller** driver is genuinely a different scale. The SD spec is ~700 pages; the eMMC spec is ~400. There are ~60 commands, multi-stage state machines, signal-voltage switching, tuning windows, CRC validation, and physical-layer subtleties. **Writing one from scratch in a chapter is not honest pedagogy.**

What we *can* do — and what's productive — is **trace a single `read()` through the layers** so you understand exactly what the kernel does, and you can read the existing host driver's source after.

### The protocol vocabulary

MMC/SD commands are 48-bit packets:

```
   bit:  47  46         45–40     39–8       7–1       0
        ┌────┬────┬──────────┬───────────┬───────┬─────┐
        │ 0  │ 1  │ index    │ argument  │ CRC7  │ 1   │
        └────┴────┴──────────┴───────────┴───────┴─────┘
              ▲
              direction: 1 = host→card, 0 = card→host (response)
```

A handful of commands you'll see in dmesg or in driver code:

| Cmd | Name | Purpose |
|-----|------|---------|
| CMD0 | GO_IDLE_STATE | Reset card to idle |
| CMD8 | SEND_IF_COND | Check SD 2.0 voltage range (SD vs eMMC discrimination) |
| ACMD41 | SD_SEND_OP_COND | SD initialization, voltage window |
| CMD1 | SEND_OP_COND | eMMC initialization equivalent |
| CMD2 | ALL_SEND_CID | Read card identification |
| CMD3 | SET_RELATIVE_ADDR | Assign a relative address (RCA) |
| CMD7 | SELECT_CARD | Select the addressed card for I/O |
| CMD8 (eMMC) | SEND_EXT_CSD | Read 512-byte EXT_CSD block |
| CMD17 | READ_SINGLE_BLOCK | Read one block (512 B) |
| CMD18 | READ_MULTIPLE_BLOCK | Read consecutive blocks until CMD12 |
| CMD23 | SET_BLOCK_COUNT | Pre-declare a multi-block count (skip CMD12) |
| CMD24 | WRITE_BLOCK | Write one block |
| CMD25 | WRITE_MULTIPLE_BLOCK | Write consecutive blocks |
| CMD12 | STOP_TRANSMISSION | End a CMD18/CMD25 sequence |
| CMD13 | SEND_STATUS | Read card status register |
| CMD6 | SWITCH | Set EXT_CSD fields (mode change, partition switch) |
| CMD21 (eMMC) | SEND_TUNING_BLOCK | HS200/HS400 tuning pattern |

Data transfers happen on the data lines in parallel with commands on the CMD line. A successful read of 4 blocks is roughly:

```
   Host → Card:  CMD17 (READ_SINGLE_BLOCK) | start_block_addr
   Card → Host:  R1 response (status, OK)
   Card → Host:  DAT lines: 512 bytes of data + CRC16
```

For multi-block (CMD18), one command triggers a stream of consecutive blocks until the host issues CMD12 to stop — much more efficient than per-block CMD17s.

### The state machine

Cards live in one of these states: **Idle → Ready → Identification → Standby → Transfer → Sending-data / Receive-data / Programming / Disconnected**. Commands move the card between states; only certain commands are valid in each state. The host's job is to track this state and never issue an illegal command.

This is why a from-scratch MMC driver isn't tractable in a chapter — it's not the wire protocol (relatively simple), it's the state-machine management plus the voltage switching plus the tuning plus the CRC plus the error recovery.

## 66.6  The kernel's MMC subsystem — three layers

```
   user-space: cat /dev/mmcblk1p1
        │ read() syscall
        ▼
   ┌──────────────────────────────────────────────────┐
   │  block layer (Ch 55D)                             │
   │  builds a struct bio → struct request             │
   └──────────────────────────────────────────────────┘
        │ mmc_blk_request_fn (queue_rq callback)
        ▼
   ┌──────────────────────────────────────────────────┐
   │  MMC block driver (drivers/mmc/core/block.c)       │
   │  - converts bio offsets → MMC block addresses     │
   │  - builds struct mmc_request                       │
   └──────────────────────────────────────────────────┘
        │ mmc_wait_for_req(host, mrq)
        ▼
   ┌──────────────────────────────────────────────────┐
   │  MMC core (drivers/mmc/core/core.c)                │
   │  - state-machine tracking                          │
   │  - CMD/data sequencing                              │
   │  - retry / error recovery                          │
   └──────────────────────────────────────────────────┘
        │ host->ops->request(host, mrq)
        ▼
   ┌──────────────────────────────────────────────────┐
   │  Host driver (drivers/mmc/host/sdhci-esdhc-imx.c) │
   │  - programs hardware registers                     │
   │  - configures DMA / PIO                            │
   │  - waits for completion IRQ                        │
   │  - reads response register, returns to core        │
   └──────────────────────────────────────────────────┘
        │ MMIO + IRQ
        ▼
   uSDHC peripheral → physical bus → card
```

### The `mmc_host_ops` contract

A host driver provides this struct of callbacks:

```c
/* drivers/mmc/host/sdhci-esdhc-imx.c — simplified */
static const struct mmc_host_ops sdhci_esdhc_ops = {
    .request          = sdhci_request,         /* execute one command + opt. data */
    .set_ios          = sdhci_set_ios,         /* change clock, bus width, voltage */
    .get_cd           = sdhci_esdhc_get_cd,    /* card-present? */
    .get_ro           = sdhci_esdhc_get_ro,    /* write-protect? */
    .enable_sdio_irq  = sdhci_enable_sdio_irq, /* for SDIO devices */
    .execute_tuning   = sdhci_esdhc_executing_tuning, /* HS200 tuning */
    .start_signal_voltage_switch = sdhci_start_signal_voltage_switch, /* 3.3→1.8 V */
    /* ... */
};
```

**That's the abstraction**. The core asks the host driver to "execute this request" or "switch to bus width 8" without caring whether the controller is uSDHC, sdhci-pci, dw-mshc, or anything else. The host driver translates abstract requests into specific MMIO writes for its hardware.

### Tracing a single 4-KB read

You run `dd if=/dev/mmcblk1p1 bs=4096 count=1 of=/tmp/x`. Here's what happens:

1. **VFS** sends `read(fd, buf, 4096)` to the block-device file's chardev.
2. **Block layer** receives a 4 KB bio at logical-block-address (LBA) = wherever in p1. Splits into `struct request` (one or more, depending on splitting policy).
3. **`mmc_blk_request_fn`** (in `block.c`) is called as the queue's `queue_rq`. It:
   - Calculates the **MMC block address** (LBA / 512, since MMC blocks are 512 B even when the FS uses larger).
   - Decides between **single-block (CMD17)** for 1 block or **multi-block (CMD18 / CMD23+CMD18)** for 2+ blocks. For 4 KB = 8 blocks: multi-block with CMD23 prefix.
   - Builds a **`struct mmc_request`** containing the command, data-direction, sg-list for the DMA destination, and a completion callback.
4. **`mmc_wait_for_req(host, mrq)`** in the core: sends to host_ops->request, waits on the completion.
5. **`sdhci_request`** in the host driver:
   - Programs the eSDHC's command register (CMD18 opcode), argument register (start block), block-count register (8).
   - Sets up SDMA: scatter-gather list pointing into the user-space buffer's pinned pages.
   - Enables IRQs for "command complete" and "transfer complete."
   - Writes the "start" bit; hardware now drives the bus.
6. **Hardware** drives CMD18 onto the CMD line; eMMC responds with R1; eMMC begins streaming 8 × 512 bytes on the 8-bit DAT bus at 200 MHz (HS200) into DDR via DMA.
7. **IRQ "command complete"** fires after the CMD line transaction; host reads R1 response register, captures status.
8. **IRQ "transfer complete"** fires after the data phase finishes. Host driver calls `mmc_request_done(host, mrq)`.
9. **MMC core** wakes the waiter; `mmc_blk_request_fn` checks for errors, retries if needed, calls `blk_mq_end_request(req, status)`.
10. **Block layer** returns to user-space.

End-to-end at HS200, 4 KB takes about ~25 µs (10 µs of bus time, ~15 µs of kernel + IRQ overhead). For a properly-sized buffer (~64 KB or larger), the kernel overhead amortises and you approach raw bus bandwidth.

### A host driver's skeleton

If you ever did need to write one (say, porting to a new SoC):

```c
static int sdhci_xxx_probe(struct platform_device *pdev)
{
    struct sdhci_host *host;
    struct resource *iomem;

    /* SDHCI is the common framework — most SDHCI-compatible host drivers
       reuse the SDHCI core and only set quirks + IOMEM */
    host = sdhci_pltfm_init(pdev, &sdhci_xxx_pdata, sizeof(struct sdhci_xxx));
    if (IS_ERR(host)) return PTR_ERR(host);

    /* Get clocks, regulators, IOMEM */
    sdhci_get_of_property(pdev);

    /* Custom: i.MX has non-standard register layout for some bits */
    host->ops = &sdhci_xxx_ops;        /* override SDHCI defaults */
    host->quirks |= SDHCI_QUIRK_BROKEN_DMA;
    host->quirks2 |= SDHCI_QUIRK2_NO_1_8_V;
    host->mmc->caps |= MMC_CAP_NONREMOVABLE | MMC_CAP_8_BIT_DATA;

    return sdhci_add_host(host);
}
```

The **SDHCI framework** (`drivers/mmc/host/sdhci.c`) handles the standard cases; vendor drivers like `sdhci-esdhc-imx.c` add quirks and override specific operations. That's why the i.MX driver is ~1500 lines (mostly quirks) rather than 5000+ — the heavy lifting is in `sdhci.c`.

For a completely custom controller (not SDHCI-compatible), you'd implement `mmc_host_ops` from scratch — that's more work but the structure is the same.

## 66.7  EXT_CSD — the eMMC's health report card

eMMCs maintain a 512-byte **Extended Card-Specific Data** register full of metadata. Read it from userspace:

```
[root@pa-mini:~]# mmc extcsd read /dev/mmcblk1
=============================================
  Extended CSD rev 1.7 (MMC 5.0)
=============================================

Card supported command sets [S_CMD_SET: 0x01]
HPI Features [HPI_FEATURE: 0x01]: implementation based on CMD13
Background operations support [BKOPS_SUPPORT: 0x01]
...

Device life time estimation type A [DEVICE_LIFE_TIME_EST_TYP_A: 0x01]
Device life time estimation type B [DEVICE_LIFE_TIME_EST_TYP_B: 0x01]
Pre EOL information [PRE_EOL_INFO: 0x01]

eMMC Life Time Estimation A: 0%–10% device life time used
eMMC Life Time Estimation B: 0%–10% device life time used
Pre EOL information: Normal
```

The three key fields:
- **`DEVICE_LIFE_TIME_EST_TYP_A`**: SLC-cell wear, 0–9 representing 10% bands (0 = 0–10% used).
- **`DEVICE_LIFE_TIME_EST_TYP_B`**: MLC-cell wear, same scale.
- **`PRE_EOL_INFO`**: 0x01 = Normal, 0x02 = Warning (80%+ wear), 0x03 = Urgent (replacement needed).

Production firmware should periodically read these, log via MQTT/syslog to a fleet management system. When you see PRE_EOL warning across many units of the same age, you've quantified your hardware lifetime — invaluable for warranty planning.

## 66.8  eMMC boot partitions

eMMCs typically have:
- **Boot partition 1** (typically 4 MB).
- **Boot partition 2** (typically 4 MB).
- **RPMB** (Replay-Protected Memory Block, ~4 MB).
- **User partition** (the bulk).

```
[root@pa-mini:~]# ls /dev/mmcblk1*
/dev/mmcblk1         /dev/mmcblk1p1
/dev/mmcblk1boot0    /dev/mmcblk1boot1
/dev/mmcblk1rpmb
```

`mmcblk1boot0` is the active boot partition — i.MX6ULL boots from it (with the right fuse setting) instead of looking at the main partition's MBR. Use it for U-Boot:

```
# Force write to mmcblk1boot0
[root@pa-mini:~]# echo 0 > /sys/block/mmcblk1boot0/force_ro
[root@pa-mini:~]# dd if=u-boot.imx of=/dev/mmcblk1boot0
[root@pa-mini:~]# echo 1 > /sys/block/mmcblk1boot0/force_ro

# Select boot partition 1 as the active partition
[root@pa-mini:~]# mmc bootpart enable 1 1 /dev/mmcblk1
```

Why? Two boot partitions enable atomic boot-loader updates: write to boot0 while booting from boot1; on success, swap. Crash mid-update = boot1 still works.

## 66.9  RPMB — replay-protected secure storage

RPMB is a small (~4 MB) partition that requires HMAC authentication for every write. The eMMC controller verifies that a key (programmed once at factory) matches before allowing writes. Reads are authenticated too — you know the data hasn't been tampered with.

Use cases:
- Secure-boot rollback prevention (store "minimum allowed firmware version").
- DRM keys.
- Counters that need replay protection (anti-replay nonce).

Programming the RPMB key is one-shot — once written, that's it forever. **Don't experiment with RPMB on production boards.**

## 66.10  Performance test

```
[root@pa-mini:~]# dd if=/dev/zero of=/data/big.bin bs=1M count=512 conv=fsync
512+0 records in
512+0 records out
536870912 bytes (537 MB) copied, 4.5 s, 119 MB/s

[root@pa-mini:~]# fio --name=randwr --filename=/data/test.bin --rw=randwrite \
    --bs=4k --runtime=30 --time_based --ioengine=psync --iodepth=1 --size=100M
   write: IOPS=2500, BW=10MiB/s
```

HS200 eMMC: 100–150 MB/s sequential, ~2500 IOPS random 4k write. Compare to a budget SD card: 30 MB/s sequential, ~200 IOPS random.

## 66.11  Lab

1. **Trace a read with ftrace.** `echo function > /sys/kernel/debug/tracing/current_tracer; echo 'mmc_*' > set_ftrace_filter; cat /dev/mmcblk1p1 > /dev/null; cat trace`. See `mmc_blk_request_fn`, `mmc_wait_for_req`, `sdhci_request` fire in order — exactly the layered call chain described in §66.6.
2. **Inspect EXT_CSD.** Run `mmc extcsd read /dev/mmcblk1`. Identify the eMMC's life-time estimation.
3. **Benchmark.** dd + fio at sequential and random. Compare against an SD card.
4. **Boot partition write.** `dd` U-Boot to `mmcblk1boot0`. Activate it. Boot.
5. **Force HS mode change.** In DT, remove `mmc-hs200-1_8v`. Reboot. Benchmark — confirm slower.
6. **Wear monitoring script.** Daily cron: read EXT_CSD, log to /var/log/wear.log. After running for weeks, plot.
7. **Pull-the-plug test.** With dd writing a large file, yank power. Reboot. Observe whether `fsck` finds errors. Compare eMMC vs SD card resilience (eMMC much better).
8. **Read the host driver.** Skim `drivers/mmc/host/sdhci-esdhc-imx.c`. Find `sdhci_esdhc_ops`. Find the i.MX-specific quirks (HS400 absence on i.MX6ULL, the tuning callback). With the layer model in §66.6 you should be able to navigate it.

## 66.12  Pitfalls

- **`bus-width = <4>`** on a chip with 8 data lines wired. You get DS or HS speeds at best; HS200 needs 8-bit. Check schematic ↔ DT.
- **Missing `vqmmc-supply`** for HS200. Driver can't switch to 1.8 V signaling; falls back to HS50. Look for "fall back" messages in dmesg.
- **`non-removable` on an SD slot.** Card-detect ignored; system keeps trying after card removal.
- **`cd-gpios` polarity wrong.** Empty slot reports as "card present" (or vice versa). `GPIO_ACTIVE_LOW` is typical for card-detect switches.
- **eMMC tuning fails.** HS200 requires per-card calibration ("tuning"). Some eMMCs require specific tuning patterns. Mainline supports this; if you see "tuning failed" in dmesg, the eMMC chip is buggy (not common but happens — usually fixable by `mmc-ddr-1_8v` instead of HS200).
- **fsync slow.** eMMC `fsync` does a real flush-to-flash cycle (10s–100s of ms). If your app fsyncs after every write, performance tanks. Batch writes.
- **Write amplification.** Even with TRIM, eMMC's GC writes amplify your data ~2–5×. A 10 GB/day app actually writes 30 GB/day to flash. Plan lifetime accordingly.
- **`force_ro` on boot partitions**. Default is RO; you must clear it to write. Don't forget to re-arm.
- **Power-fail mid-erase.** eMMC's internal erase block is invisible. A power loss can corrupt a *bigger area than you wrote*. Industrial eMMCs (Micron e.MMC, KIOXIA) have PFAIL protection; consumer ones don't.

## 66.13  Going deeper

- **`Documentation/mmc/`** — MMC subsystem documentation.
- **`drivers/mmc/core/core.c`** — MMC core. Look at `mmc_wait_for_req`, `mmc_attach_sd`, `mmc_attach_mmc` for the state-machine code.
- **`drivers/mmc/core/block.c`** — the block-driver glue. `mmc_blk_mq_issue_rq` is the per-request entry point.
- **`drivers/mmc/host/sdhci.c`** — SDHCI common framework.
- **`drivers/mmc/host/sdhci-esdhc-imx.c`** — i.MX uSDHC driver. ~1500 lines, mostly quirks over `sdhci.c`.
- **`Documentation/devicetree/bindings/mmc/`** — MMC bindings.
- **JEDEC eMMC 5.1 standard (JESD84-B51)** — the eMMC specification.
- **SD Physical Layer Specification** — at sdcard.org (free Simplified version, ~250 pages).
- **`mmc-utils`** — `mmc`, `mmc extcsd`, RPMB tools.
- **`fio`** — the storage benchmarking tool.

---

> **End of Group A — Storage (Ch 64–66).** You now have the three storage stacks covered: QSPI NOR for small boot, EEPROM for tiny metadata, eMMC/SD for bulk. Pick by capacity + speed + reliability requirements.

> Next chapter: **Chapter 67 — Temperature / humidity / pressure sensors.** Group B opens with the environmental sensors trio — BME280, SHT3x, AHT20 — and the IIO drivers that expose them.
