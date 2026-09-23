"""Tests for updating segmentation mask of annotation segmentation mask."""

from sqlmodel import Session

from lightly_studio.models.annotation.annotation_base import (
    AnnotationCreate,
    AnnotationType,
)
from lightly_studio.models.collection import CollectionCreate, SampleType
from lightly_studio.models.evaluation_run import EvaluationRunCreate, EvaluationTaskType
from lightly_studio.resolvers import (
    annotation_resolver,
    collection_resolver,
    evaluation_run_resolver,
)
from lightly_studio.services import annotations_service
from tests.helpers_resolvers import (
    create_annotation,
    create_annotation_label,
    create_collection,
    create_image,
)


def test_update_segmentation_mask(db_session: Session) -> None:
    collection = create_collection(session=db_session, sample_type=SampleType.IMAGE)
    collection_id = collection.collection_id

    car_label = create_annotation_label(
        session=db_session,
        root_collection_id=collection_id,
        label_name="car",
    )

    image = create_image(
        session=db_session,
        collection_id=collection_id,
        file_path_abs="/path/to/sample2.png",
    )

    annotation_id = annotation_resolver.create_many(
        session=db_session,
        parent_collection_id=collection_id,
        annotations=[
            AnnotationCreate(
                parent_sample_id=image.sample_id,
                annotation_label_id=car_label.annotation_label_id,
                annotation_type=AnnotationType.SEGMENTATION_MASK,
                x=50,
                y=50,
                width=20,
                height=20,
                segmentation_mask=[0, 2, 4, 6, 8],
            )
        ],
    )[0]

    annotation = annotations_service.update_segmentation_mask(
        session=db_session, annotation_id=annotation_id, segmentation_mask=[1, 2, 3, 4]
    )

    assert annotation.sample_id == annotation_id
    assert annotation.segmentation_details is not None
    assert annotation.segmentation_details.segmentation_mask == [1, 2, 3, 4]


def test_update_segmentation_mask__marks_evaluation_run_stale(db_session: Session) -> None:
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
        annotation_type=AnnotationType.SEGMENTATION_MASK,
        annotation_data={"segmentation_mask": [0, 1, 2]},
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

    annotations_service.update_segmentation_mask(
        session=db_session,
        annotation_id=annotation.sample_id,
        segmentation_mask=[1, 2, 3, 4],
    )

    refreshed = evaluation_run_resolver.get_by_id(session=db_session, evaluation_id=run.id)
    assert refreshed is not None
    assert refreshed.stale_since is not None
