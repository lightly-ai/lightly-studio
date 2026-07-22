"""Functions to add videos to a dataset in the database."""

from __future__ import annotations

import itertools
import logging
import math
import os
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import cast
from uuid import UUID

import av
import fsspec
import numpy as np
from av import FFmpegError, container
from av.codec.context import ThreadType
from av.container import InputContainer
from av.video.frame import VideoFrame as AVVideoFrame
from av.video.stream import VideoStream
from labelformat.model.instance_segmentation_track import (
    InstanceSegmentationTrackInput,
    SingleInstanceSegmentationTrack,
    VideoInstanceSegmentationTrack,
)
from labelformat.model.object_detection_track import (
    ObjectDetectionTrackInput,
    SingleObjectDetectionTrack,
    VideoObjectDetectionTrack,
)
from PIL import Image
from sqlmodel import Session
from tqdm import tqdm

from lightly_studio.core import labelformat_helpers
from lightly_studio.core.file_outcome_report import (
    AlreadyPresentInputFileError,
    BrokenInputFileError,
    FileOutcomeReport,
    MissingInputFileError,
)
from lightly_studio.dataset.embedding_manager import EmbeddingManagerProvider
from lightly_studio.models.annotation.annotation_base import (
    AnnotationCreate,
)
from lightly_studio.models.annotation.object_track import ObjectTrackCreate
from lightly_studio.models.collection import SampleType
from lightly_studio.models.video import VideoCreate, VideoFrameCreate
from lightly_studio.resolvers import (
    annotation_resolver,
    collection_resolver,
    object_track_resolver,
    sample_resolver,
    video_frame_resolver,
    video_resolver,
)

logger = logging.getLogger(__name__)

DEFAULT_VIDEO_CHANNEL = 0
# Number of samples to process in a single batch
SAMPLE_BATCH_SIZE = 128

# Video file extensions
# These are commonly supported by PyAV/FFmpeg.
VIDEO_EXTENSIONS = {
    ".mp4",
    ".mov",
    ".avi",
    ".mkv",
    ".webm",
    ".flv",
    ".wmv",
}


@dataclass
class FrameExtractionContext:
    """Lightweight container for the metadata needed during frame extraction."""

    session: Session
    collection_id: UUID
    video_sample_id: UUID
    embed_frames: bool = False
    embedding_model_id: UUID | None = None


@dataclass
class VideoLoadContext:
    """Loop-invariant settings shared while loading a batch of videos into a collection."""

    session: Session
    collection_id: UUID
    video_frames_collection_id: UUID
    video_channel: int
    num_decode_threads: int | None
    target_fps: float | None
    embed_frames: bool
    embedding_model_id: UUID | None


