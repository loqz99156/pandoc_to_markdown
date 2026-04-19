import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import ANY, patch

from pandoc_to_markdown import cli


class PrintPayloadTests(unittest.TestCase):
    def test_print_payload_text_mode(self) -> None:
        payload = {
            "results": [
                {"ok": True, "input": "/tmp/a.html", "output": "/tmp/a.md"},
                {"ok": False, "input": "/tmp/b.pdf", "error": "FAILED", "detail": "broken"},
            ]
        }
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            cli.print_payload(payload, as_json=False)

        self.assertEqual(buffer.getvalue().strip().splitlines(), ["OK /tmp/a.html -> /tmp/a.md", "FAIL /tmp/b.pdf :: broken"])

    def test_print_payload_interrupted_mineru_download_prints_recovery_hint(self) -> None:
        payload = {
            "results": [
                {
                    "ok": False,
                    "input": "/tmp/b.pdf",
                    "error": "MINERU_FAILED",
                    "detail": "download stopped at /Users/x/.cache/huggingface/blob.incomplete after Connection reset",
                }
            ]
        }
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            cli.print_payload(payload, as_json=False)

        self.assertEqual(
            buffer.getvalue().strip().splitlines(),
            [
                "FAIL /tmp/b.pdf :: download stopped at /Users/x/.cache/huggingface/blob.incomplete after Connection reset",
                "模型下载被中断了，重新执行同一条转换或模型下载命令即可继续，不需要从头开始。",
                '如需先补齐模型，可运行：PYTHONPATH="$PWD/src" python3 scripts/download_models.py --source huggingface --model-type all',
                "如果多次都卡在同一个 .incomplete 文件，再删除那个 .incomplete 文件后重试；不要清空整个 ~/.cache/huggingface。",
            ],
        )

    def test_print_payload_regular_failure_does_not_print_recovery_hint(self) -> None:
        payload = {"results": [{"ok": False, "input": "/tmp/b.html", "error": "PANDOC_FAILED", "detail": "broken"}]}
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            cli.print_payload(payload, as_json=False)

        self.assertEqual(buffer.getvalue().strip().splitlines(), ["FAIL /tmp/b.html :: broken"])

    def test_print_payload_json_mode(self) -> None:
        payload = {"results": [{"ok": True, "input": "/tmp/a.html", "output": "/tmp/a.md"}]}
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            cli.print_payload(payload, as_json=True)

        self.assertEqual(json.loads(buffer.getvalue()), payload)


