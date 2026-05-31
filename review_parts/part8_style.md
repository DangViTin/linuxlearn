# Part VIII — Style/ESL Review

## Cross-cutting patterns

- **Em-dash chaining** dominates. Many sentences chain two or three clauses with `—`. Half of them should be periods, some commas. Two em-dashes in one sentence appears in every chapter.
- **"Not X — but Y" / sledgehammer "This is X. This is Y."** — the chapter intros lean on this rhetorical move repeatedly. Pick one per chapter, not five.
- **"the right tool for the right symptom" / "the bread-and-butter" / "the killer for ..." / "the secret weapon"** — marketing voice. Use technical voice.
- **Buzzwords**: `indispensable`, `incomparable`, `essential`, `canonical`, `the survivor`, `the universal X`, `the surgical X`, `surgeon's tool`, `medical kit`, `autopsy`, `flashlight`, `the workhorse`, `the modern X`. Heavy across Ch 118 and 119 especially.
- **Royal "we"** is moderate but still present in intros / pivot lines ("we wire JTAG...", "we do both", "you'll debug ...").
- **Hedging filler**: "Important", "Killer for ...", "Master these and ...", "Once you've used X, you wonder how anyone ...". Drop or use once.
- **Footnote-as-emphasis bold inside lists** ("**Important — `--multi` mode**", "**pr_debug is the secret weapon**"). Bold for emphasis is overused; reserve for genuinely critical lines.
- **Triplet rhythm** ("Three things X is good at: 1... 2... 3..." / "Three main modes:"). Used in Ch 118 (Wiring + Pinout + Open-OCD config), Ch 120 (perf three modes).
- **"Master these and you ..." / "Once you ... it ..."** — promise-style closing line ends multiple sections. One per chapter.

---

## Ch 118 — JTAG, OpenOCD, GDB

### AI wording / sledgehammer / buzzwords
- > "the day your bare-metal LED doesn't blink and `printk` isn't an option (because the kernel hasn't started), JTAG is the only ground truth. Same when U-Boot hangs in DCD execution and you have nothing to print to. Same when the kernel oopses in early-boot before serial init."
  - Rewrite: cut one of the three "Same when" lines, and the "ground truth" phrasing. "When the LED doesn't blink and `printk` isn't an option (the kernel hasn't started yet), JTAG is the only way in. The same is true when U-Boot hangs in DCD execution, or the kernel oopses before serial init."
- > "This is the difference between "I guess the boot fails somewhere in CCM init" and "I see XTAL_24M is at 0 mV; the crystal isn't running.""
  - Rewrite: classic "Not X. Y." sledgehammer. Soften: "It's the difference between guessing the boot fails somewhere in CCM init, and seeing that XTAL_24M is at 0 mV because the crystal isn't running."
- > "Single-step a literal assembly program; watch registers change; see exactly which instruction sets the GPIO bit that turns the LED on."
  - Triplet semicolons. Rewrite: "Single-step a literal assembly program. Watch registers change. See exactly which instruction flips the GPIO bit."
- > "This is *how you learn* the bare-metal layer — by stepping every instruction and matching to the reference manual."
  - Rewrite: drop italics + em-dash. "This is how you learn the bare-metal layer: step every instruction and match it to the reference manual."
- > "Hardware breakpoints are essential for read-only memory ..."
  - Rewrite: `essential` → `needed`. "Hardware breakpoints are needed for read-only memory."
- > "The classic problem: target is in some unknown state from a previous crash. How to halt at the very first instruction after reset?"
  - Rewrite: drop the rhetorical question + classic. "Often the target is in an unknown state from a previous crash. You want to halt at the first instruction after reset."

### ESL readability
- > "The tricky parts are: getting the adapter's USB-IDs right for OpenOCD, choosing the right *target* config (Cortex-A7 vs Cortex-M differ massively), handling Cortex-A's complications (multi-CPU, secure-vs-non-secure world, MMU on/off), and giving GDB the right symbol files at the right times (one ELF for bare-metal, another for U-Boot, another for kernel + per-module symbols)."
  - One sentence carries four ideas with three parentheticals. Rewrite as a bullet list under "Tricky parts:" — adapter USB IDs, target config (A7 vs M), Cortex-A complications, GDB symbol files per layer. ESL readers stall on this.
- > "Software breakpoints (default `break`) replace the instruction with the ARM `BKPT` instruction (A32: `0xE1200070`; Thumb-2: `0xBE00`) — the CPU traps to the prefetch-abort vector, the kernel/debugger sees a "debug" exception kind, and gdb regains control."
  - Triple-clause em-dash sentence with three sub-clauses. Break into three sentences. "Software breakpoints replace the instruction with the ARM `BKPT` (A32: `0xE1200070`; Thumb-2: `0xBE00`). The CPU traps to the prefetch-abort vector. The kernel/debugger sees a debug-exception, and gdb regains control."
- > "OpenOCD listens on:" — fine. The block right after the run command is dense; one sentence summary helps.

### Needs more explanation
- **§118.1 TAP/DAP architecture is under-explained for a 6 YOE MCU reader.** The chapter introduces `TAP` (Test Access Port state machine) in one paragraph, then jumps to `CoreSight` and `DAP`. A 6 YOE MCU dev has likely poked SWD on a Cortex-M but has never seen the CoreSight/DAP/AP/MEM-AP hierarchy. Add a half-page diagram: TAP scan chain → CoreSight DAP → APB-AP / AHB-AP → debug registers (DSCR, DBGDRCR) and break-point logic. Without that the reader can't read `target/imx6ull.cfg` and understand what's actually happening on the wire.
- **§118.4 The `target/imx6ull.cfg` is hand-waved.** Show the actual content (or a stripped excerpt): `jtag newtap`, `cti create`, `target create`, the IDCODE field. Otherwise the reader can't write their own when the shipped config doesn't match.
- **§118.5 `gdbserver` vs JTAG-attached `gdb` distinction is missing.** Reader will conflate the two. One paragraph: gdbserver requires a working kernel + libc on target (Ch 120); JTAG via OpenOCD works at any layer (bare-metal, U-Boot, kernel pre-init) because it talks to silicon, not to a process. State this explicitly here so Ch 120 makes sense.
- **§118.7 KASLR + `add-symbol-file` workflow is one line.** For a kernel with KASLR enabled and an unknown offset, show the actual procedure: read `kaslr_offset` from `/proc/kallsyms` (or the kernel log line), then `add-symbol-file vmlinux <text_addr + offset>`. Currently just says "use `add-symbol-file` with the runtime offset" with no example.
- **§118.10 `reset halt` mechanism.** The DBGEN + HRR mention is correct but unexplained. One paragraph: DSCR is the Cortex-A Debug Status and Control Register; setting `HALT_REQ` plus the right enable bits gates the CPU at the reset vector. Otherwise the bullet list reads like magic.

---

## Ch 119 — Kernel debugging without JTAG

### AI wording / sledgehammer / buzzwords
- > "JTAG (Ch 118) is the surgeon's tool; this chapter is the medical kit you actually carry."
  - Sledgehammer metaphor in the intro. Rewrite: drop the analogy. "JTAG is for bench work. This chapter covers what you can run on a deployed device with no debug header."
- > "printk — the survivor", "ftrace — the surgical tracer", "eBPF — modern probes", "kgdb — actual GDB over serial", "Kernel oops — the autopsy"
  - Every §-heading is a personification. Strip to neutral. "119.1 printk", "119.2 ftrace", "119.3 eBPF", etc. The reader doesn't need a thematic title for every section.
- > "**pr_debug is the secret weapon**"
  - Marketing voice + bold. Rewrite: "`pr_debug` is worth knowing about." or just drop the line — the explanation that follows speaks for itself.
- > "This unlocks **massive** existing debug coverage in mainline drivers without recompiling."
  - Drop bold + `massive`. "This enables existing debug prints in mainline drivers without rebuilding."
- > "Killer for performance investigation."
  - Rewrite: "Useful for performance investigation."
- > "Indispensable for "why did this 1-second operation take 10 seconds.""
  - Rewrite: `indispensable` → `useful`. "Useful for `why did this 1-second operation take 10 seconds`."
- > "These are *production-safe* — eBPF verifier prevents infinite loops, bad memory access, kernel crashes."
  - Em-dash chains, triplet of risks. Rewrite: "eBPF programs are production-safe. The in-kernel verifier rejects infinite loops, bad memory access, and anything that would crash the kernel."
- > "for "produced oopses we can't reproduce, give me a full snapshot" it's incomparable."
  - Rewrite: drop `incomparable`. "For oopses you can't reproduce, it's the right tool."
