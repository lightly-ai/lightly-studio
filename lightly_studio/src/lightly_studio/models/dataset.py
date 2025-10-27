"""This module contains the Dataset model and related enumerations."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime, timezone
from typing import cast
from uuid import UUID, uuid4

from sqlalchemy.orm import Session as SQLAlchemySession
from sqlmodel import Field, Session, SQLModel

from lightly_studio.api.routes.api.validators import Paginated
from lightly_studio.models.sample import SampleTable
from lightly_studio.resolvers import sample_resolver
from lightly_studio.resolvers.samples_filter import SampleFilter


class DatasetBase(SQLModel):
    """Base class for the Dataset model."""

    name: str = Field(unique=True, index=True)


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

    __tablename__ = "datasets"
    dataset_id: UUID = Field(default_factory=uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), index=True)
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )

    def get_samples(
        self,
        offset: int = 0,
        limit: int | None = None,
        filters: SampleFilter | None = None,
        text_embedding: list[float] | None = None,
        sample_ids: list[UUID] | None = None,
    ) -> Sequence[SampleTable]:
        """Retrieve samples for this dataset with optional filtering.

        Just passes the parameters to the sample resolver.

        Args:
            offset: Offset for pagination.
            limit: Limit for pagination.
            filters: Optional filters to apply.
            text_embedding: Optional text embedding for filtering.
            sample_ids: Optional list of sample IDs to filter by.

        Returns:
            A sequence of SampleTable objects.
        """
        # Get the session from the instance.
        # SQLAlchemy Session is compatible with SQLModel's Session at runtime,
        # but we have to help mypy.
        session = cast(Session, SQLAlchemySession.object_session(self))
        if session is None:
            raise RuntimeError("No database session found for this instance")

        pagination = None
        if limit is not None:
            pagination = Paginated(offset=offset, limit=limit)

        return sample_resolver.get_all_by_dataset_id(
            session=session,
            dataset_id=self.dataset_id,
            pagination=pagination,
            filters=filters,
            text_embedding=text_embedding,
            sample_ids=sample_ids,
        ).samples
