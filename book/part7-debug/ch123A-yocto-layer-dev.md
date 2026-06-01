---
chapter: 123A
title: Yocto layer development in depth
part: VIII — Debug, production, advanced
estimated_pages: 26
status: draft
---

# Chapter 123A — Yocto layer development in depth

> **What:** the **Yocto layer design** that production vendors use. We build a 3-layer stack: **`meta-mybsp`** (board + BSP — kernel + U-Boot + DT for `imx6ull-myboard`), **`meta-mybsp-mini`** (board variant — same SoC, smaller display), **`meta-mybsp-myapp`** (application layer — your in-house Qt app, MQTT daemon, OTA config). Plus a separate **distro layer** (`meta-mybsp-distro`) that pins package versions + DISTRO_FEATURES. We walk every meaningful concept: layer priorities, bbappend patterns, machine config, `IMAGE_FEATURES`/`DISTRO_FEATURES`, `wic` for image partitioning, `RAUC`/SWUpdate integration, and the `SRC_URI` cache so reproducible builds work offline.
> **Why:** Ch 123 chose Yocto. Now the meat of the work is *writing layers properly*. A bad layer organization makes every change a hunt across the metadata tree. A good one isolates your product from upstream, keeps variants simple, and survives upstream layer updates. Done well, Yocto becomes a tool you'd recommend. Done badly, it becomes the build system everyone hates.
> **Focus:** layers stack like CSS — later layers override earlier ones via priority. The roles are:
> - **bbappend** — extend an upstream recipe.
> - **a new `.bb`** — your own packages.
> - **machine config** — "this hardware needs these kernel modules."
> - **distro config** — "this product line needs OpenSSL 3 + systemd."
> - **image recipes** — "this final shipped image contains these packages."
>
> Get these separations right and a 5-machine, 3-distro, 10-app matrix becomes manageable. Mix them up (machine-specific stuff in distro config) and you build a tar pit.

## 123A.1  Layer anatomy

A canonical Yocto layer:

```
meta-mybsp/
├── conf/
│   ├── layer.conf                 ← who I am, my priority, my namespace
│   ├── machine/
│   │   └── imx6ull-myboard.conf   ← MACHINE definitions
│   └── distro/
│       └── mybsp-distro.conf      ← optional DISTRO definition
├── recipes-bsp/
│   ├── u-boot/u-boot-mybsp_2026.04.bb
│   └── u-boot/u-boot-mybsp_2026.04.bbappend
├── recipes-kernel/
│   └── linux/linux-mybsp_6.6.bb
├── recipes-core/
│   ├── images/myapp-image.bb
│   └── images/myapp-debug-image.bb  ← variant: includes gdb, strace
├── recipes-myapp/
│   └── myapp/myapp_1.0.bb
├── classes/
│   └── mybsp-helper.bbclass        ← shared helpers
├── files/                          ← static files for recipes to install
└── README.md
```

`conf/layer.conf` is the heart:

```python
# Layer name and priority
BBFILE_COLLECTIONS += "mybsp"
BBFILE_PATTERN_mybsp = "^${LAYERDIR}/"
BBFILE_PRIORITY_mybsp = "10"

# Recipes search paths
BBPATH .= ":${LAYERDIR}"
BBFILES += "${LAYERDIR}/recipes-*/*/*.bb \
            ${LAYERDIR}/recipes-*/*/*.bbappend"

# Layer-version compat
LAYERVERSION_mybsp = "1"
LAYERSERIES_COMPAT_mybsp = "kirkstone langdale mickledore nanbield scarthgap"
LAYERDEPENDS_mybsp = "core meta-freescale"
```

Priority `10` is higher than `meta-freescale`'s 8 — your overrides win.

## 123A.2  Machine config

`conf/machine/imx6ull-myboard.conf`:

```python
#@TYPE: Machine
#@NAME: i.MX6ULL MyBoard
#@DESCRIPTION: 528 MHz, 512 MB DDR3, FEC × 2, 1 USB

require conf/machine/include/imx6ull.inc

MACHINEOVERRIDES =. "mx6ull:"

KERNEL_DEVICETREE = "imx6ull-myboard.dtb"
UBOOT_CONFIG ??= "myboard"
UBOOT_CONFIG[myboard] = "imx6ull_myboard_defconfig,sdcard"

# Kernel modules to always install
MACHINE_EXTRA_RRECOMMENDS += "kernel-module-fec kernel-module-mwifiex-sdio"

# wic image layout
IMAGE_FSTYPES += "wic.bz2 wic.bmap"
WKS_FILE = "imx6ull-myboard.wks"

# Specific UART for serial console
SERIAL_CONSOLES = "115200;ttymxc0"
```

