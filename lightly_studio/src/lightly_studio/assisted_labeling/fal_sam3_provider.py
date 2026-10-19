"""Provider for the fal.ai hosted SAM 3 models."""

from __future__ import annotations

import contextlib
import importlib.util
import logging
import os
import threading
from collections import OrderedDict
from collections.abc import Iterator
from pathlib import PurePosixPath
from typing import TYPE_CHECKING, Any, Callable
from uuid import UUID

import httpx
import numpy as np
from numpy.typing import NDArray

from lightly_studio.assisted_labeling.provider import (
    Prediction,
    ProviderError,
    ProviderImage,
    ProviderUnavailableError,
    SegmentationPrompt,
)

if TYPE_CHECKING:
    from fal_client import FalClientHTTPError, SyncClient

logger = logging.getLogger(__name__)

FAL_KEY_ENV_VAR = "FAL_KEY"
MISSING_KEY_REASON = f"Set the {FAL_KEY_ENV_VAR} environment variable."
MISSING_EXTRA_REASON = 'Install the fal extra: pip install "lightly-studio[fal]".'
MAX_CACHED_IMAGE_URLS = 256
REQUEST_TIMEOUT_S = 60.0
TIMEOUT_MESSAGE = f"fal.ai did not answer within {REQUEST_TIMEOUT_S:g} s."

# TODO(iunir, 10/2026): The offset is not verified against a live response.
RLE_START_OFFSET = 0
"""Value to subtract from each RLE start to get a 0-based pixel index."""

ENDPOINT = "fal-ai/sam-3/image-rle"

# fal.ai answers 504 with this header when `start_timeout` expires.
_HTTP_STATUS_GATEWAY_TIMEOUT = 504
_REQUEST_TIMEOUT_TYPE_HEADER = "X-Fal-Request-Timeout-Type"

_CONTENT_TYPES = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
}
_DEFAULT_CONTENT_TYPE = "image/jpeg"


class FalSam3Provider:
    """Segments images with SAM 3 on fal.ai through the fal.ai synchronous API.

    Needs the `fal` extra and the `FAL_KEY` environment variable. Uploads each image once and
    caches its URL by sample ID. The client keeps the key of its first call, so a key change
    needs a restart.
    """

    def __init__(self, create_client: Callable[[str], SyncClient] | None = None) -> None:
        """Creates the provider.

        Args:
            create_client: Creates the fal.ai client from the API key. Creates a
                `fal_client.SyncClient` if None.
        """
        self._create_client = create_client if create_client is not None else _create_client
        self._client: SyncClient | None = None
        self._client_lock = threading.Lock()
        self._image_urls: OrderedDict[UUID, str] = OrderedDict()
        self._image_urls_lock = threading.Lock()

    def unavailable_reason(self) -> str | None:
        """Returns None if the fal extra is installed and the API key is set, else a reason."""
        if importlib.util.find_spec("fal_client") is None:
            return MISSING_EXTRA_REASON
        if _read_fal_key() is None:
            return MISSING_KEY_REASON
        return None

    def segment(self, image: ProviderImage, prompt: SegmentationPrompt) -> list[Prediction]:
        """Runs SAM 3 on fal.ai and returns the predicted masks."""
        client = self._get_client()
        image_url = self._get_image_url(client=client, image=image)
        # fal-client retries connection errors and status 408, 409 and 429. With
        # `start_timeout`, it does not retry timeouts of `run`, but it retries upload timeouts.
        with _fal_errors_as_provider_errors():
            output = client.run(
                application=ENDPOINT,
                arguments=build_request_body(image_url=image_url, prompt=prompt),
                timeout=REQUEST_TIMEOUT_S,
                start_timeout=REQUEST_TIMEOUT_S,
            )
        if not isinstance(output, dict):
            raise ProviderError(f"fal.ai returned unexpected JSON: {output!r}")
        return parse_response(output=output, width=image.width, height=image.height)

    def _get_client(self) -> SyncClient:
        reason = self.unavailable_reason()
        if reason is not None:
            raise ProviderUnavailableError(reason)
        with self._client_lock:
            if self._client is None:
                try:
                    self._client = self._create_client(os.environ[FAL_KEY_ENV_VAR])
                except ImportError as error:
                    raise ProviderUnavailableError(MISSING_EXTRA_REASON) from error
            return self._client

    def _get_image_url(self, client: SyncClient, image: ProviderImage) -> str:
        # The lock also covers the upload, so each image is uploaded once.
        with self._image_urls_lock:
            url = self._image_urls.get(image.sample_id)
            if url is None:
                url = _upload(client=client, image=image)
                self._image_urls[image.sample_id] = url
                if len(self._image_urls) > MAX_CACHED_IMAGE_URLS:
                    self._image_urls.popitem(last=False)
            self._image_urls.move_to_end(image.sample_id)
            return url


def build_request_body(image_url: str, prompt: SegmentationPrompt) -> dict[str, Any]:
    """Returns the JSON input of the fal.ai SAM 3 RLE endpoint.

    Args:
        image_url: URL of the image.
        prompt: The prompts to send. Without text, an empty text prompt is sent,
            because the endpoint uses a default text prompt otherwise.
    """
    body: dict[str, Any] = {
        "image_url": image_url,
        "prompt": prompt.text or "",
        "max_masks": prompt.max_masks,
        "return_multiple_masks": prompt.max_masks > 1,
        "include_scores": True,
        "include_boxes": False,
        "apply_mask": False,
    }
    if prompt.points:
        body["point_prompts"] = [
            {
                "x": point.x,
                "y": point.y,
                "label": 1 if point.positive else 0,
                # Without a shared object id, SAM 3 treats each point as a separate object.
                "object_id": 0,
            }
            for point in prompt.points
        ]
    if prompt.boxes:
        body["box_prompts"] = [
            {"x_min": box.x_min, "y_min": box.y_min, "x_max": box.x_max, "y_max": box.y_max}
            for box in prompt.boxes
        ]
    return body


