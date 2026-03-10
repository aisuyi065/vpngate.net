from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from urllib.parse import quote, urlencode

from app.config import Settings
from app.models import HysteriaClientConfig, HysteriaConfigPayload, HysteriaStatus


def _format_listen(host: str, port: int) -> str:
    normalized_host = (host or "").strip()
    if normalized_host in {"", "0.0.0.0"}:
        return f":{port}"
    return f"{normalized_host}:{port}"


def render_hysteria_config(payload: HysteriaConfigPayload) -> str:
    lines = [f"listen: {_format_listen(payload.listen_host, payload.listen_port)}", ""]
    if payload.tls_mode == "acme":
        if not payload.domain or not payload.acme_email:
            raise ValueError("ACME mode requires both domain and acme_email")
        lines.extend(
            [
                "acme:",
                "  domains:",
                f"    - {payload.domain}",
                f"  email: {payload.acme_email}",
            ]
        )
    else:
        if not payload.cert_path or not payload.key_path:
            raise ValueError("self_signed mode requires cert_path and key_path")
        lines.extend(
            [
                "tls:",
                f"  cert: {payload.cert_path}",
                f"  key: {payload.key_path}",
            ]
        )
    lines.extend(
        [
            "",
            "auth:",
            "  type: password",
            f"  password: {payload.auth_password}",
            "",
            "masquerade:",
            "  type: proxy",
            "  proxy:",
            f"    url: {payload.masquerade_url}",
            "    rewriteHost: true",
            "",
            "quic:",
            "  initStreamReceiveWindow: 26843545",
            "  maxStreamReceiveWindow: 26843545",
            "  initConnReceiveWindow: 67108864",
            "  maxConnReceiveWindow: 67108864",
        ]
    )
    if payload.acl_inline:
        lines.extend(["", "acl:", "  inline:"])
        for rule in payload.acl_inline:
            lines.append(f"    - {json.dumps(rule)}")
    return "\n".join(lines).strip() + "\n"


def build_client_config(payload: HysteriaConfigPayload, server_host: str) -> HysteriaClientConfig:
    server = f"{server_host}:{payload.listen_port}"
    sni = payload.client_sni or payload.domain or server_host
    tls = {"sni": sni, "insecure": payload.client_insecure}
    query = urlencode({"sni": sni, "insecure": int(payload.client_insecure)})
    uri = (
        f"hysteria2://{quote(payload.auth_password, safe='')}@{server}/?{query}#VPNGate-Hysteria2"
    )
    return HysteriaClientConfig(server=server, auth=payload.auth_password, tls=tls, uri=uri)


class Hy2ServiceManager:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def default_payload(self, auth_password: str) -> HysteriaConfigPayload:
        return HysteriaConfigPayload(
            listen_host=self.settings.hysteria_listen_host,
            listen_port=self.settings.hysteria_listen_port,
            tls_mode=self.settings.hysteria_tls_mode,
            auth_password=auth_password,
            masquerade_url=self.settings.hysteria_masquerade_url,
            cert_path=str(self.settings.hysteria_cert_path),
            key_path=str(self.settings.hysteria_key_path),
            domain=self.settings.hysteria_domain,
            acme_email=self.settings.hysteria_acme_email,
            client_sni=self.settings.hysteria_client_sni,
            client_insecure=self.settings.hysteria_client_insecure,
        )

    def apply(self, payload: HysteriaConfigPayload) -> HysteriaStatus:
        config_path = self.settings.hysteria_config_path
        config_path.parent.mkdir(parents=True, exist_ok=True)
        if payload.tls_mode == "self_signed":
            self._ensure_self_signed_cert(payload)
        config_path.write_text(render_hysteria_config(payload), encoding="utf-8")
        return self.restart(payload)

    def restart(self, payload: HysteriaConfigPayload) -> HysteriaStatus:
        self._run_systemctl("restart", self.settings.hysteria_service_name)
        return self.get_status(payload)

    def get_status(self, payload: HysteriaConfigPayload) -> HysteriaStatus:
        service_state = self._systemctl_status()
        enabled = self._systemctl_enabled()
        installed = Path("/usr/local/bin/hysteria").exists() or shutil.which("hysteria") is not None
        warning = None
        if payload.tls_mode == "self_signed":
            warning = "Self-signed certificate mode requires insecure clients or manual trust."
        return HysteriaStatus(
            installed=installed,
            service_name=self.settings.hysteria_service_name,
            service_state=service_state,
            enabled=enabled,
            listen_host=payload.listen_host,
            listen_port=payload.listen_port,
            tls_mode=payload.tls_mode,
            domain=payload.domain,
            masquerade_url=payload.masquerade_url,
            config_path=str(self.settings.hysteria_config_path),
            warning=warning,
        )

    def read_logs(self, limit: int = 100) -> list[str]:
        if shutil.which("journalctl") is None:
            return []
        result = subprocess.run(
            [
                "journalctl",
                "-u",
                self.settings.hysteria_service_name,
                "--no-pager",
                "-n",
                str(limit),
                "-o",
                "cat",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            return []
        return [line for line in result.stdout.splitlines() if line.strip()]

    def _ensure_self_signed_cert(self, payload: HysteriaConfigPayload) -> None:
        cert_path = Path(payload.cert_path or self.settings.hysteria_cert_path)
        key_path = Path(payload.key_path or self.settings.hysteria_key_path)
        cert_path.parent.mkdir(parents=True, exist_ok=True)
        if cert_path.exists() and key_path.exists():
            return
        if shutil.which("openssl") is None:
            raise RuntimeError("openssl binary not found")
        common_name = payload.client_sni or payload.domain or "localhost"
        subprocess.run(
            [
                "openssl",
                "req",
                "-x509",
                "-nodes",
                "-newkey",
                "rsa:2048",
                "-keyout",
                str(key_path),
                "-out",
                str(cert_path),
                "-subj",
                f"/CN={common_name}",
                "-days",
                "3650",
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        key_path.chmod(0o600)
        cert_path.chmod(0o644)

    def _systemctl_status(self) -> str:
        if shutil.which("systemctl") is None:
            return "unavailable"
        result = subprocess.run(
            ["systemctl", "is-active", self.settings.hysteria_service_name],
            capture_output=True,
            text=True,
            check=False,
        )
        state = (result.stdout or result.stderr).strip()
        return state or "unknown"

    def _systemctl_enabled(self) -> bool:
        if shutil.which("systemctl") is None:
            return False
        result = subprocess.run(
            ["systemctl", "is-enabled", self.settings.hysteria_service_name],
            capture_output=True,
            text=True,
            check=False,
        )
        return result.returncode == 0 and result.stdout.strip() == "enabled"

    def _run_systemctl(self, action: str, service_name: str) -> None:
        if shutil.which("systemctl") is None:
            raise RuntimeError("systemctl is not available")
        result = subprocess.run(
            ["systemctl", action, service_name],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            message = (result.stderr or result.stdout).strip() or f"systemctl {action} failed"
            raise RuntimeError(message)
