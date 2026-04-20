import tempfile
import unittest
from collections import namedtuple
from pathlib import Path
from unittest.mock import patch

DiskUsage = namedtuple("usage", ["total", "used", "free"])

from pandoc_to_markdown import doctor


class BuildReportTests(unittest.TestCase):
    def test_build_report_is_ok_when_envs_and_required_cli_exist(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_root = Path(tmp_dir)
            envs_root = project_root / ".venvs"
            envs_root.mkdir()
            env_reports = {
                "core": {"path": "core", "exists": True, "python": "py", "python_version": "3.12.0", "cli": {"pandoc": "/bin/pandoc"}},
                "marker": {"path": "marker", "exists": True, "python": "py", "python_version": "3.12.0", "cli": {"marker_single": "/bin/marker_single"}},
                "mineru": {
                    "path": "mineru",
                    "exists": True,
                    "python": "py",
                    "python_version": "3.12.0",
                    "cli": {"mineru": "/bin/mineru", "mineru-models-download": "/bin/mineru-models-download"},
                },
            }
            mineru_state = {
                "assets_root": str(project_root / ".models" / "mineru"),
                "config_exists": True,
                "config_path": str(project_root / ".models" / "mineru" / "mineru.json"),
                "hf_home": str(project_root / ".models" / "mineru" / "huggingface"),
                "model_source": "local",
                "pipeline_path": str(project_root / ".models" / "mineru" / "huggingface" / "hub" / "pipeline"),
                "pipeline_exists": True,
                "vlm_path": None,
                "vlm_exists": False,
                "global_config_exists": False,
                "global_config_path": "/Users/x/mineru.json",
            }

            with patch("pandoc_to_markdown.doctor._build_env_report", side_effect=lambda _root, env_name, _executables: env_reports[env_name]), patch(
                "pandoc_to_markdown.doctor.resolve_cli_path",
                side_effect=lambda name: f"/resolved/{name}",
            ), patch("pandoc_to_markdown.doctor.get_mineru_project_state", return_value=mineru_state), patch(
                "pandoc_to_markdown.doctor.shutil.disk_usage", return_value=DiskUsage(100, 40, 60)
            ), patch("pandoc_to_markdown.doctor.is_supported_python", return_value=True), patch.object(doctor.sys, "version_info", (3, 12, 1)):
                report = doctor.build_report(project_root)

        self.assertTrue(report["ok"])
        self.assertEqual(report["warnings"], [])
        self.assertEqual(report["cli"]["pandoc"], "/resolved/pandoc")
        self.assertEqual(report["mineru"]["model_source"], "local")

    def test_build_report_is_not_ok_when_required_cli_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_root = Path(tmp_dir)
            envs_root = project_root / ".venvs"
            envs_root.mkdir()
            env_reports = {
                "core": {"path": "core", "exists": True, "python": "py", "python_version": "3.12.0", "cli": {"pandoc": None}},
                "marker": {"path": "marker", "exists": True, "python": "py", "python_version": "3.12.0", "cli": {"marker_single": "/bin/marker_single"}},
                "mineru": {
                    "path": "mineru",
                    "exists": True,
                    "python": "py",
                    "python_version": "3.12.0",
                    "cli": {"mineru": "/bin/mineru", "mineru-models-download": "/bin/mineru-models-download"},
                },
            }

            with patch("pandoc_to_markdown.doctor._build_env_report", side_effect=lambda _root, env_name, _executables: env_reports[env_name]), patch(
                "pandoc_to_markdown.doctor.resolve_cli_path", return_value=None
            ), patch("pandoc_to_markdown.doctor.get_mineru_project_state", return_value={
                "assets_root": "x",
                "config_exists": False,
                "config_path": "x",
                "hf_home": "x",
                "model_source": "huggingface",
                "pipeline_path": None,
                "pipeline_exists": False,
                "vlm_path": None,
                "vlm_exists": False,
                "global_config_exists": False,
                "global_config_path": "x",
            }), patch("pandoc_to_markdown.doctor.shutil.disk_usage", return_value=DiskUsage(100, 40, 60)), patch(
                "pandoc_to_markdown.doctor.is_supported_python", return_value=True
            ), patch.object(doctor.sys, "version_info", (3, 12, 1)):
                report = doctor.build_report(project_root)

        self.assertFalse(report["ok"])

    def test_build_report_keeps_warning_only_for_unsupported_launcher_python(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_root = Path(tmp_dir)
            envs_root = project_root / ".venvs"
            envs_root.mkdir()
            env_reports = {
                "core": {"path": "core", "exists": True, "python": "py", "python_version": "3.12.0", "cli": {"pandoc": "/bin/pandoc"}},
                "marker": {"path": "marker", "exists": True, "python": "py", "python_version": "3.12.0", "cli": {"marker_single": "/bin/marker_single"}},
                "mineru": {
                    "path": "mineru",
                    "exists": True,
                    "python": "py",
                    "python_version": "3.12.0",
                    "cli": {"mineru": "/bin/mineru", "mineru-models-download": "/bin/mineru-models-download"},
                },
            }

            with patch("pandoc_to_markdown.doctor._build_env_report", side_effect=lambda _root, env_name, _executables: env_reports[env_name]), patch(
                "pandoc_to_markdown.doctor.resolve_cli_path", return_value=None
            ), patch("pandoc_to_markdown.doctor.get_mineru_project_state", return_value={
                "assets_root": "x",
                "config_exists": True,
                "config_path": "x",
                "hf_home": "x",
                "model_source": "local",
                "pipeline_path": "x",
                "pipeline_exists": True,
                "vlm_path": None,
                "vlm_exists": False,
                "global_config_exists": False,
                "global_config_path": "x",
            }), patch("pandoc_to_markdown.doctor.shutil.disk_usage", return_value=DiskUsage(100, 40, 60)), patch(
                "pandoc_to_markdown.doctor.is_supported_python", return_value=False
            ), patch.object(doctor.sys, "version_info", (3, 14, 0)):
                report = doctor.build_report(project_root)

        self.assertTrue(report["ok"])
        self.assertEqual(
            report["warnings"],
            ["Current launcher Python is outside MinerU's supported range, but the managed environments can still be healthy."],
        )

    def test_build_report_warns_when_only_global_mineru_config_exists(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_root = Path(tmp_dir)
            envs_root = project_root / ".venvs"
            envs_root.mkdir()
            env_reports = {
                "core": {"path": "core", "exists": True, "python": "py", "python_version": "3.12.0", "cli": {"pandoc": "/bin/pandoc"}},
                "marker": {"path": "marker", "exists": True, "python": "py", "python_version": "3.12.0", "cli": {"marker_single": "/bin/marker_single"}},
                "mineru": {
                    "path": "mineru",
                    "exists": True,
                    "python": "py",
                    "python_version": "3.12.0",
                    "cli": {"mineru": "/bin/mineru", "mineru-models-download": "/bin/mineru-models-download"},
                },
            }

            with patch("pandoc_to_markdown.doctor._build_env_report", side_effect=lambda _root, env_name, _executables: env_reports[env_name]), patch(
                "pandoc_to_markdown.doctor.resolve_cli_path", side_effect=lambda name: f"/resolved/{name}"
            ), patch("pandoc_to_markdown.doctor.get_mineru_project_state", return_value={
                "assets_root": "x",
                "config_exists": False,
                "config_path": "x",
                "hf_home": "x",
                "model_source": "huggingface",
                "pipeline_path": None,
                "pipeline_exists": False,
                "vlm_path": None,
                "vlm_exists": False,
                "global_config_exists": True,
                "global_config_path": "/Users/x/mineru.json",
            }), patch("pandoc_to_markdown.doctor.shutil.disk_usage", return_value=DiskUsage(100, 40, 60)), patch(
                "pandoc_to_markdown.doctor.is_supported_python", return_value=True
            ), patch.object(doctor.sys, "version_info", (3, 12, 0)):
                report = doctor.build_report(project_root)

        self.assertEqual(
            report["warnings"],
            ["A global ~/mineru.json exists, but this project has not created its own project-local MinerU config yet."],
        )


if __name__ == "__main__":
    unittest.main()
