"""LightlyStudio Image Dataset."""

from __future__ import annotations

from lightly_studio import db_manager
from lightly_studio.core.dataset import DEFAULT_DATASET_NAME, Dataset, load_collection
from lightly_studio.core.dataset_query.dataset_query import DatasetQuery
from lightly_studio.core.image_sample import ImageSample
from lightly_studio.export.export_dataset import DatasetExport
from lightly_studio.models.collection import (
    CollectionCreate,
    CollectionTable,
    SampleType,
)
from lightly_studio.resolvers import collection_resolver


class ImageDataset(Dataset[ImageSample]):
    """Image dataset."""

    def __init__(self, collection: CollectionTable):
        """Create ImageDataset from a collection table.

        Args:
            collection: collection table.
        """
        super().__init__(collection=collection, sample_class=ImageSample)

    @classmethod
    def create(cls, name: str | None = None) -> ImageDataset:
        """Create a new image dataset.

        Args:
            name: The name of the dataset. If None, a default name is used.
        """
        if name is None:
            name = DEFAULT_DATASET_NAME

        collection = collection_resolver.create(
            session=db_manager.persistent_session(),
            collection=CollectionCreate(name=name, sample_type=SampleType.IMAGE),
        )
        return ImageDataset(collection=collection)

    @classmethod
    def load(cls, name: str | None = None) -> ImageDataset:
        """Load an existing dataset."""
        collection = load_collection(name=name, sample_type=SampleType.IMAGE)
        if collection is None:
            raise ValueError(f"Dataset with name '{name}' not found.")
        return ImageDataset(collection=collection)

    @classmethod
    def load_or_create(cls, name: str | None = None) -> ImageDataset:
        """Create a new image dataset or load an existing one.

        Args:
            name: The name of the dataset. If None, a default name is used.
        """
        collection = load_collection(name=name, sample_type=SampleType.IMAGE)
        if collection is None:
            return ImageDataset.create(name=name)
        return ImageDataset(collection=collection)

    def export(self, query: DatasetQuery | None = None) -> DatasetExport:
        """Return a DatasetExport instance which can export the dataset in various formats.

        Args:
            query:
                The dataset query to export. If None, the default query `self.query()` is used.
        """
        if query is None:
            query = self.query()
        return DatasetExport(session=self.session, root_dataset_id=self.dataset_id, samples=query)
