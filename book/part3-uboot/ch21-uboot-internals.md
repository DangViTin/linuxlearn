---
chapter: 21
title: U-Boot internals — relocation, environment, commands, driver model
part: III — U-Boot, deeply
estimated_pages: 26
status: draft
---

# Chapter 21 — U-Boot internals

> **What:** a complete narrative tour of full U-Boot — from `_start` to the `=>` prompt to a typed command running — with the source paths cited at every step. Plus the three subsystems that you will touch most often as a custom-board engineer: the **environment**, the **command system**, and the **driver model (DM)**.
> **Why:** U-Boot is the bootloader most likely to need *your* code in a real project. Knowing where to put it, and which existing patterns to follow, is half the work.
> **Focus:** **relocation** — the moment U-Boot copies itself from its load address to high DRAM and patches every pointer. Once you understand relocation, every confusing "why is `&foo` not what I expect?" question dissolves.

## 21.1  The full-U-Boot boot flow, end to end

Full U-Boot's job, once SPL hands it control:

1. `_start` (in `arch/arm/cpu/armv7/start.S`) — assembly entry, mode/IRQ setup, calls `_main`.
2. `_main` (in `arch/arm/lib/crt0.S`) — sets a temporary stack in DRAM, calls `board_init_f`.
3. `board_init_f` (in `common/board_f.c`) — runs a sequence of "init functions" that detect RAM, set up the global data structure (`gd_t`), allocate space for the relocated copy of U-Boot.
4. `relocate_code` (in `arch/arm/lib/relocate.S`) — copies U-Boot from its initial load address to the chosen "high DRAM" relocation target, fixes up all symbol references.
5. `relocate_vectors` — similar, for the exception vectors.
6. `board_init_r` (in `common/board_r.c`) — runs a second sequence of init functions in the relocated copy; this is where most subsystems (MMC, NET, USB, ENV) come up.
7. `run_main_loop` → `main_loop` (in `common/main.c`) — drains the autoboot timer, reads input, dispatches commands.
8. `cli_loop` (in `common/cli.c`) — the interactive shell.
9. `cmd_process` — the command dispatcher; we trace it in §21.5.

Each step has a name we can grep for. Each step is < 200 lines. Total reading time, all of it, end-to-end, ~3 hours. Do it once and the bootloader stops being a black box.

## 21.1a  The linker script and the named address-range symbols

