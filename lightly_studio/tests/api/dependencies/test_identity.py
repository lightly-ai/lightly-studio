from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pytest_mock import MockerFixture
from sqlmodel import Session

from lightly_studio import deployment
from lightly_studio.api.dependencies import identity
from lightly_studio.api.dependencies.identity import IdentityDep
from lightly_studio.api.routes.api import exceptions
from lightly_studio.api.routes.api.status import HTTP_STATUS_OK, HTTP_STATUS_UNAUTHORIZED
from lightly_studio.database import db_manager


@pytest.fixture
def client(db_session: Session) -> TestClient:
    app = FastAPI()
    app.dependency_overrides[db_manager._session_dependency] = lambda: db_session
    exceptions.register_exception_handlers(app=app)

    @app.get("/identity")
    def _get_identity(user: IdentityDep) -> dict[str, str | None]:
        return {"email": user.email, "role": user.role.value}

    return TestClient(app)


def test_get_identity(client: TestClient, mocker: MockerFixture) -> None:
    mocker.patch.object(deployment, "is_enterprise", return_value=True)

    response = client.get(
        "/identity", headers={"X-User-Email": "ada@example.com", "X-User-Role": "labeler"}
    )

    assert response.status_code == HTTP_STATUS_OK
    assert response.json() == {"email": "ada@example.com", "role": "labeler"}


def test_get_identity__normalizes_role(client: TestClient, mocker: MockerFixture) -> None:
    mocker.patch.object(deployment, "is_enterprise", return_value=True)

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
    mocker.patch.object(deployment, "is_enterprise", return_value=True)

    response = client.get("/identity", headers=headers)

    assert response.status_code == HTTP_STATUS_UNAUTHORIZED


def test_get_identity__local(client: TestClient, mocker: MockerFixture) -> None:
    mocker.patch.object(deployment, "is_enterprise", return_value=False)

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
    db_session: Session, mocker: MockerFixture, x_user_email: str | None, x_user_role: str | None
) -> None:
    mocker.patch.object(deployment, "is_enterprise", return_value=False)

    with pytest.raises(RuntimeError, match="Authentication is not supported in a local run"):
        identity.get_identity(
            session=db_session, x_user_email=x_user_email, x_user_role=x_user_role
        )
