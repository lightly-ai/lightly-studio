"""Tests for deep_copy resolver."""

import pytest
from sqlmodel import Session

from lightly_studio.metadata.gps_coordinate import GPSCoordinate
from lightly_studio.models.collection import SampleType
from lightly_studio.resolvers import (
    collection_resolver,
    image_resolver,
    metadata_resolver,
    sample_embedding_resolver,
    sample_resolver,
)
from lightly_studio.resolvers.sample_resolver.sample_filter import SampleFilter
from tests.helpers_resolvers import (
    create_collection,
    create_embedding_model,
    create_image,
    create_sample_embedding,
)


def test_deep_copy__empty_collection(test_db: Session) -> None:
    # Arrange
    original = create_collection(session=test_db, collection_name="original")

    # Act
    copied = collection_resolver.deep_copy(
        session=test_db,
        root_collection_id=original.collection_id,
        copy_name="copied",
    )

    # Assert - new collection created with different ID
    assert copied.collection_id != original.collection_id
    assert copied.name == "copied"
    assert copied.sample_type == original.sample_type
    assert copied.parent_collection_id is None


def test_deep_copy__with_images(test_db: Session) -> None:
    # Arrange
    original = create_collection(session=test_db, collection_name="original")
    img1 = create_image(
        session=test_db, collection_id=original.collection_id, file_path_abs="/a.png"
    )
    img2 = create_image(
        session=test_db, collection_id=original.collection_id, file_path_abs="/b.png"
    )

    # Act
    copied = collection_resolver.deep_copy(
        session=test_db,
        root_collection_id=original.collection_id,
        copy_name="copied",
    )
    # Add another image to the original collection after copying
    create_image(session=test_db, collection_id=original.collection_id, file_path_abs="/c.png")

    # Assert - new collection has new samples
    copied_samples_result = sample_resolver.get_filtered_samples(
        session=test_db,
        filters=SampleFilter(collection_id=copied.collection_id),
    )
    assert copied_samples_result.total_count == 2

    # Assert - sample IDs are different
    original_ids = {img1.sample_id, img2.sample_id}
    copied_ids = {s.sample_id for s in copied_samples_result.samples}
    assert original_ids.isdisjoint(copied_ids)

    # Assert - image data preserved
    copied_images = image_resolver.get_all_by_collection_id(
        session=test_db,
        collection_id=copied.collection_id,
    )
    copied_paths = {s.file_path_abs for s in copied_images.samples}
    assert copied_paths == {"/a.png", "/b.png"}

    # Assert - original collection has 3 samples
    original_samples_result = sample_resolver.get_filtered_samples(
        session=test_db,
        filters=SampleFilter(collection_id=original.collection_id),
    )
    assert original_samples_result.total_count == 3

    # Assert - copied collection remains with 2 samples
    copied_samples_result_after = sample_resolver.get_filtered_samples(
        session=test_db,
        filters=SampleFilter(collection_id=copied.collection_id),
    )
    assert copied_samples_result_after.total_count == 2


def test_deep_copy__with_hierarchy(test_db: Session) -> None:
    # Arrange
    root = create_collection(
        session=test_db, collection_name="original_dataset", sample_type=SampleType.VIDEO
    )
    child = create_collection(
        session=test_db,
        collection_name="original_dataset__video_frame",
        parent_collection_id=root.collection_id,
        sample_type=SampleType.VIDEO_FRAME,
    )

    # Act
    copied_root = collection_resolver.deep_copy(
        session=test_db,
        root_collection_id=root.collection_id,
        copy_name="copied_dataset",
    )

    # Assert - hierarchy copied
    hierarchy = collection_resolver.get_hierarchy(
        session=test_db, dataset_id=copied_root.collection_id
    )
    assert len(hierarchy) == 2

    # Assert - child name derived correctly
    assert hierarchy[0].name == "copied_dataset"
    assert hierarchy[1].name == "copied_dataset__video_frame"

    # Assert - child points to new parent
    copied_child = hierarchy[1]
    assert copied_child.parent_collection_id == copied_root.collection_id
    assert copied_child.collection_id != child.collection_id

    # Assert - original hierarchy unchanged
    original_hierarchy = collection_resolver.get_hierarchy(
        session=test_db, dataset_id=root.collection_id
    )
    assert len(original_hierarchy) == 2
    assert original_hierarchy[1].parent_collection_id == root.collection_id


