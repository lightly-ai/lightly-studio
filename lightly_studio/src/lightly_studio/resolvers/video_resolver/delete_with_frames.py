"""Implementation of a scoped delete for a single video and its frames."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session, col, delete, select

from lightly_studio.models.sample import SampleTable
from lightly_studio.models.sample_embedding import SampleEmbeddingTable
from lightly_studio.models.video import VideoFrameTable, VideoTable
from lightly_studio.utils import batching


def delete_with_frames(session: Session, video_sample_id: UUID) -> None:
    """Delete a video and everything indexing created for it.

    Removes the video's frame embeddings, its ``video_frame`` rows, the ``video`` row, and all the
    ``sample`` rows for the video and its frames, in foreign-key-safe order (child -> parent; there
    are no ``ON DELETE CASCADE`` foreign keys). Used to roll back a video that failed to decode
    mid-stream, so a broken video leaves no rows behind. Only rows for the given video are touched.

    Args:
        session: The database session.
        video_sample_id: The sample ID of the video to delete.
    """
    # Capture the frame sample IDs up front: the video_frame rows are deleted below, so their
    # sample rows can no longer be selected via a subquery on VideoFrameTable afterwards.
    frame_sample_ids = list(
        session.exec(
            select(VideoFrameTable.sample_id).where(
                col(VideoFrameTable.parent_sample_id) == video_sample_id
            )
        ).all()
    )
    sample_ids = [*frame_sample_ids, video_sample_id]

    # 1. Frame (and video) embeddings reference sample.sample_id.
    for batch in batching.batched(items=sample_ids):
        session.exec(
            delete(SampleEmbeddingTable).where(col(SampleEmbeddingTable.sample_id).in_(batch))
        )
    # 2. video_frame rows reference both sample.sample_id and video.sample_id.
    session.exec(
        delete(VideoFrameTable).where(col(VideoFrameTable.parent_sample_id) == video_sample_id)
    )
    # DuckDB validates foreign keys against committed state, so child deletes must be committed
    # before deleting their parent rows. PostgreSQL also supports these intermediate commits.
    session.commit()
    # 3. The video row references sample.sample_id.
    session.exec(delete(VideoTable).where(col(VideoTable.sample_id) == video_sample_id))
    session.commit()
    # 4. The sample rows for the frames and the video itself.
    for batch in batching.batched(items=sample_ids):
        session.exec(delete(SampleTable).where(col(SampleTable.sample_id).in_(batch)))

    session.commit()
