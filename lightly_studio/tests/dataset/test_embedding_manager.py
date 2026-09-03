"""Unit tests for the EmbeddingManager class."""

from __future__ import annotations

from uuid import UUID, uuid4

import numpy as np
import pytest
from numpy.typing import NDArray
from PIL import Image
from pytest_mock import MockerFixture
from sqlmodel import Session, select

from lightly_studio.dataset import embedding_manager
from lightly_studio.dataset.embedding_generator import (
    ImageEmbeddingGenerator,
    RandomEmbeddingGenerator,
)
from lightly_studio.dataset.embedding_manager import (
    EmbeddingManager,
    TextEmbedQuery,
)
from lightly_studio.embed.types import EmbeddingResult, EmbeddingSpaceSpec, ImageCrop
from lightly_studio.models.annotation.annotation_base import AnnotationType
from lightly_studio.models.collection import CollectionTable, SampleType
from lightly_studio.models.embedding_model import EmbeddingModelTable
from lightly_studio.models.image import ImageTable
from lightly_studio.models.sample_embedding import SampleEmbeddingTable
from lightly_studio.resolvers import (
    collection_embedding_model_resolver,
    collection_resolver,
    embedding_model_resolver,
    sample_embedding_resolver,
)
from tests.helpers_resolvers import (
    create_annotation,
    create_annotation_label,
    create_collection,
    create_image,
)
from tests.resolvers.video.helpers import VideoStub, create_videos


def test_register_embedding_model(
    db_session: Session,
    collection: CollectionTable,
) -> None:
    """Test registering an embedding model."""
    # Register the model.
    embedding_manager = EmbeddingManager()
    random_model = RandomEmbeddingGenerator()
    model_id = embedding_manager.register_embedding_model(
        session=db_session,
        embedding_generator=random_model,
        collection_id=collection.collection_id,
        set_as_default=True,
    ).embedding_model_id

    # Check that the model was registered in memory.
    assert model_id in embedding_manager._models
    assert embedding_manager._models[model_id] == random_model
    assert (
        embedding_manager._collection_id_to_default_model_id[collection.collection_id] == model_id
    )

    # Check that the model was stored in the database.
    stored_model = db_session.exec(
        select(EmbeddingModelTable).where(EmbeddingModelTable.embedding_model_id == model_id)
    ).first()
    assert stored_model is not None
    assert stored_model.name == "random_model"
    assert stored_model.embedding_dimension == 3
    assert stored_model.dataset_id == collection.dataset_id


def test_register_embedding_model__collection_not_found(db_session: Session) -> None:
    manager = EmbeddingManager()
    collection_id = UUID(int=0)

    with pytest.raises(ValueError, match="Provided collection_id could not be found"):
        manager.register_embedding_model(
            session=db_session,
            embedding_generator=RandomEmbeddingGenerator(),
            collection_id=collection_id,
        )


def test_register_multiple_models(
    db_session: Session,
    collection: CollectionTable,
) -> None:
    """Test registering multiple embedding models."""
    # Register first model.
    embedding_manager = EmbeddingManager()
    model_id1 = embedding_manager.register_embedding_model(
        session=db_session,
        embedding_generator=RandomEmbeddingGenerator(),
        collection_id=collection.collection_id,
        set_as_default=True,
    ).embedding_model_id

    # Register a second model.
    class FakeEmbeddingGenerator(ImageEmbeddingGenerator):
        def embedding_space_spec(self) -> EmbeddingSpaceSpec:
            return EmbeddingSpaceSpec(
                space_key="fake_model",
                dimension=5,
            )

        def embed_text(self, text: str) -> list[float]:
            raise NotImplementedError()

        def embed_images(self, filepaths: list[str], show_progress: bool = True) -> EmbeddingResult:
            raise NotImplementedError()

        def embed_image_crops(
            self, image_crops: list[ImageCrop], show_progress: bool = True
        ) -> EmbeddingResult:
            raise NotImplementedError()

        def embed_pil_images(
            self, images: list[Image.Image], show_progress: bool = True
        ) -> NDArray[np.float32]:
            raise NotImplementedError()

    model_id2 = embedding_manager.register_embedding_model(
        session=db_session,
        embedding_generator=FakeEmbeddingGenerator(),
        collection_id=collection.collection_id,
        set_as_default=False,
    ).embedding_model_id

    # Check that both models were registered in memory
    assert model_id1 in embedding_manager._models
    assert model_id2 in embedding_manager._models
    assert (
        embedding_manager._collection_id_to_default_model_id[collection.collection_id] == model_id1
    )

    # Check that both models were stored in the database
    stored_models = db_session.exec(select(EmbeddingModelTable)).all()
    assert len(stored_models) == 2
    model_names = {model.name for model in stored_models}
    assert model_names == {"random_model", "fake_model"}
    # Verify both models are associated with the same dataset
    assert all(model.dataset_id == collection.dataset_id for model in stored_models)

    # Both models are linked to the collection, not only the default one.
    linked_model_ids = collection_embedding_model_resolver.get_all_by_collection_id(
        session=db_session, collection_id=collection.collection_id
    )
    assert set(linked_model_ids) == {model_id1, model_id2}

    # The DB default is the model registered with set_as_default=True. The second model,
    # registered with set_as_default=False, must not override the existing default.
    assert (
        collection_embedding_model_resolver.get_default_by_collection_id(
            session=db_session, collection_id=collection.collection_id
        )
        == model_id1
    )


