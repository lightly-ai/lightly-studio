from __future__ import annotations

from sqlmodel import Session

from lightly_studio.models.collection import SampleType
from lightly_studio.resolvers import collection_resolver, grid_filter
from lightly_studio.resolvers.annotations.annotations_filter import AnnotationsFilter
from lightly_studio.resolvers.image_filter import ImageFilter
from lightly_studio.resolvers.video_frame_resolver.video_frame_filter import VideoFrameFilter
from lightly_studio.resolvers.video_resolver.video_filter import VideoFilter
from tests.helpers_resolvers import (
    create_annotation,
    create_annotation_label,
    create_collection,
    create_image,
)
from tests.resolvers.video.helpers import VideoStub, create_video, create_video_with_frames


def test_build_sample_ids_query__image_filter_selects_images(db_session: Session) -> None:
    collection_id = create_collection(session=db_session).collection_id
    images = [
        create_image(session=db_session, collection_id=collection_id, file_path_abs=f"s{i}.png")
        for i in range(3)
    ]

    query = grid_filter.build_sample_ids_query(
        grid_filter=ImageFilter(), collection_id=collection_id
    )

    assert set(db_session.exec(query).all()) == {image.sample_id for image in images}


def test_build_sample_ids_query__image_filter_applies_constraints(db_session: Session) -> None:
    collection_id = create_collection(session=db_session).collection_id
    wide = create_image(
        session=db_session, collection_id=collection_id, file_path_abs="wide.png", width=1920
    )
    create_image(
        session=db_session, collection_id=collection_id, file_path_abs="narrow.png", width=10
    )

    query = grid_filter.build_sample_ids_query(
        grid_filter=ImageFilter.model_validate({"width": {"min": 100}}),
        collection_id=collection_id,
    )

    assert set(db_session.exec(query).all()) == {wide.sample_id}


def test_build_sample_ids_query__video_filter_selects_videos(db_session: Session) -> None:
    collection_id = create_collection(
        session=db_session, sample_type=SampleType.VIDEO
    ).collection_id
    video = create_video(session=db_session, collection_id=collection_id, video=VideoStub())

    query = grid_filter.build_sample_ids_query(
        grid_filter=VideoFilter(), collection_id=collection_id
    )

    assert set(db_session.exec(query).all()) == {video.sample_id}


def test_build_sample_ids_query__video_frame_filter_selects_frames(db_session: Session) -> None:
    collection = create_collection(session=db_session, sample_type=SampleType.VIDEO)
    video_with_frames = create_video_with_frames(
        session=db_session,
        collection_id=collection.collection_id,
        video=VideoStub(duration_s=0.1, fps=30.0),
    )

    query = grid_filter.build_sample_ids_query(
        grid_filter=VideoFrameFilter(),
        collection_id=video_with_frames.video_frames_collection_id,
    )

    assert set(db_session.exec(query).all()) == set(video_with_frames.frame_sample_ids)


def test_build_sample_ids_query__annotations_filter_selects_annotations(
    db_session: Session,
) -> None:
    collection = create_collection(session=db_session)
    image = create_image(session=db_session, collection_id=collection.collection_id)
    label = create_annotation_label(session=db_session, root_collection_id=collection.collection_id)
    annotation = create_annotation(
        session=db_session,
        collection_id=collection.collection_id,
        sample_id=image.sample_id,
        annotation_label_id=label.annotation_label_id,
    )
    annotation_collection_id = collection_resolver.get_or_create_child_collection(
        session=db_session,
        collection_id=collection.collection_id,
        sample_type=SampleType.ANNOTATION,
    )

    query = grid_filter.build_sample_ids_query(
        grid_filter=AnnotationsFilter(), collection_id=annotation_collection_id
    )

    assert set(db_session.exec(query).all()) == {annotation.sample_id}
