---
chapter: 120A
title: Mainline patch submission workflow
part: VIII — Debug, production, advanced
estimated_pages: 18
status: draft
---

# Chapter 120A — Mainline patch submission workflow

> **What:** the **end-to-end workflow** for submitting a patch to the Linux kernel: `git format-patch`, `scripts/checkpatch.pl`, `scripts/get_maintainer.pl`, `git send-email`, the `b4` tool for series management, response etiquette (`Reviewed-by`, `Acked-by`, v2/v3 iteration), and the **Lore** archive for finding similar prior work. Worked on a real candidate patch — e.g., a YAML binding addition for a sensor used in your Cookbook chapter, or a one-line bug fix in the FEC driver.
> **Why:** if you write a driver in this book and it's useful, it can go upstream. Upstream-merged code is maintained forever (security backports, API migrations); your out-of-tree fork is on you. But the kernel community has strict, *unwritten* rules — wrong commit-message format, untested patches, replying to review with hostility, top-posting on mailing lists — these get your patch silently dropped no matter how good the code is. This chapter is the cultural primer the kernel docs don't write down.
> **Focus:** **the workflow is git-format-patch → checkpatch → get_maintainer → send-email → respond to review → v2 → repeat**. The cultural part is harder: be concise; one fix per patch; explain *why* not just *what*; never ignore review feedback (even if you disagree, respond); CC the right people but no spammy CC; subject lines are `[PATCH] subsystem/file: short summary`. Lore.kernel.org is the public archive of every mailing-list discussion since ~1998; **always search there before sending** — your "novel" fix may have been tried and rejected three times already, and the rejection threads tell you why.

## 120A.1  Decide what you're submitting

Categories, in order of acceptance ease:

| Patch type | Likelihood of acceptance | Reviewer count |
|---|---|---|
| Trivial typo / comment fix | high | low |
| Bug fix with clear reproducer | high | medium |
| YAML binding for an existing chip | high | medium (DT maintainers) |
| New driver for unsupported chip | medium | high (subsystem maintainer + experts) |
| New subsystem | very low | huge (the whole community) |
| Performance optimization | medium | high (must have benchmarks) |
| Cleanup / refactor | medium | medium (must justify churn) |
| Feature already done another way | very low | (rejected — see Lore) |

For your first patch: **trivial typo, bug fix with reproducer, or YAML binding** is the sweet spot.

## 120A.2  Prerequisites — clone the right tree

For most subsystems, patch against either:
- **mainline** (`linux/torvalds.git`) — for very recent code.
- The **subsystem maintainer's tree** — listed in `MAINTAINERS`. E.g., for NXP i.MX changes: Shawn Guo's `linux/arm/imx`; for networking: `netdev`; for staging: `staging-next`.

```sh
git clone https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git
cd linux
git checkout -b my-patch
```

## 120A.3  Make the change

Same tools as any kernel patch — Edit, build, test:

```sh
make ARCH=arm CROSS_COMPILE=arm-linux-gnueabihf- imx_v7_defconfig
# Edit
make ARCH=arm CROSS_COMPILE=arm-linux-gnueabihf- zImage
# Test on hardware

git add -p
git commit
```

Commit message structure:

```
subsystem/file: short summary (max 70 chars, imperative mood)

Explanation of WHY this change is needed. Refer to the problem,
not the patch. Cover:
- What was broken / missing
- Why prior approaches don't work (if any)
- What user-visible effect this has
- Reference any tests / kernel versions affected

Add a Fixes: tag if this fixes a known regression:
Fixes: 0123456789abcdef ("original subject line")

Signed-off-by: Your Name <your@email.com>
```

The `Signed-off-by` is the **Developer Certificate of Origin** — you certify you have the right to submit this code under the kernel's license. `git commit -s` adds it automatically. Without it, the patch is rejected.

## 120A.4  checkpatch.pl — the style validator

```sh
git format-patch -1
# 0001-subsystem-fix-something.patch

./scripts/checkpatch.pl --strict 0001-*.patch
# total: 0 errors, 0 warnings, 0 checks, 25 lines checked
# 0001-... has no obvious style problems and is ready for submission.
```

checkpatch enforces:
- Line length ≤ 100 chars
- Tabs for indentation, not spaces
- C89 declarations (declare-at-top-of-block — modern kernels relaxed)
- No trailing whitespace
- `if (cond)` not `if( cond )`
- `goto out_unlock;` style for cleanup
- Many other things

