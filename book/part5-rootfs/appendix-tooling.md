---
title: "Appendix: Userspace tooling reference"
part: V — Root filesystem & user space
status: draft
---

# Appendix — Userspace tooling reference

> **What this is.** Throughout the book, chapters reach for `bluetoothctl`, `nmcli`, `gst-launch-1.0`, `alsamixer`, `wpa_supplicant`, `i2c-tools`, `mosquitto-clients`, `tcpdump`, `iperf3`, `gpsd`, `chrony`, `libnfc`, `mtd-utils`, `gdbserver`, … without saying where they come from. They come from **whatever rootfs you built or chose**. This appendix collects every tool referenced anywhere in the book and tells you how to install it on the three rootfs paths.
>
> **TL;DR.** During *learning*, use **Ubuntu-base (Ch 35A)** and `apt install ...`. When you *ship*, use **Buildroot (Ch 35)** and flip the corresponding Kconfig flag. **BusyBox-only (Ch 31)** does not have most of these.

## A.1  Three rootfs paths, briefly recapped

| Rootfs | Size | Get tools by | Best for |
|---|---|---|---|
| **BusyBox hand-built** (Ch 31) | ~3 MB | hand-cross-compile each tool; mostly not worth it | "Hello, world" + learning the boot pipeline |
| **Buildroot** (Ch 35) | 30–80 MB | `make menuconfig` → flip `BR2_PACKAGE_*` → rebuild | Production shipping |
| **Ubuntu-base** (Ch 35A) | ~600 MB | `apt install <name>` on the target | Learning, prototyping, dev kit |

The choice is not permanent. Many teams develop a feature on Ubuntu-base, validate, then port the same configuration to Buildroot for the shipping image.

## A.2  Why BusyBox-only doesn't get you very far

BusyBox is one binary with ~240 *applets* (`ls`, `sh`, `mount`, `ip`, `mdev`, …). It covers the GNU coreutils + a slice of net-tools + sysvinit. What it does **not** contain is *anything specialised*: no `alsa-utils`, no `bluez`, no `gstreamer`, no `chrony`, no `gdbserver`. The applet list is fixed at compile time. Adding `bluetoothctl` to a BusyBox-only system means cross-compiling BlueZ separately and installing it next to BusyBox — which is what Buildroot does for you with one Kconfig flag.

Reach for BusyBox-only when the goal is to *understand* what an init does and what a rootfs minimum looks like. Once you want to *do something* with hardware (audio, BT, WiFi, modem, GPS, …) you need either Buildroot or Ubuntu-base.

## A.3  Tool index — every name used in this book

For each tool: **what it is**, **chapters that use it**, **Ubuntu-base install**, **Buildroot Kconfig**, and a short note.

### Networking + iproute2

| Tool | Chapters | Ubuntu-base | Buildroot |
|---|---|---|---|
| `ip` (iproute2) | 52, 55C, 91–94, 102, 108, 115 | preinstalled | `BR2_PACKAGE_IPROUTE2=y` |
| `dhclient`, `dhcpcd` | 24, 52, 91–93 | preinstalled / `apt install isc-dhcp-client` | `BR2_PACKAGE_DHCPCD=y` |
| `ifupdown` (`ifup`, `ifdown`) | various | `apt install ifupdown` | `BR2_PACKAGE_IFUPDOWN=y` |
| `NetworkManager` (`nmcli`) | 91–94, 102 | `apt install network-manager` | `BR2_PACKAGE_NETWORK_MANAGER=y` |
| `tcpdump` | 24, 52, 102, 108, 115 | `apt install tcpdump` | `BR2_PACKAGE_TCPDUMP=y` |
| `iperf3` | 52, 55E, 91–94, 115 | `apt install iperf3` | `BR2_PACKAGE_IPERF3=y` |
| `ethtool` | 52, 115 | `apt install ethtool` | `BR2_PACKAGE_ETHTOOL=y` |
| `ss` (sockstat) | 52, 102, 120 | preinstalled | `BR2_PACKAGE_IPROUTE2=y` (bundled) |
| `nfs-kernel-server` (host) | 24, 31, 35A | `apt install nfs-kernel-server` | n/a (host-only) |
| `tftpd-hpa` (host) | 24, 26 | `apt install tftpd-hpa` | n/a (host-only) |

