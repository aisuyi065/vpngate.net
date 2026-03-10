from fastapi.testclient import TestClient

from app.main import create_app
from app.models import ConnectionStatus, HysteriaClientConfig, HysteriaConfigPayload, HysteriaStatus, IpQualityRecord, ServerRecord


class FakeController:
    def __init__(self):
        self.server = ServerRecord(
            hostname="public-vpn-1",
            ip="1.2.3.4",
            score=100,
            ping=15,
            speed=2000000,
            country_long="Japan",
            country_code="JP",
            num_vpn_sessions=12,
            uptime=3600,
            total_users=500,
            total_traffic=1111,
            log_type="2weeks",
            operator="tester",
            message="",
            openvpn_config_b64="ZmFrZS1jb25maWc=",
            supports_openvpn=True,
            supports_l2tp=True,
            supports_softether=True,
            supports_sstp=True,
        )
        self.quality = IpQualityRecord(ip="1.2.3.4", quality_class="residential", is_datacenter=False, is_proxy=False, is_vpn=False)
        self.status = ConnectionStatus(mode="mock", environment="wsl", auto_mode_enabled=True)
        self.hysteria_status = HysteriaStatus(
            runtime_mode="hy2-native",
            installed=True,
            service_name="hysteria-server.service",
            service_state="active",
            enabled=True,
            listen_host="0.0.0.0",
            listen_port=8443,
            tls_mode="self_signed",
            masquerade_url="https://bing.com",
            config_path="/etc/hysteria/config.yaml",
        )
        self.hysteria_config = HysteriaConfigPayload(
            listen_host="0.0.0.0",
            listen_port=8443,
            tls_mode="self_signed",
            auth_password="secret-pass",
            masquerade_url="https://bing.com",
            cert_path="/etc/hysteria/server.crt",
            key_path="/etc/hysteria/server.key",
            client_sni="bing.com",
            client_insecure=True,
        )

    async def list_servers(self, filters):
        return [{
            **self.server.model_dump(),
            "ip_quality": self.quality.model_dump(),
            "quality_score": 88.0,
            "is_connected": False,
        }]

    async def get_status(self):
        return self.status

    async def refresh(self):
        return {"servers": 1, "refreshed": True}

    async def connect(self, server_id: str):
        self.status = self.status.model_copy(update={"connected_server_ip": "1.2.3.4", "state": "connected"})
        return self.status

    async def disconnect(self):
        self.status = self.status.model_copy(update={"connected_server_ip": None, "state": "idle"})
        return self.status

    async def update_auto_mode(self, enabled: bool, countries: list[str]):
        self.status = self.status.model_copy(update={"auto_mode_enabled": enabled, "allowed_countries": countries})
        return self.status

    async def list_logs(self, server_id=None):
        return []

    async def get_hysteria_status(self):
        return self.hysteria_status

    async def get_hysteria_client_config(self):
        return HysteriaClientConfig(
            server="gateway.example.com:8443",
            auth="secret-pass",
            tls={"sni": "bing.com", "insecure": True},
            uri="hysteria2://secret-pass@gateway.example.com:8443/?sni=bing.com&insecure=1#VPNGate-Hysteria2",
        )

    async def apply_hysteria_config(self, payload: HysteriaConfigPayload):
        self.hysteria_config = payload
        self.hysteria_status = self.hysteria_status.model_copy(
            update={
                "listen_host": payload.listen_host,
                "listen_port": payload.listen_port,
                "tls_mode": payload.tls_mode,
                "masquerade_url": payload.masquerade_url,
            }
        )
        return self.hysteria_status

    async def restart_hysteria(self):
        return self.hysteria_status

    async def list_hysteria_logs(self, limit: int = 100):
        return ["hysteria log line"]


def test_servers_endpoint_returns_quality_and_protocol_metadata():
    app = create_app(controller=FakeController())
    client = TestClient(app)

    response = client.get("/api/servers")

    assert response.status_code == 200
    payload = response.json()
    assert len(payload["items"]) == 1
    item = payload["items"][0]
    assert item["supports_openvpn"] is True
    assert item["supports_l2tp"] is True
    assert item["ip_quality"]["quality_class"] == "residential"


def test_auto_mode_endpoint_persists_country_selection():
    app = create_app(controller=FakeController())
    client = TestClient(app)

    response = client.post("/api/auto-mode", json={"enabled": True, "allowed_countries": ["JP", "KR"]})

    assert response.status_code == 200
    payload = response.json()
    assert payload["auto_mode_enabled"] is True
    assert payload["allowed_countries"] == ["JP", "KR"]


def test_connect_endpoint_returns_updated_status():
    app = create_app(controller=FakeController())
    client = TestClient(app)

    response = client.post("/api/connect/1.2.3.4")

    assert response.status_code == 200
    payload = response.json()
    assert payload["state"] == "connected"
    assert payload["connected_server_ip"] == "1.2.3.4"


def test_hysteria_status_endpoint_returns_service_metadata():
    app = create_app(controller=FakeController())
    client = TestClient(app)

    response = client.get("/api/hysteria/status")

    assert response.status_code == 200
    payload = response.json()
    assert payload["runtime_mode"] == "hy2-native"
    assert payload["service_name"] == "hysteria-server.service"
    assert payload["service_state"] == "active"
    assert payload["listen_port"] == 8443


def test_hysteria_apply_endpoint_updates_server_settings():
    app = create_app(controller=FakeController())
    client = TestClient(app)

    response = client.post(
        "/api/hysteria/apply",
        json={
            "listen_host": "0.0.0.0",
            "listen_port": 9443,
            "tls_mode": "self_signed",
            "auth_password": "new-secret",
            "masquerade_url": "https://example.org",
            "cert_path": "/etc/hysteria/server.crt",
            "key_path": "/etc/hysteria/server.key",
            "client_sni": "edge.example.org",
            "client_insecure": True,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["listen_port"] == 9443
    assert payload["masquerade_url"] == "https://example.org"


def test_hysteria_client_config_endpoint_returns_uri():
    app = create_app(controller=FakeController())
    client = TestClient(app)

    response = client.get("/api/hysteria/client-config")

    assert response.status_code == 200
    payload = response.json()
    assert payload["server"] == "gateway.example.com:8443"
    assert payload["tls"]["sni"] == "bing.com"
    assert payload["uri"].startswith("hysteria2://")
