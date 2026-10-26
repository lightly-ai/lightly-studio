from __future__ import annotations

from uuid import UUID

import pytest
from sqlmodel import Session

from lightly_studio.models.annotation.annotation_base import AnnotationType
from lightly_studio.models.collection import SampleType
from lightly_studio.resolvers import annotation_resolver, collection_resolver
from lightly_studio.resolvers.annotation_resolver.update_bounding_box import (
    BoundingBoxCoordinates,
)
from tests.helpers_resolvers import (
    create_annotation,
    create_annotation_label,
    create_collection,
    create_embedding_model,
    create_image,
    create_sample_embedding,
)


def test_get_unembedded_annotation_ids__returns_annotations_without_embeddings(
    db_session: Session,
) -> None:
    """Only object-detection annotations lacking an embedding for the model are returned."""
    collection = create_collection(session=db_session)
    annotation_collection_id = collection_resolver.get_or_create_child_collection(
        session=db_session,
        collection_id=collection.collection_id,
        sample_type=SampleType.ANNOTATION,
    )
    label = create_annotation_label(session=db_session, root_collection_id=collection.collection_id)
    image = create_image(session=db_session, collection_id=collection.collection_id)
    embedded_annotation = create_annotation(
        session=db_session,
        collection_id=collection.collection_id,
        sample_id=image.sample_id,
        annotation_label_id=label.annotation_label_id,
    )
    other_image = create_image(
        session=db_session,
        collection_id=collection.collection_id,
        file_path_abs="/path/to/other.png",
    )
    unembedded_annotation = create_annotation(
        session=db_session,
        collection_id=collection.collection_id,
        sample_id=other_image.sample_id,
        annotation_label_id=label.annotation_label_id,
    )
    embedding_model = create_embedding_model(
        session=db_session, collection_id=annotation_collection_id
    )
    create_sample_embedding(
        session=db_session,
        sample_id=embedded_annotation.sample_id,
        embedding_model_id=embedding_model.embedding_model_id,
        embedding=[0.1, 0.2, 0.3],
    )

    unembedded_ids = annotation_resolver.get_unembedded_annotation_ids(
        session=db_session,
        annotation_collection_id=annotation_collection_id,
        embedding_model_id=embedding_model.embedding_model_id,
    )

    assert unembedded_ids == [unembedded_annotation.sample_id]


def test_get_unembedded_annotation_ids__orders_by_image_path(
    db_session: Session,
) -> None:
    """Results are ordered by source image path so annotations on the same image stay adjacent."""
    collection = create_collection(session=db_session)
    annotation_collection_id = collection_resolver.get_or_create_child_collection(
        session=db_session,
        collection_id=collection.collection_id,
        sample_type=SampleType.ANNOTATION,
    )
    label = create_annotation_label(session=db_session, root_collection_id=collection.collection_id)
    image_b = create_image(
        session=db_session,
        collection_id=collection.collection_id,
        file_path_abs="/path/to/b.png",
    )
    image_a = create_image(
        session=db_session,
        collection_id=collection.collection_id,
        file_path_abs="/path/to/a.png",
    )
    annotation_b = create_annotation(
        session=db_session,
        collection_id=collection.collection_id,
        sample_id=image_b.sample_id,
        annotation_label_id=label.annotation_label_id,
    )
    annotation_a = create_annotation(
        session=db_session,
        collection_id=collection.collection_id,
        sample_id=image_a.sample_id,
        annotation_label_id=label.annotation_label_id,
    )
    embedding_model = create_embedding_model(
        session=db_session, collection_id=annotation_collection_id
    )

    unembedded_ids = annotation_resolver.get_unembedded_annotation_ids(
        session=db_session,
        annotation_collection_id=annotation_collection_id,
        embedding_model_id=embedding_model.embedding_model_id,
    )

    assert unembedded_ids == [annotation_a.sample_id, annotation_b.sample_id]


def test_get_unembedded_annotation_ids__none_model_returns_all_croppable(
    db_session: Session,
) -> None:
    """Without a model every croppable annotation is returned, classifications are not."""
    collection = create_collection(session=db_session)
    annotation_collection_id = collection_resolver.get_or_create_child_collection(
        session=db_session,
        collection_id=collection.collection_id,
        sample_type=SampleType.ANNOTATION,
    )
    label = create_annotation_label(session=db_session, root_collection_id=collection.collection_id)
    image_a = create_image(
        session=db_session, collection_id=collection.collection_id, file_path_abs="/a.png"
    )
    image_b = create_image(
        session=db_session, collection_id=collection.collection_id, file_path_abs="/b.png"
    )
    image_c = create_image(
        session=db_session, collection_id=collection.collection_id, file_path_abs="/c.png"
    )
    detection = create_annotation(
        session=db_session,
        collection_id=collection.collection_id,
        sample_id=image_a.sample_id,
        annotation_label_id=label.annotation_label_id,
        annotation_type=AnnotationType.OBJECT_DETECTION,
    )
    create_annotation(
        session=db_session,
        collection_id=collection.collection_id,
        sample_id=image_b.sample_id,
        annotation_label_id=label.annotation_label_id,
        annotation_type=AnnotationType.CLASSIFICATION,
    )
    embedded_detection = create_annotation(
        session=db_session,
        collection_id=collection.collection_id,
        sample_id=image_c.sample_id,
        annotation_label_id=label.annotation_label_id,
        annotation_type=AnnotationType.OBJECT_DETECTION,
    )
    embedding_model = create_embedding_model(
        session=db_session, collection_id=annotation_collection_id
    )
    create_sample_embedding(
        session=db_session,
        sample_id=embedded_detection.sample_id,
        embedding_model_id=embedding_model.embedding_model_id,
        embedding=[0.1, 0.2, 0.3],
    )

    ids = annotation_resolver.get_unembedded_annotation_ids(
        session=db_session,
        annotation_collection_id=annotation_collection_id,
        embedding_model_id=None,
    )

    assert ids == [detection.sample_id, embedded_detection.sample_id]


