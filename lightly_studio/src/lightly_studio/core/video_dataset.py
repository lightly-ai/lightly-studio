"""LightlyStudio VideoDataset."""

from __future__ import annotations

from uuid import UUID

from lightly_studio.core.dataset import Dataset
from lightly_studio.core.video_sample import VideoSample
from lightly_studio.models.collection import SampleType
from lightly_studio.resolvers import video_resolver


class VideoDataset(Dataset[VideoSample]):
    """Video dataset."""

    @staticmethod
    def sample_type() -> SampleType:
        """Returns the sample type."""
        return SampleType.VIDEO

    @staticmethod
    def sample_class() -> type[VideoSample]:
        """Returns the sample class."""
        return VideoSample

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
