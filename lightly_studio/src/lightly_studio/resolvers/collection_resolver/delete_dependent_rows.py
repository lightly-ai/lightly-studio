"""Delete the rows that reference a collection but are not samples."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session, col, delete

from lightly_studio.models.annotation_collection_coverage import (
    AnnotationCollectionCoverageTable,
)
from lightly_studio.models.collection_embedding_model import CollectionEmbeddingModelTable
from lightly_studio.models.embedding_plot import EmbeddingPlotTable
from lightly_studio.models.tag import TagTable


def delete_dependent_rows(session: Session, collection_id: UUID) -> None:
    """Delete the coverage, embedding model links, embedding plots and tags of a collection.

    Does not commit. Delete the samples and the tag links of the collection first.

    Args:
        session: Database session.
        collection_id: ID of the collection.
    """
    session.exec(
        delete(AnnotationCollectionCoverageTable).where(
            col(AnnotationCollectionCoverageTable.annotation_collection_id) == collection_id
        )
    )
    session.exec(
        delete(CollectionEmbeddingModelTable).where(
            col(CollectionEmbeddingModelTable.collection_id) == collection_id
        )
    )
    session.exec(
        delete(EmbeddingPlotTable).where(col(EmbeddingPlotTable.collection_id) == collection_id)
    )
    session.exec(delete(TagTable).where(col(TagTable.collection_id) == collection_id))
