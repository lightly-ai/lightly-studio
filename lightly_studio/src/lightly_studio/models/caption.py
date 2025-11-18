"""This module defines the caption model."""

from datetime import datetime, timezone
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy.orm import Mapped
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from lightly_studio.models.sample import SampleTable


class CaptionTable(SQLModel, table=True):
    """Class for caption model."""

    __tablename__ = "caption"

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), index=True)

    # TODO(Michal, 11/2025): Link sample_id to SampleTable.
    sample_id: UUID = Field(default_factory=uuid4, primary_key=True)
    parent_sample_id: UUID = Field(foreign_key="sample.sample_id")
    dataset_id: UUID = Field(foreign_key="dataset.dataset_id")

    parent_sample: Mapped["SampleTable"] = Relationship(
        back_populates="captions",
        sa_relationship_kwargs={
            "lazy": "select",
            "foreign_keys": "[CaptionTable.parent_sample_id]",
        },
    )

    text: str


class CaptionCreate(SQLModel):
    """Input model for creating captions."""

    dataset_id: UUID
    parent_sample_id: UUID
    text: str


class CaptionView(SQLModel):
    """Response model for caption."""

    parent_sample_id: UUID
    dataset_id: UUID
    sample_id: UUID
    text: str
