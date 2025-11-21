"""Computes similarity from embeddings."""

from uuid import UUID

from lightly_mundig import Similarity  # type: ignore[import-untyped]
from sqlmodel import Session

from lightly_studio.dataset.env import LIGHTLY_STUDIO_LICENSE_KEY
from lightly_studio.resolvers import metadata_resolver, sample_embedding_resolver
from lightly_studio.resolvers.sample_resolver.sample_filter import SampleFilter


def compute_similarity_metadata(
    session: Session,
    key_dataset_id: UUID,
    embedding_model_id: UUID,
    query_tag_id: UUID,
    metadata_name: str,
) -> None:
    """Computes similarity for each sample in the dataset from embeddings.

    Similarity is a measure of how similar a sample is to its nearest neighbor
    in the embedding space. It can be used to find duplicates.

    The computed similarity values are stored as metadata for each sample.

    Args:
        session:
            The database session.
        key_dataset_id:
            The ID of the dataset the similarity is computed on.
        embedding_model_id:
            The ID of the embedding model to use for the computation.
        query_tag_id:
            The ID of the tag describing the query.
        metadata_name:
            The name of the metadata field to store the similarity values in.
            Defaults to "similarity".
    """
    license_key = LIGHTLY_STUDIO_LICENSE_KEY
    if license_key is None:
        raise ValueError(
            "LIGHTLY_STUDIO_LICENSE_KEY environment variable is not set. "
            "Please set it to your LightlyStudio license key."
        )

    key_samples = sample_embedding_resolver.get_all_by_dataset_id(
        session=session, dataset_id=key_dataset_id, embedding_model_id=embedding_model_id
    )
    key_embeddings = [sample.embedding for sample in key_samples]
    similarity = Similarity(key_embeddings=key_embeddings, token=license_key)

    tag_filter = SampleFilter(tag_ids=[query_tag_id])
    query_samples = sample_embedding_resolver.get_all_by_dataset_id(
        session=session,
        dataset_id=key_dataset_id,
        embedding_model_id=embedding_model_id,
        filters=tag_filter,
    )
    query_embeddings = [sample.embedding for sample in query_samples]
    similarity_values = similarity.calculate_similarity(query_embeddings=query_embeddings)

    metadata = [
        (sample.sample_id, {metadata_name: similarity})
        for sample, similarity in zip(key_samples, similarity_values)
    ]

    metadata_resolver.bulk_update_metadata(session, metadata)
