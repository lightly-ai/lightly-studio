from __future__ import annotations

from uuid import uuid4

from fastapi.testclient import TestClient
from sqlmodel import Session

from lightly_studio.api.routes.api.status import HTTP_STATUS_NOT_FOUND, HTTP_STATUS_OK
from lightly_studio.resolvers import annotation_resolver
from tests.helpers_resolvers import (
    create_annotation,
    create_annotation_label,
    create_collection,
    create_image,
)


def test_delete_annotations(db_session: Session, test_client: TestClient) -> None:
    collection = create_collection(session=db_session)
    image = create_image(session=db_session, collection_id=collection.collection_id)
    label = create_annotation_label(session=db_session, root_collection_id=collection.collection_id)
    annotations = [
        create_annotation(
            session=db_session,
            collection_id=collection.collection_id,
            sample_id=image.sample_id,
            annotation_label_id=label.annotation_label_id,
        )
        for _ in range(2)
    ]
    annotation_ids = [annotation.sample_id for annotation in annotations]
    annotation_collection_id = annotations[0].sample.collection_id

    response = test_client.request(
        "DELETE",
        f"/api/collections/{annotation_collection_id}/annotations",
        json={"annotation_ids": [str(annotation_id) for annotation_id in annotation_ids]},
    )

    assert response.status_code == HTTP_STATUS_OK
    assert response.json() == {"deleted_count": 2}
    assert annotation_resolver.get_by_ids(session=db_session, annotation_ids=annotation_ids) == []


def test_delete_annotations__unknown_collection(test_client: TestClient) -> None:
    response = test_client.request(
        "DELETE",
        f"/api/collections/{uuid4()}/annotations",
        json={"annotation_ids": [str(uuid4())]},
    )

    assert response.status_code == HTTP_STATUS_NOT_FOUND
