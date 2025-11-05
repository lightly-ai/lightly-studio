"""Base operator class for LightlyStudio plugins."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, TypedDict
from uuid import UUID

from sqlmodel import Session

from lightly_studio.plugins.parameter import BaseParameter, StringParameter


class OperatorResult(TypedDict):
    """Result returned by operator execution."""

    success: bool
    message: str


class BaseOperator(ABC):
    """Base class for all operators."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the operator name."""

    @property
    @abstractmethod
    def description(self) -> str:
        """Return the description of the operator."""

    @property
    @abstractmethod
    def parameters(self) -> list[BaseParameter]:
        """Return the list of parameters this operator expects."""

    @abstractmethod
    def execute(
        self,
        *,
        session: Session,
        dataset_id: UUID,
        parameters: dict[str, Any],
    ) -> OperatorResult:
        """Execute the operator with the given parameters.

        Args:
            session: Database session.
            dataset_id: ID of the dataset to operate on.
            parameters: Parameters passed to the operator.

        Returns:
            Dictionary with 'success' (bool) and 'message' (str) keys.
        """
        # TODO (Jonas 11/2025): The parameters dict should be validated against self.parameters,
        # for now we leave it to the operator implementation.


class EchoOperator(BaseOperator):
    """An example operator that echoes the input parameters."""

    @property
    def name(self) -> str:
        """Return the operator name."""
        return "Echo Operator"

    @property
    def description(self) -> str:
        """Return the description of the operator."""
        return "An operator that echoes the input parameters."

    @property
    def parameters(self) -> list[BaseParameter]:
        """Return the list of parameters this operator expects."""
        return [
            StringParameter(name="param1", description="A string parameter", required=True),
        ]

    def execute(
        self,
        *,
        session: Session,
        dataset_id: UUID,
        parameters: dict[str, Any],
    ) -> OperatorResult:
        """Return the input parameter, the dataset_id, and the session."""
        return {
            "success": True,
            "message": f"{parameters['param1']}, {dataset_id}, {session}",
        }