def test_register_embedding_model__seeds_default_cache_from_db(
    db_session: Session,
    collection: CollectionTable,
) -> None:
    """A fresh manager caches an existing DB default even when set_as_default is False.

    The default lives in the database. A new manager starts with an empty cache, so
    re-registering a model that is already the collection's default must seed the cache
    from the database rather than leave it empty.
    """
    # A first manager registers the model and makes it the DB default.
    first_manager = EmbeddingManager()
    model_id = first_manager.register_embedding_model(
        session=db_session,
        embedding_generator=RandomEmbeddingGenerator(),
        collection_id=collection.collection_id,
        set_as_default=True,
    ).embedding_model_id

    # A fresh manager (empty cache) re-registers the same model without asking for default.
    second_manager = EmbeddingManager()
    second_manager.register_embedding_model(
        session=db_session,
        embedding_generator=RandomEmbeddingGenerator(),
        collection_id=collection.collection_id,
        set_as_default=False,
    )

    # The existing DB default is mirrored into the fresh manager's cache.
    assert second_manager._collection_id_to_default_model_id[collection.collection_id] == model_id


def test_embed_text_with_default_model(
    db_session: Session,
    collection: CollectionTable,
) -> None:
    """Test generating text embeddings with default model."""
    # Register model.
    embedding_manager = EmbeddingManager()
    embedding_manager.register_embedding_model(
        session=db_session,
        embedding_generator=RandomEmbeddingGenerator(),
        collection_id=collection.collection_id,
        set_as_default=True,
    )

    # Generate embedding.
    query = TextEmbedQuery(text="test text")
    embedding = embedding_manager.embed_text(
        collection_id=collection.collection_id, text_query=query
    )

    # Check embedding.
    assert len(embedding) == 3


def test_embed_text_with_specific_model(
    db_session: Session,
    collection: CollectionTable,
) -> None:
    """Test generating text embeddings with specific model."""
    # Register model.
    embedding_manager = EmbeddingManager()
    model_id = embedding_manager.register_embedding_model(
        session=db_session,
        embedding_generator=RandomEmbeddingGenerator(),
        collection_id=collection.collection_id,
        set_as_default=True,
    ).embedding_model_id

    # Generate embedding with specific model.
    query = TextEmbedQuery(text="test text", embedding_model_id=model_id)
    embedding = embedding_manager.embed_text(
        collection_id=collection.collection_id, text_query=query
    )

    # Check embedding.
    assert len(embedding) == 3


def test_embed_text_without_model() -> None:
    """Test generating text embeddings without registered model."""
    embedding_manager = EmbeddingManager()
    query = TextEmbedQuery(text="test text")
    with pytest.raises(ValueError, match="No embedding_model_id provided and no default embedding"):
        embedding_manager.embed_text(collection_id=uuid4(), text_query=query)


def test_embed_text_with_invalid_model(
    db_session: Session,
    collection: CollectionTable,
) -> None:
    """Test generating text embeddings with invalid model ID."""
    # Register model
    embedding_manager = EmbeddingManager()
    embedding_manager.register_embedding_model(
        session=db_session,
        embedding_generator=RandomEmbeddingGenerator(),
        collection_id=collection.collection_id,
        set_as_default=True,
    )
    invalid_model_id = uuid4()
    query = TextEmbedQuery(text="test text", embedding_model_id=invalid_model_id)
    with pytest.raises(
        ValueError,
        match=f"No embedding model found with ID {invalid_model_id}",
    ):
        embedding_manager.embed_text(collection_id=collection.collection_id, text_query=query)


def test_embed_images(
    db_session: Session,
    collection: CollectionTable,
    samples: list[ImageTable],
    mocker: MockerFixture,
) -> None:
    """Test generating and storing image embeddings."""
    # Use a small batch size so the 10 samples span multiple insertion batches.
    mocker.patch.object(embedding_manager, "EMBEDDING_INSERTION_BATCH_SIZE", 4)
    create_many_spy = mocker.spy(sample_embedding_resolver, "create_many")

    # Register model
    manager = EmbeddingManager()
    model_id = manager.register_embedding_model(
        session=db_session,
        embedding_generator=RandomEmbeddingGenerator(),
        collection_id=collection.collection_id,
        set_as_default=True,
    ).embedding_model_id

    # Generate embeddings for samples
    sample_ids = [sample.sample_id for sample in samples]
    manager.embed_images(
        session=db_session, collection_id=collection.collection_id, sample_ids=sample_ids
    )

    # 10 samples -> 3 batches with sizes 4, 4, and 2
    assert create_many_spy.call_count == 3

    # Verify embeddings were stored in the database
    stored_embeddings = db_session.exec(
        select(SampleEmbeddingTable).where(SampleEmbeddingTable.embedding_model_id == model_id)
    ).all()
    assert len(stored_embeddings) == 10
    for embedding in stored_embeddings:
        assert len(embedding.embedding) == 3  # dimension=3
        assert embedding.sample_id in sample_ids


