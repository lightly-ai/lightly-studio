"""This module contains the Collection model and related enumerations."""

from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, Relationship, SQLModel


class SampleType(str, Enum):
    """The type of samples in the collection."""

    VIDEO = "video"
    VIDEO_FRAME = "video_frame"
    IMAGE = "image"
    ANNOTATION = "annotation"
    CAPTION = "caption"
    GROUP = "group"
    MCAP = "mcap"
    SEQUENCE = "sequence"


class CollectionBase(SQLModel):
    """Base class for the Collection model."""

    name: str = Field(index=True)
    parent_collection_id: Optional[UUID] = Field(
        default=None,
        foreign_key="collection.collection_id",
        index=True,
    )
    sample_type: SampleType


class CollectionTable(CollectionBase, table=True):
    """This class defines the Collection model."""

    __tablename__ = "collection"
    __table_args__ = (
        # Does not cover root collections: NULL parents compare as distinct. Postgres
        # closes that gap with a partial unique index from migration 4f6a7b8c9d0e,
        # which lives there because DuckDB cannot create partial indexes.
        UniqueConstraint("name", "parent_collection_id", name="unique_collection"),
    )
    collection_id: UUID = Field(default_factory=uuid4, primary_key=True)
    dataset_id: UUID = Field(index=True, foreign_key="dataset.dataset_id")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), index=True)
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    parent: Optional["CollectionTable"] = Relationship(
        back_populates="children",
        sa_relationship_kwargs={"remote_side": "CollectionTable.collection_id"},
    )
    children: list["CollectionTable"] = Relationship(
        back_populates="parent",
        sa_relationship_kwargs={"lazy": "select"},
    )
    group_component_definition: Optional["GroupComponentDefinitionTable"] = Relationship()
    # TODO(lukas, 3/2026): add a relationship to DatasetTable


class CollectionCreate(CollectionBase):
    """Collection class when inserting."""


class CollectionView(CollectionBase):
    """Collection class when retrieving."""

    collection_id: UUID
    dataset_id: UUID
    created_at: datetime
    updated_at: datetime
    group_component_definition: Optional["GroupComponentDefinitionView"] = None
    children: list["CollectionView"] = []


class ComponentCollectionView(CollectionBase):
    """Collection view for group components."""

    group_component_name: str
    group_component_index: int

    @classmethod
    def from_collection_table(cls, collection: "CollectionTable") -> "ComponentCollectionView":
        """Create a ComponentCollectionView from a CollectionTable."""
        definition = collection.group_component_definition
        return cls(
            name=collection.name,
            parent_collection_id=collection.parent_collection_id,
            sample_type=collection.sample_type,
            group_component_name=definition.group_component_name if definition else "",
            group_component_index=definition.group_component_index if definition else 0,
        )


class CollectionViewWithCount(CollectionView):
    """Collection view with total sample count."""

    total_sample_count: int


class CollectionOverviewView(SQLModel):
    """Collection view for dashboard display."""

    collection_id: UUID
    name: str
    sample_type: SampleType
    created_at: datetime
    total_sample_count: int


class AnnotationCollectionView(SQLModel):
    """Slim collection view used for the annotation collections menu."""

    collection_id: UUID
    name: str
    # Distinct annotation type values present in the collection (e.g.
    # ["object_detection"]). Typed as plain strings to avoid importing
    # AnnotationType here, which would create a circular import with
    # annotation_base. Used by the GUI to filter sources by evaluation task.
    annotation_types: list[str] = Field(default_factory=list)


# Import at the bottom to:
# 1) avoid circular imports
# 2) satisfy mypy
# 3) include types in schema generation
from lightly_studio.models.group_component_definition import (  # noqa: E402
    GroupComponentDefinitionTable,
    GroupComponentDefinitionView,
)
