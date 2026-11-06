"""Delete the rows that reference a collection but are not samples."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session, col, delete, select

from lightly_studio.export import export_artifact
from lightly_studio.models.annotation_collection_coverage import (
    AnnotationCollectionCoverageTable,
)
from lightly_studio.models.collection_embedding_model import CollectionEmbeddingModelTable
from lightly_studio.models.embedding_plot import EmbeddingPlotTable
from lightly_studio.models.export_job import ExportJobTable
from lightly_studio.models.tag import TagTable


def delete_dependent_rows(session: Session, collection_id: UUID) -> None:
    """Delete the coverage, embedding model links, embedding plots, export jobs and tags.

    Also removes the files of the export jobs. Does not commit. Delete the samples and the
    tag links of the collection first.

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
    export_paths = session.exec(
        select(ExportJobTable.export_path).where(col(ExportJobTable.collection_id) == collection_id)
    ).all()
    for export_path in export_paths:
        export_artifact.remove_export_artifact(export_path=export_path)
    session.exec(delete(ExportJobTable).where(col(ExportJobTable.collection_id) == collection_id))
    session.exec(delete(TagTable).where(col(TagTable.collection_id) == collection_id))
