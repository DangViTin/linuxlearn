---
chapter: 3
title: Host environment setup
part: I — Foundations
estimated_pages: 16
status: draft
---

# Chapter 3 — Host environment setup

> **What:** a Linux development host that can cross-compile for ARMv7-A, serve files over TFTP and NFS, talk to the board over serial and USB-OTG, and recover a bricked board.
> **Why:** for the next sixty chapters, the host is your lever. A flaky host is the single most common time-sink in embedded Linux work — far more than buggy code.
> **Focus:** the iteration loop. By the end of this chapter, "change a source file, see the change run on the board" must take under thirty seconds. If it takes longer, you will quietly stop iterating, and you will stop learning.

## 3.1  Choosing the host

The book assumes **native Ubuntu 22.04 LTS** running on bare-metal hardware. Other options work but cost you time in ways that vary from "annoying" to "showstopper":

| Host | Status | Notes |
|------|--------|-------|
| Native Ubuntu 22.04 LTS | **Recommended, tested** | Everything in this book was tested here. |
| Native Debian 12 (bookworm) | Works | Some package names differ; substitute as needed. |
| Native Fedora 39+ | Works | Package names and `dnf` syntax differ; we don't translate every command. |
| WSL2 on Windows 11 | Works *with caveats* | USB-OTG (`uuu`) requires `usbipd-win`; serial passthrough is fiddly; NFS server is awkward. |
| Linux VM (VirtualBox/VMware) | Works | Slow builds; USB passthrough is fragile. |
| macOS + Docker | Don't | Cross-compile inside Docker works, but USB-OTG and serial do not pass through cleanly. |

If you are running Windows or macOS, the fastest path is to put Ubuntu on a USB-3 NVMe enclosure and boot from it. Dual-booting your daily-driver machine is the obvious alternative; the only thing that matters is that, at the end, when you plug the board into a USB port, `lsusb` on your host sees it without ceremony.

The remainder of this book assumes Ubuntu 22.04. Commands shown with the `$` prompt run as your normal user; commands with `#` run as root via `sudo`.

## 3.2  Workspace layout

Create the workspace before installing anything. The layout you set now will be referred to by every chapter:

```sh
$ mkdir -p ~/imx6ull/{src,build,boot,rootfs,scripts,notes}
$ cd ~/imx6ull
$ tree -L 1
.
├── boot       # bootable artefacts staged here, then dd'd to SD
├── build      # all out-of-tree build outputs (kernel, U-Boot, BusyBox)
├── notes      # your lab journal, per-chapter
├── rootfs     # exported over NFS to the target
├── scripts    # helpers; shared between chapters
└── src        # upstream sources: linux, u-boot, busybox, your bare-metal code
```

Two opinions about this layout, both load-bearing for the rest of the book:

1. **Sources are read-only.** We never edit inside `src/u-boot/`. We patch and build out-of-tree into `build/u-boot/`. This is the only way to keep a clean diff against upstream and keep cross-chapter reproducibility honest.
2. **`rootfs/` is the live NFS root.** Anything you copy into `rootfs/` is visible to the board after the next boot, with no flashing step. This is the central iteration trick of embedded Linux.

## 3.3  Host packages

Install in one shot:

```sh
$ sudo apt update
$ sudo apt install -y \
    build-essential bison flex libssl-dev libncurses-dev \
    bc kmod cpio rsync wget curl git unzip xz-utils \
    device-tree-compiler u-boot-tools \
    nfs-kernel-server tftpd-hpa \
    minicom picocom \
    qemu-user-static binfmt-support \
    gdb-multiarch \
    pkg-config libusb-1.0-0-dev libftdi1-dev \
    libgmp-dev libmpfr-dev libmpc-dev libisl-dev \
    fakeroot dosfstools mtools parted
```

What each pulls in, briefly:

- **`build-essential`, `bison`, `flex`, `libssl-dev`, `libncurses-dev`** — what the kernel and U-Boot need to build. The first surprise for many people is that the *kernel* uses OpenSSL during build (for module signing).
- **`bc`** — really. The kernel build literally invokes `bc` for arithmetic.
- **`device-tree-compiler`** — `dtc`. You'll use this in every chapter from Ch 27 on.
- **`u-boot-tools`** — provides `mkimage`, `mkenvimage`, `dumpimage`, `mkeficapsule`.
- **`nfs-kernel-server`, `tftpd-hpa`** — server side of the network-boot loop.
- **`minicom`, `picocom`** — serial terminals. We'll use `picocom`; `minicom` is here for users who prefer it.
- **`qemu-user-static`, `binfmt-support`** — lets you run ARM binaries on the host transparently. Useful when staging a rootfs with `chroot`.
- **`gdb-multiarch`** — one `gdb` that speaks every architecture; we'll point it at ARM ELFs.
- **`libusb-1.0-0-dev`, `libftdi1-dev`** — needed by `imx_usb_loader` and OpenOCD when we build them from source.
- **`fakeroot`, `dosfstools`, `mtools`, `parted`** — manipulate SD card images without needing root.

