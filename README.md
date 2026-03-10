# VPNGate Controller

VPNGate Controller is a single-node control plane for two different network roles:

- `openvpn` mode: refresh VPNGate nodes, score residential-looking exits, and manage a local OpenVPN session
- `hy2-native` mode: install and manage a local Hysteria 2 server on hosts that do not have `/dev/net/tun`, such as many LXC VPS environments

The project ships a FastAPI backend, a Vue dashboard, and a one-shot installer.

## What This Project Solves

Use this project when you want one of these outcomes:

- run a Hysteria 2 server on an LXC or other no-TUN host without touching the host default route
- keep a simple dashboard for service status, client URI output, and logs
- keep the older VPNGate/OpenVPN workflow available for hosts that do have TUN support

## Runtime Modes

| Mode | Best for | Depends on TUN | What it controls |
| --- | --- | --- | --- |
| `hy2-native` | LXC, no-TUN VPS, Hysteria 2 ingress | No | Only traffic that enters through the local Hysteria 2 service |
| `openvpn` | Traditional Linux or WSL setups with VPNGate exits | Yes | The local OpenVPN session and its route scope |

## Fastest Path

If your target host is an LXC VPS or any server without `/dev/net/tun`, use `hy2-native`.

### Self-signed Hysteria 2 install

```bash
bash install.sh --mode hy2-native --port 8443
```

What you get:

- the controller dashboard on port `8000`
- the official `hysteria-server.service`
- generated Hysteria 2 server config at `/etc/hysteria/config.yaml`
- a printed client URI in this format:

```text
hysteria2://PASSWORD@SERVER_IP:8443/?sni=bing.com&insecure=1#VPNGate-Hysteria2
```

Default self-signed compatibility values intentionally match the referenced community `hy2.sh` flow:

- `SNI=bing.com`
- `masquerade=https://bing.com`
- `insecure=1`

### Domain + ACME install

```bash
bash install.sh --mode hy2-native --domain vpn.example.com --acme-email ops@example.com --port 443
```

Use this when you want a cleaner production setup with a real certificate.

### Legacy VPNGate / OpenVPN install

```bash
./scripts/install-debian.sh
```

Use this only on hosts with `/dev/net/tun`.

## Post-Install Checks

After install, verify both services:

```bash
systemctl status hysteria-server.service
systemctl status vpngate-controller.service
```

Read recent Hysteria logs:

```bash
journalctl --no-pager -e -u hysteria-server.service
```

Open the dashboard:

```text
http://SERVER_IP:8000
```

## Firewall Notes

Open these ports:

- `8000/tcp` for the dashboard
- your chosen Hysteria 2 port over `udp` such as `8443/udp` or `443/udp`

If your cloud provider uses security groups, open the same ports there as well.

## Project Layout

- `backend/` - FastAPI app, controller logic, storage, VPNGate ingestion, Hysteria manager
- `frontend/` - Vue 3 dashboard
- `scripts/` - helper scripts for local starts and legacy install paths
- `systemd/` - controller service unit
- `docs/` - plans and operator-facing documents

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
npm test
npm run build
```

### Run locally

```bash
cp .env.example .env
./scripts/start-controller.sh
```

Then visit `http://localhost:8000`.

## Key Environment Variables

Copy `.env.example` to `.env` and change only what you need.

Most important Hysteria 2 variables:

- `VPNGATE_RUNTIME_MODE=hy2-native`
- `HYSTERIA_LISTEN_PORT`
- `HYSTERIA_TLS_MODE=self_signed|acme`
- `HYSTERIA_DOMAIN`
- `HYSTERIA_ACME_EMAIL`
- `HYSTERIA_AUTH_PASSWORD`
- `HYSTERIA_MASQUERADE_URL`
- `HYSTERIA_ADVERTISE_HOST`

## Important Limits

- `hy2-native` mode does not reroute host traffic. It only handles traffic proxied through the local Hysteria 2 server.
- LXC hosts without `/dev/net/tun` should use `hy2-native`, not the VPNGate/OpenVPN path.
- Automatic residential node selection still belongs to the `openvpn` path.

## Deployment Doc You Can Forward

If you want a Chinese deployment handoff that you can send directly to someone else, use:

- `docs/HY2-NATIVE-DEPLOYMENT.zh-CN.md`
