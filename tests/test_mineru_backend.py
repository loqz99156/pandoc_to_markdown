import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from pandoc_to_markdown.converters import mineru_backend


class MineruDownloadEventTests(unittest.TestCase):
    def test_convert_pdf_with_mineru_emits_download_metadata_on_first_download_line(self) -> None:
        events = []

        class FakeProc:
            def __init__(self):
                self.stdout = iter(["Downloading manifest.json\n"])

            def wait(self):
                return 0

        with tempfile.TemporaryDirectory() as tmp_dir:
            src = Path(tmp_dir) / "book.pdf"
            src.write_text("pdf", encoding="utf-8")
            out_dir = Path(tmp_dir) / "out"
            out_dir.mkdir()
            generated = out_dir / "book.md"

            class OutputProc(FakeProc):
                def wait(self):
                    generated.write_text("# ok", encoding="utf-8")
                    return 0

            with patch("pandoc_to_markdown.converters.mineru_backend.build_mineru_env", return_value={"MINERU_MODEL_SOURCE": "local"}), patch(
                "pandoc_to_markdown.converters.mineru_backend.subprocess.Popen",
                return_value=OutputProc(),
            ):
                result = mineru_backend.convert_pdf_with_mineru(src, out_dir, overwrite=True, mineru_bin="/bin/mineru", progress_callback=events.append)

        self.assertTrue(result["ok"])
        self.assertEqual(events[0]["type"], "MODEL_DOWNLOAD_STARTED")
        self.assertIn("models", events[0])
        self.assertEqual(len(events[0]["models"]), 2)
        self.assertIn("download_url", events[0]["models"][0])
        self.assertIn("model_size", events[0]["models"][0])


class ConvertPdfWithMineruTests(unittest.TestCase):
    def test_convert_pdf_with_mineru_passes_project_local_env(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            src = Path(tmp_dir) / "book.pdf"
            src.write_text("pdf", encoding="utf-8")
            out_dir = Path(tmp_dir) / "out"
            out_dir.mkdir()
            generated = out_dir / "book.md"

            class FakeProc:
                def __init__(self):
                    self.stdout = iter([])

                def wait(self):
                    generated.write_text("# ok", encoding="utf-8")
                    return 0

            with patch("pandoc_to_markdown.converters.mineru_backend.build_mineru_env", return_value={"MINERU_MODEL_SOURCE": "local"}) as build_env, patch(
                "pandoc_to_markdown.converters.mineru_backend.subprocess.Popen",
                return_value=FakeProc(),
            ) as popen:
                result = mineru_backend.convert_pdf_with_mineru(src, out_dir, overwrite=True, mineru_bin="/bin/mineru")

        self.assertTrue(result["ok"])
        build_env.assert_called_once()
        self.assertEqual(popen.call_args.kwargs["env"], {"MINERU_MODEL_SOURCE": "local"})


if __name__ == "__main__":
    unittest.main()
