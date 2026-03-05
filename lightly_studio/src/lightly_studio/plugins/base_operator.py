"""Base operator class for LightlyStudio plugins."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any

from sqlmodel import Session

from lightly_studio.plugins.operator_context import ExecutionContext, OperatorScope
from lightly_studio.plugins.parameter import BaseParameter


class OperatorStatus(str, Enum):
    """Lifecycle status of an operator."""

    PENDING = "pending"
    STARTING = "starting"
    READY = "ready"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"


@dataclass
class OperatorResult:
    """Result returned by operator execution."""

    success: bool
    message: str


class BaseOperator(ABC):
    """Base class for all operators."""

    status: OperatorStatus = OperatorStatus.PENDING
    """Current lifecycle status of the operator."""

    error_message: str = ""
    """Human-readable error description set when status is ERROR."""

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

    def startup(self) -> None:
        """Start the operator.

        Called by LightlyStudio after registration. Override this in operators
        that need setup work (venv creation, model download, server
        subprocess, etc.).

        Simple operators that run purely in-process do not need to override
        this — the default sets status to READY without any additional setup.
        """
        self.status = OperatorStatus.READY

    def shutdown(self) -> None:
        """Stop the operator and release resources.

        Called during application shutdown. Override this in operators that
        spawned subprocesses or allocated resources in ``startup()``.
        """
        self.status = OperatorStatus.STOPPED

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
