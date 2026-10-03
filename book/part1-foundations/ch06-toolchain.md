# Chapter 6: The toolchain

What happens when you press Build in an MCU IDE? Source files become object files, those objects are linked at chosen addresses, and another tool may produce the file used for downloading. The IDE collects the steps behind one button. Here we will run and inspect them ourselves.

We already selected two toolchains in Chapter 3. Now we will use a small C program to follow the Linux-target build, then assemble a bare-metal skeleton with its own startup code and linker script. Neither build needs a board transfer yet. By the end, the different files in the build directory should have recognizable jobs rather than just different extensions.

## 6.1  `gcc` is not one program

Start with a program small enough that the build machinery is easier to see than the application. Source Chapter 3's environment file, make a directory for the experiment, and open `hello.c`:

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

Build it for Arm Linux with the Linux-target compiler. We will inspect this result on the PC, not run it directly on the x86_64 host:

```sh
$ arm-none-linux-gnueabihf-gcc -O2 -o hello hello.c
```

One command produced `hello`, but several kinds of work took place. The `gcc` command is a **driver**: it selects the required tools and passes the results between stages. The output uses **ELF**, the Executable and Linkable Format, which carries code together with metadata about the target and its layout.

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

If a build fails, ask which stage reported the error. A missing header belongs to preprocessing or compilation; an undefined reference or incompatible object usually belongs to linking. Knowing the stage gives you a smaller problem to investigate than "the compiler did not work."

## 6.2  The binutils inventory

The compiler is only part of the toolchain. **Binutils** supplies tools that assemble, link, convert, and inspect binary files. The prefix selects the target family, just as it did for GCC. Use this table as a guide to which tool answers a particular question:

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

There are two files we will keep inspecting: the Linux `hello` we just built and the bare-metal ELF produced by Lab B. The commands below use those files; wait until Lab B has supplied `led.elf` before trying its disassembly.

### `objdump -d` on Lab B's build-only skeleton

```sh
$ cd ~/imx6ull/src/ch06-skeleton
$ arm-none-eabi-objdump -d led.elf
```

Run this after Lab B and look for `_start` at `0x00908000`. Follow the stack-pointer setup, the loop that clears BSS, and the branch to `main`. These are the instructions the tools generated from our startup source. Read their actual addresses and bytes from your result; they need not match a representative listing from another build.

### `readelf -l` to see segments

```sh
$ cd ~/imx6ull/src/ch06-hello
$ arm-none-linux-gnueabihf-readelf -l hello
```

Find the `LOAD` rows and, for a dynamically linked result, the `INTERP` row. The output identifies the required interpreter, commonly `/lib/ld-linux-armhf.so.3` for this glibc hard-float target. Record the actual output; header counts/addresses vary with toolchain options.

The `INTERP` row is more than a filename in a report. It tells the target kernel which dynamic loader the executable needs. That loader arranges the shared libraries before startup reaches `main`. If the target filesystem lacks the requested loader, the program cannot start even though compilation succeeded.

Our bare-metal ELF has no `INTERP` segment. There is no Linux loader to prepare its runtime. We must arrange startup ourselves, and the boot image must tell the ROM where to enter that code.

## 6.3  Section, segment, VMA, LMA

Why does one tool report a `.text` section while another reports a `LOAD` segment? They are describing the same file for different jobs. The compiler and linker organize its contents; the loader needs to know what memory to prepare. The address terms VMA and LMA describe where those contents are used and initially stored.

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

So a **segment** is the loader's view. For a Linux process, the kernel and dynamic linker use the ELF program headers to create mappings for `LOAD` segments. Our raw bare-metal image takes a different route: `objcopy` extracts bytes from the ELF, and the ROM image wrapper supplies the loading information. The ROM does not read our ELF section table.

Now separate the two address questions:

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

The distinction becomes useful when **where bytes are stored** differs from **where they are used**. A familiar Cortex-M Flash-and-RAM project already has such a case:

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

You may have used this arrangement for years without editing its linker script. The startup file and IDE supplied it. On the i.MX6ULL we need to recognize it explicitly, especially when code begins in OCRAM, initializes DDR, and later moves into DRAM.

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

Read the script from top to bottom. `ENTRY(_start)` records the entry symbol for ELF tools and debuggers. Later, the Boot ROM will use the image header's IVT entry instead, so the two descriptions must agree about where our code begins.

`MEMORY` divides the available space into a 62 KiB code/data region starting at `0x00908000` and a separate 2 KiB stack region starting at `0x00917800`. The stack ends at `0x00918000`, the ROM-active free-window limit from Chapter 5. Headers and padding belong below the code; the physical OCRAM extending above that limit is still in use by the ROM during loading.

`SECTIONS` places input sections into the output. `> OCRAM` assigns them to successive addresses in our OCRAM region. Within BSS, the dot means the current placement address, so `_sbss = .;` and `_ebss = .;` give startup the bounds it must clear.

