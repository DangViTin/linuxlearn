# Chapter 3: Host environment setup

> **What:** a Linux development host that can cross-compile for ARMv7-A, serve files over TFTP and NFS, talk to the board over serial and USB-OTG, and recover a bricked board.
>
> **Why:** for the next sixty chapters, the host is your lever. A flaky host wastes more of your time than any bug in your code.
>
> **Focus:** the iteration loop. By the end of this chapter, the loop "change a file, see it run on the board" must take under thirty seconds. If it is slower, you will iterate less, and you will learn less.


## 3.1  Choosing the host

The book assumes **native / VM(VirtualBox/VMware) Ubuntu 22.04 LTS** running on bare-metal hardware. Other options work but cost you time, sometimes a lot:|
The remainder of this book assumes Ubuntu 22.04. Commands shown with the `$` prompt run as your normal user. Commands with `#` run as root via `sudo`.

## 3.2  Workspace layout

> **Driver choice:** Use the in-tree, maintained driver first.
> Use out-of-tree, spidev, or custom-driver paths only after you accept the kernel-version maintenance cost and document who owns updates.


Create the workspace before installing anything. The layout you set now will be referred to by every chapter:

```sh
$ mkdir -p ~/imx6ull/{src,build,boot,rootfs,scripts,toolchains,notes}
$ cd ~/imx6ull
$ tree -L 1
.
├── boot       # bootable artefacts staged here, then dd'd to SD
├── build      # all out-of-tree build outputs (kernel, U-Boot, BusyBox)
├── notes      # your lab journal, per-chapter
├── rootfs     # exported over NFS to the target
├── scripts    # helpers, shared between chapters
├── src        # upstream sources: linux, u-boot, busybox, your bare-metal code
└── toolchains # prebuilt Arm compilers kept local to this project
```

Two rules about this layout. Both matter for the rest of the book:

1. **Sources are read-only.** We never edit inside `src/u-boot/`. We patch and build out-of-tree into `build/u-boot/`. This is the only way to keep a clean diff against upstream and keep cross-chapter reproducibility honest.
**U-Boot** - the bootloader that initializes enough hardware to load and start the Linux kernel.
2. **`rootfs/` is the live NFS root.** Anything you copy into `rootfs/` is visible to the board after the next boot, with no flashing step. This is the central iteration trick of embedded Linux.

## 3.3  Host packages

> Verify the removable card by size and model, unmount its partitions, and stop if the path is not the target card. Writing the wrong /dev node can destroy the host disk.

> Use throwaway keys and back up the unsigned image plus the key directory before testing irreversible security flows.


Install in one shot:

```sh
$ sudo apt update
$ sudo apt install -y \
    build-essential bison flex libssl-dev libncurses-dev \
    bc kmod cpio rsync wget curl git unzip xz-utils \
    device-tree-compiler u-boot-tools \
    nfs-kernel-server tftpd-hpa tftp-hpa \
    minicom picocom \
    qemu-user-static binfmt-support \
    gdb-multiarch \
    pkg-config libusb-1.0-0-dev libftdi1-dev \
    libgmp-dev libmpfr-dev libmpc-dev libisl-dev \
    fakeroot dosfstools mtools parted
```

What each pulls in, briefly:

- **`build-essential`, `bison`, `flex`, `libssl-dev`, `libncurses-dev`** — what the kernel and U-Boot need to build. Surprise: the kernel needs OpenSSL during build (for module signing).
- **`bc`** — really. The kernel build literally invokes `bc` for arithmetic.
- **`device-tree-compiler`** — `dtc`. You'll use this in every chapter from Ch 27 on.
- **`u-boot-tools`** — provides `mkimage`, `mkenvimage`, `dumpimage`, `mkeficapsule`.
- **`nfs-kernel-server`, `tftpd-hpa`** — server side of the network-boot loop.
- **`minicom`, `picocom`** — serial terminals. We'll use `picocom`. `minicom` is here for users who prefer it.
- **`qemu-user-static`, `binfmt-support`** — lets you run ARM binaries on the host transparently. Useful when staging a rootfs with `chroot`.
- **`gdb-multiarch`** — one `gdb` that speaks every architecture. We'll point it at ARM ELFs.
- **`libusb-1.0-0-dev`, `libftdi1-dev`** — needed by `imx_usb_loader` and OpenOCD when we build them from source.
**OpenOCD** - the host program that talks to a JTAG adapter and exposes a GDB server.
- **`fakeroot`, `dosfstools`, `mtools`, `parted`** — manipulate SD card images without needing root.

