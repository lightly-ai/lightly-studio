"""Get the lowest object track numbers that a dataset does not use."""

from __future__ import annotations

import itertools
from uuid import UUID

from sqlmodel import Session, col, select

from lightly_studio.models.annotation.object_track import ObjectTrackTable


def get_free_numbers(session: Session, dataset_id: UUID, count: int) -> list[int]:
    """Return the `count` lowest positive object_track_numbers that the dataset does not use.

    Numbers of deleted tracks are used again, so the numbers have no gaps.
    """
    used_numbers = set(
        session.exec(
            select(ObjectTrackTable.object_track_number).where(
                col(ObjectTrackTable.dataset_id) == dataset_id
            )
        ).all()
    )
    free_numbers = (number for number in itertools.count(start=1) if number not in used_numbers)
    return list(itertools.islice(free_numbers, count))
