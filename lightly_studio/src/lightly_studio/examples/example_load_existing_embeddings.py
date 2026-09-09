"""Example of how to load precomputed embeddings.

Implement a class inheriting from ls.ImageEmbeddingGenerator. For image datasets,
only `embedding_space_spec` and `embed_images` functions are necessary.
Register the generator with `ls.set_default_embedding_model`.

For video datasets, implement ls.VideoEmbeddingGenerator as well to override the
video model.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
from environs import Env
from numpy.typing import NDArray
from PIL import Image

import lightly_studio as ls
from lightly_studio.database import db_manager
from lightly_studio.embed.types import EmbeddingResult

IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
EMBEDDING_DIMENSION = 64


def create_mock_embeddings(dataset_path: Path) -> dict[str, NDArray[np.float32]]:
    """Return a dictionary that maps each filepath to a random vector.

    The returned dictionary is conceptually just `filepath -> vector`, for example
    `{"/data/images/cat.jpg": [0.1, 0.2, ...]}`. The embeddings are mocked here, a
    real implementation would read them from a file.
    """
    # Key by the same absolute posix path the backend stores as file_path_abs, so
    # the lookup in embed_images matches. A relative key here would never match.
    filepaths = sorted(
        path.absolute().as_posix()
        for path in dataset_path.rglob("*")
        if path.suffix.lower() in IMAGE_SUFFIXES
    )
    rng = np.random.default_rng(seed=0)
    return {filepath: rng.random(EMBEDDING_DIMENSION, dtype=np.float32) for filepath in filepaths}


class LoadExistingEmbeddingsGenerator(ls.ImageEmbeddingGenerator):
    """A generator that loads precomputed embeddings by filepath."""

    def __init__(self, embeddings_by_filepath: dict[str, NDArray[np.float32]]) -> None:
        """Store the precomputed vectors.

        Args:
            embeddings_by_filepath: Precomputed embedding vector for each filepath.
        """
        self._embeddings_by_filepath = embeddings_by_filepath

    def embedding_space_spec(self) -> ls.EmbeddingSpaceSpec:
        """Describe the embedding space so it can be recorded in the database."""
        return ls.EmbeddingSpaceSpec(
            space_key="your-company/model-family@version",
            dimension=EMBEDDING_DIMENSION,
        )

    def embed_text(self, text: str) -> list[float]:
        """Not supported: there is no text encoder for precomputed vectors."""
        raise NotImplementedError(
            "LoadExistingEmbeddingsGenerator has no text encoder; text search is "
            "unavailable. Supply an encoder that shares the precomputed space to "
            "enable it."
        )

    def embed_images(self, filepaths: list[str], show_progress: bool = True) -> EmbeddingResult:
        """Look up the precomputed vector for each filepath.

        This method returns one row for each filepath that has a stored vector.
        It uses kept_indices to skip a filepath that has no vector.
        """
        _ = show_progress  # No progress bar. This step is a lookup, not a model run.
        rows: list[NDArray[np.float32]] = []
        kept_indices: list[int] = []
        for index, filepath in enumerate(filepaths):
            embedding = self._embeddings_by_filepath.get(filepath)
            if embedding is None:
                continue
            rows.append(embedding)
            kept_indices.append(index)

        embeddings = (
            np.stack(rows) if rows else np.empty((0, EMBEDDING_DIMENSION), dtype=np.float32)
        )
        return EmbeddingResult(embeddings=embeddings, kept_indices=kept_indices)

    def embed_image_crops(
        self, image_crops: list[ls.ImageCrop], show_progress: bool = True
    ) -> EmbeddingResult:
        """Not supported: crops have no precomputed vectors."""
        raise NotImplementedError(
            "LoadExistingEmbeddingsGenerator only serves precomputed whole-image "
            "embeddings; object-level (crop) embeddings are unavailable."
        )

    def embed_pil_images(
        self, images: list[Image.Image], show_progress: bool = True
    ) -> NDArray[np.float32]:
        """Not supported: in-memory images have no precomputed vectors."""
        raise NotImplementedError(
            "LoadExistingEmbeddingsGenerator only serves precomputed vectors keyed "
            "by filepath; in-memory PIL images cannot be looked up."
        )


# Read environment variables
env = Env()
env.read_env()

# Remove any existing database
db_manager.connect(cleanup_existing=True)

# Get the path to the dataset directory
dataset_path = env.path("EXAMPLES_DATASET_PATH")

# Load the precomputed embeddings. Here they are mocked. In a real setup, load
# your own vectors keyed by filepath.
embeddings_by_filepath = create_mock_embeddings(dataset_path=dataset_path)

# Register the generator BEFORE you create the dataset. It overrides the model
# from LIGHTLY_STUDIO_EMBEDDINGS_MODEL_TYPE for every collection.
ls.set_default_embedding_model(LoadExistingEmbeddingsGenerator(embeddings_by_filepath))

# Create a dataset from a path. The embedding generator is invoked here.
dataset = ls.ImageDataset.create()
dataset.add_images_from_path(path=str(dataset_path))

ls.start_gui()
