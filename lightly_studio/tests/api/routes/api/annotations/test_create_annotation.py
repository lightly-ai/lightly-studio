from __future__ import annotations

from uuid import UUID

from fastapi.testclient import TestClient
from pytest_mock import MockerFixture

from lightly_studio.api.routes.api.status import HTTP_STATUS_OK
from lightly_studio.models.annotation.annotation_base import AnnotationType, AnnotationView
from lightly_studio.models.annotation.instance_segmentation import (
    InstanceSegmentationAnnotationView,
)
from lightly_studio.models.annotation.object_detection import ObjectDetectionAnnotationView
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
    expected_annotation_type = AnnotationType.OBJECT_DETECTION
    input_data = {
        "annotation_label_id": str(expected_label.annotation_label_id),
        "annotation_type": expected_annotation_type,
        "collection_id": str(collection.collection_id),
        "parent_sample_id": str(samples[0].sample_id),
        "x": 10,
        "y": 20,
        "width": 30,
        "height": 40,
    }

    spy_create_annotation = mocker.spy(annotations_service, "create_annotation")
    route = f"/api/collections/{collection.collection_id!s}/annotations"
    response = test_client.post(
        route,
        json=input_data,
    )

    spy_create_annotation.assert_called_once_with(
        session=mocker.ANY, annotation=AnnotationCreateParams.model_validate(input_data)
    )

    assert response.status_code == HTTP_STATUS_OK
    result = AnnotationView(**response.json())

    assert result == AnnotationView(
        annotation_type=expected_annotation_type,
        sample_id=result.sample_id,
        parent_sample_id=UUID(str(input_data["parent_sample_id"])),
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
    expected_annotation_type = AnnotationType.INSTANCE_SEGMENTATION
    input_data = {
        "annotation_label_id": str(expected_label.annotation_label_id),
        "annotation_type": expected_annotation_type,
        "collection_id": str(collection.collection_id),
        "parent_sample_id": str(samples[0].sample_id),
        "x": 10,
        "y": 20,
        "width": 30,
        "height": 40,
        "segmentation_mask": [0, 1, 1, 0, 0, 1],
    }

    spy_create_annotation = mocker.spy(annotations_service, "create_annotation")
    route = f"/api/collections/{collection.collection_id!s}/annotations"
    response = test_client.post(
        route,
        json=input_data,
    )

    spy_create_annotation.assert_called_once_with(
        session=mocker.ANY, annotation=AnnotationCreateParams.model_validate(input_data)
    )

    assert response.status_code == HTTP_STATUS_OK
    result = AnnotationView(**response.json())

    assert result == AnnotationView(
        annotation_type=expected_annotation_type,
        sample_id=result.sample_id,
        parent_sample_id=UUID(str(input_data["parent_sample_id"])),
        annotation_label=AnnotationView.AnnotationLabel.model_validate(expected_label),
        created_at=result.created_at,
        instance_segmentation_details=InstanceSegmentationAnnotationView(
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
    expected_type = AnnotationType.SEMANTIC_SEGMENTATION
    input_data = {
        "annotation_label_id": str(expected_label.annotation_label_id),
        "annotation_type": expected_type,
        "collection_id": str(collection.collection_id),
        "parent_sample_id": str(samples[0].sample_id),
        "segmentation_mask": [0, 1, 1, 0, 0, 1],
    }

    spy_create_annotation = mocker.spy(annotations_service, "create_annotation")
    route = f"/api/collections/{collection.collection_id!s}/annotations"
    response = test_client.post(
        route,
        json=input_data,
    )

    spy_create_annotation.assert_called_once_with(
        session=mocker.ANY,
        annotation=AnnotationCreateParams.model_validate(input_data),
    )

    assert response.status_code == HTTP_STATUS_OK
    result = AnnotationView(**response.json())
    assert result == AnnotationView(
        annotation_type=expected_type,
        sample_id=result.sample_id,
        parent_sample_id=UUID(str(input_data["parent_sample_id"])),
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
    expected_type = AnnotationType.CLASSIFICATION
    input_data = {
        "annotation_label_id": str(expected_label.annotation_label_id),
        "annotation_type": expected_type,
        "collection_id": str(collection.collection_id),
        "parent_sample_id": str(samples[0].sample_id),
    }

    spy_create_annotation = mocker.spy(annotations_service, "create_annotation")
    route = f"/api/collections/{collection.collection_id!s}/annotations"
    response = test_client.post(
        route,
        json=input_data,
    )

    spy_create_annotation.assert_called_once_with(
        session=mocker.ANY,
        annotation=AnnotationCreateParams.model_validate(
            input_data,
        ),
    )

    assert response.status_code == HTTP_STATUS_OK
    result = AnnotationView(**response.json())

    assert result == AnnotationView(
        annotation_type=expected_type,
        sample_id=result.sample_id,
        parent_sample_id=UUID(str(input_data["parent_sample_id"])),
        annotation_label=AnnotationView.AnnotationLabel.model_validate(expected_label),
        created_at=result.created_at,
        tags=[],
    )
