"""Builds the channel summary of an MCAP sequence, read from the database."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session

from lightly_studio.models.mcap_sequence_summary import MCAPSequenceSummary
from lightly_studio.resolvers import mcap_group_sequence_resolver, mcap_resolver, sequence_resolver


def get_mcap_sequence_summary(
    session: Session, dataset_id: UUID, sequence_id: UUID
) -> MCAPSequenceSummary | None:
    """Builds an MCAP sequence's channel summary from its indexed component schema.

    Reads only the database: the sequence and the component slots an indexing script
    attached to its GROUP collection. Does not open the sequence's file, so a sequence
    that is not an MCAP sequence or has not been indexed yet has no summary to return.

    Args:
        session: The database session.
        dataset_id: The dataset the sequence is expected to belong to.
        sequence_id: The MCAP sequence (sample_id) to summarize.

    Returns:
        The sequence's channel summary, or `None` if the sequence does not exist,
        does not belong to `dataset_id`, or has not been indexed as an MCAP sequence.
    """
    try:
        info = mcap_group_sequence_resolver.get_info(session=session, sample_id=sequence_id)
    except ValueError:
        return None

    if info is None:
        return None

    if info.recording.dataset_id != dataset_id:
        return None

    start_log_time_ns = mcap_resolver.get_start_log_time_ns(
        session=session, sequence_id=sequence_id
    )
    start_timestamp_ns = sequence_resolver.get_start_timestamp_ns(
        session=session, sequence_id=sequence_id
    )
    return MCAPSequenceSummary.from_info(
        info=info,
        start_log_time_ns=start_log_time_ns,
        start_timestamp_ns=start_timestamp_ns,
    )
