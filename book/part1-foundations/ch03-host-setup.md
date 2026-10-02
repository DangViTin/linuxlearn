# Chapter 3: Host environment setup

> **What:** a Linux development host that can cross-compile for ARMv7-A, serve files over TFTP and NFS, communicate with the board over serial and USB-OTG, and recover a board that cannot boot from storage.
>
> **Why:** the host builds images, inspects their contents, and communicates with the board. Checking it first separates host setup failures from later firmware failures.
>
> **Focus:** know which compiler and device each command uses. This chapter checks the host; Chapter 9 proves that a program runs on the board. Network boot services are preparation for later U-Boot/Linux labs, not prerequisites for the LED lab.


## 3.1  Choosing the host

The reference host is **native x86_64 Ubuntu 22.04 LTS**, using its default Bash terminal. The compiler archives below run on x86_64 Linux, not Windows or an ARM64 host. Commands shown with `$` run as your normal user; do not type the prompt marker. `sudo` requests root credentials for that command and may ask for your login password. Password typing is not echoed.

A dedicated Ubuntu VM can isolate package and service changes from your everyday system. Before using one, arrange:

- USB attachment to the guest for the serial bridge, ROM SDP device, and card reader. Confirm each appears inside Ubuntu with `lsusb`/`lsblk`, not just in Windows. Reattach devices after re-enumeration if necessary.
- A bridged or passed-through Ethernet adapter on the board's lab link. Default VM NAT alone does not make guest TFTP/NFS servers reachable by the board.
- Only one owner for each serial port: close a Windows terminal before attaching its bridge to the guest.

Compiler files and selection are project-local. Package installation and the optional `/etc` service/network configuration are host changes; this chapter does not call those portable. If you want them confined to a lab machine, use the dedicated VM.

## 3.2  Workspace layout

Create the workspace before installing anything. The layout you set now will be referred to by every chapter:

```sh
$ mkdir -p ~/imx6ull/{src,build,boot,rootfs,scripts,toolchains,notes}
$ cd ~/imx6ull
$ ls
.
├── boot       # bootable artefacts staged here, then dd'd to SD
├── build      # all out-of-tree build outputs (kernel, U-Boot, BusyBox)
├── notes      # your lab journal, per-chapter
├── rootfs     # exported over NFS to the target
├── scripts    # helpers, shared between chapters
├── src        # upstream sources: linux, u-boot, busybox, your bare-metal code
└── toolchains # prebuilt Arm compilers kept local to this project
```

`~` means your home directory; `$HOME` is its shell-variable form. `mkdir -p` creates missing directories. Bash's `{src,build,...}` expands to one path per name. `cd` changes this terminal's working directory; `ls` lists its contents. The annotated tree above describes the resulting layout, not literal output from `ls`.

Two rules about this layout:

1. **Sources and outputs have different roles.** Edit tracked sources in `src/`, including your own bare-metal files. Git records source changes against upstream. Where a project supports `O=`, place generated output in `build/`; this does not move or apply source patches for you.
2. **`rootfs/` is the future NFS root.** Once the later lab exports it and Linux mounts it, the board uses files from this host directory without reflashing storage. Creating the directory alone does not configure NFS or boot the target.

## 3.3  Host packages

`apt update` refreshes Ubuntu's package catalog; `apt install` installs named packages and dependencies. These commands change the host. Read the proposed installation before answering its confirmation prompt. `-dev` packages contain headers/libraries needed to compile other programs.

```sh
$ sudo apt update
$ sudo apt install \
    build-essential bison flex libssl-dev libncurses-dev \
    bc kmod cpio rsync wget curl git unzip xz-utils \
    device-tree-compiler u-boot-tools \
    minicom picocom \
    qemu-user-static binfmt-support \
    gdb-multiarch \
    pkg-config libusb-1.0-0-dev libftdi1-dev \
    libgmp-dev libmpfr-dev libmpc-dev libisl-dev \
    fakeroot dosfstools mtools parted nano usbutils python3
```

What the main packages provide:

