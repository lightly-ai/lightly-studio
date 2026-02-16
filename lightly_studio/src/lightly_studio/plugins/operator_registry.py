"""Operator registry for LightlyStudio plugins."""

from __future__ import annotations

import asyncio
import logging
import sys
import uuid
from dataclasses import dataclass

from .base_operator import BaseOperator, OperatorStatus

logger = logging.getLogger(__name__)

ENTRY_POINT_GROUP = "lightly_studio.plugins"


@dataclass
class RegisteredOperatorMetadata:
    """Meta data for a registered operator."""

    operator_id: str
    name: str
    status: str


class OperatorRegistry:
    """Registry for managing operators."""

    def __init__(self) -> None:
        """Initialize the operator registry."""
        self._operators: dict[str, BaseOperator] = {}

    def register(self, operator: BaseOperator) -> None:
        """Register an operator."""
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

    # --- Lifecycle orchestration ---

    async def start_all(self, timeout_per_operator: float = 120.0) -> None:
        """Start all registered operators concurrently.

        Each operator's ``start()`` is awaited with a per-operator timeout.
        Failures are logged but do not prevent other operators from starting.
        """
        tasks = [
            self._start_one(operator_id, operator, timeout_per_operator)
            for operator_id, operator in self._operators.items()
        ]
        await asyncio.gather(*tasks)

    async def _start_one(
        self, operator_id: str, operator: BaseOperator, timeout: float
    ) -> None:
        """Start a single operator with timeout and error handling."""
        operator._status = OperatorStatus.STARTING
        try:
            await asyncio.wait_for(operator.start(), timeout=timeout)
            if operator._status == OperatorStatus.STARTING:
                operator._status = OperatorStatus.READY
            logger.info("Operator '%s' (%s) started.", operator.name, operator_id)
        except asyncio.TimeoutError:
            operator._status = OperatorStatus.ERROR
            operator._error_message = f"Startup timed out after {timeout}s"
            logger.warning(
                "Operator '%s' (%s) startup timed out after %ss.",
                operator.name,
                operator_id,
                timeout,
            )
        except Exception:
            operator._status = OperatorStatus.ERROR
            logger.warning(
                "Operator '%s' (%s) failed to start.",
                operator.name,
                operator_id,
                exc_info=True,
            )

    async def stop_all(self) -> None:
        """Stop all registered operators concurrently."""
        tasks = [
            self._stop_one(operator_id, operator)
            for operator_id, operator in self._operators.items()
        ]
        await asyncio.gather(*tasks)

    async def _stop_one(self, operator_id: str, operator: BaseOperator) -> None:
        """Stop a single operator with error handling."""
        operator._status = OperatorStatus.STOPPING
        try:
            await asyncio.wait_for(operator.stop(), timeout=10.0)
            operator._status = OperatorStatus.STOPPED
            logger.info("Operator '%s' (%s) stopped.", operator.name, operator_id)
        except Exception:
            logger.warning(
                "Operator '%s' (%s) failed to stop cleanly.",
                operator.name,
                operator_id,
                exc_info=True,
            )

    # --- Queries ---

    def get_all_metadata(self) -> list[RegisteredOperatorMetadata]:
        """Get all registered operators with their names."""
        return [
            RegisteredOperatorMetadata(
                operator_id=operator_id,
                name=operator.name,
                status=operator.status.value,
            )
            for operator_id, operator in self._operators.items()
        ]

    def get_by_id(self, operator_id: str) -> BaseOperator | None:
        """Get an operator by its ID."""
        return self._operators.get(operator_id)


# Global registry instance
operator_registry = OperatorRegistry()
