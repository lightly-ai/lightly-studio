from sqlmodel import Session

from lightly_studio.models.annotation.annotation_base import AnnotationType
from lightly_studio.models.collection import SampleType
from lightly_studio.resolvers import (
    video_resolver,
)
from tests.helpers_resolvers import (
    AnnotationDetails,
    create_annotation_label,
    create_annotations,
    create_collection,
)
from tests.resolvers.video.helpers import VideoStub, create_videos


def test_get_view_by_id(db_session: Session) -> None:
    collection = create_collection(session=db_session, sample_type=SampleType.VIDEO)
    collection_id = collection.collection_id

    create_videos(
        session=db_session,
        collection_id=collection_id,
        videos=[
            VideoStub(path="/path/to/sample1.mp4"),
            VideoStub(path="/path/to/sample2.mp4"),
        ],
    )

    videos = video_resolver.get_all_by_collection_id(
        session=db_session,
        collection_id=collection_id,
    ).samples

    result = video_resolver.get_view_by_id(session=db_session, sample_id=videos[0].sample_id)

    assert result is not None
    assert result.file_name == "sample1.mp4"


def test_get_view_by_id__with_classification_annotation(db_session: Session) -> None:
    collection = create_collection(session=db_session, sample_type=SampleType.VIDEO)
    label = create_annotation_label(
        session=db_session,
        root_collection_id=collection.collection_id,
        label_name="car",
    )
    video_ids = create_videos(
        session=db_session,
        collection_id=collection.collection_id,
        videos=[VideoStub(path="/path/to/sample1.mp4")],
    )
    create_annotations(
        session=db_session,
        collection_id=collection.collection_id,
        annotations=[
            AnnotationDetails(
                sample_id=video_ids[0],
                annotation_label_id=label.annotation_label_id,
                annotation_type=AnnotationType.CLASSIFICATION,
            )
        ],
    )

    result = video_resolver.get_view_by_id(session=db_session, sample_id=video_ids[0])

    assert result is not None
    assert len(result.sample.annotations) == 1
    assert result.sample.annotations[0].annotation_type == AnnotationType.CLASSIFICATION
    assert result.sample.annotations[0].annotation_label.annotation_label_name == "car"
    assert result.sample.annotations[0].object_detection_details is None
    assert result.sample.annotations[0].segmentation_details is None
