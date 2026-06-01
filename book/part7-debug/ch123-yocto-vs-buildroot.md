---
chapter: 123
title: Yocto vs Buildroot — an honest comparison
part: VIII — Debug, production, advanced
estimated_pages: 22
status: draft
---

# Chapter 123 — Yocto vs Buildroot, an honest comparison

> **What:** picking a build system shapes your product's CI, release, and maintenance flow for years. **Buildroot** (the make-driven, "tightly-curated tree of packages" approach) vs **Yocto/OpenEmbedded** (the metadata-driven, "recipes + layers" approach). We walk through the mental model of each, build the same image with both side-by-side, compare reproducibility, build times, SDK production, multi-machine support, layer composition, and BSP integration. Then a verdict on when each wins, when each is a poor fit, and when neither is right.
> **Why:** most production embedded Linux teams use Buildroot or Yocto. Some use both. The choice affects:
> - hiring (Yocto skills are scarcer and more expensive than Buildroot),
> - CI infrastructure (Yocto builds are slower and need more storage),
> - onboarding a new engineer (Buildroot is friendlier),
> - maintaining a fleet of variants (Yocto wins),
> - debugging a build problem (Buildroot wins).
>
> Choosing badly costs months; choosing well saves them.
> **Focus:** **the mental model is different — Buildroot is "menuconfig builds a complete image"; Yocto is "metadata recipes are combined to produce many possible images." Buildroot scales by adding packages; Yocto scales by adding layers + machines + distros. For a single product with 1–3 variants, Buildroot wins. For a vendor BSP that serves dozens of customer products from one codebase, Yocto wins. Most teams overestimate their multi-variant complexity and end up with Yocto sledgehammers cracking Buildroot walnuts.**

## 123.1  Mental model side-by-side

| | Buildroot | Yocto / OpenEmbedded |
|---|---|---|
| Configuration unit | a single `defconfig` | a stack of *layers*; a *machine* + *distro* + *image* recipe |
| Build engine | GNU Make | BitBake (Python-driven, task-based) |
| Package definitions | `package/foo/foo.mk` + `Config.in` | `meta-*/recipes-*/foo/foo_1.2.3.bb` |
| Per-package config | menuconfig globals | `bbappend` files per layer |
| Parallel builds | yes (make -j) | yes (BitBake tasks across CPUs + machines) |
| Build cache | none (rebuild from scratch is the norm) | sstate-cache (artifacts keyed by input hash) |
| Time-to-first-image | 30–60 min | 1–4 hours (initial); 5–30 min (incremental) |
| Output | a single `output/images/` tree | per-image `tmp/deploy/images/<machine>/...` |
| SDK production | `make sdk` | `bitbake -c populate_sdk core-image-minimal` |
| Reproducibility | quasi (depends on host) | strong (with `BB_HASHSERVE`, ~bit-for-bit) |
| Number of packages | ~3000 | ~10,000+ |
| Documentation | clear, single PDF | sprawling, spread across many sources |
| Learning curve | gentle (few weeks) | steep (months) |

## 123.2  Buildroot in 5 minutes

```sh
git clone https://git.buildroot.net/buildroot
cd buildroot
make qemu_arm_versatile_defconfig             # or your custom defconfig
make menuconfig
# Target options → Target Architecture → ARM
# Toolchain → external Linaro toolchain
# Target packages → Hardware handling → i2c-tools (check)
# Filesystem images → ext2/3/4 root filesystem (check)
# Bootloaders → U-Boot
# Kernel → use the Linux 6.6
make -j$(nproc)
# 30 min later:
ls output/images/
# bzImage  rootfs.ext4  rootfs.tar  u-boot.bin
```

That's everything in one tree: cross-toolchain (built or downloaded), U-Boot, kernel, rootfs with the packages you picked. One command, predictable output. To save your config:

```sh
make savedefconfig            # writes to configs/myboard_defconfig
```

Commit `configs/myboard_defconfig` to git; teammates `make myboard_defconfig && make` to get identical output.

