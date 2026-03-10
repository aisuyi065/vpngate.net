#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [[ -f .env ]]; then
  set -a
  source .env
  set +a
fi

HOST="${VPNGATE_BIND_HOST:-0.0.0.0}"
PORT="${VPNGATE_BIND_PORT:-8000}"

exec "$ROOT_DIR/.venv/bin/python" -m uvicorn app.main:app --app-dir "$ROOT_DIR/backend" --host "$HOST" --port "$PORT"
