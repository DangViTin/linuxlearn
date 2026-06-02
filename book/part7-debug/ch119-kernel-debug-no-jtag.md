---
chapter: 119
title: Kernel debugging without JTAG (ftrace, eBPF, kgdb, oops)
part: VIII — Debug, production, advanced
estimated_pages: 26
status: draft
---

# Chapter 119 — Kernel debugging without JTAG

> **What:** the **software-only kernel debugging toolkit** that works on a deployed device with no hardware debug access. **printk**'s deeper toolbox (`pr_debug`, `dynamic_debug`, ring-buffer levels), **ftrace** (function tracer + `function_graph` + tracepoint events), **trace-cmd** + **KernelShark** (record + GUI), **bpftrace** and **bcc** (eBPF for live kernel introspection), **kgdb** over serial (when you do want a debugger but only have UART), and the **oops decoder** workflow (`addr2line`, `scripts/decode_stacktrace.sh`).
>
> **Why:** JTAG is for bench work. This chapter covers what you can run on a deployed device with no debug header. You can't ship a fleet with a JTAG cable attached; you can ship a fleet with ftrace enabled. If a customer's device hangs once every three days, you need to know what the kernel was doing in the second before the freeze. ftrace's persistent buffer plus the oops decoder answers that. eBPF lets you attach a probe to `tcp_retransmit_skb` on a production server and count retransmits per remote address, without recompiling the kernel.
>
> **Focus:** match the tool to the symptom. Too much output in `dmesg`: use `dynamic_debug` to filter. "It worked once, now hangs": ftrace `function_graph` on the suspect subsystem. "What system calls is this app making?": a bpftrace one-liner. "Kernel oops on customer device": save dmesg and run decode_stacktrace.sh against the matching vmlinux. "I want to breakpoint and step a remote production kernel": kgdb over serial (rare, but sometimes the right call).
>
> **Tooling.** **Target:** `trace-cmd` (for ftrace), optional `bpfcc-tools` / `bpftrace` (eBPF — better on aarch64 / newer kernels). **Host:** `kernelshark` to visualise ftrace dumps; `crash(8)` for vmcore analysis. Ubuntu install: `apt install trace-cmd kernelshark bpfcc-tools bpftrace`. Buildroot: `BR2_PACKAGE_TRACE_CMD=y`, `BR2_PACKAGE_BCC=y`, `BR2_PACKAGE_BPFTRACE=y`. Full reference: [Userspace tooling appendix](../part5-rootfs/appendix-tooling.md).

## 119.1  printk

The kernel's `printk` is your first line of debug. Levels:

```c
pr_emerg("system unusable\n");           /* KERN_EMERG, 0 */
pr_alert("action immediately\n");        /* KERN_ALERT, 1 */
pr_crit("critical conditions\n");        /* KERN_CRIT, 2 */
pr_err("error conditions\n");             /* KERN_ERR, 3 */
pr_warn("warning conditions\n");          /* KERN_WARNING, 4 */
pr_notice("normal but significant\n");    /* KERN_NOTICE, 5 */
pr_info("informational\n");               /* KERN_INFO, 6 */
pr_debug("debug-level\n");                /* KERN_DEBUG, 7 */
```

`dmesg -w` (follow) shows the live ring buffer. `dmesg -l err,warn` filters. The ring buffer is bounded (default ~128 KB; configurable via `CONFIG_LOG_BUF_SHIFT`).

Console log level (which prints to console vs only-ring-buffer):

```sh
cat /proc/sys/kernel/printk
# 4   4   1   7   <-- current, default, min, default-console
echo 7 > /proc/sys/kernel/printk   # show DEBUG and lower on console
```

Or boot with `loglevel=7` cmdline.

`pr_debug` is worth knowing about: by default it compiles to nothing (zero-cost when off). Enable per-file via `dyndbg`:

```sh
# Enable all pr_debug in net/wireless/
echo 'file net/wireless/*.c +p' > /sys/kernel/debug/dynamic_debug/control

# Enable a single function
echo 'func nl80211_get_wiphy +p' > /sys/kernel/debug/dynamic_debug/control

# At boot via cmdline:
dyndbg="file drivers/net/ethernet/freescale/fec_main.c +p"
```

