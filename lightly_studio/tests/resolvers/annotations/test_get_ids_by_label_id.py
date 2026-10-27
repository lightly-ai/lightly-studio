from __future__ import annotations

from sqlmodel import Session

from lightly_studio.resolvers import annotation_resolver
from tests.helpers_resolvers import (
    create_annotation,
    create_annotation_label,
    create_collection,
    create_image,
)


def test_get_ids_by_label_id(db_session: Session) -> None:
    collection_id = create_collection(session=db_session).collection_id
    image_id = create_image(session=db_session, collection_id=collection_id).sample_id
    cat = create_annotation_label(
        session=db_session, root_collection_id=collection_id, label_name="cat"
    )
    dog = create_annotation_label(
        session=db_session, root_collection_id=collection_id, label_name="dog"
    )
    cat_annotations = [
        create_annotation(
            session=db_session,
            collection_id=collection_id,
            sample_id=image_id,
            annotation_label_id=cat.annotation_label_id,
        )
        for _ in range(2)
    ]
    create_annotation(
        session=db_session,
        collection_id=collection_id,
        sample_id=image_id,
        annotation_label_id=dog.annotation_label_id,
    )

    ids = annotation_resolver.get_ids_by_label_id(
        session=db_session, label_id=cat.annotation_label_id
    )

    assert set(ids) == {annotation.sample_id for annotation in cat_annotations}
