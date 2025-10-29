from __future__ import annotations

from uuid import uuid4

from fastapi.testclient import TestClient
from pytest_mock import MockerFixture

from lightly_studio.api.routes.api.status import HTTP_STATUS_OK
from lightly_studio.models.dataset import DatasetTable
from lightly_studio.models.sample_type import SampleType
from lightly_studio.resolvers import dataset_resolver, tag_resolver


def test_read_tags__calls_get_all_by_dataset_id(
    mocker: MockerFixture, test_client: TestClient
) -> None:
    dataset_id = uuid4()

    mocker.patch.object(
        dataset_resolver,
        "get_by_id",
        return_value=DatasetTable(dataset_id=dataset_id, sample_type=SampleType.IMAGE),
    )

    # Mock the tag_resolver
    mock_get_all_by_dataset_id = mocker.patch.object(
        tag_resolver, "get_all_by_dataset_id", return_value=[]
    )

    # Make the request to the `/tags` endpoint
    response = test_client.get(
        f"/api/datasets/{dataset_id}/tags", params={"offset": 0, "limit": 100}
    )

    # Assert the response
    assert response.status_code == HTTP_STATUS_OK
    assert response.json() == []

    # Assert that `get_all_by_dataset_id` was called with the correct arguments
    mock_get_all_by_dataset_id.assert_called_once_with(
        session=mocker.ANY, dataset_id=dataset_id, offset=0, limit=100
    )
