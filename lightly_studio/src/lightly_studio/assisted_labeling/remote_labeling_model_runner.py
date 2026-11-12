"""Runs a labeling model on a server that speaks the labeling protocol.

The server is one that ``lightly_studio_serve.serve(labeling_model=...)`` runs, or another
server that speaks the same protocol. The wire models come from
``lightly_studio_serve.labeling_protocol``, so the two halves cannot drift.
"""

from __future__ import annotations

from typing import TypeVar

import httpx
from lightly_studio_serve import labeling_protocol, protocol
from lightly_studio_serve.labeling_model import ModelTask
from lightly_studio_serve.labeling_protocol import LabelingDescribeResponse, PredictionsResponse
from lightly_studio_serve.types import PredictedAnnotation
from pydantic import BaseModel, ValidationError

from lightly_studio.assisted_labeling.provider import (
    ProviderError,
    ProviderImage,
    ProviderUnavailableError,
)
from lightly_studio.embed.remote import url_policy

# The time to open a connection. A server that does not accept one inside it is down.
_CONNECT_SECONDS = 3.0
# The describe endpoint carries no payload.
_DESCRIBE_TIMEOUT = httpx.Timeout(timeout=10.0, connect=_CONNECT_SECONDS)
# One forward pass over one image. A user waits for the answer in the GUI.
_PREDICT_TIMEOUT = httpx.Timeout(timeout=120.0, connect=_CONNECT_SECONDS)

_STATUS_UNAUTHORIZED = 401
_STATUS_FORBIDDEN = 403
_STATUS_UNAVAILABLE = 503
_STATUS_ERROR_FLOOR = 400
_MAX_DETAIL_LENGTH = 200

_WireModelT = TypeVar("_WireModelT", bound=BaseModel)


class RemoteLabelingModelError(RuntimeError):
    """Raised when a labeling server cannot be connected.

    The server gives no answer, rejects the API key, speaks another protocol, or has an
    address that the URL policy refuses.
    """


class RemoteLabelingModelRunner:
    """Runs the labeling model of one server. Implements ``LabelingModelRunner``."""

    def __init__(
        self, client: httpx.Client, api_key: str | None, description: LabelingDescribeResponse
    ) -> None:
        """Run the model that ``description`` describes through ``client``.

        Use ``connect``, which reads the description from the server.
        """
        self._client = client
        self._headers = _headers(api_key=api_key)
        self._description = description

    @classmethod
    def connect(cls, client: httpx.Client, api_key: str | None = None) -> RemoteLabelingModelRunner:
        """Read ``/v1/labeling/describe`` over ``client`` and build the runner.

        The ``base_url`` of ``client`` names the server. The caller owns the client and
        closes it.

        Args:
            client: The client that carries every request.
            api_key: The token to send as ``Authorization: Bearer``, or ``None`` for a
                server that wants none.

        Raises:
            RemoteLabelingModelError: If the URL policy refuses the address, the client
                follows redirects, the server gives no answer, rejects the token, or
                answers a description that the protocol does not allow.
        """
        try:
            url_policy.check_url(url=str(client.base_url), api_key=api_key)
            url_policy.check_no_redirects(client=client)
        except ValueError as error:
            raise RemoteLabelingModelError(
                f"The labeling server URL {str(client.base_url)!r} is refused: {error}"
            ) from error
        try:
            description = _describe(client=client, headers=_headers(api_key=api_key))
        except (ProviderError, ProviderUnavailableError) as error:
            raise RemoteLabelingModelError(str(error)) from error
        return cls(client=client, api_key=api_key, description=description)

    @property
    def model_id(self) -> str:
        """Unique ID of the model."""
        return self._description.model_id

    @property
    def task(self) -> ModelTask:
        """The kind of annotations that the model predicts."""
        return self._description.task

    @property
    def class_names(self) -> list[str]:
        """Names of the annotation classes that the model can predict."""
        return self._description.class_names

    def close(self) -> None:
        """Close the client of the runner."""
        self._client.close()

    def predict(self, image: ProviderImage, threshold: float) -> list[PredictedAnnotation]:
        """Send the image file to the server and return its predictions.

        Raises:
            NotFoundError: If the image file cannot be read.
            ProviderUnavailableError: If the server gives no answer, rejects the token,
                or still loads its model.
            ProviderError: If the server fails, or answers a body that the protocol does
                not allow.
        """
        data = image.read_bytes()
        response = _request(
            client=self._client,
            headers=self._headers,
            method="POST",
            path=labeling_protocol.LABELING_PREDICT_PATH,
            timeout=_PREDICT_TIMEOUT,
            files={labeling_protocol.IMAGE_FIELD_NAME: (image.file_name, data)},
            data={labeling_protocol.THRESHOLD_FIELD_NAME: repr(threshold)},
        )
        body = _validate(model=PredictionsResponse, response=response)
        if body.model_id != self.model_id:
            raise ProviderError(
                f"The labeling server answered for the model {body.model_id!r}, "
                f"expected {self.model_id!r}. Register the server again."
            )
        try:
            return [
                labeling_protocol.from_wire_prediction(prediction=prediction)
                for prediction in body.predictions
            ]
        except ValueError as error:
            raise ProviderError(
                f"The labeling server answered a mask that is not valid: {error}"
            ) from error


