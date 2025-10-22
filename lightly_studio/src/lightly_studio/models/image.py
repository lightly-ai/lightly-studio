"""This module defines the User model for the application."""

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, List, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict
from pydantic import Field as PydanticField
from sqlalchemy.orm import Mapped, Session
from sqlmodel import Field, Relationship, SQLModel

from lightly_studio.models.annotation.annotation_base import AnnotationView
from lightly_studio.models.caption import CaptionView
from lightly_studio.resolvers import metadata_resolver

if TYPE_CHECKING:
    from lightly_studio.models.annotation.annotation_base import (
        AnnotationBaseTable,
    )
    from lightly_studio.models.caption import CaptionTable
    from lightly_studio.models.metadata import (
        SampleMetadataTable,
        SampleMetadataView,
    )
    from lightly_studio.models.sample import SampleTable
    from lightly_studio.models.sample_embedding import SampleEmbeddingTable
else:
    AnnotationBaseTable = object
    CaptionTable = object
    SampleEmbeddingTable = object
    SampleMetadataTable = object
    SampleTable = object
    SampleMetadataView = object


class ImageBase(SQLModel):
    """Base class for the Image model."""

    """The name of the image file."""
    file_name: str

    """The width of the image in pixels."""
    width: int

    """The height of the image in pixels."""
    height: int

    """The dataset ID to which the sample belongs."""
    dataset_id: UUID = Field(default=None, foreign_key="dataset.dataset_id")

    """The dataset image path."""
    file_path_abs: str = Field(default=None, unique=True)


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
    annotations: Mapped[List["AnnotationBaseTable"]] = Relationship(
        back_populates="sample",
    )
    captions: Mapped[List["CaptionTable"]] = Relationship(
        back_populates="sample",
    )

    embeddings: Mapped[List["SampleEmbeddingTable"]] = Relationship(back_populates="sample")
    metadata_dict: "SampleMetadataTable" = Relationship(back_populates="sample")

    sample: Mapped["SampleTable"] = Relationship()

    # TODO(Michal, 9/2025): Remove this function in favour of Sample.metadata.
    def __getitem__(self, key: str) -> Any:
        """Provides dict-like access to sample metadata.

        Args:
            key: The metadata key to access.

        Returns:
            The metadata value for the given key, or None if the key doesn't
            exist.
        """
        if self.metadata_dict is None:
            return None
        return self.metadata_dict.get_value(key)

    # TODO(Michal, 9/2025): Remove this function in favour of Sample.metadata.
    def __setitem__(self, key: str, value: Any) -> None:
        """Sets a metadata key-value pair for this sample.

        Args:
            key: The metadata key.
            value: The metadata value.

        Note:
            If the sample has no metadata, a new Metadata Table instance
            will be created. Changes are automatically committed to the
            database.

        Raises:
            RuntimeError: If no database session is found.
        """
        # Get the session from the instance
        session = Session.object_session(self)
        if session is None:
            raise RuntimeError("No database session found for this instance")

        # Use metadata_resolver to handle the database operations.
        # Added type: ignore to avoid type checking issues. SQLAlchemy and
        # SQLModel sessions are compatible at runtime but have different type
        # annotations.
        metadata_resolver.set_value_for_sample(
            session=session,  # type: ignore[arg-type]
            sample_id=self.sample_id,
            key=key,
            value=value,
        )


TagKind = Literal[
    "sample",
    "annotation",
]


class ImageView(SQLModel):
    """Image class when retrieving."""

    class ImageViewTag(SQLModel):
        """Tag view inside Image view."""

        tag_id: UUID
        name: str
        kind: TagKind
        created_at: datetime
        updated_at: datetime

    """The name of the image file."""
    file_name: str
    file_path_abs: str
    sample_id: UUID
    dataset_id: UUID
    annotations: List["AnnotationView"]
    captions: List[CaptionView] = []
    tags: List[ImageViewTag]
    metadata_dict: Optional["SampleMetadataView"] = None
    width: int
    height: int


class ImageViewsWithCount(BaseModel):
    """Response model for counted images."""

    model_config = ConfigDict(populate_by_name=True)

    samples: List[ImageView] = PydanticField(..., alias="data")
    total_count: int
    next_cursor: Optional[int] = PydanticField(None, alias="nextCursor")
