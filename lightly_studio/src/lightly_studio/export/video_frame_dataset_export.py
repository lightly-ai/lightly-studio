"""Exports video-frame datasets from Lightly Studio into various formats."""

from __future__ import annotations

import logging
from collections.abc import Iterable
from typing import cast
from uuid import UUID

import av
import fsspec
import numpy as np
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

        Args:
            output_dir: The output directory path (can be local or s3://bucket/prefix).

        Raises:
            ValueError: If a video file cannot be opened or a frame cannot be decoded.
        """
        output_dir_str = str(output_dir)
        fs, fs_path = fsspec.core.url_to_fs(url=output_dir_str)

        if not fs.exists(fs_path):
            fs.makedirs(fs_path, exist_ok=True)

        frame_samples = cast(list[VideoFrameSample], self.samples_list)
        for frame_sample in tqdm(frame_samples, desc="Exporting frames", unit=" frames"):
            video_path = frame_sample.parent_video.file_path_abs
            frame_number = frame_sample.frame_number
            rotation_deg = frame_sample.rotation_deg
            video_name = frame_sample.parent_video.file_name

            try:
                pil_image = _decode_frame_to_pil(
                    video_path=video_path, frame_number=frame_number, rotation_deg=rotation_deg
                )
                filename = f"{video_name}/{frame_number:09d}.jpg"
                _save_jpeg_file(fs=fs, output_dir=fs_path, filename=filename, image=pil_image)
            except Exception as e:
                logger.warning(
                    f"Failed to export frame {frame_number} from video {video_path}: {e}"
                )


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


def _get_frame_rotation_deg(frame: av.video.frame.VideoFrame) -> int:
    """Get the rotation metadata from a video frame.

    Reads DISPLAYMATRIX side data to determine rotation.

    Args:
        frame: A decoded video frame.

    Returns:
        The rotation in degrees. Valid values are 0, 90, 180, 270.
    """
    matrix_data = frame.side_data.get("DISPLAYMATRIX")
    if matrix_data is None:
        return 0
    buffer = cast(bytes, matrix_data)
    matrix = np.frombuffer(buffer=buffer, dtype=np.int32).reshape((3, 3))

    if matrix[0, 0] > 0:
        return 0
    if matrix[0, 0] < 0:
        return 180
    if matrix[0, 1] < 0:
        return 90
    return 270


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


def _decode_frame_to_pil(video_path: str, frame_number: int, rotation_deg: int) -> PILImage.Image:
    """Decode a single frame from a video and return as PIL Image.

    Args:
        video_path: Path to the video file (local or S3).
        frame_number: Frame index to decode.
        rotation_deg: Rotation in degrees to apply.

    Returns:
        PIL Image of the decoded frame.

    Raises:
        ValueError: If the video cannot be opened or frame cannot be decoded.
    """
    fs, fs_path = fsspec.core.url_to_fs(url=video_path)
    video_file = fs.open(path=fs_path, mode="rb")
    try:
        try:
            video_container = container.open(file=video_file)
        except (OSError, FFmpegError) as e:
            raise ValueError(f"Could not open video {video_path}: {e}") from e

        try:
            video_stream = video_container.streams.video[0]
            for frame_count, frame in enumerate(video_container.decode(video_stream)):
                if frame_count == frame_number:
                    pil_image = frame.to_image().convert("RGB")
                    return _apply_rotation(pil_image, rotation_deg)
            raise ValueError(f"Frame {frame_number} not found in video {video_path}")
        except (OSError, FFmpegError) as e:
            raise ValueError(f"Could not decode frame {frame_number} from {video_path}: {e}") from e
        finally:
            video_container.close()
    finally:
        video_file.close()


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
