"""Ingestion transport that adds samples in the same process."""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from lightly_studio.database import db_manager
from lightly_studio.embed import embed_samples
from lightly_studio.resolvers import collection_embedding_model_resolver, image_resolver


class LocalIngestionTransport:
    """Implements `IngestionTransport` with the persistent database session."""

    def embed_images(self, collection_id: UUID, sample_ids: Sequence[UUID]) -> None:
        """Compute embeddings for images with the default embedding model of the collection.

        The images of the collection without an embedding of the default model get one too,
        so a rerun completes an embedding that failed before.
        """
        session = db_manager.persistent_session()
        ids_to_embed = list(sample_ids)
        default_model_id = collection_embedding_model_resolver.get_default_by_collection_id(
            session=session, collection_id=collection_id
        )
        if default_model_id is not None:
            unembedded_sample_ids = image_resolver.get_unembedded_sample_ids(
                session=session, collection_id=collection_id, embedding_model_id=default_model_id
            )
            ids_to_embed = list(dict.fromkeys([*ids_to_embed, *unembedded_sample_ids]))
        if not ids_to_embed:
            return
        embed_samples.embed_image_samples(
            session=session, collection_id=collection_id, sample_ids=ids_to_embed
        )
