#!/usr/bin/env bash
set -euo pipefail

SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="/opt/vpngate-controller"
MODE="auto"
DOMAIN=""
ACME_EMAIL=""
PORT="8443"
AUTH_PASSWORD=""
DASHBOARD_PASSWORD=""
MASQUERADE_URL="https://bing.com"
ADVERTISE_HOST=""

usage() {
  cat <<EOF
Usage: bash install.sh [options]

Options:
  --project-dir PATH       Install into PATH (default: /opt/vpngate-controller)
  --mode MODE              auto | hy2-native | openvpn (default: auto)
  --domain DOMAIN          Domain for ACME mode
  --acme-email EMAIL       Email used for ACME registration
  --port PORT              Hysteria UDP listen port (default: 8443)
  --auth-password VALUE    Explicit Hysteria password
  --dashboard-password V   Password required to access http://SERVER_IP:8000
  --masquerade-url URL     Hysteria masquerade URL
  --advertise-host HOST    Host advertised in client URI
  --help                   Show this message
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --project-dir)
      PROJECT_DIR="$2"
      shift 2
      ;;
    --mode)
      MODE="$2"
      shift 2
      ;;
    --domain)
      DOMAIN="$2"
      shift 2
      ;;
    --acme-email)
      ACME_EMAIL="$2"
      shift 2
      ;;
    --port)
      PORT="$2"
      shift 2
      ;;
    --auth-password)
      AUTH_PASSWORD="$2"
      shift 2
      ;;
    --dashboard-password)
      DASHBOARD_PASSWORD="$2"
      shift 2
      ;;
    --masquerade-url)
      MASQUERADE_URL="$2"
      shift 2
      ;;
    --advertise-host)
      ADVERTISE_HOST="$2"
      shift 2
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage
      exit 1
      ;;
  esac
done

require_root() {
  if [[ "${EUID}" -eq 0 ]]; then
    return
  fi
  if command -v sudo >/dev/null 2>&1; then
    exec sudo bash "$0" "$@"
  fi
  echo "This installer must run as root." >&2
  exit 1
}

random_secret() {
  if [[ -r /proc/sys/kernel/random/uuid ]]; then
    cat /proc/sys/kernel/random/uuid
    return
  fi
  openssl rand -hex 16
}

detect_public_host() {
  local detected=""
  detected="$(curl -fsSL https://api.ipify.org 2>/dev/null || true)"
  if [[ -z "$detected" ]]; then
    detected="$(hostname -I | awk '{print $1}')"
  fi
  echo "$detected"
}

set_env_value() {
  local file="$1"
  local key="$2"
  local value="$3"
  python3 - "$file" "$key" "$value" <<'PY'
from pathlib import Path
import sys

path = Path(sys.argv[1])
key = sys.argv[2]
value = sys.argv[3]
lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
prefix = f"{key}="
updated = False
for index, line in enumerate(lines):
    if line.startswith(prefix):
        lines[index] = f"{key}={value}"
        updated = True
        break
if not updated:
    lines.append(f"{key}={value}")
path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
PY
}

detect_mode() {
  if [[ "$MODE" != "auto" ]]; then
    return
  fi
  if [[ -c /dev/net/tun ]]; then
    MODE="openvpn"
  else
    MODE="hy2-native"
  fi
}

validate_inputs() {
  if ! command -v systemctl >/dev/null 2>&1; then
    echo "systemd is required for this installer." >&2
    exit 1
  fi
  if [[ "$MODE" == "openvpn" && ! -c /dev/net/tun ]]; then
    echo "OpenVPN mode requires /dev/net/tun, but this host does not provide it." >&2
    exit 1
  fi
  if [[ -n "$DOMAIN" && -z "$ACME_EMAIL" ]]; then
    echo "--domain requires --acme-email for ACME mode." >&2
    exit 1
  fi
  if [[ "$MODE" == "hy2-native" && -z "$ADVERTISE_HOST" ]]; then
    if [[ -n "$DOMAIN" ]]; then
      ADVERTISE_HOST="$DOMAIN"
    else
      ADVERTISE_HOST="$(detect_public_host)"
    fi
  fi
}