def test_embed_images_with_incompatible_generator(
    db_session: Session,
    collection: CollectionTable,
) -> None:
    """Ensure we surface a clear error when the model doesn't support images."""
    manager = EmbeddingManager()
    manager.register_embedding_model(
        session=db_session,
        embedding_generator=TextOnlyEmbeddingGenerator(),
        collection_id=collection.collection_id,
        set_as_default=True,
    )

    with pytest.raises(ValueError, match=r"Embedding model not compatible with images."):
        manager.embed_images(
            session=db_session, collection_id=collection.collection_id, sample_ids=[uuid4()]
        )


@pytest.mark.parametrize(
    "annotation_type",
    [AnnotationType.OBJECT_DETECTION, AnnotationType.SEGMENTATION_MASK],
)
def test_embed_annotations(
    db_session: Session,
    collection: CollectionTable,
    annotation_type: AnnotationType,
) -> None:
    """embed_annotations stores one embedding per croppable annotation, per type."""
    image = create_image(session=db_session, collection_id=collection.collection_id)
    label = create_annotation_label(session=db_session, root_collection_id=collection.collection_id)
    create_annotation(
        session=db_session,
        collection_id=collection.collection_id,
        sample_id=image.sample_id,
        annotation_label_id=label.annotation_label_id,
        annotation_type=annotation_type,
    )
    annotation_collection_id = collection_resolver.get_or_create_child_collection(
        session=db_session,
        collection_id=collection.collection_id,
        sample_type=SampleType.ANNOTATION,
    )

    manager = EmbeddingManager()
    model_id = manager.register_embedding_model(
        session=db_session,
        embedding_generator=RandomEmbeddingGenerator(),
        collection_id=annotation_collection_id,
        set_as_default=True,
    ).embedding_model_id

    manager.embed_annotations(
        session=db_session,
        annotation_collection_id=annotation_collection_id,
        embedding_model_id=model_id,
    )

    stored_embeddings = sample_embedding_resolver.get_all_by_collection_id(
        session=db_session,
        collection_id=annotation_collection_id,
        embedding_model_id=model_id,
    )
    assert len(stored_embeddings) == 1


def test_embed_annotations_is_idempotent(
    db_session: Session,
    collection: CollectionTable,
) -> None:
    """Re-running embed_annotations does not duplicate embeddings."""
    image = create_image(session=db_session, collection_id=collection.collection_id)
    label = create_annotation_label(session=db_session, root_collection_id=collection.collection_id)
    create_annotation(
        session=db_session,
        collection_id=collection.collection_id,
        sample_id=image.sample_id,
        annotation_label_id=label.annotation_label_id,
    )
    annotation_collection_id = collection_resolver.get_or_create_child_collection(
        session=db_session,
        collection_id=collection.collection_id,
        sample_type=SampleType.ANNOTATION,
    )

    manager = EmbeddingManager()
    model_id = manager.register_embedding_model(
        session=db_session,
        embedding_generator=RandomEmbeddingGenerator(),
        collection_id=annotation_collection_id,
        set_as_default=True,
    ).embedding_model_id

    manager.embed_annotations(session=db_session, annotation_collection_id=annotation_collection_id)
    manager.embed_annotations(session=db_session, annotation_collection_id=annotation_collection_id)

    stored_embeddings = sample_embedding_resolver.get_all_by_collection_id(
        session=db_session,
        collection_id=annotation_collection_id,
        embedding_model_id=model_id,
    )
    assert len(stored_embeddings) == 1


def test_embed_annotations_processes_all_chunks(
    db_session: Session,
    collection: CollectionTable,
    mocker: MockerFixture,
) -> None:
    """All annotations are embedded even when they span multiple chunks."""
    # Force several chunks.
    mocker.patch.object(embedding_manager, "ANNOTATION_EMBED_BATCH_SIZE", 2)
    label = create_annotation_label(session=db_session, root_collection_id=collection.collection_id)
    for index in range(3):
        image = create_image(
            session=db_session,
            collection_id=collection.collection_id,
            file_path_abs=f"/path/to/sample_{index}.png",
        )
        create_annotation(
            session=db_session,
            collection_id=collection.collection_id,
            sample_id=image.sample_id,
            annotation_label_id=label.annotation_label_id,
        )
    annotation_collection_id = collection_resolver.get_or_create_child_collection(
        session=db_session,
        collection_id=collection.collection_id,
        sample_type=SampleType.ANNOTATION,
    )

    manager = EmbeddingManager()
    model_id = manager.register_embedding_model(
        session=db_session,
        embedding_generator=RandomEmbeddingGenerator(),
        collection_id=annotation_collection_id,
        set_as_default=True,
    ).embedding_model_id

    manager.embed_annotations(
        session=db_session,
        annotation_collection_id=annotation_collection_id,
        embedding_model_id=model_id,
    )

    stored_embeddings = sample_embedding_resolver.get_all_by_collection_id(
        session=db_session,
        collection_id=annotation_collection_id,
        embedding_model_id=model_id,
    )
    assert len(stored_embeddings) == 3


