"""Transport protocol for adding samples from files."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol
from uuid import UUID


class IngestionTransport(Protocol):
    """Adds images and videos to a collection.

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
        """Add the images in a folder to a collection.

        Args:
            collection_id: The ID of the collection.
            path: The folder with the images.
            allowed_extensions: The file extensions to add. None uses the default extensions.
            embed: If True, compute embeddings for the new images.
            tag_depth: The folder depth that gives tags. 0 adds no tags.
            limit: The maximum number of images to add. None adds all images.
        """

    def add_videos_from_path(  # noqa: PLR0913
        self,
        collection_id: UUID,
        path: str,
        allowed_extensions: Sequence[str] | None,
        embed: bool,
        embed_frames: bool,
        target_fps: float | None,
        limit: int | None,
    ) -> None:
        """Add the videos in a folder to a collection.

        Args:
            collection_id: The ID of the collection.
            path: The folder with the videos.
            allowed_extensions: The file extensions to add. None uses the default extensions.
            embed: If True, compute embeddings for the new videos.
            embed_frames: If True, compute embeddings for the frames of the new videos.
            target_fps: The frame rate of the added frames. None adds all frames.
            limit: The maximum number of videos to add. None adds all videos.
        """

    def add_images(self, collection_id: UUID, paths: Sequence[str], embed: bool) -> dict[str, UUID]:
        """Add images from a list of file paths to a collection.

        Label imports use it, for example COCO or YOLO, and then add the annotations.

        Args:
            collection_id: The ID of the collection.
            paths: The image files.
            embed: If True, compute embeddings for the new images.

        Returns:
            The sample ID of each new image, by its path as given in `paths`. Skipped files
            have no entry.
        """

    def add_videos(
        self,
        collection_id: UUID,
        paths: Sequence[str],
        embed: bool,
        embed_frames: bool,
        target_fps: float | None,
    ) -> dict[str, UUID]:
        """Add videos from a list of file paths to a collection.

        Label imports use it, for example YouTube-VIS, and then add the annotations.

        Args:
            collection_id: The ID of the collection.
            paths: The video files.
            embed: If True, compute embeddings for the new videos.
            embed_frames: If True, compute embeddings for the frames of the new videos.
            target_fps: The frame rate of the added frames. None adds all frames.

        Returns:
            The sample ID of each new video, by its path as given in `paths`. Skipped files
            have no entry.
        """
