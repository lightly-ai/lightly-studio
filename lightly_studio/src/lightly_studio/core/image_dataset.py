"""LightlyStudio Image Dataset."""

from __future__ import annotations

from uuid import UUID

from lightly_studio.core.dataset import Dataset
from lightly_studio.core.dataset_query.dataset_query import DatasetQuery
from lightly_studio.core.image_sample import ImageSample
from lightly_studio.export.export_dataset import DatasetExport
from lightly_studio.models.collection import SampleType
from lightly_studio.resolvers import image_resolver


class ImageDataset(Dataset[ImageSample]):
    """Image dataset."""

    @staticmethod
    def sample_type() -> SampleType:
        """Returns the sample type."""
        return SampleType.IMAGE

    @staticmethod
    def sample_class() -> type[ImageSample]:
        """Returns the sample class."""
        return ImageSample

    def export(self, query: DatasetQuery | None = None) -> DatasetExport:
        """Return a DatasetExport instance which can export the dataset in various formats.

        Args:
            query:
                The dataset query to export. If None, the default query `self.query()` is used.
        """
        if query is None:
            query = self.query()
        return DatasetExport(session=self.session, root_dataset_id=self.dataset_id, samples=query)

    def get_sample(self, sample_id: UUID) -> ImageSample:
        """Get a single sample from the dataset by its ID.

        Args:
            sample_id: The UUID of the sample to retrieve.

        Returns:
            A single ImageSample object.

        Raises:
            IndexError: If no sample is found with the given sample_id.
        """
        sample = image_resolver.get_by_id(self.session, sample_id=sample_id)

        if sample is None:
            raise IndexError(f"No sample found for sample_id: {sample_id}")
        return ImageSample(inner=sample)
