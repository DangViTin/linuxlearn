---
chapter: 35
title: Buildroot, after you can do it by hand
part: V — Root filesystem & user space
estimated_pages: 20
status: draft
---

# Chapter 35 — Buildroot, after you can do it by hand

> **What:** Buildroot — a make-driven build system that produces a complete root filesystem (optionally + bootloader + kernel + cross-toolchain) from one `make` command and one `.config` file. By the end you will have built a working rootfs that boots on the i.MX6ULL, then customised it with extra packages, and learned where to look when the build fails.
> **Why:** Chapter 31 took us 22 pages and a dozen hand-typed commands to get a BusyBox shell. Buildroot does the same in 20 minutes of compile time and one menuconfig session, and on top of that adds 3000+ optional packages (Qt, alsa-utils, openssh, mosquitto, nodejs, ...). We did Ch 31 first so you know what Buildroot is doing under the hood; now we let the tool save time.
> **Focus:** **the `output/` tree** — every artefact Buildroot produces lives in one place under `output/`, with a predictable layout. Once you can navigate `output/`, debugging build failures becomes a directed search rather than a hunt.

## 35.1  What Buildroot is

Buildroot is a **make-driven** build system written almost entirely in GNU Make + shell. Architecturally:

- One Kconfig tree describes ~3000 packages plus the BusyBox / kernel / toolchain configuration.
- Each package has a small `package.mk` that says "download from URL X, extract, configure, build, install."
- A top-level `Makefile` orchestrates: select packages → fetch tarballs → build toolchain → build each package → assemble rootfs.
- Output is a `rootfs.tar` (or `.ext4` / `.cpio.gz` / `.ubifs` — your choice).

Three things Buildroot is *good* at:

1. **Tiny minimal images.** A no-extras BusyBox rootfs from Buildroot is ~3 MB. Same Yocto build is ~30 MB.
2. **Reproducible builds.** Same `.config` + same source versions → bit-identical output (usually).
3. **Fast development cycle.** Type one command, get a `rootfs.tar` in 10–30 minutes.

Three things Buildroot is *not* good at:

1. **Per-package customisation.** Patching a package is doable but awkward.
2. **Concurrent multi-config builds.** Each `make` is one config; switching configs means rebuilding.
3. **Long-term maintenance of many products.** Yocto / OpenEmbedded scales to many product variants better.

For *learning* and for *single-purpose products with simple package needs*, Buildroot is the right tool. For *commercial product lines with many variants*, Yocto is. Most engineers learn Buildroot first.

## 35.2  Get the source

```sh
$ cd ~/imx6ull/src
$ wget https://buildroot.org/downloads/buildroot-2024.02.tar.gz
$ tar xzf buildroot-2024.02.tar.gz
$ cd buildroot-2024.02
```

LTS releases are tagged `<year>.02` and `<year>.08`. Use the latest LTS for a real project; the latest non-LTS for personal experiments.

```sh
$ ls
arch/      configs/   docs/      Makefile      support/
board/     dl/        fs/        package/      system/
boot/      DEVELOPERS Kbuild     README        toolchain/
CHANGES    Config.in  linux/     Makefile.legacy utils/
```

Top-level layout:

| Directory | Purpose |
|-----------|---------|
| `arch/` | CPU architecture support (most users never touch this) |
| `board/` | Per-board files: defconfigs and post-build scripts |
| `boot/` | Bootloader recipes (`uboot/`, `barebox/`, `grub2/`) |
| `configs/` | Pre-canned configurations (`*_defconfig`) |
| `dl/` | Downloaded source tarballs (cached across builds) |
| `docs/` | Manual — read `docs/manual/manual.html` after this chapter |
| `fs/` | Filesystem-image builders (ext4, cpio, squashfs, ubi, ...) |
| `linux/` | Kernel recipe |
| `package/` | One subdirectory per package — ~3000 entries |
| `support/` | Support scripts (kconfig wrapper, checksum tools) |
| `system/` | System-skeleton files (default `/etc/inittab`, etc.) |
| `toolchain/` | Cross-toolchain recipes |

The first time you build, `dl/` is empty and Buildroot downloads every source tarball. Subsequent builds reuse the cache. Net `dl/` size for a typical build: 200 MB to 1 GB depending on packages.

## 35.3  First build — the i.MX6UL EVK defconfig

Buildroot ships a defconfig for the NXP i.MX6UL/ULL EVK:

```sh
$ make list-defconfigs | grep -i imx6
freescale_imx6sololiteevk_defconfig - ...
freescale_imx6sxsabresd_defconfig   - ...
freescale_imx6ulevk_defconfig       - NXP i.MX 6UL EVK
freescale_imx6ullevk_defconfig      - NXP i.MX 6ULL EVK   ← this one
```

