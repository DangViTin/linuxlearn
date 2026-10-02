---
chapter: 35E
title: Buildroot product board directory
part: V - Root filesystem and user space
estimated_pages: 18
status: draft
---

# Chapter 35E: Buildroot product board directory

Chapter 35 showed Buildroot. Chapter 35D showed the SD/eMMC image layout. Chapter 35I showed the SPI NOR layout. This chapter turns those pieces into a product-style board directory.

The goal is a tree like this:

```text
buildroot/
  configs/pa_mini_defconfig
  board/myorg/pa-mini/
    rootfs-overlay/
    post-build.sh
    post-image.sh
    genimage.cfg
    linux.fragment
    busybox.fragment
```

That is the shape you can commit, review, rebuild, and hand to another engineer.

## 35E.1  What belongs in the board directory

| File | Purpose |
|------|---------|
| `configs/pa_mini_defconfig` | The saved Buildroot configuration |
| `rootfs-overlay/` | Files copied directly into the target rootfs |
| `post-build.sh` | Final rootfs edits before image creation |
| `post-image.sh` | Create SD/eMMC image after Buildroot creates filesystems |
| `genimage.cfg` | Partition/image description |
| `linux.fragment` | Kernel config additions |
| `busybox.fragment` | BusyBox applet/config additions |

Keep product-specific files here. Do not edit `output/target/` by hand.

## 35E.2  Create the directory

```sh
$ cd ~/imx6ull/src/buildroot-2025.02.15
$ mkdir -p board/myorg/pa-mini/rootfs-overlay/etc/init.d
$ mkdir -p board/myorg/pa-mini/rootfs-overlay/data
```

Add a message of the day:

```sh
$ cat > board/myorg/pa-mini/rootfs-overlay/etc/motd <<'EOF'
Point Atom MINI i.MX6ULL
Buildroot product rootfs
EOF
```

Add a first boot script:

```sh
$ cat > board/myorg/pa-mini/rootfs-overlay/etc/init.d/S99hello <<'EOF'
#!/bin/sh
echo "hello from product overlay"
EOF
$ chmod +x board/myorg/pa-mini/rootfs-overlay/etc/init.d/S99hello
```

## 35E.3  Add a post-build script

`post-build.sh` runs after Buildroot has assembled `output/target/`, before the filesystem image is created.

```sh
$ cat > board/myorg/pa-mini/post-build.sh <<'EOF'
#!/bin/sh
set -eu

TARGET_DIR="$1"

mkdir -p "$TARGET_DIR/data" "$TARGET_DIR/etc"

cat > "$TARGET_DIR/etc/build-info" <<INFO
board=pa-mini
date=$(date -u +%Y-%m-%dT%H:%M:%SZ)
git=$(git -C "$BR2_EXTERNAL" rev-parse --short HEAD 2>/dev/null || echo unknown)
INFO

chmod 0644 "$TARGET_DIR/etc/build-info"
EOF
$ chmod +x board/myorg/pa-mini/post-build.sh
```

This is where you generate simple files. Keep it deterministic when making releases. For a final release, avoid `date` unless you intentionally want the image to differ every build.

## 35E.4  Add genimage

Create `board/myorg/pa-mini/genimage.cfg`:

```text
image boot.vfat {
  vfat {
    files = {
      "zImage",
      "imx6ull-pa-mini.dtb"
    }
  }
  size = 128M
}

image sdcard.img {
  hdimage {
  }

  partition boot {
    partition-type = 0x0C
    bootable = true
    image = "boot.vfat"
    size = 128M
  }

  partition rootfs {
    partition-type = 0x83
    image = "rootfs.ext4"
    size = 512M
  }

  partition data {
    partition-type = 0x83
    size = 512M
  }
}
```

Add `post-image.sh`:

