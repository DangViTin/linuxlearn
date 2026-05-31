---
chapter: 32
title: /proc, /sys, devtmpfs
part: V — Root filesystem & user space
estimated_pages: 18
status: draft
---

# Chapter 32 — /proc, /sys, devtmpfs

> **What:** the three virtual filesystems through which user space sees and pokes the kernel — `procfs` (process & system info), `sysfs` (the modern device model), and `devtmpfs` (device nodes). Each is RAM-backed and populated by the kernel.
> **Why:** every later chapter pokes `/proc` or `/sys` somewhere — to read a sensor, to set a GPIO, to inspect a driver. Knowing which virtual filesystem holds what is what makes the difference between following a tutorial and debugging an unfamiliar problem.
> **Focus:** **the file-as-interface pattern.** In Unix everything is a file; the kernel takes that literally. `cat /proc/cpuinfo` reads CPU info; `echo 1 > /sys/class/leds/led0/brightness` turns on an LED; `cat /proc/interrupts` shows IRQ counts. Once you know this idiom, a lot of debugging needs no code.

## 32.1  Three virtual filesystems, three jobs

| Filesystem | Mount point | Source of content | Best at |
|------------|-------------|-------------------|---------|
| **procfs** | `/proc` | Process info + miscellaneous kernel data | Per-process state; legacy kernel knobs |
| **sysfs** | `/sys` | The kernel's device model (drivers, buses, devices) | Modern device introspection and control |
| **devtmpfs** | `/dev` | Device nodes auto-created by the kernel | Actually reading from / writing to devices |

All three are **virtual** — RAM-backed, no physical storage. They are populated by the kernel on the fly. Every entry corresponds to a kernel data structure. Writing to a file usually calls a kernel callback that parses the bytes.

## 32.2  procfs — the process FS that grew

`/proc` was originally a way for `ps` to list processes. Every running process gets a directory named for its PID. That part is unchanged in 30 years:

```
[root@pa-mini:~]# ls /proc/
1   116  2    33   45   685  9          consoles    cpuinfo   ...
```

Numbered directories are processes. `1` is `init`; `2` is `kthreadd`; later entries are everything else.

Inside a process directory:

```
[root@pa-mini:~]# ls /proc/1/
cmdline      comm         cwd          environ      exe          fd/
maps         mem          mountinfo    mounts       net/         oom_score
root         stat         statm        status       task/        wchan
```

| File | Contents |
|------|----------|
| `cmdline` | The args the process was exec'd with, null-separated. `cat /proc/1/cmdline` → `/sbin/init` |
| `comm` | Just the program's short name |
| `exe` | Symlink to the binary on disk: `ls -l /proc/1/exe` → `/sbin/init` |
| `cwd` | Symlink to current working directory |
| `root` | Symlink to the process's root (changes if `chroot`'d) |
| `environ` | Environment variables, null-separated |
| `fd/` | Directory of symlinks for each open file descriptor |
| `maps` | The process's memory map — every region with addresses and permissions |
| `mem` | The process's address space, as a file (mostly inaccessible without `ptrace`) |
| `status` | Human-readable summary: state, uid, memory, signals |
| `stat` | Machine-readable: 50+ fields used by tools like `top` |

Useful command-line idioms:

```sh
# How many open file descriptors does init have?
[root@pa-mini:~]# ls /proc/1/fd | wc -l
8

# What environment did init inherit from the kernel?
[root@pa-mini:~]# cat /proc/1/environ | tr '\0' '\n'
HOME=/
TERM=linux

# What's the memory layout of busybox?
[root@pa-mini:~]# cat /proc/$(pidof busybox)/maps | head
00010000-00050000 r-xp 00000000 00:00 1234567 /bin/busybox
0005f000-00060000 r--p 0003f000 00:00 1234567 /bin/busybox
00060000-00061000 rw-p 00040000 00:00 1234567 /bin/busybox
...
```

The non-PID entries in `/proc/` are global system info:

| Path | Contents |
|------|----------|
| `/proc/cpuinfo` | CPU model, features, BogoMIPS |
| `/proc/meminfo` | Total/free/buffers/cached memory |
| `/proc/loadavg` | Load averages: 1-min, 5-min, 15-min |
| `/proc/uptime` | System uptime in seconds (since boot) |
| `/proc/version` | The full `linux_banner` string |
| `/proc/cmdline` | The bootargs the kernel received (echo of what `chosen.bootargs` from DT carried) |
| `/proc/interrupts` | Per-IRQ counts. Useful for `is my IRQ firing?` |
| `/proc/iomem` | The physical memory map: kernel code, kernel data, peripherals |
| `/proc/devices` | Registered character and block major numbers |
| `/proc/filesystems` | Filesystems the kernel knows about (loadable + built-in) |
| `/proc/mounts` | Live mount table (newer than `/etc/mtab`) |
| `/proc/modules` | Currently loaded kernel modules |
| `/proc/sys/` | A whole subtree of *tunable* kernel parameters (more below) |
| `/proc/<tid>/` | Per-thread variants (a thread is a task whose pid != tgid) |

`/proc/sys/` is special — most files there are **writable** and tweak kernel behavior live:

```sh
# Read the current value
[root@pa-mini:~]# cat /proc/sys/kernel/hostname
pa-mini

# Change it
[root@pa-mini:~]# echo new-hostname > /proc/sys/kernel/hostname

# Lots of these. The full set is huge.
[root@pa-mini:~]# ls /proc/sys/
abi/  debug/  dev/  fs/  kernel/  net/  user/  vm/
```

Most production code uses `sysctl` (a wrapper) instead of writing to `/proc/sys/` directly:

```sh
[root@pa-mini:~]# sysctl -a | head
kernel.hostname = pa-mini
kernel.osrelease = 6.6.0
...
[root@pa-mini:~]# sysctl -w net.ipv4.ip_forward=1
```

The values are the same; `sysctl` adds value-validation and persistence support via `/etc/sysctl.conf`.

## 32.3  sysfs — the modern device model

`/sys` is newer (kernel 2.5/2.6, ~2003). It exposes the **kernel device model** — every `struct device`, `struct device_driver`, `struct bus_type`, `struct class`, etc. — as a directory tree.

Top-level layout:

```
[root@pa-mini:~]# ls /sys/
block/   bus/      class/    dev/    devices/   firmware/   fs/   hypervisor/
kernel/  module/   power/
```

Each is a different *view* of the same underlying graph:

- **`/sys/devices/`** — the master tree. Every device the kernel knows about lives here exactly once, organized by physical topology (which bus is on which controller is on which CPU complex). Hierarchical and verbose.
- **`/sys/bus/`** — devices grouped by *bus type* (`i2c`, `spi`, `platform`, `usb`, …). Each bus lists its devices and the drivers bound to them.
- **`/sys/class/`** — devices grouped by *function* (`leds`, `gpio`, `tty`, `net`, …). Best for "I want all the LEDs" or "all the network interfaces."
- **`/sys/block/`** — block devices (SD card, eMMC, USB sticks).
- **`/sys/dev/`** — devices indexed by `major:minor` number.
- **`/sys/module/`** — every loaded kernel module, with its parameters.
- **`/sys/kernel/`** — kernel-internal stuff (security, slab, debug).
- **`/sys/firmware/`** — info from firmware (the DT lives here as `/sys/firmware/devicetree/base/`).

### Walking a device

The on-chip ADC (Chapter 49 will be all about this; here is a teaser):

```
[root@pa-mini:~]# ls /sys/bus/iio/devices/
iio:device0

[root@pa-mini:~]# ls /sys/bus/iio/devices/iio:device0/
dev               in_voltage1_raw    name        of_node        scan_elements
in_voltage0_raw   in_voltage_scale   power       subsystem      uevent

[root@pa-mini:~]# cat /sys/bus/iio/devices/iio:device0/name
2198000.adc

[root@pa-mini:~]# cat /sys/bus/iio/devices/iio:device0/in_voltage_scale
0.806884765

[root@pa-mini:~]# cat /sys/bus/iio/devices/iio:device0/in_voltage0_raw
1453
```

That's the ADC reading channel 0 as a raw 12-bit value, with a known scale factor to convert to volts: `1453 × 0.806884765 / 1000 = 1.172 V`. No code; one `cat`.

### Controlling a device

GPIO LEDs:

```
[root@pa-mini:~]# ls /sys/class/leds/
led0  mmc0::

[root@pa-mini:~]# cat /sys/class/leds/led0/brightness
0
[root@pa-mini:~]# cat /sys/class/leds/led0/max_brightness
1
[root@pa-mini:~]# echo 1 > /sys/class/leds/led0/brightness
# LED lights up
[root@pa-mini:~]# echo 0 > /sys/class/leds/led0/brightness
# LED turns off
```

Other useful patterns to look up:

```sh
[root@pa-mini:~]# ls /sys/class/net/
eth0  lo

[root@pa-mini:~]# cat /sys/class/net/eth0/address
00:04:9f:01:30:ad

[root@pa-mini:~]# cat /sys/class/net/eth0/operstate
up

[root@pa-mini:~]# echo down > /sys/class/net/eth0/operstate
# eth0 brought administratively down
```

### Device-tree introspection

The currently-active DT lives at `/sys/firmware/devicetree/base/`:

```
[root@pa-mini:~]# ls /sys/firmware/devicetree/base/
aliases/             chosen/        cpus/        firmware/    interrupt-controller@a01000/
clocks/              compatible     model        soc/         ...

[root@pa-mini:~]# cat /sys/firmware/devicetree/base/model
Freescale i.MX6 ULL 14x14 EVK Board

[root@pa-mini:~]# cat /sys/firmware/devicetree/base/soc/aips-bus@2000000/serial@2020000/compatible
fsl,imx6ul-uartfsl,imx6q-uartfsl,imx21-uart
```

Each DT property is a file; each node is a directory. Mirrors the DT structure exactly.

## 32.4  devtmpfs — where device nodes live

Historically, `/dev/` was a regular directory populated at install time with `mknod` calls. Every device that *might* exist had a static node. Modern Linux replaces this with **`devtmpfs`** — a tmpfs that the kernel auto-populates whenever a device probes.

Enable in kernel `.config`:

```
CONFIG_DEVTMPFS=y
CONFIG_DEVTMPFS_MOUNT=y
```

With both set, the kernel mounts devtmpfs at `/dev` early in boot, before init runs. Every `device_create()` or platform-device probe with a `class` adds a node.

What you see:

```
[root@pa-mini:~]# ls /dev/
console     mtd0          mtdblock0   ram0          ttymxc0     ttymxc4
fb0         mtd0ro        null        random        ttymxc1     urandom
i2c-0       mtd1          ptmx        rtc0          ttymxc2     vcs
i2c-1       mtd1ro        pts/        snd/          ttymxc3     vcs1
[root@pa-mini:~]# ls -l /dev/console
crw------- 1 root root 5, 1 Jan 22 12:34 /dev/console
```

The `c` at the start of the permissions means **character device**. `5, 1` is the major and minor number. The kernel routes any open/read/write on this file to the driver registered with that major number.

When a USB device gets plugged in, devtmpfs *immediately* gains entries for it:

```
# Before plugging in a USB stick
[root@pa-mini:~]# ls /dev/sd* 2>/dev/null
[root@pa-mini:~]#
# (Plug in USB stick)
[    142.512345] usb 1-1: new high-speed USB device number 5
[    142.789012] sd 0:0:0:0: [sda] 30277632 512-byte logical blocks
[    142.812345] sda: sda1
[root@pa-mini:~]# ls /dev/sd*
/dev/sda  /dev/sda1
```

No user-space help needed. The kernel did all of it.

### What devtmpfs *doesn't* do

It creates device *nodes*, not the metadata around them. For things like:

- Setting permissions per-device (e.g., `/dev/i2c-1` should be group-readable by users in `dialout`)
- Creating symlinks (e.g., `/dev/serial/by-id/usb-FTDI...`)
- Running scripts when a device appears (e.g., auto-mount a USB stick)