If `apt` complains about any package on your distribution, search for the closest equivalent and note the substitution in your journal.

## 3.4  The cross toolchain

We need two prebuilt Arm toolchains:

- **Linux target toolchain:** `arm-none-linux-gnueabihf-`
  Builds U-Boot, the Linux kernel, BusyBox, and target user-space programs. It targets 32-bit Arm Linux with the hard-float glibc ABI.
- **Bare-metal toolchain:** `arm-none-eabi-`
  Builds the small no-OS experiments in Part II. It does not assume Linux, glibc, processes, or a dynamic loader.

Keeping both is not the same as letting random compilers leak into the build. We will install both in one project-local directory, name them clearly, and select them explicitly.

Download these two Arm GNU Toolchain packages from Arm's official page:

<https://developer.arm.com/downloads/-/arm-gnu-toolchain-downloads>

- `arm-gnu-toolchain-*-x86_64-arm-none-linux-gnueabihf.tar.xz`
- `arm-gnu-toolchain-*-x86_64-arm-none-eabi.tar.xz`

Save both tarballs in `~/imx6ull/src/toolchains/`. Keeping the original tarballs there makes it easy to see exactly what was installed later.

```sh
$ mkdir -p ~/imx6ull/src/toolchains
$ cd ~/imx6ull/src/toolchains
$ ls
arm-gnu-toolchain-<version>-x86_64-arm-none-linux-gnueabihf.tar.xz
arm-gnu-toolchain-<version>-x86_64-arm-none-eabi.tar.xz
```

Extract both under the project workspace, not `/opt`. This keeps the setup portable and avoids changing the host machine more than necessary.

```sh
$ mkdir -p ~/imx6ull/toolchains
$ tar -xf arm-gnu-toolchain-*-x86_64-arm-none-linux-gnueabihf.tar.xz \
    -C ~/imx6ull/toolchains
$ tar -xf arm-gnu-toolchain-*-x86_64-arm-none-eabi.tar.xz \
    -C ~/imx6ull/toolchains
```
After extract, we have:

```text
~/imx6ull/toolchains/arm-gnu-toolchain-<version>-x86_64-arm-none-linux-gnueabihf/bin/arm-none-linux-gnueabihf-gcc
~/imx6ull/toolchains/arm-gnu-toolchain-<version>-x86_64-arm-none-eabi/bin/arm-none-eabi-gcc
```

Those are the paths to remember when debugging build problems.

### Decoding the triplets

`arm-none-linux-gnueabihf` and `arm-none-eabi` look alphabet-soupy. They are not.

- `arm` means the target CPU family is 32-bit Arm.
- The middle `none` is the vendor field. Here it means no specific silicon vendor.
- `linux` means the generated program expects a Linux target environment.
- `gnu` means GNU userland and glibc ABI.
- `eabi` means Embedded ABI v5.
**ABI** - Application Binary Interface: the calling convention, register use, binary format, and library contract that let separately built code run together.
- `hf` means hard-float: floating-point arguments are passed in VFP registers.

The practical rule:

- Use `arm-none-linux-gnueabihf-` when the output is meant to run with Linux or link against Linux user-space libraries.
- Use `arm-none-eabi-` when the output is a freestanding image with no OS underneath it.

### Environment script

Do not edit `~/.bashrc` for this book. Hidden global shell state is convenient after you understand it, but it is bad for learning and can break unrelated projects.

Create one explicit environment script:

```sh
$ nano ~/imx6ull/scripts/env.sh
```

Put this in the file:

```sh
#!/bin/sh

export IMX6ULL_HOME="$HOME/imx6ull"
export ARM_LINUX_TOOLCHAIN="$(ls -d "$IMX6ULL_HOME"/toolchains/arm-gnu-toolchain-*-x86_64-arm-none-linux-gnueabihf)"
export ARM_BAREMETAL_TOOLCHAIN="$(ls -d "$IMX6ULL_HOME"/toolchains/arm-gnu-toolchain-*-x86_64-arm-none-eabi)"

export PATH="$ARM_LINUX_TOOLCHAIN/bin:$ARM_BAREMETAL_TOOLCHAIN/bin:$PATH"

export ARCH=arm
export CROSS_COMPILE=arm-none-linux-gnueabihf-
export BAREMETAL_CROSS_COMPILE=arm-none-eabi-

export TFTPROOT=/srv/tftp
export NFSROOT="$IMX6ULL_HOME/rootfs"

# Default direct-link lab addresses. If you use your home/office router
# instead, replace these with the real LAN addresses from Section 3.10.
export BOARD_IP=192.168.7.2
export HOST_IP=192.168.7.1
```

