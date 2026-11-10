"""Tests for the FastAPI app factory."""

from __future__ import annotations

from fastapi import APIRouter, FastAPI
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

from lightly_studio.api import app as app_module
from lightly_studio.api.routes.api.status import HTTP_STATUS_OK


def test_create_app__serves_extra_router_before_webapp_catch_all() -> None:
    app = app_module.create_app(routers=[_extra_router()])

    response = TestClient(app).get("/api/extra/ping")
    assert response.status_code == HTTP_STATUS_OK
    assert response.json() == {"status": "ok"}
    assert _route_paths(app).index("/api/extra/ping") < _route_paths(app).index("/{path:path}")


def test_create_app__repeated_calls_do_not_duplicate_routes() -> None:
    first = app_module.create_app(routers=[_extra_router()])
    second = app_module.create_app(routers=[_extra_router()])
    plain = app_module.create_app()

    assert _route_paths(first) == _route_paths(second)
    assert _route_paths(first).count("/api/extra/ping") == 1
    assert _route_paths(plain) == _route_paths(app_module.app)


def _extra_router() -> APIRouter:
    router = APIRouter(prefix="/extra", tags=["extra"])

    @router.get("/ping")
    def ping() -> dict[str, str]:
        return {"status": "ok"}

    return router


def _route_paths(app: FastAPI) -> list[str]:
    return [route.path for route in app.routes if isinstance(route, APIRoute)]
