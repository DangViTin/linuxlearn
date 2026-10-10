---
chapter: "24F"
title: "Watchdog, bootcount, and rollback in U-Boot"
part: "III - U-Boot, deeply"
estimated_pages: 20
status: draft
---

# Chapter 24F: Watchdog, bootcount, and rollback in U-Boot

The new kernel starts, prints a few lines, and hangs before the application
runs. On an MCU you might already have a watchdog that resets this failure.
But a reset alone repeats the same bad image. Something must remember that
this image was being tried, and choose a different one next time.

We will give U-Boot that piece of memory. Linux will confirm success only
after checking the system it actually booted. This is an **A/B policy
demonstration**, not a production updater: authentication, interrupted image
writes, metadata durability, and rescue remain separate requirements.

Start with the **MINI vendor baseline from Chapter 19**: identify the fitted
core, reach UART1 through the board's USB_TTL connector, and establish SD or
eMMC access. This chapter then develops the policy against upstream
**U-Boot v2026.04**. The `mx6ull_pa_mini` target and `imx6ull-pa-mini.dts`
are the book's modern migration work, not names for the vendor firmware.
Do not paste these APIs/configs into the older vendor tree unchanged.

The modern path uses ROM + board-matched DCD + full U-Boot, not SPL.
Chapter 22 supplies a complete, host-buildable MINI source/image candidate with
documented UART/storage wiring and a source-checked PHY-driver candidate.
Its physical operation remains unqualified. `CONFIG_ENV_IS_NOWHERE=y`
means its **environment is RAM-only**, not that the whole firmware is merely
a mock; it cannot yet implement persistent A/B. Keep the vendor baseline
available and pass the separate storage/persistence gate in Section 24F.3.

## 24F.1  The problem in one timeline

After storage and persistence are qualified, suppose A is known good and B
is a newly written candidate:

```text
persist candidate B, with attempt counter = 0
    |
next U-Boot: persist attempt 1, then try B
    |
Linux hangs before health confirmation
    |
watchdog reset: next U-Boot persists attempt 2, then tries B
    |
after the permitted attempts: choose known-good A
```

The counter records **attempts**, not detected kernel failures. A manual
reset or power loss before confirmation also consumes an attempt. A hang
without a reset gives U-Boot no opportunity to choose another slot.

| Decision | Owner |
|---|---|
| Which complete image set to try | U-Boot policy and persistent metadata |
| Whether an attempt was recorded | Bootcount backend |
| Whether the running image is healthy | Linux health service |
| Whether a stalled system resets | Hardware watchdog and feeding policy |

```{figure} ../illustrations/part3/14-boot-attempts-and-acceptance.png
:name: fig-p3-boot-attempts-acceptance
:figclass: concept-sketch
:width: 100%
:alt: An unconfirmed candidate can be retried after reset within its attempt limit or replaced by the recorded good slot. Separate Linux health checks accept the actual running candidate.

Reset gives U-Boot another decision point, not proof of success. Every candidate attempt needs recorded metadata, and Linux must identify and check the running image before accepting it. This is a policy model, not a guarantee that storage saves are durable.
```

## 24F.2  Terms

| Term | Meaning here |
|---|---|
| Slot A or B | A matching kernel, DTB, and root filesystem set |
| `active_slot` | Next slot U-Boot intends to boot; not proof of what Linux is running |
| `good_slot` | Last slot accepted by the health service |
| Candidate | Installed but not yet accepted slot |
| `bootcount` | Attempts since the candidate was armed, with backend-specific persistence |
| `bootlimit` | Limit compared with the incremented count using **greater than** |
| `altbootcmd` | Command selected instead of `bootcmd` when the limit is exceeded |

