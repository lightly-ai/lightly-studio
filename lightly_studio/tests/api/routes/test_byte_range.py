"""Tests for shared byte-range serving."""

from lightly_studio.api.routes import byte_range


def test_parse_range_header() -> None:
    assert byte_range.parse_range_header(range_header="bytes=10-19", file_size=100) == (10, 19)


def test_parse_range_header__open_ended() -> None:
    assert byte_range.parse_range_header(range_header="bytes=90-", file_size=100) == (90, 99)


def test_parse_range_header__empty_start_is_zero() -> None:
    # Not a suffix range: this is the behaviour the video endpoint has always had.
    assert byte_range.parse_range_header(range_header="bytes=-20", file_size=100) == (0, 20)


def test_parse_range_header__single_byte() -> None:
    assert byte_range.parse_range_header(range_header="bytes=0-0", file_size=100) == (0, 0)


def test_parse_range_header__absent() -> None:
    assert byte_range.parse_range_header(range_header=None, file_size=100) is None


def test_parse_range_header__unsupported_unit() -> None:
    assert byte_range.parse_range_header(range_header="items=0-9", file_size=100) is None


def test_parse_range_header__malformed() -> None:
    assert byte_range.parse_range_header(range_header="bytes=abc-def", file_size=100) is None
    assert byte_range.parse_range_header(range_header="bytes=0", file_size=100) is None


def test_parse_range_header__past_the_end() -> None:
    assert byte_range.parse_range_header(range_header="bytes=0-100", file_size=100) is None


def test_parse_range_header__reversed() -> None:
    assert byte_range.parse_range_header(range_header="bytes=20-10", file_size=100) is None
