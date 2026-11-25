"""Delete the caption samples of a collection."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session, col, delete, select

from lightly_studio.models.sample import SampleTable
from lightly_studio.resolvers.sample_resolver import sample_dependent_tables


def delete_caption_samples(session: Session, collection_id: UUID) -> None:
    """Delete the samples of a caption collection with their captions and dependent rows.

    Also deletes samples without a caption, which ``caption_resolver.delete_caption`` keeps.
    Commits twice, because DuckDB rejects the delete of a sample in the transaction that
    deleted its referencing rows.

    Args:
        session: Database session.
        collection_id: ID of the caption collection.
    """
    sample_ids = select(SampleTable.sample_id).where(
        col(SampleTable.collection_id) == collection_id
    )
    for table in sample_dependent_tables.SAMPLE_DEPENDENT_TABLES:
        session.exec(delete(table).where(col(table.sample_id).in_(sample_ids)))
    session.commit()
    session.exec(delete(SampleTable).where(col(SampleTable.collection_id) == collection_id))
    session.commit()
