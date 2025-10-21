from __future__ import annotations

from unittest.mock import patch
from uuid import UUID

from fastapi.testclient import TestClient
from pytest_mock import MockerFixture

from lightly_studio.api.routes.api.status import HTTP_STATUS_OK
from lightly_studio.services.annotations_service.update_annotation import AnnotationUpdate
from tests.conftest import AnnotationsTestData


def test_update_annotations_labels(
    mocker: MockerFixture,
    dataset_id: UUID,
    test_client: TestClient,
    annotations_test_data: AnnotationsTestData,
) -> None:
    annotation = annotations_test_data.annotations[1]
    annotation_id = annotation.annotation_id
    label = annotations_test_data.annotation_labels[1]

    with patch(
        "lightly_studio.services.annotations_service.update_annotations"
    ) as mock_update_annotations:
        mock_update_annotations.return_value = [annotation]
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

        # Verify the spy was called with annotation_update
        mock_update_annotations.assert_called_once_with(
            session=mocker.ANY,
            annotation_updates=[
                AnnotationUpdate(
                    dataset_id=dataset_id,
                    annotation_id=annotation_id,
                    label_name=label.annotation_label_name,
                )
            ],
        )

        assert response.status_code == HTTP_STATUS_OK
        result = response.json()
        assert result[0]["annotation_id"] == str(annotation.annotation_id)
        assert result[0]["annotation_label_id"] == str(label.annotation_label_id)
