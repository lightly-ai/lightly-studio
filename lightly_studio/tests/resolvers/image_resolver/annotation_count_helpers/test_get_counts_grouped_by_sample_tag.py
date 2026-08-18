from __future__ import annotations

from sqlmodel import Session

from lightly_studio.resolvers import tag_resolver
from lightly_studio.resolvers.image_resolver import annotation_count_helpers
from lightly_studio.resolvers.image_resolver.annotation_count_types import AnnotationCountMode
from tests.helpers_resolvers import (
    AnnotationDetails,
    create_annotation_label,
    create_annotations,
    create_collection,
    create_image,
    create_tag,
)


def test_get_counts_grouped_by_sample_tag__basic(db_session: Session) -> None:
    collection = create_collection(session=db_session)
    collection_id = collection.collection_id
    image_a = create_image(session=db_session, collection_id=collection_id, file_path_abs="a.png")
    image_b = create_image(session=db_session, collection_id=collection_id, file_path_abs="b.png")
    dog = create_annotation_label(
        session=db_session, root_collection_id=collection_id, label_name="dog"
    )
    cat = create_annotation_label(
        session=db_session, root_collection_id=collection_id, label_name="cat"
    )
    dog_id, cat_id = dog.annotation_label_id, cat.annotation_label_id
    create_annotations(
        session=db_session,
        collection_id=collection_id,
        annotations=[
            AnnotationDetails(sample_id=image_a.sample_id, annotation_label_id=dog_id),
            AnnotationDetails(sample_id=image_b.sample_id, annotation_label_id=cat_id),
        ],
    )
    tag_a = create_tag(session=db_session, collection_id=collection_id, tag_name="tag-a")
    tag_b = create_tag(session=db_session, collection_id=collection_id, tag_name="tag-b")
    tag_resolver.add_sample_ids_to_tag_id(
        session=db_session, tag_id=tag_a.tag_id, sample_ids=[image_a.sample_id]
    )
    tag_resolver.add_sample_ids_to_tag_id(
        session=db_session, tag_id=tag_b.tag_id, sample_ids=[image_b.sample_id]
    )

    result = annotation_count_helpers.get_counts_grouped_by_sample_tag(
        session=db_session,
        collection_id=collection_id,
        sample_tag_ids=[tag_a.tag_id, tag_b.tag_id],
        image_filter=None,
        annotation_type=None,
        annotation_collection_ids=None,
        count_mode=AnnotationCountMode.OBJECTS,
    )

    assert result == {(tag_a.tag_id, "dog"): 1, (tag_b.tag_id, "cat"): 1}


def test_get_counts_grouped_by_sample_tag__samples_mode_deduplicates(db_session: Session) -> None:
    collection = create_collection(session=db_session)
    collection_id = collection.collection_id
    image = create_image(session=db_session, collection_id=collection_id)
    dog = create_annotation_label(
        session=db_session, root_collection_id=collection_id, label_name="dog"
    )
    dog_id = dog.annotation_label_id
    create_annotations(
        session=db_session,
        collection_id=collection_id,
        annotations=[
            AnnotationDetails(sample_id=image.sample_id, annotation_label_id=dog_id),
            AnnotationDetails(sample_id=image.sample_id, annotation_label_id=dog_id),
        ],
    )
    tag = create_tag(session=db_session, collection_id=collection_id)
    tag_resolver.add_sample_ids_to_tag_id(
        session=db_session, tag_id=tag.tag_id, sample_ids=[image.sample_id]
    )

    result = annotation_count_helpers.get_counts_grouped_by_sample_tag(
        session=db_session,
        collection_id=collection_id,
        sample_tag_ids=[tag.tag_id],
        image_filter=None,
        annotation_type=None,
        annotation_collection_ids=None,
        count_mode=AnnotationCountMode.SAMPLES,
    )

    assert result == {(tag.tag_id, "dog"): 1}
