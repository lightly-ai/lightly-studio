"""Helper functions and classes for loading YouTube-VIS format annotations.

This module provides utilities for loading video annotations in YouTube-VIS format.
It's a temporary solution until YouTubeVIS is supported natively in labelformat.
"""

from __future__ import annotations

import json
from argparse import ArgumentParser
from pathlib import Path
from typing import Iterable
from uuid import UUID

import tqdm
from labelformat.model.bounding_box import BoundingBox, BoundingBoxFormat
from labelformat.model.category import Category
from labelformat.model.image import Image
from labelformat.model.object_detection import (
    ImageObjectDetection,
    ObjectDetectionInput,
    SingleObjectDetection,
)
from sqlmodel import Session

from lightly_studio.core import add_samples
from lightly_studio.models.collection import SampleType
from lightly_studio.resolvers import collection_resolver, video_resolver


class YouTubeVISObjectDetectionInput(ObjectDetectionInput):
    """Loads object detections from a modified YouTube-VIS format.

    The annotation json format is without modification, but the images are loaded as videos.

    This is a temporary hack until YouTubeVIS is supported natively in labelformat. The code
    is adapted from labelformat's COCOObjectDetectionInput.
    """

    @staticmethod
    def add_cli_arguments(parser: ArgumentParser) -> None:
        """Add CLI arguments for the input format.

        Args:
            parser: Argument parser to add arguments to

        Raises:
            NotImplementedError: This method is not implemented
        """
        raise NotImplementedError()

    def __init__(self, input_file: Path) -> None:
        """Initialize the YouTube-VIS object detection input.

        Args:
            input_file: Path to the YouTube-VIS format JSON file
        """
        with input_file.open() as file:
            self._data = json.load(file)

    def get_categories(self) -> Iterable[Category]:
        """Get all categories from the annotation file.

        Yields:
            Category objects from the annotation file
        """
        for category in self._data["categories"]:
            yield Category(
                id=category["id"],
                name=category["name"],
            )

    def get_images(self) -> Iterable[Image]:
        """Get all images (videos) from the annotation file.

        Yields:
            Image objects representing videos from the annotation file
        """
        for video in self._data["videos"]:
            yield Image(
                id=video["id"],
                # The video name is <video_folder>.mp4
                filename=Path(video["file_names"][0]).parent.name + ".mp4",
                width=int(video["width"]),
                height=int(video["height"]),
            )

    def get_labels(self) -> Iterable[ImageObjectDetection]:
        """Get all object detection labels from the annotation file.

        Yields:
            ImageObjectDetection objects containing frame-level detections
        """
        video_id_to_video = {video.id: video for video in self.get_images()}
        category_id_to_category = {category.id: category for category in self.get_categories()}

        for annotation_json in self._data["annotations"]:
            # Only extract bounding boxes, not segmentations. Every element in "bboxes"
            # corresponds to one frame in the video.
            frame_detections: list[SingleObjectDetection] = [
                SingleObjectDetection(
                    category=category_id_to_category[annotation_json["category_id"]],
                    box=BoundingBox.from_format(bbox=bbox, format=BoundingBoxFormat.XYWH),
                )
                if bbox is not None
                else SingleObjectDetection(
                    category=Category(-1, "no segmentation"),
                    box=BoundingBox.from_format(bbox=[0, 0, 0, 0], format=BoundingBoxFormat.XYWH),
                )
                for bbox in annotation_json["bboxes"]
            ]
            yield ImageObjectDetection(
                image=video_id_to_video[annotation_json["video_id"]],
                objects=frame_detections,
            )


def load_annotations(session: Session, collection_id: UUID, annotations_path: Path) -> None:
    """Loads video annotations from a YouTube-VIS format.

    Temporarily use internal add_samples API until labelformat supports videos natively.

    Args:
        session: Database session
        collection_id: ID of the collection to add annotations to
        annotations_path: Path to the YouTube-VIS format JSON file
    """
    print("Loading video annotations...")
    videos = video_resolver.get_all_by_collection_id_with_frames(
        session=session, collection_id=collection_id
    )
    video_name_to_video = {video.file_name: video for video in videos}
    yvis_input = YouTubeVISObjectDetectionInput(input_file=annotations_path)
    label_map = add_samples._create_label_map(  # noqa: SLF001
        session=session,
        dataset_id=collection_id,
        input_labels=yvis_input,
    )
    for label in tqdm.tqdm(yvis_input.get_labels(), desc="Adding annotations", unit=" objects"):
        video = video_name_to_video[label.image.filename]
        assert len(label.objects) == len(video.frames), (
            f"Number of frames in annotation ({len(label.objects)}) does not match "
            f"number of frames in video ({len(video.frames)}) for video {label.image.filename}"
        )
        # Use frame index as path to match frames with annotations
        path_to_id = {str(idx): frame.sample_id for idx, frame in enumerate(video.frames)}
        path_to_anno_data = {
            str(idx): ImageObjectDetection(
                image=label.image,
                objects=[obj],
            )
            if obj.category.id != -1
            else ImageObjectDetection(
                image=label.image,
                objects=[],
            )
            for idx, obj in enumerate(label.objects)
        }
        # Use frames collection as parent for annotations collection
        frames_collection_id = collection_resolver.get_or_create_child_collection(
            session=session, collection_id=collection_id, sample_type=SampleType.VIDEO_FRAME
        )
        add_samples._process_batch_annotations(  # noqa: SLF001
            session=session,
            created_path_to_id=path_to_id,
            path_to_anno_data=path_to_anno_data,
            dataset_id=frames_collection_id,
            label_map=label_map,
        )
