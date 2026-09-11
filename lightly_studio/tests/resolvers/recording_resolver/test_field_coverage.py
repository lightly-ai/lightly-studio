"""Guards that recording's fields stay off sequence and sample tables."""

from __future__ import annotations

from lightly_studio.models.mcap import McapTable
from lightly_studio.models.recording import RecordingTable
from lightly_studio.models.sequence import SequenceTable


def test_sequence_and_sample_tables_have_no_uri() -> None:
    for table in (SequenceTable, McapTable):
        fields = set(table.model_fields)
        assert "uri" not in fields
        assert "recording_id" not in fields

    recording_fields = set(RecordingTable.model_fields)
    assert recording_fields == {"recording_id", "dataset_id", "format", "uri"}
