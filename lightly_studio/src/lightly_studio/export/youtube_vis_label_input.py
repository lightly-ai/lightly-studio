"""Labelformat track input adapters for YouTube-VIS export from Lightly Studio DB."""

from __future__ import annotations

from argparse import ArgumentParser
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
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
    ) -> None:
        self._session = session
        self._export_context = self._load_youtube_vis_videos_and_categories(
            session=session,
            samples=list(samples),
        )

    @staticmethod
    def add_cli_arguments(parser: ArgumentParser) -> None:
        # Add CLI arguments implementation is not needed for this class. We need it only
        # to satisfy the interface.
        raise NotImplementedError()

    def get_categories(self) -> Iterable[Category]:
        return self._export_context.categories

    def get_videos(self) -> Iterable[Video]:
        return self._export_context.videos

    @staticmethod
    def _load_youtube_vis_videos_and_categories(
        session: Session,
        samples: list[VideoSample],
    ) -> _YouTubeVISExportContext:
        """Load shared video metadata and categories for YouTube-VIS export."""
        if not samples:
            return _YouTubeVISExportContext(
                root_collection_id=None,
                videos=[],
                uuid_to_videos={},
                frame_to_video_id_and_index={},
                label_uuid_to_category={},
                categories=[],
            )

        root_collection_id = samples[0].dataset_id
        uuid_to_videos, frame_to_video_id_and_index = _build_videos_and_frame_map(
            session=session, samples=samples
        )
        label_uuid_to_category = _build_label_id_to_category(
            session=session, root_collection_id=root_collection_id
        )
        return _YouTubeVISExportContext(
            root_collection_id=root_collection_id,
            videos=list(uuid_to_videos.values()),
            uuid_to_videos=uuid_to_videos,
            frame_to_video_id_and_index=frame_to_video_id_and_index,
            label_uuid_to_category=label_uuid_to_category,
            categories=list(label_uuid_to_category.values()),
        )


class LightlyStudioYouTubeVISInstanceSegmentationTrackInput(
    _LightlyStudioYouTubeVISTrackInputBase, InstanceSegmentationTrackInput
):
    """Labelformat InstanceSegmentationTrackInput backed by Lightly Studio DB."""

    def __init__(
        self,
        session: Session,
        samples: Iterable[VideoSample],
    ) -> None:
        """Initialize the adapter and load segmentation tracks."""
        super().__init__(session=session, samples=samples)
        self._tracks = self._load_youtube_vis_segmentation_tracks_out(
            session=session,
        )

    def get_labels(self) -> Iterable[VideoInstanceSegmentationTrack]:
        """Yield video instance segmentation tracks for export."""
        yield from self._tracks

    def _load_youtube_vis_segmentation_tracks_out(
        self,
        session: Session,
    ) -> list[VideoInstanceSegmentationTrack]:
        """Load per-video instance segmentation tracks for YouTube-VIS export."""
        root_collection_id = self._export_context.root_collection_id
        if root_collection_id is None:
            return []

        tracks = object_track_resolver.get_all_by_root_collection_id(
            session=session, root_collection_id=root_collection_id
        )
        video_id_to_tracks: dict[UUID, list[SingleInstanceSegmentationTrack]] = defaultdict(list)
        for track in tracks:
            annotations = annotation_resolver.get_all_by_object_track_id(
                session=session,
                object_track_id=track.object_track_id,
                annotation_types=[AnnotationType.INSTANCE_SEGMENTATION],
            )
            if not annotations:
                continue

            annotations_by_video = _split_annotations_by_video(
                annotations,
                self._export_context.frame_to_video_id_and_index,
            )
            for video_id, video_annotations in annotations_by_video.items():
                track_obj = _build_segmentation_track_entry_from_annotations(
                    annotations=video_annotations,
                    video=self._export_context.uuid_to_videos[video_id],
                    frame_to_video_id_and_index=self._export_context.frame_to_video_id_and_index,
                    label_uuid_to_category=self._export_context.label_uuid_to_category,
                    object_track_id=track.object_track_number,
                )
                if track_obj is None:
                    continue
                video_id_to_tracks[video_id].append(track_obj)

        return _track_tuples_to_video_instance_segmentation(
            video_id_to_tracks, self._export_context.uuid_to_videos
        )


