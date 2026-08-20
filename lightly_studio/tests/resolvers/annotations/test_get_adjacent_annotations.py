from collections.abc import Sequence
from datetime import datetime, timezone
from types import ModuleType
from uuid import UUID

import pytest
from pytest_mock import MockerFixture
from sqlmodel import Session, col

from lightly_studio.core.dataset_query.order_by import OrderByAnnotationEvaluationMetricField
from lightly_studio.models.annotation import annotation_base as annotation_base_module
from lightly_studio.models.annotation.annotation_base import AnnotationBaseTable
from lightly_studio.models.collection import SampleType
from lightly_studio.models.evaluation_annotation_metric import EvaluationAnnotationSide
from lightly_studio.resolvers import annotation_resolver, collection_resolver, tag_resolver
from lightly_studio.resolvers.annotation_resolver import (
    get_adjacent_annotations_keyset,
    get_adjacent_annotations_window,
)
from lightly_studio.resolvers.annotations.annotations_filter import AnnotationsFilter
from tests import helpers_resolvers
from tests.resolvers.evaluation_sample_metric_resolver.helpers import (
    FalseNegativeMetricStub,
    TruePositiveMetricStub,
    create_annotation_metrics,
    create_run,
)
from tests.resolvers.video.helpers import VideoStub, create_video_with_frames

# The two adjacency implementations the entry point dispatches to, as the (module, function)
# pairs `_fail_if_used` patches.
_KEYSET_PATH = (get_adjacent_annotations_keyset, "get_adjacent_annotations_keyset")
_WINDOW_PATH = (get_adjacent_annotations_window, "get_adjacent_annotations_window")


def test_get_adjacent_annotations__orders_by_path(db_session: Session) -> None:
    collection = helpers_resolvers.create_collection(
        session=db_session, sample_type=SampleType.IMAGE
    )
    collection_id = collection.collection_id

    label = helpers_resolvers.create_annotation_label(
        session=db_session,
        root_collection_id=collection_id,
        label_name="label",
    )

    image_a = helpers_resolvers.create_image(
        session=db_session,
        collection_id=collection_id,
        file_path_abs="/images/a.png",
    )
    image_b = helpers_resolvers.create_image(
        session=db_session,
        collection_id=collection_id,
        file_path_abs="/images/b.png",
    )
    image_c = helpers_resolvers.create_image(
        session=db_session,
        collection_id=collection_id,
        file_path_abs="/images/c.png",
    )

    annotation_a, annotation_b, annotation_c = helpers_resolvers.create_annotations(
        session=db_session,
        collection_id=collection_id,
        annotations=[
            helpers_resolvers.AnnotationDetails(
                sample_id=image_a.sample_id,
                annotation_label_id=label.annotation_label_id,
            ),
            helpers_resolvers.AnnotationDetails(
                sample_id=image_b.sample_id,
                annotation_label_id=label.annotation_label_id,
            ),
            helpers_resolvers.AnnotationDetails(
                sample_id=image_c.sample_id,
                annotation_label_id=label.annotation_label_id,
            ),
        ],
    )
    annotation_collection_id = annotation_a.sample.collection_id

    result = annotation_resolver.get_adjacent_annotations(
        session=db_session,
        sample_id=annotation_b.sample_id,
        filters=AnnotationsFilter(collection_ids=[annotation_collection_id]),
    )

    assert result is not None
    assert result.previous_sample_id == annotation_a.sample_id
    assert result.sample_id == annotation_b.sample_id
    assert result.next_sample_id == annotation_c.sample_id
    assert result.current_sample_position == 2
    assert result.total_count == 3


def test_get_adjacent_annotations__raises_with_filter_missing_collection_id(
    db_session: Session,
) -> None:
    collection = helpers_resolvers.create_collection(
        session=db_session, sample_type=SampleType.IMAGE
    )
    collection_id = collection.collection_id

    label = helpers_resolvers.create_annotation_label(
        session=db_session,
        root_collection_id=collection_id,
        label_name="label",
    )

    image = helpers_resolvers.create_image(
        session=db_session,
        collection_id=collection_id,
        file_path_abs="/images/a.png",
    )

    annotation = helpers_resolvers.create_annotation(
        session=db_session,
        collection_id=collection_id,
        sample_id=image.sample_id,
        annotation_label_id=label.annotation_label_id,
    )

    with pytest.raises(ValueError, match=r"Collection IDs must be provided in filters."):
        annotation_resolver.get_adjacent_annotations(
            session=db_session,
            sample_id=annotation.sample_id,
            filters=AnnotationsFilter(collection_ids=[]),
        )