def test_get_valid_model_id_without_default_model() -> None:
    """_get_valid_model_id raises when there is no default or explicit ID."""
    manager = EmbeddingManager()
    with pytest.raises(
        ValueError,
        match=r"No embedding_model_id provided and no default embedding model registered.",
    ):
        manager._get_default_or_validate(collection_id=uuid4(), embedding_model_id=None)


def test_get_valid_model_id_with_invalid_requested_model(
    db_session: Session,
    collection: CollectionTable,
) -> None:
    """_get_valid_model_id raises when the provided ID is unknown."""
    manager = EmbeddingManager()
    manager.register_embedding_model(
        session=db_session,
        embedding_generator=RandomEmbeddingGenerator(),
        collection_id=collection.collection_id,
        set_as_default=True,
    )
    missing_model_id = uuid4()
    with pytest.raises(
        ValueError,
        match=f"No embedding model found with ID {missing_model_id}",
    ):
        manager._get_default_or_validate(
            collection_id=collection.collection_id, embedding_model_id=missing_model_id
        )


def test_get_valid_model_id_with_default_and_explicit_id(
    db_session: Session,
    collection: CollectionTable,
) -> None:
    """_get_valid_model_id prefers explicit IDs but falls back to default."""
    manager = EmbeddingManager()
    default_model_id = manager.register_embedding_model(
        session=db_session,
        embedding_generator=RandomEmbeddingGenerator(),
        collection_id=collection.collection_id,
        set_as_default=True,
    ).embedding_model_id
    assert (
        manager._get_default_or_validate(
            collection_id=collection.collection_id, embedding_model_id=None
        )
        == default_model_id
    )

    other_model_id = manager.register_embedding_model(
        session=db_session,
        embedding_generator=RandomEmbeddingGenerator(),
        collection_id=collection.collection_id,
        set_as_default=False,
    ).embedding_model_id
    assert (
        manager._get_default_or_validate(
            collection_id=collection.collection_id, embedding_model_id=other_model_id
        )
        == other_model_id
    )


def test_load_or_get_default_model(
    db_session: Session,
    mocker: MockerFixture,
) -> None:
    collection = create_collection(session=db_session)
    manager = EmbeddingManager()

    # Mock the loading function to return a random model.
    fake_generator = RandomEmbeddingGenerator()
    mock_load = mocker.patch.object(
        embedding_manager,
        "_load_embedding_generator_from_env",
        return_value=fake_generator,
    )

    # Register a new default model.
    model_id = manager.load_or_get_default_model(
        session=db_session,
        collection_id=collection.collection_id,
    )
    assert model_id is not None

    # Verify we got back the random model.
    mock_load.assert_called_once_with(sample_type=SampleType.IMAGE)
    model = embedding_model_resolver.get_by_id(session=db_session, embedding_model_id=model_id)
    assert model is not None
    assert model.name == "random_model"

    # Second registration should be a no-op and return the same ID.
    second_id = manager.load_or_get_default_model(
        session=db_session,
        collection_id=collection.collection_id,
    )
    assert model_id == second_id
    mock_load.assert_called_once_with(sample_type=SampleType.IMAGE)  # still only one call


def test_load_or_get_default_model__shares_generator_across_collections(
    db_session: Session,
    mocker: MockerFixture,
) -> None:
    """An annotation child collection reuses the parent's loaded generator.

    The generator weights are loaded once, and both collections resolve to the same
    embedding-model record because the model is deduplicated per dataset.
    """
    image_collection = create_collection(session=db_session, sample_type=SampleType.IMAGE)
    annotation_collection = create_collection(
        session=db_session,
        parent_collection_id=image_collection.collection_id,
        sample_type=SampleType.ANNOTATION,
    )
    manager = EmbeddingManager()

    mock_load = mocker.patch.object(
        embedding_manager,
        "_load_embedding_generator_from_env",
        return_value=RandomEmbeddingGenerator(),
    )

    annotation_model_id = manager.load_or_get_default_model(
        session=db_session, collection_id=annotation_collection.collection_id
    )
    image_model_id = manager.load_or_get_default_model(
        session=db_session, collection_id=image_collection.collection_id
    )
    assert image_model_id is not None
    assert annotation_model_id is not None

    # The generator is loaded only once and shared between both collections.
    mock_load.assert_called_once_with(sample_type=SampleType.IMAGE)
    assert manager._models[image_model_id] is manager._models[annotation_model_id]

    # Both collections share the dataset, so the model is deduplicated to one record.
    assert image_model_id == annotation_model_id


