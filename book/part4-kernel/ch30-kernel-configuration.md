---
chapter: 30
title: Kernel configuration deep-dive
part: IV — The Kernel
estimated_pages: 18
status: draft
---

# Chapter 30 — Kernel configuration deep-dive

> **What:** the kernel's Kconfig system — `make menuconfig`, the `.config` file, defconfig snapshots — and the dozen config options that matter most for an i.MX6ULL embedded image. By the end you should be able to enable/disable any kernel feature, save a clean `defconfig`, and explain to a teammate why each option is set.
> **Why:** Through Chapter 29 we used `imx_v6_v7_defconfig` as a black box. For real products you'll customise: smaller kernels for smaller flash, PREEMPT_RT for real-time, specific debug options on engineering builds. Knowing where each knob lives lets you build a kernel that fits your product, not just one that boots.
> **Focus:** `.config` is the canonical file. `menuconfig`, `xconfig`, and the others are just UIs that edit it. Read it, edit through the UI, and rebuild.

## 30.1  The Kconfig system

The kernel has ~7000 configurable options across hundreds of `Kconfig` files scattered through the source tree. Each is a `CONFIG_FOO` symbol that ends up as `=y` (compiled in), `=m` (loadable module), or absent (compiled out) in the final `.config`.

Five `make` targets cover 95% of use:

| Target | What it does |
|--------|--------------|
| `make defconfig` | Use the default config (`arch/$ARCH/configs/defconfig`) |
| `make <name>_defconfig` | Use a named per-board/per-arch starting point (e.g., `imx_v6_v7_defconfig`) |
| `make menuconfig` | Interactive ncurses-based config editor |
| `make oldconfig` | Update an existing `.config` against new Kconfig options; prompt for each new one |
| `make savedefconfig` | Distill the current `.config` down to the minimum diff from defaults and save to `defconfig` |

Other UIs exist (`nconfig`, `xconfig`, `gconfig`) — same functionality, different UIs. `menuconfig` is the one everyone uses.

## 30.2  `make menuconfig` tour

From a configured tree:

```sh
$ make ARCH=arm CROSS_COMPILE=arm-linux-gnueabihf- menuconfig
```

You'll get a full-screen ncurses interface. Navigation:

- **Arrow keys** — move
- **Enter** — descend into a submenu
- **Space** — cycle `=y` / `=m` / disabled
- **`?`** — show help for the current option (very useful — every Kconfig symbol has descriptive help)
- **`/`** — search for an option by name (case-insensitive substring; multiple matches show their location in the menu tree)
- **`esc esc`** — go back
- **`Q`** — quit; prompts to save

A representative top-level menu:

```
  General setup  --->
  System Type  --->
  Bus support  --->
  Kernel Features  --->
  Boot options  --->
  CPU Power Management  --->
  Floating point emulation  --->
  Userspace binary formats  --->
  Power management options  --->
  [*] Networking support  --->
  Device Drivers  --->
  File systems  --->
  Security options  --->
-*- Cryptographic API  --->
  Library routines  --->
  Kernel hacking  --->
```

Each `--->` is a submenu. Each `[*]` / `<*>` / `<M>` / `< >` is a yes/module/no option. Each `(...)` is a string or integer option. The structure is consistent: subsystems group their options together.

## 30.3  The `.config` file

After saving in `menuconfig`, the entire state lives in `.config` at the kernel-tree root. It is plain text. Each line is one of: `CONFIG_FOO=y`, `CONFIG_FOO=m`, `CONFIG_FOO="string"`, `CONFIG_FOO=10`, or `# CONFIG_FOO is not set`.

```sh
$ wc -l .config
2147 .config

$ head -10 .config
#
# Automatically generated file; DO NOT EDIT.
# Linux/arm 6.6.0 Kernel Configuration
#
CONFIG_CC_VERSION_TEXT="arm-linux-gnueabihf-gcc (Ubuntu 11.4.0-1ubuntu1~22.04) 11.4.0"
CONFIG_GCC_VERSION=110400
CONFIG_CLANG_VERSION=0
CONFIG_AS_IS_GNU=y
CONFIG_AS_VERSION=24200
...
```

