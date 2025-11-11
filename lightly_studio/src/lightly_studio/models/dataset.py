"""This module contains the Dataset model and related enumerations."""

from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional, Sequence, cast
from uuid import UUID, uuid4

from sqlalchemy.orm import Session as SQLAlchemySession
from sqlmodel import Field, Relationship, Session, SQLModel

from lightly_studio.api.routes.api.validators import Paginated
from lightly_studio.models.image import ImageTable
from lightly_studio.resolvers.image_filter import ImageFilter


class SampleType(str, Enum):
    """The type of samples in the dataset."""

    VIDEO = "video"
    VIDEO_FRAME = "video_frame"
    IMAGE = "image"
    IMAGE_ANNOTATION = "image_annotation"


class DatasetBase(SQLModel):
    """Base class for the Dataset model."""

    name: str = Field(unique=True, index=True)
    parent_dataset_id: Optional[UUID] = Field(default=None, foreign_key="dataset.dataset_id")
    sample_type: SampleType


class DatasetCreate(DatasetBase):
    """Dataset class when inserting."""


class DatasetView(DatasetBase):
    """Dataset class when retrieving."""

    dataset_id: UUID
    created_at: datetime
    updated_at: datetime


class DatasetViewWithCount(DatasetView):
    """Dataset view with total sample count."""

    total_sample_count: int


class DatasetTable(DatasetBase, table=True):
    """This class defines the Dataset model."""

    __tablename__ = "dataset"
    dataset_id: UUID = Field(default_factory=uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), index=True)
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    parent: Optional["DatasetTable"] = Relationship(
        back_populates="children",
        sa_relationship_kwargs={"remote_side": "DatasetTable.dataset_id"},
    )
    children: List["DatasetTable"] = Relationship(back_populates="parent")

    def get_samples(
        self,
        offset: int = 0,
        limit: Optional[int] = None,
        filters: Optional[ImageFilter] = None,
        text_embedding: Optional[List[float]] = None,
        sample_ids: Optional[List[UUID]] = None,
    ) -> Sequence[ImageTable]:
        """Retrieve samples for this dataset with optional filtering.

        Just passes the parameters to the sample resolver.

        Args:
            offset: Offset for pagination.
            limit: Limit for pagination.
            filters: Optional filters to apply.
            text_embedding: Optional text embedding for filtering.
            sample_ids: Optional list of sample IDs to filter by.

        Returns:
            A sequence of ImageTable objects.
        """
        # TODO(Michal, 11/2025): Import moved here to avoid circular imports. Remove this function
        # completely in the future in favor of iter(Dataset).
        from lightly_studio.resolvers import image_resolver

        # Get the session from the instance.
        # SQLAlchemy Session is compatible with SQLModel's Session at runtime,
        # but we have to help mypy.
        session = cast(Session, SQLAlchemySession.object_session(self))
        if session is None:
            raise RuntimeError("No database session found for this instance")

        pagination = None
        if limit is not None:
            pagination = Paginated(offset=offset, limit=limit)

        return image_resolver.get_all_by_dataset_id(
            session=session,
            dataset_id=self.dataset_id,
            pagination=pagination,
            filters=filters,
            text_embedding=text_embedding,
            sample_ids=sample_ids,
        ).samples
