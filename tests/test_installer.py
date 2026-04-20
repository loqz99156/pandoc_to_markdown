import tempfile
import unittest
from pathlib import Path
from subprocess import CompletedProcess
from unittest.mock import patch

from pandoc_to_markdown import installer


class MineruProjectHelpersTests(unittest.TestCase):
    def test_build_mineru_env_prefers_project_local_models_when_present(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_root = Path(tmp_dir)
            pipeline_dir = installer.get_mineru_snapshot_root(project_root, "pipeline") / "snap-a"
            pipeline_dir.mkdir(parents=True)

            env = installer.build_mineru_env(project_root)

        self.assertEqual(env["MINERU_MODEL_SOURCE"], "local")
        self.assertEqual(env["MINERU_TOOLS_CONFIG_JSON"], str(installer.get_mineru_project_config_path(project_root)))
        self.assertEqual(env["HF_HOME"], str(installer.get_mineru_hf_home(project_root)))
        self.assertEqual(env["HUGGINGFACE_HUB_CACHE"], str(installer.get_mineru_hub_root(project_root)))

    def test_migrate_global_mineru_models_copies_known_global_paths_into_project(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_root = Path(tmp_dir)
            global_home = Path(tmp_dir) / "home"
            global_home.mkdir()
            pipeline_source = global_home / ".cache" / "huggingface" / "hub" / "models--opendatalab--PDF-Extract-Kit-1.0" / "snapshots" / "snap-p"
            vlm_source = global_home / ".cache" / "huggingface" / "hub" / "models--opendatalab--MinerU2.5-Pro-2604-1.2B" / "snapshots" / "snap-v"
            (pipeline_source / "models").mkdir(parents=True)
            (vlm_source / "weights").mkdir(parents=True)
            (pipeline_source / "models" / "a.txt").write_text("a", encoding="utf-8")
            (vlm_source / "weights" / "b.txt").write_text("b", encoding="utf-8")
            (global_home / "mineru.json").write_text(
                '{"models-dir":{"pipeline":"%s","vlm":"%s"}}' % (pipeline_source, vlm_source),
                encoding="utf-8",
            )

            with patch("pandoc_to_markdown.installer.Path.home", return_value=global_home):
                migrated = installer.migrate_global_mineru_models(project_root)
                project_pipeline = installer.discover_project_mineru_model_dir(project_root, "pipeline")
                project_vlm = installer.discover_project_mineru_model_dir(project_root, "vlm")

                self.assertEqual(migrated["pipeline"], str(project_pipeline))
                self.assertEqual(migrated["vlm"], str(project_vlm))
                self.assertTrue((project_pipeline / "models" / "a.txt").exists())
                self.assertTrue((project_vlm / "weights" / "b.txt").exists())


class DownloadMineruModelsTests(unittest.TestCase):
    def test_download_mineru_models_builds_non_interactive_command_with_project_env(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_root = Path(tmp_dir)
            executable = project_root / ".venvs" / "mineru" / "bin" / "mineru-models-download"
            executable.parent.mkdir(parents=True)
            executable.write_text("", encoding="utf-8")
            pipeline_dir = installer.get_mineru_snapshot_root(project_root, "pipeline") / "snap-a"
            vlm_dir = installer.get_mineru_snapshot_root(project_root, "vlm") / "snap-b"
            pipeline_dir.mkdir(parents=True)
            vlm_dir.mkdir(parents=True)

            with patch(
                "pandoc_to_markdown.installer.subprocess.run",
                return_value=CompletedProcess(args=[], returncode=0, stdout="done", stderr=""),
            ) as run:
                result = installer.download_mineru_models(project_root, model_source="huggingface", model_type="pipeline")

        run.assert_called_once_with(
            [str(executable), "--source", "huggingface", "--model_type", "pipeline"],
            capture_output=True,
            text=True,
            env=installer.build_mineru_env(project_root, model_source="huggingface"),
        )
        self.assertTrue(result["ok"])
        self.assertEqual(result["model_source"], "huggingface")
        self.assertEqual(result["model_type"], "pipeline")
        self.assertEqual(result["detail"], "done")
        self.assertEqual(result["pipeline_path"], str(pipeline_dir))
        self.assertEqual(result["vlm_path"], str(vlm_dir))

    def test_download_mineru_models_fails_when_executable_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_root = Path(tmp_dir)
            with self.assertRaisesRegex(RuntimeError, "unavailable"):
                installer.download_mineru_models(project_root)


class RunInstallTests(unittest.TestCase):
    def test_run_install_reuses_existing_project_local_models(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_root = Path(tmp_dir)
            existing_pipeline = installer.get_mineru_snapshot_root(project_root, "pipeline") / "snap-a"
            existing_pipeline.mkdir(parents=True)

            with patch("pandoc_to_markdown.installer.find_supported_python", return_value=("python3.12", (3, 12, 2))), patch(
                "pandoc_to_markdown.installer.install_env",
                side_effect=[
                    {"name": "core", "venv": "core", "python": "core-python", "dependencies": [], "executables": [], "missing_executables": []},
                    {"name": "marker", "venv": "marker", "python": "marker-python", "dependencies": [], "executables": [], "missing_executables": []},
                    {"name": "mineru", "venv": "mineru", "python": "mineru-python", "dependencies": [], "executables": [], "missing_executables": []},
                ],
            ), patch("pandoc_to_markdown.installer.get_env_python", return_value=project_root / ".venvs" / "core" / "bin" / "python"), patch(
                "pandoc_to_markdown.installer.preload_pandoc", return_value="/bin/pandoc"
            ), patch("pandoc_to_markdown.installer.migrate_global_mineru_models", return_value={}), patch(
                "pandoc_to_markdown.installer.download_mineru_models"
            ) as download_models:
                result = installer.run_install(
                    project_root,
                    explicit_python="python3.12",
                    preload_models=True,
                    model_source="huggingface",
                    model_type="pipeline",
                )

        download_models.assert_not_called()
        self.assertFalse(result["models_downloaded"])
        self.assertEqual(result["models_status"], "reused")
        self.assertEqual(result["models_source"], "local")
        self.assertEqual(result["models_type"], "pipeline")

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
            ), patch("pandoc_to_markdown.installer.migrate_global_mineru_models", return_value={}), patch(
                "pandoc_to_markdown.installer.download_mineru_models",
                return_value={
                    "ok": True,
                    "model_source": "modelscope",
                    "model_type": "vlm",
                    "detail": "downloaded",
                    "pipeline_path": None,
                    "vlm_path": str(project_root / ".models" / "mineru" / "huggingface" / "hub" / "x"),
                },
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
