"""Shared helpers for the evaluation route tests."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlmodel import Session

from lightly_studio.models.annotation.annotation_base import AnnotationType
from lightly_studio.models.collection import CollectionTable, SampleType
from lightly_studio.models.evaluation_run import EvaluationRunTable, EvaluationTaskType
from tests.helpers_resolvers import (
    create_annotation,
    create_annotation_label,
    create_collection,
    create_image,
)


def make_evaluation_run(  # noqa: PLR0913
    *,
    run_id: UUID,
    name: str,
    config_json: dict[str, Any],
    created_at: datetime,
    gt_annotation_collection_id: UUID | None = None,
    pred_annotation_collection_id: UUID | None = None,
    task_type: EvaluationTaskType = EvaluationTaskType.OBJECT_DETECTION,
) -> EvaluationRunTable:
    return EvaluationRunTable(
        id=run_id,
        name=name,
        gt_annotation_collection_id=gt_annotation_collection_id or uuid4(),
        pred_annotation_collection_id=pred_annotation_collection_id or uuid4(),
        task_type=task_type,
        config_json=config_json,
        created_at=created_at,
    )


def create_dataset_with_annotations(
    db_session: Session,
    annotation_type: AnnotationType = AnnotationType.OBJECT_DETECTION,
    image_widths: tuple[int, ...] = (1920,),
) -> CollectionTable:
    """Create a root collection with images and 'gt'/'pred' annotation collections."""
    root = create_collection(session=db_session)
    label = create_annotation_label(session=db_session, root_collection_id=root.collection_id)
    for source_name in ("gt", "pred"):
        create_collection(
            session=db_session,
            collection_name=source_name,
            parent_collection_id=root.collection_id,
            sample_type=SampleType.ANNOTATION,
        )
    for index, width in enumerate(image_widths):
        image = create_image(
            session=db_session,
            collection_id=root.collection_id,
            file_path_abs=f"/path/to/sample_{index}.png",
            width=width,
        )
        for source_name in ("gt", "pred"):
            create_annotation(
                session=db_session,
                collection_id=root.collection_id,
                sample_id=image.sample_id,
                annotation_label_id=label.annotation_label_id,
                annotation_type=annotation_type,
                annotation_collection_name=source_name,
            )
    return root
