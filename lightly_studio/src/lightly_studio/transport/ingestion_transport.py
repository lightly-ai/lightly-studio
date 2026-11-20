"""Transport protocol for adding samples from files."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol
from uuid import UUID

from lightly_studio.models.image import AddImagesResult, ImageCreate


class IngestionTransport(Protocol):
    """Adds samples to a collection.

    A path is a local path or a cloud URI. A remote transport reads it on the server.
    """

    # TODO(Iunir, 11/2026): Add the ingestion of videos.
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

    def embed_videos(self, collection_id: UUID, sample_ids: Sequence[UUID]) -> None:
        """Compute embeddings for videos with the default video embedding model.

        Args:
            collection_id: The ID of the collection.
            sample_ids: The videos to embed.
        """
