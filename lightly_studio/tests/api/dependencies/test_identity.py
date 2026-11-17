from __future__ import annotations

from typing import Annotated

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from pytest_mock import MockerFixture
from sqlmodel import Session

from lightly_studio import deployment
from lightly_studio.api.dependencies import identity
from lightly_studio.api.dependencies.identity import Identity, IdentityDep
from lightly_studio.api.routes.api import exceptions
from lightly_studio.api.routes.api.status import (
    HTTP_STATUS_FORBIDDEN,
    HTTP_STATUS_INTERNAL_SERVER_ERROR,
    HTTP_STATUS_OK,
    HTTP_STATUS_UNAUTHORIZED,
)
from lightly_studio.database import db_manager
from lightly_studio.models.user import Role, UserTable


@pytest.fixture
def client(db_session: Session) -> TestClient:
    app = FastAPI()
    app.dependency_overrides[db_manager._session_dependency] = lambda: db_session
    exceptions.register_exception_handlers(app=app)

    @app.get("/identity")
    def _get_identity(user: IdentityDep) -> dict[str, str | int | None]:
        return {"email": user.email, "role": user.role.value, "user_id": user.user_id}

    @app.get("/editor")
    def _get_editor(
        user: Annotated[Identity, Depends(identity.require_role(min_role=Role.EDITOR))],
    ) -> dict[str, str | None]:
        return {"email": user.email, "role": user.role.value}

    return TestClient(app, raise_server_exceptions=False)


def test_get_identity(client: TestClient, db_session: Session, mocker: MockerFixture) -> None:
    mocker.patch.object(deployment, "is_enterprise", return_value=True)
    _add_user(session=db_session, user_id=7, email="ada@example.com", role="labeler")

    # The role comes from auth.users, not from the header.
    response = client.get(
        "/identity", headers={"X-User-Email": "ada@example.com", "X-User-Role": "admin"}
    )

    assert response.status_code == HTTP_STATUS_OK
    assert response.json() == {"email": "ada@example.com", "role": "labeler", "user_id": 7}


def test_get_identity__normalizes(
    client: TestClient, db_session: Session, mocker: MockerFixture
) -> None:
    mocker.patch.object(deployment, "is_enterprise", return_value=True)
    _add_user(session=db_session, user_id=7, email="Ada@Example.com", role="editor")

    response = client.get(
        "/identity", headers={"X-User-Email": " ADA@example.COM ", "X-User-Role": "editor"}
    )

    assert response.status_code == HTTP_STATUS_OK
    assert response.json() == {"email": "ada@example.com", "role": "editor", "user_id": 7}


@pytest.mark.parametrize(
    "headers",
    [
        {},
        {"X-User-Email": "ada@example.com"},
        {"X-User-Role": "admin"},
        {"X-User-Email": "  ", "X-User-Role": "admin"},
        {"X-User-Email": "ada@example.com", "X-User-Role": "  "},
    ],
)
def test_get_identity__invalid_headers(
    client: TestClient, db_session: Session, mocker: MockerFixture, headers: dict[str, str]
) -> None:
    mocker.patch.object(deployment, "is_enterprise", return_value=True)
    _add_user(session=db_session, user_id=7, email="ada@example.com", role="admin")

    response = client.get("/identity", headers=headers)

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
def test_get_identity__repeated_header(
    client: TestClient,
    db_session: Session,
    mocker: MockerFixture,
    headers: list[tuple[str, str]],
) -> None:
    mocker.patch.object(deployment, "is_enterprise", return_value=True)
    _add_user(session=db_session, user_id=7, email="ada@example.com", role="admin")
    _add_user(session=db_session, user_id=8, email="eve@example.com", role="admin")

    response = client.get("/identity", headers=headers)

    assert response.status_code == HTTP_STATUS_UNAUTHORIZED


@pytest.mark.parametrize("status", ["pending", "inactive"])
def test_get_identity__user_not_active(
    client: TestClient, db_session: Session, mocker: MockerFixture, status: str
) -> None:
    mocker.patch.object(deployment, "is_enterprise", return_value=True)
    _add_user(session=db_session, user_id=7, email="ada@example.com", role="admin", status=status)

    response = client.get(
        "/identity", headers={"X-User-Email": "ada@example.com", "X-User-Role": "admin"}
    )

    assert response.status_code == HTTP_STATUS_UNAUTHORIZED


def test_get_identity__logs_unauthenticated_request(
    client: TestClient, db_session: Session, mocker: MockerFixture, caplog: pytest.LogCaptureFixture
) -> None:
    mocker.patch.object(deployment, "is_enterprise", return_value=True)
    _add_user(session=db_session, user_id=7, email="ada@example.com", role="admin")

    response = client.get(
        "/identity", headers={"X-User-Email": "eve@example.com", "X-User-Role": "admin"}
    )

    assert response.status_code == HTTP_STATUS_UNAUTHORIZED
    assert response.json() == {"error": "The request has no valid user identity."}
    assert "No user has the email 'eve@example.com'." in caplog.text


def test_get_identity__local(client: TestClient, mocker: MockerFixture) -> None:
    mocker.patch.object(deployment, "is_enterprise", return_value=False)

    response = client.get("/identity")

    assert response.status_code == HTTP_STATUS_OK
    assert response.json() == {"email": None, "role": "admin", "user_id": None}


@pytest.mark.parametrize(
    "headers",
    [
        {"X-User-Email": "ada@example.com", "X-User-Role": "viewer"},
        {"X-User-Email": "ada@example.com"},
        {"X-User-Role": "viewer"},
        {"X-User-Email": ""},
    ],
)
def test_get_identity__local_with_headers(
    client: TestClient, mocker: MockerFixture, headers: dict[str, str]
) -> None:
    mocker.patch.object(deployment, "is_enterprise", return_value=False)

    response = client.get("/identity", headers=headers)

    assert response.status_code == HTTP_STATUS_INTERNAL_SERVER_ERROR


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
    client: TestClient,
    db_session: Session,
    mocker: MockerFixture,
    role: str,
    expected_status: int,
) -> None:
    mocker.patch.object(deployment, "is_enterprise", return_value=True)
    _add_user(session=db_session, user_id=7, email="ada@example.com", role=role)

    response = client.get(
        "/editor", headers={"X-User-Email": "ada@example.com", "X-User-Role": role}
    )

    assert response.status_code == expected_status


def test_require_role__without_identity(client: TestClient, mocker: MockerFixture) -> None:
    mocker.patch.object(deployment, "is_enterprise", return_value=True)

    response = client.get("/editor")

    assert response.status_code == HTTP_STATUS_UNAUTHORIZED


def test_require_role__local(client: TestClient, mocker: MockerFixture) -> None:
    mocker.patch.object(deployment, "is_enterprise", return_value=False)

    response = client.get("/editor")

    assert response.status_code == HTTP_STATUS_OK


def test_role_rank() -> None:
    ranks = [
        identity._ROLE_RANK[role] for role in (Role.VIEWER, Role.LABELER, Role.EDITOR, Role.ADMIN)
    ]

    assert ranks == sorted(set(ranks))


def _add_user(
    session: Session, user_id: int, email: str, role: str, status: str = "active"
) -> None:
    """Adds a user to the stand-in of `auth.users`. In production, the auth service adds it."""
    session.add(UserTable(id=user_id, email=email, role=role, status=status))
    session.commit()
