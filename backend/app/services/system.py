from __future__ import annotations

import os
from pathlib import Path

import httpx


def detect_environment() -> str:
    if os.getenv("WSL_DISTRO_NAME"):
        return "wsl"
    try:
        release = Path("/proc/sys/kernel/osrelease").read_text(encoding="utf-8").lower()
    except OSError:
        return "linux"
    return "wsl" if "microsoft" in release else "linux"


def detect_scope(environment: str) -> str:
    return "wsl" if environment == "wsl" else "system"


async def fetch_public_ip() -> str | None:
    try:
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            response = await client.get("https://api.ipify.org", params={"format": "json"})
            response.raise_for_status()
            return response.json().get("ip")
    except Exception:
        return None
