"""Tests for utils.byte_range."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from lightly_studio.utils.byte_range import FileInfo, file_info, parse_range_header

# --- parse_range_header ---


def test_parse_range_header__full_range() -> None:
    result = parse_range_header(range_header="bytes=0-99", file_size=200)
    assert result == (0, 99)


def test_parse_range_header__open_end() -> None:
    result = parse_range_header(range_header="bytes=50-", file_size=200)
    assert result == (50, 199)


def test_parse_range_header__open_start() -> None:
    result = parse_range_header(range_header="bytes=-100", file_size=200)
    assert result == (0, 100)


def test_parse_range_header__none() -> None:
    assert parse_range_header(range_header=None, file_size=200) is None


def test_parse_range_header__empty_string() -> None:
    assert parse_range_header(range_header="", file_size=200) is None


def test_parse_range_header__wrong_unit() -> None:
    assert parse_range_header(range_header="items=0-10", file_size=200) is None


def test_parse_range_header__no_dash() -> None:
    assert parse_range_header(range_header="bytes=050", file_size=200) is None


def test_parse_range_header__start_beyond_end() -> None:
    assert parse_range_header(range_header="bytes=100-50", file_size=200) is None


def test_parse_range_header__end_at_file_boundary() -> None:
    result = parse_range_header(range_header="bytes=0-199", file_size=200)
    assert result == (0, 199)


def test_parse_range_header__end_beyond_file() -> None:
    assert parse_range_header(range_header="bytes=0-200", file_size=200) is None


def test_parse_range_header__non_numeric() -> None:
    assert parse_range_header(range_header="bytes=abc-def", file_size=200) is None


# --- file_info ---


def _make_fs_mock(size: int, etag: str | None = None, mtime: float | None = None) -> MagicMock:
    fs = MagicMock()
    info: dict[str, object] = {"size": size}
    if etag is not None:
        info["ETag"] = etag
    if mtime is not None:
        info["mtime"] = mtime
    fs.info.return_value = info
    return fs


def test_file_info__uses_etag() -> None:
    fs = _make_fs_mock(size=1024, etag='"abc123"')
    with patch("fsspec.core.url_to_fs", return_value=(fs, "/path/file.mcap")):
        result = file_info("/path/file.mcap")
    assert result == FileInfo(size_bytes=1024, etag="abc123")


def test_file_info__falls_back_to_mtime() -> None:
    fs = _make_fs_mock(size=512, mtime=1700000000.0)
    with patch("fsspec.core.url_to_fs", return_value=(fs, "/path/file.mcap")):
        result = file_info("/path/file.mcap")
    assert result.size_bytes == 512
    assert len(result.etag) == 32  # sha256 hex prefix


def test_file_info__falls_back_to_size_only() -> None:
    fs = _make_fs_mock(size=256)
    with patch("fsspec.core.url_to_fs", return_value=(fs, "/path/file.mcap")):
        result = file_info("/path/file.mcap")
    assert result == FileInfo(size_bytes=256, etag="256")
