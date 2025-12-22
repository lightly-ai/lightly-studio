"""LightlyStudio VideoDataset."""

from __future__ import annotations

from uuid import UUID

from lightly_studio import db_manager
from lightly_studio.core.dataset import DEFAULT_DATASET_NAME, Dataset, load_collection
from lightly_studio.core.video_sample import VideoSample
from lightly_studio.models.collection import CollectionCreate, CollectionTable, SampleType
from lightly_studio.resolvers import collection_resolver, video_resolver


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
            A single ImageSample object.

        Raises:
            IndexError: If no sample is found with the given sample_id.
        """
        sample = video_resolver.get_by_id(self.session, sample_id=sample_id)

        if sample is None:
            raise IndexError(f"No sample found for sample_id: {sample_id}")
        return VideoSample(inner=sample)
