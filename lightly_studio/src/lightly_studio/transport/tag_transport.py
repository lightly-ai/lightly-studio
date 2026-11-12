"""Transport protocol for sample tags."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol
from uuid import UUID

from lightly_studio.models.tag import TagView


class TagTransport(Protocol):
    """Finds tags and adds them to samples or removes them from samples."""

    def get_by_name(self, collection_id: UUID, tag_name: str) -> TagView | None:
        """Get a tag of a collection by name, or None if it does not exist."""

    def add_to_samples(
        self, collection_id: UUID, tag_name: str, sample_ids: Sequence[UUID]
    ) -> None:
        """Add a tag to samples. Create the tag if it does not exist.

        Samples that already have the tag do not change.
        """

    def remove_from_samples(
        self, collection_id: UUID, tag_name: str, sample_ids: Sequence[UUID]
    ) -> None:
        """Remove a tag from samples.

        Samples without the tag do not change.
        """
