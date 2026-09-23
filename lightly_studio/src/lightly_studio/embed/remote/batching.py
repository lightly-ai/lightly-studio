"""Splits a batch into the chunks that an embedding server accepts.

A server reports a ``max_batch_size`` and a ``max_request_bytes`` in ``/v1/describe``, and
refuses a request over either one. Splitting here keeps the bytes of a batch that is too
large off the network, and it works for any input kind: the caller says how to measure an
item, so text and encoded bytes use the same splitter.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Iterator, Sequence
from typing import TypeVar

# What one item adds around its own data: a multipart boundary with the headers of the
# part, or the quotes of a JSON string. Large enough for both forms.
ITEM_ENVELOPE_BYTES = 256

_ItemT = TypeVar("_ItemT")


def split_batches(
    items: Sequence[_ItemT],
    max_batch_size: int,
    max_request_bytes: int,
    size_of: Callable[[_ItemT], int],
) -> Iterator[tuple[int, list[_ItemT]]]:
    """Split a batch into the chunks that the server accepts.

    The count is exact and the size is an estimate, because httpx writes the envelope, so
    the 413 of the server stays the authority. An item that fills the limit on its own
    goes alone.

    Args:
        items: The items to embed. An empty batch yields nothing, so it sends no request.
        max_batch_size: The largest number of items in one request. ``ServerLimits``
            validates that it is positive.
        max_request_bytes: The largest body that the server accepts. ``ServerLimits``
            validates that it is positive.
        size_of: The bytes that one item puts in the body, without its envelope.

    Yields:
        Each chunk together with the index of its first item in ``items``. That index
        turns the ``kept_indices`` of a chunk back into indices of the whole batch.
    """
    offset = 0
    chunk: list[_ItemT] = []
    chunk_bytes = 0
    for index, item in enumerate(items):
        item_bytes = size_of(item) + ITEM_ENVELOPE_BYTES
        full = len(chunk) >= max_batch_size or chunk_bytes + item_bytes > max_request_bytes
        if chunk and full:
            yield offset, chunk
            offset = index
            chunk = []
            chunk_bytes = 0
        chunk.append(item)
        chunk_bytes += item_bytes
    if chunk:
        yield offset, chunk


def text_size(text: str) -> int:
    """The bytes that one string puts in a JSON body, without its envelope."""
    encoded = json.dumps(text, ensure_ascii=False)
    return len(encoded[1:-1].encode("utf-8"))
