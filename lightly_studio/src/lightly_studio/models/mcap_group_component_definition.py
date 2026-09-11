"""This module contains the McapGroupComponentDefinition model.

1:1 extension of ``group_component_definition``.  Video vs point cloud is ``mcap_data_type``
on this table.
"""

from __future__ import annotations

from enum import Enum
from uuid import UUID

from sqlmodel import Field, SQLModel


class McapDataType(str, Enum):
    """Kind of MCAP data stored in a group component slot."""

    VIDEO_FRAME = "video_frame"
    POINT_CLOUD = "point_cloud"


class McapGroupComponentDefinitionBase(SQLModel):
    """Base class for the McapGroupComponentDefinition model."""

    mcap_data_type: McapDataType

    """The id used to match this slot against calibration/transform data, e.g. ``"main"`` or
    ``"livox_front_left"``. Not the Studio slot name (e.g. ``"front"``). ``None`` when the slot
    has no associated calibration/transform."""
    frame_id: str | None = None

    """The MCAP channel id, unique within the source bag. Same meaning as ``mcap.channel_id``."""
    channel_id: int


class McapGroupComponentDefinitionCreate(McapGroupComponentDefinitionBase):
    """McapGroupComponentDefinition class when inserting."""

    collection_id: UUID


class McapGroupComponentDefinitionTable(McapGroupComponentDefinitionBase, table=True):
    """MCAP-specific metadata for a group component definition.

    One row per MCAP component collection. The ``collection_id`` primary key is the
    same id as the generic ``group_component_definition`` row.
    """

    __tablename__ = "mcap_group_component_definition"

    collection_id: UUID = Field(
        foreign_key="group_component_definition.collection_id",
        primary_key=True,
    )
