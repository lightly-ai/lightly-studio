"""Tests for deep_copy_subset resolver."""

import uuid

import pytest
from sqlmodel import Session

from lightly_studio.models.annotation.annotation_base import AnnotationType
from lightly_studio.resolvers import (
    annotation_resolver,
    dataset_resolver,
    embedding_model_resolver,
    image_resolver,
    sample_embedding_resolver,
    sample_resolver,
)
from lightly_studio.resolvers.annotations.annotations_filter import AnnotationsFilter
from tests.helpers_resolvers import (
    create_annotation,
    create_annotation_label,
    create_collection,
    create_embedding_model,
    create_image,
    create_sample_embedding,
)


def test_deep_copy_subset__keeps_only_selected_images(db_session: Session) -> None:
    # Arrange
    original = create_collection(session=db_session, collection_name="original")
    img1 = create_image(
        session=db_session, collection_id=original.collection_id, file_path_abs="/a.png"
    )
    img2 = create_image(
        session=db_session, collection_id=original.collection_id, file_path_abs="/b.png"
    )
    create_image(session=db_session, collection_id=original.collection_id, file_path_abs="/c.png")

    # Act
    copied = dataset_resolver.deep_copy_subset(
        session=db_session,
        dataset_id=original.dataset_id,
        copy_name="copied",
        sample_ids=[img1.sample_id, img2.sample_id],
    )

    # Assert - only the selected images are in the copy.
    copied_images = image_resolver.get_all_by_collection_id(
        session=db_session,
        collection_id=copied.collection_id,
    )
    copied_paths = {s.file_path_abs for s in copied_images.samples}
    assert copied_paths == {"/a.png", "/b.png"}


def test_deep_copy_subset__empty_selection_copies_no_samples(db_session: Session) -> None:
    # Arrange
    original = create_collection(session=db_session, collection_name="original")
    create_image(session=db_session, collection_id=original.collection_id, file_path_abs="/a.png")

    # Act
    copied = dataset_resolver.deep_copy_subset(
        session=db_session,
        dataset_id=original.dataset_id,
        copy_name="copied",
        sample_ids=[],
    )

    # Assert - the new dataset exists but has no samples.
    copied_samples = sample_resolver.get_filtered_samples(
        session=db_session,
        collection_id=copied.collection_id,
    )
    assert copied_samples.total_count == 0


def test_deep_copy_subset__unknown_sample_ids_ignored(db_session: Session) -> None:
    # Arrange
    original = create_collection(session=db_session, collection_name="original")
    img = create_image(
        session=db_session, collection_id=original.collection_id, file_path_abs="/a.png"
    )

    # Act - mix of valid and unknown IDs.
    copied = dataset_resolver.deep_copy_subset(
        session=db_session,
        dataset_id=original.dataset_id,
        copy_name="copied",
        sample_ids=[img.sample_id, uuid.uuid4(), uuid.uuid4()],
    )

    # Assert - only the valid image was copied.
    copied_images = image_resolver.get_all_by_collection_id(
        session=db_session,
        collection_id=copied.collection_id,
    )
    assert len(copied_images.samples) == 1


def test_deep_copy_subset__includes_annotations_of_kept_samples(db_session: Session) -> None:
    # Arrange
    original = create_collection(session=db_session, collection_name="original")
    kept = create_image(
        session=db_session, collection_id=original.collection_id, file_path_abs="/kept.png"
    )
    dropped = create_image(
        session=db_session, collection_id=original.collection_id, file_path_abs="/dropped.png"
    )
    label = create_annotation_label(
        session=db_session, root_collection_id=original.collection_id, label_name="cat"
    )
    create_annotation(
        session=db_session,
        collection_id=original.collection_id,
        sample_id=kept.sample_id,
        annotation_label_id=label.annotation_label_id,
        annotation_type=AnnotationType.CLASSIFICATION,
    )
    create_annotation(
        session=db_session,
        collection_id=original.collection_id,
        sample_id=dropped.sample_id,
        annotation_label_id=label.annotation_label_id,
        annotation_type=AnnotationType.CLASSIFICATION,
    )

    # Act - subset includes only the parent image; the annotation must follow.
    copied = dataset_resolver.deep_copy_subset(
        session=db_session,
        dataset_id=original.dataset_id,
        copy_name="copied",
        sample_ids=[kept.sample_id],
    )

    # Assert - only the kept image's annotation made it into the copy.
    result = annotation_resolver.get_all(
        session=db_session,
        filters=AnnotationsFilter(collection_ids=[copied.children[0].collection_id]),
    )
    assert result.total_count == 1


def test_deep_copy_subset__copies_embeddings_for_kept_samples(db_session: Session) -> None:
    # Arrange
    original = create_collection(session=db_session, collection_name="original")
    kept = create_image(
        session=db_session, collection_id=original.collection_id, file_path_abs="/kept.png"
    )
    dropped = create_image(
        session=db_session, collection_id=original.collection_id, file_path_abs="/dropped.png"
    )
    embedding_model = create_embedding_model(
        session=db_session,
        collection_id=original.collection_id,
        embedding_model_name="model",
        embedding_dimension=3,
    )
    create_sample_embedding(
        session=db_session,
        sample_id=kept.sample_id,
        embedding_model_id=embedding_model.embedding_model_id,
        embedding=[1.0, 2.0, 3.0],
    )
    create_sample_embedding(
        session=db_session,
        sample_id=dropped.sample_id,
        embedding_model_id=embedding_model.embedding_model_id,
        embedding=[4.0, 5.0, 6.0],
    )

    # Act
    copied = dataset_resolver.deep_copy_subset(
        session=db_session,
        dataset_id=original.dataset_id,
        copy_name="copied",
        sample_ids=[kept.sample_id],
    )

    # Assert - the embedding model is copied; only the kept embedding follows.
    copied_model_rows = embedding_model_resolver.get_all_by_collection_id(
        session=db_session,
        collection_id=copied.collection_id,
    )
    assert len(copied_model_rows) == 1
    copied_embeddings = sample_embedding_resolver.get_all_by_collection_id(
        session=db_session,
        collection_id=copied.collection_id,
        embedding_model_id=copied_model_rows[0].embedding_model_id,
    )
    assert len(copied_embeddings) == 1
    assert tuple(copied_embeddings[0].embedding) == (1.0, 2.0, 3.0)


def test_deep_copy_subset__original_dataset_unchanged(db_session: Session) -> None:
    # Arrange
    original = create_collection(session=db_session, collection_name="original")
    img1 = create_image(
        session=db_session, collection_id=original.collection_id, file_path_abs="/a.png"
    )
    create_image(session=db_session, collection_id=original.collection_id, file_path_abs="/b.png")

    # Act
    dataset_resolver.deep_copy_subset(
        session=db_session,
        dataset_id=original.dataset_id,
        copy_name="copied",
        sample_ids=[img1.sample_id],
    )

    # Assert - the source dataset is unchanged.
    original_samples = sample_resolver.get_filtered_samples(
        session=db_session,
        collection_id=original.collection_id,
    )
    assert original_samples.total_count == 2


def test_deep_copy_subset__raises_for_nonexistent_dataset(db_session: Session) -> None:
    with pytest.raises(ValueError, match="not found"):
        dataset_resolver.deep_copy_subset(
            session=db_session,
            dataset_id=uuid.uuid4(),
            copy_name="copied",
            sample_ids=[uuid.uuid4()],
        )
