---
chapter: 35A
title: Ubuntu-base rootfs as a peer to BusyBox/Buildroot
part: V — Root filesystem & user space (supplementary v1.1)
estimated_pages: 16
status: draft
---

# Chapter 35A — Ubuntu-base rootfs as a peer to BusyBox/Buildroot
**sysfs** - a kernel-generated filesystem under /sys that exposes devices, drivers, and attributes.

> **What:** an Ubuntu rootfs on the i.MX6ULL. Ubuntu-the-distro with GNOME is too heavy. We use **Ubuntu-base** instead, the same Debian-family userland your laptop has, in a 80 MB tarball that runs `apt` and `bash` natively. You unpack it, `chroot` into it via `qemu-user-static`, install packages from the host's network, then NFS-boot the target into it.
> **NFS** - Network File System, which lets the target mount a host directory over Ethernet during development.
> **rootfs** - root filesystem, the directory tree mounted at / that contains /bin, /etc, /dev, and libraries.
>
> **Why:** for projects where the developer's familiarity matters more than image footprint, Ubuntu-base wins. Glibc, full coreutils, systemd, an actual `bash` — all present, in exchange for ~80 MB on disk and ~30 MB RAM at idle vs. BusyBox's < 5 MB / < 10 MB.
>
> **Focus:** the **`qemu-user-static` + `chroot` trick** — installing armhf packages from x86_64 host into the armhf rootfs by transparently running ARM binaries on the host CPU through QEMU emulation. Apt-get doesn't notice and the workflow works.


## 35A.1  When this is the right answer

| Reason | Buildroot wins | Ubuntu-base wins |
|--------|:---:|:---:|
| Smallest possible image | ✓ | |
| Fastest boot (<2 s) | ✓ | |
| Compatible with team's `apt-get` muscle memory | | ✓ |
| Easy to `apt install foo` for a quick fix in the field | | ✓ |
| Reproducible byte-for-byte builds | ✓ | |
| Long-term security backports for free | | ✓ (Ubuntu LTS) |
| Lowest RAM | ✓ | |
| Best for prototypes / dev boards | | ✓ |
| Best for shipping products | ✓ (usually) | |

The headline feature is `apt install <anything>` — Ubuntu's ~100 000-package archive available, no recompilation. For early development this is hard to beat.

The headline cost is ~25× the disk and ~3× the RAM vs Buildroot. On i.MX6ULL with 512 MiB DRAM and an 8 GB eMMC, both are fine. On a 32 MiB device, only Buildroot fits.
**Buildroot** - a configuration-driven build system that produces a complete root filesystem and related images.

## 35A.2  Get the rootfs tarball

```sh
$ cd ~/imx6ull
$ wget http://cdimage.ubuntu.com/ubuntu-base/releases/22.04/release/ubuntu-base-22.04.5-base-armhf.tar.gz
$ mkdir ubuntu-rootfs
$ sudo tar -xzf ubuntu-base-22.04.5-base-armhf.tar.gz -C ubuntu-rootfs/
$ ls ubuntu-rootfs/
bin   dev  etc   home  lib    media  mnt  opt
proc  root  run   sbin  srv    sys    tmp  usr
var
```

That's already a minimal Ubuntu 22.04 LTS rootfs for ARM. Total size: ~80 MB. Use `20.04` or `24.04` if you prefer — same workflow.

Three release tracks Ubuntu publishes:

- **20.04 LTS** — supported through April 2025 (and ESM through 2030).
- **22.04 LTS** — supported through April 2027 (ESM 2032). Current LTS recommended for new work.
- **24.04 LTS** — supported through April 2029 (ESM 2034).

Pick the most-recent LTS unless something specific requires older.

## 35A.3  Install qemu-user-static on the host

The trick that makes the whole flow work:

```sh
$ sudo apt install qemu-user-static binfmt-support
$ ls /usr/bin/qemu-arm-static
/usr/bin/qemu-arm-static
```

`qemu-user-static` runs one ARM binary at a time on your x86_64 host. `binfmt-support` registers it with the kernel via `binfmt_misc`. When the kernel sees `exec` of an ARM ELF, it transparently invokes `qemu-arm-static` to run it.
**ELF** - Executable and Linkable Format, the standard Linux object and executable file format.

