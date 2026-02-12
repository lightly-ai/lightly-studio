"""Operator registry for LightlyStudio plugins."""

from __future__ import annotations

import logging
import sys
import uuid
from dataclasses import dataclass

from .base_operator import BaseOperator

logger = logging.getLogger(__name__)

ENTRY_POINT_GROUP = "lightly_studio.plugins"


@dataclass
class RegisteredOperatorMetadata:
    """Meta data for a registered operator."""

    operator_id: str
    name: str
    description: str
    operator_type: str


class OperatorRegistry:
    """Registry for managing operators."""

    def __init__(self) -> None:
        """Initialize the operator registry."""
        self._operators: dict[str, BaseOperator] = {}

    def register(
        self, operator: BaseOperator, operator_id: str | None = None
    ) -> None:
        """Register an operator.

        Args:
            operator: The operator instance to register.
            operator_id: Optional deterministic ID. If not provided, a UUID is
                generated.
        """
        if operator_id is None:
            operator_id = str(uuid.uuid4())
        self._operators[operator_id] = operator

    def discover_plugins(self) -> None:
        """Auto-discover and register operators from installed packages.

        Scans for packages that declare entry points in the
        ``lightly_studio.plugins`` group. Each entry point should reference a
        ``BaseOperator`` subclass. The entry point name is used as the
        ``operator_id``.

        Example entry in an external package's ``pyproject.toml``::

            [project.entry-points."lightly_studio.plugins"]
            grounding_dino = "my_package:GroundingDinoOperator"
        """
        from importlib.metadata import entry_points

        if sys.version_info >= (3, 10):
            eps = entry_points(group=ENTRY_POINT_GROUP)
        else:
            eps = entry_points().get(ENTRY_POINT_GROUP, [])  # type: ignore[assignment]

        for ep in eps:
            if ep.name in self._operators:
                logger.debug(
                    "Plugin '%s' already registered, skipping entry point.",
                    ep.name,
                )
                continue
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
                self.register(operator, operator_id=ep.name)
                logger.info("Discovered plugin '%s' from %s", ep.name, ep.value)
            except Exception:
                logger.warning(
                    "Failed to load plugin '%s' from %s",
                    ep.name,
                    ep.value,
                    exc_info=True,
                )

    def get_all_metadata(self) -> list[RegisteredOperatorMetadata]:
        """Get all registered operators with their names."""
        return [
            RegisteredOperatorMetadata(
                operator_id=operator_id,
                name=operator.name,
                description=operator.description,
                operator_type=operator.operator_type,
            )
            for operator_id, operator in self._operators.items()
        ]

    def get_by_id(self, operator_id: str) -> BaseOperator | None:
        """Get an operator by its ID."""
        return self._operators.get(operator_id)


# Global registry instance
operator_registry = OperatorRegistry()
