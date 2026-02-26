"""Tests for get_adjacent_samples service function."""

from __future__ import annotations

from uuid import uuid4

import pytest
from pytest_mock import MockerFixture
from sqlmodel import Session

from lightly_studio.models.adjacents import AdjacentResultView
from lightly_studio.models.collection import SampleType
from lightly_studio.resolvers.annotations.annotations_filter import (
    AnnotationsFilter,
)
from lightly_studio.resolvers.image_filter import ImageFilter
from lightly_studio.resolvers.sample_resolver.sample_filter import SampleFilter
from lightly_studio.resolvers.video_frame_resolver import VideoFrameAdjacentFilter
from lightly_studio.resolvers.video_frame_resolver.video_frame_filter import (
    VideoFrameFilter,
)
from lightly_studio.resolvers.video_resolver.video_filter import VideoFilter
from lightly_studio.services.sample_services.sample_adjacents_service import (
    AdjacentRequest,
    get_adjacent_samples,
)


def _make_adjacent_result() -> AdjacentResultView:
    return AdjacentResultView(
        previous_sample_id=uuid4(),
        sample_id=uuid4(),
        next_sample_id=uuid4(),
        current_sample_position=2,
        total_count=3,
    )


def test_get_adjacent_samples__delegates_to_image_resolver(
    db_session: Session,
    mocker: MockerFixture,
) -> None:
    expected = _make_adjacent_result()
    mock_get_adjacent_images = mocker.patch(
        "lightly_studio.resolvers.image_resolver.get_adjacent_images",
        return_value=expected,
    )

    sample_id = uuid4()
    collection_id = uuid4()
    filters = ImageFilter(sample_filter=SampleFilter(collection_id=collection_id))
    text_embedding = [0.1, 0.2, 0.3]
    request = AdjacentRequest(
        sample_type=SampleType.IMAGE,
        filters=filters,
        text_embedding=text_embedding,
    )

    result = get_adjacent_samples(
        session=db_session,
        sample_id=sample_id,
        request=request,
    )

    assert result == expected
    mock_get_adjacent_images.assert_called_once_with(
        session=db_session,
        filters=filters,
        text_embedding=text_embedding,
        sample_id=sample_id,
    )


def test_get_adjacent_samples__delegates_to_video_resolver(
    db_session: Session,
    mocker: MockerFixture,
) -> None:
    expected = _make_adjacent_result()
    mock_get_adjacent_videos = mocker.patch(
        "lightly_studio.resolvers.video_resolver.get_adjacent_videos",
        return_value=expected,
    )

    sample_id = uuid4()
    collection_id = uuid4()
    filters = VideoFilter(sample_filter=SampleFilter(collection_id=collection_id))
    text_embedding = [0.4, 0.5]
    request = AdjacentRequest(
        sample_type=SampleType.VIDEO,
        filters=filters,
        text_embedding=text_embedding,
    )

    result = get_adjacent_samples(
        session=db_session,
        sample_id=sample_id,
        request=request,
    )

    assert result == expected
    mock_get_adjacent_videos.assert_called_once_with(
        session=db_session,
        filters=filters,
        text_embedding=text_embedding,
        sample_id=sample_id,
    )


def test_get_adjacent_samples__delegates_to_video_frame_resolver(
    db_session: Session,
    mocker: MockerFixture,
) -> None:
    expected = _make_adjacent_result()
    mock_get_adjacent_video_frames = mocker.patch(
        "lightly_studio.resolvers.video_frame_resolver.get_adjacent_video_frames",
        return_value=expected,
    )

    sample_id = uuid4()
    filters = VideoFrameAdjacentFilter(
        video_frame_filter=VideoFrameFilter(
            sample_filter=SampleFilter(collection_id=uuid4()),
        )
    )
    request = AdjacentRequest(
        sample_type=SampleType.VIDEO_FRAME,
        filters=filters,
    )

    result = get_adjacent_samples(
        session=db_session,
        sample_id=sample_id,
        request=request,
    )

    assert result == expected
    mock_get_adjacent_video_frames.assert_called_once_with(
        session=db_session,
        filters=filters,
        sample_id=sample_id,
    )


def test_get_adjacent_samples__delegates_to_annotation_resolver(
    db_session: Session,
    mocker: MockerFixture,
) -> None:
    expected = _make_adjacent_result()
    mock_get_adjacent_annotations = mocker.patch(
        "lightly_studio.resolvers.annotation_resolver.get_adjacent_annotations",
        return_value=expected,
    )

    sample_id = uuid4()
    filters = AnnotationsFilter(collection_ids=[uuid4()])
    request = AdjacentRequest(
        sample_type=SampleType.ANNOTATION,
        filters=filters,
    )

    result = get_adjacent_samples(
        session=db_session,
        sample_id=sample_id,
        request=request,
    )

    assert result == expected
    mock_get_adjacent_annotations.assert_called_once_with(
        session=db_session,
        filters=filters,
        sample_id=sample_id,
    )


def test_get_adjacent_samples__raises_for_image_with_wrong_filter_type(
    db_session: Session,
) -> None:
    request = AdjacentRequest(
        sample_type=SampleType.IMAGE,
        filters=VideoFilter(sample_filter=SampleFilter(collection_id=uuid4())),
    )

    with pytest.raises(ValueError, match="Invalid filter provided. Expected ImageFilter"):
        get_adjacent_samples(
            session=db_session,
            sample_id=uuid4(),
            request=request,
        )


def test_get_adjacent_samples__raises_for_video_with_wrong_filter_type(
    db_session: Session,
) -> None:
    request = AdjacentRequest(
        sample_type=SampleType.VIDEO,
        filters=ImageFilter(sample_filter=SampleFilter(collection_id=uuid4())),
    )

    with pytest.raises(ValueError, match="Invalid filter provided. Expected VideoFilter"):
        get_adjacent_samples(
            session=db_session,
            sample_id=uuid4(),
            request=request,
        )


def test_get_adjacent_samples__raises_for_video_frame_with_wrong_filter_type(
    db_session: Session,
) -> None:
    request = AdjacentRequest(
        sample_type=SampleType.VIDEO_FRAME,
        filters=ImageFilter(sample_filter=SampleFilter(collection_id=uuid4())),
    )

    with pytest.raises(
        ValueError, match="Invalid filter provided. Expected VideoFrameAdjacentFilter"
    ):
        get_adjacent_samples(
            session=db_session,
            sample_id=uuid4(),
            request=request,
        )


def test_get_adjacent_samples__raises_for_annotation_with_wrong_filter_type(
    db_session: Session,
) -> None:
    request = AdjacentRequest(
        sample_type=SampleType.ANNOTATION,
        filters=ImageFilter(sample_filter=SampleFilter(collection_id=uuid4())),
    )

    with pytest.raises(ValueError, match="Invalid filter provided. Expected AnnotationsFilter"):
        get_adjacent_samples(
            session=db_session,
            sample_id=uuid4(),
            request=request,
        )


def test_get_adjacent_samples__raises_not_implemented_for_unsupported_type(
    db_session: Session,
) -> None:
    request = AdjacentRequest(
        sample_type=SampleType.CAPTION,
        filters=ImageFilter(sample_filter=SampleFilter(collection_id=uuid4())),
    )

    with pytest.raises(NotImplementedError, match="not implemented for sample type"):
        get_adjacent_samples(
            session=db_session,
            sample_id=uuid4(),
            request=request,
        )