def test_load_or_get_default_model__cant_load(
    db_session: Session,
    mocker: MockerFixture,
) -> None:
    """If the loader returns None, no model should be registered."""
    collection = create_collection(session=db_session)
    manager = EmbeddingManager()

    mock_load = mocker.patch.object(
        embedding_manager,
        "_load_embedding_generator_from_env",
        return_value=None,
    )

    model_id = manager.load_or_get_default_model(
        session=db_session,
        collection_id=collection.collection_id,
    )

    mock_load.assert_called_once_with(sample_type=SampleType.IMAGE)
    assert model_id is None


def test_set_default_embedding_model_overrides_env(
    db_session: Session,
    mocker: MockerFixture,
) -> None:
    """A registered override is used instead of loading a generator from the env."""
    collection = create_collection(session=db_session)
    manager = EmbeddingManager()
    mock_load = mocker.patch.object(embedding_manager, "_load_embedding_generator_from_env")

    override = RandomEmbeddingGenerator()
    manager.set_default_embedding_model(embedding_generator=override)

    model_id = manager.load_or_get_default_model(
        session=db_session, collection_id=collection.collection_id
    )

    assert model_id is not None
    assert manager._models[model_id] is override
    # The env loader is never consulted when an override is registered.
    mock_load.assert_not_called()


def test_set_default_embedding_model_fills_both_slots() -> None:
    """A generator implementing both protocols overrides image and video slots."""
    manager = EmbeddingManager()
    override = RandomEmbeddingGenerator()

    manager.set_default_embedding_model(embedding_generator=override)

    assert manager._override_generators[SampleType.IMAGE] is override
    assert manager._override_generators[SampleType.VIDEO] is override


def test_set_default_embedding_model_falls_back_to_env_for_unregistered_slot(
    db_session: Session,
    mocker: MockerFixture,
) -> None:
    """Sample types without an override still load from the env."""

    class ImageOnlyGenerator:
        # Implements the image protocol but not embed_videos, so only the image
        # slot is overridden.
        def embedding_space_spec(self) -> EmbeddingSpaceSpec:
            return EmbeddingSpaceSpec(
                space_key="image_only_model",
                dimension=3,
            )

        def embed_text(self, text: str) -> list[float]:
            _ = text
            return [0.1, 0.2, 0.3]

        def embed_images(self, filepaths: list[str], show_progress: bool = True) -> EmbeddingResult:
            _ = show_progress
            return EmbeddingResult(
                embeddings=np.zeros((len(filepaths), 3), dtype=np.float32),
                kept_indices=list(range(len(filepaths))),
            )

        def embed_image_crops(
            self, image_crops: list[ImageCrop], show_progress: bool = True
        ) -> EmbeddingResult:
            _ = show_progress
            return EmbeddingResult(
                embeddings=np.zeros((len(image_crops), 3), dtype=np.float32),
                kept_indices=list(range(len(image_crops))),
            )

        def embed_pil_images(
            self, images: list[Image.Image], show_progress: bool = True
        ) -> NDArray[np.float32]:
            _ = show_progress
            return np.zeros((len(images), 3), dtype=np.float32)

    video_collection = create_collection(session=db_session, sample_type=SampleType.VIDEO)
    manager = EmbeddingManager()
    env_generator = RandomEmbeddingGenerator()
    mock_load = mocker.patch.object(
        embedding_manager,
        "_load_embedding_generator_from_env",
        return_value=env_generator,
    )

    manager.set_default_embedding_model(embedding_generator=ImageOnlyGenerator())

    model_id = manager.load_or_get_default_model(
        session=db_session, collection_id=video_collection.collection_id
    )

    assert model_id is not None
    assert manager._models[model_id] is env_generator
    mock_load.assert_called_once_with(sample_type=SampleType.VIDEO)


def test_set_default_embedding_model_raises_on_incompatible_generator() -> None:
    """A generator implementing neither image nor video protocol is rejected."""
    manager = EmbeddingManager()
    with pytest.raises(
        TypeError,
        match=r"must implement ImageEmbeddingGenerator or VideoEmbeddingGenerator",
    ):
        manager.set_default_embedding_model(embedding_generator=TextOnlyEmbeddingGenerator())


def test_default_model(
    db_session: Session,
    collection: CollectionTable,
) -> None:
    """Test default model functionality."""
    embedding_manager = EmbeddingManager()
    first_model_id = embedding_manager.register_embedding_model(
        session=db_session,
        embedding_generator=RandomEmbeddingGenerator(),
        collection_id=collection.collection_id,
        set_as_default=False,
    ).embedding_model_id
    # The first model is always set as default, both in memory and in the database.
    assert (
        embedding_manager._collection_id_to_default_model_id[collection.collection_id]
        == first_model_id
    )
    assert (
        collection_embedding_model_resolver.get_default_by_collection_id(
            session=db_session, collection_id=collection.collection_id
        )
        == first_model_id
    )

    # Override default model with set_as_default=True.
    second_model_id = embedding_manager.register_embedding_model(
        session=db_session,
        embedding_generator=RandomEmbeddingGenerator(),
        collection_id=collection.collection_id,
        set_as_default=True,
    ).embedding_model_id

    assert (
        embedding_manager._collection_id_to_default_model_id[collection.collection_id]
        == second_model_id
    )