### WiFi + wireless

| Tool | Chapters | Ubuntu-base | Buildroot |
|---|---|---|---|
| `wpa_supplicant` | 55E, 91–94 | `apt install wpasupplicant` | `BR2_PACKAGE_WPA_SUPPLICANT=y` |
| `iw` | 91–94 | `apt install iw` | `BR2_PACKAGE_IW=y` |
| `hostapd` (AP mode) | 91 | `apt install hostapd` | `BR2_PACKAGE_HOSTAPD=y` |
| `wireless-regdb` | 91 | preinstalled | `BR2_PACKAGE_WIRELESS_REGDB=y` |
| `crda` (legacy regdb tool) | 91 | preinstalled (deprecated, merged into kernel) | typically not needed on modern kernels |
| WiFi firmware blobs | 91–94 | `apt install firmware-realtek firmware-brcm80211 …` | `BR2_PACKAGE_RTL_BT_FIRMWARE=y`, etc. (one per chip) |

### Bluetooth

| Tool | Chapters | Ubuntu-base | Buildroot |
|---|---|---|---|
| BlueZ stack (`bluetoothd`) | 95–97 | `apt install bluez` | `BR2_PACKAGE_BLUEZ5_UTILS=y` |
| `bluetoothctl` | 95–97 | bundled with bluez | bundled |
| `btmon`, `btmgmt`, `hciattach` | 95–97 | `apt install bluez-tools` | `BR2_PACKAGE_BLUEZ5_UTILS_DEPRECATED=y` (legacy `hciconfig`/`hcitool`) |
| `bluetooth-meshd` + `mesh-cfgclient` | 97 | `apt install bluez-meshd` (Ubuntu 22.04+) | `BR2_PACKAGE_BLUEZ5_UTILS=y` + experimental mesh support |
| Pre-built BT firmware | 95–97 | `apt install firmware-misc-nonfree` | per-chip firmware package |

### Cellular (modems)

| Tool | Chapters | Ubuntu-base | Buildroot |
|---|---|---|---|
| `pppd` + `chat` | 24, 55F, 103 | `apt install ppp` | `BR2_PACKAGE_PPP=y` |
| `ModemManager` (`mmcli`) | 55F, 102 | `apt install modemmanager` | `BR2_PACKAGE_MODEM_MANAGER=y` |
| `libqmi` (`qmicli`) | 55F, 102 | `apt install libqmi-utils` | `BR2_PACKAGE_LIBQMI=y` |
| `libmbim` (`mbimcli`) | 55F, 102 | `apt install libmbim-utils` | `BR2_PACKAGE_LIBMBIM=y` |
| `gpsd` + `gpspipe`, `cgps`, `gpsmon` | 107 | `apt install gpsd gpsd-clients` | `BR2_PACKAGE_GPSD=y` |
| `quectel-CM` (vendor) | 102 | not in apt; build from NXP/Quectel repo | not in mainline Buildroot |

### Audio (ALSA, PulseAudio, GStreamer)

