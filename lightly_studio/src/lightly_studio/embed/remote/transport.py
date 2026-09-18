"""Sends the requests of the LightlyStudio embedding protocol over HTTP.

``RemoteTransport`` sends the requests of version 1 of the protocol and reads the answers
back into the wire models of ``lightly_studio_serve``, so the client and the server cannot
drift apart. A status that is not 200 becomes the exception of ``errors`` that names its
cause. A 429 or a 503 is sent again, for a capped number of attempts and after a capped
wait.

The transport holds no state of the server. ``RemoteEmbedder`` reads ``/v1/describe`` once
and keeps the answer for the lifetime of the process.
"""

from __future__ import annotations

import email.utils
import time
from dataclasses import dataclass
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
    # The protocol names 501, but a server that mounts only the routes of its own
    # capabilities never reaches one: its router answers 404 first. `create_app` of
    # `lightly_studio_serve` is such a server.
    httpx.codes.NOT_FOUND: (RemoteEmbedderCapabilityError, ", so it does not serve that path"),
    httpx.codes.TOO_MANY_REQUESTS: (
        RemoteEmbedderUnreachableError,
        f", so it stayed busy for {_MAX_ATTEMPTS} attempts",
    ),
    httpx.codes.SERVICE_UNAVAILABLE: (
        RemoteEmbedderUnreachableError,
        f", so it stayed busy for {_MAX_ATTEMPTS} attempts",
    ),
}

# The content type of a multipart part. The server reads the real format from the header
# of the data, so this value only has to be a type that is not text.
_OCTET_STREAM = "application/octet-stream"

# The longest message that an exception repeats from a server that this client does not
# control. Long enough to carry a stack trace or a validation report that names the real
# cause, short enough to keep an unbounded body out of a log line.
_MAX_DETAIL_CHARS = 1000

_ModelT = TypeVar("_ModelT", bound=BaseModel)

# One multipart part: the name of the field, then the filename, the data and the content
# type of the item.
_FilePart = tuple[str, tuple[str, bytes, str]]

# The time to open a connection, the same for every request. A server that does not accept
# a connection inside it is down, whatever the request was going to carry.
_CONNECT_SECONDS = 3.0

# `/v1/describe` carries no payload, and it runs at construction with
# `EmbedderRegistry.register` waiting on it.
_DESCRIBE_READ_SECONDS = 10.0

# A text query sits under the Enter key of a user in the GUI. A ceiling above this is a
# hang, not a slow answer.
_TEXT_READ_SECONDS = 10.0

# A batch of encoded images. The server decodes each one and runs a forward pass over it.
_IMAGE_BYTES_READ_SECONDS = 120.0

# A batch of encoded videos. Decoding a video is the most expensive work that a server of
# this protocol does.
_VIDEO_BYTES_READ_SECONDS = 300.0


@dataclass(frozen=True)
class RemoteTimeouts:
    """The budget of one request, per capability.

    One budget for every call is wrong in both directions. A text query answers while a
    user waits on it, so a high ceiling turns a broken server into a hang. A batch of
    encoded videos needs far longer than that, and the same low ceiling would fail on a
    server that is working correctly.

    Each field carries the connect, read, write and pool budget of the requests of one
    capability. ``DEFAULT_TIMEOUTS`` holds the values that this client applies, and
    ``dataclasses.replace`` changes one of them.

    Attributes:
        describe: The budget of ``GET /v1/describe``.
        text: The budget of ``POST /v1/embed/texts``.
        image_bytes: The budget of ``POST /v1/embed/images/bytes``.
        video_bytes: The budget of ``POST /v1/embed/videos/bytes``.
    """

    describe: httpx.Timeout
    text: httpx.Timeout
    image_bytes: httpx.Timeout
    video_bytes: httpx.Timeout


# The write budget follows the read budget of the same capability, because sending a batch
# of encoded items over a slow link is a write and not a read. The pool budget follows the
# connect budget: both are the wait for a connection.
DEFAULT_TIMEOUTS = RemoteTimeouts(
    describe=httpx.Timeout(
        connect=_CONNECT_SECONDS,
        read=_DESCRIBE_READ_SECONDS,
        write=_DESCRIBE_READ_SECONDS,
        pool=_CONNECT_SECONDS,
    ),
    text=httpx.Timeout(
        connect=_CONNECT_SECONDS,
        read=_TEXT_READ_SECONDS,
        write=_TEXT_READ_SECONDS,
        pool=_CONNECT_SECONDS,
    ),
    image_bytes=httpx.Timeout(
        connect=_CONNECT_SECONDS,
        read=_IMAGE_BYTES_READ_SECONDS,
        write=_IMAGE_BYTES_READ_SECONDS,
        pool=_CONNECT_SECONDS,
    ),
    video_bytes=httpx.Timeout(
        connect=_CONNECT_SECONDS,
        read=_VIDEO_BYTES_READ_SECONDS,
        write=_VIDEO_BYTES_READ_SECONDS,
        pool=_CONNECT_SECONDS,
    ),
)


