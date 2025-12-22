from __future__ import annotations

from unittest.mock import patch
from uuid import UUID

from fastapi.testclient import TestClient
from pytest_mock import MockerFixture

from lightly_studio.api.routes.api.status import HTTP_STATUS_OK
from lightly_studio.resolvers.annotation_resolver.update_bounding_box import BoundingBoxCoordinates
from lightly_studio.services.annotations_service.update_annotation import AnnotationUpdate
from tests.conftest import AnnotationsTestData


def test_update_annotations_object_detection_bounding_box(
    mocker: MockerFixture,
    collection_id: UUID,
    test_client: TestClient,
    annotations_test_data: AnnotationsTestData,
) -> None:
    object_detection_annotation = annotations_test_data.annotations[3]

    annotation_id = object_detection_annotation.sample_id
    bounding_box = {"x": 10, "y": 20, "width": 200, "height": 200}

    with patch(
        "lightly_studio.services.annotations_service.update_annotations"
    ) as mock_update_annotations:
        mock_update_annotations.return_value = [object_detection_annotation]
        # Update the annotation label using the service
        response = test_client.put(
            f"/api/collections/{collection_id!s}/annotations",
            json=[
                {
                    "annotation_id": str(annotation_id),
                    "collection_id": str(collection_id),
                    "bounding_box": bounding_box,
                }
            ],
        )

        # Verify the spy was called with annotation_update
        mock_update_annotations.assert_called_once_with(
            session=mocker.ANY,
            annotation_updates=[
                AnnotationUpdate(
                    collection_id=collection_id,
                    annotation_id=annotation_id,
                    bounding_box=BoundingBoxCoordinates(
                        x=bounding_box["x"],
                        y=bounding_box["y"],
                        width=bounding_box["width"],
                        height=bounding_box["height"],
                    ),
                )
            ],
        )

        assert response.status_code == HTTP_STATUS_OK
        result = response.json()[0]

        # check what we return result from the service
        assert result["sample_id"] == str(object_detection_annotation.sample_id)
