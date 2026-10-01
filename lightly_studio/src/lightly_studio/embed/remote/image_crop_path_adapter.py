"""Embeds image crops through the image-bytes route of a remote embedder.

A crop is a pixel box in an image file, and a file path does not cross the wire. This
module reads each file once in this process, cuts each box with no padding, the same as
the local crop embedding, and sends each crop as JPEG bytes on the image-bytes route.
"""

from __future__ import annotations

import io
import logging
from collections.abc import Iterable, Iterator
from dataclasses import dataclass

import fsspec
import numpy as np
from lightly_studio_serve.embedder import ImageCropPathEmbedder
from lightly_studio_serve.types import EmbeddingResult, ImageCrop
from PIL import Image

from lightly_studio.core.file_outcome_report import BROKEN_IMAGE_ERRORS
from lightly_studio.embed.remote import composition
from lightly_studio.embed.remote.prepared_image_route import PreparedImageRoute
from lightly_studio.utils import executor, parallelize

logger = logging.getLogger(__name__)

_JPEG_QUALITY = 95


@dataclass(frozen=True)
class _FileCrops:
    """The crops of one image file, each with the index of its input in the batch."""

    filepath: str
    indexed_crops: list[tuple[int, ImageCrop]]


@dataclass(frozen=True)
class _DecodedFile:
    """The decoded image of one file, or None if the file cannot be read, and its crops."""

    image: Image.Image | None
    indexed_crops: list[tuple[int, ImageCrop]]


class ImageCropPathRoute(PreparedImageRoute, ImageCropPathEmbedder):
    """Adds the image-crop-path capability, which reaches the server as image bytes."""

    def embed_image_crops(self, crops: list[ImageCrop]) -> EmbeddingResult:
        """Cut a batch of crops out of their images and embed the crops on the server.

        Each file is read once, on a thread pool, a small number of files ahead of the
        requests. Each crop is encoded only when a request takes it, so the memory use
        does not depend on the number of crops in one file. A crop is not embedded if its
        file cannot be read, if its box gives no image, if its JPEG cannot be encoded, or
        if it is larger than one request.
        """
        decoded_files = parallelize.thread_imap_lazy(
            function=_decode_file,
            iterable=_group_by_file(crops=crops),
            max_workers=executor.get_media_worker_count(),
        )
        result = self._embed_prepared(
            images=_encode_crops(decoded_files=decoded_files),
            name_of=lambda index: f"the crop {crops[index]}",
        )
        # The crops of one file are sent together, which changes the order of the inputs
        return _in_input_order(result=result)


# `EmbedderRegistry` adds this route again when it builds the embedder from a stored endpoint
composition.add_rebuildable_routes(routes=[ImageCropPathRoute])


def _group_by_file(crops: list[ImageCrop]) -> list[_FileCrops]:
    """Group the crops by file, in the order of the first crop of each file."""
    crops_by_filepath: dict[str, list[tuple[int, ImageCrop]]] = {}
    for index, crop in enumerate(crops):
        crops_by_filepath.setdefault(crop.filepath, []).append((index, crop))
    return [
        _FileCrops(filepath=filepath, indexed_crops=indexed_crops)
        for filepath, indexed_crops in crops_by_filepath.items()
    ]


def _decode_file(file_crops: _FileCrops) -> _DecodedFile:
    """Read and decode one image file. A file that cannot be read gives no image."""
    return _DecodedFile(
        image=_open_rgb(filepath=file_crops.filepath), indexed_crops=file_crops.indexed_crops
    )


def _encode_crops(decoded_files: Iterable[_DecodedFile]) -> Iterator[tuple[int, bytes]]:
    """Encode the crops of each decoded file, one crop at a time."""
    for decoded_file in decoded_files:
        if decoded_file.image is None:
            continue
        with decoded_file.image:
            for index, crop in decoded_file.indexed_crops:
                data = _encode_crop(image=decoded_file.image, crop=crop)
                if data is not None:
                    yield index, data


def _open_rgb(filepath: str) -> Image.Image | None:
    """Open and decode an image as RGB, or None if the file cannot be read."""
    try:
        with fsspec.open(urlpath=filepath, mode="rb") as file, Image.open(file) as opened:
            image: Image.Image = opened.convert("RGB")
    except BROKEN_IMAGE_ERRORS as error:
        logger.warning("Cannot read the image %s: %s", filepath, error)
        return None
    return image


def _encode_crop(image: Image.Image, crop: ImageCrop) -> bytes | None:
    """Cut the box of a crop out of an RGB image and encode it as JPEG.

    Args:
        image: The decoded RGB image that the crop is taken from.
        crop: The pixel box to cut. The import clamps each box to the image. A box that
            extends past the image is filled with black.

    Returns:
        The JPEG bytes of the crop, or None if the box gives no image to embed or if the
        JPEG encoder rejects the crop, for example a side longer than 65,500 pixels.
    """
    corners = (crop.x, crop.y, crop.x + crop.width, crop.y + crop.height)
    if corners[0] >= corners[2] or corners[1] >= corners[3]:
        return None
    image_crop = image.crop(corners)
    with io.BytesIO() as buffer:
        try:
            image_crop.save(buffer, format="JPEG", quality=_JPEG_QUALITY)
        except OSError as error:
            logger.warning("Cannot encode the crop %s as JPEG: %s", crop, error)
            return None
        return buffer.getvalue()


def _in_input_order(result: EmbeddingResult) -> EmbeddingResult:
    """Sort the rows of a result by the index of their input."""
    order = np.argsort(result.kept_indices, kind="stable")
    return EmbeddingResult(
        embeddings=result.embeddings[order],
        kept_indices=[result.kept_indices[position] for position in order],
    )
