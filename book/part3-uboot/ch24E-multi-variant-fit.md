---
chapter: "24E"
title: Multi-variant FIT images and DT overlays
part: III - U-Boot, deeply
estimated_pages: 14
status: draft
---

# Chapter 24E: Multi-variant FIT images and DT overlays

A FIT configuration is a set of references: this kernel, this DTB, and optionally this ramdisk or overlay sequence. Several configurations can share a kernel without duplicating it. One release artifact is possible, but every supported hardware combination still needs testing.

We will package the three **hypothetical common-DDR variants** from Chapter 24D and then examine overlays separately. The baseline is upstream **U-Boot v2026.04**, commit `88dc2788777babfd6322fa655df549a019aa1e69`. FIT means Flattened Image Tree. The DT-shaped container is not the OS hardware DTB stored inside it.

## 24E.1  The scenario

| Identity LCD option | FIT configuration | Payload DTB |
|---------------------|-------------------|-------------|
| 0 | `conf-no-lcd` | `imx6ull-pa-mini-no-lcd.dtb` |
| 1 | `conf-lcd43` | `imx6ull-pa-mini-lcd43.dtb` |
| 2 | `conf-lcd70` | `imx6ull-pa-mini-lcd70.dtb` |

All three share qualified early DDR, a kernel and an MMC rootfs. This example includes **no initramfs**; its arguments still point to MMC. One FIT is not automatically a full recovery image or an OTA transaction.

Actual panel timings, pinmux, power sequence and touch wiring require schematics and datasheets. Neither a panel size nor an example filename establishes those facts. Late FIT selection cannot change the ROM/DCD initialization already performed.

```{figure} ../illustrations/part3/13-fit-configuration-references.png
:name: fig-p3-fit-configuration-references
:figclass: concept-sketch
:width: 100%
:alt: Two FIT configurations reference the same kernel and different matched DTBs. The no-display configuration selects the no-display tree, while the LCD43 configuration selects its LCD43 tree.

Configurations reference payloads rather than duplicating the kernel. Two of our three proposed combinations are shown here. Hashes check bytes against stored values, but trusted required signatures and boot policy are needed for authentication.
```

## 24E.2  The .its file with three configurations

Place matching `zImage` and qualified DTBs beside this complete `multi.its`. No fallback default is specified: identity must select a supported configuration.

```dts
/dts-v1/;

/ {
    description = "mx6ull_pa_mini common-DDR variant lab";
    #address-cells = <1>;

    images {
        kernel-1 {
            description = "Shared ARM Linux zImage";
            data = /incbin/("zImage");
            type = "kernel";
            arch = "arm";
            os = "linux";
            compression = "none";
            load = <0x82000000>;
            entry = <0x82000000>;
            hash-1 { algo = "sha256"; };
        };
        fdt-no-lcd {
            description = "Qualified no-display DTB";
            data = /incbin/("imx6ull-pa-mini-no-lcd.dtb");
            type = "flat_dt";
            arch = "arm";
            compression = "none";
            hash-1 { algo = "sha256"; };
        };
        fdt-lcd43 {
            description = "Qualified 4.3-inch display DTB";
            data = /incbin/("imx6ull-pa-mini-lcd43.dtb");
            type = "flat_dt";
            arch = "arm";
            compression = "none";
            hash-1 { algo = "sha256"; };
        };
        fdt-lcd70 {
            description = "Qualified 7-inch display DTB";
            data = /incbin/("imx6ull-pa-mini-lcd70.dtb");
            type = "flat_dt";
            arch = "arm";
            compression = "none";
            hash-1 { algo = "sha256"; };
        };
    };

    configurations {
        conf-no-lcd {
            description = "No display";
            kernel = "kernel-1";
            fdt = "fdt-no-lcd";
        };
        conf-lcd43 {
            description = "4.3-inch display";
            kernel = "kernel-1";
            fdt = "fdt-lcd43";
        };
        conf-lcd70 {
            description = "7-inch display";
            kernel = "kernel-1";
            fdt = "fdt-lcd70";
        };
    };
};
```

In the prepared Bash environment (`. ~/imx6ull/scripts/env.sh`, successful status), use host tools built from the pinned source:

```sh
mkimage -f multi.its multi.itb
mkimage -l multi.itb
stat -c '%n %s bytes' multi.itb
```

These write host artifacts, not board storage. Size depends on the actual inputs; there is no promised megabyte count. Listing the FIT is not a boot or signature-validation test.