You **can** edit `.config` by hand, but the comment is honest: changes you make can be silently undone the next time `make` runs, because the Kconfig dependencies might reject your edit. Always go through `make olddefconfig` or `make oldconfig` after a manual edit to let the system reconcile.

## 30.4  defconfigs — capturing your customisation

A *defconfig* is the **minimum** set of options that, applied on top of the architecture's defaults, reproduces your `.config`. It's how you preserve a customisation without saving the full 2000-line `.config`.

```sh
$ make ARCH=arm savedefconfig
$ ls defconfig
defconfig
$ wc -l defconfig
324 defconfig
```

That `defconfig` file (324 lines vs 2147 for full `.config`) contains *only* the lines that differ from the architecture default. Save it as `arch/arm/configs/myboard_defconfig`, commit it to git, and anyone can reproduce your build:

```sh
$ make ARCH=arm myboard_defconfig
$ make ARCH=arm -j$(nproc) zImage
```

With those two commands, the second engineer has the same kernel. This is why upstream ships `imx_v6_v7_defconfig` instead of full `.config`s.

## 30.5  The dozen knobs that matter most

Reading every help text in `menuconfig` takes hours and is not the fastest way to learn what matters. Here are the dozen options that matter most on the path from `defconfig` to an i.MX6ULL image:

### Preemption model — `CONFIG_PREEMPT_*`

```
General setup
  Preemption Model  --->
    ( ) No Forced Preemption (Server)
    (X) Voluntary Kernel Preemption (Desktop)     ← default
    ( ) Preemptible Kernel (Low-Latency Desktop)
    ( ) Fully Preemptible Kernel (Real-Time)
```

Determines how long kernel code can hold the CPU before letting another thread run. **`PREEMPT_NONE`** maximizes throughput, **`PREEMPT_VOLUNTARY`** (the default) is a reasonable compromise, **`PREEMPT`** improves desktop responsiveness, `PREEMPT_RT` turns the kernel into a real-time kernel with bounded, low latency (Chapter 52A is dedicated to this).

For a typical embedded product, `PREEMPT_VOLUNTARY` is fine. For motion control or audio with hard latency budgets, `PREEMPT_RT`. For a router pushing packets, `PREEMPT_NONE`.

### Tick rate — `CONFIG_HZ`

```
Kernel Features
  Timer frequency  --->
    ( ) 100 Hz
    (X) 250 Hz
    ( ) 300 Hz
    ( ) 1000 Hz
```

How often the kernel scheduler tick fires. Higher = better latency, more overhead. 250 Hz is the modern default for non-server workloads. For battery-powered devices, lower; for low-latency, 1000 Hz.

### Tickless idle — `CONFIG_NO_HZ_*`

```
General setup
  Timers subsystem
    Timer tick handling  --->
      ( ) Periodic timer ticks (constant rate, no dynticks)
      (X) Idle dynticks system (tickless idle)
      ( ) Full dynticks system (tickless)
```

**`NO_HZ_IDLE`** lets the CPU sleep longer when idle by stopping the tick. Saves power. The default for v6.x.

### Devtmpfs — `CONFIG_DEVTMPFS` + `CONFIG_DEVTMPFS_MOUNT`

```
Device Drivers
  Generic Driver Options
    [*] Maintain a devtmpfs filesystem to mount at /dev
    [*]   Automount devtmpfs at /dev, after the kernel mounted the rootfs
```

Required for the modern `/dev` model: kernel populates `/dev/*` from device probes. Without it, you need `udev` or `mdev` in userspace. **Always enable both.**

### Initramfs — `CONFIG_BLK_DEV_INITRD` + `CONFIG_INITRAMFS_SOURCE`

```
General setup
  [*] Initial RAM filesystem and RAM disk (initramfs/initrd) support
  ()  Initramfs source file(s)             ← optional, embeds an initramfs
```

Required for Chapter 29. The source field embeds a cpio archive directly into `zImage`.

### Modules — `CONFIG_MODULES` and `CONFIG_MODULE_UNLOAD`