Configure and build:

```sh
$ make freescale_imx6ullevk_defconfig
$ make -j$(nproc) 2>&1 | tee build.log
```

What happens, in order:

1. `make` parses Kconfig + `.config`, builds a list of selected packages.
2. Downloads every required tarball to `dl/`.
3. Builds the cross-toolchain (the first build only; about 8 minutes).
4. Extracts and builds each package, in dependency order.
5. Assembles the rootfs in `output/target/`.
6. Packages it into `output/images/rootfs.<format>`.

First build on a 4-core machine: 30-60 minutes. Subsequent rebuilds: seconds (only changed packages rebuild).

When done:

```sh
$ ls output/images/
imx6ull-14x14-evk.dtb   rootfs.cpio   rootfs.cpio.gz   rootfs.ext2
rootfs.ext4 → rootfs.ext2                rootfs.tar    SPL    u-boot-dtb.imx   zImage
```

The whole stack — SPL, U-Boot, kernel, DTB, rootfs in multiple formats — produced by one `make`. The defconfig also enabled `BR2_TARGET_UBOOT` and `BR2_LINUX_KERNEL`, which we'll often turn off if we want to build only the rootfs.

## 35.4  The output/ tree

The single most useful thing to learn about Buildroot is its output layout:

```
output/
├── build/                          # extracted, configured, built packages
│   ├── busybox-1.36.1/
│   │   ├── .stamp_downloaded
│   │   ├── .stamp_extracted
│   │   ├── .stamp_configured
│   │   ├── .stamp_built
│   │   ├── .stamp_target_installed
│   │   └── ...source files extracted here, build artefacts mixed in...
│   ├── host-gcc-arm-...
│   ├── linux-headers-...
│   └── ...one dir per package...
├── host/                           # host-side tools that Buildroot built
│   ├── bin/                        # qemu, mkimage, mkfs.ext4, ...
│   ├── arm-buildroot-linux-...-/   # the cross-toolchain
│   └── ...
├── images/                         # the FINAL ARTEFACTS
│   ├── rootfs.tar
│   ├── rootfs.ext4
│   ├── zImage
│   ├── imx6ull-14x14-evk.dtb
│   └── SPL, u-boot-dtb.imx
├── staging → ./host/arm-buildroot-linux-.../sysroot  # symlink for convenience
└── target/                         # the rootfs staging area (pre-packaging)
    ├── bin/
    ├── sbin/
    ├── etc/
    ├── lib/
    └── ...
```

Three subdirectories you'll visit:

- **`output/target/`** — the rootfs being assembled. You can `chroot` into it for inspection. **Don't edit it directly** — your changes are wiped on next build. Use the post-build script mechanism (§35.7) for persistent customisations.
- **`output/host/`** — host-side binaries. The `mkimage` Buildroot built for you lives at `output/host/bin/mkimage`. Useful when you want a known-version tool without polluting the host.
- **`output/build/<package>/`** — where each package was unpacked and built. When a build fails inside a package, this is where you go.

The `.stamp_*` files are Buildroot's idea of "what stage of the build is this package in?" If you delete `.stamp_built` and re-run `make <package>`, only that package rebuilds.

## 35.5  Reading the defconfig

```sh
$ head -40 .config
#
# Automatically generated file; DO NOT EDIT.
# Buildroot 2024.02 Configuration
#
BR2_HAVE_DOT_CONFIG=y
BR2_HOST_GCC_AT_LEAST_4_9=y
...
BR2_ARCH_HAS_TOOLCHAIN_BUILDROOT=y
BR2_arm=y
BR2_ARM_CPU_HAS_VFPV4=y
BR2_arm_cortex_a7=y
BR2_ARM_FPU_NEON_VFPV4=y
BR2_ARM_EABIHF=y
...
BR2_TOOLCHAIN_BUILDROOT_GLIBC=y      # use Buildroot-built glibc
BR2_TOOLCHAIN_BUILDROOT_CXX=y         # with C++
...
BR2_PACKAGE_BUSYBOX=y
BR2_PACKAGE_BUSYBOX_SHOW_OTHERS=y
...
BR2_LINUX_KERNEL=y
BR2_LINUX_KERNEL_CUSTOM_VERSION=y
BR2_LINUX_KERNEL_CUSTOM_VERSION_VALUE="6.6"
BR2_LINUX_KERNEL_DEFCONFIG="imx_v7"
BR2_LINUX_KERNEL_DTS_SUPPORT=y
BR2_LINUX_KERNEL_INTREE_DTS_NAME="nxp/imx/imx6ull-14x14-evk"
...
BR2_TARGET_UBOOT=y
BR2_TARGET_UBOOT_BOARDNAME="mx6ull_14x14_evk"
BR2_TARGET_UBOOT_CUSTOM_VERSION=y
BR2_TARGET_UBOOT_CUSTOM_VERSION_VALUE="2023.10"
BR2_TARGET_UBOOT_FORMAT_IMX=y
```

