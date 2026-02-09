"""Models for creating annotations."""

from __future__ import annotations

from typing import Protocol
from uuid import UUID

import numpy as np
from labelformat.model.binary_mask_segmentation import BinaryMaskSegmentation
from labelformat.model.bounding_box import BoundingBox, BoundingBoxFormat
from numpy.typing import NDArray
from pydantic import BaseModel
from sqlmodel import Session

from lightly_studio.models.annotation.annotation_base import AnnotationCreate, AnnotationType
from lightly_studio.models.annotation_label import AnnotationLabelCreate
from lightly_studio.resolvers import annotation_label_resolver


class Sample2D(Protocol):
    """Protocol describing samples that have width x height resolution in pixels.

    For example images and video frames.
    """

    @property
    def width(self) -> int:
        """Width in pixels of an image or a video frame."""
        ...

    @property
    def height(self) -> int:
        """Height in pixels of an image or a video frame."""
        ...


class CreateAnnotation(Protocol):
    """Protocol from converting to AnnotationCreate."""

    def to_annotation_create(
        self, session: Session, dataset_id: UUID, parent_sample_id: UUID
    ) -> AnnotationCreate:
        """Convert to AnnotationCreate."""
        ...


class CreateAnnotationBase(BaseModel):
    """Base model for creating annotations."""

    label: str
    """Annotation label."""
    confidence: float | None = None
    """Confidence expressed as probability between 0.0 and 1.0 (inclusive)."""

    def _get_label_id(self, session: Session, dataset_id: UUID) -> UUID:
        label = annotation_label_resolver.get_by_label_name(
            session=session, dataset_id=dataset_id, label_name=self.label
        )
        if label is None:
            label = annotation_label_resolver.create(
                session=session,
                label=AnnotationLabelCreate(
                    dataset_id=dataset_id, annotation_label_name=self.label
                ),
            )
        return label.annotation_label_id


class CreateClassification(CreateAnnotationBase):
    """Input model for creating classification annotations."""

    def to_annotation_create(
        self, session: Session, dataset_id: UUID, parent_sample_id: UUID
    ) -> AnnotationCreate:
        """Convert to AnnotationCreate."""
        return AnnotationCreate(
            annotation_label_id=self._get_label_id(session=session, dataset_id=dataset_id),
            annotation_type=AnnotationType.CLASSIFICATION,
            confidence=self.confidence,
            parent_sample_id=parent_sample_id,
        )


class CreateObjectDetection(CreateAnnotationBase):
    """Input model for creating object detection annotations."""

    x: int
    """Left X coordinate (px) of the object detection bounding box."""
    y: int
    """Top Y coordinate (px) of the object detection bounding box."""
    width: int
    """Width (px) of the object detection bounding box."""
    height: int
    """Height (px) of the object detection bounding box."""

    def to_annotation_create(
        self, session: Session, dataset_id: UUID, parent_sample_id: UUID
    ) -> AnnotationCreate:
        """Convert to AnnotationCreate."""
        return AnnotationCreate(
            annotation_label_id=self._get_label_id(session=session, dataset_id=dataset_id),
            annotation_type=AnnotationType.OBJECT_DETECTION,
            confidence=self.confidence,
            parent_sample_id=parent_sample_id,
            x=self.x,
            y=self.y,
            width=self.width,
            height=self.height,
        )


class CreateInstanceSegmentation(CreateAnnotationBase):
    """Input model for creating instance segmentation annotations."""

    x: int
    """Left X coordinate (px) of the object detection bounding box."""
    y: int
    """Top Y coordinate (px) of the object detection bounding box."""
    width: int
    """Width (px) of the segmentation bounding box."""
    height: int
    """Height (px) of the segmentation bounding box."""
    segmentation_mask: list[int]
    """Segmentation mask given as a run-length encoding."""

    def to_annotation_create(
        self, session: Session, dataset_id: UUID, parent_sample_id: UUID
    ) -> AnnotationCreate:
        """Convert to AnnotationCreate."""
        return AnnotationCreate(
            annotation_label_id=self._get_label_id(session=session, dataset_id=dataset_id),
            annotation_type=AnnotationType.INSTANCE_SEGMENTATION,
            confidence=self.confidence,
            parent_sample_id=parent_sample_id,
            x=self.x,
            y=self.y,
            width=self.width,
            height=self.height,
            segmentation_mask=self.segmentation_mask,
        )

    @staticmethod
    def from_binary_mask(
        label: str,
        binary_mask: NDArray[np.int_],
        confidence: float | None = None,
    ) -> CreateInstanceSegmentation:
        """Create an instance segmentation annotation from a binary mask.

        Args:
            label: Annotation label
            binary_mask: Binary mask of the segmentation given as a 2D array. The dimensions of the
                array must match the image.
            confidence: Optional annotation confidence, between 0.0 and 1.0 (inclusive).

        Returns:
            The CreateInstanceSegmentation instance for the provided details.
        """
        (segmentation_mask, bbox) = _segmentation_mask_and_bounding_box(binary_mask=binary_mask)
        x, y, width, height = bbox

        return CreateInstanceSegmentation(
            x=x,
            y=y,
            width=width,
            height=height,
            segmentation_mask=segmentation_mask,
            label=label,
            confidence=confidence,
        )

    @staticmethod
    def from_rle_mask(
        label: str,
        segmentation_mask: list[int],
        two_dim_sample: Sample2D,
        confidence: float | None = None,
    ) -> CreateInstanceSegmentation:
        """Create an instance segmentation annotation from a RLE segmentation mask.

        Args:
            label: Annotation label
            segmentation_mask: A run-length encoded (RLE) segmentation mask.
            two_dim_sample: A sample having width and height in pixels (image, video frame, etc.).
            confidence: Optional annotation confidence, between 0.0 and 1.0 (inclusive).

        Returns:
            The CreateInstanceSegmentation instance for the provided details.
        """
        x, y, width, height = _bounding_box_from_rle(
            segmentation_mask=segmentation_mask, two_dim_sample=two_dim_sample
        )
        return CreateInstanceSegmentation(
            label=label,
            x=x,
            y=y,
            width=width,
            height=height,
            segmentation_mask=segmentation_mask,
            confidence=confidence,
        )


