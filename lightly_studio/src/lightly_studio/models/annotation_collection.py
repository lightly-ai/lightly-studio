"""AnnotationCollection model — a named group of annotations (GT or predictions)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel
from sqlmodel import Field, SQLModel


class AnnotationCollectionTable(SQLModel, table=True):
    """Metadata for a named group of annotations sharing a common origin.

    Each entry wraps exactly one CollectionTable row (sample_type=ANNOTATION) via
    `collection_id`. Annotations in that collection are the actual annotation records.
    """

    __tablename__ = "annotation_collection"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    dataset_id: UUID = Field(foreign_key="dataset.dataset_id", index=True)
    collection_id: UUID = Field(foreign_key="collection.collection_id", unique=True, index=True)
    name: str = Field(index=True)
    is_ground_truth: bool = False
    processed_sample_count: Optional[int] = None
    notes: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class AnnotationCollectionCreate(BaseModel):
    """Input model for creating an annotation collection."""

    name: str
    is_ground_truth: bool = False
    processed_sample_count: Optional[int] = None
    notes: Optional[str] = None


class AnnotationCollectionView(BaseModel):
    """Response model for an annotation collection."""

    model_config = {"from_attributes": True}

    id: UUID
    dataset_id: UUID
    collection_id: UUID
    name: str
    is_ground_truth: bool
    processed_sample_count: Optional[int]
    notes: Optional[str]
    created_at: datetime
