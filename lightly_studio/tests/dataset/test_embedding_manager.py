"""Unit tests for the EmbeddingManager class."""

from __future__ import annotations

from uuid import UUID, uuid4

import numpy as np
import pytest
from numpy.typing import NDArray
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
from lightly_studio.models.dataset import DatasetTable, SampleType
from lightly_studio.models.embedding_model import EmbeddingModelCreate, EmbeddingModelTable
from lightly_studio.models.image import ImageTable
from lightly_studio.models.sample_embedding import SampleEmbeddingTable
from lightly_studio.resolvers import embedding_model_resolver
from tests.helpers_resolvers import create_dataset
from tests.resolvers.video.helpers import VideoStub, create_videos


def test_register_embedding_model(
    db_session: Session,
    dataset: DatasetTable,
) -> None:
    """Test registering an embedding model."""
    # Register the model.
    embedding_manager = EmbeddingManager()
    random_model = RandomEmbeddingGenerator()
    model_id = embedding_manager.register_embedding_model(
        session=db_session,
        embedding_generator=random_model,
        dataset_id=dataset.dataset_id,
        set_as_default=True,
    ).embedding_model_id

    # Check that the model was registered in memory.
    assert model_id in embedding_manager._models
    assert embedding_manager._models[model_id] == random_model
    assert embedding_manager._default_model_id == model_id

    # Check that the model was stored in the database.
    stored_model = db_session.exec(
        select(EmbeddingModelTable).where(EmbeddingModelTable.embedding_model_id == model_id)
    ).first()
    assert stored_model is not None
    assert stored_model.name == "Random"
    assert stored_model.embedding_dimension == 3


def test_register_multiple_models(
    db_session: Session,
    dataset: DatasetTable,
) -> None:
    """Test registering multiple embedding models."""
    # Register first model.
    embedding_manager = EmbeddingManager()
    model_id1 = embedding_manager.register_embedding_model(
        session=db_session,
        embedding_generator=RandomEmbeddingGenerator(),
        dataset_id=dataset.dataset_id,
        set_as_default=True,
    ).embedding_model_id

    # Register a second model.
    class FakeEmbeddingGenerator(ImageEmbeddingGenerator):
        def get_embedding_model_input(self, dataset_id: UUID) -> EmbeddingModelCreate:
            return EmbeddingModelCreate(
                name="Fake",
                dataset_id=dataset_id,
                embedding_model_hash="fake_hash",
                parameter_count_in_mb=50,
                embedding_dimension=5,
            )

        def embed_text(self, text: str) -> list[float]:
            raise NotImplementedError()

        def embed_images(self, filepaths: list[str]) -> NDArray[np.float32]:
            raise NotImplementedError()

    model_id2 = embedding_manager.register_embedding_model(
        session=db_session,
        embedding_generator=FakeEmbeddingGenerator(),
        dataset_id=dataset.dataset_id,
        set_as_default=False,
    ).embedding_model_id

    # Check that both models were registered in memory
    assert model_id1 in embedding_manager._models
    assert model_id2 in embedding_manager._models
    assert embedding_manager._default_model_id == model_id1

    # Check that both models were stored in the database
    stored_models = db_session.exec(select(EmbeddingModelTable)).all()
    assert len(stored_models) == 2
    model_names = {model.name for model in stored_models}
    assert model_names == {"Random", "Fake"}
    # Verify both models are associated with the same dataset
    assert all(model.dataset_id == dataset.dataset_id for model in stored_models)


def test_embed_text_with_default_model(
    db_session: Session,
    dataset: DatasetTable,
) -> None:
    """Test generating text embeddings with default model."""
    # Register model.
    embedding_manager = EmbeddingManager()
    embedding_manager.register_embedding_model(
        session=db_session,
        embedding_generator=RandomEmbeddingGenerator(),
        dataset_id=dataset.dataset_id,
        set_as_default=True,
    )

    # Generate embedding.
    query = TextEmbedQuery(text="test text")
    embedding = embedding_manager.embed_text(query)

    # Check embedding.
    assert len(embedding) == 3


