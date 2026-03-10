from __future__ import annotations

import base64
import csv
import io
import re
from urllib.parse import parse_qs, urlparse

import httpx
from bs4 import BeautifulSoup

from app.models import ServerRecord, SiteServerMetadata, utcnow_iso

API_URL = "http://www.vpngate.net/api/iphone/"
SITES_URL = "https://www.vpngate.net/cn/"
IP_PATTERN = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")


def _safe_int(value: str) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return 0


def parse_vpngate_csv(text: str) -> list[ServerRecord]:
    lines = [line for line in text.splitlines() if line.strip()]
    filtered: list[str] = []
    for line in lines:
        if line.startswith("*vpn_servers"):
            continue
        if line.startswith("#"):
            filtered.append(line.lstrip("#"))
            continue
        filtered.append(line)
    reader = csv.DictReader(io.StringIO("\n".join(filtered)))
    servers: list[ServerRecord] = []
    timestamp = utcnow_iso()
    for row in reader:
        if not row or not row.get("IP"):
            continue
        servers.append(
            ServerRecord(
                hostname=(row.get("HostName") or row["IP"]).strip(),
                ip=row["IP"].strip(),
                score=_safe_int(row.get("Score")),
                ping=_safe_int(row.get("Ping")),
                speed=_safe_int(row.get("Speed")),
                country_long=(row.get("CountryLong") or "Unknown").strip(),
                country_code=(row.get("CountryShort") or "--").strip().upper(),
                num_vpn_sessions=_safe_int(row.get("NumVpnSessions")),
                uptime=_safe_int(row.get("Uptime")),
                total_users=_safe_int(row.get("TotalUsers")),
                total_traffic=_safe_int(row.get("TotalTraffic")),
                log_type=(row.get("LogType") or "").strip(),
                operator=(row.get("Operator") or "").strip(),
                message=(row.get("Message") or "").strip(),
                openvpn_config_b64=(row.get("OpenVPN_ConfigData_Base64") or "").strip(),
                supports_openvpn=True,
                last_seen_at=timestamp,
                updated_at=timestamp,
            )
        )
    return servers


def parse_sites_html(html: str) -> list[SiteServerMetadata]:
    soup = BeautifulSoup(html, "html.parser")
    selected_table = None
    for table in soup.find_all("table"):
        headers = " ".join(cell.get_text(" ", strip=True) for cell in table.select("td.vg_table_header"))
        if "OpenVPN" in headers and "MS-SSTP" in headers:
            selected_table = table
            break
    if selected_table is None:
        return []

    details: list[SiteServerMetadata] = []
    for row in selected_table.find_all("tr"):
        cells = row.find_all("td", recursive=False)
        if len(cells) < 8:
            continue
        server_cell = cells[1]
        openvpn_cell = cells[6]
        ip_match = IP_PATTERN.search(server_cell.get_text(" ", strip=True))
        if not ip_match:
            continue
        hostname = server_cell.find("b")
        openvpn_link = openvpn_cell.find("a", href=lambda href: bool(href and "do_openvpn.aspx" in href))
        query = parse_qs(urlparse(openvpn_link["href"]).query) if openvpn_link else {}
        details.append(
            SiteServerMetadata(
                hostname=(hostname.get_text(" ", strip=True) if hostname else ip_match.group(0)),
                ip=ip_match.group(0),
                supports_softether="yes_33" in str(cells[4]) or "SSL-VPN" in cells[4].get_text(" ", strip=True),
                supports_l2tp="yes_33" in str(cells[5]) or "L2TP" in cells[5].get_text(" ", strip=True),
                supports_openvpn=bool(openvpn_link),
                supports_sstp="yes_33" in str(cells[7]) or "SSTP" in cells[7].get_text(" ", strip=True),
                openvpn_tcp_port=_safe_int(query.get("tcp", [0])[0]) or None,
                openvpn_udp_port=_safe_int(query.get("udp", [0])[0]) or None,
            )
        )
    return details


def merge_server_sources(csv_servers: list[ServerRecord], html_details: list[SiteServerMetadata]) -> list[ServerRecord]:
    detail_by_ip = {detail.ip: detail for detail in html_details}
    merged: list[ServerRecord] = []
    for server in csv_servers:
        detail = detail_by_ip.get(server.ip)
        if detail:
            merged.append(
                server.model_copy(
                    update={
                        "supports_softether": detail.supports_softether,
                        "supports_l2tp": detail.supports_l2tp,
                        "supports_openvpn": detail.supports_openvpn,
                        "supports_sstp": detail.supports_sstp,
                        "openvpn_tcp_port": detail.openvpn_tcp_port,
                        "openvpn_udp_port": detail.openvpn_udp_port,
                    }
                )
            )
        else:
            merged.append(server)
    return merged


async def fetch_server_catalog() -> list[ServerRecord]:
    timeout = httpx.Timeout(30.0)
    headers = {"User-Agent": "VPNGateController/0.1"}
    async with httpx.AsyncClient(timeout=timeout, headers=headers, follow_redirects=True) as client:
        import asyncio

        csv_response, html_response = await asyncio.gather(
            client.get(API_URL),
            client.get(SITES_URL),
        )
        csv_response.raise_for_status()
        html_response.raise_for_status()
    csv_servers = parse_vpngate_csv(csv_response.text)
    html_details = parse_sites_html(html_response.text)
    return merge_server_sources(csv_servers, html_details)


def decode_openvpn_config(server: ServerRecord) -> str:
    decoded = base64.b64decode(server.openvpn_config_b64).decode("utf-8", "replace")
    required_lines = [
        "auth-nocache",
        "persist-key",
        "persist-tun",
        "remote-cert-tls server",
        "data-ciphers AES-256-GCM:AES-128-GCM:CHACHA20-POLY1305:AES-128-CBC",
        "data-ciphers-fallback AES-128-CBC",
    ]
    output = decoded
    if "redirect-gateway" not in decoded and "route-nopull" not in decoded:
        output += "\nredirect-gateway def1\n"
    for line in required_lines:
        if line not in output:
            output += f"\n{line}\n"
    return output.strip() + "\n"
