"""Tests for the process-wide MCAP summary cache."""

from __future__ import annotations

import threading
import time
from collections.abc import Iterator
from unittest.mock import Mock

import pytest
from mcap.summary import Summary

from lightly_studio.core.mcap.reader import summary_cache


@pytest.fixture(autouse=True)
def clear_summary_cache() -> Iterator[None]:
    summary_cache.clear()
    yield
    summary_cache.clear()


def test_install_cached_summary__reuses_summary() -> None:
    uri = "s3://bucket/recording.mcap"
    summary = Summary()
    first = _reader(summary)
    summary_cache.install_cached_summary(reader=first, uri=uri)

    second = Mock()
    second.get_summary.side_effect = AssertionError("cached summary was read again")
    summary_cache.install_cached_summary(reader=second, uri=uri)

    assert second._summary is summary
    first.get_summary.assert_called_once()


def test_install_cached_summary__skips_local_path() -> None:
    reader = _reader(Summary())
    summary_cache.install_cached_summary(reader=reader, uri="C:/data/recording.mcap")

    reader.get_summary.assert_not_called()


def test_install_cached_summary__evicts_least_recently_used() -> None:
    summaries = [Summary() for _ in range(summary_cache._CACHE_SIZE + 1)]
    uris = [f"s3://bucket/recording-{index}.mcap" for index in range(len(summaries))]
    for uri, summary in zip(uris, summaries):
        summary_cache.install_cached_summary(reader=_reader(summary), uri=uri)

    evicted = _reader(Summary())
    summary_cache.install_cached_summary(reader=evicted, uri=uris[0])
    evicted.get_summary.assert_called_once()

    kept = Mock()
    kept.get_summary.side_effect = AssertionError("cached summary was read again")
    summary_cache.install_cached_summary(reader=kept, uri=uris[-1])
    assert kept._summary is summaries[-1]


def test_install_cached_summary__single_flight() -> None:
    uri = "s3://bucket/recording.mcap"
    summary = Summary()
    entered = threading.Event()
    release = threading.Event()
    readers: list[Mock] = []
    errors: list[BaseException] = []

    def read_summary() -> Summary:
        entered.set()
        if not release.wait(timeout=5):
            raise TimeoutError("The summary read was not released.")
        return summary

    def open_one() -> None:
        reader = Mock()
        readers.append(reader)
        reader.get_summary.side_effect = read_summary
        try:
            summary_cache.install_cached_summary(reader=reader, uri=uri)
        except Exception as error:
            errors.append(error)

    leader = threading.Thread(target=open_one)
    follower = threading.Thread(target=open_one)
    leader.start()
    try:
        assert entered.wait(timeout=5)
        follower.start()
        assert _waiter_arrived(uri), "The second reader did not wait for the summary."
        release.set()
        leader.join(timeout=5)
        follower.join(timeout=5)
    finally:
        release.set()
        leader.join(timeout=5)
        if follower.ident is not None:
            follower.join(timeout=5)

    assert errors == []
    assert not leader.is_alive()
    assert not follower.is_alive()
    assert sorted(reader.get_summary.call_count for reader in readers) == [0, 1]
    assert [reader._summary for reader in readers] == [summary, summary]


def _reader(summary: Summary) -> Mock:
    reader = Mock()
    reader.get_summary.return_value = summary
    return reader


def _waiter_arrived(uri: str) -> bool:
    """Returns whether a second opener is waiting on the download of `uri`."""
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        with summary_cache._lock:
            flight = summary_cache._inflight.get(uri)
            if flight is not None and flight.waiters >= 1:
                return True
        time.sleep(0.01)
    return False
