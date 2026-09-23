from __future__ import annotations

import fsspec
import pytest
from pytest_mock import MockerFixture

from lightly_studio.dataset import env, remote_storage


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        ("/videos/a.mp4", False),
        ("file:///videos/a.mp4", False),
        ("local:///videos/a.mp4", False),
        ("s3://bucket/a.mp4", True),
        ("gs://bucket/a.mp4", True),
    ],
)
def test_is_remote(path: str, expected: bool) -> None:
    assert remote_storage.is_remote(path=path) is expected


def test_image_probe_workers(mocker: MockerFixture) -> None:
    mocker.patch.object(env, "LIGHTLY_STUDIO_REMOTE_IMAGE_PROBE_WORKERS", 7)

    assert remote_storage.image_probe_workers(paths=["/images/a.png", "s3://bucket/b.png"]) == 7
    assert remote_storage.image_probe_workers(paths=["/images/a.png", "file:///b.png"]) == 1


@pytest.mark.parametrize(
    ("initial_config", "expected_pool_size"),
    [
        ({}, 7),
        ({"s3": {"config_kwargs": {"max_pool_connections": 3}}}, 7),
        # An existing pool larger than our worker count must not be shrunk.
        ({"s3": {"config_kwargs": {"max_pool_connections": 64}}}, 64),
    ],
)
def test_configure_connections(
    initial_config: dict[str, dict[str, dict[str, int]]],
    expected_pool_size: int,
    mocker: MockerFixture,
) -> None:
    mocker.patch.object(env, "LIGHTLY_STUDIO_REMOTE_IMAGE_PROBE_WORKERS", 7)
    # fsspec.config.conf is global process state, patch.dict restores it after the test.
    mocker.patch.dict(fsspec.config.conf, initial_config, clear=True)

    remote_storage.configure_connections(paths=["s3://bucket/image.png"])

    assert fsspec.config.conf["s3"]["config_kwargs"]["max_pool_connections"] == expected_pool_size
