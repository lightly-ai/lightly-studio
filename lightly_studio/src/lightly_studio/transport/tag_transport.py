"""Transport protocol for sample tags."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Protocol
from uuid import UUID

from lightly_studio.models.tag import TagView


class TagTransport(Protocol):
    """Finds tags and adds them to samples or removes them from samples."""

    def get_by_name(self, collection_id: UUID, tag_name: str) -> TagView | None:
        """Get a tag of a collection by name, or None if it does not exist."""

    def get_names_by_sample_ids(self, sample_ids: Sequence[UUID]) -> dict[UUID, list[str]]:
        """Get the sorted tag names of each sample. A sample without tags is not in the result."""

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

    def split_samples(
        self,
        collection_id: UUID,
        sample_ids: Sequence[UUID],
        tag_sizes: Mapping[str, int],
        seed: int | None,
    ) -> dict[str, int]:
        """Assign each sample to exactly one of new tags, in the given relative sizes.

        Returns:
            The number of samples of each tag, in the order of `tag_sizes`.

        Raises:
            ValueError: If the sizes are not valid, a tag exists already, or there are no samples.
        """
