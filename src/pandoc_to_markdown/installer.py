import json
import os
import shutil
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
    MINERU_PIPELINE_REPO_DIRNAME,
    MINERU_PROJECT_CONFIG_FILENAME,
    MINERU_PROJECT_DIRNAME,
    MINERU_PROJECT_HF_HOME_DIRNAME,
    MINERU_VLM_REPO_DIRNAME,
    PACKAGE_INSTALL_ATTEMPTS,
    PACKAGE_INSTALL_RETRY_DELAY_SECONDS,
    PROJECT_MODELS_DIRNAME,
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
MINERU_REPO_DIR_BY_MODEL_TYPE = {
    "pipeline": MINERU_PIPELINE_REPO_DIRNAME,
    "vlm": MINERU_VLM_REPO_DIRNAME,
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


def get_mineru_assets_root(project_root: Path) -> Path:
    return project_root / PROJECT_MODELS_DIRNAME / MINERU_PROJECT_DIRNAME


def get_mineru_project_config_path(project_root: Path) -> Path:
    return get_mineru_assets_root(project_root) / MINERU_PROJECT_CONFIG_FILENAME


def get_mineru_hf_home(project_root: Path) -> Path:
    return get_mineru_assets_root(project_root) / MINERU_PROJECT_HF_HOME_DIRNAME


def get_mineru_hub_root(project_root: Path) -> Path:
    return get_mineru_hf_home(project_root) / "hub"


def get_mineru_snapshot_root(project_root: Path, model_type: str) -> Path:
    return get_mineru_hub_root(project_root) / MINERU_REPO_DIR_BY_MODEL_TYPE[model_type] / "snapshots"


def get_global_mineru_config_path() -> Path:
    return Path.home() / MINERU_PROJECT_CONFIG_FILENAME


def _read_json_file(path: Path) -> dict | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _write_json_file(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=4), encoding="utf-8")


def _get_mineru_config_models_dir(config: dict | None) -> dict[str, str]:
    if not isinstance(config, dict):
        return {}
    models_dir = config.get("models-dir")
    if not isinstance(models_dir, dict):
        return {}
    return {key: value for key, value in models_dir.items() if isinstance(value, str)}


def _get_configured_model_dir(config: dict | None, model_type: str) -> Path | None:
    path = _get_mineru_config_models_dir(config).get(model_type)
    if not path:
        return None
    return Path(path).expanduser()


