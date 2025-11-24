"""Resolvers for caption."""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from sqlmodel import Session, col, select

from lightly_studio.models.caption import CaptionCreate, CaptionTable
from lightly_studio.models.dataset import SampleType
from lightly_studio.models.sample import SampleCreate
from lightly_studio.resolvers import dataset_resolver, sample_resolver


class CaptionCreateHelper(CaptionCreate):
    """Helper class to create CaptionTable with sample_id."""

    sample_id: UUID


def create_many(
    session: Session, parent_dataset_id: UUID, captions: Sequence[CaptionCreate]
) -> list[UUID]:
    """Create captions for a single dataset in bulk.

    It is responsibility of the caller to ensure that all parent samples belong to the same
    dataset with ID `parent_dataset_id`. This function does not perform this check for performance
    reasons.

    Args:
        session: Database session
        parent_dataset_id: UUID of the parent dataset of which the caption dataset is a child
        captions: The captions to create

    Returns:
        List of created CaptionTable sample_ids
    """
    if not captions:
        return []

    caption_dataset_id = dataset_resolver.get_or_create_child_dataset(
        session=session, dataset_id=parent_dataset_id, sample_type=SampleType.CAPTION
    )
    sample_ids = sample_resolver.create_many(
        session=session,
        samples=[SampleCreate(dataset_id=caption_dataset_id) for _ in captions],
    )

    # Bulk create CaptionTable entries using the generated sample_ids.
    db_captions = [
        CaptionTable.model_validate(
            CaptionCreateHelper(
                parent_sample_id=sample.parent_sample_id,
                text=sample.text,
                sample_id=sample_id,
            )
        )
        for sample_id, sample in zip(sample_ids, captions)
    ]
    session.bulk_save_objects(db_captions)
    session.commit()
    return sample_ids


def get_by_ids(session: Session, sample_ids: Sequence[UUID]) -> list[CaptionTable]:
    """Retrieve captions by IDs."""
    results = session.exec(
        select(CaptionTable).where(col(CaptionTable.sample_id).in_(set(sample_ids)))
    ).all()
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
    session.commit()
    session.delete(caption)
    session.commit()