The file is dense but readable. Section by section:

- **`BR2_arm` + `BR2_arm_cortex_a7`** — target CPU.
- **`BR2_TOOLCHAIN_BUILDROOT_*`** — Buildroot builds its own glibc-based toolchain.
- **`BR2_PACKAGE_BUSYBOX`** — include BusyBox in the rootfs.
- **`BR2_LINUX_KERNEL`** — build the kernel as part of this Buildroot run, using mainline 6.6 with `imx_v7` defconfig and the `imx6ull-14x14-evk` DTS.
- **`BR2_TARGET_UBOOT`** — build U-Boot 2023.10 as part of this run.

To suppress kernel + U-Boot builds (you're building those separately):

```sh
$ make menuconfig
# Linux  →  [ ] Linux Kernel        ← uncheck
# Bootloaders  →  [ ] U-Boot         ← uncheck
$ make
```

Or programmatically:

```sh
$ ./utils/config --disable LINUX_KERNEL
$ ./utils/config --disable TARGET_UBOOT
$ make olddefconfig
$ make
```

## 35.6  Adding a package

Buildroot ships ~3000 packages. To pick one (e.g., `nano` editor):

```sh
$ make menuconfig
# Target packages  →  Text editors and viewers  →  [*] nano
$ make
```

Or:

```sh
$ ./utils/config --enable BR2_PACKAGE_NANO
$ make olddefconfig
$ make
```

Buildroot:
1. Downloads `nano-7.2.tar.xz` to `dl/nano/`.
2. Extracts to `output/build/nano-7.2/`.
3. Runs the package's `./configure` with the cross-compiler.
4. `make` and `make install` into `output/staging/` and `output/target/`.
5. Re-rolls `rootfs.tar`.

Re-deploy and `nano` is now on the target. Total time for adding a small package: ~30 seconds.

## 35.7  Customising without forking — `BR2_ROOTFS_OVERLAY` and post-build scripts

You almost always need to add *your own* files to the rootfs (custom `/etc/inittab`, `/etc/init.d/S99myapp`, your application binary). Three mechanisms, in order of complexity:

### Overlay directory

```sh
$ mkdir -p board/myorg/overlay/etc/init.d
$ cat > board/myorg/overlay/etc/init.d/S99myapp <<'EOF'
#!/bin/sh
echo "starting my app"
/usr/bin/myapp &
EOF
$ chmod +x board/myorg/overlay/etc/init.d/S99myapp
```

In `.config`:

```
BR2_ROOTFS_OVERLAY="board/myorg/overlay"
```

Now every Buildroot build copies the overlay tree on top of `output/target/` before packaging. Your `S99myapp` ships in the rootfs.

### Post-build script

For things you need to *generate* (interpolated config files, version strings, etc.):

```sh
$ cat > board/myorg/post-build.sh <<'EOF'
#!/bin/sh
TARGET_DIR=$1
echo "build $(date) on $(hostname)" > "$TARGET_DIR/etc/build-info"
EOF
$ chmod +x board/myorg/post-build.sh
```

In `.config`:

```
BR2_ROOTFS_POST_BUILD_SCRIPT="board/myorg/post-build.sh"
```

The script receives `$TARGET_DIR` as `$1` and runs after the overlay is applied but before packaging.

### Custom package

For shipping your own software *as a Buildroot package* with a real Makefile-driven build:

```sh
$ mkdir package/myapp
$ cat > package/myapp/Config.in <<'EOF'
config BR2_PACKAGE_MYAPP
    bool "myapp"
    help
      The myapp daemon.
EOF
$ cat > package/myapp/myapp.mk <<'EOF'
MYAPP_VERSION = 1.0
MYAPP_SITE = $(TOPDIR)/../my-app-source
MYAPP_SITE_METHOD = local

define MYAPP_BUILD_CMDS
    $(MAKE) CC="$(TARGET_CC)" -C $(@D)
endef

define MYAPP_INSTALL_TARGET_CMDS
    $(INSTALL) -D -m 0755 $(@D)/myapp $(TARGET_DIR)/usr/bin/myapp
endef

$(eval $(generic-package))
EOF
```

Then in the top-level `package/Config.in`, add `source "package/myapp/Config.in"`. After `make menuconfig && make`, your `myapp` is in the rootfs.

For a single product, the overlay mechanism handles 90% of needs. For multi-product BSPs you graduate to packages.

## 35.8  Saving the defconfig

After your `menuconfig` changes:

```sh
$ make savedefconfig BR2_DEFCONFIG=configs/myproduct_defconfig
$ git add configs/myproduct_defconfig
```

That file is ~200 lines and contains only the differences from defaults. Anyone with the Buildroot tree + the defconfig can reproduce your build.

## 35.9  Comparing to the hand-built rootfs from Chapter 31

| | Chapter 31 (by hand) | Chapter 35 (Buildroot) |
|---|---|---|
| Number of commands typed | ~20 | ~3 |
| Number of files created by you | ~6 | 0 (everything templated) |
| BusyBox config | Started from busybox `defconfig` | Same; Buildroot wraps it |
| Library copying | Manual (`cp -d ... lib/`) | Automatic |
| `/etc/inittab` | You wrote it | Buildroot provided default; overlay if you want custom |
| Reproducibility | Notes in your head | `defconfig` file in git |
| First-build time | ~5 minutes once you've practised | ~30 minutes |
| Rebuild time | Edit + retest in seconds (NFS) | Edit + rerun build (~1 minute for an overlay change) |
| New package | Hunt down + build + install yourself | One menuconfig click |

The hand-built path was for *understanding*. Buildroot is for *production work*. From this chapter on, we use Buildroot.

## 35.10  Lab

1. **Build the imx6ullevk defconfig.** Boot the resulting `rootfs.tar` over NFS. Compare with your Chapter 31 rootfs — what's there that you didn't have? (Hint: `getty`, `udev` instead of `mdev`, `dropbear` ssh, more BusyBox applets enabled.)
2. **Disable the in-Buildroot kernel and U-Boot builds.** Use your own from earlier chapters.
3. **Add three packages.** `htop`, `tmux`, `mosquitto`. Verify each works.
4. **Write an overlay.** Drop a `motd` file at `/etc/motd` so logging in prints a greeting. Drop an `S99hello` script that echoes "hello" at boot.
5. **Save a defconfig.** Commit your customised defconfig to a git repo. Have someone else clone it, run `make myproduct_defconfig && make`, and verify they get a working rootfs.
6. **Read `output/build/busybox-*/`.** That's the extracted busybox source. Compare against a fresh tarball; identify any patches Buildroot applied (look in `package/busybox/`).
7. **Use the Buildroot manual.** `docs/manual/manual.html` — load it in a browser. The section on writing custom packages is the canonical reference; bookmark it.

Commit your defconfig + overlay to `code/ch35-buildroot/`.

## 35.11  Pitfalls

- **`make clean` is not enough.** Buildroot has many levels of "clean":
  - `make clean` — remove `output/`; tarballs in `dl/` remain.
  - `make distclean` — remove `output/` and `.config`.
  - `make <pkg>-dirclean` — clean *one* package.
  - `make <pkg>-rebuild` — force rebuild without dirty clean.
- **Network access required for first build.** Buildroot downloads from upstream. Behind a corporate firewall, you may need `BR2_PRIMARY_SITE=` to point to a mirror. The `dl/` directory caches between builds.
- **Building as root.** Buildroot refuses to build as root (good safety check). Use a regular user.
- **Modifying files under `output/target/` directly.** They will be overwritten the next time `make` runs. Use overlay or post-build scripts.
- **Linux kernel built by Buildroot may not match yours.** If you enabled `BR2_LINUX_KERNEL` and pointed it at a custom branch, but also reused your own kernel binary outside Buildroot, your `modules_install` may collide. Disable Buildroot's kernel build OR commit to using only Buildroot's.
- **`/etc/inittab` from Buildroot's skeleton is different from §31.5.** Buildroot uses `system/skeleton/etc/inittab`. If your overlay's inittab doesn't completely replace it, Buildroot may keep parts of its own.
- **Package version pinning.** Buildroot pins each package to a specific version (in the `.mk` file). To upgrade, you edit the `.mk` to bump the version and possibly update the checksum file. Don't try to upgrade the package from inside `output/build/`; the next clean rebuild wipes it.

## 35.12  Going deeper

- **`docs/manual/manual.html`** in the Buildroot tree — the canonical reference.
- **`docs/manual/adding-packages-*.txt`** for the package-creation tutorial.
- **`http://buildroot.org/#community`** — mailing list (`buildroot@buildroot.org`) and IRC (`#buildroot` on Libera Chat) for help.
- **`Bootlin's Buildroot training`** — free online materials, very thorough.
- **`Yocto vs Buildroot: A Comparison`** articles on LWN — when you outgrow Buildroot's limitations, this is the case for switching to Yocto.

> Next chapter: **Chapter 35A — Ubuntu-base rootfs as a peer to BusyBox/Buildroot.** A radically different approach: take a pre-built Ubuntu and run it.
