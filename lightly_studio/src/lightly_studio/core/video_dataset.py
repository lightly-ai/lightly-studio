"""LightlyStudio VideoDataset."""

from __future__ import annotations

from lightly_studio import db_manager
from lightly_studio.core.dataset import DEFAULT_DATASET_NAME, Dataset, _load_collection
from lightly_studio.core.video_sample import VideoSample
from lightly_studio.models.collection import CollectionCreate, CollectionTable, SampleType
from lightly_studio.resolvers import collection_resolver


class VideoDataset(Dataset[VideoSample]):
    """Video dataset."""

    def __init__(self, collection: CollectionTable):
        """Create VideoDataset from collection table.

        Args:
            collection: collection table.
        """
        super().__init__(collection=collection, sample_class=VideoSample)

    @staticmethod
    def create(name: str | None = None) -> VideoDataset:
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

    @staticmethod
    def load(name: str | None = None) -> VideoDataset:
        """Load an existing dataset."""
        collection = _load_collection(name=name, sample_type=SampleType.VIDEO)
        if collection is None:
            raise ValueError(f"Dataset with name '{name}' not found.")
        return VideoDataset(collection=collection)

    @staticmethod
    def load_or_create(name: str | None = None) -> VideoDataset:
        """Create a new video dataset or load an existing one.

        Args:
            name: The name of the dataset. If None, a default name is used.
        """
        collection = _load_collection(name=name, sample_type=SampleType.VIDEO)
        if collection is None:
            return VideoDataset.create(name=name)
        return VideoDataset(collection=collection)
