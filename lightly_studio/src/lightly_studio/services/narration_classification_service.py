"""Maintain narration classification validity after caption mutations."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any
from uuid import UUID

from sqlmodel import Session

from lightly_studio.resolvers import metadata_resolver


def mark_stale(
    session: Session,
    parent_sample_id: UUID,
    caption_sample_id: UUID | None = None,
) -> None:
    """Mark an existing narration classification as stale after a caption change."""
    parent_metadata = metadata_resolver.get_by_sample_id(
        session=session,
        sample_id=parent_sample_id,
    )
    if parent_metadata is None or "narration_qa_status" not in parent_metadata.data:
        return
    updates: list[tuple[UUID, Mapping[str, Any]]] = [
        (
            parent_sample_id,
            {
                "narration_classification_complete": False,
                "narration_classification_stale": True,
                "narration_qa_status": "incomplete",
                "narration_classification_error": "Caption data changed; rerun classification.",
            },
        )
    ]
    if caption_sample_id is not None:
        caption_metadata = metadata_resolver.get_by_sample_id(
            session=session,
            sample_id=caption_sample_id,
        )
        if caption_metadata is not None and "narration_label" in caption_metadata.data:
            updates.append((caption_sample_id, {"narration_classification_stale": True}))
    metadata_resolver.bulk_update_metadata(session=session, sample_metadata=updates)
