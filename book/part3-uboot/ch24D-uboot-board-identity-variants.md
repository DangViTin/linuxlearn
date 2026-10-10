---
chapter: "24D"
title: Board identity and variant selection in U-Boot
part: III - U-Boot, deeply
estimated_pages: 18
status: draft
---

# Chapter 24D: Board identity and variant selection in U-Boot

An EEPROM byte can select a display DTB. It can also select the wrong one after a partial factory write or a read from the wrong bus. Before that byte controls boot, we need to know what record it belongs to, whether the record is complete, and whether the combination describes hardware we support.

We will define a small binary identity record, validate it, and publish a DTB/FIT choice only after validation succeeds. This continues the **U-Boot v2026.04** baseline, commit `88dc2788777babfd6322fa655df549a019aa1e69`, and the `mx6ull_pa_mini` port. Chapter 24E packages those choices in one FIT.

The supplied MINI V2.2 and CORE schematics contain **no factory identity EEPROM**. Our 64-byte record is a proposed lab format for an **optional external EEPROM** on the documented I2C1 route, not a vendor record to discover on an unmodified board. The display connector and available panel models are documented MINI hardware options. No lab step programs EEPROM or fuses.

This is a v2026.04 host-study/modern-migration exercise. Chapter 19's vendor board names and old I2C API are not interchangeable with this port's names and driver-model helpers. A stock MINI can use an explicitly selected, matching OS DTB without pretending that it has this EEPROM.

## 24D.1  The real problem

Fix one MINI baseboard revision and **one core assembly** first. Within that assembly, the proposed late selector changes only the optional display description, not DDR, boot storage or the single ENET2 port. The guide documents these panel choices at RGBLCD J1 (pp267-268):

| LCD option | Selected MINI attachment | OS DTB to implement | FIT configuration |
|------------|------------------|--------|-------------------|
| 0 | No display | `imx6ull-pa-mini-no-lcd.dtb` | `conf-no-lcd` |
| 1 | Optional 4.3-inch **ID4342**, 480 x 272 | `imx6ull-pa-mini-lcd43.dtb` | `conf-lcd43` |
| 2 | Optional 7-inch **ID7016**, 1024 x 600 | `imx6ull-pa-mini-lcd70.dtb` | `conf-lcd70` |

These are filenames for OS trees to develop and test, not supplied or bench-qualified DTBs. The same-size **ID4384** (4.3-inch, 800 x 480) and **ID7084** (7-inch, 800 x 480) are different options and are **not** accepted by these two entries. No size alone determines full display timing, supply sequence or the attached touch controller's address/driver.

MINI sheet 2 documents RGB888, I2C2 touch signals, backlight `BLT_PWM` on GPIO1_IO08 and a hardware `RESET` shared with the SoC. Do not copy the vendor file's inherited software LCD reset on GPIO5_IO09 onto this board. Its three SGM3157 switches isolate LCD_DATA7/15/23, which also serve ROM boot straps and panel ID signals. The proposed EEPROM avoids implementing that separate panel-ID switching sequence; its LCD byte is an assembly declaration, **not an automatic measurement of the fitted screen**.

The guide pp238-239 documents NAND cores with 256 MiB DDR and eMMC cores with 512 MiB DDR; the supplied CORE schematic shows the storage alternatives and the 512 MiB DDR part. Choose the early image/DCD for the actual core before these late exercises. Do not combine those assemblies into the display table or treat baseboard V2.2 as a RAM size.

A late EEPROM read cannot choose DDR timing that the Boot ROM already needed. The pinned EVK path initializes DDR using the image's DCD, before `board_late_init`. Families with different DDR may need distinct early images or an independently engineered early-selection mechanism. Do not claim this late hook enables arbitrary RAM variants in one binary.

## 24D.2  Three ways to identify a board

| Source | Useful information | What must be established |
|--------|--------------------|--------------------------|
| Dedicated GPIO straps | A few assembly options | Mux, input ownership, pull resistors, settled readings and reserved states. |
| I2C EEPROM | Revision, options, MAC, serial | Actual part, address scheme, record format and factory process. |
| Documented read-only chip identity/fuse data | Provisioned chip identity | Board mapping and authorized allocation of fields. A UID alone does not encode peripherals. |

