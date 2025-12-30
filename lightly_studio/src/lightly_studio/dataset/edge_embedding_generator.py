"""EdgeCLIP embedding generator."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Tuple
from uuid import UUID

import cv2
import fsspec
import numpy as np
from lightly_edge_sdk import (
    InferenceDeviceType,
    LightlyEdge,
    LightlyEdgeConfig,
    LightlyEdgeDetectorConfig,
)
from numpy.typing import NDArray
from torch.utils.data import DataLoader, Dataset
from tqdm import tqdm

from lightly_studio.dataset.embedding_generator import ImageEmbeddingGenerator
from lightly_studio.models.embedding_model import EmbeddingModelCreate

MAX_BATCH_SIZE: int = 1


class _ImageFileDatasetEdge(Dataset[Tuple[bytes, int, int]]):
    """Dataset wrapping image file paths for processing."""

    def __init__(
        self,
        filepaths: Sequence[str],
    ) -> None:
        self.filepaths = filepaths

    def __len__(self) -> int:
        return len(self.filepaths)

    def __getitem__(self, idx: int) -> tuple[bytes, int, int]:
        # Load the image.
        with fsspec.open(self.filepaths[idx], "rb") as file:
            image_bytes = file.read()
            # Decode image from bytes using OpenCV
            nparr = np.frombuffer(image_bytes, np.uint8)
            bgr_image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            rgb_image = cv2.cvtColor(bgr_image, cv2.COLOR_BGR2RGB)
            rgb_bytes = rgb_image.tobytes()
            height, width, _ = rgb_image.shape
            return rgb_bytes, width, height


class EdgeSDKEmbeddingGenerator(ImageEmbeddingGenerator):
    """Embedding generator using Edge SDK runtime."""

    def __init__(self, model_path: str) -> None:
        """Initialize the LightlyEdge object.

        Args:
            model_path: Path to the model tar file.
        """
        # Initialize the LightlyEdge SDK.
        config = _create_edge_config()
        self.lightly_edge = LightlyEdge(
            path=model_path,
            config=config,
        )
        model_config = self.lightly_edge.get_image_model_config()
        self._model_hash = model_config.model_hash
        self._embedding_size = model_config.embedding_size
        self._model_name = model_config.model_name

    def get_embedding_model_input(self, collection_id: UUID) -> EmbeddingModelCreate:
        """Generate an EmbeddingModelInput instance.

        Args:
            collection_id: The ID of the collection.

        Returns:
            An EmbeddingModelInput instance with the model details.
        """
        return EmbeddingModelCreate(
            name=self._model_name,
            embedding_model_hash=self._model_hash,
            embedding_dimension=self._embedding_size,
            collection_id=collection_id,
        )

    def embed_text(self, text: str) -> list[float]:
        """Embed a text with EdgeCLIP.

        Args:
            text: The text to embed.

        Returns:
            A list of floats representing the generated embedding.
        """
        embeddings = self.lightly_edge.embed_texts([text])
        if len(embeddings):
            return embeddings[0]
        return []

    def embed_images(self, filepaths: list[str], show_progress: bool = True) -> NDArray[np.float32]:
        """Embed images with EdgeSDK.

        Args:
            filepaths: A list of file paths to the images to embed.
            show_progress: Whether to show a progress bar during embedding.

        Returns:
            A numpy array representing the generated embeddings.
        """
        total_images = len(filepaths)
        if not total_images:
            return np.empty((0, self._embedding_size), dtype=np.float32)

        dataset = _ImageFileDatasetEdge(filepaths)

        # To avoid issues with db locking and multiprocessing we set the
        # number of workers to 0 (no multiprocessing). The DataLoader is still
        # very useful for batching and async prefetching of images.
        loader = DataLoader(
            dataset,
            batch_size=MAX_BATCH_SIZE,
            num_workers=0,  # must be 0 to avoid multiprocessing issues
            pin_memory=True,
        )

        embeddings = np.empty((total_images, self._embedding_size), dtype=np.float32)
        with tqdm(
            total=total_images,
            desc="Generating embeddings",
            unit=" images",
            disable=not show_progress,
        ) as progress_bar:
            for i, (rgb_bytes, width, height) in enumerate(loader):
                embedding = self.lightly_edge.embed_frame_rgb_bytes(
                    rgb_bytes=rgb_bytes[0],
                    width=width[0].item(),
                    height=height[0].item(),
                )
                embeddings[i] = embedding
                progress_bar.update(1)

        return embeddings


def _create_edge_config() -> LightlyEdgeConfig:
    """Create configuration for LightlyEdge.

    Returns:
        Configured LightlyEdgeConfig instance.
    """
    config = LightlyEdgeConfig.default()
    config.inference_device_type = InferenceDeviceType.Auto
    config.detector_config = LightlyEdgeDetectorConfig(
        object_detector_enable=False,
        classifiers_enable=False,
        max_classifications=0,
    )
    return config
