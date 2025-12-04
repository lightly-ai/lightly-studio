"""Perception Encoder embedding generator."""

from __future__ import annotations

from pathlib import Path
from typing import Callable
from uuid import UUID

import cv2
import fsspec
import numpy as np
import torch
from numpy.typing import NDArray
from PIL import Image
from torch.utils.data import DataLoader, Dataset
from tqdm import tqdm

from lightly_studio.models.embedding_model import EmbeddingModelCreate
from lightly_studio.vendor.perception_encoder.vision_encoder import pe, transforms

from . import file_utils
from .embedding_generator import ImageEmbeddingGenerator, VideoEmbeddingGenerator

MODEL_NAME = "PE-Core-T16-384"

MAX_BATCH_SIZE: int = 16
VIDEO_FRAMES_PER_SAMPLE: int = 8


# TODO move to helper
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


# Dataset for efficient batched video loading and preprocessing
class _VideoFileDataset(Dataset[torch.Tensor]):
    """Dataset wrapping video file paths and a preprocess function."""

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
        video_path = self.filepaths[idx]
        frames = self._load_frames(video_path)
        if not frames:
            raise ValueError(f"Unable to read frames from video '{video_path}'.")

        processed_frames = [self.preprocess(frame) for frame in frames]
        return torch.stack(processed_frames)

    def _load_frames(self, video_path: str) -> list[Image.Image]:
        """Sample uniformly spaced frames and return them as PIL images."""
        capture = cv2.VideoCapture(video_path)
        if not capture.isOpened():
            raise ValueError(f"Unable to open video '{video_path}'.")

        try:
            total_frames = int(capture.get(cv2.CAP_PROP_FRAME_COUNT)) or 0
            frames_to_sample = (
                VIDEO_FRAMES_PER_SAMPLE if total_frames >= VIDEO_FRAMES_PER_SAMPLE else total_frames
            )

            frames: list[Image.Image]
            if frames_to_sample > 0:
                frame_indices = np.linspace(
                    0,
                    max(total_frames - 1, 0),
                    num=frames_to_sample,
                    dtype=int,
                )
                frames = self._read_specific_frames(capture, frame_indices)
            else:
                frames = []

            if not frames:
                return []

            return self._pad_frames(frames)
        finally:
            capture.release()

    def _read_specific_frames(
        self, capture: cv2.VideoCapture, indices: NDArray[np.int32]
    ) -> list[Image.Image]:
        """Read frames at the provided indices."""
        frames: list[Image.Image] = []
        for frame_idx in indices:
            capture.set(cv2.CAP_PROP_POS_FRAMES, int(frame_idx))
            success, frame = capture.read()
            if not success:
                break
            frames.append(self._to_pil(frame))
        return frames

    def _pad_frames(self, frames: list[Image.Image]) -> list[Image.Image]:
        """Ensure a fixed number of frames by repeating the last frame if needed."""
        if len(frames) >= VIDEO_FRAMES_PER_SAMPLE:
            return frames[:VIDEO_FRAMES_PER_SAMPLE]

        padded_frames = frames.copy()
        last_frame = frames[-1]
        while len(padded_frames) < VIDEO_FRAMES_PER_SAMPLE:
            padded_frames.append(last_frame.copy())
        return padded_frames

    @staticmethod
    def _to_pil(frame: NDArray[np.float32]) -> Image.Image:
        """Convert an OpenCV BGR frame to a PIL Image."""
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        return Image.fromarray(rgb_frame)


