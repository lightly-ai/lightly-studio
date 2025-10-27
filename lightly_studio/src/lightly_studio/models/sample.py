"""This module defines the Sample model for the application."""

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, List, Optional
from uuid import UUID, uuid4

from sqlalchemy.orm import Mapped, Session
from sqlmodel import Field, Relationship, SQLModel

from lightly_studio.resolvers import metadata_resolver

if TYPE_CHECKING:
    from lightly_studio.models.metadata import (
        SampleMetadataTable,
        SampleMetadataView,
    )
    from lightly_studio.models.sample_embedding import SampleEmbeddingTable
    from lightly_studio.models.tag import TagTable
    from lightly_studio.models.caption import CaptionTable, CaptionView
else:
    TagTable = object
    SampleEmbeddingTable = object
    SampleMetadataTable = object
    SampleMetadataView = object
    CaptionTable = object
    CaptionView = object


class SampleTagLinkTable(SQLModel, table=True):
    """Model to define links between Sample and Tag Many-to-Many."""

    sample_id: Optional[UUID] = Field(
        default=None, foreign_key="sample.sample_id", primary_key=True
    )
    tag_id: Optional[UUID] = Field(default=None, foreign_key="tag.tag_id", primary_key=True)


class SampleBase(SQLModel):
    """Base class for the Sample model."""

    """The dataset ID to which the sample belongs."""
    dataset_id: Optional[UUID] = Field(default=None, foreign_key="dataset.dataset_id")


class SampleCreate(SampleBase):
    """Sample class when inserting."""


class SampleTable(SampleBase, table=True):
    """This class defines the Sample model."""

    __tablename__ = "sample"
    sample_id: UUID = Field(default_factory=uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), index=True)
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )

    tags: Mapped[List["TagTable"]] = Relationship(
        back_populates="samples", link_model=SampleTagLinkTable
    )
    embeddings: Mapped[List["SampleEmbeddingTable"]] = Relationship(back_populates="sample")
    metadata_dict: "SampleMetadataTable" = Relationship(back_populates="sample")
    captions: Mapped[List["CaptionTable"]] = Relationship(
        back_populates="sample",
    )

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


class SampleView(SampleBase):
    """This class defines the Sample view model."""

    dataset_id: UUID

    sample_id: UUID
    created_at: datetime
    updated_at: datetime

    tags: List["TagTable"] = []
    metadata_dict: Optional["SampleMetadataView"] = None
    captions: List[CaptionView] = []
