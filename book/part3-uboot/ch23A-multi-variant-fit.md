---
chapter: 23A
title: Multi-variant FIT images and DT overlays
part: III — U-Boot, deeply (inserted v1.2)
estimated_pages: 14
status: draft
---

# Chapter 23A — Multi-variant FIT images and DT overlays

> **What:** one FIT image that boots correctly on three different board variants — same kernel, different DTBs — with the variant selected at boot time from a strap pin or an EEPROM ID.
> **Why:** real products ship in revisions. Rev A has a 4.3" display; Rev B has a 7" display and a fan controller; Rev C drops the display and adds a Wi-Fi module. Shipping three separate images means three separate OTA targets and three release-engineering pipelines. **Shipping one image** means one OTA stream and one set of QA artifacts. PA never confronts this; mainline-shipping products always do.
> **Focus:** the **runtime-selection mechanism** — strap pin or EEPROM ID read by U-Boot before `bootm` selects which `configurations` entry to apply. Plus DT overlays, which let you patch one base DTB with small fragments rather than maintaining N full DTBs.

## 23A.1  The scenario

Picture a shipping product on the i.MX6ULL with three hardware revs:

- **Rev A:** Point Atom MINI as-is. No display.
- **Rev B:** + 4.3" RGB display, GT911 capacitive touch on I²C2.
- **Rev C:** Rev B + GT911-on-I²C2 + a small fan controller on PWM3.

You have one rootfs (the application code is the same), one kernel (the same drivers compile in, just probe-as-needed), but **three different DTBs** because each board has different peripherals enabled. You want one OTA package.

## 23A.2  The .its file with three configurations

Extend the Chapter 23 single-config FIT to three:

```its
/dts-v1/;

/ {
    description = "Multi-variant FIT for mx6ull product line";
    #address-cells = <1>;

    images {
        kernel-1 {
            description = "Linux kernel 6.x";
            data = /incbin/("./zImage");
            type = "kernel";
            arch = "arm";
            os = "linux";
            compression = "none";
            load = <0x82000000>;
            entry = <0x82000000>;
            hash-1 { algo = "sha256"; };
        };

        fdt-rev-a {
            description = "DT for Rev A (no display)";
            data = /incbin/("./imx6ull-mini-rev-a.dtb");
            type = "flat_dt";
            arch = "arm";
            compression = "none";
            hash-1 { algo = "sha256"; };
        };

        fdt-rev-b {
            description = "DT for Rev B (4.3 LCD)";
            data = /incbin/("./imx6ull-mini-rev-b.dtb");
            type = "flat_dt";
            arch = "arm";
            compression = "none";
            hash-1 { algo = "sha256"; };
        };

        fdt-rev-c {
            description = "DT for Rev C (LCD + fan)";
            data = /incbin/("./imx6ull-mini-rev-c.dtb");
            type = "flat_dt";
            arch = "arm";
            compression = "none";
            hash-1 { algo = "sha256"; };
        };

        ramdisk-1 {
            description = "Application initramfs (same for all revs)";
            data = /incbin/("./rootfs.cpio.gz");
            type = "ramdisk";
            arch = "arm";
            os = "linux";
            compression = "gzip";
            hash-1 { algo = "sha256"; };
        };
    };

    configurations {
        default = "conf-rev-a";   /* fail-safe default */

        conf-rev-a {
            description = "Rev A — no display";
            kernel = "kernel-1";
            fdt = "fdt-rev-a";
            ramdisk = "ramdisk-1";
        };

        conf-rev-b {
            description = "Rev B — 4.3 LCD";
            kernel = "kernel-1";
            fdt = "fdt-rev-b";
            ramdisk = "ramdisk-1";
        };

        conf-rev-c {
            description = "Rev C — LCD + fan";
            kernel = "kernel-1";
            fdt = "fdt-rev-c";
            ramdisk = "ramdisk-1";
        };
    };
};
```

Build:

```sh
mkimage -f multi.its multi.itb
ls -lh multi.itb
# 6.5 MB — kernel 4 MB + 3 × DTBs 200 KB + rootfs 1 MB + overhead
```

The kernel is included *once*, regardless of how many configurations reference it. Same for the rootfs. FIT does not duplicate.

## 23A.3  Booting a specific configuration

From U-Boot:

```
=> load mmc 0:1 0x82000000 multi.itb
=> bootm 0x82000000#conf-rev-b
```

The `#conf-rev-b` selects the configuration. With no `#`, the default (`conf-rev-a`) applies.

The `bootm` flow:

1. Parse the FIT header at `0x82000000`.
2. Look up `configurations/conf-rev-b`.
3. Find its `kernel`, `fdt`, `ramdisk` references.
4. Verify hashes (for unsigned FIT) or signatures (Ch 62).
5. Move/decompress each image to its `load=` address.
6. Branch to the kernel `entry=` with the DTB address in `r2`.

The whole thing is one command.

## 23A.4  Detecting which variant we are running on

The interesting part is *automating* the selection. Three common patterns.

### Pattern A — Strap pin

A GPIO is tied high or low by a populating resistor that differs by rev. U-Boot reads it in `board_late_init`:

```c
int board_late_init(void)
{
    int rev_pin = gpio_get_value(IMX_GPIO_NR(1, 9));   /* GPIO1_IO09 */
    int rev2_pin = gpio_get_value(IMX_GPIO_NR(1, 10));

    if (rev_pin == 0 && rev2_pin == 0)
        env_set("variant", "conf-rev-a");
    else if (rev_pin == 1 && rev2_pin == 0)
        env_set("variant", "conf-rev-b");
    else if (rev_pin == 0 && rev2_pin == 1)
        env_set("variant", "conf-rev-c");
    else
        env_set("variant", "conf-rev-a");   /* fail-safe */

    return 0;
}
```

Two pins encode four states. The strapping resistors are set during PCB assembly; software reads them on every boot. The env var `variant` then feeds `bootcmd`:

```
bootcmd=load mmc 0:1 0x82000000 multi.itb; bootm 0x82000000#${variant}
```

The `${variant}` is shell-substituted before `bootm` runs.

### Pattern B — EEPROM ID

A small I²C EEPROM (e.g., 24C04) has a board-ID byte written at manufacture. U-Boot reads it:

```c
int board_late_init(void)
{
    u8 id;
    i2c_set_bus_num(0);
    if (i2c_read(0x50, 0xFF, 1, &id, 1) != 0) {
        printf("WARN: failed to read EEPROM ID, defaulting to Rev A\n");
        env_set("variant", "conf-rev-a");
        return 0;
    }

    switch (id) {
        case 0x01: env_set("variant", "conf-rev-a"); break;
        case 0x02: env_set("variant", "conf-rev-b"); break;
        case 0x03: env_set("variant", "conf-rev-c"); break;
        default:
            printf("WARN: unknown EEPROM ID 0x%02x, using Rev A\n", id);
            env_set("variant", "conf-rev-a");
    }
    return 0;
}
```

Advantages over strap pins: 256 possible IDs, easy to reprogram in the field, no extra pads needed if you already have an I²C EEPROM for serial number / MAC address.

### Pattern C — eFuse

The i.MX6ULL has 96 words of OCOTP fuses. You can burn a board-ID into a dedicated fuse word at manufacture and read it from U-Boot:

```c
u32 board_id;
fuse_read(BOARD_ID_BANK, BOARD_ID_WORD, &board_id);
```

One-time programmable; uncopiable; tamper-resistant. Used in production for the security-conscious. Expensive to undo if you make a mistake — the fuse cannot be cleared.

For dev work, strap pins or EEPROM. For shipping security-critical products, eFuse.

## 23A.5  DT overlays — the alternative

Instead of N full DTBs, you can have **one base DTB** and **N overlay files** that patch it. An overlay is a small DTS fragment that says "add this node, modify this property, delete this other thing." U-Boot applies the overlay before passing the DT to the kernel.

A Rev B overlay (`imx6ull-mini-rev-b.dtso`):

```dts
/dts-v1/;
/plugin/;

&i2c2 {
    status = "okay";

    gt911@5d {
        compatible = "goodix,gt911";
        reg = <0x5d>;
        interrupt-parent = <&gpio1>;
        interrupts = <11 2>;
        reset-gpios = <&gpio1 12 GPIO_ACTIVE_HIGH>;
        irq-gpios = <&gpio1 11 GPIO_ACTIVE_HIGH>;
        touchscreen-size-x = <800>;
        touchscreen-size-y = <480>;
    };
};

&lcdif {
    status = "okay";
    display = <&display0>;

    display0: display@0 {
        bits-per-pixel = <16>;
        bus-width = <24>;

        display-timings {
            native-mode = <&timing0>;
            timing0: 480x272 {
                clock-frequency = <9000000>;
                hactive = <480>;
                vactive = <272>;
                /* ... porch, sync widths ... */
            };
        };
    };
};
```

The overlay is compiled with `dtc -@ -O dtb` and shipped alongside the base DTB. U-Boot:

```
=> load mmc 0:1 0x82000000 zImage
=> load mmc 0:1 0x83000000 imx6ull-mini-base.dtb
=> load mmc 0:1 0x84000000 imx6ull-mini-rev-b.dtbo
=> fdt addr 0x83000000
=> fdt resize 8192            # room to merge
=> fdt apply 0x84000000
=> bootz 0x82000000 - 0x83000000
```

