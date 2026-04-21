import tempfile
import unittest
from pathlib import Path
from unittest.mock import ANY, patch

from pandoc_to_markdown import routing


class NormalizeExtsTests(unittest.TestCase):
    def test_normalize_exts_trims_deduplicates_and_lowercases(self) -> None:
        self.assertEqual(routing.normalize_exts(" PDF, .Html,md, pdf "), {".pdf", ".html", ".md"})


class ResolveSourcesTests(unittest.TestCase):
    def test_resolve_sources_single_returns_input_paths(self) -> None:
        paths = [Path("/tmp/a.docx"), Path("/tmp/b.pdf")]
        self.assertEqual(routing.resolve_sources("single", paths), paths)

    def test_resolve_sources_batch_filters_matching_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            nested = root / "nested"
            nested.mkdir()
            keep_top = root / "a.html"
            keep_nested = nested / "b.pdf"
            ignore = root / "c.txt"
            keep_top.write_text("<h1>x</h1>", encoding="utf-8")
            keep_nested.write_text("pdf", encoding="utf-8")
            ignore.write_text("ignore", encoding="utf-8")

            non_recursive = routing.resolve_sources("batch", [root], exts="html,pdf", recursive=False)
            recursive = routing.resolve_sources("batch", [root], exts="html,pdf", recursive=True)

            self.assertEqual(non_recursive, [keep_top])
            self.assertEqual(recursive, [keep_top, keep_nested])

    def test_resolve_sources_batch_keeps_missing_paths_for_later_error_handling(self) -> None:
        missing = Path("/tmp/does-not-exist.pdf")
        self.assertEqual(routing.resolve_sources("batch", [missing], exts="pdf", recursive=False), [missing])


class RunConversionTests(unittest.TestCase):
    def test_run_conversion_uses_pandoc_for_non_pdf(self) -> None:
        source = Path("/tmp/book.html")
        with patch("pandoc_to_markdown.routing.ensure_pandoc", return_value="/bin/pandoc") as ensure_pandoc, patch(
            "pandoc_to_markdown.routing.convert_non_pdf_with_pandoc",
            return_value={"ok": True, "input": str(source), "output": "/tmp/book.md"},
        ) as convert_non_pdf, patch("pandoc_to_markdown.routing.postprocess_markdown_file") as postprocess_markdown_file:
            payload = routing.run_conversion([source], None, overwrite=True, to_format="commonmark_x", pdf_engine="marker")

        ensure_pandoc.assert_called_once_with()
        convert_non_pdf.assert_called_once_with(source, None, True, "commonmark_x", "/bin/pandoc")
        postprocess_markdown_file.assert_called_once_with(Path("/tmp/book.md"))
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["count"], 1)

    def test_run_conversion_reports_missing_pandoc(self) -> None:
        source = Path("/tmp/book.html")
        with patch("pandoc_to_markdown.routing.ensure_pandoc", side_effect=RuntimeError("pandoc missing")):
            payload = routing.run_conversion([source], None, overwrite=False, to_format="commonmark_x", pdf_engine="marker")

        self.assertFalse(payload["ok"])
        self.assertEqual(payload["results"][0]["error"], "PANDOC_NOT_INSTALLED")
        self.assertEqual(payload["results"][0]["detail"], "pandoc missing")

    def test_run_conversion_uses_marker_for_pdf(self) -> None:
        source = Path("/tmp/book.pdf")
        events = []

        def progress(event: dict) -> None:
            events.append(event)

        with patch("pandoc_to_markdown.routing.ensure_marker", return_value="/bin/marker_single") as ensure_marker, patch(
            "pandoc_to_markdown.routing.convert_pdf_with_marker",
            side_effect=lambda src, out_dir, overwrite, marker_bin, progress_callback=None, marker_mode='auto': (
                progress_callback({"type": "MODEL_DOWNLOAD_STARTED", "engine": "marker", "message": "首次使用 Marker，需要先下载模型，下载完成后会继续转换。", "models": [{"name": "layout", "download_url": "https://models.datalab.to/layout/2025_09_23/manifest.json", "model_size": "1.35 GB"}]})
                or {"ok": True, "input": str(src), "output": "/tmp/book.md"}
            ),
        ) as convert_pdf, patch("pandoc_to_markdown.routing.postprocess_markdown_file") as postprocess_markdown_file:
            payload = routing.run_conversion(
                [source],
                None,
                overwrite=False,
                to_format="commonmark_x",
                pdf_engine="marker",
                progress_callback=progress,
            )

        ensure_marker.assert_called_once_with()
        convert_pdf.assert_called_once_with(source, None, False, "/bin/marker_single", progress_callback=ANY, marker_mode="auto")
        postprocess_markdown_file.assert_called_once_with(Path("/tmp/book.md"))
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["notices"][0]["type"], "MODEL_DOWNLOAD_STARTED")
        self.assertEqual(payload["notices"][0]["models"][0]["download_url"], "https://models.datalab.to/layout/2025_09_23/manifest.json")
        self.assertEqual(events[0]["engine"], "marker")

    def test_run_conversion_uses_mineru_for_pdf(self) -> None:
        source = Path("/tmp/book.pdf")
        with patch("pandoc_to_markdown.routing.ensure_mineru", return_value="/bin/mineru") as ensure_mineru, patch(
            "pandoc_to_markdown.routing.convert_pdf_with_mineru",
            return_value={"ok": True, "input": str(source), "output": "/tmp/book.md"},
        ) as convert_pdf, patch("pandoc_to_markdown.routing.postprocess_markdown_file") as postprocess_markdown_file:
            payload = routing.run_conversion([source], None, overwrite=True, to_format="commonmark_x", pdf_engine="mineru", marker_mode="cpu")

        ensure_mineru.assert_called_once_with()
        convert_pdf.assert_called_once_with(source, None, True, "/bin/mineru", progress_callback=ANY)
        postprocess_markdown_file.assert_called_once_with(Path("/tmp/book.md"))
        self.assertTrue(payload["ok"])

    def test_run_conversion_reports_unsupported_suffix(self) -> None:
        source = Path("/tmp/book.xyz")
        payload = routing.run_conversion([source], None, overwrite=False, to_format="commonmark_x", pdf_engine="marker")

        self.assertFalse(payload["ok"])
        self.assertEqual(payload["results"][0]["error"], "UNSUPPORTED_INPUT_FORMAT")

    def test_run_conversion_skips_postprocess_for_failed_result(self) -> None:
        source = Path("/tmp/book.html")
        with patch("pandoc_to_markdown.routing.ensure_pandoc", return_value="/bin/pandoc"), patch(
            "pandoc_to_markdown.routing.convert_non_pdf_with_pandoc",
            return_value={"ok": False, "input": str(source), "error": "PANDOC_FAILED", "detail": "broken"},
        ), patch("pandoc_to_markdown.routing.postprocess_markdown_file") as postprocess_markdown_file:
            payload = routing.run_conversion([source], None, overwrite=False, to_format="commonmark_x", pdf_engine="marker")

        postprocess_markdown_file.assert_not_called()
        self.assertFalse(payload["ok"])


if __name__ == "__main__":
    unittest.main()