This enables existing debug prints in mainline drivers without rebuilding.

## 119.2  ftrace

`ftrace` lives in `/sys/kernel/tracing/`. It's a function call tracer that records every kernel function call (and optionally entry/exit pairs) with nanosecond timestamps into a ring buffer.

```sh
cd /sys/kernel/tracing
echo function > current_tracer        # trace every function call
echo 1 > tracing_on

# ... run your test workload ...

echo 0 > tracing_on
cat trace | head -50
# # tracer: function
# # entries-in-buffer/entries-written: 9994/9994 ...
# my_app-1024  [000] d... 12.345: __vfs_read <-vfs_read
# my_app-1024  [000] d... 12.346: ext4_file_read <-__vfs_read
# my_app-1024  [000] d... 12.347: ext4_buffered_read <-ext4_file_read
# ...
```

This is *every kernel function called by any process* during the trace window. The buffer fills fast (~MB/sec); use filters:

```sh
echo ext4_* > set_ftrace_filter         # trace only ext4_ functions
echo my_app > set_ftrace_pid            # only trace one process
echo > set_ftrace_filter                # clear
```

### function_graph — the call tree visualization

```sh
echo function_graph > current_tracer
echo ext4_file_read > set_graph_function
echo 1 > tracing_on
# ... workload ...
echo 0 > tracing_on
cat trace
#  3)               |  ext4_file_read() {
#  3)               |    generic_file_read_iter() {
#  3)               |      filemap_read() {
#  3)   1.234 us    |        ext4_buffered_read();
#  3)   5.678 us    |      }
#  3) ! 23.456 us   |    }
#  3) + 45.012 us   |  }
```

Indentation shows call depth; duration per call (`us`); markers (`!` = >100 µs, `+` = >10 µs) draw attention to slow paths. Useful for performance investigation.

### Events — predefined tracepoints

The kernel ships hundreds of tracepoints (`/sys/kernel/tracing/events/`):

```sh
ls events/
# block  cpu_id  irq  kvm  net  sched  syscalls  tcp  workqueue  ...

# Enable sched_switch events
echo 1 > events/sched/sched_switch/enable
echo 1 > tracing_on
sleep 1
echo 0 > tracing_on
cat trace
# bash-1024 [000] d..3. 12.345: sched_switch: prev_comm=bash prev_pid=1024 ... next_comm=kworker/0:1
# kworker/0:1-15 [000] d..3. 12.346: sched_switch: ...
```

Combined: "which processes ran in the last second + what kernel functions did they call" → use both `function_graph` + `sched/sched_switch` events.

### trace-cmd + KernelShark

For larger traces and a GUI:

```sh
apt install trace-cmd kernelshark

# Record while a workload runs
trace-cmd record -e sched_switch -e block -p function_graph -g ext4_file_read myworkload
# (creates trace.dat)

# Open in GUI
kernelshark trace.dat
```

KernelShark gives a timeline-per-CPU view with function-graph trees and event flags overlaid. Useful for `why did this 1-second operation take 10 seconds`.

## 119.3  eBPF

eBPF lets you attach safe (verified) C-like programs to thousands of kernel hook points. `bpftrace` is the high-level DSL; `bcc` (Python+C) is the lower-level library.

```sh
apt install bpftrace

# Count TCP retransmits per remote IP
bpftrace -e 'kprobe:tcp_retransmit_skb { @retx[ntop(((struct sock*)arg0)->__sk_common.skc_daddr)] = count(); }'
# ^C
# @retx[192.168.1.5]: 12
# @retx[8.8.8.8]: 3

# Histogram of read sizes
bpftrace -e 'kprobe:vfs_read { @reads = hist(arg2); }' -c 'dd if=/dev/zero of=/tmp/x bs=4096 count=1000'

# Trace every execve
bpftrace -e 'tracepoint:syscalls:sys_enter_execve { printf("%s %s\n", comm, str(args->filename)); }'
```

eBPF programs are production-safe. The in-kernel verifier rejects infinite loops, bad memory access, and anything that would crash the kernel. You can run them on a live customer device.

