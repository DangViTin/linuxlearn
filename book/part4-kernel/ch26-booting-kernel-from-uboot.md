---
chapter: 26
title: Booting the kernel from U-Boot
part: IV — The Kernel
estimated_pages: 14
status: draft
---

# Chapter 26 — Booting the kernel from U-Boot
**IRQ** - interrupt request, the signal path that tells the CPU or interrupt controller that hardware needs service.
**DMA** - Direct Memory Access. hardware moves data to or from memory without the CPU copying each byte.
**Buildroot** - a configuration-driven build system that produces a complete root filesystem and related images.

> **What:** transfer the `zImage` + `imx6ull-14x14-evk.dtb` we built in Chapter 25 to the board over TFTP, run `bootz` in U-Boot, and watch the first 30 lines of kernel output appear on the UART. Decode each line.
> **TFTP** - Trivial File Transfer Protocol, a simple network protocol U-Boot commonly uses to fetch kernels from the host.
> **U-Boot** - the bootloader that initializes enough hardware to load and start the Linux kernel.
>
> **Why:** From here on, Linux is running. Your job changes from writing the boot code to reading what the kernel prints.
>
> **Focus:** the **kernel boot log** as a diagnostic instrument. Every line means something specific. every successful boot prints predictable lines in predictable order. If you can recognise the first 30 lines, you can recognise which of them is missing or wrong on a board that's not booting.


## 26.1  The pre-boot contract

The kernel expects three things at the moment U-Boot transfers control:

| Condition | Value | How U-Boot establishes it |
|-----------|-------|--------------------------|
| **CPU state** | SVC mode, IRQ/FIQ masked, MMU off, caches off | `bootz` calls `cleanup_before_linux()` before the jump |
| **`r0`** | 0 (or boot-magic on some platforms; 0 is safe) | `bootz` sets |
| **`r1`** | "Machine number" for legacy ATAGS path; ignored on DT systems | `bootz` sets |
| **`r2`** | **Physical address of the DTB** | `bootz` sets to the DTB load address |

The first instruction the kernel executes is `stext` (in `arch/arm/kernel/head.S`). It begins by reading `r2` to find the DTB. If `r2` is wrong, the kernel cannot parse its hardware description and dies silently (no UART, no output, no diagnostic — because UART has not been initialised yet).

This is the *one* hardware contract every ARM Linux boot relies on. If `r2` is correct, the kernel almost always boots. If `r2` is wrong, you see nothing on the UART.

## 26.2  The three-command boot

From the U-Boot prompt:

```
=> tftp 0x82000000 zImage
=> tftp 0x83000000 imx6ull.dtb
=> bootz 0x82000000 - 0x83000000
```

What each does:

1. `tftp 0x82000000 zImage` — pulls the kernel from your TFTP server into DRAM at `0x82000000`. The address was chosen for two reasons: it's far enough above the DRAM base (`0x80000000`) that U-Boot's image (currently relocated near the top of DRAM) doesn't conflict, and it's far enough below that the kernel has room to decompress upward into.
2. `tftp 0x83000000 imx6ull.dtb` — pulls the DT blob to a second location. ~50 KB.
3. `bootz 0x82000000 - 0x83000000` — start a zImage at `0x82000000`, no initrd (`-`), DTB at `0x83000000`. This is the key step. U-Boot sets `r2 = 0x83000000`, jumps to the kernel, and is done.

You can save these as an env one-shot:

```
=> setenv bootnet 'tftp 0x82000000 zImage; tftp 0x83000000 imx6ull.dtb; bootz 0x82000000 - 0x83000000'
=> setenv bootcmd 'run bootnet'
=> saveenv
```

Now every power-on auto-boots over the network.

## 26.3  The cmdline

Before `bootz`, set `bootargs`:

```
=> setenv bootargs 'console=ttymxc0,115200 earlycon root=/dev/mmcblk0p2 rw rootwait'
=> saveenv
```

Token by token:

- **`console=ttymxc0,115200`** — once the i.MX UART driver loads, route `printk` to UART1 at 115200 baud. *If this token is wrong, you see no kernel output.* The driver name `ttymxc0` is the i.MX-specific convention. other SoCs use `ttyS0`, `ttyAMA0`, etc.
- **`earlycon`** — very early UART printk *before* the full driver loads. Reads the DT's `chosen.stdout-path` to find which UART. Without `earlycon`, the first ~10 boot lines stay in a buffer. You see them only when the regular console driver loads.
- **`root=/dev/mmcblk0p2`** — what device holds the rootfs. We will return to this in Part V. For the first boot we may not have a usable rootfs yet, in which case the kernel panics. That's fine for *this* chapter — we're verifying kernel boot, not full system boot.
> **MCU bridge:** Think of the rootfs as the firmware image's file-backed runtime environment. On an MCU you link everything into flash. On Linux, programs and config live in this mounted tree.
**rootfs** - root filesystem, the directory tree mounted at / that contains /bin, /etc, /dev, and libraries.
- **`rw`** — mount the root read-write.
- **`rootwait`** — don't panic if `root=` isn't immediately ready. wait. Always safe to include.

A development cmdline, with NFS root, looks like:
**NFS** - Network File System, which lets the target mount a host directory over Ethernet during development.

```
console=ttymxc0,115200 earlycon
root=/dev/nfs nfsroot=192.168.7.1:/home/you/imx6ull/rootfs,vers=3,nolock,tcp
ip=192.168.7.2:192.168.7.1:192.168.7.1:255.255.255.0::eth0:off
rw rootwait
```

We'll use this from Chapter 31 onward.

## 26.4  What you should see

```
=> run bootnet
Using FEC0 device
TFTP from server 192.168.7.1; our IP address is 192.168.7.2
Filename 'zImage'.
Load address: 0x82000000
Loading: ########################  4.5 MiB/s  done
Bytes transferred = 6291456 (600000 hex)
Using FEC0 device
TFTP from server 192.168.7.1; our IP address is 192.168.7.2
Filename 'imx6ull.dtb'.
Load address: 0x83000000
Loading: #  100 KiB/s  done
Bytes transferred = 56320 (dc00 hex)
## Flattened Device Tree blob at 83000000
   Booting using the fdt blob at 0x83000000
   Loading Device Tree to 8ffec000, end 8ffffdff ... OK

Starting kernel ...

[    0.000000] Booting Linux on physical CPU 0x0
[    0.000000] Linux version 6.6.0 (you@host) (arm-none-linux-gnueabihf-gcc 11.4.0) ...
[    0.000000] CPU: ARMv7 Processor [410fc075] revision 5 (ARMv7), cr=10c5387d
[    0.000000] CPU: div instructions available: patching division code
[    0.000000] CPU: PIPT / VIPT nonaliasing data cache, VIPT aliasing instruction cache
[    0.000000] OF: fdt: Machine model: Freescale i.MX6 ULL 14x14 EVK Board
[    0.000000] Memory policy: Data cache writealloc
[    0.000000] efi: UEFI not found.
[    0.000000] cma: Reserved 64 MiB at 0x0000000094000000
[    0.000000] Zone ranges:
[    0.000000]   Normal   [mem 0x0000000080000000-0x000000009fffffff]
[    0.000000]   HighMem  empty
[    0.000000] Movable zone start for each node
[    0.000000] Early memory node ranges
[    0.000000]   node   0: [mem 0x0000000080000000-0x000000009fffffff]
[    0.000000] Initmem setup node 0 [mem 0x0000000080000000-0x000000009fffffff]
[    0.000000] percpu: Embedded 13 pages/cpu s24336 r8192 d20720 u53248
[    0.000000] Built 1 zonelists, mobility grouping on.  Total pages: 130048
[    0.000000] Kernel command line: console=ttymxc0,115200 earlycon root=/dev/mmcblk0p2 rw rootwait
[    0.000000] Dentry cache hash table entries: 65536 (order: 6, 262144 bytes, linear)
[    0.000000] Inode-cache hash table entries: 32768 (order: 5, 131072 bytes, linear)
[    0.000000] mem auto-init: stack:all(zero), heap alloc:off, heap free:off
[    0.000000] Memory: 444184K/524288K available (10240K kernel code, 1112K rwdata,
                3144K rodata, 1024K init, 268K bss, 14760K reserved, 65536K cma-reserved,
                0K highmem)
[    0.000000] SLUB: HWalign=64, Order=0-3, MinObjects=0, CPUs=1, Nodes=1
...
```

Read every line. Each tells you something concrete:

| Line | What it tells you |
|------|-------------------|
| `Booting Linux on physical CPU 0x0` | CPU0 has booted (SMP would say `0x0–0xN`). On i.MX6ULL there's only one core. |
| `Linux version 6.6.0 ...` | The kernel version + the toolchain that built it. Cross-check this against your build. |
| `CPU: ARMv7 Processor [410fc075]` | The MIDR (Main ID Register) of the core. `0x410FC075` decodes as: implementer `0x41` (ARM), variant `0xF`, architecture `0xC`, primary part `0xC07` (Cortex-A7), revision `r0p5`. |
| `CPU: div instructions available` | The CPU has hardware integer division. Some Cortex-A profiles don't. |
| `CPU: PIPT / VIPT nonaliasing data cache, VIPT aliasing instruction cache` | The cache aliasing properties. Matters for DMA correctness. |
| `OF: fdt: Machine model: Freescale i.MX6 ULL 14x14 EVK Board` | **The model string from the DT root node.** Confirms the right DTB loaded. |
| `Memory policy: Data cache writealloc` | The cache write policy the kernel chose. |
| `cma: Reserved 64 MiB at 0x94000000` | Contiguous Memory Allocator carved out 64 MiB. Used for big DMA buffers (framebuffer, camera). |
| `Zone ranges: Normal [mem 0x80000000-0x9fffffff]` | The 512 MiB of DRAM, mapped as Normal cacheable memory (Ch 17). |
| `Kernel command line: ...` | The literal `bootargs` U-Boot passed. **Verify this matches what you set.** |
| `Memory: 444184K/524288K available ...` | Of 524 288 KB DRAM, 444 184 KB is usable for user memory; the rest is kernel code/data/reserved. |
| `SLUB: HWalign=64, Order=0-3` | The slab allocator is up. CPU's cache-line size is 64 bytes. |

After Memory: SLUB, output continues for another 50–100 lines as drivers probe. The kernel reaches user-space when it prints:

```
[    2.158972] EXT4-fs (mmcblk0p2): mounted filesystem with ordered data mode...
[    2.193456] VFS: Mounted root (ext4 filesystem) on device 179:2.
[    2.198321] Run /sbin/init as init process

Welcome to Buildroot
buildroot login:
```

That last "Mounted root" line is the threshold: the kernel has finished its own initialisation and is now executing user-space. From here, Part V takes over.

## 26.5  When it doesn't boot — what to look for

If you see *nothing at all* after `Starting kernel ...`:

- **The DTB address in `r2` is wrong.** Usually `bootz 0x82000000 - 0x83000000` is correct. If you type `bootz 0x82000000 0x83000000` (no `-`), U-Boot reads `0x83000000` as the initrd address. The kernel then gets no DTB. Symptom: silence.
- **Wrong DTB for the board.** Kernel finds *a* DTB but it describes hardware the actual board doesn't have. Symptom: silence after `Starting kernel ...`. Cross-check the DT model line by trying earlycon (see below).
- **`console=` token wrong.** Kernel boots fine. UART driver loads. but printk is redirected somewhere else. Symptom: nothing after `Starting kernel ...`. Add `earlycon` to bootargs to see *very* early printk before the driver loads — if those appear, the regular console is the problem.
- **DDR not all working.** The kernel does an early memtest of sorts. If DRAM has bit errors it usually panics early but the panic might not reach the UART. Rerun the U-Boot `mtest` first.
**DDR** - external DRAM that must be configured and trained before most software can run from it.

If you see *some output then silence*:

- **Driver hang.** Look at the *last* line printed. The next subsystem to probe is likely hanging. A common cause is the PMIC on I²C. If I²C is broken, the regulators stay off. Devices fail to enumerate, and the kernel hangs.
> **MCU bridge:** Think of a PMIC like a programmable power-tree supervisor: it replaces discrete enables and LDO assumptions with sequenced rails the kernel can model.
**PMIC** - Power Management IC, a chip that sequences and regulates the board's voltage rails.
- **VFS panic** ("Cannot open root device 'mmcblkXpY'"): rootfs not found. The panic message is clear. Fix the `root=` argument.
- **`Kernel panic - not syncing: VFS: Unable to mount root fs`**: same as above. The kernel says exactly what's wrong.

## 26.6  Verifying with earlycon

`earlycon` activates a tiny inline UART driver during `start_kernel()` (Chapter 28), long before the regular `console=` driver loads. It's invaluable for diagnosing "kernel boots but I see no output" issues, because earlycon is much harder to misconfigure.

Add to bootargs:

```
earlycon
```

…or explicitly:

```
earlycon=ec_imx6q,0x02020000
```

The first form reads the UART address from the DT's `chosen.stdout-path` (an i.MX6ULL DTB already sets this). The second form pins it explicitly to the UART1 register base.

