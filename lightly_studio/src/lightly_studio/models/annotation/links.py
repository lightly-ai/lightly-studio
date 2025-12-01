"""This module defines the base annotation model."""

from typing import Optional
from uuid import UUID

from sqlmodel import Field, SQLModel


class AnnotationTagLinkTable(SQLModel, table=True):
    """Model defines the link table between annotations and tags."""

    annotation_sample_id: Optional[UUID] = Field(
        default=None,
        foreign_key="annotation_base.sample_id",
        primary_key=True,
    )
    tag_id: Optional[UUID] = Field(default=None, foreign_key="tag.tag_id", primary_key=True)
