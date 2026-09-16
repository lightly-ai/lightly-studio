"""The HTTP half of the remote embedder: one request, one answer, one exception.

``RemoteTransport`` sends the requests of version 1 of the LightlyStudio embedding
protocol and reads the answers back into the wire models of ``lightly_studio_serve``. It
holds no state of the server: ``RemoteEmbedder`` reads ``/v1/describe`` once and keeps the
answer for the lifetime of the process.

The module turns a status into the exception that names it and sends a 429 or a 503 again
a capped number of times, after a wait that it also caps. A server can name a wait of any
length, and the caller of a text query sits under a key press.
"""

from __future__ import annotations

import email.utils
import time
from datetime import datetime, timezone
from typing import Any, TypeVar

import httpx
from lightly_studio_serve import protocol
from lightly_studio_serve.protocol import DescribeResponse, EmbeddingsResponse, EmbedTextsRequest
from pydantic import BaseModel, ValidationError

from lightly_studio.embed.remote.errors import (
    RemoteEmbedderAuthError,
    RemoteEmbedderBatchTooLargeError,
    RemoteEmbedderCapabilityError,
    RemoteEmbedderError,
    RemoteEmbedderProtocolError,
    RemoteEmbedderUnreachableError,
)

# How many times the client sends one request. A 429 or a 503 names a wait, and a server
# that still loads its model answers 503 until the weights arrive.
_MAX_ATTEMPTS = 3

# The longest that the client waits between two attempts, whatever `Retry-After` asks. A
# server can name an hour, and the caller of a text query sits under a key press.
_MAX_RETRY_WAIT_SECONDS = 30.0

# The wait for a 429 or a 503 that carries no `Retry-After`, or one that cannot be read.
_DEFAULT_RETRY_WAIT_SECONDS = 1.0

# The two statuses that say "later". Every other status says "not this request".
_RETRY_STATUSES = frozenset({httpx.codes.TOO_MANY_REQUESTS, httpx.codes.SERVICE_UNAVAILABLE})

# The error that names each status the protocol defines, with the reason that the server
# had for it. A 429 and a 503 reach this mapping only after the attempts are spent.
_STATUS_ERRORS: dict[int, tuple[type[RemoteEmbedderError], str]] = {
    httpx.codes.UNAUTHORIZED: (RemoteEmbedderAuthError, ", so it did not accept the token"),
    httpx.codes.FORBIDDEN: (RemoteEmbedderAuthError, ", so it did not accept the token"),
    protocol.STATUS_PAYLOAD_TOO_LARGE: (
        RemoteEmbedderBatchTooLargeError,
        ", so the request is over one of its limits",
    ),
    httpx.codes.NOT_IMPLEMENTED: (
        RemoteEmbedderCapabilityError,
        ", so it does not serve that input kind",
    ),
    httpx.codes.TOO_MANY_REQUESTS: (
        RemoteEmbedderUnreachableError,
        f", so it stayed busy for {_MAX_ATTEMPTS} attempts",
    ),
    httpx.codes.SERVICE_UNAVAILABLE: (
        RemoteEmbedderUnreachableError,
        f", so it stayed busy for {_MAX_ATTEMPTS} attempts",
    ),
}

# Every other status. The protocol gives the server no reason to answer it here.
_UNKNOWN_STATUS_ERROR: tuple[type[RemoteEmbedderError], str] = (RemoteEmbedderProtocolError, "")

# The content type of a multipart part. The server reads the real format from the header
# of the data, so this value only has to be a type that is not text.
_OCTET_STREAM = "application/octet-stream"

# The longest message that an exception repeats from a server that this client does not
# control.
_MAX_DETAIL_CHARS = 200

_ModelT = TypeVar("_ModelT", bound=BaseModel)

# One multipart part: the name of the field, then the filename, the data and the content
# type of the item.
_FilePart = tuple[str, tuple[str, bytes, str]]