def load_into_collection_from_paths(  # noqa: PLR0913
    session: Session,
    collection_id: UUID,
    video_paths: Iterable[str],
    video_channel: int = DEFAULT_VIDEO_CHANNEL,
    num_decode_threads: int | None = None,
    show_progress: bool = True,
    target_fps: float | None = None,
    embed_frames: bool = False,
) -> tuple[list[UUID], list[UUID]]:
    """Load video samples from file paths into the dataset using PyAV.

    Args:
        session: The database session.
        collection_id: The ID of the collection to load video samples into. It should have
        sample_type == SampleType.VIDEO.
        video_paths: An iterable of file paths to the videos to load.
        video_channel: The video channel from which frames are loaded.
        num_decode_threads: Optional override for the number of FFmpeg decode threads.
            If omitted, the available CPU cores - 1 (max 16) are used.
        show_progress: Whether to display a progress bar and final summary of loading results.
        target_fps: Optional target frame rate for subsampling. When set below the source
            frame rate, only selected frames are kept. frame_number values remain
            original. Must be greater than 0.
        embed_frames: If True, generate image embeddings for extracted video frames during
            decoding. Requires an image-compatible embedding model.

    Returns:
        A tuple containing:
            - List of UUIDs of the created video samples
            - List of UUIDs of the created video frame samples
    """
    if target_fps is not None and target_fps <= 0:
        raise ValueError(f"target_fps must be greater than 0, got {target_fps}.")

    created_video_sample_ids: list[UUID] = []
    created_video_frame_sample_ids: list[UUID] = []
    video_paths_list = list(video_paths)
    # The set starts with paths already in the database and grows with paths seen in this
    # call, so both already-present and in-run duplicate paths are skipped.
    _, existing_paths = sample_resolver.filter_new_paths(
        session=session,
        collection_id=collection_id,
        file_paths_abs=video_paths_list,
    )
    seen_or_existing_paths = set(existing_paths)
    report = FileOutcomeReport()
    # Get the video frames collection ID
    video_frames_collection_id = collection_resolver.get_or_create_child_collection(
        session=session, collection_id=collection_id, sample_type=SampleType.VIDEO_FRAME
    )
    embedding_model_id: UUID | None = None
    if embed_frames:
        embedding_manager = EmbeddingManagerProvider.get_embedding_manager()
        embedding_model_id = embedding_manager.load_or_get_default_model(
            session=session,
            collection_id=video_frames_collection_id,
        )
        if embedding_model_id is None:
            logger.warning("No embedding model loaded. Skipping frame embedding generation.")
    effective_embed_frames = embed_frames and embedding_model_id is not None

    load_context = VideoLoadContext(
        session=session,
        collection_id=collection_id,
        video_frames_collection_id=video_frames_collection_id,
        video_channel=video_channel,
        num_decode_threads=num_decode_threads,
        target_fps=target_fps,
        embed_frames=effective_embed_frames,
        embedding_model_id=embedding_model_id,
    )

    # TODO(Malte, 07/2026): Parallelize video indexing across videos with
    # parallelize.thread_imap_lazy (one task per whole video, never split a video;
    # workers and prefetch stay bounded) to overlap remote reads. Decode single-threaded
    # per video and keep DB writes and embedding on a single thread, as neither the
    # session nor the model is thread-safe.
    for video_path in tqdm(
        video_paths_list,
        desc="Loading frames from videos",
        unit=" video",
        disable=not show_progress,
    ):
        with report.track(path=video_path):
            video_sample_id, frame_sample_ids = _load_single_video(
                context=load_context,
                video_path=video_path,
                seen_or_existing_paths=seen_or_existing_paths,
            )
            created_video_sample_ids.append(video_sample_id)
            created_video_frame_sample_ids.extend(frame_sample_ids)

    report.log_summary()
    report.raise_if_all_failed()

    return created_video_sample_ids, created_video_frame_sample_ids


