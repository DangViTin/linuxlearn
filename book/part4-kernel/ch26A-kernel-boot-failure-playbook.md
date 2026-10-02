---
chapter: 26A
title: Kernel boot failure playbook
part: IV - The Kernel
estimated_pages: 12
status: draft
---

# Chapter 26A: Kernel boot failure playbook

> **What:** a practical checklist for the failures that happen between `bootz` and the first shell.
>
> **Why:** when Linux does not boot, the symptom is often vague: silence, a panic, or one last line that looks unrelated. This chapter gives you a repeatable debug order.
>
> **Result:** you can look at the last visible line and choose the next test instead of changing random settings.
>
> **Focus:** classify the failure first: no output, early output then silence, VFS panic, init panic, or driver probe failure.

This chapter assumes you already built the kernel in Chapter 25 and can type the manual boot commands from Chapter 26.

## 26A.1  Keep one known-good boot command

Before debugging anything, save a known-good command that uses `&&`. If a load fails, the boot stops instead of jumping into stale RAM.

```text
=> setenv boot_good 'tftp 0x82000000 zImage && tftp 0x83000000 imx6ull.dtb && bootz 0x82000000 - 0x83000000'
=> setenv bootargs_good 'console=ttymxc0,115200 earlycon root=/dev/mmcblk0p2 rw rootwait'
=> saveenv
```

Then boot with:

```text
=> setenv bootargs ${bootargs_good}
=> run boot_good
```

If you later break `bootcmd`, you still have a known-good path.

## 26A.2  Symptom table

| Symptom | Most likely area | First test |
|---------|------------------|------------|
| Nothing after `Starting kernel ...` | DTB address, early console, CPU entry state | Add explicit `earlycon=ec_imx6q,0x02020000` |
| A few early lines, then silence | Console handoff or driver hang | Add `ignore_loglevel loglevel=8 initcall_debug` |
| `VFS: Cannot open root device` | `root=` or storage driver | Boot initramfs from Chapter 29 |
| `No working init found` | rootfs content or init path | Try `init=/bin/sh` or `rdinit=/init` |
| Ethernet/NFS root hangs | network driver, IP args, server export | Boot SD root first, then test NFS |
| Random panics | DDR, bad DT memory node, kernel/module mismatch | Run U-Boot `mtest`; check `Memory:` line |

Do not skip the table. Pick the row that matches the last visible line.

## 26A.3  Case 1: nothing after `Starting kernel ...`

Start with the three boot arguments that maximize early visibility:

```text
=> setenv bootargs 'console=ttymxc0,115200 earlycon=ec_imx6q,0x02020000 ignore_loglevel loglevel=8 root=/dev/mmcblk0p2 rw rootwait'
=> run boot_good
```

If output appears now, the kernel was running. Your normal console path was wrong.

Check:

```text
=> fdt addr 0x83000000
=> fdt print /chosen
=> fdt print /aliases
```

You want `/chosen/stdout-path` to name the same UART you use for serial.

Common causes:

- Wrong third argument to `bootz`.
- Missing `-` when there is no initrd.
- Wrong DTB for the board.
- Bad `stdout-path`.
- U-Boot loaded the DTB to an address overwritten by kernel decompression.

The correct no-initrd shape is:

```text
bootz kernel_addr - dtb_addr
```

The correct initramfs shape is:

```text
bootz kernel_addr initrd_addr:initrd_size dtb_addr
```

## 26A.4  Case 2: early output, then silence

When early messages appear but normal output disappears, the early console worked and the regular console did not.

Compare three values:

| Place | What to check |
|-------|---------------|
| U-Boot `bootargs` | `console=ttymxc0,115200` |
| DT `/chosen` | `stdout-path = &uart1;` or `serial0:115200n8` |
| Linux driver | i.MX UART driver enabled and UART node `status = "okay"` |

Useful bootargs:

```text
console=ttymxc0,115200 earlycon ignore_loglevel loglevel=8
```

If the log stops near a specific driver, add:

```text
initcall_debug
```

Then search the log:

```sh
target# dmesg | grep initcall
```

The last initcall before the stop is your suspect.

## 26A.5  Case 3: VFS cannot mount root

The kernel booted. It reached the point where it needs a root filesystem.

Typical panic:

```text
VFS: Cannot open root device "mmcblk0p2" or unknown-block(179,2)
Kernel panic - not syncing: VFS: Unable to mount root fs
```

Read it literally:

| Message part | Meaning |
|--------------|---------|
| `mmcblk0p2` | The requested root device. |
| `unknown-block(179,2)` | The block major/minor the kernel tried. |
| `Unable to mount root fs` | Device missing, driver missing, wrong filesystem, or partition not ready. |

Checklist:

1. Add `rootwait`.
2. Confirm the DT enables the SD/eMMC controller.
3. Confirm `CONFIG_MMC` and `CONFIG_MMC_SDHCI_ESDHC_IMX`.
4. Confirm `CONFIG_EXT4_FS` if the root partition is ext4.
5. Boot the Chapter 29 initramfs and run `cat /proc/partitions`.

If initramfs boots but SD root does not, the kernel is fine. The problem is storage, partitioning, or `root=`.

## 26A.6  Case 4: no working init

Typical panic:

```text
Run /sbin/init as init process
Failed to execute /sbin/init (error -2)
Kernel panic - not syncing: No working init found.
```

Error `-2` is `ENOENT`: file not found.

Try a shell:

```text
=> setenv bootargs 'console=ttymxc0,115200 earlycon root=/dev/mmcblk0p2 rw rootwait init=/bin/sh'
=> run boot_good
```

If `/bin/sh` runs, your rootfs exists but its init system is missing or broken.

If `/bin/sh` also fails:

- The rootfs may not contain `/bin/sh`.
- The binary may be for the wrong architecture.
- Dynamic libraries may be missing.
- `/dev/console` may be missing if devtmpfs is disabled.

Check from an initramfs:

```sh
# mount /dev/mmcblk0p2 /mnt
# ls -l /mnt/sbin/init /mnt/bin/sh
# file /mnt/bin/sh
# ls /mnt/lib
```

## 26A.7  Case 5: NFS root hangs

First prove local boot works. Then prove network from U-Boot. Then try NFS root.

Known-good NFS bootargs shape:

```text
console=ttymxc0,115200 earlycon
root=/dev/nfs
nfsroot=192.168.7.1:/home/you/imx6ull/rootfs,vers=3,nolock,tcp
ip=192.168.7.2:192.168.7.1:192.168.7.1:255.255.255.0:pa-mini:eth0:off
rw rootwait
```

Common mistakes:

- Host firewall blocks NFS.
- `/etc/exports` path is wrong.
- Missing `no_root_squash` on a development export.
- Kernel lacks `CONFIG_IP_PNP` or NFS root support.
- Wrong Ethernet DT pinctrl or PHY reset GPIO.

For development, use NFSv3 first. It is simpler to debug on small embedded boards.

## 26A.8  Minimum debug bootargs

Keep these three sets.

Normal:

```text
console=ttymxc0,115200 root=/dev/mmcblk0p2 rw rootwait
```

Verbose:

```text
console=ttymxc0,115200 earlycon ignore_loglevel loglevel=8 root=/dev/mmcblk0p2 rw rootwait
```

Probe timing:

```text
console=ttymxc0,115200 earlycon ignore_loglevel loglevel=8 initcall_debug root=/dev/mmcblk0p2 rw rootwait
```

Use the smallest one that answers the question.

## 26A.9  Lab

1. Boot with the known-good command and save the serial log.
2. Break the DTB address and confirm the symptom.
3. Remove `console=` and recover with `earlycon`.
4. Set `root=/dev/mmcblk9p9` and read the VFS panic.
5. Set `init=/does-not-exist` and read the init panic.
6. Add `initcall_debug` and find the longest initcall in the log.

## 26A.10  Pitfalls

- **Changing three things at once.** Change one variable, boot, save the log.
- **Ignoring the last line.** The last printed line is often the clue.
- **Using semicolons in boot scripts.** Use `&&` for commands that must stop on failure.
- **Assuming silence means dead CPU.** Often the kernel is running, but the console path is wrong.
- **Debugging rootfs before kernel boot.** If you have not seen the `VFS:` lines, you are not debugging rootfs yet.

## 26A.11  Going deeper

- `Documentation/admin-guide/kernel-parameters.txt`, for bootargs.
- `Documentation/arch/arm/booting.rst`, for the ARM boot contract.
- `init/do_mounts.c`, for root filesystem mounting.
- `init/main.c`, for init selection and `kernel_init()`.

---

**Previous:** [Chapter 26: Booting the kernel from U-Boot](ch26-booting-kernel-from-uboot.md)

**Next:** [Chapter 27: Device Tree: the contract between firmware and kernel](ch27-device-tree.md)
