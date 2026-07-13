"""Example of how to register a custom embedding model.

This shows how to bypass the model selected by the
LIGHTLY_STUDIO_EMBEDDINGS_MODEL_TYPE environment variable and use your own
generator instead. The generator below mimics the built-in MobileCLIP model, but
you can swap in any implementation of the EmbeddingGenerator protocol.

Register the model with ls.set_default_embedding_model BEFORE creating a dataset,
so ingestion uses your generator instead of the environment default.
"""

from __future__ import annotations

from pathlib import Path
from uuid import UUID

import numpy as np
import torch
from environs import Env
from numpy.typing import NDArray
from PIL import Image

import lightly_studio as ls
from lightly_studio.database import db_manager
from lightly_studio.dataset import file_utils, image_crop_embedding, image_embedding
from lightly_studio.dataset.env import LIGHTLY_STUDIO_MODEL_CACHE_DIR
from lightly_studio.dataset.image_embedding import EmbeddingContext
from lightly_studio.models.embedding_model import EmbeddingModelCreate
from lightly_studio.vendor import mobileclip

MODEL_NAME = "mobileclip_s0"
MOBILECLIP_DOWNLOAD_URL = (
    f"https://docs-assets.developer.apple.com/ml-research/datasets/mobileclip/{MODEL_NAME}.pt"
)
MAX_BATCH_SIZE: int = 16
EMBEDDING_DIMENSION: int = 512


class CustomEmbeddingGenerator(ls.ImageEmbeddingGenerator):
    """A custom image embedding model.

    This implements the ls.ImageEmbeddingGenerator protocol. Here it wraps
    MobileCLIP to keep the example runnable, but the same structure works for any
    model: implement get_embedding_model_input, embed_text, embed_images,
    embed_image_crops and embed_pil_images. Implement ls.VideoEmbeddingGenerator as
    well to override the video model.
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
        self._model_hash = file_utils.get_file_xxhash(model_path)

    def get_embedding_model_input(self, collection_id: UUID) -> EmbeddingModelCreate:
        """Describe the model so it can be recorded in the database.

        The name shows up in the GUI and the hash lets Lightly Studio detect when
        the same model has been used before.
        """
        return EmbeddingModelCreate(
            name="Custom Embedding Model",
            embedding_model_hash=self._model_hash,
            embedding_dimension=EMBEDDING_DIMENSION,
            collection_id=collection_id,
        )

    def embed_text(self, text: str) -> list[float]:
        """Embed a text query into the same space as the images (for text search)."""
        tokenized = self._tokenizer([text]).to(self._device)
        with torch.no_grad():
            embedding = self._model.encode_text(tokenized)[0]  # type: ignore[operator]
            embedding_list: list[float] = embedding.cpu().numpy().flatten().tolist()
        return embedding_list

    def embed_images(self, filepaths: list[str], show_progress: bool = True) -> NDArray[np.float32]:
        """Embed a batch of images, returning one row per input path."""
        return image_embedding.embed_image_files_batched(
            filepaths=filepaths,
            context=self._embedding_context(),
            show_progress=show_progress,
        )

    def embed_image_crops(
        self, image_crops: list[ls.ImageCrop], show_progress: bool = True
    ) -> NDArray[np.float32]:
        """Embed a batch of image crops (used for annotation embeddings)."""
        return image_crop_embedding.embed_image_crops_batched(
            image_crops=image_crops,
            context=self._embedding_context(),
            show_progress=show_progress,
        )

    def embed_pil_images(
        self, images: list[Image.Image], show_progress: bool = True
    ) -> NDArray[np.float32]:
        """Embed a batch of in-memory PIL images."""
        return image_embedding.embed_pil_images_batched(
            images=images,
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

# Register the custom model BEFORE creating the dataset. This overrides the model
# selected by LIGHTLY_STUDIO_EMBEDDINGS_MODEL_TYPE for every collection.
ls.set_default_embedding_model(CustomEmbeddingGenerator())

# Define the path to the dataset directory
dataset_path = env.path("EXAMPLES_DATASET_PATH", "/path/to/your/dataset")

# Create a Dataset from a path. Images are embedded with the custom model.
dataset = ls.ImageDataset.create()
dataset.add_images_from_path(path=str(dataset_path))

ls.start_gui()
