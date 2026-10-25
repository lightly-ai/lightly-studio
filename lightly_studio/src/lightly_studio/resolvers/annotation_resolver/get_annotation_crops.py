"""Build image crops for annotations from their bounding boxes."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from uuid import UUID

from lightly_studio_serve.types import ImageCrop
from sqlalchemy import ColumnElement, String, cast, func, literal, select
from sqlmodel import Session, col

from lightly_studio.models.annotation.annotation_base import AnnotationBaseTable
from lightly_studio.models.annotation.object_detection import ObjectDetectionAnnotationTable
from lightly_studio.models.annotation.segmentation import SegmentationAnnotationTable
from lightly_studio.models.image import ImageTable

logger = logging.getLogger(__name__)

CROP_FINGERPRINT_PREFIX = "bbox1:"
_BOX_COLUMN_NAMES = ("x", "y", "width", "height")


@dataclass(frozen=True)
class AnnotationCrop:
    """A resolved annotation crop ready for embedding.

    Binds an annotation sample to the image crop derived from its box. The fingerprint
    describes the raw box, read in the same query as the crop.
    """

    annotation_sample_id: UUID
    image_crop: ImageCrop
    source_fingerprint: str


def build_crop_fingerprint_expression() -> ColumnElement[str]:
    """The crop fingerprint of an annotation's raw box, as SQL.

    The query must outer join ObjectDetectionAnnotationTable and SegmentationAnnotationTable
    on the annotation's sample_id.
    """
    box: ColumnElement[str] = literal(CROP_FINGERPRINT_PREFIX)
    for index, name in enumerate(_BOX_COLUMN_NAMES):
        value = cast(_box_column(name=name), String)
        box = box + value if index == 0 else box + "," + value
    return box


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
    # Plain columns, not ORM entities: an entity can come from the session's identity map
    # with a stale box, while the fingerprint is always read fresh.
    rows = session.execute(
        select(
            col(AnnotationBaseTable.sample_id),
            col(ImageTable.file_path_abs),
            col(ImageTable.width),
            col(ImageTable.height),
            *(_box_column(name=name) for name in _BOX_COLUMN_NAMES),
            build_crop_fingerprint_expression(),
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
    for (
        annotation_sample_id,
        file_path_abs,
        image_width,
        image_height,
        x,
        y,
        width,
        height,
        fingerprint,
    ) in rows:
        # An annotation has a detail row in exactly one table, set by its type in
        # create_many, so at most one of these joins matches.
        if x is None:
            logger.warning(
                "Skipping annotation crop %s without a bounding box.", annotation_sample_id
            )
            continue
        image_crop = _create_valid_image_crop(
            filepath=file_path_abs,
            image_size=(image_width, image_height),
            box=(x, y, width, height),
        )
        if image_crop is None:
            logger.warning("Skipping invalid annotation crop %s.", annotation_sample_id)
            continue
        annotation_crops.append(
            AnnotationCrop(
                annotation_sample_id=annotation_sample_id,
                image_crop=image_crop,
                source_fingerprint=fingerprint,
            )
        )

    return annotation_crops


def _box_column(name: str) -> ColumnElement[int]:
    """One box coordinate from whichever detail table holds the annotation's box."""
    return func.coalesce(
        getattr(ObjectDetectionAnnotationTable, name),
        getattr(SegmentationAnnotationTable, name),
    )


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