This means: inside the `chroot`, when you type `apt install nano`, `apt` is an ARM binary, `dpkg` is an ARM binary, every `.postinst` script's binary callouts are ARM — and they *all run on your x86_64 host* via QEMU emulation. The chroot doesn't know the difference. Neither do the binaries.

Copy the QEMU binary into the rootfs so the chroot has it:

```sh
$ sudo cp /usr/bin/qemu-arm-static ubuntu-rootfs/usr/bin/
```

## 35A.4  The mount-and-chroot script

Inspired by the PA workflow, but adapted. Save as `~/imx6ull/mount-ubuntu.sh`:

```sh
#!/bin/bash
set -e

ROOTFS=$HOME/imx6ull/ubuntu-rootfs

echo "Mounting host filesystems into $ROOTFS..."

sudo mount -t proc /proc      "$ROOTFS/proc"
sudo mount -t sysfs /sys      "$ROOTFS/sys"
sudo mount --bind /dev        "$ROOTFS/dev"
sudo mount --bind /dev/pts    "$ROOTFS/dev/pts"

# Copy host resolv.conf so DNS works in chroot
sudo cp /etc/resolv.conf "$ROOTFS/etc/resolv.conf"

# Drop into the rootfs
sudo chroot "$ROOTFS" /bin/bash
```

And the unmount counterpart `~/imx6ull/unmount-ubuntu.sh`:

```sh
#!/bin/bash
ROOTFS=$HOME/imx6ull/ubuntu-rootfs
echo "Unmounting..."
sudo umount "$ROOTFS/dev/pts" || true
sudo umount "$ROOTFS/dev"     || true
sudo umount "$ROOTFS/sys"     || true
sudo umount "$ROOTFS/proc"    || true
```

Make both executable:

```sh
$ chmod +x mount-ubuntu.sh unmount-ubuntu.sh
```

## 35A.5  Configure the rootfs from inside the chroot

```sh
$ ./mount-ubuntu.sh
# (host shell becomes ARM shell — transparently, via qemu-arm-static)

root@host:/# uname -m
armv7l                  # ← we are inside the chroot, claiming to be ARM
```

You are now inside a fake ARM machine. Whatever you run here runs on QEMU. Whatever you write to the filesystem is in the rootfs.

### Set up apt sources

The default `sources.list` in `ubuntu-base` is empty. Add the official Ubuntu ports archive (ports.ubuntu.com hosts the armhf packages):

```sh
root@host:/# cat > /etc/apt/sources.list <<'EOF'
deb http://ports.ubuntu.com/ubuntu-ports jammy main restricted universe multiverse
deb http://ports.ubuntu.com/ubuntu-ports jammy-updates main restricted universe multiverse
deb http://ports.ubuntu.com/ubuntu-ports jammy-security main restricted universe multiverse
EOF
```

(`jammy` is the codename for 22.04. Use `focal` for 20.04 or `noble` for 24.04.)

For users in China who find the official mirrors slow, the Tsinghua or USTC mirror is much faster:

```sh
deb http://mirrors.ustc.edu.cn/ubuntu-ports jammy main restricted universe multiverse
deb http://mirrors.ustc.edu.cn/ubuntu-ports jammy-updates main restricted universe multiverse
deb http://mirrors.ustc.edu.cn/ubuntu-ports jammy-security main restricted universe multiverse
```

### Install essential packages

> **Privilege boundary:** $ means normal user. # or sudo means root and can change host or target state.
> After a privileged command, verify the expected device, service, or file appears before continuing. Roll back by undoing the config change or stopping the service you just enabled.


```sh
root@host:/# apt update
root@host:/# apt install -y \
    sudo vim openssh-server kmod net-tools \
    ifupdown iputils-ping rsyslog less htop \
    language-pack-en-base
```

That's the minimum for: a non-root user (sudo), an editor, ssh in, kernel module loading, networking, ping, syslog. ~50 MB of additional packages.

For the curious, this is what runs:

1. `apt update` — downloads package metadata. Runs on QEMU. HTTP calls go to the host's network.
2. `apt install` — for each package: download `.deb`, dpkg-extract files into `/`, run pre/post-install scripts. The scripts themselves are ARM binaries running under QEMU.

### Set root password and create a user

```sh
root@host:/# passwd root
New password: <something>

root@host:/# adduser dev
# Creates /home/dev, sets password

root@host:/# usermod -aG sudo dev
```

### Set hostname

```sh
root@host:/# echo pa-mini > /etc/hostname
root@host:/# cat > /etc/hosts <<'EOF'
127.0.0.1   localhost
127.0.1.1   pa-mini
EOF
```

### Enable the serial console for systemd

Ubuntu uses systemd. We need a getty on `ttymxc0` for serial login:

```sh
root@host:/# systemctl enable serial-getty@ttymxc0.service
```

`systemctl` here just creates a symlink — it doesn't actually start anything (we're in a chroot). The symlink ensures the service is enabled on first boot of the target.

### Done — exit and unmount

```sh
root@host:/# exit
# (back to host x86_64 shell)
$ ./unmount-ubuntu.sh
```

## 35A.6  Boot it from NFS

Export `~/imx6ull/ubuntu-rootfs/` over NFS (same as Ch 31, different rootfs path). In U-Boot:
MCU bridge: Think of U-Boot like a much larger boot stub plus debug monitor: it initializes hardware, loads the next image, and gives you commands before Linux starts.
**U-Boot** - the bootloader that initializes enough hardware to load and start the Linux kernel.

```
=> setenv bootargs 'console=ttymxc0,115200 earlycon \
                    root=/dev/nfs nfsroot=192.168.7.1:/home/you/imx6ull/ubuntu-rootfs,vers=3,nolock,tcp \
                    ip=192.168.7.2:192.168.7.1:192.168.7.1:255.255.255.0::eth0:off \
                    rw rootwait'
=> run bootnet
```

After kernel boot:

```
[OK] Started Serial Getty on ttymxc0.

Ubuntu 22.04.5 LTS pa-mini ttymxc0

pa-mini login: dev
Password:
Welcome to Ubuntu 22.04.5 LTS (GNU/Linux 6.6.0 armv7l)
...

dev@pa-mini:~$ uname -a
Linux pa-mini 6.6.0 #1 SMP ... armv7l armv7l armv7l GNU/Linux

dev@pa-mini:~$ sudo apt install screen
[sudo] password for dev:
...

dev@pa-mini:~$ which python3
/usr/bin/python3

dev@pa-mini:~$ python3 -c 'print("hello from an ARM Ubuntu")'
hello from an ARM Ubuntu
```

A full Ubuntu shell. `apt install` works, `python3` is there, every command you're used to is there.

Boot time on i.MX6ULL: ~12-15 seconds from `bootz` to login prompt (vs ~3 s for BusyBox). Most of that is systemd's startup.

## 35A.7  Persistence — burning to eMMC

NFS-rooted Ubuntu is great for development but you eventually want it on the target's flash.

```sh
# On the host, pack the configured rootfs:
$ cd ubuntu-rootfs
$ sudo tar -czf ../ubuntu-rootfs.tar.gz .
$ cd ..

# Format an SD card or eMMC partition (assume /dev/sdb1 is the rootfs partition):
$ sudo mkfs.ext4 /dev/sdb1
$ sudo mount /dev/sdb1 /mnt/rootfs
$ sudo tar -xzf ubuntu-rootfs.tar.gz -C /mnt/rootfs/
$ sudo umount /mnt/rootfs

# Configure U-Boot to boot from eMMC:
# bootargs: root=/dev/mmcblk1p2 rw rootwait ...
```

The same rootfs works whether served over NFS or mounted from eMMC.

## 35A.8  Comparison: BusyBox vs Buildroot vs Ubuntu-base

| | BusyBox by hand (Ch 31) | Buildroot (Ch 35) | Ubuntu-base (Ch 35A) |
|---|---|---|---|
| Initial rootfs size | ~5 MB | ~10 MB | ~80 MB |
| RAM at idle | ~10 MB | ~15 MB | ~30 MB |
| Boot to login | < 3 s | < 5 s | ~12 s |
| Customisation method | Edit `/etc/` directly | Overlay + defconfig | `apt install` |
| New package | Cross-compile + copy | menuconfig + rebuild | `apt install` |
| Reproducibility | Notes | Defconfig | Snapshot of `apt` state |
| Long-term security | You backport | Buildroot package version | Ubuntu LTS team |
| Best for | Learning, tiny | Most embedded products | Dev boards, prototypes |

