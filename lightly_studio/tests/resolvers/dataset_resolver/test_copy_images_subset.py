"""Tests for copy_images_subset resolver."""

import uuid

import pytest
from sqlmodel import Session

from lightly_studio.models.annotation.annotation_base import AnnotationType
from lightly_studio.models.collection import SampleType
from lightly_studio.resolvers import (
    annotation_resolver,
    dataset_resolver,
    embedding_model_resolver,
    image_resolver,
    sample_embedding_resolver,
    sample_resolver,
    tag_resolver,
)
from lightly_studio.resolvers.annotations.annotations_filter import AnnotationsFilter
from tests.helpers_resolvers import (
    create_annotation,
    create_annotation_label,
    create_collection,
    create_embedding_model,
    create_image,
    create_sample_embedding,
    create_tag,
)


def test_copy_images_subset__copies_only_selected_image_samples(db_session: Session) -> None:
    # Arrange
    original = create_collection(session=db_session, collection_name="original")
    img1 = create_image(
        session=db_session, collection_id=original.collection_id, file_path_abs="/a.png"
    )
    create_image(session=db_session, collection_id=original.collection_id, file_path_abs="/b.png")

    # Act
    copied = dataset_resolver.copy_images_subset(
        session=db_session,
        dataset_id=original.dataset_id,
        copy_name="copied",
        sample_ids=[img1.sample_id],
    )

    # Assert - only the selected image exists in the new dataset.
    copied_images = image_resolver.get_all_by_collection_id(
        session=db_session,
        collection_id=copied.collection_id,
    )
    paths = [s.file_path_abs for s in copied_images.samples]
    assert paths == ["/a.png"]


def test_copy_images_subset__new_dataset_is_separate(db_session: Session) -> None:
    # Arrange
    original = create_collection(session=db_session, collection_name="original")
    img = create_image(
        session=db_session, collection_id=original.collection_id, file_path_abs="/a.png"
    )

    # Act
    copied = dataset_resolver.copy_images_subset(
        session=db_session,
        dataset_id=original.dataset_id,
        copy_name="copied",
        sample_ids=[img.sample_id],
    )

    # Assert - new dataset has a different ID and is a root collection.
    assert copied.dataset_id != original.dataset_id
    assert copied.collection_id != original.collection_id
    assert copied.parent_collection_id is None


def test_copy_images_subset__does_not_copy_annotations(db_session: Session) -> None:
    # Arrange
    original = create_collection(session=db_session, collection_name="original")
    img = create_image(
        session=db_session, collection_id=original.collection_id, file_path_abs="/a.png"
    )
    label = create_annotation_label(
        session=db_session, root_collection_id=original.collection_id, label_name="cat"
    )
    create_annotation(
        session=db_session,
        collection_id=original.collection_id,
        sample_id=img.sample_id,
        annotation_label_id=label.annotation_label_id,
        annotation_type=AnnotationType.CLASSIFICATION,
    )

    # Act
    copied = dataset_resolver.copy_images_subset(
        session=db_session,
        dataset_id=original.dataset_id,
        copy_name="copied",
        sample_ids=[img.sample_id],
    )

    # Assert - no annotations in the new dataset.
    copied_child_collection_ids = [c.collection_id for c in copied.children]
    result = annotation_resolver.get_all(
        session=db_session,
        filters=AnnotationsFilter(
            collection_ids=copied_child_collection_ids + [copied.collection_id],
        ),
    )
    assert result.total_count == 0


def test_copy_images_subset__does_not_copy_tags(db_session: Session) -> None:
    # Arrange
    original = create_collection(session=db_session, collection_name="original")
    img = create_image(
        session=db_session, collection_id=original.collection_id, file_path_abs="/a.png"
    )
    create_tag(session=db_session, collection_id=original.collection_id, tag_name="keep")

    # Act
    copied = dataset_resolver.copy_images_subset(
        session=db_session,
        dataset_id=original.dataset_id,
        copy_name="copied",
        sample_ids=[img.sample_id],
    )

    # Assert - no tags in the new dataset.
    copied_tags = tag_resolver.get_all_by_collection_id(
        session=db_session, collection_id=copied.collection_id
    )
    assert copied_tags == []


