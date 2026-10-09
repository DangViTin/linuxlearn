"""Run with python -m unittest discover -s tools -p 'test_*.py'."""

import base64
from io import BytesIO
import json
from pathlib import Path
import random
import tempfile
import unittest
from unittest.mock import patch

import pikepdf
from PIL import Image
from pypdf import PdfReader
from weasyprint import HTML

from build_book_pdf import assemble_book, document_id, local_fetcher, reading_order
from build_book_pdf import JPEG_QUALITY, main, optimize_pdf


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

    def test_print_code_drops_only_unstyled_token_wrappers(self):
        self.page(self.first, '<h1>One</h1><div class="highlight"><pre><span class="k">int</span> <span class="n">r0</span> = 5;\n<span></span>  @ a comment\n<span id="keep">anchor</span><span style="color:red">styled</span><span aria-label="note">labelled</span></pre></div>')
        book = assemble_book(self.site, [self.first])
        self.assertEqual(book.pre.get_text(), "int r0 = 5;\n  @ a comment\nanchorstyledlabelled")
        self.assertEqual(len(book.pre.select("span")), 3)
        self.assertIsNotNone(book.find(id=document_id(self.first) + "--keep"))

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
        self.assertFalse(output.with_suffix(".render.pdf").exists())

    def test_failed_optimization_preserves_existing_pdf(self):
        self.page(self.first, "<h1>One</h1>")
        output = self.site / "downloads/book.pdf"
        output.parent.mkdir()
        output.write_bytes(b"previous complete PDF")
        def fake_render(path, **options):
            path.write_bytes(b"rendered PDF")
        with patch("sys.argv", ["build_book_pdf", "--html-dir", str(self.site), "--output", str(output)]), patch("build_book_pdf.HTML") as html, patch("build_book_pdf.optimize_pdf", side_effect=RuntimeError("optimization failed")):
            html.return_value.write_pdf.side_effect = fake_render
            with self.assertRaisesRegex(RuntimeError, "optimization failed"):
                main()
        self.assertEqual(output.read_bytes(), b"previous complete PDF")
        self.assertFalse(output.with_suffix(".print.html").exists())
        self.assertFalse(output.with_suffix(".tmp.pdf").exists())
        self.assertFalse(output.with_suffix(".render.pdf").exists())

    def test_optimization_rejects_in_place_output(self):
        path = self.site / "book.pdf"
        with self.assertRaisesRegex(ValueError, "separate output"):
            optimize_pdf(path, path)

    def test_complete_export_records_optimization_and_cleans_temporary_files(self):
        self.page(self.first, '<h1>One</h1><p id="target">A complete export.</p><a href="#target">Internal link</a>')
        output = self.site / "downloads/book.pdf"
        with patch("sys.argv", ["build_book_pdf", "--html-dir", str(self.site), "--output", str(output)]):
            main()
        metadata = json.loads(output.with_suffix(".json").read_text())
        self.assertEqual(metadata["bytes"], output.stat().st_size)
        self.assertEqual(metadata["documents"], [self.first.with_suffix("").as_posix()])
        self.assertEqual(metadata["warnings"], [])
        self.assertTrue(metadata["optimization"]["linearized"])
        self.assertEqual(metadata["optimization"]["jpeg_quality"], JPEG_QUALITY)
        self.assertGreater(metadata["optimization"]["rendered_bytes"], 0)
        self.assertEqual(metadata["pages"], len(PdfReader(output).pages))
        for suffix in [".print.html", ".tmp.pdf", ".render.pdf"]:
            self.assertFalse(output.with_suffix(suffix).exists())

    def test_optimizer_preserves_text_navigation_tags_and_image_dimensions(self):
        image = Image.frombytes("RGB", (256, 256), random.Random(42).randbytes(256 * 256 * 3))
        data = BytesIO()
        image.save(data, format="PNG")
        uri = "data:image/png;base64," + base64.b64encode(data.getvalue()).decode("ascii")
        source = self.site / "source.pdf"
        output = self.site / "optimized.pdf"
        HTML(string=f'<h1 id="one">One</h1><p>Selectable text <a href="#one">Internal</a> <a href="https://example.com">External</a></p><figure><img src="{uri}" alt="A test pattern" width="256"></figure>').write_pdf(source, pdf_tags=True)
        shared = self.site / "shared-resources.pdf"
        with pikepdf.open(source) as pdf:
            blank = pdf.add_blank_page()
            blank.Resources = pdf.pages[0].Resources
            self.assertEqual(len(blank.images), 1)
            pdf.save(shared)
        source = shared
        optimize_pdf(source, output)
        before, after = PdfReader(source), PdfReader(output)
        self.assertEqual(len(before.pages), len(after.pages))
        self.assertEqual([p.extract_text() for p in before.pages], [p.extract_text() for p in after.pages])
        self.assertEqual([e.title for e in before.outline], [e.title for e in after.outline])
        self.assertEqual(len(before.pages[0]["/Annots"]), len(after.pages[0]["/Annots"]))
        with pikepdf.open(output) as pdf:
            self.assertTrue(pdf.is_linearized)
            self.assertTrue(pdf.check_linearization())
            self.assertIn("/StructTreeRoot", pdf.Root)
            self.assertTrue(pdf.Root.MarkInfo.Marked)
            self.assertEqual(len(pdf.pages[1].images), 0)
            images = list(pdf.pages[0].images.values())
            self.assertEqual(len(images), 1)
            self.assertEqual((images[0].Width, images[0].Height), (256, 256))
            self.assertEqual(images[0].Filter, pikepdf.Name.DCTDecode)
        self.assertLess(output.stat().st_size, source.stat().st_size)
        self.assertEqual(JPEG_QUALITY, 95)


if __name__ == "__main__":
    unittest.main()
