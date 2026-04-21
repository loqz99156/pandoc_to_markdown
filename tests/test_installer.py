import tempfile
import unittest
from pathlib import Path
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


class RunInstallTests(unittest.TestCase):
    def test_run_install_returns_envs_and_mineru_state(self) -> None:
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
            ):
                result = installer.run_install(project_root, explicit_python="python3.12")

        self.assertTrue(result["ok"])
        self.assertEqual(result["python"], "python3.12")
        self.assertEqual(result["python_version"], "3.12.2")
        self.assertEqual(result["pandoc"], "/bin/pandoc")
        self.assertIn("core", result["envs"])
        self.assertIn("marker", result["envs"])
        self.assertIn("mineru", result["envs"])
        self.assertIn("mineru", result)
        self.assertNotIn("models_downloaded", result)
        self.assertNotIn("models_status", result)


if __name__ == "__main__":
    unittest.main()
