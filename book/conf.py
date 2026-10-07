"""
Sphinx configuration for "Embedded Linux on i.MX6ULL".
Source files are Markdown (.md) read by MyST.  The theme is Furo (modern,
dark-mode-aware, mobile-responsive, fork of pydata-sphinx-theme).
"""

import os
import sys
from datetime import datetime

from bs4 import BeautifulSoup
from pygments.lexer import inherit
from pygments.lexers.asm import GasLexer
from pygments.token import Comment, Name, Operator

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

root_doc = "part1-foundations/ch01-preface"
templates_path = ["_templates"]
html_additional_pages = {"index": "start.html.jinja"}

# Patterns to exclude
exclude_patterns = [
    "_build",
    "_navigation.md",  # included by Chapter 1, not a separate reading page
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

# Product names such as i.MX are not scheme-less website addresses.
myst_linkify_fuzzy_links = False

# Pygments does not fully understand several book-specific snippets
# (linker scripts, FIT .its files, BitBake recipes). Keep rendering them as
# code without reporting those lexer limitations as documentation defects.
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
    "light_css_variables": {
        "color-brand-primary": "#126b5e",
        "color-brand-content": "#0c6859",
        "color-foreground-primary": "#242b30",
        "color-foreground-secondary": "#52616b",
        "color-background-primary": "#ffffff",
        "color-background-secondary": "#f3f6f7",
        "color-background-border": "#dfe5e8",
        "color-sidebar-background": "#f5f7f8",
        "color-sidebar-background-border": "#dfe5e8",
        "color-sidebar-item-background--current": "#e3f1eb",
        "color-sidebar-link-text--top-level": "#35434c",
        "color-sidebar-link-text--top-level--current": "#0b5b4c",
        "color-admonition-background": "#f3f6f7",
    },
    "dark_css_variables": {
        "color-brand-primary": "#78dbbd",
        "color-brand-content": "#78dbbd",
        "color-foreground-primary": "#e6ecef",
        "color-foreground-secondary": "#b8c3ca",
        "color-background-primary": "#171b1e",
        "color-background-secondary": "#21272b",
        "color-background-border": "#364148",
        "color-sidebar-background": "#1c2226",
        "color-sidebar-background-border": "#364148",
        "color-sidebar-item-background--current": "#253c34",
        "color-sidebar-link-text--top-level": "#c3cdd3",
        "color-sidebar-link-text--top-level--current": "#9be8cd",
        "color-admonition-background": "#21272b",
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
html_sidebars = {"**": [
    "sidebar/brand.html", "sidebar/search.html", "sidebar/download.html",
    "sidebar/scroll-start.html", "sidebar/navigation.html",
    "sidebar/ethical-ads.html", "sidebar/scroll-end.html", "sidebar/variant-selector.html",
]}

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


class ArmGasLexer(GasLexer):
    """Adapt the GAS highlighter to the book's GNU Arm assembly listings."""

    tokens = {
        "root": [
            (r"@[^\n]*", Comment.Single),
            (r"[0-9]+:", Name.Label),
            inherit,
        ],
        "instruction-args": [
            (r"@[^\n]*", Comment.Single),
            # Arm uses # for immediates and = for literal-pool loads.
            (r"[=#<>+|&^~]+", Operator),
            inherit,
        ],
        "directive-args": [
            (r"@[^\n]*", Comment.Single),
            (r"%[A-Za-z_][\w.]*", Name.Attribute),
            inherit,
        ],
    }


def include_first_chapter(app, pagename, templatename, context, doctree):
    # Adding the root to Sphinx's toctree would create a circular reading order.
    navigation = context.get("furo_navigation_tree")
    if not navigation:
        return
    tree = BeautifulSoup(navigation, "html.parser")
    foundations = tree.find("ul")
    if foundations is None:
        return
    current = pagename == app.config.root_doc
    item = tree.new_tag("li", attrs={"class": ["toctree-l1", "book-start"]})
    link = tree.new_tag("a", href=context["pathto"](app.config.root_doc), attrs={"class": ["reference", "internal"]})
    link.string = app.env.titles[app.config.root_doc].astext()
    if current:
        item["class"] += ["current", "current-page"]
        link["class"].append("current")
        foundations["class"] = foundations.get("class", []) + ["current"]
    item.append(link)
    foundations.insert(0, item)
    for active in tree.select(".current-page > a"):
        active["aria-current"] = "page"
    for heading in tree.select('.caption[role="heading"]'):
        heading["aria-level"] = "2"
    context["furo_navigation_tree"] = str(tree)


def prepare_sketch_images(app, pagename, templatename, context, doctree):
    body = context.get("body", "")
    if "concept-sketch" not in body:
        return
    fragment = BeautifulSoup(body, "html.parser")
    for sketch in fragment.select("figure.concept-sketch img"):
        sketch["loading"] = "lazy"
        sketch["decoding"] = "async"
    context["body"] = str(fragment)


def setup(app):
    app.add_lexer("asm", ArmGasLexer)
    app.connect("html-page-context", include_first_chapter, priority=600)
    app.connect("html-page-context", prepare_sketch_images, priority=610)