```sh
$ cat > board/myorg/pa-mini/post-image.sh <<'EOF'
#!/bin/sh
set -eu

BOARD_DIR="$(dirname "$0")"
GENIMAGE_TMP="${BUILD_DIR}/genimage.tmp"

rm -rf "$GENIMAGE_TMP"

genimage \
  --rootpath "$TARGET_DIR" \
  --tmppath "$GENIMAGE_TMP" \
  --inputpath "$BINARIES_DIR" \
  --outputpath "$BINARIES_DIR" \
  --config "$BOARD_DIR/genimage.cfg"
EOF
$ chmod +x board/myorg/pa-mini/post-image.sh
```

Enable host `genimage` in Buildroot:

```text
BR2_PACKAGE_HOST_GENIMAGE=y
```

## 35E.5  Connect it in Buildroot config

Open menuconfig:

```sh
$ make menuconfig
```

Set:

```text
System configuration  --->
  Root filesystem overlay directories = board/myorg/pa-mini/rootfs-overlay

System configuration  --->
  Custom scripts to run before creating filesystem images = board/myorg/pa-mini/post-build.sh

Filesystem images  --->
  [*] ext2/3/4 root filesystem
      ext2/3/4 variant = ext4

Host utilities  --->
  [*] host genimage

System configuration  --->
  Custom scripts to run after creating filesystem images = board/myorg/pa-mini/post-image.sh
```

Then save:

```sh
$ make savedefconfig BR2_DEFCONFIG=configs/pa_mini_defconfig
```

Now the product can be rebuilt with:

```sh
$ make pa_mini_defconfig
$ make -j$(nproc)
```

## 35E.6  Kernel and BusyBox fragments

Buildroot can merge kernel config fragments:

```text
BR2_LINUX_KERNEL_CONFIG_FRAGMENT_FILES="board/myorg/pa-mini/linux.fragment"
```

Example `linux.fragment`:

```text
CONFIG_DEVTMPFS=y
CONFIG_DEVTMPFS_MOUNT=y
CONFIG_OVERLAY_FS=y
CONFIG_BLK_DEV_INITRD=y
```

BusyBox fragments work similarly:

```text
BR2_PACKAGE_BUSYBOX_CONFIG_FRAGMENT_FILES="board/myorg/pa-mini/busybox.fragment"
```

Example `busybox.fragment`:

```text
CONFIG_ASH=y
CONFIG_MDEV=y
CONFIG_SWITCH_ROOT=y
CONFIG_FEATURE_EDITING=y
```

Fragments are better than hand-editing generated `.config` files.

## 35E.7  What to commit

Commit:

- `configs/pa_mini_defconfig`
- `board/myorg/pa-mini/rootfs-overlay/`
- `board/myorg/pa-mini/post-build.sh`
- `board/myorg/pa-mini/post-image.sh`
- `board/myorg/pa-mini/genimage.cfg`
- kernel and BusyBox fragments

Do not commit:

- `output/`
- `dl/`
- `host/`
- generated images

Those are build outputs or caches.

## 35E.8  Lab

1. Create `board/myorg/pa-mini/`.
2. Add `/etc/motd` through `rootfs-overlay/`.
3. Add `post-build.sh` that writes `/etc/build-info`.
4. Add `genimage.cfg` and `post-image.sh`.
5. Build `sdcard.img`.
6. Flash the image to SD and boot.
7. Confirm `/etc/motd`, `/etc/build-info`, and `/data` exist.

## 35E.9  Pitfalls

- **Editing `output/target/`.** It feels fast but disappears on rebuild.
- **Putting generated files in overlay.** Use post-build for generated files.
- **Using absolute host paths.** Keep paths relative to the Buildroot tree or board directory.
- **Forgetting host genimage.** `post-image.sh` fails if `genimage` is not available.
- **Committing `output/`.** It is huge and not reproducible review material.

---

Previous chapter: [Chapter 35I - Boot from SPI NOR flash](ch35I-boot-from-spi-nor-flash.md)

Next chapter: [Chapter 35A - Ubuntu-base rootfs](ch35A-ubuntu-base.md)
