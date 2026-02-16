"""Base operator class for LightlyStudio plugins."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from uuid import UUID

import requests
from sqlmodel import Session

from lightly_studio.plugins.parameter import BaseParameter


class OperatorStatus(str, Enum):
    """Lifecycle status of an operator."""

    PENDING = "pending"
    STARTING = "starting"
    READY = "ready"
    EXECUTING = "executing"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"


@dataclass
class OperatorProgress:
    """Progress information returned by get_progress()."""

    samples_processed: int = 0
    samples_total: int | None = None
    status: OperatorStatus = OperatorStatus.PENDING
    message: str = ""


@dataclass
class OperatorResult:
    """Result returned by operator execution."""

    success: bool
    message: str


class OperatorAPIError(Exception):
    """Raised when operator API calls fail."""


class BaseOperator(ABC):
    """Base class for all operators.

    Operators may optionally override ``start()`` and ``stop()`` to manage
    their own resources (virtual environments, server subprocesses, model
    loading, etc.).  The studio calls ``start()`` during application startup
    and ``stop()`` during shutdown.

    Progress tracking is built in: operators increment
    ``self._samples_processed`` during ``execute()`` and the studio exposes
    it via the ``get_progress()`` method / API endpoint.
    """

    _status: OperatorStatus = OperatorStatus.PENDING
    _samples_processed: int = 0
    _samples_total: int | None = None
    _error_message: str = ""

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
        self._status = OperatorStatus.READY

    async def stop(self) -> None:
        """Stop the operator and release resources.

        Called during application shutdown.  Override this in operators that
        spawned subprocesses or allocated resources in ``start()``.
        """
        self._status = OperatorStatus.STOPPED

    def get_progress(self) -> OperatorProgress:
        """Return the current progress of this operator.

        The default implementation returns progress from the internal
        counters (``_samples_processed``, ``_samples_total``).
        """
        return OperatorProgress(
            samples_processed=self._samples_processed,
            samples_total=self._samples_total,
            status=self._status,
            message=self._error_message,
        )

    @property
    def status(self) -> OperatorStatus:
        """Return the current lifecycle status."""
        return self._status

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
            OperatorResult with success flag and message.
        """
        # TODO (Jonas 11/2025): The parameters dict should be validated against self.parameters,
        # for now we leave it to the operator implementation.

    # --- Helper methods (optional, for convenience) ---

    def _make_api_request(
        self,
        url: str,
        method: str = "POST",
        headers: dict[str, str] | None = None,
        json_data: dict[str, Any] | None = None,
        timeout: int = 30,
    ) -> dict[str, Any]:
        """Make an HTTP request with error handling.

        Raises:
            OperatorAPIError: If the request fails.
        """
        try:
            response = requests.request(
                method=method,
                url=url,
                headers=headers,
                json=json_data,
                timeout=timeout,
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            raise OperatorAPIError(f"API request failed: {e}") from e

    def _get_samples_by_filter(
        self,
        session: Session,
        collection_id: UUID,
        tag_ids: list[UUID] | None = None,
    ) -> list:
        """Fetch samples matching the tag filter."""
        from lightly_studio.resolvers import sample_resolver
        from lightly_studio.resolvers.sample_resolver.sample_filter import SampleFilter

        sample_filter = SampleFilter(
            collection_id=collection_id,
            tag_ids=tag_ids if tag_ids else None,
        )

        result = sample_resolver.get_filtered_samples(
            session=session,
            filters=sample_filter,
        )
        return list(result.samples)
