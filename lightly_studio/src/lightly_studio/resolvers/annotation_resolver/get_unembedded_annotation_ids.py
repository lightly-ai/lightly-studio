"""Query for object-detection annotations lacking an embedding."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session, col, select

from lightly_studio.models.annotation.annotation_base import AnnotationBaseTable, AnnotationType
from lightly_studio.models.image import ImageTable
from lightly_studio.models.sample import SampleTable
from lightly_studio.models.sample_embedding import SampleEmbeddingTable


def get_unembedded_annotation_ids(
    session: Session,
    annotation_collection_id: UUID,
    embedding_model_id: UUID,
) -> list[UUID]:
    """Return IDs of object-detection annotations in the collection lacking an embedding.

    Results are ordered by source image path so an image's annotations stay adjacent and tend to
    land in the same chunk, preserving the single-open-per-image behaviour of crop embedding.

    Args:
        session: Database session for resolver operations.
        annotation_collection_id: The annotation collection to scan.
        embedding_model_id: Model whose existing embeddings mark an annotation as done.

    Returns:
        Annotation sample IDs that still need an embedding, ordered by image path.
    """
    embedded_ids_subquery = select(col(SampleEmbeddingTable.sample_id)).where(
        col(SampleEmbeddingTable.embedding_model_id) == embedding_model_id
    )
    sample_ids = session.exec(
        select(col(AnnotationBaseTable.sample_id))
        .join(SampleTable, col(SampleTable.sample_id) == col(AnnotationBaseTable.sample_id))
        .join(ImageTable, col(ImageTable.sample_id) == col(AnnotationBaseTable.parent_sample_id))
        .where(col(SampleTable.collection_id) == annotation_collection_id)
        .where(col(AnnotationBaseTable.annotation_type) == AnnotationType.OBJECT_DETECTION)
        .where(col(AnnotationBaseTable.sample_id).notin_(embedded_ids_subquery))
        .order_by(col(ImageTable.file_path_abs))
    ).all()
    return list(sample_ids)
