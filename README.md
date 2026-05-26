# Embedded Linux on i.MX6ULL — From First Boot to First Driver

The Raw Approach: build it yourself, understand it forever.

> **📖 Read online: <https://example.github.io/linuxlearn/>** *(URL updates to your username after first push — see [PUBLISH.md](PUBLISH.md))*

## What's in this repository

This is the source of a ~1,700-page book in progress. The repo holds:

- The Markdown source under `book/`
- The master TOC `BOOK_TOC.md`
- A **Sphinx + sphinx-rtd-theme** site that publishes itself to GitHub Pages on every push (see [PUBLISH.md](PUBLISH.md) for the one-time setup)

## Repository layout

```
LinuxLearn/
├── BOOK_TOC.md              # Master table of contents
├── README.md                # This file
├── PUBLISH.md               # How to publish the site online (10-min setup)
├── requirements-docs.txt    # Sphinx + theme + MyST, pinned versions
├── .github/workflows/
│   └── docs.yml             # Build with sphinx-build, deploy to Pages on push
├── book/                    # Chapter source AND Sphinx source root
│   ├── conf.py              # Sphinx configuration
│   ├── _static/custom.css   # Theme overrides (fonts, colors, spacing)
│   ├── index.md             # Site landing page + sidebar toctree
│   ├── toc.md               # Auto-mirrored from BOOK_TOC.md on build
│   ├── part1-foundations/   # Ch 1–8 (drafted)
│   ├── part2-baremetal/     # Ch 9–18 + 18A/B/C (drafted)
│   ├── part3-uboot/         # Ch 19–24 + 23A (drafted)
│   ├── part4-kernel/        # (not yet drafted)
│   ├── part5-rootfs/        # (not yet drafted)
│   ├── part6-drivers/       # (not yet drafted)
│   └── part7-debug/         # (not yet drafted)
├── code/                    # Companion source (MIT / Apache-2.0); ch by ch
├── figures/                 # Diagrams, schematics, screenshots
└── book/_build/             # Sphinx HTML output — gitignored
```

## Reading the book

**Online (after publish):** <https://YOUR-USERNAME.github.io/linuxlearn/>

**Locally with live reload:** see [PUBLISH.md §"Preview locally"](PUBLISH.md#preview-locally-before-pushing-optional-but-recommended).

**Or just read the Markdown:** every chapter is a self-contained `.md` file in `book/`. Render in your editor, or browse on GitHub once pushed.

## Target board

**i.MX6ULL on Point Atom MINI** — i.MX6ULL @ 696 MHz, 512 MiB DDR3L, slim peripheral set.

ALPHA is fully supported with sidebars where peripherals differ. See Chapter 5 §5.9a for the per-peripheral table.

## Host environment

Native **Ubuntu 22.04 LTS** or Debian 12. WSL2 will mostly work but is not tested; USB-OTG and serial pass-through are the friction points.

## Publishing the book online

See **[PUBLISH.md](PUBLISH.md)** — ≈10 minutes one-time setup. Zero cost. Auto-rebuild on every push. Free GitHub Pages hosting.

After setup, the day-to-day workflow is:

```sh
git add book/
git commit -m "..."
git push                   # site rebuilds automatically; live in ~30 s
```

## Licensing

- **Book prose** (the `book/` tree): CC-BY-SA-4.0 *(tentative — finalized before public release)*
- **Companion code** (the `code/` tree): MIT OR Apache-2.0, except chapters that touch GPL'd kernel code which inherit GPL-2.0-only

## Status

| Part | Status | Pages |
|------|--------|-------|
| TOC | ✅ Complete — v1.3 (118 numbered + 23 inserted = 141 chapters) | — |
| Part I — Foundations | ✅ Drafted (Ch 1–8, patched v1.1 + v1.2) | ~136 |
| Part II — Bare-metal | ✅ Drafted (Ch 9–18 + inserted 18A / 18B / 18C) | ~252 |
| Part III — U-Boot | ✅ Drafted (Ch 19–24 + inserted 23A) | ~128 |
| Part IV — Kernel | ✅ Drafted (Ch 25–30 + inserted 27A, 30A) | ~148 |
| Part V — Rootfs | ✅ Drafted (Ch 31–35 + inserted 35A, 35B, 35C) | ~140 |
| Part VI — Drivers | 🟡 Drafting (Ch 36–43 done; 44–55I + inserts pending) | ~644 |
| Part VII — Device cookbook | ⬜ Not yet drafted (54 chapters, Ch 64–117) | ~735 |
| Part VIII — Debug, production | ⬜ Not yet drafted (9 numbered + 5 inserts: 120A–125A) | ~290 |
| **Total drafted: ~944 pp of ~2,473 pp planned (~38 %)** | | |
