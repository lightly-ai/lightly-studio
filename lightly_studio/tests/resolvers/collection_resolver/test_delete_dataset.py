"""Tests for delete_dataset resolver."""

import pytest
from sqlmodel import Session

from lightly_studio.models.annotation.annotation_base import AnnotationType
from lightly_studio.models.collection import SampleType
from lightly_studio.resolvers import (
    annotation_label_resolver,
    collection_resolver,
    metadata_resolver,
    sample_embedding_resolver,
    sample_resolver,
    tag_resolver,
)
from lightly_studio.resolvers.sample_resolver.sample_filter import SampleFilter
from tests.helpers_resolvers import (
    AnnotationDetails,
    create_annotation_label,
    create_annotations,
    create_collection,
    create_embedding_model,
    create_image,
    create_sample_embedding,
    create_tag,
)
from tests.resolvers.video.helpers import VideoStub, create_video_with_frames


def test_delete_dataset__empty_collection(test_db: Session) -> None:
    # Arrange
    dataset = create_collection(session=test_db, collection_name="to_delete")
    collection_id = dataset.collection_id  # Capture before delete

    # Act
    collection_resolver.delete_dataset(
        session=test_db,
        root_collection_id=collection_id,
    )

    # Assert - collection deleted
    assert collection_resolver.get_by_id(session=test_db, collection_id=collection_id) is None


def test_delete_dataset__with_images_and_annotations(test_db: Session) -> None:
    # Arrange
    dataset = create_collection(session=test_db, collection_name="to_delete")
    collection_id = dataset.collection_id  # Capture before delete
    img = create_image(session=test_db, collection_id=collection_id, file_path_abs="/a.png")
    label = create_annotation_label(session=test_db, dataset_id=collection_id, label_name="cat")
    label_id = label.annotation_label_id  # Capture before delete
    create_annotations(
        session=test_db,
        collection_id=collection_id,
        annotations=[
            AnnotationDetails(
                sample_id=img.sample_id,
                annotation_label_id=label_id,
                annotation_type=AnnotationType.OBJECT_DETECTION,
            )
        ],
    )
    child_collection_id = (
        collection_resolver.get_by_id(session=test_db, collection_id=collection_id)
        .children[0]
        .collection_id
    )

    # Act
    collection_resolver.delete_dataset(
        session=test_db,
        root_collection_id=collection_id,
    )

    # Assert - collection, annotations, and labels deleted
    assert collection_resolver.get_by_id(session=test_db, collection_id=collection_id) is None
    assert collection_resolver.get_by_id(session=test_db, collection_id=child_collection_id) is None
    assert annotation_label_resolver.get_by_id(session=test_db, label_id=label_id) is None


def test_delete_dataset__with_video_and_frames(test_db: Session) -> None:
    # Arrange
    root_collection_id = create_collection(
        session=test_db, collection_name="root_dataset", sample_type=SampleType.VIDEO
    ).collection_id
    create_video_with_frames(
        session=test_db,
        collection_id=root_collection_id,
        video=VideoStub(path="/path/to/sample1.mp4"),
    )
    # Refetch root after adding frames.
    root = collection_resolver.get_by_id(session=test_db, collection_id=root_collection_id)
    child_collection_id = root.children[0].collection_id  # Capture before delete

    # Act
    collection_resolver.delete_dataset(
        session=test_db,
        root_collection_id=root_collection_id,
    )

    # Assert - entire hierarchy deleted
    assert collection_resolver.get_by_id(session=test_db, collection_id=root_collection_id) is None
    assert collection_resolver.get_by_id(session=test_db, collection_id=child_collection_id) is None


def test_delete_dataset__with_metadata(test_db: Session) -> None:
    # Arrange
    dataset = create_collection(session=test_db, collection_name="to_delete")
    collection_id = dataset.collection_id  # Capture before delete
    img = create_image(session=test_db, collection_id=collection_id, file_path_abs="/test.png")
    sample_id = img.sample_id  # Capture before delete
    img.sample["temperature"] = 25
    img.sample["location"] = "city"

    # Act
    collection_resolver.delete_dataset(
        session=test_db,
        root_collection_id=collection_id,
    )

    # Assert - collection and metadata deleted
    assert collection_resolver.get_by_id(session=test_db, collection_id=collection_id) is None
    assert metadata_resolver.get_by_sample_id(session=test_db, sample_id=sample_id) is None


