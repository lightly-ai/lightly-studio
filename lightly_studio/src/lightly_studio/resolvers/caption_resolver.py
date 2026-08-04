"""Resolvers for caption."""

from __future__ import annotations

import math
from collections.abc import Sequence
from uuid import UUID

from sqlmodel import Session, col, delete, select

from lightly_studio.models.caption import CaptionCreate, CaptionTable
from lightly_studio.models.collection import SampleType
from lightly_studio.models.sample import SampleCreate
from lightly_studio.models.temporal_span import TemporalSpanTable
from lightly_studio.resolvers import collection_resolver, sample_resolver
from lightly_studio.utils import batching


class CaptionCreateHelper(CaptionCreate):
    """Helper class to create CaptionTable with sample_id."""

    sample_id: UUID


def create_many(
    session: Session, parent_collection_id: UUID, captions: Sequence[CaptionCreate]
) -> list[UUID]:
    """Create captions for a single collection in bulk.

    It is responsibility of the caller to ensure that all parent samples belong to the same
    collection with ID `parent_collection_id`. This function does not perform this check for
    performance reasons.

    Args:
        session: Database session
        parent_collection_id: UUID of the parent collection of which the caption collection is a
        child
        captions: The captions to create

    Returns:
        List of created CaptionTable sample_ids
    """
    if not captions:
        return []

    # Validate all temporal spans before writing any rows.
    temporal_spans_by_index = {
        index: temporal_span
        for index, caption in enumerate(captions)
        if (temporal_span := _validate_optional_temporal_span(caption=caption)) is not None
    }

    caption_collection_id = collection_resolver.get_or_create_child_collection(
        session=session, collection_id=parent_collection_id, sample_type=SampleType.CAPTION
    )
    sample_ids = sample_resolver.create_many(
        session=session,
        samples=[SampleCreate(collection_id=caption_collection_id) for _ in captions],
    )

    # Bulk create CaptionTable entries and their optional temporal spans using the
    # generated sample_ids.
    db_captions = []
    temporal_spans = []
    for index, (sample_id, caption) in enumerate(zip(sample_ids, captions)):
        db_captions.append(
            CaptionTable.model_validate(
                CaptionCreateHelper(
                    parent_sample_id=caption.parent_sample_id,
                    text=caption.text,
                    sample_id=sample_id,
                )
            )
        )
        temporal_span = temporal_spans_by_index.get(index)
        if temporal_span is not None:
            start_time_s, end_time_s = temporal_span
            temporal_spans.append(
                TemporalSpanTable(
                    sample_id=sample_id,
                    start_time_s=start_time_s,
                    end_time_s=end_time_s,
                )
            )

    session.bulk_save_objects(db_captions)
    session.bulk_save_objects(temporal_spans)
    session.commit()
    return sample_ids


def get_by_ids(session: Session, sample_ids: Sequence[UUID]) -> list[CaptionTable]:
    """Retrieve captions by IDs."""
    results: list[CaptionTable] = []
    for batch in batching.batched(items=set(sample_ids)):
        results.extend(
            session.exec(select(CaptionTable).where(col(CaptionTable.sample_id).in_(batch))).all()
        )
    # Return samples in the same order as the input IDs
    caption_map = {caption.sample_id: caption for caption in results}
    return [caption_map[id_] for id_ in sample_ids if id_ in caption_map]


def update_text(
    session: Session,
    sample_id: UUID,
    text: str,
) -> CaptionTable:
    """Update the text of a caption.

    Args:
        session: Database session for executing the operation.
        sample_id: UUID of the caption to update.
        text: New text.

    Returns:
        The updated caption with the new text.

    Raises:
        ValueError: If the caption is not found.
    """
    captions = get_by_ids(session, [sample_id])
    if not captions:
        raise ValueError(f"Caption with ID {sample_id} not found.")

    caption = captions[0]
    try:
        caption.text = text
        session.commit()
        session.refresh(caption)
        return caption
    except Exception:
        session.rollback()
        raise


def delete_caption(
    session: Session,
    sample_id: UUID,
) -> None:
    """Delete a caption.

    Args:
        session: Database session for executing the operation.
        sample_id: UUID of the caption to update.

    Raises:
        ValueError: If the caption is not found.
    """
    captions = get_by_ids(session=session, sample_ids=[sample_id])
    if len(captions) == 0:
        raise ValueError(f"Caption with ID {sample_id} not found.")

    caption = captions[0]
    # Delete the caption's optional temporal span first to avoid leaving an orphaned row.
    session.exec(delete(TemporalSpanTable).where(col(TemporalSpanTable.sample_id) == sample_id))
    session.delete(caption)
    session.commit()


def _validate_optional_temporal_span(caption: CaptionCreate) -> tuple[float, float] | None:
    """Validate the optional temporal span of a caption to create.

    Args:
        caption: The caption to validate.

    Returns:
        The validated ``(start_time_s, end_time_s)`` tuple, or ``None`` if the caption has
        no temporal span.

    Raises:
        ValueError: If only one of the two bounds is set or the span is invalid.
    """
    start_time_s = caption.start_time_s
    end_time_s = caption.end_time_s
    if start_time_s is None and end_time_s is None:
        return None

    if start_time_s is None or end_time_s is None:
        raise ValueError("Both start_time_s and end_time_s must be provided together.")
    if not math.isfinite(start_time_s) or not math.isfinite(end_time_s):
        raise ValueError("start_time_s and end_time_s must be finite.")
    if start_time_s < 0:
        raise ValueError("start_time_s must be non-negative.")
    if start_time_s >= end_time_s:
        raise ValueError("start_time_s must be less than end_time_s.")

    return (start_time_s, end_time_s)
