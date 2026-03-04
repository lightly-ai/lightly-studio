"""Group table definition."""

from typing import Optional, Union
from uuid import UUID

from pydantic import BaseModel, ConfigDict
from pydantic import Field as PydanticField
from sqlalchemy.orm import Mapped
from sqlmodel import Field, Relationship, SQLModel

from lightly_studio.models.collection import ComponentCollectionView
from lightly_studio.models.image import ImageTable, ImageView
from lightly_studio.models.sample import SampleTable, SampleView
from lightly_studio.models.video import FrameView, VideoTable, VideoView


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
      sample belongs to a component collection.
    - Group relationship (via SampleGroupLinkTable): The component is linked to a parent group
      sample through the SampleGroupLinkTable join table, where the component is referenced
      by sample_id and the parent group by parent_sample_id.
    - Content relationship: Each sample's actual content (media file information) is stored in
      either ImageTable or VideoTable, linked via sample_id as a foreign key. A sample_id exists
      in SampleTable and exactly one of ImageTable/VideoTable - never both.
    """

    collection: ComponentCollectionView
    details: Union[ImageView, VideoView, None] = None

    @classmethod
    def from_image_table(
        cls,
        image: "ImageTable",
        collection: ComponentCollectionView,
        similarity_score: Optional[float] = None,
    ) -> "GroupComponentView":
        """Create a GroupComponentView from an ImageTable.

        Args:
            image: ImageTable instance with loaded sample relationship.
            collection: ComponentCollectionView instance with collection data.

        Returns:
            GroupComponentView with image data populated.
        """
        # TODO(Kondrat 03/25): Replace manual ImageView construction with
        # ImageView.from_image_table() once that factory method is implemented
        return cls(
            collection=collection,
            details=ImageView.from_image_table(image=image, similarity_score=similarity_score),
        )

    @classmethod
    def from_video_table(
        cls,
        video: "VideoTable",
        collection: ComponentCollectionView,
        similarity_score: Optional[float] = None,
        frame: Optional["FrameView"] = None,
    ) -> "GroupComponentView":
        """Create a GroupComponentView from a VideoTable.

        Args:
            video: VideoTable instance with loaded sample relationship.
            collection: ComponentCollectionView instance with collection data.

        Returns:
            GroupComponentView with video data populated.
        """
        # TODO(Kondrat 03/25): Replace manual VideoView construction with
        # VideoView.from_video_table() once that factory method is implemented
        return cls(
            collection=collection,
            details=VideoView(
                sample_id=video.sample_id,
                file_name=video.file_name,
                file_path_abs=video.file_path_abs,
                width=video.width,
                height=video.height,
                fps=video.fps,
                duration_s=video.duration_s,
                sample=SampleView.model_validate(video.sample),
                similarity_score=similarity_score,
                frame=frame,
            ),
        )
