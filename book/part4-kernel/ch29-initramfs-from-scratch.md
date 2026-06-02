---
chapter: 29
title: Initramfs from scratch
part: IV — The Kernel
estimated_pages: 16
status: draft
---

# Chapter 29 — Initramfs from scratch

> **What:** the absolute minimum user space that a Linux kernel can hand off to — a single statically-linked binary in a cpio archive, ~30 KB, that prints "hello" and reboots. Then a BusyBox-based initramfs with a real shell. Both reachable in under an hour.
>
> **Why:** the standard rootfs path (`root=/dev/mmcblk0p2`) hides a lot. Building an initramfs by hand surfaces the actual kernel-to-userspace handoff: what kernel_init's `kernel_execve` does, what `/init` must look like, how cpio archives become a populated filesystem at boot. Once you have done it once, Buildroot and Ubuntu-base in Part V build on the same idea, just with more pieces.
>
> **Focus:** the **cpio archive as a filesystem image** that the kernel unpacks into the initial tmpfs. Once that model is clear, the rest is just commands.

## 29.1  What an initramfs is

An **initramfs** is a small filesystem image that the kernel loads into RAM before any "real" disk filesystem is mounted. The kernel mounts the initramfs as `/`, runs `/init`, and from there `/init` can do whatever it wants — usually pivot to a real rootfs on disk, but for embedded systems the initramfs *is* the rootfs.

The image format is **cpio** (the venerable Unix archive format), optionally compressed with gzip/bzip2/xz/zstd. The kernel has a built-in cpio extractor that runs very early in boot.

Two ways to get the cpio archive into kernel memory:

1. **Built into the kernel image.** The kernel's `usr/initramfs_data.cpio.gz` gets linked into `vmlinux` (and therefore into `zImage`). The kernel knows the archive's location; on boot it extracts it.
2. **Loaded separately by the bootloader.** U-Boot reads `initramfs.cpio.gz` into RAM at some address, passes that address via the DT's `/chosen/linux,initrd-start` and `linux,initrd-end` properties (or the legacy ATAGS), and the kernel extracts from there.

Option 1 is simpler for tiny images. Option 2 is more flexible — you can change the rootfs without rebuilding the kernel — and is the standard choice for anything bigger. We'll do both.

## 29.2  The smallest possible initramfs

A single binary that prints "hello", waits a moment, and reboots:

`hello.c`:

```c
#include <stdio.h>
#include <unistd.h>
#include <sys/reboot.h>
#include <linux/reboot.h>

int main(void)
{
    /* Open the kernel console so printf goes somewhere visible. */
    /* (kernel_init opens /dev/console as fd 0,1,2 before running /init.) */

    puts("\n*** hello from a one-binary initramfs ***\n");

    for (int i = 5; i > 0; i--) {
        printf("rebooting in %d...\n", i);
        sleep(1);
    }

    /* Use the raw syscall — we don't depend on libc init having done anything. */
    syscall(__NR_reboot,
            LINUX_REBOOT_MAGIC1, LINUX_REBOOT_MAGIC2,
            LINUX_REBOOT_CMD_RESTART, NULL);

    return 0;   /* unreachable on a successful reboot */
}
```

Build statically so we have no library dependencies on the target:

```sh
$ arm-linux-gnueabihf-gcc -static -Os -o init hello.c
$ arm-linux-gnueabihf-strip init
$ ls -lh init
-rwxr-xr-x 1 you you 480K Jan 22 init
```

480 KB statically linked against glibc. That's ten times the size of the program itself; glibc is fat. With **musl** instead:

```sh
$ musl-gcc -static -Os -o init hello.c   # or use arm-linux-musleabihf-gcc
$ arm-linux-gnueabihf-strip init
$ ls -lh init
-rwxr-xr-x 1 you you  30K Jan 22 init
```

30 KB. That's roughly the minimum a statically-linked C program reaches.

Build the cpio archive:

```sh
$ mkdir -p initramfs
$ cp init initramfs/init                 # MUST be named "init" at the root
$ cd initramfs
$ find . | cpio -o -H newc | gzip > ../initramfs.cpio.gz
$ ls -lh ../initramfs.cpio.gz
-rw-r--r-- 1 you you 14K Jan 22 ../initramfs.cpio.gz
```

`-H newc` selects the SVR4 / portable ASCII cpio format the kernel expects. The result is a 14 KB compressed image containing one file (`/init`, executable). The kernel will extract this into a tmpfs, execute `/init`, and we'll see the hello message.

## 29.3  Booting it from U-Boot

Drop `initramfs.cpio.gz` into your TFTP server, then:

```
=> tftp 0x82000000 zImage
=> tftp 0x83000000 imx6ull.dtb
=> tftp 0x84000000 initramfs.cpio.gz
=> setenv bootargs 'console=ttymxc0,115200 earlycon rdinit=/init'
=> bootz 0x82000000 0x84000000 0x83000000
```

