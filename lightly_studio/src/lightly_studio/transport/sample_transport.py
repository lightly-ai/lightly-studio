"""Transport protocol for samples and captions."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol
from uuid import UUID

from lightly_studio.models.caption import CaptionCreate
from lightly_studio.models.query_expr import QueryExpr
from lightly_studio.models.sample import SampleView


class SampleTransport(Protocol):
    """Finds samples and changes their captions."""

    # TODO(Iunir, 11/2026): Add sort, cursor paging and the related data to include.
    def query(
        self, collection_id: UUID, query_expr: QueryExpr | None, offset: int, limit: int | None
    ) -> list[SampleView]:
        """Get the samples of a collection that match a query.

        Args:
            collection_id: The ID of the collection.
            query_expr: The filter for the samples. None gets all samples.
            offset: The number of samples to skip.
            limit: The maximum number of samples to get. None gets all samples.
        """

    def get_by_ids(self, sample_ids: Sequence[UUID]) -> list[SampleView]:
        """Get samples by ID. Samples that do not exist are not in the result."""

    def add_captions(self, captions: Sequence[CaptionCreate]) -> None:
        """Add captions to samples."""

    def delete_captions(self, caption_ids: Sequence[UUID]) -> None:
        """Delete captions by ID."""