def test_get_adjacent_annotations__respects_annotation_filter(db_session: Session) -> None:
    collection = helpers_resolvers.create_collection(
        session=db_session, sample_type=SampleType.IMAGE
    )
    collection_id = collection.collection_id

    dog_label = helpers_resolvers.create_annotation_label(
        session=db_session,
        root_collection_id=collection_id,
        label_name="dog",
    )
    cat_label = helpers_resolvers.create_annotation_label(
        session=db_session,
        root_collection_id=collection_id,
        label_name="cat",
    )

    image_a = helpers_resolvers.create_image(
        session=db_session,
        collection_id=collection_id,
        file_path_abs="/images/a.png",
    )
    image_b = helpers_resolvers.create_image(
        session=db_session,
        collection_id=collection_id,
        file_path_abs="/images/b.png",
    )
    image_c = helpers_resolvers.create_image(
        session=db_session,
        collection_id=collection_id,
        file_path_abs="/images/c.png",
    )

    annotation_a, annotation_b, _ = helpers_resolvers.create_annotations(
        session=db_session,
        collection_id=collection_id,
        annotations=[
            helpers_resolvers.AnnotationDetails(
                sample_id=image_a.sample_id,
                annotation_label_id=dog_label.annotation_label_id,
            ),
            helpers_resolvers.AnnotationDetails(
                sample_id=image_b.sample_id,
                annotation_label_id=dog_label.annotation_label_id,
            ),
            helpers_resolvers.AnnotationDetails(
                sample_id=image_c.sample_id,
                annotation_label_id=cat_label.annotation_label_id,
            ),
        ],
    )
    annotation_collection_id = annotation_a.sample.collection_id

    result = annotation_resolver.get_adjacent_annotations(
        session=db_session,
        sample_id=annotation_b.sample_id,
        filters=AnnotationsFilter(
            collection_ids=[annotation_collection_id],
            annotation_label_ids=[dog_label.annotation_label_id],
        ),
    )

    assert result is not None
    assert result.previous_sample_id == annotation_a.sample_id
    assert result.sample_id == annotation_b.sample_id
    assert result.next_sample_id is None
    assert result.current_sample_position == 2
    assert result.total_count == 2


