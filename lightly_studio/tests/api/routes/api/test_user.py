from __future__ import annotations

from fastapi.testclient import TestClient
from pytest_mock import MockerFixture
from sqlmodel import Session

from lightly_studio import deployment
from lightly_studio.api.routes.api.status import HTTP_STATUS_OK
from lightly_studio.models.user import UserTable


def test_get_me(test_client: TestClient, db_session: Session, mocker: MockerFixture) -> None:
    mocker.patch.object(deployment, "is_enterprise", return_value=True)
    db_session.add(UserTable(id=7, email="Ada@Example.com", role="labeler", status="active"))
    db_session.commit()

    response = test_client.get(
        "/api/me", headers={"X-User-Email": "ada@example.com", "X-User-Role": "labeler"}
    )

    assert response.status_code == HTTP_STATUS_OK
    assert response.json() == {
        "id": 7,
        "email": "Ada@Example.com",
        "role": "labeler",
        "status": "active",
    }


def test_get_me__local(test_client: TestClient, mocker: MockerFixture) -> None:
    mocker.patch.object(deployment, "is_enterprise", return_value=False)

    response = test_client.get("/api/me")

    assert response.status_code == HTTP_STATUS_OK
    assert response.json() is None