If `apt` complains about any package on your distribution, search for the closest equivalent and note the substitution in your journal.

## 3.4  The cross toolchain

We need a toolchain that runs on `x86_64-linux-gnu` (the host) and produces code for `arm-linux-gnueabihf` (the target). Two reasonable sources for now; we build one ourselves in Ch 60.

### Option A — Ubuntu package

```sh
$ sudo apt install -y gcc-arm-linux-gnueabihf
$ arm-linux-gnueabihf-gcc --version
arm-linux-gnueabihf-gcc (Ubuntu 11.4.0-1ubuntu1~22.04) 11.4.0
```

The cleanest choice for getting started. Ships with a sysroot. Limitation: locked to whatever GCC version Ubuntu shipped.

### Option B — ARM/Linaro pre-built

Download the latest `arm-gnu-toolchain-*-x86_64-arm-none-linux-gnueabihf.tar.xz` from <https://developer.arm.com/downloads/-/arm-gnu-toolchain-downloads> and untar to `/opt/`. Then:

```sh
$ export PATH=/opt/arm-gnu-toolchain-13.3.rel1-x86_64-arm-none-linux-gnueabihf/bin:$PATH
$ arm-none-linux-gnueabihf-gcc --version
```

Pros: newer GCC, often better optimization. Cons: triplet is `arm-none-linux-gnueabihf`, not `arm-linux-gnueabihf`. We accommodate both throughout the book.

### Decoding the triplet

`arm-linux-gnueabihf` looks alphabet-soupy; it is not.

- `arm` — target CPU family
- `linux` — target OS (vs `none` for bare metal, `eabi` for bare-metal-ish without OS)
- `gnu` — userland convention (vs `musl`, `uclibc`)
- `eabi` — Embedded ABI v5
- `hf` — hard-float: floating-point arguments passed in VFP registers (faster but binary-incompatible with `gnueabi` soft-float)

For bare-metal Part II we will sometimes want a `arm-none-eabi` toolchain (no OS, no libc). Install it now so we don't have to interrupt later:

```sh
$ sudo apt install -y gcc-arm-none-eabi
```

We now have two toolchains:

- `arm-linux-gnueabihf-gcc` — for code that runs *under* Linux on the target.
- `arm-none-eabi-gcc` — for the bare-metal experiments where there is no OS.

A common source of confusion: people use the `linux-gnueabihf` toolchain for bare metal and get baffled when their build pulls in libc. Use the right tool for the job.

### Pin the toolchain in your shell

Add this to `~/.bashrc` so every shell finds the toolchain consistently:

```sh
# ~/.bashrc
export CROSS_COMPILE=arm-linux-gnueabihf-
export ARCH=arm
```

These two variables are what U-Boot's, the kernel's, and BusyBox's Makefiles look for. Setting them globally saves a lot of typing.

## 3.5  Serial console

Wire pin 8 of UART1 TX on the SoC to the host's USB-serial dongle RX, and UART1 RX on the SoC to the host's TX. Ground common. The Point Atom MINI exposes UART1 on a 3.3 V header — do **not** connect a 5 V FTDI adapter directly or you may damage the SoC. A `CP2102` or `CH340G` 3.3 V module is the standard cheap option.

Once plugged in:

```sh
$ ls /dev/ttyUSB*
/dev/ttyUSB0
```

If that file does not exist, check `dmesg | tail`:

```sh
$ dmesg | tail
[...] usb 1-1.2: new full-speed USB device number 5 using xhci_hcd
[...] usb 1-1.2: New USB device found, idVendor=10c4, idProduct=ea60
[...] cp210x 1-1.2:1.0: cp210x converter detected
[...] usb 1-1.2: cp210x converter now attached to ttyUSB0
```

Add your user to the `dialout` group so you do not need `sudo` for serial:

```sh
$ sudo usermod -aG dialout $USER
$ # log out and back in for the group to take effect
```

