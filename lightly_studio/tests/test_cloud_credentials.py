"""Tests for applying cloud storage credentials."""

from __future__ import annotations

import json
import os
from collections.abc import Generator

import fsspec
import pytest
from gcsfs import GCSFileSystem  # type: ignore[import-untyped]
from pytest_mock import MockerFixture

from lightly_studio.cloud_credentials import apply_cloud_credentials


@pytest.fixture(autouse=True)
def _reset_cloud_configuration(mocker: MockerFixture) -> Generator[None, None, None]:
    mocker.patch.dict(os.environ, {}, clear=True)
    mocker.patch.dict(fsspec.config.conf, {}, clear=True)
    GCSFileSystem.clear_instance_cache()
    yield
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

    apply_cloud_credentials(credentials={"FSSPEC_GCS": serialized_options})

    assert os.environ["FSSPEC_GCS"] == serialized_options
    assert fsspec.config.conf["gcs"] == storage_options
    clear_cache.assert_called_once_with()


def test_apply_cloud_credentials__invalidates_cached_gcs_filesystem() -> None:
    apply_cloud_credentials(
        credentials={"FSSPEC_GCS": json.dumps({"project": "old-project", "token": "anon"})}
    )
    old_filesystem = fsspec.filesystem("gcs")
    assert GCSFileSystem._cache
    assert fsspec.filesystem("gcs") is old_filesystem

    apply_cloud_credentials(
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

    apply_cloud_credentials(credentials={"FSSPEC_GCS": json.dumps({"token": "new-token"})})

    assert fsspec.config.conf["gcs"] == {"token": "new-token"}


@pytest.mark.parametrize("value", ["not-json", "[]"])
def test_apply_cloud_credentials__rejects_invalid_fsspec_config(value: str) -> None:
    with pytest.raises(ValueError, match="Invalid FSSPEC cloud credential configuration"):
        apply_cloud_credentials(credentials={"FSSPEC_GCS": value})

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
        apply_cloud_credentials(credentials={"FSSPEC_GCS": json.dumps({"token": "anon"})})

    assert "FSSPEC_GCS" not in os.environ
    assert "gcs" not in fsspec.config.conf
