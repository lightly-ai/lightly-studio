from __future__ import annotations

from uuid import UUID

from fastapi.testclient import TestClient
from pytest_mock import MockerFixture

from lightly_studio.api.routes.api.status import HTTP_STATUS_OK
from lightly_studio.models.annotation.cuboid_3d import Cuboid3DCreate
from lightly_studio.services.annotations_service.update_annotation import AnnotationUpdate
from tests.conftest import AnnotationsTestData


def test_update_annotations_cuboid_3d(
    mocker: MockerFixture,
    collection_id: UUID,
    test_client: TestClient,
    annotations_test_data: AnnotationsTestData,
) -> None:
    annotation = annotations_test_data.annotations[0]
    annotation_id = annotation.sample_id

    cuboid = {
        "frame_id": "map",
        "px": 1.0,
        "py": 2.0,
        "pz": 3.0,
        "qx": 0.0,
        "qy": 0.0,
        "qz": 0.0,
        "qw": 1.0,
        "sx": 4.0,
        "sy": 5.0,
        "sz": 6.0,
    }

    mock_update_annotations = mocker.patch(
        "lightly_studio.services.annotations_service.update_annotations"
    )
    mock_update_annotations.return_value = [annotation]
    response = test_client.put(
        f"/api/collections/{collection_id!s}/annotations",
        json=[
            {
                "annotation_id": str(annotation_id),
                "collection_id": str(collection_id),
                "cuboid_3d": cuboid,
            }
        ],
    )

    mock_update_annotations.assert_called_once_with(
        session=mocker.ANY,
        annotation_updates=[
            AnnotationUpdate(
                collection_id=collection_id,
                annotation_id=annotation_id,
                cuboid_3d=Cuboid3DCreate(
                    frame_id="map",
                    px=1.0,
                    py=2.0,
                    pz=3.0,
                    qx=0.0,
                    qy=0.0,
                    qz=0.0,
                    qw=1.0,
                    sx=4.0,
                    sy=5.0,
                    sz=6.0,
                ),
            )
        ],
    )

    assert response.status_code == HTTP_STATUS_OK
    result = response.json()[0]
    assert result["sample_id"] == str(annotation_id)
