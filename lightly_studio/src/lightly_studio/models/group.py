"""Group table definition."""

from uuid import UUID

from sqlalchemy.orm import Mapped
from sqlmodel import Field, Relationship, SQLModel

from lightly_studio.models.sample import SampleTable


class GroupTable(SQLModel, table=True):
    """This class defines the Group model."""

    __tablename__ = "group"
    sample_id: UUID = Field(foreign_key="sample.sample_id", primary_key=True)

    sample: Mapped["SampleTable"] = Relationship(
        sa_relationship_kwargs={
            "lazy": "select",
            "foreign_keys": "[GroupTable.sample_id]",
        },
    )


class SampleGroupLinkTable(SQLModel, table=True):
    """Model to define links between Group and Sample One-to-Many."""

    sample_id: UUID = Field(foreign_key="sample.sample_id", primary_key=True)
    parent_sample_id: UUID = Field(foreign_key="group.sample_id")