@dataclass(frozen=True)
class _YouTubeVISExportContext:
    root_collection_id: UUID | None
    videos: list[Video]
    uuid_to_videos: dict[UUID, Video]
    frame_to_video_id_and_index: dict[UUID, tuple[UUID, int]]
    label_uuid_to_category: dict[UUID, Category]
    categories: list[Category]


def _build_videos_and_frame_map(
    session: Session,
    samples: list[VideoSample],
) -> tuple[
    dict[UUID, Video],
    dict[UUID, tuple[UUID, int]],
]:
    """Build UUID -> Video mapping and frame_uuid -> (video uuid, frame_index) mapping.

    Frame id to video_id mapping is needed to associate annotations to the correct video and
    frame in the output.
    """
    videos: dict[UUID, Video] = {}
    frame_to_video_id_and_index: dict[UUID, tuple[UUID, int]] = {}
    frames_by_video_id: dict[UUID, list[VideoFrameTable]] = defaultdict(list)
    # Get all frames for the videos. The frames are sorted by video and frame number, so the index
    # in the list corresponds to the frame number.
    frames = video_frame_resolver.get_all_by_video_ids(
        session=session,
        video_ids=[sample.sample_id for sample in samples],
    )
    for frame in frames:
        frames_by_video_id[frame.parent_sample_id].append(frame)

    for yvis_id, sample in enumerate(samples, start=1):
        sample_frames = frames_by_video_id[sample.sample_id]
        length = len(sample_frames)
        videos[sample.sample_id] = Video(
            id=yvis_id,
            filename=Path(sample.file_name).name,
            width=int(sample.width),
            height=int(sample.height),
            number_of_frames=length,
        )

        for frame_index, frame in enumerate(sample_frames):
            frame_to_video_id_and_index[frame.sample_id] = (frame.parent_sample_id, frame_index)
    return videos, frame_to_video_id_and_index


def _split_annotations_by_video(
    annotations: list[AnnotationBaseTable],
    frame_to_video_id_and_index: dict[UUID, tuple[UUID, int]],
) -> dict[UUID, list[AnnotationBaseTable]]:
    """Group annotations by output video_id."""
    annotations_by_video: dict[UUID, list[AnnotationBaseTable]] = defaultdict(list)
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


def _build_segmentation_track_entry_from_annotations(
    annotations: list[AnnotationBaseTable],
    video: Video,
    frame_to_video_id_and_index: dict[UUID, tuple[UUID, int]],
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
        video_and_index = frame_to_video_id_and_index.get(ann.parent_sample_id)
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


def _build_label_id_to_category(session: Session, root_collection_id: UUID) -> dict[UUID, Category]:
    """Build a mapping from annotation label UUID to YouTube-VIS category."""
    labels = annotation_label_resolver.get_all_sorted_alphabetically(
        session=session,
        root_collection_id=root_collection_id,
    )
    return {
        label.annotation_label_id: Category(id=idx, name=label.annotation_label_name)
        for idx, label in enumerate(labels, start=1)
    }


def _track_tuples_to_video_instance_segmentation(
    video_id_to_tracks: dict[UUID, list[SingleInstanceSegmentationTrack]],
    video_by_uuid: dict[UUID, Video],
) -> list[VideoInstanceSegmentationTrack]:
    """Convert per-video SingleInstanceSegmentationTracks to VideoInstanceSegmentationTrack list."""
    tracks: list[VideoInstanceSegmentationTrack] = []
    for vid_id in sorted(video_id_to_tracks.keys()):
        video = video_by_uuid[vid_id]
        objects = video_id_to_tracks[vid_id]
        tracks.append(VideoInstanceSegmentationTrack(video=video, objects=objects))
    return tracks
