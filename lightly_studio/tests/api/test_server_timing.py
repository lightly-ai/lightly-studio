from __future__ import annotations

import contextvars
import re

import pytest
from fastapi.testclient import TestClient

from lightly_studio.api import app as app_module
from lightly_studio.api import server_timing
from lightly_studio.api.routes.api.status import HTTP_STATUS_OK

_SERVER_TIMING_PATTERN = re.compile(
    r"total;dur=(?P<total>\d+(\.\d+)?),\s*"
    r"db;dur=(?P<db>\d+(\.\d+)?),\s*"
    r"backend;dur=(?P<backend>\d+(\.\d+)?)"
)


def test_server_timing_header__enabled(
    monkeypatch: pytest.MonkeyPatch,
    test_client: TestClient,
) -> None:
    monkeypatch.setattr(app_module, "LIGHTLY_STUDIO_SERVER_TIMING_ENABLED", True)

    response = test_client.get("/api/collections")
    assert response.status_code == HTTP_STATUS_OK

    server_timing_header = response.headers.get("server-timing")
    assert server_timing_header is not None

    match = _SERVER_TIMING_PATTERN.fullmatch(server_timing_header)
    assert match is not None
    assert float(match.group("total")) >= 0
    assert float(match.group("db")) >= 0
    assert float(match.group("backend")) >= 0


def test_server_timing_header__disabled(
    monkeypatch: pytest.MonkeyPatch,
    test_client: TestClient,
) -> None:
    monkeypatch.setattr(app_module, "LIGHTLY_STUDIO_SERVER_TIMING_ENABLED", False)

    response = test_client.get("/api/collections")
    assert response.status_code == HTTP_STATUS_OK
    assert response.headers.get("server-timing") is None


def test_db_timing_accumulates_from_copied_context() -> None:
    request_start_time, token = server_timing.start_request_timing()

    copied_context = contextvars.copy_context()
    copied_context.run(server_timing.add_db_time_ms, 5.0)

    _, db_ms, _ = server_timing.finish_request_timing(
        request_start_time=request_start_time,
        token=token,
    )
    assert db_ms >= 5.0
