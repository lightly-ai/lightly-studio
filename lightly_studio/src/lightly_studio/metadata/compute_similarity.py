"""Computes similarity from embeddings."""

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from lightly_mundig import Similarity  # type: ignore[import-untyped]
from sqlmodel import Session

from lightly_studio.dataset.env import LIGHTLY_STUDIO_LICENSE_KEY
from lightly_studio.errors import TagNotFoundError
from lightly_studio.resolvers import metadata_resolver, sample_embedding_resolver, tag_resolver
from lightly_studio.resolvers.sample_resolver.sample_filter import SampleFilter


def compute_similarity_metadata(
    session: Session,
    key_collection_id: UUID,
    embedding_model_id: UUID,
    query_tag_id: UUID,
    metadata_name: Optional[str] = None,
) -> str:
    """Computes similarity for each sample in the collection from embeddings.

    Similarity is a measure of how similar a sample is to its nearest neighbor
    in the embedding space. It can be used to find duplicates.

    The computed similarity values are stored as metadata for each sample.

    Args:
        session:
            The database session.
        key_collection_id:
            The ID of the collection the similarity is computed on.
        embedding_model_id:
            The ID of the embedding model to use for the computation.
        query_tag_id:
            The ID of the tag describing the query.
        metadata_name:
            The name of the metadata field to store the similarity values in.

    Raises:
        TagNotFoundError if tag with ID `query_tag_id` does not exist.

    Returns:
        The name of the metadata storing the similarity values.
    """
    license_key = LIGHTLY_STUDIO_LICENSE_KEY
    if license_key is None:
        raise ValueError(
            "LIGHTLY_STUDIO_LICENSE_KEY environment variable is not set. "
            "Please set it to your LightlyStudio license key."
        )
    key_samples = sample_embedding_resolver.get_all_by_collection_id(
        session=session, collection_id=key_collection_id, embedding_model_id=embedding_model_id
    )
    key_embeddings = [sample.embedding for sample in key_samples]
    similarity = Similarity(key_embeddings=key_embeddings, token=license_key)

    query_tag = tag_resolver.get_by_id(session=session, tag_id=query_tag_id)
    if query_tag is None:
        raise TagNotFoundError("Query tag with ID {query_tag_id} not found")
    tag_filter = SampleFilter(tag_ids=[query_tag_id])
    query_samples = sample_embedding_resolver.get_all_by_collection_id(
        session=session,
        collection_id=key_collection_id,
        embedding_model_id=embedding_model_id,
        filters=tag_filter,
    )
    query_embeddings = [sample.embedding for sample in query_samples]
    similarity_values = similarity.calculate_similarity(query_embeddings=query_embeddings)
    if metadata_name is None:
        date = datetime.now(timezone.utc)
        # Only use whole seconds, such as "2025-11-26T10:11:56'. This is 19 characters.
        formatted_date = date.isoformat()[:19]
        metadata_name = f"similarity_{query_tag.name}_{formatted_date}"

    metadata = [
        (sample.sample_id, {metadata_name: similarity})
        for sample, similarity in zip(key_samples, similarity_values)
    ]

    metadata_resolver.bulk_update_metadata(session, metadata)
    return metadata_name
