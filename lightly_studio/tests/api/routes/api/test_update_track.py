"""Tests for PATCH /datasets/{dataset_id}/tracks/{track_id} endpoint."""

from __future__ import annotations

import uuid

from fastapi.testclient import TestClient
from sqlmodel import Session

from lightly_studio.api.routes.api.status import (
    HTTP_STATUS_BAD_REQUEST,
    HTTP_STATUS_NOT_FOUND,
    HTTP_STATUS_OK,
)
from lightly_studio.models.annotation.annotation_base import AnnotationCreate, AnnotationType
from lightly_studio.models.annotation.object_track import ObjectTrackCreate
from lightly_studio.models.annotation_label import AnnotationLabelCreate
from lightly_studio.models.collection import CollectionTable
from lightly_studio.models.image import ImageTable
from lightly_studio.resolvers import (
    annotation_label_resolver,
    annotation_resolver,
    object_track_resolver,
)


def test_update_track__set_parent(
    db_session: Session,
    collection: CollectionTable,
    test_client: TestClient,
) -> None:
    track_ids = object_track_resolver.create_many(
        session=db_session,
        tracks=[
            ObjectTrackCreate(object_track_number=1, dataset_id=collection.dataset_id),
            ObjectTrackCreate(object_track_number=2, dataset_id=collection.dataset_id),
        ],
    )

    response = test_client.patch(
        f"/api/datasets/{collection.dataset_id}/tracks/{track_ids[0]}",
        json={"parent_object_track_id": str(track_ids[1])},
    )

    assert response.status_code == HTTP_STATUS_OK
    data = response.json()
    assert data["parent_object_track_id"] == str(track_ids[1])
    assert data["object_track_number"] == 1


def test_update_track__change_parent(
    db_session: Session,
    collection: CollectionTable,
    test_client: TestClient,
) -> None:
    track_ids = object_track_resolver.create_many(
        session=db_session,
        tracks=[
            ObjectTrackCreate(object_track_number=1, dataset_id=collection.dataset_id),
            ObjectTrackCreate(object_track_number=2, dataset_id=collection.dataset_id),
            ObjectTrackCreate(object_track_number=3, dataset_id=collection.dataset_id),
        ],
    )
    first_response = test_client.patch(
        f"/api/datasets/{collection.dataset_id}/tracks/{track_ids[0]}",
        json={"parent_object_track_id": str(track_ids[1])},
    )
    new_track_id = first_response.json()["object_track_id"]

    response = test_client.patch(
        f"/api/datasets/{collection.dataset_id}/tracks/{new_track_id}",
        json={"parent_object_track_id": str(track_ids[2])},
    )

    assert response.status_code == HTTP_STATUS_OK
    assert response.json()["parent_object_track_id"] == str(track_ids[2])


def test_update_track__remove_parent(
    db_session: Session,
    collection: CollectionTable,
    test_client: TestClient,
) -> None:
    track_ids = object_track_resolver.create_many(
        session=db_session,
        tracks=[
            ObjectTrackCreate(object_track_number=1, dataset_id=collection.dataset_id),
            ObjectTrackCreate(object_track_number=2, dataset_id=collection.dataset_id),
        ],
    )
    first_response = test_client.patch(
        f"/api/datasets/{collection.dataset_id}/tracks/{track_ids[0]}",
        json={"parent_object_track_id": str(track_ids[1])},
    )
    new_track_id = first_response.json()["object_track_id"]

    response = test_client.patch(
        f"/api/datasets/{collection.dataset_id}/tracks/{new_track_id}",
        json={"parent_object_track_id": None},
    )

    assert response.status_code == HTTP_STATUS_OK
    assert response.json()["parent_object_track_id"] is None


