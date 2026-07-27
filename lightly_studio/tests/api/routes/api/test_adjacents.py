"""Tests for the adjacents API endpoint."""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from lightly_studio.api.routes.api.status import (
    HTTP_STATUS_OK,
    HTTP_STATUS_UNPROCESSABLE_ENTITY,
)
from lightly_studio.models.collection import SampleType
from tests import helpers_resolvers
from tests.resolvers.video.helpers import VideoStub, create_video


def test_get_adjacent_samples__returns_adjacents_for_images(
    db_session: Session,
    test_client: TestClient,
) -> None:
    collection = helpers_resolvers.create_collection(session=db_session)
    collection_id = collection.collection_id

    image_a = helpers_resolvers.create_image(
        session=db_session,
        collection_id=collection_id,
        file_path_abs="/images/a.png",
    )
    image_b = helpers_resolvers.create_image(
        session=db_session,
        collection_id=collection_id,
        file_path_abs="/images/b.png",
    )
    image_c = helpers_resolvers.create_image(
        session=db_session,
        collection_id=collection_id,
        file_path_abs="/images/c.png",
    )

    response = test_client.post(
        f"/api/samples/{image_b.sample_id}/adjacents",
        json={
            "sample_type": "image",
            "collection_id": str(collection_id),
        },
    )

    assert response.status_code == HTTP_STATUS_OK
    data = response.json()
    assert data["previous_sample_id"] == str(image_a.sample_id)
    assert data["sample_id"] == str(image_b.sample_id)
    assert data["next_sample_id"] == str(image_c.sample_id)
    assert data["current_sample_position"] == 2
    assert data["total_count"] == 3


def test_get_adjacent_samples__first_sample_has_no_previous(
    db_session: Session,
    test_client: TestClient,
) -> None:
    collection = helpers_resolvers.create_collection(session=db_session)
    collection_id = collection.collection_id

    image_a = helpers_resolvers.create_image(
        session=db_session,
        collection_id=collection_id,
        file_path_abs="/images/a.png",
    )
    image_b = helpers_resolvers.create_image(
        session=db_session,
        collection_id=collection_id,
        file_path_abs="/images/b.png",
    )

    response = test_client.post(
        f"/api/samples/{image_a.sample_id}/adjacents",
        json={
            "sample_type": "image",
            "collection_id": str(collection_id),
        },
    )

    assert response.status_code == HTTP_STATUS_OK
    data = response.json()
    assert data["previous_sample_id"] is None
    assert data["sample_id"] == str(image_a.sample_id)
    assert data["next_sample_id"] == str(image_b.sample_id)
    assert data["current_sample_position"] == 1
    assert data["total_count"] == 2


def test_get_adjacent_samples__last_sample_has_no_next(
    db_session: Session,
    test_client: TestClient,
) -> None:
    collection = helpers_resolvers.create_collection(session=db_session)
    collection_id = collection.collection_id

    image_a = helpers_resolvers.create_image(
        session=db_session,
        collection_id=collection_id,
        file_path_abs="/images/a.png",
    )
    image_b = helpers_resolvers.create_image(
        session=db_session,
        collection_id=collection_id,
        file_path_abs="/images/b.png",
    )

    response = test_client.post(
        f"/api/samples/{image_b.sample_id}/adjacents",
        json={
            "sample_type": "image",
            "collection_id": str(collection_id),
        },
    )

    assert response.status_code == HTTP_STATUS_OK
    data = response.json()
    assert data["previous_sample_id"] == str(image_a.sample_id)
    assert data["sample_id"] == str(image_b.sample_id)
    assert data["next_sample_id"] is None
    assert data["current_sample_position"] == 2
    assert data["total_count"] == 2


def test_get_adjacent_samples__unknown_sample_returns_none(
    db_session: Session,
    test_client: TestClient,
) -> None:
    collection = helpers_resolvers.create_collection(session=db_session)
    collection_id = collection.collection_id

    helpers_resolvers.create_image(
        session=db_session,
        collection_id=collection_id,
        file_path_abs="/images/a.png",
    )

    unknown_sample_id = uuid4()
    response = test_client.post(
        f"/api/samples/{unknown_sample_id}/adjacents",
        json={
            "sample_type": "image",
            "collection_id": str(collection_id),
        },
    )

    assert response.status_code == HTTP_STATUS_OK
    assert response.json() is None


