from __future__ import annotations

from uuid import UUID

import pytest
from sqlmodel import Session

from lightly_studio.models.annotation.annotation_base import AnnotationBaseTable
from lightly_studio.models.collection import SampleType
from lightly_studio.resolvers import annotation_resolver, collection_resolver
from lightly_studio.resolvers.annotation_resolver import EmbeddingCoverage
from lightly_studio.resolvers.annotations.annotations_filter import AnnotationsFilter
from tests.helpers_resolvers import (
    create_annotation,
    create_annotation_label,
    create_collection,
    create_embedding_model,
    create_image,
    create_sample_embedding,
)


def test_count_embedding_coverage(db_session: Session) -> None:
    annotation_collection_id, cats, _dog = _create_annotations(session=db_session)

    coverage = annotation_resolver.count_embedding_coverage(
        session=db_session, collection_id=annotation_collection_id
    )
    assert coverage == EmbeddingCoverage(embedded_count=2, total_count=3)

    # The label filter applies, and has_embedding is ignored.
    coverage = annotation_resolver.count_embedding_coverage(
        session=db_session,
        collection_id=annotation_collection_id,
        filters=AnnotationsFilter(
            annotation_label_ids=[cats[0].annotation_label_id], has_embedding=False
        ),
    )
    assert coverage == EmbeddingCoverage(embedded_count=1, total_count=2)


@pytest.mark.parametrize(
    ("has_embedding", "expected_names"), [(True, ["cat_0", "dog"]), (False, ["cat_1"])]
)
def test_get_sample_ids__has_embedding_filter(
    db_session: Session, has_embedding: bool, expected_names: list[str]
) -> None:
    annotation_collection_id, cats, dog = _create_annotations(session=db_session)
    by_name = {"cat_0": cats[0].sample_id, "cat_1": cats[1].sample_id, "dog": dog.sample_id}

    sample_ids = annotation_resolver.get_sample_ids(
        session=db_session,
        collection_id=annotation_collection_id,
        filters=AnnotationsFilter(has_embedding=has_embedding),
    )

    assert sample_ids == {by_name[name] for name in expected_names}


def _create_annotations(
    session: Session,
) -> tuple[UUID, list[AnnotationBaseTable], AnnotationBaseTable]:
    """Create two cats and a dog. The first cat and the dog have an embedding."""
    collection = create_collection(session=session)
    image = create_image(session=session, collection_id=collection.collection_id)
    cat_label = create_annotation_label(
        session=session, root_collection_id=collection.collection_id, label_name="cat"
    )
    dog_label = create_annotation_label(
        session=session, root_collection_id=collection.collection_id, label_name="dog"
    )
    cats = [
        create_annotation(
            session=session,
            collection_id=collection.collection_id,
            sample_id=image.sample_id,
            annotation_label_id=cat_label.annotation_label_id,
        )
        for _ in range(2)
    ]
    dog = create_annotation(
        session=session,
        collection_id=collection.collection_id,
        sample_id=image.sample_id,
        annotation_label_id=dog_label.annotation_label_id,
    )
    annotation_collection_id = collection_resolver.get_or_create_child_collection(
        session=session, collection_id=collection.collection_id, sample_type=SampleType.ANNOTATION
    )
    model = create_embedding_model(
        session=session, collection_id=annotation_collection_id, embedding_dimension=2
    )
    for annotation in [cats[0], dog]:
        create_sample_embedding(
            session=session,
            sample_id=annotation.sample_id,
            embedding_model_id=model.embedding_model_id,
            embedding=[1.0, 0.0],
        )
    return annotation_collection_id, cats, dog
