"""Exports datasets from Lightly Studio into various formats."""

from __future__ import annotations

import json
from collections.abc import Iterable
from pathlib import Path
from typing import cast
from uuid import UUID

from labelformat.formats import (
    COCOInstanceSegmentationOutput,
    COCOObjectDetectionOutput,
    PascalVOCSemanticSegmentationOutput,
    YOLOv8ObjectDetectionOutput,
)
from labelformat.model.image import Image
from sqlmodel import Session

from lightly_studio.core.image.image_sample import ImageSample
from lightly_studio.core.sample import Sample
from lightly_studio.export import coco_captions
from lightly_studio.export.lightly_studio_label_input import (
    LightlyStudioInstanceSegmentationInput,
    LightlyStudioObjectDetectionInput,
    LightlyStudioPascalVOCInstanceSegmentationInput,
    LightlyStudioYOLOObjectDetectionInput,
    SampleToImage,
)
from lightly_studio.type_definitions import PathLike

DEFAULT_EXPORT_FILENAME = "coco_export.json"
YOLO_DATASET_CONFIG_FILENAME = "data.yaml"
YOLO_DEFAULT_SPLIT = "train"


class DatasetExport:
    """Provides methods to export a dataset or a subset of it."""

    # TODO(malte, 07/2026): Move `DatasetExport` into its own `dataset_export.py` module.
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
            sample_to_image=self._sample_to_image,
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
            sample_to_image=self._sample_to_image,
        )
        # Keep `background_class_id` unchanged: the label input defines category IDs and
        # reserves class 0 for background.
        PascalVOCSemanticSegmentationOutput(output_folder=Path(output_folder)).save(
            label_input=export_input
        )


class ImageDatasetExport(DatasetExport):
    """Provides methods to export an image dataset or a subset of it.

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
        super().__init__(
            session=session,
            dataset_id=dataset_id,
            samples=samples,
            sample_to_image=image_sample_to_image,
        )


def image_sample_to_image(sample: Sample, image_id: int, use_relative_filename: bool) -> Image:
    """Maps an image sample to a labelformat `Image`.

    Conforms to the `SampleToImage` strategy, so `sample` is typed as `Sample`; it is always
    an `ImageSample` here because this strategy is only used by `ImageDatasetExport`.

    COCO stores the absolute path verbatim; YOLO and Pascal VOC need a relative file name.
    """
    image_sample = cast(ImageSample, sample)
    filename = image_sample.file_name if use_relative_filename else image_sample.file_path_abs
    return Image(
        id=image_id,
        filename=filename,
        width=image_sample.width,
        height=image_sample.height,
    )
