from __future__ import annotations

import uuid
from uuid import UUID

import pytest
from sqlmodel import Session

from lightly_studio.models.annotation.annotation_base import AnnotationType
from lightly_studio.models.embedding_region import EmbeddingRegion, Point2D
from lightly_studio.resolvers import image_resolver, tag_resolver
from lightly_studio.resolvers.annotations.annotations_filter import AnnotationsFilter
from lightly_studio.resolvers.image_filter import ImageFilter
from lightly_studio.resolvers.image_resolver import annotation_count_helpers
from lightly_studio.resolvers.image_resolver.annotation_count_types import (
    AnnotationCountMode,
)
from lightly_studio.resolvers.sample_resolver.sample_filter import SampleFilter
from tests.helpers_resolvers import (
    AnnotationDetails,
    create_annotation_label,
    create_annotations,
    create_collection,
    create_image,
    create_tag,
)
from tests.resolvers.image_resolver import annotation_count_cases
from tests.resolvers.image_resolver.annotation_count_cases import BuildFilter


def test_count_image_annotations_by_sample_tags__overlap_order_and_zero_fill(
    db_session: Session,
) -> None:
    collection = create_collection(session=db_session)
    collection_id = collection.collection_id
    image_a = create_image(session=db_session, collection_id=collection_id, file_path_abs="a.png")
    image_b = create_image(session=db_session, collection_id=collection_id, file_path_abs="b.png")
    image_c = create_image(session=db_session, collection_id=collection_id, file_path_abs="c.png")
    cat = create_annotation_label(
        session=db_session, root_collection_id=collection_id, label_name="cat"
    )
    dog = create_annotation_label(
        session=db_session, root_collection_id=collection_id, label_name="dog"
    )
    create_annotations(
        session=db_session,
        collection_id=collection_id,
        annotations=[
            AnnotationDetails(
                sample_id=image_a.sample_id,
                annotation_label_id=dog.annotation_label_id,
            ),
            AnnotationDetails(
                sample_id=image_a.sample_id,
                annotation_label_id=dog.annotation_label_id,
            ),
            AnnotationDetails(
                sample_id=image_b.sample_id,
                annotation_label_id=cat.annotation_label_id,
            ),
            AnnotationDetails(
                sample_id=image_c.sample_id,
                annotation_label_id=dog.annotation_label_id,
            ),
        ],
    )
    tag_ab = create_tag(session=db_session, collection_id=collection_id, tag_name="a-and-b")
    tag_bc = create_tag(session=db_session, collection_id=collection_id, tag_name="b-and-c")
    empty_tag = create_tag(session=db_session, collection_id=collection_id, tag_name="empty")
    tag_resolver.add_sample_ids_to_tag_id(
        session=db_session,
        tag_id=tag_ab.tag_id,
        sample_ids=[image_a.sample_id, image_b.sample_id],
    )
    tag_resolver.add_sample_ids_to_tag_id(
        session=db_session,
        tag_id=tag_bc.tag_id,
        sample_ids=[image_b.sample_id, image_c.sample_id],
    )

    result = image_resolver.count_image_annotations_by_sample_tags(
        session=db_session,
        collection_id=collection_id,
        sample_tag_ids=[tag_bc.tag_id, empty_tag.tag_id, tag_ab.tag_id],
    )

    assert [series.sample_tag_id for series in result] == [
        tag_bc.tag_id,
        empty_tag.tag_id,
        tag_ab.tag_id,
    ]
    assert [[(row.label_name, row.count) for row in series.counts] for series in result] == [
        [("cat", 1), ("dog", 1)],
        [("cat", 0), ("dog", 0)],
        [("cat", 1), ("dog", 2)],
    ]


