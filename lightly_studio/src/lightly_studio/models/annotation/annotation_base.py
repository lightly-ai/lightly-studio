"""This module defines the base annotation model."""

from datetime import datetime, timezone
from enum import Enum
from typing import TYPE_CHECKING, List, Optional, Union
from uuid import UUID

from pydantic import BaseModel, ConfigDict
from pydantic import Field as PydanticField
from sqlalchemy.orm import Mapped
from sqlmodel import Field, Relationship, SQLModel

from lightly_studio.models.annotation.instance_segmentation import (
    InstanceSegmentationAnnotationTable,
    InstanceSegmentationAnnotationView,
)
from lightly_studio.models.annotation.links import AnnotationTagLinkTable
from lightly_studio.models.annotation.object_detection import (
    ObjectDetectionAnnotationTable,
    ObjectDetectionAnnotationView,
)
from lightly_studio.models.annotation.semantic_segmentation import (
    SemanticSegmentationAnnotationTable,
    SemanticSegmentationAnnotationView,
)
from lightly_studio.models.sample import SampleTable

if TYPE_CHECKING:
    from lightly_studio.models.annotation_label import (
        AnnotationLabelTable,
    )
    from lightly_studio.models.tag import TagTable
else:
    TagTable = object
    AnnotationLabelTable = object


class AnnotationType(str, Enum):
    """The type of annotation task."""

    CLASSIFICATION = "classification"
    SEMANTIC_SEGMENTATION = "semantic_segmentation"
    INSTANCE_SEGMENTATION = "instance_segmentation"
    OBJECT_DETECTION = "object_detection"


class AnnotationBaseTable(SQLModel, table=True):
    """Base class for all annotation models."""

    __tablename__ = "annotation_base"

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), index=True)

    sample_id: UUID = Field(foreign_key="sample.sample_id", primary_key=True)
    annotation_type: AnnotationType
    annotation_label_id: UUID = Field(foreign_key="annotation_label.annotation_label_id")

    confidence: Optional[float] = None
    parent_sample_id: UUID = Field(foreign_key="sample.sample_id")

    annotation_label: Mapped["AnnotationLabelTable"] = Relationship(
        sa_relationship_kwargs={"lazy": "select"},
    )
    sample: Mapped["SampleTable"] = Relationship(
        sa_relationship_kwargs={
            "lazy": "select",
            "foreign_keys": "[AnnotationBaseTable.sample_id]",
        },
    )
    parent_sample: Mapped[Optional["SampleTable"]] = Relationship(
        back_populates="annotations",
        sa_relationship_kwargs={
            "lazy": "select",
            "foreign_keys": "[AnnotationBaseTable.parent_sample_id]",
        },
    )
    tags: Mapped[List["TagTable"]] = Relationship(
        back_populates="annotations",
        link_model=AnnotationTagLinkTable,
    )

    """ Details about object detection. """
    object_detection_details: Mapped[Optional["ObjectDetectionAnnotationTable"]] = Relationship(
        back_populates="annotation_base",
        sa_relationship_kwargs={"lazy": "select"},
    )

    """ Details about instance segmentation. """
    instance_segmentation_details: Mapped[Optional["InstanceSegmentationAnnotationTable"]] = (
        Relationship(
            back_populates="annotation_base",
            sa_relationship_kwargs={"lazy": "select"},
        )
    )

    """ Details about semantic segmentation. """
    semantic_segmentation_details: Mapped[Optional["SemanticSegmentationAnnotationTable"]] = (
        Relationship(
            back_populates="annotation_base",
            sa_relationship_kwargs={"lazy": "select"},
        )
    )


class AnnotationCreate(SQLModel):
    """Input model for creating annotations."""

    """ Required properties for all annotations. """
    annotation_label_id: UUID
    annotation_type: AnnotationType
    confidence: Optional[float] = None
    parent_sample_id: UUID

    """ Optional properties for object detection. """
    x: Optional[int] = None
    y: Optional[int] = None
    width: Optional[int] = None
    height: Optional[int] = None

    """ Optional properties for instance and semantic segmentation. """
    segmentation_mask: Optional[List[int]] = None


class AnnotationView(BaseModel):
    """Response model for bounding box annotation."""

    model_config = ConfigDict(populate_by_name=True, from_attributes=True)

    class AnnotationLabel(SQLModel):
        """Model used when retrieving an annotation label."""

        annotation_label_name: str

    class AnnotationViewTag(SQLModel):
        """Tag view inside Annotation view."""

        tag_id: UUID
        name: str

    parent_sample_id: UUID
    sample_id: UUID
    annotation_type: AnnotationType
    annotation_label: AnnotationLabel
    confidence: Optional[float] = None
    created_at: datetime

    object_detection_details: Optional[ObjectDetectionAnnotationView] = None
    instance_segmentation_details: Optional[InstanceSegmentationAnnotationView] = None
    semantic_segmentation_details: Optional[SemanticSegmentationAnnotationView] = None

    tags: List[AnnotationViewTag] = []


class AnnotationViewsWithCount(BaseModel):
    """Response model for counted annotations."""

    model_config = ConfigDict(populate_by_name=True)

    annotations: List[AnnotationView] = PydanticField(..., alias="data")
    total_count: int
    next_cursor: Optional[int] = PydanticField(..., alias="nextCursor")


class ImageAnnotationView(BaseModel):
    """Response model for image annotation view."""

    model_config = ConfigDict(populate_by_name=True)

    sample_id: UUID
    file_path_abs: str
    width: int
    height: int


class VideoFrameAnnotationView(BaseModel):
    """Response model for video frame annotation view."""

    model_config = ConfigDict(populate_by_name=True)

    class VideoAnnotationView(BaseModel):
        """Response model for video view."""

        height: int
        width: int
        file_path_abs: str

    sample_id: UUID
    video: VideoAnnotationView


class AnnotationWithPayloadView(BaseModel):
    """Response model for annotation with payload."""

    model_config = ConfigDict(populate_by_name=True)

    annotation: AnnotationView
    parent_sample_data: Union[ImageAnnotationView, VideoFrameAnnotationView]


class AnnotationWithPayloadAndCountView(BaseModel):
    """Response model for counted annotations with payload."""

    model_config = ConfigDict(populate_by_name=True)

    annotations: List[AnnotationWithPayloadView] = PydanticField(..., alias="data")
    total_count: int
    next_cursor: Optional[int] = PydanticField(None, alias="nextCursor")
