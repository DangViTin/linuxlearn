# Part VIII — Debug/Production: Review

## Cross-cutting observations
- The "What/Why/Focus" preamble pattern is consistent and pleasant; reader sees scope before any code. Keep it.
- The book is consistently strong at building **STM32-to-Linux bridges in code/text** (e.g., `arm-linux-gnueabihf-gdb`, gdbserver workflow). Where it falls short is the **explicit "this is the same as X on STM32"** call-outs the persona needs. Almost every chapter could add one or two such MCU-bridge sidebars (Yocto vs Buildroot Kconfig vs Make; OP-TEE vs TZ on Cortex-M33; OTA A/B vs MCUBoot dual-bank).
- ASCII figures are *very* sparse. Architecture-heavy chapters (124 secure boot/OP-TEE, 125 OTA, 121A CI/CD, 123A Yocto layer) really need 1–3 ASCII diagrams each to anchor the text. Most chapters currently have zero.
- Cross-references to earlier parts are inconsistent. Some chapters (118, 119, 120) refer to "Ch 9", "Ch 36", "Ch 14"; others just say "as you saw in Part II". A single convention plus a tiny "you'll need from Part X" callout at top would help.
- Many chapters end with a long "Pitfalls" list which is gold for the persona — keep this pattern; it is one of the most MCU-engineer-friendly aspects of the book.
- Tool versions are usually omitted. For Yocto/OP-TEE/Mender/OpenOCD, **pinning to a tested version** (with one line: "tested on Yocto Kirkstone 4.0, OpenOCD 0.12.0, OP-TEE 4.1") would save the reader days. Add as a single top-matter line per chapter where applicable.
- Lab sections are good but rarely give expected output. For a reader who's never run `bitbake core-image-minimal`, expected-output snippets ("you should see ~3000 tasks scheduled, ~45 min on a 16-core box") would help calibrate "did this work or am I stuck".

## Ch118 — JTAG / OpenOCD / gdb

### Readability
- The opening "What" paragraph is one sentence stretched over 80+ words. Suggest splitting after "...halt the CPU at the very first reset vector instruction." into two sentences for breath.
- "the difference between 'I guess the boot fails somewhere in CCM init' and 'I see XTAL_24M is at 0 mV; the crystal isn't running.'" is great — keep these contrast lines, the reader cites them as motivation.
- "The tricky parts are: getting the adapter's USB-IDs right for OpenOCD, choosing the right *target* config..." — this is a colon-introduced list of four items run together. Convert to a bulleted list for scannability.
- "This is *how you learn* the bare-metal layer — by stepping every instruction and matching to the reference manual." Good line. Move to a callout box.

### MCU-engineer friendliness
- Section 118.1 introduces JTAG/TAP/CoreSight/DAP/ETM as if new. The reader has used JTAG on STM32 — call this out: "You've done this on STM32 with ST-Link or J-Link; the wire-level protocol is identical (IEEE 1149.1). What's new for Cortex-A: CoreSight wraps multi-core debug, the MMU complicates address interpretation, and there is no 'reset & halt the M-core at vector 0' button — you must explicitly configure the A-core's halt-on-reset bit." That single bridge would save 4 pages of confusion.
- "OpenOCD is the bridge" — bridge it explicitly: "On STM32 with ST-Link, the ST-Link USB driver IS your OpenOCD (proprietary). On i.MX6ULL with a generic FT2232H, OpenOCD plays the same role — speak USB to the adapter, expose port 3333 for gdb. Same gdb you used; different remote."
- `lx-symbols`/`lx-dmesg` will look magic. Add: "These Python helpers ship inside the kernel tree (`scripts/gdb/`); when you `gdb vmlinux`, gdb auto-loads them via the `.gdbinit` in build dir. You may need `add-auto-load-safe-path` in `~/.gdbinit` — gdb will tell you on first run."
- The reader has never run gdb against a *kernel*. Add a quick "what's different from app gdb": "no `run`, only `continue`; `bt` can show user-space + kernel mixed; software breakpoints only work in RAM (not in ROM bootrom or XIP flash)."

### Missing examples / figures
- No diagram of the JTAG state machine (Run-Test-Idle → Shift-IR/DR). For the persona who has used SWD-only adapters, a small ASCII FSM helps demystify "TMS steers".
- No figure of the OpenOCD architecture: `[Adapter USB] → [OpenOCD daemon] → port 3333 (gdb) / 4444 (telnet) / 6666 (tcl)`. Trivial ASCII, big clarity gain.
- No example of a real `imx6ull.cfg` excerpt (TAP IDCODE, DAP declaration). The chapter shows the user file but not the OpenOCD-shipped target file. A 10-line snippet would let the reader sanity-check their setup.
- Lab item 9 says "look up the i.MX6ULL JTAG disable fuse" without giving the fuse word/bit. Provide: SJC_DISABLE lives in OCOTP_LOCK / OCOTP_CFG5 — reader will not know which bank/word to read. Reference manual Ch. 5 (OCOTP) and Ch. 56 (SJC) — give the exact OCOTP shadow register address.
- Show one screenshot or representative `monitor reg` output so the reader knows what "good" looks like.

### Technical errors
- TAP IDCODE shown is `0x5ba00477`. That is the **CoreSight DAP** ROM-table IDCODE (ARM mfg 0x23B), NOT the i.MX6ULL chip JTAG TAP ID. The i.MX6ULL JTAG has multiple TAPs (SJC + DAP). The text says "JTAG tap: imx6ull.cpu tap/device found: 0x5ba00477" which is what OpenOCD prints for the DAP — fine, but worth noting there is also an SJC TAP at IDCODE `0x0891C01D` (or similar; verify per chip). Reader may otherwise be confused why one chip has multiple TAPs.
- "Cortex-A7 has 6 hardware breakpoints and 4 watchpoints (counts may vary)." Cortex-A7 actually exposes 6 HW breakpoints **and 4 watchpoints** as configurable per implementation. State this is implementation-defined, point at DBGDIDR for runtime detection: `monitor arm reg DBGDIDR` and decode BRPs/WRPs fields.
- "Software breakpoints (default `break`) replace the instruction with an undefined-instruction → exception → debug." On ARM, the BKPT instruction (T2: `0xBE00`; A: `0xE1200070`) is used, not undefined. Minor accuracy.
- `arm-linux-gnueabihf-gdb led.elf` followed by `load`: this works *only* if your bare-metal ELF has proper LMA/VMA and you've initialized DDR (or the load region is OCRAM). Add a sentence: "If you load to DDR, you must first do `monitor mmdc_init` or run U-Boot's SPL up to relocation; OpenOCD does not auto-init DDR on i.MX6ULL."
- "make DEBUG=1" for U-Boot is non-standard. The actual flag is `KCFLAGS="-O0 -g"` or editing config; U-Boot does not honor a DEBUG=1 makefile var by default. Verify and correct.
- `target/imx6ull.cfg` is **not** shipped with mainline OpenOCD as of 0.12 — mainline has `imx6.cfg`, `imx6_dq.cfg`, `imx6sx.cfg`, `imx6sl.cfg`. i.MX6ULL config is typically community-maintained or copied from Boundary/NXP. Either point to the community repo or warn the reader.

### Knowledge prerequisites missing
- Reader needs to know how to **build a U-Boot with debug symbols**. Reference Part III chapter or give the 3-line recipe.
- Reader needs to know **where to place `add-auto-load-safe-path`** in `.gdbinit`. Show example.
- KASLR for ARM 32-bit is rarely enabled by default — clarify whether iMX6ULL kernels even need `nokaslr`. Most ARMv7 kernels don't randomize.

### Other
- "Production fuse" lab item should be moved to its own callout with a giant warning: **blowing SJC_DISABLE is irreversible and prevents all future JTAG**. New readers will read fast and brick a chip.
- Adapter table calls J-Link EDU "non-commercial" — that is accurate but worth a one-liner on what counts as commercial (SEGGER licensing FAQ link).