class CreateSemanticSegmentation(CreateAnnotationBase):
    """Input model for creating semantic segmentation annotations."""

    x: int
    """Left X coordinate (px) of the object detection bounding box."""
    y: int
    """Top Y coordinate (px) of the object detection bounding box."""
    width: int
    """Width (px) of the segmentation bounding box."""
    height: int
    """Height (px) of the segmentation bounding box."""
    segmentation_mask: list[int]
    """Segmentation mask given as a run-length encoding."""

    def to_annotation_create(
        self, session: Session, dataset_id: UUID, parent_sample_id: UUID
    ) -> AnnotationCreate:
        """Convert to AnnotationCreate."""
        return AnnotationCreate(
            annotation_label_id=self._get_label_id(session=session, dataset_id=dataset_id),
            annotation_type=AnnotationType.SEMANTIC_SEGMENTATION,
            confidence=self.confidence,
            parent_sample_id=parent_sample_id,
            x=self.x,
            y=self.y,
            width=self.width,
            height=self.height,
            segmentation_mask=self.segmentation_mask,
        )

    @staticmethod
    def from_binary_mask(
        label: str,
        binary_mask: NDArray[np.int_],
        confidence: float | None = None,
    ) -> CreateSemanticSegmentation:
        """Create a semantic segmentation annotation from a binary mask.

        Args:
            label: Annotation label
            binary_mask: Binary mask of the segmentation given as a 2D array. The dimensions of the
                array must match the image.
            confidence: Optional annotation confidence, between 0.0 and 1.0 (inclusive).

        Returns:
            The CreateSemanticSegmentation instance for the provided details.
        """
        (segmentation_mask, bbox) = _segmentation_mask_and_bounding_box(binary_mask=binary_mask)
        x, y, width, height = bbox

        return CreateSemanticSegmentation(
            x=x,
            y=y,
            width=width,
            height=height,
            segmentation_mask=segmentation_mask,
            label=label,
            confidence=confidence,
        )

    @staticmethod
    def from_rle_mask(
        label: str,
        segmentation_mask: list[int],
        two_dim_sample: Sample2D,
        confidence: float | None = None,
    ) -> CreateSemanticSegmentation:
        """Create a semantic segmentation annotation from a RLE segmentation mask.

        Args:
            label: Annotation label
            segmentation_mask: A run-length encoded (RLE) segmentation mask.
            two_dim_sample: A sample having width and height in pixels (image, video frame, etc.).
            confidence: Optional annotation confidence, between 0.0 and 1.0 (inclusive).

        Returns:
            The CreateSemanticSegmentation instance for the provided details.
        """
        x, y, width, height = _bounding_box_from_rle(
            segmentation_mask=segmentation_mask, two_dim_sample=two_dim_sample
        )
        return CreateSemanticSegmentation(
            label=label,
            x=x,
            y=y,
            width=width,
            height=height,
            segmentation_mask=segmentation_mask,
            confidence=confidence,
        )


def _segmentation_mask_and_bounding_box(
    binary_mask: NDArray[np.int_],
) -> tuple[list[int], list[int]]:
    """Extract run-length encoding and bounding box from a binary mask.

    Args:
        binary_mask: Binary mask of the segmentation.

    Returns:
        A tuple containing:
            - Run-length encoding of the segmentation mask.
            - Bounding box in [x, y, width, height] format.
    """
    if not np.any(binary_mask):  # Handle an empty mask
        xmin, ymin, xmax, ymax = 0, 0, -1, -1
    else:
        rows, cols = np.where(binary_mask)
        ymin, ymax = int(np.min(rows)), int(np.max(rows))
        xmin, xmax = int(np.min(cols)), int(np.max(cols))

    bounding_box = BoundingBox(
        xmin=xmin,
        ymin=ymin,
        xmax=xmax + 1,
        ymax=ymax + 1,
    )
    segmentation = BinaryMaskSegmentation.from_binary_mask(
        binary_mask=binary_mask, bounding_box=bounding_box
    )
    box = segmentation.bounding_box.to_format(BoundingBoxFormat.XYWH)
    box_i = [int(v) for v in box]
    return (segmentation.get_rle(), box_i)


def _bounding_box_from_rle(segmentation_mask: list[int], two_dim_sample: Sample2D) -> list[int]:
    """Extract bounding box from a run-length encoded (RLE) segmentation mask.

    Args:
        segmentation_mask: Run-length encoded (RLE) segmentation mask.
        two_dim_sample: A sample having width and height in pixels (image, video frame, etc.).

    Returns:
        Bounding box in [x, y, width, height] format.
    """
    binary_mask_segmentation = BinaryMaskSegmentation.from_rle(
        rle_row_wise=segmentation_mask,
        width=two_dim_sample.width,
        height=two_dim_sample.height,
    )
    bbox = binary_mask_segmentation.bounding_box.to_format(BoundingBoxFormat.XYWH)
    return [int(v) for v in bbox]
