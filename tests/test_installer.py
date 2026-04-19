import tempfile
import unittest
from pathlib import Path
from subprocess import CompletedProcess
from unittest.mock import patch

from pandoc_to_markdown import installer


class DownloadMineruModelsTests(unittest.TestCase):
    def test_download_mineru_models_builds_non_interactive_command(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_root = Path(tmp_dir)
            executable = project_root / ".venvs" / "mineru" / "bin" / "mineru-models-download"
            executable.parent.mkdir(parents=True)
            executable.write_text("", encoding="utf-8")

            with patch(
                "pandoc_to_markdown.installer.subprocess.run",
                return_value=CompletedProcess(args=[], returncode=0, stdout="done", stderr=""),
            ) as run:
                result = installer.download_mineru_models(project_root, model_source="huggingface", model_type="pipeline")

        run.assert_called_once_with(
            [str(executable), "--source", "huggingface", "--model_type", "pipeline"],
            capture_output=True,
            text=True,
        )
        self.assertTrue(result["ok"])
        self.assertEqual(result["model_source"], "huggingface")
        self.assertEqual(result["model_type"], "pipeline")
        self.assertEqual(result["detail"], "done")

    def test_download_mineru_models_fails_when_executable_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_root = Path(tmp_dir)
            with self.assertRaisesRegex(RuntimeError, "unavailable"):
                installer.download_mineru_models(project_root)


class RunInstallTests(unittest.TestCase):
    def test_run_install_includes_model_download_result_when_requested(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_root = Path(tmp_dir)
            with patch("pandoc_to_markdown.installer.find_supported_python", return_value=("python3.12", (3, 12, 2))), patch(
                "pandoc_to_markdown.installer.install_env",
                side_effect=[
                    {"name": "core", "venv": "core", "python": "core-python", "dependencies": [], "executables": [], "missing_executables": []},
                    {"name": "marker", "venv": "marker", "python": "marker-python", "dependencies": [], "executables": [], "missing_executables": []},
                    {"name": "mineru", "venv": "mineru", "python": "mineru-python", "dependencies": [], "executables": [], "missing_executables": []},
                ],
            ), patch("pandoc_to_markdown.installer.get_env_python", return_value=project_root / ".venvs" / "core" / "bin" / "python"), patch(
                "pandoc_to_markdown.installer.preload_pandoc", return_value="/bin/pandoc"
            ), patch(
                "pandoc_to_markdown.installer.download_mineru_models",
                return_value={"ok": True, "model_source": "modelscope", "model_type": "vlm", "detail": "downloaded"},
            ) as download_models:
                result = installer.run_install(
                    project_root,
                    explicit_python="python3.12",
                    preload_models=True,
                    model_source="modelscope",
                    model_type="vlm",
                )

        download_models.assert_called_once_with(project_root, model_source="modelscope", model_type="vlm")
        self.assertTrue(result["models_downloaded"])
        self.assertEqual(result["models_status"], "downloaded")
        self.assertEqual(result["models_source"], "modelscope")
        self.assertEqual(result["models_type"], "vlm")
        self.assertEqual(result["models_detail"], "downloaded")


if __name__ == "__main__":
    unittest.main()
