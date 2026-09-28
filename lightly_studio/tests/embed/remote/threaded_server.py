"""Serve an embedder over a real loopback socket in a background thread."""

from __future__ import annotations

import contextlib
import socket
import threading
import time
from collections.abc import Iterator

import httpx
import uvicorn
from lightly_studio_serve import protocol, server
from lightly_studio_serve.embedder import Embedder

_HOST = "127.0.0.1"

# The wait for the server to answer its first request. Generous for a loopback server, so
# that a loaded machine running the suite under xdist does not make a test flaky.
_STARTUP_TIMEOUT_SECONDS = 10.0
_POLL_INTERVAL_SECONDS = 0.02
_POLL_TIMEOUT_SECONDS = 1.0


@contextlib.contextmanager
def serve(embedder: Embedder, api_key: str | None = None) -> Iterator[str]:
    """Serve ``embedder`` until the context exits, and yield the address of the server.

    The socket is bound before uvicorn starts, so another process cannot claim the port
    in between.

    Args:
        embedder: The embedder to serve.
        api_key: The bearer token the server requires, or `None` for no authentication.

    Raises:
        TimeoutError: If the server does not answer within the startup timeout.
    """
    listener = socket.socket()
    listener.bind((_HOST, 0))
    listener.listen()
    port = int(listener.getsockname()[1])
    app = server.create_app(embedder=embedder, api_key=api_key)
    uvicorn_server = uvicorn.Server(uvicorn.Config(app=app, log_level="warning"))
    thread = threading.Thread(
        target=uvicorn_server.run,
        kwargs={"sockets": [listener]},
        daemon=True,
    )
    thread.start()
    # A startup that fails still has to stop the server, or its thread serves on.
    try:
        url = f"http://{_HOST}:{port}"
        wait_until_ready(url=url, api_key=api_key)
        yield url
    finally:
        uvicorn_server.should_exit = True
        thread.join(timeout=_STARTUP_TIMEOUT_SECONDS)
        listener.close()


def wait_until_ready(url: str, api_key: str | None = None) -> None:
    """Poll `/v1/describe` until the server answers.

    Args:
        url: The address of the server.
        api_key: The bearer token the server requires, or `None` for no authentication.

    Raises:
        TimeoutError: If the server does not answer within the startup timeout, with what
            went wrong on the last poll.
    """
    headers = {} if api_key is None else {"Authorization": f"Bearer {api_key}"}
    deadline = time.monotonic() + _STARTUP_TIMEOUT_SECONDS
    last_problem = "it was never reached"
    while time.monotonic() < deadline:
        try:
            response = httpx.get(
                url=f"{url}{protocol.DESCRIBE_PATH}",
                headers=headers,
                timeout=_POLL_TIMEOUT_SECONDS,
            )
        except httpx.HTTPError as error:
            last_problem = f"{type(error).__name__}: {error}"
        else:
            if response.status_code == httpx.codes.OK:
                return
            last_problem = f"it answered {response.status_code}"
        time.sleep(_POLL_INTERVAL_SECONDS)
    raise TimeoutError(
        f"The embedding server at {url} did not serve {protocol.DESCRIBE_PATH} within "
        f"{_STARTUP_TIMEOUT_SECONDS} seconds: {last_problem}."
    )
