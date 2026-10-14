from __future__ import annotations

from lightly_studio.core.mcap.reader.span_store import SpanStore

_URI = "s3://bucket/recording.mcap"


class TestSpanStore:
    def test_get(self) -> None:
        store = SpanStore(max_bytes=100)
        store.put(uri=_URI, offset=10, data=b"0123456789")

        assert store.get(uri=_URI, offset=10, length=10) == b"0123456789"

    def test_get__range_inside_a_span(self) -> None:
        store = SpanStore(max_bytes=100)
        store.put(uri=_URI, offset=10, data=b"0123456789")

        assert store.get(uri=_URI, offset=13, length=4) == b"3456"

    def test_get__range_past_the_span(self) -> None:
        store = SpanStore(max_bytes=100)
        store.put(uri=_URI, offset=10, data=b"0123456789")

        assert store.get(uri=_URI, offset=18, length=4) is None

    def test_get__range_across_two_spans(self) -> None:
        store = SpanStore(max_bytes=100)
        store.put(uri=_URI, offset=0, data=b"aaaa")
        store.put(uri=_URI, offset=4, data=b"bbbb")

        assert store.get(uri=_URI, offset=2, length=4) is None

    def test_get__inside_a_long_span_before_a_short_one(self) -> None:
        store = SpanStore(max_bytes=100)
        store.put(uri=_URI, offset=0, data=b"0123456789")
        store.put(uri=_URI, offset=6, data=b"xy")

        assert store.get(uri=_URI, offset=7, length=3) == b"789"

    def test_get__other_uri(self) -> None:
        store = SpanStore(max_bytes=100)
        store.put(uri=_URI, offset=0, data=b"aaaa")

        assert store.get(uri="s3://bucket/other.mcap", offset=0, length=4) is None

    def test_contains(self) -> None:
        store = SpanStore(max_bytes=100)
        store.put(uri=_URI, offset=10, data=b"0123456789")

        assert store.contains(uri=_URI, offset=12, length=8)
        assert not store.contains(uri=_URI, offset=12, length=9)

    def test_put__drops_the_least_recently_used_span(self) -> None:
        store = SpanStore(max_bytes=8)
        store.put(uri=_URI, offset=0, data=b"aaaa")
        store.put(uri=_URI, offset=4, data=b"bbbb")
        store.get(uri=_URI, offset=0, length=1)
        store.put(uri=_URI, offset=8, data=b"cccc")

        assert store.get(uri=_URI, offset=0, length=4) == b"aaaa"
        assert store.get(uri=_URI, offset=4, length=4) is None
        assert store.cached_bytes == 8

    def test_put__span_larger_than_the_bound(self) -> None:
        store = SpanStore(max_bytes=4)
        store.put(uri=_URI, offset=0, data=b"aaaaa")

        assert store.get(uri=_URI, offset=0, length=1) is None
        assert store.cached_bytes == 0

    def test_put__same_span_twice(self) -> None:
        store = SpanStore(max_bytes=100)
        store.put(uri=_URI, offset=0, data=b"aaaa")
        store.put(uri=_URI, offset=0, data=b"aaaa")

        assert store.cached_bytes == 4

    def test_clear(self) -> None:
        store = SpanStore(max_bytes=100)
        store.put(uri=_URI, offset=0, data=b"aaaa")
        store.clear()

        assert store.get(uri=_URI, offset=0, length=4) is None
        assert store.cached_bytes == 0
