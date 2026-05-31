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

