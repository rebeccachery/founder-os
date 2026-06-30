#!/usr/bin/env bash
# Start the FastAPI backend using the project venv.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ ! -d .venv ]]; then
  echo "Creating .venv..."
  python3 -m venv .venv
  .venv/bin/pip install -r requirements.txt
fi

exec .venv/bin/uvicorn api.main:app --reload --host 127.0.0.1 --port "${PORT:-8000}"