Before tracing code, look at where it lives. The linker script `u-boot.lds` (generated at the top of the source tree only **after** a successful build — pre-build there's only the unprocessed `arch/arm/cpu/u-boot.lds`) defines several symbols that the U-Boot startup and relocation code uses by name. A representative `u-boot.map`-derived snapshot for our `mx6ull_14x14_evk_defconfig` build:

| Symbol | Sample value | Meaning |
|--------|--------------|---------|
| `__image_copy_start` | `0x87800000` | First byte of U-Boot's code image |
| `_start` | `0x87800000` | Same — the entry point (defined in `arch/arm/lib/vectors.S`) |
| `__image_copy_end` | `0x8785DD54` | One past the last byte of code+data |
| `__rel_dyn_start` | `0x8785DD54` | Start of the `.rel.dyn` relocation table |
| `__rel_dyn_end` | `0x878668F4` | End of the relocation table |
| `_image_binary_end` | `0x878668F4` | The "loadable image" ends here |
| `__bss_start` | `0x878668F4` | Start of `.bss` (zero-initialized at runtime) |
| `__bss_end` | `0x878A8E74` | End of `.bss` |

The starting address `0x87800000` is what makes the EVK config's `CONFIG_SYS_TEXT_BASE` what it is. It's a deliberate choice: the kernel's typical load address is `0x82000000` (= 32 MB into DRAM), and U-Boot relocates itself **above** the kernel's eventual landing zone so it can `bootz` without writing over itself.

**Every value in this table changes each time you change a CONFIG_FOO, add a feature, or upgrade compilers.** Always read your own `u-boot.map` to confirm. The relative *structure* — what symbols exist, their meaning — is what's stable across builds.

`u-boot.map` is the file to grep when chasing any "what address is this symbol at?" question. It is generated automatically by the linker; no extra command needed.

## 21.2  `_start` and `_main`

Open `arch/arm/cpu/armv7/start.S`. We saw this in Chapter 20:

```asm
ENTRY(reset)
    b   save_boot_params
save_boot_params_ret:
    /* CPSR → SVC mode, IRQ/FIQ masked */
    bl  cpu_init_cp15
    bl  cpu_init_crit
    bl  _main
```

`_main` is in `arch/arm/lib/crt0.S` (shared between SPL and full U-Boot, with `CONFIG_SPL_BUILD` switching paths):

```asm
ENTRY(_main)
    /*
     * Set up initial C runtime environment and call board_init_f(0).
     */
    ldr sp, =(CONFIG_SYS_INIT_SP_ADDR)   @ early stack in OCRAM or DRAM
    bic sp, sp, #7                       @ 8-byte alignment
    mov r0, sp
    bl  board_init_f_alloc_reserve       @ allocate gd_t early in stack
    mov sp, r0
    bl  board_init_f_init_reserve

    mov r0, #0
    bl  board_init_f                     @ <-- our journey into C
```

A few worth knowing:

- `CONFIG_SYS_INIT_SP_ADDR` is per-board. For the EVK it's a high address near the top of OCRAM — *before* relocation, U-Boot uses OCRAM for its stack, even though its code is already in DRAM (SPL put it there). After relocation, U-Boot moves the stack into high DRAM.
- `gd_t` is "global data" — a single structure that holds pointers and state used everywhere. `board_init_f_alloc_reserve` carves space for it from the stack.

### Walking the SP arithmetic for the EVK

The macro expansion in `include/configs/mx6ullevk.h`:

```c
#define CONFIG_SYS_INIT_RAM_ADDR       IRAM_BASE_ADDR      /* 0x00900000 */
#define CONFIG_SYS_INIT_RAM_SIZE       IRAM_SIZE           /* 0x00020000 = 128 KB */
#define CONFIG_SYS_INIT_SP_OFFSET \
    (CONFIG_SYS_INIT_RAM_SIZE - GENERATED_GBL_DATA_SIZE)   /* - 256 */
#define CONFIG_SYS_INIT_SP_ADDR \
    (CONFIG_SYS_INIT_RAM_ADDR + CONFIG_SYS_INIT_SP_OFFSET)
```

With `GENERATED_GBL_DATA_SIZE = 256` (`(sizeof(struct global_data) + 15) & ~15`) and `GD_SIZE = 248`:

```
CONFIG_SYS_INIT_SP_OFFSET  = 0x00020000 − 0x100 = 0x0001FF00
CONFIG_SYS_INIT_SP_ADDR    = 0x00900000 + 0x1FF00 = 0x0091FF00
```

So `_main` sets the initial SP to `0x0091FF00` — near the top of the i.MX6ULL's 128 KB OCRAM, leaving room for the `gd_t` itself and a few stack frames. After `lowlevel_init` allocates GD on the stack, the real SP sits at:

```
SP = 0x0091FF00 − GD_SIZE (248) → 0x0091FE08
```

Visually:

```
  0x00900000  ┌────────────────────────────┐  <- start of OCRAM
              │     U-Boot pre-reloc       │
              │       (code in DRAM,       │
              │        but stack here)     │
              │                            │
              │            ↓ grows down    │
              │     ...                    │
  0x0091FE08  ├────────────────────────────┤  <- SP after gd_t allocation
              │     gd_t (248 bytes)       │
  0x0091FF00  ├────────────────────────────┤  <- CONFIG_SYS_INIT_SP_ADDR
              │  generated GD slack 256 B  │
  0x0091FFFF  └────────────────────────────┘  <- top of OCRAM (128 KB)
```

This is the layout when `_main` first runs. After relocation in §21.4, SP moves to high DRAM near `relocaddr`.

When `board_init_f` returns... it doesn't. Like SPL, the flow ends in a tail-call. We'll see the actual return path is via relocation: `board_init_f` arranges for the next phase to live elsewhere, then jumps there.

## 21.3  `board_init_f` and the init-function sequence

Open `common/board_f.c`. The function is short; most of it is a *list*:

```c
static const init_fnc_t init_sequence_f[] = {
    setup_mon_len,
    fdtdec_setup,
    initf_malloc,
    log_init,
    initf_bootstage,
    bootstage_start_run,
    setup_spl_handoff,
    initf_console_record,
    arch_cpu_init,           /* CPU-specific re-init */
    mach_cpu_init,
    initf_dm,                /* Driver Model init (early) */
    arch_cpu_init_dm,
    timer_init,
    env_init,                /* env subsystem (early) */
    init_baud_rate,
    serial_init,             /* console UART */
    console_init_f,
    display_options,
    display_text_info,
    print_cpuinfo,
    show_board_info,
    init_func_i2c,
    announce_dram_init,
    dram_init,               /* detect DRAM (already up; just measure) */
    /* ... */
    reserve_uboot,           /* reserve high DRAM for the relocated copy */
    reserve_global_data,
    reserve_fdt,
    reserve_bootstage,
    setup_reloc,             /* compute reloc_off */
    NULL
};

void board_init_f(ulong boot_flags)
{
    if (initcall_run_list(init_sequence_f))
        hang();
}
```

Read that list top to bottom. **It is the entire pre-relocation boot.** Each entry is a small function in the same file (or in `arch/`, `lib/`, etc.). Each is < 50 lines. The architecture is: *one giant array of function pointers, walked in order, halt on the first non-zero return.*

A few entries worth pausing on:

- **`fdtdec_setup`** — locates U-Boot's own embedded device tree (the EVK config builds the DT into the U-Boot binary). U-Boot reads its own configuration from this DT.
- **`initf_dm`** — Driver Model: U-Boot's modern "register devices and their drivers" framework. The early version binds only the devices needed for pre-relocation work.
- **`timer_init`** — bring up the timer used for `udelay`. On i.MX6ULL this is GPT1.
- **`env_init`** — read the environment from its backing store (MMC sector, SPI flash sector, NAND). We see this subsystem in detail in §21.6.
- **`dram_init`** — note this *detects* DRAM size and verifies it; SPL *initialized* DRAM. Two different jobs.
- **`reserve_uboot`** — computes where in high DRAM U-Boot will live after relocation. The size is determined at build time; the offset is computed at runtime from RAM size minus reservations.
- **`setup_reloc`** — sets `gd->reloc_off`, the magic number by which every pointer in U-Boot's code/data must be adjusted after the copy.

After `board_init_f` returns, control falls back into `_main` at the line *after* `bl board_init_f`, which is:

```asm
    /* board_init_f() has set up our DRAM relocation address.  Jump back
       into _main's "after relocation" path with the new SP. */
    ldr r0, [r9, #GD_START_ADDR_SP]       @ load relocated SP
    bic r0, r0, #7
    mov sp, r0
    ldr r9, [r9, #GD_NEW_GD]               @ load new gd_t pointer
    adr lr, here
    ldr r0, [r9, #GD_RELOC_OFF]            @ reloc_off
    add lr, lr, r0
    ldr r0, =__bss_start
    ldr r1, =__bss_end
    b   relocate_code

here:
    /* relocate_code jumps back here AT THE RELOCATED ADDRESS */
    bl  c_runtime_cpu_setup
    bl  board_init_r
```

That's the relocation handshake. Every detail matters.

## 21.4  Relocation — the trick that confuses everyone

This is the most surprising design choice in U-Boot for a newcomer. Let's pin it down.

### Why relocate at all

When U-Boot was originally built for embedded systems running from flash, relocation made sense: "copy yourself from slow XIP flash to fast RAM, fix pointers, run from RAM." On a modern i.MX6ULL booting from SD via SPL, U-Boot is already in RAM. So why relocate?

Two reasons:

1. **Make room for the kernel.** When U-Boot calls `bootz`, it loads the kernel into low DRAM (typically `0x80800000`) and the device tree into another low address. If U-Boot were itself running from `0x80000000`-ish, those load addresses would overwrite U-Boot. Relocating to the *top* of DRAM (just below the stack) keeps U-Boot's code out of the kernel's way.
2. **Position independence at build time.** The linker doesn't know where DRAM ends on every board. By making U-Boot relocatable at runtime, the same binary works on boards with different DRAM sizes.

### How relocation works mechanically

1. U-Boot is built with **position-independent code** (`-fpic` / `-fpie`) and a **relocation table** in `.rel.dyn`. The table is a list of every absolute address in the binary that needs fixing.
2. `relocate_code` (in `arch/arm/lib/relocate.S`) does three things:
   - **memcpy** the entire U-Boot binary from its current address to the destination.
   - **Walk the relocation table** and, for each entry, adjust the value at that address by `reloc_off`.
   - **Branch to the relocated code**, specifically to the saved `lr` (which is `here:` + `reloc_off`).

```asm
ENTRY(relocate_code)
    /*
     * r0 = destination address
     * r1 = source address (where U-Boot currently is)
     * r2 = length of binary
     */
copy_loop:
    ldmia   r1!, {r10-r11}
    stmia   r0!, {r10-r11}
    cmp     r1, r6
    blo     copy_loop

    /* now fixup relocations */
fixloop:
    ldr     r1, [r2]               @ relocation entry: an offset
    add     r0, r1, r4             @ add reloc_off
    ...
    cmp     r2, r3
    blo     fixloop

    bx      lr                     @ jump to relocated code via patched lr
```

The post-copy `bx lr` is the **single most important instruction** in this entire chapter. Before it, the CPU is executing the original (pre-relocation) U-Boot. After it, the CPU is executing the relocated copy. The transition is one machine instruction.

After this, the original U-Boot in low DRAM is reusable memory — the kernel can land there.

### What you observe

In a U-Boot session:

```
=> bdinfo
relocaddr   = 0x9ff37000
reloc off   = 0x1f737000
```

So U-Boot was built linked for an address of approximately `0x80800000` (the "load address") and is now running at `0x9ff37000` (high DRAM). The difference is the `reloc_off`.

Try:

```
=> md $relocaddr 4
9ff37000: ea0001e1 e59ff014 e59ff014 e59ff014    ................
```

Disassembling those bytes... they're branch instructions, the start of the U-Boot text segment. Now compare:

```
=> md 0x80800000 4
80800000: <something else or zeros>
```

The original load location is no longer U-Boot — it's been overwritten by subsequent operation (likely a temporarily-staged buffer for environment, etc.).

## 21.5  The command system

When you type `md 0x80000000 4` at the `=>` prompt, the call chain is:

```
main_loop                                  (common/main.c)
   └─► autoboot_command  (run bootcmd if no key pressed)
   └─► cli_loop                            (common/cli.c)
          └─► cli_simple_loop_process_line  or  cli_hush
                 └─► cmd_process            (common/command.c)
                        └─► find_cmd(name)
                        └─► cmdtp->cmd(cmdtp, flag, argc, argv)
```

`find_cmd` looks up the command name in the **command table**, an array of `cmd_tbl_t` structures that the linker assembles into a single contiguous section at link time. Each `.c` file in `cmd/` ends with a `U_BOOT_CMD()` macro that pushes a `cmd_tbl_t` entry into a specific linker section.

Example — `cmd/mem.c`:

```c
U_BOOT_CMD(
    md,     3,     1,     do_mem_md,
    "memory display",
    "[.b, .w, .l, .q] address [# of objects]"
);
```

The macro expands to:

```c
static const cmd_tbl_t _u_boot_cmd_md __attribute__((section(".u_boot_list_2_cmd_2_md")))
    = { "md", 3, 1, do_mem_md, "memory display", "...", NULL };
```

The linker collects all `.u_boot_list_2_cmd_*` sections into a contiguous range bounded by `__u_boot_list_2_cmd_start` and `__u_boot_list_2_cmd_end`. `find_cmd` walks this range.

**Why this matters for you:** to add a custom command, you write one `do_foo()` function and one `U_BOOT_CMD(...)` macro in your `cmd/` file. No central registration, no Makefile edit beyond adding your `.c` file. The linker takes care of registration.

### Adding a `hello` command

`cmd/hello.c`:

```c
#include <command.h>

static int do_hello(struct cmd_tbl *cmdtp, int flag, int argc, char *const argv[])
{
    printf("hello from a custom U-Boot command\n");
    if (argc > 1) printf("first arg: %s\n", argv[1]);
    return CMD_RET_SUCCESS;
}

U_BOOT_CMD(
    hello, 2, 1, do_hello,
    "print a greeting",
    "[name]\n"
    "    - print 'hello' and an optional argument"
);
```

Add to `cmd/Makefile`:

```make
obj-y += hello.o
```

Rebuild, flash, boot:

```
=> hello world
hello from a custom U-Boot command
first arg: world
```

Eight lines of code, one Makefile line. You have just shipped a U-Boot patch — a tiny one, but a real one. This is the discipline pattern for everything in `cmd/`.

## 21.6  The environment

The **environment** is U-Boot's persistent key-value store. It is how `bootcmd`, `bootargs`, MAC addresses, IP configs, and your own custom variables survive across power cycles.

### What it is and where it lives

The environment is a flat block of `KEY=VALUE\0KEY=VALUE\0...\0\0` bytes, capped at `CONFIG_ENV_SIZE` (typical: 8 KB). It is stored on the **boot medium** — for our SD-card workflow, in a fixed-offset sector of the SD card (`CONFIG_ENV_OFFSET`, often 0x100000 = 1 MiB). For NAND boots it's in a dedicated partition. For SPI-NOR it's in a sector.

The fixed-offset storage means the env survives reflashing of U-Boot itself, as long as the env sector isn't overwritten. It also means the env is *outside* any filesystem — direct sector access, no FAT, no ext4.

### Reading and writing

```
=> printenv                  # print everything
=> printenv bootcmd          # print one variable
=> setenv ipaddr 192.168.7.2 # set
=> setenv ipaddr             # unset (omit the value)
=> saveenv                   # persist to the boot medium
```

`setenv` modifies the in-RAM copy. `saveenv` writes it to the medium. Forget `saveenv` and your changes vanish on reboot.

### From U-Boot scripts and from C code

The environment can be read inside U-Boot's "shell scripts":

```
=> setenv myloadcmd 'tftp 0x82000000 zImage; tftp 0x83000000 imx6ull.dtb; bootz 0x82000000 - 0x83000000'
=> run myloadcmd
```

`run` evaluates the variable as a sequence of commands. The string can contain `${other_var}` references for substitution.

From C inside U-Boot:

```c
const char *ip = env_get("ipaddr");
env_set("autoload", "no");
ulong addr = env_get_hex("loadaddr", 0x82000000);
```

### From Linux user-space

Once Linux is booted, `fw_setenv` and `fw_printenv` (in the `u-boot-tools` package) can read and modify U-Boot's environment from a running Linux system. The configuration file `/etc/fw_env.config` tells these tools which sector to access. This is how production OTA systems (Chapter 63) flip "boot-slot" variables from inside Linux.

## 21.7  The driver model (DM)

U-Boot's modern driver framework. Conceptually identical to Linux's `struct device` + `struct driver`, but much smaller. Three core concepts:

- **`udevice`** — an instance: "the UART at address 0x02020000 on bus AIPS-1."
- **`driver`** — the code that knows how to operate one *kind* of device: "any i.MX UART."
- **`uclass`** — the *category* of devices, with a uniform API: "any UART, regardless of vendor."

A driver attaches to a uclass. When a `udevice` of the right kind appears (typically from a DT node), DM matches the device to a driver in its uclass and calls the driver's `probe()`.

### What you write to add a DM driver

```c
static int my_uart_probe(struct udevice *dev)
{
    /* read DT, ioremap registers, configure clocks, set initial baud */
    return 0;
}

static const struct dm_serial_ops my_uart_ops = {
    .putc = my_uart_putc,
    .pending = my_uart_pending,
    .getc = my_uart_getc,
    .setbrg = my_uart_setbrg,
};

static const struct udevice_id my_uart_ids[] = {
    { .compatible = "fsl,my-uart" },
    { }
};

U_BOOT_DRIVER(my_uart) = {
    .name = "my_uart",
    .id = UCLASS_SERIAL,
    .of_match = my_uart_ids,
    .probe = my_uart_probe,
    .ops = &my_uart_ops,
};
```

If a node with `compatible = "fsl,my-uart"` exists in the DT, DM creates a `udevice` for it and calls `my_uart_probe`. The `dm_serial_ops` callbacks are then routed by the `serial` uclass to the right operations.

You write a Linux driver later in Chapter 39 and the structure will look almost identical. That is not a coincidence — DM was deliberately modeled on the Linux driver model.

## 21.8  Reading a real boot, end to end

With all this in your head, re-read the Chapter 19 boot log. Each line maps to a function call sequence we've now named:

```
U-Boot SPL 2025.01 ...           ← SPL's printf via preloader_console_init
Trying to boot from MMC1         ← spl_load_image() probing MMC1

U-Boot 2025.01 ...               ← full U-Boot's print_cpuinfo + display_options
CPU:   i.MX6ULL ...              ← print_cpuinfo
Reset cause: POR                 ← print_reset_cause
Model: ...                       ← show_board_info (reads /model from DT)
DRAM:  512 MiB                   ← announce_dram_init
PMIC:  PFUZE3000 ...             ← board's late_init reading I²C
MMC:   FSL_SDHC: 0, FSL_SDHC: 1  ← mmc subsystem init
Loading Environment from MMC...  ← env_init's first call to env_load
*** Warning - bad CRC ...        ← env CRC mismatch; fallback to defaults

In/Out/Err: serial               ← console_init_r
Switch to partitions #0, OK      ← MMC partition probe
mmc0 is current device           ← mmc init complete
Net:   FEC0                      ← FEC PHY probe via DM
Hit any key to stop autoboot:    ← run_main_loop's autoboot countdown
=>                               ← cli_loop's prompt
```

Now you can also predict, with high confidence, where to look in the source if any of those lines reports an error.

## 21.9  Lab

1. **Add a `hello` command.** Follow §21.5. Push it to your custom board (or to the EVK).
2. **Trace one init function.** Pick `init_baud_rate` from `init_sequence_f`. Find it in source. Read it. Annotate.
3. **Find and read `_main`** in `arch/arm/lib/crt0.S`. Identify the lines that set the early stack, the lines that call `board_init_f`, and the lines that resume execution post-relocation.
4. **Inspect the relocation table.** `arm-linux-gnueabihf-readelf -r u-boot | head -30` to see relocations. Each entry is an absolute address inside U-Boot's image that `relocate_code` fixes up.
5. **Make and save an env change.** `setenv myname yourname; saveenv; reset`. After reboot, `printenv myname` should still print your name.
6. **Custom autoboot script.**
   ```
   => setenv bootcmd 'echo hello from custom bootcmd; sleep 2; reset'
   => saveenv
   => reset
   ```
   The board now reboots itself every 2 seconds. Disable by re-flashing the SD with original env, or interrupt autoboot and `env default -a; saveenv`.
7. **Find the DM tree.**
   ```
   => dm tree
   ```
   Read the output. Match every entry to a DT node in `imx6ull-14x14-evk.dts`.

Commit to `code/ch21-uboot-internals/`.

## 21.10  Pitfalls

- **Forgetting `saveenv`.** Most "my env change didn't stick" bug reports are this.
- **Editing U-Boot, expecting hot reload.** U-Boot is not Linux. To see a code change you rebuild, reflash, reboot. There is no `modprobe`-equivalent.
- **Function pointer addresses in C code.** Because of relocation, taking `&foo` may surprise you — it returns the relocated address, not the linked address. This matters when you write the address to MMIO or share it with an external system.
- **Custom commands not appearing.** Check that you (a) added the `.o` to `cmd/Makefile`'s `obj-y`, (b) did not typo the `U_BOOT_CMD` macro, (c) rebuilt.
- **Env corruption.** `env default -a` resets to the compiled-in defaults. Useful when your env is somehow scrambled. `eraseenv` (if available) wipes the medium.
- **Build with `-Werror` and a stale tree.** New kernel/gcc combinations sometimes break old U-Boot trees. Use a release tag matched to the gcc on your host.
- **Two `U_BOOT_CMD` macros with the same name.** Last-defined wins, silently. Pick distinctive names for your custom commands.

## 21.11  Going deeper

- **U-Boot docs `doc/develop/driver-model/`** — the official DM tutorial. Read end-to-end before writing your first DM driver.
- **U-Boot docs `doc/usage/cmd/`** — per-command pages, useful when you forget syntax.
- **`common/main.c`, `common/cli.c`, `common/command.c`** — the entire UI layer of U-Boot. Three files, ~1000 lines combined.
- **`common/board_f.c` and `common/board_r.c`** — the two init sequences. Read these once; the rest of U-Boot makes vastly more sense.
- **Linaro's "U-Boot under the hood"** training material — covers relocation in particular more visually than this chapter does.
- **DENX U-Boot training** — paid course; also available as recordings; very thorough.

> Next chapter: **Chapter 22 — Porting U-Boot to a custom board.** With internals understood, we fork the EVK config into our own board directory and modify what differs: DDR timings, pinmux, MAC address, defaults.
