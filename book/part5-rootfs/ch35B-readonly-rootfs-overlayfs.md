---
chapter: 35B
title: Read-only rootfs + overlayfs (the industrial pattern)
part: V - Root filesystem & user space (supplementary v1.2)
estimated_pages: 16
status: draft
---

# Chapter 35B: Read-only rootfs + overlayfs
> **sysfs:** a kernel-generated filesystem under /sys that exposes devices, drivers, and attributes.

> **What:** separate an immutable base system from writable runtime state. A **read-only root filesystem** and **overlayfs** can place changes in a per-boot tmpfs or a persistent upper layer. This reduces writes to the base image, but is not a blanket power-loss guarantee for the storage device or writable data.
> **rootfs:** root filesystem, the directory tree mounted at / that contains /bin, /etc, /dev, and libraries.
>
> **Why:** an unexpected power cut can interrupt a write or leave application state inconsistent. Keeping the base system immutable limits what ordinary runtime writes can change and gives recovery a stable starting point. Writable state still needs a home: tmpfs for disposable data, a separate data partition for persistent records, or an overlay for changes presented inside the root tree. Its durability and recovery behavior remain design decisions.
>
> **Focus:** the **three-tier model**, `lowerdir` (immutable rootfs), `upperdir` (where changes accumulate), `workdir` (overlay's scratch space). Once you understand those three, every overlayfs setup follows the same shape.


## 35B.1  The problem this solves

A standard development rootfs is mounted `rw` (read-write). A successful write can still leave data buffered in memory. If power disappears before that data reaches persistent storage, the next boot may see an older file or an incomplete update.

The filesystem and the application protect different things. Ext4's default journal protects metadata updates, not complete application transactions. A filesystem can recover its structure while a configuration file remains unusable. Journal replay and any boot-time filesystem check also depend on the filesystem and boot policy. A repair tool cannot reconstruct application data that never reached storage. See the [ext4 journal documentation](https://docs.kernel.org/filesystems/ext4/journal.html).

The risk belongs to both the filesystem and the application: a filesystem can remain mountable while a partially updated configuration is unusable.

One strategy is **not to write to the base rootfs at runtime**. That removes a class of interrupted updates to the base image. It does not remove the need for durable application transactions, storage qualification and a recoverable update process.

## 35B.2  Two patterns

There are two common ways to ship a read-only rootfs:

### Pattern A, RO rootfs + tmpfs for writable paths

The simplest. Your application doesn't need writes to persist. It just needs *some* place to put `/var/log/`, `/tmp/`, and any temp state. Make those paths point to a tmpfs (RAM-backed, lost on reboot, exactly what you want for `/tmp/`):

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

### Pattern B, RO rootfs + overlay for selective persistence

If you want some changes to persist (e.g., the device's serial number, configuration, learned data), use **overlayfs**. The rootfs stays read-only. An overlay on top gives the illusion of writability and stores changes to a separate persistent partition.

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

- **More flexible** than Pattern A, you can change config files post-deployment.
- **More complex**: early boot must mount the overlay and handle an unreadable upper layer. Falling back to base defaults is safe only if the product can operate without the settings or identity stored in that layer.

The following examples show where each pattern puts its writable state. Pattern A has fewer boot dependencies, so it comes first.

## 35B.3  Pattern A in practice

Assume the rootfs we built in Chapter 31 or Chapter 35 lives on `/dev/mmcblk1p2` (the second eMMC partition. `p1` is FAT for boot, `p2` is ext4 root).

The rootfs build owns the `/etc/fstab` entries shown in §35B.2. Runtime services must agree with those mount boundaries.

Searching configuration files can help identify expected writers, but a text search cannot prove that every service respects a read-only root:

```sh
# What writes to /etc/ at runtime?
$ grep -rn "open.*WRONLY\|fopen.*\"[wa]" $TARGET_DIR/etc/ | head
```

Common culprits to fix:

- `/etc/resolv.conf` updated by `dhclient`, link to `/run/resolv.conf` (tmpfs) instead.
- `/etc/adjtime` updated by `hwclock`, same fix, or use `--noadjfile`.
- `/etc/machine-id` (systemd), needs to be persistent. Pre-generate at install time, then it's not written at boot.
- `/var/log/*`: ensure your tmpfs has enough space (`size=8M` in our fstab) and you have log rotation. Otherwise the tmpfs fills up.

The `ro` boot argument expresses the initial root-mount policy. Persistent environment changes are a separate bootloader design decision, not a requirement for this example:
> **MCU bridge:** Think of U-Boot like a much larger boot stub plus debug monitor: it initializes hardware, loads the next image, and gives you commands before Linux starts.
> **U-Boot:** the bootloader that initializes enough hardware to load and start the Linux kernel.

```
=> setenv bootargs 'console=ttymxc0,115200 earlycon root=/dev/mmcblk1p2 ro rootwait ...'
```

An illustrative shell transcript shows the distinction:

```
[root@pa-mini:~]# mount | head -1
/dev/mmcblk1p2 on / type ext4 (ro,relatime,...)

[root@pa-mini:~]# touch /etc/test
touch: /etc/test: Read-only file system

[root@pa-mini:~]# touch /var/log/test
[root@pa-mini:~]# ls /var/log/test
/var/log/test                            ← writable, in tmpfs
```

This output illustrates the intended write boundary: `/` rejects ordinary writes and the tmpfs paths accept disposable state. It does not establish power-loss resilience for the complete system.

## 35B.4  Pattern B, overlayfs

For changes that need to persist, this example overlays `/etc/`, `/var/`, and `/home/` on the read-only rootfs. A separate eMMC partition holds the upper layer.

### Partition layout

> **Storage safety:** Before any command that names /dev/sdX, run lsblk -o NAME,SIZE,MODEL,TRAN,TYPE,MOUNTPOINTS.
> Verify the removable card by size and model, unmount its partitions, and stop if the path is not the target card. Writing the wrong /dev node can destroy the host disk.


```
/dev/mmcblk1p1   FAT  boot files (zImage, dtb, optional)
/dev/mmcblk1p2   ext4 rootfs (RO, ~200 MB)
/dev/mmcblk1p3   ext4 overlay upper + data (RW, ~500 MB)
```

These names describe an example target layout, not disks to format on the host. Provisioning must identify the actual medium and separate image installation from the runtime mounting policy.

### Initial population

The installed base contains the rootfs and its mount points. The persistent partition contains an upper/work directory pair for each overlaid tree: `upper-etc` with `work-etc`, and equivalent pairs for `var` and `home`. Each work directory starts empty and shares a filesystem with its upper directory. Data kept outside the overlay has its own retention policy.

### Boot-time overlay setup

The overlay must exist before services start using the affected paths. An initramfs can establish those mounts before handing control to the real rootfs. A late overlay risks hiding files that a service has already opened.

The following `/init` fragment illustrates that handoff. It assumes the layout and directories described above. A production implementation also needs checked mount results, a recovery branch and device discovery appropriate to the actual board:

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

# Move the virtual filesystems into the new root.
mkdir -p /merged-root/proc /merged-root/sys /merged-root/dev
mount --move /proc /merged-root/proc
mount --move /sys  /merged-root/sys
mount --move /dev  /merged-root/dev

# Exec the real init
exec switch_root /merged-root /sbin/init
```

That `/init` is small but does the whole dance: mount RO rootfs, mount overlay storage, overlay-mount the writable subdirs, move `/proc` `/sys` `/dev`, switch root, exec real init.

A simpler approach (no initramfs) that works for some setups: a small `S00-overlay` script in `/etc/init.d/` that runs *before* `S01-mountall` (BusyBox runs them alphabetically). But mounting overlay over a partial filesystem is fragile. Initramfs is cleaner.

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

<span id="b-5-power-cycle-test"></span>
## 35B.5  Power-loss failure boundaries

Imagine the product updating its network settings when power disappears. The base image may still be usable, but an incomplete setting in the upper layer can hide its default. Recovery therefore needs more than a read-only mount.

| State | Design responsibility |
|---|---|
| Base image | Keep runtime changes out of the shipped system and retain a recovery path if the image cannot be read. |
| Tmpfs state | Treat its contents as disposable and recreate them during startup. |
| Persistent upper layer | Define application commit boundaries and a response to incomplete or unreadable state. |
| Storage device | Qualify the actual medium and power behavior. Separate partitions are not independent physical devices. |

There is no universal "last two seconds" loss window or failure percentage. Durability depends on the application, filesystem and storage stack. Synchronization must be explicit when persistence matters, with errors handled rather than ignored. Overlayfs does not make several application writes one transaction. Its [durability documentation](https://www.kernel.org/doc/html/latest/filesystems/overlayfs.html#durability-and-copy-up) explains that boundary.

Even `ro` needs context: ext4 can replay its journal during a read-only mount. Suppressing replay is not a general repair strategy for an inconsistent filesystem. See the [ext4 mount documentation](https://docs.kernel.org/admin-guide/ext4.html).

Power-loss qualification belongs to a controlled hardware validation plan, not a required reading exercise. This chapter provides no measured MINI power-cut results.

## 35B.6  Factory reset

With Pattern B, an empty upper layer exposes the base defaults again. That makes reset possible without reflashing the base image, but deciding what to discard is a product responsibility.

User settings may be disposable. Device identity, credentials, calibration and retained records may not be. Keep those lifetimes separate instead of putting everything into one erasable layer.

A recovery environment can prepare replacement upper/work directories while the overlay is unmounted. Deleting backing files under a live overlay is not valid: the kernel documents [undefined behavior for such changes](https://www.kernel.org/doc/html/latest/filesystems/overlayfs.html#changes-to-underlying-filesystems).

The reset design also needs a recoverable state if power disappears halfway through, and a path that works when the old upper layer cannot be mounted. A button gesture requests this policy. It does not, by itself, implement it or promise a fixed reset time.

<span id="b-7-lab"></span>
## 35B.7  Key Notes

- An immutable rootfs separates the shipped system from changing data. Read-only mounting reduces exposure to interrupted writes to that filesystem, but does not make the storage device or the entire product immune to power loss.
- Tmpfs gives disposable writable state at the cost of RAM. A persistent data partition or overlay retains changes, so its consistency, capacity and wear remain part of the design.
- Overlayfs combines a lower filesystem with an upper layer and work directory. The work and upper directories must share a filesystem, and the apparent merged tree can hide which layer owns a change.
- Factory reset is a data-lifecycle decision: disposable settings may be cleared while device identity, credentials and records may need to survive.
- Power-loss resilience requires evidence for the actual hardware, filesystem and application write pattern. A fixed number of restarts is not a universal durability guarantee.

## 35B.8  Pitfalls

- **`/etc/resolv.conf` and `/etc/adjtime`.** Both written at runtime in default Ubuntu/Debian setups. Either symlink them to `/run/` (tmpfs) or use overlay. If they end up trying to write to a RO mount, things like DHCP and NTP silently misbehave.
- **systemd's `/etc/machine-id`.** Generated on first boot, written to `/etc/`. On RO root, systemd may regenerate it every boot, breaking journal continuity. Fix: pre-generate at flash time.
- **Forgetting `ro` in `bootargs`.** Without `ro` in `bootargs` the whole scheme is defeated. Verify with `mount | head -1` after boot.
- **Overlay `workdir` must be on the same filesystem as `upperdir`.** Different filesystems for `workdir` and `upperdir` is an immediate mount failure.
- **Tmpfs filling up.** `/var/log` on tmpfs without log rotation, plus a chatty daemon, eats your RAM. Set `size=` explicitly and use `logrotate` (or just `> /var/log/messages` from cron).
- **Apps writing to `/etc/` expecting persistence.** If your app does `fopen("/etc/myapp.conf", "w")` to save settings, with Pattern A those settings are lost on reboot. Either use Pattern B (overlay) or move the writable file to `/data/` (a real persistent partition).
- **`switch_root` missing.** The initramfs must include a `switch_root` applet, usually from BusyBox. Without it, the overlay setup works but cannot hand off to the real rootfs.

## 35B.9  Going deeper

- **`Documentation/filesystems/overlayfs.rst`** in the kernel tree, the canonical reference.
- **`man 8 mount.overlay`**: overlay mount options in depth.
- **`erofs`**: Enhanced Read-Only File System, an alternative to ext4-RO with better compression. Used in modern Android.
- **`squashfs`**: another RO filesystem, slower but more compact than erofs. Common on initramfs images.
- **`A/B partition schemes`**: pair this chapter with Ch 63 (Field updates). Two RO rootfs partitions, switch atomically on update.

> Next chapter: **Chapter 35H: Rootfs security basics.** A read-only rootfs helps reliability. Before containers or release images, we remove the development shortcuts that should not ship.
