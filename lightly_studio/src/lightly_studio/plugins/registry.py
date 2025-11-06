"""Operator registry for LightlyStudio plugins."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from .base_operator import BaseOperator


class OperatorRegistry:
    """Registry for managing operators."""

    def __init__(self) -> None:
        """Initialize the operator registry."""
        self._operators: dict[str, BaseOperator] = {}

    def register(self, operator: BaseOperator) -> None:
        """Register an operator."""
        operator_id = operator.__class__.__name__.lower()
        self._operators[operator_id] = operator

    def get_all(self) -> list[dict[str, Any]]:
        """Get all registered operators with their names and parameters."""
        operators = []
        for operator_id, operator in self._operators.items():
            operators.append({
                "id": operator_id,
                "name": operator.name,
                "parameters": [asdict(param) for param in operator.parameters],
            })
        return operators

    def get_by_id(self, operator_id: str) -> type[BaseOperator] | None:
        """Get an operator by its ID."""
        return self._operators.get(operator_id)


# Global registry instance
operator_registry = OperatorRegistry()
