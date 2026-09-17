"""This module contains the McapGroupComponentDefinition model.

1:1 extension of ``group_component_definition``.  Video vs point cloud is ``mcap_data_type``
on this table.
"""

from __future__ import annotations

from enum import Enum
from uuid import UUID

from pydantic import BaseModel
from sqlmodel import Field, SQLModel

from lightly_studio.models.group_component_definition import GroupComponentDefinitionTable


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

    """The MCAP channel id, unique within the source bag. Same meaning as ``mcap.channel_id``.
    ``None`` until the first recording is indexed."""
    channel_id: int | None = None


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


class McapGroupComponentDefinitionView(BaseModel):
    """API view of one MCAP slot on a GROUP collection.

    Merges the generic slot naming/ordering (`GroupComponentDefinitionTable`) with the
    MCAP-specific metadata (`McapGroupComponentDefinitionTable`) that shares its
    `collection_id`.
    """

    collection_id: UUID
    group_component_name: str
    group_component_index: int
    mcap_data_type: McapDataType
    frame_id: str | None
    channel_id: int

    @classmethod
    def from_definitions(
        cls,
        gcd: GroupComponentDefinitionTable,
        mcap_gcd: McapGroupComponentDefinitionTable,
    ) -> McapGroupComponentDefinitionView:
        """Builds the API view of a slot from its generic and MCAP-specific rows.

        Args:
            gcd: The slot's generic naming/ordering row.
            mcap_gcd: The slot's MCAP-specific row. Its `collection_id` must match
                `gcd.collection_id`.
        """
        return cls(
            collection_id=mcap_gcd.collection_id,
            group_component_name=gcd.group_component_name,
            group_component_index=gcd.group_component_index,
            mcap_data_type=mcap_gcd.mcap_data_type,
            frame_id=mcap_gcd.frame_id,
            channel_id=mcap_gcd.channel_id,
        )
