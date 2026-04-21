from pathlib import Path

from pandoc_to_markdown.bootstrap import ensure_marker, ensure_mineru, ensure_pandoc
from pandoc_to_markdown.config import DEFAULT_EXTS, MARKER_INSTALL_HINT, MINERU_INSTALL_HINT, PANDOC_INPUT_SUFFIXES, PDF_INPUT_SUFFIX
from pandoc_to_markdown.converters.marker_backend import convert_pdf_with_marker
from pandoc_to_markdown.converters.mineru_backend import convert_pdf_with_mineru
from pandoc_to_markdown.converters.pandoc_backend import convert_non_pdf_with_pandoc
from pandoc_to_markdown.markdown_postprocess import postprocess_markdown_file


def normalize_exts(ext_string: str) -> set[str]:
    exts = set()
    for part in ext_string.split(','):
        cleaned = part.strip().lower().lstrip('.')
        if cleaned:
            exts.add(f'.{cleaned}')
    return exts


def collect_batch_inputs(paths: list[Path], exts: set[str], recursive: bool) -> list[Path]:
    files: list[Path] = []
    for root in paths:
        if not root.exists() or not root.is_dir():
            files.append(root)
            continue
        iterator = root.rglob('*') if recursive else root.glob('*')
        for item in iterator:
            if item.is_file() and item.suffix.lower() in exts:
                files.append(item)
    return files


def resolve_sources(mode: str, paths: list[Path], exts: str = DEFAULT_EXTS, recursive: bool = False) -> list[Path]:
    if mode == 'single':
        return paths
    return collect_batch_inputs(paths, normalize_exts(exts), recursive)


def run_conversion(
    sources: list[Path],
    out_dir: Path | None,
    overwrite: bool,
    to_format: str,
    pdf_engine: str,
    marker_mode: str = 'auto',
    progress_callback=None,
) -> dict:
    need_pandoc = any(src.suffix.lower() in PANDOC_INPUT_SUFFIXES for src in sources)
    need_pdf = any(src.suffix.lower() == PDF_INPUT_SUFFIX for src in sources)

    notices: list[dict] = []

    def emit_progress(event: dict) -> None:
        notices.append(event)
        if progress_callback is not None:
            progress_callback(event)

    pandoc_bin = None
    pandoc_error = None
    if need_pandoc:
        try:
            pandoc_bin = ensure_pandoc()
        except RuntimeError as exc:
            pandoc_error = str(exc)

    pdf_engine_bin = None
    pdf_engine_error = None
    if need_pdf:
        try:
            if pdf_engine == 'mineru':
                pdf_engine_bin = ensure_mineru()
            else:
                pdf_engine_bin = ensure_marker()
        except RuntimeError as exc:
            pdf_engine_error = str(exc)

    results = []
    for src in sources:
        suffix = src.suffix.lower()
        if suffix == PDF_INPUT_SUFFIX:
            if pdf_engine_bin is None:
                result = {
                    'ok': False,
                    'input': str(src),
                    'error': f'{pdf_engine.upper()}_NOT_INSTALLED',
                    'detail': pdf_engine_error or (MINERU_INSTALL_HINT if pdf_engine == 'mineru' else MARKER_INSTALL_HINT),
                }
            elif pdf_engine == 'mineru':
                result = convert_pdf_with_mineru(src, out_dir, overwrite, pdf_engine_bin, progress_callback=emit_progress)
            else:
                result = convert_pdf_with_marker(
                    src,
                    out_dir,
                    overwrite,
                    pdf_engine_bin,
                    progress_callback=emit_progress,
                    marker_mode=marker_mode,
                )
        elif suffix in PANDOC_INPUT_SUFFIXES:
            if pandoc_bin is None:
                result = {
                    'ok': False,
                    'input': str(src),
                    'error': 'PANDOC_NOT_INSTALLED',
                    'detail': pandoc_error or 'Pandoc is required for non-PDF document conversion.',
                }
            else:
                result = convert_non_pdf_with_pandoc(src, out_dir, overwrite, to_format, pandoc_bin)
        else:
            result = {
                'ok': False,
                'input': str(src),
                'error': 'UNSUPPORTED_INPUT_FORMAT',
                'detail': f'Unsupported input format: {suffix or "<none>"}',
            }

        if result.get('ok') and result.get('output'):
            postprocess_markdown_file(Path(result['output']))

        results.append(result)

    return {
        'ok': all(item.get('ok') for item in results),
        'count': len(results),
        'results': results,
        'notices': notices,
    }
