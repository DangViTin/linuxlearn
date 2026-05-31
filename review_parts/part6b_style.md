# Part VIb — Style/ESL Review

## Cross-cutting patterns

- **Em-dash chaining** dominates almost every chapter intro and "Focus" line. The pattern "X — Y — Z" appears so often it has become invisible to the author but is jarring for an ESL reader. Replace with periods or commas.
- **"Not X — but Y" / "isn't X. It's Y"** sledgehammer used in chapter intros (esp. Ch 52A, Ch 53). Just state what it is.
- **Triplet rhythms** in "Focus:" lines ("what, why, how", "request, configure, prepare, submit"). Cut one.
- **Buzzwords cluster**: "seamless" (Ch 53), "deterministic" (Ch 52A — used correctly here but reused as marketing), "robust", "critical/crucial" (Ch 51A, 52A), "invaluable" (Ch 51B). Drop or replace with concrete numbers.
- **Royal "we'll / let's"** in section transitions and "Next chapter" boxes. Fine in moderation but appears in every chapter's closing line — vary or drop.
- **Hedging interjections** ("Worth its weight in gold", "Subtle.", "Better:") litter the text. Strip; the engineer reader does not need editorial nudges.
- **Bullet-list-as-prose**: short clauses bolded with "**Term.** Sentence." Used so consistently in Pitfalls/Tradeoffs sections that it becomes monotone. Mix in full sentences.
- **Long compound sentences** with three to four clauses joined by em-dashes and parentheticals are the dominant readability problem for ESL. Almost every paragraph has one.

## Ch51 — DMA

### AI wording / sledgehammer / buzzwords

- > "the CPU is a terrible bulk-data mover. Sustained 10 Mbps of SPI traffic eats a chunk of i.MX6ULL's CPU when each byte requires an IRQ; the SDMA controller does it at zero CPU cost."
  - Rewrite: "The CPU is bad at bulk data moves. At 10 Mbps SPI, one IRQ per byte burns a large fraction of the i.MX6ULL CPU. SDMA does the same job at zero CPU cost."
- > "turns 'this driver is incomprehensible' into 'this driver is a textbook dmaengine consumer.'"
  - Rewrite: "Once you know the consumer API, most DMA-using drivers read the same way."
- > "the four-step ritual"
  - Rewrite: "the four standard steps" (used four times across the chapter; "ritual" is decorative)
- > "Once you can mentally walk those four steps for any peripheral, every DMA driver in the kernel looks like a variation on one theme."
  - Rewrite: "Once you know these four steps, most DMA drivers look the same."
- > "the trap that catches everyone"
  - Rewrite: "A common bug:" (the "trap" framing is dramatic)
- > "the cache dance"
  - Rewrite: "the cache flush/invalidate sequence"

### ESL readability

- > "Setup cost. Configuring an SDMA transfer costs ~1 µs. For 4-byte transfers, PIO is faster."
  - Rewrite: keep as is — already short. But the surrounding `Memory pinning` bullet has too much packed in. Split: "DMA needs physically-contiguous, cache-coherent buffers. Use `dma_alloc_coherent` (slower, smaller pool) or `dma_map_single` (faster, manages cache). The MMU/cache material from Ch 4 matters here."
- > "you populate a buffer in user-space, give the kernel pointer to your driver, your driver DMAs from it — and DMA reads stale data because the CPU's recent writes are still in L1 cache."
  - Rewrite: "User-space fills a buffer. The driver hands the kernel pointer to DMA. DMA reads stale data — the CPU's recent writes are still in L1 cache."
- > "the kernel handles this for you *if you use the APIs correctly*. If you cast a pointer to `dma_addr_t` and skip the map call, you'll get sporadic data corruption that depends on whether the cache line happened to be evicted between operations."
  - Rewrite: "The kernel handles cache coherency for you, but only if you use the APIs. If you cast a pointer to `dma_addr_t` and skip `dma_map_*`, you get random data corruption. Whether it appears depends on whether the cache line was evicted between operations."

### Needs more explanation

- §51.3 "Step 3 — Prepare a descriptor": scatter-gather gets one line. Add 10 lines: what `struct scatterlist` is, why peripherals stream into multiple discontiguous pages (user-space buffers crossing page boundaries), the `sg_init_table` / `sg_set_buf` / `dma_map_sg` flow, and what the engine actually does (chain of descriptors, one per SG entry). This is the hard part of the dmaengine API and the chapter waves at it.
- §51.5 "Cyclic transfers": mention the relationship between `period` count, total ring size, and the residue API (`dmaengine_tx_status` returning the in-period offset) — that's how ALSA computes the hardware pointer.
- §51.7 "Cache coherency": the explanation conflates ARMv7 cache ops with the Linux DMA API. Add a sentence: "ARMv7 has separate inner/outer caches (PL310 L2). The DMA API takes care of both. `dma_alloc_coherent` returns memory that's mapped non-cacheable in the page tables, so no flushes are ever needed."
- A short paragraph on **dma-buf** is missing entirely. Even if not covered here, name it and forward-reference where it lives (camera / DRM zero-copy). The reader will hit it in Ch 54B and have no anchor.

---

## Ch51A — Watchdog

### AI wording / sledgehammer / buzzwords

- > "every product shipped to a customer needs this."
  - Rewrite: "Most shipping products need this." (avoid absolute marketing tone)
- > "Watchdog handling is the difference between 'this product is reliable' and 'this product is not.'"
  - Rewrite: drop the sentence. The previous line already made the point.
- > "Worth its weight in gold for debugging field failures."
  - Rewrite: "Very useful for debugging field failures." or drop.
- > "**Pretty short timeouts.**"
  - Rewrite: "**Short timeouts.**" ("Pretty" is filler.)
- > "Layered watchdog: hardware → systemd → application. Each layer protects the layer above."
  - Rewrite: leave the diagram, but the trailing "Each layer protects the layer above" is filler — the diagram says it.

### ESL readability

- > "A kernel oops on an unrelated subsystem, a deadlock in your driver, a CPU stuck in a tight infinite loop in user-space — without a watchdog, that's a brick that needs a power-cycle by hand."
  - Rewrite: "A kernel oops in some other subsystem. A deadlock in your driver. A user-space process stuck in an infinite loop. Without a watchdog, the device becomes a brick that needs a manual power-cycle."
