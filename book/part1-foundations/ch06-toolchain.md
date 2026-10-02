# Chapter 6: The toolchain

> **What:** the set of programs that turn your C and assembly source into a binary your i.MX6ULL will execute.
>
> **Why:** every later chapter ends with "now build it." If you do not know what the build tools are doing, build failures become guesswork.
>
> **Focus:** GCC drives compilation/linking; ELF carries objects and debugging information; the ABI defines binary calling conventions. The ROM ultimately loads a wrapped raw image, not our debugging ELF.

> **ELF:** Executable and Linkable Format, the standard Linux object and executable file format.

> **ABI:** Application Binary Interface: the calling convention, register use, binary format, and library contract that let separately built code run together.

## 6.1  `gcc` is not one program

Source Chapter 3's environment, create a directory, and open `hello.c`:

```sh
$ . ~/imx6ull/scripts/env.sh
$ mkdir -p ~/imx6ull/src/ch06-hello
$ cd ~/imx6ull/src/ch06-hello
$ nano hello.c
```

Save this complete source:

```c
#include <stdio.h>
int main(void) { puts("hello"); return 0; }
```

Now build a Linux-target executable (do not run it directly on the x86_64 host):

```sh
$ arm-none-linux-gnueabihf-gcc -O2 -o hello hello.c
```

The `gcc` command coordinates several build stages. GCC is a **driver**: it parses the command line, selects the required tools, and passes each stage's output to the next stage.

The main build stages are:

1. **`cpp`, preprocessor.** Resolves `#include`, expands macros, strips comments. Output: pure C, no directives. Try `-E` to stop here.
2. **`cc1`, the C compiler proper.** Parses C, builds an internal IR (RTL/GIMPLE), optimizes, lowers to target assembly. Output: a `.s` file. Try `-S` to stop here.
3. **`as` (from binutils), assembler.** Turns `.s` into a relocatable `.o` (ELF object file). Try `-c` to stop here.
4. **`collect2`**, when used by this GCC build. It wraps the linker and helps arrange constructor initialization. You normally do not invoke it directly.
5. **`ld` (from binutils), linker.** Combines `.o` files and libraries, resolves symbol references, applies the linker script's address layout, and writes the final ELF executable.

For a dynamically linked program, the final ELF also names a dynamic loader. That loader runs later on the target when the program starts. It is not a stage of the host compile command.

You can see the chain by adding `-v` to any compile:

```sh
$ arm-none-linux-gnueabihf-gcc -v -o hello hello.c 2>&1 | head -20
Using built-in specs.
COLLECT_GCC=arm-none-linux-gnueabihf-gcc
COLLECT_LTO_WRAPPER=/home/<you>/imx6ull/toolchains/arm-gnu-toolchain-<version>-x86_64-arm-none-linux-gnueabihf/libexec/gcc/arm-none-linux-gnueabihf/<version>/lto-wrapper
Target: arm-none-linux-gnueabihf
...
```

Common failures include incorrect include paths during preprocessing, incompatible object files during linking, and missing libraries or startup files in the sysroot.

## 6.2  The binutils inventory

`binutils` is a collection of tools that operate on object files and binaries. Cross-prefixed versions exist for every target. The ones you will use:

| Tool | What it does | When you reach for it |
|------|-------------|----------------------|
| `as` | Assemble `.s` into `.o` | Usually invoked through `gcc` |
| `ld` | Link object files and libraries into an ELF | Bare-metal builds using `-T linker.ld` |
| `objcopy` | Convert formats and extract sections | Convert an ELF into a raw binary |
| `objdump` | Disassemble code and display headers or sections | Inspect generated instructions |
| `nm` | List symbols in an object | Find where a symbol is defined or exported |
| `readelf` | Display ELF metadata | Inspect sections, segments, and dynamic information |
| `strip` | Remove symbols/debug info | Producing the shipped binary. |
| `ar` | Build/dissect `.a` archives (static libraries) | When making your own libs. |
| `addr2line` | Map address → file:line | Decoding crash addresses, oopses. |
| `size` | Print section sizes | Quick sanity check on memory budget. |

