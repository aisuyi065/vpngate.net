# Hysteria 2 Native Mode Design

## Background

The current project is an OpenVPN-based VPNGate controller. It refreshes VPNGate nodes, writes `.ovpn` files, and starts an `openvpn` process that modifies default routes. This model assumes TUN support and is not suitable for LXC VPS environments without `/dev/net/tun`.

The new requirement is different: this machine runs a Hysteria 2 server, and only traffic entering through Hysteria 2 should be handled by the service. The host machine itself must not be globally rerouted. Docker is out of scope, and the deployment target must work on LXC.

## Goal

Add a first-class `hy2-native` runtime mode that installs, configures, monitors, and exposes Hysteria 2 directly from this project. In this mode, the project no longer tries to own the system default route and does not depend on OpenVPN/TUN.

## Non-goals

- Do not make local host traffic exit through VPNGate in `hy2-native` mode.
- Do not emulate TUN or container isolation on LXC.
- Do not promise that VPNGate/OpenVPN exits can work without TUN.
- Do not vendor third-party one-click scripts directly into the repository.

## External References

- Official Hysteria installation: `https://v2.hysteria.network/docs/getting-started/Installation/`
- Official full server config: `https://v2.hysteria.network/docs/advanced/Full-Server-Config/`
- Official ACL docs: `https://v2.hysteria.network/docs/advanced/ACL/`
- Official GitHub repo: `https://github.com/apernet/hysteria`
- User-provided helper scripts:
  - `https://raw.githubusercontent.com/yeahwu/v2ray-wss/main/tcp-wss.sh`
  - `https://raw.githubusercontent.com/yeahwu/v2ray-wss/main/hy2.sh`

## Chosen Architecture

### Runtime modes

The backend will support two runtime modes:

- `openvpn`: existing behavior, kept for hosts with TUN support.
- `hy2-native`: new mode for LXC and other no-TUN environments.

A lightweight runtime manager will expose the active mode in the backend status payload and the frontend UI. When `hy2-native` is enabled, VPNGate node selection remains visible only as legacy/inactive functionality or is hidden entirely in the UI depending on available data.

### Hysteria 2 service management

The backend will manage the existing systemd service installed by the official Hysteria installer instead of embedding Hysteria internals. The project becomes an orchestrator around:

- `/etc/hysteria/config.yaml`
- `hysteria-server.service`
- generated client connection metadata
- runtime logs from systemd/journal

This avoids copying the third-party shell logic while still delivering a single-project experience.

### Installer integration

A new project-owned `install.sh` will become the preferred one-shot installer for Debian/Ubuntu/LXC systems. It will:

1. install system packages and app dependencies,
2. install the backend and frontend,
3. call the official Hysteria installer,
4. render the Hysteria config from project variables,
5. write the project `.env`,
6. install/update systemd units,
7. start both the controller and Hysteria services,
8. print a usable `hysteria2://` client URI.

The user-provided community scripts influence UX only: random password generation, optional random port, and client config output. We will not reuse their insecure defaults verbatim.

## Configuration model

### Project environment

Add Hysteria-specific settings such as:

- runtime mode
- Hysteria listen host and UDP port
- auth password
- TLS mode (`acme` or `self_signed`)
- certificate paths
- ACME domain/email
- masquerade URL
- client SNI / insecure toggle
- ACL / outbounds raw config hooks for future expansion

### Generated Hysteria config

The project will generate the server YAML with the official field names. Two certificate paths are supported:

- `acme` for production with a real domain,
- `tls` with local self-signed cert/key fallback.

The initial implementation will keep ACL/outbounds optional but reserve typed config fields so the backend can expose them later without schema churn.

## Backend changes

### New service manager

Add a `Hy2ServiceManager` responsible for:

- rendering `/etc/hysteria/config.yaml`,
- writing self-signed certs when needed,
- restarting and querying `hysteria-server.service`,
- reading recent logs,
- generating the client URI and JSON payload.

### New API surface

Expose dedicated Hysteria endpoints:

- `GET /api/hysteria/status`
- `GET /api/hysteria/client-config`
- `POST /api/hysteria/apply`
- `POST /api/hysteria/restart`
- `GET /api/hysteria/logs`

The existing `/api/status` stays as the global runtime status entry point, but it gains Hysteria-aware fields in `hy2-native` mode.

## Frontend changes

The dashboard will gain a Hysteria 2 section with:

- service status,
- runtime mode badge,
- listen port,
- TLS mode,
- masquerade target,
- client URI / copyable config,
- recent service logs,
- restart/apply controls.

The VPNGate residential server table remains meaningful only in `openvpn` mode, so the UI should avoid presenting fake “connect” actions when `hy2-native` is active.

## Security notes

- Prefer ACME when a real domain is available.
- Self-signed mode is allowed but clearly labeled as insecure for clients.
- Secrets should live in `.env` and generated config files with restrictive permissions.
- Default self-signed mode intentionally mirrors the referenced community script’s `bing.com` SNI, `https://bing.com` masquerade target, and insecure client flag for compatibility with the user’s established client setup.

## Testing strategy

- backend API tests for new Hysteria endpoints,
- unit tests for config rendering,
- frontend component test for the Hysteria panel,
- frontend build verification,
- backend pytest verification.

## Deployment notes

- No Docker requirement.
- Must work on LXC without `/dev/net/tun`.
- systemd is the default service manager path.
- If systemd is unavailable, the installer should fail loudly with actionable guidance instead of pretending success.

## Git note

This workspace currently has no `.git` directory, so the “commit the design doc” step from the brainstorming workflow cannot be completed here. The document is still written to the repository so it can be committed later in the real VCS root.
