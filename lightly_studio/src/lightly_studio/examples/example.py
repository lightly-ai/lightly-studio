"""Example of how to load videos from path with the dataset class."""

from __future__ import annotations

import json
from argparse import ArgumentParser
from pathlib import Path
from typing import Iterable, TypedDict

from environs import Env
from labelformat.model.binary_mask_segmentation import (
    BinaryMaskSegmentation,
)
from labelformat.model.bounding_box import BoundingBox, BoundingBoxFormat
from labelformat.model.category import Category
from labelformat.model.image import Image
from labelformat.model.instance_segmentation import (
    ImageInstanceSegmentation,
    InstanceSegmentationInput,
    SingleInstanceSegmentation,
)
from labelformat.model.multipolygon import MultiPolygon
from labelformat.model.bounding_box import BoundingBox, BoundingBoxFormat
from labelformat.model.category import Category
from labelformat.model.image import Image
from labelformat.model.instance_segmentation import (
    ImageInstanceSegmentation,
    InstanceSegmentationInput,
    InstanceSegmentationOutput,
    SingleInstanceSegmentation,
)
from labelformat.model.multipolygon import MultiPolygon
from labelformat.model.object_detection import (
    ImageObjectDetection,
    ObjectDetectionInput,
    ObjectDetectionOutput,
    SingleObjectDetection,
)
from labelformat.types import JsonDict, ParseError

import lightly_studio as ls
from lightly_studio import db_manager
from lightly_studio.core.add_samples import _process_batch_annotations, _create_label_map
from lightly_studio.resolvers import video_resolver


class YouTubeVISInput(InstanceSegmentationInput):
    """Loads instance segmentation annotations in YouTube-VIS format.

    Until YouTubeVIS is supported natively in labelformat, we TODO
    """

    @staticmethod
    def add_cli_arguments(parser: ArgumentParser) -> None:
        raise NotImplementedError()

    def __init__(self, input_file: Path) -> None:
        with input_file.open() as file:
            self._data = json.load(file)

    def get_categories(self) -> Iterable[Category]:
        for category in self._data["categories"]:
            yield Category(
                id=category["id"],
                name=category["name"],
            )

    def get_images(self) -> Iterable[Image]:
        for video in self._data["videos"]:
            yield Image(
                id=video["id"],
                # TODO
                filename=Path(video["file_names"][0]).parent.name + ".mp4",
                width=int(video["width"]),
                height=int(video["height"]),
            )

    def get_labels(self) -> Iterable[ImageInstanceSegmentation]:
        video_id_to_video = {video.id: video for video in self.get_images()}
        category_id_to_category = {category.id: category for category in self.get_categories()}

        for annotation_json in self._data["annotations"]:
            video_id = annotation_json["video_id"]
            frame_segs: list[SingleInstanceSegmentation] = []

            for seg, bbox in zip(annotation_json["segmentations"], annotation_json["bboxes"]):
                if seg is not None:
                    frame_segs.append(
                        SingleInstanceSegmentation(
                            category=category_id_to_category[annotation_json["category_id"]],
                            segmentation=_coco_segmentation_to_binary_mask_rle(
                                segmentation=seg, bbox=bbox
                            ),
                        )
                    )
                else:
                    frame_segs.append(
                        SingleInstanceSegmentation(
                            category=Category(-1, "no segmentation"),
                            segmentation=MultiPolygon([]),
                        )
                    )
            yield ImageInstanceSegmentation(
                image=video_id_to_video[video_id],
                objects=frame_segs,
            )


