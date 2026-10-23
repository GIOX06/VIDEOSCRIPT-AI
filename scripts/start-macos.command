#!/bin/bash
set -euo pipefail
SCRIPT_DIR="$(cd -- "$(dirname -- "$0")" && pwd)"
PROJECT_DIR="$(dirname -- "$SCRIPT_DIR")"
cd "$PROJECT_DIR"
if [ ! -x .venv/bin/python ]; then
  echo "Prima esegui scripts/setup-macos.command."
  exit 1
fi
exec .venv/bin/python scripts/start.py "$@"
