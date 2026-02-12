"""Manages subprocess lifecycle for plugin servers."""

from __future__ import annotations

import logging
import subprocess
import time
from typing import TYPE_CHECKING

import requests

if TYPE_CHECKING:
    from lightly_studio.plugins.operator_registry import OperatorRegistry

logger = logging.getLogger(__name__)

HEALTH_CHECK_TIMEOUT_S = 30
HEALTH_CHECK_INTERVAL_S = 1


class PluginServerManager:
    """Starts, monitors, and stops plugin server subprocesses."""

    def __init__(self) -> None:
        self._processes: dict[str, subprocess.Popen] = {}  # operator_id → process

    def start_all(self, registry: OperatorRegistry) -> None:
        """Start servers for all registered operators that declare one.

        Iterates over the registry. For each operator with a non-None
        ``server_command()``, checks if the server is already reachable
        (via ``server_health_url()``). If not, spawns a subprocess and
        waits for it to become healthy.

        Args:
            registry: The operator registry to scan.
        """
        for operator_id, operator in registry._operators.items():
            command = operator.server_command()
            if command is None:
                continue

            health_url = operator.server_health_url()

            # Check if already running (e.g., user started it manually)
            if health_url and self._is_healthy(health_url):
                logger.info(
                    "Plugin '%s' server already running at %s",
                    operator_id,
                    health_url,
                )
                continue

            logger.info(
                "Starting server for plugin '%s': %s",
                operator_id,
                " ".join(command),
            )

            try:
                process = subprocess.Popen(
                    command,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )
                self._processes[operator_id] = process

                # Wait for health check if URL is provided
                if health_url:
                    if self._wait_for_healthy(health_url, operator_id):
                        logger.info(
                            "Plugin '%s' server is ready at %s",
                            operator_id,
                            health_url,
                        )
                    else:
                        logger.warning(
                            "Plugin '%s' server did not become healthy within %ds "
                            "(health URL: %s). It may still be starting.",
                            operator_id,
                            HEALTH_CHECK_TIMEOUT_S,
                            health_url,
                        )
                else:
                    logger.info(
                        "Plugin '%s' server started (no health URL configured).",
                        operator_id,
                    )

            except Exception:
                logger.warning(
                    "Failed to start server for plugin '%s'",
                    operator_id,
                    exc_info=True,
                )

    def shutdown(self) -> None:
        """Terminate all managed server subprocesses."""
        for operator_id, process in self._processes.items():
            if process.poll() is None:  # still running
                logger.info("Stopping server for plugin '%s'", operator_id)
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    logger.warning(
                        "Plugin '%s' server did not stop gracefully, killing.",
                        operator_id,
                    )
                    process.kill()
        self._processes.clear()

    def _is_healthy(self, url: str) -> bool:
        """Check if a health URL returns a 2xx status."""
        try:
            response = requests.get(url, timeout=2)
            return response.ok
        except requests.RequestException:
            return False

    def _wait_for_healthy(self, url: str, operator_id: str) -> bool:
        """Poll a health URL until it responds or timeout is reached."""
        deadline = time.monotonic() + HEALTH_CHECK_TIMEOUT_S
        while time.monotonic() < deadline:
            # Check if process died
            process = self._processes.get(operator_id)
            if process and process.poll() is not None:
                stderr = process.stderr.read().decode() if process.stderr else ""
                logger.warning(
                    "Plugin '%s' server exited with code %d. stderr: %s",
                    operator_id,
                    process.returncode,
                    stderr[:500],
                )
                return False

            if self._is_healthy(url):
                return True

            time.sleep(HEALTH_CHECK_INTERVAL_S)
        return False


# Global instance
plugin_server_manager = PluginServerManager()