Two inspections to revisit after producing their input files.

### `objdump -d` on Lab B's build-only skeleton

```sh
$ cd ~/imx6ull/src/ch06-skeleton
$ arm-none-eabi-objdump -d led.elf
```

Run this after Lab B. Locate `_start` at `0x00908000`, SP setup, BSS clearing, and the branch to `main`. The precise instruction bytes and `main` address come from your build, not a representative hex listing.

### `readelf -l` to see segments

```sh
$ cd ~/imx6ull/src/ch06-hello
$ arm-none-linux-gnueabihf-readelf -l hello
```

Find the `LOAD` rows and, for a dynamically linked result, the `INTERP` row. The output identifies the required interpreter, commonly `/lib/ld-linux-armhf.so.3` for this glibc hard-float target. Record the actual output; header counts/addresses vary with toolchain options.

Notice: the segment marked `INTERP` says the dynamic linker for this binary is `/lib/ld-linux-armhf.so.3`. That is what runs first when the kernel `exec`s this file. Only after the dynamic linker finishes loading shared libraries does control reach `main`.

For bare-metal output we will *not* have an INTERP segment. The ELF will be statically resolved and the entry point we set is what runs.

## 6.3  Section, segment, VMA, LMA

These terms describe three different viewpoints: the compiler, the linker, and the loader.

| Word | Who mainly cares? | Meaning |
|------|-------------------|---------|
| **Section** | Compiler and linker | A named bucket of related bytes: `.text`, `.rodata`, `.data`, `.bss`, `.debug_*`. |
| **Segment** | Loader | A loadable memory range described by ELF program headers. One segment can contain several sections. |
| **VMA** | CPU at runtime | The address the code/data expects to have when it is being used. |
| **LMA** | Loader/startup code | The address where the initial bytes are stored before they are moved to their runtime address. |

If you come from MCU work, start with **sections**. You already know these:

- `.text`: executable instructions.
- `.rodata`: constants and string literals.
- `.data`: globals/statics with non-zero initial values, such as `int led = 1;`.
- `.bss`: globals/statics that start as zero, such as `int counter;`.

The linker script arranges sections. The loader does not want to reason about every tiny section. It wants bigger chunks it can load or map with permissions:

```text
sections:  .text  .rodata  .data  .bss  .debug_*
             |       |       |      |
             v       v       v      v
segments:  LOAD R-X        LOAD RW       debug is not loaded
```

So a **segment** is the loader-facing package. For a Linux process, the kernel and dynamic linker read the ELF program headers, create mappings for the `LOAD` segments, and eventually call into the program. For our bare-metal image, the "loader" is usually the Boot ROM, U-Boot, `uuu`, or our own startup code.

Now the address pair:

- **VMA** answers: "Where will this section live when the CPU uses it?"
- **LMA** answers: "Where are the bytes stored in the image before runtime setup?"

In a Linux process, a VMA is normally a virtual address. In early bare-metal code, before the MMU is enabled, it is usually the physical address from which the CPU executes or accesses data. For this chapter, think of VMA as the **runtime address**.

Simple OCRAM code can have VMA = LMA. In the first-image layout, the IVT is at `0x00907400`, but code begins at `0x00908000`. The header is not the first instruction:

```text
image in OCRAM:
  IVT    at 0x00907400, not executable code
  .text  VMA = LMA = 0x00908000
  .data  VMA = LMA = its linked address after code/constants
```

The useful case is when **where bytes are stored** differs from **where bytes must run**. Classic Cortex-M Flash + RAM does this every day:

```text
Flash image                         RAM after startup
-----------                         -----------------
.text   runs from Flash             .data  variables live here
.rodata stays in Flash              .bss   zeroed here
.data  initial values  ----copy---> .data  runtime values
```

For `.data` in that system:

| Address kind | Example meaning |
|--------------|-----------------|
| VMA | RAM address where `led` lives when C code reads/writes it. |
| LMA | Flash address where the initial value of `led` was stored in the image. |

That is why Flash/RAM startup copies `.data` from LMA to VMA, then zeros `.bss`. `AT(addr)` gives a section a different load address. Our OCRAM-only skeleton does not need that copy: its initialized data is loaded at its runtime address. Later OCRAM-to-DDR relocation makes the distinction useful again.

Linux user-space hides most of this because the kernel and dynamic linker perform the load/mapping work. Bare-metal code cannot hide it. On the i.MX6ULL, the distinction returns whenever a small image starts in OCRAM, initializes DDR, then moves code or data into DRAM.

## 6.4  Linker scripts

A linker script (`.ld` file) is a small text file that tells `ld`:

1. What memory regions exist and their attributes.
2. Which sections go into which regions.
3. Where the entry point is.
4. What symbols to export (`_etext`, `_sdata`, `_edata`, `_sbss`, `_ebss`).

Save this as `link.ld` for Lab B. It aligns code with Chapter 9's entry address but does not create a ROM header:

```text
ENTRY(_start)

MEMORY
{
    OCRAM (rwx) : ORIGIN = 0x00908000, LENGTH = 0x0000F800
    STACK (rw)  : ORIGIN = 0x00917800, LENGTH = 0x00000800
}

SECTIONS
{
    .text   : { KEEP(*(.text.startup)) *(.text*) } > OCRAM
    .rodata : { *(.rodata*) } > OCRAM
    .data   : { *(.data*) } > OCRAM
    .bss (NOLOAD) :
    {
        . = ALIGN(4);
        _sbss = .;
        *(.bss*) *(COMMON)
        . = ALIGN(4);
        _ebss = .;
    } > OCRAM

    _image_end = .;
    _stack_limit = ORIGIN(STACK);
    _stack_top = ORIGIN(STACK) + LENGTH(STACK);
    ASSERT(_image_end <= _stack_limit, "Image overlaps reserved stack")
}
```

Five things to notice:

1. `ENTRY(_start)` records the ELF entry symbol. The Boot ROM uses the IVT entry field instead, but debuggers and ELF tools use this value.
2. Code/data have 62 KiB from `0x00908000` to exclusive limit `0x00917800`. A separate 2 KiB stack ends at `0x00918000`, the ROM-active free-window limit. Headers/padding occupy space below the code; physical OCRAM extends farther but ROM loading cannot safely overwrite its top working area.
3. `SECTIONS` combines input sections into output sections. The `> OCRAM` placement assigns each output section to the next available address in OCRAM.
4. `_sbss = .; ... _ebss = .;` exports the bounds of `.bss` so our startup code can clear it.
5. `_stack_top` is an address, not allocated storage. The separate memory budget and assertion prevent linked sections from consuming its downward-growing stack region. Its 8-byte alignment satisfies the public-call stack requirement; the BSS bounds are aligned for word clearing.

We will revise this script over the next chapters as we move to DDR. The format does not change. Only the regions do.

## 6.5  The ABI: what makes function calls work

When `foo()` calls `bar()`, both sides must agree on:

- Which register contains the first argument? The second? Where do return values live?
- Which registers must `bar()` preserve, and which can it freely clobber?
- How is the stack aligned?
- Where do floating-point arguments go, in integer registers, or in FPU registers?
- How are structs > 8 bytes returned?

The **EABI** (Embedded ABI) for ARM specifies all of this. ARMv7-A Linux uses the **AAPCS** (ARM Architecture Procedure Call Standard) plus the EABI's runtime conventions. The relevant variant for us is **AAPCS-VFP**, also called "hard-float," in which floating-point parameters use `s0`-`s15` / `d0`-`d7` rather than integer registers.

The core rules (simplified):

