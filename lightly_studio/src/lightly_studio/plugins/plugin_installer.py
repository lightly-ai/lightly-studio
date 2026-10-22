"""Install plugins from the catalog into the Python environment of the running server."""

from __future__ import annotations

import collections
import importlib.metadata
import ipaddress
import logging
import shutil
import subprocess
import sys
import tempfile
import threading
import uuid
from enum import Enum
from pathlib import Path

from pydantic import BaseModel, Field

from lightly_studio.dataset import env
from lightly_studio.errors import NotFoundError
from lightly_studio.plugins import plugin_catalog
from lightly_studio.plugins.operator_registry import operator_registry
from lightly_studio.plugins.plugin_catalog import CatalogEntry
from lightly_studio.utils import executor

logger = logging.getLogger(__name__)

_LIGHTLY_STUDIO_DISTRIBUTION = "lightly-studio"
_MAX_LOG_LINES = 200


class InstallJobStatus(str, Enum):
    """The state of a plugin install job."""

    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class InstallJob(BaseModel):
    """A plugin install that runs in the background."""

    job_id: str
    plugin_id: str
    status: InstallJobStatus = InstallJobStatus.QUEUED
    log: str = ""
    """The last lines of the installer output."""

    error_message: str = ""
    new_operator_ids: list[str] = Field(default_factory=list)
    """The operators that the installed plugin registered."""

    restart_recommended: bool = False
    """True if the install changed a package that the server already imported."""


class PluginInstallNotAllowedError(Exception):
    """Exception raised when plugin installs are not allowed for a request."""


_jobs: dict[str, InstallJob] = {}
_jobs_lock = threading.Lock()


def is_install_allowed(client_host: str | None) -> bool:
    """Return whether a request from this client may install plugins.

    ``LIGHTLY_STUDIO_ALLOW_PLUGIN_INSTALL`` overrides the decision. If it is not set, only a
    client on the same machine may install plugins, because an install runs code on the server.

    Args:
        client_host: The address of the client that sent the request.
    """
    if env.LIGHTLY_STUDIO_ALLOW_PLUGIN_INSTALL is not None:
        return env.LIGHTLY_STUDIO_ALLOW_PLUGIN_INSTALL
    if client_host is None:
        return False
    if client_host == "localhost":
        return True
    try:
        return ipaddress.ip_address(client_host).is_loopback
    except ValueError:
        return False


def start_install(entry: CatalogEntry) -> InstallJob:
    """Start to install a catalog plugin in the background.

    If an install of the same plugin is already queued or running, that job is returned.

    Args:
        entry: The catalog entry of the plugin.

    Returns:
        A copy of the install job.
    """
    with _jobs_lock:
        for job in _jobs.values():
            if job.plugin_id == entry.id and job.status in (
                InstallJobStatus.QUEUED,
                InstallJobStatus.RUNNING,
            ):
                return job.model_copy(deep=True)
        job = InstallJob(job_id=str(uuid.uuid4()), plugin_id=entry.id)
        _jobs[job.job_id] = job
    # One worker, so that two installs never change the environment at the same time.
    executor.get_media_executor(thread_name_prefix="plugin_install", max_workers=1).submit(
        _run_install, job=job, install_spec=entry.install_spec
    )
    return job.model_copy(deep=True)


def get_job(job_id: str) -> InstallJob:
    """Get a copy of an install job.

    Raises:
        NotFoundError: If there is no job with this ID.
    """
    with _jobs_lock:
        job = _jobs.get(job_id)
        if job is None:
            raise NotFoundError(f"Plugin install job '{job_id}' not found.")
        return job.model_copy(deep=True)


def build_install_command(install_spec: str, constraints_path: Path) -> list[str]:
    """Build the command that installs a requirement into the environment of the server.

    uv is preferred if it is available, because environments that uv creates often have no pip.

    Args:
        install_spec: The requirement to install.
        constraints_path: A pip constraints file.

    Returns:
        The command as a list of arguments.
    """
    uv_path = shutil.which("uv")
    if uv_path is not None:
        return [
            uv_path,
            "pip",
            "install",
            "--python",
            sys.executable,
            "--constraint",
            str(constraints_path),
            install_spec,
        ]
    return [
        sys.executable,
        "-m",
        "pip",
        "install",
        "--constraint",
        str(constraints_path),
        install_spec,
    ]


