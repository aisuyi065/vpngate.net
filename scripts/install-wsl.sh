#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

sudo apt-get update
sudo apt-get install -y python3 python3-venv python3-pip nodejs npm openvpn iproute2 iputils-ping curl ca-certificates

cd "$PROJECT_DIR"
if [[ ! -f .env ]]; then
  cp .env.example .env
fi

python3 -m venv .venv
. .venv/bin/activate
pip install --upgrade pip
pip install -e backend
npm --prefix frontend install
npm --prefix frontend run build
mkdir -p data/openvpn

echo "WSL install complete. This setup only manages WSL traffic, not the full Windows host."
if command -v systemctl >/dev/null 2>&1 && systemctl --user show-environment >/dev/null 2>&1; then
  echo "systemd --user is available; you can register a user service manually if desired."
else
  echo "Start the controller with: ./scripts/start-controller.sh"
fi
