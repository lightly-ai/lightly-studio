"""Embedding manager for dataset processing."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from uuid import UUID

import numpy as np
from numpy.typing import NDArray
from sqlmodel import Session, col, select
from tqdm import tqdm

from lightly_studio.dataset import env
from lightly_studio.dataset.embedding_generator import (
    EmbeddingGenerator,
    ImageCrop,
    ImageEmbeddingGenerator,
    VideoEmbeddingGenerator,
)
from lightly_studio.models.annotation.annotation_base import AnnotationBaseTable, AnnotationType
from lightly_studio.models.annotation.object_detection import ObjectDetectionAnnotationTable
from lightly_studio.models.collection import SampleType
from lightly_studio.models.embedding_model import EmbeddingModelTable
from lightly_studio.models.image import ImageTable
from lightly_studio.models.sample import SampleTable
from lightly_studio.models.sample_embedding import SampleEmbeddingCreate, SampleEmbeddingTable
from lightly_studio.resolvers import (
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

# Number of annotation crops processed per chunk in embed_annotations. Each chunk is
# queried, embedded, and committed independently to bound peak memory (ORM rows plus the
# embeddings array) and to make the operation resumable on large datasets. Kept well below
# PostgreSQL's bind-parameter cap so the per-chunk IN-clause stays valid.
ANNOTATION_EMBED_BATCH_SIZE = 2048


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


@dataclass(frozen=True)
class _AnnotationCrop:
    """Resolved annotation crop ready for embedding."""

    annotation_sample_id: UUID
    image_crop: ImageCrop


class EmbeddingManager:
    """Manages embedding models and handles embedding generation and storage."""

    def __init__(self) -> None:
        """Initialize the embedding manager."""
        self._models: dict[UUID, EmbeddingGenerator] = {}
        self._model_id_to_collection_id: dict[UUID, UUID] = {}
        self._collection_id_to_default_model_id: dict[UUID, UUID] = {}

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
        self._model_id_to_collection_id[model_id] = collection_id

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
        """Generate and store embeddings for object-detection annotations.

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
            raise ValueError("Embedding model not compatible with annotation crops.")

        # Resolve only the lightweight IDs of annotations still needing an embedding, then
        # process them in chunks. Each chunk queries its own crops, embeds, and commits, so
        # peak memory stays bounded and a crash resumes from the last committed chunk.
        annotation_sample_ids = _get_unembedded_annotation_ids(
            session=session,
            annotation_collection_id=annotation_collection_id,
            embedding_model_id=model_id,
        )
        if not annotation_sample_ids:
            logger.info("No annotation crops to embed.")
            return

        for sample_id_chunk in batching.batched(
            items=annotation_sample_ids, batch_size=ANNOTATION_EMBED_BATCH_SIZE
        ):
            annotation_crops = _get_annotation_crops_for_ids(
                session=session, annotation_sample_ids=sample_id_chunk
            )
            if not annotation_crops:
                continue

            embeddings = model.embed_image_crops(
                image_crops=[annotation_crop.image_crop for annotation_crop in annotation_crops]
            )

            _store_embeddings(
                session=session,
                model_id=model_id,
                sample_ids=[
                    annotation_crop.annotation_sample_id for annotation_crop in annotation_crops
                ],
                embeddings=embeddings,
            )

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

        # Load the embedding generator based on sample_type from the env var.
        dataset = collection_resolver.get_by_id(session=session, collection_id=collection_id)
        if dataset is None:
            raise ValueError("Provided collection_id could not be found.")

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
        default_model_id = self._collection_id_to_default_model_id.get(collection_id, None)
        if embedding_model_id is None and default_model_id is None:
            raise ValueError(
                "No embedding_model_id provided and no default embedding model registered."
            )

        if embedding_model_id is None and default_model_id is not None:
            return default_model_id

        if embedding_model_id not in self._models:
            raise ValueError(f"No embedding model found with ID {embedding_model_id}")
        if self._model_id_to_collection_id.get(embedding_model_id) != collection_id:
            raise ValueError(
                f"Embedding model {embedding_model_id} is not registered for "
                f"collection {collection_id}."
            )
        return embedding_model_id


def _store_embeddings(
    session: Session,
    model_id: UUID,
    sample_ids: list[UUID],
    embeddings: NDArray[np.float32],
) -> None:
    """Store embeddings in the database.

    Insertion is batched to reduce peak memory. All batches are committed together
    so a failure leaves no partially embedded dataset behind.
    """
    with tqdm(total=len(sample_ids), desc="Storing embeddings", unit=" embeddings") as progress:
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


