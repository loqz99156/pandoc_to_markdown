#!/usr/bin/env python3
import argparse
import json
from pathlib import Path

from pandoc_to_markdown.config import DEFAULT_EXTS, PANDOC_TARGET_FORMAT
from pandoc_to_markdown.doctor import build_report, print_report
from pandoc_to_markdown.installer import run_install
from pandoc_to_markdown.routing import resolve_sources, run_conversion


def build_progress_printer(as_json: bool):
    seen_messages: set[str] = set()
    last_progress_line = None

    def handle(event: dict) -> None:
        nonlocal last_progress_line
        message = event.get("message")
        if not message:
            return
        if event.get("type") == "MODEL_DOWNLOAD_PROGRESS":
            line = event.get("line") or message
            if line == last_progress_line:
                return
            last_progress_line = line
            if "model.safetensors" in line or "manifest.json" in line or "Downloading" in line:
                print(line)
            return
        if as_json or message in seen_messages:
            return
        seen_messages.add(message)
        print(message)
        if event.get("type") == "MODEL_DOWNLOAD_STARTED":
            for model in event.get("models", []):
                name = model.get("name") or "model"
                download_url = model.get("download_url")
                model_size = model.get("model_size")
                details = []
                if download_url:
                    details.append(f"链接: {download_url}")
                if model_size:
                    details.append(f"大小: {model_size}")
                if details:
                    print(f"- {name} ({', '.join(details)})")

    return handle


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="pandoc-to-markdown project CLI")
    subparsers = parser.add_subparsers(dest="command")

    info_parser = subparsers.add_parser("info", help="Show project info")
    info_parser.add_argument("--json", action="store_true", help="Output JSON")

    convert_parser = subparsers.add_parser("convert", help="Convert documents to Markdown")
    convert_parser.add_argument("--mode", choices=["single", "batch"], required=True)
    convert_parser.add_argument("--paths", nargs="+", required=True)
    convert_parser.add_argument("--exts", default=DEFAULT_EXTS)
    convert_parser.add_argument("--recursive", action="store_true")
    convert_parser.add_argument("--to", default=PANDOC_TARGET_FORMAT)
    convert_parser.add_argument("--out-dir", default=None)
    convert_parser.add_argument("--overwrite", action="store_true")
    convert_parser.add_argument("--pdf-engine", choices=["marker", "mineru"], default="marker")
    convert_parser.add_argument("--marker-mode", choices=["auto", "cpu"], default="auto")
    convert_parser.add_argument("--json", action="store_true")

    install_parser = subparsers.add_parser("install", help="Prepare local environment")
    install_parser.add_argument("--python", default=None, help="Explicit Python executable")
    install_parser.add_argument("--json", action="store_true")

    doctor_parser = subparsers.add_parser("doctor", help="Inspect local environment")
    doctor_parser.add_argument("--json", action="store_true")

    return parser


def looks_like_interrupted_model_download(item: dict) -> bool:
    error = str(item.get("error") or "")
    detail = str(item.get("detail") or "")
    combined = f"{error}\n{detail}".lower()
    if ".incomplete" in combined:
        return True
    if "connection reset" in combined or "read timed out" in combined or "incompleteread" in combined:
        return True
    return "download" in combined and any(token in combined for token in ["interrupt", "failed", "resume"])


def print_recovery_hint(item: dict) -> None:
    print("模型下载被中断了，重新执行同一条转换命令即可继续，不需要从头开始。")
    print("如果多次都卡在同一个 .incomplete 文件，再删除那个 .incomplete 文件后重试；不要清空整个项目内 .models/mineru/huggingface。")


def print_payload(payload: dict, as_json: bool) -> None:
    if as_json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return

    for item in payload["results"]:
        if item["ok"]:
            print(f"OK {item['input']} -> {item['output']}")
        else:
            detail = item.get("detail") or item["error"]
            print(f"FAIL {item['input']} :: {detail}")
            if looks_like_interrupted_model_download(item):
                print_recovery_hint(item)


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "info":
        payload = {
            "project": "pandoc-to-markdown",
            "status": "bootstrap",
        }
        if args.json:
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            print("pandoc-to-markdown bootstrap is ready")
        return

    if args.command == "convert":
        project_root = Path(__file__).resolve().parents[2]
        input_paths = [Path(p).expanduser().resolve() for p in args.paths]
        out_dir = Path(args.out_dir).expanduser().resolve() if args.out_dir else project_root / "outputs"
        sources = resolve_sources(args.mode, input_paths, exts=args.exts, recursive=args.recursive)
        payload = run_conversion(
            sources=sources,
            out_dir=out_dir,
            overwrite=args.overwrite,
            to_format=args.to,
            pdf_engine=args.pdf_engine,
            marker_mode=args.marker_mode,
            progress_callback=build_progress_printer(args.json),
        )
        print_payload(payload, args.json)
        if not payload["ok"]:
            raise SystemExit(1)
        return

    if args.command == "install":
        project_root = Path(__file__).resolve().parents[2]
        payload = run_install(project_root, explicit_python=args.python)
        if args.json:
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            print(f"Managed environments ready in {payload['envs_root']} with Python {payload['python_version']}")
        return

    if args.command == "doctor":
        project_root = Path(__file__).resolve().parents[2]
        report = build_report(project_root)
        print_report(report, args.json)
        if not report["ok"]:
            raise SystemExit(1)
        return

    parser.print_help()


if __name__ == "__main__":
    main()