Our proposed add-on is an **AT24C02-class 256-byte device**, at 7-bit `0x50`, using a one-byte offset. It connects to MINI P4 pin **43 for I2C1 SCL** and pin **42 for I2C1 SDA**, with 24B's control-DT alias making that bus U-Boot sequence 0. Pin 44 belongs to I2C2 SDA, not I2C1. UART4 must not own those pads. The baseboard already pulls these nets up to 3.3 V; choose a compatible device/module and account for any additional pull-ups. The address and record are our design assumptions, not detected factory hardware.

Microchip's [AT24C02C addressing specification](https://onlinedocs.microchip.com/oxy/GUID-84DB5234-25BE-4966-B7FA-22A50FA88666-en-US-2/GUID-BBF9285C-1347-453B-AC8D-B7FDB5176294.html) describes that part's eight-bit word address and package-dependent address pins. A 24C04 may put upper address bits in the slave address; larger parts commonly use two-byte offsets. Check the exact part and strapped address rather than substituting a generic EEPROM name. The optional TMP102 at `0x48` can share this bus if both modules' electrical/address contracts are satisfied; neither is fitted by default.

For a muxed bus, use the child bus sequence or resolve the intended bus by its control-DT node. No code below reads or writes a PMIC.

## 24D.3  Do not let the identity format grow by accident

A format is a byte-level contract, not a C structure written to EEPROM. This proposed version occupies exactly 64 bytes starting at offset zero:

| Offset | Bytes | Encoding / rule |
|--------|-------|-----------------|
| `0x00` | 8 | Exact bytes `PAMID01` followed by NUL. |
| `0x08` | 1 | Format version 1. |
| `0x09` | 1 | Reserved, zero. |
| `0x0a` | 2 | Record length 64, little-endian. |
| `0x0c` | 1 | Lab hardware-profile revision 1 only; not the MINI PCB silkscreen revision. |
| `0x0d` | 1 | LCD option 0, 1 or 2. |
| `0x0e` | 1 | Ethernet option 1: the single onboard MINI ENET2 RJ45. |
| `0x0f` | 1 | Reserved, zero. |
| `0x10` | 6 | MAC in transmitted byte order. |
| `0x16` | 10 | Reserved, all zero. |
| `0x20` | 16 | Nonempty ASCII serial: 1-15 letters/digits/hyphens, NUL terminated, remaining bytes zero. |
| `0x30` | 12 | Reserved, all zero. |
| `0x3c` | 4 | Little-endian CRC-32 over bytes `0x00..0x3b`. |

`hw_rev=1` names this proposed fixed-core/fixed-baseboard profile. It is not a conversion of "V2.2" to an integer, and `eth_opt=1` does not mean ENET1 or identify the PHY silicon. The profile's bill of materials must specify the baseboard revision, core and supported PHY software separately. This record alone cannot establish working SR8201F support.

The CRC is U-Boot `crc32(0, data, 60)`: reflected CRC-32/ISO-HDLC, polynomial `0xedb88320`, standard initial/final complement. The known check value for ASCII `123456789` is `0xcbf43926`. State coverage, seed and byte order so the factory generator and bootloader agree.

CRC detects accidental corruption; anyone able to rewrite the record can recompute it. This is not authenticated identity. Factory programming, readback verification, power-failure handling and write protection are separate procedures. An incomplete record is invalid even if some fields look plausible; do not salvage an unverified MAC or revision from it.

```{figure} ../illustrations/part3/12-identity-validation.png
:name: fig-p3-identity-validation
:figclass: concept-sketch
:width: 100%
:alt: A hypothetical EEPROM's complete 64-byte identity record passes version, length, CRC, field and combination checks before selecting an allowed DTB. An invalid record keeps boot closed.

Validate the complete record before trusting any field to select hardware. CRC detects corruption, not authenticated identity. The EEPROM is an optional lab addition, absent from the supplied stock MINI schematics.
```

