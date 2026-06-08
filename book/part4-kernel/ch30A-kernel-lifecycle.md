---
chapter: 30A
title: Kernel lifecycle — mainline, stable, LTS, vendor BSPs
part: IV — The Kernel (supplementary v1.2)
estimated_pages: 16
status: draft
---

# Chapter 30A — Kernel lifecycle: mainline, stable, LTS, vendor BSPs
**ABI** - Application Binary Interface: the calling convention, register use, binary format, and library contract that let separately built code run together.

> **What:** a decision framework for one of the most important architectural choices in any Linux-based product: *which* kernel release do we ship? Mainline tip, the latest stable, an LTS, a vendor BSP frozen years ago, or something curated between them?
> **BSP** - Board Support Package: vendor patches, configs, bootloader files, and scripts needed to boot one board.
>
> **Why:** the choice determines your security-fix cadence, your driver-update cost, your hardware-support range, and your migration burden for the next five-to-ten years. If you choose well, updates ship easily for years. If you choose poorly, three years from now you are backporting six years of CVEs onto a fork no one upstream maintains.
>
> **Focus:** **maintenance economics**, not features. Whatever you pick, you commit to maintaining the gap between it and what the world ships next. If you cannot maintain it yourself, you pay someone who will.


## 30A.1  The six release tracks

The kernel has more than one "version". When someone says "use Linux 6.6", they could mean any of six related things:

| Track | What it is | Maintainer | Release cadence | Lifetime |
|-------|-----------|------------|-----------------|----------|
| **Mainline** | Linus's tree at `git.kernel.org/torvalds/linux.git` | Linus Torvalds | One "x.y" release every ~9 weeks | "Tip" only; superseded by next release |
| **Stable** | Per-release backport tree | Greg Kroah-Hartman | Daily/weekly through ~6 weeks after release | ~6 weeks per minor |
| **LTS** | Selected mainline releases extended | Greg KH + Sasha Levin | Weekly tagged releases | **2 years** (regular) or **6 years** (extended) |
| **Vendor BSP** | Forked mainline + thousands of vendor patches | NXP / TI / ST / etc. | Vendor-internal cadence | Until the vendor abandons the SoC |
| **Yocto / Buildroot kernel** | A curated combination of an LTS + a small layer of fixes | Yocto / Buildroot maintainers | Aligned with Yocto release cadence | Tied to the Yocto release's lifetime |
| **Distribution kernel** | Debian, Ubuntu, Fedora kernel packages | Distro maintainers | Distro release cadence | Tied to distro release lifetime |

For embedded systems, the three that matter are **Mainline**, **LTS**, and **Vendor BSP**. The other three are either too volatile (mainline tip), too short-lived (stable), or too desktop-oriented (distro) for most embedded products.

## 30A.2  Mainline

`git.kernel.org/torvalds/linux.git` — the canonical tree. Every kernel feature, fix, and driver ultimately lives here.

**Releases:** the merge window opens 1 week after each release, accepts new features for 2 weeks, then there are 6-8 weekly `-rcN` candidates before the next `x.y` final. The cycle is roughly:

```
6.5 release  ─────────►  6.6-rc1 (window closes)
                 (1 week)   │
                            └─ 8 × rc cycles, ~1 week each ─►  6.6 release  ─►  6.7-rc1 ...
```

In 2025, mainline runs at roughly 6.6 → 6.7 → 6.8 → 6.9 across a calendar year, with each minor having ~9-week cadence.

**Lifetime:** none. The day 6.6 ships, 6.7-rc1 is already absorbing the next merge window. There is no concept of "support" for plain mainline. If you ship `6.6.0` and there's a CVE in `6.6.1`, you must either (a) take `6.6.1` (the stable update), (b) cherry-pick the fix yourself, or (c) decline the fix.

**When to choose mainline:**

- **Development.** You're building the next product. You want every recent driver fix and every new feature.
- **Pre-production hardware bring-up.** Mainline is where the i.MX6ULL gained DT bindings, gained mainline EVK support, gained subsequent fixes. Tracking mainline means you can be confident about what works.
- **Demo / proof-of-concept devices.** Lifetime doesn't matter. recent features do.

**When *not* to choose mainline:**

- **Shipping product.** A device in a customer's hands needs an upstream commitment longer than 9 weeks. Mainline gives you no such commitment.

## 30A.3  Stable