The stack symbols are addresses, not an allocation caused by naming them. The separate memory budget and `ASSERT` keep linked sections out of the stack's downward-growing region. `_stack_top` is 8-byte aligned for public function calls, and the BSS bounds are aligned for clearing whole words. When we move to DDR, we will change the regions while keeping these same placement ideas.

## 6.5  The ABI: what makes function calls work

Suppose one source file calls a function compiled from another file. The compiler cannot choose argument registers independently for each one. Both sides need the same **Application Binary Interface**, or ABI. In particular, they must agree on:

- Which register contains the first argument? The second? Where do return values live?
- Which registers must `bar()` preserve, and which can it freely clobber?
- How is the stack aligned?
- Where do floating-point arguments go, in integer registers, or in FPU registers?
- How does a function return a structure rather than a single integer?

The **EABI** (Embedded ABI) for ARM specifies all of this. ARMv7-A Linux uses the **AAPCS** (ARM Architecture Procedure Call Standard) plus the EABI's runtime conventions. The relevant variant for us is **AAPCS-VFP**, also called "hard-float," in which floating-point parameters use `s0`-`s15` / `d0`-`d7` rather than integer registers.

The core rules (simplified):

| Register | AAPCS role |
|----------|-----------|
| r0-r3 | First four integer arguments / return value (`r0`, optionally `r0,r1` for 64-bit). Caller-saved. |
| r4-r11 | Callee-saved (must be preserved). R9 has a platform-specific role; see Chapter 4. |
| r12 (ip) | Intra-procedure-call scratch. Caller-saved. |
| r13 (sp) | Stack pointer. 8-byte aligned at function boundary. |
| r14 (lr) | Link register (return address). |
| r15 (pc) | Program counter. |
| s0-s15 / d0-d7 | Applicable hard-float arguments/return values; allocation depends on types and signature, with different variadic-call rules. Caller-saved. |
| s16-s31 / d8-d15 | Callee-saved FP. |

The compiler follows these rules for C calls. Handwritten assembly needs to follow them too. For example, if a C caller keeps a value in a callee-saved register, an assembly function that overwrites it without restoring it can damage the caller's work. A function may return to the correct address and still be wrong because it broke this agreement.

### Hard-float vs soft-float

Floating-point options describe both the instructions used and how arguments cross a function boundary. GCC provides three selections:

- **soft-float** (`-mfloat-abi=soft`) uses software floating-point operations and the base calling convention, with floating-point arguments passed through core registers or the stack as applicable.
- **softfp** (`-mfloat-abi=softfp`) permits hardware floating-point instructions while retaining the base calling convention.
- **hard-float** (`-mfloat-abi=hard`) permits hardware instructions and uses the VFP calling-convention variant for applicable arguments.

