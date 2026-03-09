"""Operator registry for LightlyStudio plugins."""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field

from .base_operator import BaseOperator, OperatorStatus
from .operator_context import OperatorScope

logger = logging.getLogger(__name__)


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


# Global registry instance
operator_registry = OperatorRegistry()
