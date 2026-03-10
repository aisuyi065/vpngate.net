#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="${1:-/opt/vpngate-controller}"
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

exec sudo bash "$REPO_DIR/install.sh" --project-dir "$PROJECT_DIR"
