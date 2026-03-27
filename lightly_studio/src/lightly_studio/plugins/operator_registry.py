"""Operator registry for LightlyStudio plugins."""

from __future__ import annotations

import logging
import sys
import uuid
from dataclasses import dataclass, field
from importlib.metadata import entry_points

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


class OperatorRegistry:
    """Registry for managing operators."""

    def __init__(self) -> None:
        """Initialize the operator registry."""
        self._operators: dict[str, BaseOperator] = {}

    def register(self, operator: BaseOperator) -> None:
        """Register an operator."""
        operator_id = str(uuid.uuid4())
        self._operators[operator_id] = operator

    def startup_all(self) -> None:
        """Start all registered operators sequentially.

        Failures are logged but do not prevent other operators from starting.
        """
        for operator_id, operator in self._operators.items():
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

    def shutdown_all(self) -> None:
        """Stop all registered operators sequentially."""
        for operator_id, operator in self._operators.items():
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
            )
            for operator_id, operator in self._operators.items()
        ]

    def get_by_id(self, operator_id: str) -> BaseOperator | None:
        """Get an operator by its ID."""
        return self._operators.get(operator_id)

    def discover_plugins(self) -> None:
        """Auto-discover and register operators from installed packages.

        Scans for packages that declare entry points in the ``lightly_studio.plugins`` group.
        Each entry point should reference a ``BaseOperator`` subclass.

        Example entry in an external packages ``pyproject.toml``:

        [project.entry-points."lightly_studio.plugins"]
            bbox_auto_propagation_nano_tracker =
            "lightly_plugins_bbox_auto_propagation_nano_tracker.operator:AutoPropagateOperator"
        """
        if sys.version_info >= (3, 10):
            eps = entry_points(group=ENTRY_POINT_GROUP)
        else:
            eps = entry_points().get(ENTRY_POINT_GROUP, [])

        for ep in eps:
            try:
                operator_class = ep.load()
                operator = operator_class()
                if not isinstance(operator, BaseOperator):
                    logger.warning(
                        "Plugin '%s' (%s) is not a BaseOperator subclass, skipping.",
                        ep.name,
                        ep.value,
                    )
                    continue
                self.register(operator)
                logger.info("Discovered plugin '%s' from %s", ep.name, ep.value)
            except Exception:
                logger.warning(
                    "Failed to load plugin '%s' from %s",
                    ep.name,
                    ep.value,
                    exc_info=True,
                )


# Global registry instance
operator_registry = OperatorRegistry()
