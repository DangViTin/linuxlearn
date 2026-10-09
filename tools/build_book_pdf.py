"""Export the Sphinx reading order as one offline, linked PDF."""

import argparse
from datetime import datetime, timezone
import json
import logging
from pathlib import Path
import re
import tempfile
from urllib.parse import unquote, urljoin, urlsplit

from bs4 import BeautifulSoup
import pikepdf
from pypdf import PdfReader
from weasyprint import CSS, HTML, URLFetcher

ROOT_DOCUMENT = "part1-foundations/ch01-preface"
PUBLIC_URL = "https://dangvitin.github.io/linuxlearn/"
FILENAME = "embedded-linux-imx6ull.pdf"
JPEG_QUALITY = 95


def document_id(path):
    return "doc-" + path.with_suffix("").as_posix().replace("/", "--")


def reading_order(site, root_document):
    root = site / (root_document + ".html")
    soup = BeautifulSoup(root.read_text(encoding="utf-8"), "html.parser")
    navigation = soup.select_one('nav.sidebar-tree[aria-label="Book chapters"]')
    if navigation is None:
        raise ValueError("The Sphinx book navigation was not found")
    documents = [root.relative_to(site)]
    for link in navigation.select("a[href]"):
        url = urlsplit(link["href"])
        if url.scheme or url.netloc or url.fragment or not url.path:
            continue
        target = (root.parent / unquote(url.path)).resolve()
        relative = target.relative_to(site)
        if target.suffix == ".html" and relative not in documents:
            if not target.is_file():
                raise FileNotFoundError(target)
            documents.append(relative)
    # Missing chapters must fail the export rather than produce a partial book.
    chapter_pages = {p.relative_to(site) for p in site.glob("part*/ch*.html")}
    omitted = chapter_pages - set(documents)
    if omitted:
        raise ValueError(f"Chapters missing from reading order: {sorted(map(str, omitted))}")
    return documents


def assemble_book(site, documents):
    soup = BeautifulSoup('<html lang="en"><head><meta charset="utf-8"><title>Embedded Linux on i.MX6ULL</title><meta name="author" content="DangViTin"></head><body><nav class="contents"><h1>Contents</h1><ol></ol></nav><main></main></body></html>', "html.parser")
    chapter_ids = {}
    articles = []
    for relative in documents:
        page = BeautifulSoup((site / relative).read_text(encoding="utf-8"), "html.parser")
        article = page.select_one("article")
        if article is None or article.find("h1") is None:
            raise ValueError(f"No chapter article in {relative}")
        prefix = document_id(relative)
        chapter_ids[relative] = {element["id"] for element in article.select("[id]")}
        articles.append((relative, prefix, article))

    for relative, prefix, article in articles:
        for unwanted in article.select(".headerlink, .toctree-wrapper, .copybtn, .book-download-inline"):
            unwanted.decompose()
        # Print has no token-color CSS. Keep code semantics without tagging every token.
        for token in article.select(".highlight pre span"):
            if set(token.attrs) <= {"class"}:
                token.unwrap()
        title = " ".join(article.find("h1").get_text().split())
        entry = soup.new_tag("li")
        link = soup.new_tag("a", href="#" + prefix)
        link.string = title
        entry.append(link)
        soup.select_one(".contents ol").append(entry)
        for element in article.select("[id]"):
            element["id"] = prefix + "--" + element["id"]
        for anchor in article.select("a[href]"):
            url = urlsplit(anchor["href"])
            if url.scheme or url.netloc:
                continue
            target = (site / relative).parent / unquote(url.path) if url.path else site / relative
            try:
                destination = target.resolve().relative_to(site)
            except ValueError:
                raise ValueError(f"Link escapes the build directory: {relative}: {anchor['href']}")
            if destination in chapter_ids and (not url.fragment or unquote(url.fragment) in chapter_ids[destination]):
                anchor["href"] = "#" + document_id(destination) + ("--" + unquote(url.fragment) if url.fragment else "")
            else:
                anchor["href"] = urljoin(PUBLIC_URL + relative.as_posix(), anchor["href"])
        for image in article.select("img[src]"):
            url = urlsplit(image["src"])
            if url.scheme or url.netloc:
                raise ValueError(f"PDF images must be local: {image['src']}")
            image_path = ((site / relative).parent / unquote(url.path)).resolve()
            image_path.relative_to(site)
            if not image_path.is_file():
                raise FileNotFoundError(image_path)
            image["src"] = image_path.as_uri()
            image.attrs.pop("loading", None)
            image.attrs.pop("decoding", None)
            image.attrs.pop("width", None)
            if image.parent.name == "a" and "image-reference" in image.parent.get("class", []):
                image.parent.unwrap()
        # Preserve wide text diagrams instead of wrapping their connecting lines.
        for pre in article.select("pre"):
            text = pre.get_text().expandtabs(4)
            if re.search(r"[\u2500-\u257f]", text):
                longest = max(map(len, text.splitlines()), default=1)
                size = min(8.4, 462 / (max(longest, 1) * 0.61))
                pre["style"] = f"font-size: {size:.2f}pt; white-space: pre;"
        chapter = soup.new_tag("section", attrs={"id": prefix, "class": "chapter"})
        for child in list(article.contents):
            chapter.append(child)
        soup.main.append(chapter)
    return soup