- > "That points to the exact source line. Combine with `git blame` and you know whose patch caused the regression."
  - Rewrite: "That points to the exact source line. Run `git blame` on it to see which patch introduced the regression."

### ESL readability
- > "the **software-only kernel debugging toolkit** that works on a deployed device with no hardware debug access. **printk**'s deeper toolbox (`pr_debug`, `dynamic_debug`, ring-buffer levels), **ftrace** (function tracer + `function_graph` + tracepoint events), **trace-cmd** + **KernelShark** (record + GUI), **bpftrace** and **bcc** (eBPF for live kernel introspection), **kgdb** over serial (when you do want a debugger but only have UART), and the **oops decoder** workflow (`addr2line`, `scripts/decode_stacktrace.sh`)."
  - One sentence of ~80 words. ESL reader stalls. Rewrite as a bullet list under the **What** line.
- > "On a customer's device hanging once every 3 days, you need *post-hoc forensics* — what was the kernel doing in the second before the freeze? ftrace's persistent buffer + an oops decoder gives you that."
  - Idiomatic + Latin. ESL-friendly: "If a customer's device hangs once every three days, you need to know what the kernel was doing in the second before the freeze. ftrace's persistent buffer plus the oops decoder answers that."
- > "eBPF lets you attach a probe to `tcp_retransmit_skb` on a production server and count retransmits per remote — without recompiling the kernel."
  - Em-dash for a single qualifier. "eBPF lets you attach a probe to `tcp_retransmit_skb` on a production server and count retransmits per remote address, without recompiling the kernel."
- > "Spam in `dmesg` → `dynamic_debug` to filter."
  - Idiom (`Spam`) + arrow. Rewrite: "Too much output in `dmesg`: use `dynamic_debug` to filter."

### Needs more explanation
- **§119.2 ftrace internals are skipped.** The chapter shows `echo function > current_tracer` but doesn't explain *how* ftrace patches the kernel: `mcount`/`__fentry__` callsites, CONFIG_FUNCTION_TRACER inserts a nop at every function entry, the tracer patches the nop to a call. For a 6 YOE MCU dev who has done bare-metal hooking, this is the conceptual hook that makes ftrace stop feeling magic. One paragraph + a one-line `objdump` of a traced function.
- **§119.3 eBPF verifier is mentioned but not explained.** "the verifier prevents X" — but what *is* the verifier? It's a kernel-side static analyzer that rejects programs with unbounded loops, out-of-bounds memory access, or paths that could fault. The reader will use bpftrace next chapter; they need to know why their program compiles but then "doesn't load" with a verifier error.
- **§119.4 kgdb workflow is incomplete.** The text shows the boot path with `kgdbwait` but doesn't show how to trigger kgdb from a *running* kernel (sysrq-g, or `echo g > /proc/sysrq-trigger`). That's the common case; `kgdbwait` is the early-boot edge.
- **§119.5 Oops decoding workflow has a gap.** The example shows `addr2line` against `vmlinux` for the kernel PC, and against the `.ko` for the module offset. But it skips how to *compute* the module offset from the oops output. The oops shows `[<7f000024>]`; this is the loaded VA, not the file offset. Show: `cat /proc/modules` to get module load base, subtract from PC, feed to `addr2line`. Otherwise the reader follows the example, gets a confusing answer, and gives up.
- **§119.6 kdump on small-RAM devices is dismissed in one line.** For a 6 YOE MCU dev this is the conceptually hardest part — kexec a second kernel from the dying kernel's memory, save vmcore from the second kernel. Even though the chapter says "skip on i.MX6ULL," explain why kexec works (the capture kernel's memory is reserved at boot, not allocated post-crash). One paragraph; it's a beautiful trick worth knowing.

---

## Ch 120 — User-space debugging

### AI wording / sledgehammer / buzzwords
- > "kernel debugging (Ch 118, 119) is the rare case; you'll debug applications 10× more often."
  - Opinion-as-fact framing. Soften: "Kernel debugging (Ch 118, 119) is less common in day-to-day work; most of the time you're debugging applications."
- > "Master these and you debug embedded apps as productively as desktop ones."
  - Sledgehammer closer. Rewrite: "Once these are set up, embedded app debug feels much like desktop debug."
- > "strace — the syscall flashlight"
  - Personification. Rewrite section header: "120.5 strace — trace syscalls"
- > "perf — the universal profiler"
  - Marketing. "120.7 perf — sampling profiler and counters"
- > "ltrace — same for library calls"
  - Fine. Less marketing.
- > "perf top — htop for CPU functions"
  - Cute analogy, fine if reader knows `htop`. Add one line: "Continuously updated, like `htop`, but functions instead of processes."
- > "The single most useful CPU-profile visualization. ... Once you've used flamegraphs, you wonder how anyone debugged performance without them."
  - Drop both sentences. The screenshot or example sells it; the marketing line doesn't.
- > "Killer for:" (in §120.5)
  - Rewrite: "Useful for:"

### ESL readability
- > "the toolkit for debugging your **user-space applications** on the i.MX6ULL target from a host workstation. **gdbserver** + **gdb-multiarch** for breakpoint-and-step debugging across the network; **strace** for "what syscalls is this program making"; **ltrace** for shared-library calls; **perf** for sampling profilers + hardware-counter-based analysis + flamegraphs; **core dumps** with `coredumpctl` for post-mortem analysis of crashed processes."
  - One 75-word sentence with five semicolons-as-bullets. Rewrite as a bullet list. ESL standard fix.
- > "99 Hz sampling (not a round 100 Hz — that's deliberate, to avoid harmonic with periodic kernel timers that often run at 100/250/1000 Hz) gives ~1 sample per 10 ms with minimal overhead (~0.1–0.5 %). Perfect for "what is this thing actually doing.""
  - Nested parenthetical + dash + quoted aside. Break apart. "99 Hz sampling, not 100 Hz, avoids harmonics with kernel timers (which run at 100/250/1000 Hz). At 99 Hz you get about one sample per 10 ms with 0.1–0.5 % CPU overhead. Good for figuring out what an app is actually doing."
- > "X-axis = sample count (~time spent); Y-axis = call stack."
  - The `~` shortcut and equals-signs read like notes. ESL-friendly: "The x-axis is sample count (roughly time spent); the y-axis is the call stack."
- > "Sysroot pointing to wrong path. gdb finds libc.so.6 in /lib (host) instead of the cross-built one; symbols mismatch."
  - Two semicolon-clauses. "When `sysroot` points at the wrong path, gdb loads the host's `libc.so.6` from `/lib`. Symbols then mismatch."

### Needs more explanation
- **§120.2 `sysroot` and `solib-search-path` are command-line gestures with no explanation of *why*.** The reader needs to know: GDB on the host needs to find the *exact same* shared libraries as the target so symbol offsets match. If the host's `/lib/libc.so.6` differs even slightly, every backtrace in libc is wrong. One paragraph explaining this; otherwise the reader sets sysroot, it still doesn't work, and they don't know why.
- **§120.7 perf hardware counters — what's actually available on Cortex-A7?** The chapter says "limited to a handful" but doesn't list them. The Cortex-A7 PMU exposes 4 programmable counters plus the cycle counter. Mention: `perf list` to enumerate, and which events are useful (`cache-references`, `cache-misses`, `branch-instructions`, `branch-misses`, `L1-dcache-loads`). Without this the reader has no idea what `perf stat -e <event>` is allowed.
- **§120.8 core dump tuning is shallow.** Default `core_pattern` interacts with systemd-coredump on systemd systems, with apport on Ubuntu, with the raw `core` file on others. Spell out the precedence and the `%e/%p/%t/%s` format specifiers. Also mention `coredump_filter` (`/proc/<pid>/coredump_filter`) — needed to capture shared memory regions, often missed.
- **§120.9 the worked example is great but tooling is mixed.** Reader needs to know that `wchan` requires `CONFIG_KALLSYMS=y` (most distros), and that `ss` replaces `netstat` (which is deprecated). One-line aside.

---

## Ch 120A — Mainline patch submission

### AI wording / sledgehammer / buzzwords
- > "if you write a driver in this book and it's useful, it can go upstream. Upstream-merged code is maintained forever (security backports, API migrations); your out-of-tree fork is on you."
  - Slightly preachy. Rewrite: "If you write a driver that's useful, it can go upstream. Upstream-merged code gets security backports and API migrations for free; an out-of-tree fork is yours to maintain."
