"""Provider for OpenAI GPT-6 Astra through the OpenAI Responses API.

Astra has no segmentation endpoint. The provider asks for polygons or boxes as strict JSON
and rasterizes them to full-image masks.
"""

from __future__ import annotations

import base64
import io
import json
import logging
import os
import threading
from collections import OrderedDict
from dataclasses import dataclass, replace
from typing import Any
from uuid import UUID

import cv2
import numpy as np
import requests
from numpy.typing import NDArray
from PIL import Image

from lightly_studio.assisted_labeling import astra_prompts
from lightly_studio.assisted_labeling.provider import (
    BoxPrompt,
    OutputType,
    PointPrompt,
    Prediction,
    ProviderCapabilities,
    ProviderError,
    ProviderImage,
    SegmentationPrompt,
)

logger = logging.getLogger(__name__)

OPENAI_API_KEY_ENV_VAR = "OPENAI_API_KEY"
RESPONSES_URL = "https://api.openai.com/v1/responses"
MODEL = "gpt-6-astra"
DEFAULT_REASONING_EFFORT = "medium"
MAX_INSTANCES = 32
MIN_POLYGON_VALUES = 6
MAX_IMAGE_SIDE = 2048
"""Longest side of the sent image in pixels. Larger images are downscaled."""
JPEG_QUALITY = 90
MAX_CACHED_IMAGES = 16
# TODO(Jonas, 10/2026): Read the rates from a config if they change or differ per tier.
INPUT_USD_PER_MILLION_TOKENS = 10.0
CACHED_INPUT_USD_PER_MILLION_TOKENS = 1.0
OUTPUT_USD_PER_MILLION_TOKENS = 50.0
REQUEST_TIMEOUT_S = 300.0
"""Astra reasons before it answers, a polygon request can take more than a minute."""


@dataclass(frozen=True)
class EncodedImage:
    """A JPEG image as it is sent to the model.

    Attributes:
        data_uri: Base64 data URI of the JPEG.
        width: Width of the sent image in pixels.
        height: Height of the sent image in pixels.
    """

    data_uri: str
    width: int
    height: int


@dataclass(frozen=True)
class ImageScale:
    """Size of the original image and its scale in the sent image.

    Attributes:
        width: Original image width in pixels.
        height: Original image height in pixels.
        scale_x: Sent image width divided by the original width.
        scale_y: Sent image height divided by the original height.
    """

    width: int
    height: int
    scale_x: float
    scale_y: float


class OpenAIAstraProvider:
    """Segments images with OpenAI GPT-6 Astra.

    Reads the API key from the `OPENAI_API_KEY` environment variable on each call. Encodes
    each image once and caches it by sample ID.
    """

    provider_id = "openai_astra"
    display_name = "OpenAI GPT-6 Astra"
    sends_data_to_third_party = True

    def __init__(
        self,
        session: requests.Session | None = None,
        reasoning_effort: str = DEFAULT_REASONING_EFFORT,
        timeout_s: float = REQUEST_TIMEOUT_S,
    ) -> None:
        """Creates the provider.

        Args:
            session: HTTP session for all requests. A new session is used if None.
            reasoning_effort: Reasoning effort of the model, for example `medium`.
            timeout_s: Timeout of one model request in seconds.
        """
        self._session = session if session is not None else requests.Session()
        self._reasoning_effort = reasoning_effort
        self._timeout_s = timeout_s
        self._images: OrderedDict[UUID, EncodedImage] = OrderedDict()
        self._images_lock = threading.Lock()

    def capabilities(self) -> ProviderCapabilities:
        """Returns support for all prompt types with up to 32 instances."""
        return ProviderCapabilities(
            positive_points=True,
            negative_points=True,
            boxes=True,
            text_prompt=True,
            max_instances=MAX_INSTANCES,
        )

    def is_available(self) -> str | None:
        """Returns None if the API key is set, else a reason."""
        if os.environ.get(OPENAI_API_KEY_ENV_VAR):
            return None
        return f"Set the {OPENAI_API_KEY_ENV_VAR} environment variable."

    def prepare(self, image: ProviderImage) -> None:
        """Encodes the image if it is not cached yet."""
        self._get_encoded_image(image=image)

    def segment(self, image: ProviderImage, prompt: SegmentationPrompt) -> list[Prediction]:
        """Asks Astra for polygons or boxes and returns them as full-image masks."""
        api_key = _get_api_key()
        encoded = self._get_encoded_image(image=image)
        scale = ImageScale(
            width=image.width,
            height=image.height,
            scale_x=encoded.width / image.width,
            scale_y=encoded.height / image.height,
        )
        body = build_request_body(
            image=encoded,
            prompt=scale_prompt(prompt=prompt, scale=scale),
            reasoning_effort=self._reasoning_effort,
        )
        output = _post_json(
            session=self._session, api_key=api_key, body=body, timeout_s=self._timeout_s
        )
        _log_usage(usage=output.get("usage") or {})
        return parse_instances(
            text=extract_output_text(output=output),
            output_type=prompt.output_type,
            scale=scale,
            class_name=prompt.text,
        )

    def _get_encoded_image(self, image: ProviderImage) -> EncodedImage:
        with self._images_lock:
            cached = self._images.get(image.sample_id)
            if cached is not None:
                self._images.move_to_end(image.sample_id)
                return cached
        # Encoding runs outside the lock. Parallel encodes of the same image are harmless.
        encoded = encode_image(data=image.read_bytes(), max_side=MAX_IMAGE_SIDE)
        with self._images_lock:
            self._images[image.sample_id] = encoded
            if len(self._images) > MAX_CACHED_IMAGES:
                self._images.popitem(last=False)
        return encoded


