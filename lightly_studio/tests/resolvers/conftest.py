"""Fixtures for annotation resolver tests."""

import pytest
from sqlmodel import Session

from lightly_studio.models.annotation.annotation_base import AnnotationBaseTable, AnnotationType
from lightly_studio.models.collection import SampleType
from tests.helpers_resolvers import create_annotation, create_annotation_label, create_collection
from tests.resolvers.video.helpers import VideoStub, create_video


@pytest.fixture
def video_event(db_session: Session) -> AnnotationBaseTable:
    collection = create_collection(session=db_session, sample_type=SampleType.VIDEO)
    video = create_video(
        session=db_session, collection_id=collection.collection_id, video=VideoStub()
    )
    label = create_annotation_label(session=db_session, root_collection_id=collection.collection_id)
    return create_annotation(
        session=db_session,
        collection_id=collection.collection_id,
        sample_id=video.sample_id,
        annotation_label_id=label.annotation_label_id,
        annotation_type=AnnotationType.CLASSIFICATION,
        annotation_data={"start_time_s": 1.5, "end_time_s": 4.0},
    )