Notice the new things:

- **`tftp 0x84000000 initramfs.cpio.gz`** — load the initramfs at a third DRAM address.
- **`rdinit=/init`** — tells `kernel_init` to run `/init` from the initramfs (instead of `/sbin/init` from a disk rootfs).
- **`bootz 0x82000000 0x84000000 0x83000000`** — the second argument is now the initrd address (no longer `-`). U-Boot writes both `linux,initrd-start` and `linux,initrd-end` into the DT.

You should see:

```
[   2.087xxx] Freeing unused kernel image (initmem) memory: 1024K
[   2.110xxx] Run /init as init process

*** hello from a one-binary initramfs ***

rebooting in 5...
rebooting in 4...
rebooting in 3...
rebooting in 2...
rebooting in 1...
[   7.214xxx] reboot: Restarting system
```

That is the smallest user space that boots Linux on this board: 30 KB compiled.

## 29.4  A BusyBox-based initramfs (real shell)

`hello` is just a demo. A practical initramfs has a shell and some utilities, plus an init system. **BusyBox** packs all of these into one statically-linked binary of about 600 KB. It exposes hundreds of applets — most of the common Unix utilities.

```sh
$ cd ~/imx6ull/src
$ wget https://busybox.net/downloads/busybox-1.36.1.tar.bz2
$ tar xf busybox-1.36.1.tar.bz2
$ cd busybox-1.36.1
$ make ARCH=arm CROSS_COMPILE=arm-linux-gnueabihf- defconfig

# Enable static linking
$ make ARCH=arm CROSS_COMPILE=arm-linux-gnueabihf- menuconfig
# Settings → Build static binary (no shared libs) → [*]
# Save and exit.

$ make ARCH=arm CROSS_COMPILE=arm-linux-gnueabihf- -j$(nproc)
$ ls -lh busybox
-rwxr-xr-x 1 you you 1.2M Jan 22 busybox
$ arm-linux-gnueabihf-strip busybox
$ ls -lh busybox
-rwxr-xr-x 1 you you 580K Jan 22 busybox
```

580 KB statically linked against glibc. With musl, ~450 KB.

Now build a rootfs around it:

```sh
$ cd ~/imx6ull
$ mkdir -p initramfs/{bin,sbin,etc,proc,sys,dev,tmp,var,root,lib,usr/bin,usr/sbin}
$ cp ~/imx6ull/src/busybox-1.36.1/busybox initramfs/bin/

# Create busybox symlinks for every applet (ls, sh, cp, ...)
$ cd initramfs/bin
$ for app in $(./busybox --list); do
    ln -s busybox $app
  done
$ cd ../..

# Symlink /sbin/init → /bin/busybox; busybox knows to run as init when called this way.
$ ln -s /bin/busybox initramfs/sbin/init

# A minimal inittab for busybox's init
$ cat > initramfs/etc/inittab <<'EOF'
::sysinit:/etc/init.d/rcS
::respawn:-/bin/sh
::ctrlaltdel:/sbin/reboot
::shutdown:/bin/umount -a -r
EOF

# A minimal startup script
$ mkdir -p initramfs/etc/init.d
$ cat > initramfs/etc/init.d/rcS <<'EOF'
#!/bin/sh
mount -t proc none /proc
mount -t sysfs none /sys
mount -t devtmpfs none /dev
echo "*** BusyBox initramfs is up ***"
EOF
$ chmod +x initramfs/etc/init.d/rcS

# Repackage
$ cd initramfs
$ find . | cpio -o -H newc | gzip > ../initramfs.cpio.gz
$ ls -lh ../initramfs.cpio.gz
-rw-r--r-- 1 you you 250K Jan 22 ../initramfs.cpio.gz
```

250 KB compressed. Load and boot as before, but **drop `rdinit=/init`** from bootargs — busybox-init wants to run as `/sbin/init`, which is the default search order:

```
=> setenv bootargs 'console=ttymxc0,115200 earlycon'
=> bootz 0x82000000 0x84000000 0x83000000
```

After kernel boots, you should see:

```
[   2.298xxx] Run /sbin/init as init process
*** BusyBox initramfs is up ***

Please press Enter to activate this console.

# ls /
bin   dev  etc   lib   proc  root  sbin  sys  tmp  usr  var
# cat /proc/cpuinfo
processor  : 0
model name : ARMv7 Processor rev 5 (v7l)
...
```

You have a real Unix shell on the i.MX6ULL. From here you can `cd`, `ls`, `mount`, `vi`, `ifconfig` — every common Unix command, supplied by BusyBox.

## 29.5  Embedded vs separate

Two architectures for shipping the initramfs:

### Embedded in the kernel

