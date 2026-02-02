"""Class for creating an image sample from a file path."""

from dataclasses import dataclass
from uuid import UUID

from sqlmodel import Session

from lightly_studio.core import add_images
from lightly_studio.core.create_sample import CreateSample
from lightly_studio.models.collection import SampleType


@dataclass
class CreateImage(CreateSample):
    """Class for creating an image sample from a file path."""

    path: str
    """The file path of the image to be created."""

    def create_in_collection(self, session: Session, collection_id: UUID) -> UUID:
        """Create an image sample in the specified collection.

        Args:
            session: Database session for resolver operations.
            collection_id: The ID of an image collection to create the sample in.

        Returns:
            The UUID of the created image sample.

        Raises:
            ValueError: If the image could not be added.
        """
        sample_ids = add_images.load_into_dataset_from_paths(
            session=session,
            dataset_id=collection_id,
            image_paths=[self.path],
        )
        if len(sample_ids) != 1:
            raise ValueError("Failed to create image sample.")
        return sample_ids[0]

    def sample_type(self) -> SampleType:
        """Return the sample type."""
        return SampleType.IMAGE
