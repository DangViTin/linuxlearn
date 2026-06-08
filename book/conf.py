"""
Sphinx configuration for "Embedded Linux on i.MX6ULL".
Source files are Markdown (.md) read by MyST.  The theme is Furo (modern,
dark-mode-aware, mobile-responsive, fork of pydata-sphinx-theme).
"""

import os
import sys
from datetime import datetime

# ---------------------------------------------------------------------------
# Project metadata
# ---------------------------------------------------------------------------
project = "Embedded Linux on i.MX6ULL"
author = "DangViTin"
copyright = f"{datetime.now().year}, {author}"
release = "1.2"
version = release

# ---------------------------------------------------------------------------
# Extensions
# ---------------------------------------------------------------------------
extensions = [
    "myst_parser",          # Markdown support
    "sphinx_copybutton",    # "Copy" button on code blocks
    "sphinx_design",        # Tabs, cards, grids (optional but useful)
]

# Files to find
source_suffix = {
    ".md": "markdown",
    ".rst": "restructuredtext",
}

master_doc = "index"

# Patterns to exclude
exclude_patterns = [
    "_build",
    "Thumbs.db",
    ".DS_Store",
]

# ---------------------------------------------------------------------------
# MyST configuration
# ---------------------------------------------------------------------------
myst_enable_extensions = [
    "colon_fence",       # ::: fenced blocks for admonitions
    "deflist",           # definition lists
    "tasklist",          # GitHub-style task lists
    "fieldlist",         # field lists
    "linkify",           # auto-link bare URLs
    "substitution",      # variable substitution
    "html_admonition",   # raw HTML admonitions
    "html_image",        # <img> tags
    "attrs_inline",      # inline attributes
    "smartquotes",       # smart quotes
]

# Auto-create header anchors so [link text](file.md#section) works
myst_heading_anchors = 4

# Permit URL fragments without strict checking
myst_url_schemes = ("http", "https", "mailto", "ftp")

# Pygments does not fully understand several book-specific snippets
# (GNU ARM assembly with literal pools, linker scripts, FIT .its files,
# BitBake recipes). Keep rendering them as code, but do not make those
# lexer limitations look like documentation defects in CI output.
suppress_warnings = [
    "misc.highlighting_failure",
]

# ---------------------------------------------------------------------------
# HTML output — Furo theme
# ---------------------------------------------------------------------------
html_theme = "furo"

# Furo handles dark/light mode automatically based on the user's OS preference,
# with a manual toggle in the page header. The colour palette is overridable
# via CSS variables — see _static/custom.css.
html_theme_options = {
    # Show "View on GitHub" link in the right ToC (Furo's edit-source feature).
    "source_repository": "https://github.com/DangViTin/linuxlearn/",
    "source_branch": "main",
    "source_directory": "book/",
    # A subtle accent for both light + dark — readable, low saturation.
    "light_css_variables": {
        "color-brand-primary": "#2563eb",      # blue-600
        "color-brand-content": "#2563eb",
        "color-admonition-background": "#f5f7fb",
    },
    "dark_css_variables": {
        "color-brand-primary": "#60a5fa",      # blue-400 — easier on dark BG
        "color-brand-content": "#60a5fa",
        "color-admonition-background": "#1c2434",
    },
    # Behaviour
    "sidebar_hide_name": False,
    "navigation_with_keys": True,    # j/k or arrow keys to navigate
    "top_of_page_buttons": ["view", "edit"],
    "footer_icons": [
        {
            "name": "GitHub",
            "url": "https://github.com/DangViTin/linuxlearn",
            "html": (
                '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16">'
                '<path fill="currentColor" d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59'
                '.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23'
                '-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87'
                '.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59'
                '.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27'
                '.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56'
                '.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 '
                '1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0016 8c0-4.42-3.58-8-8-8z"/>'
                '</svg>'
            ),
            "class": "",
        },
    ],
}

html_static_path = ["_static"]
html_css_files = ["custom.css"]
html_js_files = ["custom.js"]

# Sidebar logo / favicon (optional — drop into book/_static/ to enable)
# html_logo = "_static/logo.svg"
# html_favicon = "_static/favicon.ico"

html_title = f"{project}"
html_short_title = "i.MX6ULL Linux"
html_show_sourcelink = True
html_show_sphinx = False    # remove "Built with Sphinx" footer
html_copy_source = False

# ---------------------------------------------------------------------------
# Code highlighting — VS Code-style themes for light + dark
# ---------------------------------------------------------------------------
# Pygments style for the LIGHT theme. "tango" is closest to VS Code Light+.
pygments_style = "tango"
# Pygments style for the DARK theme (Furo-specific).
# "github-dark" matches VS Code Dark+ closely; "monokai" and "one-dark" are
# also reasonable. github-dark is the most VSCode-like.
pygments_dark_style = "github-dark"

# Default to "none" so plain prompt examples and ASCII diagrams aren't lexed
# as some specific language.  Code blocks that DO specify a language (```c,
# ```sh, ```make, ```asm, ...) still get highlighted normally.
highlight_language = "none"
