"""Transport protocol for samples."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol
from uuid import UUID

from lightly_studio.models.sample import SampleView
from lightly_studio.models.sample_query import SamplePage, SampleQueryRequest


# TODO(Iunir, 11/2026): Return a model without DB tables. `SampleView.tags` holds `TagTable`.
class SampleTransport(Protocol):
    """Gets and queries samples."""

    def get_by_ids(self, sample_ids: Sequence[UUID]) -> list[SampleView]:
        """Get samples by ID. Samples that do not exist are not in the result."""

    def query(self, collection_id: UUID, request: SampleQueryRequest) -> SamplePage:
        """Get one page of the image samples of a collection that match a request.

        Raises:
            ValueError: If the cursor is not valid or an include value is not supported.
            QueryExprError: If the query uses an unknown field.
        """

    def get_image_ids_by_paths(
        self, collection_id: UUID, file_paths: Sequence[str]
    ) -> dict[str, UUID]:
        """Get the sample IDs of the images of a collection by file path.

        Callers pass absolute, normalized paths. The lookup compares them exactly to the
        stored image paths. Paths without an image in the collection are not in the result.
        """
