"""Group table definition."""

from typing import TYPE_CHECKING, Optional, Union
from uuid import UUID

from pydantic import BaseModel, ConfigDict
from pydantic import Field as PydanticField
from sqlalchemy.orm import Mapped
from sqlmodel import Field, Relationship, SQLModel

from lightly_studio.models.image import ImageView
from lightly_studio.models.sample import SampleTable, SampleView
from lightly_studio.models.video import VideoView

if TYPE_CHECKING:
    from lightly_studio.models.image import ImageTable
    from lightly_studio.models.video import VideoTable


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
    group_preview: Union[ImageView, VideoView, None] = None
    sample_count: int


class GroupViewsWithCount(BaseModel):
    """Result of getting all group views."""

    model_config = ConfigDict(populate_by_name=True)

    samples: list[GroupView] = PydanticField(..., alias="data")
    total_count: int
    next_cursor: Optional[int] = PydanticField(None, alias="nextCursor")


class GroupComponentView(BaseModel):
    """GroupComponentView representation.

    Represents a group component with its name and associated media (image or video).
    A component is always either an image or a video, never both.

    A "GroupComponent" is a sample that has the following relationships:
    - Collection relationship (samples.collection_id → collections.collection_id): The component
      belongs to a collection/dataset.
    - Group relationship (via SampleGroupLinkTable): The component is linked to a parent group
      sample through the SampleGroupLinkTable join table, where the component is referenced
      by sample_id and the parent group by parent_sample_id.
    - Content relationship: Each sample's actual content (media file information) is stored in
      either ImageTable or VideoTable, linked via sample_id as a foreign key. A sample_id exists
      in SampleTable and exactly one of ImageTable/VideoTable - never both. 
    """

    component_name: str
    image: Optional[ImageView] = None
    video: Optional[VideoView] = None

    @classmethod
    def from_image_table(cls, image: "ImageTable", component_name: str) -> "GroupComponentView":
        """Create a GroupComponentView from an ImageTable.

        Args:
            image: ImageTable instance with loaded sample relationship.
            component_name: Name of the component from the collection.

        Returns:
            GroupComponentView with image data populated.
        """
        # TODO(Kondrat 03/25): Replace manual ImageView construction with
        # ImageView.from_image_table() once that factory method is implemented
        return cls(
            component_name=component_name,
            image=ImageView.from_image_table(image=image),
            video=None,
        )

    @classmethod
    def from_video_table(cls, video: "VideoTable", component_name: str) -> "GroupComponentView":
        """Create a GroupComponentView from a VideoTable.

        Args:
            video: VideoTable instance with loaded sample relationship.
            component_name: Name of the component from the collection.

        Returns:
            GroupComponentView with video data populated.
        """
        # TODO(Kondrat 03/25): Replace manual VideoView construction with
        # VideoView.from_video_table() once that factory method is implemented
        return cls(
            component_name=component_name,
            image=None,
            video=VideoView(
                sample_id=video.sample_id,
                file_name=video.file_name,
                file_path_abs=video.file_path_abs,
                width=video.width,
                height=video.height,
                fps=video.fps,
                duration_s=video.duration_s,
                sample=SampleView.model_validate(video.sample),
            ),
        )