| Tool | Chapters | Ubuntu-base | Buildroot |
|---|---|---|---|
| `alsa-utils` (`alsamixer`, `aplay`, `arecord`) | 53, 78, 89, 90 | `apt install alsa-utils` | `BR2_PACKAGE_ALSA_UTILS=y` |
| ALSA libraries (`libasound2`) | 53, 89, 90 | preinstalled / `apt install libasound2-dev` | `BR2_PACKAGE_ALSA_LIB=y` |
| `pulseaudio` | optional (Ch 53 sidebar) | `apt install pulseaudio` | `BR2_PACKAGE_PULSEAUDIO=y` |
| `pipewire` | optional (Ch 53 sidebar) | `apt install pipewire` | `BR2_PACKAGE_PIPEWIRE=y` |
| `gstreamer1.0-tools` (`gst-launch-1.0`) | 54B, 87, 88 | `apt install gstreamer1.0-tools` | `BR2_PACKAGE_GSTREAMER1=y` |
| GStreamer plugins (base/good/bad/ugly) | 54B, 87, 88 | `apt install gstreamer1.0-plugins-{base,good,bad}` | `BR2_PACKAGE_GST1_PLUGINS_BASE/GOOD/BAD=y` |
| `v4l-utils` (`v4l2-ctl`, `qv4l2`) | 54B, 87 | `apt install v4l-utils` | `BR2_PACKAGE_V4L_UTILS=y` |

### GPIO / I²C / SPI / sensors / IIO

| Tool | Chapters | Ubuntu-base | Buildroot |
|---|---|---|---|
| `libgpiod` (`gpioget`, `gpioset`, `gpiomon`, `gpioinfo`) | 18B, 44, 78, 99, 111 | `apt install gpiod` | `BR2_PACKAGE_LIBGPIOD=y` |
| `i2c-tools` (`i2cdetect`, `i2cdump`, `i2cset`, `i2cget`) | 18, 46, 64–117 (most cookbook) | `apt install i2c-tools` | `BR2_PACKAGE_I2C_TOOLS=y` |
| `spidev-test` | 47 | `apt install spi-tools` (older) / build manually | `BR2_PACKAGE_SPI_TOOLS=y` |
| `evtest` (input subsystem) | 45, 55G, 86, 106 | `apt install evtest` | `BR2_PACKAGE_EVTEST=y` |
| `libinput-tools` | 86 | `apt install libinput-tools` | `BR2_PACKAGE_LIBINPUT=y` |
| `tslib` (resistive touch) | 86 | `apt install libts-bin` | `BR2_PACKAGE_TSLIB=y` |
| IIO sysfs (`/sys/bus/iio/devices/`) | all sensor chapters | kernel-provided; no userspace install | kernel `CONFIG_IIO=y` |
| `iio-utils` (`iio_readdev`, `iio_info`) | various | `apt install libiio-utils` | `BR2_PACKAGE_LIBIIO_TOOLS=y` |

### Storage / filesystem / flash

| Tool | Chapters | Ubuntu-base | Buildroot |
|---|---|---|---|
| `mtd-utils` (`flash_erase`, `nandwrite`, `flashcp`, `mtdinfo`) | 54A, 64 | `apt install mtd-utils` | `BR2_PACKAGE_MTD=y` |
| `ubi-utils` (`ubinfo`, `ubiformat`, `ubinize`) | 54A | bundled with `mtd-utils` | bundled |
| `parted`, `fdisk`, `sfdisk` | 19, 31, 121 | preinstalled | `BR2_PACKAGE_PARTED=y` / `BR2_PACKAGE_UTIL_LINUX_FDISK=y` |
| `e2fsprogs` (`mkfs.ext4`, `e2fsck`, `tune2fs`) | 19, 31, 35B | preinstalled | `BR2_PACKAGE_E2FSPROGS=y` |
| `dosfstools` (`mkfs.vfat`) | 121, 125 | preinstalled | `BR2_PACKAGE_DOSFSTOOLS=y` |
| `cryptsetup` (LUKS) | 124 (sidebar) | `apt install cryptsetup` | `BR2_PACKAGE_CRYPTSETUP=y` |
| `veritysetup` (dm-verity) | 124 | bundled with cryptsetup | bundled |
| `overlayfs` (kernel feature, not a tool) | 35B | n/a | kernel `CONFIG_OVERLAY_FS=y` |

### Time + NTP + PPS

