#!/usr/bin/env python3
import argparse
import json
from pathlib import Path

from pandoc_to_markdown.installer import MODEL_SOURCES, MODEL_TYPES, download_mineru_models, get_env_dir
from pandoc_to_markdown.config import MINERU_ENV_NAME


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Download MinerU models in the managed environment")
    parser.add_argument("--source", choices=MODEL_SOURCES, default="huggingface")
    parser.add_argument("--model-type", choices=MODEL_TYPES, default="all")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    project_root = Path(__file__).resolve().parents[1]
    mineru_env = get_env_dir(project_root, MINERU_ENV_NAME)
    if not mineru_env.exists():
        raise SystemExit("MinerU environment is missing. Run setup_env.py first.")

    result = download_mineru_models(project_root, model_source=args.source, model_type=args.model_type)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
