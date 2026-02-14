"""Manages subprocess lifecycle for plugin servers."""

from __future__ import annotations

import logging
import os
import shutil
import socket
import subprocess
import sys
import time
import venv
from pathlib import Path
from typing import TYPE_CHECKING

import requests

if TYPE_CHECKING:
    from lightly_studio.plugins.operator_registry import OperatorRegistry

logger = logging.getLogger(__name__)

HEALTH_CHECK_TIMEOUT_S = 30
HEALTH_CHECK_INTERVAL_S = 1
VENV_BASE_DIR = Path.home() / ".lightly" / "plugin-envs"
PORT_RANGE_START = 19400
PORT_RANGE_END = 19500


class PluginServerManager:
    """Starts, monitors, and stops plugin server subprocesses.

    When an operator declares ``server_package()``, the manager creates a
    dedicated virtual environment under ``~/.lightly/plugin-envs/<operator_id>/``,
    installs the package there, and runs the server command with that
    environment's Python.  Uses ``uv`` when available for speed, otherwise
    falls back to the standard library ``venv`` + ``pip``.

    The manager assigns each plugin server a free port from the range
    19400–19500 and passes it via the ``LIGHTLY_PLUGIN_PORT`` environment
    variable.  The assigned port is stored on the operator instance so it
    can derive its own server URL via ``operator.server_url``.
    """

    def __init__(self) -> None:
        self._processes: dict[str, subprocess.Popen] = {}  # operator_id -> process

    def start_all(self, registry: OperatorRegistry) -> None:
        """Start servers for all registered operators that declare one."""
        for operator_id, operator in registry._operators.items():
            command = operator.server_command()
            if command is None:
                continue

            # Assign a free port
            port = self._find_free_port()
            operator._server_port = port

            health_path = operator.server_health_path()
            health_url = f"http://localhost:{port}{health_path}" if health_path else None

            # Check if already running (e.g., user started it manually)
            if health_url and self._is_healthy(health_url):
                logger.info(
                    "Plugin '%s' server already running at %s",
                    operator_id,
                    health_url,
                )
                continue

            # Ensure venv exists if the operator declares a server package
            package = operator.server_package()
            if package is not None:
                venv_python = self._ensure_venv(operator_id, package)
                if venv_python is None:
                    continue  # venv setup failed, already logged
                # Replace {python} placeholder in command
                command = [
                    venv_python if arg == "{python}" else arg for arg in command
                ]

            logger.info(
                "Starting server for plugin '%s' on port %d: %s",
                operator_id,
                port,
                " ".join(command),
            )

            try:
                env = {**os.environ, "LIGHTLY_PLUGIN_PORT": str(port)}
                process = subprocess.Popen(
                    command,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    env=env,
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
                        "Plugin '%s' server started (no health path configured).",
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

    # --- port assignment ---

    @staticmethod
    def _find_free_port() -> int:
        """Find an available port in the plugin port range."""
        for port in range(PORT_RANGE_START, PORT_RANGE_END):
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                try:
                    s.bind(("localhost", port))
                    return port
                except OSError:
                    continue
        # Fallback: let OS pick any free port
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("localhost", 0))
            return s.getsockname()[1]

    # --- venv management ---

    def _ensure_venv(self, operator_id: str, package: str) -> str | None:
        """Create or reuse a venv for the operator and install its package.

        Uses ``uv`` if available (much faster), otherwise falls back to
        the standard library ``venv`` + ``pip``.

        Returns the path to the venv's Python executable, or None on failure.
        """
        venv_dir = VENV_BASE_DIR / operator_id
        python_path = self._venv_python(venv_dir)

        uv = shutil.which("uv")
        if uv:
            return self._ensure_venv_uv(uv, operator_id, package, venv_dir, python_path)
        return self._ensure_venv_stdlib(operator_id, package, venv_dir, python_path)

    def _ensure_venv_uv(
        self,
        uv: str,
        operator_id: str,
        package: str,
        venv_dir: Path,
        python_path: Path,
    ) -> str | None:
        """Create venv and install package using uv (fast path)."""
        if not python_path.exists():
            logger.info("Creating venv for plugin '%s' at %s (uv)", operator_id, venv_dir)
            result = subprocess.run(
                [uv, "venv", str(venv_dir)],
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                logger.error("Failed to create venv for plugin '%s': %s", operator_id, result.stderr)
                return None

        logger.info("Installing '%s' into plugin '%s' venv (uv)", package, operator_id)
        result = subprocess.run(
            [uv, "pip", "install", "--python", str(python_path), package],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            logger.error("Failed to install '%s' for plugin '%s': %s", package, operator_id, result.stderr)
            return None

        return str(python_path)

    def _ensure_venv_stdlib(
        self,
        operator_id: str,
        package: str,
        venv_dir: Path,
        python_path: Path,
    ) -> str | None:
        """Create venv and install package using stdlib venv + pip (fallback)."""
        if not python_path.exists():
            logger.info("Creating venv for plugin '%s' at %s (stdlib)", operator_id, venv_dir)
            try:
                venv.create(str(venv_dir), with_pip=True)
            except Exception:
                logger.error("Failed to create venv for plugin '%s'", operator_id, exc_info=True)
                return None

        logger.info("Installing '%s' into plugin '%s' venv (pip)", package, operator_id)
        result = subprocess.run(
            [str(python_path), "-m", "pip", "install", package],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            logger.error("Failed to install '%s' for plugin '%s': %s", package, operator_id, result.stderr)
            return None

        return str(python_path)

    @staticmethod
    def _venv_python(venv_dir: Path) -> Path:
        """Return the path to the Python executable inside a venv."""
        if sys.platform == "win32":
            return venv_dir / "Scripts" / "python.exe"
        return venv_dir / "bin" / "python"

    # --- health checking ---

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
                    stderr[:2000],
                )
                return False

            if self._is_healthy(url):
                return True

            time.sleep(HEALTH_CHECK_INTERVAL_S)
        return False


# Global instance
plugin_server_manager = PluginServerManager()
