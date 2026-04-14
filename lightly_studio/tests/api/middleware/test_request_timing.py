"""Test module for RequestTimingMiddleware."""

from __future__ import annotations

import asyncio
import logging
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from lightly_studio.api.middleware import RequestTimingMiddleware


@pytest.fixture
def app_with_timing_middleware() -> FastAPI:
    """Create a FastAPI app with RequestTimingMiddleware for testing."""
    test_app = FastAPI()
    test_app.add_middleware(
        RequestTimingMiddleware,
        warning_threshold_ms=100,
        error_threshold_ms=200,
    )

    @test_app.get("/fast")
    async def fast_endpoint() -> dict[str, str]:
        """Fast endpoint that completes in < 100ms."""
        return {"status": "ok"}

    @test_app.get("/slow")
    async def slow_endpoint() -> dict[str, str]:
        """Slow endpoint that takes ~150ms (warning threshold)."""
        await asyncio.sleep(0.15)
        return {"status": "ok"}

    @test_app.get("/very_slow")
    async def very_slow_endpoint() -> dict[str, str]:
        """Very slow endpoint that takes ~250ms (error threshold)."""
        await asyncio.sleep(0.25)
        return {"status": "ok"}

    return test_app


def test_request_timing_middleware_fast_request_debug_log(
    app_with_timing_middleware: FastAPI, caplog: pytest.LogCaptureFixture
) -> None:
    """Test that fast requests are logged at debug level."""
    client = TestClient(app_with_timing_middleware)

    with caplog.at_level(logging.DEBUG):
        response = client.get("/fast")

    assert response.status_code == 200
    assert any("GET /fast completed in" in record.message for record in caplog.records)
    debug_records = [record for record in caplog.records if record.levelname == "DEBUG"]
    assert len(debug_records) > 0


def test_request_timing_middleware_slow_request_warning_log(
    app_with_timing_middleware: FastAPI, caplog: pytest.LogCaptureFixture
) -> None:
    """Test that slow requests exceeding warning threshold are logged as warning."""
    client = TestClient(app_with_timing_middleware)

    with caplog.at_level(logging.WARNING):
        response = client.get("/slow")

    assert response.status_code == 200
    warning_records = [record for record in caplog.records if record.levelname == "WARNING"]
    assert len(warning_records) == 1
    assert "GET /slow completed in" in warning_records[0].message
    assert "ms" in warning_records[0].message


def test_request_timing_middleware_very_slow_request_error_log(
    app_with_timing_middleware: FastAPI, caplog: pytest.LogCaptureFixture
) -> None:
    """Test that very slow requests exceeding error threshold are logged as error."""
    client = TestClient(app_with_timing_middleware)

    with caplog.at_level(logging.ERROR):
        response = client.get("/very_slow")

    assert response.status_code == 200
    error_records = [record for record in caplog.records if record.levelname == "ERROR"]
    assert len(error_records) == 1
    assert "GET /very_slow completed in" in error_records[0].message
    assert "ms" in error_records[0].message


def test_request_timing_middleware_custom_thresholds() -> None:
    """Test that custom thresholds are respected."""
    app = FastAPI()
    app.add_middleware(
        RequestTimingMiddleware,
        warning_threshold_ms=50,
        error_threshold_ms=100,
    )

    @app.get("/endpoint")
    async def endpoint() -> dict[str, str]:
        await asyncio.sleep(0.075)  # 75ms - between thresholds
        return {"status": "ok"}

    client = TestClient(app)
    mock_logger = MagicMock()

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr("lightly_studio.api.middleware.request_timing.logger", mock_logger)
        response = client.get("/endpoint")

    assert response.status_code == 200
    # Should log at warning level (75ms > 50ms but < 100ms)
    mock_logger.warning.assert_called_once()
    mock_logger.error.assert_not_called()
