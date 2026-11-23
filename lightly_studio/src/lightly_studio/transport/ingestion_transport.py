"""Transport protocol for adding samples from files."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Protocol
from uuid import UUID

from lightly_studio.core.create_sample import CreateSample
from lightly_studio.models.dynamic_transform import DynamicTransformCreate
from lightly_studio.models.image import AddImagesResult, ImageCreate
from lightly_studio.models.sensor_calibration import SensorCalibrationCreate
from lightly_studio.models.sequence import SampleSequenceLinkCreate
from lightly_studio.models.static_transform import StaticTransformCreate


class IngestionTransport(Protocol):
    """Adds samples to a collection.

    A path is a local path or a cloud URI. A remote transport reads it on the server.
    """

    # TODO(Iunir, 11/2026): Add MCAP ingestion when `McapComponentSpec` has no DB imports.

    def add_images_from_path(  # noqa: PLR0913
        self,
        collection_id: UUID,
        path: str,
        allowed_extensions: Sequence[str] | None,
        embed: bool,
        tag_depth: int,
        limit: int | None,
    ) -> None:
        """Add the raw images from a path to a collection.

        Args:
            collection_id: The ID of the collection.
            path: The folder with the images.
            allowed_extensions: The file extensions to add. None uses the default extensions.
            embed: If True, compute embeddings for the new images, and for the images
                without an embedding of the default model.
            tag_depth: The folder depth that gives tags. 0 adds no tags.
            limit: The maximum number of images to add. None adds all images.

        Raises:
            ValueError: If `tag_depth` is negative or `limit` is not greater than 0.
            AllInputFilesFailedError: If all images are missing or broken.
        """

    def add_images(self, collection_id: UUID, images: Sequence[ImageCreate]) -> AddImagesResult:
        """Add images with known dimensions to a collection.

        The ingestion of annotated data uses it, for example COCO or YOLO, and then adds the
        annotations. The label files give the dimensions, so the image files are not opened.

        Args:
            collection_id: The ID of the collection.
            images: The images to add.

        Returns:
            The sample ID of each new image by its path, and the outcome of each input image.
            An image that is in the collection or earlier in `images` is already present. An
            image whose file does not exist is missing.
        """

    def add_directory_tags(
        self, collection_id: UUID, path: str, sample_ids: Sequence[UUID], tag_depth: int
    ) -> None:
        """Tag images with the names of the folders between `path` and the image file.

        Args:
            collection_id: The ID of the collection.
            path: The folder that the images were added from.
            sample_ids: The images to tag.
            tag_depth: The number of folder levels that give tags. 0 adds no tags.

        Raises:
            ValueError: If `tag_depth` is negative.
        """

    def embed_images(self, collection_id: UUID, sample_ids: Sequence[UUID]) -> None:
        """Compute embeddings for images with the default embedding model of the collection.

        The images of the collection without an embedding of the default model get one too.

        Args:
            collection_id: The ID of the collection.
            sample_ids: The images to embed.
        """

    def add_videos_from_path(  # noqa: PLR0913
        self,
        collection_id: UUID,
        path: str,
        allowed_extensions: Sequence[str] | None,
        num_decode_threads: int | None,
        embed: bool,
        embed_frames: bool,
        target_fps: float | None,
        limit: int | None,
    ) -> None:
        """Add the raw videos from a path to a collection.

        Args:
            collection_id: The ID of the collection.
            path: The folder with the videos.
            allowed_extensions: The file extensions to add. None uses the default extensions.
            num_decode_threads: The number of FFmpeg decode threads. None uses the number
                of CPU cores minus 1, at most 16.
            embed: If True, compute embeddings for the new videos.
            embed_frames: If True, compute embeddings for the frames of the new videos.
            target_fps: The frame rate of the added frames. None adds all frames.
            limit: The maximum number of videos to add. None adds all videos.

        Raises:
            ValueError: If `target_fps` or `limit` is not greater than 0.
            AllInputFilesFailedError: If all videos are missing or broken.
        """

    def add_videos(
        self,
        collection_id: UUID,
        paths: Sequence[str],
        embed_frames: bool,
        target_fps: float | None,
    ) -> dict[str, UUID]:
        """Add videos from a list of file paths to a collection.

        The ingestion of annotated data uses it, for example YouTube-VIS, and then adds the
        annotations.

        Args:
            collection_id: The ID of the collection.
            paths: The video files.
            embed_frames: If True, compute embeddings for the frames of the new videos.
            target_fps: The frame rate of the added frames. None adds all frames.

        Returns:
            The sample ID of each new video, by its absolute path. Skipped files have no entry.

        Raises:
            ValueError: If `target_fps` is not greater than 0.
            AllInputFilesFailedError: If all videos are missing or broken.
        """

    def embed_videos(self, collection_id: UUID, sample_ids: Sequence[UUID]) -> None:
        """Compute embeddings for videos with the default video embedding model.

        Args:
            collection_id: The ID of the collection.
            sample_ids: The videos to embed.
        """

    def add_group_samples(
        self, collection_id: UUID, groups: Sequence[Mapping[str, CreateSample]]
    ) -> list[UUID]:
        """Add group samples and their component samples to a group collection.

        Args:
            collection_id: The ID of the group collection.
            groups: The component samples of each group, by component name.

        Returns:
            The sample ID of each new group, in the order of `groups`.

        Raises:
            ValueError: If a component name is not in the collection, or if the sample type
                of a component does not match.
        """

    def add_sensor_calibrations(self, rows: Sequence[SensorCalibrationCreate]) -> list[UUID]:
        """Add camera calibrations to MCAP recordings.

        Returns:
            The IDs of the new calibrations, in the order of `rows`.

        Raises:
            ValueError: If `rows` is empty, or if a component does not carry video frames.
        """

    def add_static_transforms(self, rows: Sequence[StaticTransformCreate]) -> list[UUID]:
        """Add static transforms between the coordinate frames of MCAP recordings.

        Returns:
            The IDs of the new transforms, in the order of `rows`.

        Raises:
            ValueError: If `rows` is empty, or if a frame ID is empty.
        """

    def add_dynamic_transforms(self, rows: Sequence[DynamicTransformCreate]) -> list[UUID]:
        """Add dynamic transforms between the coordinate frames of MCAP recordings.

        Returns:
            The IDs of the new transforms, in the order of `rows`.

        Raises:
            ValueError: If `rows` is empty, or if a frame ID is empty.
        """

    def add_sequence_samples(
        self, sequence_sample_id: UUID, links: Sequence[SampleSequenceLinkCreate]
    ) -> None:
        """Put groups in the slots of an MCAP sequence, in a single commit.

        Args:
            sequence_sample_id: The sample ID of the sequence.
            links: The groups to add and the slot of each.

        Raises:
            ValueError: If a group does not exist, or if a `seq_number` is negative.
        """
