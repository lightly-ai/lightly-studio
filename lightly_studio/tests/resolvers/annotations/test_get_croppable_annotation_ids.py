from __future__ import annotations

from sqlmodel import Session

from lightly_studio.models.annotation.annotation_base import AnnotationType
from lightly_studio.models.collection import SampleType
from lightly_studio.resolvers import annotation_resolver, collection_resolver
from tests.helpers_resolvers import (
    create_annotation,
    create_annotation_label,
    create_collection,
    create_image,
)


def test_get_croppable_annotation_ids__skips_classification_and_orders_by_path(
    db_session: Session,
) -> None:
    collection = create_collection(session=db_session)
    annotation_collection_id = collection_resolver.get_or_create_child_collection(
        session=db_session,
        collection_id=collection.collection_id,
        sample_type=SampleType.ANNOTATION,
    )
    label = create_annotation_label(session=db_session, root_collection_id=collection.collection_id)
    # Created out of path order, so the result order comes from the query, not insertion.
    annotation_ids = {}
    for path in ["/c.png", "/a.png", "/b.png"]:
        image = create_image(
            session=db_session, collection_id=collection.collection_id, file_path_abs=path
        )
        annotation_ids[path] = create_annotation(
            session=db_session,
            collection_id=collection.collection_id,
            sample_id=image.sample_id,
            annotation_label_id=label.annotation_label_id,
        ).sample_id
    classified_image = create_image(
        session=db_session, collection_id=collection.collection_id, file_path_abs="/d.png"
    )
    create_annotation(
        session=db_session,
        collection_id=collection.collection_id,
        sample_id=classified_image.sample_id,
        annotation_label_id=label.annotation_label_id,
        annotation_type=AnnotationType.CLASSIFICATION,
    )

    ids = annotation_resolver.get_croppable_annotation_ids(
        session=db_session, annotation_collection_id=annotation_collection_id
    )

    assert ids == [annotation_ids["/a.png"], annotation_ids["/b.png"], annotation_ids["/c.png"]]