def _load_single_video(
    context: VideoLoadContext,
    video_path: str,
    seen_or_existing_paths: set[str],
) -> tuple[UUID, list[UUID]]:
    """Load one video and its frames, returning the created video and frame sample IDs.

    Raises a ``FileOutcomeReport`` error (already-present, missing, or broken) when the
    video cannot be loaded, so the caller's ``report.track`` block can record the outcome.
    """
    # Skip paths already in the database or already seen in this call.
    if video_path in seen_or_existing_paths:
        raise AlreadyPresentInputFileError()
    seen_or_existing_paths.add(video_path)

    # Detect a missing path proactively: FileNotFoundError is unreliable across
    # fsspec backends and is a subclass of OSError, which we treat as broken.
    fs, fs_path = fsspec.core.url_to_fs(url=video_path)
    if not fs.exists(fs_path):
        raise MissingInputFileError()

    video_file = fs.open(path=fs_path, mode="rb")
    try:
        # Open the container first: if this fails there is nothing to close, so the
        # failed open is translated into a broken-file signal at this I/O boundary.
        try:
            # Open video container for reading (returns InputContainer)
            video_container = container.open(file=video_file)
        except (OSError, FFmpegError) as e:
            raise BrokenInputFileError() from e

        try:
            # Translate a failed header read into a broken-file signal; any other
            # exception propagates rather than being recorded.
            try:
                video_stream = video_container.streams.video[context.video_channel]

                # Get video metadata
                framerate = float(video_stream.average_rate) or 0.0
                video_width = video_stream.width or 0
                video_height = video_stream.height or 0
                if video_stream.duration and video_stream.time_base:
                    video_duration = float(video_stream.duration * video_stream.time_base)
                else:
                    video_duration = None
            except (OSError, IndexError, FFmpegError) as e:
                raise BrokenInputFileError() from e

            # Create video sample
            video_sample_ids = video_resolver.create_many(
                session=context.session,
                collection_id=context.collection_id,
                samples=[
                    VideoCreate(
                        file_path_abs=video_path,
                        width=video_width,
                        height=video_height,
                        duration_s=video_duration,
                        fps=framerate,
                        file_name=Path(video_path).name,
                    )
                ],
            )

            if len(video_sample_ids) != 1:
                raise RuntimeError(f"There was an error adding {video_path} to the dataset.")

            # Create video frame samples by parsing all frames
            extraction_context = FrameExtractionContext(
                session=context.session,
                collection_id=context.video_frames_collection_id,
                video_sample_id=video_sample_ids[0],
                embed_frames=context.embed_frames,
                embedding_model_id=context.embedding_model_id,
            )
            try:
                frame_sample_ids = _create_video_frame_samples(
                    context=extraction_context,
                    video_container=video_container,
                    video_channel=context.video_channel,
                    num_decode_threads=context.num_decode_threads,
                    target_fps=context.target_fps,
                )
            except (OSError, FFmpegError) as e:
                # A frame that fails to decode mid-stream leaves the already-committed video row
                # and any flushed frame batches behind. Remove them so a broken video leaves no
                # rows, then translate the failure into a broken-file signal so the caller's
                # report.track records it and the run continues instead of aborting.
                video_resolver.delete_with_frames(
                    session=context.session, video_sample_id=video_sample_ids[0]
                )
                raise BrokenInputFileError() from e

            return video_sample_ids[0], frame_sample_ids
        finally:
            # Always release the native FFmpeg container once it has been opened, even
            # if metadata reads, sample creation, or frame extraction raised.
            video_container.close()
    finally:
        video_file.close()