For embedded — i.MX6ULL is technically a Cortex-A7 (32-bit) and eBPF support on 32-bit ARM is limited; better tooling on aarch64. The principle is the same; consider arm64 SoCs for newer designs where eBPF is the primary debug tool.

## 119.4  kgdb — GDB over serial

When you do want full GDB on a deployed device but have no JTAG:

```sh
# Build kernel with CONFIG_KGDB=y, CONFIG_KGDB_SERIAL_CONSOLE=y
# Boot with: kgdboc=ttymxc0,115200 kgdbwait

# Kernel pauses early in boot waiting for debugger
# On host:
arm-linux-gnueabihf-gdb vmlinux
(gdb) target remote /dev/ttyUSB0
(gdb) ... full GDB experience ...
(gdb) continue
```

Limitations:
- The console is taken; you can't `dmesg` from a serial terminal while kgdb owns it.
- A scheduled-out task can't be inspected (only the currently-running one + scheduled queues).
- Performance overhead — every breakpoint is a serial round-trip.

Most useful for: a kernel that hangs early-boot (you set `kgdbwait`); a deployed device with a specific reproducible bug; a CI test runner that can attach gdb on test failure.

## 119.5  Kernel oops

When the kernel hits an unhandled fault, it prints an "oops":

```
Unable to handle kernel NULL pointer dereference at virtual address 00000018
pgd = 80c54000
[00000018] *pgd=00000000
Internal error: Oops: 5 [#1] PREEMPT ARM
Modules linked in: my_driver(O)
CPU: 0 PID: 1234 Comm: my_app Not tainted 6.1.0-myimg #1
Hardware name: Freescale i.MX6 ULL (Device Tree)
PC is at my_driver_probe+0x24/0x100 [my_driver]
LR is at __platform_driver_probe+0x20/0x50
pc : [<7f000024>]    lr : [<8050a0b0>]    psr: 60000113
...
[<7f000024>] (my_driver_probe [my_driver]) from [<8050a0b0>] (__platform_driver_probe+0x20/0x50)
[<8050a0b0>] (__platform_driver_probe) from [<8050a1a0>] ...
```

The stack trace addresses are virtual (kernel-VA mapped). To decode:

```sh
# Auto-decode via the kernel's helper
dmesg | scripts/decode_stacktrace.sh vmlinux /path/to/modules > oops.decoded

# Manual: addr2line on the kernel ELF
arm-linux-gnueabihf-addr2line -e vmlinux -f 0x8050a0b0
# __platform_driver_probe
# drivers/base/platform.c:583
```

For a module, the offset within the module file:

```sh
arm-linux-gnueabihf-addr2line -e my_driver.ko -f 0x24
# my_driver_probe
# /path/to/my_driver.c:42
```

That points to the exact source line. Run `git blame` on it to see which patch introduced the regression.

For the oops to be useful, you must have:
- `CONFIG_DEBUG_INFO=y` when building.
- The *exact* same kernel + modules ELFs that were running on the failing device.

Tip: always keep the build artifacts (`vmlinux`, `.ko` files with debug info) for every shipped build. Without them, oops decoding is impossible.

## 119.6  kdump — full crash dump

For really deep autopsies, `kdump` captures the entire kernel memory image after a crash:

```
Crashed kernel → kexec → small "capture kernel" boots → saves /proc/vmcore to disk
Reboot with normal kernel; analyze vmcore with crash(8) on host
```

```sh
crash vmlinux vmcore
crash> bt                     # backtrace at time of crash
crash> ps                     # all tasks at time of crash
crash> mod                    # loaded modules
crash> rd 0x80c00000 32       # read kernel memory
crash> log                    # dmesg
```

`crash` is RH's tool; takes some learning, but for oopses you can't reproduce, it's the right tool.

Embedded systems often lack the disk space for vmcore (200+ MB); skip kdump and rely on ftrace + oops decoder.

## 119.7  Lab