def test_deep_copy__with_metadata(test_db: Session) -> None:
    # Arrange
    original = create_collection(session=test_db, collection_name="original")
    img = create_image(
        session=test_db, collection_id=original.collection_id, file_path_abs="/test.png"
    )

    img.sample["temperature"] = 25
    img.sample["location"] = "city"
    img.sample["gps_location"] = GPSCoordinate(lat=40.7128, lon=-74.0060)

    # Act
    copied = collection_resolver.deep_copy(
        session=test_db,
        root_collection_id=original.collection_id,
        copy_name="copied",
    )

    # Assert - metadata gets copied
    copied_samples = sample_resolver.get_filtered_samples(
        session=test_db,
        filters=SampleFilter(collection_id=copied.collection_id),
    )
    assert copied_samples.total_count == 1
    copied_sample = copied_samples.samples[0]

    copied_metadata = metadata_resolver.get_by_sample_id(
        session=test_db,
        sample_id=copied_sample.sample_id,
    )
    assert copied_metadata is not None

    # Assert - data preserved
    assert copied_metadata.data["temperature"] == 25
    assert copied_metadata.data["location"] == "city"
    assert copied_metadata.data["gps_location"]["lat"] == 40.7128
    assert copied_metadata.data["gps_location"]["lon"] == -74.0060

    assert copied_metadata.metadata_schema["gps_location"] == "gps_coordinate"
    assert copied_metadata.metadata_schema["location"] == "string"
    assert copied_metadata.metadata_schema["temperature"] == "integer"

    # Assert - modifications to copied metadata do not affect original
    copied_sample["temperature"] = 30
    original_metadata = metadata_resolver.get_by_sample_id(
        session=test_db, sample_id=img.sample.sample_id
    )
    assert original_metadata is not None
    assert original_metadata.data["temperature"] == 25
    assert copied_metadata.data["temperature"] == 30


def test_deep_copy__with_nested_metadata(test_db: Session) -> None:
    """Verify nested metadata structures are properly deep copied.

    This test ensures that modifying nested dicts/lists in copied metadata
    does not affect the original metadata (i.e., model_dump() properly
    deep copies JSON fields).
    """
    # Arrange
    original = create_collection(session=test_db, collection_name="original")
    img = create_image(
        session=test_db, collection_id=original.collection_id, file_path_abs="/test.png"
    )

    # Set metadata with nested structures
    img.sample["config"] = {"threshold": 0.5, "options": {"enabled": True, "mode": "auto"}}
    img.sample["some_list"] = ["el1", "el2"]

    # Act
    copied = collection_resolver.deep_copy(
        session=test_db,
        root_collection_id=original.collection_id,
        copy_name="copied",
    )

    # Get copied metadata
    copied_samples = sample_resolver.get_filtered_samples(
        session=test_db,
        filters=SampleFilter(collection_id=copied.collection_id),
    )
    copied_sample = copied_samples.samples[0]
    copied_metadata = metadata_resolver.get_by_sample_id(
        session=test_db, sample_id=copied_sample.sample_id
    )
    assert copied_metadata is not None

    # Assert - nested data was copied correctly
    assert copied_metadata.data["config"]["threshold"] == 0.5
    assert copied_metadata.data["config"]["options"]["enabled"] is True
    assert copied_metadata.data["config"]["options"]["mode"] == "auto"
    assert copied_metadata.data["some_list"] == ["el1", "el2"]

    # Act - modify nested values in the copy
    copied_metadata.data["config"]["threshold"] = 0.9
    copied_metadata.data["config"]["options"]["enabled"] = False
    copied_metadata.data["config"]["options"]["mode"] = "manual"
    copied_metadata.data["some_list"].append("el3")

    # Assert - original metadata is unchanged
    original_metadata = metadata_resolver.get_by_sample_id(
        session=test_db, sample_id=img.sample.sample_id
    )
    assert original_metadata is not None
    assert original_metadata.data["config"]["threshold"] == 0.5
    assert original_metadata.data["config"]["options"]["enabled"] is True
    assert copied_metadata.data["config"]["options"]["mode"] == "manual"
    assert original_metadata.data["some_list"] == ["el1", "el2"]


