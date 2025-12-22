"""LightlyStudio VideoDataset."""

from __future__ import annotations

import logging
from typing import Iterable
from uuid import UUID

from sqlmodel import Session

from lightly_studio import db_manager
from lightly_studio.core import add_videos
from lightly_studio.core.add_videos import VIDEO_EXTENSIONS
from lightly_studio.core.dataset import (
    DEFAULT_DATASET_NAME,
    Dataset,
    _mark_embedding_features_enabled,
    load_collection,
)
from lightly_studio.core.video_sample import VideoSample
from lightly_studio.dataset import fsspec_lister
from lightly_studio.dataset.embedding_manager import EmbeddingManagerProvider
from lightly_studio.models.collection import CollectionCreate, CollectionTable, SampleType
from lightly_studio.resolvers import collection_resolver, video_resolver
from lightly_studio.type_definitions import PathLike

logger = logging.getLogger(__name__)


class VideoDataset(Dataset[VideoSample]):
    """Video dataset."""

    def __init__(self, collection: CollectionTable):
        """Create VideoDataset from a collection table.

        Args:
            collection: collection table.
        """
        super().__init__(collection=collection, sample_class=VideoSample)

    @classmethod
    def create(cls, name: str | None = None) -> VideoDataset:
        """Create a new video dataset.

        Args:
            name: The name of the dataset. If None, a default name is used.
        """
        if name is None:
            name = DEFAULT_DATASET_NAME

        collection = collection_resolver.create(
            session=db_manager.persistent_session(),
            collection=CollectionCreate(name=name, sample_type=SampleType.VIDEO),
        )
        return VideoDataset(collection=collection)

    @classmethod
    def load(cls, name: str | None = None) -> VideoDataset:
        """Load an existing dataset."""
        collection = load_collection(name=name, sample_type=SampleType.VIDEO)
        if collection is None:
            raise ValueError(f"Dataset with name '{name}' not found.")
        return VideoDataset(collection=collection)

    @classmethod
    def load_or_create(cls, name: str | None = None) -> VideoDataset:
        """Create a new video dataset or load an existing one.

        Args:
            name: The name of the dataset. If None, a default name is used.
        """
        collection = load_collection(name=name, sample_type=SampleType.VIDEO)
        if collection is None:
            return VideoDataset.create(name=name)
        return VideoDataset(collection=collection)

    def get_sample(self, sample_id: UUID) -> VideoSample:
        """Get a single sample from the dataset by its ID.

        Args:
            sample_id: The UUID of the sample to retrieve.

        Returns:
            A single VideoSample object.

        Raises:
            IndexError: If no sample is found with the given sample_id.
        """
        sample = video_resolver.get_by_id(self.session, sample_id=sample_id)

        if sample is None:
            raise IndexError(f"No sample found for sample_id: {sample_id}")
        return VideoSample(inner=sample)

    def add_videos_from_path(
        self,
        path: PathLike,
        allowed_extensions: Iterable[str] | None = None,
        num_decode_threads: int | None = None,
        embed: bool = True,
    ) -> None:
        """Adding video frames from the specified path to the dataset.

        Args:
            path: Path to the folder containing the videos to add.
            allowed_extensions: An iterable container of allowed video file
                extensions in lowercase, including the leading dot. If None,
                uses default VIDEO_EXTENSIONS.
            num_decode_threads: Optional override for the number of FFmpeg decode threads.
                If omitted, the available CPU cores - 1 (max 16) are used.
            embed: If True, generate embeddings for the newly added videos.
        """
        # Collect video file paths.
        if allowed_extensions:
            allowed_extensions_set = {ext.lower() for ext in allowed_extensions}
        else:
            allowed_extensions_set = VIDEO_EXTENSIONS
        video_paths = list(
            fsspec_lister.iter_files_from_path(
                path=str(path), allowed_extensions=allowed_extensions_set
            )
        )
        logger.info(f"Found {len(video_paths)} videos in {path}.")

        # Process videos.
        created_sample_ids, _ = add_videos.load_into_dataset_from_paths(
            session=self.session,
            dataset_id=self.dataset_id,
            video_paths=video_paths,
            num_decode_threads=num_decode_threads,
        )

        if embed:
            _generate_embeddings_video(
                session=self.session,
                dataset_id=self.dataset_id,
                sample_ids=created_sample_ids,
            )


def _generate_embeddings_video(
    session: Session,
    dataset_id: UUID,
    sample_ids: list[UUID],
) -> None:
    """Generate and store embeddings for samples.

    Args:
        session: Database session for resolver operations.
        dataset_id: The ID of the dataset to associate with the embedding model.
        sample_ids: List of sample IDs to generate embeddings for.
    """
    if not sample_ids:
        return

    embedding_manager = EmbeddingManagerProvider.get_embedding_manager()
    model_id = embedding_manager.load_or_get_default_model(
        session=session, collection_id=dataset_id
    )
    if model_id is None:
        logger.warning("No embedding model loaded. Skipping embedding generation.")
        return

    embedding_manager.embed_videos(
        session=session,
        collection_id=dataset_id,
        sample_ids=sample_ids,
        embedding_model_id=model_id,
    )

    _mark_embedding_features_enabled()
