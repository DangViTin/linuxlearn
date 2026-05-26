---
chapter: 64
title: QSPI NOR flash (W25Q128 / MX25L256 / MT25Q)
part: VII — Device cookbook
estimated_pages: 16
status: draft
---

# Chapter 64 — QSPI NOR flash

> **What:** how to add a QSPI NOR flash chip to an i.MX6ULL board. Three representative chips compared: **Winbond W25Q128** (16 MB, the workhorse), **Macronix MX25L25645G** (32 MB, larger boot images), **Micron MT25QL256ABA** (32 MB, industrial-grade). One chapter, one schematic, three DT examples, one driver (mainline `spi-nor` covers all three), MTD partitions for boot/kernel/dtb/rootfs slots, and the production layout pattern.
> **Why:** for a boot device, QSPI NOR is the sweet spot between "tiny SPI EEPROM" and "huge eMMC." A 16-MB W25Q128 holds U-Boot + kernel + dtb + minimal rootfs with room for an A/B update scheme. Costs ~$1.50, soldered on board, no card-slot reliability issues. Many industrial i.MX6ULL designs boot from QSPI NOR.
> **Compare**: W25Q128 (cheap, common), MX25L256 (2× capacity, similar price), MT25Q (industrial temp, longer-life, ~3× price).

## 64.1  Why QSPI NOR vs eMMC vs SD vs raw NAND

| | QSPI NOR | eMMC | SD card | Raw NAND |
|---|---|---|---|---|
| Typical size | 8–32 MB | 4–64 GB | 4 GB–1 TB | 256 MB–4 GB |
| Read speed | 50 MB/s | 250 MB/s | 90 MB/s | 30 MB/s |
| Write speed | 0.5 MB/s | 100 MB/s | 60 MB/s | 5 MB/s |
| Erase block | 4–64 KB | invisible | invisible | 128 KB |
| Erase cycles | 100,000 | 1,000–10,000 | varies | 10,000 |
| XIP-capable | ✔ (slow) | ✗ | ✗ | ✗ |
| Wear leveling needed | yes, in driver | built-in | built-in | UBI |
| Cost | $1–5 | $5–20 | $3–10 | $2–10 |
| Best for | Small boot device | Main storage on consumer products | Removable, dev | Mid-size industrial |

