from uuid import uuid4

from fastapi.testclient import TestClient
from pytest_mock import MockerFixture

from lightly_studio.api.routes.api.status import (
    HTTP_STATUS_CREATED,
    HTTP_STATUS_OK,
)
from lightly_studio.api.routes.api.validators import Paginated
from lightly_studio.models.dataset import DatasetTable
from lightly_studio.models.image import ImageView
from lightly_studio.resolvers import (
    dataset_resolver,
    sample_resolver,
    tag_resolver,
)
from lightly_studio.resolvers.sample_resolver import GetAllSamplesByDatasetIdResult
from lightly_studio.resolvers.samples_filter import (
    FilterDimensions,
    SampleFilter,
)


def test_read_samples_calls_get_all(mocker: MockerFixture, test_client: TestClient) -> None:
    dataset_id = uuid4()

    mocker.patch.object(
        dataset_resolver,
        "get_by_id",
        return_value=DatasetTable(dataset_id=dataset_id),
    )

    # Mock the sample_resolver
    mock_get_all_by_dataset_id = mocker.patch.object(
        sample_resolver,
        "get_all_by_dataset_id",
        return_value=GetAllSamplesByDatasetIdResult(samples=[], total_count=0),
    )
    # Make the request to the `/samples` endpoint
    mock_annotation_label_ids = [uuid4(), uuid4()]
    mock_tag_ids = [uuid4(), uuid4(), uuid4()]
    json_body = {
        "dataset_id": str(dataset_id),
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
    response = test_client.post(f"/api/datasets/{dataset_id}/samples/list", json=json_body)

    # Assert the response
    assert response.status_code == HTTP_STATUS_OK
    assert (
        response.json()["data"] == []
    )  # Empty list as per mocked `get_all_by_dataset_id` return value
    assert response.json()["total_count"] == 0

    # Assert that `get_all_by_dataset_id` was called with the correct arguments
    mock_get_all_by_dataset_id.assert_called_once_with(
        session=mocker.ANY,
        dataset_id=dataset_id,
        filters=SampleFilter(
            width=FilterDimensions(
                min=10,
                max=100,
            ),
            height=FilterDimensions(
                min=10,
                max=100,
            ),
            annotation_label_ids=mock_annotation_label_ids,
            tag_ids=mock_tag_ids,
        ),
        pagination=Paginated(offset=0, limit=100),
        text_embedding=json_body["text_embedding"],
        sample_ids=None,
    )


def test_read_samples_calls_get_all__no_sample_resolver_mock(
    mocker: MockerFixture,
    test_client: TestClient,
) -> None:
    dataset_id = uuid4()

    mocker.patch.object(
        dataset_resolver,
        "get_by_id",
        return_value=DatasetTable(dataset_id=dataset_id),
    )

    # Make the request to the `/samples` endpoint
    mock_annotation_label_ids = [uuid4(), uuid4()]
    mock_tag_ids = [uuid4(), uuid4(), uuid4()]
    json_body = {
        "dataset_id": str(dataset_id),
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
    response = test_client.post(f"/api/datasets/{dataset_id}/samples/list", json=json_body)

    # Assert the response
    assert response.status_code == HTTP_STATUS_OK
    assert response.json()["data"] == []  # There are no samples in the database.
    assert response.json()["total_count"] == 0


def test_get_samples_dimensions_calls_get_dimension_bounds(
    mocker: MockerFixture,
    test_client: TestClient,
) -> None:
    dataset_id = uuid4()

    mocker.patch.object(
        dataset_resolver,
        "get_by_id",
        return_value=DatasetTable(dataset_id=dataset_id),
    )

    # Mock sample_resolver.get_dimension_bounds
    mock_get_dimension_bounds = mocker.patch.object(
        sample_resolver,
        "get_dimension_bounds",
        return_value={
            "min_width": 0,
            "max_width": 100,
            "min_height": 0,
            "max_height": 100,
        },
    )

    # Make the request to the `/samples/dimensions` endpoint
    response = test_client.get(f"/api/datasets/{dataset_id}/samples/dimensions")

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
        session=mocker.ANY, dataset_id=dataset_id, annotation_label_ids=None
    )


def test_add_tag_to_sample_calls_add_tag_to_sample(
    mocker: MockerFixture,
    test_client: TestClient,
) -> None:
    dataset_id = uuid4()
    sample_id = uuid4()
    tag_id = uuid4()

    sample = ImageView(
        dataset_id=dataset_id,
        sample_id=sample_id,
        file_path_abs="/path/to/sample1.png",
        file_name="sample1.jpg",
        annotations=[],
        tags=[],
        width=100,
        height=100,
    )

    # Mock the sample_resolver
    mocker.patch.object(sample_resolver, "get_by_id", return_value=sample)

    # Mock the tag_resolver
    mock_add_tag_to_sample = mocker.patch.object(
        tag_resolver, "add_tag_to_sample", return_value=True
    )

    # Make the request to add sample to a tag
    response = test_client.post(f"/api/datasets/{dataset_id}/samples/{sample_id}/tag/{tag_id}")

    # Assert the response
    assert response.status_code == HTTP_STATUS_CREATED

    # Assert that `add_tag_to_sample` was called with the correct arguments
    mock_add_tag_to_sample.assert_called_once_with(
        session=mocker.ANY,
        tag_id=tag_id,
        sample=sample,
    )


def test_remove_tag_from_sample_calls_remove_tag_from_sample(
    mocker: MockerFixture,
    test_client: TestClient,
) -> None:
    dataset_id = uuid4()
    tag_id = uuid4()
    sample_id = uuid4()

    sample = ImageView(
        dataset_id=dataset_id,
        sample_id=sample_id,
        file_path_abs="/path/to/sample1.png",
        file_name="sample1.jpg",
        annotations=[],
        tags=[],
        width=100,
        height=100,
    )

    # Mock the sample_resolver
    mocker.patch.object(sample_resolver, "get_by_id", return_value=sample)

    # Mock the tag_resolver
    mock_remove_tag_from_sample = mocker.patch.object(
        tag_resolver, "remove_tag_from_sample", return_value=True
    )

    # Make the request to add sample to a tag
    response = test_client.delete(f"/api/datasets/{dataset_id}/samples/{sample_id}/tag/{tag_id}")

    # Assert the response
    assert response.status_code == HTTP_STATUS_OK

    # Assert that `remove_tag_from_sample` was called with the correct arguments
    mock_remove_tag_from_sample.assert_called_once_with(
        session=mocker.ANY,
        tag_id=tag_id,
        sample=sample,
    )
