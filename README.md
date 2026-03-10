# VPNGate Controller

A single-node VPNGate controller that refreshes VPNGate server data, enriches server IP quality, auto-selects residential OpenVPN nodes, and exposes a web dashboard for manual and automatic connection control.

## Features

- Refreshes VPNGate nodes from the public CSV/API feed and the public site table.
- Enriches each server IP with IP intelligence and classifies it as `residential`, `hosting`, or `unknown`.
- Supports automatic OpenVPN selection using a country whitelist and a quality score.
- Supports a `hy2-native` runtime mode for Hysteria 2 server management on LXC or other no-TUN hosts.
- Exposes a FastAPI backend plus a Vue dashboard.
- Supports Linux hosts and WSL, with a clear WSL-only traffic scope warning.

## Project Layout

- `backend/`: FastAPI API, scheduler, storage, VPNGate ingestion, and OpenVPN connector.
- `frontend/`: Vue 3 dashboard.
- `scripts/`: local start and install scripts.
- `systemd/`: Linux service unit.

## Local Development

### Backend

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -U pip
pip install -e backend[dev]
pytest backend/tests
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

### Run the app

```bash
cp .env.example .env
./scripts/start-controller.sh
```

Then open `http://localhost:8000` after building the frontend, or run the frontend dev server on `http://localhost:5173`.

## Deployment

### Debian VPS

```bash
./scripts/install-debian.sh
```

### Hysteria 2 / LXC / no-TUN install

```bash
bash install.sh --mode hy2-native --port 8443
```

With a real domain and ACME:

```bash
bash install.sh --mode hy2-native --domain vpn.example.com --acme-email ops@example.com --port 443
```

### WSL Ubuntu

```bash
./scripts/install-wsl.sh
```

WSL mode manages WSL traffic only. It does not take over the full Windows host network stack.

## Environment Variables

Copy `.env.example` to `.env` and adjust as needed.

Key Hysteria-related variables:

- `VPNGATE_RUNTIME_MODE=hy2-native`
- `HYSTERIA_LISTEN_PORT`
- `HYSTERIA_TLS_MODE=self_signed|acme`
- `HYSTERIA_DOMAIN`
- `HYSTERIA_ACME_EMAIL`
- `HYSTERIA_AUTH_PASSWORD`
- `HYSTERIA_MASQUERADE_URL`
- `HYSTERIA_ADVERTISE_HOST`

Default self-signed mode follows the same client-facing defaults as the referenced community `hy2.sh`: `SNI=bing.com`, `masquerade=https://bing.com`, and client `insecure=1`.

## Notes

- Automatic connection currently targets OpenVPN only.
- The backend must run with sufficient privileges to let OpenVPN create a TUN device and modify routes.
- `hy2-native` mode does not take over host routing. It only manages the local Hysteria 2 service and the traffic proxied through it.
- On LXC hosts without `/dev/net/tun`, prefer `hy2-native`; the legacy VPNGate OpenVPN path is not expected to work there.
- Docker deployment uses `network_mode: host` and `NET_ADMIN`; native deployment is still the recommended path for route control.