def test_get_unembedded_annotation_ids__missing_is_selected(db_session: Session) -> None:
    annotation_collection_id, annotation_id, model_id = _create_embedded_annotation(
        session=db_session, source_fingerprint=None, embed=False
    )

    ids = annotation_resolver.get_unembedded_annotation_ids(
        session=db_session,
        annotation_collection_id=annotation_collection_id,
        embedding_model_id=model_id,
    )

    assert ids == [annotation_id]


@pytest.mark.parametrize(
    "annotation_type",
    [AnnotationType.OBJECT_DETECTION, AnnotationType.SEGMENTATION_MASK],
)
def test_get_unembedded_annotation_ids__matching_fingerprint_not_selected(
    db_session: Session,
    annotation_type: AnnotationType,
) -> None:
    annotation_collection_id, _, model_id = _create_embedded_annotation(
        session=db_session,
        source_fingerprint="bbox1:50,50,20,20",
        annotation_type=annotation_type,
    )

    ids = annotation_resolver.get_unembedded_annotation_ids(
        session=db_session,
        annotation_collection_id=annotation_collection_id,
        embedding_model_id=model_id,
    )

    assert ids == []


@pytest.mark.parametrize(
    "annotation_type",
    [AnnotationType.OBJECT_DETECTION, AnnotationType.SEGMENTATION_MASK],
)
def test_get_unembedded_annotation_ids__edited_box_selected(
    db_session: Session,
    annotation_type: AnnotationType,
) -> None:
    annotation_collection_id, annotation_id, model_id = _create_embedded_annotation(
        session=db_session,
        source_fingerprint="bbox1:50,50,20,20",
        annotation_type=annotation_type,
    )
    annotation_resolver.update_bounding_box(
        session=db_session,
        annotation_id=annotation_id,
        coordinates=BoundingBoxCoordinates(x=60, y=50, width=20, height=20),
    )

    ids = annotation_resolver.get_unembedded_annotation_ids(
        session=db_session,
        annotation_collection_id=annotation_collection_id,
        embedding_model_id=model_id,
    )

    assert ids == [annotation_id]


def test_get_unembedded_annotation_ids__null_fingerprint_not_selected(
    db_session: Session,
) -> None:
    annotation_collection_id, _, model_id = _create_embedded_annotation(
        session=db_session, source_fingerprint=None
    )

    ids = annotation_resolver.get_unembedded_annotation_ids(
        session=db_session,
        annotation_collection_id=annotation_collection_id,
        embedding_model_id=model_id,
    )

    assert ids == []


def _create_embedded_annotation(
    session: Session,
    source_fingerprint: str | None,
    embed: bool = True,
    annotation_type: AnnotationType = AnnotationType.OBJECT_DETECTION,
) -> tuple[UUID, UUID, UUID]:
    """Create a default-box annotation, optionally embedded with the given fingerprint.

    Returns the annotation collection, annotation and embedding model IDs.
    """
    collection = create_collection(session=session)
    annotation_collection_id = collection_resolver.get_or_create_child_collection(
        session=session,
        collection_id=collection.collection_id,
        sample_type=SampleType.ANNOTATION,
    )
    label = create_annotation_label(session=session, root_collection_id=collection.collection_id)
    image = create_image(session=session, collection_id=collection.collection_id)
    annotation = create_annotation(
        session=session,
        collection_id=collection.collection_id,
        sample_id=image.sample_id,
        annotation_label_id=label.annotation_label_id,
        annotation_type=annotation_type,
    )
    embedding_model = create_embedding_model(
        session=session, collection_id=annotation_collection_id
    )
    if embed:
        create_sample_embedding(
            session=session,
            sample_id=annotation.sample_id,
            embedding_model_id=embedding_model.embedding_model_id,
            embedding=[0.1, 0.2, 0.3],
            source_fingerprint=source_fingerprint,
        )
    return (
        annotation_collection_id,
        annotation.sample_id,
        embedding_model.embedding_model_id,
    )
