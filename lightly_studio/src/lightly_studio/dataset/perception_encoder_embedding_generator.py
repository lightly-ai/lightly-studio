"""Perception Encoder embedding generator."""

from __future__ import annotations

from pathlib import Path
from typing import Callable
from uuid import UUID

import fsspec
import numpy as np
import torch
from av import FFmpegError, container
from numpy.typing import NDArray
from PIL import Image
from torch.utils.data import DataLoader, Dataset
from tqdm import tqdm

from lightly_studio.models.embedding_model import EmbeddingModelCreate
from lightly_studio.vendor.perception_encoder.vision_encoder import pe, transforms

from . import file_utils
from .embedding_generator import ImageEmbeddingGenerator, VideoEmbeddingGenerator

MODEL_NAME = "PE-Core-T16-384"
DEFAULT_VIDEO_CHANNEL = 0
MAX_BATCH_SIZE: int = 16
VIDEO_FRAMES_PER_SAMPLE: int = 8


# TODO(Jonas, 12/225): Move to a helper.
class _ImageFileDataset(Dataset[torch.Tensor]):
    """Dataset wrapping image file paths and a preprocess function.

    Used for efficient batched image loading and preprocessing
    """

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
        try:
            # Open video and extract metadata
            fs, fs_path = fsspec.core.url_to_fs(url=video_path)
            video_file = fs.open(path=fs_path, mode="rb")
            try:
                # Open video container for reading (returns InputContainer)
                video_container = container.open(file=video_file)
                video_stream = video_container.streams.video[DEFAULT_VIDEO_CHANNEL]

                if video_stream.duration is None:
                    video_container.close()
                    return []

                ts_to_sample = np.linspace(
                    0, video_stream.duration, num=VIDEO_FRAMES_PER_SAMPLE, dtype=int
                )

                frames: list[Image.Image] = []
                for ts_target in ts_to_sample:
                    video_container.seek(offset=int(ts_target), stream=video_stream)
                    frame = next(video_container.decode(video=DEFAULT_VIDEO_CHANNEL))
                    frames.append(frame.to_image())

                video_container.close()
                return frames
            finally:
                # Ensure file is closed even if container operations fail
                video_file.close()
        except (FileNotFoundError, OSError, IndexError, FFmpegError) as e:
            raise ValueError(f"Error processing video {video_path}: {e}") from e


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
        total_images = len(filepaths)
        if not total_images:
            return np.empty((0, self._model.output_dim), dtype=np.float32)

        dataset = _ImageFileDataset(filepaths, self._preprocess)

        # To avoid issues with db locking and multiprocessing we set the
        # number of workers to 0 (no multiprocessing). The DataLoader is still
        # very useful for batching and async prefetching of images.
        loader = DataLoader(
            dataset,
            batch_size=MAX_BATCH_SIZE,
            num_workers=0,  # must be 0 to avoid multiprocessing issues
        )

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
