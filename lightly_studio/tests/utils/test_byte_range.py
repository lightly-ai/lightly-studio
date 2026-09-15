"""Tests for utils.byte_range."""

from __future__ import annotations

import asyncio
from typing import Any, cast

from fastapi import Request
from fastapi.responses import StreamingResponse
from pytest_mock import MockerFixture

from lightly_studio.api.routes.api import status
from lightly_studio.utils.byte_range import FileInfo, file_info, parse_range_header, serve_file

# --- file_info ---


def test_file_info__uses_etag(mocker: MockerFixture) -> None:
    fs = _make_fs_mock(mocker=mocker, size=1024, etag='"abc123"')
    mocker.patch("fsspec.core.url_to_fs", return_value=(fs, "/path/file.mcap"))
    result = file_info("/path/file.mcap")
    assert result == FileInfo(size_bytes=1024, etag="abc123")


def test_file_info__omits_unreliable_validator(mocker: MockerFixture) -> None:
    fs = _make_fs_mock(mocker=mocker, size=256)
    mocker.patch("fsspec.core.url_to_fs", return_value=(fs, "/path/file.mcap"))
    result = file_info("/path/file.mcap")
    assert result == FileInfo(size_bytes=256, etag=None)


# --- parse_range_header ---


def test_parse_range_header__full_range() -> None:
    result = parse_range_header(range_header="bytes=0-99", file_size=200)
    assert result == (0, 99)


def test_parse_range_header__open_end() -> None:
    result = parse_range_header(range_header="bytes=50-", file_size=200)
    assert result == (50, 199)


def test_parse_range_header__open_start() -> None:
    result = parse_range_header(range_header="bytes=-100", file_size=200)
    assert result == (100, 199)


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
    assert parse_range_header(range_header="bytes=0-200", file_size=200) == (0, 199)


def test_parse_range_header__start_beyond_file() -> None:
    assert parse_range_header(range_header="bytes=200-", file_size=200) is None


def test_parse_range_header__zero_suffix() -> None:
    assert parse_range_header(range_header="bytes=-0", file_size=200) is None


def test_parse_range_header__non_numeric() -> None:
    assert parse_range_header(range_header="bytes=abc-def", file_size=200) is None


def test_serve_file__full_response(mocker: MockerFixture) -> None:
    fs = _make_fs_mock(mocker=mocker, size=3, etag='"abc"')
    handle = mocker.MagicMock()
    handle.read.side_effect = [b"abc", b""]
    fs.open.return_value = handle
    mocker.patch("fsspec.core.url_to_fs", return_value=(fs, "/path/file.mcap"))

    response = serve_file("/path/file.mcap", _request(mocker), None, "application/octet-stream")

    assert response.status_code == status.HTTP_STATUS_OK
    assert response.headers["content-length"] == "3"
    assert response.headers["etag"] == '"abc"'
    assert response.headers["accept-ranges"] == "bytes"
    assert asyncio.run(_read_response(cast(StreamingResponse, response))) == b"abc"


def test_serve_file__partial_response_and_stream(mocker: MockerFixture) -> None:
    fs = _make_fs_mock(mocker=mocker, size=5, etag='"abc"')
    handle = mocker.MagicMock()
    handle.read.side_effect = [b"bc", b""]
    fs.open.return_value = handle
    mocker.patch("fsspec.core.url_to_fs", return_value=(fs, "/path/file.mcap"))

    response = serve_file("/path/file.mcap", _request(mocker), "bytes=1-2", "text/plain")

    assert response.status_code == status.HTTP_STATUS_PARTIAL_CONTENT
    assert response.headers["content-range"] == "bytes 1-2/5"
    assert response.headers["content-length"] == "2"
    assert asyncio.run(_read_response(cast(StreamingResponse, response))) == b"bc"


def test_serve_file__precondition_and_unsatisfiable_range(mocker: MockerFixture) -> None:
    fs = _make_fs_mock(mocker=mocker, size=5, etag='"abc"')
    mocker.patch("fsspec.core.url_to_fs", return_value=(fs, "/path/file.mcap"))

    precondition = serve_file("/path/file.mcap", _request(mocker), None, "text/plain", '"old"')
    unsatisfiable = serve_file("/path/file.mcap", _request(mocker), "bytes=5-", "text/plain")

    assert precondition.status_code == status.HTTP_STATUS_PRECONDITION_FAILED
    assert unsatisfiable.status_code == status.HTTP_STATUS_RANGE_NOT_SATISFIABLE
    assert unsatisfiable.headers["content-range"] == "bytes */5"


def test_serve_file__if_match_wildcard_and_list(mocker: MockerFixture) -> None:
    fs = _make_fs_mock(mocker=mocker, size=5, etag='"abc"')
    handle = mocker.MagicMock()
    fs.open.return_value = handle
    mocker.patch("fsspec.core.url_to_fs", return_value=(fs, "/path/file.mcap"))

    wildcard = serve_file("/path/file.mcap", _request(mocker), None, "text/plain", "*")
    tag_list = serve_file("/path/file.mcap", _request(mocker), None, "text/plain", '"old", "abc"')

    assert wildcard.status_code == status.HTTP_STATUS_OK
    assert tag_list.status_code == status.HTTP_STATUS_OK


def _make_fs_mock(mocker: MockerFixture, size: int, etag: str | None = None) -> Any:
    fs = mocker.MagicMock()
    info: dict[str, object] = {"size": size}
    if etag is not None:
        info["ETag"] = etag
    fs.info.return_value = info
    return fs


def _request(mocker: MockerFixture) -> Request:
    request = mocker.MagicMock(spec=Request)
    request.is_disconnected = mocker.AsyncMock(return_value=False)
    return cast(Request, request)


async def _read_response(response: StreamingResponse) -> bytes:
    chunks: list[bytes] = []
    async for chunk in response.body_iterator:
        chunks.append(cast(bytes, chunk))
    return b"".join(chunks)
