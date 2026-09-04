"""Perception Encoder embedding generator."""

from __future__ import annotations

from collections.abc import Callable, Iterator

import fsspec
import numpy as np
import torch
from av import FFmpegError, container
from PIL import Image
from tqdm import tqdm

from lightly_studio.core.file_outcome_report import (
    BrokenInputFileError,
    FileOutcome,
    FileOutcomeReport,
    MissingInputFileError,
)
from lightly_studio.dataset.env import LIGHTLY_STUDIO_MODEL_CACHE_DIR
from lightly_studio.embed.embedder import (
    CropPathEmbedder,
    ImagePathEmbedder,
    ImagePILEmbedder,
    TextEmbedder,
    VideoPathEmbedder,
)
from lightly_studio.embed.types import EmbeddingResult, EmbeddingSpaceSpec, ImageCrop
from lightly_studio.utils import batching
from lightly_studio.vendor.perception_encoder.vision_encoder import pe, transforms

from . import image_crop_embedding, image_embedding
from .image_embedding import EmbeddingContext

MODEL_NAME = "PE-Core-T16-384"
DEFAULT_VIDEO_CHANNEL = 0
MAX_BATCH_SIZE: int = 16
VIDEO_FRAMES_PER_SAMPLE: int = 8


class PerceptionEncoderEmbedder(
    ImagePathEmbedder,
    CropPathEmbedder,
    ImagePILEmbedder,
    TextEmbedder,
    VideoPathEmbedder,
):
    """Perception Encoder Core embedding model."""

    def __init__(self) -> None:
        """Initialize the Perception Encoder Core embedding model.

        This method loads the Perception Encoder Core model and its tokenizer. The model
        checkpoint is downloaded and cached locally for future use.
        """
        LIGHTLY_STUDIO_MODEL_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        self._model, _ = pe.CLIP.from_config(
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

    def embedding_space_spec(self) -> EmbeddingSpaceSpec:
        """Describe the embedding space produced by this generator.

        Returns:
            A specification of the embedding space.
        """
        return EmbeddingSpaceSpec(
            space_key=MODEL_NAME,
            dimension=self._model.output_dim,
        )

    def embed_text(self, texts: list[str]) -> EmbeddingResult:
        """Embed a batch of texts with Perception Encoder.

        Args:
            texts: The strings to embed.

        Returns:
            The embeddings and the indices of the inputs they cover.
        """
        if not texts:
            empty = np.empty((0, self._model.output_dim), dtype=np.float32)
            return EmbeddingResult(embeddings=empty, kept_indices=[])

        tokenized = self._tokenizer(texts).to(self._device)
        with torch.no_grad():
            embeddings = self._model.encode_text(tokenized, normalize=True).cpu().numpy()
        return EmbeddingResult(
            embeddings=embeddings.astype(np.float32), kept_indices=list(range(len(texts)))
        )

    def embed_images(self, paths: list[str]) -> EmbeddingResult:
        """Embed images with Perception Encoder.

        Args:
            paths: fsspec paths or URLs of the images to embed.

        Returns:
            The embeddings and the indices of the inputs they cover.
        """
        return image_embedding.embed_image_files_batched(
            filepaths=paths,
            context=self._embedding_context(),
            show_progress=True,
        )

    def embed_crops(self, crops: list[ImageCrop]) -> EmbeddingResult:
        """Embed image crops with Perception Encoder.

        Args:
            crops: The crops to embed.

        Returns:
            The embeddings and the indices of the inputs they cover.
        """
        return image_crop_embedding.embed_image_crops_batched(
            image_crops=crops,
            context=self._embedding_context(),
            show_progress=True,
        )

    def embed_frames(self, frames: list[Image.Image]) -> EmbeddingResult:
        """Embed video frames with Perception Encoder.

        Args:
            frames: The frames to embed, as PIL images.

        Returns:
            The embeddings and the indices of the inputs they cover.
        """
        embeddings = image_embedding.embed_pil_images_batched(
            images=frames,
            context=self._embedding_context(),
            show_progress=True,
        )
        return EmbeddingResult(embeddings=embeddings, kept_indices=list(range(len(frames))))

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

    def embed_videos(self, paths: list[str]) -> EmbeddingResult:
        """Embed videos with Perception Encoder, skipping missing or broken files.

        Args:
            paths: fsspec paths or URLs of the videos to embed.

        Returns:
            An ``EmbeddingResult`` whose embeddings cover only the readable videos, with
            ``kept_indices`` mapping each row back to its input position.

        Raises:
            AllInputFilesFailedError: If every attempted file was missing or broken.
        """
        total_videos = len(paths)
        if not total_videos:
            empty = np.empty((0, self._model.output_dim), dtype=np.float32)
            return EmbeddingResult(embeddings=empty, kept_indices=[])

        embeddings = np.empty((total_videos, self._model.output_dim), dtype=np.float32)
        kept_indices: list[int] = []
        report = FileOutcomeReport(label_overrides={FileOutcome.ADDED: "embedded"})

        def preprocessed_videos_iter() -> Iterator[torch.Tensor]:
            for index, filepath in enumerate(paths):
                frames: torch.Tensor | None = None
                with report.track(path=filepath):
                    frames = _load_video_frames(filepath, self._preprocess)
                if frames is not None:
                    kept_indices.append(index)
                    yield frames

        position = 0
        with (
            tqdm(total=total_videos, desc="Generating embeddings", unit=" videos") as progress_bar,
            torch.no_grad(),
        ):
            for batch in batching.batched(preprocessed_videos_iter(), batch_size=MAX_BATCH_SIZE):
                videos_tensor = torch.stack(batch).to(self._device)
                batch_embeddings = (
                    self._model.encode_video(videos_tensor, normalize=True).cpu().numpy()
                )
                batch_size = videos_tensor.size(0)
                embeddings[position : position + batch_size] = batch_embeddings
                position += batch_size
                progress_bar.update(batch_size)

        report.log_summary()
        report.raise_if_all_failed()

        return EmbeddingResult(embeddings=embeddings[:position], kept_indices=kept_indices)


def _load_video_frames(
    filepath: str,
    preprocess: Callable[[Image.Image], torch.Tensor],
) -> torch.Tensor:
    """Sample uniformly spaced frames from a video and stack them into a model input.

    As in the original paper we subsample N frames from a video and stack them to a tensor.
    As in the paper, we use a default of 8 frames per video (VIDEO_FRAMES_PER_SAMPLE).
    Note: the video length in the paper was 16.7 +/- 9.8 sec, hence for longer videos we might
    consider alternative models or more frames.

    Using seek for sampling is fast, however it may yield slightly different results on
    different OS (known issue: MacOS vs Linux). Alternative option is to decode frame-by-frame
    to be OS independent, however this comes with a performance drop.

    Args:
        filepath: Path or URL of the video to sample frames from.
        preprocess: Transform applied to each sampled frame to produce a model input tensor.

    Returns:
        Tensor of shape ``[VIDEO_FRAMES_PER_SAMPLE, C, H, W]``.

    Raises:
        MissingInputFileError: If the video path does not resolve.
        BrokenInputFileError: If the video is present but unreadable/undecodable (corrupt,
            has no video stream, or has no usable duration).
    """
    fs, fs_path = fsspec.core.url_to_fs(url=filepath)
    if not fs.exists(fs_path):
        raise MissingInputFileError(f"Video does not exist: '{filepath}'.")

    try:
        with (
            fs.open(path=fs_path, mode="rb") as video_file,
            container.open(file=video_file) as video_container,
        ):
            video_stream = video_container.streams.video[DEFAULT_VIDEO_CHANNEL]
            duration_pts = video_stream.duration
            time_base = float(video_stream.time_base)
            if duration_pts is None or duration_pts <= 0 or time_base <= 0.0:
                raise BrokenInputFileError(f"Unable to read frames from video '{filepath}'.")

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
                try:
                    frame = next(video_container.decode(video=DEFAULT_VIDEO_CHANNEL))
                except StopIteration as error:
                    raise BrokenInputFileError(
                        f"Unable to decode frame at {ts_target:.3f}s from video '{filepath}'."
                    ) from error
                frames.append(frame.to_image())
    except (OSError, FFmpegError, IndexError) as error:
        raise BrokenInputFileError(f"Unable to read frames from video '{filepath}'.") from error

    processed_frames = [preprocess(frame) for frame in frames]
    return torch.stack(processed_frames)
