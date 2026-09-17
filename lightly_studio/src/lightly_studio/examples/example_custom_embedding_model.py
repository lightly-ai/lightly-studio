"""Example of how to register a custom embedder.

This shows how to bypass the built-in embedder and use your own instead. The
embedder below mimics the built-in MobileCLIP model, but you can swap in any
implementation of the ``Embedder`` capability interfaces.

An embedder subclasses one interface per input it can embed. This one embeds
images by path, image crops and text into one shared space, so text queries can
be compared against image embeddings. Implement ``VideoPathEmbedder`` as well to
embed whole videos.

Register the embedder with ls.register_default_embedder BEFORE creating a dataset,
so ingestion uses it instead of the built-in default.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import torch
from environs import Env
from lightly_studio_serve.embedder import (
    ImageCropPathEmbedder,
    ImagePathEmbedder,
    TextEmbedder,
)

import lightly_studio as ls
from lightly_studio.database import db_manager
from lightly_studio.dataset import file_utils
from lightly_studio.dataset.env import LIGHTLY_STUDIO_MODEL_CACHE_DIR
from lightly_studio.embed import image_crop_embedding, image_embedding
from lightly_studio.embed.image_embedding import EmbeddingContext
from lightly_studio.vendor import mobileclip

MODEL_NAME = "mobileclip_s0"
MOBILECLIP_DOWNLOAD_URL = (
    f"https://docs-assets.developer.apple.com/ml-research/datasets/mobileclip/{MODEL_NAME}.pt"
)
MAX_BATCH_SIZE: int = 16
EMBEDDING_DIMENSION: int = 512


class CustomEmbedder(
    ImagePathEmbedder,
    ImageCropPathEmbedder,
    TextEmbedder,
):
    """A custom embedder.

    This subclasses the ``ImagePathEmbedder``, ``ImageCropPathEmbedder`` and
    ``TextEmbedder`` interfaces. Here it wraps MobileCLIP to keep the example
    runnable, but the same structure works for any model: subclass the interface for
    each capability you support and implement its embed method. Subclass only the
    capabilities your model provides.
    """

    def __init__(self) -> None:
        """Load the model weights and tokenizer once, up front."""
        model_path = _get_cached_checkpoint()
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

    def embedding_space_spec(self) -> ls.EmbeddingSpaceSpec:
        """Describe the embedding space so it can be recorded in the database.

        Returns metadata about the embedding space to be stored in the database.
        The `space_key` field is used to match the same embedding space across
        multiple LightlyStudio runs.
        """
        return ls.EmbeddingSpaceSpec(
            space_key="your-company/model-family@version",
            dimension=EMBEDDING_DIMENSION,
        )

    def embed_images(self, paths: list[str]) -> ls.EmbeddingResult:
        """Embed a batch of images, returning one row per readable input path."""
        return image_embedding.embed_image_files_batched(
            filepaths=paths,
            context=self._embedding_context(),
            show_progress=True,
        )

    def embed_image_crops(self, crops: list[ls.ImageCrop]) -> ls.EmbeddingResult:
        """Embed a batch of image crops (used for annotation embeddings)."""
        return image_crop_embedding.embed_image_crops_batched(
            image_crops=crops,
            context=self._embedding_context(),
            show_progress=True,
        )

    def embed_text(self, texts: list[str]) -> ls.EmbeddingResult:
        """Embed text queries into the same space as the images (for text search)."""
        if not texts:
            empty = np.empty((0, EMBEDDING_DIMENSION), dtype=np.float32)
            return ls.EmbeddingResult(embeddings=empty, kept_indices=[])

        tokenized = self._tokenizer(texts).to(self._device)
        with torch.no_grad():
            embeddings = self._model.encode_text(tokenized).cpu().numpy()  # type: ignore[operator]
        return ls.EmbeddingResult(
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


def _get_cached_checkpoint() -> Path:
    file_path = LIGHTLY_STUDIO_MODEL_CACHE_DIR / f"{MODEL_NAME}.pt"
    file_utils.download_file_if_does_not_exist(
        url=MOBILECLIP_DOWNLOAD_URL,
        local_filename=file_path,
    )
    return file_path


# Read environment variables
env = Env()
env.read_env()

# Cleanup an existing database
db_manager.connect(cleanup_existing=True)

# Register the custom embedder BEFORE creating the dataset. It becomes the default
# for every capability it implements, so ingestion uses it for every collection.
ls.register_default_embedder(embedder=CustomEmbedder())

# Define the path to the dataset directory
dataset_path = env.path("EXAMPLES_DATASET_PATH")

# Create a Dataset from a path. Images are embedded with the custom embedder.
dataset = ls.ImageDataset.create()
dataset.add_images_from_path(path=str(dataset_path))

ls.start_gui()
