---
chapter: 125
title: Field updates (RAUC, SWUpdate, Mender)
part: VIII — Debug, production, advanced
estimated_pages: 20
status: draft
---

# Chapter 125 — Field updates

> **Privilege boundary:** $ means normal user. # or sudo means root and can change host or target state.
> After a privileged command, verify the expected device, service, or file appears before continuing. Roll back by undoing the config change or stopping the service you just enabled.


> **Lab vs production:** Do not burn fuses, enroll production keys, or sign release images while following the lab.
> Use throwaway keys and back up the unsigned image plus the key directory before testing irreversible security flows.


> **What:** **over-the-air (OTA) firmware update** systems for shipped embedded Linux products. Three options compared: **RAUC** (Robust Auto-Update Client — German rail-grade, simple, well-fit Yocto), **SWUpdate** (Toradex-originated, flexible, complex), **Mender** (commercial-style with hosted backend. also self-host). Each implements **A/B partitioning** + atomic update + rollback. We design a complete OTA flow: build → sign → host → device pulls + verifies + installs → reboots into new partition → marks "good" if boot completes → fall-back to other partition if not.
> **RAUC** - an embedded update framework for signed A/B image installation and rollback.
> **Yocto** - a metadata-driven build system for producing custom Linux distributions.
>
> **Why:** most shipping products need a way to deliver updates. Bug fixes, security patches, new features — all delivered after the box leaves your hand. The risk: a botched update bricks 10,000 devices. The mitigation: atomic A/B updates + rollback on boot failure. Get the OTA architecture right and you can ship updates weekly. Get it wrong and one bad update can disable thousands of devices in the field.
>
> **Focus:** A/B is the standard pattern:
> - two rootfs partitions;
> **MCU bridge:** Think of the rootfs as the firmware image's file-backed runtime environment. On an MCU you link everything into flash. On Linux, programs and config live in this mounted tree.
> **rootfs** - root filesystem, the directory tree mounted at / that contains /bin, /etc, /dev, and libraries.
> - the running kernel mounts one;
> - an update writes to the other;
> - the bootloader switches to the new one on next reboot;
> - if the new one fails to reach a "we're good" marker within a deadline, the bootloader reverts to the old one.
>
> The complexity is everywhere else. The open questions are:
> - Who hosts the update bundle?
> - How is it signed (Ch 124's keys)?
> - How does the device know an update is available?
> - What if the user's WiFi drops mid-download?
> - How do you stage rollouts (10 % → 50 % → 100 %)?
>
> These systems address all of them.
>
> **Tooling.** This chapter uses `rauc` *or* `swupdate` *or* `mender-client` (pick one), plus `casync` for delta-update chunking.
> - **Ubuntu-base (target):** `apt install rauc casync  # or: swupdate, or mender-client`
> - **Buildroot:** `BR2_PACKAGE_RAUC=y BR2_PACKAGE_CASYNC=y  # or BR2_PACKAGE_SWUPDATE=y / BR2_PACKAGE_MENDER=y`
> **Buildroot** - a configuration-driven build system that produces a complete root filesystem and related images.
> - Full per-tool reference: [Userspace tooling appendix](../part5-rootfs/appendix-tooling.md).


## 125.1  Comparison

| | RAUC | SWUpdate | Mender |
|---|---|---|---|
| Origin | Pengutronix (Germany) | Toradex (Switzerland) | Northern.tech (Norway) |
| License | LGPL | GPL | Apache 2.0 (client); commercial backend optional |
| Bundle format | "RAUC bundle" (squashfs+manifest+signature) | CPIO archive with metadata | Mender artifact (.mender) |
| Signing | OpenSSL/PKCS#11 + X.509 cert chain | OpenSSL CMS | Mender's own |
| Update transports | local, web pull, HTTP streaming | local, HTTP, local-update | local, mender server (cloud or self-hosted) |
| A/B + rollback | yes | yes | yes |
| Delta updates | optional (casync) | yes (bsdiff style) | yes (binary delta) |
| Backend / cloud | none (you build your own) | none | Mender Hosted (paid) or self-host |
| Yocto integration | excellent (meta-rauc) | excellent (meta-swupdate) | excellent (meta-mender) |
| Buildroot integration | yes | yes | yes |
| Use case | EU industrial; vendor-rolled-back-end | Toradex ecosystem; complex updates | "I want a hosted SaaS" or "I want it just to work" |

**Pick guide:**
- **RAUC** — control freaks. You write your own backend. LGPL OK.
- **SWUpdate** — complex update scenarios (e.g., updating only FPGAs, only a partition's worth of files).
- **Mender** — fastest time-to-deployment. willing to pay for hosted backend. or self-host the open-source server.

## 125.2  A/B partition design

```
   SD/eMMC layout
   ┌─────────────────────────────────────────────────┐
   │ U-Boot (raw, offset 1 KB)                        │
   ├─────────────────────────────────────────────────┤
   │ U-Boot env (env partition)                        │  ← which slot to boot
   ├─────────────────────────────────────────────────┤
   │ /boot (FAT, 64 MB) — kernel + DTB per slot        │
   │   boot/zImage.a    boot/imx6ull-myboard.a.dtb     │
   │   boot/zImage.b    boot/imx6ull-myboard.b.dtb     │
   ├─────────────────────────────────────────────────┤
   │ rootfs.A (ext4, ~512 MB)                          │
   ├─────────────────────────────────────────────────┤
   │ rootfs.B (ext4, ~512 MB)                          │
   ├─────────────────────────────────────────────────┤
   │ /data (ext4, remaining) — persistent user data     │  ← survives updates
   └─────────────────────────────────────────────────┘
```

The bootloader knows: "current slot = A or B". Read from env var. Update flow:
1. Currently running A. Download new image. write to B.
2. Set env var: "next boot = B. previous = A".
3. Reboot.
4. U-Boot reads env. boots B's kernel.
5. Once Linux reaches a known-good state — a specific service reports active — it signals boot success via a U-Boot environment variable.
6. If step 5 doesn't happen within N seconds, U-Boot reverts to A on next power-cycle (watchdog auto-reset).

## 125.3  RAUC end-to-end

### Device side

`/etc/rauc/system.conf`:

```
[system]
compatible=mybsp-imx6ull-myboard
bootloader=uboot
mountpoint=/run/rauc

[keyring]
path=/etc/rauc/rauc-bundle.cert.pem

[slot.rootfs.0]
device=/dev/mmcblk0p2
type=ext4
bootname=A

[slot.rootfs.1]
device=/dev/mmcblk0p3
type=ext4
bootname=B
```

U-Boot env (set at first boot):

```
BOOT_ORDER="A B"
BOOT_A_LEFT=3
BOOT_B_LEFT=3
```

`BOOT_X_LEFT` counts down with each failed boot attempt. reaches 0 → fall back to the other slot.

U-Boot script:

```
=> setenv bootcmd 'rauc_boot'
=> setenv rauc_boot 'if test "${BOOT_ORDER%%* *}" = "A"; then \
                       run boot_a; \
                     else \
                       run boot_b; \
                     fi'
=> setenv boot_a 'load mmc 0:1 ${kernel_addr_r} zImage.a; \
                  load mmc 0:1 ${fdt_addr_r} imx6ull-myboard.a.dtb; \
                  setenv bootargs "console=ttymxc0,115200 root=/dev/mmcblk0p2 rauc.slot=A"; \
                  bootz ${kernel_addr_r} - ${fdt_addr_r}'
=> setenv boot_b '... mmcblk0p3 rauc.slot=B'
```

After Linux boots to a known-good state, user-space calls:

```sh
rauc status mark-good
```

This sets `BOOT_X_LEFT=3` again (full credit) and is the "we're alive" signal.

### Building a bundle

```
# meta-mybsp/recipes-core/bundles/myapp-bundle.bb
inherit bundle
RAUC_BUNDLE_COMPATIBLE = "mybsp-imx6ull-myboard"
RAUC_BUNDLE_VERSION = "${PV}"
RAUC_BUNDLE_DESCRIPTION = "MyApp ${PV} OTA bundle"

RAUC_BUNDLE_SLOTS = "rootfs"
RAUC_SLOT_rootfs = "myapp-image"
RAUC_SLOT_rootfs[fstype] = "ext4"

RAUC_KEY_FILE ?= "${TOPDIR}/keys/rauc-bundle.key.pem"
RAUC_CERT_FILE ?= "${TOPDIR}/keys/rauc-bundle.cert.pem"
```

`bitbake myapp-bundle` produces `myapp-bundle-1.0.raucb` — a signed bundle.

### Device-side install

```sh
# Local install (via USB stick or scp)
rauc install /mnt/usb/myapp-bundle-1.0.raucb

# Streaming via HTTPS
rauc install https://updates.example.com/imx6ull/myapp-bundle-1.0.raucb
```

RAUC verifies the signature against the keyring, writes to the inactive slot, updates bootloader env, reboots.

After reboot to new slot, if all OK:

```sh
rauc status mark-good
```

If something fails (e.g., your watchdog daemon never says "OK"), U-Boot reverts on next reboot.

## 125.4  Network architecture

```
   Developer pushes update → CI builds bundle → upload to artifact store
                                                          │
                                                          ▼
                                                  ┌──────────────┐
                                                  │  HTTPS server  │  (S3, nginx, custom)
                                                  └──────┬───────┘
                                                          │
                                  Device polls (e.g., every hour):
                                  GET https://updates.example.com/imx6ull/latest.json
                                                          │
                                                          ▼
                                                  {"version": "1.0.1", "url": "..."}
                                                          │
                                  Device compares with installed version;
                                  if newer → rauc install <url>
```

You build the "device polling" daemon yourself. RAUC provides the install primitive but no scheduler / staging logic.

For staged rollouts: serve different `latest.json` to different device IDs (canary 10 %, then 50 %, then 100 %).

For privacy, each device authenticates with its own client TLS certificate, provisioned at manufacturing time. The server checks per-device permissions.

## 125.5  Delta updates with casync

A 1 GB rootfs is too big to push over LTE every week. **casync** (Lennart Poettering's tool) chunks images. only changed chunks transfer:

```sh
# Build a casync index
casync make rootfs.caidx /path/to/rootfs/

# Each rootfs.caidx is a 1 MB index pointing to chunks in a chunk store
# Device downloads only the chunks it doesn't already have
```

RAUC integrates with casync via `RAUC_CASYNC_BUNDLE = "1"`. Typical delta: 5–50 MB instead of 500 MB. Massive savings on cellular fleet.

## 125.6  SWUpdate's strengths

SWUpdate's `sw-description` file is more flexible than RAUC's bundle format:

```
software = {
    version = "1.0.1";
    images: ({
        filename = "rootfs.ext4";
        device = "/dev/mmcblk0p3";    # or @slot.B
        sha256 = "abc...";
    });
    scripts: ({
        filename = "preinstall.sh";
        type = "shellscript";
    });
}
```

You can update:
- A rootfs partition.
- A single file in the rootfs (`/usr/bin/myapp`).
- An FPGA bitstream.
- A kernel module.
- Run pre/post-install scripts.

For products with non-uniform update needs (e.g., the rootfs rarely changes but the FPGA config updates monthly), SWUpdate wins.

## 125.7  Mender's strengths

Mender ships a **complete server stack** (frontend, REST API, artifact storage). Self-host or use Mender's hosted SaaS.

```sh
# Build a mender artifact in Yocto
inherit mender-full
INHERIT += "mender-full"
MENDER_DEVICE_TYPE = "imx6ull-myboard"
```

Result: a `core-image-base-imx6ull-myboard.mender` file.

Push to Mender server:

```sh
mender-cli artifacts upload --description "Bug fix release" core-image-base.mender
mender-cli deployments create --artifact-name 1.0.1 --device-group production
```

The server orchestrates: which devices get it, how many at a time, monitor success rate, auto-pause on failure threshold.

For teams that don't want to build their own backend, Mender is the fastest path.

## 125.8  Boot-success detection — the actually-hard part

Defining "boot succeeded" matters. Options:

- **Service-based**: a critical systemd service started OK (e.g., `myapp.service`).
- **Connectivity-based**: device reaches a heartbeat URL within 60 s.
- **Application-based**: the app processes ≥1 request without crashing.
- **Manual**: user presses a "looks fine" button (development only).

Each has a trade-off:
- Service-based misses bugs that crash the service later (5 minutes after boot).
- Connectivity-based misses bugs that prevent network setup.
- Application-based is best but requires app-side instrumentation.

Pattern in production: combine 2–3. "Service started + heartbeat seen + ≥1 user request processed in 10 min" → mark good.

If conditions not met: watchdog fires. reboot. U-Boot reverts. You're back on the previous version. alert sent.

## 125.9  Lab

1. **Set up A/B partitions.** Modify your .wks to create rootfs.A and rootfs.B partitions. flash. verify both exist (`lsblk`).
2. **U-Boot env for slot selection.** Add the `BOOT_ORDER`/`BOOT_A_LEFT` env vars. write a U-Boot bootcmd that selects based on them.
3. **Install RAUC.** `IMAGE_INSTALL += "rauc"`. Build. Verify `rauc status` runs on the target.
4. **Build a bundle.** Bitbake the `myapp-bundle.bb`. Inspect with `rauc info myapp-bundle-1.0.raucb`.
5. **Local install.** Copy bundle to target via scp. `rauc install`. Reboot. Verify other slot is now active.
6. **Mark good.** After verifying the new slot is healthy, `rauc status mark-good`. Reboot. verify still on new slot.
7. **Force a bad update.** Build a bundle whose `myapp` crashes immediately. Install. Reboot. Watchdog should fire. U-Boot reverts.
8. **HTTPS pull.** Set up nginx with a self-signed cert. serve a bundle. Device pulls via `rauc install https://...`.
9. **Delta update.** Enable casync in your bundle build. Compare bundle sizes before/after. reach 5–10× smaller delta.
10. **Mender stretch.** Self-host the Mender server (Docker compose). register a device. push a deployment from the UI.

## 125.10  Pitfalls

- **No watchdog → no rollback enforcement.** If your "mark good" check doesn't run, U-Boot still boots the new slot forever. Watchdog (Ch 51A) is mandatory for safe OTA.
- **Power loss mid-update.** If you write to the inactive partition + lose power mid-write, the inactive partition is corrupt. Next boot uses the *active* (= old) slot. old still works → no harm. But: if you flip the bootloader pointer *before* writing finishes, you brick. Write-then-flip ordering matters.
- **Bundle signed with wrong key.** Device's keyring doesn't include this key. install rejected. Verify keys deployed to fleet match signing keys.
- **Key compromise.** Same as Ch 124: stolen signing key = attacker can ship arbitrary firmware. Use HSMs. rotate.
- **Anti-rollback missing.** Attacker can install old (vulnerable) versions. Add version-number check in update logic.
- **Persistent data clobbered.** `/data` lost because update wrote new image and didn't preserve it. Keep `/data` in a separate partition.
- **Network failure mid-download.** RAUC's HTTPS streaming handles resume. bundle downloads can survive disconnect. Test it.
- **Bundle larger than rootfs partition.** Won't fit. Provision rootfs partitions 1.5× expected size to allow growth.
- **Bundle version not incremented.** Device says "I already have 1.0.0, nothing to do." Always increment.
- **Rolling out untested update.** Stage: dev → 10 % canary → 50 % → 100 %, with auto-pause on >5 % failure rate.
- **Cellular fleet downloading 500 MB each.** Use delta updates (casync). else your data bill is shocking.
- **Updates breaking customer's customizations.** A user-modified `/etc/foo` is overwritten by the update. Document. warn customers. provide a /etc/local-overrides mechanism.

## 125.11  Going deeper

- **RAUC documentation** — https://rauc.readthedocs.io/.
- **SWUpdate documentation** — https://sbabic.github.io/swupdate/.
- **Mender documentation** — https://docs.mender.io/.
- **`meta-rauc` + `meta-rauc-community`** layers — for Yocto integration.
- **`casync`** — for delta updates.
- **U-Boot's `env` command + `setenv saveenv`** — the persistent state at the heart of slot selection.
- **Pengutronix blog posts on RAUC** — many production case studies.
- **`mender-cli` + `mender-cli api`** — for CI integration.
- **NIST SP 800-189: Resilient Interdomain Traffic Exchange** — for fleet-OTA threat models.
- **Ch 51A** — watchdog (mandatory companion).
- **Ch 121A** — CI for building bundles.
- **Ch 124** — secure boot for ensuring updates are authentic.

---

> Next chapter: **Chapter 125A — VSCode + gdbserver remote-debug workflow**.