…you need either **`udev`** (full-featured but heavy) or **`mdev`** (BusyBox's tiny alternative).

### `mdev` — BusyBox's user-space helper

We already wired this up in Chapter 31's `rcS`:

```sh
echo /sbin/mdev > /proc/sys/kernel/hotplug
/sbin/mdev -s
```

The first line registers mdev as the kernel's hotplug agent: whenever a device appears or disappears, the kernel `fork`+`exec`s `/sbin/mdev` with environment variables describing the event. mdev then applies rules from `/etc/mdev.conf`.

The second line says "scan `/sys` for everything that already exists and create any missing nodes" — useful right after boot for devices that were enumerated before mdev was wired up.

A minimal `/etc/mdev.conf`:

```
# pattern              user:group  mode  command

# Default: root:root, 0660.

# Make audio nodes group-writable so members of "audio" can play sound.
snd/[!c].*             root:audio  0660

# I²C buses readable by "i2c" group.
i2c-[0-9]+             root:i2c    0660

# Run a script when an SD card appears or vanishes.
mmcblk[0-9]p[0-9]      root:root   0660  @/etc/mdev/auto-mount.sh
```

The `@` prefix runs the command *after* the node is created (`$` runs *before*; `*` both).

## 32.5  Lab

1. **Tour `/proc`.** Run `cat /proc/cpuinfo`, `/proc/meminfo`, `/proc/version`, `/proc/cmdline`, `/proc/interrupts`. Match each output line to what you know about the hardware.
2. **Tour `/sys/class/`.** `ls` each subdirectory; identify which one corresponds to your LED, your network interface, your I²C buses.
3. **Manually toggle the LED via sysfs.** `echo 1 > /sys/class/leds/led0/brightness` should turn the LED on.
4. **Read the ADC.** `cat /sys/bus/iio/devices/iio:device0/in_voltage0_raw` — get a raw value. Apply the scale; compute volts. Touch the ADC pin and re-read; see it change.
5. **Find the device tree.** Walk `/sys/firmware/devicetree/base/` and find the I²C controller's `compatible` string. Verify it matches what's in `imx6ull.dtsi`.
6. **Make mdev set audio permissions.** Add `snd/[!c].*` to `/etc/mdev.conf` (with a group that exists). Reboot. `ls -l /dev/snd/*` should show the new permissions.

## 32.6  Pitfalls

- **`/proc/` writes that don't take effect.** Some `/proc/sys/` entries are read-only on certain configurations. Symptom: `echo 1 > /proc/sys/...` succeeds, but `cat` still shows the old value. Use `sysctl -w` and check the return code.
- **`sysfs` attribute file write that hangs.** If a `store` callback in the driver does something blocking (e.g., reset the chip), the `echo` shell command appears to hang. It's not hung — it's waiting for the kernel callback to complete. Normal.
- **devtmpfs not mounted.** Without `CONFIG_DEVTMPFS_MOUNT=y`, the kernel doesn't auto-mount at boot. Either set that config or mount manually in early `rcS`. Otherwise `/dev/console` may not exist and you get the dreaded "Warning: unable to open an initial console" message.
- **Confusing `/proc/<pid>/mem` with `/proc/<pid>/maps`.** `maps` is the *layout* (text, addresses, permissions); `mem` is the raw bytes. Reading `mem` without `ptrace` is usually denied.
- **`/proc/sys/kernel/hotplug` overwritten.** If you `echo /sbin/mdev > /proc/sys/kernel/hotplug` and later run something that sets it to something else (rare but possible), mdev stops working. Check the file's value at runtime.
- **Forgetting that `/sys` paths are case-sensitive.** `/sys/class/Leds/` won't work; it's `leds`.
- **Sysfs path stability assumptions.** Don't hard-code paths under `/sys/devices/`; they rename across kernel versions. Use `/sys/class/...` in scripts.

## 32.7  Going deeper

- **`Documentation/filesystems/proc.rst`** — comprehensive procfs reference.
- **`Documentation/filesystems/sysfs.rst`** and `Documentation/driver-api/driver-model/`.
- **`Documentation/admin-guide/sysctl/`** — all the `/proc/sys/` knobs.
- **`man 5 proc`** — concise but complete procfs guide.
- **`man udev`** and **`man udevadm`** — when you outgrow mdev. Most embedded systems can stick with mdev.
- **The `iio_utils` user-space tools** — for richer ADC/sensor interaction than `cat`/`echo`.

> Next chapter: **Chapter 33 — Init systems.** With sysfs/proc/devtmpfs understood, we look at PID 1's job in detail and compare BusyBox init, sysvinit, and systemd.