`git.kernel.org/stable/linux.git`, branches `linux-6.6.y`, `linux-6.5.y`, etc.

Greg KH manages this tree. Stable releases backport **bug fixes and security patches only** from mainline to a specific x.y. So `linux-6.6.y` accumulates fixes from mainline that apply cleanly (or with light tweaks) to 6.6's codebase.

Releases come out daily-to-weekly with version tags like `v6.6.1`, `v6.6.2`, ..., `v6.6.42`.

**Lifetime:** historically ~6 weeks per minor (one cycle of mainline). The current minor's stable tree continues until the next minor's stable tree starts. The older one is then EOL'd.

**Exception:** selected stable trees are promoted to **LTS** (next section) and continue for years.

**When to choose stable (non-LTS):**

- You want the latest known-good kernel, with all minor-version fixes, and you're going to upgrade to the next minor every 9 weeks anyway. Mostly: development boards, where you regularly rebase.

**When *not* to choose stable:**

- Shipping product, again. You'll lose support in 6 weeks.

## 30A.4  Long-Term Support (LTS)

Selected mainline releases are designated **LTS** and get stable-tree backports for years instead of weeks. The current pattern, as of 2026:

| LTS | Released | Support ends | Notes |
|-----|----------|--------------|-------|
| 6.6 | Oct 2023 | Dec 2026 | Default LTS pick for new 2024+ products |
| 6.1 | Dec 2022 | Dec 2026 | Heavily used by Android, several distros |
| 5.15 | Oct 2021 | Oct 2026 | Still common in embedded |
| 5.10 | Dec 2020 | Dec 2026 | Android 11/12 ABI baseline |
| 5.4 | Nov 2019 | Dec 2025 | Aging; many vendor BSPs are pinned here |
| 4.19 | Oct 2018 | Dec 2024 | EOL imminent |
| 4.14 | Nov 2017 | Jan 2024 | EOL'd |

**LTS lifetime is the lifetime of the product, in practice.** A product shipping in 2025 on LTS 6.6 has fixes flowing in until Dec 2026, by which time you should already be migrating to a newer LTS (LTS 6.12 will likely be the next one, supported until ~2030).

**The "extended LTS" track** (sometimes called "Civil Infrastructure Platform" or CIP) backports security fixes for **6+ years** on selected LTS releases, funded by industrial users (Toshiba, Siemens, others). Less drama-prone than mainline LTS but slower-moving.

**When to choose LTS:**

- **Any shipping product with a multi-year field life.** This is the default answer.
- Cost-sensitive products that can't afford a dedicated kernel maintainer. LTS gives you free upstream backports.
- Products that need security-fix updates after end-of-development.

**When *not* to choose LTS:**

- You need a brand-new feature only in mainline that hasn't been backported.
- Your hardware vendor's BSP is pinned to a non-LTS release and you can't afford to forward-port their patches.

## 30A.5  Vendor BSPs

Every silicon vendor (NXP, TI, ST, Rockchip, Broadcom, ...) maintains a downstream fork of mainline with their own additions. For i.MX6ULL, that's NXP's `linux-imx` at `github.com/nxp-imx/linux-imx`.

A vendor BSP typically contains:

1. **A pinned mainline base.** NXP's recent linux-imx branches are based on `5.15.71` or `6.6.23`, not on mainline tip.
2. **Vendor patches.** Thousands. Drivers for proprietary silicon, performance tweaks, customer-requested features, security fixes the vendor hasn't yet upstreamed.
3. **Vendor BSP-only drivers.** Drivers that exist *only* in the BSP, never in mainline. Frequently for GPU, video codec, ISP, or other IP blocks the vendor considers a trade secret.

The vendor releases new tags periodically (NXP about quarterly). Old tags get little attention.

**The upside.** Every peripheral on the vendor's reference board has a working driver. The vendor's tool — Yocto layer (`meta-imx`), demo image, evaluation kit — assumes their BSP.
**Yocto** - a metadata-driven build system for producing custom Linux distributions.

**The downside.** Three things you must factor in:

- **Security-fix latency.** The vendor's quarterly cadence means CVEs in your BSP base are typically 1-3 months behind mainline. Some critical fixes never get backported to the vendor's older releases.
- **Mainline drift.** Every quarter, the vendor's tree drifts further from mainline. Any patch you write against the BSP needs porting before it works against mainline. The longer you wait, the harder that port becomes.
- **Vendor abandonment risk.** When NXP stops supporting i.MX6ULL (they will, eventually), `linux-imx` will stop getting updates for that SoC. You're then maintaining the BSP yourself or porting to mainline.