`require` includes shared SoC config from upstream `meta-freescale`'s `imx6ull.inc`; your machine adds board-specific overrides. The `KERNEL_DEVICETREE` selects the DT; `UBOOT_CONFIG` selects the U-Boot defconfig.

## 123A.3  Image recipes

`recipes-core/images/myapp-image.bb`:

```python
SUMMARY = "MyApp production image"
LICENSE = "MIT"

inherit core-image

IMAGE_FEATURES += "ssh-server-dropbear"

IMAGE_INSTALL += " \
    myapp \
    rauc \
    chrony \
    mosquitto-clients \
    libssl3 \
    "

# Strip debug info for production
IMAGE_INSTALL:remove = "kernel-module-*-dbg"
INHIBIT_PACKAGE_STRIP = "0"
INHIBIT_PACKAGE_DEBUG_SPLIT = "0"

IMAGE_ROOTFS_SIZE = "204800"   # 200 MB
IMAGE_OVERHEAD_FACTOR = "1.1"
```

`bitbake myapp-image` builds the rootfs with these packages, applies any IMAGE_FEATURES (ssh-server-dropbear adds dropbear ssh), produces a `.wic.bz2` for SD/eMMC flashing.

Variant for debug:

```python
# recipes-core/images/myapp-debug-image.bb
require myapp-image.bb

SUMMARY = "MyApp debug image (with gdb, strace, perf)"
IMAGE_INSTALL += "gdb gdbserver strace ltrace perf valgrind dropbear"
IMAGE_FEATURES += "debug-tweaks"
```

`bitbake myapp-debug-image` builds the same base image + debug tools. One-line difference; fully separate output artifact.

## 123A.4  Custom recipe — your app

`recipes-myapp/myapp/myapp_1.0.bb`:

```python
SUMMARY = "MyApp embedded controller"
LICENSE = "Proprietary"
LIC_FILES_CHKSUM = "file://LICENSE;md5=abc..."

SRC_URI = "git://gitlab.internal/myorg/myapp.git;protocol=ssh;branch=main"
SRCREV = "abc123def4567890abc123def4567890abc123de"   # use the full 40-char SHA1
PV = "1.0+git${SRCREV}"                               # ${SRCPV} was removed in Scarthgap
S = "${WORKDIR}/git"

DEPENDS = "libcurl mosquitto qtbase"
RDEPENDS:${PN} = "chrony mosquitto-clients"

inherit cmake systemd

SYSTEMD_SERVICE:${PN} = "myapp.service"

EXTRA_OECMAKE = "-DBUILD_TESTS=OFF"

do_install:append() {
    install -d ${D}${systemd_unitdir}/system
    install -m 0644 ${WORKDIR}/myapp.service ${D}${systemd_unitdir}/system/
    install -d ${D}${sysconfdir}/myapp
    install -m 0644 ${WORKDIR}/myapp.conf ${D}${sysconfdir}/myapp/
}

FILES:${PN} += "${systemd_unitdir}/system/myapp.service ${sysconfdir}/myapp/"
```

What's happening:
- `inherit cmake` adds `do_configure/compile/install` for CMake.
- `inherit systemd` enables auto-registration of the systemd service.
- `DEPENDS` = build-time deps; `RDEPENDS:${PN}` = runtime deps.
- `do_install:append` adds extra install steps (the systemd unit + config file).
- `FILES:${PN}` declares which paths go in the main package (vs `-dev`, `-dbg`).

Now `bitbake myapp` builds your app; `bitbake myapp-image` includes it in the rootfs.

## 123A.5  bbappend — extending upstream recipes

You need to enable an extra kernel config option. Don't fork the kernel recipe; bbappend it:

`recipes-kernel/linux/linux-imx_%.bbappend`:

```python
FILESEXTRAPATHS:prepend := "${THISDIR}/${PN}:"

SRC_URI += "file://0001-myboard-add-RFM69-driver.patch \
            file://myboard.cfg"
```

Where `myboard.cfg` is a kernel config fragment:

```
CONFIG_SPI_RFM69=y
CONFIG_IIO_RFM69=y
CONFIG_WIREGUARD=y
```

BitBake applies the patch and the config fragment automatically. You haven't forked `meta-imx`'s kernel recipe; you've augmented it. The change survives upstream layer updates.

## 123A.6  Distro vs machine vs image — separation of concerns

