---
chapter: 125A
title: VSCode + gdbserver remote-debug workflow
part: VIII — Debug, production, advanced
estimated_pages: 12
status: draft
---

# Chapter 125A — VSCode + gdbserver remote-debug workflow

> **What:** the **IDE-driven cross-debug workflow** for engineers who prefer Visual Studio Code over the gdb command line. **`gdbserver`** on the target; **`gdb-multiarch`** on the host; VSCode's C/C++ extension and `launch.json` tying them together; `.vscode/c_cpp_properties.json` resolving headers from the cross-sysroot so "Go to Definition" works on both your app *and* kernel sources. Plus a short note on Source Insight, an old commercial editor that's still the fastest tool for read-only kernel-source navigation.
> **Why:** many readers come from microcontroller backgrounds where the IDE *is* the debugger (Keil, IAR, STM32CubeIDE). Forcing them to learn gdb's tui mode just to set a breakpoint is unnecessary. VSCode plus the right config gives the same click-to-set-breakpoint experience cross-debugging a remote ARM target, while leaving the underlying gdb fully scriptable for when you do want the command line. Setting up `launch.json` once pays back every debug session after.
> **Focus:** VSCode's debug UI is a wrapper around gdb. `launch.json` configures it. You set: which gdb binary, which binary to debug, where gdbserver listens, and where the source tree lives. The non-obvious part is `c_cpp_properties.json`. It must point IntelliSense at the target's sysroot headers, not the host's. Otherwise "Go to Definition" finds your laptop's `stdio.h`, not the cross-compiled one. With both files right, IDE-style debug and accurate Go-to-Definition make embedded debug feel close to desktop.

## 125A.1  Target side — install gdbserver

```sh
# Yocto / Buildroot: enable gdbserver in image
# OR Debian/Ubuntu on the target:
apt install gdbserver

# Static-linked is preferable so it works even with weird libc situations
```

`gdbserver` is small — about 100 KB statically linked — and needs no debug info on the target.

## 125A.2  Host side — VSCode + extensions

```sh
# Install VSCode (Microsoft .deb or your distro's package)
# Install extensions:
#   C/C++ (ms-vscode.cpptools)
#   C/C++ Themes (optional)
#   Native Debug (webfreak.debug) — alternative; sometimes friendlier for cross
```

And the cross-debugger:

```sh
apt install gdb-multiarch
# or:
apt install gcc-arm-linux-gnueabihf  # includes gdb in some distros
```

## 125A.3  The two config files

VSCode reads two project-local files from `.vscode/`:

- **`launch.json`** — debug-time configuration (which gdb, which binary, where to connect).
- **`c_cpp_properties.json`** — IntelliSense / Go-to-Definition (which headers, which compiler).

### `.vscode/launch.json`

```json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Cross-debug myapp on imx6ull-pa",
            "type": "cppdbg",
            "request": "launch",
            "program": "${workspaceFolder}/build/myapp",
            "miDebuggerPath": "/usr/bin/gdb-multiarch",
            "miDebuggerServerAddress": "192.168.1.100:2345",
            "cwd": "${workspaceFolder}",
            "args": [],
            "stopAtEntry": true,
            "setupCommands": [
                {
                    "description": "Use sysroot",
                    "text": "set sysroot /home/dev/yocto/build/tmp/work/imx6ull-myboard-poky-linux-gnueabi/myapp/1.0-r0/recipe-sysroot",
                    "ignoreFailures": false
                },
                {
                    "description": "Enable pretty-printing",
                    "text": "-enable-pretty-printing",
                    "ignoreFailures": true
                }
            ],
            "preLaunchTask": "Start gdbserver"
        }
    ]
}
```

Key fields:
- **`program`**: the unstripped ELF on the host. Symbols come from here.
- **`miDebuggerPath`**: cross-gdb. Must understand ARM.
- **`miDebuggerServerAddress`**: where gdbserver listens on the target.
- **`setupCommands`**: extra gdb commands at start (`set sysroot`, `set solib-search-path`, ...).
- **`preLaunchTask`** (optional): a VSCode task that starts gdbserver on the target. See below.

### `.vscode/tasks.json` — pre-launch gdbserver

