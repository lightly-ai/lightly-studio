"""MobileCLIP embedder.

Wraps the MobileCLIP model behind the ``Embedder`` capability interfaces. It embeds
images by path, image crops, PIL images and text into a shared embedding space, so
text queries can be compared against image embeddings.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import torch
from PIL import Image

from lightly_studio.dataset import file_utils
from lightly_studio.dataset.env import LIGHTLY_STUDIO_MODEL_CACHE_DIR
from lightly_studio.embed import image_crop_embedding, image_embedding
from lightly_studio.embed.embedder import (
    ImageCropPathEmbedder,
    ImagePathEmbedder,
    ImagePILEmbedder,
    TextEmbedder,
)
from lightly_studio.embed.image_embedding import EmbeddingContext
from lightly_studio.embed.types import EmbeddingResult, EmbeddingSpaceSpec, ImageCrop
from lightly_studio.vendor import mobileclip

MODEL_NAME = "mobileclip_s0"
MOBILECLIP_DOWNLOAD_URL = (
    f"https://docs-assets.developer.apple.com/ml-research/datasets/mobileclip/{MODEL_NAME}.pt"
)
MAX_BATCH_SIZE: int = 128
EMBEDDING_DIMENSION: int = 512


class MobileCLIPEmbedder(
    ImagePathEmbedder,
    ImageCropPathEmbedder,
    ImagePILEmbedder,
    TextEmbedder,
):
    """MobileCLIP embedding model.

    Embeds images by path, image crops, video frames and text into one shared
    embedding space. MobileCLIP cannot embed a whole video, so there is no video
    capability; a video is covered frame by frame through ``embed_frames``.
    """

    __slots__ = ("_device", "_model", "_preprocess", "_tokenizer")

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

    def embedding_space_spec(self) -> EmbeddingSpaceSpec:
        """Describe the embedding space produced by this embedder.

        Returns:
            A specification of the embedding space.
        """
        return EmbeddingSpaceSpec(
            space_key=MODEL_NAME,
            dimension=EMBEDDING_DIMENSION,
        )

    def embed_images(self, paths: list[str]) -> EmbeddingResult:
        """Embed images with MobileCLIP.

        Args:
            paths: fsspec paths of the images to embed.

        Returns:
            The embeddings and the indices of the inputs they cover.
        """
        return image_embedding.embed_image_files_batched(
            filepaths=paths,
            context=self._embedding_context(),
            show_progress=True,
        )

    def embed_image_crops(self, crops: list[ImageCrop]) -> EmbeddingResult:
        """Embed image crops with MobileCLIP.

        Args:
            crops: The crops to embed.

        Returns:
            The embeddings and the indices of the inputs they cover.
        """
        return image_crop_embedding.embed_image_crops_batched(
            image_crops=crops,
            context=self._embedding_context(),
            show_progress=True,
        )

    def embed_frames(self, frames: list[Image.Image]) -> EmbeddingResult:
        """Embed video frames with MobileCLIP.

        Args:
            frames: The frames to embed, as PIL images.

        Returns:
            The embeddings and the indices of the inputs they cover.
        """
        embeddings = image_embedding.embed_pil_images_batched(
            images=frames,
            context=self._embedding_context(),
            show_progress=True,
        )
        return EmbeddingResult(embeddings=embeddings, kept_indices=list(range(len(frames))))

    def embed_text(self, texts: list[str]) -> EmbeddingResult:
        """Embed texts with MobileCLIP.

        Args:
            texts: The strings to embed.

        Returns:
            The embeddings and the indices of the inputs they cover.
        """
        if not texts:
            empty = np.empty((0, EMBEDDING_DIMENSION), dtype=np.float32)
            return EmbeddingResult(embeddings=empty, kept_indices=[])

        tokenized = self._tokenizer(texts).to(self._device)
        with torch.no_grad():
            embeddings = self._model.encode_text(tokenized).cpu().numpy()  # type: ignore[operator]
        return EmbeddingResult(
            embeddings=embeddings.astype(np.float32), kept_indices=list(range(len(texts)))
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
