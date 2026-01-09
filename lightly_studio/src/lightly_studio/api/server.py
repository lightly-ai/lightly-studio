"""This module contains the Server class for running the API using Uvicorn."""

import random
import socket
from contextlib import suppress

import uvicorn

from lightly_studio.api.app import app
from lightly_studio.dataset import env


class Server:
    """This class represents a server for running the API using Uvicorn."""

    port: int
    host: str

    def __init__(self, host: str, port: int) -> None:
        """Initialize the Server with host and port.

        Args:
            host (str): The hostname to bind the server to.
            port (int): The port number to run the server on.
        """
        self.host = host
        if self.host == "localhost" and not _is_ipv6_available():
            # There is no config option for uvicorn to start in a IPv4-only mode. For the most
            # common case of binding to localhost, we can translate the adress to the IPv4 format.
            self.host = "127.0.0.1"  # IPv4-only
        self.port = _get_available_port(host=self.host, preferred_port=port)
        if port != self.port:
            env.LIGHTLY_STUDIO_PORT = self.port
            env.APP_URL = f"{env.LIGHTLY_STUDIO_PROTOCOL}://{env.LIGHTLY_STUDIO_HOST}:{env.LIGHTLY_STUDIO_PORT}"

    def create_uvicorn_server(self) -> uvicorn.Server:
        """Create a Uvicorn server instance."""
        config = uvicorn.Config(
            app=app,
            host=self.host,
            port=self.port,
            http="h11",
            # https://uvicorn.dev/settings/#resource-limits
            limit_concurrency=100,  # Max concurrent connections
            limit_max_requests=10000,  # Max requests before worker restart
            # https://uvicorn.dev/settings/#timeouts
            timeout_keep_alive=5,  # Keep-alive timeout in seconds
            timeout_graceful_shutdown=30,  # Graceful shutdown timeout
            access_log=env.LIGHTLY_STUDIO_DEBUG,
        )
        return uvicorn.Server(config=config)


def _is_ipv6_available() -> bool:
    """Check if IPv6 is available on the system."""
    try:
        # We try to bind to an IPv6 address to check if it is available.
        # This is needed because some systems (e.g. some docker containers)
        # have IPv6 disabled but socket.has_ipv6 is True.
        with socket.socket(socket.AF_INET6, socket.SOCK_STREAM) as s:
            s.bind(("::1", 0))
        return True
    except OSError:
        return False


def _get_available_port(host: str, preferred_port: int, max_tries: int = 50) -> int:
    """Get an available port, if possible, otherwise a random one.

    Args:
        host: The hostname or IP address to bind to.
        preferred_port: The port to try first.
        max_tries: Maximum number of random ports to try.

    Raises:
        RuntimeError if it cannot find an available port.

    Returns:
        An available port number.
    """
    if _is_port_available(host=host, port=preferred_port):
        return preferred_port

    # Try random ports in the range 1024-65535
    for _ in range(max_tries):
        port = random.randint(1024, 65535)
        if _is_port_available(host=host, port=port):
            return port

    raise RuntimeError("Could not find an available port.")


def _is_port_available(host: str, port: int) -> bool:
    # Determine address family based on host.
    try:
        socket.inet_pton(socket.AF_INET, host)
        families = [socket.AF_INET]
    except OSError:
        try:
            socket.inet_pton(socket.AF_INET6, host)
            families = [socket.AF_INET6]
        except OSError:
            # Fallback for hostnames like 'localhost'
            families = [socket.AF_INET]
            if _is_ipv6_available():
                families.append(socket.AF_INET6)

    for family in families:
        with socket.socket(family, socket.SOCK_STREAM) as s:
            # Allow port binding during TIME_WAIT to avoid false "port busy" checks.
            with suppress(OSError):
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                s.bind((host, port))
            except OSError:
                return False
    return True
