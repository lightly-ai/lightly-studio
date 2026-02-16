"""Group table definition."""

from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict
from pydantic import Field as PydanticField
from sqlalchemy.orm import Mapped
from sqlmodel import Field, Relationship, SQLModel

from lightly_studio.models.sample import SampleTable, SampleView


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


class GroupView(BaseModel):
    """This class defines the Group view model."""

    sample_id: UUID
    sample: SampleView
    similarity_score: Optional[float] = None
    # First sample's image or video for display in grid
    first_sample_image: Optional["ImageView"] = None
    first_sample_video: Optional["VideoView"] = None


class GroupViewsWithCount(BaseModel):
    """Result of getting all group views."""

    model_config = ConfigDict(populate_by_name=True)

    samples: List[GroupView] = PydanticField(..., alias="data")
    total_count: int
    next_cursor: Optional[int] = PydanticField(None, alias="nextCursor")


# Import at the bottom to avoid circular imports
from lightly_studio.models.image import ImageView  # noqa: E402
from lightly_studio.models.video import VideoView  # noqa: E402