**When to choose a vendor BSP:**

- **You need a vendor driver that isn't in mainline.** Common for GPUs, hardware codecs, vendor-specific ISP/camera pipelines.
- **Time-to-market is paramount and the product lifecycle is < 3 years.** Vendor BSPs ship fast. If you don't need to maintain it for 10 years, the migration cost may never arrive.
- **You're under contractual pressure to use the vendor's reference design.** This happens.

**When *not* to choose a vendor BSP:**

- **Multi-year product life and security matters.** The BSP is a long-term liability.
- **Mainline already supports your hardware completely.** For i.MX6ULL with stock peripherals, mainline is fully sufficient. Going vendor adds future cost without benefit.

## 30A.6  The decision framework

A flowchart-as-text:

```
Question 1: Does your hardware work on mainline?
   ├─ Yes  ─► Question 2
   └─ No   ─► Vendor BSP is forced.  Plan a migration to mainline within 1-2 years.
                  See Chapter 122A for the playbook.

Question 2: What's the product's expected field life?
   ├─ < 1 year         ─► Mainline tip is fine; rebase to next LTS before manufacturing.
   ├─ 1-3 years        ─► Current LTS.
   ├─ 3-7 years        ─► Current LTS, with explicit budget for one LTS migration mid-lifecycle.
   └─ 7+ years         ─► Extended LTS (CIP) or self-maintained LTS branch.

Question 3: Do you have a kernel maintainer on the team?
   ├─ Yes              ─► You can run mainline if Q1 says you can.
   └─ No               ─► Stick with LTS.  Don't try to maintain a fork.
```

For our i.MX6ULL on Point Atom MINI:

- **Q1: Does it work on mainline?** Yes. full support since v4.10.
- **Q2: Product life?** Assume 5 years for an industrial product.
- **Q3: Maintainer?** This book exists to teach you to be one.

→ **Current LTS, with a mid-lifecycle migration plan.** As of 2025, that means LTS 6.6 (or 6.1 if you want extra runway). Plan a 6.6 → 6.12 (or 6.1 → 6.6) migration in year 3.

## 30A.7  The 4.1.15 trap