def _run_install(job: InstallJob, install_spec: str) -> None:
    try:
        _set_job(job=job, status=InstallJobStatus.RUNNING)
        versions_before = _installed_versions()
        with tempfile.TemporaryDirectory() as tmp_dir:
            constraints_path = Path(tmp_dir) / "constraints.txt"
            # The plugin must not upgrade or downgrade the running LightlyStudio.
            lightly_studio_version = importlib.metadata.version(_LIGHTLY_STUDIO_DISTRIBUTION)
            constraints_path.write_text(
                f"{_LIGHTLY_STUDIO_DISTRIBUTION}=={lightly_studio_version}\n"
            )
            command = build_install_command(
                install_spec=install_spec, constraints_path=constraints_path
            )
            logger.info("Installing plugin '%s': %s", job.plugin_id, " ".join(command))
            return_code = _run_and_capture(job=job, command=command)

        if return_code != 0:
            _set_job(
                job=job,
                status=InstallJobStatus.FAILED,
                error_message=f"The installer exited with code {return_code}.",
            )
            return

        restart_recommended = _has_changed_imported_packages(
            versions_before=versions_before, versions_after=_installed_versions()
        )
        new_operator_ids = operator_registry.discover_new_plugins()
        error_message = (
            ""
            if new_operator_ids
            else "The package was installed, but it registered no new plugins."
        )
        with _jobs_lock:
            job.new_operator_ids = new_operator_ids
            job.restart_recommended = restart_recommended
        _set_job(job=job, status=InstallJobStatus.SUCCEEDED, error_message=error_message)
    except Exception as e:
        logger.exception("Plugin install '%s' failed.", job.plugin_id)
        _set_job(job=job, status=InstallJobStatus.FAILED, error_message=str(e))


def _run_and_capture(job: InstallJob, command: list[str]) -> int:
    """Run the installer and keep the last lines of its output in the job."""
    lines: collections.deque[str] = collections.deque(maxlen=_MAX_LOG_LINES)
    with subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    ) as process:
        assert process.stdout is not None
        for line in process.stdout:
            lines.append(line.rstrip("\n"))
            with _jobs_lock:
                job.log = "\n".join(lines)
        return process.wait()


def _set_job(job: InstallJob, status: InstallJobStatus, error_message: str = "") -> None:
    with _jobs_lock:
        job.status = status
        job.error_message = error_message


def _installed_versions() -> dict[str, str]:
    """Get the version of each installed distribution, keyed by the normalized name."""
    versions = {}
    for dist in importlib.metadata.distributions():
        name = dist.metadata.get("Name")
        if name is not None:
            versions[plugin_catalog.normalize_package_name(name)] = dist.version
    return versions


def _has_changed_imported_packages(
    versions_before: dict[str, str], versions_after: dict[str, str]
) -> bool:
    """Return whether the install changed a distribution that has an imported module.

    Python keeps the old code of an imported module. A changed distribution is only used after a
    restart of the server.
    """
    changed = [
        name
        for name, version in versions_before.items()
        if versions_after.get(name) not in (None, version)
    ]
    for name in changed:
        modules = _top_level_modules(package_name=name)
        imported = sorted(module for module in modules if module in sys.modules)
        if imported:
            logger.info("The plugin install changed '%s', which is imported: %s", name, imported)
            return True
    return False


def _top_level_modules(package_name: str) -> set[str]:
    """Get the names of the top-level modules that a distribution installs."""
    try:
        files = importlib.metadata.distribution(package_name).files or []
    except importlib.metadata.PackageNotFoundError:
        return set()
    modules = set()
    for file in files:
        top = file.parts[0]
        if top.endswith((".dist-info", ".data", ".pth")) or top in ("..", "__pycache__"):
            continue
        modules.add(top[: -len(".py")] if top.endswith(".py") else top)
    return modules