def load_video_annotations_from_labelformat(  # noqa: PLR0913
    session: Session,
    collection_id: UUID,
    dataset_id: UUID,
    video_paths: Iterable[str],
    input_labels: ObjectDetectionTrackInput | InstanceSegmentationTrackInput,
    input_labels_paths_root: Path | str,
    limit: int | None = None,
    embed_frames: bool = False,
) -> tuple[list[UUID], list[UUID]]:
    """Load video frame annotations from a labelformat input into the dataset.

    Important: due to the missing file extension for the video file names in YouTube-VIS,
    this method assumes that "full path w/o suffix" of the videos in the dataset are unique!
    File handling per video file name specified in YouTube-VIS:
    - A) The file name contains the file extension: (input_labels_paths_root/file_name)
    - B) The file name does not contains the file extension:
        A file with matching "path w/o suffix" is used

    Args:
        session: The database session.
        collection_id: The ID of the video collection to load annotations into.
        dataset_id: The ID of the dataset this collection belongs to.
        video_paths: An iterable of file paths to the videos to load.
            Note: This is used for file names from input_labels, that don't have a file extension.
        input_labels: The labelformat input containing video annotations.
        input_labels_paths_root: The root path for the paths in input_labels.
        limit: Maximum number of samples to load. By default, all samples are loaded.
            Annotations of videos beyond the limit are skipped.
        embed_frames: If True, generate image embeddings for extracted video frames during
            decoding. Requires an image-compatible embedding model.

    Returns:
        A tuple containing:
            - List of UUIDs of the created video samples
            - List of UUIDs of the created video frame samples
    """
    # TODO (Jonas, 2/2026): Add support for cloud paths.
    root_path = Path(input_labels_paths_root).absolute()
    video_paths_labelformat = _resolve_video_paths_from_labelformat(
        input_labels=input_labels, root_path=root_path, video_paths=video_paths, limit=limit
    )

    created_sample_ids, created_video_frame_sample_ids = load_into_collection_from_paths(
        session=session,
        collection_id=collection_id,
        video_paths=video_paths_labelformat,
        embed_frames=embed_frames,
    )

    # In YouTube-VIS, the file extension is typically missing. Hence we fallback to the path
    # without suffix. This method is assuming that we have no files with same path without suffix in
    # the dataset. E.g. /root/my_video.mp4 and /root/my_video.mov will not be present in the dataset
    # at the same time.
    # Construct the mapping from path without suffix to sample id.
    video_path_without_suffix_to_sample_id: dict[str, UUID] = {}
    for sample_id in created_sample_ids:
        video = video_resolver.get_by_id(session=session, sample_id=sample_id)
        if video is not None:
            video_path_without_suffix = str(Path(video.file_path_abs).absolute().with_suffix(""))
            video_path_without_suffix_to_sample_id[video_path_without_suffix] = sample_id

    label_map = labelformat_helpers.create_label_map(
        session=session,
        root_collection_id=collection_id,
        input_labels=input_labels,
    )

    for video_annotation_raw in tqdm(
        input_labels.get_labels(), desc="Adding video annotations", unit=" videos"
    ):
        video_annotation: VideoInstanceSegmentationTrack | VideoObjectDetectionTrack = (
            video_annotation_raw  # type: ignore[assignment]
        )
        video_annotation_filename = Path(video_annotation.video.filename)
        video_path_without_suffix = str((root_path / video_annotation_filename).with_suffix(""))
        video_sample_id = video_path_without_suffix_to_sample_id.get(video_path_without_suffix)
        if video_sample_id is None:
            # The video was not created: it is beyond the limit, or the per-run report
            # already recorded it as missing/broken/already-present. Skip its annotations
            # rather than crashing the run, in line with tolerate-don't-crash handling.
            logger.warning(
                f"Skipping annotations for video '{video_annotation_filename}': "
                "no matching loaded video found."
            )
            continue

        video_with_frames = video_resolver.get_by_id(session=session, sample_id=video_sample_id)
        if video_with_frames is None:
            raise ValueError(
                f"No matching video ({video_annotation_filename}) for annotations found"
            )

        frames = video_with_frames.frames
        if video_annotation.video.number_of_frames != len(frames):
            raise ValueError(
                f"Number of frames in annotation ({video_annotation.video.number_of_frames}) "
                f"does not match number of frames in video ({len(frames)}) "
                f"for video {video_with_frames.file_name}"
            )
        frame_number_to_id = {frame.frame_number: frame.sample_id for frame in frames}

        object_track_map = _create_object_tracks(
            session=session,
            video_annotation=video_annotation,
            dataset_id=dataset_id,
        )

        if isinstance(video_annotation, VideoInstanceSegmentationTrack):
            annotations_to_create = _process_video_annotations_segmentation_mask(
                frame_number_to_id=frame_number_to_id,
                video_annotation=video_annotation,
                label_map=label_map,
                object_track_map=object_track_map,
            )
        elif isinstance(video_annotation, VideoObjectDetectionTrack):
            annotations_to_create = _process_video_annotations_object_detection(
                frame_number_to_id=frame_number_to_id,
                video_annotation=video_annotation,
                label_map=label_map,
                object_track_map=object_track_map,
            )
        else:
            raise ValueError(f"Unsupported annotation type: {type(video_annotation)}")
        # Use frames collection as parent for annotations collection
        frames_collection_id = collection_resolver.get_or_create_child_collection(
            session=session, collection_id=collection_id, sample_type=SampleType.VIDEO_FRAME
        )
        annotation_resolver.create_many(
            session=session,
            parent_collection_id=frames_collection_id,
            annotations=annotations_to_create,
        )

    return created_sample_ids, created_video_frame_sample_ids


