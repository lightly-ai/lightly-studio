"""Computes typicality from embeddings."""

from uuid import UUID

from lightly_mundig import Typicality  # type: ignore[import-untyped]
from sqlmodel import Session

from lightly_studio.dataset.env import LIGHTLY_STUDIO_LICENSE_KEY
from lightly_studio.resolvers import (
    metadata_resolver,
    sample_embedding_resolver,
)

DEFAULT_NUM_NEAREST_NEIGHBORS = 20


def compute_typicality_metadata(
    session: Session,
    collection_id: UUID,
    embedding_model_id: UUID,
    metadata_name: str = "typicality",
) -> None:
    """Computes typicality for each sample in the collection from embeddings.

    Typicality is a measure of how representative a sample is of the collection.
    It is calculated for each sample from its K-nearest neighbors in the
    embedding space.

    The computed typicality values are stored as metadata for each sample.

    Args:
        session:
            The database session.
        collection_id:
            The ID of the collection for which to compute the typicality.
        embedding_model_id:
            The ID of the embedding model to use for the computation.
        metadata_name:
            The name of the metadata field to store the typicality values in.
            Defaults to "typicality".
    """
    license_key = LIGHTLY_STUDIO_LICENSE_KEY
    if license_key is None:
        raise ValueError(
            "LIGHTLY_STUDIO_LICENSE_KEY environment variable is not set. "
            "Please set it to your LightlyStudio license key."
        )

    samples = sample_embedding_resolver.get_all_by_collection_id(
        session=session, collection_id=collection_id, embedding_model_id=embedding_model_id
    )

    embeddings = [sample.embedding for sample in samples]
    typicality = Typicality(embeddings=embeddings, token=license_key)
    typicality_values = typicality.calculate_typicality(
        num_nearest_neighbors=DEFAULT_NUM_NEAREST_NEIGHBORS
    )
    assert len(samples) == len(typicality_values), (
        "The number of samples and computed typicality values must match"
    )

    metadata = [
        (sample.sample_id, {metadata_name: typicality})
        for sample, typicality in zip(samples, typicality_values)
    ]

    metadata_resolver.bulk_update_metadata(session, metadata)
