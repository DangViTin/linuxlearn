---
chapter: 25
title: Building mainline Linux for i.MX6ULL
part: IV — The Kernel
estimated_pages: 16
status: draft
---

# Chapter 25 — Building mainline Linux for i.MX6ULL

> **What:** clone the mainline Linux source, build a `zImage` + device tree blobs + modules for the i.MX6ULL, and inspect the artefacts. Stop just short of booting; that is Chapter 26.
> **Why:** every later chapter assumes a built kernel tree on disk. The build itself is mechanical, but the artefacts it produces — and the source-tree structure you will navigate for the next several Parts — are the first thing that needs to be at your fingertips.
> **Focus:** the four build artefacts you actually use (`vmlinux`, `zImage`, `*.dtb`, `*.ko`) and the four directories you will visit most (`arch/arm/`, `drivers/`, `include/`, `Documentation/`).

## 25.1  Why mainline

The Linux kernel ships under several release tracks:

- **Mainline** at `git.kernel.org/torvalds/linux.git` — Linus's tree. The current development tip; new releases roughly every 9 weeks (the "x.y" releases like 6.6, 6.7).
- **Stable** — Greg KH applies bugfix backports to each mainline release for ~6 weeks after it. Tagged `6.6.1`, `6.6.2`, etc.
- **Long-Term Support (LTS)** — selected mainline releases get fix backports for 2 or 6 years. As of 2026 the active LTS lines are `6.6`, `6.1`, `5.15`, `5.10`, `5.4`.
- **Vendor BSPs** — NXP, ST, TI, and other silicon vendors ship forks pinned to a specific kernel minor with thousands of patches on top. The NXP fork for i.MX6ULL is `linux-imx`, currently pinned around `5.15` and `6.6` depending on the branch.

We build from **mainline** (or LTS where stability matters). The i.MX6ULL has had full support in mainline since v4.10 (released 2017); every silicon revision and DT change is upstreamed. Chapter 30A goes deeper on when each track is appropriate.

## 25.2  Clone the source

```sh
$ cd ~/imx6ull/src
$ git clone --depth=20 https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git
$ cd linux
$ git log --oneline -1
```

`--depth=20` pulls just the recent history (about 30 MB) instead of the full ~5 GB tree. Drop it if you want to bisect.

Tag-based checkout for reproducibility:

```sh
$ git fetch --tags --depth=1
$ git checkout v6.6     # latest LTS as of this writing
```

The chapter examples assume v6.6 unless otherwise noted. Newer minors (6.7, 6.8, …) work identically for our purposes.

### Directory layout (the parts you'll touch)

```
linux/
├── arch/                # CPU architecture support
│   └── arm/             # 32-bit ARM, includes i.MX6ULL
│       ├── boot/        # boot wrapper + device tree compiler
│       │   ├── dts/     # device tree source files (*.dts, *.dtsi)
│       │   └── compressed/
│       ├── configs/     # *_defconfig files
│       ├── include/asm/ # ARM-specific kernel headers
│       ├── kernel/      # ARM-specific kernel entry (start.S, head.S)
│       ├── mach-imx/    # i.MX SoC family code
│       └── mm/          # ARM memory management
├── block/               # block device layer
├── crypto/              # cryptography subsystem
├── Documentation/       # Sphinx-rendered kernel docs
├── drivers/             # all device drivers, grouped by subsystem
│   ├── clk/imx/         # i.MX clock drivers
│   ├── gpio/            # GPIO drivers
│   ├── i2c/             # I²C bus + slave drivers
│   ├── input/           # input subsystem
│   ├── irqchip/         # interrupt controllers (incl. GIC)
│   ├── mmc/             # MMC / SD card
│   ├── net/             # network drivers
│   ├── pinctrl/         # pin control (incl. freescale/)
│   ├── rtc/             # real-time clocks
│   ├── spi/             # SPI bus
│   ├── tty/serial/      # UART drivers (incl. imx.c)
│   └── usb/             # USB host + gadget
├── fs/                  # file systems (ext4, fat, tmpfs, ...)
├── include/             # kernel-wide headers
│   ├── linux/           # the main public kernel API
│   ├── uapi/            # user-space ABI headers
│   └── dt-bindings/     # DT binding constants (clocks, gpios, IRQs)
├── init/                # kernel init: start_kernel, kernel_init
├── ipc/                 # System V IPC
├── kernel/              # core kernel: scheduler, signals, sysctl, locking
├── lib/                 # generic kernel utility code
├── mm/                  # memory management (page allocator, slab, ...)
├── net/                 # network stack
├── samples/             # example code
├── scripts/             # build scripts (Kconfig, kbuild, dtc)
├── security/            # LSMs (selinux, apparmor, ...)
├── sound/               # ALSA (SoC audio in sound/soc/)
├── tools/               # user-space companion tools
└── usr/                 # initramfs cpio packager
```

