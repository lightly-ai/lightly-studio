"""Wire models of the LightlyStudio embedding protocol, version 1.

Holds the request and response bodies, the capability strings that name the
endpoints, the paths they are mounted under, and the multipart field the bytes
endpoints read. This is the shared definition of the contract: the server in this
package answers with these models and ``lightly-studio`` validates the same ones on
the client side, so the two halves cannot drift apart.

A capability ``{subject}_{transport}`` is served by
``POST /v1/embed/{subjects}/{transport}``; ``text`` carries no transport segment
because text is already a payload.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field

PROTOCOL_VERSION = "1.0"

BASE_PATH = "/v1"

DESCRIBE_PATH = f"{BASE_PATH}/describe"

EMBED_TEXTS_PATH = f"{BASE_PATH}/embed/texts"

EMBED_IMAGES_BYTES_PATH = f"{BASE_PATH}/embed/images/bytes"

EMBED_VIDEOS_BYTES_PATH = f"{BASE_PATH}/embed/videos/bytes"

# Specified for a server that implements the URL transports; `serve` mounts neither.
EMBED_IMAGES_URLS_PATH = f"{BASE_PATH}/embed/images/urls"

EMBED_VIDEOS_URLS_PATH = f"{BASE_PATH}/embed/videos/urls"

# Multipart form field the bytes endpoints read, one part per item in input order.
FILES_FIELD_NAME = "files"

DEFAULT_MAX_BATCH_SIZE = 64

DEFAULT_MAX_REQUEST_BYTES = 32 * 1024 * 1024


class WireCapability(str, Enum):
    """An input kind an embedding server can accept over HTTP.

    A path is deliberately absent: an fsspec path is resolved with LightlyStudio's
    credentials, so it never crosses the wire.
    """

    TEXT = "text"
    """Text queries, as JSON."""

    IMAGE_BYTES = "image_bytes"
    """Images as raw file bytes (JPEG, PNG or WebP), as multipart parts."""

    IMAGE_URL = "image_url"
    """Images the server fetches from presigned URLs. Not served by ``serve`` yet."""

    VIDEO_BYTES = "video_bytes"
    """Videos as raw file bytes, as multipart parts."""

    VIDEO_URL = "video_url"
    """Videos the server fetches from presigned URLs. Not served by ``serve`` yet."""


class ServerLimits(BaseModel):
    """Ceilings the server enforces and advertises, so a client need not guess them."""

    max_batch_size: int = Field(default=DEFAULT_MAX_BATCH_SIZE, gt=0)
    """Largest number of items one request may carry."""

    max_request_bytes: int = Field(default=DEFAULT_MAX_REQUEST_BYTES, gt=0)
    """Largest request body the server accepts, in bytes."""


class DescribeResponse(BaseModel):
    """Body of ``GET /v1/describe``, the only endpoint every server implements."""

    protocol_version: str = PROTOCOL_VERSION
    """Version of this contract the server speaks."""

    space_key: str
    """Identifier of the embedding space the server produces."""

    dimension: int
    """Length of every embedding vector the server returns."""

    ready: bool
    """Whether the model is loaded. ``False`` means retry shortly, not broken."""

    capabilities: list[WireCapability]
    """The input kinds this server accepts. Exactly the endpoints it mounts."""

    limits: ServerLimits
    """The ceilings a client has to batch against."""


class EmbedTextsRequest(BaseModel):
    """Body of ``POST /v1/embed/texts``."""

    texts: list[str]
    """The strings to embed, in the order the embeddings are returned for."""


class EmbedUrlsRequest(BaseModel):
    """Body of the URL transports, ``POST /v1/embed/{images,videos}/urls``.

    Defined so that a server implementing them has one definition to validate
    against, even though ``serve`` mounts no URL route yet.
    """

    urls: list[str]
    """Presigned URLs the server fetches, in the order the embeddings are returned for.

    A URL the server cannot fetch is a per-item failure: it is left out of
    ``kept_indices`` rather than failing the batch.
    """


class EmbeddingsResponse(BaseModel):
    """Body of every embed endpoint.

    ``space_key`` and ``dimension`` are echoed on each response, because that is the
    only thing that catches a server whose weights changed without a new
    ``space_key``.
    """

    space_key: str
    """Identifier of the embedding space these vectors belong to."""

    dimension: int
    """Length of every vector in ``embeddings``."""

    kept_indices: list[int]
    """Indices of the request items that were embedded, ascending.

    An item the server cannot decode is skipped here instead of failing the batch.
    """

    embeddings: list[list[float]]
    """One row per entry in ``kept_indices``, in the same order."""
