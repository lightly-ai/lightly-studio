from __future__ import annotations

from lightly_studio.embed.remote import batching

_MAX_BATCH_SIZE = 999
_MAX_REQUEST_BYTES = 1_000_000


def test_split_batches() -> None:
    chunks = list(
        batching.split_batches(
            items=["a", "b", "c", "d", "e"],
            max_batch_size=2,
            max_request_bytes=_MAX_REQUEST_BYTES,
            size_of=len,
        )
    )

    assert chunks == [(0, ["a", "b"]), (2, ["c", "d"]), (4, ["e"])]


def test_split_batches__exact_multiple() -> None:
    chunks = list(
        batching.split_batches(
            items=["a", "b", "c", "d"],
            max_batch_size=2,
            max_request_bytes=_MAX_REQUEST_BYTES,
            size_of=len,
        )
    )

    assert chunks == [(0, ["a", "b"]), (2, ["c", "d"])]


def test_split_batches__single_chunk() -> None:
    chunks = list(
        batching.split_batches(
            items=["a", "b"],
            max_batch_size=_MAX_BATCH_SIZE,
            max_request_bytes=_MAX_REQUEST_BYTES,
            size_of=len,
        )
    )

    assert chunks == [(0, ["a", "b"])]


def test_split_batches__empty() -> None:
    assert (
        list(
            batching.split_batches(
                items=[],
                max_batch_size=_MAX_BATCH_SIZE,
                max_request_bytes=_MAX_REQUEST_BYTES,
                size_of=len,
            )
        )
        == []
    )


def test_split_batches__request_bytes() -> None:
    # Each item counts its own size plus the envelope, so two fit and three do not.
    limit = 2 * (10 + batching.ITEM_ENVELOPE_BYTES)
    items = ["a" * 10, "b" * 10, "c" * 10]

    chunks = list(
        batching.split_batches(
            items=items,
            max_batch_size=_MAX_BATCH_SIZE,
            max_request_bytes=limit,
            size_of=len,
        )
    )

    assert chunks == [(0, items[:2]), (2, items[2:])]


def test_split_batches__item_over_the_request_limit() -> None:
    # No split makes the middle item fit, so it goes alone.
    items = ["a", "b" * 100, "c"]

    chunks = list(
        batching.split_batches(
            items=items,
            max_batch_size=_MAX_BATCH_SIZE,
            max_request_bytes=batching.ITEM_ENVELOPE_BYTES + 10,
            size_of=len,
        )
    )

    assert chunks == [(0, ["a"]), (1, ["b" * 100]), (2, ["c"])]


def test_text_size() -> None:
    assert batching.text_size(text="a dog") == 5


def test_text_size__outside_ascii() -> None:
    # The wire counts bytes, not characters.
    assert batching.text_size(text="Grüezi") == 7


def test_text_size__escaped_characters() -> None:
    assert batching.text_size(text='a\n"b\\c') == 9