- > "the kernel community has strict, *unwritten* rules — wrong commit-message format, untested patches, replying to review with hostility, top-posting on mailing lists — these get your patch silently dropped no matter how good the code is."
  - Triple em-dashes, four examples in one breath, sledgehammer close. Break apart. "The kernel community has strict and partly unwritten rules. A wrong commit-message format, an untested patch, a hostile reply to review, or a top-posted email is enough to get a patch silently dropped, no matter how good the code is."
- > "This chapter is the cultural primer the kernel docs don't write down."
  - Self-aggrandizing closer. Drop it; the chapter speaks for itself.
- > "Lore.kernel.org is the public archive of every mailing-list discussion since ~1998; **always search there before sending** — your "novel" fix may have been tried and rejected three times already, and the rejection threads tell you why."
  - Two clauses joined by `;` and `—`. Rewrite: "Lore.kernel.org is the public archive of every mailing-list discussion since ~1998. Always search it before sending. A 'novel' fix may have been tried and rejected three times already, and the rejection threads tell you why."
- > "DT bindings are one of the easiest categories to get merged — they're additive (don't break anything) and self-contained. Good first-patch target."
  - Fine, but the "Good first-patch target." fragment reads like a TV pitch. Either fold in or drop.

### ESL readability
- > "The output is your To: + CC: list. **Do not invent additional CCs** — only what `get_maintainer.pl` says. Spam to "the whole kernel" gets you on people's filter-out lists."
  - The idiom "filter-out lists" is informal. Rewrite: "The output is your To and CC list. Don't add extra CCs beyond what `get_maintainer.pl` returns. CC'ing every kernel address you can find gets you ignored or filtered."
- > "Maintainer responds with feedback. Don't argue; address each point. If you disagree, explain politely."
  - Choppy three-fragment paragraph. ESL-friendly: "When a maintainer responds with feedback, address each point. If you disagree, say so politely and explain why."
- > "Apologies for the missing comment. The hardware register interprets the value in 50% steps; multiplying by 2 converts user-supplied percent to register units. I'll add a comment in v2."
  - This is example dialog — keep it. Fine.
- > "If you go silent for >2 weeks after a review, your patch gets dropped from maintainers' queues. Stay engaged."
  - Two short imperatives. Fine, but `>2 weeks` reads like a math symbol; spell out: "If you go silent for more than two weeks after a review, your patch will be dropped from the maintainer's queue. Stay engaged."

