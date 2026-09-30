"""Embeds images by path through the image-bytes route of a remote embedder.

An fsspec path does not cross the wire, and the image import asks for an image-path
embedder. This module reads each file in this process and sends its bytes on the
image-bytes route.
"""

from __future__ import annotations

import functools
import logging
from typing import IO

import fsspec
from lightly_studio_serve.embedder import ImagePathEmbedder
from lightly_studio_serve.types import EmbeddingResult

from lightly_studio.embed.remote import composition
from lightly_studio.embed.remote.prepared_image_route import PreparedImageRoute
from lightly_studio.utils import executor, parallelize

logger = logging.getLogger(__name__)


class ImagePathRoute(PreparedImageRoute, ImagePathEmbedder):
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
        return self._embed_prepared(
            images=((index, image) for index, image in enumerate(images) if image is not None),
            name_of=lambda index: f"the image {paths[index]}",
        )


# `EmbedderRegistry` adds this route again when it builds the embedder from a stored endpoint
composition.add_rebuildable_routes(routes=[ImagePathRoute])


def _read(path: str, max_bytes: int) -> bytes | None:
    """Read the bytes of a file, or None if the file cannot be read.

    Read at most one byte more than ``max_bytes``. That byte shows that the file is too
    large for one request, and a large file does not fill the memory.
    """
    try:
        with fsspec.open(urlpath=path, mode="rb") as file:
            return _read_at_most(file=file, max_bytes=max_bytes + 1)
    except OSError as error:
        logger.warning("Cannot read the image %s: %s", path, error)
        return None


def _read_at_most(file: IO[bytes], max_bytes: int) -> bytes:
    """Read until the end of the file or until ``max_bytes`` bytes.

    One read can give fewer bytes than it asks for before the end, for example from an
    HTTP stream.
    """
    chunks: list[bytes] = []
    remaining = max_bytes
    while remaining > 0:
        chunk = file.read(remaining)
        if not chunk:
            break
        chunks.append(chunk)
        remaining -= len(chunk)
    return b"".join(chunks)
