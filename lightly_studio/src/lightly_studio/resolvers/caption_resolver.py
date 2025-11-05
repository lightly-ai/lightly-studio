"""Resolvers for caption."""

from __future__ import annotations

from collections.abc import Sequence

from sqlmodel import Session

from lightly_studio.models.caption import CaptionCreate, CaptionTable


def create_many(session: Session, captions: Sequence[CaptionCreate]) -> list[CaptionTable]:
    """Create many captions in bulk.

    Args:
        session: Database session
        captions: The captions to create

    Returns:
        The created captions
    """
    if not captions:
        return []

    db_captions = [CaptionTable.model_validate(caption) for caption in captions]
    session.bulk_save_objects(db_captions)
    session.commit()
    return db_captions
