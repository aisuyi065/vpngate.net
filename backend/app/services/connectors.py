from __future__ import annotations

import asyncio
import shutil
import subprocess
import time
from collections import deque
from pathlib import Path

from app.config import Settings
from app.models import ConnectionStatus, ServerRecord, utcnow_iso
from app.services.system import detect_environment, detect_scope
from app.services.vpngate import decode_openvpn_config


class BaseConnector:
    async def connect(self, server: ServerRecord) -> ConnectionStatus:
        raise NotImplementedError

    async def disconnect(self) -> ConnectionStatus:
        raise NotImplementedError

    async def get_status(self) -> ConnectionStatus:
        raise NotImplementedError

    async def read_logs(self, limit: int = 200) -> list[str]:
        raise NotImplementedError

    async def health_check(self) -> tuple[bool, str | None]:
        raise NotImplementedError


class MockConnector(BaseConnector):
    def __init__(self) -> None:
        self.environment = detect_environment()
        self.current_server: ServerRecord | None = None
        self.state = "idle"
        self.last_error: str | None = None

    async def connect(self, server: ServerRecord) -> ConnectionStatus:
        self.current_server = server
        self.state = "connected"
        self.last_error = None
        return await self.get_status()

    async def disconnect(self) -> ConnectionStatus:
        self.current_server = None
        self.state = "idle"
        return await self.get_status()

    async def get_status(self) -> ConnectionStatus:
        return ConnectionStatus(
            state=self.state,
            mode="mock",
            environment=self.environment,
            current_scope=detect_scope(self.environment),
            connected_server_ip=self.current_server.ip if self.current_server else None,
            connected_server_hostname=self.current_server.hostname if self.current_server else None,
            note="WSL traffic only" if self.environment == "wsl" else "System traffic managed by this node",
            last_error=self.last_error,
            updated_at=utcnow_iso(),
        )

    async def read_logs(self, limit: int = 200) -> list[str]:
        return ["mock connector active"]

    async def health_check(self) -> tuple[bool, str | None]:
        if self.current_server is None:
            return False, "not connected"
        return self.state == "connected", None if self.state == "connected" else "mock connector is not connected"


class OpenVpnConnector(BaseConnector):
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.environment = detect_environment()
        self._state = "idle"
        self._last_error: str | None = None
        self._current_server: ServerRecord | None = None
        self._process: subprocess.Popen[bytes] | None = None
        self._lock = asyncio.Lock()
        self._log_lines: deque[str] = deque(maxlen=400)
        self.config_path = settings.openvpn_dir / "current.ovpn"
        self.log_path = settings.openvpn_dir / "openvpn.log"
        self.status_path = settings.openvpn_dir / "openvpn.status"
        self.pid_path = settings.openvpn_dir / "openvpn.pid"

    async def connect(self, server: ServerRecord) -> ConnectionStatus:
        async with self._lock:
            return await asyncio.to_thread(self._connect_sync, server)

    async def disconnect(self) -> ConnectionStatus:
        async with self._lock:
            return await asyncio.to_thread(self._disconnect_sync)

    async def get_status(self) -> ConnectionStatus:
        if self._process and self._process.poll() is not None and self._state == "connected":
            self._state = "failed"
            self._last_error = f"OpenVPN exited with code {self._process.returncode}"
        return ConnectionStatus(
            state=self._state,
            mode="openvpn",
            environment=self.environment,
            current_scope=detect_scope(self.environment),
            connected_server_ip=self._current_server.ip if self._current_server else None,
            connected_server_hostname=self._current_server.hostname if self._current_server else None,
            note="WSL traffic only" if self.environment == "wsl" else "System traffic managed by this node",
            last_error=self._last_error,
            updated_at=utcnow_iso(),
        )

    async def read_logs(self, limit: int = 200) -> list[str]:
        if self.log_path.exists():
            lines = self.log_path.read_text(encoding="utf-8", errors="replace").splitlines()
            return lines[-limit:]
        return list(self._log_lines)[-limit:]

    async def health_check(self) -> tuple[bool, str | None]:
        return await asyncio.to_thread(self._health_check_sync)

    def _connect_sync(self, server: ServerRecord) -> ConnectionStatus:
        if not shutil.which("openvpn"):
            self._state = "failed"
            self._last_error = "openvpn binary not found"
            raise RuntimeError(self._last_error)

        self._disconnect_sync()
        self._state = "connecting"
        self._current_server = server
        self._last_error = None
        self.config_path.write_text(decode_openvpn_config(server), encoding="utf-8")
        if self.log_path.exists():
            self.log_path.unlink()
        command = [
            "openvpn",
            "--config",
            str(self.config_path),
            "--status",
            str(self.status_path),
            "5",
            "--writepid",
            str(self.pid_path),
            "--log-append",
            str(self.log_path),
        ]
        self._process = subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
        deadline = time.time() + self.settings.connect_timeout_seconds
        while time.time() < deadline:
            if self._process.poll() is not None:
                self._state = "failed"
                self._last_error = f"OpenVPN exited with code {self._process.returncode}"
                raise RuntimeError(self._last_error)
            if self.log_path.exists():
                lines = self.log_path.read_text(encoding="utf-8", errors="replace").splitlines()
                if lines:
                    self._log_lines.extend(lines[-20:])
                if any("Initialization Sequence Completed" in line for line in lines[-20:]):
                    self._state = "connected"
                    return ConnectionStatus(
                        state="connected",
                        mode="openvpn",
                        environment=self.environment,
                        current_scope=detect_scope(self.environment),
                        connected_server_ip=server.ip,
                        connected_server_hostname=server.hostname,
                        note="WSL traffic only" if self.environment == "wsl" else "System traffic managed by this node",
                        updated_at=utcnow_iso(),
                    )
            time.sleep(1)
        self._disconnect_sync()
        self._state = "failed"
        self._last_error = "Timed out waiting for OpenVPN connection"
        raise RuntimeError(self._last_error)

    def _disconnect_sync(self) -> ConnectionStatus:
        if self._process and self._process.poll() is None:
            self._process.terminate()
            try:
                self._process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self._process.kill()
                self._process.wait(timeout=5)
        self._process = None
        self._current_server = None
        self._state = "idle"
        return ConnectionStatus(
            state="idle",
            mode="openvpn",
            environment=self.environment,
            current_scope=detect_scope(self.environment),
            note="WSL traffic only" if self.environment == "wsl" else "System traffic managed by this node",
            last_error=self._last_error,
            updated_at=utcnow_iso(),
        )

    def _health_check_sync(self) -> tuple[bool, str | None]:
        if self._current_server is None or self._state != "connected":
            return False, "not connected"
        if self._process is None:
            return False, "openvpn process missing"
        if self._process.poll() is not None:
            self._state = "failed"
            self._last_error = f"OpenVPN exited with code {self._process.returncode}"
            return False, self._last_error
        if not self.status_path.exists():
            return False, "status file missing"
        age = time.time() - self.status_path.stat().st_mtime
        if age > self.settings.tunnel_health_stale_seconds:
            return False, "status file stale"
        content = self.status_path.read_text(encoding="utf-8", errors="replace")
        if "CONNECTED,SUCCESS" not in content:
            return False, "openvpn status is not connected"
        return True, None


def build_connector(settings: Settings) -> BaseConnector:
    if settings.connector_mode == "mock":
        return MockConnector()
    return OpenVpnConnector(settings)