def test_embed_videos(
    db_session: Session,
) -> None:
    """Test generating embeddings for video samples."""
    video_collection = create_collection(session=db_session, sample_type=SampleType.VIDEO)
    collection_id = video_collection.collection_id
    video_ids = create_videos(
        session=db_session,
        collection_id=collection_id,
        videos=[
            VideoStub(path=f"/videos/video_{idx}.mp4", duration_s=1.0 + idx, fps=24.0)
            for idx in range(3)
        ],
    )
    manager = EmbeddingManager()
    model_id = manager.register_embedding_model(
        session=db_session,
        embedding_generator=RandomEmbeddingGenerator(),
        collection_id=collection_id,
        set_as_default=True,
    ).embedding_model_id

    manager.embed_videos(session=db_session, collection_id=collection_id, sample_ids=video_ids)

    stored_embeddings = db_session.exec(
        select(SampleEmbeddingTable).where(SampleEmbeddingTable.embedding_model_id == model_id)
    ).all()
    assert len(stored_embeddings) == len(video_ids)
    for embedding in stored_embeddings:
        assert len(embedding.embedding) == 3
        assert embedding.sample_id in video_ids


def test_embed_videos__raises_when_a_video_is_missing(
    db_session: Session,
) -> None:
    """Raises a ValueError when a sample_id has no video, instead of embedding a subset."""
    video_collection = create_collection(session=db_session, sample_type=SampleType.VIDEO)
    collection_id = video_collection.collection_id
    video_ids = create_videos(
        session=db_session,
        collection_id=collection_id,
        videos=[VideoStub(path="/videos/video_0.mp4", duration_s=1.0, fps=24.0)],
    )
    manager = EmbeddingManager()
    manager.register_embedding_model(
        session=db_session,
        embedding_generator=RandomEmbeddingGenerator(),
        collection_id=collection_id,
        set_as_default=True,
    )

    missing_id = UUID(int=1234567)
    with pytest.raises(ValueError, match="Could not fetch all video paths"):
        manager.embed_videos(
            session=db_session,
            collection_id=collection_id,
            sample_ids=[*video_ids, missing_id],
        )


def test_embed_videos_skips_broken_videos(
    db_session: Session,
) -> None:
    """A generator that drops a broken video stores embeddings only for the kept ones."""

    class DropsMiddleVideoGenerator(RandomEmbeddingGenerator):
        def embed_videos(self, filepaths: list[str]) -> EmbeddingResult:  # noqa: ARG002
            # Simulate the middle video being broken and skipped.
            return EmbeddingResult(
                embeddings=np.zeros((2, self._dimension), dtype=np.float32),
                kept_indices=[0, 2],
            )

    video_collection = create_collection(session=db_session, sample_type=SampleType.VIDEO)
    collection_id = video_collection.collection_id
    video_ids = create_videos(
        session=db_session,
        collection_id=collection_id,
        videos=[
            VideoStub(path="/videos/video_0.mp4", duration_s=1.0, fps=24.0),
            VideoStub(path="/videos/video_1.mp4", duration_s=2.0, fps=24.0),
            VideoStub(path="/videos/video_2.mp4", duration_s=3.0, fps=24.0),
        ],
    )
    manager = EmbeddingManager()
    model_id = manager.register_embedding_model(
        session=db_session,
        embedding_generator=DropsMiddleVideoGenerator(),
        collection_id=collection_id,
        set_as_default=True,
    ).embedding_model_id

    manager.embed_videos(session=db_session, collection_id=collection_id, sample_ids=video_ids)

    stored_embeddings = db_session.exec(
        select(SampleEmbeddingTable).where(SampleEmbeddingTable.embedding_model_id == model_id)
    ).all()
    stored_sample_ids = {embedding.sample_id for embedding in stored_embeddings}
    # The middle video was skipped, so only the first and third sample IDs are stored.
    assert stored_sample_ids == {video_ids[0], video_ids[2]}


def test_embed_videos_with_incompatible_generator(db_session: Session) -> None:
    """Ensure we raise when the default lacks video support."""
    video_collection = create_collection(session=db_session, sample_type=SampleType.VIDEO)
    collection_id = video_collection.collection_id
    manager = EmbeddingManager()
    manager.register_embedding_model(
        session=db_session,
        embedding_generator=TextOnlyEmbeddingGenerator(),
        collection_id=collection_id,
        set_as_default=True,
    )

    with pytest.raises(ValueError, match=r"Embedding model not compatible with videos."):
        manager.embed_videos(session=db_session, collection_id=collection_id, sample_ids=[uuid4()])


class TextOnlyEmbeddingGenerator:
    """Simple embedding generator that only supports text embeddings."""

    def __init__(self, dimension: int = 3) -> None:
        self._dimension = dimension

    def embedding_space_spec(self) -> EmbeddingSpaceSpec:
        return EmbeddingSpaceSpec(
            space_key="text_only_model",
            dimension=self._dimension,
        )

    def embed_text(self, text: str) -> list[float]:
        _ = text
        return [0.1 for _ in range(self._dimension)]


