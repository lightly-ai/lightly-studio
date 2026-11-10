from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

import fsspec
import pytest
from adlfs import AzureBlobFileSystem  # type: ignore[import-untyped]
from fastapi.testclient import TestClient
from gcsfs import GCSFileSystem  # type: ignore[import-untyped]
from pytest_mock import MockerFixture
from s3fs import S3FileSystem  # type: ignore[import-untyped]

from lightly_studio import ca_bundle
from lightly_studio.dataset import env
from tests import helpers_tls

_SECRET = "test-cloud-credentials-secret"
_HEADERS = {"X-Cloud-Credentials-Secret": _SECRET}


@pytest.fixture(autouse=True)
def _set_cloud_credentials_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(env, "LIGHTLY_STUDIO_CLOUD_CREDENTIALS_SECRET", _SECRET)


@pytest.mark.parametrize(
    "headers",
    [
        {},
        {"X-Cloud-Credentials-Secret": ""},
        {"X-Cloud-Credentials-Secret": "wrong-secret"},
    ],
)
def test_refresh_cloud_credentials__rejects_missing_or_wrong_secret(
    test_client: TestClient,
    mocker: MockerFixture,
    headers: dict[str, str],
) -> None:
    mocker.patch.dict(os.environ, clear=False)

    response = test_client.put(
        "/api/cloud-credentials",
        headers=headers,
        json={"AWS_ACCESS_KEY_ID": "attacker-key"},
    )

    assert response.status_code == 403
    assert os.environ.get("AWS_ACCESS_KEY_ID") != "attacker-key"


def test_refresh_cloud_credentials__rejects_non_ascii_secret(
    test_client: TestClient,
) -> None:
    response = test_client.put(
        "/api/cloud-credentials",
        headers={b"X-Cloud-Credentials-Secret": "wrong-\u00e9".encode()},
        json={"AWS_ACCESS_KEY_ID": "key"},
    )

    assert response.status_code == 403


@pytest.mark.parametrize("secret", [None, ""])
def test_refresh_cloud_credentials__rejects_every_request_without_configured_secret(
    test_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    secret: str | None,
) -> None:
    monkeypatch.setattr(env, "LIGHTLY_STUDIO_CLOUD_CREDENTIALS_SECRET", secret)

    response = test_client.put(
        "/api/cloud-credentials",
        headers={"X-Cloud-Credentials-Secret": ""},
        json={"AWS_ACCESS_KEY_ID": "key"},
    )

    assert response.status_code == 403


def test_refresh_cloud_credentials__checks_secret_before_body(
    test_client: TestClient,
) -> None:
    response = test_client.put("/api/cloud-credentials", json=[1])

    assert response.status_code == 403


def test_refresh_cloud_credentials__sets_env_vars(
    test_client: TestClient,
    mocker: MockerFixture,
) -> None:
    mocker.patch.dict(os.environ, clear=False)

    response = test_client.put(
        "/api/cloud-credentials",
        headers=_HEADERS,
        json={
            "AWS_ACCESS_KEY_ID": "test-key-id",
            "AWS_SECRET_ACCESS_KEY": "test-secret",
        },
    )

    assert response.status_code == 204
    assert os.environ["AWS_ACCESS_KEY_ID"] == "test-key-id"
    assert os.environ["AWS_SECRET_ACCESS_KEY"] == "test-secret"


def test_refresh_cloud_credentials__clears_s3_cache(
    test_client: TestClient,
    mocker: MockerFixture,
) -> None:
    mocker.patch.dict(os.environ, clear=False)
    spy = mocker.spy(S3FileSystem, "clear_instance_cache")

    response = test_client.put(
        "/api/cloud-credentials",
        headers=_HEADERS,
        json={"AWS_ACCESS_KEY_ID": "x"},
    )

    assert response.status_code == 204
    spy.assert_called_once()


def test_refresh_cloud_credentials__applies_gcs_config(
    test_client: TestClient,
    mocker: MockerFixture,
) -> None:
    mocker.patch.dict(os.environ, clear=False)
    mocker.patch.dict(fsspec.config.conf, {}, clear=True)
    clear_cache = mocker.spy(GCSFileSystem, "clear_instance_cache")
    storage_options = {"project": "test-project", "token": "anon"}

    response = test_client.put(
        "/api/cloud-credentials",
        headers=_HEADERS,
        json={"FSSPEC_GCS": json.dumps(storage_options)},
    )

    assert response.status_code == 204
    assert fsspec.config.conf["gcs"] == storage_options
    clear_cache.assert_called_once_with()


def test_refresh_cloud_credentials__applies_azure_config(
    test_client: TestClient,
    mocker: MockerFixture,
) -> None:
    mocker.patch.dict(os.environ, clear=False)
    mocker.patch.dict(fsspec.config.conf, {}, clear=True)
    clear_cache = mocker.spy(AzureBlobFileSystem, "clear_instance_cache")
    storage_options = {"account_name": "test-account", "account_key": "test-key"}
    serialized_options = json.dumps(storage_options)

    response = test_client.put(
        "/api/cloud-credentials",
        headers=_HEADERS,
        json={"FSSPEC_ABFS": serialized_options},
    )

    assert response.status_code == 204
    assert os.environ["FSSPEC_ABFS"] == serialized_options
    assert fsspec.config.conf["abfs"] == storage_options
    clear_cache.assert_called_once_with()


