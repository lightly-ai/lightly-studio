"""Exports datasets from Lightly Studio into various formats."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from typing import cast
from uuid import UUID

from labelformat.model.image import Image
from sqlmodel import Session

from lightly_studio.core.image.image_sample import ImageSample
from lightly_studio.core.sample import Sample
from lightly_studio.export import classification_csv
from lightly_studio.export.dataset_export import DatasetExport
from lightly_studio.type_definitions import PathLike

DEFAULT_CLASSIFICATION_EXPORT_FILENAME = "classification_export.csv"


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
