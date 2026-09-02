"""Load a LightlyTrain model into LightlyStudio and explore its embeddings.

Part 2 of a two-script example. Run ``example_lightlytrain_train_and_export.py``
first to produce ``out/embedding_model.pt``. This script loads that model, embeds
the dataset with it on the fly, selects a diverse subset, and opens the app.

The environment that runs this needs the same ``lightly-train`` version used to
export the model, because ``torch.load`` unpickles LightlyTrain's model class:

    pip install lightly-train lightly-studio
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import torch
from numpy.typing import NDArray
from PIL import Image
from torchvision import transforms  # type: ignore[import-untyped]

import lightly_studio as ls
from lightly_studio.database import db_manager
from lightly_studio.dataset import file_utils, image_crop_embedding, image_embedding
from lightly_studio.dataset.embedding_result import EmbeddingResult
from lightly_studio.dataset.image_embedding import EmbeddingContext

MODEL_FILE = "out/embedding_model.pt"
MAX_BATCH_SIZE = 128
IMAGE_SIZE = 224
# LightlyTrain's default normalization is ImageNet. If you trained with custom
# normalize_args, pass the matching mean/std here.
IMAGENET_MEAN = (0.485, 0.456, 0.406)
IMAGENET_STD = (0.229, 0.224, 0.225)


class LightlyTrainEmbeddingGenerator(ls.ImageEmbeddingGenerator):
    """Embed images on the fly with a model exported from LightlyTrain.

    Loads the ``EmbeddingModel`` written by
    ``lightly_train.export(part="embedding_model", format="torch_model")`` and runs
    it inside LightlyStudio, so whole images, object crops, and video frames are all
    embedded live during ingestion.
    """

    def __init__(self, model_file: str) -> None:
        """Load the exported model and build its preprocessing.

        Args:
            model_file: Path to the torch module written by ``lightly_train.export``.
        """
        # Auto select device: CUDA > MPS (Apple Silicon) > CPU.
        self._device = torch.device(
            "cuda"
            if torch.cuda.is_available()
            else "mps"
            if torch.backends.mps.is_available()
            else "cpu"
        )
        # Full-module pickle: the same lightly_train version must be installed to load it.
        # map_location="cpu" first, so a model exported on a GPU still loads on a CPU/MPS host.
        self._model = (
            torch.load(model_file, map_location="cpu", weights_only=False).to(self._device).eval()
        )
        self._preprocess = transforms.Compose(
            [
                transforms.Resize((IMAGE_SIZE, IMAGE_SIZE)),
                transforms.ToTensor(),
                transforms.Normalize(mean=IMAGENET_MEAN, std=IMAGENET_STD),
            ]
        )
        self._model_hash = file_utils.get_file_xxhash(Path(model_file))
        # EmbeddingModel.forward returns (B, D, 1, 1); infer D from a dummy pass.
        with torch.no_grad():
            dummy = torch.zeros(1, 3, IMAGE_SIZE, IMAGE_SIZE, device=self._device)
            self._embedding_dimension = int(self._model(dummy).flatten(1).shape[1])

    def embedding_space_spec(self) -> ls.EmbeddingSpaceSpec:
        """Describe the embedding space so LightlyStudio can record and deduplicate it."""
        return ls.EmbeddingSpaceSpec(
            space_key=f"lightlytrain/{self._model_hash}",
            dimension=self._embedding_dimension,
        )

    def embed_text(self, text: str) -> list[float]:
        """Not supported: a LightlyTrain SSL backbone has no text encoder."""
        raise NotImplementedError(
            "LightlyTrain backbones are vision-only; text search is unavailable."
        )

    def embed_images(self, filepaths: list[str], show_progress: bool = True) -> EmbeddingResult:
        """Embed a batch of images, returning one row per readable input path."""
        return image_embedding.embed_image_files_batched(
            filepaths=filepaths,
            context=self._embedding_context(),
            show_progress=show_progress,
        )

    def embed_image_crops(
        self, image_crops: list[ls.ImageCrop], show_progress: bool = True
    ) -> EmbeddingResult:
        """Embed a batch of object crops (used for annotation embeddings)."""
        return image_crop_embedding.embed_image_crops_batched(
            image_crops=image_crops,
            context=self._embedding_context(),
            show_progress=show_progress,
        )

    def embed_pil_images(
        self, images: list[Image.Image], show_progress: bool = True
    ) -> NDArray[np.float32]:
        """Embed a batch of in-memory PIL images (used for video frames)."""
        return image_embedding.embed_pil_images_batched(
            images=images,
            context=self._embedding_context(),
            show_progress=show_progress,
        )

    def _embedding_context(self) -> EmbeddingContext:
        """Build the model-specific configuration for batched embedding."""
        return EmbeddingContext(
            embedding_dimension=self._embedding_dimension,
            max_batch_size=MAX_BATCH_SIZE,
            device=self._device,
            preprocess=self._preprocess,
            encode_batch=lambda batch: self._model(batch).flatten(1).cpu().numpy(),
        )


# 1. Point at the same dataset used for training (train_and_export.py downloaded it).
images_path = "imagenette2-320/val"

# 2. Load the model into LightlyStudio. Register the generator BEFORE creating the
# dataset, so ingestion embeds live with it instead of a built-in model.
# cleanup_existing=True resets the local database each run; remove it to keep prior runs.
db_manager.connect(cleanup_existing=True)
ls.set_default_embedding_model(LightlyTrainEmbeddingGenerator(model_file=MODEL_FILE))
dataset = ls.ImageDataset.create(name="lightlytrain-embeddings")
# tag_depth=1 tags each image with its class folder, so you can color the plot by class.
dataset.add_images_from_path(path=images_path, tag_depth=1)

# 3. Curate in code: select a diverse subset. The result is stored as a tag you can
# open in the app. You can also do this interactively with the lasso in the GUI.
dataset.query().sampling().diverse(
    n_samples_to_select=32, sampling_result_tag_name="diverse_subset"
)

# 4. Explore the embedding map. Open the printed URL and pick the Embed panel.
ls.start_gui(open_browser=True)
