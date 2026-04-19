#!/usr/bin/env python3
import argparse
import json
from pathlib import Path

from pandoc_to_markdown.installer import run_install


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Set up pandoc-to-markdown managed environments")
    parser.add_argument("--python", default=None, help="Explicit Python executable")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    project_root = Path(__file__).resolve().parents[1]
    result = run_install(project_root, explicit_python=args.python)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
