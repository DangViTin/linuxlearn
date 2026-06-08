---
chapter: 24
title: Workflows — TFTP, NFS, USB-OTG
part: III — U-Boot, deeply
estimated_pages: 14
status: draft
---

# Chapter 24 — Workflows — TFTP, NFS, USB-OTG
**FIT** - Flattened Image Tree, U-Boot's container format for kernels, DTBs, initramfs images, hashes, and signatures.

> **What:** stop reflashing the SD card. From this chapter on, every kernel change and every rootfs change is visible on the board within seconds, over the wire — TFTP for the kernel + DTB, NFS for the rootfs, USB-OTG (`uuu`) for recovery.
> **MCU bridge:** Think of the rootfs as the firmware image's file-backed runtime environment. On an MCU you link everything into flash. On Linux, programs and config live in this mounted tree.
> **NFS** - Network File System, which lets the target mount a host directory over Ethernet during development.
> **TFTP** - Trivial File Transfer Protocol, a simple network protocol U-Boot commonly uses to fetch kernels from the host.
> **rootfs** - root filesystem, the directory tree mounted at / that contains /bin, /etc, /dev, and libraries.
>
> **Why:** Iteration speed bounds productivity. SD-reflash takes 1–2 minutes per cycle. TFTP+NFS takes 5–10 seconds. Across hundreds of kernel builds in Parts IV–VI, that adds up to days. The workflow in this chapter is what the rest of the book assumes.
>
> **Focus:** the single mental loop: edit a file on the host, the target sees it immediately. That loop is what turns embedded Linux from a build-and-flash cycle into real development.


## 24.1  Three transports, three jobs

| Transport | What it carries | When used |
|-----------|-----------------|-----------|
| **TFTP** | Kernel `zImage`, device tree `.dtb`, FIT `.itb` | Every kernel rebuild |
| **NFS** | The entire root filesystem | Every userspace change |
| **USB-OTG (SDP via `uuu`)** | A full image stack (SPL + U-Boot + kernel + rootfs) | Bricked-board recovery; first-time flashing |

Each was set up in Chapter 3 (`tftpd-hpa`, `nfs-kernel-server`, `uuu`/`imx_usb_loader`). This chapter ties them into a coherent workflow.

## 24.2  TFTP for the kernel

### Stage layout on the host

```
/srv/tftp/                     # owned by your user (Ch 3 §3.6)
├── zImage                     # symlink → ~/imx6ull/src/linux/arch/arm/boot/zImage
├── imx6ull-pa-mini.dtb        # symlink → ~/.../arch/arm/boot/dts/...
├── boot.itb                   # FIT image (if you use Ch 23's flow)
└── rescue-zImage              # known-good backup
```

The symlinks let you `make` in the kernel tree and the new artefacts are *immediately* available to TFTP — no copy step.

```sh
$ cd /srv/tftp
$ ln -s ~/imx6ull/src/linux/arch/arm/boot/zImage .
$ ln -s ~/imx6ull/src/linux/arch/arm/boot/dts/nxp/imx/imx6ull-pa-mini.dtb .
```

### TFTP from U-Boot

```
=> setenv ipaddr 192.168.7.2
=> setenv serverip 192.168.7.1
=> setenv loadaddr 0x82000000
=> setenv fdt_addr 0x83000000
=> setenv fdtfile imx6ull-pa-mini.dtb

=> tftp ${loadaddr} zImage
Using FEC0 device
TFTP from server 192.168.7.1; our IP address is 192.168.7.2
Filename 'zImage'.
Load address: 0x82000000
Loading: ##################################### 4.8 MiB/s
done
Bytes transferred = 6291456 (600000 hex)

=> tftp ${fdt_addr} ${fdtfile}
Loading: ###  20 KiB/s
done
Bytes transferred = 56320 (dc00 hex)

=> bootz ${loadaddr} - ${fdt_addr}
## Booting kernel from Legacy Image at 82000000 ...
...
```

Save these into `bootcmd`:

```
=> setenv bootcmd 'tftp ${loadaddr} zImage; tftp ${fdt_addr} ${fdtfile}; bootz ${loadaddr} - ${fdt_addr}'
=> saveenv
```

Now the boot sequence is: power on → ROM → SPL → U-Boot → TFTP → kernel. No SD-card writes, ever.
> **MCU bridge:** Think of SPL like the tiny early startup code that runs from internal SRAM before DDR is usable.
**SPL** - Secondary Program Loader, a tiny first U-Boot stage that fits in OCRAM and initializes DDR.
**U-Boot** - the bootloader that initializes enough hardware to load and start the Linux kernel.

### Speed

TFTP runs at ~1 MB/s on 10/100 Ethernet (UDP, small windows). A 6 MB `zImage` arrives in ~6 seconds. Faster than `dd`, eject, insert, boot.

## 24.3  NFS for the rootfs

### Export from the host

Configured in Chapter 3 §3.7:

```
$ cat /etc/exports
/home/you/imx6ull/rootfs *(rw,sync,no_root_squash,no_subtree_check)
```

Populate the rootfs in the exported directory (we'll do this properly in Part V. For now a Buildroot-generated rootfs works):
**Buildroot** - a configuration-driven build system that produces a complete root filesystem and related images.

```sh
$ tar -xf ~/buildroot-output/rootfs.tar -C ~/imx6ull/rootfs/
$ ls ~/imx6ull/rootfs/
bin  dev  etc  lib  proc  root  sbin  sys  tmp  usr  var
```

Restart the NFS server to pick up new content:

```sh
$ sudo exportfs -ra
```

### NFS-root from the kernel cmdline

```
=> setenv bootargs 'console=ttymxc0,115200 root=/dev/nfs nfsroot=192.168.7.1:/home/you/imx6ull/rootfs,vers=3,nolock,tcp ip=192.168.7.2:192.168.7.1:192.168.7.1:255.255.255.0:pa-mini:eth0:off rw'
=> saveenv
=> run bootcmd
```

The `ip=` token format is `client::gateway:netmask::interface:autoconf`. Each colon-separated field is positional. Setting them explicitly avoids DHCP delays.

When the kernel boots:

```
[    7.812345] Sending DHCP requests . OK
[    7.834567] IP-Config: Got nfsroot answers from 192.168.7.1
[    8.012345] VFS: Mounted root (nfs filesystem) on device 0:16.
[    8.123456] Run /sbin/init as init process
                Welcome to your i.MX6ULL board!
target login: root
target#
```

Now: edit a file in `~/imx6ull/rootfs/etc/...` on the host. The target sees the change on next read. No reboot needed for userspace changes.

### What can't be on NFS

> **Privilege boundary:** $ means normal user. # or sudo means root and can change host or target state.
> After a privileged command, verify the expected device, service, or file appears before continuing. Roll back by undoing the config change or stopping the service you just enabled.


- **Kernel modules.** Modules loaded by `modprobe` come from `/lib/modules/...` on the rootfs, which *is* NFS — that works. But the *running kernel* itself is not from NFS. It was TFTP-loaded.
- **Device tree blobs.** Same — TFTP, not NFS.
- **The bootloader.** SD card or eMMC.

So the boot chain has three transports active simultaneously: SD/eMMC for U-Boot, TFTP for kernel/DTB, NFS for everything in user space.

### Speed and reliability

NFS over wired 100 Mbit Ethernet is consistently fast (~10 MB/s read). NFS over Wi-Fi is occasionally slow and occasionally drops packets — *not* recommended for the root mount. If your Wi-Fi USB driver is being developed (Chapter 55E), keep an Ethernet cable plugged in.

A common boot-time hang is "NFS mount timed out." Almost always the cause is a server-side firewall, wrong export options, or a wrong kernel cmdline path. Diagnose with the kernel cmdline `nfs.callback_tcpport=0` and `nfsroot=...,debug` (kernel must be built with `CONFIG_NFS_DEBUG`).

## 24.4  USB-OTG recovery via `uuu`

When the board cannot boot from SD (the boot sector is corrupt, the SPL won't run, or U-Boot panics on init), USB-OTG is your way back. The same `uuu` we used in Chapter 9 pushes a full image stack into RAM and runs U-Boot from there, with no persistent change to the board's storage.

### A complete `uuu` recipe

`flash_all.uuu`:

```
uuu_version 1.5.0

SDP: boot -f SPL
SDPU: write -f u-boot-dtb.imx -addr 0x87800000
SDPU: jump

# Now full U-Boot is running.  Tell it to flash the SD card from the host.
FB: ucmd setenv fastboot_buffer 0x82000000
FB: ucmd setenv fastboot_size 0x10000000
FB: download zImage
FB: ucmd mmc dev 0
FB: ucmd mmc write ${fastboot_buffer} 0x2000 0x6000   # write zImage to MMC
```

(Real recipes are more involved. This is the structure.)

Run from the host:

```sh
$ uuu flash_all.uuu
```

The board needs to be in SDP mode (boot switch in the "USB" position, USB-OTG cable connected to host). `uuu` enumerates the i.MX6ULL Boot ROM, pushes SPL, runs it, the SPL hands off to U-Boot in RAM, U-Boot enables Fastboot, `uuu` then drives `fastboot` commands to flash the persistent storage.

### When to use it

- **First-time flashing** a fresh board (or a fresh SD card).
- **Recovery** after corrupting U-Boot or SPL on the persistent storage.
- **Automated production line** — `uuu` can flash N boards in parallel. standard NXP practice for factory programming.

For day-to-day development, you do not need `uuu`. TFTP + NFS is faster and easier. `uuu` is the safety net.

## 24.5  The canonical development loop

Put it all together. The day-to-day workflow:

```
                      [you edit code]
                          │
                          ▼
                  ┌────────────────┐
                  │   Host PC      │
                  │                │
                  │ Linux source ──┼──make zImage──► /srv/tftp/zImage (symlink)
                  │                │
                  │ Rootfs tree ───┼─────────────►  /srv/nfs/rootfs/ (already exported)
                  │                │
                  │ TFTP server    │
                  │ NFS server     │
                  └────────────────┘
                          │
                  Ethernet │
                          ▼
                  ┌────────────────┐
                  │   Target       │
                  │                │
                  │  SPL → U-Boot ─┼──TFTP──► kernel + dtb in RAM
                  │                │
                  │  Kernel boots ─┼──NFS───► /home/you/imx6ull/rootfs (mounted as /)
                  │                │
                  └────────────────┘
                          │
                  Serial  │
                          ▼
                    [you read logs]
```

**Time from "edit a kernel file" to "see the change running on the target":**

```sh
$ vim drivers/foo.c
$ make -j$(nproc) zImage modules
$ make modules_install INSTALL_MOD_PATH=/home/you/imx6ull/rootfs
$ # On the board:
target# reboot
```

~30 seconds for a kernel-source change to be observable. No other workflow on this hardware iterates this fast.

For user-space changes, it's even faster:

```sh
$ vim /srv/nfs/rootfs/usr/bin/myapp.sh   # edit directly in the exported tree
$ # On the board:
target# myapp.sh                          # see it immediately
```

No reboot needed.

## 24.6  Some useful U-Boot env helpers

Save these in your environment for the development loop:

```
nfsroot_args=root=/dev/nfs nfsroot=${serverip}:${nfspath},vers=3,nolock,tcp \
             ip=${ipaddr}:${serverip}:${gatewayip}:${netmask}::eth0:off

devel_bootargs=console=${console} ${nfsroot_args} rw rootwait

devel_boot=tftp ${loadaddr} zImage; \
            tftp ${fdt_addr} ${fdtfile}; \
            setenv bootargs ${devel_bootargs}; \
            bootz ${loadaddr} - ${fdt_addr}

bootcmd=run devel_boot
```

Then:

```
=> setenv serverip 192.168.7.1
=> setenv nfspath /home/you/imx6ull/rootfs
=> saveenv
```

Now every reboot does the full TFTP+NFS loop.

For occasional SD-card boot (when you want to verify the persistent path still works):

```
sdboot=load mmc 0:1 ${loadaddr} zImage; \
        load mmc 0:1 ${fdt_addr} ${fdtfile}; \
        setenv bootargs console=${console} root=/dev/mmcblk0p2 rw rootwait; \
        bootz ${loadaddr} - ${fdt_addr}

=> run sdboot           # one-shot SD boot, doesn't change autoboot default
```

## 24.7  Lab

> **Storage safety:** Before any command that names /dev/sdX, run lsblk -o NAME,SIZE,MODEL,TRAN,TYPE,MOUNTPOINTS.
> Verify the removable card by size and model, unmount its partitions, and stop if the path is not the target card. Writing the wrong /dev node can destroy the host disk.


1. **Set up TFTP boot.** Get a kernel loaded from `/srv/tftp/zImage` and booting on the target. Time the load.
2. **Set up NFS-root.** Boot to a shell whose root is the host's directory. Confirm by editing a file on the host and seeing it on the target.
3. **Touch a kernel source file** (`echo "no-op" >> drivers/tty/serial/imx.c`), `make zImage`, reboot the board. Verify the new kernel is running (a date in the version banner or a custom string you added).
4. **Set up the full `devel_bootargs` / `devel_boot` / `bootcmd` chain** from §24.6. Confirm a fresh power-on goes through the full loop without manual commands.
5. **Practice the `uuu` recovery.** Deliberately wipe the SD card's first MB (`sudo dd if=/dev/zero of=/dev/sdX bs=1M count=1`). Boot the board into SDP (boot switch). Run a `uuu` script that re-flashes SPL + U-Boot. Confirm the board is back.

## 24.8  Pitfalls

- **Firewall on the host blocking UDP/69 (TFTP) or TCP/2049 (NFS).** `sudo ufw status`. `sudo ufw allow tftp`. `sudo ufw allow nfs`. Or disable UFW on the dev host.
- **NFS `root_squash`.** Without `no_root_squash`, the target's root user is mapped to nobody, and file permissions break. Always include `no_root_squash` in `/etc/exports` for development. *Never* on a public network.
- **NFS v4 by default on modern distros.** v4 has different semantics (especially around stale file handles). For embedded, v3 is more reliable. specify `vers=3` in the mount options.
- **Wrong IP on the target side.** `ip=` cmdline must match the host's NIC config (Chapter 3 §3.10). Mismatched netmask = silent failure to mount.
- **TFTP path includes a directory.** Some `tftpd-hpa` configs disable directories for security. Use `--secure` and serve from `/srv/tftp/` directly.
- **`uuu` cannot find the device.** Check with `lsusb | grep 15a2`. If absent: boot switch wrong, USB-OTG cable wrong (some are charge-only), or `udev` rule from Chapter 3 §3.8 missing.
**udev** - the user-space device manager that reacts to kernel device events and creates policy-driven /dev nodes.
- **Slow Ethernet PHY auto-negotiation.** Some PHYs take 2–3 seconds to come up. Add `rootwait` to bootargs and ignore the warning.
**PHY** - physical-layer block or chip that converts digital MAC signals to electrical or radio signals.

## 24.9  Going deeper

- **`Documentation/admin-guide/nfs/nfsroot.rst`** in the Linux kernel — definitive `nfsroot=` and `ip=` cmdline reference.
- **`man tftpd-hpa`** and **`man 5 exports`** — the canonical references for the server configs.
- **`uuu` README** at `https://github.com/nxp-imx/mfgtools` — script DSL, every supported command.
- **Bootlin "Embedded Linux Booting" training** — the same workflow in a different style.

---

**End of Part III.**

You can build mainline U-Boot, you can port it to a custom board, you understand its boot flow line-by-line, you can write commands and drivers within it, and you have a development loop that doesn't involve reflashing. Everything from here on assumes you can boot to a U-Boot prompt, network-boot a kernel, and NFS-mount a rootfs.

> **Part IV begins with Chapter 25 — Building mainline Linux for i.MX6ULL.** We leave the bootloader behind and start working on the kernel itself.
