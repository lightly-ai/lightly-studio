"""Train an embedding model with LightlyTrain and explore it in LightlyStudio.

This script runs the full path end to end:

1. Train (distill) an embedding model on your images with ``lightly_train.pretrain``.
2. Generate embeddings for those images with ``lightly_train.embed``.
3. Load the embeddings into LightlyStudio through a small ``ImageEmbeddingGenerator``
   and open the app to explore and curate them.

LightlyTrain is a separate install and needs Python 3.10 or newer:

    pip install lightly-train lightly-studio

Run the whole script with a single ``python example_lightlytrain_embeddings.py``.
Training is the slow part; reduce ``EPOCHS`` for a quick smoke test, or point
``MODEL`` at a smaller backbone (see ``lightly_train.list_models()``).
"""

from __future__ import annotations

from pathlib import Path

import lightly_train  # type: ignore[import-not-found]
import numpy as np
import torch
from numpy.typing import NDArray
from PIL import Image

import lightly_studio as ls
from lightly_studio.database import db_manager
from lightly_studio.dataset import file_utils
from lightly_studio.dataset.embedding_result import EmbeddingResult
from lightly_studio.models.embedding_model import EmbeddingSpaceDescription

# Backbone to distill on your data. Any name from lightly_train.list_models() works.
MODEL = "dinov2/vits14"
# Real runs use more epochs; a handful is enough to see the pipeline work.
EPOCHS = 10
PRETRAIN_DIR = "out/pretrain"
EMBEDDINGS_FILE = "out/embeddings.pt"


class LightlyTrainEmbeddingsGenerator(ls.ImageEmbeddingGenerator):
    """Serve embeddings precomputed by ``lightly_train.embed``, keyed by filepath.

    ``lightly_train.embed(format="torch")`` writes ``{"filenames", "embeddings"}``,
    where ``filenames`` are relative to the embedded directory. LightlyStudio looks
    embeddings up by the absolute path it stores for each image, so this generator
    rebuilds those absolute paths and also keeps a basename fallback for the common
    case of a flat image folder.
    """

    def __init__(self, embeddings_file: str, data_dir: str) -> None:
        """Load the precomputed vectors and index them by filepath.

        Args:
            embeddings_file: Path to the file written by ``lightly_train.embed``.
            data_dir: The directory that was passed to ``lightly_train.embed`` as
                ``data`` and to ``add_images_from_path`` as ``path``.
        """
        blob = torch.load(embeddings_file, weights_only=True)
        vectors: NDArray[np.float32] = blob["embeddings"].to(torch.float32).numpy()
        self._embedding_dimension = int(vectors.shape[1])

        by_path: dict[str, NDArray[np.float32]] = {}
        names_seen: dict[str, list[NDArray[np.float32]]] = {}
        for index, name in enumerate(blob["filenames"]):
            # LightlyStudio stores absolute paths via Path(path).absolute(), so match
            # that exactly here (see core/image/image_dataset.py _normalize_input_path).
            absolute_path = (Path(data_dir) / name).absolute().as_posix()
            by_path[absolute_path] = vectors[index]
            names_seen.setdefault(Path(name).name, []).append(vectors[index])
        self._by_path = by_path
        # Fallback only where a basename is unambiguous (a flat folder of images).
        self._by_name = {name: rows[0] for name, rows in names_seen.items() if len(rows) == 1}

        self._model_hash = file_utils.get_file_xxhash(Path(embeddings_file))

    def get_embedding_model_input(self) -> EmbeddingSpaceDescription:
        """Describe the model so LightlyStudio can record and deduplicate it."""
        return EmbeddingSpaceDescription(
            name="LightlyTrain",
            embedding_model_hash=self._model_hash,
            embedding_dimension=self._embedding_dimension,
        )

    def embed_text(self, text: str) -> list[float]:
        """Not supported: a LightlyTrain SSL backbone has no text encoder."""
        raise NotImplementedError(
            "LightlyTrain backbones are vision-only; text search is unavailable."
        )

    def embed_images(self, filepaths: list[str], show_progress: bool = True) -> EmbeddingResult:
        """Look up the precomputed vector for each filepath.

        Returns one row per filepath that has a stored vector and uses
        ``kept_indices`` to skip any image without one.
        """
        _ = show_progress  # This is a lookup, not a model run, so there is nothing to show.
        rows: list[NDArray[np.float32]] = []
        kept_indices: list[int] = []
        for index, filepath in enumerate(filepaths):
            vector = self._by_path.get(filepath)
            if vector is None:
                vector = self._by_name.get(Path(filepath).name)
            if vector is None:
                continue
            rows.append(vector)
            kept_indices.append(index)

        embeddings = (
            np.stack(rows) if rows else np.empty((0, self._embedding_dimension), dtype=np.float32)
        )
        return EmbeddingResult(embeddings=embeddings, kept_indices=kept_indices)

    def embed_image_crops(
        self, image_crops: list[ls.ImageCrop], show_progress: bool = True
    ) -> EmbeddingResult:
        """Not supported: crops have no precomputed vectors."""
        raise NotImplementedError(
            "This generator only serves precomputed whole-image embeddings; "
            "object-level (crop) embeddings are unavailable."
        )

    def embed_pil_images(
        self, images: list[Image.Image], show_progress: bool = True
    ) -> NDArray[np.float32]:
        """Not supported: in-memory images have no precomputed vectors."""
        raise NotImplementedError(
            "This generator serves precomputed vectors keyed by filepath; "
            "in-memory PIL images cannot be looked up."
        )


# 1. Get a dataset. Swap in your own image folder here.
data_dir = ls.utils.download_example_dataset(download_dir="dataset_examples")
images_path = str(Path(data_dir) / "coco_subset_128_images" / "images")

# 2. Train (distill) an embedding model on the images.
lightly_train.pretrain(out=PRETRAIN_DIR, data=images_path, model=MODEL, epochs=EPOCHS)

# 3. Generate embeddings with the trained model.
lightly_train.embed(
    out=EMBEDDINGS_FILE,
    data=images_path,
    checkpoint=f"{PRETRAIN_DIR}/checkpoints/last.ckpt",
    format="torch",
)

# 4. Load the embeddings into LightlyStudio. Register the generator BEFORE creating the
# dataset, so ingestion reuses the precomputed vectors instead of a built-in model.
db_manager.connect(cleanup_existing=True)
ls.set_default_embedding_model(
    LightlyTrainEmbeddingsGenerator(embeddings_file=EMBEDDINGS_FILE, data_dir=images_path)
)
dataset = ls.ImageDataset.create(name="lightlytrain-embeddings")
dataset.add_images_from_path(path=images_path)

# 5. Curate in code: select a diverse subset. The result is stored as a tag you can
# open in the app. You can also do this interactively with the lasso in the GUI.
dataset.query().sampling().diverse(
    n_samples_to_select=32, sampling_result_tag_name="diverse_subset"
)

# 6. Explore the embedding map. Open the printed URL and pick the Embed panel.
ls.start_gui(open_browser=True)
