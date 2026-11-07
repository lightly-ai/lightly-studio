"""Regression tests for dataset ownership when updating parent tracks."""

import uuid
from collections.abc import Sequence
from uuid import UUID

import pytest
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
from tests.helpers_resolvers import create_collection


@pytest.mark.parametrize("parent", ["set", "remove", "self"])
def test_update_track__dataset_mismatch(
    db_session: Session,
    collection: CollectionTable,
    samples: list[ImageTable],
    test_client: TestClient,
    parent: str,
) -> None:
    other_collection = create_collection(session=db_session)
    root_id = _create_track(session=db_session, dataset_id=collection.dataset_id, number=1)
    target_id = _create_track(
        session=db_session, dataset_id=collection.dataset_id, number=2, parent_id=root_id
    )
    child_id = _create_track(
        session=db_session, dataset_id=collection.dataset_id, number=3, parent_id=target_id
    )
    annotation_ids = _create_annotations(
        session=db_session, collection=collection, samples=samples, track_ids=[target_id, child_id]
    )
    tracks_before = test_client.get(f"/api/datasets/{collection.dataset_id}/tracks").json()
    annotations_before = _read_annotations(
        test_client=test_client, collection=collection, annotation_ids=annotation_ids
    )
    parent_id = {"set": str(root_id), "remove": None, "self": str(target_id)}[parent]

    response = test_client.patch(
        f"/api/datasets/{other_collection.dataset_id}/tracks/{target_id}",
        json={"parent_object_track_id": parent_id},
    )

    assert response.status_code == HTTP_STATUS_NOT_FOUND
    assert response.json() == {"error": f"Track {target_id} not found."}
    assert test_client.get(f"/api/datasets/{collection.dataset_id}/tracks").json() == tracks_before
    assert test_client.get(f"/api/datasets/{other_collection.dataset_id}/tracks").json() == []
    assert (
        _read_annotations(
            test_client=test_client, collection=collection, annotation_ids=annotation_ids
        )
        == annotations_before
    )


@pytest.mark.parametrize("parent_exists", [True, False])
def test_update_track__invalid_parent(
    db_session: Session,
    collection: CollectionTable,
    samples: list[ImageTable],
    test_client: TestClient,
    parent_exists: bool,
) -> None:
    other_collection = create_collection(session=db_session)
    parent_id = (
        _create_track(session=db_session, dataset_id=other_collection.dataset_id, number=1)
        if parent_exists
        else uuid.uuid4()
    )
    target_id = _create_track(session=db_session, dataset_id=collection.dataset_id, number=1)
    child_id = _create_track(
        session=db_session, dataset_id=collection.dataset_id, number=2, parent_id=target_id
    )
    annotation_ids = _create_annotations(
        session=db_session,
        collection=collection,
        samples=samples,
        track_ids=[target_id, target_id, child_id],
    )
    tracks_before = test_client.get(f"/api/datasets/{collection.dataset_id}/tracks").json()
    other_tracks_before = test_client.get(
        f"/api/datasets/{other_collection.dataset_id}/tracks"
    ).json()
    annotations_before = _read_annotations(
        test_client=test_client, collection=collection, annotation_ids=annotation_ids
    )

    response = test_client.patch(
        f"/api/datasets/{collection.dataset_id}/tracks/{target_id}",
        json={"parent_object_track_id": str(parent_id)},
    )

    assert response.status_code == HTTP_STATUS_BAD_REQUEST
    assert response.json() == {"error": "Parent track not found in the dataset."}
    assert test_client.get(f"/api/datasets/{collection.dataset_id}/tracks").json() == tracks_before
    assert (
        test_client.get(f"/api/datasets/{other_collection.dataset_id}/tracks").json()
        == other_tracks_before
    )
    assert (
        _read_annotations(
            test_client=test_client, collection=collection, annotation_ids=annotation_ids
        )
        == annotations_before
    )


