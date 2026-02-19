"""Base operator class for LightlyStudio plugins."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any
from uuid import UUID

from sqlmodel import Session

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
    """Base class for all operators.

    Operators may optionally override ``start()`` and ``stop()`` to manage
    their own resources (virtual environments, server subprocesses, model
    loading, etc.). LightlyStudio calls ``start()`` during application startup
    and ``stop()`` during shutdown.
    """

    status: OperatorStatus = OperatorStatus.PENDING
    error_message: str = ""

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

    # --- Lifecycle methods ---

    async def start(self) -> None:
        """Start the operator.

        Called by the studio after registration.  Override this in operators
        that need setup work (venv creation, model download, server
        subprocess, etc.).  The studio awaits this with a configurable
        timeout.

        Simple operators that run purely in-process do not need to override
        this — the default is a no-op that sets status to READY.
        """
        self.status = OperatorStatus.READY

    async def stop(self) -> None:
        """Stop the operator and release resources.

        Called during application shutdown.  Override this in operators that
        spawned subprocesses or allocated resources in ``start()``.
        """
        self.status = OperatorStatus.STOPPED

    # --- Core execution ---

    @abstractmethod
    def execute(
        self,
        *,
        session: Session,
        collection_id: UUID,
        parameters: dict[str, Any],
    ) -> OperatorResult:
        """Execute the operator with the given parameters.

        Args:
            session: Database session.
            collection_id: ID of the collection to operate on.
            parameters: Parameters passed to the operator.

        Returns:
            Dictionary with 'success' (bool) and 'message' (str) keys.
        """
        # TODO (Jonas 11/2025): The parameters dict should be validated against self.parameters,
        # for now we leave it to the operator implementation.
