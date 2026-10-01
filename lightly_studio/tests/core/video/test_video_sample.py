import pytest
from sqlmodel import Session

from lightly_studio.core.annotation import ClassificationAnnotation, CreateClassification
from lightly_studio.core.video.video_sample import VideoSample
from lightly_studio.models.collection import SampleType
from tests.helpers_resolvers import create_collection
from tests.resolvers.video.helpers import VideoStub, create_video


class TestImageSample:
    def test_video_sample(self, db_session: Session) -> None:
        collection = create_collection(session=db_session, sample_type=SampleType.VIDEO)
        collection_id = collection.collection_id

        video_table = create_video(
            session=db_session,
            collection_id=collection_id,
            video=VideoStub(path="/path/to/sample1.mp4", width=320, height=240),
        )

        sample = VideoSample(inner=video_table)
        assert sample.file_name == "sample1.mp4"
        assert sample.width == 320
        assert sample.height == 240
        assert sample.collection_id == collection.collection_id
        assert sample.file_path_abs == "/path/to/sample1.mp4"
        assert sample.sample_id == video_table.sample_id


def test_add_annotation_classification(db_session: Session) -> None:
    collection = create_collection(session=db_session, sample_type=SampleType.VIDEO)
    video_table = create_video(
        session=db_session,
        collection_id=collection.collection_id,
        video=VideoStub(path="/path/to/sample.mp4"),
    )
    video = VideoSample(inner=video_table)

    video.add_annotation(
        CreateClassification(class_name="cat", confidence=0.75),
        annotation_source="model-v1",
    )

    assert len(video.annotations) == 1
    annotation = video.annotations[0]
    assert isinstance(annotation, ClassificationAnnotation)
    assert annotation.class_name == "cat"
    assert annotation.confidence == pytest.approx(0.75)
    assert annotation.annotation_source == "model-v1"
