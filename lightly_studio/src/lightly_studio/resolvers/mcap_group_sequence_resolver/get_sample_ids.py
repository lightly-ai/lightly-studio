"""Get the sample IDs of the MCAP sequences that match a filter."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session

from lightly_studio.resolvers import mcap_group_sequence_resolver
from lightly_studio.resolvers.mcap_group_sequence_resolver.mcap_sequence_filter import (
    McapSequenceFilter,
)


def get_sample_ids(
    session: Session,
    collection_id: UUID,
    filters: McapSequenceFilter | None = None,
) -> set[UUID]:
    """Get the sample IDs of the MCAP sequences in a collection.

    Args:
        session: The database session.
        collection_id: The ID of the SEQUENCE collection to scope results to.
        filters: The sequence filters to apply.

    Returns:
        The sample IDs of the sequences that match the filters.
    """
    mcap_group_sequence_resolver.resolve_embedding_region(
        session=session, collection_id=collection_id, sequence_filter=filters
    )
    query = (filters or McapSequenceFilter()).build_sample_ids_query(collection_id=collection_id)
    return set(session.exec(query).all())
