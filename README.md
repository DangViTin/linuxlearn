# Embedded Linux on i.MX6ULL — From First Boot to First Driver

The Raw Approach: build it yourself, understand it forever.

> **📖 Read online: <https://example.github.io/linuxlearn/>** *(URL updates to your username after first push — see [PUBLISH.md](PUBLISH.md))*

## What's in this repository

This is the source of a ~1,700-page book in progress. The repo holds:

- The Markdown source under `book/`
- The master TOC `BOOK_TOC.md`
- A working **MkDocs Material** site that publishes itself to GitHub Pages on every push (see [PUBLISH.md](PUBLISH.md) for the one-time setup)

## Repository layout

```
LinuxLearn/
├── BOOK_TOC.md              # Master table of contents (the master copy)
├── README.md                # This file
├── PUBLISH.md               # How to publish the site online (10-min setup)
├── mkdocs.yml               # MkDocs Material configuration
├── requirements-docs.txt    # Python dependencies for building the site
├── .github/workflows/
│   └── docs.yml             # Auto-build & deploy to GitHub Pages on push
├── book/                    # Chapter source (Markdown) — also the docs_dir
│   ├── index.md             # Site landing page
│   ├── toc.md               # Auto-mirrored from BOOK_TOC.md on build
│   ├── status.md            # "Coming soon" stub for undrafted Parts
│   ├── part1-foundations/
│   ├── part2-baremetal/
│   ├── part3-uboot/         # (empty; not yet drafted)
│   ├── part4-kernel/        # (empty)
│   ├── part5-rootfs/        # (empty)
│   ├── part6-drivers/       # (empty)
│   └── part7-debug/         # (empty)
├── code/                    # Companion source (MIT / Apache-2.0); ch by ch
├── figures/                 # Diagrams, schematics, screenshots
└── site/                    # MkDocs build output — gitignored
```

## Reading the book

**Online (after publish):** <https://YOUR-USERNAME.github.io/linuxlearn/>

**Locally with live reload:** see [PUBLISH.md §"Preview locally"](PUBLISH.md#preview-locally-before-pushing-optional-but-recommended).

**Or just read the Markdown:** every chapter is a self-contained `.md` file in `book/`. Render in your editor, or browse on GitHub once pushed.

## Target board

**Point Atom (正点原子) i.MX6ULL MINI** — i.MX6ULL @ 696 MHz, 512 MiB DDR3L, slim peripheral set.

ALPHA is fully supported with sidebars where peripherals differ. See [Chapter 5 §5.9a](book/part1-foundations/ch05-imx6ull-tour.md#59a-point-atom-alpha-vs-mini--whats-on-each-board) for the exact peripheral comparison.

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
| TOC | ✅ Complete — v1.2 (64 numbered + 23 inserted = 87 chapters) | — |
| Part I — Foundations | ✅ Drafted (Ch 1–8, patched v1.1 + v1.2) | ~136 |
| Part II — Bare-metal | ✅ Drafted (Ch 9–18 + inserted 18A / 18B / 18C) | ~252 |
| Part III — U-Boot | ⬜ Not yet drafted (6 numbered + 1 insert: 23A) | ~128 |
| Part IV — Kernel | ⬜ Not yet drafted (6 numbered + 2 inserts: 27A, 30A) | ~148 |
| Part V — Rootfs | ⬜ Not yet drafted (5 numbered + 3 inserts: 35A, B, C) | ~140 |
| Part VI — Drivers | ⬜ Not yet drafted (20 numbered + 13 inserts: 51A–55I) | ~644 |
| Part VII — Debug, production | ⬜ Not yet drafted (9 numbered + 5 inserts: 58A–63A) | ~290 |
| **Total drafted: ~388 pp of ~1,738 pp planned (~22 %)** | | |
