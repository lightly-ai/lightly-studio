"""MCAP specialisation of a sequence: links to the recording holding the bag path.

A sequence with this 1:1 row references a ``recording`` (whose ``uri`` is the bag path). A
sequence without it stays valid (classic / non-MCAP sequences). Identity is the parent
sequence's ``sample_id``.
"""

from typing import Optional
from uuid import UUID

import pydantic
from pydantic import BaseModel, ConfigDict
from sqlmodel import Field, SQLModel

from lightly_studio.models.mcap_group_component_definition import (
    McapGroupComponentDefinitionView,
)
from lightly_studio.models.recording import RecordingDetails, RecordingTable


class McapGroupSequenceTable(SQLModel, table=True):
    """1:1 link from a sequence to its MCAP recording."""

    __tablename__ = "mcap_group_sequence"
    sample_id: UUID = Field(foreign_key="sequence.sample_id", primary_key=True)
    recording_id: UUID = Field(foreign_key="recording.recording_id", index=True)
    """FK to the recording holding the bag path. Required. Not unique."""


class McapGroupSequenceInfoView(BaseModel):
    """The bag and component schema of one MCAP sequence.

    The "open this bag" payload: `recording` for a range-request open of the file, and
    `components`, sorted by slot index, for the numeric `channel_id` of each slot.
    Carries no per-tick data (no locators, calibration, transforms, or links) — see
    the group resolver for those.
    """

    sample_id: UUID
    recording: RecordingDetails
    components: list[McapGroupComponentDefinitionView]

    @classmethod
    def from_parts(
        cls,
        sample_id: UUID,
        recording: RecordingTable,
        components: list[McapGroupComponentDefinitionView],
    ) -> McapGroupSequenceInfoView:
        """Builds the view from the sequence's recording row and its sorted slots."""
        return cls(
            sample_id=sample_id,
            recording=RecordingDetails.from_recording_table(recording),
            components=components,
        )


class McapSequenceView(BaseModel):
    """View model for a single MCAP sequence in a list response."""

    sample_id: UUID
    sample_count: int


class McapSequenceViewsWithCount(BaseModel):
    """Result of listing MCAP sequences for a collection."""

    model_config = ConfigDict(populate_by_name=True)

    samples: list[McapSequenceView] = pydantic.Field(default=..., alias="data")
    total_count: int
    next_cursor: Optional[int] = pydantic.Field(default=None, alias="nextCursor")
