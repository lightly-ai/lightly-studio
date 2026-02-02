"""Models for creating annotations."""

from __future__ import annotations

from typing import Protocol
from uuid import UUID

from pydantic import BaseModel
from sqlmodel import Session

from lightly_studio.models.annotation.annotation_base import AnnotationCreate, AnnotationType
from lightly_studio.models.annotation_label import AnnotationLabelCreate
from lightly_studio.resolvers import annotation_label_resolver


class CreateAnnotation(Protocol):
    """Protocol from converting to AnnotationCreate."""

    def to_annotation_create(
        self, session: Session, dataset_id: UUID, parent_sample_id: UUID
    ) -> AnnotationCreate:
        """Convert to AnnotationCreate."""
        ...


class CreateAnnotationBase(BaseModel):
    """Base model for creating annotations."""

    annotation_label_name: str
    confidence: float | None = None

    def _get_label_id(self, session: Session, dataset_id: UUID) -> UUID:
        label = annotation_label_resolver.get_by_label_name(
            session=session, dataset_id=dataset_id, label_name=self.annotation_label_name
        )
        if label is None:
            label = annotation_label_resolver.create(
                session=session,
                label=AnnotationLabelCreate(
                    dataset_id=dataset_id, annotation_label_name=self.annotation_label_name
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
    y: int
    width: int
    height: int

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
    y: int
    width: int
    height: int
    segmentation_mask: list[int]

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


class CreateSemanticSegmentation(CreateAnnotationBase):
    """Input model for creating semantic segmentation annotations."""

    x: int
    y: int
    width: int
    height: int
    segmentation_mask: list[int]

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