| Tool | Chapters | Ubuntu-base | Buildroot |
|---|---|---|---|
| `chrony` (`chronyc`) | 107, 117 | `apt install chrony` | `BR2_PACKAGE_CHRONY=y` |
| `ntpd` (legacy alternative) | 117 | `apt install ntp` | `BR2_PACKAGE_NTP=y` |
| `pps-tools` (`ppstest`) | 107 | `apt install pps-tools` | `BR2_PACKAGE_PPS_TOOLS=y` |
| `hwclock` | 18C, 117 | preinstalled (util-linux) | `BR2_PACKAGE_UTIL_LINUX_HWCLOCK=y` |

### CAN / RS-485 / industrial

| Tool | Chapters | Ubuntu-base | Buildroot |
|---|---|---|---|
| `can-utils` (`candump`, `cansend`, `cangen`, `canplayer`, `cansniffer`, `isotpsend`, `isotprecv`, `cangw`) | 55C, 110 | `apt install can-utils` | `BR2_PACKAGE_CAN_UTILS=y` |
| `libsocketcan` | 55C, 110 | `apt install libsocketcan2 libsocketcan-dev` | `BR2_PACKAGE_LIBSOCKETCAN=y` |
| `libmodbus` (`modbus_*`) | 108 | `apt install libmodbus5 libmodbus-dev` | `BR2_PACKAGE_LIBMODBUS=y` |
| `pymodbus` (Python) | 108 | `pip install pymodbus` | `BR2_PACKAGE_PYTHON3_PYMODBUS=y` |

### Identification / NFC / Fingerprint

| Tool | Chapters | Ubuntu-base | Buildroot |
|---|---|---|---|
| `libnfc-bin` (`nfc-list`, `nfc-mfultralight`, …) | 105 | `apt install libnfc-bin libnfc-dev` | `BR2_PACKAGE_LIBNFC=y` |
| `neard` (NFC daemon, `neardctl`) | 105 | `apt install neard` | `BR2_PACKAGE_NEARD=y` |
| `mfoc` / `mfcuk` (Mifare Classic key recovery; security research) | 105 sidebar | `apt install mfoc mfcuk` | not in mainline Buildroot |
| `fprintd` + `libfprint` | 106 | `apt install fprintd libfprint-2-2` | `BR2_PACKAGE_FPRINTD=y` |
| `pamu2fcfg` (2FA) | 106 | `apt install libpam-u2f` | `BR2_PACKAGE_LIBPAM_*` |

### Smart-home / mesh / IoT

| Tool | Chapters | Ubuntu-base | Buildroot |
|---|---|---|---|
| `mosquitto` broker | 100, 114, all MQTT examples | `apt install mosquitto` | `BR2_PACKAGE_MOSQUITTO=y` |
| `mosquitto-clients` (`mosquitto_pub`, `mosquitto_sub`) | as above | `apt install mosquitto-clients` | bundled when mosquitto enabled |
| `zigbee2mqtt` | 100 | Node 18+: `apt install nodejs npm`; then `npm install -g zigbee2mqtt` | non-trivial; usually run from a separate container |
| OpenThread Border Router (`otbr-agent`) | 100 | build from `openthread/ot-br-posix` source | non-trivial; typically self-built |
| `chip-tool` (Matter) | 100 | build from `project-chip/connectedhomeip` | non-trivial |

### Debug / tracing / profiling

| Tool | Chapters | Ubuntu-base | Buildroot |
|---|---|---|---|
| `gdb-multiarch` (host) | 118, 120, 125A | `apt install gdb-multiarch` | n/a (host-only) |
| `gdbserver` (target) | 120, 125A | `apt install gdbserver` | `BR2_PACKAGE_GDB=y` + `BR2_PACKAGE_GDB_SERVER=y` |
| `strace` | 120 | `apt install strace` | `BR2_PACKAGE_STRACE=y` |
| `ltrace` | 120 | `apt install ltrace` | `BR2_PACKAGE_LTRACE=y` |
| `perf` (`linux-tools`) | 120 | `apt install linux-tools-generic` (kernel-version-matched) | `BR2_PACKAGE_LINUX_TOOLS_PERF=y` |
| `valgrind` (memcheck) | 120 sidebar | `apt install valgrind` | `BR2_PACKAGE_VALGRIND=y` |
| `trace-cmd` + `kernelshark` | 119 | `apt install trace-cmd kernelshark` | `BR2_PACKAGE_TRACE_CMD=y` (kernelshark builds separately on host) |
| `bcc`, `bpftrace` | 119 | `apt install bpfcc-tools bpftrace` | `BR2_PACKAGE_BCC=y` / `BR2_PACKAGE_BPFTRACE=y` (kernel must have BPF + BTF) |
| `coredumpctl` (systemd) | 120 | bundled with systemd | requires systemd init |
| OpenOCD (host) | 118 | `apt install openocd` | n/a (host-only) |