This script assumes there is exactly one Linux toolchain folder and exactly one bare-metal toolchain folder in `~/imx6ull/toolchains/`. If you later upgrade the toolchains, remove the old extracted folders first.

Every time you open a new terminal for this book, run:

```sh
$ . ~/imx6ull/scripts/env.sh
```

That leading dot matters. It means "source this file into the current shell." Running `~/imx6ull/scripts/env.sh` without the dot would run it in a child shell, then throw the environment away when the script exits.

Verify both compilers and both prefixes:

```sh
$ which arm-none-linux-gnueabihf-gcc
/home/<you>/imx6ull/toolchains/arm-gnu-toolchain-<version>-x86_64-arm-none-linux-gnueabihf/bin/arm-none-linux-gnueabihf-gcc

$ arm-none-linux-gnueabihf-gcc --version | head -1
arm-none-linux-gnueabihf-gcc (Arm GNU Toolchain ...)

$ which arm-none-eabi-gcc
/home/<you>/imx6ull/toolchains/arm-gnu-toolchain-<version>-x86_64-arm-none-eabi/bin/arm-none-eabi-gcc

$ arm-none-eabi-gcc --version | head -1
arm-none-eabi-gcc (Arm GNU Toolchain ...)

$ echo "$CROSS_COMPILE"
arm-none-linux-gnueabihf-

$ echo "$BAREMETAL_CROSS_COMPILE"
arm-none-eabi-
```

`CROSS_COMPILE` is the prefix U-Boot's, the kernel's, and BusyBox's Makefiles look for. We reserve `BAREMETAL_CROSS_COMPILE` for our own bare-metal Makefiles so the two worlds stay visible.

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

Open the console with `sudo`:

