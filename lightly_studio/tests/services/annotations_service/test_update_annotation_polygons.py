"""Tests for update_annotation_polygons."""

from sqlmodel import Session

from lightly_studio.models.annotation.annotation_base import AnnotationType
from lightly_studio.models.collection import CollectionCreate, SampleType
from lightly_studio.models.evaluation_run import EvaluationRunCreate, EvaluationTaskType
from lightly_studio.resolvers import collection_resolver, evaluation_run_resolver
from lightly_studio.services import annotations_service
from tests.helpers_resolvers import (
    create_annotation,
    create_annotation_label,
    create_collection,
    create_image,
)


def test_update_annotation_polygons__marks_evaluation_run_stale(db_session: Session) -> None:
    image_collection = create_collection(session=db_session, sample_type=SampleType.IMAGE)
    image = create_image(session=db_session, collection_id=image_collection.collection_id)
    label = create_annotation_label(
        session=db_session,
        root_collection_id=image_collection.collection_id,
        label_name="car",
    )
    gt_collection = collection_resolver.create(
        session=db_session,
        collection=CollectionCreate(
            name="gt",
            sample_type=SampleType.ANNOTATION,
            parent_collection_id=image_collection.collection_id,
        ),
    )
    pred_collection = create_collection(
        session=db_session,
        sample_type=SampleType.ANNOTATION,
        parent_collection_id=image_collection.collection_id,
    )
    annotation = create_annotation(
        session=db_session,
        collection_id=image_collection.collection_id,
        sample_id=image.sample_id,
        annotation_label_id=label.annotation_label_id,
        annotation_type=AnnotationType.POLYGON,
        polygons=[[(0, 0), (2, 0), (2, 2)]],
        annotation_collection_name="gt",
    )
    run = evaluation_run_resolver.create(
        session=db_session,
        evaluation_run_input=EvaluationRunCreate(
            name="run",
            gt_annotation_collection_id=gt_collection.collection_id,
            pred_annotation_collection_id=pred_collection.collection_id,
            dataset_id=image_collection.dataset_id,
            task_type=EvaluationTaskType.OBJECT_DETECTION,
        ),
    )
    assert run.stale_since is None

    annotations_service.update_annotation_polygons(
        session=db_session,
        annotation_id=annotation.sample_id,
        polygons=[[(0, 0), (9, 0), (9, 7)]],
    )

    refreshed = evaluation_run_resolver.get_by_id(session=db_session, evaluation_id=run.id)
    assert refreshed is not None
    assert refreshed.stale_since is not None