`--strict` catches more (e.g., long lines that aren't strictly forbidden but discouraged). For your first patch: fix everything checkpatch reports, even warnings. Maintainers run checkpatch themselves; clean output is professional.

## 120A.5  get_maintainer.pl — who to send to

```sh
./scripts/get_maintainer.pl 0001-*.patch
# Shawn Guo <shawnguo@kernel.org> (maintainer:ARM/FREESCALE IMX...)
# Sascha Hauer <s.hauer@pengutronix.de> (maintainer:ARM/FREESCALE IMX...)
# Pengutronix Kernel Team <kernel@pengutronix.de> (reviewer:ARM/FREESCALE IMX...)
# Fabio Estevam <festevam@gmail.com> (reviewer:ARM/FREESCALE IMX...)
# NXP Linux Team <linux-imx@nxp.com> (reviewer:ARM/FREESCALE IMX...)
# linux-arm-kernel@lists.infradead.org (moderated list:ARM/FREESCALE IMX...)
# linux-kernel@vger.kernel.org (open list)
```

The output is your To: + CC: list. **Do not invent additional CCs** — only what `get_maintainer.pl` says. Spam to "the whole kernel" gets you on people's filter-out lists.

## 120A.6  Send via git send-email

`git send-email` is the only patch-submission tool kernel maintainers accept. **Not** GitHub PRs, not email attachments, not pastebin links. Plain text email with the patch in the body.

```sh
# One-time config
git config --global sendemail.smtpserver smtp.gmail.com
git config --global sendemail.smtpserverport 587
git config --global sendemail.smtpencryption tls
git config --global sendemail.smtpuser your@gmail.com

# For Gmail, generate an App Password (with 2FA enabled) and use that

# Send
git send-email --to "Shawn Guo <shawnguo@kernel.org>" \
               --cc "Sascha Hauer <s.hauer@pengutronix.de>" \
               --cc linux-arm-kernel@lists.infradead.org \
               --cc linux-kernel@vger.kernel.org \
               0001-*.patch
```

Or to-from-file:

```sh
git send-email --to-cmd='./scripts/get_maintainer.pl --no-rolestats' --cc-cmd ... 0001-*.patch
```

`git send-email` is finicky to set up the first time (SMTP auth, App Passwords for Gmail/Outlook); allow an hour for first-time setup.

## 120A.7  Multi-patch series + cover letter

For more than one patch:

```sh
git format-patch -3 --cover-letter
# 0000-cover-letter.patch
# 0001-foo-fix-bar.patch
# 0002-foo-add-baz.patch
# 0003-foo-update-bindings.patch
```

Edit `0000-cover-letter.patch` (the `*** SUBJECT HERE ***` and `*** BLURB HERE ***` placeholders):

```
Subject: [PATCH 0/3] foo: bug fix + new feature

This series fixes the X bug in foo (patch 1) by approach Y, then adds
support for the new Z chip (patches 2-3). Tested on hardware A and B.

Series structure:
  Patch 1: foo: fix X bug (the actual bug fix)
  Patch 2: foo: add support for Z chip (the driver code)
  Patch 3: dt-bindings: foo: add Z binding (the DT binding)

Patch 1 stands alone; patches 2-3 require patch 1 first.

Andy Doe (3):
  foo: fix X bug
  foo: add support for Z chip
  dt-bindings: foo: add Z binding

 ...

```

Cover letter sets the context maintainers need to triage. Send all patches together:

```sh
git send-email --to ... 0000-cover-letter.patch 0001-*.patch 0002-*.patch 0003-*.patch
# OR send the whole folder:
git send-email --to ... 00*.patch
```

## 120A.8  v2 / v3 — revising based on feedback

Maintainer responds with feedback. Don't argue; address each point. If you disagree, explain politely.

```sh
# Make changes
git commit --amend  # OR rebase + rework

git format-patch -1 -v 2 --in-reply-to=<msg-id-from-original-v1>
# 0001-subsystem-fix-something.patch (header now says "[PATCH v2]")

# Add a changelog at the bottom of the cover letter:
#   ---
#   Changes in v2:
#     - addressed Foo's feedback about Bar
#     - removed redundant baz check
git send-email --to ... 0001-v2-*.patch
```

The `---` separator in the commit body means "this text goes under the patch as a note, not part of the commit message." Put your changelog there.

## 120A.9  Reviewed-by, Acked-by, Tested-by, Reported-by

In reply to your patch, others may say "Reviewed-by: …" — that means they read it carefully and approve. Include their tag in your v2:

```
Reviewed-by: Reviewer Name <reviewer@example.com>
Signed-off-by: Your Name <you@example.com>
```

Tags:
- **Signed-off-by**: required; certifies origin.
- **Reviewed-by**: reviewer carefully read and approved.
- **Acked-by**: subsystem maintainer or expert agrees (lower bar than Reviewed-by).
- **Tested-by**: someone other than you tested it on hardware.
- **Reported-by**: someone reported the bug this fixes.
- **Suggested-by**: someone suggested this approach.
- **Co-developed-by**: pairs with Signed-off-by for joint authorship.

Tags accumulate over revisions; carry forward all relevant ones.

## 120A.10  Replying to reviews — etiquette

```
On Mon, Mar 5, 2026 at 10:00 AM, Foo Maintainer wrote:
> > +    if (val < 0)
> > +        return -EINVAL;
> > +    val *= 2;
>
> Why is this multiplication needed? Comment seems lacking.

Apologies for the missing comment. The hardware register interprets
the value in 50% steps; multiplying by 2 converts user-supplied
percent to register units. I'll add a comment in v2.

Thanks for the review.
```

Rules:
- **Reply inline, below the quoted text** (not top-posted).
- **Trim quoted context** — don't quote the whole patch back.
- **Plain text email** — no HTML, no signatures with images.
- **Address every comment**: either "fixed in v2," "I disagree because …," or "this is out of scope for this patch."
- **Don't take feedback personally**. Code review is the kernel's quality bar; criticism is professional, not personal.

If you go silent for >2 weeks after a review, your patch gets dropped from maintainers' queues. Stay engaged.

## 120A.11  Lore — search before you send

Lore.kernel.org is the public archive of every kernel mailing-list post since ~1998.

**Before** sending, search for:
- The file you're touching (`drivers/net/ethernet/freescale/fec_main.c`)
- The function name
- The bug symptom

```
https://lore.kernel.org/search?q=fec_main.c+phy+probe
```

You may discover: someone already proposed your fix and it was rejected for a reason; or there's a parallel discussion you should join; or the maintainer is mid-rework that supersedes your patch. Discovering this *before* sending saves embarrassment.

**`b4`** is a tool that simplifies series management:

```sh
pip install b4
b4 am https://lore.kernel.org/all/20260301...     # download a patch series locally
b4 prep -n my-series                                # start a new series for tracking
b4 send                                              # send via git send-email under the hood
b4 trailers                                          # collect Reviewed-by/Tested-by from replies
```

`b4` is increasingly standard in newer kernel work. Use it once you've sent your first patch the manual way.

## 120A.12  A worked example — adding a YAML binding for an existing chip

Suppose you wrote Ch 99's nRF24L01 user-space driver and want to upstream the *DT binding* (the actual kernel driver is out-of-tree but the binding is reusable):

```sh
# 1. Find the right path
ls Documentation/devicetree/bindings/net/wireless/
# atmel,*.yaml  marvell,*.yaml  ti,*.yaml  ...
# No nordic,nrf24*.yaml — opportunity.

# 2. Write the YAML
cat > Documentation/devicetree/bindings/net/wireless/nordic,nrf24l01p.yaml <<'EOF'
# SPDX-License-Identifier: (GPL-2.0-only OR BSD-2-Clause)
%YAML 1.2
---
$id: http://devicetree.org/schemas/net/wireless/nordic,nrf24l01p.yaml#
$schema: http://devicetree.org/meta-schemas/core.yaml#

title: Nordic nRF24L01+ 2.4 GHz radio

maintainers:
  - Your Name <you@example.com>

allOf:
  - $ref: spi-peripheral-props.yaml#

properties:
  compatible:
    enum:
      - nordic,nrf24l01p

  reg:
    maxItems: 1

  spi-max-frequency:
    maximum: 10000000

  ce-gpios:
    maxItems: 1
    description: Chip Enable pin (radio TX/RX activation)

  interrupts:
    maxItems: 1

required:
  - compatible
  - reg
  - ce-gpios
  - interrupts

unevaluatedProperties: false

examples:
  - |
    #include <dt-bindings/gpio/gpio.h>
    #include <dt-bindings/interrupt-controller/irq.h>

    spi {
        #address-cells = <1>;
        #size-cells = <0>;

        radio@0 {
            compatible = "nordic,nrf24l01p";
            reg = <0>;
            spi-max-frequency = <8000000>;
            ce-gpios = <&gpio4 27 GPIO_ACTIVE_HIGH>;
            interrupts-extended = <&gpio4 28 IRQ_TYPE_EDGE_FALLING>;
        };
    };
EOF

# 3. Validate the YAML
make ARCH=arm dt_binding_check DT_SCHEMA_FILES=Documentation/devicetree/bindings/net/wireless/nordic,nrf24l01p.yaml

# 4. Commit
git add Documentation/devicetree/bindings/net/wireless/nordic,nrf24l01p.yaml
git commit -s -m "dt-bindings: net: wireless: add nordic,nrf24l01p

The nRF24L01+ is a 2.4 GHz GFSK radio commonly used in low-cost
mesh and remote-control products. This adds a DT binding for
SPI-connected modules, used by community out-of-tree drivers as
well as user-space spidev-based stacks.

Signed-off-by: Your Name <you@example.com>"

# 5. Generate patch
git format-patch -1

# 6. Check
./scripts/checkpatch.pl --strict 0001-*.patch

# 7. Find maintainers
./scripts/get_maintainer.pl 0001-*.patch
# (DT bindings → Rob Herring + devicetree@vger.kernel.org)

# 8. Send
git send-email --to "Rob Herring <robh@kernel.org>" \
               --cc "Krzysztof Kozlowski <krzk+dt@kernel.org>" \
               --cc devicetree@vger.kernel.org \
               --cc linux-kernel@vger.kernel.org \
               0001-*.patch
```

DT bindings are one of the easiest categories to get merged — they're additive (don't break anything) and self-contained. Good first-patch target.