Distinguishing what goes where:

| Concept | What it controls | Example |
|---|---|---|
| **DISTRO** | The product *family*'s policy | "we use systemd, OpenSSL 3, glibc, en_US locale" |
| **MACHINE** | The hardware variant | "i.MX6ULL Cortex-A7 at 528 MHz with FEC × 2, no GPU" |
| **IMAGE** | The shipped artifact | "myapp + ssh + chrony, no debug tools, 200 MB rootfs" |

If you mix these (for example, putting a machine-specific kernel module into the distro config) you create surprises:
- A second machine's image gets that module unnecessarily.
- Debugging "why does machine X have this kernel module" leads you on a wild goose chase.

Always: machine-specific stuff in `machine/*.conf`; distro-wide policy in `distro/*.conf`; image content in `images/*.bb`.

## 123A.7  Layer priorities for variant management

Build a stack:

```
meta-poky                 (priority 5)   ← reference distro
meta-openembedded/meta-oe (priority 6)
meta-freescale            (priority 7)   ← i.MX SoC support
meta-freescale-3rdparty   (priority 4)   ← board-specific overrides
meta-mybsp                (priority 10)  ← our BSP layer
meta-mybsp-mini           (priority 12)  ← variant for the MINI board
meta-mybsp-myapp          (priority 15)  ← app-specific overrides
meta-mybsp-distro         (priority 20)  ← product-family-wide policy
```

When two layers ship `recipes-bsp/u-boot/u-boot-imx_%.bbappend`, the higher-priority layer's takes precedence. Use this to override BSP-defaults from your distro layer.

## 123A.8  wic — disk image layouts

`wic` (Wic Image Creator) generates partition layouts. Spec file:

`recipes-bsp/u-boot/imx6ull-myboard.wks`:

```
# Bootloader at offset 1k (i.MX SD/eMMC raw region)
bootloader --append="console=ttymxc0,115200 root=/dev/mmcblk0p2 rw rootwait"
part u-boot --source rawcopy --sourceparams="file=u-boot-dtb.imx" --ondisk mmcblk0 --no-table --align 1
part /boot --source bootimg-partition --ondisk mmcblk0 --fstype=vfat --label boot --active --align 1024 --size 16
part / --source rootfs --ondisk mmcblk0 --fstype=ext4 --label rootfs --align 1024
part swap --ondisk mmcblk0 --size 64 --label swap --fstype=swap
```

After `bitbake myapp-image`:
```sh
ls tmp/deploy/images/imx6ull-myboard/
# myapp-image-imx6ull-myboard.wic.bz2
bzcat myapp-image-imx6ull-myboard.wic.bz2 | sudo dd of=/dev/sdX bs=4M
```

Done. The wic image has the right partition table, U-Boot in the raw offset, kernel+DTB in /boot, rootfs in /, swap.

For OTA-ready layouts: add A/B partitions for RAUC.

## 123A.9  RAUC integration

```python
# In myapp-image.bb
IMAGE_INSTALL += "rauc"

# /etc/rauc/system.conf in the rootfs (via a custom recipe)
[system]
compatible=mybsp-imx6ull
bootloader=uboot
mountpoint=/mnt/rauc/bundle

[slot.rootfs.0]
device=/dev/mmcblk0p2
type=ext4
bootname=A

[slot.rootfs.1]
device=/dev/mmcblk0p3
type=ext4
bootname=B
```

And in wic file: two A/B rootfs partitions instead of one.

After deployment:
```sh
rauc install bundle.raucb
reboot
# System boots into the new slot; on success, marks it "good"
```

Ch 125 covers this in depth.

## 123A.10  SRC_URI cache — offline reproducibility

For builds you can run without internet:

```sh
# Pre-fetch everything
bitbake -c fetchall myapp-image
# Or:
bitbake --runall=fetch myapp-image

# Now downloads/ contains all source tarballs + git clones
# Archive it for offline build:
tar cf yocto-downloads.tar downloads/

# On the offline builder
tar xf yocto-downloads.tar
# In local.conf:
BB_GENERATE_MIRROR_TARBALLS = "1"
BB_NO_NETWORK = "1"
```

For reproducible-at-time-X builds: archive downloads + sstate-cache + pinned layer revisions.

## 123A.11  bbappend recipes for production

Common pattern: a vendor recipe almost-does-what-you-want; you bbappend to tweak.

