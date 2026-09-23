from sqlmodel import Session

from lightly_studio.api.routes.api.validators import Paginated
from lightly_studio.models import sort
from lightly_studio.models.collection import SampleType
from lightly_studio.models.sort import SortFieldSource, VideoSortFieldExpr
from lightly_studio.models.sort_direction import SortDirection
from lightly_studio.resolvers import (
    metadata_resolver,
    video_resolver,
)
from tests.helpers_resolvers import (
    create_collection,
    create_embedding_model,
    create_sample_embedding,
)
from tests.resolvers.video.helpers import VideoStub, create_video_with_frames, create_videos


def test_get_all_by_collection_id__embedding_sort_overrides_order_by(db_session: Session) -> None:
    # A duration sort would order the videos the exact reverse of the similarity
    # order, so a passing assertion can only mean `order_by` was ignored.
    collection = create_collection(session=db_session, sample_type=SampleType.VIDEO)
    collection_id = collection.collection_id

    embedding_model = create_embedding_model(
        session=db_session,
        collection_id=collection_id,
        embedding_model_name="test_embedding_model",
        embedding_dimension=3,
        set_as_default=True,
    )

    video1_data = create_video_with_frames(
        session=db_session,
        collection_id=collection_id,
        video=VideoStub(path="/path/to/video1.mp4", duration_s=10.0),
    )
    video2_data = create_video_with_frames(
        session=db_session,
        collection_id=collection_id,
        video=VideoStub(path="/path/to/video2.mp4", duration_s=30.0),
    )
    for sample_id, embedding in [
        (video1_data.video_sample_id, [1.0, 1.0, 1.0]),
        (video2_data.video_sample_id, [-1.0, -1.0, -1.0]),
    ]:
        create_sample_embedding(
            session=db_session,
            sample_id=sample_id,
            embedding=embedding,
            embedding_model_id=embedding_model.embedding_model_id,
        )

    result = video_resolver.get_all_by_collection_id(
        session=db_session,
        collection_id=collection_id,
        text_embedding=[-1.0, -1.0, -1.0],
        order_by=[sort.sort_field_expr_to_order_by(_video_sort(field_name="duration_s"))],
    )

    # Ordered by similarity (video2 is nearest), not by ascending duration.
    assert [sample.sample_id for sample in result.samples] == [
        video2_data.video_sample_id,
        video1_data.video_sample_id,
    ]
    assert result.samples[0].similarity_score is not None


def test_get_all_by_collection_id__similarity_ties_broken_by_file_path(
    db_session: Session,
) -> None:
    # Identical embeddings make every distance equal, so ordering falls entirely to the
    # tiebreakers. Videos are inserted out of order; a pass means `file_path_abs` broke the
    # tie. Without it the similarity path leaves equal-distance rows in an undefined order,
    # which can repeat or drop videos across pages.
    collection = create_collection(session=db_session, sample_type=SampleType.VIDEO)
    collection_id = collection.collection_id

    embedding_model = create_embedding_model(
        session=db_session,
        collection_id=collection_id,
        embedding_model_name="test_embedding_model",
        embedding_dimension=3,
        set_as_default=True,
    )

    video_ids = create_videos(
        session=db_session,
        collection_id=collection_id,
        videos=[VideoStub(path=f"/path/to/{name}.mp4") for name in "cadb"],
    )
    for sample_id in video_ids:
        create_sample_embedding(
            session=db_session,
            sample_id=sample_id,
            embedding=[1.0, 1.0, 1.0],
            embedding_model_id=embedding_model.embedding_model_id,
        )

    text_embedding = [1.0, 1.0, 1.0]
    full = video_resolver.get_all_by_collection_id(
        session=db_session,
        collection_id=collection_id,
        text_embedding=text_embedding,
    )
    paged_sample_ids = [
        sample.sample_id
        for offset in [0, 2]
        for sample in video_resolver.get_all_by_collection_id(
            session=db_session,
            collection_id=collection_id,
            text_embedding=text_embedding,
            pagination=Paginated(offset=offset, limit=2),
        ).samples
    ]

    # Equal distances resolve to `file_path_abs` ascending, regardless of insert order.
    assert [sample.file_name for sample in full.samples] == ["a.mp4", "b.mp4", "c.mp4", "d.mp4"]
    # Pagination walks that same total order with no repeats or omissions.
    assert paged_sample_ids == [sample.sample_id for sample in full.samples]
    assert len(set(paged_sample_ids)) == 4


