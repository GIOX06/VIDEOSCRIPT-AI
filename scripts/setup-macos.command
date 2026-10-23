#!/bin/bash
set -euo pipefail
SCRIPT_DIR="$(cd -- "$(dirname -- "$0")" && pwd)"
PROJECT_DIR="$(dirname -- "$SCRIPT_DIR")"
cd "$PROJECT_DIR"
for tool in uv node npm ffmpeg ffprobe; do
  if ! command -v "$tool" >/dev/null 2>&1; then
    echo "Manca $tool. Installa i prerequisiti descritti in README.md e riapri il terminale."
    exit 1
  fi
done
if [ "${1:-}" = "--base" ]; then
  uv sync --frozen
elif [ "$#" -eq 0 ]; then
  uv sync --frozen --extra ai
else
  echo "Uso: scripts/setup-macos.command [--base]"
  exit 1
fi
(cd frontend && npm ci)
.venv/bin/python scripts/start.py --check
echo "Installazione completata. Avvia scripts/start-macos.command."
