---
chapter: 122A
title: BSP → mainline migration playbook
part: VIII — Debug, production, advanced
estimated_pages: 22
status: draft
---

# Chapter 122A — BSP → mainline migration playbook

> **What:** the **systematic procedure** for taking an inherited vendor BSP (NXP `linux-imx 4.1.15`, ST's `stm32mp1 4.19`, TI's `ti-linux-5.10`, …) and moving the product to a **mainline** Linux kernel that's supportable for the product's lifetime. We cover the patch inventory + classification, the subsystem-by-subsystem migration order (the safest path through the dependency graph), the test-coverage strategy, the parallel-tree maintenance during the migration, the upstreaming of recoverable bits, and the "do not migrate" decision criterion.
> **Why:** you join a project; the existing kernel is Linux 4.1.15 from NXP's 2017 BSP; the product ships for 8 more years; security CVEs accumulate weekly; mainline is at 6.6+; and the BSP is *frozen* — no upstream updates because the vendor moved on. You're staring at a project-defining decision. This chapter is the playbook so it doesn't become a project-killing one.
> **Focus:** **classify every vendor patch into mainline-merged (delete), mainline-equivalent (replace), still-needed (forward-port), or vendor-only (decide individually); migrate subsystem-by-subsystem in dependency order; maintain BOTH trees in parallel during the transition; CI on both**. The hardest bits aren't technical (`git rebase` does most of it); they're *cultural*: convincing management that 6 months of "no new features, just kernel work" pays back over the product's life. This chapter arms you with the data.

## 122A.1  Why migration is hard