def test_embed_text_with_specific_model(
    db_session: Session,
    dataset: DatasetTable,
) -> None:
    """Test generating text embeddings with specific model."""
    # Register model.
    embedding_manager = EmbeddingManager()
    model_id = embedding_manager.register_embedding_model(
        session=db_session,
        embedding_generator=RandomEmbeddingGenerator(),
        dataset_id=dataset.dataset_id,
        set_as_default=True,
    ).embedding_model_id

    # Generate embedding with specific model.
    query = TextEmbedQuery(text="test text", embedding_model_id=model_id)
    embedding = embedding_manager.embed_text(query)

    # Check embedding.
    assert len(embedding) == 3


def test_embed_text_without_model() -> None:
    """Test generating text embeddings without registered model."""
    embedding_manager = EmbeddingManager()
    query = TextEmbedQuery(text="test text")
    with pytest.raises(ValueError, match="No embedding model specified"):
        embedding_manager.embed_text(query)


def test_embed_text_with_invalid_model(
    db_session: Session,
    dataset: DatasetTable,
) -> None:
    """Test generating text embeddings with invalid model ID."""
    # Register model
    embedding_manager = EmbeddingManager()
    embedding_manager.register_embedding_model(
        session=db_session,
        embedding_generator=RandomEmbeddingGenerator(),
        dataset_id=dataset.dataset_id,
        set_as_default=True,
    )
    invalid_model_id = uuid4()
    query = TextEmbedQuery(text="test text", embedding_model_id=invalid_model_id)
    with pytest.raises(
        ValueError,
        match=f"Embedding model with ID {invalid_model_id} not found.",
    ):
        embedding_manager.embed_text(query)


def test_embed_images(
    db_session: Session,
    dataset: DatasetTable,
    samples: list[ImageTable],
) -> None:
    """Test generating and storing image embeddings."""
    # Register model
    embedding_manager = EmbeddingManager()
    model_id = embedding_manager.register_embedding_model(
        session=db_session,
        embedding_generator=RandomEmbeddingGenerator(),
        dataset_id=dataset.dataset_id,
        set_as_default=True,
    ).embedding_model_id

    # Generate embeddings for samples
    sample_ids = [sample.sample_id for sample in samples]
    embedding_manager.embed_images(session=db_session, sample_ids=sample_ids)

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
    dataset: DatasetTable,
) -> None:
    """Ensure we surface a clear error when the model doesn't support images."""
    manager = EmbeddingManager()
    manager.register_embedding_model(
        session=db_session,
        embedding_generator=TextOnlyEmbeddingGenerator(),
        dataset_id=dataset.dataset_id,
        set_as_default=True,
    )

    with pytest.raises(ValueError, match=r"Embedding model not compatible with images."):
        manager.embed_images(session=db_session, sample_ids=[uuid4()])


def test_get_valid_model_id_without_default_model() -> None:
    """_get_valid_model_id raises when there is no default or explicit ID."""
    manager = EmbeddingManager()
    with pytest.raises(
        ValueError,
        match=r"No embedding_model_id provided and no default embedding model registered.",
    ):
        manager._get_default_or_validate(embedding_model_id=None)


def test_get_valid_model_id_with_invalid_requested_model(
    db_session: Session,
    dataset: DatasetTable,
) -> None:
    """_get_valid_model_id raises when the provided ID is unknown."""
    manager = EmbeddingManager()
    manager.register_embedding_model(
        session=db_session,
        embedding_generator=RandomEmbeddingGenerator(),
        dataset_id=dataset.dataset_id,
        set_as_default=True,
    )
    missing_model_id = uuid4()
    with pytest.raises(
        ValueError,
        match=f"No embedding model found with ID {missing_model_id}",
    ):
        manager._get_default_or_validate(embedding_model_id=missing_model_id)


def test_get_valid_model_id_with_default_and_explicit_id(
    db_session: Session,
    dataset: DatasetTable,
) -> None:
    """_get_valid_model_id prefers explicit IDs but falls back to default."""
    manager = EmbeddingManager()
    default_model_id = manager.register_embedding_model(
        session=db_session,
        embedding_generator=RandomEmbeddingGenerator(),
        dataset_id=dataset.dataset_id,
        set_as_default=True,
    ).embedding_model_id
    assert manager._get_default_or_validate(embedding_model_id=None) == default_model_id

    other_model_id = manager.register_embedding_model(
        session=db_session,
        embedding_generator=RandomEmbeddingGenerator(),
        dataset_id=dataset.dataset_id,
        set_as_default=False,
    ).embedding_model_id
    assert manager._get_default_or_validate(embedding_model_id=other_model_id) == other_model_id