### Needs more explanation
- **§120A.3 commit-message structure is shown but not *taught*.** The example has imperative-mood subject and `WHY not what` body. A 6 YOE MCU dev whose company uses "fixed bug" commits needs to see *why* the kernel insists on imperative mood ("subsystem: do X" reads naturally as "this patch makes the subsystem do X"). One sentence on the grammar pattern. Also: the `Fixes:` tag is shown once with no explanation of where to find the original commit hash — show `git log --oneline --grep=...` or `git log -- <file>` workflow.
- **§120A.4 checkpatch.pl is run but its output isn't read.** Show one or two *actual* failing checkpatch outputs ("ERROR: do not use assignment in if condition", "WARNING: line over 80 characters") and how to interpret them. Otherwise the reader doesn't know what to do when checkpatch complains.
- **§120A.5 `get_maintainer.pl` output is shown but the role-suffix is not explained.** `(maintainer:...)`, `(reviewer:...)`, `(open list)`, `(moderated list:...)` — each is treated differently. Maintainers go to `--to`, reviewers and lists to `--cc`. State this; it's the first practical question the reader has after running the script.
- **§120A.6 `git send-email` SMTP config is hand-waved for Outlook/corporate.** Gmail App Password is explained. Many readers will have a corporate SMTP server with O365 / OAuth2 — say a sentence about `oauth2.py` helpers or recommend a personal address for kernel work (which is what most kernel devs do).
- **§120A.8 `--in-reply-to=<msg-id>` is mentioned but not sourced.** Where do you get the Message-ID? From the lore.kernel.org page of the v1 thread (right-click → copy permalink, or the `Message-ID:` header in the raw mbox). Without this the reader can't actually use `--in-reply-to`.
- **§120A.11 the `b4` workflow is one block of commands with no narrative.** `b4 prep -n` creates a new series; `b4 send` previews and sends; `b4 trailers` collects review tags into your local branch. Show the loop: prep → write → send → wait → trailers → send v2. Currently it reads as a tool reference, not a workflow.
- **§120A.12 the YAML example uses `unevaluatedProperties: false` without explanation.** This is the strictest JSON-Schema validation mode — any property not in `properties:` or inherited via `allOf` is rejected. For a reader new to YAML bindings this is critical (Rob Herring's bot will reject your binding if you forget it). One sentence.

---

## Ch 121 — Capstone: custom board port

### AI wording / sledgehammer / buzzwords
- > "the **capstone exercise** that puts everything in this book together."
  - Self-congratulation in the opening line. Rewrite: "A board-port exercise that uses most of what came before."
- > "every Cookbook chapter taught a slice. Doing a real board port is where those slices integrate into competence."
  - "Slices integrate into competence" reads like a workshop brochure. Rewrite: "Each Cookbook chapter covered one piece. A real board port is where those pieces have to work together."
- > "That deliverable, plus the experience of debugging the inevitable subtle problems, is what makes an embedded-Linux engineer hireable."
  - Career-marketing close. Drop the last clause: "That deliverable, plus the debugging experience that comes with it, is what gets you to the next level of confidence on this stack."
- > "Don't try to "boot everything at once" — bring up serial, then DDR, then SD, then Ethernet, then your custom peripheral, in that order, with a serial-console probe after each."
  - Single em-dash sentence with five clauses. Rewrite: "Don't try to boot everything at once. Bring up serial, then DDR, then SD, then Ethernet, then your custom peripheral. Probe the serial console after each step."
- > "Use Ch 118's JTAG when serial is too coarse. Keep a *known-good* fall-back image you can flash to recover from bricks."
  - Fine. Drop the italics on `known-good`.
- > "And reflect: at the end, what was the surprise? Why? That insight is what makes the next board port faster."
  - Royal "we" / coaching tone. Rewrite: "At the end, ask what surprised you and why. That's what makes the next port faster."
- > "This is the **highest-risk** step. Bad DDR config = nothing else works. The DDR Stress Tool is non-negotiable; do not hand-calculate."
  - "Non-negotiable" + "do not" + bold reads like a sales rep. Rewrite: "This is the riskiest step. If DDR config is wrong, nothing else will work. Use the DDR Stress Tool; don't hand-calculate."
- > "If you see U-Boot banner → 80 % of bring-up complete."
  - Made-up statistic. Soften: "If you see the U-Boot banner, the hard part is behind you."
- > "If this works, you've taken a peripheral from "nonexistent on the EVK" to "fully driven by mainline Linux" via DT alone — the canonical pattern."
  - Rewrite: drop `canonical`. "If this works, you've taken a peripheral the EVK doesn't have to a fully Linux-driven device using DT alone. This is the common pattern."
- > "**This script** is the deliverable. Hand it to a teammate; they get the same image. Reproducibility is the difference between "I shipped a product" and "I have a Linux running on my desk.""
  - Sledgehammer "X is the difference between Y and Z" closer. Rewrite: "The script is the deliverable. A teammate runs it and gets the same image. Without a reproducible build, what you have on your desk isn't a shippable product."

### ESL readability
- > "You'll touch: pin-muxing (Ch 5), DDR initialization (Ch 14), U-Boot porting (Ch 22), kernel DT (Ch 27), each peripheral chapter that applies (whatever your board has)."
  - Inline parentheticals make this hard to scan. Reformat as a short bullet list under "You'll touch:".
- > "A 5 % timing margin difference can mean "works at 25 °C, crashes at 40 °C.""
  - The inline quoted phrase is fine; works for ESL. Keep.
- > "`console=ttyS0` won't work on i.MX6ULL (it's `ttymxc0`). Verify against your DT."
  - Good. Keep.
- > "Solder/desolder peripherals on the existing board:" plus the bullet list with one-line scenarios.
  - Fine but five bullets all start with a verb fragment. Add one connecting sentence: "These changes touch real wiring and partial-board mods. Good practice for DT skills."

### Needs more explanation
- **§121.2 hardware variant tradeoffs are listed but not explained.** Option A "Pretend-port" sounds dismissive — but it's the right starting choice and the chapter doesn't justify it. State: even renaming the board exercises the full toolchain (defconfig, board file, DTS, MAINTAINERS), which is the bulk of what a real port involves. Option C "Full PCB" — say one sentence on the gap (schematic, layout, fab, assembly) and why it's out of scope.
- **§121.4.4 DDR Stress Tool is named without explanation of what it does.** A 6 YOE MCU dev probably hasn't used it. One paragraph: it's an NXP tool that runs on the target, sweeps DDR calibration values, reports the safe operating window. It's a *bring-up* tool, not a *debug* tool — you run it once per layout, capture the calibration block, embed it in U-Boot SPL.
- **§121.5.4 `bootz` vs `bootm` vs `booti` is not explained.** Reader sees `bootz 0x80800000 - 0x83000000` and doesn't know why three addresses with a `-`. State: `bootz <kernel> [initrd] <dtb>`, with `-` for "no initrd." Otherwise the reader copies the magic and panics when it doesn't fit their layout.
- **§121.7 the build script does a `sudo bash -c` heredoc with multiple mounts.** That's a serious footgun for ESL readers — if `sfdisk` partitions the wrong device, you lose your laptop's disk. Mention: confirm `$TARGET_SD` is a USB SD reader, not `/dev/sda`. A `lsblk | grep $TARGET_SD` sanity check before `sfdisk` would save accidents.
- **§121.8 the failures section lacks the JTAG link.** Each failure should say "verify with JTAG / probe / multimeter." Several do; "Driver doesn't probe" should add: `dmesg | grep -i probe`, `cat /sys/kernel/debug/devices_unbound`, and the "EPROBE_DEFER" gotcha (driver returns -EPROBE_DEFER, kernel retries later — looks like a fail in early dmesg but resolves later).

---

## Ch 121A — CI/CD for embedded Linux

### AI wording / sledgehammer / buzzwords
- > "any embedded product shipping updates beyond one engineer's laptop needs CI."
  - Absolutist opening. Soften: "Any embedded product shipping updates from more than one developer benefits from CI."
- > "The fundamental risk: someone merges a DT change that breaks boot; nobody notices until a customer tries to update; days of fire-fighting."
  - Triple semicolons + idiom. Rewrite: "The risk is real: someone merges a DT change that breaks boot, nobody notices until a customer tries to update, and you spend days firefighting."
- > "With CI + real-hardware smoke tests on every PR, that bug is caught in 10 minutes. The cost is one $50 dev board + one Linux box + 4 hours setup. The savings — even on a 3-person team — pay back in the first month."
  - Triplet rhythm + sales pitch. Rewrite as two sentences and drop the dollar-figures-as-flourish: "With CI plus real-hardware smoke tests on every PR, that bug surfaces in ten minutes. The setup cost is small (a dev board, a Linux host, and a few hours) and pays back quickly."
- > "**the trick is that a normal cloud CI runner has no USB to your hardware; you self-host a runner on a Linux box that physically owns the board**"
  - "The trick is X" voice. Drop the rhetorical move: "A normal cloud CI runner has no USB connection to your board. To run hardware tests, self-host a runner on a Linux box that physically owns the board."
- > "A "smoke test" is small (boot, get prompt, run 3 sanity checks, capture log) but enormously valuable."
  - "Enormously valuable" is buzzword. Rewrite: "A smoke test is small (boot, get prompt, run a few checks, capture the log) but catches most regressions."
- > "For embedded, "it compiles" is necessary but not sufficient. The real value of CI is **catching regressions on actual hardware** ..."
  - "Necessary but not sufficient" is academic-paper voice. Rewrite: "For embedded, building cleanly isn't enough. The real value of CI is catching regressions on real hardware ..."
- > "Use short, shielded cables; powered hubs."
  - Fine. Concise.

### ESL readability
- > "`pull_request_target` is dangerous"
  - Fine, but a reader who hasn't met it will not know why. Add one sentence: "`pull_request_target` runs the workflow with write permissions on the target repo, which a forked PR can abuse."
- > "**continuous integration** for embedded Linux — building U-Boot, kernel, rootfs on every commit; running smoke tests on **real hardware** in a board farm via a self-hosted CI runner with USB-OTG flashing; a **Labgrid**-style test harness; pass/fail signaling back to the PR."
  - One 50-word **What** sentence with three semicolons. Bullet-list it.
- > "On every push, the runner does the Ch 121 build, flashes via `uuu`, watches serial for `=>` prompt + a sysfs check, captures the serial log, marks the PR pass/fail."
  - Five comma-clauses. Break into two sentences: "On every push, the runner does the Ch 121 build and flashes via `uuu`. It then watches serial for the `=>` prompt, runs a sysfs check, captures the log, and marks the PR pass or fail."

### Needs more explanation
- **§121A.3 `uuu` is used without an introduction.** Reader who hasn't done Ch 8/19's recovery path won't know what `uuu` is. One sentence: `uuu` (Universal Update Utility) puts the i.MX into Serial Download Protocol mode, then scripts U-Boot + kernel + rootfs loading over USB. Came from NXP's MFGTOOL.
- **§121A.4 the Python smoke-test script needs more guard rails.** No try/except, no carriage-return handling on different shells, no escape if the board hangs partway. For a 6 YOE MCU dev who'll adapt this, mention: wrap each `expect` in try/except, log the buffer on failure, always do a hard power-cycle in `finally`. Pexpect is the canonical library for this kind of script; mention it.
- **§121A.5 Labgrid is one short section.** This is the *hard concept* in the chapter — how multiple test runners coordinate on shared hardware, the coordinator/exporter/client model, and why locking matters. A diagram (Labgrid Coordinator ↔ Exporter on board host ↔ Client/test runner) plus the "place" abstraction would carry it. Currently reads as just "configure a YAML, call the API."
- **§121A.7 ccache for cross-builds has a subtle gotcha.** ccache by default doesn't consider the cross-compiler version in its hash, leading to "stale cache after toolchain upgrade." Mention `CCACHE_COMPILERCHECK=content` to fix this. Currently the chapter just says "5× speed-up" with no mention of cache-poisoning risk.
- **§121A.8 trigger patterns include `paths-ignore` and `paths`** — but the YAML is brittle (e.g., a PR that touches both code and docs runs both, then doesn't run on the next docs-only push). Add one sentence about the limitation: `paths-ignore` is best-effort, not a contract.

---

## Ch 122 — Build your own cross-toolchain

### AI wording / sledgehammer / buzzwords
- > "the **canonical tool**"
  - Used twice in the intro. Rewrite second use: "the standard tool." Or just "crosstool-NG."
- > "for most users, `apt install gcc-arm-linux-gnueabihf` is fine. So why build your own? Three real reasons:"
  - "Three real reasons" triplet rhetoric. Rewrite without the count: "For most users, `apt install gcc-arm-linux-gnueabihf` is fine. Build your own when one of these matters: ..."
- > "Educational value matches Ch 11 (boot ROM image) and Ch 14 (DDR init)."
  - Self-referential praise. Drop. Replace: "It also teaches what every flag and stage actually does."
- > "**the multi-stage build resolves the chicken-and-egg: stage 1 gcc ... → kernel headers → glibc ... → stage 2 gcc ...**"
  - Bold + arrow chain is hard to read. Rewrite the line into clean prose: "A multi-stage build solves the chicken-and-egg problem. Stage 1 gcc has no libc and can only compile freestanding code. It builds the kernel headers, then glibc. Stage 2 gcc is then built against the new glibc and has a full C++/pthread runtime."
- > "Get any of these wrong and the linker can't find libc, or gcc looks in `/usr/lib` instead of the cross sysroot."
  - Fine. Concrete.
- > "Each `configure` line is a tour of GNU autoconf flags."
  - Cute but vague. Drop or replace with concrete: "Each `configure` line is a stack of GNU autoconf flags. The important ones are `--target`, `--prefix`, and `--with-sysroot`."
- > "For one-time understanding, build it by hand. Compressed (a full tutorial is 30+ pages; here's the skeleton):"
  - Aside-as-parenthetical. Move outside: "Building it by hand is a one-time learning exercise. A full tutorial would run 30+ pages; here's the skeleton."
- > "Your own toolchain, pinned to specific versions, reproducible."
  - Triplet-closer. Drop or rewrite: "You now have a toolchain pinned to specific versions, reproducible by anyone with the same config."

### ESL readability
- > "You want to build gcc. gcc needs glibc to compile programs. glibc needs gcc to compile itself. Circular."
  - The four-fragment punch landing on "Circular." is mannered. Rewrite ESL-friendly: "To build gcc, you need glibc. To build glibc, you need gcc. This is circular."
- > "**hf binaries cannot run on soft-float systems** and vice versa."
  - "and vice versa" is short but Latin-source idiom. ESL-friendly: "Hard-float binaries cannot run on a soft-float system. Soft-float binaries can technically run on a hard-float system, but you usually don't mix them."
- > "These three concepts confuse first-time toolchain builders:"
  - Fine. Keep.
- > "When compiling for the target: gcc reads .c source → gcc preprocessor includes ..."
  - The ASCII-art "→" chain is fine for the engineer-at-whiteboard tone. Keep.
- > "**Pick guide:**"
  - Twice in the chapter. Fine.

### Needs more explanation
- **§122.2 bootstrap problem — the "why each stage is configured this way" is hand-waved.** Why does stage-1 gcc need `--disable-shared`, `--disable-threads`? Because shared libraries need a dynamic linker (libc), and threads need libpthread (libc). Stage 1 is freestanding. One paragraph spelling out the *causal* link from "no libc yet" to each disable-flag. Otherwise it reads as a magic incantation.
- **§122.4 manual build — the `libc_cv_forced_unwind=yes` flag is mysterious.** This is the famous glibc-build-against-stage-1-gcc workaround. Mention: glibc's configure checks if gcc supports a feature by *trying to compile a test program that links*; stage-1 gcc can't link, so the check returns false, but the feature actually works at runtime. Forcing `=yes` skips the broken check.
- **§122.5 musl vs glibc — `dlopen support`** row says "yes/yes/yes/partial". This contradicts the well-known "musl static + dlopen don't mix" issue. Clarify: dynamic musl supports dlopen; static musl does not. (Same is true of glibc, but glibc's static dlopen "works" with warnings.)
- **§122.6 ABI suffix — the calling-convention difference is not shown.** Mention concretely: on `gnueabihf`, `float foo(float x)` passes `x` in `s0` (FPU register) and returns in `s0`. On `gnueabi`, `x` is passed in `r0` (general register) and the FPU is used internally if available. That's why the ABIs are not link-compatible.
- **§122.8 sysroot vs prefix vs target — the diagram is good but lacks one concrete check.** Show `gcc -print-sysroot`, `gcc -print-search-dirs`, `gcc -v` (which prints the full include and library search paths used at this invocation). These are the actual commands a reader will need when debugging "why does gcc not find my libc."

---

## Ch 122A — BSP → mainline migration

### AI wording / sledgehammer / buzzwords
- > "You're staring at a project-defining decision. This chapter is the playbook so it doesn't become a project-killing one."
  - Sledgehammer "project-defining → project-killing" wordplay. Rewrite: "This is a project-defining decision. This chapter is the playbook for getting it right."
- > "The "easy" path — stay on 4.1.15 forever — leaves accumulated CVEs unfixed:" / "The "hard" path — migrate to mainline 6.6+ LTS — buys:"
  - Scare-quoted easy/hard pattern. Rewrite without the quotes and the parallel structure: "Staying on 4.1.15 means accumulated CVEs go unfixed: ... Migrating to mainline 6.6+ LTS buys: ..."
- > "After 100+ CVEs, the backport effort exceeds the migration effort. Track this."
  - Fine, "Track this." is a useful imperative.
- > "Months of work, not years."
  - Closer cliche. Rewrite: "Expect months of work, not years."
- > "The hardest bits aren't technical (`git rebase` does most of it); they're *cultural*: convincing management that 6 months of "no new features, just kernel work" pays back over the product's life."
  - "Not X, they're Y" sledgehammer + parenthetical + italics. Rewrite: "The hardest part isn't technical. `git rebase` handles most of the code work. The hardest part is cultural — convincing management that six months of kernel work, with no new features, pays back over the product's lifetime."
- > "This chapter arms you with the data."
  - Drop. The chapter speaks for itself.

### ESL readability
- > "Plus: Old toolchain (gcc 6.x) won't compile mainline kernel 6.6 cleanly. The kernel's hard minimum is gcc 5.1 (Documentation/process/changes.rst), but newer features and warnings require gcc 11+; most distros ship gcc 12+ for embedded cross-builds."
  - Two nested parentheticals. Break apart: "Plus there's a toolchain problem. gcc 6.x won't compile a mainline 6.6 kernel cleanly. The kernel's hard minimum is gcc 5.1 (see `Documentation/process/changes.rst`), but newer features need gcc 11+. Most distros ship gcc 12+ for embedded cross-builds."
- > "Old GStreamer 1.10; mainline drivers use new V4L2 APIs."
  - Fragment-as-sentence + idiomatic shorthand. ESL-friendly: "Old GStreamer 1.10 doesn't speak to mainline V4L2 drivers, which now use newer APIs."
- > "If mainline has it (committed by someone else after 2017): **delete the BSP patch**, use mainline's version."
  - The colon-comma chain reads awkward. Rewrite: "If mainline has it already (someone committed the same fix after 2017), delete the BSP patch and use the mainline version."
- > "Migrate subsystems in dependency order, **most-isolated first**."
  - Fine. ESL clear.
- > "Cutover: schedule a date when new customer shipments come on the mainline-port version."
  - "Cutover" is a project-manager idiom. ESL-friendly: "Plan the cutover. Pick a date. After that date, new customer shipments use the mainline-ported kernel."

### Needs more explanation
- **§122A.2 inventory script is too short.** The `git log --oneline` to spreadsheet flow is the right idea but skips the actual hard part: matching a BSP patch to its mainline counterpart. Show `git log --grep='<subject substring>'` on mainline, plus the `--diff-filter` for "did this file get added later?" Also: `git pickaxe` (`git log -Sfunction_name`) is the workhorse for "where did this code go?" Mention it.
- **§122A.4 subsystem dependency graph** — the ASCII art is good but doesn't explain *why* clk/pinctrl come first. Why: every device driver `probe()` calls `clk_get()` and `pinctrl_select_state()`. If these are wrong, every other subsystem fails to probe with confusing errors (-EPROBE_DEFER loops, "could not get clock"). Spell this out.
- **§122A.5 per-subsystem migration — the cherry-pick conflict handling is just one bullet.** Show a concrete worked example: a BSP patch that adds a parameter to a function that mainline has already removed. Strategy: (a) is the BSP patch's intent already in mainline? `git log -p drivers/foo/foo.c` to see; (b) if no, port the *intent* not the diff — write a new patch against current mainline structure. This is the actual hard skill of the chapter.
- **§122A.6 "pinned driver" section needs concrete pointers.** etnaviv vs Vivante is mentioned but the actual API gap isn't shown. The relevant gap: vendor blob expects `vendor-fbdev` ioctl path; etnaviv exposes only DRM/GBM. A short table of "vendor stack → mainline equivalent + caveat" would help.
- **§122A.9 worked example is light on the actual hard step.** "Boot from existing rootfs first; later update rootfs to libcs ABI-matched to gcc 13" — this *is* the hard step. Mainline 6.6 + glibc 2.38 rootfs + old gcc 6 BSP binaries = ABI mismatch. Spell out the bisect strategy: (1) boot mainline with BSP rootfs to validate kernel; (2) rebuild rootfs with new toolchain; (3) bisect any new-rootfs-only failures. Currently the example skips from "build kernel" to "cutover" in one bullet.

---

## Ch 123 — Yocto vs Buildroot

### AI wording / sledgehammer / buzzwords
- > "the **build-system decision** that defines your product's whole CI/release/maintenance story."
  - Sweeping opening. Rewrite: "Picking a build system shapes your product's CI, release, and maintenance flow for years."
- > "Then the honest verdict: when each wins, when each is a poor fit, when *neither* is right."
  - Italics + triplet rhythm. Rewrite: "Then a verdict on when each wins, when each is a poor fit, and when neither is right."
- > "Choosing badly costs months down the road; choosing well saves them."
  - Cliche. Drop or rewrite: "Choosing badly costs months; choosing well saves them — but mostly later, when you can't tell the difference yet."
- > "Most teams overestimate their multi-variant complexity and end up with Yocto sledgehammers cracking Buildroot walnuts."
  - Cute metaphor; works once but fights for attention with the surrounding bold. Keep, drop the bold around the surrounding sentence so this lands.
- > "That's *everything*: cross-toolchain (built or downloaded), U-Boot, kernel, rootfs with selected packages. One command, one tree, predictable output."
  - Italics + triplet close. Rewrite: "That's everything in one tree: cross-toolchain, U-Boot, kernel, rootfs with the packages you picked. One command, predictable output."
- > "The pieces:" followed by bullets.
  - Fine.
- > "For complex builds, Yocto's task graph (do_fetch, do_unpack, do_patch, do_configure, do_compile, do_install, do_package, ...) gives finer control but more places to get lost."
  - "More places to get lost" is fine. Keep.
- > "Buildroot is *quasi-reproducible*" / "Yocto with `BB_HASHSERVE` is *strongly reproducible*"
  - Italics + parallel structure. Rewrite without italics: "Buildroot is mostly reproducible. Yocto with `BB_HASHSERVE` is strongly reproducible — same inputs always produce bit-for-bit identical outputs."
- > "Choosing Yocto for a 1-person project. You spend 80 % of your time learning Yocto and 20 % on your product. Use Buildroot."
  - Made-up 80/20. Soften: "Yocto on a one-person project: you'll spend more time on Yocto than on your product. Use Buildroot."

### ESL readability
- > "every production embedded Linux team uses one (occasionally both)."
  - The inline parenthetical and the absolutist `every` are awkward. Rewrite: "Most production embedded Linux teams use Buildroot or Yocto. Some use both."
- > "The choice has implications for years: hiring (Yocto skills are scarcer + more expensive than Buildroot), CI infrastructure (Yocto builds are slower + need more storage), how easy it is to onboard a new engineer (Buildroot is friendlier), how easy it is to maintain a fleet of variants (Yocto wins), how easy it is to debug a build problem (Buildroot wins)."
  - 60-word sentence with five parenthetical mini-clauses. Reformat as a bullet list: "The choice affects: ..."
- > "Time-to-first-image | 30–60 min | 1–4 hours (initial); 5–30 min (incremental)"
  - Fine in a table.
- > "Choose badly costs months down the road; choosing well saves them."
  - Already flagged above.

### Needs more explanation
- **§123.1 the comparison table is the chapter's centerpiece but several rows need context.** "sstate-cache (artifacts keyed by input hash)" — what's an input hash? It's BitBake hashing every input to a task (source files + dependencies + recipe content) and using that as a cache key. If the inputs are bit-identical, the cached output is reused. One paragraph in §123.3 would help.
- **§123.3 Yocto layer structure is shown but BitBake variable expansion isn't.** `${PV}`, `${PN}`, `${D}`, `${WORKDIR}`, `${S}`, `${B}` — these appear in §123.3 onward without an introduction. A short reference table: PN=package name, PV=package version, S=source dir, B=build dir, D=destination (install root), WORKDIR=top of the build's working tree. Without this the recipes look like template syntax-noise.
- **§123.4 / §123.5 "when X wins" lists overlap.** Several criteria (size, build time, learning curve) cut both ways. Add a one-paragraph "the decision in 30 seconds": "single product, < 5 engineers, < 3 board variants → Buildroot. Vendor BSP serving multiple downstream products, > 5 board variants, regulatory compliance → Yocto."
- **§123.8 reproducibility — what "BB_HASHSERVE" actually does is not explained.** It's a network-accessible hash equivalence service. Two recipes that produce *functionally* identical outputs from *different* input hashes can share a cache entry. This is the secret behind Yocto's reproducibility claim. Without this, readers don't see why Yocto beats Buildroot here.
- **§123.10 CI mention is one paragraph.** This is a Part VIII chapter; Ch 121A is right next door. Add a sentence cross-referencing: "Ch 121A shows the CI mechanics; this section just notes the storage/cache cost difference."

---

## Ch 123A — Yocto layer development

### AI wording / sledgehammer / buzzwords
- > "the production-grade **Yocto layer design** pattern."
  - "Production-grade" is a marketing adjective. Rewrite: "The Yocto layer design that production vendors use."
- > "the pattern below is what production vendors use; it's the difference between "Yocto is awful" and "Yocto is the best build system in embedded Linux.""
  - Sledgehammer "is the difference between X and Y" close. Drop or rewrite: "Done well, Yocto becomes a tool you'd recommend. Done badly, it becomes the build system everyone hates."
- > "**layers stack like CSS — later layers override earlier ones via priority. Use bbappend to extend an upstream recipe; use a new bb for your own packages; use machine config for "this hardware needs these kernel modules"; use distro config for "this product line needs OpenSSL 3 + systemd"; use image recipes for "this final shipped image contains these packages"**"
  - One 65-word bolded run-on sentence with five `use X for ...` clauses. Reformat. Even with the analogy, ESL readers won't survive it. Bullet list.
- > "Get these separations right and a 5-machine, 3-distro, 10-app matrix becomes trivial. Mix them up (machine-specific stuff in distro config) and you build a tar pit."
  - "Tar pit" — keep, vivid and clear; one of the better metaphors in the book. But the "trivial" claim is overstated. Soften: "Get these separations right and a 5-machine, 3-distro, 10-app matrix becomes manageable."
- > "Common pattern: a vendor recipe almost-does-what-you-want; you bbappend to tweak."
  - Fine. Concise.

### ESL readability
- > "Distinguishing what goes where:" + 3-row table.
  - Fine. Good.
- > "If you mix these — e.g., put a machine-specific kernel module in the distro config — you create surprises:"
  - Em-dash inserts an example mid-sentence. Rewrite: "If you mix these (for example, putting a machine-specific kernel module into the distro config) you create surprises:"
- > "A bad layer organization makes every change a hunt across the metadata tree; a good one isolates your product changes from upstream, makes variants trivial, and survives upstream layer updates."
  - 35-word semicolon-joined sentence. Break: "A bad layer organization makes every change a hunt across the metadata tree. A good one isolates your product from upstream, keeps variants simple, and survives upstream layer updates."
- > "BitBake applies the patch + the config fragment automatically. You haven't forked `meta-imx`'s kernel recipe — you've augmented it. Survives upstream layer updates cleanly."
  - The "Survives upstream layer updates cleanly." fragment is ad-copy. Rewrite: "BitBake applies the patch and the config fragment automatically. You haven't forked `meta-imx`'s kernel recipe; you've augmented it. The change survives upstream layer updates."

### Needs more explanation
- **§123A.1 `BBFILE_COLLECTIONS`, `BBFILE_PATTERN`, `BBFILE_PRIORITY`, `LAYERSERIES_COMPAT`, `LAYERDEPENDS` are shown but not explained.** Each is a critical layer-config variable. A short table of "this variable + what it does" is needed. Otherwise the `layer.conf` looks like boilerplate to copy without understanding.
- **§123A.2 `MACHINEOVERRIDES =. "mx6ull:"` — what does `=.` do?** It's BitBake's "prepend with space" operator, distinct from `:=` (immediate expansion), `+=` (append), `=+` (prepend), and `.=` (append no-space). A short reference to BitBake's many operators is needed; the variable-operator zoo is one of Yocto's main confusions for newcomers.
- **§123A.4 the recipe uses `do_install:append()` (with the colon).** This is the modern syntax (Yocto 3.4+ / Honister+). Older recipes used `do_install_append()` (underscore). Mention this — a 6 YOE MCU dev finding old documentation will mix the two and BitBake errors out cryptically.
- **§123A.5 bbappend pattern `linux-imx_%.bbappend` — the `%` wildcard is not explained.** It matches "any version of the recipe named linux-imx." Use `_%` for "any version," `_6.6.%` for "any 6.6.x." Critical to get right; mismatched patterns silently fail to apply.
- **§123A.10 SRC_URI offline cache — the difference between source tarballs cache and sstate-cache is not stated.** `downloads/` = source archives (small, < 1 GB). `sstate-cache/` = build artifacts (large, 10+ GB). Both are needed for fully-reproducible offline builds; you need to copy both. Currently the section only mentions `downloads/`.
- **§123A.13 the `PR` (Package Revision) pitfall is mentioned but `PR-server` (the service that auto-increments PR across CI builds) isn't.** For production fleets using opkg/rpm/dpkg for delta updates within a kernel-version, this is critical. One sentence pointing to it.

---

## Ch 124 — Secure boot and OP-TEE

### AI wording / sledgehammer / buzzwords
- > "any product that handles user data, payment credentials, certificate-based identity, or DRM content needs verified boot. Without it, an attacker who gets physical access can: replace U-Boot with one that dumps memory, boot a custom kernel that bypasses authentication, extract storage encryption keys."
  - Triplet of attack scenarios + sledgehammer. Rewrite: "Verified boot is needed for any product handling user data, payment credentials, certificate-based identity, or DRM. Without it, an attacker with physical access can replace U-Boot, boot a custom kernel that bypasses authentication, or extract storage encryption keys."
- > "With HAB + dm-verity, even physical access leaves the device unbreakable (modulo silicon-level attacks)."
  - "Unbreakable" is dangerous marketing. Rewrite: "With HAB plus dm-verity, the device resists most physical-access attacks. Silicon-level attacks (decap, side-channel, fault injection) remain possible but require expensive equipment."
- > "**the chain is "the ROM checks U-Boot's signature against the SRK hash in eFuses; verified U-Boot checks the kernel + DT's signature; verified kernel mounts a dm-verity'd rootfs whose hash matches; the user app can use OP-TEE to access secrets that no part of Linux can read". Break any link → all subsequent links lose meaning. Get key management wrong (lose the private key, expose it) and you either brick the fleet or hand attackers full control. This chapter is short on the easy bits and long on the "you'll regret skipping this" bits.**"
  - 90-word bolded run-on; ESL-hostile + sledgehammer close. Reformat as numbered prose chain + a separate line on key management.
- > "This is a ritual, not a checkbox:"
  - Cute. Acceptable. Keep.
- > "For prototyping: simpler procedure (keys on your laptop, no HSM). For production: take the ceremony seriously. Lose the keys → cannot ship a single firmware update ever; the fleet is permanently frozen at whatever was last signed."
  - "Cannot ship a single firmware update ever; the fleet is permanently frozen" is correct but doom-laden. Tone down once: "If you lose the keys, you can't ship firmware updates. Whatever was last signed is what the fleet runs forever."
- > "**This is irreversible**."
  - Fine. Earned.
- > "Real TAs: key storage (the secret stays in Secure World; only operations like sign/verify are exposed), secure storage of credentials, attestation (proving to a server that "the firmware running here is what you expect")."
  - Triplet of TA examples with nested parentheticals. Reformat as a small list.

### ESL readability
- > "**SRK (Super Root Key)**: a 4096-bit RSA public key. The hash of the SRK is **blown into eFuses** during manufacturing."
  - Fine. The bold on "blown into eFuses" is acceptable because it's the once-per-chip irreversible operation.
- > "Each request is an SMC → kernel context switch → OP-TEE serves request → SMC return."
  - Arrow chain. Fine for engineer-whiteboard tone. Keep.
- > "ARMv7-A's TrustZone divides the CPU into two "worlds":"
  - Fine.
- > "After Linux boots to a known-good state (a service reaches "active"), it signals "boot succeeded" via env var."
  - Nested quotes; ESL reader stalls. Rewrite: "Once Linux reaches a known-good state — a specific service reports active — it signals boot success via a U-Boot environment variable."
- > "Cannot OTA. The fleet is permanently bricked at whatever was last signed."
  - Repeat from intro. Pick one place to make the point.

### Needs more explanation
- **§124.2 SRK / CSF / CST acronyms are introduced in one breath.** Worth a one-table layout: SRK = Super Root Key (public, hashed into fuses); CSK = Code Signing Key (the actual day-to-day signing key, chained from SRK); CSF = Command Sequence File (binary blob telling the ROM what to verify and where); CST = Code Signing Tool (NXP host-side tool that produces a CSF). The current text mixes these.
- **§124.4 the CSF-text format is one of the hardest bits in the chapter.** "Blocks = 0x877FF400 0x00000000 0x00065F60 "u-boot-ivt.imx"" — three magic numbers. Spell out: load_address, offset_in_file, length, filename. One sentence per field. Without this the reader copies it blindly and gets opaque CST errors.
- **§124.5 HAB closure — the `fuse prog 0 6 0x2` is shown but the fuse map isn't.** Bank 0, word 6, bit 1 = HAB_TYPE. Show the OCOTP layout from the reference manual. Also mention: many vendors use a *separate* SRK_REVOKE fuse so individual SRKs can be revoked without nuking the chip.
- **§124.7 dm-verity hash tree mechanics is sketched in one sentence.** This is the hard concept: each data block is hashed; those hashes are grouped into hash-blocks; hash-blocks are hashed into the next level; recursively until one root hash. On read, verity recomputes the path from block to root and rejects if any hash mismatches. Without this picture the reader doesn't know why dm-verity needs a separate hash partition.
- **§124.8 TrustZone primer is light on the architecture.** SCR.NS bit, NSACR, Secure Monitor Mode — these aren't named. For a 6 YOE MCU dev who knows Cortex-M (which lacks TrustZone except on Armv8-M), the conceptual gap is: Cortex-A's TrustZone is enforced via the NS (Non-Secure) bit in the SCR register, which propagates to every memory transaction and selects the relevant peripheral access. A diagram of the SCR.NS bit flowing through AXI/AHB transactions would land the concept.
- **§124.10 the hello-world TA is shown but the TA build/sign step is missing.** TAs are signed with a TA signing key (separate from the SRK/CSK chain in U-Boot's HAB). Mention this — readers will be confused about why a TA needs *another* set of keys.

---

## Ch 125 — Field updates

### AI wording / sledgehammer / buzzwords
- > "no shipping product survives without updates."
  - Absolutist. Rewrite: "Most shipping products need a way to deliver updates."
- > "Get the OTA architecture right and you ship one update per week, customers love you. Get it wrong and one bad update wipes out a quarter's revenue."
  - "Wipes out a quarter's revenue" — drop the dramatization. Rewrite: "Get the OTA architecture right and you can ship updates weekly. Get it wrong and one bad update can disable thousands of devices in the field."
- > "**A/B is the universal pattern: two rootfs partitions; the running kernel mounts one; an update writes to the other; bootloader switches to the new one on next reboot; if the new one fails to boot to a "we're good" marker within a deadline, bootloader reverts to the old one**"
  - 50-word bolded run-on with five semicolons. Bullet list it.
- > "The complexity is everywhere else: who hosts the update bundle? how is it signed (Ch 124's keys)? how does the device know an update is available? what if the user's WiFi drops mid-download? how do you stage rollouts (10 % → 50 % → 100 %)? these systems handle all of that."
  - Five rhetorical questions in one sentence, then a sales pitch close. Rewrite as a bullet list of "the open questions:" then "these systems address all of them."
- > "Each has a trade-off:"
  - Fine. Concise.
- > "Use HSMs; rotate."
  - Two-word imperatives. Fine; matches the engineer-whiteboard tone.

### ESL readability
- > "RAUC verifies the signature against the keyring, writes to the inactive slot, updates bootloader env, reboots."
  - Four-comma chain. Slightly long for ESL. Acceptable.
- > "For staged rollouts: serve different `latest.json` to different device IDs (canary 10 %, then 50 %, then 100 %)."
  - Fine.
- > "For privacy: device authenticates via client TLS cert (each device has a unique cert provisioned at manufacturing time); server checks per-device permissions."
  - Semicolon then nested-parenthetical. Rewrite: "For privacy, each device authenticates with its own client TLS certificate, provisioned at manufacturing time. The server checks per-device permissions."
- > "A 1 GB rootfs is too big to push over LTE every week. **casync** (Lennart Poettering's tool) chunks images; only changed chunks transfer:"
  - Fine. ESL-clear.
- > "For products with non-uniform update needs (e.g., the rootfs rarely changes but the FPGA config updates monthly), SWUpdate wins."
  - Fine.

### Needs more explanation
- **§125.2 A/B mechanics — `BOOT_X_LEFT` countdown is the key safety primitive but is glossed over.** Worth a worked example: device boots A, mark-good not called → next reboot, A_LEFT decrements to 2; another bad boot, 1; another, 0; bootloader fails to A and tries B. Show this state machine; otherwise the env-var dance reads as magic.
- **§125.3 the U-Boot scripting is shown but the `if test "${BOOT_ORDER%%* *}"` syntax is opaque.** That's a U-Boot environment variable substitution: `%%* *` strips everything from the first space onward, leaving the first slot in the order. Explain — it's the kind of detail that bites readers who try to modify the script.
- **§125.5 casync chunking — the chunk-deduplication mechanism isn't explained.** It's content-defined chunking via a rolling hash (like rsync's chunking but better at unaligned changes). Two builds of the rootfs differing only in `/usr/bin/myapp` share 99 % of chunks. One paragraph on this; otherwise "5-50 MB instead of 500 MB" sounds like magic.
- **§125.8 boot-success detection — the "watchdog reverts" path is hand-waved.** The mechanism: at boot, U-Boot has set a watchdog timer (e.g., 60 s); userspace's "mark-good" script disables it; if the script never runs, watchdog resets the device; on next boot, U-Boot sees `BOOT_LEFT` decremented and falls back. Spell this out — it's the safety chain that makes A/B reliable.
- **§125.9 lab #7 "force a bad update" — needs the actual test mechanism.** A bundle whose `myapp` crashes doesn't necessarily prevent boot-completion (other services may report good). Show the *real* test: a bundle where the kernel panics during init, or where mark-good is removed from systemd's start chain. Otherwise the lab can pass while the rollback path isn't actually exercised.

---

## Ch 125A — VSCode + gdbserver

### AI wording / sledgehammer / buzzwords
- > "**`launch.json` joining them**"
  - "Joining them" is wishful. Concrete: "`launch.json` ties them together."
- > "Asking them to learn `gdb` tui mode is a barrier they shouldn't have to clear."
  - Slightly preachy. Rewrite: "Forcing them to learn gdb's tui mode just to set a breakpoint is unnecessary."
- > "The cost is one-time `launch.json` setup; the payoff is every subsequent debug session."
  - Salesy. Rewrite: "Setting up `launch.json` once pays back every debug session after."
- > "**VSCode's debug UI is a shell around gdb; the `launch.json` is its config; you tell it which gdb binary to use, what binary to debug, what host:port to connect gdbserver on, and where the source tree lives**"
  - 40-word bolded run-on. Reformat: "VSCode's debug UI is a wrapper around gdb. `launch.json` configures it. You set: which gdb binary, which binary to debug, where gdbserver listens, and where the source tree lives."
- > "The trick is `c_cpp_properties.json`: point IntelliSense at the **target's** sysroot headers, not the host's; otherwise "Go to Definition" finds your laptop's `stdio.h` instead of the cross-compiled one."
  - "The trick is" again. Rewrite: "The non-obvious part is `c_cpp_properties.json`. It must point IntelliSense at the target's sysroot headers, not the host's. Otherwise 'Go to Definition' finds your laptop's `stdio.h`, not the cross-compiled one."
- > "With both files right, IDE-style debug + perfect Go-to-Definition makes embedded debugging as productive as desktop development."
  - "Perfect" is overstated; soften: "With both files right, IDE-style debug and accurate Go-to-Definition make embedded debug feel close to desktop."
- > "It's not a debugger; not an editor for serious projects. But for "I'm reading the kernel source and want to navigate quickly," nothing beats it."
  - "Nothing beats it" — keep, it's an honest endorsement and not buzzword-rotten. Acceptable.

### ESL readability
- > "Plus a sidebar on **Source Insight** for read-only kernel-source navigation (it's old but still the fastest tool for that one task)."
  - "Sidebar" is editor's jargon for "aside." ESL-friendly: "Plus a short note on Source Insight, an old commercial editor that's still the fastest tool for read-only kernel-source navigation."
- > "Critical: without this, IntelliSense reports cross-compile-time errors that don't actually exist (because it thinks you're targeting x86 but ARM-only macros are not defined)."
  - The parenthetical is the actual explanation; promote it. "Without this, IntelliSense reports errors that aren't real: it thinks you're compiling for x86, so ARM-only macros are undefined and code inside `#ifdef __arm__` looks dead."
- > "**`gdb-dashboard`** — terminal alternative if you decide to leave VSCode."
  - Fine.
- > "**`gdbserver` is small (~100 KB statically linked); no debug-info needed on the target.**"
  - Reads as a parenthetical aside. Move to its own line: "`gdbserver` is small — about 100 KB statically linked — and needs no debug info on the target."

### Needs more explanation
- **§125A.3 the `set sysroot` value is hardcoded to a Yocto recipe-sysroot path.** This is the wrong path for most readers, who'll have either a Buildroot SDK at `output/host/arm-buildroot-linux-gnueabihf/sysroot/` or a crosstool-NG sysroot at `~/x-tools/arm-linux-gnueabihf/arm-linux-gnueabihf/sysroot/`. Mention all three patterns. Also: the Yocto path embeds the recipe name (`myapp/1.0-r0`), which changes with version bumps — fragile, mention how to use `populate_sdk` output instead.
- **§125A.5 multi-target — for a 6 YOE MCU dev, the question is "how do I attach to a *running* process?" rather than spawn a new one.** Show the `--attach <pid>` flow with VSCode (`"request": "attach"` instead of `"launch"`, plus `"processId"`). Currently the chapter only shows launch.
- **§125A.6 kernel module debugging via KGDB is shown in one config block.** This is *very* hard and the section under-explains. Spell out: KGDB needs `kgdboc=ttymxc0,115200 kgdbwait` on the cmdline; the target serial cable becomes the gdb transport, displacing the console; VSCode connects to a `socat` bridge that exposes the serial as a TCP port. Without this the example doesn't actually work for the reader.
- **§125A.9 pitfalls is good but missing the "MI parser" gotcha.** VSCode talks to gdb via MI (Machine Interface). Cross-gdb versions that don't fully implement MI cause silent breakpoint-not-set failures. Mention: if breakpoints set silently but never hit, try a newer cross-gdb (the crosstool-NG one built in Ch 122 is usually fine; an old Ubuntu gdb-multiarch may not be).

---

## Ch 126 — Closing

### AI wording / sledgehammer / buzzwords
- > "You have, in 125 chapters, gone from "I am an MCU engineer who has never used Linux" to "I can bring up a custom i.MX6ULL board with mainline U-Boot + mainline Linux + a hand-built rootfs + a real driver + secure boot + CI + OTA." That's not a small feat."
  - Inspirational-poster voice. Rewrite shorter: "In 125 chapters you've gone from MCU engineer to someone who can bring up a custom i.MX6ULL board with mainline U-Boot, Linux, a hand-built rootfs, drivers, secure boot, CI, and OTA. That's a lot of ground."
- > "This chapter is the bridge from here to the rest of your career as an embedded-Linux engineer."
  - "Bridge from here to the rest of your career" — graduation-speech cliche. Rewrite: "This chapter points to what to read and do next."
- > "The mental model it gives you is correct; just check current APIs in the kernel source when implementing."
  - Fine. Concrete advice.
- > "**free, comprehensive, current, and license-permissive**"
  - Four-adjective bold. Drop bold. The list is fine.
- > "The single best free-online resource for further study."
  - Sledgehammer "single best." Rewrite: "Probably the best free online resource for further study."
- > "Reading LWN weekly is *the* way to absorb kernel-development culture and stay current."
  - Italics + "*the* way" superlative. Rewrite: "Reading LWN weekly is one of the most reliable ways to absorb kernel-development culture and stay current."
- > "200 pages total; every new contributor should read it once."
  - Fine. Concrete imperative.
- > "Lurk for a month before posting."
  - Fine. Clear.
- > "Most importantly: now you have the **vocabulary** to read the kernel source, the **frameworks** to think about new problems, the **debugging instincts** to solve them, and the **community connections** to learn faster than you could alone."
  - Bold-quadrilateral, motivational-poster prose. Rewrite without the bold rhythm: "Most importantly, you now have the vocabulary to read kernel source, the frameworks to think about new problems, the debugging instincts to solve them, and the community connections to learn faster than alone."
- > "Build something. Ship it. Watch a customer use it for years. *That* is embedded Linux."
  - Three-fragment closer with italicized "*That*". This is the book's closing line; you may *want* it punchy. Acceptable as a closing flourish — but the italics on "That" is unnecessary. Drop them: "Build something. Ship it. Watch a customer use it for years. That is embedded Linux."
- > "Good luck. Send your first patch."
  - Fine. Short closer earns its keep.

### ESL readability
- > "Five books / sites that take you from where this book ends:"
  - Slash-list. ESL-friendly: "Five books and sites that pick up where this book ends:"
- > "Pay subscription ($10/month) is worth every cent if you work with Linux full-time."
  - Sales pitch. Rewrite: "A paid subscription ($10/month) is worth it if you work with Linux full-time."
- > "Bring questions; the community is welcoming."
  - Fine. Clear.
- > "Cultivate the soft skills — talking to product managers, defending engineering trade-offs."
  - Em-dash + parallel verbs. Rewrite: "Develop soft skills: talking to product managers, defending engineering trade-offs."
- > "you'll never design boards, maybe, but you'll read 1000s."
  - The "maybe" is awkward mid-sentence. Rewrite: "You may never design boards, but you'll read thousands."

### Needs more explanation
- **§126.1 #1 — LDD3 caveats need more pointing.** Beyond "specific APIs are dated," some chapters (USB, PCI) are now substantially outdated; the char-device, sleeping, locking, memory chapters are still excellent. A two-sentence "what's still good vs what's stale" guide would save the reader days of confusion when they hit deprecated APIs.
- **§126.4 path A / B / C — each is one paragraph.** Path A (Kernel hacker) — give one concrete first step: pick a driver in the IIO or GPIO subsystem and read every patch to its file in the last year. Mention `git log --follow drivers/iio/...`. Path B (Product engineer) — name one to-do: build a board with everything in Part VIII chained together. Path C (Embedded security) — mention concrete reading: Boneh's Coursera, plus the *ARM Architecture Security Reference Manual* for TrustZone-Av8.
- **§126.5 "skills outside Linux" — Rust is mentioned but the kernel's Rust-for-Linux status as of 2026 isn't.** As of 6.6 LTS, Rust is in mainline but mostly for new drivers. For a reader picking what to learn, this matters: Rust for new kernel work, C for everything else, C++ for application stacks. One sentence on the current state.