| Register | AAPCS role |
|----------|-----------|
| r0-r3 | First four integer arguments / return value (`r0`, optionally `r0,r1` for 64-bit). Caller-saved. |
| r4-r11 | Callee-saved (must be preserved). R9 is "platform register", see §6.6. |
| r12 (ip) | Intra-procedure-call scratch. Caller-saved. |
| r13 (sp) | Stack pointer. 8-byte aligned at function boundary. |
| r14 (lr) | Link register (return address). |
| r15 (pc) | Program counter. |
| s0-s15 / d0-d7 | Applicable hard-float arguments/return values; allocation depends on types and signature, with different variadic-call rules. Caller-saved. |
| s16-s31 / d8-d15 | Callee-saved FP. |

Why this matters: when you write a function in assembly and call it from C (or vice versa), you **must** obey AAPCS or memory corruption follows. The toolchain assumes it. You must too.

### Hard-float vs soft-float

Three flavors of FP ABI exist:

- **soft-float** (`-mfloat-abi=soft`), FP ops are emulated in libgcc. FP arguments go in integer registers. Slow but universally compatible.
- **softfp** (`-mfloat-abi=softfp`), FP ops use the FPU, but FP arguments still go in integer registers. Compromise, used when linking soft-float libraries with code that has an FPU.
- **hard-float** (`-mfloat-abi=hard`), FP ops use the FPU. FP arguments use FP registers. Fastest.

The Linux triplet suffix normally distinguishes `gnueabi` from hard-float `gnueabihf`. Objects/libraries with incompatible floating-point calling conventions must not be combined; the linker often diagnoses their attributes. A prefix alone does not prove that every freestanding object is incompatible. Check `readelf -A` and the matching runtime, and use one consistent compiler/ABI selection per build.

The Linux toolchain selected for this book uses the hard-float ABI. All Linux user-space objects and libraries that we combine must use the same ABI.

## 6.6  The C library, or its absence

For bare-metal code in Part II, we want **no libc at all**. We will write our own `memcpy` and our own `printf`. This keeps the early examples explicit: every dependency and hardware assumption is visible.

The C library, or libc, is **separate from GCC**. GCC is the compiler driver and compiler. Libc is a runtime library plus headers that the compiler links against when you build Linux user-space programs. A complete cross-toolchain usually ships all of these together:

| Piece | Example | Job |
|-------|---------|-----|
| Compiler | `arm-none-linux-gnueabihf-gcc` | Turns C into object files. |
| Binutils | `as`, `ld`, `objcopy`, `readelf` | Assembles, links, converts, and inspects binaries. |
| libc headers | `stdio.h`, `unistd.h`, `pthread.h` | Tell the compiler what user-space APIs look like. |
| libc binaries | `libc.so`, `libc.a`, startup files such as `crt1.o` | Provide the code that implements the C/POSIX runtime. |
| libgcc | `libgcc.a` | Small helper routines that GCC itself may need, such as integer division helpers. |

The Linux-target headers and libraries live in the toolchain's **sysroot**, a directory resembling a target root filesystem. Glibc is packaged alongside our official Arm compiler, not inside its executable. Inspect the selected installation with `arm-none-linux-gnueabihf-gcc -print-sysroot` and `-print-file-name=libc.a`.

For Linux user-space code, we use a libc. Three options:

| libc | Size of typical static `hello world` | Notes |
|------|--------------------------------------|-------|
| glibc | ~700 KB | Common on general-purpose Linux distributions. Broad compatibility. |
| musl | ~30 KB | Small, MIT-licensed implementation often used in compact systems. |
| uClibc-ng | ~50 KB | Maintained fork of uClibc, available in Buildroot and used by some embedded distributions. |

The selected official Arm Linux archive supplies glibc. Chapter 34 compares libc choices; a musl build needs matching headers/libraries and toolchain configuration, not merely a flag on a glibc build.

### What libc actually provides

A libc bundles:

- **Wrappers around syscalls** (`open`, `read`, `write`, `mmap`, ...) so you can call them as C functions.
- **Memory allocator** (`malloc`, `free`, internally calling `brk`/`mmap`).
- **Standard I/O** (`fopen`, `printf`), buffered layers atop the syscall wrappers.
- **Math** (`sin`, `sqrt`, ...), in `libm.so`.
- **POSIX threads** (`pthread_*`), sometimes a separate `libpthread.so`, sometimes folded in.
- **Locale, time, network, etc.**

Bare-metal code does not receive these services automatically. There is no `malloc`, `printf`, or `errno` unless our program or another linked library implements it.

## 6.7  Make, in working depth

`make` runs the builds for the bare-metal projects in Part II and for U-Boot, Linux, and Buildroot later in the book. This section explains the parts used by those builds.

First pass: rules, dependencies, automatic variables, and the complete Makefile are enough for Lab B. Assignment variants, functions, and conditionals are a reference track; do not memorize every form before your first build.

Before syntax, understand the job.

`make` decides which build commands need to run. It does not know C, assembly, ELF, or ARM by itself. You teach it:

1. Which files you want to create.
2. Which input files each output depends on.
3. Which shell command creates the output from the inputs.

Then `make` answers one question: **what commands need to run right now?**

It answers by looking at files and timestamps:

- If the output file does not exist, build it.
- If an input file is newer than the output file, rebuild it.
- If the output exists and all inputs are older, skip it.

For our bare-metal LED program, the dependency chain looks like this:

```text
startup.S ──► startup.o ┐
                         ├──► led.elf ──► led.bin
main.c    ──► main.o    ┘
link.ld   ──────────────┘
```

If you edit `main.c`, only `main.o`, `led.elf`, and `led.bin` need rebuilding. `startup.o` can be reused. If you edit `link.ld`, the object files can be reused, but `led.elf` and `led.bin` must be rebuilt. This is why `make` exists: it avoids rebuilding everything when only part of the input changed.

A `Makefile` records those dependency relationships and the shell commands that produce each output. `make` decides whether to run the commands and in what order.

When you run plain `make`, it reads a file named `Makefile` in the current directory and builds the first target in that file. In our examples, the first target is usually `all`, and `all` depends on the final file we want, such as `led.bin`.

### 6.7.1  Rule shape

```make
target ...: prerequisite ...
<TAB>command
<TAB>command
```

In a rule, the *target* is the file you want to create. The *prerequisites* are the files it depends on. The indented commands are the recipe that creates or updates the target.

`make` builds the target when the target does not exist or when a prerequisite is newer than the target. Recipe commands **must** be indented with a literal `TAB`. Spaces do not work.

### 6.7.2  Variables: four flavors of assignment

```make
CC     = arm-none-linux-gnueabihf-gcc         # 1) recursive ("deferred")
CC    := arm-none-linux-gnueabihf-gcc         # 2) simple ("immediate")
CFLAGS ?= -O2                                 # 3) only if not already set
OBJS  += extra.o                              # 4) append
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

Use `:=` everywhere by default. The `=` form is occasionally necessary (recursive expansion of generated variables), but it is easier to misuse.

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

Tells `make` that `all` / `clean` / `install` are **not** filenames. Without `.PHONY`, a file named `clean` would make `make clean` consider the target up to date and skip the recipe. With `.PHONY`, the recipe always runs.

### 6.7.5  Useful functions

`make` has a small set of built-in functions, called as `$(name args,...)`:

| Function | What it does | Example |
|----------|--------------|---------|
| `$(wildcard PATTERN)` | List files matching a glob (no quoting) | `$(wildcard *.c)` → `a.c b.c` |
| `$(patsubst PAT,REPL,LIST)` | Pattern substitution | `$(patsubst %.c,%.o,a.c b.c)` → `a.o b.o` |
| `$(subst FROM,TO,STR)` | Plain string substitution | `$(subst .,_,a.b.c)` → `a_b_c`; a space before `_` would be part of the replacement |
| `$(dir NAMES)` | Directory part | `$(dir src/a.c)` → `src/` |
| `$(notdir NAMES)` | Filename part | `$(notdir src/a.c)` → `a.c` |
| `$(basename NAMES)` | Drop the extension | `$(basename src/a.c)` → `src/a` |
| `$(addsuffix S,LIST)` / `$(addprefix P,LIST)` | Append / prepend | `$(addsuffix .o,a b)` → `a.o b.o` |
| `$(filter PAT,LIST)` / `$(filter-out PAT,LIST)` | Keep / remove matching | `$(filter %.c,a.c b.h)` → `a.c` |
| `$(sort LIST)` | Sort + de-duplicate | `$(sort c a b a)` → `a b c` |
| `$(shell CMD)` | Run a shell command, capture stdout | `$(shell uname -m)` → `x86_64` |

A common idiom, collect every `.c` in the tree:

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

These Make directives are evaluated when Make reads the file. They are not tab-indented shell recipe commands, and automatic variables such as `$@` are not available as recipe-time values there. Compare:

```make
show:
ifeq ($(DEBUG),1)
	@echo debug selected while reading the Makefile
