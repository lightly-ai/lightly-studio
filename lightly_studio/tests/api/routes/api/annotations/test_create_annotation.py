from __future__ import annotations

from uuid import UUID

from fastapi.testclient import TestClient
from pytest_mock import MockerFixture

from lightly_studio.api.routes.api.status import HTTP_STATUS_OK
from lightly_studio.models.annotation.annotation_base import AnnotationType, AnnotationView
from lightly_studio.models.annotation.object_detection import ObjectDetectionAnnotationView
from lightly_studio.models.annotation.segmentation import (
    SegmentationAnnotationView,
)
from lightly_studio.models.annotation.semantic_segmentation import (
    SemanticSegmentationAnnotationView,
)
from lightly_studio.models.annotation_label import AnnotationLabelTable
from lightly_studio.models.collection import CollectionTable
from lightly_studio.models.image import ImageTable
from lightly_studio.services import annotations_service
from lightly_studio.services.annotations_service.create_annotation import AnnotationCreateParams


def test_create_annotation_object_detection(
    mocker: MockerFixture,
    collection: CollectionTable,
    test_client: TestClient,
    samples: list[ImageTable],
    annotation_labels: list[AnnotationLabelTable],
) -> None:
    expected_label = annotation_labels[0]
    parent_sample_id = samples[0].sample_id

    spy_create_annotation = mocker.spy(annotations_service, "create_annotation")
    route = f"/api/collections/{collection.collection_id!s}/annotations"

    response = test_client.post(
        route,
        json={
            "annotation_label_id": str(expected_label.annotation_label_id),
            "annotation_type": AnnotationType.OBJECT_DETECTION,
            "collection_id": str(collection.collection_id),
            "parent_sample_id": str(parent_sample_id),
            "x": 10,
            "y": 20,
            "width": 30,
            "height": 40,
        },
    )

    spy_create_annotation.assert_called_once_with(
        session=mocker.ANY,
        annotation=AnnotationCreateParams.model_validate(
            {
                "annotation_label_id": str(expected_label.annotation_label_id),
                "annotation_type": AnnotationType.OBJECT_DETECTION,
                "collection_id": str(collection.collection_id),
                "parent_sample_id": str(parent_sample_id),
                "x": 10,
                "y": 20,
                "width": 30,
                "height": 40,
            }
        ),
    )

    assert response.status_code == HTTP_STATUS_OK
    result = AnnotationView(**response.json())

    assert result == AnnotationView(
        annotation_type=AnnotationType.OBJECT_DETECTION,
        sample_id=result.sample_id,
        parent_sample_id=UUID(str(parent_sample_id)),
        annotation_label=AnnotationView.AnnotationLabel.model_validate(expected_label),
        created_at=result.created_at,
        object_detection_details=ObjectDetectionAnnotationView(
            x=10,
            y=20,
            width=30,
            height=40,
        ),
        tags=[],
    )


def test_create_annotation_instance_segmentation(
    mocker: MockerFixture,
    collection: CollectionTable,
    test_client: TestClient,
    samples: list[ImageTable],
    annotation_labels: list[AnnotationLabelTable],
) -> None:
    expected_label = annotation_labels[0]
    parent_sample_id = samples[0].sample_id

    spy_create_annotation = mocker.spy(annotations_service, "create_annotation")
    route = f"/api/collections/{collection.collection_id!s}/annotations"

    response = test_client.post(
        route,
        json={
            "annotation_label_id": str(expected_label.annotation_label_id),
            "annotation_type": AnnotationType.INSTANCE_SEGMENTATION,
            "collection_id": str(collection.collection_id),
            "parent_sample_id": str(parent_sample_id),
            "x": 10,
            "y": 20,
            "width": 30,
            "height": 40,
            "segmentation_mask": [0, 1, 1, 0, 0, 1],
        },
    )

    spy_create_annotation.assert_called_once_with(
        session=mocker.ANY,
        annotation=AnnotationCreateParams.model_validate(
            {
                "annotation_label_id": str(expected_label.annotation_label_id),
                "annotation_type": AnnotationType.INSTANCE_SEGMENTATION,
                "collection_id": str(collection.collection_id),
                "parent_sample_id": str(parent_sample_id),
                "x": 10,
                "y": 20,
                "width": 30,
                "height": 40,
                "segmentation_mask": [0, 1, 1, 0, 0, 1],
            }
        ),
    )

    assert response.status_code == HTTP_STATUS_OK
    result = AnnotationView(**response.json())

    assert result == AnnotationView(
        annotation_type=AnnotationType.INSTANCE_SEGMENTATION,
        sample_id=result.sample_id,
        parent_sample_id=UUID(str(parent_sample_id)),
        annotation_label=AnnotationView.AnnotationLabel.model_validate(expected_label),
        created_at=result.created_at,
        segmentation_details=SegmentationAnnotationView(
            x=10,
            y=20,
            width=30,
            height=40,
            segmentation_mask=[0, 1, 1, 0, 0, 1],
        ),
        tags=[],
    )


