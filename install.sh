#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
PYTHONPATH="$ROOT_DIR/src" python3 "$ROOT_DIR/scripts/setup_env.py"
