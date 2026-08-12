"""Tests for the enterprise remote connection module."""

from __future__ import annotations

import json
import os

import fsspec
import pytest
import requests
from gcsfs import GCSFileSystem  # type: ignore[import-untyped]
from pytest_mock import MockerFixture, MockType

from lightly_studio import enterprise
from lightly_studio.database import db_manager


@pytest.fixture(autouse=True)
def _patch_env_vars(mocker: MockerFixture) -> None:
    """Clear enterprise env vars so tests are not affected by local config."""
    mocker.patch.dict(os.environ, {}, clear=True)
    mocker.patch.object(enterprise, "LIGHTLY_STUDIO_API_URL", None)
    mocker.patch.object(enterprise, "LIGHTLY_STUDIO_TOKEN", None)
    mocker.patch.object(enterprise, "LIGHTLY_STUDIO_API_KEY", None)


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

    enterprise.connect(api_url="http://10.0.0.5:8100", token="token")

    mock_get.assert_called_once_with(
        url="http://10.0.0.5:8100/auth/api/v1/enterprise-connect",
        headers={"Authorization": "Bearer token"},
        timeout=10,
    )
    patch_db_connect.assert_called_once_with(
        db_url="postgresql://lightly:secret@10.0.0.5:5433/lightly_studio"
    )


def test_connect__success_api_key(mocker: MockerFixture, patch_db_connect: MockType) -> None:
    mock_response = mocker.MagicMock()
    mock_response.status_code = 200
    mock_response.ok = True
    mock_response.json.return_value = {
        "engine_url": "postgresql://lightly:secret@10.0.0.5:5433/lightly_studio"
    }
    mock_post = mocker.patch.object(requests, "post", return_value=mock_response)

    enterprise.connect(api_url="http://10.0.0.5:8100", api_key="ls_testkey")

    mock_post.assert_called_once_with(
        url="http://10.0.0.5:8100/auth/api/v1/api-key-login",
        json={"api_key": "ls_testkey"},
        timeout=10,
    )
    patch_db_connect.assert_called_once_with(
        db_url="postgresql://lightly:secret@10.0.0.5:5433/lightly_studio"
    )