class RemoteTransport:
    """Sends the requests of the embedding protocol to one server.

    The transport holds no address of its own. The ``base_url`` of the client names the
    server, and every request goes to a relative path of the protocol. A test therefore
    passes a client that drives an application in process, and production passes a client
    that opens a socket.
    """

    def __init__(self, client: httpx.Client, api_key: str | None = None) -> None:
        """Send every request through ``client``.

        Args:
            client: The client to send with. Its ``base_url`` names the server. The caller
                owns it and closes it.
            api_key: The token to send as ``Authorization: Bearer``. ``None`` sends no
                header, which is what an unauthenticated server needs.
        """
        self._client = client
        # A header of the request, not of the client: the caller owns the client, and a
        # transport must not put a token on a client that it was lent.
        self._headers = {} if api_key is None else {"Authorization": f"Bearer {api_key}"}

    def describe(self) -> DescribeResponse:
        """Read the identity, the capabilities and the limits of the server.

        Returns:
            What the server reports about itself.

        Raises:
            RemoteEmbedderError: If the server gives no answer, rejects the token, or
                answers a body that the protocol does not allow. A server that speaks
                another major version of the protocol raises
                ``RemoteEmbedderProtocolError``.
        """
        response = self._request(method="GET", path=protocol.DESCRIBE_PATH)
        description = _parse(model=DescribeResponse, response=response)
        _check_protocol_version(description=description, response=response)
        return description

    def embed_texts(self, texts: list[str]) -> EmbeddingsResponse:
        """Embed a batch of strings on the server.

        Args:
            texts: The strings to embed, at most the ``max_batch_size`` of the server.

        Returns:
            The vectors and the indices of the strings that they cover.

        Raises:
            RemoteEmbedderError: If the server gives no answer, refuses the request, or
                answers a body that the protocol does not allow.
        """
        request = EmbedTextsRequest(texts=texts)
        response = self._request(
            method="POST", path=protocol.EMBED_TEXTS_PATH, json=request.model_dump()
        )
        return _parse(model=EmbeddingsResponse, response=response)

    def embed_image_bytes(self, images: list[bytes]) -> EmbeddingsResponse:
        """Embed a batch of encoded images on the server.

        Args:
            images: The encoded images, at most the ``max_batch_size`` of the server.

        Returns:
            The vectors and the indices of the images that they cover.

        Raises:
            RemoteEmbedderError: If the server gives no answer, refuses the request, or
                answers a body that the protocol does not allow.
        """
        return self._post_files(path=protocol.EMBED_IMAGES_BYTES_PATH, items=images)

    def embed_video_bytes(self, videos: list[bytes]) -> EmbeddingsResponse:
        """Embed a batch of encoded videos on the server.

        Args:
            videos: The encoded videos, at most the ``max_batch_size`` of the server.

        Returns:
            The vectors and the indices of the videos that they cover.

        Raises:
            RemoteEmbedderError: If the server gives no answer, refuses the request, or
                answers a body that the protocol does not allow.
        """
        return self._post_files(path=protocol.EMBED_VIDEOS_BYTES_PATH, items=videos)

    def _post_files(self, path: str, items: list[bytes]) -> EmbeddingsResponse:
        """Send a batch of items as multipart, one part for each item, in input order."""
        # Every part carries a filename. A parser reads a part without one as a text
        # field, so the route would see no file at all. The name is the position of the
        # item, and the content type only has to be a type that is not text: the server
        # reads the real format from the header of the data.
        files = [
            (protocol.FILES_FIELD_NAME, (str(index), data, _OCTET_STREAM))
            for index, data in enumerate(items)
        ]
        response = self._request(method="POST", path=path, files=files)
        return _parse(model=EmbeddingsResponse, response=response)

    def _request(
        self,
        method: str,
        path: str,
        json: dict[str, Any] | None = None,
        files: list[_FilePart] | None = None,
    ) -> httpx.Response:
        """Send one request, wait out a busy server, and raise for a status that is not 200.

        Args:
            method: The HTTP method of the request.
            path: The path of the protocol, relative to the ``base_url`` of the client.
            json: The body to send as JSON, if the endpoint reads JSON.
            files: The multipart parts to send, if the endpoint reads multipart.

        Returns:
            The answer of the server, with status 200.

        Raises:
            RemoteEmbedderError: If the server gives no answer or answers a status that
                carries no embeddings.
        """
        attempt = 1
        while True:
            response = self._send(method=method, path=path, json=json, files=files)
            if response.status_code not in _RETRY_STATUSES or attempt >= _MAX_ATTEMPTS:
                break
            attempt += 1
            time.sleep(_retry_wait_seconds(response=response))
        _check_status(response=response)
        return response

    def _send(
        self,
        method: str,
        path: str,
        json: dict[str, Any] | None,
        files: list[_FilePart] | None,
    ) -> httpx.Response:
        """Make one attempt. A failure of the network is the one error without a status."""
        try:
            return self._client.request(
                method=method, url=path, headers=self._headers, json=json, files=files
            )
        except httpx.HTTPError as error:
            raise RemoteEmbedderUnreachableError(
                f"The embedding server at {self._client.base_url} did not answer "
                f"{method} {path}: {error}"
            ) from error


def _check_status(response: httpx.Response) -> None:
    """Raise the error that names the status of an answer. 200 is the only status with a body.

    A 429 and a 503 arrive here only after the attempts of ``_request`` are spent, so the
    server stayed busy for as long as the client waits.
    """
    status = response.status_code
    if status == httpx.codes.OK:
        return
    error_type, reason = _STATUS_ERRORS.get(status, _UNKNOWN_STATUS_ERROR)
    raise error_type(
        f"The embedding server answered {status} to {_where(response=response)}{reason}: "
        f"{_detail(response=response)}"
    )