```json
{
    "version": "2.0.0",
    "tasks": [
        {
            "label": "Start gdbserver",
            "type": "shell",
            "command": "ssh root@192.168.1.100 'gdbserver --multi :2345 &'",
            "isBackground": true,
            "problemMatcher": []
        }
    ]
}
```

VSCode runs this task before launching debug; gdbserver is up; the debug session connects immediately.

### `.vscode/c_cpp_properties.json`

```json
{
    "configurations": [
        {
            "name": "i.MX6ULL Cross-compile",
            "includePath": [
                "${workspaceFolder}/**",
                "/home/dev/yocto/build/tmp/work/imx6ull-myboard-poky-linux-gnueabi/myapp/1.0-r0/recipe-sysroot/usr/include",
                "/home/dev/yocto/build/tmp/work/imx6ull-myboard-poky-linux-gnueabi/myapp/1.0-r0/recipe-sysroot/usr/include/c++/12"
            ],
            "defines": [],
            "compilerPath": "/home/dev/x-tools/arm-linux-gnueabihf/bin/arm-linux-gnueabihf-gcc",
            "cStandard": "c17",
            "cppStandard": "c++17",
            "intelliSenseMode": "linux-gcc-arm"
        }
    ],
    "version": 4
}
```

With this, hover-over-symbol and "Go to Definition" find the target's headers, not your host's. Without this, IntelliSense reports errors that aren't real: it thinks you're compiling for x86, so ARM-only macros are undefined and code inside `#ifdef __arm__` looks dead.

## 125A.4  Debugging workflow

1. **Build** on host: `cd build && cmake --build .` (or your build system).
2. **Copy binary** to target: `scp build/myapp root@target:/usr/bin/` (or NFS rootfs auto-syncs).
3. **F5 in VSCode**: pre-launch task starts gdbserver; gdb connects; binary loads; stops at entry (or your `main()`).
4. **Set breakpoints** by clicking in the gutter of source files.
5. **Continue/step/inspect** via the debug toolbar.
6. **Watch / Locals / Call Stack** panels show variables and stack.
7. **Debug Console** for arbitrary gdb commands (`-exec print foo`).

When done: VSCode disconnects; gdbserver stops (or stays running if `--multi`).

## 125A.5  Multi-target — connect to multiple boards

For a fleet:

```json
"configurations": [
    { "name": "Debug on board A", "miDebuggerServerAddress": "192.168.1.100:2345", ... },
    { "name": "Debug on board B", "miDebuggerServerAddress": "192.168.1.101:2345", ... },
    { "name": "Debug on board C", "miDebuggerServerAddress": "192.168.1.102:2345", ... }
]
```

Pick the right config from VSCode's debug dropdown.

## 125A.6  Debugging kernel modules (advanced)

Set a breakpoint in your Chapter 36/41 LED driver's `probe()`:

```json
{
    "name": "Debug LED kernel module",
    "type": "cppdbg",
    "request": "launch",
    "program": "${workspaceFolder}/path/to/linux/vmlinux",
    "miDebuggerPath": "/usr/bin/gdb-multiarch",
    "miDebuggerServerAddress": "192.168.1.100:1234",
    "setupCommands": [
        { "text": "set arch arm" },
        { "text": "set sysroot /home/dev/sysroot" },
        { "text": "add-auto-load-safe-path /home/dev/yocto/build/tmp/work/.../linux/scripts/gdb/" },
        { "text": "source /home/dev/yocto/build/tmp/work/.../linux/scripts/gdb/vmlinux-gdb.py" }
    ]
}
```

The kernel-side gdb stub is **KGDB over UART** (Ch 119) on port 1234. After connect:

```
> -exec lx-symbols   # load module symbol files
> break led_probe    # the breakpoint
> continue
# Now insmod the module on the target — breakpoint hits in VSCode.
```

## 125A.7  Source Insight — the read-only navigator

Source Insight is a 25-year-old commercial editor (Windows; runs in Wine on Linux). For navigating *huge* code bases (Linux source is ~30 M lines) it's still fastest:
- 5 s to index Linux kernel.
- Hover any symbol → instant definition + cross-references.
- Call graph generation.

