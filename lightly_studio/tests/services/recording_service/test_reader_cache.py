"""Tests for the process-wide MCAP reader pool."""

from __future__ import annotations

import threading
from collections.abc import Iterator
from pathlib import Path

import pytest

from lightly_studio.core.mcap.reader import McapFileReader
from lightly_studio.services.recording_service import reader_cache
from tests.core.mcap import helpers


@pytest.fixture(autouse=True)
def clear_reader_cache() -> Iterator[None]:
    reader_cache.clear()
    yield
    reader_cache.clear()


def test_borrow_reader__reuses_a_returned_reader(tmp_path: Path) -> None:
    uri = str(helpers.write_mcap(tmp_path / "recording.mcap"))
    with reader_cache.borrow_reader(uri=uri) as first:
        opened = first
    with reader_cache.borrow_reader(uri=uri) as second:
        assert second is opened


def test_borrow_reader__parallel_borrows_open_distinct_readers(tmp_path: Path) -> None:
    uri = str(helpers.write_mcap(tmp_path / "recording.mcap"))
    ready = threading.Barrier(2)
    opened: list[object] = []

    def borrow() -> None:
        with reader_cache.borrow_reader(uri=uri) as reader:
            opened.append(reader)
            ready.wait(timeout=5)

    first = threading.Thread(target=borrow)
    second = threading.Thread(target=borrow)
    first.start()
    second.start()
    first.join(timeout=5)
    second.join(timeout=5)

    assert not first.is_alive()
    assert not second.is_alive()
    assert len(opened) == 2
    assert opened[0] is not opened[1]


def test_borrow_reader__closes_the_least_recently_used_idle_reader(tmp_path: Path) -> None:
    uris = [
        str(helpers.write_mcap(tmp_path / f"r{index}.mcap"))
        for index in range(reader_cache._MAX_IDLE_READERS + 1)
    ]
    opened: list[McapFileReader] = []
    for uri in uris:
        with reader_cache.borrow_reader(uri=uri) as reader:
            opened.append(reader)

    with pytest.raises(ValueError, match="closed file"):
        opened[0].get_topics()
    assert uris[0] not in reader_cache._slots
    with reader_cache.borrow_reader(uri=uris[0]) as replacement:
        assert replacement is not opened[0]


def test_borrow_reader__local_uri_opens(tmp_path: Path) -> None:
    uri = str(helpers.write_mcap(tmp_path / "recording.mcap"))
    with reader_cache.borrow_reader(uri=uri) as reader:
        assert reader.get_topics()