def test_get_adjacent_annotations__respects_annotation_tags(db_session: Session) -> None:
    collection = helpers_resolvers.create_collection(
        session=db_session, sample_type=SampleType.IMAGE
    )
    collection_id = collection.collection_id

    dog_label = helpers_resolvers.create_annotation_label(
        session=db_session,
        root_collection_id=collection_id,
        label_name="dog",
    )

    image_a = helpers_resolvers.create_image(
        session=db_session,
        collection_id=collection_id,
        file_path_abs="/images/a.png",
    )
    image_b = helpers_resolvers.create_image(
        session=db_session,
        collection_id=collection_id,
        file_path_abs="/images/b.png",
    )
    image_c = helpers_resolvers.create_image(
        session=db_session,
        collection_id=collection_id,
        file_path_abs="/images/c.png",
    )

    annotation_a, annotation_b, annotation_c = helpers_resolvers.create_annotations(
        session=db_session,
        collection_id=collection_id,
        annotations=[
            helpers_resolvers.AnnotationDetails(
                sample_id=image_a.sample_id,
                annotation_label_id=dog_label.annotation_label_id,
            ),
            helpers_resolvers.AnnotationDetails(
                sample_id=image_b.sample_id,
                annotation_label_id=dog_label.annotation_label_id,
            ),
            helpers_resolvers.AnnotationDetails(
                sample_id=image_c.sample_id,
                annotation_label_id=dog_label.annotation_label_id,
            ),
        ],
    )
    annotation_collection_id = annotation_a.sample.collection_id

    tag_one = helpers_resolvers.create_tag(
        session=db_session,
        collection_id=annotation_collection_id,
        tag_name="anno-tag-1",
    )
    tag_two = helpers_resolvers.create_tag(
        session=db_session,
        collection_id=annotation_collection_id,
        tag_name="anno-tag-2",
    )

    tag_resolver.add_sample_ids_to_tag_id(
        session=db_session, tag_id=tag_one.tag_id, sample_ids=[annotation_a.sample_id]
    )
    tag_resolver.add_sample_ids_to_tag_id(
        session=db_session,
        tag_id=tag_one.tag_id,
        sample_ids=[annotation_b.sample_id],
    )
    tag_resolver.add_sample_ids_to_tag_id(
        session=db_session, tag_id=tag_two.tag_id, sample_ids=[annotation_b.sample_id]
    )
    tag_resolver.add_sample_ids_to_tag_id(
        session=db_session, tag_id=tag_two.tag_id, sample_ids=[annotation_c.sample_id]
    )

    result = annotation_resolver.get_adjacent_annotations(
        session=db_session,
        sample_id=annotation_b.sample_id,
        filters=AnnotationsFilter(
            collection_ids=[annotation_collection_id],
            annotation_tag_ids=[tag_one.tag_id, tag_two.tag_id],
        ),
    )

    assert result is not None
    assert result.previous_sample_id == annotation_a.sample_id
    assert result.sample_id == annotation_b.sample_id
    assert result.next_sample_id == annotation_c.sample_id
    assert result.current_sample_position == 2
    assert result.total_count == 3


def test_get_adjacent_annotations__respects_sample_tags(db_session: Session) -> None:
    collection = helpers_resolvers.create_collection(
        session=db_session, sample_type=SampleType.IMAGE
    )
    collection_id = collection.collection_id

    dog_label = helpers_resolvers.create_annotation_label(
        session=db_session,
        root_collection_id=collection_id,
        label_name="dog",
    )

    image_a = helpers_resolvers.create_image(
        session=db_session,
        collection_id=collection_id,
        file_path_abs="/images/a.png",
    )
    image_b = helpers_resolvers.create_image(
        session=db_session,
        collection_id=collection_id,
        file_path_abs="/images/b.png",
    )
    image_c = helpers_resolvers.create_image(
        session=db_session,
        collection_id=collection_id,
        file_path_abs="/images/c.png",
    )

    annotation_a, annotation_b, annotation_c = helpers_resolvers.create_annotations(
        session=db_session,
        collection_id=collection_id,
        annotations=[
            helpers_resolvers.AnnotationDetails(
                sample_id=image_a.sample_id,
                annotation_label_id=dog_label.annotation_label_id,
            ),
            helpers_resolvers.AnnotationDetails(
                sample_id=image_b.sample_id,
                annotation_label_id=dog_label.annotation_label_id,
            ),
            helpers_resolvers.AnnotationDetails(
                sample_id=image_c.sample_id,
                annotation_label_id=dog_label.annotation_label_id,
            ),
        ],
    )
    annotation_collection_id = annotation_a.sample.collection_id

    sample_tag_one = helpers_resolvers.create_tag(
        session=db_session,
        collection_id=collection_id,
        tag_name="sample-tag-1",
    )
    sample_tag_two = helpers_resolvers.create_tag(
        session=db_session,
        collection_id=collection_id,
        tag_name="sample-tag-2",
    )

    tag_resolver.add_sample_ids_to_tag_id(
        session=db_session, tag_id=sample_tag_one.tag_id, sample_ids=[image_a.sample_id]
    )
    tag_resolver.add_sample_ids_to_tag_id(
        session=db_session,
        tag_id=sample_tag_one.tag_id,
        sample_ids=[image_b.sample_id],
    )
    tag_resolver.add_sample_ids_to_tag_id(
        session=db_session, tag_id=sample_tag_two.tag_id, sample_ids=[image_b.sample_id]
    )
    tag_resolver.add_sample_ids_to_tag_id(
        session=db_session, tag_id=sample_tag_two.tag_id, sample_ids=[image_c.sample_id]
    )

    result = annotation_resolver.get_adjacent_annotations(
        session=db_session,
        sample_id=annotation_b.sample_id,
        filters=AnnotationsFilter(
            collection_ids=[annotation_collection_id],
            sample_tag_ids=[sample_tag_one.tag_id, sample_tag_two.tag_id],
        ),
    )

    assert result is not None
    assert result.previous_sample_id == annotation_a.sample_id
    assert result.sample_id == annotation_b.sample_id
    assert result.next_sample_id == annotation_c.sample_id
    assert result.current_sample_position == 2
    assert result.total_count == 3


