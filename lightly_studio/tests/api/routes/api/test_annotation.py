from __future__ import annotations

from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from lightly_studio.api.routes.api.status import HTTP_STATUS_NOT_FOUND, HTTP_STATUS_OK
from lightly_studio.models.collection import SampleType
from lightly_studio.models.tag import TagTable
from tests.conftest import AnnotationsTestData
from tests.helpers_resolvers import (
    create_annotation,
    create_annotation_label,
    create_collection,
    create_image,
)


@pytest.fixture
def dataset_id(annotations_test_data: AnnotationsTestData) -> UUID:
    return annotations_test_data.datasets[0].collection_id


@pytest.fixture
def annotation_dataset_id(annotations_test_data: AnnotationsTestData) -> UUID:
    annotation_dataset = annotations_test_data.datasets[0].children[0]
    assert annotation_dataset.sample_type == SampleType.ANNOTATION
    return annotation_dataset.collection_id


def test_read_annotations_first_page(
    test_client: TestClient,
    annotation_dataset_id: UUID,
) -> None:
    response = test_client.get(
        f"/api/datasets/{annotation_dataset_id}/annotations",
        params={
            "offset": 0,
            "limit": 100,
        },
    )

    assert response.status_code == HTTP_STATUS_OK
    result = response.json()
    assert len(result["data"]) == 8
    assert result["total_count"] == 8


def test_read_annotations_middle_page(
    test_client: TestClient,
    annotation_dataset_id: UUID,
) -> None:
    response = test_client.get(
        f"/api/datasets/{annotation_dataset_id}/annotations",
        params={
            "cursor": 4,
            "limit": 2,
        },
    )

    assert response.status_code == HTTP_STATUS_OK
    result = response.json()
    assert result["total_count"] == 8
    assert result["nextCursor"] == 6


def test_read_annotations_last_page(
    test_client: TestClient,
    annotation_dataset_id: UUID,
) -> None:
    response = test_client.get(
        f"/api/datasets/{annotation_dataset_id}/annotations",
        params={
            "cursor": 6,
            "limit": 2,
        },
    )

    assert response.status_code == HTTP_STATUS_OK
    result = response.json()
    assert result["total_count"] == 8
    assert result["nextCursor"] is None


def test_read_annotations_with_tag_ids(
    annotation_dataset_id: UUID,
    test_client: TestClient,
    annotation_tags_assigned: list[TagTable],
) -> None:
    response = test_client.get(
        f"/api/datasets/{annotation_dataset_id}/annotations",
        params={
            "offset": 0,
            "limit": 100,
            "tag_ids": [
                str(annotation_tags_assigned[0].tag_id),
                str(annotation_tags_assigned[1].tag_id),
            ],
        },
    )

    assert response.status_code == HTTP_STATUS_OK
    result = response.json()
    # The fixture assigns the first tag to two annotations and the second tag to
    # an additional three. Ordering changes should not affect the total count,
    # so we expect all five tagged annotations to be returned.
    assert len(result["data"]) == 5
    assert result["total_count"] == 5


def test_read_annotations_with_annotation_labels_ids(
    annotation_dataset_id: UUID,
    test_client: TestClient,
    annotations_test_data: AnnotationsTestData,
) -> None:
    label_id = annotations_test_data.annotation_labels[0].annotation_label_id
    response = test_client.get(
        f"/api/datasets/{annotation_dataset_id}/annotations",
        params={
            "offset": 0,
            "limit": 100,
            "annotation_label_ids": [
                str(label_id),
            ],
        },
    )

    assert response.status_code == HTTP_STATUS_OK
    result = response.json()
    expected_count = len(annotations_test_data.labeled_annotations[label_id])
    assert len(result["data"]) == expected_count
    assert result["total_count"] == expected_count


def test_delete_annotation(
    test_client: TestClient,
    dataset_id: UUID,
    annotations_test_data: AnnotationsTestData,
) -> None:
    annotation = annotations_test_data.annotations[0]
    annotation_id = annotation.sample_id

    delete_response = test_client.delete(f"/api/datasets/{dataset_id}/annotations/{annotation_id}")
    assert delete_response.status_code == HTTP_STATUS_OK
    assert delete_response.json() == {"status": "deleted"}

    # Try to delete again and expect a 404
    delete_response = test_client.delete(f"/api/datasets/{dataset_id}/annotations/{annotation_id}")
    assert delete_response.status_code == HTTP_STATUS_NOT_FOUND
    assert delete_response.json() == {"detail": "Annotation not found"}


def test_read_annotations_with_payload(
    test_client: TestClient,
    db_session: Session,
) -> None:
    dataset = create_collection(session=db_session)
    dataset_id = dataset.collection_id

    image_1 = create_image(
        session=db_session,
        collection_id=dataset_id,
        file_path_abs="/path/to/sample2.png",
    )
    image_2 = create_image(
        session=db_session,
        collection_id=dataset_id,
        file_path_abs="/path/to/sample1.png",
    )

    car_label = create_annotation_label(
        session=db_session,
        root_dataset_id=dataset_id,
        label_name="car",
    )

    airplane_label = create_annotation_label(
        session=db_session,
        root_dataset_id=dataset_id,
        label_name="airplane",
    )

    # Create annotations
    annotation_1 = create_annotation(
        session=db_session,
        sample_id=image_1.sample_id,
        annotation_label_id=car_label.annotation_label_id,
        collection_id=dataset_id,
    )
    create_annotation(
        session=db_session,
        sample_id=image_2.sample_id,
        annotation_label_id=airplane_label.annotation_label_id,
        collection_id=dataset_id,
    )

    response = test_client.get(
        f"/api/datasets/{annotation_1.sample.collection_id}/annotations/payload",
        params={
            "offset": 0,
            "limit": 1,
        },
    )

    assert response.status_code == HTTP_STATUS_OK
    result = response.json()

    assert len(result["data"]) == 1
    assert result["total_count"] == 2

    assert (
        result["data"][0]["annotation"]["annotation_label"]["annotation_label_name"]
        == airplane_label.annotation_label_name
    )

    assert result["data"][0]["parent_sample_data"]["sample_id"] == str(image_2.sample_id)


def test_get_annotation_with_payload(
    test_client: TestClient,
    db_session: Session,
) -> None:
    collection = create_collection(session=db_session)
    collection_id = collection.collection_id

    image_1 = create_image(
        session=db_session,
        collection_id=collection_id,
        file_path_abs="/path/to/sample2.png",
    )

    car_label = create_annotation_label(
        session=db_session,
        root_dataset_id=dataset_id,
        label_name="car",
    )

    annotation = create_annotation(
        session=db_session,
        sample_id=image_1.sample_id,
        annotation_label_id=car_label.annotation_label_id,
        collection_id=collection_id,
    )

    response = test_client.get(
        f"/api/datasets/{annotation.sample.collection_id}/annotations/payload/{annotation.sample_id}",
    )

    assert response.status_code == HTTP_STATUS_OK
    result = response.json()

    assert (
        result["annotation"]["annotation_label"]["annotation_label_name"]
        == car_label.annotation_label_name
    )

    assert result["parent_sample_data"]["file_path_abs"] == "/path/to/sample2.png"
    assert result["parent_sample_data"]["sample"]["sample_id"] == str(image_1.sample.sample_id)
