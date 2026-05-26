---
chapter: 65
title: I²C / SPI EEPROM (AT24Cxx / 25LCxx)
part: VII — Device cookbook
estimated_pages: 12
status: draft
---

# Chapter 65 — I²C / SPI EEPROM

> **What:** small (128 B – 64 KB) non-volatile storage chips on I²C or SPI. The standard mainline driver `at24` handles dozens of variants; SPI EEPROM uses `at25`. Two chips compared: **Microchip AT24C02** (I²C, 256 B, ubiquitous) and **Microchip 25LC512** (SPI, 64 KB). Plus the **nvmem** framework that lets EEPROM contents back kernel structures (MAC address, board serial, calibration).
> **Why:** EEPROM is for "this never changes" or "this changes maybe once per device-lifetime" data: board serial number, MAC address (preferred over OCOTP fuses when factory-programmable), small calibration tables, factory test results. Cheap, simple, no wear-levelling needed (rated ~1M writes per cell).
> **Compare**: AT24C02 (I²C, smallest, ~$0.30), AT24C512 (I²C, 64 KB, ~$1), 25LC512 (SPI, 64 KB, faster, ~$1.50).

## 65.1  When EEPROM beats flash/eFuse

| Use case | Best fit |
|---|---|
| Permanently identify a board (read-only after factory) | **eFuse** (i.MX6ULL OCOTP) — one-time-programmable, no risk of erasure |
| MAC address, serial, calibration — write rarely, read every boot | **EEPROM** (I²C/SPI) — many writes possible, but unlikely to need them |
| Frequently updated config (boot env, A/B slot pointer) | **NOR flash** (QSPI; with redundant copies) |
| Bulk storage (firmware, images) | **NAND flash / eMMC** |

EEPROMs occupy the "we want to be able to rewrite, but only rarely" niche. ~1M write cycles is plenty for "rewrite once per factory test." Bytes are individually addressable for reads.

## 65.2  Chip comparison

### Microchip AT24C02 (I²C, 256 B)

- 8-pin SOIC or DIP package.
- I²C up to 1 MHz (some variants up to 3.4 MHz).
- 8-byte page write; ~5 ms write cycle per page.
- I²C address 0x50–0x57 (3 strap pins).
- ~$0.30.
- Family: AT24C01 (128 B) → AT24C512 (64 KB). Same protocol scaled.

### Microchip AT24C512 (I²C, 64 KB)

