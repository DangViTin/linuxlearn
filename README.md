# Embedded Linux on i.MX6ULL — From First Boot to First Driver

The Raw Approach: build it yourself, understand it forever.

> **📖 Read online: <https://example.github.io/linuxlearn/>** *(URL updates to your username after first push — see [PUBLISH.md](PUBLISH.md))*

## What this is

A ~2,470-page **online guide** for engineers who already write firmware for microcontrollers and want to take a first-principles approach to embedded Linux. The full stack — from the reset vector to OTA + secure boot + CI/CD — covered in 141 chapters across 8 Parts, with every register dance, kernel API, and DT binding explained, never hidden behind a framework you can't see through.

This is a **guide**, not a code-companion repository. All code listings are inline in the chapters — copy-paste-ready, but the goal is that you read them, understand them, and type them by hand on your own board.

## Repository layout

```
LinuxLearn/
├── BOOK_TOC.md                  # Master table of contents (the canonical scope)
├── README.md                    # This file
├── PUBLISH.md                   # How to publish the site online (10-min setup)
├── requirements-docs.txt        # Sphinx + theme + MyST, pinned versions
├── Makefile                     # Sphinx build entry points
├── .github/workflows/
│   └── docs.yml                 # Build with sphinx-build, deploy to Pages on push
├── book/                        # Chapter source + Sphinx source root
│   ├── conf.py                  # Sphinx configuration
│   ├── _static/custom.css       # Theme overrides
│   ├── index.md                 # Site landing page + sidebar toctree
│   ├── toc.md                   # Mirror of BOOK_TOC.md
│   ├── status.md                # Placeholder for not-yet-drafted parts
│   ├── part1-foundations/       # Ch 1–8
│   ├── part2-baremetal/         # Ch 9–18 + 18A/B/C
│   ├── part3-uboot/             # Ch 19–24 + 23A
│   ├── part4-kernel/            # Ch 25–30 + 27A/30A
│   ├── part5-rootfs/            # Ch 31–35 + 35A/B/C
│   ├── part6-drivers/           # Ch 36–55 + 51A/B, 52A, 54A/B, 55A–I
│   ├── part7-cookbook/          # Ch 64–117 (54-chapter device cookbook)
│   └── part7-debug/             # Part VIII — Ch 118–126 + 120A/121A/122A/123A/125A
├── reference_docs/              # Internal-only: source PDFs (Point Atom guides, NXP RM)
│                                # NOT redistributed; used only as research inputs
└── build/                       # Sphinx HTML output — gitignored
```

## Target board

**i.MX6ULL on Point Atom MINI** (正点原子 ALPHA-MINI, also abbreviated ATK MINI) — i.MX6ULL Cortex-A7 @ 696 MHz, 512 MiB DDR3L.

The guide is written against the MINI, but **most of the content generalizes** to:
- Any i.MX6ULL-based board (ATK ALPHA, NXP EVK, vendor BSPs).
- Any Cortex-A7 SoC for Parts I + IV + V + VI + VIII (kernel, rootfs, drivers, debug, production).
- Any Linux-capable ARM SoC for Parts IV–VIII (the kernel/userspace/process chapters are SoC-agnostic).

Hardware-specific content lives in Parts II (bare-metal) and III (U-Boot port); pin assignments and register addresses are i.MX6ULL-specific. Everything else transfers.

## Reading the book

**Online (after publish):** <https://YOUR-USERNAME.github.io/linuxlearn/>

**Locally with live reload:** see [PUBLISH.md §"Preview locally"](PUBLISH.md#preview-locally-before-pushing-optional-but-recommended).

**Or just read the Markdown:** every chapter is a self-contained `.md` file in `book/`. Render in your editor, or browse on GitHub once pushed.

Recommended path:
1. Start with [Chapter 1 — Preface](book/part1-foundations/ch01-preface.md) for philosophy and the seven-section chapter template.
2. [Chapter 2 — What "Embedded Linux" actually is](book/part1-foundations/ch02-what-is-embedded-linux.md) for vocabulary.
3. Follow Parts I + II in order — they build on each other and labs assume prior chapters.
4. Parts VI's driver chapters and Part VII's cookbook chapters are largely sibling-independent — pick what you need.

## Host environment

Native **Ubuntu 22.04 LTS** or Debian 12. WSL2 will mostly work but is not the primary test target; USB-OTG passthrough and serial-port behavior are the friction points.

## Publishing the book online

See **[PUBLISH.md](PUBLISH.md)** — ≈10 minutes one-time setup. Zero cost. Auto-rebuild on every push. Free GitHub Pages hosting via Sphinx + `furo` + `myst-parser` (dark-mode-aware, VS-Code-style code highlighting, hideable sidebar with `Ctrl+B`).

After setup, the day-to-day workflow is:

```sh
git add book/
git commit -m "..."
git push                   # site rebuilds automatically; live in ~30 s
```

## Licensing

- **Guide prose** (`book/` tree): **CC-BY-SA-4.0** — read, share, adapt, attribute.
- **Inline code listings** (snippets embedded in chapters): **MIT** — copy into your projects without attribution required.
- **`reference_docs/`** — not in the license above; these are third-party source documents (Point Atom guides, NXP Reference Manual, NXP datasheet, NXP errata) retained for research only and **not redistributed** with the site build.

## Status

| Part | Status | Chapters | Est. pages |
|------|--------|----------|-----------|
| TOC | ✅ Complete (v1.3) | 141 | — |
| Part I — Foundations | ✅ Drafted | 8 | ~136 |
| Part II — Bare-metal i.MX6ULL | ✅ Drafted | 10 + 3 supp. | ~252 |
| Part III — U-Boot | ✅ Drafted | 6 + 1 supp. | ~128 |
| Part IV — The Kernel | ✅ Drafted | 6 + 2 supp. | ~148 |
| Part V — Rootfs & user space | ✅ Drafted | 5 + 3 supp. | ~140 |
| Part VI — Driver development | ✅ Drafted | 20 + 13 supp. | ~644 |
| Part VII — Device cookbook | ✅ Drafted | 54 | ~735 |
| Part VIII — Debug, production | ✅ Drafted | 9 + 5 supp. | ~290 |
| **Total** | **✅ Full first draft** | **141** | **~2,473** |

Next phase: technical-review pass, copy edit, then release-candidate. See the end of [Chapter 126](book/part7-debug/ch126-closing.md) and the issues tracker.

## Contributing

This is a one-author project at the moment, but errata, broken-link reports, technical corrections, and clarification suggestions are welcome via GitHub Issues (after first publish).