def test_count_image_annotations_by_sample_tags__samples_mode_and_active_tag_filter(
    db_session: Session,
) -> None:
    collection = create_collection(session=db_session)
    collection_id = collection.collection_id
    image_a = create_image(session=db_session, collection_id=collection_id, file_path_abs="a.png")
    image_b = create_image(session=db_session, collection_id=collection_id, file_path_abs="b.png")
    dog = create_annotation_label(
        session=db_session, root_collection_id=collection_id, label_name="dog"
    )
    create_annotations(
        session=db_session,
        collection_id=collection_id,
        annotations=[
            AnnotationDetails(
                sample_id=image_a.sample_id,
                annotation_label_id=dog.annotation_label_id,
            ),
            AnnotationDetails(
                sample_id=image_a.sample_id,
                annotation_label_id=dog.annotation_label_id,
            ),
            AnnotationDetails(
                sample_id=image_b.sample_id,
                annotation_label_id=dog.annotation_label_id,
            ),
        ],
    )
    comparison_tag = create_tag(
        session=db_session, collection_id=collection_id, tag_name="comparison"
    )
    active_tag = create_tag(session=db_session, collection_id=collection_id, tag_name="active")
    tag_resolver.add_sample_ids_to_tag_id(
        session=db_session,
        tag_id=comparison_tag.tag_id,
        sample_ids=[image_a.sample_id, image_b.sample_id],
    )
    tag_resolver.add_sample_ids_to_tag_id(
        session=db_session,
        tag_id=active_tag.tag_id,
        sample_ids=[image_a.sample_id],
    )

    result = image_resolver.count_image_annotations_by_sample_tags(
        session=db_session,
        collection_id=collection_id,
        sample_tag_ids=[comparison_tag.tag_id],
        image_filter=ImageFilter(sample_filter=SampleFilter(tag_ids=[active_tag.tag_id])),
        count_mode=AnnotationCountMode.SAMPLES,
    )

    assert [(row.label_name, row.count) for row in result[0].counts] == [("dog", 1)]


def test_count_image_annotations_by_sample_tags__annotation_source_and_type_scope(
    db_session: Session,
) -> None:
    collection = create_collection(session=db_session)
    collection_id = collection.collection_id
    image = create_image(session=db_session, collection_id=collection_id)
    scene = create_annotation_label(
        session=db_session, root_collection_id=collection_id, label_name="scene"
    )
    dog = create_annotation_label(
        session=db_session, root_collection_id=collection_id, label_name="dog"
    )
    source_a = create_annotations(
        session=db_session,
        collection_id=collection_id,
        annotations=[
            AnnotationDetails(
                sample_id=image.sample_id,
                annotation_label_id=scene.annotation_label_id,
                annotation_type=AnnotationType.CLASSIFICATION,
            )
        ],
        collection_name="source-a",
    )
    create_annotations(
        session=db_session,
        collection_id=collection_id,
        annotations=[
            AnnotationDetails(
                sample_id=image.sample_id,
                annotation_label_id=dog.annotation_label_id,
                annotation_type=AnnotationType.OBJECT_DETECTION,
            )
        ],
        collection_name="source-b",
    )
    tag = create_tag(session=db_session, collection_id=collection_id)
    tag_resolver.add_sample_ids_to_tag_id(
        session=db_session,
        tag_id=tag.tag_id,
        sample_ids=[image.sample_id],
    )

    result = image_resolver.count_image_annotations_by_sample_tags(
        session=db_session,
        collection_id=collection_id,
        sample_tag_ids=[tag.tag_id],
        image_filter=ImageFilter(
            sample_filter=SampleFilter(
                annotations_filter=AnnotationsFilter(
                    collection_ids=[source_a[0].annotation_collection_id]
                )
            )
        ),
        annotation_type=AnnotationType.CLASSIFICATION,
    )

    assert [(row.label_name, row.count) for row in result[0].counts] == [("scene", 1)]


@pytest.mark.parametrize("invalid_tag_case", ["missing", "foreign"])
def test_count_image_annotations_by_sample_tags__rejects_invalid_tags(
    db_session: Session,
    invalid_tag_case: str,
) -> None:
    collection = create_collection(session=db_session)
    invalid_tag_id = _create_invalid_tag_id(
        session=db_session,
        invalid_tag_case=invalid_tag_case,
    )

    with pytest.raises(ValueError, match="must belong to collection"):
        image_resolver.count_image_annotations_by_sample_tags(
            session=db_session,
            collection_id=collection.collection_id,
            sample_tag_ids=[invalid_tag_id],
        )


def test_count_image_annotations_by_sample_tags__empty_selection(db_session: Session) -> None:
    collection = create_collection(session=db_session)

    result = image_resolver.count_image_annotations_by_sample_tags(
        session=db_session,
        collection_id=collection.collection_id,
        sample_tag_ids=[],
    )

    assert result == []


def _create_invalid_tag_id(
    session: Session,
    invalid_tag_case: str,
) -> UUID:
    if invalid_tag_case == "missing":
        return uuid.uuid4()
    foreign_collection = create_collection(session=session)
    return create_tag(session=session, collection_id=foreign_collection.collection_id).tag_id


