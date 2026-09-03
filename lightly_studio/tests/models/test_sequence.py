"""Tests for the Sequence model."""

from sqlalchemy import BigInteger
from sqlmodel import SQLModel

from lightly_studio.models.sequence import (  # noqa: F401, registers the tables in the metadata
    SampleSequenceLinkTable,
    SequenceTable,
)


def test_sequence_table__is_mcap_free() -> None:
    """A sequence only carries its own identity; MCAP details live in a separate table."""
    columns = SQLModel.metadata.tables["sequence"].columns
    assert set(columns.keys()) == {"seq_id", "sample_id"}


def test_sample_sequence_link_table__is_mcap_free() -> None:
    """A link only orders a sample in a sequence; it holds no MCAP locator fields."""
    columns = SQLModel.metadata.tables["sample_sequence_link"].columns
    assert set(columns.keys()) == {"sample_id", "seq_id", "seq_number", "timestamp_ns"}


def test_sample_sequence_link_table__timestamp_ns_is_64_bit() -> None:
    """Epoch nanoseconds need a BIGINT; a 32-bit INTEGER would overflow."""
    columns = SQLModel.metadata.tables["sample_sequence_link"].columns
    assert isinstance(columns["timestamp_ns"].type, BigInteger)
