from __future__ import annotations

from uuid import uuid4

from fastapi.testclient import TestClient
from pytest_mock import MockerFixture
from sqlmodel import Session

from lightly_studio.api.routes.api.status import HTTP_STATUS_CONFLICT, HTTP_STATUS_OK
from lightly_studio.models.collection import CollectionTable, SampleType
from lightly_studio.resolvers import collection_resolver, tag_resolver
from tests.helpers_resolvers import create_collection, create_image, create_tag


def test_read_tags__calls_get_all_by_collection_id(
    mocker: MockerFixture, test_client: TestClient
) -> None:
    collection_id = uuid4()

    mocker.patch.object(
        collection_resolver,
        "get_by_id",
        return_value=CollectionTable(collection_id=collection_id, sample_type=SampleType.IMAGE),
    )

    # Mock the tag_resolver
    mock_get_all_by_collection_id = mocker.patch.object(
        tag_resolver, "get_all_by_collection_id", return_value=[]
    )

    # Make the request to the `/tags` endpoint
    response = test_client.get(
        f"/api/collections/{collection_id}/tags", params={"offset": 0, "limit": 100}
    )

    # Assert the response
    assert response.status_code == HTTP_STATUS_OK
    assert response.json() == []

    # Assert that `get_all_by_collection_id` was called with the correct arguments
    mock_get_all_by_collection_id.assert_called_once_with(
        session=mocker.ANY, collection_id=collection_id, offset=0, limit=100
    )


def test_delete_tag__deletes_tag_with_sample_links(
    db_session: Session, test_client: TestClient
) -> None:
    collection = create_collection(session=db_session)
    tag = create_tag(session=db_session, collection_id=collection.collection_id)
    image = create_image(session=db_session, collection_id=collection.collection_id)

    tag_resolver.add_tag_to_sample(session=db_session, tag_id=tag.tag_id, sample=image.sample)

    response = test_client.delete(f"/api/collections/{collection.collection_id}/tags/{tag.tag_id}")

    assert response.status_code == HTTP_STATUS_OK
    assert response.json() == {"status": "deleted"}
    assert tag_resolver.get_by_id(session=db_session, tag_id=tag.tag_id) is None


def test_update_tag__renames_tag_with_sample_links(
    db_session: Session, test_client: TestClient
) -> None:
    collection = create_collection(session=db_session)
    tag = create_tag(session=db_session, collection_id=collection.collection_id)
    image = create_image(session=db_session, collection_id=collection.collection_id)

    tag_resolver.add_tag_to_sample(session=db_session, tag_id=tag.tag_id, sample=image.sample)

    response = test_client.put(
        f"/api/collections/{collection.collection_id}/tags/{tag.tag_id}",
        json={
            "name": "renamed_tag",
            "description": tag.description,
            "kind": tag.kind,
        },
    )

    assert response.status_code == HTTP_STATUS_OK
    assert response.json()["name"] == "renamed_tag"

    updated_tag = tag_resolver.get_by_id(session=db_session, tag_id=tag.tag_id)
    assert updated_tag is not None
    assert updated_tag.name == "renamed_tag"
    assert len(updated_tag.samples) == 1
    assert updated_tag.samples[0].sample_id == image.sample.sample_id


def test_update_tag__rename_only_preserves_description(
    db_session: Session, test_client: TestClient
) -> None:
    collection = create_collection(session=db_session)
    tag = create_tag(
        session=db_session,
        collection_id=collection.collection_id,
        description="existing description",
    )

    response = test_client.put(
        f"/api/collections/{collection.collection_id}/tags/{tag.tag_id}",
        json={"name": "renamed_tag"},
    )

    assert response.status_code == HTTP_STATUS_OK
    assert response.json()["name"] == "renamed_tag"
    assert response.json()["description"] == "existing description"

    updated_tag = tag_resolver.get_by_id(session=db_session, tag_id=tag.tag_id)
    assert updated_tag is not None
    assert updated_tag.description == "existing description"


def test_update_tag__returns_conflict_if_name_is_already_used_by_another_tag(
    db_session: Session, test_client: TestClient
) -> None:
    collection = create_collection(session=db_session)
    tag = create_tag(session=db_session, collection_id=collection.collection_id, tag_name="tag_1")
    create_tag(session=db_session, collection_id=collection.collection_id, tag_name="tag_2")

    response = test_client.put(
        f"/api/collections/{collection.collection_id}/tags/{tag.tag_id}",
        json={
            "name": "tag_2",
            "description": tag.description,
            "kind": tag.kind,
        },
    )

    assert response.status_code == HTTP_STATUS_CONFLICT
