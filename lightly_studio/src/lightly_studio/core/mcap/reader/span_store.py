"""Stores byte spans of files and serves the reads that fall inside them."""

from __future__ import annotations

import bisect
from collections import OrderedDict


class SpanStore:
    """Byte spans of files, bounded in size, that drop the least recently used span.

    A read is served from any stored span that contains it, so one download of a whole
    MCAP chunk serves the reads of its header and of its body.

    The store is not thread-safe. The caller holds a lock.

    Attributes:
        cached_bytes: How many bytes are stored.
    """

    def __init__(self, max_bytes: int) -> None:
        """Starts an empty store.

        Args:
            max_bytes: The most bytes to keep. A span larger than this is not stored.
        """
        self.cached_bytes = 0
        self._max_bytes = max_bytes
        self._spans: OrderedDict[tuple[str, int, int], bytes] = OrderedDict()
        # The (start, end) of the stored spans of each URI, in ascending order.
        self._bounds_by_uri: dict[str, list[tuple[int, int]]] = {}
        # No stored span is longer, so a span that contains an offset starts at most
        # this many bytes before it.
        self._longest_span = 0

    def get(self, uri: str, offset: int, length: int) -> bytes | None:
        """Returns the bytes at a range, from a stored span that contains the range.

        Args:
            uri: The URI of the file.
            offset: The first byte of the range.
            length: The number of bytes of the range.

        Returns:
            The bytes at the range, or `None` if no stored span contains it. Fewer
            bytes when the span ends at the end of the file.
        """
        bounds = self._containing_bounds(uri=uri, offset=offset, end=offset + length)
        if bounds is None:
            return None
        key = (uri, *bounds)
        self._spans.move_to_end(key)
        data = self._spans[key]
        local_start = offset - bounds[0]
        if local_start == 0 and length >= len(data):
            return data
        return data[local_start : local_start + length]

    def put(self, uri: str, offset: int, data: bytes) -> None:
        """Stores a span and drops the least recently used spans past the bound.

        Args:
            uri: The URI of the file.
            offset: The first byte of the span.
            data: The bytes of the span.
        """
        if len(data) > self._max_bytes:
            return
        key = (uri, offset, offset + len(data))
        if key in self._spans:
            self._spans.move_to_end(key)
            return
        self._spans[key] = data
        bisect.insort(self._bounds_by_uri.setdefault(uri, []), key[1:])
        self.cached_bytes += len(data)
        self._longest_span = max(self._longest_span, len(data))
        while self.cached_bytes > self._max_bytes:
            self._drop_oldest()

    def clear(self) -> None:
        """Drops every span."""
        self._spans.clear()
        self._bounds_by_uri.clear()
        self.cached_bytes = 0
        self._longest_span = 0

    def _containing_bounds(self, uri: str, offset: int, end: int) -> tuple[int, int] | None:
        """Returns the bounds of a stored span that contains `[offset, end)`."""
        bounds = self._bounds_by_uri.get(uri)
        if not bounds:
            return None
        first = bisect.bisect_left(bounds, (offset - self._longest_span, 0))
        last = bisect.bisect_right(bounds, (offset, end + self._longest_span))
        for start, span_end in bounds[first:last]:
            if start <= offset and end <= span_end:
                return start, span_end
        return None

    def _drop_oldest(self) -> None:
        """Drops the least recently used span."""
        (uri, start, end), data = self._spans.popitem(last=False)
        self.cached_bytes -= len(data)
        bounds = self._bounds_by_uri[uri]
        del bounds[bisect.bisect_left(bounds, (start, end))]
        if not bounds:
            del self._bounds_by_uri[uri]
