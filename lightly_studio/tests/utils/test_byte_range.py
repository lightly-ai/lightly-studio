"""Tests for utils.byte_range."""

from __future__ import annotations

import asyncio
from typing import Any, cast

from fastapi import Request, Response
from fastapi.responses import StreamingResponse
from pytest_mock import MockerFixture

from lightly_studio.api.routes.api import status
from lightly_studio.utils.byte_range import FileInfo, file_info, parse_range_header, serve_file

_PATH = "/path/file.mcap"

# --- file_info ---


def test_file_info__uses_etag(mocker: MockerFixture) -> None:
    _patch_fs(mocker=mocker, size=1024, etag='"abc123"')
    assert file_info(_PATH) == FileInfo(path=_PATH, size_bytes=1024, etag="abc123")


def test_file_info__omits_unreliable_validator(mocker: MockerFixture) -> None:
    _patch_fs(mocker=mocker, size=256)
    assert file_info(_PATH) == FileInfo(path=_PATH, size_bytes=256, etag=None)


# --- parse_range_header ---


def test_parse_range_header__full_range() -> None:
    assert parse_range_header(range_header="bytes=0-99", file_size=200) == (0, 99)


def test_parse_range_header__open_end() -> None:
    assert parse_range_header(range_header="bytes=50-", file_size=200) == (50, 199)


def test_parse_range_header__open_start() -> None:
    assert parse_range_header(range_header="bytes=-100", file_size=200) == (100, 199)


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
    assert parse_range_header(range_header="bytes=0-199", file_size=200) == (0, 199)


def test_parse_range_header__end_beyond_file() -> None:
    assert parse_range_header(range_header="bytes=0-200", file_size=200) == (0, 199)


def test_parse_range_header__start_beyond_file() -> None:
    assert parse_range_header(range_header="bytes=200-", file_size=200) is None


def test_parse_range_header__zero_suffix() -> None:
    assert parse_range_header(range_header="bytes=-0", file_size=200) is None


def test_parse_range_header__non_numeric() -> None:
    assert parse_range_header(range_header="bytes=abc-def", file_size=200) is None


# --- serve_file ---


def test_serve_file__full_response(mocker: MockerFixture) -> None:
    _patch_fs(mocker=mocker, size=3, etag='"abc"', read_chunks=[b"abc", b""])
    info = FileInfo(path=_PATH, size_bytes=3, etag="abc")

    response = _serve(mocker=mocker, info=info, range_header=None)

    assert response.status_code == status.HTTP_STATUS_OK
    assert response.headers["content-length"] == "3"
    assert response.headers["etag"] == '"abc"'
    assert response.headers["accept-ranges"] == "bytes"
    assert _read(response) == b"abc"


def test_serve_file__partial_response(mocker: MockerFixture) -> None:
    _patch_fs(mocker=mocker, size=5, etag='"abc"', read_chunks=[b"bc", b""])
    info = FileInfo(path=_PATH, size_bytes=5, etag="abc")

    response = _serve(mocker=mocker, info=info, range_header="bytes=1-2")

    assert response.status_code == status.HTTP_STATUS_PARTIAL_CONTENT
    assert response.headers["content-range"] == "bytes 1-2/5"
    assert response.headers["content-length"] == "2"
    assert _read(response) == b"bc"


def test_serve_file__unsatisfiable_range(mocker: MockerFixture) -> None:
    _patch_fs(mocker=mocker, size=5, etag='"abc"')
    info = FileInfo(path=_PATH, size_bytes=5, etag="abc")

    response = _serve(mocker=mocker, info=info, range_header="bytes=5-")

    assert response.status_code == status.HTTP_STATUS_RANGE_NOT_SATISFIABLE
    assert response.headers["content-range"] == "bytes */5"


def test_serve_file__multi_range_falls_back_to_full_response(mocker: MockerFixture) -> None:
    """Multi-range requests fall back to full 200 rather than 416."""
    _patch_fs(mocker=mocker, size=5, etag='"abc"', read_chunks=[b"hello", b""])
    info = FileInfo(path=_PATH, size_bytes=5, etag="abc")

    response = _serve(mocker=mocker, info=info, range_header="bytes=0-1,3-4")

    assert response.status_code == status.HTTP_STATUS_OK


def test_serve_file__if_match_matching_tag(mocker: MockerFixture) -> None:
    _patch_fs(mocker=mocker, size=5, etag='"abc"')
    info = FileInfo(path=_PATH, size_bytes=5, etag="abc")

    assert _serve(mocker=mocker, info=info, if_match='"abc"').status_code == status.HTTP_STATUS_OK


