# Part V — Rootfs: Review

## Cross-cutting observations

- **MCU-to-Linux bridges are mostly absent.** Across all eight chapters there is no introductory paragraph that says something like "if you come from MCU-land: a rootfs is the file-tree the kernel mounts as `/` once it boots — analogous to the data your bootloader-burner tool would have written to an SD card image, except the kernel mounts it dynamically." Almost every chapter assumes the reader already has the Unix-userspace mental model. Add a 3-5 line "for the MCU reader" callout at the top of Ch31, Ch33, and Ch34 in particular.
- **PID 1 / init concept is repeatedly used before it is properly explained.** Ch31 §31.5 talks about "BusyBox init reads `/etc/inittab`" and `/sbin/init` long before Ch33 explains what PID 1 actually is. Either forward-reference Ch33 at the top of Ch31 §31.5 ("init = PID 1 = the first user-space process, equivalent to your RTOS scheduler's `main` task — covered in Ch33") or move the §33.1 "What PID 1 actually does" box into Ch31.
- **"Dynamic linking" is used in Ch31 §31.10 before Ch34 explains it.** Ch31 says "if you copy any *other* dynamically-linked binary…", with one paragraph of context, then ships you to copy libraries. The MCU reader doesn't know what dynamic linking is yet. A two-sentence bridge ("dynamic linking = library code lives in separate `.so` files at runtime, like loading function pointers from another flash region at boot — full treatment in Ch34") is needed.
- **No FHS figure beyond a tree-list.** The Ch31 §31.1 directory tree is good, but Part V never shows the *purpose-flow* (e.g., "binaries depend on libraries in `/lib`; init reads scripts in `/etc/init.d`; processes are reflected in `/proc`"). One diagram showing the runtime relationships would pay back across the whole part.
- **glibc / musl / uClibc comparison repeated three times.** Ch31 §31.3 mentions glibc size, Ch34 §34.1 has the full table, Ch35 §35.5 mentions `BR2_TOOLCHAIN_BUILDROOT_GLIBC=y`. Forward-reference Ch34 from Ch31 instead of foreshadowing twice.
- **NFS root setup is described in Ch31 §31.11 and repeated in Ch35A §35A.6 with almost identical wording.** Either factor it into a single "appendix: NFS root setup" callout or have Ch35A say "exactly the bootargs from §31.11 but with the Ubuntu rootfs path."
- **Boot-time claims vary by chapter.** Ch33 §33.5 says BusyBox boots in ~100 ms; Ch35A §35A.8 says BusyBox is "<3 s"; Ch35C §35C.8 says "Podman boot adds 2-5 s." The 100 ms figure in Ch33 is `kernel_init`→first userspace, not full boot; the rest are full-system numbers. Clarify in Ch33 what is being measured (it's the init-startup portion, not full boot).
- **`/etc/inittab` is shown with three different schemas** (BusyBox in Ch31 §31.5, sysvinit in Ch33 §33.3 implied, "systemd doesn't use inittab" never said outright). The reader may not realize that the same filename means different things across the three init systems. A one-line aside in Ch33 ("note: BusyBox init's inittab uses a *4-column* format; sysvinit's inittab is a *4-column* format with runlevel semantics in the second column; systemd has no inittab at all") would close that confusion.
- **No ASCII figure for "how a binary actually starts."** Ch34 §34.2 has prose-only description of "kernel `exec`s INTERP, INTERP loads NEEDED, fixes up GOT, jumps to `_start`." For an MCU engineer this is genuinely novel — a flow diagram with the kernel on the left, ld-linux in the middle, your binary on the right, with arrows for each step, would be one of the highest-value figures in Part V.

## Ch31 — Rootfs by hand

### Readability
- §31.1 "We will create every one of these and populate the populated ones." is confusing/recursive. Replace with: "We will create each of these directories. The ones that should contain files at boot (`bin/`, `sbin/`, `lib/`, `etc/`) we populate now; the ones the kernel or daemons fill (`proc/`, `sys/`, `dev/`, `tmp/`, `var/run/`) stay empty until mount time."
- §31.6 first sentence: "The shell script `/etc/inittab`'s `sysinit` line runs." is fragmented. Rewrite: "Now create the shell script that the `sysinit` line in `/etc/inittab` runs. This is where most per-boot setup lives."
- §31.10 "The dynamic linker itself MUST be the real file, not a symlink." is asserted twice but never explained *why* a symlink would break — does the kernel reject a symlink for INTERP? (It doesn't, generally — but inside a chroot/initramfs the link target may not resolve.) Either delete the second mention or replace with the actual reason.
- §31.13 "All five check out" — five what? Lists six commands above. Rename, e.g., "The five sanity checks pass: kernel running, CPU detected, devices enumerated, mounts active, memory free."

### MCU-engineer friendliness
- §31.3 builds BusyBox statically without first explaining what "BusyBox" is conceptually beyond Ch29's reference. Add one line: "BusyBox is a single binary that *contains* the implementations of `ls`, `cat`, `sh`, `mount`, ~240 others — like a single firmware image that exposes 240 separate command-line tools depending on how it's invoked."
- §31.5 `<id>:<runlevels>:<action>:<process>` — runlevels are mentioned without definition (defined only in Ch33). Either forward-reference Ch33 or say "BusyBox ignores this field, treat as blank."
- §31.6 mentions `mdev`, devpts, and "kernel's hotplug mechanism" without explaining any of them. mdev is then covered properly in Ch32 §32.4. Add a "(covered in detail in Ch32 §32.4)" pointer.
- §31.7 `<dump-freq>` and `<fsck-order>` fields shown but never explained. One-line gloss: "`dump-freq` controls a backup tool you'll never use; `fsck-order` controls boot-time fsck order — `0` means skip."
- §31.10 The whole library-copy step needs an MCU framing: "the cross-toolchain on your host contains the same libraries your target needs — `cp` them into `rootfs/lib/`. This is the equivalent of linking a startup file and HAL into your MCU build — except libraries are *separate files at runtime*, not compiled in."
- §31.12 "The development loop" — for an MCU engineer this is the killer feature and is buried. Add a contrast box: "On MCU: edit → cross-compile → JTAG-flash → reset → test = 30-60 s per iteration. With NFS rootfs: edit → save → re-run on target = 0 s per iteration."

### Missing examples / figures
- After §31.1 add an ASCII figure showing the *runtime dependency* graph: `/sbin/init` → reads `/etc/inittab` → runs `/etc/init.d/rcS` → which mounts `/proc`, `/sys`, `/dev/pts`, populates `/dev` via mdev. The current tree is structural; the reader needs the temporal flow.
- §31.5 needs a worked example of one `inittab` line annotated: `console::respawn:-/bin/sh` → "ID=console (use the system console as the controlling tty), runlevels=(ignored), action=respawn (restart whenever it exits), process=`-/bin/sh` (the leading `-` makes it a *login* shell)."
- §31.7 — show what `mount` looks like before and after `mount -a`. Right now you have to wait until §31.13 to see the output.
- §31.10 add a quick `arm-linux-gnueabihf-readelf -d /bin/some-app | grep NEEDED` example showing the *actual* libraries that need to be present.

### Technical errors / suspect claims
- §31.3 "static glibc = 580 KB" and "~450 KB with musl-gcc". This is for BusyBox-statically-linked. A typical full-applet static BusyBox is closer to ~800 KB with glibc; 580 KB is achievable but with a stripped applet set. Either tag the number as "minimal-applet build" or update.
- §31.3 callout: "DNS resolution doesn't work with static glibc, because glibc's NSS (Name Service Switch) requires dynamic loading." Accurate but the failure mode is more nuanced — `gethostbyname` from a static glibc *does* try to `dlopen` `libnss_files.so.2`, and on absence it falls back to compiled-in resolution that handles `/etc/hosts` but not DNS. Add: "specifically, static glibc binaries can still resolve hostnames in `/etc/hosts`; what they cannot do is real DNS over the network."
- §31.6 `echo /sbin/mdev > /proc/sys/kernel/hotplug` — this works but is the *legacy* mechanism; modern kernels can also use the netlink-based uevent socket (which mdev/udev prefer). Worth a one-line caveat.
- §31.10 "Total size: ~60 MB for glibc" — overstated unless you include locales and NSS modules. A trimmed glibc runtime is 5-10 MB. Suggest: "60 MB unstripped, 5-10 MB after `strip` and removing locales/NSS modules you don't need."
- §31.11 `nfsroot=...vers=3,nolock,tcp` — `nolock` is needed on NFS root, good. Worth saying *why*: NFSv3 file locking requires `rpc.lockd` and `rpc.statd` daemons which aren't running this early in boot.

### Knowledge prerequisites missing
- "FHS" introduced in §31.1 title without unpacking the acronym before using it.
- "applet" used in §31.4 without definition — for BusyBox it means "one of the commands BusyBox implements internally." Define on first use.
- "tmpfs" used in §31.7 without explaining it's a RAM-backed filesystem. The MCU reader does not know this.
- "login shell" mentioned in §31.5 — what makes a shell a "login shell" vs not? One sentence: "a login shell reads `/etc/profile` and `~/.profile` to set up the environment; a non-login shell doesn't."
- "NSS" used in §31.3 callout without explanation.
- §31.10 introduces `SONAME` indirectly ("`libc.so.6` is the ABI version") but the term `SONAME` is never defined; it shows up in Ch34. Forward-ref.

### Other
- §31.14 Lab item 4: "Persist `/var/log/`. Currently nothing writes to it." But §31.6 (`rcS`) doesn't redirect anything to `/var/log`. The lab makes sense, but say *explicitly* "modify `rcS` so it runs `dmesg > /var/log/dmesg.txt` at the end" — not "redirect `dmesg > ...`," which the reader might read as a shell-redirection requirement.
- §31.15 pitfall "NFS over Wi-Fi" — true but very specific; consider putting this in a sidebar so it doesn't drown the more important "forgot `chmod +x` on rcS" pitfall (which is the actual #1 bug).
- The chapter is titled "by hand" but never explicitly says when in the workflow you'd ever do this *outside* of learning. Add a 2-line "in production you'd use Buildroot (Ch35); doing it by hand once is the equivalent of writing your first MCU startup file from scratch."

## Ch32 — /proc, /sys, devtmpfs

### Readability
- §32.1 "Master this idiom and you can debug things without writing any code." — punchy, good. Keep.
- §32.2 "`/proc` was originally a way for `ps` to list processes." Choppy. Suggest: "`/proc` was originally a kernel hack to give `ps` a uniform way to enumerate processes. Each running process gets a directory named for its PID — that core design has not changed in 30 years."
- §32.3 "Each is a different *view* of the same underlying graph" — good metaphor, but the reader doesn't yet have a graph mental model. Either drop "graph" or define it ("the kernel internally tracks every device as a node in a graph of `struct device` pointers; the various `/sys/` subtrees are different traversals of that graph").
- §32.4 "What devtmpfs *doesn't* do" — useful section, but it never explains what udev *is*. A two-line intro: "udev (`systemd-udevd` on systemd systems) is the desktop-class device manager: a daemon that watches kernel uevents and runs rules from `/etc/udev/rules.d/`. Heavy (~1 MB binary + rules); on embedded we usually prefer mdev."

### MCU-engineer friendliness
- §32.1 "the file-as-interface pattern" is the headline insight for an MCU engineer — they spend their lives writing peripheral register accesses. Push harder on the analogy: "On an MCU, you read a sensor by reading a register at a fixed memory-mapped address. On Linux, you read the same sensor by `cat`-ing a file. The file *is* the register-access interface; the kernel translates the read into the right register/bus operation. `cat /sys/bus/iio/devices/iio:device0/in_voltage0_raw` is the same operation as your MCU's `adc->DR` read."
- §32.2 The list of files in `/proc/<pid>/` is good but doesn't explain *why* they exist as files. Add: "These don't exist as files on disk — every read causes the kernel to format the in-RAM struct into text and hand it to your `read()` syscall. Like reading a peripheral status register, but formatted as ASCII."
- §32.3 devtmpfs needs an MCU-style framing: "devtmpfs is the kernel saying 'here are all the peripherals I found at probe time, exposed as nodes you can `open()` and `read()`/`write()`.' It's the runtime equivalent of an MCU's peripheral base-address table — but populated by `device_create()` calls scattered across drivers."

### Missing examples / figures
- After the §32.2 first-look at `/proc/`, add an ASCII tree of 6-8 illustrative entries with one-line descriptions: `/proc/cpuinfo` (CPU model, features, BogoMIPS), `/proc/meminfo` (RAM totals), `/proc/<pid>/maps` (per-process address space), `/proc/<pid>/fd/` (open file descriptors), `/proc/interrupts` (IRQ counters), `/proc/cmdline` (kernel boot args). The current table is good but visually dense — a tree makes the structure pop.
- §32.3 deserves a small figure: `/sys/devices/` (the master tree) with arrows out to `/sys/bus/`, `/sys/class/`, `/sys/block/`, `/sys/dev/` showing they're all symlinked views of the same nodes.
- §32.4 — show `ls -l /dev/mmcblk0` so the reader sees `b` (block) vs `c` (character) distinction with actual output.
- A before/after of `ls /dev/sd*` around a USB plug-in (you have it!) — good, keep.
- An ASCII flow diagram for the mdev path: USB plug-in → kernel uevent → `/proc/sys/kernel/hotplug` invokes `/sbin/mdev` → mdev creates `/dev/sda` per `/etc/mdev.conf`.

### Technical errors / suspect claims
- §32.3 "kernel 2.5/2.6, ~2003" — sysfs was added in 2.5, stable in 2.6 (2003). Correct.
- §32.3 device-tree introspection example shows `fsl,imx6ul-uartfsl,imx6q-uartfsl,imx21-uart` concatenated without separators. In `/sys/firmware/devicetree/base/`, multiple compatible strings are NUL-separated and `cat` runs them together visually. Worth a footnote: "the bytes are NUL-separated; `cat` collapses them. Use `hexdump -C` or `tr '\0' '\n'` to see the actual strings."
- §32.4 "every `device_create()` or platform-device probe with a `class` adds a node" — pedantically, devtmpfs nodes come from registered character/block devices via `device_add()` → `device_create_sys_dev_entry()` → devtmpfs reaction. The Ch is correct in spirit but the function name is misleading; consider "every time the kernel registers a device with a `class` (`device_create()`, miscdevice, etc.) the devtmpfs node appears automatically."
- §32.4 `mdev.conf` example: the `mmcblk[0-9]p[0-9]      root:root   0660  @/etc/mdev/auto-mount.sh` line — `@` after `mode` runs the command *after* creation, correct. `$` runs *before*, `*` is described as "both" but BusyBox docs say `*` runs both with action set to the actual action. Worth verifying against the BusyBox docs (`docs/mdev.txt`); the chapter's description is roughly right but slightly simplified.

### Knowledge prerequisites missing
- "uevent" used in §32.4 without explaining what it is. One-liner: "a uevent is a kernel→userspace notification sent on a netlink socket (or via the `/proc/sys/kernel/hotplug` exec) whenever a device appears, disappears, or changes state."
- "tgid" mentioned in §32.2 ("a thread is a task whose pid != tgid") without prior context. Define: "in Linux, a *thread* is a task that shares its `tgid` (thread group ID) with other tasks — the tgid is the 'PID' that userspace sees, the task's individual pid is invisible to most tools."
- "sysctl" introduced in §32.2 without defining it as "the userspace tool for reading/writing `/proc/sys/`."
- "IIO" used in §32.3 without expansion — Industrial I/O subsystem. Define.
- "platform-device" used in §32.4 without forward-pointing to where it's defined (Ch36/37 perhaps?).

### Other
- §32.5 Lab item 5 says "find the I²C controller's `compatible` string." Helpful to give the expected output (`fsl,imx6ul-i2c\0fsl,imx21-i2c`) so the reader can self-check.
- §32.6 pitfall "Sysfs path stability assumptions" is excellent — keep.

## Ch33 — Init systems

### Readability
- §33.1 "That's it. Any program that does these five things is a legitimate PID 1." Good.
- §33.2 "It is **~1500 lines of C**, statically compiled into the BusyBox binary" — clarify "statically *linked* into" (it's one applet inside the busybox binary, not "statically compiled"). The reader is just learning the static/dynamic distinction.
- §33.3 the LSB block in the script "gives dependency hints — sysvinit can read these and compute service order" — actually classical sysvinit usually does *not* compute order from LSB headers; it's the `insserv` (or `update-rc.d --depends`) tool at install time that reads them and creates the S/K symlinks. Reword: "The LSB info block is read by `insserv` / `update-rc.d` at install time, which then sets the S/K symlink numbers. sysvinit itself just runs the symlinks in numeric order."
- §33.6 "This is the embedded equivalent of an MCU's `main()`." — good. Keep.

### MCU-engineer friendliness
- §33.1 — open with the MCU bridge: "PID 1 is the first user-space process the kernel creates. Think of it as the equivalent of your RTOS scheduler's `main()` task — except it's the *only* task the kernel starts, and every other process descends from it via `fork()`."
- §33.2 "you can read all the init code in an hour" — good selling point, push it: "compare to systemd's ~600k LOC. If you're used to MCU firmware where you read every line of your own code, BusyBox init is the only init that keeps that property."
- §33.4 systemd unit file example — explain the format briefly. "Like an INI file (sections in `[…]`, key=value pairs), parsed by systemd at boot. Equivalent to your MCU's startup file declaring init order — but declarative instead of imperative."
- §33.6 "no init" pattern — needs more emphasis on the watchdog story for MCU readers, since they're used to watchdogs. "Your app crashes → kernel sees PID 1 die → kernel panics → hardware watchdog (you set up in Ch51A) reboots the system. This is exactly the same fail-and-reset pattern an MCU uses; just one level up the stack."

### Missing examples / figures
- §33.3 needs a sysvinit `/etc/rc3.d/` directory listing to make the S/K symlink scheme tangible: `S10rsyslog -> ../init.d/rsyslog`, `S20networking -> ../init.d/networking`, `K20cron -> ../init.d/cron`, etc.
- §33.4 needs `systemctl list-units` or `systemctl status` output to ground the discussion in something runnable. The MCU reader has never seen these.
- A timing diagram for §33.5 boot-time row: bar chart `100 ms — 300 ms — 3-5 s` for the three init systems would visualize the trade-off instantly.

### Technical errors / suspect claims
- §33.1 "`SIGINT` (Ctrl-Alt-Del on a physical keyboard) → reboot" — kernel sends `SIGINT` to PID 1 on Ctrl-Alt-Del when `reboot(LINUX_REBOOT_CMD_CAD_OFF)` has handed it to userspace, correct. But many readers will know `SIGINT` as the "Ctrl-C" signal. Worth a parenthetical: "yes, both Ctrl-C-from-terminal and Ctrl-Alt-Del-from-console send `SIGINT` — the kernel uses the same signal to mean 'interrupt' in both cases."
- §33.2 "Reads `/etc/inittab` once at boot; re-reads on SIGHUP" — correct.
- §33.3 runlevels: "2 = multi-user, no networking (rarely used)" — on Debian, runlevels 2-5 are all equivalent by default; on Red Hat, 3 vs 5 differs (text vs graphical). Distro-dependent. Worth flagging: "the meaning of each runlevel is set by convention per distro — Red Hat differentiates 3 vs 5, Debian historically treats 2-5 as identical."
- §33.4 systemd RAM "~30 MB" — closer to 15-25 MB idle on a 32-bit ARM with a minimal install, 30+ MB with journald + logind + udevd combined. The figure is in the right ballpark; consider "~30 MB" → "20-40 MB depending on which satellites are enabled."
- §33.5 table row "Lines of code | ~1.5 K | ~5 K | ~600 K" — systemd is closer to 1.3-1.5M LoC including all components by recent counts. ~600 K may be just core systemd. Consider either dropping the count or footnoting "core systemd; with udev, journald, networkd, logind, etc., closer to 1.5M LoC."
- §33.5 "BusyBox boot time on i.MX6ULL: ~100 ms" — this is init-only, not full system to login prompt. Other chapters quote 3 s for full boot. Clarify in the table: "init startup time (kernel_init → first userspace command)" not "full boot."
- §33.6 "init=/path/to/myapp" — true that the kernel just `exec`s whatever `init=` points to. Worth noting: your app needs to handle `SIGCHLD` (reap zombies) or you'll leak. The current text says "set up signal handlers for SIGTERM" but doesn't mention SIGCHLD — important enough to add.

### Knowledge prerequisites missing
- "zombie" used in §33.1 without explanation. One-line: "a zombie process is a child that has exited but whose parent hasn't `wait()`ed for it yet — kernel keeps a stub around so the parent can read the exit code. If never reaped, the stub never goes away."
- "reparent to PID 1" needs a sentence. "When a process's parent dies before it, the kernel changes the dead parent to PID 1 — so PID 1 is responsible for cleaning up *every* orphan in the system."
- "cgroups" used in §33.4 without defining. Forward-ref Ch35C §35C.2 or define inline.
- "socket activation" is mentioned twice but never explained: "systemd creates the listening socket on behalf of the service; the service starts only when the first client connects. Like lazy initialization for daemons. Useful when you have 50 services that mostly idle."
- "target" used in §33.4 unit-file example (`multi-user.target`) — needs a one-line gloss: "a *target* in systemd is a grouping (e.g., 'we've reached the point where networking is up'); roughly equivalent to a sysvinit runlevel."
- "respawn storm" pitfall mentioned in §33.9 — concept is clear, but the term `respawn` was defined only in Ch31; forward/back-ref.

### Other
- §33.5 table is missing a "default on" row for the major embedded BSPs (NXP, ST, TI, RPi). NXP's Yocto BSP defaults to systemd; Buildroot defaults to BusyBox; Raspberry Pi OS uses systemd. Worth one row to anchor the reader.
- §33.7 recommendation is good ("BusyBox init is the default for this book"). Worth adding "if you're working at a company that already has a systemd-based BSP, don't fight it — Ch33's analysis is for *new* designs."

## Ch34 — libc, dynamic linking, and the loader

### Readability
- §34.1 "Embedded Linux gives you a real choice of C library, unlike a typical desktop where you get glibc and that's it." — good opener.
- §34.2 "That second point is the heart of dynamic linking and worth understanding precisely." — agreed, but the next paragraph immediately dives into `readelf` output without first stating the punchline. Restate the punchline first: "Punchline: when you run a dynamically-linked binary, the *first* program that actually executes is `/lib/ld-linux-armhf.so.3` — *not* your binary. The kernel reads the INTERP segment, finds that path, and `exec`s it instead. Your binary becomes an argument to ld-linux. Only after ld-linux finishes loading libraries does control jump to your `_start`."
- §34.3 "lazy binding" paragraph is good but reads dense. Consider one example: "The very first call to `puts` goes to the PLT stub → lookup resolver → ld-linux finds `puts` at address X → writes X into the GOT → jumps to X. The *second* call to `puts` reads X directly from the GOT and jumps — one indirect load instead of a full resolution."
- §34.5 "Right column is *load addresses* — where each `.so` was `mmap`'d into the process's address space." — good. Keep.

### MCU-engineer friendliness
- §34.1 — needs an MCU bridge upfront: "On an MCU you usually link statically against `newlib` or `picolibc` and ship one ELF. On Linux you typically dynamically link against a `libc.so.6` that lives separately on the target's filesystem. This chapter is about that separation: what's in the lib, how the binary finds it at runtime, and what breaks when it can't."
- §34.2 PLT/GOT — for MCU readers, frame it as: "PLT is a thunk table (like an MCU's interrupt vector but for function calls). GOT is a pointer table the thunks indirect through. The first call resolves the pointer; subsequent calls are one indirect load. The compiler/linker emit the thunks automatically when you call across .so boundaries."
- §34.3 "ASLR shuffles them if enabled" — for MCU readers ASLR is unknown. One line: "Address Space Layout Randomization — kernel chooses different library load addresses each run, so attackers can't predict where `system()` is. On embedded, often disabled for determinism."
- §34.7 the trade-off table is good. Add an MCU framing: "Static linking on Linux = what you've always done on MCU — one self-contained binary. Dynamic linking = library code lives on the filesystem at runtime, shared across binaries — pays back when you have many binaries needing the same library."

### Missing examples / figures
- §34.2 needs an ASCII diagram of "what happens when you exec a dynamically-linked binary":
  ```
  exec("/usr/bin/hello") → kernel reads ELF header
                         → reads INTERP = "/lib/ld-linux-armhf.so.3"
                         → mmaps ld-linux into a fresh address space
                         → jumps to ld-linux's entry point with argv=[hello]
                         → ld-linux reads hello's DT_NEEDED entries
                         → mmaps libc.so.6, etc.
                         → relocates GOT/PLT
                         → jumps to hello's _start
                         → _start calls __libc_start_main()
                         → which calls your main()
  ```
- §34.5 — show a `readelf -d hello` side-by-side with `ldd hello` so reader sees the same info from two angles.
- §34.7 — sample `ldd` output for both static and dynamic builds of "hello world" side-by-side. The lab mentions this but the chapter never shows it.

### Technical errors / suspect claims
- §34.1 table "Static-linked 'hello world' | ~700 KB | ~30 KB | ~50 KB" — glibc static hello-world is closer to ~600-900 KB depending on version and arch; musl ~25-30 KB on ARM. Reasonable.
- §34.2 program headers example: "Elf file type is DYN (Position-Independent Executable file)". Worth a note: PIE-vs-EXEC is a separate axis from dynamic-vs-static. Modern toolchains default to PIE for ASLR. Briefly explain: "DYN here means PIE; ld-linux can mmap this binary at a random base address. A non-PIE dynamic executable would show type EXEC."
- §34.2 "Reads `hello`'s DYNAMIC segment. This contains a table of needed libraries:" — strictly, the DYNAMIC segment is a table of dynamic entries (NEEDED, SYMTAB, STRTAB, RELOCS, etc.). NEEDED is just one entry type. Minor pedantic point but worth tightening.
- §34.3 "`R_ARM_GLOB_DAT` entries are data-section relocations" — actually GLOB_DAT applies to GOT entries (not arbitrary data). Tighten.
- §34.5 `LD_DEBUG=libs` output sample shows glibc-style output; musl's dynamic linker uses `LD_DEBUG_OUTPUT=...` differently and lacks some categories. Worth one-line: "this is glibc's `LD_DEBUG`; musl has a smaller set."
- §34.7 table row "Boot time | Slightly faster (no linker startup) | Slightly slower" — for a single binary the difference is real but tiny (5-50 ms). Worth quantifying: "~10-50 ms per dynamic binary on i.MX6ULL for ld-linux startup. Negligible at boot if you start one binary; visible at boot if you start fifty."
- §34.4 "On embedded systems running BusyBox, `ldconfig` is often skipped" — true; mention that BusyBox doesn't ship `ldconfig` by default (it's a separate applet that has to be enabled in BusyBox config).
- §34.9 pitfall "Mixed glibc and musl on one rootfs. Don't. They share the `libc.so.6` SONAME and conflict." — both *can* coexist if one is at `/lib/ld-linux-armhf.so.3` (glibc) and the other at `/lib/ld-musl-armhf.so.1` (musl) — they have different SONAMEs (`libc.so.6` vs `libc.musl-armhf.so.1`). The pitfall as stated is misleading. Reword: "Don't try to use the same `libc.so.6` symlink for both. Either pick one libc per rootfs, or put musl binaries in their own prefix with their own loader path."

### Knowledge prerequisites missing
- "SONAME" used in §34.4 implicitly but never explicitly defined. Define: "SONAME = the name the dynamic linker looks for. Encoded in the ELF; visible as `(SONAME)` in `readelf -d`. Conventionally `libfoo.so.N` where N is the ABI version."
- "relocation" used in §34.3 without definition. One line: "A relocation is a placeholder address in the ELF; the dynamic linker resolves and patches it at load time. Different relocation types tell the linker how to compute the value (e.g., absolute, GOT-relative, jump slot)."
- "ELF" itself never expanded. First use: "Executable and Linkable Format — the binary format Linux uses, equivalent to Windows' PE or Mach-O on macOS. On MCU you might know it from your toolchain's `.elf` outputs."
- "NSS" referenced in §34.4 — defined briefly in Ch31 §31.3 callout. Forward-ref.
- "setuid" used in §34.9 — explain briefly: "setuid binaries run as their file-owner (often root) regardless of who invoked them. `passwd` is the classic example."

### Other
- §34.6 RPATH section — recommend showing `chrpath` / `patchelf` to inspect and modify after the fact. Useful tool, common need.
- §34.8 Lab item 3 "Break a dynamic binary on purpose. Move /lib/libm.so.6 somewhere" — caution the reader not to do this with an NFS rootfs they're actively using as `/`, since deleting `libm.so.6` from under a running system kills currently-loaded processes' future mmap calls and is recoverable but messy.
- §34.9 the `ldconfig` pitfall — note that this is a glibc-only issue; musl's loader doesn't use a cache file.

## Ch35 — Buildroot

### Readability
- §35.1 list of "things Buildroot is good/not good at" is well-structured. Keep.
- §35.4 "where each package was unpacked and built. When a build fails inside a package, this is where you go." Good operational guidance.
- §35.6 "Re-deploy and `nano` is now on the target. Total time for adding a small package: ~30 seconds." — slightly misleading; ~30 s is just the package's own build, not the rootfs re-pack and NFS re-deploy. Tighten: "build time for nano itself ~30 s; rolling the new rootfs.tar and updating the NFS export adds a few more."
- §35.7 the three customisation mechanisms section heading "without forking" is jargony for an MCU reader. Reword: "Customising your rootfs without modifying Buildroot itself."
- §35.11 pitfall "make clean is not enough" — the multi-level clean explanation is great. Keep.

### MCU-engineer friendliness
- §35.1 — open with MCU framing: "Think of Buildroot as a Makefile-driven IDE for entire embedded Linux images. The way your MCU IDE knows how to compile your C, link your startup file, and produce a `.bin` you flash, Buildroot knows how to build a cross-toolchain, kernel, U-Boot, and rootfs — and produce a `rootfs.tar` you flash. The `.config` file is your project settings."
- §35.5 reading the defconfig — the MCU reader has never read a Kconfig defconfig in their life. Add: "Buildroot uses *Kconfig*, the same configuration system the Linux kernel uses. `make menuconfig` opens a TUI; the resulting settings are saved in `.config` as `BR2_xxx=y` / `=n` / `="string"`. The `defconfig` files in `configs/` are pre-canned `.config` files for known boards."
- §35.7 — package definition `myapp.mk` example uses `$(eval $(generic-package))` without explaining the indirection. One line: "the `generic-package` macro at the end is what wires this `.mk` into Buildroot's dependency graph — without it, your package is invisible to `make`."
- §35.9 comparison table is good. Add: "If Ch31's manual rootfs felt like writing your MCU startup file from scratch, Buildroot is using your IDE's project wizard to do the same thing."

### Missing examples / figures
- §35.4 — a *runtime* version of the output tree showing what `make` writes when, e.g., a Mermaid-style flow: `dl/ → output/build/ → output/staging/ → output/target/ → output/images/`. The current section is a static layout.
- §35.6 — show the actual `make menuconfig` ASCII screen (a small mock) for the "Target packages → Text editors → [*] nano" navigation. The MCU reader hasn't used menuconfig; a screenshot-as-ASCII would orient them.
- A short example diff of "what changes in `.config` when you flip one option" — illustrates that `.config` is just a flat key-value file.

### Technical errors / suspect claims
- §35.1 "A no-extras BusyBox rootfs from Buildroot is ~3 MB. Same Yocto build is ~30 MB." — Yocto's `core-image-minimal` is closer to 8-15 MB depending on init system and packages. ~30 MB is more like `core-image-base`. Tighten or qualify.
- §35.3 "First build on a 4-core machine: 30-60 minutes." — depends heavily on toolchain choice. With an external pre-built toolchain (`BR2_TOOLCHAIN_EXTERNAL=y`), more like 10-20 minutes. With the internal toolchain (default, builds gcc + glibc), 30-60 min is right.
- §35.5 `BR2_LINUX_KERNEL_INTREE_DTS_NAME="nxp/imx/imx6ull-14x14-evk"` — the DTS path inside the kernel source moved when arm DTS subdirs were created (kernel v6.5+); older kernels would use `imx6ull-14x14-evk` without the `nxp/imx/` prefix. Worth a note.
- §35.5 `BR2_LINUX_KERNEL_CUSTOM_VERSION_VALUE="6.6"` — Buildroot defconfig may pin a specific kernel point release (e.g., `6.6.10`). Confirm and tighten.
- §35.6 adding `nano` — Buildroot's nano needs `ncurses`; the rebuild "re-roll" is mentioned but not the dependency-pull-in. Add: "Buildroot also pulls in ncurses (a dependency); the first time you add a package that needs it, you'll see ncurses being built too."
- §35.10 Lab item 1 — "udev instead of mdev" — Buildroot's `imx6ullevk` defconfig actually uses `mdev` by default (the default `BR2_ROOTFS_DEVICE_HANDLING=mdev`). Confirm before publishing; if defconfig has changed to `eudev`, update.

### Knowledge prerequisites missing
- "Kconfig" mentioned in §35.1 — undefined for the MCU reader. Define on first use (see suggestion above).
- "defconfig" used everywhere — define once: "a *defconfig* is a partial `.config` containing only non-default settings. Small and clean to commit to git."
- "BSP" used in §35.7 ("multi-product BSPs") — define: "Board Support Package — the set of files (DTS, kernel patches, U-Boot config, defconfig) that enable a particular board."
- "Yocto / OpenEmbedded" mentioned several times — at first use, one-liner: "Yocto/OpenEmbedded is the other major embedded-Linux build system. Bigger, more flexible, harder to learn. Beyond this book's scope; we mention it for context."
- `BR2_TARGET_GENERIC_ROOT_PASSWD` is mentioned nowhere — but the persona note says BR2 Kconfig style needs explanation. If you use any `BR2_*=y` examples (you do, in §35.5), accompany with a sentence: "the `BR2_*` symbols are Kconfig settings; `=y` means selected, `=n` deselected, `="string"` for string values. Buildroot uses the same Kconfig system as the Linux kernel — the menuconfig UI is the same."

### Other
- §35.8 "savedefconfig" is a critical hygiene step and only gets one paragraph. Worth emphasising: "after every menuconfig change you intend to keep, run `make savedefconfig`. The resulting file is what you commit; the `.config` itself you do *not* commit (it's full of defaults that change with Buildroot version)."
- §35.10 Lab item 6 "Read output/build/busybox-*/. ... identify any patches Buildroot applied" — useful, but explain how: `ls package/busybox/*.patch` shows what Buildroot adds. Otherwise the reader doesn't know where to look.
- §35.11 "Building as root. Buildroot refuses to build as root" — true; worth saying *why* (some package build scripts behave differently when uid=0, e.g., file permissions get set to root, breaking when copied to target).

## Ch35A — Ubuntu-base

### Readability
- §35A.1 table headed "When this is the right answer" with check marks is clear. Keep.
- §35A.3 "`binfmt-support` registers it with the kernel so that when the kernel sees `exec("/usr/bin/ls")` and `ls` is an ARM binary, it transparently runs `qemu-arm-static /usr/bin/ls` instead." — clearest single sentence in the whole part. Good.
- §35A.5 "you are now inside a fake ARM machine" — punchy. Keep.
- §35A.6 "every command you're used to is there." — slightly informal; consider "every Debian/Ubuntu command you're used to is there — full bash, python3, apt, ssh, systemctl."
- §35A.10 pitfall list reads well. Keep.

### MCU-engineer friendliness
- §35A.1 — needs an explicit "what is Ubuntu" framing. An MCU engineer may not realize Ubuntu-the-rootfs is just *files in a tarball*. Add: "Ubuntu is just a *collection of files* on top of a Linux kernel — the kernel comes from us (Ch24), the files come from Canonical's release. Ubuntu-base is the minimal version of those files: ~80 MB of binaries + libraries + scripts, with no GUI."
- §35A.3 — `chroot` itself is undefined for the MCU reader. Add: "`chroot` changes the apparent root directory for a process. Inside the chroot, `/` *is* `ubuntu-rootfs/`; the host filesystem is invisible. Like switching the bootloader's memory-map base address — same instructions, different addresses."
- §35A.5 — explain `sources.list` for the unfamiliar: "Debian/Ubuntu's `apt` reads `/etc/apt/sources.list` for URLs of package archives. Each `deb http://… jammy main …` line says: fetch packages tagged `jammy` (Ubuntu 22.04's codename), from this URL, in the `main` component."
- §35A.5 "systemctl enable serial-getty@ttymxc0.service" — explain why this matters: "Ubuntu has no `/etc/inittab` (that's BusyBox's world); instead, systemd has a `serial-getty@.service` template, instantiated per-tty. Enabling it for `ttymxc0` says 'spawn a login prompt on the serial console at boot.'"
- §35A.8 comparison table is good. Add an MCU framing line above it: "These three are not 'better/worse' — they are different points on the size/familiarity trade-off. For your first dev board, Ubuntu-base; for a production unit, Buildroot."

### Missing examples / figures
- §35A.3 needs a one-figure timeline of the qemu-binfmt-chroot flow:
  ```
  $ chroot ubuntu-rootfs /bin/bash
       │
       ├── kernel sees /bin/bash is an ELF for ARM
       ├── binfmt_misc registered "ARM ELF → /usr/bin/qemu-arm-static"
       ├── kernel actually runs: /usr/bin/qemu-arm-static /bin/bash
       └── inside the chroot, /bin/bash sees /lib (the ARM /lib in the rootfs)
  ```
- §35A.5 — show actual `apt update` and `apt install` output (truncated). The MCU reader has never seen apt output; concrete examples help.
- A figure showing where each piece lives during the chroot: host `/proc` bind-mounted to `rootfs/proc`, host `/dev` bind-mounted, etc.

### Technical errors / suspect claims
- §35A.2 "Ubuntu 22.04 LTS … supported through April 2027 (ESM 2032)" — correct as of 22.04 release.
- §35A.5 `apt install -y sudo vim openssh-server kmod net-tools ifupdown iputils-ping rsyslog less htop language-pack-en-base` — "~50 MB of additional packages" — closer to 70-100 MB on disk with all dependencies pulled. Worth re-measuring.
- §35A.6 "Boot time on i.MX6ULL: ~12-15 seconds from `bootz` to login prompt (vs ~3 s for BusyBox)" — plausible for a default Ubuntu-base install with systemd, but optimisations (`systemd-analyze`, mask unnecessary services) easily knock it to 6-8 s. Mention this as a foreshadow to the Lab §35A.9 item 4.
- §35A.8 table row "Boot to login | < 3 s | < 5 s | ~12 s" — consistent with §35A.6 and §33.5. Good.
- §35A.10 pitfall "Choosing the wrong armhf … Downloading arm64 and trying to run it on a 32-bit i.MX6ULL" — true; worth noting how to verify: `file ubuntu-base-*.tar.gz`'s name carries `armhf` vs `arm64`. Also: i.MX6ULL is ARMv7-A; ubuntu-ports `armhf` requires VFPv3+; iMX6ULL has VFPv4-D16 so it's fine.

### Knowledge prerequisites missing
- "qemu-user-static" — needs a one-paragraph definition before §35A.3. "qemu has two modes: *system emulation* (emulates a whole machine including BIOS, IO devices) and *user emulation* (emulates only the CPU, syscalls passed through to the host kernel). `qemu-user-static` is the user-mode emulator, statically linked so it works inside arbitrary rootfses. It runs *one* foreign-arch binary at a time."
- "binfmt_misc" — define: "Linux kernel feature that lets you register handlers for new binary formats. When the kernel sees an `exec` of a registered format (e.g., ARM ELF), instead of erroring, it runs the registered handler on the binary."
- "chroot" — define on first use (see above).
- "ports.ubuntu.com" vs `archive.ubuntu.com` — explain: Ubuntu hosts armhf/arm64/ppc64el at `ports.ubuntu.com`; the main `archive.ubuntu.com` only has amd64 and i386.
- "ESM (Expanded Security Maintenance)" mentioned without expansion in §35A.2.
- "snap" / "snapd" used in §35A.9 lab without defining it. One sentence: "Ubuntu's containerized package format; heavyweight on embedded; disabling it speeds boot."

### Other
- §35A.4 mount-and-chroot script — for an MCU engineer the `sudo mount --bind` operations are alien. Add a 2-line comment line above each mount explaining what it does: "make the host's /proc visible inside the rootfs (so apt's post-install scripts that read /proc work)".
- §35A.10 pitfall about `systemctl start` inside chroot — good catch; worth elevating to a §35A.5 sidenote since the chapter does `systemctl enable` inside the chroot.
- §35A.11 — `debootstrap` mentioned as "Debian's equivalent of `ubuntu-base.tar.gz`". Actually debootstrap is the *tool* that builds a Debian rootfs by pulling packages from the archive; Ubuntu publishes `ubuntu-base.tar.gz` instead of expecting you to debootstrap. Tighten: "`debootstrap` is the tool Canonical uses internally to *generate* `ubuntu-base.tar.gz`. You can run it yourself to build a custom Debian rootfs from scratch."

## Ch35B — Read-only rootfs + overlayfs

### Readability
- §35B.1 "you have:" list of corruption modes is clear and concrete. Keep.
- §35B.2 the ASCII overlayfs diagram (lowerdir/upperdir/workdir) is excellent — keep.
- §35B.4 the `/init` script for the initramfs is the densest part of the chapter — 30 lines of shell with little annotation. Add inline comments explaining what each `mount`, `mount --bind`, `pivot_root` does in MCU-translatable terms.
- §35B.5 "Compare with the same test on a RW rootfs: half the time you get a clean boot; half the time `fsck` finds something" — slightly hyperbolic. With ext4's journal it's more like "9 in 10 clean, 1 in 10 needs auto-repair, occasional unrecoverable." Tighten the claim.

### MCU-engineer friendliness
- §35B.1 — open with MCU bridge: "MCU engineers shipping products with power-loss exposure usually pick this pattern unconsciously: 'EEPROM is read-only at runtime, write only via explicit erase-and-program cycle.' Linux's equivalent is a read-only rootfs. Same idea, same reason: power-loss safety."
- §35B.2 — the *purpose* of overlayfs needs a one-liner an MCU person can map onto. "Overlayfs lets two filesystems pretend to be one. The lower is read-only (the original); the upper accumulates changes (the writable side). Like the way your MCU might use a 'staging' area in RAM that overrides the flash defaults until you commit them — but in Linux, the union is transparent to every program."
- §35B.4 — `pivot_root` is a foreign syscall. Define: "`pivot_root new_root put_old` swaps the current `/` with `new_root`, then moves the old `/` to `put_old`. After `pivot_root`, processes see the new root; the old root is unmounted later. Used in initramfs to hand off from the early init to the real rootfs."

### Missing examples / figures
- §35B.3 — show `mount | head -2` output for the Pattern A case so the reader sees `ext4 ro` and `tmpfs rw` lines together.
- §35B.4 — show the `mount` output *after* overlay setup, so reader sees the `overlay` filesystem type in the table.
- A figure showing the partition layout in §35B.4 alongside the mount tree:
  ```
  /dev/mmcblk1p2 (ro ext4)         /dev/mmcblk1p3 (rw ext4)
        │                              │
        │ mounted at /rofs             │ mounted at /overlay
        │                              │
        └─── lowerdir ──┐    ┌─── upperdir
                       overlayfs
                          │
                         /etc (writable)
  ```
- An example `/etc/init.d/S00-overlay` for the "simpler approach" briefly mentioned in §35B.4 — currently only the initramfs path has code.

### Technical errors / suspect claims
- §35B.2 Pattern A "`/var/log` on tmpfs" — fine, but most systemd-based systems put logs in `journald` which auto-rotates; for BusyBox+rsyslog you need explicit log rotation. Already covered in §35B.8 pitfalls; consider moving to the body for visibility.
- §35B.4 "the cleanest place is an initramfs that does the overlay setup, then exec's the real init" — agreed. Worth noting: this initramfs needs to *contain* `mount`, `pivot_root`, and a shell — i.e., busybox-statically — so the chain becomes "busybox-init in initramfs → overlay-setup → switch_root or pivot_root → real init on the overlayed rootfs." (Modern kernels prefer `switch_root` for initramfs handoff; `pivot_root` is the older mechanism.)
- §35B.4 the script does `pivot_root /merged-root /merged-root/oldroot` then `exec /sbin/init`. After `pivot_root`, the old root (now at `/oldroot`) needs to be unmounted lazy or processes will hold references. Worth a comment line: "in a production initramfs you'd `umount -l /oldroot` after the exec; omitted here for clarity."
- §35B.4 `mount --bind /rofs /merged-root` then bind-mounts on top — this works but the more idiomatic pattern is to use overlayfs *as* the rootfs (one overlay covering all of `/`) rather than three sub-overlays. Both approaches are valid; the chapter chose the sub-overlay approach. Worth a sentence justifying: "we could have one overlay over the entire rootfs, but per-directory overlays make it easier to reason about what's in upper and lets us put `/home/` on a different partition if we wanted."
- §35B.4 the simple alternative (S00-overlay in rcS) is dismissed as "fragile" without details. Worth one sentence: "if you do it from `rcS`, by the time the script runs, the rootfs is already mounted RW; you'd need to `mount -o remount,ro /` first, which can fail if any file is open RW."
- §35B.8 pitfall "Overlay `workdir` must be on the same filesystem as `upperdir`. Different filesystems for `workdir` and `upperdir` is an immediate mount failure." — correct, and worth saying why: "the workdir holds in-progress copy-up files; overlayfs uses `rename()` between workdir and upperdir, which only works within one filesystem."
- §35B.8 pitfall on `pivot_root` — correct.

### Knowledge prerequisites missing
- "page cache" / "buffers flushed" mentioned in §35B.1 — undefined. One line: "Linux holds recent writes in RAM (the *page cache*) and flushes them to disk lazily. If power dies before the flush, the disk has older data than RAM showed. The journal protects metadata; file *data* can still be partially written."
- "initramfs" used in §35B.4 — defined in Ch29 per intro; forward-ref.
- "switch_root" — never mentioned but is the modern alternative to `pivot_root`. Brief mention.
- "factory reset" — for the MCU reader, frame it: "On MCU, factory reset usually means erasing EEPROM. On Linux with overlayfs, factory reset means erasing the overlay partition — the original rootfs is untouched, so the device returns to factory state without reflashing anything."
- "ext4 journal" mentioned in §35B.1 — define briefly: "ext4 maintains a small log (journal) of pending metadata changes; on next mount the kernel replays the log to bring metadata back to a consistent state. Protects directory/inode structure, not file *contents*."

### Other
- §35B.6 "factory reset" section is excellent — a very real production feature explained in a few lines. Worth promoting from §35B.6 to its own subsection title that mentions the "hold-button-at-boot" UX pattern.
- §35B.7 Lab item 3 — "Power-cycle 100 times at random intervals" — this is a legit reliability test but assumes the reader has a setup for automated power cycling. Mention that the cheap version is a USB-controlled power relay (or a hand pulling the SD card).
- §35B.9 — recommend mentioning `dm-verity` for read-only rootfs integrity (each block is hash-verified). Used in Android, ChromeOS; can be added later as a future-direction pointer.

## Ch35C — Containers on embedded

### Readability
- §35C.2 "**Docker, Podman, containerd, and CRI-O all do the same thing**" — strong, clear. Keep.
- §35C.2 "Podman has no daemon — `podman run` directly spawns the container process." — accurate and useful contrast.
- §35C.5 "A real Alpine Linux 3.x container, pulled, run, exited, cleaned up — in roughly 30 seconds plus download time." — concrete.
- §35C.8 the costs section is honest. Keep.
- §35C.9 "Image swap is atomic at the container level: either the new image is running or the old one is. Much cleaner than 'extract a tarball into /opt/myapp/' updates." — good.

### MCU-engineer friendliness
- §35C.1 — open with framing: "If your firmware-update story has ever been 'flash a new bin to a separate slot, jump to it, fall back on watchdog if it crashes,' you already understand the *spirit* of containers. They're the userspace equivalent: ship a self-contained app package, run it isolated, swap it atomically. The kernel does the isolation; you ship the app as an image."
- §35C.2 — namespaces, cgroups, overlayfs all need MCU-friendly framing:
  - **namespaces**: "the kernel keeps separate 'views' per process group. A process in a new PID namespace sees only the processes that share its namespace and thinks it's PID 1. Like running multiple instances of the same firmware on the same MCU, each with its own private memory and devices — except it's just one kernel partitioning views."
  - **cgroups**: "resource limits per process group. CPU bandwidth, memory caps, IO weights. Enforced by the kernel scheduler / allocators. Like the MPU on an MCU, but for CPU time and memory rather than just memory regions."
  - **overlayfs**: already covered in Ch35B; forward-ref.
- §35C.3 — kernel config block has 20+ symbols. Add: "Don't worry about every symbol; the headline ones are NAMESPACES, USER_NS, CGROUPS, OVERLAY_FS, BRIDGE/VETH. The rest are the satellites those need."
- §35C.6 — the bind-mount-sysfs example is good but doesn't say *why* the container needs sysfs explicitly. Explain: "the container has its own /sys (because of mount namespace), which is empty by default. Bind-mounting host's `/sys/class/leds/` into the container exposes only those host files; reads/writes go directly to the host kernel."

### Missing examples / figures
- §35C.2 — a layered figure of "what a container *is* underneath":
  ```
          Process
        ┌─────────┐
        │  app    │   ← regular user-space binary
        └─────────┘
          │
   ┌──────┴───────┐
   │ namespaces   │   ← PID, NET, MOUNT, UTS, IPC, USER, CGROUP
   │ cgroups      │   ← CPU/MEM/IO limits
   │ overlayfs    │   ← layered rootfs view
   └──────────────┘
          │
        kernel
  ```
- §35C.3 — `make menuconfig` paths for each CONFIG symbol (e.g., "General setup → Namespaces support → User namespaces"). Helps the reader who needs to flip these on.
- §35C.5 — concrete output from `podman ps`, `podman images`, `podman info | grep -i graph` to give the reader a feel for the CLI.

### Technical errors / suspect claims
- §35C.2 "Daemonless. Docker has a privileged daemon that runs as root and listens on a socket. Podman has no daemon — podman run directly spawns the container process." — accurate. (Podman does use `conmon` per container as a monitor, but no central daemon.)
- §35C.3 `cgroup_no_v1=all systemd.unified_cgroup_hierarchy=1` — correct for forcing v2.
- §35C.4 "On a Buildroot rootfs, enable `BR2_PACKAGE_PODMAN`." — Buildroot does have a podman package as of recent versions (added ~2021). Confirm against Buildroot 2024.02. (Buildroot 2024.02 does have `BR2_PACKAGE_PODMAN`.)
- §35C.4 output sample shows "podman version 4.3.1" and "buildahVersion: 1.28.2" — match plausibly to early-2023 versions. Recent Buildroot LTS may have Podman 4.7+; worth refreshing or marking version-as-of-date.
- §35C.5 "Alpine images for armv7 are ~3-5 MB compressed, ~10 MB on disk." — alpine:latest armv7 manifest is ~3 MB compressed, ~7 MB on disk. Tighten.
- §35C.6 `podman run --rm -v /sys/class/leds:/sys/class/leds:rw led-blinker` — the bind-mount approach works. Note that the container's `/sys` is typically mounted as a *new* sysfs by the runtime (different namespaces), so the bind mount overlays on top of the per-container sysfs. Worth one line: "the container's /sys is the container's own — your bind mount replaces that specific subtree."
- §35C.8 "Each container adds ~10-20 MB at minimum." — for a minimal Alpine container with one Python process, more like 5-15 MB RSS. The figure is in the right ballpark.
- §35C.9 "podman rollback" is shown as if it's a real command — Podman doesn't have a built-in `rollback`; you'd typically run a previous version of the image. Fix the example or annotate "or pull v1.0 again" — actually the chapter does annotate this; tighten the apparent command line: change `podman rollback ...` to a comment `# (Podman doesn't have rollback; re-pull and re-run the previous image)`.
- §35C.11 pitfall "`USER_NS` disabled … rootless mode fails with 'no subuid map'" — actually the more common symptom of `USER_NS=n` is "operation not permitted" on namespace creation; the subuid map issue is a separate `/etc/subuid` config problem. Worth disentangling: missing `CONFIG_USER_NS` and missing `/etc/subuid` entries are different failures.

### Knowledge prerequisites missing
- "namespace" / "cgroup" / "overlayfs" — addressed in §35C.2 but needs MCU framing (see above).
- "OCI" first used in the §35C title and the §35C.1 sentence ("running OCI containers"). Expand on first use: "Open Container Initiative — the standards body for container image format and runtime interface. Docker, Podman, containerd all consume OCI images."
- "rootless" used in §35C.2 — define: "a rootless container is one that runs as a non-root host user, using user namespaces to *appear* root inside the container without being root on the host. Better security model than 'everything as host root.'"
- "Alpine Linux" mentioned in §35C.1 and used as the example image — one-line gloss: "Alpine is a minimal Linux distribution built around musl libc and BusyBox; container images are ~5 MB compressed, ~10 MB extracted. The de-facto default for small container images."
- "veth" used in §35C.3 — define: "virtual ethernet pair; a kernel object that looks like two NICs connected by a virtual cable. One end is in the container's net namespace, the other in the host's, bridged to the outside."
- "capability" used in §35C.6 ("`--cap-add SYS_RAWIO`") — define: "Linux *capabilities* are fine-grained privileges (formerly bundled as 'root'). `CAP_NET_ADMIN`, `CAP_SYS_RAWIO`, etc. Containers normally run with a reduced set; `--cap-add` grants extra ones explicitly."
- "registry" used in §35C.5 and §35C.9 — define: "a server that hosts container images. Docker Hub is the default; you can run your own (`docker-registry`, `harbor`)."

### Other
- §35C.4 the `containers.conf` snippet uses TOML inline. Worth saying so (and "TOML is a config format like INI but more strict"); MCU engineers may not have seen it.
- §35C.6 — running the LED-blinker container as root (default) is the easy path. Worth mentioning the *correct* permission story: `chown root:gpio /sys/class/leds/led0/brightness` on the host + `--user gpio` for the container.
- §35C.7 `graphroot = "/data/containers/storage"` — `/data/` is referenced as a real persistent partition that doesn't exist in any previous chapter's rootfs layout. Either point back to Ch35B Pattern B (which introduces `/data/`) or add a footnote: "`/data` here is a persistent partition you'd set up in your fstab; we use it as the convention in this book."
- §35C.10 Lab item 4 "Bind-mount sysfs" — typo `--v` should be `-v`.
- The end-of-chapter "End of Part V" wrap-up is great — a nice cap. Keep.