## 120A.13  Lab

1. **Find a typo.** Read a Documentation/ file (e.g., `Documentation/devicetree/bindings/`); find a real typo or grammatical fix; format-patch + checkpatch + send. Even 1-letter fixes get accepted (and add your name to git log).
2. **YAML binding.** Pick a chip from Part VII that doesn't have a binding yet (check `Documentation/devicetree/bindings/`); write + validate one; submit.
3. **b4 explorer.** Use `b4 am` to download a recent merged series from Lore; rebuild it locally; understand each patch.
4. **Lore search.** Search for a function name you're considering changing; read 5+ years of discussion; report what you learn.
5. **Send a bug report (not yet a patch).** If you found a real bug while reading Part VI/VII drivers, send a clear bug report to the maintainer + linux-* list. Maintainers love good bug reports.
6. **Set up git send-email.** Configure Gmail App Password; test-send a patch to yourself first to verify formatting.
7. **Read the responses.** Wait a week; read every reply on the list (subscribe via lore RSS); even if no one responds to your patch, watch how others handle review.
8. **v2 cycle.** Take a maintainer's feedback; produce v2 with a clear changelog. Carry forward Reviewed-by tags.
9. **Watch a merge.** Find an `Applied to` reply from a maintainer; check `git log` in the maintainer's tree for your patch's commit hash; trace it from there to Linus's mainline.

