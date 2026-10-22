from pytest_mock import MockerFixture
from sqlmodel import Session

from lightly_studio.models.collection import SampleType
from lightly_studio.models.embedding_region import EmbeddingRegion, Point2D
from lightly_studio.models.recording import RecordingFormat
from lightly_studio.resolvers import (
    embedding_region_resolver,
    grid_filter_sample_ids,
    mcap_group_sequence_resolver,
    recording_resolver,
)
from lightly_studio.resolvers.annotations.annotations_filter import AnnotationsFilter
from lightly_studio.resolvers.mcap_group_sequence_resolver.mcap_sequence_filter import (
    McapSequenceFilter,
)
from lightly_studio.resolvers.sample_resolver.sample_filter import SampleFilter
from lightly_studio.resolvers.video_resolver.video_filter import VideoFilter
from tests.helpers_resolvers import (
    AnnotationDetails,
    create_annotation_label,
    create_annotations,
    create_collection,
    create_image,
)
from tests.resolvers.video.helpers import VideoStub, create_videos


def test_build_sample_ids_query__video_embedding_region(
    db_session: Session, mocker: MockerFixture
) -> None:
    collection = create_collection(session=db_session, sample_type=SampleType.VIDEO)
    video_ids = create_videos(
        session=db_session,
        collection_id=collection.collection_id,
        videos=[VideoStub(path="/path/to/a.mp4"), VideoStub(path="/path/to/b.mp4")],
    )
    mocker.patch.object(
        embedding_region_resolver,
        "get_sample_ids_in_region",
        return_value=[video_ids[1]],
    )
    video_filter = VideoFilter(
        sample_filter=SampleFilter(
            embedding_region=EmbeddingRegion(
                polygon=[Point2D(x=0, y=0), Point2D(x=1, y=0), Point2D(x=1, y=1)]
            )
        )
    )

    query = grid_filter_sample_ids.build_sample_ids_query(
        session=db_session,
        collection_id=collection.collection_id,
        grid_filter=video_filter,
    )

    assert set(db_session.exec(query).all()) == {video_ids[1]}
    assert video_filter.sample_filter is not None
    assert video_filter.sample_filter.region_sample_ids == [video_ids[1]]


def test_build_sample_ids_query__mcap_sequence_embedding_region(
    db_session: Session, mocker: MockerFixture
) -> None:
    collection = create_collection(session=db_session, sample_type=SampleType.SEQUENCE)
    recording_id = recording_resolver.create(
        session=db_session,
        dataset_id=collection.dataset_id,
        uri="/bags/drive_001.mcap",
        format_=RecordingFormat.MCAP,
    )
    sequence_ids = [
        mcap_group_sequence_resolver.create(
            session=db_session, collection_id=collection.collection_id, recording_id=recording_id
        )
        for _ in range(2)
    ]
    mocker.patch.object(
        embedding_region_resolver,
        "get_sample_ids_in_region",
        return_value=[sequence_ids[1]],
    )
    sequence_filter = McapSequenceFilter(
        sample_filter=SampleFilter(
            embedding_region=EmbeddingRegion(
                polygon=[Point2D(x=0, y=0), Point2D(x=1, y=0), Point2D(x=1, y=1)]
            )
        )
    )

    query = grid_filter_sample_ids.build_sample_ids_query(
        session=db_session,
        collection_id=collection.collection_id,
        grid_filter=sequence_filter,
    )

    assert set(db_session.exec(query).all()) == {sequence_ids[1]}
    assert sequence_filter.sample_filter is not None
    assert sequence_filter.sample_filter.region_sample_ids == [sequence_ids[1]]


def test_build_sample_ids_query__annotations_embedding_region(
    db_session: Session, mocker: MockerFixture
) -> None:
    collection = create_collection(session=db_session)
    image = create_image(session=db_session, collection_id=collection.collection_id)
    label = create_annotation_label(session=db_session, root_collection_id=collection.collection_id)
    annotations = create_annotations(
        session=db_session,
        collection_id=collection.collection_id,
        annotations=[
            AnnotationDetails(
                sample_id=image.sample_id, annotation_label_id=label.annotation_label_id
            ),
            AnnotationDetails(
                sample_id=image.sample_id, annotation_label_id=label.annotation_label_id
            ),
        ],
        collection_name="ground_truth",
    )
    annotation_ids = [annotation.sample_id for annotation in annotations]
    mocker.patch.object(
        embedding_region_resolver,
        "get_sample_ids_in_region",
        return_value=[annotation_ids[1]],
    )
    annotations_filter = AnnotationsFilter(
        embedding_region=EmbeddingRegion(
            polygon=[Point2D(x=0, y=0), Point2D(x=1, y=0), Point2D(x=1, y=1)]
        )
    )

    query = grid_filter_sample_ids.build_sample_ids_query(
        session=db_session,
        collection_id=annotations[0].annotation_collection_id,
        grid_filter=annotations_filter,
    )

    assert set(db_session.exec(query).all()) == {annotation_ids[1]}
    assert annotations_filter.region_sample_ids == [annotation_ids[1]]
