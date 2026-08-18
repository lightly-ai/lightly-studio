from __future__ import annotations

from uuid import UUID, uuid4

import pytest
from lightly_studio.resolvers.image_resolver.annotation_count_types import (
    AnnotationCountMode,
)
from sqlmodel import Session

from lightly_studio.models.annotation.annotation_base import AnnotationType
from lightly_studio.resolvers import image_resolver, tag_resolver
from lightly_studio.resolvers.annotations.annotations_filter import AnnotationsFilter
from lightly_studio.resolvers.image_filter import ImageFilter
from lightly_studio.resolvers.sample_resolver.sample_filter import SampleFilter
from tests.helpers_resolvers import (
    AnnotationDetails,
    create_annotation_label,
    create_annotations,
    create_collection,
    create_image,
    create_tag,
)


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


@pytest.mark.parametrize("invalid_tag_kind", ["missing", "foreign", "annotation"])
def test_count_image_annotations_by_sample_tags__rejects_invalid_tags(
    db_session: Session,
    invalid_tag_kind: str,
) -> None:
    collection = create_collection(session=db_session)
    invalid_tag_id = _create_invalid_tag_id(
        session=db_session,
        collection_id=collection.collection_id,
        invalid_tag_kind=invalid_tag_kind,
    )

    with pytest.raises(ValueError, match="must be sample tags belonging to collection"):
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
    collection_id: UUID,
    invalid_tag_kind: str,
) -> UUID:
    if invalid_tag_kind == "missing":
        return uuid4()
    if invalid_tag_kind == "annotation":
        return create_tag(
            session=session,
            collection_id=collection_id,
            kind="annotation",
        ).tag_id
    foreign_collection = create_collection(session=session)
    return create_tag(session=session, collection_id=foreign_collection.collection_id).tag_id
