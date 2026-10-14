"""Tests for sharing dynamic transforms of a remote MCAP file."""

from __future__ import annotations

import threading
import time
from collections.abc import Iterator

import pytest

from lightly_studio.core.mcap.reader import calibration, dynamic_transform_cache
from lightly_studio.core.mcap.type_definitions import StaticTransform

_URI = "s3://bucket/recording.mcap"
_WINDOW_NS = 100_000_000


@pytest.fixture(autouse=True)
def clear_dynamic_transform_cache() -> Iterator[None]:
    dynamic_transform_cache.clear()
    yield
    dynamic_transform_cache.clear()


def test_edges_covering__one_load_serves_a_bucket() -> None:
    loads: list[tuple[int, int]] = []
    edges = [_edge(child="base", timestamp_ns=0), _edge(child="base", timestamp_ns=50_000_000)]

    def load(start_ns: int, end_ns: int) -> list[StaticTransform]:
        loads.append((start_ns, end_ns))
        return edges

    first = dynamic_transform_cache.edges_covering(
        uri=_URI, topic="/tf", timestamp_ns=10_000_000, window_ns=_WINDOW_NS, load=load
    )
    second = dynamic_transform_cache.edges_covering(
        uri=_URI, topic="/tf", timestamp_ns=90_000_000, window_ns=_WINDOW_NS, load=load
    )

    assert loads == [(0, 200_000_000)]
    assert first == second == edges
    closest_early = calibration._closest_per_child(edges=edges, timestamp_ns=10_000_000)
    closest_late = calibration._closest_per_child(edges=edges, timestamp_ns=90_000_000)
    assert closest_early[0].timestamp_ns == 0
    assert closest_late[0].timestamp_ns == 50_000_000


def test_edges_covering__next_bucket_reads_again() -> None:
    loads = 0

    def load(start_ns: int, _end_ns: int) -> list[StaticTransform]:
        nonlocal loads
        loads += 1
        return [_edge(child="base", timestamp_ns=start_ns)]

    dynamic_transform_cache.edges_covering(
        uri=_URI, topic="/tf", timestamp_ns=10_000_000, window_ns=_WINDOW_NS, load=load
    )
    dynamic_transform_cache.edges_covering(
        uri=_URI, topic="/tf", timestamp_ns=150_000_000, window_ns=_WINDOW_NS, load=load
    )

    assert loads == 2


def test_edges_covering__local_path_reads_every_time() -> None:
    loads = 0

    def load(_start_ns: int, _end_ns: int) -> list[StaticTransform]:
        nonlocal loads
        loads += 1
        return []

    for _ in range(2):
        dynamic_transform_cache.edges_covering(
            uri="C:/data/recording.mcap",
            topic="/tf",
            timestamp_ns=10_000_000,
            window_ns=_WINDOW_NS,
            load=load,
        )

    assert loads == 2


def test_edges_covering__evicts_least_recently_used(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(dynamic_transform_cache, "_CACHE_SIZE", 1)
    loads = 0

    def load(start_ns: int, _end_ns: int) -> list[StaticTransform]:
        nonlocal loads
        loads += 1
        return [_edge(child="base", timestamp_ns=start_ns)]

    dynamic_transform_cache.edges_covering(
        uri=_URI, topic="/tf", timestamp_ns=10_000_000, window_ns=_WINDOW_NS, load=load
    )
    dynamic_transform_cache.edges_covering(
        uri=_URI, topic="/tf", timestamp_ns=150_000_000, window_ns=_WINDOW_NS, load=load
    )
    dynamic_transform_cache.edges_covering(
        uri=_URI, topic="/tf", timestamp_ns=10_000_000, window_ns=_WINDOW_NS, load=load
    )

    assert loads == 3


def test_edges_covering__single_flight() -> None:
    entered = threading.Event()
    release = threading.Event()
    loads = 0
    errors: list[BaseException] = []

    def load(_start_ns: int, _end_ns: int) -> list[StaticTransform]:
        nonlocal loads
        loads += 1
        entered.set()
        if not release.wait(timeout=5):
            raise TimeoutError("The transform read was not released.")
        return [_edge(child="base", timestamp_ns=0)]

    def read() -> None:
        try:
            dynamic_transform_cache.edges_covering(
                uri=_URI, topic="/tf", timestamp_ns=10_000_000, window_ns=_WINDOW_NS, load=load
            )
        except Exception as error:
            errors.append(error)

    leader = threading.Thread(target=read)
    follower = threading.Thread(target=read)
    leader.start()
    try:
        assert entered.wait(timeout=5)
        follower.start()
        assert _follower_is_waiting(), "The second lookup did not wait for the bucket."
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
    assert loads == 1


def _edge(child: str, timestamp_ns: int) -> StaticTransform:
    return StaticTransform(
        parent_frame_id="map",
        child_frame_id=child,
        translation=(0.0, 0.0, 0.0),
        rotation=(0.0, 0.0, 0.0, 1.0),
        timestamp_ns=timestamp_ns,
    )


def _follower_is_waiting() -> bool:
    """Returns whether a second lookup is waiting on the in-flight bucket."""
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        with dynamic_transform_cache._lock:
            if any(flight.waiters >= 1 for flight in dynamic_transform_cache._inflight.values()):
                return True
        time.sleep(0.01)
    return False