- **`build-essential`, `bison`, `flex`, `libssl-dev`, `libncurses-dev`** provide tools and libraries needed to build the kernel and U-Boot. The kernel uses OpenSSL during build for features such as module signing.
- **`bc`** provides arithmetic used by parts of the kernel build.
- **`device-tree-compiler`** provides `dtc`, the device-tree compiler.
- **`u-boot-tools`** provides `mkimage`, `mkenvimage`, `dumpimage`, and `mkeficapsule`.
- **`nfs-kernel-server`, `tftpd-hpa`** provide network boot services; install them later in Sections 3.6-3.7 when needed, because package installation can start daemons.
- **`minicom`, `picocom`** are serial terminals. This book uses `picocom`.
- **`qemu-user-static`, `binfmt-support`** let the host run ARM user-space binaries. This is useful when preparing a root filesystem with `chroot`.
- **`gdb-multiarch`** is a GDB build that supports multiple architectures, including ARM.
- **`libusb-1.0-0-dev`, `libftdi1-dev`** are needed when building USB and JTAG tools such as `imx_usb_loader` and OpenOCD.
- **OpenOCD** is the host program that controls a JTAG adapter and exposes a GDB server.
- **`fakeroot`, `dosfstools`, `mtools`, `parted`** manipulate filesystem and SD-card images.

If `apt` cannot find a package on the reference Ubuntu release, stop and record the exact error and release. Check that `apt update` succeeded; do not substitute a similarly named package without checking what it provides.

## 3.4  The cross toolchain

We need two prebuilt Arm toolchains:

- **Linux target toolchain:** `arm-none-linux-gnueabihf-`
  Builds U-Boot, the Linux kernel, BusyBox, and target user-space programs. It targets 32-bit Arm Linux with the hard-float glibc ABI.
- **Bare-metal toolchain:** `arm-none-eabi-`
  Builds the small no-OS experiments in Part II. It does not assume Linux, glibc, processes, or a dynamic loader.

We will install both toolchains in one project-local directory, give them unambiguous paths, and select the required toolchain explicitly for each build.

