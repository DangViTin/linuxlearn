---
chapter: 28
title: Kernel startup, traced
part: IV — The Kernel
estimated_pages: 24
status: draft
---

# Chapter 28 — Kernel startup, traced

> **What:** trace the kernel from the first instruction at `stext` to the moment it `exec`s `/sbin/init` — with the source files and line numbers at every step. By the end you should be able to point at any line of the boot log from Chapter 26 and say which function in which source file printed it.
>
> **Why:** The boot path is long but readable. Each line you trace becomes one less thing that surprises you when something breaks. By the time you have walked `stext → __mmap_switched → start_kernel → rest_init → kernel_init` once, you can debug "why is my system not booting?" with confidence.
>
> **Focus:** the **four phases** of kernel startup: (1) architecture-specific assembly that runs *before* virtual memory, (2) early C in `start_kernel()` that brings up subsystems in a fixed order, (3) `rest_init()` which forks PID 1 and PID 2, (4) `kernel_init` which exec's user-space. Each phase has a clean handoff to the next.

## 28.1  The four phases

```
┌─────────────────────────────────────────────────────────────────────┐
│ Phase 1: arch-asm  (arch/arm/kernel/head.S)                         │
│   - entry: stext   (the very first instruction)                     │
│   - MMU off, D-cache off, IRQ off                                   │
│   - sanity-check the FDT pointer (r2)                               │
│   - build initial page table                                        │
│   - enable MMU                                                      │
│   - jump to __mmap_switched (still in head-common.S)                │
│                                       │                             │
│ Phase 2: early C  (init/main.c)       ▼                             │
│   - __mmap_switched: copy .data, zero .bss, save boot args          │
│   - call start_kernel(), the boss function                          │
│   - 60+ init-step calls in a fixed order:                           │
│       setup_arch, mm_init, sched_init, init_IRQ, time_init, ...     │
│   - the kernel is now "up" but no user space exists                 │
│                                       │                             │
│ Phase 3: process model  (rest_init)   ▼                             │
│   - kernel_thread(kernel_init)  → PID 1                             │
│   - kernel_thread(kthreadd)     → PID 2                             │
│   - this CPU becomes the idle thread (PID 0)                        │
│                                       │                             │
│ Phase 4: user space   (kernel_init)   ▼                             │
│   - mount the rootfs (NFS / EXT4 / initramfs / ...)                 │
│   - run /sbin/init  (or /etc/init / /bin/init / /bin/sh fallback)   │
│   - if exec succeeds, kernel_init's job is done                     │
└─────────────────────────────────────────────────────────────────────┘
```

We walk each phase in turn. Source-file paths are relative to the kernel source root. Line numbers reference v6.6; ±5 lines on other versions.

## 28.2  Phase 1 — `stext` (arch/arm/kernel/head.S)

`stext` is the entry point — the very first instruction the kernel executes. The linker script `arch/arm/kernel/vmlinux.lds.S` declares it as the entry:

```ld
ENTRY(stext)
```

`stext` is defined in `arch/arm/kernel/head.S`. Before the kernel takes control, U-Boot has prepared:

```
MMU       = off
D-cache   = off
I-cache   = don't care (kernel will flush)
r0        = 0  (or boot-magic; ignored on DT systems)
r1        = machine number  (legacy ATAGS; ignored on DT systems)
r2        = physical address of the DTB
```

This contract is documented in `Documentation/arch/arm/booting.rst` — the page to consult if you ever doubt what register holds what.

`stext` walked, with our annotations:

```asm
ENTRY(stext)
    safe_svcmode_maskall r9    @ ensure SVC mode, IRQ+FIQ masked

    mrc p15, 0, r9, c0, c0      @ read processor MIDR
    bl  __lookup_processor_type @ find proc_info for this MIDR in __proc_info_begin..end
    movs r10, r5                @ r5 = procinfo struct ptr (or 0 = not supported)
    beq __error_p               @ if not supported, hang in __error_p

    bl  __vet_atags             @ sanity-check the FDT/ATAGS pointer in r2

    bl  __create_page_tables    @ build a minimal page table in OCRAM/early DRAM

    /* compute the address to jump to AFTER the MMU comes up */
    ldr r13, =__mmap_switched
    adr lr, 1f                  @ set up return for the __cpu_setup call
    mov r8, r4
    ldr r12, [r10, #PROCINFO_INITFUNC]
    add r12, r12, r10
    ret r12                     @ call CPU-specific __cpu_setup (arch/arm/mm/proc-v7.S)

1:  b   __enable_mmu            @ enable MMU; flow continues at r13 (=__mmap_switched)
ENDPROC(stext)
```

Four points to keep in mind:

- **`__lookup_processor_type`** walks a linker-supplied array (`__proc_info_begin..__proc_info_end`) of `struct proc_info_list`. Each entry says "for MIDR mask X = value Y, this is your `cpu_setup`, `cpu_cache_fns`, etc." The Cortex-A7 entry lives in `arch/arm/mm/proc-v7.S`. If your CPU isn't recognised, the kernel hangs in `__error_p` (you see no output because UART isn't initialised yet — Chapter 26 §26.5 covers this failure mode).
- **`__vet_atags`** does a quick byte-pattern check on the data at `r2`. If it looks like a DTB (magic bytes `0xD00DFEED`) or ATAGS, it's accepted; otherwise the address is zeroed and the kernel will later boot with no DT (almost certainly panicking).
- **`__create_page_tables`** builds a flat identity-mapped 1-MiB-section page table just big enough to cover the kernel image + early reservations. Real page tables come later in `paging_init()`.
- **`__enable_mmu`** sets `SCTLR.M=1`. The next instruction it executes is via virtual addresses; the jump-via-`r13` lands at `__mmap_switched`, which lives at a virtual address in the kernel's mapped region.

## 28.3  Phase 2 begins — `__mmap_switched` (arch/arm/kernel/head-common.S)

The first C-callable function after the MMU comes up. It does the C runtime setup:

```asm
__mmap_switched:
    adr r3, __mmap_switched_data

    /* copy .data from its initial location to its run location (if any) */
    ldmia r3!, {r4, r5, r6, r7}
1:  cmp r5, r6
    ldrne fp, [r4], #4
    strne fp, [r5], #4
    bne 1b

    /* zero .bss */
    mov fp, #0
1:  cmp r6, r7
    strcc fp, [r6], #4
    bcc 1b

    /* save processor ID, machine number, atags/dtb pointer for early kernel code */
    ldmia r3, {r4, r5, r6, r7, sp}
    str r9, [r4]   @ processor ID
    str r1, [r5]   @ machine number
    str r2, [r6]   @ atags/dtb pointer

    b start_kernel  @ never returns
ENDPROC(__mmap_switched)
```

The two stash-saves at the end are why `r9`, `r1`, `r2` were preserved through Phase 1: they get parked at well-known kernel addresses so the C code can find them.

After `b start_kernel`, we are running C with a stack, BSS zeroed, and the boot arguments tucked away. **This is the boundary between assembly and C.** Everything from here is in `init/main.c` or files it calls.

## 28.4  Phase 2 main — `start_kernel()` (init/main.c)

`start_kernel()` is ~200 lines of sequential setup calls. Each call brings one subsystem from "uninitialised" to "minimally functional." The order matters — many calls depend on earlier ones. Read it from the top:

```c
asmlinkage __visible void __init start_kernel(void)
{
    char *command_line;
    char *after_dashes;

    set_task_stack_end_magic(&init_task);
    smp_setup_processor_id();
    debug_objects_early_init();
    init_vmlinux_build_id();
    cgroup_init_early();

    local_irq_disable();
    early_boot_irqs_disabled = true;

    boot_cpu_init();
    page_address_init();
    pr_notice("%s", linux_banner);          /* the famous "Linux version ..." */
    early_security_init();
    setup_arch(&command_line);              /* the heavy lifter — see below */
    setup_boot_config();
    setup_command_line(command_line);
    setup_nr_cpu_ids();
    setup_per_cpu_areas();
    smp_prepare_boot_cpu();
    boot_cpu_hotplug_init();

    build_all_zonelists(NULL);
    page_alloc_init();
    pr_notice("Kernel command line: %s\n", saved_command_line);

    /* parameter parsing */
    after_dashes = parse_args("Booting kernel",
                              static_command_line, __start___param,
                              __stop___param - __start___param,
                              -1, -1, NULL, &unknown_bootoption);

    setup_log_buf(0);
    vfs_caches_init_early();
    sort_main_extable();
    trap_init();
    mm_core_init();                         /* the memory manager */
    poking_init();
    ftrace_init();
    early_trace_init();
    sched_init();                           /* the scheduler */
    radix_tree_init();
    maple_tree_init();
    housekeeping_init();
    workqueue_init_early();
    rcu_init();
    trace_init();
    context_tracking_init();
    early_irq_init();
    init_IRQ();                             /* the interrupt subsystem */
    tick_init();
    rcu_init_nohz();
    init_timers();
    srcu_init();
    hrtimers_init();
    softirq_init();
    timekeeping_init();
    kfence_init();
    time_init();

    /* enable interrupts — kernel can now respond to IRQs */
    local_irq_enable();
    early_boot_irqs_disabled = false;

    /* ... many more init calls ... */

    console_init();                         /* now printk reaches the UART for real */
    ...
    rest_init();                            /* hand off to phase 3 */
}
```

A few calls earn their own attention.

### `setup_arch(&command_line)` — `arch/arm/kernel/setup.c`

The biggest single call in `start_kernel()` on ARM. The main steps are:

1. **`setup_machine_fdt(__atags_pointer)`** — parses the DT blob (passed in `r2` and saved by Phase 1). Calls `unflatten_device_tree()` which converts the flat DTB to the in-memory tree of `struct device_node`. Reads `/chosen/bootargs` and stores it in `boot_command_line`.
2. **`parse_early_param()`** — handles a small set of cmdline tokens that need to be processed before most subsystems exist (`earlycon=`, `debug=`, `nokaslr`, `mem=`).
3. **`paging_init()`** — builds the *real* page tables now that we know how much DRAM exists (from the DT) and where the kernel needs to map peripherals.
4. **`request_standard_resources()`** — populates `/proc/iomem` with the kernel-code / kernel-data / DRAM regions.
5. **`smp_init_cpus()`** — initializes per-CPU data structures.

After `setup_arch` returns, *the kernel knows what hardware it's on*, and the command line is parsed.

### `mm_core_init()` — `mm/mm_init.c`

Brings up the memory subsystem: the page allocator (`buddy`), the slab allocator (`SLUB`), the vmalloc address space. After this, `kmalloc()` works.

### `sched_init()` — `kernel/sched/core.c`

Initializes the scheduler's data structures and creates the boot CPU's runqueue. After this, `schedule()` works — but there's still only one task (the boot thread).

### `init_IRQ()` — calls into `arch/arm/kernel/irq.c` → `irqchip_init()`

Walks the DT looking for nodes with `compatible = "arm,cortex-a7-gic"` (or whichever interrupt controller the SoC uses), and probes the GIC driver. After this, IRQs from devices can be registered with `request_irq()`.

### `time_init()` — `drivers/clocksource/`

Walks the DT for clocksource and clockevent providers (the generic ARM timer, or i.MX GPT, depending on configuration). Establishes the kernel's notion of "the current time" and "how to schedule future events." After this, `jiffies` advances, `udelay()` works, `hrtimer`s work.

### `console_init()` — `drivers/tty/`