With a counter initially zero and `bootlimit=3`, counts 1, 2, and 3 try the
candidate. Count 4 selects `altbootcmd`. Zero or a missing `bootlimit` disables
the limit check. Without the alternate command the intended automatic
rollback cannot happen. See the [bootcount documentation](https://docs.u-boot.org/en/v2026.04/api/bootcount.html).

## 24F.3  Storage layout for the lab

The supplied MINI V2.2 baseboard has a **TF/microSD socket on USDHC1**. The
core-board design offers **eMMC on USDHC2 or NAND**, depending on the fitted
variant; the two flash drawings do not mean both chips are installed.
The SDIO Wi-Fi connector shares USDHC1 with the TF socket, so do not use
both during this lab. These routes are visible on MINI schematic sheets
1-2 and core sheet 4, and explained in the guide's MINI Sections 5.2.3 and
5.4.16-17.

Use an identified spare microSD as the first disposable A/B medium, leaving
the vendor baseline and accepted installation recoverable. An eMMC-core
owner can later qualify the eMMC user area separately. A NAND-core owner
can still use the microSD lab: **the MMC/PARTUUID policy below is not a NAND
or UBI updater**. Do not translate its partition numbers into NAND offsets.

Record the baseline's `mmc list`, `mmc info`, `part list`, environment
settings, and Linux storage identity before planning changes. Hardware
USDHC1/2 names do not establish U-Boot sequence numbers. Chapter 22's modern
candidate deliberately uses `ENV_IS_NOWHERE`: environment changes, candidate flags,
slot choice and bootcount cannot survive reset. `ENV_SIZE` alone reserves
no media range. Neither a vendor storage driver nor the modern MINI candidate
allocates the new A/B layout for you.

**Mandatory persistence and layout gate before hardware A/B:**

1. Qualify the actual MINI boot path, DDR, storage wiring and device identity.
   Record the U-Boot device/hardware partition and the corresponding Linux
   device; controller numbering is not interchangeable between them.
2. Review a complete byte-range map for that medium: ROM boot image,
   partition-table metadata, environment copy or copies, and both slots.
   Reserve non-overlapping ranges explicitly, including any backup partition
   table. No MINI offset or partition allocation is supplied by this chapter.
3. Select a persistent environment backend supported by that storage and
   configure its approved device, hardware partition, offset, size and any
   redundancy. Replace `ENV_IS_NOWHERE` only in this qualified hardware
   variant; retain it for host modeling and the nonpersistent candidate.
4. Under the approved storage-qualification procedure, establish successful
   environment writes, readback and reload across the required reset/power
   cycles, plus a defined invalid-environment/recovery path. Merely seeing a
   RAM variable change or compiling `BOOTCOUNT_ENV` does not pass this gate.
5. Before Linux can confirm an attempt, establish its matching `fw_env.config`
   from that same approved layout and compare read-only results with U-Boot.
   Keep the modern lab build's autoboot disabled until its boot
   command, load ranges and recovery policy have also been reviewed.

Without this evidence, stop at source inspection and host fixtures. This is
a prerequisite for the hardware demonstration, not production power-cut
qualification. Only after it passes may a **disposable, identified** lab
medium use the proposed layout below. The table is not a disk creation
recipe, and does not establish that any of these partitions already exist.

| U-Boot partition | Name | Content |
|---|---|---|
| `mmc 0:1` | `boot_a` | A's `zImage` and `imx6ull-pa-mini.dtb` |
| `mmc 0:2` | `rootfs_a` | A's ext4 root filesystem |
| `mmc 0:3` | `boot_b` | B's `zImage` and `imx6ull-pa-mini.dtb` |
| `mmc 0:4` | `rootfs_b` | B's ext4 root filesystem |

Confirm device identity with `mmc list`, `mmc dev 0`, `mmc info`, and
`part list mmc 0`. U-Boot MMC numbering is not Linux `/dev/mmcblkN` numbering.
We obtain the root partition's **PARTUUID**, its partition-table identity,
instead of assuming `/dev/mmcblk0p2`.

Initially A and B may have identical contents, but then kernel version alone
cannot distinguish them. Root PARTUUID and slot markers must still differ.
Later use uniquely identified kernel builds.

## 24F.4  Files changed in this chapter

| File or area | Responsibility |
|---|---|
| `configs/mx6ull_pa_mini_defconfig` | Bootcount/commands; a separately qualified persistent environment backend for the hardware variant |
| `arch/arm/dts/imx6ull-pa-mini.dts` | Watchdog availability and board reset wiring |
| `include/configs/mx6ull_pa_mini.h` | A/B defaults, merged into the existing environment once |
| Linux rootfs | Environment tools, matching storage description, per-slot identity, health service |

In the qualified persistent variant, compiled defaults do not replace a
saved environment. Inspect `printenv` after installing a build. Import only
reviewed variables; do not erase
unrelated identity/network settings with a blanket environment reset.

## 24F.5  Enable the U-Boot features

The v2026.04 fragment is:

```text
CONFIG_BOOTCOUNT_LIMIT=y
CONFIG_BOOTCOUNT_ENV=y
CONFIG_WDT=y
CONFIG_IMX_WATCHDOG=y
CONFIG_CMD_WDT=y
# CONFIG_WATCHDOG_AUTOSTART is not set
CONFIG_HUSH_PARSER=y
CONFIG_CMD_BOOTZ=y
CONFIG_CMD_MMC=y
CONFIG_CMD_PART=y
CONFIG_PARTITION_UUIDS=y
CONFIG_CMD_FS_GENERIC=y
CONFIG_CMD_EXT4=y
CONFIG_CMD_FAT=y
```

`IMX_WATCHDOG`, not `WDT_IMX2`, selects this release's i.MX driver. `WDT`
enables the driver-model watchdog API. Leave autostart off for initial
command/policy work; later qualify the watchdog handoff deliberately. Check
the generated `.config`, including filesystem support selected by commands.

`BOOTCOUNT_ENV` is not an environment-storage driver. This fragment does
not turn `ENV_IS_NOWHERE` into persistent storage; a RAM-only build can host
the policy exercise but not retain attempts. Complete Section 24F.3's gate
before hardware trials, even if the vendor baseline already saves its own
environment. Its storage map must be reconciled with the modern build and
the new slots. Do not restore EVK MMC settings as assumed MINI values.
In [bootcount_env.c](https://github.com/u-boot/u-boot/blob/v2026.04/drivers/bootcount/bootcount_env.c),
`upgrade_available` nonzero enables loading the stored count and saving each
increment through `env_save()`. With it zero, the backend loads zero and
does not save increments; a RAM `bootcount` may still appear. This backend
**does not propagate environment-save errors**. Failed persistence can defeat
the attempt bound.

Build your reviewed v2026.04 MINI migration source in its own checkout,
separate from Chapter 19's vendor source:

```sh
$ . ~/imx6ull/scripts/env.sh
$ cd ~/imx6ull/src/u-boot
$ make O="$IMX6ULL_HOME/build/uboot-ab" ARCH=arm CROSS_COMPILE="$CROSS_COMPILE" mx6ull_pa_mini_defconfig
$ make O="$IMX6ULL_HOME/build/uboot-ab" ARCH=arm CROSS_COMPILE="$CROSS_COMPILE" -j "$(nproc)"
```

Build success does not validate the MINI's DDR or reset circuit.

## 24F.6  Manual bootcount test

This cross-reset persistence test is unavailable with `ENV_IS_NOWHERE`. First
pass the mandatory gate in Section 24F.3; until then use the paper/host-mock
tests instead. Before `saveenv`, confirm the approved storage range, record
current boot variables, and keep Chapter 8 ROM recovery available. This writes persistent
metadata: use only the prepared disposable lab medium.

Temporarily make both paths stop after identifying themselves:

```text
pa-mini=> setenv bootcmd 'echo candidate path; false'
pa-mini=> setenv altbootcmd 'echo limit path; false'
pa-mini=> setenv bootlimit 3
pa-mini=> setenv bootcount 0
pa-mini=> setenv upgrade_available 1
pa-mini=> saveenv
```

Require an actual successful save before resetting. On permitted lab resets,
record the path and `printenv bootcount bootlimit`. Predict the fourth
selection before observing it. Interrupting autoboot is not a Linux failure,
but U-Boot has already incremented the counter at this stage.

Restore your recorded commands and clear candidate/count in one save when
finished. Do not leave this echo-only test as the product policy.

## 24F.7  A/B environment variables

Append this demonstration macro to the existing `CFG_EXTRA_ENV_SETTINGS`
in `mx6ull_pa_mini.h`. Remove duplicate `bootcmd`/`altbootcmd` definitions;
they need one owner. Keep the port's `CONFIG_BOOTCOMMAND` default consistent.
Use it as a host fixture before qualification, or in the hardware variant
only after Section 24F.3's gate. Do not enable the candidate's autoboot merely
because this macro compiles.

```c
#define PA_MINI_AB_ENV \
    "active_slot=A\0" \
    "good_slot=A\0" \
    "upgrade_available=0\0" \
    "bootlimit=3\0" \
    "bootcount=0\0" \
    "ab_mmc=0\0" \
    "select_slot=if test \"${active_slot}\" = \"A\"; then " \
        "setenv bootpart 0:1 && setenv rootpart 0:2; " \
    "elif test \"${active_slot}\" = \"B\"; then " \
        "setenv bootpart 0:3 && setenv rootpart 0:4; " \
    "else echo Invalid active slot; false; fi\0" \
    "boot_selected=if run select_slot && mmc dev ${ab_mmc} && " \
        "mmc rescan && part uuid mmc ${rootpart} rootuuid; then " \
        "if setenv bootargs console=ttymxc0,115200 " \
            "root=PARTUUID=${rootuuid} rw rootwait ab.slot=${active_slot}; then " \
        "if load mmc ${bootpart} ${kernel_addr_r} zImage && " \
            "load mmc ${bootpart} ${fdt_addr_r} imx6ull-pa-mini.dtb; then " \
            "bootz ${kernel_addr_r} - ${fdt_addr_r}; " \
        "else echo Slot image load failed; false; fi; " \
        "else echo Boot arguments unavailable; false; fi; " \
    "else echo Slot selection or MMC failed; false; fi\0" \
    "rollback=if test \"${upgrade_available}\" = \"1\" && " \
        "test \"${active_slot}\" != \"${good_slot}\"; then " \
        "if test \"${good_slot}\" = \"A\" || test \"${good_slot}\" = \"B\"; then " \
            "if setenv active_slot ${good_slot} && " \
                "setenv upgrade_available 0 && setenv bootcount 0 && " \
                "saveenv; then run boot_selected; " \
            "else echo Rollback metadata save failed; false; fi; " \
        "else echo Invalid good slot; false; fi; " \
    "else echo No valid pending rollback; false; fi\0" \
    "bootcmd=run boot_selected\0" \
    "altbootcmd=run rollback\0"
```

Supply qualified, non-overlapping `kernel_addr_r` and `fdt_addr_r` for the
actual hardware variant. Chapter 22 supplies a source memory layout, but
its load ranges still require physical DDR and overlap qualification for
this A/B workflow. No additional RAM addresses are guessed here. Device 0 is fixed in both
partition mappings: changing `ab_mmc` alone does not change those mappings.

The `&&` operators matter. A failed kernel or DTB load must not call `bootz`
with stale bytes from a previous attempt. If `bootz` returns an error, the
command returns to U-Boot, without accepting the image. This demo does not
immediately reset or try another slot after a load failure; manual recovery
or a qualified watchdog supplies the next decision opportunity.

The alternate path checks that a candidate is pending before changing slot
state. Recovery and power policy in Chapters 24G/H must override **both**
commands, not just the normal path.

## 24F.8  Mark slot B as candidate

Only after Section 24F.3's gate passes and all B components are written,
flushed, and verified, with accepted A preserved, arm B:

```text
pa-mini=> setenv active_slot B
pa-mini=> setenv good_slot A
pa-mini=> setenv upgrade_available 1
pa-mini=> setenv bootcount 0
pa-mini=> saveenv
```

Reset only after a successful save. `good_slot A` is valid here because the
lab already accepted A. On an A update while B is good, reverse the roles;
never hard-code A as the accepted slot in an updater.

One save groups these fields into one environment blob. It does **not** make
the storage write power-cut atomic. Candidate metadata is the final step,
not the first step before copying files.

## 24F.9  Linux marks the boot good

First prove that Linux's environment tools access the same bytes as U-Boot.
The modern NOWHERE candidate has no persistent environment bytes for these tools;
do not install or run a hardware writer against a guessed location.
There is a concrete vendor starting point to inspect: the supplied public
vendor tree's `include/configs/mx6ull_alientek_emmc.h` defines fallback MMC
environment device 1 (commented USDHC2), hardware partition 0 (user area), byte offset
`12 * 64 KiB = 0xC0000`, and size `8 KiB = 0x2000` in its MMC branch. These
are **that source target's defaults**, not authorization to use them on a
microSD, NAND variant, changed build, or repartitioned eMMC. In that vendor
tree, `mmc_get_env_dev()` in `arch/arm/cpu/armv7/mx6/soc.c` derives the device
from the boot controller when booted from SD/MMC; the board mapping can
adjust it. Thus an SD-booted session need not save to the header's device 1.
Check the generated configuration and this runtime mapping before deriving
Linux's path.
The `/etc/fw_env.config` shape below requires the approved matching layout:

```text
<matching Linux block device/hardware partition> <approved byte offset> <approved environment byte size>
```

Derive the real device, hardware partition, offset, size, and redundant copy
from your generated config and `env/mmc.c` board overrides. Offsets are bytes,
not sectors; a partition path changes the origin. eMMC boot partitions are
not user-area partitions. Compare read-only `fw_printenv` with U-Boot
`printenv` before enabling a writer. Stop on CRC/default-environment warnings
or a mismatch.

The rootfs builder must install three files under `/etc/boot-health/`:
`slot` (A or B), `root-partuuid` (the deployed root partition identity), and
`kernel-release` (intended `uname -r`). Give distinct builds distinct releases.
This script requires `findmnt`, `blkid`, `flock`, environment tools, and a
product-specific `/usr/libexec/product-health`; a minimal BusyBox image may
not contain them.

```sh
#!/bin/sh
# /usr/sbin/mark-boot-good; run as root after product readiness.
set -efu
die() { echo "mark-boot-good: $*" >&2; exit 1; }
exec 9>/run/boot-metadata.lock
flock -x 9
slot=
for word in $(cat /proc/cmdline); do
    case "$word" in
        ab.slot=*)
            [ -z "$slot" ] || die "duplicate slot token"
            slot=${word#ab.slot=}
            ;;
    esac
done
case "$slot" in A|B) ;; *) die "invalid booted slot" ;; esac
[ "$slot" = "$(cat /etc/boot-health/slot)" ] || die "rootfs slot mismatch"
[ "$(uname -r)" = "$(cat /etc/boot-health/kernel-release)" ] || die "kernel mismatch"
rootdev=$(findmnt -n -o SOURCE --target /)
case "$rootdev" in /dev/*) ;; *) die "unsupported root device" ;; esac
uuid=$(blkid -s PARTUUID -o value "$rootdev")
[ -n "$uuid" ] || die "root has no PARTUUID"
[ "$uuid" = "$(cat /etc/boot-health/root-partuuid)" ] || die "wrong mounted root"
[ "$slot" = "$(fw_printenv -n active_slot)" ] || die "metadata slot mismatch"
pending=$(fw_printenv -n upgrade_available)
case "$pending" in 0) exit 0 ;; 1) ;; *) die "invalid pending flag" ;; esac
test -x /usr/libexec/product-health || die "health check missing"
/usr/libexec/product-health || die "product unhealthy"
batch=$(mktemp /run/boot-good.XXXXXX)
trap 'rm -f "$batch"' EXIT HUP INT TERM
printf 'good_slot %s\nupgrade_available 0\nbootcount 0\n' "$slot" > "$batch"
fw_setenv -s "$batch" || die "metadata write failed"
[ "$(fw_printenv -n good_slot)" = "$slot" ] || die "good slot readback failed"
[ "$(fw_printenv -n upgrade_available)" = 0 ] || die "pending readback failed"
[ "$(fw_printenv -n bootcount)" = 0 ] || die "count readback failed"
```

The batch requests one update rather than three independent writes. All
updater/health writers must share the lock; this script cannot serialize a
writer that ignores it. The checks suit a direct block-device ext4 root,
not NFS, overlay, or device-mapper roots without adaptation.

These identity checks catch integration mistakes, not malicious substitution.
Two kernels sharing a release cannot be cryptographically distinguished
this way. Signed images and a trusted update framework provide that stronger
contract. Install the script through the rootfs build with executable
permissions, invoke it from the actual init system after readiness, and
propagate failure. Merely waiting some seconds is not a health test.

## 24F.10  Watchdog role

Read the reset circuit and watchdog DT properties before starting it.
On the supplied core schematic, `SNVS_TAMPER9` is labeled `nWDOG` and joins
the reset network; MINI's RESET button also reaches that network. A net
label is not proof that the i.MX watchdog peripheral is muxed onto that pad.
Retain the established baseline reset behavior while reviewing the modern
driver. UART1_CTS/GPIO1_IO18 belongs to the MINI KEY0 switch, and GPIO1_IO08
to RGB backlight. GPIO1_IO01 instead reaches GBC_KEY/AP_INT on this baseboard;
an inherited EVK watchdog-output pinmux there still needs its actual net and
accessory ownership reviewed, not a copied KEY0 assumption.
`fsl,ext-reset-output` changes reset routing, not generic reliability. The
v2026.04 i.MX driver has **no stop operation**; `wdt stop` cannot be relied on
to disable a started device.

For an approved idle-board reset test, select the **name** printed by the
command, not a numeric device index:

```text
pa-mini=> wdt list
pa-mini=> wdt dev <name printed by wdt list>
pa-mini=> wdt expire
```

The last command deliberately resets the board. Never run it during writes
or useful product work. `wdt start 10000; sleep 20` is not a starvation proof:
U-Boot's cyclic scheduler can keep feeding during sleep or console waits.
See [wdt usage](https://docs.u-boot.org/en/v2026.04/usage/cmd/wdt.html) and
`drivers/watchdog/wdt-uclass.c`.

Qualify the whole handoff: U-Boot starts the watchdog, Linux's built-in i.MX
driver services the same device soon enough, and userspace takes ownership
under its required `nowayout`/close policy. Choose timeouts from measured
worst-case paths, including recovery. A driver/daemon may feed independently
of application health: verify a stuck product really stops feeding.
Acceptance is a one-time event; runtime health supervision continues later.

## 24F.11  Environment storage warning

With a qualified persistent backend, each candidate attempt rewrites the
environment. Save errors do not stop this backend's bootcount logic.

| Storage choice | What still needs proof |
|---|---|
| RAM-only `ENV_IS_NOWHERE` | The complete modern candidate can use RAM variables, but cannot retain hardware rollback metadata across reset |
| Single environment | Torn write can lose policy and count; no production guarantee |
| Redundant environment | Separate ranges, CRC/selection rules, matching Linux config, power-cut behavior |
| Filesystem bootcount | Exact backend/config and interrupted filesystem write recovery; a file is not automatically atomic |
| RTC/SNVS counter | Available backend, retained-register ownership, reset/backup-loss behavior; no automatic MINI backend assumed |
| Dedicated metadata | Journal/copy protocol, generation/integrity checks, ordering, invalid-state recovery |

Redundancy does not prove controller caches are durable or copies cannot
fail together. Preserve the accepted image and commit candidate metadata
last. An environment recovered from defaults must lead to a deliberately
chosen safe path, not an accidental slot choice.

## 24F.12  Lab

1. Record the MINI base/core revision and fitted flash, then inventory the
   Chapter 19 baseline through UART1. Identify the spare TF medium without
   disturbing eMMC/NAND or attaching SDIO Wi-Fi. Trace counts 0 through 4
   with limit 3 on paper: why is the fourth entry alternate?
2. Inspect the mandatory Section 24F.3 gate. With `ENV_IS_NOWHERE` or an
   unqualified medium/layout, use only paper and host-mock tests. Hardware
   A/B must wait for the independent storage/persistence qualification.
3. After that gate passes, on the disposable medium perform Section 24F.6,
   record actual paths/counts and restore the intended A/B commands afterward.
4. Accept A, prepare B, and arm it only after verification. Disable automatic
   mark-good for the failure exercise.
5. Use permitted resets before confirmation and verify A after three B
   attempts. A missing B kernel or DTB must never reach `bootz`.
6. Add identity files and a real health check. Wrong root PARTUUID or kernel
   release must prevent confirmation.
7. Test an A candidate with B retained as good. Rollback must select B.
8. Test watchdog reset separately under the approved procedure. Model metadata
   write failure before considering controlled hardware power-cut qualification.

Keep serial logs/readbacks. Normal boot does not establish rollback; a host
policy test does not establish power-cut safety.

## 24F.13  Pitfalls

- **Calling attempts detected failures.** Reset reasons need a separate design.
- **Booting stale RAM.** Gate both loads before the kernel jump.
- **Clearing pending from the wrong system.** Check running kernel and root,
  not just metadata's intent.
- **Missing resets.** A hung Linux stays hung without a reset mechanism.
- **Assuming counts persist.** This backend ignores save errors.
- **Treating RAM variables as boot metadata.** `ENV_IS_NOWHERE` cannot retain
  state across reset; a complete firmware build does not qualify persistence.
- **Treating A/B as rescue.** Both slots and metadata can fail; keep recovery.
- **Overriding only normal boot.** Safety choices must cover `altbootcmd` too.

## 24F.14  Going deeper

- Supplied `IMX6ULL_MINI_V2.2_(Mini_base_plate_schematic).pdf`, sheets 1-2,
  and `IMX6ULL_CORE_V2.0_(core_board_schematic).pdf`, sheets 1, 4, 5-6:
  storage routes, fitted-variant choices, and reset/pad ownership.
- [Vendor eMMC target header](https://github.com/alientek-openedv/uboot-imx-rel_imx_4.1.15_2.1.0_ga_alientek/blob/edb7ca5ac4be2d978be60a2a12c61e0b6d1f7feb/include/configs/mx6ull_alientek_emmc.h):
  a baseline map to inspect, not a modern A/B allocation.
- [Bootcount API](https://docs.u-boot.org/en/v2026.04/api/bootcount.html),
  [include/bootcount.h](https://github.com/u-boot/u-boot/blob/v2026.04/include/bootcount.h),
  and [common/autoboot.c](https://github.com/u-boot/u-boot/blob/v2026.04/common/autoboot.c): increment and selection order.
- [MMC environment backend](https://github.com/u-boot/u-boot/blob/v2026.04/env/mmc.c)
  and [tool config format](https://github.com/u-boot/u-boot/blob/v2026.04/tools/env/fw_env.config).
- [Linux watchdog API](https://docs.kernel.org/watchdog/watchdog-api.html):
  feeding, timeout, and close semantics, with driver-specific limitations.
- Part VIII's update-framework chapters: authenticated images and durable
  metadata beyond this demonstration.

---

**Previous:** [Chapter 24E: Multi-variant FIT images and DT overlays](ch24E-multi-variant-fit.md)

**Next:** [Chapter 24G: Factory and recovery modes in U-Boot](ch24G-uboot-factory-recovery-usb.md)
