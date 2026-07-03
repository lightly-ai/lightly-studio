"""MobileCLIP embedding generator."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from uuid import UUID

import torch

from lightly_studio.dataset.env import LIGHTLY_STUDIO_MODEL_CACHE_DIR
from lightly_studio.models.embedding_model import EmbeddingModelCreate
from lightly_studio.vendor import mobileclip

from . import file_utils, image_crop_embedding, image_embedding
from .embedding_generator import BatchedEmbeddingResult, ImageCrop, ImageEmbeddingGenerator
from .image_embedding import EmbeddingContext

MODEL_NAME = "mobileclip_s0"
MOBILECLIP_DOWNLOAD_URL = (
    f"https://docs-assets.developer.apple.com/ml-research/datasets/mobileclip/{MODEL_NAME}.pt"
)
MAX_BATCH_SIZE: int = 16
EMBEDDING_DIMENSION: int = 512


class MobileCLIPEmbeddingGenerator(ImageEmbeddingGenerator):
    """MobileCLIP embedding model."""

    def __init__(self) -> None:
        """Initialize the MobileCLIP embedding model.

        This method loads the MobileCLIP model and its tokenizer. The model
        checkpoint is downloaded and cached locally for future use.
        """
        model_path = _get_cached_mobileclip_checkpoint()
        self._model, _, self._preprocess = mobileclip.create_model_and_transforms(
            model_name=MODEL_NAME, pretrained=str(model_path)
        )

        # Auto select device: CUDA > MPS (Apple Silicon) > CPU
        self._device = torch.device(
            "cuda"
            if torch.cuda.is_available()
            else "mps"
            if torch.backends.mps.is_available()
            else "cpu"
        )
        self._model = self._model.to(self._device)
        self._tokenizer = mobileclip.get_tokenizer(model_name=MODEL_NAME)
        self._model_hash = file_utils.get_file_xxhash(model_path)

    def get_embedding_model_input(self, collection_id: UUID) -> EmbeddingModelCreate:
        """Generate an EmbeddingModelCreate instance.

        Args:
            collection_id: The ID of the collection.

        Returns:
            An EmbeddingModelCreate instance with the model details.
        """
        return EmbeddingModelCreate(
            name=MODEL_NAME,
            embedding_model_hash=self._model_hash,
            embedding_dimension=EMBEDDING_DIMENSION,
            collection_id=collection_id,
        )

    def embed_text(self, text: str) -> list[float]:
        """Embed a text with MobileCLIP.

        Args:
            text: The text to embed.

        Returns:
            A list of floats representing the generated embedding.
        """
        tokenized = self._tokenizer([text]).to(self._device)
        with torch.no_grad():
            embedding = self._model.encode_text(tokenized)[0]  # type: ignore[operator]
            # Convert embedding to list of floats.
            embedding_list: list[float] = embedding.cpu().numpy().flatten().tolist()
        return embedding_list

    def embed_images(
        self,
        keyed_filepaths: Sequence[tuple[UUID, str]],
        show_progress: bool = True,
    ) -> BatchedEmbeddingResult:
        """Embed images with MobileCLIP.

        Args:
            keyed_filepaths: ``(sample_id, filepath)`` pairs to embed.
            show_progress: Whether to show a progress bar during embedding.

        Returns:
            Embeddings for the embedded files, keyed by sample id.
        """
        return image_embedding.embed_image_files_batched(
            keyed_filepaths=keyed_filepaths,
            context=self._embedding_context(),
            show_progress=show_progress,
        )

    def embed_image_crops(
        self,
        keyed_crops: Sequence[tuple[UUID, ImageCrop]],
        show_progress: bool = True,
    ) -> BatchedEmbeddingResult:
        """Embed image crops with MobileCLIP.

        Args:
            keyed_crops: ``(sample_id, crop)`` pairs to embed.
            show_progress: Whether to show a progress bar during embedding.

        Returns:
            Embeddings for the embedded crops, keyed by sample id.
        """
        return image_crop_embedding.embed_image_crops_batched(
            keyed_crops=keyed_crops,
            context=self._embedding_context(),
            show_progress=show_progress,
        )

    def _embedding_context(self) -> EmbeddingContext:
        """Build the model-specific configuration for batched image embedding."""
        return EmbeddingContext(
            embedding_dimension=EMBEDDING_DIMENSION,
            max_batch_size=MAX_BATCH_SIZE,
            device=self._device,
            preprocess=self._preprocess,
            encode_batch=lambda images_tensor: (
                self._model.encode_image(images_tensor)  # type: ignore[operator]
                .cpu()
                .numpy()
            ),
        )


def _get_cached_mobileclip_checkpoint() -> Path:
    file_path = LIGHTLY_STUDIO_MODEL_CACHE_DIR / f"{MODEL_NAME}.pt"
    file_utils.download_file_if_does_not_exist(
        url=MOBILECLIP_DOWNLOAD_URL,
        local_filename=file_path,
    )
    return file_path
