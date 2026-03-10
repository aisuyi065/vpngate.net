from app.controller import VpnGateController
from app.models import ConnectionStatus, IpQualityRecord, ServerRecord
from app.storage import Storage


class FailoverConnector:
    def __init__(self, *, initially_connected_ip: str | None = None, healthy: bool = True, failing_ips: set[str] | None = None):
        self.connected_ip = initially_connected_ip
        self.healthy = healthy
        self.failing_ips = failing_ips or set()
        self.connect_attempts: list[str] = []
        self.disconnect_calls = 0

    async def connect(self, server: ServerRecord) -> ConnectionStatus:
        self.connect_attempts.append(server.ip)
        if server.ip in self.failing_ips:
            raise RuntimeError(f"simulated connect failure for {server.ip}")
        self.connected_ip = server.ip
        self.healthy = True
        return await self.get_status()

    async def disconnect(self) -> ConnectionStatus:
        self.disconnect_calls += 1
        self.connected_ip = None
        return await self.get_status()

    async def get_status(self) -> ConnectionStatus:
        return ConnectionStatus(
            state="connected" if self.connected_ip else "idle",
            mode="mock",
            environment="linux",
            current_scope="system",
            connected_server_ip=self.connected_ip,
            connected_server_hostname=self.connected_ip,
            note=None,
            last_error=None,
        )

    async def read_logs(self, limit: int = 200) -> list[str]:
        return []

    async def health_check(self) -> tuple[bool, str | None]:
        if not self.connected_ip:
            return False, "not connected"
        if self.healthy:
            return True, None
        return False, "status file stale"


def make_server(ip: str, country: str = "JP", score: int = 1000) -> ServerRecord:
    return ServerRecord(
        hostname=f"server-{ip}",
        ip=ip,
        score=score,
        ping=10,
        speed=500_000_000,
        country_long="Japan",
        country_code=country,
        num_vpn_sessions=10,
        uptime=7200,
        total_users=100,
        total_traffic=1000,
        log_type="2weeks",
        operator="tester",
        message="",
        openvpn_config_b64="ZmFrZS1jb25maWc=",
        supports_openvpn=True,
    )


async def test_auto_connect_fails_over_when_current_tunnel_is_unhealthy(tmp_path):
    controller = VpnGateController(
        connector=FailoverConnector(initially_connected_ip="1.1.1.1", healthy=False),
    )
    controller.storage = Storage(tmp_path / "controller.sqlite3")
    controller.storage.initialize()
    controller.allowed_countries = ["JP"]

    servers = [make_server("1.1.1.1", score=900), make_server("2.2.2.2", score=1500)]
    controller.storage.upsert_servers(servers)
    controller.storage.upsert_ip_qualities([
        IpQualityRecord(ip="1.1.1.1", quality_class="residential"),
        IpQualityRecord(ip="2.2.2.2", quality_class="residential"),
    ])

    status = await controller.ensure_auto_connected()

    assert controller.connector.disconnect_calls == 1
    assert controller.connector.connect_attempts == ["2.2.2.2"]
    assert status.connected_server_ip == "2.2.2.2"


async def test_auto_connect_tries_next_candidate_when_first_connection_fails(tmp_path):
    controller = VpnGateController(
        connector=FailoverConnector(failing_ips={"2.2.2.2"}),
    )
    controller.storage = Storage(tmp_path / "controller.sqlite3")
    controller.storage.initialize()
    controller.allowed_countries = ["JP"]

    servers = [make_server("2.2.2.2", score=1500), make_server("3.3.3.3", score=1400)]
    controller.storage.upsert_servers(servers)
    controller.storage.upsert_ip_qualities([
        IpQualityRecord(ip="2.2.2.2", quality_class="residential"),
        IpQualityRecord(ip="3.3.3.3", quality_class="residential"),
    ])

    status = await controller.ensure_auto_connected()

    assert controller.connector.connect_attempts == ["2.2.2.2", "3.3.3.3"]
    assert status.connected_server_ip == "3.3.3.3"
