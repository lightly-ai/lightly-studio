from __future__ import annotations

from fastapi.testclient import TestClient
from sqlmodel import Session, select

from lightly_studio.api.routes.api.status import HTTP_STATUS_CREATED
from lightly_studio.models.annotation.annotation_base import AnnotationBaseTable, AnnotationType
from tests.helpers_resolvers import ImageStub, create_collection, create_images


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
        f"/api/collections/{collection.collection_id}/annotations/classifications/bulk",
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
    url = f"/api/collections/{collection.collection_id}/annotations/classifications/bulk_by_filter"
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
