from __future__ import annotations

import pytest
from sqlmodel import Session

from lightly_studio.errors import AnnotationSourceInUseError
from lightly_studio.models.annotation.annotation_base import AnnotationBaseTable
from lightly_studio.models.collection import CollectionTable
from lightly_studio.models.evaluation_run import EvaluationRunCreate, EvaluationTaskType
from lightly_studio.resolvers import (
    annotation_collection_coverage_resolver,
    annotation_resolver,
    collection_resolver,
    evaluation_run_resolver,
)
from lightly_studio.services import annotation_source_service
from tests.helpers_resolvers import (
    AnnotationDetails,
    create_annotation_label,
    create_annotations,
    create_collection,
    create_image,
)


def test_rename_annotation_source(db_session: Session) -> None:
    collection = create_collection(session=db_session)
    annotation = _create_annotation(session=db_session, collection=collection, source="predictions")
    old_id = annotation.annotation_collection_id
    # An image the source covers without an annotation keeps its coverage.
    empty_image = create_image(
        session=db_session, collection_id=collection.collection_id, file_path_abs="/empty.png"
    )
    annotation_collection_coverage_resolver.add_many(
        session=db_session,
        annotation_collection_id=old_id,
        parent_sample_ids=[empty_image.sample_id],
    )

    new_id = annotation_source_service.rename_annotation_source(
        session=db_session,
        dataset_collection_id=collection.collection_id,
        annotation_source_id=old_id,
        name="model_v2",
    )

    assert collection_resolver.get_by_id(session=db_session, collection_id=old_id) is None
    renamed = collection_resolver.get_by_id(session=db_session, collection_id=new_id)
    assert renamed is not None
    assert renamed.name == "model_v2"
    moved = annotation_resolver.get_by_id(session=db_session, annotation_id=annotation.sample_id)
    assert moved is not None
    assert moved.annotation_collection_id == new_id
    assert set(
        annotation_collection_coverage_resolver.list_by_collection_id(
            session=db_session, annotation_collection_id=new_id
        )
    ) == {annotation.parent_sample_id, empty_image.sample_id}


def test_rename_annotation_source__same_name(db_session: Session) -> None:
    collection = create_collection(session=db_session)
    annotation = _create_annotation(session=db_session, collection=collection, source="predictions")

    new_id = annotation_source_service.rename_annotation_source(
        session=db_session,
        dataset_collection_id=collection.collection_id,
        annotation_source_id=annotation.annotation_collection_id,
        name="predictions",
    )

    assert new_id == annotation.annotation_collection_id


def test_rename_annotation_source__name_of_other_source(db_session: Session) -> None:
    collection = create_collection(session=db_session)
    _create_annotation(session=db_session, collection=collection, source="ground_truth")
    annotation = _create_annotation(session=db_session, collection=collection, source="predictions")

    with pytest.raises(ValueError, match="'ground_truth' already exists"):
        annotation_source_service.rename_annotation_source(
            session=db_session,
            dataset_collection_id=collection.collection_id,
            annotation_source_id=annotation.annotation_collection_id,
            name="ground_truth",
        )


def test_rename_annotation_source__used_by_evaluation_run(db_session: Session) -> None:
    collection = create_collection(session=db_session)
    gt = _create_annotation(session=db_session, collection=collection, source="ground_truth")
    pred = _create_annotation(session=db_session, collection=collection, source="predictions")
    evaluation_run_resolver.create(
        session=db_session,
        evaluation_run_input=EvaluationRunCreate(
            name="run_a",
            gt_annotation_collection_id=gt.annotation_collection_id,
            pred_annotation_collection_id=pred.annotation_collection_id,
            dataset_id=collection.dataset_id,
            task_type=EvaluationTaskType.OBJECT_DETECTION,
        ),
    )

    with pytest.raises(AnnotationSourceInUseError, match="run_a"):
        annotation_source_service.rename_annotation_source(
            session=db_session,
            dataset_collection_id=collection.collection_id,
            annotation_source_id=pred.annotation_collection_id,
            name="model_v2",
        )


def _create_annotation(
    session: Session, collection: CollectionTable, source: str
) -> AnnotationBaseTable:
    image = create_image(
        session=session, collection_id=collection.collection_id, file_path_abs=f"/{source}.png"
    )
    label = create_annotation_label(
        session=session, root_collection_id=collection.collection_id, label_name=source
    )
    return create_annotations(
        session=session,
        collection_id=collection.collection_id,
        annotations=[
            AnnotationDetails(
                sample_id=image.sample_id, annotation_label_id=label.annotation_label_id
            )
        ],
        collection_name=source,
    )[0]
