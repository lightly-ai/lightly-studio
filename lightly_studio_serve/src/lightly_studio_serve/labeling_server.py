"""Makes the HTTP endpoints of the labeling protocol from a labeling model.

``mount_labeling_routes`` mounts ``/v1/labeling/describe`` and ``/v1/labeling/predict``
on the router of the application that ``create_app`` builds.
"""

from __future__ import annotations

import io
import logging
from typing import Annotated

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from PIL import Image as PILImage
from PIL import UnidentifiedImageError
from PIL.Image import Image
from pydantic import ValidationError

from lightly_studio_serve import labeling_protocol, protocol, validation
from lightly_studio_serve.errors import LabelingModelError
from lightly_studio_serve.labeling_model import LabelingModel
from lightly_studio_serve.labeling_protocol import (
    LabelingDescribeResponse,
    PredictionsResponse,
    WirePrediction,
)
from lightly_studio_serve.protocol import ServerLimits
from lightly_studio_serve.types import PredictedAnnotation

logger = logging.getLogger(__name__)

_ImageFile = Annotated[UploadFile, File(alias=labeling_protocol.IMAGE_FIELD_NAME)]
_Threshold = Annotated[
    float, Form(alias=labeling_protocol.THRESHOLD_FIELD_NAME, ge=0, le=1, allow_inf_nan=False)
]


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
        return PredictionsResponse(
            model_id=labeling_model.model_id,
            predictions=[_to_wire(prediction=prediction) for prediction in predictions],
        )

    return frozenset({labeling_protocol.LABELING_PREDICT_PATH})


def _decode(file: UploadFile) -> Image:
    """Read the uploaded file as an RGB image, or answer 422 if it is not an image."""
    data = file.file.read()
    file.file.close()
    try:
        with PILImage.open(io.BytesIO(data)) as image_file:
            return image_file.convert("RGB")
    except (UnidentifiedImageError, OSError) as error:
        raise HTTPException(
            status_code=labeling_protocol.STATUS_UNUSABLE_INPUT,
            detail="The image cannot be decoded.",
        ) from error


def _predict(
    labeling_model: LabelingModel, image: Image, threshold: float
) -> list[PredictedAnnotation]:
    """Run the model. The error of a model becomes a ``LabelingModelError``.

    The message names the class alone, because the text of an exception can hold the
    input that it failed on. The traceback goes to the log.
    """
    try:
        return labeling_model.predict(image=image, threshold=threshold)
    except Exception as error:
        logger.exception("The labeling model failed.")
        raise LabelingModelError(
            f"The labeling model raised {type(error).__name__}. See the server log."
        ) from error


def _to_wire(prediction: PredictedAnnotation) -> WirePrediction:
    """Convert one prediction, and name the rule that a broken one breaks."""
    try:
        return labeling_protocol.to_wire_prediction(prediction=prediction)
    except ValidationError as error:
        raise LabelingModelError(
            "The labeling model returned a prediction that is not valid: "
            f"{validation.name_broken_rules(error)}"
        ) from error
    except (ValueError, TypeError, AttributeError) as error:
        raise LabelingModelError(
            f"The labeling model returned a prediction that is not valid: {error}"
        ) from error