Use the **13.2.Rel1** release of both official Arm GNU Toolchains for this edition, rather than choosing different latest releases. This is a selected baseline, not a claim that every lab has been hardware-validated with it. Obtain the archives and their checksum manifests from [Arm's release downloads](https://developer.arm.com/downloads/-/arm-gnu-toolchain-downloads); the [13.2 release notes](https://documentation-service.arm.com/static/666180bfd72aaf32efecd262) list the host/target packages.

<https://developer.arm.com/downloads/-/arm-gnu-toolchain-downloads>

- `arm-gnu-toolchain-13.2.rel1-x86_64-arm-none-linux-gnueabihf.tar.xz`
- `arm-gnu-toolchain-13.2.rel1-x86_64-arm-none-eabi.tar.xz`

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
$ tar -xf arm-gnu-toolchain-13.2.rel1-x86_64-arm-none-linux-gnueabihf.tar.xz \
    -C ~/imx6ull/toolchains
$ tar -xf arm-gnu-toolchain-13.2.rel1-x86_64-arm-none-eabi.tar.xz \
    -C ~/imx6ull/toolchains
```
Before extracting, compare `sha256sum <archive-name>` with the matching Arm checksum manifest. Replace the placeholder with one actual filename; do not type angle brackets. Keep the manifests with the archives. After extraction, keep the directory names Arm supplied, including their capitalization:

```text
~/imx6ull/toolchains/arm-gnu-toolchain-<version>-x86_64-arm-none-linux-gnueabihf/bin/arm-none-linux-gnueabihf-gcc
~/imx6ull/toolchains/arm-gnu-toolchain-<version>-x86_64-arm-none-eabi/bin/arm-none-eabi-gcc
```

Those are the paths to remember when debugging build problems.

### Decoding the triplets

The names `arm-none-linux-gnueabihf` and `arm-none-eabi` are long because each part describes the target environment.

- `arm` means the target CPU family is 32-bit Arm.
- The middle `none` is the vendor field. Here it means no specific silicon vendor.
- `linux` means the generated program expects a Linux target environment.
- `gnu` means GNU userland and glibc ABI.
- `eabi` means Embedded ABI v5.
**ABI** - Application Binary Interface: the calling convention, register use, binary format, and library contract that let separately built code run together.
- `hf` means hard-float: floating-point arguments are passed in VFP registers.

The practical rule:

- Use `arm-none-linux-gnueabihf-` for this book's U-Boot, kernel, and Linux user-space builds. Only user-space builds use its glibc runtime; U-Boot/kernel choose their own freestanding build rules.
- Use `arm-none-eabi-` for our no-OS Part II experiments. Keep these two selections explicit even though some freestanding objects can be ABI-compatible across compiler families.

### Environment script

Do not edit `~/.bashrc` for this book. Hidden global shell state is convenient after you understand it, but it is bad for learning and can break unrelated projects.

Create one explicit environment script:

```sh
$ nano ~/imx6ull/scripts/env.sh
```

Put this in the file:

```sh
#!/bin/bash

IMX6ULL_HOME="$HOME/imx6ull"
linux_dirs=("$IMX6ULL_HOME"/toolchains/arm-gnu-toolchain-*-x86_64-arm-none-linux-gnueabihf)
bare_dirs=("$IMX6ULL_HOME"/toolchains/arm-gnu-toolchain-*-x86_64-arm-none-eabi)

if [ "${#linux_dirs[@]}" -ne 1 ] || [ ! -x "${linux_dirs[0]}/bin/arm-none-linux-gnueabihf-gcc" ]; then
    echo "Keep one extracted Linux toolchain in $IMX6ULL_HOME/toolchains."
    return 1
fi
if [ "${#bare_dirs[@]}" -ne 1 ] || [ ! -x "${bare_dirs[0]}/bin/arm-none-eabi-gcc" ]; then
    echo "Keep one extracted bare-metal toolchain in $IMX6ULL_HOME/toolchains."
    return 1
fi

export IMX6ULL_HOME
export ARM_LINUX_TOOLCHAIN="${linux_dirs[0]}"
export ARM_BAREMETAL_TOOLCHAIN="${bare_dirs[0]}"

export PATH="$ARM_LINUX_TOOLCHAIN/bin:$ARM_BAREMETAL_TOOLCHAIN/bin:$IMX6ULL_HOME/build/mfgtools/uuu:$PATH"

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

This file is sourced by **Bash**, not `sh`. It discovers the unchanged folder names and refuses missing or multiple matches before changing `PATH`. If a check fails, stop: inspect `toolchains/` and move old installations elsewhere before sourcing again. A failed re-source does not erase an environment already selected in this terminal.

The unfamiliar syntax has a small purpose:

- `name=value` assigns a variable; `$name` reads it. Quotes keep a path with spaces together.
- `*` matches the release part of the directory name. Each `(... )` collects matches into a Bash list. `${#linux_dirs[@]}` counts them; `${linux_dirs[0]}` reads the first.
- `[ ... ]` tests a condition. `-ne 1` means not equal to one, `-x` checks for an executable, and `||` means "or". `return 1` stops this sourced file with failure.
- `export` makes a variable available to programs started by this terminal. `PATH` is the colon-separated list of directories searched for commands, in order. The `uuu` directory is populated in Section 3.8.
- `TFTPROOT` and `NFSROOT` are convenient shell names; they do not configure the servers. `/etc` configuration must still be edited manually.

In `nano`, save with Ctrl-O, Enter, then exit with Ctrl-X.

Every time you open a new terminal for this book, run:

```sh
$ . ~/imx6ull/scripts/env.sh
```

That leading dot means "read this file into the current shell." Running `bash ~/imx6ull/scripts/env.sh` starts a child shell whose exports cannot change its parent; it is not the setup command. Direct execution may also fail because the file has not been made executable. Sourcing needs read permission, not an executable bit.

Verify both compilers and both prefixes:

```sh
$ command -v arm-none-linux-gnueabihf-gcc
/home/<you>/imx6ull/toolchains/arm-gnu-toolchain-<version>-x86_64-arm-none-linux-gnueabihf/bin/arm-none-linux-gnueabihf-gcc

$ arm-none-linux-gnueabihf-gcc --version | head -1
arm-none-linux-gnueabihf-gcc (Arm GNU Toolchain ...)

$ command -v arm-none-eabi-gcc
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

The Point Atom MINI includes a USB-to-TTL bridge connected to its debug UART. Connect the board's **USB-TTL** or **DEBUG USB** port to the host. Do not add an external serial adapter for the normal setup.

After connecting it, check which serial device appeared:

```sh
$ ls /dev/ttyUSB*
/dev/ttyUSB0
```

If that file does not exist, check `dmesg | tail`:

```sh
$ sudo dmesg | tail
[...] usb 1-1.2: new full-speed USB device number 5 using xhci_hcd
[...] usb 1-1.2: New USB device found, idVendor=10c4, idProduct=ea60
[...] cp210x 1-1.2:1.0: cp210x converter detected
[...] usb 1-1.2: cp210x converter now attached to ttyUSB0
```

On this host, the serial device normally restricts access to root and a group such as `dialout`. We leave user groups unchanged and use an explicit privileged command for each session. This is a teaching choice, not a rule that all hardware requires root. Log inspection may also need `sudo` on Ubuntu.

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

Quit with Ctrl-A then Ctrl-X. Plain Ctrl-C sends the interrupt character to the target; Ctrl-A then Ctrl-C instead toggles local echo. These keys follow [picocom's manual](https://raw.githubusercontent.com/npat-efault/picocom/master/picocom.1.md).

At this stage, a silent console is normal because we have not built a bootable image. If later output is unreadable, confirm 115200 8N1, check that you opened the correct serial device, and try another USB data cable.

If a board revision has no built-in USB-TTL bridge, use a separate **3.3 V** USB-TTL adapter on the UART header. Connect board TX to adapter RX, board RX to adapter TX, and GND to GND. Leave the adapter VCC pin disconnected.

### 3.5a  Windows-side serial terminals (for Windows-mainly readers)

For an optional Windows-side serial session, PuTTY provides a serial connection: select the bridge's COM port in Device Manager, choose Serial, and set 115200 8N1 with no flow control. This does not substitute for attaching USB devices to Ubuntu when using the Linux build/transfer commands.

Other optional terminals include:

- **MobaXterm** (`mobaxterm.mobatek.net`, free Home Edition) combines SSH, serial, X server, saved sessions, and SFTP.
- **SecureCRT** (`vandyke.com`, commercial) provides fast scrollback, saved sessions, and a configurable keymap.
- **PuTTY** (`putty.org`, free) provides a small serial and SSH client.
- **Tera Term** (`teratermproject.github.io`, free) provides serial access and a macro language.

The board's integrated bridge may use a CH340 or CP2102 device. Windows may need the corresponding driver from `wch.cn` or `silabs.com`. Linux normally includes both drivers.

When configuring any of these tools, the settings are the same we used for `picocom`: **115200 8N1, no flow control**.

### 3.5b  Source Insight as a kernel-source navigation aid (optional)

The Linux kernel source tree is ~80,000 files. Tools that index it on a fast SSD beat ones that don't.

- **Source Insight 4** (`sourceinsight.com`, commercial Windows) provides source indexing, Go to Definition, and call graphs.
- **VS Code + C/C++ extension** (Microsoft) is free and cross-platform. Use `compile_commands.json` from a kernel build so IntelliSense follows the correct include paths.
- **`cscope` + `ctags`** provide terminal-based source navigation and can be scripted.
- **`elixir.bootlin.com`** provides a web-based Linux source cross-reference without a local installation.

For this book, we do not require any of them. But if you find yourself spending more than five minutes hunting a kernel symbol, install one.

## 3.6  TFTP server

**Needed later, before network-loading from U-Boot.** You may skip Sections 3.6, 3.7, and 3.10 until Chapter 24. These services persist beyond the terminal; record existing configuration before editing it, and preserve unrelated settings. Do not expose them on a public or shared network.

The board's U-Boot will fetch kernel images from your host over TFTP.

Install the server package if you have not already:

```sh
$ sudo apt install tftpd-hpa tftp-hpa
```

Now open the server configuration:

```sh
$ SUDO_EDITOR=nano sudoedit /etc/default/tftpd-hpa
```

`SUDO_EDITOR=nano` chooses the familiar editor for this command only. `sudoedit` lets you edit a temporary copy as your normal user, then writes it back with authorization. Save and exit with the same nano keys used earlier; your shell's default editor is not changed.

Make the file look like this:

```text
TFTP_USERNAME="tftp"
TFTP_DIRECTORY="/srv/tftp"
TFTP_ADDRESS="192.168.7.1:69"
TFTP_OPTIONS="--secure"
```

What each line means:

- `TFTP_USERNAME="tftp"` runs the daemon as the unprivileged `tftp` user.
- `TFTP_DIRECTORY="/srv/tftp"` is the directory U-Boot will read files from.
- `TFTP_ADDRESS="192.168.7.1:69"` listens only on the host lab address and standard UDP port. Configure that address using Section 3.10 before restarting; router mode must use the actual host address.
- `TFTP_OPTIONS="--secure"` roots requests inside `/srv/tftp`. This book downloads existing files, so it does not enable new-file uploads with `--create`; that option would not grant filesystem write permission anyway.

Create the directory, make your normal user its owner, and keep it readable by the TFTP daemon:

```sh
$ sudo mkdir -p /srv/tftp
$ sudo chown "$USER:$(id -gn)" /srv/tftp
$ chmod 755 /srv/tftp
```

Why the permission change matters:

- `/srv` is a system directory. Without `sudo`, a normal user usually cannot create `/srv/tftp`.
- After `sudo mkdir`, the new directory is owned by `root`, so your normal user would need `sudo` every time you copy a kernel, device tree, or U-Boot image into it.
- `sudo chown "$USER:$(id -gn)" /srv/tftp` selects your user and actual primary group. `$()` substitutes command output; `id -gn` prints that group. Now you can stage files with normal `cp` commands. Change ownership only for this dedicated lab directory, not an existing shared service directory.
- The TFTP server does not run as your user. `TFTP_USERNAME="tftp"` means it runs as the low-privilege `tftp` user, so a bug in the TFTP server has less power on the host.
- `chmod 755 /srv/tftp` grants the owner read/write/execute and others read/execute. For a directory, read lists names and execute permits traversal to a named file; the file itself must separately be readable. Other ordinary users cannot add files, though root still can.

Files you copy into `/srv/tftp` also need to be readable by the TFTP daemon. Normal files created by `cp` or `echo` are usually readable already. If U-Boot gets "permission denied" from TFTP, check with:

```sh
$ ls -l /srv/tftp
```

If a staged file is not readable by `tftp`, change that file's mode, not the whole tree. The smoke test below demonstrates `chmod 644`: owner read/write, others read.

Restart for this lab session, without enabling automatic startup:

```sh
$ sudo systemctl restart tftpd-hpa
```

Smoke-test:

```sh
$ echo "hello tftp" > /srv/tftp/test.txt
$ chmod 644 /srv/tftp/test.txt
$ tftp 192.168.7.1 -c get test.txt
$ cat test.txt
hello tftp
```

The test writes a small file into the TFTP root, then asks this host's lab-address listener for it. Substitute your configured host address in router mode. The final `cat` proves the file came back; this is still a host-local test, not a board transfer.

This proves only the local daemon, path, and file permissions. It does not test the board, cable, VM reachability, or firewall path. The target TFTP test comes after U-Boot runs in Chapter 24.

**Firewall:** keep the existing firewall enabled. Inspect `sudo ufw status`; where UFW is active, allow the board only on the dedicated lab interface, substituting the interface name found in Section 3.10:

```sh
$ sudo ufw allow in on enp0s31f6 from 192.168.7.2 to 192.168.7.1 port 69 proto udp
```

TFTP uses additional UDP transfer ports; a stateful firewall must track the exchange or have a lab-interface rule appropriate to its policy. If the transfer stalls, inspect that path rather than disabling workstation protection. Stop the service with `sudo systemctl stop tftpd-hpa` after the lab; restore only the settings/rules you changed.

## 3.7  NFS server

The Linux kernel can mount its root filesystem over NFS during development. That lets you edit files on the host and reboot the board without rebuilding an SD-card image.

Install the server package if needed:

```sh
$ sudo apt install nfs-kernel-server
```

Open the export table:

```sh
$ SUDO_EDITOR=nano sudoedit /etc/exports
```

Add one line at the end. Replace `<you>` with your Linux username:

```text
/home/<you>/imx6ull/rootfs 192.168.7.2(rw,sync,no_root_squash,no_subtree_check)
```

Then apply and verify:

```sh
$ sudo exportfs -ar
$ sudo systemctl restart nfs-kernel-server
$ sudo showmount -e localhost
Export list for localhost:
/home/<you>/imx6ull/rootfs 192.168.7.2
```

What the commands do:

- `exportfs -ar` asks the NFS server to re-read `/etc/exports` and apply the export table.
- `systemctl restart nfs-kernel-server` restarts the NFS daemon so the kernel-side service is using the current config.
- `showmount -e localhost` checks the advertised export, not whether the target can mount or boot it. That requires the later kernel/rootfs lab.

The flags decoded:

- `rw` lets the target write to the exported filesystem.
- `sync` commits writes before the server replies. This is slower but reduces the chance of losing recent writes.
- `no_root_squash` maps the target's root user to host UID 0. This is convenient for a development root filesystem but unsafe on an untrusted network.
- `no_subtree_check` disables a subtree validation step that is not useful for this dedicated export.

**Security:** the client address narrows access; `*` would allow any matching client and is not used here. `no_root_squash` grants that client's root identity host-root access within the export, so use expendable lab files only, on an isolated link. IP restrictions are not authentication. Router mode must substitute the reserved board address and restrict firewall access to that board/interface. NFSv3 also uses RPC services; inspect the active ports with `rpcinfo -p localhost` rather than opening arbitrary ports to everyone. See [exports(5)](https://man7.org/linux/man-pages/man5/exports.5.html).

To undo this lab export, remove only its line from `/etc/exports` with `sudoedit`, then run `sudo exportfs -ar`. Stop `nfs-kernel-server` if no other exports need it. Do not erase a pre-existing export table or stop services other users require.

## 3.8  USB-OTG flashing tools

The i.MX6ULL Boot ROM speaks **SDP** (Serial Download Protocol) over its USB-OTG port. When the board's boot selector is in **USB mode**, the chip enumerates as a USB device and waits for the host to send an image. Two tools speak SDP:

### `uuu` (Universal Update Utility)

Use NXP's [uuu_1.5.201 release](https://github.com/nxp-imx/mfgtools/releases/tag/uuu_1.5.201), pinned instead of a moving branch. Build as your normal user into the workspace:

```sh
$ cd ~/imx6ull/src
$ git clone --branch uuu_1.5.201 --depth 1 https://github.com/nxp-imx/mfgtools
$ sudo apt install libusb-1.0-0-dev zlib1g-dev libbz2-dev pkg-config cmake libzstd-dev libtinyxml2-dev
$ cmake -S ~/imx6ull/src/mfgtools -B ~/imx6ull/build/mfgtools
$ cmake --build ~/imx6ull/build/mfgtools -j "$(nproc)"
$ . ~/imx6ull/scripts/env.sh
$ command -v uuu
/home/<you>/imx6ull/build/mfgtools/uuu/uuu
$ uuu -h
... help text and the selected release version ...
```

`-S` selects source files; `-B` selects build output. `nproc` prints the available CPU count for parallel building. No binary is installed in `/usr/local/bin`. The dependency list follows this release's [CMake requirements](https://github.com/nxp-imx/mfgtools/blob/uuu_1.5.201/uuu/CMakeLists.txt), including zlib and TinyXML2 development files.

We leave USB groups and udev rules unchanged. Use the full local path with `sudo`, because sudo's command search path may omit your workspace:

```sh
$ sudo "$IMX6ULL_HOME/build/mfgtools/uuu/uuu" -lsusb
```

Run this device check only after Chapter 8's power and USB-mode checks. `15a2:0080` is the ROM SDP identity. Enumeration proves device visibility, not successful image transfer or code execution. Read any flashing command before running it with root credentials.

## 3.9  SD card preparation for later chapters

Use a spare 4-32 GB SD card, class 10 or better, dedicated to this project. We will overwrite it many times. Do not write an image in this chapter.

Identify which device it is, **carefully**:

```sh
$ lsblk -o NAME,PATH,SIZE,MODEL,SERIAL,TRAN,RM,TYPE,MOUNTPOINTS
```

Read your actual output: `PATH` is the device path, `TYPE` distinguishes a whole `disk` from a `part` partition, and `MOUNTPOINTS` shows what is mounted. The later examples use `/dev/sdc` with a `/dev/sdc1` partition, but your card may have different names.

If you wipe the wrong block device you will lose your operating system. Check the size and the mount points twice before running `dd`.

Compare the device list before and after insertion. Match size, model/serial, and the newly appearing reader/card; `RM=1` alone is not proof. Reject a device containing `/`, `/boot`, swap, or unrelated mounted data. A host disk can be `/dev/sdb`; a card can be `/dev/sda` or `/dev/mmcblkN`. Disk letters do not establish safety.

**Preview only: do not run the following write commands in Chapter 3.** No image exists yet. Chapter 11 gives a real artifact and repeats identification. `/dev/sdc` below is an example observation, not a fixed name. Re-identify after every insertion.

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

When a later chapter supplies a full partitioned `sdcard.img`, its whole-card write has this form:

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
$ lsblk -o NAME,PATH,SIZE,MODEL,SERIAL,TYPE,MOUNTPOINTS
```

Identify the card again before interpreting its partitions. A partitioned Linux image should show the expected partition layout. The small Part II `.imx` image is different: it is a raw boot payload, not a filesystem/partitioned card image, so a partition listing does not verify it. Chapter 11 uses a byte-level readback. We do not supply an automatic disk-selection helper.

## 3.10  Host IP plan

For TFTP, NFS, and U-Boot experiments, the board must know how to reach the host. The important thing is not the exact address. The important thing is that the address stays stable.

There are two common setups.

### Option A: direct host-to-board link

Use this when your computer has a spare Ethernet port, a USB-to-Ethernet adapter, or Wi-Fi for internet plus Ethernet for the board.

In this book, the clean lab network is:

- Host: **192.168.7.1**
- Board: **192.168.7.2**

Use this private `192.168.7.0/24` subnet only if it does not overlap an existing LAN or VPN route. It avoids router DHCP changes when assigned to a dedicated adapter.

If you use NetworkManager:

```sh
$ sudo nmtui
```

In the text UI:

1. Choose **Edit a connection**.
2. Create a separate Ethernet connection named `imx-link` for the board adapter rather than overwriting your everyday connection. Find that adapter with `ip -br link`.
3. Set **IPv4 CONFIGURATION** to **Manual**.
4. Add address `192.168.7.1/24`.
5. Leave gateway and DNS empty for this direct board link.
6. Save and activate the connection. This creates a persistent host profile. After the lab, deactivate it and reactivate your previous profile; remove only `imx-link` if it is no longer needed.

`enp0s31f6` below is an example host interface name, not the board interface. Substitute your adapter's actual name.

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

Reserve the host address as well as the board address in the router, or use documented unused static addresses outside its DHCP pool. Update `HOST_IP`/`BOARD_IP` in `env.sh`, the TFTP bind address, and the NFS client address consistently. For the board address:

- Reserve a fixed DHCP address for the board in your router.
- Let U-Boot request DHCP, then read the assigned address.
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

Chapter 8 checks physical Ethernet presence only. Target ping and TFTP tests wait until U-Boot runs; NFS-root acceptance waits until Linux and a complete rootfs exist.

## 3.11  Sanity check

Required-now checklist: compiler commands must resolve inside the workspace. Output below is schematic; record your actual release strings and paths.

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
/home/<you>/imx6ull/build/mfgtools/uuu/uuu

$ ls -d ~/imx6ull/{src,build,boot,rootfs,scripts,toolchains,notes}
/home/<you>/imx6ull/boot
/home/<you>/imx6ull/build
/home/<you>/imx6ull/notes
/home/<you>/imx6ull/rootfs
/home/<you>/imx6ull/scripts
/home/<you>/imx6ull/src
/home/<you>/imx6ull/toolchains
```

Before Part II, also identify the serial bridge and confirm Chapter 8's ROM USB enumeration. A silent UART is not a failed host setup. Record card identity without writing it.

For later network labs only, check both services with `systemctl is-active tftpd-hpa nfs-kernel-server`, the host address, host-local TFTP retrieval at that address, and the narrowed NFS export. These host checks do not replace target transfers/boots and need not block Chapter 9.

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

Open another terminal from the desktop, not from the already-configured shell, and run `echo "$CROSS_COMPILE"` before sourcing. With no prior setup it should be empty. A child terminal can inherit its parent's exported variables, so an inherited value is not evidence of a `.bashrc` change.

## 3.13  Pitfalls

- **`tftp` blocked by firewall.** Ubuntu's UFW, if enabled, drops UDP/69 silently. `sudo ufw status` first.
- **NFS-root failure.** Prefer the wired lab link. For "VFS: Unable to mount root fs", inspect the full preceding error, `root=`/`nfsroot=`/`ip=` arguments, built-in NFS/network support, host exports/firewall, and rootfs contents. That message alone does not identify a timeout.
- **Forgot to source `env.sh`.** If `arm-none-linux-gnueabihf-gcc` or `arm-none-eabi-gcc` is not found, run `. ~/imx6ull/scripts/env.sh` in that terminal.
- **Wrong compiler on `PATH`.** `which arm-none-linux-gnueabihf-gcc` and `which arm-none-eabi-gcc` must both point inside `/home/<you>/imx6ull/toolchains/`. If either points into `/usr/bin`, fix the environment before building.
- **Wrong storage destination.** Stop if identity is uncertain. No disk-letter filter can distinguish a spare card from a host disk; repeat identification and unmount checks at each write.
- **Building with `sudo`.** Build as the normal user. Plain `sudo make` may lose inherited compiler selection and creates root-owned output. Explicit assignments such as `sudo CROSS_COMPILE=...` can work subject to sudo policy, but are not a reason to build as root or disable `env_reset`. Use `sudo` only for the specific restricted operation.

## 3.14  Going deeper

- `man 8 exportfs`, `man 5 exports`, and `man 8 tftpd` explain the optional services configured in this chapter.
- In picocom, `-l` disables locking, `-i` skips initialization, and `-t` sends an initialization string. They are not needed for the normal console command; do not add options without checking the manual.
- *The TCP/IP Guide* (Charles Kozierok) on TFTP and NFS protocols if you want to know what is on the wire.
- If you intend to run a lot of cross-builds, look at `ccache` (`sudo apt install ccache`) and prepend it to `CROSS_COMPILE`: `CROSS_COMPILE="ccache arm-none-linux-gnueabihf-"`. We do *not* use it in this book because it occasionally masks subtle dependency bugs in Makefiles we're trying to read.

> Next chapter: **Chapter 4: ARMv7-A and the Cortex-A7 for the MCU engineer.** We leave the host and examine the CPU architecture we will program.
