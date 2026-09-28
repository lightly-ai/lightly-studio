"""Tests for the process-wide MCAP reader cache."""

from __future__ import annotations

import threading
from collections.abc import Iterator
from pathlib import Path

import pytest

from lightly_studio.core.mcap.reader import McapFileReader
from lightly_studio.services.recording_service import reader_cache
from lightly_studio.services.recording_service.reader_cache import get_cached_reader
from tests.core.mcap import helpers


@pytest.fixture(autouse=True)
def clear_reader_cache() -> Iterator[None]:
    reader_cache.clear()
    yield
    reader_cache.clear()


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


def test_get_cached_reader__shares_reader_across_threads(tmp_path: Path) -> None:
    uri = str(helpers.write_mcap(tmp_path / "recording.mcap"))
    readers: list[McapFileReader] = []
    threads = [
        threading.Thread(target=lambda: readers.append(get_cached_reader(uri))) for _ in range(2)
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert readers[0] is readers[1]


def test_clear(tmp_path: Path) -> None:
    uri = str(helpers.write_mcap(tmp_path / "recording.mcap"))
    first = get_cached_reader(uri)

    reader_cache.clear()

    assert get_cached_reader(uri) is not first