def test_compute_image_embedding(
    db_session: Session,
    collection: CollectionTable,
) -> None:
    """Test generating an image embedding without storing it."""
    # Register model
    embedding_manager = EmbeddingManager()
    model_id = embedding_manager.register_embedding_model(
        session=db_session,
        embedding_generator=RandomEmbeddingGenerator(),
        collection_id=collection.collection_id,
        set_as_default=True,
    ).embedding_model_id

    # Compute embedding for a single image
    embedding = embedding_manager.compute_image_embedding(
        collection_id=collection.collection_id, filepath="/path/to/image.jpg"
    )

    # Verify embedding
    assert len(embedding) == 3  # dimension=3

    # Verify NO embeddings were stored in the database for this operation
    stored_embeddings = db_session.exec(
        select(SampleEmbeddingTable).where(SampleEmbeddingTable.embedding_model_id == model_id)
    ).all()
    assert len(stored_embeddings) == 0


# Dimension of the model registered by _register_random_model, used to build
# well-formed test embeddings below.
_RANDOM_MODEL_DIMENSION = 3


def test_validate_and_coerce_embeddings(
    db_session: Session,
    collection: CollectionTable,
) -> None:
    """A well-formed batch of embeddings passes validation unchanged."""
    model_id = _register_random_model(session=db_session, collection=collection)
    sample_ids = [uuid4(), uuid4()]
    embeddings = np.zeros((2, _RANDOM_MODEL_DIMENSION), dtype=np.float32)

    result = embedding_manager._validate_and_coerce_embeddings(
        session=db_session, model_id=model_id, sample_ids=sample_ids, embeddings=embeddings
    )

    assert result.dtype == np.float32
    np.testing.assert_array_equal(result, embeddings)


def test_validate_and_coerce_embeddings__empty_is_valid(
    db_session: Session,
    collection: CollectionTable,
) -> None:
    """An empty batch passes validation without touching the embedding model."""
    model_id = _register_random_model(session=db_session, collection=collection)

    result = embedding_manager._validate_and_coerce_embeddings(
        session=db_session,
        model_id=model_id,
        sample_ids=[],
        embeddings=np.zeros((0, _RANDOM_MODEL_DIMENSION), dtype=np.float32),
    )

    assert len(result) == 0


def test_validate_and_coerce_embeddings__rejects_non_2d_array(
    db_session: Session,
    collection: CollectionTable,
) -> None:
    """A 0-D array raises a clear ValueError instead of TypeError from `len()`."""
    model_id = _register_random_model(session=db_session, collection=collection)
    sample_ids = [uuid4()]
    embeddings = np.array(1.0, dtype=np.float32)

    with pytest.raises(ValueError, match=r"must be a 2-D array .* got a 0-D array"):
        embedding_manager._validate_and_coerce_embeddings(
            session=db_session,
            model_id=model_id,
            sample_ids=sample_ids,
            embeddings=embeddings,
        )


def test_validate_and_coerce_embeddings__count_mismatch(
    db_session: Session,
    collection: CollectionTable,
) -> None:
    """A different number of embeddings and sample IDs raises a clear error."""
    model_id = _register_random_model(session=db_session, collection=collection)
    sample_ids = [uuid4(), uuid4()]
    embeddings = np.zeros((1, _RANDOM_MODEL_DIMENSION), dtype=np.float32)

    with pytest.raises(ValueError, match=r"does not match number of sample IDs"):
        embedding_manager._validate_and_coerce_embeddings(
            session=db_session, model_id=model_id, sample_ids=sample_ids, embeddings=embeddings
        )


def test_validate_and_coerce_embeddings__wrong_dimension(
    db_session: Session,
    collection: CollectionTable,
) -> None:
    """A vector whose length doesn't match embedding_dimension raises a clear error."""
    model_id = _register_random_model(session=db_session, collection=collection)
    sample_ids = [uuid4()]
    wrong_dimension = _RANDOM_MODEL_DIMENSION + 1
    embeddings = np.zeros((1, wrong_dimension), dtype=np.float32)

    with pytest.raises(ValueError, match=rf"Embedding dimension \({wrong_dimension}\)"):
        embedding_manager._validate_and_coerce_embeddings(
            session=db_session, model_id=model_id, sample_ids=sample_ids, embeddings=embeddings
        )


def test_validate_and_coerce_embeddings__casts_float64_to_float32(
    db_session: Session,
    collection: CollectionTable,
) -> None:
    """A float64 array (the numpy default) is safely cast down to float32, not rejected."""
    model_id = _register_random_model(session=db_session, collection=collection)
    sample_ids = [uuid4()]
    embeddings = np.array(
        [[0.1 * (i + 1) for i in range(_RANDOM_MODEL_DIMENSION)]], dtype=np.float64
    )

    result = embedding_manager._validate_and_coerce_embeddings(
        session=db_session,
        model_id=model_id,
        sample_ids=sample_ids,
        embeddings=embeddings,  # type: ignore[arg-type]
    )

    assert result.dtype == np.float32
    np.testing.assert_allclose(result, embeddings, rtol=1e-6)