1. **dyndbg.** Enable all `pr_debug` in `net/wireless/`; watch a `wpa_supplicant` connection; see the previously-hidden debug output.
2. **ftrace function_graph.** Trace `ext4_file_read` for a `cat /etc/passwd`; identify which function dominates the time.
3. **trace-cmd capture.** Record `sched/sched_switch + irq/* + block/block_rq*` during a `dd` write; open in KernelShark; visualize.
4. **bpftrace one-liner: top syscalls.**
   ```sh
   bpftrace -e 'tracepoint:raw_syscalls:sys_enter { @[comm, args->id] = count(); }'
   ```
   Run for 30 s; identify which process is hammering which syscall.
5. **bpftrace TCP retransmits.** Run the example; pull the network cable mid-transfer; watch retransmit counts climb per IP.
6. **kgdb on early boot.** Boot kernel with `kgdbwait` + `kgdboc=ttymxc0`; attach GDB; step through `start_kernel`.
7. **Force an oops.** Write a kernel module that dereferences NULL in `init`. `insmod` it; capture the oops; decode with `decode_stacktrace.sh`.
8. **vmcore capture.** Set up kdump on the i.MX6ULL (challenging — small RAM); trigger an oops; capture vmcore; analyze with `crash` on host.
9. **Permanent ftrace.** Configure ftrace to run from boot, recording sched + IRQ events; on next oops, save the ftrace buffer with the oops. (Use `ftrace_dump_on_oops=1` kernel cmdline.)
10. **dynamic_debug at boot.** Add `dyndbg="file drivers/usb/* +p"` to cmdline; see all USB debug prints during enumeration.

## 119.8  Pitfalls

- **dmesg buffer wraps.** Default 128 KB; verbose drivers eat it in seconds. Bump to 1 MB with `CONFIG_LOG_BUF_SHIFT=20`.
- **printk during fast path.** A printk in an IRQ context with `loglevel >= 4` blocks for 1+ ms (UART transmission). Don't `pr_info` in hot paths.
- **ftrace overhead.** Function tracer adds ~50 ns per traced kernel call. Realistic kernel function rates under load on a Cortex-A7 are 1–10 M/s, so unfiltered tracing typically costs 5–10 % CPU. Always use `set_ftrace_filter` to scope.
- **ftrace buffer fills in seconds.** Default 1 KB per CPU; bump to `echo 8192 > buffer_size_kb` for usable durations.
- **lost trace events.** When the buffer fills, oldest events drop. Check `cat /sys/kernel/tracing/per_cpu/cpu0/stats` for lost_events.
- **dynamic_debug requires CONFIG_DYNAMIC_DEBUG=y.** Most distros have it; verify.
- **kgdb console conflict.** Once kgdb attaches, the same UART can't be used for dmesg. Use a second serial port or USB-serial.
- **bpftrace BTF requirement.** Modern bpftrace expects BTF info in vmlinux; older kernels without `CONFIG_DEBUG_INFO_BTF=y` can't be probed by BTF-typed programs.
- **eBPF on 32-bit ARM.** Limited support; many newer features are arm64-only. i.MX6ULL is 32-bit; use ftrace/trace-cmd instead.
- **vmlinux without DEBUG_INFO.** Oops decoding fails silently — addresses can't be mapped to symbols. Build with `CONFIG_DEBUG_INFO=y`.
- **module addresses changing.** Each `insmod` chooses a different load address; can't reuse oops decoder output across loads. Capture both oops and `/proc/modules` simultaneously.

## 119.9  Going deeper

- **`Documentation/trace/ftrace.rst`** — the canonical ftrace guide.
- **`Documentation/trace/events.rst`** — tracepoints + events.
- **`Documentation/dev-tools/kgdb.rst`** — kgdb docs.
- **Brendan Gregg's `bpftrace`/`bcc` tutorials** — http://brendangregg.com.
- **`scripts/decode_stacktrace.sh`** in kernel source.
- **Greg Kroah-Hartman's "Linux Kernel Driver" tutorials** — debugging chapters.
- **Steven Rostedt's ftrace papers** — the LWN series.
- **`crash(8)` man page + Red Hat docs** — for vmcore analysis.
- **Ch 118** — JTAG when none of the above suffice.
- **Ch 120** — user-space side.

---

> Next chapter: **Chapter 120 — User-space debugging** — gdbserver, strace, perf, coredumpctl.
