---
chapter: 120
title: User-space debugging (gdbserver, strace, ltrace, perf, coredumpctl)
part: VIII — Debug, production, advanced
estimated_pages: 20
status: draft
---

# Chapter 120 — User-space debugging

> **What:** the toolkit for debugging your **user-space applications** on the i.MX6ULL target from a host workstation. **gdbserver** + **gdb-multiarch** for breakpoint-and-step debugging across the network; **strace** for "what syscalls is this program making"; **ltrace** for shared-library calls; **perf** for sampling profilers + hardware-counter-based analysis + flamegraphs; **core dumps** with `coredumpctl` for post-mortem analysis of crashed processes.
> **Why:** kernel debugging (Ch 118, 119) is the rare case; you'll debug applications 10× more often. The pattern: target runs `gdbserver`; host runs `gdb-multiarch` with the unstripped binary; you set breakpoints by source line, inspect variables, step through code — exactly as if developing locally. `strace` reveals "the open() is returning EACCES" before you've even opened gdb. `perf` answers "why is my video pipeline using 80 % CPU" with a flamegraph. Master these and you debug embedded apps as productively as desktop ones.
> **Focus:** **gdbserver is the network agent (no debugger UI; just exposes the process's debug API over TCP); gdb-multiarch on the host knows ARM and connects; the unstripped ELF + sysroot give it symbols and headers**. For performance: `perf` is the universal sampling tool; understand the difference between sampling (CPU%-style overview, low overhead) and tracing (every event, high overhead). For crashed programs: configure `coredumpctl` to save dumps to a known location, retrieve from the target, analyze on the host.

## 120.1  Target side — install gdbserver

On a Buildroot/Yocto rootfs:

```sh
# Buildroot menuconfig:
#   Target packages → Debugging, profiling and benchmark → gdb → gdbserver

# Or via Debian/Ubuntu on the target
apt install gdbserver
```

`gdbserver` is small (~100 KB statically linked); no debug-info needed on the target.

## 120.2  Host side — gdb-multiarch + sysroot

```sh
apt install gdb-multiarch
```

`gdb-multiarch` is gdb with all architecture support compiled in (ARM, MIPS, RISC-V, ...). For a dedicated cross-debug:

```sh
apt install gdb-arm-none-eabi
# or:
arm-linux-gnueabihf-gdb        # part of the cross-toolchain
```

Tell GDB about your **sysroot** — the target's filesystem layout, so GDB can resolve symbols in shared libraries:

```
(gdb) set sysroot /path/to/target/rootfs
(gdb) set solib-search-path /path/to/target/rootfs/lib:/path/to/target/rootfs/usr/lib
```

## 120.3  Remote debug — gdbserver + gdb-multiarch

```sh
# On target:
gdbserver :2345 /path/to/myapp arg1 arg2
# Process myapp created; pid = 1234
# Listening on port 2345

# On host:
arm-linux-gnueabihf-gdb /path/to/build/myapp     # unstripped binary
(gdb) set sysroot /path/to/target/sysroot
(gdb) target remote 192.168.1.100:2345
(gdb) b main
(gdb) continue
Breakpoint 1, main (argc=3, argv=0x...) at myapp.c:42
42        printf("Hello, world!\n");
(gdb) n
(gdb) p argv[1]
$1 = 0x7fffd344 "arg1"
```

This is the bread-and-butter cross-debug workflow. You write code on your Linux host, cross-compile, copy to target (NFS or scp), gdbserver on target, attach from host. Loop time: 10 seconds.

**Important — `--multi` mode for re-launching**:

```sh
gdbserver --multi :2345
# (gdb) target extended-remote 192.168.1.100:2345
# (gdb) set remote exec-file /path/to/myapp
# (gdb) run arg1 arg2
```

`--multi` keeps gdbserver alive across program runs — no need to restart on every test. Use during heavy iteration.

## 120.4  Attaching to a running process

```sh
gdbserver :2345 --attach <pid>
```

From host:
```
(gdb) target remote 192.168.1.100:2345
(gdb) bt           # see where in code the process is
(gdb) detach        # release without killing
```

Especially useful for hung daemons: attach, `bt`, `print global_state`, identify the deadlock, detach.

## 120.5  strace — the syscall flashlight

```sh
strace ./myapp
execve("./myapp", ["./myapp"], 0x7ffe... /* 14 vars */) = 0
brk(NULL)                            = 0x55c0000
arch_prctl(ARCH_SET_FS, 0x7fff...)   = 0
openat(AT_FDCWD, "/etc/myapp.conf", O_RDONLY) = 3
read(3, "key=value\n", 4096)         = 10
close(3)                             = 0
write(1, "Hello, world!\n", 14)      = 14
exit_group(0)                        = ?
+++ exited with 0 +++
```

Every syscall, its arguments, its return value. Killer for:

- "Why is `open()` failing?" → `strace -e openat ./myapp` shows the failed path + errno.
- "What files does this access?" → `strace -e file ./myapp`.
- "Slow startup?" → `strace -c ./myapp` shows time per syscall.
- "Hanging?" → `strace -p <pid>` shows what syscall it's blocked in.

Options:
- `-f` follow forks (track child processes).
- `-e trace=open,read,write` filter to syscalls of interest.
- `-o file` save to file (don't drown the terminal).
- `-T` show time per call.
- `-t` add timestamp.

For embedded — gdb-multiarch is a host tool; strace runs on the target.

## 120.6  ltrace — same for library calls

`ltrace` shows shared-library function calls (libc, libpthread, libssl, your-libfoo). Less popular than strace but complementary:

```sh
ltrace ./myapp
__libc_start_main(0x401170, 1, 0x7fff..., 0x401200 ...
printf("Hello, %s!\n", "world")              = 14
malloc(64)                                    = 0x55c0080
free(0x55c0080)                               = <void>
+++ exited (status 0) +++
```

Use when "is this calling the right OpenSSL function" matters.

## 120.7  perf — the universal profiler

`perf` is the Linux performance toolkit. Three main modes:

### perf top — htop for CPU functions

```sh
perf top -p <pid>
# Real-time view of which functions are using CPU
#  35.4 %  myapp        compute_hash
#  12.1 %  myapp        memcpy
#   8.2 %  libc.so.6    malloc
```

Updates every second. Press `?` for help; arrow keys to navigate; `Enter` to drill into a function's assembly.

### perf record + perf report — sampling profile

```sh
perf record -F 99 -g ./myapp           # sample at 99 Hz with call graphs
perf report
# Children      Self  Command  Shared Object  Symbol
# +   35.4%    35.4%  myapp    myapp          compute_hash
# +   12.1%    12.1%  myapp    myapp          memcpy
# ...
```

99 Hz sampling = ~1 sample per 10 ms; gives a statistical CPU profile with minimal overhead (~1 %). Perfect for "what is this thing actually doing."

### Flamegraphs

```sh
git clone https://github.com/brendangregg/FlameGraph
perf record -F 99 -g ./myapp
perf script | ./FlameGraph/stackcollapse-perf.pl | ./FlameGraph/flamegraph.pl > out.svg
# Open out.svg in a browser; interactive flame graph
```

The single most useful CPU-profile visualization. X-axis = sample count (~time spent); Y-axis = call stack. Click any block to zoom; type to search. Once you've used flamegraphs, you wonder how anyone debugged performance without them.

### Hardware counters

```sh
perf stat ./myapp
#       12345.67 msec task-clock                #    0.999 CPUs utilized
#                100      context-switches
#         1,234,567      cache-misses             #   12.34 % of all cache refs
#       567,890,123      instructions             #    1.23  insn per cycle
#       456,789,012      cycles
```

Counters tell you why something is slow: high cache-miss rate → memory bound; low instructions-per-cycle → branch misprediction or stall.

For embedded:
- `perf` compiles for ARM cleanly.
- Hardware counters on i.MX6ULL Cortex-A7 are limited to a handful; high-end profiling is easier on Cortex-A53/A72.

## 120.8  Core dumps — post-mortem

When an app crashes:

```sh
# Enable on target
ulimit -c unlimited
echo /var/log/core/core.%e.%p > /proc/sys/kernel/core_pattern

./crashy_app
# Segmentation fault (core dumped)

ls /var/log/core/
# core.crashy_app.1234
```

Or with systemd-coredump:

```sh
# /etc/systemd/coredump.conf
[Coredump]
Storage=external
Compress=yes
ProcessSizeMax=2G
ExternalSizeMax=2G

coredumpctl list                    # see all recent cores
coredumpctl dump 1234 > /tmp/core   # extract one
```

Analyze on the host:

```sh
arm-linux-gnueabihf-gdb crashy_app /tmp/core
(gdb) bt
#0  0x000115a4 in crash_function () at crashy.c:42
#1  0x00011620 in main () at crashy.c:10
(gdb) p some_variable
(gdb) f 1
(gdb) info locals
```

You get the dying process's stack + register + memory state, debuggable as if it was alive.

## 120.9  Real-world workflow — debugging a hung app

Symptom: customer reports `myapp` "freezes" after ~1 hour.

```sh
# 1. Find the PID
ps aux | grep myapp
# user  1234  ...

# 2. Is it blocked on a syscall?
cat /proc/1234/wchan
# poll_schedule_timeout              # yep, in poll()
strace -p 1234
# poll([{fd=3, events=POLLIN}], 1, -1)    # blocked waiting for fd 3 forever
ls -la /proc/1234/fd/3
# lrwx... -> socket:[12345678]

# 3. What socket? netstat shows
ss -anp | grep 12345678
# tcp ... 192.168.1.100:5555  ESTAB  pid=1234,fd=3

# 4. Other end stopped responding? confirm via tcpdump
tcpdump -ni eth0 host 192.168.1.100

# 5. Get a backtrace to see WHERE in code it's waiting
gdbserver :2345 --attach 1234
# (on host)
(gdb) target remote ...
(gdb) bt
#0  0x... in poll () from /lib/libc.so.6
#1  0x... in wait_for_response () at myapp.c:127
#2  0x... in main_loop () at myapp.c:200
```

Now you know: line 127 calls poll() on a socket that's hung. Fix: add a timeout, handle disconnect, reconnect.

## 120.10  Lab

1. **gdbserver hello world.** Build a 10-line C program with `-g`. Run via gdbserver; attach gdb-multiarch from host; step through; print variables.
2. **Set sysroot properly.** Try to print a `pthread_mutex_t` from gdb without sysroot; observe missing libpthread symbols. Set sysroot; observe symbols appear.
3. **strace.** Run `cat /etc/passwd` under strace; identify every syscall. Now run `ls`; compare syscall patterns.
4. **strace -c.** Run a typical workload; identify the most-frequent and slowest syscall.
5. **perf top.** Run `dd if=/dev/zero of=/tmp/x bs=1M count=100` while `perf top` is running. See which kernel functions dominate.
6. **Flamegraph of your app.** Sample your app; produce an SVG. Identify the hot path.
7. **Hardware counter profile.** `perf stat -e cache-misses,instructions,cycles ./myapp`; compute CPI (cycles per instruction). >2 = memory-bound; <1.5 = compute-bound.
8. **Crash + core.** Write a program that intentionally dereferences NULL; capture the core; analyze with gdb on host. Identify the line.
9. **Attach to systemd service.** Find a running daemon's PID; attach gdbserver; bt; identify what it's doing.
10. **End-to-end customer-bug workflow.** Pick a "stuck" daemon (httpd, sshd); use cat /proc/<pid>/wchan + strace -p + gdb-attach; produce a one-page bug report.

## 120.11  Pitfalls

- **gdbserver and gdb-multiarch ABI mismatch.** Cross-compiler ARM ABI must match target's libc ABI (gnueabihf vs gnueabi). Different ABI = unable to set breakpoints in shared libraries.
- **Sysroot pointing to wrong path.** gdb finds libc.so.6 in /lib (host) instead of the cross-built one; symbols mismatch. Always `set sysroot` before `target remote`.
- **Stripped binaries.** No symbols, no source-level debug. Build with `-g`; copy unstripped to host; ship stripped to target.
- **PIE binaries with ASLR.** Address space randomization makes addresses different each run. GDB handles it; manual address arithmetic doesn't. Disable ASLR for repeatable debug: `setarch -R ./myapp`.
- **strace heavy slowdown.** Tracing a high-syscall-rate process can 10× slow it. Use `-e trace=read,write` to filter.
- **strace doesn't show shared library calls.** Use ltrace or gdb for that.
- **perf record -g with no CFI.** Without `-fno-omit-frame-pointer` in the build, perf can't unwind stacks. Compile with both `-g` and `-fno-omit-frame-pointer`.
- **perf hardware events unavailable.** Some VMs / containers / 32-bit ARM can't access perf counters. Falls back to software events only.
- **core dump truncated.** Default `ulimit -c` is often 0 (disabled). Set `ulimit -c unlimited`. Also kernel.core_pattern must allow writing somewhere.
- **systemd-coredump compresses cores.** `coredumpctl dump` decompresses; `xz -d` if you pulled directly.
- **gdb attach permission denied.** Need CAP_SYS_PTRACE (root) on target, or run as the same user as the target process. /proc/sys/kernel/yama/ptrace_scope = 0 to allow ptrace of any process; 1 is "only descendants" (default on many distros).
- **Detaching gdbserver leaves the process running.** Use `(gdb) detach` then exit. `(gdb) quit` without detaching kills the process — usually NOT what you want.

## 120.12  Going deeper

- **GDB manual** (https://sourceware.org/gdb/onlinedocs/) — chapters on remote debugging.
- **`strace(1)`, `ltrace(1)`** — man pages.
- **Brendan Gregg's `perf` tutorial** — http://brendangregg.com/perf.html.
- **`Documentation/admin-guide/perf-security.rst`** — for kernel.perf_event_paranoid.
- **`Flame Graph` repo + paper** — http://brendangregg.com/flamegraphs.html.
- **`coredumpctl(1)`, `systemd-coredump.conf(5)`**.
- **Valgrind** (memcheck, callgrind) — slower but more detailed; runs on the target if you have enough RAM.
- **AddressSanitizer (ASan), UndefinedBehaviorSanitizer (UBSan)** — compile-time instrumentation; catches memory bugs at runtime.
- **Ch 125A** — VSCode + gdbserver workflow for IDE users.

---

> Next chapter: **Chapter 120A — Mainline patch submission workflow** (inserted v1.2).