class PerceptionEncoderEmbeddingGenerator(ImageEmbeddingGenerator, VideoEmbeddingGenerator):
    """Perception Encoder Core embedding model."""

    def __init__(self) -> None:
        """Initialize the Perception Encoder Core embedding model.

        This method loads the Perception Encoder Core model and its tokenizer. The model
        checkpoint is downloaded and cached locally for future use.
        """
        self._model, model_path = pe.CLIP.from_config(MODEL_NAME, pretrained=True)
        self._preprocess = transforms.get_image_transform(self._model.image_size)
        self._tokenizer = transforms.get_text_tokenizer(self._model.context_length)

        # Auto select device: CUDA > MPS (Apple Silicon) > CPU
        self._device = torch.device(
            "cuda"
            if torch.cuda.is_available()
            else "mps"
            if torch.backends.mps.is_available()
            else "cpu"
        )
        self._model = self._model.to(self._device)
        self._model_hash = file_utils.get_file_xxhash(Path(model_path))

    def get_embedding_model_input(self, dataset_id: UUID) -> EmbeddingModelCreate:
        """Generate an EmbeddingModelCreate instance.

        Args:
            dataset_id: The ID of the dataset.

        Returns:
            An EmbeddingModelCreate instance with the model details.
        """
        return EmbeddingModelCreate(
            name=MODEL_NAME,
            embedding_model_hash=self._model_hash,
            embedding_dimension=self._model.output_dim,
            dataset_id=dataset_id,
        )

    def embed_text(self, text: str) -> list[float]:
        """Embed a text with Perception Encoder.

        Args:
            text: The text to embed.

        Returns:
            A list of floats representing the generated embedding.
        """
        tokenized = self._tokenizer([text]).to(self._device)
        with torch.no_grad():
            embedding = self._model.encode_text(tokenized, normalize=True)[0]
            # Convert embedding to list of floats.
            embedding_list: list[float] = embedding.cpu().numpy().flatten().tolist()
        return embedding_list

    def embed_images(self, filepaths: list[str]) -> NDArray[np.float32]:
        """Embed images with Perception Encoder.

        Args:
            filepaths: A list of file paths to the images to embed.

        Returns:
            A numpy array representing the generated embeddings
            in the same order as the input file paths.
        """
        dataset = _ImageFileDataset(filepaths, self._preprocess)

        # To avoid issues with db locking and multiprocessing we set the
        # number of workers to 0 (no multiprocessing). The DataLoader is still
        # very useful for batching and async prefetching of images.
        loader = DataLoader(
            dataset,
            batch_size=MAX_BATCH_SIZE,
            num_workers=0,  # must be 0 to avoid multiprocessing issues
        )
        total_images = len(filepaths)
        if not total_images:
            return np.empty((0, self._model.output_dim), dtype=np.float32)

        embeddings = np.empty((total_images, self._model.output_dim), dtype=np.float32)
        position = 0
        with tqdm(
            total=total_images, desc="Generating embeddings", unit=" images"
        ) as progress_bar, torch.no_grad():
            for images_tensor in loader:
                imgs = images_tensor.to(self._device, non_blocking=True)
                batch_embeddings = self._model.encode_image(imgs, normalize=True).cpu().numpy()
                batch_size = imgs.size(0)
                embeddings[position : position + batch_size] = batch_embeddings
                position += batch_size
                progress_bar.update(batch_size)

        return embeddings

    def embed_videos(self, filepaths: list[str]) -> NDArray[np.float32]:
        """Embed images with Perception Encoder.

        Args:
            filepaths: A list of file paths to the images to embed.

        Returns:
            A numpy array representing the generated embeddings
            in the same order as the input file paths.
        """
        dataset = _VideoFileDataset(filepaths, self._preprocess)

        # To avoid issues with db locking and multiprocessing we set the
        # number of workers to 0 (no multiprocessing). The DataLoader is still
        # very useful for batching and async prefetching of images.
        loader = DataLoader(
            dataset,
            batch_size=MAX_BATCH_SIZE,
            num_workers=0,  # must be 0 to avoid multiprocessing issues
        )
        total_videos = len(filepaths)
        if not total_videos:
            return np.empty((0, self._model.output_dim), dtype=np.float32)

        embeddings = np.empty((total_videos, self._model.output_dim), dtype=np.float32)
        position = 0
        with tqdm(
            total=total_videos, desc="Generating embeddings", unit=" videos"
        ) as progress_bar, torch.no_grad():
            for images_tensor in loader:
                videos = images_tensor.to(self._device, non_blocking=True)
                batch_embeddings = self._model.encode_video(videos, normalize=True).cpu().numpy()
                batch_size = videos.size(0)
                embeddings[position : position + batch_size] = batch_embeddings
                position += batch_size
                progress_bar.update(batch_size)

        return embeddings
