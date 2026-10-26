"""Query for croppable annotations whose embedding is missing or stale."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import ColumnElement, and_, or_
from sqlmodel import Session, col

from lightly_studio.models.annotation.annotation_base import AnnotationBaseTable
from lightly_studio.models.annotation.object_detection import ObjectDetectionAnnotationTable
from lightly_studio.models.annotation.segmentation import SegmentationAnnotationTable
from lightly_studio.models.sample_embedding import SampleEmbeddingTable
from lightly_studio.resolvers.annotation_resolver import (
    croppable_annotations_query,
    get_annotation_crops,
)


def get_unembedded_annotation_ids(
    session: Session,
    annotation_collection_id: UUID,
    embedding_model_id: UUID | None,
) -> list[UUID]:
    """Return IDs of croppable annotations whose embedding is missing or stale.

    An embedding is stale when it was computed from a different box than the current one. An
    embedding without a stored box is not stale.

    Object-detection and segmentation-mask annotations are both included; each annotation
    source is assumed to hold a single annotation type.

    Results are ordered by source image path so an image's annotations stay adjacent and tend to
    land in the same chunk, preserving the single-open-per-image behaviour of crop embedding.

    Args:
        session: Database session for resolver operations.
        annotation_collection_id: The annotation collection to scan.
        embedding_model_id: Model whose up-to-date embeddings mark an annotation as done. `None`
            means the collection has no default model yet, so every croppable annotation is
            returned.

    Returns:
        Annotation sample IDs that need an embedding, ordered by image path.
    """
    query = croppable_annotations_query.build(annotation_collection_id=annotation_collection_id)
    if embedding_model_id is None:
        return list(session.exec(query).all())
    query = query.outerjoin(
        SampleEmbeddingTable,
        and_(
            col(SampleEmbeddingTable.sample_id) == col(AnnotationBaseTable.sample_id),
            col(SampleEmbeddingTable.embedding_model_id) == embedding_model_id,
        ),
    )
    is_missing = col(SampleEmbeddingTable.sample_id).is_(None)
    query = (
        query.outerjoin(
            ObjectDetectionAnnotationTable,
            col(ObjectDetectionAnnotationTable.sample_id) == col(AnnotationBaseTable.sample_id),
        )
        .outerjoin(
            SegmentationAnnotationTable,
            col(SegmentationAnnotationTable.sample_id) == col(AnnotationBaseTable.sample_id),
        )
        .where(or_(is_missing, _is_stale_clause()))
    )
    return list(session.exec(query).all())


def _is_stale_clause() -> ColumnElement[bool]:
    """The stored fingerprint differs from the current crop fingerprint.

    A NULL fingerprint compares as NULL, so it is not stale.
    """
    return (
        col(SampleEmbeddingTable.source_fingerprint)
        != get_annotation_crops.build_crop_fingerprint_expression()
    )