The practical difference is compatibility, not a promise that one option always makes a program faster. See [GCC's Arm floating-point options](https://gcc.gnu.org/onlinedocs/gcc/ARM-Options.html#index-mfloat-abi).

The Linux triplet suffix normally distinguishes `gnueabi` from hard-float `gnueabihf`. Objects/libraries with incompatible floating-point calling conventions must not be combined; the linker often diagnoses their attributes. A prefix alone does not prove that every freestanding object is incompatible. Check `readelf -A` and the matching runtime, and use one consistent compiler/ABI selection per build.

The Linux toolchain selected for this book uses the hard-float ABI. All Linux user-space objects and libraries that we combine must use the same ABI.

## 6.6  The C library, or its absence

Our `hello` used `puts()` without supplying its implementation. A library provided it. That is convenient for Linux user space, but our first bare-metal program has no operating system or runtime prepared for such a call. In Part II, we begin with **no libc** and later write the small `memcpy` and `printf` routines our experiments need.

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

Knowing a function's name is not enough to make it available. In a bare-metal build, `malloc`, `printf`, or `errno` needs an implementation from our code or a deliberately selected library. This is why runtime dependencies matter as much as the target instruction set.

## 6.7  Make, in working depth

`make` runs the builds for the bare-metal projects in Part II and for U-Boot, Linux, and Buildroot later in the book. This section explains the parts used by those builds.

Before learning the syntax, consider the next edit to our program. Repeating a compile command by hand is manageable for one file. With startup assembly, several C files, headers, and a linker script, it becomes easy to forget a step or rebuild the wrong output. `make` records those relationships.

For Lab B, concentrate on rules, dependencies, automatic variables, and the complete Makefile. The assignment variants, functions, and conditionals are reference material for larger builds; you do not need to memorize them before trying the skeleton.

`make` decides which build commands need to run. It does not know C, assembly, ELF, or ARM by itself. You teach it:

1. Which files you want to create.
2. Which input files each output depends on.
3. Which shell command creates the output from the inputs.

With those relationships recorded, `make` can answer: **which outputs need to be rebuilt now?**

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

The difference between `=` and `:=` is easier to see with a changing value. Read what `greet` prints after `name` changes:

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

Our small Makefile uses `:=` where we want the value expanded as Make reads the assignment. Larger projects also use deferred `=` expansion deliberately. When reading one, ask whether the value should be fixed now or resolved when it is used.

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

For `main.o`, the rule substitutes `main.c` for `$<` and `main.o` for `$@`. The same recipe can then build other C objects without repeating the compiler command for each filename. Together with the assembly rule and final link rule, this is enough for our small project.

### 6.7.4  Phony targets

```make
.PHONY: all clean install
```

Tells `make` that `all` / `clean` / `install` are **not** filenames. Without `.PHONY`, a file named `clean` would make `make clean` consider the target up to date and skip the recipe. With `.PHONY`, the recipe always runs.

### 6.7.5  Useful functions

Larger Makefiles often need to derive one filename list from another. These functions use the form `$(name args,...)`. Keep the table as a reading aid; the complete skeleton below does not require learning every function first.

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

`-j` lets Make run several ready recipes at once. That can shorten a large build, but each job also needs memory, so use fewer jobs on a small VM. If a build fails only in parallel, check the dependencies: one recipe may be using a file another has not finished creating.

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

Here the tool selections, flags, and rules finally meet in one file. Follow `all` to `led.bin`, then `led.elf`, then the two objects. The flags explain what environment we are asking the compiler to assume:

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

- **Static linking** includes the selected library code in the executable at link time. It does not need those libraries as `.so` files on the target, but the executable is usually larger.
- **Dynamic linking** leaves references to shared libraries that must be available on the target. The dynamic loader, such as `/lib/ld-linux-armhf.so.3`, resolves them when the process starts.

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

Compare your two files rather than expecting an exact size from the book. A dynamic hello may occupy kilobytes while a glibc static hello occupies hundreds of kilobytes, depending on versions, flags, and symbols. The dynamic executable's smaller size does not include the shared libraries it needs on the target.

Also keep the target environment in view: a statically-linked Linux program still needs Linux. Some library features still use external files or configuration. `-static` does not turn `hello` into firmware that the Boot ROM can start by itself.

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

Now use the tools to answer questions about two actual builds. Lab A compares host and target executables from the same C source. Lab B gives the bare-metal program its own startup, memory layout, and build rules. We inspect the results on the host; board execution comes in Chapter 9.

### Lab A, One source file, two target CPUs

```sh
$ cd ~/imx6ull/src/ch06-hello
$ gcc -g -O2 -o hello-host hello.c
$ arm-none-linux-gnueabihf-gcc -g -O2 -o hello-arm hello.c
$ file hello-host hello-arm
$ readelf -a hello-arm | head -40
$ arm-none-linux-gnueabihf-objdump -d hello-arm | grep -A 5 '<main>:'
```

Run `./hello-host` on the host; it should print `hello`. Inspect, but do not directly execute, `hello-arm` on x86_64. Find the call to `puts` (possibly `puts@plt`) and argument setup in its disassembly. Exact instruction choices vary.

### Lab B, Our first bare-metal build

Create `~/imx6ull/src/ch06-skeleton/` with:

- `startup.S`: the complete listing below.
- `main.c`: the complete listing below.
- `link.ld`: the minimal script from §6.4.
- `Makefile`: from §6.7.

The program below does not operate the LED yet. It increments a variable so we have code and a BSS object to inspect. Saving the four files and running `make` should produce `led.elf` and `led.bin`; Chapter 9 adds the LED operation and ROM wrapper.

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

Read this in three parts. First, `cpsid if` masks IRQ/FIQ and the first `ldr` sets SP to the stack address from our linker script. The next loads obtain the BSS bounds, and `mov` supplies the zero used to clear it.

Second, the loop compares the current address with `_ebss` and clears one word at a time. A numeric label can be reused: `1b` means the previous label `1`, while `2f` means the next label `2`. These suffixes tell the assembler which direction to search.

Finally, `bl main` calls the C function and places a return address in LR. If that function returns, the last branch loops in place. `.ltorg` emits the literal constants needed by the address loads. This listing lets us inspect startup and linking; it is not yet a full exception or ROM-handoff implementation.

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

`counter` gives us a four-byte object in BSS, and `volatile` keeps its accesses present in this exercise. Build once, then run `make` again without changing a file. The second run should have no compilation or linking to do. Edit the loop and build again, watching which commands return.

**Do not try to boot `led.bin` yet.** The code has a linked layout, but the ROM loading header and observable LED behavior are still missing. We add them in Chapter 9.

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

We can now inspect the instructions and addresses produced by a build. One question remains before the chip can run them: how does the Boot ROM know where to load the bytes and where to begin execution? Chapter 7 adds the image header that answers those questions.
