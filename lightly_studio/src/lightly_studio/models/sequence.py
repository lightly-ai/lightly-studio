"""This module defines the Sequence model for the application.

A sequence is a sample that puts other samples in order: every linked sample gets a
``seq_number`` inside the sequence and, optionally, the sensor timestamp it was captured
at. Identity is the sequence sample's ``sample_id``, the same pattern as Group.
"""

from typing import Optional
from uuid import UUID

from sqlalchemy import BigInteger, UniqueConstraint
from sqlmodel import Field, SQLModel


class SequenceTable(SQLModel, table=True):
    """This class defines the Sequence model."""

    __tablename__ = "sequence"
    sample_id: UUID = Field(foreign_key="sample.sample_id", primary_key=True)


class SampleSequenceLinkTable(SQLModel, table=True):
    """Model to define the ordered links between a Sequence and Samples One-to-Many."""

    __tablename__ = "sample_sequence_link"
    __table_args__ = (
        UniqueConstraint("sequence_id", "seq_number", name="unique_seq_number_per_sequence"),
    )
    # Primary key, so a sample sits in at most one slot of at most one sequence.
    sample_id: UUID = Field(foreign_key="sample.sample_id", primary_key=True)
    sequence_id: UUID = Field(foreign_key="sequence.sample_id", index=True)
    seq_number: int
    # BigInteger: epoch nanoseconds overflow a 32-bit INTEGER on PostgreSQL.
    timestamp_ns: Optional[int] = Field(default=None, sa_type=BigInteger)
