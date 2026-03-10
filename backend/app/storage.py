from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from app.models import ConnectionLogEntry, IpQualityRecord, ServerRecord, utcnow_iso


class Storage:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def initialize(self) -> None:
        with self.connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS servers (
                    ip TEXT PRIMARY KEY,
                    hostname TEXT NOT NULL,
                    score INTEGER NOT NULL,
                    ping INTEGER NOT NULL,
                    speed INTEGER NOT NULL,
                    country_long TEXT NOT NULL,
                    country_code TEXT NOT NULL,
                    num_vpn_sessions INTEGER NOT NULL,
                    uptime INTEGER NOT NULL,
                    total_users INTEGER NOT NULL,
                    total_traffic INTEGER NOT NULL,
                    log_type TEXT NOT NULL,
                    operator TEXT NOT NULL,
                    message TEXT NOT NULL,
                    openvpn_config_b64 TEXT NOT NULL,
                    supports_softether INTEGER NOT NULL DEFAULT 0,
                    supports_l2tp INTEGER NOT NULL DEFAULT 0,
                    supports_openvpn INTEGER NOT NULL DEFAULT 0,
                    supports_sstp INTEGER NOT NULL DEFAULT 0,
                    openvpn_tcp_port INTEGER,
                    openvpn_udp_port INTEGER,
                    last_seen_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS ip_quality (
                    ip TEXT PRIMARY KEY,
                    provider TEXT NOT NULL,
                    quality_class TEXT NOT NULL,
                    isp TEXT,
                    organization TEXT,
                    company_type TEXT,
                    asn_type TEXT,
                    country_code TEXT,
                    is_datacenter INTEGER NOT NULL DEFAULT 0,
                    is_proxy INTEGER NOT NULL DEFAULT 0,
                    is_vpn INTEGER NOT NULL DEFAULT 0,
                    is_tor INTEGER NOT NULL DEFAULT 0,
                    raw_json TEXT,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS app_state (
                    key TEXT PRIMARY KEY,
                    value_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS connection_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TEXT NOT NULL,
                    server_ip TEXT,
                    level TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    message TEXT NOT NULL
                );
                """
            )

    def upsert_servers(self, servers: list[ServerRecord]) -> None:
        if not servers:
            return
        rows = []
        now = utcnow_iso()
        for server in servers:
            payload = server.model_copy(update={"updated_at": now})
            rows.append(
                (
                    payload.ip,
                    payload.hostname,
                    payload.score,
                    payload.ping,
                    payload.speed,
                    payload.country_long,
                    payload.country_code,
                    payload.num_vpn_sessions,
                    payload.uptime,
                    payload.total_users,
                    payload.total_traffic,
                    payload.log_type,
                    payload.operator,
                    payload.message,
                    payload.openvpn_config_b64,
                    int(payload.supports_softether),
                    int(payload.supports_l2tp),
                    int(payload.supports_openvpn),
                    int(payload.supports_sstp),
                    payload.openvpn_tcp_port,
                    payload.openvpn_udp_port,
                    payload.last_seen_at,
                    payload.updated_at,
                )
            )
        with self.connect() as conn:
            conn.executemany(
                """
                INSERT INTO servers (
                    ip, hostname, score, ping, speed, country_long, country_code,
                    num_vpn_sessions, uptime, total_users, total_traffic, log_type,
                    operator, message, openvpn_config_b64, supports_softether,
                    supports_l2tp, supports_openvpn, supports_sstp, openvpn_tcp_port,
                    openvpn_udp_port, last_seen_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(ip) DO UPDATE SET
                    hostname=excluded.hostname,
                    score=excluded.score,
                    ping=excluded.ping,
                    speed=excluded.speed,
                    country_long=excluded.country_long,
                    country_code=excluded.country_code,
                    num_vpn_sessions=excluded.num_vpn_sessions,
                    uptime=excluded.uptime,
                    total_users=excluded.total_users,
                    total_traffic=excluded.total_traffic,
                    log_type=excluded.log_type,
                    operator=excluded.operator,
                    message=excluded.message,
                    openvpn_config_b64=excluded.openvpn_config_b64,
                    supports_softether=excluded.supports_softether,
                    supports_l2tp=excluded.supports_l2tp,
                    supports_openvpn=excluded.supports_openvpn,
                    supports_sstp=excluded.supports_sstp,
                    openvpn_tcp_port=excluded.openvpn_tcp_port,
                    openvpn_udp_port=excluded.openvpn_udp_port,
                    last_seen_at=excluded.last_seen_at,
                    updated_at=excluded.updated_at
                """,
                rows,
            )

    def list_servers(self) -> list[ServerRecord]:
        with self.connect() as conn:
            rows = conn.execute("SELECT * FROM servers ORDER BY score DESC, ping ASC, total_users DESC").fetchall()
        return [self._server_from_row(row) for row in rows]

    def get_server(self, ip: str) -> ServerRecord | None:
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM servers WHERE ip = ?", (ip,)).fetchone()
        return self._server_from_row(row) if row else None

    def upsert_ip_qualities(self, records: list[IpQualityRecord]) -> None:
        if not records:
            return
        with self.connect() as conn:
            conn.executemany(
                """
                INSERT INTO ip_quality (
                    ip, provider, quality_class, isp, organization, company_type,
                    asn_type, country_code, is_datacenter, is_proxy, is_vpn,
                    is_tor, raw_json, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(ip) DO UPDATE SET
                    provider=excluded.provider,
                    quality_class=excluded.quality_class,
                    isp=excluded.isp,
                    organization=excluded.organization,
                    company_type=excluded.company_type,
                    asn_type=excluded.asn_type,
                    country_code=excluded.country_code,
                    is_datacenter=excluded.is_datacenter,
                    is_proxy=excluded.is_proxy,
                    is_vpn=excluded.is_vpn,
                    is_tor=excluded.is_tor,
                    raw_json=excluded.raw_json,
                    updated_at=excluded.updated_at
                """,
                [
                    (
                        record.ip,
                        record.provider,
                        record.quality_class,
                        record.isp,
                        record.organization,
                        record.company_type,
                        record.asn_type,
                        record.country_code,
                        int(record.is_datacenter),
                        int(record.is_proxy),
                        int(record.is_vpn),
                        int(record.is_tor),
                        json.dumps(record.raw or {}),
                        record.updated_at,
                    )
                    for record in records
                ],
            )

    def get_ip_qualities(self, ips: list[str] | None = None) -> dict[str, IpQualityRecord]:
        query = "SELECT * FROM ip_quality"
        params: tuple[Any, ...] = ()
        if ips:
            placeholders = ", ".join("?" for _ in ips)
            query += f" WHERE ip IN ({placeholders})"
            params = tuple(ips)
        with self.connect() as conn:
            rows = conn.execute(query, params).fetchall()
        return {row["ip"]: self._ip_quality_from_row(row) for row in rows}

    def put_state(self, key: str, value: Any) -> None:
        now = utcnow_iso()
        payload = json.dumps(value)
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO app_state (key, value_json, updated_at) VALUES (?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET value_json=excluded.value_json, updated_at=excluded.updated_at
                """,
                (key, payload, now),
            )

    def get_state(self, key: str, default: Any = None) -> Any:
        with self.connect() as conn:
            row = conn.execute("SELECT value_json FROM app_state WHERE key = ?", (key,)).fetchone()
        if not row:
            return default
        return json.loads(row["value_json"])

    def append_log(self, event_type: str, message: str, server_ip: str | None = None, level: str = "info") -> None:
        with self.connect() as conn:
            conn.execute(
                "INSERT INTO connection_logs (created_at, server_ip, level, event_type, message) VALUES (?, ?, ?, ?, ?)",
                (utcnow_iso(), server_ip, level, event_type, message),
            )

    def list_logs(self, server_ip: str | None = None, limit: int = 100) -> list[ConnectionLogEntry]:
        query = "SELECT * FROM connection_logs"
        params: tuple[Any, ...] = ()
        if server_ip:
            query += " WHERE server_ip = ?"
            params = (server_ip,)
        query += " ORDER BY id DESC LIMIT ?"
        params = (*params, limit)
        with self.connect() as conn:
            rows = conn.execute(query, params).fetchall()
        return [ConnectionLogEntry(**dict(row)) for row in rows]

    def _server_from_row(self, row: sqlite3.Row) -> ServerRecord:
        return ServerRecord(**dict(row))

    def _ip_quality_from_row(self, row: sqlite3.Row) -> IpQualityRecord:
        payload = dict(row)
        payload["raw"] = json.loads(payload.pop("raw_json") or "{}")
        return IpQualityRecord(**payload)
