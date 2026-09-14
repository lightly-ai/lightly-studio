"""Wire models of the LightlyStudio embedding protocol, version 1.

The module holds the request bodies, the response bodies, the route paths and the
multipart field name. The server in this package sends these models.
``lightly-studio`` reads the same models. One definition keeps the two halves equal.

A server serves the capability ``{subject}_{transport}`` at
``POST /v1/embed/{subjects}/{transport}``. The capability ``text`` has no transport
segment. Text is already a payload.

``EmbeddingsResponse`` holds every rule that a response body shows.
``lightly_studio_serve.validation`` adds only the rules that the body cannot show.
"""

from __future__ import annotations

import math
from typing import Annotated, Any

import numpy as np
from pydantic import BaseModel, Field, field_validator, model_validator

from lightly_studio_serve.embedder import Capability

PROTOCOL_VERSION = "1.0"

BASE_PATH = "/v1"

DESCRIBE_PATH = f"{BASE_PATH}/describe"

EMBED_TEXTS_PATH = f"{BASE_PATH}/embed/texts"

EMBED_IMAGES_BYTES_PATH = f"{BASE_PATH}/embed/images/bytes"

EMBED_VIDEOS_BYTES_PATH = f"{BASE_PATH}/embed/videos/bytes"

# The multipart field that the bytes endpoints read. One part per item, in input order.
FILES_FIELD_NAME = "files"

# A number, because starlette renamed its constant for this status.
STATUS_PAYLOAD_TOO_LARGE = 413

# TODO(Iunir, 09/2026): Report a limit per capability. Text queries and videos do not
# belong under one ceiling.
DEFAULT_MAX_BATCH_SIZE = 1024

DEFAULT_MAX_REQUEST_BYTES = 32 * 1024 * 1024

# Both ends store the vectors as `float32`. A larger value becomes an infinity there.
MAX_ABS_EMBEDDING_VALUE = float(np.finfo(np.float32).max)

# `IMAGE_PIL` is an object in memory, so it cannot cross the wire. An fsspec path can.
WIRE_CAPABILITIES = frozenset(Capability) - {Capability.IMAGE_PIL}

# A kept index names a position in the request, so it is never negative.
_KeptIndex = Annotated[int, Field(ge=0)]


class ServerLimits(BaseModel):
    """The limits that the server applies and reports. A client does not have to guess them."""

    max_batch_size: int = Field(default=DEFAULT_MAX_BATCH_SIZE, gt=0)
    """The largest number of items in one request."""

    max_request_bytes: int = Field(default=DEFAULT_MAX_REQUEST_BYTES, gt=0)
    """The largest request body that the server accepts, in bytes."""


class DescribeResponse(BaseModel):
    """The body of ``GET /v1/describe``. Every server has this endpoint."""

    protocol_version: str = PROTOCOL_VERSION
    """The version of this contract that the server speaks.

    A client compares this against its own ``PROTOCOL_VERSION`` first. The model accepts
    any string, so a client can name the version that it met.
    """

    space_key: str
    """The identifier of the embedding space that the server produces."""

    dimension: int = Field(gt=0)
    """The length of every embedding vector that the server returns."""

    # TODO(Iunir, 09/2026): A ServerStatus enum may replace this flag. A model that
    # failed to load is not the same as a model that is still loading.
    ready: bool
    """Whether the model is loaded. ``False`` means try again soon. It is not an error."""

    capabilities: list[Capability]
    """The input kinds that this server accepts. These are the endpoints that it mounts.

    The model permits only the members of ``WIRE_CAPABILITIES``. LightlyStudio cannot
    request the other kinds.
    """

    limits: ServerLimits
    """The limits that a client must apply to its batches."""

    @field_validator("capabilities")
    @classmethod
    def _reject_unservable_capabilities(cls, value: list[Capability]) -> list[Capability]:
        unservable = [capability for capability in value if capability not in WIRE_CAPABILITIES]
        if unservable:
            raise ValueError(
                f"{unservable} cannot be served over HTTP; only {sorted(WIRE_CAPABILITIES)} can."
            )
        return value


class EmbedTextsRequest(BaseModel):
    """The body of ``POST /v1/embed/texts``."""

    texts: list[str]
    """The strings to embed. The server returns the embeddings in this order."""


class EmbeddingsResponse(BaseModel):
    """The body of every embed endpoint.

    Each response repeats ``space_key`` and ``dimension``. A client reads them to find a
    server that changed its weights and kept its ``space_key``.
    """

    space_key: str
    """The identifier of the embedding space of these vectors."""

    dimension: int = Field(gt=0)
    """The length of every vector in ``embeddings``."""

    kept_indices: list[_KeptIndex]
    """The indices of the request items that the server embedded, in ascending order.

    The server omits an item that it cannot decode. It does not fail the batch.
    """

    embeddings: list[list[float]]
    """One row for each entry in ``kept_indices``, in the same order."""

    @field_validator("kept_indices", mode="before")
    @classmethod
    def _reject_boolean_mask(cls, value: Any) -> Any:
        """Reject a mask before the field turns it into indices.

        An embedder that derives ``kept_indices`` from a numpy comparison, such as
        ``scores > 0.5``, holds ``np.bool_`` values. A lax ``int`` field reads those as
        ``0`` and ``1``. Every vector then lines up with the wrong item, and the database
        keeps the wrong vector for the sample. The check runs before the conversion,
        which is the only point where the bool is still visible.
        """
        if not isinstance(value, (list, tuple, np.ndarray)):
            return value
        for item in value:
            if isinstance(item, (bool, np.bool_)):
                raise ValueError(f"kept_indices holds {item!r}, a bool, not an index.")
        return value

    @model_validator(mode="after")
    def _check_rows_against_indices(self) -> EmbeddingsResponse:  # noqa: N804
        """Check the rules that hold between the fields.

        A field type does not show that a response is correct. A client reads this model
        from a server that it does not control. Without these rules a client aligns the
        wrong vector with an item.
        """
        if len(self.embeddings) != len(self.kept_indices):
            raise ValueError(
                f"Got {len(self.embeddings)} embeddings for {len(self.kept_indices)} kept "
                f"indices. The two must have the same length."
            )
        if any(
            current >= following
            for current, following in zip(self.kept_indices, self.kept_indices[1:])
        ):
            raise ValueError(f"kept_indices must be ascending and unique, got {self.kept_indices}.")
        for index, row in enumerate(self.embeddings):
            if len(row) != self.dimension:
                raise ValueError(
                    f"Embedding {index} has {len(row)} values. The server declares "
                    f"dimension {self.dimension}."
                )
            _check_values(row=row, index=index)
        return self


def _check_values(row: list[float], index: int) -> None:
    """Check one vector. A value outside ``float32`` is as wrong as a NaN.

    Both ends store the vectors as ``float32``. A larger value becomes an infinity there,
    and a similarity search then ranks it.
    """
    for value in row:
        if not math.isfinite(value):
            raise ValueError(f"Embedding {index} holds a value that is not finite.")
        if abs(value) > MAX_ABS_EMBEDDING_VALUE:
            raise ValueError(
                f"Embedding {index} holds {value}, over the {MAX_ABS_EMBEDDING_VALUE} that "
                f"the float32 of an embedding can hold. It would become an infinity."
            )
