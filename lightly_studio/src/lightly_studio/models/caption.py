"""This module defines the caption model."""

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.orm import Mapped
from sqlmodel import Field, Relationship, SQLModel

from lightly_studio.models.sample import SampleTable


class CaptionTable(SQLModel, table=True):
    """Class for caption model."""

    __tablename__ = "caption"

    sample_id: UUID = Field(foreign_key="sample.sample_id", primary_key=True)
    parent_sample_id: UUID = Field(foreign_key="sample.sample_id")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), index=True)
    text: str

    sample: Mapped["SampleTable"] = Relationship(
        sa_relationship_kwargs={
            "lazy": "select",
            "foreign_keys": "[CaptionTable.sample_id]",
        },
    )
    parent_sample: Mapped["SampleTable"] = Relationship(
        back_populates="captions",
        sa_relationship_kwargs={
            "lazy": "select",
            "foreign_keys": "[CaptionTable.parent_sample_id]",
        },
    )


class CaptionCreate(SQLModel):
    """Input model for creating captions."""

    parent_sample_id: UUID
    text: str


class CaptionView(SQLModel):
    """Response model for caption."""

    parent_sample_id: UUID
    sample_id: UUID
    text: str