def test_get_adjacent_annotations__returns_none_when_sample_not_in_filter(
    db_session: Session,
) -> None:
    collection = helpers_resolvers.create_collection(session=db_session)
    collection_1 = helpers_resolvers.create_collection(
        session=db_session, collection_name="collection_1"
    )

    dog_label = helpers_resolvers.create_annotation_label(
        session=db_session,
        root_collection_id=collection.collection_id,
        label_name="dog",
    )

    image_a = helpers_resolvers.create_image(
        session=db_session,
        collection_id=collection.collection_id,
        file_path_abs="/images/a.png",
    )

    annotation_a = helpers_resolvers.create_annotation(
        session=db_session,
        collection_id=collection.collection_id,
        sample_id=image_a.sample_id,
        annotation_label_id=dog_label.annotation_label_id,
    )

    result = annotation_resolver.get_adjacent_annotations(
        session=db_session,
        sample_id=annotation_a.sample_id,
        filters=AnnotationsFilter(
            collection_ids=[collection_1.collection_id],
        ),
    )

    assert result is None


def test_get_adjacent_annotations__orders_video_frame_annotations_by_video_path(
    db_session: Session,
    mocker: MockerFixture,
) -> None:
    _fail_if_used(mocker=mocker, path=_WINDOW_PATH)

    collection = helpers_resolvers.create_collection(
        session=db_session, sample_type=SampleType.VIDEO
    )
    label = helpers_resolvers.create_annotation_label(
        session=db_session,
        root_collection_id=collection.collection_id,
        label_name="label",
    )

    # Paths are created out of order so that ordering by video path is observable.
    video_c = create_video_with_frames(
        session=db_session,
        collection_id=collection.collection_id,
        video=VideoStub(path="/videos/c.mp4", duration_s=0.2, fps=10.0),
    )
    video_a = create_video_with_frames(
        session=db_session,
        collection_id=collection.collection_id,
        video=VideoStub(path="/videos/a.mp4", duration_s=0.2, fps=10.0),
    )
    video_b = create_video_with_frames(
        session=db_session,
        collection_id=collection.collection_id,
        video=VideoStub(path="/videos/b.mp4", duration_s=0.2, fps=10.0),
    )

    annotation_c, annotation_a, annotation_b = helpers_resolvers.create_annotations(
        session=db_session,
        collection_id=video_c.video_frames_collection_id,
        annotations=[
            helpers_resolvers.AnnotationDetails(
                sample_id=video.frame_sample_ids[0],
                annotation_label_id=label.annotation_label_id,
            )
            for video in (video_c, video_a, video_b)
        ],
    )

    result = annotation_resolver.get_adjacent_annotations(
        session=db_session,
        sample_id=annotation_b.sample_id,
        filters=AnnotationsFilter(collection_ids=[annotation_b.sample.collection_id]),
    )

    assert result is not None
    assert result.previous_sample_id == annotation_a.sample_id
    assert result.next_sample_id == annotation_c.sample_id
    assert result.current_sample_position == 2
    assert result.total_count == 3


