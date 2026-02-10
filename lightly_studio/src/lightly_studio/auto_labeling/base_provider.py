"""Base provider class for auto-labeling."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Generic, TypeVar
from uuid import UUID

import requests
from sqlmodel import Session

from lightly_studio.models.sample import SampleTable

T = TypeVar("T")


@dataclass
class ProviderResult(Generic[T]):
    """Result from processing a single sample."""

    sample_id: UUID
    success: bool
    data: T | None = None
    error_message: str | None = None


@dataclass
class ProviderParameter:
    """Parameter definition for provider UI."""

    name: str
    type: str  # "string", "int", "float", "bool", "tag_filter", "json"
    description: str = ""
    default: Any = None
    required: bool = True


class BaseAutoLabelingProvider(ABC):
    """Base class for all auto-labeling providers."""

    @property
    @abstractmethod
    def provider_id(self) -> str:
        """Unique identifier for this provider."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable name for this provider."""

    @property
    @abstractmethod
    def description(self) -> str:
        """Description of what this provider does."""

    @property
    @abstractmethod
    def parameters(self) -> list[ProviderParameter]:
        """Parameters this provider requires."""

    @abstractmethod
    def execute(
        self,
        *,
        session: Session,
        collection_id: UUID,
        parameters: dict[str, Any],
    ) -> list[ProviderResult]:
        """Execute auto-labeling on filtered samples.

        This method should:
        1. Fetch samples based on tag filter
        2. Process each sample via external API
        3. Return results for each sample

        Args:
            session: Database session.
            collection_id: ID of the collection to operate on.
            parameters: Parameters passed to the provider.

        Returns:
            List of ProviderResult objects, one per sample processed.
        """

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

        Handles common API patterns:
        - Authentication
        - Retry logic
        - Error handling
        - Rate limiting

        Args:
            url: URL to request.
            method: HTTP method (GET, POST, etc.).
            headers: Optional headers dictionary.
            json_data: Optional JSON data to send.
            timeout: Request timeout in seconds.

        Returns:
            Response JSON as dictionary.

        Raises:
            ProviderAPIError: If the request fails.
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
            raise ProviderAPIError(f"API request failed: {e}") from e

    def _get_samples_by_filter(
        self,
        session: Session,
        collection_id: UUID,
        tag_ids: list[UUID] | None = None,
    ) -> list[SampleTable]:
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


class ProviderAPIError(Exception):
    """Raised when provider API calls fail."""

    pass
