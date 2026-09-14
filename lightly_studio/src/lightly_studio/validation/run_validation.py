"""Run object-detection annotation integrity checks and build a report.

The read path reuses the evaluation helpers: the source name is resolved and
validated as an object-detection collection, the annotations are eager-loaded with
their box details, and the image sizes come from the image resolver.
"""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from sqlmodel import Session

from lightly_studio.evaluation import validators
from lightly_studio.evaluation.object_detection_metric import BoundingBox
from lightly_studio.models.annotation.annotation_base import AnnotationBaseTable
from lightly_studio.models.evaluation_run import EvaluationTaskType
from lightly_studio.models.validation_report import BoxIssue, ValidationReport
from lightly_studio.resolvers import annotation_resolver, image_resolver
from lightly_studio.validation import box_checks

_TASK_TYPE = EvaluationTaskType.OBJECT_DETECTION


def validate_object_detection(
    session: Session,
    collection_id: UUID,
    annotation_source: str,
    sample_ids: Sequence[UUID],
) -> ValidationReport:
    """Check a dataset's object-detection annotations for integrity problems.

    Args:
        session: Database session used by resolver calls.
        collection_id: ID of the dataset's root collection.
        annotation_source: Name of the annotation source to check.
        sample_ids: IDs of the image samples to check.

    Returns:
        A report of the flagged annotations.

    Raises:
        ValueError: If ``annotation_source`` does not exist or is not an
            object-detection collection.
    """
    annotation_collection_id = validators.resolve_and_validate_collection(
        session=session,
        collection_id=collection_id,
        collection_name=annotation_source,
        task_type=_TASK_TYPE,
    )
    annotations = annotation_resolver.get_all_by_collection_id_and_parent_sample_ids(
        session=session,
        parent_sample_ids=list(sample_ids),
        annotation_collection_id=annotation_collection_id,
        annotation_type=validators.get_annotation_type_for_task(_TASK_TYPE),
    )
    boxes_by_image = _boxes_by_image(annotations)
    image_by_id = {
        image.sample_id: image
        for image in image_resolver.get_many_by_id(session=session, sample_ids=list(boxes_by_image))
    }

    degenerate_boxes: list[BoxIssue] = []
    out_of_bounds_boxes: list[BoxIssue] = []
    for image_sample_id, boxes in boxes_by_image.items():
        degenerate_boxes.extend(
            BoxIssue(sample_id=image_sample_id, annotation_id=annotation_id)
            for annotation_id in box_checks.find_degenerate_boxes(boxes)
        )
        # The bounds check needs the image size; skip if the image row is missing.
        image = image_by_id.get(image_sample_id)
        if image is not None:
            out_of_bounds_boxes.extend(
                BoxIssue(sample_id=image_sample_id, annotation_id=annotation_id)
                for annotation_id in box_checks.find_out_of_bounds_boxes(
                    boxes, image_width=image.width, image_height=image.height
                )
            )
    return ValidationReport(
        degenerate_boxes=degenerate_boxes,
        out_of_bounds_boxes=out_of_bounds_boxes,
    )


def _boxes_by_image(
    annotations: Sequence[AnnotationBaseTable],
) -> dict[UUID, list[BoundingBox]]:
    """Group object-detection annotations into bounding boxes per parent image."""
    boxes_by_image: dict[UUID, list[BoundingBox]] = {}
    for annotation in annotations:
        details = annotation.object_detection_details
        if details is None:
            continue
        boxes_by_image.setdefault(annotation.parent_sample_id, []).append(
            BoundingBox(
                annotation_id=annotation.sample_id,
                x=details.x,
                y=details.y,
                width=details.width,
                height=details.height,
                label_id=annotation.annotation_label_id,
                confidence=annotation.confidence,
            )
        )
    return boxes_by_image
