from __future__ import annotations

import re
from pathlib import Path


HEADER_RE = re.compile(r"^#{1,6}\s")
LIST_RE = re.compile(r"^(?:[-*+]\s|\d+[.)]\s)")
FENCE_RE = re.compile(r"^```+")
TABLE_RE = re.compile(r"^\|.*\|$")
TABLE_SEPARATOR_RE = re.compile(r"^\|?(?:\s*:?-{3,}:?\s*\|)+\s*$")
NOISE_RE = re.compile(r"^[\s\-|•·⋯·_=~]{1,3}$")


def _rstrip_lines(lines: list[str]) -> list[str]:
    return [line.rstrip() for line in lines]


def _drop_noise_lines(lines: list[str]) -> list[str]:
    cleaned: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped and NOISE_RE.fullmatch(stripped):
            while cleaned and cleaned[-1] == "":
                cleaned.pop()
            cleaned.append("")
            continue
        cleaned.append(line)
    return cleaned


def _normalize_blank_runs(lines: list[str]) -> list[str]:
    normalized: list[str] = []
    blank_count = 0
    for line in lines:
        if line == "":
            blank_count += 1
            if blank_count <= 1:
                normalized.append(line)
            continue
        blank_count = 0
        normalized.append(line)
    return normalized


def _ensure_block_spacing(lines: list[str]) -> list[str]:
    spaced: list[str] = []
    in_code_fence = False
    for index, line in enumerate(lines):
        stripped = line.strip()
        is_fence = bool(FENCE_RE.match(stripped))
        is_header = bool(HEADER_RE.match(stripped))
        is_table = bool(TABLE_RE.match(stripped))
        is_separator = bool(TABLE_SEPARATOR_RE.match(stripped))
        is_list = bool(LIST_RE.match(stripped))

        if is_fence:
            if not in_code_fence and spaced and spaced[-1] != "":
                spaced.append("")
            spaced.append(line)
            in_code_fence = not in_code_fence
            next_line = lines[index + 1].strip() if index + 1 < len(lines) else ""
            if not in_code_fence and next_line and next_line != "":
                spaced.append("")
            continue

        if in_code_fence:
            spaced.append(line)
            continue

        if (is_header or (is_table and not is_separator)) and spaced and spaced[-1] != "":
            spaced.append("")

        if is_list and spaced:
            previous = spaced[-1].strip()
            if previous and not LIST_RE.match(previous):
                spaced.append("")

        spaced.append(line)

        next_line = lines[index + 1].strip() if index + 1 < len(lines) else ""
        if is_header and next_line:
            spaced.append("")
        elif is_table and not is_separator and next_line and not TABLE_RE.match(next_line):
            spaced.append("")
        elif is_list and next_line and not LIST_RE.match(next_line):
            spaced.append("")

    return spaced


def _close_unterminated_fence(lines: list[str]) -> list[str]:
    fence_count = sum(1 for line in lines if FENCE_RE.match(line.strip()))
    if fence_count % 2 == 1:
        if lines and lines[-1] != "":
            lines.append("")
        lines.append("```")
    return lines


def _trim_edges(lines: list[str]) -> list[str]:
    start = 0
    end = len(lines)
    while start < end and lines[start] == "":
        start += 1
    while end > start and lines[end - 1] == "":
        end -= 1
    return lines[start:end]


def postprocess_markdown(text: str) -> str:
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    lines = _rstrip_lines(lines)
    lines = _drop_noise_lines(lines)
    lines = _ensure_block_spacing(lines)
    lines = _close_unterminated_fence(lines)
    lines = _normalize_blank_runs(lines)
    lines = _trim_edges(lines)
    return "\n".join(lines) + "\n"


def postprocess_markdown_file(path: Path) -> None:
    original = path.read_text(encoding="utf-8")
    processed = postprocess_markdown(original)
    if processed != original:
        path.write_text(processed, encoding="utf-8")
