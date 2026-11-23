"""Ingestion transport that adds samples in the same process."""

from __future__ import annotations

import logging
from collections.abc import Sequence
from uuid import UUID

from lightly_studio.core.image import add_images
from lightly_studio.database import db_manager
from lightly_studio.dataset import fsspec_lister, remote_storage
from lightly_studio.embed import embed_samples
from lightly_studio.models.image import AddImagesResult, ImageCreate
from lightly_studio.resolvers import collection_embedding_model_resolver, image_resolver

logger = logging.getLogger(__name__)


class LocalIngestionTransport:
    """Implements `IngestionTransport` with the persistent database session."""

    def add_images_from_path(  # noqa: PLR0913
        self,
        collection_id: UUID,
        path: str,
        allowed_extensions: Sequence[str] | None,
        embed: bool,
        tag_depth: int,
        limit: int | None,
    ) -> None:
        """Add the raw images from a path to a collection."""
        fsspec_lister.validate_limit(limit)
        if tag_depth < 0:
            raise ValueError(f"tag_depth must be non-negative, got {tag_depth}.")
        allowed_extensions_set = (
            {ext.lower() for ext in allowed_extensions} if allowed_extensions else None
        )
        # Configure clients before discovery creates and caches a filesystem.
        remote_storage.configure_connections(paths=[path])
        image_paths = list(
            fsspec_lister.iter_files_from_path(
                path=path, allowed_extensions=allowed_extensions_set, limit=limit
            )
        )
        logger.info(f"Found {len(image_paths)} images in {path}.")

        session = db_manager.persistent_session()
        path_to_sample_id = add_images.load_into_dataset_from_paths(
            session=session, root_collection_id=collection_id, image_paths=image_paths
        )
        created_sample_ids = list(path_to_sample_id.values())
        if created_sample_ids:
            add_images.tag_samples_by_directory(
                session=session,
                collection_id=collection_id,
                input_path=path,
                sample_ids=created_sample_ids,
                tag_depth=tag_depth,
            )
        if embed:
            self.embed_images(collection_id=collection_id, sample_ids=created_sample_ids)

    def add_images(self, collection_id: UUID, images: Sequence[ImageCreate]) -> AddImagesResult:
        """Add images with known dimensions to a collection."""
        return add_images.create_images(
            session=db_manager.persistent_session(), collection_id=collection_id, images=images
        )

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