install_packages() {
  apt-get update -y
  apt-get install -y python3 python3-venv python3-pip nodejs npm curl ca-certificates rsync openssl
  if [[ "$MODE" == "openvpn" ]]; then
    apt-get install -y openvpn iproute2 iputils-ping
  fi
}

sync_project() {
  mkdir -p "$PROJECT_DIR"
  if [[ "$SOURCE_DIR" != "$PROJECT_DIR" ]]; then
    rsync -a --delete --exclude .venv --exclude node_modules --exclude data "$SOURCE_DIR/" "$PROJECT_DIR/"
  fi
}

install_app() {
  cd "$PROJECT_DIR"
  [[ -f .env ]] || cp .env.example .env
  python3 -m venv .venv
  .venv/bin/pip install --upgrade pip
  .venv/bin/pip install -e backend
  npm --prefix frontend install
  npm --prefix frontend run build
  mkdir -p data/openvpn
}

configure_env() {
  cd "$PROJECT_DIR"
  [[ -f .env ]] || cp .env.example .env
  set_env_value .env VPNGATE_BIND_HOST 0.0.0.0
  set_env_value .env VPNGATE_BIND_PORT 8000
  set_env_value .env VPNGATE_DATA_DIR "$PROJECT_DIR/data"
  set_env_value .env VPNGATE_RUNTIME_MODE "$MODE"
  if [[ -z "$DASHBOARD_PASSWORD" ]]; then
    DASHBOARD_PASSWORD="$(random_secret)"
  fi
  set_env_value .env VPNGATE_DASHBOARD_PASSWORD "$DASHBOARD_PASSWORD"
  set_env_value .env VPNGATE_DASHBOARD_SESSION_SECRET "$(random_secret)"
  if [[ "$MODE" == "hy2-native" ]]; then
    if [[ -z "$AUTH_PASSWORD" ]]; then
      AUTH_PASSWORD="$(random_secret)"
    fi
    if [[ -n "$DOMAIN" ]]; then
      set_env_value .env HYSTERIA_TLS_MODE acme
      set_env_value .env HYSTERIA_DOMAIN "$DOMAIN"
      set_env_value .env HYSTERIA_CLIENT_SNI "$DOMAIN"
      set_env_value .env HYSTERIA_CLIENT_INSECURE false
      set_env_value .env HYSTERIA_ACME_EMAIL "$ACME_EMAIL"
    else
      set_env_value .env HYSTERIA_TLS_MODE self_signed
      set_env_value .env HYSTERIA_DOMAIN ""
      set_env_value .env HYSTERIA_ACME_EMAIL ""
      set_env_value .env HYSTERIA_CLIENT_INSECURE true
      set_env_value .env HYSTERIA_CLIENT_SNI bing.com
    fi
    set_env_value .env VPNGATE_CONNECTOR_MODE mock
    set_env_value .env HYSTERIA_SERVICE_NAME hysteria-server.service
    set_env_value .env HYSTERIA_CONFIG_DIR /etc/hysteria
    set_env_value .env HYSTERIA_CONFIG_NAME config.yaml
    set_env_value .env HYSTERIA_LISTEN_HOST 0.0.0.0
    set_env_value .env HYSTERIA_LISTEN_PORT "$PORT"
    set_env_value .env HYSTERIA_AUTH_PASSWORD "$AUTH_PASSWORD"
    set_env_value .env HYSTERIA_MASQUERADE_URL "$MASQUERADE_URL"
    set_env_value .env HYSTERIA_CERT_PATH /etc/hysteria/server.crt
    set_env_value .env HYSTERIA_KEY_PATH /etc/hysteria/server.key
    if [[ -n "$ADVERTISE_HOST" ]]; then
      set_env_value .env HYSTERIA_ADVERTISE_HOST "$ADVERTISE_HOST"
    fi
  else
    set_env_value .env VPNGATE_CONNECTOR_MODE openvpn
  fi
}

