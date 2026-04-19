#!/usr/bin/env python3
import os
import subprocess
import sys
from pathlib import Path


SKILL_DIR_NAME = "pandoc_to_markdown"
PROJECT_ROOT_FILE = ".project-root"


def resolve_project_root() -> Path:
    override = os.environ.get("PANDOC_TO_MARKDOWN_PROJECT_ROOT")
    if override:
        return Path(override).expanduser().resolve()

    marker_file = Path(__file__).resolve().with_name(PROJECT_ROOT_FILE)
    if marker_file.exists():
        root = marker_file.read_text(encoding="utf-8").strip()
        if root:
            return Path(root).expanduser().resolve()

    return Path(__file__).resolve().parents[3]


def resolve_runner_python(project_root: Path) -> Path:
    if os.name == "nt":
        managed_python = project_root / ".venvs" / "core" / "Scripts" / "python.exe"
    else:
        managed_python = project_root / ".venvs" / "core" / "bin" / "python"
    if managed_python.exists():
        return managed_python
    return Path(sys.executable).resolve()


def main() -> None:
    project_root = resolve_project_root()
    cli_path = project_root / "src" / "pandoc_to_markdown" / "cli.py"
    if not cli_path.exists():
        raise SystemExit(f"Cannot find CLI entrypoint: {cli_path}")

    runner_python = resolve_runner_python(project_root)
    env = os.environ.copy()
    src_dir = str(project_root / "src")
    existing_pythonpath = env.get("PYTHONPATH")
    env["PYTHONPATH"] = src_dir if not existing_pythonpath else f"{src_dir}{os.pathsep}{existing_pythonpath}"

    command = [str(runner_python), str(cli_path), *sys.argv[1:]]
    proc = subprocess.run(command, env=env)
    raise SystemExit(proc.returncode)


if __name__ == "__main__":
    main()
