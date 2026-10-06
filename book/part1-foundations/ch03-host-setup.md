# Chapter 3: Host environment setup

A new terminal can look exactly like the last one and still choose a different compiler. It can even report "command not found" while the compiler files are sitting where you left them. The files and the terminal's knowledge of them are two different things.

An MCU IDE usually keeps that distinction out of sight by choosing tools with the project. Here we make the choice ourselves. The computer on your desk is the **host**: it edits and builds the code, inspects the result, and sends it to the i.MX6ULL **target** board. Our first job is to give the files a known home and make each terminal's tool selection visible.

For Part II we need a workspace, two compilers, a serial terminal, and a USB download tool. We will also identify a spare SD card without writing it. TFTP, NFS, and the Ethernet address plan serve later network-boot labs; Sections 3.6, 3.7, and 3.10 can wait until Chapter 24. As we set up the immediate tools, keep two questions in mind: where did the file go, and which program will this terminal run?

## 3.1  Choosing the host

We use **x86_64 Ubuntu 22.04 LTS** and its default Bash terminal as the reference host. The compiler archives in this chapter run on x86_64 Linux, so they cannot be launched directly in Windows or on an ARM64 host. Start with Ubuntu installed, either natively or in a dedicated virtual machine.

Open Ubuntu's Terminal application. This is where the host commands in the book belong. A `$` at the start of a listing is a prompt marker, not a character to type. Most commands run as your normal user. When a command needs authorization to change a system file or access a restricted device, we show `sudo` explicitly. It may ask for your login password; the terminal displays no characters while you type it.

A dedicated VM keeps package and service changes inside that lab system. It still needs access to the physical board. Before relying on one, check these connections:

- USB attachment to the guest for the serial bridge, ROM SDP device, and card reader. Confirm each appears inside Ubuntu with `lsusb`/`lsblk`, not just in Windows. Reattach devices after re-enumeration if necessary.
- A bridged or passed-through Ethernet adapter on the board's lab link. Default VM NAT alone does not make guest TFTP/NFS servers reachable by the board.
- Only one owner for each serial port: close a Windows terminal before attaching its bridge to the guest.

We can keep compiler files and compiler selection local to the project. Ubuntu packages and the optional service settings under `/etc` are different: they change the host system and remain after the terminal closes. Use the dedicated VM if you want those changes kept off your everyday installation.

## 3.2  Workspace layout

Consider the next time a build fails and you need to find the source you edited. It helps if that file is not buried among yesterday's generated objects and downloaded archives. We use `~/imx6ull` to keep those roles separate. The layout below will stay with us as the projects grow:

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

Read the first command before entering it. `~` means your home directory, and Bash expands `{src,build,...}` into one path for each name. `mkdir -p` creates those directories if they are missing. Then `cd` moves this terminal into the workspace and `ls` lists what is there. The annotated tree shows what the names mean; ordinary `ls` does not print that tree or its comments.

You will also see `$HOME`, the shell-variable form of your home-directory path. It lets the environment file below refer to your directory without embedding a particular username.

Two distinctions will save confusion later:

1. **Sources and outputs have different roles.** Edit tracked sources in `src/`, including your own bare-metal files. Git records source changes against upstream. Where a project supports `O=`, place generated output in `build/`; this does not move or apply source patches for you.
2. **`rootfs/` is the future NFS root.** Once the later lab exports it and Linux mounts it, the board uses files from this host directory without reflashing storage. Creating the directory alone does not configure NFS or boot the target.

## 3.3  Host packages

Not every program used during an Arm build runs on Arm. The host also runs tools that process configuration, generate source, and package files. Ubuntu supplies these helpers through its package manager, `apt`. The long installation below prepares those host jobs; our two Arm compilers will still be downloaded separately into the workspace.

`apt update` refreshes the package catalog; `apt install` installs the named packages and their dependencies. Read the proposed installation before answering its confirmation prompt. Packages ending in `-dev` generally supply headers and libraries needed to compile another program. These installations change Ubuntu, rather than just the project directory.

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

The list is long because it covers several later builds. You do not need to learn every package now, but the main groups have recognizable jobs:

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

The name `gcc` tells you which compiler family you called, not which processor its output will run on. Ubuntu's ordinary `gcc` builds for the host PC. For our board, we need a compiler that runs on the PC but produces Arm instructions. That is a **cross-compiler**. Its linker, assembler, and inspection tools form a **toolchain**. Chapter 6 will make this difference visible by building the same C source for two targets.