The hierarchy is consistent: **subsystem at top → vendor at the second level → SoC/board at the third**. The i.MX6ULL UART driver lives at `drivers/tty/serial/imx.c`; its DT binding is at `Documentation/devicetree/bindings/serial/fsl-imx-uart.yaml`; its register definitions are inside the driver file. This pattern repeats for every subsystem.

The four directories you will spend the most time in over the rest of this book:

- `arch/arm/boot/dts/` — every chapter from 27 onward
- `drivers/<subsystem>/` — every driver chapter in Part VI
- `Documentation/devicetree/bindings/` — DT binding schemas (Ch 27A)
- `include/dt-bindings/` — constants shared between DT source and driver source

## 25.3  Defconfig and the kernel's config system

Like U-Boot, the kernel uses Kconfig + a `.config` file. The `arch/arm/configs/` directory holds default starting points:

```sh
$ ls arch/arm/configs/ | grep imx
imx_v6_v7_defconfig
mxs_defconfig
```

`imx_v6_v7_defconfig` (formerly `imx_v7_defconfig`) is the omnibus i.MX configuration that covers every i.MX SoC the v6/v7 ARM cores support — i.MX5, i.MX6 (all variants including ULL), i.MX7. One config builds for all of them; a single `zImage` boots on any. This is mainline's preferred organisation.

```sh
$ export ARCH=arm
$ export CROSS_COMPILE=arm-linux-gnueabihf-
$ make imx_v6_v7_defconfig
#
# configuration written to .config
#
```

Inspect `.config`:

```sh
$ grep -E '^CONFIG_(ARCH|SOC|MACH|ARM|EABI|VFP)' .config | head -20
CONFIG_ARCH_MULTIPLATFORM=y
CONFIG_ARCH_MXC=y
CONFIG_SOC_IMX6=y
CONFIG_SOC_IMX6UL=y          # ← i.MX6UL family (includes 6ULL)
CONFIG_SOC_IMX6Q=y
...
```

Every Y in `.config` is either compiled in (`=y`) or compiled as a loadable module (`=m`). The set of options is enormous (~7000 for a v6.6 kernel); for now we trust `imx_v6_v7_defconfig`'s defaults. Chapter 30 returns to specific knobs.

## 25.4  Build

Single-shot build of everything we need:

```sh
$ make -j$(nproc) zImage modules dtbs
```

Three independent targets:

- **`zImage`** — the compressed kernel image. ~6 MB. This is what U-Boot will `bootz`.
- **`modules`** — every `=m` driver, compiled to `.ko` files. ~hundreds in a default config. Installed separately.
- **`dtbs`** — every device tree blob the architecture defines. Includes `imx6ull-14x14-evk.dtb` for the NXP EVK and ~20 other i.MX6ULL variants.

First build takes 5–10 minutes on a modern host depending on `-j` parallelism. Subsequent incremental builds are seconds.

### What just got produced

```sh
$ ls -lh arch/arm/boot/zImage
-rw-r--r-- 1 you you 6.0M Jan 22 14:42 zImage

$ ls arch/arm/boot/dts/imx6ull*.dtb
imx6ull-14x14-evk.dtb
imx6ull-9x9-evk.dtb
imx6ull-colibri-eval-v3.dtb
imx6ull-colibri-iris.dtb
imx6ull-colibri-wifi-iris.dtb
...

$ find . -name '*.ko' | wc -l
432

$ ls -lh vmlinux
-rwxr-xr-x 1 you you 145M Jan 22 14:42 vmlinux
```

Four artefacts, four roles:

| File | Type | Used for |
|------|------|----------|
| `vmlinux` | ELF with full debug info | gdb / `addr2line` / oops decoding |
| `arch/arm/boot/Image` | Raw kernel binary, uncompressed | rarely used on ARM32 (used on AArch64) |
| `arch/arm/boot/zImage` | Compressed kernel + decompressor stub | **what U-Boot loads** |
| `arch/arm/boot/dts/*.dtb` | Compiled device tree blobs | one per board variant |
| `**/*.ko` | Loadable kernel modules | each `=m` driver |

You do *not* ship `vmlinux` to the target — it is 20× the size of `zImage`. You *do* keep `vmlinux` around on the host because it has symbols `zImage` lacks (Chapter 57 uses it to decode panics).

### Module installation to the rootfs

The `.ko` files are scattered across the build tree; before they are useful on the target, they need to be collected into a `/lib/modules/<version>/` hierarchy:

```sh
$ make INSTALL_MOD_PATH=~/imx6ull/rootfs modules_install
$ ls ~/imx6ull/rootfs/lib/modules/
6.6.0/
$ ls ~/imx6ull/rootfs/lib/modules/6.6.0/kernel/drivers/ | head
acpi
ata
auxdisplay
base
block
bluetooth
...
```

`INSTALL_MOD_PATH=~/imx6ull/rootfs` is the path that becomes `/` on the target — usually your NFS-exported rootfs directory (Chapter 24). The `make` rule also generates `modules.dep`, `modules.alias`, and a few other index files so `modprobe` works on the target.

## 25.5  zImage vs vmlinux vs Image — what compresses what

A short sketch of the wrapping:

```
              vmlinux (ELF with symbols, 145 MB)
                       │
                strip + objcopy
                       ▼
        arch/arm/boot/Image (raw binary, ~16 MB)
                       │
              gzip compression
                       ▼
              compressed/piggy.gzip (~6 MB)
                       │
   prepend decompressor stub (compressed/head.S + misc.c)
                       ▼
        arch/arm/boot/zImage (~6 MB)
```

When U-Boot `bootz`'s a `zImage`:

1. U-Boot loads the `zImage` into DRAM at the address told (typically `0x82000000`).
2. U-Boot transfers control to the first instruction of `zImage`, which is the **decompressor stub** in `arch/arm/boot/compressed/head.S`.
3. The stub copies itself out of the way, sets up a small workspace, and decompresses the gzipped kernel into the final run-from address.
4. The stub jumps to the decompressed kernel's entry point `stext` (Chapter 28). You see the famous *"Uncompressing Linux... done, booting the kernel."* message.
5. The decompressor stub is now discarded; the kernel runs from where the stub decompressed it to.

This is why the kernel works regardless of whether you store it compressed or not — the kernel image carries its own decompressor.

## 25.6  Sanity check the build

```sh
$ file arch/arm/boot/zImage
arch/arm/boot/zImage: Linux kernel ARM boot executable zImage (little-endian)

$ file vmlinux
vmlinux: ELF 32-bit LSB executable, ARM, EABI5 version 1 (SYSV),
         statically linked, BuildID[sha1]=..., with debug_info, not stripped

$ arm-linux-gnueabihf-readelf -h vmlinux | head
ELF Header:
  ...
  Entry point address:               0x80008000
  ...

$ ls arch/arm/boot/dts/imx6ull-14x14-evk.dtb
arch/arm/boot/dts/imx6ull-14x14-evk.dtb

$ dtc -I dtb -O dts arch/arm/boot/dts/imx6ull-14x14-evk.dtb | head -30
/dts-v1/;
/ {
    #address-cells = <0x01>;
    #size-cells = <0x01>;
    interrupt-parent = <0x01>;
    compatible = "fsl,imx6ull-14x14-evk", "fsl,imx6ull";
    model = "Freescale i.MX6 ULL 14x14 EVK Board";
    ...
};
```

The `dtc` reverse-compile is a useful sanity check that the DT compiled correctly. We will walk this DT in detail in Chapter 27.

## 25.7  Make this fit your workspace

A practical workspace recipe:

```sh
$ mkdir -p ~/imx6ull/{src,build,rootfs}
$ cd ~/imx6ull/src
$ git clone --depth=20 https://git.kernel.org/.../linux.git
$ cd linux

# Build out-of-tree to keep the source clean (optional but recommended)
$ make O=~/imx6ull/build/kernel imx_v6_v7_defconfig
$ make O=~/imx6ull/build/kernel -j$(nproc) zImage modules dtbs

# Symlink artefacts into TFTP and rootfs
$ ln -sf ~/imx6ull/build/kernel/arch/arm/boot/zImage /srv/tftp/zImage
$ ln -sf ~/imx6ull/build/kernel/arch/arm/boot/dts/imx6ull-14x14-evk.dtb /srv/tftp/imx6ull.dtb

# Install modules into NFS-exported rootfs
$ make O=~/imx6ull/build/kernel INSTALL_MOD_PATH=~/imx6ull/rootfs modules_install
```

`O=...` puts every generated file in a sibling directory. The source tree stays bit-identical to what `git` checked out. Cleanups are `rm -rf ~/imx6ull/build/kernel`.

## 25.8  Lab

1. **Clone, defconfig, build.** Time the build. On a 4-core / 8-thread modern host, expect 5–8 minutes for a fresh full build, < 30 s for an incremental change.
2. **Inspect the boot logo string.** Run `grep -n linux_banner init/version-timestamp.c` (or `init/version.c`) to find the banner format. Edit it to add `(yourname)`, rebuild *just* `zImage` (`make -j$(nproc) zImage`), and verify the boot message changes when you run it in Chapter 26.
3. **Build for the EVK and the Colibri.** Both `.dtb`s come out of one build. Verify by re-running `ls arch/arm/boot/dts/imx6ull-*.dtb` after `make dtbs` and comparing against the list of `imx6ull-*` `.dts` source files in the same directory.
4. **Quantify the compression.** Compare sizes: `ls -l arch/arm/boot/{Image,zImage}` and `vmlinux`. The ratios tell you something about kernel content (lots of string tables, dictionaries, …).
5. **Make distclean and reconfigure.** `make distclean` wipes `.config` and everything else. Re-run `make imx_v6_v7_defconfig && make -j$(nproc) zImage` and observe that the second build is essentially as fast as the first incremental build — `ccache` is the reason if you have it installed; otherwise the same speed.

## 25.9  Pitfalls

- **Forgetting `ARCH=arm CROSS_COMPILE=arm-linux-gnueabihf-`.** The `make` will try to build a host x86-64 kernel and fail with cryptic errors deep in the architecture-specific code. Always export both before invoking `make`.
- **Building from the source tree without `O=`.** Works, but `git status` becomes useless because every `make` populates the source tree with `.o` files. Out-of-tree builds keep the source pristine.
- **Wrong defconfig.** `make imx_v6_v7_defconfig` not `make x86_64_defconfig`. The latter happens when you forget to export `ARCH=arm` — Linux helpfully picks the host default.
- **Old gcc-toolchain miscompile.** Mainline kernels usually require a fairly recent gcc (≥ 5.1 for v6.x; ≥ 4.9 for older). Distribution `gcc-arm-linux-gnueabihf` is fine. Custom-built ancient toolchains sometimes miscompile RCU or aaprcp.
- **`make modules_install` to a system location.** By default `make modules_install` writes to `/lib/modules/$(uname -r)/`. **Always** pass `INSTALL_MOD_PATH=...` when cross-building or you will overwrite your host's modules.
- **Mismatch between `zImage` and `modules`.** Modules built against kernel version X will refuse to load on a running kernel built from version Y (they check the version's "vermagic" string). If you rebuild the kernel, rebuild + reinstall modules.

## 25.10  Going deeper

- **`Documentation/admin-guide/README.rst`** in the kernel tree — the upstream-maintained README. Read it once.
- **`Documentation/process/`** — how the community works (`coding-style.rst`, `submitting-patches.rst`, `4.Coding.rst`).
- **`Documentation/kbuild/`** — the kernel build system. `kconfig.rst` and `makefiles.rst` are the most useful.
- **`Documentation/arch/arm/`** — ARM-specific docs, including the `.dts` → `.dtb` flow.
- **kernelnewbies.org** — the friendliest entry point for new kernel hackers.
- **The kernel mailing list archive** at `lore.kernel.org` — search `[PATCH] imx6ull` to read every recent i.MX6ULL change discussion.

> Next chapter: **Chapter 26 — Booting the kernel from U-Boot.** We hand the freshly-built `zImage` to U-Boot and watch the first dozen lines of kernel output appear on the UART.
