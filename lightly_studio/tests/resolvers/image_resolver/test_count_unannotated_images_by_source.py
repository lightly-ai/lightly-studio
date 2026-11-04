from __future__ import annotations

from sqlmodel import Session

from lightly_studio.models.collection import CollectionCreate, SampleType
from lightly_studio.resolvers import collection_resolver, image_resolver, tag_resolver
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


def test_count_unannotated_images_by_source(db_session: Session) -> None:
    collection_id = create_collection(session=db_session).collection_id
    label = create_annotation_label(
        session=db_session, root_collection_id=collection_id, label_name="car"
    )
    images = [
        create_image(
            session=db_session, collection_id=collection_id, file_path_abs=f"/path/{name}.png"
        )
        for name in ("a", "b", "c")
    ]
    labels_source = create_annotations(
        session=db_session,
        collection_id=collection_id,
        annotations=[
            AnnotationDetails(
                sample_id=image.sample_id, annotation_label_id=label.annotation_label_id
            )
            for image in images[:2]
        ],
        collection_name="labels",
    )
    model_source = create_annotations(
        session=db_session,
        collection_id=collection_id,
        annotations=[
            AnnotationDetails(
                sample_id=images[0].sample_id, annotation_label_id=label.annotation_label_id
            )
        ],
        collection_name="model_v1",
    )

    counts = image_resolver.count_unannotated_images_by_source(
        session=db_session, collection_id=collection_id
    )

    assert {
        row.annotation_collection_id: (row.current_count, row.total_count) for row in counts
    } == {
        labels_source[0].annotation_collection_id: (1, 1),
        model_source[0].annotation_collection_id: (2, 2),
    }


def test_count_unannotated_images_by_source__tag_filter_lowers_current_not_total(
    db_session: Session,
) -> None:
    collection_id = create_collection(session=db_session).collection_id
    label = create_annotation_label(
        session=db_session, root_collection_id=collection_id, label_name="car"
    )
    image_a = create_image(
        session=db_session, collection_id=collection_id, file_path_abs="/path/a.png"
    )
    image_b = create_image(
        session=db_session, collection_id=collection_id, file_path_abs="/path/b.png"
    )
    create_image(session=db_session, collection_id=collection_id, file_path_abs="/path/c.png")
    source = create_annotations(
        session=db_session,
        collection_id=collection_id,
        annotations=[
            AnnotationDetails(
                sample_id=image_a.sample_id, annotation_label_id=label.annotation_label_id
            )
        ],
        collection_name="labels",
    )
    tag = create_tag(session=db_session, collection_id=collection_id, tag_name="tagged")
    tag_resolver.add_sample_ids_to_tag_id(
        session=db_session, tag_id=tag.tag_id, sample_ids=[image_b.sample_id]
    )

    counts = image_resolver.count_unannotated_images_by_source(
        session=db_session,
        collection_id=collection_id,
        image_filter=ImageFilter(sample_filter=SampleFilter(tag_ids=[tag.tag_id])),
    )

    assert len(counts) == 1
    assert counts[0].annotation_collection_id == source[0].annotation_collection_id
    assert (counts[0].current_count, counts[0].total_count) == (1, 2)


def test_count_unannotated_images_by_source__source_without_annotations_has_row(
    db_session: Session,
) -> None:
    collection_id = create_collection(session=db_session).collection_id
    create_image(session=db_session, collection_id=collection_id, file_path_abs="/path/a.png")
    empty_source = collection_resolver.create(
        session=db_session,
        collection=CollectionCreate(
            name="empty",
            sample_type=SampleType.ANNOTATION,
            parent_collection_id=collection_id,
        ),
    )

    counts = image_resolver.count_unannotated_images_by_source(
        session=db_session, collection_id=collection_id
    )

    assert [
        (row.annotation_collection_id, row.current_count, row.total_count) for row in counts
    ] == [(empty_source.collection_id, 1, 1)]