def _parse(model: type[_ModelT], response: httpx.Response) -> _ModelT:
    """Read the body of an answer into a wire model.

    The wire models hold the rules of the protocol, so a body that breaks one never
    becomes a vector.

    Args:
        model: The wire model that the endpoint answers.
        response: The answer to read.

    Returns:
        The body of the answer.

    Raises:
        RemoteEmbedderProtocolError: If the body is not JSON, or if it breaks a rule of
            the model.
    """
    where = _where(response=response)
    try:
        body = response.json()
    except ValueError as error:
        raise RemoteEmbedderProtocolError(
            f"The embedding server answered {where} with a body that is not JSON."
        ) from error
    try:
        return model.model_validate(body)
    except ValidationError as error:
        raise RemoteEmbedderProtocolError(
            f"The embedding server answered {where} with a body that the protocol does not "
            f"allow: {_broken_rules(error=error)}"
        ) from error


def _broken_rules(error: ValidationError) -> str:
    """Name the field and the rule of every error in one line.

    The message of a pydantic error repeats the value that failed, here the answer of a
    server that this client does not control. That value can be a whole matrix of vectors,
    so only the field and the rule reach the exception.
    """
    rules = []
    for detail in error.errors():
        location = ".".join(str(part) for part in detail["loc"])
        rules.append(f"{location}: {detail['msg']}" if location else detail["msg"])
    return "; ".join(rules)


def _detail(response: httpx.Response) -> str:
    """Read the message of an error answer, short enough to put in an exception.

    Every error of a server of this protocol carries ``{"detail": ...}``. A server that
    this client does not control can answer anything, so a body that is not JSON is read
    as text, and a long text is cut.
    """
    try:
        body = response.json()
    except ValueError:
        body = None
    detail = body.get("detail") if isinstance(body, dict) else None
    text = (str(detail) if detail is not None else response.text).strip()
    if len(text) > _MAX_DETAIL_CHARS:
        return f"{text[:_MAX_DETAIL_CHARS]}..."
    return text


def _check_protocol_version(description: DescribeResponse, response: httpx.Response) -> None:
    """Check that the server speaks a version of the protocol that this client reads.

    Only the major version has to match. A minor version adds fields, and a reader of the
    wire models ignores the fields that it does not know.

    Raises:
        RemoteEmbedderProtocolError: If the major versions are different.
    """
    served = _major(version=description.protocol_version)
    if served != _major(version=protocol.PROTOCOL_VERSION):
        raise RemoteEmbedderProtocolError(
            f"The embedding server at {_where(response=response)} speaks protocol version "
            f"{description.protocol_version}. This client speaks {protocol.PROTOCOL_VERSION}."
        )


def _major(version: str) -> str:
    """The part of a version that both ends must share."""
    return version.partition(".")[0]


def _retry_wait_seconds(response: httpx.Response) -> float:
    """Read how long ``Retry-After`` asks the client to wait.

    A server can name a wait of any length, and the caller of a text query sits under a
    key press, so the answer is capped.

    Returns:
        The wait in seconds, between zero and ``_MAX_RETRY_WAIT_SECONDS``.
    """
    header = response.headers.get("Retry-After")
    if header is None:
        return _DEFAULT_RETRY_WAIT_SECONDS
    seconds = _parse_retry_after(value=header.strip())
    # A header that names zero, or a date that has passed, asks for the request again in
    # the same instant. The default holds the client back from that.
    if seconds is None or seconds <= 0:
        return _DEFAULT_RETRY_WAIT_SECONDS
    return min(seconds, _MAX_RETRY_WAIT_SECONDS)


def _parse_retry_after(value: str) -> float | None:
    """Read a ``Retry-After`` value as a number of seconds from now.

    RFC 9110 writes the value as a number of seconds or as an HTTP date. Both forms are
    read here, because a server picks either one.

    Returns:
        The seconds to wait, which is negative for a date that has passed, or ``None`` if
        the value is neither form.
    """
    try:
        return float(int(value))
    except ValueError:
        pass
    try:
        deadline = email.utils.parsedate_to_datetime(value)
    except (TypeError, ValueError):
        return None
    # An HTTP date carries GMT, but a server can send one without a zone. UTC is the only
    # reading that the standard allows for it.
    if deadline.tzinfo is None:
        deadline = deadline.replace(tzinfo=timezone.utc)
    return (deadline - datetime.now(tz=timezone.utc)).total_seconds()


def _where(response: httpx.Response) -> str:
    """Name the request that an answer belongs to, for the message of an exception."""
    return f"{response.request.method} {response.request.url}"
