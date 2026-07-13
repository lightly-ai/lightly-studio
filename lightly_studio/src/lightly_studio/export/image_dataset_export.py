"""Exports datasets from Lightly Studio into various formats."""

from __future__ import annotations

from collections.abc import Iterable
from typing import cast
from uuid import UUID

from labelformat.model.image import Image
from sqlmodel import Session

from lightly_studio.core.image.image_sample import ImageSample
from lightly_studio.core.sample import Sample
from lightly_studio.export.dataset_export import DatasetExport


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