def encode_image(data: bytes, max_side: int) -> EncodedImage:
    """Decodes an image file and returns it as JPEG with the longest side <= `max_side`.

    Raises:
        ProviderError: If the data is not a valid image.
    """
    try:
        with Image.open(io.BytesIO(data)) as opened:
            rgb = opened.convert("RGB")
    except (OSError, ValueError) as error:
        raise ProviderError("The image file could not be decoded.") from error
    rgb.thumbnail(size=(max_side, max_side))
    buffer = io.BytesIO()
    rgb.save(buffer, format="JPEG", quality=JPEG_QUALITY)
    data_uri = f"data:image/jpeg;base64,{base64.b64encode(buffer.getvalue()).decode('ascii')}"
    return EncodedImage(data_uri=data_uri, width=rgb.width, height=rgb.height)


def scale_prompt(prompt: SegmentationPrompt, scale: ImageScale) -> SegmentationPrompt:
    """Returns the prompt with point and box coordinates scaled to the sent image."""
    sx, sy = scale.scale_x, scale.scale_y
    return replace(
        prompt,
        points=[
            PointPrompt(x=round(point.x * sx), y=round(point.y * sy), positive=point.positive)
            for point in prompt.points
        ],
        boxes=[
            BoxPrompt(
                x_min=round(box.x_min * sx),
                y_min=round(box.y_min * sy),
                x_max=round(box.x_max * sx),
                y_max=round(box.y_max * sy),
            )
            for box in prompt.boxes
        ],
    )


def build_request_body(
    image: EncodedImage, prompt: SegmentationPrompt, reasoning_effort: str
) -> dict[str, Any]:
    """Returns the JSON input of the Responses API.

    Args:
        image: The sent image.
        prompt: Prompts in pixel coordinates of the sent image.
        reasoning_effort: Reasoning effort of the model.
    """
    instructions = astra_prompts.build_instructions(
        prompt=prompt, width=image.width, height=image.height
    )
    return {
        "model": MODEL,
        "reasoning": {"effort": reasoning_effort},
        "input": [
            {
                "role": "user",
                "content": [
                    {"type": "input_text", "text": instructions},
                    # "original" keeps the pixel grid that the coordinates refer to.
                    {"type": "input_image", "image_url": image.data_uri, "detail": "original"},
                ],
            }
        ],
        "text": {"format": astra_prompts.build_response_format(output_type=prompt.output_type)},
    }


def estimate_cost_usd(usage: dict[str, Any]) -> float:
    """Returns the cost of a request in USD at the standard rates.

    Args:
        usage: The `usage` object of a Responses API output. `output_tokens` includes the
            reasoning tokens and `input_tokens` includes the cached tokens.
    """
    input_tokens = int(usage.get("input_tokens") or 0)
    output_tokens = int(usage.get("output_tokens") or 0)
    cached_tokens = int((usage.get("input_tokens_details") or {}).get("cached_tokens") or 0)
    cost_per_million = (
        (input_tokens - cached_tokens) * INPUT_USD_PER_MILLION_TOKENS
        + cached_tokens * CACHED_INPUT_USD_PER_MILLION_TOKENS
        + output_tokens * OUTPUT_USD_PER_MILLION_TOKENS
    )
    return cost_per_million / 1_000_000


def extract_output_text(output: dict[str, Any]) -> str:
    """Returns the text of the first message in a Responses API output.

    Raises:
        ProviderError: If the response is incomplete, a refusal, or has no text.
    """
    if output.get("status") != "completed":
        raise ProviderError(
            f"OpenAI response has status {output.get('status')!r}: "
            f"{output.get('incomplete_details') or output.get('error')}"
        )
    for item in output.get("output") or []:
        if item.get("type") != "message":
            continue
        for content in item.get("content") or []:
            if content.get("type") == "refusal":
                raise ProviderError(f"OpenAI refused the request: {content.get('refusal')}")
            if content.get("type") == "output_text":
                return str(content.get("text", ""))
    raise ProviderError("OpenAI response has no output text.")