```sh
# In kernel's .config:
CONFIG_INITRAMFS_SOURCE="/home/you/imx6ull/initramfs.cpio.gz"

$ make ARCH=arm zImage     # zImage now includes initramfs internally
```

The `zImage` grows by the initramfs size; no separate bootloader step. Convenient for a *fixed* initramfs that's part of the kernel's release artifact. Used by single-purpose appliances and by recovery kernels.

### Separate file loaded by bootloader

What we did above. The kernel is one file (`zImage`), the initramfs is another (`initramfs.cpio.gz`). The bootloader loads both. The advantage is *changing the rootfs doesn't require rebuilding the kernel*. Used by basically every serious embedded system.

Choose based on how often the rootfs changes vs the kernel. For early development, embedded is faster (one artefact). For production, separate is more flexible.

## 29.6  Init systems compared

Once you have user space running, what runs as PID 1? Three common choices for embedded:

| Init | Footprint | What you get |
|------|-----------|--------------|
| **BusyBox init** | < 1 KB on top of busybox | One inittab; classic Unix `respawn` / `sysinit` semantics. Sufficient for 95% of embedded |
| **`sysvinit`** | ~80 KB | The traditional System V `/etc/rc.d/init.d/*` scripts. Familiar to anyone from before 2010 |
| **`systemd`** | ~5 MB + dependencies | Service unit files, sockets, journal, timers. Powerful, big, dependency-heavy |

For embedded, **BusyBox init** is the default. We use it in this book through Chapter 31 and switch to discussing systemd in Chapter 33.

## 29.7  Lab

1. **Build and run the one-binary initramfs** from §29.2 and §29.3. Time how long the kernel takes from `bootz` to printing `hello`.
2. **Replace the C program** with one that reads `/proc/cpuinfo` and prints it. Confirms that you can run arbitrary code as PID 1.
3. **Build and run the BusyBox initramfs** from §29.4. Get to a shell. Run `ls /proc`, `cat /proc/meminfo`, `dmesg | tail`.
4. **Embed the initramfs.** Add `CONFIG_INITRAMFS_SOURCE` to your kernel's `.config`, rebuild, boot with `bootz <kernel> - <dtb>` (no separate initrd address). Verify the kernel boots to the same shell.
5. **Mount sysfs.** From the BusyBox shell, `ls /sys/class/gpio/`. Confirm devtmpfs and sysfs are populated. Echo a value to `/sys/class/leds/<your-led>/brightness` and observe the LED change.

## 29.8  Pitfalls

- **`/init` must exist at the root and be executable.** Forget either and the kernel panics with "No filesystem could mount root, tried: ramfs". Cpio archives don't error on missing init.
- **`/init` linked dynamically.** If `/init` depends on `libc.so.6` and `libc.so.6` isn't in the cpio, exec fails silently. Either statically link (recommended) or include the needed `.so` files in `/lib/` of the initramfs.
- **`init=` vs `rdinit=`.** `init=path` tells the kernel to look on the *root filesystem* (the one specified by `root=`). `rdinit=path` tells it to look on the *initramfs*. For initramfs-only boots, use `rdinit=` or just rely on the default `/init` lookup.
- **cpio archive built without `-H newc`.** Default cpio format isn't what the kernel expects; the unpacker reports an error and gives up. Always `-H newc`.
- **Trailing slash on `find .`.** `find .` gives relative paths like `./init`, which is what cpio wants. `find /home/you/initramfs` gives absolute paths, so the archive ends up with `/home/you/initramfs/init` and the kernel cannot find `/init`. Always `cd` into the rootfs first.
- **BusyBox not statically linked.** Built dynamic by default. Forgetting to set static causes the binary to need glibc shared objects you don't have in the initramfs. Symptom: `Kernel panic - not syncing: Attempted to kill init!` because `exec` fails.
- **No `/dev/console` before `kernel_init` opens it.** Kernel handles this automatically via devtmpfs auto-mount, but if you disable that in `.config`, you'll see `Warning: unable to open an initial console` and lose all stdio in your init. Keep `CONFIG_DEVTMPFS=y` and `CONFIG_DEVTMPFS_MOUNT=y`.

## 29.9  Going deeper

- **`Documentation/filesystems/ramfs-rootfs-initramfs.rst`** — canonical kernel doc on the initramfs mechanism.
- **`Documentation/admin-guide/initrd.rst`** — older initrd mechanism (predecessor to initramfs); useful context.
- **BusyBox manual** at `busybox.net/about.html` and the per-applet `--help`.
- **`init/initramfs.c`** — the kernel's cpio extractor. Short and readable.
- **`klibc`** — an even smaller libc-replacement than musl, designed specifically for in-kernel-cpio-initramfs static binaries.

> Next chapter: **Chapter 30 — Kernel configuration deep-dive.** We've used `imx_v6_v7_defconfig` blindly through Part IV. Now we open `make menuconfig` and learn the major knobs that decide what's compiled in.