Now binds the *real* console driver to the UART. Until this point, all `printk` output went to one of two places. Either it sat in the `printk` ring buffer for `dmesg` to read later, or it was pushed to the UART by `earlycon` if the bootloader configured that. After `console_init()`, every later `printk` reaches the UART in real time.

### Roughly 30 more init calls

`vfs_caches_init`, `proc_root_init`, `cgroup_init`, `taskstats_init_early`, `cpuset_init`, `kthread_init`, `late_time_init`, … each brings up one subsystem. Don't memorise the order; do know that it's a fixed sequence that you can trace in source.

At the end, `start_kernel()` calls `rest_init()` and never returns.

## 28.5  Phase 3 — `rest_init()` (init/main.c)

```c
noinline void __ref rest_init(void)
{
    struct task_struct *tsk;
    int pid;

    rcu_scheduler_starting();

    /*
     * We need to spawn init first so that it obtains pid 1, however
     * the init task will end up wanting to create kthreads, which,
     * if we schedule it before we create kthreadd, will OOPS.
     */
    pid = user_mode_thread(kernel_init, NULL, CLONE_FS);
    rcu_read_lock();
    tsk = find_task_by_pid_ns(pid, &init_pid_ns);
    tsk->flags |= PF_NO_SETAFFINITY;
    set_cpus_allowed_ptr(tsk, cpumask_of(smp_processor_id()));
    rcu_read_unlock();

    numa_default_policy();
    pid = kernel_thread(kthreadd, NULL, NULL, CLONE_FS | CLONE_FILES);
    rcu_read_lock();
    kthreadd_task = find_task_by_pid_ns(pid, &init_pid_ns);
    rcu_read_unlock();

    system_state = SYSTEM_SCHEDULING;
    complete(&kthreadd_done);

    /* Call into cpu_idle with preempt disabled */
    schedule_preempt_disabled();
    cpu_startup_entry(CPUHP_ONLINE);
}
```

Three things happen:

1. **PID 1 created.** `user_mode_thread(kernel_init)` creates a task running `kernel_init()` as PID 1. This task will eventually `exec` user space.
2. **PID 2 created.** `kernel_thread(kthreadd)` creates a task running `kthreadd()` as PID 2. `kthreadd` is the kernel-thread daemon: every subsequent `kthread_create()` is dispatched through it. There is a separate task for this because creating kthreads needs certain locks that the boot thread cannot easily take.
3. **The boot CPU becomes the idle thread (PID 0).** `cpu_startup_entry(CPUHP_ONLINE)` enters `do_idle()`, which is the per-CPU idle loop. When no other task is runnable, the CPU runs idle, which on ARM eventually executes `wfi` (wait for interrupt).

After `rest_init()` returns to the boot CPU's task, that task *is* PID 0 doing idle.

You can verify on a running system:

```
target# ps -A | head
  PID TTY          TIME CMD
    1 ?        00:00:01 init
    2 ?        00:00:00 kthreadd
    3 ?        00:00:00 rcu_gp
    4 ?        00:00:00 rcu_par_gp
    ...
```

PID 1 is init. PID 2 is kthreadd. PID 0 (the idle task) doesn't show in `ps` because it's a kernel-internal thread.

## 28.6  Phase 4 — `kernel_init()` (init/main.c)

PID 1 starts here:

```c
static int __ref kernel_init(void *unused)
{
    int ret;

    /*
     * Wait until kthreadd is all set-up.
     */
    wait_for_completion(&kthreadd_done);

    kernel_init_freeable();             /* device init, SMP wakeup, rootfs mount */
    async_synchronize_full();
    kprobe_free_init_mem();
    ftrace_free_init_mem();
    kgdb_free_init_mem();
    exit_boot_config();
    free_initmem();                     /* free .init.* sections — done with them */
    mark_readonly();

    /*
     * Kernel mappings are now finalized - update the userspace page-table
     * to finalize PTI.
     */
    pti_finalize();

    system_state = SYSTEM_RUNNING;
    numa_default_policy();

    rcu_end_inkernel_boot();

    do_sysctl_args();

    if (ramdisk_execute_command) {
        ret = run_init_process(ramdisk_execute_command);
        if (!ret)
            return 0;
        pr_err("Failed to execute %s (error %d)\n",
               ramdisk_execute_command, ret);
    }

    /*
     * We try each of these until one succeeds.
     *
     * The Bourne shell can be used instead of init if we are
     * trying to recover a really broken machine.
     */
    if (execute_command) {
        ret = run_init_process(execute_command);
        if (!ret)
            return 0;
        panic("Requested init %s failed (error %d).",
              execute_command, ret);
    }

    if (CONFIG_DEFAULT_INIT[0] != '\0') {
        ret = run_init_process(CONFIG_DEFAULT_INIT);
        if (ret)
            pr_err("Default init %s failed (error %d)\n",
                   CONFIG_DEFAULT_INIT, ret);
        else
            return 0;
    }

    if (!try_to_run_init_process("/sbin/init") ||
        !try_to_run_init_process("/etc/init")  ||
        !try_to_run_init_process("/bin/init")  ||
        !try_to_run_init_process("/bin/sh"))
        return 0;

    panic("No working init found.  Try passing init= option to kernel. "
          "See Linux Documentation/admin-guide/init.rst for guidance.");
}
```

In English:

1. **Wait for `kthreadd` to be ready** (so the rest of init can spawn kthreads).
2. **`kernel_init_freeable()`** — finishes device probing, mounts the rootfs (per `root=` and `rootfstype=` from cmdline), opens `/dev/console`. This is the call that emits the *"VFS: Mounted root (ext4 filesystem) on device 179:2."* boot-log line.
3. **`free_initmem()`** — frees the `.init.*` linker sections. The kernel's setup code has run; it's no longer needed and gets returned to the page allocator. You see the famous *"Freeing unused kernel image (initmem) memory: 1024K"* line.
4. **Fall through the init-binary search**:
   - If `rdinit=` was on the cmdline → run that (initramfs case; see Ch 29).
   - Else if `init=` was on the cmdline → run that.
   - Else if `CONFIG_DEFAULT_INIT` is set → run that.
   - Else try `/sbin/init`, `/etc/init`, `/bin/init`, `/bin/sh` in order.
5. **`run_init_process()`** calls `kernel_execve()` which `exec`s the chosen binary. **On a successful `exec`, the calling task's image is replaced** — `kernel_init()`'s code is unmapped, the new program runs. From the kernel's perspective, PID 1 is now /sbin/init (which lives in user space). `kernel_init` "returns" only in the sense that it never returns from `kernel_execve`.

After this point, the kernel is in steady state. User-space processes run. The kernel responds to syscalls and interrupts. The boot is done.

## 28.7  Mapping boot-log lines to source

For every memorable boot-log line, you can now name the source location. Spot-checks:

| Boot log line | Source file | Function |
|---|---|---|
| `Booting Linux on physical CPU 0x0` | `arch/arm/kernel/setup.c` | `setup_arch` calling `pr_info` |
| `Linux version 6.6.0 (you@host) ...` | `init/version.c` | `start_kernel` printing `linux_banner` |
| `OF: fdt: Machine model: ...` | `drivers/of/fdt.c` | `early_init_dt_scan` |
| `Kernel command line: ...` | `init/main.c` | `start_kernel` printing `saved_command_line` |
| `Memory: 444184K/524288K available ...` | `mm/mm_init.c` | `mem_init_print_info` (moved out of `mm/page_alloc.c` in v6.2+) |
| `clocksource: arm_global_timer: ...` | `drivers/clocksource/arm_global_timer.c` | clocksource registration |
| `imx-uart 2020000.serial: ...` | `drivers/tty/serial/imx.c` | `imx_uart_probe` |
| `Freeing unused kernel image (initmem) memory: 1024K` | `mm/page_alloc.c` | `free_initmem` |
| `Run /sbin/init as init process` | `init/main.c` | `run_init_process` |