def local_fetcher(site):
    class LocalAssets(URLFetcher):
        def fetch(self, url, headers=None):
            parsed = urlsplit(url)
            if parsed.scheme != "file":
                raise ValueError(f"Network assets are not allowed in the PDF: {url}")
            path = Path(unquote(parsed.path))
            if path.drive == "" and re.match(r"^/[A-Za-z]:", str(path)):
                path = Path(str(path)[1:])
            path.resolve().relative_to(site)
            return super().fetch(url, headers)
    return LocalAssets(allowed_protocols={"file"}, fail_on_errors=True)


def optimize_pdf(source, output):
    if source.resolve() == output.resolve():
        raise ValueError("PDF optimization requires a separate output file")
    with tempfile.TemporaryDirectory(prefix="book-pdf-", dir=output.parent) as work:
        cleaned = Path(work) / "resources.pdf"
        # Shared image dictionaries otherwise make every page reference every sketch.
        with pikepdf.open(source) as pdf:
            pdf.remove_unreferenced_resources()
            pdf.save(cleaned, object_stream_mode=pikepdf.ObjectStreamMode.disable)
        job = pikepdf.Job([
            "pikepdf", "--linearize", "--object-streams=generate",
            "--recompress-flate", "--compression-level=9", "--optimize-images",
            f"--jpeg-quality={JPEG_QUALITY}", str(cleaned), str(output),
        ])
        job.run()
        if job.exit_code != 0:
            raise RuntimeError(f"PDF optimization failed with exit code {job.exit_code}")
    with pikepdf.open(output) as pdf:
        if not pdf.is_linearized or not pdf.check_linearization():
            raise RuntimeError("The PDF fast-web-view layout is invalid")
        if "/StructTreeRoot" not in pdf.Root or not pdf.Root.MarkInfo.Marked:
            raise RuntimeError("PDF optimization lost the accessibility structure")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--html-dir", type=Path, default=Path("book/_build/html"))
    parser.add_argument("--output", type=Path)
    parser.add_argument("--root-document", default=ROOT_DOCUMENT)
    args = parser.parse_args()
    site = args.html_dir.resolve()
    output = (args.output or site / "downloads" / FILENAME).resolve()
    documents = reading_order(site, args.root_document)
    book = assemble_book(site, documents)
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary_pdf = output.with_suffix(".tmp.pdf")
    rendered_pdf = output.with_suffix(".render.pdf")
    print(f"Rendering {len(documents)} reading documents into one PDF", flush=True)
    css = Path(__file__).with_name("book_pdf.css")
    html_path = output.with_suffix(".print.html")
    html_path.write_text(str(book), encoding="utf-8")
    messages = []

    class Capture(logging.Handler):
        def emit(self, record):
            if record.levelno >= logging.WARNING:
                messages.append(record.getMessage())

    capture = Capture()
    logger = logging.getLogger("weasyprint")
    logger.addHandler(capture)
    try:
        # Let QPDF pack objects in small groups instead of parsing one giant object stream.
        HTML(string=str(book), base_url=site.as_uri() + "/", url_fetcher=local_fetcher(site)).write_pdf(rendered_pdf, stylesheets=[CSS(filename=str(css))], pdf_tags=True, optimize_images=True, uncompressed_pdf=True)
        if messages:
            raise RuntimeError("PDF rendering warnings:\n" + "\n".join(messages))
        rendered_bytes = rendered_pdf.stat().st_size
        print("Optimizing images and preparing fast web view", flush=True)
        optimize_pdf(rendered_pdf, temporary_pdf)
        reader = PdfReader(temporary_pdf)
        if not reader.pages or not reader.outline:
            raise RuntimeError("The PDF has no pages or bookmarks")
        top_titles = [entry.title for entry in reader.outline if not isinstance(entry, list)]
        expected_titles = [" ".join(heading.get_text().split()) for heading in book.select("h1")]
        if top_titles != expected_titles:
            raise RuntimeError("PDF bookmarks do not cover every reading document in order")
        temporary_pdf.replace(output)
    finally:
        logger.removeHandler(capture)
        html_path.unlink(missing_ok=True)
        temporary_pdf.unlink(missing_ok=True)
        rendered_pdf.unlink(missing_ok=True)
    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "filename": output.name,
        "bytes": output.stat().st_size,
        "pages": len(reader.pages),
        "documents": [p.with_suffix("").as_posix() for p in documents],
        "chapter_documents": sum(p.name.startswith("ch") for p in documents),
        "figures": len(book.select("figure")),
        "warnings": messages,
        "optimization": {
            "rendered_bytes": rendered_bytes,
            "jpeg_quality": JPEG_QUALITY,
            "linearized": True,
        },
    }
    output.with_suffix(".json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in summary.items() if k != "documents"}, indent=2), flush=True)


if __name__ == "__main__":
    main()
