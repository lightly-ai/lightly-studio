"""Nearest-neighbour query over annotation crop embeddings."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from uuid import UUID

from sqlmodel import Session, col, select

from lightly_studio.database import db_vector
from lightly_studio.models.annotation.annotation_base import AnnotationBaseTable
from lightly_studio.models.sample import SampleTable
from lightly_studio.models.sample_embedding import SampleEmbeddingTable
from lightly_studio.resolvers import similarity_utils


@dataclass(frozen=True)
class AnnotationNeighbour:
    """A labeled annotation near a query embedding.

    Attributes:
        annotation_label_id: Label of the neighbouring annotation.
        similarity: Cosine similarity to the query embedding.
    """

    annotation_label_id: UUID
    similarity: float


def get_nearest_labeled_annotations(  # noqa: PLR0913
    session: Session,
    annotation_collection_id: UUID,
    embedding_model_id: UUID,
    query_embedding: Sequence[float],
    exclude_annotation_id: UUID,
    limit: int,
) -> list[AnnotationNeighbour]:
    """Return the annotations whose crop embeddings are nearest to a query embedding.

    Args:
        session: Database session for resolver operations.
        annotation_collection_id: Only annotations in this annotation collection are searched.
        embedding_model_id: Only embeddings of this model are searched.
        query_embedding: The embedding to compare against.
        exclude_annotation_id: Annotation to leave out, usually the one being predicted.
        limit: Maximum number of neighbours to return.

    Returns:
        Neighbours ordered by similarity, highest first.
    """
    distance = db_vector.cosine_distance(SampleEmbeddingTable.embedding, list(query_embedding))
    rows = session.exec(
        select(col(AnnotationBaseTable.annotation_label_id), distance)
        .join(SampleTable, col(SampleTable.sample_id) == col(AnnotationBaseTable.sample_id))
        .join(
            SampleEmbeddingTable,
            col(SampleEmbeddingTable.sample_id) == col(AnnotationBaseTable.sample_id),
        )
        .where(col(SampleTable.collection_id) == annotation_collection_id)
        .where(col(SampleEmbeddingTable.embedding_model_id) == embedding_model_id)
        .where(col(AnnotationBaseTable.sample_id) != exclude_annotation_id)
        .order_by(distance)
        .limit(limit)
    ).all()
    return [
        AnnotationNeighbour(
            annotation_label_id=label_id,
            similarity=similarity_utils.distance_to_similarity(distance=row_distance),
        )
        for label_id, row_distance in rows
    ]