## 24D.4  Files changed in this chapter

| File | Responsibility |
|------|----------------|
| `configs/mx6ull_pa_mini_defconfig` | Late init and driver-model I2C; commands only for diagnosis. |
| `arch/arm/dts/imx6ull-pa-mini.dts` | EEPROM bus/pads in U-Boot's control DT. |
| `board/myorg/mx6ull_pa_mini/mx6ull_pa_mini.c` | Decode, validate, map and publish the identity. |
| `include/configs/mx6ull_pa_mini.h` | Boot helpers consume the selected filename/configuration. |

Keep manufacturing identity separate from user boot preferences. The code overwrites the volatile selection on each boot; it does not save auto-detected values.

## 24D.5  Enable the useful configs

Retain 24B's `BOARD_LATE_INIT`, `DM_I2C`, `SYS_I2C_MXC`, control-DT/pinctrl support and hush. The MAC helper example also assumes the network/environment support from 24C. `CMD_I2C` is a diagnostic convenience, not required by the decoder.

For **separate DTBs**, retain `CMD_BOOTZ`, `CMD_MMC`, `CMD_FS_GENERIC` and the chosen filesystem from 24C. For **FIT**, additionally enable:

```text
CONFIG_FIT=y
CONFIG_FIT_FULL_CHECK=y
CONFIG_SHA256=y
CONFIG_CMD_BOOTM=y
```

For manual overlays, additionally enable:

```text
CONFIG_CMD_FDT=y
CONFIG_OF_LIBFDT_OVERLAY=y
```

Neither FIT nor overlays are needed merely to read identity. No legacy `i2c_read()`/global-bus API or `setexpr` byte reinterpretation is used. Configure in a private out-of-tree build with `. ~/imx6ull/scripts/env.sh` and `CROSS_COMPILE=arm-none-linux-gnueabihf-`, as in 24B.

## 24D.6  Manual EEPROM read first

For a later read-only test **with the proposed EEPROM add-on fitted** and the documented I2C1 route enabled:

```text
=> i2c bus
=> i2c dev 0
=> i2c probe 50
=> i2c md 50 00.1 40
```

The hexadecimal length `40` reads all 64 bytes, including CRC. `.1` matches only the proposed one-byte-offset part. Probe only the documented address; do not scan an unknown bus. An ACK at `0x50` does not prove a particular EEPROM or record exists.

Record the actual dump, then compare it with the format table. Erased `ff` bytes, all-zero bytes, a missing terminator or bad CRC should fail. There is no fabricated factory dump to copy and no `i2c mw` exercise.

## 24D.7  Board code to read identity

These are complete helpers for the proposed format, to add to the existing board C file. Merge their includes with 24B's includes at the top, once each. Parsing uses bytes explicitly, avoiding host structure padding, unaligned loads and implicit endianness.