def _path_is_within(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def _find_latest_snapshot_dir(snapshot_root: Path) -> Path | None:
    if not snapshot_root.exists():
        return None
    candidates = [item for item in snapshot_root.iterdir() if item.is_dir()]
    if not candidates:
        return None
    candidates.sort(key=lambda item: item.stat().st_mtime, reverse=True)
    return candidates[0]


def discover_project_mineru_model_dir(project_root: Path, model_type: str) -> Path | None:
    project_config = _read_json_file(get_mineru_project_config_path(project_root))
    configured = _get_configured_model_dir(project_config, model_type)
    if configured is not None and configured.exists() and _path_is_within(configured, project_root):
        return configured
    return _find_latest_snapshot_dir(get_mineru_snapshot_root(project_root, model_type))


def _load_project_mineru_base_config(project_root: Path) -> dict:
    project_config = _read_json_file(get_mineru_project_config_path(project_root))
    if isinstance(project_config, dict):
        return project_config
    global_config = _read_json_file(get_global_mineru_config_path())
    if isinstance(global_config, dict):
        return global_config
    return {}


def sync_project_mineru_config(project_root: Path) -> Path:
    config_path = get_mineru_project_config_path(project_root)
    base_config = _load_project_mineru_base_config(project_root)
    models_dir = {
        model_type: str(path)
        for model_type in ("pipeline", "vlm")
        if (path := discover_project_mineru_model_dir(project_root, model_type)) is not None
    }

    if not models_dir and not config_path.exists():
        return config_path

    payload = dict(base_config)
    payload["models-dir"] = models_dir
    _write_json_file(config_path, payload)
    return config_path


def _copy_model_tree(source_dir: Path, destination_dir: Path) -> Path:
    destination_dir.parent.mkdir(parents=True, exist_ok=True)
    if source_dir.resolve() == destination_dir.resolve():
        return destination_dir
    shutil.copytree(source_dir, destination_dir, dirs_exist_ok=True)
    return destination_dir


def migrate_global_mineru_models(project_root: Path) -> dict[str, str]:
    global_config = _read_json_file(get_global_mineru_config_path())
    if global_config is None:
        return {}

    migrated: dict[str, str] = {}
    for model_type in ("pipeline", "vlm"):
        if discover_project_mineru_model_dir(project_root, model_type) is not None:
            continue
        source_dir = _get_configured_model_dir(global_config, model_type)
        if source_dir is None or not source_dir.exists() or not source_dir.is_dir():
            continue
        destination_dir = get_mineru_snapshot_root(project_root, model_type) / source_dir.name
        migrated[model_type] = str(_copy_model_tree(source_dir, destination_dir))

    if migrated:
        sync_project_mineru_config(project_root)

    return migrated


def build_mineru_env(project_root: Path, model_source: str | None = None) -> dict[str, str]:
    assets_root = get_mineru_assets_root(project_root)
    assets_root.mkdir(parents=True, exist_ok=True)

    env = os.environ.copy()
    env["MINERU_TOOLS_CONFIG_JSON"] = str(get_mineru_project_config_path(project_root))
    env["HF_HOME"] = str(get_mineru_hf_home(project_root))
    env["HUGGINGFACE_HUB_CACHE"] = str(get_mineru_hub_root(project_root))

    effective_model_source = model_source
    if effective_model_source is None:
        pipeline_dir = discover_project_mineru_model_dir(project_root, "pipeline")
        if pipeline_dir is not None:
            sync_project_mineru_config(project_root)
            effective_model_source = "local"

    if effective_model_source is not None:
        env["MINERU_MODEL_SOURCE"] = effective_model_source

    return env


def get_mineru_project_state(project_root: Path) -> dict:
    config_path = get_mineru_project_config_path(project_root)
    pipeline_dir = discover_project_mineru_model_dir(project_root, "pipeline")
    vlm_dir = discover_project_mineru_model_dir(project_root, "vlm")
    model_source = os.environ.get("MINERU_MODEL_SOURCE") or ("local" if pipeline_dir is not None else "huggingface")

    return {
        "assets_root": str(get_mineru_assets_root(project_root)),
        "config_exists": config_path.exists(),
        "config_path": str(config_path),
        "hf_home": str(get_mineru_hf_home(project_root)),
        "model_source": model_source,
        "pipeline_path": str(pipeline_dir) if pipeline_dir is not None else None,
        "pipeline_exists": pipeline_dir is not None,
        "vlm_path": str(vlm_dir) if vlm_dir is not None else None,
        "vlm_exists": vlm_dir is not None,
        "global_config_exists": get_global_mineru_config_path().exists(),
        "global_config_path": str(get_global_mineru_config_path()),
    }


def has_project_mineru_models(project_root: Path, model_type: str) -> bool:
    required_types = ("pipeline", "vlm") if model_type == "all" else (model_type,)
    return all(discover_project_mineru_model_dir(project_root, item) is not None for item in required_types)


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
    proc = subprocess.run(command, capture_output=True, text=True, env=build_mineru_env(project_root, model_source=model_source))
    detail = (proc.stderr or proc.stdout).strip()
    if proc.returncode != 0:
        raise RuntimeError(detail or "MinerU model download failed.")

    sync_project_mineru_config(project_root)
    project_state = get_mineru_project_state(project_root)
    return {
        "ok": True,
        "command": command,
        "model_source": model_source,
        "model_type": model_type,
        "detail": detail,
        "config_path": project_state["config_path"],
        "hf_home": project_state["hf_home"],
        "pipeline_path": project_state["pipeline_path"],
        "vlm_path": project_state["vlm_path"],
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

    migrated_models = migrate_global_mineru_models(project_root)
    sync_project_mineru_config(project_root)

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
        "models_migrated": migrated_models,
        "mineru": get_mineru_project_state(project_root),
    }

    if preload_models:
        if has_project_mineru_models(project_root, model_type):
            result["models_status"] = "migrated" if migrated_models else "reused"
            result["models_source"] = "local"
            result["models_type"] = model_type
            result["models_detail"] = (
                "Migrated existing MinerU models into the project." if migrated_models else "Reused project-local MinerU models."
            )
        else:
            models_result = download_mineru_models(project_root, model_source=model_source, model_type=model_type)
            result["models_downloaded"] = True
            result["models_status"] = "downloaded"
            result["models_source"] = models_result["model_source"]
            result["models_type"] = models_result["model_type"]
            result["models_detail"] = models_result["detail"]
            result["mineru"] = get_mineru_project_state(project_root)

    return result