def test_get_all_by_collection_id__order_by_video_field(db_session: Session) -> None:
    collection = create_collection(session=db_session, sample_type=SampleType.VIDEO)
    create_videos(
        session=db_session,
        collection_id=collection.collection_id,
        videos=[
            VideoStub(path="/path/to/a.mp4", duration_s=30.0),
            VideoStub(path="/path/to/b.mp4", duration_s=10.0),
            VideoStub(path="/path/to/c.mp4", duration_s=20.0),
        ],
    )

    result = video_resolver.get_all_by_collection_id(
        session=db_session,
        collection_id=collection.collection_id,
        order_by=[sort.sort_field_expr_to_order_by(_video_sort(field_name="duration_s"))],
    )

    assert [sample.file_name for sample in result.samples] == ["b.mp4", "c.mp4", "a.mp4"]
    assert [sample.order_value for sample in result.samples] == [10.0, 20.0, 30.0]


def test_get_all_by_collection_id__order_by_video_field_descending(db_session: Session) -> None:
    collection = create_collection(session=db_session, sample_type=SampleType.VIDEO)
    create_videos(
        session=db_session,
        collection_id=collection.collection_id,
        videos=[
            VideoStub(path="/path/to/a.mp4", duration_s=30.0),
            VideoStub(path="/path/to/b.mp4", duration_s=10.0),
        ],
    )

    result = video_resolver.get_all_by_collection_id(
        session=db_session,
        collection_id=collection.collection_id,
        order_by=[
            sort.sort_field_expr_to_order_by(
                _video_sort(field_name="duration_s", direction=SortDirection.desc)
            )
        ],
    )

    assert [sample.file_name for sample in result.samples] == ["a.mp4", "b.mp4"]


def test_get_all_by_collection_id__order_by_video_field_descending_nulls_last(
    db_session: Session,
) -> None:
    # A video with unknown duration sorts last on descending order. PostgreSQL and DuckDB
    # default NULLs to opposite ends, so the engine pins them last for both.
    collection = create_collection(session=db_session, sample_type=SampleType.VIDEO)
    create_videos(
        session=db_session,
        collection_id=collection.collection_id,
        videos=[
            VideoStub(path="/path/to/a.mp4", duration_s=30.0),
            VideoStub(path="/path/to/b.mp4", duration_s=None),
            VideoStub(path="/path/to/c.mp4", duration_s=10.0),
        ],
    )

    result = video_resolver.get_all_by_collection_id(
        session=db_session,
        collection_id=collection.collection_id,
        order_by=[
            sort.sort_field_expr_to_order_by(
                _video_sort(field_name="duration_s", direction=SortDirection.desc)
            )
        ],
    )

    assert [sample.file_name for sample in result.samples] == ["a.mp4", "c.mp4", "b.mp4"]
    assert [sample.order_value for sample in result.samples] == [30.0, 10.0, None]


def test_get_all_by_collection_id__order_by_created_at(db_session: Session) -> None:
    # created_at lives on SampleTable and is stamped at insert, so inserting b before a
    # in separate calls makes b the older row. Ascending created_at ([b, a]) disagrees
    # with the file_path tiebreaker ([a, b]), so a pass can only mean it sorted by
    # created_at. DuckDB forbids updating an FK-referenced sample row, so the value is
    # controlled through insert order rather than set afterward.
    collection = create_collection(session=db_session, sample_type=SampleType.VIDEO)
    create_videos(
        session=db_session,
        collection_id=collection.collection_id,
        videos=[VideoStub(path="/path/to/b.mp4")],
    )
    create_videos(
        session=db_session,
        collection_id=collection.collection_id,
        videos=[VideoStub(path="/path/to/a.mp4")],
    )

    result = video_resolver.get_all_by_collection_id(
        session=db_session,
        collection_id=collection.collection_id,
        order_by=[sort.sort_field_expr_to_order_by(_video_sort(field_name="created_at"))],
    )

    assert [sample.file_name for sample in result.samples] == ["b.mp4", "a.mp4"]
    # created_at is a datetime, so it does not surface as a numeric order_value.
    assert [sample.order_value for sample in result.samples] == [None, None]


def test_get_all_by_collection_id__order_by_metadata(db_session: Session) -> None:
    collection = create_collection(session=db_session, sample_type=SampleType.VIDEO)
    video_ids = create_videos(
        session=db_session,
        collection_id=collection.collection_id,
        videos=[
            VideoStub(path="/path/to/a.mp4"),
            VideoStub(path="/path/to/b.mp4"),
            VideoStub(path="/path/to/c.mp4"),
        ],
    )
    for sample_id, blur_score in zip(video_ids, [0.9, 0.1, 0.5]):
        metadata_resolver.set_value_for_sample(
            session=db_session,
            sample_id=sample_id,
            key="blur_score",
            value=blur_score,
        )

    result = video_resolver.get_all_by_collection_id(
        session=db_session,
        collection_id=collection.collection_id,
        order_by=[
            sort.sort_field_expr_to_order_by(
                VideoSortFieldExpr(
                    source=SortFieldSource.metadata,
                    field_name="blur_score",
                    direction=SortDirection.asc,
                )
            )
        ],
    )

    assert [sample.file_name for sample in result.samples] == ["b.mp4", "c.mp4", "a.mp4"]
    assert [sample.order_value for sample in result.samples] == [0.1, 0.5, 0.9]