For the unsigned lab, enable `FIT`, `FIT_FULL_CHECK`, `SHA256`, `CMD_BOOTM` and the filesystem/hush support in 24D. Retain the port's ARM Linux boot support. Disable `FIT_BEST_MATCH` if omission of an explicit configuration should fail rather than attempt compatible matching. Our policy always names the configuration.

## 24E.3  Booting a specific configuration

Stage the FIT separately from its kernel destination: here `fit_addr_r=0x85000000`, while the kernel loads/enters at `0x82000000`. Do not stage this FIT at its own kernel load address and rely on an overlapping copy.

For a later qualified board test, with correct root arguments already established:

```text
=> if load mmc ${mmcdev}:${bootpart} ${fit_addr_r} multi.itb; then bootm ${fit_addr_r}#conf-lcd43; else echo FIT load failed; false; fi
```

24E.6 defines the variables and arguments. The attached `#` suffix is part of the `bootm` argument, not a shell comment. An unknown configuration fails, rather than selecting a nearby name. Without explicit selection, FIT defaults and matching options affect behavior; this FIT has no `default` property.

U-Boot resolves the selected image references, checks them according to verification policy, loads the kernel at its declared destination and prepares the OS DTB. `compression="none"` describes the outer payload; the zImage still decompresses itself. The DTB has no fixed `load` here, so U-Boot's FDT relocation policy applies. Its final address is not necessarily the FIT staging address.

Qualify usable DDR, actual sizes, kernel decompression, FDT growth/relocation, and U-Boot stack/malloc/reservations using the real RAM map and `bdinfo`. A reserved FIT window of, for example, 32 MiB at `0x85000000` is a packaging constraint, not a runtime bounds checker. These addresses do not guarantee safety for another memory size or large image.

### Hashes and trusted selection

SHA-256 detects changed payload bytes when verification runs. It does not authenticate the producer: an attacker can replace payload **and hash**. Missing hash children are not equivalent to an enforced required signature. Keep lab verification enabled and inspect hash nodes, but do not call an unsigned FIT trusted boot.

A product needs required signatures checked against trusted public keys in U-Boot's control DT, a verified chain to that U-Boot, and a policy binding the allowed kernel/DTB/overlay combination. `CONFIG_FIT_SIGNATURE=y` alone neither installs trusted keys nor requires signatures. Individually signed images without authenticated configuration policy can permit unwanted recombination. A valid signed configuration also does not prove it is allowed on this board; trusted identity and selection must decide that.

