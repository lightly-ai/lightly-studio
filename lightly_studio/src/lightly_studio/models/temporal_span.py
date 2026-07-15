"""Temporal span model.

A temporal span stores start and end times in seconds for sample-backed
entities.
"""

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy.orm import Mapped
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from lightly_studio.models.sample import SampleTable
else:
    SampleTable = object


class TemporalSpanTable(SQLModel, table=True):
    """Database table model for temporal spans."""

    __tablename__ = "temporal_span"

    sample_id: UUID = Field(foreign_key="sample.sample_id", primary_key=True)

    start_time_s: float
    end_time_s: float

    sample: Mapped["SampleTable"] = Relationship(
        sa_relationship_kwargs={
            "lazy": "select",
            "foreign_keys": "[TemporalSpanTable.sample_id]",
        },
    )


class TemporalSpanView(SQLModel):
    """API response model for temporal spans."""

    start_time_s: float
    end_time_s: float
