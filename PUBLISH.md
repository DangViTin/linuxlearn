# Publishing this book online

We use **Sphinx + sphinx-rtd-theme + MyST-Parser** to render the Markdown into a clean Read-the-Docs-style site, then **GitHub Pages** hosts it. Free, no server, auto-rebuilds on every push.

Site URL after the GitHub Action runs:

```
https://<your-github-username>.github.io/linuxlearn/
```

Mobile-friendly, full text search, prev/next page navigation, copy-button on every code block.

---

## One-time setup (≈10 minutes)

### 1. Install GitHub CLI (if you don't have it)

```sh
# Ubuntu / Debian
sudo apt install gh
# macOS
brew install gh
# Windows
winget install --id GitHub.cli
```

Then log in:

```sh
gh auth login
```

### 2. Create the repo and push

```sh
cd ~/imx6ull/LinuxLearn        # or wherever this folder lives
git init -b main
git add .
git commit -m "Initial commit"
gh repo create linuxlearn --public --source=. --remote=origin --push
```

The single `gh repo create` line creates the GitHub repo, sets `origin`, and pushes.

### 3. Edit your username into `book/conf.py`

Open `book/conf.py` and find:

```python
html_context = {
    "display_github": True,
    "github_user": "DangViTin",      # <— change to your username
    "github_repo": "linuxlearn",
    "github_version": "main",
    "conf_py_path": "/book/",
}
```

Replace `DangViTin` with your GitHub username. Commit and push:

```sh
git add book/conf.py
git commit -m "Update github_user for site"
git push
```

### 4. Enable GitHub Pages

CLI:

```sh
gh api -X POST repos/:owner/linuxlearn/pages -f "build_type=workflow"
```

Or web: `https://github.com/YOUR-USERNAME/linuxlearn/settings/pages` → **Build and deployment → Source → "GitHub Actions"** → save.

### 5. Watch the first build

```sh
gh run watch
```

Or check `https://github.com/YOUR-USERNAME/linuxlearn/actions`. First run takes ~90 seconds; subsequent builds ~25 seconds.

When the run goes green, the site is live at:

```
https://YOUR-USERNAME.github.io/linuxlearn/
```

---

## Day-to-day workflow

```sh
# edit a chapter
vim book/part1-foundations/ch01-preface.md

# commit and push
git add book/
git commit -m "Ch 1: tighten the closing"
git push
```

GitHub Action rebuilds the site automatically. Refresh the URL ~30 seconds later.

---

## Preview locally before pushing (recommended)

```sh
# One-time: create a venv and install dependencies
python -m venv .venv
source .venv/bin/activate                   # Windows: .venv\Scripts\Activate.ps1
pip install -r requirements-docs.txt

# Mirror the TOC (the GitHub Action does this automatically; locally we do it by hand)
cp BOOK_TOC.md book/toc.md

# Live build with auto-rebuild on file save
sphinx-autobuild book book/_build/html
```

Open <http://127.0.0.1:8000/> in your browser. Edit a chapter; the page refreshes automatically.

For a one-shot build without the dev server:

```sh
sphinx-build -b html book book/_build/html
```

Then open `book/_build/html/index.html` directly.

To deactivate the venv when done:

```sh
deactivate
```

---

## Customization quick reference

| Want to change... | Edit... |
|-------------------|---------|
| Site title / author / version | `book/conf.py` → `project`, `author`, `release` |
| Theme colors | `book/_static/custom.css` (already wired in) |
| Sidebar header background | `book/conf.py` → `html_theme_options.style_nav_header_background` |
| Navigation depth | `book/conf.py` → `html_theme_options.navigation_depth` |
| Add a new chapter | drop the `.md` in `book/partX-.../` and add the filename (without `.md`) under the matching `toctree` in `book/index.md` |
| Sidebar logo / favicon | drop files into `book/_static/`, then set `html_logo` and `html_favicon` in `conf.py` |

---

## File map

| File | Purpose |
|------|---------|
| `book/conf.py` | Sphinx configuration |
| `book/index.md` | Site landing page + sidebar toctree |
| `book/_static/custom.css` | Theme tweaks (font sizes, sidebar color, etc.) |
| `book/part*-*/ch*.md` | Chapter content (Markdown, untouched) |
| `book/toc.md` | Auto-generated each build from `BOOK_TOC.md` |
| `requirements-docs.txt` | Sphinx + extensions, pinned |
| `.github/workflows/docs.yml` | Build + deploy on every push to main |

---

## Custom domain (optional)

If you have your own domain:

1. In your DNS provider, add a `CNAME` record pointing to `YOUR-USERNAME.github.io`.
2. Repo → **Settings → Pages → Custom domain** → enter it → save.
3. The Action will write a `CNAME` file into the deployed site and serve under HTTPS via Let's Encrypt.

---

## If something goes wrong

- **Build fails: "could not find file foo"** — a path in `book/index.md`'s `toctree` doesn't match an actual file. Check the spelling (no `.md` extension in toctree entries).
- **Build fails: "duplicate toctree"** — a chapter is listed in two different toctrees. Each file may appear in exactly one toctree.
- **Site shows but looks unstyled** — Pages enabled before the first successful build. Re-run the workflow: `gh workflow run docs.yml`.
- **Action fails with "Pages not enabled"** → finish step 4.
- **Local `sphinx-autobuild` not found** → it ships with Sphinx but in some installs is a separate package: `pip install sphinx-autobuild`.

---

## Migrating from a previous MkDocs setup

If you used MkDocs Material before:

```sh
git rm mkdocs.yml                  # already removed by the migration commit
# requirements-docs.txt is now Sphinx-based; pip-install fresh in your venv:
pip install -r requirements-docs.txt --upgrade
```

No chapter `.md` files needed changes. The site URL stays the same.
