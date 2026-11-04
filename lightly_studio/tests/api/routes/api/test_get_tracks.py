"""Tests for GET /datasets/{dataset_id}/tracks endpoint."""

from __future__ import annotations

from fastapi.testclient import TestClient
from sqlmodel import Session

from lightly_studio.api.routes.api.status import HTTP_STATUS_OK
from lightly_studio.models.annotation.annotation_base import AnnotationCreate, AnnotationType
from lightly_studio.models.annotation.object_track import ObjectTrackCreate, TrackWithClassNameView
from lightly_studio.models.annotation_label import AnnotationLabelCreate
from lightly_studio.models.collection import CollectionTable
from lightly_studio.models.image import ImageTable
from lightly_studio.resolvers import (
    annotation_label_resolver,
    annotation_resolver,
    object_track_resolver,
)


def test_get_tracks_empty(
    collection: CollectionTable,
    test_client: TestClient,
) -> None:
    response = test_client.get(f"/api/datasets/{collection.dataset_id}/tracks")

    assert response.status_code == HTTP_STATUS_OK
    assert response.json() == []


def test_get_tracks_with_class_name(
    db_session: Session,
    collection: CollectionTable,
    samples: list[ImageTable],
    test_client: TestClient,
) -> None:
    label = annotation_label_resolver.create(
        db_session,
        AnnotationLabelCreate(
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

    response = test_client.get(f"/api/datasets/{collection.dataset_id}/tracks")

    assert response.status_code == HTTP_STATUS_OK
    result = [TrackWithClassNameView(**t) for t in response.json()]
    assert len(result) == 2

    by_number = {t.object_track_number: t for t in result}
    assert by_number[1].annotation_class_name == "truck"
    assert by_number[2].annotation_class_name is None
