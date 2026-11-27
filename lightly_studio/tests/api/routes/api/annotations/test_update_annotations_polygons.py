from __future__ import annotations

from fastapi.testclient import TestClient
from sqlmodel import Session

from lightly_studio.api.routes.api.status import HTTP_STATUS_OK
from lightly_studio.models.annotation.annotation_base import AnnotationType
from tests.helpers_resolvers import (
    create_annotation,
    create_annotation_label,
    create_collection,
    create_image,
)


def test_update_annotation__polygons(test_client: TestClient, db_session: Session) -> None:
    collection_id = create_collection(session=db_session).collection_id
    label = create_annotation_label(session=db_session, root_collection_id=collection_id)
    image = create_image(session=db_session, collection_id=collection_id)
    annotation = create_annotation(
        session=db_session,
        collection_id=collection_id,
        sample_id=image.sample_id,
        annotation_label_id=label.annotation_label_id,
        annotation_type=AnnotationType.POLYGON,
        polygons=[[(0, 0), (2, 0), (2, 2)]],
    )

    response = test_client.put(
        f"/api/collections/{collection_id!s}/annotations",
        json=[
            {
                "annotation_id": str(annotation.sample_id),
                "collection_id": str(collection_id),
                "polygons": [[[0, 0], [9, 0], [9, 7]]],
            }
        ],
    )

    assert response.status_code == HTTP_STATUS_OK
    db_session.refresh(annotation)
    assert annotation.polygon_details is not None
    details = annotation.polygon_details
    assert (details.x, details.y, details.width, details.height) == (0, 0, 9, 7)
    assert details.polygons == [[[0, 0], [9, 0], [9, 7]]]
