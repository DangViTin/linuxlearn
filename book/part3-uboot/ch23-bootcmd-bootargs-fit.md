---
chapter: 23
title: bootcmd, bootargs, FIT images
part: III — U-Boot, deeply
estimated_pages: 18
status: draft
---

# Chapter 23 — `bootcmd`, `bootargs`, FIT images

> **What:** the *contract* between U-Boot and the Linux kernel. `bootcmd` is what U-Boot runs to load and start the kernel; `bootargs` is what U-Boot tells the kernel about the system; FIT (Flattened Image Tree) is the modern signed-bundle format that carries kernel + DTB + initramfs in one file.
>
> **Why:** These three things sit between "U-Boot works" and "Linux boots." Most "the kernel won't start" bugs live here. Once you understand them, you can diagnose boot failures from the boot log alone.
>
> **Focus:** the **cmdline as a contract**. The kernel's behavior depends entirely on what it finds in `chosen.bootargs` of the DT (which `bootargs` writes to). Know which knobs are kernel-side and which are U-Boot-side, and you stop chasing the wrong file.

## 23.1  `bootcmd` — U-Boot's autoboot

`bootcmd` is one environment variable whose value is treated as a sequence of U-Boot commands, evaluated automatically after `CONFIG_BOOTDELAY` seconds if no key is pressed.

A minimal `bootcmd` for SD-booting a kernel:

```
bootcmd=load mmc 0:1 0x82000000 zImage;
         load mmc 0:1 0x83000000 imx6ull-pa-mini.dtb;
         bootz 0x82000000 - 0x83000000
```

(In practice it would be on one line, separated by `;`.)

What each piece does:

| Command | What it does |
|---------|--------------|
| `load mmc 0:1 0x82000000 zImage` | Read the file `zImage` from MMC device 0, partition 1, FAT or ext, into DRAM at `0x82000000` |
| `load mmc 0:1 0x83000000 imx6ull-pa-mini.dtb` | Read the DTB into DRAM at `0x83000000` |
| `bootz 0x82000000 - 0x83000000` | Start a zImage at `0x82000000`, no initramfs (`-`), DTB at `0x83000000` |

After `bootz`, U-Boot is gone. The kernel runs.

### EVK's default `bootcmd` (cleaned up)

The EVK defconfig ships a more sophisticated default that tries multiple boot sources:

```
bootcmd=run findfdt; mmc dev ${mmcdev}; mmc rescan;
         if run loadbootscript; then run bootscript;
         else
             if run loadimage; then run mmcboot;
             else run netboot; fi;
         fi
```

The script is verbose, but the pattern is common to most boards:

1. Find the appropriate DT (`findfdt` runs `setenv fdtfile imx6ull-pa-mini.dtb` based on board detection).
2. Initialize MMC.
3. Try to load a "boot script" — a small text file the user can drop on the SD card to override boot behavior without touching the env.
4. If no script, try to load `zImage` from MMC.
5. If no MMC, try TFTP.

Each `loadbootscript`, `bootscript`, `loadimage`, `mmcboot`, `netboot` is another env variable. The structure is a small embedded DSL.

You can replace this with anything. For development I use:

```
bootcmd=run nfsboot
nfsboot=setenv bootargs console=ttymxc0,115200 root=/dev/nfs nfsroot=${serverip}:/srv/nfs/rootfs ip=dhcp;
         tftp 0x82000000 zImage;
         tftp 0x83000000 imx6ull-pa-mini.dtb;
         bootz 0x82000000 - 0x83000000
```

One `setenv bootcmd '...'; saveenv` and the board network-boots on every power-up. Chapter 24 builds on this.

## 23.2  `bootargs` — the kernel command line

`bootargs` is *the* kernel cmdline. U-Boot writes it into the DT's `chosen.bootargs` node before transferring control. The kernel parses it during `start_kernel()` (Chapter 28).

The minimum for any embedded boot:

```
bootargs=console=ttymxc0,115200 root=/dev/mmcblk0p2 rw rootwait
```

Each token has a meaning:

| Token | Effect |
|-------|--------|
| `console=ttymxc0,115200` | Direct printk output to UART1 at 115200 baud. *Required* for serial-debug boards. |
| `root=/dev/mmcblk0p2` | The kernel will try to mount this device as `/`. |
| `rw` | Mount root read-write. (vs `ro`.) |
| `rootwait` | Don't panic if the root device isn't immediately ready; wait. Essential when the rootfs is on USB or slow media. |

Some more useful tokens:

| Token | Effect |
|-------|--------|
| `init=/bin/sh` | Override `/sbin/init` with a shell. Excellent for "rootfs is broken; let me poke around" debugging. |
| `single` | Single-user (no daemons, root shell only). |
| `quiet` | Suppress most `printk` (`KERN_NOTICE` and below). |
| `loglevel=8` | Print everything (the opposite of `quiet`). |
| `nokaslr` | Disable address-space randomization. Needed when using `gdb` against the kernel. |
| `panic=10` | After panic, reboot after 10 s. |
| `earlycon=ec_imx6q,0x02020000` | Print *very early* `printk`s via direct UART access, before the full serial driver loads. Critical for debugging boot hangs. |
| `nfsroot=192.168.7.1:/srv/nfs/rootfs,vers=3,nolock` | When `root=/dev/nfs`. |
| `ip=192.168.7.2::192.168.7.1:255.255.255.0::eth0:off` | Static IP for the kernel's built-in IP stack. |
| `ip=dhcp` | DHCP at boot time. |
| `rdinit=/init` | Where the initramfs's init lives, when using initramfs. |

A common pattern: keep your *board's* defaults in the env, and override at the boot prompt for specific debugging:

```
=> setenv bootargs ${bootargs} earlycon ignore_loglevel
=> run bootcmd
```

### Where `bootargs` ends up in the DT

When U-Boot is about to `bootz`, it calls `do_bootm_states` which calls `fixup_chosen_node`. That function modifies the `chosen` node of the DT in place:

```dts
/ {
    chosen {
        bootargs = "console=ttymxc0,115200 root=/dev/mmcblk0p2 rw rootwait";
        /* ... other chosen fields ... */
    };
};
```

This is the channel through which the kernel learns the cmdline. There is also a fallback: if the kernel finds no `chosen.bootargs`, it uses `CONFIG_CMDLINE` (built-in default). Embedded systems almost always use the DT path.

## 23.3  `bootm`, `bootz`, `booti` — what's the difference

Three commands with similar names but different jobs.

| Command | Expected kernel format | Endianness |
|---------|------------------------|------------|
| `bootm <addr> [<initrd>] [<fdt>]` | "U-Boot image" (legacy uImage) | architecture-dependent |
| `bootz <addr> [<initrd>] [<fdt>]` | Raw zImage (compressed ARM kernel) | ARM 32-bit |
| `booti <addr> [<initrd>] [<fdt>]` | Raw arm64 Image | AArch64 |

For our i.MX6ULL (ARMv7-A, 32-bit), we use **`bootz`** because mainline ARM kernels build to `zImage` by default.

