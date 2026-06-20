# Chapter 6: The toolchain

> **What:** the set of programs that turn your C and assembly source into a binary your i.MX6ULL will execute.
>
> **Why:** every later chapter ends with "now build it." If you do not know what the build tools are doing, build failures become guesswork.
>
> **Focus:** **(a)** that `gcc` is a *driver* over half a dozen smaller tools. **(b)** that **ELF** is the universal container, and the linker decides where every byte ends up. **(c)** that the **ABI** is the contract that every function call in your program follows.

> **ELF:** Executable and Linkable Format, the standard Linux object and executable file format.

> **ABI:** Application Binary Interface: the calling convention, register use, binary format, and library contract that let separately built code run together.

## 6.1  `gcc` is not one program

When you type:

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

This output lets you verify the instructions and addresses produced by the toolchain.

### `readelf -l` to see segments

```sh
$ arm-none-linux-gnueabihf-readelf -l hello
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

Most simple programs have VMA = LMA. If the Boot ROM loads your whole image into OCRAM at `0x00907400`, and your code also runs from `0x00907400`, the load address and runtime address match:

```text
image in OCRAM:
  .text  VMA 0x00907400, LMA 0x00907400
  .data  VMA 0x00908000, LMA 0x00908000
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

That is why startup code copies `.data` from LMA to VMA before `main()`, then zeros `.bss`. In linker-script language, `AT(addr)` is how you say "this section runs over here, but its initial bytes are loaded over there." Chapter 10 uses this pattern with `AT(_etext)`.

Linux user-space hides most of this because the kernel and dynamic linker perform the load/mapping work. Bare-metal code cannot hide it. On the i.MX6ULL, the distinction returns whenever a small image starts in OCRAM, initializes DDR, then moves code or data into DRAM.

## 6.4  Linker scripts

A linker script (`.ld` file) is a small text file that tells `ld`:

1. What memory regions exist and their attributes.
2. Which sections go into which regions.
3. Where the entry point is.
4. What symbols to export (`_etext`, `_sdata`, `_edata`, `_sbss`, `_ebss`).

The simplest useful linker script for our Chapter 9 bare-metal LED:

```text
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

1. `ENTRY(_start)` records the ELF entry symbol. The Boot ROM uses the IVT entry field instead, but debuggers and ELF tools use this value.
2. `MEMORY` declares one region called `OCRAM` of ~100 KB. Permissions (`rwx`) are advisory for now.
3. `SECTIONS` combines input sections into output sections. The `> OCRAM` placement assigns each output section to the next available address in OCRAM.
4. `_sbss = .; ... _ebss = .;` exports the bounds of `.bss` so our startup code can clear it.
5. `_stack_top` is computed at link time as one address past the end of the declared OCRAM region. Startup code loads `sp` from this symbol.

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
| s0-s15 / d0-d7 | First eight FP arguments / FP return. Caller-saved. |
| s16-s31 / d8-d15 | Callee-saved FP. |

Why this matters: when you write a function in assembly and call it from C (or vice versa), you **must** obey AAPCS or memory corruption follows. The toolchain assumes it. You must too.

### Hard-float vs soft-float

Three flavors of FP ABI exist:

- **soft-float** (`-mfloat-abi=soft`), FP ops are emulated in libgcc. FP arguments go in integer registers. Slow but universally compatible.
- **softfp** (`-mfloat-abi=softfp`), FP ops use the FPU, but FP arguments still go in integer registers. Compromise, used when linking soft-float libraries with code that has an FPU.
- **hard-float** (`-mfloat-abi=hard`), FP ops use the FPU. FP arguments use FP registers. Fastest.

The triplet suffix tells you which: `arm-none-linux-gnueabi` (soft), `arm-none-linux-gnueabihf` (hard). **You cannot link a soft-float `.o` with a hard-float `.o`**. The linker refuses.

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

Those headers and libraries live in the toolchain's **sysroot**: a directory that looks like a tiny target root filesystem, containing target headers and target libraries. So people say "the Ubuntu ARM GCC toolchain ships glibc," but glibc is not inside the compiler executable. It is packaged alongside the compiler and selected by the compiler when linking.

For Linux user-space code, we use a libc. Three options:

| libc | Size of typical static `hello world` | Notes |
|------|--------------------------------------|-------|
| glibc | ~700 KB | Common on general-purpose Linux distributions. Broad compatibility. |
| musl | ~30 KB | Small, MIT-licensed implementation often used in compact systems. |
| uClibc-ng | ~50 KB | Maintained fork of uClibc, available in Buildroot and used by some embedded distributions. |

We will mostly use glibc because the Ubuntu toolchain ships it. In Chapter 34 we switch to musl once for comparison.

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
| `$(subst FROM,TO,STR)` | Plain string substitution | `$(subst ., _,a.b.c)` → `a_b_c` |
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

Four conditional forms: `ifeq`, `ifneq`, `ifdef`, `ifndef`. They work both at the *top level* (selecting variable values) and inside *recipes*, though for recipe-level branching, shell `if` is usually cleaner.

### 6.7.7  Parallelism

```sh
$ make -j$(nproc)            # use all available cores
$ make -j8                    # 8 jobs in parallel
```

For our bare-metal builds (~10 files), `-j` makes no measurable difference. For the kernel (~30 000 files) it cuts build time by ~7× on an 8-core host. Always use it for kernel work. Harmless for everything else.

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

Every flag in `CFLAGS` matters:

- `-mcpu=cortex-a7`: generate code that uses Cortex-A7 features.
- `-mfpu=neon-vfpv4 -mfloat-abi=hard`: match what the silicon supports and the ABI we picked.
- `-ffreestanding`: "I do not have a hosted C environment." Disables the assumption that `main` is the standard entry, etc.
- `-fno-builtin`: disables compiler's optimization of calls like `printf` into special builtins.
- `-nostdlib`: do not implicitly link `crt0`, libc, libgcc. (We will manually add libgcc later if we need its compiler-rt routines.)
- `-O2 -g`: optimize but keep debug info.
- `-Wall`: turn on the warnings everyone should be using.

## 6.8  Static vs dynamic linking (for Linux user-space)

Two ways to combine your code with libraries:

- **Static.** Library code is copied into your binary at link time. The binary is self-contained. No `libfoo.so` is needed at runtime. Bigger file. Faster startup.
- **Dynamic.** Library code lives in `.so` files on disk. Your binary references them by name. The dynamic loader (`/lib/ld-linux-armhf.so.3`) resolves them at process start.

Linux distributions normally use dynamic linking. Small embedded systems may use either model. Static linking simplifies deployment for a few standalone programs, while dynamic linking saves storage when many programs share the same libraries.

To force static:

```sh
$ arm-none-linux-gnueabihf-gcc -static -o hello hello.c
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

