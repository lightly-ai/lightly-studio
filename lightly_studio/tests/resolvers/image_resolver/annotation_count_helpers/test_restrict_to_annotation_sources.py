from __future__ import annotations

from uuid import UUID

from sqlmodel import Session, col, select
from sqlmodel.sql.expression import Select

from lightly_studio.models.annotation.annotation_base import AnnotationBaseTable
from lightly_studio.models.annotation_label import AnnotationLabelTable
from lightly_studio.resolvers.image_resolver import annotation_count_helpers
from tests.helpers_resolvers import (
    AnnotationDetails,
    create_annotation_label,
    create_annotations,
    create_collection,
    create_image,
)


def test_restrict_to_annotation_sources__excludes_other_sources(db_session: Session) -> None:
    collection = create_collection(session=db_session)
    collection_id = collection.collection_id
    image = create_image(session=db_session, collection_id=collection_id)
    dog = create_annotation_label(
        session=db_session, root_collection_id=collection_id, label_name="dog"
    )
    cat = create_annotation_label(
        session=db_session, root_collection_id=collection_id, label_name="cat"
    )
    source_a = create_annotations(
        session=db_session,
        collection_id=collection_id,
        annotations=[
            AnnotationDetails(
                sample_id=image.sample_id, annotation_label_id=dog.annotation_label_id
            )
        ],
        collection_name="source-a",
    )
    create_annotations(
        session=db_session,
        collection_id=collection_id,
        annotations=[
            AnnotationDetails(
                sample_id=image.sample_id, annotation_label_id=cat.annotation_label_id
            )
        ],
        collection_name="source-b",
    )
    base_query: Select[tuple[str, UUID]] = select(
        AnnotationLabelTable.annotation_label_name,
        AnnotationBaseTable.annotation_label_id,
    ).join(
        AnnotationBaseTable,
        col(AnnotationBaseTable.annotation_label_id)
        == col(AnnotationLabelTable.annotation_label_id),
    )

    restricted: Select[tuple[str, UUID]] = annotation_count_helpers.restrict_to_annotation_sources(
        query=base_query,
        annotation_collection_ids=[source_a[0].annotation_collection_id],
    )

    labels = [row[0] for row in db_session.exec(restricted).all()]
    assert labels == ["dog"]