```sh
$ sudo picocom -b 115200 /dev/ttyUSB0
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

We use `sudo` here on purpose. `/dev/ttyUSB0` is a hardware device node, and Linux protects hardware access with file permissions. For this book, keep `sudo` in the serial command so the privilege boundary stays visible.

Quit with Ctrl-A Ctrl-X. To send a real Ctrl-C to the board, press Ctrl-A then Ctrl-C — picocom uses Ctrl-A as its escape key.

**Pitfall:** if you see garbage characters, the baud rate is wrong or the host's TX is fighting with the board's TX. Disconnect, double-check wiring.

### 3.5a  Windows-side serial terminals (for Windows-mainly readers)

If your host is Windows (WSL2 or dual-boot Linux), or if you sometimes connect from a Windows laptop in the field, the most-used serial-terminal options are:

- **MobaXterm** (`mobaxterm.mobatek.net`, free Home Edition) — combined SSH client + serial terminal + X server + session-saving + SFTP browser. Recommended for Windows hosts.
- **SecureCRT** (`vandyke.com`, commercial) — fastest scrollback, best session-tabs, configurable keymap. Worth the money if you live in serial consoles.
- **Putty** (`putty.org`, free) — minimal, ubiquitous, no scripting. Fine if you only need it occasionally.
- **Tera Term** (`teratermproject.github.io`, free) — Japanese-origin, popular in industrial settings, has a useful macro language.

For all of them, the **CH340/CP2102 USB-serial dongle driver** is the prerequisite on Windows. install from the chip vendor's site (`wch.cn` for CH340, `silabs.com` for CP2102). Linux includes both kernel drivers by default, nothing to install.

When configuring any of these tools, the settings are the same we used for `picocom`: **115200 8N1, no flow control**.

### 3.5b  Source Insight as a kernel-source navigation aid (optional)

The Linux kernel source tree is ~80,000 files. Tools that index it on a fast SSD beat ones that don't.

- **Source Insight 4** (`sourceinsight.com`, commercial Windows) — extremely fast indexer, instant "Go to Definition," visual call graphs. Read-only for our purposes. It is popular in Chinese-language embedded communities.
- **VSCode + C/C++ extension** (Microsoft) — slower indexer but free, cross-platform, and you can edit. Use `compile_commands.json` from a kernel build so IntelliSense follows the right includes.
- **`cscope` + `ctags`** in the terminal — old-school, instant, scriptable.
- **`elixir.bootlin.com`** — kernel cross-reference in your browser, no install. Surprisingly capable.

For this book, we do not require any of them. But if you find yourself spending more than five minutes hunting a kernel symbol, install one.

## 3.6  TFTP server

The board's U-Boot will fetch kernel images from your host over TFTP.

Install the server package if you have not already:

```sh
$ sudo apt install -y tftpd-hpa tftp-hpa
```

Now open the server configuration:

```sh
$ sudoedit /etc/default/tftpd-hpa
```

Make the file look like this:

```text
TFTP_USERNAME="tftp"
TFTP_DIRECTORY="/srv/tftp"
TFTP_ADDRESS=":69"
TFTP_OPTIONS="--secure --create"
```

What each line means:

- `TFTP_USERNAME="tftp"` runs the daemon as the unprivileged `tftp` user.
- `TFTP_DIRECTORY="/srv/tftp"` is the directory U-Boot will read files from.
- `TFTP_ADDRESS=":69"` listens on the standard TFTP UDP port.
- `TFTP_OPTIONS="--secure --create"` keeps the daemon rooted inside `/srv/tftp` and permits file creation.

Create the directory, make your normal user its owner, and keep it readable by the TFTP daemon:

```sh
$ sudo mkdir -p /srv/tftp
$ sudo chown $USER:$USER /srv/tftp
$ chmod 755 /srv/tftp
```

Why the permission change matters:

- `/srv` is a system directory. Without `sudo`, a normal user usually cannot create `/srv/tftp`.
- After `sudo mkdir`, the new directory is owned by `root`, so your normal user would need `sudo` every time you copy a kernel, device tree, or U-Boot image into it.
- `sudo chown $USER:$USER /srv/tftp` changes the owner to your user. Now you can write files there with normal commands like `cp zImage /srv/tftp/`.
- The TFTP server does not run as your user. `TFTP_USERNAME="tftp"` means it runs as the low-privilege `tftp` user, so a bug in the TFTP server has less power on the host.
- `chmod 755 /srv/tftp` means: owner can read/write/enter, everyone else can read/enter but not write. That lets the `tftp` user read files from the directory while only you can add or replace files.

Files you copy into `/srv/tftp` also need to be readable by the TFTP daemon. Normal files created by `cp` or `echo` are usually readable already. If U-Boot gets "permission denied" from TFTP, check with:

```sh
$ ls -l /srv/tftp
```

Restart and enable the service:

```sh
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

The test writes a small file into the TFTP root, then asks the local TFTP server for that file. The final `cat` proves the file came back.

If that round-trip works, U-Boot will be able to do the same thing.

**Pitfall:** Ubuntu's `ufw` firewall, if enabled, blocks UDP/69. Either disable `ufw` on the dev host or `sudo ufw allow tftp`.

## 3.7  NFS server

The Linux kernel can mount its root filesystem over NFS during development. That lets you edit files on the host and reboot the board without rebuilding an SD-card image.

Install the server package if needed:

```sh
$ sudo apt install -y nfs-kernel-server
```

Open the export table:

```sh
$ sudoedit /etc/exports
```

Add one line at the end. Replace `<you>` with your Linux username:

```text
/home/<you>/imx6ull/rootfs *(rw,sync,no_root_squash,no_subtree_check)
```

Then apply and verify:

```sh
$ sudo exportfs -ar
$ sudo systemctl restart nfs-kernel-server
$ sudo showmount -e localhost
Export list for localhost:
/home/<you>/imx6ull/rootfs *
```

What the commands do:

- `exportfs -ar` asks the NFS server to re-read `/etc/exports` and apply the export table.
- `systemctl restart nfs-kernel-server` restarts the NFS daemon so the kernel-side service is using the current config.
- `showmount -e localhost` lists what this host exports over NFS. Seeing the `rootfs` path here is the sanity check.

The flags decoded:

- `rw` — the target can write back. We want this. The target's `dmesg` and `/var/log` should be persistent across reboots.
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
$ sudo apt install -y libusb-1.0-0-dev libzip-dev libbz2-dev pkg-config cmake libzstd-dev libtinyxml2-dev
$ cmake . && make -j$(nproc)
$ sudo cp uuu/uuu /usr/local/bin/
$ uuu -h
uuu (Universal Update Utility) for nxp imx chips -- 1.5.x-0-gxxxxxxx
```
Now add a udev rule so your normal user can talk to the board over USB without running `uuu` as root.

You *can* type `sudo uuu ...` every time, but do not make that your normal workflow. `uuu` is a host-side flashing tool that opens USB devices and writes boot images. It does not need full root access to your workstation. Giving it root privileges hides the real permission problem and increases the damage if you point a command at the wrong file or run a broken script.

The cleaner model is:

- root owns system configuration, such as the udev rule;
- your user belongs to a hardware-access group;
- `uuu` runs as your user and can open only the matching USB devices.

First check whether the group already exists:

```sh
$ getent group plugdev
```

If that prints a `plugdev:...` line, the group already exists and you do not need to create it. Add yourself to it:

```sh
$ sudo usermod -aG plugdev "$USER"
```

If `getent` prints nothing, create the group first:

```sh
$ sudo groupadd plugdev
$ sudo usermod -aG plugdev "$USER"
```

You will also see this shorter form in many setup notes:

```sh
$ sudo groupadd -f plugdev
$ sudo usermod -aG plugdev "$USER"
```

The `-f` means "succeed even if the group already exists", so the command is safe to run on both cases.

Log out and back in after `usermod`; group membership is read when your login session starts.

Open a new rule file:

```sh
$ sudoedit /etc/udev/rules.d/99-imx.rules
```

Put these two lines in it:

```text
SUBSYSTEM=="usb", ATTR{idVendor}=="15a2", ATTR{idProduct}=="0080", MODE="0660", GROUP="plugdev"
SUBSYSTEM=="usb", ATTR{idVendor}=="1fc9", ATTR{idProduct}=="0145", MODE="0660", GROUP="plugdev"
```

Then reload udev:

```sh
$ sudo udevadm control --reload-rules
$ sudo udevadm trigger
```

`15a2:0080` is the i.MX6ULL ROM SDP enumeration. `1fc9:0145` is the same after a board enters the second-stage download (different VID/PID once U-Boot SPL takes over).

After reloading the rules, unplug and replug the board. Then test without `sudo`:

```sh
$ uuu -lsusb
```

If `uuu -lsusb` sees the board as your normal user, the setup is correct. Use `sudo` only while installing host packages, copying binaries into `/usr/local/bin`, or editing `/etc` files, do not use it as a workaround for USB permissions.

## 3.9  SD card preparation (just read for later chapter, not to follow now)

A spare 4–32 GB SD card, class 10 or better, dedicated to this project. We will overwrite it many times.

Identify which device it is, **carefully**:

```sh
$ lsblk
NAME    MAJ:MIN RM   SIZE RO TYPE MOUNTPOINTS
sda       8:0    0   1.0T  0 disk
└─sda1    8:1    0   1.0T  0 part /
sdc       8:32   1   7.5G  0 disk         ← this is the SD card
└─sdc1    8:33   1   7.5G  0 part
```

If you wipe the wrong block device you will lose your operating system. Check the size and the mount points twice before running `dd`.

The manual write flow is short, and you should understand it before using any helper script. In later chapters the image name will be whatever image you just built, for example `~/imx6ull/build/images/sdcard.img`.

First unmount any mounted partition on the card. Unmount the partition path, not the whole-disk path:

```sh
$ sudo umount /dev/sdc1
```

If the card has more than one mounted partition, unmount each one:

```sh
$ lsblk /dev/sdc
$ sudo umount /dev/sdc1
$ sudo umount /dev/sdc2
```

Then write the image to the whole card:

```sh
$ sudo dd if=~/imx6ull/build/images/sdcard.img of=/dev/sdc bs=4M status=progress conv=fsync
$ sync
```

Read that command carefully:

- `if=` means input file. This is the image you built.
- `of=` means output file. For `dd`, a block device is treated like a file.
- `of=/dev/sdc` writes the whole SD card, including the partition table.
- `of=/dev/sdc1` writes only the first partition. That is wrong for a full bootable card image.
- `bs=4M` writes in 4 MiB chunks instead of tiny default chunks.
- `status=progress` shows progress while the write runs.
- `conv=fsync` asks `dd` to flush the written data before it exits.
- `sync` waits for any remaining buffered writes before you remove the card.

After `sync` returns, remove and reinsert the card, then check the result:

```sh
$ lsblk /dev/sdc
```

You should see the partitions created by the image. If `lsblk` still shows the old partitions, you probably wrote the wrong device or the image path was wrong.

After you understand the manual flow, a small helper script can save you from repeat typing mistakes. Create this file:

```sh
$ nano ~/imx6ull/scripts/sd-write.sh
```

Paste the script below, then read it before saving. The important part is the safety check that refuses `/dev/sda`.

```sh
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
```

Make it executable:

```sh
$ chmod +x ~/imx6ull/scripts/sd-write.sh
```

That regex on `/dev/sd[b-z]` is the seatbelt: it refuses to write to `/dev/sda`, which is almost always your host's root disk.

## 3.10  Host IP plan

For TFTP, NFS, and U-Boot experiments, the board must know how to reach the host. The important thing is not the exact address. The important thing is that the address stays stable.

There are two common setups.

### Option A: direct host-to-board link

Use this when your computer has a spare Ethernet port, a USB-to-Ethernet adapter, or Wi-Fi for internet plus Ethernet for the board.

In this book, the clean lab network is:

- Host: **192.168.7.1**
- Board: **192.168.7.2**

This private `192.168.7.0/24` network is separate from your home or office LAN. It avoids DHCP changes, router settings, and IP conflicts. That is why many embedded Linux labs use a dedicated direct link.

If you use NetworkManager:

```sh
$ sudo nmtui
```

In the text UI:

1. Choose **Edit a connection**.
2. Select the Ethernet interface connected to the board.
3. Set **IPv4 CONFIGURATION** to **Manual**.
4. Add address `192.168.7.1/24`.
5. Leave gateway and DNS empty for this direct board link.
6. Save and activate the connection.

The same setup can be done from the command line:

```sh
$ sudo nmcli con add type ethernet con-name imx-link ifname enp0s31f6 ipv4.method manual ipv4.addresses 192.168.7.1/24
$ sudo nmcli con up imx-link
```

Substitute your NIC name from `ip a`. The `nmtui` path is slower, but it makes the fields visible the first time.

Verify:

```sh
$ ip -4 addr show enp0s31f6
... inet 192.168.7.1/24 ...
```

### Option B: board and host on your existing router

Use this when your computer has only one Ethernet port and it already connects to your Wi-Fi modem or home router. In that case, do **not** force the host to `192.168.7.1`. Leave the host on the router's LAN, usually something like `192.168.1.x`, and plug the i.MX6ULL board into the same router or switch.

Example:

- Router: **192.168.1.1**
- Host: **192.168.1.23**
- Board: **192.168.1.50**

Find the host's current LAN address:

```sh
$ ip -4 addr
```

Look for the address on the interface connected to the router. In later U-Boot commands, this host address becomes `serverip`.

For the board address, use one of these:

- reserve a fixed DHCP address for the board in your router;
- let U-Boot request DHCP, then read the assigned address;
- choose an unused static address outside the router's DHCP pool.

Router mode is practical, but it has two drawbacks:

- DHCP can change the board address unless you reserve it.
- Some routers isolate clients, especially guest Wi-Fi networks. If TFTP or ping fails even though both devices have `192.168.1.x` addresses, check client isolation and firewall settings.

Throughout the book, commands may show the direct-link values:

```text
serverip=192.168.7.1
ipaddr=192.168.7.2
```

If you use router mode, substitute your real LAN values instead:

```text
serverip=<your host IP, for example 192.168.1.23>
ipaddr=<your board IP, for example 192.168.1.50>
```

We test the link to the board in Chapter 8 after the board has U-Boot on it.

## 3.11  Sanity check

End-of-chapter checklist. Run every command, get every expected result:

```sh
$ . ~/imx6ull/scripts/env.sh

