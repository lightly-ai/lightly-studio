"""Embedding manager for dataset processing."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from uuid import UUID

import numpy as np
from numpy.typing import NDArray
from sqlmodel import Session
from tqdm import tqdm

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
    annotation_resolver,
    collection_resolver,
    embedding_model_resolver,
    image_resolver,
    sample_embedding_resolver,
    video_resolver,
)
from lightly_studio.utils import batching

logger = logging.getLogger(__name__)

# Number of embeddings inserted per database round-trip. Larger batches mean fewer
# round-trips but higher peak memory. 1024 balances the two.
EMBEDDING_INSERTION_BATCH_SIZE = 1024

# Number of annotation crops processed per chunk in embed_annotations.
ANNOTATION_EMBED_BATCH_SIZE = 2048
# Mapping of sample types to the generator type used for embedding generation.
_GENERATOR_SAMPLE_TYPE: dict[SampleType, SampleType] = {
    SampleType.IMAGE: SampleType.IMAGE,
    SampleType.ANNOTATION: SampleType.IMAGE,
    SampleType.VIDEO: SampleType.VIDEO,
}


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


def set_default_embedding_model(embedding_generator: EmbeddingGenerator) -> None:
    """Register a custom embedding model that overrides the env-var default.

    Call this before ingesting a dataset (e.g. before ImageDataset.load_or_create)
    to use your own generator instead of the model selected by
    LIGHTLY_STUDIO_EMBEDDINGS_MODEL_TYPE. The override applies to every collection.

    Note: the registration lives in-process only. When re-launching the GUI via the
    `lightly-studio gui` CLI without re-running this call, embeddings computed with the
    custom model remain, but text search falls back to the env-var default model and
    will not match them.

    Args:
        embedding_generator: A generator implementing ImageEmbeddingGenerator and/or
            VideoEmbeddingGenerator.
    """
    EmbeddingManagerProvider.get_embedding_manager().set_default_embedding_model(
        embedding_generator=embedding_generator
    )


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
        self._collection_id_to_default_model_id: dict[UUID, UUID] = {}
        self._sample_type_to_model_id: dict[SampleType, UUID] = {}
        # Generators registered by the user that override the env-var default.
        # Keyed by generator sample type (IMAGE or VIDEO) and consulted before
        # loading a generator from the environment.
        self._override_generators: dict[SampleType, EmbeddingGenerator] = {}

    def set_default_embedding_model(self, embedding_generator: EmbeddingGenerator) -> None:
        """Register a generator that overrides the env-var default for all collections.

        The generator's sample-type slot(s) are inferred from the protocols it
        implements: an ImageEmbeddingGenerator overrides image (and annotation and
        text) embeddings, a VideoEmbeddingGenerator overrides video embeddings, and a
        generator implementing both overrides both. This must be called before a
        collection loads its default model (e.g. before ingesting a dataset).

        Args:
            embedding_generator: The generator to use instead of the env-var default.

        Raises:
            TypeError: If the generator implements neither the image nor the video
                embedding protocol.
        """
        matched = False
        if isinstance(embedding_generator, ImageEmbeddingGenerator):
            self._override_generators[SampleType.IMAGE] = embedding_generator
            self._sample_type_to_model_id.pop(SampleType.IMAGE, None)
            matched = True
        if isinstance(embedding_generator, VideoEmbeddingGenerator):
            self._override_generators[SampleType.VIDEO] = embedding_generator
            self._sample_type_to_model_id.pop(SampleType.VIDEO, None)
            matched = True
        if not matched:
            raise TypeError(
                "embedding_generator must implement ImageEmbeddingGenerator or "
                "VideoEmbeddingGenerator."
            )

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
        if set_as_default or collection_id not in self._collection_id_to_default_model_id:
            self._collection_id_to_default_model_id[collection_id] = model_id

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

        _store_embeddings(
            session=session,
            model_id=model_id,
            sample_ids=sample_ids,
            embeddings=embeddings,
        )

    def embed_annotations(
        self,
        session: Session,
        annotation_collection_id: UUID,
        embedding_model_id: UUID | None = None,
    ) -> None:
        """Generate and store embeddings for annotation crops.

        Object-detection and segmentation-mask annotations are both embedded.

        Args:
            session: Database session for resolver operations.
            annotation_collection_id: The annotation collection whose annotation
                samples should receive embeddings.
            embedding_model_id: ID of the model to use. Uses default if None.

        Raises:
            ValueError: If no image-compatible embedding model is registered.
        """
        model_id = self._get_default_or_validate(
            collection_id=annotation_collection_id, embedding_model_id=embedding_model_id
        )
        model = self._models[model_id]
        if not isinstance(model, ImageEmbeddingGenerator):
            raise ValueError("Embedding model not compatible with images.")

        annotation_sample_ids = annotation_resolver.get_unembedded_annotation_ids(
            session=session,
            annotation_collection_id=annotation_collection_id,
            embedding_model_id=model_id,
        )
        if not annotation_sample_ids:
            logger.info("No annotation crops to embed.")
            return

        with tqdm(
            total=len(annotation_sample_ids),
            desc="Embedding annotations",
            unit=" crops",
        ) as progress:
            for sample_id_chunk in batching.batched(
                items=annotation_sample_ids, batch_size=ANNOTATION_EMBED_BATCH_SIZE
            ):
                annotation_crops = annotation_resolver.get_annotation_crops_for_ids(
                    session=session, annotation_sample_ids=sample_id_chunk
                )
                if not annotation_crops:
                    continue

                embeddings = model.embed_image_crops(
                    image_crops=[crop.image_crop for crop in annotation_crops],
                    show_progress=False,
                )

                _store_embeddings(
                    session=session,
                    model_id=model_id,
                    sample_ids=[crop.annotation_sample_id for crop in annotation_crops],
                    embeddings=embeddings,
                    show_progress=False,
                )
                progress.update(len(annotation_crops))

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

        _store_embeddings(
            session=session,
            model_id=model_id,
            sample_ids=sample_ids,
            embeddings=embeddings,
        )

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
        if collection_id in self._collection_id_to_default_model_id:
            return self._collection_id_to_default_model_id[collection_id]

        dataset = collection_resolver.get_by_id(session=session, collection_id=collection_id)
        if dataset is None:
            raise ValueError("Provided collection_id could not be found.")

        # Check if a model suitable for this sample type is already registered
        generator_sample_type = _GENERATOR_SAMPLE_TYPE.get(dataset.sample_type)
        if generator_sample_type is None:
            return None
        existing_model_id = self._sample_type_to_model_id.get(generator_sample_type)
        embedding_generator: EmbeddingGenerator | None = None
        if existing_model_id is not None:
            embedding_generator = self._models[existing_model_id]
        elif generator_sample_type in self._override_generators:
            # Prefer a user-registered generator over the env-var default.
            embedding_generator = self._override_generators[generator_sample_type]
        else:
            # Load the embedding generator based on sample_type from the env var.
            embedding_generator = _load_embedding_generator_from_env(
                sample_type=generator_sample_type
            )
        if embedding_generator is None:
            return None

        # Register the embedding model and set it as default.
        embedding_model = self.register_embedding_model(
            session=session,
            collection_id=collection_id,
            embedding_generator=embedding_generator,
            set_as_default=True,
        )
        # Store the model ID for the sample type to avoid reloading it in the future.
        self._sample_type_to_model_id[generator_sample_type] = embedding_model.embedding_model_id

        return embedding_model.embedding_model_id

    def _get_default_or_validate(
        self, collection_id: UUID, embedding_model_id: UUID | None
    ) -> UUID:
        """Get a valid model_id or raise error of non available.

        If embedding_model_id is not provided, returns the default model for collection_id.
        If embedding_model_id is provided, validates that the model has been loaded and returns it.
        """
        default_model_id = self._collection_id_to_default_model_id.get(collection_id, None)
        if embedding_model_id is None and default_model_id is None:
            raise ValueError(
                "No embedding_model_id provided and no default embedding model registered."
            )

        if embedding_model_id is None and default_model_id is not None:
            return default_model_id

        if embedding_model_id not in self._models:
            raise ValueError(f"No embedding model found with ID {embedding_model_id}")
        return embedding_model_id


def _store_embeddings(
    session: Session,
    model_id: UUID,
    sample_ids: list[UUID],
    embeddings: NDArray[np.float32],
    show_progress: bool = True,
) -> None:
    """Store embeddings in the database.

    Insertion is batched to reduce peak memory. All batches are committed together
    so a failure leaves no partially embedded dataset behind.
    """
    with tqdm(
        total=len(sample_ids),
        desc="Storing embeddings",
        unit=" embeddings",
        disable=not show_progress,
    ) as progress:
        for batch in batching.batched(
            items=zip(sample_ids, embeddings), batch_size=EMBEDDING_INSERTION_BATCH_SIZE
        ):
            sample_embeddings = [
                SampleEmbeddingCreate(
                    sample_id=sample_id,
                    embedding_model_id=model_id,
                    embedding=embedding,
                )
                for sample_id, embedding in batch
            ]
            sample_embedding_resolver.create_many(
                session=session, sample_embeddings=sample_embeddings, commit=False
            )

            progress.update(len(sample_embeddings))

    session.commit()


def _load_embedding_generator_from_env(sample_type: SampleType) -> EmbeddingGenerator | None:
    """Load the embedding generator based on environment variable configuration."""
    if sample_type == SampleType.IMAGE:
        return _load_image_embedding_generator_from_env()
    if sample_type == SampleType.VIDEO:
        return _load_video_embedding_generator()
    return None


# TODO(Michal, 09/2025): Write tests for this function.
def _load_image_embedding_generator_from_env() -> ImageEmbeddingGenerator | None:
    if env.LIGHTLY_STUDIO_EMBEDDINGS_MODEL_TYPE == "MOBILE_CLIP":
        try:
            # Keep this import local because this backend is only needed when selected.
            from lightly_studio.dataset.mobileclip_embedding_generator import (  # noqa: PLC0415
                MobileCLIPEmbeddingGenerator,
            )

            logger.info("Using MobileCLIP embedding generator for images.")
            return MobileCLIPEmbeddingGenerator()
        except ImportError:
            logger.warning("Embedding functionality is disabled.")
    elif env.LIGHTLY_STUDIO_EMBEDDINGS_MODEL_TYPE == "PE":
        try:
            # Keep this import local because this backend is only needed when selected.
            from lightly_studio.dataset.perception_encoder_embedding_generator import (  # noqa: PLC0415
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
        # Keep this import local because this backend is only needed when selected.
        from lightly_studio.dataset.perception_encoder_embedding_generator import (  # noqa: PLC0415
            PerceptionEncoderEmbeddingGenerator,
        )

        logger.info("Using PerceptionEncoder embedding generator for videos.")
        return PerceptionEncoderEmbeddingGenerator()
    except ImportError:
        logger.warning("Embedding functionality is disabled.")
        return None