def test_load_or_get_default_model(
    db_session: Session,
    mocker: MockerFixture,
) -> None:
    dataset = create_dataset(session=db_session)
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
        dataset_id=dataset.dataset_id,
    )
    assert model_id is not None

    # Verify we got back the random model.
    mock_load.assert_called_once_with()
    model = embedding_model_resolver.get_by_id(session=db_session, embedding_model_id=model_id)
    assert model is not None
    assert model.name == "Random"

    # Second registration should be a no-op and return the same ID.
    second_id = manager.load_or_get_default_model(
        session=db_session,
        dataset_id=dataset.dataset_id,
    )
    assert model_id == second_id
    mock_load.assert_called_once_with()  # still only one call


def test_load_or_get_default_model__cant_load(
    db_session: Session,
    mocker: MockerFixture,
) -> None:
    """If the loader returns None, no model should be registered."""
    dataset = create_dataset(session=db_session)
    manager = EmbeddingManager()

    mock_load = mocker.patch.object(
        embedding_manager,
        "_load_embedding_generator_from_env",
        return_value=None,
    )

    model_id = manager.load_or_get_default_model(
        session=db_session,
        dataset_id=dataset.dataset_id,
    )

    mock_load.assert_called_once_with()
    assert model_id is None


def test_default_model(
    db_session: Session,
    dataset: DatasetTable,
) -> None:
    """Test default model functionality."""
    embedding_manager = EmbeddingManager()
    first_model_id = embedding_manager.register_embedding_model(
        session=db_session,
        embedding_generator=RandomEmbeddingGenerator(),
        dataset_id=dataset.dataset_id,
        set_as_default=False,
    ).embedding_model_id
    # The first model is always set as default.
    assert embedding_manager._default_model_id == first_model_id

    # Override default model with set_as_default=True.
    second_model_id = embedding_manager.register_embedding_model(
        session=db_session,
        embedding_generator=RandomEmbeddingGenerator(),
        dataset_id=dataset.dataset_id,
        set_as_default=True,
    ).embedding_model_id

    assert embedding_manager._default_model_id == second_model_id


def test_embed_videos(
    db_session: Session,
) -> None:
    """Test generating embeddings for video samples."""
    video_dataset = create_dataset(session=db_session, sample_type=SampleType.VIDEO)
    video_ids = create_videos(
        session=db_session,
        dataset_id=video_dataset.dataset_id,
        videos=[
            VideoStub(path=f"/videos/video_{idx}.mp4", duration_s=1.0 + idx, fps=24.0)
            for idx in range(3)
        ],
    )
    manager = EmbeddingManager()
    model_id = manager.register_embedding_model(
        session=db_session,
        embedding_generator=RandomEmbeddingGenerator(),
        dataset_id=video_dataset.dataset_id,
        set_as_default=True,
    ).embedding_model_id

    manager.embed_videos(session=db_session, sample_ids=video_ids)

    stored_embeddings = db_session.exec(
        select(SampleEmbeddingTable).where(SampleEmbeddingTable.embedding_model_id == model_id)
    ).all()
    assert len(stored_embeddings) == len(video_ids)
    for embedding in stored_embeddings:
        assert len(embedding.embedding) == 3
        assert embedding.sample_id in video_ids


def test_embed_videos_with_incompatible_generator(db_session: Session) -> None:
    """Ensure we raise when the default lacks video support."""
    video_dataset = create_dataset(session=db_session, sample_type=SampleType.VIDEO)
    manager = EmbeddingManager()
    manager.register_embedding_model(
        session=db_session,
        embedding_generator=TextOnlyEmbeddingGenerator(),
        dataset_id=video_dataset.dataset_id,
        set_as_default=True,
    )

    with pytest.raises(ValueError, match=r"Embedding model not compatible with videos."):
        manager.embed_videos(session=db_session, sample_ids=[uuid4()])


class TextOnlyEmbeddingGenerator:
    """Simple embedding generator that only supports text embeddings."""

    def __init__(self, dimension: int = 3) -> None:
        self._dimension = dimension

    def get_embedding_model_input(self, dataset_id: UUID) -> EmbeddingModelCreate:
        return EmbeddingModelCreate(
            name="TextOnly",
            dataset_id=dataset_id,
            embedding_dimension=self._dimension,
            embedding_model_hash="text_only_model",
        )

    def embed_text(self, text: str) -> list[float]:
        _ = text
        return [0.1 for _ in range(self._dimension)]
