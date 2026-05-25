---
chapter: 6
title: The toolchain
part: I — Foundations
estimated_pages: 24
status: draft
---

# Chapter 6 — The toolchain

> **What:** the set of programs that turn your C and assembly source into a binary your i.MX6ULL will execute.
> **Why:** every later chapter ends with "now build it." If "build" is a black box, every failure will be too.
> **Focus:** **(a)** that `gcc` is a *driver* over half a dozen smaller tools; **(b)** that **ELF** is the universal container, and the linker decides where every byte ends up; **(c)** that the **ABI** is a contract between every function call across your program.

## 6.1  `gcc` is not one program

When you type:

```sh
$ arm-linux-gnueabihf-gcc -O2 -o hello hello.c
```

…six programs run in sequence. `gcc` is a **driver**: it parses the command line, decides which sub-tools to invoke, builds their argument lists, and chains their I/O.

The six sub-stages (the driver may merge some into one process for speed):

1. **`cpp` — preprocessor.** Resolves `#include`, expands macros, strips comments. Output: pure C, no directives. Try `-E` to stop here.
2. **`cc1` — the C compiler proper.** Parses C, builds an internal IR (RTL/GIMPLE), optimizes, lowers to target assembly. Output: a `.s` file. Try `-S` to stop here.
3. **`as` (from binutils) — assembler.** Turns `.s` into a relocatable `.o` (ELF object file). Try `-c` to stop here.
4. **`collect2`** — a wrapper around the linker that also handles C++ constructors. You almost never invoke it directly.
5. **`ld` (from binutils) — linker.** Combines `.o` files and libraries, resolves symbol references, applies the linker script's address layout, and writes the final ELF executable.
6. *(For dynamically-linked output)* — the resulting ELF references the dynamic loader, which runs at process start time on the target. Not part of host build, but in the picture.

You can see the chain by adding `-v` to any compile:

```sh
$ arm-linux-gnueabihf-gcc -v -o hello hello.c 2>&1 | head -20
Using built-in specs.
COLLECT_GCC=arm-linux-gnueabihf-gcc
COLLECT_LTO_WRAPPER=/usr/libexec/gcc-cross/arm-linux-gnueabihf/11/lto-wrapper
Target: arm-linux-gnueabihf
...
```

For embedded work, the steps that bite are #1 (include path mismatches), #5 (linker script and wrong sysroot), and the boundary between #3 and #5 (relocation types).

## 6.2  The binutils inventory

`binutils` is a collection of tools that operate on object files and binaries. Cross-prefixed versions exist for every target. The ones you will use:

| Tool | What it does | When you reach for it |
|------|-------------|----------------------|
| `as` | Assemble `.s` → `.o` | Indirectly via `gcc`; rarely by hand. |
| `ld` | Link `.o` + libraries → ELF | Bare-metal builds (`-T linker.ld`). |
| `objcopy` | Convert between formats; extract sections | "I have an ELF, give me a raw binary." |
| `objdump` | Disassemble, dump headers/sections | "What does this code actually look like?" |
| `nm` | List symbols in an object | "Where is `foo` defined and is it exported?" |
| `readelf` | Dump ELF metadata in detail | "What sections, segments, and dynamic info does this have?" |
| `strip` | Remove symbols/debug info | Producing the shipped binary. |
| `ar` | Build/dissect `.a` archives (static libraries) | When making your own libs. |
| `addr2line` | Map address → file:line | Decoding crash addresses, oopses. |
| `size` | Print section sizes | Quick sanity check on memory budget. |

Two examples to internalize.

### `objdump -d` on a bare-metal LED

```sh
$ arm-none-eabi-objdump -d hello.elf | head -25

hello.elf:     file format elf32-littlearm

Disassembly of section .text:

00900000 <_start>:
  900000:   ea000001    b   90000c <main>

00900004 <_irq_handler>:
  900004:   eafffffe    b   900004 <_irq_handler>

0090000c <main>:
  90000c:   e3a00d22    mov r0, #0x2200
  900010:   e3400000    movt    r0, #0
  900014:   e5803000    str r3, [r0]
  900018:   eafffffe    b   900018 <main+0xc>
```

You can read your own machine code. This is non-negotiable for embedded work.

