"""Exports video-frame datasets from Lightly Studio into various formats."""

from __future__ import annotations

import logging
from collections.abc import Iterable, Sequence
from typing import cast
from uuid import UUID

import fsspec
from av import FFmpegError, container
from labelformat.model.image import Image
from PIL import Image as PILImage
from sqlmodel import Session
from tqdm import tqdm

from lightly_studio.core.sample import Sample
from lightly_studio.core.video.video_frame_sample import VideoFrameSample
from lightly_studio.export.dataset_export import DatasetExport
from lightly_studio.type_definitions import PathLike

logger = logging.getLogger(__name__)

ROTATION_90_DEG = 90
ROTATION_180_DEG = 180
ROTATION_270_DEG = 270


class VideoFrameDatasetExport(DatasetExport):
    """Provides methods to export a video-frame dataset or a subset of it.

    This class is typically not instantiated directly but returned by
    `VideoFrameDataset.export()`. It allows exporting data in various formats.
    """

    def __init__(
        self,
        session: Session,
        dataset_id: UUID,
        samples: Iterable[VideoFrameSample],
    ):
        """Initializes the VideoFrameDatasetExport object.

        Args:
            session: The database session.
            dataset_id: The dataset ID for label retrieval.
            samples: Samples to export.
        """
        self.samples_list = list(samples)
        super().__init__(
            session=session,
            dataset_id=dataset_id,
            samples=self.samples_list,
            sample_to_image=video_frame_to_image,
        )

    def to_jpeg_files(self, output_dir: PathLike) -> None:
        """Export video frames as JPEG files to a local or S3 directory.

        Decodes each frame from its parent video and writes it as a JPEG file to
        the output directory with a structured filename: {video_name}/{frame_number}.jpg.
        Frames from the same video are decoded in a single pass to avoid reopening
        the video file for every frame.

        Args:
            output_dir: The output directory path (can be local or s3://bucket/prefix).

        Raises:
            ValueError: If a video file cannot be opened or a frame cannot be decoded.
        """
        output_dir_str = str(output_dir)
        fs, fs_path = fsspec.core.url_to_fs(url=output_dir_str)

        if not fs.exists(fs_path):
            fs.makedirs(fs_path, exist_ok=True)

        # Group frames by their parent video to minimize video file openings.
        frames_by_video: dict[str, list[VideoFrameSample]] = {}
        for frame_sample in self.samples_list:
            video_path = frame_sample.parent_video.file_path_abs
            frames_by_video.setdefault(video_path, []).append(frame_sample)

        for video_path, frame_samples in frames_by_video.items():
            try:
                _decode_frame_to_pil(
                    video_path=video_path,
                    frames=frame_samples,
                    fs=fs,
                    output_dir=fs_path,
                )
            except Exception as e:
                logger.warning(f"Failed to export frames from video {video_path}: {e}")


def video_frame_to_image(sample: Sample, image_id: int, use_relative_filename: bool) -> Image:
    """Maps a video-frame sample to a labelformat `Image`.

    Conforms to the `SampleToImage` strategy, so `sample` is typed as `Sample`; it is always
    a `VideoFrameSample` here because this strategy is only used by `VideoFrameDatasetExport`.

    A frame has no file of its own, so the file name is synthesized from the parent video and
    the frame number (``<video>/<frame_number>.jpg``) and the dimensions are the parent video's.
    COCO stores the absolute video path verbatim; YOLO and Pascal VOC need a relative video name.
    """
    frame_sample = cast(VideoFrameSample, sample)
    video = frame_sample.parent_video
    video_reference = video.file_name if use_relative_filename else video.file_path_abs
    return Image(
        id=image_id,
        filename=f"{video_reference}/{frame_sample.frame_number:09d}.jpg",
        width=video.width,
        height=video.height,
    )


def _apply_rotation(image: PILImage.Image, rotation_deg: int) -> PILImage.Image:
    """Apply counter-rotation to an image based on metadata rotation.

    Args:
        image: PIL Image to rotate.
        rotation_deg: Rotation in degrees (0, 90, 180, 270).

    Returns:
        Rotated PIL Image.
    """
    if rotation_deg == ROTATION_90_DEG:
        return image.rotate(-ROTATION_90_DEG, expand=True)
    if rotation_deg == ROTATION_180_DEG:
        return image.rotate(-ROTATION_180_DEG, expand=True)
    if rotation_deg == ROTATION_270_DEG:
        return image.rotate(-ROTATION_270_DEG, expand=True)
    return image


def _decode_frame_to_pil(
    video_path: str,
    frames: Sequence[VideoFrameSample],
    fs: fsspec.AbstractFileSystem,
    output_dir: str,
) -> None:
    """Decode frames from a video and save them as JPEG files.

    Opens the video once and exports all requested frames in a single decode pass.

    Args:
        video_path: Path to the video file (local or S3).
        frames: Frames from the same video to decode and export.
        fs: fsspec filesystem instance for the output directory.
        output_dir: Output directory path in the filesystem.

    Raises:
        ValueError: If the video cannot be opened or frames cannot be decoded.
    """
    if not frames:
        return

    frames_by_number = {frame.frame_number: frame for frame in frames}
    max_frame_number = max(frames_by_number)
    total_frames = len(frames_by_number)

    video_fs, video_fs_path = fsspec.core.url_to_fs(url=video_path)
    video_file = video_fs.open(path=video_fs_path, mode="rb")
    try:
        try:
            video_container = container.open(file=video_file)
        except (OSError, FFmpegError) as e:
            raise ValueError(f"Could not open video {video_path}: {e}") from e

        try:
            video_stream = video_container.streams.video[0]
            with tqdm(total=total_frames, desc="Exporting frames", unit=" frames") as pbar:
                for frame_count, frame in enumerate(video_container.decode(video_stream)):
                    if frame_count > max_frame_number:
                        break
                    if frame_count not in frames_by_number:
                        continue

                    frame_sample = frames_by_number.pop(frame_count)
                    try:
                        pil_image = _apply_rotation(
                            image=frame.to_image().convert("RGB"),
                            rotation_deg=frame_sample.rotation_deg,
                        )
                        filename = f"{frame_sample.parent_video.file_name}/{frame_count:09d}.jpg"
                        _save_jpeg_file(
                            fs=fs,
                            output_dir=output_dir,
                            filename=filename,
                            image=pil_image,
                        )
                    except Exception as e:
                        logger.warning(
                            f"Failed to export frame {frame_count} from video {video_path}: {e}"
                        )
                    pbar.update(1)
                    if not frames_by_number:
                        break
        except (OSError, FFmpegError) as e:
            raise ValueError(f"Could not decode frames from {video_path}: {e}") from e
        finally:
            video_container.close()
    finally:
        video_file.close()

    if frames_by_number:
        missing = ", ".join(str(n) for n in sorted(frames_by_number))
        raise ValueError(f"Frames [{missing}] not found in video {video_path}")


def _save_jpeg_file(
    fs: fsspec.AbstractFileSystem, output_dir: str, filename: str, image: PILImage.Image
) -> None:
    """Save a PIL Image as JPEG to a local or cloud path.

    Args:
        fs: fsspec filesystem instance.
        output_dir: Output directory path in the filesystem.
        filename: Relative filename (can include subdirectories).
        image: PIL Image to save.
    """
    file_path = f"{output_dir}/{filename}".replace("\\", "/")

    dir_path = file_path.rsplit("/", 1)[0]
    if not fs.exists(dir_path):
        fs.makedirs(dir_path, exist_ok=True)

    with fs.open(file_path, "wb") as f:
        image.save(f, format="JPEG", quality=95)
