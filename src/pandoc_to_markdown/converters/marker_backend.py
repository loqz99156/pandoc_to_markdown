import os
import subprocess
from pathlib import Path

from pandoc_to_markdown.config import MARKER_SUPPORTED_OUTPUT_FORMAT


MARKER_CPU_RETRY_NOTICE = 'Marker 在当前加速设备上失败，正在切到 CPU 重试，可能会更慢。'


def get_marker_output_path(src: Path, target_dir: Path) -> Path:
    return target_dir / src.stem / f'{src.stem}.md'


def build_marker_command(
    src: Path,
    target_dir: Path,
    marker_bin: str,
    *,
    debug: bool = False,
    force_ocr: bool = False,
    disable_multiprocessing: bool = False,
    disable_image_extraction: bool = False,
) -> list[str]:
    command = [
        marker_bin,
        str(src),
        '--output_dir',
        str(target_dir),
        '--output_format',
        MARKER_SUPPORTED_OUTPUT_FORMAT,
    ]
    if debug:
        command.append('--debug')
    if force_ocr:
        command.append('--force_ocr')
    if disable_multiprocessing:
        command.append('--disable_multiprocessing')
    if disable_image_extraction:
        command.append('--disable_image_extraction')
    return command


def build_marker_env(torch_device: str | None = None) -> dict[str, str]:
    env = os.environ.copy()
    if torch_device is not None:
        env['TORCH_DEVICE'] = torch_device
    return env


def looks_like_marker_device_crash(detail: str) -> bool:
    combined = detail.lower()
    if 'torch.acceleratorerror' in combined or 'invalid buffer size' in combined:
        return True
    return 'mps backend' in combined and 'surya' in combined and ('runtimeerror' in combined or 'traceback' in combined)


def run_marker_command(
    src: Path,
    target_dir: Path,
    marker_bin: str,
    *,
    progress_callback=None,
    torch_device: str | None = None,
    debug: bool = False,
    force_ocr: bool = False,
    disable_multiprocessing: bool = False,
    disable_image_extraction: bool = False,
) -> tuple[int, str, bool]:
    output_lines: list[str] = []
    download_started = False
    proc = subprocess.Popen(
        build_marker_command(
            src,
            target_dir,
            marker_bin,
            debug=debug,
            force_ocr=force_ocr,
            disable_multiprocessing=disable_multiprocessing,
            disable_image_extraction=disable_image_extraction,
        ),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        env=build_marker_env(torch_device),
    )

    assert proc.stdout is not None
    for raw_line in proc.stdout:
        output_lines.append(raw_line)
        line = raw_line.strip()
        if not line:
            continue
        if 'Downloading' not in line and 'model.safetensors' not in line and 'manifest.json' not in line:
            continue
        if progress_callback is None:
            continue
        if not download_started:
            download_started = True
            progress_callback(
                {
                    'type': 'MODEL_DOWNLOAD_STARTED',
                    'engine': 'marker',
                    'message': '首次使用 Marker，需要先下载模型，下载完成后会继续转换。',
                    'line': line,
                }
            )
        progress_callback(
            {
                'type': 'MODEL_DOWNLOAD_PROGRESS',
                'engine': 'marker',
                'message': line,
                'line': line,
            }
        )

    return proc.wait(), ''.join(output_lines).strip(), download_started


def convert_pdf_with_marker(
    src: Path,
    out_dir: Path | None,
    overwrite: bool,
    marker_bin: str,
    progress_callback=None,
) -> dict:
    target_dir = out_dir if out_dir is not None else src.parent
    target_dir.mkdir(parents=True, exist_ok=True)
    dst = get_marker_output_path(src, target_dir)

    if dst.exists() and not overwrite:
        return {
            'ok': False,
            'input': str(src),
            'output': str(dst),
            'error': 'OUTPUT_EXISTS',
        }

    returncode, detail, download_started = run_marker_command(
        src,
        target_dir,
        marker_bin,
        progress_callback=progress_callback,
    )

    if returncode != 0 and looks_like_marker_device_crash(detail):
        if progress_callback is not None:
            progress_callback(
                {
                    'type': 'MARKER_RETRY_CPU',
                    'engine': 'marker',
                    'message': MARKER_CPU_RETRY_NOTICE,
                }
            )
        retry_returncode, retry_detail, retry_download_started = run_marker_command(
            src,
            target_dir,
            marker_bin,
            progress_callback=progress_callback,
            torch_device='cpu',
        )
        download_started = download_started or retry_download_started
        if retry_returncode == 0:
            returncode = retry_returncode
            detail = retry_detail
        else:
            returncode = retry_returncode
            detail = (
                'Marker failed on the default device, then failed again after retrying on CPU.\n\n'
                '--- default-device failure ---\n'
                f'{detail}\n\n'
                '--- cpu retry failure ---\n'
                f'{retry_detail}'
            ).strip()

    if returncode != 0:
        return {
            'ok': False,
            'input': str(src),
            'error': 'MARKER_FAILED',
            'detail': detail,
        }

    if download_started and progress_callback is not None:
        progress_callback(
            {
                'type': 'MODEL_DOWNLOAD_COMPLETED',
                'engine': 'marker',
                'message': 'Marker 模型下载完成，继续转换。',
            }
        )

    if not dst.exists():
        return {
            'ok': False,
            'input': str(src),
            'error': 'MARKER_OUTPUT_NOT_FOUND',
            'detail': f'Expected Marker to create {dst}',
        }

    return {'ok': True, 'input': str(src), 'output': str(dst)}
