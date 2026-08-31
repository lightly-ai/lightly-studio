"""Tests for annotation deletion resolver."""

from __future__ import annotations

from sqlmodel import Session

from lightly_studio.models.collection import CollectionCreate, SampleType
from lightly_studio.models.evaluation_run import EvaluationRunCreate, EvaluationTaskType
from lightly_studio.resolvers import (
    annotation_label_resolver,
    annotation_resolver,
    collection_resolver,
    evaluation_run_resolver,
)
from lightly_studio.resolvers.annotations.annotations_filter import (
    AnnotationsFilter,
)
from tests.conftest import AnnotationsTestData
from tests.helpers_resolvers import (
    create_annotation,
    create_annotation_label,
    create_collection,
    create_image,
)


def test_delete_annotations(
    db_session: Session,
    annotations_test_data: AnnotationsTestData,
) -> None:
    """Test deleting annotations."""
    dataset_id = annotations_test_data.collections[0].dataset_id
    # get a label ID to create filters
    label = annotation_label_resolver.get_by_label_name(
        session=db_session, dataset_id=dataset_id, label_name="test_label_0"
    )
    assert label is not None
    annotation_filter = AnnotationsFilter(annotation_label_ids=[label.annotation_label_id])
    filtered_annotations = annotation_resolver.get_all(
        session=db_session, filters=annotation_filter
    ).annotations
    assert len(filtered_annotations) == 6

    annotation_resolver.delete_annotations(
        session=db_session,
        annotation_label_ids=[label.annotation_label_id],
    )
    filtered_annotations = annotation_resolver.get_all(
        session=db_session, filters=annotation_filter
    ).annotations
    assert len(filtered_annotations) == 0


def test_delete_annotations__marks_evaluation_run_stale(db_session: Session) -> None:
    image_collection = create_collection(session=db_session)
    image = create_image(session=db_session, collection_id=image_collection.collection_id)
    label = create_annotation_label(
        session=db_session,
        root_collection_id=image_collection.collection_id,
        label_name="cat",
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
    create_annotation(
        session=db_session,
        collection_id=image_collection.collection_id,
        sample_id=image.sample_id,
        annotation_label_id=label.annotation_label_id,
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

    annotation_resolver.delete_annotations(
        session=db_session,
        annotation_label_ids=[label.annotation_label_id],
    )

    refreshed = evaluation_run_resolver.get_by_id(session=db_session, evaluation_id=run.id)
    assert refreshed is not None
    assert refreshed.stale_since is not None
