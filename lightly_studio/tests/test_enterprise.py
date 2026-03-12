"""Tests for the enterprise remote connection module."""

from __future__ import annotations

import pytest
import requests
from pytest_mock import MockerFixture, MockType

from lightly_studio import db_manager, enterprise


@pytest.fixture(autouse=True)
def _patch_env_vars(mocker: MockerFixture) -> None:
    """Clear enterprise env vars so tests are not affected by local config."""
    mocker.patch.object(enterprise, "LIGHTLY_STUDIO_API_URL", None)
    mocker.patch.object(enterprise, "LIGHTLY_STUDIO_TOKEN", None)


@pytest.fixture
def patch_db_connect(mocker: MockerFixture) -> MockType:
    return mocker.patch.object(db_manager, "connect")


def test_connect__success(mocker: MockerFixture, patch_db_connect: MockType) -> None:
    mock_response = mocker.MagicMock()
    mock_response.status_code = 200
    mock_response.ok = True
    mock_response.json.return_value = {
        "engine_url": "postgresql://lightly:secret@10.0.0.5:5433/lightly_studio"
    }
    mock_get = mocker.patch.object(requests, "get", return_value=mock_response)
    # mock_connect = mocker.patch.object(db_manager, "connect")

    enterprise.connect(api_url="http://10.0.0.5:8100", token="token")

    mock_get.assert_called_once_with(
        url="http://10.0.0.5:8100/auth/api/v1/db-connect-engine-url",
        headers={"Authorization": "Bearer token"},
        timeout=10,
    )
    patch_db_connect.assert_called_once_with(
        engine_url="postgresql://lightly:secret@10.0.0.5:5433/lightly_studio"
    )


def test_connect__success_env_vars(
    mocker: MockerFixture,
    patch_db_connect: None,  # noqa: ARG001
) -> None:
    mocker.patch.object(enterprise, "LIGHTLY_STUDIO_API_URL", "http://10.0.0.5:8100")
    mocker.patch.object(enterprise, "LIGHTLY_STUDIO_TOKEN", "token")

    mock_response = mocker.MagicMock()
    mock_response.status_code = 200
    mock_response.ok = True
    mock_response.json.return_value = {"engine_url": "postgresql://lightly:secret@10.0.0.5:5433/lightly_studio"}
    mock_get = mocker.patch.object(requests, "get", return_value=mock_response)

    enterprise.connect()

    mock_get.assert_called_once_with(
        url="http://10.0.0.5:8100/auth/api/v1/db-connect-engine-url",
        headers={"Authorization": "Bearer token"},
        timeout=10,
    )


def test_connect__strips_trailing_slash(
    mocker: MockerFixture,
    patch_db_connect: MockType,  # noqa: ARG001
) -> None:
    mock_response = mocker.MagicMock()
    mock_response.status_code = 200
    mock_response.ok = True
    mock_response.json.return_value = {"engine_url": "postgresql://lightly:secret@10.0.0.5:5433/lightly_studio"}
    mock_get = mocker.patch.object(requests, "get", return_value=mock_response)

    enterprise.connect(api_url="http://10.0.0.5:8100/", token="tok")

    mock_get.assert_called_once_with(
        url="http://10.0.0.5:8100/auth/api/v1/db-connect-engine-url",
        headers={"Authorization": "Bearer tok"},
        timeout=10,
    )


def test_connect__explicit_params_over_env(
    mocker: MockerFixture,
    patch_db_connect: None,  # noqa: ARG001
) -> None:
    """Test that explicit parameters take precedence over env vars."""
    mocker.patch.object(enterprise, "LIGHTLY_STUDIO_API_URL", "http://10.0.0.5:8100")
    mocker.patch.object(enterprise, "LIGHTLY_STUDIO_TOKEN", "token")

    mock_response = mocker.MagicMock()
    mock_response.status_code = 200
    mock_response.ok = True
    mock_response.json.return_value = {"engine_url": "postgresql://lightly:secret@10.0.0.5:5433/lightly_studio"}
    mock_get = mocker.patch.object(requests, "get", return_value=mock_response)

    enterprise.connect(api_url="http://10.0.0.6:8100", token="explicit-token")

    mock_get.assert_called_once_with(
        url="http://10.0.0.6:8100/auth/api/v1/db-connect-engine-url",
        headers={"Authorization": "Bearer explicit-token"},
        timeout=10,
    )


def test_connect__missing_api_url_raises() -> None:
    with pytest.raises(ValueError, match="api_url is required"):
        enterprise.connect(api_url=None, token="some-token")


def test_connect__missing_token_raises() -> None:
    with pytest.raises(ValueError, match="token is required"):
        enterprise.connect(api_url="http://host:8100", token=None)


def test_connect__token_expired_401(mocker: MockerFixture, patch_db_connect: MockType) -> None:
    mock_response = mocker.MagicMock()
    mock_response.status_code = 401
    mocker.patch.object(requests, "get", return_value=mock_response)

    with pytest.raises(PermissionError, match="token may have expired"):
        enterprise.connect(api_url="http://host:8100", token="expired-token")

    patch_db_connect.assert_not_called()


def test_connect__not_admin_403(mocker: MockerFixture, patch_db_connect: MockType) -> None:
    mock_response = mocker.MagicMock()
    mock_response.status_code = 403
    mocker.patch.object(requests, "get", return_value=mock_response)

    with pytest.raises(PermissionError, match="admin role required"):
        enterprise.connect(api_url="http://host:8100", token="editor-token")

    patch_db_connect.assert_not_called()


def test_connect__server_not_configured_503(
    mocker: MockerFixture, patch_db_connect: MockType
) -> None:
    mock_response = mocker.MagicMock()
    mock_response.status_code = 503
    mocker.patch.object(requests, "get", return_value=mock_response)

    with pytest.raises(RuntimeError, match="not configured for remote connections"):
        enterprise.connect(api_url="http://host:8100", token="tok")

    patch_db_connect.assert_not_called()


def test_connect__connection_error(mocker: MockerFixture, patch_db_connect: MockType) -> None:
    mocker.patch.object(requests, "get", side_effect=requests.ConnectionError("refused"))

    with pytest.raises(ConnectionError, match="Could not reach LightlyStudio"):
        enterprise.connect(api_url="http://unreachable:8100", token="tok")

    patch_db_connect.assert_not_called()
