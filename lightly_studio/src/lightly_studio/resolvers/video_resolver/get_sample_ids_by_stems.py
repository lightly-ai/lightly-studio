"""Implementation of get_sample_ids_by_stems function for videos."""

from __future__ import annotations

from pathlib import Path
from uuid import UUID

from sqlmodel import Session, col, select

from lightly_studio.models.sample import SampleTable
from lightly_studio.models.video import VideoTable


def get_sample_ids_by_stems(
    session: Session,
    collection_id: UUID,
) -> dict[str, UUID]:
    """Build a mapping from video identifier stems to sample IDs in a collection.

    Each video is indexed by ``Path(file_name).stem`` and ``Path(file_path_abs).stem``.
    If the same stem maps to multiple videos, a ``ValueError`` is raised.

    Args:
        session: The database session.
        collection_id: The ID of the video collection to scope results to.

    Returns:
        A mapping from stem to sample_id.
    """
    query = (
        select(VideoTable).join(SampleTable).where(col(SampleTable.collection_id) == collection_id)
    )
    videos = session.exec(query).all()

    stem_to_sample_id: dict[str, UUID] = {}
    for video in videos:
        for stem in {Path(video.file_name).stem, Path(video.file_path_abs).stem}:
            existing = stem_to_sample_id.get(stem)
            if existing is not None and existing != video.sample_id:
                raise ValueError(
                    f"Duplicate video stem '{stem}' in collection {collection_id}. "
                    "Video identifiers must be unique."
                )
            stem_to_sample_id[stem] = video.sample_id

    return stem_to_sample_id
