from __future__ import annotations

from pathlib import Path
from secrets import token_hex

from fastapi import FastAPI, HTTPException, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.responses import FileResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles

from app.config import Settings, settings
from app.controller import VpnGateController
from app.models import AutoModePayload, DashboardAuthStatus, DashboardLoginPayload, HysteriaConfigPayload, ServerFilters
from app.services.dashboard_auth import (
    DASHBOARD_AUTH_COOKIE,
    create_dashboard_session_token,
    dashboard_auth_enabled,
    verify_dashboard_password,
    verify_dashboard_session_token,
)


class AppControllerAdapter:
    def __init__(self, controller: VpnGateController) -> None:
        self.controller = controller

    async def start(self) -> None:
        await self.controller.start()

    async def stop(self) -> None:
        await self.controller.stop()

    def _serialize_status(self, status):
        payload = status.model_dump()
        payload["traffic_scope"] = payload.pop("current_scope")
        payload["warning"] = payload.pop("note")
        payload.setdefault("connected_server_country", None)
        payload.setdefault("last_refresh_at", None)
        return payload

    async def list_servers(self, filters: ServerFilters):
        items = []
        for item in await self.controller.list_servers(filters):
            payload = item.model_dump()
            payload["server_id"] = payload["ip"]
            items.append(payload)
        return items

    async def get_status(self):
        return self._serialize_status(await self.controller.get_status())

    async def refresh(self):
        payload = (await self.controller.refresh()).model_dump()
        payload["timestamp"] = payload.pop("updated_at")
        return payload

    async def connect(self, server_id: str):
        return self._serialize_status(await self.controller.connect(server_id))

    async def disconnect(self):
        return self._serialize_status(await self.controller.disconnect())

    async def update_auto_mode(self, enabled: bool, countries: list[str]):
        return self._serialize_status(await self.controller.update_auto_mode(enabled, countries))

    async def list_logs(self, server_id: str | None = None):
        return await self.controller.list_logs(server_id)

    async def get_hysteria_status(self):
        return (await self.controller.get_hysteria_status()).model_dump()

    async def get_hysteria_client_config(self):
        return (await self.controller.get_hysteria_client_config()).model_dump()

    async def apply_hysteria_config(self, payload: HysteriaConfigPayload):
        return (await self.controller.apply_hysteria_config(payload)).model_dump()

    async def restart_hysteria(self):
        return (await self.controller.restart_hysteria()).model_dump()

    async def list_hysteria_logs(self, limit: int = 100):
        return await self.controller.list_hysteria_logs(limit)


