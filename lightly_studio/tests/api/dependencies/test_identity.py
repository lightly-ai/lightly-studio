from __future__ import annotations

from typing import Annotated

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from pytest_mock import MockerFixture

from lightly_studio.api.dependencies import identity
from lightly_studio.api.dependencies.identity import Identity, IdentityDep, Role
from lightly_studio.api.routes.api import exceptions
from lightly_studio.api.routes.api.status import (
    HTTP_STATUS_FORBIDDEN,
    HTTP_STATUS_OK,
    HTTP_STATUS_UNAUTHORIZED,
)
from lightly_studio.dataset import env


@pytest.fixture
def client() -> TestClient:
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

    return TestClient(app)


def test_get_identity(client: TestClient, mocker: MockerFixture) -> None:
    mocker.patch.object(env, "LIGHTLY_STUDIO_DEPLOYMENT_MODE", "enterprise")

    response = client.get(
        "/identity", headers={"X-User-Email": "ada@example.com", "X-User-Role": "labeler"}
    )

    assert response.status_code == HTTP_STATUS_OK
    assert response.json() == {"email": "ada@example.com", "role": "labeler"}


def test_get_identity__normalizes_role(client: TestClient, mocker: MockerFixture) -> None:
    mocker.patch.object(env, "LIGHTLY_STUDIO_DEPLOYMENT_MODE", "enterprise")

    response = client.get(
        "/identity", headers={"X-User-Email": " ada@example.com ", "X-User-Role": " Editor "}
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
def test_get_identity__invalid_headers(
    client: TestClient, mocker: MockerFixture, headers: dict[str, str]
) -> None:
    mocker.patch.object(env, "LIGHTLY_STUDIO_DEPLOYMENT_MODE", "enterprise")

    response = client.get("/identity", headers=headers)

    assert response.status_code == HTTP_STATUS_UNAUTHORIZED


def test_get_identity__local(client: TestClient, mocker: MockerFixture) -> None:
    mocker.patch.object(env, "LIGHTLY_STUDIO_DEPLOYMENT_MODE", "local")

    response = client.get("/identity")

    assert response.status_code == HTTP_STATUS_OK
    assert response.json() == {"email": None, "role": "admin"}


@pytest.mark.parametrize(
    ("x_user_email", "x_user_role"),
    [
        ("ada@example.com", "viewer"),
        ("ada@example.com", None),
        (None, "viewer"),
    ],
)
def test_get_identity__local_with_headers(
    mocker: MockerFixture, x_user_email: str | None, x_user_role: str | None
) -> None:
    mocker.patch.object(env, "LIGHTLY_STUDIO_DEPLOYMENT_MODE", "local")

    with pytest.raises(RuntimeError, match="Authentication is not supported in a local run"):
        identity.get_identity(x_user_email=x_user_email, x_user_role=x_user_role)


@pytest.mark.parametrize(
    ("role", "expected_status"),
    [
        ("viewer", HTTP_STATUS_FORBIDDEN),
        ("labeler", HTTP_STATUS_FORBIDDEN),
        ("editor", HTTP_STATUS_OK),
        ("admin", HTTP_STATUS_OK),
    ],
)
def test_require_role(
    client: TestClient, mocker: MockerFixture, role: str, expected_status: int
) -> None:
    mocker.patch.object(env, "LIGHTLY_STUDIO_DEPLOYMENT_MODE", "enterprise")

    response = client.get(
        "/editor", headers={"X-User-Email": "ada@example.com", "X-User-Role": role}
    )

    assert response.status_code == expected_status


def test_require_role__without_identity(client: TestClient, mocker: MockerFixture) -> None:
    mocker.patch.object(env, "LIGHTLY_STUDIO_DEPLOYMENT_MODE", "enterprise")

    response = client.get("/editor")

    assert response.status_code == HTTP_STATUS_UNAUTHORIZED


def test_require_role__local(client: TestClient, mocker: MockerFixture) -> None:
    mocker.patch.object(env, "LIGHTLY_STUDIO_DEPLOYMENT_MODE", "local")

    response = client.get("/editor")

    assert response.status_code == HTTP_STATUS_OK


def test_role_rank() -> None:
    ranks = [
        identity._ROLE_RANK[role] for role in (Role.VIEWER, Role.LABELER, Role.EDITOR, Role.ADMIN)
    ]

    assert ranks == sorted(set(ranks))