def test_create_annotation_semantic_segmentation(
    mocker: MockerFixture,
    collection: CollectionTable,
    test_client: TestClient,
    samples: list[ImageTable],
    annotation_labels: list[AnnotationLabelTable],
) -> None:
    expected_label = annotation_labels[0]
    parent_sample_id = samples[0].sample_id

    spy_create_annotation = mocker.spy(annotations_service, "create_annotation")
    route = f"/api/collections/{collection.collection_id!s}/annotations"

    response = test_client.post(
        route,
        json={
            "annotation_label_id": str(expected_label.annotation_label_id),
            "annotation_type": AnnotationType.SEMANTIC_SEGMENTATION,
            "collection_id": str(collection.collection_id),
            "parent_sample_id": str(parent_sample_id),
            "segmentation_mask": [0, 1, 1, 0, 0, 1],
        },
    )

    spy_create_annotation.assert_called_once_with(
        session=mocker.ANY,
        annotation=AnnotationCreateParams.model_validate(
            {
                "annotation_label_id": str(expected_label.annotation_label_id),
                "annotation_type": AnnotationType.SEMANTIC_SEGMENTATION,
                "collection_id": str(collection.collection_id),
                "parent_sample_id": str(parent_sample_id),
                "segmentation_mask": [0, 1, 1, 0, 0, 1],
            }
        ),
    )

    assert response.status_code == HTTP_STATUS_OK
    result = AnnotationView(**response.json())

    assert result == AnnotationView(
        annotation_type=AnnotationType.SEMANTIC_SEGMENTATION,
        sample_id=result.sample_id,
        parent_sample_id=UUID(str(parent_sample_id)),
        annotation_label=AnnotationView.AnnotationLabel.model_validate(expected_label),
        created_at=result.created_at,
        semantic_segmentation_details=SemanticSegmentationAnnotationView(
            segmentation_mask=[0, 1, 1, 0, 0, 1],
        ),
        tags=[],
    )


def test_create_annotation_classification(
    mocker: MockerFixture,
    collection: CollectionTable,
    test_client: TestClient,
    samples: list[ImageTable],
    annotation_labels: list[AnnotationLabelTable],
) -> None:
    expected_label = annotation_labels[0]
    parent_sample_id = samples[0].sample_id

    spy_create_annotation = mocker.spy(annotations_service, "create_annotation")
    route = f"/api/collections/{collection.collection_id!s}/annotations"

    response = test_client.post(
        route,
        json={
            "annotation_label_id": str(expected_label.annotation_label_id),
            "annotation_type": AnnotationType.CLASSIFICATION,
            "collection_id": str(collection.collection_id),
            "parent_sample_id": str(parent_sample_id),
        },
    )

    spy_create_annotation.assert_called_once_with(
        session=mocker.ANY,
        annotation=AnnotationCreateParams.model_validate(
            {
                "annotation_label_id": str(expected_label.annotation_label_id),
                "annotation_type": AnnotationType.CLASSIFICATION,
                "collection_id": str(collection.collection_id),
                "parent_sample_id": str(parent_sample_id),
            }
        ),
    )

    assert response.status_code == HTTP_STATUS_OK
    result = AnnotationView(**response.json())

    assert result == AnnotationView(
        annotation_type=AnnotationType.CLASSIFICATION,
        sample_id=result.sample_id,
        parent_sample_id=UUID(str(parent_sample_id)),
        annotation_label=AnnotationView.AnnotationLabel.model_validate(expected_label),
        created_at=result.created_at,
        tags=[],
    )
