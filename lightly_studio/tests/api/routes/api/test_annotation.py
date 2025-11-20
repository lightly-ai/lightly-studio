from __future__ import annotations

from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from lightly_studio.api.routes.api.status import HTTP_STATUS_NOT_FOUND, HTTP_STATUS_OK
from lightly_studio.models.tag import TagTable
from tests.conftest import AnnotationsTestData


@pytest.fixture
def dataset_id(annotations_test_data: AnnotationsTestData) -> UUID:
    return annotations_test_data.datasets[0].dataset_id


@pytest.fixture
def annotations_dataset_id(annotations_test_data: AnnotationsTestData) -> UUID:
    return annotations_test_data.datasets[0].children[0].dataset_id


def test_read_annotations_first_page(
    test_client: TestClient,
    annotations_dataset_id: UUID,
) -> None:
    response = test_client.get(
        f"/api/datasets/{annotations_dataset_id}/annotations",
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
    annotations_dataset_id: UUID,
) -> None:
    response = test_client.get(
        f"/api/datasets/{annotations_dataset_id}/annotations",
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
    annotations_dataset_id: UUID,
) -> None:
    response = test_client.get(
        f"/api/datasets/{annotations_dataset_id}/annotations",
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
    annotations_dataset_id: UUID,
    test_client: TestClient,
    annotation_tags_assigned: list[TagTable],
) -> None:
    response = test_client.get(
        f"/api/datasets/{annotations_dataset_id}/annotations",
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
    annotations_dataset_id: UUID,
    test_client: TestClient,
    annotations_test_data: AnnotationsTestData,
) -> None:
    label_id = annotations_test_data.annotation_labels[0].annotation_label_id
    response = test_client.get(
        f"/api/datasets/{annotations_dataset_id}/annotations",
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
    annotation_id = annotation.annotation_id

    delete_response = test_client.delete(f"/api/datasets/{dataset_id}/annotations/{annotation_id}")
    assert delete_response.status_code == HTTP_STATUS_OK
    assert delete_response.json() == {"status": "deleted"}

    # Try to delete again and expect a 404
    delete_response = test_client.delete(f"/api/datasets/{dataset_id}/annotations/{annotation_id}")
    assert delete_response.status_code == HTTP_STATUS_NOT_FOUND
    assert delete_response.json() == {"detail": "Annotation not found"}
