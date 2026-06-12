---
chapter: 33
title: Init systems
part: V - Root filesystem & user space
estimated_pages: 14
status: draft
---

# Chapter 33: Init systems

> **What:** PID 1, what it does, what it should do, and the three real choices for an embedded Linux system: BusyBox `init` (tiny, traditional), `sysvinit` (the classical desktop init from the 90s), and `systemd` (the modern service manager that runs on basically every desktop distro).
>
> **Why:** PID 1 is special: the kernel panics if it dies, and every other process on the system descends from it. The choice you make here determines how you write boot scripts, how you crash-restart services, how logs are collected, and how much disk and RAM the system uses just to "be up."
>
> **Focus:** the **trade-off triangle**: simplicity, capability, and footprint. BusyBox wins on simplicity and footprint. Systemd wins on capability. Sysvinit is the historical middle. For most embedded products in 2025, BusyBox init is the right answer. Knowing *why* is the goal of this chapter.


## 33.1  What PID 1 actually does

The minimum PID-1 job description:

1. **Run startup scripts** (mount filesystems, configure network, start daemons).
2. **Spawn login prompts** (one per console / serial line).
3. **Reap zombies.** When a process's parent dies, its children get reparented to PID 1. When *those* children eventually exit, PID 1 must `wait()` for them or they become zombies forever.
4. **Handle signals.** `SIGTERM` → shut down cleanly. `SIGINT` (Ctrl-Alt-Del on a physical keyboard) → reboot or do whatever the policy says.
5. **Coordinate shutdown.** Stop services in reverse start order, unmount filesystems, sync disks, then `reboot()` or `poweroff()`.

That's it. Any program that does these five things is a legitimate PID 1. The choice is *how* much beyond this it does.

## 33.2  BusyBox init

We've been using this since Chapter 29. It is **~1500 lines of C**, statically linked into the BusyBox binary as one of its applets, and does exactly the five things in §33.1, no more, no less. Configuration is one file: `/etc/inittab` (Chapter 31 §31.5).

Features it has:

- `inittab`-based: `sysinit`, `respawn`, `askfirst`, `once`, `wait`, `shutdown`, etc. (the 8 actions from Ch 31)
- Reads `/etc/inittab` once at boot. Re-reads on SIGHUP
- Reaps zombies. Signals shutdown properly

Features it does *not* have:

- No service dependency tracking. If service A needs service B running, you have to encode that in shell scripts yourself.
- No automatic restart count limit. If a service crashes 1000 times in 1 second, busybox-init dutifully restarts it 1000 times.
- No socket activation. (Systemd's headline feature. Nice to have for embedded? Rarely.)
- No structured logging. `printf` to the console. That's it.
- No cgroup-based resource isolation per service.

**When to choose BusyBox init:**

- Single-purpose appliance. The system runs one or two daemons + a shell.
- Boot time matters. BusyBox init starts within 100 ms of `kernel_init`.
- RAM and flash budget are tight. The init itself adds 0 bytes (it's inside busybox).
- You want to *understand* every line that runs at boot. You can read all the init code in an hour.

For most i.MX6ULL-class embedded products, this is the right answer.

## 33.3  sysvinit

The classical Unix init from the 80s/90s. Still around, still on some Debian systems if you uninstall systemd.

The model:

- `/etc/inittab` (different syntax from BusyBox. Runs `/etc/rc.d/rc <N>` for each runlevel)
- `/etc/init.d/`: one shell script per service. Each script accepts `start`, `stop`, `restart`, `status` as arguments.
- `/etc/rc<N>.d/`: symlinks to `/etc/init.d/` scripts, named `S<NN><name>` (start) or `K<NN><name>` (kill). Init runs them in numeric order when entering runlevel N.

**Runlevels**: a number 0-6 representing system states. By convention:

- 0 = halt
- 1 = single-user maintenance
- 2 = multi-user, no networking (rarely used)
- 3 = multi-user, networking, text console
- 5 = multi-user, networking, graphical login
- 6 = reboot

You change runlevel with `init <N>` or `telinit <N>`. The current level is in `/var/run/utmp`.

A sysvinit service script:

```sh
#!/bin/sh
### BEGIN INIT INFO
# Provides:          my-daemon
# Required-Start:    $network
# Required-Stop:     $network
# Default-Start:     2 3 4 5
# Default-Stop:      0 1 6
# Short-Description: My daemon
### END INIT INFO

case "$1" in
    start)
        start-stop-daemon --start --background --make-pidfile \
            --pidfile /var/run/my-daemon.pid \
            --exec /usr/bin/my-daemon
        ;;
    stop)
        start-stop-daemon --stop --pidfile /var/run/my-daemon.pid
        ;;
    restart) $0 stop; $0 start ;;
    *) echo "Usage: $0 {start|stop|restart}"; exit 1 ;;
esac
```

The `LSB info` block in the comment header gives dependency hints, sysvinit can read these and compute service order (or you arrange the symlink names manually).

**When to choose sysvinit:**

- You're maintaining an existing system that already uses it.
- You explicitly want runlevels and you'd find shell scripts comforting.

**When *not* to choose sysvinit:**

- You're starting fresh in 2025. BusyBox init does the same job with one tenth the bytes. Systemd does *more* if you need it. Sysvinit has little reason to exist in a new design.

## 33.4  systemd

Systemd is the giant in the room. Every major desktop distro (Debian, Ubuntu, Fedora, Arch) ships systemd by default. It is *the* default for general-purpose Linux in 2025.

What you get:

- **Unit files** instead of shell scripts. Declarative, in `/etc/systemd/system/`:
  ```ini
  [Unit]
  Description=My daemon
  After=network.target

  [Service]
  ExecStart=/usr/bin/my-daemon
  Restart=on-failure
  RestartSec=5s
  
  [Install]
  WantedBy=multi-user.target
  ```
- **Dependency-driven ordering.** `After=`, `Before=`, `Requires=`, `Wants=`, `Conflicts=`. Systemd computes the right parallel start order.
- **Per-service resource limits** via cgroups: `CPUQuota=`, `MemoryMax=`, `IOWeight=`.
- **Sandbox options**: `PrivateTmp=true`, `ProtectSystem=strict`, `NoNewPrivileges=true`, `CapabilityBoundingSet=`.
- **Socket activation**: a service starts when something connects to its socket, not at boot.
- **Timer units**: like cron jobs, but unit-managed.
- **`journald`**: a binary, queryable log database. `journalctl -u my-daemon` shows your service's logs.
- **A few hundred more features.**

The cost is footprint. Systemd itself plus its required satellites (`udev`, `systemd-journald`, `systemd-logind`, …) is **~6 MB on disk and ~30 MB RAM at idle** on a minimal install. On i.MX6ULL's 512 MB DRAM that's tolerable but not negligible.
> **udev:** the user-space device manager that reacts to kernel device events and creates policy-driven /dev nodes.

**When to choose systemd:**

- Your rootfs is **Ubuntu-base** or **Debian** (Chapter 35A). They already use systemd. Fighting it is more work than embracing it.
- You need socket activation, advanced sandboxing, or per-service cgroup limits.
- Your team is Linux-distro-experienced and `systemctl status` is muscle memory.

**When *not* to choose systemd:**

- You're on a Buildroot or yocto-core-image-minimal-style image. They default to BusyBox init for good reason.
> **Buildroot:** a configuration-driven build system that produces a complete root filesystem and related images.
- Your boot-time budget is < 2 seconds. Systemd needs 3-5 seconds on i.MX6ULL just for itself.
- RAM is tight (< 256 MB).

## 33.5  Comparing them at a glance

| | BusyBox init | sysvinit | systemd |
|---|---|---|---|
| Lines of code | ~1.5 K | ~5 K | ~600 K |
| Disk footprint | 0 (part of busybox) | ~100 KB | ~6 MB |
| RAM footprint (idle) | < 100 KB | ~1 MB | ~30 MB |
| Boot time on i.MX6ULL | ~100 ms | ~300 ms | ~3-5 s |
| Config format | `inittab` (4-column) | `inittab` + shell scripts | unit files (ini-style) |
| Service dependencies | manual (script order) | LSB headers | declarative `After=`/`Requires=` |
| Auto-restart | yes (respawn) | manual | yes (`Restart=`) |
| Resource limits | no | no | yes (cgroup) |
| Sandbox features | no | no | yes |
| Logging | console | console + syslog | journald (binary) |
| Industry default for embedded | yes | rare | growing |

## 33.6  Why embedded might want *no* init system at all

For some products the simplest answer is: **don't have one**. The kernel's `init=/path/to/myapp` cmdline argument tells the kernel to run *your application* as PID 1. No shell, no inittab, no service manager. Your application:

```c
int main(void) {
    /* set up signal handlers for SIGTERM */
    /* mount /proc, /sys, /dev */
    /* configure network */
    /* run forever, waiting on hardware */
}
```

This is the embedded equivalent of an MCU's `main()`. Boot time: under 500 ms total (kernel + your app). Footprint: whatever your app is. No `/etc/`, no `/sbin/init`, no nothing.

**When this works:**

- The system has one job (industrial controller, single-purpose sensor).
- No need to ssh in, no need to inspect anything live.
- Failure mode is "reboot", your app crashes, PID 1 crashes, kernel panics, watchdog (Ch 51A) reboots.

**When this doesn't work:**

- You need diagnostics. Without `/bin/sh` you can't poke around.
- Multi-service. If you have two daemons, you need *something* to start the second one.

For a developer board you almost always want a shell. For a shipping single-purpose appliance, "no init" is a real choice and surprisingly common.

## 33.7  Recommendation

For the rest of this book, and for most readers' real products, **BusyBox init** is the default. We use it in every chapter from here through Part VI. When we need to talk about a feature only systemd has (Chapter 51A's watchdog daemon, Chapter 35C's container manager), we'll note it explicitly. When we get to Chapter 35A (Ubuntu-base), we'll meet systemd in its natural habitat.

## 33.8  Lab

1. **Read your BusyBox `inittab`.** Identify which lines run at boot, which respawn, which run only on shutdown.
2. **Add a respawning service.** Edit `/etc/inittab` to add `::respawn:/usr/bin/my-counter`. Write `my-counter` as a tiny script that prints the date every 10 seconds. Save, reboot, watch.
3. **Trigger a manual shutdown.** From the console: `halt`. Read what BusyBox init does in response (it runs the `shutdown` lines from inittab). Compare with `reboot`.
4. **Read a systemd unit.** If you have a Debian/Ubuntu host nearby, `cat /lib/systemd/system/ssh.service`. Note the syntax differences vs BusyBox.
5. **Estimate the boot-time difference.** Boot your BusyBox rootfs and note the time from `kernel_init` to the login prompt. The `dmesg` timestamps are your clock. Now do the same on the Ubuntu-base rootfs (Ch 35A). Typical figures: ~2 s BusyBox vs ~8 s Ubuntu-base. Most of the gap is systemd.

## 33.9  Pitfalls

- **Zombies accumulating.** Some daemons double-fork and detach. The grandchild then gets reparented to PID 1. If PID 1's `wait()` loop is correct, the kernel hands it the SIGCHLD and the child is reaped. BusyBox init does this correctly. Custom PID-1 binaries often forget the `wait()` loop. The symptom is `<defunct>` processes piling up in `ps`.
- **Respawn storm.** A `respawn` line for a service that immediately exits causes infinite restart loop, burning CPU. BusyBox init doesn't rate-limit. Add a `sleep 5` to your service or use systemd's `RestartSec=`.
- **`/etc/inittab` syntax differences.** sysvinit uses runlevels in the second field. BusyBox ignores that field entirely. Don't copy/paste between init implementations.
- **`init=` cmdline overrides everything.** Even if `/sbin/init` exists, if you boot with `init=/bin/sh`, the kernel runs the shell directly. Useful for recovery. Surprising if you forgot you set it.
- **systemd in a 256 MB system.** It will boot but everything will be sluggish. Choose BusyBox or sysvinit instead.
- **systemd unit-file ordering bugs.** Putting both `After=` and `Wants=` on a unit can produce unexpected orderings if the targets aren't carefully chosen. When in doubt, read `systemd.unit(5)`.

## 33.10  Going deeper

- **BusyBox init source**: `init/init.c` in the BusyBox tree. ~1500 lines. Read it.
- **`Documentation/admin-guide/initrd.rst`** (kernel) for the init handoff details.
- **`man systemd.unit`**, **`man systemd.service`**, canonical systemd reference.
- **`Lennart Poettering`'s "Rethinking PID 1"** blog post, the original systemd design rationale. Worth reading for context.
- **`Rich Felker`'s posts on musl + init systems**: the minimalist's counter-argument.

> Next chapter: **Chapter 34: libc, dynamic linking, and the loader.** Down one more level: what the libraries are that everything else depends on, and how the kernel hands control to user space's first instruction.
