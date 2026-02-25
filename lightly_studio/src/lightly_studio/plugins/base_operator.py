"""Base operator class for LightlyStudio plugins."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from sqlmodel import Session

from lightly_studio.plugins.operator_context import ExecutionContext, OperatorScope
from lightly_studio.plugins.parameter import BaseParameter


@dataclass
class OperatorResult:
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

    @property
    @abstractmethod
    def supported_scopes(self) -> list[OperatorScope]:
        """Return the list of scopes this operator can be triggered from.

        Determines where in the UI the operator is surfaced.
        ``OperatorScope.ROOT`` targets dataset/root collections.
        """

    @abstractmethod
    def execute(
        self,
        *,
        session: Session,
        context: ExecutionContext,
        parameters: dict[str, Any],
    ) -> OperatorResult:
        """Execute the operator with the given parameters.

        Args:
            session: Database session.
            context: Execution context containing collection_id and optional filter.
            parameters: Parameters passed to the operator.

        Returns:
            An OperatorResult with success flag and message.
        """
        # TODO (Jonas 11/2025): The parameters dict should be validated against self.parameters,
        # for now we leave it to the operator implementation.