$ which arm-none-linux-gnueabihf-gcc
/home/<you>/imx6ull/toolchains/arm-gnu-toolchain-<version>-x86_64-arm-none-linux-gnueabihf/bin/arm-none-linux-gnueabihf-gcc

$ arm-none-linux-gnueabihf-gcc --version | head -1
arm-none-linux-gnueabihf-gcc (Arm GNU Toolchain ...)

$ which arm-none-eabi-gcc
/home/<you>/imx6ull/toolchains/arm-gnu-toolchain-<version>-x86_64-arm-none-eabi/bin/arm-none-eabi-gcc

$ arm-none-eabi-gcc --version | head -1
arm-none-eabi-gcc (Arm GNU Toolchain ...)

$ which dtc mkimage picocom uuu
/usr/bin/dtc
/usr/bin/mkimage
/usr/bin/picocom
/usr/local/bin/uuu

$ systemctl is-active tftpd-hpa nfs-kernel-server
active
active

$ ls -d ~/imx6ull/{src,build,boot,rootfs,scripts,toolchains,notes}
/home/<you>/imx6ull/boot
/home/<you>/imx6ull/build
/home/<you>/imx6ull/notes
/home/<you>/imx6ull/rootfs
/home/<you>/imx6ull/scripts
/home/<you>/imx6ull/src
/home/<you>/imx6ull/toolchains
```

If any of these fail, do not move on. Subsequent chapters silently assume each.

## 3.12  Lab

Open a new terminal and source the environment script:

```sh
$ . ~/imx6ull/scripts/env.sh
```

Then prove the environment is local to this terminal:

```sh
$ echo "$CROSS_COMPILE"
arm-none-linux-gnueabihf-