Expect roughly 8 KB dynamic vs 600 KB static with glibc, or ~30 KB static with musl.

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
- **Type `EXEC`** (executable), produced by linking statically.
- **Type `DYN`** (shared object / PIE executable), relocatable at load time, used for both `.so` libraries and modern position-independent executables.
- **`.bss` occupies no file bytes.** It only declares "give me N bytes of zero at runtime." The startup code (or the kernel) zeroes it.
- **DWARF** is the debug-info format used in `.debug_*` sections. `gdb`, `objdump -S`, and `addr2line` read it.

When `gdb` says "no debug info, no symbols", it means the binary was stripped (`strip` removed the symbol and DWARF sections).

## 6.10  Lab

Two builds. Both reproducible from a clean checkout.

### Lab A, Host hello world, inspected

```sh
$ cat > hello.c <<'EOF'
#include <stdio.h>
int main(void) { puts("hello"); return 0; }
EOF
$ gcc -g -O2 -o hello-host hello.c
$ arm-none-linux-gnueabihf-gcc -g -O2 -o hello-arm hello.c
$ file hello-host hello-arm
$ readelf -a hello-arm | head -40
$ arm-none-linux-gnueabihf-objdump -d hello-arm | grep -A 5 '<main>:'
```

Read the disassembly. Find the `bl puts` instruction (or its inline equivalent). Find where `r0` is loaded with the address of the string `"hello"`.

### Lab B, Bare-metal LED skeleton (build only. We'll add the LED code in Ch 9)

Create `~/imx6ull/src/ch06-skeleton/` with:

- `startup.S`: a minimal startup that sets SP and branches to `main`.
- `main.c`: `int main(void){ while(1); return 0; }`.
- `link.ld`: the minimal script from §6.4.
- `Makefile`: from §6.7.

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

Compare the reported sections, symbols, and addresses with the linker script. Use `readelf -a` when you need additional ELF details.

## 6.11  Pitfalls

- **Mixing incompatible toolchain outputs.** Do not link bare-metal objects from `arm-none-eabi-` into Linux user-space programs built with `arm-none-linux-gnueabihf-`. They have different runtime assumptions. The failure may appear only at link time and may mention an ABI or relocation mismatch.
- **`-nostdlib` also removes the automatic libgcc link.** If code uses an operation such as 64-bit integer division, GCC may emit a call to `__aeabi_uldivmod` from `libgcc`. Add `-lgcc` explicitly after your object files when required.
- **Linker-script order matters.** Place a specific startup section before a broader wildcard such as `*(.text*)` when startup must appear first. Chapter 9 shows the required ordering.
- **`.bss` must be zeroed.** If startup does not clear `.bss`, uninitialized globals contain old memory values and program behavior can change between boots.
- **Wrong `-march`/`-mcpu`.** Toolchain defaults vary. Always specify `-mcpu=cortex-a7` explicitly for Cortex-A7 code. The compiler then schedules instructions for that pipeline.
- **`strip` on the binary you wanted to debug.** Keep an unstripped copy. A useful convention in your Makefile: `$(NAME).elf` is unstripped (for `gdb`/`objdump`). `$(NAME).stripped.elf` is the smaller deliverable.

## 6.12  Going deeper

- *Linkers and Loaders* by John Levine. A detailed explanation of linkers and loaders.
- *The ELF Specification* (latest is the System V ABI ed. 4.1. The AAPCS additions are in ARM IHI 0042).
- The GCC manual, at least the section on language-independent options.
- *Procedure Call Standard for the Arm Architecture* (AAPCS32), ARM IHI 0042.
- `man elf`, `man 5 elf`, `man 1 ld`, `man 1 ld.so`.
- LWN: "How programs get run" (the kernel `exec` path. Relevant when you write a `binfmt`).

> Next chapter: **Chapter 7: The Boot ROM, IVT, DCD, and BootData.** With the toolchain understood, we can build images in the format expected by the Boot ROM.
> **DCD:** Device Configuration Data: ROM-executed register writes that prepare clocks and DDR before your code runs.
