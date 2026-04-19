import json
import os
import subprocess
import sys
from pathlib import Path

MODEL_SOURCES = ("huggingface", "modelscope")
MODEL_TYPES = ("pipeline", "vlm", "all")

from pandoc_to_markdown.bootstrap import ensure_pandoc
from pandoc_to_markdown.config import (
    CORE_ENV_NAME,
    MANAGED_ENVS_DIRNAME,
    MARKER_ENV_NAME,
    MARKER_PACKAGE_NAME,
    MINERU_ENV_NAME,
    MINERU_PACKAGE_NAME,
    PYPANDOC_PACKAGE_NAME,
)

SUPPORTED_MIN = (3, 10)
SUPPORTED_MAX_EXCLUSIVE = (3, 14)
CORE_DEPENDENCIES = [PYPANDOC_PACKAGE_NAME]
MARKER_DEPENDENCIES = [MARKER_PACKAGE_NAME]
MINERU_DEPENDENCIES = [MINERU_PACKAGE_NAME]
ENV_DEPENDENCIES = {
    CORE_ENV_NAME: CORE_DEPENDENCIES,
    MARKER_ENV_NAME: MARKER_DEPENDENCIES,
    MINERU_ENV_NAME: MINERU_DEPENDENCIES,
}
CLI_BY_ENV = {
    CORE_ENV_NAME: [],
    MARKER_ENV_NAME: ["marker_single"],
    MINERU_ENV_NAME: ["mineru", "mineru-models-download"],
}