- > "if `CONFIG_WATCHDOG_NOWAYOUT=y` (default on most distros), once `/dev/watchdog` is opened, it cannot be safely closed — closing without the magic 'V' character first leaves it armed; closing with 'V' disables it."
  - Rewrite: "With `CONFIG_WATCHDOG_NOWAYOUT=y` (the usual default), once `/dev/watchdog` is opened, it cannot be safely closed. To disable it on close, write a `'V'` first. Closing without the `'V'` leaves it armed."

### Needs more explanation

- §51A.5 "boot-reason register": SRC_SRSR is named but not decoded. Show the actual bit layout (POR, WDOG, WARM, JTAG) and how to read it from user-space (`cat /sys/...` path) so the reader can actually use it.
- §51A.6 "Writing a watchdog driver" feels too thin given the chapter's depth requirement. Add: what the core does for you (the `dev_t` allocation, the `/dev/watchdogN` node, the IOCTL multiplex), and *why* you usually do not need to write one (because chips are usually wired through GPIO + a kthread, see external IC pattern).
- pstore/ramoops: name `pstore_blk` and `pstore-zone`. Reader hitting eMMC-only boards needs to know there is a path without preserved RAM.

---

## Ch51B — Power management

### AI wording / sledgehammer / buzzwords

- > "Runtime PM is the kernel's autonomic nervous system."
  - Rewrite: "Runtime PM is the kernel's automatic per-device idle/active state machine." (the biology metaphor is a tell.)
- > "DVFS — the 'voltage before frequency' / 'frequency before voltage' dance"
  - Rewrite: "DVFS — when raising clock, the regulator goes up first, then the clock; when lowering, the reverse."
- > "`powertop` is invaluable for finding which userspace process is keeping the CPU awake."
  - Rewrite: "`powertop` shows which userspace process is keeping the CPU awake."
- > "Each step is small (~mA). Together they go from '1 Ah lasts 4 hours' to '1 Ah lasts 4 days.'"
  - Rewrite: "Each step saves a few mA. Together they take a 1 Ah cell from 4 hours to 4 days." (the quoted-string framing is theatrical.)
- > "for any battery-powered product, this is half the engineering work."
  - Rewrite: "On battery-powered products, PM tuning is a large fraction of the work."

### ESL readability

- > "Each device declares idle and active states; the framework reference-counts usage and runs `runtime_suspend` / `runtime_resume` callbacks when the count crosses zero."
  - Rewrite: "Each device has an idle and an active state. The framework counts users with a refcount. When the refcount hits zero it calls `runtime_suspend`. When it goes from zero to one it calls `runtime_resume`."
- > "the kernel calls system-suspend callbacks during `echo mem > /sys/power/state` and runtime-suspend callbacks autonomously."
  - Rewrite: "System-suspend callbacks run when user-space writes `mem` to `/sys/power/state`. Runtime-suspend callbacks run automatically when the device goes idle."
- > "If `cpu-supply` is wrong, raising the frequency before voltage stabilises = unreliable execution."
  - Rewrite: "If `cpu-supply` is wrong, the kernel may raise the clock before voltage settles. Execution becomes unreliable."

### Needs more explanation

- §51B.1 "Runtime PM" — runtime PM has subtle interaction with **system suspend**, parent/child device PM, and `dev_pm_domain`. Add a few lines on: parent must be active before child can resume; PM domains (genpd) on i.MX gate whole IP blocks; what "no_callbacks" devices mean.
- §51B.3 "System sleep" — add a paragraph on the difference between `suspend`, `suspend_late`, `suspend_noirq` callbacks. This is the part of system PM that bites everyone: ordering across the device tree matters, and the three callback phases are exactly that ordering.
- §51B.2 DVFS: the OPP table is shown but the **regulator coupling** is not explained. Mention that on i.MX6ULL the ANATOP arm regulator and the SOC/PU regulators are coupled, and getting that wrong is the most common DVFS bring-up bug.
- Missing entirely: **CPU idle** (`cpuidle`) — distinct from cpufreq. WFI vs deeper idle states. On i.MX6ULL there are only WAIT and STOP idle modes, but the reader should know they exist and how the framework picks them.

---

## Ch52 — Network (FEC + KSZ8081)

### AI wording / sledgehammer / buzzwords

- > "Ethernet is the most-debugged peripheral on any embedded board."
  - Rewrite: "Ethernet is one of the most-debugged peripherals on any embedded board." (the absolute is unprovable and reads like marketing.)
- > "the full anatomy of 'Linux has eth0 working.'"
  - Rewrite: "the full path from MAC to `eth0`."
- > "Get the four layers right and packets flow."
  - Rewrite: drop (sledgehammer). The diagram already says it.
- > "**This is the biggest bring-up gotcha**"
  - Rewrite: "This is the most common bring-up bug on i.MX6ULL boards."
- > "Half the 'FEC not working' reports turn out to be a bent CAT5e or a dead RJ45 jack."
  - Rewrite: keep — this one is funny and accurate.

### ESL readability

- > "i.MX6ULL has **two FEC instances**, FEC1 and FEC2. Some boards wire both (giving dual Ethernet). Point Atom MINI typically has one wired, ALPHA may have two."
  - Rewrite: already short and clear. No change.
- > "NAPI batches RX interrupts to reduce the IRQ rate at high packet rates — instead of one IRQ per packet, the driver gets one IRQ, then polls until the RX queue is empty, then re-arms IRQ."
  - Rewrite: "NAPI batches RX interrupts. The driver gets one IRQ, then polls until the RX queue is empty, then re-arms the IRQ. This avoids one IRQ per packet at high rates."
- > "Wrong direction = no link, no MDIO communication, mysterious failures."
  - Rewrite: "If the clock direction is wrong, you get no link, no MDIO communication, and confusing symptoms."

### Needs more explanation

- §52.3 "netdev framework" — `sk_buff` is the central object and is not mentioned. Add 10 lines: an `sk_buff` is what `ndo_start_xmit` receives and what NAPI hands up the stack; data is in a headroom/data/tailroom layout; skb_pull/skb_push manipulate headers. Without this, the reader cannot read `fec_main.c` meaningfully.
- §52.4 "phylib" — explain the **link state machine**. The PHY library has its own kthread (`phy_state_machine`) that polls PHY status registers and invokes the MAC driver's `adjust_link` callback. The reader should know why "no link" sometimes means "phylib has not polled yet."
- §52.6 "RMII pinmux": the `0x1b0b0` pad value is repeated 9 times with no decode. Spend 5 lines decoding the conf_reg bits (PUS, PUE, HYS, SPEED, DSE, SRE) so the reader knows what they are setting.
- Missing: a quick word on **`xdp`** and where it sits relative to NAPI. Even if not implemented for FEC, name it; the reader will encounter it.

