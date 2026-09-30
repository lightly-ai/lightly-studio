"""Resolver for the range of similarities between a text embedding and a collection."""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import func
from sqlmodel import Session, col, select

from lightly_studio.database import db_vector
from lightly_studio.models.range import FloatRange
from lightly_studio.models.sample import SampleTable
from lightly_studio.models.sample_embedding import SampleEmbeddingTable
from lightly_studio.resolvers import collection_embedding_model_resolver, similarity_utils


def get_similarity_range(
    session: Session,
    collection_id: UUID,
    text_embedding: Sequence[float],
) -> FloatRange | None:
    """Get the min and max similarity between a text embedding and all samples of a collection.

    Uses the embeddings of the default embedding model of the collection, the same as the
    similarity sort and the similarity threshold. Filters are not applied. The similarity is
    ``1 - cosine distance``.

    Args:
        session: The database session.
        collection_id: The collection with the samples to compare against.
        text_embedding: The text embedding to compare with the sample embeddings.

    Returns:
        The similarity range, or None if the collection has no default embedding model or no
        sample has an embedding of that model.
    """
    embedding_model_id = collection_embedding_model_resolver.get_default_by_collection_id(
        session=session, collection_id=collection_id
    )
    if embedding_model_id is None:
        return None

    distance = db_vector.cosine_distance(SampleEmbeddingTable.embedding, list(text_embedding))
    query = (
        select(func.min(distance), func.max(distance))
        .select_from(SampleEmbeddingTable)
        .join(SampleTable, col(SampleTable.sample_id) == col(SampleEmbeddingTable.sample_id))
        .where(col(SampleTable.collection_id) == collection_id)
        .where(col(SampleEmbeddingTable.embedding_model_id) == embedding_model_id)
    )
    min_distance, max_distance = session.exec(query).one()
    if min_distance is None or max_distance is None:
        return None
    return FloatRange(
        min=similarity_utils.distance_to_similarity(distance=max_distance),
        max=similarity_utils.distance_to_similarity(distance=min_distance),
    )