def _headers(api_key: str | None) -> dict[str, str]:
    """The headers of every request. They go on the request, not on the client.

    The caller owns the client, and a runner must not put a token on a client that it
    was lent.
    """
    return {} if api_key is None else {"Authorization": f"Bearer {api_key}"}


def _describe(client: httpx.Client, headers: dict[str, str]) -> LabelingDescribeResponse:
    """Read what the server reports about its labeling model."""
    response = _request(
        client=client,
        headers=headers,
        method="GET",
        path=labeling_protocol.LABELING_DESCRIBE_PATH,
        timeout=_DESCRIBE_TIMEOUT,
    )
    description = _validate(model=LabelingDescribeResponse, response=response)
    _check_protocol_version(served=description.protocol_version)
    return description


# PLR0913: The arguments are the parts of one HTTP request.
def _request(  # noqa: PLR0913
    client: httpx.Client,
    headers: dict[str, str],
    method: str,
    path: str,
    timeout: httpx.Timeout,
    files: dict[str, tuple[str, bytes]] | None = None,
    data: dict[str, str] | None = None,
) -> httpx.Response:
    """Send one request, and turn a failure into an error of the provider interface.

    Raises:
        ProviderUnavailableError: If the server gives no answer, rejects the token, or
            still loads its model.
        ProviderError: If the server answers another error status.
    """
    try:
        response = client.request(
            method=method, url=path, headers=headers, timeout=timeout, files=files, data=data
        )
    except httpx.HTTPError as error:
        raise ProviderUnavailableError(
            f"The labeling server at {client.base_url} gives no answer: {type(error).__name__}."
        ) from error
    if response.status_code in (_STATUS_UNAUTHORIZED, _STATUS_FORBIDDEN):
        raise ProviderUnavailableError(
            f"The labeling server at {client.base_url} rejects the API key."
        )
    if response.status_code == _STATUS_UNAVAILABLE:
        raise ProviderUnavailableError(
            f"The labeling server at {client.base_url} is not ready: {_detail(response=response)}"
        )
    if response.status_code >= _STATUS_ERROR_FLOOR:
        raise ProviderError(
            f"The labeling server answered {response.status_code}: {_detail(response=response)}"
        )
    return response


def _validate(model: type[_WireModelT], response: httpx.Response) -> _WireModelT:
    """Read the body of an answer as a wire model.

    Raises:
        ProviderError: If the body is not what the protocol allows.
    """
    try:
        return model.model_validate_json(response.content)
    except ValidationError as error:
        raise ProviderError(
            f"The labeling server answered a body that is not a {model.__name__}. "
            "Check that the URL names a labeling server."
        ) from error


def _check_protocol_version(served: str) -> None:
    """Check that the server speaks the major version that this client reads.

    Raises:
        ProviderError: If the major versions are different.
    """
    if served.partition(".")[0] != protocol.PROTOCOL_VERSION.partition(".")[0]:
        raise ProviderError(
            f"The labeling server speaks protocol {served!r}. "
            f"This LightlyStudio reads {protocol.PROTOCOL_VERSION!r}."
        )


def _detail(response: httpx.Response) -> str:
    """Read the message of an error answer, short enough to put in an exception."""
    try:
        body = response.json()
    except ValueError:
        body = None
    detail = body.get("detail") if isinstance(body, dict) else None
    text = (str(detail) if detail is not None else response.text).strip()
    return text[:_MAX_DETAIL_LENGTH]
