from __future__ import annotations

import os
from pathlib import Path

from pydantic import BaseModel, Field


def _csv_env(name: str, default: list[str]) -> list[str]:
    raw = os.getenv(name)
    if not raw:
        return default
    return [part.strip() for part in raw.split(',') if part.strip()]


def _bool_env(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


class Settings(BaseModel):
    app_name: str = "VPNGate Controller"
    bind_host: str = os.getenv("VPNGATE_BIND_HOST", "0.0.0.0")
    bind_port: int = int(os.getenv("VPNGATE_BIND_PORT", "8000"))
    data_dir: Path = Path(os.getenv("VPNGATE_DATA_DIR", "data"))
    runtime_mode: str = os.getenv("VPNGATE_RUNTIME_MODE", "openvpn")
    connector_mode: str = os.getenv("VPNGATE_CONNECTOR_MODE", "openvpn")
    ip_intel_provider: str = os.getenv("VPNGATE_IP_INTEL_PROVIDER", "ipapi.is")
    refresh_interval_seconds: int = int(os.getenv("VPNGATE_REFRESH_INTERVAL_SECONDS", "3600"))
    heartbeat_interval_seconds: int = int(os.getenv("VPNGATE_HEARTBEAT_INTERVAL_SECONDS", "60"))
    quality_ttl_seconds: int = int(os.getenv("VPNGATE_QUALITY_TTL_SECONDS", str(24 * 3600)))
    max_quality_lookups_per_refresh: int = int(os.getenv("VPNGATE_MAX_QUALITY_LOOKUPS_PER_REFRESH", "60"))
    connect_timeout_seconds: int = int(os.getenv("VPNGATE_CONNECT_TIMEOUT_SECONDS", "45"))
    tunnel_health_stale_seconds: int = int(os.getenv("VPNGATE_TUNNEL_HEALTH_STALE_SECONDS", "20"))
    background_tasks_enabled: bool = os.getenv("VPNGATE_BACKGROUND_TASKS_ENABLED", "true").lower() == "true"
    auto_mode_default_enabled: bool = os.getenv("VPNGATE_AUTO_MODE_DEFAULT_ENABLED", "true").lower() == "true"
    auto_mode_default_countries: list[str] = Field(default_factory=lambda: _csv_env("VPNGATE_AUTO_COUNTRIES", ["JP"]))
    allowed_origins: list[str] = Field(default_factory=lambda: _csv_env("VPNGATE_ALLOWED_ORIGINS", ["http://localhost:5173", "http://127.0.0.1:5173"]))
    ipinfo_token: str | None = os.getenv("IPINFO_TOKEN")
    ipapi_token: str | None = os.getenv("IPAPI_TOKEN")
    hysteria_service_name: str = os.getenv("HYSTERIA_SERVICE_NAME", "hysteria-server.service")
    hysteria_config_dir: Path = Path(os.getenv("HYSTERIA_CONFIG_DIR", "/etc/hysteria"))
    hysteria_config_name: str = os.getenv("HYSTERIA_CONFIG_NAME", "config.yaml")
    hysteria_listen_host: str = os.getenv("HYSTERIA_LISTEN_HOST", "0.0.0.0")
    hysteria_listen_port: int = int(os.getenv("HYSTERIA_LISTEN_PORT", "8443"))
    hysteria_tls_mode: str = os.getenv("HYSTERIA_TLS_MODE", "self_signed")
    hysteria_domain: str | None = os.getenv("HYSTERIA_DOMAIN")
    hysteria_acme_email: str | None = os.getenv("HYSTERIA_ACME_EMAIL")
    hysteria_auth_password: str | None = os.getenv("HYSTERIA_AUTH_PASSWORD")
    hysteria_masquerade_url: str = os.getenv("HYSTERIA_MASQUERADE_URL", "https://bing.com")
    hysteria_cert_path: Path = Path(os.getenv("HYSTERIA_CERT_PATH", "/etc/hysteria/server.crt"))
    hysteria_key_path: Path = Path(os.getenv("HYSTERIA_KEY_PATH", "/etc/hysteria/server.key"))
    hysteria_client_sni: str | None = os.getenv("HYSTERIA_CLIENT_SNI", "bing.com")
    hysteria_client_insecure: bool = _bool_env("HYSTERIA_CLIENT_INSECURE", True)
    hysteria_advertise_host: str | None = os.getenv("HYSTERIA_ADVERTISE_HOST")

    @property
    def db_path(self) -> Path:
        return self.data_dir / "vpngate.db"

    @property
    def openvpn_dir(self) -> Path:
        return self.data_dir / "openvpn"

    @property
    def hysteria_config_path(self) -> Path:
        return self.hysteria_config_dir / self.hysteria_config_name

    def prepare(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.openvpn_dir.mkdir(parents=True, exist_ok=True)


settings = Settings()
settings.prepare()