---

## Ch52A — PREEMPT_RT

### AI wording / sledgehammer / buzzwords

- > "Many shipping industrial products (CNCs, robotic arms, real-time camera ML inference) run PREEMPT_RT Linux today."
  - Rewrite: "Many industrial products run PREEMPT_RT Linux today — CNCs, robotic arms, real-time camera inference."
- > "Internalising what 'bounded' really means — and what defeats it — is the whole game."
  - Rewrite: "What 'bounded' actually means, and what breaks it, is the main thing to learn."
- > "The 30× improvement in the long tail makes hard-RT applications viable."
  - Rewrite: "A 30× drop in the worst case makes hard-RT applications viable."
- > "This single feature avoids the Mars Pathfinder bug."
  - Rewrite: keep — this is genuinely informative. Could be expanded with two lines on what the Pathfinder bug actually was, since ESL readers will not know.
- > "PREEMPT_RT alone isn't enough. Tune:"
  - Rewrite: "PREEMPT_RT alone is not enough. You also need to tune the kernel, the cmdline, and userspace:" (the colon-as-section-header is a tic that appears in several chapters.)

### ESL readability

- > "A standard Linux kernel might run your callback in 100 µs on average — but every 1000th time, it takes 5 ms because some other kernel code held a non-preemptible lock."
  - Rewrite: "On a standard kernel, your callback runs in about 100 µs on average. But every 1000th time, it takes 5 ms because some other kernel code held a non-preemptible lock."
- > "Standard Linux runs IRQ handlers in IRQ context — atomic, fast, but blocking other IRQs of the same priority. PREEMPT_RT runs *all* IRQ handlers as kernel threads, schedulable like any other thread."
  - Rewrite: "Standard Linux runs IRQ handlers in IRQ context: atomic, fast, but blocking other IRQs at the same priority. PREEMPT_RT runs every IRQ handler as a kernel thread. The scheduler treats them like any other thread."
- > "Without priority inheritance: low-priority task A holds mutex M. High-priority task B wants M, blocks. Medium-priority task C runs (preempts A). B is now blocked indefinitely by C — *priority inversion*."
  - Rewrite: "Without priority inheritance, priority inversion happens. Low-priority task A holds mutex M. High-priority task B wants M and blocks. Medium-priority task C runs and preempts A. B now waits behind C indefinitely."

### Needs more explanation

- §52A.2.1 "Preemptible spinlocks" — the conversion from `spinlock_t` to sleeping lock is the most important RT idea and only gets two sentences. Add: this is why some code is wrong under RT (calling `spin_lock` then `kmalloc(GFP_ATOMIC)` is fine on mainline but the lock is sleepable on RT, so the rules for what you can do inside it change). The reader from MCU-RTOS world needs this contrast.
- §52A.4 `cyclictest`: explain *what cyclictest actually measures* — it is the gap between the `nanosleep(target)` expected wake time and the moment the user-space thread actually runs. So the number is (kernel timer jitter) + (IRQ-to-thread wake) + (scheduler latency). Many readers think it measures hardware IRQ latency directly.
- Missing entirely: **what threaded IRQs look like to a driver writer**. Two paragraphs on `IRQF_ONESHOT`, the primary/threaded split, and `IRQF_NO_AUTOEN`. This is the day-to-day mechanic of writing RT-safe drivers.
- The relationship to **`runtime PM`** (Ch 51B): runtime suspend can add 100+ µs to wake-from-idle. A real RT chapter should at least name this trade-off.

---

## Ch53 — Sound (ALSA / ASoC)

### AI wording / sledgehammer / buzzwords

- > "audio is one of the most stressful real-time loops in any system."
  - Rewrite: "audio is one of the tightest real-time loops in any embedded system."
- > "the most architecturally complex subsystem in the kernel"
  - Rewrite: "one of the most layered subsystems in the kernel"
- > "a magnificent hack" (in Ch 54 about panel-simple)
  - Rewrite: "a useful shortcut" (the "magnificent hack" framing is cute but not informative.)
- > "as long as user-space writes fast enough that the buffer doesn't underrun, sound plays seamlessly."
  - Rewrite: "if user-space writes fast enough to avoid an underrun, playback continues without glitches."
- > "Once you grok this binding pattern, every ASoC driver in the kernel becomes legible."
  - Rewrite: "Once you understand this binding, ASoC drivers become readable."

### ESL readability

- > "ASoC splits an audio chain into three driver pieces: **CPU-DAI** (the SoC's I²S/SAI controller), **codec** (the analog chip, e.g., WM8960 or SGTL5000), and **machine** (the glue that wires them together for one specific board)."
  - Rewrite: "ASoC splits an audio chain into three drivers. The **CPU-DAI** is the SoC's I²S/SAI controller. The **codec** is the analog chip (WM8960, SGTL5000). The **machine driver** wires them together for one specific board."
- > "Every period (typically 1024 samples = ~21 ms at 48 kHz), the DMA fires an IRQ; ALSA refills that period from the user-space buffer; the cycle continues."
  - Rewrite: "DMA fires an IRQ every period (typically 1024 samples, about 21 ms at 48 kHz). ALSA refills that period from the user-space buffer. The cycle continues."

### Needs more explanation

- §53.1 should at least name **DAPM** (Dynamic Audio Power Management) as a concept before §53.7 references it. DAPM is the second-hardest ASoC concept (after the three-driver split) and is currently introduced sideways via the DT routing example. Two paragraphs: each codec block (HP_L, MIC, etc.) is a DAPM widget; the routing graph decides which blocks are powered; user-space mixer changes propagate through the graph and gate power.
- §53.4 "Writing a machine driver": the example does not show the `dai_fmt` constants in detail. ESL reader sees `SND_SOC_DAIFMT_CBS_CFS` and has no chance — decode: "Codec is Bit-clock Slave, Frame-clock Slave (CBS_CFS). The SoC is master."
- The cyclic DMA path is the same as Ch 51's cyclic transfer, but the **residue-based hardware-pointer** computation that ALSA does is not shown. This is the bridge between Ch 51.5 and Ch 53; a one-paragraph diagram would close the loop.
- Missing: **ALSA's PCM substream states** (OPEN → SETUP → PREPARED → RUNNING → XRUN → DRAINING). The pcm_ops callbacks fire on these transitions; without the state machine the callbacks are random functions.