QSPI NOR is the right choice when:
- Total storage need is < 32 MB.
- You want fast boot (NOR's deterministic read speed gives sub-second U-Boot startup).
- You want a soldered-on, theft-resistant boot device.
- You're not storing much user data.

## 64.2  Chip comparison

### Winbond W25Q128

- 128 Mbit (16 MB).
- Standard SPI up to 104 MHz, QSPI (quad-IO) up to 80 MHz.
- 4 KB sector erase / 32 KB block erase / 64 KB block erase / chip erase.
- 256-byte page program.
- VCC 2.7–3.6 V.
- $1.20–1.80 in volume.
- The most popular small QSPI NOR. Shows up in everything from ESP32 boards to industrial PLCs.

### Macronix MX25L25645G

- 256 Mbit (32 MB).
- Up to 133 MHz SPI, 104 MHz QSPI.
- Compatible feature set with W25Q.
- 4-byte address mode for >16 MB access (3-byte addressing only reaches 16 MB).
- $2.50–4.00.
- The "I need more than 16 MB" upgrade.

### Micron MT25QL256ABA

- 256 Mbit (32 MB).
- Up to 166 MHz.
- 100,000 erase cycles (rated; competitors often rate at fewer).
- AEC-Q100 automotive grade.
- $5–7.
- Use when reliability/lifetime matters more than cost.

The mainline `spi-nor` driver supports all three via a database lookup keyed on the chip's "JEDEC ID" (read from registers at probe time). You usually need *no chip-specific code*.

## 64.3  Schematic

The minimum is six wires:

```
 i.MX6ULL                   W25Q128 / MX25L256 / MT25Q
 ─────────                  ──────────────────────────
 QSPI_A_SCLK  ───────────►  CLK
 QSPI_A_DATA0 ◄──────────►  IO0 (MOSI in single mode)
 QSPI_A_DATA1 ◄──────────►  IO1 (MISO in single mode)
 QSPI_A_DATA2 ◄──────────►  IO2 (/WP in single mode — pull HIGH for QSPI)
 QSPI_A_DATA3 ◄──────────►  IO3 (/HOLD in single mode — pull HIGH for QSPI)
 QSPI_A_SS0_B ───────────►  /CS

 VCC          ───────────►  VCC (3.3 V)
 GND          ───────────►  GND
```

**Decoupling**: 100 nF + 4.7 µF close to VCC. NOR draws sharp current pulses when programming; insufficient decoupling causes spurious resets.

**PCB layout**: keep traces short and length-matched (within 5 mm) — at 80 MHz QSPI you have ~25 ns rise time and ~6 cm wavelength. Series termination resistors (33 Ω) on each line are common.

**Pull-ups**: 10 kΩ on each of IO2 and IO3 when running in 1-bit mode at boot (before quad-mode is enabled).

## 64.4  Device tree

```dts
&qspi {
    pinctrl-names = "default";
    pinctrl-0 = <&pinctrl_qspi>;
    status = "okay";

    flash@0 {
        compatible = "winbond,w25q128", "jedec,spi-nor";
        reg = <0>;
        spi-max-frequency = <80000000>;
        spi-rx-bus-width = <4>;
        spi-tx-bus-width = <4>;

        partitions {
            compatible = "fixed-partitions";
            #address-cells = <1>;
            #size-cells = <1>;

            partition@0 {
                label = "u-boot";
                reg = <0x000000 0x100000>;       /* 1 MB */
                read-only;
            };
            partition@100000 {
                label = "u-boot-env";
                reg = <0x100000 0x010000>;       /* 64 KB */
            };
            partition@110000 {
                label = "dtb";
                reg = <0x110000 0x010000>;       /* 64 KB */
            };
            partition@120000 {
                label = "kernel-a";
                reg = <0x120000 0x600000>;       /* 6 MB slot */
            };
            partition@720000 {
                label = "kernel-b";
                reg = <0x720000 0x600000>;       /* 6 MB slot */
            };
            partition@d20000 {
                label = "user-data";
                reg = <0xd20000 0x2e0000>;       /* remainder */
            };
        };
    };
};
```

For Macronix or Micron, change the first compatible:

```dts
compatible = "macronix,mx25l25645g", "jedec,spi-nor";
/* or */
compatible = "micron,mt25ql256", "jedec,spi-nor";
```

The driver uses the JEDEC fallback (`"jedec,spi-nor"`) if it doesn't recognise the first string, then identifies the chip from its read-id at probe.

### Compatible vs JEDEC fallback

The `"jedec,spi-nor"` fallback means: even without an exact-match compatible, the driver runs and reads the chip's JEDEC ID. The database in `drivers/mtd/spi-nor/winbond.c`, `macronix.c`, `micron.c` then identifies the chip and sets its parameters (size, sector layout, fast-read commands, quad-enable bit position).

If your chip is in the JEDEC database but your DT doesn't have its specific compatible, it still works — but the early-boot probe takes slightly longer (JEDEC read vs. immediate parameter lookup).

## 64.5  Driver and MTD

After boot:

```
[root@pa-mini:~]# dmesg | grep -i qspi
fsl-quadspi 21e0000.qspi: 64KiB QuadSPI NOR flash 'w25q128' (id 0xef4018) at 0
[root@pa-mini:~]# cat /proc/mtd
dev:    size   erasesize  name
mtd0: 00100000 00010000 "u-boot"
mtd1: 00010000 00010000 "u-boot-env"
mtd2: 00010000 00010000 "dtb"
mtd3: 00600000 00010000 "kernel-a"
mtd4: 00600000 00010000 "kernel-b"
mtd5: 002e0000 00010000 "user-data"
```

Read/write/erase from user-space:

```
[root@pa-mini:~]# nanddump /dev/mtd2 > my-dtb.bin     # back up the DTB
[root@pa-mini:~]# flash_erase /dev/mtd3 0 0           # erase kernel-A slot
[root@pa-mini:~]# nandwrite -p /dev/mtd3 zImage       # write new kernel
[root@pa-mini:~]# flashcp -v new-dtb.dtb /dev/mtd2    # erase + write in one call (preserves OOB-style layout for NOR is N/A; uses raw write)
```

For *small writable* areas like `u-boot-env`, the standard `fw_setenv` (from u-boot-tools) reads/writes the env area directly:

```
[root@pa-mini:~]# cat /etc/fw_env.config
# Device         Offset    Env size  Sector size
/dev/mtd1        0x0       0x10000   0x10000

[root@pa-mini:~]# fw_setenv bootcmd 'echo hello; bootm 0x82000000'
[root@pa-mini:~]# fw_printenv bootcmd
bootcmd=echo hello; bootm 0x82000000
```

## 64.6  XIP from QSPI

NOR flash supports **XIP** (eXecute In Place) — the CPU can read instructions directly from QSPI without first loading them to RAM. i.MX6ULL's QSPI maps to a memory window (typically 0x60000000) where reads transparently fetch from the flash chip.

XIP from QSPI:
- **Pro**: smaller RAM footprint; faster boot (no copy).
- **Con**: slow (max 50 MB/s on i.MX6ULL QSPI; vs 800 MB/s DDR3); higher power; instruction cache misses are expensive.

In practice on i.MX6ULL, XIP is used only for U-Boot (small, fast-boot critical). The kernel and rootfs go to RAM. We touched on this in Ch 11.

## 64.7  Boot from QSPI NOR

U-Boot config sets where to load kernel + dtb from:

```
boot_qspi=sf probe; \
  sf read 0x80800000 0x120000 0x600000; \
  sf read 0x83000000 0x110000 0x10000; \
  bootz 0x80800000 - 0x83000000

bootcmd=run boot_qspi
```

- `sf probe` initialises the QSPI controller.
- `sf read <ram> <flash-offset> <length>` copies from QSPI to RAM.
- `bootz <kernel> - <dtb>` boots.

For A/B update — `boot_qspi_a` and `boot_qspi_b` differ by `<flash-offset>`. A boot counter (`fw_setenv boot_count`) plus an A/B flag selects which slot.

## 64.8  Lab

1. **Detect.** Boot with a known QSPI chip; verify `dmesg`, `/proc/mtd`.
2. **Identify.** `mtd_debug info /dev/mtd0` and `flash_erase /dev/mtd0 0 1` to confirm minimum erase unit.
3. **Read out the entire chip.** `nanddump -f all-flash.bin /dev/mtdblock0`. Compare against expected size.
4. **Update U-Boot env**. `fw_setenv` a custom variable, reboot, observe in U-Boot's `printenv`.
5. **Swap A/B kernel slots.** Erase `kernel-b`, copy `zImage` to it, change `bootcmd` to load from B. Reboot; verify boot from B.
6. **JEDEC ID poke.** With kernel logs at `loglevel=8`, observe the chip identification text. Substitute a different-compatible chip in DT (with the same physical chip); confirm the driver still works via the `"jedec,spi-nor"` fallback.

Commit code to `code/ch64-qspi-flash/`.

## 64.9  Pitfalls

- **Quad-mode enable.** Some chips require setting the QE (Quad Enable) bit in their status register. The `spi-nor` driver handles this automatically for known chips; if you use `"jedec,spi-nor"` only, the driver may not know your chip's QE-bit position. Symptom: bit-errors in QSPI mode but single-bit mode works. Add the specific compatible.
- **4-byte addressing for > 16 MB**. Chips ≤ 16 MB use 3-byte addresses; > 16 MB needs 4-byte. The driver auto-switches; old U-Boot versions might not. Verify your U-Boot is recent enough.
- **Partition off the chip.** A typo in `reg = <offset size>;` that goes past chip end → mysterious failures. The mainline DT parser warns; check dmesg.
- **U-Boot-env partition mismatch with `fw_env.config`.** Both reference the same flash offset; if they disagree, `fw_setenv` corrupts areas U-Boot expects to be readable. Always cross-check.
- **Writes corrupting because of unaligned erase.** NOR's smallest erase is the sector size (4 KB typical). Trying to "write" without first erasing fills with NAND-like garbage (NOR pre-erase is all 1s; you can only program 1→0). `flash_erase` first, then `nandwrite`.
- **Boot-cycle wear on `u-boot-env`.** Each `saveenv` erases + writes the env sector. NOR rated 100k cycles; if your system saves env every boot for years, you'll wear it out. Use `redundant_env` (two copies, ping-pong) for safety, or move env to a less-stressed location.

## 64.10  Going deeper

- **`drivers/mtd/spi-nor/`** — directory; one file per vendor. Worth skimming `core.c` and the vendor file for your chip.
- **`drivers/spi/spi-fsl-qspi.c`** — i.MX QSPI controller driver.
- **`Documentation/devicetree/bindings/mtd/jedec,spi-nor.yaml`** — DT binding.
- **`mtd-utils`**: `flash_erase`, `nandwrite`, `nanddump`, `flashcp`, `mtd_debug`. Indispensable for board bring-up.
- **`u-boot/cmd/sf.c`** — the SPI flash command. Read for understanding what `sf probe / read / write / erase` actually do.
- **JEDEC SFDP** (Serial Flash Discoverable Parameters) — the standard mechanism by which the driver discovers chip parameters at runtime. Most chips support it.

> Next chapter: **Chapter 65 — I²C / SPI EEPROM.** When you need just a few KB of persistent storage for serial numbers, MAC addresses, or factory calibration — far less than a flash chip but more than fuses.