else
	@echo release selected while reading the Makefile
endif
	@if [ -f main.c ]; then echo main.c exists at recipe time; fi
```

The `ifeq`/`else`/`endif` lines start at column one; the shell `if` starts with a tab. See [GNU Make conditional syntax](https://www.gnu.org/software/make/manual/html_node/Conditional-Syntax.html).

### 6.7.7  Parallelism

```sh
$ make -j$(nproc)            # use all available cores
$ make -j8                    # 8 jobs in parallel
```

Parallel jobs can reduce a large build's time, but the gain depends on the host. Use fewer jobs if RAM is limited, especially in a VM. Missing dependency edges can cause races; a parallel-only failure needs diagnosis rather than a claim that `-j` is harmless.

### 6.7.8  A complete Makefile for Lab B's skeleton

```make
CROSS  := arm-none-eabi-
CC     := $(CROSS)gcc
OC     := $(CROSS)objcopy

CFLAGS := -mcpu=cortex-a7 -marm -mfloat-abi=soft \
          -ffreestanding -fno-builtin -fno-pie -fno-stack-protector \
          -fno-unwind-tables -fno-asynchronous-unwind-tables -O2 -g -Wall
LDFLAGS := -nostdlib -Wl,-T,link.ld

SRCS   := startup.S main.c
OBJS   := startup.o main.o

all: led.bin

%.o: %.S
	$(CC) $(CFLAGS) -MMD -MP -c -o $@ $<

%.o: %.c
	$(CC) $(CFLAGS) -MMD -MP -c -o $@ $<

led.elf: $(OBJS) link.ld
	$(CC) $(CFLAGS) $(LDFLAGS) -o $@ $(OBJS)

led.bin: led.elf
	$(OC) -O binary $< $@

clean:
	rm -f startup.o main.o startup.d main.d led.elf led.bin

-include $(OBJS:.o=.d)

.PHONY: all clean
```

Every flag in `CFLAGS` matters:

- `-mcpu=cortex-a7`: generate code that uses Cortex-A7 features.
- `-marm -mfloat-abi=soft`: this integer-only startup exercise uses ARM instructions and does not enable VFP. Hard-float code generation alone would not enable the hardware in startup.
- `-ffreestanding`: "I do not have a hosted C environment." Disables the assumption that `main` is the standard entry, etc.
- `-fno-builtin`: disables compiler's optimization of calls like `printf` into special builtins.
- `-fno-pie -fno-stack-protector`: do not require a position-independent runtime or stack-check runtime in this freestanding exercise.
- `-fno-unwind-tables -fno-asynchronous-unwind-tables`: no runtime stack-unwinding tables are needed here.
- `-nostdlib` is a **link** option in `LDFLAGS`: the GCC driver adds no default startup/libc/libgcc. `-Wl,-T,link.ld` forwards the script selection to its linker. This deliberately uses GCC for linking so a later explicit `-lgcc` can select its matching runtime.
- `-MMD -MP` writes `.d` header dependencies; `-include` reads them on the next build. A header edit then rebuilds the affected objects.
- `-O2 -g`: optimize but keep debug info.
- `-Wall`: turn on the warnings everyone should be using.

## 6.8  Static vs dynamic linking (for Linux user-space)

Two ways to combine your code with libraries:

- **Static.** Library code is copied into your binary at link time. The binary is self-contained. No `libfoo.so` is needed at runtime. Bigger file. Faster startup.
- **Dynamic.** Library code lives in `.so` files on disk. Your binary references them by name. The dynamic loader (`/lib/ld-linux-armhf.so.3`) resolves them at process start.

Linux distributions normally use dynamic linking. Small embedded systems may use either model. Static linking simplifies deployment for a few standalone programs, while dynamic linking saves storage when many programs share the same libraries.

To force static:

```sh
$ arm-none-linux-gnueabihf-gcc -g -static -o hello hello.c
$ file hello
hello: ELF 32-bit LSB executable, ARM, EABI5 version 1 (SYSV),
       statically linked, BuildID[sha1]=..., with debug_info, not stripped
