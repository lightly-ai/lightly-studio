"""Base operator classes for LightlyStudio plugins."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Generic, TypeVar
from uuid import UUID

import requests
from sqlmodel import Session

from lightly_studio.plugins.parameter import BaseParameter

T = TypeVar("T")


@dataclass
class OperatorResult:
    """Result returned by operator execution."""

    success: bool
    message: str


@dataclass
class SampleResult(Generic[T]):
    """Result from processing a single sample."""

    sample_id: UUID
    success: bool
    data: T | None = None
    error_message: str | None = None


class BaseOperator(ABC):
    """Base class for all operators."""

    @property
    def operator_type(self) -> str:
        """Return the type of this operator. Override in subclasses."""
        return "simple"

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


class OperatorAPIError(Exception):
    """Raised when operator API calls fail."""


class BatchSampleOperator(BaseOperator):
    """Operator that processes samples individually in batch.

    Subclass this for operations that iterate over samples (e.g., auto-labeling,
    captioning, detection). Provides helper methods for API calls and sample
    filtering.
    """

    @property
    def operator_type(self) -> str:
        return "batch_sample"

    @abstractmethod
    def execute_batch(
        self,
        *,
        session: Session,
        collection_id: UUID,
        parameters: dict[str, Any],
    ) -> list[SampleResult]:
        """Execute batch processing on filtered samples.

        This method should:
        1. Fetch samples based on tag filter
        2. Process each sample
        3. Return results for each sample

        Args:
            session: Database session.
            collection_id: ID of the collection to operate on.
            parameters: Parameters passed to the operator.

        Returns:
            List of SampleResult objects, one per sample processed.
        """

    def execute(
        self,
        *,
        session: Session,
        collection_id: UUID,
        parameters: dict[str, Any],
    ) -> OperatorResult:
        """Execute by delegating to execute_batch and summarizing results."""
        results = self.execute_batch(
            session=session,
            collection_id=collection_id,
            parameters=parameters,
        )
        processed = sum(1 for r in results if r.success)
        errors = sum(1 for r in results if not r.success)
        total = len(results)
        return OperatorResult(
            success=errors == 0,
            message=f"Processed {processed}/{total} samples ({errors} errors)",
        )

    # Helper methods

    def _make_api_request(
        self,
        url: str,
        method: str = "POST",
        headers: dict[str, str] | None = None,
        json_data: dict[str, Any] | None = None,
        timeout: int = 30,
    ) -> dict[str, Any]:
        """Make an API request with error handling.

        Args:
            url: URL to request.
            method: HTTP method (GET, POST, etc.).
            headers: Optional headers dictionary.
            json_data: Optional JSON data to send.
            timeout: Request timeout in seconds.

        Returns:
            Response JSON as dictionary.

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
        """Fetch samples matching the tag filter.

        Args:
            session: Database session.
            collection_id: Collection to fetch samples from.
            tag_ids: Optional list of tag IDs to filter by.

        Returns:
            List of SampleTable objects matching the filter.
        """
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