def _should_keep_frame(decoded_index: int, target_fps: float | None, original_fps: float) -> bool:
    """Decide whether to keep a frame when subsampling to a lower frame rate.

    Frames are mapped to buckets of size ``original_fps / target_fps`` and the first
    frame of each bucket is kept, which yields frames spaced approximately at
    ``target_fps``. All frames are kept when no target fps is given, when the target
    is not lower than the source rate, or when the source rate is unknown.

    Args:
        decoded_index: The original index of the frame in the source video.
        target_fps: The desired target frame rate, or None to keep all frames.
        original_fps: The source video frame rate (0 if unknown).

    Returns:
        True if the frame should be persisted.
    """
    if target_fps is None or original_fps <= 0.0 or target_fps >= original_fps:
        return True
    if decoded_index == 0:
        return True
    return math.floor(decoded_index * target_fps / original_fps) != math.floor(
        (decoded_index - 1) * target_fps / original_fps
    )


def _create_video_frame_samples(
    context: FrameExtractionContext,
    video_container: InputContainer,
    video_channel: int,
    num_decode_threads: int | None = None,
    target_fps: float | None = None,
) -> list[UUID]:
    """Create video frame samples for a video by parsing all frames.

    This function decodes all frames to extract metadata. When frame embedding is enabled,
    embeddings are generated from the decoded frames in the same pass.

    Args:
        context: Frame extraction context (session, dataset and parent video).
        video_container: The PyAV container with the opened video.
        video_channel: The video channel from which frames are loaded.
        num_decode_threads: Optional override for FFmpeg decode thread count.
        target_fps: Optional target frame rate for subsampling. If set and lower than the
            source frame rate, only a subset of frames is persisted; kept frames retain
            their original frame_number. If omitted, all frames are persisted.

    Returns:
        A list of UUIDs of the created video frame samples.
    """
    created_sample_ids: list[UUID] = []
    samples_to_create: list[VideoFrameCreate] = []
    pil_frames: list[Image.Image] = []
    video_stream = video_container.streams.video[video_channel]
    _configure_stream_threading(video_stream=video_stream, num_decode_threads=num_decode_threads)

    # Get time base for converting PTS to seconds
    time_base = video_stream.time_base if video_stream.time_base else None
    original_fps = float(video_stream.average_rate) if video_stream.average_rate else 0.0

    # Decode all frames, persisting only the subset selected by the target fps.
    for decoded_index, frame in enumerate(video_container.decode(video_stream)):
        if not _should_keep_frame(
            decoded_index=decoded_index, target_fps=target_fps, original_fps=original_fps
        ):
            continue

        # Get the presentation timestamp in seconds from the frame
        # Convert frame.pts from time base units to seconds
        if frame.pts is not None and time_base is not None:
            frame_timestamp_s = float(frame.pts * time_base)
        else:
            # Fallback to frame.time if pts or time_base is not available
            frame_timestamp_s = frame.time if frame.time is not None else -1.0

        sample = VideoFrameCreate(
            frame_number=decoded_index,
            frame_timestamp_s=frame_timestamp_s,
            frame_timestamp_pts=frame.pts if frame.pts is not None else -1,
            parent_sample_id=context.video_sample_id,
            rotation_deg=_get_frame_rotation_deg(frame=frame),
        )
        samples_to_create.append(sample)
        if context.embed_frames:
            pil_frames.append(frame.to_image().convert("RGB"))  # type: ignore[no-untyped-call]

        if len(samples_to_create) >= SAMPLE_BATCH_SIZE:
            created_sample_ids.extend(
                _flush_frame_batch(
                    context=context,
                    samples_to_create=samples_to_create,
                    pil_frames=pil_frames,
                )
            )
            samples_to_create = []
            pil_frames = []

    if samples_to_create:
        created_sample_ids.extend(
            _flush_frame_batch(
                context=context,
                samples_to_create=samples_to_create,
                pil_frames=pil_frames,
            )
        )

    return created_sample_ids