```

Compare sizes:

```sh
$ arm-none-linux-gnueabihf-gcc -o hello-dyn hello.c
$ ls -l hello-dyn
$ arm-none-linux-gnueabihf-gcc -static -o hello-stc hello.c
$ ls -l hello-stc
```

Record your measured sizes. Rough examples are kilobytes for a dynamic hello and hundreds of kilobytes for a glibc static hello; flags, symbols, libraries, and versions change them. Static Linux code still needs a Linux kernel, and some library features may need external configuration/resources. Static linking does not turn a Linux executable into bare-metal firmware.

## 6.9  ELF structure needed for this book

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

- **Type `REL`** (relocatable, `.o`), produced by the assembler, fed to the linker.
- **Type `EXEC`** is an executable type, not proof of static linking: a dynamically linked non-PIE executable can also be `EXEC`.
- **Type `DYN`** can describe a shared library, dynamic PIE, or static PIE. Type and runtime-library dependencies are separate questions.
- **`.bss` occupies no file bytes.** It only declares "give me N bytes of zero at runtime." The startup code (or the kernel) zeroes it.
- **DWARF** is the debug-info format used in `.debug_*` sections. `gdb`, `objdump -S`, and `addr2line` read it.

Use `file` for a quick summary, `readelf -l` for an interpreter/program headers, and `readelf -d` for dynamic entries/dependencies. `readelf -S` checks `.debug_*`; `nm` checks ordinary symbols. Missing DWARF can simply mean the program was built without `-g`; it does not prove stripping. See [elf(5)](https://man7.org/linux/man-pages/man5/elf.5.html).

## 6.10  Lab

Two builds using the files supplied here. Neither transfers an image to the board.

### Lab A, Host hello world, inspected

```sh
$ cd ~/imx6ull/src/ch06-hello
$ gcc -g -O2 -o hello-host hello.c
$ arm-none-linux-gnueabihf-gcc -g -O2 -o hello-arm hello.c
$ file hello-host hello-arm
$ readelf -a hello-arm | head -40
$ arm-none-linux-gnueabihf-objdump -d hello-arm | grep -A 5 '<main>:'
```

Run `./hello-host` on the host; it should print `hello`. Inspect, but do not directly execute, `hello-arm` on x86_64. Find the call to `puts` (possibly `puts@plt`) and argument setup in its disassembly. Exact instruction choices vary.

### Lab B, Bare-metal LED skeleton (build only. We'll add the LED code in Ch 9)

Create `~/imx6ull/src/ch06-skeleton/` with:

- `startup.S`: the complete listing below.
- `main.c`: the complete listing below.
- `link.ld`: the minimal script from §6.4.
- `Makefile`: from §6.7.

Once all four files below/from the referenced sections are saved, `make` should produce `led.elf` and `led.bin`.

First create and enter the directory with `mkdir -p ~/imx6ull/src/ch06-skeleton` and `cd ~/imx6ull/src/ch06-skeleton`. Use `nano` to create the four named files. Save this as `startup.S`:

```asm
.syntax unified
.cpu cortex-a7
.arm
.section .text.startup, "ax"
.global _start
_start:
    cpsid   if
    ldr     sp, =_stack_top
    ldr     r0, =_sbss
    ldr     r1, =_ebss
    mov     r2, #0
