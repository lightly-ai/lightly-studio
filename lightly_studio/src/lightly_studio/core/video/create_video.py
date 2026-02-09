"""Class for creating a video sample from a file path."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlmodel import Session

from lightly_studio.core.create_sample import CreateSample
from lightly_studio.core.video import add_videos
from lightly_studio.core.video.add_videos import DEFAULT_VIDEO_CHANNEL
from lightly_studio.models.collection import SampleType


@dataclass
class CreateVideo(CreateSample):
    """Class for creating a video sample from a file path."""

    path: str
    """The file path of the video to be created."""
    video_channel: int = DEFAULT_VIDEO_CHANNEL
    """The video channel to be used for loading the video."""
    num_decode_threads: int | None = None
    """The number of threads to use for decoding the video."""

    def create_in_collection(self, session: Session, collection_id: UUID) -> UUID:
        """Create a video sample in the specified collection.

        Args:
            session: Database session for resolver operations.
            collection_id: The ID of a video collection to create the sample in.

        Returns:
            The UUID of the created video sample.

        Raises:
            ValueError: If the video could not be added.
        """
        video_ids, _ = add_videos.load_into_dataset_from_paths(
            session=session,
            dataset_id=collection_id,
            video_paths=[self.path],
            video_channel=self.video_channel,
            num_decode_threads=self.num_decode_threads,
            show_progress=False,
        )
        if len(video_ids) != 1:
            raise ValueError("Failed to create video sample.")
        return video_ids[0]

    def sample_type(self) -> SampleType:
        """Return the sample type."""
        return SampleType.VIDEO
