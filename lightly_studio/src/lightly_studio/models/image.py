"""This module defines the User model for the application."""

from datetime import datetime, timezone
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict
from pydantic import Field as PydanticField
from sqlalchemy.orm import Mapped
from sqlmodel import Field, Relationship, SQLModel

from lightly_studio.models.annotation.annotation_base import AnnotationView
from lightly_studio.models.caption import CaptionView
from lightly_studio.models.collection import SampleType
from lightly_studio.models.metadata import SampleMetadataView
from lightly_studio.models.sample import SampleTable, SampleView


class ImageBase(SQLModel):
    """Base class for the Image model."""

    """The name of the image file."""
    file_name: str

    """The width of the image in pixels."""
    width: int

    """The height of the image in pixels."""
    height: int

    """The collection image path."""
    file_path_abs: str = Field(default=None)


class ImageCreate(ImageBase):
    """Image class when inserting."""


class ImageTable(ImageBase, table=True):
    """This class defines the Image model."""

    __tablename__ = "image"
    sample_id: UUID = Field(foreign_key="sample.sample_id", primary_key=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), index=True)
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )
    sample: Mapped["SampleTable"] = Relationship()


TagKind = Literal[
    "sample",
    "annotation",
]


class ImageView(BaseModel):
    """Image class when retrieving."""

    class ImageViewTag(BaseModel):
        """Tag view inside Image view."""

        tag_id: UUID
        name: str
        kind: TagKind
        created_at: datetime
        updated_at: datetime

    type: SampleType = SampleType.IMAGE
    file_name: str
    file_path_abs: str
    sample_id: UUID
    annotations: list["AnnotationView"]
    width: int
    height: int

    sample: SampleView

    # TODO(Michal, 10/2025): Add SampleView to ImageView, don't expose these fields directly.
    tags: list[ImageViewTag]
    metadata_dict: Optional["SampleMetadataView"] = None
    captions: list[CaptionView] = []
    similarity_score: Optional[float] = None

    @classmethod
    def from_image_table(
        cls, image: "ImageTable", similarity_score: Optional[float] = None
    ) -> "ImageView":
        """Convert an ImageTable to an ImageView."""
        return cls(
            file_name=image.file_name,
            file_path_abs=image.file_path_abs,
            sample_id=image.sample_id,
            annotations=[
                AnnotationView.from_annotation_table(annotation=annotation)
                for annotation in image.sample.annotations
            ],
            captions=[CaptionView.model_validate(caption) for caption in image.sample.captions],
            tags=[
                ImageView.ImageViewTag(
                    tag_id=tag.tag_id,
                    name=tag.name,
                    kind=tag.kind,
                    created_at=tag.created_at,
                    updated_at=tag.updated_at,
                )
                for tag in image.sample.tags
            ],
            metadata_dict=SampleMetadataView.model_validate(image.sample.metadata_dict)
            if image.sample.metadata_dict
            else None,
            width=image.width,
            height=image.height,
            sample=SampleView.model_validate(image.sample),
            similarity_score=similarity_score,
        )


class ImageViewsWithCount(BaseModel):
    """Response model for counted images."""

    model_config = ConfigDict(populate_by_name=True)

    samples: list[ImageView] = PydanticField(..., alias="data")
    total_count: int
    next_cursor: Optional[int] = PydanticField(None, alias="nextCursor")