def test_get_adjacent_annotations__orders_annotations_sharing_a_parent_image(
    db_session: Session,
    mocker: MockerFixture,
) -> None:
    # Annotations on the same image share the leading sort key, so the order is only total if
    # the created-at and sample-id tiebreakers are applied. Two of them are pinned to the same
    # created_at below, so their relative order can only come from the sample_id tiebreaker.
    collection = helpers_resolvers.create_collection(
        session=db_session, sample_type=SampleType.IMAGE
    )
    label = helpers_resolvers.create_annotation_label(
        session=db_session,
        root_collection_id=collection.collection_id,
        label_name="label",
    )
    image = helpers_resolvers.create_image(
        session=db_session,
        collection_id=collection.collection_id,
        file_path_abs="/images/a.png",
    )
    annotations = _create_annotations_with_pinned_created_at(
        session=db_session,
        mocker=mocker,
        collection_id=collection.collection_id,
        annotations=[
            helpers_resolvers.AnnotationDetails(
                sample_id=image.sample_id,
                annotation_label_id=label.annotation_label_id,
            )
            for _ in range(3)
        ],
    )
    expected_order = sorted(
        annotations, key=lambda annotation: (annotation.created_at, annotation.sample_id)
    )
    filters = AnnotationsFilter(collection_ids=[annotations[0].sample.collection_id])

    _assert_matches_expected_order(
        session=db_session, filters=filters, expected_order=expected_order
    )


@pytest.mark.parametrize(
    ("annotation_collection_names", "path_not_taken"),
    [
        # One collection has a known parent kind, so it can seek. Several could mix parent
        # kinds, so the keyset path bows out.
        (["annotations"], _WINDOW_PATH),
        (["annotations_a", "annotations_b"], _KEYSET_PATH),
    ],
    ids=["one_collection_seeks", "several_collections_fall_back"],
)
def test_get_adjacent_annotations__dispatches_on_collection_count(
    db_session: Session,
    mocker: MockerFixture,
    annotation_collection_names: list[str],
    path_not_taken: tuple[ModuleType, str],
) -> None:
    collection = helpers_resolvers.create_collection(
        session=db_session, sample_type=SampleType.IMAGE
    )
    label = helpers_resolvers.create_annotation_label(
        session=db_session,
        root_collection_id=collection.collection_id,
        label_name="label",
    )
    image = helpers_resolvers.create_image(
        session=db_session,
        collection_id=collection.collection_id,
        file_path_abs="/images/a.png",
    )
    annotations = [
        helpers_resolvers.create_annotation(
            session=db_session,
            collection_id=collection.collection_id,
            sample_id=image.sample_id,
            annotation_label_id=label.annotation_label_id,
            annotation_collection_name=name,
        )
        for name in annotation_collection_names
    ]

    _fail_if_used(mocker=mocker, path=path_not_taken)

    result = annotation_resolver.get_adjacent_annotations(
        session=db_session,
        sample_id=annotations[0].sample_id,
        filters=AnnotationsFilter(
            collection_ids=[annotation.sample.collection_id for annotation in annotations]
        ),
    )

    assert result is not None
    assert result.total_count == len(annotations)


def test_get_adjacent_annotations__falls_back_for_video_level_annotations(
    db_session: Session,
    mocker: MockerFixture,
) -> None:
    # Annotations on a video rather than on one of its frames, which the keyset path cannot
    # serve: it joins one parent table and there is no join from an annotation to its video.
    # The window query it falls back to reaches VideoTable only through VideoFrameTable, so
    # these annotations have no path to sort by — only the created-at and sample-id
    # tiebreakers order them, which is why created_at is pinned below.
    collection = helpers_resolvers.create_collection(
        session=db_session, sample_type=SampleType.VIDEO
    )
    label = helpers_resolvers.create_annotation_label(
        session=db_session,
        root_collection_id=collection.collection_id,
        label_name="label",
    )

    videos = [
        create_video_with_frames(
            session=db_session,
            collection_id=collection.collection_id,
            video=VideoStub(path=path, duration_s=0.2, fps=10.0),
        )
        for path in ("/videos/c.mp4", "/videos/a.mp4", "/videos/b.mp4")
    ]

    annotations = _create_annotations_with_pinned_created_at(
        session=db_session,
        mocker=mocker,
        collection_id=collection.collection_id,
        annotations=[
            helpers_resolvers.AnnotationDetails(
                sample_id=video.video_sample_id,
                annotation_label_id=label.annotation_label_id,
            )
            for video in videos
        ],
    )
    expected_order = sorted(
        annotations, key=lambda annotation: (annotation.created_at, annotation.sample_id)
    )
    filters = AnnotationsFilter(collection_ids=[annotations[0].sample.collection_id])

    _fail_if_used(mocker=mocker, path=_KEYSET_PATH)

    _assert_matches_expected_order(
        session=db_session, filters=filters, expected_order=expected_order
    )


