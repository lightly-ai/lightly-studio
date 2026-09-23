from __future__ import annotations

from fastapi.testclient import TestClient
from sqlmodel import Session

from lightly_studio.api.routes.api.status import HTTP_STATUS_BAD_REQUEST, HTTP_STATUS_OK
from lightly_studio.resolvers import tag_resolver
from tests.helpers_resolvers import (
    create_annotation,
    create_annotation_label,
    create_collection,
    create_image,
    create_tag,
)


def test_count_image_annotations_by_sample_tags(
    test_client: TestClient,
    db_session: Session,
) -> None:
    collection = create_collection(session=db_session)
    collection_id = collection.collection_id
    image = create_image(session=db_session, collection_id=collection_id)
    dog = create_annotation_label(
        session=db_session,
        root_collection_id=collection_id,
        label_name="dog",
    )
    create_annotation(
        session=db_session,
        sample_id=image.sample_id,
        annotation_label_id=dog.annotation_label_id,
        collection_id=collection_id,
    )
    populated_tag = create_tag(
        session=db_session,
        collection_id=collection_id,
        tag_name="populated",
    )
    empty_tag = create_tag(
        session=db_session,
        collection_id=collection_id,
        tag_name="empty",
    )
    tag_resolver.add_sample_ids_to_tag_id(
        session=db_session,
        tag_id=populated_tag.tag_id,
        sample_ids=[image.sample_id],
    )

    response = test_client.post(
        f"/api/collections/{collection_id}/images/annotations/count-by-sample-tags",
        json={"sample_tag_ids": [str(empty_tag.tag_id), str(populated_tag.tag_id)]},
    )

    assert response.status_code == HTTP_STATUS_OK
    assert response.json() == [
        {
            "sample_tag_id": str(empty_tag.tag_id),
            "sample_tag_name": "empty",
            "counts": [{"label_name": "dog", "count": 0}],
        },
        {
            "sample_tag_id": str(populated_tag.tag_id),
            "sample_tag_name": "populated",
            "counts": [{"label_name": "dog", "count": 1}],
        },
    ]


def test_count_image_annotations_by_sample_tags__rejects_annotation_tag(
    test_client: TestClient,
    db_session: Session,
) -> None:
    collection = create_collection(session=db_session)
    annotation_tag = create_tag(
        session=db_session,
        collection_id=collection.collection_id,
        kind="annotation",
    )

    response = test_client.post(
        f"/api/collections/{collection.collection_id}/images/annotations/count-by-sample-tags",
        json={"sample_tag_ids": [str(annotation_tag.tag_id)]},
    )

    assert response.status_code == HTTP_STATUS_BAD_REQUEST
    assert "must be sample tags belonging to collection" in response.json()["error"]