Adding a custom package:

```
# package/myapp/Config.in
config BR2_PACKAGE_MYAPP
    bool "myapp"
    help
      My internal app.

# package/myapp/myapp.mk
MYAPP_VERSION = 1.0
MYAPP_SITE = $(BR2_EXTERNAL)/src/myapp
MYAPP_SITE_METHOD = local
MYAPP_DEPENDENCIES = libcurl

define MYAPP_BUILD_CMDS
    $(MAKE) CC="$(TARGET_CC)" -C $(@D)
endef

define MYAPP_INSTALL_TARGET_CMDS
    $(INSTALL) -m 0755 $(@D)/myapp $(TARGET_DIR)/usr/bin/
endef

$(eval $(generic-package))
```

50 lines. The `generic-package` framework provides defaults for everything you don't override. Add `source "package/myapp/Config.in"` somewhere in the `Config.in` tree; rebuild; `myapp` is now in the rootfs.

## 123.3  Yocto in 30 minutes

```sh
git clone -b kirkstone https://git.yoctoproject.org/poky
cd poky
. oe-init-build-env
# Working in build/

# Pick a machine
# bblayers.conf: BBLAYERS += "/path/to/meta-imx /path/to/meta-mybsp"
# local.conf: MACHINE = "imx6ull-myboard"
#             DISTRO = "poky"

bitbake core-image-minimal
# Takes 1–4 hours first build (downloads + compiles ~1000 packages)
ls tmp/deploy/images/imx6ull-myboard/
# core-image-minimal-imx6ull-myboard.tar.bz2
# zImage  imx6ull-myboard.dtb  u-boot.imx  ...
```

The pieces:
- **`poky`** = the reference distro + tooling.
- **`meta-imx`** = NXP's BSP layer (or `meta-freescale` for older).
- **`meta-mybsp`** = your layer with board DTS + machine config.
- **`local.conf`** = build-specific knobs.

A layer's structure:

```
meta-mybsp/
├── conf/
│   ├── layer.conf
│   └── machine/imx6ull-myboard.conf
├── recipes-bsp/
│   └── u-boot/u-boot-mybsp_2026.04.bb
├── recipes-kernel/
│   └── linux/linux-mybsp_6.6.bb
├── recipes-core/
│   └── images/myapp-image.bb
└── recipes-myapp/
    └── myapp/myapp_1.0.bb
```

Each `.bb` recipe is a Python+shell file describing how to fetch, configure, build, install, and package one component.

`myapp_1.0.bb`:

```python
DESCRIPTION = "My internal app"
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://LICENSE;md5=abc..."

SRC_URI = "git://github.com/myorg/myapp.git;protocol=https;branch=main"
SRCREV = "abc123def456"
S = "${WORKDIR}/git"

DEPENDS = "curl"

do_compile() {
    oe_runmake CC="${CC}" CFLAGS="${CFLAGS}" LDFLAGS="${LDFLAGS}"
}

do_install() {
    install -d ${D}${bindir}
    install -m 0755 ${S}/myapp ${D}${bindir}/
}
```

The `${...}` are BitBake variables filled in by the layer config + base classes (`inherit autotools`, `inherit cmake`, etc., provide build-system-specific defaults).

## 123.4  When Buildroot wins

- **One product, few variants.** A single defconfig per variant; everything in one tree.
- **Build-from-source is the goal.** No interest in vendor SDKs or sharing recipes across products.
- **Small team.** 1–5 engineers can master Buildroot in a week.
- **Predictable build time matters.** Buildroot builds are fast (30 min) and deterministic.
- **Debugging build failures.** Stepping through a `make` is easier than a BitBake task graph.
- **Small rootfs.** Buildroot's curated packages are lean; the default core-image is ~30 MB. Yocto's `core-image-minimal` is closer to **~10 MB** (depending on init/packagegroups); only `core-image-base` or `core-image-full-cmdline` climbs into the 60 MB+ range.

