"""This module defines the caption model."""

from datetime import datetime, timezone
from typing import TYPE_CHECKING, List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict
from pydantic import Field as PydanticField
from sqlalchemy.orm import Mapped
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from lightly_studio.models.sample import ImageTable


class CaptionTable(SQLModel, table=True):
    """Class for caption model."""

    __tablename__ = "caption"

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), index=True)

    caption_id: UUID = Field(default_factory=uuid4, primary_key=True)
    dataset_id: UUID = Field(foreign_key="dataset.dataset_id")
    sample_id: UUID = Field(foreign_key="sample.sample_id")

    sample: Mapped[Optional["ImageTable"]] = Relationship(
        back_populates="captions",
        sa_relationship_kwargs={"lazy": "select"},
    )

    text: str


class CaptionCreate(SQLModel):
    """Input model for creating captions."""

    dataset_id: UUID
    sample_id: UUID
    text: str


class CaptionImageView(SQLModel):
    """Sample class for caption view."""

    file_path_abs: str
    file_name: str
    dataset_id: UUID
    sample_id: UUID


class CaptionView(SQLModel):
    """Response model for caption."""

    sample_id: UUID
    dataset_id: UUID
    caption_id: UUID
    text: str


class CaptionDetailsView(CaptionView):
    """Response model for caption."""

    sample: CaptionImageView


class CaptionsListView(BaseModel):
    """Response model for counted captions."""

    model_config = ConfigDict(populate_by_name=True)

    captions: List[CaptionDetailsView] = PydanticField(..., alias="data")
    total_count: int
    next_cursor: Optional[int] = PydanticField(..., alias="nextCursor")