It's not a debugger; not an editor for serious projects. But for "I'm reading the kernel source and want to navigate quickly," nothing beats it. License: $239 one-time.

VSCode's IntelliSense on the kernel source works but is slower (~5 minutes to index). For active editing: VSCode. For pure reading: Source Insight.

## 125A.8  Lab

1. **Install gdbserver target / gdb-multiarch host.** Verify versions match major ARM target.
2. **Hello-world C app cross-compile.** With `-g` flag. Copy to target.
3. **Manual gdbserver test.** `gdbserver :2345 ./hello` on target; `gdb-multiarch ./hello` + `target remote target-ip:2345` on host. Step, print. Confirm it works before introducing VSCode.
4. **VSCode launch.json.** Set up the config. F5. Confirm debug session connects.
5. **Set breakpoint.** Click in gutter at a source line. Continue. Verify breakpoint hits and you can inspect locals.
6. **Set sysroot properly.** Try without (note libc symbol errors); then set; observe they resolve.
7. **c_cpp_properties.json.** Configure to point at target sysroot. Verify hover-over-symbol finds the target's libc, not your host's.
8. **Multi-target.** Add 2 board configs; switch between them via dropdown.
9. **Debug a real driver in your app** that wraps Ch 105 (RFID) or Ch 117 (RTC). Set breakpoint on init; trace through.
10. **Source Insight evaluation (stretch).** Try the 30-day trial; index your kernel; compare navigation speed to VSCode.

## 125A.9  Pitfalls

- **Wrong gdb binary.** `/usr/bin/gdb` (host) won't debug ARM; needs `gdb-multiarch` or the cross-toolchain gdb.
- **Sysroot path stale.** Yocto recreates `recipe-sysroot` paths each build; the hardcoded path in `launch.json` drifts. Use `${workspaceFolder}` + relative paths or update on rebuild.
- **gdbserver not actually started.** preLaunchTask SSH command fails silently; debug session times out. Verify with manual SSH first.
- **IntelliSense crashes parsing kernel source.** 30M lines exceeds VSCode's default RAM. Increase: `"C_Cpp.intelliSenseEngine": "default"`, plus 8+ GB RAM.
- **Source paths don't match.** Binary built in `/build/...` but you opened the project in `/src/...`. GDB can't find source files. Add `substitute-path` to setupCommands.
- **Stripped binary on target.** gdbserver opens it but no symbols. Always use unstripped on host side; target-side `strip` is fine.
- **Breakpoints don't hit.** Often: target's libc not matching host's compile-time libc; symbols mismatch; libc functions step into stripped code. Set sysroot.
- **Slow over remote SSH.** gdbserver+ssh tunnel adds ~50 ms per breakpoint. Use direct TCP (open the port in firewall) if you control the network.
- **"Cannot find ld-linux-armhf.so.3".** sysroot wrong. Verify it points to `${YOCTO_BUILD}/.../recipe-sysroot/`, not the host's `/`.
- **VSCode's debug console is one-liner.** Multi-line gdb commands (define, document) need to go in a separate script file loaded via `source` from setupCommands.
- **Pre-launch task hangs.** If `gdbserver --multi :2345 &` doesn't background properly, VSCode waits forever. Use `isBackground: true` and a `problemMatcher` that VSCode treats as "this is OK to keep running."

## 125A.10  Going deeper

- **VSCode C/C++ extension documentation** — https://code.visualstudio.com/docs/cpp/cpp-debug.
- **`launch.json` reference** — all options.
- **GDB manual chapters on MI (Machine Interface)** — what VSCode uses to talk to gdb.
- **`gdb-dashboard`** — terminal alternative if you decide to leave VSCode.
- **`gef` and `pwndbg`** — gdb plugins for security research, with VSCode-like features in terminal.
- **CLion** + remote toolchain — JetBrains commercial alternative; even smoother UX, paid.
- **Ch 118** — JTAG with gdb (same gdb, different remote target).
- **Ch 120** — gdbserver + cli gdb (same workflow, manual setup).
- **Ch 119** — KGDB for kernel-side debug.

---

> Next chapter: **Chapter 126 — Closing: what to read next**. End of the book.