Mutable environment, alternate unsigned boot paths, prompt access, writable EEPROM identity and rollback need separate treatment. No key-enrollment, production-signing or fuse-programming procedure is provided. Read the pinned [signature design](https://github.com/u-boot/u-boot/blob/v2026.04/doc/usage/fit/signature.rst) for image versus configuration authentication.

## 24E.4  Detecting which variant we are running on

Selection happens before `bootm`, in the single 24B/24D board hook. Use `fitconf` consistently, not a second `variant` variable with different names.

### Pattern A, Strap pin

Request dedicated input descriptors, check errors, allow levels to settle and sample for stability. Follow 24B.10's ownership/polarity/cleanup method, but qualify strap timing separately from mechanical-key debounce.

This is a mapping table, not pin-reading code:

| Qualified logical state | Selection |
|-------------------------|-----------|
| 00 | `conf-no-lcd` |
| 01 | `conf-lcd43` |
| 10 | `conf-lcd70` |
| 11, changing readings or read failure | Closed gate; unsupported identity. |

No GPIO1_IO09/IO10 wiring is asserted. Do not borrow boot pins, reset outputs or peripheral pads. Floating straps cannot be fixed with a software default. GPIO5/SNVS pads need IOMUXC-SNVS configuration if actually selected.

### Pattern B, EEPROM ID

Use 24D's DM-I2C reader and full 64-byte validation: magic, version, length, CRC, options, valid MAC and bounded serial before publishing `fitconf` and `identity_ready`. It propagates binding/allocation errors and explicitly sets pointer width.

Do not substitute legacy global-bus `i2c_read()` or one unvalidated byte. Reading one byte to RAM and then using `setexpr.l` consumes a whole word, including three unrelated bytes. There is no reason to use the future kernel/FIT buffer as identity scratch space.

Factory provisioning and readback remain separate. Reprogramming live identity is not a normal boot step or a lab exercise here.

### Pattern C, eFuse

Already-provisioned, documented read-only fields may identify a chip. They require the exact fuse map, field ownership and board mapping. A one-time value is not automatically confidential or authenticated board-option data, or proof of tamper resistance.

There is no generic "spare OCOTP word" in this example and no burn guidance. Reserved/security/boot fields are not interchangeable with identity storage. Use host records or schematic-qualified straps/EEPROM reads for the exercise.

## 24E.5  DT overlays, the alternative

An overlay adds or changes nodes/properties in a base DT. It suits optional blocks on a qualified common base. It is not a general runtime deletion mechanism: DTS source deletion directives are not arbitrary deletion operations carried through `fdt apply`.

This complete **host-only pair** changes a lab property, not display/PHY/power wiring. Never pass the toy base to Linux as the MINI hardware DTB.

`lab-base.dts`:

```dts
/dts-v1/;
/ {
    model = "Host overlay fixture, not a board DTB";
    compatible = "myorg,overlay-fixture";

    lab: lab-options {
        display-option = <0>;
    };
};
```

`lab-lcd43.dtso`:

```dts
/dts-v1/;
/plugin/;

&lab {
    display-option = <1>;
};
```

Compile and merge on the host:

```sh
dtc -@ -I dts -O dtb -o lab-base.dtb lab-base.dts
dtc -@ -I dts -O dtb -o lab-lcd43.dtbo lab-lcd43.dtso
fdtoverlay -i lab-base.dtb -o lab-combined.dtb lab-lcd43.dtbo
fdtget -t x lab-combined.dtb /lab-options display-option
```

The resulting property should be 1. Both label-referencing inputs use `-@`; base symbols and overlay fixups allow the label to resolve. Real DTS files using preprocessor includes/macros need their normal build preprocessing, not an unqualified direct `dtc` call.

For optional read-to-RAM board inspection, qualify nonoverlapping `fdt_addr_r`/`fdtoverlay_addr_r` slots with `0x2000` extra bytes after the base:

```text
if load mmc ${mmcdev}:${bootpart} ${fdt_addr_r} lab-base.dtb; then
    if load mmc ${mmcdev}:${bootpart} ${fdtoverlay_addr_r} lab-lcd43.dtbo; then
        if fdt addr ${fdt_addr_r} && fdt resize 2000 && fdt apply ${fdtoverlay_addr_r}; then
            fdt print /lab-options
        else
            echo Overlay failed - reload both originals; false
        fi
    else
        echo Overlay load failed; false
    fi
else
    echo Base load failed; false
fi
```

This is a complete compound U-Boot command, shown across lines for reading, not a Bash program. It deliberately does **not** boot. `fdt addr` without `-c` selects the **working FDT**; for real boot that must be a separately loaded OS DTB, never U-Boot's live control DT at `fdtcontroladdr`.

`fdt resize 2000` parses hexadecimal: 8192 extra bytes, not decimal 2000. It changes the declared buffer size, not RAM allocation or neighboring-image bounds. Too little space causes an error, not silent truncation. Apply mutates its inputs; libfdt invalidates them on failure. Reload **both** originals before retrying. Do not boot after failure or assume the base remains untouched.

### Trade-offs vs separate DTBs

| Choice | Separate DTBs | Base plus overlays |
|--------|---------------|--------------------|
| Source maintenance | Share `.dtsi`; full DTBs need not duplicate source | Maintain shared labels and ordered sets. |
| Failure handling | Select a qualified DTB | Stop on merge failure; reload inputs. |
| Validation | Each complete board tree | Each supported final combination and ordering. |
| Shipping | Several FDT image nodes | Base/overlays can also be FIT image nodes. |

There is no universal variant-count threshold. Overlays help only when shared hardware and combinations justify their additional contracts.

For **automatic FIT overlays**, define the compiled base and overlays as separate `type="flat_dt"` image nodes, each with a hash. With `OF_LIBFDT_OVERLAY`, this is a **replacement configuration fragment**, not a complete ITS:

```dts
conf-lcd43 {
    kernel = "kernel-1";
    fdt = "fdt-base", "overlay-lcd43";
};
```

Define `fdt-base` and `overlay-lcd43` under `images` with actual data. The first FDT is the base; later entries apply in order. The pinned interface also supports `bootm <addr>#<base-config>#<extra-config>` for deliberately selected add-ons. Do not accept arbitrary extra names from unauthenticated identity. A signed design must authenticate and permit the complete selected combination.

## 24E.6  Putting it together, the full multi-variant boot script

Use 24D's C identification and 24B's gate ordering. This complete macro replaces 24C's normal path with **local FIT boot**; it does not silently fall back to unsigned network payloads.

```c
#define PA_MINI_MULTI_FIT_ENV \
    "fit_addr_r=0x85000000\0" \
    "fitfile=multi.itb\0" \
    "mmcdev=0\0" \
    "bootpart=1\0" \
    "rootdev=/dev/mmcblk0p2\0" \
    "set_fit_args=setenv bootargs console=ttymxc0,115200 " \
        "root=${rootdev} rw rootwait\0" \
    "boot_multi=if test \"${identity_ready}\" = \"1\"; then " \
        "if mmc dev ${mmcdev} && mmc rescan; then " \
            "if load mmc ${mmcdev}:${bootpart} ${fit_addr_r} ${fitfile}; then " \
                "if setenv verify yes && run set_fit_args; then " \
                    "bootm ${fit_addr_r}#${fitconf}; " \
                "else echo FIT argument setup failed; false; fi; " \
            "else echo FIT load failed; false; fi; " \
        "else echo MMC unavailable; false; fi; " \
    "else echo Identity not ready; false; fi\0" \
    "normal_boot=run boot_multi\0"
```

Merge once into `CFG_EXTRA_ENV_SETTINGS`, removing conflicting definitions of the same keys. Keep `CONFIG_BOOTCOMMAND="run normal_boot"`; the late hook still installs blocked, normal or recovery dispatch. There is no default `fitconf` in this macro.

Confirm Linux's actual root partition; U-Boot `${mmcdev}` does not establish its `/dev/mmcblk` name. Adding a FIT ramdisk later requires coordinated ITS, argument and memory changes, not simply an extra `rootfs.cpio.gz` reference.

Mutable `verify=yes` enables corruption checking in this unsigned lab. It is not required-signature enforcement or a bypass-resistant boot policy. Alternate boot routes must independently obey the final product's trust requirements.

## 24E.7  Lab

1. Build the host overlay pair; inspect the merged property and symbol/fixup nodes.
2. Make a host-only overlay reference a nonexistent label. Confirm merge failure; do not reuse its in-memory inputs.
3. Package the complete ITS with host fixtures to test references. A dummy kernel is for inspection only, never boot it.
4. Test 24D's three valid identities and invalid records against the FIT configuration names.
5. In sandbox/mock dispatch, inject readiness, MMC, FIT-load and argument failures; confirm `bootm` is reached only after success.
6. Only after real DTBs, kernel, RAM map and identity are qualified, test each configuration on matching hardware. Host packaging does not establish a hardware boot.

No fuse writes, production signing, EEPROM programming or saved-environment changes are needed.

## 24E.8  Pitfalls

- **One artifact mistaken for one test.** Validate every supported final combination.
- **Overlapping staging/destination.** Keep FIT clear of kernel decompression and relocated U-Boot.
- **Unknown identity mapped to a default.** No variant is automatically safe for unknown hardware.
- **Hash mistaken for authentication.** Payloads and hashes can be replaced together.
- **Control DT mistaken for OS DTB.** Do not mutate driver model's live tree.
- **Failed overlay reused.** Reload base and overlay originals.
- **Source deletion mistaken for merge behavior.** Inspect the actual resulting tree.

## 24E.9  Going deeper

- [FIT source format](https://github.com/u-boot/u-boot/blob/v2026.04/doc/usage/fit/source_file_format.rst) and [implementation](https://github.com/u-boot/u-boot/blob/v2026.04/boot/image-fit.c): references, selection and hashes.
- [FIT overlays](https://github.com/u-boot/u-boot/blob/v2026.04/doc/usage/fit/overlay-fdt-boot.rst): ordered FDT lists and extra configurations.
- [Manual overlays](https://github.com/u-boot/u-boot/blob/v2026.04/doc/usage/fdt_overlays.rst), [FDT command](https://github.com/u-boot/u-boot/blob/v2026.04/cmd/fdt.c) and [libfdt apply](https://github.com/u-boot/u-boot/blob/v2026.04/scripts/dtc/libfdt/fdt_overlay.c): working-tree mutation and errors.
- [FIT signatures](https://github.com/u-boot/u-boot/blob/v2026.04/doc/usage/fit/signature.rst) and [boot Kconfig](https://github.com/u-boot/u-boot/blob/v2026.04/boot/Kconfig): support versus required trusted signatures.

**Previous:** [Chapter 24D: Board identity and variant selection in U-Boot](ch24D-uboot-board-identity-variants.md)

**Next:** [Chapter 24F: Watchdog, bootcount, and rollback in U-Boot](ch24F-uboot-bootcount-watchdog-rollback.md)
