"""Perception Encoder embedding generator."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable
from uuid import UUID

import fsspec
import numpy as np
import torch
from av import FFmpegError, container
from numpy.typing import NDArray
from PIL import Image
from tqdm import tqdm

from lightly_studio.core.file_outcome_report import FileOutcome, FileOutcomeReport
from lightly_studio.dataset.env import LIGHTLY_STUDIO_MODEL_CACHE_DIR
from lightly_studio.models.embedding_model import EmbeddingModelCreate
from lightly_studio.vendor.perception_encoder.vision_encoder import pe, transforms

from . import file_utils, image_crop_embedding, image_embedding
from .embedding_generator import ImageCrop, ImageEmbeddingGenerator, VideoEmbeddingGenerator
from .embedding_result import EmbeddingResult
from .image_embedding import EmbeddingContext

MODEL_NAME = "PE-Core-T16-384"
DEFAULT_VIDEO_CHANNEL = 0
MAX_BATCH_SIZE: int = 16
VIDEO_FRAMES_PER_SAMPLE: int = 8


def _load_video_frames(
    filepath: str,
    preprocess: Callable[[Image.Image], torch.Tensor],
) -> torch.Tensor | None:
    """Sample uniformly spaced frames from a video and stack them into a model input.

    As in the original paper we subsample N frames from a video and stack them to a tensor.
    As in the paper, we use a default of 8 frames per video (VIDEO_FRAMES_PER_SAMPLE).
    Note: the video length in the paper was 16.7 +/- 9.8 sec, hence for longer videos we might
    consider alternative models or more frames.

    Using seek for sampling is fast, however it may yield slightly different results on
    different OS (known issue: MacOS vs Linux). Alternative option is to decode frame-by-frame
    to be OS independent, however this comes with a performance drop.

    Returns:
        Tensor of shape ``[VIDEO_FRAMES_PER_SAMPLE, C, H, W]``, or ``None`` if the video is
        unreadable/undecodable (missing, corrupt, no video stream, or no usable duration).
    """
    try:
        fs, fs_path = fsspec.core.url_to_fs(url=filepath)
        with (
            fs.open(path=fs_path, mode="rb") as video_file,
            container.open(file=video_file) as video_container,
        ):
            video_stream = video_container.streams.video[DEFAULT_VIDEO_CHANNEL]
            duration_pts = video_stream.duration
            time_base = float(video_stream.time_base)
            if duration_pts is None or duration_pts <= 0 or time_base <= 0.0:
                return None

            duration_seconds = duration_pts * time_base

            # Sample VIDEO_FRAMES_PER_SAMPLE evenly spaced inside [0, duration_seconds)
            ts_to_sample = np.linspace(
                0.0,
                duration_seconds,
                num=VIDEO_FRAMES_PER_SAMPLE,
                endpoint=False,
                dtype=np.float64,
            )

            frames: list[Image.Image] = []
            for ts_target in ts_to_sample:
                pts_target = int(ts_target / time_base)
                video_container.seek(offset=pts_target, stream=video_stream)
                frame = next(video_container.decode(video=DEFAULT_VIDEO_CHANNEL))
                frames.append(frame.to_image())
    except (OSError, FFmpegError, IndexError, StopIteration):
        return None

    processed_frames = [preprocess(frame) for frame in frames]
    return torch.stack(processed_frames)


class PerceptionEncoderEmbeddingGenerator(ImageEmbeddingGenerator, VideoEmbeddingGenerator):
    """Perception Encoder Core embedding model."""

    def __init__(self) -> None:
        """Initialize the Perception Encoder Core embedding model.

        This method loads the Perception Encoder Core model and its tokenizer. The model
        checkpoint is downloaded and cached locally for future use.
        """
        LIGHTLY_STUDIO_MODEL_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        self._model, model_path = pe.CLIP.from_config(
            name=MODEL_NAME, pretrained=True, download_dir=LIGHTLY_STUDIO_MODEL_CACHE_DIR
        )
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
            embedding_dimension=self._model.output_dim,
            collection_id=collection_id,
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

    def embed_images(self, filepaths: list[str], show_progress: bool = True) -> EmbeddingResult:
        """Embed images with Perception Encoder.

        Args:
            filepaths: A list of file paths to the images to embed.
            show_progress: Whether to show a progress bar during embedding.

        Returns:
            An ``EmbeddingResult`` with embeddings for the readable files, in the same
            order as the corresponding input file paths.
        """
        return image_embedding.embed_image_files_batched(
            filepaths=filepaths,
            context=self._embedding_context(),
            show_progress=show_progress,
        )

    def embed_image_crops(
        self, image_crops: list[ImageCrop], show_progress: bool = True
    ) -> NDArray[np.float32]:
        """Embed image crops with Perception Encoder.

        Args:
            image_crops: A list of image crop definitions to embed.
            show_progress: Whether to show a progress bar during embedding.

        Returns:
            A numpy array representing the generated embeddings in the same order
            as the input crops.
        """
        return image_crop_embedding.embed_image_crops_batched(
            image_crops=image_crops,
            context=self._embedding_context(),
            show_progress=show_progress,
        )

    def embed_pil_images(
        self, images: list[Image.Image], show_progress: bool = True
    ) -> NDArray[np.float32]:
        """Embed in-memory PIL images with Perception Encoder.

        Args:
            images: PIL images to embed.
            show_progress: Whether to show a progress bar during embedding.

        Returns:
            A numpy array representing the generated embeddings in the same order
            as the input images.
        """
        return image_embedding.embed_pil_images_batched(
            images=images,
            context=self._embedding_context(),
            show_progress=show_progress,
        )

    def _embedding_context(self) -> EmbeddingContext:
        """Build the model-specific configuration for batched image embedding."""
        return EmbeddingContext(
            embedding_dimension=self._model.output_dim,
            max_batch_size=MAX_BATCH_SIZE,
            device=self._device,
            preprocess=self._preprocess,
            encode_batch=lambda images_tensor: (
                self._model.encode_image(images_tensor, normalize=True).cpu().numpy()
            ),
        )

    def embed_videos(self, filepaths: list[str]) -> EmbeddingResult:
        """Embed videos with Perception Encoder, skipping broken files.

        A video that is unreadable/undecodable is skipped rather than aborting the whole
        run, and is recorded once as broken.

        Args:
            filepaths: A list of file paths to the videos to embed.

        Returns:
            An ``EmbeddingResult`` whose embeddings cover only the readable videos, with
            ``kept_indices`` mapping each row back to its input position.

        Raises:
            AllInputFilesFailedError: If at least one file was attempted and every attempted
                file was broken (i.e. no file could be read and embedded).
        """
        total_videos = len(filepaths)
        if not total_videos:
            empty = np.empty((0, self._model.output_dim), dtype=np.float32)
            return EmbeddingResult(embeddings=empty, kept_indices=[])

        embeddings = np.empty((total_videos, self._model.output_dim), dtype=np.float32)
        # Input indices of the videos that were embedded (their file could be read).
        kept_indices: list[int] = []
        # Reusable batch buffer, lazily sized from the first preprocessed video.
        batch_buffer: torch.Tensor | None = None
        batch_indices: list[int] = []
        report = FileOutcomeReport()

        with (
            tqdm(total=total_videos, desc="Generating embeddings", unit=" videos") as progress_bar,
            torch.no_grad(),
        ):
            for index, filepath in enumerate(filepaths):
                frames = _load_video_frames(filepath, self._preprocess)
                if frames is None:
                    report.record(path=filepath, outcome=FileOutcome.BROKEN)
                    continue
                report.record(path=filepath, outcome=FileOutcome.ADDED)
                if batch_buffer is None:
                    batch_buffer = torch.empty((MAX_BATCH_SIZE, *frames.shape), dtype=frames.dtype)
                batch_buffer[len(batch_indices)] = frames
                batch_indices.append(index)
                kept_indices.append(index)
                if len(batch_indices) >= MAX_BATCH_SIZE:
                    self._flush_video_batch(
                        batch_buffer=batch_buffer,
                        batch_indices=batch_indices,
                        embeddings=embeddings,
                        progress_bar=progress_bar,
                    )

            self._flush_video_batch(
                batch_buffer=batch_buffer,
                batch_indices=batch_indices,
                embeddings=embeddings,
                progress_bar=progress_bar,
            )

        report.raise_if_all_failed()
        report.log_summary()

        # kept_indices in input order maps each returned row back to its input video.
        return EmbeddingResult(embeddings=embeddings[kept_indices], kept_indices=kept_indices)

    def _flush_video_batch(
        self,
        batch_buffer: torch.Tensor | None,
        batch_indices: list[int],
        embeddings: NDArray[np.float32],
        progress_bar: Any,
    ) -> None:
        """Encode the current video batch and write results into ``embeddings``."""
        if batch_buffer is None or not batch_indices:
            return
        filled = len(batch_indices)
        videos_tensor = batch_buffer[:filled].to(self._device, non_blocking=True)
        batch_embeddings = self._model.encode_video(videos_tensor, normalize=True).cpu().numpy()
        for batch_position, video_index in enumerate(batch_indices):
            embeddings[video_index] = batch_embeddings[batch_position]
        progress_bar.update(filled)
        batch_indices.clear()