Here is a common scenario. You inherit a vendor BSP pinned to Linux 4.1.15 (NXP's i.MX BSP from 2017). The hardware works and the board boots, so you are tempted to ship it.

What you would actually be shipping:

- **A kernel from 2017.** Five-plus years of CVE backlog. Even cherry-picking critical fixes is a part-time job.
- **A driver model from 2017.** Many subsystems (DT bindings YAML, modern clk framework, regmap-everywhere, devm-_* helpers, etc.) have evolved. Code you write against 4.1.15 doesn't transfer to mainline without rewrite.
> **MCU bridge:** Think of regmap like a typed wrapper around your read_reg() and write_reg() helpers, with caching, locking, and bus differences handled centrally.
**regmap** - a kernel helper that wraps register reads and writes over I2C, SPI, or MMIO.
- **Toolchain constraints.** 4.1.15 doesn't build with modern gcc (>= 11) without patches. You're committing to an old gcc too.
- **No upstream support.** Linux 4.1 has been EOL for years. Issues you file get closed as "fixed in 5.x".

The 4.1.15 trap is real. It works *today*. It costs increasingly more *every year*. If you find yourself inheriting one, treat the migration to mainline as a P1 work item, not a P3 "someday". Chapter 122A walks the migration.

The same applies to any sufficiently-old vendor BSP: 4.9, 4.14, 4.19, 5.4, 5.10. Each year past the LTS EOL the situation worsens.

## 30A.8  Worked example: shipping decisions

Three scenarios:

### Scenario A — Consumer IoT smart-light, 3-year product life

- Need: low-power Wi-Fi, BLE, a custom LED-strip driver, OTA updates.
- All hardware supported in mainline (the Wi-Fi via standard mainline drivers, BLE via Bluetooth subsystem, LED strip via SPI).
- **Decision: LTS 6.6.** Migrate to next LTS (~6.12) in year 2 alongside any major firmware bump. Set up an OTA pipeline (Ch 63) so kernel upgrades reach the field.

### Scenario B — Industrial PLC, 10-year product life, IEC 61131 certified

- Need: hard real-time (< 100 µs jitter), CAN bus, EtherCAT master, vendor-specific ISP for camera.
- ISP driver only in NXP's BSP. never upstreamed.
- **Decision: Vendor BSP — for now — with mandatory migration plan.** Track NXP's LTS-aligned branch (6.6-based). Allocate budget in year 3 to begin upstreaming the ISP driver. Aim to be on mainline LTS by year 5. Otherwise: pay an external Linux company to extended-LTS your kernel for the remaining lifespan.

### Scenario C — Hobbyist single-board computer kit

- Need: just works out of the box. users will run their own kernels too.
- **Decision: Mainline tip, refresh per Yocto release.** Hobbyists expect to be current. nobody's running this kit for 5 years.

The pattern across all three: **the product's field life and the security level required together determine the kernel track.**

## 30A.9  Lab

1. **Read the LTS announcement** for the current LTS at `lwn.net` or `kernel.org`. Note the maintainer, support window, and any caveats.
2. **Audit your codebase against an LTS.** Pick a recent commit in mainline that adds a feature you care about (e.g., a new DT binding). Run `git log --oneline v6.6.. -- Documentation/devicetree/bindings/...` to see whether it has been backported to LTS 6.6. Most large features are not.
3. **Pretend you inherited a 4.14 BSP** with a custom GPIO driver. Look at the mainline-equivalent driver (`drivers/gpio/gpio-mxc.c`) and identify which kernel-API changes have happened since 4.14 that would require rewriting (DT bindings, devm_, the gpio chip api, ...). Make a one-page "migration burden" estimate.
> **MCU bridge:** Think of Linux GPIO like the same pin set/reset block you used on STM32, but accessed through a kernel subsystem that owns numbering, direction, interrupts, and user-space exposure.
**GPIO** - General-Purpose Input/Output, a pin controlled as a digital input, output, or interrupt source.
4. **Set up a CI matrix.** Imagine you need to build the same `defconfig` against three kernels: mainline tip, LTS 6.6, LTS 6.1. Sketch a GitHub Actions / GitLab CI job matrix. Estimate build-time and disk usage.
5. **Subscribe to two mailing lists.** `linux-kernel-announce@vger.kernel.org` (release announcements only) and `linux-stable@vger.kernel.org` (stable-tree releases). Build the habit of seeing what's happening before it affects you.

## 30A.10  Pitfalls

- **"Just stay on 5.4 forever."** 5.4 ends in Dec 2025. That is not forever.
- **"We'll upgrade the kernel later."** "Later" never comes if your code is so deeply intertwined with vendor BSP internals that migration is a major rewrite. Budget the migration *now*, even if you delay execution.
- **"LTS = no breaking changes."** LTS gets bug fixes and security patches. Behavior fixes can change semantics. Test before deploying.
- **"Mainline is unstable."** Modern mainline is *very* stable. what's unstable is mainline tip *between releases*. Pick a tagged release (`v6.6` not `master`) and you have what was tested.
- **"We don't need security fixes. The device isn't on the internet."** This is less and less true. Even isolated devices receive USB sticks. Even airgapped devices face supply-chain attacks. Apply the fixes.
- **"Our customer requires the vendor BSP."** Sometimes true (compliance, IP). Often a habit. Push back on the contractual requirement when the technical justification is weak.

## 30A.11  Going deeper

- **`kernel.org/category/releases.html`** — current state of every kernel release.
- **`lwn.net/Articles/...`** — weekly Linux Weekly News articles, the best source for keeping current.
- **The `linux-cip` (Civil Infrastructure Platform) project** — extended-LTS for industrial applications.
- **Bootlin's "Embedded Linux from Scratch" training** (free online materials) — covers a similar decision framework.
- **`Documentation/process/stable-kernel-rules.rst`** — what does and doesn't get backported to stable trees.
- **`drm/kernel-doc-rst` discussions on `linux-rt-users` mailing list** for PREEMPT_RT-specific lifecycle considerations.
**PREEMPT_RT** - the Linux real-time patch set that makes more kernel paths preemptible and reduces latency.

> Next part: **Part V — Root filesystem & user space.** With the kernel sorted, we turn to what runs on top. BusyBox by hand, then Buildroot, then Ubuntu-base — and the production patterns (read-only root, containers) that real shipping products use.
> **Buildroot** - a configuration-driven build system that produces a complete root filesystem and related images.