```
[*] Enable loadable module support  --->
    [*]   Module unloading
    [*]   Forced module unloading      ← off in production usually
```

Enables `=m`-style driver loading. Useful for development (load/unload a driver without reboot). Off if you want a monolithic kernel.

### `console=` defaults via DT — already covered

The kernel reads `chosen.stdout-path` from DT plus the `console=` cmdline; both are independent of `.config`.

### USB — `CONFIG_USB` + `CONFIG_USB_EHCI_HCD` + `CONFIG_USB_GADGET`

```
Device Drivers
  [*] USB support  --->
       <*>   Support for Host-side USB
       <*>   EHCI HCD (USB 2.0) support
       [*]   USB Gadget Support
```

EHCI host = USB host port on i.MX6ULL. Gadget = device-mode (Chapter 55).

### Network drivers — `CONFIG_FEC` for the i.MX FEC

```
Device Drivers
  [*] Network device support  --->
       Ethernet driver support  --->
         <*>   Freescale devices  --->
                 <*>   FEC (Freescale FEC and i.MX6UL/ULL)
```

Without `CONFIG_FEC`, your Ethernet won't work. Default `imx_v6_v7_defconfig` enables this; if you start from a stripped-down config you may have to add it back.

### MMC / SD — `CONFIG_MMC` + `CONFIG_MMC_SDHCI_ESDHC_IMX`

```
Device Drivers
  <*> MMC/SD/SDIO card support  --->
        <*>   Secure Digital Host Controller Interface support
        <*>     Freescale eSDHC/uSDHC i.MX controller
```

Required to access SD card and eMMC.

### Filesystem support — `CONFIG_EXT4_FS`, `CONFIG_F2FS_FS`, `CONFIG_VFAT_FS`

```
File systems  --->
  <*> The Extended 4 (ext4) filesystem
  <*> F2FS filesystem support
  <*> DOS/FAT/EXFAT/NT Filesystems  --->
        <*>   VFAT (Windows-95) fs support
```

Need at least one filesystem matching your `root=`. Most embedded systems use ext4 on eMMC, F2FS on eMMC for flash longevity, FAT for boot partitions.

### Kernel debug options — `CONFIG_DEBUG_KERNEL` + `CONFIG_DEBUG_INFO`

```
Kernel hacking  --->
  [*] Kernel debugging
      Compile-time checks and compiler options  --->
        Debug information --->
          (X) Generate DWARF Version 5 debuginfo
```

For development, keep these on — gdb stack traces and oops decoding need DWARF symbols. For production, off — they bloat `vmlinux` by 100+ MB (though `zImage` stays small).

## 30.6  Building a smaller kernel

Default `imx_v6_v7_defconfig` produces a ~6 MB `zImage`. For a tighter image:

```sh
$ make ARCH=arm imx_v6_v7_defconfig
$ make ARCH=arm menuconfig
```

Aggressive trimming:

- **Disable unused architectures/SoCs.** `System Type → Multiple platform selection`: turn off `ARM_AT91`, `ARM_OMAP`, `ARCH_BCM`, etc. — keep only `ARCH_MXC`. Saves ~500 KB.
- **Disable unused drivers.** `Device Drivers → Sound card support → ALSA for SoC audio support` — off if you don't have audio. Saves ~200 KB.
- **Disable unused filesystems.** Only ext4 needed? Disable F2FS, FAT, etc. Saves ~100 KB.
- **Disable IPv6 / IPv4 sub-features you don't need.** TCP / UDP / unicast routing — yes. Multicast routing / fib_rules / netfilter — no. Saves ~500 KB.
- **Disable debug info.** `Kernel hacking → Kernel debugging → off`. Cuts `vmlinux` size dramatically; `zImage` shrinks by ~1 MB. Keep your dev build separate.

A trimmed image for i.MX6ULL can reach ~3 MB. Below that requires turning off things you usually want (e.g., loadable modules → +200 KB savings, but you lose `modprobe`).

## 30.7  Useful Kconfig idioms

### Find an option by name

```
( ) Inside menuconfig, press / and type CONFIG_FOO
```

