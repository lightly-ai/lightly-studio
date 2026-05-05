from __future__ import annotations

from uuid import uuid4

from fastapi.testclient import TestClient
from pytest_mock import MockerFixture
from sqlmodel import Session

from lightly_studio.api.routes.api.status import (
    HTTP_STATUS_BAD_REQUEST,
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
from tests.helpers_resolvers import (
    create_annotation,
    create_annotation_label,
    create_collection,
    create_image,
)
from tests.resolvers.video.helpers import VideoStub, create_video


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


def test_read_images__query_expr_filter(
    test_client: TestClient,
    db_session: Session,
) -> None:
    """Integration test: QueryExpr with OR across image and annotation fields."""
    collection = create_collection(session=db_session)
    collection_id = collection.collection_id

    # Three images: one wide, one with a "cat" detection, one with neither.
    wide_image = create_image(
        session=db_session,
        collection_id=collection_id,
        file_path_abs="/data/wide.png",
        width=800,
    )
    annotated_image = create_image(
        session=db_session,
        collection_id=collection_id,
        file_path_abs="/data/annotated.png",
        width=200,
    )
    create_image(
        session=db_session,
        collection_id=collection_id,
        file_path_abs="/data/neither.png",
        width=200,
    )

    cat_label = create_annotation_label(
        session=db_session,
        root_collection_id=collection_id,
        label_name="cat",
    )
    create_annotation(
        session=db_session,
        collection_id=collection_id,
        sample_id=annotated_image.sample_id,
        annotation_label_id=cat_label.annotation_label_id,
    )

    # Query: width >= 500 OR has_object_detection(label == "cat")
    # Should match wide_image (via width) and annotated_image (via annotation).
    query_expr = {
        "match_expr": {
            "type": "or",
            "children": [
                {
                    "type": "integer_expr",
                    "field": {"table": "image", "name": "width"},
                    "operator": ">=",
                    "value": 500,
                },
                {
                    "type": "object_detection_match_expr",
                    "subexpr": {
                        "type": "string_expr",
                        "field": {
                            "table": "object_detection",
                            "name": "label",
                        },
                        "operator": "==",
                        "value": "cat",
                    },
                },
            ],
        },
    }
    json_body = {
        "filters": {
            "sample_filter": {"query_expr": query_expr},
        },
    }
    response = test_client.post(f"/api/collections/{collection_id}/images/list", json=json_body)

    assert response.status_code == HTTP_STATUS_OK
    data = response.json()
    assert data["total_count"] == 2
    returned_ids = {item["sample_id"] for item in data["data"]}
    assert returned_ids == {str(wide_image.sample_id), str(annotated_image.sample_id)}


def test_read_images__query_expr_nonexistent_field(
    test_client: TestClient,
    db_session: Session,
) -> None:
    collection = create_collection(session=db_session)
    collection_id = collection.collection_id

    query_expr = {
        "match_expr": {
            "type": "string_expr",
            "field": {"table": "invalid", "name": "invalid"},
            "operator": "==",
            "value": "test",
        },
    }
    json_body = {
        "filters": {
            "sample_filter": {"query_expr": query_expr},
        },
    }
    response = test_client.post(f"/api/collections/{collection_id}/images/list", json=json_body)

    assert response.status_code == HTTP_STATUS_BAD_REQUEST
    data = response.json()
    assert data["error"] == "Unknown string field: invalid.invalid"


def test_read_images__query_expr_wrong_context(
    test_client: TestClient,
    db_session: Session,
) -> None:
    """This test documents an edge case behaviour.

    An invalid query referencing a field in the wrong context (e.g. video in an image context) will
    not error out. Instead, SQLAlchemy performs an outer join and samples will be returned if the
    query matches.
    """
    collection = create_collection(session=db_session, sample_type=SampleType.IMAGE)
    collection_id = collection.collection_id
    image = create_image(
        session=db_session,
        collection_id=collection_id,
        file_path_abs="/image.png",
    )

    video_collection = create_collection(session=db_session, sample_type=SampleType.VIDEO)
    create_video(
        session=db_session,
        collection_id=video_collection.collection_id,
        video=VideoStub(path="/video.mp4"),
    )

    # Video query for image dataset
    query_expr = {
        "match_expr": {
            "type": "string_expr",
            "field": {"table": "video", "name": "file_name"},
            "operator": "==",
            "value": "video.mp4",
        },
    }
    json_body = {
        "filters": {
            "sample_filter": {"query_expr": query_expr},
        },
    }
    response = test_client.post(f"/api/collections/{collection_id}/images/list", json=json_body)

    assert response.status_code == HTTP_STATUS_OK
    data = response.json()
    assert data["total_count"] == 1
    returned_ids = {item["sample_id"] for item in data["data"]}
    assert returned_ids == {str(image.sample_id)}


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


def test_count_image_annotations_by_collection__with_image_filter(
    test_client: TestClient,
    db_session: Session,
) -> None:
    collection = create_collection(session=db_session)
    collection_id = collection.collection_id

    image_1 = create_image(
        session=db_session,
        collection_id=collection_id,
        file_path_abs="/path/to/sample1.png",
    )
    image_2 = create_image(
        session=db_session,
        collection_id=collection_id,
        file_path_abs="/path/to/sample2.png",
    )
    image_3 = create_image(
        session=db_session,
        collection_id=collection_id,
        file_path_abs="/path/to/sample3.png",
    )

    dog_label = create_annotation_label(
        session=db_session,
        root_collection_id=collection_id,
        label_name="dog",
    )
    cat_label = create_annotation_label(
        session=db_session,
        root_collection_id=collection_id,
        label_name="cat",
    )

    create_annotation(
        session=db_session,
        sample_id=image_1.sample_id,
        annotation_label_id=cat_label.annotation_label_id,
        collection_id=collection_id,
    )
    create_annotation(
        session=db_session,
        sample_id=image_2.sample_id,
        annotation_label_id=dog_label.annotation_label_id,
        collection_id=collection_id,
    )
    create_annotation(
        session=db_session,
        sample_id=image_3.sample_id,
        annotation_label_id=dog_label.annotation_label_id,
        collection_id=collection_id,
    )

    response = test_client.post(
        f"/api/collections/{collection_id}/images/annotations/count",
        json={
            "filter": {
                "sample_filter": {
                    "annotations_filter": {
                        "annotation_label_ids": [str(dog_label.annotation_label_id)]
                    }
                }
            }
        },
    )

    assert response.status_code == HTTP_STATUS_OK
    result = response.json()

    assert result == [
        {"label_name": "cat", "current_count": 0, "total_count": 1},
        {"label_name": "dog", "current_count": 2, "total_count": 2},
    ]


def test_count_image_annotations_by_collection__without_body(
    test_client: TestClient,
    db_session: Session,
) -> None:
    collection = create_collection(session=db_session)
    collection_id = collection.collection_id

    image_1 = create_image(
        session=db_session,
        collection_id=collection_id,
        file_path_abs="/path/to/sample1.png",
    )
    dog_label = create_annotation_label(
        session=db_session,
        root_collection_id=collection_id,
        label_name="dog",
    )

    create_annotation(
        session=db_session,
        sample_id=image_1.sample_id,
        annotation_label_id=dog_label.annotation_label_id,
        collection_id=collection_id,
    )
    response = test_client.post(
        f"/api/collections/{collection_id}/images/annotations/count",
    )

    assert response.status_code == HTTP_STATUS_OK
    result = response.json()

    assert result == [
        {"label_name": "dog", "current_count": 1, "total_count": 1},
    ]


def test_get_image_sample_ids(
    test_client: TestClient,
    db_session: Session,
) -> None:
    collection = create_collection(session=db_session)
    image = create_image(
        session=db_session,
        collection_id=collection.collection_id,
        file_path_abs="/path/to/sample.png",
    )

    response = test_client.post(
        f"/api/collections/{collection.collection_id}/images/sample_ids",
        json={},
    )

    assert response.status_code == HTTP_STATUS_OK
    assert response.json() == [str(image.sample_id)]