---

## Ch54 — LCD / DRM

### AI wording / sledgehammer / buzzwords

- > "panel-simple + DT timings == working display"
  - Rewrite: "For most boards, panel-simple plus correct DT timings is enough." (the `==` is cute but reads as code where the prose should not.)
- > "is a magnificent hack"
  - Rewrite: "is a database-driven panel driver" (matter-of-fact)
- > "**Pixel clock too high.** PCLK > ~80 MHz on i.MX6ULL LCDIF → silent failure."
  - Rewrite: "**Pixel clock too high.** Above about 80 MHz the LCDIF gives no output."
- > "Always test with daylight first."
  - Rewrite: "Always check in good ambient light first." (slight ESL clarity — "test with daylight" is unusual English.)
- > "drm.debug=15 on kernel cmdline floods dmesg with DRM info; invaluable for chasing modeset issues."
  - Rewrite: "`drm.debug=15` on the kernel cmdline fills dmesg with DRM trace output. Very useful for modeset bugs."

### ESL readability

- > "For embedded HMI with one panel and a single fullscreen Qt app, fbdev still works. For anything with multiple outputs, GPU acceleration, or Wayland, DRM is the only option."
  - Rewrite: clear already; no change.
- > "**Both are present** on modern kernels; fbdev is emulated on top of DRM via `fbdev_emulation`. Your fullscreen Qt app sees `/dev/fb0`; under the hood DRM is doing the work."
  - Rewrite: "Both APIs are present on modern kernels. fbdev is emulated on top of DRM (`fbdev_emulation`). A fullscreen Qt app opens `/dev/fb0`, but DRM is doing the work underneath."
- > "Off-by-one in front-porch is the most common error."
  - Rewrite: keep — already crisp.

### Needs more explanation

- §54.1 (fbdev vs DRM table) — the four central DRM objects (**CRTC, plane, encoder, connector**) appear in the table but are not defined. For an ESL reader coming from MCU framebuffer drivers, this is the single biggest leap. One short section is essential:
  - CRTC = the scan-out engine (the LCDIF instance).
  - plane = a layer that the CRTC composites (overlay, cursor, primary).
  - encoder = the bridge between pixel data and a physical interface (DPI, HDMI, MIPI).
  - connector = the physical output port and its EDID/state.
  Without this the entire chapter is opaque.
- §54.3 — `panel-timing` is shown with 12 fields and no diagram. Add a small ASCII diagram of a video frame showing where each porch / sync lives. The MCU reader has seen this on a CRT controller but the naming differs.
- §54.5 "DRM style" introduces `modetest` then says "atomic mode-setting" only in the table. Add a paragraph: the atomic ioctl bundles all CRTC + plane + connector state into one ioctl that either all succeeds or all fails. This is the API that DRM clients (Weston, Qt EGLFS) actually use; `modetest` exposes it through `-P`/`-s`.
- **dma-buf** is absent again. DRM is where dma-buf truly matters: any zero-copy from V4L2 to DRM (Ch 54B → Ch 54) goes through dma-buf. Either name it here or in Ch 54B and cross-reference.

---

## Ch54A — MTD / UBI

### AI wording / sledgehammer / buzzwords

- > "raw NAND is everywhere in industrial embedded"
  - Rewrite: "Raw NAND is common in industrial embedded."
- > "Used by every shipping NAND-based product on Linux."
  - Rewrite: drop. The previous sentence makes the point.
- > "**Don't confuse them**; each solves a distinct problem."
  - Rewrite: "Keep them separate in your head — each solves a different problem."
- > "**Wear test.** Write a script that writes a 1 MB file in a loop"
  - Rewrite: keep, but "Wear test" as section header is fine.

### ESL readability

- > "But NAND is *not* a block device: it has erase blocks (~128 KB), pages (~2 KB), bad-blocks that grow over the lifetime, and limited erase cycles."
  - Rewrite: "But NAND is not a block device. It has erase blocks (about 128 KB) and pages (about 2 KB). Bad blocks appear over the device's lifetime. Erase cycles are limited."
- > "UBIFS atop a block layer that's atop NAND is double-translation."
  - Rewrite: "If you put a block-device emulation on top of NAND, then a filesystem on top of that, you pay for two translation layers."

### Needs more explanation

- §54A.1 should mention **MTD-on-SPI-NOR** (m25p80) as the other common MTD use case. The chapter is NAND-only by title, but readers with SPI-NOR boot devices need to know MTD is the same framework.
- §54A.4 "UBI on top" — UBI's **fastmap** feature is a real win on large NANDs (cuts attach time from seconds to ~100 ms) and is missing. One paragraph: `ubi.fm_autoconvert=1` or DT `linux,ubi-fastmap`.
- §54A.6 "Wear levelling" — the chapter does not explain **why** UBI works the way it does. Two paragraphs on the algorithm: UBI keeps each LEB's erase counter; when free LEBs are needed, it picks ones with low counters; periodically it migrates static data off low-counter PEBs to even things out. Without this the `ubinfo` output is just numbers.
- Missing: **UBI block driver** (`ubiblock`) for read-only mounting of squashfs over UBI — a common pattern for /usr on industrial products. Worth a short subsection.
- Power-loss safety is asserted ("UBIFS handles this well") but not explained. Add a sentence: UBIFS uses a journal and the UBI layer guarantees that an LEB is either erased or fully written; partial writes are detected and discarded on attach.

---

## Ch54B — V4L2 / GStreamer

### AI wording / sledgehammer / buzzwords

- > "Mastering the pipeline mental model unlocks the entire imaging stack."
  - Rewrite: "Once the pipeline model clicks, the rest of the imaging stack reads easily."
- > "Everything else is image processing."
  - Rewrite: "After that, the rest is image processing."
- > "100 lines for a complete capture loop. Tedious but predictable."
  - Rewrite: keep — already plain.
- > "GStreamer 30 seconds"
  - Rewrite: "GStreamer in 30 seconds" (small ESL correction)
- > "Auto-exposure / auto-white-balance work surprisingly well for general use."
  - Rewrite: "Auto-exposure and auto-white-balance are good enough for general use."

### ESL readability

- > "A V4L2 *device* is what user-space opens (`/dev/video0`). It's connected to *sub-devices* — the sensor (OV5640) and the CSI bridge (i.MX CSI/ISI) — via a **media graph**. The user-space configures both the format (resolution, pixelformat) at the video device and the format at each subdev."
  - Rewrite: "A V4L2 *device* is what user-space opens (`/dev/video0`). It connects to *sub-devices* — the sensor and the CSI bridge — through a **media graph**. User-space sets the format on both the video device and on each subdev."