```python
# recipes-connectivity/openssh/openssh_%.bbappend
FILESEXTRAPATHS:prepend := "${THISDIR}/${PN}:"

# Disable root login, enable our hardened sshd_config
SRC_URI += "file://sshd_config"

do_install:append() {
    install -m 0600 ${WORKDIR}/sshd_config ${D}${sysconfdir}/ssh/sshd_config
}
```

Place `sshd_config` in `recipes-connectivity/openssh/openssh/sshd_config`. Yocto finds it via `FILESEXTRAPATHS`.

## 123A.12  Lab

1. **Create a layer.** `bitbake-layers create-layer ../meta-mybsp`. Add it to `bblayers.conf`. Verify it's in the build.
2. **Add a machine.** Write `imx6ull-myboard.conf`. Set MACHINE in `local.conf`. `bitbake -e core-image-minimal | grep ^MACHINE` to verify it took.
3. **Add a custom kernel patch.** Write `linux-imx_%.bbappend` with a config fragment. Rebuild kernel; verify your config is enabled.
4. **Custom recipe.** Write a `.bb` for a hello-world C program. `bitbake myapp`. Verify it builds.
5. **Image recipe.** Write `myapp-image.bb`. `bitbake myapp-image`. Verify rootfs contains your binary.
6. **wic image.** Write a .wks. Build a .wic image. `dd` it to an SD; boot.
7. **Variant via bbappend.** Add `meta-mybsp-mini` with priority 12; bbappend the kernel to disable a peripheral the MINI doesn't have. Verify per-machine differentiation.
8. **Distro layer.** Create `meta-mybsp-distro`; set OpenSSL pinned to 3.x; verify all your packages use it.
9. **SRC_URI mirror.** Run `bitbake --runall=fetch`; archive downloads; rebuild on an offline VM.
10. **Reproducibility.** Build the same image twice; `diff` the `.wic` files — should be byte-identical with `BB_HASHSERVE` set up.

## 123A.13  Pitfalls

- **Recipe in wrong layer.** Recipe for an upstream package living in your BSP layer = drifts from upstream. Use bbappend instead.
- **Hardcoded paths.** `/home/dev/yocto/...` in a recipe = breaks on every other dev's machine. Always use `${WORKDIR}` and similar variables.
- **bbappend without `FILESEXTRAPATHS:prepend`.** BitBake can't find your patches. Add the prepend.
- **Layer priority too high.** Overrides everything; surprising consequences. Use minimum priority needed.
- **`SRCREV = "${AUTOREV}"`.** Builds use latest HEAD; non-reproducible. Pin to specific commit hashes.
- **Caching across layer changes.** sstate-cache may keep using old object. `bitbake -c cleansstate <recipe>` after edits.
- **`do_install` install with wrong owner.** Resulting rootfs has files owned by build user, breaking installers. Use `install -m 0755 ...` not `cp`.
- **DEPENDS vs RDEPENDS confusion.** DEPENDS at build time; RDEPENDS at run time. Forgetting RDEPENDS means missing libs at runtime.
- **Recipe order: do_compile before do_configure.** Yocto's task order is fixed; if you `addtask` you must specify ordering.
- **machine.conf assumes a kernel feature not enabled.** `KERNEL_DEVICETREE = "x.dtb"` but the dtb isn't in your kernel's Makefile. Bitbake fails late.
- **PR (Package Revision).** Bumping `PR = "r1"` on a recipe lets package managers (OPKG, etc.) know to upgrade. Easy to forget on bugfix recipes.
- **License license license.** Every recipe needs a `LICENSE` and `LIC_FILES_CHKSUM`. Proprietary stuff: use `LICENSE = "Proprietary"` + `LICENSE_FLAGS` for legal compliance.

## 123A.14  Going deeper

- **Yocto Mega-Manual** — https://docs.yoctoproject.org/singleindex.html.
- **Yocto Reference Manual** — variables, classes, tasks.
- **`bitbake-layers`** — `create-layer`, `add-layer`, `show-layers`.
- **`devtool`** — for iterative recipe development (`devtool modify`, `devtool finish`).
- **`oe-pkgdata-util`** — query the package database.
- **`bitbake -g <image>; cat task-depends.dot`** — visualize task dependencies.
- **`pyrex`** — containerized Yocto builds.
- **Konsulko + Pengutronix Yocto consulting reports** — for production-grade patterns.
- **`meta-virtualization`** — for containers in Yocto.
- **`meta-security`** — for hardened distro layers.
- **Ch 123** — the comparison chapter that led you here.
- **Ch 125** — RAUC / OTA for Yocto-built images.

---

> Next chapter: **Chapter 124 — Secure boot (HAB) and OP-TEE**.