The search results include the menu path. Quote: "`Symbol: PREEMPT_RT [=n]; Defined at kernel/Kconfig.preempt:64; Location: Main menu → General setup → Preemption Model → ...`". You can jump there with Enter.

### See dependencies

```
( ) Highlight an option and press ? for help; the "Depends on:" lines list its preconditions
```

If `CONFIG_FOO` depends on `BAR && BAZ`, enabling FOO requires both BAR and BAZ. menuconfig hides FOO if its dependencies aren't met. Search to find the missing dependency.

### Strip a feature from a defconfig

```sh
$ make ARCH=arm imx_v6_v7_defconfig
$ ./scripts/config --disable AUDIT
$ make ARCH=arm olddefconfig
```

`scripts/config` is the headless command-line equivalent of menuconfig — invaluable for CI.

### Combine multiple defconfigs

```sh
$ make ARCH=arm imx_v6_v7_defconfig
$ ./scripts/config --enable PREEMPT_RT
$ make ARCH=arm olddefconfig
```

You start from a known baseline and apply targeted changes. Easier to maintain than committing a full bespoke defconfig.

## 30.8  Lab

1. **Read the help for ten random options.** Press `/` to search for something innocuous (`PREEMPT`, `DEVTMPFS`, etc.), press `?` on each, read the help. Get a feel for how Kconfig documentation reads.
2. **Trim the kernel.** Starting from `imx_v6_v7_defconfig`, disable five features you're confident you don't need on the i.MX6ULL MINI. Rebuild. Measure `zImage` size before and after.
3. **Generate a custom defconfig.** After trimming, run `make ARCH=arm savedefconfig`. Inspect `defconfig`. Save as `arch/arm/configs/myboard_defconfig`. Verify another `make distclean && make myboard_defconfig && make` reproduces the same trimmed kernel.
4. **Enable a kernel module.** Find a driver currently `=y` (e.g., `CONFIG_USB_F_MASS_STORAGE`). Change it to `=m`. Rebuild. Confirm a corresponding `.ko` appears under `drivers/usb/gadget/function/`.
5. **Read `Documentation/admin-guide/kernel-parameters.txt`** for any 10 cmdline tokens. Cross-reference with the `.config` options that produce them.

## 30.9  Pitfalls

- **Editing `.config` directly and not running `make oldconfig`.** Your edits may be silently reverted on next build because of dependency rules. Always go through Kconfig.
- **Forgetting `ARCH=arm`.** Without it, `make menuconfig` shows you the *host's* Kconfig (x86 or arm64), not the cross target's. Always export.
- **`make defconfig` overwrites `.config`.** If you've made customisations and run `make defconfig`, those changes are gone. Save with `make savedefconfig` first.
- **Different defconfigs in different parts of the tree.** `arch/arm/configs/imx_v6_v7_defconfig` is for ARM 32-bit i.MX6/i.MX7. `arch/arm64/configs/defconfig` is for everything ARM 64-bit. Don't cross them.
- **Disabling `CONFIG_MMU`.** There is a `CONFIG_MMU` symbol you can clear. Don't. The result is `nommu` Linux for parts without an MMU, which won't run on Cortex-A7 anyway.
- **Disabling `CONFIG_PREEMPT_VOLUNTARY` to "make it faster".** If you turn off `CONFIG_PREEMPT_VOLUNTARY`, the build falls back to `CONFIG_PREEMPT_NONE`, which is the server profile (higher latency, higher throughput). On an interactive system this is a regression. Read the help on each Preemption Model option before changing.

## 30.10  Going deeper

- **`Documentation/kbuild/kconfig-language.rst`** — the canonical Kconfig syntax reference.
- **`Documentation/kbuild/kconfig.rst`** — operational guide for `make menuconfig` and friends.
- **`scripts/kconfig/`** — the Kconfig parser and UI source. Worth a skim if you write your own Kconfig.
- **`Documentation/admin-guide/`** — runtime-tunable options many of which correspond to `.config` choices.

> Next chapter: **Chapter 30A — Kernel lifecycle decision framework.** Now that you can configure any kernel, the question becomes *which* kernel — mainline, stable, LTS, or vendor BSP. The single most important architectural decision in any product.
