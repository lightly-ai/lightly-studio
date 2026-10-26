"""Query for croppable annotations lacking an embedding."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import and_
from sqlmodel import Session, col

from lightly_studio.models.annotation.annotation_base import AnnotationBaseTable
from lightly_studio.models.sample_embedding import SampleEmbeddingTable
from lightly_studio.resolvers import annotation_resolver


def get_unembedded_annotation_ids(
    session: Session,
    annotation_collection_id: UUID,
    embedding_model_id: UUID | None,
) -> list[UUID]:
    """Return IDs of croppable annotations in the collection lacking an embedding.

    Object-detection and segmentation-mask annotations are both included; each annotation
    source is assumed to hold a single annotation type.

    Results are ordered by source image path so an image's annotations stay adjacent and tend to
    land in the same chunk, preserving the single-open-per-image behaviour of crop embedding.

    Args:
        session: Database session for resolver operations.
        annotation_collection_id: The annotation collection to scan.
        embedding_model_id: Model whose existing embeddings mark an annotation as done. `None`
            means the collection has no default model yet, so every croppable annotation is
            returned.

    Returns:
        Annotation sample IDs that still need an embedding, ordered by image path.
    """
    query = annotation_resolver.build_croppable_annotations_query(
        annotation_collection_id=annotation_collection_id
    )
    if embedding_model_id is not None:
        query = query.outerjoin(
            SampleEmbeddingTable,
            and_(
                col(SampleEmbeddingTable.sample_id) == col(AnnotationBaseTable.sample_id),
                col(SampleEmbeddingTable.embedding_model_id) == embedding_model_id,
            ),
        ).where(col(SampleEmbeddingTable.sample_id).is_(None))
    return list(session.exec(query).all())
