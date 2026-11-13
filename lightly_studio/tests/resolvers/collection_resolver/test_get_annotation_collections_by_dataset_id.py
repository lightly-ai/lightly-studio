from __future__ import annotations

from sqlmodel import Session

from lightly_studio.models.collection import SampleType
from lightly_studio.resolvers import collection_resolver
from tests.helpers_resolvers import create_collection


def test_get_annotation_collections_by_dataset_id(db_session: Session) -> None:
    videos = create_collection(session=db_session, sample_type=SampleType.VIDEO)
    events = create_collection(
        session=db_session,
        collection_name="events",
        parent_collection_id=videos.collection_id,
        sample_type=SampleType.ANNOTATION,
    )
    frames = create_collection(
        session=db_session,
        collection_name="frames",
        parent_collection_id=videos.collection_id,
        sample_type=SampleType.VIDEO_FRAME,
    )
    detections = create_collection(
        session=db_session,
        collection_name="detections",
        parent_collection_id=frames.collection_id,
        sample_type=SampleType.ANNOTATION,
    )

    result = collection_resolver.get_annotation_collections_by_dataset_id(
        session=db_session, dataset_id=videos.dataset_id
    )

    assert [c.collection_id for c in result] == [events.collection_id, detections.collection_id]


def test_get_annotation_collections_by_dataset_id__other_dataset(db_session: Session) -> None:
    images = create_collection(session=db_session, collection_name="images")
    create_collection(
        session=db_session,
        collection_name="ground_truth",
        parent_collection_id=images.collection_id,
        sample_type=SampleType.ANNOTATION,
    )
    other_images = create_collection(session=db_session, collection_name="other_images")

    result = collection_resolver.get_annotation_collections_by_dataset_id(
        session=db_session, dataset_id=other_images.dataset_id
    )

    assert result == []
