#!/usr/bin/env python3
import json
import os
import subprocess
import sys
from pathlib import Path


SKILL_DIR_NAME = "pandoc_to_markdown"
PROJECT_ROOT_FILE = ".project-root"
HISTORY_FILE = "history.json"
LAST_CUSTOM_OUT_DIR_KEY = "last_custom_out_dir"


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


def get_history_path(project_root: Path) -> Path:
    return project_root / ".claude" / "skills" / SKILL_DIR_NAME / HISTORY_FILE


def read_history(path: Path) -> dict | None:
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def read_last_custom_out_dir(project_root: Path) -> Path | None:
    payload = read_history(get_history_path(project_root))
    if not isinstance(payload, dict):
        return None
    value = payload.get(LAST_CUSTOM_OUT_DIR_KEY)
    if not isinstance(value, str) or not value.strip():
        return None
    return Path(value).expanduser().resolve()


def write_last_custom_out_dir(project_root: Path, out_dir: Path) -> None:
    history_path = get_history_path(project_root)
    history_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {LAST_CUSTOM_OUT_DIR_KEY: str(out_dir.expanduser().resolve())}
    history_path.write_text(json.dumps(payload, ensure_ascii=False, indent=4), encoding="utf-8")


def get_effective_out_dir(argv: list[str], project_root: Path) -> Path:
    if "--out-dir" not in argv:
        return (project_root / "outputs").resolve()
    index = argv.index("--out-dir")
    if index + 1 >= len(argv):
        return (project_root / "outputs").resolve()
    return Path(argv[index + 1]).expanduser().resolve()


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

    forwarded_args = list(sys.argv[1:])
    command = [str(runner_python), str(cli_path), *forwarded_args]
    proc = subprocess.run(command, env=env)

    effective_out_dir = get_effective_out_dir(forwarded_args, project_root)
    default_out_dir = (project_root / "outputs").resolve()
    if proc.returncode == 0 and effective_out_dir != default_out_dir:
        write_last_custom_out_dir(project_root, effective_out_dir)

    raise SystemExit(proc.returncode)


if __name__ == "__main__":
    main()
