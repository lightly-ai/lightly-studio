from uuid import uuid4

from fastapi.testclient import TestClient
from pytest_mock import MockerFixture

from lightly_studio.api.routes.api.status import (
    HTTP_STATUS_OK,
)
from lightly_studio.api.routes.api.validators import Paginated
from lightly_studio.models.collection import CollectionTable, SampleType
from lightly_studio.resolvers import (
    collection_resolver,
    image_resolver,
)
from lightly_studio.resolvers.image_filter import (
    FilterDimensions,
    ImageFilter,
)
from lightly_studio.resolvers.image_resolver.get_all_by_collection_id import (
    GetAllSamplesByCollectionIdResult,
)
from lightly_studio.resolvers.sample_resolver.sample_filter import SampleFilter


def test_read_samples_calls_get_all(mocker: MockerFixture, test_client: TestClient) -> None:
    collection_id = uuid4()

    mocker.patch.object(
        collection_resolver,
        "get_by_id",
        return_value=CollectionTable(collection_id=collection_id, sample_type=SampleType.IMAGE),
    )

    # Mock the sample_resolver
    mock_get_all_by_collection_id = mocker.patch.object(
        image_resolver,
        "get_all_by_collection_id",
        return_value=GetAllSamplesByCollectionIdResult(samples=[], total_count=0),
    )
    # Make the request to the `/images` endpoint
    mock_annotation_label_ids = [uuid4(), uuid4()]
    mock_tag_ids = [uuid4(), uuid4(), uuid4()]
    json_body = {
        "collection_id": str(collection_id),
        "filters": {
            "width": {
                "min": 10,
                "max": 100,
            },
            "height": {
                "min": 10,
                "max": 100,
            },
            "sample_filter": {
                "annotation_label_ids": [str(x) for x in mock_annotation_label_ids],
                "tag_ids": [str(x) for x in mock_tag_ids],
            },
        },
        "text_embedding": [1, 2, 3],
        "pagination": {
            "offset": 0,
            "limit": 100,
        },
    }
    response = test_client.post(f"/api/collections/{collection_id}/images/list", json=json_body)

    # Assert the response
    assert response.status_code == HTTP_STATUS_OK
    assert (
        response.json()["data"] == []
    )  # Empty list as per mocked `get_all_by_collection_id` return value
    assert response.json()["total_count"] == 0

    # Assert that `get_all_by_collection_id` was called with the correct arguments
    mock_get_all_by_collection_id.assert_called_once_with(
        session=mocker.ANY,
        collection_id=collection_id,
        filters=ImageFilter(
            width=FilterDimensions(
                min=10,
                max=100,
            ),
            height=FilterDimensions(
                min=10,
                max=100,
            ),
            sample_filter=SampleFilter(
                annotation_label_ids=mock_annotation_label_ids,
                tag_ids=mock_tag_ids,
            ),
        ),
        pagination=Paginated(offset=0, limit=100),
        text_embedding=json_body["text_embedding"],
        sample_ids=None,
    )


def test_read_samples_calls_get_all__no_sample_resolver_mock(
    mocker: MockerFixture,
    test_client: TestClient,
) -> None:
    collection_id = uuid4()

    mocker.patch.object(
        collection_resolver,
        "get_by_id",
        return_value=CollectionTable(collection_id=collection_id, sample_type=SampleType.IMAGE),
    )

    # Make the request to the `/images` endpoint
    mock_annotation_label_ids = [uuid4(), uuid4()]
    mock_tag_ids = [uuid4(), uuid4(), uuid4()]
    json_body = {
        "collection_id": str(collection_id),
        "filters": {
            "width": {
                "min": 10,
                "max": 100,
            },
            "height": {
                "min": 10,
                "max": 100,
            },
            "annotation_label_ids": [str(x) for x in mock_annotation_label_ids],
            "tag_ids": [str(x) for x in mock_tag_ids],
        },
        "text_embedding": [1, 2, 3],
        "pagination": {
            "offset": 0,
            "limit": 100,
        },
    }
    response = test_client.post(f"/api/collections/{collection_id}/images/list", json=json_body)

    # Assert the response
    assert response.status_code == HTTP_STATUS_OK
    assert response.json()["data"] == []  # There are no samples in the database.
    assert response.json()["total_count"] == 0


def test_get_samples_dimensions_calls_get_dimension_bounds(
    mocker: MockerFixture,
    test_client: TestClient,
) -> None:
    collection_id = uuid4()

    mocker.patch.object(
        collection_resolver,
        "get_by_id",
        return_value=CollectionTable(collection_id=collection_id, sample_type=SampleType.IMAGE),
    )

    # Mock sample_resolver.get_dimension_bounds
    mock_get_dimension_bounds = mocker.patch.object(
        image_resolver,
        "get_dimension_bounds",
        return_value={
            "min_width": 0,
            "max_width": 100,
            "min_height": 0,
            "max_height": 100,
        },
    )

    # Make the request to the `/images/dimensions` endpoint
    response = test_client.get(f"/api/collections/{collection_id}/images/dimensions")

    # Assert the response
    assert response.status_code == HTTP_STATUS_OK
    assert response.json() == {
        "min_width": 0,
        "max_width": 100,
        "min_height": 0,
        "max_height": 100,
    }

    # Assert that `get_dimension_bounds` was called with the correct arguments
    mock_get_dimension_bounds.assert_called_once_with(
        session=mocker.ANY,
        collection_id=collection_id,
        annotation_label_ids=None,
    )
