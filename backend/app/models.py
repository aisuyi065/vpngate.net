from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field


def utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class ServerRecord(BaseModel):
    hostname: str
    ip: str
    score: int
    ping: int
    speed: int
    country_long: str
    country_code: str
    num_vpn_sessions: int
    uptime: int
    total_users: int
    total_traffic: int
    log_type: str
    operator: str
    message: str
    openvpn_config_b64: str
    supports_softether: bool = False
    supports_l2tp: bool = False
    supports_openvpn: bool = False
    supports_sstp: bool = False
    openvpn_tcp_port: int | None = None
    openvpn_udp_port: int | None = None
    last_seen_at: str = Field(default_factory=utcnow_iso)
    updated_at: str = Field(default_factory=utcnow_iso)


class SiteServerMetadata(BaseModel):
    hostname: str
    ip: str
    supports_softether: bool = False
    supports_l2tp: bool = False
    supports_openvpn: bool = False
    supports_sstp: bool = False
    openvpn_tcp_port: int | None = None
    openvpn_udp_port: int | None = None


class IpQualityRecord(BaseModel):
    ip: str
    provider: str = "unknown"
    quality_class: Literal["residential", "hosting", "unknown"] = "unknown"
    isp: str | None = None
    organization: str | None = None
    company_type: str | None = None
    asn_type: str | None = None
    country_code: str | None = None
    is_datacenter: bool = False
    is_proxy: bool = False
    is_vpn: bool = False
    is_tor: bool = False
    raw: dict[str, Any] | None = None
    updated_at: str = Field(default_factory=utcnow_iso)


class ConnectionStatus(BaseModel):
    state: Literal["idle", "connecting", "connected", "degraded", "reconnecting", "failed"] = "idle"
    mode: str = "mock"
    environment: str = "linux"
    current_scope: str = "system"
    auto_mode_enabled: bool = False
    allowed_countries: list[str] = Field(default_factory=list)
    connected_server_ip: str | None = None
    connected_server_hostname: str | None = None
    current_public_ip: str | None = None
    note: str | None = None
    last_error: str | None = None
    updated_at: str = Field(default_factory=utcnow_iso)


class ServerListItem(ServerRecord):
    ip_quality: IpQualityRecord = Field(default_factory=lambda: IpQualityRecord(ip="0.0.0.0"))
    quality_score: float = 0.0
    is_connected: bool = False


class ServerFilters(BaseModel):
    country: str | None = None
    protocol: Literal["openvpn", "softether", "l2tp", "sstp"] | None = None
    residential: bool | None = None


class AutoModePayload(BaseModel):
    enabled: bool
    allowed_countries: list[str] = Field(default_factory=list)


class RefreshResult(BaseModel):
    servers: int
    refreshed: bool
    quality_enriched: int = 0
    updated_at: str = Field(default_factory=utcnow_iso)


class HysteriaConfigPayload(BaseModel):
    listen_host: str = "0.0.0.0"
    listen_port: int = 8443
    tls_mode: Literal["self_signed", "acme"] = "self_signed"
    auth_password: str
    masquerade_url: str = "https://bing.com"
    cert_path: str | None = "/etc/hysteria/server.crt"
    key_path: str | None = "/etc/hysteria/server.key"
    domain: str | None = None
    acme_email: str | None = None
    client_sni: str | None = None
    client_insecure: bool = True
    acl_inline: list[str] = Field(default_factory=list)


class HysteriaStatus(BaseModel):
    runtime_mode: str = "hy2-native"
    installed: bool = False
    service_name: str = "hysteria-server.service"
    service_state: str = "unknown"
    enabled: bool = False
    listen_host: str = "0.0.0.0"
    listen_port: int = 8443
    tls_mode: Literal["self_signed", "acme"] = "self_signed"
    domain: str | None = None
    masquerade_url: str = "https://bing.com"
    config_path: str = "/etc/hysteria/config.yaml"
    warning: str | None = None
    updated_at: str = Field(default_factory=utcnow_iso)


class HysteriaClientConfig(BaseModel):
    server: str
    auth: str
    tls: dict[str, Any]
    uri: str


class ConnectionLogEntry(BaseModel):
    id: int | None = None
    created_at: str = Field(default_factory=utcnow_iso)
    server_ip: str | None = None
    level: str = "info"
    event_type: str = "event"
    message: str
