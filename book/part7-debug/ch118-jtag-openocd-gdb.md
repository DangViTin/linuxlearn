---
chapter: 118
title: JTAG, OpenOCD, GDB at every layer
part: VIII — Debug, production, advanced
estimated_pages: 20
status: draft
---

# Chapter 118 — JTAG, OpenOCD, GDB at every layer

> **What:** the **hardware-level debug stack**: **JTAG adapters** (FT2232H-based generic, J-Link, SEGGER pro), **OpenOCD** as the software bridge between adapter and target, and **GDB** as the user interface. We wire JTAG to the i.MX6ULL's debug header, write an OpenOCD config, halt the CPU at the very first reset vector instruction, single-step through U-Boot, attach to the running kernel with full `vmlinux` symbol resolution, and inspect a kernel module's variables interactively.
> **Why:** the day your bare-metal LED doesn't blink and `printk` isn't an option (because the kernel hasn't started), JTAG is the only ground truth. Same when U-Boot hangs in DCD execution and you have nothing to print to. Same when the kernel oopses in early-boot before serial init. JTAG lets you read every register, dump every memory region, set hardware breakpoints, and step a single instruction at a time — at any layer (bare-metal, bootloader, kernel, user-space). This is the difference between "I guess the boot fails somewhere in CCM init" and "I see XTAL_24M is at 0 mV; the crystal isn't running."
> **Focus:** **OpenOCD is the bridge: it speaks USB to the JTAG adapter and exposes a GDB-server on TCP; GDB connects, fetches symbols from your ELF, and gives you the familiar `b`, `n`, `s`, `p` commands**. The tricky parts are: getting the adapter's USB-IDs right for OpenOCD, choosing the right *target* config (Cortex-A7 vs Cortex-M differ massively), handling Cortex-A's complications (multi-CPU, secure-vs-non-secure world, MMU on/off), and giving GDB the right symbol files at the right times (one ELF for bare-metal, another for U-Boot, another for kernel + per-module symbols).

## 118.1  JTAG basics — the 4-wire debug bus

JTAG (IEEE 1149.1) is a serial scan chain. Four mandatory wires + 1 optional + 1 hardware reset:

```
   TDI  — Test Data In   (host → target shift)
   TDO  — Test Data Out  (target → host shift)
   TCK  — Test Clock     (host drives)
   TMS  — Test Mode Sel  (host steers FSM)
   TRST — Test Reset     (optional; if absent, soft-reset via TMS sequence)
   SRST — System Reset   (optional; resets the SoC itself)
```

The target has a TAP (Test Access Port) state machine; TMS steers it through states (Run-Test-Idle, Shift-IR, Shift-DR, etc.). The host sends bits via TDI, sees them shifted back via TDO. Higher-level commands (read register, read memory, halt CPU, single-step) are encoded as sequences of these primitives.

ARM Cortex-A debug uses the **CoreSight** extension on top of JTAG (or SWD on Cortex-M; Cortex-A uses JTAG). Within CoreSight, **DAP** (Debug Access Port), **ETM** (trace), **TPIU** (trace output) live.

## 118.2  Adapter comparison

| | FT2232H breakout | SEGGER J-Link EDU | SEGGER J-Link Pro | NXP MCU-Link Pro |
|---|---|---|---|---|
| Cost | $15–25 | $60 (non-commercial) | $400 | $50 |
| Speed | up to 30 MHz JTAG clock | up to 50 MHz | 50+ MHz | 30 MHz |
| OpenOCD support | excellent | yes | yes | partial |
| Proprietary tools | n/a | J-Link GDBServer (closed) | yes | proprietary |
| SWD support | yes | yes | yes | yes |
| Voltage flexibility | 1.8 – 5 V | 1.2 – 5 V | 1.2 – 5 V | 1.8 – 5 V |
| Use case | hobbyist + most pro work | dev | production volume | NXP-specific |

**Pick guide:**
- **FT2232H breakout** (e.g., Olimex ARM-USB-OCD-H, FTDI's eval board) — the workhorse for OpenOCD. Cheap, works with everything.
- **J-Link EDU** — when you want SEGGER's polished GDBServer + Ozone GUI, non-commercial use.
- **J-Link Pro** — production / commercial.

## 118.3  Wiring JTAG to the Point Atom

The Point Atom MINI exposes the JTAG header on a 2.54 mm 10-pin connector (or 20-pin Cortex JTAG; check your specific board revision). Pinout (10-pin Cortex):

```
   1  VTREF       — target voltage reference (3.3 V on i.MX6ULL)
   2  TMS / SWDIO
   3  GND
   4  TCK / SWCLK
   5  GND
   6  TDO / SWO
   7  KEY         — present-pin (low if connected)
   8  TDI         — JTAG only
   9  GND
   10 RESET       — SRST
```

Wire to the adapter's matching connector (often it's the same Cortex pinout).

**Important**: VTREF must be 3.3 V; the adapter senses this and adjusts its IO level. Misconfigured VTREF (5 V into a 3.3 V SoC) = blown JTAG pins on the SoC. Permanent.

## 118.4  OpenOCD config

OpenOCD needs three things: interface config (adapter), target config (CPU), and board config (memory map, reset behavior).

`/etc/openocd/imx6ull-pa.cfg`:

```tcl
# Adapter — FTDI-based interface (e.g. Olimex ARM-USB-OCD-H)
source [find interface/ftdi/olimex-arm-usb-ocd-h.cfg]
adapter speed 1000      ;# Start at 1 MHz; ramp up to 6 MHz after init

# i.MX6ULL is single-core Cortex-A7
source [find target/imx6ull.cfg]

# Reset config: SRST = system reset; TRST optional
reset_config srst_only srst_push_pull

# Board-specific: where SDRAM lives, the OCRAM, etc.
set OCRAM_BASE 0x00900000
set OCRAM_SIZE 0x00020000      ;# 128 KB
set DRAM_BASE  0x80000000
set DRAM_SIZE  0x20000000      ;# 512 MB

# Init script — runs at openocd startup
init
reset halt
```

The `target/imx6ull.cfg` (shipped with OpenOCD) declares the CoreSight DAP, the A7 core, the TAP-IDCODE expected from the chip. If your SoC variant isn't in stock OpenOCD, you may need a custom file.

Run:

```sh
openocd -f /etc/openocd/imx6ull-pa.cfg
# Open On-Chip Debugger 0.12.0+...
# Info : Listening on port 6666 for tcl connections
# Info : Listening on port 4444 for telnet connections
# Info : auto-selecting first available session transport "jtag"
# Info : clock speed 1000 kHz
# Info : JTAG tap: imx6ull.cpu tap/device found: 0x5ba00477 (mfg: 0x23b ARM, part: 0xba00, ver: 0x5)
# Info : Listening on port 3333 for gdb connections
# Info : target halted in ARM state due to debug-request
```

OpenOCD listens on:
- TCP 3333 — GDB protocol
- TCP 4444 — telnet (for direct OpenOCD commands)
- TCP 6666 — TCL

You can `telnet localhost 4444` and issue raw commands:

```
> reset halt
> mdw 0x00900000 4
0x00900000: 12345678 9abcdef0 deadbeef cafebabe
> reg
> mww 0x20a4000 0x00000001     ;# write a register
> resume
```

## 118.5  GDB connected to OpenOCD — bare-metal

For Ch 9's LED-in-assembly bare-metal example:

```sh
arm-linux-gnueabihf-gdb led.elf
(gdb) target remote :3333
Remote debugging using :3333
0x00900000 in ?? ()
(gdb) load                        # write the ELF to target memory
Loading section .text, size 0x40 lma 0x900000
Start address 0x900000
(gdb) break _start
Breakpoint 1 at 0x900000: file led.S, line 10.
(gdb) continue
Breakpoint 1, _start () at led.S:10
10        ldr r0, =GPIO1_BASE
(gdb) step
(gdb) info registers
r0  0x209c000  34602880
r1  ...
(gdb) x/16w 0x209c000             # examine GPIO1 register block
```

Single-step a literal assembly program; watch registers change; see exactly which instruction sets the GPIO bit that turns the LED on.

This is *how you learn* the bare-metal layer — by stepping every instruction and matching to the reference manual.

## 118.6  GDB on U-Boot

```sh
arm-linux-gnueabihf-gdb u-boot
(gdb) target remote :3333
(gdb) symbol-file u-boot          # already loaded
(gdb) add-symbol-file spl/u-boot-spl 0x00908000   # SPL lives in OCRAM
(gdb) break board_init_f
(gdb) continue
Breakpoint 1, board_init_f (boot_flags=0) at common/board_f.c:880
880        gd = (gd_t *)((CONFIG_SYS_INIT_SP_ADDR) & ~7) - 16;
(gdb) next
881        ...
```

You're now stepping through U-Boot's C code, single-line at a time, in the same way as gdb on a user-space binary. Set breakpoints in `board_init_r`, in `cmd_bootm`, anywhere.

U-Boot is built without `-O2` if you `make DEBUG=1`; with default `-O2` some variables are optimized out — debug builds give cleaner GDB experience.

## 118.7  GDB on the running kernel — `vmlinux` + KASLR

For kernel debug, you need:
1. `CONFIG_DEBUG_KERNEL=y`, `CONFIG_DEBUG_INFO=y`, `CONFIG_GDB_SCRIPTS=y` in kconfig.
2. `vmlinux` (the unstripped ELF in the kernel build dir).
3. KASLR (Kernel Address Space Layout Randomization) disabled, or the offset known.

```sh
# Build kernel with debug info
make ARCH=arm CROSS_COMPILE=arm-linux-gnueabihf- imx_v7_defconfig
echo CONFIG_DEBUG_INFO=y >> .config
echo CONFIG_GDB_SCRIPTS=y >> .config
make ARCH=arm zImage modules

# Connect
arm-linux-gnueabihf-gdb vmlinux
(gdb) target remote :3333
(gdb) lx-symbols                   # the kernel GDB scripts: load module symbols too
(gdb) break start_kernel
(gdb) continue
... U-Boot runs, kernel handoff happens, breakpoint hits ...
Breakpoint 1, start_kernel () at init/main.c:925
925     {
(gdb) bt
#0  start_kernel () at init/main.c:925
#1  0x80101000 in stext () at arch/arm/kernel/head.S:115
```

The `lx-symbols` GDB command (part of the kernel's `scripts/gdb/` Python helpers) iterates `/proc/modules`-style data inside the kernel to find loaded modules and load each `.ko`'s symbols at the correct offset. Now `break my_driver_probe` works on a dynamically loaded driver.

## 118.8  Inspecting kernel state with `lx-*` commands

The kernel's GDB scripts (`scripts/gdb/linux/`):

```
(gdb) lx-dmesg                    # the printk ring buffer, formatted
(gdb) lx-ps                        # task list
(gdb) lx-lsmod                     # loaded modules
(gdb) lx-cmdline                   # boot command line
(gdb) lx-version                   # uname-equivalent
(gdb) lx-iomem                     # like /proc/iomem
(gdb) p $lx_current()->comm        # the running task's name
(gdb) p init_task                  # init process struct
```

These walk the kernel's in-memory data structures the same way `procfs` does, but live and without needing the kernel itself functional (debug a wedged kernel).

## 118.9  Hardware breakpoints + watchpoints

Cortex-A7 has 6 hardware breakpoints and 4 watchpoints (counts may vary). GDB uses them transparently:

```
(gdb) hbreak my_function              # hardware breakpoint
(gdb) watch *(int *)0x80100000        # break on write to this addr
(gdb) rwatch global_var                # break on read
```

Hardware breakpoints are essential for read-only memory (you can't replace the instruction with a breakpoint trap if the memory is in flash/ROM). Software breakpoints (default `break`) replace the instruction with an undefined-instruction → exception → debug.

## 118.10  Reset behavior — the trickiest part

The classic problem: target is in some unknown state from a previous crash. How to halt at the very first instruction after reset?

OpenOCD's `reset halt` does:
1. Assert SRST.
2. Configure the CPU's debug-halt-on-reset bit (DBGEN + HRR in DSCR).
3. Deassert SRST.
4. CPU starts, immediately halts at PC = reset vector (= Boot ROM entry).

To debug ROM execution: from `reset halt` state, set a breakpoint on the first DCD-runtime address, `resume`, watch ROM execute DCD then jump to your image.

`reset init` runs OpenOCD's TCL "init" hooks first (typically configure clocks/DDR via OpenOCD before loading your binary) — useful for debugging code that requires DDR but you don't want to depend on the Boot ROM doing it.

## 118.11  Lab

1. **OpenOCD up.** Wire JTAG (FT2232H breakout). Run OpenOCD with your config; verify TAP IDCODE.
2. **Halt + dump.** `telnet :4444`; `reset halt`; `mdw 0x900000 16` — see what's in OCRAM.
3. **Single-step bare-metal LED.** Load Ch 9's bare-metal binary; set breakpoint on first instruction; step every instruction; observe register changes.
4. **Bare-metal DDR debug.** Run Ch 14's DDR3 init. Set breakpoint on `mmdc_init` first instruction. Step through; verify MMDC registers reach expected values. If DRAM doesn't work, this is *the* way to find which MDCFGn value was wrong.
5. **U-Boot stepping.** Build U-Boot with `-O0` if needed. Halt at `_start`, step into SPL init, watch DRAM come up, watch relocation copy U-Boot to high DRAM.
6. **Kernel attach.** Boot kernel from SD; from another shell, run `gdb vmlinux` + `target remote`. Use `lx-dmesg` to see the kernel log. Set a soft breakpoint on `printk`; trigger a printk from `/proc/sysrq-trigger`; see it hit.
7. **Module debugging.** `insmod` a kernel module of your own (Ch 36's hello-LKM). `lx-symbols`; `break my_init`; `rmmod` then `insmod` → breakpoint hits.
8. **Watch a corruption.** Set a watchpoint on a kernel structure (e.g., `init_task.comm`); write to it from user-space via `/proc/self/comm`; see watchpoint trigger.
9. **Production fuse.** Look up the i.MX6ULL "JTAG disable" fuse. Read it via OpenOCD. Verify it's *not* blown (or you've bricked debug access). In production: blow this fuse to prevent attacker debug, but accept the support cost.

## 118.12  Pitfalls

- **VTREF wrong.** Adapter at 5 V into 3.3 V SoC fries the JTAG pins. Always confirm VTREF before connecting.
- **JTAG disabled by fuse.** Some boards ship with the SJC_DISABLE eFuse blown for security. JTAG silently doesn't connect. Verify with a fresh chip.
- **SRST not wired.** Without SRST, OpenOCD's `reset` is a soft-reset (TMS sequence); some states (CPU in WFI) can't be reset this way. Wire SRST for production debug.
- **TCK too fast for unhardened wiring.** Long flying-wire JTAG (>10 cm) needs slower TCK (≤ 1 MHz). Start at 1 MHz; ramp up only if reliable.
- **Multi-core target.** If your SoC is multi-core (i.MX6ULL is single-core; most newer chips are multi), OpenOCD config must declare each core separately.
- **Cortex-A MMU on — virtual vs physical addresses.** After MMU is enabled, `mdw 0x80100000` queries virtual address; sometimes you want physical. Use `mdw phys 0x80100000` in OpenOCD.
- **GDB `monitor` commands.** You can run OpenOCD commands from GDB via `monitor`: `monitor reset halt`; useful when you don't want to switch windows.
- **Symbols missing for kernel module.** `lx-symbols` works only on debug-built kernels; check `CONFIG_GDB_SCRIPTS=y`.
- **KASLR.** Kernel address randomization shifts vmlinux symbols at each boot. Disable for debug (`nokaslr` boot arg) or use `add-symbol-file` with the runtime offset.
- **OpenOCD config drift.** Each OpenOCD version slightly different config syntax; tested-known-good configs in your repo save hours.
- **Adapter unplugged mid-session.** OpenOCD doesn't recover; restart it. GDB needs `target remote :3333` again.
- **HW breakpoint exhaustion.** Cortex-A7 has 6 HW breakpoints; if you set 7, GDB silently uses software for the 7th, which fails on ROM/flash.

## 118.13  Going deeper

- **OpenOCD User Guide** (https://openocd.org/doc/html/) — the canonical reference.
- **ARM Cortex-A Series Programmer's Guide, ch. on Debug** — CoreSight, DAP, ETM in depth.
- **`scripts/gdb/`** in Linux source — the kernel's GDB scripts.
- **`Documentation/dev-tools/gdb-kernel-debugging.rst`** in Linux source.
- **NXP IMX6ULL Reference Manual, ch. 56 (System JTAG Controller)** — fuse and security configuration.
- **SEGGER J-Link User Guide** — for the J-Link path.
- **Ch 119** — kernel debugging without JTAG (`ftrace`, `kgdb`, eBPF).
- **Ch 120** — user-space debugging with gdbserver + perf + strace.
- **Ch 125A** — VSCode + gdbserver for the IDE-driven debug workflow.

---

> Next chapter: **Chapter 119 — Kernel debugging without JTAG** — ftrace, eBPF, KGDB.