### `readelf -l` to see segments

```sh
$ arm-linux-gnueabihf-readelf -l hello
Elf file type is DYN (Shared object file)
Entry point 0x4c0
There are 9 program headers, starting at offset 52

Program Headers:
  Type           Offset   VirtAddr   PhysAddr   FileSiz MemSiz   Flg Align
  PHDR           0x000034 0x00000034 0x00000034 0x00120 0x00120  R   0x4
  INTERP         0x000154 0x00000154 0x00000154 0x00019 0x00019  R   0x1
      [Requesting program interpreter: /lib/ld-linux-armhf.so.3]
  LOAD           0x000000 0x00000000 0x00000000 0x004f4 0x004f4  R   0x10000
  LOAD           0x000ed4 0x00010ed4 0x00010ed4 0x0011c 0x0011c  RW  0x10000
  ...
```

Notice: the segment marked `INTERP` says the dynamic linker for this binary is `/lib/ld-linux-armhf.so.3`. *That* is what runs first when the kernel `exec`'s this file; only after it finishes loading shared libraries does control reach `main`.

For bare-metal output we will *not* have an INTERP segment. The ELF will be statically resolved and the entry point we set is what runs.

## 6.3  Section, segment, VMA, LMA

A common source of confusion: what is the difference between a section and a segment?

- **Sections** are the linker's view of an ELF. `.text`, `.rodata`, `.data`, `.bss`, `.init_array`, `.debug_*`. The linker script names these and decides where each ends up.
- **Segments** are the loader's view. A segment is a contiguous range of memory the runtime is supposed to load with given permissions. Segments are described by program headers. Multiple sections can map into one segment (e.g., `.text` + `.rodata` both go into a single R-X segment).

**VMA (Virtual Memory Address)** is the address the section's content *expects to live at when the program runs*.

**LMA (Load Memory Address)** is the address from which the loader should *initially read* the section's content.

Most of the time VMA = LMA. The interesting case is **`.data`** in a bare-metal Flash + RAM system:

- VMA of `.data` = somewhere in RAM (where the variables live at runtime).
- LMA of `.data` = somewhere in Flash (where the *initial values* are stored persistently).
- Your startup code copies LMA → VMA before `main()`.

In the Cortex-M world this distinction is everyday. In Linux user-space it disappears because the loader handles it. In bare-metal on the i.MX6ULL it returns.

## 6.4  Linker scripts

A linker script is a small DSL that tells `ld`:

1. What memory regions exist and their attributes.
2. Which sections go into which regions.
3. Where the entry point is.
4. What symbols to export (`_etext`, `_sdata`, `_edata`, `_sbss`, `_ebss`).

The simplest useful linker script for our Chapter 9 bare-metal LED:

```ld
ENTRY(_start)

MEMORY
{
    OCRAM (rwx) : ORIGIN = 0x00907000, LENGTH = 0x00019000  /* ~100 KB */
}

SECTIONS
{
    .text   : { *(.vectors) *(.text*) *(.rodata*) } > OCRAM
    .data   : { *(.data*) } > OCRAM
    .bss    : { _sbss = .; *(.bss*) *(COMMON) _ebss = .; } > OCRAM

    _stack_top = ORIGIN(OCRAM) + LENGTH(OCRAM);
}
```

Five things to notice:

1. `ENTRY(_start)` tells the linker which symbol is the entry. The Boot ROM does not consult this — it jumps to a fixed offset. But debuggers and tooling care.
2. `MEMORY` declares one region called `OCRAM` of ~100 KB. Permissions (`rwx`) are advisory for now.
3. `SECTIONS` orders the input sections into output sections, attached `> OCRAM` to lay each at the next available address inside OCRAM.
4. `_sbss = .; ... _ebss = .;` exports the bounds of `.bss` so our startup code can clear it.
5. `_stack_top` is computed at link time as "one past the end of OCRAM" — our startup code loads SP from this.

We will revise this script over the next chapters as we move to DDR. The format does not change; only the regions do.

## 6.5  The ABI: what makes function calls work

When `foo()` calls `bar()`, both sides must agree on:

- Which register contains the first argument? The second? Where do return values live?
- Which registers must `bar()` preserve, and which can it freely clobber?
- How is the stack aligned?
- Where do floating-point arguments go — in integer registers, or in FPU registers?
- How are structs > 8 bytes returned?

The **EABI** (Embedded ABI) for ARM specifies all of this. ARMv7-A Linux uses the **AAPCS** (ARM Architecture Procedure Call Standard) plus the EABI's run-time conventions. The relevant variant for us is **AAPCS-VFP**, also called "hard-float," in which floating-point parameters travel in `s0`–`s15` / `d0`–`d7` rather than integer registers.

The core rules (simplified):

| Register | AAPCS role |
|----------|-----------|
| r0–r3 | First four integer arguments / return value (`r0`, optionally `r0,r1` for 64-bit). Caller-saved. |
| r4–r11 | Callee-saved (must be preserved). r9 is "platform register" — see §6.6. |
| r12 (ip) | Intra-procedure-call scratch. Caller-saved. |
| r13 (sp) | Stack pointer. 8-byte aligned at function boundary. |
| r14 (lr) | Link register (return address). |
| r15 (pc) | Program counter. |
| s0–s15 / d0–d7 | First eight FP arguments / FP return. Caller-saved. |
| s16–s31 / d8–d15 | Callee-saved FP. |

Why this matters: when you write a function in assembly and call it from C (or vice versa), you **must** obey AAPCS or memory corruption follows. The toolchain assumes it; you must too.

### Hard-float vs soft-float

Three flavors of FP ABI exist:

- **soft-float** (`-mfloat-abi=soft`) — FP ops are emulated in libgcc; FP arguments go in integer registers. Slow but universally compatible.
- **softfp** (`-mfloat-abi=softfp`) — FP ops use the FPU, but FP arguments still go in integer registers. Compromise — used when linking soft-float libraries with code that has an FPU.
- **hard-float** (`-mfloat-abi=hard`) — FP ops use the FPU; FP arguments use FP registers. Fastest.

The triplet suffix tells you which: `arm-linux-gnueabi` (soft), `arm-linux-gnueabihf` (hard). **You cannot link a soft-float `.o` with a hard-float `.o`**; the linker refuses.

Linux on i.MX6ULL is universally hard-float in 2026. So is everything we build.

## 6.6  The C library, or its absence

For bare-metal code in Part II, we want **no libc at all**. We will write our own `memcpy`, our own `printf`. The reason is the same reason we are doing this book: dependencies hide assumptions.

For Linux user-space code, we use a libc. Three options:

| libc | Size of typical static `hello world` | Notes |
|------|--------------------------------------|-------|
| glibc | ~700 KB | The default on most distros. Largest, most compatible. |
| musl | ~30 KB | Tiny, MIT-licensed, fast cold-start. Increasingly default for embedded. |
| uClibc-ng | ~50 KB | Maintained fork of uClibc. Still used in OpenWRT/Buildroot. |

We will mostly use glibc (because the Ubuntu toolchain ships it) and switch to musl for one comparison build in Chapter 34.

### What libc actually provides

A libc bundles:

- **Wrappers around syscalls** (`open`, `read`, `write`, `mmap`, ...) so you can call them as C functions.
- **Memory allocator** (`malloc`, `free`, internally calling `brk`/`mmap`).
- **Standard I/O** (`fopen`, `printf`) — buffered layers atop the syscall wrappers.
- **Math** (`sin`, `sqrt`, ...) — in `libm.so`.
- **POSIX threads** (`pthread_*`) — sometimes a separate `libpthread.so`, sometimes folded in.
- **Locale, time, network, etc.**

When we write bare-metal code, *none of this is available*. There is no `malloc`. There is no `printf` (we write one). There is no `errno` (we set our own). This is liberating once you accept it.

## 6.7  Make, in working depth

`make` is older than most engineers reading this, but for the bare-metal projects in Part II — and for every kernel / U-Boot / Buildroot build later — it is the tool of record. This section is longer than it might first seem because every later chapter references it; once you have it, you do not need it again.

### 6.7.1  Rule shape

```make
target ...: prerequisite ...
<TAB>command
<TAB>command
```

`make` builds the *target* by running the *command(s)* when (a) the target does not exist, or (b) any prerequisite is newer than the target. Commands **must** be indented with a literal `TAB` — spaces do not work; the first time you cut-and-paste a rule, this bites everyone.

