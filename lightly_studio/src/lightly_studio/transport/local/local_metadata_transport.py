"""Metadata transport that calls the resolvers in the same process."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any
from uuid import UUID

from lightly_studio.database import db_manager
from lightly_studio.models.caption import CaptionCreate, CaptionView
from lightly_studio.resolvers import caption_resolver, metadata_resolver


class LocalMetadataTransport:
    """Implements `MetadataTransport` with the persistent database session."""

    def get(self, sample_ids: Sequence[UUID]) -> dict[UUID, dict[str, Any]]:
        """Get the metadata of samples. A sample without metadata is not in the result."""
        rows = metadata_resolver.get_by_sample_ids(
            session=db_manager.persistent_session(), sample_ids=sample_ids
        )
        return {row.sample_id: {key: row.get_value(key) for key in row.data} for row in rows}

    def update(self, sample_metadata: Sequence[tuple[UUID, Mapping[str, Any]]]) -> None:
        """Merge new metadata into the metadata of samples."""
        metadata_resolver.bulk_update_metadata(
            session=db_manager.persistent_session(), sample_metadata=list(sample_metadata)
        )

    def get_captions(self, parent_sample_ids: Sequence[UUID]) -> list[CaptionView]:
        """Get the captions of samples."""
        captions = caption_resolver.get_by_parent_sample_ids(
            session=db_manager.persistent_session(), parent_sample_ids=parent_sample_ids
        )
        return [CaptionView.model_validate(caption) for caption in captions]

    def add_captions(
        self, parent_collection_id: UUID, captions: Sequence[CaptionCreate]
    ) -> list[UUID]:
        """Add captions to samples. Return the IDs of the new captions."""
        return caption_resolver.create_many(
            session=db_manager.persistent_session(),
            parent_collection_id=parent_collection_id,
            captions=captions,
        )

    def delete_captions(self, caption_ids: Sequence[UUID]) -> None:
        """Delete captions by ID."""
        session = db_manager.persistent_session()
        for caption_id in caption_ids:
            caption_resolver.delete_caption(session=session, sample_id=caption_id)
