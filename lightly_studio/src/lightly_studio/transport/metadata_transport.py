"""Transport protocol for sample metadata and captions."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, Protocol
from uuid import UUID

from lightly_studio.models.caption import CaptionCreate, CaptionView


class MetadataTransport(Protocol):
    """Gets and changes the metadata and the captions of samples."""

    def get(self, sample_ids: Sequence[UUID]) -> dict[UUID, dict[str, Any]]:
        """Get the metadata of samples.

        Values of a complex type, for example `GPSCoordinate`, are objects of that type.

        Returns:
            The metadata for each sample ID. A sample without metadata is not in the result.
        """

    def update(self, sample_metadata: Sequence[tuple[UUID, Mapping[str, Any]]]) -> None:
        """Merge new metadata into the metadata of samples.

        Args:
            sample_metadata: Pairs of a sample ID and the metadata to merge, for example
                `{"weather": "cloudy"}`. Keys that are already set get the new value.

        Raises:
            ValueError: If the type of a value is not the type that the key has.
        """

    def get_captions(self, parent_sample_ids: Sequence[UUID]) -> list[CaptionView]:
        """Get the captions of samples."""

    def add_captions(
        self, parent_collection_id: UUID, captions: Sequence[CaptionCreate]
    ) -> list[UUID]:
        """Add captions to samples.

        Args:
            parent_collection_id: The ID of the collection of the captioned samples.
            captions: The captions to add.

        Returns:
            The IDs of the new captions, in the order of `captions`.
        """

    def delete_captions(self, caption_ids: Sequence[UUID]) -> None:
        """Delete captions by ID.

        Raises:
            ValueError: If a caption does not exist.
        """
