"""Provider for the fal.ai hosted SAM 3 models."""

from __future__ import annotations

import logging
import os
import threading
from collections import OrderedDict
from dataclasses import dataclass
from typing import Any
from uuid import UUID

import numpy as np
import requests
from numpy.typing import NDArray

from lightly_studio.assisted_labeling import fal_http
from lightly_studio.assisted_labeling.provider import (
    Prediction,
    ProviderCapabilities,
    ProviderError,
    ProviderImage,
    SegmentationPrompt,
)

logger = logging.getLogger(__name__)

FAL_KEY_ENV_VAR = "FAL_KEY"
MAX_MASKS = 32
MAX_CACHED_IMAGE_URLS = 256

# TODO(Jonas, 10/2026): Verify with a live request whether RLE starts are 0- or 1-based.
RLE_START_OFFSET = 0
"""Value to subtract from each RLE start to get a 0-based pixel index."""


@dataclass(frozen=True)
class FalSamModel:
    """A SAM 3 model on fal.ai and its request quirks.

    Attributes:
        provider_id: Stable ID of the provider.
        display_name: Human-readable name of the provider.
        endpoint: fal.ai model endpoint, for example `fal-ai/sam-3/image-rle`.
        supports_points: True if the endpoint handles point prompts.
        blank_text_prompt: Text prompt to send if the prompt has no text. The endpoints
            use a default text prompt if the field is missing.
    """

    provider_id: str
    display_name: str
    endpoint: str
    supports_points: bool
    blank_text_prompt: str


SAM3 = FalSamModel(
    provider_id="fal_sam3",
    display_name="fal.ai SAM 3",
    endpoint="fal-ai/sam-3/image-rle",
    supports_points=True,
    blank_text_prompt="",
)
# SAM 3.1 returns a full-image mask for boxes with an empty text prompt, and ignores
# point prompts or returns noise for them.
SAM3_1 = FalSamModel(
    provider_id="fal_sam3_1",
    display_name="fal.ai SAM 3.1",
    endpoint="fal-ai/sam-3-1/image-rle",
    supports_points=False,
    blank_text_prompt=" ",
)


class FalSam3Provider:
    """Segments images with a SAM 3 model on fal.ai through the fal.ai queue API.

    Reads the API key from the `FAL_KEY` environment variable on each call. Uploads each
    image once and caches its URL by sample ID.
    """

    sends_data_to_third_party = True

    def __init__(
        self,
        model: FalSamModel = SAM3,
        session: requests.Session | None = None,
        polling: fal_http.PollingConfig | None = None,
    ) -> None:
        """Creates the provider.

        Args:
            model: The fal.ai model to call.
            session: HTTP session for all requests. A new session is used if None.
            polling: Timing of the queue status requests. Defaults are used if None.
        """
        self.provider_id = model.provider_id
        self.display_name = model.display_name
        self._model = model
        self._session = session if session is not None else requests.Session()
        self._polling = polling if polling is not None else fal_http.PollingConfig()
        self._uploader = fal_http.FalUploader(session=self._session)
        self._image_urls: OrderedDict[UUID, str] = OrderedDict()
        self._image_urls_lock = threading.Lock()
        self._upload_locks: dict[UUID, threading.Lock] = {}

    def capabilities(self) -> ProviderCapabilities:
        """Returns the supported prompt types with up to 32 instances."""
        return ProviderCapabilities(
            positive_points=self._model.supports_points,
            negative_points=self._model.supports_points,
            boxes=True,
            text_prompt=True,
            max_instances=MAX_MASKS,
        )

    def is_available(self) -> str | None:
        """Returns None if the API key is set, else a reason."""
        if os.environ.get(FAL_KEY_ENV_VAR):
            return None
        return f"Set the {FAL_KEY_ENV_VAR} environment variable."

    def prepare(self, image: ProviderImage) -> None:
        """Uploads the image to fal.ai storage if it is not uploaded yet."""
        self._get_image_url(image=image, fal_key=_get_fal_key())

    def segment(self, image: ProviderImage, prompt: SegmentationPrompt) -> list[Prediction]:
        """Runs the SAM 3 model on fal.ai and returns the predicted masks."""
        if prompt.points and not self._model.supports_points:
            raise ProviderError(f"{self.display_name} does not support point prompts.")
        fal_key = _get_fal_key()
        image_url = self._get_image_url(image=image, fal_key=fal_key)
        output = fal_http.run_queue_request(
            session=self._session,
            fal_key=fal_key,
            endpoint=self._model.endpoint,
            body=build_request_body(
                image_url=image_url,
                prompt=prompt,
                blank_text_prompt=self._model.blank_text_prompt,
            ),
            polling=self._polling,
        )
        return parse_response(output=output, width=image.width, height=image.height)

    def _get_image_url(self, image: ProviderImage, fal_key: str) -> str:
        with self._image_urls_lock:
            upload_lock = self._upload_locks.setdefault(image.sample_id, threading.Lock())
        # The per-sample lock prevents parallel uploads of the same image.
        with upload_lock:
            with self._image_urls_lock:
                cached_url = self._image_urls.get(image.sample_id)
                if cached_url is not None:
                    self._image_urls.move_to_end(image.sample_id)
                    return cached_url
            url = self._uploader.upload(
                fal_key=fal_key, file_name=image.file_name, data=image.read_bytes()
            )
            with self._image_urls_lock:
                self._image_urls[image.sample_id] = url
                self._upload_locks.pop(image.sample_id, None)
                if len(self._image_urls) > MAX_CACHED_IMAGE_URLS:
                    self._image_urls.popitem(last=False)
            return url


