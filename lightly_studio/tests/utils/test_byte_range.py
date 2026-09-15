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
    assert result == FileInfo(path="/path/file.mcap", size_bytes=1024, etag="abc123")


def test_file_info__omits_unreliable_validator(mocker: MockerFixture) -> None:
    fs = _make_fs_mock(mocker=mocker, size=256)
    mocker.patch("fsspec.core.url_to_fs", return_value=(fs, "/path/file.mcap"))
    result = file_info("/path/file.mcap")
    assert result == FileInfo(path="/path/file.mcap", size_bytes=256, etag=None)


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
    info = FileInfo(path="/path/file.mcap", size_bytes=3, etag="abc")

    response = serve_file(
        info=info,
        request=_request(mocker),
        range_header=None,
        media_type="application/octet-stream",
    )

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
    info = FileInfo(path="/path/file.mcap", size_bytes=5, etag="abc")

    response = serve_file(
        info=info,
        request=_request(mocker),
        range_header="bytes=1-2",
        media_type="text/plain",
    )

    assert response.status_code == status.HTTP_STATUS_PARTIAL_CONTENT
    assert response.headers["content-range"] == "bytes 1-2/5"
    assert response.headers["content-length"] == "2"
    assert asyncio.run(_read_response(cast(StreamingResponse, response))) == b"bc"


def test_serve_file__precondition_and_unsatisfiable_range(mocker: MockerFixture) -> None:
    fs = _make_fs_mock(mocker=mocker, size=5, etag='"abc"')
    mocker.patch("fsspec.core.url_to_fs", return_value=(fs, "/path/file.mcap"))
    info = FileInfo(path="/path/file.mcap", size_bytes=5, etag="abc")

    precondition = serve_file(
        info=info,
        request=_request(mocker),
        range_header=None,
        media_type="text/plain",
        if_match='"old"',
    )
    unsatisfiable = serve_file(
        info=info, request=_request(mocker), range_header="bytes=5-", media_type="text/plain"
    )

    assert precondition.status_code == status.HTTP_STATUS_PRECONDITION_FAILED
    assert unsatisfiable.status_code == status.HTTP_STATUS_RANGE_NOT_SATISFIABLE
    assert unsatisfiable.headers["content-range"] == "bytes */5"


def test_serve_file__if_match_wildcard_and_list(mocker: MockerFixture) -> None:
    fs = _make_fs_mock(mocker=mocker, size=5, etag='"abc"')
    handle = mocker.MagicMock()
    fs.open.return_value = handle
    mocker.patch("fsspec.core.url_to_fs", return_value=(fs, "/path/file.mcap"))
    info = FileInfo(path="/path/file.mcap", size_bytes=5, etag="abc")

    wildcard = serve_file(
        info=info,
        request=_request(mocker),
        range_header=None,
        media_type="text/plain",
        if_match="*",
    )
    tag_list = serve_file(
        info=info,
        request=_request(mocker),
        range_header=None,
        media_type="text/plain",
        if_match='"old", "abc"',
    )

    assert wildcard.status_code == status.HTTP_STATUS_OK
    assert tag_list.status_code == status.HTTP_STATUS_OK


def test_serve_file__if_match_explicit_tag_412_when_no_revision(mocker: MockerFixture) -> None:
    """Explicit If-Match tags must 412 even when the file has no ETag."""
    fs = _make_fs_mock(mocker=mocker, size=5)
    mocker.patch("fsspec.core.url_to_fs", return_value=(fs, "/path/file.mcap"))
    info = FileInfo(path="/path/file.mcap", size_bytes=5, etag=None)

    response = serve_file(
        info=info,
        request=_request(mocker),
        range_header=None,
        media_type="text/plain",
        if_match='"some-tag"',
    )

    assert response.status_code == status.HTTP_STATUS_PRECONDITION_FAILED


def test_serve_file__if_match_wildcard_passes_when_no_revision(mocker: MockerFixture) -> None:
    """Wildcard If-Match must pass through even when the file has no ETag."""
    fs = _make_fs_mock(mocker=mocker, size=5)
    handle = mocker.MagicMock()
    fs.open.return_value = handle
    mocker.patch("fsspec.core.url_to_fs", return_value=(fs, "/path/file.mcap"))
    info = FileInfo(path="/path/file.mcap", size_bytes=5, etag=None)

    response = serve_file(
        info=info,
        request=_request(mocker),
        range_header=None,
        media_type="text/plain",
        if_match="*",
    )

    assert response.status_code == status.HTTP_STATUS_OK


def test_serve_file__multi_range_falls_back_to_full_response(mocker: MockerFixture) -> None:
    """Multi-range requests must fall back to a full 200, not 416."""
    fs = _make_fs_mock(mocker=mocker, size=5, etag='"abc"')
    handle = mocker.MagicMock()
    handle.read.side_effect = [b"hello", b""]
    fs.open.return_value = handle
    mocker.patch("fsspec.core.url_to_fs", return_value=(fs, "/path/file.mcap"))
    info = FileInfo(path="/path/file.mcap", size_bytes=5, etag="abc")

    response = serve_file(
        info=info,
        request=_request(mocker),
        range_header="bytes=0-1,3-4",
        media_type="text/plain",
    )

    assert response.status_code == status.HTTP_STATUS_OK


def test_serve_file__if_match_etag_with_comma(mocker: MockerFixture) -> None:
    """ETags containing commas must be parsed correctly in If-Match."""
    fs = _make_fs_mock(mocker=mocker, size=5, etag='"a,b"')
    handle = mocker.MagicMock()
    fs.open.return_value = handle
    mocker.patch("fsspec.core.url_to_fs", return_value=(fs, "/path/file.mcap"))
    info = FileInfo(path="/path/file.mcap", size_bytes=5, etag="a,b")

    response = serve_file(
        info=info,
        request=_request(mocker),
        range_header=None,
        media_type="text/plain",
        if_match='"a,b"',
    )

    assert response.status_code == status.HTTP_STATUS_OK


def test_serve_file__disconnection_stops_stream(mocker: MockerFixture) -> None:
    """Stream must stop without error when the client disconnects."""
    fs = _make_fs_mock(mocker=mocker, size=10, etag='"abc"')
    handle = mocker.MagicMock()
    handle.read.return_value = b"x" * 10
    fs.open.return_value = handle
    mocker.patch("fsspec.core.url_to_fs", return_value=(fs, "/path/file.mcap"))
    info = FileInfo(path="/path/file.mcap", size_bytes=10, etag="abc")
    request = mocker.MagicMock(spec=Request)
    request.is_disconnected = mocker.AsyncMock(return_value=True)

    response = serve_file(
        info=info,
        request=cast(Request, request),
        range_header=None,
        media_type="text/plain",
    )

    data = asyncio.run(_read_response(cast(StreamingResponse, response)))
    assert data == b""


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
