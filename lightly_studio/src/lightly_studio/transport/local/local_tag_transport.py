"""Tag transport that calls the resolvers in the same process."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from uuid import UUID

from lightly_studio.database import db_manager
from lightly_studio.models.tag import TagView
from lightly_studio.resolvers import tag_resolver


class LocalTagTransport:
    """Implements `TagTransport` with the persistent database session."""

    def get_by_name(self, collection_id: UUID, tag_name: str) -> TagView | None:
        """Get a tag of a collection by name, or None if it does not exist."""
        tag = tag_resolver.get_by_name(
            session=db_manager.persistent_session(),
            tag_name=tag_name,
            collection_id=collection_id,
        )
        return None if tag is None else TagView.model_validate(tag)

    def get_names_by_sample_ids(self, sample_ids: Sequence[UUID]) -> dict[UUID, list[str]]:
        """Get the sorted tag names of each sample. A sample without tags is not in the result."""
        return tag_resolver.get_names_by_sample_ids(
            session=db_manager.persistent_session(), sample_ids=sample_ids
        )

    def add_to_samples(
        self, collection_id: UUID, tag_name: str, sample_ids: Sequence[UUID]
    ) -> None:
        """Add a tag to samples. Create the tag if it does not exist."""
        session = db_manager.persistent_session()
        tag = tag_resolver.get_or_create_sample_tag_by_name(
            session=session, collection_id=collection_id, tag_name=tag_name
        )
        tag_resolver.add_sample_ids_to_tag_id(
            session=session, tag_id=tag.tag_id, sample_ids=list(sample_ids)
        )

    def remove_from_samples(
        self, collection_id: UUID, tag_name: str, sample_ids: Sequence[UUID]
    ) -> None:
        """Remove a tag from samples. A tag that does not exist changes nothing."""
        session = db_manager.persistent_session()
        tag = tag_resolver.get_by_name(
            session=session, tag_name=tag_name, collection_id=collection_id
        )
        if tag is None:
            return
        tag_resolver.remove_sample_ids_from_tag_id(
            session=session, tag_id=tag.tag_id, sample_ids=list(sample_ids)
        )

    def split_samples(
        self,
        collection_id: UUID,
        sample_ids: Sequence[UUID],
        tag_sizes: Mapping[str, int],
        seed: int | None,
    ) -> dict[str, int]:
        """Assign each sample to exactly one of new tags, in the given relative sizes."""
        return tag_resolver.split_samples(
            session=db_manager.persistent_session(),
            collection_id=collection_id,
            sample_ids=sample_ids,
            splits=[
                tag_resolver.SplitDefinition(tag_name=name, relative_size=size)
                for name, size in tag_sizes.items()
            ],
            seed=seed,
        )
