---
chapter: 34
title: libc, dynamic linking, and the loader
part: V - Root filesystem & user space
estimated_pages: 16
status: draft
---

# Chapter 34: libc, dynamic linking, and the loader

> **What:** the C library that user-space programs link against (glibc, musl, uClibc-ng), the ELF dynamic-linker that resolves shared-library references at runtime (`/lib/ld-linux-armhf.so.3`), and the bookkeeping (PLT, GOT, `LD_LIBRARY_PATH`, `RPATH`) that makes `hello-world` actually find `printf`.
> **ELF:** Executable and Linkable Format, the standard Linux object and executable file format.
>
> **Why:** every dynamically-linked program on the target depends on this machinery. When it works it's invisible. When it breaks you get `No such file or directory` on a file that does exist. Knowing what the loader does demystifies these failures.
>
> **Focus:** **ld-linux's job.** When the kernel `exec`s a dynamically-linked program, the first thing that runs is *not* `main()`, it's the dynamic linker, which loads every required shared library, fixes up addresses, and only *then* jumps to your code. Once you've traced this sequence you can debug most `libfoo.so.X: cannot open shared object file` problems.


## 34.1  Three C libraries

Embedded Linux lets you pick the C library. On a desktop you get glibc and nothing else.

| | glibc | musl | uClibc-ng |
|---|---|---|---|
| Origin | GNU project, ~1988 | Rich Felker, ~2011 | Fork of uClibc, 2014 |
| License | LGPL-2.1 | MIT | LGPL-2.1 |
| Static linking | discouraged (NSS won't work) | first-class | first-class |
| Static-linked "hello world" | ~700 KB | ~30 KB | ~50 KB |
| Dynamic-linked "hello world" | 8 KB + ~2 MB libs | 8 KB + 600 KB libs | 8 KB + 700 KB libs |
| Feature completeness | most complete | very complete (POSIX, most GNU exts) | complete enough for embedded |
| Performance | optimized aggressively | conservative, predictable | adequate |
| Used in mainstream | Debian, Ubuntu, Fedora | Alpine, Void | OpenWrt, Buildroot |

For embedded Linux **musl is the default**. Reasons:

- One sixth the size of glibc for the same program.
- Static linking actually works (no NSS / dlopen surprises).
- Tighter, more predictable behavior (no surprise heuristics).
- MIT-licensed (LGPL is fine for most people but not all).

glibc remains right for: anything that ships large dynamic apps (Qt, Python, Java), or any rootfs that's a distro derivative (Ubuntu-base / Debian).
> **MCU bridge:** Think of the rootfs as the firmware image's file-backed runtime environment. On an MCU you link everything into flash. On Linux, programs and config live in this mounted tree.
> **rootfs:** root filesystem, the directory tree mounted at / that contains /bin, /etc, /dev, and libraries.

## 34.2  Anatomy of a dynamically-linked ELF

Compile a trivial program against glibc:

```sh
$ cat > hello.c <<'EOF'
#include <stdio.h>
int main(void) { puts("hello"); return 0; }
EOF
$ arm-none-linux-gnueabihf-gcc -o hello hello.c
$ file hello
hello: ELF 32-bit LSB executable, ARM, EABI5 version 1 (SYSV),
       dynamically linked, interpreter /lib/ld-linux-armhf.so.3, ...
```

Two things to notice from `file`:

- **dynamically linked**: references shared libraries that aren't part of the binary.
- **interpreter /lib/ld-linux-armhf.so.3**: when the kernel `exec`s this binary, it actually runs the *interpreter* first, passing the binary as an argument.

That second point is the heart of dynamic linking and worth understanding precisely.

### The ELF program headers

```sh
$ arm-none-linux-gnueabihf-readelf -l hello | head -25

Elf file type is DYN (Position-Independent Executable file)
Entry point 0x4c0
There are 9 program headers, starting at offset 52

Program Headers:
  Type           Offset   VirtAddr   PhysAddr   FileSiz MemSiz   Flg Align
  PHDR           0x000034 0x00000034 0x00000034 0x00120 0x00120  R   0x4
  INTERP         0x000154 0x00000154 0x00000154 0x00019 0x00019  R   0x1
      [Requesting program interpreter: /lib/ld-linux-armhf.so.3]
  LOAD           0x000000 0x00000000 0x00000000 0x004f4 0x004f4  R   0x10000
  LOAD           0x000ed4 0x00010ed4 0x00010ed4 0x0011c 0x0011c  RW  0x10000
  DYNAMIC        0x000eec 0x00010eec 0x00010eec 0x000d0 0x000d0  RW  0x4
  ...
```

The **INTERP** segment is a single string: `/lib/ld-linux-armhf.so.3`. The kernel reads this string out of the ELF, opens that file, and `exec`s *it*, passing your `hello` as a regular argument to the linker. The dynamic linker is the *real* program PID-wise. Your `hello` is its workload.

### What the linker does

`ld-linux-armhf.so.3` runs and:

1. **Reads `hello`'s DYNAMIC segment.** This contains a table of needed libraries:
   ```sh
   $ arm-none-linux-gnueabihf-readelf -d hello | head
    0x00000001 (NEEDED) Shared library: [libc.so.6]
    0x0000001d (RUNPATH) Library runpath: [/path/to/runtime/libs]   (if set)
    ...
   ```
2. **Resolves each NEEDED library.** Search order:
   - `LD_LIBRARY_PATH` environment variable (colon-separated)
   - `RPATH` / `RUNPATH` from the ELF
   - `/etc/ld.so.cache` (built by `ldconfig`)
   - `/lib`, `/usr/lib` (default fallback)
3. **`mmap`s each `.so` into memory** at addresses chosen for that process (ASLR shuffles them if enabled).
4. **Repeats recursively**: Libc may need other libraries (pthread, ld, …).
5. **Performs symbol resolution.** For every undefined symbol in `hello` and the loaded libraries, find the defining library. Rewrite the address tables (PLT / GOT) so that calls go to the right place.
6. **Calls the program's entry point** (`_start`, which eventually calls `main`).

All of that happens before your `main()` runs. On embedded i.MX6ULL hardware, dynamic linking adds ~5-50 ms to startup depending on how many libraries are pulled in.

## 34.3  PLT and GOT

The PLT and GOT are the two tables that make dynamic linking efficient.

### GOT, Global Offset Table

The GOT holds runtime addresses of every external symbol the program references. The compiler emits `LOAD r0, [GOT+offset]` instead of a fixed address.

```sh
$ arm-none-linux-gnueabihf-readelf -r hello

Relocation section '.rel.dyn' at offset 0x444 contains 4 entries:
 Offset     Info    Type            Sym.Value  Sym. Name
00010eec  00000017 R_ARM_RELATIVE
00010ef0  00000017 R_ARM_RELATIVE
00010ff0  00000115 R_ARM_GLOB_DAT    00000000   __libc_start_main@GLIBC_2.34
00010ff4  00000215 R_ARM_GLOB_DAT    00000000   __cxa_finalize@GLIBC_2.4

Relocation section '.rel.plt' at offset 0x464 contains 1 entry:
 Offset     Info    Type            Sym.Value  Sym. Name
00011000  00000316 R_ARM_JUMP_SLOT   00000000   puts@GLIBC_2.4
```

`R_ARM_GLOB_DAT` entries are data-section relocations. The loader writes the resolved address of `__libc_start_main` into the GOT slot at `0x10ff0`.

### PLT, Procedure Linkage Table

The PLT is a tiny stub per function that jumps via the GOT. The first time you call `puts()`:

```
puts@plt:
    ldr  r12, [pc, #plt_offset_to_GOT_entry]
    bx   r12              @ → resolved address of puts, or to the resolver stub
```

The first time, the GOT slot still points at a "resolver" routine inside ld-linux. The resolver looks up `puts` for real, writes the real address into the GOT slot, and jumps there. **Subsequent calls** go directly via the GOT, fast.

This trick is called **lazy binding**. The dynamic linker doesn't resolve every function at startup. It resolves them on first use. You can disable lazy binding with `LD_BIND_NOW=1`, useful for security-hardened systems (no resolver stub at runtime).

## 34.4  Where libraries actually come from

On the target:

```
[root@pa-mini:~]# ls /lib/
ld-2.31.so              libnss_files.so.2
ld-linux-armhf.so.3     libnss_files-2.31.so
libc-2.31.so            libpthread-2.31.so
libc.so.6               libpthread.so.0
libdl-2.31.so           libresolv-2.31.so
libdl.so.2              libresolv.so.2
libm-2.31.so            librt-2.31.so
libm.so.6               librt.so.1
```

Notice:

- `libc.so.6` is a *symlink* to `libc-2.31.so`. The "6" is the ABI version. "2.31" is the implementation version.
> **ABI:** Application Binary Interface: the calling convention, register use, binary format, and library contract that let separately built code run together.
- `ld-linux-armhf.so.3` is the dynamic linker, a *real file*, not a symlink. (See Ch 31 §31.10's gotcha.)
- The `nss_files` library is for Name Service Switch, loaded dynamically by glibc when you call `gethostbyname`, `getpwuid`, etc. This is the part that breaks under static linking.

The dynamic linker also consults `/etc/ld.so.cache`, a pre-indexed map of `library-name → file-path`:

```sh
$ ldconfig -p | head
21 libs found in cache `/etc/ld.so.cache'
   libz.so.1 (libc6,hard-float) => /lib/libz.so.1
   libuClibc-1.0.so (libc6) => /lib/libuClibc-1.0.so
   ...
```

`ldconfig` rebuilds this cache from `/etc/ld.so.conf` and `/etc/ld.so.conf.d/*.conf`. On embedded systems running BusyBox, `ldconfig` is often skipped, the search defaults (`/lib`, `/usr/lib`) cover everything.

## 34.5  Looking inside a real program

`ldd` shows what a binary depends on:

```sh
[root@pa-mini:~]# ldd /bin/busybox
        not a dynamic executable
```

(Static, no dependencies.) But:

```sh
[root@pa-mini:~]# ldd /usr/bin/some-dynamic-binary
        libpthread.so.0 => /lib/libpthread.so.0 (0xb6f00000)
        libm.so.6 => /lib/libm.so.6 (0xb6e80000)
        libc.so.6 => /lib/libc.so.6 (0xb6d80000)
        /lib/ld-linux-armhf.so.3 (0xb6f80000)
```

Right column is *load addresses*, where each `.so` was `mmap`'d into the process's address space.

For a deeper look:

```sh
[root@pa-mini:~]# LD_DEBUG=libs my-binary 2>&1 | head -20
      6: find library=libpthread.so.0 [0]; searching
      6:  search cache=/etc/ld.so.cache
      6:   trying file=/lib/libpthread.so.0
      6:
      6: find library=libc.so.6 [0]; searching
      6:  search cache=/etc/ld.so.cache
      6:   trying file=/lib/libc.so.6
      6:
      6: calling init: /lib/libpthread.so.0
      6: calling init: /lib/libc.so.6
      6: initialize program: my-binary
      6: transferring control: my-binary
```

`LD_DEBUG=libs` (`LD_DEBUG=help` for the full list of categories) is the diagnostic tool for "why isn't this library being found?" Use `LD_DEBUG=libs` before guessing.

## 34.6  RPATH and friends

Sometimes you ship a binary that depends on libraries *not* in `/lib`. Three common ways to point the loader at them:

### `LD_LIBRARY_PATH`

```sh
[root@pa-mini:~]# LD_LIBRARY_PATH=/opt/myapp/lib /opt/myapp/bin/my-binary
```

Most general. User can override per-invocation. Downside: easy to forget. Security-sensitive binaries (setuid) ignore it for safety.

### `RPATH` baked into the binary

```sh
$ arm-none-linux-gnueabihf-gcc -Wl,-rpath,/opt/myapp/lib -o my-binary my.c
```

The binary now searches `/opt/myapp/lib/` automatically. Visible in `readelf -d` as a `RUNPATH` entry. Best for self-contained apps that bundle their own libs.

`$ORIGIN` is a special token that expands to the binary's own directory:

```sh
$ arm-none-linux-gnueabihf-gcc -Wl,-rpath,'$ORIGIN/../lib' -o my-binary my.c
```

Binary in `/opt/myapp/bin/` searches `/opt/myapp/lib/`, regardless of where the package is installed.

### `/etc/ld.so.conf.d/myapp.conf`

```sh
$ echo /opt/myapp/lib > /etc/ld.so.conf.d/myapp.conf
$ ldconfig
```

System-wide. Affects all binaries. Use sparingly.

## 34.7  Static vs dynamic for embedded, the real trade-off

| | Static | Dynamic |
|---|---|---|
| Binary size | Big (KB to MB per program) | Small (KB) |
| RAM per process | High (no library sharing) | Low (shared mmaps) |
| Disk for whole image | Variable; if you have 1 binary, smaller. 10 binaries: larger. | One copy of each lib regardless of binary count |
| Update granularity | Replace binary | Replace library; binaries pick it up |
| `dlopen()` works | No (in practice for glibc) | Yes |
| DNS / NSS works | No (glibc) / Yes (musl) | Yes |
| Boot time | Slightly faster (no linker startup) | Slightly slower |

For embedded with **N small binaries**, dynamic linking is almost always smaller in total. For embedded with **1 large binary**, static can win.

`busybox`, our biggest single binary, is the canonical case for static: 580 KB static vs ~580 KB binary + ~2 MB glibc dynamic. Choosing static for busybox saves 2 MB. Choosing dynamic means dozens of other small dynamic binaries can also be on the system without adding more libc copies.

The decision is per-binary, not per-system. Mix as needed.

## 34.8  Lab

1. **Inspect a binary's dependencies.** `arm-none-linux-gnueabihf-readelf -d /bin/my-binary` from the host (or from the target after copying). Note each NEEDED entry. Verify each exists in `/lib/` or `/usr/lib/`.
2. **`ldd` on the target.** Run `ldd /usr/bin/...` on something dynamic and read each line. Identify the dynamic linker. Verify it matches the INTERP from `readelf`.
3. **Break a dynamic binary on purpose.** Move `/lib/libm.so.6` somewhere. Try to run a math-dependent binary. Observe the "cannot open shared object file" error. Restore.
4. **Trace library loading.** `LD_DEBUG=libs LD_DEBUG_OUTPUT=/tmp/ldlog my-binary. cat /tmp/ldlog`. Identify every library load.
5. **Build the same program against musl.** If you have a musl-targeting cross toolchain, build `hello.c` against musl and against glibc. Compare sizes statically: `arm-linux-musleabihf-gcc -static -o hello-musl hello.c` versus `arm-none-linux-gnueabihf-gcc -static -o hello-glibc hello.c`.
6. **Set up `$ORIGIN` rpath.** Build a binary with `-Wl,-rpath,'$ORIGIN/../lib'`, place it under `/opt/myapp/bin/`, place a custom `.so` under `/opt/myapp/lib/`, verify the binary finds it without `LD_LIBRARY_PATH`.

## 34.9  Pitfalls

- **`libfoo.so.X: cannot open shared object file`**: the dynamic linker can't find a NEEDED library. Diagnose with `LD_DEBUG=libs`. Fix by copying the library into `/lib` or adding to `LD_LIBRARY_PATH` / `RPATH`.
- **`relocation error: undefined symbol`**: the library was found but doesn't have a symbol the binary needs. Usually means library *version* mismatch. The binary was built against newer libc. The runtime has older.
- **Mixed glibc and musl on one rootfs.** Mixing glibc and musl on one rootfs is possible but easy to get wrong. Glibc uses SONAME `libc.so.6` and loader `/lib/ld-linux-armhf.so.3`. Musl uses its own loader `/lib/ld-musl-armhf.so.1` and its own libc. They can live in separate prefixes. The failure mode is when both want to own the same `/lib/libc.so.6` symlink. Pick one libc per rootfs, or put musl binaries under their own prefix with the loader path baked in via `RPATH`.
- **Static glibc + getaddrinfo.** Returns "Temporary failure in name resolution" with no obvious cause. NSS modules are dlopen'd at runtime even for "static" binaries. If the .so files aren't on disk you lose DNS. Either ship the NSS .so files alongside your "static" binary or switch to musl.
- **`LD_LIBRARY_PATH` and setuid binaries.** Ignored for setuid binaries (security). Don't rely on it for system binaries.
- **`ldconfig` not run after copying libraries.** Some glibc setups won't find a library until you `ldconfig`. Symptom: works after `ldconfig`, breaks on fresh boot. Fix: run `ldconfig` from `rcS` or include the library path in `/etc/ld.so.conf.d/`.
- **`$ORIGIN` rpath doesn't work in shell scripts.** It's resolved by the *dynamic linker*, not the shell. Only matters for the ELF binary itself. If you invoke the binary via a wrapper script, `$ORIGIN` is relative to the wrapper's location only if the wrapper itself is dynamic.

## 34.10  Going deeper

- **`man ld.so`**: the canonical loader reference.
- **`man ldd`**, **`man ldconfig`**, **`man dlopen`**.
- **`Documentation/admin-guide/dynamic-debug-howto.rst`** for kernel-side dlopen-like patterns.
- **`Drepper, "How to Write Shared Libraries"`**: long PDF, gold standard.
- **musl's website**, `musl.libc.org`, design rationale, comparison tables.
- **`The ELF Specification`** (System V ABI, ARM supplement) for the gritty details of dynamic sections.

> Next chapter: **Chapter 35: Buildroot, after you can do it by hand.** With BusyBox + libc + init understood, we adopt the tool that automates all of it.
> **Buildroot:** a configuration-driven build system that produces a complete root filesystem and related images.
