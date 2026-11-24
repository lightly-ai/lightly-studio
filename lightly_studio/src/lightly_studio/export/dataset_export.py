"""Exports datasets from Lightly Studio into various formats."""

from __future__ import annotations

import json
import logging
import warnings
from collections.abc import Iterable
from pathlib import Path
from uuid import UUID

from labelformat.formats import (
    COCOInstanceSegmentationOutput,
    COCOObjectDetectionOutput,
    PascalVOCSemanticSegmentationOutput,
    YOLOv8InstanceSegmentationOutput,
    YOLOv8ObjectDetectionOutput,
)
from sqlmodel import Session

from lightly_studio.core.sample import Sample
from lightly_studio.export import annotation_batches, coco_captions
from lightly_studio.export.lightly_studio_label_input import (
    LightlyStudioInstanceSegmentationInput,
    LightlyStudioObjectDetectionInput,
    LightlyStudioPascalVOCInstanceSegmentationInput,
    LightlyStudioYOLOInstanceSegmentationInput,
    LightlyStudioYOLOObjectDetectionInput,
    SampleToImage,
)
from lightly_studio.models.annotation.annotation_base import AnnotationType
from lightly_studio.type_definitions import PathLike

logger = logging.getLogger(__name__)

DEFAULT_EXPORT_FILENAME = "coco_export.json"
YOLO_DATASET_CONFIG_FILENAME = "data.yaml"
YOLO_DEFAULT_SPLIT = "train"


class DatasetExport:
    """Provides methods to export a dataset or a subset of it."""

    def __init__(
        self,
        session: Session,
        dataset_id: UUID,
        samples: Iterable[Sample],
        sample_to_image: SampleToImage,
    ):
        """Initializes the DatasetExport object.

        Args:
            session: The database session.
            dataset_id: The dataset ID for label retrieval.
            samples: Samples to export.
            sample_to_image: Strategy mapping a sample to a labelformat `Image`.
        """
        self.session = session
        self._dataset_id = dataset_id
        self.samples = samples
        self._sample_to_image = sample_to_image

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
        """
        if output_json is None:
            output_json = DEFAULT_EXPORT_FILENAME
        export_input = LightlyStudioObjectDetectionInput(
            session=self.session,
            dataset_id=self._dataset_id,
            samples=self.samples,
            annotation_collection_id=annotation_collection_id,
            sample_to_image=self._sample_to_image,
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
            sample_to_image=self._sample_to_image,
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
        coco_captions_dict = coco_captions.to_coco_captions_dict(
            samples=self.samples, sample_to_image=self._sample_to_image
        )
        with Path(output_json).open("w") as f:
            json.dump(coco_captions_dict, f, indent=2)

    def to_coco_instance_segmentation(
        self,
        output_json: PathLike | None = None,
        annotation_collection_id: UUID | None = None,
    ) -> None:
        """Exports polygons and segmentation masks to a COCO format JSON file.

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
            sample_to_image=self._sample_to_image,
        )
        COCOInstanceSegmentationOutput(output_file=Path(output_json)).save(label_input=export_input)

    def to_yolo_instance_segmentation(
        self,
        output_folder: PathLike,
        annotation_collection_id: UUID | None = None,
    ) -> None:
        """Exports polygons to YOLO (Ultralytics YOLOv8) instance segmentation format.

        Creates a folder with a ``data.yaml`` dataset config and a ``labels``
        subfolder containing one ``.txt`` file per image with normalized
        ``<class_id> <x1> <y1> <x2> <y2> ...`` rows. A polygon with several parts is
        written as one row. YOLO supports only polygons, so segmentation masks are
        skipped with a warning.

        Args:
            output_folder: The folder where YOLO files are written.
            annotation_collection_id: If provided, only annotations from this collection
                are exported. If None, all annotations are exported.
        """
        export_input = LightlyStudioYOLOInstanceSegmentationInput(
            session=self.session,
            dataset_id=self._dataset_id,
            samples=self.samples,
            annotation_collection_id=annotation_collection_id,
            sample_to_image=self._sample_to_image,
        )
        skipped_mask_count = annotation_batches.count_annotations(
            session=self.session,
            samples=self.samples,
            annotation_type=AnnotationType.SEGMENTATION_MASK,
            annotation_collection_id=annotation_collection_id,
        )
        if skipped_mask_count > 0:
            logger.warning(
                "Skipped %d segmentation mask annotations: "
                "YOLO instance segmentation supports only polygons.",
                skipped_mask_count,
            )
        YOLOv8InstanceSegmentationOutput(
            output_file=Path(output_folder) / YOLO_DATASET_CONFIG_FILENAME,
            output_split=YOLO_DEFAULT_SPLIT,
        ).save(label_input=export_input)

    def to_coco_segmentation_masks(
        self,
        output_json: PathLike | None = None,
        annotation_collection_id: UUID | None = None,
    ) -> None:
        """Deprecated: use `to_coco_instance_segmentation` instead.

        Args:
            output_json: The path to the output COCO JSON file. If not provided,
                defaults to "coco_export.json" in the current working directory.
            annotation_collection_id: If provided, only annotations from this collection
                are exported. If None, all annotations are exported.
        """
        warnings.warn(
            "to_coco_segmentation_masks is deprecated, use to_coco_instance_segmentation instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        self.to_coco_instance_segmentation(
            output_json=output_json, annotation_collection_id=annotation_collection_id
        )

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
            sample_to_image=self._sample_to_image,
        )
        # Keep `background_class_id` unchanged: the label input defines category IDs and
        # reserves class 0 for background.
        PascalVOCSemanticSegmentationOutput(output_folder=Path(output_folder)).save(
            label_input=export_input
        )