def test_get_adjacent_samples__missing_body_returns_unprocessable(
    test_client: TestClient,
) -> None:
    response = test_client.post(
        f"/api/samples/{uuid4()}/adjacents",
        json={},
    )

    assert response.status_code == HTTP_STATUS_UNPROCESSABLE_ENTITY


def test_get_adjacent_samples__returns_adjacents_for_videos(
    db_session: Session,
    test_client: TestClient,
) -> None:
    collection = helpers_resolvers.create_collection(
        session=db_session,
        sample_type=SampleType.VIDEO,
    )
    collection_id = collection.collection_id

    video_a = create_video(
        session=db_session,
        collection_id=collection_id,
        video=VideoStub(path="/videos/a.mp4"),
    )
    video_b = create_video(
        session=db_session,
        collection_id=collection_id,
        video=VideoStub(path="/videos/b.mp4"),
    )
    video_c = create_video(
        session=db_session,
        collection_id=collection_id,
        video=VideoStub(path="/videos/c.mp4"),
    )

    response = test_client.post(
        f"/api/samples/{video_b.sample_id}/adjacents",
        json={
            "sample_type": "video",
            "collection_id": str(collection_id),
        },
    )

    assert response.status_code == HTTP_STATUS_OK
    data = response.json()
    assert data["previous_sample_id"] == str(video_a.sample_id)
    assert data["sample_id"] == str(video_b.sample_id)
    assert data["next_sample_id"] == str(video_c.sample_id)
    assert data["current_sample_position"] == 2
    assert data["total_count"] == 3


def test_get_adjacent_samples__annotations_match_grid_ordering(
    db_session: Session,
    test_client: TestClient,
) -> None:
    collection = helpers_resolvers.create_collection(
        session=db_session, sample_type=SampleType.IMAGE
    )
    collection_id = collection.collection_id

    label = helpers_resolvers.create_annotation_label(
        session=db_session,
        root_collection_id=collection_id,
        label_name="dog",
    )

    # Paths are created out of order so that ordering by file path is observable.
    images = helpers_resolvers.create_images(
        db_session=db_session,
        collection_id=collection_id,
        images=[
            helpers_resolvers.ImageStub(path=path)
            for path in ["/images/c.png", "/images/a.png", "/images/b.png"]
        ],
    )

    # Two annotations per image so the created-at and annotation-id tiebreakers matter.
    annotations = helpers_resolvers.create_annotations(
        session=db_session,
        collection_id=collection_id,
        annotations=[
            helpers_resolvers.AnnotationDetails(
                sample_id=image.sample_id,
                annotation_label_id=label.annotation_label_id,
            )
            for image in images
            for _ in range(2)
        ],
    )
    annotation_collection_id = annotations[0].sample.collection_id

    grid_response = test_client.post(
        f"/api/collections/{annotation_collection_id}/annotations/payload",
        json={"pagination": {"cursor": 0, "limit": len(annotations)}},
    )
    assert grid_response.status_code == HTTP_STATUS_OK
    grid_sample_ids = [
        UUID(entry["annotation"]["sample_id"]) for entry in grid_response.json()["data"]
    ]
    assert len(grid_sample_ids) == len(annotations)

    # Follow the adjacency endpoint's next pointers from the first annotation.
    walked_sample_ids = [grid_sample_ids[0]]
    for _ in range(len(annotations)):
        response = test_client.post(
            f"/api/samples/{walked_sample_ids[-1]}/adjacents",
            json={
                "sample_type": SampleType.ANNOTATION.value,
                "collection_id": str(annotation_collection_id),
                "filters": {
                    "filter_type": "annotations",
                    "collection_ids": [str(annotation_collection_id)],
                },
            },
        )
        next_sample_id = response.json()["next_sample_id"]
        if next_sample_id is None:
            break
        walked_sample_ids.append(UUID(next_sample_id))
    else:
        pytest.fail("Adjacency chain did not terminate, the next pointers likely cycle.")

    assert walked_sample_ids == grid_sample_ids