def test_validate_and_coerce_embeddings__rejects_non_numeric_dtype(
    db_session: Session,
    collection: CollectionTable,
) -> None:
    """A non-numeric dtype (e.g. strings) is rejected."""
    model_id = _register_random_model(session=db_session, collection=collection)
    sample_ids = [uuid4()]
    embeddings = np.array([[f"s{i}" for i in range(_RANDOM_MODEL_DIMENSION)]])

    with pytest.raises(ValueError, match=r"must be numeric"):
        embedding_manager._validate_and_coerce_embeddings(
            session=db_session,
            model_id=model_id,
            sample_ids=sample_ids,
            embeddings=embeddings,
        )


def test_validate_and_coerce_embeddings__rejects_overflow_from_cast(
    db_session: Session,
    collection: CollectionTable,
) -> None:
    """A float64 value too large for float32 overflows to Inf and is rejected."""
    model_id = _register_random_model(session=db_session, collection=collection)
    sample_ids = [uuid4()]
    embeddings = np.zeros((1, _RANDOM_MODEL_DIMENSION), dtype=np.float64)
    embeddings[0, 0] = 1e308  # Too large to represent as float32.

    with pytest.raises(ValueError, match=r"NaN or infinite"):
        embedding_manager._validate_and_coerce_embeddings(
            session=db_session,
            model_id=model_id,
            sample_ids=sample_ids,
            embeddings=embeddings,  # type: ignore[arg-type]
        )


def test_validate_and_coerce_embeddings__nan(
    db_session: Session,
    collection: CollectionTable,
) -> None:
    """A NaN value in an embedding raises a clear error."""
    model_id = _register_random_model(session=db_session, collection=collection)
    sample_ids = [uuid4()]
    embeddings = np.full((1, _RANDOM_MODEL_DIMENSION), np.nan, dtype=np.float32)

    with pytest.raises(ValueError, match=r"NaN or infinite"):
        embedding_manager._validate_and_coerce_embeddings(
            session=db_session, model_id=model_id, sample_ids=sample_ids, embeddings=embeddings
        )


def test_validate_and_coerce_embeddings__inf(
    db_session: Session,
    collection: CollectionTable,
) -> None:
    """An infinite value in an embedding raises a clear error."""
    model_id = _register_random_model(session=db_session, collection=collection)
    sample_ids = [uuid4()]
    embeddings = np.full((1, _RANDOM_MODEL_DIMENSION), np.inf, dtype=np.float32)

    with pytest.raises(ValueError, match=r"NaN or infinite"):
        embedding_manager._validate_and_coerce_embeddings(
            session=db_session, model_id=model_id, sample_ids=sample_ids, embeddings=embeddings
        )


def test_store_embeddings__rejects_invalid_embeddings_before_write(
    db_session: Session,
    collection: CollectionTable,
) -> None:
    """_store_embeddings raises before writing anything to the database."""
    model_id = _register_random_model(session=db_session, collection=collection)
    sample_ids = [uuid4()]
    embeddings = np.full((1, _RANDOM_MODEL_DIMENSION), np.nan, dtype=np.float32)

    with pytest.raises(ValueError, match=r"NaN or infinite"):
        embedding_manager._store_embeddings(
            session=db_session,
            model_id=model_id,
            sample_ids=sample_ids,
            embeddings=embeddings,
            show_progress=False,
        )

    stored_embeddings = db_session.exec(
        select(SampleEmbeddingTable).where(SampleEmbeddingTable.embedding_model_id == model_id)
    ).all()
    assert len(stored_embeddings) == 0


def test_store_embeddings__casts_float64_embeddings(
    db_session: Session,
    collection: CollectionTable,
) -> None:
    """_store_embeddings accepts and stores embeddings passed in as float64."""
    model_id = _register_random_model(session=db_session, collection=collection)
    image = create_image(session=db_session, collection_id=collection.collection_id)
    sample_ids = [image.sample_id]
    embeddings = np.array(
        [[0.1 * (i + 1) for i in range(_RANDOM_MODEL_DIMENSION)]], dtype=np.float64
    )

    embedding_manager._store_embeddings(
        session=db_session,
        model_id=model_id,
        sample_ids=sample_ids,
        embeddings=embeddings,  # type: ignore[arg-type]
        show_progress=False,
    )

    stored_embeddings = db_session.exec(
        select(SampleEmbeddingTable).where(SampleEmbeddingTable.embedding_model_id == model_id)
    ).all()
    assert len(stored_embeddings) == 1
    assert len(stored_embeddings[0].embedding) == _RANDOM_MODEL_DIMENSION


def _register_random_model(session: Session, collection: CollectionTable) -> UUID:
    """Register a RandomEmbeddingGenerator with dimension `_RANDOM_MODEL_DIMENSION`."""
    manager = EmbeddingManager()
    return manager.register_embedding_model(
        session=session,
        embedding_generator=RandomEmbeddingGenerator(dimension=_RANDOM_MODEL_DIMENSION),
        collection_id=collection.collection_id,
        set_as_default=True,
    ).embedding_model_id
