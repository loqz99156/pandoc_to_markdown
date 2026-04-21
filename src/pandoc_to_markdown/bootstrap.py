import contextlib
import importlib
import io
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

from pandoc_to_markdown.config import (
    AUTO_INSTALL_FAILURE_TEMPLATE,
    AUTO_INSTALL_POST_CHECK_TEMPLATE,
    CORE_ENV_NAME,
    DOWNLOAD_ATTEMPTS,
    DOWNLOAD_RETRY_DELAY_SECONDS,
    MANAGED_ENVS_DIRNAME,
    MARKER_ENV_NAME,
    MARKER_INSTALL_HINT,
    MARKER_PACKAGE_NAME,
    MINERU_ENV_NAME,
    MINERU_INSTALL_HINT,
    MINERU_PACKAGE_NAME,
    PACKAGE_INSTALL_ATTEMPTS,
    PACKAGE_INSTALL_RETRY_DELAY_SECONDS,
    PANDOC_DOWNLOAD_ERROR,
    PANDOC_POST_CHECK_ERROR,
    PIP_DISABLE_VERSION_CHECK,
    PIP_NO_INPUT,
    PIP_QUIET,
    PYPANDOC_IMPORT_ERROR,
    PYPANDOC_PACKAGE_NAME,
)

MANAGED_ENV_BY_EXECUTABLE = {
    "marker_single": MARKER_ENV_NAME,
    "mineru": MINERU_ENV_NAME,
    "pandoc": CORE_ENV_NAME,
}

MANAGED_PANDOC_SCRIPT = """
import contextlib
import io
from pathlib import Path

try:
    import pypandoc
    from pypandoc.pandoc_download import download_pandoc
except ImportError:
    raise SystemExit(2)

try:
    pandoc_path = pypandoc.get_pandoc_path()
except (OSError, RuntimeError):
    pandoc_path = None

if not pandoc_path:
    try:
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            download_pandoc(delete_installer=True)
        pandoc_path = pypandoc.get_pandoc_path()
    except Exception as exc:
        print(str(exc))
        raise SystemExit(1)

if not pandoc_path:
    raise SystemExit(1)

print(Path(pandoc_path).expanduser())
"""


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _managed_env_dir(env_name: str) -> Path:
    return _project_root() / MANAGED_ENVS_DIRNAME / env_name


def _managed_env_bin_dir(env_name: str) -> Path:
    env_dir = _managed_env_dir(env_name)
    if os.name == "nt":
        return env_dir / "Scripts"
    return env_dir / "bin"


def _managed_env_python(env_name: str) -> Path:
    bin_dir = _managed_env_bin_dir(env_name)
    if os.name == "nt":
        return bin_dir / "python.exe"
    return bin_dir / "python"


def _managed_executable_path(executable_name: str) -> str | None:
    env_name = MANAGED_ENV_BY_EXECUTABLE.get(executable_name)
    if env_name is None:
        return None

    bin_dir = _managed_env_bin_dir(env_name)
    candidates = [bin_dir / executable_name]
    if os.name == "nt":
        candidates.append(bin_dir / f"{executable_name}.exe")
    for candidate in candidates:
        if candidate.exists() and candidate.is_file():
            return str(candidate)
    return None