Example: a hobbyist product, a one-off consumer gadget, a small-fleet IoT device. Buildroot for these is right.

## 123.5  When Yocto wins

- **Multi-customer BSP.** One vendor's layer (`meta-imx`) shared across 50+ downstream products.
- **Many machines, one codebase.** `MACHINE = imx6ull-foo` vs `MACHINE = imx8mq-bar` from the same layer.
- **Vendor support contracts.** NXP, TI, ST ship Yocto BSPs as their officially-supported integration.
- **Reproducibility (binary-identical builds).** sstate-cache + `BB_HASHSERVE` give the strongest reproducibility in the industry.
- **Compliance / license tracking.** Yocto generates SBOMs (Software Bills of Materials), license manifests, source archives for GPL compliance.
- **Distro-style packaging.** Build .deb or .rpm for OTA delivery.

Example: a vendor-grade industrial gateway, a fleet of medical devices, anything needing rigorous compliance + 10-year maintenance.

## 123.6  When neither is right

- **Bare-metal RTOS** — both these tools assume a full Linux userspace.
- **Single-binary container** — use Alpine + Docker; no rootfs builder needed.
- **Pre-built distribution** — `Ubuntu Core` or `Debian arm64` may give you everything in 1 day; skip the build tooling.
- **Microcontroller** — neither applies; use Zephyr or vendor SDKs.

## 123.7  Side-by-side example — same recipe in both

A package `foo` that builds with autotools:

### Buildroot

`package/foo/Config.in`:
```
config BR2_PACKAGE_FOO
    bool "foo"
    select BR2_PACKAGE_LIBBAR
```

`package/foo/foo.mk`:
```
FOO_VERSION = 1.0
FOO_SITE = https://example.com
FOO_SOURCE = foo-$(FOO_VERSION).tar.gz
FOO_DEPENDENCIES = libbar
FOO_LICENSE = MIT

$(eval $(autotools-package))
```

~10 lines. Done.

### Yocto

`meta-mybsp/recipes-myapp/foo/foo_1.0.bb`:
```python
DESCRIPTION = "foo utility"
HOMEPAGE = "https://example.com"
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://COPYING;md5=abc..."

SRC_URI = "https://example.com/foo-${PV}.tar.gz"
SRC_URI[md5sum] = "abc..."
SRC_URI[sha256sum] = "abc..."

DEPENDS = "libbar"

inherit autotools
```

~10 lines too! Yocto's class system (`inherit autotools`) handles configure/build/install identically to Buildroot's `autotools-package`. For simple recipes, similar effort.

For complex builds, Yocto's task graph (do_fetch, do_unpack, do_patch, do_configure, do_compile, do_install, do_package, ...) gives finer control but more places to get lost.

## 123.8  Reproducible builds

Buildroot is mostly reproducible: pin Buildroot version + pin defconfig + pin host toolchain → likely identical output, but not guaranteed.

Yocto with `BB_HASHSERVE` is strongly reproducible — same inputs always produce bit-for-bit identical outputs. Important for security-audited products and regulatory compliance.

Both can be made fully reproducible with care; Yocto requires less effort.

## 123.9  SDK production