## Ch119 — Kernel debugging without JTAG

### Readability
- "Spam in `dmesg` → `dynamic_debug` to filter." The phrasing "right tool for the right symptom" intro list is great; consider rendering as a table (symptom | tool | one-liner).
- "Master these and you debug embedded apps as productively as desktop ones." — duplicates a similar line in Ch 120 opening. Cut one.
- "Killer for performance investigation." Informal but works. Fine.

### MCU-engineer friendliness
- printk → reader knows `printf` over UART on STM32. Make the bridge: "printk is the kernel's printf, but rate-limited and async-flushed to a ring buffer. Unlike printf-over-UART, a stuck CPU's last printks may not reach the console — for last-words use `printk_safe`/`printk_nmi` paths or earlycon." Worth one paragraph.
- ftrace looks like SystemView/Tracealyzer — make that bridge explicitly: "If you've used SystemView or Tracealyzer for FreeRTOS, ftrace + KernelShark is the Linux equivalent: a per-CPU ring buffer of events with a timeline GUI. The kernel-side instrumentation is already in mainline; you just enable it."
- eBPF — no familiar MCU analog. Best bridge: "treat eBPF as 'safe DTrace inside the kernel'; you write tiny verified programs that attach to hook points and aggregate data, similar to how you might use ETM trace + filter on Cortex-M55, but software-defined and zero hardware."
- kgdb — reader knows OpenOCD+gdb. Bridge: "kgdb is gdbserver-in-the-kernel: same gdb protocol, transported over serial instead of TCP. Limitation: only the running task's full state; scheduled-out tasks are visible only via their saved-context fields."

### Missing examples / figures
- ASCII diagram of ftrace ring buffer per CPU + writer→reader → trace_pipe is missing. Two boxes and an arrow.
- The "right tool for right symptom" advice deserves a decision tree figure: oops? → decode_stacktrace; hang? → sysrq + ftrace_dump_on_oops; perf-glitch? → trace-cmd; live counter? → bpftrace.
- Example bpftrace one-liner for a *driver* author: "count probe() invocations and time them per device" — closer to what an embedded driver dev cares about than TCP retransmits.
- Example: minimum viable kdump config on iMX6ULL with crashkernel reservation. Currently text says "skip kdump on small RAM" but doesn't show the calculation. Reader has 512 MB; what's the actual `crashkernel=` value?

### Technical errors
- "default ring buffer ~128 KB; configurable via `CONFIG_LOG_BUF_SHIFT`." Actually default is 17 (128 KB) for many configs but ARM defconfigs often set 16 (64 KB) or 14. Be more precise: "default depends on defconfig; on `imx_v7_defconfig` it is `CONFIG_LOG_BUF_SHIFT=18` (256 KB)" — verify against current defconfig.
- "eBPF support on 32-bit ARM is limited" — true historically. Newer kernels (5.10+) have a JIT for arm32. Update wording: "eBPF JIT exists on arm32 since 4.14; the verifier is the same; BUT many bcc/bpftrace tools assume arm64 BTF, so 32-bit deployments often fall back to legacy kprobes." Cite kernel docs.
- "Function tracer adds ~50 ns per call; on a Cortex-A7 with 100 M function calls/sec, that's 5 % CPU." A Cortex-A7 at 528 MHz running glibc-heavy load is nowhere near 100 M kernel function calls/sec. Tone down: realistic kernel function rate is ~1–10 M/s under load; overhead is 5–10%.
- Section 119.5 oops output: "PC is at my_driver_probe+0x24/0x100 [my_driver]". The `[my_driver]` suffix only shows up after `lsmod` info is in `dmesg`; ARM32 oops format has been updated several times across 5.x → 6.x. Either pin to a kernel version or note "format varies slightly between 5.4 and 6.1".

