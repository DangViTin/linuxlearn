---
chapter: 30B
title: Product kernel configs
part: IV - The Kernel
estimated_pages: 16
status: draft
---

# Chapter 30B: Product kernel configs

Chapter 30 explained how kernel configuration works. Chapter 30A explained how to choose and maintain a kernel version.

This chapter is about using configuration in a product. A product rarely has only one kernel config. You usually need at least:

- a development config,
- a production config,
- a recovery config.

They should be related, but not identical.

## 30B.1  Why one config is not enough

During bring-up, you want many debug features:

- verbose logs,
- debug filesystems,
- extra drivers,
- symbols,
- tracing.

In production, you usually want less:

- smaller image,
- shorter boot time,
- fewer attack paths,
- fewer accidental interfaces.

In recovery, you want a kernel that can boot when the normal system is broken:

- storage driver built in,
- console built in,
- initramfs support,
- enough networking or USB for update,
- fewer optional product features.

Trying to use one `.config` for all three jobs makes the file confusing.

## 30B.2  Use fragments

Do not hand-edit one huge `.config` forever.

Keep small config fragments in your board repository:

```text
kernel-configs/
  base.config
  dev.config
  prod.config
  recovery.config
```

Example `base.config`:

```text
CONFIG_ARCH_MXC=y
CONFIG_SOC_IMX6ULL=y
CONFIG_SERIAL_IMX=y
CONFIG_SERIAL_IMX_CONSOLE=y
CONFIG_MMC=y
CONFIG_MMC_SDHCI=y
CONFIG_MMC_SDHCI_ESDHC_IMX=y
CONFIG_EXT4_FS=y
CONFIG_DEVTMPFS=y
CONFIG_DEVTMPFS_MOUNT=y
```

Example `dev.config`:

```text
CONFIG_DEBUG_KERNEL=y
CONFIG_DYNAMIC_DEBUG=y
CONFIG_DEBUG_FS=y
CONFIG_KALLSYMS=y
CONFIG_KALLSYMS_ALL=y
CONFIG_FTRACE=y
CONFIG_FUNCTION_TRACER=y
```

Example `prod.config`:

```text
# CONFIG_DEBUG_FS is not set
# CONFIG_DYNAMIC_DEBUG is not set
CONFIG_STRICT_KERNEL_RWX=y
CONFIG_STRICT_MODULE_RWX=y
```

Example `recovery.config`:

```text
CONFIG_BLK_DEV_INITRD=y
CONFIG_INITRAMFS_SOURCE=""
CONFIG_USB_SUPPORT=y
CONFIG_USB=y
CONFIG_USB_STORAGE=y
CONFIG_VFAT_FS=y
CONFIG_FAT_FS=y
```

These are examples, not a final product policy. The important idea is that each fragment has a purpose.

## 30B.3  Build separate output directories

Use one output directory per config.

```sh
$ cd ~/imx6ull/src/linux-v6.6
$ mkdir -p build-dev build-prod build-recovery
```

Merge the development config:

```sh
$ ./scripts/kconfig/merge_config.sh \
      -O build-dev \
      arch/arm/configs/imx_v6_v7_defconfig \
      kernel-configs/base.config \
      kernel-configs/dev.config
$ make O=build-dev olddefconfig
```

Merge the production config:

```sh
$ ./scripts/kconfig/merge_config.sh \
      -O build-prod \
      arch/arm/configs/imx_v6_v7_defconfig \
      kernel-configs/base.config \
      kernel-configs/prod.config
$ make O=build-prod olddefconfig
```

Merge the recovery config:

```sh
$ ./scripts/kconfig/merge_config.sh \
      -O build-recovery \
      arch/arm/configs/imx_v6_v7_defconfig \
      kernel-configs/base.config \
      kernel-configs/recovery.config
$ make O=build-recovery olddefconfig
```

Then build each one:

```sh
$ make O=build-dev -j$(nproc) zImage dtbs modules
$ make O=build-prod -j$(nproc) zImage dtbs modules
$ make O=build-recovery -j$(nproc) zImage dtbs
```