We use two official prebuilt Arm toolchains because the target environments differ:

- **Linux target toolchain:** `arm-none-linux-gnueabihf-`
  Builds U-Boot, the Linux kernel, BusyBox, and target user-space programs. It targets 32-bit Arm Linux with the hard-float glibc ABI.
- **Bare-metal toolchain:** `arm-none-eabi-`
  Builds the small no-OS experiments in Part II. It does not assume Linux, glibc, processes, or a dynamic loader.

Both archives go into the workspace, with their original directory names. We will not install another Arm compiler through `apt` or rename these folders. Keeping the two paths visible makes it easier to check which tool a build actually used.

Use **13.2.Rel1** for both targets in this edition. A fixed release gives us the same starting point when comparing build results; it is not a claim that every lab has been tested on hardware with that release. Download these two archives and their matching checksum manifests from [Arm's release page](https://developer.arm.com/downloads/-/arm-gnu-toolchain-downloads). The [13.2 release notes](https://documentation-service.arm.com/static/666180bfd72aaf32efecd262) identify the host and target packages.

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

Before extracting, use `sha256sum <archive-name>` to calculate each archive's checksum and compare it with the matching Arm manifest. Here `<archive-name>` is a placeholder: replace it with the actual filename and omit the angle brackets. Keep the manifests beside the archives.

Then extract them into `~/imx6ull/toolchains`, not a system directory such as `/opt`. The compiler files remain part of the workspace, and removing this workspace does not remove a compiler another project installed globally.

```sh
$ mkdir -p ~/imx6ull/toolchains
$ tar -xf arm-gnu-toolchain-13.2.rel1-x86_64-arm-none-linux-gnueabihf.tar.xz \
    -C ~/imx6ull/toolchains
$ tar -xf arm-gnu-toolchain-13.2.rel1-x86_64-arm-none-eabi.tar.xz \
    -C ~/imx6ull/toolchains
```

After extraction, keep the directory names Arm supplied, including their capitalization. The two compiler executables are inside the corresponding `bin` directories:

```text
~/imx6ull/toolchains/arm-gnu-toolchain-<version>-x86_64-arm-none-linux-gnueabihf/bin/arm-none-linux-gnueabihf-gcc
~/imx6ull/toolchains/arm-gnu-toolchain-<version>-x86_64-arm-none-eabi/bin/arm-none-eabi-gcc
```

If a later build reports the wrong compiler, these are the paths to check first.

### Decoding the triplets

The long prefixes tell us more than "this is an Arm compiler." They describe the environment the output is intended to use. **ABI**, or Application Binary Interface, means the agreement about calling conventions, register use, binary format, and runtime libraries that lets separately built code work together.

- `arm` means the target CPU family is 32-bit Arm.
- The middle `none` is the vendor field. Here it means no specific silicon vendor.
- `linux` means the generated program expects a Linux target environment.
- `gnu` means GNU userland and glibc ABI.
- `eabi` means Embedded ABI v5.
- `hf` means hard-float: floating-point arguments are passed in VFP registers.

You do not need to reconstruct these names at every build. For this book, the selection is:

- Use `arm-none-linux-gnueabihf-` for this book's U-Boot, kernel, and Linux user-space builds. Only user-space builds use its glibc runtime; U-Boot/kernel choose their own freestanding build rules.
- Use `arm-none-eabi-` for our no-OS Part II experiments. Keep these two selections explicit even though some freestanding objects can be ABI-compatible across compiler families.

### Environment script

We now have the compiler files. What is still missing? When you enter a program name, Bash searches the directories listed in a variable called `PATH`; it does not search the whole disk. This is how a terminal can fail to find a compiler that is plainly present in the file manager. One small file, `env.sh`, will add the right directories for the current terminal.

Leave `~/.bashrc` unchanged. Putting the setup there would select these tools automatically in future terminals, including terminals used for other work. Instead, we will make the selection visible each time we begin a book session.

Create the file with the editor:

```sh
$ nano ~/imx6ull/scripts/env.sh
```

Enter the following contents. The first part finds one directory for each target; the remaining lines give this terminal the paths and names used by later builds:

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

Use this file with **Bash**, not `sh`. The two checks catch a common setup mistake: having no matching compiler, or having several releases and accidentally choosing one. If a check fails, inspect `toolchains/` and move old installations elsewhere before trying again. The file stops before changing `PATH`; it does not clear a selection already present in the terminal.

There is no need to learn Bash scripting in full to understand this file. Read its parts in order:

- `name=value` assigns a variable; `$name` reads it. Quotes keep a path with spaces together.
- `*` matches the release part of the directory name. Each `(... )` collects matches into a Bash list. `${#linux_dirs[@]}` counts them; `${linux_dirs[0]}` reads the first.
- `[ ... ]` tests a condition. `-ne 1` means not equal to one, `-x` checks for an executable, and `||` means "or". `return 1` stops this sourced file with failure.
- `export` makes a variable available to programs started by this terminal. `PATH` is the colon-separated list of directories searched for commands, in order. The `uuu` directory is populated in Section 3.8.
- `TFTPROOT` and `NFSROOT` are convenient shell names; they do not configure the servers. `/etc` configuration must still be edited manually.

In `nano`, press Ctrl-O and then Enter to save. Press Ctrl-X to return to the terminal.

Every time you open a new terminal for this book, run:

```sh
$ . ~/imx6ull/scripts/env.sh
```

The leading dot matters. It tells Bash to read the file **into this shell**, which is called *sourcing* the file. Its exported values then apply to commands you run in this terminal.

If you instead enter `bash ~/imx6ull/scripts/env.sh`, the file runs in a child shell. That child's settings cannot change the terminal you return to afterward. We also do not need to make `env.sh` executable: sourcing reads it as a file rather than launching it as a separate program.

```{figure} ../illustrations/part1/03-terminal-environment.png
:alt: Sourcing env.sh adds the bare-metal and Linux toolchain paths to this terminal. Another independent terminal is not changed by that operation and needs its own setup.
:width: 100%
:figclass: concept-sketch
:name: fig-terminal-environment

The compiler files have not moved. We have told one shell where to look for them. Source `~/imx6ull/scripts/env.sh` in each independently opened Bash terminal used for the book; a child shell can inherit exported settings, but another already-open terminal does not receive them.
```

Ask the terminal what it selected before trusting a build. `command -v` reports the executable found through `PATH`; the version commands identify it. Both paths should lead into this workspace:

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

Those paths answer the puzzle at the start of the chapter. The files live in the workspace; sourcing `env.sh` makes this terminal find them. A terminal that has not inherited those values needs its own selection. Keep that distinction when a command later works in one window and fails in another.

The trailing hyphen in each prefix is intentional. Build systems append names such as `gcc` or `objcopy` to it. U-Boot, Linux, and BusyBox use `CROSS_COMPILE`; our own bare-metal Makefiles use the separate `BAREMETAL_CROSS_COMPILE` name.

## 3.5  Serial console

The serial console will be our way to see what the board prints. The MINI already has a USB-to-TTL bridge connected to its debug UART, so normal setup does not need an external adapter or jumper wires. Use the port labeled **USB-TTL** or **DEBUG USB**, not USB-OTG.

Before attaching a cable to an unfamiliar board, follow Chapter 8's power-arrangement check. A USB cable carries power as well as data. Once that arrangement is established, the following commands identify and open the bridge on the host.

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

Finding the device and having permission to open it are separate steps. On this host, access is normally restricted to root and a group such as `dialout`. We leave your groups unchanged and show `sudo` for each serial session. Ubuntu may also restrict the kernel log read by `dmesg`.

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

"Terminal ready" means the host opened the port; it does not promise a message from the board. Our own bootable image does not exist yet, so silence is normal. A pre-installed factory image may print something; save that output if it does. Later, when our UART program is supposed to print, unreadable text is a reason to check 115200 8N1, the device path, and the USB cable.

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

When we reach the kernel sources, following a function across many files can be slow in an ordinary editor. A source-navigation tool can help with that later; it is not another prerequisite for host setup.

- **Source Insight 4** (`sourceinsight.com`, commercial Windows) provides source indexing, Go to Definition, and call graphs.
- **VS Code + C/C++ extension** (Microsoft) is free and cross-platform. Use `compile_commands.json` from a kernel build so IntelliSense follows the correct include paths.
- **`cscope` + `ctags`** provide terminal-based source navigation and can be scripted.
- **`elixir.bootlin.com`** provides a web-based Linux source cross-reference without a local installation.

Use whichever of these you already know, or defer the choice until you need it. For the small files in Part I, `nano` is enough.

## 3.6  TFTP server

Once U-Boot is running, think about the next ten kernel builds. Moving the card from board to host and back for every image soon becomes more work than the small code change you wanted to test. **TFTP** lets U-Boot fetch the file from the host over Ethernet instead. This section prepares that host service; it can wait until Chapter 24.

Unlike `env.sh`, a network service continues independently of this terminal. Keep a record of the existing configuration, preserve unrelated settings, and use an isolated lab link. Work through the address plan in Section 3.10 before restarting a server bound to that address. Do not expose these services on a public or shared network.

Install the server package if you have not already:

```sh
$ sudo apt install tftpd-hpa tftp-hpa
```

Now open the server configuration:

```sh
$ SUDO_EDITOR=nano sudoedit /etc/default/tftpd-hpa
```

`SUDO_EDITOR=nano` chooses the familiar editor for this command only. `sudoedit` lets you edit a temporary copy as your normal user, then writes it back with authorization. Save and exit with the same nano keys used earlier; your shell's default editor is not changed.

Set the four fields as follows for the direct-link address plan:

```text
TFTP_USERNAME="tftp"
TFTP_DIRECTORY="/srv/tftp"
TFTP_ADDRESS="192.168.7.1:69"
TFTP_OPTIONS="--secure"
```

Each line answers one setup question:

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

There are two users involved here, and they want different things. You need to put new images in the directory. The `tftp` service needs to read them, but does not need your authority to change the host. The ownership and permission commands arrange that distinction:

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

Before involving the board, retrieve one small file from the host's own server:

```sh
$ echo "hello tftp" > /srv/tftp/test.txt
$ chmod 644 /srv/tftp/test.txt
$ tftp 192.168.7.1 -c get test.txt
$ cat test.txt
hello tftp
```

`echo` creates the test file; the TFTP client then requests it through the configured host address. Finally, `cat` displays the downloaded contents. Use your actual host address in router mode.

If this works, the local service can read and serve the file. The board-to-host cable, firewall path, and VM reachability still need a target transfer. We make that check after U-Boot runs in Chapter 24.

**Firewall:** keep the existing firewall enabled. Inspect `sudo ufw status`; where UFW is active, allow the board only on the dedicated lab interface, substituting the interface name found in Section 3.10:

```sh
$ sudo ufw allow in on enp0s31f6 from 192.168.7.2 to 192.168.7.1 port 69 proto udp
```

TFTP uses additional UDP transfer ports; a stateful firewall must track the exchange or have a lab-interface rule appropriate to its policy. If the transfer stalls, inspect that path rather than disabling workstation protection. Stop the service with `sudo systemctl stop tftpd-hpa` after the lab; restore only the settings/rules you changed.

## 3.7  NFS server

TFTP saves us a trip with the SD card, but it still transfers individual files. What if Linux could use a directory on the host as its root filesystem? **NFS**, the Network File System, allows that. During development, the host can hold the target's files, and the board can read an updated file without needing a new SD-card image.

We will not boot that way until the later kernel and root-filesystem labs. For now, if you are preparing networking, tell the host which directory the board may access.

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

The options in the export line determine what that access means:

- `rw` lets the target write to the exported filesystem.
- `sync` commits writes before the server replies. This is slower but reduces the chance of losing recent writes.
- `no_root_squash` maps the target's root user to host UID 0. This is convenient for a development root filesystem but unsafe on an untrusted network.
- `no_subtree_check` disables a subtree validation step that is not useful for this dedicated export.

**Security:** the client address narrows access; `*` would allow any matching client and is not used here. `no_root_squash` grants that client's root identity host-root access within the export, so use expendable lab files only, on an isolated link. IP restrictions are not authentication. Router mode must substitute the reserved board address and restrict firewall access to that board/interface. NFSv3 also uses RPC services; inspect the active ports with `rpcinfo -p localhost` rather than opening arbitrary ports to everyone. See [exports(5)](https://man7.org/linux/man-pages/man5/exports.5.html).

To undo this lab export, remove only its line from `/etc/exports` with `sudoedit`, then run `sudo exportfs -ar`. Stop `nfs-kernel-server` if no other exports need it. Do not erase a pre-existing export table or stop services other users require.

## 3.8  USB-OTG flashing tools

Our first program cannot depend on a bootloader we have not built yet. Fortunately, there is already code in the chip: the Boot ROM. In USB boot mode it exposes **SDP**, the Serial Download Protocol, through USB-OTG and waits for a host tool to send an image. We use NXP's `uuu` to reach that starting point, even when storage has no working image.

### `uuu` (Universal Update Utility)

Build NXP's [uuu_1.5.201 release](https://github.com/nxp-imx/mfgtools/releases/tag/uuu_1.5.201) inside the workspace. Selecting a release keeps these instructions tied to known sources. The package-install command needs `sudo`; the source checkout and build run as your normal user:

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

`cmake -S ... -B ...` reads sources from one directory and generates the build in another. The next command performs that build; `nproc` supplies the available CPU count for parallel jobs. The result stays under `build/mfgtools`, with no installation into `/usr/local/bin`. The dependency list comes from this release's [CMake requirements](https://github.com/nxp-imx/mfgtools/blob/uuu_1.5.201/uuu/CMakeLists.txt), including zlib and TinyXML2 development files.

The final path is worth noticing: the build directory contains a subdirectory named `uuu`, and the executable inside it is also named `uuu`. For restricted USB access, we leave groups and udev rules unchanged and use `sudo`. Give it the full local path because its command search path may not include our workspace:

```sh
$ sudo "$IMX6ULL_HOME/build/mfgtools/uuu/uuu" -lsusb
```

Run this device check only after Chapter 8's power and USB-mode checks. `15a2:0080` is the ROM SDP identity. Enumeration proves device visibility, not successful image transfer or code execution. Read any flashing command before running it with root credentials.

## 3.9  SD card preparation for later chapters

Choose a spare 4-32 GB SD card, class 10 or better, with no data you need to keep. Later we will write images over its contents. Today's task is only to recognize the card on the host; there is no image to write yet.

Identify which device it is, **carefully**:

```sh
$ lsblk -o NAME,PATH,SIZE,MODEL,SERIAL,TRAN,RM,TYPE,MOUNTPOINTS
```

Read your actual output: `PATH` is the device path, `TYPE` distinguishes a whole `disk` from a `part` partition, and `MOUNTPOINTS` shows what is mounted. The later examples use `/dev/sdc` with a `/dev/sdc1` partition, but your card may have different names.

Here, a command finishing successfully can be the wrong result. `dd` can write perfectly good image bytes to a perfectly valid device path that happens to be your system disk. It cannot decide which disk you meant. Compare identity, size, and mount points before every write, not just during this first setup.

Compare the device list before and after insertion. Match size, model/serial, and the newly appearing reader/card; `RM=1` alone is not proof. Reject a device containing `/`, `/boot`, swap, or unrelated mounted data. A host disk can be `/dev/sdb`; a card can be `/dev/sda` or `/dev/mmcblkN`. Disk letters do not establish safety.

**The following write commands are a preview; do not run them in Chapter 3.** They explain the manual workflow we will use when Chapter 11 supplies an image. `/dev/sdc` is an example, not a destination to copy from the book. Re-identify the card after every insertion.

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

For TFTP, NFS, and U-Boot experiments, the board needs an address for the host. That address must stay stable so a working command does not suddenly point to the wrong machine.

Choose the arrangement that matches your desk. The direct link is the isolated lab setup used in our examples; a router-connected setup needs its own consistent addresses.

### Option A: direct host-to-board link

Use this when your computer has a spare Ethernet port, a USB-to-Ethernet adapter, or Wi-Fi for internet plus Ethernet for the board.

For the direct link, our example addresses are:

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
- Choose an unused static address outside the router's DHCP pool.

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

Return to a fresh terminal and follow the selection from beginning to end: source `env.sh`, find both compilers, and find `uuu`. The listings below show the shape of the output. Your own paths and version strings are the evidence to keep; the placeholders are not output you need to reproduce.

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

Check that this terminal has selected the two project-local compilers:

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

Now open another terminal from the desktop, rather than launching it from the configured shell. Before sourcing the file, try `echo "$CROSS_COMPILE"` there. With no prior setup, it should be empty. Source `env.sh` and check again.

The compiler files did not move during that comparison. Only the second terminal's selection changed. A child terminal can inherit its parent's exported values, so an inherited value alone does not mean `.bashrc` was edited. Record the two compiler paths and the sourcing command in your notes. If the tools disappear from a future window, you now have a specific setting to inspect before downloading them again.

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
- For frequent cross-builds, `ccache` can reuse previous compilation results. Leave it out of the first experiments so the compile commands and rebuild decisions remain easy to follow. Add it later only after checking how the project's build system selects its compiler.

We can now trace a compiler name to a real file and explain why we source the environment script at the start of a session. The next uncertainty is on the other end of the build. The Cortex-A7 accepts familiar-looking instructions, but it does not enter an interrupt like a Cortex-M. That difference is where Chapter 4 begins.