That table is the goal of this chapter. After it, you can grep the kernel for any boot-log line and find its source in under a minute.

## 28.8  Lab

1. **Walk `start_kernel()` end-to-end** with the source open. Count the init-step calls. Mark which ones you'd expect to be expensive (memory init, clocksource init, console init) vs cheap.
2. **Find which DT property each setup_arch step reads.** Look at `early_init_dt_scan_*()` functions in `drivers/of/fdt.c`. Note which ones look at `/chosen/bootargs`, which at `/cpus`, which at `/memory`.
3. **Build with `ftrace_dump_on_oops`** in `.config` and add `printk.devkmsg=on initcall_debug` to bootargs. Boot. Run `dmesg | grep initcall`. You will see every initcall function name printed as it runs — a more detailed view of the same flow this chapter described.
4. **Boot with `loglevel=8`** to see *all* `printk` levels. You'll see kilobytes more output than the default; among it are the debug-level prints that document things like the page allocator's initial population, slab cache creation, and so on.
5. **Trace a panic.** Pass `init=/nonexistent` in bootargs. Boot. The kernel reaches `kernel_init`, the four `try_to_run_init_process()` calls fail in turn, and `panic("No working init found.")` fires. Compare the panic message to the source in `kernel_init()`.

## 28.9  Pitfalls

- **Confusing `vmlinux` with `zImage`.** When debugging a panic, you want symbols. The symbols are in `vmlinux`, not `zImage`. Always have `vmlinux` from the *same build* alongside your `zImage`.
- **Thinking init runs in kernel space.** PID 1 is *kernel_init* until `kernel_execve("/sbin/init")` returns successfully; thereafter PID 1 is the `/sbin/init` user-space binary. The transition is invisible in `ps` output but real in process address space.
- **`free_initmem` recycles `.init.text` and `.init.data`.** Function names like `init_IRQ`, `setup_arch`, `start_kernel` themselves get freed — you cannot call them after boot. The compiler enforces this via the `__init` attribute, which places them in the `.init.text` section.
- **`__init` data referenced after boot.** A subtler version of the above. If a driver's probe routine stashes a pointer to a global tagged `__initdata`, that pointer becomes dangling after `free_initmem`. Symptom: crash on first access to the data, much later. Lint catches most of these; some slip through.
- **Console output disappearing mid-boot.** Happens when the early `earlycon` is active, then the regular console-driver probes but mismatches the port, and the regular driver "takes over" without working. Symptom: log goes silent partway through. Fix: ensure your `console=` and DT `/chosen/stdout-path` agree.
- **Reading kernel source on the wrong version.** Always check what `cat /proc/version` reports on your target and read the matching tag in your local source tree. v6.6 and v6.7 can differ in startup flow.

## 28.10  Going deeper

- **`init/main.c`** — the file `start_kernel` lives in. Read it cover to cover; ~1000 lines, mostly the function we walked.
- **`arch/arm/kernel/head.S`** and **`arch/arm/kernel/head-common.S`** — the assembly entry. Short and educational.
- **`Documentation/arch/arm/booting.rst`** — the boot contract.
- **`Documentation/admin-guide/init.rst`** — what cmdline parameters `kernel_init` consults.
- **`Documentation/core-api/printk-formats.rst`** — printk format specifiers (`%pK`, `%pS`, `%px`, …) that you'll see all through the kernel.
- **The Bootlin "Embedded Linux kernel" training material** (free, public) — covers the same startup path with different emphasis.

> Next chapter: **Chapter 29 — Initramfs from scratch.** Now that we understand the kernel's boot path, we build the smallest possible thing it can hand off to — a single statically-linked binary in a cpio archive.