def _get_unembedded_annotation_ids(
    session: Session,
    annotation_collection_id: UUID,
    embedding_model_id: UUID,
) -> list[UUID]:
    """Return IDs of object-detection annotations in the collection lacking an embedding.

    Only sample IDs are loaded so the result stays small even for very large collections;
    the crops themselves are fetched per chunk by ``_get_annotation_crops_for_ids``. Results
    are ordered by source image path so an image's annotations stay adjacent and tend to land
    in the same chunk, preserving the single-open-per-image behaviour of crop embedding.

    Args:
        session: Database session for resolver operations.
        annotation_collection_id: The annotation collection to scan.
        embedding_model_id: Model whose existing embeddings mark an annotation as done.

    Returns:
        Annotation sample IDs that still need an embedding, ordered by image path.
    """
    embedded_ids_subquery = select(col(SampleEmbeddingTable.sample_id)).where(
        col(SampleEmbeddingTable.embedding_model_id) == embedding_model_id
    )
    sample_ids = session.exec(
        select(col(AnnotationBaseTable.sample_id))
        .join(SampleTable, col(SampleTable.sample_id) == col(AnnotationBaseTable.sample_id))
        .join(ImageTable, col(ImageTable.sample_id) == col(AnnotationBaseTable.parent_sample_id))
        .where(col(SampleTable.collection_id) == annotation_collection_id)
        .where(col(AnnotationBaseTable.annotation_type) == AnnotationType.OBJECT_DETECTION)
        .where(col(AnnotationBaseTable.sample_id).notin_(embedded_ids_subquery))
        .order_by(col(ImageTable.file_path_abs))
    ).all()
    return list(sample_ids)


def _get_annotation_crops_for_ids(
    session: Session,
    annotation_sample_ids: list[UUID],
) -> list[_AnnotationCrop]:
    """Build valid image crops for the given object-detection annotation IDs.

    Crops whose box does not overlap the source image are skipped with a warning, so the
    returned list may be shorter than ``annotation_sample_ids``.

    Args:
        session: Database session for resolver operations.
        annotation_sample_ids: Annotation sample IDs to resolve crops for.

    Returns:
        Resolved annotation crops ready for embedding.
    """
    rows = session.exec(
        select(AnnotationBaseTable, ImageTable, ObjectDetectionAnnotationTable)
        .join(
            ObjectDetectionAnnotationTable,
            col(ObjectDetectionAnnotationTable.sample_id) == col(AnnotationBaseTable.sample_id),
        )
        .join(ImageTable, col(ImageTable.sample_id) == col(AnnotationBaseTable.parent_sample_id))
        .where(col(AnnotationBaseTable.sample_id).in_(annotation_sample_ids))
    ).all()

    annotation_crops: list[_AnnotationCrop] = []
    for annotation, image, object_detection in rows:
        image_crop = _create_valid_image_crop(
            filepath=image.file_path_abs,
            image_size=(image.width, image.height),
            box=(
                object_detection.x,
                object_detection.y,
                object_detection.width,
                object_detection.height,
            ),
        )
        if image_crop is None:
            logger.warning("Skipping invalid annotation crop %s.", annotation.sample_id)
            continue
        annotation_crops.append(
            _AnnotationCrop(annotation_sample_id=annotation.sample_id, image_crop=image_crop)
        )

    return annotation_crops


def _create_valid_image_crop(
    filepath: str,
    image_size: tuple[int, int],
    box: tuple[int, int, int, int],
) -> ImageCrop | None:
    image_width, image_height = image_size
    x, y, width, height = box
    x_min = max(0, x)
    y_min = max(0, y)
    x_max = min(image_width, x + width)
    y_max = min(image_height, y + height)
    crop_width = x_max - x_min
    crop_height = y_max - y_min
    if crop_width <= 0 or crop_height <= 0:
        return None
    return ImageCrop(
        filepath=filepath,
        x=x_min,
        y=y_min,
        width=crop_width,
        height=crop_height,
    )


def _load_embedding_generator_from_env(sample_type: SampleType) -> EmbeddingGenerator | None:
    """Load the embedding generator based on environment variable configuration."""
    if sample_type in (SampleType.IMAGE, SampleType.ANNOTATION):
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
