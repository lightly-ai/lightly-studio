from __future__ import annotations

from sqlmodel import Session, select

from lightly_studio.core.dataset_query.object_detection_query import (
    ObjectDetectionField,
    ObjectDetectionQuery,
)
from lightly_studio.core.dataset_query.video_frame_annotation_query import (
    VideoFrameAnnotationQuery,
)
from lightly_studio.models.collection import SampleType
from lightly_studio.models.sample import SampleTable
from lightly_studio.models.video import VideoTable
from tests.helpers_resolvers import (
    create_annotation,
    create_annotation_label,
    create_collection,
)
from tests.resolvers.video.helpers import VideoStub, create_video_with_frames


class TestVideoFrameAnnotationQuery:
    def test_get__matches_video_and_frame_annotations(self, db_session: Session) -> None:
        collection = create_collection(session=db_session, sample_type=SampleType.VIDEO)
        collection_id = collection.collection_id
        video_stub = VideoStub(duration_s=1.0, fps=2.0)
        video_annotated = create_video_with_frames(
            session=db_session, collection_id=collection_id, video=video_stub
        )
        frame_annotated = create_video_with_frames(
            session=db_session, collection_id=collection_id, video=video_stub
        )
        other_class = create_video_with_frames(
            session=db_session, collection_id=collection_id, video=video_stub
        )
        car = create_annotation_label(
            session=db_session, root_collection_id=collection_id, label_name="car"
        )
        bus = create_annotation_label(
            session=db_session, root_collection_id=collection_id, label_name="bus"
        )
        create_annotation(
            session=db_session,
            collection_id=collection_id,
            sample_id=video_annotated.video_sample_id,
            annotation_label_id=car.annotation_label_id,
        )
        create_annotation(
            session=db_session,
            collection_id=collection_id,
            sample_id=frame_annotated.frame_sample_ids[1],
            annotation_label_id=car.annotation_label_id,
        )
        create_annotation(
            session=db_session,
            collection_id=collection_id,
            sample_id=other_class.frame_sample_ids[0],
            annotation_label_id=bus.annotation_label_id,
        )

        query = (
            select(VideoTable.sample_id)
            .join(VideoTable.sample)
            .where(SampleTable.collection_id == collection_id)
            .where(
                VideoFrameAnnotationQuery(
                    annotation_query=ObjectDetectionQuery(ObjectDetectionField.class_name == "car")
                ).get()
            )
        )

        assert set(db_session.exec(query).all()) == {
            video_annotated.video_sample_id,
            frame_annotated.video_sample_id,
        }
