"""Bulk update width/height/status for image samples."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable, Literal
from uuid import UUID

from sqlmodel import Session, col, select

from lightly_studio.models.image import ImageTable

StatusField = Literal["ready", "queued", "failed"]


@dataclass
class ImageUpdate:
    """Update payload for a single image sample."""

    sample_id: UUID
    width: int | None = None
    height: int | None = None
    status_metadata: StatusField | None = None
    status_embeddings: StatusField | None = None


def update_many(session: Session, updates: Iterable[ImageUpdate]) -> int:
    """Update multiple images in one transaction.

    Args:
        session: Active database session.
        updates: Iterable of ``ImageUpdate`` items containing the fields to update.

    Returns:
        Number of rows that were updated.
    """
    updates_list = list(updates)
    if not updates_list:
        return 0

    sample_ids = [update.sample_id for update in updates_list]
    existing_images = session.exec(
        select(ImageTable).where(col(ImageTable.sample_id).in_(sample_ids))
    ).all()
    image_map = {image.sample_id: image for image in existing_images}

    updated_rows = 0
    now = datetime.now(timezone.utc)

    for update in updates_list:
        image = image_map.get(update.sample_id)
        if not image:
            continue

        changed = False
        if update.width is not None:
            image.width = update.width
            changed = True
        if update.height is not None:
            image.height = update.height
            changed = True
        if update.status_metadata is not None:
            image.status_metadata = update.status_metadata
            changed = True
        if update.status_embeddings is not None:
            image.status_embeddings = update.status_embeddings
            changed = True

        if changed:
            image.updated_at = now
            updated_rows += 1

    if updated_rows > 0:
        session.commit()

    return updated_rows
