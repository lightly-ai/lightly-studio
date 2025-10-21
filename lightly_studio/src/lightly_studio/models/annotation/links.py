"""This module defines the base annotation model."""

from typing import Optional
from uuid import UUID

from sqlmodel import Field, SQLModel


class AnnotationTagLinkTable(SQLModel, table=True):
    """Model defines the link table between annotations and tags."""

    annotation_id: Optional[UUID] = Field(
        default=None,
        foreign_key="annotation_base.annotation_id",
        primary_key=True,
    )
    tag_id: Optional[UUID] = Field(default=None, foreign_key="tags.tag_id", primary_key=True)