def test_delete_dataset__with_embeddings(test_db: Session) -> None:
    # Arrange
    dataset = create_collection(session=test_db, collection_name="to_delete")
    collection_id = dataset.collection_id  # Capture before delete
    img = create_image(session=test_db, collection_id=collection_id, file_path_abs="/a.png")

    embedding_model = create_embedding_model(
        session=test_db,
        collection_id=collection_id,
        embedding_model_name="test_model",
        embedding_dimension=512,
    )
    embedding_model_id = embedding_model.embedding_model_id  # Capture before delete
    create_sample_embedding(
        session=test_db,
        sample_id=img.sample_id,
        embedding_model_id=embedding_model_id,
        embedding=[1.0, 2.0, 3.0],
    )

    # Act
    collection_resolver.delete_dataset(
        session=test_db,
        root_collection_id=collection_id,
    )

    # Assert - collection deleted, embeddings deleted
    assert collection_resolver.get_by_id(session=test_db, collection_id=collection_id) is None
    embeddings = sample_embedding_resolver.get_all_by_collection_id(
        session=test_db,
        collection_id=collection_id,
        embedding_model_id=embedding_model_id,
    )
    assert len(embeddings) == 0


def test_delete_dataset__with_tags(test_db: Session) -> None:
    # Arrange
    dataset = create_collection(session=test_db, collection_name="to_delete")
    collection_id = dataset.collection_id  # Capture before delete
    img = create_image(session=test_db, collection_id=collection_id, file_path_abs="/a.png")
    tag = create_tag(session=test_db, collection_id=collection_id, tag_name="my_tag")
    tag_id = tag.tag_id  # Capture before delete
    tag_resolver.add_tag_to_sample(session=test_db, tag_id=tag_id, sample=img.sample)

    # Act
    collection_resolver.delete_dataset(
        session=test_db,
        root_collection_id=collection_id,
    )

    # Assert - collection and tags deleted
    assert collection_resolver.get_by_id(session=test_db, collection_id=collection_id) is None
    assert tag_resolver.get_by_id(session=test_db, tag_id=tag_id) is None


def test_delete_dataset__does_not_affect_other_datasets(test_db: Session) -> None:
    # Arrange - create two datasets
    dataset_to_delete = create_collection(session=test_db, collection_name="to_delete")
    delete_collection_id = dataset_to_delete.collection_id  # Capture before delete
    create_image(session=test_db, collection_id=delete_collection_id, file_path_abs="/a.png")
    tag_to_delete = create_tag(
        session=test_db, collection_id=delete_collection_id, tag_name="tag_delete"
    )
    delete_tag_id = tag_to_delete.tag_id  # Capture before delete

    other_dataset = create_collection(session=test_db, collection_name="other")
    other_collection_id = other_dataset.collection_id  # Capture before delete
    other_image = create_image(
        session=test_db, collection_id=other_collection_id, file_path_abs="/other.png"
    )
    other_sample_id = other_image.sample_id  # Capture before delete
    other_tag = create_tag(session=test_db, collection_id=other_collection_id, tag_name="tag_other")
    other_tag_id = other_tag.tag_id  # Capture before delete

    # Act
    collection_resolver.delete_dataset(
        session=test_db,
        root_collection_id=delete_collection_id,
    )

    # Assert - deleted dataset is gone
    assert (
        collection_resolver.get_by_id(session=test_db, collection_id=delete_collection_id) is None
    )
    assert tag_resolver.get_by_id(session=test_db, tag_id=delete_tag_id) is None

    # Assert - other dataset is intact
    assert (
        collection_resolver.get_by_id(session=test_db, collection_id=other_collection_id)
        is not None
    )
    assert tag_resolver.get_by_id(session=test_db, tag_id=other_tag_id) is not None

    other_samples = sample_resolver.get_filtered_samples(
        session=test_db,
        filters=SampleFilter(collection_id=other_collection_id),
    )
    assert other_samples.total_count == 1
    assert other_samples.samples[0].sample_id == other_sample_id


def test_delete_dataset__raises_for_non_root_collection(test_db: Session) -> None:
    # Arrange
    root = create_collection(session=test_db, collection_name="root")
    child = create_collection(
        session=test_db,
        collection_name="child",
        parent_collection_id=root.collection_id,
    )
    child_id = child.collection_id  # Capture before delete

    # Act & Assert
    with pytest.raises(ValueError, match="Only root collections can be deleted"):
        collection_resolver.delete_dataset(
            session=test_db,
            root_collection_id=child_id,
        )


def test_delete_dataset__raises_for_nonexistent_collection(test_db: Session) -> None:
    # Arrange
    from uuid import uuid4

    nonexistent_id = uuid4()

    # Act & Assert
    with pytest.raises(ValueError, match="not found"):
        collection_resolver.delete_dataset(
            session=test_db,
            root_collection_id=nonexistent_id,
        )
