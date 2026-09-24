"""Tests for the thread-local MCAP reader cache."""

from __future__ import annotations

from collections import OrderedDict
from collections.abc import Iterator
from pathlib import Path
from typing import cast

import pytest
from pytest_mock import MockerFixture

from lightly_studio.core.mcap.reader import McapFileReader
from lightly_studio.services.recording_service import reader_cache
from lightly_studio.services.recording_service.reader_cache import get_cached_reader
from tests.core.mcap import helpers


@pytest.fixture(autouse=True)
def clear_reader_cache() -> Iterator[None]:
    cache = cast(
        "OrderedDict[str, McapFileReader] | None",
        getattr(reader_cache._thread_local, "reader_cache", None),
    )
    if cache is None:
        cache = OrderedDict()
        reader_cache._thread_local.reader_cache = cache
    for reader in cache.values():
        reader.close()
    cache.clear()
    yield
    for reader in cache.values():
        reader.close()
    cache.clear()


def test_get_cached_reader__returns_same_reader_on_hit(tmp_path: Path) -> None:
    uri = str(helpers.write_mcap(tmp_path / "recording.mcap"))
    first = get_cached_reader(uri)
    second = get_cached_reader(uri)
    assert first is second


def test_get_cached_reader__evicts_lru_and_closes_it(tmp_path: Path) -> None:
    uris = [
        str(helpers.write_mcap(tmp_path / f"r{i}.mcap"))
        for i in range(reader_cache._READER_CACHE_SIZE + 1)
    ]
    evicted = get_cached_reader(uris[0])
    for uri in uris[1:]:
        get_cached_reader(uri)

    # The first reader was evicted; opening it again should yield a new object.
    replacement = get_cached_reader(uris[0])
    assert evicted is not replacement


def test_get_cached_reader__local_uri_has_no_storage_options(tmp_path: Path) -> None:
    uri = str(helpers.write_mcap(tmp_path / "recording.mcap"))
    reader = get_cached_reader(uri)
    # Local paths must not use blockcache — the fsspec open call would fail if it tried.
    assert reader is not None


def test_get_cached_reader__remote_uri_uses_endpoint_url(
    monkeypatch: pytest.MonkeyPatch, mocker: MockerFixture
) -> None:
    mock_reader_cls = mocker.patch.object(reader_cache, "McapFileReader")
    monkeypatch.setenv("AWS_ENDPOINT_URL", "https://minio.example.com")
    assert get_cached_reader("s3://bucket/recording.mcap") is mock_reader_cls.return_value
    _, kwargs = mock_reader_cls.call_args
    assert kwargs["storage_options"] == {
        "client_kwargs": {"endpoint_url": "https://minio.example.com"}
    }


def test_get_cached_reader__remote_uri_without_endpoint_has_no_storage_options(
    monkeypatch: pytest.MonkeyPatch, mocker: MockerFixture
) -> None:
    mock_reader_cls = mocker.patch.object(reader_cache, "McapFileReader")
    monkeypatch.delenv("AWS_ENDPOINT_URL", raising=False)
    get_cached_reader("gs://bucket/recording.mcap")
    _, kwargs = mock_reader_cls.call_args
    assert kwargs["storage_options"] is None
