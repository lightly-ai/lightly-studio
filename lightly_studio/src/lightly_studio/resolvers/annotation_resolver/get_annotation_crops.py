"""Build image crops for annotations from their bounding boxes."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from uuid import UUID

from sqlmodel import Session, col, select

from lightly_studio.dataset.embedding_generator import ImageCrop
from lightly_studio.models.annotation.annotation_base import AnnotationBaseTable
from lightly_studio.models.annotation.object_detection import ObjectDetectionAnnotationTable
from lightly_studio.models.annotation.segmentation import SegmentationAnnotationTable
from lightly_studio.models.image import ImageTable

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AnnotationCrop:
    """A resolved annotation crop ready for embedding.

    Binds an annotation sample to the image crop derived from its box.
    """

    annotation_sample_id: UUID
    image_crop: ImageCrop


def get_annotation_crops_for_ids(
    session: Session,
    annotation_sample_ids: list[UUID],
) -> list[AnnotationCrop]:
    """Build valid image crops for the given annotation IDs.

    The bounding box is read from whichever detail table holds it: object-detection
    annotations store it in ``ObjectDetectionAnnotationTable`` and segmentation
    annotations in ``SegmentationAnnotationTable`` (both expose ``x/y/width/height``).

    Crops whose box does not overlap the source image are skipped with a warning, so the
    returned list may be shorter than ``annotation_sample_ids``.

    Args:
        session: Database session for resolver operations.
        annotation_sample_ids: Annotation sample IDs to resolve crops for.

    Returns:
        Resolved annotation crops ready for embedding.
    """
    rows = session.exec(
        select(
            AnnotationBaseTable,
            ImageTable,
            ObjectDetectionAnnotationTable,
            SegmentationAnnotationTable,
        )
        .join(ImageTable, col(ImageTable.sample_id) == col(AnnotationBaseTable.parent_sample_id))
        .outerjoin(
            ObjectDetectionAnnotationTable,
            col(ObjectDetectionAnnotationTable.sample_id) == col(AnnotationBaseTable.sample_id),
        )
        .outerjoin(
            SegmentationAnnotationTable,
            col(SegmentationAnnotationTable.sample_id) == col(AnnotationBaseTable.sample_id),
        )
        .where(col(AnnotationBaseTable.sample_id).in_(annotation_sample_ids))
        .order_by(col(ImageTable.file_path_abs))
    ).all()

    annotation_crops: list[AnnotationCrop] = []
    for annotation, image, object_detection, segmentation in rows:
        # An annotation has a detail row in exactly one table, set by its type in
        # create_many, so at most one of these joins matches.
        box_source = object_detection or segmentation
        if box_source is None:
            logger.warning(
                "Skipping annotation crop %s without a bounding box.", annotation.sample_id
            )
            continue
        image_crop = _create_valid_image_crop(
            filepath=image.file_path_abs,
            image_size=(image.width, image.height),
            box=(
                box_source.x,
                box_source.y,
                box_source.width,
                box_source.height,
            ),
        )
        if image_crop is None:
            logger.warning("Skipping invalid annotation crop %s.", annotation.sample_id)
            continue
        annotation_crops.append(
            AnnotationCrop(annotation_sample_id=annotation.sample_id, image_crop=image_crop)
        )

    return annotation_crops


def _create_valid_image_crop(
    filepath: str,
    image_size: tuple[int, int],
    box: tuple[int, int, int, int],
) -> ImageCrop | None:
    """Clamp an annotation box to the image bounds and return the resulting crop.

    Args:
        filepath: Absolute path to the source image.
        image_size: Source image size as ``(width, height)`` in pixels.
        box: Annotation box as ``(x, y, width, height)`` in pixels, possibly extending
            outside the image.

    Returns:
        An ``ImageCrop`` clamped to the image bounds, or ``None`` if the box does not
        overlap the image (degenerate crop).
    """
    image_width, image_height = image_size
    x, y, width, height = box
    x_min = max(0, x)
    y_min = max(0, y)
    x_max = min(image_width, x + width)
    y_max = min(image_height, y + height)
    crop_width = x_max - x_min
    crop_height = y_max - y_min
    if crop_width <= 0 or crop_height <= 0:
        return None
    return ImageCrop(
        filepath=filepath,
        x=x_min,
        y=y_min,
        width=crop_width,
        height=crop_height,
    )
