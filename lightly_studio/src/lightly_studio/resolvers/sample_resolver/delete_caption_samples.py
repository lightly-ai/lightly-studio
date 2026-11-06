"""Delete the caption samples of a collection."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session, col, delete, select

from lightly_studio.models.caption import CaptionTable
from lightly_studio.models.metadata import SampleMetadataTable
from lightly_studio.models.sample import SampleTable, SampleTagLinkTable
from lightly_studio.models.sample_embedding import SampleEmbeddingTable
from lightly_studio.models.temporal_span import TemporalSpanTable


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
    for table in (
        CaptionTable,
        TemporalSpanTable,
        SampleTagLinkTable,
        SampleEmbeddingTable,
        SampleMetadataTable,
    ):
        session.exec(delete(table).where(col(table.sample_id).in_(sample_ids)))
    session.commit()
    session.exec(delete(SampleTable).where(col(SampleTable.collection_id) == collection_id))
    session.commit()