If your kernel build produces a **uImage** (a zImage wrapped with U-Boot's legacy header), use **`bootm`**.

If your kernel build is **arm64**, use **`booti`**.

All three take the same arguments after the address: `[initrd-addr] [dtb-addr]`. The `-` in `bootz 0x82000000 - 0x83000000` means "no initrd; DTB is at the next argument."

## 23.4  Boot scripts — a slightly nicer layer

A "boot script" is a small file the user drops on the SD card that overrides `bootcmd` without touching the env. Useful for distributing a board image where each user has their own customization.

You write a plain-text file `boot.cmd`:

```
setenv bootargs console=ttymxc0,115200 root=/dev/mmcblk0p2 rw rootwait
load mmc 0:1 0x82000000 zImage
load mmc 0:1 0x83000000 imx6ull-pa-mini.dtb
bootz 0x82000000 - 0x83000000
```

Then wrap it with `mkimage` into a `boot.scr`:

```sh
mkimage -A arm -O linux -T script -C none -d boot.cmd boot.scr
```

Copy `boot.scr` onto the SD card's FAT partition. If U-Boot's default `bootcmd` includes "look for `boot.scr` and run it" (the EVK config does), the script runs on next boot.

Boot scripts are mostly for distros. For development work, just edit `bootcmd`.

## 23.5  FIT — Flattened Image Tree

FIT is a single binary container that holds one or more *images* (kernel, DTB, initramfs, microcode, firmware), grouped into named *configurations*. It supersedes the legacy uImage format and is the recommended format for new designs.

Why FIT:

- **Multiple images in one file.** Kernel + DTB + initramfs in a single SD-card sector range. Much easier to deploy atomically.
- **Multiple configurations.** One FIT can hold "boot config for rev A board" + "boot config for rev B board" with different DTBs. Selecting which is a U-Boot command-line argument.
- **Signed boot.** The FIT can have an attached signature. U-Boot's HAB- or FIT-signature-verifying boot path is what `bootm` invokes for `-c` (signed configs).

### A FIT image source file (.its)

```dts
/dts-v1/;

/ {
    description = "Kernel + DT for mx6ull_pa_mini";
    #address-cells = <1>;

    images {
        kernel-1 {
            description = "Linux kernel";
            data = /incbin/("./zImage");
            type = "kernel";
            arch = "arm";
            os = "linux";
            compression = "none";
            load = <0x82000000>;
            entry = <0x82000000>;
            hash-1 {
                algo = "sha256";
            };
        };

        fdt-1 {
            description = "Device Tree (mx6ull-pa-mini)";
            data = /incbin/("./imx6ull-pa-mini.dtb");
            type = "flat_dt";
            arch = "arm";
            compression = "none";
            hash-1 {
                algo = "sha256";
            };
        };

        ramdisk-1 {
            description = "initramfs";
            data = /incbin/("./rootfs.cpio.gz");
            type = "ramdisk";
            arch = "arm";
            os = "linux";
            compression = "gzip";
            hash-1 {
                algo = "sha256";
            };
        };
    };

    configurations {
        default = "conf-mini";
        conf-mini {
            description = "Point Atom MINI";
            kernel = "kernel-1";
            fdt = "fdt-1";
            ramdisk = "ramdisk-1";
        };
    };
};
```

Build with:

```sh
mkimage -f boot.its boot.itb
```

`boot.itb` is the binary FIT. To boot it from U-Boot:

```
=> load mmc 0:1 0x82000000 boot.itb
=> bootm 0x82000000#conf-mini
```

The `#conf-mini` selects the configuration. With no `#`, the default applies.

### Why this matters in Chapter 23A

A FIT can hold several DTBs and several configurations. That is what we use in Chapter 23A to ship one image for several board variants — strap pins or an EEPROM ID pick which `conf-xxx` to invoke at boot time.

For now, get one config working.

## 23.6  Practical boot-command idioms

A few patterns to keep ready.

### Quick recovery boot (sh as init)

```
=> setenv bootargs console=ttymxc0,115200 root=/dev/mmcblk0p2 rw rootwait init=/bin/sh
=> run bootcmd
```

If `/sbin/init` is corrupt, `/bin/sh` runs as PID 1 and you get a root shell. From there you can `mount`, edit files, `reboot`.

### NFS-root development loop

```
=> setenv serverip 192.168.7.1
=> setenv ipaddr 192.168.7.2
=> setenv bootargs console=ttymxc0,115200 root=/dev/nfs nfsroot=${serverip}:/srv/nfs/rootfs,vers=3,nolock ip=dhcp rw rootwait
=> setenv bootcmd 'tftp 0x82000000 zImage; tftp 0x83000000 imx6ull-pa-mini.dtb; bootz 0x82000000 - 0x83000000'
=> saveenv
=> run bootcmd
```

Everything on the host. Edit a file in `/srv/nfs/rootfs/`; the board sees it on next access. `make modules_install INSTALL_MOD_PATH=/srv/nfs/rootfs` puts new kernel modules into the running target. No reflashing.

### Boot from a USB stick

```
=> usb start
=> load usb 0:1 0x82000000 zImage
=> load usb 0:1 0x83000000 imx6ull-pa-mini.dtb
=> bootz 0x82000000 - 0x83000000
```

Useful for installer media and rescue boots.

### Boot the same kernel with two different DTBs

```
=> load mmc 0:1 0x82000000 zImage
=> load mmc 0:1 0x83000000 imx6ull-pa-mini-v1.dtb
=> bootz 0x82000000 - 0x83000000
                                  # later, after reset:
=> load mmc 0:1 0x82000000 zImage
=> load mmc 0:1 0x83000000 imx6ull-pa-mini-v2.dtb
=> bootz 0x82000000 - 0x83000000
```

The kernel doesn't care; it accepts whichever DTB it's handed. Trade-off: two DT files on disk vs the cleaner single-FIT approach in Ch 23A.

## 23.7  Common kernel-boot failure modes (and which line of bootargs to blame)

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| Boot hangs after "Uncompressing Linux... done, booting the kernel." | `console=` token wrong or missing | Add `console=ttymxc0,115200 earlycon` |
| "VFS: Cannot open root device 'mmcblk0p2'" | `root=` points at a device that isn't ready or doesn't exist | Add `rootwait`; verify partition number; check `dmesg` for mmc init |
| "Kernel panic: VFS: Unable to mount root fs" | rootfs filesystem type unsupported by kernel | Add `rootfstype=ext4` (or build the right FS into the kernel) |
| Boots, then immediately freezes | Wrong DTB; clocks misconfigured | Verify the DTB matches the board; check `console=` is on the right UART |
| "Warning: maxcpus=1 ignored" or similar | Vendor-BSP cmdline tokens that mainline doesn't recognize | Strip vendor-specific tokens |
| Kernel boots but no userspace | `init=` points at nothing executable | Add `init=/bin/sh` as a fallback |
| Network not coming up | `ip=` malformed | Use `ip=dhcp` for diagnostics |

## 23.8  Lab

1. **Print and parse the EVK's default `bootcmd`.** Read each variable it references; trace the full chain.
2. **Write three different `bootcmd`s**: SD-root, NFS-root, ramdisk-root. Switch between them with `setenv bootcmd '$nfsboot'; run bootcmd`.
3. **Build a `boot.scr`** that does the same as one of your `bootcmd`s. Verify it loads.
4. **Build a FIT** containing your kernel + DTB. Boot it.
5. **Add `earlycon=ec_imx6q,0x02020000`** to bootargs. Compare boot logs with and without it; you should see ~10 more lines of early `printk` output.
6. **Break it on purpose.** Pass `root=/dev/nonsense` and watch the panic. Then add `init=/bin/sh` and recover.

## 23.9  Pitfalls

- **`console=` typos.** `ttymxc0` not `ttymx0` not `ttyMXC0`. Case- and digit-sensitive. Wrong console = silent kernel.
- **No `rootwait`.** On boards with slow MMC init, the kernel races MMC and panics. Add it always.
- **`bootargs` not saved.** `saveenv` is required for env changes to survive reboot.
- **FIT load/entry addresses overlap.** If your kernel `load=0x82000000` and your DTB `load=0x82800000` and the kernel grows past 8 MB, they collide. Choose addresses that don't.
- **`bootm` on a `zImage`.** Will fail with "Bad magic." Use `bootz`. Or wrap the zImage as a uImage with `mkimage -A arm -O linux -T kernel -C none -a 0x82000000 -e 0x82000000 -d zImage uImage`.
- **Mismatched `mkimage` arch.** `mkimage -A arm64` on a 32-bit ARM zImage produces a FIT the kernel can't unpack.
- **Endianness of `bootargs` storage.** Not an issue here (all little-endian), but on big-endian SoCs (some PowerPC) the env on the medium and U-Boot's runtime view can mismatch.

## 23.10  Going deeper

- **U-Boot docs `doc/usage/cmd/bootm.rst`, `bootz.rst`, `bootargs.rst`.**
- **Linux Documentation: `Documentation/admin-guide/kernel-parameters.txt`** — the canonical list of every cmdline token the kernel understands. ~1000 entries; skim once for the categories you might need.
- **FIT docs at `doc/uImage.FIT/`** in U-Boot — the FIT spec and examples.
- **Bootlin training: "Boot Time Reduction"** — practical techniques for shaving seconds off boot via cmdline and FIT tuning.
- **AN5096** — *Configuring U-Boot for the i.MX 6/7 Series* (NXP). Procedural; good cross-check.

> Next chapter: **Chapter 23A — Multi-variant FIT images and DT overlays.** Now that one FIT works, we extend it to carry several DTBs for several board revisions and switch between them at runtime.