With earlycon active, you'll see ~5 extra lines printed *before* the normal "Booting Linux on physical CPU 0x0" — these are emitted by setup_arch() before the regular console driver loads.

## 26.7  Lab

1. **Boot the kernel.** Confirm you see the boot log. If the kernel panics on rootfs (you don't have one yet), that's fine — the goal is "kernel ran and reached the rootfs-mount step."
2. **Save the boot log.** `picocom`'s capture mode (`-L log.txt`) writes the serial stream to a file. Save your first successful boot. You will diff against it later when something changes.
3. **Mismatch the DT.** Try `bootz 0x82000000 - 0x83000000` with `imx6ull-9x9-evk.dtb` instead of `imx6ull-14x14-evk.dtb`. Observe what changes in the boot log (probably the model line. maybe other things if pin assignments differ enough that drivers panic).
4. **Bad cmdline.** Set `bootargs` to omit `console=`. Boot. observe silence. Add `earlycon`. observe partial output. Restore.
5. **Bad DTB address.** Forget the `-` in `bootz <kernel> - <dtb>` and use `bootz <kernel> <dtb>`. Observe silence (kernel believes `<dtb>` is an initrd. there is no DTB at `r2`).

## 26.8  Pitfalls

- **DT load address conflicts with kernel decompression area.** If the kernel decompresses to a region that overlaps where you loaded the DTB, the DT gets corrupted partway through boot and the kernel hangs at a random point. The address `0x83000000` for DTB is safe because the kernel decompresses from `0x82000000` upward but stops well before 16 MiB (the kernel is < 16 MiB). For *very* large kernels (CONFIG_DEBUG_INFO, huge configs), use `0x88000000` for DTB instead.
- **Forgetting `cleanup_before_linux()`.** U-Boot's `bootz` does this automatically. If you wrote your own jump-to-kernel code (don't), you need to flush caches and disable MMU before transferring.
**MMU** - Memory Management Unit, hardware that translates virtual addresses to physical addresses and enforces permissions.
- **Kernel built for a different ARM revision.** A `zImage` built with `CONFIG_ARCH_MULTI_V6_V7` or `CONFIG_ARCH_MULTI_V7` runs on Cortex-A7. (`CONFIG_ARCH_MULTI_V7_ONLY` is *not* a mainline symbol — earlier drafts of this chapter listed it. ignore.) A 64-bit kernel (`CONFIG_ARM64`) will not run on Cortex-A7. Symptom: undefined instruction at `stext`. A Thumb-2-only kernel (`CONFIG_THUMB2_KERNEL=y`) requires the bootloader to enter in Thumb state. If your bootloader hands off in ARM state to a Thumb kernel, you fault on the very first instruction.
- **Wrong board's DTB.** Loading the i.MX8MP EVK DTB on an i.MX6ULL board: the kernel reads the DT's `compatible` root property, looks for `fsl,imx6ull` (or the matching SoC), doesn't find it, and panics in `setup_machine_fdt()`. Sometimes silently.
- **`root=` pointing at something not ready by the time VFS mounts root.** USB-stick root devices need `rootwait` because USB enumeration is slow. SD cards are usually fast enough that you can skip `rootwait` — but always safe to add.

## 26.9  Going deeper

- **`arch/arm/boot/compressed/head.S`** — read the decompressor stub. It is short and educational.
- **`init/main.c`** — the file `start_kernel()` lives in. We trace it line-by-line in Chapter 28.
- **`Documentation/admin-guide/kernel-parameters.txt`** — every cmdline parameter the kernel understands. ~1500 lines. Skim the headers. You'll come back for specific tokens.
- **`Documentation/arch/arm/booting.rst`** — the boot contract (`r0`/`r1`/`r2`) in the canonical place.
- **The kernel's `printk` format** — `<5>` (KERN_NOTICE), `<6>` (KERN_INFO), `<7>` (KERN_DEBUG) prefix codes. Mostly invisible at boot. visible when you use `dmesg --level=info` etc.

> Next chapter: **Chapter 27 — Device Tree: the contract between firmware and kernel.** We open `imx6ull-14x14-evk.dts` and walk every node from the root down. The DT is the single biggest mental shift for an MCU engineer. We spend extra time here.
> **MCU bridge:** Think of Device Tree like a board-level hardware description table that replaces hard-coded #define LED_PORT GPIOA decisions. Unlike an MCU header, the kernel parses it at boot and matches it to drivers.
> **Device Tree** - a data file that describes board hardware to the Linux kernel instead of hard-coding it in C.
