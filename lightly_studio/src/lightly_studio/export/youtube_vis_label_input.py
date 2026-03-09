"""Labelformat track input adapters for YouTube-VIS export from Lightly Studio DB."""

from __future__ import annotations

from argparse import ArgumentParser
from collections import defaultdict
from collections.abc import Iterable
from pathlib import Path
from uuid import UUID

from labelformat.model.binary_mask_segmentation import BinaryMaskSegmentation
from labelformat.model.bounding_box import BoundingBox, BoundingBoxFormat
from labelformat.model.category import Category
from labelformat.model.instance_segmentation_track import (
    InstanceSegmentationTrackInput,
    SingleInstanceSegmentationTrack,
    VideoInstanceSegmentationTrack,
)
from labelformat.model.multipolygon import MultiPolygon
from labelformat.model.video import Video
from sqlmodel import Session

from lightly_studio.core.video.video_sample import VideoSample
from lightly_studio.models.annotation.annotation_base import AnnotationBaseTable, AnnotationType
from lightly_studio.models.video import VideoFrameTable
from lightly_studio.resolvers import (
    annotation_label_resolver,
    annotation_resolver,
    object_track_resolver,
    video_frame_resolver,
)


class _LightlyStudioYouTubeVISTrackInputBase:
    """Shared base for YouTube-VIS instance segmentation track input."""

    def __init__(
        self,
        session: Session,
        samples: Iterable[VideoSample],
        annotation_types: list[AnnotationType],
    ) -> None:
        self._session = session
        self._videos, self._categories, self._tracks = _load_youtube_vis_track_data(
            session=session,
            samples=list(samples),
            annotation_types=annotation_types,
        )

    @staticmethod
    def add_cli_arguments(parser: ArgumentParser) -> None:
        # Add CLI arguments implementation is not needed for this class. We need it only
        # to satisfy the interface.
        raise NotImplementedError()

    def get_categories(self) -> Iterable[Category]:
        return self._categories

    def get_videos(self) -> Iterable[Video]:
        return self._videos


class LightlyStudioYouTubeVISInstanceSegmentationTrackInput(
    _LightlyStudioYouTubeVISTrackInputBase, InstanceSegmentationTrackInput
):
    """Labelformat InstanceSegmentationTrackInput backed by Lightly Studio DB."""

    def get_labels(self) -> Iterable[VideoInstanceSegmentationTrack]:
        """Yield video instance segmentation tracks for export."""
        yield from self._tracks


def _build_videos_and_frame_map(
    session: Session,
    samples: list[VideoSample],
) -> tuple[
    list[Video],
    dict[int, Video],
    dict[UUID, tuple[int, int]],
]:
    """Build Video list, video_by_yvis_id, and frame_uuid -> (output_video_id, frame_index).

    Frame id to video_id mapping is needed to associate annotations to the correct video and
    frame in the output.
    """
    videos: list[Video] = []
    frame_to_video_id_and_index: dict[UUID, tuple[int, int]] = {}
    frames_by_video_id: dict[UUID, list[VideoFrameTable]] = defaultdict(list)
    frames = video_frame_resolver.get_all_by_video_ids(
        session=session,
        video_ids=[sample.sample_id for sample in samples],
    )
    for frame in frames:
        frames_by_video_id[frame.parent_sample_id].append(frame)

    for yvis_id, sample in enumerate(samples, start=1):
        sample_frames = frames_by_video_id[sample.sample_id]
        length = len(sample_frames)
        videos.append(
            Video(
                id=yvis_id,
                filename=Path(sample.file_name).name,
                width=int(sample.width),
                height=int(sample.height),
                number_of_frames=length,
            )
        )
        for frame_index, frame in enumerate(sample_frames):
            frame_to_video_id_and_index[frame.sample_id] = (yvis_id, frame_index)
    video_by_yvis_id = {v.id: v for v in videos}
    return videos, video_by_yvis_id, frame_to_video_id_and_index


def _get_video_id_and_frame_index(
    annotation: AnnotationBaseTable,
    frame_to_video_id_and_index: dict[UUID, tuple[int, int]],
) -> tuple[int, int] | None:
    """Return (output_video_id, frame_index) for the annotation's frame, or None."""
    return frame_to_video_id_and_index.get(annotation.parent_sample_id)


def _split_annotations_by_video(
    annotations: list[AnnotationBaseTable],
    frame_to_video_id_and_index: dict[UUID, tuple[int, int]],
) -> dict[int, list[AnnotationBaseTable]]:
    """Group annotations by output video_id."""
    annotations_by_video: dict[int, list[AnnotationBaseTable]] = defaultdict(list)
    for ann in annotations:
        video_and_index = frame_to_video_id_and_index.get(ann.parent_sample_id)
        if video_and_index is None:
            continue
        video_id, _ = video_and_index
        annotations_by_video[video_id].append(ann)
    return annotations_by_video