### Build infrastructure (host)

| Tool | Chapters | Ubuntu-base (host) |
|---|---|---|
| Cross toolchains (`arm-none-linux-gnueabihf-gcc`, `arm-none-eabi-gcc`) | 3, 6, 122 | Arm GNU Toolchain tarballs installed under `~/imx6ull/toolchains/` |
| `crosstool-NG` (build your own toolchain) | 122 | `apt install autoconf bison flex texinfo unzip`; clone `crosstool-ng` |
| `bison`, `flex`, `bc`, `libssl-dev` (kernel build) | 25, 122 | `apt install build-essential bison flex bc libssl-dev` |
| `device-tree-compiler` (`dtc`) | 27, 27A | `apt install device-tree-compiler` |
| `u-boot-tools` (`mkimage`, `mkenvimage`) | 11, 19, 23 | `apt install u-boot-tools` |
| `qemu-user-static` (chroot foreign arch) | 35A | `apt install qemu-user-static` |
| `binfmt-support` | 35A | `apt install binfmt-support` |
| `imx_usb_loader`, `uuu` (i.MX SDP flashing) | 3, 8, 24, 121A | `apt install imx-usb-loader`; build `uuu` from `nxp-imx/mfgtools` |

### OTA / images / production

| Tool | Chapters | Ubuntu-base | Buildroot |
|---|---|---|---|
| RAUC (`rauc`) | 125 | `apt install rauc` | `BR2_PACKAGE_RAUC=y` |
| SWUpdate | 125 | build from source (sbabic/swupdate) | `BR2_PACKAGE_SWUPDATE=y` |
| Mender (`mender-client`, `mender-cli`) | 125 | `apt install mender-client`; `mender-cli` separate | `BR2_PACKAGE_MENDER=y` (community); commercial via Mender |
| `casync` (delta-update chunking) | 125 | `apt install casync` | `BR2_PACKAGE_CASYNC=y` |
| `wic` (Yocto image creator) | 123A | bundled with Yocto / bitbake | n/a |

### Secure boot / TEE

| Tool | Chapters | Ubuntu-base | Buildroot |
|---|---|---|---|
| NXP CST (Code Signing Tool) | 124 | download from NXP site; non-redistributable | not in Buildroot |
| `openssl` (key generation) | 124 | preinstalled | `BR2_PACKAGE_OPENSSL=y` |
| OP-TEE (`tee-supplicant`) | 124 | build from `OP-TEE/optee_os` and `OP-TEE/optee_client` | `BR2_PACKAGE_OPTEE_CLIENT=y` |
| `imx_habtool` (HAB CSF helper) | 124 | from NXP CST tarball | not in Buildroot |

## A.4  Quick-start "install everything" cheat sheets

### Ubuntu-base one-liner

For a *learning* dev kit (any chapter in the book usable after this):

