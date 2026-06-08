---
chapter: 35B
title: Read-only rootfs + overlayfs (the industrial pattern)
part: V — Root filesystem & user space (supplementary v1.2)
estimated_pages: 16
status: draft
---

# Chapter 35B — Read-only rootfs + overlayfs
**sysfs** - a kernel-generated filesystem under /sys that exposes devices, drivers, and attributes.

> **What:** mount the root filesystem **read-only** on a shipped product, then use **`overlayfs`** to give the parts of `/` that must be writable (e.g., `/var/log/`, `/etc/`, `/tmp/`) a per-boot tmpfs or persistent overlay. The result: power can drop at any instant without corrupting the rootfs.
> **rootfs** - root filesystem, the directory tree mounted at / that contains /bin, /etc, /dev, and libraries.
>
> **Why:** every shipping industrial product mounts its rootfs read-only. The reason is simple: a user yanks the power, the filesystem doesn't catch the close-and-flush, the next boot's `fsck` finds inconsistencies, sometimes corrects them, sometimes returns "dropped to /bin/sh for emergency repair." A read-only rootfs cannot be corrupted by power loss because no one is writing to it. The trade is that any data the system *does* need to write must go somewhere else — a tmpfs (lost on reboot), a separate data partition (persistent), or an overlay (write-through to tmpfs / data partition).
>
> **Focus:** the **three-tier model** — `lowerdir` (immutable rootfs), `upperdir` (where changes accumulate), `workdir` (overlay's scratch space). Once you understand those three, every overlayfs setup follows the same shape.


## 35B.1  The problem this solves

A standard development rootfs is mounted `rw` (read-write). The kernel buffers writes in its page cache and flushes them to disk lazily. If power drops between the page-cache write and the disk flush, you can end up with:

- Files partially written (data in disk blocks that the inode doesn't yet point to)
- Inodes updated but their containing block not yet flushed (vice versa)
- Journal entries half-committed (ext4's journal recovers some of these on next mount)

`fsck` runs on next boot and tries to fix what it can. Sometimes it succeeds. Sometimes a critical config file ends up with garbage in it and your system boots into a degraded state. Sometimes `fsck` decides the filesystem is unrecoverable and aborts to a recovery shell.

Every team that has shipped a product has at least one corrupted-rootfs story from a power glitch in the field.

The fix: **don't write to the rootfs at runtime**. If nothing is writing, nothing can be half-written. Power-loss safety becomes a property of the filesystem layout, not of the application or filesystem driver.

## 35B.2  Two patterns

There are two common ways to ship a read-only rootfs:

### Pattern A — RO rootfs + tmpfs for writable paths

The simplest. Your application doesn't need writes to persist. It just needs *some* place to put `/var/log/`, `/tmp/`, and any temp state. Make those paths point to a tmpfs (RAM-backed, lost on reboot — exactly what you want for `/tmp/`):

```
/        ext4 ro       (root filesystem; immutable)
/tmp     tmpfs rw      (RAM; gone on reboot)
/var/log tmpfs rw      (RAM; gone on reboot)
/var/run tmpfs rw      (RAM; gone on reboot)
/run     tmpfs rw      (RAM; gone on reboot)
```

Add to `/etc/fstab`:

```
# device     mountpoint   type     options                    dump  pass
proc         /proc        proc     defaults                   0     0
sysfs        /sys         sysfs    defaults                   0     0
tmpfs        /tmp         tmpfs    defaults,nosuid,nodev      0     0
tmpfs        /var/log     tmpfs    defaults,size=8M           0     0
tmpfs        /var/run     tmpfs    defaults,size=2M           0     0
tmpfs        /run         tmpfs    defaults,size=2M           0     0
```

And set bootargs:

```
root=/dev/mmcblk1p2 ro rootwait    # ← note the "ro"
```

That's it. The rootfs is mounted RO. The tmpfs mounts give you writable paths.

The downside: anything in `/etc/` you'd want to modify (e.g., `/etc/network/interfaces` to change IP, `/etc/hostname` to set device serial) requires *rebuilding the rootfs* or some out-of-band update mechanism.

### Pattern B — RO rootfs + overlay for selective persistence

If you want some changes to persist (e.g., the device's serial number, configuration, learned data), use **overlayfs**. The rootfs stays read-only. an overlay on top gives the illusion of writability and stores changes to a separate persistent partition.

```
                user-space sees a normal "writable /"
                            ▲
                            │   read = check upper first, else lower
                            │   write = always to upper
                            │
                ┌───────────┴────────────┐
                │  overlayfs (kernel)    │
                └───────────┬────────────┘
                            │
        ┌───────────────────┴──────────────────┐
        │                                      │
   lowerdir (RO)                          upperdir (RW)
   /dev/mmcblk1p2                         /dev/mmcblk1p3
   the rootfs                             persistent overlay partition
   (~100 MB)                              (~50 MB, only changes)
```

When the application writes to `/etc/hostname`, overlayfs copies `/etc/hostname` from `lowerdir` to `upperdir` ("copy-up"), then applies the write. From then on, reads of `/etc/hostname` come from `upperdir`. When `upperdir` is on a persistent partition, the change survives reboots.

The deeper trade-off:

- **More flexible** than Pattern A — you can change config files post-deployment.
- **More complex** — you need a second partition, a setup script that mounts the overlay, and a story for "what if the overlay partition gets corrupted?" (Hint: factory reset = mount without the overlay, you get the pristine rootfs.)

We'll set up both. Pattern A first because it's simpler.

## 35B.3  Pattern A in practice

Assume the rootfs we built in Chapter 31 or Chapter 35 lives on `/dev/mmcblk1p2` (the second eMMC partition. `p1` is FAT for boot, `p2` is ext4 root).

Build the rootfs as normal, with whatever method you prefer. Then customise `/etc/fstab` as in §35B.2 above. Save.

On the host, **before deploying**, make sure no `rw` paths sneak in:

```sh
# What writes to /etc/ at runtime?
$ grep -rn "open.*WRONLY\|fopen.*\"[wa]" $TARGET_DIR/etc/ | head
```

Common culprits to fix:

- `/etc/resolv.conf` updated by `dhclient` — link to `/run/resolv.conf` (tmpfs) instead.
- `/etc/adjtime` updated by `hwclock` — same fix, or use `--noadjfile`.
- `/etc/machine-id` (systemd) — needs to be persistent. pre-generate at install time, then it's not written at boot.
- `/var/log/*` — ensure your tmpfs has enough space (`size=8M` in our fstab) and you have log rotation. otherwise the tmpfs fills up.

Adjust bootargs (in U-Boot env):
> **MCU bridge:** Think of U-Boot like a much larger boot stub plus debug monitor: it initializes hardware, loads the next image, and gives you commands before Linux starts.
**U-Boot** - the bootloader that initializes enough hardware to load and start the Linux kernel.

```
=> setenv bootargs 'console=ttymxc0,115200 earlycon root=/dev/mmcblk1p2 ro rootwait ...'
=> saveenv
```

Boot. From the shell:

```
[root@pa-mini:~]# mount | head -1
/dev/mmcblk1p2 on / type ext4 (ro,relatime,...)

[root@pa-mini:~]# touch /etc/test
touch: /etc/test: Read-only file system

[root@pa-mini:~]# touch /var/log/test
[root@pa-mini:~]# ls /var/log/test
/var/log/test                            ← writable, in tmpfs
```

`/` is RO. tmpfs paths are RW. The system is now power-cycle safe.

## 35B.4  Pattern B — overlayfs

For changes that need to persist, set up overlayfs. We'll make `/etc/`, `/var/`, and `/home/` overlay-mounted on top of the RO rootfs, with the upper layer on a separate eMMC partition.

### Partition layout

> **Storage safety:** Before any command that names /dev/sdX, run lsblk -o NAME,SIZE,MODEL,TRAN,TYPE,MOUNTPOINTS.
> Verify the removable card by size and model, unmount its partitions, and stop if the path is not the target card. Writing the wrong /dev node can destroy the host disk.


```
/dev/mmcblk1p1   FAT  boot files (zImage, dtb, optional)
/dev/mmcblk1p2   ext4 rootfs (RO, ~200 MB)
/dev/mmcblk1p3   ext4 overlay upper + data (RW, ~500 MB)
```

Create them with `fdisk` or `parted`. Format:

```sh
$ sudo mkfs.ext4 -L rootfs   /dev/mmcblk1p2
$ sudo mkfs.ext4 -L overlay  /dev/mmcblk1p3
```

### Initial population

```sh
$ sudo mount /dev/mmcblk1p2 /mnt/rootfs
$ sudo tar -xzf rootfs.tar.gz -C /mnt/rootfs/
$ sudo mount /dev/mmcblk1p3 /mnt/overlay
$ sudo mkdir /mnt/overlay/{upper-etc,work-etc,upper-var,work-var,upper-home,work-home,data}
```

### Boot-time overlay setup

The overlay mount has to happen *after* the kernel mounts the rootfs but *before* `init` runs significant other things. The cleanest place is an initramfs that does the overlay setup, then exec's the real init. Or, if you don't have an initramfs, in `/etc/init.d/rcS` very early (before `mount -a`).

Here's the initramfs approach (preferred). Build an initramfs (Ch 29) with a `/init` like:

```sh
#!/bin/sh
# Early init: set up overlay, then exec real /sbin/init

# Mount essential virtual filesystems
mount -t proc      none /proc
mount -t sysfs     none /sys
mount -t devtmpfs  none /dev

# Mount the RO rootfs
mkdir -p /rofs
mount -o ro /dev/mmcblk1p2 /rofs

# Mount the overlay upper partition
mkdir -p /overlay
mount /dev/mmcblk1p3 /overlay

# Build an overlay for /etc, /var, /home
for d in etc var home; do
    mkdir -p /merged/$d
    mount -t overlay overlay \
        -o lowerdir=/rofs/$d,upperdir=/overlay/upper-$d,workdir=/overlay/work-$d \
        /merged/$d
done

# Build the merged root: lower = rofs, upper = merged dirs
mkdir -p /merged-root
mount --bind /rofs /merged-root

# Bind-mount the overlayed subdirs over the read-only rootfs
mount --bind /merged/etc  /merged-root/etc
mount --bind /merged/var  /merged-root/var
mount --bind /merged/home /merged-root/home

# Pivot
mkdir -p /merged-root/oldroot
pivot_root /merged-root /merged-root/oldroot

# Exec the real init
exec /sbin/init
```

That `/init` is ~30 lines but does the whole dance: mount RO rootfs, mount overlay storage, overlay-mount the writable subdirs, pivot the root, exec real init.

A simpler approach (no initramfs) that works for some setups: a small `S00-overlay` script in `/etc/init.d/` that runs *before* `S01-mountall` (BusyBox runs them alphabetically). But mounting overlay over a partial filesystem is fragile. initramfs is cleaner.

### From inside the running system

```
[root@pa-mini:~]# mount | grep overlay
overlay on /etc type overlay (rw,lowerdir=/rofs/etc,upperdir=/overlay/upper-etc,workdir=/overlay/work-etc)
overlay on /var type overlay (rw,lowerdir=/rofs/var,upperdir=/overlay/upper-var,workdir=/overlay/work-var)
overlay on /home type overlay (rw,lowerdir=/rofs/home,upperdir=/overlay/upper-home,workdir=/overlay/work-home)

[root@pa-mini:~]# touch /etc/test
[root@pa-mini:~]# ls /overlay/upper-etc/
test
```

You wrote to `/etc/test`. The kernel copy-up'd to `/overlay/upper-etc/test`. The original `/rofs/etc/` is untouched.

Reboot. `/etc/test` survives. The RO rootfs is unchanged.

## 35B.5  Power-cycle test

The whole point. Let's verify:

```
[root@pa-mini:~]# cat > /var/log/important.txt <<EOF
> some important production log entry
> EOF

[root@pa-mini:~]# while true; do
>   echo "$(date) tick" >> /var/log/important.txt
>   sleep 1
> done
```

While that's running, **yank the power**. (Use the SD card. pull it. reinsert. power up.)

After reboot:

- The rootfs at `/dev/mmcblk1p2` is intact. `fsck` shows clean (it was mounted RO. no journal entries to recover).
- `/var/log/important.txt`'s last few lines may be missing or partial — but **only the lines written in the second or two before power loss**. The earlier content is preserved.
- The system boots cleanly.

Compare with the same test on a RW rootfs: half the time you get a clean boot. half the time `fsck` finds something that needs manual intervention. Over a thousand power cycles, the difference is large enough to count.

## 35B.6  Factory reset

A nice property of Pattern B: **factory reset is trivial**. Erase the overlay partition:

```
[root@pa-mini:~]# rm -rf /overlay/upper-*/*
[root@pa-mini:~]# reboot
```

Next boot, the overlay has nothing, so user-space sees the pristine rootfs. No actual reflashing of the rootfs needed — it was never written to.

A common production button-combination is "hold the recovery button at boot for 5 seconds → wipe overlay → reboot." The user gets a factory-fresh system in 30 seconds.

## 35B.7  Lab

1. **Convert your Chapter 31/35 rootfs to RO + tmpfs (Pattern A).** Test that writes to `/tmp/` work but writes to `/etc/` fail. Power-cycle 10 times. verify no `fsck` errors.
2. **Set up Pattern B.** Partition an SD card with `rootfs` + `overlay` partitions. Build the initramfs. Boot. Verify `/etc/test` persists across reboots.
3. **Power-cycle stress test.** Write a script that creates a counter file in the overlay, increments it once per second, and `sync`s. Run it. power-cycle 100 times at random intervals. After 100 cycles, the counter should be roughly accurate (within ~2 per cycle of slack for sync timing) and the rootfs should never have needed `fsck`.
4. **Factory reset.** Trigger from inside a running shell (`rm -rf /overlay/upper-*. reboot`). Verify pristine state on next boot.
5. **Quantify the cost.** What's the boot-time overhead of the overlay setup? (Time the initramfs's overlay mounts.) What's the RAM cost?

## 35B.8  Pitfalls

- **`/etc/resolv.conf` and `/etc/adjtime`.** Both written at runtime in default Ubuntu/Debian setups. Either symlink them to `/run/` (tmpfs) or use overlay. If they end up trying to write to a RO mount, things like DHCP and NTP silently misbehave.
- **systemd's `/etc/machine-id`.** Generated on first boot, written to `/etc/`. On RO root, systemd may regenerate it every boot, breaking journal continuity. Fix: pre-generate at flash time.
- **Forgetting `ro` in `bootargs`.** Without `ro` in `bootargs` the whole scheme is defeated. Verify with `mount | head -1` after boot.
- **Overlay `workdir` must be on the same filesystem as `upperdir`.** Different filesystems for `workdir` and `upperdir` is an immediate mount failure.
- **Tmpfs filling up.** `/var/log` on tmpfs without log rotation, plus a chatty daemon, eats your RAM. Set `size=` explicitly and use `logrotate` (or just `> /var/log/messages` from cron).
- **Apps writing to `/etc/` expecting persistence.** If your app does `fopen("/etc/myapp.conf", "w")` to save settings, with Pattern A those settings are lost on reboot. Either use Pattern B (overlay) or move the writable file to `/data/` (a real persistent partition).
- **`pivot_root` failing in initramfs.** `pivot_root` requires the new root to not be `/`. Always operate on `/merged-root` or similar, never directly on `/`.

## 35B.9  Going deeper

- **`Documentation/filesystems/overlayfs.rst`** in the kernel tree — the canonical reference.
- **`man 8 mount.overlay`** — overlay mount options in depth.
- **`erofs`** — Enhanced Read-Only File System, an alternative to ext4-RO with better compression. Used in modern Android.
- **`squashfs`** — another RO filesystem, slower but more compact than erofs. Common on initramfs images.
- **`A/B partition schemes`** — pair this chapter with Ch 63 (Field updates). Two RO rootfs partitions, switch atomically on update.

> Next chapter: **Chapter 35C — Container runtimes on embedded.** With a stable RO rootfs base, container engines like Podman become an attractive way to ship the variable application layer.