def _flush_frame_batch(
    context: FrameExtractionContext,
    samples_to_create: list[VideoFrameCreate],
    pil_frames: list[Image.Image],
) -> list[UUID]:
    """Persist a batch of frame samples and optionally embed them."""
    created_sample_ids = video_frame_resolver.create_many(
        session=context.session,
        samples=samples_to_create,
        collection_id=context.collection_id,
    )

    if context.embed_frames and context.embedding_model_id is not None and pil_frames:
        embedding_manager = EmbeddingManagerProvider.get_embedding_manager()
        embedding_manager.embed_and_store_pil_images(
            session=context.session,
            embedding_model_id=context.embedding_model_id,
            sample_ids=created_sample_ids,
            images=pil_frames,
            show_progress=False,
        )

    return created_sample_ids


def _configure_stream_threading(video_stream: VideoStream, num_decode_threads: int | None) -> None:
    """Configure codec-level threading for faster decode when available."""
    codec_context = getattr(video_stream, "codec_context", None)
    if codec_context is None:
        return

    if num_decode_threads is None:
        cpu_count = os.cpu_count() or 1
        # Use available cores - 1 but at least 1. Cap to prevent runaway usage.
        num_decode_threads = max(1, min(cpu_count - 1 or 1, 16))

    try:
        codec_context.thread_type = ThreadType.AUTO
        codec_context.thread_count = num_decode_threads
    except av.FFmpegError:
        # Some codecs do not support threading—ignore silently.
        logger.warning(
            "Could not set up multithreading to decode videos, will use a single thread."
        )


def _get_frame_rotation_deg(frame: AVVideoFrame) -> int:
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

    # The top left 2x2 sub-matrix has four possible configurations. The rotation can be
    # determined from the first two values.
    #
    #  0        90       180      270
    #  x  0     0 -x    -x  0     0  x
    #  0  x     x  0     0 -x    -x  0
    if matrix[0, 0] > 0:
        return 0
    if matrix[0, 0] < 0:
        return 180
    if matrix[0, 1] < 0:
        return 90
    return 270


def _resolve_video_paths_from_labelformat(
    input_labels: ObjectDetectionTrackInput | InstanceSegmentationTrackInput,
    root_path: Path,
    video_paths: Iterable[str],
    limit: int | None = None,
) -> list[str]:
    """Collecting the available video paths for the videos referenced in the input_labels.

    If the full video name is provided in the input (e.g. movie.mp4), the path is used directly.
    If only the stem is provided, an available video with the stem in the video_paths is used.

    Args:
        input_labels: Input containing the required video file paths.
        root_path: The paths for the videos in input_labels are relative to this one.
        video_paths: An iterable of file paths to the videos to load.
        limit: Maximum number of videos to resolve. By default, all videos are resolved.

    Return:
        list of resolved video file paths
    """
    # Construct mappings between path without suffix and actual file path.
    video_path_without_suffix_to_path: dict[str, str] = {}
    for video_file in video_paths:
        file_path_without_suffix = str(Path(video_file).absolute().with_suffix(""))
        if file_path_without_suffix in video_path_without_suffix_to_path:
            raise ValueError(
                f"Duplicate video path '{file_path_without_suffix}' found: "
                f"'{video_path_without_suffix_to_path[file_path_without_suffix]}' and "
                f"'{video_file}'."
            )
        video_path_without_suffix_to_path[file_path_without_suffix] = video_file

    # Construct the list of resolved video paths.
    video_paths = []
    for video_annotation in itertools.islice(input_labels.get_videos(), limit):
        filename = Path(video_annotation.filename)
        resolved_path: str | None
        if filename.suffix:
            resolved_path = str(root_path / filename)
        else:
            annotation_path_without_suffix = str((root_path / filename).with_suffix(""))
            resolved_path = video_path_without_suffix_to_path.get(annotation_path_without_suffix)
        if resolved_path is None:
            raise FileNotFoundError(f"No video file found for '{filename}'.")
        video_paths.append(resolved_path)
    return video_paths


