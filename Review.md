# Review — Embedded Linux on i.MX6ULL (book/)

> **Reviewer brief.** Each Part below was reviewed by reading every chapter file in full, channeling an MCU engineer with strong HW/firmware background but very little Linux experience. Reviewers were told to focus on: readability (choppy sentences, awkward phrasing), MCU-engineer friendliness (missing bridges from MCU world to Linux concepts), missing examples / ASCII figures, technical errors against the iMX6ULL reference manual, knowledge prerequisites used before being defined, and (for Part VII cookbook) whether each chapter went deep enough to show driver internals rather than just "enable Kconfig + paste a DT node".

> **How to use this.** Each Part has a *Cross-cutting observations* block — these are issues that appear across many chapters and are the highest-leverage to fix. Then per-chapter sections list specific, actionable bullets with quoted text where helpful. Subheadings inside a chapter are only present when the reviewer found something to say.

---

## Executive summary — fix these first

The findings below recur across multiple parts. Fixing them once will improve dozens of chapters at the same time.

### A. Technical errors that propagate across multiple chapters

1. **"No L2 cache on i.MX6ULL" is wrong.** Ch04 §4.6 and Ch05 §5.3/§5.4 both state this; the IMX6ULLRM (RM lines 9738, 9766, 10014, 22167, 22212) lists a **128 KB unified L2** inside the Cortex-A7 MPCore platform. Reframe as "no external PL310 controller (the i.MX6Q has one); the MPCore platform contains an integrated 128 KB L2." Fix early — later chapters reference this.
2. **`class_create(THIS_MODULE, "name")` everywhere — wrong since kernel v6.4.** The `owner` argument was removed (commit 1aaba11da9aa). Appears in Ch38, Ch40, Ch41, Ch64, Ch65 and many cookbook chapters. Modern call is `class_create("name")`. Pick a target kernel version and state it once, then update snippets.
3. **`i2c_driver.probe` two-argument signature is wrong since v6.3.** Modern kernels expect `int probe(struct i2c_client *client)` only. Appears in Ch46 and in cookbook chapters Ch65/67/68/70/72/73/75/76/79/80/81 — the cookbook silently regresses from what Part VI just taught.
4. **`platform_driver.remove` / `i2c_driver.remove` returns `void` since v6.11.** Multiple chapters still show `return 0;`. State the kernel target once and rewrite.
5. **SPL OCRAM budget overstated.** Ch20 §20.3 says "~100 KB" — the actual free OCRAM window is **68 KB** (RM puts the ROM working area at 0x00900000–0x00906FFF). NXP's `mx6ull_14x14_evk` defconfig caps `CONFIG_SPL_MAX_SIZE` near 64 KB. Reword to "~64 KB practical SPL budget."
6. **DTS path is stale for kernels ≥ v6.5.** Ch25/26/27/27A reference `arch/arm/boot/dts/imx6ull-*.dts`. Since v6.5 i.MX files live under `arch/arm/boot/dts/nxp/imx/`. The book pins to v6.6 in Ch25, so every cited path is wrong. Either pin to v6.1 LTS or update all paths globally.
7. **"PREEMPT_RT is out of tree / partially in mainline" is stale.** As of v6.12 (Dec 2024) PREEMPT_RT is fully merged. Ch52A reads as if work is still in progress.
8. **`spidev` placeholder compatible `"rohm,dh2228fv"` will trigger kernel warnings.** Used unflagged in Ch98/99/101/105/106 since kernel 4.15+ actively warns. Either document a proper DT overlay path or call the warning out.
9. **CCGR encoding never explained.** Every Part II chapter writes `(3u << N)` to a CCM_CCGRx register without showing the 2-bit-per-gate table (00=off, 01=run-only, 10=reserved, 11=always-on). Single highest-payoff fix for Part II.
10. **Ch09 GPIO bit-number table contradicts the code.** Tables say "(bit 4 = our pin)" while the asm correctly uses `(1 << 3)` for `GPIO1_IO03`. Fix the table.
11. **Verify "Freescale i.MX6 UltraLiteLite 14x14 EVK Board" double-Lite (Ch19 §19.5).** If reproduced from a real boot log, add a footnote; otherwise fix.

### B. Reader-experience issues that recur across most parts

1. **The MCU→Linux bridge is the book's pitch, but it's applied inconsistently.** Ch02, Ch04, Ch15, Ch41, Ch51 do it well; Ch06, Ch07, most of Part V, most advanced driver chapters (Part VIb), and almost all of Part VII have *no* explicit "on STM32 you would X; in Linux you Y because Z" sidebar. Adopt a fixed sidebar style (a callout box) and require one per chapter.
2. **Acronyms appear without first-use expansion.** AAPCS, EABI, AIPS, ANATOP, IVT, DCD, SDP, HAB, SRK, CSF, TLB, VIPT, PIPT, ASID, MMDC, GIC, SCU, PL0/PL1, DAPM, ASoC, of_graph, CFI, DMA-BUF, etc. Each first occurrence needs `(...)` expansion. This is the **#1 ESL-comprehension issue** identified across every part.
3. **Sentence rhythm is too choppy for an ESL reader.** Many chapters use a string of 3–8 word sentences. Reviewers flagged specific examples in every part — combine where possible.
4. **Forward references are used as crutches.** Part I alone forward-references to Ch11, Ch14, Ch17, Ch28, etc. — dozens of IOUs. Reader needs either an "answer just enough for now" callout at each forward reference, or a mini-glossary at end of each Part.
5. **No memory-map figure for the SoC.** Hex addresses (`0x020C406C`, `0x0209C000`, `0x80000000`, etc.) are scattered without a single canonical 4 GiB map. One ASCII figure in Ch09 (or pulled forward from Ch17) reused across Parts II, III, IV would unlock comprehension.
6. **No address-oriented "where is what at each boot stage" diagram.** Part III especially needs one canonical stage chart (ROM → SPL → U-Boot pre-reloc → U-Boot post-reloc → kernel) showing addresses and what's in OCRAM vs DDR at each step. Reusable across Ch20/21/24.
7. **Stack-layering diagrams are missing across the driver and cookbook parts.** Required figures: DRM CRTC/encoder/connector/panel chain (Ch82–85), V4L2 sensor-subdev → CSI → media graph (Ch87), ASoC machine ↔ codec_dai ↔ cpu_dai (Ch89–90), wpa_supplicant ↔ nl80211 ↔ cfg80211 ↔ driver (Ch91–94), HCI ↔ kernel BT ↔ bluetoothd (Ch95–97), SocketCAN ↔ af_can ↔ flexcan (Ch110). Currently only prose.
8. **No "what good dmesg looks like" output for from-scratch drivers.** First thing the MCU reader will check on a successful insmod. Show the actual `dev_info` lines, IRQ allocation lines, IIO device registration line. Show the actual sysfs path tree after probe. Missing in almost every cookbook chapter.
9. **Sleeping-vs-atomic context recap is missing in Parts VI/VII.** Ch41 introduces it; later chapters use `mutex_lock`, `i2c_smbus_*`, `spi_sync` in IRQ-adjacent code without recapping the rule. One "context cheat sheet" sidebar in Ch41 plus a one-line cross-link from every later chapter.
10. **DT graph syntax (`port { endpoint { remote-endpoint }}`) is unintroduced** but appears in 4+ chapters (Ch53, Ch54, Ch54B, Ch55H). Needs one 10-line explainer at first appearance.
11. **`THIS_MODULE`, `container_of`, `dev_info` vs `pr_info`, `dev_err_probe`, IIO `INFO_RAW`/`scan_index`/`INDIO_DIRECT_MODE`, `phandle`, `&label`, `__weak`, `EXPORT_SYMBOL_GPL` — all used dozens of times but never properly introduced.** Pick a discipline: define-on-first-use, or add a per-part glossary appendix.
12. **DT pin-mux groups are never cross-checked against the IOMUXC table.** Cookbook chapters say `pinctrl-0 = <&pinctrl_sai2>` without telling the reader which physical pads carry the signal. The most common bring-up failure on iMX6ULL is picking the wrong pad. Add one pad-table per chapter, or a shared appendix.
13. **Part VII "from-scratch driver" depth is uneven.** Some chapters (Ch67/68/70/73/75/76/79/80) deliver real internals walks. Others (Ch65, Ch78, Ch100, Ch102–104) are thin wrappers or pure userspace recipes. Either commit to the cookbook-depth contract or explicitly tag those chapters as "integration recipes."
14. **Per-chapter "you will need this tooling" preamble missing.** `picocom -L`, `cpio -H newc`, `dtc -@`, `dtschema`, `bitbake`, `Mender CLI`, `uuu`, `imx_usb_loader` are referenced without prior install. One-line "tooling" preamble per chapter would prevent reader-dead-ends.
15. **The "pa-mini" prompt is used everywhere without being introduced.** Need one line at the start of Part VII saying that's the reference iMX6ULL hostname.

### C. Where to start

If you have a weekend, do these in order:
1. Fix the L2-cache claim across Ch04/Ch05.
2. Pick a target kernel version and put it in `index.md` and every Part-VI/VII chapter that ships a driver snippet. Update `class_create`/`i2c_probe`/`remove` accordingly.
3. Add the CCGR-encoding sidebar (Part II) and the SoC memory-map ASCII figure (Part II → used through book).
4. Update DTS paths to either v6.1 (no rename needed) or v6.5+ (`nxp/imx/...`) consistently.
5. Adopt one MCU-bridge callout style and add one to every chapter that's missing one (mostly Part V, Part VIb, all of Part VII).

Everything else is per-chapter detail in the sections below.

---
# Part I — Foundations: Review

## Cross-cutting observations

- **Forward references to "Chapter X" used as load-bearing crutches.** Most chapters defer hard explanations to a future chapter (e.g., Ch02 "Chapter 17 builds a page table"; Ch04 "Chapter 17"; Ch05 "Chapter 14"; Ch07 "Chapter 11"). That is fine in moderation, but the reader of Part I gets dozens of IOUs. Consider adding a single mini-glossary at the end of Part I (or callouts that briefly answer "what would I need to know *for now*?") so readers do not feel they must trust the author for 100 pages without payoff.
- **L2-cache claim is technically wrong for iMX6ULL.** Ch04 §4.6 and Ch05 §5.3/§5.4 both state "no L2 on i.MX6ULL." The IMX6ULLRM (rev 1, 11/2017) explicitly lists "Level 2 cache — unified instruction and data (128 KB)" in the Cortex-A7 MPCore platform description (Ch11/Ch12 of the RM; quoted at RM lines 9738, 9766, 10014, 22167, 22212). The Cortex-A7 MPCore platform in iMX6ULL **does** include a 128 KB unified L2. It is not a separate PL310 (which the i.MX6Q has), but it is present. Either correct the claim or add a careful nuance: "no external PL310 controller, but the MPCore platform contains an integrated 128 KB L2." This affects 3 chapters and should be fixed early since the rest of the book references it.
- **MCU-equivalence bridging is uneven.** Ch02 and Ch04 do this well (RTOS task vs Linux process; Cortex-M NVIC vs A-profile GIC). Ch06 (toolchain) and Ch07 (boot ROM) drop the comparison style entirely. Add at least one "compare to your MCU experience" callout per chapter — e.g., in Ch06 "binutils" section, note that the Keil/IAR toolchain bundles `ld`/`objcopy` invisibly; in Ch07, note that an MCU vector table at 0x0 is roughly what the IVT is, only it is data the ROM reads rather than vectors the CPU jumps to.
- **Acronym density without first-use expansion.** AAPCS, EABI, AIPS, ANATOP, PFD, IPS, IVT, DCD, SDP, HAB, SRK, CSF, PIE, TLB, VIPT, PIPT, ASID, MMDC, GIC, SCU, PL0/PL1/PL2 — many appear capitalized inline without "(...)" expansion the very first time. Each needs a (one-time) parenthetical on first occurrence. This is the #1 thing that hurts comprehension for an ESL reader.
- **Long fragmented sentences with semicolons/em-dashes can be hard for an ESL reader.** Ch02 and Ch04 in particular chain three or four clauses with em-dashes. Break some of them. (Author's general voice is good — terse, opinionated; the fixes are surgical, not a rewrite.)
- **No single "what we just learned" recap at the end of Part I.** Part II opens directly with Ch09 assembly. An end-of-Part-I summary table — "what each chapter contributed and the artifacts you should have on disk" — would lock the foundations down before the reader plunges into bare-metal.

## Ch01 — Preface

### Readability
- "You can read a schematic, solder a wire, and you know what a power rail is." — comma-spliced. Suggest: "You can read a schematic and solder a wire. You know what a power rail is."
- "If you have *no* embedded background at all — if 'register' means 'bank teller window' — the bare-metal chapters in Part II will feel cruel." — the joke is good, but "cruel" is jarring for a non-native reader. Suggest "will be very hard" or "will be discouraging."
- Section 1.5 list item 1: "*Object first.*" — too compressed. Suggest: "We always start from the *concrete object* — the artifact this chapter builds."

### MCU-engineer friendliness
- Section 1.9 pruning table assumes the reader already knows what an MCU vs SoC means and which path they fit. The table is useful — but consider adding a 1-sentence "if you are unsure which row applies to you, pick the first row (full experience)."

### Missing examples / figures
- After §1.5 "How each chapter is organized," include a tiny worked example: pick any one chapter and label which paragraphs are What/Why/How/Focus etc. Even three sentences. The seven-section template is the spine of the whole book; a worked sample saves a lot of "wait, which one is this?" later.

### Other
- The pruning table in §1.9 says "1–3, 4–8, 19+" — the reader does not yet know what chapters 19+ contain. Either move the table behind a forward-pointing "skip to the TOC" note or keep the same advice but expand into 2–3 lines of prose ("If you already wrote MCU firmware and only want Linux: read Part I, skim Part II, then start at Part IV").
- §1.13 "Errata and corrections" mentions a GitHub repo. §1.7 says "there is no companion repository." These two contradict; reconcile (the GitHub repo for errata is fine, but say so explicitly: "the book has no source repo, but errata live at <url>").

## Ch02 — What "Embedded Linux" actually is

### Readability
- "From here on, your code owns the machine." in Ch07 §7.2 — good, but Ch02's equivalent is missing. Add a similar one-liner at the end of §2.2 to lock the four-layer diagram in.
- §2.3 "How then does a user-mode program ever ask for I/O?" — slightly old-fashioned; "How, then, does..." or just "So how does a user-mode program ask for I/O?"
- §2.4 "On i.MX6ULL with the MMU on, *no two processes see the same address as the same thing*." — clear, but the italics drift over a long sentence. Suggest splitting: "On i.MX6ULL with the MMU enabled, no two processes see the same address as the same thing. Each process has its own virtual address space."

### MCU-engineer friendliness
- §2.3 introduces "system call" via `svc #0` and r7/r0–r6 register conventions. The reader has not yet had Ch04's primer on AAPCS or the SVC exception. Either (a) defer the ARM register-level detail to "we'll see in Ch04," or (b) add one sentence: "If this looks like a software interrupt, that is exactly what it is — the M-profile equivalent is `svc`/`SVCall`, which you may have used to enter the kernel of an RTOS that has one."
- §2.4 "Virtual memory, in one section" is the densest section. An MCU engineer who has never used an MMU will struggle. Add a single explicit "compare to Cortex-M" paragraph at the start: "On Cortex-M, a pointer holds a hardware address. The MPU (if present) just enforces read/write permissions on top of those addresses. On Cortex-A, the pointer holds a *virtual* address; every memory access goes through the MMU, which substitutes a different physical address per process." Until this is said plainly, the diagram in §2.4 is not informative.
- §2.5 "Linux implements threads as 'tasks' — internally, the kernel does not strongly distinguish processes and threads; both are `struct task_struct`." — this is too compressed for the first encounter. The reader does not yet know what `task_struct` is. Add: "Inside the kernel source there is one C struct, `task_struct`, used for both."

### Missing examples / figures
- After §2.3 "Why the split exists", add an ASCII figure of the syscall transition showing **register state** before, during, and after — something like:
  ```
  before svc:  CPSR.M = 10000 (USR)   PC = 0x0001AAAA (user libc)   SP = SP_usr
  on svc:      CPSR.M = 10011 (SVC)   PC = vector + 0x08            SP = SP_svc
  in handler:  CPSR.M = 10011        kernel runs, can access any phys addr
  return:      restore SPSR_svc → CPSR, LR_svc → PC, back to USR
  ```
  Right now §2.3 says this in prose. A picture would lock it in and would also forward-reference §4.3 cleanly.
- §2.4 paragraph "A *physical* address — say, the IOMUXC register block at `0x020E0000` — is not, by default, mapped into any user process's address space." would benefit hugely from an ASCII picture of process address space showing IOMUXC NOT mapped, vs kernel address space WITH IOMUXC mapped.
- §2.7 size table is great but does not show a memory map of what those bytes occupy in 256 MiB DRAM. Add a small ASCII memory map of a typical embedded Linux DRAM layout (kernel, modules, user heap, free) to anchor the numbers.

### Technical errors
- §2.3 says: "the `svc` instruction (formerly `swi`) raises an SVC exception; the CPU switches to SVC mode, jumps to the exception handler, and the kernel decides what to do based on the syscall number in `r7` and arguments in `r0`–`r6`." — that is correct for EABI Linux on ARMv7. Worth noting (parenthetically) that the convention differs from OABI; you can drop this in a Pitfall in Ch04 if you prefer.
- §2.7 "Decompressed kernel in RAM | 12–20 MB" — for a mainline 32-bit ARM kernel on iMX6ULL with a modest config, 12-20 MB is on the high side; a stripped-down embedded config is more like 4-8 MB. The number is defensible if you mean defconfig with modules-built-in. Either tighten or qualify ("defconfig with most drivers built-in").

### Knowledge prerequisites missing
- §2.6 mentions "`/sys/class/gpio` is a real filesystem" without explaining sysfs. Comes up again in Ch31/45. For Part I, either replace with a less specific example or add one sentence: "`sysfs` is a kernel-generated tree that exposes driver state as files; we build one in Ch 40."
- §2.6 paragraph on "syscall, libc, glibc, musl" introduces glibc and musl side-by-side. Good. But then "When you call `printf()`..." path lists eight layers including "tty driver's write callback" — `tty` and "driver callback" are undefined here. Sketch one sentence about what a "tty" is, even if you say "a Linux abstraction over a terminal/UART that we will dissect in Ch 28."

### Other
- §2.10 lab Q3 ("list every syscall that probably happens when you `cat /etc/hostname`") — fun question, but the reader at this point has never seen a syscall trace. Either give a `strace cat /etc/hostname` example upfront, or note "we will revisit this when we have `strace` running on the target."
- §2.11 "Pitfalls" is concatenated with §2.10 in the source (line 267: `Compare your answers against the chapter text and the references below.## 2.11  Pitfalls`). Missing newline before the `## 2.11` heading. Easy fix.

## Ch03 — Host environment setup

### Readability
- §3.1 "If you are running Windows or macOS, the fastest path is to put Ubuntu on a USB-3 NVMe enclosure and boot from it." — strong opinion. Fine to keep, but soften slightly for ESL readers: "If you are on Windows or macOS, the fastest option is to install Ubuntu on a USB-3 NVMe drive and boot from it directly." (Avoid "USB-3 NVMe enclosure" without defining; some readers will not know what an NVMe enclosure is.)
- §3.4 "The cleanest choice for getting started." — sentence fragment. Suggest "This is the cleanest choice for getting started." Same with "Pros: newer GCC..." — keep as bullets or convert to full sentences for consistency with the rest of the chapter's prose voice.

### MCU-engineer friendliness
- §3.4 "Decoding the triplet" is excellent. But add an MCU-bridge: "In the Keil/IAR/STM32CubeIDE world, your toolchain prefix was rarely visible — the IDE picked one. On a Linux host, you call the compiler by its full prefixed name (`arm-linux-gnueabihf-gcc`), and *which* one you pick decides everything: ABI, libc, OS target."
- §3.7 NFS server: the reader has never used NFS. They have probably used SD-card swapping or SWD to put files on an MCU. Add one paragraph: "NFS lets the *target board* mount your host's `~/imx6ull/rootfs/` directory as if it were a local disk. After NFS is up, copying a file into `~/imx6ull/rootfs/` on the host is immediately visible to the running board. This replaces the SD-card-swap loop you may have used on Cortex-M projects."

### Missing examples / figures
- §3.10 "Host IP plan" — would benefit from a simple ASCII network diagram showing host (192.168.7.1) -- crossover Ethernet -- board (192.168.7.2), with TFTP and NFS arrows pointing at the host. Three lines of ASCII; saves the reader visualizing it.
- §3.11 sanity-check block is the only end-of-chapter sanity check in Part I. Beautiful. Consider repeating this pattern in Ch07/Ch08.

### Knowledge prerequisites missing
- §3.4 first sentence uses "x86_64-linux-gnu (the host) and arm-linux-gnueabihf (the target)" — this is the first time the triplet is named. The reader has not yet read §3.4.3 "Decoding the triplet." Either reorder so decoding precedes use, or insert "(this is the GNU 'triplet' format we decode below)" on the first mention.
- §3.8 `udev rule` — the term `udev` has not been introduced. One sentence: "`udev` is the Linux service that creates device nodes (like `/dev/ttyUSB0`) when hardware appears. We write a rule so the i.MX6ULL ROM USB device is owned by your user, not root."
- §3.12 lab references `direnv` without much context. Fine to keep as a recommendation but state explicitly: "`direnv` is a tool that runs `.envrc` scripts when you `cd` into a directory; it isolates env-var pollution."

### Other
- §3.3 — `pkg-config libusb-1.0-0-dev libftdi1-dev` is listed in the `apt install` block AND mentioned again in §3.8 as needed for `uuu`. The latter then says `sudo apt install -y libusb-1.0-0-dev libzip-dev libbz2-dev pkg-config cmake`. Reconcile: either install everything in §3.3 or note in §3.8 "(some of these you already installed in §3.3; the new ones are libzip-dev, libbz2-dev, cmake)".
- §3.7 the `echo "/home/$SUDO_USER/imx6ull/rootfs ..."` heredoc has a subtle bug: when run inside `sudo bash -c`, `$SUDO_USER` is correct *for that subshell* — but the reader may copy the command into a script and lose the variable. Add a one-line note: "if you copy this into a script run as root from cron/systemd, replace `$SUDO_USER` with your actual username."

## Ch04 — ARMv7-A and the Cortex-A7, for the MCU engineer

### Readability
- §4.2 "Stand a Cortex-M7 datasheet next to a Cortex-A7 TRM and the list of 'things only A has' runs to:" — colon-introducing-table is fine, but "things only A has" is informal in a way that contrasts with surrounding prose. Suggest: "Compared to Cortex-M7, Cortex-A7 adds the following architectural features:"
- §4.3 "This is the most jarring difference for an engineer coming from Cortex-M, so we cover it carefully." — drop "jarring"; suggest "biggest change."
- §4.5 "It is in-order, dual-issue, with a short pipeline (8 stages). Its strength is power efficiency, silicon area, and *price*." (back in §4.1) — comma-spliced. Suggest two sentences. (Same pattern appears multiple times in §4.1.)
- §4.10 "For user space, NEON is just there — `libc`'s `memcpy`, `memset`, `strcmp` use it." — "is just there" reads oddly. Suggest: "For user space, NEON is always available; glibc's `memcpy`, `memset`, and `strcmp` already use it."

### MCU-engineer friendliness
- §4.3 "PL0 vs PL1 vs PL2" — table is correct but again very dense. Add: "On Cortex-M, you have **two** privilege levels (Privileged + Unprivileged) and you usually run everything Privileged. On Cortex-A, you have **three**, and you spend ~95% of the time at PL0 (your application) or PL1 (the kernel)."
- §4.3 the assembly example `srsdb sp!, #0x12` / `cpsid if, #0x13` will read like Greek to a Cortex-M engineer. Add a 2-line decoding under the code block: "`srsdb` = Save Return State, Decrement Before — push LR + SPSR. `cpsid if, #0x13` = Change Processor State: Interrupt Disable {IRQ,FIQ}, mode = 0x13 (SVC). The two instructions together move from IRQ context into SVC context with a clean stack."
- §4.5 MMU section explains short-descriptor format mechanically but never explicitly says "by analogy, this is the equivalent of the Cortex-M MPU's region tables, except the table lives in DRAM and the MMU walks it instead of the core checking 8 regions." Add this analogy upfront.
- §4.6 caches — "Caches are off at reset. Just like Cortex-M, but unlike Cortex-M, you cannot easily run usefully fast without them." The "but unlike Cortex-M" framing is correct (caches are mandatory for usable A-class performance) but the sentence is hard to parse. Suggest: "Caches start disabled at reset on both M and A profiles. The difference: on Cortex-M you can run usable code with caches off; on Cortex-A7 at 696 MHz fetching from DDR with no cache, you lose more than 90% of usable throughput. Enabling caches is therefore one of the first jobs of any A-profile bootloader."
- §4.8 GIC — the table of SGI/PPI/SPI ID ranges and the note "UART1 is SPI 26 (which the GIC sees as ID 26+32 = 58)" is excellent. Add an MCU-bridge sentence first: "On Cortex-M, the NVIC is inside the core and the interrupt-vector number is the IRQn used in your driver code. On Cortex-A, the GIC is a separate memory-mapped peripheral, and the interrupt ID space is split into three ranges:"

### Missing examples / figures
- §4.3 — after the nine-modes table, add an ASCII picture of "what happens when an IRQ fires" showing the register-bank swap. The prose explanation is correct but a banked-register diagram (USR view side-by-side with IRQ view, with arrows on R13/R14) makes it click in 5 seconds.
- §4.5 short-descriptor walk diagram is good. Add a *worked example* underneath: "VA `0xC0001234` with the kernel TTBR1 → L1 index = `0xC00` (3072) → entry at TTBR1+0xC00*4 → if section: PA = section_base | 0x1234." One concrete example replaces a paragraph of theory.
- §4.7 generic timer — show a tiny code snippet for reading `CNTPCT`: `mrrc p15, 0, r0, r1, c14` (or use a `volatile asm` wrapper). Reader has never accessed CP15; one snippet would demystify "CP15 access" for the next 50 pages.

### Technical errors
- §4.1 "running at up to **528 MHz** (commercial) or **696 MHz** (industrial)." — The IMX6ULLRM (line 9758) states: "The target frequency of the core is 528 MHz non-overdrive and overdrive to 800 MHz for industrial processor and 900 MHz for consumer processor." And the commercial datasheet (line 132) lists `MCIMX6Y2DVM09AB` at 900 MHz commercial. So the maxes are 800 MHz industrial / 900 MHz consumer, not 528 / 696. The 696 MHz number is the operating frequency the Point Atom BSPs configure, not the silicon ceiling. Suggest rewriting as: "The architectural maximum is 800 MHz (industrial) or 900 MHz (consumer/commercial). Most BSPs — including the Point Atom factory image — clock the part at 528 MHz or 696 MHz to stay in a safer voltage/power envelope. We will run at the BSP-default 696 MHz."
- §4.6 "There is no L2 on this part (no PL310 controller is integrated)." — Disputed; see Cross-cutting observation. The Cortex-A7 MPCore platform on iMX6ULL has an integrated 128 KB L2 (RM lines 9738, 9766, 22167, 22212). What is *absent* is a PL310 (CoreLink Level-2 Cache Controller, used on Cortex-A9 designs like iMX6Q). Suggest: "Cortex-A7 in iMX6ULL has 32 KB L1-I + 32 KB L1-D + 128 KB unified L2 (integrated in the MPCore complex; there is no separate PL310 controller as you would find on Cortex-A9/iMX6Q)."
- §4.6 "Caches are VIPT for L1-D (Virtually Indexed, Physically Tagged) on Cortex-A7." — Per ARM's Cortex-A7 TRM, L1-D is actually **PIPT** on Cortex-A7 (the line in Ch04 §4.11 table — "L1 D-cache | 32 KB VIPT" — also disagrees with TRM). Cortex-A7 chose PIPT to avoid the aliasing issues VIPT has. The chapter's aliasing discussion is therefore not applicable. Worth verifying against ARM DDI 0464 and correcting.
- §4.5 "Uses TTBR0 for user-space (per-process) and TTBR1 for kernel-space" — correct; small nit: ARMv7 splits the VA space using TTBCR.N, not by fiat. Worth a parenthetical: "(the split point is configured in TTBCR.N; default Linux uses N=2 → 0xC0000000)."

### Knowledge prerequisites missing
- §4.3 uses `cps`, `srsdb`, `rfeia`, `mrs`, `cpsid` — none have been introduced. Reader from Cortex-M knows `MRS`/`MSR` (slightly different mnemonics on M-profile, e.g., `MRS R0, PRIMASK`). Sketch the new mnemonics in a footnote or sidebar.
- §4.4 mentions IT[7:0] split across bits 26:25 and 15:10 — fine, but "IF-THEN block" is not common to Cortex-M readers (it was added in Thumb-2 which M-profile also has). Note: "If you wrote Thumb-2 on M4, you have implicitly used IT blocks every time you wrote a conditional instruction outside of branches."
- §4.5 uses "Inner shareable", "Outer shareable" implicitly via the cache-maintenance discussion. Either explain or defer to a glossary.

### Other
- §4.2 table has an error: "Atomic ops | LDREX/STREX | LDREX/STREX (same family)" — they are the same instructions, but reorder so the M-side column also says "LDREX/STREX (M7 onwards)" to clarify; M0/M0+ have no exclusives.
- §4.13 Pitfalls "Cache flush by set/way for 'flush everything'" — good warning, but "not broadcast" needs explaining or replacing. For a single-core part this is less critical; consider rewording: "On multi-core A-profile parts, set/way operations only act on the issuing core's local cache and miss aliased lines; even on single-core iMX6ULL it is safer to default to VA-based cache ops."

## Ch05 — A tour of the i.MX6ULL SoC

### Readability
- §5.1 "NXP positions the i.MX6ULL ('Ultra-Low-Layer') at the bottom..." — "Ultra-Low-Layer" is informal NXP marketing; the official term is "Ultra-Lite Low-end" depending on source. If keeping, a footnote: "NXP's marketing uses 'Ultra-Lite' as well; the family-name conventions are looser than they should be."
- §5.5 "PLL2 and PLL3 expose **PFDs** (Phase Fractional Dividers)" — PFD is actually **Phase Fractional Divider** in NXP parlance, but most NXP docs call it **Phase-Fractional-Divider** or just "PFD" without expansion. Verify the exact NXP term; the RM may spell it "Phase Fractional Divider" or "PLL Fractional Divider." (Either way, expand on first use.)

### MCU-engineer friendliness
- §5.5 "Layer 4 — Gates (CCGR0..CCGR6)" — excellent. Add an MCU-bridge sentence: "On STM32, you write `RCC->AHB1ENR |= RCC_AHB1ENR_GPIOAEN` to enable a peripheral clock. The iMX6ULL equivalent is `CCM->CCGRx |= (peripheral_bits)` — same idea, more registers, finer-grained mode control."
- §5.6 IOMUX — first time the reader meets pin muxing on a SoC scale. Cortex-M parts have 16-way muxers too (AF0–AF15 on STM32). Add: "If you have used STM32 AFx selection, you have used a 16-way pin mux. The iMX6ULL IOMUXC is the same concept but bigger (8-way per pin × 380 pins) and has an extra 'daisy' step that we explain below."

### Missing examples / figures
- After §5.3 (memory map table), add an ASCII figure of the 4 GB address space showing what is mapped and what is unused — most of the gaps from 0x021FFFFF to 0x08000000, from 0x10000000 to 0x60000000, etc. Visualizing "almost all of the 4 GB is unused" cements the geography.
- §5.5 "Layer 2 — PLLs" — the table is good. Add a small ASCII clock-tree diagram showing PLL1 → ARM, PLL2 → SYS bus, PLL3 → USB/UART for the most-used paths. The "shape" you mention in the opening sentence is invisible without a picture.
- §5.6 IOMUX — the 8-way ALT list for one pin is good. Add an ASCII picture of the pin signal flow: PAD ↔ PAD_CTL ↔ MUX_CTL ↔ ALT-input-mux ↔ peripheral-input-mux (the daisy chain). Three boxes connected by arrows would be enough.

### Technical errors
- §5.1 "**L2 cache:** none (only L1)" — see Cross-cutting observation. The MPCore platform has an integrated 128 KB L2. Suggest rewording to "128 KB L2 (integrated in MPCore; no external PL310)."
- §5.1 "**TCM:** 128 KB tightly coupled (split as 32 KB ROM + 96 KB OCRAM accessible from outside — see §5.4)" — this is **incorrect terminology and incorrect numbers**. There is no TCM on Cortex-A7. What iMX6ULL has is **128 KB OCRAM** and a **96 KB Boot ROM** (RM line 9770/9773 explicitly: "Boot ROM, including High-Assurance Boot (HAB, 96 KB)" and "Internal fast access RAM (OCRAM, 128 KB)"). These are separate blocks, not a single 128 KB TCM. Fix the bullet entirely: "**On-chip memory:** 128 KB OCRAM at `0x00900000`; separate 96 KB Boot ROM at `0x00000000` (mask-programmed by NXP). No TCM — TCM is a Cortex-M and Cortex-R concept; A-profile cores rely on L1/L2 caches."
- §5.3 memory map table — "Boot ROM | `0x00000000` | 96 KB" + "OCRAM | `0x00900000` | 128 KB" is correct (per RM line 10224-10225). But "Caches debug | `0x00018000` | 16 KB | (alias of ROM in normal modes)" is suspicious — verify against RM Ch 2 memory map.
- §5.4 "Of the 128 KB OCRAM, the Boot ROM uses a portion for its own data while executing. By the time control reaches your code: **OCRAM `0x00907000`–`0x0091FFFF`** (~100 KB) is free for your use." — This is **backwards** compared to RM. RM (line 16077) says: "The entire OCRAM region can be used freely after the boot." During boot, RM (line 18685) Table 8-31 says: "OCRAM free space 0x00907000 0x00917FF0" — that is only `0x917FF0 - 0x907000 ≈ 68 KB` (not ~100 KB), and is the area available for DCD writes / the program image before the ROM hands off. After handoff, the *entire* OCRAM 0x00900000–0x0091FFFF (128 KB) is yours. The ROM only used the upper portion (`0x00918000`–`0x0091FFFF`, ~32 KB) for its MMU table/stack/vectors during execution (RM line 16054-16069). Fix the numbers and the direction (top of OCRAM was ROM's; bottom 0x00900000-0x00906FFF is reserved before the ROM completes).
- §5.4 "**OCRAM `0x00900000`–`0x00906FFF`** holds the ROM's working area" — RM doesn't support this; the ROM's working area is at `0x00918000`–`0x0091FFFF` (high end of OCRAM). The low region `0x00900000`–`0x000001FF` is the *exception vector* area and `0x00000200`–`0x00907000` is OCRAM Free Area (~68 KB) per RM Figure 8-3 (line 16040). This whole §5.4 needs reconciliation with RM Figure 8-3.

### Knowledge prerequisites missing
- §5.2 mentions "AXI" and "AHB" and "IPS" without expansion. AXI = AMBA eXtensible Interface; AHB = Advanced High-performance Bus; IPS = IP Slave (or "IP Bus" depending on NXP doc). MCU readers from STM32 land have seen AHB but not AXI. Add a single sentence in §5.2: "AXI and AHB are ARM bus protocols (high-speed and lower-speed respectively); IPS is NXP's name for the peripheral-side bridge to the slower peripheral bus."
- §5.6 "SION ('Software Input On')" is introduced then never explained why you'd want it. One sentence: "SION forces the input buffer enabled even when the pad is configured as an output. You need it for open-drain I²C readback and for some loopback debugging."
- §5.8 OCOTP — "HAB SRK hashes" and "NX bits" appear without expansion. SRK = Super Root Key (introduced briefly in Ch07 §7.8). NX = No-Execute. Either define or forward-reference Ch62.

### Other
- §5.9 peripherals table — the chapter numbers in the "Notes" column refer to *this book's* chapters, but the column header is "Notes" and the entries look like "Ch 5, 13" without saying so. Add the prefix "Book ch ..." to one row or change the column header to "Book chapters." Otherwise the reader confuses RM chapters and book chapters.
- §5.10 "Print the table of contents (the first 30 pages of the PDF)..." — good advice. Consider including a 1-page "Reference Manual cheat-sheet" appendix with the 10 most-used RM chapters mapped to the topics they cover; this is the single most-asked-for resource by every reader of the RM.

## Ch06 — The toolchain

### Readability
- §6.1 "When you type:" + "...six programs run in sequence." then numbered list with steps 1–6 where step 4 (collect2) and step 6 (dynamic loader) are partly redundant. Suggest: "Five stages run for a typical compile-and-link (`cpp` → `cc1` → `as` → `ld`), plus a dynamic-link step that happens later, at runtime, on the target." Then list only the five plus the runtime note.
- §6.7.1 "Commands must be indented with a literal TAB — spaces do not work; the first time you cut-and-paste a rule, this bites everyone." — long sentence with two punctuation marks; suggest: "Recipe lines must be indented with a literal TAB; spaces do not work. The first time you cut-and-paste a rule from a web page, this bites everyone."
- §6.7.2 "The pair people misunderstand most is `=` vs `:=`:" — minor: "The most common confusion is between `=` and `:=`."
- §6.9 "When `gdb` says 'no debug info, no symbols', it means the binary was stripped (`strip` removed the symbol and DWARF sections)." — good. Add the inverse: "To prevent this, keep an unstripped copy as `name.elf` and a stripped copy as `name.stripped.elf`." (Already mentioned in Pitfalls but worth restating here.)

### MCU-engineer friendliness
- §6.1 the six sub-stages list is correct, but reader from Keil/IAR/STM32CubeIDE has *never seen these as separate*. Add bridge: "If your workflow has been Keil µVision or STM32CubeIDE, you have never seen `cpp`/`cc1`/`as`/`ld` as separate steps; the IDE invokes them invisibly. On the command line, we can interrupt at any step (`-E`, `-S`, `-c`) and inspect the intermediate file. This is enormously useful when debugging build issues."
- §6.4 linker scripts — Cortex-M engineers using STM32CubeIDE will have edited the generated `STM32F4xx_FLASH.ld`. Mention: "If you've ever opened the auto-generated `.ld` file in STM32CubeIDE, this is the same syntax. We are just writing one for the iMX6ULL's OCRAM region by hand."
- §6.5 ABI section is good. Add a contrast row at the top: "On Cortex-M, the AAPCS rules are identical except for FP-register usage (Cortex-M has no NEON; FP-call conventions differ between M0/M0+ no-FPU, M4F single-precision FPU, M7 double-precision FPU)." That anchors r0-r3-as-args for the reader who already half-remembers this.
- §6.6 — the comparison to MCU is missing. Add: "On Cortex-M, the 'libc' from Keil/IAR was a small newlib or proprietary library, often without `malloc`. On Linux user space, glibc/musl is much larger because it implements full POSIX. For our bare-metal Part II we will use *no* libc at all, which is closer to your MCU experience."

### Missing examples / figures
- §6.3 VMA vs LMA paragraph would benefit from an ASCII diagram showing Flash and RAM side-by-side, with `.data` arrows showing LMA in Flash and VMA in RAM, and the startup-code copy arrow between them.
- §6.7.8 "A complete Makefile for the Chapter 9 LED" — excellent. Consider adding a parallel "what each line produces": after `led.elf: $(OBJS) link.ld`, show what the linker invocation actually expands to (`arm-none-eabi-ld -T link.ld -o led.elf startup.o main.o`). The reader benefits from seeing the substitution in action.

### Technical errors
- §6.2 — `objdump -d` example shows code at `00900000`. That is OCRAM base on iMX6ULL but Ch05 §5.4 said the available region starts at `0x00907000` (which is itself wrong; see Ch05 review). Bring these two examples into agreement.
- §6.5 "AAPCS-VFP" — actually called "AAPCS-VFP" or "Hard-Float ABI"; the official ARM document name is "Procedure Call Standard for the Arm Architecture (AAPCS32)" with hardfp ABI variant. Citing it as "AAPCS-VFP" is fine but inconsistent with §6.12's "AAPCS32 — ARM IHI 0042" — pick one name and use it everywhere.
- §6.5 table "r9 is 'platform register' — see §6.6" — but §6.6 doesn't actually explain r9. Either add an r9 paragraph in §6.6 or remove the forward reference.

### Knowledge prerequisites missing
- §6.1 mentions `binutils` without expansion. Define on first use: "binutils — the GNU 'binary utilities' package containing the linker, assembler, and other tools."
- §6.7.5 `$(shell ...)` — make this scary moment kinder: "Note that `$(shell ...)` runs at parse time, not when the recipe runs. Avoid using it for anything expensive."
- §6.9 ELF — define ELF on first use ("Executable and Linkable Format"). Currently introduced in §6.1 as `.s into a relocatable .o (ELF object file)` without expansion.

### Other
- §6.10 Lab B asks: "How big is `.bss`?" — but the skeleton `main.c` has no global variables, so `.bss` will be near-zero. Either pre-populate `main.c` with a `static int buf[1024];` so the reader sees a measurable `.bss`, or rephrase the question to "how big is `.bss` and why so small?"
- §6.11 Pitfall "`-nostdlib` silently dropping libgcc" is great — but the reader has not yet hit the `__aeabi_uldivmod` case. Consider expanding into a worked example: a 64-bit division failing to link, then adding `-lgcc` and succeeding.

## Ch07 — The Boot ROM, IVT, DCD, and BootData

### Readability
- §7.1 "Three useful facts about the Boot ROM:" — list item 2 "It is the same across all i.MX6ULL chips of a given silicon revision." — fine. Item 3 "It is recoverable" needs rewriting for natural English: "Even a board with garbage in every flash chip can recover: the ROM can drop into **USB Serial Download Protocol (SDP)** and accept a new image over USB-OTG."
- §7.5 "This is the cleverest, least-documented, and most useful part of i.MX boot." — fine; this is opinion and that's OK in the book's voice.
- §7.9 "Wait — those don't make sense together. Actually they do: this is a U-Boot image meant to be loaded to `0x80700000` (DRAM), and the byte order is little-endian. With a little practice you read these in your head." — this is conversational and good for an ESL reader. Keep.

### MCU-engineer friendliness
- §7.1 first paragraph — add: "On your MCU, the 'boot ROM' was either nonexistent (you jumped to `0x0` which is your code's vector table) or a small DfuSe-like loader on STM32. On iMX6ULL, the ROM is a much larger and more capable program — it must find a boot image, optionally configure DDR, and verify signatures before your code runs."
- §7.5 DCD — the analogy is missing. Add: "If you have used STM32 OPTION_BYTES or DCMI_BOOT registers, you have used a small list of register pre-configurations the chip applies before your code runs. DCD is the same idea, but it lives in your boot image as a *list of writes the ROM performs on your behalf* — typically to bring up DDR."
- §7.7 .imx layout — would be much clearer if the ASCII diagram annotated which fields are decided by *your script* (IVT.self, BootData.start, IVT.entry) vs which are fixed by the ROM (offset 0x400 for SD/MMC).

### Missing examples / figures
- After §7.1 "Three useful facts" — add an ASCII memory layout of the ROM/OCRAM region: where the 96 KB ROM lives, where its alias at `0x00100000` is, where OCRAM sits, and where the ROM places your image. The reader needs this picture to even understand §7.2 step 5 ("read the IVT at the fixed offset").
- §7.2 — the 10-step boot sequence would benefit from a single all-in-one ASCII flowchart. The bulleted list is okay but a picture makes it click. Suggest:
  ```
  POR_B rising
       ↓
  Sample BT_FUSE_SEL fuse
   ┌───┴───┐
   │       │
  fuse    pins (BOOT_MODE[1:0])
   ↓       ↓
   ↓    Internal-boot? → probe device → read IVT@offset → walk DCD → load image → jump
   ↓    SDP?           → wait for USB host
   ↓    Reserved       → halt
  ```
- §7.3 worked IVT example — superb. But place an ASCII byte-dump alongside the table so the reader sees the layout as both struct fields and raw bytes:
  ```
  Offset  Bytes                                    Field
  +0x00   D1 00 20 40                              header (tag, len_be, ver)
  +0x04   00 84 90 00                              entry = 0x00908400 (little-endian)
  +0x08   00 00 00 00                              reserved1
  ...
  ```
- §7.7 ".imx image format" ASCII figure is good but the offsets shown jump from `0x0500ish` to `0x1000`. Be explicit: "Padding from end of BootData to offset 0x1000 — anywhere from a few bytes to ~3 KB depending on layout."

### Technical errors
- §7.2 step 5 "NAND: IVT at offset 0 of the first valid block." — RM Table 8-25 (line 18465-18470) lists IVT offsets only for **NOR (0x1000)**, **OneNAND (0x100)**, and **SD/MMC/eSD/eMMC/SDXC (0x400)** and **SPI EEPROM (0x400)**. NAND (non-OneNAND) is handled via a different code path; the IVT lives in the **firmware configuration block (FCB)** structure, not at offset 0. Fix: either consult RM Ch 8.7.1.4 (NAND) and update the bullet, or remove the NAND row and add a footnote: "Raw NAND boot uses a different layout (FCB); we cover this only in the optional NAND chapter."
- §7.2 step 5 "Parallel NOR: IVT at offset 0." — RM says **NOR** is at **0x1000** (4 KB), not 0. Correct this.
- §7.2 step 5 "SPI-NOR / QSPI: IVT at offset 0x400." — RM Table 8-25 row "SPI EEPROM" is at 0x400, but **QSPI** uses a different offset (0x1000 per AN12056 for some configurations). Verify; the ULL QSPI offset may actually be 0x1000 not 0x400.
- §7.3 IVT header "`0xD1` (tag), `0x00 0x20` (length = 32, big-endian), `0x40` (version)" — version is `0x40` *or* `0x41` per RM line 18524: "Version: A single byte field set to 0x40 or 0x41." Add the `0x41` alternative; some U-Boot images emit `0x41`.
- §7.6 "VID `0x15A2`, PID `0x0080` for i.MX6ULL" — Confirm against RM Ch 8.9.3 (Serial Download Protocol). For iMX6UL/6ULL the PID is `0x0080`, but some i.MX parts use other PIDs (`0x0061`, etc.); make sure this is the correct one for ULL specifically. (Sectional Ch03 §3.8 udev rule uses the same `15a2:0080`, so internally consistent at least.)
- §7.5 "Opcode `0xCC` WRITE, `0xCF` CHECK, `0xC0` NOP" — RM uses tag 0xCC for write-data and 0xCF for check-data, agreeing with the chapter. But `0xC0` for NOP — verify; RM lists `0xC0` as the NOP command but also has `0xB2` (unlock) and others worth mentioning in a footnote.

### Knowledge prerequisites missing
- §7.1 mentions "Cortex-M MemManage fault" via Ch02; in Ch07 it says "POR_B rising" without defining POR_B. Define: "POR_B (Power-On Reset, active-Bar/active-low) — the SoC's reset pin held low until power is stable."
- §7.5 first sentence introduces "DCD" but the abbreviation has been used since the chapter title. Fold the title-page note into the first paragraph: "(Device Configuration Data)."
- §7.6 introduces "fuses" without defining (after §5.8 OCOTP did define them). Add a brief reminder: "fuses (also called eFuses or OCOTP) are one-time-programmable bits inside the chip; see §5.8."

### Other
- §7.4 BootData paragraph: "A common bug: you set `length` to 'just the code size' and the ROM stops loading before your `.data` is copied. Always include header bytes in `length`." — good. Reinforce in §7.11 Pitfalls.
- §7.9 the `xxd` hex dump has fictional values (the `00 00 78 80` example for entry → 0x80780000). Replace with values from an actually-existing U-Boot image — pull a current `u-boot-dtb.imx` from a Buildroot or Yocto output and use its real bytes. As written, the reader who tries to verify your math against their own image will be confused.
- The 32-byte IVT header decoding "`D1 00 20 40` → 0xD1 tag, length 0x0020 (32 bytes), version 0x40" is **exactly right** and a great example of decoding raw bytes. Keep this.

## Ch08 — Hardware bring-up checklist

### Readability
- §8.1 "Reject and return if so." — clipped; fine for a checklist but consider "If you see any of these, reject the board and return it."
- §8.6 "Once you've done this, no boot-flash mishap can scare you. You always have a path back." — strong and good. Keep.
- §8.3 "Plug the dongle into the host PC and check:" — followed by `dmesg | tail -5`. Add the expected line count: "You should see 3-4 new lines describing the USB enumeration."

### MCU-engineer friendliness
- §8.2 "Power rails — measure before applying" — this section is *perfect* for an MCU hardware engineer; they already know to do this. Add a 1-line note: "If you are coming from a software-only background, this section may feel paranoid. It is not. Do it anyway."
- §8.6 recovery drill — superb. Could also note: "On Cortex-M with SWD, you have always had a recovery path via the debugger. On iMX6ULL the equivalent is SDP over USB-OTG — but no JTAG/SWD setup required for recovery (JTAG is for code-level debugging, not for booting)."

### Missing examples / figures
- §8.3 — add a small ASCII pinout diagram of the 4-pin debug-UART header showing TX/RX/GND/VCC labels and the wiring crossover. The text describes it but a picture is faster.
- §8.4 — show what the boot-mode switch *looks like* in each position. Even a 4-line ASCII "ON/OFF | SDP | SD" sketch helps.
- §8.5 expected U-Boot banner — annotate which lines tell you the board is OK ("Model: Point Atom MINI" → DTB loaded; "DRAM: 512 MiB" → DDR controller is up; "=>" → fully ready for commands). Right now the banner is given but the reader does not know how to read it.

### Technical errors
- §8.3 "i.MX6ULL ROM and U-Boot speak 115200 8N1 by default." — Confirm: the **iMX6ULL ROM does not print over UART by default** unless serial-downloader debug is enabled. The 115200 number is U-Boot's default, not the ROM's. Rephrase: "U-Boot prints at 115200 8N1; the iMX6ULL Boot ROM itself is silent unless you enable serial downloader on UART1."
- §8.6 step 3: "With no SD card, power on. The ROM finds no boot device on USDHC. After a short timeout it falls back to SDP." — Verify this is the default behavior. The fallback to SDP requires specific BOOT_CFG fusing or a specific BOOT_MODE pin state. On a stock board, the fallback to SDP after a missing-device timeout *is* the typical behavior, but worth saying "this fallback is configured by the board's default pull-resistors on BOOT_MODE pins; some boards do not fall back and just hang."

### Knowledge prerequisites missing
- §8.4 references `15a2:0080` again but does not link to Ch03 §3.8 where the udev rule was set up. Add: "If `lsusb` shows the device but with a permission error, you skipped the udev step in §3.8 — go back and do it."
- §8.7 mentions OpenOCD without expansion. Define: "OpenOCD — open-source JTAG/SWD debug server; speaks to your debug probe on one side and gdb on the other."

### Other
- §8.6 sub-step "uuu -b spl u-boot-dtb.imx" — the `-b spl` argument is for boards that use a U-Boot SPL + main U-Boot. If you are using a single-image U-Boot, this is `-b sd` or similar. Specify which boot script applies to Point Atom MINI's U-Boot variant.
- §8.6 "Variation — pushing a bare-metal image" → `uuu -b sdp_recovery led.imx`. The script name "sdp_recovery" — verify this is the script name in current `uuu`; older `uuu` releases used `mfgtools` builtin script names. Cross-check.
- §8.9 end-of-chapter checklist is a beautiful close to Part I. Could benefit from one final line: "If every box is checked, you can return to this chapter in 6 months as a regression test when your setup mysteriously breaks." This reinforces the lab-discipline message from Ch01.
- §8.10 lab "Make a deliberate failure" is the best lab in Part I. Keep this pattern in Part II.

## End-of-Part summary suggestion

Consider adding a one-page recap at the end of Ch08 (or as a Ch08.X section) that lists, in two columns:
- "By now you can answer:" — the conceptual questions from Ch02 (user/kernel split, four layers, syscalls vs function calls, MMU vs MPU, VMA vs LMA, what the ROM does).
- "By now you have on disk / on the board:" — Ubuntu host with toolchains; TFTP and NFS running; serial console working; board boots stock SD; SDP recovery verified.

If any reader cannot tick both columns, they should re-read Part I before starting Part II. This recap also serves as a great "is this book working for me?" self-check.


---

# Part II — Bare-metal: Review

## Cross-cutting observations

- **Cortex-M → Cortex-A bridging is uneven.** Ch15 has an explicit "What is different from Cortex-M" section. Ch09–Ch14 introduce the chip without ever telling an MCU engineer what is different about Cortex-A7. The reader meets banked registers (`LR_irq`, `SP` in SVC vs IRQ mode), CPSR mode bits, CP15 system registers, CPSID/CPS instructions, and "PL1/PL0" without ever being told that on Cortex-M they had `MSP`/`PSP` and `IPSR`-coded handlers and that A-profile is a different beast. Add a short "From Cortex-M to Cortex-A7" sidebar somewhere in Ch09 or Ch10 — ideally a one-page table (NVIC↔GIC, MSP/PSP↔banked-SP-per-mode, fixed-vector-table↔VBAR, MPU↔MMU, SysTick↔EPIT/GPT, BX_LR-magic↔explicit-RFE).
- **CCGR enable values are not explained.** Every chapter does `REG(CCM_CCGRx) |= (3u << N)` and says "enable the clock," but the 2-bit-per-gate encoding (`0b00`=off, `0b01`=on-when-CPU-running, `0b11`=always-on, `0b10`=reserved) is never spelled out. An MCU engineer wonders why it's `0b11` not `0b1`. Add a one-paragraph CCGR encoding sidebar in Ch09 or Ch13 (it's also the source of every "why did the author write 3 << x?" moment).
- **`volatile` justification is good but its semantics relative to memory barriers is missed.** Ch10 §10.9 sells `volatile` correctly. But `volatile` does NOT give memory ordering, and on a CPU with caches and write buffers (Ch17+) you also need `dsb` / `dmb` between MMIO writes that must observe each other on the bus. Add a one-paragraph forward reference: "`volatile` covers the compiler; `dsb` covers the CPU; Ch17 will explain why both are needed."
- **Linker-symbol-as-address idiom is never explained.** Ch10's `ldr r0, =_sbss` and Ch14's `extern uint32_t _text_start; … (uint32_t)&_text_start` both rely on the trick that the *address of* a linker-defined symbol is the symbol's value. MCU engineers used to STM32 startup files have usually seen this, but it deserves one paragraph. Otherwise `&_text_start` looks like "addressing a four-byte variable" instead of "asking the linker for the location it stamped at link time."
- **No memory map figure for the SoC.** Every chapter quotes hex addresses (`0x020C406C`, `0x0209C000`, `0x021B0000`, `0x80000000`) but Part II never shows a 4 GiB map: ROM, OCRAM, AIPS-1, AIPS-2, GIC, DDR. Add one ASCII figure early in Ch09 (or pull it forward from Ch17 §17.2 which already maps DRAM and peripherals indirectly). Without it, the addresses feel arbitrary.
- **Inconsistent bit-position notation.** Some tables use "bits 26:27" (high:low order), some use "bits 27:26" (low:high), some use "Bits 26-27" (range). Pick one — ARM's convention is `[high:low]`, so write `[27:26]`. Mixing both inside Ch13 alone is visible.
- **"3% baud error tolerated" / "within 1% / 10% / 15%" claims are scattered.** These rules-of-thumb help, but they go by quickly. Box one (UART tolerance, DDR overclock margin, RTC drift) in a callout each time so the MCU engineer who is used to hand-tweaking knows where the limit lives.
- **Voice and sentence length.** Many sentences are short and choppy ("DDR works. We want to copy the *entire* image to DRAM at `0x80100000`…"). Reader's first language is not English; choppy fragments read worse than connected prose. Combine where you can. Specific examples noted per chapter.

## Ch09 — Assembly LED

### Readability
- "**Internalize it; we use it for every peripheral, forever.**" — drop "forever" (sounds dramatic); replace with "throughout this book."
- "**The blink is, in the most literal sense, you driving electrons through silicon you wrote a contract with.**" — striking but grammatically tortured. Suggest: "The blink is, in the most literal sense, electrons moving through silicon under a contract you wrote."
- "**Hanging off the end of an asm program is not a thing on bare-metal — you must explicitly loop forever.**" — "is not a thing" is colloquial; for an ESL reader, write "On bare-metal there is no OS to catch the fall-through; you must explicitly loop forever."
- "**About 160 bytes. Now we know how small bare-metal can be.**" — fine, but the next paragraph immediately jumps to objdump. Add a sentence connecting the two: "Let's look at what those bytes actually became."

### MCU-engineer friendliness
- The first paragraph of §9.1 ("The Chapter 9 program had no `.data` and no `.bss`...") never explains *why* the program has no `.data`/`.bss` and what the implication is — an MCU dev knows STM32 startup hits a `.bss` zero loop. One sentence: "An STM32 startup file would normally zero `.bss` and copy `.data`; we postpone both to Ch 10 because this program uses neither."
- §9.2 says "Without [the CCGR], all writes to the GPIO registers go into the void." Good. But add the MCU-style hook: "On STM32, this is `RCC->AHBxENR |= GPIOxEN`. The pattern is identical; only the name changes."
- "`ldr r0, =0x...` is GNU assembler syntax for 'load-pc-relative pool constant'." — a Cortex-M engineer has seen this with `ldr Rn, =label`; mention it: "On Cortex-M you've probably seen `LDR R0, =SomeFn`; this is the same construct."
- Nothing tells the reader that Cortex-A7 starts in **SVC mode** with `CPSR.I = CPSR.F = 1` after reset. Ch10's `startup.S` mentions it but Ch09 doesn't. The reader is doing memory writes with no awareness of what mode they're in.

### Missing examples / figures
- After the three-write-pattern paragraph in §9.2, add an ASCII diagram of how the three writes route signal flow: `CCGR1[27:26]` → "GPIO1 module clock gate enable" → `IOMUXC pad mux ALT5` → "pad-to-GPIO1_IO03 routing" → `GPIO1_GDIR.bit3=1` → "drive direction" → `GPIO1_DR.bit3=^bit3` → "level on pad."
- The IVT layout described in §9.5 is text-heavy. Add a tiny figure: a vertical strip showing offset 0x000 (pad), 0x400 (IVT 32B), 0x420 (BootData 12B), 0x42C (pad), 0x1000 (`_start`). Ch11 has this content but Ch09 introduces it first and would benefit from the picture too.
- A register layout figure for `CCM_CCGR1` showing CG0–CG15 as 2-bit fields with CG13 highlighted would unlock the "why `3 << 26`?" question instantly.

### Technical errors
- **Bit number inconsistency.** Tables on lines 55–56 say "(bit 4 = our pin)" for `GPIO1_DR` and `GPIO1_GDIR`. Code comment on line 115 says "Toggle bit 4 in GPIO1_DR." But pin `GPIO1_IO03` is **bit 3**, and the code itself correctly uses `(1 << 3)`. The summary line at line 27 also says "bit 3" correctly. Fix the table column ("bit 3 = our pin") and the two `bit 4` comments in the asm.
- "**Cortex-A7 cannot encode arbitrary 32-bit immediates in a single instruction**" — true, but the cause is the 12-bit rotated-immediate encoding of `MOV/MOVT` predecessors. A clarifying half-sentence helps: "...because the data-processing immediate form encodes only a rotated 8-bit value."
- §9.4 footnote about `-Ttext=0x00907400`: the OCRAM start is 0x00900000 with 128 KB, so 0x00907400 is at offset 29 KB. The chapter says "above the ROM's bookkeeping at the bottom of OCRAM." RM §8.7 puts the ROM's working area at 0x00900000–0x00906FFF (28 KB). State the 28 KB ROM region explicitly so the offset makes sense.
- "**The CCGR encoding for 'always on' is `0b11`.**" The CCM_CCGRx field encoding has four values: 00=off, 01=on-during-run, 10=reserved/off, 11=on-always. Spell out the table; this is the most reusable nugget in the chapter and it's hidden in one sentence.

### Knowledge prerequisites missing
- The chapter assumes `uuu` and SDP boot from Ch07/08. Fine — but the reader hasn't seen IVT/BootData yet; §9.5 hand-waves "accept the magic." A two-sentence "what the IVT is for, just enough to make this chapter run" callout would help. Currently the chapter says "we will write a Python tool in Chapter 11" without saying *why* an IVT is needed at all (i.e., "the ROM only loads images that begin with a 32-byte header").
- `.syntax unified`, `.cpu`, `.global` are briefly mentioned. A new-to-GAS reader needs one more sentence per directive — these aren't familiar from Keil/IAR.
- `_start` is the default GCC entry point — the chapter says "GCC's default entry is `_start` already" but never connects this to: "On STM32 your reset handler is named `Reset_Handler` and lives at vector[1]; here we just name our entry `_start` and the linker places it first."

### Other
- The 1.5 M iteration "≈ 8 ms" calculation in §9.3 should show its working. At 396 MHz with a 4-instruction loop body, `4/(396e6) × 1.5e6 ≈ 15 ms`, not 8. The lab at §9.8.1 then says "an inner-loop body of 4 instructions and a counter of 1.5M is ~15 ms" — so the §9.3 "~8 ms" is inconsistent with the lab. Pick one and be consistent.
- §9.6 step 4 calls out USB ID `15a2:0080`. The data sheet sometimes shows different VID for different mask sets; reference the *RM Table 8-X* or note "Your VID may be `15a2:00xx` depending on chip revision."

## Ch10 — C + startup.S + linker script

### Readability
- "**Without it, the first function-call instruction in C destroys the world.**" — drop the hyperbole or save it; for ESL readers it parses as literal. Suggest: "Without SP set, the first `push` in a C prologue writes to an undefined address and corrupts memory."
- "**Habit is cheap, and bugs from 'we will never need this' are expensive.**" — keep; this one lands.
- "**`bl main` is a *branched-and-link***" — typo: "branch-and-link" (no -ed).
- "**One instruction; three guarantees.**" — fine pithy line, but unpack which three explicitly since the prior line bundled them: "(1) mode = SVC, (2) IRQ masked, (3) FIQ masked."

### MCU-engineer friendliness
- §10.1 sells the no-loader idea well. Add one sentence: "On STM32, the linker and the ST-provided `startup_stm32fXXX.s` together provide what we are about to build."
- §10.3's mode-bit `0x13` for SVC is dropped without context. An MCU engineer hasn't seen CPSR `M[4:0]`. Add a tiny table (SVC=10011, IRQ=10010, FIQ=10001, USR=10000, etc.) at first use. Without this, the reader reads "mode = SVC" as a magic incantation.
- "`cpsid if, #0x13`" — explain that `i` flag masks IRQ, `f` flag masks FIQ. The `if` together is "mask both." Currently the comment says `@ mode = SVC, mask IRQ+FIQ` but the syntax is not parsed.
- §10.5 introduces `-mfpu=neon-vfpv4 -mfloat-abi=hard`. Cortex-A7 *has* a VFP and NEON; Cortex-M4F has VFP too. But on bare-metal you must enable the FPU before using it (writes to `FPEXC`/`CPACR`). The flags compile-time-enable codegen; the chapter never runtime-enables the FPU. If the reader's `main` accidentally uses a float, they will trap. Add a one-paragraph warning: "We pass `-mfpu` for codegen but we do not yet enable the FPU at runtime; Ch15 mentions where; until then, avoid float."

### Missing examples / figures
- §10.2 introduces `_etext`, `_sdata`, `_edata`, `_sbss`, `_ebss`. Add an ASCII figure showing the OCRAM layout with these labels stamped at the boundaries: a vertical strip from `0x00907400` (ORIGIN) up to `_stack_top`, with `.text`, `_etext`, `.data(VMA=LMA here)`, `_edata`, `.bss`, `_ebss`, `_irq_stack`, `_stack_top`. This single figure makes the whole script click.
- §10.2 should follow with a *second* figure showing the LMA-vs-VMA split when `.data` is moved to DRAM (forward-referenced from Ch14). One picture, two layouts side-by-side, would crystallize `AT(_etext)`.
- The literal pool concept from Ch09 is repeated here in §10.7 ("the literal pool follows the function"). Add a small disassembly snippet annotating "this is the pool" so the reader can see it.

### Technical errors
- §10.3 comment: "**The Boot ROM may have left us in another mode; SVC is what we want.**" The ROM enters SVC mode on i.MX6ULL after reset (per RM §8.X). The "may have left us in another mode" wording is overcautious and misleading. Better: "We are entered in SVC mode after reset; we re-assert mode and masks defensively."
- §10.4: `(1u << 3)` is `LED_BIT`. Code is correct (GPIO1_IO03 = bit 3). But the macro name suggests it's a *bit number* `3`, while the macro evaluates to a *mask* `0x08`. Either rename (`LED_PIN_BIT` for the bit number, `LED_PIN_MASK` for the mask) or note in a comment.
- §10.5 Makefile: `LDFLAGS := -T link.ld -nostdlib`. The rule invokes `$(CC) $(LDFLAGS) -o $@ $(OBJS)`, where `-Tlink.ld` is being passed to gcc — gcc forwards it to the linker. Works, but stylistically passing linker options to gcc usually uses `-Wl,-T,link.ld`. Not wrong; just note for the curious. (`gcc` does accept `-T` directly.)
- §10.5 `-fno-builtin -nostdlib` — `-nostdlib` already implies you have no libc; adding `-fno-builtin` on top is conservative but worth a one-line explanation ("prevents GCC from recognising e.g. `memcpy` and substituting library calls"). Otherwise the reader wonders why two flags say "no library."
- The `__attribute__((noreturn))` discussion in §10.8 is good. Note that GCC requires `void` return type for `noreturn`; `noreturn int main(void)` is contradictory. The compiler will warn or error; flag this.

### Knowledge prerequisites missing
- "**AAPCS requires SP to be 8-byte aligned at every public function entry.**" — what is AAPCS? First mention, no expansion. Spell out: "ARM Architecture Procedure Call Standard (AAPCS)."
- `KEEP(*(.vectors))` — the `*(.section)` linker syntax is explained ("gather all `.text*`"), but `KEEP` itself only gets one sentence about `-gc-sections`. An MCU engineer using IAR/Keil has not necessarily met `-gc-sections`. One additional sentence: "GCC's linker can be told to discard sections that nothing references; `KEEP` opts a section out of that."
- The CRT0 concept appears in "Going deeper" but never in the body. Worth a one-line callout: "`crt0.S` is what the standard C runtime uses as its `startup.S`; we are writing our own because crt0 expects a hosted environment."

### Other
- §10.7 ends with "Try it: change ORIGIN to `0x00908000`, rebuild, redump." Then "Then change it back." Combine into the lab section instead of mid-prose; the reader is unsure if it's mandatory.
- §10.11 mentions `_sbss` 4-byte alignment, but the zero loop uses `strlo r2, [r0], #4` which assumes 4-byte alignment of the *length* too. If `_ebss - _sbss` is not a multiple of 4, the loop overshoots. The `ALIGN(4)` on `.bss` handles the start but not the end. Mention or use a different terminator (`bne` on remaining bytes).

## Ch11 — Hand-building a Boot ROM-acceptable image

### Readability
- "**Owning the tool means owning the image format. Once you own the image format, you own boot.**" — fine.
- "**`uuu`'s magic and let it work.**" — confusing because the next chapter is the one that demystifies. Suggest: "...let the magic work for now; the next sentence shows what's inside it."
- "**Wait — entry is `0x00908000` but the code is *placed* at `0x00908400`? That's wrong.**" — strong rhetorical move; works. Just make sure the previous output block clearly shows the contradiction. Currently it does, but a "Look at the third line of the output:" pointer would help an ESL reader catch it.
- "**With 60 lines of Python and 50 lines of C and assembly.**" — closer might be 100 lines of Python + 30 lines of asm. Update or footnote with the actual count.

### MCU-engineer friendliness
- An MCU engineer rarely sees an "image header" — they `objcopy -O binary` directly to flash. The reason an i.MX needs one (mask ROM is generic, BootData is part of the boot protocol) is explained in Ch7 but worth a one-paragraph recap here: "Unlike STM32, where the boot ROM jumps directly to a fixed address and your reset vector at 0x08000004 is enough, the i.MX boot ROM accepts arbitrary load+entry through a small header."
- The big-endian-length-but-little-endian-rest gotcha is well-flagged. Add a one-paragraph explanation of *why*: "The header was designed for HAB (High Assurance Boot) sign/verify tools that came from networking codebases where big-endian lengths are conventional. The rest of the IVT was added later and is native ARM little-endian."

### Missing examples / figures
- §11.1's offset table is the layout. Convert it to a one-page ASCII picture (vertical strip of file offsets) — readers internalize spatial layouts faster than dotted tables.
- §11.3's hex dump + decode table is great. Worth adding "in pictures": draw the 32-byte IVT as a 4×8 grid with field names and the actual bytes for one example image.
- After §11.5, an ASCII figure of the SD card layout from byte 0 with sectors labeled: `[byte 0..0x400 = MBR area / pre-pad] [0x400..0x420 = IVT] [0x420..0x42C = BootData] [pad] [0x1000.. = code]`. The "LBA 2" / "byte offset 0x400" relationship is hard to track in prose.

### Technical errors
- §11.5: "`dd if=led.imx of=/dev/sdX bs=1k seek=1`" — `seek=1` with `bs=1k` writes at offset 1024 (0x400). Correct.
- §11.5 Option 2: "the `0x400` pad inside the `.imx` IS the first 1 KB of the SD card." Correct, and the cleaner approach. The chapter weighs both options well.
- "**`BootData.length` shorter than the file. Tail bytes are not loaded.**" — verify against RM. Some ROMs stop at `length`; some load entire input. For i.MX6ULL it's truly `BootData.length` that's authoritative.
- §11.6 vendor-image decode: the math "the simpler view is that `dcd_addr` is the *post-load* address" is glossed. Spell it out: "After the ROM finishes loading from the boot device into RAM at `BootData.start`, the DCD lives at `(dcd_addr - BootData.start)` bytes into the image, which on disk equals `0x400 + (dcd_addr - BootData.start)`."

### Knowledge prerequisites missing
- The chapter assumes Python 3, `struct`, `argparse` are familiar. They are for most readers; an MCU engineer who lives in C may not be. One-paragraph "if Python is unfamiliar, the script is doing X" footnote at the top of §11.2 helps.
- "HAB" is mentioned ("disables HAB signature checking. Will revisit in Chapter 62.") but not expanded. First-mention expansion: "HAB = High Assurance Boot, NXP's secure boot framework."

## Ch12 — UART driver and `printf`

### Readability
- "**This text travels at 115200 baud.**" — cute. Keep.
- "**Without it, RX appears dead.**" — keep.
- "**The chip rounds; up to ~3% baud error is tolerated by most receivers.**" — combine the next sentence: "Mismatched baud manifests as garbage characters that resemble valid ASCII but aren't."  Tighter: "Up to ~3% baud error is tolerated; beyond that you get garbage characters that resemble ASCII but aren't."
- "**Always. Every. Time.**" — final pitfall ("Forgot the CCGR"). Sets tone; works.

### MCU-engineer friendliness
- An MCU engineer has used STM32's USART, which also has UBRR-style baud divisors. Open §12.2 with one sentence: "STM32's USART uses `BRR = f_CK / baud`; the i.MX is the same shape but with a *fractional* divisor (numerator/denominator pair) instead of an integer." This frames the whole chapter.
- §12.4 says "8N1; RX+TX enable; release SRST." Spell out what 8N1 means once on first use ("8 data bits, no parity, 1 stop bit") — most know it, but completeness costs nothing.
- "`UCR2.SRST` is **active-low**" — write `SRST = 0` means *asserted reset*. Counterintuitive for an MCU engineer who is used to "1 = active." Bold this sentence — it's the most surprising single thing in the chapter.

### Missing examples / figures
- §12.2 baud-rate derivation deserves an ASCII flow: `XTAL 24 MHz → PLL3 480 MHz → /6 → uart_clk_root 80 MHz → ÷RFDIV(1) → ÷16 oversample → × UBIR/UBMR fraction → 115200`. The intermediate divisions are scattered in prose.
- A register-bit diagram of `UCR2` showing `IRTS / WS / TXEN / RXEN / SRST` highlighted would help. Same for `USR1` and `USR2`.
- After §12.4, a sequence diagram of "what `uart_putc('A')` does on the wire": spin on TRDY → write 0x41 to UTXD → 1 start + 8 data + 1 stop bits at 8.68 µs each → 10 × 8.68 µs ≈ 87 µs.

### Technical errors
- §12.1: "On the Point Atom MINI these are routed to pads **UART1_TX_DATA** and **UART1_RX_DATA**." This is circular wording. Suggest: "On the MINI these signals are routed to the pads named `UART1_TX_DATA` and `UART1_RX_DATA` (the pads have the same names as the UART1 module signals because they default to that function at ALT0)."
- §12.1: "**IOMUXC_UART1_RX_DATA_SELECT_INPUT** at `0x020E0624`, telling UART1 which pad to listen on for RX (usually `0` for the matching `UART1_RX_DATA` pad)." Then §12.4 sets `REG(IOMUX_DAISY) = 3`. Discrepancy: "usually 0" but code writes `3`. Cross-check against the RM SELECT_INPUT register table. For UART1_RX_DATA_SELECT_INPUT the daisy values map to specific pads; if the MINI uses the `UART1_RX_DATA` pad itself, the value is 3 per RM (selecting that pad as the input source). The comment "usually 0" is wrong — fix or explain.
- §12.4 UCR4 comment: "`(1u << 0)` /* DREN: receive-ready interrupt enable bit; we don't use IRQ yet but writing 0 elsewhere is fine */". The code sets bit 0 (= DREN = DMA Enable for Receive). Then comment contradicts itself ("we don't use IRQ"). Per RM §55.15.4, UCR4 bit 0 is `DREN` (DMA Receive Enable). Setting it to 1 in polled mode is wrong — should be 0. This is likely a bug.
- §12.2 baud calc: "(UBIR + 1) / (UBMR + 1) = 0.02304" then "UBIR = 70, UBMR = 3082". 71/3083 = 0.02303. Correct. Show the actual achieved baud (80e6 / 16 × 71/3083 = 115,160 Hz, off by 0.035%) so the reader sees how close — and add "this is within the 3% tolerance band."
- §12.5 `va_arg(ap, unsigned)` discussion: on AAPCS / 32-bit ARM, `unsigned int` and `unsigned long` are both 32 bits, so the code works, but on 64-bit ARM (AArch64) they differ. Add a one-line note "On AArch64 we'd need `unsigned long` for the same code; we are 32-bit here."

### Knowledge prerequisites missing
- `va_arg`, `va_list`, `va_start`, `va_end` (§12.5) come in unannounced. Most C devs know them, but a one-paragraph recap with the warning "these are macros, not functions; their internal state is implementation-defined" would be charitable.
- `picocom` — first introduced in earlier chapters? Quickly recap connection params (`picocom -b 115200 /dev/ttyUSB0`) in the §12.6 build/run block.

### Other
- §12.4 sets `IOMUX_PAD_RX = 0x000130B1` (with keeper) but `IOMUX_PAD_TX = 0x000010B0`. The two pad-control values differ; the difference (HYS bit and keeper) is buried. Add a one-line decode of each: "HYS=1, keeper enabled, PUS=… for RX to avoid floating; output-only TX needs none."
- §12.9 pitfalls is great. Add: "`UBMR` written before `UBIR`" symptom = baud rate inverted/scrambled.

## Ch13 — CCM clock tree bring-up

### Readability
- "**Every peripheral hangs off one root clock; each root clock hangs off one PLL.**" — keep, but slightly inaccurate (some peripherals use osc24m directly, no PLL). Soften to "most peripherals."
- "**Software-reads-software-writes is the easiest check to lie to itself.**" — elegant.
- "**Or, more simply: put PLL1 in bypass while reprogramming. Bypassed PLL1 outputs the 24 MHz reference, so the core runs slow but never crashes.**" — clearer than the step-clk alternative; move this to be the primary explanation rather than alternative.
- "**Looks like text but has occasional corruption.**" (re: baud) — concrete; good.

### MCU-engineer friendliness
- §13.2: An MCU engineer knows PLLs from STM32's RCC: HSE → PLLM/PLLN/PLLP → SYSCLK. Frame i.MX's tree against that: "STM32's PLL has one VCO and a few post-dividers. i.MX has *many* PLLs and *PFDs*, which are fractional dividers off each PLL's VCO. This gives more output options at the cost of complexity."
- §13.4 step 1 talks about "step_clk" then says "Or, more simply: bypass." Choose one and explain it. Right now the reader is told two ways without a recommendation — actually the second is the chosen path.
- "**PMU**" is introduced in §13.6 with no explanation. On Cortex-M there's no PMU (you use SysTick/DWT). One sentence: "The Cortex-A7's PMU (Performance Monitor Unit, ARM PMUv2) provides cycle counter, event counters, and architectural events; we use only CCNT (cycle counter)."

### Missing examples / figures
- An ASCII tree diagram of the clock tree we're building. Roots: 24 MHz XTAL. Branches: PLL1 (ARM), PLL2 (System=528 MHz fixed → PFD0/1/2/3), PLL3 (USB1=480 MHz fixed → PFD0/1/2/3), PLL5 (Video), PLL6 (ENET), PLL7 (USB2). Each PFD feeds a mux feeding a divider feeding a peripheral. This *is* the chapter — without the picture, the reader has to draw it themselves.
- §13.2 PFD encoding: figure showing each 32-bit `ANATOP_PFD_528` register as four 8-bit byte lanes (PFD0..PFD3), each with FRAC[5:0], CLKGATE, STABLE.
- §13.5 "Expected" output should be paired with a "what you actually saw" troubleshooting box for common deviations.

### Technical errors
- §13.4 step 6: "PFD2 is in ANATOP_PFD_528 bits 16:21 (PFD2_FRAC). Bit 23 (PFD2_CLKGATE) must be 0." Per RM §18.7.16, PFD2_FRAC is bits **21:16** (FRAC[5:0]) and PFD2_CLKGATE is **bit 23**. Correct.
- §13.4 step 7 (CBCMR PRE_PERIPH_CLK_SEL): "Bits [19:18] -- select what feeds the periph_clk mux: 00=PLL2 (528), 01=PLL2_PFD2 (396), 10=PLL2_PFD0, 11=PLL2_PFD2/2." Per RM §18.6.10, the encoding is: 00=PLL2 528, 01=PLL2_PFD2, 10=PLL2_PFD0, 11=PLL2/2 (PLL2 divided by 2). The "11=PLL2_PFD2/2" claim is suspect — cross-check the table. Default reset value is 01 (PLL2_PFD2). The reset already does what we want; the code is fine but the table description for `11` needs verification.
- §13.4 step 9 "CSCDR1.UART_CLK_SEL (bit 6) = 0 -> PLL3_80M (already /6)". Per RM §18.6.13, UART_CLK_SEL bit 6: 0 = derive from PLL3 80MHz, 1 = osc_clk. Correct.
- §13.5: "Pre-clocks_init(): ARM = 396000000 Hz". The function `clocks_get_arm_hz()` does `XTAL × DIV / 2 / (CACRR+1)`. After ROM, with default CACRR + default PLL_ARM (DIV=88? actual reset varies), what does it report? The chapter just states 396 MHz. Actual i.MX6ULL boot-ROM leaves ARM_PODF defaulting to /1 and PLL_ARM at the reset DIV_SELECT (88), so ARM = 24*88/2 = 1056? Or the ROM reprograms? Verify the claim "ARM = 396 MHz" experimentally and document the chain.
- §13.7 "1 cycle = 2.525 ns" at 396 MHz: 1/396e6 = 2.525e-9 s. Correct.

### Knowledge prerequisites missing
- The chapter uses "ATOMIC SET/CLR/TOG registers at +4/+8/+0xC" once (§13.2) but the reader has not seen this NXP idiom. One paragraph: "Each ANATOP register has three sibling addresses 4/8/12 bytes ahead, used for atomic SET (write-ones-to-set), CLR (write-ones-to-clear), TOG (write-ones-to-toggle). On a multi-core SoC this avoids the read-modify-write race; on our single-core bare-metal, it's a convenience."
- `mrc p15, …` / `mcr p15, …` (§13.6 PMU): co-processor instruction syntax. An MCU engineer hasn't used CP15. One paragraph at first use explaining `mcr<sub>15</sub>(opc1, CRn, CRm, opc2)` mapping to architectural register names.

### Other
- §13.6 "scope a GPIO" — at 696 MHz, a 5-cycle-per-iteration loop produces 70 MHz; the chapter notes "the scope and the GPIO drive strength will not produce cleanly; you'll see a degraded waveform but the *period* is measurable." The MCU engineer reading might not have a 100+ MHz scope. Suggest a lower-frequency variant ("add 20 nops; toggle at ~1 MHz") for cheaper instruments.
- §13.8 step 4 "set DIV_SELECT = 66" should give 24 × 66 / 2 = 792 MHz. Verify the wording matches.

## Ch14 — DDR3 initialization with MMDC

### Readability
- "**Set an afternoon aside.**" — keep.
- "**You cannot guess them; you must look them up.**" — keep; punchy.
- "**Treat them as a black box you can re-derive at any time by running the tool.**" — re-derive *by* not *at*.
- "**For *learning*, doing it in C (as we did) is better — you see the logic. For *deployment*, the DCD is better — it lets you load larger images.**" — neat trade-off framing.

### MCU-engineer friendliness
- Most MCU engineers have never touched external DRAM (STM32H7 has an FMC controller, but few use it). The §14.1a primer is helpful but should highlight *why DRAM is hard*: refresh requirement, timing sensitivity, calibration drift with temperature, signal integrity demands beyond a Cortex-M's SRAM connection. Even a one-paragraph "what makes DRAM bring-up different from peripheral bring-up" would orient the reader.
- "**Refreshed every 64 ms**" — explain the consequence: "the DRAM controller has to issue ~8000 refresh commands per second in the background." Otherwise "refresh" is an abstract word.

### Missing examples / figures
- An ASCII figure of the DDR3 protocol: command bus, address bus (RAS/CAS/CKE), data bus (DQ + DQS), control (CS, ODT). MCU engineers know SPI; DDR3 is "very wide SPI on steroids" but the analogy needs a picture.
- A timing diagram showing the JEDEC init sequence in §14.6: RESET#, CKE, NOPs, MRS0..3, ZQCL spread across the 500 µs+200 µs+ZQ window.
- A diagram of MMDC's three calibration steps (write leveling, DQS gating, read/write delay) showing what each compensates for (CK vs DQS skew, DQS framing window, per-bit data eye centering).
- The "two chips, one bus" picture in §14.3 (16-bit bus from two ×8 chips) deserves an ASCII figure with chip-1 driving DQ[7:0], chip-2 driving DQ[15:8].

### Technical errors
- §14.6 MR0 encoding table: "CAS latency CL = 11 → 1110_1 → 0b01110". The MR0 CL field is bits {6:4, 2}, *not* contiguous. The encoding for CL=11 per JEDEC JESD79-3F Table 41 is `A6:A4 = 0b011`, `A2 = 0b1`. So the bit pattern across MR0 is `... A6=0, A5=1, A4=1, A3=?, A2=1 ...`. The "0b01110" looks like a contiguous 5-bit value, which is not how MR0 encodes it. Re-derive and present as the {6:4} + {2} split.
- §14.6 MR0 "tWR for tWR=15ns@800MHz, 6 ⇒ 0b101". For DDR3, tWR_min(cycles) = ceil(15 ns / tCK). At 800 MT/s, tCK = 2.5 ns, so tWR = ceil(15/2.5) = 6 cycles. MR0[11:9] encoding for tWR=6 is `010` per JEDEC; for tWR=8 it's `100`. The "6 ⇒ 0b101" claim is wrong (`101` encodes tWR=14). Verify and correct.
- §14.6 representative MR values labeled as "depends on exact tWR/CL". MR0 = 0x00000A50. Decode: bits[11:9]=`101`(=tWR_enc 5 → 14 cycles), bits[8]=`0`(DLL not reset), bits[6:4]=`101`(CL bits hi)=>CL_hi=5, bit[3]=`0`, bit[2]=`0`(CL low bit). The actual MR0 for CL=11, tWR=6 should be ~0x00000C50 or ~0x00000A60 depending on burst length. **Strongly recommend recomputing from JEDEC tables and republishing exact values**, OR clearly labelling these as "placeholder bit patterns, not valid for any real configuration."
- §14.6 MR1 = 0x00000044. Decode: bit 6 = `1` (Rtt_Nom A6), bit 2 = `1` (Rtt_Nom A2 → composite Rtt_Nom = 0b101 with A9 = 0 → invalid for DDR3). The values look ad-hoc.
- §14.10 `relocate_to_dram`: `entry_t entry = (entry_t)(0x80100000 + ((uint32_t)main - 0x00907400));`. This assumes `main` was linked at the OCRAM load address. But the linker placed `main` somewhere inside `.text` starting at `_text_start` not at `0x00907400` (which is the IVT/header base). The arithmetic is plausible if `_text_start = 0x00907400` and `main` lives there, but the chapter never reconciles. Recommend using a linker-provided symbol `_main_offset = main - ORIGIN(OCRAM)` and then `entry = 0x80100000 + _main_offset`. As written, the off-by-IVT-header (0x1000) is potentially wrong if the loaded image starts at 0x00907400 but `_start` is at 0x00908400 (per Ch11 §11.3).
- §14.10 "The flag-in-`.data` works because we copy `.data` along with `.text`" — but `relocate_to_dram` only copies `_text_start..._text_end + _data_start..._data_end`. The chapter shows two contiguous copies but the source addresses use `0x00907400` as the start of *everything*, which conflates `.text` LMA with `.data` LMA. Per Ch10's linker script, `.data` LMA is at `_etext`, not `_text_start`. The logic is broken: the second copy would copy the *same* address range as the first (because both start from `src = 0x00907400`). Rewrite the relocation code with explicit per-section source/dest addressing, OR copy the contiguous OCRAM image as one block.
- §14.7 `MDCFG2 = 0x01FF00DB` value placement: the comment says "tDLLK, tRTP, tWTR, tRRD" but MDCFG2 layout is tDLLK[31:16], tRTP[6:4], tWTR[3:0] (no tRRD in MDCFG2 — tRRD is elsewhere). Cross-check RM §39.4 register map. The chapter's claim "MDCFG2: tDLLK, tRTP, tWTR, tRRD" is approximate at best.
- §14.13 NXP DDR Stress Tool — "Windows GUI / CLI program." Newer releases also have Linux CLI variants. Update if appropriate.
- §14.10 "use a flag" pattern: `static uint32_t already_in_dram = 0;` followed by `if (!already_in_dram) { ... already_in_dram = 1; relocate_to_dram(); }`. But the *DRAM copy* sees `already_in_dram = 1` only if `.data` (which contains `already_in_dram`) was correctly copied to DRAM with the value `1` *after* the OCRAM execution set it to 1. Order matters: the OCRAM main first sets `already_in_dram = 1`, then calls relocate which copies `.data` (now containing `1`) to DRAM, then jumps. The DRAM copy reads `1` and skips the init block. This works iff the copy happens AFTER the OCRAM main sets the flag. The current code in §14.10 sets `already_in_dram = 1` *then* calls `relocate_to_dram()` — correct. But this is subtle; add a comment explaining the ordering.

### Knowledge prerequisites missing
- The "Mode Register" terminology comes from JEDEC DDR3 standard, not from i.MX. State explicitly: "MR0..MR3 are *DDR3 chip* registers (not MMDC registers). The MMDC's `MDSCR` command interface is what sends `MRS` (Mode Register Set) packets to the chip over the DRAM bus."
- "ZQ calibration" is named without explanation. One sentence: "ZQ calibration tunes the chip's output driver impedance against an external 240 Ω precision resistor (ZQ pin); it must be done at boot and periodically thereafter."
- "ODT" briefly explained as "on-die termination" but its purpose (signal-integrity matching for the bus's reflection-free operation) is left implicit.

### Other
- §14.7 `ddr_iomux()` shows one register write and "... (all DRAM pads) ...". For a chapter that demands the reader run real code, omitting the bulk of pad config is risky. Either provide the full list (it's ~30 lines), reference a downloadable companion file with the complete table, or warn loudly "this is a sketch; you cannot run this without the full pad config from §14.5."
- §14.15 pitfall "Wrong MR0 CAS latency": "CL=11 on chip = `MR0[6:4,2] = 0b1110_1`". Note same `0b1110_1` issue as §14.6 — the field is non-contiguous and the underscore should make that explicit.
- The chapter could really use the calibration values from a known-good Point Atom MINI BSP committed as a constant block, so a reader can compile-and-go for first attempt before running the Stress Tool. Currently the reader can't even *try* without the tool.

## Ch15 — Exceptions and the GIC

### Readability
- §15.1 "**No auto-stacking. Your handler must save and restore registers itself.**" — perfect framing for the MCU engineer. This is the best Cortex-M-vs-Cortex-A intro in Part II.
- "**All of it correct, all of it terrifying the first time you read it.**" — re: Linux entry-armv.S; keep.
- "**Eleven steps. Every Linux IRQ in user space follows the same pattern.**" — strong closing of §15.8.

### MCU-engineer friendliness
- §15.1 is genuinely good. Apply this exact pattern (Cortex-M-vs-A diff box) at the start of Ch09 and Ch10 too — the rest of Part II is missing this scaffolding.
- The "banked register" concept is implicit in §15.4 ("IRQ mode needs its own stack") but never visually shown. A reader who has never seen banked registers will mentally model "IRQ mode" as "a flag" rather than "a different SP/LR pair." Show the bank.
- "**`bl c_irq_dispatch` is the standard branch-and-link, but with our preserved state.**" — fine; but emphasise that `BL` writes LR with the return address (= current PC+4 in ARM mode), and that this LR is the *SVC mode LR* now that we switched modes. The mode-switch erases the `LR_irq` from view (it's banked).

### Missing examples / figures
- **A banked register diagram.** Show R0–R7 shared, R8–R12 shared (with FIQ-mode having its own R8–R12), then for each mode (USR/SYS, SVC, IRQ, FIQ, ABT, UND) show separate SP and LR, plus SPSR per privileged mode. This single figure is the missing centerpiece of Ch15.
- **A CPSR/SPSR bit-layout diagram.** Show the mode bits M[4:0] with the five encodings used, plus the I/F/T/A flags.
- **A "vector table on disk vs in memory after VBAR" picture.** Show the 8-instruction table at `_vectors` with each slot's offset and what it branches to.
- **A timing diagram of `irq_entry`'s stack manipulation.** Show the IRQ stack before/after `srsdb`, the SVC stack before/after `push`, and the return path.
- §15.5 GIC flow has 9 steps in prose. Convert to an ASCII swimlane diagram (Peripheral | Distributor | CPU IF | CPU | Handler).

### Technical errors
- §15.3 `sub lr, lr, #4` comment: "**adjust LR_irq to point at the *interrupted* instruction (so RFE re-executes it... no, it resumes correctly with this -4 fixup)**". The wording is confused. The CPU stores PC+4 in LR_irq on IRQ entry (or PC+8 for prefetch/data abort, depending on the spec edition). The -4 makes LR_irq point to the *next* instruction to execute, which is the one that *would have* executed had the IRQ not fired. `rfeia` then resumes there. Clean up the comment — the "no, it resumes correctly" mid-sentence reverse is confusing.
- §15.3 `srsdb sp!, #0x12`. Per ARM ARM, `SRSDB SP!, #mode` stores `LR_<current_mode>` and `SPSR_<current_mode>` to the *banked SP for <mode>*. So `SRSDB SP!, #0x12` from IRQ mode stores onto the IRQ stack — but it reads LR_irq and SPSR_irq from the *current* mode (IRQ, since we're in it). This is correct in the chapter's code but the explanation "stores `{LR, SPSR}` to the IRQ-mode stack pointer. Mode 0x12 = IRQ" reads as if the mode operand selects what to *save*. Clarify: "the `#0x12` selects which mode's SP is used as the storage base."
- §15.5 table for `GICD_IPRIORITYRn`: "Priority (8 bits each; 256 bytes for 256 IRQs)". The total IRQ count on this GIC is 160 (TYPER reports it); 256 was overstated. Match `MAX_IRQ = 192`.
- §15.5 says GIC distributor at `0x00A01000`. The Cortex-A7 typically *exposes* the GICD inside an internal `peripheral base + 0x1000`. The peripheral base on i.MX6ULL is `0x00A00000`, so GICD = `0x00A01000`. Correct, but mention the parent peripheral-base CP15 register `CBAR` so the curious can verify.
- §15.7: "UART1's IRQ goes through GIC SPI ID **26**. In GIC terms that's `26 + 32 = 58` — but the *GIC's view* of the IRQ ID also adds 32 internally. Conventionally we use the SoC's labeling, which on i.MX6ULL puts UART1 at GIC ID 58." This is muddled. Per RM Table 3-1, the listed IRQ number is the SPI number minus 32 — actually per RM the listed IRQ uses GIC INTID directly (so the table number IS the SPI number, with `+32` going to the GIC INTID). The chapter's claim "GIC's view of the IRQ ID also adds 32 internally" is wrong — the GIC distributor uses INTIDs directly with SGIs=0–15, PPIs=16–31, SPIs=32+. Verify against the GIC v2 spec, and rewrite this paragraph. Suggested clean version: "RM Table 3-1 lists this as 'IRQ 26.' That number is the SPI offset; the GIC INTID is `32 + 26 = 58`, which is what we pass to `gic_register` and `gic_enable_irq`."
- §15.6 `c_irq_dispatch`: `uint32_t irq = iar & 0x3FF;`. Correct (IAR's INTID is bits 9:0 = 10 bits). But the *spurious interrupt* check is missing. If `iar == 1023` (spurious), `handlers[1023]` is OOB. Add a check.
- §15.7 "`UCR1.RRDYEN`" (bit 9) — verify against RM. UCR1 bit 9 is RRDYEN (Receiver Ready Interrupt Enable) per §55.15.4. Correct.

### Knowledge prerequisites missing
- `mcr` / `mrc` syntax: introduced briefly in Ch13 PMU code, used here for VBAR. The mnemonic decode (`mcr p15, opc1, Rt, CRn, CRm, opc2`) deserves a one-paragraph reference card on first heavy use.
- "AAPCS" referenced in pitfalls and prose but expanded only in Ch10.
- `dsb`, `isb` introduced in §15.4 ("isb after VBAR write") and §15.10 ("`dsb; isb` around MMU/cache changes"). Define on first use: "`dsb` (Data Synchronization Barrier) waits for all preceding memory accesses to complete before the next instruction; `isb` (Instruction Synchronization Barrier) flushes the pipeline so the next fetch sees the new system state."

### Other
- §15.6 `gic_register` uses a flat array `handlers[MAX_IRQ]` indexed by INTID. Memory: 192 × 4 = 768 bytes in `.bss`. Fine for bare-metal; might be worth a comment.
- §15.9 lab 5 (trigger data abort): the suggested fix "use JTAG to inspect" is fine but for a reader without a JTAG dongle, the lab is unrunnable. Provide an alternative: "or rewrite `data_handler` to switch to SVC mode and `printf` the fault address from `DFAR`."

## Ch16 — Timers

### Readability
- "**You could use one timer for both jobs ... but separating them keeps each minimal.**" — keep.
- "**Production code would track 64-bit ticks (read low, read high, re-read low, retry on wrap — the standard 32-bit pair pattern).**" — good — this is the same pattern §18C.6 uses; cross-reference them.
- "**`udelay(1)` calibration. From Ch 16, `udelay` is GPT-based; should be accurate to within 1 µs.**" — accurate phrasing.

### MCU-engineer friendliness
- "**EPIT (Enhanced Periodic Interrupt Timer)**" — name decoded; good.
- "**GPT (General Purpose Timer)**" — also good.
- Frame against SysTick: "SysTick on Cortex-M is a 24-bit countdown timer with a single ISR; Cortex-A7 has no integrated SysTick equivalent. Linux on i.MX6ULL uses the Cortex-A7 *generic timer* for both tick and clocksource; we use EPIT (analog of SysTick) and GPT (analog of an STM32 TIM in free-run mode)." This bridge is missing.

### Missing examples / figures
- A timing diagram: the IPG clock (66 MHz) feeding EPIT's down-counter loaded with 66000, hitting zero every 1 ms, triggering IRQ.
- GPT register bit-fields: a one-figure diagram of `GPT_CR` showing `EN, ENMOD, FRR, CLKSRC[8:6], SWR[15]` highlighted.
- A picture comparing PMU CCNT (cycle-precise, clock-tied) vs GPT (time-precise, divided to 1 MHz). Useful for "when do I use which."

### Technical errors
- §16.2: "`PRESCALER = 0 (divide-by-1)`" in EPIT discussion. EPIT_CR has PRESCALER at bits [15:4] (12 bits). 0 means /1. Correct.
- §16.2 GPT prescaler "65 = divisor 66". Register field `PRESCALER[11:0]` value N means divide by N+1, so 65 → /66. Correct.
- §16.3 EPIT IRQ ID: "GIC SPI ID for EPIT1 = 88 on i.MX6ULL (RM Table 3-1). Verify." Per RM Table 3-1 (entry 56: "epit1 - EPIT1 output compare interrupt"), the listed IRQ is 56, which gives GIC INTID = 56 + 32 = 88. Correct under the SPI+32 convention. But the comment "GIC SPI ID = 88" is again confused — 56 is the SPI ID; 88 is the GIC INTID. Same issue as Ch15. Fix wording.
- §16.3 "Bits to enable in EPIT_CR: (1 << 25) CLKSRC, (1 << 22) IOVW, (1 << 3) RLD, (1 << 2) OCIEN, (1 << 1) ENMOD, (1 << 0) EN." Per RM §30.5.1 EPIT_CR: CLKSRC[25:24] (2 bits). Writing `1 << 25` sets bit 25 alone, which is CLKSRC = 0b10 (high-frequency reference). The chapter intends "peripheral clock" which is CLKSRC = 0b01, i.e., `1 << 24`. **Bug.** Verify and fix.
- §16.3 IOVW bit position: per RM §30.5.1, IOVW is bit 17, not bit 22. **Bug** — verify and fix.
- §16.2 GPT_CR bits used: "`(1 << 9) FRR free-run, (1 << 1) ENMOD, (1 << 6) CLKSRC, (1 << 0) EN`". Per RM §29.5.1 GPT_CR: CLKSRC[8:6] (3 bits). `1 << 6` = CLKSRC = 0b001 = peripheral clock. Correct. FRR is bit 9. Correct. ENMOD is bit 1. Correct. EN is bit 0. Correct. Good.
- §16.5 "A 4 MB write + 4 MB read on DDR3 at 396 MHz takes ~30 ms (≈ 250 MB/s). At 696 MHz CPU that's ~21 million CPU cycles. The cycle/µs ratio should be ~696, matching the CPU clock; if it isn't, your clock initialization (Chapter 13) is wrong." — Math: 30 ms = 0.03 s. At 696 MHz CPU, 30 ms = 0.03 × 696e6 = 20.88 million cycles. Correct. Cycle/µs at 696 MHz = 696. Correct.

### Knowledge prerequisites missing
- "Jiffies" is a Linux kernel term meaning "the tick counter." The chapter uses `jiffies_ms` without explaining; an MCU engineer who's seen FreeRTOS knows `xTickCount` but not `jiffies`. One footnote: "Linux calls this counter `jiffies`; we keep the name as forward-compatibility."
- W1C (write-1-to-clear) is used several times without expansion. First-use definition: "the status flag is cleared by writing 1 to it, *not* by writing 0. This is conventional for sticky flags in ARM peripherals."

### Other
- §16.4 main() does `uart_init(); clocks_init(); uart_init();`. The double init is intentional (clocks change → UART divisors stale). Comment it.
- §16.6 lab 4 "Inside `epit_isr`, `printf("tick\n")`." `uart_putc` polls; printf is heavy. The lab is valid but the result at 1 ms tick × 87 µs per character × ~5 chars/line = 435 µs per tick — close to 1 ms — the system will spend half its time inside the ISR. Note this as the *teaching* point of the lab.

## Ch17 — MMU and caches

### Readability
- "**The last bare-metal infrastructure piece.**" — keep.
- "**Our way is harder to misconfigure.**" — keep.
- "**The 10× factor is real and is the reason Linux insists on having caches before doing anything useful.**" — keep.
- "**Memory-mapped IO that wrongly cached: works on a board where MMU is off, breaks the moment caches are on.**" — paraphrasing; the §17.7 wording is "code works on a board where MMU is off, breaks the moment caches are on." Slightly awkward — should be "code that works without the MMU on breaks the moment caches turn on." Re-flow.

### MCU-engineer friendliness
- Cortex-M3/M4/M7 has an *optional* MPU (Memory Protection Unit) with 8 or 16 regions, no virtual-physical translation. Cortex-A7 has an MMU with 1 MiB sections (and 4 KiB pages via L2). Frame the leap explicitly: "MPU: protection only, VA=PA, region table. MMU: protection + translation + caching attributes, full page table." This is the chapter's biggest opportunity to bridge.
- The "short descriptor" vs "long descriptor (LPAE)" choice — explain in one paragraph that LPAE is needed for >4 GiB physical, which we don't have.
- §17.6 cache maintenance: "Before a DMA peripheral reads from a buffer, the CPU must **clean** the buffer's cache lines." Frame this with Cortex-M analog: "On Cortex-M7 with DMA you've maybe seen `SCB_CleanDCache_by_Addr` / `SCB_InvalidateDCache_by_Addr`. The Cortex-A7 versions are CP15 ops; same intent, different mnemonics." Then the readers' knowledge transfers.

### Missing examples / figures
- **The L1 entry bit layout diagram (Critical, identified in user prompt).** §17.2 has a quasi-figure but it's misaligned and bit numbers are confusing ("TX EX") . Redraw as ASCII with bit ranges clearly stamped:
  ```
   31      20  19  18  17 16 15 14   12 11   10 9  8   5 4 3 2 1 0
  ┌──────────┬───┬───┬───┬──┬───┬──────┬─────┬───┬─────┬──┬─┬─┬─┬─┐
  │ Sect base│NS │ 0 │nG │ S│AP2│TEX[2:0]│AP[1:0]│IMP│Dom │XN│C│B│1│0│
  └──────────┴───┴───┴───┴──┴───┴──────┴─────┴───┴─────┴──┴─┴─┴─┴─┘
  ```
  with TEX/C/B encodings table beneath.
- **A 4 GiB virtual-to-physical map.** Show the 4096 L1 entries as a stack: 0..0x009 device, 0x009 OCRAM (Normal), 0x00A..0x07F device, 0x080–0x09F DRAM (Normal), 0x0A0..0xFFF device. (Or whatever exact mapping the code produces.)
- **A two-stage figure of "page table walk" for a hypothetical access.** Show the CPU emitting a VA, the MMU splitting VA[31:20] as L1 index, looking up the L1 entry, extracting the section base, concatenating with VA[19:0] to form PA, sending PA to the bus.
- **Before-MMU / After-MMU bandwidth comparison.** §17.8 has a table; promote it to a chart-style ASCII or at minimum bold the 10× factor.

### Technical errors
- §17.2 bit layout figure includes "TX EX" — that should be "TEX". Typo.
- §17.2 AP encodings: "For 'full access at PL1, no access at PL0,' AP = `0b001` → AP2=0, AP[1:0]=01. For 'full access at PL1 and PL0,' AP = `0b011`." Per ARM ARM B3.7.1: AP[2:0]=001 means PL1 RW, PL0 no access. AP[2:0]=011 means PL1 RW, PL0 RW. Correct.
- §17.3 `__attribute__((aligned(16384)))` is correct (L1 table base alignment). But the size of the table is `4096 × 4 = 16384` bytes, which matches the alignment. Good — note this coincidence in prose.
- §17.3 `invalidate_dcache_all` uses "256 sets × 4 ways" hardcoded. Per Cortex-A7 TRM the L1 D-cache is 32 KB with 4-way set-assoc and 64-byte lines: 32768/(4×64) = 128 sets, not 256. **Probable bug.** Verify against `CCSIDR_EL1` (in 32-bit ARM, `CCSIDR`) which tells you `(NumSets-1)` and `(Associativity-1)`. The chapter even mentions "256 sets, 4 ways, 64-byte lines" inline (twice in §17.3 and §17.10). If wrong, all the "invalidate D-cache" inner-loop iterations are wrong.
- §17.3 set/way invalidate mnemonic and operand layout: per ARM ARM, the DCISW operand is `way[A-1:A-W]:set[L+S-1:L]:level[3:1]:...` where W = log2(associativity), S = log2(num_sets), L = log2(line_size). For Cortex-A7: way occupies bits [31:30] (W=2), set occupies bits [13:6] (S=8 for 256 sets, or [12:6] S=7 for 128 sets), line bits [5:0]. The chapter writes `(way << 30) | (set << 6)`. If sets=128, set should be in [12:6], which means `(set << 6)` for set up to 127 works (fits in bits 6..12). Verify against the geometry above.
- §17.3 `cp15_write_dacr(0x55555555)`: each domain is 2 bits, 16 domains. `0x5 = 0b0101` → bits[1:0]=01 (client). `0x55555555` = all 16 domains as client. Correct.
- §17.4: "Roughly an 8× speedup on the memtest. The exact ratio depends on access pattern; sequential memcpy can hit 10–15× with both caches on." Believable for L1-resident sizes; 4 MB doesn't fit in 32 KB L1, so the L1 D-cache is mostly thrashing and the *L2* (128 KB) takes over. The "10–15×" feels optimistic for 4 MB — likely the right ballpark is 4-8× for that size. Validate with a real measurement if possible.
- §17.6 `dcache_clean_va` macro: "DCCMVAC". Verify: per ARM ARM, the `DCCMVAC` op (Data Cache Clean by Modified Virtual Address to PoC) is `mcr p15, 0, Rt, c7, c10, 1`. Correct.

### Knowledge prerequisites missing
- "PL0/PL1" privilege levels are mentioned but never defined. One sentence: "Cortex-A7 has Privilege Level 0 (user mode) and Privilege Level 1 (everything else: SVC, IRQ, etc.). We are always at PL1 in this book."
- "VIPT cache" mentioned in §17.9 lab 4. "Virtually Indexed, Physically Tagged" — Cortex-A7 L1 caches are VIPT. Define on first use.

### Other
- §17.6 cache maintenance ops: `dcache_clean_range` example is good. Add: "Linux kernel calls these `__cpuc_clean_dcache_range`, `__cpuc_inv_dcache_range` etc. in `arch/arm/mm/cache-v7.S`; the names differ but the CP15 ops are the same."
- §17.9 lab 4 "Construct this [aliasing] by adding a second mapping in your page table" — the lab is interesting but quite advanced for a Part II reader. Mark it `(optional/advanced)`.

## Ch18 — Optional bare-metal peripherals

### Readability
- "**Confidence that the Linux abstractions are not hiding magic. Every subsystem callback eventually pokes the registers in this chapter.**" — keep.
- "**Touching it raw, once, removes the mystery.**" — keep.
- "**This is how the rest of the book uses the bare-metal foundation: not as a thing we keep building on, but as a *mental rosetta stone* for understanding the higher layers.**" — strong closing.
- "**Annoying but unambiguous.**" (re: 1 kHz tone) — funny; keep.

### MCU-engineer friendliness
- I²C: MCU engineers know Phillips/NXP's `IC1`/`IIC` controllers and STM32's `I2C1`. State once: "The i.MX I²C peripheral is the same Philips IP that NXP ships on Kinetis and on many other parts. Same registers, same names — you may have used it under a different memory base." This frames the chapter as "you already know this."
- SPI/ECSPI: same. "ECSPI is a more flexible variant of the classic Philips SPI. CPOL/CPHA/MSB-first/CS-as-software work the same."
- The "driver shape that repeats" in §18.5 is good. Make it a numbered figure / template that the rest of the book can refer back to.

### Missing examples / figures
- I²C transaction timing: a waveform showing START / address+W / ACK / register / ACK / repeated START / address+R / ACK / data / NAK / STOP. Most i.MX engineers haven't seen the i.MX bus controller emit this; the wave makes the polled state machine click.
- ECSPI burst-length and FIFO layout — a small diagram of the 32-bit TXDATA/RXDATA being interpreted as a single 8-bit burst would help.
- §18.4 mentions cache+DMA but doesn't draw the issue. Add a tiny "cache coherency problem" figure: CPU writes to `framebuffer[]` → lines in L1 cache → physical DRAM still has old → eLCDIF reads physical DRAM → stale.

### Technical errors
- §18.3 ECSPI `CONREG` write `(1u << 4)`: per RM §21.6.3, CONREG bits [7:4] are CHANNEL_MODE[3:0] (per-channel master/slave). `1 << 4` sets CHANNEL_MODE[0]=1 → channel 0 master. Correct.
- §18.3 CONFIG register: `(1u << 0) | (1u << 12)`. Per RM §21.6.4 CONFIGREG: bit 0 = SCLK_PHA0 (CPHA for CS0); bit 12 = SS_POL[0]. Setting CPHA=1 and SS_POL=1 may not match the W25Q32 (CPOL=0/CPHA=0 mode is standard for JEDEC ID read). Verify; the comment "/* SS_CTL_0 + SS_POL_0 */" doesn't match the math (SS_CTL is at bits [11:8]; SS_POL is bits [15:12]). Likely incorrect; revisit.
- §18.2 I²C read sequence: "**The 'read I2DR' step is doubled because the first read latches the byte; the second returns it.**" Actually the i.MX I²C: clearing `IIF` after the address-ACK starts the next byte fetch (clock pulses on SCL); the next byte appears after the read. The "doubled read" is the dummy-read-to-start-clocking idiom. Worth one more sentence explaining *why* (the read of I2DR triggers the next 9 clock cycles).
- §18.2 `i2c_init`: `REG(I2C_IFDR) = 0x15`. Per RM Table 31-3 IFDR encoding, `0x15` = divider 320 → at 66 MHz IPG → 206 kHz, not 100 kHz. The comment "~100 kHz from 66 MHz" is wrong. For 100 kHz, IFDR should be ~`0x1E` (divider 640) or `0x18` (divider 480). Recompute.

### Knowledge prerequisites missing
- ELCDIF, eMMC, eSPI — the "e" prefix means "enhanced" but readers wonder. One footnote: "NXP's convention: `e<thing>` is enhanced (more FIFO, more channels) compared to the simpler base IP."
- JEDEC ID lookup: "EF 40 16" decoded as Winbond W25Q32 — explain how to look up JEDEC manufacturer codes (jedec.org / SPI Flash Programmer table).

### Other
- §18.4 LCD section is acknowledged-incomplete ("Pseudocode" + "Omitted here; panel-specific"). For a chapter where the reader is supposed to run code, this section reads as a placeholder. Either (a) provide a complete LCD bring-up for the specific Point Atom carrier panel, or (b) move LCD to "Going deeper" and remove the pseudocode skeleton.
- §18.6 transition into Part III is excellent. Keep.

## Ch18A — Project organization

### Readability
- "**Once a bare-metal project crosses ~500 lines and ~3 peripherals, the single-file layout costs more than it saves.**" — keep.
- "**It is boring. It is also the most-used file in your project for the next decade if you keep using i.MX6ULL.**" — keep.
- "**The 30-vs-10-min number is what matters.**" — keep.

### MCU-engineer friendliness
- An MCU engineer using STM32 CubeMX has seen `stm32f4xx.h` (CMSIS struct-based header) and per-peripheral driver folders (`stm32f4xx_hal_uart.c` etc.). The chapter's BSP layout is essentially a hand-written CubeMX-equivalent. Open the chapter with one sentence: "If you've used STM32CubeMX, this is the layout you got for free; here we build it deliberately, so you understand why the structure exists." This grounds the whole chapter.

### Missing examples / figures
- A "before / after" file-tree diagram. The chapter has a one-line "Chapter 16 code" then a target tree; visually compare them side-by-side.
- A "header dependency graph" — `imx6ull.h` at the bottom, `bsp_*.h` above it, `main.c` and `bsp_*.c` at the top with arrows showing includes. Helps the §18A.9 "header layering" warning click.

### Technical errors
- §18A.5 Makefile uses `find . -name '*.o' -delete` in clean. Cross-platform issue: on Windows-MSYS / Cygwin / WSL this should still work; on bare Windows CMD it won't. Note the dependency on a POSIX environment (which the rest of the book already assumes).
- §18A.5 wildcard usage `$(wildcard bsp/*/*.c)` recurses one level only. If a peripheral subfolder grows nested files, the build silently skips them. Either document the one-level constraint or use `$(shell find bsp -name '*.c')`.

### Knowledge prerequisites missing
- Makefile pattern rules (`%.o: %.c`), variables, automatic vars (`$@`, `$<`). The chapter assumes these; for an MCU engineer who uses IAR's project-file-only build, a one-paragraph Make primer would help. Or reference an earlier chapter (Ch04? Ch08?) where Make basics were introduced.

### Other
- §18A.7 SDK sidebar is good. Add a one-line: "We use `REG(addr)` macros in this book to keep addresses visible. Production code on NXP parts typically uses `MCIMX6Y2.h` struct-style access."
- The chapter could end with a "checklist for refactoring an existing project" — 5 bullets — making §18A.8 lab 1 more guided.

## Ch18B — Button input and beep

### Readability
- "**Production code retries.**" (re: I²C ACK polling) — keep.
- "**Annoying but unambiguous.**" — repeat from Ch18 — different sentence here, but mind the repetition if you reuse.
- "**The explicit silencing line is not decoration.**" — keep.
- "**The right answer for production: drive BEEP from a *PWM peripheral* ... we plumb the same buzzer via the PWM framework instead of bit-banging.**" — clear forward link.
- "**Why active-low via a transistor? The buzzer draws more current than a bare GPIO can sink without risking the SoC's IO drive specs.**" — accurate for a piezo; piezos are nearly capacitive — peak inrush current can exceed GPIO drive. Keep.

### MCU-engineer friendliness
- §18B.2 "**The classical fix in 1980s firmware was a 20 ms hardware RC filter on the input.**" — good. Add: "On STM32 you may also have seen TIM2 with an external clock from the button used as a debouncer — same idea via a different mechanism."
- §18B.2 sliding-window debouncer with `key_history` is the same Ganssle pattern. Cite Ganssle inline (§18B.7 has it; promote to the body).

### Missing examples / figures
- A bouncing-switch waveform vs the sliding-window sample's view (8 ticks of 0 followed by some bouncing 0/1 then steady 1). Makes the 80 ms validation visible.
- The PNP-transistor circuit (3V3 → buzzer → C → Q1 collector; Q1 base ← GPIO via R; Q1 emitter ← GND) as a small ASCII schematic. Reader who doesn't read schematics needs help.

### Technical errors
- §18B.1: "**KEY0 — a normally-open momentary tactile switch wired between the UART1_CTS_B pad (which in ALT5 becomes GPIO1_IO18) and GND.**" Verify: in i.MX6ULL IOMUX, UART1_CTS_B has ALT5 = GPIO1_IO18 (per RM Table 32-X). Correct based on the IOMUX table.
- §18B.3: `REG(IOMUXC_SNVS_BASE + 0x00) = 5;` — the SNVS IOMUXC base is at `0x02290000` on i.MX6ULL (separate from main IOMUXC at `0x020E0000`). The chapter never defines `IOMUXC_SNVS_BASE`. Fix.
- §18B.3 GPIO5_BASE = `0x020AC000` (per Ch18A). GPIO5 *is* in the SNVS power domain on i.MX6ULL — its register addresses live in the regular AIPS-1 space but the pins are SNVS pads. Worth one sentence clarifying.
- §18B.6 pitfall "EPIT tick too fast. A 1 ms tick × 8-deep history = 8 ms" — if your `key_history` is masked to `0xFF` (8 bits), then 8 ms total at 1 ms tick. Math is right.

### Knowledge prerequisites missing
- "Passive vs active buzzer" distinction in §18B.6 pitfall — actually mentioned. But the §18B.3 prose just says "passive piezo." Add the active-vs-passive callout near the top of §18B.3, not just in pitfalls.

### Other
- §18B.4 `key_tick()` is called from the EPIT ISR. ISR running `printf`-via-poll-UART is risky if `key_tick` later calls `on_key_press` which prints. The chain works because `uart_putc` polls (no IRQ recursion), but the call depth in ISR context is non-trivial. Comment on this; it's also a teaching opportunity for §18B.5 lab 3.

## Ch18C — Bare-metal RTC

### Readability
- "**While the main SoC sleeps or browns out, SNVS keeps counting.**" — keep.
- "**This is the lab that makes SNVS feel real.**" — keep.
- "**The error is rare (~once per 2^15 reads) but real.**" — keep.
- "**The fix is in hardware.**" — keep.

### MCU-engineer friendliness
- The "separate power domain" framing (§18C.1) is excellent — MCU engineers from STM32 know the LSE/BKP-domain pattern (STM32's RTC + backup registers are in a separate VBAT-powered domain). Cite the analogy: "STM32's RTC + backup registers live in a VBAT-backed domain; i.MX's SNVS is the same idea, with the additional security-friendly features (tamper, secure secrets)."

### Missing examples / figures
- A power-domain diagram: VDD_SOC_IN (main), VDD_SNVS_IN (always-on / VBAT), with the SNVS oscillator, counter, and scratch SRAM inside the VDD_SNVS_IN island.
- The 48-bit counter layout: a strip showing bits 47:32 in `LPSRTCMR`, bits 31:0 in `LPSRTCLR`, the 32 kHz tick rate, and the "shift right by 15 = seconds" derivation.

### Technical errors
- §18C.3: "**The actual counter ticks at 32 kHz, but the architectural view splits it: bit 14 of `LPSRTCLR` increments at 2 Hz; treat upper 32 bits of the 48-bit concatenation as seconds.**" The wording is confused. The SRTC clocks at 32.768 kHz so the LSB increments at 32768 Hz (period 1/32768 s ≈ 30.5 µs). Bit 15 increments at 1 Hz (1/2 Hz pair). The "upper 32 bits of the 48-bit concatenation as seconds" works only after shifting right by 15. Re-explain cleanly: "The 47-bit counter (`LPSRTCMR[14:0]:LPSRTCLR[31:0]`) ticks at 32.768 kHz. Bits[46:15] count seconds; bits[14:0] are sub-second."
- §18C.4 `rtc_get_seconds`: `uint64_t raw = ((uint64_t)hi1 << 32) | lo;` then `return raw >> 15;`. The high register is only 15 bits wide (`LPSRTCMR[14:0]`), so shifting it << 32 places its high bit at position 46 — correct for a 47-bit counter. The chapter says "32 bits high, 32 bits low" but `LPSRTCMR` is not 32 bits of seconds; it's 15 bits of (high part of the 47-bit count). **Verify per RM §47**. The computation may be off-by-shift if `LPSRTCMR`'s low 15 bits are the high part.
- §18C.4 `rtc_set_seconds`: writing `raw = s << 15` then writing the high/low pair. Same width concern.

### Knowledge prerequisites missing
- "32.768 kHz" — why this specific frequency? Because 2^15 = 32768. Spell out the connection: "32768 Hz is chosen so that bit 15 ticks at 1 Hz, giving an integer-second sub-counter."

### Other
- §18C.5 `format_secs` has unused locals (`(void)out; (void)buf; (void)days; ...`). Cleanup before publication.
- §18C.7 lab 5 (wall-clock UNIX time) is a great exercise but pulls in `gmtime`-style date math; mention that the standard `<time.h>` is unavailable bare-metal and the reader will need to roll their own (or limit to UTC seconds → readable string).


---

# Part III — U-Boot: Review

## Cross-cutting observations

- **No "U-Boot vs. your bare-metal blob" framing chapter or opening section.** The MCU reader's biggest gap going into Part III is conceptual: *they have never used an interactive bootloader.* On MCUs, the engineer flashes a single blob and the chip runs it. U-Boot is a separate program that loads *another* program and provides a CLI in between. Ch19's "Why" sentence ("From here on the question is no longer 'can we?' but 'what does the professional version of this work look like?'") does some of this work, but it does not explicitly say: "U-Boot is a program. Linux is a separate program. U-Boot's only job is to find Linux, prepare RAM/peripherals, and call it. Then U-Boot is gone." A two-paragraph framing at the top of Ch19 (or as a brand-new §III.0 page) before §19.1 would save the reader an hour of confusion when they first see `bootcmd`, `bootargs`, and `bootm` and wonder why a bootloader has a *shell*.
- **The environment as "persistent NVRAM your CLI can edit" is never explicitly bridged.** MCU engineers may know "EEPROM-backed config blob" but not "shell variables that persist." `setenv` / `saveenv` / `printenv` show up across Ch19, Ch21, Ch23, Ch24 with the assumption that the reader already knows what an env var is in a bootloader. Add to Ch19 §19.6 (`printenv`) or as a fresh sub-section: "Concept break: U-Boot's environment is a key/value store stored in a known sector of the boot medium. Think of it as one I²C-EEPROM-backed `struct config` whose fields you can edit from a shell. `setenv` modifies the in-RAM copy; `saveenv` writes it to flash. Reboot loses anything you didn't `saveenv`."
- **`source.denx.de` vs `git.denx.de` slash naming.** Several places use `https://source.denx.de/u-boot/u-boot.git`; the canonical project URL has shifted over the years and the directive page now is `https://source.denx.de/u-boot/u-boot.git` (correct as written in Ch19) but the parenthetical "(a.k.a. `git.denx.de`)" is no longer accurate as a current alias. Either drop or rephrase as "(historically `git.denx.de`)".
- **No ASCII figure of "where is what at each boot stage."** Part III would benefit enormously from one canonical "stage chart" that the reader can flip back to from any chapter: at stage 0 (ROM) PC is in iROM, what is in OCRAM; at stage 1 (SPL) what code is at what address, what stack is where; at stage 2 (U-Boot pre-relocation); stage 3 (U-Boot post-relocation, kernel about to be loaded); stage 4 (kernel running). Ch20 §20.4 has a partial flow chart but it is verb-oriented, not address-oriented. Add an address-oriented diagram once, reuse across Ch20, Ch21, Ch24.
- **OCRAM/SPL size budget mismatch with the reference manual.** Ch20 §20.3 says "the Boot ROM's effective load window for SPL is **~100 KB** within OCRAM." The IMX6ULL reference manual (page ~260 in our extract, the ROM/RAM memory-map figure) shows OCRAM = 128 KB total, with the **free area = 68 KB** (0x00907000-0x00917FF0) — the rest is reserved for ROM stack, MMU table, log buffer, RAM exception vectors. NXP's `CONFIG_SPL_MAX_SIZE` on `mx6ull_14x14_evk` is typically set near 64 KB for exactly this reason. Either cite the 68 KB free figure directly, or rephrase as "~64 KB practical SPL budget within 128 KB OCRAM (the ROM reserves the rest for its own MMU table / stack / log buffer)". The current "~100 KB" overstates the budget by ~50 %.
- **Mainline EVK board-name string check.** Ch19 §19.5 boot log shows `Model: Freescale i.MX6 UltraLiteLite 14x14 EVK Board`. That double-"Lite" looks like a typo and a reader would assume the book made an error. In mainline U-Boot the actual board file at `board/freescale/mx6ull_14x14_evk/mx6ull_14x14_evk.c` historically uses "i.MX6 UltraLite/ULL" or "i.MX6ULL 14x14 EVK Board". If the "UltraLiteLite" string is reproduced verbatim from a real boot log, leave it but add a brief footnote ("yes, this odd double-Lite is in NXP's source verbatim — `UltraLite` + `Lite` for ULL"). If not, fix to `i.MX6 ULL 14x14 EVK Board`. Either way, the reader needs the cue.
- **Chapter cross-references use chapter numbers in a way that may be brittle.** Examples: Ch19 "Chapter 14 §14.6", Ch20 "Chapter 11 §20.1's Pattern 1", Ch21 "Chapter 14's tRP/tRAS/tRC/tWR setting", Ch22 "Chapter 14 §14.13", Ch23 "Chapter 28", Ch23A "Chapter 62", Ch24 "Chapter 3 §3.6/3.7/3.8/3.10", "Chapter 55E". This is fine if the TOC is locked, but section numbers are easy to drift. Consider a final-pass automated cross-ref check before publication.
- **The two-IMX-fork story (mainline vs. NXP `imx_v2016.03_4.1.15_2.0.0_ga`) is mentioned only in Ch19 §19.1 and is not picked up again.** A reader following a *Chinese-language guide or a vendor BSP* (e.g., Point Atom uses the 2016 NXP fork) will get confused when source paths diverge — e.g., NXP fork has `arch/arm/cpu/armv7/mx6/...` legacy layout while mainline has `arch/arm/mach-imx/mx6/`. Add a short callout near §19.1 or as a sidebar: "If a tutorial or AN you're following references a file path that doesn't exist in your tree, you're probably reading NXP-fork docs. Mainline's `mach-imx` layout was introduced in 2016+."
- **"Bare-metal" → "U-Boot mapping" cross-reference table missing.** Each chapter references "Chapter X" frequently, but a single table at the start of Part III ("Chapter 10's startup.S = U-Boot's `arch/arm/cpu/armv7/start.S`; Chapter 14's `ddr_init` = `arch/arm/mach-imx/mx6/ddr.c`; Chapter 12's UART init = `drivers/serial/serial_mxc.c`; Chapter 11's `mkimx.py` = `tools/mkimage` + `imximage` plugin") would crystallize the "U-Boot is our Part II, productized" message that the book keeps making prose-only.

## Ch19 — U-Boot from source

### Readability
- §19.3 sentence: "The first build takes 1–2 minutes on a modern host. A few interesting moments scroll past:" — "A few interesting moments scroll past" is awkward and slightly poetic. Suggest: "Watch for these lines as the build scrolls past:". The same goes for §19.5 "Pause. Read the boot log a third time. Notice:" — fine for English speakers but the imperative repetition feels off. Suggest: "Re-read the boot log a third time, paying attention to each of these lines:".
- §19.1 last sentence reads: "The boards are close enough that the EVK config boots on the MINI with only minor DT changes for IOMUX and DDR timings." DDR timing changes are *not* minor on hardware that differs (different DRAM chip, different trace lengths, different number of chips). The whole point of Ch22 §22.6 is "this part you cannot fake." Either soften to "...with EVK config as a starting point — DDR timings need fresh stress-tool values for the MINI; IOMUX needs per-pad updates," or move the qualifier here.
- §19.3 table: `MLO` row says "Symbolic link / copy of the SPL image used by some SoCs (TI / OMAP heritage)". On i.MX6ULL this is irrelevant. Either remove the row, or add: "(not used on i.MX6ULL — ignore)" to spare the reader looking it up.

### MCU-engineer friendliness
- §19.2 directory layout: the comment `cmd/  # one .c per U-Boot command` is the first hint that U-Boot *has* commands. The reader doesn't know yet what "U-Boot commands" means. Add a parenthetical: "(`cmd/md.c` is the `md` 'memory display' command you'll type at the `=>` prompt in §19.6.)" — pre-bridges the discovery in §19.6.
- §19.5 — first sight of the `=>` prompt. This is *the* moment the MCU reader meets an interactive bootloader. Add a paragraph immediately after the boot-log block: "If you've only ever worked with MCUs, this is the new concept of Part III. The chip is *not* yet running Linux. It is running a small program (U-Boot) that gives you a shell, a memory editor, drivers for SD/USB/Ethernet, and the ability to load and start another program (Linux). For the next four chapters we'll live at this prompt."
- §19.4 SD-card flash table: the reader who hand-flashed in Part II knows the IVT offset. But they don't know why SPL goes to LBA 2 (1 KiB offset) *and* U-Boot goes to LBA 138 (69 KiB offset). One sentence: "The 1 KiB offset is what the ROM expects (Ch 7). The 69 KiB offset is where SPL is *configured* to look for its second-stage image — a U-Boot Kconfig choice (`CONFIG_SYS_MMCSD_RAW_MODE_U_BOOT_SECTOR`), not a hardware constraint." This makes the magic numbers stop being magic.
- §19.6 `printenv`: the sample output has `bootcmd=run findfdt; mmc dev ${mmcdev}; mmc rescan; ...` — that `...` is doing a lot of work. The MCU reader has no analog for a shell-script-stored-in-a-variable. Add a one-line annotation: "`${mmcdev}` is variable substitution like Bash. `run findfdt` evaluates the variable `findfdt` as a sequence of commands. Chapter 23 covers this DSL in detail."
- §19.6 `bdinfo`: `relocaddr = 0x9ff37000` and "U-Boot started executing somewhere lower in DRAM, then *relocated itself* to high DRAM" — relocation is a deep concept and Ch21 covers it, but the *first* mention here for an MCU reader who has only ever written XIP-from-flash MCU code is jarring. One extra sentence: "MCU engineers: think of this as the equivalent of `memcpy(0x9ff37000, 0x80800000, image_size); jmp 0x9ff37000;` — but with the linker's pointer fix-ups also adjusted by the offset. Trust this for now; Ch21 explains."

### Missing examples / figures
- After §19.5 add an ASCII diagram showing: ROM → reads SPL from SD LBA 2 → SPL in OCRAM @ 0x907400 → SPL DDR init → SPL reads u-boot.imx from SD LBA 138 → u-boot.bin in DRAM @ 0x87800000 → SPL jumps to it → U-Boot relocates to high DRAM (~0x9ff37000) → `=>` prompt. This is the canonical "Part III mental model" diagram and the reader will refer back to it from Ch20 and Ch21.
- §19.6 `bdinfo`: include an annotated diagram of the DRAM map at the moment of `=>`: low DRAM unused (0x80000000-?), reloc target (0x9ff37000) U-Boot code, stack growing down from somewhere above, env load buffer somewhere, fdt blob @ 0x9ed3d2c0. The numbers are all in the bdinfo output — link them visually.

### Technical errors
- §19.3 table: `MLO` description is TI/OMAP. On i.MX6ULL `MLO` is unused and the file may not even exist for the EVK defconfig. Drop or qualify.
- §19.4 says `bs=1k seek=1` writes at LBA 2 — correct, since LBA 2 = byte offset 1024. But the offset table above it says `1 (= LBA 2)` and labels the column "Offset (KiB)" — a reader could read "offset 1 KiB = LBA 2" as a contradiction with "LBA 2 = byte 1024 = 1 KiB". Clarify or just say "byte offset 0x400".
- §19.4 the offset `8192` "Reserved for partitions" — actually `8192 KiB = 8 MiB` and the EVK convention is partitions start at `8 MiB` (= LBA 16384, sector 512). Spell out "8192 KiB = 8 MiB" so the reader doesn't read it as sectors.
- §19.5 boot log: "CPU: i.MX6ULL rev1.1 at 396 MHz" — the EVK config does run at 396 MHz initially (from the ROM's default PLL1 setting, see RM Table 8-4). But later it ramps to 528 or 696 MHz under Linux. State this once so the reader doesn't conclude "U-Boot caps the EVK at 396 MHz."
- §19.5 "DRAM: 512 MiB — SPL's DDR setup worked. The same 100-line MMDC dance as our Chapter 14". The mainline `arch/arm/mach-imx/mx6/ddr.c` is closer to 1500 lines, not 100, and even the board-specific spl.c is several hundred. The "100-line" claim under-sells the production code by an order of magnitude. The chapter already does this better in §19.7 ("~600 lines"). Make §19.5 say "the productized MMDC bring-up you wrote 100 lines of in Ch 14; in U-Boot it's a 600-line table-driven engine."

### Knowledge prerequisites missing
- §19.3 references `make distclean` for the first time in Pitfalls but uses `make mx6ull_14x14_evk_defconfig` without explaining that it generates a `.config` file. An MCU engineer using Make may not know the Linux-kernel-Kconfig convention. One sentence: "`make foo_defconfig` reads `configs/foo_defconfig` and writes the resulting `.config` (a Kconfig artefact) to the build root. `make` then reads `.config` and the per-CONFIG `Makefile`s to decide what to build."
- §19.6 mentions `bootz` only via the prose "bootcmd ... tries to find a kernel and chain-boot Linux." But the actual command `bootz` is introduced cleanly only in Ch23. A forward-reference link would help: "(`bootz` is the kernel-launch command; we cover it in Ch 23.)"
- §19.7 — `arch/arm/include/asm/arch-mx6/...` paths and the macro `MX6_PAD_*` are referenced but the cross-tree DT-vs-source-header file structure is not yet introduced. Forward-reference Ch22 explicitly.

### Other
- §19.10 "Going deeper" lists `https://docs.u-boot.org/` — the actual URL is `https://docs.u-boot.org/en/latest/` for the modern Sphinx-built docs site. Minor but worth correcting.
- The "DENX's Bootloader_with_U-Boot article series (free)" reference is vague; the canonical thing is "U-Boot manual" on docs.u-boot.org. Consider replacing.

## Ch20 — U-Boot SPL: the missing link

### Readability
- §20.1 "Pattern 3 ... Has been done. Painful." — fragments. Either expand ("This pattern was used historically — strip features until the binary fits in 100 KB OCRAM. It works but the resulting U-Boot is too feature-thin for any real product."), or accept as deliberate. Currently feels half-finished.
- §20.8 has a confused, self-correcting passage: `"Hmm. Let me re-check. The entry for an SPL is *inside OCRAM*, not DRAM..."` and later `"...wait no, that's not right either, because SPL is what initializes DDR. The answer is subtle and worth pinning..."`. **This reads as if the author was reasoning live in the chapter and didn't clean up.** For a book aimed at a non-native English MCU engineer, this is highly confusing — the reader can't tell which statement is correct. Rewrite §20.8 as a single clean explanation: (1) SPL's `.imx` may or may not have a DCD; (2) if present, the DCD does pad/clock setup needed *before SPL's C code runs* — but **not** DDR init; (3) DDR init is SPL's C code's job; (4) compare to the EVK's `.cfg` file. Remove all the "wait" / "hmm" / "actually" hedging.
- §20.9 "Full U-Boot's `_main` then proceeds with *its* `board_init_f` → relocation → `board_init_r` → main loop." — Bare-minimum sentence but missing a connective. "We trace this in Chapter 21." → consider expanding to: "The full-U-Boot init flow runs `board_init_f`, relocates to high DRAM, then `board_init_r`, then the main loop. Chapter 21 walks each step."

### MCU-engineer friendliness
- §20.1 "Three possible solutions" is great for an engineer who already knows the constraint. But it dives into Pattern 1/2/3 before reminding the reader *why* the constraint exists. One sentence at the very top: "The i.MX6ULL Boot ROM, when loading from SD/eMMC, reads at most 4 KiB initially (see Ch 7's IVT-Initial-Load-Region) and ultimately loads what fits into OCRAM (~68 KB free). Full U-Boot doesn't fit. SPL exists to bridge that gap."
- §20.2 "What SPL is responsible for" — the seven-step list is excellent, but the closing paragraph ("SPL is the smallest program that can do exactly the seven things above on this hardware") should be picked up *visually* as a hand-off contract diagram: SPL's exit conditions = the world full U-Boot expects to inherit. Otherwise the seven items feel like a list and not a contract.
- §20.6 "The 'f' stands for 'flash' (historical — back when U-Boot ran first from flash...)". MCU engineer reads "U-Boot ran first from flash" and thinks "wait, you said it doesn't fit in OCRAM, so how did it run from flash directly?" — the answer is that this is *legacy CPU-NOR-flash XIP era*, distinct from our SD-boot-into-DRAM flow. Add one clarifying sentence: "Historically (i.MX1/2/3 era), the bootloader was small enough to execute in place (XIP) from parallel NOR flash. The `_f` / `_r` distinction is a vestige of that."

### Missing examples / figures
- Add to §20.3 a real `size spl/u-boot-spl` output annotated with what fits where in OCRAM. Currently the budget is abstract; an image of "39204 bytes text + 1872 data + 8112 bss = 49188 bytes, free OCRAM after SPL = 68KB - 49KB = ~19KB headroom" would crystallize the constraint.
- §20.4 has a great ASCII flow but no *address* annotations. Add: "SPL @ 0x00907400, stack @ ~0x0091FE00, gd_t @ ~0x0091FE08, U-Boot loaded to DRAM @ 0x87800000" — same skeleton as the Ch21 §21.2 SP-arithmetic walk, but for SPL.
- §20.7 — when `_main` is shown, it includes `ldr sp, =(CONFIG_SYS_INIT_SP_ADDR)` but does not show what that value is *in SPL*. For SPL on i.MX6ULL EVK this is also near the top of OCRAM. Add a one-line annotation.

### Technical errors
- §20.3 "the Boot ROM's effective load window for SPL is ~100 KB within OCRAM" — see cross-cutting note; per RM the free area is 68 KB. Fix.
- §20.4 ASCII diagram says "loads SPL (~40 KB) into OCRAM @ 0x00907400". 0x907400 is correct for typical EVK; pinpoint it correctly. But the diagram also implies the ROM does the load *after* IVT parsing — it does, and the load address is what the IVT `self` field declares (see Ch 11 §11.x), not a hard-coded ROM constant. State this.
- §20.4 — `arch/arm/cpu/armv7/start.S` is shared between SPL and full U-Boot; `lowlevel_init.S` is **not** at `arch/arm/cpu/armv7/lowlevel_init.S` in modern mainline (varies by SoC; on i.MX it's in `arch/arm/mach-imx/`). Double-check paths.
- §20.5 `cpu_init_crit` description "very-early board-critical init (memory remapping, system control register tweaks)" — on ARMv7 `cpu_init_crit` mostly invalidates caches and TLBs and sets up the SCTLR; it doesn't do "memory remapping" in any general sense. Tighten.
- §20.6 The pseudo-`board_init_f` is shown as 5 explicit calls (`arch_cpu_init`, `timer_init`, `preloader_console_init`, `spl_dram_init`, `memset`...). In reality SPL's `board_init_f` may directly include this sequence on i.MX, but the *generic* SPL framework uses `spl_board_init_f` or the init-sequence pattern from `common/spl/spl.c`. Make clear this is the i.MX SPL flavor, not the generic SPL framework's flow.
- §20.7 mentions `spl_load_image(BOOT_DEVICE_MMC1, &spl_image)` — modern SPL has the framework call `spl_load_image_method` and choose the loader from a list. The simplified pseudocode is fine but could note: "Reality is `spl_load_image` runs a list of registered `spl_image_loader` methods, this is a simplification."
- §20.7 "spl_mmc_load_image → reads `u-boot.imx` from SD card LBA 138 (= seek=69 in 1 KB blocks)". 69 KiB / 0.5 KiB-per-LBA = 138 LBAs from start — correct, but worth stating once: 1 LBA = 512 bytes, so 69 KiB = 138 LBAs.

### Knowledge prerequisites missing
- §20.4 introduces `board_init_f` / `board_init_r` for the first time without defining the `f`/`r` convention. §20.6 then defines it. Reorder so the definition comes before first use, or define at first use.
- §20.7 introduces `gd_t` (struct global_data) without explanation. Define it once with: "`gd_t` is U-Boot's per-CPU 'global data' — a single struct holding pre-relocation state, DRAM detection results, console pointers, env state, etc. It's allocated on the stack early and pointed to by a fixed register (r9 on ARM) so any code can reach it without passing pointers around."
- §20.8 references `mx6ull_14x14_evk.cfg` (a `.cfg` file). MCU readers won't know that NXP's U-Boot uses `.cfg` files to feed `mkimage` for IVT/DCD generation. Brief explanation: "the `.cfg` file is a small text file specifying IVT entry, DCD entries, etc. `mkimage`'s `imximage` plugin reads it. The same logic as your Ch 11 `mkimx.py`'s args."

### Other
- §20.11 Pitfall "Out-of-bounds OCRAM access. SPL has ~100 KB of OCRAM" — same 100KB error.
- §20.11 Pitfall "Calling SPL functions from full U-Boot. They don't exist there — different binary, different memory map." — this is a very real trap for a beginner. Add an example: "If you write `spl_load_image()` in your full-U-Boot code, the build fails because that symbol is gated by `#ifdef CONFIG_SPL_BUILD`."

## Ch21 — U-Boot internals

### Readability
- §21.1 — the 9-step list is excellent. But each step lacks a one-line "what to grep for". Add: "1. `_start` (file: `arch/arm/cpu/armv7/start.S`, ~50 lines)". Most steps already have file refs; complete them all consistently and add LOC estimates so the reader knows what they're committing to.
- §21.1a — "the linker script `u-boot.lds` (generated at the top of the source tree only **after** a successful build — pre-build there's only the unprocessed `arch/arm/cpu/u-boot.lds`)" — the parenthetical is too dense. Split: "The linker script `u-boot.lds` is generated during build from the per-arch template `arch/arm/cpu/u-boot.lds`. Until you've built once, only the template exists at the source root."
- §21.3 lists the `init_sequence_f` array. The closing line "After `board_init_f` returns, control falls back into `_main`" is followed by ASM. The transition between "here's the C list" and "now here's the ASM after the return" needs a connective sentence: "Control returns to `_main` after the C list executes. The ASM that runs next is the relocation handshake — every line below is critical."
- §21.4 — "This is the most surprising design choice in U-Boot for a newcomer." Good hook, but the explanation jumps between abstract ("Why relocate at all") and concrete ("How relocation works mechanically") quickly. Add a clearer transition: "With *why* clear, here's *how* in three steps."
- §21.4 "The post-copy `bx lr` is the **single most important instruction** in this entire chapter." Excellent line — keep it. Consider boxing it as a callout.

### MCU-engineer friendliness
- §21.2 SP-arithmetic walk is one of the strongest passages in the part. **Keep it as is**, and consider doing similar walks for one or two other "what address holds what" moments (e.g., `relocaddr` calculation, env-load-buffer placement).
- §21.4 — when introducing position-independent code, an MCU engineer who hasn't dealt with PIC will not have the mental model. Add one paragraph: "Position-independent code is compiled so all internal jumps and data references are *relative* to the program counter, not absolute. The cost is a few extra instructions per non-local reference. The benefit is that the same binary works at any load address. U-Boot uses `-fpic` to get this, and `.rel.dyn` to track which absolute references remain (string literals, function pointers in tables, etc.) so relocation can patch them."
- §21.5 — the `cmd_tbl_t` linker-section trick. MCU readers know `__attribute__((section))` for ISR vector tables in MCU startup code. Make the analogy explicit: "If you've ever placed an ISR vector or initcall via `__attribute__((section(".isr_vector")))` and let the linker assemble all entries into a contiguous range, this is the same trick. U-Boot's `cmd/Makefile` doesn't need a central registry; each `.c` file self-registers via the section attribute."
- §21.6 — the env subsystem. The "Where it lives" passage is good. The MCU equivalent: "If you've ever stored config in a chip-internal EEPROM or a reserved flash sector with a CRC and a magic word, U-Boot's env is the same idea, but with a userspace API (`fw_setenv`) and a shell."
- §21.7 (Driver Model) — "Conceptually identical to Linux's `struct device` + `struct driver`, but much smaller." Good. Now add: "If you've used HAL APIs on STM32 (HAL_UART_Init etc.), DM is the same idea but with a runtime registry of (device, driver) pairs instead of a static `huart1` global. The DT tells DM what devices exist; DM walks the device list and binds each to a matching driver."

### Missing examples / figures
- §21.4 — add a 4-quadrant before/after memory layout diagram for relocation: LEFT = "U-Boot at load addr 0x80800000 in low DRAM, stack in OCRAM" → RIGHT = "U-Boot at 0x9ff37000 in high DRAM, stack in high DRAM, low DRAM free for kernel/DTB". Even a 6-line ASCII box would lock the concept.
- §21.5 — add the actual disassembly of `find_cmd` (10 lines) so the reader sees the section-walk pattern in code. Currently we describe it but never show it.
- §21.6 — show a real `fw_printenv` invocation from Linux user-space with annotated output. Currently the Linux-side env access is mentioned in one paragraph but never demonstrated.
- §21.7 — add a `dm tree` output sample with a 5-line tree. Lab item 7 asks the reader to run `dm tree` but doesn't preview what they'll see.
- §21.8 boot-log walk: this is the best section in the chapter. Consider adding the *file path* for each subsystem-init call so the reader can grep directly: `MMC: ...` ← `drivers/mmc/mmc.c:mmc_init` (etc.).

### Technical errors
- §21.1a table: `relocaddr = 0x9ff37000` in Ch19's `bdinfo` matches "near the top of 512 MiB DRAM" — 0x80000000 + 512 MiB = 0xa0000000, so 0x9ff37000 is 0xc9000 (812 KiB) below the top. Sanity-check that the linker script's `__bss_end = 0x878A8E74` is *pre-relocation*, not the final runtime location — these are the linker's view, not the post-reloc view. The text says "Sample value" and "for our ... build" — make explicit that these are the *linked* addresses, which the relocation engine then offsets by `reloc_off`.
- §21.2 ASCII memory map: shows `0x0091FFFF` as "top of OCRAM (128 KB)". But OCRAM ends at `0x0091FFFF` only if base is `0x00900000` and size is `0x20000` = 128 KiB. The arithmetic is fine, but `0x00900000 + 0x20000 - 1 = 0x0091FFFF`, OK. Then the ASM says SP = 0x0091FF00, leaving 256 bytes above SP — confirm this aligns with `GENERATED_GBL_DATA_SIZE = 256`. The text says GD_SIZE = 248 but reserves 256. Clarify: "256 = round-up of 248 to 16-byte alignment".
- §21.3 — `setup_spl_handoff` exists in the init sequence list. This is only relevant for boards using the SPL→U-Boot handoff data passing (added in 2019). Not all i.MX boards use it. Either qualify or note "may or may not appear depending on CONFIG_SPL_HANDOFF".
- §21.4 — `relocate_code` snippet shows `ldmia r1!, {r10-r11}` / `stmia r0!, {r10-r11}`. That's a 2-register copy loop (8 bytes per iteration). Modern mainline uses `ldmia r1!, {r10-r11}` exactly, so this is correct. But the relocation fix-up loop uses different register conventions; double-check `r0/r1/r2/r3/r4/r6` assignments against the current `arch/arm/lib/relocate.S` rather than older versions.
- §21.4 "U-Boot was built linked for an address of approximately `0x80800000`" — actually the EVK's `CONFIG_SYS_TEXT_BASE = 0x87800000` (per Ch22 §22.4's defconfig). The text in Ch21 §21.1a also uses `0x87800000`. Fix §21.4 to be consistent.
- §21.6 "stored on the boot medium — for our SD-card workflow, in a fixed-offset sector of the SD card (`CONFIG_ENV_OFFSET`, often 0x100000 = 1 MiB)". On the mainline `mx6ull_14x14_evk_defconfig` the env offset is actually a different value (often `0xC0000` = 768 KiB or `0x100000` depending on version). Verify with `grep CONFIG_ENV_OFFSET configs/mx6ull_14x14_evk_defconfig`.

### Knowledge prerequisites missing
- §21.3 references `init_fnc_t` typedef without defining it. One line: "`typedef int (*init_fnc_t)(void)` — a function returning 0 on success, non-zero on fatal init failure."
- §21.5 references `cmd_tbl_t` but the actual modern name in mainline is `struct cmd_tbl`. Either explain the `_t` suffix is historical / shorthand, or update to current naming.
- §21.7 — `dm_serial_ops`, `udevice`, `uclass_get`, `device_probe` are all introduced in code but never defined as types. Add a quick "DM types you'll see" box: `struct udevice` (instance), `struct driver` (code), `struct uclass` (category), `struct udevice_id` (DT compat match table).
- §21.7 — `compatible = "fsl,my-uart"` syntax. The reader hasn't yet seen DT compatibility strings (Part IV introduces DT). Forward-reference: "DT compatible strings come up in detail in Ch 27; for now just know that a string in DT lets DM match a device to a driver."

### Other
- §21.5 — the `U_BOOT_CMD` macro expansion is shown but the field meanings are not all explained: `md, 3, 1, do_mem_md, ...` — what does the `3` mean? (max argc). What does the `1` mean? (repeatable on Enter). Add a comment line.
- §21.9 Lab item 4: `arm-linux-gnueabihf-readelf -r u-boot | head -30` — fine. But add expected output: "you should see hundreds of R_ARM_RELATIVE entries, each one a pointer in U-Boot's image that gets fixed up at relocation."
- §21.10 Pitfall "Two `U_BOOT_CMD` macros with the same name. Last-defined wins, silently." — actually with the linker-section approach, *both* are present and the lookup order depends on link order. Could be "first wins" or "last wins" depending on linker behavior; either way it's surprising. Verify and reword.

## Ch22 — Porting U-Boot to a custom board

### Readability
- §22.1 "Three categories of port" — the third bullet ("**Real port** ... New defconfig + new DT + new DDR config + new board.c. The Point Atom MINI vs the NXP EVK is approximately this. Closer to variant but with DDR and pinmux changes.") is contradictory — first says "real port", then "closer to variant". Pick one description and stick with it.
- §22.7 — "The macros `MX6_PAD_UART1_TX_DATA__UART1_DCE_TX` etc. are generated from the i.MX6ULL IOMUX tables; they encode pad, mux mode, and SELECT_INPUT in one constant." Good. Then "See `arch/arm/include/asm/arch-mx6/mx6ul_pins.h`." — note the i.MX6ULL pin header is sometimes split between `mx6ul_pins.h` and `mx6ull_pins.h`; double-check which mainline uses in 2025.

### MCU-engineer friendliness
- §22.2 "the per-board content lives in:" — the layout is fine. Add a sentence noting which of these files exist on the MCU bare-metal side (none): "Compare to your Ch11 setup where you had a single `board.c` and a `Makefile`. In U-Boot, the same conceptual 'board' is split across six locations: build config (`defconfig`), source tree (`include/configs/`), board folder (with Kconfig + sources), DT, and a per-arch DT-Makefile entry. The split is mostly to play well with mainline's build system."
- §22.3 — `git mv mx6ull_14x14_evk.c mx6ull_pa_mini.c` while files are in a *copied* (not added) directory. `git mv` on uncommitted files is `mv + git add` effectively, but the reader may be confused. Add: "These files are not in git yet; `git mv` here is equivalent to `mv + git add`. If you've staged the copy first, `git mv` preserves history."
- §22.6 "This is the part you cannot fake." — Excellent emphasis. Keep.
- §22.7 — for an MCU engineer who has done IOMUX register-by-register, the U-Boot abstraction `imx_iomux_v3_setup_multiple_pads(array, ARRAY_SIZE(array))` is just a thin wrapper around writing the same registers. Explicitly say so: "Compare to Ch11 §X where you wrote IOMUXC_SW_MUX_CTL_PAD_xxx directly. U-Boot's helper just writes the same registers from a table; the macros pre-compute the register address + value pair from the pad name."

### Missing examples / figures
- §22.3 — add a "before vs after" tree-diff after the `cp -r` and `git mv` commands so the reader can verify their working tree matches.
- §22.5 — the DT snippet is good but the reader has not yet seen DT in Part IV. Add a one-line note: "If `&fec1`, `pinctrl-0`, `phy-handle` syntax is unfamiliar, skim Ch 27 first. For now, treat it as 'JSON-ish hardware description'."
- §22.6 — the three structs are introduced but `mx6_dram_cfg(&ddr_sysinfo, &mx6_mmdc_calib, &mt41k128m16jt_125)` at the bottom uses *different argument order* than the EVK's `mx6_ddr3_cfg(&sysinfo, &mx6_mmcd_calib, &mt41k128m16jt_125)` in Ch19 §19.7. Make sure the function name is consistent (`mx6_dram_cfg` vs `mx6_ddr3_cfg`). In modern mainline it's `mx6_dram_cfg`.
- §22.9 Verify per-peripheral: add an explicit "if the MAC PHY doesn't link, here's what to check" sub-troubleshooting list. Currently only `ping` failure is noted at high level.

### Technical errors
- §22.3 — `board/myorg/mx6ull_pa_mini/` — mainline U-Boot does not have a `board/myorg/` directory; you're creating one. State explicitly: "We're inventing a new vendor namespace `myorg`. You'll also need to create `board/myorg/Kconfig`." That bit is in §22.3 but the chronology is "make Kconfig if it doesn't exist" — clarify it definitely doesn't exist if you're forking your own.
- §22.3 — `source "board/myorg/mx6ull_pa_mini/Kconfig"` from `board/myorg/Kconfig` — that's fine, but you also need `board/myorg/Kconfig` to be `source`d from `arch/arm/mach-imx/mx6/Kconfig` or similar. The chapter says "in `arch/arm/mach-imx/mx6/Kconfig`, add ..." — but doesn't explicitly say to *also* source the new myorg/Kconfig from there. Check this; the reader will hit a build error if missed.
- §22.4 — `CONFIG_SYS_PROMPT="=> "` → `"pa-mini=> "`. In modern U-Boot, `CONFIG_SYS_PROMPT` may be a Kconfig string rather than a `defconfig` literal; check whether `=` syntax works directly.
- §22.5 — `pwms = <&pwm0 0 50000>;` — i.MX6ULL has 4 PWM controllers numbered `pwm1`-`pwm4`, not `pwm0`. Check DT label.
- §22.6 — `static struct mx6_ddr3_cfg mt41k128m16jt_125 = { ... .density = 2, /* Gb */ ...}` for an MT41K128M16 part. MT41K128M16 is 2 Gb (128 M × 16). Correct. But `.trcd = 1310, .trcmin = 4875, .trasmin = 3500` — these are timing values in units that vary. The U-Boot ddr.h convention is typically in tenths of nanoseconds; double-check the units (1310 = 13.10 ns tRCD-on?). The reader will copy these blindly without that knowledge.
- §22.6 — `.refsel = 1, /* refresh = 32 kHz / 64 */` — `refsel = 1` selects 32 kHz / something; the comment "32 kHz / 64" needs verification against the MMDC register doc.
- §22.10 — `MAINTAINERS` block uses tabs (M:\t, S:\t, F:\t). Make sure the rendered code block preserves tabs vs spaces; this is checked by `scripts/get_maintainer.pl`.

### Knowledge prerequisites missing
- §22.5 — DT syntax (`compatible`, `#address-cells`, `phandle`, `&label`) is used throughout but DT is not introduced until Ch 27. Add a forward-reference paragraph at the top of §22.5: "We use device-tree syntax extensively below. If unfamiliar, this is a good moment to skim Ch 27 §27.1-§27.3, then come back. For now: `compatible` is what DM/Linux uses to match driver↔device; `&label` is a phandle reference."
- §22.6 — the *DDR Stress Tool* (Ch14 §14.13) is referenced but the reader may have skipped or forgotten Ch14's stress-tool section. Add a 2-line reminder: "NXP's `mx6ull_ddr_stress_tester` is a Windows app that drives the i.MX6ULL via UART/USB while you tweak MMDC parameters live. It produces the six calibration values you copy into `mx6_mmdc_calib`. See Ch14 §14.13 for setup."

### Other
- §22.10 — for non-mainline-submission cases, the MAINTAINERS file is optional. State this: "If you're shipping an internal-only port, skip this; the file is only required for upstream submission."
- §22.11 Lab item 5 "Pick something the EVK doesn't have — for instance, the BEEP GPIO toggling once on boot from `board_late_init`." Good idea, but `board_late_init` selection (`select BOARD_LATE_INIT`) is in §22.3's Kconfig and `BOARD_LATE_INIT` itself is not explained. One line: "`BOARD_LATE_INIT` Kconfig enables U-Boot to call your `board_late_init()` after the main DM init — it's the standard hook for board-specific env tweaks or hardware initialization that needs full DM up."

## Ch23 — bootcmd, bootargs, FIT images

### Readability
- §23.1 — first sentence "`bootcmd` is one environment variable whose value is treated as a sequence of U-Boot commands, evaluated automatically after `CONFIG_BOOTDELAY` seconds if no key is pressed." Excellent. Keep verbatim — clean and complete.
- §23.1 "EVK's default `bootcmd` (cleaned up)" — the multi-line bootcmd is wrapped for readability but the chapter doesn't say so. Add: "In the real env this is one logical line (`;`-separated). I've line-wrapped here for reading."
- §23.5 "Why FIT" bullet list is good. The "Signed boot" bullet says "U-Boot's HAB- or FIT-signature-verifying boot path is what `bootm` invokes for `-c` (signed configs)." But Ch23 has not introduced `-c` syntax. Either show the `bootm <addr>#<config>` and `bootm <addr> -c <config>` syntax once, or drop the `-c` reference.
- §23.7 — table column "Likely cause" works well. Consider adding a 4th column "Where to look in dmesg" for each row.

### MCU-engineer friendliness
- §23.1 — first encounter with the embedded DSL idea ("run findfdt; if; then ...; else ...; fi"). Add a "Concept break" callout: "U-Boot has its own mini-shell language: variables, command substitution (`${var}`), `;`-chained commands, `if`/`else`/`fi`, `run var`. It's a Bash subset, optimized for embedded boot logic. Most env entries are 'one liners' in this DSL."
- §23.2 — `bootargs` is *the* kernel command line. Excellent emphasis. Now add the MCU-engineer-friendly framing: "On an MCU you compile-time configure your firmware via macros. On Linux, the kernel is generic — the cmdline tells it at boot what role to play. Same kernel, different cmdline → different system. `bootargs` is the chief lever."
- §23.3 table — `bootm` / `bootz` / `booti`. For our board, `bootz`. Make this explicit: "**For everything in this book on i.MX6ULL, use `bootz`.** `bootm` and `booti` are documented here for completeness."
- §23.5 — FIT vs uImage vs zImage distinction. The MCU engineer's mental model is "a flash image is a flat binary blob". FIT — a structured container — is a new concept. Add: "FIT is to flash images what `zip` is to a folder. Multiple files, optional compression, optional signatures, a manifest. The 'manifest' (the FIT header) tells U-Boot where each file lives within the FIT."
- §23.5 — `data = /incbin/("./zImage");` syntax is FDT/DTS-specific. Reader who hasn't done DT-yet won't know this. Add: "`/incbin/` is a DTS directive that includes the *binary contents* of a file. The `mkimage -f` driver compiles the .its (DTS-like source) → .itb (binary FIT)."

### Missing examples / figures
- §23.1 — add a real `printenv bootcmd` from the EVK on first boot, *unwrapped*, then show the same with line-wrapping for the chapter. This gives the reader the "this is really one line" mental model.
- §23.2 — add an annotated diagram of: "Where does `bootargs` flow?" Showing: env → `bootcmd` runs → kernel image loaded → `bootm`/`bootz` writes `bootargs` into DT `chosen.bootargs` → kernel reads it during `start_kernel()`. The arrow from env to DT is the key insight.
- §23.5 — add a `mkimage -l boot.itb` output showing the FIT's structure (hashes, sizes, configurations). This is the "look inside the box" demo.
- §23.7 — add a real "boot hangs at 'Uncompressing Linux...'" UART log sample so the reader recognizes the pattern when they see it.

### Technical errors
- §23.3 table: "`bootm` ... 'U-Boot image' (legacy uImage)" — `bootm` also handles FIT images (so it's not just legacy uImage). Add: "`bootm` handles both legacy uImage *and* FIT (.itb) images — the format is auto-detected from the header."
- §23.3 — `bootz <addr> [<initrd>] [<fdt>]` — the addr is the *zImage* address. Some readers will pass the kernel.bin address instead. Clarify.
- §23.5 — the .its example uses `compression = "none";` for the kernel but `zImage` is *already self-decompressing* (the `z` in zImage). Note this: "`zImage` is self-extracting, so we tell FIT `compression=none` even though the kernel content is compressed. If you instead use `Image` (raw kernel) you'd specify `compression=gzip` and pre-gzip the file."
- §23.5 — `load = <0x82000000>; entry = <0x82000000>;` — for zImage these can be the same. But for an Image (arm64) they differ. Note the constraint.
- §23.5 — `arch = "arm";` for kernel/ramdisk — correct. But `os = "linux";` is missing on the `fdt-1` block. Inconsistent — `flat_dt` doesn't need `os`, but the absence may confuse the reader. Add a one-line comment.
- §23.5 — `mkimage -f boot.its boot.itb` doesn't always pick the right output type; modern usage is `mkimage -f boot.its -E boot.itb` for external data, or just `mkimage -f boot.its boot.itb` for embedded. Verify your default flow.
- §23.6 — `setenv bootargs ${bootargs} earlycon ignore_loglevel` — note this *appends* to the existing bootargs in place. Some U-Boots do not expand `${bootargs}` when reassigning to itself; double-check syntax.

### Knowledge prerequisites missing
- §23.2 — `KEY_HOME` and other Linux input codes from `linux,code = <KEY_HOME>` (introduced in Ch22 §22.5's DT) are *Linux kernel* constants, not visible to U-Boot. The DT processed by U-Boot is *passed* to the kernel for those nodes. Worth noting that U-Boot doesn't act on `gpio-keys` nodes — they're for Linux.
- §23.2 `console=ttymxc0,115200` — `ttymxc0` is the Linux tty name for `uart1` on i.MX6. The Linux-side mapping is `imx_uart_dev[0]` → `ttymxc0`. State this: "Linux names i.MX6 UARTs as `ttymxc0`, `ttymxc1`, ... corresponding to the i.MX UART instance number minus one (`UART1` → `ttymxc0`)."
- §23.2 `earlycon=ec_imx6q,0x02020000` — `ec_imx6q` is a Linux earlycon driver name. Reader has not seen earlycon yet. Brief note: "earlycon is Linux's very-earliest console driver, before the full UART subsystem comes up. The 'ec_imx6q' parser knows the i.MX6 UART register layout; the address is UART1's MMIO base (Ch12)."
- §23.4 `mkimage -A arm -O linux -T script -C none -d boot.cmd boot.scr` — `-T script` is a specific image type. Reader hasn't seen the `-T` taxonomy. List `kernel`, `ramdisk`, `script`, `flat_dt` as the common values.

### Other
- §23.8 Lab item 6: "Break it on purpose. Pass `root=/dev/nonsense` and watch the panic." — good. But the recovery instruction says "Then add `init=/bin/sh` and recover." — `init=/bin/sh` won't help if `/dev/nonsense` makes root un-mountable; the kernel won't reach the init step. Reword: "When the kernel panics on root, your only recovery is to re-edit `bootargs` in U-Boot and retry. Practice doing this."

## Ch23A — Multi-variant FIT images and DT overlays

### Readability
- §23A.4 Pattern B EEPROM code: `i2c_read(0x50, 0xFF, 1, &id, 1)` — legacy i2c API. The fourth arg is the buffer, fifth is length. Reading 1 byte from address `0xFF` of chip 0x50. The reader will not know U-Boot's `i2c_read()` signature; add a comment annotating each arg.
- §23A.5 "DT overlays — the alternative" — first sentence is "Instead of N full DTBs, you can have **one base DTB** and **N overlay files** that patch it." Good and clear. Keep.
- §23A.6 — embedded `bootcmd` script with `if/elif/else/fi`. Reader from Ch23 §23.1's intro will see this and recognize the DSL. Now ensure §23.1 actually introduces `elif` syntax — it doesn't currently. Either backfill in Ch23 or add a note in §23A.6: "`elif` is U-Boot's else-if; standard hush syntax."

### MCU-engineer friendliness
- §23A.1 — Three hardware revs scenario is excellent and very real. Keep.
- §23A.4 Pattern A — Strap pin — explain WHY a strap pin: "On MCUs you'd compile different firmware per board variant. On Linux you ship one binary and detect the variant at runtime. Strap pins (resistor-populated GPIOs) are the cheapest detection mechanism: $0.01 BOM, 1 ms boot-time read, instantly identifiable in software." This justifies the pattern instead of presenting it as a given.
- §23A.5 — "DT overlays" — for an MCU reader this is new vocabulary. Add: "An overlay is a small DT 'patch file'. It says 'add these nodes, change these properties' relative to a base DT. U-Boot (or the kernel) merges them in memory. Conceptually identical to a `git diff` of two DT files." 

### Missing examples / figures
- §23A.2 — `mkimage -f multi.its multi.itb` output should show the build's hash-verification step so the reader sees that the hashes were computed.
- §23A.3 — show actual `bootm 0x82000000#conf-rev-b` output (the lines: "Loading kernel from FIT Image at 82000000 ... Verifying Hash Integrity ... OK ... Loading fdt from FIT Image ..."). Reader needs to know what success looks like.
- §23A.5 — show the resulting merged DT after `fdt apply`. A `fdt print /` excerpt would show "the base I²C2 node + the overlay's gt911@5d node combined". Without seeing the result, the reader has no mental verification.
- §23A.6 — the inline `bootcmd` script is large and complex. Add a small flow diagram: "i2c probe → read byte → switch → setenv variant → bootm with variant".

### Technical errors
- §23A.4 Pattern A — `gpio_get_value(IMX_GPIO_NR(1, 9))` — the `IMX_GPIO_NR(bank, offset)` macro encodes a GPIO descriptor; check it's the U-Boot API (some versions use `gpio_request` first). Add a note that you may need `gpio_request(IMX_GPIO_NR(1, 9), "rev_pin")` before `gpio_get_value`.
- §23A.4 Pattern B — `i2c_set_bus_num(0)` then `i2c_read(0x50, 0xFF, 1, &id, 1)`. The address `0xFF` of a 24C04 is at end of bank 0 (24C04 is 512 bytes total, 256 per bank with the bank chosen via the I²C slave address LSB). For a 24C04 the high half (256-511) is accessed at chip address 0x51. So reading "byte 0xFF" via chip 0x50 reads byte 255 of the lower bank, which is fine — but if the manufacturing pipeline writes the ID byte at offset 0xFF of the *upper* bank, the code reads the wrong byte. Note the assumption.
- §23A.5 — `fdt resize 8192` — the syntax is `fdt resize <size_in_bytes>`. 8192 = 8 KiB additional space. The reader will see "8192" and might read it as KiB; specify "8192 bytes (= 8 KiB) extra".
- §23A.5 trade-offs table — "Tooling support" row for overlays says ">= 2020.07". That's accurate for some features (e.g., `fdt apply` with symbol resolution) but `fdt apply` itself has been around longer. Tighten: "`fdt apply` works in any modern U-Boot; symbol-based overlay support requires `dtc -@` and U-Boot ≥ 2020.07."
- §23A.6 — `i2c read 0x50 0xFF 1 0x82000000` reads 1 byte from chip 0x50 offset 0xFF into DRAM address 0x82000000. The `setexpr.l id *0x82000000` then assigns env var `id` from the loaded byte. This works *only if* the byte is at the lowest address of the loaded buffer (little-endian read of a 4-byte value where only the low byte matters). For 1-byte reads use `setexpr.b` if available, or carefully comment.

### Knowledge prerequisites missing
- §23A.4 Pattern C — eFuse — `BOARD_ID_BANK, BOARD_ID_WORD` are placeholder symbols; the reader will not know which bank/word to use. Either give a real example (e.g., NXP commonly uses GP1[0:7] for board ID) or state "you choose bank/word per project; verify with `imx_efuse_blow_helper` (Ch9 reference) which fuses are available".
- §23A.5 — DT overlay syntax (`/plugin/`, `&label`) is new. Reader hasn't yet read Ch 27. Forward-reference.
- §23A.5 — `dtc -@ -O dtb` — the `-@` flag generates a `__symbols__` node in the compiled DTB so overlays can resolve labels. Explain once.

### Other
- §23A.8 Pitfall "Strap pin floats" — good. Add a corollary: "Use the i.MX6ULL internal pull-up/pull-down if you don't have an external pull. Configure via IOMUX PAD_CTL (Ch12)."
- §23A.7 Lab item 5: "Read U-Boot's `fdt apply` source." — fine, but the suggested path `cmd/fdt.c` and `common/fdt_support.c` — the actual `fdt apply` implementation in modern mainline lives in `boot/fdt_support.c` (not `common/`). Verify.

## Ch24 — Workflows: TFTP, NFS, USB-OTG

### Readability
- §24.1 introduction: "stop reflashing the SD card." Strong opener. Keep.
- §24.4 `flash_all.uuu` script: "(Real recipes are more involved; this is the structure.)" — this disclaimer undermines the example. Either provide a real, working recipe, or remove the disclaimer and explain that this is an illustration. As-is the reader is left wondering what's wrong with the example.
- §24.5 ASCII flow diagram is excellent. Possibly the best diagram in Part III. Keep verbatim.

### MCU-engineer friendliness
- §24.1 — the table mapping transport → job is great. Add a line acknowledging this is *very* alien to MCU engineers: "MCU engineers: this workflow has no equivalent in MCU dev. On an STM32 you flash and run; on embedded Linux you can have the kernel come from a TFTP server, the rootfs from an NFS mount, and the bootloader from SD — three transports, three lifecycles. The next sections set each up."
- §24.2 "Stage layout on the host" — using `ln -s` to symlink `/srv/tftp/zImage` to the kernel build tree's output is *the* pro tip. Currently it's stated cleanly. Keep. Add: "MCU engineers used to copy-then-flash workflows: this symlink eliminates the copy step entirely. `make zImage` immediately publishes a new kernel."
- §24.3 — NFS root explanation. MCU engineers may not know NFS at all. Add: "NFS is 'mount a directory on the host as a directory on the target over the network'. The target sees `/srv/nfs/rootfs/etc/passwd` as if it were a local file; reads are RPCs. For development this is magical: edit on host, change visible on target in milliseconds."
- §24.4 `uuu` — `uuu` is a high-level scripting tool. MCU engineers will see "fastboot" + "SDP" + "uucmd" and feel lost. Brief glossary: "**SDP** (Serial Download Protocol) is the i.MX BootROM's USB interface — Ch9. **Fastboot** is an Android-derived protocol U-Boot can speak to expose 'flash my eMMC' commands over USB. **uuu** is a script driver that combines both."

### Missing examples / figures
- §24.2 — add a wireshark / `tcpdump -i eth0 port 69` snippet showing TFTP packet flow. Or at least show "after `tftp ${loadaddr} zImage`, on the host you'll see one UDP request packet to port 69, then ~6000 data packets." Helps reader debug when TFTP doesn't work.
- §24.3 — add an example `/etc/exports` line *plus* the `showmount -e localhost` verification. Currently the reader sets exports once and hopes; show how to verify.
- §24.4 — provide a real, working `uuu` recipe for first-time flashing of the MINI. The current placeholder script is non-functional. Reference NXP's `imx_uart` or `imx_usb_loader` if there's a simpler tool.
- §24.6 — the env helpers block is great. Add a "save this to a file `dev-env.txt` and load via `env import -t 0x82000000 <size>`" tip — so the reader can version-control their dev env.

### Technical errors
- §24.2 — TFTP speed: "TFTP runs at ~1 MB/s on 10/100 Ethernet (UDP, small windows). A 6 MB `zImage` arrives in ~6 seconds." On modern U-Boot with `CONFIG_TFTP_BLOCKSIZE=1468` and `CONFIG_TFTP_WINDOWSIZE=8` (RFC 7440 windowsize), TFTP can run at 5-10 MB/s. The 1 MB/s figure is for default block size 512. Either cite the conservative default or mention the tunables.
- §24.3 — `nfsroot=192.168.7.1:/home/you/imx6ull/rootfs,vers=3,nolock,tcp` — `tcp` here is implicit for NFSv3 in many distros but not all. Verify the exact tokens accepted by the kernel's nfsroot parser (`Documentation/admin-guide/nfs/nfsroot.rst`).
- §24.3 — kernel boot log sample shows "`[ 7.812345] Sending DHCP requests . OK`" but the `ip=` cmdline shown earlier sets a static IP, not DHCP. Inconsistent. Either change cmdline to `ip=dhcp` or change the log to not mention DHCP.
- §24.4 — `uuu` script: `SDP: boot -f SPL` then `SDPU: write -f u-boot-dtb.imx`. `SDPU` is the SDP-mode-as-a-USB-device-after-boot subset. The order is plausible but the actual NXP recipe is `SDP: boot -f flash.bin` (combined SPL+U-Boot) or `SDP: boot -f SPL` + `SDPU: write -f u-boot.imx`. The variant in this chapter doesn't match the most common form; check against the latest `uuu` documentation.
- §24.4 — `FB: ucmd mmc write ${fastboot_buffer} 0x2000 0x6000` writes 0x6000 sectors (24576 sectors = 12 MiB) starting at sector 0x2000 (= 4 MiB). A 6 MiB zImage wouldn't need 12 MiB. Numbers don't quite match the comment "write zImage to MMC".
- §24.6 — `console=${console}` env var is referenced but never set. Add `setenv console ttymxc0,115200` to the prerequisites.

### Knowledge prerequisites missing
- §24.3 — `ip=` cmdline format: `client::gateway:netmask::interface:autoconf`. The number of colons is critical. Show with each field labeled:
  ```
  ip=192.168.7.2 : : 192.168.7.1 : 255.255.255.0 : : eth0 : off
       client      server-ip     gateway          netmask     hostname  interface  autoconf
  ```
  The empty fields (`::`) are critical and easy to miscount.
- §24.3 — `nfs.callback_tcpport=0` and `CONFIG_NFS_DEBUG` — these are kernel-side knobs the reader has not yet encountered. Forward-reference Ch28/Ch29.
- §24.4 — `udev` rule from Ch3 §3.8 — refresh the reader's memory: "the `udev` rule lets non-root users access /dev/uuu* devices; without it `uuu` needs sudo."
- §24.6 — `bootargs` substitution with `${var}` — the reader has seen this in Ch23, but the `nfsroot_args` here is a 2-line continuation with `\`. U-Boot env values can't contain literal newlines; the `\` continuation is a *display* convenience in this chapter, not actual env syntax. Add: "(These are formatted across lines for readability; in the actual env they're one logical line.)"

### Other
- §24.4 — "**Automated production line** — `uuu` can flash N boards in parallel; standard NXP practice for factory programming." — true and useful. Consider expanding into a short subsection or forward-reference to Ch63 (production / OTA).
- §24.7 Lab item 5: "Practice the `uuu` recovery. Deliberately wipe the SD card's first MB" — this is genuinely scary for a beginner. Add a safety note: "Be triple-certain `/dev/sdX` is your SD card and not your host's hard disk before running `dd if=/dev/zero`. `lsblk` before any `dd` operation."
- §24.8 — Pitfall "Slow Ethernet PHY auto-negotiation. Some PHYs take 2-3 seconds to come up." — useful. Add: "Symptom: `tftp` says 'no link' on first try, works on second. Either pre-bring-up the link with `mii info` then wait, or use `setenv autoload no; dhcp` to force link establishment before TFTP."
- End-of-Part-III box: "Everything from here on assumes you can boot to a U-Boot prompt, network-boot a kernel, and NFS-mount a rootfs." — Strong closer. Keep.


---

# Part IV — Kernel: Review

## Cross-cutting observations

- **DTS path is stale for v6.5+.** Every chapter (25, 26, 27, 27A) refers to `arch/arm/boot/dts/imx6ull-*.dts` and `arch/arm/boot/dts/Makefile`. Since v6.5 (mid-2023), mainline reorganised ARM 32-bit DTS into per-vendor subdirectories: i.MX files live under `arch/arm/boot/dts/nxp/imx/`. The book pins to v6.6 in Ch 25 (`git checkout v6.6`), so every cited path is wrong. Either pin to a pre-v6.5 tag (`v6.1` LTS works) or globally update paths to `arch/arm/boot/dts/nxp/imx/imx6ull-14x14-evk.dts`. This affects the Makefile snippet in §27.2 too — that snippet now lives in `arch/arm/boot/dts/nxp/imx/Makefile`.
- **MCU-bridge style applied unevenly.** Ch 25 and Ch 26 have light bridging; Ch 27 has one excellent §27.11 bridge but most other DT mechanics arrive without analogy. Ch 28 has almost no MCU comparisons despite covering material (page tables, idle thread, BSS zeroing) that maps cleanly onto bare-metal startup code the reader has already written. Suggest a consistent "MCU parallel" sidebar pattern, one or two per chapter.
- **First-time term policy.** "platform_device", "platform_driver", "phandle", "tmpfs", "devtmpfs", "udev", "mdev", "regmap", "devm_", "CONFIG_OF", "EXPORT_SYMBOL_GPL", "noinline __ref", "user_mode_thread", "kernel_thread" all appear without inline definition somewhere across these chapters. Decide whether to define on first use or to add a Part IV glossary appendix; right now the reader has to guess from context.
- **MCU-style line-numbered or commented register-map diagrams are absent across all chapters.** The author leaves them in code text. Ch 26's pre-boot contract table and Ch 28's phase-diagram are the only ASCII visuals — these work well; replicate the style.
- **Lab steps occasionally assume tooling the book has not introduced.** `picocom -L`, `cpio -H newc`, `dtc -@`, `make scripts/config`, `pip install dtschema` — each is referenced once but never previously installed. Add a per-chapter "you will need" preamble or a one-page "Part IV tooling" appendix.
- **Boot decompressor claim.** Ch 25 §25.5 says "the stub copies itself out of the way". Ch 26 §26.8 says "the kernel is < 16 MiB" justifies `0x83000000` for DTB. These two together undersell the rule: on ARM the decompressor by default places the decompressed kernel at `ZRELADDR` (`0x80008000` on i.MX6ULL) and walks upward; the DTB at `0x83000000` is safe because it's above the 16 MiB the kernel needs at run time, **not** because the compressed image is small. Reader will infer the wrong rule when they bump kernel size.

## Ch25 — Building mainline Linux

### Readability
- §25.1, "thousands of patches on top" is fine but the surrounding paragraph is choppy: "The NXP fork for i.MX6ULL is `linux-imx`, currently pinned around `5.15` and `6.6` depending on the branch." Two clauses joined by "depending on the branch" reads stilted to an ESL reader. Suggest: "NXP forks mainline into `linux-imx`. Active branches are pinned to `5.15` and `6.6`; older branches exist for legacy products."
- §25.3, "Every Y in `.config`" — should be "Every entry" or "Every line". "Y" reads like a placeholder.
- §25.4, "Three independent targets" is misleading — `zImage` depends on the same Makefile-generated objects as `modules` if those modules are `=y`. Reword to "three artifact groups" or "three build targets".
- §25.4 "First build takes 5–10 minutes on a modern host depending on `-j` parallelism. Subsequent incremental builds are seconds." — split to two sentences without "depending on": "On a modern host with `-j$(nproc)`, the first build takes 5–10 minutes. Incremental rebuilds finish in seconds."
- §25.9 pitfalls — "aaprcp" is a typo (probably "aarch64"-related or "aapcs"). Fix.

### MCU-engineer friendliness
- §25.1 "vendor BSPs" — bridge to what the reader knows: "Like the STM32CubeMX HAL: the vendor's curated, well-tested but slow-moving snapshot. NXP's `linux-imx` is the equivalent for i.MX."
- §25.2 directory layout — add a one-line note next to `arch/arm/kernel/`: "MCU equivalent: vendor `startup.s` and `system_xxx.c` files — the bring-up code that runs before `main`."
- §25.4 — the `=y` vs `=m` distinction needs the bridge: "`=y` is what you're used to — code linked into the final binary. `=m` is *new* to you: a separately-loadable driver, a `.ko` file that the running kernel can `insmod` and `rmmod`. There is no MCU equivalent; it's one of Linux's defining capabilities."
- §25.4 table — `vmlinux` "ELF with full debug info" — bridge: "Like the `.elf` your STM32 toolchain produces alongside the `.bin`. Same idea: full symbol table for the debugger."
- §25.5 — the bare-metal reader has done their own decompressor exactly never. Compare to "an STM32 bootloader that XIPs out of flash" vs "Linux's compressed kernel that *self*-decompresses". Spell out the novelty.

### Missing examples / figures
- After §25.2 directory layout add a "where does the equivalent live in a typical MCU project?" two-column comparison table (e.g., `arch/arm/kernel/head.S` ↔ `startup_stm32f4xx.s`, `kernel/sched/` ↔ "your RTOS scheduler", `drivers/tty/serial/imx.c` ↔ "your `uart.c` HAL", etc.).
- After §25.4 add an artifact-flow ASCII diagram complementing §25.5's wrapping diagram: a left-to-right "source files → object files → vmlinux ELF → Image → zImage → boot" pipeline so the reader sees the full chain in one figure.
- §25.4 "What just got produced" — show one screenful of `size vmlinux` output (`text data bss dec hex filename`) so the reader sees the segment sizes. Reinforces the bare-metal mental model (`.text/.data/.bss`).

### Technical errors
- §25.3 reads "`imx_v6_v7_defconfig` (formerly `imx_v7_defconfig`) is the omnibus i.MX configuration that covers every i.MX SoC the v6/v7 ARM cores support — i.MX5, i.MX6 (all variants including ULL), i.MX7." This omnibus does *not* cover i.MX5 (that's `imx_v6_v7_defconfig` for v5 series — actually some i.MX5 boards are covered, but framing it as "every i.MX SoC" is too broad). Verify: in v6.6, `imx_v6_v7_defconfig` covers i.MX31/35/27 (v6), i.MX5/6/7 (v7). Tighten the claim.
- §25.4 the table row `arch/arm/boot/Image` says "rarely used on ARM32 (used on AArch64)" — true but worth noting that `Image` *is* what some bootloaders prefer on ARM32 with FIT images. Not an error, but the parenthetical undersells.
- §25.6 "Entry point address: 0x80008000" — confirm. On i.MX6ULL DRAM base is `0x80000000` and the ARM Linux convention is `PHYS_OFFSET + 0x8000`. Correct, but worth noting that this is the *physical* entry; the virtual `_text` is at the kernel's virtual base (`PAGE_OFFSET + TEXT_OFFSET` = `0xC0008000` historically; with `CONFIG_VMSPLIT_*` it varies). The reader will check the wrong number against `vmlinux`.
- §25.8 lab #2: `init/version-timestamp.c` — that filename does not exist in mainline v6.6. The banner string is built in `init/version.c` and `init/version-timestamp.c` only exists conditionally on some configs; `kernel/Makefile` and `scripts/mkcompile_h` are involved. Verify before publishing; reader will copy/paste and fail.
- §25.10 path "`Documentation/arch/arm/`" — modern path is `Documentation/arch/arm/` in v6.5+; pre-v6.5 it was `Documentation/arm/`. Pin to whichever version you're using.

### Knowledge prerequisites missing
- §25.2 introduces `arch/arm/boot/compressed/` without explaining what that subdirectory's contents do until §25.5. Forward-reference or move §25.5's diagram concept up.
- §25.3 uses `CONFIG_ARCH_MULTIPLATFORM=y` and `CONFIG_SOC_IMX6=y` without ever defining "Kconfig symbol", "compiled in (`=y`) vs module (`=m`)", or the `.config` mechanic — that lands in Ch 30. Add a 2-sentence forward-reference in §25.3: "We treat `.config` as a black box here; Ch 30 is the deep dive."
- §25.4 references "the version's vermagic string" in pitfalls — never defined. Add one sentence.
- §25.7 says `O=` "puts every generated file in a sibling directory" without explaining *why* out-of-tree builds matter beyond `git status` cleanliness (parallel configs, faster clean, CI sharing). Worth two more sentences.

### Other
- Lab step 5 says "`ccache` is the reason if you have it installed; otherwise the same speed." That second clause is wrong — without ccache, `make distclean` forces a full recompile, much slower than incremental. Verify and rewrite; the lab as written will confuse the reader who runs it.
- §25.2 — the i.MX clock-driver path is `drivers/clk/imx/`, written correctly, but elsewhere when bindings are referenced the path is the older flat one. Be consistent.

## Ch26 — Booting the kernel from U-Boot

### Readability
- §26.1 "Get `r2` right and a 95% chance the kernel boots; get it wrong and you stare at silence wondering what's happening." — grammar is off. Suggest: "Get `r2` right and the kernel boots ~95% of the time. Get it wrong and you stare at silence."
- §26.2 "The address was chosen for two reasons" — passive and clipped. Suggest: "We picked `0x82000000` for two reasons: it sits 32 MiB above the DRAM base (`0x80000000`) so it doesn't collide with U-Boot's relocated image near the top of DRAM, and it leaves room below for the decompressed kernel to land at the canonical `0x80008000`."
- §26.3 "If this token is wrong, you see no kernel output." reads abrupt; expand: "If `console=` names a device the kernel cannot find, every `printk` after console init goes nowhere and you see no kernel output past the early-decompressor banner."
- §26.4 caption "Read every line. Each tells you something concrete:" — split. "Read every line. Each one carries a piece of state the kernel just discovered."
- §26.5 "Symptom: silence." appears three times in one bullet list. Vary: "you see nothing", "the boot log is empty", "the UART stays quiet."

### MCU-engineer friendliness
- §26.1 — the pre-boot contract table needs the bridge: "This is the kernel's ABI to the bootloader. The MCU equivalent is the reset-vector contract in your STM32 startup code: the bootloader (or ROM) hands off in Thumb mode, MSP loaded from `0x0`, PC from `0x4`. Same idea — just more registers carrying state."
- §26.2 — `bootz` looks like magic. Bridge: "`bootz` plays the role your STM32 bootloader's `JumpToApp()` plays: it sets up the handoff state then `bx` into the application. The complication is that the 'application' (Linux) wants a DTB pointer in `r2`, where your STM32 app only wanted `SP` in `MSP`."
- §26.3 — `bootargs` deserves explicit bridging to "what an MCU engineer has never seen": the runtime-parsed command line. "Bare metal has no equivalent. The closest analog is a config struct you set in flash before boot, except this string is dynamic and the kernel parses dozens of tokens at startup."
- §26.4 boot-log walk-through — bridge `MIDR` to a concept the reader owns: "MIDR is the ARM Cortex equivalent of `DBGMCU_IDCODE` on STM32 — the silicon-readable 'what am I'."
- §26.4 — `CMA: Reserved 64 MiB` is unintroduced. Bridge: "Like reserving a heap pool at link time, but at run time and from the page allocator. Used when a peripheral needs a physically-contiguous DMA buffer larger than a single page."

### Missing examples / figures
- After §26.1 add an ASCII handoff diagram: U-Boot DRAM map immediately before `bootz` — show where U-Boot itself lives (top of DRAM), where the zImage is loaded, where the DTB sits, and which register holds which address. The reader has the bare-metal mental model for memory maps; activate it here.
- After §26.4 add a labeled annotated boot-log: take the 20-line example, draw arrows from each line back to the kernel subsystem that produced it (preview of Ch 28).
- §26.5 troubleshooting — flowchart of "what to check when there's no output": is `bootargs` set? did the DTB load? did `bootz` syntax include the `-`? Diagram is more navigable than the bullet list.

### Technical errors
- §26.1 row 1 "MMU off, caches off" — i.MX6ULL U-Boot at the time of `bootz` has typically *enabled* I-cache, sometimes D-cache too, for boot speed. `cleanup_before_linux()` flushes and disables before the jump. The current wording ("MMU off, caches off … `bootz` calls `cleanup_before_linux()` before the jump") technically tells the truth but reads as if caches are off long before the jump. Tighten to "caches are flushed and disabled inside `cleanup_before_linux()` right before the jump."
- §26.2 — "this is the magic line" overstates `bootz`. It's just a regular U-Boot command. Suggest "this is the line that hands control over."
- §26.4 boot log "CPU: ARMv7 Processor [410fc075] revision 5 (ARMv7), cr=10c5387d" and accompanying table entry "`0x410FC075` decodes to ARM-implemented Cortex-A7." Verify the MIDR decode: 0x410FC075 → implementer 0x41 (ARM), variant 0xF, architecture 0xC, primary part 0x075. Cortex-A7's primary part number is 0xC07, not 0xC075. The `5` in `C075` is the revision nibble. The decode statement is slightly wrong as written; correct is "implementer ARM, part 0xC07 (Cortex-A7), revision r0p5."
- §26.4 table row "Movable zone start for each node" — accompanying boot-log line is informational and present in modern kernels but readers will not always see it. Note it's optional/conditional.
- §26.6 "`earlycon=ec_imx6q,0x02020000`" — verify the earlycon driver name. Mainline registers as `ec_imx6q` for the i.MX UART early-console. Confirm against `drivers/tty/serial/imx.c` (it uses `EARLYCON_DECLARE(ec_imx6q, ...)`)). The address `0x02020000` is UART1's base — correct per IMX6ULL RM.
- §26.8 pitfall on `CONFIG_ARCH_MULTI_V6_V7` / `CONFIG_ARCH_MULTI_V7_ONLY`: the latter symbol does not exist in mainline (the canonical symbols are `ARCH_MULTI_V7` and `ARCH_MULTI_V6_V7`). Fix.

### Knowledge prerequisites missing
- §26.1 introduces "SVC mode, IRQ/FIQ masked" — the reader knows IRQ from MCU world, but ARM-A processor modes (USR/SVC/IRQ/FIQ/ABT/UND/SYS) were not covered in Parts I–III in this depth. Add one sentence or forward to Ch 28.
- §26.3 `earlycon` is introduced here and again in §26.6. Combine: first introduction should land in §26.3 with one paragraph; §26.6 is the deep dive.
- §26.5 "VFS panic" — `VFS` is not defined yet. Inline: "VFS = Virtual File System, the kernel layer that abstracts over ext4 / vfat / NFS / etc. We meet it properly in Part V."
- §26.5 "PMIC over I²C" — PMIC was covered in Part II but ESL readers benefit from the one-line reminder.

### Other
- Lab step 3 ("Mismatch the DT") and step 4 ("Bad cmdline") are excellent — they teach failure modes by induction. Add a step 6: deliberately load a corrupt DTB (truncate the file by 100 bytes) and observe `__vet_atags` rejecting it.
- §26.8 mentions "kernel built ARMv8-only" as a pitfall — but the reader almost certainly cannot build an arm64 kernel by accident given the toolchain they have. Remove or replace with a more likely real-world trap (e.g., `CONFIG_THUMB2_KERNEL=y` mismatch with bootloader thumb-state assumption).

## Ch27 — Device Tree

### Readability
- §27.1 — "the community's response was to adopt the **Device Tree**" — fine, but the quote about Linus is informal anecdote that some readers will read as unprofessional. Either drop the quote or set it off as a sidebar.
- §27.2 "what the kernel actually consumes at boot" — fine. But the surrounding paragraph reads list-of-bullets-then-prose, then list-of-bullets-then-prose. Vary the structure.
- §27.4 — "for an MMIO peripheral like UART1, this is the register-block base address: `serial@2020000`" — slightly muddled because `@2020000` follows the *name* and the example then mentions the address again. Suggest: "The unit address comes from the device's base address on its parent bus. For UART1 (memory-mapped at `0x02020000`), the node is named `serial@2020000`."
- §27.5 "A 'cell' is exactly 32 bits." — abrupt. Expand: "A cell is the DT's atomic integer unit — always exactly 32 bits, regardless of the host architecture's word size."
- §27.6 — the heading "`compatible` — the binding key" is good. Sub-section flow then jumps to `reg`, then back to `#address-cells`, then `interrupts`. Re-order so dependencies flow forward: `compatible` → `#address-cells/#size-cells` → `reg` → `interrupts` → `clocks` → `pinctrl` → `status` → `aliases/chosen`.
- §27.11 — title "The single biggest mental shift" is duplicated wording from the chapter-opener "What" line. Pick one place to say it.

### MCU-engineer friendliness
- §27.1 — fantastic motivational opener for an MCU engineer, *but* the C-array example is from Samsung S3C2440 not i.MX. Use a fictional/redacted snippet that's more obviously similar to "what you would have written on STM32 if you booted Linux on it." Or actually reference an old `arch/arm/mach-imx/mach-mx6q_sabrelite.c`-style file that no longer exists but would have on the i.MX side.
- §27.5 "cell" — bridge: "Think of a cell as a `uint32_t` in your driver code, packed big-endian in the binary form."
- §27.6 — phandles arrive without naming. Define explicitly: "A phandle is a 32-bit unique integer the DTC assigns to every labelled node. The `&label` syntax expands at compile time to the phandle of that node. In the runtime kernel, `of_parse_phandle()` does the reverse lookup. The MCU equivalent: a pointer-by-name resolved at link time — except DT does this in a binary blob and the kernel resolves it on the fly."
- §27.8 nine-step flow — superb. Reinforce: end with one sentence "All nine steps fire automatically; the board engineer's only contribution is the DT node."

### Missing examples / figures
- §27.3 needs an ASCII tree diagram. The textual description ("`/`, then `chosen`, then `memory@…`, then `reg_sd1_vmmc:`, then `&uart1`") is hard to picture. A `tree(1)`-style figure with `/`, `chosen`, `aliases`, `memory@80000000`, `soc { aips1 { ... } }`, `&uart1`, etc., would help enormously.
- §27.6 `#address-cells`/`#size-cells` — add a 2x2 figure: parent `<1>/<1>` → child `reg = <0xA 0xB>`; parent `<2>/<2>` → child `reg = <0x0 0xA 0x0 0xB>`. Visual makes the rule click.
- §27.7 `imx6ull.dtsi` walk-through is a wall of text; add an ASCII tree of the SoC's DT hierarchy: root → `intc`, `cpus`, `clocks`, `soc { aips1, aips2, aips3, ocram, ddr-pmu }` with the AIPS bridges expanded.
- §27.8 nine-step flow — turn into a numbered flow diagram with arrows from "DTB in DRAM" → "unflatten_device_tree" → "platform devices" → "driver match" → "probe()" → "/dev/ttymxc0". Reader sees the whole pipeline.
- §27.10 — add an end-of-section ASCII showing "DT node properties" ↔ "of_* API calls" mapping (e.g., `reg = <…>;` ↔ `platform_get_resource(MEM)` / `devm_ioremap_resource`; `clocks = <…>` ↔ `devm_clk_get`; `interrupts = <…>` ↔ `platform_get_irq` / `devm_request_irq`).

### Technical errors
- §27.7 `imx6ull.dtsi` — the snippet shows `intc: interrupt-controller@a01000` with `compatible = "arm,cortex-a7-gic"`. The actual mainline binding for the i.MX6ULL GIC is `compatible = "arm,gic-400"` (with `arm,cortex-a7-gic` accepted as a fallback by some versions). Verify the exact string in current `imx6ull.dtsi`; the example will mislead a reader who greps for it.
- §27.7 `aips1: aips-bus@2000000` — modern mainline DTS uses `compatible = "fsl,aips-bus", "simple-bus"` *and* node names like `bus@2000000` (the kernel DT-bindings YAML team has been renaming `aips-bus@` to `bus@`). Verify against v6.6 `imx6ul.dtsi`.
- §27.7 mentions `ddr_pmu: ddr-pmu@21b0000` with `reg = <0x21b0000 0x10000>`. Verify — i.MX6ULL MMDC base per the IMX6ULL RM is `0x021B0000` (correct). Region size of `0x10000` (64 KiB) — verify, the MMDC register region is much smaller (~4 KiB in the RM register definition section). A 64K reg region works because it's a power-of-two MMU mapping unit but the actual register block is smaller — the YAML `reg` should reflect the actual block size, not the page.
- §27.8 step 3: "`setup_arch()` → `setup_machine_fdt(0x83000000)`" — `setup_machine_fdt` doesn't take the raw address as an argument in recent kernels; it uses the global `__atags_pointer` saved by Phase 1. Tighten the wording so the reader doesn't grep for that signature.
- §27.9 last paragraph: "the upstream driver `drivers/hwmon/tmp103.c` and its variants — verify the exact name in current sources". You're correct to flag verification, but the canonical TMP102 driver is `drivers/hwmon/tmp102.c`, not `tmp103.c`. Fix the speculation; show the real path.
- §27.6 `chosen` properties: `linux,initrd-start` and `linux,initrd-end` properties take **physical addresses**, not flag them as "where an initrd lives" without that detail. Worth a sentence.
- §27.12 lab step 4 `grep -r "fsl,imx6ul-uart" drivers/` — correct command but the reader will hit no match because mainline uses `fsl,imx21-uart` as the fallback. Worth a hint: "If grep returns nothing, try the *second* compatible string in the DT list — that's the fallback that drivers actually match."
- §27.13 "`status = "okay"` typo" pitfall says newer dtbs_check will warn on `"ok"`. Verify — dtschema currently flags `"ok"` as invalid (it's not in the enum); strengthen from "lenient about it" to "older kernels accepted `"ok"`; modern dtbs_check rejects it as invalid."

### Knowledge prerequisites missing
- §27.6 `interrupt-controller;` (empty property) marks the node as an IRQ source — but `#interrupt-cells` and the interrupt-parent inheritance chain deserve their own short subsection. Currently scattered.
- §27.6 `#clock-cells` is mentioned in passing ("the number of cells per entry comes from a `#clock-cells` property on the provider node") but never shown in an example. Show the provider's `#clock-cells = <1>;` declaration explicitly.
- §27.8 step 7 uses `struct platform_device *pdev` — the reader needs a one-paragraph "platform_device = the Linux representation of a non-discoverable bus device", because the term will be used through Part VI. Define it once here.
- §27.10 `devm_clk_get` and `devm_pinctrl_get` — both `devm_*` helpers are introduced without explaining the managed-resource pattern. Worth one sidebar: "`devm_*` functions auto-free their resource when the device is detached. Saves you from writing error-unwind code. We meet them properly in Part VI."
- §27.10 "About twenty `of_*` helpers" — name a few more in a table (of_property_present, of_property_match_string, of_iomap, of_address_to_resource). The current sample is short.
- §27.10 introduces `pdev->dev.of_node` without ever explaining `struct device` vs `struct platform_device`. Worth a forward reference: "the device structure embeds the DT node pointer; we cover the device/driver model in Ch 41."

### Other
- §27.9 overlay example uses `dtc -@ -O dtb` — the `-@` flag is necessary for overlays and never explained. Add: "`-@` instructs dtc to emit a symbol table in the DTB so phandles can be resolved at overlay-apply time."
- Lab step 5 says "compile with `dtc -@ -O dtb`" — also missing `-I dts` and the input filename in the example command line. Reader will run a broken command. Fix to the full form: `dtc -@ -I dts -O dtb -o tmp.dtbo tmp.dtso`.

## Ch27A — DT bindings YAML and dt_binding_check

### Readability
- §27A.1 — first sentence is long. "For the first ~15 years of Device Tree's life, 'bindings' lived as free-form `.txt` files in `Documentation/devicetree/bindings/`." Split: "Bindings used to be free-form `.txt` files. They lived in `Documentation/devicetree/bindings/` for the first ~15 years of DT."
- §27A.2 — "the value `true` after a name is the YAML shorthand for 'this is a valid property with no additional constraints'" — confusing because `true` in YAML is a scalar. The DT-schema rule is that `<name>: true` means "this property is allowed; inherit constraints from parent". Reword: "`uart-has-rtscts: true` says 'this property is permitted; inherit its type from the parent schema (`serial.yaml`).'"
- §27A.3 "A typical `dtbs_check` run on the i.MX tree produces ~100 warnings as of v6.6" — give the reader an action: "Don't try to fix all of them; we'll add zero new ones."
- §27A.5 pattern "A pair of related arrays whose lengths must match" — the surrounding example has no `dependencies:` clause showing how arity is *actually* enforced. The current explanation only says lengths "should" match. Either show the schema construct that enforces or relabel as "convention".

### MCU-engineer friendliness
- §27A.1 — "machine-checkable" is the key concept. Bridge: "Compare to your STM32 CMSIS SVD files: they describe the chip's registers in a machine-readable XML so headers can be auto-generated. DT bindings are the same idea — a machine-readable schema so DTS files can be auto-validated."
- §27A.2 — `oneOf` / `allOf` are JSON-Schema constructs. The MCU engineer has not seen JSON-Schema. One sentence: "`oneOf` = exactly one of these forms is permitted. `allOf` = all of these constraints apply (used for inheritance)."

### Missing examples / figures
- §27A.2 — after walking the YAML, add an ASCII showing the inheritance chain: `fsl-imx-uart.yaml` → `serial.yaml` → `serial-base.yaml` / `dtschema/types.yaml`. The reader needs to *see* what `allOf` does.
- §27A.3 — show one actual error message from `dtbs_check` when it fires. The reader has never seen the output format; they won't know what to look for. Suggest: a 5-line excerpt like `imx6ull-14x14-evk.dtb: serial@2020000: clock-name: 'ipg' is not one of ['per', 'ipg']`.
- §27A.5 — visual table of "intent → JSON-Schema construct → example" rather than free-form sections, would compress the page and help navigation.

### Technical errors
- §27A.1 "Since kernel v4.18 (mid-2018), every new binding *must* ship a YAML schema" — *strong* statement. The actual policy: since v4.18 the infrastructure existed, but the *requirement* for new bindings to be YAML was rolled in gradually and the strict-rejection policy is more recent (v5.x). Tighten: "From v4.18 the YAML infrastructure landed. Since roughly v5.x, the policy has hardened: new bindings without a YAML schema are typically rejected on the lists."
- §27A.2 `clock-names: items: [const: ipg, const: per]` — verify against current `fsl-imx-uart.yaml`. The order in current mainline matches; just confirm before printing.
- §27A.2 `fsl,uart-has-rtscts` "Deprecated, use uart-has-rtscts instead." — confirm the property is actually deprecated upstream; the schema as quoted in some kernel versions does not say "deprecated" but "obsolete" or carries the deprecation in `description`. Pin to v6.6 exactly.
- §27A.4 "Save that and run: `make ARCH=arm CROSS_COMPILE=arm-linux-gnueabihf- dt_binding_check DT_SCHEMA_FILES=leds/myorg,pa-led.yaml`" — `DT_SCHEMA_FILES` takes a path relative to `Documentation/devicetree/bindings/`. The shell will not expand the comma in `myorg,pa-led.yaml` to a special character; you want the full filename. Verify the exact path syntax.
- §27A.4 binding example has `additionalProperties: false` — but if you inherit (`allOf: $ref: ...`) you generally want `unevaluatedProperties: false` (the §27A.8 pitfall says exactly this). The example as written contradicts the pitfall. Use `unevaluatedProperties: false` in the example.

### Knowledge prerequisites missing
- §27A.2 "`$id`" and "`$schema`" — JSON-Schema concepts. Define inline.
- §27A.2 "`$ref: serial.yaml#`" — explain the `#`-fragment syntax (refers to the root of the document).
- §27A.6 "inheriting from base schemas" — `i2c-controller.yaml` and `spi-controller.yaml` are mentioned, but the reader has not seen I²C or SPI bindings yet. Add a forward reference: "see Ch 41-42 for the bindings these inherit from."

### Other
- Lab step 4 ("Write your first schema") forward-references Ch 41 ("e.g., one of your own from Chapter 41 onward"). Fine, but the reader cannot do this lab today. Maybe convert to a guided exercise where the reader writes a schema for a fictional GPIO-LED variant that we provide a DTS for.
- §27A.9 references "`grep -r "unevaluatedProperties" Documentation/devicetree/bindings/`" — recommend using `--include='*.yaml'` or the reader gets noise from matching string in Python files under `dtschema/`.

## Ch28 — Kernel startup, traced

### Readability
- Phase-overview ASCII diagram is excellent; keep.
- §28.2 — "Worth pinning:" reads informal/abrupt. Suggest: "Four points worth pinning down:" then the bullets.
- §28.4 — the bullet-list of init calls runs ~50 lines of `name();` followed by a comment. After the first ten, the reader's eyes glaze. Suggest: keep the first 15 inline, then summarize "and roughly 30 more init calls" earlier (which §28.4 already does at the end). Tighter pacing.
- §28.4 "After this, `kmalloc()` works." / "After this, `schedule()` works" / "After this, IRQs from devices can be registered" — repetition of "After this" is intentional cadence and works; keep. Just verify each claim is accurate (see Technical Errors).
- §28.6 — the long `kernel_init` C snippet pasted in full (~80 lines) is too much. Cut to the structurally interesting parts (initmem free, init-path search), drop the routine bookkeeping (do_sysctl_args, pti_finalize).
- §28.7 mapping-table is gold. Highlight it more — make it a numbered figure or call-out.

### MCU-engineer friendliness
- §28.2 — `stext` and `__create_page_tables` need bridging. "Your bare-metal `Reset_Handler` set up SP, zero'd BSS, copied .data. `stext` does the same — plus it builds an early MMU page table (which you've never done because MCUs don't have an MMU) and then *enables the MMU mid-function*. The instruction after MMU-enable runs at a different virtual address than the one before. This is the single most magical line of code in the kernel."
- §28.3 `__mmap_switched` "does the C runtime setup" — bridge: "This is your `__libc_init_array` / SystemInit equivalent: zero BSS, copy initial-data, set up stack. Then it calls `start_kernel` the way your reset handler calls `main`."
- §28.4 — `start_kernel` as "the boss function" — keep, but expand: "Compare to your MCU `main()`: a long sequence of `HAL_Init()`, `SystemClock_Config()`, `MX_GPIO_Init()`, etc. `start_kernel` is the same pattern, just 200 calls deep and with a lot of internal dependency."
- §28.5 — kernel_thread / user_mode_thread / PID 0/1/2 — the MCU reader has *never* dealt with multiple tasks created from inside the kernel. Bridge: "RTOS analogy: `xTaskCreate` from inside the scheduler-startup code. The boot CPU's current stack becomes one of the tasks. The difference: PID 0 (idle) is implicit — it *is* the current execution context after `rest_init` returns, not a separately-created task."
- §28.6 — `kernel_execve` "replaces the calling task's image" is a syscall-mode concept foreign to MCU. Expand: "exec is the single most powerful syscall in Unix — it tears down the calling process's memory map, mmaps the binary at `/sbin/init`, sets the PC to the binary's entry, and returns to user space *as that program*. There is no MCU equivalent because MCUs don't reload programs at run time."

### Missing examples / figures
- After §28.2 add an ASCII showing the ARM virtual-address layout that `__create_page_tables` produces: kernel `_text`/`_etext`/`_data`/`_bss` regions, vector page, identity map area. The reader knows physical address layout from bare-metal but has never seen kernel virtual mapping.
- After §28.4 add a small "subsystem dependency graph": which init step depends on which other one (`mm_init` before `sched_init`, `init_IRQ` before `time_init`, etc.). One ASCII figure beats a paragraph of prose.
- §28.5 — diagram of "PID 0 / PID 1 / PID 2 after `rest_init`": three boxes labelled with their entry function (`do_idle`, `kernel_init`, `kthreadd`), their stack base, the CPU they're running on. Reader needs the visual.
- §28.6 — annotated diagram of the process address space *before* and *after* `kernel_execve` for PID 1 (kernel-only mapping → user mapping + kernel mapping). This is the most under-illustrated transition in the chapter.

### Technical errors
- §28.4 `start_kernel` snippet calls `page_alloc_init()` — in mainline v6.6 the corresponding function is `mem_init_print_info` / `page_alloc_init_cpuhp` (depending on whether you mean the early or the CPU-hotplug init). Verify the exact symbol present in v6.6's `start_kernel`.
- §28.4 same snippet calls `boot_cpu_init()` and `page_address_init()`, then `pr_notice("%s", linux_banner);`. In v6.6 the order has `boot_cpu_init`, `boot_cpu_hotplug_init` (later), `page_address_init`. Check the v6.6 source and reorder.
- §28.4 same snippet calls `mm_core_init()` — verify. The function is `mm_core_init` in v6.6+ (added around v6.2; before that it was `mm_init`). Correct.
- §28.4 same snippet calls `sched_init()` then `radix_tree_init()` then `maple_tree_init()`. In modern kernels `radix_tree_init` was removed (xarray took over) and `maple_tree_init` may not be a public-facing init. Verify against current `init/main.c` and prune the list to what's actually there.
- §28.4 `early_irq_init()` followed by `init_IRQ()` — both exist, order is correct, but `early_irq_init` does the irq_desc array allocation; `init_IRQ` does the GIC probe. Worth a one-line distinction.
- §28.6 `kernel_init` snippet uses `try_to_run_init_process` and four hard-coded paths (`/sbin/init`, `/etc/init`, `/bin/init`, `/bin/sh`). Mainline currently uses `try_to_run_init_process` indeed, and the four paths are correct. Good.
- §28.7 table row "`OF: fdt: Machine model: ...`" mapped to `drivers/of/fdt.c` `early_init_dt_scan` — verify. The exact `pr_info` call is in `drivers/of/fdt.c` `early_init_dt_scan_root` or similar helper, not `early_init_dt_scan` itself. Pin to the exact function.
- §28.7 table row "`Memory: 444184K/524288K available ...`" mapped to `mm/page_alloc.c` `mem_init_print_info` — verify. In v6.6 the function is `mem_init_print_info` in `mm/mm_init.c`, not `mm/page_alloc.c`. Fix the path.
- §28.9 pitfall "`free_initmem` recycles `.init.text` and `.init.data`. Function names like `init_IRQ`, `setup_arch`, `start_kernel` themselves get freed" — `start_kernel` is marked `__init` so yes, it gets freed. Confirm by `objdump -h vmlinux | grep init.text`. Correct.

### Knowledge prerequisites missing
- §28.2 — `safe_svcmode_maskall` is a macro from `arch/arm/include/asm/assembler.h`. The reader has not seen this macro and does not know what "SVC mode" is in ARMv7 (covered briefly in Part I but not in this detail). One sentence: "SVC mode is the ARM-A processor mode the kernel runs in; the bootloader may hand off in another mode (HYP, USR, etc.); this macro forces SVC and masks IRQs."
- §28.2 — `mrc p15, 0, r9, c0, c0` is a coprocessor read of the MIDR. The reader has likely never written `mrc`/`mcr`; explain inline: "ARMv7 coprocessor-15 register access; reads the Main ID Register (MIDR) into `r9`."
- §28.2 `__proc_info_begin..__proc_info_end` — linker-supplied symbols. The reader has not seen the kernel's section-symbol pattern. One sentence on how the linker script `arch/arm/kernel/vmlinux.lds.S` collects all `struct proc_info_list` into one section.
- §28.4 `__init` is used in `asmlinkage __visible void __init start_kernel(void)` — `__init`, `__visible`, `asmlinkage` all unintroduced. Define each in a small sidebar.
- §28.5 `noinline __ref` — `__ref` allows a non-`__init` function to call an `__init` function safely; the reader needs this defined.
- §28.6 `kernel_init_freeable` — vague name, no description of what it actually does. Expand the comment or replace with §-§28.6 sub-bullet.

### Other
- §28.10 "Going deeper" link to "Bootlin's 'Embedded Linux kernel' training material" — verify the link/name; Bootlin has multiple courses with similar names. Pick the right one.
- Lab step 3 — `initcall_debug` is the boot-arg; `printk.devkmsg=on` is unrelated to seeing initcalls. Drop `printk.devkmsg=on` or explain its separate purpose.

## Ch29 — Initramfs from scratch

### Readability
- §29.1 "An **initramfs** is a small filesystem image that the kernel loads into RAM before any 'real' disk filesystem is mounted." — good opening. The next sentence: "The kernel mounts the initramfs as `/`, runs `/init`, and from there `/init` can do whatever it wants — usually pivot to a real rootfs on disk, but for embedded systems the initramfs *is* the rootfs." — too long. Break into two.
- §29.2 — "30 KB. That's roughly the minimum a statically-linked C program reaches." — slightly off; with klibc you get tiny binaries (a few KB). Reword to "roughly the floor for a glibc-or-musl static binary; klibc and stripped assembly can go further."
- §29.3 "Notice the new things" — chatty. "Three new pieces:" lands cleaner.
- §29.4 — the busybox build instructions ("Settings → Build static binary (no shared libs) → [*]") are interleaved with shell commands. Separate into "1. Build busybox", "2. Configure busybox static", "3. Strip", "4. Populate rootfs", "5. Pack cpio" — numbered steps make the lab reproducible.

### MCU-engineer friendliness
- §29.1 — the initramfs concept needs the MCU bridge explicit: "An MCU has no equivalent. Closest: imagine your bootloader copying a separate flash partition into RAM, and your application using that RAM region as 'C: drive' before any SD-card driver has come up. The cpio archive is just how Linux packs that RAM disk's contents."
- §29.2 — "Build statically so we have no library dependencies on the target" — bridge: "Like building your STM32 firmware with `-static` linker option turned on — there's no `libc.so` to dlopen at run time. Linux makes dynamic linking the default and you opt out of it here."
- §29.4 — BusyBox's "applets" via symlinks — the multi-call binary pattern is foreign. Worth one sentence: "BusyBox inspects `argv[0]` at start. If invoked as `ls`, it runs the ls applet; if invoked as `sh`, the shell. One binary, dozens of personalities — saves flash."
- §29.6 init-systems table is helpful but `systemd` "powerful, big, dependency-heavy" undersells *why* it's used. One more sentence on socket activation, journald, dependency-aware service start — gives the MCU reader the context for the Part IX coverage.

### Missing examples / figures
- After §29.1 add an ASCII showing the boot-path with vs without initramfs. Two parallel timelines: "no initramfs → kernel → directly mount /dev/mmcblk0p2 → /sbin/init" vs "with initramfs → kernel → unpack cpio into tmpfs → run /init → /init does pivot_root → mount real disk → exec real init". Visual disambiguates.
- §29.2 add a hex dump of the cpio header bytes (a "newc" header is 110 chars per file entry). Show what the kernel's cpio parser sees byte-for-byte.
- §29.4 — `find . | cpio -o -H newc` produces a flat archive. Show a tree of the busybox-initramfs directory before packing (with the symlinks) and the cpio archive after. Reader needs to see "this directory becomes that file" as one figure.

### Technical errors
- §29.2 `puts("\n*** hello from a one-binary initramfs ***\n");` — `puts` adds its own newline; the explicit `\n` at the end is redundant. Reader will see a blank line. Minor.
- §29.3 `bootz 0x82000000 0x84000000 0x83000000` — verify U-Boot's bootz argument order. Per `cmd/booti.c` / `cmd/bootm.c`, `bootz <kernel-addr> [<initrd-addr>[:<initrd-size>]] [<fdt-addr>]`. The example is correct, but the §29.3 prose says "the second argument is now the initrd address (no longer `-`)" — which is right. Just confirm before publishing.
- §29.4 `mount -t devtmpfs none /dev` — works, but on a kernel built with `CONFIG_DEVTMPFS_MOUNT=y` (which §29.8 recommends), the kernel has already auto-mounted devtmpfs before init runs. Mounting again on top is harmless but redundant. Either remove the line from the rcS or note that the redundancy is intentional for the case where someone builds without `CONFIG_DEVTMPFS_MOUNT`.
- §29.4 `cd initramfs/bin; for app in $(./busybox --list)` — running `./busybox` from the *target's bin dir* may fail on the host if the binary is cross-compiled for ARM. The host can run `./busybox` only via QEMU user-mode emulation or if you happen to be on an ARM host. Replace with: run `--list` on the host using a host BusyBox or hardcode the symlink list.
- §29.4 the inittab `::respawn:-/bin/sh` — the leading `-` on `-/bin/sh` makes the shell a login shell. Worth a note; the reader doesn't know this convention.
- §29.5 `CONFIG_INITRAMFS_SOURCE="/home/you/imx6ull/initramfs.cpio.gz"` — the source can also be a directory or a cpio_list file. Mention briefly.
- §29.8 pitfall "Cpio archives don't error on missing init." — actually `init/initramfs.c` does check that `/init` exists and falls through to the `prepare_namespace` path otherwise. Verify the exact behavior: missing `/init` → kernel tries to mount `root=`; missing `/init` *and* no `root=` → panic with "No filesystem could mount root, tried…". Tighten the wording.

### Knowledge prerequisites missing
- §29.1 "tmpfs" appears without definition. One sentence: "tmpfs is the kernel's in-RAM filesystem (think `ramdisk` but reclaimable and growable). The initramfs lives in a tmpfs the kernel creates at boot."
- §29.1 "cpio" — the reader has likely not used cpio. One sentence on the format ("a sequence of (header, filename, content) records concatenated"), or a forward reference to a "What is cpio?" sidebar.
- §29.2 "musl" and "glibc" — both libc implementations appear. Quick definition: "musl is a smaller, simpler libc; glibc is the desktop default. Cross-compilers tagged `*-musleabihf` use musl. Toolchains tagged `*-gnueabihf` use glibc."
- §29.4 "Settings → Build static binary (no shared libs)" — the reader has never run busybox menuconfig. Cross-reference to Ch 30's menuconfig coverage; the navigation is similar.
- §29.6 "respawn / sysinit semantics" — System V init semantics are unintroduced. One sentence each.

### Other
- §29.7 lab step 5 — "Echo a value to `/sys/class/leds/<your-led>/brightness`" — the reader does not yet have an LED in their DT. Forward-reference to Ch 38 (GPIO chapter) or set up a simulated LED earlier.
- §29.9 "Going deeper" — "klibc — an even smaller libc-replacement than musl, designed specifically for in-kernel-cpio-initramfs static binaries." Correct, but klibc is actually used by some distro initramfs (and is mostly orthogonal to musl). Soften "designed specifically for".

## Ch30 — Kernel configuration deep-dive

### Readability
- §30.1 "The kernel has ~7000 configurable options across hundreds of `Kconfig` files scattered through the source tree." — fine.
- §30.2 — "You'll get a full-screen ncurses interface." — describe what they will see before listing keys. Currently: "From a configured tree: `make ... menuconfig` | You'll get a full-screen ncurses interface. | Navigation:" — three jumps in three sentences.
- §30.5 — "You can read every help text in `menuconfig` and learn nothing useful for hours." — informal, OK for a book in this voice but verify the author wants that tone consistently.
- §30.5 each knob's blurb is structured well; keep.
- §30.6 — "Aggressive trimming" bullet list is good. Add a one-line summary at the end: "Trimmed kernel size: 3.2 MiB. Trade-off: removed audio, USB gadget, debug info."

### MCU-engineer friendliness
- §30.1 — "Kconfig" is the kernel's analog to what the MCU engineer might know from STM32CubeMX or KConfig-style menus in IDE settings. Bridge: "Kconfig is the kernel's equivalent of your IDE's project-options dialog: select features by checkbox; the build system reads those selections and includes/excludes files accordingly. Difference: Kconfig is text-driven, scriptable, and version-controlled."
- §30.2 — "ncurses" is unintroduced jargon. Brief: "ncurses is the terminal-graphics library that draws the menu's box characters; you need no separate install on a typical Linux host."
- §30.5 — `PREEMPT_RT` mentioned but the reader's first impression of "preemption" is the RTOS kind. Bridge: "Linux defaults to non-preemptible kernel code (a syscall runs to completion). PREEMPT_RT changes this so almost every kernel codepath is preemptible — like turning the kernel into an RTOS task itself."
- §30.5 — `NO_HZ_IDLE` "saves power" — bridge: "Like your STM32 stopping the SysTick when going into STOP mode. The Linux scheduler can stop the periodic tick when idle and wake on the next scheduled timer."

### Missing examples / figures
- After §30.3 (the .config file) — show a side-by-side: `defconfig` (terse, ~324 lines) vs `.config` (full, ~2147 lines) headers, so the reader sees the size difference visually.
- After §30.5 — a single visual cheat-sheet listing the twelve knobs with their menu paths and "for our i.MX6ULL: set to X". This is a reference page the reader will revisit; making it scannable matters.
- §30.6 — a before/after `ls -lh zImage` showing the trimmed result. Currently described in prose ("A trimmed image for i.MX6ULL can reach ~3 MB"); show the actual numbers.

### Technical errors
- §30.4 "That `defconfig` file (324 lines vs 2147 for full `.config`) contains *only* the lines that differ from the architecture default." — slightly imprecise. `savedefconfig` strips lines that match Kconfig defaults *and* lines that follow trivially from dependencies. A `defconfig` is the minimal set that, when run through `make defconfig`, reproduces the same final `.config`. Tighten.
- §30.5 PREEMPT_RT description "turns the kernel into a deterministic real-time kernel (Chapter 52A is dedicated to this)" — PREEMPT_RT is *not* hard real-time deterministic in the strict sense; it's *bounded* latency. Soften to "low, bounded latency".
- §30.5 `CONFIG_FEC` menu path — verify the exact menu label. In v6.6 it's "FEC ethernet controller" (not "FEC (Freescale FEC and i.MX6UL/ULL)") in `drivers/net/ethernet/freescale/Kconfig`. The current text suggests the menu label includes "(i.MX6UL/ULL)" which it does not.
- §30.5 "MMC/SD/SDIO card support" → "Secure Digital Host Controller Interface support" → "Freescale eSDHC/uSDHC i.MX controller" — verify exact menu strings (they migrate occasionally).
- §30.6 — "Disable IPv6 / IPv4 sub-features you don't need. TCP / UDP / unicast routing — yes. Multicast routing / fib_rules / netfilter — no. Saves ~500 KB." — disabling `fib_rules` is risky; many distros require it for basic functionality even without netfilter rules. Soften to "if you don't use complex routing/policy".
- §30.7 — "`scripts/config --disable AUDIT`" — verify the symbol; `CONFIG_AUDIT` exists. Correct.
- §30.7 — "Combine multiple defconfigs" subsection is mislabeled: the example combines a *defconfig* with a *single-flag override*, not two defconfigs. Rename "Targeted Kconfig override on a base defconfig".

### Knowledge prerequisites missing
- §30.5 `CONFIG_BLK_DEV_INITRD` mentions "Initial RAM filesystem and RAM disk (initramfs/initrd)" — by Ch 30 the reader knows what initramfs is (Ch 29). Good. But the *option name* implies "BLK_DEV" — explain why a RAM-filesystem option is in the block-device subtree (historical artifact: initrd was originally a block device).
- §30.5 PREEMPT_RT "turns the kernel into a deterministic real-time kernel (Chapter 52A is dedicated to this)" — fine forward-ref; the reader doesn't need depth here.
- §30.6 — disabling "ARM_AT91 / ARM_OMAP / ARCH_BCM" assumes the reader knows these are SoC families. One sentence: "Each ARCH_* is a SoC family. ARCH_MXC is i.MX. The others are AT91 (Atmel), OMAP (TI), Broadcom, etc."
- §30.7 `scripts/config` — useful tool, no prior introduction. Explain it's a shell script wrapper around the `.config` file format that maintains dependency reconciliation.

### Other
- Lab step 4: "Find a driver currently `=y` (e.g., `CONFIG_USB_F_MASS_STORAGE`). Change it to `=m`." — verify USB_F_MASS_STORAGE is `=y` in `imx_v6_v7_defconfig` (it may be `=m` or unset by default; pick a driver that's actually `=y`).
- §30.10 "`Documentation/admin-guide/`" — there's no "Going deeper" link to `Documentation/admin-guide/sysctl/` which is where many runtime tunables live; worth a one-line cross-reference.

## Ch30A — Kernel lifecycle

### Readability
- §30A.1 — table header "Maintainer" then "Maintainer | Release cadence | Lifetime" — table is dense; consider one column at a time as separate sub-tables, or annotate the table with which columns matter for "decisions".
- §30A.2 — "The day 6.6 ships, 6.7-rc1 is already absorbing the next merge window." — vivid, keep.
- §30A.4 — table "LTS | Released | Support ends | Notes". The 6.6 row says "Default LTS pick for new 2024+ products" — the book is dated 2026; phrasing should be "as of writing" because 6.12 LTS is the current default by 2026.
- §30A.6 — the decision-framework flowchart is the highlight of the chapter. Good.
- §30A.7 — "The 4.1.15 trap is real." — informal-but-effective. Keep.

### MCU-engineer friendliness
- §30A.5 — vendor BSP "Thousands. Drivers for proprietary silicon" — bridge: "Like the STM32CubeMX HAL bundle — vendor code that lives outside your project but you depend on. Difference: NXP's BSP carries kernel patches, not just user-facing HAL. So you're forking the OS itself."
- §30A.6 — flowchart applies the same maintenance-economics lens an MCU engineer applies to "do we stay on this STM32F4 BSP or migrate to F7?" Make the parallel explicit.
- §30A.7 "4.1.15 trap" — the reader probably has not lived through inheriting a five-year-old MCU BSP. Add the MCU parallel: "Imagine inheriting an STM32F4 firmware built against StdPeriph 1.4.0 from 2014. The HAL is gone. The toolchain is ancient. New libraries assume CMSIS 5. Migration is mandatory. Same situation, kernel scale."

### Missing examples / figures
- §30A.1 — add a horizontal timeline showing the release cadence: a horizontal axis (2018 → 2030), with bars for each LTS (when released, when EOL). Visualises "your product life vs LTS coverage" at a glance.
- §30A.6 — the decision-framework flowchart is text-only. Render it as ASCII with proper branches.
- §30A.8 worked examples — add a fourth scenario: "Hobbyist Yocto-based home-automation hub, 5-year product life, OTA-managed." This is the gap between B and C: a real product, but not industrial, and Yocto-curated. Useful for the maker reader.

### Technical errors
- §30A.4 table row "5.10 | Dec 2020 | Dec 2026 | Android 11/12 ABI baseline" — verify the EOL date. As of 2026, 5.10 LTS support window has been extended in some plans. Pin exact dates.
- §30A.4 "The 'extended LTS' track (sometimes called 'Civil Infrastructure Platform' or CIP)" — CIP is one specific extended-LTS effort. There are others (Greg KH's "super-long-term-support" stable trees, vendor-managed extended LTS). Tighten the wording or clarify CIP is one of several.
- §30A.5 "NXP about quarterly" — verify the cadence; NXP's `linux-imx` cadence is closer to per-Yocto-release (2-3 times per year). Pin precisely.
- §30A.5 "github.com/nxp-imx/linux-imx" — confirm the canonical repo URL. NXP has moved between several Git hosts.

### Knowledge prerequisites missing
- §30A.4 "CIP" appears with one expansion ("Civil Infrastructure Platform"). Add a one-line "industrial-Linux consortium funded by Toshiba, Siemens, Hitachi etc.; backports security fixes for 6+ years on selected LTS releases."
- §30A.5 "Yocto layer (`meta-imx`)" — Yocto and `meta-imx` not yet introduced in Part IV. Forward-reference to Part V/VI.
- §30A.8 scenario B mentions "ISP driver" and "ISP" — image-signal-processor. Reader from MCU world may not know. Define inline.
- §30A.11 "drm/kernel-doc-rst discussions" — appears to be a typo or copy-paste error; the symbol doesn't match anything. Either remove or correct to whatever was intended.

### Other
- §30A.10 pitfalls bullet "Our customer requires the vendor BSP." — strong opinion phrased as fact. Soften to "Sometimes a customer mandates the vendor BSP. Push back when the technical justification is weak; accept it when contract or compliance demands it."
- The chapter sits between Ch 30 (config) and Part V. The chapter's title says "Kernel lifecycle" but content is also a strategic-decision-framework chapter. Consider re-titling to "Kernel lifecycle and selection: which kernel ships?" to set expectations.


---

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


---

# Part VIa — Driver foundations + subsystems: Review

## Cross-cutting observations

- **Mainline kernel API drift (critical).** Multiple chapters use APIs that have changed signatures in the kernels you're likely targeting (5.15 LTS, 6.1 LTS, 6.6 LTS, 6.12 LTS). The most damaging ones:
  - `class_create(THIS_MODULE, "name")` — the `owner` argument was removed in **6.4** (commit 1aaba11da9aa). On 6.6+ the call is `class_create("name")`. Ch 38, Ch 40 comparison table, and Ch 41 references all show the old form. State once which kernel the book targets and add a one-paragraph "API drift" note pointing readers at the new signature when they're on >=6.4.
  - `i2c_driver.probe` lost its `(struct i2c_client *, const struct i2c_device_id *)` two-arg signature in **6.3** (commit b8a1a4cd5a98 made `probe_new` the canonical, then renamed). Modern kernels expect `int probe(struct i2c_client *client)`. Ch 46 uses the old two-arg form everywhere. The AT24/BME280 reference drivers you point to are now single-arg.
  - `.remove` returning `int` for `platform_driver`/`i2c_driver` was changed to `void` in 6.11 (and `remove_new` introduced earlier as the transition mechanism). Ch 39, Ch 46 still show `return 0;` from remove. Note this for readers on bleeding-edge kernels.
  - SPI's `.remove` is already `void` in your Ch 47 example — good — but make this consistency explicit.
- **MCU-bridge sidebars are inconsistent.** Ch 36 has a strong MCU-vs-Linux table; Ch 37 starts the user/kernel-boundary discussion well; Ch 41 nails the FreeRTOS-vs-kernel-context framing in §41.1. But Ch 42 (sleeping), Ch 43 (IRQs), Ch 46/47 (I2C/SPI) jump straight into Linux abstractions with no MCU mental-anchor. Promise from the persona is that *this part* is THE goal — every new concept needs a 2-3 sentence "in MCU/RTOS you would have… in Linux you…" callout.
- **No driver-skeleton callout box.** A persistent reader-friendliness improvement: each chapter would benefit from a tiny "shape of every driver in this category" box at the top, like:
  ```
  init → register subsystem object → callbacks fire → unregister → exit
  ```
  …with the chapter's actual function names plugged in. The MCU dev needs this scaffolding to know what's about to land.
- **`THIS_MODULE` is used dozens of times but never explained.** First mention is Ch 37 §37.4 (`.owner = THIS_MODULE`); first explanation is missing. Add one sentence in Ch 36 when introducing `module_init`: "`THIS_MODULE` is a per-module token, defined by the Kbuild scaffolding, that frameworks use to pin module refcounts so you can't be unloaded while the kernel still has a pointer to your code."
- **`dev_info` vs `pr_info` switch happens silently.** Ch 36 establishes `pr_info`; Ch 39 onwards uses `dev_info(&pdev->dev, ...)` without ever introducing the family. Add 2 lines in Ch 39 §39.3: "Once you have a `struct device *`, prefer `dev_info(dev, ...)`. It prefixes the log line with the device name automatically — `dev_info(&pdev->dev, "ready")` prints `linuxlearn-blinker 0.gpio: ready` instead of just `ready`."
- **`container_of` appears in Ch 37 but is never properly explained.** "Compile-time trick" is the only hint. The MCU reader has never seen offsetof-based pointer math. A 4-line diagram showing `cdev` member inside `hello_dev` and the pointer-subtract is warranted.
- **Locking-context cross-references are weak.** Ch 41 introduces sleeping/atomic distinction. Ch 42 uses `mutex_lock` in driver code. Ch 43 forbids it. Ch 44 says "use `_cansleep` in process context." Ch 46 silently uses `i2c_transfer` (sleeps) inside what could be IRQ-context handlers in some examples. A single "context-rules" sidebar in Ch 41 that you cross-link from every later chapter would clean this up. Suggested name: *"the sleep/atomic compact"*.
- **No upfront DT phandle / `&label` syntax recap.** Chapters from 39 onwards rely heavily on `&i2c1`, `&pwm1`, `&gpio4`, etc. Even the persona who got through Part V may have lost this. One sentence each in Ch 39 and Ch 44 reminding "`&foo` references a node labelled `foo:` elsewhere in the DT" would help.

## Ch36 — Your first kernel module

### Readability
- §36.1 opening "If your last decade was MCU work" — strong hook, keep.
- "Twenty-some lines. Let's go through each." (after the code block at line 60) — change to "About twenty lines. Let's walk through them." ("twenty-some" reads as "approximately twenty plus a few" and is informal/odd for non-native readers).
- §36.3 "The kernel build system (Kbuild) is invasive — it generates per-module ELF sections" — "invasive" has negative connotation; consider "deeply involved" or "tightly coupled to your build."
- §36.6 final paragraph "Crank it up" — informal; use "Increase it" or "Raise it."
- §36.8 Pitfalls bullet on `__init` data: "Compile warning: 'section mismatch.'" — quote the actual modpost warning text: `WARNING: modpost: section mismatch in reference: hello_init (section: .init.text) -> some_runtime_fn (section: .text)` so readers grep-match what they'll see.

### MCU-engineer friendliness
- §36.2 explanation of `MODULE_LICENSE`: great. Add one sentence on *why* `EXPORT_SYMBOL_GPL` exists at all — "the kernel community uses license-tagged symbols as a contract: GPL symbols are stable kernel internals; non-GPL symbols are the stable user-facing kernel API. Without GPL on your module, you only see the user-facing API."
- §36.5 module parameters: missing a bridge — "this is the Linux equivalent of `#define CFG_FOO 1` in your firmware, except you can change it after boot without recompiling." That one sentence saves three paragraphs of explanation.
- §36.6 `printk` table — bridge: "MCU `printf`-over-UART is roughly `pr_warn` level. The level system lets you keep low-priority messages in the dmesg ring buffer without flooding the console — useful when you don't have a fast UART."

### Missing examples / figures
- After §36.2 table headers, show a small "anatomy" ASCII diagram of `hello.ko` listing the sections (`.text`, `.init.text`, `.exit.text`, `.modinfo`, `__versions`) so the `__init`/`__exit` story has visual anchor.
- After §36.3 build log, a one-line diagram of the link relationship: `hello.o + Module.symvers (from kernel) → modpost generates hello.mod.c → hello.mod.o + hello.o → hello.ko`.
- Add a "what happens at `insmod`" mini-diagram between §36.3 and §36.4: ELF on disk → `init_module()` syscall → kernel allocates module address space → relocations applied → `module_init` callback invoked.

### Technical errors
- §36.2 "Stack is ~16 KB and shared with whoever called you" — ARM32 kernel stack is **8 KB by default** (`THREAD_SIZE_ORDER=1`, 2 pages, 4KB pages). 16 KB is x86_64/arm64. Either qualify or state "8 KB on i.MX6ULL." Ch 37 §37.9 even contradicts §36.2 by saying "16 KB on i.MX6ULL (sometimes 8 KB)" — fix both to "8 KB on ARM32 i.MX6ULL with `CONFIG_4KSTACKS`-equivalent (the default)."
- §36.2 "`module_init(hello_init)`. This isn't a function call — it's a macro that expands to a special section entry" — slightly misleading. It expands to `__inittest`/`init_module` aliasing or to an `__initcall` entry (for built-in). It's worth saying "for a `.ko`, it aliases `hello_init` to the symbol `init_module`, which the loader looks up by name."
- §36.3 `vermagic` example shows `mod_unload modversions ARMv7`. Real i.MX6ULL vermagic also typically includes `preempt` / `preempt_rt` / `mod_unload modversions ARMv7 p2v8`. Pull the actual string from a built kernel rather than a synthesized one.
- §36.6 console-loglevel table is **off by one** in the framing: "console shows messages with priority **lower than or equal to** the first number" — actually messages with level **strictly less than** the console_loglevel are printed. With `4 4 1 7`, levels `0..3` print; `4..7` do not. The text says "0–3 print … 4–7 only go to the ring buffer" which agrees in outcome — but the rule stated is "lower than or equal to" which would include 4. Reword to "strictly less than."

### Knowledge prerequisites missing
- `THIS_MODULE` — see cross-cutting note above; introduce in §36.2 alongside `MODULE_LICENSE`.
- `GPF_KERNEL`/`GFP_ATOMIC` — `kmalloc` is mentioned in the MCU/Linux table without GFP flags. A footnote pointing to Ch 37 would suffice.
- `.modinfo` section — `modinfo` is shown without explaining that the kernel reads ELF section data. Brief sentence: "All `MODULE_*` macros build entries in a special `.modinfo` ELF section; `modinfo` is just an ELF reader."

### Other
- Lab #5 says crashing the module on i.MX6ULL is "recoverable" — qualify: a NULL-deref in a kernel module *can* be recoverable on some configs but is **not guaranteed**. It's quite common for ARM32 to panic on a kernel-mode page fault unless `CONFIG_BUG_ON_DATA_CORRUPTION` and friends are set. Suggest: "Often recoverable on i.MX6ULL; sometimes panics. Have a serial console and a reset button ready."

## Ch37 — A character driver, by hand

### Readability
- §37.1 ASCII flow diagram is excellent; keep as-is.
- "It's the most readable way to handle error paths in C — far better than nested `if`s." — slightly preachy; tone down to "It's the kernel's idiomatic error-path style; once you read a dozen drivers it becomes the natural pattern."
- §37.6 table row "Multiple `cat`s in a row read the same 5 bytes each time" — confusing because there's also a "Two `cat /dev/hello > x &` in parallel" row. The first sentence in §37.5 says "Multiple `cat`s in a row read the same 5 bytes each time — because our `read` checks `*ppos >= buf_len` and signals EOF appropriately, then `cat` reopens and starts from `*ppos = 0` next time." This is reasoning about *sequential* `cat` invocations; reword to "Each new `cat` invocation gets a fresh open (so `*ppos` resets to 0); within one `cat`, the first `read` returns 5 bytes and the second returns 0 (EOF)."

### MCU-engineer friendliness
- §37.4 Idea 1 (`container_of`): badly missing the MCU bridge. The MCU dev has never used embedded-struct-with-recover-the-parent. Add a small diagram:
  ```
  struct hello_dev {
      struct cdev cdev;   ← inode->i_cdev points HERE
      ...
  };
                        ↑ container_of subtracts offsetof(cdev) to recover &hello_dev
  ```
  Two lines of explanation: "MCU equivalent: imagine you have `&task->state_field` and need `&task` — `container_of` does that with just compile-time offsetof math."
- §37.4 Idea 2: critical MCU bridge missing on `__user`. The MCU has no MMU and no separate address space. Add a paragraph: "In MCU/RTOS, your firmware sees one flat address space — `memcpy(user_buf, kernel_buf, n)` just works. In Linux, user-space and kernel-space live in *different* page tables. Even though the kernel can technically reach into user memory, *some pages may not be mapped right now* (paged out, lazy-allocation, COW), and the kernel must check permissions. `copy_to_user` does the lookup, brings pages in if needed, and uses the user-side mapping. A raw `memcpy` may oops the kernel."
- §37.4 Idea 3 (locking) mentions `mutex_lock_interruptible` but the MCU dev doesn't know what "interruptible" even means in this context. Add 2 sentences linking to FreeRTOS: "Think of `taskENTER_CRITICAL` (FreeRTOS) — but instead of disabling IRQs, a mutex puts the *waiting* task to sleep. `_interruptible` means: if Ctrl-C fires while sleeping, the wait function returns an error so the syscall can be cleanly aborted. RTOS analogue: an `xSemaphoreTake` with `INCLUDE_xTaskAbortDelay`."
- §37.4 Idea 4 (goto cascade): the MCU dev was taught `goto` is evil. Add one defensive sentence: "Yes, this is `goto`. The kernel coding style explicitly endorses this pattern; it's the only way to keep cleanup ordered correctly without RAII or exceptions. Read it as 'jump to the cleanup that's appropriate at this allocation depth.'"

### Missing examples / figures
- After §37.3, add a 6-line minimal `hello_fops` struct with each callback **labelled** in a comment with what it represents (`.open = ... // called once per fd creation`, etc.). The full driver is shown next, but the reader benefits from seeing the bare `file_operations` first.
- Diagram in §37.4: kernel→driver call stack for one `write()` syscall, with each frame's context and what's safe to do at each level.
- After §37.5 demo, a `ls -l /sys/class/...` or `cat /proc/devices` shot. Currently §37.5 jumps to §37.6 testing without showing the driver's footprint in sysfs/procfs.

### Technical errors
- §37.2 "12 bits major, 20 bits minor" — correct.
- §37.4 `cdev_init(&mycdev, &my_fops)` then `mycdev.owner = THIS_MODULE`. Setting `cdev.owner` *after* `cdev_init` is fine, but the more common idiom is to set it via `cdev_init` itself which already pulls `owner` from `&my_fops.owner`. Mention that since `hello_fops.owner = THIS_MODULE` is already set, the explicit `mycdev.owner = THIS_MODULE` line is redundant. (Not wrong, just noise.)
- §37.7 paragraph "The device file disappears if /dev/ is tmpfs (almost always true; remember Ch 32)." — This is misleading. The issue with `mknod` isn't that tmpfs makes it disappear *automatically*; it's that `/dev` is tmpfs which means **rebooting** wipes the manually-mknod'd node. Reword: "On a tmpfs `/dev`, the node disappears on reboot — you'd need to `mknod` again every boot. Hot-plug agents (udev/mdev) fix this in Ch 38."
- §37.9 "Kernel stacks are 16 KB on i.MX6ULL (sometimes 8 KB)" — see Ch 36 note; ARM32 default is **8 KB**, not 16 KB. Reverse the parenthetical: "8 KB on ARM32 i.MX6ULL (16 KB on x86_64/arm64)."

### Knowledge prerequisites missing
- `IS_ERR` / `PTR_ERR` are not yet introduced in Ch 37 (they appear in Ch 38). Ch 37 uses them implicitly via Knowing-where-to-go but is OK — fine, *but* Ch 38 should introduce them with a sentence: "Linux kernel functions that return `void *` (where `NULL` is a valid 'no such thing' result) signal errors by *casting* a negative errno into the pointer. `IS_ERR(p)` checks the high bits; `PTR_ERR(p)` extracts the errno. Compare to MCU code returning `(void *)-1` or `(void *)NULL` — Linux uses the high address range of pointers as a side-channel."

### Other
- Pitfall on `THIS_MODULE` in `cdev.owner` is excellent — keep.
- §37.10 references LDD3 Chapter 3 — note that LDD3 covers kernel 2.6 era; many APIs in LDD3 are now deprecated (`class_simple_*`, `register_chrdev` legacy). One sentence warning: "Read for the *concepts*; cross-check API names against current kernel before copying code."

## Ch38 — Auto-creating /dev nodes

### Readability
- §38.1 pipeline ASCII is excellent.
- §38.2 "Take the driver from Chapter 37 and add three lines." — actually adds quite a bit more (struct fields, init lines, exit lines, cleanup labels). Reword: "Take the Ch 37 driver and add a class, a device, and matching cleanup labels — about a dozen lines."
- §38.3 final paragraph "(`echo add > uevent` re-triggers — useful for replaying events on a system that booted before udev was running.)" — keep but move out of parens; this is genuinely useful info that the reader will want to find again.

### MCU-engineer friendliness
- §38.1 critical bridge: the MCU dev has no concept of a hot-plug event. Add: "MCU equivalent: there isn't one. The closest analogy is a USB-host stack on a microcontroller that emits 'device attached' callbacks — except in Linux, *every* device, whether hot-pluggable or not, goes through the same notification system. This means a tool sitting in user-space gets the same event whether you `insmod` a driver, plug in a USB stick, or boot the system."
- §38.3 "subsystem framework instead" — Ch 38 hints that "LED → leds; RTC → rtc" without saying which chapter covers them; add forward references explicitly.

### Missing examples / figures
- Before/after sysfs comparison: `find /sys/class/hello -type f` after probe shows the new attributes; this concretises the "shadow of sysfs" claim.
- After §38.2 cleanup code, show the full updated init function with the cleanup labels so the reader sees the goto-cascade extension end-to-end. Currently only the new lines are shown without the cascade context.
- Diagram for §38.5 multi-device: show a tree
  ```
  hello (class)
    ├── hello0  (minor 0, cdev #0)
    ├── hello1  (minor 1, cdev #1)
    ├── hello2  (minor 2, cdev #2)
    └── hello3  (minor 3, cdev #3)
  ```
  …and which struct member holds what.

### Technical errors
- **`class_create` signature: critical.** Throughout the chapter you use `class_create(THIS_MODULE, "hello")`. As of kernel **6.4** the `owner` argument is gone — it's now `class_create("hello")`. Either pick a target kernel version explicitly and stick to that signature, or write a note: "Kernel 6.4+ removed the `THIS_MODULE` argument. The macro magic in modern kernels means `class_create(THIS_MODULE, name)` no longer compiles in some configurations — use `class_create(name)` if you see `error: too many arguments to function 'class_create'`."
- §38.6 `device_create_file` is mentioned alongside `sysfs_create_group` but `device_create_file` is technically deprecated in favor of `default_attrs` / `groups` in `device_attribute_group` set on the class at registration time. Modern style: set `class->dev_groups` before `class_create`, and the core auto-creates attributes. Mention the deprecation, even if you keep `device_create_file` as the introductory pattern.
- §38.6 `sprintf(buf, "loaded\n")` — should be `sysfs_emit(buf, "loaded\n")` in modern kernels (since 5.10). `sysfs_emit` is bounds-checked; `sprintf` is not. Update or note the modern replacement.
- §38.8 Pitfall "Calling `device_create` before `cdev_add`. Device node appears but `open` on it returns `-ENXIO`" — the actual symptom on most kernels is that the open *races* with cdev_add: usually `-ENXIO`, sometimes `-ENODEV`. Mention both.

### Knowledge prerequisites missing
- `IS_ERR`/`PTR_ERR` — see Ch 37 note. Introduce here with at least one sentence before they appear in the code block.
- `kobj` — appears in `&dev->kobj` for `sysfs_create_group` (line 334 area). Briefly: "Every `struct device` embeds a `struct kobject` — the sysfs object model's atom. `&dev->kobj` is how you say 'the sysfs directory belonging to this device.'"
- `DEVICE_ATTR_RW` is used without explaining the wrapper around `dev_attr_state` it produces. The naming convention (the `dev_attr_*` global) trips first-time readers.

### Other
- §38.4 udev rule example uses `KERNEL=="hello"` — correct, but readers who copy-paste with a custom name will often wonder why nothing happens. Add: "After editing rules, run `udevadm control --reload && udevadm trigger`. If still nothing, `udevadm monitor` shows the events the rule is seeing."
- §38.8 Pitfall on race between insmod and udev — good, but mention that the cleanest fix is `udevadm settle --timeout=5` in a script, OR (for embedded) just put your test in a service file with `After=systemd-udev-settle.service`.

## Ch39 — Platform drivers + device tree

### Readability
- §39.3 "Let's pull apart the four interesting pieces." — Pieces A, B, C, D structure is great.
- §39.5 "Useful in development … Also useful in production for power-saving" — overlong sentence; split.
- §39.7 "A driver's `probe()` may depend on something that isn't ready yet — e.g., the PMIC regulator the driver wants hasn't probed itself." — the MCU dev has no concept of "PMIC" + "regulator" + "probed itself." Either swap to a more relatable example ("the clock source isn't registered yet") or define PMIC in passing.

### MCU-engineer friendliness
- §39.1 "the kernel doesn't probe address ranges blindly looking for hardware (that's how PC BIOSes work, and it doesn't scale to SoCs with no buses to enumerate)" — good bridge from PC world. Add the MCU bridge: "On an MCU, your firmware *knows* its own peripherals because you wrote `#include <stm32f4xx.h>` with the base addresses hardcoded. Linux uses DT for the same job, but at runtime, so one kernel image can run on many boards."
- §39.3 "the kernel walks the DT, finds matching nodes, and invokes the driver's `probe()` once per match" — explain the MCU equivalent: "Think of it as: `module_init` gives you 'kernel just loaded this code,' but `probe` gives you 'kernel just found a *device* this code knows about.' In RTOS terms, `module_init` is `void main()`; `probe` is `int driver_init(struct hardware *)`."
- §39.3 Piece C `devm_*` — strong content; add an MCU bridge: "In bare-metal you'd manually pair every `malloc` with a `free`. `devm_kzalloc` is closer to a C++ RAII pattern or scope-bound allocation: the kernel auto-frees when the device goes away. This is the single biggest 'feels like modern code, not C' moment in the kernel."

### Missing examples / figures
- A driver-vs-device-vs-bus diagram between §39.1 and §39.2 would help. Showing:
  ```
  platform_driver "demo"
       ↑    .of_match_table = [{ "linuxlearn,demo" }]
       │
       │  matched by platform_bus
       │
       ↓
  platform_device "demo@1000"
       └── dev.of_node → DT node @ /demo@1000
                          compatible = "linuxlearn,demo"
                          reg = <0x1000 0x100>
  ```
- §39.6 lists six DT-reading APIs without showing how they connect to the DT node's structure. A 3-line example DT alongside the C code would tie it together.
- After §39.4 "Verify in sysfs" output, add a tree showing the platform-bus hierarchy in `/sys`:
  ```
  /sys/bus/platform/
    drivers/demo/      ← the platform_driver
    devices/demo@1000/ ← the platform_device
  ```
  with arrows pointing both directions.

### Technical errors
- §39.3 `platform_get_resource(pdev, IORESOURCE_MEM, 0)` followed by `devm_ioremap_resource(&pdev->dev, res)` — modern kernels prefer **`devm_platform_ioremap_resource(pdev, 0)`** which combines both into one call. Mention it in Going Deeper or as a "modern shortcut" sidebar.
- §39.3 `pdev->dev.of_node->name` — `of_node->name` was deprecated in 4.16 era and removed/changed in some configs. Use `of_node_full_name(pdev->dev.of_node)` or just `dev_name(&pdev->dev)`. The probe log will look slightly different but be more robust.
- §39.3 `static int demo_remove(struct platform_device *pdev)` returning `int` — on kernels 6.11+, platform driver `.remove` returns `void` (and a transitional `.remove_new` was added in 6.5). Add a note.
- §39.7 `if (PTR_ERR(priv->vcc) == -EPROBE_DEFER) return -EPROBE_DEFER;` followed by `dev_err_probe`. This block is logically backwards: `dev_err_probe` *already* handles `-EPROBE_DEFER` silently, so the manual check is redundant. The block should just be:
  ```c
  if (IS_ERR(priv->vcc))
      return dev_err_probe(&pdev->dev, PTR_ERR(priv->vcc), "no vcc regulator\n");
  ```
  The text correctly says so in the next paragraph but the code block contradicts itself. Drop the manual check.
- §39.9 "Driver and device names with hyphens vs underscores" — the kernel itself doesn't care; some *tools* (`modalias`, `depmod`) do, and the *convention* is hyphens in `compatible` and either in `.name`. Slightly stronger phrasing would help: "Stick to lowercase letters, digits, and hyphens for both `.name` and `compatible`. Underscores are tolerated but not idiomatic."

### Knowledge prerequisites missing
- `regulator`/`clock`/`reset` references in §39.6 — first time these appear without forward references. Add: "We'll meet the clock framework in Ch 50A (clocks) and the regulator framework in Ch 51B (power management); for now treat them as 'subsystem APIs that hand you a handle and let you turn things on/off.'"
- The `phandle` concept — mentioned via `<&clks IMX6UL_CLK_GPIO1>` in §39.1 but not explained. Cross-link to whichever DT chapter (presumably Ch 27) introduces phandles.

### Other
- §39.5 manual bind/unbind: excellent feature to demonstrate. Add one line: "The `unbind/bind` files require that the driver and device names be exact; an extra newline from `echo` is what `bind` expects (it strips it)."
- §39.7 shutdown vs remove: clarify that `shutdown()` runs in **process context** but should be *fast*, not "atomic context." Atomic-context shutdown handlers would be exceptional. Reword: "It can sleep, but the whole system is waiting for it — keep it under tens of milliseconds."

## Ch40 — The misc framework

### Readability
- Tight, clean chapter. Minor: "Six lines to register, one to deregister." — quantify the comparison more clearly. The Ch 37 version was ~30 lines in `init` excluding cleanup; the misc version is ~6 lines total. Saying "About 30 lines collapsed to 6" is more vivid.
- §40.5 comparison table — good summary; consider adding a row for "what /sys/class entry appears" to make the trade-off concrete.

### MCU-engineer friendliness
- §40.1 "Use misc when..." — give one MCU-friendly framing first: "Misc is the 'I just need a /dev/ node, don't make me think about classes' shortcut. In bare-metal you'd write a single read/write function. Misc lets your Linux code be almost that small."

### Missing examples / figures
- Add `ls -l /dev/hello` and `ls -l /sys/class/misc/hello` side-by-side to show what the user sees, mirroring Ch 38's approach.
- A diagram comparing the lifecycle of a manual chardev (alloc region → cdev_init → cdev_add → class_create → device_create) vs misc (misc_register) would let the reader see the collapse visually.

### Technical errors
- §40.3 example struct is fine; one small note: setting `.mode = 0660` directly in the struct works, but the kernel framework's preferred path is **a class-level `devnode` callback** (mentioned briefly in Ch 38). Either method works for misc; just mention that the misc layer handles the mode field for you.
- §40.4 lists `loop-control`, `watchdog`, `hwrng`, `rfkill` as misc — all correct. Mention that `/dev/loop-control` minor is 237, `/dev/watchdog` is 130 (reserved minors in `include/linux/miscdevice.h`) — readers reading that header will find a table.

### Other
- §40.6 Lab #3 "Combine misc + platform driver" — this is the canonical embedded chardev pattern and deserves more space. Consider expanding into a small worked example showing the misc-inside-probe pattern fully, not just as a lab exercise.

## Ch41 — Concurrency in the kernel

### Readability
- §41.1 opener is excellent — directly contrasts MCU loop with Linux SMP.
- §41.2 three-question framework is fantastic and is the right pedagogy.
- §41.4 "While you hold a spinlock, the holding CPU has IRQs disabled (in the IRQ-safe variant)" — the bracketed qualifier matters but reads as an afterthought. Restructure: "A bare `spin_lock`/`spin_unlock` only disables preemption. The `_irq` variants additionally disable IRQs on the holding CPU. The reason for the variants is...".
- §41.9 "Lockdep — your friend" is short and breezy — keep, but add a one-line example of what a lockdep splat looks like (just the first 5-6 lines) so readers know what to expect.

### MCU-engineer friendliness
- §41.1 — best MCU bridge in the chapter. Other sections should match this energy. Specifically:
  - §41.4 spinlocks vs MCU `taskENTER_CRITICAL`: explicit mention. "FreeRTOS's `taskENTER_CRITICAL` disables interrupts and preemption on a single-core system. A Linux spinlock is similar, but on SMP must additionally lock out other CPUs. `spin_lock_irqsave` is the closest analogue — it disables IRQs (single-core protection) *and* acquires the bus lock (multi-core protection)."
  - §41.5 mutexes vs RTOS semaphores: "FreeRTOS `xSemaphoreTake(mutex, portMAX_DELAY)` ≈ Linux `mutex_lock`. The RTOS version blocks the calling task and lets the scheduler pick another; Linux mutexes do the same."
  - §41.10 worked example: an MCU dev with a SPSC ring buffer might think "I just need atomic head/tail pointers." Add a sentence: "On a single-core MCU, you can sometimes avoid locks entirely by carefully ordering head/tail updates. Linux on SMP makes that hard — the cost of a single `LDREX/STREX` round-trip across CPU caches dominates. Spinlocks are simpler and almost always fast enough."

### Missing examples / figures
- §41.4 Variants table is comprehensive but lacks a "what gets disabled" column. Suggested:
  | Variant | Preempt off | IRQs off | When |
  |---------|-------------|----------|------|
  | `spin_lock` | yes | no | process only |
  | `spin_lock_bh` | yes | softirqs only | process + softirq |
  | `spin_lock_irq` | yes | yes | known IRQs-on context |
  | `spin_lock_irqsave` | yes | yes (save state) | any context |
- §41.7 RCU example: a diagram showing "writer publishes new pointer; readers in flight still see old; synchronize_rcu waits; old freed" would clarify the magic. Currently it's a wall of code.
- §41.10 ring buffer: a tiny state diagram showing head/tail movement with one producer + consumer would help. The MCU dev knows this from their FreeRTOS queue code; show the parallel.

### Technical errors
- §41.4 "On a single-core CPU (the i.MX6ULL), the per-CPU array has one slot..." (in §41.8) — actually i.MX6ULL is single-core but the *kernel* may still be built `CONFIG_SMP=y` (and usually is, on Linux distros). Per-CPU still uses one slot. The text says this; the lab note in 41.11 #4 says "the test is harder to write on a single-core i.MX6ULL." Slightly contradictory tone — clarify that the *semantics* are the same, only the *demonstrable speedup* is invisible on single-core.
- §41.5 "Mutexes have one nice property over semaphores: the kernel tracks who holds them." — correct, but worth adding: "This is why kernel mutexes are owner-aware and disallow being released by a thread other than the holder; counting semaphores (`struct semaphore`) don't have this." The reader who has used FreeRTOS counting semaphores would otherwise be confused.
- §41.7 `rcu_dereference_protected(cur_config, lockdep_is_held(&write_lock))` — `write_lock` is referenced but never defined in the example. Add `static DEFINE_MUTEX(write_lock);` so the snippet compiles in spirit.
- §41.12 "Linux mutexes are **not recursive**" — correct. Worth strengthening: "Even checking is forbidden — `mutex_is_locked()` returns whether *anyone* holds it, not whether the current task does. To attempt a recursive-like pattern, manage a counter alongside the mutex."

### Knowledge prerequisites missing
- "Softirq" introduced before being defined. §41.2 talks about "Process + softirq/tasklet → spinlock with `_bh` variant." Tasklet is hinted at but never defined until Ch 43. Add a one-paragraph definition: "A softirq is a kernel-internal mechanism for 'do this work later, but soon, at an interrupt-like time.' Tasklets are softirqs scheduled per-instance. Work queues are softirqs scheduled to kernel threads. You'll meet them properly in Ch 43; for now: 'softirq context = not process context, but not hard-IRQ context either.'"
- `ldrex/strex` — mentioned without explanation. The MCU reader who knows ARMv7 will recognize them, but a one-liner — "ARM's load-exclusive/store-exclusive pair, the foundation of all atomic operations on ARM" — is useful.

### Other
- §41.12 Pitfall on `volatile` is excellent and worth keeping — many MCU devs have `volatile` everywhere.
- §41.8 per-CPU section ends with "Per-CPU data is brilliant when reads are rare relative to writes (the opposite of RCU's sweet spot)." — actually per-CPU data is for cases where **writes are local and reads are rare-but-aggregating**, regardless of frequency. The contrast to RCU is reads-vs-writes. Tighten the framing.

## Ch42 — Sleeping, waiting, polling

### Readability
- Strong chapter overall.
- §42.1 "Both eventually rest on the same kernel primitive: a **wait queue**." — concise; keep.
- §42.5 list of sleep/delay functions: this is a critical reference and should be elevated to a "Cheat sheet" callout box. Currently buried inside a flowing paragraph.
- §42.6 task state machine: useful but could be moved earlier (before §42.2's "the macro sets state to `TASK_INTERRUPTIBLE`" comment, which is otherwise opaque).

### MCU-engineer friendliness
- §42.1 — *missing* the MCU bridge entirely. The MCU dev knows `vTaskDelay`, `xQueueReceive`, `xSemaphoreTake` (block until). Add: "In FreeRTOS, a task blocks via `xQueueReceive(queue, &item, portMAX_DELAY)` — the scheduler removes it from the ready list until something puts an item in. Linux wait queues are exactly this, generalized: the 'queue' is just a list of sleeping tasks, the 'condition' is whatever predicate you write, the 'unblock' is the producer calling `wake_up`."
- §42.2 wait_event_interruptible variants — the MCU dev needs to map this to RTOS task states. Add a column to the variant table: "RTOS analogue" with rows like "vTaskDelay-with-abort," "xQueueReceive-with-timeout," etc.
- §42.5 `udelay` / `mdelay`: critical bridge. "These are the Linux equivalents of HAL_Delay(ms) — busy-wait. `msleep` is the equivalent of vTaskDelay — yields to the scheduler. The difference is the same as in MCU code: busy-wait keeps the CPU; sleep lets other tasks run."

### Missing examples / figures
- §42.4 poll/select flow diagram is great. Add a similar diagram for blocking read in §42.3:
  ```
  user: read(fd, buf, n)
        │
  driver: wait_event_interruptible(wq, data_len > 0)
        │      ↳ schedule()  ← task is asleep here
        │
  IRQ/producer: writes data, wake_up_interruptible(&wq)
        │
  driver: wakes, checks condition, returns data
  ```
- §42.6 task state diagram as an actual state diagram, not just a list. Arrows: `TASK_RUNNING ↔ TASK_INTERRUPTIBLE ↔ TASK_UNINTERRUPTIBLE` with labels for the syscalls that cause transitions.

### Technical errors
- §42.3 `wait_event_interruptible(read_wq, data_len > 0)` — `data_len` is read **without holding the lock**. This is a classic subtle bug: `data_len` is set inside `data_lock`, so the check needs a memory barrier or the lock. In practice, on i.MX6ULL ARMv7 with a single core and the wake_up sequence, this happens to work — but the pattern shown is unsafe on SMP. Either:
  - Add a `READ_ONCE(data_len) > 0` (and `WRITE_ONCE` in the producer), OR
  - Move the lock inside the wait expression: `wait_event_interruptible(read_wq, ({ mutex_lock(&data_lock); int r = data_len > 0; if (!r) mutex_unlock(&data_lock); r; }))` (ugly), OR
  - Mention this as a teaching note: "this works for our single-core case but production code uses `READ_ONCE` here to prevent compiler reordering."
- §42.3 `O_NONBLOCK` check happens *before* acquiring the lock — fine, but the `data_len == 0` check has the same memory-ordering question. Mention it.
- §42.4 `__poll_t` is correct. `EPOLLIN | EPOLLRDNORM` is also correct. Worth mentioning: traditional `POLLIN | POLLRDNORM` is also accepted but `EPOLLIN` is preferred in modern kernels (since 4.16) because it forces the typed `__poll_t` cast.
- §42.5 `usleep_range(50, 100)` — minimum is 1 µs, but the kernel coalesces short sleeps. Worth noting: on a busy system, even `usleep_range(50, 100)` may return after 5-10 ms. For sub-millisecond timing, you must `udelay`.
- §42.8 Pitfall on memory-barrier: correctly states "wake_up implies a full barrier." This is true *for the writer*, but the reader who checked the condition before sleeping needs a separate guarantee that `wait_event_interruptible` provides. The `Documentation/memory-barriers.txt` reference is good; consider adding "in practice, `wait_event_*` and `wake_up_*` form a complete pair and you don't need explicit barriers between them. Add barriers only if you're checking flags *outside* the wait_event mechanism."

### Knowledge prerequisites missing
- "jiffies" — used in `wait_event_interruptible_timeout` and `schedule_timeout(jiffies)` (§42.5) without introduction. Sentence: "A jiffy is the kernel's coarse time unit, equal to 1/HZ seconds. On i.MX6ULL with default `CONFIG_HZ=250`, one jiffy is 4 ms. Convert: `msecs_to_jiffies(50)` for 50 ms, etc."
- `kthread_run` (§42.3 example uses a `producer_fn` started by kthread) — never shown. Either include the `kthread_run` line or forward-reference.

### Other
- §42.7 Lab #4 — explicitly note that the test relies on `cat` translating `-ERESTARTSYS` correctly. On some systems, `cat` retries silently and the Ctrl-C is "absorbed." Suggest using a custom test program that returns immediately on read failure.

## Ch43 — Interrupts

### Readability
- §43.1 chain diagram is excellent.
- §43.2 "Five lines of real work. Read status, ack, snapshot, defer, return. Under 1 µs on i.MX6ULL." — punchy, keep.
- §43.4 four-bottom-half choices — clear taxonomy, keep the table.
- §43.5 GPIO interrupts section — well-paced.
- §43.7 `/proc/interrupts` example is good but the table format renders awkwardly with long lines. Pre-format or use a code block fence with horizontal scroll.

### MCU-engineer friendliness
- §43.1 — this is the most critical MCU-bridge spot in the chapter and it's missing. Add: "On an MCU, an IRQ fires → NVIC vectors directly to your ISR. Period. On Linux, the chain has *six* levels because Linux runs on hundreds of SoCs each with different IRQ controllers and the kernel has to abstract them. The kernel's `virq` (virtual IRQ number) is the platform-independent ID; it's what your driver works with. Everything else (GIC, mapping, demux) is plumbing the kernel handles."
- §43.2 contract bullets — strong; add MCU bridge: "MCU equivalent: imagine your ISR could be preempted by a task switch, must hand off work to a deferred task, and shares the CPU with several other things. The 'top half' is the ISR; the 'bottom half' is the deferred task. FreeRTOS's `xTaskNotifyFromISR` followed by a task that processes the notification is the same pattern."
- §43.4 threaded IRQ — best MCU framing would be: "FreeRTOS pattern: ISR signals semaphore → high-priority task takes semaphore → processes. Linux threaded IRQ: kernel runs your primary handler in interrupt context → returns IRQ_WAKE_THREAD → kernel wakes a kthread that runs your threaded handler. Same architecture, different names."
- §43.5 GPIO IRQs — give the explicit MCU comparison: "On STM32 with EXTI, `EXTI0_IRQHandler` fires for any pin-0 across ports. On i.MX6ULL, GPIO IRQ banks work the same — one IRQ line per bank of 32 pins, demuxed by the GPIO driver. The kernel's `gpio_to_irq` (now `gpiod_to_irq`) gives you a per-pin virq so your driver doesn't need to demux."

### Missing examples / figures
- §43.1 chain ASCII is good; add a parallel diagram showing the *MCU* IRQ chain side-by-side to emphasize the abstraction layers Linux adds.
- §43.4 four-option comparison: a flowchart "do you need to sleep?" → "do you need atomic context?" → ... → which bottom half to pick.
- §43.5 GPIO IRQ — show the `/proc/interrupts` line after registration, so readers know how to verify their IRQ actually got connected.
- After §43.6, a Venn diagram of "your handler always called" vs "shared handlers all called" would help.

### Technical errors
- §43.2 "It runs with that IRQ disabled. The GIC won't re-fire the same IRQ on the same CPU until you return. (Other CPUs *can* see it; that's how SMP works.)" — slight nuance: with `IRQF_ONESHOT`, the IRQ is also masked on other CPUs until the threaded handler completes. Without `IRQF_ONESHOT`, the IRQ is re-enabled on the GIC after the top half returns and **can** fire on another CPU. Worth being precise.
- §43.3 `IRQF_TRIGGER_*` flags — "usually omitted for platform drivers because the DT specifies it" is correct. Add: "If you specify both, the kernel uses the DT one and ignores yours. If they conflict, the kernel logs a warning."
- §43.4 `DECLARE_TASKLET_OLD` — your example uses `DECLARE_TASKLET_OLD`, but `DECLARE_TASKLET_OLD` itself was deprecated in 5.9 in favor of `DECLARE_TASKLET` (the new-style with `tasklet_struct *` callback). The "OLD" macro is the *backwards-compat* macro; the modern one is `DECLARE_TASKLET(name, callback)` where `callback(struct tasklet_struct *t)`. Update or note the rename.
- §43.5 `gpiod_to_irq(b->button)` returns int that may be -ve on failure. The pattern `if (virq < 0) return virq;` is correct.
- §43.5 `IRQF_TRIGGER_FALLING | IRQF_ONESHOT` in the request — combining with the DT's `IRQ_TYPE_EDGE_FALLING` is redundant but harmless. Mention.
- §43.7 `/proc/interrupts` row shows `46:    0  gpio-mxc  14 Falling   button` — `gpio-mxc` is correct for the i.MX6ULL GPIO driver name. The IRQ line numbers (46) are example values; vary by kernel.
- §43.9 Pitfall "Symptom: must `modprobe demo` by hand at every boot" appears in Ch 39's pitfalls verbatim — copy-paste from Ch 39? Tighten to be IRQ-specific. (Actually it's in Ch 39; Ch 43's pitfalls don't mention this — false alarm; ignore.)

### Knowledge prerequisites missing
- `irqreturn_t` — appears as a type without introduction. One sentence: "An enum: `IRQ_NONE` (this wasn't mine), `IRQ_HANDLED` (took it), `IRQ_WAKE_THREAD` (top half done; run threaded handler now)."
- `writel`/`readl` — first use in §43.2 without introduction. Sentence: "Linux's portable MMIO accessors. `writel(val, addr)` writes 32 bits with memory-barrier semantics appropriate to the architecture. On ARM, includes a DMB. The reversed argument order vs `*addr = val` is a common stumble — value first, address second."
- `container_of` reappears in §43.4 work queue example. Cross-link back to Ch 37.

### Other
- §43.4 "Tasklets are **discouraged** in new code." — well-stated. Mention that they're being actively removed; some subsystems (notably block-I/O) have already converted. Forward-link to PREEMPT_RT chapter that explains the why.
- Lab #4 force IRQ storm — good, but warn that on production hardware with a watchdog, this might actually reboot. Add a sentence: "Disable any kernel watchdog before this experiment, or set it to a long timeout."

## Ch44 — GPIO subsystem + pinctrl

### Readability
- §44.1 multiplexing table is clear; keep.
- §44.2 the iomux macro deconstruction is just right.
- §44.4 descriptor API: very readable.
- §44.5 worked example is long but well-paced.
- §44.6 libgpiod output is great.
- §44.7 expander section — short and punchy.

### MCU-engineer friendliness
- §44.1 — MCU bridge missing. Add: "On STM32, you set `GPIOA->MODER` to mux a pin, then `GPIOA->ODR` to drive it. Linux splits these into two subsystems because on a complex SoC the pinmux is a *separate hardware block* (IOMUXC on i.MX6ULL) with its own clock and register space, distinct from the GPIO controllers. They're two register banks; Linux gives them two APIs."
- §44.2 the macro `MX6UL_PAD_UART1_RTS_B__GPIO1_IO19` — strong explanation. Add the MCU bridge: "If you've worked with NXP MCUXpresso, this is the same idea as the IOMUXC mux register tool — each macro encodes (mux_reg, conf_reg, input_reg, mux_mode, input_val) as a single 32-bit constant the kernel can write directly."
- §44.4 `gpiod_set_value_cansleep` vs `gpiod_set_value` — MCU bridge: "On an MCU, GPIO writes are register writes — never sleep. On Linux, a GPIO might live behind I²C (the expander); a write triggers an I²C transaction. `_cansleep` flags that 'this might block.' Use it in process context; reserve the non-`_cansleep` version for IRQ handlers and spinlock-held code where blocking is forbidden."

### Missing examples / figures
- A diagram in §44.1 showing the layered relationship:
  ```
   driver → gpiod API → gpio_chip (e.g., gpio-mxc) → IOMUXC + GPIO MMIO
                          ↓
                       (or)  → mcp23017 → I²C transaction → external chip
  ```
- §44.3 DT example — annotate the three cells more concretely with arrows pointing to "GPIO1_IO19 pin on bank 1" so the cell numbering clicks.
- After §44.5 example, show the `/proc/interrupts` line and `gpioinfo gpiochip0` output to prove the driver claimed the pin.

### Technical errors
- §44.2 `MX6UL_PAD_NAND_CE1_B__GPIO4_IO14` in the LED pinctrl entry — cross-check: NAND_CE1_B muxed to GPIO4_IO14 is correct for i.MX6ULL. The conf value `0x10b0` (drive strength 40Ω, slow slew) is reasonable for an LED.
- §44.3 "i.MX6ULL has 5 banks (`gpio1`–`gpio5`), each up to 32 pins" — correct, but **GPIO5 has only 12 pins** (per the i.MX6ULL reference manual; the rest are NC). GPIO4 also has fewer than 32 in some packages. Worth noting: "GPIO5 in particular is only partial — pins 0–11 are available."
- §44.4 `devm_gpiod_get(&pdev->dev, "reset", GPIOD_OUT_HIGH)` — "asserted" semantics — the wording "set as an output, and initialise it to **asserted** (`GPIOD_OUT_HIGH`) or **deasserted** (`GPIOD_OUT_LOW`)" is **incorrect in spirit**. `GPIOD_OUT_HIGH` and `GPIOD_OUT_LOW` set the **logical** initial value, but the names are misleading — they correspond to logical "high" (asserted, considering ACTIVE_LOW polarity) and logical "low" (deasserted). The kernel docs actually say `GPIOD_OUT_HIGH` = asserted, `GPIOD_OUT_LOW` = deasserted *after polarity is applied*. Reword: "`GPIOD_OUT_HIGH` initialises to logical-high (i.e., asserted given the DT polarity flag); `GPIOD_OUT_LOW` to logical-low (deasserted)."
- §44.6 sysfs deprecation: correct that `/sys/class/gpio/` is deprecated. Mention the kernel config: `CONFIG_GPIO_SYSFS=n` in modern kernel configs disables it; on Debian/Ubuntu it's usually still compiled in.
- §44.6 `gpioget gpiochip0 19` returns `1 ← button not pressed` — but the example DT has `GPIO_ACTIVE_LOW`, and `gpioget` returns the **raw line value** unless `--active-low` is passed. Specify: "gpioget shows raw level by default; `gpioget --active-low gpiochip0 19` shows logical."
- §44.9 Pitfall on "GPIO1 IO19 = global GPIO number 19" — correct that global numbers are legacy. On i.MX6ULL, the legacy global mapping was bank*32 + pin: GPIO1_19 = 19, GPIO2_5 = 37, etc. Worth mentioning the formula for readers debugging old DTs or sysfs.

### Knowledge prerequisites missing
- `GPIOD_*` flags — table appears mid-section; promote to a dedicated callout or table. Modern docs use additional flags (`GPIOD_FLAGS_BIT_OPEN_DRAIN`, etc.) — at least mention they exist.
- `pinctrl_select_state` is mentioned in §44.2 multiple-states but not introduced. One sentence: "When a driver wants to switch between declared states (e.g., active → sleep), it calls `pinctrl_select_state(pctrl, state)`. The most common use is the runtime PM hooks in §44.9 / Ch 51B."
- "phandle" again — see cross-cutting note.

### Other
- §44.5 — driver is solid; suggest adding the `#include <linux/of.h>` (referenced implicitly via `of_match_table` but the header isn't shown for the include block). Header completeness matters for the MCU dev who is going to literally copy-paste.
- §44.6 libgpiod — note libgpiod **v2** (releases 2023+) has a different C API than v1; CLI tools are mostly the same. Worth a forward note.

## Ch45 — Input subsystem

### Readability
- §45.1 pipeline diagram is clear.
- §45.2 event types table is great.
- §45.4 worked example structure is good.
- §45.5 — autorepeat/debounce/keymap section reads as three small topics; consider sub-headers for each.

### MCU-engineer friendliness
- §45.1 — MCU bridge missing. Add: "On an MCU, you'd parse a keyboard scan matrix in firmware and emit characters over UART or HID. On Linux, the kernel handles the scan-to-event translation in your driver; everything above (X11, Wayland, terminal) speaks one event protocol. You write the bottom of the stack; the rest is reused."
- §45.2 type/code/value triple — the MCU dev who's done HID will recognize this immediately. Add: "If you've ever written a USB HID descriptor, this is the same idea: 'usage page + usage + value' becomes 'type + code + value.' Linux's input layer is essentially a HID descriptor flattened."
- §45.4 IRQ handler design: critical bridge missing. The driver here uses `gpiod_get_value_cansleep` inside a *threaded* IRQ — that's fine because threaded IRQs can sleep, but the reader who internalized Ch 43 might wonder why it's safe to sleep in an IRQ handler. Add: "Because this is a *threaded* IRQ (via `devm_request_threaded_irq(...)` with `NULL` primary), the handler runs in kthread context — sleeping is fine. If we'd used `devm_request_irq` (non-threaded), `gpiod_get_value_cansleep` would BUG."

### Missing examples / figures
- After §45.4 evtest output, show `cat /proc/bus/input/handlers` so readers see how `evdev` registers itself as a handler.
- A diagram in §45.2 showing the input core's internal flow:
  ```
  input_report_key →  input_event() queues event → input_sync() flushes
                                                     ↓
                                              all evdev handlers
                                                     ↓
                                              wake_up readers of /dev/input/event*
  ```
- §45.5 debounce: the explanation says "implementing this is an exercise" — show the actual `delayed_work` + `cancel_delayed_work` pattern. Without code, the MCU dev reads "exercise" and skips.
- §45.6 multi-touch hint — actually show the bare protocol (one slot, one finger) so the reader doesn't have to flip to Ch 55G for the basic idea.

### Technical errors
- §45.3 `gpio-keys` example: `linux,code = <KEY_ENTER>;` — the kernel binding for `gpio-keys` uses `linux,code = <KEY_ENTER>` as the actual property name. Correct. Note that some older bindings used `code` (without prefix); modern is `linux,code`.
- §45.4 `bd->input->id.bustype = BUS_HOST;` — `BUS_HOST` is fine; some prefer `BUS_VIRTUAL` for software-generated devices. Either works.
- §45.4 IRQ request uses `IRQF_TRIGGER_RISING | IRQF_TRIGGER_FALLING | IRQF_ONESHOT` — to detect both press and release. With **edge-triggered** IRQ on both edges, the GPIO subsystem on i.MX6ULL handles this fine (it's "either edge" mode). Confirm.
- §45.4 in `button_irq`: reads gpio with `gpiod_get_value_cansleep` and reports the current value. This is a **polling-after-IRQ** pattern that handles both press and release with one handler. The classic alternative is to use the IRQ alone and toggle a software state; both work. Worth noting tradeoff: this approach handles bouncing poorly (a contact bounce while reading might give wrong polarity); the `gpio-keys` approach uses a debounce timer.
- §45.4 `input_set_capability(bd->input, EV_KEY, KEY_ENTER)` — correct, but the modern alternative is `set_bit(EV_KEY, input->evbit); set_bit(KEY_ENTER, input->keybit);` for setting multiple at once. Both work; mention.
- §45.7 `input_setup_polling` — correct, but the kernel symbol exists since 5.7. On older kernels it was `input_polled_dev`. State the cutoff.
- §45.10 Pitfalls — strong list. Add: "Don't allocate `input_dev` on the stack; always use `input_allocate_device` or `devm_input_allocate_device`."

### Knowledge prerequisites missing
- `kobj_to_dev` used in some code paths (sysfs callbacks) — for input chapter, not directly used, but in case forward-ref to Ch 46 §46.6.
- The `EV_REP` capability for autorepeat — mentioned in §45.5 but not shown how to enable. One sentence: "Set `input_set_capability(input, EV_REP, 0)` and configure repeat parameters via `input->rep[REP_DELAY] = 250; input->rep[REP_PERIOD] = 33;`."

### Other
- §45.6 absolute axes: `input_set_abs_params(input, ABS_X, 0, 4095, 0, 0);` — the parameters `fuzz` and `flat` need spelling out. "fuzz = noise threshold; events that differ by less than fuzz are not reported. flat = dead-zone for the value (joystick centers)."
- Lab #6 power-button: "With systemd, a long press should trigger a graceful shutdown" — this requires logind configuration. Mention `/etc/systemd/logind.conf` `HandlePowerKey=poweroff` or equivalent.

## Ch46 — I²C drivers

### Readability
- §46.1 split table is clear.
- §46.2 DT rules are well-stated.
- §46.3 skeleton is appropriate length.
- §46.4 SMBus API list is clean.
- §46.5 i2c_msg explanation could be more visual.
- §46.6 worked example is good.
- §46.7 i2c-tools section is great.

### MCU-engineer friendliness
- §46.1 — best MCU bridge in the chapter is missing. Add: "On an MCU, you write a function like `bme280_read(i2c_handle, reg, val)` that twiddles I²C peripheral registers directly. On Linux, the `i2c_adapter` is that 'i2c_handle' but abstracted across all I²C controllers in the kernel — same API for i.MX6ULL, STM32, x86, etc. Your driver only writes the chip-side code; the bus-side is reused."
- §46.3 `module_i2c_driver` — same idea as `module_platform_driver`; cross-reference Ch 39.
- §46.4 SMBus vs raw — MCU bridge: "On a bare-metal I²C library you usually have `i2c_read_register(addr, reg, buf, len)` as a single function. SMBus helpers are that. `i2c_transfer` is the raw form for chips that need unusual sequences (e.g., 16-bit register addresses)."

### Missing examples / figures
- §46.1 ASCII showing the three-player split is text-only; an actual diagram would help.
- §46.5 i2c_msg with repeated-start vs separate transactions — a wave diagram of SDA/SCL with START/repeated-START/STOP would clarify what "atomically" means in §46.5.
- After §46.6 worked example, an `i2cdump 1 0x50` showing the EEPROM contents would tie the example to the user-space view.
- A figure mapping `regmap` (Ch 50) layered over `i2c_transfer` layered over the i.MX I2C controller driver layered over the hardware. (The book has this concept but never illustrates the layering.)

### Technical errors
- **`i2c_driver.probe` signature is the major issue.** Modern kernels (6.3+) use `int probe(struct i2c_client *client)` — one argument. Your example uses the legacy two-argument form `int probe(struct i2c_client *, const struct i2c_device_id *)`. Either pick a target kernel and adjust, or note: "Since kernel 6.3, the second argument is gone. The `id_table` is still used by the I²C core to match, but the probe function no longer needs to look at it. For pre-6.3 kernels, the two-arg form below is correct."
- §46.3 `mychip_remove(struct i2c_client *client)` returning `int` — on kernel 6.11+, this returns `void`. Add a note.
- §46.3 includes `<linux/of.h>` — actually the modern way is `<linux/mod_devicetable.h>` for `of_device_id`. Both work.
- §46.4 `i2c_smbus_read_byte_data` returns `int` (negative on error, value as `s32`). The example correctly handles this.
- §46.6 example uses `dev_get_drvdata(kobj_to_dev(kobj))` — `kobj_to_dev` is the right helper, good. But `dev_get_drvdata` returns the `void *` set by `dev_set_drvdata`; the cast is implicit. Note the macro pattern.
- §46.6 EEPROM write `msleep(5)` — AT24C02's max page write time is 5 ms per datasheet, but ACK-polling (try a `i2c_smbus_write_quick(client, I2C_SMBUS_WRITE)` until it succeeds) is faster and more reliable. Mention it as an improvement.
- §46.9 Pitfall "Bus contention with multiple drivers" — the kernel actually allows multiple addresses if they don't conflict. The pitfall really should be "two DT children at the same `reg = <0x76>`" which would never happen if DT is correct.

### Knowledge prerequisites missing
- "i2c_adapter" — what number is `/dev/i2c-1` vs `/dev/i2c-0`? On i.MX6ULL, `i2c1` in DT → `/dev/i2c-0`? Or 1-indexed? It's 0-indexed by adapter registration order (which usually matches the DT order). Show `cat /sys/class/i2c-dev/i2c-1/device/of_node/full_name` to map.
- `mod_devicetable.h` — referenced indirectly; one mention is enough.
- The `0660` mode for sysfs and udev — already covered in Ch 38; cross-reference.

### Other
- §46.6 worked AT24 example — note that the real `at24` mainline driver uses nvmem framework now, not raw sysfs bin attributes. Reference: `drivers/misc/eeprom/at24.c` is on nvmem; readers might be confused if they cross-check. Add: "For a real driver, the modern path is to register as an nvmem provider; this example uses sysfs binary attributes only to keep the I²C wiring visible."
- Lab #6 strace — wonderful. `I2C_RDWR` ioctl is the right thing to see.

## Ch47 — SPI drivers

### Readability
- §47.1 SPI-vs-I²C table is excellent.
- §47.3 skeleton mirrors Ch 46 cleanly — readers will find it easy.
- §47.4 transfer/message explanation is clear.
- §47.6 spidev section is informative.
- §47.7 MCP3008 example is concise and concrete.

### MCU-engineer friendliness
- §47.1 — Add: "STM32 SPI peripheral or any MCU SPI: the controller pumps bits; you fill TXFIFO, drain RXFIFO. Linux abstracts FIFO management; you give it buffers, it returns when done. The SPI controller may be using DMA — you don't care."
- §47.4 full-duplex emphasis: "On an MCU, you choose between `HAL_SPI_TransmitReceive` (full duplex) and `HAL_SPI_Transmit` (half duplex). Linux's `spi_sync_transfer` with both `tx_buf` and `rx_buf` set is the equivalent of the former; passing NULL for one is the equivalent of the latter."
- §47.6 spidev: the MCU dev probably tried "I'll just write to a file" once. Add: "spidev is the 'I'll just write to a file' for SPI. It works. Use for prototyping; don't ship products on top of it (the real driver gives you proper power management, error handling, and proper user-space ABI)."

### Missing examples / figures
- A timing diagram for §47.4 showing two `spi_transfer`s in one message vs two separate messages — CS waveform highlighting "held vs released."
- §47.3 — show `cat /sys/class/spi_master/spi2/of_node/full_name` and the resulting `/sys/bus/spi/devices/spi2.0/` after probe.
- §47.7 — show the connection diagram of MCP3008 to ecspi (CS, MOSI, MISO, SCK) so the reader can build it.

### Technical errors
- §47.3 `fastadc_remove(struct spi_device *spi)` returning `void` — correct! SPI's `remove` has been `void` for a while now (long before the platform/i2c transition). Good.
- §47.3 the `spi_setup(spi)` call in probe is correct.
- §47.4 `xfers[0].delay.value = 10; xfers[0].delay.unit = SPI_DELAY_UNIT_USECS;` — confirmed the modern `spi_delay` struct (since 5.5). Older kernels used `xfer->delay_usecs` directly; you can mention both.
- §47.5 `spi_write`, `spi_read`, `spi_write_then_read` — correct. Add: "These all use `spi_sync` internally; they sleep, must be called from process context."
- §47.6 `"rohm,dh2228fv"` placeholder — correct historical note. Mention that the kernel now (since ~6.0) accepts `"spidev"` for `compatible` if you really want generic spidev, but it logs a warning about uninstantiable bindings. The community still prefers using the real chip's compatible.
- §47.7 MCP3008 protocol — the 3-byte command `{ 0x01, 0x80 | (ch << 4), 0x00 }` decodes the channel correctly. Note: bit 7 of byte 2 = single-ended/differential select. The example uses single-ended (bit 7 set); correct for typical wiring.
- §47.9 Pitfall on `spi_sync_transfer` from atomic context — correct.
- §47.9 Pitfall "`bits_per_word` != 8 ... byte order may not be what you expect" — slight clarification: when `bits_per_word = 16`, the buffers are read as `__u16` and the kernel handles byte order based on `spi->mode` flags (`SPI_LSB_FIRST` etc.). For most chips, stick to 8.

### Knowledge prerequisites missing
- "ecspi" — i.MX6ULL has 4 controllers named ECSPI1..4. Some boards also have a `gpmi-spi` or similar. Worth one sentence on the i.MX nomenclature: "ECSPI = Enhanced Configurable SPI; the i.MX-specific SPI controller. Mainline driver is `drivers/spi/spi-imx.c`."
- "MOSI/MISO/SCK/CS" — the chapter assumes the reader knows. Probably fine for the persona (6 YOE embedded), but a footnote with the meanings is cheap.
- `spi_set_drvdata` — set in §47.3 but not introduced. Same pattern as `i2c_set_clientdata` — cross-reference.

### Other
- §47.10 Going deeper — strong list. Add: "`Documentation/spi/spi-summary.rst`" (the high-level overview).

## Ch48 — PWM and RTC subsystems

### Readability
- Chapter splits cleanly into PWM and RTC halves.
- §48.1.1 PWM architecture ASCII is good.
- §48.1.2 DT example annotation is excellent.
- §48.2.1 "Two RTCs to know about" framing is great.
- §48.2.6 wake-from-suspend section is short and effective.

### MCU-engineer friendliness
- §48.1.3 consumer API — add MCU bridge: "Equivalent of `HAL_TIM_PWM_Start(htim, channel)` on STM32, but with the period/duty in nanoseconds instead of compare register values. The kernel computes the divisor and compare for you given the requested period."
- §48.2.1 — MCU bridge: "Your RTC chip on the MCU side was probably I²C-attached DS3231 with `Wire.h` calls. Same chip on Linux is registered by a kernel driver; you read it via `hwclock` or the kernel reads it at boot. You almost never write RTC code in a Linux driver."
- §48.2.6 alarms — add: "On an MCU you'd configure the RTC's alarm register and wire it to an EXTI line for wake. On Linux, set `/sys/class/rtc/rtc0/wakealarm` to the future timestamp; the kernel arms the RTC and configures power management to use it as a wake source."

### Missing examples / figures
- A waveform showing PWM output (period, duty cycle, polarity) — even ASCII art:
  ```
  ▕▔▔▔▔▔▔▔▕▁▁▁▁▁▕▔▔▔▔▔▔▔▕▁▁▁▁▁
   on (duty)   off (period-duty)
  ```
- After §48.1.5 sysfs example, a `scope` photograph or a `gpio capture` showing the PWM coming out the pin would help.
- A diagram for §48.2 showing the two RTCs and how Linux picks one as `/dev/rtc0`.

### Technical errors
- §48.1.1 "i.MX6ULL has 8 PWM channels (PWM1–PWM8)" — **8 PWM modules**, each is a single channel. The kernel exposes them as `pwmchip0` through `pwmchip7` typically, with one channel each. Worth being precise: "8 independent PWM controllers, each one channel wide on this SoC."
- §48.1.3 `pwm_apply_state(pwm, &state)` — modern. `pwm_apply_might_sleep` exists in some places too. Standard usage is fine.
- §48.2.2 `compatible = "maxim,ds3231", "dallas,ds1307"` — both compatibles in one node is correct; the kernel matches the first; the second is a fallback for older drivers.
- §48.2.5 `hwclock -w` writes RTC; `hwclock -s` reads RTC into system. Correct.
- §48.2.4 RTC provider sketch — `devm_rtc_allocate_device` and `devm_rtc_register_device` are modern. Correct.
- §48.4 Pitfall on "RTC time-zone confusion" — note that systemd's `timedatectl set-local-rtc 0` is the modern command; the older path was `hwclock --systohc --utc`.

### Knowledge prerequisites missing
- `pwm-backlight` — used in §48.1.2 but the binding details (brightness curve, `brightness-levels`) deserve a sentence on what the array means: "Linear brightness 0–255 mapped to those levels at the indices given. Index N maps to `brightness-levels[N]` as the duty cycle."
- `wakeup-source` flag — introduced in §48.2.2 without context. Note: "This flag tells PM core that the device's IRQ can wake the system from suspend. It enables `/sys/class/.../power/wakeup` controls."
- `SNVS_LP` — i.MX6ULL Secure Non-Volatile Storage / Low Power. Worth one sentence. The reader may have heard of "SNVS" in NXP datasheets and wonder.

### Other
- Lab #2 `pwm-beeper` — note that `pwm-beeper` is driven via `/dev/input/eventN` (yes, an input device!) with EV_SND. The Ch 45 input subsystem chapter doesn't mention this; cross-reference back.
- §48.5 references `drivers/rtc/rtc-ds1307.c` as a masterclass — agree, but warn that the file is ~1700 lines. Skim the family-detection logic at the top first.

## Ch49 — IIO subsystem (ADCs, sensors)

### Readability
- §49.1 architecture ASCII is great.
- §49.2 channel table is comprehensive.
- §49.3 channel definition is clear.
- §49.6 trigger orchestration is well-explained step-by-step.
- §49.7 ADC special case is well-paced.

### MCU-engineer friendliness
- §49.1 — best opportunity for an MCU bridge: "On an MCU, you'd write a sensor driver that exposes `read_temp()`, `read_pressure()`. Each app calls these directly. Linux pushes the same idea to a framework: your driver exposes channels named by type, and *any* app — yours, gnuplot, Grafana, the test harness — reads them through one consistent interface. The cost: more boilerplate. The benefit: tools work without modification."
- §49.2 channels: "Think of each channel as one ADC pin or one sensor axis. The MCU equivalent of a 3-axis accelerometer is calling `accel_read(&x, &y, &z)`. The Linux IIO version is reading three files: `in_accel_x_raw`, `in_accel_y_raw`, `in_accel_z_raw` — each is one channel."
- §49.6 buffered capture: "On MCU + RTOS you'd run a timer ISR sampling at 1 kHz pushing to a circular buffer drained by a task. IIO does the same but the timer is `hrtimer-N`, the buffer is a kfifo, and the drainer is whoever reads `/dev/iio:device0`."

### Missing examples / figures
- §49.2 conversion formula `real_value = (raw + offset) × scale` deserves a worked numeric example with all three numbers shown.
- §49.6 — show the actual `/sys/bus/iio/devices/iio:device0/` tree after enabling buffered capture, with `scan_elements/`, `buffer/`, `trigger/` directories visible.
- §49.7 — diagram showing the relationship between `scan_index`, `scan_type`, and how user-space decodes the binary buffer. The MCU dev who's done binary protocols will get this fast with a picture.

### Technical errors
- §49.3 `IIO_VAL_INT_PLUS_MICRO` returns `*val + *val2/1000000`. The example sets `*val = 0; *val2 = 10000;` and says "0.01 °C per raw." Math: `0 + 10000/1e6 = 0.01`. Correct.
- §49.4 `INDIO_DIRECT_MODE` — correct that this enables polled-via-sysfs.
- §49.4 `devm_iio_device_alloc(&client->dev, sizeof(*p))` — correct.
- §49.5 user-space `iio_attr` and `iio_readdev` — these are from `libiio` (Analog Devices) tooling, not in mainline. Specify package: `libiio-utils` (Debian) or `iio_info` (Yocto). Some distros only ship the in-kernel `tools/iio/` binaries.
- §49.6 the orchestration sequence is correct. Worth adding: triggers are a separate kernel object — `hrtimer-0` is created by writing to `/sys/bus/iio/devices/iio_sysfs_trigger/add_trigger`. Mention this so the reader doesn't wonder where `hrtimer-0` came from.
- §49.7 ADC_CHANNEL macro: `.scan_type = { .sign = 'u', .realbits = 10, .storagebits = 16 }` — for MCP3008 (10-bit unsigned), correct. `shift` defaults to 0.
- §49.9 Pitfall "Forgetting `iio_priv()`" — strongly worded; good. Note: in modern kernels (since 4.x), the private struct is allocated *after* the `iio_dev` in a single block; the alignment is handled by the alloc helper.

### Knowledge prerequisites missing
- "hwmon" — mentioned in §49.9 Pitfall "Two drivers competing... `hwmon` and IIO drivers exist for the same chip" — the reader doesn't know what hwmon is yet. Add one sentence: "hwmon (hardware monitoring) is the older sensor framework, predating IIO. New drivers should be IIO; some chips still have hwmon-only drivers."
- "kfifo" — mentioned without introduction. "Kernel FIFO — a SPSC ring buffer primitive in the kernel. `kfifo_in`, `kfifo_out`, `kfifo_len`. Lockless if there's one reader and one writer."

### Other
- §49.6 ends with "We'll meet triggers and buffers again in Ch 70/71 (IMUs) where they really earn their keep." — good forward reference.
- Lab #4 plot with gnuplot — concrete and good.

## Ch50 — regmap

### Readability
- §50.1 motivation is the strongest opener in Part VI — clear, concrete, sells the abstraction immediately.
- §50.2 minimal example is well-scoped.
- §50.3 variations subsections are clear.
- §50.5 "the full pattern" combining regmap + IIO + IRQ is a great capstone for the whole part.
- §50.6 debugfs section is excellent.

### MCU-engineer friendliness
- §50.1 — already strong. Add the MCU bridge explicitly: "If you've written an MCU driver for an audio codec or sensor with 100+ registers, you wrote the same I²C wrapper functions and bit-manipulation macros over and over. Regmap is Linux's 'enough — let me describe my chip declaratively and stop writing wrappers.'"
- §50.3 cache_type discussion — MCU bridge: "An MCU driver might `static uint8_t shadow[256]` to avoid re-reading registers it just wrote. Regmap's cache is the same idea, but the framework handles invalidation when you mark registers volatile."
- §50.4 `regmap_update_bits` — bridge: "Equivalent of:
  ```c
  uint8_t v;
  i2c_read(reg, &v);
  v = (v & ~mask) | (val & mask);
  i2c_write(reg, v);
  ```
  ...except atomic with respect to other regmap callers on the same device, and possibly cache-only if the register is cached."

### Missing examples / figures
- A layered diagram for §50.1 showing:
  ```
   driver code → regmap API → cache layer → bus layer (I²C/SPI/MMIO) → hardware
                                  ↓
                              debugfs view
  ```
- §50.3 cache types comparison — a small table:
  | Type | Lookup cost | Memory cost | Best for |
  |------|-------------|-------------|----------|
  | NONE | bus hit | 0 | rarely accessed registers |
  | RBTREE | O(log N) | sparse | thousands of regs used sparsely |
  | FLAT | O(1) | dense (max_reg bytes) | <128 regs all used |
- §50.5 full pattern — show the call graph: probe → regmap_init → init_sequence → request_irq → iio_register. The MCU dev wants to see the order of operations.

### Technical errors
- §50.2 `devm_regmap_init_i2c(client, &my_regmap_config)` — correct.
- §50.3 `REGCACHE_RBTREE` and `REGCACHE_FLAT` are both correct constants. There's also `REGCACHE_MAPLE` in newer kernels (6.4+) — replacing rbtree for sparse cases. Mention.
- §50.4 `regmap_multi_reg_write` correctly takes `struct reg_sequence` array. Good.
- §50.5 sketch: `iio_priv(idev)` and `devm_iio_device_alloc` are used correctly. The `regmap_read` for two registers and combining hi/lo is a common pattern; would be cleaner with `regmap_bulk_read(p->regmap, REG_DATA_HI, buf, 2)` followed by `be16_to_cpup(buf)`. Mention as a stylistic improvement.
- §50.6 debugfs path is correct; the directory name `1-0076` is `bus-address` (1 = i2c-1, 0076 = address 0x76). Mention the naming convention.
- §50.8 Pitfall "Mixing regmap and direct bus access" — strong. Worth adding: "Even calling `i2c_smbus_read_byte_data` on the same chip while a regmap exists for it can corrupt the cache."

### Knowledge prerequisites missing
- `REGCACHE_NONE` is the default — worth stating explicitly. The reader might wonder.
- `regcache_mark_dirty` and `regcache_sync` are mentioned in §50.3 and §50.7 Lab — first time they appear without clear definitions. Add: "`regcache_mark_dirty(rm)` marks every cached register as 'cache may differ from hardware.' `regcache_sync(rm)` writes back all dirty registers to hardware. Together they form the suspend/resume idiom."
- `reg_default` vs `reg_sequence` — both used; they're different types. Spell out the difference: "`reg_default` says 'register X defaults to value Y'; the cache uses this to know what *not* to push to hardware. `reg_sequence` says 'send this sequence of writes'; it's an init script."

### Other
- §50.9 Going deeper — note that `sound/soc/codecs/wm8960.c` is a great teaching example; agree. Also recommend `drivers/mfd/syscon.c` for an MMIO regmap example.
- The chapter is the strongest in the part. Use it as the structural template if you ever revise the others.


---

# Part VIb — Drivers advanced: Review

## Cross-cutting observations

- **Several chapters claim PREEMPT_RT is "out of tree" or "partially in mainline."** As of v6.12 (December 2024), PREEMPT_RT is fully merged into mainline. Ch 52A §52A.3 reads "PREEMPT_RT is partially in mainline. If 'Fully Preemptible Kernel (Real-Time)' is missing, you need the out-of-tree PREEMPT_RT patch" — for a v6.6 kernel that's still true, but the framing makes it sound like the work is in progress. Add: "From v6.12 the option is unconditionally available; older kernels need the patch."
- **MCU-bridge boxes are missing throughout.** None of these advanced chapters opens with an explicit "this maps to your MCU experience as X." For a 6-YOE MCU engineer reading dense topics like DMA-engine, ASoC, V4L2, DRM/KMS, MTD/UBI, USB-gadget, every chapter should have a 3–5 line "from MCU's perspective" sidebar before §1. Ch 51 hints at it but doesn't commit; the rest jump straight into Linux jargon.
- **DT graph syntax (`port { endpoint { remote-endpoint }}`) appears in 4 chapters (54, 54B, 55H, also in 53)** but is never introduced. Reader has seen `phy-handle = <&node>` (Ch 52) but `of_graph` two-port endpoints are a different style — needs a 10-line explainer somewhere, probably first appearance (Ch 54).
- **"softirq context" is used as a synonym for "tasklet context" interchangeably.** Ch 51 §51.4 says "callback runs in tasklet context"; Ch 55A says "softirq context." These aren't identical; tasklets are a subset of softirqs (TASKLET_SOFTIRQ specifically). DMA completion callbacks today run in a `tasklet` or in `dmaengine`'s `vchan_complete` — flag the imprecision and unify wording.
- **Channel-context warnings recur ("no kmalloc(GFP_KERNEL), no mutex_lock") without one consolidated table.** Reader benefits if Part VIb opens with a quick "context cheat sheet" pointer back to Ch 41 — atomic / softirq / process — because every dense chapter assumes the reader silently recalls it.
- **Pitfall blocks are excellent but the per-chapter "Going deeper" reference paths sometimes drift.** A few mainline paths are slightly off (`sound/soc/fsl/imx-sdma.c` doesn't exist; the real file is `imx-pcm-dma.c`; `drivers/sound/soc/fsl/fsl_sai.c` should be `sound/soc/fsl/fsl_sai.c`). Listed per chapter.
- **No chapter shows what dmesg looks like when things WORK fully end-to-end.** Several show fragments. For a chapter that's the reader's first contact with a subsystem (ALSA, V4L2, gadget) including a full "successful probe trace" really helps build the mental model.

## Ch 51 — DMA

### MCU-engineer friendliness

- Strong opening, but the bridge is implicit. Add a sidebar: "On STM32 you set up DMA1_Channel3 → SPI1_TX in HAL by filling DMA_HandleTypeDef and calling HAL_SPI_Transmit_DMA(). Linux's dmaengine is the same idea, factored differently: the *controller* driver (imx-sdma) does what HAL_DMA_Init did; the *consumer* (your driver) does what HAL_SPI_Transmit_DMA did. The 'four-step ritual' below is the consumer half." That single paragraph would orient the reader.
- §51.7 cache coherency trap — for an MCU engineer this is the *biggest* mental shift. STM32 Cortex-M0/M3 has no data cache; Cortex-M7 has but they manually `SCB_CleanDCache_by_Addr`. Linux's `dma_map_single` *automates* that. Make this explicit: "If you've used SCB_CleanDCache, dma_map_single is its automatic Linux equivalent."

### Missing examples / figures

- §51.3 — show an ASCII timeline of "SDMA event 7 fires → SDMA runs script → fills RX buffer → DMA IRQ → callback." Helps with the "where does event 7 come from" mystery.
- §51.5 — cyclic DMA needs a picture. ASCII box of ring buffer with period markers and a write/read pointer. Otherwise the reader has to mentally invent it.
- §51.4 Step 3 — would benefit from an ASCII diagram of how a scatter-gather list looks: discontiguous physical pages → one sg_table → one descriptor.

### Technical errors

- §51.4 line "(or use the `devm_` style: `devm_get_free_pages` etc. don't have a DMA equivalent for channel requests, so manual cleanup)" is misleading. There IS `devm_request_chan(dev, name)` in mainline since v5.13; recommend it. Manual cleanup is no longer the only option.
- §51.4 Step 2: code uses both `peripheral_phys + RX_FIFO` and `peripheral_phys + TX_FIFO`. The chapter never says what `peripheral_phys` is — for the reader's first DMA driver, spell out "use the controller's `struct resource` from `platform_get_resource(...)->start`."
- §51.4 Step 4 — the comment says callback runs in "tasklet context," but for imx-sdma it actually runs as a virtual-channel tasklet inside vchan_complete_descriptor. Functionally same constraints (atomic, no sleep), but call it "softirq/tasklet — atomic context" for accuracy.
- §51.6 has a real bug: `dma_request_chan_by_mask(&dma_cap_zero(mask))` — `dma_cap_zero(mask)` is a void macro that zeroes mask; you can't take its address. Should be:
  ```c
  dma_cap_mask_t mask;
  dma_cap_zero(mask);
  dma_cap_set(DMA_MEMCPY, mask);
  struct dma_chan *chan = dma_request_chan_by_mask(&mask);
  ```
  The current snippet will not compile.

### Knowledge prerequisites missing

- §51.3 references "PWM and clocks" pattern but reader may want a one-line reminder of where the `dmas`/`dma-names` lookup tree sits in the of_dma framework.
- `GFP_DMA` (in pitfalls) introduced without explanation. For a reader who hasn't met memory zones, this is opaque. One sentence: "GFP_DMA is the kernel's hint to allocate from the low 16 MB ZONE_DMA region — historically required by ISA DMA; on most ARM SoCs it's a no-op since all RAM is DMA-capable, but the API expects the flag."

### Other

- §51.8 lab item 5 "Provoke a cache bug" is good but risky on real hardware — clarify that doing this might trash adjacent kernel memory, not just print wrong data. Recommend running in a controlled VM or with KASAN if available.
- "Going deeper" list: there is no `sound/soc/fsl/imx-sdma.c` — the audio side is `sound/soc/fsl/imx-pcm-dma.c`. Fix path.

## Ch 51A — Watchdog

### Readability

- §51A.5 ramoops paragraph is dense. Sentence "On the next boot, the recovered data lives in `/sys/fs/pstore/`" is fine, but the lead-in "a small chunk of DRAM marked 'preserved across warm reset'" — reader will ask: how does DRAM survive a reset? Add one sentence: "On most SoCs the DRAM controller is not reset by a CPU reset; rows stay refreshed for at least several seconds, so a small reserved region holds its data."

### MCU-engineer friendliness

- Need a bridge. On STM32 you talk to the IWDG by clearing a key into a single register at IWDG_KR. Here you `write()` to `/dev/watchdog`. Worth noting: "From your driver's perspective, IWDG_KR ↔ a regmap_write; from user-space, it's now a file descriptor — same underlying register, layered behind file_operations and the watchdog subsystem."

### Technical errors

- §51A.1 says "i.MX6ULL has two: WDOG1 and WDOG2 (in SNVS)." The Reference Manual lists **three** watchdogs: WDOG1, WDOG2, and WDOG3 (also "TrustZone Watchdog" / TZ_WDOG). None of them is "in SNVS" — SNVS is a separate IP for secure non-volatile storage. The IPS memory map (RM 10260–10334) shows WDOG1 at 0x020B_C000, WDOG2 at 0x020C_0000, WDOG3 at 0x021E_4000. Fix to: "i.MX6ULL has three watchdog instances (WDOG1, WDOG2, WDOG3); WDOG3 is reserved for TrustZone. WDOG1 is the one Linux normally uses."
- §51A.3 — `WDIOC_SETOPTIONS` example uses `&(int){ WDIOS_DISABLECARD }` (a compound literal). This works in C99 but the comment "gracefully — driver-dependent" understates it: most production drivers DON'T support DISABLECARD at all and return -EOPNOTSUPP. Worth noting.
- §51A.5 line "imx2_wdt reads this and reports via `dmesg` / `/proc/sys/kernel/last_reboot_reason`" — there is no `/proc/sys/kernel/last_reboot_reason` in mainline. The boot reason is exposed via the `reboot-mode` framework or by the driver into `/sys/class/watchdog/watchdog0/bootstatus`. Fix the path.

### Missing examples / figures

- Add an ASCII timeline showing: "userspace stops feeding (T0) → counter hits 0 (T0 + timeout) → WDOG asserts RESET → SoC reboots → bootloader → kernel reads WRSR → dmesg 'last reboot was watchdog'." That's the whole story in one picture.

### Other

- §51A.7 lab item 2 "kill -9 the daemon; verify the system resets 10 s later" — strongly recommend a "save your work first" note. Readers may forget that this *actually* hard-resets the board.
- §51A.9 reference: `Documentation/admin-guide/pstore-blk.rst` is renamed to `pstore-blk.rst` under different paths in newer kernels; verify path against your kernel target.

## Ch 51B — Power management

### Readability

- §51B.4 sentence "powertop is invaluable for finding which userspace process is keeping the CPU awake." is good but the surrounding text is choppy. Suggest: "powertop measures per-process and per-driver wakeup rates and converts them to estimated power. The goal at idle: see 'kernel sleep' at 95 %+ and total wakeups below 10/sec."
- "User-space pick the **governor**" — grammar; should be "User-space picks the **governor**."

### MCU-engineer friendliness

- The runtime-PM model is genuinely alien to MCU folks. Add a bridge: "On an STM32, you call __HAL_RCC_USART1_CLK_DISABLE() yourself when you're done with USART1 to save current. Linux's runtime PM does the same thing but driven by *reference counts*: every `pm_runtime_get` is the moral equivalent of 'enable clock and bump usage'; every `pm_runtime_put_autosuspend` is 'maybe disable clock when no one's using it for a second.' The kernel handles the bookkeeping."
- DVFS — MCU folks know dynamic clock prescaling but rarely couple it with voltage scaling. Note: "Unlike STM32's RCC clock tree where you change PLL freely, ARM Cortex-A needs *voltage* to track *frequency* because higher frequencies need higher Vdd to settle gate delays. The DT 'operating-points-v2' table is the (freq, voltage) pair list — the kernel scales both in the right order."

### Missing examples / figures

- §51B.3 — the "topological-order suspend" claim wants a tiny ASCII diagram. Show parent → child (USB controller → USB hub → mass-storage), suspended in *leaf-first* order (mass-storage, hub, controller), resumed in reverse.
- §51B.4 sample `powertop` output is generic; add an annotated example showing "if you see this line, blame this driver."

### Technical errors

- §51B.2 OPP table — `<&reg_arm>` is the regulator that controls `VDD_ARM_IN`. For i.MX6ULL the OPP frequencies in mainline are 198/396/528/696 MHz (the 198 OPP is omitted here). Worth listing all four for accuracy.
- §51B.3 wakeup sysfs path is wrong: `/sys/class/wakeup/.../wakeup` doesn't exist in mainline. Wakeup attributes are at `/sys/devices/.../power/wakeup` (write `enabled`/`disabled`). Fix.
- §51B.7 — "Hardware quirks. Some i.MX6ULL peripherals (SDMA, USB) introduce latency" — this is Ch 52A territory, not 51B. Either remove or reword.

### Knowledge prerequisites missing

- "regcache_sync" appears in §51B.3 with no explanation. Reader has seen regmap in Ch 50; one sentence: "regcache_sync replays all writes the driver made to the chip while it was suspended — restoring the chip's register state from the kernel-side cache."
- `pm_ptr` mentioned in pitfalls without prior context. Either define ("pm_ptr is a macro that compiles to NULL when CONFIG_PM is off, sparing you ifdefs around .pm = ...") or drop.

## Ch 52 — Network FEC + KSZ8081

### Readability

- §52.1 caption "RJ45 magnetics" is correct technical English but unusual; consider "RJ45 jack with integrated magnetics" to be unambiguous.
- "Critical fields" bullet list — readable, but `phy-supply = <&reg_enet_3v3>;` appears in the DT block but isn't called out in the bullets. Reader who wants to know what it does will hunt. Add it.

### MCU-engineer friendliness

- MCU folks have done STM32+LAN8720 by hand (RMII pinout, ETH_RST GPIO, MDIO bit-bang). Add a bridge: "Compared to STM32 HAL_ETH, here the MAC layer is `fec_main.c` (equivalent to stm32_eth.c), but Linux adds *phylib* — a generic PHY library that knows how to talk to dozens of vendor PHY chips via MDIO. Where on STM32 you'd manually write to MII registers, Linux discovers the PHY's ID, autoloads `micrel.c`, and calls a generic `phy_start`."
- The "MAC vs PHY" distinction is easy to confuse. Worth a sentence: "MAC = MAC layer = Media Access Controller, the digital frame engine inside the SoC. PHY = Physical layer = the analog SerDes chip outside, on the board. RMII is the wire bus between them."

### Missing examples / figures

- §52.4 — ASCII showing the relationship: `phy_device` (per-PHY struct) hangs off `mii_bus` (per-MDIO bus) hangs off `net_device` (per-MAC). Three nested layers; one diagram clarifies everything.

### Technical errors

- §52.1 statement "i.MX6ULL has two FEC instances, FEC1 and FEC2" is correct. RM line 9868 "Two Controller Area Network (FlexCAN), 1 Mbit/s each" confirms two ENET instances elsewhere — good.
- §52.4 — "phylib functions: `phy_start(phydev)` — start autonegotiation." This is partially wrong. `phy_start` starts the PHY state machine; autoneg is started during `phy_connect_direct` / `phy_attach_direct` based on advertise registers. The state machine then transitions through autoneg if enabled. Reword: "phy_start kicks the state machine; if autoneg is enabled (default), the PHY negotiates link speed/duplex automatically."
- §52.5 — "Omit the `clocks` and instead have the PHY's `clock-names = 'rmii-ref';`" — these two lines describe contradictory configurations. The condition is: PHY-supplied clock → no `clocks` on the PHY (the SoC's `ENET_REF_CLK1` pin becomes an input), and you set `clock_in_out = "in"` (or whatever the binding is for that PHY); MAC-supplied → SoC drives, `clocks = <&clks IMX6UL_CLK_ENET_REF>` ensures the SoC produces it. Rewrite for clarity.
- §52.6 — pin mux table includes `MX6UL_PAD_ENET1_RX_ER__ENET1_RX_ER` but RMII doesn't use RX_ER; the FEC tolerates it but it's not required. Either drop or note "optional, FEC ignores."
- §52.7 — MAC address fallback order in mainline fec_main is roughly: nvmem (OCOTP) cell → DT mac-address property → MAC register from bootloader → random. Verify against fec_get_mac() in your kernel. Order in chapter (DT → OCOTP → MAC reg → random) differs from current code which prefers nvmem first.

### Knowledge prerequisites missing

- "PHC device 0" appears in dmesg output without comment. PHC = PTP Hardware Clock; reader will not know. Either gloss it or omit.
- "NAPI" — defined parenthetically ("New API; the polled receive model"), good. But the description as "batches RX interrupts" is half-true; NAPI actually masks the IRQ during polling. Worth one more sentence: "After NAPI poll drains the RX ring, the driver re-enables the IRQ. This way a high-rate flood only causes one IRQ then a series of polls until quiet."

### Other

- §52.11 pitfall about NAPI weight 64 mentions gigabit "not on i.MX6ULL" — keep, helpful.

## Ch 52A — PREEMPT_RT

### MCU-engineer friendliness

- The MCU engineer's mental model is FreeRTOS / Zephyr — a fully preemptible kernel by default. They will be surprised that mainline Linux *isn't*. Open with: "Coming from FreeRTOS where the highest-priority ready task always runs instantly, mainline Linux's surprise is: a `spin_lock_irqsave` in kernel code blocks even the highest-priority RT thread until it's released. PREEMPT_RT changes that contract."
- Priority inheritance — explain the analogy: "Same problem FreeRTOS solves with mutex priority inheritance. xSemaphoreCreateMutex() in FreeRTOS automatically does PI; on Linux, only `rt_mutex` (and pthread_mutex with PTHREAD_PRIO_INHERIT) does."

### Missing examples / figures

- §52A.4 — show one `cyclictest` *histogram* (the `-h` flag) — long tail visualization is essential to explain "P99 vs P99.99 latency."
- §52A.2 — diagram of standard Linux vs PREEMPT_RT IRQ flow: top-half/bottom-half vs all-in-thread. ASCII boxes for "IRQ context", "softirq context", "kthread context", with which is preemptible in each kernel.

### Technical errors

- §52A.3 statement "PREEMPT_RT is partially in mainline" is outdated. v6.12 (Dec 2024) fully merged the remaining `PREEMPT_RT` work; the `Fully Preemptible Kernel (Real-Time)` Kconfig option is unconditionally selectable from 6.12 onwards. Reword to: "PREEMPT_RT fully merged as of v6.12. For older kernels you may still need the patch series."
- §52A.5 mentions `mce=off` for "machine-check exceptions" — that's an x86 cmdline. On ARM/i.MX6ULL it does nothing. Drop or note "x86 only."
- §52A.5 "Pre-fault 256 KB of stack" — the example does `char stack[256 * 1024]; memset(stack, 0, sizeof(stack));` but this is a local variable, not the *thread's* actual stack. After return from `memset`, the stack may not even still have those pages allocated (compiler may not put it on stack, may VLA it, etc.). The standard recipe is `mlockall` + a separate stack pre-fault loop, e.g., recursive function that touches each page. Worth rewriting.
- §52A.6 pitfall about `GFP_ATOMIC` is slightly off: under PREEMPT_RT the `spin_lock` is preemptible so a `kmalloc(GFP_KERNEL)` inside it is now legal (it's just expensive). The pitfall is more about *not changing semantics across configs* — code that worked on standard Linux because `GFP_KERNEL` happened not to sleep may sleep under PREEMPT_RT. Reword.

### Knowledge prerequisites missing

- `SCHED_FIFO` mentioned without definition. One line: "SCHED_FIFO is a Linux scheduler policy where a thread runs until it yields, blocks, or is preempted by a higher-priority FIFO thread — no time slicing among same-priority FIFO threads."

### Other

- §52A.5 `processor.max_cstate=0` — i.MX6ULL Cortex-A7 doesn't expose ACPI C-states; the cpufreq governor controls idle. Cmdline has no effect on this SoC. Recommend removing or replacing with `cpuidle.off=1`.

## Ch 53 — Sound (ALSA + ASoC)

### Readability

- §53.1 paragraph chain is fine but the term "DAI" appears 6+ times in the diagram and isn't defined until §53.3 ("DAI link" then "DAI format"). Define DAI = Digital Audio Interface (the I²S/TDM serial bus) in the first paragraph.

### MCU-engineer friendliness

- This is a chapter where the MCU bridge matters most. ALSA/ASoC will feel insane otherwise. Bridge:
  > "On STM32 with I²S, you'd configure SPI3 in I²S mode, DMA from a buffer to its DR, and call your codec's I²C config functions yourself. Linux's ASoC factors this into three pieces that mirror the chip layout: (1) a **CPU-DAI driver** wrapping the SoC's I²S/SAI peripheral (same code STM32 HAL_I2S would call), (2) a **codec driver** that talks I²C/SPI to the codec chip (same code your wm8960_init() did), and (3) a **machine driver** — a tiny board-specific file that says 'pair THIS CPU-DAI with THIS codec, at 48 kHz, in I²S format.' The reason for three is that one codec driver is reused across many boards, one CPU-DAI driver across many codecs."

### Missing examples / figures

- §53.2 — DT block lists `assigned-clocks` / `assigned-clock-parents` / `assigned-clock-rates` without explanation. A 5-line ASCII showing the clock tree (PLL4_AUDIO → SAI2_SEL mux → SAI2 divider → 24.576 MHz on the wire) would unlock this.
- The **machine + cpu_dai + codec_dai** triangle from the review brief is exactly what's missing. ASCII:
  ```
  machine driver
    └─ snd_soc_dai_link ─── CPU-DAI ←── SAI2 ←── SDMA (cyclic) ←── DRAM ring
                          └ codec_dai ─── WM8960  ←── I²C2 (control)
                                                  ─── I²S (audio)
  ```
- §53.3 "How a sample plays" — actually quite good. Keep.

### Technical errors

- §53.1 line "`drivers/sound/soc/fsl/fsl_sai.c`" — path wrong. Should be `sound/soc/fsl/fsl_sai.c` (no `drivers/` prefix; `sound/` is at kernel root). Same error in §53.8.
- §53.2 — `mux-int-port = <2>; mux-ext-port = <6>;` are properties of the legacy `fsl,imx-audio-wm8960` binding (specific to i.MX SoCs that route audio through an AUDMUX). The i.MX6ULL has no AUDMUX — SAI connects directly. Confirm against the actual `imx-wm8960.c` binding for i.MX6ULL. The example may be copy-pasted from an i.MX6Q board.
- §53.4 — `COMP_CPU("imx-sai2")` uses a string identifier for the CPU-DAI. In real DT-based ASoC machine drivers, you typically use `COMP_DUMMY()` for the platform and let DT bind via `of_node`. The hardcoded string is the older platform-data style. For a new chapter consider using the DT-based pattern (`SND_SOC_DAILINK_DEF` with `OF_DAI_NAME` or similar). Worth flagging "this is illustrative; mainline machine drivers use of_node references."
- §53.4 `.dai_fmt = ... | SND_SOC_DAIFMT_CBS_CFS` — note that as of v5.16 the format names changed: `CBS_CFS` (Codec Bit-clock Slave, Codec Frame-clock Slave) was renamed to `CBC_CFC` (Codec Bit-Consumer, Codec Frame-Consumer) for inclusive language. Older code still has CBS_CFS aliases but the recommendation is to use the new names. Update if targeting current mainline.

### Knowledge prerequisites missing

- "DAPM" — Dynamic Audio Power Management — appears in §53.4, §53.6, §53.7 without explanation. One sentence: "DAPM is ASoC's power-saving graph: the codec has internal blocks (mics, headphone amp, DAC) and DAPM tracks which are needed for the active stream, powering the rest down. Widgets describe what's *physically wired*; routes describe what's connected."
- "xrun" — defined in passing ("underrun"). Good.

### Other

- §53.6 — point reader at `arecord -L` (capital L) and `aplay -L` to see ALSA's plug/dmix configuration too; helpful for debugging.

## Ch 54 — LCD framebuffer and DRM/KMS

### Readability

- §54.1 table is clear. Keep.
- §54.4 "magnificent hack" is loaded — for a serious reference book consider "a clever shortcut: panel-simple has a built-in database of dozens of common panels keyed by compatible string." Reader-friendly without editorialising.
- §54.7 "Verify HSYNC and VSYNC" — actually says "Polarity matches DT (`hsync-active = <0>` = active-low)." Good.

### MCU-engineer friendliness

- Crucial bridge missing. The MCU engineer has likely driven an RGB-parallel LCD via STM32 LTDC. Add: "If you've used STM32 LTDC, LCDIF is the i.MX equivalent — same parallel RGB output, same HSYNC/VSYNC/DE timing, but here Linux's DRM/KMS exposes it through `/dev/dri/card0` rather than direct register access. The **panel-simple** driver replaces the per-LCD timing struct you'd have hand-rolled in `MX_LTDC_LayerConfig`."
- DRM vs framebuffer history confuses MCU engineers who only know "linear memory you write pixels into." Explain: "DRM/KMS is a *plane composer* (think layers in PowerPoint, with hardware support) plus a *modesetting* engine. fbdev was just 'one 2D buffer, write pixels.' i.MX6ULL has no GPU and only one plane, so for you the difference is mostly API style — but DRM is the future-proof one."

### Missing examples / figures

- ASCII showing the DRM object graph: `drm_device` → `crtc` → `plane` → `connector` → `encoder` → `bridge` → `panel`. Each chapter chapter (54, 55H) references pieces of this; show it once.
- §54.7 — add a "scope trace cheat sheet" showing what PCLK, HSYNC, VSYNC, DE *should* look like (boxes + arrows; H/V active and porch labelled).

### Technical errors

- §54.1 table claims "Multi-display: Awkward" for fbdev, "Native" for DRM. True. Also claims fbdev "Wayland: No" — also true (Wayland never supported fbdev as a back end). Keep.
- §54.2 — i.MX6ULL LCDIF can output up to 24-bit RGB but the **practical pixel clock ceiling is 70 MHz**, not "6–80 MHz typical" (the lower bound is fine but the upper bound is 70 MHz per the LCDIF clock specs in the Reference Manual; this matches §55H's note of "≤ 80 MHz" being optimistic). Reconcile the two chapters.
- §54.5 fbset output shows `geometry 800 480 800 480 32` — `32` is the bpp. fbdev emulation on top of DRM typically reports the actual bpp; if the underlying DRM is RGB565 it'd report 16. Either pick a consistent example or note "may vary."
- §54.5 line "For Qt: `-platform eglfs` (full GPU, not on i.MX6ULL — no GPU)" — correct. `-platform linuxfb` is the alternative. Good.

### Knowledge prerequisites missing

- "GBM (Generic Buffer Management)" appears in §54.5 once; not defined. One sentence: "GBM is libdrm's userspace handle to allocate DMA-coherent display buffers."
- "fbcon" appears in pitfalls without prior intro. Define: "fbcon = the kernel's framebuffer text console; appears as the early-boot text after the bootloader hands off."

### Other

- §54.10 — link `https://gitlab.freedesktop.org/mesa/drm` for libdrm source, not "kernel.org."

## Ch 54A — MTD / UBI

### MCU-engineer friendliness

- The MCU engineer has either bit-banged SPI NOR (Winbond W25Q64) or used built-in NOR on STM32. They've not necessarily met *raw NAND* — page/block/OOB/BBT concepts. Add a 6-line primer:
  > "Raw NAND is **not** memory-mapped flash like an STM32's internal flash. It's accessed via a controller (GPMI on i.MX) over a parallel bus, page-at-a-time. Each page is 2 KB data + 64 B 'spare' (OOB) area for ECC and metadata. Pages must be *erased* before writing; erase happens in *blocks* of 64 pages (128 KB). Some blocks are 'bad' (manufactured or worn out) and must be marked and skipped — that's the **bad-block table (BBT)**. The kernel hides this complexity behind MTD."
- "Erase cycle" budget — MCU folks know the STM32 flash spec of 10000 cycles. Note this is in the same ballpark for SLC NAND (~100k) and worse for MLC/TLC (~3k–10k); UBI's job is to spread wear so no single block dies first.

### Missing examples / figures

- ASCII: NAND page layout (2 KB main + 64 B OOB / spare), block (64 pages = 128 KB), die / LUN. Explain why the unit of erase ≠ unit of write.
- §54A.4 — ASCII showing one **physical eraseblock (PEB)** versus one **logical eraseblock (LEB)** — the remapping table is what UBI is. Without that picture wear-levelling is hand-wavy.

### Technical errors

- §54A.2 — `partition@2 { ... reg = <0xc00000 0x0>; ... };` — `reg = <addr 0>` is the convention in some bindings for "to end of device," but the standard NAND partition binding wants the actual size. Verify this works in your DT compiler. The mainline NAND binding doc says "size = 0" is interpreted as "extend to end" by some drivers but isn't universal. Safer to compute the real size.
- §54A.4 — `ubiformat /dev/mtd2 -O 2048 -s 2048` — `-O` is the VID-header offset and `-s` sets subpage size. The default subpage size for most chips is determined by ECC layout; manually setting both rarely necessary. Worth a note "default usually works; override if you see attach errors."
- §54A.5 line "`nand read 80800000 kernel`" — in U-Boot this typically loads from a named partition (requires `mtdparts` env or DT MTD partitions visible to U-Boot). Add the prerequisite or use raw offset: `nand read 80800000 0x400000 0x800000`.
- §54A.5 `bootz 80800000 - 81000000` — the dash is "no initramfs"; reader might wonder. Explain.
- §54A.7 "Read/write performance ~2–3× ext4-on-eMMC" — this is misleading. UBIFS read on NAND is *slower* than ext4 on eMMC because raw NAND is bandwidth-limited (~30 MB/s) and eMMC HS200 hits ~120 MB/s. The "2–3×" claim might apply to write *with compression* on small files, but the broad claim doesn't hold. Rephrase or qualify ("at small-write workloads, UBIFS's log-structured design + compression can outpace ext4-on-rotational, but on flash media it's not a general win").

### Knowledge prerequisites missing

- "OOB" (out-of-band) area mentioned in pitfalls without intro. Define when you introduce NAND geometry.
- "Subpage" never explained.

### Other

- §54A.10 link `http://linux-mtd.infradead.org/` — confirmed live, good.

## Ch 54B — V4L2 + GStreamer

### MCU-engineer friendliness

- The MCU engineer has likely brought up an OV7670 or OV5640 on STM32 DCMI by hand: I²C init script (hundreds of registers!), DCMI peripheral, DMA to a memory buffer. Bridge:
  > "On STM32 you'd write hundreds of OV5640 initialization registers via I²C, configure DCMI for the parallel data, and DMA frames into a buffer. Linux factors this into: a **sensor sub-device driver** (`ov5640.c`) handling the I²C init script + V4L2 control interface, a **bridge driver** (CSI on i.MX) handling the parallel capture, and a **video device** (`/dev/video0`) you mmap and dequeue buffers from. Same hardware, factored into media-controller topology."
- "Sub-device" concept is alien. Explain: "V4L2 calls each hardware block in the capture pipeline a *sub-device* — the sensor is one, the CSI bridge is another. Each has its own /dev/v4l-subdevN node so userspace can configure them independently."

### Missing examples / figures

- The V4L2 *pipeline graph* from the review brief is essential. ASCII:
  ```
   OV5640 (subdev)
        │ parallel YUYV @ 30fps
        ▼
   i.MX CSI (subdev)
        │ DMA
        ▼
   /dev/video0 (V4L2 video device)
        │ mmap buffer
        ▼
   user-space
  ```
- §54B.3 — the V4L2 capture sequence (S_FMT → REQBUFS → QUERYBUF → MMAP → QBUF → STREAMON → DQBUF/QBUF loop) is the V4L2 mental model. An ASCII state diagram or numbered timeline would help.

### Technical errors

- §54B.1 i.MX6ULL claim "the only camera interface on this SoC" — correct, i.MX6ULL has parallel CSI only; no MIPI-CSI2. Good clarification.
- §54B.2 DT — `clock-lanes = <0>; data-lanes = <1>;` are MIPI-CSI properties. The OV5640 on i.MX6ULL is wired parallel, not MIPI; these properties shouldn't be there. Reader will copy the example and confuse the wiring. Remove or qualify.
- §54B.2 `&csi` node — the i.MX6ULL CSI uses the staging driver historically (`drivers/staging/media/imx/`). Mainline support has been improving but verify the compatible string against your kernel target.
- §54B.4 line "i.MX6ULL has no GPU/VPU, so video encoding is software" — correct. "5–10 fps at QVGA" — depends a lot on the encoder, JPEG is much cheaper than H.264; QVGA H.264 in software on Cortex-A7 will be near-zero fps. Split into "JPEG ~30 fps QVGA, H.264 ~2 fps QVGA, 720p is impractical."
- §54B.5 `v4l2-ctl --set-ctrl=exposure_auto=1` — value 1 in V4L2 means "manual" (counterintuitive); value 3 is "aperture priority" etc. Reader will be confused. Note "value 1 = MANUAL in V4L2's enum."

### Knowledge prerequisites missing

- "media-controller" mentioned in §54B.6 lab item 2 without prior intro. The framework deserves a couple sentences earlier.
- "subdev" — see MCU-friendliness bridge above.

### Other

- §54B.8 — `drivers/staging/media/imx/` may have moved out of staging in recent kernels; verify path.

## Ch 55 — USB gadget

### MCU-engineer friendliness

- MCU engineers know USB device firmware: descriptors, endpoints, USB-CDC-ACM as a virtual COM port. The bridge:
  > "On STM32 with the USB-CDC middleware, you write `usbd_cdc_if.c` with `CDC_Receive_FS` callbacks. Linux's gadget framework factors this into 'composable function drivers' — instead of writing CDC code, you mkdir functions/acm.GS0 in configfs and the kernel's `f_acm.c` does the work. Functions can be combined: ACM + ECM (USB Ethernet) + mass storage in one device. The configfs filesystem replaces firmware-time configuration with runtime configuration."

### Missing examples / figures

- The review brief calls out: "diagram USB-gadget device-controller / gadget-driver / function relationship." Essential. ASCII:
  ```
                +-- mass_storage.0 ──┐
   UDC (chipidea)  ── gadget ──+-- acm.GS0 ─────────+── /sys/class/configfs/
   = HW endpoints              +-- ecm.usb0 ───────-+   composing as device
  ```
- Show the **USB descriptor tree** that gets built from configfs: Device descriptor → Configuration descriptor → Interface(s) → Endpoint(s). The path from "mkdir functions/acm.GS0" to the actual descriptors a PC sees is the gadget framework's main magic.

### Technical errors

- §55.2 — `mkdir functions/acm.GS0` — the format is `<type>.<name>`. `GS0` is just a name (any string); the binding to `/dev/ttyACM0` on the host is determined by the gadget's interface ordering, not the name. Reader might think "GS0" is significant. Note: "the suffix after `.` is just an identifier you choose."
- §55.2 — `bcdUSB = 0x0200`. Fine. But `idVendor 0x1d6b idProduct 0x0104` is "Multifunction Composite Gadget" — registered to Linux Foundation. Strictly only valid for testing; for production, use your assigned VID. Add a footnote.
- §55.2 `echo 2184000.usb > UDC` — the i.MX6ULL UDC node name depends on which OTG controller; `2184000.usb` is OTG1, `2194000.usb` is OTG2. Verify against `ls /sys/class/udc/`.
- §55.4 — composite gadget ECM example sets `host_addr` and `dev_addr` as MAC addresses; should clarify that `host_addr` is the MAC on the PC side, `dev_addr` is the MAC on the gadget side. Two-line note prevents confusion.
- §55.5 mentions FunctionFS but doesn't show any code. Either show a minimal FunctionFS example or remove (the "go check it out" placeholder is unsatisfying).

### Knowledge prerequisites missing

- "configfs" — first appears in §55.2 without explanation. ConfigFS is a kernel filesystem that turns *kernel object creation* into mkdir/echo. One sentence: "configfs is similar to sysfs but the other direction — userspace creates kernel objects by mkdir-ing in /sys/kernel/config. The gadget framework uses it because USB devices have so many runtime-configurable parameters."
- "ConfigFS gadget" vs "FunctionFS" — these are different. Reader may conflate. ConfigFS composes existing kernel function drivers; FunctionFS lets userspace *implement* the function. Distinguish.

### Other

- §55.7 pitfall "ACM not appearing on Windows" — note "Windows 10+ has built-in CDC-ACM driver; Win7 needs the .inf." Otherwise reader thinks they always need INF files.

## Ch 55A — Kernel timers and hrtimers

### Readability

- Concise and tight. Few issues.
- §55A.2 typo: "hrtimer (the GPT has ~30 ns resolution)" — actually the i.MX6ULL GPT can be clocked from a 24 MHz xtal (41.6 ns tick) or higher; "30 ns" should be "~42 ns" or just "tens of ns."

### MCU-engineer friendliness

- The MCU engineer knows HAL_TIM_OC_Start_IT (one-shot output compare with IRQ). Bridge: "timer_list is the 'fire callback in N jiffies' equivalent; hrtimer is the high-resolution one-shot timer with nanosecond setpoints. Both run in softirq context — equivalent to your STM32's TIM IRQ but on the kernel's soft IRQ thread (or the timer wheel for timer_list)."

### Technical errors

- §55A.1 — `mod_timer(&my_timer, jiffies + msecs_to_jiffies(100));` — correct. But note that the older calling convention `setup_timer(&timer, fn, data)` was *removed* in v4.15+; the chapter correctly uses `timer_setup` + `from_timer`. Good.
- §55A.2 `hrtimer_init` + manual `function = ...` is the older API. As of v6.6 the recommended pattern is `hrtimer_init` with the function set later or `hrtimer_init_on_stack`. There's also the newer `hrtimer_setup` available since v6.x. Worth mentioning the API trend.

### Other

- §55A.7 reference "LDD3 Chapter 7" — LDD3 is from 2005 and quite outdated for timers (no hrtimer at all). Recommend additionally pointing to a recent kernel-doc URL.

## Ch 55B — Async notification (SIGIO)

### Readability

- §55B.6 line "(no, just kidding)" — humor mid-reference is jarring; pull out the joke and just provide the real refs.

### MCU-engineer friendliness

- The mechanism is mostly POSIX, not kernel-specific. No MCU bridge needed; the chapter handles it well by being short.

### Technical errors

- §55B.3 line "Use `F_SETSIG` for realtime signals with `siginfo`" — correct concept, but missing detail: the user needs to add `SA_SIGINFO` to `sa_flags` and use `sa_sigaction` (not `sa_handler`) for `siginfo_t` access. The minimal example doesn't show this; readers will be confused.

### Other

- §55B.3 "Use when... Events come at ≤ a few per second" — emphasize this is *the* use case; everything else should be poll/epoll. Currently the bullet feels equal-weighted with the negatives.

## Ch 55C — CAN bus (SocketCAN + FlexCAN)

### Readability

- §55C.4 line "The kernel filters in software (or hardware where possible — FlexCAN has MB filtering)" — "MB" is unexplained (Message Buffer). One-line gloss.

### MCU-engineer friendliness

- MCU engineers have absolutely done CAN — bxCAN on STM32F4, MCAN on STM32G4. Bridge:
  > "On STM32 you'd configure bxCAN's CAN_FilterRegisterX, then in the RX FIFO0 IRQ unpack the message ID + data into your app buffer. Linux's SocketCAN abstracts the controller away: you `socket(PF_CAN, SOCK_RAW, CAN_RAW)`, `bind()` to `can0`, then `read()` returns `struct can_frame` already unpacked. Filters become `setsockopt(CAN_RAW_FILTER)`. The FlexCAN driver does the IRQ + DMA work behind the scenes."

### Technical errors

- §55C.1 — "**CAN-FD** ... i.MX6ULL FlexCAN supports CAN-FD on the newer revisions." This is **wrong**. The i.MX6ULL Reference Manual (line 71407, line 71449) clearly states the FlexCAN is "CAN 2.0B" — there is no mention of CAN-FD support anywhere in the RM. CAN-FD support came in newer i.MX SoCs (i.MX8M, S32). Remove this claim or correct: "i.MX6ULL FlexCAN is CAN 2.0A/B only; CAN-FD is on newer i.MX parts."
- §55C.3 "CAN-FD with bit-rate switch" example — readers on i.MX6ULL who try this will be confused when it fails. Either drop the CAN-FD example or move it to a "for other SoCs" sidebar.
- §55C.8 pitfall "Different CAN-FD speeds" — also CAN-FD-specific; remove or relegate.

### Other

- §55C.8 "single 120 Ω resistor across CAN_H/CAN_L" — clarify this is "one of the two terminations" not "instead of both." The CAN standard requires 120 Ω at each end, totaling 60 Ω across the bus. Bench setups often skip one end which is fine for short distances; the wording "stick a single 120 Ω resistor and live with reduced robustness" is OK but could read clearer.

## Ch 55D — Block device drivers

### Readability

- §55D.2 RAM disk code is the densest in the entire Part. Add inline comments tying each part to the framework: "// tag_set: blk-mq's per-disk resource pool. ops + queue depth + number of HW queues."
- The phrase "blk-mq" never expands. Define: "block multi-queue, the kernel's modern block layer that supports multiple hardware-submit queues per device (for SSDs with multiple cores serving I/O); a RAM disk uses nr_hw_queues = 1."

### MCU-engineer friendliness

- This is the chapter most foreign to an MCU engineer. They've never seen a block device. Bridge:
  > "Most embedded MCU work uses character-oriented storage: a SPI flash chip you read byte-ranges from. Linux's *block layer* is for storage with fixed sector size (512 B or 4 KB), random access, and the kernel's page cache between userspace and the device. The bio struct represents one read/write request — its `bv_page[]` are kernel pages, `bv_offset`/`bv_len` describe a byte range. Drivers process bios."
- A simple "every read() ends up as a bio submitted to your queue_rq" picture would orient the reader.

### Missing examples / figures

- ASCII timeline: userspace `read(fd, buf, 8192)` → ext4 mkmap pagecache miss → bio submitted → blk-mq dispatch → driver queue_rq → memcpy → blk_mq_end_request → wake userspace.

### Technical errors

- §55D.2 — `void *user_buf = kmap_local_page(bvec.bv_page) + bvec.bv_offset;` then `kunmap_local(user_buf);` — the kunmap variant should take the address *returned by kmap_local_page* (i.e., before the offset adjustment), not the offset-adjusted pointer. Bug:
  ```c
  void *page_addr = kmap_local_page(bvec.bv_page);
  void *user_buf = page_addr + bvec.bv_offset;
  /* ... copy ... */
  kunmap_local(page_addr);
  ```
  Reader will copy the broken code.
- §55D.2 — `r->disk->major = 240;` — hardcoding major number 240 risks collision. The portable way is `register_blkdev(0, "myram")` to get a dynamic major, then assign. Or use `blk_mq_alloc_disk` which handles major allocation. Note the issue.
- §55D.2 — `nr_hw_queues = 1` on a single-CPU machine is correct. Fine.
- §55D.4 line "fio: IOPS=350k" on i.MX6ULL is implausible. A 696 MHz Cortex-A7 doing 4K memcpy + ext4 overhead can't sustain 350k IOPS — that's modern desktop NVMe territory. The number is probably copy-pasted from a desktop benchmark. Recompute or remove.

### Knowledge prerequisites missing

- "vmalloc" used in code without intro. Reader has likely met kmalloc only. One sentence: "vmalloc allocates virtually-contiguous (but physically discontiguous) memory; useful when you want a big buffer that doesn't fit in kmalloc's order-N physical block."
- "page cache" implicit in the discussion of FS-on-block. Brief intro would help.

## Ch 55E — WiFi + wpa_supplicant

### MCU-engineer friendliness

- The MCU engineer has used ESP8266/ESP32 from an AT command perspective, or built embedded WiFi via SDIO with custom firmware. Bridge:
  > "On a bare-MCU you'd talk to an ESP8266 over UART AT commands or use an SDIO WiFi chip with vendor binary blobs and a proprietary API. Linux factors this into a chip driver (`brcmfmac` etc.) + a generic kernel WiFi core (`mac80211` + `cfg80211`) + a userspace supplicant. You write zero code; you just feed firmware + nvram + config."

### Missing examples / figures

- ASCII bring-up flow showing: kernel sees SDIO device → matches `brcm,bcm4329-fmac` → driver requests firmware from `/lib/firmware/brcm/` → firmware uploaded → chip enumerates → wlan0 appears → mac80211 + cfg80211 register interfaces → wpa_supplicant connects → DHCP. Each step is a debug point.

### Technical errors

- §55E.2 DT `compatible = "brcm,bcm4329-fmac"` for AP6212 — AP6212 is a BCM43438/BCM43430 module; the compatible should be more specific in current mainline (e.g., `brcm,bcm4329-fmac` is generic but the firmware file name keyed off chip-id is what actually matters). The DT compatible was reworked in recent kernels to use the chip-specific string. Verify.
- §55E.4 dmesg says "bcm4330-fmac initialized" but the chip is supposedly BCM43430 (AP6212). Either copy-paste mismatch or the example is from a different board.
- §55E.5 — `wpa_supplicant -B -i wlan0 -c /etc/wpa_supplicant.conf -D nl80211` — for `key_mgmt=SAE` (WPA3), wpa_supplicant must be built with `CONFIG_SAE=y` and `CONFIG_IEEE80211W=y`. Note this as a build-time concern.

### Other

- §55E.8 pitfall "32 KHz clock missing" — good. Worth explicitly noting that on AP6212/AP6256 the LPO is the WiFi chip's deep-sleep clock; without it BT side breaks first, WiFi survives.

## Ch 55F — Cellular modems

### MCU-engineer friendliness

- MCU folks have done UART AT commands with SIM800 / SIM7600. The bridge: "UART AT modems work the same as on STM32 — chat scripts replace your hand-written state machine. USB modems on Linux let you skip AT entirely via QMI/MBIM — much more reliable. ModemManager is the daemon that hides QMI complexity."

### Technical errors

- §55F.4 — `qmicli -d /dev/cdc-wdm0 --wda-set-data-format='raw-ip'` then `echo Y > /sys/class/net/wwan0/qmi/raw_ip` — these are redundant for most current firmware. Mention that newer kernels and ModemManager set this automatically.
- §55F.5 — UART modem example using `/dev/ttymxc1` and PWRKEY GPIO sysfs path `/sys/class/gpio/gpioN/value` — sysfs GPIO is deprecated. Recommend libgpiod (`gpioset` command) which was introduced in earlier chapters.
- §55F.7 pitfall "EC25 needs `raw_ip` mode" — yes, but as noted above this is mostly automatic now.

### Other

- §55F.6 lab item 4 SMS test ("Cost: ~$0.05") — varies by carrier. Reword as "may be billed."

## Ch 55G — Multi-touch (GT911)

### Readability

- §55G.5 "Try combinations until the touch matches the cursor on screen" — replace "trial and error" feel with a systematic recipe: "Touch top-left corner with one finger; if reported X is near max not 0, set `inverted-x`; if reported Y is large but you touched top, set `inverted-y`; if X tracks finger Y-motion, set `swapped-x-y`. Apply one fix at a time."

### MCU-engineer friendliness

- MCU folks have done resistive touch with calibration (4-point or 5-point). Bridge:
  > "Resistive touch on MCU = ADC reads → 4×4 calibration matrix → screen coordinates. Capacitive controllers like GT911 already report screen-space coordinates over I²C, so software calibration is just *orientation* (rotate / flip) — set in DT, no per-unit calibration needed. MT-B is the kernel input protocol for *multiple* simultaneous touches; each tracked finger has a 'slot.'"

### Missing examples / figures

- ASCII showing the slot model: 5 slots (max), each carrying (tracking-id, X, Y). When finger 0 lifts: tracking-id of slot 0 → -1. Easier to grok than the linear ABS_MT_* listing.

### Technical errors

- §55G.2 `irq-gpios` and `interrupts` both specified — the binding actually wants one or the other depending on driver version. Check mainline `goodix.yaml`.
- §55G.3 "INT pin level at reset selects I²C address" — correct; but note that the modern `goodix.c` driver supports both 0x5d and 0x14 (and handles the reset sequence itself), so the DT just declares the address you've wired.

### Knowledge prerequisites missing

- "evtest" appears in §55G.4 without intro — though it's plausible the reader has met it in Ch 45's input chapter.

## Ch 55H — RGB-to-HDMI bridge (sii902x)

### Readability

- Concise and clear. Good.

### MCU-engineer friendliness

- MCU folks have not generally added HDMI to their boards (HDMI sinks expect a PHY-grade signal). Bridge: "The SoC has no HDMI PHY; sii902x is an external chip that takes your parallel RGB and adds the HDMI TMDS encoding + DDC negotiation. From Linux's perspective it's a 'DRM bridge' — a building block that hangs between the CRTC and the HDMI connector. No bridge code to write."

### Missing examples / figures

- ASCII of the bridge chain: `LCDIF (CRTC) → sii902x (bridge) → hdmi-connector → cable → sink`. Show how each is a DRM object.

### Technical errors

- §55H.1 "1080p60" — i.MX6ULL LCDIF tops out at ~70 MHz pixel clock; 1080p60 needs 148.5 MHz. §55H.3 correctly says 1080p doesn't work. But §55H.1 lead-in promises "HDMI 1.4 at up to 1080p60" which is the *chip's* capability — clarify "the bridge supports 1080p60, but i.MX6ULL LCDIF can't drive the pixel clock that fast; expect 720p max on this SoC."
- §54 pitfall says LCDIF max is "~80 MHz"; §55H.3 says "~80 MHz" then settles on "74.25 MHz for 720p"; values vary. Reconcile across chapters.

### Other

- §55H.6 pitfall "RGB vs YCbCr" — correct that some old TVs prefer YCbCr, but sii902x defaults to RGB888 and modern sinks all accept it. Most readers won't hit this; consider de-emphasizing.

## Ch 55I — Rust for Linux

### Readability

- Good as an overview. The "this doesn't apply to your i.MX6ULL board" framing is honest and good.

### MCU-engineer friendliness

- MCU folks may have heard of "Rust on embedded" via embassy / RTIC. Note: "Kernel Rust is different from embedded-Rust (no_std crates like embassy). Kernel Rust links against the kernel's own `kernel::` crate, runs in kernel space, and uses the kernel's allocators. embassy code wouldn't compile here."

### Technical errors

- §55I.1 "ARM32 (i.MX6ULL's architecture) is NOT yet supported." Confirmed — as of writing, Rust-for-Linux supports x86_64, arm64, RISC-V, LoongArch; ARM32 is not on the list. Good.
- §55I.2 "rustup toolchain install 1.74.0" — kernel-Rust pins a specific version per kernel release. The version in the chapter is illustrative; reference `scripts/min-tool-version.sh rustc` for the real number. Note that.
- §55I.3 — the `module!` macro syntax shown is roughly current but check against a recent kernel (the keys `type:`, `name:`, etc. have evolved). At least the `license: "GPL"` and `pr_info!` calls match v6.6+.
- §55I.5 "kernel::miscdev::Registration" — verify against current mainline; the API has been refactored multiple times. Same for `kernel::file`. These are moving targets and the chapter should warn the reader to verify against their kernel version.

### Other

- §55I.6 Cons "Rust version requirements change with each kernel" — true. Could also note: rust-for-linux now uses stable Rust 1.78+ since v6.10 (no longer requires nightly), an important practical improvement.
- §55I.9 link to https://github.com/Rust-for-Linux is dated (the project lives in mainline now). Update to point at upstream kernel docs primarily, github as historical reference.



---

# Part VIIa — Cookbook (Storage + Sensors): Review

## Cross-cutting observations

These issues appear across multiple chapters; per-chapter notes only call them out where the instance is particularly bad or where there is something specific to add.

- **`class_create(THIS_MODULE, ...)` is wrong on modern kernels.** Ch64 `mf_probe` and Ch65 `me_probe` both call `class_create(THIS_MODULE, "name")`. Since v6.4 (and signaled as deprecated long before), `class_create` takes only `(const char *name)` — the `THIS_MODULE` argument was dropped. Code as written will not compile against a current mainline kernel. Either drop the argument, or note explicitly that the snippet targets a specific older kernel.
- **`i2c_driver.probe` prototype is wrong on modern kernels.** Ch65/Ch67/Ch68/Ch70/Ch72/Ch73/Ch75/Ch76/Ch79/Ch80/Ch81 all declare `static int X_probe(struct i2c_client *client, const struct i2c_device_id *id)`. Since v6.3 the framework switched to single-argument `probe(struct i2c_client *)` (the legacy form is `probe_new`, now removed). Either pick the modern prototype throughout, or add one footnote explaining the kernel-version dependency. The book has just spent Part VI teaching probe patterns — the cookbook code should not silently regress.
- **`i2c_driver.remove` returns void in modern kernels.** Ch65 has `static int me_remove(struct i2c_client *client) { ... return 0; }`. Mainline switched `remove` to `void` in v6.x. Same fix-or-footnote remark.
- **`module_init`/`THIS_MODULE` & misc kernel-API churn.** A general "these snippets are pseudocode targeting kernel ~5.10–6.1; mainline ≥ 6.5 needs minor API tweaks" disclaimer would save the reader hours.
- **MCU-engineer bridge is uneven.** The intro paragraphs of each chapter often mention what an MCU engineer would do, but inside the driver walk-throughs the analogy disappears just when it would help most (e.g., "on STM32 you'd write `I2C->DR = byte; while(!(I2C->SR1 & TXE));`; here `i2c_smbus_write_byte_data` blocks because the kernel scheduler may put you to sleep — so never call it from an IRQ handler"). Add 1–2 explicit STM32/HAL-vs-Linux-API comparisons per chapter, especially around the first I²C and first SPI calls.
- **Sleeping vs atomic context is never spelled out.** A reader fresh from STM32 will see `msleep`, `usleep_range`, `mutex_lock`, `i2c_smbus_*` and `spi_sync` next to each other without being told these may sleep — and therefore why they cannot live inside a hard IRQ. Part VI introduced this, but in the cookbook chapters there is no recap, and several drivers (Ch71 `ma_irq_thread`, Ch79 `mh_irq_thread`) explicitly run sleeping calls from threaded IRQs without explaining *why that's legal here but not in a top-half hardirq*. One paragraph in the cross-cutting prelude or at the first appearance would settle this.
- **No `dmesg` "expected output" for most from-scratch drivers.** Most chapters show `cat /sys/.../value` succeeding, but skip the `dmesg | tail` after `insmod` that shows the `dev_info` line(s), bus-id, IIO device-name, IRQ allocation. That output is the *first* thing the reader will look at; show what "good" looks like.
- **No ASCII wiring diagrams in many chapters.** Ch64 and Ch65 have good wiring sketches; Ch67/68/69/70/71/72/73/74/75/76/77/78/79/80/81 either have none or only a partial physics diagram. A 6-line "i.MX6ULL pad ➜ chip pin" sketch per chapter would set the reader up before they hit the DT.
- **DT `pinctrl_*` references are unresolved.** Almost every chapter shows `pinctrl-0 = <&pinctrl_xxxx>` or `&i2c1 { ... }` without showing what's in `pinctrl_xxxx` or where `&i2c1` is declared. The reader needs to be told once ("`&i2c1` and `pinctrl_i2c1` come from `imx6ull.dtsi` and your board's pinctrl group respectively — see Ch 40"), then it can be assumed.
- **Pin assignments are never cross-checked against the reference manual.** No chapter cites the IOMUXC table from `IMX6ULL_Reference_Manual.md`. For example Ch78 says `&sai2 { ... pinctrl-0 = <&pinctrl_sai2>; ... }` without telling the reader which physical pads carry SAI2_TX_BCLK / SAI2_TX_SYNC / SAI2_RX_DATA on the iMX6ULL — yet picking the wrong pad is the most common bring-up failure. Add one "pad table" per chapter (or one shared appendix referenced from each).
- **`pa-mini` shell prompts and the implied board.** The transcripts use `[root@pa-mini:~]#` — fine — but the book has not yet introduced "pa-mini" as a board name in earlier parts (per the TOC). A single sentence at the start of Part VII saying "the prompt `pa-mini` is our reference iMX6ULL board; substitute your own hostname" would head off confusion.
- **The "from-scratch driver" is sometimes a thin wrapper around the mainline driver's logic without acknowledging it.** Ch67/68/70/73/75/76/79/80 are *good* examples of true from-scratch (per cookbook-depth requirement). Ch66 and Ch78 explicitly *do not* implement from-scratch and explain why — also good. But Ch65 and others would benefit from a one-line "what makes this 'from scratch' vs the mainline is X" sentence to keep the contract clear.
- **No glossary callouts for first-use IIO terms.** "INFO_RAW", "INFO_PROCESSED", "INFO_SCALE", "scan_index", "scan_type", "INDIO_DIRECT_MODE", "INDIO_BUFFER_TRIGGERED" appear without a quick recap. Part VI presumably covers this, but a 5-line "IIO sysfs key" recap at the start of Group B (Ch67) would help — the reader will be flipping back constantly otherwise.
- **English/readability.** Many chapter intros use compressed noun-phrase sentences ("Cookbook chapters should be HIGH-VALUE recipes — DT snippet, kernel config..."). For a non-native English reader, these read as bullet-lists masquerading as prose. The body text is usually fine; the intros are the worst. Smooth them out: "These chapters are recipes. Each gives you a DT snippet, the kernel config it needs, an expected `dmesg`, an expected `/sys` or `/dev` path, a userspace test command, and the common ways it fails."
- **`i2c_smbus_read_i2c_block_data` semantics.** Ch67, Ch70, Ch72, Ch79, Ch80 all use this. It is limited to 32 bytes per call, sets the register pointer with one byte, and uses SMBUS "block read with length byte" semantics on some adapters. Most i.MX users get away with it, but flagging this once would prevent surprise when ports get to a controller that's stricter.
- **`devm_iio_triggered_buffer_setup` called with all-NULL handlers (Ch71, Ch79).** Passing `NULL, NULL, NULL` registers the triggered-buffer infrastructure with *no* handler — meaning if a user does `echo 1 > buffer/enable` against an hrtimer trigger, nothing pushes samples. The drivers depend instead on the chip's own watermark/data-ready IRQ to push samples. Spell this out, otherwise a reader trying to bind an hrtimer trigger will get an empty buffer and have no idea why.

## Ch64 — QSPI NOR flash

### Readability
- §64.1 opening: "QSPI NOR fits when storage need is < 32 MB, you want fast/deterministic boot..." — comma splices and missing "if". Suggest: "QSPI NOR fits when the storage need is under 32 MB, the system wants fast and deterministic boot, the device should be theft-resistant (soldered), and there is no bulk user data to store."
- §64.4 "Three invariants that catch beginners" — strong section, just fix point 3's grammar: "first requires the relevant sector to have been erased to all-0xFF" → "first requires the sector to have been erased to all 0xFF".
- §64.10 prose around `boot_qspi=...` is dense — break into the three command lines and explain each. Currently relies on the reader knowing U-Boot env syntax.

### MCU-engineer friendliness
- The opening §64.4 protocol description is excellent — exactly the right tone for a reader who has bit-banged an SPI flash on an STM32. Keep doing this. Reinforce: "on bare metal you'd write `SPI->DR = 0x9F` and busy-wait `SPI->SR & RXNE`; here `spi_mem_exec_op` does the equivalent — but may sleep waiting on DMA completion, so it cannot be called from an IRQ handler."

### Missing examples / figures
- Show the actual `dmesg` after `insmod myflash.ko` (just the bus enumeration line + JEDEC line) — not only the `cat /dev/myflash | hexdump` output.
- A timing diagram of "page program 256 B + status poll loop" with annotated µs ranges would crystallise §64.4's three invariants.
- No `i2cdetect`-equivalent for SPI — show that `/dev/spidev3.0` exists (or that `ls /sys/class/spi_master/spi3/` shows the bus) so the reader knows how to verify SPI is alive before loading the chip driver.

### Insufficient depth
- This chapter meets the cookbook-depth requirement well (mainline internals, then from-scratch ~250-line driver, then mainline DT). Nothing to flag.

### Technical errors
- §64.6, `spi_nor_read` skeleton uses `nor->addr_nbytes` — the mainline field is currently `nor->addr_nbytes` in 6.x but was `nor->addr_width` historically. Footnote the kernel version, or accept that small skew is OK.
- §64.6, `spi_nor_wait_till_ready` uses a 40-second deadline — true for chip-erase but wildly long for sector-erase. Real driver uses per-operation deadlines from `info->mfr_flags`. Not wrong, just simplified — flag it.
- §64.7 `mf_probe` calls `class_create(THIS_MODULE, ...)` — see cross-cutting.
- §64.7 `mf_xfer` builds `hdr[5]` but only ever writes 4 bytes (`hdr_len = 4` at most). Fine but suggestive of "I planned to support 4-byte addressing"; either drop the unused byte or implement 4-byte mode.
- §64.7 — the chip type checking `if (id[0] != 0xEF || id[2] != 0x18)` only accepts a 16 MB W25Q128 (manufacturer 0xEF, capacity-code 0x18). Fine for the from-scratch demo, but call out explicitly that a W25Q64 (0xEF 40 17) will refuse to probe even though the protocol is identical.
- §64.9 "XIP from QSPI" claims max ~50 MB/s on i.MX6ULL — the i.MX6ULL QSPI controller maxes out at 60 MHz quad-mode = ~30 MB/s sustained from typical NOR. The 50 MB/s figure looks lifted from a higher-spec part (i.MX6Q/SX QSPI). Verify against the i.MX6ULL reference manual §8.6 or substitute a measured number.

### Other
- Lab #1 says "Without your driver loaded, use raw SPI via `/dev/spidev*` to send `0x9F`" — but `/dev/spidev*` only appears if the DT binds something to `compatible = "spidev"`. Tell the reader how to get spidev exposed for this lab (DT snippet, kernel config, the `spidev` ACL warnings in dmesg). Otherwise the lab is a dead end.
- `flash_erase` and `nandwrite` are used in §64.8 — but those come from `mtd-utils`. Mention that and that `nandwrite` works on NOR despite the name. Beginners often don't realize.

## Ch65 — I²C / SPI EEPROM

### Readability
- §65.2 table comment "Pick AT24C02 for tiny ID storage (MAC, serial), AT24C512 for calibration tables, 25LC512 for SPI bus or factory-speed bulk programming." reads fine.
- §65.4 ASCII diagram of I²C transaction has misaligned ACK arrows on the second line; the byte boundaries don't line up with the arrow positions. Either fix the alignment, or replace with a clean per-byte table.

### MCU-engineer friendliness
- Add: "On STM32 you'd write the register pointer with `HAL_I2C_Mem_Write(... &addr, 1, ...)` then `HAL_I2C_Master_Receive`. Here `i2c_transfer(adapter, msgs, 2)` does the same two-segment transaction in one kernel call — the second `i2c_msg` with `I2C_M_RD` flag is the read phase."

### Missing examples / figures
- No `i2cdetect -y 1` output shown anywhere in this chapter. Add a 3-line example.
- No `dmesg` after `insmod myeeprom.ko` — only the `cat` output.

### Technical errors
- §65.6 `me_probe` signature uses the legacy two-argument form — see cross-cutting.
- §65.6 `me_remove` returns int — see cross-cutting.
- §65.6 `class_create(THIS_MODULE, "myeeprom")` — see cross-cutting.
- §65.6 `me_fops_read` allocates `u8 kbuf[EEPROM_SIZE]` on the kernel stack (256 B). Fine for this tiny EEPROM, but generalising the pattern to larger AT24C512 would put 64 KB on the stack — disaster. Add a remark.
- §65.6 The ACK-poll loop sends a 1-byte write (`zero = 0`) as the poll. Cleaner is `i2c_smbus_xfer` with a zero-length write (the canonical "address probe"). Functionally equivalent here — but worth a sentence noting the convention used in `at24.c`.
- §65.7 "The mainline `at24` driver registers an nvmem provider. The FEC driver consumes the `mac-address` cell at probe — six bytes from offset 0 become eth0's MAC address." This is *the* killer feature, but the link from "FEC" to "Ethernet MAC" is left implicit. One sentence: "FEC is the iMX6ULL's Ethernet MAC peripheral (Ch 88 onwards in this book) — `fec1`'s `nvmem-cells` property pulls the MAC address from EEPROM at boot."
- §65.8 `awk -F: '{for(i=1;i<=NF;i++) printf "%c", strtonum("0x"$i)}'` is a busybox-awk gotcha — `strtonum` is gawk-specific. On a typical busybox-based iMX6ULL rootfs this command fails silently. Use `printf` + a small shell loop instead.

### Insufficient depth
- The mainline `at24` walk-through skips the multi-bank machinery (large chips that span multiple I²C addresses). The footnote mentions it but doesn't show. Half a paragraph on how `at24_select_regmap` picks the right bank would be welcome.

## Ch66 — SD card and eMMC deep dive

### Readability
- §66.5 opening: "Unlike QSPI and EEPROM (Ch 64/65) — where a from-scratch driver was tractable in ~200 lines — an MMC/SD host controller driver is genuinely a different scale." — overlong em-dash sentence. Suggest: "QSPI and EEPROM each fit in ~200 lines of from-scratch driver. An MMC/SD host controller is a different scale: the SD spec is ~700 pages, the eMMC spec ~400."
- §66.6 "**That's the abstraction**." — bold standalone sentence reads as a slogan; just integrate into the surrounding paragraph.

### MCU-engineer friendliness
- The "trace a single 4-KB read" walkthrough in §66.6 is the highlight of the chapter. Add an MCU mental model: "On STM32 the SDIO peripheral does a similar dance: program CMD register, kick off DMA, wait for transfer-complete IRQ. The big difference in Linux is the layering — block → MMC core → host driver. Each layer adds queueing, scheduling, and error recovery that bare-metal SDIO code doesn't have."

### Missing examples / figures
- Show `cat /proc/mounts` and `lsblk` or `cat /sys/block/mmcblk1/...` after eMMC enumerates — confirms the kernel saw the chip and what partitions are present.
- The "tracing a single 4-KB read" section would benefit from an actual ftrace snippet of output, not just the prose description. Lab #1 says to run ftrace; show the expected trace lines.

### Insufficient depth
- This chapter deliberately doesn't include a from-scratch driver — and explains why (the SD spec is 700 pages). That's the right call given the cookbook-depth requirement *would* technically be violated, but the chapter justifies the omission and replaces it with a layer-tracing walkthrough that is genuinely educational. Author-memory note: this might still trip the "Part VII chapters MUST show driver internals + a from-scratch implementation" rule. Recommend you either (a) keep this exception and add a paragraph in the Part VII introduction listing it explicitly, or (b) write a tiny "host driver skeleton" beyond the 20-line one in §66.6 — say, a 100-line "pretend the host is bit-banged on GPIO" implementation showing how the `mmc_host_ops` callbacks plug in.

### Technical errors
- §66.5 command table has "CMD8 (eMMC) | SEND_EXT_CSD | Read 512-byte EXT_CSD block". CMD8 sent to an eMMC during init is SEND_EXT_CSD, but the same opcode to an SD card is SEND_IF_COND — the row above. The table is correct but the dual-meaning is the kind of detail that catches beginners; add a footnote.
- §66.6 `sdhci_xxx_probe` uses `sdhci_pltfm_init` and `sdhci_get_of_property` — `sdhci_get_of_property` was renamed `sdhci_get_property` in 5.15. Pick one and footnote.
- §66.10 `fio --name=randwr` — the line `write: IOPS=2500, BW=10MiB/s` for HS200 eMMC is plausible for budget eMMC but optimistic for high-end industrial parts. Worth qualifying with "depends heavily on chip; budget consumer eMMC may be 5× slower at random 4k write."

### Other
- §66.7 `mmc extcsd read /dev/mmcblk1` — confirm the user has installed `mmc-utils` (separate package). Add one line.

## Ch67 — Temperature / humidity / pressure

### Readability
- §67.2 "All three are 4–6 pin packages" — fine but the ASCII schematic that follows uses `─╳─` to denote what exactly? Pull-up resistor? Pad? The two leftmost glyphs `┌── A0 ────────►` look like there are extra `┌` brackets that don't close. Clean up the ASCII.
- §67.5 "The chip's calibration coefficients (silicon process variation)" — slightly tense-mismatched. "These coefficients capture per-chip silicon process variation."

### MCU-engineer friendliness
- The §67.4 "compensation formula is in the driver, not the chip" point is exactly the kind of insight an MCU engineer needs. Sharpen: "On an STM32 you'd port Bosch's reference C functions directly into your project; the Linux driver does the same thing — *the math doesn't move into the kernel*, it just lives in the kernel module rather than your application." That tells the reader the Bosch code is identical across all platforms.

### Missing examples / figures
- Show `i2cdetect -y 1` and `i2cdump -y 1 0x76` snippets — the chapter mentions them in the lab but doesn't show what they look like.
- A flowchart of "forced measurement: write ctrl_meas → sleep 10 ms → read 8 bytes → 3 compensation calls → return" would lock in the data path.

### Technical errors
- §67.1 table: "`sht3x.c` (hwmon) + `humidity/shtc1.c`-style IIO not yet for SHT3x in IIO; `sht3x` is hwmon" — actually `drivers/iio/humidity/sht3x.c` exists in modern kernels (added in 6.8). Update.
- §67.5 `mb_probe` legacy two-argument form — see cross-cutting.
- §67.5 `mb_read_calib` uses `i2c_smbus_read_i2c_block_data` for 24 bytes — but the SMBus block-data limit is 32, and *some* I²C controllers reject blocks of 24 bytes (only 32 or smaller multiples). Mostly works on i.MX, but worth flagging.
- §67.5 H4/H5 decoding: `m->H4 = (s16)(((s8)buf[3] << 4) | (buf[4] & 0x0F))` — this is wrong if `buf[4] & 0x0F` has the top nibble overlap with the sign-extended high byte. The Bosch reference code uses unsigned shifts then sign-extends explicitly. Cross-check this byte by byte against datasheet §8.2.
- §67.6 "SHT3x reset = `0x30 41`" — Sensirion's soft-reset command is actually `0x30 A2`. Verify against the datasheet command table.
- §67.7 AHT20 reset is `0xBA` — the datasheet says reset command is `0xBA` (single byte, written without register). OK.
- §67.7 AHT20 packing: "H and T raw values are 20-bit, packed across 5 bytes with a nibble split at byte 3" — text says 5 bytes, but the worked read shows 7 bytes (S, H0, H1, H2/T0, T1, T2, CRC = 7). The pack is 6 data bytes + 1 CRC. Fix the description.
- §67.8 mainline DT for BME280 — `compatible = "bosch,bme280"` is correct, but `CONFIG_BMP280=y` plus `CONFIG_BMP280_I2C=y` — the second now requires `CONFIG_BMP280_I2C=m` to be a separate module, or both `y`. Mention dependency.

### Insufficient depth
- The chapter is excellent — protocol + mainline internals + from-scratch + compensation math + SHT3x/AHT20 conversion sketches. No depth complaints.

### Knowledge prerequisites missing
- "regmap" appears in §67.4 ("decoupled via regmap") — this *was* introduced in Ch 50 per the memory note. Just a forward-ref pointer "(Ch 50)" would help readers who skipped ahead.
- "IIO_VAL_INT_PLUS_MICRO" and "IIO_VAL_INT_PLUS_NANO" appear without explanation; a one-line "scale conventions" callout would help.

## Ch68 — Light & color sensors

### Readability
- §68.2 "The user never sees the lambdaweighting" — "lambda-weighting" with a hyphen (and a word missing space).
- §68.4 ends abruptly after the read_raw snippet; segue into §68.5.

### MCU-engineer friendliness
- Bring across the MCU analogy explicitly: "If you've used a BH1750 on Arduino, you wrote `Wire.write(0x10); delay(180); Wire.requestFrom(...,2);`. Linux's `i2c_smbus_write_byte` + `msleep` + `i2c_master_recv` is the same sequence — but `msleep(180)` actually puts your driver context to sleep, releasing the CPU; on Arduino `delay()` busy-waits."

### Missing examples / figures
- Show actual `cat /sys/.../in_illuminance_raw` and `_scale` for a few lighting scenarios (dark, indoor, sunny window) — the chapter only shows two readings.
- No physical wiring diagram for the BH1750. The chip has VCC, GND, SDA, SCL, ADDR (and DVI on some breakouts). Show it.

### Technical errors
- §68.5 `mb_probe` two-argument legacy form — see cross-cutting.
- §68.5 `mb_read_raw` returns `IIO_VAL_INT` for `_PROCESSED` after computing `((u32)count * 1000) / 12 * 10` — but the IIO `_processed` ABI expects the value in the *natural unit* (lx) and `IIO_VAL_INT_PLUS_MICRO` for fractions. Reporting `lux × 1000` as `IIO_VAL_INT` makes user-space think it's reading 410000 lx, not 410 lx. The mainline driver uses `_processed` returning lx (an integer), not millilux. Re-check the unit.
- §68.5 `mb_remove` returns 0 (int) — see cross-cutting.
- §68.6 TSL2561 formula coefficients (`0.0304`, `0.062`, etc.) — these come from the datasheet's "CS package" formulation. The "T/FN package" has different coefficients. Most modules sold are T-package; clarify.
- §68.7 "VEML7700 has 6 integration times (25/50/100/200/400/800 ms) and 4 gains" — datasheet actually lists `IT = 25/50/100/200/400/800` × `gain = 1, 2, 1/4, 1/8`. The integration values and gains both list correctly; just worth a footnote on which combinations are valid (not all 6×4 work due to internal saturation).

### Other
- Lab #4 "expose `_integration_time` as a writable IIO attribute. Verify writing 1 / 0.5 / 2 changes the effective integration time." — but BH1750's integration is fixed at "L-mode 16 ms / H-mode 120 ms / H-mode2 240 ms" — there's no continuous scaling. The MTREG trim varies sensitivity, not integration time. Re-word the lab.

## Ch69 — Air quality / gas / particulate matter

### Readability
- §69 intro "**NDIR is physics; metal-oxide is correlation; laser scatter is counting**" — strong and memorable. Keep.
- §69.4 transitions abruptly between "user-space: `cat /sys/.../in_concentration_co2_input` returns eCO₂ ppm" and the next paragraph. Add a one-line bridge.

### MCU-engineer friendliness
- For the PMS5003 SerDev section: tell the MCU reader that SerDev is essentially a "kernel UART line discipline" with cleaner API — equivalent to "I used to call `HAL_UART_Receive_IT` and accumulate bytes in a callback; SerDev's `receive_buf` is the same callback, just with kernel context."

### Missing examples / figures
- The PMS5003 wiring diagram is missing. Show: PMS5003 TX → iMX6ULL UART2_RX, common ground, 5 V supply (PMS5003 cannot tolerate 3.3 V supply but its TX is 3.3 V CMOS compatible). The 5 V supply detail catches people.
- Show the actual UART2 DT node and which iMX6ULL pads back it. Cross-reference IOMUX.

### Technical errors
- §69.3 SCD30 float decoding: `bits = (raw[0]<<24) | (raw[1]<<16) | (raw[3]<<8) | raw[4];` — correct in that it skips the CRC bytes at indices 2 and 5. Cast `*(float*)&bits` is technically undefined behaviour by strict aliasing; use `memcpy(&f, &bits, 4)` or a union. Production drivers do this; mention it.
- §69.4 CCS811 reset register address: "0xFF SW_RESET" — wait, the chapter says "0xB0 SW_RESET" in the same table. Pick one. Datasheet: SW_RESET is at register 0xFF; 0xB0 is BASELINE. Cross-check.
- §69.4 "Wait ≥ 70 ms" after power-on for CCS811 — actually datasheet specifies ≥ 1 second (boot time). The 70 ms figure is the *minimum delay between writes*, not the boot delay. Verify.
- §69.5 `mp_probe` for serdev — `serdev_device_open` returns 0 on success; missing close-on-error path. devm doesn't auto-close serdev unless you use `devm_serdev_device_open` (kernel 5.5+). Either use the devm variant or add explicit cleanup.
- §69.5 PMS5003 frame field at offset 30 is the checksum — and the checksum is *sum of bytes 0..29* per the manual, which the code matches. Good. But you should mention that the frame's "length" field at offset 2 is the *remaining* bytes count, not the total — useful for handling other PMSxx variants with different sizes.

### Insufficient depth
- The CCS811 section says "writes `0xF4` (no data) to switch to app mode" but doesn't show the actual I²C transaction (it's a one-byte write with no register address — special form). Demonstrate.
- The SerDev section is treated almost too lightly — it's pedagogically the most interesting framework introduced here. Spend another half-page on what `serdev_device_set_client_ops` does and how the kernel knows when bytes arrive (versus polling).

## Ch70 — I²C IMUs

### Readability
- §70.4 "1000/s = unacceptable" reads as a stat aside in the middle of a sentence. Move to a parenthetical or break out. Also: "30 µs per sysfs read × 6 axes × 1000 Hz = 18 % of one CPU just on the syscall overhead" — the arithmetic is `30e-6 × 6 × 1000 = 0.18`, i.e. 18 %. Good. But "1000 Hz" reads as if it's the *per-axis* rate; clarify that's the full sample rate.
- §70.10 Madgwick C-snippet is *almost* C but uses operator overloading (`q + q`, `q * 0.5`) — non-native readers will assume that's real C. Either use explicit function calls (`quat_add`, `quat_scale`) or label the snippet "pseudocode".

### MCU-engineer friendliness
- The "30 µs per sysfs syscall" budgeting is gold. Add an explicit comparison: "On STM32 you'd just write a tight ISR reading the FIFO into a circular buffer; in Linux that 'tight ISR' is the kernel scheduler waking your trigger-handler thread — same effect, more layers."

### Missing examples / figures
- Show actual `dmesg` after probe (the IIO device assignment, trigger registration, IRQ allocation).
- Show what the captured `imu.bin` looks like — a hex dump of one sample to make the byte layout concrete.
- No physical wiring diagram. INT pin → which GPIO, what pull-up?

### Insufficient depth
- This chapter is the longest and most thorough in the part. Excellent. Just confirm the IIO buffer / trigger explanation in §70.4 actually matches what Part VI introduced — if Part VI's IIO chapter is light on triggers, expand here. The "Two-stage IRQ path for hardware trigger" passage is a good place to point out where the threaded-IRQ pattern fits (Ch 43 per cross-reference).

### Technical errors
- §70.1 table: "Mainline driver | `inv_mpu6050_*.c` family | same | same" — the ICM-20948 mainline support is in `drivers/iio/imu/inv_mpu6050/` but registered as a *new* `inv_icm20948` family in recent kernels (formerly `inv_mpu6050` with bank quirks). Slight historical mismatch.
- §70.5 `inv_mpu_core_probe` skeleton uses `devm_iio_triggered_buffer_setup(...)` — pass the function names but skip the actual function signature; OK as illustrative.
- §70.5 channel macros: `INV_MPU6050_CHAN` defines `scan_type = { .endianness = IIO_BE }` — correct for MPU6050. ICM-42688 outputs *little-endian* — a footnote helps here, especially since the SPI IMU chapter (Ch71) makes a big deal of this.
- §70.6 `mp_read_raw` does `mp_read_accel_axis(m, chan->scan_index - 1, &raw)` — `scan_index` for X is 1, so `1-1 = 0` ⇒ X reg base + 0 = ACCEL_X. OK. But the index math is fragile: if you ever rearrange the channel table, the off-by-one breaks. Better to use `chan->channel2` (`IIO_MOD_X/Y/Z`) and a switch.
- §70.6 `mp_probe` legacy two-arg form — see cross-cutting.
- §70.6 scale calculation: "Accel: 1/16384 g/LSB = 9.80665 / 16384 m/s² per LSB ≈ 0.000598" — yes, 9.80665/16384 = 5.985e-4. So `*val2 = 598` would be `598e-6 = 5.98e-4` — correct to 0.1 %. Just note that mainline drivers usually express this with more precision (`*val2 = 598407`).

### Knowledge prerequisites missing
- "hrtimer" trigger — readers may not know that has to be enabled via `CONFIG_IIO_HRTIMER_TRIGGER=y` and instantiated via configfs (Ch83 in TOC). One-line forward-ref.

## Ch71 — SPI IMUs

### Readability
- §71 intro is solid. §71.3 "The 'MB' (multi-byte) flag tells the chip to auto-increment the register pointer between bytes — efficient way to dump consecutive registers." → fine.

### MCU-engineer friendliness
- Add: "On STM32 you'd write `*(uint8_t*)&SPI->DR = 0xC0 | reg; while(!(SPI->SR & RXNE)); discard; ...` for each byte. Linux's `spi_message` builds the whole sequence and submits to a kernel thread that does the same — but with DMA, IRQs, and per-CS configuration handled for you."

### Missing examples / figures
- Wiring diagram for ADXL345 with IRQ pin to a GPIO. Pull-up resistor needed? Active-high or active-low IRQ?
- Show `cat /proc/interrupts` before/after — to demonstrate the IRQ rate dropping ~10× with watermark enabled (lab #4 mentions this without showing target numbers).

### Insufficient depth
- The "FIFO + watermark" pattern is the gem of the chapter. Make sure the reader sees, in code, the *full* round-trip: chip configured to assert INT on FIFO ≥ N; kernel `request_threaded_irq`; IRQ thread reads FIFO_STATUS, drains N × 6 bytes, clears the IRQ. The chapter has this but the linkage between `INT_ENABLE = 0x02` and "IRQ now fires on watermark" is implicit. Spell it out.

### Technical errors
- §71.4 driver fragment uses `devm_request_threaded_irq(dev, irq, NULL, adxl345_irq_handler, IRQF_TRIGGER_HIGH | IRQF_ONESHOT, name, indio_dev);` — that's correct (NULL primary, secondary on thread). Good.
- §71.5 `ma_probe` `spi->mode = SPI_MODE_3` — correct for ADXL345. Then `spi_setup(spi);` — but the DT also specifies `spi-cpha` and `spi-cpol`. Either trust the DT and remove the explicit mode assignment, or trust the explicit one — having both with conflicting intent is the kind of thing that catches people. (Here they agree, but flag the pattern.)
- §71.5 `devm_iio_triggered_buffer_setup(&spi->dev, idev, NULL, NULL, NULL);` — all-NULL handlers. See cross-cutting. Add a comment: "we push samples from the watermark IRQ; this call just registers the buffer infrastructure."
- §71.5 endianness: `ma_read_axis` reads `*out = (s16)(buf[0] | (buf[1] << 8));` — ADXL345 outputs *little-endian* (low byte at lower address). The `IIO_LE` in scan_type matches. Verify against datasheet — ADXL345 datasheet does say LSB-first byte order. OK.
- §71.10 pitfall "ADXL345 is mode 3 (CPOL=1, CPHA=1)" — datasheet confirms mode 3. OK.

### Other
- `INV_MPU6050_CHAN` macro was reused across chapters but the name suggests it's MPU-specific. In Ch71 it's `ACCEL_CH`/`GYRO_CH`. Fine.

## Ch72 — Distance & proximity

### Readability
- §72.1 sub-bullets read naturally.
- §72.6 "Bottom line: don't ship HC-SR04 connected to Linux GPIO" — perfect blunt advice. The whole §72.6 is one of the best "honest about Linux limitations" passages in the book.

### MCU-engineer friendliness
- The HC-SR04 discussion is genuinely useful — but the comparison to "what you'd do on STM32" (capture-compare on a timer input) is implicit. Spell it out: "On STM32 you'd configure TIM2_CH1 in input-capture mode, get an IRQ on rising-then-falling edges, read the capture register difference — ±1 µs accuracy with zero CPU. Linux's GPIO IRQ + ktime has 100× worse latency."

### Missing examples / figures
- No wiring diagram for VL53L0X. The chip has XSHUT and INT pins — wire them. Also the I²C pull-ups.
- Show `dmesg | grep vl53` after the from-scratch driver loads.

### Technical errors
- §72.4 mainline driver: "ID register 0xC0 — Always 0xEE (or 0xEEAA depending on rev)" — VL53L0X model-ID at register 0xC0 is one byte 0xEE; the "0xEEAA" might be referring to the 16-bit MODEL_ID at 0xC0:0xC1 read as a word (0xEE 0xAA). Clarify.
- §72.5 `myvl53l0x` minimal tuning blob: "{0x70, 0x04}, {0x71, 0x08}, /* set measurement-timing-budget for ~33 ms */" — the official ST API sets timing budget via much more elaborate VHV+phase calibration registers, not these two. The blob shown will probably produce *some* reading but will not give the ±3 % accuracy quoted in §72.1 — the reader's measurements will be off by 5–10 %. Be more upfront: this is a "smoke-test" tuning, not a calibrated one.
- §72.5 `mv_probe` legacy two-arg form.
- §72.6 HC-SR04 driver fragment busy-waits with `cpu_relax()` inside `gpiod_get_value` — but doesn't disable preemption. A scheduler tick during the wait will easily cost 100+ µs. Either add `local_irq_disable()` around the timing-critical loop (matching the technique used by `w1-gpio` in Ch77), or be explicit that this driver alone doesn't bring the accuracy claim — only RT-kernel does.
- §72.7 GP2Y0A on i.MX6ULL ADC — i.MX6ULL has 2 ADC blocks (ADC1, ADC2) per the reference manual, each with 10 input channels (ADC1_IN0..ADC1_IN9). Not "2 channels total". Update §72.7 phrasing.

### Other
- Lab #4 says to use `gpiomon` — but libgpiod versioning matters here (`gpiomon` was renamed in libgpiod 2.0). Note the version.

## Ch73 — Magnetometer / compass

### Readability
- §73.1 trap callout "If your 'HMC5883L' doesn't probe at 0x1E, try QMC5883L at 0x0D" — superb concrete pitfall. Keep.
- §73.7 "Phase 1: collect ~1000 samples while the user rotates the sensor" — slot in "the user rotates the sensor in 3D, ideally covering as much of the imaginary sphere around it as possible."

### MCU-engineer friendliness
- Calibration is universal across MCU and Linux. Helpful explicit note: "This calibration script runs in user-space because IIO drivers should not bake board-specific magnetic environment into the kernel. On an MCU you'd do the same fit in your application code."

### Missing examples / figures
- A wiring diagram for QMC5883L on I²C1 — same as the other I²C sensors but the chapter never shows one.
- A scatter plot (ASCII or callout to a generated image) of "raw mag data on uncalibrated chip" versus "after hard-iron correction" would be the single most impactful figure in the chapter.

### Technical errors
- §73.4 QMC5883L bring-up: "Write 0x0B = 0x01: set the 'period' register (mandatory; chip won't work without it)." — datasheet says SET/RESET period register at 0x0B should be 0x01 for typical use; this is correct.
- §73.6 `mq_probe` legacy two-arg form.
- §73.6 `mq_read_axes` uses `i2c_smbus_read_i2c_block_data(..., 6, buf)` from REG_DATA = 0x00. QMC5883L data registers are 0x00..0x05 — works. Just note that some I²C controllers refuse a block-read at register 0 (interprets as length byte in SMBus block-read semantics) — i.MX6ULL is fine.
- §73.6 scale: "±8 G range, 16-bit signed ⇒ 32768 LSB / 8 G = 4096 LSB/G. Convert to Tesla: 1 G = 100 µT, so 1 LSB = 100/4096 µT" → 24.4 nT/LSB = `*val2 = 24414` with IIO_VAL_INT_PLUS_NANO. Verify against the mainline `qmc5883.c` scale convention — it might publish scale in Gauss not Tesla.

### Insufficient depth
- §73.7 calibration math is intentionally simplified — author calls it out. Could add a 10-line "proper" ellipsoid-fit pseudocode (the eigen-decomposition step) so the reader sees what the simplified version is approximating.

## Ch74 — Hall-effect & rotary position

### Readability
- §74.2 "The magnet must be: ..." bullet list is good.
- §74.5 ends at "ADC-based. For 'is there a magnet nearby?' (lid open/closed, latch position): A1324 + ADC + a threshold is enough." — fine but feels a bit terse compared to the AS5048 walkthrough.

### MCU-engineer friendliness
- Two-frame SPI sequence is an MCU concept readers will already know; just say "if you've used the AS5048 from STM32, the same two-frame trick applies — first transaction sends the command, the chip's response appears in the *next* transaction."

### Missing examples / figures
- Show a wiring diagram. AS5048A on ECSPI3, INT pin connected to a GPIO? Datasheet doesn't have a data-ready INT pin (the chip has ABI/UVW outputs and a PWM output); clarify.
- Show what the magnitude register reads with no magnet vs with the correct magnet at 1 mm — concrete numbers tell the reader what "good" looks like.

### Technical errors
- §74.3 "Each SPI frame is 16 bits: bit 15 = parity (even parity over remaining 15 bits)" — AS5048A actually uses even parity over bits 14:0 (the 15 lower bits), and bit 15 is the parity bit itself. The text says exactly that. OK.
- §74.4 `ma_probe` SPI mode 1 — datasheet says CPOL=0, CPHA=1, which is mode 1. OK.
- §74.4 `ma_read_reg`: the second read of MAGNITUDE in probe to "get the actual answer (first frame is throwaway)" — yes, two-frame protocol. But this means probe issues 4 SPI transactions where 2 would do; it's clearer to do "issue cmd, then issue cmd again" *both* explicitly named "first is throwaway." Cosmetic.
- §74.4 scale: "14-bit = 16384 LSB per full turn = 2π rad. 1 LSB = 2π / 16384 ≈ 383.5 µrad." → `*val2 = 383495` for IIO_VAL_INT_PLUS_NANO ⇒ 383.495 µrad/LSB. 2π / 16384 = 383,495.18 nrad. OK.
- §74.6 "Mainline driver: `drivers/iio/position/iqs62x.c` covers some Iqs sensors; TLE5012 has out-of-tree drivers from Infineon." — `iqs62x` is unrelated to TLE5012. Either remove the misleading sentence or replace with the correct mainline status.
- §74.7 "`drivers/iio/position/as5048.c` is the mainline AS5048 driver" — the mainline file is `drivers/iio/position/as5011.c` and the AS5048 driver is `drivers/iio/position/as5048a.c` historically. Check current upstream.

### Other
- §74.10 last pitfall mentions "Hot-plug/start-up race" — phrase it as "AS5048 boot delay" for clarity; "hot-plug" suggests removable bus device.

## Ch75 — Current & power monitoring

### Readability
- §75.1 column "I²C clock | 100 kHz / 400 kHz / 2.94 MHz (HS) | up to 2.94 MHz | up to 2.94 MHz" — 2.94 MHz is the High-speed-mode max. i.MX6ULL I²C controllers don't do HS-mode — they max out at 400 kHz Fast-mode. Add a footnote: "i.MX6ULL drives the bus at 100/400 kHz; the 2.94 MHz figure is the chip's max with an HS-mode-capable controller."
- §75.3 "Calibration = trunc(0.04096 / (Current_LSB × R_shunt))" — formula text and worked example are excellent. Keep.

### MCU-engineer friendliness
- The calibration-register-is-the-trap insight is a classic MCU gotcha (anyone who's used INA219 from Arduino has hit it). Acknowledge: "This is the exact same trap Arduino INA219 users hit; the difference is on Linux you discover it via `cat curr1_input` reading 0 forever, instead of `Serial.println` reading 0 forever."

### Missing examples / figures
- The schematic in §75.2 is *almost* useful but the ASCII art has issues — the V+, V- arrows don't visually attach to anything. Redraw as a cleaner block diagram.

### Technical errors
- §75.4 `ina2xx_config` table — `[ina226]`'s `calibration_value = 2048`: datasheet INA226 calibration formula is `Cal = 0.00512 / (Current_LSB × R_shunt)`. Confirm the magic constant against datasheet.
- §75.5 `mi_probe` legacy two-arg form.
- §75.5 `mi_probe` references `&m->client->client_dev` — there's no `client_dev` member; it's `&m->client->dev`. Compilation error.
- §75.5 calibration math: "cal = 40960000u / (m->current_lsb_uA * (m->shunt_uohms / 1000))" — for shunt_uohms = 25000 and current_lsb_uA = 100: `40960000 / (100 * 25) = 16384`. OK. But the `shunt_uohms / 1000` integer divide loses precision for shunts not divisible by 1000 (e.g., 1500 µΩ ⇒ 1 ⇒ wrong). Use a 64-bit do_div() pattern or document the assumed precision.
- §75.5 hwmon attribute `in0_input` for shunt voltage returns mV — `uV / 1000` truncates microvolts of detail. For a ~3 mV shunt voltage, the result is "3" — that's 33 % rounding error. Either return microvolts (which `in0_input` doesn't quite mean per hwmon convention) or round properly.

### Insufficient depth
- The hwmon vs IIO sidebar (§75.6) is a key insight the rest of the book has been ducking. Keep it. Could add: "if you implemented this same chip in IIO, what would change?" — answer is the framework name and the attribute layout, but the per-register reading code is identical.

## Ch76 — Battery fuel gauge + charger

### Readability
- §76.2 "voltage isn't linear with SoC" — solid pedagogically. The "discharge curve" is well-described in prose. An ASCII chart would make it click instantly.

### MCU-engineer friendliness
- "On STM32 you might wire a voltage divider to the ADC and read battery voltage directly. That gives you the cell's open-circuit voltage *only when there's no load* — under load the voltage drops by I × R_internal, which on a Li-ion cell looks identical to 'low battery'. Fuel gauges solve this; ADC dividers don't." That's the kind of MCU-to-Linux bridge.

### Missing examples / figures
- Wiring diagram: MAX17048 (just I²C + cell). Trivial but include for consistency.
- ASCII discharge curve: 4.2 V at 100 % falling through 3.7 V at 50 % to 3.4 V at 10 %.

### Technical errors
- §76.3 SoC raw encoding: "bits 15:8 = %, bits 7:0 = fractional 256ths" — correct per MAX17048 datasheet.
- §76.5 `mm_probe` legacy two-arg form.
- §76.5 `mm_read_reg(m, REG_VERSION, &version)` returns the value via `i2c_smbus_read_word_swapped`; the version check `(version & 0xFFF0) != 0x0010` — MAX17048 datasheet says version is 0x0010 to 0x001F range. Verify the mask matches the actual silicon-id range.
- §76.5 `power_supply_register` uses `devm_power_supply_register` — correct.
- §76.6 "Charge current is set by `R_PROG`: `I_charge = 1200 / R_prog`" — TP4056 datasheet equation is `I_BAT = V_PROG / R_PROG × 1200` where V_PROG = 1.0 V typical, so `I = 1200 / R_PROG` with R in ohms gives I in mA. So R = 1.2 kΩ ⇒ 1000 mA, R = 2.4 kΩ ⇒ 500 mA. The text "R = 1.2 kΩ → 1 A; R = 2.4 kΩ → 500 mA" matches. OK. But mention units clearly: "R in kΩ, I in mA, or equivalently R in Ω with I in A."

### Insufficient depth
- The chapter only implements PRESENT/VOLTAGE_NOW/CAPACITY/STATUS (and STATUS is stubbed). Reading CRATE (register 0x16) to derive STATUS = CHARGING/DISCHARGING is straightforward and would round out the driver. The author explicitly notes this in the closing paragraph; consider just doing it inline rather than as homework.

## Ch77 — 1-Wire sensors

### Readability
- §77.6 "Bottom line: if you see DHT22 in someone's product schematic, suggest a swap to SHT3x." — great closing line.
- §77.4 "imaginary family — say, a custom sensor with family code 0xA5" — fine, but flag explicitly that 0xA5 is *not* a registered Maxim family code (real ones are listed in Maxim AN155). The reader could otherwise accidentally claim an in-use code.

### MCU-engineer friendliness
- "On STM32 you'd bit-bang the same timing in a tight loop with DWT cycle counter for sub-µs timing. Linux's `udelay` + `local_irq_disable` is the same idea — but interrupts off in Linux is more *consequential* than on STM32 (no other RTOS task runs)."

### Missing examples / figures
- Show the wiring diagram: GPIO4_IO14 ↔ 4.7 kΩ to 3.3 V ↔ DS18B20 DQ; DS18B20 VDD and GND.
- Show the actual SEARCH-ROM dance — even just one cycle — would deepen the "binary-tree enumeration" claim.

### Technical errors
- §77.3 `w1-gpio` `w1_gpio_read_bit` timing: "Pull low for ~6 µs / sample at 15 µs / finish 55 µs" — close to standard 1-Wire spec (Maxim AN126 gives "tLOW1 ≤ 15 µs, tRDV = 15 µs, tRELEASE ≈ 45 µs total slot = 60 µs"). Numbers are slightly off but within tolerance. OK as illustrative.
- §77.3 says "wraps the bit operations in `local_irq_disable()` / `local_irq_enable()` around the timing-critical region" — actually the mainline `w1-gpio.c` does *not* unconditionally disable IRQs; it relies on `udelay` accuracy plus 1-Wire's timing tolerance. The `slaves/w1_therm.c` may use specific atomic windows. Verify.
- §77.4 `w1_reset_select_slave(sl)` returns 0 on success, but the doc check `if (w1_reset_select_slave(sl)) { ... return -EIO; }` treats non-zero as failure — that means "returns 0 on success" semantic, which matches `w1.h`. OK but inverts the natural reading.

### Other
- DS18B20 temperature decode: "temp_C = temp_raw / 16.0 (signed!)" — yes, 16-bit signed with 4 fractional bits. Correct.

## Ch78 — MEMS microphones

### Readability
- §78.1 table "PDM | needs the SoC's PDM-decoder hardware. i.MX6ULL's SAI has *only I²S*, no native PDM. So PDM mics are awkward on i.MX6ULL — skip." — straight talk, good.
- §78.4 "There's no I²C control — the mic has no registers. The wires alone (BCLK, LRCLK, SD, LR-select strap) determine its behavior." — excellent framing.

### MCU-engineer friendliness
- "On STM32 with the SAI peripheral, you'd use HAL_SAI_Receive_DMA into a circular buffer. Linux's SAI driver + SDMA does exactly the same — but ALSA owns the ring buffer, and user-space `arecord` reads from it via ioctl/mmap. The DMA hardware doesn't care which layer is on top."

### Missing examples / figures
- The data-flow box in §78.5 is good; consider a parallel "where the kernel symbols live" diagram (so the reader knows `fsl_sai.c`, `dmic.c`, `simple-card.c` correspond to each layer).
- Show the SAI2 IOMUX pin assignments from the reference manual (SAI2_TX_BCLK at which pad, SAI2_TX_SYNC at which pad — these are the user's actual schematic decisions).
- Show actual `arecord` output for `arecord -l` and `cat /proc/asound/cards` so the reader knows what success looks like.

### Insufficient depth
- The chapter intentionally skips writing a codec driver for the INMP441 because *there is no chip to drive*. That's pedagogically correct — but per the cookbook-depth requirement, the chapter should still show "what writing a machine driver looks like" beyond the 30-line sketch. The §78.6 sketch *is* mostly that, but it could be a complete, compilable example with the `module_platform_driver` boilerplate, even if it duplicates `simple-audio-card`.

### Technical errors
- §78.4 DT `assigned-clock-rates = <0>, <24576000>;` — the IMX6UL_CLK_SAI2_SEL doesn't take a rate (it's a mux), so `<0>` is correct as a "don't change". The MCLK rate 24.576 MHz is correct for 48 kHz audio. OK.
- §78.4 `bitclock-master = <&cpu_dai>; frame-master = <&cpu_dai>;` — these properties were renamed in newer kernels to `bitclock-master = <&cpu>` style with phandles to the appropriate child. The DT shown is correct for current `simple-card.c`. Verify in 6.x.
- §78.4 `dmic_codec` node uses `compatible = "dmic-codec"`. Mainline `sound/soc/codecs/dmic.c` registers a platform driver for that compatible. Confirm `CONFIG_SND_SOC_DMIC=y` is required (the §78.9 pitfall already notes this).

### Other
- Lab #8 "FFT in user-space" is a great teaser but assumes Python availability — many minimal iMX6ULL rootfs don't ship Python. Note this or provide a tiny C alternative.

## Ch79 — Health sensors

### Readability
- §79 intro reads well. "Without good signal processing, the readings are garbage — and the chip can't fix bad processing." Strong.
- §79.6 Python sketch is clear.

### MCU-engineer friendliness
- "Most MAX30102 Arduino examples do their HR/SpO₂ math on-MCU. On Linux you can do the same — but for a one-off product, doing the DSP in Python or NumPy in user-space is far faster to iterate on."

### Missing examples / figures
- Show the IRQ wiring (the chip's INT pin to which GPIO).
- An ASCII waveform of "PPG signal: DC pedestal + small AC ripple" would crystallize §79.2 way better than the prose.

### Technical errors
- §79.5 `mh_probe` legacy two-arg form.
- §79.5 `devm_iio_triggered_buffer_setup(..., NULL, NULL, NULL)` — same as Ch71, all-NULL handlers; the chip's IRQ pushes samples directly. Document this.
- §79.5 18-bit packing: `((buf[0] << 16) | (buf[1] << 8) | buf[2]) & 0x3FFFF` — the mask `0x3FFFF` keeps low 18 bits. But the MAX30102 outputs already zero the top 6 bits when ADC range is 18-bit; if range is 17-bit/16-bit (configurable), the field is different. Note dependence on §79.3 step 6's `SPO2_CONFIG` value.
- §79.5 `mh_read_raw` "drain all but the latest, return latest" — this is acceptable for sysfs reads but has poor semantics: each sysfs read silently discards 30+ samples that the buffered-capture path *would* have wanted. If the buffer is enabled, both paths conflict. Caveat the reader.
- §79.6 SpO₂ formula "110 - 25·R" — the original literature uses different fits (Maxim AN6409 gives a piecewise formula). The 110-25R approximation is roughly right for R ≈ 0.4–1.0 (95–100 % SpO₂) but breaks badly outside that range. Mention the limitation.

### Other
- §79.4 "There is no IIO mainline driver for MAX30100/30102 as of this writing (early 2026)" — there is `drivers/iio/health/max30100.c` and `max30102.c` already mainline since 4.x. Update the chapter intro and §79.4.

## Ch80 — External ADCs

### Readability
- §80.1 table is well structured; "ENOB" column needs a one-line definition somewhere (probably § "Why not use the SoC's internal ADC?") for non-EE readers.
- §80.3 "ADS1115 has just 4 registers" — clear.
- §80.9 "Ratiometric measurement — the noise-cancellation trick" — keep this section; it's exactly the kind of physical insight that separates a textbook ADC writer from a competent engineer.

### MCU-engineer friendliness
- "On STM32 you'd use the internal ADC with DMA-circular mode for continuous capture. ADS1115 over I²C is much slower but vastly more accurate — the trade-off is the same one as MCU-onboard vs external ADC, just with kernel layers in the middle."

### Missing examples / figures
- Wiring: ADS1115 ADDR pin straps (4 addresses available), the AIN0..AIN3 inputs.
- Show what `cat /sys/.../in_voltage_scale_available` looks like for the mainline driver (a list of PGA scales) — readers don't always know that `_available` files exist.

### Technical errors
- §80.2 "The i.MX6ULL has 2× 12-bit SAR ADCs" — correct: ADC1 and ADC2 each are 12-bit SAR. But then "2 channels: not enough for a multi-sensor product" — wrong. Each ADC has up to 10 external input channels (ADC1_IN0..ADC1_IN9 per the reference manual at line 22435+). The constraint is the *number of ADC blocks*, not channels. Rewrite as "limited to two simultaneous conversions; each ADC has multiple input pins but they're muxed."
- §80.5 `ma_probe` legacy two-arg form.
- §80.5 `ma_read_channel` OS-bit polling logic comment: "note: OS reads 1 when conversion is DONE in single-shot; check datasheet" — the chapter author *correctly* flags this in the §80.11 pitfall, but the polling loop `while (!(status & CFG_OS_SINGLE) && retries--)` matches "1 = done" reading. Good.
- §80.5 scale: "±2.048 V over 2^15 = 62.5 µV/LSB" → `*val2 = 62500` with `IIO_VAL_INT_PLUS_NANO` ⇒ 62500 nV/LSB = 62.5 µV/LSB. Correct.
- §80.6 MCP3008 protocol is correct. The vref-supply phrase "(ratiometric: scale = vref / 1024)" — MCP3008 is 10-bit ⇒ 1024 codes ⇒ scale = vref / 1024 V/LSB. Correct.
- §80.8 AD7606 "16-bit, 8-channel simultaneous-sampling" — verify max sample rate per channel. AD7606 datasheet says 200 kSPS *per channel* with all 8 sampling simultaneously, total 1.6 MSPS aggregate. The table at §80.1 "200 kSPS/ch (all at once)" matches. OK.

### Other
- §80.9 ratiometric explanation could include an explicit example using HX711 (which is *literally* a 24-bit ratiometric ADC chip for load cells) — that's the chip readers will actually buy if they want a scale. HX711 is mentioned in passing; expand it.

## Ch81 — External DACs + clock generators

### Readability
- §81.1 table is fine. §81.3 IIO output channels primer is well-placed.
- §81.6 clk-framework section is dense — could use one more paragraph of orientation. "The kernel clock tree (Ch 13, Ch 25) is a graph of clocks where each clock has a parent. SoC clocks plug in at the top; the Si5351 adds *external* nodes consumers can use just like internal ones."

### MCU-engineer friendliness
- The DAC IIO output channel is a new concept for the IIO mental model. Bridge it: "If `read_raw` is 'kernel reading from sensor', `write_raw` is 'kernel pushing to actuator'. Same API, opposite direction." That's the one-line summary.
- For Si5351: "On STM32 you'd configure the on-chip PLL via RCC registers. An external Si5351 does the same job for external chips that need a non-standard clock; the Linux clk framework just makes the Si5351's outputs look like any other clock in the tree."

### Missing examples / figures
- Wiring diagram for MCP4725 — show VDD, GND, SDA, SCL, A0 (address-select), VOUT.
- Show the actual `cat /sys/kernel/debug/clk/clk_summary` output (a few representative lines) for an Si5351 — most readers will not have seen `clk_summary` before. Note `CONFIG_DEBUG_FS=y` and `mount -t debugfs none /sys/kernel/debug` requirements.

### Technical errors
- §81.4 `mc_probe` legacy two-arg form.
- §81.4 `mc_set` fast-write packing: `buf[0] = (value >> 8) & 0x0F; buf[1] = value & 0xFF;` — datasheet figure 6-2 (fast-write) shows byte0 = bits PD1,PD0,D11,D10,D9,D8 in low 6 bits, with top two bits being command-mode 00. For "normal mode" (no power-down), PD1=PD0=0. So `buf[0] = (value >> 8) & 0x0F` does write D11..D8 in low nibble and zeros for PD; that matches "normal mode fast write." OK. But the macro semantics is fragile — datasheet table 6-2 makes the bit layout clear; the chapter should reproduce it.
- §81.5 AD5663 SPI frame: "24-bit SPI frame: 8 command/address bits + 16 data bits" — actually datasheet says 24-bit frame with 6 bits reserved + 3 command + 3 address + 16 data + extra. Verify.
- §81.6 Si5351 — DT example uses `silabs,multisynth-source` and `silabs,clock-source` — verify against current binding (`Documentation/devicetree/bindings/clock/silabs,si5351.yaml`).
- §81.6 clk-framework reference: "the same framework that manages the SoC's internal clock tree (Ch 13, Ch 25)" — verify those chapter numbers cover the clk framework introduction (per current TOC).
- §81.6 example "f_out = f_xtal × (PLL_mult) / (output_divider)" — Si5351 actually has *two* dividers (Multisynth + R-divider) plus the PLL fractional divide. The simplified expression is OK as an introduction but flag the simplification.

### Other
- §81.7 lab #4 "Try writing to EEPROM via the mainline driver's persistence" — confirm the mainline `mcp4725.c` does expose EEPROM-write via a sysfs attribute. As of 6.x it does, via the `_powerdown_mode` and writing the persistent-flag DT property. Reader will likely struggle without the exact attribute name.
- §81.8 last pitfall "Clock consumer ordering ... `-EPROBE_DEFER`" — good. Add: "the kernel retries deferred probes after every successful probe of any other driver, so eventual success is the norm; but circular dependencies (A waits on B, B waits on A) deadlock — verify with `cat /sys/kernel/debug/devices_deferred`."


---

# Part VIIb — Cookbook (Displays/Cameras/Audio/WiFi/BT): Review

## Cross-cutting observations

- **Almost no explicit MCU contrast.** Across all 16 chapters the only direct STM32/MCU comparison is one passing nod ("like a cellular AT modem"). For a reader who has done LCDs on FSMC, cameras on DCMI, I2S on STM32 SAI, WiFi via ESP8266 AT, this is the highest-leverage analogy and it is consistently missing. Each chapter intro should include 2–4 lines: "On STM32 you would X (FSMC/DCMI/SAI/AT-WiFi); on Linux it is the same idea but with [framework] in the middle, which buys you Y but costs Z."
- **No system-level ASCII figures.** The chapters draw small per-peripheral diagrams (wire pinouts, register packets) but never the *Linux stack layering* the reader actually needs to internalize. Required figures: (a) DRM CRTC/encoder/connector/panel → mxsfb→ panel-simple wiring (Ch 82–85); (b) V4L2 sensor-subdev → CSI bridge → video-node media graph with pad-format propagation (Ch 87); (c) ASoC machine ↔ codec_dai ↔ cpu_dai (SAI) ↔ DAPM graph (Ch 89–90); (d) wpa_supplicant ↔ nl80211 ↔ cfg80211 ↔ driver / mac80211 layering (Ch 91–94); (e) HCI ↔ kernel BT ↔ bluetoothd ↔ D-Bus app (Ch 95–97). Each appears in prose but never as a picture, even though Part VI presumably set this up.
- **Knowledge prerequisites are referenced but never refreshed.** Many chapters say "as in Ch 53/55E/55G" and assume the reader carries the framework concept fresh. Cookbook chapters should re-state the one or two concepts they depend on in a 3–5 line callout ("DAPM, from Ch 53: ..."), then build on top. A reader skimming Part VII out of order will be lost.
- **`status: draft` and `estimated_pages` everywhere.** Either remove or commit to a meaning. Some page counts seem optimistic for the depth shown (Ch 84 says 16 pages but is mostly a "this doesn't really work on i.MX6ULL" disclaimer).
- **Many "from scratch" drivers omit error-path cleanup, locking, suspend/resume, and `MODULE_AUTHOR`/`MODULE_DESCRIPTION`.** They are explicitly minimal but readers will copy them. Add at least one comment per driver: "production code must add: error rollback in probe, runtime_pm hooks, locking around shared state." Some explicitly do (Ch 87), but most do not.
- **The `.remove` callback signature has changed in recent kernels (returns void in 6.11+).** Several chapters use `static int xxx_remove(...)` and others use `static void`. Inconsistent. Pick a kernel target and state it once.
- **`dev_err_probe` is used but never explained.** It appears in Ch 83/85/86/87 with no introduction. A one-line gloss ("returns the err while deferring nicely if -EPROBE_DEFER") would help.
- **Volume prices and BOM costs are scattered all over.** Useful for the practising engineer but verge on the dated. Add a once-only note: "prices Q1 2026, indicative."
- **Lab sections are good and consistent — keep them.** They turn each chapter into a real recipe, which matches the cookbook framing.
- **Choice between fbdev and DRM is treated inconsistently.** Ch 82/83/84 are DRM-first (correct, modern), Ch 85 says "DRM is modern, fbdev is more illustrative" and then writes an fbdev driver. The justification is fine but the reader is left wondering whether to write fbdev for new code. Add a one-line policy: "For new code: DRM unless the device is 1-bit + frame-buffer-style. The fbdev path is shown here for didactic reasons; mainline `ssd130x` is DRM."
- **The book consistently uses `[root@pa-mini:~]#` prompts. Good** — keep this consistency, but a reader on QEMU/another board may be confused; one footnote in Ch 82 explaining "pa-mini" suffices.
- **i.MX6ULL specificity is sometimes glossed.** Ch 82, 84, 87 are pretty clear about limits; Ch 89/90/91 should probably mention SAI vs SSI peripheral naming on i.MX6ULL (the chip has both; the audio chapters say only "SAI"), and Ch 87 should note that the i.MX6ULL CSI has *only* 8 data lines (CSI_DATA00–07), reinforcing why 10/12-bit RAW from OV5640 is moot.

## Ch82 — RGB LCD

### MCU-engineer friendliness
- Add an intro paragraph contrasting against STM32 LTDC: "On an STM32F7/H7 with LTDC you DMA a framebuffer to RGB pins; on Linux mxsfb (DRM driver) does the same DMA, but a *panel driver* describes the timing instead of you typing it into LTDC registers, and DRM owns the buffer allocation." The reader has done this on bare metal and will click immediately.

### Missing examples / figures
- The LCDIF clocking diagram is asked for in the brief — none present. Show: PLL5_VIDEO → LCDIF_PIX clock divider → LCDIF → PCLK on pad. Helps explain *why* ~70 MHz is the ceiling.
- A picture of the DRM pipeline (`drm_panel ↔ drm_connector ↔ drm_encoder ↔ drm_crtc ↔ mxsfb` + `of_graph` edges) would replace ~200 words. It is the central concept of the chapter.

### Insufficient depth
- §82.4 ("How `panel-simple` works internally") is too brief — half a page of pseudocode and stops. Either go deeper (how `drm_panel_funcs` is called by which DRM helper, the prepare/enable/disable/unprepare ordering and what the encoder does between them), or trim it and lean on §82.5's full driver.

### Technical errors
- `clock-frequency = <51200000>; hactive=1024 hfront=210 hback=46 hsync=1 vactive=600 vfront=22 vback=23 vsync=1` → h_total=1281, v_total=646, pclk required = 1281·646·60 = 49.65 MHz, not 51.2 MHz. The chapter notes the discrepancy but reports `51200000` as the binding value — DRM will either round the actual PCLK to the nearest the PLL can produce or refuse. Worth a sentence: "the kernel computes the required pclk from the timings, the `clock-frequency` value is informative." This is exactly the gotcha the brief is asking for.
- `pixelclk-active = <0>; /* latch on falling edge */` — DT property here is `pixelclk-active`, which is the *invert* of the panel's sample edge. Worth confirming against `Documentation/devicetree/bindings/display/panel/panel-timing.yaml` and re-stating which polarity = "latch on falling": the wording "active = 0 means latch on falling edge" is correct for `pixelclk-active`, but DRM/panel-simple uses `DRM_BUS_FLAG_PIXDATA_DRIVE_NEGEDGE` in `bus_flags`. Mention that the DT property and the DRM bus flag must agree (and that the kernel sometimes silently inverts).
- "ATK10261 71 MHz pclk exceeds safe LCDIF range (~70 MHz)" — the IMX6ULL RM does not give an explicit LCDIF pclk ceiling in the chapters I scanned; common community guidance is ~50–70 MHz depending on SoC speed grade. Soften to "practically capped around 50–70 MHz depending on speed grade and CCM configuration" with a reference.
- `bits-per-pixel = <24>; bus-width = <24>;` are *legacy* `display-timings` properties; the modern `panel-dpi` binding uses `bus-format = "rgb888"` (or `MEDIA_BUS_FMT_RGB888_1X24`) at the endpoint, not bus-width. The chapter shows both but doesn't flag which is current — mainline `panel-dpi.yaml` lists `bus-width` as the DT property still, but production code increasingly uses `data-mapping` and bus-format. Verify against a current binding doc and clarify.

### Knowledge prerequisites missing
- The reader needs to know what a `drm_panel` is before §82.4. A 2-line refresher ("a `drm_panel` is a kernel object representing an external panel; the encoder calls into it for prepare/enable/get_modes — Ch 53 introduced this") helps.
- §82.5 approach 3 uses `drm_panel_of_backlight` without explaining what it does (it walks the `backlight` phandle and returns the registered `backlight_device`). Two lines.

### Other
- "Backlight forgotten" pitfall is great. Move it into a callout at the top of §82.6 since it is the #1 first-bring-up symptom.
- Lab step 4 ("deliberately wrong porch") is excellent — keep.
- Approach 3 driver: `mypanel_remove` is shown without freeing the backlight; `drm_panel_of_backlight` uses devm under the hood, so this is fine, but say so.

## Ch83 — SPI LCD

### Readability
- "Drawing a pixel rectangle" pseudocode (§83.2) mixes prose and code in a confusing way. Lift it into a clear C-like block: command then data with explicit DC-toggle markers.
- "What we'd add for production: rotation handling (MADCTL variations)..." — the abrupt segue from §83.4 to §83.5 is choppy; tie them with one sentence: "In production you would not write the C above — you would use the firmware-blob path described next."

### MCU-engineer friendliness
- The reader has driven an ST7789 from STM32 with HAL_SPI + a manual init array. State it: "On STM32 you wrote a 300-line `st7789_init()` and a `draw_pixel()` that pushed bytes to SPI. On Linux that init array goes into the kernel's `mipi_dbi` helper (or a firmware blob), and `draw_pixel()` becomes `cat foo > /dev/fb0` because the DRM helper does dirty-rect tracking for you."

### Missing examples / figures
- A picture of MOSI/SCLK/DC/CS with the byte stream for `0x2A, 0x00, 0x00, 0x00, 0xEF` (CASET 0..239) with DC low/high annotated would cement the protocol better than the table.

### Insufficient depth
- §83.3 lists the `mipi_dbi` helper functions but does not show what `mipi_dbi_fb_dirty` actually does (the dirty-rect → CASET/RASET/RAMWR walk). Since this is the "what does the framework do for me" payoff, half a page of the helper's pseudocode would be excellent — it is the canonical example of how a Linux framework saves you work.

### Technical errors
- "Sitronix ST7789 max SPI clock ~62 MHz" — the ST7789 datasheet caps writes around 62.5 MHz (16 ns SCK cycle) but most modules in the wild fail above ~40 MHz. Caveat: "datasheet 62 MHz, practical 20–40 MHz, varies per module and PCB."
- `DRM_SIMPLE_MODE(240, 240, 28, 28)` macro signature is `DRM_SIMPLE_MODE(hdisplay, vdisplay, width_mm, height_mm)` — correct, just note this for the reader.
- `mipi_dbi_dev_init` is shown but its current signature requires `rotation` argument (`mipi_dbi_dev_init(dbidev, funcs, mode, rotation)`) on recent kernels, with no `bpp` parameter. The example passes `0` as the last arg which would be `rotation=0`; OK but worth a comment "rotation; we ignore the DT property here."
- "DRM headers version mismatch... `mipi_dbi_dev_init` signature changed across 5.x/6.x" — true and important. State the *target* kernel for the example (likely 6.6+ given `drm_fbdev_generic_setup`, which has itself been replaced by `drm_fbdev_dma_setup` in 6.11+). Pick one and pin it.

### Other
- "Mainline driver `drm/tiny/st7789v` (via panel-mipi-dbi)" — there is no `st7789v.c` standalone driver in mainline; ST7789-based panels are handled via `panel-mipi-dbi-spi` + a firmware blob (e.g., for Pimoroni HyperPixel). Correct the table footnote.
- INVON pitfall is excellent — keep.
- Lab 7 ("Switch to panel-mipi-dbi with a firmware init blob") needs a pointer to the `mipi-dbi-cmd` source (`Documentation/gpu/drivers/drm-panel.rst` and the kernel's `tools/mipi-dbi-cmd/` if present, or the linux-firmware repo's example).

## Ch84 — QSPI LCD

### Readability
- The chapter's honesty about "i.MX6ULL is not a great QSPI display host" is refreshing but the chapter then doesn't quite know whether it is a real cookbook recipe or a survey. Reframe the intro: "This chapter is a *survey* (concepts + when to consider QSPI) rather than a bring-up recipe — i.MX6ULL is not a good host. Read it to recognize when you have outgrown the i.MX6ULL."

### MCU-engineer friendliness
- The reader has used QSPI on STM32 for NOR flash (XIP). The analogy is right there: "STM32 QSPI is also flash-centric (Indirect-Write mode can stream display data, but the controller's CCR fields are awkward for displays — same problem as i.MX6ULL)."

### Missing examples / figures
- An ASCII showing how `SPI_MEM_OP_CMD(1lane) + SPI_MEM_OP_ADDR(1lane) + SPI_MEM_OP_DATA_OUT(4lane)` maps to the four IO lines vs single-lane writes would clarify the §84.4 description.

### Insufficient depth
- The chapter sidesteps a from-scratch driver because i.MX6ULL doesn't support it. Fair, but at least show the *delta* from Ch 83: which one function in Ch 83's `myst7789` would change (the SPI sync call becomes a `spi_mem_exec_op` with `.buswidth = 4` on the data phase) and that's it. Three or four lines is enough.

### Technical errors
- §84.2 lane-mapping diagram: `IO3 ─ b7 b3`, `IO2 ─ b6 b2`, etc. — the bit-to-lane mapping isn't part of QSPI itself, it depends on the controller. Display QSPI controllers often pack as: each *nibble* per clock = (IO3 IO2 IO1 IO0) = (b7 b6 b5 b4) first clock, (b3 b2 b1 b0) next. The diagram you drew implies `IO3 = b7 then b3` across two clocks, which is the *opposite* nibble order. Verify against ST77916 datasheet and fix; this is exactly the "wrong lane mapping" pitfall §84.7 warns about, so getting it right here matters.
- "i.MX8M Mini (with FlexSPI)" — correct, but worth noting that FlexSPI on i.MX8M Mini still has rough mainline display support; the SoC where this really works is i.MX RT1170 (NXP MCU world) or RP2040 (PIO) — clarify the better-target advice.

### Other
- The chapter could end at "for i.MX6ULL, just don't" rather than spend half the page on i.MX8M speculation. Two paragraphs total of "if you must, here's the spi_mem approach on a capable SoC" is enough.

## Ch85 — OLED & e-paper

### Readability
- "OLED is a page-addressed bitmap; e-paper is a two-buffer LUT-driven waveform machine" — excellent contrast, keep.
- "[...the chip's logic is clocked by MCLK...]" reuse from later chapter — OK; consistency is good.

### MCU-engineer friendliness
- The reader has bit-banged SSD1306 from STM32 via I²C with `_init[]` arrays just like this. Say so explicitly: "Compared to your STM32 driver, the *protocol code is identical* — the same 0x8D 0x14 charge-pump command. The Linux difference is `fb_deferred_io` doing the batched flush so user-space writes don't saturate I²C."

### Missing examples / figures
- A pixel-layout diagram (8 pages × 128 cols, bit0=top, bit7=bottom, byte 0 = column 0 rows 0–7) drawn properly as ASCII would prevent the "scrambled image" pitfall.
- A timeline figure: write → vmem → fb_deferred_io callback fires → 1 KB I²C burst → screen. Shows where the 33 ms batching window sits.

### Insufficient depth
- §85.6 (SSD1680 e-paper) describes the model but does not show *any* code — even a stub. A 30-line `epaper_update()` showing CASET-like commands + waveform LUT trigger + BUSY wait would be in keeping with the chapter's "show the structure" approach. As is, e-paper feels like an afterthought.

### Technical errors
- `fb_deferred_io.delay = HZ / 30` — `HZ` on most i.MX kernels is 100, so this is 3 jiffies ≈ 30 ms. For HZ=250 this becomes 8 ms. Use the more portable `msecs_to_jiffies(33)` and note it.
- `info->screen_buffer = m->vmem;` — `screen_buffer` is used for vmalloc'd buffers; for deferred-io on a sysram fb you typically also set `info->fix.smem_start = (unsigned long) m->vmem` and a `screen_size`. Verify against `Documentation/fb/deferred_io.rst`.
- "SSD1680 RAM model: dual buffer + LUT" — the SSD1680 uses two RAM buffers ("BW RAM" and "Red RAM" for tricolor, or "previous" + "current" for monochrome differential refresh). The text conflates the BW/Red dual-buffer with the differential-update dual-buffer. Clarify which buffer pair you mean.
- `i2c_master_send(m->client, buf, len+1)` with `buf` from kmalloc — fine, but `i2c_master_send` requires GFP_ATOMIC vs GFP_KERNEL depending on context; for an fbdev write path you may be in atomic context if called from a tasklet. The deferred-io callback runs in workqueue context (process), so GFP_KERNEL is fine, but mention it.

### Knowledge prerequisites missing
- The reader has not used `fb_deferred_io` before. Introduce the concept properly (one paragraph): the kernel mmaps your vmem to user-space write-protected; the page-fault handler queues dirty pages; a workqueue calls your callback after `delay` jiffies. Without this the mechanism feels magic.

### Other
- The SH1106 "off-by-2" pitfall is gold — many real engineers have hit this. Keep.
- Lab 3 ("comment out charge-pump command, observe black screen") is excellent pedagogy. Keep.

## Ch86 — Touch input ICs

### Readability
- "A display without touch is a monitor; with touch it's an interface" — keep, it's good.
- §86.4 "Each measurement is a 3-byte SPI transaction" → the control-byte bit breakdown is hard to read inline; render as a table.

### MCU-engineer friendliness
- The reader has done XPT2046 on STM32 with `HAL_SPI_TransmitReceive` and a software calibration table. Say: "The Linux structure is exactly your STM32 version split in two — the SPI read+median is the same, but instead of mapping ADC→pixel in your loop, you report the raw ADC to `input_dev` and `tslib`/`libinput` does the calibration."

### Missing examples / figures
- A wiring diagram: 4-wire resistive panel (X+, X-, Y+, Y-) → XPT2046 → SPI. Many readers haven't seen a resistive overlay before.
- The 3x2 affine transform `pixel_x = a·adc_x + b·adc_y + c` — show an actual measured set of (adc, pixel) tuples and the resulting matrix, even if approximated. Reader will want to know "what does ts_calibrate's `/etc/pointercal` file actually look like".

### Insufficient depth
- "PENIRQ during sampling" pitfall is mentioned but the from-scratch driver does *not* mask PENIRQ during sampling — it polls the GPIO. That's the wrong pattern for production and the reader copying this will get spurious IRQs. At least show how the mainline `ads7846` masks PENIRQ around the SPI transaction (`disable_irq_nosync` / `enable_irq` pattern).

### Technical errors
- `xp_read_filtered` uses `msleep(10)` in an IRQ thread loop — that's 100 Hz sampling. Fine, but mention that real touch needs ~125–200 Hz to feel smooth and 1 kHz for stylus work. Mainline `ads7846` uses an hrtimer for higher rates.
- `IRQF_TRIGGER_FALLING | IRQF_ONESHOT` then inside the thread loop polling `gpiod_get_value(x->pen_gpio) == 0` until PENUP — that's polling the GPIO from a sleeping thread. Works but is awkward; the more idiomatic pattern is one IRQ → one report → re-enable IRQ → wait for next falling edge. Note this.
- `input_set_abs_params(..., ABS_X, 0, MAX_ADC, 0, 0)` — values 4 and 5 are `fuzz` and `flat`. The chapter passes 0 for both; common practice is `fuzz=8` to swallow ADC noise. Mention this.
- MPR121 datasheet — NXP/Freescale yes, but make it clear MPR121 originated at Freescale (now NXP) and is *not* TI.

### Other
- "Resistive touch needs calibration, always" — perfect, very practical.
- Lab 7 ("Compare to GT911") implies Ch 55G covers GT911; double-check that reference exists.

## Ch87 — CSI cameras

### Readability
- "The driver model is the most elaborate in the kernel" — bold claim; soften or qualify ("among the most" or "more involved than most platform drivers").
- §87.4 has long mode-table snippets — break them with prose; the reader's eyes glaze.

### MCU-engineer friendliness
- The reader has used DCMI on STM32 with a sensor's init table. *That is exactly the OV5640 init.* Say so: "The init array in §87.4 is identical to what you'd write for STM32 DCMI — same registers, same OmniVision reference code. The Linux difference is *who calls it*: the `v4l2_subdev`'s `s_stream(1)` op, invoked from user-space via VIDIOC_STREAMON. Everything else (frame DMA, format negotiation) is the same hardware, just wrapped in V4L2."

### Missing examples / figures
- The brief explicitly asks for a CSI parallel-data → IPU → memory pipeline figure. None present. Show: sensor → CSI pads → CSI capture → DMA → DRAM ring buffer → V4L2 queue → user-space mmap. This is the *single most important figure* in Part VIIb cameras and it is missing.
- The media-graph ASCII in §87.3 (the boxes for ov5640, imx-csi, /dev/video0) is decent but should also show *pad numbers* (pad 0 source on sensor, pad 0 sink + pad 1 source on csi) — those are what `media-ctl --set-fmt` uses.

### Technical errors
- "i.MX6ULL CSI bandwidth: the parallel CSI captures 8-bit data at the sensor's pixel clock (typically up to ~96 MHz)". The i.MX6ULL CSI in the RM is 8-bit-only (CSI_DATA00..CSI_DATA07 pins; no CSI_DATA08+), and the max input clock is ~96 MHz per the datasheet electricals. OV5640 supports 10-bit output but on i.MX6ULL you must use 8-bit mode. The table says "8/10-bit parallel" for OV5640 — true for the chip but misleading on i.MX6ULL specifically. Add a footnote.
- `drivers/staging/media/imx/imx7-media-csi.c` — the i.MX7 driver in staging *also* covers i.MX6ULL (they share the same CSI IP). State this; reader will look for an `imx6ull-` named file and not find one.
- `bus-width = <8>;` in the endpoint — correct property name is fine, but newer bindings prefer the named-form `bus-type = <5>` (parallel) + `bus-width`. Check current binding.
- "the i.MX6ULL has *no* MIPI-CSI" — correct.
- `MEDIA_ENT_F_CAM_SENSOR` — correct function ID, good.
- `v4l2_async_register_subdev_sensor` exists; on older kernels it was `v4l2_async_register_subdev`. State the kernel target.

### Insufficient depth
- §87.6 ("The CSI bridge side") says "you don't write this." Fair, but the reader is curious what the bridge driver *does* — show three or four lines of pseudocode: configure CSI capture format, set up DMA descriptors, on EOF interrupt hand the buffer to vb2. This demystifies "the bridge" without writing one.

### Knowledge prerequisites missing
- `media_entity_pads_init` and the entity/pad/link triple deserve a paragraph before they appear. Reader saw it briefly in Ch 54B; refresh.
- The "v4l2-async" mechanism — sensor probes independently of the bridge, then they bind via fwnode-graph — should be explained explicitly. "Async" is non-obvious if you're used to "probe wires you up immediately."

### Other
- §87.7 ("GStreamer + processing") gives three example pipelines. Add `fbdevsink` is actually deprecated; modern is `kmssink` or `v4l2sink`. Verify.
- Lab 1 ("scope CSI_MCLK") is great — physical-world debugging is exactly what the MCU reader values.

## Ch88 — USB UVC

### Readability
- Very tight chapter — well-paced, good. Keep.

### MCU-engineer friendliness
- The reader has likely never written a UVC host driver (it's a kernel class driver, not MCU territory). Connect via "you've probably wired a UVC camera to a Raspberry Pi or Linux desktop and had it just work — same `/dev/video0`, same `v4l2-ctl`. The lesson is *why* it works (class driver) and what the bandwidth budget actually allows on USB 2.0."

### Missing examples / figures
- A bandwidth-budget diagram: USB 2.0 480 Mbps → -20% protocol overhead → -20% isochronous cap → ~320 Mbps available. Same info as the table but graphical aids retention.

### Technical errors
- "USB-2.0 high-speed = 480 Mbps theoretical, ~320 Mbps usable for isochronous (after protocol overhead + the spec's 80% isochronous cap)." The spec's isochronous cap is 80% of *each microframe* (so ~384 Mbps); the further drop to ~320 Mbps accounts for handshake/SOF/etc. overhead. Numbers are roughly right, but the wording conflates the two reductions. Tighten.
- "The i.MX6ULL has 2 USB controllers" — correct; both are USB OTG 2.0. Add: each is on its own root hub, so each has the full 480 Mbps.
- "PREEMPT_RT (Ch 52A) helps for deterministic capture" — RT does not change USB isochronous timing meaningfully (isoc is hardware-scheduled); it helps user-space schedule the dequeue. Phrase more carefully.

### Other
- §88.7 "USB gadget side" is useful — short and links cleanly to Ch 55.
- "MJPEG isn't a video codec" pitfall is excellent.

## Ch89 — Audio codecs

### Readability
- Long chapter; consider splitting "How `wm8960` works" and "Writing from scratch" with a transition sentence. Reader needs a breather.

### MCU-engineer friendliness
- The reader has driven SAI on STM32 + a WM8978 via I²C. Say: "On STM32 you wrote `wm8978_init()` (register array) + `SAI_Transmit_DMA()`; that's exactly the WM8960 driver here (regmap + the DMA is the SAI's `cpu_dai`). What's new on Linux: **DAPM** — there's no STM32 equivalent. DAPM is the runtime power graph that turns off the DAC/amp when no stream is active. On bare metal you either left everything on (clicks + power) or wrote it yourself. DAPM does it for you and is the bulk of any codec driver."

### Missing examples / figures
- The brief asks for "ASoC machine-driver linking codec_dai to cpu_dai". The chapter has a block diagram of the WM8960 internals but not the *ASoC layering*. Show: simple-audio-card / machine driver → codec_dai (wm8960) + cpu_dai (sai) → DAI link → PCM → user-space (ALSA aplay). This is the highest-leverage figure.
- The DAPM widget graph for `mycodec` (DAC → HP Amp → HPOUT, plus the Playback stream endpoint) should be drawn — three boxes and two arrows would make `mycodec_routes` self-explanatory.

### Insufficient depth
- §89.3 (DAPM) is good but stops short of showing the *traversal*. Add: "When the stream activates, DAPM walks back from the DAI's 'Playback' stream endpoint, finds all widgets that connect via active routes, and powers each. When deactivated, it walks the graph in reverse order and powers down — pop-aware ordering matters." That sentence is the key insight.

### Technical errors
- `.cache_type = REGCACHE_RBTREE` — fine; modern code may prefer `REGCACHE_MAPLE`. Note the choice but RBTREE is still valid.
- `SND_SOC_DAIFMT_CBC_CFC` — "Codec Bclk Consumer, Codec Fsync Consumer" is the modern name (replaces the older `CBS_CFS` slave-as-consumer wording). Good that you used the new constants; mention the naming change briefly because readers will find both in tutorials.
- `wm8960_set_dai_pll` is shown but never explained — when does ASoC call it? Answer: from the machine driver via `snd_soc_dai_set_pll()`. A 1-liner suffices.
- "WM8960 = 0x1A, SGTL5000 = 0x0A, ES8388 = 0x10/0x11" — WM8960's I²C address is actually 0x1A (per datasheet ADDR-pin low; 0x1B with ADDR high). Verify the others, especially SGTL5000 which is 0x0A. Quick sanity check warranted.
- `i.MX6ULL` has both SAI and SSI (Synchronous Serial Interface) peripherals; the chapter speaks only of SAI. Most i.MX6ULL boards use SAI2 for audio. Add a footnote: "i.MX6ULL also has SSI but new designs prefer SAI; mainline `fsl-sai.c` is the driver."

### Knowledge prerequisites missing
- `DECLARE_TLV_DB_SCALE` macro is used without explanation — what is TLV? (Threshold Level Volume — describes a dB scale so userspace can show "-73.00 dB" instead of "value=0".) One line.
- `snd_soc_component_update_bits` shorthand for regmap RMW — say so.

### Other
- Lab 3 ("DAPM trace from debugfs") is great — exactly the kind of "look inside" exercise the reader wants.
- The "Pop/click on play/stop" pitfall and §89.5's reference to `mute_stream` are linked well.

## Ch90 — Class-D amps

### Readability
- Strong chapter — "the simplest possible ASoC component" framing works. Keep.
- "The MAX98357A is the minimalist's dream" — keep this tone, it's engaging.

### MCU-engineer friendliness
- Reader has driven a MAX98357 from STM32 with literally three pin connections and no software. Say: "On STM32 you don't write a 'driver' for the MAX98357A — you just enable I²S. On Linux you *still* don't write a driver in the usual sense; you write a 100-line ASoC component that declares 'I'm a sink for I²S'. The reason: the ALSA framework requires a `snd_soc_dai_driver` on both ends of the DAI link, even if one end is just a dumb pin."

### Missing examples / figures
- A wiring diagram for the SD_MODE resistor table (4 states encoded by one analog resistor) is genuinely interesting — show a small table with the actual resistor values from the datasheet.
- Block diagram of TAS5805M (I²S → DSP → PWM → H-bridge → speaker) would help the "what is the DSP doing" question.

### Insufficient depth
- TAS5805M section (§90.5) is too thin given its importance. The book commits to "driver internals + from-scratch implementation" (per the user memory), but here it explicitly skips the from-scratch driver because "it's WM8960-shaped plus paging + firmware blob." Either show the regmap config for the paged register access (`reg_bits = 8, val_bits = 8, max_register, but with custom read/write via book-page select`), or show a minimal `tas5805m_load_blob()`. As written, the reader cannot actually build it.

### Technical errors
- "**SND_SOC_DAPM_OUT_DRV_E**" — the `_E` suffix means "with event callback" — say so, since the reader needs to understand why this variant vs `OUT_DRV`.
- `SND_SOC_DAPM_PRE_PMU | SND_SOC_DAPM_POST_PMD` — these mean "before powering up, after powering down" — write that out, because the reader will copy the line and not know which point in the cycle their callback fires.
- "TI MAX98357A" — MAX98357 is a Maxim part (now Analog Devices), not TI. Correct in §90.1 footer ("TI/Maxim"), wrong in the chapter's lead "What" sentence. Fix.
- "PCM5102A" — the PCM5102/5102A is TI (originally Burr-Brown). Correct.
- "TAS5805M needs 32–96 kHz" — datasheet allows 32–96 kHz; many products run it at 48 kHz only. Fine as written.

### Knowledge prerequisites missing
- `DECLARE_TLV_DB_SCALE` reappears here (it does not — was Ch 89). Not an issue.
- "platform_device (not I²C/SPI) because there's no control bus" is a good pedagogical point and a *new* concept for the reader (they've only seen I²C/SPI codecs). Spell it out: a platform_device is a "device described purely by DT, no enumeration bus."

### Other
- Lab 3 ("scope SD_MODE GPIO during play/stop") is exactly the right MCU-style verification. Keep.
- Pitfall "Class-D EMI" — correct and important; many products fail EMC pre-compliance here.

## Ch91 — SDIO WiFi

### Readability
- "This chapter is mostly about the bring-up sequence and debugging" — honest framing, good.
- "Bring-up trace" §91.6 (the dmesg progression with explicit "if you don't see line 1, …") is exactly the right "debugging by stage" approach. Keep and replicate elsewhere.

### MCU-engineer friendliness
- The reader probably has *not* done SDIO WiFi on bare metal (it's heavy). The right framing is the *opposite*: "On an MCU you typically use ESP-AT (Ch 93). SDIO WiFi is the 'real Linux' way, but in exchange for being mainstream, you accept that bring-up means describing 5 things in DT exactly right."

### Missing examples / figures
- The brief asks for "wpa_supplicant ↔ nl80211 ↔ cfg80211 ↔ driver layering." §91.3's diagram has the boxes but should also show *netlink sockets* between userspace and kernel (NL80211 = a netlink family). Adding the "netlink socket" arrow makes the user/kernel boundary explicit.
- An ASCII timing diagram of the SDIO power sequence: WL_REG_ON low → wait → high → LPO clock running → SDIO CMD0 → enumeration. Would clarify the §91.4 prose.

### Technical errors
- `compatible = "brcm,bcm4329-fmac"` — the canonical for AP6212/BCM43438 is `brcm,bcm4329-fmac` *or* `cypress,cyw43438-fmac` (after Cypress acquired Broadcom's IoT business; then Infineon). Some mainlines prefer the bcm4329 fallback as a generic. Note both compatibles.
- "Out-of-tree (`rtl8189es`/`rtl8189fs`)" — for the RTL8189FTV the relevant out-of-tree is `8189fs` not `8189es` (those are different chip variants). Verify with a current repo.
- `cap-power-off-card` — used in the example. This flag's semantics changed; it's also worth pairing with `non-removable`. Worth a sentence.
- "regdb missing... CRDA" — CRDA is largely deprecated in favor of in-kernel `CFG80211_DEFAULT_PS` + the kernel reading `regulatory.db` directly. Update.

### Insufficient depth
- §91.7 "How a packet flows" is the right level. Keep — this is the "framework internals" the user memory demands, done correctly: it explains the structure without re-implementing the entire driver.

### Other
- "BT half of a combo not coming up" pitfall is great — direct link to Ch 94.
- Lab 6 (swap NVRAM, observe degraded range) is brilliant pedagogy — keep.

## Ch92 — USB WiFi

### Readability
- "The chip you buy determines whether WiFi is a 5-minute job or a 5-day ordeal" — keep, perfect.
- "Soft-MAC (rt2x00) vs full-MAC (rtl8188eus)" — implicit in the text but never stated. Add a sentence: this is *why* the rt2800usb experience is so different from the rtl8188eus experience: mac80211 handles the MAC for soft-MAC chips, so the chip driver is a thin shim.

### MCU-engineer friendliness
- Reader has plugged USB WiFi into a Pi and had it work / not work; they want the buying guide. The chapter is good as-is on this dimension.

### Missing examples / figures
- A soft-MAC vs full-MAC layered diagram (mac80211 + cfg80211 boxes for soft-MAC; just cfg80211 for full-MAC) would make the in-tree/out-of-tree story click.

### Technical errors
- "RTL8188EUS... partial (`r8188eu` since 5.18, in staging)" — the staging driver `drivers/staging/r8188eu/` was added in 5.17 and graduated/removed from staging in 6.7 (with another iteration as `rtw88` family for newer parts). Recheck against the current mainline tree; the RTL8188EU support story has moved.
- "RT5370... in-tree since forever" — yes, `rt2800usb` is mainline for a decade+.
- "Counterfeit chips" pitfall — true. Add a note about `lsusb -v` showing the iManufacturer string (which is often *wrong* on clones — can't trust either).

### Knowledge prerequisites missing
- `wireless-regdb` and "country code" — quick gloss for the reader who hasn't met regulatory domains.

### Other
- AP-mode + hostapd section is solid. Keep.

## Ch93 — Hosted WiFi via ESP32

### Readability
- "Two fundamentally different offload models" — clean framing. Keep.
- "It's a wireless serial port" (later, for AT) — keep this phrase.

### MCU-engineer friendliness
- This is *the* chapter where the MCU-engineer reader is most at home — they've done ESP-AT from STM32. Lean into it: "If you've done ESP8266 AT from STM32, AT-mode is identical. esp-hosted is what you'd build if you wanted Linux to see a real `wlan0` — same ESP, different firmware on it."

### Missing examples / figures
- esp-hosted SPI transport timing: handshake GPIO assertion → host SCK → simultaneous TX/RX data → handshake deassert. Helps explain why both `handshake` and `data-ready` GPIOs are needed.

### Insufficient depth
- §93.4 "How the esp-hosted driver works" is at the right level — keep.
- §93.5 "AT-command mode" — show one *complete* working code sample (open, configure termios, send AT, parse response, send data, read +IPD). The current snippet `expect_ok(fd)` is hand-waved. A 60-line working C example would be the highest-value addition.

### Technical errors
- "The ESP32... it has its own CPU" — ESP32 has two cores (Xtensa LX6); ESP32-S2/C3 have one; ESP8266 has one (Tensilica L106). Be precise or just say "an embedded CPU."
- "esp-hosted... out-of-tree" — true (github.com/espressif/esp-hosted); state the Linux driver licensing (Apache-2.0).
- "FCC/CE/IC modular certification" — yes, this is a real product advantage. Verify against current ESP32-WROOM-32E module spec (which does carry FCC/IC/CE certifications). Good as written.

### Knowledge prerequisites missing
- `netdev_ops`, `ndo_start_xmit`, `skb` — refresh briefly. Reader has had network drivers in Part VI but a 2-line callout helps.

### Other
- Decision table §93.6 is excellent.
- Lab 4 (Bluetooth on the same ESP) — note that not all esp-hosted firmware builds include BT; explicit configure step.

## Ch94 — WiFi+BT combo

### Readability
- Strong chapter overall. "WiFi works, BT forgotten" pitfall captures a *very* real failure mode.

### MCU-engineer friendliness
- Reader has used AP6212-style modules on STM32 (rare, usually as a co-processor module). Connect: "On Linux the combo module's two halves talk to *different kernel subsystems* on different buses. There's no single 'WiFi+BT driver' — it's two drivers that happen to share silicon. This is unusual coming from a one-firmware-blob MCU world."

### Missing examples / figures
- The block diagram in §94.2 is solid. Keep.
- A sequence diagram of "boot → uSDHC2 enum → wlan0 up → UART3 serdev probe → hci_bcm fw patch load → hci0 up" with timing would clarify the order.

### Technical errors
- "RTL8723BS driver... `rtl8723bs` (in-tree, staging-graduated)" — `r8723bs` is currently in `drivers/staging/rtl8723bs/` in some kernels and graduated/moved in others; pin the kernel version.
- "uart-has-rtscts" — correct DT property for the uart3 node.
- `compatible = "brcm,bcm43438-bt"` — correct. The `hci_bcm` driver matches this; check Documentation/devicetree/bindings/net/brcm,bcm4329-bt.yaml or similar for the canonical spec.
- "BT_REG_ON vs WL_REG_ON" — for the AP6212, they're typically *separate* signals (good, as stated); but for some pin-constrained boards they're tied. Mention both possibilities.

### Insufficient depth
- §94.5 "Coexistence" describes PTA but does not say *how the user observes* whether coex is working. A practical "scope" or "iperf3 with/without A2DP" measurement procedure (which Lab 5 does propose) should be tied directly to the §94.5 prose.

### Other
- "Default/duplicate BD address" pitfall is gold — many products ship with `00:00:00:00:00:00` from the factory. Keep.

## Ch95 — HCI Bluetooth

### Readability
- Long chapter, well-structured. The "controller + host + app" split (§95.3) is the key insight; surface it earlier and reuse the phrase.
- "the controller runs the BT link layer; you build the GATT application" — keep this thesis line, repeat it.

### MCU-engineer friendliness
- Reader has done HM-10 AT-BLE from STM32. The pivot here is: "On STM32 you used the HM-10 (Ch 96). On Linux you can also use HM-10 — but Linux gives you a *real* GATT server via BlueZ. The cost: 250 lines of D-Bus glue, but you get standard GATT and any BLE app can talk to it."

### Missing examples / figures
- The brief asks for "HCI ↔ BlueZ ↔ driver layering." §95.3 has the diagram. Good. Add to it: where in this stack does `btmon` snoop? (Between kernel BT and the controller — show an arrow pointing at the HCI level.)
- A GATT service tree (service UUID → characteristic UUIDs → descriptors) drawn as ASCII would help the §95.6 model.

### Insufficient depth
- §95.6's Python example is incomplete — it admits "the full example needs the service-object + advertisement-object registration boilerplate ~250 lines total" and points at BlueZ's `test/example-gatt-server`. For a "from scratch" cookbook chapter, this is a cop-out. Either include the full ~250 lines in an appendix, or rewrite to show the *complete* minimal example. As is, the reader cannot build the lab.
- The HCI protocol (§95.2) is described at the surface level. Since you're not asking the reader to send raw HCI, this is fine — but a `btmon` decoded trace of one connection (HCI Reset, Read BD_ADDR, LE Set Advertising Data, LE Set Advertising Enable, LE Connection Complete) would make the protocol tangible.

### Technical errors
- "**HCI**: the standardized boundary between the host (Linux + BlueZ) and the controller (the BT chip)." Strictly, HCI is BT Core Spec Vol 4 Part E; H4/H5/USB are transport bindings. The text conflates HCI (the protocol) with HCI-UART (a transport). Disambiguate.
- nRF52 with Zephyr `hci_uart` sample — true and well-documented. Good.
- "DEFAULT_BD_ADDR... `43:43:A1:00:00:00`" — that's a plausible example, but the actual default for many AP6212 modules is `43:34:B1:...`. Don't fabricate addresses; say "often a vendor-prefix MAC with zeros for the unit field."
- "MTU too small. Default BLE ATT MTU is 23 bytes (20 usable)" — correct; LE legacy ATT is 23, with MTU exchange negotiating up to 247 (LE Data Length Extension) or 517 (max ATT MTU). State the cap.

### Knowledge prerequisites missing
- D-Bus as a concept — reader's first encounter? If so, two sentences: "D-Bus is the desktop-Linux RPC bus; BlueZ exposes its API via D-Bus so any language with bindings (Python, C, Rust) can drive it." Without this, the Python example is impenetrable.
- "GATT" / "GAP" / "SMP" / "L2CAP" acronyms — define on first use.

### Other
- "MTU too small" pitfall is real — keep.
- The provisioning use-case (Lab 7) is a fantastic real-world application — keep.

## Ch96 — AT-command BLE

### Readability
- "BLE-to-serial cable" phrase is perfect. Use it more.
- Very crisp chapter. Keep.

### MCU-engineer friendliness
- This is the chapter that *most* matches the reader's existing experience. They've literally done this from STM32. The "compare ~10 lines here vs ~250-line GATT server of Ch 95" is the lesson. Reinforce: "Ch 95 buys you the full BLE ecosystem; Ch 96 buys you simplicity. Pick the right tool."

### Missing examples / figures
- Show a side-by-side: HM-10 module → UART → STM32 (familiar) vs HM-10 module → UART → i.MX6ULL (now). Same wiring, same AT commands; reinforce that the embedded engineer's knowledge transfers directly.

### Technical errors
- "HM-10 (CC2540/CC2541-based)" — CC2540 is BT 4.0 classic+BLE dual; CC2541 is BLE-only. HM-10 uses CC2540 typically. Verify.
- "AT+NAME=MyDevice" vs "AT+NAMEMyDevice" — true variation across clones. Keep the warning.
- "BLE point-to-point... reaches ~30 m" — depends heavily on antenna; HM-10 with PCB antenna is more like 10–20 m line-of-sight. Don't overstate.

### Insufficient depth
- "Single connection" pitfall is mentioned briefly but not deeply — the AT modules can only act as one role (peripheral OR central) at a time on most firmwares. Worth one more sentence.

### Other
- Lab 5 (wire to BME280, command parser, LED control) — the perfect end-to-end example.

## Ch97 — BLE Mesh

### Readability
- Mesh is genuinely hard; the chapter does a reasonable job. The "publish/subscribe over flooded BLE adverts, addressed by models" thesis line is good.

### MCU-engineer friendliness
- Reader has not done mesh. The framing should be: "BLE Mesh is conceptually closer to CAN-bus broadcast or MQTT pub/sub than to the BLE you've used. There's no concept of 'connecting to one device' — you publish to addresses; subscribers act."

### Missing examples / figures
- A figure showing 5 nodes with relay paths, one node out of direct range relayed via another. The §97.7 Lab 7 hints at this; a picture would land it.
- A picture of an element/model/state hierarchy (Node → Element[0..n] → Model[OnOff, Lightness, Health]) would clarify §97.2's prose.

### Insufficient depth
- The chapter's "from scratch" content (per the cookbook depth requirement) is thin — the §97.6 says "writing a mesh node application is analogous to Ch 95's GATT server but for mesh models — more involved, and the bluez-mesh D-Bus API is less mature." Then no code. The cookbook needs at minimum a `Application1`+`Element1` skeleton showing the model registration. Even 50 lines of pseudo-D-Bus would be enough. Without it, the chapter is purely descriptive and violates the user-memory requirement.

### Technical errors
- "thousands of nodes" — BLE Mesh's hard cap is 32767 unicast addresses minus reserved; practical networks are ~100–500 nodes due to flood control. "Thousands" is technically defensible but practically optimistic. Soften.
- "bluez-mesh maturity. The Linux mesh stack and D-Bus API are less polished than GATT." — Fair and honest. Keep.
- "address 0xC000" — `0xC000-0xFEFF` is the group-address range, correct.
- "AppKey 0... bind 0 0 1000" — model ID 0x1000 is Generic OnOff Server, correct.

### Knowledge prerequisites missing
- "Element" vs "Model" — both are first-mentioned in §97.2 and could use one more concrete example: "A 4-gang switch is one *node* with 4 *elements* (one per gang), each with a Generic OnOff Server model — so the phone app can address them independently."
- The NetKey/AppKey two-tier scheme — readers familiar with TLS will get it, but a one-line analogy ("NetKey is like the WPA pre-shared key; AppKey is like an application-layer TLS key — relay nodes have NetKey but not AppKey") helps.

### Other
- Lab 7 (relay test) is the magic-moment lab. Keep.
- Pitfalls "bluetooth-meshd vs bluetoothd conflict" is real — keep.


---

# Part VIIc — Cookbook (Wireless/Cellular/Industrial/Power): Review

## Cross-cutting observations
- Recurring pattern of using the placeholder `compatible = "rohm,dh2228fv"` for spidev binding. Since Linux 4.15+, mainline kernels actively warn when this name is abused as a generic spidev stand-in (`spidev: warning: please use a real DT compatible`). The book should either (a) document binding via `spidev` module parameters / DT overlay with a proper non-warning compatible, or (b) acknowledge this warning explicitly so readers know `dmesg` complaints are expected. Today it appears unflagged in chapters 98, 99, 101, 105, 106.
- Many chapters claim "no mainline driver, use spidev + user space" without showing the *real* kernel infrastructure that does exist (e.g., `drivers/net/ieee802154/`, `nl802154`, `regmap-spi`, `serdev`). For a book about embedded Linux driver internals, "Part VII must show driver internals + a from-scratch implementation" — but chapters 100, 102, 103, 104 are mostly userspace-daemon configuration recipes with no kernel walk. Either tag those chapters as "integration recipes" or add a kernel-internals section.
- The reader is an MCU engineer. Almost no chapter explicitly relates the Linux device model back to "what you'd write on STM32." Comparisons like "this is the same as the STM32 HAL_SPI_Transmit you've used, except wrapped in an spi_device" would massively shorten the on-ramp. Currently the MCU bridge appears only in scattered asides.
- ASCII figures are often present but lack a key "subsystem stack" diagram for each chapter (e.g., where in the stack does the user lab code sit vs the kernel driver vs the userspace daemon). A consistent 5-row stack diagram per chapter (HW → kernel driver → uapi → daemon → app) would tie the whole Part VII together.
- Test/verification subsections give shell commands and expected outputs, but very few chapters show *expected dmesg lines* — the single most useful debug surface for an MCU engineer just learning Linux. Add a "what dmesg should look like on a healthy probe" block.
- Driver internals walks are paraphrased pseudo-C ("Walk of nrf24_write paraphrased"). For a reference book this should cite the file:line in the kernel tree (or out-of-tree repo) used so the reader can open it side-by-side. Without that the snippets read as invented.
- Cellular chapters (102–104) repeat ModemManager/NetworkManager bring-up. Consider consolidating that material into a shared "cellular concepts" intro chapter so the per-modem chapters can focus on what differs (band sets, AT extensions, low-power modes, certification).
- The book uses Unicode box-drawing in code blocks. On older terminals + PDF builds these may not render; consider providing ASCII-only fallbacks or noting font requirements.
- Several chapters reference "Ch 95–97" or "Ch 91" for cross-references; verify these chapter numbers are still correct after any TOC renumbering.

## Ch98 — LoRa
### Readability
- Sentence "The radio is easy. The link budget is the engineering." is good. But the intro `> Focus:` paragraph is one 4-line wall — break into two bullets ("CSS gives ~−137 dBm…" / "tune SF/BW/CR/preamble…").
- "Most engineers cargo-cult the 'Arduino LoRa library'…" is editorial; either embrace this tone consistently across Part VII or soften ("Most introductory tutorials hide the modulation details…").
- "the chip transmits OK at first but receive sensitivity is –80 dBm" — clarify "−80 dBm minimum detectable signal" (currently reads ambiguously, could be misread as "−80 dBm sensitivity is fine").

### MCU-engineer friendliness
- Reader knows SPI from MCU; reinforce by stating outright "in MCU code you'd do `HAL_SPI_Transmit(&hspi, &tx, 2, 100)` — `ioctl(SPI_IOC_MESSAGE)` is the Linux equivalent, with the kernel driver doing chip-select + clock-rate negotiation for you."
- The "command vs register-mapped" distinction between SX1276 and SX1262 should mention this is the same shift the reader saw between, e.g., a NOR flash (register-style) and an EEPROM with opcodes — make the analogy explicit.

### Missing examples / figures
- No diagram showing "where the user-space lab driver sits vs where a netdev-style kernel driver would live." Add a stack diagram: hardware → SPI controller (ecspi) → spidev OR sx127x kernel driver → userspace app OR daemon.
- A LoRaWAN class A/B/C timing diagram would massively help. Currently only mentioned as a list of three classes; show "JoinRequest uplink window + RX1/RX2 downlink windows" to make Class A concrete.
- Air-time formula is referenced but not shown. Either include the formula `Tpacket = Tpreamble + Tpayload(SF,BW,CR,n_bytes,DE,CRC,IH)` or link to Semtech AN1200.13.

### Insufficient depth
- §98.5 "the kernel side" lists three reasons no mainline driver exists, but should also discuss the existing `linux-wpan` infrastructure (ieee802154 subsystem) for comparison — explain why LoRa *couldn't* fit there cleanly (no MAC standard).
- The "translating to SX1262" table is a great hook, but the from-scratch SX1262 code is left as a stretch lab. For depth this chapter promises, include at minimum a `sx1262_setpacketparams()` function in real code.

### Technical errors
- Bitrate formula: "Bitrate ≈ SF × BW / 2^SF × CR" — the CR here should be the *coding rate fraction* (4/(4+CR_idx)), and the formula as written is dimensionally consistent only with specific conventions. Recommend stating it as `Rb = SF × (4/(4+CR_idx)) × BW / 2^SF`.
- "+22 dBm internal PA" for SX1262 is correct; "+118 mA at +22 dBm vs ~120 mA at +20 dBm for SX1276" — SX1276's +20 dBm PA_BOOST is typically ~120 mA but Semtech also lists +17 dBm at ~90 mA; clarify the operating point.
- RSSI offset claim "−157 + RSSI for HF; subtract 164 for LF" — the SX1276 datasheet has it as `RSSI = -164 + reg` for LF and `RSSI = -157 + reg` for HF; the code uses `-157 + reg` for HF correctly, but the comment "subtract 164 for LF" is misleading — it's *replace* with −164, not subtract.
- The DT placeholder `compatible = "rohm,dh2228fv"` is the well-known spidev hack; flag the kernel warning explicitly.
- `BURST_WRITE(FIFO, payload, N)` step 9 happens before step 7 (PayloadLength) in some example flows; clarify the FIFO/PayloadLength ordering — the SX1276 datasheet's TX flow has PayloadLength set before FIFO write in some modes.

### Knowledge prerequisites missing
- Assumes the reader knows what "duty cycle" is in regulatory terms (ETSI 1% per hour). One sentence on regulatory frameworks (ETSI EN 300 220, FCC Part 15.247) would help.
- Assumes familiarity with `libgpiod` (mentioned but not introduced); cross-ref the earlier GPIO chapter.

### Other
- Lab item 9 "Switch to SX1262 (stretch)" is too vague. Either commit to providing the SX1262 reference code in the book repo, or remove and replace with a smaller stretch item.
- §98.10 "Concentrator SPI clock too fast" — SX1303 supports up to 8 MHz; this is correct but mention also that SX1302 supports the same; the wording "8 MHz" needs a chip-rev qualifier.

## Ch99 — Sub-GHz proprietary
### Readability
- §99.1 table: "Address-aware? yes (Enhanced ShockBurst)" — the `Enhanced ShockBurst` markdown is inside a table cell with backticks; renders awkward in some markdown processors. Use bold or plain text.
- "the in-tree wireless dir does not contain this — verify with current kernel" parenthetical in §99.6 leaks author-note language into final text. Decide and commit ("There is no in-tree CC1101 driver in modern kernels (last reviewed against v6.x)").

### MCU-engineer friendliness
- The state-machine framing is excellent for an MCU reader. Reinforce: "this is essentially the same state diagram you'd code in an STM32 LL driver, except now it's distributed across SPI commands."
- Mention that "Enhanced ShockBurst" auto-ACK is functionally what STM32 + nRF24 Arduino libraries already gave the reader — but now you see the wire-level mechanism.

### Missing examples / figures
- A figure showing nRF24's TX FIFO → RF → auto-ACK → STATUS flag wakeup sequence (timeline diagram, microseconds-scale) would be golden for an MCU reader.
- No oscilloscope/logic-analyzer trace example for the SPI command stream during a TX burst. A captured trace would make the "STATUS comes back in the first byte, free" comment land much harder.

### Insufficient depth
- §99.6 CC1101 register configuration says "40 lines from SmartRF Studio" and stops there. For a from-scratch promise, include at least one fully filled register table for a specific configuration (e.g., 868 MHz / 2-FSK / 38.4 kbps / GFSK) so the reader can compile/run without an external tool.
- No discussion of how the CC1101 `MCSM*` registers govern automatic state transitions (RXOFF_MODE, TXOFF_MODE) — these are the most underdocumented and bite users in production.
- The "from-scratch CC1101" §99.6 is only 30 lines; promise of "300 lines" is unfulfilled. Either deliver the 300-line version or restate scope.

### Technical errors
- "TX_ADDR ≠ RX_ADDR_P0" pitfall: phrased awkwardly. Should say "On the PTX, RX_ADDR_P0 must equal TX_ADDR so the auto-ACK frame is received on pipe 0." Currently reads as if the inequality itself is the bug.
- "CC1101 has no auto-ACK" — true that there's no hardware auto-ACK frame, but CC1101 does have hardware CRC, address filtering, and an "ACKnowledgement" handled via `MCSM1` RX→TX flip on packet receipt. Worth mentioning to be precise.
- "every WiFi, BT, microwave oven, baby monitor uses 2.4 GHz" — "Sub-GHz (CC1101 433/868) is 10× quieter" — quantification is hand-wave; soften to "typically much less congested."
- nRF24L01+ "1 Mbps TX burst draws ~12 mA peaks" — datasheet lists ~11.3 mA at 0 dBm 1 Mbps; "peaks" is misleading because that's a continuous current, not a burst peak. The PA causes the rail droop, but for a different reason than implied.

### Knowledge prerequisites missing
- "FCS is XOR of LEN through last data byte" appears in chapter 100, not here; for CC1101 the chapter doesn't define FCS at all. Define on first use.

### Other
- The DT example uses `compatible = "rohm,dh2228fv"` (see cross-cutting).
- Lab item 8 "Bridge test" references Grafana with no prior context; either omit or hand off to a chapter that covers MQTT→Grafana.

## Ch100 — ZigBee / Thread / 802.15.4
### Readability
- Intro `> What:` is overlong; the bullet "i.MX6ULL is the gateway, not a node" is the load-bearing insight — pull it to the very first sentence.
- §100.2 RCP/NCP/SoC table is good. But "Spinel" appears with no expansion until §100.6. Define on first mention.

### MCU-engineer friendliness
- An MCU reader is unlikely to have used HCI-style host-controller protocols. Forward-reference Ch 95's BLE HCI section explicitly and say "Spinel is to Thread what HCI is to BLE."
- Highlight that nRF52840 firmware is in C (Zephyr/nrfx) — this matters because the reader can in principle modify it. Make the boundary "this is the chip-side firmware you don't write" vs "this is the Linux side you do" sharper.

### Missing examples / figures
- No diagram of the otbr data plane: Thread mesh → wpan0 (netdev) → IPv6 routing → eth0 upstream. The §100.6 description is text-only.
- Sequence diagram of a Thread device joining (KEK exchange, MeshLocal address allocation) would help readers reason about pairing failures.

### Insufficient depth
- This chapter is mostly *daemon configuration* (zigbee2mqtt, otbr-agent). Per the cookbook depth requirement, add at least one section that walks an actual in-tree kernel driver: `drivers/net/ieee802154/at86rf230.c` is mentioned but never walked. Show `at86rf230_xmit_complete()` or `at86rf230_isr()` to fulfill the driver-internals promise.
- The "from-scratch" §100.9 is a single 4-line `iwpan` invocation. That's not a from-scratch implementation. Either build a tiny `AF_IEEE802154` raw socket sender/receiver in C, or rename the section.

### Technical errors
- "WiFi ch 1: ████ ... WiFi ch 6: ████ ... WiFi ch 11: ████" — visually places these as if they're discrete; clarify that each WiFi 2.4 GHz channel is ~22 MHz wide and overlaps multiple ZigBee channels.
- "802.15.4 PHY: −96 dBm receiver sensitivity (vs LoRa SF12's −137; vs BLE 1M's −93)" — typical 802.15.4 sensitivity is −97 to −101 dBm depending on chip; −96 is conservative but worth citing the chip rather than asserting as a PHY property.
- "Frame format: SOF=0xFE, …, FCS is XOR of LEN through last data byte" — the TI ZNP framing FCS is correct; verify this is XOR (some texts call it "CRC-XOR"). The cited TI document is "Z-Stack Monitor and Test API," confirm spelling.
- "Apple HomeKit, Google Nest, Matter" under Thread ecosystem — Matter is a separate row (it's an *application* layer over Thread/WiFi). Putting it in the same cell is technically wrong even though §100.8 clarifies.

### Knowledge prerequisites missing
- Reader hasn't necessarily met IPv6 link-local vs ULA addressing; one paragraph on `fe80::/10` vs `fd00::/8` would help (or forward to the networking part of the book).
- 6LoWPAN compression isn't explained even though `lowpan0` is created. A sentence on header compression would close the loop.

### Other
- Channel-selection guidance "ZigBee-friendly: 15, 20, 25, 26" — channel 26 has FCC TX-power restrictions in the US; flag this.

## Ch101 — UWB ranging
### Readability
- §101.1 SS-TWR vs DS-TWR equations are dense; introduce the *intuition* first ("DS-TWR adds a second round-trip so any constant clock drift appears symmetrically and cancels in the math").
- Some sentences mix abbreviations (DWT, DTU, dtu, uus). Standardize and define on first use: DTU (device time unit), UUS (microseconds, scaled). Currently §101.5 uses both `dtu` and `DWT_TIME_UNITS` without unifying.

### MCU-engineer friendliness
- MCU reader knows time-of-flight from MCU TIM input-capture (e.g., ultrasonic range sensors). Relate: "this is the same as input-capture timestamping a pulse, except the timestamp has 64 GHz resolution in chip silicon."
- The antenna-delay calibration is a familiar concept (cable-delay calibration in lab equipment); make that bridge.

### Missing examples / figures
- A figure showing the leading-edge detection / first-path correlation vs multipath peaks would convey *why* UWB is accurate where BLE/RSSI is not. Reference Qorvo's "Channel Impulse Response" plot.
- A trilateration geometry figure (3 anchors + tag, three circles intersecting) for §101.6 — currently it's algebra only.

### Insufficient depth
- §101.5 from-scratch DS-TWR initiator code is incomplete (full version is hand-waved at end). Either include the full responder counterpart in the book or in a clearly linked code repo path.
- The chapter does not walk an out-of-tree driver (`thotro/dw1000-driver` is just listed in §101.11). Drop in a code walk of the most interesting function (the IRQ handler that extracts the RX timestamp from the FAQS register).
- No mention of the `nl802154` infrastructure or whether UWB could plug in as a 4z-MAC variant on top of `at86rf230`. Even a one-line "this is currently not in the kernel ieee802154 subsystem" closes the loop.

### Technical errors
- DEV_ID values: DW1000 returns `0xDECA0130` (correct in §101.10) but the code in §101.5 checks `0xDECA0302` for DW3000. Datasheet confirms DW3000 reads `0xDECA0302`; double-check the responder code mirrors this.
- "the 40-bit counter at 64 GHz wraps every ~17 s" — 2^40 / 64e9 = 17.18 s, correct.
- "1 µs = 65536 DWT ticks" — DWT tick is 1/(499.2e6 × 128) ≈ 15.65 ps; 1 µs / 15.65 ps ≈ 63897, not 65536. The factor 65536 is `UUS_TO_DWT_TIME` where UUS is a "scaled µs" used internally — clarify the unit; otherwise readers computing distances will get them wrong by ~2.5%.
- "DS-TWR achieves the ~10 cm accuracy spec" — typical figure is 10 cm 1-sigma in benign environments; in NLOS/multipath it degrades to 30–50 cm. Caveat needed.
- "60 µAs" / "75 µAs" energy budget for TWR — units inconsistent (Coulombs vs Ah). Recheck.

### Knowledge prerequisites missing
- No introduction to "PRF" (pulse repetition frequency) before the table cites it. Define on first use.
- Reader needs to know that UWB transmit power is FCC-restricted to −41 dBm/MHz EIRP — mention this constraint upfront.

### Other
- "Most readers won't do this" preamble for §101.9 is honest but odd for a cookbook; either commit to the recipe or drop it.

## Ch102 — USB 4G LTE modems
### Readability
- Intro `> What:` paragraph is one long sentence; break it. "Four-layer onion" metaphor in `> Why:` is nice; carry it forward into §102.3.
- "Switching modes is one AT command + reset" — true but reader may want to know which AT command lives where; the actual command is later in §102.7.

### MCU-engineer friendliness
- MCU reader has likely used AT-command modems via UART. Lead with "the AT interface you know from SIM800/SIM900 is unchanged — what's new is the USB composite device and the QMI/MBIM data path."
- The driver-binding table in §102.3 is exactly the kind of "where does my packet actually go" diagram MCU readers need. Reinforce by mapping back to: "on STM32 + USB-host, you'd write code to enumerate each interface yourself."

### Missing examples / figures
- A `dmesg` walkthrough showing the actual kernel lines as a Quectel EC25 enumerates would be invaluable (drivers binding to each interface). Currently only mentioned in lab step 1.
- Sequence diagram of QMI session start: `qmicli` → `cdc-wdm0` → modem → `WDS_START_NETWORK` reply → `wwan0` IP assignment.

### Insufficient depth
- The chapter promises "a QMI session opener using libqmi from scratch" but never delivers a code listing — only `qmicli` invocations. For depth, add a small C example using `libqmi-glib` to send `QmiMessageWdsStartNetwork`.
- `qmi_wwan_probe()` walk is 8 lines and uninformative. Either expand to show the QMI/QMAP data-path framing or remove.

### Technical errors
- "USB modems are autobound — no DT needed beyond ensuring USB-OTG/Host is enabled" — true. But the `vbus-supply` example doesn't always provide 2.5 A; consider clarifying that the regulator on iMX6ULL EVK is typically a 500 mA `reg_usb_otg1_vbus`, hence the brownout pitfall.
- "PPP throughput cap of ~1 Mbps" — closer to 0.5–1 Mbps with byte stuffing; "1–2 Mbps" elsewhere in the chapter contradicts.
- Quectel PIDs: 2c7c:0125 is correct for EC25 in default ECM+AT mode; pure-QMI is sometimes 0x0121 or 0x0125 depending on firmware. Worth caveating: "PIDs depend on firmware build; treat the table as illustrative."
- "AT+QCFG="usbnet",0 sets QMI" — value 0 is RMNET/QMI for EC25 firmware ≥ some build; older firmware uses different mapping. Add firmware version caveat.
- "T-Mobile: `fast.t-mobile.com`" — that APN is obsolete; current is `fast.t-mobile.com` or `epc.tmobile.com` depending on plan; recommend pointing to a maintained APN database rather than hardcoding.

### Knowledge prerequisites missing
- USB composite-device concept (one device, multiple interfaces) should be introduced or back-referenced; an MCU reader who's only used UART modems may not know this.
- ModemManager's D-Bus integration is implied; one line on "ModemManager is a D-Bus daemon; mmcli/nmcli are D-Bus clients" would help.

### Other
- Lab item 10 cross-references Ch 91 (WiFi); verify chapter numbering.
- §102.10 "qmi-firmware-update needed" — link to Quectel's official tool, not a community wrapper, to avoid bricking risk.

## Ch103 — UART AT-command modems
### Readability
- `> What:` intro is dense. Splitting on "the trade:" into its own bullet would be cleaner.
- "PPP is a circa-1989 link protocol" tone is good; consistent voice with Ch 98.

### MCU-engineer friendliness
- MCU readers have used SIM800/SIM900 over UART; this is a fantastic anchor. State up front: "This is the same modem you've already used from STM32 + UART. The only new thing is `pppd` and the kernel `n_ppp_async` line discipline."
- Walk the line-discipline concept explicitly — MCU readers don't know what a `TIOCSETD` is. One paragraph: "in MCU code you'd parse PPP in your own code; on Linux, `setldisc(N_PPP)` tells the kernel `tty` subsystem to do HDLC framing in-kernel."

### Missing examples / figures
- A timing diagram of the PPP bring-up: AT mode → ATDT*99# → CONNECT → LCP CONFREQ/CONFACK → IPCP CONFREQ/CONFACK. Currently only described in prose.
- A figure for the n_gsm CMUX channel multiplexing: one UART → many `gsmttyN` virtual UARTs.

### Insufficient depth
- §103.5 "How ppp_generic works" is half a page; for a from-scratch-internals book this should walk `ppp_input()` and `ppp_async_input()`. Show the HDLC byte-stuffing and FCS-16 logic.
- The "from-scratch supervisor" §103.7 is a shell script. The cookbook depth requirement wants driver internals — consider adding a tiny C program that uses raw HDLC framing without pppd, to demonstrate what pppd actually does.

### Technical errors
- "max ~5 Mbps (versus 150 Mbps over USB-QMI), and you live with PPP overhead" — at 115200 baud, PPP throughput is bounded to ~10 KB/s ≈ 80 kbps after framing. To get "5 Mbps" you'd need >5 Mbps UART (Linux supports up to 4 Mbaud on many i.MX UARTs but not all). State the baud rate explicitly.
- "PPP over UART, ~1–3 Mbps on Cat-1" — at 115200 baud, this is impossible (115.2 kbps line rate); needs higher baud rate. Recommend mentioning 921600 baud and clarifying that "5 Mbps" requires the modem's high-speed UART option.
- "echo 'AT' > /dev/ttymxc3" — this approach reads back to a separate `cat` process. Many newcomers will be confused why their `echo` "didn't return anything." Better to use `at_client.py` from Ch 102 consistently.
- §103.4 chat script: `'' AT` then `OK ATZ` — the `''` expect-empty then send `AT` is correct, but newcomers often write `OK AT` thinking it expects OK first. Add a one-line "first chat line is unusual: expect nothing, send AT to wake the modem."
- "n_gsm framing errors silent" pitfall is good; add that the kernel exposes line-discipline counters in `/proc/tty/driver/ttymxc` for debugging.

### Knowledge prerequisites missing
- HDLC byte stuffing / FCS-16 isn't explained. Either explain or cite RFC 1662.
- `ldattach` is mentioned but not introduced; cross-link to its man page or explain.

### Other
- Lab item 9 mentions baud "115200 (~80 kbps), 921600 (~600 kbps)" — these match expectation, good. But step 6 (CMUX) requires the modem to support `AT+CMUX=0`; not all do. Add a "if your modem doesn't support CMUX" note.
- The PPP material in §103.4 is excellent and worth being the canonical "how PPP comes up on Linux" reference; consider promoting some of it to a Part VI networking chapter.

## Ch104 — NB-IoT / Cat-M1
### Readability
- `> Why:` energy budget "5 J → 1 J" is great anchor. Quote real numbers (Joules/uplink) more in §104.5 to make the case land.
- §104.3 "9600 baud default!" deserves a sidebar — newcomers will set 115200 and see garbage.

### MCU-engineer friendliness
- The PSM/eDRX discussion lands well for an MCU reader who's used STM32 STOP/STANDBY modes. Explicitly call out: "PSM is the modem's equivalent of STM32 STANDBY: deep sleep with state preserved."
- The "wake-controller MCU + modem" pattern in §104.5 is classic embedded — call out that you don't need the i.MX6ULL at all for a 10-year sensor; if i.MX6ULL is overkill, an STM32L0 is cheaper. This is honest and reinforces the trade-off.

### Missing examples / figures
- No oscilloscope trace of the PSM enter/exit transition. A real-world current-vs-time plot for the BC95 going from active → PSM → wake → TX is the "show, don't tell" the chapter needs.
- A timeline showing T3324 and T3412 firing relative to the modem state would help. Currently the two timers are explained as bullets but the temporal relationship isn't visualized.

### Insufficient depth
- §104.5 "10-year sensor" walks the math but doesn't show the actual firmware. Add at least a state-machine pseudocode: sleep → wake → read BME280 → AT+CFUN=1 → wait CEREG=1 → AT+NSOST → AT+CFUN=0 → sleep.
- The new kernel `drivers/net/wwan/` subsystem is only mentioned in passing — given this is the modern path for QMI/MBIM, a one-page walk of the WWAN device model would close a gap left from Ch 102.

### Technical errors
- "Active Timer (T3324)" — per 3GPP TS 24.008, T3324 granularity is 2 s base unit (encoded 8-bit), not "4 s = `00000010`". Verify the bit encoding: `00000010` in the T3324 byte = unit "deactivated" or "2 s × 2 = 4 s"? The encoding is `[3 bits unit][5 bits value]`. `00000010` = unit 000 (2 s) × value 2 = 4 s — correct. State the encoding explicitly.
- Similarly for T3412: `00000110` is asserted as "24 hours" — verify: `[3 bits unit][5 bits value]`. `00000110` = unit 000 (10 min) × value 6 = 60 min. To get 24 h, unit 010 (1 hour, encoded `010`) × value 24 = `0_1011000`. The example value in the chapter computes to 60 min, not 24 h. Recompute.
- "NB-IoT can transmit at up to +23 dBm (200 mW)" — correct.
- "MCL 164 dB" is the Cat-NB1 max; Cat-NB2 is 164 dB also; verify and cite the 3GPP source.
- "Per cycle 152,000 µAs = 42 µAh" — `µAs / 3600 = µAh`, so `152000 / 3600 = 42.2 µAh`. Correct.
- "Per year 413 mAh" → "Battery life at 19 Ah usable: ~46 years" — `19000 / 413 = 46 years`, correct. But the "limited by self-discharge & temperature" caveat earlier is critical; consider stating "shelf life-bound" up front.

### Knowledge prerequisites missing
- T3324/T3412 are introduced as 3GPP timer names without saying these come from EMM (EPS Mobility Management). One sentence on EMM context would help readers grep the spec.
- Reader needs to understand "registered but idle" vs "RRC Connected" states. A one-paragraph 3GPP state model (EMM-DEREGISTERED → EMM-REGISTERED + ECM-IDLE → ECM-CONNECTED) would massively clarify why PSM works.

### Other
- §104.7 "PSM not granted by carrier" is the most realistic pitfall; consider promoting it to the chapter's introduction so readers don't design products based on an unverifiable assumption.
- Lab item 5 "Measure full uplink cycle energy" — note you need a low-side current monitor (INA226 or similar); a multimeter won't capture the µs-scale TX peaks.

## Ch105 — RFID / NFC
### Readability
- `> Focus:` paragraph is excellent ("inductive coupling"). Strong start.
- §105.6 from-scratch code is fine, but the comment "(full ~400 lines)" with a 150-line listing is confusing — clarify what's in the omitted 250 lines (Crypto1 + block read, presumably).

### MCU-engineer friendliness
- MCU readers may have used MFRC522 with Arduino. State this explicitly: "If you've used the Adafruit `MFRC522.h` library, this chapter is the Linux equivalent with the framework stripped."
- The "the chip's silicon does the framing" point is huge for MCU readers used to bit-banging — reinforce.

### Missing examples / figures
- A figure showing the LC tank circuit + matching network + tag inductive coupling would explain "antenna detuning" pitfalls visually.
- No diagram of the ISO 14443 anticollision tree (the bit-by-bit binary search for tag UIDs). For readers wanting to understand multi-tag environments, this is essential.

### Insufficient depth
- "Crypto1 implementation" is left as an exercise. For depth, walk the LFSR-feedback structure of Crypto1, or at minimum point at the Crapto1 / mfoc reference implementation file:line.
- Walk of the in-kernel `pn533` driver is shallow (8 lines of pseudocode). For driver-internals promise, walk the full RX path: USB URB → `pn533_recv_response()` → `nfc_targets_found()` → netlink event. Trace through real source.

### Technical errors
- "Mifare Classic Crypto1 ... reverse-engineered in 2008" — true (Nohl & Plötz, CCC 2007/2008). Crapto1 paper.
- "MFRC522 v2.0 = VersionReg 0x92" — datasheet says VersionReg returns 0x91 (v1.0) or 0x92 (v2.0). The lab step 1 says "0x91 or 0x92" — consistent, good.
- "Mifare Ultralight" — chapter calls it Type A, no Crypto1. NTAG21x (NTAG213/215/216) are Mifare Ultralight C derivatives with optional 3DES. Distinguish UL vs NTAG.
- "DESFire ATQA is 0x4403 + SAK 0x20" — accurate for DESFire EV1+; verify EV2 SAK behavior.
- "MFRC522 modules ... 1 cm range" — typical actual range for cheap modules is 2–3 cm; "1 cm" is the worst case. Soften.

### Knowledge prerequisites missing
- ISO 14443 Type A vs Type B isn't differentiated in body; only "Type A: short frame, 7 bits" appears. Mention Type B (different modulation) briefly even if not implemented.
- "ASK modulation" introduced without expansion (Amplitude Shift Keying). Define on first use.

### Other
- §105.7 "DESFire: MFRC522 supports framing but not the AES" — actually MFRC522 has no AES at all; host must implement. Worth saying "use OpenSSL/mbedtls AES for DESFire on the host side."
- The `compatible = "rohm,dh2228fv"` pattern reappears (see cross-cutting).

## Ch106 — Fingerprint sensors
### Readability
- `> Why:` is good. The "fingerprint = dominant biometric" framing is right.
- §106.3 framing protocol — the byte breakdown is good but the example `EF 01 FF FF FF FF 01 00 03 01 00 05` reads as a single line; consider laying it out vertically with annotations.

### MCU-engineer friendliness
- MCU readers will have done UART command-response protocols (e.g., AT modems, Modbus); explicitly map "this is structurally the same as Modbus RTU: address + function + length + data + CRC."
- The biometric template *state* on the module is unfamiliar — call out the closest MCU analog: "templates in module flash are like persistent EEPROM slots on STM32; once written, they survive power loss."

### Missing examples / figures
- A figure showing the enrollment 3-step dance (capture 1, lift, capture 2, combine, store) would help. Currently text-only.
- A timing chart: "place finger" → IRQ asserts → GetImg returns → GenChar runs in 200 ms → Store takes 50 ms. Concrete latencies help product design.

### Insufficient depth
- The chapter doesn't touch on the kernel side (input subsystem, evdev) — but for typical embedded uses (UART command-response with the module doing matching) that's actually fine. State explicitly: "there is no kernel driver here; the module is purely a UART peer."
- `libfprint` is mentioned in one paragraph (§106.8). For depth, walk one libfprint driver (e.g., `drivers/synaptics/synaptics.c`) to show how USB scanners differ.
- No discussion of presentation-attack detection (liveness). For real-world security this matters; state outright "these modules have no liveness detection — a gummy-bear print can fool them."

### Technical errors
- "Score is 0..2000 (higher = better match); chip's threshold is typically 50" — for R503/Grow modules the typical score range is 0..2400 with default match threshold around 50; some firmware uses 0..400 ranges. State this is module-firmware-specific.
- "Default key for new cards is `FFFFFFFFFFFF`" — this is in Ch105 not 106; should not appear here. (Verified: it's not — false alarm.)
- "FAR < 0.001%" and "FRR < 1%" are vendor-spec — caveat that real-world numbers depend on enrollment quality.
- §106.6 `recv_pkt` reads exactly 9-byte header then `len` payload. But `len` includes the 2-byte checksum (per spec: "length = payload + checksum"). The code reads `len` bytes total into payload, then claims `len - 2` is the payload size. Correct, but the comment "Verify checksum (skipped for brevity)" should at least note that production code MUST verify it.
- "Slot overwrite on re-enroll" is correct; this pitfall is well-placed.

### Knowledge prerequisites missing
- PAM is introduced without explaining its module model; one paragraph on PAM stack (auth → account → session) would help readers who've never written one.
- "Address `0xFFFFFFFF` broadcast" — explain that this is the default but module address can be changed via SetAddress command; once changed, broadcasts won't work.

### Other
- Lab item 1 references `AT+VFY-PWD` — this isn't an AT command, R503 uses its own framing. Either show the framed VfyPwd packet (command 0x13) or remove the AT pretense.
- §106.7 PAM module example missing the `Makefile` / build steps; learners need to know it's compiled with `pam_dev` headers.

## Ch107 — GPS / GNSS + PPS
### Readability
- `> Focus:` paragraph distinguishes NMEA latency vs PPS edge precision excellently — best of any chapter so far.
- "stratum-1 NTP server" framing in `> Why:` is concrete and exciting; carry the same energy into the lab section.

### MCU-engineer friendliness
- MCU readers may have hooked a GPS module to STM32 PA10 RX and parsed `$GPRMC` manually. State explicitly: "if you've done this on MCU, you parsed NMEA in software; on Linux, `gpsd` parses for you and exposes JSON, and the kernel timestamps PPS edges with nanosecond precision (which an STM32 needs an input-capture timer to do)."
- The `chrony refclock` model deserves an MCU analog: "PPS to chrony is like a sync pulse to your SPI master — it tells the disciplinator 'this is the exact moment'."

### Missing examples / figures
- A figure showing the PPS edge vs NMEA sentence arrival timeline (PPS rises at T=0; NMEA arrives at T=50-200ms after) would visualize the latency story.
- No oscilloscope/logic-analyzer capture of the PPS pin + NMEA UART line during a one-second interval. Even ASCII art would help.

### Insufficient depth
- §107.4 PPS kernel side is one paragraph. For internals depth, walk `drivers/pps/pps.c::pps_event()` and how the IRQ handler timestamps the edge. Show the `ts_real` vs `ts_raw` distinction.
- The UBX parser in §107.7 is a great start but doesn't show how to *configure* the receiver — only how to parse. Add a `ubx_send_cfg()` function with the CFG-MSG / CFG-PRT / CFG-NAV5 sequence.

### Technical errors
- "PPS jitter: ~30 ns" for NEO-6M — datasheet states ~50 ns RMS; "20 ns" for NEO-9M is achievable but typically with TCXO; cite the datasheet figure type (RMS vs peak-to-peak).
- "u-blox NEO-9M ... concurrent dual-band L1/L5" — NEO-M9N is *single-band L1 only*; ZED-F9P is dual-band L1+L5. Verify which chip is meant. NEO-9 family vs ZED-9 family is a critical distinction for RTK.
- "u-blox NEO-9M ... 184 channels" — NEO-M9N has up to 184 receive channels but that's the GNSS engine, not "tracking" channels in the historical sense. Wording is fine but worth qualifying.
- "$GPRMC,123519.00,A,4807.038,N,01131.000,E,022.4,084.4,230394,003.1,W*6A" — this is the textbook NMEA example (taken from many references); fine but cite it as the canonical example.
- "8-bit PID byte" structure in §109 (LIN); here in §107: "$GPGGA fix quality" — fix quality is a single digit 0..8; mention what each value means.
- The chrony refclock example uses `noselect` on GPS — correct since GPS via SHM is just a label provider. Add a one-liner "noselect means 'don't use as time source, just use for the seconds label'."

### Knowledge prerequisites missing
- IRIG-B / PTP / NTP layering isn't introduced; for a reader new to time sync, "stratum" needs a sentence.
- Cold-start vs warm-start vs hot-start TTFF distinction isn't defined.

### Other
- Lab item 10 cross-references "TPS6594 + GPS for outage survival" — TPS6594 is the PMIC chapter (Ch 116); good cross-link, but verify the TPS6594 lab actually covers UPS-style operation.
- §107.10 references "Ch 51B" for PPS-wake — verify chapter exists.

## Ch108 — RS-485 + Modbus RTU
### Readability
- `> Focus:` paragraph is dense but accurate; consider breaking into two: "RS-485 physical layer" then "Modbus timing requirements."
- "ground reference (a multi-meter check across grounds is mandatory)" is great practical advice — call this out as a numbered checklist item.

### MCU-engineer friendliness
- MCU readers have used Modbus extensively on STM32; the chapter currently treats Modbus as new. Lead with: "you've done Modbus master from STM32 + libmodbus or hand-rolled code. The Linux path uses the same protocol with `libmodbus` (same author!) — the only new thing is kernel RS-485 mode."
- The "kernel toggles DE/RE via TIOCSRS485" pattern is the load-bearing Linux insight — make it the highlight.

### Missing examples / figures
- A timing diagram of DE/RE toggle vs UART TX would clarify "sub-bit-time precision" claim. Show: TX byte starts → DE asserts → bytes shift out → DE deasserts after last stop bit.
- Frame-on-the-wire ASCII capture: `[01][03][00][00][00][08][CRC_LO][CRC_HI] ... gap ... [01][03][10]...response`.

### Insufficient depth
- The chapter is short on driver internals. Walk `drivers/tty/serial/imx.c::imx_uart_rs485_config()` to show how the i.MX UART manages DE via RTS automatically.
- §108.5 inter-character timeout: explain `select()` timeout heuristic in libmodbus more concretely. The current "works fine at ≤38400" is too vague — what about 115200?
- No mention of `Documentation/driver-api/serial/serial-rs485.rst` in the kernel tree as the canonical reference.

### Technical errors
- "MAX485 ... Max speed 2.5 Mbps" — the basic MAX485 is 2.5 Mbit; MAX485E and MAX485EU vary. Worth caveating.
- "ADM2483 ... Max speed 0.5 Mbps" — actually ADM2483 supports up to 500 kbps; ADM2587 supports 16 Mbps with isolation. Confirm which model.
- "9600 default" for Modbus — many devices default to 19200 8E1; the spec defines both but most field devices default to 19200. Confirm and add nuance.
- "Bias resistors 680 Ω" — actual recommended is typically 560–680 Ω depending on supply voltage. For 5 V supplies, 680 Ω gives ~3 mA bias current and ~200 mV differential. For 24 V isolated buses, higher values. Add the formula.
- "Inter-character < 1.5 char-times; Inter-frame ≥ 3.5 char-times" — at >19200 baud, the Modbus spec switches to fixed 750 µs and 1750 µs respectively (since 3.5 char times become impractical). Mention this exception.

### Knowledge prerequisites missing
- Common-mode voltage / differential signaling intro is brief; readers unfamiliar with EIA-485 may want a more thorough physics primer (or cross-ref RS-485 chapter elsewhere).
- The Modbus "register addressing 0-based vs 1-based" trap is mentioned in pitfalls but deserves earlier prominent treatment.

### Other
- Lab item 6 "Bias test" — clarify what happens without bias: "expect to see slaves randomly assert ERROR responses or stop answering" so readers know what to look for.
- §108.7 inverter register map is "typical, vendor-specific" — readers may try this against any inverter and fail. Recommend they obtain the inverter's Modbus map document.

## Ch109 — LIN bus
### Readability
- `> Focus:` paragraph captures LIN's essence well. The break-signal explanation in particular is clear.
- "Linux's lack of native support means you write the framing yourself, which is a great UART exercise" — good framing; but a more positive tone would be "Linux's lack of native support makes LIN the perfect UART internals exercise."

### MCU-engineer friendliness
- MCU readers may have done LIN on STM32 via the dedicated LIN UART (USART_CR2_LINEN). State: "STM32's USART has hardware LIN mode that generates break + sync automatically; on Linux you must orchestrate this manually because the kernel UART driver doesn't expose LINEN equivalents."
- The reverse-engineering-junkyard-HVAC story in §109.8 is exactly the kind of project that hooks MCU readers. Lead with it.

### Missing examples / figures
- Oscilloscope capture of a LIN frame (break + sync + PID + data + checksum) with annotations is essential and missing. ASCII representation would suffice.
- LIN scheduler table diagram: e.g., "100 ms: poll ID 0x10; 200 ms: poll ID 0x11; ..." showing the master's polling schedule.

### Insufficient depth
- §109.6 LIN slave implementation is incomplete; the break-detection problem is acknowledged but no working code. Either provide a tested solution (TIOCGICOUNT polling loop with sample handling) or remove the slave section.
- The chapter promises "build a master and slave responder in C." Slave is left as half-done.
- Walking the i.MX `drivers/tty/serial/imx.c::imx_uart_handle_irq()` to see how break detection is reported via PARENB+framing errors would close the loop and fulfill driver-internals.

### Technical errors
- PID parity formula: P0 = ID0 ⊕ ID1 ⊕ ID2 ⊕ ID4 — correct per LIN 2.x.
- P1 = !(ID1 ⊕ ID3 ⊕ ID4 ⊕ ID5) — correct.
- Verified PID(0x10) = 0x50: bits = 010000; P0 = 0⊕0⊕0⊕1 = 1; P1 = !(0⊕0⊕1⊕0) = !1 = 0; PID = 01_010000 = 0x50. Matches §109.9 step 2. Good.
- "Wake pulse must be ≥250 µs" — LIN 2.x spec says ≥250 µs but ≤5 ms; the wake-pulse upper bound is also important.
- "tcsendbreak(uart_fd, 0); 250 ms in POSIX" — Linux man page says POSIX-undefined but Linux behavior is "min break length" when argument is 0 (about 250–500 ms in some drivers, ~13 bit-times in others). State that scope-verifying is mandatory.
- "Break field ≥13 dominant bits = ~1.4 ms low at 9600 LIN-baud" — 13 × (1/9600) = 1.354 ms; "1.4 ms" is a safe rounding. Correct.

### Knowledge prerequisites missing
- LIN sleep-mode + EN-pin behavior is introduced in §109.7 but the reader hasn't seen automotive sleep current budgeting; one sentence on car KL30 vs KL15 wake signals would help.
- Reverse engineering a real LIN slave requires knowing the slave's published `.ldf` (LIN Description File) format — mention it.

### Other
- §109.8 junkyard VW HVAC example is great. Add a safety note: "use a bench supply, NOT the car's 12 V, when reverse-engineering — bad commands can blow fuses or trigger airbag DTCs in the car's ECM."

## Ch110 — CAN deep dive
### Readability
- `> Focus:` paragraph balances depth + accessibility very well. Best `> Focus:` in the cookbook.
- "CAN-FD adds a second bit rate during the data phase" — could be clarified with a one-line drawing showing arbitration phase at 500 kbps + data phase at 2 Mbps.

### MCU-engineer friendliness
- MCU readers know CAN deeply from STM32 bxCAN/FDCAN. Lead with: "everything you know about CAN on STM32 applies; SocketCAN is just `bxCAN_Receive()` → skbs → PF_CAN sockets." This is a transition the reader will love.
- BCM is the standout Linux feature MCU readers don't have — call this out as "the kernel does periodic broadcast for you, freeing user-space from real-time scheduling."

### Missing examples / figures
- Bit-timing diagram in §110.3 needs more visual clarity. Show TQ count = 16, with each segment colored differently and the sample point marked.
- SocketCAN data-flow diagram: hardware → CAN controller IRQ → flexcan driver → can-raw socket OR can-bcm OR can-isotp → user app. Currently spread across the chapter.
- ISO-TP frame-type diagram (SF / FF / CF / FC) is missing despite being central to §110.6.

### Insufficient depth
- §110.4–§110.5 list the kernel modules but don't walk any. For depth, walk `net/can/raw.c::raw_rcv()` and how the kernel demultiplexes received frames to sockets via the `dev_add_pack(&can_packet_type)` mechanism.
- BCM section is a working example but doesn't walk the kernel side. `net/can/bcm.c::bcm_tx_setup()` is the key function.
- ISO-TP section is correct but doesn't explain *why* a kernel module is needed (rather than user-space libisotp). Touch on the kernel timer + STmin enforcement that makes a kernel impl more reliable.

### Technical errors
- "33 MHz CAN clock" — i.MX6ULL FlexCAN clock source is typically PLL3 USB-derived (e.g., 60 MHz) or peripheral clock; not 33 MHz. The example calculation is good but the input clock should be from i.MX6ULL's actual clock tree (likely 30/60 MHz).
- "CAN-FD ... CRC15" — classic CAN has CRC-15; CAN-FD has CRC-17 (≤16 byte) and CRC-21 (>16 byte). Chapter is correct on FD but uses "CRC15" only as classic's.
- "33 MHz / 500 kbps = 66 TQ per bit" — math correct (66 = 33e6/500e3). But i.MX6ULL FlexCAN typically uses 30 MHz, giving 60 TQ — a more realistic example.
- "ISO 11898-1:2015 (CAN-FD)" — ISO 11898-1:2015 is the data-link spec; CAN-FD requires also -2:2016 for physical. Both editions.
- "candump can0  123   [8]  DE AD BE EF 00 01 02 03" — the `[8]` is the DLC; correct format.
- Bus-off pitfall mentions `restart-ms 100` — kernel correctly supports this. Worth mentioning `restart-ms 0` (no auto-restart, manual `ip link set can0 down` then `up` required).
- "MCP2515 ... up to 10 MHz SPI" — datasheet specifies up to 10 MHz; some clones top out earlier. Add caveat.

### Knowledge prerequisites missing
- "CSMA/CR" introduced as an aside; for readers new to network MAC protocols this needs one sentence on how it differs from CSMA/CD (Ethernet) and CSMA/CA (WiFi).
- The UDS application layer is referenced in §110.6 (mode/PID 0x22 0xF1 0x90) but not explained. Either provide a short UDS primer or forward-ref ISO 14229.

### Other
- Lab item 7 (capstone OBD-II) is gold. Add a safety note: "engine running, not driving; some PIDs are only valid when engine is on; double-check the OBD-II adapter wiring before plugging into the car."
- Lab item 10 (bus-off recovery via shorting) — add big warning: "ESD-safe environment; transceiver may survive but not all do; risk of damage to non-isolated SoC."
- The chapter is excellent; consider promoting some material (BCM, ISO-TP) to a dedicated "advanced CAN" chapter if length becomes an issue.

## Ch111 — Quadrature encoders & rotary
### Readability
- The QDEC truth-table at §111.2 is excellent. The "INVALID (missed an edge)" row is great — readers must understand this failure mode.
- "1.4 ms" vs "13 bits" is mixed terminology between Ch109 and Ch111; here keep it consistent within the chapter.

### MCU-engineer friendliness
- MCU readers have used STM32 TIM_EncoderMode (TIM1/2/3/4/5 support quadrature in hardware with zero IRQs). State this loudly: "STM32 has a TIM peripheral that does this in silicon at MHz rates with zero CPU. i.MX6ULL has the ENC peripheral but mainline Linux doesn't always expose it; this is why you'll often resort to GPIO IRQ software decode (slower) or an external chip."
- This is a great chance to talk about the trade-off "Linux gives you a powerful CPU but loses tight peripheral integration."

### Missing examples / figures
- Oscilloscope/timing capture of A and B signals during forward + backward rotation would be invaluable. ASCII fine but a real capture better.
- No diagram for the LS7366R wiring or the i.MX XBAR routing to the ENC peripheral.

### Insufficient depth
- "i.MX hardware quadrature ... Status in mainline" is honest but should commit to a concrete recommendation: at kernel v6.x specifically, what's supported? Without that the reader has to test themselves.
- The `rotary_encoder` kernel driver walk is shallow. The driver source is small and readable; walk its IRQ handler.

### Technical errors
- "QDEC_TABLE[16]" — indexing is `(prev_ab << 2) | curr_ab` which gives 0..15. Table values look correct for 4× decode. Confirm by tracing prev=00 curr=01 → index 1 → +1. Good.
- "i.MX6ULL ENC peripheral up to ~10 MHz edge rate" — the reference manual specifies maximum input frequency; verify against the RM. The IMX6ULL has ENC1/2/3 peripherals (multiple instances).
- "LPD3806-100BM-G5-24C-100ppr, $20" — LPD3806 is a real Chinese optical encoder; verify part number suffix.
- "LS7366R ... up to 40 MHz pulse rate" — datasheet specifies 40 MHz max quadrature input clock. Good.
- "ENC peripheral ... documented in NXP reference manual ch. 33-ish" — vague. Look up the actual chapter (the IMX6ULLRM has ENC at chapter 32 or so depending on revision).

### Knowledge prerequisites missing
- "Gray code" mentioned in DT binding (`encoding = "gray"`); not explained. One sentence: "Gray code = each step flips exactly one bit, which is what quadrature happens to produce."
- Index pulse / homing concept assumes the reader knows what "homing" is from CNC; new readers don't. One sentence.

### Other
- The chapter would benefit from forward-referencing Ch 112's closed-loop velocity example (§111.8) since it depends on the motor driver — currently it's standalone.
- Lab item 7 cross-references PID tuning; consider giving a brief Ziegler-Nichols recipe or pointing to a tuning chapter.

## Ch112 — Stepper & DC motor drivers
### Readability
- `> Focus:` paragraph is strong; covers steppers, DC, BLDC, FOC in 4 sentences.
- "FOC ... most engineers offload to a dedicated MCU because Linux's jitter exceeds the 10 kHz current-loop budget" — this is the key insight; emphasize it as the chapter's takeaway.

### MCU-engineer friendliness
- MCU readers will have used L298, BTS7960, DRV8825 from STM32. Lead with: "everything you've done on STM32 + step/dir works the same here; the only new thing is that the i.MX6ULL is faster CPU-wise but jitterier IRQ-wise."
- The "Klipper architecture: Linux planner + MCU stepper" model is exactly the right pattern for ex-MCU engineers — they instantly grasp the split.

### Missing examples / figures
- Stepper microstepping waveform diagram (full step vs 1/8 vs 1/256 current sine waves) would clarify the "smoother but lower torque" trade-off.
- H-bridge state diagram (forward, reverse, brake, coast) — there's the text drawing but a 4-state diagram would be cleaner.
- BLDC commutation table is good but a sketch of the 6 vector states (clock face with arrows) would help readers understand "rotating field."

### Insufficient depth
- TMC2209 UART CRC is referenced but not shown. For a from-scratch chapter, provide the full CRC-8 routine: `crc = (crc ^ byte) << 1` style.
- DRV8302 BLDC section is text-only. No code, no DT, no kernel walk. Either provide the gate-driver init code or scope it to "for BLDC use SimpleFOC on an external MCU."
- No discussion of the kernel `drivers/i2c/busses/i2c-rk808.c` style framework for motor control — current loop typically isn't kernel-level on Linux, but it would close the loop to acknowledge there's no in-tree FOC framework.

### Technical errors
- "Vref = Imax × 5 × 0.1 V" — DRV8825 formula is `Iref = Vref / (5 × Rsense)`. With Rsense = 0.1 Ω: `Vref = 5 × 0.1 × Iref = 0.5 × Iref`. For 0.8 A: `Vref = 0.4 V`. Matches the chapter. Good but the formula is written as `Vref = Imax × 5 × 0.1` which simplifies to `0.5 × Imax`; clarify.
- "NEMA17 stalled: 12 V / 3 Ω = 4 A" — NEMA17 typical winding resistance is 1.5–3 Ω; 4 A from 12 V is plausible. Good.
- "BLDC at 10,000 RPM with 14 magnetic poles cycles 14 × 10,000 / 60 = 2,333 commutations/s" — should be "14/2 = 7 pole-pairs × 6 commutations/electrical-rev × 10000/60 mechanical-RPS = 7000 commutations/s." Recompute. The point about Linux jitter is still valid but the number is wrong.
- "stepper microstepping ... lower torque per microstep" — actually, microstepping doesn't reduce holding torque (within ±5%); it reduces *step* torque granularity. Common misconception; clarify.
- TMC2209 has a built-in CRC (CRC-8/ATM); chapter shows pseudocode but not the polynomial. Add `polynomial 0x07` for completeness.

### Knowledge prerequisites missing
- PWM / duty-cycle / frequency intro is assumed from Ch 48; if Ch 48 hasn't covered, this might leave readers behind.
- PID intro assumed; for readers new to control loops, a one-paragraph "P controls now-error, I integrates past, D anticipates" would help.
- "Field-Oriented Control" is name-dropped; one sentence on Park/Clarke transforms or forward-ref a control textbook.

### Other
- Lab item 10 "Safety stop" is great and should be promoted to the start of the lab section — emergency stops are a topic readers should always think of first.
- §112.6 BLDC code references `apply_gates(pattern, pwm_duty)` — never defined. Either provide implementation or annotate as pseudo-code.

## Ch113 — WS2812 / SK6812 / APA102
### Readability
- `> Focus:` covers the SPI-4× trick perfectly. Best in the cookbook so far.
- The §113.3 LUT explanation (`0x88, 0x8E, 0xE8, 0xEE`) walks the encoding well.

### MCU-engineer friendliness
- MCU readers have written WS2812 drivers using DMA on STM32 (HAL_TIM_PWM_Start_DMA with a precomputed waveform). State explicitly: "this is the exact same trick you'd use on STM32 — encode 4 SPI bits per WS2812 bit, push via DMA. The encoding is identical."
- The "Klipper-style offload" pattern from Ch 112 could be invoked: "if you have 5000+ LEDs and 60 fps, you'd run an STM32 dedicated WS2812 driver and Linux as the animation source."

### Missing examples / figures
- ASCII timing diagram showing one WS2812 "0" and "1" bit (with annotated 0.4 µs / 0.85 µs vs 0.8 µs / 0.45 µs) would visualize the spec.
- A diagram showing the SPI bytes `0x88` and `0xEE` overlaid with the resulting WS2812 waveform would *make* the trick.

### Insufficient depth
- The chapter doesn't walk the kernel SPI DMA infrastructure (`spi_message_add_tail`, `dma_async`). For internals, add a short walk of `drivers/spi/spi-imx.c::spi_imx_setup_dma()` to explain *why* DMA works for big transfers.
- No mention of `drivers/leds/leds-ws2812-spi.c` (if it exists in any out-of-tree fork) or the LED class subsystem (`drivers/leds/`). Worth a one-liner acknowledging the LED framework.

### Technical errors
- WS2812 timing: T0H = 0.4 µs ±150 ns, T0L = 0.85 µs; T1H = 0.8 µs, T1L = 0.45 µs. The chapter's numbers are correct.
- "SPI `1000`" for "0" bit at 3.2 MHz → 312.5 ns high + 937.5 ns low. T0H spec is 0.4 µs ±150 ns (range 0.25–0.55); 312.5 ns is within range. Good.
- "SPI `1110`" → 937.5 ns high + 312.5 ns low. T1H spec is 0.8 µs ±150 ns (range 0.65–0.95); 937.5 ns is at the upper end but within. Good.
- "first WS2812 byte = G then R then B" — correct.
- "APA102 ... 5-bit global brightness 0..31" — correct; the start byte is `0b111_xxxxx` where the upper 3 bits are the marker.
- "Encode each WS2812 byte (8 bits) into 4 SPI bytes" — actually each WS2812 byte (8 bits) × 4 = 32 SPI bits = 4 SPI bytes. Chapter says this; the lookup table uses 2 WS2812 bits → 1 SPI byte (= 8 SPI bits = 2 WS2812 bits × 4). So 8 WS2812 bits = 4 SPI bytes via 4 LUT lookups. Correct.
- "1000-LED strip × 4× = 12 KB DMA buffer" — actually `1000 × 3 × 4 = 12000 bytes`. Correct.
- "SK6812 RGBW is GRBW" — verify; some SK6812 datasheets specify GRB+W order, others RGBW.

### Knowledge prerequisites missing
- "Gamma 2.2" — explain why eye perception is logarithmic.
- "HSV color space" — many MCU readers haven't thought beyond RGB; one paragraph on hue/saturation/value would help.

### Other
- Lab item 4 (power injection) is critical for any reader building a strip > 1 m. Add a wiring diagram explicitly.
- §113.7 gamma table generator Python expression is correct: `int((i/255.0)**2.2 * 255 + 0.5)` — but reader expects this to be C. Provide a static C array.

## Ch114 — Beepers, relays, SSRs
### Readability
- `> Why:` "shipped this for 5 years and it never fails" is exactly the right tone. Hold that.
- "AC safety — non-negotiable rules" §114.5 is excellent and should perhaps be a sidebar elsewhere (this material should never be skipped).

### MCU-engineer friendliness
- MCU readers have driven relays from STM32 with BJT + diode dozens of times. State: "this is mechanically identical to MCU practice; the only Linux-specific aspect is that the GPIO sysfs/gpiod is your interface instead of HAL_GPIO_WritePin."
- For the SSR section, contrast with the MCU reader's experience of "TRIAC + opto-isolator from STM32" — same circuit, different name.

### Missing examples / figures
- Relay back-EMF spike scope shot (with and without flyback diode) is mentioned in lab but the figure isn't shown in body. Add an ASCII representation of the voltage waveform.
- Zero-cross vs random-fire SSR timing diagram for inductive loads is missing despite being a critical pitfall.

### Insufficient depth
- This chapter is the most "thin" in the cookbook depth sense — it's almost entirely circuit guidance, no kernel walks, no driver internals. For Part VII depth requirement, add at least a short walk of `drivers/leds/leds-gpio.c` or `drivers/pwm/pwm-imx27.c` to show how GPIO/PWM frameworks bind to these actuators.
- No mention of the kernel `gpio-leds` for buzzer driving as LED-style trigger (`echo timer > /sys/class/leds/buzzer/trigger`). Add this — it's a clean abstraction.

### Technical errors
- "Songle SRD-05VDC-SL-C ... coil draws 30 mA at 5 V" — actually datasheet says ~70 mA at 5 V (coil resistance ~70 Ω); 30 mA is way off. Recheck — this matters for BJT base-resistor sizing.
- "2N2222 BJT ... 30 mA at 12 V" — BC547/2N3904/2N2222 typically rated for 200 mA collector current, but driving a 12 V coil through 2N2222 with 0.6 V Vbe + ~3 V Vsat means ~9 V across the coil. If coil resistance is 80 Ω → 110 mA — beyond 2N2222 spec edge. Use a Darlington (BC549) or MOSFET for relays.
- "GPIO direct-driving a relay coil. Coil draws 30 mA at 5 V" — see above; 30 mA is likely wrong.
- "VIH = 0.7 × VDD = 3.5 V" (Ch 113 reference) — accurate.
- "passive piezo ... drive at 2 kHz at 50% duty" — correct, though most piezos resonate at 3–4 kHz; mention the resonance lookup.
- "active buzzer ... most tolerate direct 3.3/5 V GPIO drive at <30 mA" — many Chinese active buzzers pull 50+ mA peak; check the datasheet. Recommend always using a transistor for safety.
- "Fotek SSR-40DA rated 40 A — actually good for 25 A with heatsink" — true; Fotek SSRs are notorious for over-rating. Good pitfall.

### Knowledge prerequisites missing
- Triac / SCR conduction modes not explained for SSRs.
- "Snubber" mentioned in SSR schematic but not explained. One paragraph on inductive-load snubbers (R+C across the triac for inductive loads).
- "Earth bonding" / GFCI / RCD are mentioned; for readers in regions without these, briefly explain.

### Other
- The chapter's safety emphasis is excellent. Consider adding a "Required reading before mains AC work" sidebar pointing to a real electrical safety course.
- Lab item 5 "SSR + AC load" — add an explicit "DO THIS LAB WITH A QUALIFIED ELECTRICIAN if you're not certified" warning.
- The chapter is short (~10 pages); this is fine — the topic doesn't need more — but add a closing forward-reference to Ch 116 (PMIC) for "controlling power rails as well as loads."

## Ch115 — Dual FEC + hosted Ethernet
### Readability
- `> Focus:` paragraph is accurate but dense. Splitting into "dual MAC" vs "SPI Ethernet" sub-paragraphs would improve scanability.
- Pitfall about "Bridge + ip address on members" is worth highlighting earlier (in §115.4).

### MCU-engineer friendliness
- MCU readers might have never used dual-NIC systems. Lead with: "if you've used STM32 + W5500 for a single Ethernet port, this chapter shows how Linux handles 2+ ports trivially via the netdev model — something STM32 + LwIP can't easily do."
- The W5500 "hardware TCP/IP" vs Linux netdev distinction will be familiar — many MCU folks have used W5500 for offload. Make the contrast explicit.

### Missing examples / figures
- A diagram of the two FECs sharing one MDIO bus (with separate PHY addresses 0 and 1) is essential — currently text-only.
- Router/bridge/isolated topology diagrams for §115.3-115.5 would clarify the use cases visually.
- A flow diagram showing NAPI poll (IRQ → schedule NAPI → poll budget → napi_complete) would help readers understand the receive path in §115.8.

### Insufficient depth
- §115.8 FEC driver walk is decent (~2 functions). Could go deeper on BD ring management — explain how the descriptor ring wraps and why it's allocated in DMA-coherent memory.
- PTP support is mentioned in §115.1 but not walked in §115.8 or anywhere. Cross-link to a "Linux PTP" chapter or add a short section.
- §115.6 W5500 paragraph could include the actual SPI command structure (W5500 has command/data registers) so readers see why it's "hardware TCP/IP" not netdev.

### Technical errors
- "i.MX6ULL ... 2× FEC each 10/100 Mbps" — correct.
- "Each FEC needs ... 50 MHz clock to RMII" — correct; the SoC's ENET_REF clock can source or be sourced.
- "Per-PHY address straps" — verify the KSZ8081 has a strap for `PHYAD[0]` etc.
- "DM9051 SPI at 20 MHz: ~8 Mbps" — realistic; DM9051 has 16-bit SPI burst mode that improves on this.
- "ENC28J60 SPI at 20 MHz: ~3 Mbps" — realistic; the chip's own MAC is bottleneck.
- "WIZnet W5500 ... mainline does not have W5500 driver" — there are out-of-tree W5500 drivers (w5100/w5300 are in `drivers/net/ethernet/wiznet/`). Verify if W5500 is in there too. The wiznet directory does have w5100-spi.c which supports W5100, W5200, W5300; W5500 support is in some out-of-tree forks but reaching mainline.
- Actually, mainline has `drivers/net/ethernet/wiznet/w5100-spi.c` (covers W5100); W5500 has been submitted but check version. Update wording if needed.
- "AAhB:CC" placeholder MAC — fine.

### Knowledge prerequisites missing
- RMII vs MII vs RGMII vs SGMII distinction isn't discussed; assumed familiarity. A one-paragraph summary would help readers picking PHYs.
- "NAPI" is referenced; one sentence on "NAPI = adaptive interrupt mitigation; combines IRQ + polling" would help.

### Other
- §115.7 mentions DM9051 throughput but doesn't mention KSZ8851 which is generally faster. Worth including in the comparison.
- Lab item 9 (PTP) is excellent and underexplored elsewhere — verify if there's a follow-up chapter on PTP.

## Ch116 — PMICs and regulator framework
### Readability
- `> Focus:` paragraph is excellent — the boot-sequence races warning is exactly the kind of thing MCU readers don't know they need.
- "Voltage encoding: per-buck typically `Vout = 0.6 + N × 0.025 V`" — show the actual conversion table or formula derivation for one buck.

### MCU-engineer friendliness
- MCU readers have used discrete LDOs many times. The "5–10 chips → 1 PMIC" transition is the right framing.
- The DVFS coordination is *unique to Linux* (MCU readers don't do this); call it out as "Linux's killer power-management feature."
- Mention that the regulator framework's "consumers declare in DT" pattern is the Linux equivalent of "STM32 LL_BUS_GRP1_EnableClock(...) for each peripheral."

### Missing examples / figures
- A power tree diagram (PSU → PMIC → BUCK1/BUCK2/.../LDO1/... → SoC rails → consumer drivers) is essential and missing.
- A timing diagram of DVFS transition (clock decision → regulator ramp → frequency change) would clarify §116.5 — the ordering is critical.
- A sequence diagram of suspend-to-RAM showing which rails go off and when.

### Insufficient depth
- The regulator framework walk in §116.3 is sysfs-level. For depth, walk `drivers/regulator/core.c::regulator_enable()` to show how the framework computes the dependency graph and enforces ordering.
- §116.4 power-up sequencing is described as "the PMIC enforces this" — but how does the kernel handle a rail that was *not* enabled by the PMIC at boot but needs enabling later? Touch on `of_get_regulator()` and `regulator_dev_register()`.
- The PMIC driver walk is missing. `drivers/regulator/pca9450-regulator.c` is small and readable; walk `pca9450_probe()` and `pca9450_set_voltage_sel()`.

### Technical errors
- "BUCK1: 1.0–1.65 V @ 3.5 A" — verify against PCA9450 datasheet; BUCK1's range is 0.6–2.187 V with up to 3.5 A.
- "BUCK5: 1.1 V / 1.35 V" — PCA9450 BUCK5 is the DDR rail; 1.1 V (DDR4) / 1.35 V (DDR3). Correct.
- "Power saving from 1.275 V to 1.150 V: static ~10%, dynamic ~28% at same f" — math: `(1.150/1.275)^2 = 0.81`, so dynamic decrease ~19%, not 28%. Re-derive: `1 - (1.150/1.275)^2 = 1 - 0.814 = 0.186`. Closer to 19%. Verify or rephrase.
- "i.MX6ULL has required power-up sequence" — correct that there is a sequence; specifics need to match i.MX6ULLRM ch. 11.
- "PCA9450 ... over-specified for i.MX6ULL but illustrative" — fair to use as illustration since i.MX6ULL more often pairs with PF3000 or BD71850; PCA9450 is technically i.MX8M.
- `regulator_summary` output indentation — verify it matches actual kernel output.
- "ramp-delay = <3125>" microvolts/microsecond — PCA9450 default ramp is around 6.25 mV/µs; verify the unit (kernel doc says µV/µs).

### Knowledge prerequisites missing
- "DDR3 needs ≤1 ms from VREF to VDDQ stable" — JEDEC spec; mention for readers unfamiliar with DDR timing.
- "VDD_SNVS always on" — what SNVS is hasn't been introduced; cross-ref Ch 8 or wherever it's defined.
- OPP table introduction is brief; one sentence on "OPP = Operating Performance Point: a kHz+voltage tuple."

### Other
- Lab item 8 "Add a custom OPP under-spec" is brave — but also risky. Add a strong warning about potential silicon damage from under-voltage operation.
- Lab item 9 "From-scratch I²C peek" — make explicit that this requires the regulator framework to NOT have already claimed the rail (else two writers).
- The chapter is excellent overall and ties together Ch 51B (DVFS) and Ch 75 (current measurement) — make these cross-references prominent.

## Ch117 — External RTC
### Readability
- `> What:` and `> Why:` paragraphs are well-structured. The "$0.50 chip + $0.30 coin cell" framing is effective.
- §117.7 "three clock domains coexist" is well-explained but the table format would be even clearer.

### MCU-engineer friendliness
- MCU readers have used DS3231 from STM32 endless times. State explicitly: "the chip and registers are identical to what you've done from MCU; the only new thing is Linux's rtc subsystem and `hwclock`."
- The `RTC_WKALM_SET` ioctl pattern is unique to Linux; explain "this is how userspace tells the kernel to enable a wake-on-alarm without touching the I²C bus directly."

### Missing examples / figures
- Timeline diagram of suspend → RTC alarm fires → wake → resume would clarify §117.5 wake-from-suspend flow.
- A diagram showing the three clock domains (RTC ↔ system clock ↔ NTP/PPS) with arrows for "sync direction" would help §117.7.

### Insufficient depth
- §117.6 driver walk is decent for `get_time` but doesn't walk `rtc_register_device()` or the IRQ chain registration. For depth, show how `rtc-ds1307.c` registers with the `rtc_class_ops` framework.
- Wakeup-source handling is non-trivial. Cross-link or explain how `device_init_wakeup()` interacts with `enable_irq_wake()` to make the GPIO IRQ a wake source.
- No mention of `nvmem` (some RTCs expose backed-up SRAM as nvmem-cells); MCP79410's 128B SRAM could be exposed this way.

### Technical errors
- "DS3231 ... ±2 ppm (1 min/year)" — 2 ppm × 365 days × 86400 s = 63 s/year ≈ 1 min/year. Correct.
- "PCF8563 ... ±20 ppm (10 min/year)" — 20 ppm × 365 × 86400 = 630 s = 10.5 min. Correct.
- "DS3231 has two alarms; PCF8563 has one" — DS3231 has Alarm1 + Alarm2 (correct); PCF8563 has one (verify against datasheet — PCF8563 has 1 alarm).
- "MPU-6050 IMU also defaults to 0x68. Bus conflict." — Correct. AD0 strap on MPU-6050 changes to 0x69.
- "Year-2100 problem" — DS3231 stores year as 00–99 + century bit; in 2100 the century bit flips. Some drivers handle it, some don't. Worth a one-liner about kernel `rtc-ds1307.c` century handling.
- "rtcwake -m mem -s 30" — correct invocation.
- BCD vs binary conversion code is correct.

### Knowledge prerequisites missing
- "BCD" needs one-sentence intro on first use (0x23 = decimal 23, not 35).
- "OSF (Oscillator Stop Flag)" — explain its meaning: latched when the oscillator stopped, indicating possible time corruption.
- Suspend-to-RAM concept not introduced; cross-ref Ch 51B.

### Other
- Lab item 3 (battery hot-swap) is great practical knowledge.
- §117.4 timezone discussion — recommend explicitly that for embedded products in cross-timezone use, UTC + chrony is the only sane choice; "local time in /etc/adjtime" is a deprecated quirk.
- §117.5 `alarm.time.tm_min += 5; if (...) tm_min -= 60, tm_hour++` — naïve. Doesn't handle hour overflow into next day, month, year. Better: use `mktime()` and `localtime_r()`. Worth a footnote since readers may copy-paste.
- The chapter is a strong closing for Part VII; the "wake every hour, suspend in between" pattern ties together Ch 51B + Ch 116 + Ch 117 nicely.


---

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




---