```c
#include <dm.h>
#include <env.h>
#include <i2c.h>
#include <net.h>
#include <stdio.h>
#include <string.h>
#include <linux/errno.h>
#include <u-boot/crc.h>

#define PA_MINI_ID_LEN 64

struct pa_mini_id {
    u8 hw_rev;
    u8 lcd_opt;
    u8 eth_opt;
    u8 mac[6];
    char serial[16];
};

static int pa_mini_decode_id(const u8 *raw, size_t len,
                             struct pa_mini_id *id)
{
    struct pa_mini_id decoded = { 0 };
    u32 stored_crc;
    unsigned int record_len;
    size_t i, serial_len;

    if (!raw || !id || len != PA_MINI_ID_LEN)
        return -EINVAL;
    if (memcmp(raw, "PAMID01\0", 8) || raw[8] != 1)
        return -EINVAL;
    record_len = (unsigned int)raw[10] | ((unsigned int)raw[11] << 8);
    if (record_len != PA_MINI_ID_LEN)
        return -EINVAL;
    stored_crc = (u32)raw[60] | ((u32)raw[61] << 8) |
                 ((u32)raw[62] << 16) | ((u32)raw[63] << 24);
    if (stored_crc != crc32(0, raw, 60))
        return -EBADMSG;
    if (raw[9] || raw[15])
        return -EINVAL;
    for (i = 22; i < 32; i++)
        if (raw[i])
            return -EINVAL;
    for (i = 48; i < 60; i++)
        if (raw[i])
            return -EINVAL;
    if (raw[12] != 1 || raw[13] > 2 || raw[14] != 1)
        return -ENODEV;
    if (!is_valid_ethaddr(raw + 16))
        return -EINVAL;

    for (serial_len = 0; serial_len < 16 && raw[32 + serial_len];
         serial_len++) {
        u8 c = raw[32 + serial_len];

        if (!((c >= 'A' && c <= 'Z') || (c >= 'a' && c <= 'z') ||
              (c >= '0' && c <= '9') || c == '-'))
            return -EINVAL;
    }
    if (!serial_len || serial_len == 16)
        return -EINVAL;
    for (i = serial_len; i < 16; i++)
        if (raw[32 + i])
            return -EINVAL;

    decoded.hw_rev = raw[12];
    decoded.lcd_opt = raw[13];
    decoded.eth_opt = raw[14];
    memcpy(decoded.mac, raw + 16, 6);
    memcpy(decoded.serial, raw + 32, serial_len);
    *id = decoded;
    return 0;
}

static int pa_mini_read_id(struct pa_mini_id *id)
{
    struct udevice *chip;
    u8 raw[PA_MINI_ID_LEN];
    int ret;

    ret = i2c_get_chip_for_busnum(0, 0x50, 1, &chip);
    if (ret)
        return ret;
    ret = i2c_set_chip_offset_len(chip, 1);
    if (ret)
        return ret;
    ret = dm_i2c_read(chip, 0, raw, sizeof(raw));
    if (ret)
        return ret;
    return pa_mini_decode_id(raw, sizeof(raw), id);
}

static int pa_mini_apply_id(const struct pa_mini_id *id)
{
    static const char *const configs[] = {
        "conf-no-lcd", "conf-lcd43", "conf-lcd70"
    };
    static const char *const dtbs[] = {
        "imx6ull-pa-mini-no-lcd.dtb",
        "imx6ull-pa-mini-lcd43.dtb",
        "imx6ull-pa-mini-lcd70.dtb"
    };
    const char *serial;
    u8 existing_mac[6];

    if (id->hw_rev != 1 || id->lcd_opt > 2 || id->eth_opt != 1)
        return -ENODEV;
    serial = env_get("serial#");
    if (serial && strcmp(serial, id->serial))
        return -EEXIST;
    if (!serial && env_set("serial#", id->serial))
        return -EIO;
    if (env_get("ethaddr")) {
        if (!eth_env_get_enetaddr("ethaddr", existing_mac) ||
            memcmp(existing_mac, id->mac, 6))
            return -EEXIST;
    } else if (eth_env_set_enetaddr("ethaddr", id->mac)) {
        return -EIO;
    }
    if (env_set_ulong("board_rev", id->hw_rev) ||
        env_set_ulong("lcd_opt", id->lcd_opt) ||
        env_set_ulong("eth_opt", id->eth_opt) ||
        env_set("fdtfile", dtbs[id->lcd_opt]) ||
        env_set("fitconf", configs[id->lcd_opt]))
        return -EIO;
    return env_set("identity_ready", "1") ? -EIO : 0;
}

static int pa_mini_identify(void)
{
    struct pa_mini_id id;
    int ret;

    if (env_set("identity_ready", "0") || env_set("fdtfile", NULL) ||
        env_set("fitconf", NULL))
        return -EIO;
    ret = pa_mini_read_id(&id);
    if (ret)
        return ret;
    return pa_mini_apply_id(&id);
}
```

The output structure is assigned only on complete success. The stack buffer is fixed at 64 bytes; an untrusted length never controls an allocation or read size. The CRC is mandatory and covers options, MAC, serial and all reserved bytes. All I2C/binding failures propagate.