def test_get_adjacent_annotations__returns_none_when_anchor_filtered_out_of_keyset_path(
    db_session: Session,
) -> None:
    # The keyset counterpart of __returns_none_when_sample_not_in_filter, which reaches the
    # same result through the window path: here the collection is scoped so the seek runs,
    # and the anchor's own label is what the filter excludes.
    collection = helpers_resolvers.create_collection(
        session=db_session, sample_type=SampleType.IMAGE
    )
    dog_label = helpers_resolvers.create_annotation_label(
        session=db_session,
        root_collection_id=collection.collection_id,
        label_name="dog",
    )
    cat_label = helpers_resolvers.create_annotation_label(
        session=db_session,
        root_collection_id=collection.collection_id,
        label_name="cat",
    )

    image_a = helpers_resolvers.create_image(
        session=db_session,
        collection_id=collection.collection_id,
        file_path_abs="/images/a.png",
    )
    image_b = helpers_resolvers.create_image(
        session=db_session,
        collection_id=collection.collection_id,
        file_path_abs="/images/b.png",
    )

    annotation_dog, annotation_cat = helpers_resolvers.create_annotations(
        session=db_session,
        collection_id=collection.collection_id,
        annotations=[
            helpers_resolvers.AnnotationDetails(
                sample_id=image_a.sample_id,
                annotation_label_id=dog_label.annotation_label_id,
            ),
            helpers_resolvers.AnnotationDetails(
                sample_id=image_b.sample_id,
                annotation_label_id=cat_label.annotation_label_id,
            ),
        ],
    )

    result = annotation_resolver.get_adjacent_annotations(
        session=db_session,
        sample_id=annotation_cat.sample_id,
        filters=AnnotationsFilter(
            collection_ids=[annotation_dog.sample.collection_id],
            annotation_label_ids=[dog_label.annotation_label_id],
        ),
    )

    assert result is None


def _create_annotations_with_pinned_created_at(
    session: Session,
    mocker: MockerFixture,
    collection_id: UUID,
    annotations: list[helpers_resolvers.AnnotationDetails],
) -> list[AnnotationBaseTable]:
    """Create 3 annotations, pinning created_at so the first two tie and the third is later.

    `AnnotationBaseTable.created_at` otherwise defaults to `datetime.now()` at construction
    time, so annotations created moments apart in the same batch almost never truly tie —
    pinning the clock guarantees a tie, forcing the sample_id tiebreaker to decide between
    them. Updating created_at after creation isn't an option: DuckDB rejects updating any
    column of an annotation row once it has FK-referencing detail rows (e.g. its object
    detection box).

    Args:
        session: Database session.
        mocker: Fixture used to pin the annotation module's clock.
        collection_id: ID of the collection.
        annotations: Exactly 3 annotation details to create.

    Returns:
        The created annotations, in the same order as `annotations`.
    """
    assert len(annotations) == 3, "This helper pins created_at for exactly 3 annotations."
    tied_created_at = datetime(2024, 1, 1, tzinfo=timezone.utc)
    later_created_at = datetime(2024, 1, 2, tzinfo=timezone.utc)
    times = iter([tied_created_at, tied_created_at, later_created_at])
    mocker.patch.object(
        annotation_base_module, "datetime", mocker.Mock(now=lambda _tz: next(times))
    )

    return helpers_resolvers.create_annotations(
        session=session, collection_id=collection_id, annotations=annotations
    )


def _fail_if_used(mocker: MockerFixture, path: tuple[ModuleType, str]) -> None:
    """Make the adjacency implementation at `path` fail if the dispatch calls it.

    Args:
        mocker: Fixture used to patch the implementation.
        path: The `(module, function name)` pair the dispatch must not call.
    """
    module, function_name = path
    mocker.patch.object(
        module, function_name, side_effect=AssertionError("Unexpected adjacency implementation.")
    )


