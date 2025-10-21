"""This module contains the Server class for running the API using Uvicorn."""

import random
import socket

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
        self.port = _get_available_port(host=host, preferred_port=port)
        if port != self.port:
            env.LIGHTLY_STUDIO_PORT = self.port
            env.APP_URL = f"{env.LIGHTLY_STUDIO_PROTOCOL}://{env.LIGHTLY_STUDIO_HOST}:{env.LIGHTLY_STUDIO_PORT}"

    def start(self) -> None:
        """Start the API server using Uvicorn."""
        # start the app
        uvicorn.run(app, host=self.host, port=self.port, http="h11")


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
            families = [socket.AF_INET, socket.AF_INET6]

    for family in families:
        with socket.socket(family, socket.SOCK_STREAM) as s:
            try:
                s.bind((host, port))
            except OSError:
                return False
    return True
