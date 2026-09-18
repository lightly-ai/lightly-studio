"""An embedder that calls a server instead of running a model.

``RemoteEmbedder`` is a pure mirror of the wire. It carries what every capability shares,
and one route class per capability adds the one method that the capability names. An
fsspec path, a crop and a PIL image do not cross the wire, so they are not served here.

The capabilities are data of the server. ``connect`` reads ``/v1/describe`` once and
composes the class out of the route classes that the server advertises, so a capability
that the server does not advertise has no method to call.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import TypeVar, cast

import httpx
import numpy as np
from lightly_studio_serve.embedder import (
    Capability,
    Embedder,
    ImageBytesEmbedder,
    TextEmbedder,
    VideoBytesEmbedder,
)
from lightly_studio_serve.protocol import DescribeResponse, EmbeddingsResponse, ServerLimits
from lightly_studio_serve.types import EmbeddingResult, EmbeddingSpaceSpec
from numpy.typing import NDArray

from lightly_studio.embed.remote import batching, composition, connection
from lightly_studio.embed.remote.errors import (
    RemoteEmbedderCapabilityError,
    RemoteEmbedderError,
    RemoteEmbedderProtocolError,
)
from lightly_studio.embed.remote.transport import RemoteTransport

_ItemT = TypeVar("_ItemT")


class RemoteEmbedder(Embedder):
    """Embeds by calling a conforming embedding server over HTTP.

    Every method of an embedder becomes one HTTP call, and the answer becomes an
    ``EmbeddingResult``. Nothing else in LightlyStudio changes: a caller asks the registry
    for the capability it needs and calls the method, whether the object behind it runs a
    model in this process or speaks to a server.

    This class holds no capability of its own. ``connect`` composes it with one route class
    per advertised capability.

    ``ready`` keeps the default of ``True``. The answer of ``/v1/describe`` is read once,
    at construction, so the property could only report a state that has passed. A server
    whose model is still loading answers 503, and the transport waits that out.
    """

    def __init__(
        self,
        transport: RemoteTransport,
        spec: EmbeddingSpaceSpec,
        limits: ServerLimits,
        owned_client: httpx.Client | None = None,
    ) -> None:
        """Embed through ``transport``, against a server of ``spec`` and ``limits``.

        Use ``connect``, which reads ``/v1/describe`` and passes what it learns here. This
        constructor takes the answer as given and validates nothing against the wire.

        Args:
            transport: The transport that carries every request.
            spec: The embedding space that the server produces, from ``/v1/describe``.
            limits: The limits that the server applies, from ``/v1/describe``.
            owned_client: The client that ``connect`` opened, which ``close`` closes.
                ``None`` for a client that the caller passed in and still owns.
        """
        self._transport = transport
        self._spec = spec
        self._limits = limits
        self._owned_client = owned_client
        self._closed = False

    @classmethod
    def connect(
        cls, url: str, api_key: str | None = None, client: httpx.Client | None = None
    ) -> RemoteEmbedder:
        """Read ``/v1/describe`` and build the embedder that this server can back.

        The description is read at construction and not at the first call, because
        ``EmbedderRegistry.register`` reads ``embedding_space_spec()`` as soon as it gets
        the embedder and resolves it by ``isinstance`` from that moment.

        Args:
            url: The address of the server, without a path of the protocol.
            api_key: The token to send as ``Authorization: Bearer``, or ``None`` for a
                server that wants none.
            client: The client to send with, for a test that drives an application in
                process. Its ``base_url`` then names the server and ``url`` is unused.
                ``None`` opens a client against ``url``.

        Returns:
            An embedder that implements the interface of every capability that the server
            advertises and this client routes to.

        Raises:
            RemoteEmbedderError: If the server gives no answer, rejects the token, answers
                a description that the protocol does not allow, or advertises no
                capability that LightlyStudio can use.
        """
        http_client = client if client is not None else connection.build_client(url=url)
        owned_client = http_client if client is None else None
        try:
            transport = RemoteTransport(client=http_client, api_key=api_key)
            description = transport.describe()
            connection.log_if_loading(description=description, client=http_client)
            return _embedder_for(
                transport=transport,
                description=description,
                owned_client=owned_client,
            )
        except BaseException:
            # A client that this method opened has no other owner once it raises.
            if owned_client is not None:
                owned_client.close()
            raise

    def close(self) -> None:
        """Close the connection pool of a client that ``connect`` opened.

        A client that the caller passed to ``connect`` stays the caller's to close. Calling
        this twice is allowed. An embedder that is closed sends no further request.
        """
        self._closed = True
        if self._owned_client is not None:
            self._owned_client.close()
            self._owned_client = None

    def __enter__(self) -> RemoteEmbedder:
        """Return the embedder, so a caller that owns it can close it on the way out."""
        return self

    def __exit__(self, *exc_info: object) -> None:
        """Close the client that ``connect`` opened."""
        self.close()

    def embedding_space_spec(self) -> EmbeddingSpaceSpec:
        """Describe the embedding space that the server produces.

        Returns:
            The space that ``/v1/describe`` reported at construction.
        """
        return self._spec

    def _embed(
        self,
        items: Sequence[_ItemT],
        capability: Capability,
        send: Callable[[list[_ItemT]], EmbeddingsResponse],
        size_of: Callable[[_ItemT], int],
    ) -> EmbeddingResult:
        """Embed one batch in the chunks that the server accepts, and merge the answers.

        Args:
            items: The inputs to embed. An empty batch sends no request.
            capability: The capability that ``send`` carries. It names the route in an
                error message.
            send: The transport method for this input kind.
            size_of: The bytes that one item puts in the body of a request.

        Returns:
            The embeddings and the indices of the inputs they cover.

        Raises:
            RemoteEmbedderError: If this embedder is closed, if a request fails, or if an
                answer disagrees with what ``/v1/describe`` reported.
        """
        if self._closed:
            # httpx would raise a bare `RuntimeError`, outside the hierarchy of this package.
            raise RemoteEmbedderError(
                "This embedder is closed and sends no further request. Call "
                "RemoteEmbedder.connect again to reach the server."
            )
        rows: list[list[float]] = []
        kept_indices: list[int] = []
        chunks = batching.split_batches(
            items=items,
            max_batch_size=self._limits.max_batch_size,
            max_request_bytes=self._limits.max_request_bytes,
            size_of=size_of,
        )
        for offset, chunk in chunks:
            response = self._send(send=send, chunk=chunk, capability=capability)
            self._check_answer(response=response, item_count=len(chunk))
            rows.extend(response.embeddings)
            # A chunk counts its kept indices from its own start.
            kept_indices.extend(offset + index for index in response.kept_indices)
        return EmbeddingResult(embeddings=self._to_array(rows=rows), kept_indices=kept_indices)

    def _send(
        self,
        send: Callable[[list[_ItemT]], EmbeddingsResponse],
        chunk: list[_ItemT],
        capability: Capability,
    ) -> EmbeddingsResponse:
        """Send one chunk, and name what a refusal of an advertised route means."""
        try:
            return send(chunk)
        except RemoteEmbedderCapabilityError as error:
            refusal = self._dropped_capability(capability=capability)
            if refusal is None:
                raise
            raise refusal from error

    def _dropped_capability(self, capability: Capability) -> RemoteEmbedderError | None:
        """Read ``/v1/describe`` once more and name what the refusal means. Do not loop.

        A second read can only separate a server that dropped the route from one that
        advertises a route it does not serve. The message names no status, because the
        transport reads a 404 and a 501 alike and the cause carries what arrived.

        Returns:
            The error that names the cause, or ``None`` if the second read failed. Such a
            read says nothing about the refusal, so the caller keeps the error it has.
        """
        try:
            description = self._transport.describe()
        except RemoteEmbedderError:
            return None
        if capability in description.capabilities:
            return RemoteEmbedderProtocolError(
                f"The embedding server advertises {capability.value} and refuses to serve it."
            )
        return RemoteEmbedderCapabilityError(
            f"The embedding server no longer serves {capability.value}. Build the embedder "
            f"again to follow the capabilities that it advertises now."
        )

    def _check_answer(self, response: EmbeddingsResponse, item_count: int) -> None:
        """Check the two rules of the protocol that the body cannot show on its own.

        ``EmbeddingsResponse`` holds every rule that the body shows. The identity of the
        space needs ``/v1/describe``, and the number of items needs the request.

        Raises:
            RemoteEmbedderProtocolError: If the answer breaks one of the two rules.
        """
        spec = self._spec
        if response.space_key != spec.space_key or response.dimension != spec.dimension:
            raise RemoteEmbedderProtocolError(
                f"The embedding server answered vectors of {response.space_key!r} with "
                f"dimension {response.dimension}. /v1/describe reported {spec.space_key!r} "
                f"with dimension {spec.dimension}."
            )
        if any(index >= item_count for index in response.kept_indices):
            raise RemoteEmbedderProtocolError(
                f"The embedding server kept the indices {response.kept_indices} of a request "
                f"that carried {item_count} items."
            )

    def _to_array(self, rows: list[list[float]]) -> NDArray[np.float32]:
        """Stack the rows of every chunk into one array.

        A batch where the server kept nothing still has a width, because a caller stacks
        the result with the vectors of other batches.
        """
        if not rows:
            return np.empty((0, self._spec.dimension), dtype=np.float32)
        return np.array(rows, dtype=np.float32)


class _TextRoute(RemoteEmbedder, TextEmbedder):
    """Adds the text capability, which reaches the server as JSON."""

    def embed_text(self, texts: list[str]) -> EmbeddingResult:
        """Embed a batch of text strings on the server.

        Args:
            texts: The strings to embed.

        Returns:
            The embeddings and the indices of the inputs they cover.
        """
        return self._embed(
            items=texts,
            capability=Capability.TEXT,
            send=self._transport.embed_texts,
            size_of=batching.text_size,
        )


class _ImageBytesRoute(RemoteEmbedder, ImageBytesEmbedder):
    """Adds the image-bytes capability, which reaches the server as multipart."""

    def embed_image_bytes(self, images: list[bytes]) -> EmbeddingResult:
        """Embed a batch of encoded images on the server.

        Args:
            images: Encoded image bytes.

        Returns:
            The embeddings and the indices of the inputs they cover.
        """
        return self._embed(
            items=images,
            capability=Capability.IMAGE_BYTES,
            send=self._transport.embed_image_bytes,
            size_of=len,
        )


class _VideoBytesRoute(RemoteEmbedder, VideoBytesEmbedder):
    """Adds the video-bytes capability, which reaches the server as multipart."""

    def embed_video_bytes(self, videos: list[bytes]) -> EmbeddingResult:
        """Embed a batch of encoded videos on the server.

        Args:
            videos: Encoded video bytes.

        Returns:
            The embeddings and the indices of the inputs they cover.
        """
        return self._embed(
            items=videos,
            capability=Capability.VIDEO_BYTES,
            send=self._transport.embed_video_bytes,
            size_of=len,
        )


# The capabilities that this client routes to, each with the route class that serves it.
# `WIRE_CAPABILITIES` is broader: a `DescribeResponse` can legally carry `image_path`,
# which version 1 never requests. A capability that is absent here is ignored, never
# assumed routable. The order of this mapping is the order of the bases, so two servers
# that advertise the same set compose the same class.
_CAPABILITY_TO_BASE: dict[Capability, type[RemoteEmbedder]] = {
    Capability.TEXT: _TextRoute,
    Capability.IMAGE_BYTES: _ImageBytesRoute,
    Capability.VIDEO_BYTES: _VideoBytesRoute,
}


def _embedder_for(
    transport: RemoteTransport,
    description: DescribeResponse,
    owned_client: httpx.Client | None,
) -> RemoteEmbedder:
    """Build the embedder of the capabilities that ``description`` advertises.

    Args:
        transport: The transport that carries every request.
        description: What ``GET /v1/describe`` answered.
        owned_client: The client that ``connect`` opened, or ``None`` for one that the
            caller owns.

    Returns:
        An embedder that implements the interface of every advertised capability that this
        client routes to.

    Raises:
        RemoteEmbedderCapabilityError: If nothing advertised is usable from LightlyStudio.
    """
    composed = cast(
        "type[RemoteEmbedder]",
        composition.compose_remote_embedder_class(
            capabilities=description.capabilities,
            capability_to_base=_CAPABILITY_TO_BASE,
        ),
    )
    return composed(
        transport=transport,
        spec=EmbeddingSpaceSpec(space_key=description.space_key, dimension=description.dimension),
        limits=description.limits,
        owned_client=owned_client,
    )
