"""Tests for applying cloud storage credentials."""

from __future__ import annotations

import json
import os
from collections.abc import Generator

import fsspec
import pytest
from adlfs import AzureBlobFileSystem  # type: ignore[import-untyped]
from gcsfs import GCSFileSystem  # type: ignore[import-untyped]
from pytest_mock import MockerFixture

from lightly_studio import cloud_credentials


@pytest.fixture(autouse=True)
def _reset_cloud_configuration(mocker: MockerFixture) -> Generator[None, None, None]:
    mocker.patch.dict(os.environ, {}, clear=True)
    mocker.patch.dict(fsspec.config.conf, {}, clear=True)
    AzureBlobFileSystem.clear_instance_cache()
    GCSFileSystem.clear_instance_cache()
    yield
    AzureBlobFileSystem.clear_instance_cache()
    GCSFileSystem.clear_instance_cache()


def test_apply_cloud_credentials__applies_gcs_runtime_config(
    mocker: MockerFixture,
) -> None:
    storage_options = {
        "project": "test-project",
        "token": {
            "type": "service_account",
            "client_email": "studio@test-project.iam.gserviceaccount.com",
        },
    }
    serialized_options = json.dumps(storage_options)
    clear_cache = mocker.spy(GCSFileSystem, "clear_instance_cache")

    cloud_credentials.apply_cloud_credentials(credentials={"FSSPEC_GCS": serialized_options})

    assert os.environ["FSSPEC_GCS"] == serialized_options
    assert fsspec.config.conf["gcs"] == storage_options
    clear_cache.assert_called_once_with()


def test_apply_cloud_credentials__invalidates_cached_gcs_filesystem() -> None:
    cloud_credentials.apply_cloud_credentials(
        credentials={"FSSPEC_GCS": json.dumps({"project": "old-project", "token": "anon"})}
    )
    old_filesystem = fsspec.filesystem("gcs")
    assert GCSFileSystem._cache
    assert fsspec.filesystem("gcs") is old_filesystem

    cloud_credentials.apply_cloud_credentials(
        credentials={"FSSPEC_GCS": json.dumps({"project": "new-project", "token": "anon"})}
    )

    assert not GCSFileSystem._cache
    new_filesystem = fsspec.filesystem("gcs")
    assert new_filesystem is not old_filesystem
    assert new_filesystem.project == "new-project"


def test_apply_cloud_credentials__replaces_removed_gcs_options() -> None:
    fsspec.config.conf["gcs"] = {
        "project": "old-project",
        "token": "old-token",
    }

    cloud_credentials.apply_cloud_credentials(
        credentials={"FSSPEC_GCS": json.dumps({"token": "new-token"})}
    )

    assert fsspec.config.conf["gcs"] == {"token": "new-token"}


def test_apply_cloud_credentials__applies_azure_runtime_config(
    mocker: MockerFixture,
) -> None:
    storage_options = {"account_name": "test-account", "account_key": "test-key"}
    serialized_options = json.dumps(storage_options)
    clear_cache = mocker.spy(AzureBlobFileSystem, "clear_instance_cache")

    cloud_credentials.apply_cloud_credentials(credentials={"FSSPEC_ABFS": serialized_options})

    assert os.environ["FSSPEC_ABFS"] == serialized_options
    assert fsspec.config.conf["abfs"] == storage_options
    assert fsspec.filesystem("az").account_name == "test-account"
    clear_cache.assert_called_once_with()


def test_apply_cloud_credentials__invalidates_cached_azure_filesystem() -> None:
    cloud_credentials.apply_cloud_credentials(
        credentials={
            "FSSPEC_ABFS": json.dumps({"account_name": "old-account", "account_key": "old-key"})
        }
    )
    old_filesystem = fsspec.filesystem("abfs")
    assert AzureBlobFileSystem._cache
    assert fsspec.filesystem("az") is old_filesystem

    cloud_credentials.apply_cloud_credentials(
        credentials={
            "FSSPEC_ABFS": json.dumps({"account_name": "new-account", "account_key": "new-key"})
        }
    )

    assert not AzureBlobFileSystem._cache
    new_filesystem = fsspec.filesystem("az")
    assert new_filesystem is not old_filesystem
    assert new_filesystem.account_name == "new-account"


@pytest.mark.parametrize("value", ["not-json", "[]"])
def test_apply_cloud_credentials__rejects_invalid_fsspec_config(value: str) -> None:
    with pytest.raises(ValueError, match="Invalid FSSPEC cloud credential configuration"):
        cloud_credentials.apply_cloud_credentials(credentials={"FSSPEC_GCS": value})

    assert "FSSPEC_GCS" not in os.environ
    assert "gcs" not in fsspec.config.conf


