"""Query for croppable annotations lacking an embedding."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session, col, select

from lightly_studio.models.annotation.annotation_base import AnnotationBaseTable, AnnotationType
from lightly_studio.models.image import ImageTable
from lightly_studio.models.sample import SampleTable
from lightly_studio.models.sample_embedding import SampleEmbeddingTable

# Annotation types whose crops are embedded. Both store a bounding box, so both are croppable;
# classification-style annotations are excluded because they have no box.
_CROPPABLE_ANNOTATION_TYPES = [
    AnnotationType.OBJECT_DETECTION,
    AnnotationType.SEGMENTATION_MASK,
]


def get_unembedded_annotation_ids(
    session: Session,
    annotation_collection_id: UUID,
    embedding_model_id: UUID,
) -> list[UUID]:
    """Return IDs of croppable annotations in the collection lacking an embedding.

    Object-detection and segmentation-mask annotations are both included; each annotation
    source is assumed to hold a single annotation type.

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
        .where(col(AnnotationBaseTable.annotation_type).in_(_CROPPABLE_ANNOTATION_TYPES))
        .where(col(AnnotationBaseTable.sample_id).notin_(embedded_ids_subquery))
        .order_by(col(ImageTable.file_path_abs))
    ).all()
    return list(sample_ids)