def build_request_body(
    image_url: str, prompt: SegmentationPrompt, blank_text_prompt: str = ""
) -> dict[str, Any]:
    """Returns the JSON input of the fal.ai SAM 3 and SAM 3.1 RLE endpoints.

    Args:
        image_url: URL of the image.
        prompt: The prompts to send.
        blank_text_prompt: Text prompt to send if the prompt has no text, because the
            endpoints use a default text prompt otherwise.
    """
    max_masks = max(1, min(prompt.max_masks, MAX_MASKS))
    body: dict[str, Any] = {
        "image_url": image_url,
        "prompt": prompt.text or blank_text_prompt,
        "max_masks": max_masks,
        "return_multiple_masks": max_masks > 1,
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
    """Converts the JSON output of the SAM 3 and SAM 3.1 RLE endpoints to predictions.

    Args:
        output: JSON output with `rle` as a string or a list of strings, and optional
            `scores` in the same order.
        width: Image width in pixels.
        height: Image height in pixels.

    Returns:
        One prediction for each non-empty RLE string.
    """
    rle = output.get("rle")
    rles = [rle] if isinstance(rle, str) else list(rle or [])
    scores = output.get("scores") or []
    predictions = []
    for index, rle_string in enumerate(rles):
        if not rle_string:
            continue
        score = scores[index] if index < len(scores) else None
        predictions.append(
            Prediction(
                mask=decode_rle(rle=rle_string, width=width, height=height),
                score=float(score) if score is not None else None,
                class_name=None,
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
    size = width * height
    flat = np.zeros(size, dtype=np.bool_)
    for start, length in zip(values[0::2], values[1::2]):
        begin = start - start_offset
        end = begin + length
        if begin < 0 or end > size:
            logger.warning("Clipping RLE run [%d, %d) to the image size %d.", begin, end, size)
        flat[max(begin, 0) : min(end, size)] = True
    return flat.reshape(height, width)


def _get_fal_key() -> str:
    fal_key = os.environ.get(FAL_KEY_ENV_VAR)
    if not fal_key:
        raise ProviderError(f"Set the {FAL_KEY_ENV_VAR} environment variable.")
    return fal_key