For our continuing work in this book, **Buildroot** is the default. **Ubuntu-base** is a great option when (a) you're spinning up a new dev board, (b) you need a weird package that's in Ubuntu but not Buildroot, or (c) you'd rather pay 70 MB and 10 seconds of boot for the comfort of `apt install`.

## 35A.9  Lab

1. **Build the Ubuntu rootfs.** Follow §35A.2 through §35A.6. Get to a login prompt over NFS.
2. **`apt install` something useful.** Try `htop`, then `python3-pip`, then `nodejs`. Verify each runs.
3. **Time the boot.** Compare BusyBox rootfs boot time vs Ubuntu-base.
4. **Try `systemd-analyze`.** On the Ubuntu rootfs, `systemd-analyze blame` shows which services took longest at boot. Identify the top three.
5. **Disable a heavyweight service.** Pick one (e.g., `snapd` if present, `unattended-upgrades`). `sudo systemctl disable <name>`. Reboot. compare boot times.
6. **Build a packaged image.** Tar the rootfs, write to a real partition, change `bootargs` to mount from disk, verify the system boots without the host. This is what you'd ship.

## 35A.10  Pitfalls

- **`qemu-arm-static` not copied into the rootfs.** Symptom: `chroot` fails with `Exec format error` because the kernel doesn't know how to run an ARM binary. Fix: copy `/usr/bin/qemu-arm-static` into `ubuntu-rootfs/usr/bin/`.
- **`binfmt-support` not installed on the host.** Same symptom. Fix: `apt install binfmt-support` and restart the service.
- **Forgetting `/etc/resolv.conf`.** Inside the chroot, `apt update` will fail with "Temporary failure resolving 'ports.ubuntu.com'". Fix: copy host's `/etc/resolv.conf` into the rootfs before `chroot`.
- **`mount --bind /dev` without `--bind /dev/pts`.** Symptom: `passwd` and other terminal-needing commands fail in the chroot. Fix: bind both.
- **Forgetting to unmount.** If you reboot the host without `unmount-ubuntu.sh`, the host's `/dev/pts/` is still bind-mounted under the rootfs. Later operations may misbehave. Always pair mount and unmount.
- **Choosing the wrong armhf.** Ubuntu publishes both `armhf` (32-bit, hard-float) and `arm64` (64-bit). i.MX6ULL is `armhf`. Downloading `arm64` and trying to run it on a 32-bit i.MX6ULL is a slow, confusing failure.
- **Mirror URL with HTTPS but `apt` can't validate certs.** Older Ubuntu base images may not have `ca-certificates` installed. Use `http://` mirrors initially, install `ca-certificates` first, then switch to `https://`.
- **`systemctl enable` in chroot is harmless but `systemctl start` is not.** Inside a chroot, `start` may try to manipulate cgroups or dbus and fail. Only use `enable` / `disable` for one-shot config in the chroot.

## 35A.11  Going deeper

- **`debootstrap`** — Debian's equivalent of `ubuntu-base.tar.gz`. Builds a fresh Debian rootfs from package archives. More flexible. more complex.
- **`multistrap`** — debootstrap with support for non-Debian package sources. Used by Yocto when assembling Debian-based images.
**Yocto** - a metadata-driven build system for producing custom Linux distributions.
- **`schroot`** — manage chroot environments without writing your own mount scripts.
- **`Ubuntu Core`** — Ubuntu's official "embedded" variant. Uses snaps instead of apt. immutable rootfs. Different philosophy from this chapter. worth knowing about.
- **`Yocto-meta-ubuntu`** layer — combines Yocto-style builds with Ubuntu's package archive.

> Next chapter: **Chapter 35B — Read-only rootfs + overlayfs.** Whichever rootfs you chose, when you ship to the field, you want it mounted read-only. Here is how.
