from app.models import IpQualityRecord, ServerRecord
from app.services.scoring import score_server, select_best_server


def make_server(hostname: str, ip: str, *, score: int, ping: int, speed: int, users: int, uptime: int):
    return ServerRecord(
        hostname=hostname,
        ip=ip,
        score=score,
        ping=ping,
        speed=speed,
        country_long="Japan",
        country_code="JP",
        num_vpn_sessions=10,
        uptime=uptime,
        total_users=users,
        total_traffic=999,
        log_type="2weeks",
        operator="tester",
        message="",
        openvpn_config_b64="ZmFrZS1jb25maWc=",
        supports_openvpn=True,
    )


def test_score_server_prefers_residential_nodes():
    server = make_server("home", "1.1.1.1", score=1000, ping=20, speed=400_000_000, users=200, uptime=7200)
    home_quality = IpQualityRecord(ip="1.1.1.1", quality_class="residential", is_datacenter=False, is_proxy=False, is_vpn=False)
    hosting_quality = IpQualityRecord(ip="1.1.1.1", quality_class="hosting", is_datacenter=True, is_proxy=True, is_vpn=True)

    assert score_server(server, home_quality) > score_server(server, hosting_quality)


def test_select_best_server_filters_unknown_and_country_mismatch():
    jp_server = make_server("jp-home", "1.1.1.1", score=1000, ping=20, speed=400_000_000, users=200, uptime=7200)
    us_server = make_server("us-home", "2.2.2.2", score=3000, ping=10, speed=900_000_000, users=600, uptime=9200)
    us_server.country_code = "US"
    qualities = {
        "1.1.1.1": IpQualityRecord(ip="1.1.1.1", quality_class="residential", is_datacenter=False, is_proxy=False, is_vpn=False),
        "2.2.2.2": IpQualityRecord(ip="2.2.2.2", quality_class="unknown", is_datacenter=False, is_proxy=False, is_vpn=False),
    }

    best = select_best_server([jp_server, us_server], qualities, ["JP"])

    assert best is not None
    assert best.ip == "1.1.1.1"