def test_update_track__set_parent_with_annotations(
    db_session: Session,
    collection: CollectionTable,
    samples: list[ImageTable],
    test_client: TestClient,
) -> None:
    label = annotation_label_resolver.create(
        session=db_session,
        label=AnnotationLabelCreate(
            annotation_label_name="truck",
            dataset_id=collection.dataset_id,
        ),
    )
    track_ids = object_track_resolver.create_many(
        session=db_session,
        tracks=[
            ObjectTrackCreate(object_track_number=1, dataset_id=collection.dataset_id),
            ObjectTrackCreate(object_track_number=2, dataset_id=collection.dataset_id),
        ],
    )
    annotation_resolver.create_many(
        session=db_session,
        parent_collection_id=collection.collection_id,
        annotations=[
            AnnotationCreate(
                annotation_label_id=label.annotation_label_id,
                annotation_type=AnnotationType.OBJECT_DETECTION,
                parent_sample_id=samples[0].sample_id,
                object_track_id=track_ids[0],
                x=0,
                y=0,
                width=10,
                height=10,
            ),
        ],
    )

    response = test_client.patch(
        f"/api/datasets/{collection.dataset_id}/tracks/{track_ids[0]}",
        json={"parent_object_track_id": str(track_ids[1])},
    )

    assert response.status_code == HTTP_STATUS_OK
    data = response.json()
    assert data["parent_object_track_id"] == str(track_ids[1])
    assert data["annotation_class_name"] == "truck"
    assert data["object_track_number"] == 1


def test_update_track__reject_self_reference(
    db_session: Session,
    collection: CollectionTable,
    test_client: TestClient,
) -> None:
    track_ids = object_track_resolver.create_many(
        session=db_session,
        tracks=[
            ObjectTrackCreate(object_track_number=1, dataset_id=collection.dataset_id),
        ],
    )

    response = test_client.patch(
        f"/api/datasets/{collection.dataset_id}/tracks/{track_ids[0]}",
        json={"parent_object_track_id": str(track_ids[0])},
    )

    assert response.status_code == HTTP_STATUS_BAD_REQUEST
    assert "own parent" in response.json()["error"]


def test_update_track__reject_direct_cycle(
    db_session: Session,
    collection: CollectionTable,
    test_client: TestClient,
) -> None:
    track_ids = object_track_resolver.create_many(
        session=db_session,
        tracks=[
            ObjectTrackCreate(object_track_number=1, dataset_id=collection.dataset_id),
            ObjectTrackCreate(object_track_number=2, dataset_id=collection.dataset_id),
        ],
    )
    # Set track 2 as child of track 1.
    first_response = test_client.patch(
        f"/api/datasets/{collection.dataset_id}/tracks/{track_ids[1]}",
        json={"parent_object_track_id": str(track_ids[0])},
    )
    child_track_id = first_response.json()["object_track_id"]

    # Try to set track 1 as child of track 2 — would create A↔B cycle.
    response = test_client.patch(
        f"/api/datasets/{collection.dataset_id}/tracks/{track_ids[0]}",
        json={"parent_object_track_id": child_track_id},
    )

    assert response.status_code == HTTP_STATUS_BAD_REQUEST
    assert "circular" in response.json()["error"]


def test_update_track__reject_transitive_cycle(
    db_session: Session,
    collection: CollectionTable,
    test_client: TestClient,
) -> None:
    track_ids = object_track_resolver.create_many(
        session=db_session,
        tracks=[
            ObjectTrackCreate(object_track_number=1, dataset_id=collection.dataset_id),
            ObjectTrackCreate(object_track_number=2, dataset_id=collection.dataset_id),
            ObjectTrackCreate(object_track_number=3, dataset_id=collection.dataset_id),
        ],
    )
    # Build chain: track 1 → track 2 → track 3.
    resp_b = test_client.patch(
        f"/api/datasets/{collection.dataset_id}/tracks/{track_ids[1]}",
        json={"parent_object_track_id": str(track_ids[0])},
    )
    track_b_id = resp_b.json()["object_track_id"]
    resp_c = test_client.patch(
        f"/api/datasets/{collection.dataset_id}/tracks/{track_ids[2]}",
        json={"parent_object_track_id": track_b_id},
    )
    track_c_id = resp_c.json()["object_track_id"]

    # Try to set track 1 as child of track 3 — would create A→B→C→A cycle.
    response = test_client.patch(
        f"/api/datasets/{collection.dataset_id}/tracks/{track_ids[0]}",
        json={"parent_object_track_id": track_c_id},
    )

    assert response.status_code == HTTP_STATUS_BAD_REQUEST
    assert "circular" in response.json()["error"]


def test_update_track__not_found(
    collection: CollectionTable,
    test_client: TestClient,
) -> None:
    missing_id = uuid.uuid4()

    response = test_client.patch(
        f"/api/datasets/{collection.dataset_id}/tracks/{missing_id}",
        json={"parent_object_track_id": None},
    )

    assert response.status_code == HTTP_STATUS_NOT_FOUND
