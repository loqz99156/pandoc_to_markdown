import json
import shutil
import subprocess
import sys
from pathlib import Path

from pandoc_to_markdown.bootstrap import resolve_cli_path
from pandoc_to_markdown.config import CORE_ENV_NAME, MANAGED_ENVS_DIRNAME, MARKER_ENV_NAME, MINERU_ENV_NAME
from pandoc_to_markdown.installer import (
    SUPPORTED_MAX_EXCLUSIVE,
    SUPPORTED_MIN,
    get_env_dir,
    get_env_executable,
    get_env_python,
    get_mineru_project_state,
    is_supported_python,
)


def _read_python_version(python_path: Path) -> str | None:
    if not python_path.exists():
        return None
    proc = subprocess.run(
        [str(python_path), "-c", "import sys; print('.'.join(map(str, sys.version_info[:3])))"],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        return None
    return proc.stdout.strip() or None


def _build_env_report(project_root: Path, env_name: str, executables: list[str]) -> dict:
    env_dir = get_env_dir(project_root, env_name)
    python_path = get_env_python(project_root, env_name)
    cli = {}
    for executable_name in executables:
        if executable_name == "pandoc":
            cli[executable_name] = resolve_cli_path("pandoc")
            continue
        env_executable = get_env_executable(project_root, env_name, executable_name)
        cli[executable_name] = str(env_executable) if env_executable.exists() else None

    return {
        "path": str(env_dir),
        "exists": env_dir.exists(),
        "python": str(python_path),
        "python_version": _read_python_version(python_path),
        "cli": cli,
    }


def build_report(project_root: Path) -> dict:
    version = sys.version_info[:3]
    envs_root = project_root / MANAGED_ENVS_DIRNAME
    disk = shutil.disk_usage(project_root)

    envs = {
        CORE_ENV_NAME: _build_env_report(project_root, CORE_ENV_NAME, ["pandoc"]),
        MARKER_ENV_NAME: _build_env_report(project_root, MARKER_ENV_NAME, ["marker_single"]),
        MINERU_ENV_NAME: _build_env_report(project_root, MINERU_ENV_NAME, ["mineru"]),
    }

    report = {
        "python": {
            "executable": sys.executable,
            "version": ".".join(map(str, version)),
            "supported": is_supported_python(version),
            "supported_range": f"{SUPPORTED_MIN[0]}.{SUPPORTED_MIN[1]}-{SUPPORTED_MAX_EXCLUSIVE[0]}.{SUPPORTED_MAX_EXCLUSIVE[1]-1}",
        },
        "project": {
            "root": str(project_root),
            "envs_root": str(envs_root),
            "envs_root_exists": envs_root.exists(),
        },
        "cli": {
            "pandoc": resolve_cli_path("pandoc"),
            "marker_single": resolve_cli_path("marker_single"),
            "mineru": resolve_cli_path("mineru"),
        },
        "envs": envs,
        "mineru": get_mineru_project_state(project_root),
        "disk": {
            "free_bytes": disk.free,
            "free_gb": round(disk.free / (1024 ** 3), 2),
        },
    }
    envs_ok = report["project"]["envs_root_exists"] and all(env["exists"] for env in envs.values())
    required_cli_ok = all(all(path is not None for path in env["cli"].values()) for env in envs.values())
    report["ok"] = envs_ok and required_cli_ok
    report["warnings"] = []
    if not report["python"]["supported"]:
        report["warnings"].append(
            "Current launcher Python is outside MinerU's supported range, but the managed environments can still be healthy."
        )
    return report


def print_report(report: dict, as_json: bool) -> None:
    if as_json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return

    print(f"Python: {report['python']['version']} ({'supported' if report['python']['supported'] else 'unsupported'})")
    print(f"Managed env root: {'present' if report['project']['envs_root_exists'] else 'missing'}")
    print(f"pandoc: {report['cli']['pandoc'] or 'missing'}")
    print(f"marker_single: {report['cli']['marker_single'] or 'missing'}")
    print(f"mineru: {report['cli']['mineru'] or 'missing'}")
    for env_name, env in report['envs'].items():
        print(f"{env_name} env: {'present' if env['exists'] else 'missing'} ({env['python_version'] or 'unknown python'})")
    print(f"MinerU assets root: {report['mineru']['assets_root']}")
    print(f"MinerU project config: {'present' if report['mineru']['config_exists'] else 'missing'}")
    print(f"MinerU project model source: {report['mineru']['model_source']}")
    print(f"MinerU pipeline models: {report['mineru']['pipeline_path'] or 'missing'}")
    print(f"MinerU VLM models: {report['mineru']['vlm_path'] or 'missing'}")
    print(f"Free disk: {report['disk']['free_gb']} GB")
