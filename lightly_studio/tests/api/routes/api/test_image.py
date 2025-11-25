from contextlib import contextmanager
from typing import Generator, Tuple
from unittest.mock import MagicMock
from uuid import uuid4

from fastapi.testclient import TestClient
from pytest_mock import MockerFixture

from lightly_studio.api.routes.api.status import (
    HTTP_STATUS_OK,
)
from lightly_studio.api.routes.api.validators import Paginated
from lightly_studio.models.dataset import DatasetTable, SampleType
from lightly_studio.models.image import ImageTable
from lightly_studio.resolvers import (
    dataset_resolver,
    image_resolver,
)
from lightly_studio.resolvers.image_filter import (
    FilterDimensions,
    ImageFilter,
)
from lightly_studio.resolvers.image_resolver.get_all_by_dataset_id import (
    GetAllSamplesByDatasetIdResult,
)
from lightly_studio.resolvers.sample_resolver.sample_filter import SampleFilter


def test_read_samples_calls_get_all(mocker: MockerFixture, test_client: TestClient) -> None:
    dataset_id = uuid4()

    mocker.patch.object(
        dataset_resolver,
        "get_by_id",
        return_value=DatasetTable(dataset_id=dataset_id, sample_type=SampleType.IMAGE),
    )

    # Mock the sample_resolver
    mock_get_all_by_dataset_id = mocker.patch.object(
        image_resolver,
        "get_all_by_dataset_id",
        return_value=GetAllSamplesByDatasetIdResult(samples=[], total_count=0),
    )
    # Make the request to the `/images` endpoint
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
    response = test_client.post(f"/api/datasets/{dataset_id}/images/list", json=json_body)

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
    dataset_id = uuid4()

    mocker.patch.object(
        dataset_resolver,
        "get_by_id",
        return_value=DatasetTable(dataset_id=dataset_id, sample_type=SampleType.IMAGE),
    )

    # Make the request to the `/images` endpoint
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
    response = test_client.post(f"/api/datasets/{dataset_id}/images/list", json=json_body)

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
        return_value=DatasetTable(dataset_id=dataset_id, sample_type=SampleType.IMAGE),
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
    response = test_client.get(f"/api/datasets/{dataset_id}/images/dimensions")

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


def test_serve_image_by_sample_id_releases_session_before_streaming(
    mocker: MockerFixture, test_client: TestClient
) -> None:
    """Test that the database session is released before file streaming begins."""
    sample_id = str(uuid4())
    file_path = "/path/to/image.jpg"
    image_content = b"fake image content"

    # Track session lifecycle
    session_closed = [False]  # Use list to allow modification in nested functions
    session_get_called = [False]

    # Create a mock session
    mock_session = MagicMock()

    def mock_get(_: type, sample_id: str) -> ImageTable:
        session_get_called[0] = True
        # Session should still be open when get is called
        assert not session_closed[0], "Session was closed before get() was called"
        return ImageTable(
            sample_id=sample_id,
            file_path_abs=file_path,
            file_name="image.jpg",
            width=100,
            height=100,
        )

    mock_session.get.side_effect = mock_get

    # Create a context manager that properly tracks session lifecycle
    @contextmanager
    def mock_session_context() -> Generator[MagicMock, None, None]:
        try:
            yield mock_session
        finally:
            session_closed[0] = True

    # Mock db_manager.session to return our context manager
    mocker.patch(
        "lightly_studio.api.routes.images.db_manager.session",
        side_effect=lambda: mock_session_context(),
    )

    # Mock fsspec to verify session is closed before file operations
    mock_fs = MagicMock()
    mock_fs.cat_file.return_value = image_content

    def mock_url_to_fs(path: str) -> Tuple[MagicMock, str]:
        # Session should be closed before file streaming starts
        assert session_closed[0], "Session was not released before file streaming started"
        assert session_get_called[0], "Session.get() was never called"
        return mock_fs, path

    mocker.patch("fsspec.core.url_to_fs", side_effect=mock_url_to_fs)

    # Make the request
    response = test_client.get(f"/images/sample/{sample_id}")

    # Verify response
    assert response.status_code == HTTP_STATUS_OK
    # assert response.content == image_content
    assert session_closed[0], "Session should be closed after request completes"
    assert session_get_called[0], "Session.get() should have been called during the request"