def test_get_all_by_collection_id__order_by_metadata_missing_values_last(
    db_session: Session,
) -> None:
    collection = create_collection(session=db_session, sample_type=SampleType.VIDEO)
    video_ids = create_videos(
        session=db_session,
        collection_id=collection.collection_id,
        videos=[
            VideoStub(path="/path/to/a.mp4"),
            VideoStub(path="/path/to/b.mp4"),
        ],
    )
    metadata_resolver.set_value_for_sample(
        session=db_session,
        sample_id=video_ids[1],
        key="blur_score",
        value=0.5,
    )

    result = video_resolver.get_all_by_collection_id(
        session=db_session,
        collection_id=collection.collection_id,
        order_by=[
            sort.sort_field_expr_to_order_by(
                VideoSortFieldExpr(
                    source=SortFieldSource.metadata,
                    field_name="blur_score",
                    direction=SortDirection.asc,
                )
            )
        ],
    )

    assert [sample.file_name for sample in result.samples] == ["b.mp4", "a.mp4"]
    assert result.samples[1].order_value is None


def test_get_all_by_collection_id__order_by_ties_broken_by_file_path(
    db_session: Session,
) -> None:
    collection = create_collection(session=db_session, sample_type=SampleType.VIDEO)
    create_videos(
        session=db_session,
        collection_id=collection.collection_id,
        videos=[
            VideoStub(path="/path/to/c.mp4", duration_s=5.0),
            VideoStub(path="/path/to/a.mp4", duration_s=5.0),
            VideoStub(path="/path/to/b.mp4", duration_s=5.0),
        ],
    )

    result = video_resolver.get_all_by_collection_id(
        session=db_session,
        collection_id=collection.collection_id,
        order_by=[sort.sort_field_expr_to_order_by(_video_sort(field_name="duration_s"))],
    )

    assert [sample.file_name for sample in result.samples] == ["a.mp4", "b.mp4", "c.mp4"]


def test_get_all_by_collection_id__order_by_paginates_without_repeats(
    db_session: Session,
) -> None:
    collection = create_collection(session=db_session, sample_type=SampleType.VIDEO)
    create_videos(
        session=db_session,
        collection_id=collection.collection_id,
        videos=[VideoStub(path=f"/path/to/{name}.mp4", duration_s=5.0) for name in "abcd"],
    )
    order_by = [sort.sort_field_expr_to_order_by(_video_sort(field_name="duration_s"))]

    first_page = video_resolver.get_all_by_collection_id(
        session=db_session,
        collection_id=collection.collection_id,
        pagination=Paginated(offset=0, limit=2),
        order_by=order_by,
    )
    second_page = video_resolver.get_all_by_collection_id(
        session=db_session,
        collection_id=collection.collection_id,
        pagination=Paginated(offset=2, limit=2),
        order_by=order_by,
    )

    assert [sample.file_name for sample in first_page.samples] == ["a.mp4", "b.mp4"]
    assert [sample.file_name for sample in second_page.samples] == ["c.mp4", "d.mp4"]


def test_get_all_by_collection_id__order_value_none_for_text_field(db_session: Session) -> None:
    collection = create_collection(session=db_session, sample_type=SampleType.VIDEO)
    create_videos(
        session=db_session,
        collection_id=collection.collection_id,
        videos=[VideoStub(path="/path/to/a.mp4")],
    )

    result = video_resolver.get_all_by_collection_id(
        session=db_session,
        collection_id=collection.collection_id,
        order_by=[sort.sort_field_expr_to_order_by(_video_sort(field_name="file_name"))],
    )

    assert result.samples[0].order_value is None


def test_get_all_by_collection_id__no_order_by_keeps_file_path_order(
    db_session: Session,
) -> None:
    collection = create_collection(session=db_session, sample_type=SampleType.VIDEO)
    create_videos(
        session=db_session,
        collection_id=collection.collection_id,
        videos=[
            VideoStub(path="/path/to/b.mp4"),
            VideoStub(path="/path/to/a.mp4"),
        ],
    )

    result = video_resolver.get_all_by_collection_id(
        session=db_session, collection_id=collection.collection_id
    )

    assert [sample.file_name for sample in result.samples] == ["a.mp4", "b.mp4"]
    assert [sample.order_value for sample in result.samples] == [None, None]


def _video_sort(
    field_name: str,
    direction: SortDirection = SortDirection.asc,
) -> VideoSortFieldExpr:
    return VideoSortFieldExpr(
        source=SortFieldSource.video,
        field_name=field_name,
        direction=direction,
    )
