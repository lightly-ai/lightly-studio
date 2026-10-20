"""Get the camera keyframes of MCAP sequences."""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from sqlmodel import Session, col, select

from lightly_studio.database import db_array
from lightly_studio.models.group import SampleGroupLinkTable
from lightly_studio.models.mcap import McapTable
from lightly_studio.models.mcap_group_sequence import McapSequenceKeyframe
from lightly_studio.models.sample import SampleTable
from lightly_studio.models.sequence import SampleSequenceLinkTable


def get_keyframes(
    session: Session,
    sequence_sample_ids: Sequence[UUID],
    video_frame_collection_id: UUID,
) -> dict[UUID, list[McapSequenceKeyframe]]:
    """Get the independently decodable keyframes of one camera slot for each sequence.

    Only frames where ``keyframe_log_time_ns == log_time_ns`` are returned. These frames
    decode without any preceding reference frame.

    Args:
        session: Database session for executing queries.
        sequence_sample_ids: The sample IDs of the sequences.
        video_frame_collection_id: The collection of the camera slot to read frames of,
            e.g. from ``get_first_video_frame_collection_id``.

    Returns:
        The keyframes of each sequence, ordered by log time. A sequence without a
        keyframe in the slot has no entry.
    """
    if not sequence_sample_ids:
        return {}
    query = (
        select(
            SampleSequenceLinkTable.sequence_sample_id,
            McapTable.channel_id,
            McapTable.log_time_ns,
        )
        .join(
            SampleGroupLinkTable,
            col(SampleGroupLinkTable.parent_sample_id) == col(SampleSequenceLinkTable.sample_id),
        )
        .join(McapTable, col(McapTable.sample_id) == col(SampleGroupLinkTable.sample_id))
        .join(SampleTable, col(SampleTable.sample_id) == col(McapTable.sample_id))
        .where(
            db_array.in_array(
                column=col(SampleSequenceLinkTable.sequence_sample_id),
                values=sequence_sample_ids,
            )
        )
        .where(col(SampleTable.collection_id) == video_frame_collection_id)
        .where(col(McapTable.keyframe_log_time_ns) == col(McapTable.log_time_ns))
        .order_by(col(SampleSequenceLinkTable.sequence_sample_id), col(McapTable.log_time_ns).asc())
    )
    keyframes: dict[UUID, list[McapSequenceKeyframe]] = {}
    for sequence_sample_id, channel_id, log_time_ns in session.exec(query).all():
        keyframes.setdefault(sequence_sample_id, []).append(
            McapSequenceKeyframe(channel_id=channel_id, log_time_ns=log_time_ns)
        )
    return keyframes
