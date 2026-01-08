"""MobileCLIP embedding generator."""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Callable
from uuid import UUID

import fsspec
import numpy as np
import torch
from numpy.typing import NDArray
from PIL import Image
from torch.utils.data import DataLoader, Dataset
from tqdm import tqdm

from lightly_studio.models.embedding_model import EmbeddingModelCreate
from lightly_studio.vendor import mobileclip

from . import file_utils
from .embedding_generator import ImageEmbeddingGenerator

MODEL_NAME = "mobileclip_s0"
MOBILECLIP_DOWNLOAD_URL = (
    f"https://docs-assets.developer.apple.com/ml-research/datasets/mobileclip/{MODEL_NAME}.pt"
)
MAX_BATCH_SIZE: int = 16
EMBEDDING_DIMENSION: int = 512


# Dataset for efficient batched image loading and preprocessing
class _ImageFileDataset(Dataset[torch.Tensor]):
    """Dataset wrapping image file paths and a preprocess function."""

    def __init__(
        self,
        filepaths: list[str],
        preprocess: Callable[[Image.Image], torch.Tensor],
    ) -> None:
        self.filepaths = filepaths
        self.preprocess = preprocess

    def __len__(self) -> int:
        return len(self.filepaths)

    def __getitem__(self, idx: int) -> torch.Tensor:
        with fsspec.open(self.filepaths[idx], "rb") as file:
            image = Image.open(file).convert("RGB")
            return self.preprocess(image)


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
            embedding = self._model.encode_text(tokenized)[0]
            # Convert embedding to list of floats.
            embedding_list: list[float] = embedding.cpu().numpy().flatten().tolist()
        return embedding_list

    def embed_images(self, filepaths: list[str], show_progress: bool = True) -> NDArray[np.float32]:
        """Embed images with MobileCLIP.

        Args:
            filepaths: A list of file paths to the images to embed.
            show_progress: Whether to show a progress bar during embedding.

        Returns:
            A numpy array representing the generated embeddings
            in the same order as the input file paths.
        """
        total_images = len(filepaths)
        if not total_images:
            return np.empty((0, EMBEDDING_DIMENSION), dtype=np.float32)

        dataset = _ImageFileDataset(filepaths, self._preprocess)

        # To avoid issues with db locking and multiprocessing we set the
        # number of workers to 0 (no multiprocessing). The DataLoader is still
        # very useful for batching and async prefetching of images.
        loader = DataLoader(
            dataset,
            batch_size=MAX_BATCH_SIZE,
            num_workers=0,  # must be 0 to avoid multiprocessing issues
        )

        embeddings = np.empty((total_images, EMBEDDING_DIMENSION), dtype=np.float32)
        position = 0
        with tqdm(
            total=total_images,
            desc="Generating embeddings",
            unit=" images",
            disable=not show_progress,
        ) as progress_bar, torch.no_grad():
            for images_tensor in loader:
                imgs = images_tensor.to(self._device, non_blocking=True)
                batch_embeddings = self._model.encode_image(imgs).cpu().numpy()
                batch_size = imgs.size(0)
                embeddings[position : position + batch_size] = batch_embeddings
                position += batch_size
                progress_bar.update(batch_size)

        return embeddings


def _get_cached_mobileclip_checkpoint() -> Path:
    file_path = Path(tempfile.gettempdir()) / f"{MODEL_NAME}.pt"
    file_utils.download_file_if_does_not_exist(
        url=MOBILECLIP_DOWNLOAD_URL,
        local_filename=file_path,
    )
    return file_path
