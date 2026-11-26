"""Caption transport that calls the resolvers in the same process."""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from lightly_studio.database import db_manager
from lightly_studio.models.caption import CaptionCreate, CaptionView
from lightly_studio.resolvers import caption_resolver


class LocalCaptionTransport:
    """Implements `CaptionTransport` with the persistent database session."""

    def get(self, parent_sample_ids: Sequence[UUID]) -> list[CaptionView]:
        """Get the captions of samples."""
        captions = caption_resolver.get_by_parent_sample_ids(
            session=db_manager.persistent_session(), parent_sample_ids=parent_sample_ids
        )
        return [CaptionView.model_validate(caption) for caption in captions]

    def add(self, parent_collection_id: UUID, captions: Sequence[CaptionCreate]) -> list[UUID]:
        """Add captions to samples. Return the IDs of the new captions."""
        return caption_resolver.create_many(
            session=db_manager.persistent_session(),
            parent_collection_id=parent_collection_id,
            captions=captions,
        )

    def delete(self, caption_ids: Sequence[UUID]) -> None:
        """Delete captions by ID."""
        session = db_manager.persistent_session()
        for caption_id in caption_ids:
            caption_resolver.delete_caption(session=session, sample_id=caption_id)