For application developers (who don't want to build the whole kernel + rootfs), produce an SDK:

### Buildroot
```sh
make sdk
# output/images/sdk.tar.gz — extract, source environment-setup, cross-compile your app
```

### Yocto
```sh
bitbake -c populate_sdk core-image-minimal
# tmp/deploy/sdk/poky-glibc-x86_64-core-image-minimal-...-toolchain-....sh
# Run the installer; source environment-setup-...
```

Both produce a directory with `arm-linux-gnueabihf-gcc` and a sysroot. Yocto's SDK is slightly larger (more headers, more docs); Buildroot's is leaner.

## 123.10  CI integration

Both work in CI. Yocto needs more storage (sstate-cache can be 10+ GB) and longer initial build. Buildroot starts faster but has no cache; every clean build is 30 min.

For CI:
- **Buildroot**: `make defconfig && make` in a Docker container per build.
- **Yocto**: keep an sstate-cache mounted across builds (NFS, S3); first build is slow, subsequent are fast.

## 123.11  Lab

1. **Buildroot bring-up.** Clone Buildroot. `make qemu_arm_versatile_defconfig`. `make`. Run the resulting image in QEMU. Time the build.
2. **Buildroot custom package.** Add a "hello world" package; verify it appears in the rootfs.
3. **Buildroot defconfig for your board.** Customize for i.MX6ULL Point Atom; save defconfig; commit; teammate reproduces.
4. **Yocto bring-up.** Clone poky kirkstone branch. Source `oe-init-build-env`. Set `MACHINE = "qemuarm"`. `bitbake core-image-minimal`. Time the build (initial vs second).
5. **Yocto custom recipe.** Write a `.bb` for the same "hello world." Verify it's in the rootfs.
6. **Side-by-side comparison.** Build the same rootfs from both. Compare: size, package list, build time, disk usage during build.
7. **Yocto layer.** Create your own layer (`bitbake-layers create-layer ../meta-mine`); add a board machine config; verify it works.
8. **SDK from each.** Generate SDK; cross-compile a 50-line C program with each; compare results.
9. **Update one package.** Increment a package version in both. Buildroot: edit `foo.mk`, rebuild. Yocto: write a new `foo_1.1.bb`, rebuild.
10. **Verdict.** Write a 200-word "we should choose X" for your team's situation. Defend.

## 123.12  Pitfalls

- **Yocto initial build crushing your laptop.** Needs 50+ GB disk, 4+ GB RAM, 4+ cores; a Raspberry Pi can't do it. Use a beefy build server.
- **Buildroot reproducibility myths.** Same defconfig + different host = different output (host gcc version, host libc influences some packages). Pin everything you can.
- **Yocto layer recipes too generic.** Easy to write recipes that work on x86 but break on ARM. `bitbake -c devshell` to debug per-package builds.
- **sstate-cache poisoning.** A bad sstate entry causes cryptic failures. `bitbake -c cleansstate <recipe>` to evict.
- **Layer-priority confusion.** Two layers ship the same recipe; the higher-priority one wins. Set explicit priorities in `layer.conf`.
- **`bbappend` for wrong version.** `foo_%.bbappend` matches any version; `foo_1.2.%.bbappend` matches 1.2.x. Use the right pattern.
- **Buildroot `make clean` blasts everything.** Then full 30-min rebuild. Use `make foo-rebuild` for incremental.
- **License compliance forgotten.** GPL requires source distribution. Both tools can produce source tarballs; configure and store them.
- **DISTRO != MACHINE.** Yocto's `DISTRO` (e.g., `poky`, `oe-core`, `mistral`) and `MACHINE` (e.g., `imx6ull-myboard`) are orthogonal. Mixing them up = surprising configurations.
- **Building on macOS / Windows.** Both Buildroot and Yocto only support Linux build hosts well. Use a Linux VM or WSL2.
- **Choosing Yocto for a 1-person project.** You'll spend more time on Yocto than on your product. Use Buildroot.

## 123.13  Going deeper

- **Buildroot manual** — https://buildroot.org/downloads/manual/manual.html. Concise, covers everything.
- **Yocto Project Documentation** — https://docs.yoctoproject.org/. Sprawling but authoritative.
- **OpenEmbedded Layer Index** — https://layers.openembedded.org/. Search for existing recipes/layers.
- **`bblayers.conf` + `local.conf`** — your Yocto build's primary controls.
- **Bootlin's Buildroot training material** — free PDFs.
- **Konsulko Group's Yocto training** — paid but excellent.
- **`bitbake-cookerdaemon-log`** — for debugging build orchestration.
- **`oe-pkgdata-util` + `bitbake-getvar`** — for introspecting recipes.
- **Ch 123A** — when you've decided Yocto + need to write production-quality layers.
- **Ch 35** — original Buildroot chapter.

---

> Next chapter: **Chapter 123A — Yocto layer development in depth**.
