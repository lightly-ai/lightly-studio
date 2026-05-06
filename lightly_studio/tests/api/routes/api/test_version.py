"""Tests for the version API route."""

from fastapi.testclient import TestClient
from pytest_mock import MockerFixture

from lightly_studio.api.routes.api.status import HTTP_STATUS_OK
from lightly_studio.api.routes.api.version import RuntimeVersionInfo


def test_get_version(test_client: TestClient, mocker: MockerFixture) -> None:
    mocker.patch(
        "lightly_studio.api.routes.api.version._load_version_info_from_file",
        return_value=RuntimeVersionInfo(
            version="1.2.3",
            git_sha="abc1234",
            is_tagged_commit=True,
        ),
    )

    response = test_client.get("/api/version")

    assert response.status_code == HTTP_STATUS_OK
    assert response.json() == {
        "version": "1.2.3",
        "git_sha": "abc1234",
        "is_tagged_commit": True,
    }


def test_get_version_falls_back_to_not_available(
    test_client: TestClient, mocker: MockerFixture
) -> None:
    mocker.patch(
        "lightly_studio.api.routes.api.version._load_version_info_from_file", return_value=None
    )

    response = test_client.get("/api/version")

    assert response.status_code == HTTP_STATUS_OK
    assert response.json() == {
        "version": "version not available",
        "git_sha": "version not available",
        "is_tagged_commit": False,
    }