- Same protocol as AT24C02 but with **2-byte register addressing** (since > 256 B can't fit in 1 byte).
- 128-byte page write.
- Address 0x50–0x57.
- ~$1.

### Microchip 25LC512 (SPI, 64 KB)

- SPI mode 0 or 3, up to 20 MHz.
- Faster than I²C — useful when writing many KB at factory test.
- 128-byte page write; ~5 ms cycle.
- Has a /WP pin (write protect, useful for production).
- ~$1.50.

For 99% of cases on i.MX6ULL: pick AT24C02 if you need < 256 B (typical for serial + MAC); AT24C512 if you need calibration tables; 25LC512 if you want SPI (for example, sharing a SPI bus with your QSPI flash chip-select).

## 65.3  Schematic

I²C version (AT24C02):

```
 i.MX6ULL              AT24C02
 ─────────             ───────
 I²C1_SDA  ──╬──╳──►  SDA       (4.7 kΩ pull-up to 3.3 V — shared on bus)
 I²C1_SCL  ──╬──╳──►  SCL
                       A0, A1, A2  (strap to GND or VCC to select address)
                       WP          (tie low to permit writes)
 VCC ────────────────► VCC (3.3 V)
 GND ────────────────► GND, A0–A2 (if address = 0x50)
```

SPI version (25LC512): standard 4-wire SPI + /CS + /WP. /WP can be a host GPIO for software-controlled protection.

## 65.4  Device tree

```dts
&i2c1 {
    eeprom@50 {
        compatible = "atmel,24c02";
        reg = <0x50>;
        pagesize = <8>;          /* AT24C02 = 8-byte pages */
    };
};
```

For AT24C512 (64 KB):

```dts
eeprom@50 {
    compatible = "atmel,24c512";
    reg = <0x50>;
    pagesize = <128>;
    /* The driver auto-detects 2-byte addressing for chips >256 B */
};
```

For SPI 25LC512:

```dts
&ecspi3 {
    eeprom@1 {
        compatible = "microchip,25lc512", "atmel,at25";
        reg = <1>;
        spi-max-frequency = <10000000>;
        size = <65536>;
        pagesize = <128>;
        address-width = <16>;
    };
};
```

The "atmel,at25" fallback covers most SPI EEPROMs with the same protocol; `size`, `pagesize`, `address-width` parameters tell the driver the chip's geometry.

## 65.5  Driver behavior — sysfs and nvmem

After probe, the EEPROM exposes a binary attribute:

```
[root@pa-mini:~]# ls /sys/bus/i2c/devices/1-0050/
driver/  eeprom  name  ...

[root@pa-mini:~]# hexdump -C /sys/bus/i2c/devices/1-0050/eeprom | head
00000000  ff ff ff ff ff ff ff ff  ff ff ff ff ff ff ff ff  |................|
*
00000100

[root@pa-mini:~]# echo -n "SN12345" > /tmp/serial
[root@pa-mini:~]# dd if=/tmp/serial of=/sys/bus/i2c/devices/1-0050/eeprom bs=1 seek=0
[root@pa-mini:~]# dd if=/sys/bus/i2c/devices/1-0050/eeprom bs=1 count=7
SN12345
```

The `at24` driver handles paging, write-cycle waits, and address arithmetic for you. From userspace, it looks like an offset-addressable byte file.

## 65.6  nvmem — typed access from the kernel

The `nvmem` framework lets *other kernel drivers* consume EEPROM contents as named cells. Example — MAC address for the FEC:

```dts
&i2c1 {
    eeprom: eeprom@50 {
        compatible = "atmel,24c02";
        reg = <0x50>;
        pagesize = <8>;
        #address-cells = <1>;
        #size-cells = <1>;

        mac_address: mac@0 {
            reg = <0x0 0x6>;     /* 6 bytes at offset 0 */
        };
        serial_number: serial@10 {
            reg = <0x10 0x10>;   /* 16 bytes at offset 0x10 */
        };
    };
};

&fec1 {
    nvmem-cells = <&mac_address>;
    nvmem-cell-names = "mac-address";
    /* ... */
};
```

The FEC driver, on probe, reads the 6-byte cell and uses it as the MAC address. Same DT, same driver, no per-board kernel code — the MAC is whatever your factory wrote to the EEPROM.

## 65.7  Factory programming workflow

Production:

```sh
# 1. Generate per-unit serial / MAC
SERIAL=$(uuidgen | tr -d - | cut -c1-12)
MAC="02:$(echo $SERIAL | sed 's/\(..\)/\1:/g' | cut -c1-14)"
echo "Serial: $SERIAL  MAC: $MAC"

# 2. Write to EEPROM
printf "$MAC" | xxd -r -p > /sys/bus/i2c/devices/1-0050/eeprom    # 6 bytes at 0
printf "$SERIAL" > /tmp/serial; dd if=/tmp/serial bs=1 seek=16 conv=notrunc \
    of=/sys/bus/i2c/devices/1-0050/eeprom

# 3. Verify
xxd /sys/bus/i2c/devices/1-0050/eeprom | head -2

# 4. Lock with /WP (if SPI variant)
echo 1 > /sys/class/gpio/.../wp_value
```

After factory, the WP pin is permanently high. Field firmware can read but not write.

## 65.8  Lab

1. **Identify the EEPROM.** `i2cdetect -y 1`; expect address 0x50 if A0-A2 grounded.
2. **Read out.** `hexdump -C /sys/bus/i2c/devices/1-0050/eeprom`. Expect all 0xFF on a virgin chip.
3. **Write and verify.** Write a serial number; read back; reboot; read again; persistence confirmed.
4. **nvmem MAC.** Configure DT as in §65.6. Boot; `ip link show eth0`; verify the MAC matches what you wrote.
5. **Stress test.** Write the same offset 1000 times. EEPROMs handle ~1M write cycles; this won't damage but will let you measure throughput (~200 B/s on 100 kHz I²C, limited by 5 ms page-write cycle).
6. **SPI variant.** Switch to a 25LC512; compare write speed (faster, paging cycle still 5 ms but reads zip).

Commit code to `code/ch65-eeprom/`.

## 65.9  Pitfalls

- **Wrong pagesize**. Writes that cross a page boundary wrap to the start of the same page (silent data corruption). Always set `pagesize = <N>` matching the chip; the `at24` driver respects it and splits long writes.
- **Address-width confusion.** AT24C02 uses 1-byte address; AT24C512 uses 2-byte. The driver derives this from `size` for atmel chips, but verify if you have an odd-pinout variant.
- **Multiple EEPROMs on one bus.** Each must have a unique I²C address (A0/A1/A2 strap pins). Symptom: only one responds correctly. Fix by strapping different addresses.
- **WP pin floating.** Reads of "all 0xFF" forever. Either tie WP low (always writable) or wire to a GPIO for software control.
- **5 ms page-write wait.** The chip ACKs but is busy for ~5 ms after a page write. A subsequent immediate I²C transaction NACKs. The `at24` driver handles this; manual i2c-tools writes need a delay.
- **Wrong nvmem cell offset.** Driver reads garbage. Cross-check `reg = <offset size>` against your factory-write script.
- **/WP and software write-protect register.** Some chips have both a hardware WP pin and a software status-register write-protect. Make sure both allow writes.

## 65.10  Going deeper

- **`drivers/misc/eeprom/at24.c`** — the I²C EEPROM driver (~1000 lines). Covers paging, addressing, nvmem integration.
- **`drivers/misc/eeprom/at25.c`** — SPI EEPROM driver.
- **`Documentation/devicetree/bindings/eeprom/at24.yaml`** — DT binding.
- **`Documentation/devicetree/bindings/nvmem/nvmem.yaml`** — nvmem provider binding.
- **`Documentation/ABI/testing/sysfs-bus-nvmem`** — nvmem sysfs.

> Next chapter: **Chapter 66 — SD card and eMMC deep dive.** The MMC subsystem, speed modes, EXT_CSD register, wear-life monitoring on eMMC, and why an SD card in your production product is a bad idea.
