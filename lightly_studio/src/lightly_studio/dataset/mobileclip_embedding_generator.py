"""MobileCLIP embedding generator."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from uuid import UUID

import numpy as np
import torch
from numpy.typing import NDArray
from PIL import Image

from lightly_studio.dataset.env import LIGHTLY_STUDIO_MODEL_CACHE_DIR
from lightly_studio.models.embedding_model import EmbeddingModelCreate
from lightly_studio.vendor import mobileclip

from . import file_utils, image_crop_embedding, image_embedding
from .embedding_generator import ImageCrop, ImageEmbeddingGenerator
from .embedding_result import EmbeddingResult
from .image_embedding import EmbeddingContext

logger = logging.getLogger(__name__)

DEFAULT_MODEL_NAME = "mobileclip_s0"
MOBILECLIP_CONFIGS_DIR = Path(mobileclip.__file__).parent / "configs"
MAX_BATCH_SIZE: int = 128
# Embedding dimension of the default model. Kept as a module constant for callers
# (e.g. tests) that need a stand-in dimension without instantiating the generator.
EMBEDDING_DIMENSION: int = json.loads(
    (MOBILECLIP_CONFIGS_DIR / f"{DEFAULT_MODEL_NAME}.json").read_text()
)["embed_dim"]


class MobileCLIPEmbeddingGenerator(ImageEmbeddingGenerator):
    """MobileCLIP embedding model."""

    def __init__(
        self,
        model_name: str = DEFAULT_MODEL_NAME,
        max_batch_size: int | None = None,
    ) -> None:
        """Initialize the MobileCLIP embedding model.

        This method loads the MobileCLIP model and its tokenizer. The model
        checkpoint is downloaded and cached locally for future use.

        Args:
            model_name: Which MobileCLIP variant to load. One of ``mobileclip_s0``
                (default, smallest), ``mobileclip_s1``, ``mobileclip_s2``, or
                ``mobileclip_b`` (largest).
            max_batch_size: Number of images embedded per forward pass. Defaults to
                128; lower it if a bigger model runs out of memory.

        Raises:
            ValueError: If model_name is not a supported MobileCLIP variant.
        """
        self._model_name = model_name
        self._max_batch_size = max_batch_size or MAX_BATCH_SIZE
        self._embedding_dimension = _read_embedding_dimension(model_name)

        model_path = _get_cached_mobileclip_checkpoint(model_name)
        self._model, _, self._preprocess = mobileclip.create_model_and_transforms(
            model_name=model_name, pretrained=str(model_path)
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
        self._tokenizer = mobileclip.get_tokenizer(model_name=model_name)
        self._model_hash = file_utils.get_file_xxhash(model_path)
        logger.info(f"Loaded MobileCLIP embedding model '{self._model_name}'.")

    def get_embedding_model_input(self, collection_id: UUID) -> EmbeddingModelCreate:
        """Generate an EmbeddingModelCreate instance.

        Args:
            collection_id: The ID of the collection.

        Returns:
            An EmbeddingModelCreate instance with the model details.
        """
        return EmbeddingModelCreate(
            name=self._model_name,
            embedding_model_hash=self._model_hash,
            embedding_dimension=self._embedding_dimension,
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

    def embed_images(self, filepaths: list[str], show_progress: bool = True) -> EmbeddingResult:
        """Embed images with MobileCLIP.

        Args:
            filepaths: A list of file paths to the images to embed.
            show_progress: Whether to show a progress bar during embedding.

        Returns:
            An ``EmbeddingResult`` with embeddings for the readable files, in the same
            order as the corresponding input file paths.
        """
        return image_embedding.embed_image_files_batched(
            filepaths=filepaths,
            context=self._embedding_context(),
            show_progress=show_progress,
        )

    def embed_image_crops(
        self, image_crops: list[ImageCrop], show_progress: bool = True
    ) -> EmbeddingResult:
        """Embed image crops with MobileCLIP.

        Args:
            image_crops: A list of image crop definitions to embed.
            show_progress: Whether to show a progress bar during embedding.

        Returns:
            An ``EmbeddingResult`` with embeddings for the crops of readable files,
            in the same order as the corresponding input crops.
        """
        return image_crop_embedding.embed_image_crops_batched(
            image_crops=image_crops,
            context=self._embedding_context(),
            show_progress=show_progress,
        )

    def embed_pil_images(
        self, images: list[Image.Image], show_progress: bool = True
    ) -> NDArray[np.float32]:
        """Embed in-memory PIL images with MobileCLIP.

        Args:
            images: PIL images to embed.
            show_progress: Whether to show a progress bar during embedding.

        Returns:
            A numpy array representing the generated embeddings in the same order
            as the input images.
        """
        return image_embedding.embed_pil_images_batched(
            images=images,
            context=self._embedding_context(),
            show_progress=show_progress,
        )

    def _embedding_context(self) -> EmbeddingContext:
        """Build the model-specific configuration for batched image embedding."""
        return EmbeddingContext(
            embedding_dimension=self._embedding_dimension,
            max_batch_size=self._max_batch_size,
            device=self._device,
            preprocess=self._preprocess,
            encode_batch=lambda images_tensor: (
                self._model.encode_image(images_tensor)  # type: ignore[operator]
                .cpu()
                .numpy()
            ),
        )


def _read_embedding_dimension(model_name: str) -> int:
    """Read embed_dim from the vendored config for model_name.

    Also serves as the model_name validation step, run before the checkpoint
    download so an unsupported name fails with a clear error instead of a 404.

    Raises:
        ValueError: If model_name is not a supported MobileCLIP variant.
    """
    config_path = MOBILECLIP_CONFIGS_DIR / f"{model_name}.json"
    if not config_path.exists():
        valid_names = sorted(path.stem for path in MOBILECLIP_CONFIGS_DIR.glob("*.json"))
        raise ValueError(
            f"Unsupported model name: {model_name!r}. Choose one of: {', '.join(valid_names)}."
        )
    config = json.loads(config_path.read_text())
    return int(config["embed_dim"])


def _get_cached_mobileclip_checkpoint(model_name: str) -> Path:
    file_path = LIGHTLY_STUDIO_MODEL_CACHE_DIR / f"{model_name}.pt"
    download_url = (
        f"https://docs-assets.developer.apple.com/ml-research/datasets/mobileclip/{model_name}.pt"
    )
    file_utils.download_file_if_does_not_exist(
        url=download_url,
        local_filename=file_path,
    )
    return file_path