- > "i.MX6ULL has no GPU/VPU, so video encoding is software (slow). Useful up to ~5–10 fps at QVGA. For higher framerates and resolutions you need a different SoC."
  - Rewrite: clear; no change.
- > "5 MP at 30 fps requires ~140 MB/s memory bandwidth — pushes i.MX6ULL hard."
  - Rewrite: "5 MP at 30 fps needs about 140 MB/s of memory bandwidth. This is close to the i.MX6ULL's practical limit."

### Needs more explanation

- §54B.1 — the media graph is named but not shown. Add the actual `media-ctl -p` output (or at least a sketch of one) with the link directions and the active/inactive markers. The reader cannot understand `media-ctl --set-v4l2` without seeing what the graph looks like.
- §54B.3 — the `videobuf2` (vb2) layer behind V4L2's buffer ioctls deserves a paragraph. vb2 is the kernel-side machinery that backs `REQBUFS` / `QBUF` / `DQBUF` with three queue types (MMAP, USERPTR, DMABUF). This is where **dma-buf** finally appears in the book — name it here and forward to where it crosses into DRM.
- §54B.5 — the **control framework** (`v4l2_ctrl`) deserves a short subsection. Sensors expose dozens of controls; the framework provides per-control min/max/step, change notifications, and a "control event" subscription mechanism. Without this paragraph the reader hits `v4l2-ctl --list-ctrls` and has no idea what's behind it.
- The i.MX6ULL has **CSI parallel** but the chapter mentions MIPI lanes (`data-lanes = <1>`) which is wrong for parallel CSI (parallel uses an 8-bit bus, not lanes). Either the DT snippet is for a MIPI-CSI variant or it is a bug. Worth a clarifying note: "On i.MX6ULL, CSI is 8-bit parallel; the `data-lanes` syntax is only valid if you have a CSI-2 bridge."

---

## Ch55 — USB gadget

### AI wording / sledgehammer / buzzwords

- > "the modern way to compose a USB gadget"
  - Rewrite: "The current way to compose a USB gadget." (lower-key)
- > "every Android phone, Raspberry Pi Zero in USB-Pi mode, smart-meter that exposes its data via USB-serial — all run USB gadget."
  - Rewrite: "USB gadget runs on Android phones, Raspberry Pi Zero in USB-Pi mode, smart meters that expose data over USB-serial, and many other devices."
- > "**Two gadgets bound to one UDC.** Only one bind per UDC at a time."
  - Rewrite: keep — already crisp.

### ESL readability

- > "Last line: writing the UDC name binds the gadget. Now plug a USB cable from the i.MX6ULL's OTG port to a PC; the PC sees a composite USB device with serial + Ethernet + mass storage."
  - Rewrite: "The last line binds the gadget by writing the UDC name. Plug a USB cable from the i.MX6ULL's OTG port into a PC. The PC sees a composite USB device with serial, Ethernet, and mass storage."
- > "ConfigFS is a *filesystem*: `mkdir` a function, `echo` settings into its files, then bind to a UDC. No kernel code."
  - Rewrite: short already.
- > "Windows needs an `.inf` driver hint for CDC-ACM."
  - Rewrite: "Windows needs a `.inf` driver file before it will bind to CDC-ACM."

### Needs more explanation

- §55.2 ConfigFS overview — the chapter shows the steps but does not say **why** the design is this way. One paragraph: pre-ConfigFS, every gadget composition required a kernel module (`g_serial.ko`, `g_ether.ko`); ConfigFS lets a single user-space init script change the composition at runtime. The "function" / "configuration" / "UDC" tree mirrors the actual USB device tree (one device → one or more configurations → one or more interfaces).
- §55.5 "Custom function": **FunctionFS** is named but the model is not explained. Two paragraphs: FunctionFS exposes raw endpoint files (`ep1`, `ep2`, ...) to user-space; you write descriptors into `ep0` then read/write data on the other endpoints. This is the equivalent of "raw USB device" for testing or proprietary protocols.
- Missing: **USB gadget composite vs OS Descriptors** for Windows. The chapter mentions Windows needs `.inf` but does not mention that gadgets can ship OS Descriptors (MS_OS_20) inside the device itself to make Windows auto-bind WinUSB — this is the modern Windows-compatible path.
- §55.1 OTG: the ID-pin detection mechanism (the extcon framework, `usb_role_switch`) is missing. Even a one-line forward reference would help.

---

## Ch55A — Kernel timers / hrtimers

### AI wording / sledgehammer / buzzwords

- > "They're foundational to many driver patterns: timeouts, periodic polling, throttling, scheduled deferred work."
  - Rewrite: "Common driver patterns use them: timeouts, periodic polling, rate limiting, deferred work."
- > "Pick the right one and the API choices follow."
  - Rewrite: drop. The next section explains both APIs anyway.
- > "Drifts less than re-arming manually."
  - Rewrite: "It drifts less than recomputing `now + 1ms` each time."

### ESL readability

- > "`mod_timer`: re-schedules an existing timer to a new expiry; if not active, arms it."
  - Rewrite: "`mod_timer`: re-schedules a running timer to a new expiry. If the timer is not active, it arms it."
- > "Each press triggers an IRQ, which re-arms the timer. If the button bounces, every bounce resets the timer; only after 20 ms of silence does the timer fire and report the press."
  - Rewrite: "Each press triggers an IRQ that re-arms the timer. If the button bounces, every bounce resets the timer. Only after 20 ms of silence does the timer fire and report the press."
- > "Granularity: nanoseconds, limited by hardware (i.MX6ULL's GPT has ~30 ns resolution)."
  - Rewrite: clear; no change.

### Needs more explanation

- The chapter does not explain **what runs the callback**. timer_list runs in the timer softirq (`TIMER_SOFTIRQ`); hrtimer can run in either softirq or hardirq context depending on the mode (`HRTIMER_MODE_REL_HARD` etc.). For RT users this is the key difference. One paragraph.
- §55A.2 hrtimer modes: `HRTIMER_MODE_REL`, `_ABS`, `_PINNED`, `_HARD` — the chapter only shows `_REL`. ESL reader will hit driver code with `_PINNED` and wonder what it does (pin to the CPU it was started on, useful for per-CPU timers).
- §55A.3 workqueue table is fine but `kthread_worker` (a private workqueue for one kthread) is the RT-preferred alternative and not mentioned. RT drivers prefer kthread_worker because regular workqueue can starve.
- The relationship to **NAPI** (Ch 52) is implicit and not stated: NAPI is also a softirq context, sharing the same constraints as timer callbacks. Cross-reference would help.

