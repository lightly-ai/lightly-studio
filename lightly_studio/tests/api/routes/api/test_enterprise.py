import os

import fsspec
from fastapi.testclient import TestClient
from pytest_mock import MockerFixture
from s3fs import S3FileSystem


def test_refresh_cloud_credentials__sets_env_vars(
    test_client: TestClient,
    mocker: MockerFixture,
) -> None:
    mocker.patch.dict(os.environ, clear=False)

    response = test_client.put(
        "/api/cloud-credentials",
        json={
            "AWS_ACCESS_KEY_ID": "test-key-id",
            "AWS_SECRET_ACCESS_KEY": "test-secret",
        },
    )

    assert response.status_code == 200
    assert os.environ["AWS_ACCESS_KEY_ID"] == "test-key-id"
    assert os.environ["AWS_SECRET_ACCESS_KEY"] == "test-secret"


def test_refresh_cloud_credentials__clears_s3_cache(
    test_client: TestClient,
    mocker: MockerFixture,
) -> None:
    spy = mocker.spy(S3FileSystem, "clear_instance_cache")

    response = test_client.put(
        "/api/cloud-credentials",
        json={"AWS_ACCESS_KEY_ID": "x"},
    )

    assert response.status_code == 200
    spy.assert_called_once()


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
        json={
            "AWS_ACCESS_KEY_ID": "new-key",
            "AWS_SECRET_ACCESS_KEY": "new-secret",
        },
    )

    assert response.status_code == 200
    assert not S3FileSystem._cache
    assert fsspec.filesystem("s3", anon=False) is not old_fs  # fresh instance