1:
    cmp     r0, r1
    bhs     2f
    str     r2, [r0], #4
    b       1b
2:
    bl      main
3:
    b       3b
.ltorg
```

`cpsid if` masks IRQ/FIQ; `ldr ... =symbol` loads a linked address. SP selects the reserved stack. The loop zeros words between `_sbss` and `_ebss`; `1b` means the previous label `1`, while `2f` means the next label `2`. `bl main` calls C and places a return address in LR. If C returns, the final branch stays in place. `.ltorg` emits the literal constants used by the address loads. This is build-only startup, not a full exception/ROM-handoff implementation.

Save as `main.c`:

```c
volatile unsigned int counter;
int main(void)
{
    while (1) {
        counter++;
    }
}
```

The volatile global supplies a real four-byte BSS object. After saving all files, run `make`; a second unchanged `make` should do no build work. Edit the loop and rebuild to observe the dependency chain. **`led.bin` is not bootable yet**: Chapter 9 adds the ROM wrapper and observable LED behavior.

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
4. Does `_stack_top` equal `0x00918000` and `_stack_limit` equal `0x00917800`? Is `_image_end` below the stack limit?

Check `_start = 0x00908000`, `counter` inside BSS, and the two stack bounds. `.bss` has runtime space but no stored initialization bytes. Use `readelf -a` for additional details; symbol/layout checks do not prove board execution.

## 6.11  Pitfalls

- **Mixing incompatible toolchain outputs.** Do not link bare-metal objects from `arm-none-eabi-` into Linux user-space programs built with `arm-none-linux-gnueabihf-`. They have different runtime assumptions. The failure may appear only at link time and may mention an ABI or relocation mismatch.
- **`-nostdlib` also removes the automatic libgcc link.** If code uses an operation such as 64-bit integer division, GCC may emit a call to `__aeabi_uldivmod` from `libgcc`. Add `-lgcc` explicitly after your object files when required.
- **Linker-script order matters.** Place a specific startup section before a broader wildcard such as `*(.text*)` when startup must appear first. Chapter 9 shows the required ordering.
- **`.bss` must be zeroed.** If startup does not clear `.bss`, uninitialized globals contain old memory values and program behavior can change between boots.
- **Wrong `-march`/`-mcpu`.** Toolchain defaults vary. Always specify `-mcpu=cortex-a7` explicitly for Cortex-A7 code. The compiler then schedules instructions for that pipeline.
- **`strip` on the binary you wanted to debug.** Keep an unstripped copy. A useful convention in your Makefile: `$(NAME).elf` is unstripped (for `gdb`/`objdump`). `$(NAME).stripped.elf` is the smaller deliverable.

## 6.12  Going deeper

- *Linkers and Loaders* by John Levine. A detailed explanation of linkers and loaders.
- [ELF for the Arm Architecture (AAELF32)](https://github.com/ARM-software/abi-aa/blob/main/aaelf32/aaelf32.rst), alongside the generic ELF specification. AAPCS32 defines calling conventions, not the whole ELF format.
- The GCC manual, at least the section on language-independent options.
- *Procedure Call Standard for the Arm Architecture* (AAPCS32), ARM IHI 0042.
- `man 5 elf`, `man 1 ld`, `man 8 ld.so`.
- LWN: "How programs get run" (the kernel `exec` path. Relevant when you write a `binfmt`).

> Next chapter: **Chapter 7: The Boot ROM, IVT, DCD, and BootData.** With the toolchain understood, we can build images in the format expected by the Boot ROM.
> **DCD:** Device Configuration Data: ROM-executed register writes that prepare clocks and DDR before your code runs.
