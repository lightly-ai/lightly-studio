"""Exports video-frame datasets from Lightly Studio into various formats."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import cast
from uuid import UUID

import fsspec
from av import FFmpegError, container
from av.video.frame import VideoFrame as AVVideoFrame
from labelformat.model.image import Image
from PIL import Image as PILImage
from sqlmodel import Session
from tqdm import tqdm

from lightly_studio.core.sample import Sample
from lightly_studio.core.video.video_frame_sample import VideoFrameSample
from lightly_studio.export.dataset_export import DatasetExport
from lightly_studio.type_definitions import PathLike

# Counter-rotation matching the DISPLAYMATRIX side-data convention used at ingest.
_PIL_ROTATION: dict[int, PILImage.Transpose] = {
    90: PILImage.Transpose.ROTATE_90,
    180: PILImage.Transpose.ROTATE_180,
    270: PILImage.Transpose.ROTATE_270,
}

_EXTENSION_TO_PIL_FORMAT = {
    ".jpg": "JPEG",
    ".jpeg": "JPEG",
    ".png": "PNG",
    ".webp": "WEBP",
    ".bmp": "BMP",
    ".tiff": "TIFF",
}


class VideoFrameDatasetExport(DatasetExport):
    """Provides methods to export a video-frame dataset or a subset of it.

    This class is typically not instantiated directly but returned by
    `VideoFrameDataset.export()`. It allows exporting data in various formats.
    """

    samples: Iterable[VideoFrameSample]

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
        super().__init__(
            session=session,
            dataset_id=dataset_id,
            samples=samples,
            sample_to_image=video_frame_to_image,
        )

    def to_image_files(self, output_dir: PathLike, extension: str = ".png") -> list[str]:
        """Export video frames as image files to a local or S3 directory.

        Decodes each frame from its parent video and writes it as an image file:
        ``{video_name}-{decode_index:0{zero_padding}}-{video_format}{extension}``.
        Frames from the same video are decoded in a single pass.

        Args:
            output_dir: The output directory path (can be local or s3://bucket/prefix).
            extension: Image file extension with leading dot (default: ".png").

        Returns:
            Paths of the created image files, under ``output_dir``, in decode order
            within each video (videos in first-seen sample order).

        Raises:
            ValueError: If the extension is unsupported, a video cannot be opened,
                a frame cannot be decoded, or a requested frame is missing.
        """
        extension_lower = extension.lower()
        if extension_lower not in _EXTENSION_TO_PIL_FORMAT:
            supported = ", ".join(sorted(_EXTENSION_TO_PIL_FORMAT))
            raise ValueError(
                f"Unsupported image extension '{extension}'. Supported extensions: {supported}"
            )

        output_dir_str = str(output_dir).rstrip("/\\").replace("\\", "/")
        fs, fs_path = fsspec.core.url_to_fs(url=output_dir_str)
        if not fs.exists(fs_path):
            fs.makedirs(fs_path, exist_ok=True)

        frames_by_video: dict[str, list[VideoFrameSample]] = {}
        for frame_sample in self.samples:
            video_path = frame_sample.parent_video.file_path_abs
            frames_by_video.setdefault(video_path, []).append(frame_sample)

        exported_paths: list[str] = []
        for video_path, frame_samples in frames_by_video.items():
            exported_paths.extend(
                _export_frames_from_video(
                    video_path=video_path,
                    frames=frame_samples,
                    fs=fs,
                    output_dir=output_dir_str,
                    extension=extension_lower,
                )
            )
        return exported_paths


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


def _export_frames_from_video(
    video_path: str,
    frames: Sequence[VideoFrameSample],
    fs: fsspec.AbstractFileSystem,
    output_dir: str,
    extension: str,
) -> list[str]:
    """Open a video once and export the requested frames as image files.

    Returns:
        Full paths of the written image files, in decode order.
    """
    if not frames:
        return []

    frames_by_number = {frame.frame_number: frame for frame in frames}
    max_frame_number = max(frames_by_number)
    # Pad from the source video's frame count (duration * fps).
    parent_video = frames[0].parent_video
    if parent_video.duration_s is not None and parent_video.fps > 0:
        total_frame_count = max(1, int(parent_video.duration_s * parent_video.fps))
    else:
        total_frame_count = max_frame_number
    zero_padding = len(str(total_frame_count))
    # TODO(Horatiu 08/2026): Using the filename will overwrite files if two videos with the same
    # name are in different directories. Add video sample id to the name.
    video_filename = Path(video_path).name
    pil_format = _EXTENSION_TO_PIL_FORMAT[extension]
    exported_paths: list[str] = []

    video_fs, video_fs_path = fsspec.core.url_to_fs(url=video_path)
    video_file = video_fs.open(path=video_fs_path, mode="rb")
    try:
        try:
            video_container = container.open(file=video_file)
        except (OSError, FFmpegError) as e:
            raise ValueError(f"Could not open video {video_path}: {e}") from e

        try:
            video_stream = video_container.streams.video[0]
            with tqdm(total=len(frames_by_number), desc="Exporting frames", unit=" frames") as pbar:
                for frame_count, frame in enumerate(video_container.decode(video_stream)):
                    if frame_count > max_frame_number:
                        break
                    if frame_count not in frames_by_number:
                        continue

                    frame_sample = frames_by_number.pop(frame_count)
                    pil_image = _frame_to_pil_image(
                        frame=frame, rotation_deg=frame_sample.rotation_deg
                    )
                    filename = _video_frame_filename(
                        video_filename=video_filename,
                        decode_index=frame_count,
                        zero_padding=zero_padding,
                        file_extension=extension,
                    )
                    out_path = f"{output_dir}/{filename}"
                    with fs.open(out_path, "wb") as f:
                        pil_image.save(f, format=pil_format)
                    exported_paths.append(out_path)
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
    return exported_paths


def _frame_to_pil_image(frame: AVVideoFrame, rotation_deg: int) -> PILImage.Image:
    """Convert a decoded AV frame to RGB PIL, applying counter-rotation if needed."""
    pil_image = cast(
        PILImage.Image,
        frame.to_image().convert("RGB"),  # type: ignore[no-untyped-call]
    )
    if rotation_deg == 0:
        return pil_image
    try:
        return pil_image.transpose(_PIL_ROTATION[rotation_deg])
    except KeyError as e:
        raise ValueError(f"Unsupported rotation_deg={rotation_deg}") from e


def _video_frame_filename(
    video_filename: str,
    decode_index: int,
    zero_padding: int,
    file_extension: str,
) -> str:
    """Build ``{video_name}-{decode_index}-{video_format}{extension}``."""
    video_path = Path(video_filename)
    video_name = video_path.with_suffix("")
    video_format = video_path.suffix[1:]
    if "-" in video_format:
        raise ValueError(f"Video format cannot contain '-' but found {video_format}")
    return f"{video_name}-{decode_index:0{zero_padding}}-{video_format}{file_extension}"