def _create_object_tracks(
    session: Session,
    video_annotation: VideoInstanceSegmentationTrack | VideoObjectDetectionTrack,
    dataset_id: UUID,
) -> dict[int, UUID]:
    """Create an ObjectTrackTable entry for each tracked object in the video.

    Args:
        session: Database session.
        video_annotation: The labelformat video annotation containing objects.
        dataset_id: UUID of the dataset.

    Returns:
        Mapping from object index (position in video_annotation.objects) to the
        UUID of the created object track. Objects without track ID in the annotation are not
        included in the mapping.
    """
    object_track_map: dict[int, UUID] = {}
    tracks_to_create: list[ObjectTrackCreate] = []
    object_indices: list[int] = []
    for obj_idx, obj_raw in enumerate(video_annotation.objects):
        obj: SingleInstanceSegmentationTrack | SingleObjectDetectionTrack = obj_raw  # type: ignore[assignment]
        object_track_number = obj.object_track_id
        if object_track_number is None:
            # Skip objects without track ID and do not create tracks for them
            continue

        tracks_to_create.append(
            ObjectTrackCreate(
                object_track_number=object_track_number,
                dataset_id=dataset_id,
            )
        )
        object_indices.append(obj_idx)

        if len(tracks_to_create) >= SAMPLE_BATCH_SIZE:
            created_track_ids = object_track_resolver.create_many(
                session=session, tracks=tracks_to_create
            )
            if len(created_track_ids) != len(object_indices):
                raise RuntimeError(
                    f"Expected {len(object_indices)} created object tracks but got "
                    f"{len(created_track_ids)}."
                )
            for idx, track_id in zip(object_indices, created_track_ids):
                object_track_map[idx] = track_id
            tracks_to_create = []
            object_indices = []

    if tracks_to_create:
        created_track_ids = object_track_resolver.create_many(
            session=session, tracks=tracks_to_create
        )
        if len(created_track_ids) != len(object_indices):
            raise RuntimeError(
                f"Expected {len(object_indices)} created object tracks but got "
                f"{len(created_track_ids)}."
            )
        for idx, track_id in zip(object_indices, created_track_ids):
            object_track_map[idx] = track_id

    return object_track_map


def _process_video_annotations_segmentation_mask(
    frame_number_to_id: dict[int, UUID],
    video_annotation: VideoInstanceSegmentationTrack,
    label_map: dict[int, UUID],
    object_track_map: dict[int, UUID],
) -> list[AnnotationCreate]:
    """Process segmentation mask annotations for a single video."""
    annotations = []
    for frame_number, frame_id in frame_number_to_id.items():
        for obj_idx, obj in enumerate(video_annotation.objects):
            segmentation = obj.segmentations[frame_number]
            if segmentation is not None:
                annotation = labelformat_helpers.get_segmentation_annotation_create(
                    parent_sample_id=frame_id,
                    annotation_label_id=label_map[obj.category.id],
                    segmentation=segmentation,
                    object_track_id=object_track_map.get(obj_idx),
                )
                annotations.append(annotation)
    return annotations


def _process_video_annotations_object_detection(
    frame_number_to_id: dict[int, UUID],
    video_annotation: VideoObjectDetectionTrack,
    label_map: dict[int, UUID],
    object_track_map: dict[int, UUID],
) -> list[AnnotationCreate]:
    """Process object detection annotations for a single video."""
    annotations = []
    for frame_number, frame_id in frame_number_to_id.items():
        for obj_idx, obj in enumerate(video_annotation.objects):
            box = obj.boxes[frame_number]
            if box is not None:
                annotation = labelformat_helpers.get_object_detection_annotation_create(
                    parent_sample_id=frame_id,
                    annotation_label_id=label_map[obj.category.id],
                    box=box,
                    object_track_id=object_track_map.get(obj_idx),
                )
                annotations.append(annotation)
    return annotations
