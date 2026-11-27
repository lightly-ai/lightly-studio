"""Tests for the FastAPI app factory."""

from __future__ import annotations

from fastapi import APIRouter, FastAPI
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

from lightly_studio.api import app as app_module
from lightly_studio.api.dependencies import identity
from lightly_studio.api.dependencies.identity import Identity, IdentityDep, Role
from lightly_studio.api.replaceable import Replaceable
from lightly_studio.api.routes.api.status import HTTP_STATUS_OK

_ADA = Identity(email="ada@example.com", role=Role.VIEWER)


def test_create_app__serves_extra_router_before_webapp_catch_all() -> None:
    app = app_module.create_app(routers=[_extra_router()])

    response = TestClient(app).get("/api/extra/ping")
    assert response.status_code == HTTP_STATUS_OK
    assert response.json() == {"status": "ok"}
    assert _route_paths(app=app).index("/api/extra/ping") < _route_paths(app=app).index(
        "/{path:path}"
    )


def test_create_app__extra_router_keeps_operation_ids() -> None:
    app = app_module.create_app(routers=[_extra_router()])

    paths = app.openapi()["paths"]
    assert paths["/api/extra/ping"]["get"]["operationId"] == "extra_ping"
    assert paths["/api/version"]["get"]["operationId"] == "get_version"


def test_create_app__repeated_calls_do_not_duplicate_routes() -> None:
    first = app_module.create_app(routers=[_extra_router()])
    second = app_module.create_app(routers=[_extra_router()])
    plain = app_module.create_app()

    assert _route_paths(app=first) == _route_paths(app=second)
    assert _route_paths(app=first).count("/api/extra/ping") == 1
    assert _route_paths(app=plain) == _route_paths(app=app_module.app)


def test_create_app__replace() -> None:
    app = app_module.create_app(
        routers=[_identity_router()], replace=Replaceable(get_identity=_get_ada)
    )

    response = TestClient(app).get("/api/whoami")
    assert response.json() == {"email": "ada@example.com", "role": "viewer"}
    assert app.dependency_overrides == {identity.get_identity: _get_ada}


def test_create_app__replace_with_default() -> None:
    app = app_module.create_app(replace=Replaceable(get_identity=identity.get_identity))

    assert app.dependency_overrides == {}


def test_create_app__replace_per_app() -> None:
    replaced = app_module.create_app(
        routers=[_identity_router()], replace=Replaceable(get_identity=_get_ada)
    )
    plain = app_module.create_app(routers=[_identity_router()])

    assert TestClient(replaced).get("/api/whoami").json() == {
        "email": "ada@example.com",
        "role": "viewer",
    }
    assert TestClient(plain).get("/api/whoami").json() == {"email": None, "role": "admin"}
    assert plain.dependency_overrides == {}


def _extra_router() -> APIRouter:
    router = APIRouter(prefix="/extra", tags=["extra"])

    @router.get("/ping", operation_id="extra_ping")
    def ping() -> dict[str, str]:
        return {"status": "ok"}

    return router


def _route_paths(app: FastAPI) -> list[str]:
    return [route.path for route in app.routes if isinstance(route, APIRoute)]


def _identity_router() -> APIRouter:
    router = APIRouter()

    @router.get("/whoami")
    def whoami(user: IdentityDep) -> dict[str, str | None]:
        return {"email": user.email, "role": user.role.value}

    return router


def _get_ada() -> Identity:
    return _ADA