def _managed_pandoc_path() -> str | None:
    managed_python = _managed_env_python(CORE_ENV_NAME)
    if not managed_python.exists():
        return None

    proc = subprocess.run(
        [str(managed_python), "-c", MANAGED_PANDOC_SCRIPT],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        return None

    candidate = proc.stdout.strip().splitlines()[-1] if proc.stdout.strip() else ""
    return candidate or None


def install_python_package(package_name: str) -> None:
    last_detail = None
    for attempt in range(1, PACKAGE_INSTALL_ATTEMPTS + 1):
        proc = subprocess.run(
            [sys.executable, "-m", "pip", "install", PIP_DISABLE_VERSION_CHECK, PIP_NO_INPUT, PIP_QUIET, package_name],
            capture_output=True,
            text=True,
        )
        if proc.returncode == 0:
            return
        last_detail = (proc.stderr or proc.stdout).strip() or f"pip exited with status {proc.returncode}"
        if attempt < PACKAGE_INSTALL_ATTEMPTS:
            time.sleep(PACKAGE_INSTALL_RETRY_DELAY_SECONDS)
    raise RuntimeError(
        AUTO_INSTALL_FAILURE_TEMPLATE.format(
            package=package_name,
            attempts=PACKAGE_INSTALL_ATTEMPTS,
            detail=last_detail,
        )
    )


def resolve_cli_path(executable_name: str) -> str | None:
    resolved = shutil.which(executable_name)
    if resolved is not None:
        return resolved

    if executable_name == "pandoc":
        managed_pandoc = _managed_pandoc_path()
        if managed_pandoc is not None:
            return managed_pandoc

    managed = _managed_executable_path(executable_name)
    if managed is not None:
        return managed

    python_bin_dir = Path(sys.executable).resolve().parent
    candidates = [python_bin_dir / executable_name, python_bin_dir / f"{executable_name}.exe"]
    for candidate in candidates:
        if candidate.exists() and candidate.is_file():
            return str(candidate)
    return None


def import_pypandoc_modules():
    try:
        pypandoc = importlib.import_module("pypandoc")
        pandoc_download = importlib.import_module("pypandoc.pandoc_download")
        return pypandoc, pandoc_download.download_pandoc
    except ImportError:
        install_python_package(PYPANDOC_PACKAGE_NAME)
        try:
            pypandoc = importlib.import_module("pypandoc")
            pandoc_download = importlib.import_module("pypandoc.pandoc_download")
            return pypandoc, pandoc_download.download_pandoc
        except ImportError as exc:
            raise RuntimeError(PYPANDOC_IMPORT_ERROR) from exc


def ensure_marker() -> str:
    marker_bin = resolve_cli_path("marker_single")
    if marker_bin is not None:
        return marker_bin

    install_python_package(MARKER_PACKAGE_NAME)
    marker_bin = resolve_cli_path("marker_single")
    if marker_bin is None:
        raise RuntimeError(
            f"{MARKER_INSTALL_HINT} {AUTO_INSTALL_POST_CHECK_TEMPLATE.format(package=MARKER_PACKAGE_NAME, executable='marker_single')}"
        )
    return marker_bin


def ensure_mineru() -> str:
    mineru_bin = resolve_cli_path("mineru")
    if mineru_bin is not None:
        return mineru_bin

    install_python_package(MINERU_PACKAGE_NAME)
    mineru_bin = resolve_cli_path("mineru")
    if mineru_bin is None:
        raise RuntimeError(
            f"{MINERU_INSTALL_HINT} {AUTO_INSTALL_POST_CHECK_TEMPLATE.format(package=MINERU_PACKAGE_NAME, executable='mineru')}"
        )
    return mineru_bin


def ensure_pandoc() -> str:
    pandoc_bin = shutil.which("pandoc")
    if pandoc_bin is not None:
        return pandoc_bin

    managed_pandoc = _managed_pandoc_path()
    if managed_pandoc is not None:
        return managed_pandoc

    pypandoc, download_pandoc = import_pypandoc_modules()

    try:
        pandoc_bin = pypandoc.get_pandoc_path()
    except (OSError, RuntimeError):
        pandoc_bin = None

    if pandoc_bin:
        return str(Path(pandoc_bin).expanduser())

    last_error = None
    for attempt in range(1, DOWNLOAD_ATTEMPTS + 1):
        try:
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                download_pandoc(delete_installer=True)
            pandoc_bin = pypandoc.get_pandoc_path()
            break
        except Exception as exc:
            last_error = exc
            if attempt < DOWNLOAD_ATTEMPTS:
                time.sleep(DOWNLOAD_RETRY_DELAY_SECONDS)

    if last_error is not None and not pandoc_bin:
        raise RuntimeError(PANDOC_DOWNLOAD_ERROR.format(attempts=DOWNLOAD_ATTEMPTS, detail=last_error)) from last_error

    if not pandoc_bin:
        raise RuntimeError(PANDOC_POST_CHECK_ERROR)

    return str(Path(pandoc_bin).expanduser())