### Knowledge prerequisites missing
- Reader needs to know how to enable `CONFIG_DEBUG_INFO_BTF`. One sentence: "depends on `pahole` ≥ 1.16 on the build host".
- Reader has never used a ring buffer in the kernel sense. One sentence explaining "overwrites oldest when full, ordered per CPU, lockless".
- Section 119.6 mentions `crash(8)` — totally new tool for the reader. Add 2 sentences orienting (it's like gdb but knows kernel data structures, scriptable in its own DSL).

### Other
- Pitfall about ftrace_dump_on_oops should be promoted from a "tip" deep in the chapter to an early callout — this is the single best ROI setting for a deployed device, takes 1 boot arg.
- Lab item 8 (vmcore on iMX6ULL) is described as "challenging — small RAM". Add a note: actually drop this lab for iMX6ULL; do it as a thought-exercise or on a 1 GB+ board. Otherwise readers spend a day failing.

## Ch120 — User-space debugging

### Readability
- Strong chapter overall, dense but well-organized.
- "Master these and you debug embedded apps as productively as desktop ones." — see Ch119 note; cut here or there.
- Section 120.9 "Real-world workflow" is great — keep this format and consider adding one to Ch118 and Ch119.

### MCU-engineer friendliness
- `gdbserver` ↔ OpenOCD: spell it out. "Same gdb you used on STM32. On STM32 the 'remote' is OpenOCD/ST-Link talking JTAG; here the 'remote' is gdbserver, a small user-space program, talking over TCP. The gdb side is identical."
- `strace` has no MCU analog — call this out as "the killer Linux-only tool. There is no equivalent on STM32 except trace pin instrumentation."
- `perf` is comparable to "ETM/PMU on Cortex-M with a debug probe" — reader has likely used DWT cycle counters. Bridge: "perf uses the same PMU hardware (cycle counter, cache-miss counter) you used through ITM/DWT on Cortex-M, but now mediated by the kernel and aggregated per process."
- Coredumps — fully new concept (no MCU analog). Add a paragraph: "On STM32 a crash means hardfault → reset; the closest analog is a fault-handler snapshot of registers/stack to flash. On Linux, the kernel sees SIGSEGV, dumps the entire process memory to a file, and the process exits — you load that file into gdb later." This will land.

### Missing examples / figures
- ASCII figure of gdbserver topology: `[Target: gdbserver:2345] ← TCP → [Host: gdb-multiarch + sysroot + unstripped ELF]`. Trivial, very high clarity for a new reader.
- An end-to-end Makefile fragment showing the cross-build with `-g -fno-omit-frame-pointer` and separate strip-for-target, keep-unstripped-for-host. The chapter mentions both but doesn't demonstrate.
- `coredumpctl` interaction is shown only briefly. Add a complete worked example: app segfaults → coredumpctl list → coredumpctl info → coredumpctl dump > core.app → host gdb. Reader benefits from seeing the full path.
- Flamegraph: include a tiny ASCII mock or a description of what to look for ("wide bars at the top = leaf functions burning CPU; tall narrow stacks = deep recursion").

### Technical errors
- "Sample at 99 Hz with call graphs (`perf record -F 99 -g`)... gives a statistical CPU profile with minimal overhead (~1 %)." Overhead at 99 Hz is closer to 0.1–0.5%, not 1%. Minor; the choice of 99 Hz (not 100 Hz) deserves a one-line explanation: avoids harmonic with periodic timers.
- "`ulimit -c unlimited`" — correct, but on most systemd-coredump distros, ulimit is irrelevant because systemd-coredump intercepts via `kernel.core_pattern = |/lib/systemd/systemd-coredump ...`. Add the "if you see no file in /var/log/core but `coredumpctl list` shows the dump, that's why".
- "PIE binaries with ASLR... Disable ASLR for repeatable debug: `setarch -R ./myapp`." `setarch -R` sets ADDR_NO_RANDOMIZE for that process only; system-wide is `/proc/sys/kernel/randomize_va_space=0`. Mention both.
- `gdbserver --multi :2345` and host `target extended-remote` — verify the exec-file path semantics on cross targets. `set remote exec-file` sets the *remote* (target) path; the *host* unstripped ELF is implicit from the local file. Worth one sentence.

### Knowledge prerequisites missing
- Reader has never set up an NFS root or has the cross-compile loop. The chapter says "copy to target (NFS or scp), gdbserver on target" — link/refer to the earlier chapter where NFS root was set up; otherwise the reader will spend the day fighting `mount nfs` errors.
- `gdb-multiarch` vs `arm-linux-gnueabihf-gdb` distinction: explicit table of "if your host distro has X, use X". Currently both are mentioned but the choice isn't clear.

### Other
- The "stuck daemon" workflow in 120.9 should be promoted to a sidebar or a dedicated "playbook" appendix referenced from later chapters (CI/CD test failures, field bug triage).
- Lab item 10 ("end-to-end customer-bug workflow... one-page bug report") is excellent for the persona but currently buried. Call it out as a capstone.

## Ch120A — Mainline patch submission workflow

### Readability
- "But the kernel community has strict, *unwritten* rules — wrong commit-message format, untested patches, replying to review with hostility, top-posting on mailing lists — these get your patch silently dropped no matter how good the code is. This chapter is the cultural primer the kernel docs don't write down." Excellent framing. Keep.
- The Section 120A.5 output is shown verbatim with names; either anonymize ("Maintainer A <m@example.com>") or update the names — currently includes real people (Shawn Guo etc.); the reader will copy-paste and embarrass themselves.
- Section 120A.10 reply-etiquette example is a strong worked example. The Q-and-A formatting reads well.

### MCU-engineer friendliness
- MCU engineers are used to GitHub PRs. The chapter says "Plain text email" but doesn't bridge: "This is alien to you if your last project lived on GitHub PRs. The kernel pre-dates GitHub and still uses 1990s-era email workflows; it is not gatekeeping, it is what scales to 30,000 patches/year across 4000 contributors. Once you set up git send-email, the workflow is actually faster than PR review for small patches."
- The DCO + Signed-off-by paragraph should explicitly contrast with CLA-based projects (which the persona may know): "Unlike a CLA (Contributor License Agreement) you might have signed for Apache or Google projects, DCO is a per-commit statement, not a one-time signed document."
- `git format-patch` and `git send-email` are unfamiliar even to git-fluent devs from a GitHub world. A 2-sentence "what these actually do" would help: format-patch writes mbox-format emails to disk; send-email pipes them through SMTP with thread-id headers.

### Missing examples / figures
- No ASCII or visual showing the v1 → v2 → v3 workflow with tag accumulation. A simple flow:
  ```
  v1 [PATCH] subj           → Foo: Reviewed-by ✓
       │                     Bar: requests change
       ▼
  v2 [PATCH v2] subj  with  Reviewed-by: Foo
       (changes addressed)   → Bar: Reviewed-by ✓
       │                     Maintainer: applied
       ▼
  in maintainer tree → -next → mainline
  ```
- Show a real example of a stable-tag-line addition (`Cc: stable@vger.kernel.org # v5.15+`). Backporting via stable tree is a common need not covered.
- Worked example is on a YAML binding for nRF24L01p. Good. Add a second worked example: a one-line *bug fix* (more representative of likely first patch). The current example is medium-complexity.

### Technical errors
- "checkpatch enforces: Line length ≤ 100 chars". Mainline relaxed to 100 in 2020 (commit `bdc48fa11e46`); older kernels enforce 80. Worth a note.
- "Cover letter sets the context maintainers need to triage. Send all patches together... `git send-email --to ... 0000-cover-letter.patch 0001-*.patch 0002-*.patch 0003-*.patch`" — typically you just `git send-email *.patch` or `git send-email outgoing/` after `format-patch -o outgoing/`. The example will fail because of the `00*.patch` glob behavior shown later (it works on most shells; mention this).
- "`git commit --amend  # OR rebase + rework`" for v2 — leaves no historical record locally. Suggest `git checkout -b v2` and `git rebase -i` workflow instead, with the `--in-reply-to=<msg-id>` example more prominent.
- "`b4 prep -n my-series` ... `b4 send`" — `b4 send` requires `b4 prep` initialization plus a properly formatted cover letter; reader will hit a wall. Cite `b4 prep --auto-to-cc`, `b4 send --reflect` (self-send-first).
- The example "nordic,nrf24l01p" compatible string format is correct (`vendor,part`), but DT binding examples are routinely rejected if `unevaluatedProperties: false` isn't paired with proper `$ref` to the bus binding. The example does include `allOf: - $ref: spi-peripheral-props.yaml#` which is good — keep that explicit and note it is required.

### Knowledge prerequisites missing
- Reader may not have a kernel.org account or know about Lore RSS subscriptions. Add a "set up your reading workflow" subsection: subscribe to relevant lists, set up Lore RSS, configure mutt/aerc/Thunderbird for inline replies.
- The reader needs `pahole` and other build-host packages; reference the Ch 122 / cross-toolchain prerequisites.

### Other
- Lab item 5 ("send a real bug report") is excellent and underused — promote it. Many readers will not produce a kernel patch but a clean bug report is high value.
- "Greg Kroah-Hartman's 'How to send patches to the Linux kernel'" — that doc has been merged into `Documentation/process/submitting-patches.rst`. Cite the in-tree path, not the legacy talk title.

## Ch121 — Capstone: custom board port

### Readability
- The "What/Why/Focus" preamble is dense but the "bring up serial, then DDR, then SD, then Ethernet, then your custom peripheral" sequence is gold. Bold it; reuse it as a recurring "bring-up mantra".
- "30 minutes later (mostly compile time), bootable card." — keep this confidence-builder line; it's exactly what the persona wants to hear.
- The Reflection section (121.10) is unique among the chapters. Keep. Consider replicating in 121A (CI capstone) and 123A (Yocto capstone).

### MCU-engineer friendliness
- The persona has done STM32 bring-up; bridge: "This is the Linux equivalent of bringing up an STM32 board with HAL_Init() → SystemClock_Config() → MX_GPIO_Init() → MX_UART_Init(). The order matters in both worlds; on Linux the artifacts are DT nodes instead of `MX_*` functions, but the dependency graph is identical."
- DDR Stress Tool will be foreign. The reader has used STM32CubeMX's clock configurator; DDR Stress Tool is "the same idea for DDR3 PHY calibration — vendor tool, fill in the chip datasheet, get a register dump, paste into your SPL." One sentence.
- "Forfaiting EVK config" pitfall is well-stated. Add an MCU bridge: "On STM32 you'd never copy a board.h blindly; same discipline applies to defconfig and DTS."

### Missing examples / figures
- Section 121.4 lacks a tree diagram of the U-Boot board file structure (`board/freescale/mx6ullevk/`). Show what files live there (mx6ullevk.c, Kconfig, MAINTAINERS, Makefile, plugin.S, lpddr2_timing.c). A `tree` output would help.
- No diagram of the iMX6ULL boot flow from BootROM → SPL → U-Boot → kernel that orients the reader to "where am I in this picture". Cross-reference Part III if it lives there.
- The "common failures + recovery" subsections are good but lack the corresponding *evidence* the reader will see. "U-Boot prints DCD garbage then dies" — show a real example of DCD garbage on serial (a string of `xx xx xx` or random bytes) so the reader can recognize it.
- Lab 5 (replace WM8960 with SGTL5000) needs a wiring diff or DT diff snippet, otherwise the reader has to look it up.

### Technical errors
- `cp configs/mx6ull_14x14_evk_defconfig configs/myboard_defconfig` — the EVK defconfig name in U-Boot mainline is `mx6ull_14x14_evk_defconfig` for older trees; newer trees use `imx6ull-14x14-evk_defconfig` or unified `imx6ulevk_defconfig`. Pin to a U-Boot version (the script later uses v2026.04 which doesn't exist yet — kernel/U-Boot release calendar shows latest as 2025.x for mid-2026). Use `v2025.04` or actual current LTS.
- `sudo dd if=u-boot-dtb.imx of=/dev/sdX bs=1k seek=1 conv=fsync` — for iMX6ULL boot from SD, the correct offset depends on the boot mode. SD/MMC boot ROM expects image at 1 KB offset (correct), but if reader chose eMMC primary boot from a partition the offset is 0. Add a note.
- `git checkout v2026.04` for u-boot, `v6.6` for linux, `2026.02` for Buildroot — all *future* tags. Replace with currently-released versions or `vYYYY.MM` placeholder with explanation.
- `sfdisk` heredoc partitions: writing `,,1M` first then `,64M,c,*` then `,,L` produces a starting 1 MB unallocated region (good for SPL), then a 64 MB FAT partition, then rest EXT4. But the comment says "1 MB unused | 64 MB FAT for boot | rest EXT4 for root" — verify with reader that this matches the sfdisk dialect. Modern sfdisk may complain about the leading `,,1M` syntax; safer is `--script` with explicit start offsets.
- "Buildroot's default init is BusyBox; verify `/sbin/init` exists." — Buildroot init is configurable (BR2_INIT_BUSYBOX, BR2_INIT_SYSV, BR2_INIT_SYSTEMD). Mention this; otherwise readers picking systemd config will be misled.
- `compatible = "maxim,ds3231";` is correct in mainline. Note that in some older trees the binding was `dallas,ds3231` — point at `Documentation/devicetree/bindings/rtc/dallas,ds*.yaml`.

### Knowledge prerequisites missing
- Section 121.4.4 mentions `mx6_mmcd_calib` struct but doesn't say which file declares it. Reader needs `arch/arm/include/asm/arch-mx6/mx6-ddr.h` and `board/freescale/mx6ullevk/spl.c`. Reference.
- The reader needs to know about the IVT/DCD structure of `.imx` files. Either reference Part III or summarize: "the `.imx` is U-Boot prefixed with the IVT header + DCD blob that BootROM reads."
- No mention of how to **recover** if SPL bricks DDR config. Add: "use the USB-SDP / serial-downloader path (`imx_usb`/`uuu`) — the BootROM accepts a fresh image over USB regardless of what's on SD."

### Other
- Lab 10 says "Upstream the DT (stretch)" — flag that DT for in-house boards rarely gets accepted upstream. Realistic outcome: maintainer asks "is this for a real product?" and rejects unless the answer is yes. Set expectations.
- The build script writes to `/mnt/boot` and `/mnt/root` without checking if they're already mounted — a real script needs `mountpoint -q` guards. Worth a pitfall line.
- The capstone reflection prompt is excellent; mention it should be reviewed at the start of the *next* board port — make this a habit, not a one-shot.

## Ch121A — CI/CD for embedded Linux

### Readability
- "Don't argue; address each point." That phrasing belongs in 120A not 121A — verify. (Yes, that line is in 120A.10; mentioning here just to flag the cross-chapter pacing.)
- "The cost is one $50 dev board + one Linux box + 4 hours setup." Concrete cost framing — reader loves this. Keep this pattern; do the same for OTA, Yocto chapters.
- The ASCII pipeline diagram in 121A.1 is excellent — exactly the kind of figure other chapters lack. Use it as a template.

### MCU-engineer friendliness
- "self-hosted runner" — clarify: "If you've used Jenkins or GitLab Runner for firmware CI, this is the same concept. GitHub Actions calls it 'self-hosted runner'; GitLab calls it 'runner'; the idea is a daemon on a Linux box that polls the cloud for jobs and runs them locally with access to your hardware." Worth one paragraph.
- `uuu` is unfamiliar. Bridge: "uuu is NXP's recovery-mode loader, equivalent to STM32CubeProgrammer's USB DFU mode for STM32 — load via USB when no other boot media works."
- A new reader may not know what "PR" / "merge queue" mean in the GitHub sense. One sentence orientation.

### Missing examples / figures
- No diagram of "the runner relationship": GitHub cloud ↔ self-hosted runner ↔ board(s) ↔ power/serial GPIO. Worth a 5-line ASCII (mostly there in 121A.1 but a labelled diagram with the runner-to-board USB connection would crystallize).
- The Labgrid section is too brief — show a complete `places.yaml` example and a Python pytest using `target = labgrid_client.acquire(...)`. Otherwise reader can't replicate.
- No example of how to handle test isolation/cleanup. Each test should restore the board to a known state — show a `pytest fixture` or shell script with `setup_board`/`teardown_board`.
- No flowchart of "what to do when a hardware-smoke test fails": is it a kernel bug, a flaky hardware, a CI infrastructure problem? Reader will hit this; give them a triage decision tree.

### Technical errors
- `uuu -b emmc u-boot-dtb.imx` followed by `uuu -b emmc_all u-boot-dtb.imx zImage imx6ull-myboard.dtb rootfs.tar` — `emmc_all` is a built-in script that already does everything including U-Boot. Running both is redundant and the second may fail because the board is no longer in SDP after the first. Simplify to one `uuu` invocation.
- `gpioset gpiochip0 18=0` — modern libgpiod 2.x changed the CLI: `gpioset --chip=gpiochip0 18=0`. Verify the libgpiod version and adjust.
- The smoke-test Python uses `port.in_waiting or 1` which can return 0 if buffer is empty; on a non-blocking serial this busy-spins. Use `port.read(port.in_waiting)` only if `in_waiting > 0`, else `port.read(1)` (blocking) — but with `timeout=1` configured this just costs ~1 s of polling latency. Note the implication.
- "`actions/checkout@v4`" with "`submodules: recursive`" — for a multi-repo build the user may not have submodules. Document the multi-repo strategy explicitly (matrix builds, `actions/checkout` per repo, or a manifest tool like `repo`).
- `ccache` caching pattern uses `key: ccache-${{ matrix.target }}-${{ github.sha }}` which would *never hit* (every commit has a unique SHA). Should be `key: ccache-${{ matrix.target }}-${{ github.ref_name }}-${{ github.sha }}` with `restore-keys` falling back to `ccache-${{ matrix.target }}-${{ github.ref_name }}-` then `ccache-${{ matrix.target }}-`. Worth fixing.

### Knowledge prerequisites missing
- Reader needs to know how to wire a USB-controlled power switch. Reference a part number (e.g., YKUSH-3, Yepkit; or a generic USB relay like Sainsmart). Without this hardware, the lab is blocked.
- GPIO control from userspace assumes the runner box has GPIOs (Raspberry Pi-like). Most CI hosts are x86 NUCs without GPIOs — the user needs a USB→GPIO bridge (FT232H or MCP2221). Note this.

### Other
- Pitfall about "`pull_request_target` is dangerous" — promote this to a callout box. PR-from-fork running arbitrary code on a runner with USB to your hardware is a real supply-chain risk. Worth a security paragraph.
- The schedule cron note is good. Add: never put secret-using jobs on cron without monitoring — silently-broken CI is worse than no CI.

## Ch122 — Build your own cross-toolchain

### Readability
- Section 122.2 multi-stage explanation is clear — uses indentation + arrows nicely. Keep this format for other multi-step processes (OTA flow, secure-boot flow).
- "Each `configure` line is a tour of GNU autoconf flags." Funny and accurate. Keep voice.
- 122.4 manual mini-build is a long shell script — break it into labeled subsections with prose between each, or readers will skim. Currently the rationale ("why disable libssp at stage 1?") is in a single paragraph at the end.

### MCU-engineer friendliness
- "for most users, `apt install gcc-arm-linux-gnueabihf` is fine. So why build your own?" — perfect opening for this persona. The three reasons land.
- ABI/triple discussion is one of the rare places where the persona is on familiar ground (gnueabihf vs gnueabi vs arm-none-eabi). Lean in: "The arm-none-eabi-gcc you used for STM32 has the same triple format: arch-vendor-os-abi. `none` (no OS) is replaced by `linux`, bare-metal newlib by glibc/musl. Otherwise identical structure."
- The "libgcc.a" of stage 1 will confuse readers who think of gcc as monolithic. One sentence: "libgcc is the support library gcc emits calls into (64-bit divide, unwinding, software float emulation); it's tied to the compiler version, not to libc."
- The `--with-sysroot` / `--prefix` / `--target` triplet confusion is real. 122.8 helps. Add a one-line memory aid: "prefix = where the *tools* live; target = what the tools *produce code for*; sysroot = the target's *root filesystem layout* on the host."

### Missing examples / figures
- A diagram of the toolchain dependency graph (which stage uses what artifacts from which previous stage) would beat the prose. Six labelled boxes with arrows.
- No example of what a *failed* bootstrap looks like — e.g., the error when `--with-sysroot` is wrong ("cannot find -lc"). Reader who hits this won't recognize it.
- Show the actual size breakdown: hello-world static glibc (~800 KB) vs musl (~8 KB) is mentioned, but a `size` output of both would be more memorable.

### Technical errors
- "libssp" (stack-smashing protector) is `--disable-libssp`, but modern gcc 13 also has `--disable-libssp` ignored in some configurations because it's been integrated. Check: as of gcc 12+, libssp is built unconditionally as part of libgcc. The flag may be silently no-op.
- "stage-1 gcc bootstrap requires C++ compiler" — true for gcc 11+ (which itself requires C++17 host compiler). For older gcc, C++98/03 suffices.
- The `glibc` `make install DESTDIR=$SYSROOT` is correct, but `--prefix=/usr` combined with that puts glibc in `$SYSROOT/usr/lib` — verify. With `--prefix=/usr` and `DESTDIR=$SYSROOT`, files go to `$SYSROOT/usr/lib`, but glibc also installs to `$SYSROOT/lib` for ld-linux.so.* — verify the install layout matches what stage-2 gcc expects.
- `glibc 2.34` was mentioned; current LTS-supported glibcs are 2.38 (Aug 2023), 2.39 (Feb 2024), 2.40 (Aug 2024). Update.
- "you can't easily swap later" (re glibc vs musl) — strictly true at the system level, but a toolchain can be rebuilt; what really can't change is the deployed rootfs. Sharpen.
- "Yocto SDK ... `./poky-glibc-x86_64-core-image-...-toolchain-....sh`" — the actual prefix can be `poky` or `nodistro` or custom; flag as variable.

### Knowledge prerequisites missing
- The reader doesn't know what `mpfr`, `gmp`, `mpc` are. `./contrib/download_prerequisites` fetches them — explain in one sentence: "GMP/MPFR/MPC are arbitrary-precision math libraries gcc uses for constant folding."
- `headers_install` target on the kernel will fail for a reader who never built a kernel. Reference Part IV chapter.
- `libc_cv_forced_unwind=yes` is an obscure glibc configure variable. One-line explanation: "asserts that the target kernel supports forced unwind; needed when configure can't auto-detect because it can't run target binaries."

### Other
- Lab 10 (Yocto SDK comparison) is good but should only appear *after* Ch 123A is done. Mark as forward-reference.
- Add a pitfall: "rebuilding the toolchain takes 30–90 minutes. Cache `~/.cache/ct-ng/` between runs."

## Ch122A — BSP → mainline migration playbook

### Readability
- Strong, well-paced chapter. The CVE-burndown framing in §122A.1 will land hard with anyone who has to convince management.
- "What about... your fork is on you" sentence in Ch 120A's preamble; here the analogous "the BSP is *frozen* — no upstream updates" lands well. Italics on *frozen* is a nice touch.
- "Months of work, not years." — keep this confidence-builder; it's hopeful realism.

### MCU-engineer friendliness
- The persona may have inherited an STM32CubeIDE project on a 2-year-old HAL version and felt similar pain. Bridge: "If you've ever inherited an STM32 project pinned to HAL v1.16 when the current is v1.27, you've felt this in miniature. The Linux version is the same problem at 1000× scale because you depend on so many more upstream components."
- "patch inventory" of 7000 patches is a foreign scale. The reader has tracked tens of patches in firmware repos. Add: "this is not unusual — vendor BSPs accumulate 5–10K patches over 5 years. It's not a code-quality problem; it's vendors keeping local fixes while waiting on mainline merges."

### Missing examples / figures
- The subsystem dependency graph in 122A.4 is ASCII and good, but could be richer — add cross-arrows (e.g., MMC depends on regulator and clk). Currently linear; reality is a DAG.
- No example of a "patch classification spreadsheet" template. Reader would benefit from a downloadable CSV/Excel template.
- The §122A.9 worked example is too high-level — show one actual cherry-pick conflict and how to resolve it (an i.MX6ULL clock-driver hunk that BSP changed and mainline refactored).
- No timeline visualization. Convert "Phase 1 (week 1–4)... Phase 6 (week 21–24)" into a Gantt-style ASCII.

### Technical errors
- "i.MX6ULL: mainline support is *excellent* as of 6.6" — true. Cross-check though: imx-csi has had multiple churns; SAI driver is in mainline but the SOF/ALSA UCM may still need vendor configs. Add nuance.
- "imx_v7_defconfig" is one option, but for iMX6ULL specifically `multi_v7_defconfig` is more common in newer kernels for arm32 multi-platform builds. Mention both.
- "PREEMPT_RT" listed under "buys" for mainline migration — RT was merged in 6.12 (Sep 2024); 6.6 LTS has it as patches only. Update wording.
- "CVE-2017-1000405 (Dirty COW2)" — the parenthetical "Dirty COW2" is informal; the canonical name is "Dirty COW THP race"/Huge Dirty COW. Use correct name.
- "(gcc 6.x) won't compile mainline (needs gcc 8+)" — kernel 6.6 actually requires gcc 5.1 minimum but recommended 11+. Sharpen.

### Knowledge prerequisites missing
- Reader needs to know what an LTS kernel is and the LTS cadence. One sentence: "every 5th release becomes an LTS, maintained for ~6 years; 6.6 LTS until Dec 2026 (regular), extended via CIP/Civil to 2030+."
- `cve-checker` is mentioned — not a well-known tool. Cite specifically: `cve_checker` from NIST, or `vuls`, or `linux-kernel-cve-checker`. Pick one.
- `KSPP` (Kernel Self Protection Project) is mentioned in "Going deeper" without explanation. Two-sentence intro.

### Other
- §122A.8 "when NOT to migrate" is good but should be a callout/sidebar box. Reader currently passes over it as another section; flagging "STOP - decision point" would highlight.
- The "2000 mainline-merged: delete" breakdown is suspiciously round. Tag as illustrative or give one real example case study with actual numbers (Pengutronix and Bootlin have published migration retrospectives).
- Lab item 8 (CVE diff) — add: tool-specific instructions ("use `https://github.com/kernel/linux/issues` is wrong; use `cve.mitre.org/cgi-bin/cvekey.cgi?keyword=linux+kernel` or NIST NVD's API").

## Ch123 — Yocto vs Buildroot

### Readability
- The opening table is the strongest single page in the chapter. Keep it.
- "Most teams overestimate their multi-variant complexity and end up with Yocto sledgehammers cracking Buildroot walnuts." Excellent line; cite this in the "when each wins" callout.
- "30 min later" for Buildroot vs "1–4 hours" for Yocto initial — make these numbers more memorable with a sidebar "what you can do while you wait" comparison.

### MCU-engineer friendliness
- The persona has never seen bitbake. The reader will be confused by why a single recipe consists of Python code with embedded shell. Bridge: "A bitbake recipe is *like a Makefile augmented with metadata in Python*. The `do_compile` is a shell function (like a Makefile rule body); the `SRC_URI`, `DEPENDS`, etc., are metadata variables bitbake parses (like Make variables). The 'Python' is mostly bitbake's data-flow plumbing, not full Python programs."
- Buildroot's analogy: "If you've used the Linux kernel's `make menuconfig`, you've used 90% of Buildroot." That single sentence will land.
- For "layer priorities like CSS" — perfect analogy, but persona may not know CSS layering. Add: "or like Yocto's overrides are like git rebase squashing — later edits win."
- BitBake's task model (`do_fetch`, `do_unpack`, `do_patch`, `do_configure`, `do_compile`, `do_install`, `do_package`) is invisible to readers. A small ASCII pipeline showing them in order would demystify "BitBake is task-based."

### Missing examples / figures
- No diagram of layer hierarchy. The chapter mentions "layers stack like CSS"; show it ASCII:
  ```
  ┌─ meta-mybsp-distro (priority 20) ──┐
  │  ┌─ meta-mybsp-myapp (15) ──────┐  │
  │  │  ┌─ meta-mybsp (10) ────┐    │  │
  │  │  │  ┌─ meta-freescale (7) ─┐ │  │
  │  │  │  │  poky (5)            │ │  │
  ```
- Show one head-to-head build benchmark: Buildroot vs Yocto for "same image"; include disk usage during build, peak RAM, final image size.
- The §123.7 "same recipe in both" example is too clean. Show a recipe that's *easy in Buildroot, hard in Yocto* (or vice versa) — that's where the choice actually matters.

### Technical errors
- "Buildroot ~3000 packages; Yocto ~10,000+" — Yocto's `meta-openembedded` adds ~5000; total available across layers can exceed 15K. Sharpen.
- "`make sdk`" in Buildroot — actual target is `make sdk` only after configuring with `BR2_PACKAGE_HOST_TOOLCHAIN_EXTERNAL` or building with shared-library targets. Mention `make graph-depends` for understanding.
- "BB_HASHSERVE" gives strong reproducibility — slightly misleading. `BB_HASHSERVE` is the equivalence-hash server (skips rebuilds where output would be identical). True reproducibility requires `INHERIT += "reproducible_build"` + SOURCE_DATE_EPOCH + a host-tool freeze. Clarify.
- "core-image-minimal ~60 MB rootfs" — depends heavily on packagegroups. Default poky `core-image-minimal` is ~10 MB. The 60 MB figure may be for `core-image-base` or `core-image-full-cmdline`. Verify and correct.
- "Buildroot: `make myapp-rebuild` for incremental." Actually `make myapp-reconfigure` rebuilds from configure step; `make myapp-rebuild` rebuilds from build step. Cite the manual section.
- "Use Bootlin's pre-built toolchains... `arm-buildroot-linux-gnueabihf.tar.bz2`" — Bootlin's archive uses several naming schemes; pin to the actual download URL pattern.

### Knowledge prerequisites missing
- Reader doesn't know what an OE-Core or poky-tiny is. Add one sentence each.
- `DISTRO_FEATURES` vs `IMAGE_FEATURES` is introduced in 123A but not here — readers may want a forward reference.
- "SBOM" (Software Bills of Materials) thrown out without explanation. One-line.

### Other
- §123.6 "When neither is right" is good — promote to a sidebar. Many readers will fit here without realizing.
- Pitfall about Yocto on macOS/Windows — add a positive: "Yocto under WSL2 with `kas-container` is now a fully-supported workflow as of 2024."

## Ch123A — Yocto layer development in depth

### Readability
- Strong, well-paced. The "layers stack like CSS" line repeats from 123; consider varying.
- "easy in Buildroot, hard in Yocto" style contrast would help, but this chapter is in-depth Yocto so OK to drop.
- "License license license." Good emphatic line. Keep.

### MCU-engineer friendliness
- `bbappend` is alien syntax. Bridge: "A `.bbappend` is the Yocto equivalent of a patch file — you don't fork the recipe; you ship a sidecar that says 'when you build this recipe, ALSO do this'. The closest STM32 analogy: a `*_overrides.h` that injects into a vendor HAL. Both keep your changes out of the upstream tree."
- `${PN}` (package name), `${WORKDIR}`, `${D}` are sprinkled throughout without a legend. Add a glossary box of the top 10 BitBake variables.
- `inherit cmake` / `inherit autotools` / `inherit systemd` — explain "these are bbclass files that define the do_* tasks for that build system". One paragraph.
- `RDEPENDS:${PN}` syntax with the colon override is new since Yocto 3.3 (Honister). Older readers know the underscore form (`RDEPENDS_${PN}`). Mention both.

### Missing examples / figures
- A figure of the example 4-layer stack (meta-mybsp + meta-mybsp-mini + meta-mybsp-myapp + meta-mybsp-distro) showing what each owns. Important because the chapter introduces all of them at once.
- The `wic` partition layout deserves a labelled disk-image diagram (raw offset → boot partition → rootfs A → rootfs B → data) — same diagram as Ch 125 if possible (cross-reference). Currently text-only.
- Show the actual filesystem layout of a `recipe-sysroot` after a build — this is what readers will navigate when something fails.
- No example of using `devtool modify` for iterative recipe development — single most-time-saving Yocto tool. A 5-step worked example would be high value.

### Technical errors
- `LAYERSERIES_COMPAT_mybsp = "kirkstone scarthgap"` — actual release names should be consecutive (kirkstone, langdale, mickledore, nanbield, scarthgap, styhead). Verify and provide the latest.
- "Priority `10` is higher than `meta-freescale`'s 8" — meta-freescale's default priority is `5` in older releases, `6` in newer. Check current.
- `IMAGE_FEATURES += "ssh-server-dropbear"` — that's correct. But the example also has `INHIBIT_PACKAGE_STRIP = "0"` which is the *default* — it's set to "0" to enable stripping, "1" to keep symbols. The comment "Strip debug info for production" matches but the value is the default. Either drop the line or invert it to make a point.
- The wks file has `--align 1024 --size 16` for the boot partition — that's 16 MB, very small for kernel + DT + initramfs. Production needs 64 MB+. Comment shows `64 MB FAT` but value is `--size 16`. Inconsistency.
- `oe_runmake CC="${CC}" CFLAGS="${CFLAGS}" LDFLAGS="${LDFLAGS}"` in the myapp `do_compile` — `oe_runmake` already passes these. Redundant; will work but signals "the author copy-pasted".
- `SRCREV = "abc123def456"` example uses a 12-char hash. Yocto strongly recommends full 40-char SHA1.
- `PV = "1.0+git${SRCPV}"` — `${SRCPV}` was removed in Scarthgap. Modern syntax is `PV = "1.0+git${SRCREV}"` or rely on `inherit autotools` defaults.

### Knowledge prerequisites missing
- Reader needs to know what `${PN}`, `${PV}`, `${PR}`, `${D}`, `${S}`, `${WORKDIR}` mean. A reference table.
- Reader doesn't know what `core-image` bbclass does. One paragraph.
- `MACHINEOVERRIDES =. "mx6ull:"` syntax — the `=. ` operator is BitBake-specific (prepend with space). Explain.

### Other
- "License license license" pitfall is correct but understated. Add: "any commercial product missing license metadata for a GPL component is in *immediate* compliance violation; one open-source-savvy customer can sue."
- §123A.10 "SRC_URI cache" should be promoted — for air-gapped builds this is non-negotiable; readers in regulated industries (medical, automotive) hit this on day 1.

## Ch124 — Secure boot (HAB) and OP-TEE

### Readability
- The ASCII diagram of normal world / secure world in §124.8 is the strongest figure in Part VIII. Verify the box-drawing characters render in your toolchain.
- "fail-open is impossible" — strong statement. Cite where in i.MX6ULL RM this is enforced (specifically Boot ROM behavior; ROM jumps to a hang-loop on signature fail).
- The chapter is dense; reader will struggle. Break into "secure boot" and "OP-TEE" subchapters or at minimum add a visual divider between §124.7 (dm-verity, the secure-boot story end) and §124.8 (TrustZone, the OP-TEE story start).

### MCU-engineer friendliness
- TrustZone — many readers know it from Cortex-M33 / M55 (TrustZone-M). Bridge: "If you've used STM32L5/U5 TrustZone-M, the i.MX6ULL Cortex-A TrustZone is the same concept at the application-processor scale — secure/non-secure worlds, SAU-like memory partition, but with a real Trusted OS (OP-TEE) running in the secure world rather than the firmware-as-secure-world arrangement on Cortex-M."
- OP-TEE TAs — bridge to "this is like writing a small RTOS task that lives in the secure world; cross-world communication is the equivalent of an IPC mailbox but mediated by the SMC instruction." One paragraph.
- The `SMC` instruction will be new. State: "SMC is `0xE1600070` on ARM A32; it traps the CPU into Monitor Mode, identical in role to SVC for syscall but targeting the secure-world entry point."
- HAB versus the U-Boot world the persona has seen with sboot/MCUBoot. Bridge: "If you've used MCUBoot to verify firmware images on STM32, HAB is the *hardware-enforced* version of the same idea — the ROM does what MCUBoot's bootloader does, but you can't modify the ROM, so an attacker can't disable the verification step."

### Missing examples / figures
- No diagram of the SMC calling convention / world switch register flow. Worth 10 lines of ASCII showing R0–R7 used as function args, world banking of registers, return path.
- No diagram of the dm-verity Merkle tree structure. Important because the reader will not have used dm-verity before; understanding "hash of each block, hashed in tree, root in cmdline" needs a picture.
- The CSF example mentions specific addresses (`0x877FF400`) without saying where they come from. Show how to derive these from your linker map or `mkimage` output.
- No worked example of fuse-blow command sequence for SRK_HASH (OCOTP_SRK0..SRK7) — currently the chapter says "8 OTP fuses" but doesn't show U-Boot's actual `fuse prog` command for the SRK bank.
- OP-TEE world topology is shown but no "how does Linux discover OP-TEE" walkthrough. Show the DT node:
  ```
  firmware {
      optee {
          compatible = "linaro,optee-tz";
          method = "smc";
      };
  };
  ```

### Technical errors
- "SRK (Super Root Key): a 4096-bit RSA public key. The hash of the SRK is **blown into eFuses** during manufacturing." HAB4 supports 1024/2048/3072/4096 RSA; reference manual says 4096 is recommended but smaller works. Also HABv4 supports ECC keys in newer CSTs. Sharpen.
- "the SoC's mask ROM hardcodes this behavior" — HAB type (open vs closed) is controlled by the SEC_CONFIG[1] fuse, not the ROM logic. ROM checks the fuse and adjusts behavior. Slight phrasing issue.
- `fuse prog 0 6 0x2` for closing HAB — the actual fuse word for SEC_CONFIG on iMX6ULL is OCOTP bank 0, word 6, bit 1 (=0x2). Verify against reference manual fusemap (the chapter cites the right idea but the bit position deserves an explicit table cross-ref to RM Section 5.1 Boot Fusemap).
- "Boot from USB-SDP with HAB closed... USB-SDP still works because Boot ROM accepts a signed binary over USB" — true, USB-SDP path still goes through HAB verification. Good. But the framing "Boot ROM accepts a signed binary over USB" should clarify "still requires the signature; the ROM doesn't drop verification just because the source is USB."
- OP-TEE on iMX6ULL: `PLATFORM=imx-mx6ull` — the actual platform name in OP-TEE is `imx-mx6ull` (with the `mx-` prefix for upstream OP-TEE). Modern OP-TEE may have moved to `imx-mx6ullevk` or `imx`. Verify against current OP-TEE source.
- `CFG_TZDRAM_START=0x9e000000 CFG_TZDRAM_SIZE=0x02000000` — reserves the top 32 MB of DDR for the secure world. The kernel must also be configured to *not* use this region (DT `memreserve` or `memory@80000000` truncated to 0x80000000-0x9DFFFFFF). The chapter omits this required kernel-side change.
- "TEE_TIMEOUT_INFINITE bugs" — TEE_TIMEOUT_INFINITE is the canonical wait-forever constant in GPD TEE Internal API, not a bug name. Reword.
- `mkimage -f kernel.its -K imx6ull-myboard.dtb -k keys/ -r kernel.itb` — flags are `-f` (input its), `-k` (keydir), `-K` (DTB to update with key), `-r` (mark as required); output goes after positional. The example has `-K` and `-k` reversed in description vs flag usage. Verify.
- "U-Boot env on writable storage with secure boot" pitfall — also: U-Boot must be built with `CONFIG_ENV_IS_NOWHERE` or `CONFIG_ENV_IS_IN_*` with appropriate signing. The pitfall is on point.

### Knowledge prerequisites missing
- Reader needs to know what an X.509 certificate is at a basic level (the "public key + signature" structure). One sentence.
- Reader needs to know what PKCS#11 / HSM is. One sentence per term in a glossary box.
- "anti-rollback" mentioned as a pitfall but `compatible` versioning in FIT isn't a standard anti-rollback mechanism — usually it's a monotonic counter in OTP fuses or in U-Boot env (signed). Clarify the actual mechanism.

### Other
- §124.3 "Key ceremony" is the most important section in the chapter. Promote to a callout/sidebar; make it impossible to skip. Many readers will skim and lose private keys.
- §124.5 "Closing HAB — the irreversible step" — surround with red banner "DESTRUCTIVE OPERATION".
- The lab item 4 "(IRREVERSIBLE!) Close HAB on a sacrificial board" should be removed or moved to an appendix; most readers don't have spare iMX6ULL parts to sacrifice. Replace with "simulate via HAB open mode".

## Ch125 — Field updates (RAUC, SWUpdate, Mender)

### Readability
- Good chapter. The "A/B is the universal pattern" focus statement is concise and the rest follows.
- The §125.8 "Boot-success detection — the actually-hard part" is undersold by title; this is one of the genuinely subtle topics. Frame it as "the part that engineers always under-design".
- The full disk-layout ASCII in §125.2 is excellent. Keep it.

### MCU-engineer friendliness
- MCU readers know MCUBoot. Bridge: "RAUC, SWUpdate, and Mender are conceptually MCUBoot for Linux: A/B partitions, signature verification on boot, rollback on failure. The Linux version adds: filesystem-level update granularity, network-fetched bundles, fleet management, delta compression."
- Watchdog reference (Ch 51A) is good. Reinforce: "Without a hardware watchdog enabled at boot, rollback never triggers if the new image hangs — it just hangs."
- Casync / delta updates have no MCU analog. Bridge: "Imagine MCUBoot but where instead of pushing a 2 MB binary, you push a 50 KB diff — over an LTE link this is the difference between '$5/device/year' and '$5/device/month'."

### Missing examples / figures
- The Network architecture diagram in §125.4 is good but informal. Tighten the ASCII.
- No worked example of an actual `RAUC_BUNDLE_HOOKS` recipe — readers will want a custom pre/post-install hook (the "kill myapp before update, restart after" pattern).
- Show a real example of a `latest.json` file format the device polls (the chapter mentions it without showing the schema).
- No example of how staged rollouts are actually implemented at the server end (one-line nginx config + a hash-bucketing script).

### Technical errors
- "RAUC bundle (squashfs+manifest+signature)" — RAUC bundles since v1.0 (2018) default to squashfs but support cpio archives via `RAUC_BUNDLE_FORMAT`. Mention.
- "`bootloader=uboot`" in `system.conf` — valid. Also `barebox`, `grub`, `efi`, `custom`. Worth a one-liner.
- `BOOT_A_LEFT=3` countdown — actually U-Boot's `bootcount` mechanism is more standard than per-slot `_LEFT` variables in many RAUC examples. The "_LEFT" approach is RAUC's `barebox` integration; on U-Boot, the canonical script uses `bootcount` + `BOOT_ORDER` only. Verify and clarify which bootloader you're targeting.
- "`rauc status mark-good`" — actual command is `rauc mark-good` (or `rauc status mark-good` depending on version). Pin to a RAUC version.
- "casync (Lennart Poettering's tool) chunks images" — actually casync was originally Lennart's but the active fork is `desync` (golang reimplementation by folk at folbricht). Mention.
- "Bundle larger than rootfs partition" pitfall — RAUC also requires the bundle source space (working area) to be available during install; on systems with no spare partition, the bundle is streamed. Note streaming-vs-staged installs.
- Mender's `inherit mender-full` plus `INHERIT += "mender-full"` — `inherit` is recipe-level, `INHERIT` is `local.conf`/distro level. Putting both in an image recipe is redundant and the `INHERIT` form is wrong place. Correct.

### Knowledge prerequisites missing
- Reader doesn't know U-Boot environment from prior chapters (or only superficially). Reference Part III chapter and explain "U-Boot env is a small block of key=value pairs on persistent storage that survives reboots".
- `dm-verity` was introduced in Ch 124 — cross-reference: dm-verity locks the rootfs; OTA must therefore replace the entire verity'd image, not patch files in place. Worth a sentence.

### Other
- The "no anti-rollback" pitfall is critical; promote. A signed-but-old firmware is a real attack vector (downgrade to a vulnerable signed version).
- Lab 7 "force a bad update" is the most important lab; promote to a featured exercise. This is where teams discover their watchdog isn't really configured.
- The "rolling out untested update" pitfall mentions "5% failure threshold" — recommend a real metric (Mender's deployment-failure-percentage; Pengutronix has published recommended thresholds).

## Ch125A — VSCode + gdbserver remote-debug workflow

### Readability
- Clear, focused. Good length. The persona will read this once and refer back.
- "It's not a debugger; not an editor for serious projects. But for 'I'm reading the kernel source and want to navigate quickly,' nothing beats it." Honest, good. Keep.

### MCU-engineer friendliness
- Excellent opening sentence: "many readers come from microcontroller backgrounds where the IDE *is* the debugger (Keil, IAR, STM32CubeIDE)." Lean into this all the way through. Treat each VSCode concept as "the equivalent of Keil's debug-launch dialog".
- The `c_cpp_properties.json` is unfamiliar. The bridge is "this is the cross-toolchain equivalent of pointing Keil/IAR at the right MCU pack + CMSIS headers — without it, IntelliSense thinks you're targeting x86." Make this explicit.

### Missing examples / figures
- No screenshot or labelled VSCode screenshot. Persona is visual; one screenshot of the debug panel hitting a breakpoint would be worth 1000 words.
- No diagram of "what talks to what": VSCode → MI protocol → gdb-multiarch → TCP → gdbserver → ptrace → process. Six labelled boxes.
- The KGDB example (§125A.6) glosses too quickly. Show the U-Boot/kernel command line setup (`kgdboc=ttymxc0,115200 kgdbwait`) and the gdb-side setup as a unified worked example. As-is the reader can't replicate.
- Show a `launch.json` with `${env:VAR}` variable substitution for sysroot paths — current example has hard-coded paths that change every build.

### Technical errors
- `gdbserver --multi :2345 &` over SSH from VSCode — the `&` will likely cause the SSH session to close immediately and kill gdbserver. Use `nohup` and a `disown`, or `ssh -f` (background mode). Verify.
- `"miDebuggerServerAddress": "192.168.1.100:2345"` — combined with `"request": "launch"` is correct in modern cpptools (≥1.10). Older versions required `"request": "attach"` + `"processId": 0` for remote launch. Worth a compatibility note.
- `"intelliSenseMode": "linux-gcc-arm"` — modes were renamed in cpptools 0.30+; older readers may have `"gcc-arm"`. Cite the version.
- §125A.6 "KGDB on port 1234" — KGDB uses serial, not TCP. The 1234 is gdbserver's default for kgdb-over-tcp via `kgdboe` (Ethernet) which is experimental and not in mainline. Standard KGDB is over serial. Either correct to serial path or clarify the kgdboe caveat.
- `"add-auto-load-safe-path /home/dev/yocto/build/tmp/work/.../linux/scripts/gdb/"` — `add-auto-load-safe-path` is a GDB command (no leading dash) but in MI mode it needs `set auto-load safe-path`. Verify.

### Knowledge prerequisites missing
- Reader needs to know about JSON syntax (trailing comma errors, comment policy). VSCode allows JSONC (with `//` comments) for `launch.json` but not for all files. Mention.
- VSCode tasks JSON has its own quirks (`"isBackground": true` semantics). One-paragraph orientation.

### Other
- Lab 10 (Source Insight 30-day trial) — Source Insight in 2026 is increasingly niche; consider replacing with "Lemur" or "Sourcegraph" (modern code-navigation tools).
- §125A.5 multi-target is good; add "use VSCode workspaces for very large multi-board setups; one workspace per board avoids settings collisions".

## Ch126 — Closing: what to read next

### Readability
- Short, well-paced, hopeful. The closing tone is right for the persona.
- "Build something. Ship it. Watch a customer use it for years. *That* is embedded Linux." Solid landing.
- §126.6 "if you remember nothing else" is the right number (7 items). Reader can memorize this page.

### MCU-engineer friendliness
- Acknowledge the persona one more time at the very end: "You came in as a microcontroller engineer; you leave with a foundation in embedded Linux. The MCU intuitions you brought — about timing, hardware, faults, code size — are not obsolete; they're now *augmented* with the Linux layer's intuitions."

### Missing examples / figures
- A "skills tree" diagram showing what you've now picked up and what each next-path adds.
- A timeline or "your first 12 months as an embedded Linux engineer" plan would land — week 1: subscribe to lists; month 1: send first patch; month 3: first board port; month 6: lead a CI setup; month 12: own a subsystem.

### Technical errors
- "**Linux Device Drivers, 3rd Ed. (LDD3)**" — LDD3 is from 2005, kernel 2.6.10. Many APIs are obsolete. Strongly recommend pairing with `Linux Kernel Programming` by Kaiwan Billimoria (2021/2024, modern APIs) — currently the best modern equivalent. LDD4 was never written.
- "Five books / sites" — only 5 listed; consider adding `linux-kernel-labs.github.io` (modern OS course; uses recent kernels).
- "linux-imx@nxp.com — ~5/day" — actually moderately busy; closer to 20–30/day. Verify.
- "Linux Plumbers Conference (annual; ~Sep–Oct)" — actually Sep–Nov varies. Cite https://lpc.events.

### Knowledge prerequisites missing
- No reference to LKML netiquette, which the persona has been taught in Ch 120A. Mention that 120A is the practical guide and `Documentation/process/` is the canonical version.

### Other
- §126.4 "Three further specializations" — add Path D: "Embedded Linux trainer/educator" for readers who would write the next book.
- Acknowledgements section is a placeholder. Note: must be filled in before publication.
- Consider adding a single page "lessons the book didn't cover" — what's out of scope (RT, multimedia/V4L2 pipelines, ML on edge, automotive AUTOSAR/Adaptive AUTOSAR) so the reader knows where the borders are.