class MainCommandTests(unittest.TestCase):
    def test_main_info_json_outputs_payload(self) -> None:
        buffer = io.StringIO()
        with patch("sys.argv", ["ptm", "info", "--json"]), redirect_stdout(buffer):
            cli.main()

        self.assertEqual(json.loads(buffer.getvalue()), {"project": "pandoc-to-markdown", "status": "bootstrap"})

    def test_main_convert_success_uses_resolved_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            src = (Path(tmp_dir) / "book.html").resolve()
            src.write_text("<h1>x</h1>", encoding="utf-8")
            out_dir = (Path(tmp_dir) / "out").resolve()
            buffer = io.StringIO()
            payload = {"ok": True, "count": 1, "results": [{"ok": True, "input": str(src), "output": str(out_dir / 'book.md')}]}
            with patch("sys.argv", ["ptm", "convert", "--mode", "single", "--paths", str(src), "--out-dir", str(out_dir), "--json"]), patch(
                "pandoc_to_markdown.cli.resolve_sources", return_value=[src]
            ) as resolve_sources, patch("pandoc_to_markdown.cli.run_conversion", return_value=payload) as run_conversion, redirect_stdout(buffer):
                cli.main()

        resolve_sources.assert_called_once_with("single", [src], exts=cli.DEFAULT_EXTS, recursive=False)
        run_conversion.assert_called_once_with(
            sources=[src],
            out_dir=out_dir,
            overwrite=False,
            to_format=cli.PANDOC_TARGET_FORMAT,
            pdf_engine="marker",
            progress_callback=ANY,
        )
        self.assertEqual(json.loads(buffer.getvalue()), payload)

    def test_main_convert_defaults_to_project_outputs_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            src = (Path(tmp_dir) / "book.html").resolve()
            src.write_text("<h1>x</h1>", encoding="utf-8")
            buffer = io.StringIO()
            payload = {"ok": True, "count": 1, "results": [{"ok": True, "input": str(src), "output": "unused"}], "notices": []}
            with patch("sys.argv", ["ptm", "convert", "--mode", "single", "--paths", str(src), "--json"]), patch(
                "pandoc_to_markdown.cli.resolve_sources", return_value=[src]
            ), patch("pandoc_to_markdown.cli.run_conversion", return_value=payload) as run_conversion, redirect_stdout(buffer):
                cli.main()

        project_root = Path(cli.__file__).resolve().parents[2]
        run_conversion.assert_called_once_with(
            sources=[src],
            out_dir=project_root / "outputs",
            overwrite=False,
            to_format=cli.PANDOC_TARGET_FORMAT,
            pdf_engine="marker",
            progress_callback=ANY,
        )
        self.assertEqual(json.loads(buffer.getvalue()), payload)

    def test_main_convert_text_mode_prints_model_download_notice_before_result(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            src = (Path(tmp_dir) / "book.pdf").resolve()
            src.write_text("pdf", encoding="utf-8")
            buffer = io.StringIO()

            def fake_run_conversion(*, sources, out_dir, overwrite, to_format, pdf_engine, progress_callback):
                progress_callback(
                    {
                        "type": "MODEL_DOWNLOAD_STARTED",
                        "engine": "marker",
                        "message": "首次使用 Marker，需要先下载模型，下载完成后会继续转换。",
                    }
                )
                return {
                    "ok": True,
                    "count": 1,
                    "results": [{"ok": True, "input": str(src), "output": str(out_dir / 'book.md')}],
                    "notices": [{"type": "MODEL_DOWNLOAD_STARTED", "engine": "marker", "message": "首次使用 Marker，需要先下载模型，下载完成后会继续转换。"}],
                }

            with patch("sys.argv", ["ptm", "convert", "--mode", "single", "--paths", str(src)]), patch(
                "pandoc_to_markdown.cli.resolve_sources", return_value=[src]
            ), patch("pandoc_to_markdown.cli.run_conversion", side_effect=fake_run_conversion), redirect_stdout(buffer):
                cli.main()

        self.assertEqual(
            buffer.getvalue().strip().splitlines(),
            [
                "首次使用 Marker，需要先下载模型，下载完成后会继续转换。",
                f"OK {src} -> {Path(cli.__file__).resolve().parents[2] / 'outputs' / 'book.md'}",
            ],
        )

    def test_main_convert_text_mode_prints_marker_cpu_retry_notice_before_result(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            src = (Path(tmp_dir) / "book.pdf").resolve()
            src.write_text("pdf", encoding="utf-8")
            buffer = io.StringIO()

            def fake_run_conversion(*, sources, out_dir, overwrite, to_format, pdf_engine, progress_callback):
                progress_callback(
                    {
                        "type": "MARKER_RETRY_CPU",
                        "engine": "marker",
                        "message": "Marker 在当前加速设备上失败，正在切到 CPU 重试，可能会更慢。",
                    }
                )
                return {
                    "ok": True,
                    "count": 1,
                    "results": [{"ok": True, "input": str(src), "output": str(out_dir / 'book.md')}],
                    "notices": [{"type": "MARKER_RETRY_CPU", "engine": "marker", "message": "Marker 在当前加速设备上失败，正在切到 CPU 重试，可能会更慢。"}],
                }

            with patch("sys.argv", ["ptm", "convert", "--mode", "single", "--paths", str(src)]), patch(
                "pandoc_to_markdown.cli.resolve_sources", return_value=[src]
            ), patch("pandoc_to_markdown.cli.run_conversion", side_effect=fake_run_conversion), redirect_stdout(buffer):
                cli.main()

        self.assertEqual(
            buffer.getvalue().strip().splitlines(),
            [
                "Marker 在当前加速设备上失败，正在切到 CPU 重试，可能会更慢。",
                f"OK {src} -> {Path(cli.__file__).resolve().parents[2] / 'outputs' / 'book.md'}",
            ],
        )

    def test_main_convert_failure_exits_with_status_one(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            src = Path(tmp_dir) / "book.html"
            src.write_text("<h1>x</h1>", encoding="utf-8")
            payload = {"ok": False, "count": 1, "results": [{"ok": False, "input": str(src), "error": "PANDOC_FAILED"}]}
            with patch("sys.argv", ["ptm", "convert", "--mode", "single", "--paths", str(src), "--json"]), patch(
                "pandoc_to_markdown.cli.resolve_sources", return_value=[src]
            ), patch("pandoc_to_markdown.cli.run_conversion", return_value=payload), self.assertRaises(SystemExit) as ctx:
                cli.main()

        self.assertEqual(ctx.exception.code, 1)

    def test_main_doctor_failure_exits_with_status_one(self) -> None:
        buffer = io.StringIO()
        with patch("sys.argv", ["ptm", "doctor", "--json"]), patch(
            "pandoc_to_markdown.cli.build_report", return_value={"ok": False}
        ) as build_report, patch("pandoc_to_markdown.cli.print_report") as print_report, self.assertRaises(SystemExit) as ctx, redirect_stdout(buffer):
            cli.main()

        self.assertEqual(ctx.exception.code, 1)
        build_report.assert_called_once()
        print_report.assert_called_once_with({"ok": False}, True)

    def test_main_install_passes_python_argument(self) -> None:
        payload = {"envs_root": "/tmp/.venvs", "python_version": "3.12.2"}
        buffer = io.StringIO()
        with patch("sys.argv", ["ptm", "install", "--python", "/opt/homebrew/bin/python3.12", "--json"]), patch(
            "pandoc_to_markdown.cli.run_install", return_value=payload
        ) as run_install, redirect_stdout(buffer):
            cli.main()

        project_root = Path(cli.__file__).resolve().parents[2]
        run_install.assert_called_once_with(
            project_root,
            explicit_python="/opt/homebrew/bin/python3.12",
            preload_models=False,
            model_source="huggingface",
            model_type="all",
        )
        self.assertEqual(json.loads(buffer.getvalue()), payload)

    def test_main_install_passes_model_download_options(self) -> None:
        payload = {"envs_root": "/tmp/.venvs", "python_version": "3.12.2", "models_status": "downloaded"}
        buffer = io.StringIO()
        with patch(
            "sys.argv",
            [
                "ptm",
                "install",
                "--python",
                "/opt/homebrew/bin/python3.12",
                "--preload-models",
                "--model-source",
                "modelscope",
                "--model-type",
                "pipeline",
                "--json",
            ],
        ), patch("pandoc_to_markdown.cli.run_install", return_value=payload) as run_install, redirect_stdout(buffer):
            cli.main()

        project_root = Path(cli.__file__).resolve().parents[2]
        run_install.assert_called_once_with(
            project_root,
            explicit_python="/opt/homebrew/bin/python3.12",
            preload_models=True,
            model_source="modelscope",
            model_type="pipeline",
        )
        self.assertEqual(json.loads(buffer.getvalue()), payload)


if __name__ == "__main__":
    unittest.main()


if __name__ == "__main__":
    unittest.main()
