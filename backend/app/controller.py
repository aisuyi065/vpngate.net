from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from uuid import uuid4

from app.config import Settings, settings
from app.models import (
    AutoModePayload,
    ConnectionStatus,
    HysteriaClientConfig,
    HysteriaConfigPayload,
    HysteriaStatus,
    IpQualityRecord,
    RefreshResult,
    ServerFilters,
    ServerListItem,
    ServerRecord,
)
from app.services.connectors import BaseConnector, build_connector
from app.services.hysteria import Hy2ServiceManager, build_client_config
from app.services.ip_intel import IpIntelService
from app.services.scoring import rank_candidate_servers, score_server, select_best_server
from app.services.system import detect_environment, fetch_public_ip
from app.services.vpngate import fetch_server_catalog
from app.storage import Storage


class VpnGateController:
    def __init__(self, app_settings: Settings | None = None, connector: BaseConnector | None = None) -> None:
        self.settings = app_settings or settings
        self.storage = Storage(self.settings.db_path)
        self.storage.initialize()
        self.connector = connector or build_connector(self.settings)
        self.hysteria = Hy2ServiceManager(self.settings)
        self.ip_intel = IpIntelService(self.settings.ip_intel_provider, self.settings.ipapi_token or self.settings.ipinfo_token)
        self.allowed_countries = self._normalise_countries(
            self.storage.get_state("allowed_countries", self.settings.auto_mode_default_countries)
        )
        self.auto_mode_enabled = bool(self.storage.get_state("auto_mode_enabled", self.settings.auto_mode_default_enabled))
        self._background_task: asyncio.Task[None] | None = None
        self._stop_event = asyncio.Event()
        self._refresh_lock = asyncio.Lock()
        self._public_ip_cache: tuple[str | None, float] = (None, 0.0)
        self._ensure_hysteria_config_state()

    async def start(self) -> None:
        if self.settings.background_tasks_enabled and self._background_task is None:
            self._stop_event.clear()
            self._background_task = asyncio.create_task(self._background_loop())

    async def stop(self) -> None:
        self._stop_event.set()
        if self._background_task:
            self._background_task.cancel()
            try:
                await self._background_task
            except asyncio.CancelledError:
                pass
            self._background_task = None
        await self.connector.disconnect()

    async def refresh(self) -> RefreshResult:
        if self._is_hysteria_mode():
            return RefreshResult(servers=0, refreshed=False, quality_enriched=0)
        async with self._refresh_lock:
            servers = await fetch_server_catalog()
            self.storage.upsert_servers(servers)
            enriched = await self._refresh_ip_quality(servers)
            self.storage.put_state("last_refresh_at", datetime.now(timezone.utc).isoformat())
            self.storage.append_log("refresh", f"Refreshed {len(servers)} servers and enriched {enriched} IP records")
            return RefreshResult(servers=len(servers), refreshed=True, quality_enriched=enriched)

    async def list_servers(self, filters: ServerFilters) -> list[ServerListItem]:
        if self._is_hysteria_mode():
            return []
        servers = self.storage.list_servers()
        qualities = self.storage.get_ip_qualities([server.ip for server in servers])
        status = await self.connector.get_status()
        items: list[ServerListItem] = []
        for server in servers:
            quality = qualities.get(server.ip, IpQualityRecord(ip=server.ip))
            if filters.country and server.country_code.upper() != filters.country.upper():
                continue
            if filters.protocol and not getattr(server, f"supports_{filters.protocol}"):
                continue
            if filters.residential is True and quality.quality_class != "residential":
                continue
            if filters.residential is False and quality.quality_class == "residential":
                continue
            items.append(
                ServerListItem(
                    **server.model_dump(),
                    ip_quality=quality,
                    quality_score=score_server(server, quality),
                    is_connected=status.connected_server_ip == server.ip,
                )
            )
        items.sort(key=lambda item: (item.is_connected, item.quality_score, item.score), reverse=True)
        return items

    async def get_status(self) -> ConnectionStatus:
        if self._is_hysteria_mode():
            hysteria_status = await self.get_hysteria_status()
            public_ip = await self._get_public_ip_cached(force=False)
            return ConnectionStatus(
                state=self._map_hysteria_state(hysteria_status.service_state),
                mode="hy2-native",
                environment=detect_environment(),
                current_scope="hy2",
                auto_mode_enabled=self.auto_mode_enabled,
                allowed_countries=self.allowed_countries,
                current_public_ip=public_ip,
                note="Only Hysteria 2 client traffic is handled; host traffic is not rerouted.",
                last_error="Hysteria 2 service is in a failed state." if hysteria_status.service_state == "failed" else None,
            )
        base_status = await self.connector.get_status()
        public_ip = await self._get_public_ip_cached(force=base_status.state == "connected")
        return base_status.model_copy(
            update={
                "auto_mode_enabled": self.auto_mode_enabled,
                "allowed_countries": self.allowed_countries,
                "current_public_ip": public_ip,
            }
        )

    async def connect(self, server_id: str) -> ConnectionStatus:
        if self._is_hysteria_mode():
            raise RuntimeError("Manual VPNGate connections are unavailable in hy2-native mode")
        server = self.storage.get_server(server_id)
        if not server:
            raise KeyError(f"Server {server_id} was not found")
        status = await self.connector.connect(server)
        self.storage.append_log("connect", f"Connected to {server.hostname} ({server.ip})", server_ip=server.ip)
        public_ip = await self._get_public_ip_cached(force=True)
        return status.model_copy(update={"auto_mode_enabled": self.auto_mode_enabled, "allowed_countries": self.allowed_countries, "current_public_ip": public_ip})

    async def disconnect(self) -> ConnectionStatus:
        if self._is_hysteria_mode():
            raise RuntimeError("Disconnect is unavailable in hy2-native mode")
        status = await self.connector.disconnect()
        self.storage.append_log("disconnect", "Disconnected current VPN session")
        public_ip = await self._get_public_ip_cached(force=True)
        return status.model_copy(update={"auto_mode_enabled": self.auto_mode_enabled, "allowed_countries": self.allowed_countries, "current_public_ip": public_ip})

    async def update_auto_mode(self, enabled: bool, countries: list[str]) -> ConnectionStatus:
        self.auto_mode_enabled = enabled
        self.allowed_countries = self._normalise_countries(countries or self.settings.auto_mode_default_countries)
        self.storage.put_state("auto_mode_enabled", self.auto_mode_enabled)
        self.storage.put_state("allowed_countries", self.allowed_countries)
        self.storage.append_log("auto_mode", f"Auto mode set to {enabled} for countries: {', '.join(self.allowed_countries)}")
        if self.auto_mode_enabled and not self._is_hysteria_mode():
            await self.ensure_auto_connected()
        return await self.get_status()

    async def get_hysteria_status(self) -> HysteriaStatus:
        payload = self._get_hysteria_config()
        return await asyncio.to_thread(self.hysteria.get_status, payload)

    async def get_hysteria_client_config(self) -> HysteriaClientConfig:
        payload = self._get_hysteria_config()
        public_ip = await self._get_public_ip_cached(force=False)
        server_host = self.settings.hysteria_advertise_host or payload.domain or public_ip or "127.0.0.1"
        return await asyncio.to_thread(build_client_config, payload, server_host)

    async def apply_hysteria_config(self, payload: HysteriaConfigPayload) -> HysteriaStatus:
        self.storage.put_state("hysteria_config", payload.model_dump())
        status = await asyncio.to_thread(self.hysteria.apply, payload)
        self.storage.append_log(
            "hysteria_apply",
            f"Applied Hysteria config on UDP {payload.listen_port} using {payload.tls_mode}",
        )
        return status

    async def restart_hysteria(self) -> HysteriaStatus:
        payload = self._get_hysteria_config()
        status = await asyncio.to_thread(self.hysteria.restart, payload)
        self.storage.append_log("hysteria_restart", "Restarted Hysteria service")
        return status

    async def list_hysteria_logs(self, limit: int = 100) -> list[str]:
        return await asyncio.to_thread(self.hysteria.read_logs, limit)

    async def ensure_auto_connected(self) -> ConnectionStatus:
        status = await self.connector.get_status()
        if status.state == "connected":
            healthy, reason = await self.connector.health_check()
            if healthy:
                return await self.get_status()
            self.storage.append_log(
                "health_check",
                f"Current tunnel {status.connected_server_ip} failed health check: {reason}",
                server_ip=status.connected_server_ip,
                level="warning",
            )
            await self.connector.disconnect()
        servers = self.storage.list_servers()
        if not servers:
            await self.refresh()
            servers = self.storage.list_servers()
        qualities = self.storage.get_ip_qualities([server.ip for server in servers])
        excluded_ips = {status.connected_server_ip} if status.connected_server_ip else set()
        candidates = rank_candidate_servers(servers, qualities, self.allowed_countries, exclude_ips=excluded_ips)
        if not candidates:
            self.storage.append_log("auto_mode", "No residential OpenVPN node matched the current country whitelist", level="warning")
            return await self.get_status()
        last_error: str | None = None
        for candidate in candidates:
            try:
                return await self.connect(candidate.ip)
            except Exception as exc:
                last_error = str(exc)
                self.storage.append_log(
                    "auto_mode",
                    f"Auto connect failed for {candidate.ip}: {exc}",
                    server_ip=candidate.ip,
                    level="error",
                )
        return (await self.get_status()).model_copy(update={"last_error": last_error})

    async def list_logs(self, server_id: str | None = None) -> list[dict]:
        logs = self.storage.list_logs(server_ip=server_id)
        connector_logs = await self.connector.read_logs(limit=50)
        payload = [entry.model_dump() for entry in logs]
        for line in connector_logs[-20:]:
            payload.append({
                "id": None,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "server_ip": server_id,
                "level": "debug",
                "event_type": "connector",
                "message": line,
            })
        return payload

    async def _refresh_ip_quality(self, servers: list[ServerRecord]) -> int:
        existing = self.storage.get_ip_qualities([server.ip for server in servers])
        candidates: list[ServerRecord] = []
        now_ts = datetime.now(timezone.utc).timestamp()
        for server in servers:
            quality = existing.get(server.ip)
            if quality is None:
                candidates.append(server)
                continue
            updated_ts = datetime.fromisoformat(quality.updated_at).timestamp()
            if now_ts - updated_ts > self.settings.quality_ttl_seconds:
                candidates.append(server)
        candidates.sort(key=lambda server: (server.score, -server.ping, server.total_users), reverse=True)
        candidates = candidates[: self.settings.max_quality_lookups_per_refresh]
        enriched: list[IpQualityRecord] = []
        for server in candidates:
            try:
                enriched.append(await self.ip_intel.lookup(server.ip))
            except Exception as exc:
                self.storage.append_log("ip_quality", f"IP intelligence lookup failed for {server.ip}: {exc}", server_ip=server.ip, level="warning")
        self.storage.upsert_ip_qualities(enriched)
        return len(enriched)

    async def _background_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                if self._is_hysteria_mode():
                    await self.get_hysteria_status()
                else:
                    last_refresh = self.storage.get_state("last_refresh_at")
                    should_refresh = True
                    if last_refresh:
                        try:
                            last_ts = datetime.fromisoformat(last_refresh).timestamp()
                            should_refresh = (datetime.now(timezone.utc).timestamp() - last_ts) >= self.settings.refresh_interval_seconds
                        except ValueError:
                            should_refresh = True
                    if should_refresh:
                        await self.refresh()
                    if self.auto_mode_enabled:
                        await self.ensure_auto_connected()
            except Exception as exc:
                self.storage.append_log("background", f"Background loop error: {exc}", level="error")
            try:
                await asyncio.wait_for(self._stop_event.wait(), timeout=self.settings.heartbeat_interval_seconds)
            except asyncio.TimeoutError:
                continue

    async def _get_public_ip_cached(self, force: bool = False) -> str | None:
        value, cached_at = self._public_ip_cache
        now = datetime.now(timezone.utc).timestamp()
        if force or now - cached_at > 60:
            value = await fetch_public_ip()
            self._public_ip_cache = (value, now)
        return value

    def _normalise_countries(self, countries: list[str]) -> list[str]:
        result = []
        seen = set()
        for country in countries:
            code = country.strip().upper()
            if len(code) != 2 or code in seen:
                continue
            seen.add(code)
            result.append(code)
        return result or list(self.settings.auto_mode_default_countries)

    def _is_hysteria_mode(self) -> bool:
        return self.settings.runtime_mode == "hy2-native"

    def _ensure_hysteria_config_state(self) -> None:
        if self.storage.get_state("hysteria_config") is not None:
            return
        password = self.settings.hysteria_auth_password or str(uuid4())
        self.storage.put_state("hysteria_config", self.hysteria.default_payload(password).model_dump())

    def _get_hysteria_config(self) -> HysteriaConfigPayload:
        payload = self.storage.get_state("hysteria_config")
        if payload is None:
            self._ensure_hysteria_config_state()
            payload = self.storage.get_state("hysteria_config")
        return HysteriaConfigPayload.model_validate(payload)

    def _map_hysteria_state(self, service_state: str) -> str:
        if service_state == "active":
            return "connected"
        if service_state == "failed":
            return "failed"
        return "idle"
