"""A base for the routes that send image bytes that this process prepares.

A path or a crop does not cross the wire. A route that serves one of them prepares the
image bytes in this process, and this base sends them on the image-bytes route.
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Iterable, Iterator, Sequence

import numpy as np
from lightly_studio_serve.embedder import Capability
from lightly_studio_serve.types import EmbeddingResult

from lightly_studio.embed.remote import batching
from lightly_studio.embed.remote.embedder import RemoteEmbedder

logger = logging.getLogger(__name__)


class PreparedImageRoute(RemoteEmbedder):
    """Sends prepared image bytes, each with the index of its input in the batch."""

    def _embed_prepared(
        self, images: Iterable[tuple[int, bytes]], name_of: Callable[[int], str]
    ) -> EmbeddingResult:
        """Embed prepared images on the server and skip each image that no request can hold.

        Args:
            images: Each image with the index of its input in the batch. An input that
                was not prepared is absent. The iterable is read lazily, so the memory use
                depends on the size of one request, not on the size of the batch.
            name_of: Gives the name of the input at an index, for a warning.

        Returns:
            The embeddings and the indices of the inputs they cover, in the order of
            ``images``.
        """
        chunks = batching.split_batches(
            items=self._sendable(images=images, name_of=name_of),
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
        self, images: Iterable[tuple[int, bytes]], name_of: Callable[[int], str]
    ) -> Iterator[tuple[int, bytes]]:
        """Give each image that one request can hold."""
        for index, image in images:
            if len(image) + batching.ITEM_ENVELOPE_BYTES > self._limits.max_request_bytes:
                logger.warning(
                    "Cannot embed %s. It is larger than one request to the embedding server "
                    "can be (%d bytes).",
                    name_of(index),
                    self._limits.max_request_bytes,
                )
                continue
            yield index, image


def _image_size(item: tuple[int, bytes]) -> int:
    """The bytes that one indexed image puts in the body of a request."""
    return len(item[1])
