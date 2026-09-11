"""MCAP specialisation of a sequence: links to the recording holding the bag path.

A sequence with this 1:1 row references a ``recording`` (whose ``uri`` is the bag path). A
sequence without it stays valid (classic / non-MCAP sequences). Identity is the parent
sequence's ``sample_id``.
"""

from uuid import UUID

from sqlmodel import Field, SQLModel


class McapGroupSequenceTable(SQLModel, table=True):
    """1:1 link from a sequence to its MCAP recording."""

    __tablename__ = "mcap_group_sequence"
    sample_id: UUID = Field(foreign_key="sequence.sample_id", primary_key=True)
    recording_id: UUID = Field(foreign_key="recording.recording_id", index=True)
    """FK to the recording holding the bag path. Required. Not unique."""
