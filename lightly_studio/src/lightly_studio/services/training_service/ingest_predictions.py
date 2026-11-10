"""Add the predictions of a training run to an annotation source."""

from __future__ import annotations

import json
from collections.abc import Iterable
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlmodel import Session

from lightly_studio.models.annotation.annotation_base import AnnotationCreate, AnnotationType
from lightly_studio.models.annotation_label import AnnotationLabelCreate
from lightly_studio.resolvers import annotation_label_resolver, annotation_resolver


def ingest_predictions(
    session: Session,
    collection_id: UUID,
    dataset_id: UUID,
    predictions_file: Path,
    annotation_source: str,
) -> int:
    """Add the predictions of the training process to a new annotation source.

    Missing annotation classes are created. Boxes with no area are skipped.

    Args:
        session: The database session.
        collection_id: The image collection of the predicted samples.
        dataset_id: The dataset of the annotation classes.
        predictions_file: The file that the training process writes. It holds a list of
            `{"sample_id": ..., "detections": [{"class_name", "bbox_xyxy", "score"}]}`,
            with boxes in pixels.
        annotation_source: The name of the annotation source to create.

    Returns:
        The number of added annotations.
    """
    predictions = json.loads(predictions_file.read_text(encoding="utf-8"))
    class_names = {d["class_name"] for p in predictions for d in p["detections"]}
    label_ids = _get_or_create_label_ids(
        session=session, dataset_id=dataset_id, class_names=class_names
    )
    candidates = (
        _to_annotation_create(
            sample_id=UUID(prediction["sample_id"]), detection=detection, label_ids=label_ids
        )
        for prediction in predictions
        for detection in prediction["detections"]
    )
    annotations = [annotation for annotation in candidates if annotation is not None]
    annotation_resolver.create_many(
        session=session,
        parent_collection_id=collection_id,
        annotations=annotations,
        collection_name=annotation_source,
    )
    return len(annotations)


def _to_annotation_create(
    sample_id: UUID, detection: dict[str, Any], label_ids: dict[str, UUID]
) -> AnnotationCreate | None:
    x_min, y_min, x_max, y_max = detection["bbox_xyxy"]
    x, y = round(x_min), round(y_min)
    width, height = round(x_max) - x, round(y_max) - y
    if width < 1 or height < 1:
        return None
    return AnnotationCreate(
        annotation_label_id=label_ids[detection["class_name"]],
        annotation_type=AnnotationType.OBJECT_DETECTION,
        parent_sample_id=sample_id,
        x=x,
        y=y,
        width=width,
        height=height,
        confidence=detection["score"],
    )


def _get_or_create_label_ids(
    session: Session, dataset_id: UUID, class_names: Iterable[str]
) -> dict[str, UUID]:
    label_ids: dict[str, UUID] = {}
    for class_name in class_names:
        label = annotation_label_resolver.get_by_label_name(
            session=session, dataset_id=dataset_id, label_name=class_name
        )
        if label is None:
            label = annotation_label_resolver.create(
                session=session,
                label=AnnotationLabelCreate(
                    dataset_id=dataset_id, annotation_label_name=class_name
                ),
            )
        label_ids[class_name] = label.annotation_label_id
    return label_ids
