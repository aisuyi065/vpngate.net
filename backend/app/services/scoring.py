from __future__ import annotations

from app.models import IpQualityRecord, ServerRecord


def score_server(server: ServerRecord, quality: IpQualityRecord | None) -> float:
    quality = quality or IpQualityRecord(ip=server.ip)
    total = 0.0

    if quality.quality_class == "residential":
        total += 1200
    elif quality.quality_class == "hosting":
        total -= 900
    else:
        total -= 250

    total += min(500, server.score / 5000)
    total += min(250, max(0, 250 - server.ping))
    total += min(400, server.speed / 10_000_000)
    total += min(250, server.uptime / 3600)
    total += min(150, server.total_users / 1000)

    if quality.is_datacenter:
        total -= 500
    if quality.is_proxy:
        total -= 300
    if quality.is_vpn:
        total -= 250
    if quality.is_tor:
        total -= 250

    return round(total, 2)


def select_best_server(
    servers: list[ServerRecord],
    qualities: dict[str, IpQualityRecord],
    allowed_countries: list[str],
) -> ServerRecord | None:
    candidates = rank_candidate_servers(servers, qualities, allowed_countries)
    return candidates[0] if candidates else None


def rank_candidate_servers(
    servers: list[ServerRecord],
    qualities: dict[str, IpQualityRecord],
    allowed_countries: list[str],
    exclude_ips: set[str] | None = None,
) -> list[ServerRecord]:
    allowed = {country.upper() for country in allowed_countries if country.strip()}
    excluded = exclude_ips or set()
    candidates: list[tuple[float, ServerRecord]] = []
    for server in servers:
        if server.ip in excluded:
            continue
        if not server.supports_openvpn:
            continue
        if allowed and server.country_code.upper() not in allowed:
            continue
        quality = qualities.get(server.ip)
        if not quality or quality.quality_class != "residential":
            continue
        candidates.append((score_server(server, quality), server))
    candidates.sort(key=lambda item: item[0], reverse=True)
    return [server for _, server in candidates]
