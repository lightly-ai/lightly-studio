from __future__ import annotations

from typing import Annotated

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from lightly_studio.api.dependencies import identity
from lightly_studio.api.dependencies.identity import Identity, IdentityDep, Role
from lightly_studio.api.routes.api import exceptions
from lightly_studio.api.routes.api.status import (
    HTTP_STATUS_FORBIDDEN,
    HTTP_STATUS_INTERNAL_SERVER_ERROR,
    HTTP_STATUS_OK,
    HTTP_STATUS_UNAUTHORIZED,
)


@pytest.fixture
def app() -> FastAPI:
    app = FastAPI()
    exceptions.register_exception_handlers(app=app)

    @app.get("/identity")
    def _get_identity(user: IdentityDep) -> dict[str, str | None]:
        return {"email": user.email, "role": user.role.value}

    @app.get("/editor")
    def _get_editor(
        user: Annotated[Identity, Depends(identity.require_role(min_role=Role.EDITOR))],
    ) -> dict[str, str | None]:
        return {"email": user.email, "role": user.role.value}

    return app


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def proxy_client(app: FastAPI) -> TestClient:
    app.dependency_overrides[identity.get_identity] = identity.get_proxy_identity
    return TestClient(app, raise_server_exceptions=False)


def test_get_identity(client: TestClient) -> None:
    response = client.get("/identity")

    assert response.status_code == HTTP_STATUS_OK
    assert response.json() == {"email": None, "role": "admin"}


@pytest.mark.parametrize(
    "headers",
    [
        {"X-User-Email": "ada@example.com", "X-User-Role": "viewer"},
        {"X-User-Email": "ada@example.com"},
        {"X-User-Role": "viewer"},
        {"X-User-Email": ""},
    ],
)
def test_get_identity__with_headers(client: TestClient, headers: dict[str, str]) -> None:
    response = client.get("/identity", headers=headers)

    assert response.status_code == HTTP_STATUS_INTERNAL_SERVER_ERROR


def test_get_identity__override(app: FastAPI, client: TestClient) -> None:
    app.dependency_overrides[identity.get_identity] = lambda: Identity(
        email="ada@example.com", role=Role.VIEWER
    )

    response = client.get("/identity", headers={"X-User-Email": "ignored@example.com"})

    assert response.status_code == HTTP_STATUS_OK
    assert response.json() == {"email": "ada@example.com", "role": "viewer"}


def test_get_proxy_identity(proxy_client: TestClient) -> None:
    response = proxy_client.get(
        "/identity", headers={"X-User-Email": "ada@example.com", "X-User-Role": "labeler"}
    )

    assert response.status_code == HTTP_STATUS_OK
    assert response.json() == {"email": "ada@example.com", "role": "labeler"}


def test_get_proxy_identity__normalizes(proxy_client: TestClient) -> None:
    response = proxy_client.get(
        "/identity", headers={"X-User-Email": " Ada@Example.com ", "X-User-Role": " Editor "}
    )

    assert response.status_code == HTTP_STATUS_OK
    assert response.json() == {"email": "ada@example.com", "role": "editor"}


@pytest.mark.parametrize(
    "headers",
    [
        {},
        {"X-User-Email": "ada@example.com"},
        {"X-User-Role": "admin"},
        {"X-User-Email": "  ", "X-User-Role": "admin"},
        {"X-User-Email": "ada@example.com", "X-User-Role": "owner"},
    ],
)
def test_get_proxy_identity__invalid_headers(
    proxy_client: TestClient, headers: dict[str, str]
) -> None:
    response = proxy_client.get("/identity", headers=headers)

    assert response.status_code == HTTP_STATUS_UNAUTHORIZED


@pytest.mark.parametrize(
    "headers",
    [
        [
            ("X-User-Email", "ada@example.com"),
            ("X-User-Email", "eve@example.com"),
            ("X-User-Role", "viewer"),
        ],
        [
            ("X-User-Email", "ada@example.com"),
            ("X-User-Role", "admin"),
            ("X-User-Role", "viewer"),
        ],
    ],
)
def test_get_proxy_identity__repeated_header(
    proxy_client: TestClient, headers: list[tuple[str, str]]
) -> None:
    response = proxy_client.get("/identity", headers=headers)

    assert response.status_code == HTTP_STATUS_UNAUTHORIZED


def test_get_proxy_identity__logs_unauthenticated_request(
    proxy_client: TestClient, caplog: pytest.LogCaptureFixture
) -> None:
    response = proxy_client.get(
        "/identity", headers={"X-User-Email": "ada@example.com", "X-User-Role": "owner"}
    )

    assert response.status_code == HTTP_STATUS_UNAUTHORIZED
    assert response.json() == {"error": "The request has no valid user identity."}
    assert "The X-User-Role header has an unknown role: 'owner'." in caplog.text


@pytest.mark.parametrize(
    ("role", "expected_status"),
    [
        ("viewer", HTTP_STATUS_FORBIDDEN),
        ("labeler", HTTP_STATUS_FORBIDDEN),
        ("editor", HTTP_STATUS_OK),
        ("admin", HTTP_STATUS_OK),
    ],
)
def test_require_role(proxy_client: TestClient, role: str, expected_status: int) -> None:
    response = proxy_client.get(
        "/editor", headers={"X-User-Email": "ada@example.com", "X-User-Role": role}
    )

    assert response.status_code == expected_status


def test_require_role__without_identity(proxy_client: TestClient) -> None:
    response = proxy_client.get("/editor")

    assert response.status_code == HTTP_STATUS_UNAUTHORIZED


def test_require_role__local(client: TestClient) -> None:
    response = client.get("/editor")

    assert response.status_code == HTTP_STATUS_OK


def test_role_rank() -> None:
    ranks = [
        identity._ROLE_RANK[role] for role in (Role.VIEWER, Role.LABELER, Role.EDITOR, Role.ADMIN)
    ]

    assert ranks == sorted(set(ranks))
