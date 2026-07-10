from uuid import UUID

import pytest
from sqlmodel import Session

from lightly_studio import AnnotationType
from lightly_studio.models.evaluation_annotation_metric import EvaluationAnnotationMetricCreate
from lightly_studio.models.evaluation_sample_metric import EvaluationSampleMetricCreate
from lightly_studio.resolvers import (
    annotation_resolver,
    evaluation_annotation_metric_resolver,
    evaluation_sample_metric_resolver,
)
from lightly_studio.resolvers.annotation_resolver.update_bounding_box import (
    BoundingBoxCoordinates,
)
from tests.conftest import AnnotationsTestData
from tests.helpers_resolvers import (
    create_annotation,
    create_annotation_label,
    create_collection,
    create_image,
    get_annotation_by_type,
)
from tests.resolvers.evaluation_sample_metric_resolver import (
    helpers as evaluation_sample_metric_helpers,
)


def test_update_bounding_box__object_detection(
    db_session: Session,
    annotations_test_data: AnnotationsTestData,  # noqa: ARG001
) -> None:
    """Test updating bounding box coordinates for object detection annotation."""
    annotations = annotation_resolver.get_all(db_session).annotations
    obj_det_annotation = get_annotation_by_type(
        annotations=annotations, annotation_type=AnnotationType.OBJECT_DETECTION
    )
    annotation_id = obj_det_annotation.sample_id

    new_coordinates = BoundingBoxCoordinates(
        x=11,
        y=22,
        width=111,
        height=222,
    )

    # Check if the updated annotation is properly returned.
    updated_annotation = annotation_resolver.update_bounding_box(
        db_session, annotation_id, new_coordinates
    )
    assert updated_annotation.object_detection_details is not None
    assert updated_annotation.object_detection_details.x == 11
    assert updated_annotation.object_detection_details.y == 22
    assert updated_annotation.object_detection_details.width == 111
    assert updated_annotation.object_detection_details.height == 222

    # Verify the change persisted in the database.
    updated_obj_det_annotation = annotation_resolver.get_by_id(db_session, annotation_id)
    assert updated_obj_det_annotation is not None
    assert updated_obj_det_annotation.object_detection_details is not None
    assert updated_obj_det_annotation.object_detection_details.x == 11
    assert updated_obj_det_annotation.object_detection_details.y == 22
    assert updated_obj_det_annotation.object_detection_details.width == 111
    assert updated_obj_det_annotation.object_detection_details.height == 222


def test_update_bounding_box__segmentation_mask(
    db_session: Session,
    annotations_test_data: AnnotationsTestData,  # noqa: ARG001
) -> None:
    """Test updating bounding box coordinates for segmentation mask annotation."""
    annotations = annotation_resolver.get_all(db_session).annotations
    inst_segm_annotation = get_annotation_by_type(
        annotations=annotations, annotation_type=AnnotationType.SEGMENTATION_MASK
    )
    annotation_id = inst_segm_annotation.sample_id

    new_coordinates = BoundingBoxCoordinates(
        x=11,
        y=22,
        width=111,
        height=222,
    )

    # Check if the updated annotation is properly returned.
    updated_annotation = annotation_resolver.update_bounding_box(
        db_session, annotation_id, new_coordinates
    )
    assert updated_annotation.segmentation_details is not None
    assert updated_annotation.segmentation_details.x == 11
    assert updated_annotation.segmentation_details.y == 22
    assert updated_annotation.segmentation_details.width == 111
    assert updated_annotation.segmentation_details.height == 222

    # Verify the change persisted in the database.
    updated_inst_segm_annotation = annotation_resolver.get_by_id(db_session, annotation_id)
    assert updated_inst_segm_annotation is not None
    assert updated_inst_segm_annotation.segmentation_details is not None
    assert updated_inst_segm_annotation.segmentation_details.x == 11
    assert updated_inst_segm_annotation.segmentation_details.y == 22
    assert updated_inst_segm_annotation.segmentation_details.width == 111
    assert updated_inst_segm_annotation.segmentation_details.height == 222


def test_update_bounding_box__classification(
    db_session: Session,
    annotations_test_data: AnnotationsTestData,  # noqa: ARG001
) -> None:
    """Test updating bounding box coordinates for classification annotation."""
    annotations = annotation_resolver.get_all(db_session).annotations
    classification_annotation = annotations[0]
    annotation_id = classification_annotation.sample_id

    new_coordinates = BoundingBoxCoordinates(
        x=10,
        y=20,
        width=100,
        height=200,
    )

    with pytest.raises(ValueError, match=r"Annotation type does not support bounding boxes."):
        annotation_resolver.update_bounding_box(db_session, annotation_id, new_coordinates)


def test_update_bounding_box__invalid_annotation_id(
    db_session: Session,
) -> None:
    """Test updating bounding box with an invalid annotation ID."""
    invalid_annotation_id = UUID("00000000-0000-0000-0000-000000000000")
    new_coordinates = BoundingBoxCoordinates(
        x=10,
        y=20,
        width=100,
        height=200,
    )

    with pytest.raises(ValueError, match=f"Annotation with ID {invalid_annotation_id} not found."):
        annotation_resolver.update_bounding_box(db_session, invalid_annotation_id, new_coordinates)


def test_update_bounding_box__deletes_evaluation_metrics(
    db_session: Session,
) -> None:
    """Test bounding box updates remove invalidated evaluation annotation and sample metrics."""
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
    )
    gt_annotation = create_annotation(
        session=db_session,
        collection_id=collection_id,
        sample_id=image.sample_id,
        annotation_label_id=label.annotation_label_id,
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

    annotation_resolver.update_bounding_box(
        db_session,
        gt_annotation.sample_id,
        BoundingBoxCoordinates(x=11, y=22, width=111, height=222),
    )

    annotation_metrics = evaluation_annotation_metric_resolver.get_all_by_evaluation_run_id(
        session=db_session,
        evaluation_run_id=run.id,
    )
    sample_metrics = evaluation_sample_metric_resolver.get_all_by_evaluation_run_id(
        session=db_session,
        evaluation_run_id=run.id,
    )

    assert annotation_metrics == []
    assert sample_metrics == []