def parse_response(output: dict[str, Any], width: int, height: int) -> list[Prediction]:
    """Converts the JSON output of the SAM 3 RLE endpoint to predictions.

    Args:
        output: JSON output with `rle` as a string or a list of strings, and optional
            `scores` in the same order.
        width: Image width in pixels.
        height: Image height in pixels.

    Returns:
        One prediction for each non-empty RLE string.

    Raises:
        ProviderError: If the output has no valid `rle` or an invalid score.
    """
    if "rle" not in output:
        raise ProviderError(f"fal.ai returned no RLE: {output!r}")
    rle = output["rle"]
    if isinstance(rle, str):
        rles = [rle]
    elif isinstance(rle, list) and all(isinstance(item, str) for item in rle):
        rles = rle
    else:
        raise ProviderError(f"fal.ai returned an invalid RLE: {rle!r}")
    scores = output.get("scores") or []
    if not isinstance(scores, list):
        raise ProviderError(f"fal.ai returned invalid scores: {scores!r}")
    predictions = []
    for index, rle_string in enumerate(rles):
        if not rle_string:
            continue
        score = scores[index] if index < len(scores) else None
        try:
            parsed_score = float(score) if score is not None else None
        except (TypeError, ValueError) as error:
            raise ProviderError(f"fal.ai returned an invalid score: {score!r}") from error
        predictions.append(
            Prediction(
                mask=decode_rle(rle=rle_string, width=width, height=height),
                score=parsed_score,
            )
        )
    return predictions


def decode_rle(
    rle: str, width: int, height: int, start_offset: int = RLE_START_OFFSET
) -> NDArray[np.bool_]:
    """Decodes a fal.ai RLE string to a full-image mask.

    The RLE string has space-separated `start length` pairs. The starts index the
    row-major flattened image.

    Args:
        rle: The RLE string.
        width: Image width W in pixels.
        height: Image height H in pixels.
        start_offset: Value to subtract from each start to get a 0-based index.

    Returns:
        Mask of shape (H, W) and dtype `np.bool_`.

    Raises:
        ProviderError: If the RLE string is not valid.
    """
    try:
        values = [int(value) for value in rle.split()]
    except ValueError as error:
        raise ProviderError(f"fal.ai returned an invalid RLE string: {rle[:100]!r}") from error
    if len(values) % 2 != 0:
        raise ProviderError("fal.ai returned an RLE string with an odd number of values.")
    if any(value < 0 for value in values):
        raise ProviderError("fal.ai returned an RLE string with a negative value.")
    size = width * height
    flat = np.zeros(size, dtype=np.bool_)
    clipped = False
    for start, length in zip(values[0::2], values[1::2]):
        begin = start - start_offset
        end = begin + length
        if begin < 0 or end > size:
            clipped = True
        flat[min(max(begin, 0), size) : min(max(end, 0), size)] = True
    if clipped:
        logger.warning("Clipped RLE runs to the image size %d.", size)
    return flat.reshape(height, width)


def content_type_for(file_name: str) -> str:
    """Returns the image content type for the file extension. The default is JPEG."""
    return _CONTENT_TYPES.get(PurePosixPath(file_name).suffix.lower(), _DEFAULT_CONTENT_TYPE)


def _upload(client: SyncClient, image: ProviderImage) -> str:
    data = image.read_bytes()
    with _fal_errors_as_provider_errors():
        # The fallback "fal" repository uploads without a timeout, so it is not used.
        return client.upload(
            data=data,
            content_type=content_type_for(file_name=image.file_name),
            file_name=image.file_name,
            fallback_repository=[],
        )


def _create_client(fal_key: str) -> SyncClient:
    # The fal extra is optional, so fal_client is imported on use.
    import fal_client  # noqa: PLC0415

    return fal_client.SyncClient(key=fal_key, default_timeout=REQUEST_TIMEOUT_S)


@contextlib.contextmanager
def _fal_errors_as_provider_errors() -> Iterator[None]:
    import fal_client  # noqa: PLC0415

    try:
        yield
    except (httpx.TimeoutException, fal_client.FalClientTimeoutError) as error:
        raise ProviderError(TIMEOUT_MESSAGE) from error
    except fal_client.FalClientHTTPError as error:
        is_timeout = _is_start_timeout_expiry(error=error)
        message = TIMEOUT_MESSAGE if is_timeout else f"fal.ai request failed: {error}"
        raise ProviderError(message) from error
    except (httpx.HTTPError, fal_client.FalClientError) as error:
        raise ProviderError(f"fal.ai request failed: {error}") from error
    except (KeyError, ValueError) as error:
        raise ProviderError(f"fal.ai returned an invalid response: {error!r}") from error


def _is_start_timeout_expiry(error: FalClientHTTPError) -> bool:
    """Returns True if fal.ai answered 504 because `start_timeout` expired."""
    return (
        error.status_code == _HTTP_STATUS_GATEWAY_TIMEOUT
        and _REQUEST_TIMEOUT_TYPE_HEADER in error.response.headers
    )


def _read_fal_key() -> str | None:
    return os.environ.get(FAL_KEY_ENV_VAR) or None
