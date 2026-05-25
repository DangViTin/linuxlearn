# Publishing this book online

We use **MkDocs Material + GitHub Pages**. Free. No server. Auto-rebuilds on every push.

Once set up, the site lives at:

```
https://<your-github-username>.github.io/linuxlearn/
```

You can read it on a laptop, phone, tablet — anything with a browser.

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

### 2. From the project root, initialize git and create the repo

```sh
cd ~/imx6ull/LinuxLearn        # or wherever this folder lives
git init -b main
git add .
git commit -m "Initial commit: Parts I and II drafted; MkDocs Material site"

# Public repo named `linuxlearn` under your user account
gh repo create linuxlearn --public --source=. --remote=origin --push
```

That single `gh repo create` command does five things: makes the GitHub repo, adds it as `origin`, pushes `main`, sets the description, and opens the repo page in your browser.

### 3. Fix the placeholder URLs in `mkdocs.yml`

After step 2 you know your GitHub username. Open `mkdocs.yml` and replace **`example`** with it in three places:

```yaml
site_url: https://YOUR-USERNAME.github.io/linuxlearn/
repo_url: https://github.com/YOUR-USERNAME/linuxlearn
repo_name: YOUR-USERNAME/linuxlearn
```

And in `book/index.md`, replace `https://github.com/example/linuxlearn` with the same.

Commit and push:

```sh
git add mkdocs.yml book/index.md
git commit -m "Update site_url and repo links"
git push
```

### 4. Enable GitHub Pages

Either via the CLI:

```sh
gh api -X POST repos/:owner/linuxlearn/pages -f "build_type=workflow"
```

Or via the web UI: open `https://github.com/YOUR-USERNAME/linuxlearn/settings/pages`, under **Build and deployment → Source**, choose **"GitHub Actions"**, save.

That's it. The `.github/workflows/docs.yml` workflow runs on every push to `main` and publishes to GitHub Pages.

### 5. Watch the first build

```sh
gh run watch
```

Or open `https://github.com/YOUR-USERNAME/linuxlearn/actions`. The first run takes ~2 minutes (installing MkDocs); subsequent builds are ~30 seconds.

When the run goes green, the site is live at:

```
https://YOUR-USERNAME.github.io/linuxlearn/
```

---

## Day-to-day workflow

After the one-time setup:

```sh
# edit a chapter
vim book/part1-foundations/ch01-preface.md

# commit and push
git add book/
git commit -m "Ch 1: rewrite the slow-book closing paragraph"
git push
```

GitHub Action rebuilds the site automatically. Refresh the URL in your browser ~30 seconds later.

---

## Preview locally before pushing (optional but recommended)

```sh
# One-time: install MkDocs locally
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements-docs.txt

# Mirror the TOC (the GitHub Action does this automatically; locally we do it by hand)
cp BOOK_TOC.md book/toc.md

# Live-reload server
mkdocs serve
```

Open <http://127.0.0.1:8000/> in your browser. Edit a chapter; the page refreshes automatically.

When done, deactivate the venv:

```sh
deactivate
```

---

## Customization quick reference

| Want to change... | Edit... |
|-------------------|---------|
| Site name / description | `mkdocs.yml` → `site_name`, `site_description` |
| Brand color | `mkdocs.yml` → `theme.palette.primary` (try `indigo`, `teal`, `red`, `green`, `deep purple`) |
| Light/dark mode default | `mkdocs.yml` → palette ordering |
| Navigation order | `mkdocs.yml` → `nav:` |
| Add a new chapter | drop the `.md` in `book/partX-.../` and add the line under `nav:` |
| Logo / favicon | place files in `book/assets/` and reference them in `mkdocs.yml → theme.logo / theme.favicon` |
| Custom CSS / JS | `mkdocs.yml → extra_css:` / `extra_javascript:`, files in `book/assets/` |

---

## Adding versioned releases (optional, advanced)

Once you ship a "v1.0," "v1.1," etc., the **`mike`** tool (already in `requirements-docs.txt`) lets you publish multiple site versions side-by-side at:

- `https://YOUR-USERNAME.github.io/linuxlearn/` (latest)
- `https://YOUR-USERNAME.github.io/linuxlearn/v1.0/`
- `https://YOUR-USERNAME.github.io/linuxlearn/v1.1/`

To activate, replace the build step in `.github/workflows/docs.yml` with:

```yaml
- run: mike deploy --push --update-aliases v1.2 latest
```

This is optional and not needed for the first publish.

---

## Custom domain (optional)

If you have a domain you'd like to use (`embedded-linux.example.com`):

1. In your DNS provider, add a `CNAME` record pointing to `YOUR-USERNAME.github.io`.
2. In the repo: `https://github.com/YOUR-USERNAME/linuxlearn/settings/pages` → **Custom domain** → enter it → save.
3. GitHub Actions will write a `CNAME` file into the deployed site and serve under HTTPS via Let's Encrypt.

Free for any domain you already own.

---

## If something goes wrong

- **Action fails with "Pages not enabled"** → finish step 4.
- **Action fails with "mkdocs.yml: invalid YAML"** → check indentation; YAML is whitespace-sensitive.
- **Site shows but pages 404** → check the `nav:` paths in `mkdocs.yml` are relative to `book/` (no leading `book/`).
- **Frontmatter shows up as plain text at the top of each chapter** → MkDocs Material parses YAML front matter natively when the `meta` extension is enabled. If yours doesn't, upgrade to the pinned version in `requirements-docs.txt`.
- **Want to test the build locally without pushing** → run `mkdocs build --strict` and it errors out the same way the Action does.
