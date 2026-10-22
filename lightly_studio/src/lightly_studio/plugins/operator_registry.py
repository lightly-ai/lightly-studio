"""Operator registry for LightlyStudio plugins."""

from __future__ import annotations

import importlib
import importlib.metadata
import logging
import site
import threading
import uuid
from dataclasses import dataclass, field
from pathlib import Path

from .base_operator import BaseOperator, OperatorStatus
from .operator_context import OperatorScope

logger = logging.getLogger(__name__)

ENTRY_POINT_GROUP = "lightly_studio.plugins"


@dataclass
class RegisteredOperatorMetadata:
    """Meta data for a registered operator."""

    operator_id: str
    name: str
    supported_scopes: list[OperatorScope] = field(default_factory=list)
    package_name: str | None = None
    """The distribution that provides the operator, `None` for a manually registered operator."""


class OperatorRegistry:
    """Registry for managing operators."""

    def __init__(self) -> None:
        """Initialize the operator registry."""
        self._operators: dict[str, BaseOperator] = {}
        self._package_names: dict[str, str] = {}
        # The (distribution name, entry point name) pairs that are already registered.
        self._loaded_entry_points: set[tuple[str, str]] = set()
        # Python reads the .pth files of the site directories only when the process starts.
        self._known_pth_files: set[Path] = set(_pth_files())
        self._lock = threading.Lock()

    def register(self, operator: BaseOperator, package_name: str | None = None) -> str:
        """Register an operator.

        Args:
            operator: The operator to register.
            package_name: The distribution that provides the operator, if known.

        Returns:
            The ID of the registered operator.
        """
        operator_id = str(uuid.uuid4())
        with self._lock:
            self._operators[operator_id] = operator
            if package_name is not None:
                self._package_names[operator_id] = package_name
        return operator_id

    def startup_all(self) -> None:
        """Start all registered operators sequentially.

        Failures are logged but do not prevent other operators from starting.
        """
        for operator_id, operator in list(self._operators.items()):
            _start_operator(operator_id=operator_id, operator=operator)

    def shutdown_all(self) -> None:
        """Stop all registered operators sequentially."""
        for operator_id, operator in list(self._operators.items()):
            operator.status = OperatorStatus.STOPPING
            try:
                operator.shutdown()
                operator.status = OperatorStatus.STOPPED
                logger.info("Operator '%s' (%s) stopped.", operator.name, operator_id)
            except Exception:
                logger.warning(
                    "Operator '%s' (%s) failed to stop cleanly.",
                    operator.name,
                    operator_id,
                    exc_info=True,
                )

    def get_all_metadata(self) -> list[RegisteredOperatorMetadata]:
        """Get all registered operators with their names."""
        return [
            RegisteredOperatorMetadata(
                operator_id=operator_id,
                name=operator.name,
                supported_scopes=operator.supported_scopes,
                package_name=self._package_names.get(operator_id),
            )
            for operator_id, operator in list(self._operators.items())
        ]

    def get_by_id(self, operator_id: str) -> BaseOperator | None:
        """Get an operator by its ID."""
        return self._operators.get(operator_id)

    def discover_plugins(self) -> list[str]:
        """Auto-discover and register operators from installed packages.

        Scans for packages that declare entry points in the ``lightly_studio.plugins`` group.
        Each entry point should reference a ``BaseOperator`` subclass. An entry point that is
        already registered is skipped, so it is safe to call this function again after a package
        was installed while the server runs.

        Example entry in an external packages ``pyproject.toml``:

        [project.entry-points."lightly_studio.plugins"]
            bbox_auto_propagation_nano_tracker =
            "lightly_plugins_bbox_auto_propagation_nano_tracker.operator:AutoPropagateOperator"

        Returns:
            The IDs of the newly registered operators.
        """
        # An editable install adds its source directory to sys.path with a .pth file.
        self._activate_new_pth_files()
        # Python caches the directory listings of sys.path. A package installed after the start
        # of the process is only found after the caches are cleared.
        importlib.invalidate_caches()
        new_operator_ids: list[str] = []
        for package_name, ep in _plugin_entry_points():
            key = (package_name, ep.name)
            if key in self._loaded_entry_points:
                continue
            try:
                operator_class = ep.load()
                operator = operator_class()
                # A failed load is tried again on the next scan, because an install can fix it.
                self._loaded_entry_points.add(key)
                if not isinstance(operator, BaseOperator):
                    logger.warning(
                        "Plugin '%s' (%s) is not a BaseOperator subclass, skipping.",
                        ep.name,
                        ep.value,
                    )
                    continue
                new_operator_ids.append(self.register(operator=operator, package_name=package_name))
                logger.info("Discovered plugin '%s' from %s", ep.name, ep.value)
            except Exception:
                logger.warning(
                    "Failed to load plugin '%s' from %s",
                    ep.name,
                    ep.value,
                    exc_info=True,
                )
        return new_operator_ids

    def discover_new_plugins(self) -> list[str]:
        """Discover, register and start the plugins that were installed after the last scan.

        Returns:
            The IDs of the newly registered operators.
        """
        new_operator_ids = self.discover_plugins()
        for operator_id in new_operator_ids:
            _start_operator(operator_id=operator_id, operator=self._operators[operator_id])
        return new_operator_ids

    def _activate_new_pth_files(self) -> None:
        """Process the .pth files that were added to the site directories after the start."""
        for pth_file in _pth_files():
            if pth_file in self._known_pth_files:
                continue
            self._known_pth_files.add(pth_file)
            logger.info("Adding the path entries of '%s'.", pth_file)
            site.addpackage(str(pth_file.parent), pth_file.name, None)


def _plugin_entry_points() -> list[tuple[str, importlib.metadata.EntryPoint]]:
    """Get the plugin entry points of all installed distributions.

    ``EntryPoint.dist`` is only available from Python 3.10, so the distributions are iterated to
    know which package provides each entry point.

    Returns:
        A list of (distribution name, entry point) pairs.
    """
    result: list[tuple[str, importlib.metadata.EntryPoint]] = []
    seen_distributions: set[str] = set()
    for dist in importlib.metadata.distributions():
        dist_name = dist.metadata.get("Name")
        # A distribution can be found twice if it is on sys.path twice.
        if dist_name is None or dist_name in seen_distributions:
            continue
        seen_distributions.add(dist_name)
        result.extend((dist_name, ep) for ep in dist.entry_points if ep.group == ENTRY_POINT_GROUP)
    return result


def _pth_files() -> list[Path]:
    """Get the .pth files of the site directories."""
    site_dirs = [*site.getsitepackages()]
    if site.ENABLE_USER_SITE:
        site_dirs.append(site.getusersitepackages())
    return sorted(pth for site_dir in site_dirs for pth in Path(site_dir).glob("*.pth"))


def _start_operator(operator_id: str, operator: BaseOperator) -> None:
    """Start one operator and set its status. A failure is logged, not raised."""
    operator.status = OperatorStatus.STARTING
    try:
        operator.startup()
        operator.status = OperatorStatus.READY
        logger.info("Operator '%s' (%s) started.", operator.name, operator_id)
    except Exception:
        operator.status = OperatorStatus.ERROR
        logger.warning(
            "Operator '%s' (%s) failed to start.",
            operator.name,
            operator_id,
            exc_info=True,
        )


# Global registry instance
operator_registry = OperatorRegistry()
