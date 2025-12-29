"""Test module for the Server class."""

from __future__ import annotations

from socket import AF_INET, SOCK_STREAM, socket
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from lightly_studio.api.app import app
from lightly_studio.api.routes.api.status import (
    HTTP_STATUS_NOT_FOUND,
    HTTP_STATUS_OK,
)
from lightly_studio.api.server import Server


def test_server_initialization() -> None:
    """Test that the Server class initializes correctly."""
    host = "127.0.0.1"
    port = 8000
    server = Server(host, port)

    assert server.host == host
    assert server.port == port


@patch("uvicorn.Server.run")
def test_server_start(mock_run: MagicMock) -> None:
    """Test that the start method calls uvicorn.Server.run with correct arguments."""
    host = "127.0.0.1"
    port = 8000
    server = Server(host, port)

    # Call the start method
    server.start()

    # Assert uvicorn.Server.run was called
    mock_run.assert_called_once()


def test_server_static_webapp() -> None:
    client = TestClient(app)

    # check webapp index file being returned for all non-file paths
    static_webapp = client.get("/")
    assert static_webapp.status_code == HTTP_STATUS_OK
    assert static_webapp.headers["content-type"] == "text/html; charset=utf-8"

    static_webapp = client.get("/index.html")
    assert static_webapp.status_code == HTTP_STATUS_OK
    assert static_webapp.headers["content-type"] == "text/html; charset=utf-8"

    static_webapp = client.get("/deeper/path/")
    assert static_webapp.status_code == HTTP_STATUS_OK
    assert static_webapp.headers["content-type"] == "text/html; charset=utf-8"

    # check that we otherwise try to resolve files
    static_file = client.get("/favicon.png")
    assert static_file.status_code == HTTP_STATUS_OK
    assert static_file.headers["content-type"] == "image/png"

    static_file = client.get("/_app/env.js")
    assert static_file.status_code == HTTP_STATUS_OK
    assert "javascript" in static_file.headers["content-type"]

    static_file = client.get("/non-existing-file.png")
    assert static_file.status_code == HTTP_STATUS_NOT_FOUND


def test__get_available_port__preferred_port_in_use() -> None:
    """Test that a different port is returned if the preferred port is used."""
    host = "localhost"
    port = 8001

    # Bind to the preferred port to simulate it being in use.
    s = socket(AF_INET, SOCK_STREAM)
    s.bind((host, port))
    s.listen(1)

    server = Server(host, port)
    s.close()
    assert server.port != port