def test_connect__success_api_key_env_var(
    mocker: MockerFixture,
    patch_db_connect: MockType,  # noqa: ARG001
) -> None:
    mocker.patch.object(enterprise, "LIGHTLY_STUDIO_API_URL", "http://10.0.0.5:8100")
    mocker.patch.object(enterprise, "LIGHTLY_STUDIO_API_KEY", "ls_envkey")

    mock_response = mocker.MagicMock()
    mock_response.status_code = 200
    mock_response.ok = True
    mock_response.json.return_value = {
        "engine_url": "postgresql://lightly:secret@10.0.0.5:5433/lightly_studio"
    }
    mock_post = mocker.patch.object(requests, "post", return_value=mock_response)

    enterprise.connect()

    mock_post.assert_called_once_with(
        url="http://10.0.0.5:8100/auth/api/v1/api-key-login",
        json={"api_key": "ls_envkey"},
        timeout=10,
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
    mock_response.json.return_value = {
        "engine_url": "postgresql://lightly:secret@10.0.0.5:5433/lightly_studio"
    }
    mock_get = mocker.patch.object(requests, "get", return_value=mock_response)

    enterprise.connect()

    mock_get.assert_called_once_with(
        url="http://10.0.0.5:8100/auth/api/v1/enterprise-connect",
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
    mock_response.json.return_value = {
        "engine_url": "postgresql://lightly:secret@10.0.0.5:5433/lightly_studio"
    }
    mock_get = mocker.patch.object(requests, "get", return_value=mock_response)

    enterprise.connect(api_url="http://10.0.0.5:8100/", token="tok")

    mock_get.assert_called_once_with(
        url="http://10.0.0.5:8100/auth/api/v1/enterprise-connect",
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
    mock_response.json.return_value = {
        "engine_url": "postgresql://lightly:secret@10.0.0.5:5433/lightly_studio"
    }
    mock_get = mocker.patch.object(requests, "get", return_value=mock_response)

    enterprise.connect(api_url="http://10.0.0.6:8100", token="explicit-token")

    mock_get.assert_called_once_with(
        url="http://10.0.0.6:8100/auth/api/v1/enterprise-connect",
        headers={"Authorization": "Bearer explicit-token"},
        timeout=10,
    )


def test_connect__explicit_api_key_over_env_token(
    mocker: MockerFixture,
    patch_db_connect: None,  # noqa: ARG001
) -> None:
    mocker.patch.object(enterprise, "LIGHTLY_STUDIO_TOKEN", "env-token")
    mock_response = mocker.MagicMock(status_code=200, ok=True)
    mock_response.json.return_value = {
        "engine_url": "postgresql://lightly:secret@10.0.0.5:5433/lightly_studio"
    }
    mock_post = mocker.patch.object(requests, "post", return_value=mock_response)

    enterprise.connect(api_url="http://10.0.0.5:8100", api_key="ls_explicit")

    mock_post.assert_called_once_with(
        url="http://10.0.0.5:8100/auth/api/v1/api-key-login",
        json={"api_key": "ls_explicit"},
        timeout=10,
    )


def test_connect__explicit_token_over_env_api_key(
    mocker: MockerFixture,
    patch_db_connect: None,  # noqa: ARG001
) -> None:
    mocker.patch.object(enterprise, "LIGHTLY_STUDIO_API_KEY", "ls_env")
    mock_response = mocker.MagicMock(status_code=200, ok=True)
    mock_response.json.return_value = {
        "engine_url": "postgresql://lightly:secret@10.0.0.5:5433/lightly_studio"
    }
    mock_get = mocker.patch.object(requests, "get", return_value=mock_response)

    enterprise.connect(api_url="http://10.0.0.5:8100", token="explicit-token")

    mock_get.assert_called_once_with(
        url="http://10.0.0.5:8100/auth/api/v1/enterprise-connect",
        headers={"Authorization": "Bearer explicit-token"},
        timeout=10,
    )


def test_connect__missing_api_url_raises() -> None:
    with pytest.raises(ValueError, match="api_url is required"):
        enterprise.connect(api_url=None, token="some-token")


def test_connect__missing_token_and_api_key_raises() -> None:
    with pytest.raises(ValueError, match="Exactly one of token or api_key must be provided"):
        enterprise.connect(api_url="http://host:8100", token=None, api_key=None)


def test_connect__both_token_and_api_key_raises() -> None:
    with pytest.raises(ValueError, match="Exactly one of token or api_key must be provided"):
        enterprise.connect(api_url="http://host:8100", token="token", api_key="ls_key")


def test_connect__token_expired_401(mocker: MockerFixture, patch_db_connect: MockType) -> None:
    mock_response = mocker.MagicMock()
    mock_response.status_code = 401
    mocker.patch.object(requests, "get", return_value=mock_response)

    with pytest.raises(PermissionError, match="token may have expired"):
        enterprise.connect(api_url="http://host:8100", token="expired-token")

    patch_db_connect.assert_not_called()


def test_connect__api_key_invalid_401(mocker: MockerFixture, patch_db_connect: MockType) -> None:
    mock_response = mocker.MagicMock()
    mock_response.status_code = 401
    mocker.patch.object(requests, "post", return_value=mock_response)

    with pytest.raises(PermissionError, match="invalid or expired API key"):
        enterprise.connect(api_url="http://host:8100", api_key="ls_invalid")

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


def test_connect__ssl_error(mocker: MockerFixture, patch_db_connect: MockType) -> None:
    mocker.patch.object(
        requests, "get", side_effect=requests.exceptions.SSLError("certificate verify failed")
    )

    with pytest.raises(ConnectionError, match="SSL error connecting to"):
        enterprise.connect(api_url="https://host:8100", token="tok")

    patch_db_connect.assert_not_called()


def test_connect__connection_error(mocker: MockerFixture, patch_db_connect: MockType) -> None:
    mocker.patch.object(requests, "get", side_effect=requests.ConnectionError("refused"))

    with pytest.raises(ConnectionError, match="Could not reach LightlyStudio"):
        enterprise.connect(api_url="http://unreachable:8100", token="tok")

    patch_db_connect.assert_not_called()


def test_connect__sets_aws_env_vars(
    mocker: MockerFixture,
    patch_db_connect: MockType,  # noqa: ARG001
) -> None:
    access_key_id = "AKIAIOSFODNN7EXAMPLE"
    secret_access_key = "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"

    mock_response = mocker.MagicMock()
    mock_response.status_code = 200
    mock_response.ok = True
    mock_response.json.return_value = {
        "engine_url": "postgresql://lightly:secret@10.0.0.5:5433/lightly_studio",
        "cloud_credentials": {
            "AWS_ACCESS_KEY_ID": access_key_id,
            "AWS_SECRET_ACCESS_KEY": secret_access_key,
        },
    }
    mocker.patch.object(requests, "get", return_value=mock_response)

    enterprise.connect(api_url="http://10.0.0.5:8100", token="token")

    assert os.environ["AWS_ACCESS_KEY_ID"] == access_key_id
    assert os.environ["AWS_SECRET_ACCESS_KEY"] == secret_access_key


def test_connect__applies_gcs_runtime_config(
    mocker: MockerFixture,
    patch_db_connect: MockType,  # noqa: ARG001
) -> None:
    mocker.patch.dict(fsspec.config.conf, {}, clear=True)
    clear_cache = mocker.spy(GCSFileSystem, "clear_instance_cache")
    storage_options = {"project": "test-project", "token": "anon"}
    serialized_options = json.dumps(storage_options)
    mock_response = mocker.MagicMock()
    mock_response.status_code = 200
    mock_response.ok = True
    mock_response.json.return_value = {
        "engine_url": "postgresql://lightly:secret@10.0.0.5:5433/lightly_studio",
        "cloud_credentials": {"FSSPEC_GCS": serialized_options},
    }
    mocker.patch.object(requests, "get", return_value=mock_response)

    enterprise.connect(api_url="http://10.0.0.5:8100", token="token")

    assert os.environ["FSSPEC_GCS"] == serialized_options
    assert fsspec.config.conf["gcs"] == storage_options
    clear_cache.assert_called_once_with()


def test_connect__aws_missing_skips_env(
    mocker: MockerFixture,
    patch_db_connect: MockType,  # noqa: ARG001
) -> None:
    mock_response = mocker.MagicMock()
    mock_response.status_code = 200
    mock_response.ok = True
    mock_response.json.return_value = {
        "engine_url": "postgresql://lightly:secret@10.0.0.5:5433/lightly_studio",
    }
    mocker.patch.object(requests, "get", return_value=mock_response)

    enterprise.connect(api_url="http://10.0.0.5:8100", token="token")

    assert "AWS_ACCESS_KEY_ID" not in os.environ
    assert "AWS_SECRET_ACCESS_KEY" not in os.environ