Open the console:

```sh
$ picocom -b 115200 /dev/ttyUSB0
picocom v3.1
port is        : /dev/ttyUSB0
flowcontrol    : none
baudrate is    : 115200
parity is      : none
databits are   : 8
stopbits are   : 1
...
Terminal ready
```

Quit with **Ctrl-A Ctrl-X**. Send Ctrl-C with **Ctrl-A Ctrl-C** (the leader sequence catches things picocom would otherwise intercept).

**Pitfall:** if you see garbage characters, the baud rate is wrong or the host's TX is fighting with the board's TX. Disconnect, double-check wiring, try `-b 57600` once to confirm.

### 3.5a  Windows-side serial terminals (for Windows-mainly readers)

If your host is Windows (WSL2 or dual-boot Linux), or if you sometimes connect from a Windows laptop in the field, the most-used serial-terminal options are:

- **MobaXterm** (`mobaxterm.mobatek.net`, free Home Edition) — combined SSH client + serial terminal + X server + session-saving + SFTP browser. Recommended for Windows hosts.
- **SecureCRT** (`vandyke.com`, commercial) — fastest scrollback, best session-tabs, configurable keymap. Worth the money if you live in serial consoles.
- **Putty** (`putty.org`, free) — minimal, ubiquitous, no scripting. Fine if you only need it occasionally.
- **Tera Term** (`teratermproject.github.io`, free) — Japanese-origin, popular in industrial settings, has a useful macro language.

For all of them, the **CH340/CP2102 USB-serial dongle driver** is the prerequisite on Windows; install from the chip vendor's site (`wch.cn` for CH340, `silabs.com` for CP2102). Linux includes both kernel drivers by default — nothing to install.

When configuring any of these tools, the settings are the same we used for `picocom`: **115200 8N1, no flow control**.

### 3.5b  Source Insight as a kernel-source navigation aid (optional)

The Linux kernel source tree is ~80,000 files. Tools that index it on a fast SSD beat ones that don't.

- **Source Insight 4** (`sourceinsight.com`, commercial Windows) — extremely fast indexer, instant "Go to Definition," visual call graphs. Read-only for our purposes; popular in Chinese-language embedded communities.
- **VSCode + C/C++ extension** (Microsoft) — slower indexer but free, cross-platform, and you can edit. Use `compile_commands.json` from a kernel build so IntelliSense follows the right includes.
- **`cscope` + `ctags`** in the terminal — old-school, instant, scriptable.
- **`elixir.bootlin.com`** — kernel cross-reference in your browser, no install. Surprisingly capable.

For this book, we do not require any of them. But if you find yourself spending more than five minutes hunting a kernel symbol, install one.

## 3.6  TFTP server

The board's U-Boot will fetch kernel images from your host over TFTP. Set up `tftpd-hpa`:

```sh
$ sudo sed -i 's|^TFTP_DIRECTORY=.*|TFTP_DIRECTORY="/srv/tftp"|' /etc/default/tftpd-hpa
$ sudo sed -i 's|^TFTP_OPTIONS=.*|TFTP_OPTIONS="--secure --create"|' /etc/default/tftpd-hpa
$ sudo mkdir -p /srv/tftp
$ sudo chown $USER:$USER /srv/tftp
$ sudo systemctl restart tftpd-hpa
$ sudo systemctl enable tftpd-hpa
```

Smoke-test:

```sh
$ echo "hello tftp" > /srv/tftp/test.txt
$ tftp localhost -c get test.txt
$ cat test.txt
hello tftp
```

If that round-trip works, U-Boot will be able to do the same thing.

**Pitfall:** Ubuntu's `ufw` firewall, if enabled, blocks UDP/69. Either disable `ufw` on the dev host or `sudo ufw allow tftp`.

## 3.7  NFS server

`/etc/exports`:

```sh
$ sudo bash -c 'echo "/home/$SUDO_USER/imx6ull/rootfs *(rw,sync,no_root_squash,no_subtree_check)" >> /etc/exports'
$ sudo exportfs -ar
$ sudo systemctl restart nfs-kernel-server
$ sudo showmount -e localhost
Export list for localhost:
/home/<you>/imx6ull/rootfs *
```

The flags decoded:

- `rw` — the target can write back. We want this; the target's `dmesg` and `/var/log` should be persistent across reboots.
- `sync` — writes are committed before the server replies. Slower but safer.
- `no_root_squash` — the target's `root` is treated as host root. Required, because the target's processes will create files as `uid 0` and expect them to be readable by `uid 0`.
- `no_subtree_check` — skip a check that hurts performance and offers little safety on a dev host.

