from __future__ import annotations

from uuid import UUID

from fastapi.testclient import TestClient

from lightly_studio.api.routes.api.status import HTTP_STATUS_OK
from tests.conftest import AnnotationsTestData


def test_update_annotations_labels(
    dataset_id: UUID,
    test_client: TestClient,
    annotations_test_data: AnnotationsTestData,
) -> None:
    annotation = annotations_test_data.annotations[1]
    annotation_id = annotation.sample_id
    label = annotations_test_data.annotation_labels[1]

    # Update the annotation label using the service
    response = test_client.put(
        f"/api/datasets/{dataset_id!s}/annotations",
        json=[
            {
                "annotation_id": str(annotation_id),
                "dataset_id": str(dataset_id),
                "label_name": label.annotation_label_name,
            }
        ],
    )

    assert response.status_code == HTTP_STATUS_OK
    result = response.json()
    assert result[0]["sample_id"] == str(annotation.sample_id)
    assert result[0]["annotation_label_id"] == str(label.annotation_label_id)