### 6.7.2  Variables: four flavors of assignment

```make
CC     = arm-none-eabi-gcc         # 1) recursive ("deferred")
CC    := arm-none-eabi-gcc         # 2) simple ("immediate")
CFLAGS ?= -O2                       # 3) only if not already set
OBJS  += extra.o                   # 4) append
```

The pair people misunderstand most is `=` vs `:=`:

```make
name = world
greet = hello $(name)
name = there
$(info $(greet))   # prints "hello there"   ← deferred expansion
```

```make
name := world
greet := hello $(name)
name := there
$(info $(greet))   # prints "hello world"   ← immediate expansion
```

Use `:=` everywhere by default. The `=` form is occasionally necessary (recursive expansion of generated variables) but mostly a footgun.

### 6.7.3  Pattern rules and automatic variables

A pattern rule with `%` matches every file fitting the pattern:

```make
%.o: %.c
	$(CC) $(CFLAGS) -c -o $@ $<
```

Inside the recipe, **automatic variables** carry the per-instance pieces:

| Var | Meaning |
|-----|---------|
| `$@` | The target being built |
| `$<` | The first prerequisite |
| `$^` | All prerequisites (de-duplicated, space-separated) |
| `$+` | All prerequisites (with duplicates) |
| `$?` | Prerequisites newer than the target |
| `$*` | The stem matched by `%` |

A pair of pattern rules and one main rule, plus a `clean` phony, is 90% of every Makefile you will write in this book.

### 6.7.4  Phony targets

```make
.PHONY: all clean install
```

Tells `make` that `all` / `clean` / `install` are **not** filenames. Without `.PHONY`, if you ever happen to create a file literally named `clean`, `make clean` would consider that file "up to date" and skip the recipe. With `.PHONY`, the recipe always runs.

### 6.7.5  Useful functions

`make` has a small set of built-in functions, called as `$(name args,...)`:

| Function | What it does | Example |
|----------|--------------|---------|
| `$(wildcard PATTERN)` | List files matching a glob (no quoting) | `$(wildcard *.c)` → `a.c b.c` |
| `$(patsubst PAT,REPL,LIST)` | Pattern substitution | `$(patsubst %.c,%.o,a.c b.c)` → `a.o b.o` |
| `$(subst FROM,TO,STR)` | Plain string substitution | `$(subst ., _,a.b.c)` → `a_b_c` |
| `$(dir NAMES)` | Directory part | `$(dir src/a.c)` → `src/` |
| `$(notdir NAMES)` | Filename part | `$(notdir src/a.c)` → `a.c` |
| `$(basename NAMES)` | Drop the extension | `$(basename src/a.c)` → `src/a` |
| `$(addsuffix S,LIST)` / `$(addprefix P,LIST)` | Append / prepend | `$(addsuffix .o,a b)` → `a.o b.o` |
| `$(filter PAT,LIST)` / `$(filter-out PAT,LIST)` | Keep / remove matching | `$(filter %.c,a.c b.h)` → `a.c` |
| `$(sort LIST)` | Sort + de-duplicate | `$(sort c a b a)` → `a b c` |
| `$(shell CMD)` | Run a shell command, capture stdout | `$(shell uname -m)` → `x86_64` |

A common idiom — collect every `.c` in the tree:

```make
SRCS := $(wildcard bsp/*/*.c) $(wildcard *.c)
OBJS := $(patsubst %.c,%.o,$(SRCS))
```

### 6.7.6  Conditionals

```make
ifeq ($(ARCH),arm)
  CFLAGS += -mcpu=cortex-a7
else ifeq ($(ARCH),aarch64)
  CFLAGS += -mcpu=cortex-a53
else
  $(error Unsupported ARCH=$(ARCH))
endif

ifdef DEBUG
  CFLAGS += -O0 -g3
else
  CFLAGS += -O2
endif
```

Four conditional forms: `ifeq`, `ifneq`, `ifdef`, `ifndef`. They work both at the *top level* (selecting variable values) and inside *recipes* — though for recipe-level branching, shell `if` is usually cleaner.

### 6.7.7  Parallelism