class RemoteTransport:
    """Sends the requests of the embedding protocol to one server.

    The transport holds no address of its own. The ``base_url`` of the client names the
    server, and every request goes to a relative path of the protocol. A test therefore
    passes a client that drives an application in process, and production passes a client
    that opens a socket.
    """

    def __init__(
        self,
        client: httpx.Client,
        api_key: str | None = None,
        timeouts: RemoteTimeouts | None = None,
    ) -> None:
        """Send every request through ``client``.

        Args:
            client: The client to send with. Its ``base_url`` names the server. The caller
                owns it and closes it.
            api_key: The token to send as ``Authorization: Bearer``. ``None`` sends no
                header, which is what an unauthenticated server needs.
            timeouts: The budget of each capability. ``None`` applies
                ``DEFAULT_TIMEOUTS``. The budget goes on the request, so it also overrides
                the one of a client that the caller passes in.
        """
        self._client = client
        # A header of the request, not of the client: the caller owns the client, and a
        # transport must not put a token on a client that it was lent.
        self._headers = {} if api_key is None else {"Authorization": f"Bearer {api_key}"}
        self._timeouts = timeouts if timeouts is not None else DEFAULT_TIMEOUTS

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
        response = self._request(
            method="GET", path=protocol.DESCRIBE_PATH, timeout=self._timeouts.describe
        )
        body = _read_json(response=response)
        # Before the model, not after it. See `_check_protocol_version`.
        _check_protocol_version(body=body, response=response)
        return _validate(model=DescribeResponse, body=body, response=response)

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
            method="POST",
            path=protocol.EMBED_TEXTS_PATH,
            json=request.model_dump(),
            timeout=self._timeouts.text,
        )
        return _parse(model=EmbeddingsResponse, response=response)

    def embed_image_bytes(self, images: list[bytes]) -> EmbeddingsResponse:
        """Embed a batch of encoded images on the server.

        Args:
            images: The encoded images (JPEG, PNG or WebP), at most the
                ``max_batch_size`` of the server. Each one goes on the wire as it is
                stored, with no decoding step here: the server reads the format from the
                header of the data, and it does not trust what this client claims.

        Returns:
            The vectors and the indices of the images that they cover.

        Raises:
            RemoteEmbedderError: If the server gives no answer, refuses the request, or
                answers a body that the protocol does not allow.
        """
        return self._post_files(
            path=protocol.EMBED_IMAGES_BYTES_PATH,
            items=images,
            timeout=self._timeouts.image_bytes,
        )

    def embed_video_bytes(self, videos: list[bytes]) -> EmbeddingsResponse:
        """Embed a batch of encoded videos on the server.

        Args:
            videos: The encoded videos, at most the ``max_batch_size`` of the server.
                Each one goes on the wire as it is stored, and the server reads the
                format from the header of the data. The protocol names no fixed set of
                container formats, so what a server accepts is what its model can read.

        Returns:
            The vectors and the indices of the videos that they cover.

        Raises:
            RemoteEmbedderError: If the server gives no answer, refuses the request, or
                answers a body that the protocol does not allow.
        """
        return self._post_files(
            path=protocol.EMBED_VIDEOS_BYTES_PATH,
            items=videos,
            timeout=self._timeouts.video_bytes,
        )

    def _post_files(
        self, path: str, items: list[bytes], timeout: httpx.Timeout
    ) -> EmbeddingsResponse:
        """Send a batch of items as multipart, one part for each item, in input order.

        Raises:
            ValueError: If ``items`` is empty. httpx then writes no body at all, so the
                server cannot read the request and answers 400.
        """
        if not items:
            raise ValueError(f"An empty batch cannot be sent to {path}. Return an empty result.")
        # Every part carries a filename. A parser reads a part without one as a text
        # field, so the route would see no file at all. The name is the position of the
        # item, and the content type only has to be a type that is not text: the server
        # reads the real format from the header of the data.
        files = [
            (protocol.FILES_FIELD_NAME, (str(index), data, _OCTET_STREAM))
            for index, data in enumerate(items)
        ]
        response = self._request(method="POST", path=path, files=files, timeout=timeout)
        return _parse(model=EmbeddingsResponse, response=response)

    def _request(
        self,
        method: str,
        path: str,
        timeout: httpx.Timeout,
        json: dict[str, Any] | None = None,
        files: list[_FilePart] | None = None,
    ) -> httpx.Response:
        """Send one request, wait out a busy server, and raise for a status that is not 200.

        The budget covers one attempt. A server that stays busy therefore holds the caller
        for the budget plus the waits that its ``Retry-After`` headers ask for.

        Args:
            method: The HTTP method of the request.
            path: The path of the protocol, relative to the ``base_url`` of the client.
            timeout: The budget of this request, from the capability that it serves.
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
            response = self._send(method=method, path=path, timeout=timeout, json=json, files=files)
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
        timeout: httpx.Timeout,
        json: dict[str, Any] | None,
        files: list[_FilePart] | None,
    ) -> httpx.Response:
        """Make one attempt. A failure of the network is the one error without a status."""
        try:
            # The budget goes on the request. It therefore also applies to a client that
            # the caller passed in, which carries a budget of its own.
            return self._client.request(
                method=method,
                url=path,
                headers=self._headers,
                json=json,
                files=files,
                timeout=timeout,
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
    # Every other status. The protocol gives the server no reason to answer one here.
    error_type, reason = _STATUS_ERRORS.get(status, (RemoteEmbedderProtocolError, ""))
    raise error_type(
        f"The embedding server answered {status} to {_where(response=response)}{reason}: "
        f"{_detail(response=response)}"
    )


def _parse(model: type[_ModelT], response: httpx.Response) -> _ModelT:
    """Read the body of an answer into a wire model.

    The wire models hold the rules of the protocol, so a body that breaks one never
    becomes a vector.

    Raises:
        RemoteEmbedderProtocolError: If the body is not JSON, or breaks a rule of the model.
    """
    return _validate(model=model, body=_read_json(response=response), response=response)


def _read_json(response: httpx.Response) -> Any:
    """Read the body of an answer as JSON, whatever shape it has.

    Raises:
        RemoteEmbedderProtocolError: If the body is not JSON.
    """
    try:
        return response.json()
    except ValueError as error:
        raise RemoteEmbedderProtocolError(
            f"The embedding server answered {_where(response=response)} with a body that is "
            f"not JSON."
        ) from error


def _validate(model: type[_ModelT], body: Any, response: httpx.Response) -> _ModelT:
    """Read a JSON body into a wire model.

    Raises:
        RemoteEmbedderProtocolError: If the body breaks a rule of the model.
    """
    try:
        return model.model_validate(body)
    except ValidationError as error:
        raise RemoteEmbedderProtocolError(
            f"The embedding server answered {_where(response=response)} with a body that the "
            f"protocol does not allow: {_broken_rules(error=error)}"
        ) from error


def _broken_rules(error: ValidationError) -> str:
    """Name the field and the rule of every error in one line.

    The message of a pydantic error repeats the value that failed, which can be a whole
    matrix of vectors, so only the field and the rule reach the exception.
    """
    rules = []
    for detail in error.errors():
        location = ".".join(str(part) for part in detail["loc"])
        rules.append(f"{location}: {detail['msg']}" if location else detail["msg"])
    # Pydantic gives one error per bad element of a list, so a long batch gives a list
    # of errors as long as the batch.
    return _cut(text="; ".join(rules))


def _detail(response: httpx.Response) -> str:
    """Read the message of an error answer, short enough to put in an exception.

    Every error of a server of this protocol carries ``{"detail": ...}``, but a body that
    is not JSON is read as text.
    """
    try:
        body = response.json()
    except ValueError:
        body = None
    detail = body.get("detail") if isinstance(body, dict) else None
    return _cut(text=(str(detail) if detail is not None else response.text).strip())


def _check_protocol_version(body: Any, response: httpx.Response) -> None:
    """Check that the server speaks a version of the protocol that this client reads.

    Only the major version has to match. A minor version adds fields, and a reader of the
    wire models ignores the fields that it does not know.

    The check reads the raw body, because it has to run before the model does. A server of
    another major version is the one most likely to answer a body of another shape, and
    ``DescribeResponse`` would then fail on the fields rather than on the reason for them.
    A body that carries no version reaches the model, which holds the default.

    Raises:
        RemoteEmbedderProtocolError: If the major versions are different.
    """
    served = body.get("protocol_version") if isinstance(body, dict) else None
    if not isinstance(served, str):
        return
    if _major(version=served) != _major(version=protocol.PROTOCOL_VERSION):
        raise RemoteEmbedderProtocolError(
            f"The embedding server at {_where(response=response)} speaks protocol version "
            f"{served}. This client speaks {protocol.PROTOCOL_VERSION}."
        )


def _major(version: str) -> str:
    """The part of a version that both ends must share."""
    return version.partition(".")[0]


def _retry_wait_seconds(response: httpx.Response) -> float:
    """Read how long ``Retry-After`` asks the client to wait.

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


def _cut(text: str) -> str:
    """Cut a message of a server that this client does not control, so its length is bounded."""
    if len(text) > _MAX_DETAIL_CHARS:
        return f"{text[:_MAX_DETAIL_CHARS]}..."
    return text