Commit your patches + emails sent + maintainer responses to `code/ch120A-patches/` (private; don't push if confidential).

## 120A.14  Pitfalls

- **HTML email.** Gmail's web UI sends HTML by default; mailing lists silently drop HTML patches. Use `git send-email` or plain-text mode.
- **Tabs vs spaces.** Some MUAs (Outlook, Thunderbird) helpfully convert tabs to spaces, mangling the patch. `git send-email` avoids this.
- **Reply-all to mailing lists.** When replying, hit Reply-all to keep the list CC'd. Off-list replies lose the discussion context.
- **Top-posting.** "I disagree, here's why" *above* the quoted message reverses reading order. Reply inline.
- **Spam-quoting.** Quoting the entire patch + entire prior reply in your response → 500-line emails. Trim aggressively.
- **Patch in attachment.** Mailing-list filters drop attachments. Inline only.
- **Subject line lacks subsystem prefix.** "Fix bug" gets ignored; "drivers/net/foo: fix NULL deref" gets read.
- **Missing Signed-off-by.** Patch is silently dropped.
- **Tested-on: my Pi.** Maintainers don't care unless reproducible by them. State: kernel version, defconfig, test method.
- **Multi-changes in one patch.** "Fix bug + cleanup + add feature" → maintainer asks you to split. Always one logical change per patch.
- **Sending and disappearing.** Patch sent, maintainer asks question, you don't respond for a month → patch is dropped. Stay engaged.
- **Ignoring DCO.** Every patch must be `Signed-off-by` your real legal name. Pseudonyms or company aliases without legal-real-name are usually rejected.
- **Wrong tree.** Submitting a USB patch against the staging tree → maintainer redirects you to `usb` tree. Get_maintainer.pl tells you the right tree; respect it.

## 120A.15  Going deeper

- **`Documentation/process/submitting-patches.rst`** — the canonical reference.
- **`Documentation/process/coding-style.rst`** — kernel C style.
- **`Documentation/process/email-clients.rst`** — how to configure every common MUA for kernel work.
- **`scripts/checkpatch.pl`, `scripts/get_maintainer.pl`** — read them; they're shell-helpers.
- **`b4` documentation** — https://b4.docs.kernel.org/.
- **Lore archive** — https://lore.kernel.org/.
- **LWN.net** — the periodical of kernel development; read weekly to absorb culture.
- **Kernel Mentees / Outreachy** — community programs for first-time contributors.
- **Greg Kroah-Hartman's "How to send patches to the Linux kernel"** — old but still essential.
- **Ch 121** — capstone custom-board port (your most-likely upstreamable contribution).

---

> Next chapter: **Chapter 121 — Capstone: custom board port**.
