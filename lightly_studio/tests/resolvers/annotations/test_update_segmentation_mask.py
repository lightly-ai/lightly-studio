"""Tests for updating segmentation mask of annotation segmentation mask."""

import pytest
from sqlmodel import Session

from lightly_studio.models.annotation.annotation_base import (
    AnnotationCreate,
    AnnotationType,
)
from lightly_studio.models.collection import SampleType
from lightly_studio.models.evaluation_annotation_metric import EvaluationAnnotationMetricCreate
from lightly_studio.models.evaluation_sample_metric import EvaluationSampleMetricCreate
from lightly_studio.resolvers import (
    annotation_resolver,
    evaluation_annotation_metric_resolver,
    evaluation_sample_metric_resolver,
)
from tests.helpers_resolvers import (
    create_annotation,
    create_annotation_label,
    create_collection,
    create_image,
)
from tests.resolvers.evaluation_sample_metric_resolver import (
    helpers as evaluation_sample_metric_helpers,
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

    annotation = annotation_resolver.update_segmentation_mask(
        session=db_session, annotation_id=annotation_id, segmentation_mask=[1, 2, 3, 4]
    )

    assert annotation.sample_id == annotation_id
    assert annotation.segmentation_details is not None
    assert annotation.segmentation_details.segmentation_mask == [1, 2, 3, 4]


def test_update_segmentation_mask__unsupported_annotation_type(db_session: Session) -> None:
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
                annotation_type=AnnotationType.OBJECT_DETECTION,
                x=50,
                y=50,
                width=20,
                height=20,
            )
        ],
    )[0]

    with pytest.raises(ValueError, match=r"Annotation type does not support segmentation mask."):
        annotation_resolver.update_segmentation_mask(
            session=db_session, annotation_id=annotation_id, segmentation_mask=[1, 2, 3, 4]
        )


def test_update_segmentation_mask__deletes_evaluation_metrics(db_session: Session) -> None:
    """Test mask updates remove invalidated evaluation annotation and sample metrics."""
    dataset = create_collection(session=db_session)
    run = evaluation_sample_metric_helpers.create_run(
        session=db_session,
        collection_id=dataset.collection_id,
    )
    image = create_image(session=db_session, collection_id=dataset.collection_id)
    collection_id = dataset.collection_id
    label = create_annotation_label(session=db_session, root_collection_id=collection_id)
    pred_annotation = create_annotation(
        session=db_session,
        collection_id=collection_id,
        sample_id=image.sample_id,
        annotation_label_id=label.annotation_label_id,
        annotation_type=AnnotationType.SEGMENTATION_MASK,
        annotation_data={"segmentation_mask": [0, 2, 4]},
    )
    gt_annotation = create_annotation(
        session=db_session,
        collection_id=collection_id,
        sample_id=image.sample_id,
        annotation_label_id=label.annotation_label_id,
        annotation_type=AnnotationType.SEGMENTATION_MASK,
        annotation_data={"segmentation_mask": [0, 2, 4]},
    )
    evaluation_annotation_metric_resolver.create_many(
        session=db_session,
        records=[
            EvaluationAnnotationMetricCreate(
                evaluation_run_id=run.id,
                sample_id=image.sample_id,
                pred_annotation_id=pred_annotation.sample_id,
                gt_annotation_id=gt_annotation.sample_id,
                metric_name="iou",
                value=0.75,
            )
        ],
    )
    evaluation_sample_metric_resolver.create_many(
        session=db_session,
        records=[
            EvaluationSampleMetricCreate(
                evaluation_run_id=run.id,
                sample_id=image.sample_id,
                metric_name="score",
                value=0.5,
            )
        ],
    )

    updated_annotation = annotation_resolver.update_segmentation_mask(
        session=db_session,
        annotation_id=gt_annotation.sample_id,
        segmentation_mask=[1, 2, 3, 4],
    )

    annotation_metrics = evaluation_annotation_metric_resolver.get_all_by_evaluation_run_id(
        session=db_session,
        evaluation_run_id=run.id,
    )
    sample_metrics = evaluation_sample_metric_resolver.get_all_by_evaluation_run_id(
        session=db_session,
        evaluation_run_id=run.id,
    )

    assert updated_annotation.segmentation_details is not None
    assert updated_annotation.segmentation_details.segmentation_mask == [1, 2, 3, 4]
    assert annotation_metrics == []
    assert sample_metrics == []
