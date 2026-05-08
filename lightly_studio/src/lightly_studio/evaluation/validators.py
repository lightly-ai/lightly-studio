"""Validation helpers shared across evaluation tasks."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import aliased
from sqlmodel import Session, col, func, select

from lightly_studio.models.annotation.annotation_base import AnnotationBaseTable, AnnotationType
from lightly_studio.models.collection import SampleType
from lightly_studio.models.evaluation_run import EvaluationTaskType
from lightly_studio.models.sample import SampleTable
from lightly_studio.resolvers import collection_resolver

_TASK_TO_ANNOTATION_TYPE: dict[EvaluationTaskType, AnnotationType] = {
    EvaluationTaskType.OBJECT_DETECTION: AnnotationType.OBJECT_DETECTION,
}


def resolve_and_validate_collections(
    session: Session,
    collection_id: UUID,
    gt_collection_name: str,
    pred_collection_name: str,
    task_type: EvaluationTaskType,
) -> tuple[UUID, UUID]:
    """Resolve collection names to IDs and validate their annotation types.

    Args:
        session: Database session used by resolver calls.
        collection_id: ID of the parent collection.
        gt_collection_name: Name of the ground-truth annotation collection.
        pred_collection_name: Name of the prediction annotation collection.
        task_type: Evaluation task type; determines the expected annotation type.

    Returns:
        Tuple of (gt_collection_id, pred_collection_id).

    Raises:
        ValueError: If task_type is not supported, if either collection does not
            exist, or if a collection contains annotations of a type other than
            the type expected for task_type.
    """
    if task_type not in _TASK_TO_ANNOTATION_TYPE:
        raise ValueError(f"Unsupported evaluation task type: {task_type!r}.")
    annotation_type = _TASK_TO_ANNOTATION_TYPE[task_type]
    gt_collection_id = collection_resolver.get_by_name(
        session=session,
        parent_collection_id=collection_id,
        name=gt_collection_name,
    )
    if gt_collection_id is None:
        raise ValueError(f"Collection {gt_collection_name!r} not found.")
    pred_collection_id = collection_resolver.get_by_name(
        session=session,
        parent_collection_id=collection_id,
        name=pred_collection_name,
    )
    if pred_collection_id is None:
        raise ValueError(f"Collection {pred_collection_name!r} not found.")

    # Validate that gt and pred annotation collections have the correct sample type.
    _validate_annotation_collection(
        session=session,
        collection_id=gt_collection_id,
    )
    _validate_annotation_collection(
        session=session,
        collection_id=pred_collection_id,
    )

    # Validate that all annotations in gt and pred collections have the expected annotation type.
    _validate_collection_annotation_type(
        session=session,
        collection_id=gt_collection_id,
        expected_type=annotation_type,
    )
    _validate_collection_annotation_type(
        session=session,
        collection_id=pred_collection_id,
        expected_type=annotation_type,
    )
    return gt_collection_id, pred_collection_id


def _validate_collection_annotation_type(
    session: Session,
    collection_id: UUID,
    expected_type: AnnotationType,
) -> None:
    """Raise ValueError if any annotation in the collection differs from expected_type.

    Args:
        session: Database session.
        collection_id: ID of the annotation collection to validate.
        expected_type: The annotation type every annotation must have.

    Raises:
        ValueError: If the collection contains annotations of a type other than expected_type.
    """
    sample_alias = aliased(SampleTable)
    mismatch_count: int = session.exec(
        select(func.count())
        .select_from(AnnotationBaseTable)
        .join(sample_alias, AnnotationBaseTable.sample)
        .where(col(sample_alias.collection_id) == collection_id)
        .where(col(AnnotationBaseTable.annotation_type) != expected_type)
    ).one()
    if mismatch_count > 0:
        raise ValueError(
            f"Collection {collection_id} contains annotations of types other than "
            f"{expected_type.value!r}."
        )


def _validate_annotation_collection(session: Session, collection_id: UUID) -> None:
    collection = collection_resolver.get_by_id(session=session, collection_id=collection_id)
    if collection is None:
        raise ValueError(f"Collection with id {collection_id} not found.")
    details = collection_resolver.get_collection_details(session=session, collection=collection)
    if details.sample_type != SampleType.ANNOTATION:
        raise ValueError(
            f"Collection with id {collection_id} has "
            f"sample type '{details.sample_type.value}', "
            f"expected '{SampleType.ANNOTATION.value}'."
        )