---

## Ch55B — Async / SIGIO

### AI wording / sledgehammer / buzzwords

- > "Linux's input layer doesn't use it (poll/epoll is preferred), but legacy POSIX-style apps and some custom devices do."
  - Rewrite: clear; no change.
- > "SIGIO is a 'good to know it exists' mechanism more than a 'use this often' mechanism."
  - Rewrite: "SIGIO is worth knowing about, but rarely the right tool today."
- > "`Documentation/admin-guide/cgroup-v2.rst` (no, just kidding) — the relevant kernel docs are sparse"
  - Rewrite: drop the joke. "The relevant kernel docs are sparse — see LDD3 Chapter 6 and `man 2 fcntl` instead." (The parenthetical is a Claude-ism.)

### ESL readability

- > "Three steps: install signal handler → `F_SETOWN` declares who gets the signal → `F_SETFL | O_ASYNC` enables it."
  - Rewrite: "Three steps. First, install the signal handler. Second, `F_SETOWN` tells the kernel which process gets the signal. Third, `F_SETFL | O_ASYNC` enables delivery."
- > "User-space must drain whatever was queued, not just respond to 'one event.'"
  - Rewrite: "User-space must drain everything that was queued, not just handle one event."

### Needs more explanation

- The chapter is short and that is fine, but it should at least name the **modern alternatives one more time at the end** with a one-line "use poll/epoll/io_uring instead" verdict so an ESL reader does not walk away thinking SIGIO is a good default.
- `F_SETSIG` is referenced in Pitfalls but never explained. Either show a code snippet or drop the reference.
- Missing: **how SIGIO interacts with threads**. `F_SETOWN` to a pid signals the process; signaling a specific thread requires `F_SETOWN_EX`. This bites people moving from single-threaded prototypes.

---

## Ch55C — CAN / FlexCAN

### AI wording / sledgehammer / buzzwords

- > "Linux's elegant abstraction"
  - Rewrite: "Linux's clean abstraction" or just "Linux's abstraction." ("Elegant" is a tell.)
- > "**CAN-as-network-device**"
  - Rewrite: "CAN looks like a network device."
- > "Indispensable."
  - Rewrite: "Required." or drop. (One-word emphatic sentences are a Claude pattern.)
- > "the most common embedded case"
  - Rewrite: "a common embedded case"

### ESL readability

- > "The kernel filters in software (or hardware where possible — FlexCAN has MB filtering). High-throughput receivers should always set filters; otherwise every frame on the bus arrives at every socket."
  - Rewrite: "The kernel filters in software, or in hardware where the controller supports it. FlexCAN has message-buffer (MB) filtering. High-throughput receivers should always set filters. Otherwise, every frame on the bus is delivered to every socket."
- > "Without 60 Ω at each end, signal integrity collapses. Single-node bench setups: just stick a single 120 Ω resistor across CAN_H/CAN_L and live with reduced robustness."
  - Rewrite: "Without 120 Ω termination at each end of the bus (60 Ω total), signal integrity collapses. For a single-node bench setup, put one 120 Ω resistor across CAN_H/CAN_L. Robustness is lower but it works." (Original conflates 60 Ω each-end with 60 Ω total — this is a *technical* error worth flagging: standard CAN termination is 120 Ω at each end, which forms 60 Ω parallel as the bus impedance.)

### Needs more explanation

- §55C.3 "Bringing up the interface" — the **bit-timing** segment registers (`tq`, `prop_seg`, `phase_seg1`, `phase_seg2`, `sjw`, `sample-point`) are skipped entirely. For real CAN bring-up these matter when you cannot use the default bitrate calculator. One paragraph showing how `ip link set canX type can bitrate 500000 sample-point 0.875` works, and a sentence on why CiA recommends 87.5 %.
- §55C.4 — **CAN-FD** is in DT and in the cmdline but not in the C example. Add a short C snippet using `canfd_frame` and the `CAN_RAW_FD_FRAMES` socket option.
- §55C.5 — the **BCM (Broadcast Manager)** is named in one line and never demonstrated. This is the one CAN-specific socket feature that *no other socket family has* and that is genuinely powerful (kernel-side cyclic TX, content-change RX filter). Two paragraphs with a code sketch.
- **Error handling** is the practical hard part of CAN drivers. The chapter mentions `CAN_ERR_BUSOFF` but does not explain TEC/REC (Transmit/Receive Error Counters) and the warning/passive/bus-off transitions. One small diagram of the state machine.

---

## Ch55D — Block device drivers

### AI wording / sledgehammer / buzzwords

- > "Userspace's `read(fd, ..., 4096)` becomes one or more `struct bio`s queued to a `gendisk`."
  - Rewrite: "A user-space `read(fd, ..., 4096)` becomes one or more `struct bio`s submitted to a `gendisk`."
- > "A real RAM-backed block device, mountable like any disk."
  - Rewrite: drop the editorial closing line. The code listing already showed what it did.
- > "The minimal ramdisk skips many features."
  - Rewrite: "The ramdisk above is minimal. Production block drivers add:"

### ESL readability

- > "Drivers can either process bio-at-a-time or convert to hardware-native request structures."
  - Rewrite: "Drivers can process bios one at a time, or convert them to hardware-native request structures."
- > "Modern kernels require sector-aligned bios; smaller-than-sector requests get split."
  - Rewrite: "Modern kernels require sector-aligned bios. Requests smaller than a sector get split."
- > "Block layer expects fast queue_rq returns. Defer long work to a workqueue."
  - Rewrite: "`queue_rq` is expected to return quickly. Defer long work to a workqueue."

### Needs more explanation

- §55D.1 The path from `read()` — `pagecache` is invisible in the diagram. For an MCU engineer this is a major gap: most reads do not reach the block layer because page cache catches them. One paragraph: VFS first checks page cache; on miss, the filesystem builds a bio; the bio goes through blk-mq.
- §55D.2 The ramdisk example uses `blk_mq_alloc_disk` which is the modern (5.14+) API. The chapter should say so and contrast with the pre-5.14 `blk_alloc_queue` + `alloc_disk` pattern that older code still uses, so reading older drivers in the kernel does not confuse the reader.
- The **request lifecycle** is missing: `queue_rq` → `blk_mq_start_request` → driver does work → `blk_mq_end_request` (or `blk_mq_requeue_request` on transient errors). The chapter shows the calls but does not name the lifecycle states.
- Missing entirely: **`bio_chain` and `bio_split`** — how the kernel handles bios that exceed the driver's max transfer size, and how zoned and DM (device-mapper) layers stack on top. Even a forward reference would help.