def test_deep_copy__with_embeddings(test_db: Session) -> None:
    # Arrange
    original = create_collection(session=test_db, collection_name="original")
    img1 = create_image(
        session=test_db, collection_id=original.collection_id, file_path_abs="/a.png"
    )
    img2 = create_image(
        session=test_db, collection_id=original.collection_id, file_path_abs="/b.png"
    )

    # Create embedding model
    embedding_model = create_embedding_model(
        session=test_db,
        collection_id=original.collection_id,
        embedding_model_name="test_model",
        embedding_dimension=512,
    )

    # Create embeddings
    create_sample_embedding(
        session=test_db,
        sample_id=img1.sample_id,
        embedding_model_id=embedding_model.embedding_model_id,
        embedding=[1.0, 2.0, 3.0],
    )
    create_sample_embedding(
        session=test_db,
        sample_id=img2.sample_id,
        embedding_model_id=embedding_model.embedding_model_id,
        embedding=[4.0, 5.0, 6.0],
    )

    # Act
    copied = collection_resolver.deep_copy(
        session=test_db,
        root_collection_id=original.collection_id,
        copy_name="copied",
    )

    # Assert - embeddings copied
    copied_samples = sample_resolver.get_filtered_samples(
        session=test_db,
        filters=SampleFilter(collection_id=copied.collection_id),
    )
    assert copied_samples.total_count == 2

    # Get embeddings for copied samples
    copied_embeddings = sample_embedding_resolver.get_all_by_collection_id(
        session=test_db,
        collection_id=copied.collection_id,
        embedding_model_id=embedding_model.embedding_model_id,
    )
    assert len(copied_embeddings) == 2

    # Assert - embeddings reference the same embedding model
    for emb in copied_embeddings:
        assert emb.embedding_model_id == embedding_model.embedding_model_id

    # Assert - embedding vectors are preserved
    copied_vectors = {tuple(emb.embedding) for emb in copied_embeddings}
    assert (1.0, 2.0, 3.0) in copied_vectors
    assert (4.0, 5.0, 6.0) in copied_vectors

    # Assert - sample IDs are different
    original_sample_ids = {img1.sample_id, img2.sample_id}
    copied_sample_ids = {emb.sample_id for emb in copied_embeddings}
    assert original_sample_ids.isdisjoint(copied_sample_ids)


def test_deep_copy__raises_for_non_root_collection(test_db: Session) -> None:
    # Arrange
    root = create_collection(session=test_db, collection_name="root")
    child = create_collection(
        session=test_db,
        collection_name="child",
        parent_collection_id=root.collection_id,
    )

    # Act & Assert
    with pytest.raises(ValueError, match="Only root collections can be deep copied"):
        collection_resolver.deep_copy(
            session=test_db,
            root_collection_id=child.collection_id,
            copy_name="test",
        )


def test_deep_copy__raises_for_nonexistent_collection(test_db: Session) -> None:
    # Arrange
    from uuid import uuid4

    nonexistent_id = uuid4()

    # Act & Assert
    with pytest.raises(ValueError, match="not found"):
        collection_resolver.deep_copy(
            session=test_db,
            root_collection_id=nonexistent_id,
            copy_name="test",
        )
