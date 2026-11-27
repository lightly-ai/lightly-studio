"""Helpers for setting up the sampling tests."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any
from uuid import UUID

from sqlmodel import Session

from lightly_studio.core.dataset_query.dataset_query import DatasetQuery
from lightly_studio.resolvers import collection_resolver, metadata_resolver
from tests.helpers_resolvers import (
    create_collection,
    create_embedding_model,
    create_image,
    create_sample_embedding,
)


def fill_db_with_samples_and_metadata(
    session: Session,
    metadata: list[Any],
    metadata_key: str,
) -> UUID:
    """Creates a collection and fills it with sample and metadata."""
    collection = create_collection(session)
    for i, data in enumerate(metadata):
        image_table = create_image(
            session=session,
            collection_id=collection.collection_id,
            file_path_abs=f"sample_{i}.jpg",
        )
        metadata_resolver.bulk_update_metadata(
            session=session, sample_metadata=[(image_table.sample_id, {metadata_key: data})]
        )
    return collection.collection_id


def fill_db_metadata(
    session: Session, collection_id: UUID, metadata: list[Any], metadata_key: str
) -> None:
    """Fetches a collection from the database and adds metadata to it."""
    collection = collection_resolver.get_by_id(session, collection_id)
    assert collection is not None
    query = DatasetQuery(collection, session)
    metadata_resolver.bulk_update_metadata(
        session=session,
        sample_metadata=[
            (sample.sample_id, {metadata_key: data}) for data, sample in zip(metadata, query)
        ],
    )


def create_images_with_embeddings(
    session: Session, embeddings_per_image: Sequence[Mapping[str, list[float]]]
) -> tuple[UUID, list[UUID]]:
    """Create one image per entry with the given embedding of each named model.

    Returns:
        The collection ID and the sample IDs in entry order.
    """
    collection_id = create_collection(session=session).collection_id
    model_names = dict.fromkeys(name for embeddings in embeddings_per_image for name in embeddings)
    model_ids = {
        name: create_embedding_model(
            session=session, collection_id=collection_id, embedding_model_name=name
        ).embedding_model_id
        for name in model_names
    }
    sample_ids = []
    for index, embeddings in enumerate(embeddings_per_image):
        image = create_image(
            session=session, collection_id=collection_id, file_path_abs=f"sample_{index}.jpg"
        )
        for name, embedding in embeddings.items():
            create_sample_embedding(
                session=session,
                sample_id=image.sample_id,
                embedding_model_id=model_ids[name],
                embedding=embedding,
            )
        sample_ids.append(image.sample_id)
    return collection_id, sample_ids
