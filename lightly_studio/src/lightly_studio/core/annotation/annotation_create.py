"""Models for creating annotations."""

from __future__ import annotations

from typing import Protocol
from uuid import UUID

from pydantic import BaseModel

from lightly_studio.models.annotation.annotation_base import AnnotationCreate, AnnotationType


class CreateAnnotation(Protocol):
    """Protocol from converting to AnnotationCreate."""

    def to_annotation_create(self, parent_sample_id: UUID) -> AnnotationCreate:
        """Convert to AnnotationCreate."""
        ...


class CreateAnnotationBase(BaseModel):
    """Base model for creating annotations."""

    annotation_label_id: UUID
    confidence: float | None = None


class CreateClassification(CreateAnnotationBase):
    """Input model for creating classification annotations."""

    def to_annotation_create(self, parent_sample_id: UUID) -> AnnotationCreate:
        """Convert to AnnotationCreate."""
        return AnnotationCreate(
            annotation_label_id=self.annotation_label_id,
            annotation_type=AnnotationType.CLASSIFICATION,
            confidence=self.confidence,
            parent_sample_id=parent_sample_id,
        )


class CreateObjectDetection(CreateAnnotationBase):
    """Input model for creating object detection annotations."""

    x: int
    y: int
    width: int
    height: int

    def to_annotation_create(self, parent_sample_id: UUID) -> AnnotationCreate:
        """Convert to AnnotationCreate."""
        return AnnotationCreate(
            annotation_label_id=self.annotation_label_id,
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
    y: int
    width: int
    height: int
    segmentation_mask: list[int]

    def to_annotation_create(self, parent_sample_id: UUID) -> AnnotationCreate:
        """Convert to AnnotationCreate."""
        return AnnotationCreate(
            annotation_label_id=self.annotation_label_id,
            annotation_type=AnnotationType.INSTANCE_SEGMENTATION,
            confidence=self.confidence,
            parent_sample_id=parent_sample_id,
            x=self.x,
            y=self.y,
            width=self.width,
            height=self.height,
            segmentation_mask=self.segmentation_mask,
        )


class CreateSemanticSegmentation(CreateAnnotationBase):
    """Input model for creating semantic segmentation annotations."""

    x: int
    y: int
    width: int
    height: int
    segmentation_mask: list[int]

    def to_annotation_create(self, parent_sample_id: UUID) -> AnnotationCreate:
        """Convert to AnnotationCreate."""
        return AnnotationCreate(
            annotation_label_id=self.annotation_label_id,
            annotation_type=AnnotationType.SEMANTIC_SEGMENTATION,
            confidence=self.confidence,
            parent_sample_id=parent_sample_id,
            x=self.x,
            y=self.y,
            width=self.width,
            height=self.height,
            segmentation_mask=self.segmentation_mask,
        )
