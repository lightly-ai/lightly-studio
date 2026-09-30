from __future__ import annotations

from uuid import UUID

from pytest_mock import MockerFixture
from sqlmodel import Session

from lightly_studio.models.embedding_region import EmbeddingRegion, Point2D
from lightly_studio.resolvers import embedding_region_resolver, video_resolver
from lightly_studio.resolvers.sample_resolver.sample_filter import SampleFilter
from lightly_studio.resolvers.video_resolver.video_filter import VideoFilter


def test_resolve_embedding_region__no_filter(db_session: Session) -> None:
    assert (
        video_resolver.resolve_embedding_region(
            session=db_session,
            collection_id=UUID(int=1),
            video_filter=None,
        )
        is None
    )


def test_resolve_embedding_region__copies_filter_without_region(db_session: Session) -> None:
    original_filter = VideoFilter(sample_filter=SampleFilter())

    resolved_filter = video_resolver.resolve_embedding_region(
        session=db_session,
        collection_id=UUID(int=1),
        video_filter=original_filter,
    )

    assert resolved_filter is not None
    assert resolved_filter is not original_filter
    assert resolved_filter.sample_filter is not original_filter.sample_filter
    assert resolved_filter.sample_filter is not None
    assert resolved_filter.sample_filter.region_sample_ids is None


def test_resolve_embedding_region__resolves_sample_ids(
    db_session: Session,
    mocker: MockerFixture,
) -> None:
    collection_id = UUID(int=1)
    sample_ids = [UUID(int=2), UUID(int=3)]
    region = _create_region()
    original_filter = VideoFilter(sample_filter=SampleFilter(embedding_region=region))
    resolve_mock = mocker.patch.object(
        embedding_region_resolver,
        "get_sample_ids_in_region",
        return_value=sample_ids,
    )

    resolved_filter = video_resolver.resolve_embedding_region(
        session=db_session,
        collection_id=collection_id,
        video_filter=original_filter,
    )

    resolve_mock.assert_called_once_with(
        session=db_session,
        collection_id=collection_id,
        region=region,
    )
    assert resolved_filter is not None
    assert resolved_filter.sample_filter is not None
    assert resolved_filter.sample_filter.region_sample_ids == sample_ids
    assert original_filter.sample_filter is not None
    assert original_filter.sample_filter.region_sample_ids is None


def test_resolve_embedding_region__preserves_empty_match(
    db_session: Session,
    mocker: MockerFixture,
) -> None:
    original_filter = VideoFilter(sample_filter=SampleFilter(embedding_region=_create_region()))
    mocker.patch.object(embedding_region_resolver, "get_sample_ids_in_region", return_value=[])

    resolved_filter = video_resolver.resolve_embedding_region(
        session=db_session,
        collection_id=UUID(int=1),
        video_filter=original_filter,
    )

    assert resolved_filter is not None
    assert resolved_filter.sample_filter is not None
    assert resolved_filter.sample_filter.region_sample_ids == []


def _create_region() -> EmbeddingRegion:
    return EmbeddingRegion(
        polygon=[
            Point2D(x=0, y=0),
            Point2D(x=1, y=0),
            Point2D(x=1, y=1),
        ]
    )
