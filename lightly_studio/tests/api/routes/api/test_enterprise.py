import os

import fsspec
from fastapi.testclient import TestClient
from pytest_mock import MockerFixture
from s3fs import S3FileSystem  # type: ignore[import-untyped]


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
        json={"AWS_ACCESS_KEY_ID": "x"},
    )

    assert response.status_code == 204
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

    assert response.status_code == 204
    assert not S3FileSystem._cache
    assert fsspec.filesystem("s3", anon=False) is not old_fs  # fresh instance

    S3FileSystem.clear_instance_cache()


def test_refresh_cloud_credentials__rejects_disallowed_keys(
    test_client: TestClient,
) -> None:
    response = test_client.put(
        "/api/cloud-credentials",
        json={"EVIL_KEY": "value"},
    )

    assert response.status_code == 400


def test_refresh_cloud_credentials__rejects_mixed_disallowed_keys(
    test_client: TestClient,
) -> None:
    response = test_client.put(
        "/api/cloud-credentials",
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
    mocker.patch("gcsfs.GCSFileSystem.clear_instance_cache")

    response = test_client.put(
        "/api/cloud-credentials",
        json={"GOOGLE_APPLICATION_CREDENTIALS": "/path/to/key.json"},
    )

    assert response.status_code == 204
