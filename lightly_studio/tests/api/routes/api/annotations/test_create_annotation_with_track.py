"""Tests for creating annotations with object track support."""

from __future__ import annotations

from fastapi.testclient import TestClient
from sqlmodel import Session

from lightly_studio.api.routes.api.status import HTTP_STATUS_OK
from lightly_studio.models.annotation.annotation_base import AnnotationType, AnnotationView
from lightly_studio.models.annotation.object_track import ObjectTrackCreate
from lightly_studio.models.annotation_label import AnnotationLabelTable
from lightly_studio.models.collection import CollectionTable
from lightly_studio.models.image import ImageTable
from lightly_studio.resolvers import object_track_resolver


def test_create_annotation_with_existing_track(
    collection: CollectionTable,
    test_client: TestClient,
    samples: list[ImageTable],
    annotation_labels: list[AnnotationLabelTable],
    db_session: Session,
) -> None:
    track_ids = object_track_resolver.create_many(
        session=db_session,
        tracks=[
            ObjectTrackCreate(object_track_number=1, dataset_id=collection.dataset_id),
        ],
    )
    route = f"/api/collections/{collection.collection_id!s}/annotations"

    response = test_client.post(
        route,
        json={
            "annotation_label_id": str(annotation_labels[0].annotation_label_id),
            "annotation_type": AnnotationType.OBJECT_DETECTION,
            "parent_sample_id": str(samples[0].sample_id),
            "object_track_id": str(track_ids[0]),
            "x": 0,
            "y": 0,
            "width": 10,
            "height": 10,
        },
    )

    assert response.status_code == HTTP_STATUS_OK
    result = AnnotationView(**response.json())
    assert result.object_track_id == track_ids[0]
    assert result.object_track_number == 1


def test_create_annotation_with_new_track(
    collection: CollectionTable,
    test_client: TestClient,
    samples: list[ImageTable],
    annotation_labels: list[AnnotationLabelTable],
) -> None:
    route = f"/api/collections/{collection.collection_id!s}/annotations"

    response = test_client.post(
        route,
        json={
            "annotation_label_id": str(annotation_labels[0].annotation_label_id),
            "annotation_type": AnnotationType.OBJECT_DETECTION,
            "parent_sample_id": str(samples[0].sample_id),
            "create_new_track": True,
            "x": 0,
            "y": 0,
            "width": 10,
            "height": 10,
        },
    )

    assert response.status_code == HTTP_STATUS_OK
    result = AnnotationView(**response.json())
    assert result.object_track_id is not None
    assert result.object_track_number == 1


def test_create_annotation_with_new_track_increments_number(
    collection: CollectionTable,
    test_client: TestClient,
    samples: list[ImageTable],
    annotation_labels: list[AnnotationLabelTable],
    db_session: Session,
) -> None:
    object_track_resolver.create_many(
        session=db_session,
        tracks=[
            ObjectTrackCreate(object_track_number=1, dataset_id=collection.dataset_id),
            ObjectTrackCreate(object_track_number=2, dataset_id=collection.dataset_id),
        ],
    )
    route = f"/api/collections/{collection.collection_id!s}/annotations"

    response = test_client.post(
        route,
        json={
            "annotation_label_id": str(annotation_labels[0].annotation_label_id),
            "annotation_type": AnnotationType.OBJECT_DETECTION,
            "parent_sample_id": str(samples[0].sample_id),
            "create_new_track": True,
            "x": 0,
            "y": 0,
            "width": 10,
            "height": 10,
        },
    )

    assert response.status_code == HTTP_STATUS_OK
    result = AnnotationView(**response.json())
    assert result.object_track_number == 3


def test_create_annotation_without_track(
    collection: CollectionTable,
    test_client: TestClient,
    samples: list[ImageTable],
    annotation_labels: list[AnnotationLabelTable],
) -> None:
    route = f"/api/collections/{collection.collection_id!s}/annotations"

    response = test_client.post(
        route,
        json={
            "annotation_label_id": str(annotation_labels[0].annotation_label_id),
            "annotation_type": AnnotationType.OBJECT_DETECTION,
            "parent_sample_id": str(samples[0].sample_id),
            "x": 0,
            "y": 0,
            "width": 10,
            "height": 10,
        },
    )

    assert response.status_code == HTTP_STATUS_OK
    result = AnnotationView(**response.json())
    assert result.object_track_id is None
    assert result.object_track_number is None
