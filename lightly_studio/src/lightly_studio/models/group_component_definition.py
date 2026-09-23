"""This module contains the GroupComponentDefinition model."""

from uuid import UUID

from sqlmodel import Field, SQLModel


class GroupComponentDefinitionBase(SQLModel):
    """Base class for the GroupComponentDefinition model."""

    group_component_name: str
    group_component_index: int


class GroupComponentDefinitionTable(GroupComponentDefinitionBase, table=True):
    """Group-specific metadata for a component collection.

    A component collection is a child of a GROUP collection representing one named
    slot within the group (e.g. "front_camera"). One row per component collection;
    the ``collection_id`` primary key enforces at most one definition per collection.
    """

    __tablename__ = "group_component_definition"

    collection_id: UUID = Field(foreign_key="collection.collection_id", primary_key=True)


class GroupComponentDefinitionView(GroupComponentDefinitionBase):
    """GroupComponentDefinition class when retrieving."""
