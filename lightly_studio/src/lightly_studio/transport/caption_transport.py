"""Transport protocol for captions."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol
from uuid import UUID

from lightly_studio.models.caption import CaptionCreate, CaptionView


class CaptionTransport(Protocol):
    """Gets, adds and deletes the captions of samples."""

    def get(self, parent_sample_ids: Sequence[UUID]) -> list[CaptionView]:
        """Get the captions of samples."""

    def add(self, parent_collection_id: UUID, captions: Sequence[CaptionCreate]) -> list[UUID]:
        """Add captions to samples.

        Args:
            parent_collection_id: The ID of the collection of the captioned samples.
            captions: The captions to add.

        Returns:
            The IDs of the new captions, in the order of `captions`.
        """

    def delete(self, caption_ids: Sequence[UUID]) -> None:
        """Delete captions by ID.

        Raises:
            ValueError: If a caption does not exist.
        """
