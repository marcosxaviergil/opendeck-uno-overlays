"""Manual.pdf (scripts/build_manual.py): every language, every internal link, images or placeholders.

Needs WeasyPrint (Debian: apt install weasyprint fonts-noto-cjk fonts-dejavu-core), which the Forgejo
workflow installs; elsewhere the test is skipped with a message, like the browser test without Playwright.
"""

import importlib.util
import pathlib
import re
import shutil
import sys
import tempfile
import unittest
from unittest import mock

from support import ROOT

sys.path.insert(0, str(ROOT / "scripts"))
import build_manual  # noqa: E402

HAS_WEASYPRINT = importlib.util.find_spec("weasyprint") is not None
JPEG = bytes.fromhex(  # a 1×1 white JPEG
    "ffd8ffe000104a46494600010100000100010000ffdb004300080606070605080707070909080a0c140d0c0b0b0c1912130f141d1a1f1e1d1a1c1c"
    "20242e2720222c231c1c2837292c30313434341f27393d38323c2e333432ffc0000b080001000101011100ffc4001f00000105010101010101000000"
    "00000000000102030405060708090a0bffc400b5100002010303020403050504040000017d01020300041105122131410613516107227114328191a1"
    "082342b1c11552d1f02433627282090a161718191a25262728292a3435363738393a434445464748494a535455565758595a636465666768696a7374"
    "75767778797a838485868788898a92939495969798999aa2a3a4a5a6a7a8a9aab2b3b4b5b6b7b8b9bac2c3c4c5c6c7c8c9cad2d3d4d5d6d7d8d9da"
    "e1e2e3e4e5e6e7e8e9eaf1f2f3f4f5f6f7f8f9faffda0008010100003f00fbd3ffd9"
)


class ManualSource(unittest.TestCase):
    def test_every_help_text_is_in_the_manual(self):
        """The "?" help of the inspector and the manual are one text: every help key has a place in the manual."""
        english = build_manual.catalog("en")
        listed = {f"?{a}.{f}" for a, fields in build_manual.ACTION_FIELDS.items() for f in fields}
        listed |= {f"?settings.{f}" for f in build_manual.SETTINGS_FIELDS}
        shared = {f"?{f}" for fields in build_manual.ACTION_FIELDS.values() for f in fields}
        actions = {f"?{a}" for a in build_manual.ACTION_FIELDS}
        unused = [key for key in english if key not in listed | shared | actions]
        self.assertEqual(unused, [], "help texts that the manual does not show")

    def test_every_language_has_a_source_with_title_contents_and_the_generated_blocks(self):
        def shape(text):  # what a translation keeps: chapter ids, heading levels, images, blocks
            return (
                re.findall(r"\{#([\w-]+)\}", text),
                [len(m) for m in re.findall(r"^(#+) ", text, re.M)],
                re.findall(r"!\[[^\]]*\]\(([^)]+)\)", text),
                re.findall(r"\{\{\w+\}\}", text),
            )

        english = shape((build_manual.MANUAL / "en" / "manual.md").read_text(encoding="utf-8"))
        for code in build_manual.LANGUAGES:
            with self.subTest(code):
                text = (build_manual.MANUAL / code / "manual.md").read_text(encoding="utf-8")
                lines = text.splitlines()
                self.assertTrue(lines[0].startswith("% ") and lines[1].startswith("% "))
                self.assertIn("{{actions}}", lines)
                self.assertIn("{{settings}}", lines)
                self.assertEqual(shape(text), english, "same chapters, headings and images as the English manual")

    def test_images_are_used_when_present_and_placeholders_otherwise(self):
        images = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, images, True)
        (images / "pt-BR").mkdir()
        (images / "pt-BR" / "inspetor_overlay.jpg").write_bytes(JPEG)  # only Portuguese has this capture
        (images / "engrenagem_plugins.jpg").write_bytes(JPEG)  # every language shares this one
        with mock.patch.object(build_manual, "IMAGES", images):
            page, missing = build_manual.document("9.9.9")
        self.assertNotIn("inspetor_overlay.jpg", missing["pt-BR"])
        self.assertIn("inspetor_overlay.jpg", missing["en"], "the per-language image is not used by others")
        self.assertTrue(all("engrenagem_plugins.jpg" not in names for names in missing.values()))
        self.assertIn("&lt;botao_instalar_plugins.jpg&gt;", page, "a missing image is a visible placeholder")
        self.assertEqual(page.count((images / "engrenagem_plugins.jpg").as_uri()), len(build_manual.LANGUAGES))

    def test_the_fetcher_loads_only_files_of_the_manual(self):
        if not HAS_WEASYPRINT:
            self.skipTest("WeasyPrint is not installed (Debian: apt install weasyprint)")
        for url in ("https://example.com/x.png", "file:///etc/passwd", build_manual.MANUAL.as_uri() + "/../../x"):
            with self.subTest(url), self.assertRaises(ValueError):
                build_manual.fetcher(url)


@unittest.skipUnless(HAS_WEASYPRINT, "WeasyPrint is not installed (Debian: apt install weasyprint fonts-noto-cjk)")
class ManualPdf(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.document, cls.missing = build_manual.render("9.9.9")

    def test_nine_languages_each_a_bookmark_with_its_chapters(self):
        tree = self.document.make_bookmark_tree()
        self.assertEqual(len(tree), len(build_manual.LANGUAGES), [entry[0] for entry in tree])
        for (title, _, children, _), code in zip(tree, build_manual.LANGUAGES, strict=True):
            with self.subTest(code):
                self.assertGreater(len(children), 8, f"{title}: chapters as bookmarks")

    def test_every_internal_link_reaches_a_target_and_the_first_page_lists_each_language(self):
        anchors = {anchor for page in self.document.pages for anchor in page.anchors}
        links = [link[1] for page in self.document.pages for link in page.links if link[0] == "internal"]
        self.assertEqual([target for target in links if target not in anchors], [])
        cover = {link[1] for link in self.document.pages[0].links if link[0] == "internal"}
        self.assertEqual(cover, {f"{code}-toc" for code in build_manual.LANGUAGES})

    def test_writes_a_pdf(self):
        self.assertTrue(self.document.write_pdf().startswith(b"%PDF-"))
