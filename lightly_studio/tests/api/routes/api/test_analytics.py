"""Tests for the analytics API route."""

from uuid import UUID

from fastapi.testclient import TestClient
from pytest_mock import MockerFixture

from lightly_studio.analytics import install_id
from lightly_studio.api.routes.api.status import HTTP_STATUS_OK

INSTALL_ID = UUID("0199f1a2-b775-76b8-9b09-c2fd260c67c1")


def test_get_install_id(test_client: TestClient, mocker: MockerFixture) -> None:
    mocker.patch.object(install_id, "get_install_id", return_value=INSTALL_ID)

    response = test_client.get("/api/install_id")

    assert response.status_code == HTTP_STATUS_OK
    assert response.json() == {"install_id": str(INSTALL_ID)}