---

## Ch55E — WiFi / wpa_supplicant

### AI wording / sledgehammer / buzzwords

- > "Get any layer wrong and 'nothing works.'"
  - Rewrite: "If any layer is wrong, nothing works."
- > "from a multi-day mystery into a methodical bring-up."
  - Rewrite: "from a multi-day debug into a methodical bring-up."
- > "Most BCM/Realtek modules need a 32 KHz LPO clock; if not wired/provided, sleep modes fail or chip is unreliable."
  - Rewrite: "Most BCM and Realtek modules need a 32 kHz LPO clock. Without it, sleep modes fail and the chip becomes unreliable."

### ESL readability

- > "Without the nvram, the driver probes but WiFi doesn't enumerate channels correctly (or at all). The nvram is *per-board* — copying from a different board's image gives wrong antenna config, wrong regulatory, broken behavior. Always get the matching nvram from your board vendor."
  - Rewrite: "Without the nvram, the driver probes but channels do not enumerate correctly (or at all). The nvram is per-board. Copying from another board gives the wrong antenna config, the wrong regulatory domain, and broken behavior. Always get the matching nvram from your board vendor."
- > "Three things:"
  - Rewrite: "Three things to notice:" (standalone "Three things:" is a Claude pattern.)

### Needs more explanation

- §55E.1 The stack — there is no discussion of **firmware-loading mechanics**. The reader sees "firmware blob loaded" but does not know that `request_firmware()` walks `/lib/firmware/` and that systemd/udev hooks can re-trigger probe after firmware lands. This is a real source of bring-up bugs (firmware shipped in initramfs vs rootfs).
- §55E.2 — **SDIO** itself deserves a short paragraph. The reader has not seen SDIO before. It is MMC-like with a function-based protocol. WiFi modules implement SDIO function 1 (BCM) or function 2 (others). The `wifi@1` reg matches the function number. Without this the DT snippet is opaque.
- §55E.5 — **regulatory** is one bullet in Pitfalls but is actually a separable subsystem (`CRDA` historically, `wireless-regdb` now). Worth a short subsection: the kernel sets a country code via `iw reg set XX` or via 802.11d/h beacons; this gates which channels/powers are allowed.
- Missing: **mac80211 hwsim** for development on a host without WiFi hardware. The chapter mentions it in "Going deeper" only; a sentence in the body about using it for testing wpa_supplicant configs would help.
- The **power management** angle is missing. WiFi modules have `WoWLAN` (Wake-on-WLAN), `keep-power-in-suspend` is in DT but not explained. One paragraph linking back to Ch 51B.

---

## Ch55F — Cellular modems

### AI wording / sledgehammer / buzzwords

- > "Bringing one up correctly the first time saves weeks of customer-side debugging."
  - Rewrite: "Getting the bring-up right early avoids weeks of customer-side debugging."
- > "QMI is the modern industry-standard for Linux; default to that unless you have a specific reason."
  - Rewrite: "QMI is the standard mode for Linux today. Use it unless you have a specific reason not to."
- > "Manual is fragile. ModemManager is the way."
  - Rewrite: "Manual setup is fragile. Use ModemManager when you can."
- > "PPP is slow (~10 Mbit/s max) and adds latency. Use only for old modems without USB."
  - Rewrite: keep — already plain.

### ESL readability

- > "Bench testing failures are almost always power."
  - Rewrite: "Most bench-test failures are power-related."
- > "EC25 alone exposes 4 USB modes (RNDIS, ECM, QMI, MBIM) — pick wrong and nothing works."
  - Rewrite: "The EC25 alone exposes four USB modes: RNDIS, ECM, QMI, MBIM. The wrong choice produces no working interface."
- > "Cost: ~$0.05."
  - Rewrite: "(SMS cost is around $0.05 per message on most carriers.)"

### Needs more explanation

- §55F.2 — the **`qmi_wwan` driver** is named but the role of the kernel vs user-space is not explained. The kernel handles data-path packet shuttling between `wwan0` and the USB control endpoints; ModemManager handles the QMI session setup on `/dev/cdc-wdm0`. The reader should know which side does what.
- §55F.4 "raw-ip mode": one of the most common bring-up bugs is QMI default = `802.3-ethernet` mode but newer modems require `raw-ip`. The chapter mentions it but does not explain the *symptom* (you get an interface, get an IP via DHCP, then no traffic flows because the modem is stripping/adding Ethernet headers the kernel does not). Spell it out.
- Missing: **MBIM** is named but never demonstrated. MBIM is the USB-CDC-standardised alternative to QMI, especially for Windows-friendly modems. One paragraph.
- §55F.5 PPP — the `pppd` chat-script flow needs at least one line on what PPP actually is (HDLC framing over serial, IPCP for IP negotiation). Otherwise it looks like magic init strings.
- **eSIM / iSIM** — modern modems may not have a removable SIM. Worth a single sentence forward reference.

---

## Ch55G — Multi-touch (GT911)

### AI wording / sledgehammer / buzzwords

- > "the **ubiquitous** Goodix GT911"
  - Rewrite: "the common Goodix GT911"
- > "Old code uses MT-A (sliding-window protocol); new code uses MT-B (cleaner, easier)."
  - Rewrite: "Older code uses MT-A. Current code uses MT-B."
- > "the touch's reported value isn't linearly mapped to display pixels."
  - Rewrite: "the touch values are not linearly mapped to display pixels."

### ESL readability

- > "**`reg = <0x5d>` or `<0x14>`** — GT911 has two I²C addresses; the IRQ pin level at reset selects. 0x5d when IRQ low, 0x14 when high."
  - Rewrite: "**`reg = <0x5d>` or `<0x14>`** — the GT911 has two I²C addresses. The IRQ pin level at reset selects which: 0x5d when IRQ is low, 0x14 when IRQ is high."
- > "The order of bringing up RST and INT *during reset* selects the I²C address. The driver handles this dance."
  - Rewrite: "The driver bring-up sequence for RST and INT selects the I²C address. The driver handles this for you."

### Needs more explanation