@pytest.mark.parametrize("count_mode", [AnnotationCountMode.OBJECTS, AnnotationCountMode.SAMPLES])
@pytest.mark.parametrize("annotation_type", [None, AnnotationType.OBJECT_DETECTION])
@pytest.mark.parametrize("build_filter", annotation_count_cases.BUILD_FILTERS)
def test_count_image_annotations_by_sample_tags__matches_unstripped_counts(
    db_session: Session,
    build_filter: BuildFilter,
    annotation_type: AnnotationType | None,
    count_mode: AnnotationCountMode,
) -> None:
    data = annotation_count_cases.create_count_data(session=db_session)
    # The helpers on an unstripped filter still add the parent IN.
    expected_filter = build_filter(data)
    annotation_collection_ids = annotation_count_helpers.get_annotation_collection_ids(
        image_filter=expected_filter
    )
    class_names = list(
        annotation_count_helpers.get_total_counts(
            session=db_session,
            collection_id=data.collection_id,
            annotation_type=annotation_type,
            count_mode=count_mode,
            annotation_collection_ids=annotation_collection_ids,
        )
    )
    grouped_counts = annotation_count_helpers.get_counts_grouped_by_sample_tag(
        session=db_session,
        collection_id=data.collection_id,
        sample_tag_ids=data.image_tag_ids,
        image_filter=expected_filter,
        annotation_type=annotation_type,
        annotation_collection_ids=annotation_collection_ids,
        count_mode=count_mode,
    )
    expected = annotation_count_helpers.build_sample_tag_counts(
        sample_tag_ids=data.image_tag_ids,
        sample_tags=annotation_count_helpers.get_and_validate_sample_tags(
            session=db_session,
            collection_id=data.collection_id,
            sample_tag_ids=data.image_tag_ids,
        ),
        class_names=class_names,
        grouped_counts=grouped_counts,
    )

    result = image_resolver.count_image_annotations_by_sample_tags(
        session=db_session,
        collection_id=data.collection_id,
        sample_tag_ids=data.image_tag_ids,
        image_filter=build_filter(data),
        annotation_type=annotation_type,
        count_mode=count_mode,
    )

    assert class_names
    assert result == expected


@pytest.mark.parametrize(("group", "build_filter"), annotation_count_cases.CASES)
def test_count_image_annotations_by_sample_tags__parent_in_only_when_needed(
    db_session: Session, group: str, build_filter: BuildFilter
) -> None:
    data = annotation_count_cases.create_count_data(session=db_session)

    with annotation_count_cases.record_statements(session=db_session) as statements:
        image_resolver.count_image_annotations_by_sample_tags(
            session=db_session,
            collection_id=data.collection_id,
            sample_tag_ids=data.image_tag_ids,
            image_filter=build_filter(data),
        )

    has_parent_in = any(annotation_count_cases.PARENT_IN_MARKER in s for s in statements)
    assert has_parent_in == (group == "keep")


def test_count_image_annotations_by_sample_tags__sources_with_embedding_region(
    db_session: Session,
) -> None:
    collection_id, images = annotation_count_cases.create_images_in_plot(
        session=db_session, coordinates=[(1.0, 1.0), (5.0, 5.0), (100.0, 100.0)]
    )
    car = create_annotation_label(
        session=db_session, root_collection_id=collection_id, label_name="car"
    )
    source = create_annotations(
        session=db_session,
        collection_id=collection_id,
        annotations=[
            AnnotationDetails(
                sample_id=image.sample_id, annotation_label_id=car.annotation_label_id
            )
            for image in images
        ],
        collection_name="source",
    )
    all_images_tag = create_tag(session=db_session, collection_id=collection_id, tag_name="all")
    tag_resolver.add_sample_ids_to_tag_id(
        session=db_session,
        tag_id=all_images_tag.tag_id,
        sample_ids=[image.sample_id for image in images],
    )

    # The square encloses the first two plot points, but not (100, 100).
    region = EmbeddingRegion(
        polygon=[Point2D(x=0, y=0), Point2D(x=10, y=0), Point2D(x=10, y=10), Point2D(x=0, y=10)]
    )
    result = image_resolver.count_image_annotations_by_sample_tags(
        session=db_session,
        collection_id=collection_id,
        sample_tag_ids=[all_images_tag.tag_id],
        image_filter=ImageFilter(
            sample_filter=SampleFilter(
                embedding_region=region,
                annotations_filter=AnnotationsFilter(
                    collection_ids=[source[0].annotation_collection_id]
                ),
            )
        ),
    )

    assert [[(row.label_name, row.count) for row in series.counts] for series in result] == [
        [("car", 2)]
    ]