def _assert_matches_expected_order(
    session: Session,
    filters: AnnotationsFilter,
    expected_order: Sequence[AnnotationBaseTable],
) -> None:
    """Assert get_adjacent_annotations agrees with expected_order at every position.

    Args:
        session: Database session.
        filters: Filters to query with.
        expected_order: Annotations in the exact order `get_adjacent_annotations` should place
            them, e.g. sorted by `(created_at, sample_id)`.
    """
    for position, annotation in enumerate(expected_order, start=1):
        result = annotation_resolver.get_adjacent_annotations(
            session=session, sample_id=annotation.sample_id, filters=filters
        )
        previous_annotation = expected_order[position - 2] if position > 1 else None
        next_annotation = expected_order[position] if position < len(expected_order) else None

        assert result is not None
        assert result.current_sample_position == position
        assert result.total_count == len(expected_order)
        assert result.previous_sample_id == (
            previous_annotation.sample_id if previous_annotation else None
        )
        assert result.next_sample_id == (next_annotation.sample_id if next_annotation else None)


def test_get_adjacent_annotations__sort_by_annotation_evaluation_metric(
    db_session: Session,
) -> None:
    # Unmatched (0.0) < matched (0.75); uncovered (NULL) sorts last
    root = helpers_resolvers.create_collection(session=db_session)
    label = helpers_resolvers.create_annotation_label(
        session=db_session, root_collection_id=root.collection_id
    )
    run = create_run(session=db_session, collection_id=root.collection_id)

    image_matched = helpers_resolvers.create_image(
        session=db_session, collection_id=root.collection_id, file_path_abs="/a.png"
    )
    image_unmatched = helpers_resolvers.create_image(
        session=db_session, collection_id=root.collection_id, file_path_abs="/b.png"
    )
    image_uncovered = helpers_resolvers.create_image(
        session=db_session, collection_id=root.collection_id, file_path_abs="/c.png"
    )

    matched_stub, unmatched_stub = create_annotation_metrics(
        session=db_session,
        run_id=run.id,
        pair_metric_stubs=[
            TruePositiveMetricStub(
                sample_id=image_matched.sample_id,
                metrics={"iou": 0.75},
                gt_annotation_label_id=label.annotation_label_id,
            ),
            FalseNegativeMetricStub(
                sample_id=image_unmatched.sample_id,
                gt_annotation_label_id=label.annotation_label_id,
            ),
        ],
    )

    gt_collection = collection_resolver.get_by_id(
        session=db_session, collection_id=run.gt_annotation_collection_id
    )
    assert gt_collection is not None
    uncovered = helpers_resolvers.create_annotation(
        session=db_session,
        collection_id=root.collection_id,
        sample_id=image_uncovered.sample_id,
        annotation_label_id=label.annotation_label_id,
        annotation_collection_name=gt_collection.name,
    )

    assert matched_stub.gt_annotation_id is not None
    assert unmatched_stub.gt_annotation_id is not None

    order_by = OrderByAnnotationEvaluationMetricField(
        evaluation_run_id=run.id,
        metric_name="iou",
        side=EvaluationAnnotationSide.GROUND_TRUTH,
        annotation_id_column=col(AnnotationBaseTable.sample_id),
    )
    filters = AnnotationsFilter(collection_ids=[run.gt_annotation_collection_id])

    # Query from the middle: matched is position 2 (unmatched=0.0, matched=0.75, uncovered=NULL)
    result = annotation_resolver.get_adjacent_annotations(
        session=db_session,
        sample_id=matched_stub.gt_annotation_id,
        filters=filters,
        order_by=order_by,
    )

    assert result is not None
    assert result.previous_sample_id == unmatched_stub.gt_annotation_id
    assert result.sample_id == matched_stub.gt_annotation_id
    assert result.next_sample_id == uncovered.sample_id
    assert result.current_sample_position == 2
    assert result.total_count == 3