def test_serve_file__if_match_tag_list(mocker: MockerFixture) -> None:
    _patch_fs(mocker=mocker, size=5, etag='"abc"')
    info = FileInfo(path=_PATH, size_bytes=5, etag="abc")

    response = _serve(mocker=mocker, info=info, if_match='"old", "abc"')

    assert response.status_code == status.HTTP_STATUS_OK


def test_serve_file__if_match_wildcard(mocker: MockerFixture) -> None:
    _patch_fs(mocker=mocker, size=5, etag='"abc"')
    info = FileInfo(path=_PATH, size_bytes=5, etag="abc")

    assert _serve(mocker=mocker, info=info, if_match="*").status_code == status.HTTP_STATUS_OK


def test_serve_file__if_match_mismatch(mocker: MockerFixture) -> None:
    _patch_fs(mocker=mocker, size=5, etag='"abc"')
    info = FileInfo(path=_PATH, size_bytes=5, etag="abc")

    response = _serve(mocker=mocker, info=info, if_match='"old"')

    assert response.status_code == status.HTTP_STATUS_PRECONDITION_FAILED


def test_serve_file__if_match_explicit_tag_no_revision(mocker: MockerFixture) -> None:
    """Explicit If-Match tags must 412 even when the file has no ETag."""
    _patch_fs(mocker=mocker, size=5)
    info = FileInfo(path=_PATH, size_bytes=5, etag=None)

    response = _serve(mocker=mocker, info=info, if_match='"some-tag"')

    assert response.status_code == status.HTTP_STATUS_PRECONDITION_FAILED


def test_serve_file__if_match_wildcard_no_revision(mocker: MockerFixture) -> None:
    """Wildcard If-Match passes through even when the file has no ETag."""
    _patch_fs(mocker=mocker, size=5)
    info = FileInfo(path=_PATH, size_bytes=5, etag=None)

    assert _serve(mocker=mocker, info=info, if_match="*").status_code == status.HTTP_STATUS_OK


def test_serve_file__if_match_etag_with_comma(mocker: MockerFixture) -> None:
    """ETags containing commas are parsed correctly in If-Match."""
    _patch_fs(mocker=mocker, size=5, etag='"a,b"')
    info = FileInfo(path=_PATH, size_bytes=5, etag="a,b")

    assert _serve(mocker=mocker, info=info, if_match='"a,b"').status_code == status.HTTP_STATUS_OK


def test_serve_file__disconnection_stops_stream(mocker: MockerFixture) -> None:
    """Stream stops without error when the client disconnects."""
    _patch_fs(mocker=mocker, size=10, etag='"abc"', read_chunks=[b"x" * 10])
    info = FileInfo(path=_PATH, size_bytes=10, etag="abc")
    request = mocker.MagicMock(spec=Request)
    request.is_disconnected = mocker.AsyncMock(return_value=True)

    response = serve_file(
        info=info, request=cast(Request, request), range_header=None, media_type="text/plain"
    )

    assert _read(response) == b""


def _patch_fs(
    mocker: MockerFixture,
    size: int,
    etag: str | None = None,
    read_chunks: list[bytes] | None = None,
) -> Any:
    fs = mocker.MagicMock()
    raw_info: dict[str, object] = {"size": size}
    if etag is not None:
        raw_info["ETag"] = etag
    fs.info.return_value = raw_info
    if read_chunks is not None:
        handle = mocker.MagicMock()
        handle.read.side_effect = read_chunks
        fs.open.return_value = handle
    mocker.patch("fsspec.core.url_to_fs", return_value=(fs, _PATH))
    return fs


def _serve(
    mocker: MockerFixture,
    info: FileInfo,
    range_header: str | None = None,
    if_match: str | None = None,
) -> Response:
    request = mocker.MagicMock(spec=Request)
    request.is_disconnected = mocker.AsyncMock(return_value=False)
    return serve_file(
        info=info,
        request=cast(Request, request),
        range_header=range_header,
        media_type="text/plain",
        if_match=if_match,
    )


def _read(response: Response) -> bytes:
    async def _collect() -> bytes:
        chunks: list[bytes] = []
        async for chunk in cast(StreamingResponse, response).body_iterator:
            chunks.append(cast(bytes, chunk))
        return b"".join(chunks)

    return asyncio.run(_collect())
