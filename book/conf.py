"""
Sphinx configuration for "Embedded Linux on i.MX6ULL".
Source files are Markdown (.md) read by MyST.  The theme is sphinx-rtd-theme.
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
    "status.md",         # only used as MkDocs placeholder; we use toctree now
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

# ---------------------------------------------------------------------------
# HTML output — Read the Docs theme
# ---------------------------------------------------------------------------
html_theme = "sphinx_rtd_theme"
html_theme_options = {
    # Navigation
    "navigation_depth": 3,
    "collapse_navigation": False,
    "sticky_navigation": True,
    "includehidden": True,
    "titles_only": False,
    # Branding
    "logo_only": False,
    "display_version": True,
    "prev_next_buttons_location": "both",
    "style_external_links": True,
    "style_nav_header_background": "#2980B9",
    # Add a hint of customization
    "vcs_pageview_mode": "edit",
}

html_static_path = ["_static"]
html_css_files = ["custom.css"]

# Sidebar logo / favicon (optional — drop into book/_static/ to enable)
# html_logo = "_static/logo.svg"
# html_favicon = "_static/favicon.ico"

html_title = f"{project}"
html_short_title = "i.MX6ULL Linux"
html_show_sourcelink = True
html_show_sphinx = False    # remove "Built with Sphinx" footer
html_copy_source = False

# Make the "Edit on GitHub" link work
html_context = {
    "display_github": True,
    "github_user": "DangViTin",
    "github_repo": "linuxlearn",
    "github_version": "main",
    "conf_py_path": "/book/",
}

# ---------------------------------------------------------------------------
# Code highlighting
# ---------------------------------------------------------------------------
pygments_style = "default"
highlight_language = "c"  # default; per-block overrides still work
