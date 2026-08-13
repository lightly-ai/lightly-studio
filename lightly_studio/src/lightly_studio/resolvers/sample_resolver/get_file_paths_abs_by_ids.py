"""get_file_paths_abs_by_ids: resolve the absolute file path of samples."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from uuid import UUID

from sqlmodel import Session, col, select
from sqlmodel.sql.expression import Select

from lightly_studio.models.collection import CollectionTable, SampleType
from lightly_studio.models.image import ImageTable
from lightly_studio.models.video import VideoFrameTable, VideoTable
from lightly_studio.utils import batching

_StatementBuilder = Callable[[Sequence[UUID]], Select[tuple[UUID, str]]]


def get_file_paths_abs_by_ids(
    session: Session, collection_id: UUID, sample_ids: Sequence[UUID]
) -> dict[UUID, str]:
    """Resolve the absolute file path of every given sample.

    The sample sub-type table (image, video, or video frame) is derived from the
    collection's ``sample_type``, so callers only pass the collection. Video frames
    resolve to the absolute path of their parent video.

    Args:
        session: The database session.
        collection_id: The collection the samples belong to.
        sample_ids: The sample IDs to resolve.

    Returns:
        A mapping from sample ID to absolute file path. Empty if the collection's
        sample type does not store a file path, e.g. groups.

    Raises:
        ValueError: If the collection does not exist.
    """
    collection = session.get(CollectionTable, collection_id)
    if collection is None:
        raise ValueError(f"Collection with id {collection_id} not found.")
    build_statement = _SAMPLE_TYPE_TO_STATEMENT_BUILDER.get(collection.sample_type)
    if build_statement is None:
        return {}

    file_paths_abs: dict[UUID, str] = {}
    for batch in batching.batched(items=sample_ids):
        file_paths_abs.update(session.exec(build_statement(batch)).all())
    return file_paths_abs


def _image_statement(sample_ids: Sequence[UUID]) -> Select[tuple[UUID, str]]:
    return select(col(ImageTable.sample_id), col(ImageTable.file_path_abs)).where(
        col(ImageTable.sample_id).in_(sample_ids)
    )


def _video_statement(sample_ids: Sequence[UUID]) -> Select[tuple[UUID, str]]:
    return select(col(VideoTable.sample_id), col(VideoTable.file_path_abs)).where(
        col(VideoTable.sample_id).in_(sample_ids)
    )


def _video_frame_statement(sample_ids: Sequence[UUID]) -> Select[tuple[UUID, str]]:
    return (
        select(col(VideoFrameTable.sample_id), col(VideoTable.file_path_abs))
        .join(VideoTable, col(VideoTable.sample_id) == col(VideoFrameTable.parent_sample_id))
        .where(col(VideoFrameTable.sample_id).in_(sample_ids))
    )


_SAMPLE_TYPE_TO_STATEMENT_BUILDER: dict[SampleType, _StatementBuilder] = {
    SampleType.IMAGE: _image_statement,
    SampleType.VIDEO: _video_statement,
    SampleType.VIDEO_FRAME: _video_frame_statement,
}
