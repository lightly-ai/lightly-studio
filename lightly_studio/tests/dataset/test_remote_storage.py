from __future__ import annotations

from collections.abc import Generator

import fsspec
import pytest

from lightly_studio.dataset import env, remote_storage


@pytest.fixture
def clean_fsspec_conf() -> Generator[None, None, None]:
    """Restore fsspec's global runtime config after a test mutates it."""
    previous = fsspec.config.conf.get("s3")
    fsspec.config.conf.pop("s3", None)
    yield
    fsspec.config.conf.pop("s3", None)
    if previous is not None:
        fsspec.config.conf["s3"] = previous


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        ("s3://bucket/key.jpg", True),
        ("gs://bucket/key.jpg", True),
        ("gcs://bucket/key.jpg", True),
        ("azure://container/key.jpg", True),
        ("abfs://container/key.jpg", True),
        ("/data/images/key.jpg", False),
        ("key.jpg", False),
        ("file:///data/key.jpg", False),
        ("memory://key.jpg", False),
    ],
)
def test_is_remote_path(path: str, expected: bool) -> None:
    assert remote_storage.is_remote_path(path) is expected


def test_open_kwargs_for_path__remote_caps_block_size() -> None:
    kwargs = remote_storage.open_kwargs_for_path("s3://bucket/key.jpg")

    assert kwargs == {"block_size": env.LIGHTLY_STUDIO_REMOTE_BLOCK_SIZE}


def test_open_kwargs_for_path__local_passes_no_kwargs() -> None:
    # LocalFileSystem.open does not accept block_size, so it must not be passed.
    assert remote_storage.open_kwargs_for_path("/data/images/key.jpg") == {}


def test_read_workers_for_path__remote_uses_io_concurrency() -> None:
    workers = remote_storage.read_workers_for_path("s3://bucket/key.jpg")

    assert workers == env.LIGHTLY_STUDIO_IO_CONCURRENCY


def test_read_workers_for_path__local_uses_cpu_count() -> None:
    workers = remote_storage.read_workers_for_path("/data/images/key.jpg")

    assert workers == remote_storage.cpu_workers()


@pytest.mark.usefixtures("clean_fsspec_conf")
def test_apply_s3_connection_pool_config() -> None:
    remote_storage.apply_s3_connection_pool_config()

    pool_size = fsspec.config.conf["s3"]["config_kwargs"]["max_pool_connections"]
    # The pool must not throttle the readers it serves.
    assert pool_size >= env.LIGHTLY_STUDIO_IO_CONCURRENCY


@pytest.mark.usefixtures("clean_fsspec_conf")
def test_apply_s3_connection_pool_config__preserves_existing_keys() -> None:
    fsspec.config.conf["s3"] = {"key": "AKIAEXAMPLE", "secret": "shhh"}

    remote_storage.apply_s3_connection_pool_config()

    protocol_config = fsspec.config.conf["s3"]
    assert protocol_config["key"] == "AKIAEXAMPLE"
    assert protocol_config["secret"] == "shhh"
    assert protocol_config["config_kwargs"]["max_pool_connections"] > 0


@pytest.mark.usefixtures("clean_fsspec_conf")
def test_apply_s3_connection_pool_config__does_not_lower_a_larger_pool() -> None:
    fsspec.config.conf["s3"] = {"config_kwargs": {"max_pool_connections": 1024}}

    remote_storage.apply_s3_connection_pool_config()

    assert fsspec.config.conf["s3"]["config_kwargs"]["max_pool_connections"] == 1024


@pytest.mark.usefixtures("clean_fsspec_conf")
def test_apply_s3_connection_pool_config__is_idempotent() -> None:
    remote_storage.apply_s3_connection_pool_config()
    first = dict(fsspec.config.conf["s3"]["config_kwargs"])

    remote_storage.apply_s3_connection_pool_config()

    assert fsspec.config.conf["s3"]["config_kwargs"] == first
