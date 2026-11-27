"""Test module for RequestTimingMiddleware."""

from __future__ import annotations

import logging

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pytest_mock import MockerFixture

from lightly_studio.api.middleware import RequestTimingMiddleware, request_timing


@pytest.fixture
def app_with_timing_middleware() -> FastAPI:
    """Create a FastAPI app with RequestTimingMiddleware for testing."""
    test_app = FastAPI()
    test_app.add_middleware(RequestTimingMiddleware, error_threshold_ms=50, fail_on_error=True)

    @test_app.get("/fast")
    async def fast_endpoint() -> dict[str, str]:
        return {"status": "ok"}

    @test_app.get("/slow")
    async def slow_endpoint() -> dict[str, str]:
        return {"status": "ok"}

    return test_app


def test_request_timing__has_no_error_logs_for_fast_requests(
    app_with_timing_middleware: FastAPI, caplog: pytest.LogCaptureFixture, mocker: MockerFixture
) -> None:
    """Test that fast requests do not generate error logs."""
    _patch_duration_ms(mocker=mocker, duration_ms=10)
    client = TestClient(app_with_timing_middleware)

    with caplog.at_level(logging.DEBUG):
        response = client.get("/fast")

    assert response.status_code == 200
    error_records = [record for record in caplog.records if record.levelname == "ERROR"]
    assert len(error_records) == 0


def test_request_timing__fails_slow_requests(
    app_with_timing_middleware: FastAPI, mocker: MockerFixture
) -> None:
    """Test that requests exceeding error threshold fail when fail_on_error is True."""
    _patch_duration_ms(mocker=mocker, duration_ms=80)
    client = TestClient(app_with_timing_middleware)
    response = client.get("/slow")

    assert response.status_code == 503
    assert "detail" in response.json()
    assert "exceeded 50ms" in response.json()["detail"]


def test_request_timing__has_only_error_logs_for_slow_requests(
    caplog: pytest.LogCaptureFixture, mocker: MockerFixture
) -> None:
    """Test that very slow requests exceeding error threshold are logged as error."""
    app = FastAPI()
    app.add_middleware(
        RequestTimingMiddleware,
        error_threshold_ms=50,
    )

    @app.get("/slow")
    async def slow_endpoint() -> dict[str, str]:
        return {"status": "ok"}

    _patch_duration_ms(mocker=mocker, duration_ms=80)
    client = TestClient(app)

    with caplog.at_level(logging.ERROR):
        response = client.get("/slow")

    assert response.status_code == 200
    error_records = [record for record in caplog.records if record.levelname == "ERROR"]
    assert len(error_records) == 1
    assert "GET /slow completed in 80.00ms" in error_records[0].message


def _patch_duration_ms(mocker: MockerFixture, duration_ms: float) -> None:
    """Make the middleware measure the given request duration."""
    # Patch only the module reference, other code keeps the real clock
    mock_time = mocker.patch.object(request_timing, "time")
    mock_time.perf_counter.side_effect = [0.0, duration_ms / 1000]