class YouTubeVODInput(ObjectDetectionInput):
    """Loads instance segmentation annotations in YouTube-VIS format.

    Until YouTubeVIS is supported natively in labelformat, we TODO
    """
    @staticmethod
    def add_cli_arguments(parser: ArgumentParser) -> None:
        raise NotImplementedError()

    def __init__(self, input_file: Path) -> None:
        with input_file.open() as file:
            self._data = json.load(file)

    def get_categories(self) -> Iterable[Category]:
        for category in self._data["categories"]:
            yield Category(
                id=category["id"],
                name=category["name"],
            )

    def get_images(self) -> Iterable[Image]:
        for video in self._data["videos"]:
            yield Image(
                id=video["id"],
                # TODO
                filename=Path(video["file_names"][0]).parent.name + ".mp4",
                width=int(video["width"]),
                height=int(video["height"]),
            )

    def get_labels(self) -> Iterable[ImageObjectDetection]:
        video_id_to_video = {video.id: video for video in self.get_images()}
        category_id_to_category = {category.id: category for category in self.get_categories()}

        for annotation_json in self._data["annotations"]:
            video_id = annotation_json["video_id"]
            frame_segs: list[SingleObjectDetection] = []

            for bbox in annotation_json["bboxes"]:
                if bbox is not None:
                    frame_segs.append(
                        SingleObjectDetection(
                            category=category_id_to_category[annotation_json["category_id"]],
                            box=BoundingBox.from_format(
                                bbox=bbox, format=BoundingBoxFormat.XYWH
                            ),
                        )
                    )
                else:
                    frame_segs.append(
                        SingleObjectDetection(
                            category=Category(-1, "no segmentation"),
                            box=BoundingBox.from_format(
                                bbox=[0, 0, 0, 0], format=BoundingBoxFormat.XYWH
                            ),
                        )
                    )
            yield ImageObjectDetection(
                image=video_id_to_video[video_id],
                objects=frame_segs,
            )


class _COCOInstanceSegmentationRLE(TypedDict):
    counts: list[int]
    size: list[int]


def _coco_segmentation_to_binary_mask_rle(
    segmentation: _COCOInstanceSegmentationRLE, bbox: list[float]
) -> BinaryMaskSegmentation:
    counts = segmentation["counts"]
    height, width = segmentation["size"]
    return BinaryMaskSegmentation(
        _rle_row_wise=counts,
        width=width,
        height=height,
        bounding_box=BoundingBox.from_format(bbox=bbox, format=BoundingBoxFormat.XYWH),
    )


def load_annotations(session: Session, dataset_id: UUID) -> None:
    print("Loading video annotations...")
    yvis_input = YouTubeVODInput(
        input_file=Path(
            "../../dataset_examples/youtube_vis_100_videos/train/instances_readable_filtered.json"
        )
    )
    videos = video_resolver.get_all_by_dataset_id(session=session, dataset_id=dataset_id).samples
    video_name_to_video = {video.file_name: video for video in videos}
    label_map = _create_label_map(
        session=session,
        input_labels=yvis_input,
    )
    for label in yvis_input.get_labels():
        video = video_name_to_video[label.image.filename]
        assert len(label.objects) == len(video.frames), (
            f"Number of frames in annotation ({len(label.objects)}) does not match "
            f"number of frames in video ({len(video.frames)}) for video "
            f"{label.image.filename}"
        )
        path_to_id = {
            str(idx): frame.sample_id
            for idx, frame in enumerate(video.frames)
        }
        path_to_anno_data = {
            str(idx): ImageObjectDetection(
                image=label.image,
                objects=[obj],
            ) if obj.category.id != -1 else ImageObjectDetection(
                image=label.image,
                objects=[],
            )
            for idx, obj in enumerate(label.objects)
            
        }
        _process_batch_annotations(
            session=session,
            created_path_to_id=path_to_id,
            path_to_anno_data=path_to_anno_data,
            dataset_id=dataset_id,
            label_map=label_map,
        )

        print(f"Loaded annotations for video {label.image.filename}")
        print(f"Annotations for frame 0: {video.frames[0].sample.annotations}")

if __name__ == "__main__":
    # Read environment variables
    env = Env()
    env.read_env()

    # Cleanup an existing database
    db_manager.connect(cleanup_existing=True)

    # Define the path to the dataset directory
    # dataset_path = env.path("EXAMPLES_VIDEO_DATASET_PATH", "/path/to/your/dataset")
    dataset_path = "../../dataset_examples/youtube_vis_100_videos/train/videos"

    # Create a Dataset from a path
    dataset = ls.Dataset.create(sample_type=ls.SampleType.VIDEO)
    dataset.add_videos_from_path(path=dataset_path)

    load_annotations(session=dataset.session, dataset_id=dataset.dataset_id)

    ls.start_gui()