- §55G.1 MT-B vs MT-A — `ABS_MT_TRACKING_ID` is shown in the event sequence but never explained: it is a per-contact persistent ID that user-space uses to track "the same finger" across frames. The driver assigns it; releasing the finger sets it to -1. This is the *core* of MT-B and the chapter shows it without naming it.
- Missing entirely: the **input subsystem stack** — `evdev` (/dev/input/eventN), `libinput` (the user-space library that consumes evdev), the kernel input core, the device class. The chapter sits on top of all of these without naming them. One paragraph would orient an ESL reader.
- **Palm rejection** and **touch tuning** (`touchscreen-fuzz-x/y`, `touchscreen-fuzz-pressure`) are common GT911 properties. Worth a line.
- The **rotation interaction with DRM** is missing. If the display is rotated 90 degrees via DRM, touch coordinates need the same rotation. This is currently done in libinput or in the compositor, not in DT. Forward-reference Ch 54.

---

## Ch55H — RGB-to-HDMI bridge (SiI902x)

### AI wording / sledgehammer / buzzwords

- > "Drops onto any i.MX6ULL board."
  - Rewrite: "It works on any i.MX6ULL board with LCDIF pinmux available."
- > "Three nodes form the graph: LCDIF → SiI902x → HDMI-connector. DRM bridge chain wires them."
  - Rewrite: "Three DT nodes form the graph: LCDIF, SiI902x, and the HDMI connector. The DRM bridge chain wires them together."
- > "But: i.MX6ULL's LCDIF clocks ceilings at ~80 MHz pixel clock."
  - Rewrite: "However, the i.MX6ULL LCDIF tops out at about 80 MHz pixel clock." ("clocks ceilings at" is awkward.)
- > "tiny, ~$2 chip"
  - Rewrite: "small, low-cost (~$2) chip"

### ESL readability

- > "Linux's DRM framework chains bridges automatically; you describe the chain in DT and the driver activates appropriately."
  - Rewrite: "DRM chains bridges automatically. You describe the chain in DT and the driver does the rest."
- > "**Output looks blank but kernel says 'modeset OK.'** Often the HDMI receiver is using a different format than the bridge is sending."
  - Rewrite: "**Modeset reports OK but the screen stays blank.** Often the HDMI sink is expecting a different pixel format than the bridge sends."

### Needs more explanation

- §55H.3 — **EDID** is mentioned twice but never explained. EDID is a 128/256 byte block the sink exposes over the DDC I²C lines. It lists supported modes and timings. The bridge driver reads it and feeds it into DRM's mode list. Without this paragraph, the term is opaque.
- The **bridge chain** is the key DRM concept this chapter is teaching but it gets one sentence. Expand: a "bridge" is a DRM object that sits between the CRTC and the connector and transforms the signal. Chains can be multiple bridges (e.g., RGB → LVDS bridge → LVDS → HDMI bridge → HDMI). Each bridge has `.attach`, `.mode_set`, `.enable`, `.disable` callbacks. The DRM core calls them in order on modeset.
- **HPD handling** deserves a paragraph. The chapter mentions the IRQ but does not show what the kernel does on the IRQ: schedule `drm_kms_helper_hotplug_event`, which re-reads EDID and triggers a userspace uevent that compositors listen for. This is how plugging a monitor "just works" in Wayland.
- The **DRM "bridge vs panel vs encoder vs connector"** distinction is the single confusion point. The same chip can be modeled three ways depending on the era of the driver. One paragraph clarifying which the SiI902x driver actually does (a bridge that also implements a connector).

---

## Ch55I — Rust for Linux

### AI wording / sledgehammer / buzzwords

- > "Rust as a second-class citizen language inside the kernel"
  - Rewrite: "Rust as a second supported language inside the kernel" ("second-class citizen" is loaded and a little dismissive.)
- > "the security cost of these bug classes is colossal"
  - Rewrite: "these bug classes account for a large share of kernel CVEs"
- > "Classes of 'did you forget to init?' bugs vanish."
  - Rewrite: "The 'did you forget to init?' bug class is no longer expressible."
- > "No more 'did I forget to check this errno?' — the compiler insists."
  - Rewrite: "You cannot silently ignore an error — the compiler will not let you."
- > "Not a wave."
  - Rewrite: "Adoption is slow." (Short editorial fragments like "Not a wave." are a Claude tic.)
- > "**For the i.MX6ULL specifically**: Rust isn't usable yet (ARM32 not supported)."
  - Rewrite: "**On the i.MX6ULL specifically**, Rust is not usable yet — ARM32 is not supported."

### ESL readability

- > "A whole class of C kernel bugs — use-after-free, double-free, data races on shared memory, integer overflows — become *unrepresentable* in safe Rust."
  - Rewrite: "A whole class of C kernel bugs becomes impossible to write in safe Rust: use-after-free, double-free, data races on shared memory, integer overflows."
- > "Rust safety is contingent on *correctly written* unsafe code."
  - Rewrite: "Rust safety depends on the `unsafe` blocks being correct. Bugs inside `unsafe` are no different from C bugs."
- > "The compiler refuses to call `.read()` on an uninitialised device."
  - Rewrite: "The compiler refuses to compile a call to `.read()` on an uninitialised device." (Compilers do not call; they accept or reject.)

### Needs more explanation

- §55I.1 should also note the **distinction between `kernel::` safe wrappers and `bindings::` raw C bindings**. Most beginners try to call C from Rust directly and end up writing huge `unsafe` blocks; the design point is that the kernel team writes the safe wrapper once, then drivers use only safe APIs.
- §55I.4 type-state example: the example uses `PhantomData<S>` but does not explain it. ESL reader has no chance. One sentence: "`PhantomData` is a zero-size marker that tells the compiler 'this type behaves as if it owned an S' for the borrow checker. It generates no code at runtime."
- §55I.5 the **`pin-init`** crate is one of the biggest practical hurdles in current kernel-Rust (because most kernel objects must be initialised in place, not moved). A paragraph would help readers who try to write a driver and immediately hit `Pin<&mut T>`.
- The chapter does not contrast Rust **module signing / kbuild integration** with C modules. Rust modules still produce a `.ko` with the same module loader interface; the only difference is the build path. Worth one line so readers do not think Rust modules need a separate loader.
- **GPL compatibility** is mentioned ("license: 'GPL'") but not explained: the kernel only links GPL-licensed Rust modules to its GPL-only symbols. A non-GPL Rust module is restricted to a smaller API. Same as C, but worth noting.

