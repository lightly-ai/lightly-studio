"""Wire models of the LightlyStudio labeling protocol, version 1.

The module holds the response bodies, the route paths and the multipart field names of a
server that serves a ``LabelingModel``. The server in this package sends these models.
``lightly-studio`` reads the same models. One definition keeps the two halves equal.

A mask crosses the wire as a PNG file with one bit for each pixel, in base64. Pillow is
on both sides, and a PNG keeps the shape of the mask.
"""

from __future__ import annotations

import base64
import binascii
import io
from typing import Annotated

import numpy as np
from numpy.typing import NDArray
from PIL import Image as PILImage
from PIL import UnidentifiedImageError
from pydantic import BaseModel, Field

from lightly_studio_serve import protocol
from lightly_studio_serve.labeling_model import ModelTask
from lightly_studio_serve.protocol import ServerLimits
from lightly_studio_serve.types import PredictedAnnotation

LABELING_DESCRIBE_PATH = f"{protocol.BASE_PATH}/labeling/describe"

LABELING_PREDICT_PATH = f"{protocol.BASE_PATH}/labeling/predict"

# The multipart field that holds the image file. The part carries a `filename`.
IMAGE_FIELD_NAME = "image"

# The multipart field that holds the confidence threshold, as a decimal number.
THRESHOLD_FIELD_NAME = "threshold"

# The status of an image that the server cannot decode. A number, because starlette
# renamed its constant for this status.
STATUS_UNUSABLE_INPUT = 422

_FiniteFloat = Annotated[float, Field(allow_inf_nan=False)]


class LabelingDescribeResponse(BaseModel):
    """The body of ``GET /v1/labeling/describe``. Every labeling server has this endpoint."""

    protocol_version: str = protocol.PROTOCOL_VERSION
    """The version of this contract that the server speaks."""

    model_id: str = Field(min_length=1)
    """The unique ID of the labeling model."""

    task: ModelTask
    """The kind of annotations that the model predicts."""

    class_names: list[str]
    """The names of the annotation classes that the model can predict."""

    ready: bool
    """Whether the model is loaded. ``False`` means try again soon. It is not an error."""

    limits: ServerLimits
    """The limits that a client must apply to its requests."""


class WirePrediction(BaseModel):
    """One predicted annotation in a response body."""

    class_name: str
    """The name of the predicted annotation class."""

    box: tuple[_FiniteFloat, _FiniteFloat, _FiniteFloat, _FiniteFloat]
    """The bounding box ``(x_min, y_min, x_max, y_max)`` in pixels."""

    score: _FiniteFloat
    """The confidence score."""

    mask_png: str | None = None
    """The mask as a base64 PNG file with one bit for each pixel, or ``None``."""


class PredictionsResponse(BaseModel):
    """The body of ``POST /v1/labeling/predict``.

    The response repeats ``model_id``. A client reads it to find a server that changed
    its model.
    """

    model_id: str = Field(min_length=1)
    """The unique ID of the labeling model that predicted."""

    predictions: list[WirePrediction]
    """The predicted annotations of the image, in any order."""


def to_wire_prediction(prediction: PredictedAnnotation) -> WirePrediction:
    """Convert a predicted annotation into its wire model.

    Args:
        prediction: What a labeling model returned for one object.

    Returns:
        The wire model of the prediction.

    Raises:
        ValueError: If the mask is not a boolean array with two dimensions.
        pydantic.ValidationError: If the box or the score holds a value that is not finite.
    """
    return WirePrediction(
        class_name=prediction.class_name,
        box=prediction.box,
        score=prediction.score,
        mask_png=None if prediction.mask is None else _encode_mask(mask=prediction.mask),
    )


def from_wire_prediction(prediction: WirePrediction) -> PredictedAnnotation:
    """Convert a wire model back into a predicted annotation.

    Args:
        prediction: One prediction of a response body.

    Returns:
        The predicted annotation, with the mask as a boolean array.

    Raises:
        ValueError: If ``mask_png`` is not a base64 PNG file.
    """
    return PredictedAnnotation(
        class_name=prediction.class_name,
        box=prediction.box,
        score=prediction.score,
        mask=None if prediction.mask_png is None else _decode_mask(mask_png=prediction.mask_png),
    )


def _encode_mask(mask: NDArray[np.bool_]) -> str:
    """Write a mask of shape (H, W) as a base64 PNG file with one bit for each pixel."""
    # Pillow writes a float or integer array as a gray image, not as a mask.
    if not isinstance(mask, np.ndarray) or mask.dtype != np.bool_ or mask.ndim != 2:  # noqa: PLR2004
        raise ValueError("The mask is not a boolean array with two dimensions.")
    buffer = io.BytesIO()
    PILImage.fromarray(mask).save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode("ascii")


def _decode_mask(mask_png: str) -> NDArray[np.bool_]:
    """Read a base64 PNG file as a boolean mask of shape (H, W)."""
    try:
        data = base64.b64decode(mask_png, validate=True)
        with PILImage.open(io.BytesIO(data)) as image:
            return np.asarray(image.convert("1"), dtype=np.bool_)
    except (binascii.Error, UnidentifiedImageError, OSError) as error:
        raise ValueError("mask_png is not a base64 PNG file.") from error
