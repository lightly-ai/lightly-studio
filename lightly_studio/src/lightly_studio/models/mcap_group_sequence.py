"""MCAP specialisation of a sequence: the bag path lives here, not on ``sequence``.

A sequence with this 1:1 row has an ``.mcap`` path. A sequence without it stays valid
(classic / non-MCAP sequences). Identity is the parent sequence's ``sample_id``.
"""

from uuid import UUID

from sqlmodel import Field, SQLModel


class McapGroupSequenceBase(SQLModel):
    """Shared fields for the MCAP group sequence specialisation."""

    mcap_path: str
    """Path or URI of the bag. Required, non-empty. Not unique."""


class McapGroupSequenceTable(McapGroupSequenceBase, table=True):
    """1:1 link from a sequence to its MCAP bag path."""

    __tablename__ = "mcap_group_sequence"
    sample_id: UUID = Field(foreign_key="sequence.sample_id", primary_key=True)
