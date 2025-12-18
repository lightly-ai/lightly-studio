from __future__ import annotations

from uuid import uuid4

from fastapi.testclient import TestClient
from pytest_mock import MockerFixture

from lightly_studio.api.routes.api.status import HTTP_STATUS_OK
from lightly_studio.models.collection import CollectionTable, SampleType
from lightly_studio.resolvers import collection_resolver, tag_resolver


def test_read_tags__calls_get_all_by_dataset_id(
    mocker: MockerFixture, test_client: TestClient
) -> None:
    dataset_id = uuid4()

    mocker.patch.object(
        collection_resolver,
        "get_by_id",
        return_value=CollectionTable(collection_id=dataset_id, sample_type=SampleType.IMAGE),
    )

    # Mock the tag_resolver
    mock_get_all_by_collection_id = mocker.patch.object(
        tag_resolver, "get_all_by_collection_id", return_value=[]
    )

    # Make the request to the `/tags` endpoint
    response = test_client.get(
        f"/api/datasets/{dataset_id}/tags", params={"offset": 0, "limit": 100}
    )

    # Assert the response
    assert response.status_code == HTTP_STATUS_OK
    assert response.json() == []

    # Assert that `get_all_by_collection_id` was called with the correct arguments
    mock_get_all_by_collection_id.assert_called_once_with(
        session=mocker.ANY, collection_id=dataset_id, offset=0, limit=100
    )