`fdt apply` merges the overlay into the base. The resulting in-memory DT is what the kernel sees.

### Trade-offs vs separate DTBs

| | One DTB per variant | Base + overlays |
|---|---|---|
| Source-tree size | N × full DTS | 1 × base + N × small overlays |
| Mistake blast radius | Localized | A bad overlay can fail to apply, falling back to base |
| Build complexity | Simple | Need `-@` flag on `dtc`; verify overlays apply cleanly |
| Symbol references | None across DTBs | Overlay references base by label; must match |
| Shipping format | N DTBs in FIT | Base + N overlays in FIT |
| Tooling support | Universal | DT overlay applying is supported in modern U-Boot (>= 2020.07) |

For a dev board with ~5 variants, separate DTBs are simpler. For a product line with ~50 variants, overlays scale better.

The Point Atom guide uses neither; it ships one image per board model. Our v1.2 approach assumes you grow into a product line where one image must support many revs.

## 23A.6  Putting it together — the full multi-variant boot script

```
# In U-Boot environment, set once:

bootcmd=run select_variant; run boot_multi

select_variant=if i2c probe 0x50; then
                  i2c read 0x50 0xFF 1 0x82000000;
                  setexpr.l id *0x82000000;
                  if test 0x${id} = 0x01; then setenv variant conf-rev-a;
                  elif test 0x${id} = 0x02; then setenv variant conf-rev-b;
                  elif test 0x${id} = 0x03; then setenv variant conf-rev-c;
                  else setenv variant conf-rev-a; fi;
                else
                  setenv variant conf-rev-a;
                fi

boot_multi=setenv bootargs console=ttymxc0,115200 root=/dev/mmcblk0p2 rw rootwait;
            load mmc 0:1 0x82000000 multi.itb;
            bootm 0x82000000#${variant}
```

That's an in-U-Boot embedded script. It probes the EEPROM, reads the ID byte, maps it to a configuration name, and `bootm`s the selected configuration.

When you receive a unit, you don't ask "which rev is this?" The unit answers itself.

## 23A.7  Lab

1. **Build a multi-config FIT** with two configurations differing only in a model-string change in the DT. Verify both boot.
2. **Add a strap-pin reader** in your custom `board_late_init`. Tie a GPIO high or low on the board; verify U-Boot reads it correctly and `env_set`s the right `variant`.
3. **Author a DT overlay.** Pick something small — add a new I²C node — and verify `fdt apply` succeeds. Confirm the kernel sees the added device (`/sys/bus/i2c/devices/...`).
4. **Make a deliberately broken overlay** (reference a label that doesn't exist in the base). Observe the `fdt apply` failure and the fallback to the base DT.
5. **Read U-Boot's `fdt apply` source.** `cmd/fdt.c` and `common/fdt_support.c`. Trace what happens when an overlay references a symbol that doesn't exist.

Commit to `code/ch23A-multi-variant-fit/`.

## 23A.8  Pitfalls

- **Hash mismatch in FIT.** If you forget `hash-1 { algo = "sha256"; };` on an image, `bootm` may print a warning and proceed (depending on config). For production, *always* hash; for signed FIT (Ch 62), hashes are mandatory.
- **Strap pin floats.** If your strap GPIO has no pull resistor and your board mounting position can leave it floating, you may read a different rev on every boot. Always pull explicitly.
- **EEPROM I²C address collision.** Many boards have multiple I²C devices at `0x50`-`0x57`. Verify your ID byte location vs sensor addresses.
- **Overlay `dtc` without `-@`.** Without `-@`, no symbol table is emitted, and overlays can't reference labels in the base. Always `dtc -@`.
- **`fdt resize` skipped.** Without it, applying an overlay can run out of space and silently truncate. Resize generously before `apply`.
- **Configurations missing a `kernel` reference.** Boot fails. Every configuration must specify at minimum `kernel` and `fdt`.

## 23A.9  Going deeper

- **`doc/usage/fit/` and `doc/uImage.FIT/`** in U-Boot source — FIT spec, signing, multi-config.
- **Linux Documentation `Documentation/devicetree/overlay-notes.txt`** — what overlays can and cannot do.
- **DENX FIT guide** — concise + practical.
- **`tools/mkimage.c`** for FIT details. Particularly the `-r` (required) and `-K` (key) flags for signed-FIT prep.

> Next chapter: **Chapter 24 — Workflows: TFTP, NFS, USB-OTG.** With U-Boot fully under our control, we wire it into a fast development loop — edit on host, network-boot on target, no SD-card reflashing.