@pytest.mark.parametrize("operation", ["set", "change", "remove"])
def test_update_track__preserves_annotations_and_descendants(
    db_session: Session,
    collection: CollectionTable,
    samples: list[ImageTable],
    test_client: TestClient,
    operation: str,
) -> None:
    root_id = _create_track(session=db_session, dataset_id=collection.dataset_id, number=1)
    other_parent_id = _create_track(session=db_session, dataset_id=collection.dataset_id, number=2)
    target_id = _create_track(
        session=db_session,
        dataset_id=collection.dataset_id,
        number=3,
        parent_id=None if operation == "set" else root_id,
    )
    child_id = _create_track(
        session=db_session, dataset_id=collection.dataset_id, number=4, parent_id=target_id
    )
    grandchild_id = _create_track(
        session=db_session, dataset_id=collection.dataset_id, number=5, parent_id=child_id
    )
    annotation_ids = _create_annotations(
        session=db_session,
        collection=collection,
        samples=samples,
        track_ids=[target_id, target_id, child_id, grandchild_id],
    )
    parent_id = None if operation == "remove" else str(other_parent_id)

    response = test_client.patch(
        f"/api/datasets/{collection.dataset_id}/tracks/{target_id}",
        json={"parent_object_track_id": parent_id},
    )

    assert response.status_code == HTTP_STATUS_OK
    assert response.json()["parent_object_track_id"] == parent_id
    tracks_response = test_client.get(f"/api/datasets/{collection.dataset_id}/tracks")
    assert tracks_response.status_code == HTTP_STATUS_OK
    tracks = tracks_response.json()
    assert len(tracks) == 5
    by_number = {track["object_track_number"]: track for track in tracks}
    assert by_number[1]["object_track_id"] == str(root_id)
    assert by_number[2]["object_track_id"] == str(other_parent_id)
    assert by_number[3]["object_track_id"] == response.json()["object_track_id"]
    assert by_number[4]["parent_object_track_id"] == by_number[3]["object_track_id"]
    assert by_number[5]["parent_object_track_id"] == by_number[4]["object_track_id"]
    assert {str(target_id), str(child_id), str(grandchild_id)}.isdisjoint(
        track["object_track_id"] for track in tracks
    )
    annotations = _read_annotations(
        test_client=test_client, collection=collection, annotation_ids=annotation_ids
    )
    assert [annotation["object_track_id"] for annotation in annotations] == [
        by_number[3]["object_track_id"],
        by_number[3]["object_track_id"],
        by_number[4]["object_track_id"],
        by_number[5]["object_track_id"],
    ]
    assert [annotation["parent_object_track_number"] for annotation in annotations] == [
        None if operation == "remove" else 2,
        None if operation == "remove" else 2,
        3,
        4,
    ]


def _create_track(
    session: Session, dataset_id: UUID, number: int, parent_id: UUID | None = None
) -> UUID:
    return object_track_resolver.create_many(
        session=session,
        tracks=[
            ObjectTrackCreate(
                object_track_number=number,
                dataset_id=dataset_id,
                parent_object_track_id=parent_id,
            )
        ],
    )[0]


def _create_annotations(
    session: Session,
    collection: CollectionTable,
    samples: Sequence[ImageTable],
    track_ids: Sequence[UUID],
) -> list[UUID]:
    annotation_class = annotation_label_resolver.create(
        session=session,
        label=AnnotationLabelCreate(
            annotation_label_name="truck", dataset_id=collection.dataset_id
        ),
    )
    return annotation_resolver.create_many(
        session=session,
        parent_collection_id=collection.collection_id,
        annotations=[
            AnnotationCreate(
                annotation_label_id=annotation_class.annotation_label_id,
                annotation_type=AnnotationType.OBJECT_DETECTION,
                parent_sample_id=sample.sample_id,
                object_track_id=track_id,
                x=0,
                y=0,
                width=10,
                height=10,
            )
            for sample, track_id in zip(samples, track_ids)
        ],
    )


def _read_annotations(
    test_client: TestClient, collection: CollectionTable, annotation_ids: Sequence[UUID]
) -> list[dict[str, object]]:
    annotations = []
    for annotation_id in annotation_ids:
        response = test_client.get(
            f"/api/collections/{collection.collection_id}/annotations/{annotation_id}"
        )
        assert response.status_code == HTTP_STATUS_OK
        annotations.append(response.json())
    return annotations
