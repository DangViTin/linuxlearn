"""Run with python -m unittest discover -s tools -p 'test_*.py'."""

from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from build_book_pdf import assemble_book, document_id, local_fetcher, reading_order
from build_book_pdf import main


class BookPdfTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.site = Path(self.temp.name).resolve()
        (self.site / "part1-foundations").mkdir()
        self.first = Path("part1-foundations/ch01-preface.html")
        self.second = Path("part1-foundations/ch10-example.html")

    def page(self, relative, body, navigation=""):
        (self.site / relative).write_text(f'<html><nav class="sidebar-tree" aria-label="Book chapters">{navigation}</nav><article>{body}</article></html>', encoding="utf-8")

    def test_navigation_order_not_filename_sort(self):
        third = Path("part1-foundations/ch02-example.html")
        self.page(self.first, "<h1>One</h1>", '<a href="ch10-example.html">Ten</a><a href="ch02-example.html">Two</a>')
        self.page(self.second, "<h1>Ten</h1>")
        self.page(third, "<h1>Two</h1>")
        self.assertEqual(reading_order(self.site, "part1-foundations/ch01-preface"), [self.first, self.second, third])

    def test_missing_chapter_fails(self):
        self.page(self.first, "<h1>One</h1>")
        self.page(self.second, "<h1>Ten</h1>")
        with self.assertRaisesRegex(ValueError, "missing from reading order"):
            reading_order(self.site, "part1-foundations/ch01-preface")

    def test_ids_and_cross_chapter_links_are_namespaced(self):
        self.page(self.first, '<h1>One</h1><section id="lab"><a href="#lab">Here</a><a href="ch10-example.html#lab">Other</a><a href="https://example.com">Web</a></section><pre>r0 = 5\n  @ a comment</pre><div class="book-download-inline">Download PDF</div>')
        self.page(self.second, '<h1>Ten</h1><section id="lab">Second lab</section>')
        book = assemble_book(self.site, [self.first, self.second])
        ids = [tag["id"] for tag in book.select("[id]")]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(book.main.find("a", string="Other")["href"], "#" + document_id(self.second) + "--lab")
        self.assertEqual(book.main.find("a", string="Here")["href"], "#" + document_id(self.first) + "--lab")
        self.assertEqual(book.main.find("a", string="Web")["href"], "https://example.com")
        self.assertEqual(book.pre.get_text(), "r0 = 5\n  @ a comment")
        self.assertNotIn("Download PDF", book.get_text())
        for anchor in book.select('a[href^="#"]'):
            self.assertIsNotNone(book.find(id=anchor["href"][1:]))

    def test_missing_image_fails(self):
        self.page(self.first, '<h1>One</h1><img src="../_images/missing.png">')
        with self.assertRaises(FileNotFoundError):
            assemble_book(self.site, [self.first])

    def test_network_assets_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "Network assets"):
            local_fetcher(self.site)("https://example.com/image.png")
        self.page(self.first, '<h1>One</h1><img src="https://example.com/image.png">')
        with self.assertRaisesRegex(ValueError, "must be local"):
            assemble_book(self.site, [self.first])

    def test_file_asset_cannot_escape_build(self):
        with self.assertRaises(ValueError):
            local_fetcher(self.site)((self.site.parent / "secret.png").as_uri())

    def test_failed_render_preserves_existing_pdf(self):
        self.page(self.first, "<h1>One</h1>")
        output = self.site / "downloads/book.pdf"
        output.parent.mkdir()
        output.write_bytes(b"previous complete PDF")
        with patch("sys.argv", ["build_book_pdf", "--html-dir", str(self.site), "--output", str(output)]), patch("build_book_pdf.HTML") as html:
            html.return_value.write_pdf.side_effect = RuntimeError("render failed")
            with self.assertRaisesRegex(RuntimeError, "render failed"):
                main()
        self.assertEqual(output.read_bytes(), b"previous complete PDF")
        self.assertFalse(output.with_suffix(".print.html").exists())
        self.assertFalse(output.with_suffix(".tmp.pdf").exists())


if __name__ == "__main__":
    unittest.main()
