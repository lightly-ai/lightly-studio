"""Annotation class predictions route."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Path
from pydantic import BaseModel

from lightly_studio.database.db_manager import SessionDep
from lightly_studio.errors import NotFoundError
from lightly_studio.models.annotation.annotation_base import CROPPABLE_ANNOTATION_TYPES
from lightly_studio.resolvers import annotation_resolver
from lightly_studio.services import annotations_service

predict_annotation_classes_router = APIRouter()


class AnnotationClassPredictionView(BaseModel):
    """Predicted score of one class for an annotation."""

    annotation_label_id: UUID
    label_name: str
    score: float


@predict_annotation_classes_router.post(
    "/annotations/{annotation_id}/class_predictions",
    response_model=list[AnnotationClassPredictionView],
)
def predict_annotation_classes(
    collection_id: Annotated[
        UUID, Path(title="collection Id", description="The ID of the collection")
    ],
    annotation_id: Annotated[
        UUID, Path(title="annotation Id", description="The ID of the annotation")
    ],
    session: SessionDep,
) -> list[AnnotationClassPredictionView]:
    """Predict the class of a bounding box or segmentation mask from its crop.

    Returns every class of the dataset, highest score first. The list is empty when the crop
    cannot be embedded.
    """
    del collection_id
    annotation = annotation_resolver.get_by_id(session=session, annotation_id=annotation_id)
    if annotation is None:
        raise NotFoundError(f"Annotation {annotation_id} not found.")
    if annotation.annotation_type not in CROPPABLE_ANNOTATION_TYPES:
        raise ValueError(
            f"Class prediction needs a bounding box or a segmentation mask, "
            f"not a {annotation.annotation_type.value} annotation."
        )
    predictions = annotations_service.predict_annotation_classes(
        session=session, annotation=annotation
    )
    return [
        AnnotationClassPredictionView(
            annotation_label_id=prediction.annotation_label_id,
            label_name=prediction.label_name,
            score=prediction.score,
        )
        for prediction in predictions
    ]