```sh
$ make -j$(nproc)            # use all available cores
$ make -j8                    # 8 jobs in parallel
```

For our bare-metal builds (~10 files), `-j` makes no measurable difference. For the kernel (~30 000 files) it cuts build time by ~7× on an 8-core host. Always use it for kernel work; harmless for everything else.

### 6.7.8  A complete Makefile for the Chapter 9 LED

```make
CROSS  := arm-none-eabi-
CC     := $(CROSS)gcc
LD     := $(CROSS)ld
OC     := $(CROSS)objcopy

CFLAGS := -mcpu=cortex-a7 -mfpu=neon-vfpv4 -mfloat-abi=hard \
          -ffreestanding -fno-builtin -nostdlib -O2 -g -Wall

SRCS   := startup.S main.c
OBJS   := startup.o main.o

all: led.bin

%.o: %.S
	$(CC) $(CFLAGS) -c -o $@ $<

%.o: %.c
	$(CC) $(CFLAGS) -c -o $@ $<

led.elf: $(OBJS) link.ld
	$(LD) -T link.ld -o $@ $(OBJS)

led.bin: led.elf
	$(OC) -O binary $< $@

clean:
	rm -f *.o *.elf *.bin

.PHONY: all clean
```

Every flag in `CFLAGS` is load-bearing:

- `-mcpu=cortex-a7` — generate code that uses Cortex-A7 features.
- `-mfpu=neon-vfpv4 -mfloat-abi=hard` — match what the silicon supports and the ABI we picked.
- `-ffreestanding` — "I do not have a hosted C environment." Disables the assumption that `main` is the standard entry, etc.
- `-fno-builtin` — disables compiler's optimization of calls like `printf` into special builtins.
- `-nostdlib` — do not implicitly link `crt0`, libc, libgcc. (We will manually add libgcc later if we need its compiler-rt routines.)
- `-O2 -g` — optimize but keep debug info.
- `-Wall` — turn on the warnings everyone should be using.

## 6.8  Static vs dynamic linking (for Linux user-space)

Two ways to combine your code with libraries:

- **Static.** Library code is copied into your binary at link time. The binary is self-contained; no `libfoo.so` is needed at runtime. Bigger file; faster startup.
- **Dynamic.** Library code lives in `.so` files on disk; your binary references them by name; the dynamic loader (`/lib/ld-linux-armhf.so.3`) resolves them at process start.

Default on a Linux distro: dynamic. Default on a tight embedded system with a known rootfs: often static (saves space if you only have a few binaries; saves disk IO at startup).

To force static:

```sh
$ arm-linux-gnueabihf-gcc -static -o hello hello.c
$ file hello
hello: ELF 32-bit LSB executable, ARM, EABI5 version 1 (SYSV),
       statically linked, BuildID[sha1]=..., with debug_info, not stripped
```

Compare sizes:

```sh
$ arm-linux-gnueabihf-gcc -o hello-dyn  hello.c          ; ls -l hello-dyn
$ arm-linux-gnueabihf-gcc -static -o hello-stc hello.c   ; ls -l hello-stc
```

You will see something like 8 KB dynamic vs 600 KB static (glibc). With musl, static is ~30 KB.

## 6.9  ELF, in just enough depth

An ELF file has:

```
┌──────────────────────────────┐
│ ELF Header                   │  ← architecture, type (REL/EXEC/DYN), entry point
├──────────────────────────────┤
│ Program Header Table         │  ← segments (loader's view)
├──────────────────────────────┤
│ .text                        │
│ .rodata                      │
│ .data                        │
│ .bss (no actual bytes)       │
│ .symtab, .strtab             │
│ .debug_*  (DWARF)            │
│ ...                          │
├──────────────────────────────┤
│ Section Header Table         │  ← sections (linker/debugger's view)
└──────────────────────────────┘
```

A few key facts:

- **Type `REL`** (relocatable, `.o`) — produced by the assembler, fed to the linker.
- **Type `EXEC`** (executable) — produced by linking statically.
- **Type `DYN`** (shared object / PIE executable) — relocatable at load time, used for both `.so` libraries and modern position-independent executables.
- **`.bss` occupies no file bytes.** It only declares "give me N bytes of zero at runtime." The startup code (or the kernel) zeroes it.
- **DWARF** is the debug-info format used in `.debug_*` sections. `gdb`, `objdump -S`, and `addr2line` read it.

