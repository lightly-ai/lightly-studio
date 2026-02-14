"""Base operator class for LightlyStudio plugins."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any
from uuid import UUID

import requests
from sqlmodel import Session

from lightly_studio.plugins.parameter import BaseParameter


@dataclass
class OperatorResult:
    """Result returned by operator execution."""

    success: bool
    message: str


class OperatorAPIError(Exception):
    """Raised when operator API calls fail."""


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

    def server_package(self) -> str | None:
        """Return a pip-installable package spec for the server environment.

        When this returns a non-None value, the ``PluginServerManager`` will
        create a dedicated virtual environment for this operator's server
        and install the package into it before starting.

        Return ``None`` if the server runs in the main environment (the
        default).
        """
        return None

    def server_command(self) -> list[str] | None:
        """Return the command to start this operator's server subprocess.

        Override this in operators that require a separate server process
        (e.g., a model inference server). Return ``None`` if no server is
        needed (the default).

        Use ``{python}`` as a placeholder for the venv's Python executable.
        """
        return None

    def server_health_path(self) -> str | None:
        """Return the health-check path (e.g. ``"/health"``).

        The full URL is constructed by the ``PluginServerManager`` using
        the assigned port. Return ``None`` if no health check is needed.
        """
        return None

    @property
    def server_url(self) -> str | None:
        """Return the base URL of this operator's managed server.

        Set automatically by ``PluginServerManager`` after port assignment.
        Returns ``None`` if no server is running for this operator.
        """
        port = getattr(self, "_server_port", None)
        if port is None:
            return None
        return f"http://localhost:{port}"

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
