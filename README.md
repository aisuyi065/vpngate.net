# VPNGate Controller

Deploy a Hysteria 2 edge on no-TUN hosts in one command, or keep the older VPNGate/OpenVPN workflow on machines that still have TUN.

This project bundles three things that usually get glued together by hand:

- the official `Hysteria 2` server service
- a small web dashboard for status, logs, and client URI output
- a single installer that prepares the host, writes config, and starts services

## Hero

Use it when you want a practical operator workflow instead of a pile of shell fragments:

- run `Hysteria 2` on an LXC or other no-TUN VPS without touching the host default route
- keep a visible control plane for service status, logs, and generated client links
- preserve the older VPNGate/OpenVPN path for hosts that still support `/dev/net/tun`

### Quick Start

No-TUN or LXC host:

```bash
bash install.sh --mode hy2-native --port 8443 --dashboard-password 你的面板密码
```

If you omit `--dashboard-password`, the installer will generate one and print it at the end.

Real domain + ACME certificate:

```bash
bash install.sh --mode hy2-native --domain vpn.example.com --acme-email ops@example.com --port 443 --dashboard-password 你的面板密码
```

### Why It Feels Better Than a Raw One-Liner

- one installer instead of multiple disconnected scripts
- official `hysteria-server.service`, but with project-managed config and dashboard visibility
- generated `hysteria2://...` client URI at install time
- dashboard password support at install time, with password-only access and no username
- dashboard password can be changed later inside the panel without rerunning the installer
- compatibility defaults that match the familiar community `hy2.sh` flow:
  - `SNI=bing.com`
  - `masquerade=https://bing.com`
  - `insecure=1`

### What Gets Installed

- `hysteria-server.service`
- `vpngate-controller.service`
- Hysteria config at `/etc/hysteria/config.yaml`
- web dashboard on port `8000`

## Runtime Modes

| Mode | Best for | Depends on TUN | What it controls |
| --- | --- | --- | --- |
| `hy2-native` | LXC, no-TUN VPS, Hysteria 2 ingress | No | Only traffic that enters through the local Hysteria 2 service |
| `openvpn` | Traditional Linux or WSL setups with VPNGate exits | Yes | The local OpenVPN session and its route scope |

## Fastest Path

If your target host is an LXC VPS or any server without `/dev/net/tun`, use `hy2-native`.

### Self-signed Hysteria 2 install

```bash
bash install.sh --mode hy2-native --port 8443 --dashboard-password 你的面板密码
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
bash install.sh --mode hy2-native --domain vpn.example.com --acme-email ops@example.com --port 443 --dashboard-password 你的面板密码
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
http://PUBLIC_IP:8000
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
- `VPNGATE_DASHBOARD_PASSWORD`
- `VPNGATE_DASHBOARD_SESSION_SECRET`
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