When `gdb` says "no debug info, no symbols", it means the binary was stripped (`strip` removed the symbol and DWARF sections).

## 6.10  Lab

Two builds; both reproducible from a clean checkout.

### Lab A — Host hello world, inspected

```sh
$ cat > hello.c <<'EOF'
#include <stdio.h>
int main(void) { puts("hello"); return 0; }
EOF
$ gcc -g -O2 -o hello-host hello.c
$ arm-linux-gnueabihf-gcc -g -O2 -o hello-arm hello.c
$ file hello-host hello-arm
$ readelf -a hello-arm | head -40
$ arm-linux-gnueabihf-objdump -d hello-arm | grep -A 5 '<main>:'
```

Read the disassembly. Find the `bl puts` instruction (or its inline equivalent). Find where `r0` is loaded with the address of the string `"hello"`.

### Lab B — Bare-metal LED skeleton (build only; we'll add the LED code in Ch 9)

Create `~/imx6ull/src/ch06-skeleton/` with:

- `startup.S` — a minimal startup that sets SP and branches to `main`.
- `main.c` — `int main(void){ while(1); return 0; }`.
- `link.ld` — the minimal script from §6.4.
- `Makefile` — from §6.7.

Run `make`. You should get `led.elf` and `led.bin`.

Then:

```sh
$ arm-none-eabi-size led.elf
$ arm-none-eabi-readelf -S led.elf
$ arm-none-eabi-objdump -d led.elf
$ arm-none-eabi-nm led.elf | sort
```

In your journal, answer:

1. How big is `.text` in bytes?
2. How big is `.bss`? Why does it consume no space in `led.bin`?
3. What is the address of `_start`?
4. What is the address `nm` reports for `_stack_top`? Does it match `ORIGIN(OCRAM) + LENGTH(OCRAM)`?

The companion repo has reference answers in `code/ch06-skeleton/ANSWERS.md`.

## 6.11  Pitfalls

- **Mixing `arm-none-eabi-` and `arm-linux-gnueabihf-` outputs.** They cannot be linked. The compiler will not warn; the linker will.
- **`-nostdlib` silently dropping libgcc.** If your code uses 64-bit integer division on a target without HW divide, `gcc` emits a call to `__aeabi_uldivmod` — provided by `libgcc`. With `-nostdlib`, you must explicitly add `-lgcc` after your objects.
- **Linker script orders matter.** `*(.text*)` after `*(.text.startup)` makes the startup come first. Get this wrong and the wrong code runs first. We will be deliberate about this in Ch 9.
- **`.bss` zeroing.** If your startup forgets to zero `.bss`, every uninitialized global is whatever was in memory at boot — which on i.MX6ULL OCRAM is often a useful-looking pattern, leading to bugs that "work fine" except when ROM cleans differently next boot.
- **Wrong `-march`/`-mcpu`.** `arm-linux-gnueabihf-gcc` defaults to `armv7-a` but the exact flags vary by distribution. Always specify `-mcpu=cortex-a7` explicitly for Cortex-A7 code; the compiler then schedules instructions for that pipeline.
- **`strip` on the binary you wanted to debug.** Keep an unstripped copy. The companion repo's Makefiles do this by convention (`$(NAME).elf` is unstripped, `$(NAME).stripped.elf` is the deliverable).

## 6.12  Going deeper

- *Linkers and Loaders* by John Levine. The canonical book on what `ld` actually does.
- *The ELF Specification* (latest is the System V ABI ed. 4.1; the AAPCS additions are in ARM IHI 0042).
- The GCC manual — at least the section on language-independent options.
- *Procedure Call Standard for the Arm Architecture* (AAPCS32) — ARM IHI 0042.
- `man elf`, `man 5 elf`, `man 1 ld`, `man 1 ld.so`.
- LWN: "How programs get run" (the kernel `exec` path; relevant when you write a `binfmt`).

> Next chapter: **Chapter 7 — The Boot ROM, IVT, DCD, and BootData.** With the toolchain understood, we can now build images that survive the Boot ROM's scrutiny.
