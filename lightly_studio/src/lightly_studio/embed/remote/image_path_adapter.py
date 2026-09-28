"""Embeds images by path through the image-bytes route of a remote embedder.

An fsspec path does not cross the wire, and the image import asks for an image-path
embedder. This module reads each file in this process and sends its bytes on the
image-bytes route.
"""

from __future__ import annotations

import functools
import logging
from collections.abc import Iterable, Iterator, Sequence

import fsspec
import numpy as np
from lightly_studio_serve.embedder import Capability, ImagePathEmbedder
from lightly_studio_serve.types import EmbeddingResult

from lightly_studio.embed.remote import batching
from lightly_studio.embed.remote.embedder import RemoteEmbedder
from lightly_studio.utils import executor, parallelize

logger = logging.getLogger(__name__)


class ImagePathRoute(RemoteEmbedder, ImagePathEmbedder):
    """Adds the image-path capability, which reaches the server as image bytes."""

    def embed_images(self, paths: list[str]) -> EmbeddingResult:
        """Read a batch of images by path and embed their bytes on the server.

        The files are read on a thread pool, a small number ahead of the requests. Thus
        the memory use depends on the size of one request, not on the size of the batch.
        A file that cannot be read, or that is larger than one request, is not embedded.
        """
        images = parallelize.thread_imap_lazy(
            function=functools.partial(_read, max_bytes=self._limits.max_request_bytes),
            iterable=paths,
            max_workers=executor.get_media_worker_count(),
        )
        chunks = batching.split_batches(
            items=self._sendable(paths=paths, images=images),
            max_batch_size=self._limits.max_batch_size,
            max_request_bytes=self._limits.max_request_bytes,
            size_of=_image_size,
        )
        results = [self._embed_chunk(chunk=chunk) for _, chunk in chunks]
        empty = np.empty((0, self._spec.dimension), dtype=np.float32)
        return EmbeddingResult(
            embeddings=np.concatenate([empty, *(result.embeddings for result in results)]),
            kept_indices=[index for result in results for index in result.kept_indices],
        )

    def _embed_chunk(self, chunk: Sequence[tuple[int, bytes]]) -> EmbeddingResult:
        """Embed the images of one request. The kept indices refer to the batch."""
        result = self._embed(
            items=[image for _, image in chunk],
            capability=Capability.IMAGE_BYTES,
            send=self._transport.embed_image_bytes,
            size_of=len,
        )
        return EmbeddingResult(
            embeddings=result.embeddings,
            kept_indices=[chunk[index][0] for index in result.kept_indices],
        )

    def _sendable(
        self, paths: Sequence[str], images: Iterable[bytes | None]
    ) -> Iterator[tuple[int, bytes]]:
        """Give each image that one request can hold, together with its index in the batch."""
        for index, (path, image) in enumerate(zip(paths, images)):
            if image is None:
                continue
            if len(image) + batching.ITEM_ENVELOPE_BYTES > self._limits.max_request_bytes:
                logger.warning(
                    "Cannot embed the image %s. It is larger than one request to the "
                    "embedding server can be (%d bytes).",
                    path,
                    self._limits.max_request_bytes,
                )
                continue
            yield index, image


def _read(path: str, max_bytes: int) -> bytes | None:
    """Read the bytes of a file, or None if the file cannot be read.

    Read at most one byte more than ``max_bytes``. That byte shows that the file is too
    large for one request, and a large file does not fill the memory.
    """
    try:
        with fsspec.open(urlpath=path, mode="rb") as file:
            data: bytes = file.read(max_bytes + 1)
    except OSError as error:
        logger.warning("Cannot read the image %s: %s", path, error)
        return None
    return data


def _image_size(item: tuple[int, bytes]) -> int:
    """The bytes that one indexed image puts in the body of a request."""
    return len(item[1])
