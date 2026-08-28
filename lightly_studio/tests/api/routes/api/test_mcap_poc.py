"""Tests for the MCAP processing proof-of-concept API."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pytest_mock import MockerFixture

from lightly_studio.api.routes.api import mcap_poc
from lightly_studio.dataset import env
from lightly_studio.integrations.mcap_poc import reader


def test_get_source_returns_browser_direct_metadata(
    test_client: TestClient, mocker: MockerFixture
) -> None:
    mocker.patch.object(env, "LIGHTLY_STUDIO_MCAP_POC_SOURCE", "/data/example.mcap")
    mocker.patch.object(
        reader,
        "describe_source",
        return_value=reader.McapSourceDescription(
            size_bytes=1024,
            version="version-1",
            topics=[
                reader.McapTopic(topic="/lidar/points", message_count=10, first_log_time_ns=2**63)
            ],
        ),
    )

    response = test_client.get("/api/mcap-poc/source")

    assert response.status_code == 200
    assert response.json() == {
        "direct_url": "http://testserver/api/mcap-poc/source/content",
        "size_bytes": 1024,
        "version": "version-1",
        "topics": [
            {
                "topic": "/lidar/points",
                "message_count": 10,
                "first_log_time_ns": str(2**63),
            }
        ],
    }


def test_get_frame_returns_packed_points_and_metrics(
    test_client: TestClient, mocker: MockerFixture
) -> None:
    mocker.patch.object(env, "LIGHTLY_STUDIO_MCAP_POC_SOURCE", "/data/example.mcap")
    read_frame = mocker.patch.object(reader, "read_point_cloud_frame", return_value=_frame_result())

    response = test_client.get(
        "/api/mcap-poc/frame", params={"topic": "/lidar/points", "timestamp_ns": 100}
    )

    assert response.status_code == 200
    assert response.content == bytes(32)
    assert response.headers["X-MCAP-Point-Count"] == "2"
    assert response.headers["X-MCAP-Source-Bytes"] == "456"
    assert response.headers["X-MCAP-Backend-Peak-Bytes"] == "789"
    assert response.headers["X-MCAP-Backend-Index-Ms"] == "0.000"
    assert response.headers["X-MCAP-Backend-Decode-Ms"] == "3.400"
    assert response.headers["X-MCAP-Index-Cached"] == "1"
    assert read_frame.call_args.kwargs["reuse_index"] is True


def test_get_frame_can_request_a_cold_read(test_client: TestClient, mocker: MockerFixture) -> None:
    mocker.patch.object(env, "LIGHTLY_STUDIO_MCAP_POC_SOURCE", "/data/example.mcap")
    read_frame = mocker.patch.object(
        reader,
        "read_point_cloud_frame",
        return_value=_frame_result(index_cached=False, index_time_ms=80.0),
    )

    response = test_client.get(
        "/api/mcap-poc/frame",
        params={"topic": "/lidar/points", "timestamp_ns": 100, "reuse_index": "false"},
    )

    assert response.status_code == 200
    assert response.headers["X-MCAP-Index-Cached"] == "0"
    assert response.headers["X-MCAP-Backend-Index-Ms"] == "80.000"
    assert read_frame.call_args.kwargs["reuse_index"] is False


def test_reset_clears_the_cached_index(test_client: TestClient, mocker: MockerFixture) -> None:
    clear = mocker.patch.object(reader, "clear_source_cache")

    response = test_client.post("/api/mcap-poc/reset")

    assert response.status_code == 204
    clear.assert_called_once_with()


def test_serve_local_source_supports_byte_ranges(
    test_client: TestClient, mocker: MockerFixture, tmp_path: Path
) -> None:
    path = tmp_path / "example.mcap"
    content = bytes(range(256)) * 16
    path.write_bytes(content)
    mocker.patch.object(env, "LIGHTLY_STUDIO_MCAP_POC_SOURCE", str(path))

    response = test_client.get("/api/mcap-poc/source/content", headers={"Range": "bytes=100-2147"})

    assert response.status_code == 206
    assert response.content == content[100:2148]
    assert response.headers["Content-Range"] == "bytes 100-2147/4096"
    assert "Content-Encoding" not in response.headers


def test_configured_source_is_required(mocker: MockerFixture) -> None:
    mocker.patch.object(env, "LIGHTLY_STUDIO_MCAP_POC_SOURCE", None)

    with pytest.raises(ValueError, match="LIGHTLY_STUDIO_MCAP_POC_SOURCE"):
        mcap_poc._configured_source()


def _frame_result(index_cached: bool = True, index_time_ms: float = 0.0) -> reader.McapFrameResult:
    return reader.McapFrameResult(
        content=bytes(32),
        point_count=2,
        log_time_ns=123,
        bytes_read=456,
        read_count=7,
        wall_time_ms=8.1,
        index_time_ms=index_time_ms,
        decode_time_ms=3.4,
        cpu_time_ms=6.2,
        peak_memory_bytes=789,
        index_cached=index_cached,
    )
