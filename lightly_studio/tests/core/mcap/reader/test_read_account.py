from __future__ import annotations

from lightly_studio.core.mcap.reader import read_account


def test_describe() -> None:
    read_account.reset()
    read_account.note_load(byte_count=100, seconds=0.25)
    read_account.note_wait(byte_count=20, seconds=0.5)
    read_account.note_hit(byte_count=3)
    read_account.note_hit(byte_count=4)

    assert read_account.describe() == (
        "loaded 100 B in 250 ms, waited for 20 B for 500 ms, cache hit 7 B"
    )


def test_describe__no_read() -> None:
    read_account.reset()

    assert read_account.describe() == "no chunk read"
