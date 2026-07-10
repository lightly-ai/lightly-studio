"""Exports datasets from Lightly Studio into various formats."""

from __future__ import annotations

import json
from collections.abc import Iterable
from pathlib import Path
from uuid import UUID

from labelformat.formats import (
    COCOInstanceSegmentationOutput,
    COCOObjectDetectionOutput,
    PascalVOCSemanticSegmentationOutput,
    YOLOv8ObjectDetectionOutput,
)
from sqlmodel import Session

from lightly_studio.core.image.image_sample import ImageSample
from lightly_studio.export import coco_captions
from lightly_studio.export.lightly_studio_label_input import (
    LightlyStudioInstanceSegmentationInput,
    LightlyStudioObjectDetectionInput,
    LightlyStudioPascalVOCInstanceSegmentationInput,
    LightlyStudioYOLOObjectDetectionInput,
)
from lightly_studio.type_definitions import PathLike

DEFAULT_EXPORT_FILENAME = "coco_export.json"
YOLO_DATASET_CONFIG_FILENAME = "data.yaml"
YOLO_DEFAULT_SPLIT = "train"


class ImageDatasetExport:
    """Provides methods to export a dataset or a subset of it.

    This class is typically not instantiated directly but returned by `Dataset.export()`.
    It allows exporting data in various formats.
    """

    def __init__(
        self,
        session: Session,
        dataset_id: UUID,
        samples: Iterable[ImageSample],
    ):
        """Initializes the ImageDatasetExport object.

        Args:
            session: The database session.
            dataset_id: The dataset ID for label retrieval.
            samples: Samples to export.
        """
        self.session = session
        self._dataset_id = dataset_id
        self.samples = samples

    def to_coco_object_detections(
        self,
        output_json: PathLike | None = None,
        annotation_collection_id: UUID | None = None,
    ) -> None:
        """Exports object detection annotations to a COCO format JSON file.

        Args:
            output_json: The path to the output COCO JSON file. If not provided,
                defaults to "coco_export.json" in the current working directory.
            annotation_collection_id: If provided, only annotations from this collection
                are exported. If None, all annotations are exported.

        Raises:
            ValueError: If the annotation source with the given name does not exist.
        """
        if output_json is None:
            output_json = DEFAULT_EXPORT_FILENAME
        export_input = LightlyStudioObjectDetectionInput(
            session=self.session,
            dataset_id=self._dataset_id,
            samples=self.samples,
            annotation_collection_id=annotation_collection_id,
        )
        COCOObjectDetectionOutput(output_file=Path(output_json)).save(label_input=export_input)

    def to_yolo_object_detections(
        self,
        output_folder: PathLike,
        annotation_collection_id: UUID | None = None,
    ) -> None:
        """Exports object detection annotations to YOLO (Ultralytics YOLOv8) format.

        Creates a folder with a ``data.yaml`` dataset config and a ``labels``
        subfolder containing one ``.txt`` file per image with normalized
        ``<class_id> <x_center> <y_center> <width> <height>`` rows.

        Args:
            output_folder: The folder where YOLO files are written.
            annotation_collection_id: If provided, only annotations from this collection
                are exported. If None, all annotations are exported.
        """
        export_input = LightlyStudioYOLOObjectDetectionInput(
            session=self.session,
            dataset_id=self._dataset_id,
            samples=self.samples,
            annotation_collection_id=annotation_collection_id,
        )
        YOLOv8ObjectDetectionOutput(
            output_file=Path(output_folder) / YOLO_DATASET_CONFIG_FILENAME,
            output_split=YOLO_DEFAULT_SPLIT,
        ).save(label_input=export_input)

    def to_coco_captions(self, output_json: PathLike | None = None) -> None:
        """Exports captions to a COCO format JSON file.

        Args:
            output_json: The path to the output COCO JSON file. If not provided,
                defaults to "coco_export.json" in the current working directory.
        """
        if output_json is None:
            output_json = DEFAULT_EXPORT_FILENAME
        coco_captions_dict = coco_captions.to_coco_captions_dict(samples=self.samples)
        with Path(output_json).open("w") as f:
            json.dump(coco_captions_dict, f, indent=2)

    def to_coco_segmentation_masks(
        self,
        output_json: PathLike | None = None,
        annotation_collection_id: UUID | None = None,
    ) -> None:
        """Exports segmentation masks to a COCO format JSON file.

        Args:
            output_json: The path to the output COCO JSON file. If not provided,
                defaults to "coco_export.json" in the current working directory.
            annotation_collection_id: If provided, only annotations from this collection
                are exported. If None, all annotations are exported.
        """
        if output_json is None:
            output_json = DEFAULT_EXPORT_FILENAME
        export_input = LightlyStudioInstanceSegmentationInput(
            session=self.session,
            dataset_id=self._dataset_id,
            samples=self.samples,
            annotation_collection_id=annotation_collection_id,
        )
        COCOInstanceSegmentationOutput(output_file=Path(output_json)).save(label_input=export_input)

    def to_pascalvoc_segmentation_mask(
        self,
        output_folder: PathLike,
        annotation_collection_id: UUID | None = None,
    ) -> None:
        """Exports segmentation mask annotations to Pascal VOC format.

        Creates a folder with per-pixel class masks (PNG) and a class map (JSON).

        Args:
            output_folder: The folder where Pascal VOC segmentation files are
                written. The folder contains a `SegmentationClass` subfolder
                with PNG masks and a `class_id_to_name.json` file.
            annotation_collection_id: If provided, only annotations from this collection
                are exported. If None, all annotations are exported.
        """
        export_input = LightlyStudioPascalVOCInstanceSegmentationInput(
            session=self.session,
            dataset_id=self._dataset_id,
            samples=self.samples,
            annotation_collection_id=annotation_collection_id,
        )
        # Keep `background_class_id` unchanged: the label input defines category IDs and
        # reserves class 0 for background.
        PascalVOCSemanticSegmentationOutput(output_folder=Path(output_folder)).save(
            label_input=export_input
        )