def test_copy_images_subset__does_not_copy_embeddings(db_session: Session) -> None:
    # Arrange
    original = create_collection(session=db_session, collection_name="original")
    img = create_image(
        session=db_session, collection_id=original.collection_id, file_path_abs="/a.png"
    )
    model = create_embedding_model(
        session=db_session,
        collection_id=original.collection_id,
        embedding_model_name="m",
        embedding_dimension=3,
    )
    create_sample_embedding(
        session=db_session,
        sample_id=img.sample_id,
        embedding_model_id=model.embedding_model_id,
        embedding=[1.0, 2.0, 3.0],
    )

    # Act
    copied = dataset_resolver.copy_images_subset(
        session=db_session,
        dataset_id=original.dataset_id,
        copy_name="copied",
        sample_ids=[img.sample_id],
    )

    # Assert - no embedding models in the new dataset (and therefore no embeddings).
    copied_models = embedding_model_resolver.get_all_by_collection_id(
        session=db_session, collection_id=copied.collection_id
    )
    assert copied_models == []
    # Sanity check: the original embedding still exists.
    original_embeddings = sample_embedding_resolver.get_all_by_collection_id(
        session=db_session,
        collection_id=original.collection_id,
        embedding_model_id=model.embedding_model_id,
    )
    assert len(original_embeddings) == 1


def test_copy_images_subset__original_unchanged(db_session: Session) -> None:
    # Arrange
    original = create_collection(session=db_session, collection_name="original")
    img1 = create_image(
        session=db_session, collection_id=original.collection_id, file_path_abs="/a.png"
    )
    create_image(session=db_session, collection_id=original.collection_id, file_path_abs="/b.png")

    # Act
    dataset_resolver.copy_images_subset(
        session=db_session,
        dataset_id=original.dataset_id,
        copy_name="copied",
        sample_ids=[img1.sample_id],
    )

    # Assert - original dataset still has both images.
    original_samples = sample_resolver.get_filtered_samples(
        session=db_session, collection_id=original.collection_id
    )
    assert original_samples.total_count == 2


def test_copy_images_subset__empty_sample_ids_yields_empty_dataset(db_session: Session) -> None:
    # Arrange
    original = create_collection(session=db_session, collection_name="original")
    create_image(session=db_session, collection_id=original.collection_id, file_path_abs="/a.png")

    # Act
    copied = dataset_resolver.copy_images_subset(
        session=db_session,
        dataset_id=original.dataset_id,
        copy_name="copied",
        sample_ids=[],
    )

    # Assert - new dataset exists but is empty.
    copied_samples = sample_resolver.get_filtered_samples(
        session=db_session, collection_id=copied.collection_id
    )
    assert copied_samples.total_count == 0


def test_copy_images_subset__unknown_sample_ids_ignored(db_session: Session) -> None:
    # Arrange
    original = create_collection(session=db_session, collection_name="original")
    img = create_image(
        session=db_session, collection_id=original.collection_id, file_path_abs="/a.png"
    )

    # Act
    copied = dataset_resolver.copy_images_subset(
        session=db_session,
        dataset_id=original.dataset_id,
        copy_name="copied",
        sample_ids=[img.sample_id, uuid.uuid4()],
    )

    # Assert - only the valid image was copied.
    copied_images = image_resolver.get_all_by_collection_id(
        session=db_session, collection_id=copied.collection_id
    )
    assert len(copied_images.samples) == 1


def test_copy_images_subset__rejects_non_image_datasets(db_session: Session) -> None:
    # Arrange - a VIDEO root collection.
    video_root = create_collection(
        session=db_session, collection_name="video_dataset", sample_type=SampleType.VIDEO
    )

    # Act & Assert
    with pytest.raises(ValueError, match="IMAGE"):
        dataset_resolver.copy_images_subset(
            session=db_session,
            dataset_id=video_root.dataset_id,
            copy_name="copied",
            sample_ids=[],
        )


def test_copy_images_subset__raises_for_nonexistent_dataset(db_session: Session) -> None:
    with pytest.raises(ValueError, match="not found"):
        dataset_resolver.copy_images_subset(
            session=db_session,
            dataset_id=uuid.uuid4(),
            copy_name="copied",
            sample_ids=[],
        )