def test_apply_cloud_credentials__missing_filesystem_dependency(
    mocker: MockerFixture,
) -> None:
    mocker.patch.object(
        fsspec,
        "get_filesystem_class",
        side_effect=ImportError("No module named 'gcsfs'"),
    )

    with pytest.raises(ImportError, match="lightly-studio"):
        cloud_credentials.apply_cloud_credentials(
            credentials={"FSSPEC_GCS": json.dumps({"token": "anon"})}
        )

    assert "FSSPEC_GCS" not in os.environ
    assert "gcs" not in fsspec.config.conf


def test_validate_credential_keys__accepts_aws_keys() -> None:
    cloud_credentials._validate_credential_keys(
        credentials={
            "AWS_ACCESS_KEY_ID": "key",
            "AWS_SECRET_ACCESS_KEY": "secret",
            "AWS_SESSION_TOKEN": "token",
        }
    )


def test_validate_credential_keys__accepts_google_credentials() -> None:
    cloud_credentials._validate_credential_keys(
        credentials={"GOOGLE_APPLICATION_CREDENTIALS": "/path/to/key.json"}
    )


def test_validate_credential_keys__accepts_fsspec_keys() -> None:
    cloud_credentials._validate_credential_keys(
        credentials={"FSSPEC_S3_KEY": "key", "FSSPEC_S3_SECRET": "secret"}
    )


def test_validate_credential_keys__rejects_arbitrary_key() -> None:
    with pytest.raises(ValueError, match="EVIL_KEY"):
        cloud_credentials._validate_credential_keys(credentials={"EVIL_KEY": "value"})


def test_validate_credential_keys__rejects_mixed_keys() -> None:
    with pytest.raises(ValueError, match="EVIL_KEY"):
        cloud_credentials._validate_credential_keys(
            credentials={"AWS_ACCESS_KEY_ID": "key", "EVIL_KEY": "value"}
        )


def test_validate_credential_keys__rejects_path_traversal_key() -> None:
    with pytest.raises(ValueError, match="PATH"):
        cloud_credentials._validate_credential_keys(credentials={"PATH": "/usr/bin:/usr/local/bin"})


def test_validate_credential_keys__rejects_http_proxy_key() -> None:
    with pytest.raises(ValueError, match="HTTP_PROXY"):
        cloud_credentials._validate_credential_keys(
            credentials={"HTTP_PROXY": "http://attacker.example/"}
        )


def test_remove_stale_provider_env_vars__drops_omitted_aws_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "key")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "secret")
    monkeypatch.setenv("AWS_SESSION_TOKEN", "token")

    # Rotation payload does not include AWS_SESSION_TOKEN.
    cloud_credentials._remove_stale_provider_env_vars(
        credentials={"AWS_ACCESS_KEY_ID": "new-key", "AWS_SECRET_ACCESS_KEY": "new-secret"}
    )

    assert "AWS_ACCESS_KEY_ID" not in os.environ
    assert "AWS_SECRET_ACCESS_KEY" not in os.environ
    assert "AWS_SESSION_TOKEN" not in os.environ


def test_remove_stale_provider_env_vars__does_not_touch_other_providers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "key")
    monkeypatch.setenv("GOOGLE_APPLICATION_CREDENTIALS", "/path/to/key.json")

    # AWS-only payload — GCS variable must be left alone.
    cloud_credentials._remove_stale_provider_env_vars(credentials={"AWS_ACCESS_KEY_ID": "new-key"})

    assert "AWS_ACCESS_KEY_ID" not in os.environ
    assert os.environ["GOOGLE_APPLICATION_CREDENTIALS"] == "/path/to/key.json"


def test_remove_stale_provider_env_vars__drops_omitted_fsspec_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("FSSPEC_S3_KEY", "key")
    monkeypatch.setenv("FSSPEC_S3_SECRET", "secret")
    monkeypatch.setenv("FSSPEC_S3_TOKEN", "token")

    # Rotation payload does not include FSSPEC_S3_TOKEN.
    cloud_credentials._remove_stale_provider_env_vars(
        credentials={"FSSPEC_S3_KEY": "new-key", "FSSPEC_S3_SECRET": "new-secret"}
    )

    assert "FSSPEC_S3_KEY" not in os.environ
    assert "FSSPEC_S3_SECRET" not in os.environ
    assert "FSSPEC_S3_TOKEN" not in os.environ


def test_remove_stale_provider_env_vars__fsspec_only_does_not_touch_other_providers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("FSSPEC_S3_KEY", "key")
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "aws-key")
    monkeypatch.setenv("GOOGLE_APPLICATION_CREDENTIALS", "/path/to/key.json")

    # FSSPEC-only payload — AWS and GCS variables must be left alone.
    cloud_credentials._remove_stale_provider_env_vars(credentials={"FSSPEC_S3_KEY": "new-key"})

    assert "FSSPEC_S3_KEY" not in os.environ
    assert os.environ["AWS_ACCESS_KEY_ID"] == "aws-key"
    assert os.environ["GOOGLE_APPLICATION_CREDENTIALS"] == "/path/to/key.json"
