"""Embeds decoded images, such as video frames, through the image-bytes route of a remote embedder.

A decoded image does not cross the wire. This module encodes each image as JPEG in this
process and sends the bytes on the image-bytes route.
"""

from __future__ import annotations

import io
import logging

from lightly_studio_serve.embedder import ImagePILEmbedder
from lightly_studio_serve.types import EmbeddingResult
from PIL import Image

from lightly_studio.embed.remote import composition
from lightly_studio.embed.remote.prepared_image_route import PreparedImageRoute
from lightly_studio.utils import executor, parallelize

logger = logging.getLogger(__name__)

_JPEG_QUALITY = 95


class ImagePILRoute(PreparedImageRoute, ImagePILEmbedder):
    """Adds the PIL-image capability, which reaches the server as image bytes."""

    def embed_images_pil(self, images: list[Image.Image]) -> EmbeddingResult:
        """Encode a batch of images as JPEG and embed the bytes on the server.

        The images are encoded on a thread pool, a small number ahead of the requests.
        Thus the memory use of the encoded images depends on the size of one request, not
        on the size of the batch. An image is not embedded if it cannot be encoded or if
        it is larger than one request.
        """
        encoded = parallelize.thread_imap_lazy(
            function=_encode_jpeg,
            iterable=images,
            max_workers=executor.get_media_worker_count(),
        )
        return self._embed_prepared(
            images=((index, data) for index, data in enumerate(encoded) if data is not None),
            name_of=lambda index: f"the image at index {index} of the batch",
        )


# `EmbedderRegistry` adds this route again when it builds the embedder from a stored endpoint
composition.add_rebuildable_routes(routes=[ImagePILRoute])


def _encode_jpeg(image: Image.Image) -> bytes | None:
    """Encode an image as JPEG.

    Args:
        image: The decoded image. A video frame is RGB, but another caller can give
            another mode.

    Returns:
        The JPEG bytes of the image, or None if the encoder rejects the image, for
        example a mode that JPEG cannot hold, such as RGBA, or an image with no pixels.
    """
    with io.BytesIO() as buffer:
        try:
            image.save(buffer, format="JPEG", quality=_JPEG_QUALITY)
        except (OSError, ValueError) as error:
            logger.warning("Cannot encode the image %s as JPEG: %s", image, error)
            return None
        return buffer.getvalue()
