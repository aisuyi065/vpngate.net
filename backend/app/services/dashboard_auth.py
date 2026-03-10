from __future__ import annotations

import hashlib
import hmac

from app.config import Settings

DASHBOARD_AUTH_COOKIE = "vpngate_dashboard_auth"


def dashboard_auth_enabled(settings: Settings) -> bool:
    return bool(settings.dashboard_password)


def verify_dashboard_password(candidate: str, settings: Settings) -> bool:
    expected = settings.dashboard_password
    if not expected:
        return True
    return hmac.compare_digest(candidate, expected)


def create_dashboard_session_token(settings: Settings) -> str:
    if not settings.dashboard_password:
        return ""
    secret = settings.dashboard_session_secret or settings.dashboard_password
    return hmac.new(
        secret.encode("utf-8"),
        settings.dashboard_password.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def verify_dashboard_session_token(token: str | None, settings: Settings) -> bool:
    if not dashboard_auth_enabled(settings):
        return True
    if not token:
        return False
    expected = create_dashboard_session_token(settings)
    return hmac.compare_digest(token, expected)