$ echo "$BAREMETAL_CROSS_COMPILE"
arm-none-eabi-

$ command -v arm-none-linux-gnueabihf-gcc
/home/<you>/imx6ull/toolchains/arm-gnu-toolchain-<version>-x86_64-arm-none-linux-gnueabihf/bin/arm-none-linux-gnueabihf-gcc

$ command -v arm-none-eabi-gcc
/home/<you>/imx6ull/toolchains/arm-gnu-toolchain-<version>-x86_64-arm-none-eabi/bin/arm-none-eabi-gcc
```

Open another terminal and run `echo "$CROSS_COMPILE"` before sourcing the script. It should be empty. That is intentional: the book environment appears only when you ask for it.

## 3.13  Pitfalls

- **`tftp` blocked by firewall.** Ubuntu's UFW, if enabled, drops UDP/69 silently. `sudo ufw status` first.
- **NFS over Wi-Fi to a slow board.** Booting a kernel over NFS-root on Wi-Fi works but is brittle. If you see "VFS: Unable to mount root fs", it is almost always NFS timing out, not a real kernel bug. Use wired.
- **Forgot to source `env.sh`.** If `arm-none-linux-gnueabihf-gcc` or `arm-none-eabi-gcc` is not found, run `. ~/imx6ull/scripts/env.sh` in that terminal.
- **Wrong compiler on `PATH`.** `which arm-none-linux-gnueabihf-gcc` and `which arm-none-eabi-gcc` must both point inside `/home/<you>/imx6ull/toolchains/`. If either points into `/usr/bin`, fix the environment before building.
- **`dd` to the wrong device.** Every embedded engineer has done this once. Use the helper from §3.9 and you will only do it once.
- **`sudo` and environment variables.** `sudo CROSS_COMPILE=arm-none-linux-gnueabihf- make` does *not* pass `CROSS_COMPILE` unless `sudo`'s `env_reset` is disabled. Build without `sudo`. install with `sudo`.

## 3.14  Going deeper

- `man 8 exportfs`, `man 5 exports`, `man 8 tftpd`, `man 5 udev` — read the man pages of the services you just configured.
- `picocom`'s `-l` (lock-file) and `-i` (initstring) options are useful for scripting boot.
- *The TCP/IP Guide* (Charles Kozierok) on TFTP and NFS protocols if you want to know what is on the wire.
- If you intend to run a lot of cross-builds, look at `ccache` (`sudo apt install ccache`) and prepend it to `CROSS_COMPILE`: `CROSS_COMPILE="ccache arm-none-linux-gnueabihf-"`. We do *not* use it in this book because it occasionally masks subtle dependency bugs in Makefiles we're trying to read.

> Next chapter: **Chapter 4 — ARMv7-A and the Cortex-A7, for the MCU engineer.** We leave the host and start understanding the silicon we will program.