def parse_instances(
    text: str,
    output_type: OutputType,
    scale: ImageScale,
    class_name: str | None,
) -> list[Prediction]:
    """Converts the JSON output of the model to full-image masks.

    H and W are the height and width of the original image.

    Args:
        text: JSON text that follows `astra_prompts.build_response_format`.
        output_type: Output type that the request asked for.
        scale: Original image size and its scale in the sent image.
        class_name: Class name of all predictions.

    Returns:
        One prediction with a mask of shape (H, W) for each non-empty instance.

    Raises:
        ProviderError: If the text is not valid JSON of the expected shape.
    """
    try:
        predictions = [
            Prediction(
                mask=_instance_to_mask(instance=instance, output_type=output_type, scale=scale),
                score=float(instance["confidence"]),
                class_name=class_name,
            )
            for instance in json.loads(text)["instances"]
        ]
    except (ValueError, KeyError, TypeError) as error:
        raise ProviderError(f"OpenAI returned an invalid instance list: {text[:500]!r}") from error
    return [prediction for prediction in predictions if prediction.mask.any()]


def polygons_to_mask(polygons: list[list[float]], scale: ImageScale) -> NDArray[np.bool_]:
    """Rasterizes polygons in sent image coordinates to a full-image mask.

    H and W are the height and width of the original image. Polygons with less than 3
    vertices or an odd number of values are skipped.

    Args:
        polygons: Flat vertex lists [x1, y1, x2, y2, ...] in sent image pixels.
        scale: Original image size and its scale in the sent image.

    Returns:
        Mask of shape (H, W) and dtype `np.bool_`.
    """
    canvas = np.zeros((scale.height, scale.width), dtype=np.uint8)
    contours = []
    for polygon in polygons:
        if len(polygon) < MIN_POLYGON_VALUES or len(polygon) % 2 != 0:
            logger.warning("Skipping an invalid polygon with %d values.", len(polygon))
            continue
        vertices = np.asarray(polygon, dtype=np.float64).reshape(-1, 2)
        vertices = vertices / np.array([scale.scale_x, scale.scale_y])
        contours.append(np.round(vertices).astype(np.int32))
    if contours:
        cv2.fillPoly(canvas, contours, color=(1,))
    mask: NDArray[np.bool_] = canvas.astype(np.bool_)
    return mask


def box_to_mask(box: list[float], width: int, height: int) -> NDArray[np.bool_]:
    """Returns a full-image mask that fills the box.

    Args:
        box: [x_min, y_min, x_max, y_max] in original image pixels. The box is clipped to
            the image.
        width: Image width W in pixels.
        height: Image height H in pixels.

    Returns:
        Mask of shape (H, W) and dtype `np.bool_`.
    """
    x_min, y_min, x_max, y_max = box
    mask = np.zeros((height, width), dtype=np.bool_)
    column_start = max(0, int(np.floor(x_min)))
    row_start = max(0, int(np.floor(y_min)))
    column_end = min(width, int(np.ceil(x_max)))
    row_end = min(height, int(np.ceil(y_max)))
    mask[row_start:row_end, column_start:column_end] = True
    return mask


def _instance_to_mask(
    instance: dict[str, Any], output_type: OutputType, scale: ImageScale
) -> NDArray[np.bool_]:
    if output_type == OutputType.MASK:
        return polygons_to_mask(polygons=instance["polygons"], scale=scale)
    return box_to_mask(
        box=[
            instance["x_min"] / scale.scale_x,
            instance["y_min"] / scale.scale_y,
            instance["x_max"] / scale.scale_x,
            instance["y_max"] / scale.scale_y,
        ],
        width=scale.width,
        height=scale.height,
    )


def _log_usage(usage: dict[str, Any]) -> None:
    output_details = usage.get("output_tokens_details") or {}
    logger.info(
        "OpenAI Astra request: %s input tokens, %s output tokens (%s reasoning), "
        "estimated cost $%.4f.",
        usage.get("input_tokens"),
        usage.get("output_tokens"),
        output_details.get("reasoning_tokens"),
        estimate_cost_usd(usage=usage),
    )


def _post_json(
    session: requests.Session, api_key: str, body: dict[str, Any], timeout_s: float
) -> dict[str, Any]:
    try:
        response = session.request(
            method="POST",
            url=RESPONSES_URL,
            headers={"Authorization": f"Bearer {api_key}"},
            json=body,
            timeout=timeout_s,
        )
    except requests.RequestException as error:
        raise ProviderError(f"OpenAI request failed: {error}") from error
    if not response.ok:
        raise ProviderError(
            f"OpenAI request failed with status {response.status_code}: {response.text[:500]}"
        )
    try:
        output = response.json()
    except ValueError as error:
        raise ProviderError("OpenAI returned invalid JSON.") from error
    if not isinstance(output, dict):
        raise ProviderError(f"OpenAI returned unexpected JSON: {output!r}")
    return output


def _get_api_key() -> str:
    api_key = os.environ.get(OPENAI_API_KEY_ENV_VAR)
    if not api_key:
        raise ProviderError(f"Set the {OPENAI_API_KEY_ENV_VAR} environment variable.")
    return api_key