The `O=` directory keeps generated files separate. That makes it possible to compare configs and rebuild only the one you need.

## 30B.4  Built-in or module?

For embedded boot, this decision matters.

| Driver | Built-in (`=y`) | Module (`=m`) |
|--------|-----------------|---------------|
| UART console | Usually yes | No, too late for early boot logs |
| MMC rootfs driver | Yes if rootfs is on MMC | Only if initramfs can load it |
| Ethernet | Depends on boot needs | Fine if rootfs can load modules |
| USB storage recovery | Yes for recovery kernel | Fine for normal product |
| Optional sensor | Usually no | Good module candidate |
| Filesystem for rootfs | Yes | Only if initramfs loads it first |

A simple rule:

If the kernel needs it before the real root filesystem is mounted, build it in.

## 30B.5  Compare configs

The kernel tree includes a config comparison tool:

```sh
$ ./scripts/diffconfig build-dev/.config build-prod/.config
```

Example output:

```text
-DEBUG_FS y
-DYNAMIC_DEBUG y
-FTRACE y
 STRICT_KERNEL_RWX y
 STRICT_MODULE_RWX y
```

Use this before release. It catches surprises like debug features left enabled in production.

## 30B.6  Save a small defconfig

After merging and checking a config, save the minimal form:

```sh
$ make O=build-prod savedefconfig
$ cp build-prod/defconfig kernel-configs/imx6ull_product_defconfig
```

The full `.config` is generated output. It is useful for builds, but it is noisy in code review.

Commit the small defconfig or fragments. Regenerate the full `.config` during the build.

## 30B.7  Name the kernel clearly

Set a local version so the running board tells you what it is using.

In a config fragment:

```text
CONFIG_LOCALVERSION="-imx6ull-prod"
```

Or from the command line:

```sh
$ make O=build-prod LOCALVERSION=-imx6ull-prod zImage
```

On the board:

```sh
# uname -a
Linux imx6ull 6.6.0-imx6ull-prod ...
```

This small detail saves time when several kernel builds are being tested in the same lab.

## 30B.8  Keep bootargs different from config

Kernel config decides what the kernel can do.

Bootargs decide what this boot should do.

Examples:

| Setting | Usually belongs in |
|---------|--------------------|
| Enable MMC driver | Kernel config |
| Select root device | Bootargs |
| Enable ext4 support | Kernel config |
| Pass `rootwait` | Bootargs |
| Enable initramfs support | Kernel config |
| Pass `rdinit=/init` | Bootargs |
| Enable dynamic debug support | Kernel config |
| Turn on one driver's debug messages | Bootargs or debugfs |

Do not rebuild the kernel just to change `root=/dev/mmcblk0p2`. That is a bootargs job.

## 30B.9  A small CI matrix

Even a small embedded team should build more than one kernel in automation.

Example:

| Build | Config | Must prove |
|-------|--------|------------|
| `dev` | base + dev | Boots, has debugfs and symbols |
| `prod` | base + prod | Boots normal rootfs, debug features absent |
| `recovery` | base + recovery | Boots initramfs recovery menu |
| `dtbs_check` | board DTS | Device tree still validates |

The CI does not need to run on real hardware for every commit, but hardware boot tests should happen before release.

## 30B.10  Release checklist

Before handing a kernel to manufacturing or customers:

- `uname -a` shows the expected version string.
- The DTB in the boot partition matches the kernel release.
- `scripts/diffconfig` was checked against the previous release.
- Debug-only features are intentionally enabled or disabled.
- Rootfs storage, console, and filesystem drivers are built in when needed.
- Recovery boot was tested, not only normal boot.
- The exact kernel source tag and config fragments are recorded.

This is the practical end of Part IV. You can now build a kernel, boot it from U-Boot, describe hardware with device tree, recover from failed boots, and manage kernel configs like product assets.

---

Previous chapter: [Chapter 30A - Kernel lifecycle](ch30A-kernel-lifecycle.md)

Next part: [Part V - Root filesystem and user space](../part5-rootfs/ch31-rootfs-by-hand.md)