A typical 2017-era NXP BSP:
- 4.1.15 mainline + **~7,000 NXP patches**
- ~1,500 of which are now in mainline (rebased, refactored, or rewritten)
- ~2,000 are obsolete (fix bugs in code mainline rewrote)
- ~2,000 are still-needed (drivers for chips mainline doesn't support)
- ~1,500 are NXP-internal-only (vendor APIs, downstream UI hacks, broken HW workarounds)

Plus:
- Old toolchain (gcc 6.x) won't compile mainline kernel 6.6 cleanly. The kernel's hard minimum is gcc 5.1 (Documentation/process/changes.rst), but newer features and warnings require gcc 11+; most distros ship gcc 12+ for embedded cross-builds.
- Old U-Boot 2017.04 doesn't speak modern FIT.
- Old Buildroot/Yocto recipes pinned to old library versions.
- Old GStreamer 1.10; mainline drivers use new V4L2 APIs.

The "easy" path — stay on 4.1.15 forever — leaves accumulated CVEs unfixed:
- CVE-2017-1000405 (the "Huge Dirty COW" / Dirty COW THP race): patched in 4.1.51, missed in your 4.1.15.
- CVE-2018-3639 (Spectre v4): no fix backported to your fork.
- CVE-2021-4034 (Polkit pwnkit): irrelevant to kernel but kernel-related stack.
- 2024+ CVEs: countless.

The "hard" path — migrate to mainline 6.6+ LTS — buys:
- 6 years of security maintenance from kernel.org.
- Modern features (eBPF, io_uring, PREEMPT_RT, USB4, ...).
- Predictable LTS cycle.
- Upstream-able fixes.

For products with > 2 years of remaining ship life, **migrate**. For products in last-12-months, **monitor CVEs and backport critical fixes manually**.

## 122A.2  Inventory phase — classify every patch

```sh
# In the BSP kernel
git log --oneline v4.1.15..HEAD > patches.txt
wc -l patches.txt
# 7234 patches
```

Categorize each. A spreadsheet (or simple script):

```
patch_id | subject | files_touched | category
0123abcd | Add support for SXX sensor | drivers/iio/light/sxx.c | NEW DRIVER (still needed if SXX is on product)
0124abcd | Fix race in FEC driver | drivers/net/ethernet/freescale/fec_main.c | BUG FIX (check if in mainline)
0125abcd | Add NXP-specific GStreamer plugin support | gst/ | VENDOR API (decide)
0126abcd | Backport: net/tcp fix from 4.4 | net/tcp.c | OBSOLETE (mainline already has it)
0127abcd | Add IMX support for HDMI bridge | drivers/gpu/drm/bridge/ | NEW DRIVER (probably in mainline by now)
```

For each "still-needed" or "new driver," check mainline:

```sh
cd /tmp/linux-mainline
git log --grep "SXX" --oneline
git log --diff-filter=A --all -- drivers/iio/light/sxx.c
```

If mainline has it (committed by someone else after 2017): **delete the BSP patch**, use mainline's version.

If not: this is your **upstreaming opportunity** — extract the patch, clean it, submit to mainline (Ch 120A) so the next person doesn't have to.

After inventory:
```
2000 mainline-merged: delete
2000 obsolete: delete
1500 vendor-only: triage (keep/delete/upstream)
1500 still-needed: forward-port (write into 6.6 mainline)
```

Now you have ~3000 patches to *port forward*, not 7000.

## 122A.3  Pin the BSP — set up the migration "stable" branch

Before migration, freeze BSP development:
- Branch: `bsp-frozen-2026q2` from current BSP HEAD.
- Only critical security backports and customer-blocking bugs land here.
- All new feature work goes on `mainline-6.6-port` branch.

This buys you 6+ months to migrate while still shipping fixes to existing customers.

## 122A.4  Order of attack — subsystem dependency graph

Migrate subsystems in dependency order, **most-isolated first**. The graph:

```
   most isolated                                                 most coupled
   ──────────────                                                ────────────
   clk          ──► pinctrl ──► gpio ──► i2c ──► spi ──► sensors
                                          │
                                          └─► PMIC ──► regulator ──► PHY
                                                                       │
                                                                       └─► ethernet
                                                                              │
                                                                              └─► network
                                                                                     │
                                                                                     └─► applications
   mmc          ──► block ──► filesystem ──► userspace
   usb host     ──► usb-mass-storage ──► block
   serial       (isolated)
   audio (ASoC) ──► I²S DAI ──► codec ──► applications
   display      ──► drm/kms ──► applications (heaviest)
```

For each phase:
1. **Phase 1 (week 1–4)**: clk, pinctrl, gpio — the *foundation* every other subsystem uses. Most BSP-vs-mainline divergence; lots of NXP-internal pinmux files to merge.
2. **Phase 2 (week 5–8)**: i2c, spi controllers + the *trivial* sensors hanging off them. Easy wins to build confidence.
3. **Phase 3 (week 9–12)**: PMIC, regulators, eMMC, USB host. The "boot reliably" phase.
4. **Phase 4 (week 13–16)**: Ethernet, network stack. Verify customer-facing connectivity.
5. **Phase 5 (week 17–20)**: Audio, display, camera, GPU. The "rich apps work" phase. Hardest because of vendor's binary blobs (Vivante GPU on i.MX) and downstream GStreamer integrations.
6. **Phase 6 (week 21–24)**: Application port. Update Buildroot/Yocto recipes for newer library versions.

Each phase: **bring up subsystem on mainline, run integration tests, only then move to next**. Don't skip ahead.

## 122A.5  Per-subsystem migration

For each subsystem:

1. **Identify divergence**: `git diff bsp-frozen..mainline-6.6 -- drivers/foo/`. What's different?
2. **Determine which patches still apply**: try `git cherry-pick` each. Many trivially conflict; mainline has refactored the file.
3. **For each conflict, decide**: (a) BSP patch is dead — code mainline replaced it. Drop. (b) BSP patch is still needed — port to mainline's new structure. (c) Mainline is missing functionality — extract to a separate patch, upstream.
4. **Test on hardware**. Each subsystem migrated must pass its tests before moving on.

Tools that help:
- **`git blame`** on mainline file to understand the new structure.
- **`scripts/get_maintainer.pl`** to find a mainline maintainer who knows the subsystem (ask them if your BSP patch's intent is now solved differently).
- **`Documentation/devicetree/bindings/`** to see how the DT contract changed.

## 122A.6  The "pinned driver" problem

Some vendor drivers are pinned to BSP-API versions and rewriting them is hard. Examples:
- Vivante GPU's userspace blob expects vendor's GLES driver, which talks to vendor's kernel DRM driver. Mainline has `etnaviv` (reverse-engineered) — but vendor app may not support etnaviv's slightly different EGL config.
- VPU (Video Processing Unit) for hardware H.264 decode: vendor proprietary blob; mainline `coda` driver covers some chips.
- ISP (Image Signal Processor): vendor blob; little mainline support.

For each "pinned" component, options:
- **Replace with mainline equivalent + accept feature reduction** (etnaviv for Vivante).
- **Run vendor driver as out-of-tree module** + accept the maintenance cost.
- **Switch to a different SoC** in your next product revision where mainline has full support.

The first option is best long-term; the second is a stopgap; the third is the strategic decision.

## 122A.7  Maintaining two trees in parallel

During the 6-month migration:
- `bsp-frozen-2026q2` ships to all current customers.
- `mainline-6.6-port` is what engineers work on.
- Backport critical bug fixes from BSP → mainline-port (small patches, easy).
- *Don't* port mainline-port features back to BSP (one-way migration).

CI on both:
- Cross-build both kernels on every commit.
- Run hardware smoke tests on both (need two boards or a board with a runtime-switchable boot image).

Cutover: schedule a date when new customer shipments come on the mainline-port version. Existing customers can choose to update or stay on BSP.

## 122A.8  When NOT to migrate

If any of these is true: **don't migrate; manage CVEs manually on the BSP**:

- Product is end-of-life within 12 months.
- Critical hardware silicon has no mainline driver (and you can't write one in 6 months).
- Vendor SDK / app stack only works with BSP version (and rewriting the app is out of scope).
- Customer regulatory certification requires the specific kernel version + binary build (re-cert costs more than CVE backports).

In these cases: have someone watch CVE feeds (oss-security, kernel.org); backport critical fixes manually; document the deviation from upstream for compliance.

## 122A.9  Worked example — NXP iMX6ULL 4.1.15 → 6.6 mainline

This is the canonical migration for this book's target SoC.

```sh
# 1. Set up workspaces
mkdir migrate-imx6ull && cd migrate-imx6ull
git clone https://github.com/nxp-imx/linux-imx.git nxp-bsp
cd nxp-bsp && git checkout imx_4.1.15_2.0.0_ga && cd ..
git clone https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git mainline
cd mainline && git checkout v6.6 && cd ..

# 2. Get the BSP patch list
cd nxp-bsp
git log --oneline v4.1.15..HEAD | wc -l       # ~ 7000 patches
git format-patch v4.1.15..HEAD -o ../bsp-patches/
cd ..

# 3. Quick wins — mainline already supports i.MX6ULL well as of 6.6
# - clk, pinctrl, gpio, i2c, spi, mmc, usb host: all in mainline
# - FEC: mainline driver, full feature parity
# - audio (SAI + WM8960): mainline driver
# - eLCDIF: mainline DRM driver (imx-lcdif)
# - CSI (camera): partial mainline support (imx-csi)
# - PWM, RTC (SNVS), watchdog (WDOG): all mainline

# 4. What probably needs porting from BSP
# - Specific board DTS additions (your customer's variants)
# - Out-of-tree drivers (e.g., RFM69, custom IIO sensors)
# - User-space driver agents (some IPC mechanism)

# 5. Test
cd mainline
make ARCH=arm CROSS_COMPILE=arm-linux-gnueabihf- imx_v7_defconfig
make ARCH=arm CROSS_COMPILE=arm-linux-gnueabihf- -j$(nproc) zImage dtbs
# Boot from existing rootfs first; later update rootfs to libcs ABI-matched to gcc 13

# 6. Iterate per subsystem
# Verify Ethernet works → check.
# Verify USB host enumerates a USB stick → check.
# Verify the specific sensor your product has → port the driver if needed.

# 7. Cut over
# Update CI to test mainline as primary.
# Issue product firmware update.
# Deprecate the BSP branch.
```

For i.MX6ULL specifically: mainline support is *excellent* as of 6.6 — most BSP work was upstreamed during 2018–2023. Many migrations end up with ~50 forward-ported patches (board DTS + a couple of out-of-tree drivers). Months of work, not years.

## 122A.10  Lab

1. **Inventory a real BSP.** Download NXP's `linux-imx 4.1.15`; `git log --oneline v4.1.15..` to see the patch count; sample 10 patches; classify each into the 4 categories.
2. **Cross-reference with mainline.** For each "still-needed" patch, search mainline (`git log -p` on the file): is the same fix already merged?
3. **Port the trivial subsystem.** Pick gpio or i2c; verify the BSP patches are all merged in mainline 6.6. Confirm: no porting needed for this subsystem.
4. **Find an unmerged patch.** Pick one that's not in mainline. Investigate why (was it submitted? rejected? never submitted?). Read the Lore archive (Ch 120A).
5. **Upstream candidate.** Take a BSP patch that's a clear improvement; clean it; submit to mainline per Ch 120A. (Even if rejected, the experience is valuable.)
6. **Compile mainline for your board.** Use mainline 6.6's imx6ull defconfig. Build zImage + DTB. Boot on the Point Atom MINI.
7. **Run-time comparison.** Boot the same hardware on BSP 4.1.15 and mainline 6.6. Compare: boot time, dmesg output count, kernel size, RAM usage at idle.
8. **CVE diff.** Use `cve-checker` (or NIST CVE search) to count CVEs against 4.1.15 vs 6.6 LTS. The number will shock.
9. **Plan a migration.** Imagine you're the engineer-in-charge. Write a 1-page proposal: subsystem-by-subsystem timeline, person-weeks estimate, risk register, fallback plan.

## 122A.11  Pitfalls

- **Underestimating scope.** "It's just a kernel upgrade." A 7000-patch migration is **6 person-months minimum**. Plan accordingly.
- **Migrating to non-LTS mainline.** Mainline rolls every 9 weeks. Pick an LTS (currently 6.6, supported until 2028). Don't pick the bleeding-edge.
- **Skipping subsystem isolation.** "Let me bring up everything at once" → debug becomes impossible. Phase-by-phase.
- **Forgetting userspace compatibility.** Mainline 6.6 expects glibc 2.35+; your BSP rootfs has glibc 2.24. Rebuild rootfs too.
- **DT bindings drift.** A binding that "worked in 4.1.15" may have been refactored in mainline. Update DT to match.
- **Out-of-tree drivers break.** Every kernel API change risks your custom driver. Keep custom drivers minimal; upstream them when possible.
- **Toolchain ABI mismatch.** gcc 13 produces slightly different code than gcc 6; some assumptions in old assembly break.
- **Customer regression.** Sometimes a behavior the customer relies on was a BSP-only "feature" not in mainline. Document; communicate; sometimes you have to accept regression.
- **Management commitment fades.** "It's 4 months in, no new features yet, can we go back?" Plan for this; have weekly visible progress milestones; show CVE-burndown charts.
- **Going halfway.** Migrating half the subsystems = the worst of both worlds (now you have two trees forever). Commit to the cutover.
- **Not migrating despite need.** "Easier to backport CVEs." After 100+ CVEs, the backport effort exceeds the migration effort. Track this.

## 122A.12  Going deeper

- **NXP's Yocto BSP release notes** — show what got merged upstream by version.
- **Kernel LTS announcements** (lore.kernel.org → stable@vger) — for current LTS lifetimes.
- **CVE database (NIST NVD)** — search by `linux_kernel`.
- **Bootlin's "BSP support" presentations** — practical migration case studies.
- **`scripts/git_diff_filter.sh`** in kernel — for filtering relevant diff.
- **Greg KH's stable-tree maintenance talks** — for why and how stable trees exist.
- **`grsecurity` and `KSPP`** — for understanding the security argument for mainline.
- **Ch 30A** — the original kernel-lifecycle decision framework.
- **Ch 120A** — for upstreaming what's worth saving.
- **Ch 123 / Ch 123A** — for the Yocto / Buildroot recipe migration that goes alongside.

---

> Next chapter: **Chapter 123 — Yocto vs Buildroot, an honest comparison**.
