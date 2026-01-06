"""Embedding manager for dataset processing."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from uuid import UUID

from sqlmodel import Session

from lightly_studio.dataset import env
from lightly_studio.dataset.embedding_generator import (
    EmbeddingGenerator,
    ImageEmbeddingGenerator,
    VideoEmbeddingGenerator,
)
from lightly_studio.models.collection import SampleType
from lightly_studio.models.embedding_model import EmbeddingModelTable
from lightly_studio.models.sample_embedding import SampleEmbeddingCreate
from lightly_studio.resolvers import (
    collection_resolver,
    embedding_model_resolver,
    image_resolver,
    sample_embedding_resolver,
    video_resolver,
)

logger = logging.getLogger(__name__)


class EmbeddingManagerProvider:
    """Provider for the EmbeddingManager singleton instance."""

    _instance: EmbeddingManager | None = None

    @classmethod
    def get_embedding_manager(cls) -> EmbeddingManager:
        """Get the singleton instance of EmbeddingManager.

        Returns:
            The singleton instance of EmbeddingManager.

        Raises:
            ValueError: If no instance exists and no session is provided.
        """
        if cls._instance is None:
            cls._instance = EmbeddingManager()
        return cls._instance


@dataclass
class TextEmbedQuery:
    """Parameters for text embedding generation."""

    text: str
    embedding_model_id: UUID | None = None


class EmbeddingManager:
    """Manages embedding models and handles embedding generation and storage."""

    def __init__(self) -> None:
        """Initialize the embedding manager."""
        self._models: dict[UUID, EmbeddingGenerator] = {}
        self._dataset_id_to_default_model_id: dict[UUID, UUID] = {}

    def register_embedding_model(
        self,
        session: Session,
        collection_id: UUID,
        embedding_generator: EmbeddingGenerator,
        set_as_default: bool = False,
    ) -> EmbeddingModelTable:
        """Register an embedding model in the database.

        The model is stored in an internal dictionary for later use.
        The model is set as default if requested or if it's the first model.

        Args:
            session: Database session for resolver operations.
            collection_id: The ID of the collection to associate with the model.
                And to register as default, if requested.
            embedding_generator: The model implementation used for embeddings.
            set_as_default: Whether to set this model as the default.

        Returns:
            The created EmbeddingModel.
        """
        # Get or create embedding model record in the database.
        db_model = embedding_model_resolver.get_or_create(
            session=session,
            embedding_model=embedding_generator.get_embedding_model_input(
                collection_id=collection_id
            ),
        )
        model_id = db_model.embedding_model_id

        # Store the model in our dictionary
        self._models[model_id] = embedding_generator

        # Set as default if requested or if it's the first model
        if set_as_default or collection_id not in self._dataset_id_to_default_model_id:
            self._dataset_id_to_default_model_id[collection_id] = model_id

        return db_model

    def embed_text(self, collection_id: UUID, text_query: TextEmbedQuery) -> list[float]:
        """Generate an embedding for a text sample.

        Args:
            collection_id: The ID of the collection to determine the registered default model.
                It is used if embedding_model_id is not valid.
            text_query: Text embedding query containing text and model ID.

        Returns:
            A list of floats representing the generated embedding.
        """
        model_id = self._get_default_or_validate(
            collection_id=collection_id, embedding_model_id=text_query.embedding_model_id
        )

        model = self._models[model_id]

        return model.embed_text(text_query.text)

    def embed_images(
        self,
        session: Session,
        collection_id: UUID,
        sample_ids: list[UUID],
        embedding_model_id: UUID | None = None,
    ) -> None:
        """Generate and store embeddings for image samples.

        Args:
            session: Database session for resolver operations.
            collection_id: The ID of the collection to determine the registered default model.
                It is used if embedding_model_id is not valid.
            sample_ids: List of sample IDs to generate embeddings for.
            embedding_model_id: ID of the model to use. Uses default if None.

        Raises:
            ValueError: If no embedding model is registered, provided model
            ID doesn't exist or if the embedding model does not support images.
        """
        model_id = self._get_default_or_validate(
            collection_id=collection_id, embedding_model_id=embedding_model_id
        )

        model = self._models[model_id]
        if not isinstance(model, ImageEmbeddingGenerator):
            raise ValueError("Embedding model not compatible with images.")

        # Query image filenames from the database.
        sample_id_to_filepath = {
            sample.sample_id: sample.file_path_abs
            for sample in image_resolver.get_many_by_id(
                session=session,
                sample_ids=sample_ids,
            )
        }

        # Extract filepaths in the same order as sample_ids.
        filepaths = [sample_id_to_filepath[sample_id] for sample_id in sample_ids]

        # Generate embeddings for the samples.
        embeddings = model.embed_images(filepaths=filepaths)

        # Convert to SampleEmbeddingCreate objects.
        sample_embeddings = [
            SampleEmbeddingCreate(
                sample_id=sample_id,
                embedding_model_id=model_id,
                embedding=embedding,
            )
            for sample_id, embedding in zip(sample_ids, embeddings)
        ]

        # Store the embeddings in the database.
        sample_embedding_resolver.create_many(session=session, sample_embeddings=sample_embeddings)

    def compute_image_embedding(
        self,
        collection_id: UUID,
        filepath: str,
        embedding_model_id: UUID | None = None,
    ) -> list[float]:
        """Generate an embedding for a single image without storing it.

        Args:
            collection_id: The ID of the collection to determine the registered default model.
                It is used if embedding_model_id is not valid.
            filepath: Path to the image file to generate an embedding for.
            embedding_model_id: ID of the model to use. Uses default if None.

        Returns:
            A list of floats representing the generated embedding.

        Raises:
            ValueError: If no embedding model is registered, provided model
            ID doesn't exist or if the embedding model does not support images.
        """
        model_id = self._get_default_or_validate(
            collection_id=collection_id, embedding_model_id=embedding_model_id
        )

        model = self._models[model_id]
        if not isinstance(model, ImageEmbeddingGenerator):
            raise ValueError("Embedding model not compatible with images.")

        # Generate embedding for the image without progress bar.
        embeddings = model.embed_images(filepaths=[filepath], show_progress=False)

        # Return the single embedding as a list of floats.
        result: list[float] = embeddings[0].tolist()
        return result

    def embed_videos(
        self,
        session: Session,
        collection_id: UUID,
        sample_ids: list[UUID],
        embedding_model_id: UUID | None = None,
    ) -> None:
        """Generate and store embeddings for video samples.

        Args:
            session: Database session for resolver operations.
            collection_id: The ID of the collection to determine the registered default model.
                It is used if embedding_model_id is not valid.
            sample_ids: List of sample IDs to generate embeddings for.
            embedding_model_id: ID of the model to use. Uses default if None.

        Raises:
            ValueError: If no embedding model is registered, provided model
            ID doesn't exist or if the embedding model does not support videos.
        """
        model_id = self._get_default_or_validate(
            collection_id=collection_id, embedding_model_id=embedding_model_id
        )

        model = self._models[model_id]
        if not isinstance(model, VideoEmbeddingGenerator):
            raise ValueError("Embedding model not compatible with videos.")

        # Get the samples
        filepaths = []
        for sample_id in sample_ids:
            sample = video_resolver.get_by_id(session=session, sample_id=sample_id)
            if sample is not None:
                filepaths.append(sample.file_path_abs)

        if len(filepaths) != len(sample_ids):
            raise ValueError("Could not fetch all video paths for the provided IDs.")

        # Generate embeddings for the samples.
        embeddings = model.embed_videos(filepaths=filepaths)

        # Convert to SampleEmbeddingCreate objects.
        sample_embeddings = [
            SampleEmbeddingCreate(
                sample_id=sample_id,
                embedding_model_id=model_id,
                embedding=embedding,
            )
            for sample_id, embedding in zip(sample_ids, embeddings)
        ]

        # Store the embeddings in the database.
        sample_embedding_resolver.create_many(session=session, sample_embeddings=sample_embeddings)

    def load_or_get_default_model(
        self,
        session: Session,
        collection_id: UUID,
    ) -> UUID | None:
        """Ensure a default embedding model exists and return its ID.

        Args:
            session: Database session for resolver operations.
            collection_id: Collection identifier the model should belong to.

        Returns:
            UUID of the default embedding model or None if the model cannot be loaded.
        """
        # Return the existing default model ID if available.

        if collection_id in self._dataset_id_to_default_model_id:
            return self._dataset_id_to_default_model_id[collection_id]

        # Load the embedding generator based on sample_type from the env var.
        dataset = collection_resolver.get_by_id(session=session, collection_id=collection_id)
        if dataset is None:
            raise ValueError("Provided dataset_id could not be found.")

        embedding_generator = _load_embedding_generator_from_env(sample_type=dataset.sample_type)
        if embedding_generator is None:
            return None

        # Register the embedding model and set it as default.
        embedding_model = self.register_embedding_model(
            session=session,
            collection_id=collection_id,
            embedding_generator=embedding_generator,
            set_as_default=True,
        )

        return embedding_model.embedding_model_id

    def _get_default_or_validate(
        self, collection_id: UUID, embedding_model_id: UUID | None
    ) -> UUID:
        """Get a valid model_id or raise error of non available.

        If embedding_model_id is not provided, returns the default model for collection_id.
        If embedding_model_id is provided, validates that the model has been loaded and returns it.
        """
        default_model_id = self._dataset_id_to_default_model_id.get(collection_id, None)
        if embedding_model_id is None and default_model_id is None:
            raise ValueError(
                "No embedding_model_id provided and no default embedding model registered."
            )

        if embedding_model_id is None and default_model_id is not None:
            return default_model_id

        if embedding_model_id not in self._models:
            raise ValueError(f"No embedding model found with ID {embedding_model_id}")
        return embedding_model_id


def _load_embedding_generator_from_env(sample_type: SampleType) -> EmbeddingGenerator | None:
    """Load the embedding generator based on environment variable configuration."""
    if sample_type == SampleType.IMAGE:
        return _load_image_embedding_generator_from_env()
    if sample_type == SampleType.VIDEO:
        return _load_video_embedding_generator()
    return None


# TODO(Michal, 09/2025): Write tests for this function.
def _load_image_embedding_generator_from_env() -> ImageEmbeddingGenerator | None:
    if env.LIGHTLY_STUDIO_EMBEDDINGS_MODEL_TYPE == "EDGE":
        try:
            from lightly_studio.dataset.edge_embedding_generator import (
                EdgeSDKEmbeddingGenerator,
            )

            logger.info("Using LightlyEdge embedding generator for images.")
            return EdgeSDKEmbeddingGenerator(model_path=env.LIGHTLY_STUDIO_EDGE_MODEL_FILE_PATH)
        except ImportError:
            logger.warning("Embedding functionality is disabled.")
    elif env.LIGHTLY_STUDIO_EMBEDDINGS_MODEL_TYPE == "MOBILE_CLIP":
        try:
            from lightly_studio.dataset.mobileclip_embedding_generator import (
                MobileCLIPEmbeddingGenerator,
            )

            logger.info("Using MobileCLIP embedding generator for images.")
            return MobileCLIPEmbeddingGenerator()
        except ImportError:
            logger.warning("Embedding functionality is disabled.")
    elif env.LIGHTLY_STUDIO_EMBEDDINGS_MODEL_TYPE == "PE":
        try:
            from lightly_studio.dataset.perception_encoder_embedding_generator import (
                PerceptionEncoderEmbeddingGenerator,
            )

            logger.info("Using PerceptionEncoder embedding generator for images.")
            return PerceptionEncoderEmbeddingGenerator()
        except ImportError:
            logger.warning("Embedding functionality is disabled.")
    else:
        logger.warning(f"Unsupported model type: '{env.LIGHTLY_STUDIO_EMBEDDINGS_MODEL_TYPE}'")
        logger.warning("Embedding functionality is disabled.")
    return None


def _load_video_embedding_generator() -> VideoEmbeddingGenerator | None:
    try:
        from lightly_studio.dataset.perception_encoder_embedding_generator import (
            PerceptionEncoderEmbeddingGenerator,
        )

        logger.info("Using PerceptionEncoder embedding generator for videos.")
        return PerceptionEncoderEmbeddingGenerator()
    except ImportError:
        logger.warning("Embedding functionality is disabled.")
        return None
