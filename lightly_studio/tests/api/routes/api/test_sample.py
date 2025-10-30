from uuid import uuid4

from fastapi.testclient import TestClient
from pytest_mock import MockerFixture
from sqlmodel import Session

from lightly_studio.api.routes.api.status import (
    HTTP_STATUS_CREATED,
    HTTP_STATUS_OK,
)
from lightly_studio.api.routes.api.validators import Paginated
from lightly_studio.models.dataset import DatasetTable
from lightly_studio.resolvers import (
    dataset_resolver,
    image_resolver_legacy,
    tag_resolver,
)
from lightly_studio.resolvers.image_resolver_legacy import GetAllSamplesByDatasetIdResult
from lightly_studio.resolvers.samples_filter import (
    FilterDimensions,
    SampleFilter,
)
from tests.helpers_resolvers import create_dataset, create_image, create_tag


def test_read_samples_calls_get_all(mocker: MockerFixture, test_client: TestClient) -> None:
    dataset_id = uuid4()

    mocker.patch.object(
        dataset_resolver,
        "get_by_id",
        return_value=DatasetTable(dataset_id=dataset_id),
    )

    # Mock the sample_resolver
    mock_get_all_by_dataset_id = mocker.patch.object(
        image_resolver_legacy,
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
        image_resolver_legacy,
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
    db_session: Session,
    test_client: TestClient,
) -> None:
    dataset = create_dataset(session=db_session)
    dataset_id = dataset.dataset_id
    image = create_image(session=db_session, dataset_id=dataset_id)
    tag = create_tag(session=db_session, dataset_id=dataset_id)
    sample_id = image.sample_id
    tag_id = tag.tag_id

    assert len(image.sample.tags) == 0

    # Make the request to add sample to a tag
    response = test_client.post(f"/api/datasets/{dataset_id}/samples/{sample_id}/tag/{tag_id}")

    # Assert the response
    assert response.status_code == HTTP_STATUS_CREATED

    # Assert that the tag was added
    assert len(image.sample.tags) == 1


def test_remove_tag_from_sample_calls_remove_tag_from_sample(
    db_session: Session,
    test_client: TestClient,
) -> None:
    dataset = create_dataset(session=db_session)
    dataset_id = dataset.dataset_id
    image = create_image(session=db_session, dataset_id=dataset_id)
    sample_id = image.sample_id
    tag = create_tag(session=db_session, dataset_id=dataset_id)
    tag_id = tag.tag_id

    tag_resolver.add_tag_to_sample(session=db_session, tag_id=tag_id, sample=image.sample)
    assert len(image.sample.tags) == 1

    # Make the request to add sample to a tag
    response = test_client.delete(f"/api/datasets/{dataset_id}/samples/{sample_id}/tag/{tag_id}")

    # Assert the response
    assert response.status_code == HTTP_STATUS_OK

    # Assert that the tag was removed
    assert len(image.sample.tags) == 0
