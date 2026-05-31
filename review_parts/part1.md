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