```sh
sudo apt update
sudo apt install -y \
    i2c-tools spi-tools gpiod libgpiod-dev \
    alsa-utils libasound2-dev \
    gstreamer1.0-tools gstreamer1.0-plugins-base gstreamer1.0-plugins-good gstreamer1.0-plugins-bad \
    v4l-utils libv4l-dev \
    bluez bluez-tools \
    wpasupplicant iw hostapd wireless-regdb \
    network-manager modemmanager libqmi-utils libmbim-utils \
    ppp \
    gpsd gpsd-clients pps-tools chrony \
    can-utils libsocketcan-dev libmodbus5 libmodbus-dev \
    libnfc-bin libnfc-dev neard \
    fprintd libfprint-2-2 \
    mosquitto mosquitto-clients \
    mtd-utils dosfstools parted cryptsetup \
    iperf3 tcpdump ethtool \
    gdb-multiarch gdbserver strace ltrace valgrind \
    trace-cmd \
    rauc casync \
    device-tree-compiler u-boot-tools
```

That's about 400 MB of additional disk on the target. Drop the lines you don't need.

### Buildroot Kconfig fragment

Drop into your `configs/myboard_defconfig` (or merge via `make menuconfig`):

```
BR2_PACKAGE_I2C_TOOLS=y
BR2_PACKAGE_LIBGPIOD=y
BR2_PACKAGE_LIBGPIOD_TOOLS=y
BR2_PACKAGE_ALSA_UTILS=y
BR2_PACKAGE_ALSA_LIB=y
BR2_PACKAGE_GSTREAMER1=y
BR2_PACKAGE_GST1_PLUGINS_BASE=y
BR2_PACKAGE_GST1_PLUGINS_GOOD=y
BR2_PACKAGE_GST1_PLUGINS_BAD=y
BR2_PACKAGE_V4L_UTILS=y
BR2_PACKAGE_BLUEZ5_UTILS=y
BR2_PACKAGE_BLUEZ5_UTILS_DEPRECATED=y
BR2_PACKAGE_WPA_SUPPLICANT=y
BR2_PACKAGE_IW=y
BR2_PACKAGE_HOSTAPD=y
BR2_PACKAGE_NETWORK_MANAGER=y
BR2_PACKAGE_MODEM_MANAGER=y
BR2_PACKAGE_LIBQMI=y
BR2_PACKAGE_LIBMBIM=y
BR2_PACKAGE_PPP=y
BR2_PACKAGE_GPSD=y
BR2_PACKAGE_PPS_TOOLS=y
BR2_PACKAGE_CHRONY=y
BR2_PACKAGE_CAN_UTILS=y
BR2_PACKAGE_LIBSOCKETCAN=y
BR2_PACKAGE_LIBMODBUS=y
BR2_PACKAGE_LIBNFC=y
BR2_PACKAGE_NEARD=y
BR2_PACKAGE_FPRINTD=y
BR2_PACKAGE_MOSQUITTO=y
BR2_PACKAGE_MTD=y
BR2_PACKAGE_DOSFSTOOLS=y
BR2_PACKAGE_E2FSPROGS=y
BR2_PACKAGE_PARTED=y
BR2_PACKAGE_CRYPTSETUP=y
BR2_PACKAGE_IPERF3=y
BR2_PACKAGE_TCPDUMP=y
BR2_PACKAGE_ETHTOOL=y
BR2_PACKAGE_GDB=y
BR2_PACKAGE_GDB_SERVER=y
BR2_PACKAGE_STRACE=y
BR2_PACKAGE_LTRACE=y
BR2_PACKAGE_VALGRIND=y
BR2_PACKAGE_TRACE_CMD=y
BR2_PACKAGE_RAUC=y
BR2_PACKAGE_CASYNC=y
BR2_PACKAGE_OPTEE_CLIENT=y
```

This will bloat the image by ~40 MB. That's expected for a dev-image; production images trim to only what they ship.

## A.5  Per-Part cheat sheets

If you only want the tools for the Part you're reading right now:

### Part VI — Driver development

```sh
# Ubuntu-base on target
apt install i2c-tools gpiod alsa-utils v4l-utils gstreamer1.0-tools \
            bluez wpasupplicant iw modemmanager libqmi-utils \
            mtd-utils can-utils evtest
```

### Part VII — Device cookbook

