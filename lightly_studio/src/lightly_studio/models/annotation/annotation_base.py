"""This module defines the base annotation model."""

from datetime import datetime, timezone
from enum import Enum
from typing import TYPE_CHECKING, List, Optional, Union
from uuid import UUID

from pydantic import BaseModel, ConfigDict
from pydantic import Field as PydanticField
from sqlalchemy.orm import Mapped
from sqlmodel import Field, Relationship, SQLModel

from lightly_studio.models.annotation.links import AnnotationTagLinkTable
from lightly_studio.models.annotation.object_detection import (
    ObjectDetectionAnnotationTable,
    ObjectDetectionAnnotationView,
)
from lightly_studio.models.annotation.segmentation import (
    SegmentationAnnotationTable,
    SegmentationAnnotationView,
)
from lightly_studio.models.collection import SampleType
from lightly_studio.models.sample import SampleTable
from lightly_studio.models.video import VideoFrameTable

if TYPE_CHECKING:
    from lightly_studio.models.annotation_label import (
        AnnotationLabelTable,
    )
    from lightly_studio.models.image import ImageTable
    from lightly_studio.models.tag import TagTable

else:
    TagTable = object
    AnnotationLabelTable = object
    ImageTable = object


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

    """ Details about instance and semantic segmentation. """
    segmentation_details: Mapped[Optional["SegmentationAnnotationTable"]] = Relationship(
        back_populates="annotation_base",
        sa_relationship_kwargs={"lazy": "select"},
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
    segmentation_details: Optional[SegmentationAnnotationView] = None

    tags: List[AnnotationViewTag] = []


class AnnotationViewsWithCount(BaseModel):
    """Response model for counted annotations."""

    model_config = ConfigDict(populate_by_name=True)

    annotations: List[AnnotationView] = PydanticField(..., alias="data")
    total_count: int
    next_cursor: Optional[int] = PydanticField(..., alias="nextCursor")


class SampleAnnotationView(BaseModel):
    """Response model for sample annotation view."""

    model_config = ConfigDict(populate_by_name=True)

    collection_id: UUID


class ImageAnnotationView(BaseModel):
    """Response model for image annotation view."""

    model_config = ConfigDict(populate_by_name=True)

    sample_id: UUID
    file_path_abs: str
    width: int
    height: int
    sample: SampleAnnotationView


class VideoAnnotationView(BaseModel):
    """Response model for video view."""

    height: int
    width: int
    file_path_abs: str


class VideoFrameAnnotationView(BaseModel):
    """Response model for video frame annotation view."""

    model_config = ConfigDict(populate_by_name=True)

    sample_id: UUID
    video: VideoAnnotationView


class AnnotationWithPayloadView(BaseModel):
    """Response model for annotation with payload."""

    model_config = ConfigDict(populate_by_name=True)

    parent_sample_type: SampleType
    annotation: AnnotationView
    parent_sample_data: Union[ImageAnnotationView, VideoFrameAnnotationView]


class AnnotationWithPayloadAndCountView(BaseModel):
    """Response model for counted annotations with payload."""

    model_config = ConfigDict(populate_by_name=True)

    annotations: List[AnnotationWithPayloadView] = PydanticField(..., alias="data")
    total_count: int
    next_cursor: Optional[int] = PydanticField(None, alias="nextCursor")


class SampleAnnotationDetailsView(BaseModel):
    """Response model for sample annotation details view."""

    sample_id: UUID
    collection_id: UUID
    tags: List["TagTable"] = []

    @classmethod
    def from_sample_table(cls, sample: SampleTable) -> "SampleAnnotationDetailsView":
        """Convert sample table to sample annotation details view."""
        return SampleAnnotationDetailsView(
            sample_id=sample.sample_id,
            tags=sample.tags,
            collection_id=sample.collection_id,
        )


class ImageAnnotationDetailsView(BaseModel):
    """Response model for image annotation details view."""

    model_config = ConfigDict(populate_by_name=True)

    file_path_abs: str
    file_name: str
    width: int
    height: int
    sample: SampleAnnotationDetailsView

    @classmethod
    def from_image_table(cls, image: ImageTable) -> "ImageAnnotationDetailsView":
        """Convert image table to image annotation details view."""
        return ImageAnnotationDetailsView(
            height=image.height,
            width=image.width,
            file_path_abs=image.file_path_abs,
            file_name=image.file_name,
            sample=SampleAnnotationDetailsView.from_sample_table(image.sample),
        )


class VideoFrameAnnotationDetailsView(BaseModel):
    """Response model for video frame annotation view."""

    model_config = ConfigDict(populate_by_name=True)

    sample_id: UUID
    frame_number: int
    frame_timestamp_s: float

    video: VideoAnnotationView
    sample: SampleAnnotationDetailsView

    @classmethod
    def from_video_frame_table(
        cls, video_frame: VideoFrameTable
    ) -> "VideoFrameAnnotationDetailsView":
        """Convert video frame table to video frame annotation details view."""
        return VideoFrameAnnotationDetailsView(
            sample_id=video_frame.sample_id,
            frame_number=video_frame.frame_number,
            frame_timestamp_s=video_frame.frame_timestamp_s,
            video=VideoAnnotationView(
                width=video_frame.video.width,
                height=video_frame.video.height,
                file_path_abs=video_frame.video.file_path_abs,
            ),
            sample=SampleAnnotationDetailsView.from_sample_table(video_frame.sample),
        )


class AnnotationDetailsWithPayloadView(BaseModel):
    """Response model for annotation details with payload."""

    model_config = ConfigDict(populate_by_name=True)

    parent_sample_type: SampleType
    annotation: AnnotationView
    parent_sample_data: Union[ImageAnnotationDetailsView, VideoFrameAnnotationDetailsView]