**Security:** these are dev-host settings. Do not run an NFS server with these flags on a network you do not control.

## 3.8  USB-OTG flashing tools

The i.MX6ULL Boot ROM speaks **SDP** (Serial Download Protocol) over its USB-OTG port. When you strap the boot pins to "USB" or no SD/eMMC is present, the chip enumerates as a USB device and waits for someone to push an image. Two tools speak SDP:

### `uuu` (Universal Update Utility)

NXP's official tool. Download the latest release from <https://github.com/nxp-imx/mfgtools>:

```sh
$ cd ~/imx6ull/src
$ git clone https://github.com/nxp-imx/mfgtools
$ cd mfgtools
$ sudo apt install -y libusb-1.0-0-dev libzip-dev libbz2-dev pkg-config cmake
$ cmake . && make -j$(nproc)
$ sudo cp uuu/uuu /usr/local/bin/
$ uuu -v
uuu (Universal Update Utility) for nxp imx chips -- 1.5.x-0-gxxxxxxx
```

### `imx_usb_loader`

A community alternative that some find easier. Lighter, single binary, no fancy script DSL:

```sh
$ cd ~/imx6ull/src
$ git clone https://github.com/boundarydevices/imx_usb_loader
$ cd imx_usb_loader
$ make
$ sudo make install
```

You only need one. We will use `uuu` in this book because its scripting language is useful for Chapter 8's recovery flow. Install both if you like options.

**udev rule for non-root access:**

```sh
$ sudo tee /etc/udev/rules.d/99-imx.rules > /dev/null <<'EOF'
SUBSYSTEM=="usb", ATTR{idVendor}=="15a2", ATTR{idProduct}=="0080", MODE="0666"
SUBSYSTEM=="usb", ATTR{idVendor}=="1fc9", ATTR{idProduct}=="0145", MODE="0666"
EOF
$ sudo udevadm control --reload-rules
$ sudo udevadm trigger
```

`15a2:0080` is the i.MX6ULL ROM SDP enumeration; `1fc9:0145` is the same after a board enters the second-stage download (different VID/PID once U-Boot SPL takes over).

## 3.9  SD card preparation

A spare 4–32 GB SD card, class 10 or better, dedicated to this project. We will overwrite it many times.

Identify which device it is — **carefully**:

```sh
$ lsblk
NAME    MAJ:MIN RM   SIZE RO TYPE MOUNTPOINTS
sda       8:0    0   1.0T  0 disk
└─sda1    8:1    0   1.0T  0 part /
sdc       8:32   1   7.5G  0 disk         ← this is the SD card
└─sdc1    8:33   1   7.5G  0 part
```

If you wipe the wrong block device you will lose your operating system. Look at the size. Look at the mount points. Then look again.

A small helper script saves you from typos:

```sh
$ cat > ~/imx6ull/scripts/sd-write.sh <<'EOF'
#!/bin/bash
# Usage: sd-write.sh <image> <device>
set -euo pipefail
IMG="$1"; DEV="$2"
[ -b "$DEV" ] || { echo "Not a block device: $DEV" >&2; exit 1; }
[[ "$DEV" =~ ^/dev/sd[b-z]$ ]] || { echo "Refusing $DEV (must be /dev/sd[b-z])" >&2; exit 1; }
read -p "Wipe $DEV (size $(lsblk -bdno SIZE "$DEV" | numfmt --to=iec))? [y/N] " r
[ "$r" = y ] || exit 1
sudo dd if="$IMG" of="$DEV" bs=1M conv=fsync status=progress
sync
EOF
$ chmod +x ~/imx6ull/scripts/sd-write.sh
```

That regex on `/dev/sd[b-z]` is the seatbelt: it refuses to write to `/dev/sda`, which is almost always your host's root disk.

## 3.10  Host IP plan

Pick a static IP for the dev host on the wire to the board. We will use `192.168.7.1` throughout the book:

- Host: **192.168.7.1**
- Board: **192.168.7.2**

The simplest setup is a directly-connected Ethernet cable between host and board, with the host's secondary NIC set to a static IP. If you only have one NIC and need internet, a small unmanaged switch in between is fine. Wi-Fi works but adds variables; we prefer wired.

If you use NetworkManager:

```sh
$ sudo nmcli con add type ethernet con-name imx-link ifname enp0s31f6 \
    ipv4.method manual ipv4.addresses 192.168.7.1/24
$ sudo nmcli con up imx-link
```

(Substitute your NIC name from `ip a`.)

Verify:

```sh
$ ip -4 addr show enp0s31f6
... inet 192.168.7.1/24 ...
```

We test the link to the board in Chapter 8 after the board has U-Boot on it.

## 3.11  Sanity check

End-of-chapter checklist. Run every command, get every expected result:

```sh
$ arm-linux-gnueabihf-gcc --version | head -1
arm-linux-gnueabihf-gcc (Ubuntu 11.4.0-1ubuntu1~22.04) 11.4.0

$ arm-none-eabi-gcc --version | head -1
arm-none-eabi-gcc (15:10.3-2021.07-4) 10.3.1 20210621 (release)

$ which dtc mkimage picocom uuu
/usr/bin/dtc
/usr/bin/mkimage
/usr/bin/picocom
/usr/local/bin/uuu

$ systemctl is-active tftpd-hpa nfs-kernel-server
active
active

$ ls -d ~/imx6ull/{src,build,boot,rootfs,scripts,notes}
/home/<you>/imx6ull/boot
/home/<you>/imx6ull/build
/home/<you>/imx6ull/notes
/home/<you>/imx6ull/rootfs
/home/<you>/imx6ull/scripts
/home/<you>/imx6ull/src

$ groups | grep -ow dialout
dialout
```

If any of these fail, do not move on. Subsequent chapters silently assume each.

## 3.12  Lab

Write a short shell script `~/imx6ull/scripts/env.sh` that exports:

- `CROSS_COMPILE=arm-linux-gnueabihf-`
- `ARCH=arm`
- `TFTPROOT=/srv/tftp`
- `NFSROOT=$HOME/imx6ull/rootfs`
- `BOARD_IP=192.168.7.2`
- `HOST_IP=192.168.7.1`

Then `. ~/imx6ull/scripts/env.sh` at the top of every new shell. Add the source line to `~/.bashrc` if you like — but be aware that it makes those variables global, which has occasionally surprised people when they later cross-compile something unrelated.

A more disciplined alternative is `direnv` (`sudo apt install direnv`), which auto-loads `.envrc` only when you `cd` into `~/imx6ull/`. Recommended for serious work.

## 3.13  Pitfalls

- **WSL2 USB-OTG.** USB pass-through via `usbipd-win` works for ordinary USB but the SDP enumeration after a board reset can race with WSL's USB stack. Symptom: `uuu` reports "no device". Workaround: re-attach with `usbipd attach --busid <id>` after every reset. Annoying. Native Linux avoids this entirely.
- **`tftp` blocked by firewall.** Ubuntu's UFW, if enabled, drops UDP/69 silently. `sudo ufw status` first.
- **NFS over Wi-Fi to a slow board.** Booting a kernel over NFS-root on Wi-Fi works but is brittle. If you see "VFS: Unable to mount root fs", it is almost always NFS timing out, not a real kernel bug. Use wired.
- **Multiple toolchains on PATH.** The first `arm-linux-gnueabihf-gcc` in `PATH` wins. If you install both the Ubuntu package and Linaro, prepend the one you want explicitly.
- **`dd` to the wrong device.** Every embedded engineer has done this once. Use the helper from §3.9 and you will only do it once.
- **`sudo` and environment variables.** `sudo CROSS_COMPILE=arm-linux-gnueabihf- make` does *not* pass `CROSS_COMPILE` unless `sudo`'s `env_reset` is disabled. Build without `sudo`; install with `sudo`.

## 3.14  Going deeper

- `man 8 exportfs`, `man 5 exports`, `man 8 tftpd`, `man 5 udev` — read the man pages of the services you just configured.
- `picocom`'s `-l` (lock-file) and `-i` (initstring) options are useful for scripting boot.
- *The TCP/IP Guide* (Charles Kozierok) on TFTP and NFS protocols if you want to know what is on the wire.
- If you intend to run a lot of cross-builds, look at `ccache` (`sudo apt install ccache`) and prepend it to `CROSS_COMPILE`: `CROSS_COMPILE="ccache arm-linux-gnueabihf-"`. We do *not* use it in this book because it occasionally masks subtle dependency bugs in Makefiles we're trying to read.

> Next chapter: **Chapter 4 — ARMv7-A and the Cortex-A7, for the MCU engineer.** We leave the host and start understanding the silicon we will program.
