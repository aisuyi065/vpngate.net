from app.config import Settings
from app.models import HysteriaConfigPayload
from app.services.hysteria import Hy2ServiceManager, build_client_config, render_hysteria_config


def test_render_hysteria_config_self_signed():
    settings = Settings()
    payload = Hy2ServiceManager(settings).default_payload("secret-pass")

    rendered = render_hysteria_config(payload)

    assert "listen: :8443" in rendered
    assert "tls:" in rendered
    assert "cert: /etc/hysteria/server.crt" in rendered
    assert "key: /etc/hysteria/server.key" in rendered
    assert "password: secret-pass" in rendered
    assert "url: https://bing.com" in rendered
    assert "initStreamReceiveWindow: 26843545" in rendered
    assert "maxStreamReceiveWindow: 26843545" in rendered
    assert "initConnReceiveWindow: 67108864" in rendered
    assert "maxConnReceiveWindow: 67108864" in rendered
    assert "acme:" not in rendered


def test_render_hysteria_config_acme():
    payload = HysteriaConfigPayload(
        listen_host="0.0.0.0",
        listen_port=443,
        tls_mode="acme",
        auth_password="secret-pass",
        masquerade_url="https://bing.com",
        domain="vpn.example.com",
        acme_email="ops@example.com",
        client_sni="vpn.example.com",
        client_insecure=False,
    )

    rendered = render_hysteria_config(payload)

    assert "listen: :443" in rendered
    assert "acme:" in rendered
    assert "- vpn.example.com" in rendered
    assert "email: ops@example.com" in rendered
    assert "tls:" not in rendered


def test_build_client_config_generates_uri_and_json():
    settings = Settings()
    payload = Hy2ServiceManager(settings).default_payload("secret-pass")

    client = build_client_config(payload, server_host="gateway.example.com")

    assert client.server == "gateway.example.com:8443"
    assert client.auth == "secret-pass"
    assert client.tls["sni"] == "bing.com"
    assert client.tls["insecure"] is True
    assert client.uri.startswith("hysteria2://secret-pass@gateway.example.com:8443/")
    assert "sni=bing.com" in client.uri
    assert "insecure=1" in client.uri