def _probe_python(python_bin: str) -> tuple[int, int, int] | None:
    try:
        proc = subprocess.run(
            [python_bin, "-c", "import json, sys; print(json.dumps(sys.version_info[:3]))"],
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        return None
    if proc.returncode != 0:
        return None
    try:
        major, minor, patch = json.loads(proc.stdout.strip())
        return int(major), int(minor), int(patch)
    except Exception:
        return None


def is_supported_python(version: tuple[int, int, int]) -> bool:
    return SUPPORTED_MIN <= version[:2] < SUPPORTED_MAX_EXCLUSIVE


def find_supported_python(explicit_python: str | None = None) -> tuple[str, tuple[int, int, int]]:
    candidates = []
    if explicit_python:
        candidates.append(explicit_python)
    candidates.extend([
        sys.executable,
        "python3.13",
        "python3.12",
        "python3.11",
        "python3.10",
    ])

    seen = set()
    for candidate in candidates:
        if candidate in seen:
            continue
        seen.add(candidate)
        version = _probe_python(candidate)
        if version and is_supported_python(version):
            return candidate, version

    raise RuntimeError("No supported Python found. MinerU requires Python 3.10-3.13.")


def get_envs_root(project_root: Path) -> Path:
    return project_root / MANAGED_ENVS_DIRNAME


def get_env_dir(project_root: Path, env_name: str) -> Path:
    return get_envs_root(project_root) / env_name


def create_venv(venv_dir: Path, python_bin: str) -> Path:
    if venv_dir.exists():
        return venv_dir

    proc = subprocess.run([python_bin, "-m", "venv", str(venv_dir)], capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError((proc.stderr or proc.stdout).strip() or "Failed to create virtual environment.")
    return venv_dir


def get_venv_python(venv_dir: Path) -> Path:
    if os.name == "nt":
        return venv_dir / "Scripts" / "python.exe"
    return venv_dir / "bin" / "python"


def get_venv_bin_dir(venv_dir: Path) -> Path:
    if os.name == "nt":
        return venv_dir / "Scripts"
    return venv_dir / "bin"


def get_env_python(project_root: Path, env_name: str) -> Path:
    return get_venv_python(get_env_dir(project_root, env_name))


def get_env_executable(project_root: Path, env_name: str, executable_name: str) -> Path:
    bin_dir = get_venv_bin_dir(get_env_dir(project_root, env_name))
    if os.name == "nt":
        return bin_dir / f"{executable_name}.exe"
    return bin_dir / executable_name


def install_dependencies(venv_python: Path, dependencies: list[str]) -> None:
    commands = [
        [str(venv_python), "-m", "pip", "install", "--upgrade", "pip", "setuptools", "wheel"],
        [str(venv_python), "-m", "pip", "install", *dependencies],
    ]
    for command in commands:
        proc = subprocess.run(command, capture_output=True, text=True)
        if proc.returncode != 0:
            raise RuntimeError((proc.stderr or proc.stdout).strip() or f"Command failed: {' '.join(command)}")


def preload_pandoc(project_root: Path, venv_python: Path) -> str:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(project_root / "src")
    proc = subprocess.run(
        [str(venv_python), "-c", "from pandoc_to_markdown.bootstrap import ensure_pandoc; print(ensure_pandoc())"],
        capture_output=True,
        text=True,
        env=env,
    )
    if proc.returncode != 0:
        raise RuntimeError((proc.stderr or proc.stdout).strip() or "Failed to preload pandoc.")
    return proc.stdout.strip().splitlines()[-1]


def install_env(project_root: Path, env_name: str, python_bin: str) -> dict:
    env_dir = create_venv(get_env_dir(project_root, env_name), python_bin)
    venv_python = get_venv_python(env_dir)
    install_dependencies(venv_python, ENV_DEPENDENCIES[env_name])

    installed_cli = []
    missing_cli = []
    for executable_name in CLI_BY_ENV[env_name]:
        executable = get_env_executable(project_root, env_name, executable_name)
        if executable.exists():
            installed_cli.append(str(executable))
        else:
            missing_cli.append(executable_name)

    return {
        "name": env_name,
        "venv": str(env_dir),
        "python": str(venv_python),
        "dependencies": ENV_DEPENDENCIES[env_name],
        "executables": installed_cli,
        "missing_executables": missing_cli,
    }


def download_mineru_models(project_root: Path, model_source: str = "huggingface", model_type: str = "all") -> dict:
    if model_source not in MODEL_SOURCES:
        raise RuntimeError(f"Unsupported MinerU model source: {model_source}")
    if model_type not in MODEL_TYPES:
        raise RuntimeError(f"Unsupported MinerU model type: {model_type}")

    executable = get_env_executable(project_root, MINERU_ENV_NAME, "mineru-models-download")
    if not executable.exists():
        raise RuntimeError("mineru-models-download is unavailable in the managed MinerU environment.")

    command = [str(executable), "--source", model_source, "--model_type", model_type]
    proc = subprocess.run(command, capture_output=True, text=True)
    detail = (proc.stderr or proc.stdout).strip()
    if proc.returncode != 0:
        raise RuntimeError(detail or "MinerU model download failed.")

    return {
        "ok": True,
        "command": command,
        "model_source": model_source,
        "model_type": model_type,
        "detail": detail,
    }


def run_install(
    project_root: Path,
    explicit_python: str | None = None,
    preload_models: bool = False,
    model_source: str = "huggingface",
    model_type: str = "all",
) -> dict:
    python_bin, version = find_supported_python(explicit_python)
    get_envs_root(project_root).mkdir(parents=True, exist_ok=True)

    core_env = install_env(project_root, CORE_ENV_NAME, python_bin)
    pandoc_path = preload_pandoc(project_root, get_env_python(project_root, CORE_ENV_NAME))
    marker_env = install_env(project_root, MARKER_ENV_NAME, python_bin)
    mineru_env = install_env(project_root, MINERU_ENV_NAME, python_bin)

    result = {
        "ok": True,
        "python": python_bin,
        "python_version": ".".join(map(str, version)),
        "envs_root": str(get_envs_root(project_root)),
        "envs": {
            CORE_ENV_NAME: core_env,
            MARKER_ENV_NAME: marker_env,
            MINERU_ENV_NAME: mineru_env,
        },
        "pandoc": pandoc_path,
        "models_downloaded": False,
    }

    if preload_models:
        models_result = download_mineru_models(project_root, model_source=model_source, model_type=model_type)
        result["models_downloaded"] = True
        result["models_status"] = "downloaded"
        result["models_source"] = models_result["model_source"]
        result["models_type"] = models_result["model_type"]
        result["models_detail"] = models_result["detail"]

    return result