Same as Part VI, plus:

```sh
apt install libnfc-bin neard fprintd \
            libmodbus-dev mosquitto-clients \
            gpsd gpsd-clients pps-tools chrony \
            iperf3 tcpdump
```

### Part VIII — Debug, production, advanced

```sh
# On the host
apt install gdb-multiarch openocd build-essential bison flex bc libssl-dev \
            qemu-user-static binfmt-support u-boot-tools device-tree-compiler

# On the target (debug image only — strip for production)
apt install gdbserver strace ltrace valgrind trace-cmd perf \
            rauc casync
```

### Part IX — Applied virtualization

```sh
# On the host
apt install qemu-system-arm qemu-system-aarch64 gdb-multiarch \
            device-tree-compiler u-boot-tools bridge-utils

# Hypervisor builds also need the normal kernel/U-Boot build tools above.
# Xen, Jailhouse, Zephyr, and STM32MP1-specific tooling are pinned inside
# their chapters because version drift matters.
```

## A.6  Pitfalls

- **libgpiod v1 vs v2.** The CLI changed: `gpioget --chip=gpiochip0 18` (v2) vs `gpioget gpiochip0 18` (v1). Ubuntu 24.04+ ships v2; older Buildroot trees ship v1. Match documentation to your version.
- **GStreamer plugin sets.** "`base`" + "`good`" + "`bad`" cover ~95 % of pipelines; "`ugly`" adds patented-codec elements (h264, mp3). Add `gstreamer1.0-libav` for ffmpeg-backed elements. Ubuntu separates these into named packages; Buildroot uses `BR2_PACKAGE_GST1_PLUGINS_*=y`.
- **WiFi firmware blobs are non-redistributable.** Ubuntu ships them in `firmware-iwlwifi`, `firmware-realtek`, etc.; Buildroot has corresponding packages but you may need `BR2_LEGAL_INFO=y` and to accept the licenses.
- **`bluez` 5.x vs `bluetooth-meshd`.** Mesh support is a *separate daemon* (`bluetooth-meshd`); installing `bluez` alone does **not** give you mesh.
- **`mosquitto` broker + clients.** "Clients" without "broker" still works — you just connect to a remote broker. Drop `BR2_PACKAGE_MOSQUITTO=y` and keep `BR2_PACKAGE_MOSQUITTO_CLIENTS=y` if you don't host the broker.
- **`zigbee2mqtt` is Node.js, not a C package.** Run from npm, or containerize.
- **OpenThread / Matter require building from source.** No clean apt or Buildroot package; expect 30–90 min of build time and tracking upstream master.
- **NXP CST (Code Signing Tool) is not redistributable.** Download from the NXP site after registration; do not check it into a public repo.
- **`mfoc`/`mfcuk` are offensive-security tools.** Many jurisdictions restrict cloning RFID cards. Use for authorized assessment only.
- **systemd-only utilities.** `journalctl`, `coredumpctl`, `systemd-analyze` only work if your init is `systemd`. BusyBox-init / runit / sysvinit systems use `dmesg`, `gdb on /var/lib/cores/*`, and their own benchmarking instead.
- **`pip install` on production images.** Convenient on dev kit; ruins reproducibility on shipping firmware. Use Buildroot's `BR2_PACKAGE_PYTHON3_*` packages or vendor your wheels.

## A.7  Going deeper

- **Buildroot manual, "Package recipes" chapter** — the canonical reference; lists every `BR2_PACKAGE_*` symbol.
- **Yocto Project Layer Index** (https://layers.openembedded.org/) — search any tool name to find the recipe.
- **Debian / Ubuntu packages.ubuntu.com** — search to verify the exact package name for any tool.
- **`apt-file`** (`apt install apt-file && apt-file update`) — search "which package ships this binary?": `apt-file search bin/gpioget`.
- **Per-chapter "Tooling" boxes** — most chapters that depend on a specific tool now carry a one-line install hint at the top of the chapter; this appendix is the canonical full reference.
