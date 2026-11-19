from __future__ import annotations

from uuid import UUID

from fastapi.testclient import TestClient
from sqlmodel import Session

from lightly_studio.api.routes.api.status import (
    HTTP_STATUS_BAD_REQUEST,
    HTTP_STATUS_NO_CONTENT,
    HTTP_STATUS_NOT_FOUND,
    HTTP_STATUS_UNPROCESSABLE_ENTITY,
)
from lightly_studio.resolvers import tag_resolver
from tests.helpers_resolvers import create_collection, create_image, create_tag


def test_v1_read_tag_by_name(test_client: TestClient, db_session: Session) -> None:
    collection_id = create_collection(session=db_session).collection_id
    tag = create_tag(session=db_session, collection_id=collection_id, tag_name="cat")
    url = f"/api/v1/collections/{collection_id}/tags"

    found = test_client.get(url, params={"name": "cat"})
    missing = test_client.get(url, params={"name": "dog"})

    assert found.json()["tag_id"] == str(tag.tag_id)
    assert missing.status_code == HTTP_STATUS_NOT_FOUND


def test_v1_add_tag_to_samples(test_client: TestClient, db_session: Session) -> None:
    collection_id = create_collection(session=db_session).collection_id
    image = create_image(session=db_session, collection_id=collection_id)
    body = {"tag_name": "cat", "sample_ids": [str(image.sample_id)]}

    response = test_client.post(f"/api/v1/collections/{collection_id}/tags:add", json=body)

    assert response.status_code == HTTP_STATUS_NO_CONTENT
    names = tag_resolver.get_names_by_sample_ids(session=db_session, sample_ids=[image.sample_id])
    assert names == {image.sample_id: ["cat"]}


def test_v1_add_tag_to_samples__sample_of_other_collection(
    test_client: TestClient, db_session: Session
) -> None:
    collection_id = create_collection(session=db_session).collection_id
    other_id = create_collection(session=db_session).collection_id
    image = create_image(session=db_session, collection_id=other_id)
    body = {"tag_name": "cat", "sample_ids": [str(image.sample_id)]}

    response = test_client.post(f"/api/v1/collections/{collection_id}/tags:add", json=body)

    assert response.status_code == HTTP_STATUS_BAD_REQUEST


def test_v1_add_tag_to_samples__too_many_samples(test_client: TestClient) -> None:
    collection_id = UUID("00000000-0000-0000-0000-000000000001")
    sample_ids = [str(UUID(int=i)) for i in range(1001)]
    body = {"tag_name": "cat", "sample_ids": sample_ids}

    response = test_client.post(f"/api/v1/collections/{collection_id}/tags:add", json=body)

    assert response.status_code == HTTP_STATUS_UNPROCESSABLE_ENTITY


def test_v1_remove_tag_from_samples(test_client: TestClient, db_session: Session) -> None:
    collection_id = create_collection(session=db_session).collection_id
    image = create_image(session=db_session, collection_id=collection_id)
    tag = create_tag(session=db_session, collection_id=collection_id, tag_name="cat")
    tag_resolver.add_sample_ids_to_tag_id(
        session=db_session, tag_id=tag.tag_id, sample_ids=[image.sample_id]
    )
    url = f"/api/v1/collections/{collection_id}/tags:remove"

    sample_ids = [str(image.sample_id)]

    missing = test_client.post(url, json={"tag_name": "dog", "sample_ids": sample_ids})
    names_after_missing = tag_resolver.get_names_by_sample_ids(
        session=db_session, sample_ids=[image.sample_id]
    )
    removed = test_client.post(url, json={"tag_name": "cat", "sample_ids": sample_ids})
    names_after_removed = tag_resolver.get_names_by_sample_ids(
        session=db_session, sample_ids=[image.sample_id]
    )

    assert missing.status_code == HTTP_STATUS_NO_CONTENT
    assert names_after_missing == {image.sample_id: ["cat"]}
    assert removed.status_code == HTTP_STATUS_NO_CONTENT
    assert names_after_removed == {}
