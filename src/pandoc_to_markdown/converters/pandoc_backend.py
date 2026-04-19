import subprocess
from pathlib import Path


def convert_non_pdf_with_pandoc(src: Path, out_dir: Path | None, overwrite: bool, to_format: str, pandoc_bin: str) -> dict:
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

    proc = subprocess.run(
        [
            pandoc_bin,
            str(src),
            '-t',
            to_format,
            '--markdown-headings=atx',
            '--wrap=none',
            '--reference-links',
            '-o',
            str(dst),
        ],
        capture_output=True,
        text=True,
    )

    if proc.returncode != 0:
        return {
            'ok': False,
            'input': str(src),
            'error': 'PANDOC_FAILED',
            'detail': (proc.stderr or proc.stdout).strip(),
        }

    return {'ok': True, 'input': str(src), 'output': str(dst)}
