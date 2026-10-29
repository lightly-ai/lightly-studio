"""Exports datasets from Lightly Studio into various formats."""

from __future__ import annotations

import dataclasses
from collections.abc import Iterable
from pathlib import Path
from typing import cast
from uuid import UUID

from labelformat.model.image import Image
from sqlmodel import Session

from lightly_studio.core.image.image_sample import ImageSample
from lightly_studio.core.sample import Sample
from lightly_studio.export import classification_csv, image_files
from lightly_studio.export.dataset_export import DEFAULT_EXPORT_FILENAME, DatasetExport
from lightly_studio.type_definitions import PathLike

DEFAULT_CLASSIFICATION_EXPORT_FILENAME = "classification_export.csv"
IMAGES_FOLDER_NAME = "images"


class ImageDatasetExport(DatasetExport):
    """Provides methods to export an image dataset or a subset of it.

    This class is typically not instantiated directly but returned by `Dataset.export()`.
    It allows exporting data in various formats.
    """

    samples: Iterable[ImageSample]

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

    def to_coco_object_detections(
        self,
        output_json: PathLike | None = None,
        annotation_collection_id: UUID | None = None,
        include_images: bool = False,
    ) -> None:
        """Exports object detection annotations to a COCO format JSON file.

        Args:
            output_json: The path to the output COCO JSON file. If not provided,
                defaults to "coco_export.json" in the current working directory.
            annotation_collection_id: If provided, only annotations from this collection
                are exported. If None, all annotations are exported.
            include_images: If True, the images are copied into an ``images`` folder next
                to ``output_json``, and each COCO ``file_name`` is the image path relative
                to that folder. Images are read from local or remote storage. If False,
                each ``file_name`` is the absolute image path.
        """
        if not include_images:
            super().to_coco_object_detections(
                output_json=output_json, annotation_collection_id=annotation_collection_id
            )
            return

        output_json = Path(output_json if output_json is not None else DEFAULT_EXPORT_FILENAME)
        samples = list(self.samples)
        source_paths = [sample.file_path_abs for sample in samples]
        relative_paths = image_files.relative_image_paths(paths=source_paths)
        images_folder = output_json.parent / IMAGES_FOLDER_NAME
        images_folder.mkdir(parents=True, exist_ok=True)
        image_files.copy_images(
            sources=source_paths,
            destinations=[images_folder / path for path in relative_paths],
        )

        relative_path_by_sample_id = {
            sample.sample_id: path for sample, path in zip(samples, relative_paths)
        }

        def sample_to_bundled_image(
            sample: Sample, image_id: int, use_relative_filename: bool
        ) -> Image:
            image = image_sample_to_image(
                sample=sample, image_id=image_id, use_relative_filename=use_relative_filename
            )
            return dataclasses.replace(image, filename=relative_path_by_sample_id[sample.sample_id])

        DatasetExport(
            session=self.session,
            dataset_id=self._dataset_id,
            samples=samples,
            sample_to_image=sample_to_bundled_image,
        ).to_coco_object_detections(
            output_json=output_json, annotation_collection_id=annotation_collection_id
        )

    def to_csv_classifications(
        self,
        output_csv: PathLike | None = None,
        annotation_collection_id: UUID | None = None,
    ) -> None:
        """Export classification annotations to a long-form CSV file.

        The output contains one row per classification annotation with the columns
        ``file_path_abs``, ``class_name``, ``confidence``, and ``annotation_source``.

        Args:
            output_csv: Destination CSV file. If omitted, defaults to
                ``classification_export.csv`` in the current working directory.
            annotation_collection_id: If provided, only annotations from this annotation
                collection are exported. If ``None``, all annotation sources are exported.
        """
        if output_csv is None:
            output_csv = DEFAULT_CLASSIFICATION_EXPORT_FILENAME
        classification_csv.write_classifications_csv(
            samples=self.samples,
            output_csv=Path(output_csv),
            annotation_collection_id=annotation_collection_id,
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
