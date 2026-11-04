from __future__ import annotations

from sqlmodel import Session

from lightly_studio.resolvers import image_resolver, tag_resolver
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


def test_count_image_annotations_by_pair__shared_class_in_two_sources(
    db_session: Session,
) -> None:
    collection_id = create_collection(session=db_session).collection_id
    car_label = create_annotation_label(
        session=db_session, root_collection_id=collection_id, label_name="car"
    )
    image_a = create_image(
        session=db_session, collection_id=collection_id, file_path_abs="/path/a.png"
    )
    image_b = create_image(
        session=db_session, collection_id=collection_id, file_path_abs="/path/b.png"
    )
    source_a = create_annotations(
        session=db_session,
        collection_id=collection_id,
        annotations=[
            AnnotationDetails(
                sample_id=image_a.sample_id, annotation_label_id=car_label.annotation_label_id
            ),
            AnnotationDetails(
                sample_id=image_b.sample_id, annotation_label_id=car_label.annotation_label_id
            ),
        ],
        collection_name="source_a",
    )
    source_b = create_annotations(
        session=db_session,
        collection_id=collection_id,
        annotations=[
            AnnotationDetails(
                sample_id=image_a.sample_id, annotation_label_id=car_label.annotation_label_id
            ),
        ],
        collection_name="source_b",
    )

    counts = image_resolver.count_image_annotations_by_pair(
        session=db_session, collection_id=collection_id
    )

    assert {
        (row.annotation_collection_id, row.label_name): (row.current_count, row.total_count)
        for row in counts
    } == {
        (source_a[0].annotation_collection_id, "car"): (2, 2),
        (source_b[0].annotation_collection_id, "car"): (1, 1),
    }
    assert len(counts) == 2
    assert {row.annotation_label_id for row in counts} == {car_label.annotation_label_id}


def test_count_image_annotations_by_pair__tag_filter_lowers_current_not_total(
    db_session: Session,
) -> None:
    collection_id = create_collection(session=db_session).collection_id
    car_label = create_annotation_label(
        session=db_session, root_collection_id=collection_id, label_name="car"
    )
    image_a = create_image(
        session=db_session, collection_id=collection_id, file_path_abs="/path/a.png"
    )
    image_b = create_image(
        session=db_session, collection_id=collection_id, file_path_abs="/path/b.png"
    )
    annotations = create_annotations(
        session=db_session,
        collection_id=collection_id,
        annotations=[
            AnnotationDetails(
                sample_id=image_a.sample_id, annotation_label_id=car_label.annotation_label_id
            ),
            AnnotationDetails(
                sample_id=image_b.sample_id, annotation_label_id=car_label.annotation_label_id
            ),
        ],
        collection_name="source_a",
    )
    tag = create_tag(session=db_session, collection_id=collection_id, tag_name="tagged")
    tag_resolver.add_sample_ids_to_tag_id(
        session=db_session, tag_id=tag.tag_id, sample_ids=[image_a.sample_id]
    )

    counts = image_resolver.count_image_annotations_by_pair(
        session=db_session,
        collection_id=collection_id,
        image_filter=ImageFilter(sample_filter=SampleFilter(tag_ids=[tag.tag_id])),
    )

    assert len(counts) == 1
    assert counts[0].annotation_collection_id == annotations[0].annotation_collection_id
    assert (counts[0].current_count, counts[0].total_count) == (1, 2)