Publication is not an atomic environment transaction: earlier diagnostic assignments can remain if a later assignment fails. `identity_ready` is therefore cleared first and set **last**. The boot gate must remain closed on any error. Inspect diagnostics as provisional until readiness is 1.

The MAC validator rejects zero and multicast/broadcast, not duplicates or addresses you do not own. Factory allocation/readback must enforce uniqueness and address ownership. For lab fixtures use unique locally administered unicast addresses, never a copied public MAC. A record with missing serial or invalid MAC fails as a whole under this example's contract. A different product can define an explicit optional-field version; it should not silently weaken this one.

The helper assumes the sole interface is Ethernet sequence 0 and therefore sets `ethaddr`, as in 24C. A port using sequence 1 must deliberately map its address to `eth1addr`; a multi-port board needs a record with separately allocated addresses and its own validated mapping, not reuse of this one-port record.

Existing `serial#`/`ethaddr` must match, or selection stops. This catches stale or conflicting saved identity without requiring `CONFIG_ENV_OVERWRITE`. Clearing/reconciling those protected variables is a deliberate service operation, not a default lab step.

In the **EEPROM-equipped exercise only**, insert this fragment into the **single** `board_late_init()` from 24B, immediately after successfully installing its blocked `bootcmd` and before any enabled temperature/key dispatch. Do not install this mandatory reader on a stock MINI with no EEPROM:

```c
    ret = pa_mini_identify();
    if (ret) {
        printf("Board identity blocked boot: %d\n", ret);
        return 0;
    }
```

The order is now: close boot gate, identify, check temperature **if that add-on is part of this build**, read stock KEY0, then open exactly one path. Never let a later successful check undo an earlier failure. Network initialization occurs after this hook, so a successful identity can supply its MAC before normal Ethernet initialization.

## 24D.8  Boot with separate DTB files

Keep 24C's load-gated path; it already uses `${fdtfile}`. A stock MINI uses a deliberately chosen DTB matching its known core/baseboard/panel, without adding `identity_ready`. For the **EEPROM-identified exercise**, replace its `normal_boot` definition with this complete environment entry:

```c
"normal_boot=if test \"${identity_ready}\" = \"1\"; then run fallback_boot; " \
    "else echo Identity not ready; false; fi\0"
```

Use the pinned hush `test` command. The readiness variable is always set to 0/1 by the identification helper; it is not a cryptographic authorization token. Loose DTB filenames on MMC and TFTP must match the allow-list, and every load must remain guarded. Do not boot whatever stale DTB happens to occupy `fdt_addr_r`.

## 24D.9  Boot with a FIT configuration

The Chapter 24E FIT uses the same `conf-no-lcd`, `conf-lcd43` and `conf-lcd70` names. Set `fitfile=multi.itb` and a separate qualified staging address such as `fit_addr_r=0x85000000`; see 24E's memory assumptions. Its guarded command is conceptually:

```text
if test "${identity_ready}" = "1"; then
    if load mmc ${mmcdev}:${bootpart} ${fit_addr_r} ${fitfile}; then
        bootm ${fit_addr_r}#${fitconf}
    else
        echo FIT load failed; false
    fi
else
    echo Identity not ready; false
fi
```

This is a **command-body fragment**; 24E.6 supplies the complete environment macro, including argument setup, verification setting and MMC initialization. `${fitconf}` comes from the allow-list, not arbitrary EEPROM text. There is no `conf-safe` default for unknown hardware.

## 24D.10  Boot with a base DTB plus overlay

Use overlays only for qualified optional hardware on a common base. Identity selects an allow-listed overlay set; a filename from unvalidated EEPROM must not become a command.

U-Boot's control DT is already in use by driver model. Apply overlays to a separately loaded **OS DTB** selected as the working FDT, never to `fdt addr -c` or `fdtcontroladdr`. An OS overlay does not retroactively change U-Boot's devices or early DDR setup.

Chapter 24E supplies a complete, harmless host overlay pair and a guarded manual flow. Both label-referencing base and overlay must be compiled with `dtc -@`. Reserve room to grow the base without touching the overlay/kernel. In the pinned command, `fdt resize 2000` means **hexadecimal `0x2000`**, or 8192 extra bytes.

