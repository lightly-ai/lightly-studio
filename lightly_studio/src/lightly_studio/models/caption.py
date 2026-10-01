"""This module defines the caption model."""

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Mapped
from sqlmodel import Field, Relationship, SQLModel

from lightly_studio.models.sample import SampleTable
from lightly_studio.models.temporal_span import TemporalSpanTable, TemporalSpanView


class CaptionTable(SQLModel, table=True):
    """Class for caption model."""

    __tablename__ = "caption"

    sample_id: UUID = Field(foreign_key="sample.sample_id", primary_key=True)
    parent_sample_id: UUID = Field(foreign_key="sample.sample_id", index=True)
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

    # Optional temporal bounds for this caption's sample.
    temporal_span_details: Mapped[Optional["TemporalSpanTable"]] = Relationship(
        sa_relationship_kwargs={
            "primaryjoin": "CaptionTable.sample_id == foreign(TemporalSpanTable.sample_id)",
            "lazy": "selectin",
            "uselist": False,
            "viewonly": True,
        },
    )


class CaptionCreate(SQLModel):
    """Input model for creating captions."""

    parent_sample_id: UUID
    text: str

    # Optional temporal bounds for the caption's sample.
    start_time_s: Optional[float] = None
    end_time_s: Optional[float] = None


class CaptionView(SQLModel):
    """Response model for caption."""

    parent_sample_id: UUID
    sample_id: UUID
    text: str
    temporal_span_details: Optional[TemporalSpanView] = None
