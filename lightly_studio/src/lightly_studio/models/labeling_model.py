"""This module defines the labeling model servers that a dataset saves."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, SQLModel


class LabelingModelBase(SQLModel):
    """Base class for a labeling model on a remote server."""

    dataset_id: UUID = Field(foreign_key="dataset.dataset_id", index=True)
    model_id: str
    url: str
    # Secret: `repr=False` keeps it out of logged rows, and it must never reach a response model.
    api_key: str | None = Field(default=None, repr=False)


class LabelingModelCreate(LabelingModelBase):
    """Model used for saving a labeling model on a remote server."""


class LabelingModelTable(LabelingModelBase, table=True):
    """A labeling model on a remote server, saved in a dataset."""

    __tablename__ = "labeling_model"
    __table_args__ = (UniqueConstraint("dataset_id", "model_id", name="unique_labeling_model_id"),)
    labeling_model_id: UUID = Field(default_factory=uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), index=True)