On apply failure, treat both buffers as unusable and reload both originals before retrying. Do not boot the base as an automatic fallback after an overlay error; a product needs an independently qualified no-overlay path to make that choice.

## 24D.11  What if identity is missing?

| Failure | This example's behavior |
|---------|-------------------------|
| Bus/read/probe error | Closed boot gate, error reported. |
| Wrong magic, version, length or CRC | No record fields published as trusted selections. |
| Unknown revision/options | Stop; do not infer a nearest variant. |
| Missing/invalid MAC or serial | Incomplete record rejected. |
| Conflicting saved identity | Stop for deliberate service reconciliation. |
| Environment publication failure | Keep the gate closed; do not boot partially updated state. |

This table applies to a build that **requires the add-on record**. On a stock MINI, the expected absence of an EEPROM is not a damaged factory identity: omit this reader and select the documented fixed hardware explicitly. Do not invent a valid record, salvage partial fields, or force `identity_ready=1` to conceal an error in the add-on mode.

A known recovery image may be an alternative, but only if it is electrically compatible with **every** board that can reach it. Calling an image "safe" does not establish that property. The prompt itself permits bypass by an operator; production trust requires more than this mutable environment policy.

## 24D.12  Lab

1. Generate the proposed records as **host files**, including a valid CRC and unique local lab MACs. No EEPROM write is required.
2. Test all three LCD values plus wrong revision/Ethernet combinations.
3. Test short/long buffers, length/endian errors, missing NUL, embedded invalid serial bytes, nonzero reserved bytes and CRC corruption.
4. Test all-zero, broadcast and multicast MACs, matching saved identity, conflicts and failed environment assignments.
5. Confirm no failure publishes readiness or opens `bootcmd`. Keep a sentinel output structure to detect partial decoder writes.
6. Only with verified EEPROM hardware, compare a read-only dump and the decoder. Do not corrupt live identity to exercise failure paths.

Factory provisioning and persistence require their own reviewed process on deliberate spare devices/media. They are not exercises in this chapter.

## 24D.13  Pitfalls

- **C structure as storage format.** Padding and endianness are not a wire contract.
- **Magic-only validation.** A plausible prefix says nothing about completeness or corruption.
- **Unbounded serial.** Never pass an unterminated EEPROM array to string APIs.
- **Wrong EEPROM address scheme.** Pointer width and bank-in-address behavior are part-specific.
- **Late RAM selection.** DDR is already working when this hook runs.
- **Partial publication.** Use a final readiness marker and keep dispatch closed on errors.
- **CRC mistaken for trust.** A writable record with a recomputable CRC is not authenticated.

## 24D.14  Going deeper

- [I2C declarations](https://github.com/u-boot/u-boot/blob/v2026.04/include/i2c.h) and [implementation](https://github.com/u-boot/u-boot/blob/v2026.04/drivers/i2c/i2c-uclass.c): bus lookup, offsets and binding failures.
- [CRC implementation](https://github.com/u-boot/u-boot/blob/v2026.04/lib/crc32.c): the exact factory/bootloader CRC contract.
- [Ethernet validity helpers](https://github.com/u-boot/u-boot/blob/v2026.04/include/net-common.h) and [environment API](https://github.com/u-boot/u-boot/blob/v2026.04/include/env.h): validity versus ownership, and assignment status.
- [Manual overlays](https://github.com/u-boot/u-boot/blob/v2026.04/doc/usage/fdt_overlays.rst) and [FIT overlays](https://github.com/u-boot/u-boot/blob/v2026.04/doc/usage/fit/overlay-fdt-boot.rst): OS tree construction, not control-DT replacement.

---

**Previous:** [Chapter 24C: Ethernet fallback boot in U-Boot](ch24C-uboot-ethernet-fallback-boot.md)

**Next:** [Chapter 24E: Multi-variant FIT images and DT overlays](ch24E-multi-variant-fit.md)
