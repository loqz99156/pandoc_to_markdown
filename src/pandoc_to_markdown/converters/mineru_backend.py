import shutil
import subprocess
from pathlib import Path


def convert_pdf_with_mineru(
    src: Path,
    out_dir: Path | None,
    overwrite: bool,
    mineru_bin: str,
    progress_callback=None,
) -> dict:
    target_dir = out_dir if out_dir is not None else src.parent
    target_dir.mkdir(parents=True, exist_ok=True)
    dst = (target_dir / src.stem).with_suffix('.md')

    if dst.exists() and not overwrite:
        return {
            'ok': False,
            'input': str(src),
            'output': str(dst),
            'error': 'OUTPUT_EXISTS',
        }

    output_lines: list[str] = []
    download_started = False
    proc = subprocess.Popen(
        [
            mineru_bin,
            '-p',
            str(src),
            '-o',
            str(target_dir),
            '-b',
            'pipeline',
            '-l',
            'ch',
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
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
                    'engine': 'mineru',
                    'message': '首次使用 MinerU，需要先下载模型，下载完成后会继续转换。',
                    'line': line,
                }
            )
        progress_callback(
            {
                'type': 'MODEL_DOWNLOAD_PROGRESS',
                'engine': 'mineru',
                'message': line,
                'line': line,
            }
        )

    returncode = proc.wait()
    detail = ''.join(output_lines).strip()

    if returncode != 0:
        return {
            'ok': False,
            'input': str(src),
            'error': 'MINERU_FAILED',
            'detail': detail,
        }

    if download_started and progress_callback is not None:
        progress_callback(
            {
                'type': 'MODEL_DOWNLOAD_COMPLETED',
                'engine': 'mineru',
                'message': 'MinerU 模型下载完成，继续转换。',
            }
        )

    candidate_paths = [
        target_dir / src.stem / 'auto' / f'{src.stem}.md',
        target_dir / src.stem / 'pipeline' / f'{src.stem}.md',
        target_dir / src.stem / 'hybrid_auto' / f'{src.stem}.md',
        target_dir / src.stem / 'vlm' / f'{src.stem}.md',
        target_dir / f'{src.stem}.md',
    ]
    generated = next((path for path in candidate_paths if path.exists()), None)

    if generated is None:
        return {
            'ok': False,
            'input': str(src),
            'error': 'MINERU_OUTPUT_NOT_FOUND',
            'detail': f"Expected MinerU to create one of: {', '.join(str(path) for path in candidate_paths)}",
        }

    if generated != dst:
        shutil.copyfile(generated, dst)

    return {'ok': True, 'input': str(src), 'output': str(dst)}
