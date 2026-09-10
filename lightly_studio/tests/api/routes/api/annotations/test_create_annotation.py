from __future__ import annotations

from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from pytest_mock import MockerFixture
from sqlmodel import Session, select

from lightly_studio.api.routes.api.status import (
    HTTP_STATUS_CREATED,
    HTTP_STATUS_NOT_FOUND,
    HTTP_STATUS_OK,
)
from lightly_studio.models.annotation.annotation_base import (
    AnnotationBaseTable,
    AnnotationType,
    AnnotationView,
)
from lightly_studio.models.annotation.object_detection import ObjectDetectionAnnotationView
from lightly_studio.models.annotation.segmentation import (
    SegmentationAnnotationView,
)
from lightly_studio.models.annotation_label import AnnotationLabelTable
from lightly_studio.models.collection import CollectionTable
from lightly_studio.models.image import ImageTable
from lightly_studio.services import annotations_service
from lightly_studio.services.annotations_service.create_annotation import AnnotationCreateParams
from tests.helpers_resolvers import ImageStub, create_collection, create_images


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
        annotation_collection_id=result.annotation_collection_id,
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


def test_create_annotation_segmentation_mask(
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
            "annotation_type": AnnotationType.SEGMENTATION_MASK,
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
                "annotation_type": AnnotationType.SEGMENTATION_MASK,
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
        annotation_type=AnnotationType.SEGMENTATION_MASK,
        sample_id=result.sample_id,
        annotation_collection_id=result.annotation_collection_id,
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
        annotation_collection_id=result.annotation_collection_id,
        parent_sample_id=UUID(str(parent_sample_id)),
        annotation_label=AnnotationView.AnnotationLabel.model_validate(expected_label),
        created_at=result.created_at,
        tags=[],
    )


def test_create_annotation_with_collection_name(
    mocker: MockerFixture,
    collection: CollectionTable,
    test_client: TestClient,
    samples: list[ImageTable],
    annotation_labels: list[AnnotationLabelTable],
) -> None:
    expected_label = annotation_labels[0]
    parent_sample_id = samples[0].sample_id
    collection_name = "test-collection"

    spy_create_annotation = mocker.spy(annotations_service, "create_annotation")
    route = f"/api/collections/{collection.collection_id!s}/annotations"

    response = test_client.post(
        route,
        json={
            "annotation_label_id": str(expected_label.annotation_label_id),
            "annotation_type": AnnotationType.CLASSIFICATION,
            "annotation_collection_name": collection_name,
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
                "annotation_collection_name": collection_name,
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
        annotation_collection_id=result.annotation_collection_id,
        parent_sample_id=UUID(str(parent_sample_id)),
        annotation_label=AnnotationView.AnnotationLabel.model_validate(expected_label),
        created_at=result.created_at,
        tags=[],
    )


def test_bulk_create_classifications_route__creates_classifications(
    db_session: Session,
    test_client: TestClient,
) -> None:
    collection = create_collection(session=db_session)
    images = create_images(
        db_session=db_session,
        collection_id=collection.collection_id,
        images=[ImageStub(path="a.png"), ImageStub(path="b.png")],
    )

    response = test_client.post(
        f"/api/collections/{collection.collection_id}/annotations/classifications/bulk_create",
        json={
            "sample_ids": [str(image.sample_id) for image in images],
            "class_name": "dog",
            "annotation_collection_name": "ground_truth",
        },
    )

    assert response.status_code == HTTP_STATUS_CREATED
    assert response.json()["created_count"] == 2
    assert response.json()["skipped_count"] == 0
    assert {
        annotation.annotation_type
        for annotation in db_session.exec(select(AnnotationBaseTable)).all()
    } == {AnnotationType.CLASSIFICATION}


def test_bulk_create_classifications_by_filter_route__skips_existing(
    db_session: Session,
    test_client: TestClient,
) -> None:
    collection = create_collection(session=db_session)
    create_images(
        db_session=db_session,
        collection_id=collection.collection_id,
        images=[ImageStub(path="wide.png", width=1920), ImageStub(path="narrow.png", width=10)],
    )
    url = (
        f"/api/collections/{collection.collection_id}"
        "/annotations/classifications/bulk_create_by_filter"
    )
    body = {
        "filter": {"filter_type": "image", "width": {"min": 100}},
        "class_name": "dog",
        "annotation_collection_name": "ground_truth",
    }

    first = test_client.post(url, json=body)
    second = test_client.post(url, json=body)

    assert first.status_code == HTTP_STATUS_CREATED
    assert second.status_code == HTTP_STATUS_CREATED
    assert first.json()["created_count"] == 1
    assert second.json()["created_count"] == 0
    assert second.json()["skipped_count"] == 1


def test_bulk_create_classifications_route__unknown_collection(
    test_client: TestClient,
) -> None:
    response = test_client.post(
        f"/api/collections/{uuid4()}/annotations/classifications/bulk_create",
        json={"sample_ids": [], "class_name": "dog"},
    )

    assert response.status_code == HTTP_STATUS_NOT_FOUND