def _extract_segmentation_from_annotation(
    ann: AnnotationBaseTable,
    video: Video,
) -> BinaryMaskSegmentation | None:
    """Extract BinaryMaskSegmentation from annotation."""
    if ann.segmentation_details is not None:
        seg_details = ann.segmentation_details
        bbox = BoundingBox.from_format(
            format=BoundingBoxFormat.XYWH,
            bbox=[
                float(seg_details.x),
                float(seg_details.y),
                float(seg_details.width),
                float(seg_details.height),
            ],
        )

        if seg_details.segmentation_mask is not None:
            return BinaryMaskSegmentation.from_rle(
                rle_row_wise=list(seg_details.segmentation_mask),
                width=video.width,
                height=video.height,
                bounding_box=bbox,
            )
    return None


def _build_track_entry_from_annotations(
    annotations: list[AnnotationBaseTable],
    video: Video,
    frame_to_video_id_and_index: dict[UUID, tuple[int, int]],
    label_uuid_to_category: dict[UUID, Category],
    object_track_id: int | None = None,
) -> SingleInstanceSegmentationTrack | None:
    """Build a SingleInstanceSegmentationTrack for one track. Returns None if invalid."""
    # Initialize segmentations list with None for all frames. We will fill in the segmentations for
    # frames that have annotations, and keep None for frames without annotations.
    segmentations: list[MultiPolygon | BinaryMaskSegmentation | None] = [
        None
    ] * video.number_of_frames
    label_uuid: UUID | None = None

    for ann in annotations:
        video_and_index = _get_video_id_and_frame_index(ann, frame_to_video_id_and_index)
        if video_and_index is None:
            continue
        _, frame_index = video_and_index
        label_uuid = ann.annotation_label_id

        seg = _extract_segmentation_from_annotation(ann, video)
        if seg is None:
            continue
        segmentations[frame_index] = seg

    if label_uuid is None:
        return None

    category = label_uuid_to_category[label_uuid]
    return SingleInstanceSegmentationTrack(
        category=category,
        segmentations=segmentations,
        object_track_id=object_track_id,
    )


def _build_label_id_to_category(session: Session, dataset_id: UUID) -> dict[UUID, Category]:
    """Build a mapping from annotation label UUID to YouTube-VIS category."""
    labels = annotation_label_resolver.get_all_sorted_alphabetically(
        session=session,
        dataset_id=dataset_id,
    )
    return {
        label.annotation_label_id: Category(id=idx, name=label.annotation_label_name)
        for idx, label in enumerate(labels, start=1)
    }


def _track_tuples_to_video_instance_segmentation(
    video_id_to_tracks: dict[int, list[SingleInstanceSegmentationTrack]],
    video_by_yvis_id: dict[int, Video],
) -> list[VideoInstanceSegmentationTrack]:
    """Convert per-video SingleInstanceSegmentationTracks to VideoInstanceSegmentationTrack list."""
    tracks: list[VideoInstanceSegmentationTrack] = []
    for vid_id in sorted(video_id_to_tracks.keys()):
        video = video_by_yvis_id[vid_id]
        objects = video_id_to_tracks[vid_id]
        tracks.append(VideoInstanceSegmentationTrack(video=video, objects=objects))
    return tracks


def _load_youtube_vis_track_data(
    session: Session,
    samples: list[VideoSample],
    annotation_types: list[AnnotationType],
) -> tuple[list[Video], list[Category], list[VideoInstanceSegmentationTrack]]:
    """Load videos, categories, and per-video instance segmentation tracks from DB."""
    if not samples:
        return [], [], []

    dataset_id = samples[0].dataset_id
    # Create videos map for export and maps for associating annotations to videos and frames
    videos, video_by_yvis_id, frame_to_video_id_and_index = _build_videos_and_frame_map(
        session=session, samples=samples
    )
    # Build label_uuid -> YouTube-VIS category map
    label_uuid_to_category = _build_label_id_to_category(session=session, dataset_id=dataset_id)

    tracks = object_track_resolver.get_all_by_dataset_id(session=session, dataset_id=dataset_id)
    video_id_to_tracks: dict[int, list[SingleInstanceSegmentationTrack]] = defaultdict(list)
    for track in tracks:
        annotations = annotation_resolver.get_all_by_object_track_id(
            session=session,
            object_track_id=track.object_track_id,
            annotation_types=annotation_types,
        )
        if not annotations:
            continue

        # There can be annotations from different videos in the same track, so we need to split
        # them by video
        annotations_by_video = _split_annotations_by_video(annotations, frame_to_video_id_and_index)
        for video_id, video_annotations in annotations_by_video.items():
            track_obj = _build_track_entry_from_annotations(
                annotations=video_annotations,
                video=video_by_yvis_id[video_id],
                frame_to_video_id_and_index=frame_to_video_id_and_index,
                label_uuid_to_category=label_uuid_to_category,
                object_track_id=track.object_track_number,
            )
            if track_obj is None:
                continue
            video_id_to_tracks[video_id].append(track_obj)

    tracks_out = _track_tuples_to_video_instance_segmentation(video_id_to_tracks, video_by_yvis_id)
    categories = list(label_uuid_to_category.values())
    return videos, categories, tracks_out
