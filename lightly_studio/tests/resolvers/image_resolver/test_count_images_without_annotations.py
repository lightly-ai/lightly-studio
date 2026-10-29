from __future__ import annotations

from sqlmodel import Session

from lightly_studio.resolvers import image_resolver, tag_resolver
from lightly_studio.resolvers.annotations.annotations_filter import AnnotationsFilter
from lightly_studio.resolvers.image_filter import ImageFilter
from lightly_studio.resolvers.sample_resolver.sample_filter import SampleFilter
from tests.helpers_resolvers import (
    create_annotation,
    create_annotation_label,
    create_collection,
    create_image,
    create_tag,
)


def test_count_images_without_annotations(db_session: Session) -> None:
    collection_id = create_collection(session=db_session).collection_id
    cat = create_annotation_label(
        session=db_session, root_collection_id=collection_id, label_name="cat"
    )
    annotated = create_image(session=db_session, collection_id=collection_id, file_path_abs="/a")
    create_image(session=db_session, collection_id=collection_id, file_path_abs="/b")
    create_image(session=db_session, collection_id=collection_id, file_path_abs="/c")
    create_annotation(
        session=db_session,
        collection_id=collection_id,
        sample_id=annotated.sample_id,
        annotation_label_id=cat.annotation_label_id,
    )

    counts = image_resolver.count_images_without_annotations(
        session=db_session, collection_id=collection_id
    )

    assert counts == (2, 2)


def test_count_images_without_annotations__with_filter(db_session: Session) -> None:
    collection_id = create_collection(session=db_session).collection_id
    cat = create_annotation_label(
        session=db_session, root_collection_id=collection_id, label_name="cat"
    )
    in_source_a = create_image(session=db_session, collection_id=collection_id, file_path_abs="/a")
    in_source_b = create_image(session=db_session, collection_id=collection_id, file_path_abs="/b")
    unannotated = create_image(session=db_session, collection_id=collection_id, file_path_abs="/c")
    annotation_a = create_annotation(
        session=db_session,
        collection_id=collection_id,
        sample_id=in_source_a.sample_id,
        annotation_label_id=cat.annotation_label_id,
        annotation_collection_name="source_a",
    )
    create_annotation(
        session=db_session,
        collection_id=collection_id,
        sample_id=in_source_b.sample_id,
        annotation_label_id=cat.annotation_label_id,
        annotation_collection_name="source_b",
    )
    tag = create_tag(session=db_session, collection_id=collection_id, tag_name="picked")
    tag_resolver.add_sample_ids_to_tag_id(
        session=db_session, tag_id=tag.tag_id, sample_ids=[unannotated.sample_id]
    )

    # In source A, images "/b" and "/c" have no annotations. Only "/c" has the tag.
    # The selected class does not reduce the count.
    counts = image_resolver.count_images_without_annotations(
        session=db_session,
        collection_id=collection_id,
        image_filter=ImageFilter(
            sample_filter=SampleFilter(
                tag_ids=[tag.tag_id],
                annotations_filter=AnnotationsFilter(
                    collection_ids=[annotation_a.annotation_collection_id],
                    annotation_label_ids=[cat.annotation_label_id],
                ),
            )
        ),
    )

    assert counts == (1, 2)
