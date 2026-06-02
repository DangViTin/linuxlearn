#!/usr/bin/env python3
"""
Fix the What / Why / Focus / Tooling preamble in chapter markdown files.

Background
----------
Most chapters open with a blockquote like::

    > **What:**    ...
    > **Why:**     ...
    > **Focus:**   ...
    > **Tooling.** ...
    > - bullet
    > - bullet

CommonMark joins consecutive blockquote lines (no blank line between them) into
one paragraph with soft line breaks — so the rendered HTML becomes a single
run-on sentence instead of four labeled paragraphs.

This script walks every ``*.md`` file under the book directory, finds those
run-on label lines, and inserts a blank ``>`` between them so each labeled
segment becomes its own paragraph. Bullet rows inside the blockquote
(``> - ...``) are left attached to whichever label they follow.

The script is idempotent — running it twice produces the same result.

Usage
-----
    python fix_preamble.py             # apply changes in-place
    python fix_preamble.py --dry-run   # just print what would change
    python fix_preamble.py --root book # scan a different directory
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# A blockquote line whose first content token is a **Bold label:** or
# **Bold label.**  — what we want to bump onto its own paragraph.
#   matches:  > **What:** ...
#             > **Tooling.** ...
LABEL_LINE = re.compile(r"^>\s+\*\*[A-Z][A-Za-z0-9\s/'\-]+[:.]\*\*")

# A blockquote "blank" line — just `>` (optionally with trailing whitespace).
BQ_BLANK_LINE = re.compile(r"^>\s*$")

# A blockquote content line — `>` followed by at least one non-whitespace char.
BQ_CONTENT_LINE = re.compile(r"^>\s+\S")


def fix_text(text: str) -> str:
    """Insert a blank `>` before every label line that follows another
    blockquote content line, so CommonMark renders the labels as separate
    paragraphs instead of merging them with soft line breaks."""
    lines = text.splitlines()
    out: list[str] = []
    for line in lines:
        if LABEL_LINE.match(line) and out and BQ_CONTENT_LINE.match(out[-1]):
            out.append(">")
        out.append(line)

    fixed = "\n".join(out)
    if text.endswith("\n"):
        fixed += "\n"
    return fixed


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--root",
        default="book",
        help="Directory to scan recursively for *.md files (default: book)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Don't write — just print the files that would change.",
    )
    args = parser.parse_args(argv)

    root = Path(args.root)
    if not root.is_dir():
        print(f"error: '{root}' is not a directory", file=sys.stderr)
        return 1

    scanned = 0
    changed = 0
    for md in sorted(root.rglob("*.md")):
        scanned += 1
        original = md.read_text(encoding="utf-8")
        updated = fix_text(original)
        if updated == original:
            continue
        changed += 1
        if args.dry_run:
            print(f"would fix: {md}")
        else:
            md.write_text(updated, encoding="utf-8")
            print(f"fixed:     {md}")

    verb = "would change" if args.dry_run else "changed"
    print(f"\nscanned {scanned} files, {verb} {changed}.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
