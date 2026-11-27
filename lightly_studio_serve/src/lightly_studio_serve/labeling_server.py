"""Makes the HTTP endpoints of the labeling protocol from a labeling model.

``mount_labeling_routes`` mounts ``/v1/labeling/describe`` and ``/v1/labeling/predict``
on the router of the application that ``create_app`` builds.
"""

from __future__ import annotations

import contextlib
import logging
import struct
from collections.abc import Iterator, Set
from typing import Annotated

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from PIL import Image as PILImage
from PIL import UnidentifiedImageError
from PIL.Image import Image
from pydantic import ValidationError

from lightly_studio_serve import labeling_protocol, protocol, validation
from lightly_studio_serve.errors import LabelingModelError
from lightly_studio_serve.labeling import LabelingModel, PredictedAnnotation
from lightly_studio_serve.labeling_protocol import (
    LabelingDescribeResponse,
    PredictionsResponse,
    WirePrediction,
)
from lightly_studio_serve.protocol import ServerLimits

logger = logging.getLogger(__name__)

_ImageFile = Annotated[UploadFile, File(alias=labeling_protocol.IMAGE_FIELD_NAME)]
_Threshold = Annotated[
    float, Form(alias=labeling_protocol.THRESHOLD_FIELD_NAME, ge=0, le=1, allow_inf_nan=False)
]

# The formats that LightlyStudio imports. Other formats, for example EPS, start other programs.
_IMAGE_FORMATS = ("PNG", "JPEG", "GIF", "WEBP", "BMP", "TIFF")


def mount_labeling_routes(
    router: APIRouter, labeling_model: LabelingModel, limits: ServerLimits
) -> frozenset[str]:
    """Mount the endpoints of a labeling model.

    Args:
        router: The router of the application.
        labeling_model: The model to serve.
        limits: The limits that the describe endpoint reports.

    Returns:
        The paths that must answer 503 while the model is not ready.
    """

    @router.get(labeling_protocol.LABELING_DESCRIBE_PATH)
    def describe_labeling() -> LabelingDescribeResponse:
        with _properties_checked():
            return LabelingDescribeResponse(
                protocol_version=protocol.PROTOCOL_VERSION,
                model_id=labeling_model.model_id,
                task=labeling_model.task,
                class_names=labeling_model.class_names,
                ready=labeling_model.ready,
                limits=limits,
            )

    # A synchronous handler runs the forward pass in a worker thread, not on the loop.
    @router.post(labeling_protocol.LABELING_PREDICT_PATH)
    def predict(image: _ImageFile, threshold: _Threshold) -> PredictionsResponse:
        pil_image = _decode(file=image)
        predictions = _predict(labeling_model=labeling_model, image=pil_image, threshold=threshold)
        class_names = frozenset(labeling_model.class_names)
        wire_predictions = [
            _to_wire(prediction=prediction, class_names=class_names, image=pil_image)
            for prediction in predictions
        ]
        with _properties_checked():
            return PredictionsResponse(
                model_id=labeling_model.model_id, predictions=wire_predictions
            )

    return frozenset({labeling_protocol.LABELING_PREDICT_PATH})


def _decode(file: UploadFile) -> Image:
    """Read the uploaded file as an RGB image, or answer 422 if it is not an image."""
    try:
        # Pillow reads the pixels lazily, so convert inside the context.
        with PILImage.open(file.file, formats=_IMAGE_FORMATS) as image_file:
            _check_pixel_count(size=image_file.size)
            return image_file.convert("RGB")
    # Pillow raises SyntaxError, struct.error and EOFError for some broken files.
    except (
        UnidentifiedImageError,
        PILImage.DecompressionBombError,
        OSError,
        ValueError,
        SyntaxError,
        struct.error,
        EOFError,
    ) as error:
        raise HTTPException(
            status_code=labeling_protocol.STATUS_UNUSABLE_INPUT,
            detail="The image cannot be decoded.",
        ) from error
    finally:
        file.file.close()


def _check_pixel_count(size: tuple[int, int]) -> None:
    """Refuse an image with more pixels than ``PILImage.MAX_IMAGE_PIXELS``.

    ``Image.open`` refuses only twice that number. Below it, Pillow gives a warning, and
    ``convert`` then uses a lot of memory. ``warnings.catch_warnings`` cannot make the
    warning an error, because it changes a filter of the process, and each request runs in
    a worker thread.
    """
    width, height = size
    max_pixels = PILImage.MAX_IMAGE_PIXELS
    if max_pixels is not None and width * height > max_pixels:
        raise PILImage.DecompressionBombError(
            f"The image has {width * height} pixels, over the limit of {max_pixels}."
        )


def _predict(
    labeling_model: LabelingModel, image: Image, threshold: float
) -> list[PredictedAnnotation]:
    """Run the model, and refuse a result that is not a list of predictions.

    The error of a model becomes a ``LabelingModelError``. The message names the class
    alone, because the text of an exception can hold the input that it failed on. The
    traceback goes to the log.
    """
    try:
        predictions = labeling_model.predict(image=image, threshold=threshold)
    except Exception as error:
        logger.exception("The labeling model failed.")
        raise LabelingModelError(
            f"The labeling model raised {type(error).__name__}. See the server log."
        ) from error
    is_prediction_list = isinstance(predictions, list) and all(
        isinstance(prediction, PredictedAnnotation) for prediction in predictions
    )
    if not is_prediction_list:
        raise LabelingModelError(
            f"The labeling model returned {type(predictions).__name__}, "
            "not a list of PredictedAnnotation."
        )
    return predictions


@contextlib.contextmanager
def _properties_checked() -> Iterator[None]:
    """Name the broken rule of a model property that a response body does not allow."""
    try:
        yield
    except ValidationError as error:
        raise LabelingModelError(
            "The labeling model has a property that is not valid: "
            f"{validation.name_broken_rules(error)}"
        ) from error


def _to_wire(
    prediction: PredictedAnnotation, class_names: Set[str], image: Image
) -> WirePrediction:
    """Convert one prediction, and name the rule that a broken one breaks.

    A client cannot use a prediction of a class that the model does not declare, a box
    without a positive size, or a mask with a size that is not the size of the image.
    """
    try:
        wire_prediction = labeling_protocol.to_wire_prediction(prediction=prediction)
    except ValidationError as error:
        raise _invalid_prediction(problem=validation.name_broken_rules(error)) from error
    except ValueError as error:
        raise _invalid_prediction(problem=str(error)) from error
    if prediction.class_name not in class_names:
        raise _invalid_prediction(
            problem=f"The class name '{prediction.class_name}' is not one of class_names."
        )
    x_min, y_min, x_max, y_max = wire_prediction.box
    if x_min >= x_max or y_min >= y_max:
        raise _invalid_prediction(
            problem=f"The box {wire_prediction.box} does not have a positive size."
        )
    width, height = image.size
    if prediction.mask is not None and prediction.mask.shape != (height, width):
        mask_height, mask_width = prediction.mask.shape
        raise _invalid_prediction(
            problem=f"The mask has the size {mask_width} x {mask_height} pixels, "
            f"but the image has the size {width} x {height} pixels."
        )
    return wire_prediction


def _invalid_prediction(problem: str) -> LabelingModelError:
    return LabelingModelError(
        f"The labeling model returned a prediction that is not valid: {problem}"
    )