def create_app(controller: object | None = None, app_settings: Settings | None = None) -> FastAPI:
    resolved_settings = app_settings or settings
    adapter = controller if controller is not None else AppControllerAdapter(VpnGateController(resolved_settings))
    app = FastAPI(title="VPNGate Controller", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.state.controller = adapter
    app.state.settings = resolved_settings

    def persist_dashboard_auth_state(password: str, session_secret: str) -> None:
        root_controller = getattr(app.state.controller, "controller", app.state.controller)
        storage = getattr(root_controller, "storage", None)
        if storage is None:
            return
        storage.put_state("dashboard_password", password)
        storage.put_state("dashboard_session_secret", session_secret)

    @app.middleware("http")
    async def dashboard_auth_middleware(request: Request, call_next):
        current_settings = app.state.settings
        path = request.url.path
        if not dashboard_auth_enabled(current_settings):
            return await call_next(request)
        if path == "/health" or path.startswith("/assets"):
            return await call_next(request)
        if path in {"/api/auth/login", "/api/auth/status"}:
            return await call_next(request)
        if path.startswith("/api/"):
            token = request.cookies.get(DASHBOARD_AUTH_COOKIE)
            if not verify_dashboard_session_token(token, current_settings):
                return JSONResponse({"detail": "Authentication required"}, status_code=401)
        return await call_next(request)

    @app.on_event("startup")
    async def startup() -> None:
        start = getattr(app.state.controller, "start", None)
        if start:
            await start()

    @app.on_event("shutdown")
    async def shutdown() -> None:
        stop = getattr(app.state.controller, "stop", None)
        if stop:
            await stop()

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/status")
    async def status():
        return await app.state.controller.get_status()

    @app.get("/api/auth/status")
    async def auth_status(request: Request):
        current_settings = app.state.settings
        authenticated = verify_dashboard_session_token(
            request.cookies.get(DASHBOARD_AUTH_COOKIE),
            current_settings,
        )
        return DashboardAuthStatus(
            enabled=dashboard_auth_enabled(current_settings),
            authenticated=authenticated,
        )

    @app.post("/api/auth/login")
    async def auth_login(payload: DashboardLoginPayload, response: Response):
        current_settings = app.state.settings
        if not dashboard_auth_enabled(current_settings):
            return DashboardAuthStatus(enabled=False, authenticated=True)
        if not verify_dashboard_password(payload.password, current_settings):
            raise HTTPException(status_code=401, detail="Invalid dashboard password")
        response.set_cookie(
            key=DASHBOARD_AUTH_COOKIE,
            value=create_dashboard_session_token(current_settings),
            httponly=True,
            samesite="lax",
            secure=False,
            max_age=7 * 24 * 3600,
        )
        return DashboardAuthStatus(enabled=True, authenticated=True)

    @app.post("/api/auth/logout")
    async def auth_logout(response: Response):
        response.delete_cookie(DASHBOARD_AUTH_COOKIE)
        return DashboardAuthStatus(
            enabled=dashboard_auth_enabled(app.state.settings),
            authenticated=False,
        )

    @app.post("/api/auth/password")
    async def auth_change_password(payload: DashboardLoginPayload, response: Response):
        current_settings = app.state.settings
        password = payload.password.strip()
        if not password:
            raise HTTPException(status_code=400, detail="Dashboard password cannot be empty")
        current_settings.dashboard_password = password
        current_settings.dashboard_session_secret = token_hex(32)
        persist_dashboard_auth_state(password, current_settings.dashboard_session_secret)
        response.set_cookie(
            key=DASHBOARD_AUTH_COOKIE,
            value=create_dashboard_session_token(current_settings),
            httponly=True,
            samesite="lax",
            secure=False,
            max_age=7 * 24 * 3600,
        )
        return DashboardAuthStatus(enabled=True, authenticated=True)

    @app.get("/api/servers")
    async def servers(
        country: str | None = Query(default=None),
        protocol: str | None = Query(default=None),
        residential: bool | None = Query(default=None),
    ):
        filters = ServerFilters(country=country, protocol=protocol, residential=residential)
        items = await app.state.controller.list_servers(filters)
        return {"items": items, "total": len(items)}

    @app.post("/api/refresh")
    async def refresh():
        return await app.state.controller.refresh()

    @app.post("/api/connect/{server_id}")
    async def connect(server_id: str):
        try:
            return await app.state.controller.connect(server_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except RuntimeError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/api/disconnect")
    async def disconnect():
        return await app.state.controller.disconnect()

    @app.post("/api/auto-mode")
    async def auto_mode(payload: AutoModePayload):
        return await app.state.controller.update_auto_mode(payload.enabled, payload.allowed_countries)

    @app.get("/api/logs")
    async def logs(server_id: str | None = Query(default=None)):
        return {"items": await app.state.controller.list_logs(server_id)}

    @app.get("/api/hysteria/status")
    async def hysteria_status():
        return await app.state.controller.get_hysteria_status()

    @app.get("/api/hysteria/client-config")
    async def hysteria_client_config():
        return await app.state.controller.get_hysteria_client_config()

    @app.post("/api/hysteria/apply")
    async def hysteria_apply(payload: HysteriaConfigPayload):
        return await app.state.controller.apply_hysteria_config(payload)

    @app.post("/api/hysteria/restart")
    async def hysteria_restart():
        return await app.state.controller.restart_hysteria()

    @app.get("/api/hysteria/logs")
    async def hysteria_logs(limit: int = Query(default=100, ge=1, le=500)):
        return {"items": await app.state.controller.list_hysteria_logs(limit)}

    frontend_dist = Path(__file__).resolve().parents[2] / "frontend" / "dist"
    if (frontend_dist / "assets").exists():
        app.mount("/assets", StaticFiles(directory=frontend_dist / "assets"), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    async def spa(path: str):
        if path.startswith("api") or path == "health":
            raise HTTPException(status_code=404, detail="Not found")
        index = frontend_dist / "index.html"
        if index.exists():
            return FileResponse(index)
        return PlainTextResponse("Frontend build not found. Run the frontend build first.", status_code=404)

    return app


app = create_app()