def test_refresh_cloud_credentials__invalidates_cached_s3_filesystem(
    test_client: TestClient,
    mocker: MockerFixture,
) -> None:
    mocker.patch.dict(os.environ, clear=False)

    # Create an S3FileSystem instance so fsspec caches it.
    os.environ["AWS_ACCESS_KEY_ID"] = "old-key"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "old-secret"
    old_fs = fsspec.filesystem("s3", anon=False)
    assert S3FileSystem._cache
    assert fsspec.filesystem("s3", anon=False) is old_fs  # same cached instance

    # Push new credentials via the endpoint
    response = test_client.put(
        "/api/cloud-credentials",
        headers=_HEADERS,
        json={
            "AWS_ACCESS_KEY_ID": "new-key",
            "AWS_SECRET_ACCESS_KEY": "new-secret",
        },
    )

    assert response.status_code == 204
    assert not S3FileSystem._cache
    assert fsspec.filesystem("s3", anon=False) is not old_fs  # fresh instance

    S3FileSystem.clear_instance_cache()


def test_refresh_cloud_credentials__rejects_disallowed_keys(
    test_client: TestClient,
) -> None:
    response = test_client.put(
        "/api/cloud-credentials",
        headers=_HEADERS,
        json={"EVIL_KEY": "value"},
    )

    assert response.status_code == 400


def test_refresh_cloud_credentials__rejects_mixed_disallowed_keys(
    test_client: TestClient,
) -> None:
    response = test_client.put(
        "/api/cloud-credentials",
        headers=_HEADERS,
        json={
            "AWS_ACCESS_KEY_ID": "key",
            "EVIL_KEY": "value",
        },
    )

    assert response.status_code == 400


def test_refresh_cloud_credentials__drops_omitted_aws_key_on_rotation(
    test_client: TestClient,
    mocker: MockerFixture,
) -> None:
    mocker.patch.dict(
        os.environ,
        {
            "AWS_ACCESS_KEY_ID": "old-key",
            "AWS_SECRET_ACCESS_KEY": "old-secret",
            "AWS_SESSION_TOKEN": "old-token",
        },
        clear=False,
    )

    # Rotation payload uses long-term credentials — no session token.
    response = test_client.put(
        "/api/cloud-credentials",
        headers=_HEADERS,
        json={
            "AWS_ACCESS_KEY_ID": "new-key",
            "AWS_SECRET_ACCESS_KEY": "new-secret",
        },
    )

    assert response.status_code == 204
    assert os.environ["AWS_ACCESS_KEY_ID"] == "new-key"
    assert os.environ["AWS_SECRET_ACCESS_KEY"] == "new-secret"
    assert "AWS_SESSION_TOKEN" not in os.environ


def test_refresh_cloud_credentials__accepts_google_credentials(
    test_client: TestClient,
    mocker: MockerFixture,
) -> None:
    mocker.patch.dict(os.environ, clear=False)
    clear_cache = mocker.patch("gcsfs.GCSFileSystem.clear_instance_cache")

    response = test_client.put(
        "/api/cloud-credentials",
        headers=_HEADERS,
        json={"GOOGLE_APPLICATION_CREDENTIALS": "/path/to/key.json"},
    )

    assert response.status_code == 204
    assert os.environ["GOOGLE_APPLICATION_CREDENTIALS"] == "/path/to/key.json"
    clear_cache.assert_called_once()


def test_refresh_cloud_credentials__writes_ca_bundle(
    test_client: TestClient,
    mocker: MockerFixture,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    mocker.patch.dict(os.environ, clear=False)
    mocker.patch.object(ca_bundle, "_written_files", [])
    monkeypatch.setattr(tempfile, "tempdir", str(tmp_path))
    ca_pem = helpers_tls.create_ca(common_name="Test Root CA").certificate_pem()

    response = test_client.put(
        "/api/cloud-credentials",
        headers=_HEADERS,
        json={"AWS_ACCESS_KEY_ID": "key", "AWS_CA_BUNDLE_PEM": ca_pem},
    )

    assert response.status_code == 204
    assert "AWS_CA_BUNDLE_PEM" not in os.environ
    assert Path(os.environ["AWS_CA_BUNDLE"]).read_text().endswith(ca_pem)
    ca_bundle.delete_ca_bundles(keep=None)


def test_refresh_cloud_credentials__rejects_invalid_ca_bundle(
    test_client: TestClient,
) -> None:
    response = test_client.put(
        "/api/cloud-credentials",
        headers=_HEADERS,
        json={"AWS_ACCESS_KEY_ID": "key", "AWS_CA_BUNDLE_PEM": "not a certificate"},
    )

    assert response.status_code == 400