install_controller_service() {
  cp "$PROJECT_DIR/systemd/vpngate-controller.service" /etc/systemd/system/vpngate-controller.service
  systemctl daemon-reload
  systemctl enable vpngate-controller.service
}

install_hysteria() {
  if [[ "$MODE" != "hy2-native" ]]; then
    return
  fi
  bash <(curl -fsSL https://get.hy2.sh/)
  systemctl enable hysteria-server.service
}

apply_hysteria_config() {
  if [[ "$MODE" != "hy2-native" ]]; then
    return
  fi
  cd "$PROJECT_DIR"
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
  PYTHONPATH="$PROJECT_DIR/backend" "$PROJECT_DIR/.venv/bin/python" - <<'PY'
from app.config import settings
from app.models import HysteriaConfigPayload
from app.services.hysteria import Hy2ServiceManager

payload = HysteriaConfigPayload(
    listen_host=settings.hysteria_listen_host,
    listen_port=settings.hysteria_listen_port,
    tls_mode=settings.hysteria_tls_mode,
    auth_password=settings.hysteria_auth_password or "",
    masquerade_url=settings.hysteria_masquerade_url,
    cert_path=str(settings.hysteria_cert_path),
    key_path=str(settings.hysteria_key_path),
    domain=settings.hysteria_domain,
    acme_email=settings.hysteria_acme_email,
    client_sni=settings.hysteria_client_sni,
    client_insecure=settings.hysteria_client_insecure,
)
Hy2ServiceManager(settings).apply(payload)
PY
}

start_services() {
  systemctl restart vpngate-controller.service
  if [[ "$MODE" == "hy2-native" ]]; then
    systemctl restart hysteria-server.service
  fi
}

print_summary() {
  local host
  host="$(detect_public_host)"
  echo
  echo "Installed mode: $MODE"
  echo "Dashboard: http://${host}:8000"
  echo "Dashboard password: $DASHBOARD_PASSWORD"
  if [[ "$MODE" == "hy2-native" ]]; then
    cd "$PROJECT_DIR"
    set -a
    # shellcheck disable=SC1091
    source .env
    set +a
    VPNGATE_INSTALL_DASHBOARD_HOST="$host" PYTHONPATH="$PROJECT_DIR/backend" "$PROJECT_DIR/.venv/bin/python" - <<'PY'
import os

from app.config import settings
from app.models import HysteriaConfigPayload
from app.services.hysteria import build_client_config

server_host = settings.hysteria_advertise_host or settings.hysteria_domain or "127.0.0.1"
dashboard_host = os.getenv("VPNGATE_INSTALL_DASHBOARD_HOST", server_host)
payload = HysteriaConfigPayload(
    listen_host=settings.hysteria_listen_host,
    listen_port=settings.hysteria_listen_port,
    tls_mode=settings.hysteria_tls_mode,
    auth_password=settings.hysteria_auth_password or "",
    masquerade_url=settings.hysteria_masquerade_url,
    cert_path=str(settings.hysteria_cert_path),
    key_path=str(settings.hysteria_key_path),
    domain=settings.hysteria_domain,
    acme_email=settings.hysteria_acme_email,
    client_sni=settings.hysteria_client_sni,
    client_insecure=settings.hysteria_client_insecure,
)
client = build_client_config(payload, server_host)
print("Hysteria URI:", client.uri)
print()
print("===== Client Share Block =====")
print("把下面这段直接发给客户端：")
print()
print(f"管理面板: http://{dashboard_host}:8000")
print(f"Panel password: {settings.dashboard_password}")
print(f"Server: {client.server}")
print(f"SNI: {client.tls.get('sni')}")
print(f"Insecure: {str(client.tls.get('insecure')).lower()}")
print(f"URI: {client.uri}")
print("===== End =====")
PY
  fi
}

main() {
  require_root "$@"
  detect_mode
  validate_inputs
  install_packages
  sync_project
  install_app
  configure_env
  install_controller_service
  install_hysteria
  apply_hysteria_config
  start_services
  print_summary
}

main "$@"
